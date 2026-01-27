"""
Valora AI - GIS Multi-Agent System
Phase 2: Deterministic agents that collect grounded facts.
LLM only synthesizes narrative from these facts.
"""

import re
import statistics
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

# Import StateChange for digital twin updates
# Import advanced reasoning engine
try:
    from advanced_reasoning import get_reasoning_engine, ReasoningTrace
    REASONING_AVAILABLE = True
except ImportError:
    REASONING_AVAILABLE = False
    get_reasoning_engine = None
    ReasoningTrace = None
try:
    from digital_twin import StateChange
except ImportError:
    StateChange = None

try:
    from spatial_nlp import get_spatial_nlp, ParsedSpatialQuery
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
    from spatial_3d_reasoning import get_spatial_3d_reasoning, Spatial3DAnalysis
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
    NAVIGATE = "navigate"           # "Show me Whitefield", "Go to Koramangala"
    ANALYZE_AREA = "analyze_area"   # "What's the area like?", "Analyze this location"
    ANALYZE_BUILDING = "analyze_building"  # Building-specific queries
    PROPERTY_SEARCH = "property_search"    # "Find apartments near...", "Properties under 1Cr"
    VALUATION = "valuation"         # "What's the price?", "Estimate value"
    TERRAIN = "terrain"             # "Elevation?", "Is it flood-prone?"
    COMPARISON = "comparison"       # "Compare X and Y"
    SIMULATE = "simulate"           # "What if we add a metro station here?"
    GENERAL = "general"             # General questions, greetings


@dataclass
class AgentFacts:
    """Structured facts collected by agents. All values are grounded in data."""
    # Location context
    location_name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    
    # Reasoning metadata
    confidence_score: Optional[float] = None
    
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
    
    def to_context_string(self) -> str:
        """Convert facts to a structured context string for LLM."""
        parts = []
        
        if self.location_name:
            parts.append(f"**Location:** {self.location_name}")
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


