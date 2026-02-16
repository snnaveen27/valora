"""
Valora AI - Tool Executor & Validator
Validates LLM tool calls against schema and dispatches to appropriate services.

This module enables reliable LLM-directed tool calling by:
1. Validating parameters against JSON schema
2. Dispatching to the correct service
3. Returning structured results
4. Enforcing offline-only constraints
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from functools import lru_cache


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    tool_name: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolCall:
    """Represents a tool call request from LLM."""
    name: str
    parameters: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'ToolCall':
        return cls(name=d.get('name', ''), parameters=d.get('parameters', {}))


class ToolValidator:
    """Validates tool calls against the schema."""
    
    def __init__(self, schema_path: str = None):
        if schema_path is None:
            schema_path = Path(__file__).parent / 'spatial_tools_schema.json'
        self.schema_path = Path(schema_path)
        self._schema = None
        self._tools_by_name = {}
        self._load_schema()
    
    def _load_schema(self):
        """Load and index the tool schema."""
        try:
            with open(self.schema_path, 'r') as f:
                self._schema = json.load(f)
            
            # Index tools by name
            for tool in self._schema.get('tools', []):
                self._tools_by_name[tool['name']] = tool
            
            print(f"[ToolValidator] Loaded {len(self._tools_by_name)} tools from schema")
        except Exception as e:
            print(f"[ToolValidator] Error loading schema: {e}")
            self._schema = {'tools': [], 'constraints': {}}
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific tool."""
        return self._tools_by_name.get(tool_name)
    
    def list_tools(self, category: str = None) -> List[Dict[str, Any]]:
        """List available tools, optionally filtered by category."""
        tools = self._schema.get('tools', [])
        if category:
            tools = [t for t in tools if t.get('category') == category]
        return tools
    
    def validate_call(self, tool_call: ToolCall) -> Tuple[bool, Optional[str]]:
        """
        Validate a tool call against the schema.
        
        Returns:
            (is_valid, error_message)
        """
        tool_schema = self.get_tool_schema(tool_call.name)
        
        if not tool_schema:
            return False, f"Unknown tool: {tool_call.name}"
        
        params_schema = tool_schema.get('parameters', {})
        required = params_schema.get('required', [])
        properties = params_schema.get('properties', {})
        
        # Check required parameters
        for req in required:
            if req not in tool_call.parameters:
                return False, f"Missing required parameter: {req}"
        
        # Validate parameter types
        for param_name, param_value in tool_call.parameters.items():
            if param_name not in properties:
                # Allow extra params but warn
                continue
            
            expected_type = properties[param_name].get('type')
            if expected_type:
                if not self._check_type(param_value, expected_type):
                    return False, f"Invalid type for {param_name}: expected {expected_type}"
            
            # Check enum constraints
            if 'enum' in properties[param_name]:
                if param_value not in properties[param_name]['enum']:
                    allowed = ', '.join(properties[param_name]['enum'])
                    return False, f"Invalid value for {param_name}: must be one of [{allowed}]"
        
        return True, None
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected JSON schema type."""
        type_map = {
            'string': str,
            'number': (int, float),
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict
        }
        expected = type_map.get(expected_type)
        if expected is None:
            return True  # Unknown type, allow
        return isinstance(value, expected)
    
    def get_constraints(self) -> Dict[str, Any]:
        """Get global constraints from schema."""
        return self._schema.get('constraints', {})


class ToolExecutor:
    """
    Executes validated tool calls by dispatching to appropriate services.
    All tools are OFFLINE-ONLY.
    """
    
    def __init__(self):
        self.validator = ToolValidator()
        self._services = {}
        self._init_services()
    
    def _init_services(self):
        """Lazy-initialize services on first use."""
        pass  # Services are initialized on demand
    
    def _get_spatial_3d(self):
        """Get spatial 3D reasoning service."""
        if 'spatial_3d' not in self._services:
            try:
                from spatial.spatial_3d_reasoning import get_spatial_3d_reasoning
                self._services['spatial_3d'] = get_spatial_3d_reasoning()
            except ImportError:
                from backend.spatial.spatial_3d_reasoning import get_spatial_3d_reasoning
                self._services['spatial_3d'] = get_spatial_3d_reasoning()
        return self._services['spatial_3d']
    
    def _get_viewshed(self):
        """Get viewshed analyzer service."""
        if 'viewshed' not in self._services:
            try:
                from analyzers.viewshed_analyzer import get_viewshed_analyzer
                self._services['viewshed'] = get_viewshed_analyzer()
            except ImportError:
                from backend.analyzers.viewshed_analyzer import get_viewshed_analyzer
                self._services['viewshed'] = get_viewshed_analyzer()
        return self._services['viewshed']
    
    def _get_building_analyzer(self):
        """Get building analyzer service."""
        if 'building' not in self._services:
            try:
                from analyzers.building_analyzer import get_building_analyzer
                self._services['building'] = get_building_analyzer()
            except ImportError:
                from backend.analyzers.building_analyzer import get_building_analyzer
                self._services['building'] = get_building_analyzer()
        return self._services['building']
    
    def _get_property_service(self):
        """Get property service."""
        if 'property' not in self._services:
            try:
                from services.property_service import PropertyService
                self._services['property'] = PropertyService()
            except ImportError:
                from backend.services.property_service import PropertyService
                self._services['property'] = PropertyService()
        return self._services['property']
    
    def _get_locality_service(self):
        """Get locality service."""
        if 'locality' not in self._services:
            try:
                from services.locality_service import get_locality_service
                self._services['locality'] = get_locality_service()
            except ImportError:
                from backend.services.locality_service import get_locality_service
                self._services['locality'] = get_locality_service()
        return self._services['locality']
    
    def _get_simulation_engine(self):
        """Get simulation engine."""
        if 'simulation' not in self._services:
            try:
                from simulation_engine import SimulationEngine
                self._services['simulation'] = SimulationEngine()
            except ImportError:
                from backend.simulation_engine import SimulationEngine
                self._services['simulation'] = SimulationEngine()
        return self._services['simulation']
    
    def execute(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a tool call after validation.
        
        Args:
            tool_call: The tool call to execute
            
        Returns:
            ToolResult with success status and data/error
        """
        import time
        start = time.time()
        
        # Validate first
        is_valid, error = self.validator.validate_call(tool_call)
        if not is_valid:
            return ToolResult(
                success=False,
                tool_name=tool_call.name,
                error=error
            )
        
        # Dispatch to appropriate handler
        try:
            result_data = self._dispatch(tool_call)
            elapsed = (time.time() - start) * 1000
            
            return ToolResult(
                success=True,
                tool_name=tool_call.name,
                data=result_data,
                execution_time_ms=elapsed
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return ToolResult(
                success=False,
                tool_name=tool_call.name,
                error=str(e),
                execution_time_ms=elapsed
            )
    
    def _dispatch(self, tool_call: ToolCall) -> Dict[str, Any]:
        """Dispatch tool call to the appropriate service."""
        name = tool_call.name
        params = tool_call.parameters
        
        # 3D Spatial Tools
        if name == 'get_3d_context':
            svc = self._get_spatial_3d()
            result = svc.analyze_3d_context(
                lat=params['lat'],
                lng=params['lng'],
                floor_height=params.get('floor_height_m', 0),
                radius_m=params.get('radius_m', 200)
            )
            return {
                'buildings_above': result.buildings_above,
                'buildings_below': result.buildings_below,
                'buildings_at_level': result.buildings_at_level,
                'sky_view_factor': result.sky_view_factor,
                'open_directions': result.open_directions,
                'view_quality': result.view_quality,
                'skyline_character': result.skyline_character,
                'avg_height_nearby': result.avg_height_nearby,
                'max_height_nearby': result.max_height_nearby,
                'density_score': result.density_score,
                'reasoning': result.reasoning
            }
        
        elif name == 'analyze_viewshed':
            svc = self._get_viewshed()
            result = svc.analyze_viewshed(
                lat=params['lat'],
                lng=params['lng'],
                floor=params.get('floor', 1),
                building_height=params.get('building_height_m')
            )
            return result.to_dict()
        
        elif name == 'compare_floors':
            svc = self._get_viewshed()
            result = svc.compare_floors(
                lat=params['lat'],
                lng=params['lng'],
                floors=params.get('floors', [1, 5, 10, 15, 20])
            )
            return result
        
        elif name == 'get_shadow_impact':
            svc = self._get_spatial_3d()
            result = svc.get_shadow_impact(
                lat=params['lat'],
                lng=params['lng'],
                hour=params.get('hour', 10)
            )
            return result
        
        elif name == 'find_best_floor':
            svc = self._get_spatial_3d()
            result = svc.find_best_floor(
                lat=params['lat'],
                lng=params['lng'],
                max_floor=params.get('max_floor', 20)
            )
            return result
        
        elif name == 'analyze_building':
            svc = self._get_building_analyzer()
            result = svc.analyze_building(
                lat=params['lat'],
                lng=params['lng'],
                height=params.get('height_m'),
                building_type=params.get('building_type'),
                building_id=params.get('building_id')
            )
            return result.to_dict()
        
        # Real Estate Tools
        elif name == 'search_properties':
            svc = self._get_property_service()
            results = svc.search(
                lat=params.get('lat'),
                lng=params.get('lng'),
                radius_m=params.get('radius_m', 2000),
                listing_type=params.get('listing_type'),
                property_category=params.get('property_category'),
                property_subtype=params.get('property_subtype'),
                pg_type=params.get('pg_type'),
                bhk=params.get('bhk'),
                min_price=params.get('min_price'),
                max_price=params.get('max_price'),
                locality=params.get('locality'),
                text_query=params.get('text_query'),
                limit=params.get('limit', 50)
            )
            return {
                'properties': results,
                'count': len(results),
                'filters_applied': {k: v for k, v in params.items() if v is not None}
            }
        
        elif name == 'get_locality_profile':
            svc = self._get_locality_service()
            result = svc.get_locality_state(
                locality_name=params['locality_name'],
                city_id=params.get('city_id', 'BLR')
            )
            return result or {'error': 'Locality not found'}
        
        elif name == 'get_nearby_locality':
            svc = self._get_locality_service()
            result = svc.get_nearby_locality(
                lat=params['lat'],
                lng=params['lng'],
                radius_km=params.get('radius_km', 2.0)
            )
            return result or {'error': 'No locality found nearby'}
        
        # Simulation Tools
        elif name == 'simulate_infrastructure':
            svc = self._get_simulation_engine()
            result = svc.simulate(
                infrastructure_type=params['infrastructure_type'],
                lat=params['lat'],
                lng=params['lng'],
                name=params.get('name', 'New Infrastructure'),
                radius_m=params.get('radius_m', 2000)
            )
            return result
        
        # UI Command
        elif name == 'ui_command':
            # UI commands are returned as-is for frontend handling
            return {
                'action': params['action'],
                'payload': params.get('payload', {}),
                'success': True
            }
        
        else:
            raise ValueError(f"No handler for tool: {name}")
    
    def execute_batch(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute multiple tool calls."""
        constraints = self.validator.get_constraints()
        max_tools = constraints.get('max_tools_per_turn', 5)
        
        if len(tool_calls) > max_tools:
            return [ToolResult(
                success=False,
                tool_name='batch',
                error=f"Too many tool calls: {len(tool_calls)} > {max_tools}"
            )]
        
        return [self.execute(tc) for tc in tool_calls]
    
    def get_tools_for_llm(self) -> str:
        """
        Get a formatted string of available tools for LLM context.
        This helps the LLM understand what tools are available.
        """
        tools = self.validator.list_tools()
        
        lines = ["# Available Tools (OFFLINE ONLY)\n"]
        
        for tool in tools:
            lines.append(f"## {tool['name']}")
            lines.append(f"**Category:** {tool.get('category', 'general')}")
            lines.append(f"**Description:** {tool['description']}")
            
            params = tool.get('parameters', {}).get('properties', {})
            required = tool.get('parameters', {}).get('required', [])
            
            if params:
                lines.append("**Parameters:**")
                for pname, pschema in params.items():
                    req = "(required)" if pname in required else "(optional)"
                    ptype = pschema.get('type', 'any')
                    desc = pschema.get('description', '')
                    lines.append(f"  - `{pname}` ({ptype}) {req}: {desc}")
            
            lines.append("")
        
        return "\n".join(lines)


# Singleton instance
_tool_executor = None


def get_tool_executor() -> ToolExecutor:
    """Get or create the tool executor singleton."""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor


def execute_tool(name: str, **params) -> ToolResult:
    """Convenience function to execute a tool by name."""
    executor = get_tool_executor()
    tool_call = ToolCall(name=name, parameters=params)
    return executor.execute(tool_call)
