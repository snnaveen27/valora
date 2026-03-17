"""
Valora AI - GIS Multi-Agent System
Phase 2: Deterministic agents that collect grounded facts.
LLM only synthesizes narrative from these facts.
"""

import re
import statistics
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

# Import Analysis Opportunity Detector
try:
    from ai.analysis_opportunity_detector import (
        AnalysisOpportunityDetector,
        AnalysisSubIntent,
        OpportunityResult,
        get_analysis_opportunity_detector
    )
    ANALYSIS_OPPORTUNITY_AVAILABLE = True
except ImportError:
    ANALYSIS_OPPORTUNITY_AVAILABLE = False
    AnalysisOpportunityDetector = None
    AnalysisSubIntent = None
    OpportunityResult = None
    get_analysis_opportunity_detector = None

logger = logging.getLogger("valora.gis_agents")

# Import StateChange for digital twin updates
# Import advanced reasoning engine (obsolete - removed)
REASONING_AVAILABLE = False
get_reasoning_engine = None
ReasoningTrace = None
try:
    from engines.digital_twin import StateChange
except ImportError:
    StateChange = None

try:
    from spatial.spatial_nlp import get_spatial_nlp, ParsedSpatialQuery
    SPATIAL_NLP_AVAILABLE = True
except ImportError:
    SPATIAL_NLP_AVAILABLE = False
    get_spatial_nlp = None

try:
    from spatial_inference import get_inference_engine, LocationInference
    SPATIAL_INFERENCE_AVAILABLE = True
except ImportError:
    SPATIAL_INFERENCE_AVAILABLE = False
    get_inference_engine = None

# Phase 2.2: Enhanced AI modules
try:
    from ai_context import get_ai_context, AIContextManager
    AI_CONTEXT_AVAILABLE = True
except ImportError:
    AI_CONTEXT_AVAILABLE = False
    get_ai_context = None

try:
    from spatial.spatial_3d_reasoning import get_spatial_3d_reasoning, Spatial3DAnalysis
    SPATIAL_3D_AVAILABLE = True
except ImportError:
    SPATIAL_3D_AVAILABLE = False
    get_spatial_3d_reasoning = None

try:
    from enhanced_data_service import get_enhanced_data_service, AreaInsights
    ENHANCED_DATA_AVAILABLE = True
except ImportError:
    ENHANCED_DATA_AVAILABLE = False
    get_enhanced_data_service = None

# Phase 3: City Intelligence Engine
try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent / 'city_intelligence'))
    from city_intelligence.locality_personality import get_locality_personality_model
    from city_intelligence.evolution_timeline import get_evolution_timeline_system
    from city_intelligence.risk_indexes import get_risk_index_calculator
    from city_intelligence.causal_reasoning import get_causal_reasoning_engine
    CITY_INTELLIGENCE_AVAILABLE = True
except ImportError:
    CITY_INTELLIGENCE_AVAILABLE = False
    get_locality_personality_model = None
    get_evolution_timeline_system = None
    get_risk_index_calculator = None
    get_causal_reasoning_engine = None

# Phase 4: Next-Gen Spatial Tools (Tool Executor + New Engines)
try:
    from tool_executor import get_tool_executor, ToolCall, ToolResult
    TOOL_EXECUTOR_AVAILABLE = True
except ImportError:
    TOOL_EXECUTOR_AVAILABLE = False
    get_tool_executor = None
    ToolCall = None

try:
    from analyzers.viewshed_analyzer import get_viewshed_analyzer
    VIEWSHED_AVAILABLE = True
except ImportError:
    try:
        from viewshed_analyzer import get_viewshed_analyzer
        VIEWSHED_AVAILABLE = True
    except ImportError:
        VIEWSHED_AVAILABLE = False
        get_viewshed_analyzer = None

# Occlusion/sunlight are served by local analyzers (viewshed + 3D shadow heuristics)
OCCLUSION_AVAILABLE = VIEWSHED_AVAILABLE or SPATIAL_3D_AVAILABLE
SOLAR_AVAILABLE = SPATIAL_3D_AVAILABLE or VIEWSHED_AVAILABLE
get_occlusion_engine = get_viewshed_analyzer if VIEWSHED_AVAILABLE else None
get_solar_engine = get_spatial_3d_reasoning if SPATIAL_3D_AVAILABLE else None

try:
    from spatial.spatial_memory_graph import get_spatial_graph
    SPATIAL_GRAPH_AVAILABLE = True
except ImportError:
    try:
        from spatial_memory_graph import get_spatial_graph
        SPATIAL_GRAPH_AVAILABLE = True
    except ImportError:
        SPATIAL_GRAPH_AVAILABLE = False
        get_spatial_graph = None