class IntentRouter:
    """Classifies user intent from query text."""
    
    NAVIGATE_PATTERNS = [
        r'\b(show me|go to|take me to|navigate to|fly to|zoom to|where is)\b',
        r'\b(locate|search for)\s+\w+\s*(area|location|place|neighborhood)\b',
        r'\b(move to|pan to|center on|focus on)\b',
    ]
    
    AREA_PATTERNS = [
        r'\b(analyze|analysis|what.s (the|this) area|area like|tell me about|describe)\b',
        r'\b(amenities|facilities|infrastructure|connectivity)\b',
        r'\b(how is|what about|info about|details of)\s+.*(area|location|place)\b',
        r'\b(neighbourhood|neighborhood|locality|surroundings)\b',
        r'\b(livability|liveable|safe|safety)\b',
    ]
    
    PROPERTY_PATTERNS = [
        r'\b(apartments?|flats?|houses?|plots?|properties|listings?)\b',
        r'\b(buy|rent|for sale|available)\b',
        r'\b(under|below|above)\s*\d+\s*(lakh|lac|cr|crore)?\b',
        r'\b(\d+\s*bhk|\d+\s*bedroom)\b',
        r'\b(real estate|realty|homes?)\b',
        r'\b(villa|duplex|penthouse|studio)\b',
        r'\b(commercial|office|shop|warehouse|industrial)\s*(space|property)?\b',
        r'\b(top|best|recommend|suggest)\s*(properties|apartments?|flats?|houses?|listings?)?\b',
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
    ]
    
    SIMULATE_PATTERNS = [
        r'\b(simulate|what if|proposed|scenario|impact of)\b',
        r'\b(add|new|build|construct)\s+(metro|highway|road|park|school|hospital|station)\b',
    ]
    
    BUILDING_PATTERNS = [
        r'\b(this building|selected building|building details)\b',
        r'\b(what is this|tell me about this|analyze this)\s+(building|structure)\b',
        r'\b(building|structure)\s*(info|information|details)\b',
    ]
    
    @classmethod
    def classify(cls, query: str, has_building: bool = False, has_location: bool = False) -> Intent:
        """Classify user intent from query."""
        q = query.lower().strip()
        
        # PRIORITY: Check for property keywords FIRST - these should override navigation
        # This allows "show me properties in hebbal" to be PROPERTY_SEARCH, not NAVIGATE
        has_property_keyword = any(re.search(p, q, re.IGNORECASE) for p in cls.PROPERTY_PATTERNS)
        if has_property_keyword:
            return Intent.PROPERTY_SEARCH
        
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
        """Extract place name from navigation query."""
        q = query.strip()
        
        # Common patterns
        patterns = [
            r'(?:show me|go to|take me to|navigate to|fly to|zoom to)\s+(.+?)(?:\s*$|\s+and\s)',
            r'(?:where is|find|locate)\s+(.+?)(?:\s*$|\s*\?)',
            r'(?:tell me about|analyze|what.s)\s+(.+?)(?:\s+like|\s*$|\s*\?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, q, re.IGNORECASE)
            if match:
                place = match.group(1).strip()
                # Clean up common suffixes
                place = re.sub(r'\s*(area|location|place|neighborhood|locality)$', '', place, flags=re.IGNORECASE)
                return place.strip() if place else None
        
        return None


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
            from spatial_memory import get_spatial_memory
            spatial_memory = get_spatial_memory(session_id)
        except Exception as e:
            print(f"[GIS] Spatial memory init error: {e}")
        
        # Extract context
        selected_building = context.get('selectedBuilding')
        selected_location = context.get('selectedLocation')
        selected_place = context.get('selectedPlace')
        
        # Start first task: understanding query
        next_task()
        
        # Detect intent if not provided
        if intent is None:
            intent = IntentRouter.classify(
                query,
                has_building=bool(selected_building),
                has_location=bool(selected_location or selected_place),
            )
        
        # Determine location to analyze
        lat, lng, location_name = None, None, None
        
        if selected_place:
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
            if not location_name:
                location_name = selected_location.get('name', 'Selected Location')
        
        # Enhanced: Use Spatial NLP for better query understanding
        parsed_spatial = None
        if SPATIAL_NLP_AVAILABLE and intent in [Intent.NAVIGATE, Intent.PROPERTY_SEARCH, Intent.ANALYZE_AREA]:
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
        
        # Fallback: If navigate or property_search intent, try to geocode location from query
        if intent in [Intent.NAVIGATE, Intent.PROPERTY_SEARCH] and not lat:
            next_task(f"Geocoded location")
            place_name = IntentRouter.extract_place_name(query)
            if place_name and self.geocoder:
                results = self.geocoder.search(place_name, limit=1)
                if results:
                    top = results[0]
                    lat = top.get('lat')
                    lng = top.get('lng')
                    location_name = top.get('name', place_name)
                    # Only add flyTo for navigation intent
                    if intent == Intent.NAVIGATE:
                        ui_actions.append({"action": "flyTo", "lat": lat, "lng": lng, "zoom": 15})
                    else:
                        # For property search, fly to location at wider zoom
                        ui_actions.append({"action": "flyTo", "lat": lat, "lng": lng, "zoom": 14})
        
        facts.lat = lat
        facts.lng = lng
        facts.location_name = location_name
        
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
        
        # Gather terrain facts
        if lat and lng and self.terrain_service and intent in [Intent.TERRAIN, Intent.ANALYZE_AREA, Intent.VALUATION]:
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
        if lat and lng and SPATIAL_3D_AVAILABLE:
            try:
                spatial_3d = get_spatial_3d_reasoning()
                floor_height = 0
                
                # If analyzing a building, use its height
                if selected_building and selected_building.get('height'):
                    floor_height = selected_building['height'] / 2  # Mid-floor analysis
                
                analysis_3d = spatial_3d.analyze_3d_context(lat, lng, floor_height, radius_m=200)
                
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
                    optimal = spatial_3d.find_best_floor(lat, lng, max_floor=15)
                    facts.optimal_floor = optimal.get('recommended_floor')
                
                # Shadow analysis for morning/noon
                shadow_10am = spatial_3d.get_shadow_impact(lat, lng, hour=10)
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
        if lat and lng and self.property_service:
            next_task(f"Retrieved market data and trends")
            try:
                market = _compute_market_facts(self.property_service, lat, lng, 1500)
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
            try:
                props = self.property_service.search(lat=lat, lng=lng, radius_m=2000, limit=10)
                facts.nearby_properties = [
                    {
                        "name": p.get('name', 'Property'),
                        "price": p.get('price'),
                        "price_per_sqft": p.get('price_per_sq_ft'),
                        "bedrooms": p.get('bedrooms'),
                        "area": p.get('covered_area'),
                        "distance_m": int(p.get('_distance', 0)),
                        "lat": p.get('latitude'),
                        "lng": p.get('longitude'),
                    }
                    for p in props[:10]
                ]
                
                # Map Sync: Add highlightProperties action for properties with coordinates
                properties_to_highlight = [
                    {
                        "lat": p.get('latitude'),
                        "lng": p.get('longitude'),
                        "name": p.get('name', 'Property'),
                        "price": p.get('price'),
                        "bedrooms": p.get('bedrooms'),
                    }
                    for p in props[:10]
                    if p.get('latitude') and p.get('longitude')
                ]
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
                    from building_analyzer import get_building_analyzer
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
        base = """You are Valora AI, a professional real estate intelligence assistant for Bangalore, India.

**YOUR ROLE:** You are a licensed real estate analysis tool. Your primary purpose is to provide real estate advice, market analysis, investment insights, property valuations, and location recommendations. This is your core function - always provide helpful real estate guidance.

**YOUR CAPABILITIES:**
- Real estate market analysis and investment advice
- Property valuation and price predictions
- Location comparison and recommendations
- Risk assessment for real estate investments
- Urban development and infrastructure impact analysis

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
