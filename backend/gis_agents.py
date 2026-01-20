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
try:
    from digital_twin import StateChange
except ImportError:
    StateChange = None


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
    
    # Simulation facts
    simulation_results: Optional[Dict[str, Any]] = None
    
    # RAG context
    rag_context: Optional[str] = None
    
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
        
        # RAG context
        if self.rag_context:
            parts.append(f"**Knowledge Base:**\n{self.rag_context}")
        
        return "\n".join(parts) if parts else "No specific location data available."
    
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
    ) -> Tuple[AgentFacts, Intent, List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Gather grounded facts from all relevant agents.
        Returns (facts, detected_intent, ui_actions, digital_twin_state).
        """
        facts = AgentFacts()
        ui_actions = []
        digital_twin_state = None
        
        # Extract context
        selected_building = context.get('selectedBuilding')
        selected_location = context.get('selectedLocation')
        selected_place = context.get('selectedPlace')
        
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
            location_name = f"Building at {lat:.4f}, {lng:.4f}" if lat and lng else "Selected Building"
        elif selected_location:
            lat = selected_location.get('lat')
            lng = selected_location.get('lng')
            location_name = f"Location {lat:.4f}, {lng:.4f}" if lat and lng else "Selected Location"
        
        # If navigate or property_search intent, try to geocode location from query
        if intent in [Intent.NAVIGATE, Intent.PROPERTY_SEARCH] and not lat:
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
            try:
                terrain = self.terrain_service.get_terrain_analysis(lat, lng)
                if terrain:
                    facts.elevation_m = terrain.get('elevation_mean')
                    facts.slope_deg = terrain.get('slope_mean')
                    facts.terrain_suitability = terrain.get('suitability_score')
                    facts.flood_risk = terrain.get('flood_risk', 'unknown')
            except Exception as e:
                print(f"Terrain agent error: {e}")
        
        # Gather market facts (deterministic from property data)
        if lat and lng and self.property_service:
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
                    }
                    for p in props[:10]
                ]
            except Exception as e:
                print(f"Property agent error: {e}")
        
        # Building facts
        if selected_building:
            facts.building_height = selected_building.get('height')
            facts.building_levels = selected_building.get('levels')
            facts.building_type = selected_building.get('buildingType')
            facts.building_area = selected_building.get('area')
            
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
        
        return facts, intent, ui_actions, digital_twin_state
    
    def build_system_prompt(self, intent: Intent) -> str:
        """Build a focused system prompt based on intent."""
        base = """You are Valora AI, a GIS and real estate intelligence assistant for Bangalore, India.

**CRITICAL RULES:**
1. ONLY use the factual data provided in the context below. Do NOT invent statistics.
2. If data is missing, say "data not available" rather than making up numbers.
3. Be concise (2-3 short paragraphs).
4. Focus on insights the user can act on.
5. Do NOT output code, XML, or tool calls.
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