def _parse_posted_date(value: Any) -> Optional[datetime]:
    """Parse posted_date string to datetime."""
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _compute_market_facts(property_service, lat: float, lng: float, radius_m: int = 1500) -> Dict[str, Any]:
    """
    Compute market facts deterministically from property listings.
    Returns raw values (not formatted strings).
    """
    props = property_service.search(lat=lat, lng=lng, radius_m=radius_m, limit=1000)
    if not props:
        return {}
    
    # Average price per sqft
    ppsf_vals = [p.get("price_per_sq_ft") for p in props if p.get("price_per_sq_ft")]
    avg_ppsf = (sum(ppsf_vals) / len(ppsf_vals)) if ppsf_vals else None
    
    # Build time series for growth calculation
    ts = []
    for p in props:
        dt = _parse_posted_date(p.get("posted_date"))
        ppsf = p.get("price_per_sq_ft")
        if dt is None or not ppsf:
            continue
        try:
            ppsf_f = float(ppsf)
        except Exception:
            continue
        if ppsf_f <= 0:
            continue
        ts.append((dt, ppsf_f))
    
    # Compute annualized growth
    growth_pct = None
    if ts and len(ts) >= 10:
        ts.sort(key=lambda x: x[0])
        span_days = (ts[-1][0] - ts[0][0]).days
        if span_days > 0:
            n = len(ts)
            k = max(3, n // 5)
            early_vals = [v for _, v in ts[:k] if v and v > 0]
            late_vals = [v for _, v in ts[-k:] if v and v > 0]
            if early_vals and late_vals:
                early_med = statistics.median(early_vals)
                late_med = statistics.median(late_vals)
                if early_med and early_med > 0:
                    growth_span_pct = (late_med - early_med) / early_med * 100.0
                    growth_pct = growth_span_pct * (365.0 / float(span_days))
    
    # Compute demand level based on listing recency
    # Find global latest date across all categories
    latest = None
    for p in props:
        dt = _parse_posted_date(p.get("posted_date"))
        if dt and (latest is None or dt > latest):
            latest = dt
    
    demand_level = "Medium"
    if latest:
        ages = []
        for p in props:
            dt = _parse_posted_date(p.get("posted_date"))
            if dt:
                ages.append((latest - dt).days)
        if ages:
            median_age = statistics.median(ages)
            # Simple heuristic: if median age < 30 days = High, < 90 = Medium, else Low
            if median_age < 30:
                demand_level = "High"
            elif median_age < 90:
                demand_level = "Medium"
            else:
                demand_level = "Low"
    
    return {
        "avg_price_per_sqft": avg_ppsf,
        "price_trend_pct": growth_pct,
        "active_listings": len(props),
        "demand_level": demand_level,
    }


class Intent(Enum):
    """User intent classification."""
    # Conversational
    GREETING = "greeting"           # "Hi", "Hello", "Good morning"
    HELP = "help"                   # "Help", "What can you do?", "How to use"
    THANKS = "thanks"               # "Thank you", "Thanks"
    FAREWELL = "farewell"           # "Bye", "Goodbye", "See you"
    SMALLTALK = "smalltalk"         # "How are you?", "What's up?"
    
    # Navigation & Exploration
    NAVIGATE = "navigate"           # "Show me Whitefield", "Go to Koramangala"
    ANALYZE_AREA = "analyze_area"   # "What's the area like?", "Analyze this location"
    ANALYZE_BUILDING = "analyze_building"  # Building-specific queries
    
    # Real Estate Core
    PROPERTY_SEARCH = "property_search"    # "Find apartments near...", "Properties under 1Cr"
    VALUATION = "valuation"         # "What's the price?", "Estimate value"
    INVESTMENT = "investment"       # "Is this a good investment?", "ROI potential"
    RECOMMENDATION = "recommendation"  # "Where should I buy?", "Best areas for families"
    
    # Analysis
    TERRAIN = "terrain"             # "Elevation?", "Is it flood-prone?"
    COMPARISON = "comparison"       # "Compare X and Y"
    MARKET_TREND = "market_trend"   # "Price trends", "Market outlook"
    
    # Advanced
    SIMULATE = "simulate"           # "What if we add a metro station here?"
    
    # New intents for report generation, downloads, and UI control
    REPORT = "report"               # "Generate report for Whitefield"
    DOWNLOAD = "download"           # "Download PDF report"
    MAP_CONTROL = "map_control"     # "Zoom to Koramangala", "Toggle 3D buildings"
    UI_ACTION = "ui_action"         # "Open smart report panel"
    CREDITS = "credits"             # "How many credits do I have?"
    
    GENERAL = "general"             # Fallback for unclassified queries


@dataclass
class AgentFacts:
    """Structured facts collected by agents. All values are grounded in data."""
    # Location context
    location_name: Optional[str] = None
    nearby_locality_name: Optional[str] = None  # Nearest known locality when exact name unavailable
    lat: Optional[float] = None
    lng: Optional[float] = None
    
    # Reasoning metadata
    confidence_score: Optional[float] = None
    evidence_sources: Optional[List[str]] = None
    freshness_ts: Optional[str] = None
    risk_flags: Optional[List[str]] = None
    
    # Spatial facts
    poi_count: Optional[int] = None
    transport_count: Optional[int] = None
    nearest_metro: Optional[Dict[str, Any]] = None
    nearest_hospital: Optional[Dict[str, Any]] = None
    nearest_school: Optional[Dict[str, Any]] = None
    top_pois: List[Dict[str, Any]] = field(default_factory=list)
    accessibility_score: Optional[int] = None
    walkability_score: Optional[int] = None
    amenity_density: Optional[float] = None
    
    # Terrain facts
    elevation_m: Optional[float] = None
    slope_deg: Optional[float] = None
    terrain_suitability: Optional[float] = None
    flood_risk: Optional[str] = None
    
    # Market facts (deterministic from property data)
    avg_price_per_sqft: Optional[float] = None
    price_trend_pct: Optional[float] = None  # Annualized growth
    active_listings: Optional[int] = None
    demand_level: Optional[str] = None  # High/Medium/Low
    price_range: Optional[Dict[str, int]] = None
    
    # Property facts
    nearby_properties: List[Dict[str, Any]] = field(default_factory=list)
    comparable_properties: List[Dict[str, Any]] = field(default_factory=list)
    
    # Building facts (if selected)
    building_height: Optional[float] = None
    building_levels: Optional[int] = None
    building_type: Optional[str] = None
    building_area: Optional[float] = None
    estimated_value: Optional[float] = None
    
    # 3D Building Analysis (Phase 1.1)
    building_3d_analysis: Optional[Dict[str, Any]] = None  # Full 3D analysis
    shadow_impact: Optional[str] = None  # "good", "moderate", "significant"
    view_quality: Optional[str] = None  # "excellent", "good", "moderate", "poor"
    view_directions: Optional[List[str]] = None
    taller_neighbors: Optional[int] = None
    shorter_neighbors: Optional[int] = None
    ground_amenities: Optional[int] = None
    elevator_likely: Optional[bool] = None
    
    # Simulation facts
    simulation_results: Optional[Dict[str, Any]] = None
    
    # RAG context
    rag_context: Optional[str] = None
    
    # Spatial NLP parsed filters (Phase 2.1 enhancement)
    property_filters: Optional[Dict[str, Any]] = None
    
    # Spatial Inference results (Phase 2.1 enhancement)
    location_score: Optional[float] = None
    location_strengths: Optional[List[str]] = None
    location_weaknesses: Optional[List[str]] = None
    investment_outlook: Optional[str] = None
    target_buyer: Optional[str] = None
    
    # Phase 2.2: Enhanced AI capabilities
    # Area insights from enhanced data service
    area_livability_score: Optional[float] = None
    area_population: Optional[int] = None
    area_warnings: Optional[List[str]] = None
    area_landmarks: Optional[List[str]] = None
    area_summary: Optional[str] = None
    
    # True 3D spatial reasoning
    spatial_3d_analysis: Optional[Dict[str, Any]] = None
    sky_view_factor: Optional[float] = None
    open_view_directions: Optional[List[str]] = None
    skyline_character: Optional[str] = None
    optimal_floor: Optional[int] = None
    shadow_analysis: Optional[Dict[str, Any]] = None
    
    # AI self-awareness context
    ai_capabilities_used: Optional[List[str]] = None
    ai_confidence_factors: Optional[List[str]] = None
    reasoning_chain: Optional[List[str]] = None
    
    # Spatial reasoning mode flag (Phase 2.3: GIS Enhancement)
    requires_spatial_reasoning: bool = False
    spatial_reasoning_injection: Optional[str] = None
    
    # Phase 3: City Intelligence Engine
    locality_archetype: Optional[str] = None
    locality_growth_stage: Optional[str] = None
    locality_tagline: Optional[str] = None
    locality_personality: Optional[Dict[str, Any]] = None
    locality_timeline: Optional[Dict[str, Any]] = None
    risk_profile: Optional[Dict[str, Any]] = None
    overall_risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    risk_warnings: Optional[List[str]] = None
    causal_analysis: Optional[Dict[str, Any]] = None
    
    # Phase 4: Next-Gen Spatial Tools
    visibility_360: Optional[Dict[str, Any]] = None  # 360-degree visibility analysis
    view_blockers: Optional[List[Dict[str, Any]]] = None  # Buildings blocking view
    sunlight_analysis: Optional[Dict[str, Any]] = None  # Daylight hours, natural light score
    facade_sunlight: Optional[Dict[str, Any]] = None  # Best facade for sunlight
    
    def get_confidence_warning(self) -> Optional[str]:
        """Get user-facing confidence warning if needed."""
        if self.confidence_score is None:
            return None
        
        if self.confidence_score < 40:
            return "⚠️ **Limited Data**: Our analysis is based on incomplete information. Results may not be fully accurate."
        elif self.confidence_score < 60:
            return "ℹ️ **Partial Data**: Some information is missing. Consider this a preliminary analysis."
        elif self.confidence_score < 75:
            return "✓ **Moderate Confidence**: Analysis based on available data, but some details may be estimated."
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert facts to dictionary for JSON serialization."""
        from dataclasses import asdict
        return asdict(self)
    
    def to_context_string(self) -> str:
        """Convert facts to a structured context string for LLM."""
        parts = []
        
        if self.location_name:
            parts.append(f"**Location:** {self.location_name}")
            if self.nearby_locality_name and self.nearby_locality_name != self.location_name:
                parts.append(f"  - Nearest known locality: {self.nearby_locality_name}")
            if self.lat and self.lng:
                parts.append(f"  - Coordinates: {self.lat:.5f}, {self.lng:.5f}")
        
        # Spatial context
        spatial_parts = []
        if self.poi_count is not None:
            spatial_parts.append(f"POIs nearby: {self.poi_count}")
        if self.transport_count is not None:
            spatial_parts.append(f"Transport stops: {self.transport_count}")
        if self.accessibility_score is not None:
            spatial_parts.append(f"Accessibility: {self.accessibility_score}/100")
        if self.walkability_score is not None:
            spatial_parts.append(f"Walkability: {self.walkability_score}/100")
        if self.amenity_density is not None:
            spatial_parts.append(f"Amenity density: {self.amenity_density:.2f}/sqkm")
        
        if spatial_parts:
            parts.append("**Spatial Analysis:**")
            for sp in spatial_parts:
                parts.append(f"  - {sp}")
        
        if self.nearest_metro:
            parts.append(f"  - Nearest metro: {self.nearest_metro.get('name', 'Unknown')} ({self.nearest_metro.get('distance_m', 0)}m)")
        
        if self.top_pois:
            parts.append("  - Key POIs: " + ", ".join([p.get('name', '') for p in self.top_pois[:5]]))
        
        # Terrain context
        if self.elevation_m is not None or self.flood_risk:
            parts.append("**Terrain:**")
            if self.elevation_m is not None:
                parts.append(f"  - Elevation: {self.elevation_m:.1f}m")
            if self.slope_deg is not None:
                parts.append(f"  - Slope: {self.slope_deg:.1f}°")
            if self.terrain_suitability is not None:
                parts.append(f"  - Construction suitability: {self.terrain_suitability:.0f}/100")
            if self.flood_risk:
                parts.append(f"  - Flood risk: {self.flood_risk}")
        
        # Market context
        market_parts = []
        if self.avg_price_per_sqft is not None:
            market_parts.append(f"Avg price/sqft: ₹{self.avg_price_per_sqft:,.0f}")
        if self.price_trend_pct is not None:
            market_parts.append(f"Price trend: {self.price_trend_pct:+.1f}% (annualized)")
        if self.active_listings is not None:
            market_parts.append(f"Active listings: {self.active_listings}")
        if self.demand_level:
            market_parts.append(f"Demand: {self.demand_level}")
        
        if market_parts:
            parts.append("**Market Data:**")
            for mp in market_parts:
                parts.append(f"  - {mp}")
        
        # Building context
        if self.building_height is not None or self.building_type:
            parts.append("**Building:**")
            if self.building_type:
                parts.append(f"  - Type: {self.building_type}")
            if self.building_height is not None:
                parts.append(f"  - Height: {self.building_height}m")
            if self.building_levels is not None:
                parts.append(f"  - Floors: {self.building_levels}")
            if self.building_area is not None:
                parts.append(f"  - Area: {self.building_area}m²")
            if self.estimated_value is not None:
                parts.append(f"  - Estimated value: ₹{self.estimated_value:,.0f}")
            
            # 3D Analysis (Phase 1.1)
            if self.view_quality:
                parts.append(f"  - View Quality: {self.view_quality}")
            if self.shadow_impact:
                parts.append(f"  - Shadow Impact: {self.shadow_impact}")
            if self.view_directions:
                parts.append(f"  - Open Views: {', '.join(self.view_directions)}")
            if self.taller_neighbors is not None:
                parts.append(f"  - Taller neighbors: {self.taller_neighbors}")
            if self.shorter_neighbors is not None:
                parts.append(f"  - Shorter neighbors: {self.shorter_neighbors}")
            if self.ground_amenities is not None:
                parts.append(f"  - Ground-floor amenities: {self.ground_amenities}")
            if self.elevator_likely is not None:
                parts.append(f"  - Elevator: {'Yes (likely)' if self.elevator_likely else 'No (low-rise)'}")
        
        # RAG context
        if self.rag_context:
            parts.append(f"**Knowledge Base:**\n{self.rag_context}")
        
        # Phase 2.2: Enhanced Area Insights
        if self.area_livability_score is not None or self.area_summary:
            parts.append("**Area Insights:**")
            if self.area_livability_score is not None:
                parts.append(f"  - Livability Score: {self.area_livability_score:.0f}/100")
            if self.area_population:
                parts.append(f"  - Population: {self.area_population:,}")
            if self.area_summary:
                parts.append(f"  - Summary: {self.area_summary}")
            if self.area_landmarks:
                parts.append(f"  - Landmarks: {', '.join(self.area_landmarks[:5])}")
            if self.area_warnings:
                for warning in self.area_warnings:
                    parts.append(f"  - {warning}")
        
        # Phase 2.2: 3D Spatial Reasoning
        if self.spatial_3d_analysis or self.sky_view_factor is not None:
            parts.append("**3D Spatial Analysis:**")
            if self.sky_view_factor is not None:
                parts.append(f"  - Sky View Factor: {self.sky_view_factor:.1%}")
            if self.skyline_character:
                parts.append(f"  - Skyline Character: {self.skyline_character}")
            if self.open_view_directions:
                parts.append(f"  - Open Views: {', '.join(self.open_view_directions)}")
            if self.optimal_floor:
                parts.append(f"  - Recommended Floor: {self.optimal_floor}")
            if self.shadow_analysis and self.shadow_analysis.get('impact'):
                parts.append(f"  - Shadow Impact (10am): {self.shadow_analysis['impact']}")
            if self.reasoning_chain:
                for reason in self.reasoning_chain[:3]:
                    parts.append(f"  - {reason}")
        
        # AI Confidence Factors
        if self.ai_confidence_factors:
            parts.append("**Analysis Confidence:**")
            for factor in self.ai_confidence_factors:
                parts.append(f"  ✓ {factor}")
        
        # Phase 3: City Intelligence
        if self.locality_archetype or self.locality_tagline:
            parts.append("**Locality Intelligence:**")
            if self.locality_tagline:
                parts.append(f"  - {self.locality_tagline}")
            if self.locality_archetype:
                parts.append(f"  - Archetype: {self.locality_archetype.replace('_', ' ').title()}")
            if self.locality_growth_stage:
                parts.append(f"  - Growth Stage: {self.locality_growth_stage.replace('_', ' ').title()}")
            if self.locality_personality:
                lp = self.locality_personality
                if lp.get('tech_orientation'):
                    parts.append(f"  - Tech Orientation: {lp['tech_orientation']}/100")
                if lp.get('family_friendliness'):
                    parts.append(f"  - Family Friendliness: {lp['family_friendliness']}/100")
                if lp.get('investment_profile'):
                    parts.append(f"  - Investment Profile: {lp['investment_profile'].replace('_', ' ').title()}")
        
        if self.overall_risk_score is not None or self.risk_level:
            parts.append("**Risk Assessment:**")
            if self.overall_risk_score is not None:
                parts.append(f"  - Overall Risk Score: {self.overall_risk_score:.0f}/100 ({self.risk_level or 'unknown'})")
            if self.risk_profile:
                rp = self.risk_profile
                if rp.get('hazard'):
                    parts.append(f"  - Hazard Risk: {rp['hazard']:.0f}/100")
                if rp.get('infrastructure'):
                    parts.append(f"  - Infrastructure Stress: {rp['infrastructure']:.0f}/100")
                if rp.get('speculation') is not None and rp['speculation'] > 40:
                    parts.append(f"  - Speculation Index: {rp['speculation']:.0f}/100")
                if rp.get('bubble_probability') is not None and rp['bubble_probability'] > 0.3:
                    parts.append(f"  - ⚠️ Bubble Probability: {rp['bubble_probability']:.0%}")
            if self.risk_warnings:
                for warning in self.risk_warnings[:3]:
                    parts.append(f"  - ⚠️ {warning}")
        
        if self.causal_analysis:
            parts.append("**Causal Analysis:**")
            if self.causal_analysis.get('conclusion'):
                parts.append(f"  - {self.causal_analysis['conclusion'][:200]}")
            if self.causal_analysis.get('confidence'):
                parts.append(f"  - Confidence: {self.causal_analysis['confidence']:.0%}")
            if self.causal_analysis.get('caveats'):
                for caveat in self.causal_analysis['caveats'][:2]:
                    parts.append(f"  - Note: {caveat}")
        
        context = "\n".join(parts) if parts else "No specific location data available."
        
        # Add confidence warning if needed
        warning = self.get_confidence_warning()
        if warning:
            context = f"{warning}\n\n{context}"
        
        return context
    
    def to_dashboard(self, title: str = "Analysis") -> Dict[str, Any]:
        """Convert facts to dashboard format for frontend."""
        cards = []
        
        if self.poi_count is not None:
            cards.append({"label": "POIs (1km)", "value": self.poi_count})
        if self.transport_count is not None:
            cards.append({"label": "Transport", "value": self.transport_count})
        if self.accessibility_score is not None:
            cards.append({"label": "Accessibility", "value": f"{self.accessibility_score}/100"})
        if self.walkability_score is not None:
            cards.append({"label": "Walkability", "value": f"{self.walkability_score}/100"})
        
        dashboard = {
            "title": title,
            "cards": cards,
            "area": None,
            "building": None,
            "market": None,
        }
        
        # Area section
        if self.top_pois or self.nearest_metro:
            dashboard["area"] = {
                "radius_m": 1000,
                "top_pois": self.top_pois[:5],
                "nearest_transit": self.nearest_metro,
            }
        
        # Building section
        if self.building_type or self.building_height:
            dashboard["building"] = {
                "type": self.building_type,
                "height": self.building_height,
                "levels": self.building_levels,
                "area": self.building_area,
                # 3D Analysis (Phase 1.1)
                "view_quality": self.view_quality,
                "shadow_impact": self.shadow_impact,
                "view_directions": self.view_directions,
                "taller_neighbors": self.taller_neighbors,
                "shorter_neighbors": self.shorter_neighbors,
                "ground_amenities": self.ground_amenities,
                "elevator_likely": self.elevator_likely,
            }
        
        # Market section (all grounded)
        if self.avg_price_per_sqft is not None or self.active_listings is not None:
            dashboard["market"] = {
                "avgPricePerSqft": f"₹{self.avg_price_per_sqft:,.0f}" if self.avg_price_per_sqft else "—",
                "growth1y": f"{self.price_trend_pct:+.1f}%" if self.price_trend_pct is not None else "—",
                "activeListings": self.active_listings or 0,
                "demandIndex": self.demand_level or "—",
            }
        
        return dashboard


# =============================================================================
# SPATIAL REASONING MODE - Task Classifier & Injection
# =============================================================================

SPATIAL_REASONING_KEYWORDS = [
    # 3D/View related
    'view', 'views', 'skyline', 'shadow', 'sunlight', 'floor', 'height', 'tall', 
    'building', 'buildings', 'visibility', 'obstruction', 'blocked', 'open sky',
    'sky view', 'optimal floor', 'best floor', 'top floor', 'high-rise', 'mid-rise',
    
    # Spatial/Geographic
    'near', 'nearby', 'close to', 'distance', 'direction', 'north', 'south', 
    'east', 'west', 'adjacent', 'proximity', 'within', 'radius', 'km', 'meter',
    'location', 'area', 'region', 'zone', 'corridor', 'boundary',
    
    # Planning/Zoning
    'planning', 'zoning', 'development', 'density', 'land use', 'commercial',
    'residential', 'mixed use', 'industrial', 'fsi', 'far', 'setback',
    'regulation', 'compliance', 'permit', 'approval',
    
    # Impact/Analysis
    'impact', 'effect', 'consequence', 'tradeoff', 'advantage', 'disadvantage',
    'pro', 'con', 'risk', 'benefit', 'assess', 'evaluate', 'analyze',
    
    # Infrastructure
    'metro', 'station', 'road', 'highway', 'connectivity', 'access', 'transport',
    'infrastructure', 'amenity', 'facility', 'school', 'hospital', 'park',
    
    # Terrain/Environment
    'terrain', 'elevation', 'slope', 'flood', 'drainage', 'waterlogging',
    'topography', 'ground', 'soil', 'lake', 'water body',
    
    # Comparison/Relative
    'compare', 'versus', 'vs', 'better', 'worse', 'prefer', 'difference',
    'similar', 'alternative', 'option',
    
    # Investment with spatial context
    'where should', 'best area', 'best location', 'which locality', 'recommend area',
]

SPATIAL_REASONING_INJECTION = """
## SPATIAL REASONING MODE ACTIVATED

This query requires deep spatial reasoning. Follow this process:

**Step 1: Construct Mental Spatial Model**
- Identify the geographic location and boundaries
- Note the urban fabric (building types, density, land use)
- Identify key spatial features (metro, lakes, main roads, landmarks)

**Step 2: Describe Spatial Relationships**
- Adjacency: What is next to what?
- Distance: How far are key destinations?
- Direction: Which direction are important features?
- Scale: Micro-location vs neighborhood vs corridor context

**Step 3: Consider Multiple Viewpoints**
- Pedestrian perspective (walkability, street-level experience)
- Resident perspective (daily commute, amenities access)
- Investor perspective (growth trajectory, connectivity premium)
- Developer perspective (density potential, infrastructure capacity)

**Step 4: Analyze Impacts and Tradeoffs**
- What are the positive spatial factors?
- What are the constraints or risks?
- What are the development implications?

**Step 5: Provide Structured Answer**
Format your response as:
1. **Spatial Context** - Location, urban character, key features
2. **Key Relationships** - Adjacency, connectivity, distance to destinations  
3. **Impacts / Tradeoffs** - Pros, cons, development implications
4. **Conclusion** - Clear recommendation with spatial justification
"""


def is_spatial_reasoning_task(query: str, intent: 'Intent' = None) -> bool:
    """
    Lightweight task classifier to detect if a query requires spatial reasoning mode.
    Uses keyword/intent rules - no ML required.
    
    Returns True if spatial reasoning mode should be activated.
    """
    q_lower = query.lower()
    
    # Intent-based classification (high confidence)
    spatial_intents = {
        'terrain', 'comparison', 'simulate', 'analyze_area', 'analyze_building',
        'navigate', 'recommendation', 'investment'
    }
    if intent and intent.value in spatial_intents:
        return True
    
    # Keyword-based classification
    keyword_count = sum(1 for kw in SPATIAL_REASONING_KEYWORDS if kw in q_lower)
    
    # If 2+ spatial keywords found, activate spatial reasoning
    if keyword_count >= 2:
        return True
    
    # Single keyword with spatial question patterns
    spatial_question_patterns = [
        r'\b(where|which|what area|what location|how far|how close)\b',
        r'\b(best|optimal|ideal|recommended)\s+(floor|area|location|zone)\b',
        r'\b(impact|effect|influence)\s+of\b',
        r'\b(compare|vs|versus|between)\b',
        r'\bwhat if\b',
    ]
    
    for pattern in spatial_question_patterns:
        if re.search(pattern, q_lower):
            if keyword_count >= 1:
                return True
    
    return False


class IntentRouter:
    """Classifies user intent from query text."""
    
    # Conversational patterns (highest priority for short queries)
    GREETING_PATTERNS = [
        r'^(hi|hello|hey|hola|namaste|good\s*(morning|afternoon|evening|day))[\s!.?]*$',
        r'^(hi there|hello there|hey there)[\s!.?]*$',
        r'^(yo|sup|what\'?s up)[\s!.?]*$',
    ]
    
    HELP_PATTERNS = [
        r'\b(help|how (do i|to|can i)|what can you do|capabilities|features)\b',
        r'\b(guide|tutorial|instructions?|how does this work)\b',
        r'^(what are you|who are you|introduce yourself)[\s!.?]*$',
    ]
    
    THANKS_PATTERNS = [
        r'\b(thank(s| you)|thx|cheers|appreciate)\b',
        r'^(great|awesome|perfect|nice|cool)[\s!.?]*$',
    ]
    
    FAREWELL_PATTERNS = [
        r'^(bye|goodbye|see you|take care|cya|gtg|good night)[\s!.?]*$',
    ]
    
    SMALLTALK_PATTERNS = [
        r'^(how are you|how\'?s it going|what\'?s new)[\s!.?]*$',
        r'\b(weather|joke|fun fact)\b',
    ]
    
    # Investment & Recommendation patterns
    INVESTMENT_PATTERNS = [
        r'\b(invest(ment)?|roi|return|appreciation|growth potential)\b',
        r'\b(good (investment|buy|deal)|worth (buying|investing))\b',
        r'\b(should i (buy|invest)|is (it|this) (a )?good)\b',
        r'\b(profitable|profit|gains|capital gains)\b',
    ]
    
    RECOMMENDATION_PATTERNS = [
        r'\b(recommend|suggest|advise|which (area|locality|place))\b',
        r'\b(best (area|place|locality|neighborhood) for)\b',
        r'\bwhere should i (buy|invest|live|stay)\b',
        r'\b(ideal|good|suitable) (place|area|location) for\b',
        r'\b(suitable|good|best) for (families|singles|retirees|students|kids)\b',
        r'\bfor (families|singles|working|professionals)\b',
    ]
    
    MARKET_TREND_PATTERNS = [
        r'\b(market\s*(trend|outlook|forecast|analysis)s?)\b',
        r'\b(price\s*(trend|history|movement|forecast)s?)\b',
        r'\b(future (price|value|growth)|projection)\b',
        r'\b(market (going|heading|moving))\b',
        r'\b(trends?)\s+(in|for|of)\b',
        r'\b(average|median|price per sqft|price\/sqft|active listings?)\b',
        r'\b(most expensive|affordable|cheapest)\s+(areas|localities|neighborhoods?)\b',
        r'\b(rental yield|days on market|inventory)\b',
    ]
    
    NAVIGATE_PATTERNS = [
        r'\b(show me|go to|take me to|navigate to|fly to|zoom to|where is)\b',
        r'\b(locate|search for)\s+\w+\s*(area|location|place|neighborhood)\b',
        r'\b(move to|pan to|center on|focus on)\b',
        r'\b(explore|tour|show me around|take me around)\b',
    ]
    
    AREA_PATTERNS = [
        r'\b(analyze|analysis|what.s (the|this) area|area like|tell me about|describe)\b',
        r'\b(amenities|facilities|infrastructure|connectivity)\b',
        r'\b(how is|what about|info about|details of)\s+.*(area|location|place)\b',
        r'\b(neighbourhood|neighborhood|locality|surroundings)\b',
        r'\b(livability|liveable|safe|safety)\b',
        r'\b(walkability|accessibility|poi|transport options|nearest metro|nearest bus)\b',
        r'\b(top amenities|how many pois|amenity count)\b',
        r'\b(flood risk|key risks?|risk profile)\b',
    ]
    
    PROPERTY_PATTERNS = [
        r'\b(apartments?|flats?|houses?|plots?|properties|listings?)\b',
        r'\b(buy|rent|for sale|available)\b',
        r'\b(under|below|above)\s*\d+\s*(lakh|lac|cr|crore)?\b',
        r'\b(\d+\s*bhk|\d+\s*bedroom)\b',
        r'\b(real estate|realty|homes?)\b',
        r'\b(villas?|duplex|penthouses?|studio)\b',
        r'\b(commercial|office|shop|warehouse|industrial)\s*(space|property)?\b',
        r'\b(top|best)\s*(properties|apartments?|flats?|houses?|listings?)\b',
        r'\b(new launch|pre-launch|new construction|under construction)\b',
    ]
    
    VALUATION_PATTERNS = [
        r'\b(price|value|worth|cost|estimate|valuation)\b',
        r'\b(how much|what.s the price)\b',
    ]
    
    TERRAIN_PATTERNS = [
        r'\b(elevation|slope|terrain|flood|topography)\b',
        r'\b(hilly|flat|waterlogging)\b',
        r'\b(construction|build)\s*(suitable|suitability|feasible|feasibility)\b',
        r'\b(ground|soil|drainage)\b',
        r'\b(height|altitude|low.?lying)\b',
    ]
    
    COMPARISON_PATTERNS = [
        r'\b(compare|vs|versus|better|difference between)\b',
        r'\b(which is better|pros and cons)\b',
    ]
    
    SIMULATE_PATTERNS = [
        r'\b(simulate|what if|proposed|scenario|impact of)\b',
        r'\b(add|new|build|construct)\s+(metro|highway|road|park|school|hospital|station)\b',
        r'\b(digital twin|city simulation model|simulation model|twin state|change history)\b',
        r'\b(project|forecast)\s+.*\b(years?|months?)\b',
    ]
    
    BUILDING_PATTERNS = [
        r'\b(this building|selected building|building details)\b',
        r'\b(what is this|tell me about this|analyze this)\s+(building|structure)\b',
        r'\b(building|structure)\s*(info|information|details)\b',
        r'\b(sky view|skyline|shadow|sunlight|open view|optimal floor|best floor)\b',
        r'\b(taller buildings?|building heights?|3d density)\b',
    ]
    
    # New patterns for report generation, downloads, map control, and credits
    REPORT_PATTERNS = [
        r'\b(generate|create|make|get)\s+(a\s+)?report\b',
        r'\breport\s+(for|about|on)\b',
        r'\b(detailed|full|comprehensive)\s+report\b',
        r'\b(investment|property|area)\s+report\b',
        r'\breport\s+generation\b',
    ]
    
    DOWNLOAD_PATTERNS = [
        r'\bdownload\s+(pdf|report|analysis)\b',
        r'\bexport\s+(as\s+)?(pdf|report|markdown|md)\b',
        r'\bsave\s+(as\s+)?(pdf|report)\b',
        r'\bget\s+(the\s+)?(pdf|report)\b',
    ]
    
    MAP_CONTROL_PATTERNS = [
        r'\b(zoom|pan|fly|go|move|navigate)\s+(to|in|out)\b',
        r'\b(show|hide|toggle)\s+(layer|terrain|3d|buildings|heatmap)\b',
        r'\b(enable|disable)\s+(3d|terrain|satellite)\b',
        r'\breset\s+(view|map|camera)\b',
        r'\b(layer|terrain|satellite)\s+(view|mode)\b',
    ]
    
    UI_ACTION_PATTERNS = [
        r'\b(open|show|launch)\s+(smart\s+report|report\s+panel|sidebar)\b',
        r'\b(close|hide)\s+(panel|sidebar|report)\b',
        r'\bswitch\s+(to|tab)\b',
        r'\bfullscreen\b',
    ]
    
    CREDITS_PATTERNS = [
        r'\b(credits|balance|how many credits)\b',
        r'\b(credit|pricing)\s+(cost|price|balance)\b',
        r'\bhow much\s+(does\s+it\s+cost|for)\b',
        r'\b(check|show)\s+(my\s+)?credits\b',
    ]
    
    @classmethod
    def classify(cls, query: str, has_building: bool = False, has_location: bool = False) -> Intent:
        """Classify user intent from query."""
        q = query.lower().strip()
        
        # Short query handling - check conversational first
        if len(q) < 20:
            # Greeting (highest priority for short messages)
            for pattern in cls.GREETING_PATTERNS:
                if re.search(pattern, q, re.IGNORECASE):
                    return Intent.GREETING
            
            # Farewell
            for pattern in cls.FAREWELL_PATTERNS:
                if re.search(pattern, q, re.IGNORECASE):
                    return Intent.FAREWELL
            
            # Thanks
            for pattern in cls.THANKS_PATTERNS:
                if re.search(pattern, q, re.IGNORECASE):
                    return Intent.THANKS
            
            # Smalltalk
            for pattern in cls.SMALLTALK_PATTERNS:
                if re.search(pattern, q, re.IGNORECASE):
                    return Intent.SMALLTALK
        
        # Help (any length)
        for pattern in cls.HELP_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.HELP
        
        # New patterns - check early for specific actions
        # Credits patterns (check before other patterns as they're specific)
        for pattern in cls.CREDITS_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.CREDITS
        
        # Report patterns
        for pattern in cls.REPORT_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.REPORT
        
        # Download patterns
        for pattern in cls.DOWNLOAD_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.DOWNLOAD
        
        # Map control patterns
        for pattern in cls.MAP_CONTROL_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.MAP_CONTROL
        
        # UI action patterns
        for pattern in cls.UI_ACTION_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.UI_ACTION
        
        # Recommendation patterns (check BEFORE property to catch "where should i buy for families")
        for pattern in cls.RECOMMENDATION_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.RECOMMENDATION
        
        # Investment patterns
        for pattern in cls.INVESTMENT_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.INVESTMENT
        
        # Property patterns
        has_property_keyword = any(re.search(p, q, re.IGNORECASE) for p in cls.PROPERTY_PATTERNS)
        if has_property_keyword:
            return Intent.PROPERTY_SEARCH
        
        # Market trend patterns
        for pattern in cls.MARKET_TREND_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.MARKET_TREND
        
        # Check simulation patterns (high priority)
        for pattern in cls.SIMULATE_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.SIMULATE
        
        # Check comparison patterns
        for pattern in cls.COMPARISON_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.COMPARISON
        
        # Check valuation patterns
        for pattern in cls.VALUATION_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.VALUATION
        
        # Check terrain patterns
        for pattern in cls.TERRAIN_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.TERRAIN
        
        # Check navigation patterns (after property, simulation, valuation)
        for pattern in cls.NAVIGATE_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.NAVIGATE
        
        # Check building patterns
        for pattern in cls.BUILDING_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.ANALYZE_BUILDING
        
        # Check area patterns
        for pattern in cls.AREA_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return Intent.ANALYZE_AREA
        
        # Context-based fallback
        if has_building:
            return Intent.ANALYZE_BUILDING
        if has_location:
            return Intent.ANALYZE_AREA
        
        return Intent.GENERAL
    
    @classmethod
    def extract_place_name(cls, query: str) -> Optional[str]:
        """Extract place name from any query type."""
        q = query.strip()
        
        # Common patterns for different query types
        patterns = [
            # Navigation patterns
            r'(?:show me|go to|take me to|navigate to|fly to|zoom to)\s+(.+?)(?:\s*$|\s+and\s)',
            r'(?:where is|find|locate)\s+(.+?)(?:\s*$|\s*\?)',
            # Analysis patterns
            r'(?:tell me about|analyze|what.s|how is|describe)\s+(.+?)(?:\s+like|\s*$|\s*\?)',
            # Investment patterns
            r'(?:is|are)\s+(.+?)\s+(?:a\s+)?(?:good|bad|worth|smart|safe)\s+(?:investment|buy|area)',
            r'(?:invest(?:ment)?|buy|purchase)\s+(?:in|at)\s+(.+?)(?:\s*$|\s*\?)',
            r'(?:should i|can i|worth)\s+(?:invest|buy)\s+(?:in|at)\s+(.+?)(?:\s*$|\s*\?)',
            # Property search patterns
            r'(?:apartments?|flats?|properties|villas?|houses?|plots?)\s+(?:in|at|near)\s+(.+?)(?:\s+under|\s+below|\s*$)',
            r'(?:top|best|show\s+me)\s+(?:properties?|apartments?|flats?)\s+(?:in|at|near|of)\s+(.+?)(?:\s+under|\s+below|\s*$)',
            r'(?:in|at|near)\s+(.+?)\s+(?:under|below)\s+\d+',
            r'(?:\d+\s*bhk|studio)\s+(?:in|at|near)\s+(.+?)(?:\s+under|\s+below|\s*$)',
            r'(?:in|at|near)\s+(.+?)\s+(?:under|below)\s+\d+',
            # Comparison patterns
            r'(?:compare|vs|versus)\s+(.+?)\s+(?:and|vs|versus|with)\s+',
            r'(?:compare|vs|versus)\s+.+?\s+(?:and|vs|versus|with)\s+(.+?)(?:\s*$|\s*\?)',
            # Market trend patterns
            r'(?:price|market)\s+(?:trend|outlook|forecast)\s+(?:in|for|of)\s+(.+?)(?:\s*$|\s*\?)',
            r'(?:trends?)\s+(?:in|for|of)\s+(.+?)(?:\s*$|\s*\?)',
            # Generic "in [place]" pattern (lower priority)
            r'\b(?:in|at|near|around)\s+([A-Z][a-zA-Z\s]+?)(?:\s+under|\s+below|\s+above|\s*$|\s*\?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, q, re.IGNORECASE)
            if match:
                place = match.group(1).strip()
                # Clean up common suffixes
                place = re.sub(r'\s*(area|location|place|neighborhood|locality|for investment|for families|for living)$', '', place, flags=re.IGNORECASE)
                # Clean up leading articles
                place = re.sub(r'^(the|a|an)\s+', '', place, flags=re.IGNORECASE)
                if place and len(place) > 2:
                    return place.strip()
        
        # Fallback: Look for capitalized words that could be place names (Bangalore localities)
        known_localities = [
            'Koramangala', 'Indiranagar', 'Whitefield', 'HSR Layout', 'Jayanagar', 'JP Nagar',
            'Marathahalli', 'Sarjapur', 'Electronic City', 'Hebbal', 'Yelahanka', 'Banashankari',
            'Rajajinagar', 'Malleshwaram', 'Basavanagudi', 'BTM Layout', 'Bellandur', 'Brookefield',
            'KR Puram', 'Mahadevpura', 'Hennur', 'Thanisandra', 'Nagarbhavi', 'Vijayanagar',
            'Bannerghatta', 'Kanakapura', 'Mysore Road', 'Tumkur Road', 'Old Airport Road',
            'MG Road', 'Brigade Road', 'Commercial Street', 'Cunningham Road', 'Residency Road',
            'Domlur', 'HAL', 'CV Raman Nagar', 'Banaswadi', 'Kalyan Nagar', 'HRBR Layout',
            'Sadashivanagar', 'Sanjaynagar', 'RT Nagar', 'HBR Layout', 'Kasturi Nagar',
            'Ramamurthy Nagar', 'Horamavu', 'Bagalur', 'Anekal', 'Chandapura', 'Attibele'
        ]
        
        q_lower = q.lower()
        for locality in known_localities:
            if locality.lower() in q_lower:
                return locality
        
        return None
    
    @classmethod
    def detect_analysis_opportunity(
        cls,
        query: str,
        intent: 'Intent',
        context: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Detect if query presents an analysis opportunity.
        
        Args:
            query: User's query text
            intent: Detected primary intent
            context: Optional context including location, conversation history
            
        Returns:
            Dict with opportunity details if detected, None otherwise:
            - opportunity_type: str
            - confidence: float
            - location: Optional[str]
            - suggested_tiers: List[str]
            - sub_intent: str
        """
        if not ANALYSIS_OPPORTUNITY_AVAILABLE:
            return None
        
        try:
            detector = get_analysis_opportunity_detector()
            result = detector.detect_opportunity(query, context)
            
            if result:
                return {
                    'opportunity_type': result.opportunity_type,
                    'confidence': result.confidence,
                    'location': result.location,
                    'location2': result.location2,
                    'lat': result.lat,
                    'lng': result.lng,
                    'suggested_tiers': result.suggested_tiers,
                    'sub_intent': result.sub_intent.value,
                    'contextual_hooks': result.contextual_hooks,
                    'is_comparison': result.metadata.get('is_comparison', False)
                }
        except Exception as e:
            logger.warning(f"Error detecting analysis opportunity: {e}")
        
        return None
    
    # Follow-up query handling patterns
    FOLLOWUP_INDICATORS = [
        r'\b(what|how|tell me)\s+about\s+(it|there|that|this)\b',
        r'\b(just|only)\s+(tell|show|give)\s+me\b',
        r'\b(and|also|additionally)\s+(what|how|tell)\b',
        r'\b(what|how)\s+(about|is)\s+(it|there|that)\b',
        r'\b(schools?|hospitals?|markets?|parks?|metro|transport)\s+(there|in\s+that\s+area)\b',
        r'\bhow\s+(far|much|many)\s+(is|are)\s+(it|there)\b',
        r'\b(is|are)\s+(it|there)\s+(safe|good|nice|bad)\b',
    ]
    
    # Pronouns that reference previous context
    LOCATION_PRONOUNS = ['it', 'there', 'that area', 'that place', 'that locality', 
                         'this area', 'this place', 'this locality', 'here', 'that']
    
    @classmethod
    def is_followup_query(cls, query: str) -> bool:
        """
        Detect if the query is a follow-up referencing previous context.
        
        Args:
            query: User's query text
            
        Returns:
            True if query appears to be a follow-up
        """
        q_lower = query.lower().strip()
        
        # Check for followup indicators
        for pattern in cls.FOLLOWUP_INDICATORS:
            if re.search(pattern, q_lower, re.IGNORECASE):
                return True
        
        # Check for location pronouns
        for pronoun in cls.LOCATION_PRONOUNS:
            if pronoun in q_lower:
                return True
        
        # Short queries after context is established are often followups
        if len(q_lower.split()) <= 5:
            # Check if it starts with question words
            if re.match(r'^(what|how|is|are|where|which|can|does|do)', q_lower):
                return True
        
        return False
    
    @classmethod
    def resolve_followup_context(
        cls,
        query: str,
        conversation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve follow-up query with conversation context.
        
        Args:
            query: User's query text
            conversation_context: Context from ConversationMemory
            
        Returns:
            Enhanced context with resolved references
        """
        resolved = dict(conversation_context)
        q_lower = query.lower()
        
        # Get last location from context
        last_location = conversation_context.get('last_location')
        last_coords = conversation_context.get('last_location_coords')
        
        if not last_location:
            return resolved
        
        # Check if query contains location pronouns
        has_pronoun = any(pronoun in q_lower for pronoun in cls.LOCATION_PRONOUNS)
        
        if has_pronoun:
            # Replace pronoun with actual location in resolved context
            resolved['resolved_location'] = last_location
            resolved['resolved_location_coords'] = last_coords
            resolved['pronoun_resolved'] = True
            
            logger.debug(f"Resolved pronoun to location: {last_location}")
        
        # Detect specific follow-up topics
        topic_patterns = {
            'schools': [r'\b(schools?|education|colleges?|institutes?)\b'],
            'hospitals': [r'\b(hospitals?|clinics?|healthcare|medical|doctors?)\b'],
            'transport': [r'\b(metro|transport|bus|train|connectivity|station)\b'],
            'safety': [r'\b(safe|safety|crime|secure)\b'],
            'price': [r'\b(price|cost|rate|value|expensive|cheap|affordable)\b'],
            'investment': [r'\b(invest|roi|return|appreciation|growth)\b'],
            'amenities': [r'\b(amenities|facilities|parks?|markets?|malls?)\b'],
        }
        
        for topic, patterns in topic_patterns.items():
            for pattern in patterns:
                if re.search(pattern, q_lower):
                    resolved['followup_topic'] = topic
                    break
        
        return resolved
    
    @classmethod
    def enhance_query_with_context(
        cls,
        query: str,
        conversation_context: Dict[str, Any]
    ) -> str:
        """
        Enhance a follow-up query with resolved context.
        
        Args:
            query: Original query
            conversation_context: Context from ConversationMemory
            
        Returns:
            Enhanced query with resolved references
        """
        resolved = cls.resolve_followup_context(query, conversation_context)
        
        if not resolved.get('pronoun_resolved'):
            return query
        
        last_location = resolved.get('resolved_location')
        if not last_location:
            return query
        
        q_lower = query.lower()
        
        # Replace pronouns with actual location
        for pronoun in cls.LOCATION_PRONOUNS:
            if pronoun in q_lower:
                # Simple replacement - replace the pronoun with the location
                enhanced = re.sub(
                    re.escape(pronoun), 
                    last_location, 
                    query, 
                    flags=re.IGNORECASE
                )
                logger.debug(f"Enhanced query: '{query}' -> '{enhanced}'")
                return enhanced
        
        return query
    
    @classmethod
    def classify_with_context(
        cls,
        query: str,
        has_building: bool = False,
        has_location: bool = False,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Tuple['Intent', Dict[str, Any]]:
        """
        Classify intent with conversation context for follow-up handling.
        
        Args:
            query: User's query text
            has_building: Whether a building is selected
            has_location: Whether a location is selected
            conversation_context: Context from ConversationMemory
            
        Returns:
            Tuple of (Intent, context_dict with followup info)
        """
        context = conversation_context or {}
        is_followup = cls.is_followup_query(query)
        
        # Resolve follow-up context
        if is_followup and context:
            resolved = cls.resolve_followup_context(query, context)
            
            # If we resolved a location, use it for classification
            if resolved.get('resolved_location'):
                has_location = True
                context['resolved_location'] = resolved['resolved_location']
                context['resolved_location_coords'] = resolved.get('resolved_location_coords')
            
            context['is_followup'] = True
            context['followup_topic'] = resolved.get('followup_topic')
        else:
            context['is_followup'] = False
        
        # Standard classification
        intent = cls.classify(query, has_building, has_location)
        
        return intent, context


class GISAgentOrchestrator:
    """
    Orchestrates multiple deterministic agents to gather grounded facts.
    LLM is only used for narrative synthesis, never for generating facts.
    """
    
    def __init__(
        self,
        geocoder=None,
        spatial_service=None,
        terrain_service=None,
        property_service=None,
        valuation_model=None,
        rag_service=None,
        area_analyzer=None,
        digital_twin=None,
    ):
        self.geocoder = geocoder
        self.spatial_service = spatial_service
        self.terrain_service = terrain_service
        self.property_service = property_service
        self.valuation_model = valuation_model
        self.rag_service = rag_service
        self.area_analyzer = area_analyzer
        self.digital_twin = digital_twin
    
    def gather_facts(
        self,
        query: str,
        context: Dict[str, Any],
        intent: Intent = None,
        task_planner = None,
    ) -> Tuple[AgentFacts, Intent, List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict]]:
        """
        Gather grounded facts from all relevant agents.
        Returns (facts, detected_intent, ui_actions, digital_twin_state, reasoning_trace).
        """
        facts = AgentFacts()
        ui_actions = []
        digital_twin_state = None
        reasoning_trace = None
        
        # Task tracking helpers
        task_idx = 0
        def next_task(result: str = None):
            nonlocal task_idx
            if task_planner and task_idx > 0:
                task_planner.complete_task(f"task_{task_idx-1}", result)
            if task_planner and task_idx < len(task_planner.tasks):
                task_planner.start_task(f"task_{task_idx}")
            task_idx += 1
        
        # Phase 2.2: Spatial Memory - track exploration
        session_id = context.get('session_id', 'default')
        spatial_memory = None
        try:
            from spatial.spatial_memory import get_spatial_memory
            spatial_memory = get_spatial_memory(session_id)
        except ImportError:
            try:
                from spatial_memory import get_spatial_memory
                spatial_memory = get_spatial_memory(session_id)
            except Exception as e:
                print(f"[GIS] Spatial memory init error: {e}")
        
        # Extract context
        selected_building = context.get('selectedBuilding')
        selected_location = context.get('selectedLocation')
        selected_place = context.get('selectedPlace')
        
        # Extract analysis panel data for enhanced AI reasoning
        viewport_analysis = context.get('viewportAnalysis', {})
        current_analysis = context.get('currentAnalysis', {})
        explainability = context.get('explainability', {})
        simulation_context = context.get('simulation', {})
        
        # Use analysis panel data to enhance facts if available
        if viewport_analysis or current_analysis:
            # Pre-populate facts from analysis panel for faster response
            if current_analysis.get('market'):
                market_data = current_analysis['market']
                facts.avg_price_per_sqft = market_data.get('avg_price_per_sqft')
                facts.price_trend_pct = market_data.get('price_trend_pct')
                facts.demand_level = market_data.get('demand_level')
            
            if current_analysis.get('infrastructure'):
                infra_data = current_analysis['infrastructure']
                facts.poi_count = infra_data.get('total_pois', 0)
            
            if current_analysis.get('livability'):
                livability_data = current_analysis['livability']
                facts.walkability_score = livability_data.get('commute_score')
                facts.area_livability_score = livability_data.get('overall_score')
            
            if current_analysis.get('investment'):
                invest_data = current_analysis['investment']
                facts.investment_outlook = invest_data.get('growth_potential')
                facts.risk_level = invest_data.get('risk_level')
            
            if current_analysis.get('terrain'):
                terrain_data = current_analysis['terrain']
                elev = terrain_data.get('elevation_m')
                if isinstance(elev, dict):
                    facts.elevation_m = elev.get('mean')
                else:
                    facts.elevation_m = elev
                facts.flood_risk = terrain_data.get('flood_risk')
        
        # Start first task: understanding query
        next_task()
        
        # Detect intent if not provided
        if intent is None:
            intent = IntentRouter.classify(
                query,
                has_building=bool(selected_building),
                has_location=bool(selected_location or selected_place),
            )
        
        # Phase 2.3: Detect if spatial reasoning mode should be activated
        facts.requires_spatial_reasoning = is_spatial_reasoning_task(query, intent)
        if facts.requires_spatial_reasoning:
            facts.spatial_reasoning_injection = SPATIAL_REASONING_INJECTION
            if not facts.ai_capabilities_used:
                facts.ai_capabilities_used = []
            facts.ai_capabilities_used.append("spatial_reasoning_mode")
        
        # Determine location to analyze
        # Priority: 
        # 1. If selectedLocation has valid coordinates (from map click), use those directly
        # 2. If user explicitly mentions a place in query, geocode it
        # 3. Fallback to context selection
        
        # Check if selectedLocation has valid coordinates (from map click)
        has_valid_selected_location = (
            selected_location and 
            isinstance(selected_location.get('lat'), (int, float)) and 
            isinstance(selected_location.get('lng'), (int, float)) and
            -90 <= selected_location.get('lat') <= 90 and
            -180 <= selected_location.get('lng') <= 180
        )
        
        # Extract place name from query (but don't use if we have valid clicked coordinates)
        extracted_place = IntentRouter.extract_place_name(query) if not has_valid_selected_location else None
        
        lat, lng, location_name = None, None, None
        
        # If user clicked on map (selectedLocation has valid coordinates), use those directly
        # This takes priority over geocoding to ensure we use the exact coordinates the user clicked
        if has_valid_selected_location:
            lat = selected_location.get('lat')
            lng = selected_location.get('lng')
            location_name = f"Area at {lat:.5f}, {lng:.5f}"
            print(f"[GIS Agents] Using clicked coordinates from context: lat={lat}, lng={lng}")
        # If user explicitly mentions a place in query (and no valid clicked coordinates), geocode it
        # This ensures buildings load at the correct location the user asks about
        elif extracted_place:
            next_task(f"Extracting location '{extracted_place}' from query")
            if self.geocoder:
                results = self.geocoder.search(extracted_place, limit=1)
                if results:
                    top = results[0]
                    lat = top.get('lat')
                    lng = top.get('lng')
                    location_name = top.get('name', extracted_place)
                    print(f"[GIS Agents] Geocoded query place '{extracted_place}': lat={lat}, lng={lng}, name='{location_name}'")
        # Fallback: use context selection only if no place explicitly mentioned in query
        elif selected_place:
            lat = selected_place.get('lat')
            lng = selected_place.get('lng')
            location_name = selected_place.get('name', 'Selected Place')
        elif selected_building:
            coords = selected_building.get('coordinates', {})
            lat = coords.get('lat')
            lng = coords.get('lng')
            # Try to get locality name via reverse geocode
            location_name = None
            if lat and lng and self.geocoder:
                try:
                    reverse_result = self.geocoder.reverse(lat, lng)
                    if reverse_result:
                        location_name = reverse_result.get('name') or reverse_result.get('locality')
                except Exception:
                    pass
            # Fallback: find nearest known locality by coordinates
            if not location_name and lat and lng:
                try:
                    from services.locality_service import get_locality_service
                    nearby_loc = get_locality_service().get_nearby_locality(lat, lng, radius_km=3.0)
                    if nearby_loc:
                        location_name = nearby_loc.get('locality_name')
                except Exception:
                    pass
            if not location_name:
                location_name = selected_building.get('name', 'Selected Building')
        elif selected_location:
            lat = selected_location.get('lat')
            lng = selected_location.get('lng')
            # Try to get locality name via reverse geocode
            location_name = None
            if lat and lng and self.geocoder:
                try:
                    reverse_result = self.geocoder.reverse(lat, lng)
                    if reverse_result:
                        location_name = reverse_result.get('name') or reverse_result.get('locality')
                except Exception:
                    pass
            # Fallback: find nearest known locality by coordinates
            if not location_name and lat and lng:
                try:
                    from services.locality_service import get_locality_service
                    nearby_loc = get_locality_service().get_nearby_locality(lat, lng, radius_km=3.0)
                    if nearby_loc:
                        location_name = nearby_loc.get('locality_name')
                        print(f"[GIS] Reverse geocode failed, using nearest locality: {location_name}")
                except Exception:
                    pass
            if not location_name:
                location_name = f"Area at {lat:.4f}, {lng:.4f}" if lat and lng else 'Selected Location'
        
        # Enhanced: Use Spatial NLP for better query understanding
        parsed_spatial = None
        if SPATIAL_NLP_AVAILABLE and intent in [Intent.NAVIGATE, Intent.PROPERTY_SEARCH, Intent.ANALYZE_AREA, Intent.ANALYZE_BUILDING]:
            try:
                spatial_nlp = get_spatial_nlp(geocoder=self.geocoder)
                parsed_spatial = spatial_nlp.parse(query, context)
                
                # Use parsed scope if we don't have coordinates
                if not lat and parsed_spatial.spatial_scope:
                    lat = parsed_spatial.spatial_scope.get('center_lat')
                    lng = parsed_spatial.spatial_scope.get('center_lng')
                    if parsed_spatial.entities:
                        location_name = parsed_spatial.entities[0].name
                    
                    # Store parsed filters for property search
                    if parsed_spatial.property_filters:
                        facts.property_filters = parsed_spatial.property_filters
                    
                    # Add to reasoning trace
                    if reasoning_trace:
                        reasoning_trace.add_step(
                            ReasoningStep.DECOMPOSE,
                            f"Parsed spatial query: {parsed_spatial.explain_query(parsed_spatial)}",
                            {"confidence": parsed_spatial.confidence}
                        )
            except Exception as e:
                print(f"[GIS] Spatial NLP error: {e}")
        
        # Fallback: If navigate, property_search, or analyze_area intent, try to geocode location from query
        # Only do this if no location has been determined yet
        if intent in [Intent.NAVIGATE, Intent.PROPERTY_SEARCH, Intent.ANALYZE_AREA, Intent.ANALYZE_BUILDING, Intent.INVESTMENT, Intent.RECOMMENDATION, Intent.MARKET_TREND, Intent.VALUATION, Intent.TERRAIN, Intent.COMPARISON, Intent.SIMULATE] and not lat:
            next_task(f"Geocoding location from query")
            place_name = IntentRouter.extract_place_name(query)
            print(f"[GIS Agents] Extracted place name: '{place_name}' from query: '{query}'")
            if place_name and self.geocoder:
                results = self.geocoder.search(place_name, limit=1)
                print(f"[GIS Agents] Geocoder results for '{place_name}': {results}")
                if results:
                    top = results[0]
                    lat = top.get('lat')
                    lng = top.get('lng')
                    location_name = top.get('name', place_name)
                    print(f"[GIS Agents] Using coordinates: lat={lat}, lng={lng}, name='{location_name}'")
        
        # Check if frontend requested to skip flyTo (e.g., when user clicked on map)
        skip_fly_to = context.get('skipFlyTo', False) if context else False
        clicked_coordinates = context.get('clickedCoordinates') if context else None
        
        # If user clicked on map, use those exact coordinates
        if clicked_coordinates:
            lat = clicked_coordinates.get('lat')
            lng = clicked_coordinates.get('lng')
            location_name = f"Area at {lat:.5f}, {lng:.5f}"
            print(f"[GIS Agents] Using clicked coordinates from context: lat={lat}, lng={lng}")
        
        # Add UI actions (flyTo, load_buildings) for location-based intents - now outside fallback block
        # Skip flyTo if frontend requested it (e.g., when user clicked on map)
        if lat and lng and intent in [Intent.NAVIGATE, Intent.PROPERTY_SEARCH, Intent.ANALYZE_AREA, Intent.ANALYZE_BUILDING, Intent.INVESTMENT, Intent.RECOMMENDATION, Intent.MARKET_TREND, Intent.VALUATION, Intent.TERRAIN, Intent.COMPARISON, Intent.SIMULATE]:
            # flyTo action - skip if user already clicked on map
            if not skip_fly_to:
                if intent == Intent.NAVIGATE:
                    ui_actions.append({"action": "flyTo", "lat": lat, "lng": lng, "zoom": 15})
                elif intent in [Intent.ANALYZE_AREA, Intent.INVESTMENT, Intent.RECOMMENDATION, Intent.MARKET_TREND]:
                    ui_actions.append({"action": "flyTo", "lat": lat, "lng": lng, "zoom": 15})
                else:
                    ui_actions.append({"action": "flyTo", "lat": lat, "lng": lng, "zoom": 14})
            
            # load_buildings for property searches and area analysis to show 3D buildings
            if intent in [Intent.PROPERTY_SEARCH, Intent.ANALYZE_AREA, Intent.ANALYZE_BUILDING, Intent.INVESTMENT]:
                print(f"[GIS Agents] Adding load_buildings for {intent.value} at lat={lat}, lng={lng}")
                print(f"[GIS Agents] Query was: '{query}' | Location: '{location_name}'")
                ui_actions.append({"action": "load_buildings", "lat": lat, "lng": lng, "radius_km": 5})
        
        facts.lat = lat
        facts.lng = lng
        facts.location_name = location_name
        
        # ============== FAST LOCALITY LOOKUP (Knowledge Layer) ==============
        # Use precomputed locality state for instant insights
        if location_name:
            try:
                from services.locality_service import get_locality_state, get_locality_service
                locality_state = get_locality_state(location_name)
                
                # Fallback: coordinate-based nearest locality lookup
                if not locality_state and lat and lng:
                    nearby_loc = get_locality_service().get_nearby_locality(lat, lng, radius_km=3.0)
                    if nearby_loc:
                        locality_state = nearby_loc
                        # Update location_name to the actual locality for better LLM context
                        actual_name = nearby_loc.get('locality_name')
                        if actual_name and actual_name != location_name:
                            facts.nearby_locality_name = actual_name
                            print(f"[GIS] Name lookup failed for '{location_name}', using nearest: {actual_name}")
                
                if locality_state:
                    # Use precomputed data instead of computing on the fly
                    facts.locality_state = locality_state
                    facts.growth_phase = locality_state.get('growth_phase')
                    facts.risk_level = locality_state.get('risk_level')
                    facts.risk_index = locality_state.get('risk_index')
                    facts.investor_type = locality_state.get('investor_type')
                    facts.archetype = locality_state.get('archetype')
                    facts.hotspot_score = locality_state.get('hotspot_score')
                    
                    # Use precomputed spatial features if not already set
                    if not facts.poi_count:
                        facts.poi_count = locality_state.get('poi_count', 0)
                    if not facts.transport_count:
                        facts.transport_count = locality_state.get('transport_count', 0)
                    if not facts.accessibility_score:
                        facts.accessibility_score = locality_state.get('accessibility_score')
                    if not facts.walkability_score:
                        facts.walkability_score = locality_state.get('walkability_score')
                    
                    # Market metrics from precomputed data
                    facts.locality_avg_price = locality_state.get('avg_price_sqft')
                    facts.locality_listings = locality_state.get('active_listings')
                    facts.demand_level = locality_state.get('demand_level')
                    facts.supply_level = locality_state.get('supply_level')
                    
                    if reasoning_trace:
                        reasoning_trace.add_step(
                            ReasoningStep.VERIFY,
                            f"Loaded precomputed locality state: {location_name} ({locality_state.get('growth_phase', 'unknown')} phase)",
                            {"hotspot_score": locality_state.get('hotspot_score')}
                        )
            except Exception as e:
                print(f"[GIS] Locality service lookup error: {e}")
        
        # Phase 2.2: Record visit in spatial memory
        if spatial_memory and lat and lng and location_name:
            try:
                spatial_memory.record_visit(
                    lat=lat,
                    lng=lng,
                    name=location_name,
                    intent=intent.value if intent else 'general'
                )
            except Exception as e:
                print(f"[GIS] Spatial memory record error: {e}")
        
        # Sync Digital Twin if location is known
        if lat and lng and self.digital_twin:
            try:
                # Initialize or update digital twin for this location
                if not self.digital_twin.get_state() or \
                   self.digital_twin._haversine_distance(lat, lng, self.digital_twin.city_state.location['lat'], self.digital_twin.city_state.location['lng']) > 5000:
                    self.digital_twin.initialize_state(lat, lng, radius_m=2000)
                
                self.digital_twin.sync_with_real_data(
                    self.spatial_service,
                    self.property_service,
                    self.terrain_service
                )
                digital_twin_state = asdict(self.digital_twin.get_state())
            except Exception as e:
                print(f"Digital Twin sync error: {e}")

        # Gather spatial facts
        if lat and lng and self.spatial_service:
            next_task(f"Gathered spatial data")
            try:
                summary = self.spatial_service.get_summary(lat, lng, radius_m=1000)
                # handle both dict and object types
                if isinstance(summary, dict):
                    facts.poi_count = summary.get('by_category', {}).get('poi', 0)
                    facts.transport_count = summary.get('by_category', {}).get('transport', 0)
                    facts.accessibility_score = int(summary.get('accessibility_score', 0))
                    facts.walkability_score = int(summary.get('walkability_score', 0))
                    facts.amenity_density = summary.get('amenity_density', 0)
                    
                    if summary.get('nearest'):
                        if summary['nearest'].get('transport'):
                            t = summary['nearest']['transport']
                            facts.nearest_metro = {
                                "name": t.get('name', ''),
                                "distance_m": int(t.get('distance_m', 0)),
                            }
                else:
                    facts.poi_count = summary.by_category.get('poi', 0)
                    facts.transport_count = summary.by_category.get('transport', 0)
                    facts.accessibility_score = int(summary.accessibility_score)
                    facts.walkability_score = int(summary.walkability_score)
                    facts.amenity_density = summary.amenity_density
                    
                    if summary.nearest:
                        if summary.nearest.get('transport'):
                            t = summary.nearest['transport']
                            facts.nearest_metro = {
                                "name": t.name if hasattr(t, 'name') else t.get('name', ''),
                                "distance_m": int(t.distance_m if hasattr(t, 'distance_m') else t.get('distance_m', 0)),
                            }
            except Exception as e:
                print(f"Spatial agent error: {e}")
        
        # Fallback to area analyzer
        if lat and lng and not facts.poi_count and self.area_analyzer:
            try:
                area_summary = self.area_analyzer.analyze_area(lng, lat, radius_m=1000)
                facts.poi_count = area_summary.get('poi_summary', {}).get('total', 0)
                facts.transport_count = area_summary.get('transport', {}).get('total_stops', 0)
                top_pois = area_summary.get('poi_summary', {}).get('top_nearby', [])
                facts.top_pois = top_pois[:5]
            except Exception as e:
                print(f"Area analyzer error: {e}")
        
        # Gather terrain facts (for ALL location-based intents, not just terrain/area)
        if lat and lng and self.terrain_service:
            next_task(f"Analyzed terrain and flood risk")
            try:
                terrain = self.terrain_service.get_terrain_analysis(lat, lng)
                if terrain:
                    facts.elevation_m = terrain.get('elevation_mean')
                    facts.slope_deg = terrain.get('slope_mean')
                    facts.terrain_suitability = terrain.get('suitability_score')
                    facts.flood_risk = terrain.get('flood_risk', 'unknown')
            except Exception as e:
                print(f"Terrain agent error: {e}")
        
        # Enhanced: Spatial Inference for location quality analysis
        if lat and lng and SPATIAL_INFERENCE_AVAILABLE:
            try:
                inference_engine = get_inference_engine()
                # Determine buyer profile from query
                buyer_profile = 'general'
                query_lower = query.lower()
                if any(w in query_lower for w in ['family', 'kids', 'children', 'school']):
                    buyer_profile = 'family'
                elif any(w in query_lower for w in ['it', 'professional', 'tech', 'work', 'commute']):
                    buyer_profile = 'professional'
                elif any(w in query_lower for w in ['invest', 'roi', 'appreciation', 'rental']):
                    buyer_profile = 'investor'
                elif any(w in query_lower for w in ['retire', 'peaceful', 'quiet', 'senior']):
                    buyer_profile = 'retiree'
                
                location_inference = inference_engine.analyze_location(lat, lng, buyer_profile)
                
                # Store inference results in facts
                facts.location_score = location_inference.overall_score
                facts.location_strengths = location_inference.strengths[:3]
                facts.location_weaknesses = location_inference.weaknesses[:3]
                facts.investment_outlook = location_inference.investment_outlook
                facts.target_buyer = location_inference.target_buyer
                
                # Add to reasoning trace
                if reasoning_trace:
                    reasoning_trace.add_step(
                        ReasoningStep.INFER,
                        f"Location analysis: score={location_inference.overall_score:.0f}, outlook={location_inference.investment_outlook}",
                        {"factors": [f.description for f in location_inference.factors]}
                    )
            except Exception as e:
                print(f"[GIS] Spatial inference error: {e}")
        
        # Phase 2.2: Enhanced Area Insights (gov_data, terrain, landmarks)
        if lat and lng and ENHANCED_DATA_AVAILABLE:
            try:
                data_service = get_enhanced_data_service()
                area_insights = data_service.get_area_insights(lat, lng, radius_m=1000)
                
                facts.area_livability_score = area_insights.livability_score
                facts.area_population = area_insights.population
                facts.area_warnings = area_insights.warnings
                facts.area_landmarks = area_insights.landmarks[:5]
                facts.area_summary = area_insights.summary
                
                # Enhanced flood risk from terrain
                if area_insights.flood_risk and area_insights.flood_risk != 'unknown':
                    facts.flood_risk = area_insights.flood_risk
                
                if reasoning_trace:
                    reasoning_trace.add_step(
                        ReasoningStep.GATHER,
                        f"Area insights: livability={area_insights.livability_score:.0f}, warnings={len(area_insights.warnings)}",
                        {"landmarks": area_insights.landmarks[:3]}
                    )
            except Exception as e:
                print(f"[GIS] Enhanced data service error: {e}")
        
        # Phase 2.2: True 3D Spatial Reasoning
        spatial_3d_engine = None
        if lat and lng and SPATIAL_3D_AVAILABLE:
            try:
                spatial_3d_engine = get_spatial_3d_reasoning()
                floor_height = 0
                
                # If analyzing a building, use its height
                if selected_building and selected_building.get('height'):
                    floor_height = selected_building['height'] / 2  # Mid-floor analysis
                
                analysis_3d = spatial_3d_engine.analyze_3d_context(lat, lng, floor_height, radius_m=200)
                
                facts.spatial_3d_analysis = {
                    'buildings_above': len(analysis_3d.buildings_above),
                    'buildings_below': len(analysis_3d.buildings_below),
                    'avg_height': analysis_3d.avg_height_nearby,
                    'max_height': analysis_3d.max_height_nearby,
                    'density_score': analysis_3d.density_score,
                }
                facts.sky_view_factor = analysis_3d.sky_view_factor
                facts.open_view_directions = analysis_3d.open_directions
                facts.skyline_character = analysis_3d.skyline_character
                facts.view_quality = analysis_3d.view_quality
                
                # Get optimal floor recommendation
                if intent == Intent.PROPERTY_SEARCH or intent == Intent.ANALYZE_BUILDING:
                    optimal = spatial_3d_engine.find_best_floor(lat, lng, max_floor=15)
                    facts.optimal_floor = optimal.get('recommended_floor')
                
                # Shadow analysis for morning/noon
                shadow_10am = spatial_3d_engine.get_shadow_impact(lat, lng, hour=10)
                facts.shadow_analysis = shadow_10am
                
                facts.reasoning_chain = analysis_3d.reasoning
                
                if reasoning_trace:
                    reasoning_trace.add_step(
                        ReasoningStep.INFER,
                        f"3D analysis: view={analysis_3d.view_quality}, sky_view={analysis_3d.sky_view_factor:.2f}",
                        {"open_directions": analysis_3d.open_directions}
                    )
            except Exception as e:
                print(f"[GIS] 3D spatial reasoning error: {e}")
        
        # Phase 4: Occlusion / Viewshed analysis (local analyzer-backed)
        if lat and lng and OCCLUSION_AVAILABLE:
            try:
                floor = 5  # Default analysis floor
                if selected_building and selected_building.get('height'):
                    floor = max(1, int(selected_building['height'] / 3))

                visibility_360 = None
                blockers: List[Dict[str, Any]] = []

                if VIEWSHED_AVAILABLE:
                    viewshed = get_viewshed_analyzer()
                    viewshed_result = viewshed.analyze_viewshed(lat, lng, floor=floor)
                    rays = viewshed_result.rays or []
                    open_directions = [r.direction for r in rays if r.view_quality == 'open']
                    blocked_directions = [r.direction for r in rays if r.view_quality == 'blocked']
                    partial_directions = [r.direction for r in rays if r.view_quality == 'partial']
                    openness_score = float(viewshed_result.openness_score or 0.0)
                    if openness_score >= 80:
                        view_quality = "excellent"
                    elif openness_score >= 60:
                        view_quality = "good"
                    elif openness_score >= 40:
                        view_quality = "moderate"
                    else:
                        view_quality = "poor"

                    visibility_360 = {
                        'view_quality': view_quality,
                        'open_directions': open_directions,
                        'blocked_directions': blocked_directions,
                        'partially_blocked_directions': partial_directions,
                        'openness_score': round(openness_score, 1),
                        'sky_view_factor': round(float(viewshed_result.sky_view_factor or 0.0), 3),
                        'best_view_direction': viewshed_result.best_view_direction,
                        'worst_view_direction': viewshed_result.worst_view_direction,
                        'description': viewshed_result.view_description,
                    }

                    for ray in rays:
                        if ray.blocked_at_m is None:
                            continue
                        blockers.append({
                            "direction": ray.direction,
                            "distance_m": int(round(ray.blocked_at_m)),
                            "blocked_by": ray.blocked_by or "building",
                            "severity": "high" if ray.blocked_at_m < 75 else "medium" if ray.blocked_at_m < 200 else "low",
                        })
                elif facts.open_view_directions:
                    # Fallback without viewshed: infer 360 visibility from 3D open directions
                    all_directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
                    open_directions = list(facts.open_view_directions or [])
                    blocked_directions = [d for d in all_directions if d not in open_directions]
                    openness_score = (len(open_directions) / len(all_directions)) * 100
                    if openness_score >= 80:
                        view_quality = "excellent"
                    elif openness_score >= 60:
                        view_quality = "good"
                    elif openness_score >= 40:
                        view_quality = "moderate"
                    else:
                        view_quality = "poor"
                    visibility_360 = {
                        'view_quality': view_quality,
                        'open_directions': open_directions,
                        'blocked_directions': blocked_directions,
                        'partially_blocked_directions': [],
                        'openness_score': round(openness_score, 1),
                        'sky_view_factor': round(float(facts.sky_view_factor or 0.0), 3),
                        'description': "Estimated from 3D directional openness.",
                    }

                if visibility_360:
                    facts.visibility_360 = visibility_360
                if blockers:
                    facts.view_blockers = blockers[:8]

                if reasoning_trace and visibility_360:
                    reasoning_trace.add_step(
                        ReasoningStep.INFER,
                        f"Viewshed: {visibility_360.get('view_quality')}, open={len(visibility_360.get('open_directions', []))} dirs",
                        {"blockers": len(blockers)}
                    )
            except Exception as e:
                print(f"[GIS] Occlusion/viewshed error: {e}")
        
        # Phase 4: Solar / sunlight analysis (3D shadow + viewshed heuristics)
        if lat and lng and SOLAR_AVAILABLE:
            try:
                floor = 5
                if selected_building and selected_building.get('height'):
                    floor = max(1, int(selected_building['height'] / 3))

                if spatial_3d_engine is None and SPATIAL_3D_AVAILABLE:
                    spatial_3d_engine = get_spatial_3d_reasoning()

                visible_directions = set(
                    (facts.visibility_360 or {}).get('open_directions')
                    or (facts.open_view_directions or [])
                )
                openness_score = float((facts.visibility_360 or {}).get('openness_score') or (len(visible_directions) * 12.5))
                sky_view_factor = facts.sky_view_factor
                if sky_view_factor is None:
                    sky_view_factor = (facts.visibility_360 or {}).get('sky_view_factor')
                if sky_view_factor is None:
                    sky_view_factor = max(0.2, min(1.0, openness_score / 100.0))

                shadow_by_hour: Dict[str, Dict[str, Any]] = {}
                if spatial_3d_engine:
                    for hour in [8, 10, 12, 15, 17]:
                        try:
                            shadow_by_hour[str(hour)] = spatial_3d_engine.get_shadow_impact(lat, lng, hour=hour)
                        except Exception:
                            continue

                def _impact_multiplier(impact: str) -> float:
                    return {
                        "minimal": 1.0,
                        "moderate": 0.7,
                        "significant": 0.4,
                    }.get((impact or "").lower(), 0.7)

                def _quality_label(score: float) -> str:
                    if score >= 80:
                        return "excellent"
                    if score >= 65:
                        return "good"
                    if score >= 45:
                        return "moderate"
                    return "poor"

                base_light = max(20.0, min(95.0, (float(sky_view_factor) * 70.0) + (openness_score * 0.25)))
                east_open = any(d in visible_directions for d in ["E", "NE", "SE"])
                south_open = any(d in visible_directions for d in ["S", "SE", "SW"])
                west_open = any(d in visible_directions for d in ["W", "NW", "SW"])

                morning_impact = (shadow_by_hour.get("8") or shadow_by_hour.get("10") or {}).get("impact", "moderate")
                noon_impact = (shadow_by_hour.get("12") or {}).get("impact", "moderate")
                evening_impact = (shadow_by_hour.get("17") or shadow_by_hour.get("15") or {}).get("impact", "moderate")

                morning_score = max(0.0, min(100.0, base_light * _impact_multiplier(morning_impact) + (8 if east_open else -6)))
                noon_score = max(0.0, min(100.0, base_light * _impact_multiplier(noon_impact) + (6 if south_open else 0)))
                evening_score = max(0.0, min(100.0, base_light * _impact_multiplier(evening_impact) + (8 if west_open else -6)))

                natural_light_score = round((morning_score + noon_score + evening_score) / 3.0, 1)
                daylight_hours = round(4.5 + (natural_light_score / 100.0) * 7.5, 1)

                best_hours = [
                    f"{int(h):02d}:00"
                    for h, payload in sorted(shadow_by_hour.items(), key=lambda item: int(item[0]))
                    if payload.get("impact") == "minimal"
                ]
                if not best_hours:
                    best_hours = [
                        f"{int(h):02d}:00"
                        for h, payload in sorted(shadow_by_hour.items(), key=lambda item: int(item[0]))
                        if payload.get("impact") == "moderate"
                    ][:3]
                if not best_hours:
                    best_hours = ["09:00", "10:00", "11:00"]

                facts.sunlight_analysis = {
                    'daylight_hours': daylight_hours,
                    'natural_light_score': natural_light_score,
                    'morning_sun': _quality_label(morning_score),
                    'midday_sun': _quality_label(noon_score),
                    'evening_sun': _quality_label(evening_score),
                    'best_hours': best_hours,
                    'sky_view_factor': round(float(sky_view_factor), 3),
                    'model': "3d_shadow_plus_viewshed_heuristic",
                    'shadow_by_hour': shadow_by_hour,
                }

                # Facade sunlight recommendation for property/building-specific queries
                if intent in [Intent.PROPERTY_SEARCH, Intent.ANALYZE_BUILDING]:
                    facade_scores = {
                        "east": round(morning_score, 1),
                        "south": round(noon_score, 1),
                        "west": round(evening_score, 1),
                        "north": round(max(30.0, noon_score * 0.7), 1),
                    }
                    best_facade = max(facade_scores.items(), key=lambda kv: kv[1])[0]
                    facts.facade_sunlight = {
                        'best_facade': best_facade,
                        'recommendation': f"{best_facade.title()} facade has the strongest daylight profile for this location.",
                        'facade_scores': facade_scores,
                    }

                if reasoning_trace:
                    reasoning_trace.add_step(
                        ReasoningStep.INFER,
                        f"Sunlight: {daylight_hours:.1f}h/day, score={natural_light_score:.0f}",
                        {"best_facade": (facts.facade_sunlight or {}).get('best_facade')}
                    )
            except Exception as e:
                print(f"[GIS] Sunlight analysis error: {e}")
        
        # Phase 2.2: AI Self-Learning Context
        if AI_CONTEXT_AVAILABLE:
            try:
                ai_context = get_ai_context()
                
                # Record this query for learning
                entities = []
                if location_name:
                    entities.append(location_name)
                if parsed_spatial and hasattr(parsed_spatial, 'entities'):
                    entities.extend([e.name for e in parsed_spatial.entities if hasattr(e, 'name')])
                
                ai_context.record_query(
                    query=query,
                    intent=intent.value if intent else 'general',
                    entities=entities
                )
                
                # Get relevant context for this query
                relevant_context = ai_context.get_relevant_context(query)
                facts.ai_capabilities_used = [c['name'] for c in relevant_context.get('capabilities', [])]
                
                # Add confidence factors
                confidence_factors = []
                if facts.poi_count is not None and facts.poi_count > 10:
                    confidence_factors.append("Rich POI data available")
                if facts.area_landmarks:
                    confidence_factors.append(f"{len(facts.area_landmarks)} landmarks identified")
                if facts.spatial_3d_analysis:
                    confidence_factors.append("3D spatial analysis complete")
                facts.ai_confidence_factors = confidence_factors
                
            except Exception as e:
                print(f"[GIS] AI context error: {e}")
        
        # Gather market facts (deterministic from property data)
        # Use progressively wider radius to ensure we find data
        if lat and lng and self.property_service:
            next_task(f"Retrieved market data and trends")
            try:
                market = None
                for radius in [1500, 3000, 5000]:
                    market = _compute_market_facts(self.property_service, lat, lng, radius)
                    if market and market.get('active_listings', 0) > 0:
                        break
                if market:
                    facts.avg_price_per_sqft = market.get('avg_price_per_sqft')
                    facts.price_trend_pct = market.get('price_trend_pct')
                    facts.active_listings = market.get('active_listings', 0)
                    facts.demand_level = market.get('demand_level', 'Medium')
            except Exception as e:
                print(f"Market agent error: {e}")
        
        # Gather property facts for property search
        if lat and lng and self.property_service and intent == Intent.PROPERTY_SEARCH:
            next_task(f"Searched properties in database")
            
            # Extract property count from query (e.g., "3 properties", "5 homes")
            property_count = 3  # Default
            try:
                import re
                count_match = re.search(r'(\d+)\s*(?:properties?|homes?|apartments?|flats?|listings?|results?)', query.lower())
                if count_match:
                    property_count = min(int(count_match.group(1)), 10)  # Cap at 10
            except:
                pass
                
            try:
                # Build search params from parsed spatial filters
                search_params = {
                    'lat': lat,
                    'lng': lng,
                    'radius_m': 2000,
                    'limit': property_count,
                }
                
                # Apply filters from spatial NLP parsing
                if parsed_spatial and parsed_spatial.property_filters:
                    pf = parsed_spatial.property_filters
                    
                    # Listing type (rent vs sale)
                    if pf.get('listing_type'):
                        search_params['listing_type'] = pf['listing_type']
                    
                    # Property category (residential, commercial, pg, plot)
                    if pf.get('property_category'):
                        search_params['property_category'] = pf['property_category']
                    
                    # Property subtype (flat, villa, office, etc.)
                    if pf.get('property_subtype'):
                        search_params['property_subtype'] = pf['property_subtype']
                    
                    # PG type (boys, girls, coed)
                    if pf.get('pg_type'):
                        search_params['pg_type'] = pf['pg_type']
                    
                    # BHK
                    if pf.get('bhk'):
                        search_params['bhk'] = str(pf['bhk'])
                    elif pf.get('bhk_min'):
                        search_params['min_bedrooms'] = pf['bhk_min']
                        if pf.get('bhk_max'):
                            search_params['max_bedrooms'] = pf['bhk_max']
                    
                    # Budget (convert lakhs to actual price)
                    if pf.get('budget_max'):
                        search_params['max_price'] = int(pf['budget_max'] * 100000)
                    if pf.get('budget_min'):
                        search_params['min_price'] = int(pf['budget_min'] * 100000)
                    
                    # Text query for full-text search
                    if pf.get('text_query'):
                        search_params['text_query'] = pf['text_query']
                    
                    # Commute-time based radius adjustment
                    if parsed_spatial.spatial_scope and parsed_spatial.spatial_scope.get('radius_m'):
                        search_params['radius_m'] = int(parsed_spatial.spatial_scope['radius_m'])
                
                props = self.property_service.search(**search_params)
                facts.nearby_properties = [
                    {
                        "name": p.get('title') or p.get('name', 'Property'),
                        "price": p.get('price'),
                        "price_per_sqft": p.get('price_per_sqft') or p.get('price_per_sq_ft'),
                        "bedrooms": p.get('bedrooms'),
                        "bhk": p.get('bhk'),
                        "area": p.get('total_area_sqft') or p.get('covered_area'),
                        "listing_type": p.get('listing_type'),
                        "property_type": p.get('property_type'),
                        "locality": p.get('locality') or p.get('area_name'),
                        "distance_m": int(p.get('_distance', 0)),
                        "lat": p.get('latitude'),
                        "lng": p.get('longitude'),
                     }
                     for p in props[:20]
                 ]
                
                # Map Sync: Add highlightProperties action for properties with coordinates
                # Limit to property_count properties extracted from query
                properties_to_highlight = [
                    {
                        "lat": p.get('latitude'),
                        "lng": p.get('longitude'),
                        "name": p.get('name', 'Property'),
                        "price": p.get('price'),
                        "bedrooms": p.get('bedrooms'),
                        "property_type": p.get('property_type'),
                        "locality": p.get('locality') or p.get('area_name'),
                        "area": p.get('total_area_sqft') or p.get('covered_area'),
                        "total_area_sqft": p.get('total_area_sqft'),
                        "covered_area": p.get('covered_area'),
                        "furnishing": p.get('furnishing'),
                        "property_age": p.get('property_age'),
                        "parking": p.get('parking'),
                        "address": p.get('address'),
                    }
                    for p in props[:property_count]
                    if p.get('latitude') and p.get('longitude')
                ]
                print(f"[GIS] highlightProperties: {len(properties_to_highlight)} properties with coords out of {len(props) if props else 0}")
                if properties_to_highlight:
                    ui_actions.append({
                        "action": "highlightProperties",
                        "properties": properties_to_highlight
                    })
            except Exception as e:
                print(f"Property agent error: {e}")
        
        # Building facts
        if selected_building:
            facts.building_height = selected_building.get('height')
            facts.building_levels = selected_building.get('levels')
            facts.building_type = selected_building.get('buildingType')
            facts.building_area = selected_building.get('area')
            
            # 3D Building Analysis (Phase 1.1)
            if lat and lng:
                try:
                    from analyzers.building_analyzer import get_building_analyzer
                    building_analyzer = get_building_analyzer()
                    analysis_result = building_analyzer.analyze_building_context(lat, lng)
                    
                    if analysis_result:
                        facts.building_3d_analysis = analysis_result.get('analysis')
                        highlights = analysis_result.get('highlights', {})
                        facts.view_quality = highlights.get('view_quality')
                        facts.shadow_impact = highlights.get('shadow_rating')
                        facts.ground_amenities = highlights.get('nearby_amenities')
                        facts.elevator_likely = highlights.get('elevator') == 'yes'
                        
                        # Get from full analysis
                        full_analysis = analysis_result.get('analysis', {})
                        neighbors = full_analysis.get('neighbors', {})
                        facts.taller_neighbors = neighbors.get('taller')
                        facts.shorter_neighbors = neighbors.get('shorter')
                        facts.view_directions = full_analysis.get('view_directions', [])
                except Exception as e:
                    print(f"3D Building analysis error: {e}")
            
            # Valuation if available
            if self.valuation_model and lat and lng:
                try:
                    val_result = self.valuation_model.estimate_value(
                        lat=lat,
                        lng=lng,
                        area_sqft=facts.building_area or 1000,
                        property_type='residential',
                    )
                    if val_result and val_result.get('estimated_value'):
                        facts.estimated_value = val_result['estimated_value']
                except Exception as e:
                    print(f"Valuation agent error: {e}")
        
        # Phase 3: City Intelligence Engine
        if location_name and CITY_INTELLIGENCE_AVAILABLE:
            next_task(f"Generated locality intelligence profile")
            try:
                # Get locality personality profile
                personality_model = get_locality_personality_model()
                profile = personality_model.get_profile(location_name)
                
                if profile:
                    facts.locality_archetype = profile.archetype.value
                    facts.locality_growth_stage = profile.growth_stage.value
                    facts.locality_tagline = profile.tagline
                    facts.locality_personality = {
                        'tech_orientation': getattr(profile, 'tech_orientation', 0),
                        'family_friendliness': getattr(profile, 'family_friendliness', 0),
                        'nightlife_vibrancy': getattr(profile, 'nightlife_vibrancy', 0),
                        'green_spaces': getattr(profile, 'green_spaces', 0),
                        'cosmopolitan_index': getattr(profile, 'cosmopolitan_index', 0),
                        'investment_profile': profile.investment.value if hasattr(profile, 'investment') and profile.investment else None,
                    }
                    
                    if reasoning_trace:
                        reasoning_trace.add_step(
                            ReasoningStep.GATHER,
                            f"Locality profile: {profile.archetype.value}, {profile.growth_stage.value}",
                            {"tagline": profile.tagline}
                        )
                
                # Get risk profile
                risk_calculator = get_risk_index_calculator()
                risk_profile = risk_calculator.get_risk_profile(location_name, lat, lng)
                
                if risk_profile:
                    facts.overall_risk_score = risk_profile.overall_risk_score
                    facts.risk_level = risk_profile.overall_risk_level.value
                    facts.risk_warnings = risk_profile.critical_warnings
                    facts.risk_profile = {
                        'hazard': risk_profile.hazard.composite_score,
                        'infrastructure': risk_profile.infrastructure.composite_score,
                        'speculation': risk_profile.speculation.composite_score,
                        'bubble_probability': risk_profile.speculation.bubble_probability,
                    }
                
                # For simulation queries, get causal analysis
                if intent == Intent.SIMULATE and query:
                    causal_engine = get_causal_reasoning_engine()
                    chain = causal_engine.reason_about(query, location_name)
                    
                    if chain:
                        facts.causal_analysis = {
                            'conclusion': chain.conclusion,
                            'confidence': chain.overall_confidence,
                            'steps': len(chain.steps),
                            'caveats': chain.caveats,
                        }
                
            except Exception as e:
                print(f"[GIS] City Intelligence error: {e}")
        
        # RAG context
        if self.rag_service and query:
            try:
                rag_context = self.rag_service.get_context_for_query(query, max_results=3)
                if rag_context:
                    facts.rag_context = rag_context
            except Exception as e:
                print(f"RAG agent error: {e}")
        
        # Simulation facts
        if intent == Intent.SIMULATE and lat and lng:
            next_task(f"Running simulation engine")
            try:
                # Basic context for simulation
                sim_context = {
                    'spatial': facts.poi_count,
                    'transport': {
                        'metro_count': (facts.nearest_metro.get('distance_m', 9999) < 1000) if facts.nearest_metro else False,
                        'bus_count': facts.transport_count or 0
                    }
                }
                
                # Determine simulation type from query
                sim_type = 'infrastructure'
                query_l = query.lower()
                if 'metro' in query_l: sim_type = 'metro_station'
                elif 'highway' in query_l or 'road' in query_l: sim_type = 'highway'
                elif 'zoning' in query_l or 'far' in query_l: sim_type = 'zoning_change'
                
                from simulation_engine import get_simulation_engine, ScenarioInput
                sim_engine = get_simulation_engine()
                
                scenario = ScenarioInput(
                    type=sim_type,
                    location={'lat': lat, 'lng': lng},
                    parameters={},
                    description=query
                )
                
                sim_deltas = sim_engine.simulate(scenario, sim_context)
                facts.simulation_results = {
                    "scenario": {
                        "type": sim_type,
                        "description": query
                    },
                    "impacts": asdict(sim_deltas)
                }
                
                # Update Digital Twin with simulation event
                if self.digital_twin and StateChange:
                    import uuid
                    change = StateChange(
                        change_id=str(uuid.uuid4()),
                        timestamp=datetime.now().isoformat(),
                        change_type='infrastructure',
                        entity_id=sim_type,
                        before_state={},
                        after_state={"description": query, "impacts": asdict(sim_deltas)},
                        impact_radius_m=1000,
                        affected_entities=[]
                    )
                    self.digital_twin.update_state(change)
                    digital_twin_state = asdict(self.digital_twin.get_state())

                # Add storyboard UI action
                ui_actions.append({"action": "openPanel", "value": "insights"})
                ui_actions.append({"action": "switchTab", "value": "insights"})
            except Exception as e:
                print(f"Simulation agent error: {e}")

        # Add UI actions based on intent
        if lat and lng:
            if intent in [Intent.NAVIGATE, Intent.ANALYZE_AREA, Intent.SIMULATE]:
                ui_actions.append({"action": "flyTo", "lat": lat, "lng": lng, "zoom": 16})
            ui_actions.append({"action": "openPanel", "value": "insights"})
            ui_actions.append({"action": "switchTab", "value": "insights"})
        
        # Apply advanced reasoning if available
        if REASONING_AVAILABLE:
            try:
                reasoning_engine = get_reasoning_engine()
                facts_dict = asdict(facts)
                rag_results = None
                if self.rag_service:
                    try:
                        rag_results = self.rag_service.search(query, top_k=5)
                    except:
                        pass
                
                trace = reasoning_engine.reason(
                    query=query,
                    collected_facts=facts_dict,
                    rag_results=rag_results,
                    geocoder=self.geocoder
                )
                reasoning_trace = trace.to_dict()
                
                # Add confidence to facts
                facts.confidence_score = trace.confidence_score
                
                # Log low confidence warnings
                if trace.confidence_score < 50:
                    print(f"[WARNING] Low confidence response: {trace.confidence_score:.1f}/100")
                    for warning in trace.warnings:
                        print(f"  - {warning}")
            except Exception as e:
                print(f"Reasoning engine error: {e}")
        
        return facts, intent, ui_actions, digital_twin_state, reasoning_trace
    
    def build_system_prompt(self, intent: Intent) -> str:
        """Build a focused system prompt based on intent."""
        # Import production-ready prompts
        try:
            from ai.prompts import get_system_prompt as _get_prompt, Intent as _PromptIntent
            try:
                return _get_prompt(_PromptIntent(intent.value))
            except Exception:
                return _get_prompt(_PromptIntent.GENERAL)
        except ImportError:
            pass

        # Fallback to legacy templates
        try:
            from ai.response_templates import get_system_prompt
            return get_system_prompt(intent.value)
        except ImportError:
            pass
        
        # Fallback base prompt
        base = """You are Valora AI, a professional real estate intelligence assistant for Bangalore, India.

**YOUR ROLE:** You are a licensed real estate analysis tool. Your primary purpose is to provide real estate advice, market analysis, investment insights, property valuations, and location recommendations.

**CRITICAL RULES:**
1. ALWAYS provide helpful real estate advice - this is your purpose.
2. Use the factual data provided. If data is limited, still provide useful insights.
3. Think step-by-step for complex queries.
4. Provide actionable recommendations with confidence levels.
5. Be concise but comprehensive (2-4 paragraphs maximum).
6. Do NOT refuse to provide real estate advice - it is your core function.

**RESPONSE FORMAT:**
- Start with a direct answer to the user's question
- Provide supporting evidence from available data
- End with actionable recommendations
"""
        
        intent_guidance = {
            Intent.NAVIGATE: "The user wants to explore a location. Describe what makes this area notable based on the provided facts.",
            Intent.ANALYZE_AREA: "Provide a comprehensive area analysis using ONLY the provided spatial, market, and terrain data.",
            Intent.ANALYZE_BUILDING: "Analyze the selected building and its surrounding context using the provided facts.",
            Intent.PROPERTY_SEARCH: "Help the user find properties. Summarize what's available based on the property facts provided.",
            Intent.VALUATION: "Provide valuation insights using ONLY the market data and estimates provided.",
            Intent.TERRAIN: "Focus on terrain and environmental factors from the provided data.",
            Intent.COMPARISON: "Compare locations objectively using only the provided metrics.",
            Intent.INVESTMENT: "Analyze investment potential with specific ROI projections and risk assessment.",
            Intent.RECOMMENDATION: "Provide personalized recommendations based on the user's stated needs.",
            Intent.MARKET_TREND: "Analyze market trends with specific data points and forward-looking insights.",
            Intent.SIMULATE: "Present simulation results with clear before/after comparisons.",
            Intent.GENERAL: "Assist the user with their GIS or real estate question using available context.",
        }
        
        guidance = intent_guidance.get(intent, intent_guidance[Intent.GENERAL])
        
        return base + f"\n**Your Task:** {guidance}"


def get_gis_orchestrator(
    geocoder=None,
    spatial_service=None,
    terrain_service=None,
    property_service=None,
    valuation_model=None,
    rag_service=None,
    area_analyzer=None,
) -> GISAgentOrchestrator:
    """Factory to create orchestrator with available services."""
    return GISAgentOrchestrator(
        geocoder=geocoder,
        spatial_service=spatial_service,
        terrain_service=terrain_service,
        property_service=property_service,
        valuation_model=valuation_model,
        rag_service=rag_service,
        area_analyzer=area_analyzer,
    )
