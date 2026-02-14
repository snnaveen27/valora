"""
Valora AI - Production Tool Registry
Registers real GIS tools that the Agentic Loop can invoke autonomously.
All tools return grounded data from the local database — no hallucination.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger("valora.tools")

ToolCategory = str


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_params: List[str] = field(default_factory=list)
    handler: Optional[Callable] = None
    category: str = "general"

    async def invoke(self, **kwargs) -> Any:
        if self.handler:
            result = self.handler(**kwargs)
            # Support both sync and async handlers
            import asyncio
            if asyncio.iscoroutine(result):
                return await result
            return result
        return {"error": f"Tool '{self.name}' has no handler"}


class ToolRegistry:
    """Production tool registry with real GIS tool handlers.
    Supports dynamic registration, enable/disable, and runtime management."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._disabled: set = set()  # disabled tool names

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool
        logger.info(f"[ToolRegistry] Registered: {tool.name}")

    def unregister(self, name: str) -> bool:
        """Remove a tool at runtime. Returns True if found."""
        if name in self._tools:
            del self._tools[name]
            self._disabled.discard(name)
            logger.info(f"[ToolRegistry] Unregistered: {name}")
            return True
        return False

    def enable_tool(self, name: str) -> bool:
        self._disabled.discard(name)
        return name in self._tools

    def disable_tool(self, name: str) -> bool:
        if name in self._tools:
            self._disabled.add(name)
            return True
        return False

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        if name in self._disabled:
            return None
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return [t for t in self._tools.values() if t.name not in self._disabled]

    def list_all_tools(self) -> List[Dict]:
        """List all tools including disabled ones (for admin panel)."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "required_params": t.required_params,
                "enabled": t.name not in self._disabled,
            }
            for t in self._tools.values()
        ]

    def get_tool_descriptions(self) -> str:
        if not self._tools:
            return "No tools registered."
        lines = []
        for t in self._tools.values():
            if t.name in self._disabled:
                continue
            params_str = ", ".join(t.required_params) if t.required_params else "none"
            lines.append(f"- {t.name}({params_str}): {t.description}")
        return "\n".join(lines)

    def get_tool_schema(self) -> List[Dict]:
        """Return JSON schema for all enabled tools (for LLM function calling)."""
        schemas = []
        for t in self._tools.values():
            if t.name in self._disabled:
                continue
            schemas.append({
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "required": t.required_params,
            })
        return schemas

    def register_dynamic(self, name: str, description: str, handler: Callable,
                         params: Dict = None, required: List[str] = None,
                         category: str = "custom") -> bool:
        """Register a new tool at runtime (for admin panel)."""
        if name in self._tools:
            return False  # already exists
        tool = ToolDefinition(
            name=name, description=description,
            parameters=params or {}, required_params=required or [],
            handler=handler, category=category,
        )
        self.register(tool)
        return True


# ---------------------------------------------------------------------------
# Tool handler implementations — all grounded in real data
# ---------------------------------------------------------------------------

def _get_orchestrator():
    """Lazy import the GIS orchestrator singleton."""
    try:
        from routes.chat_routes import _get_gis_orchestrator
        return _get_gis_orchestrator()
    except Exception:
        return None


def _tool_geocode(location: str, **kwargs) -> Dict:
    """Geocode a location name to coordinates."""
    orch = _get_orchestrator()
    if not orch or not orch.geocoder:
        return {"error": "Geocoder not available"}
    try:
        results = orch.geocoder.search(location, limit=3)
        if not results:
            return {"location": location, "found": False, "results": []}
        return {
            "location": location,
            "found": True,
            "results": [
                {"name": r.get("name", location), "lat": r.get("lat"), "lng": r.get("lng")}
                for r in results[:3]
            ],
        }
    except Exception as e:
        return {"error": str(e)}


def _tool_area_analysis(location: str, lat: float = None, lng: float = None, **kwargs) -> Dict:
    """Analyze an area — POIs, walkability, transport, market data."""
    orch = _get_orchestrator()
    if not orch:
        return {"error": "Orchestrator not available"}

    # Geocode if no coordinates
    if lat is None or lng is None:
        if orch.geocoder:
            results = orch.geocoder.search(location, limit=1)
            if results:
                lat = results[0].get("lat")
                lng = results[0].get("lng")
        if lat is None:
            return {"error": f"Could not geocode '{location}'"}

    analysis = {"location": location, "lat": lat, "lng": lng}

    # Spatial data
    if orch.spatial_service:
        try:
            summary = orch.spatial_service.get_summary(lat, lng, radius_m=1000)
            if isinstance(summary, dict):
                analysis["poi_count"] = summary.get("by_category", {}).get("poi", 0)
                analysis["transport_count"] = summary.get("by_category", {}).get("transport", 0)
                analysis["walkability_score"] = summary.get("walkability_score", 0)
                analysis["accessibility_score"] = summary.get("accessibility_score", 0)
            else:
                analysis["poi_count"] = getattr(summary, "by_category", {}).get("poi", 0)
                analysis["transport_count"] = getattr(summary, "by_category", {}).get("transport", 0)
                analysis["walkability_score"] = getattr(summary, "walkability_score", 0)
                analysis["accessibility_score"] = getattr(summary, "accessibility_score", 0)
        except Exception as e:
            analysis["spatial_error"] = str(e)

    # Market data
    if orch.property_service:
        try:
            from ai.gis_agents import _compute_market_facts
            market = _compute_market_facts(orch.property_service, lat, lng, radius_m=2000)
            analysis.update(market)
        except Exception as e:
            analysis["market_error"] = str(e)

    # Locality knowledge
    try:
        from locality_service import get_locality_state
        state = get_locality_state(location)
        if state:
            analysis["growth_phase"] = state.get("growth_phase")
            analysis["archetype"] = state.get("archetype")
            analysis["risk_level"] = state.get("risk_level")
            analysis["hotspot_score"] = state.get("hotspot_score")
    except Exception:
        pass

    return analysis


def _tool_property_search(location: str, bhk: int = None, budget_max: float = None,
                          property_type: str = None, lat: float = None, lng: float = None, **kwargs) -> Dict:
    """Search properties with filters. Returns grounded listings from DB."""
    orch = _get_orchestrator()
    if not orch or not orch.property_service:
        return {"error": "Property service not available"}

    # Geocode if needed
    if lat is None or lng is None:
        if orch.geocoder:
            results = orch.geocoder.search(location, limit=1)
            if results:
                lat = results[0].get("lat")
                lng = results[0].get("lng")
        if lat is None:
            return {"error": f"Could not geocode '{location}'"}

    try:
        search_kwargs = {"lat": lat, "lng": lng, "radius_m": 2000, "limit": 20}
        if bhk:
            search_kwargs["bhk"] = f"{bhk}BHK"
        if budget_max:
            search_kwargs["max_price"] = int(budget_max)
        if property_type:
            search_kwargs["property_type"] = property_type

        props = orch.property_service.search(**search_kwargs)
        if not props:
            return {"location": location, "count": 0, "properties": []}

        # Format results
        listings = []
        for p in props[:10]:
            listings.append({
                "type": p.get("property_type", p.get("type", "")),
                "bedrooms": p.get("bedrooms", p.get("bhk")),
                "area_sqft": p.get("area_sqft", p.get("super_built_up_area")),
                "price": p.get("price"),
                "price_per_sqft": p.get("price_per_sq_ft", p.get("price_per_sqft")),
                "locality": p.get("locality", location),
                "title": p.get("title", ""),
            })

        return {
            "location": location,
            "count": len(props),
            "showing": len(listings),
            "properties": listings,
        }
    except Exception as e:
        return {"error": str(e)}


def _tool_terrain_analysis(location: str, lat: float = None, lng: float = None, **kwargs) -> Dict:
    """Analyze terrain — elevation, slope, flood risk."""
    orch = _get_orchestrator()
    if not orch:
        return {"error": "Orchestrator not available"}

    if lat is None or lng is None:
        if orch.geocoder:
            results = orch.geocoder.search(location, limit=1)
            if results:
                lat = results[0].get("lat")
                lng = results[0].get("lng")
        if lat is None:
            return {"error": f"Could not geocode '{location}'"}

    if not orch.terrain_service:
        return {"location": location, "lat": lat, "lng": lng, "error": "Terrain service not available"}

    try:
        terrain = orch.terrain_service.get_terrain_analysis(lat, lng)
        return {
            "location": location,
            "lat": lat,
            "lng": lng,
            "elevation_m": terrain.get("elevation_mean") if terrain else None,
            "slope_deg": terrain.get("slope_mean") if terrain else None,
            "flood_risk": terrain.get("flood_risk", "unknown") if terrain else "unknown",
            "suitability": terrain.get("suitability_score") if terrain else None,
        }
    except Exception as e:
        return {"error": str(e)}


async def _tool_comparison(location_a: str, location_b: str, **kwargs) -> Dict:
    """Compare two areas side-by-side using grounded metrics.
    Uses parallel execution for both areas simultaneously."""
    import asyncio
    loop = asyncio.get_event_loop()
    # Run both area analyses concurrently in the thread pool
    result_a, result_b = await asyncio.gather(
        loop.run_in_executor(None, _tool_area_analysis, location_a),
        loop.run_in_executor(None, _tool_area_analysis, location_b),
    )
    return {
        "comparison": {
            "area_a": result_a,
            "area_b": result_b,
        },
        "differences": _compute_differences(result_a, result_b),
    }


def _compute_differences(a: Dict, b: Dict) -> Dict:
    """Compute key differences between two area analyses."""
    diffs = {}
    for key in ["walkability_score", "poi_count", "transport_count", "avg_price_per_sqft", "hotspot_score"]:
        va = a.get(key)
        vb = b.get(key)
        if va is not None and vb is not None:
            try:
                diffs[key] = {"area_a": va, "area_b": vb, "delta": round(float(va) - float(vb), 2)}
            except (TypeError, ValueError):
                pass
    return diffs


def _tool_market_trends(location: str, lat: float = None, lng: float = None, **kwargs) -> Dict:
    """Get market trends and price data for a locality."""
    orch = _get_orchestrator()
    if not orch or not orch.property_service:
        return {"error": "Property service not available"}

    if lat is None or lng is None:
        if orch.geocoder:
            results = orch.geocoder.search(location, limit=1)
            if results:
                lat = results[0].get("lat")
                lng = results[0].get("lng")
        if lat is None:
            return {"error": f"Could not geocode '{location}'"}

    try:
        from ai.gis_agents import _compute_market_facts
        market = _compute_market_facts(orch.property_service, lat, lng, radius_m=2000)
        market["location"] = location
        market["lat"] = lat
        market["lng"] = lng
        return market
    except Exception as e:
        return {"error": str(e)}


def _tool_proactive_suggestions(location: str = None, intent: str = None,
                                 context: Dict = None, **kwargs) -> Dict:
    """Generate context-aware follow-up suggestions based on current state."""
    suggestions = []

    if intent == "navigate" and location:
        suggestions = [
            {"query": f"Analyze {location} for investment", "reason": "Deeper area analysis"},
            {"query": f"Properties in {location} under 1 crore", "reason": "Property search"},
            {"query": f"What is the flood risk in {location}?", "reason": "Terrain safety"},
        ]
    elif intent == "property_search" and location:
        suggestions = [
            {"query": f"Compare {location} with nearby areas", "reason": "Comparative analysis"},
            {"query": f"Price trends in {location}", "reason": "Market trajectory"},
            {"query": f"Is {location} good for investment?", "reason": "Investment potential"},
        ]
    elif intent == "analyze_area" and location:
        suggestions = [
            {"query": f"Find 2BHK in {location}", "reason": "Browse listings"},
            {"query": f"What if a metro opens near {location}?", "reason": "Simulation"},
            {"query": f"Terrain and flood risk in {location}", "reason": "Environmental check"},
        ]
    elif intent == "investment" and location:
        suggestions = [
            {"query": f"Top properties in {location}", "reason": "Actionable picks"},
            {"query": f"Compare {location} vs alternatives", "reason": "Benchmarking"},
            {"query": f"Price trend in {location}", "reason": "Growth trajectory"},
        ]
    elif intent == "simulate" and location:
        suggestions = [
            {"query": f"Current price in {location}", "reason": "Pre-simulation baseline"},
            {"query": f"Infrastructure near {location}", "reason": "Existing connectivity"},
        ]
    else:
        suggestions = [
            {"query": "Show me top investment areas in Bangalore", "reason": "City-wide scan"},
            {"query": "Compare Koramangala vs Indiranagar", "reason": "Popular comparison"},
            {"query": "Find 2BHK under 80 lakhs in Whitefield", "reason": "Popular search"},
        ]

    return {"suggestions": suggestions, "location": location, "intent": intent}


# ---------------------------------------------------------------------------
# Registry singleton with all tools registered
# ---------------------------------------------------------------------------

_registry = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the production tool registry with all GIS tools registered."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()

        _registry.register(ToolDefinition(
            name="geocode",
            description="Convert a location name to lat/lng coordinates. Use when you need coordinates for a place.",
            parameters={"location": {"type": "string", "description": "Place name to geocode"}},
            required_params=["location"],
            handler=_tool_geocode,
            category="spatial",
        ))

        _registry.register(ToolDefinition(
            name="area_analysis",
            description="Comprehensive area analysis — POIs, walkability, transport, market data, locality profile. Use for any area-level question.",
            parameters={
                "location": {"type": "string", "description": "Area/locality name"},
                "lat": {"type": "number", "description": "Latitude (optional)"},
                "lng": {"type": "number", "description": "Longitude (optional)"},
            },
            required_params=["location"],
            handler=_tool_area_analysis,
            category="analysis",
        ))

        _registry.register(ToolDefinition(
            name="property_search",
            description="Search property listings with filters (location, BHK, budget, type). Returns real listings from database.",
            parameters={
                "location": {"type": "string", "description": "Area to search in"},
                "bhk": {"type": "integer", "description": "Number of bedrooms (optional)"},
                "budget_max": {"type": "number", "description": "Max budget in rupees (optional)"},
                "property_type": {"type": "string", "description": "apartment/villa/plot (optional)"},
            },
            required_params=["location"],
            handler=_tool_property_search,
            category="search",
        ))

        _registry.register(ToolDefinition(
            name="terrain_analysis",
            description="Analyze terrain — elevation, slope, flood risk, construction suitability. Use for safety/environmental queries.",
            parameters={
                "location": {"type": "string", "description": "Location name"},
                "lat": {"type": "number", "description": "Latitude (optional)"},
                "lng": {"type": "number", "description": "Longitude (optional)"},
            },
            required_params=["location"],
            handler=_tool_terrain_analysis,
            category="terrain",
        ))

        _registry.register(ToolDefinition(
            name="comparison",
            description="Compare two areas side-by-side on all metrics (price, walkability, transport, growth). Use for 'X vs Y' queries.",
            parameters={
                "location_a": {"type": "string", "description": "First area"},
                "location_b": {"type": "string", "description": "Second area"},
            },
            required_params=["location_a", "location_b"],
            handler=_tool_comparison,
            category="analysis",
        ))

        _registry.register(ToolDefinition(
            name="market_trends",
            description="Get market price data, trends, demand level, and active listings for an area.",
            parameters={
                "location": {"type": "string", "description": "Locality name"},
            },
            required_params=["location"],
            handler=_tool_market_trends,
            category="market",
        ))

        _registry.register(ToolDefinition(
            name="suggest_next",
            description="Generate context-aware follow-up suggestions. Use after answering to propose next steps.",
            parameters={
                "location": {"type": "string", "description": "Current location (optional)"},
                "intent": {"type": "string", "description": "Current intent (optional)"},
            },
            required_params=[],
            handler=_tool_proactive_suggestions,
            category="proactive",
        ))

        logger.info(f"[ToolRegistry] Registered {len(_registry.list_tools())} production tools")

    return _registry
