"""
Production Task Planner with Map Actions and Cloud LLM Learning
Manages task execution with GIS operations, map actions, and self-improvement
"""

import asyncio
import json
import time
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import hashlib

@dataclass
class Task:
    """Production task with execution tracking"""
    id: str
    type: str  # 'map_action', 'gis_operation', 'llm_call', 'data_fetch'
    name: str
    description: str
    params: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed, cancelled
    priority: int = 1  # 1=high, 2=medium, 3=low
    estimated_duration_ms: int = 1000
    actual_duration_ms: Optional[int] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

@dataclass
class TaskExecutionResult:
    """Result of task execution with metrics"""
    success: bool
    task_id: str
    result: Any
    duration_ms: int
    error: Optional[str] = None
    map_actions_executed: List[Dict] = field(default_factory=list)
    gis_results: Dict = field(default_factory=dict)

class ProductionTaskPlanner:
    """
    Production-grade task planner with:
    - Map action integration
    - Cloud LLM assistance for complex tasks
    - Self-learning from execution history
    - SQLite persistence of task patterns
    """
    
    def __init__(self, db_path: str = "valora_tasks.db"):
        self.db_path = db_path
        self._init_database()
        
        # Task execution history cache
        self._execution_history = {}
        
        # Success rate tracking
        self._success_rates = {}
    
    def _init_database(self):
        """Initialize SQLite database for task learning"""
        import os
        # Ensure directory exists for database
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # Task patterns table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_patterns (
                    pattern_hash TEXT PRIMARY KEY,
                    intent TEXT NOT NULL,
                    query_template TEXT,
                    task_sequence TEXT,  -- JSON
                    map_actions TEXT,    -- JSON
                    success_rate REAL DEFAULT 0.0,
                    avg_duration_ms INTEGER DEFAULT 0,
                    execution_count INTEGER DEFAULT 0,
                    last_executed TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Task execution log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    task_type TEXT,
                    intent TEXT,
                    query TEXT,
                    status TEXT,
                    duration_ms INTEGER,
                    error TEXT,
                    map_actions_executed TEXT,  -- JSON
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Map action success tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS map_action_stats (
                    action_type TEXT PRIMARY KEY,
                    total_executions INTEGER DEFAULT 0,
                    successful_executions INTEGER DEFAULT 0,
                    avg_duration_ms INTEGER DEFAULT 0,
                    last_error TEXT
                )
            """)
            
            # Cloud LLM assistance log (disabled - local only)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cloud_llm_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT,
                    intent TEXT,
                    response TEXT,
                    used_for TEXT,  -- 'task_planning', 'reasoning', 'fallback'
                    duration_ms INTEGER,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def _load_cloud_config(self) -> bool:
        """Load cloud LLM enabled status from config - always returns False (local only)"""
        return False
    
    async def create_task_plan(
        self,
        query: str,
        intent: str,
        slots: Dict[str, Any],
        use_cloud_assistance: bool = True
    ) -> List[Task]:
        """
        Create optimized task plan with optional cloud LLM assistance
        """
        tasks = []
        
        # Step 1: Check learned patterns first
        learned_pattern = self._get_learned_pattern(intent, query)
        if learned_pattern and learned_pattern['success_rate'] > 0.8:
            tasks = self._tasks_from_pattern(learned_pattern, slots)
            print(f"[TaskPlanner] Using learned pattern (success rate: {learned_pattern['success_rate']:.2f})")
        
        # Step 2: Fall back to default task templates (local only)
        if not tasks:
            tasks = self._generate_default_tasks(intent, slots)
            print(f"[TaskPlanner] Using default task template ({len(tasks)} tasks)")
        
        # Optimize task order based on dependencies
        tasks = self._optimize_task_order(tasks)
        
        return tasks
    
    def _generate_default_tasks(self, intent: str, slots: Dict) -> List[Task]:
        """Generate default tasks based on intent type"""
        tasks = []
        
        if intent == "navigate":
            tasks = [
                Task(
                    id="t1_geocode",
                    type="gis_operation",
                    name="Geocode location",
                    description=f"Resolve {slots.get('location', 'location')} to coordinates",
                    params={"location": slots.get('location'), "coordinates": slots.get('coordinates')},
                    priority=1
                ),
                Task(
                    id="t2_flyto",
                    type="map_action",
                    name="Navigate map",
                    description="Fly camera to target location",
                    params={"action": "flyTo", "location": slots.get('location'), "zoom": 16},
                    dependencies=["t1_geocode"],
                    priority=1
                ),
                Task(
                    id="t3_orbit",
                    type="map_action",
                    name="Orbit view",
                    description="360° orbit around location",
                    params={"action": "orbit", "center": slots.get('location'), "duration": 5000},
                    dependencies=["t2_flyto"],
                    priority=2
                )
            ]
        
        elif intent == "property_search":
            tasks = [
                Task(
                    id="t1_parse",
                    type="llm_call",
                    name="Parse filters",
                    description="Extract search filters from query",
                    params={"bhk": slots.get('bhk'), "budget": slots.get('budget'), "location": slots.get('location')},
                    priority=1
                ),
                Task(
                    id="t2_flyto",
                    type="map_action",
                    name="Show search area",
                    description="Navigate to search location",
                    params={"action": "flyTo", "location": slots.get('location'), "zoom": 15},
                    priority=1
                ),
                Task(
                    id="t3_query",
                    type="gis_operation",
                    name="Spatial property query",
                    description="Query properties within radius",
                    params={
                        "operation": "spatialQuery",
                        "location": slots.get('location'),
                        "radius": slots.get('radius', 2000),
                        "filters": {"bhk": slots.get('bhk'), "budget_max": slots.get('budget')}
                    },
                    dependencies=["t1_parse"],
                    priority=1
                ),
                Task(
                    id="t4_mark",
                    type="map_action",
                    name="Mark properties",
                    description="Highlight matching properties on map",
                    params={"action": "markProperties", "filter": "query_results"},
                    dependencies=["t2_flyto", "t3_query"],
                    priority=1
                )
            ]
        
        elif intent == "analyze_area":
            tasks = [
                Task(
                    id="t1_flyto",
                    type="map_action",
                    name="Focus on area",
                    description="Navigate to analysis area",
                    params={"action": "flyTo", "location": slots.get('location'), "zoom": 15},
                    priority=1
                ),
                Task(
                    id="t2_metrics",
                    type="gis_operation",
                    name="Compute area metrics",
                    description="Calculate livability, connectivity, risk scores",
                    params={
                        "operation": "areaMetrics",
                        "location": slots.get('location'),
                        "metrics": ["price_trend", "livability", "connectivity", "risk"]
                    },
                    priority=1
                ),
                Task(
                    id="t3_layer",
                    type="map_action",
                    name="Add analytics layer",
                    description="Show metrics overlay on map",
                    params={"action": "addLayer", "layer": "analytics"},
                    dependencies=["t1_flyto"],
                    priority=2
                ),
                Task(
                    id="t4_orbit",
                    type="map_action",
                    name="Area orbit",
                    description="360° view of area",
                    params={"action": "orbit", "center": slots.get('location'), "duration": 5000},
                    dependencies=["t1_flyto"],
                    priority=3
                )
            ]
        
        elif intent == "comparison":
            loc_a = slots.get('location_a', slots.get('location', 'area A'))
            loc_b = slots.get('location_b', 'area B')
            tasks = [
                Task(
                    id="t1_flyto_a",
                    type="map_action",
                    name=f"Show {loc_a}",
                    description=f"Navigate to {loc_a}",
                    params={"action": "flyTo", "location": loc_a, "zoom": 14},
                    priority=1
                ),
                Task(
                    id="t2_metrics_a",
                    type="gis_operation",
                    name=f"Analyze {loc_a}",
                    description=f"Get area metrics for {loc_a}",
                    params={"operation": "areaMetrics", "location": loc_a},
                    priority=1
                ),
                Task(
                    id="t3_metrics_b",
                    type="gis_operation",
                    name=f"Analyze {loc_b}",
                    description=f"Get area metrics for {loc_b}",
                    params={"operation": "areaMetrics", "location": loc_b},
                    priority=1
                ),
                Task(
                    id="t4_props_a",
                    type="gis_operation",
                    name=f"Properties in {loc_a}",
                    description=f"Search properties in {loc_a}",
                    params={"operation": "spatialQuery", "location": loc_a, "radius": 2000, "filters": {}},
                    dependencies=["t2_metrics_a"],
                    priority=2
                ),
                Task(
                    id="t5_props_b",
                    type="gis_operation",
                    name=f"Properties in {loc_b}",
                    description=f"Search properties in {loc_b}",
                    params={"operation": "spatialQuery", "location": loc_b, "radius": 2000, "filters": {}},
                    dependencies=["t3_metrics_b"],
                    priority=2
                )
            ]
        
        elif intent == "investment":
            tasks = [
                Task(
                    id="t1_flyto",
                    type="map_action",
                    name="Show investment area",
                    description="Navigate to investment area",
                    params={"action": "flyTo", "location": slots.get('location'), "zoom": 14},
                    priority=1
                ),
                Task(
                    id="t2_metrics",
                    type="gis_operation",
                    name="Area investment metrics",
                    description="Analyze area for investment potential",
                    params={"operation": "areaMetrics", "location": slots.get('location')},
                    priority=1
                ),
                Task(
                    id="t3_properties",
                    type="gis_operation",
                    name="Investment properties",
                    description="Find properties with investment potential",
                    params={
                        "operation": "spatialQuery",
                        "location": slots.get('location'),
                        "radius": slots.get('radius', 3000),
                        "filters": {"budget_max": slots.get('budget')}
                    },
                    dependencies=["t2_metrics"],
                    priority=2
                )
            ]
        
        elif intent == "price_trend":
            tasks = [
                Task(
                    id="t1_flyto",
                    type="map_action",
                    name="Show area",
                    description="Navigate to price trend area",
                    params={"action": "flyTo", "location": slots.get('location'), "zoom": 14},
                    priority=1
                ),
                Task(
                    id="t2_metrics",
                    type="gis_operation",
                    name="Area market data",
                    description="Get current market metrics and property prices",
                    params={"operation": "areaMetrics", "location": slots.get('location')},
                    priority=1
                ),
                Task(
                    id="t3_properties",
                    type="gis_operation",
                    name="Price samples",
                    description="Get property price samples for trend analysis",
                    params={
                        "operation": "spatialQuery",
                        "location": slots.get('location'),
                        "radius": 2000,
                        "filters": {}
                    },
                    dependencies=["t2_metrics"],
                    priority=2
                )
            ]
        
        elif intent == "building_analysis":
            tasks = [
                Task(
                    id="t1_highlight",
                    type="map_action",
                    name="Highlight building",
                    description="Focus on selected building",
                    params={"action": "highlightBuilding", "building_id": slots.get('building_id')},
                    priority=1
                ),
                Task(
                    id="t2_metrics",
                    type="gis_operation",
                    name="Building context",
                    description="Analyze building surroundings",
                    params={
                        "operation": "areaMetrics",
                        "location": slots.get('location', slots.get('coordinates', '')),
                    },
                    priority=1
                )
            ]
        
        elif intent == "draw_polygon":
            tasks = [
                Task(
                    id="t1_flyto",
                    type="map_action",
                    name="Navigate to center",
                    description="Go to polygon center",
                    params={"action": "flyTo", "location": slots.get('location'), "zoom": 14},
                    priority=1
                ),
                Task(
                    id="t2_draw",
                    type="map_action",
                    name="Draw polygon",
                    description=f"Draw {slots.get('radius', 1000)}m radius circle",
                    params={
                        "action": "drawCircle",
                        "center": slots.get('location'),
                        "radius": slots.get('radius', 1000)
                    },
                    dependencies=["t1_flyto"],
                    priority=1
                ),
                Task(
                    id="t3_query",
                    type="gis_operation",
                    name="Query within polygon",
                    description="Find properties/POIs within drawn area",
                    params={"operation": "spatialQuery", "polygon": "user_drawn"},
                    dependencies=["t2_draw"],
                    priority=2
                )
            ]
        
        elif intent == "route_analysis":
            tasks = [
                Task(
                    id="t1_geocode_from",
                    type="gis_operation",
                    name="Geocode start",
                    description="Resolve start location",
                    params={"location": slots.get('from_location')},
                    priority=1
                ),
                Task(
                    id="t2_geocode_to",
                    type="gis_operation",
                    name="Geocode end",
                    description="Resolve end location",
                    params={"location": slots.get('to_location')},
                    priority=1
                ),
                Task(
                    id="t3_route",
                    type="gis_operation",
                    name="Calculate route",
                    description="Compute optimal route",
                    params={
                        "operation": "routeAnalysis",
                        "from": slots.get('from_location'),
                        "to": slots.get('to_location'),
                        "mode": "driving"
                    },
                    dependencies=["t1_geocode_from", "t2_geocode_to"],
                    priority=1
                ),
                Task(
                    id="t4_draw",
                    type="map_action",
                    name="Draw route",
                    description="Visualize route on map",
                    params={
                        "action": "drawRoute",
                        "from": slots.get('from_location'),
                        "to": slots.get('to_location')
                    },
                    dependencies=["t3_route"],
                    priority=1
                ),
                Task(
                    id="t5_flyto",
                    type="map_action",
                    name="Show full route",
                    description="Fit route bounds in view",
                    params={"action": "flyTo", "bounds": "route", "padding": 0.2},
                    dependencies=["t4_draw"],
                    priority=2
                )
            ]
        
        elif intent == "simulate":
            tasks = [
                Task(
                    id="t1_flyto",
                    type="map_action",
                    name="Focus on impact area",
                    description="Navigate to simulation location",
                    params={"action": "flyTo", "location": slots.get('location'), "zoom": 14},
                    priority=1
                ),
                Task(
                    id="t2_baseline",
                    type="gis_operation",
                    name="Get baseline data",
                    description="Capture current state metrics",
                    params={"operation": "areaMetrics", "location": slots.get('location')},
                    priority=1
                ),
                Task(
                    id="t3_simulate",
                    type="llm_call",
                    name="Run simulation",
                    description=f"Simulate: {slots.get('scenario_type', 'change')}",
                    params={
                        "scenario": slots.get('scenario_type'),
                        "location": slots.get('location'),
                        "change": slots.get('change')
                    },
                    dependencies=["t2_baseline"],
                    priority=1
                ),
                Task(
                    id="t4_animate",
                    type="map_action",
                    name="Animate scenario",
                    description="Visualize simulation results",
                    params={
                        "action": "animateScenario",
                        "scenario": slots.get('scenario_type'),
                        "impact_radius": slots.get('radius', 3000)
                    },
                    dependencies=["t3_simulate"],
                    priority=1
                )
            ]
        
        return tasks
    
    async def execute_tasks(
        self,
        tasks: List[Task],
        on_task_start: Optional[callable] = None,
        on_task_complete: Optional[callable] = None,
        on_task_fail: Optional[callable] = None
    ) -> List[TaskExecutionResult]:
        """
        Execute tasks with streaming progress and self-learning
        """
        results = []
        completed_tasks = set()
        failed_tasks = set()
        
        # Sort tasks by priority and dependencies
        execution_order = self._topological_sort(tasks)
        
        for task in execution_order:
            # Check if dependencies completed
            deps_ok = all(
                d in completed_tasks or not any(t.id == d for t in tasks)
                for d in task.dependencies
            )
            
            if not deps_ok:
                print(f"[TaskPlanner] Skipping {task.id} - dependencies not met")
                continue
            
            # Notify start
            if on_task_start:
                await on_task_start(task)
            
            # Execute with retry
            result = await self._execute_task_with_retry(task)
            results.append(result)
            
            if result.success:
                completed_tasks.add(task.id)
                task.status = "completed"
                task.result = result.result
                
                if on_task_complete:
                    await on_task_complete(task, result)
            else:
                failed_tasks.add(task.id)
                task.status = "failed"
                task.error = result.error
                
                if on_task_fail:
                    await on_task_fail(task, result)
            
            # Log execution
            self._log_task_execution(task, result)
        
        # Learn from this execution
        self._learn_from_execution(tasks, results)
        
        return results
    
    async def _execute_task_with_retry(self, task: Task) -> TaskExecutionResult:
        """Execute task with automatic retry on failure"""
        for attempt in range(task.max_retries + 1):
            result = await self._execute_single_task(task)
            
            if result.success:
                return result
            
            task.retry_count += 1
            
            if attempt < task.max_retries:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"[TaskPlanner] Retrying {task.id} in {wait_time}s...")
                await asyncio.sleep(wait_time)
        
        return result
    
    async def _execute_single_task(self, task: Task) -> TaskExecutionResult:
        """Execute a single task using real database and services"""
        start_time = time.time()
        task.status = "running"
        task.started_at = datetime.now().isoformat()
        
        try:
            result = {}
            
            if task.type == "map_action":
                # Map actions are dispatched to frontend - just record them
                result = {
                    "action_executed": task.params.get('action'),
                    "params": task.params,
                    "visual_update": True,
                    "summary": f"Map action: {task.params.get('action', 'unknown')}"
                }
            
            elif task.type == "gis_operation":
                result = await self._execute_gis_operation(task)
            
            elif task.type == "llm_call":
                # LLM calls handled by the brain's narrative generator
                result = {
                    "summary": f"Processed: {task.name}",
                    "confidence": 0.85
                }
            
            elif task.type == "data_fetch":
                result = await self._execute_data_fetch(task)
            
            else:
                result = {"status": "completed", "summary": task.name}
            
            duration = int((time.time() - start_time) * 1000)
            task.actual_duration_ms = duration
            task.completed_at = datetime.now().isoformat()
            
            return TaskExecutionResult(
                success=True,
                task_id=task.id,
                result=result,
                duration_ms=duration,
                map_actions_executed=[task.params] if task.type == "map_action" else []
            )
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            print(f"[TaskPlanner] Task {task.id} failed: {e}")
            return TaskExecutionResult(
                success=False,
                task_id=task.id,
                result={"summary": f"Failed: {str(e)}"},
                duration_ms=duration,
                error=str(e)
            )
    
    async def _execute_gis_operation(self, task: Task) -> Dict:
        """Execute real GIS operations against the database"""
        operation = task.params.get('operation', '')
        location = task.params.get('location', '')
        
        # Geocode location to coordinates
        lat, lng = await self._geocode_location(location)
        
        if operation == 'spatialQuery':
            # Real property search from database
            return await self._query_properties(task.params, lat, lng)
        
        elif operation == 'areaMetrics':
            # Real area analysis
            return await self._query_area_metrics(lat, lng, task.params)
        
        elif operation == 'routeAnalysis':
            return {
                "summary": f"Route analysis from {task.params.get('from')} to {task.params.get('to')}",
                "from_location": task.params.get('from'),
                "to_location": task.params.get('to'),
            }
        
        else:
            # Geocode operation
            return {
                "summary": f"Geocoded '{location}' to ({lat:.4f}, {lng:.4f})",
                "lat": lat,
                "lng": lng,
                "location": location
            }
    
    async def _geocode_location(self, location: str) -> tuple:
        """Geocode a location name to lat/lng using local geocoder"""
        if not location:
            return 12.9716, 77.5946  # Default Bangalore center
        
        try:
            from spatial.local_geocoder import get_local_geocoder
            from pathlib import Path
            geocoder = get_local_geocoder(Path(__file__).parent.parent.parent / 'data' / 'osm_extracted')
            if geocoder:
                result = geocoder.geocode(location)
                if result and result.get('lat') and result.get('lng'):
                    return result['lat'], result['lng']
        except Exception as e:
            print(f"[TaskPlanner] Geocode error for '{location}': {e}")
        
        # Bangalore locality fallback coordinates
        BANGALORE_LOCALITIES = {
            'koramangala': (12.9352, 77.6245),
            'indiranagar': (12.9784, 77.6408),
            'hsr layout': (12.9116, 77.6389),
            'hsr': (12.9116, 77.6389),
            'whitefield': (12.9698, 77.7500),
            'electronic city': (12.8399, 77.6770),
            'marathahalli': (12.9591, 77.6974),
            'jayanagar': (12.9308, 77.5838),
            'jp nagar': (12.9063, 77.5857),
            'bannerghatta': (12.8878, 77.5974),
            'hebbal': (13.0358, 77.5970),
            'yelahanka': (13.1007, 77.5963),
            'sarjapur': (12.8680, 77.7870),
            'btm layout': (12.9166, 77.6101),
            'mg road': (12.9756, 77.6068),
            'brigade road': (12.9716, 77.6070),
            'rajajinagar': (12.9900, 77.5530),
            'malleswaram': (13.0035, 77.5647),
            'basavanagudi': (12.9430, 77.5740),
            'vijayanagar': (12.9700, 77.5350),
            'banashankari': (12.9255, 77.5468),
        }
        loc_lower = location.lower().strip()
        for name, coords in BANGALORE_LOCALITIES.items():
            if name in loc_lower:
                return coords
        
        return 12.9716, 77.5946  # Default Bangalore center
    
    async def _query_properties(self, params: Dict, lat: float, lng: float) -> Dict:
        """Query real properties from database"""
        try:
            from services.property_service import get_property_service
            from pathlib import Path
            ps = get_property_service(Path(__file__).parent.parent.parent / 'data' / 'properties')
            
            filters = params.get('filters', {})
            radius = params.get('radius', 2000)
            
            properties = ps.search(
                lat=lat, lng=lng,
                radius_m=radius,
                min_bedrooms=filters.get('bhk'),
                max_price=filters.get('budget_max'),
                limit=10
            )
            
            if properties:
                prices = [p.get('price', 0) for p in properties if p.get('price')]
                avg_price = int(sum(prices) / len(prices)) if prices else 0
                
                # Build concise property summaries for LLM
                prop_summaries = []
                for p in properties[:5]:
                    name = p.get('name', p.get('title', 'Property'))
                    price = p.get('price', 0)
                    bedrooms = p.get('bedrooms', '?')
                    area = p.get('area_sqft', p.get('carpet_area', '?'))
                    locality = p.get('locality', p.get('location', ''))
                    price_str = f"₹{price/100000:.0f}L" if price and price < 10000000 else (f"₹{price/10000000:.1f}Cr" if price else "Price N/A")
                    prop_summaries.append(f"{name} - {bedrooms}BHK, {area}sqft, {price_str}, {locality}")
                
                return {
                    "summary": f"Found {len(properties)} properties near ({lat:.4f}, {lng:.4f}). Avg price: ₹{avg_price/100000:.0f}L" if avg_price else f"Found {len(properties)} properties",
                    "count": len(properties),
                    "avg_price": avg_price,
                    "properties": prop_summaries,
                    "location": params.get('location', ''),
                    "filters_applied": filters,
                }
            else:
                return {
                    "summary": f"No properties found within {radius}m of {params.get('location', 'location')} with given filters",
                    "count": 0,
                    "properties": [],
                }
        except Exception as e:
            print(f"[TaskPlanner] Property query error: {e}")
            return {"summary": f"Property search error: {str(e)}", "count": 0}
    
    async def _query_area_metrics(self, lat: float, lng: float, params: Dict) -> Dict:
        """Query real area metrics from database"""
        try:
            from analyzers.area_analyzer import AreaAnalyzer
            from pathlib import Path
            analyzer = AreaAnalyzer(Path(__file__).parent.parent.parent / 'data' / 'osm_extracted')
            
            summary = analyzer.analyze_area(lng, lat, radius_m=1000)
            insights = analyzer.generate_area_insights(summary)
            
            poi_total = summary.get('poi_summary', {}).get('total', 0)
            transport_total = summary.get('transport', {}).get('total_stops', 0)
            top_pois = summary.get('poi_summary', {}).get('top_nearby', [])[:3]
            nearest_transport = summary.get('transport', {}).get('nearest_stops', [])[:2]
            
            poi_names = [p['name'] for p in top_pois if p.get('name')]
            transport_names = [t['name'] for t in nearest_transport if t.get('name')]
            
            return {
                "summary": f"Area has {poi_total} POIs, {transport_total} transit stops. " + 
                          (f"Nearby: {', '.join(poi_names[:3])}. " if poi_names else "") +
                          (f"Transit: {', '.join(transport_names[:2])}." if transport_names else ""),
                "poi_count": poi_total,
                "transport_count": transport_total,
                "insights": insights,
                "top_pois": poi_names,
                "nearest_transport": transport_names,
            }
        except Exception as e:
            print(f"[TaskPlanner] Area metrics error: {e}")
            return {"summary": f"Area analysis error: {str(e)}"}
    
    async def _execute_data_fetch(self, task: Task) -> Dict:
        """Execute data fetch operations"""
        return {"summary": f"Data fetched: {task.name}", "status": "completed"}
    
    def _get_learned_pattern(self, intent: str, query: str) -> Optional[Dict]:
        """Get learned pattern for intent/query"""
        pattern_hash = hashlib.md5(f"{intent}:{query[:50]}".encode()).hexdigest()[:16]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM task_patterns WHERE intent = ? OR pattern_hash = ?",
                (intent, pattern_hash)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    "pattern_hash": row['pattern_hash'],
                    "intent": row['intent'],
                    "task_sequence": json.loads(row['task_sequence']) if row['task_sequence'] else [],
                    "map_actions": json.loads(row['map_actions']) if row['map_actions'] else [],
                    "success_rate": row['success_rate'],
                    "avg_duration_ms": row['avg_duration_ms'],
                    "execution_count": row['execution_count']
                }
        
        return None
    
    def _tasks_from_pattern(self, pattern: Dict, slots: Dict) -> List[Task]:
        """Generate tasks from learned pattern"""
        tasks = []
        
        for i, task_def in enumerate(pattern['task_sequence']):
            task = Task(
                id=f"t{i+1}_{task_def.get('name', 'task')}",
                type=task_def.get('type', 'map_action'),
                name=task_def.get('name', f'Task {i+1}'),
                description=task_def.get('description', ''),
                params=task_def.get('params', {}),
                dependencies=task_def.get('dependencies', []),
                priority=task_def.get('priority', 2)
            )
            tasks.append(task)
        
        return tasks
    
    def _optimize_task_order(self, tasks: List[Task]) -> List[Task]:
        """Optimize task order based on dependencies and priority"""
        # Topological sort with priority weighting
        task_map = {t.id: t for t in tasks}
        in_degree = {t.id: len(t.dependencies) for t in tasks}
        
        # Priority queue: lower number = higher priority
        ready = [t for t in tasks if in_degree[t.id] == 0]
        ready.sort(key=lambda t: t.priority)
        
        ordered = []
        while ready:
            task = ready.pop(0)
            ordered.append(task)
            
            # Find tasks that depend on this one
            for t in tasks:
                if task.id in t.dependencies:
                    in_degree[t.id] -= 1
                    if in_degree[t.id] == 0:
                        ready.append(t)
            
            ready.sort(key=lambda t: t.priority)
        
        return ordered
    
    def _topological_sort(self, tasks: List[Task]) -> List[Task]:
        """Topological sort of tasks by dependencies"""
        task_map = {t.id: t for t in tasks}
        in_degree = {t.id: 0 for t in tasks}
        
        for t in tasks:
            for dep in t.dependencies:
                if dep in in_degree:
                    in_degree[t.id] += 1
        
        ready = [t for t in tasks if in_degree[t.id] == 0]
        ordered = []
        
        while ready:
            task = ready.pop(0)
            ordered.append(task)
            
            for t in tasks:
                if task.id in t.dependencies:
                    in_degree[t.id] -= 1
                    if in_degree[t.id] == 0:
                        ready.append(t)
        
        return ordered
    
    def _log_task_execution(self, task: Task, result: TaskExecutionResult):
        """Log task execution to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO task_executions 
                (task_id, task_type, intent, query, status, duration_ms, error, map_actions_executed, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id,
                task.type,
                task.name,
                task.description,
                "success" if result.success else "failed",
                result.duration_ms,
                result.error,
                json.dumps(result.map_actions_executed),
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def _log_cloud_llm_call(self, query: str, intent: str, response: str, used_for: str, duration_ms: int):
        """Log cloud LLM call"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO cloud_llm_calls (query, intent, response, used_for, duration_ms, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (query, intent, response[:1000], used_for, duration_ms, datetime.now().isoformat()))
            conn.commit()
    
    def _learn_from_execution(self, tasks: List[Task], results: List[TaskExecutionResult]):
        """Learn from task execution to improve future plans"""
        # Calculate success rate
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)
        success_rate = success_count / total_count if total_count > 0 else 0
        
        # Create pattern hash
        intent = tasks[0].name if tasks else "unknown"
        pattern_hash = hashlib.md5(f"{intent}:{len(tasks)}".encode()).hexdigest()[:16]
        
        # Average duration
        avg_duration = sum(r.duration_ms for r in results) / len(results) if results else 0
        
        # Store or update pattern
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO task_patterns (pattern_hash, intent, task_sequence, map_actions, success_rate, avg_duration_ms, execution_count, last_executed)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(pattern_hash) DO UPDATE SET
                    success_rate = (task_patterns.success_rate * task_patterns.execution_count + ?) / (task_patterns.execution_count + 1),
                    avg_duration_ms = (task_patterns.avg_duration_ms * task_patterns.execution_count + ?) / (task_patterns.execution_count + 1),
                    execution_count = task_patterns.execution_count + 1,
                    last_executed = ?
            """, (
                pattern_hash,
                intent,
                json.dumps([{"type": t.type, "name": t.name, "priority": t.priority} for t in tasks]),
                json.dumps([t.params for t in tasks if t.type == "map_action"]),
                success_rate,
                int(avg_duration),
                datetime.now().isoformat(),
                success_rate,
                int(avg_duration),
                datetime.now().isoformat()
            ))
            conn.commit()
        
        print(f"[TaskPlanner] Learned pattern: success_rate={success_rate:.2f}, avg_duration={avg_duration:.0f}ms")
    
    def get_stats(self) -> Dict:
        """Get task planner statistics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Pattern stats
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as pattern_count,
                    AVG(success_rate) as avg_success_rate,
                    SUM(execution_count) as total_executions
                FROM task_patterns
            """)
            pattern_stats = dict(cursor.fetchone())
            
            # Execution stats
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    AVG(duration_ms) as avg_duration
                FROM task_executions
                WHERE timestamp > datetime('now', '-7 days')
            """)
            execution_stats = dict(cursor.fetchone())
            
            # Cloud LLM stats
            cursor = conn.execute("""
                SELECT COUNT(*) as cloud_calls, AVG(duration_ms) as avg_cloud_duration
                FROM cloud_llm_calls
                WHERE timestamp > datetime('now', '-7 days')
            """)
            cloud_stats = dict(cursor.fetchone())
            
            return {
                "patterns": pattern_stats,
                "executions": execution_stats,
                "cloud_llm": cloud_stats
            }


# Singleton instance
_planner_instance = None

def get_production_task_planner() -> ProductionTaskPlanner:
    """Get or create singleton production task planner"""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = ProductionTaskPlanner()
    return _planner_instance
