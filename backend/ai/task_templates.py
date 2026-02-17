"""
Task Templates - Reusable, Parameterized Task Templates
Implements a template library for common task patterns with auto-generation support.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Tuple
from datetime import datetime
import json
import re
import sqlite3
from pathlib import Path
import os


@dataclass
class TaskSpec:
    """
    Specification for a single task within a template.
    Supports parameterized values using ${param_name} syntax.
    """
    id_template: str                    # e.g., "t1_${location}_geocode"
    action: str                         # e.g., "geocode", "search", "analyze"
    entity: str                         # e.g., "property", "area", "POI"
    task_type: str = "generic"          # map_action, gis_operation, llm_call, data_fetch
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    priority: int = 1
    estimated_duration_ms: int = 1000
    max_retries: int = 2
    
    def render(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render the task spec with context variables.
        Returns a dictionary suitable for TaskNode creation.
        """
        def substitute(value: Any) -> Any:
            if isinstance(value, str):
                # Substitute ${param} patterns
                for key, val in context.items():
                    value = value.replace(f"${{{key}}}", str(val))
                return value
            elif isinstance(value, dict):
                return {k: substitute(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute(v) for v in value]
            return value
        
        return {
            "id": substitute(self.id_template),
            "action": substitute(self.action),
            "entity": substitute(self.entity),
            "task_type": substitute(self.task_type),
            "parameters": substitute(self.parameters),
            "dependencies": substitute(self.dependencies),
            "priority": self.priority,
            "estimated_duration_ms": self.estimated_duration_ms,
            "max_retries": self.max_retries
        }


@dataclass
class TaskTemplate:
    """
    A reusable, parameterized task template.
    Templates capture common task patterns for efficient reuse.
    """
    id: str
    name: str
    description: str
    intent_patterns: List[str]              # Regex patterns for intent matching
    parameter_schema: Dict[str, Any]        # JSON schema for parameters
    task_sequence: List[TaskSpec]           # Parameterized task definitions
    success_rate: float = 0.0
    avg_duration_ms: int = 0
    execution_count: int = 0
    last_used: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)
    version: int = 1
    
    def matches_intent(self, intent: str) -> bool:
        """Check if this template matches the given intent"""
        for pattern in self.intent_patterns:
            if re.search(pattern, intent, re.IGNORECASE):
                return True
        return False
    
    def validate_parameters(self, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate parameters against schema.
        Returns (is_valid, list_of_errors).
        """
        errors = []
        schema = self.parameter_schema
        
        # Check required parameters
        required = schema.get("required", [])
        for param in required:
            if param not in params:
                errors.append(f"Missing required parameter: {param}")
        
        # Check parameter types
        properties = schema.get("properties", {})
        for param, value in params.items():
            if param in properties:
                expected_type = properties[param].get("type")
                if expected_type:
                    type_map = {
                        "string": str,
                        "number": (int, float),
                        "integer": int,
                        "boolean": bool,
                        "array": list,
                        "object": dict
                    }
                    if expected_type in type_map:
                        if not isinstance(value, type_map[expected_type]):
                            errors.append(f"Parameter '{param}' should be {expected_type}")
        
        return len(errors) == 0, errors
    
    def render_tasks(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Render all tasks in the template with given parameters.
        Returns list of task dictionaries.
        """
        # Merge with defaults
        defaults = self.parameter_schema.get("default", {})
        context = {**defaults, **params}
        
        return [spec.render(context) for spec in self.task_sequence]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize template to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "intent_patterns": self.intent_patterns,
            "parameter_schema": self.parameter_schema,
            "task_sequence": [
                {
                    "id_template": spec.id_template,
                    "action": spec.action,
                    "entity": spec.entity,
                    "task_type": spec.task_type,
                    "parameters": spec.parameters,
                    "dependencies": spec.dependencies,
                    "priority": spec.priority,
                    "estimated_duration_ms": spec.estimated_duration_ms,
                    "max_retries": spec.max_retries
                }
                for spec in self.task_sequence
            ],
            "success_rate": self.success_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "execution_count": self.execution_count,
            "last_used": self.last_used,
            "created_at": self.created_at,
            "tags": self.tags,
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskTemplate":
        """Deserialize template from dictionary"""
        task_sequence = [
            TaskSpec(
                id_template=spec["id_template"],
                action=spec["action"],
                entity=spec["entity"],
                task_type=spec.get("task_type", "generic"),
                parameters=spec.get("parameters", {}),
                dependencies=spec.get("dependencies", []),
                priority=spec.get("priority", 1),
                estimated_duration_ms=spec.get("estimated_duration_ms", 1000),
                max_retries=spec.get("max_retries", 2)
            )
            for spec in data.get("task_sequence", [])
        ]
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            intent_patterns=data["intent_patterns"],
            parameter_schema=data["parameter_schema"],
            task_sequence=task_sequence,
            success_rate=data.get("success_rate", 0.0),
            avg_duration_ms=data.get("avg_duration_ms", 0),
            execution_count=data.get("execution_count", 0),
            last_used=data.get("last_used"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            tags=data.get("tags", []),
            version=data.get("version", 1)
        )


# Import Tuple for type hints
from typing import Tuple


class TemplateLibrary:
    """
    Library of task templates with CRUD operations and matching.
    Persists templates to SQLite for durability.
    """
    
    def __init__(self, db_path: str = "valora_templates.db"):
        self.db_path = db_path
        self._templates: Dict[str, TaskTemplate] = {}
        self._intent_index: Dict[str, List[str]] = {}  # intent -> template ids
        self._initialized = False
        
        # Initialize database and load templates
        self._init_database()
        self._load_templates()
    
    def _init_database(self):
        """Initialize SQLite database for template storage"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    intent_patterns TEXT,    -- JSON array
                    parameter_schema TEXT,   -- JSON object
                    task_sequence TEXT,      -- JSON array
                    success_rate REAL DEFAULT 0.0,
                    avg_duration_ms INTEGER DEFAULT 0,
                    execution_count INTEGER DEFAULT 0,
                    last_used TEXT,
                    created_at TEXT,
                    tags TEXT,               -- JSON array
                    version INTEGER DEFAULT 1
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_templates_intent 
                ON task_templates(intent_patterns)
            """)
            
            conn.commit()
    
    def _load_templates(self):
        """Load all templates from database into memory"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM task_templates")
            
            for row in cursor.fetchall():
                template_data = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "intent_patterns": json.loads(row[3]) if row[3] else [],
                    "parameter_schema": json.loads(row[4]) if row[4] else {},
                    "task_sequence": json.loads(row[5]) if row[5] else [],
                    "success_rate": row[6],
                    "avg_duration_ms": row[7],
                    "execution_count": row[8],
                    "last_used": row[9],
                    "created_at": row[10],
                    "tags": json.loads(row[11]) if row[11] else [],
                    "version": row[12]
                }
                
                template = TaskTemplate.from_dict(template_data)
                self._templates[template.id] = template
                
                # Build intent index
                for pattern in template.intent_patterns:
                    # Extract intent keyword from pattern
                    match = re.search(r'\b(\w+)\b', pattern)
                    if match:
                        intent_key = match.group(1).lower()
                        if intent_key not in self._intent_index:
                            self._intent_index[intent_key] = []
                        self._intent_index[intent_key].append(template.id)
        
        self._initialized = True
    
    def add_template(self, template: TaskTemplate) -> bool:
        """Add a new template to the library"""
        if template.id in self._templates:
            return False
        
        # Persist to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO task_templates 
                (id, name, description, intent_patterns, parameter_schema, 
                 task_sequence, success_rate, avg_duration_ms, execution_count,
                 last_used, created_at, tags, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template.id,
                template.name,
                template.description,
                json.dumps(template.intent_patterns),
                json.dumps(template.parameter_schema),
                json.dumps([{
                    "id_template": spec.id_template,
                    "action": spec.action,
                    "entity": spec.entity,
                    "task_type": spec.task_type,
                    "parameters": spec.parameters,
                    "dependencies": spec.dependencies,
                    "priority": spec.priority,
                    "estimated_duration_ms": spec.estimated_duration_ms,
                    "max_retries": spec.max_retries
                } for spec in template.task_sequence]),
                template.success_rate,
                template.avg_duration_ms,
                template.execution_count,
                template.last_used,
                template.created_at,
                json.dumps(template.tags),
                template.version
            ))
            conn.commit()
        
        # Add to memory
        self._templates[template.id] = template
        
        # Update intent index
        for pattern in template.intent_patterns:
            match = re.search(r'\b(\w+)\b', pattern)
            if match:
                intent_key = match.group(1).lower()
                if intent_key not in self._intent_index:
                    self._intent_index[intent_key] = []
                if template.id not in self._intent_index[intent_key]:
                    self._intent_index[intent_key].append(template.id)
        
        return True
    
    def update_template(self, template: TaskTemplate) -> bool:
        """Update an existing template"""
        if template.id not in self._templates:
            return False
        
        template.version = self._templates[template.id].version + 1
        
        # Update database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE task_templates 
                SET name=?, description=?, intent_patterns=?, parameter_schema=?,
                    task_sequence=?, success_rate=?, avg_duration_ms=?, execution_count=?,
                    last_used=?, tags=?, version=?
                WHERE id=?
            """, (
                template.name,
                template.description,
                json.dumps(template.intent_patterns),
                json.dumps(template.parameter_schema),
                json.dumps([{
                    "id_template": spec.id_template,
                    "action": spec.action,
                    "entity": spec.entity,
                    "task_type": spec.task_type,
                    "parameters": spec.parameters,
                    "dependencies": spec.dependencies,
                    "priority": spec.priority,
                    "estimated_duration_ms": spec.estimated_duration_ms,
                    "max_retries": spec.max_retries
                } for spec in template.task_sequence]),
                template.success_rate,
                template.avg_duration_ms,
                template.execution_count,
                template.last_used,
                json.dumps(template.tags),
                template.version,
                template.id
            ))
            conn.commit()
        
        self._templates[template.id] = template
        return True
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template from the library"""
        if template_id not in self._templates:
            return False
        
        # Remove from database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM task_templates WHERE id=?", (template_id,))
            conn.commit()
        
        # Remove from memory
        template = self._templates.pop(template_id)
        
        # Update intent index
        for pattern in template.intent_patterns:
            match = re.search(r'\b(\w+)\b', pattern)
            if match:
                intent_key = match.group(1).lower()
                if intent_key in self._intent_index:
                    if template_id in self._intent_index[intent_key]:
                        self._intent_index[intent_key].remove(template_id)
        
        return True
    
    def get_template(self, template_id: str) -> Optional[TaskTemplate]:
        """Get a template by ID"""
        return self._templates.get(template_id)
    
    def list_templates(self, tag: Optional[str] = None) -> List[TaskTemplate]:
        """List all templates, optionally filtered by tag"""
        templates = list(self._templates.values())
        
        if tag:
            templates = [t for t in templates if tag in t.tags]
        
        return sorted(templates, key=lambda t: t.success_rate, reverse=True)
    
    def find_matching_templates(self, intent: str) -> List[TaskTemplate]:
        """Find templates that match the given intent"""
        matches = []
        
        for template in self._templates.values():
            if template.matches_intent(intent):
                matches.append(template)
        
        # Sort by success rate
        return sorted(matches, key=lambda t: t.success_rate, reverse=True)
    
    def get_best_template(self, intent: str, params: Dict[str, Any]) -> Optional[TaskTemplate]:
        """Get the best matching template for intent and parameters"""
        matches = self.find_matching_templates(intent)
        
        for template in matches:
            is_valid, _ = template.validate_parameters(params)
            if is_valid:
                return template
        
        return None
    
    def record_execution(
        self, 
        template_id: str, 
        success: bool, 
        duration_ms: int
    ) -> bool:
        """Record execution result for template statistics"""
        template = self._templates.get(template_id)
        if not template:
            return False
        
        # Update statistics
        total_duration = template.avg_duration_ms * template.execution_count + duration_ms
        template.execution_count += 1
        template.avg_duration_ms = total_duration // template.execution_count
        
        if success:
            successful = int(template.success_rate * (template.execution_count - 1))
            template.success_rate = (successful + 1) / template.execution_count
        else:
            successful = int(template.success_rate * (template.execution_count - 1))
            template.success_rate = successful / template.execution_count
        
        template.last_used = datetime.now().isoformat()
        
        # Persist changes
        return self.update_template(template)
    
    def get_templates_by_success_rate(self, min_rate: float = 0.8) -> List[TaskTemplate]:
        """Get templates with success rate above threshold"""
        return [
            t for t in self._templates.values() 
            if t.success_rate >= min_rate and t.execution_count >= 5
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall template library statistics"""
        templates = list(self._templates.values())
        
        if not templates:
            return {
                "total_templates": 0,
                "total_executions": 0,
                "avg_success_rate": 0.0,
                "most_used": None,
                "best_performing": None
            }
        
        total_executions = sum(t.execution_count for t in templates)
        avg_success = sum(t.success_rate for t in templates) / len(templates)
        
        most_used = max(templates, key=lambda t: t.execution_count)
        best_performing = max(
            [t for t in templates if t.execution_count >= 5],
            key=lambda t: t.success_rate,
            default=None
        )
        
        return {
            "total_templates": len(templates),
            "total_executions": total_executions,
            "avg_success_rate": avg_success,
            "most_used": most_used.id if most_used else None,
            "best_performing": best_performing.id if best_performing else None
        }


# Pre-defined templates for common operations
def get_default_templates() -> List[TaskTemplate]:
    """Get default templates for common Valora operations"""
    return [
        # Navigation template
        TaskTemplate(
            id="navigate_to_location",
            name="Navigate to Location",
            description="Navigate map to a specific location with optional orbit",
            intent_patterns=[r"navigate", r"go to", r"show.*location", r"fly.*to"],
            parameter_schema={
                "type": "object",
                "required": ["location"],
                "properties": {
                    "location": {"type": "string", "description": "Target location"},
                    "zoom": {"type": "integer", "default": 16},
                    "orbit": {"type": "boolean", "default": True}
                },
                "default": {"zoom": 16, "orbit": True}
            },
            task_sequence=[
                TaskSpec(
                    id_template="t1_${location}_geocode",
                    action="geocode",
                    entity="location",
                    task_type="gis_operation",
                    parameters={"location": "${location}"},
                    priority=1
                ),
                TaskSpec(
                    id_template="t2_${location}_flyto",
                    action="flyTo",
                    entity="location",
                    task_type="map_action",
                    parameters={"location": "${location}", "zoom": "${zoom}"},
                    dependencies=["t1_${location}_geocode"],
                    priority=1
                ),
                TaskSpec(
                    id_template="t3_${location}_orbit",
                    action="orbit",
                    entity="location",
                    task_type="map_action",
                    parameters={"center": "${location}", "duration": 5000},
                    dependencies=["t2_${location}_flyto"],
                    priority=2
                )
            ],
            tags=["navigation", "map"]
        ),
        
        # Property search template
        TaskTemplate(
            id="property_search",
            name="Property Search",
            description="Search for properties with filters",
            intent_patterns=[r"property.*search", r"find.*property", r"search.*home", r"house.*in"],
            parameter_schema={
                "type": "object",
                "required": ["location"],
                "properties": {
                    "location": {"type": "string"},
                    "bhk": {"type": "string"},
                    "budget_max": {"type": "number"},
                    "radius": {"type": "integer", "default": 2000}
                },
                "default": {"radius": 2000}
            },
            task_sequence=[
                TaskSpec(
                    id_template="t1_${location}_parse",
                    action="parse",
                    entity="filters",
                    task_type="llm_call",
                    parameters={"bhk": "${bhk}", "budget": "${budget_max}"},
                    priority=1
                ),
                TaskSpec(
                    id_template="t2_${location}_flyto",
                    action="flyTo",
                    entity="location",
                    task_type="map_action",
                    parameters={"location": "${location}", "zoom": 15},
                    priority=1
                ),
                TaskSpec(
                    id_template="t3_${location}_query",
                    action="spatialQuery",
                    entity="property",
                    task_type="gis_operation",
                    parameters={
                        "location": "${location}",
                        "radius": "${radius}",
                        "filters": {"bhk": "${bhk}", "budget_max": "${budget_max}"}
                    },
                    dependencies=["t1_${location}_parse"],
                    priority=1
                ),
                TaskSpec(
                    id_template="t4_${location}_mark",
                    action="markProperties",
                    entity="property",
                    task_type="map_action",
                    parameters={"filter": "query_results"},
                    dependencies=["t2_${location}_flyto", "t3_${location}_query"],
                    priority=1
                )
            ],
            tags=["property", "search"]
        ),
        
        # Area analysis template
        TaskTemplate(
            id="analyze_area",
            name="Area Analysis",
            description="Analyze an area for livability, connectivity, and risk",
            intent_patterns=[r"analyze.*area", r"area.*analysis", r"study.*locality", r"evaluate.*neighborhood"],
            parameter_schema={
                "type": "object",
                "required": ["location"],
                "properties": {
                    "location": {"type": "string"},
                    "metrics": {"type": "array", "default": ["price_trend", "livability", "connectivity", "risk"]}
                },
                "default": {"metrics": ["price_trend", "livability", "connectivity", "risk"]}
            },
            task_sequence=[
                TaskSpec(
                    id_template="t1_${location}_flyto",
                    action="flyTo",
                    entity="area",
                    task_type="map_action",
                    parameters={"location": "${location}", "zoom": 15},
                    priority=1
                ),
                TaskSpec(
                    id_template="t2_${location}_metrics",
                    action="areaMetrics",
                    entity="area",
                    task_type="gis_operation",
                    parameters={"location": "${location}", "metrics": "${metrics}"},
                    priority=1
                ),
                TaskSpec(
                    id_template="t3_${location}_layer",
                    action="addLayer",
                    entity="analytics",
                    task_type="map_action",
                    parameters={"layer": "analytics"},
                    dependencies=["t1_${location}_flyto"],
                    priority=2
                )
            ],
            tags=["analysis", "area"]
        ),
        
        # Comparison template
        TaskTemplate(
            id="compare_areas",
            name="Compare Areas",
            description="Compare two areas across multiple metrics",
            intent_patterns=[r"compare", r"versus", r"vs\.", r"difference.*between"],
            parameter_schema={
                "type": "object",
                "required": ["location_a", "location_b"],
                "properties": {
                    "location_a": {"type": "string"},
                    "location_b": {"type": "string"}
                }
            },
            task_sequence=[
                TaskSpec(
                    id_template="t1_${location_a}_flyto",
                    action="flyTo",
                    entity="area_a",
                    task_type="map_action",
                    parameters={"location": "${location_a}", "zoom": 14},
                    priority=1
                ),
                TaskSpec(
                    id_template="t2_${location_a}_metrics",
                    action="areaMetrics",
                    entity="area_a",
                    task_type="gis_operation",
                    parameters={"location": "${location_a}"},
                    priority=1
                ),
                TaskSpec(
                    id_template="t3_${location_b}_metrics",
                    action="areaMetrics",
                    entity="area_b",
                    task_type="gis_operation",
                    parameters={"location": "${location_b}"},
                    priority=1
                ),
                TaskSpec(
                    id_template="t4_compare",
                    action="compare",
                    entity="areas",
                    task_type="llm_call",
                    parameters={"area_a": "${location_a}", "area_b": "${location_b}"},
                    dependencies=["t2_${location_a}_metrics", "t3_${location_b}_metrics"],
                    priority=2
                )
            ],
            tags=["comparison", "analysis"]
        ),
        
        # Route analysis template
        TaskTemplate(
            id="route_analysis",
            name="Route Analysis",
            description="Analyze route between two locations",
            intent_patterns=[r"route", r"direction", r"how.*to.*reach", r"travel.*from"],
            parameter_schema={
                "type": "object",
                "required": ["from_location", "to_location"],
                "properties": {
                    "from_location": {"type": "string"},
                    "to_location": {"type": "string"},
                    "mode": {"type": "string", "default": "driving"}
                },
                "default": {"mode": "driving"}
            },
            task_sequence=[
                TaskSpec(
                    id_template="t1_${from_location}_geocode",
                    action="geocode",
                    entity="start",
                    task_type="gis_operation",
                    parameters={"location": "${from_location}"},
                    priority=1
                ),
                TaskSpec(
                    id_template="t2_${to_location}_geocode",
                    action="geocode",
                    entity="end",
                    task_type="gis_operation",
                    parameters={"location": "${to_location}"},
                    priority=1
                ),
                TaskSpec(
                    id_template="t3_route",
                    action="routeAnalysis",
                    entity="route",
                    task_type="gis_operation",
                    parameters={"from": "${from_location}", "to": "${to_location}", "mode": "${mode}"},
                    dependencies=["t1_${from_location}_geocode", "t2_${to_location}_geocode"],
                    priority=1
                ),
                TaskSpec(
                    id_template="t4_draw_route",
                    action="drawRoute",
                    entity="route",
                    task_type="map_action",
                    parameters={"from": "${from_location}", "to": "${to_location}"},
                    dependencies=["t3_route"],
                    priority=1
                )
            ],
            tags=["route", "navigation"]
        )
    ]


# Singleton instance
_template_library: Optional[TemplateLibrary] = None

def get_template_library(db_path: str = "valora_templates.db") -> TemplateLibrary:
    """Get or create singleton TemplateLibrary instance"""
    global _template_library
    if _template_library is None:
        _template_library = TemplateLibrary(db_path)
        
        # Add default templates if library is empty
        if len(_template_library._templates) == 0:
            for template in get_default_templates():
                _template_library.add_template(template)
    
    return _template_library
