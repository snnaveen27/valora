"""
Valora AI — Fine-Tuning Data Helpers v2
Aligned with production pipeline:
  - Facts format matches gis_agents.AgentFacts.to_context_string()
  - System prompt = condensed constitution + intent instruction
  - Chat format (system/user/assistant) matching /api/chat
  - All production fields included
"""

import random
import math

# =============================================================================
# 1. BANGALORE LOCALITY DATA (61 localities with ALL production fields)
# =============================================================================

LOCALITIES = [
    {"name": "Koramangala", "lat": 12.9352, "lng": 77.6245, "price": 12500, "trend": 8.2, "walk": 82, "invest": 78, "livability": 80, "metro_dist": 2100, "metro_name": "Indiranagar Metro", "pois": 487, "transport": 32, "access": 78, "density": 4.2, "elev": 920, "slope": 2.1, "flood": "LOW", "terrain_suit": 85, "listings": 342, "demand": "HIGH", "archetype": "tech_hub", "stage": "mature", "tagline": "Premium tech hub with vibrant startup ecosystem", "tech": 85, "family": 70, "invest_profile": "stable_growth", "risk_score": 35, "risk_level": "LOW", "hazard": 20, "infra_stress": 40},
    {"name": "Indiranagar", "lat": 12.9784, "lng": 77.6408, "price": 14200, "trend": 6.1, "walk": 88, "invest": 72, "livability": 85, "metro_dist": 800, "metro_name": "Indiranagar Metro", "pois": 520, "transport": 38, "access": 85, "density": 4.8, "elev": 915, "slope": 1.8, "flood": "LOW", "terrain_suit": 90, "listings": 285, "demand": "HIGH", "archetype": "lifestyle_hub", "stage": "mature", "tagline": "Bangalore's lifestyle capital with metro connectivity", "tech": 72, "family": 75, "invest_profile": "premium_stable", "risk_score": 28, "risk_level": "LOW", "hazard": 15, "infra_stress": 35},
    {"name": "Whitefield", "lat": 12.9698, "lng": 77.7500, "price": 7200, "trend": 9.5, "walk": 55, "invest": 82, "livability": 65, "metro_dist": 1500, "metro_name": "Whitefield Metro", "pois": 380, "transport": 25, "access": 62, "density": 3.1, "elev": 895, "slope": 1.5, "flood": "LOW", "terrain_suit": 88, "listings": 485, "demand": "HIGH", "archetype": "it_corridor", "stage": "growing", "tagline": "IT powerhouse driving east Bangalore growth", "tech": 90, "family": 60, "invest_profile": "high_growth", "risk_score": 38, "risk_level": "LOW", "hazard": 18, "infra_stress": 45},
    {"name": "HSR Layout", "lat": 12.9116, "lng": 77.6389, "price": 10800, "trend": 10.1, "walk": 75, "invest": 80, "livability": 74, "metro_dist": 3200, "metro_name": "HSR Layout Metro", "pois": 410, "transport": 28, "access": 70, "density": 3.8, "elev": 905, "slope": 1.9, "flood": "LOW", "terrain_suit": 86, "listings": 310, "demand": "HIGH", "archetype": "startup_cluster", "stage": "growing", "tagline": "Startup hub with planned Outer Ring Road metro", "tech": 88, "family": 65, "invest_profile": "high_growth", "risk_score": 32, "risk_level": "LOW", "hazard": 16, "infra_stress": 38},
    {"name": "Electronic City", "lat": 12.8440, "lng": 77.6593, "price": 5200, "trend": 7.8, "walk": 42, "invest": 75, "livability": 52, "metro_dist": 4500, "metro_name": "Bommasandra Metro", "pois": 180, "transport": 15, "access": 48, "density": 2.2, "elev": 880, "slope": 2.5, "flood": "LOW", "terrain_suit": 82, "listings": 520, "demand": "MEDIUM", "archetype": "it_corridor", "stage": "established", "tagline": "India's largest IT park cluster with affordable housing", "tech": 92, "family": 45, "invest_profile": "value_growth", "risk_score": 40, "risk_level": "MEDIUM", "hazard": 22, "infra_stress": 48},
    {"name": "Sarjapur Road", "lat": 12.9100, "lng": 77.6800, "price": 6500, "trend": 11.2, "walk": 42, "invest": 85, "livability": 55, "metro_dist": 6000, "metro_name": "Bellandur Metro (planned)", "pois": 210, "transport": 18, "access": 45, "density": 2.5, "elev": 895, "slope": 2.0, "flood": "MEDIUM", "terrain_suit": 78, "listings": 580, "demand": "HIGH", "archetype": "emerging_corridor", "stage": "growing", "tagline": "High-growth corridor connecting IT hubs", "tech": 82, "family": 58, "invest_profile": "high_growth", "risk_score": 42, "risk_level": "MEDIUM", "hazard": 28, "infra_stress": 50},
    {"name": "JP Nagar", "lat": 12.9063, "lng": 77.5857, "price": 9800, "trend": 5.8, "walk": 72, "invest": 70, "livability": 78, "metro_dist": 1200, "metro_name": "JP Nagar Metro", "pois": 370, "transport": 32, "access": 75, "density": 3.5, "elev": 910, "slope": 1.5, "flood": "LOW", "terrain_suit": 90, "listings": 260, "demand": "MEDIUM", "archetype": "established_residential", "stage": "mature", "tagline": "Well-planned residential hub with excellent connectivity", "tech": 55, "family": 85, "invest_profile": "stable_growth", "risk_score": 25, "risk_level": "LOW", "hazard": 12, "infra_stress": 30},
    {"name": "Marathahalli", "lat": 12.9591, "lng": 77.7009, "price": 7800, "trend": 8.5, "walk": 58, "invest": 76, "livability": 60, "metro_dist": 2800, "metro_name": "Marathahalli Metro (planned)", "pois": 340, "transport": 22, "access": 55, "density": 3.2, "elev": 900, "slope": 1.8, "flood": "LOW", "terrain_suit": 84, "listings": 410, "demand": "HIGH", "archetype": "it_corridor", "stage": "established", "tagline": "ORR IT corridor with growing infrastructure", "tech": 80, "family": 55, "invest_profile": "moderate_growth", "risk_score": 38, "risk_level": "LOW", "hazard": 20, "infra_stress": 42},
    {"name": "Jayanagar", "lat": 12.9308, "lng": 77.5838, "price": 13500, "trend": 4.5, "walk": 85, "invest": 65, "livability": 88, "metro_dist": 500, "metro_name": "Jayanagar Metro", "pois": 480, "transport": 35, "access": 88, "density": 4.5, "elev": 918, "slope": 1.2, "flood": "LOW", "terrain_suit": 92, "listings": 180, "demand": "HIGH", "archetype": "premium_residential", "stage": "mature", "tagline": "Old Bangalore charm with modern metro connectivity", "tech": 40, "family": 92, "invest_profile": "premium_stable", "risk_score": 20, "risk_level": "LOW", "hazard": 10, "infra_stress": 25},
    {"name": "Bellandur", "lat": 12.9260, "lng": 77.6762, "price": 8200, "trend": 9.8, "walk": 48, "invest": 78, "livability": 55, "metro_dist": 3500, "metro_name": "Bellandur Metro (planned)", "pois": 280, "transport": 20, "access": 52, "density": 2.8, "elev": 892, "slope": 1.5, "flood": "HIGH", "terrain_suit": 65, "listings": 450, "demand": "HIGH", "archetype": "it_corridor", "stage": "growing", "tagline": "IT corridor hub near ORR with lake proximity", "tech": 85, "family": 50, "invest_profile": "high_growth", "risk_score": 55, "risk_level": "MEDIUM", "hazard": 45, "infra_stress": 48},
    {"name": "Thanisandra", "lat": 12.9950, "lng": 77.6300, "price": 5200, "trend": 12.0, "walk": 38, "invest": 84, "livability": 48, "metro_dist": 4500, "metro_name": "Nagawara Metro", "pois": 130, "transport": 12, "access": 40, "density": 1.8, "elev": 905, "slope": 2.2, "flood": "LOW", "terrain_suit": 80, "listings": 380, "demand": "MEDIUM", "archetype": "emerging_suburb", "stage": "emerging", "tagline": "North Bangalore's fastest-growing suburb", "tech": 65, "family": 55, "invest_profile": "speculative_growth", "risk_score": 48, "risk_level": "MEDIUM", "hazard": 22, "infra_stress": 55},
    {"name": "Bannerghatta Road", "lat": 12.8900, "lng": 77.5967, "price": 7000, "trend": 7.0, "walk": 48, "invest": 74, "livability": 60, "metro_dist": 4000, "metro_name": "Gottigere Metro", "pois": 200, "transport": 20, "access": 50, "density": 2.5, "elev": 890, "slope": 3.0, "flood": "MEDIUM", "terrain_suit": 75, "listings": 320, "demand": "MEDIUM", "archetype": "corridor", "stage": "growing", "tagline": "Southern corridor with nature and IT proximity", "tech": 60, "family": 65, "invest_profile": "moderate_growth", "risk_score": 42, "risk_level": "MEDIUM", "hazard": 25, "infra_stress": 45},
    {"name": "Rajajinagar", "lat": 12.9900, "lng": 77.5530, "price": 11500, "trend": 5.2, "walk": 78, "invest": 68, "livability": 82, "metro_dist": 600, "metro_name": "Rajajinagar Metro", "pois": 420, "transport": 30, "access": 82, "density": 4.0, "elev": 925, "slope": 1.5, "flood": "LOW", "terrain_suit": 88, "listings": 195, "demand": "MEDIUM", "archetype": "established_residential", "stage": "mature", "tagline": "West Bangalore's residential cornerstone", "tech": 45, "family": 85, "invest_profile": "stable_growth", "risk_score": 22, "risk_level": "LOW", "hazard": 12, "infra_stress": 28},
    {"name": "Hebbal", "lat": 13.0350, "lng": 77.5970, "price": 8500, "trend": 10.5, "walk": 52, "invest": 82, "livability": 62, "metro_dist": 2500, "metro_name": "Hebbal Metro (planned)", "pois": 250, "transport": 22, "access": 58, "density": 2.8, "elev": 910, "slope": 2.0, "flood": "LOW", "terrain_suit": 82, "listings": 340, "demand": "HIGH", "archetype": "growth_hub", "stage": "growing", "tagline": "Airport corridor hub with flyover connectivity", "tech": 70, "family": 60, "invest_profile": "high_growth", "risk_score": 35, "risk_level": "LOW", "hazard": 18, "infra_stress": 40},
    {"name": "Yelahanka", "lat": 13.1007, "lng": 77.5963, "price": 5800, "trend": 8.8, "walk": 45, "invest": 78, "livability": 58, "metro_dist": 5500, "metro_name": "Yelahanka Station", "pois": 190, "transport": 18, "access": 50, "density": 2.2, "elev": 915, "slope": 1.8, "flood": "LOW", "terrain_suit": 85, "listings": 290, "demand": "MEDIUM", "archetype": "suburban", "stage": "growing", "tagline": "Air Force town evolving into residential hub", "tech": 45, "family": 72, "invest_profile": "moderate_growth", "risk_score": 30, "risk_level": "LOW", "hazard": 15, "infra_stress": 35},
    {"name": "Malleshwaram", "lat": 13.0035, "lng": 77.5690, "price": 15000, "trend": 3.8, "walk": 85, "invest": 60, "livability": 90, "metro_dist": 400, "metro_name": "Malleshwaram Metro", "pois": 450, "transport": 35, "access": 90, "density": 4.5, "elev": 922, "slope": 1.0, "flood": "LOW", "terrain_suit": 92, "listings": 120, "demand": "HIGH", "archetype": "heritage_residential", "stage": "mature", "tagline": "Bangalore's heritage heart with premium walkability", "tech": 30, "family": 95, "invest_profile": "premium_stable", "risk_score": 18, "risk_level": "LOW", "hazard": 8, "infra_stress": 22},
    {"name": "Banashankari", "lat": 12.9255, "lng": 77.5468, "price": 8500, "trend": 5.5, "walk": 70, "invest": 68, "livability": 75, "metro_dist": 1500, "metro_name": "Banashankari Metro", "pois": 350, "transport": 28, "access": 72, "density": 3.5, "elev": 912, "slope": 1.5, "flood": "LOW", "terrain_suit": 88, "listings": 230, "demand": "MEDIUM", "archetype": "established_residential", "stage": "mature", "tagline": "South Bangalore residential hub with temple heritage", "tech": 35, "family": 88, "invest_profile": "stable_growth", "risk_score": 24, "risk_level": "LOW", "hazard": 12, "infra_stress": 28},
    {"name": "BTM Layout", "lat": 12.9166, "lng": 77.6101, "price": 9200, "trend": 7.5, "walk": 72, "invest": 75, "livability": 70, "metro_dist": 2000, "metro_name": "BTM Layout Metro (planned)", "pois": 380, "transport": 26, "access": 68, "density": 3.8, "elev": 908, "slope": 1.8, "flood": "LOW", "terrain_suit": 85, "listings": 280, "demand": "HIGH", "archetype": "startup_cluster", "stage": "established", "tagline": "Affordable tech hub bridging Koramangala and Silk Board", "tech": 82, "family": 55, "invest_profile": "moderate_growth", "risk_score": 35, "risk_level": "LOW", "hazard": 18, "infra_stress": 40},
    {"name": "Sadashivanagar", "lat": 13.0089, "lng": 77.5780, "price": 22000, "trend": 3.2, "walk": 75, "invest": 55, "livability": 92, "metro_dist": 1800, "metro_name": "Sadashivanagar Metro", "pois": 180, "transport": 15, "access": 72, "density": 1.8, "elev": 928, "slope": 1.0, "flood": "LOW", "terrain_suit": 95, "listings": 45, "demand": "HIGH", "archetype": "ultra_premium", "stage": "mature", "tagline": "Bangalore's most exclusive address near Raj Bhavan", "tech": 20, "family": 90, "invest_profile": "premium_stable", "risk_score": 12, "risk_level": "LOW", "hazard": 5, "infra_stress": 15},
    {"name": "Hennur", "lat": 13.0350, "lng": 77.6400, "price": 5500, "trend": 11.5, "walk": 35, "invest": 80, "livability": 45, "metro_dist": 5000, "metro_name": "Nagawara Metro", "pois": 120, "transport": 10, "access": 38, "density": 1.5, "elev": 908, "slope": 2.2, "flood": "LOW", "terrain_suit": 80, "listings": 350, "demand": "MEDIUM", "archetype": "emerging_suburb", "stage": "emerging", "tagline": "Emerging north-east corridor with lake frontage", "tech": 55, "family": 50, "invest_profile": "speculative_growth", "risk_score": 48, "risk_level": "MEDIUM", "hazard": 25, "infra_stress": 52},
    {"name": "Kanakapura Road", "lat": 12.8700, "lng": 77.5600, "price": 5000, "trend": 9.2, "walk": 35, "invest": 76, "livability": 48, "metro_dist": 3000, "metro_name": "Konanakunte Metro", "pois": 140, "transport": 14, "access": 42, "density": 1.8, "elev": 885, "slope": 2.8, "flood": "MEDIUM", "terrain_suit": 72, "listings": 310, "demand": "MEDIUM", "archetype": "emerging_corridor", "stage": "emerging", "tagline": "Southern expansion corridor with metro arrival", "tech": 40, "family": 55, "invest_profile": "value_growth", "risk_score": 45, "risk_level": "MEDIUM", "hazard": 28, "infra_stress": 48},
    {"name": "Basavanagudi", "lat": 12.9420, "lng": 77.5740, "price": 14500, "trend": 4.0, "walk": 82, "invest": 62, "livability": 86, "metro_dist": 1000, "metro_name": "National College Metro", "pois": 400, "transport": 30, "access": 80, "density": 4.2, "elev": 916, "slope": 1.2, "flood": "LOW", "terrain_suit": 90, "listings": 150, "demand": "HIGH", "archetype": "heritage_residential", "stage": "mature", "tagline": "Heritage district with Bull Temple and Bugle Rock", "tech": 25, "family": 90, "invest_profile": "premium_stable", "risk_score": 18, "risk_level": "LOW", "hazard": 8, "infra_stress": 22},
    {"name": "Varthur", "lat": 12.9400, "lng": 77.7400, "price": 5800, "trend": 12.5, "walk": 32, "invest": 82, "livability": 42, "metro_dist": 7000, "metro_name": "Whitefield Metro", "pois": 100, "transport": 8, "access": 35, "density": 1.2, "elev": 888, "slope": 1.8, "flood": "HIGH", "terrain_suit": 60, "listings": 420, "demand": "MEDIUM", "archetype": "emerging_suburb", "stage": "emerging", "tagline": "Fast-growing suburb with lake and IT proximity", "tech": 75, "family": 40, "invest_profile": "speculative_growth", "risk_score": 58, "risk_level": "MEDIUM", "hazard": 42, "infra_stress": 52},
    {"name": "Uttarahalli", "lat": 12.9000, "lng": 77.5400, "price": 5500, "trend": 8.0, "walk": 40, "invest": 72, "livability": 50, "metro_dist": 4000, "metro_name": "Kengeri Metro", "pois": 130, "transport": 12, "access": 42, "density": 1.6, "elev": 895, "slope": 2.0, "flood": "LOW", "terrain_suit": 82, "listings": 280, "demand": "MEDIUM", "archetype": "suburban", "stage": "growing", "tagline": "Affordable south-west suburb near NICE Road", "tech": 30, "family": 65, "invest_profile": "value_growth", "risk_score": 35, "risk_level": "LOW", "hazard": 18, "infra_stress": 38},
    {"name": "Domlur", "lat": 12.9610, "lng": 77.6387, "price": 13000, "trend": 6.5, "walk": 80, "invest": 72, "livability": 78, "metro_dist": 1200, "metro_name": "Indiranagar Metro", "pois": 350, "transport": 28, "access": 78, "density": 4.0, "elev": 912, "slope": 1.5, "flood": "LOW", "terrain_suit": 88, "listings": 180, "demand": "HIGH", "archetype": "commercial_mixed", "stage": "mature", "tagline": "Central hub bridging MG Road and Indiranagar", "tech": 75, "family": 60, "invest_profile": "stable_growth", "risk_score": 28, "risk_level": "LOW", "hazard": 14, "infra_stress": 32},
    {"name": "Devanahalli", "lat": 13.2468, "lng": 77.7120, "price": 4200, "trend": 14.0, "walk": 25, "invest": 88, "livability": 35, "metro_dist": 15000, "metro_name": "Airport (no metro)", "pois": 60, "transport": 6, "access": 30, "density": 0.8, "elev": 930, "slope": 1.5, "flood": "LOW", "terrain_suit": 88, "listings": 250, "demand": "MEDIUM", "archetype": "airport_corridor", "stage": "emerging", "tagline": "Airport economy zone with aerospace and IT SEZ", "tech": 60, "family": 25, "invest_profile": "speculative_growth", "risk_score": 52, "risk_level": "MEDIUM", "hazard": 15, "infra_stress": 60},
    {"name": "Rajarajeshwari Nagar", "lat": 12.9200, "lng": 77.5200, "price": 5000, "trend": 7.5, "walk": 42, "invest": 70, "livability": 52, "metro_dist": 3500, "metro_name": "RR Nagar Metro", "pois": 160, "transport": 15, "access": 45, "density": 2.0, "elev": 900, "slope": 2.5, "flood": "LOW", "terrain_suit": 80, "listings": 320, "demand": "MEDIUM", "archetype": "suburban", "stage": "growing", "tagline": "West Bangalore affordable hub with metro planned", "tech": 35, "family": 70, "invest_profile": "value_growth", "risk_score": 38, "risk_level": "LOW", "hazard": 20, "infra_stress": 42},
    {"name": "Cunningham Road", "lat": 12.9880, "lng": 77.5860, "price": 18000, "trend": 4.2, "walk": 82, "invest": 58, "livability": 80, "metro_dist": 800, "metro_name": "MG Road Metro", "pois": 320, "transport": 30, "access": 85, "density": 3.8, "elev": 920, "slope": 1.0, "flood": "LOW", "terrain_suit": 92, "listings": 65, "demand": "HIGH", "archetype": "cbd_premium", "stage": "mature", "tagline": "CBD premium commercial and residential address", "tech": 50, "family": 60, "invest_profile": "premium_stable", "risk_score": 15, "risk_level": "LOW", "hazard": 8, "infra_stress": 18},
    {"name": "Bommanahalli", "lat": 12.9000, "lng": 77.6200, "price": 6200, "trend": 8.8, "walk": 50, "invest": 74, "livability": 55, "metro_dist": 2500, "metro_name": "Bommanahalli Metro", "pois": 220, "transport": 20, "access": 55, "density": 2.8, "elev": 902, "slope": 1.8, "flood": "LOW", "terrain_suit": 82, "listings": 380, "demand": "MEDIUM", "archetype": "transit_hub", "stage": "growing", "tagline": "Silk Board corridor with metro junction potential", "tech": 70, "family": 50, "invest_profile": "moderate_growth", "risk_score": 40, "risk_level": "MEDIUM", "hazard": 20, "infra_stress": 45},
    {"name": "Vijayanagar", "lat": 12.9700, "lng": 77.5350, "price": 9000, "trend": 5.5, "walk": 72, "invest": 66, "livability": 75, "metro_dist": 1500, "metro_name": "Vijayanagar Metro", "pois": 340, "transport": 28, "access": 72, "density": 3.5, "elev": 918, "slope": 1.5, "flood": "LOW", "terrain_suit": 88, "listings": 200, "demand": "MEDIUM", "archetype": "established_residential", "stage": "mature", "tagline": "Well-connected west Bangalore residential zone", "tech": 40, "family": 82, "invest_profile": "stable_growth", "risk_score": 25, "risk_level": "LOW", "hazard": 12, "infra_stress": 30},
]

# BHK types and price multipliers
BHK_TYPES = [
    {"bhk": 1, "sqft_range": (550, 750), "mult": 0.55},
    {"bhk": 2, "sqft_range": (900, 1300), "mult": 1.0},
    {"bhk": 3, "sqft_range": (1400, 2200), "mult": 1.65},
    {"bhk": 4, "sqft_range": (2200, 3500), "mult": 2.8},
]

PROPERTY_TYPES = ["Apartment", "Villa", "Independent House", "Penthouse", "Studio"]

INFRA_EVENTS = [
    "Metro Phase 2B extension", "New flyover on ORR", "IT park expansion",
    "Signal-free corridor project", "Lake rejuvenation project",
    "New bus rapid transit", "Peripheral ring road segment",
    "Suburban rail station", "Smart city upgrades", "New hospital complex",
]

LANDMARKS = [
    "Phoenix Mall", "Forum Mall", "Orion Mall", "Embassy Tech Village",
    "Manyata Tech Park", "Bagmane Tech Park", "Prestige Shantiniketan",
    "Mantri Square", "UB City", "Brigade Gateway", "RMZ Ecoworld",
    "Infosys Campus", "Wipro Campus", "Cubbon Park", "Lalbagh Garden",
]

# =============================================================================
# 2. FACTS BUILDER — matches to_context_string() format EXACTLY
# =============================================================================

def build_facts_string(loc, intent, loc_b=None):
    """Build grounded facts in the EXACT format of AgentFacts.to_context_string()."""
    parts = []

    if intent == "comparison" and loc_b:
        return _build_comparison_facts(loc, loc_b)

    # Location
    parts.append(f"**Location:** {loc['name']}")
    parts.append(f"  - Coordinates: {loc['lat']:.5f}, {loc['lng']:.5f}")

    # Spatial Analysis (for most intents)
    if intent in ("navigate", "analyze_area", "property_search", "investment",
                   "recommendation", "market_trend", "simulate", "valuation",
                   "analyze_building", "general"):
        sp = []
        sp.append(f"POIs nearby: {loc['pois']}")
        sp.append(f"Transport stops: {loc['transport']}")
        sp.append(f"Accessibility: {loc['access']}/100")
        sp.append(f"Walkability: {loc['walk']}/100")
        sp.append(f"Amenity density: {loc['density']:.2f}/sqkm")
        parts.append("**Spatial Analysis:**")
        for s in sp:
            parts.append(f"  - {s}")
        parts.append(f"  - Nearest metro: {loc['metro_name']} ({loc['metro_dist']}m)")
        landmarks = random.sample(LANDMARKS, min(3, len(LANDMARKS)))
        parts.append(f"  - Key POIs: {', '.join(landmarks)}")

    # Terrain (for terrain, analyze_area, investment, simulate)
    if intent in ("terrain", "analyze_area", "investment", "simulate"):
        parts.append("**Terrain:**")
        parts.append(f"  - Elevation: {loc['elev']:.1f}m")
        parts.append(f"  - Slope: {loc['slope']:.1f}°")
        parts.append(f"  - Construction suitability: {loc['terrain_suit']}/100")
        parts.append(f"  - Flood risk: {loc['flood']}")

    # Market Data (for most analytical intents)
    if intent in ("analyze_area", "property_search", "valuation", "investment",
                   "market_trend", "simulate", "recommendation", "comparison"):
        parts.append("**Market Data:**")
        parts.append(f"  - Avg price/sqft: ₹{loc['price']:,}")
        parts.append(f"  - Price trend: {loc['trend']:+.1f}% (annualized)")
        parts.append(f"  - Active listings: {loc['listings']}")
        parts.append(f"  - Demand: {loc['demand']}")

    # Building context (for building analysis, valuation)
    if intent in ("analyze_building", "valuation", "spatial_3d"):
        floors = random.randint(4, 25)
        height = floors * 3.2
        svf = round(random.uniform(0.35, 0.85), 2)
        opt_floor = max(floors - random.randint(2, 5), 3)
        directions = random.sample(["N", "NE", "E", "SE", "S", "SW", "W", "NW"], random.randint(2, 4))
        taller = random.randint(1, 8)
        shorter = random.randint(5, 20)
        btype = random.choice(["residential", "commercial", "mixed-use"])

        parts.append("**Building:**")
        parts.append(f"  - Type: {btype}")
        parts.append(f"  - Height: {height:.1f}m")
        parts.append(f"  - Floors: {floors}")
        parts.append(f"  - Area: {random.randint(800, 3000)}m²")
        val = int(loc['price'] * random.randint(1000, 2500) * random.uniform(0.9, 1.1))
        parts.append(f"  - Estimated value: ₹{val:,}")
        shadow = random.choice(["Low", "Moderate", "High"])
        view = random.choice(["Excellent", "Good", "Average", "Limited"])
        parts.append(f"  - View Quality: {view}")
        parts.append(f"  - Shadow Impact: {shadow}")
        parts.append(f"  - Open Views: {', '.join(directions)}")
        parts.append(f"  - Taller neighbors: {taller}")
        parts.append(f"  - Shorter neighbors: {shorter}")

        parts.append("**3D Spatial Analysis:**")
        parts.append(f"  - Sky View Factor: {svf:.0%}")
        skyline = "high-rise" if floors > 15 else "mid-rise" if floors > 8 else "low-rise"
        parts.append(f"  - Skyline Character: {skyline}")
        parts.append(f"  - Open Views: {', '.join(directions)}")
        parts.append(f"  - Recommended Floor: {opt_floor}")

    # Area Insights (for area analysis, investment, recommendation)
    if intent in ("analyze_area", "investment", "recommendation", "simulate", "market_trend"):
        parts.append("**Area Insights:**")
        parts.append(f"  - Livability Score: {loc['livability']}/100")
        parts.append(f"  - Summary: {loc['tagline']}")
        lm = random.sample(LANDMARKS, min(3, len(LANDMARKS)))
        parts.append(f"  - Landmarks: {', '.join(lm)}")

    # Locality Intelligence (for analysis, investment)
    if intent in ("analyze_area", "investment", "market_trend", "recommendation", "simulate"):
        parts.append("**Locality Intelligence:**")
        parts.append(f"  - {loc['tagline']}")
        parts.append(f"  - Archetype: {loc['archetype'].replace('_', ' ').title()}")
        parts.append(f"  - Growth Stage: {loc['stage'].replace('_', ' ').title()}")
        parts.append(f"  - Tech Orientation: {loc['tech']}/100")
        parts.append(f"  - Family Friendliness: {loc['family']}/100")
        parts.append(f"  - Investment Profile: {loc['invest_profile'].replace('_', ' ').title()}")

    # Risk Assessment (for investment, analysis, terrain)
    if intent in ("analyze_area", "investment", "terrain", "simulate"):
        parts.append("**Risk Assessment:**")
        parts.append(f"  - Overall Risk Score: {loc['risk_score']}/100 ({loc['risk_level']})")
        parts.append(f"  - Hazard Risk: {loc['hazard']}/100")
        parts.append(f"  - Infrastructure Stress: {loc['infra_stress']}/100")

    # Property listings (for property search)
    if intent == "property_search":
        parts.append("**Property Listings:**")
        n = random.randint(5, 25)
        parts.append(f"  - Matching properties: {n}")
        for i in range(min(3, n)):
            bt = random.choice(BHK_TYPES)
            sqft = random.randint(*bt["sqft_range"])
            price = int(loc["price"] * sqft * bt["mult"] / bt["sqft_range"][0] * random.uniform(0.85, 1.15))
            price_l = price / 100000
            ptype = random.choice(PROPERTY_TYPES[:3])
            parts.append(f"  - #{i+1}: {bt['bhk']}BHK {ptype}, {sqft} sqft, ₹{price_l:.1f}L ({loc['name']})")

    # Simulation results (for simulate)
    if intent == "simulate":
        event = random.choice(INFRA_EVENTS)
        impact = round(random.uniform(8, 28), 1)
        timeline = random.choice(["12-18", "18-24", "24-36"])
        radius = round(random.uniform(1.0, 3.0), 1)
        parts.append("**Simulation Results:**")
        parts.append(f"  - Scenario: {event}")
        parts.append(f"  - Property value impact: +{impact}%")
        parts.append(f"  - Timeline: {timeline} months")
        parts.append(f"  - Affected radius: {radius}km")
        parts.append(f"  - Confidence: {'HIGH' if impact < 15 else 'MEDIUM'}")

    return "\n".join(parts)


def _build_comparison_facts(loc_a, loc_b):
    """Build comparison facts for two localities."""
    parts = []
    for label, loc in [("Area A", loc_a), ("Area B", loc_b)]:
        parts.append(f"**{label}: {loc['name']}**")
        parts.append(f"  - Avg price/sqft: ₹{loc['price']:,}")
        parts.append(f"  - Price trend: {loc['trend']:+.1f}% YoY")
        parts.append(f"  - Walkability: {loc['walk']}/100")
        parts.append(f"  - Metro: {loc['metro_dist']/1000:.1f}km ({loc['metro_name']})")
        parts.append(f"  - Investment score: {loc['invest']}/100")
        parts.append(f"  - Livability: {loc['livability']}/100")
        parts.append(f"  - POIs: {loc['pois']} | Transport: {loc['transport']}")
        parts.append(f"  - Phase: {loc['stage']} | Risk: {loc['risk_level'].lower()}")
        parts.append(f"  - Archetype: {loc['archetype'].replace('_', ' ').title()}")
        parts.append("")
    return "\n".join(parts).strip()


# =============================================================================
# 3. TRAINING SYSTEM PROMPT — condensed but captures key behavioral patterns
# =============================================================================

TRAINING_CONSTITUTION = """# VALORA AI - GIS REASONING AGENT

You are Valora AI, a GIS reasoning agent for Bangalore real estate intelligence.

## REASONING FORMAT
Put internal reasoning in <think> tags, then final answer OUTSIDE the tags.
<think> = construct spatial model + step-by-step reasoning.
OUTSIDE <think> = user's answer with cited facts.

## TRUTH FIREWALL
1. CITE OR DECLINE — Every number must come from [GROUNDED FACTS]. No exceptions.
2. NO HALLUCINATION — If data missing: "I don't have [X] data for [location]."
3. CONFIDENCE — End analyses with: "Confidence: HIGH/MEDIUM/LOW based on [reason]."

## CONSTRAINTS
- GROUNDED FACTS ONLY — Use ONLY data from facts section below
- BANGALORE ONLY — Decline non-Bangalore queries politely
- OFFLINE DATA — 686K buildings, 42K properties, 27K POIs from local database
- INDIAN FORMAT — ₹ lakhs/crores, sqft, BHK notation. Bold key metrics.

## RESPONSE STRUCTURE
1. Direct answer (1-2 sentences)
2. Supporting evidence (bullet points with bold metrics)
3. Actionable insight (recommendation)"""

INTENT_INSTRUCTIONS = {
    "navigate": "TASK: Navigate to location. Confirm destination, provide 1-2 key area facts, mention what map shows.",
    "analyze_area": "TASK: Comprehensive area analysis. Include: executive summary, market data, infrastructure score, investment outlook with confidence.",
    "analyze_building": "TASK: 3D building analysis. Cover: building ID, 3D context (sky view, shadows, neighbors), location quality, investment indicator.",
    "property_search": "TASK: Property search. Show: search summary count, top results (BHK/sqft/price), market context comparison, refinement options.",
    "valuation": "TASK: Property valuation. Include: estimated value with range (±15%), factor breakdown, market comparison, confidence level.",
    "investment": "TASK: Investment analysis. Provide: rating (STRONG BUY/BUY/HOLD/AVOID), ROI projection, growth drivers, risk assessment, entry strategy.",
    "recommendation": "TASK: Area/property recommendation. Give: top 3 options with pros/cons, comparison table, best pick for user's criteria.",
    "terrain": "TASK: Terrain analysis. Cover: elevation profile, flood risk, environmental factors, construction suitability recommendation.",
    "comparison": "TASK: Area comparison. Format: comparison table, top 3 key differences, recommendations per buyer type.",
    "market_trend": "TASK: Market trend analysis. Include: current snapshot, price trajectory, supply-demand dynamics, 6-12 month outlook.",
    "simulate": "TASK: What-if simulation. Structure: scenario summary, impact analysis (value/timeline/radius), causal chain, risk factors, recommendation.",
    "general": "TASK: General query. Be helpful, explain capabilities, redirect out-of-scope to Bangalore real estate.",
    "conversational": "TASK: Conversational response. Be brief and friendly. No analysis needed.",
}


def build_system_message(intent, facts_string):
    """Build the complete system message matching _build_llm_messages() in production."""
    instruction = INTENT_INSTRUCTIONS.get(intent, INTENT_INSTRUCTIONS["general"])
    return (
        TRAINING_CONSTITUTION
        + f"\n\n{instruction}"
        + "\n\n**GROUNDED FACTS (use ONLY these):**\n"
        + facts_string
    )


# =============================================================================
# 4. QUERY TEMPLATES
# =============================================================================

QUERY_TEMPLATES = {
    "navigate": [
        "Show me {name}", "Take me to {name}", "Navigate to {name}",
        "Where is {name}?", "Fly to {name}", "Go to {name} on the map",
        "I want to see {name}", "Can you show {name} area?",
    ],
    "analyze_area": [
        "Analyze {name} for investment", "Tell me about {name}",
        "How is {name} as a residential area?", "What's the market like in {name}?",
        "Give me a complete analysis of {name}", "Is {name} good for families?",
        "What are the pros and cons of {name}?", "Describe {name} locality",
        "How livable is {name}?", "What's the infrastructure like in {name}?",
    ],
    "analyze_building": [
        "Analyze this building in {name}", "Tell me about this building",
        "What's the view quality from this building?", "How is the shadow impact here?",
        "Which floor should I pick in this building?", "Is this a good building to buy in?",
    ],
    "property_search": [
        "Find {bhk}BHK in {name} under {budget}",
        "Show me apartments in {name}", "Properties in {name} under {budget}",
        "I'm looking for a {bhk}BHK flat near {name}",
        "Search for {bhk}BHK apartments in {name}",
        "What's available in {name} for {budget}?",
        "Find affordable flats in {name}",
    ],
    "valuation": [
        "What's a {bhk}BHK worth in {name}?",
        "Estimate value of {sqft} sqft apartment in {name}",
        "How much is a {bhk}BHK in {name}?",
        "Fair price for property in {name}?",
        "What should I pay for a {bhk}BHK in {name}?",
    ],
    "investment": [
        "Is {name} a good investment?", "Should I invest in {name}?",
        "What's the ROI potential in {name}?", "Is {name} worth buying?",
        "Investment analysis for {name}", "Growth potential of {name}",
        "Which is better for investment, {name}?",
    ],
    "recommendation": [
        "Where should I buy a {bhk}BHK under {budget}?",
        "Best areas for families in Bangalore?",
        "Recommend areas for investment under {budget}",
        "Where to buy for rental income?",
        "Best locality for IT professionals?",
    ],
    "terrain": [
        "Is {name} flood prone?", "What's the elevation of {name}?",
        "Terrain analysis for {name}", "Is it safe to build in {name}?",
        "Flood risk in {name}?", "How's the terrain around {name}?",
    ],
    "comparison": [
        "Compare {name_a} vs {name_b}",
        "{name_a} or {name_b} - which is better?",
        "Difference between {name_a} and {name_b}",
        "{name_a} vs {name_b} for investment",
        "Compare {name_a} and {name_b} for families",
    ],
    "market_trend": [
        "Price trends in {name}", "Market outlook for {name}",
        "How are prices moving in {name}?", "What's the price forecast for {name}?",
        "Is {name} market going up or down?", "Market analysis for {name}",
    ],
    "simulate": [
        "What if a metro station comes to {name}?",
        "Simulate a {event} near {name}",
        "How would a new IT park affect {name}?",
        "What happens if {event} is built near {name}?",
        "Impact of {event} on {name} property values",
    ],
    "general": [
        "What can you do?", "Help me understand walkability scores",
        "How does your analysis work?", "What data do you have?",
        "Tell me about yourself", "What areas do you cover?",
    ],
    "conversational": [
        "Hi", "Hello", "Thanks!", "That was helpful",
        "Good morning", "Bye", "Thank you for the analysis",
        "Great, what else can you show me?",
    ],
}


def make_query(intent, loc, loc_b=None):
    """Generate a natural query for the given intent and locality."""
    templates = QUERY_TEMPLATES.get(intent, QUERY_TEMPLATES["general"])
    template = random.choice(templates)

    bt = random.choice(BHK_TYPES)
    budget_l = int(loc["price"] * bt["sqft_range"][1] * bt["mult"] / 100000 * random.uniform(0.8, 1.2))
    budget_str = f"₹{budget_l}L" if budget_l < 100 else f"₹{budget_l/100:.1f}Cr"

    return template.format(
        name=loc["name"],
        name_a=loc["name"] if not loc_b else loc["name"],
        name_b=loc_b["name"] if loc_b else "",
        bhk=bt["bhk"],
        budget=budget_str,
        sqft=random.randint(*bt["sqft_range"]),
        event=random.choice(INFRA_EVENTS),
    )


# =============================================================================
# 5. RESPONSE GENERATORS — match INTENT_PROMPTS formatting exactly
# =============================================================================

def make_response(intent, loc, facts_string, loc_b=None):
    """Generate a response matching production prompt formatting."""
    if intent == "conversational":
        return random.choice([
            "Hello! I'm Valora AI, your Bangalore real estate intelligence agent. How can I help you today?",
            "You're welcome! Feel free to ask about any Bangalore locality, property search, or investment analysis.",
            "I'm Valora AI, specializing in Bangalore real estate. I can analyze areas, search properties, estimate values, and more. What would you like to explore?",
            "Good to have you! Try asking: 'Analyze Koramangala for investment' or 'Find 2BHK under 80L in Whitefield'.",
            "Glad I could help! I can also compare areas, run simulations, or analyze buildings in 3D. What's next?",
        ])

    if intent == "general":
        return _resp_general()

    # All analytical intents get <think> reasoning
    think = _make_think(intent, loc, loc_b)
    body = _RESPONSE_BUILDERS[intent](loc, loc_b)
    return f"<think>\n{think}\n</think>\n\n{body}"


def _make_think(intent, loc, loc_b=None):
    """Generate <think> reasoning content."""
    lines = []
    if intent == "navigate":
        lines.append(f"User wants to navigate to {loc['name']}.")
        lines.append(f"Coordinates: {loc['lat']:.5f}, {loc['lng']:.5f}")
        lines.append(f"Key context: walkability {loc['walk']}/100, {loc['pois']} POIs, metro {loc['metro_dist']}m.")
    elif intent == "analyze_area":
        lines.append(f"Analyzing {loc['name']} comprehensively.")
        lines.append(f"Price: ₹{loc['price']:,}/sqft, trend: {loc['trend']:+.1f}%.")
        lines.append(f"Infrastructure: {loc['pois']} POIs, walkability {loc['walk']}/100, metro {loc['metro_dist']}m.")
        lines.append(f"Archetype: {loc['archetype']}, stage: {loc['stage']}.")
        lines.append(f"Risk: {loc['risk_score']}/100 ({loc['risk_level']}). Investment score: {loc['invest']}/100.")
    elif intent == "analyze_building":
        lines.append(f"Building analysis in {loc['name']}.")
        lines.append(f"Area character: {loc['archetype'].replace('_', ' ')}. Need to assess view, shadow, optimal floor.")
    elif intent == "property_search":
        lines.append(f"Searching properties in {loc['name']}.")
        lines.append(f"Market: ₹{loc['price']:,}/sqft, {loc['listings']} active listings, {loc['demand']} demand.")
    elif intent == "valuation":
        lines.append(f"Estimating property value in {loc['name']}.")
        lines.append(f"Base rate: ₹{loc['price']:,}/sqft. Trend: {loc['trend']:+.1f}%.")
        lines.append(f"Need to apply adjustments for BHK, floor, age, amenities.")
    elif intent == "investment":
        lines.append(f"Investment analysis for {loc['name']}.")
        lines.append(f"Investment score: {loc['invest']}/100. Price: ₹{loc['price']:,}/sqft.")
        lines.append(f"Growth: {loc['trend']:+.1f}%. Risk: {loc['risk_score']}/100.")
        lines.append(f"Stage: {loc['stage']}. Profile: {loc['invest_profile']}.")
    elif intent == "recommendation":
        lines.append("User needs area recommendations based on criteria.")
        lines.append(f"Considering {loc['name']} (₹{loc['price']:,}/sqft, invest {loc['invest']}/100).")
    elif intent == "terrain":
        lines.append(f"Terrain analysis for {loc['name']}.")
        lines.append(f"Elevation: {loc['elev']}m, slope: {loc['slope']}°, flood: {loc['flood']}.")
        lines.append(f"Construction suitability: {loc['terrain_suit']}/100.")
    elif intent == "comparison":
        lines.append(f"Comparing {loc['name']} vs {loc_b['name'] if loc_b else 'other area'}.")
        if loc_b:
            lines.append(f"Price: ₹{loc['price']:,} vs ₹{loc_b['price']:,}/sqft.")
            lines.append(f"Investment: {loc['invest']} vs {loc_b['invest']}/100.")
            lines.append(f"Livability: {loc['livability']} vs {loc_b['livability']}/100.")
    elif intent == "market_trend":
        lines.append(f"Market trend analysis for {loc['name']}.")
        lines.append(f"Current: ₹{loc['price']:,}/sqft, trend: {loc['trend']:+.1f}%.")
        lines.append(f"Demand: {loc['demand']}. Listings: {loc['listings']}.")
    elif intent == "simulate":
        lines.append(f"Simulating infrastructure impact on {loc['name']}.")
        lines.append(f"Current baseline: ₹{loc['price']:,}/sqft, invest {loc['invest']}/100.")
    return "\n".join(lines)


def _resp_navigate(loc, _=None):
    return (
        f"Flying to **{loc['name']}**, {loc['tagline'].lower()}.\n\n"
        f"**Quick Context:**\n"
        f"- Walkability: **{loc['walk']}/100**\n"
        f"- Nearby POIs: **{loc['pois']}** within 1km\n"
        f"- Nearest metro: **{loc['metro_name']}** ({loc['metro_dist']}m)\n\n"
        f"The 3D map will show the {loc['archetype'].replace('_', ' ')} character of this area."
    )


def _resp_analyze_area(loc, _=None):
    inv_label = "strong investment zone" if loc['invest'] >= 75 else "moderate investment zone" if loc['invest'] >= 60 else "value zone"
    return (
        f"**{loc['name']}** is a {inv_label} with {loc['demand'].lower()} demand.\n\n"
        f"**Market Snapshot:**\n"
        f"- Average price: **₹{loc['price']:,}/sqft** ({loc['trend']:+.1f}% YoY)\n"
        f"- Active listings: {loc['listings']} properties\n"
        f"- Demand: {loc['demand']}\n\n"
        f"**Infrastructure:** Walkability **{loc['walk']}/100**, {loc['pois']} POIs, "
        f"metro {loc['metro_dist']/1000:.1f}km ({loc['metro_name']})\n\n"
        f"**Locality Profile:** {loc['archetype'].replace('_', ' ').title()} — {loc['tagline']}\n"
        f"- Growth stage: {loc['stage'].title()}\n"
        f"- Risk: {loc['risk_level']} ({loc['risk_score']}/100)\n\n"
        f"**Outlook:** {'Suitable for both end-users and investors' if loc['invest'] >= 70 else 'Better suited for end-users'}. "
        f"{'Strong appreciation expected' if loc['trend'] > 8 else 'Stable growth expected'}.\n\n"
        f"Confidence: {'HIGH' if loc['listings'] > 200 else 'MEDIUM'} based on {loc['listings']} listings and {loc['pois']} POI data points."
    )


def _resp_analyze_building(loc, _=None):
    floors = random.randint(6, 20)
    svf = round(random.uniform(0.4, 0.8), 2)
    opt = max(floors - random.randint(2, 4), 4)
    dirs = random.sample(["North", "Northeast", "East", "Southeast", "South"], random.randint(2, 3))
    taller = random.randint(2, 6)
    shorter = random.randint(5, 15)
    return (
        f"**3D Analysis at {loc['lat']:.4f}, {loc['lng']:.4f} ({loc['name']})**\n\n"
        f"**Sky View Factor: {svf}** ({'Good' if svf > 0.6 else 'Moderate'} - {'minor' if svf > 0.6 else 'some'} obstruction)\n"
        f"- Open views: {', '.join(dirs)}\n"
        f"- {taller} taller buildings within 200m, {shorter} shorter\n\n"
        f"**Building Context:**\n"
        f"- Area character: {loc['archetype'].replace('_', ' ').title()}\n"
        f"- Density score: {min(95, loc['pois'] // 5)}/100\n\n"
        f"**Optimal Floor: {opt}th+** for unobstructed views\n"
        f"- Floors 1-{opt//3}: Significant shadow impact\n"
        f"- Floors {opt//3+1}-{opt-1}: Partial obstruction\n"
        f"- Floors {opt}+: Clear views towards {dirs[0]}\n\n"
        f"Confidence: MEDIUM based on 3D spatial model."
    )


def _resp_property_search(loc, _=None):
    bt = random.choice(BHK_TYPES[:3])
    n = random.randint(8, 35)
    results = []
    for i in range(3):
        sqft = random.randint(*bt["sqft_range"])
        price_l = int(loc["price"] * sqft * random.uniform(0.85, 1.15) / 100000)
        ppsf = int(price_l * 100000 / sqft)
        feat = random.choice(["Near metro", "Gated community", "New construction", "Corner unit", "Garden view", "Covered parking"])
        results.append(f"{i+1}. **{bt['bhk']}BHK {sqft} sqft** — ₹{price_l}L (₹{ppsf:,}/sqft) — {feat}")
    return (
        f"Found **{n} properties** matching {bt['bhk']}BHK in {loc['name']}.\n\n"
        f"**Top Picks:**\n" + "\n".join(results) + "\n\n"
        f"Average for area: **₹{loc['price']:,}/sqft** — "
        f"{'these are below' if random.random() > 0.5 else 'at'} market average.\n\n"
        f"Refine by: amenities, floor preference, or specific micro-location.\n\n"
        f"Confidence: HIGH based on {loc['listings']} active listings."
    )


def _resp_valuation(loc, _=None):
    bt = random.choice(BHK_TYPES[:3])
    sqft = random.randint(*bt["sqft_range"])
    base = loc["price"]
    adj_floor = random.randint(-5, 12)
    adj_age = random.randint(-8, 5)
    adj_bhk = random.randint(-3, 8)
    final_ppsf = int(base * (1 + (adj_floor + adj_age + adj_bhk) / 100))
    total = final_ppsf * sqft
    total_cr = total / 10000000
    low = total_cr * 0.85
    high = total_cr * 1.15
    return (
        f"**Estimated Value: ₹{total_cr:.2f} Cr** (Range: ₹{low:.2f} - {high:.2f} Cr)\n\n"
        f"**Breakdown:**\n"
        f"- Base rate: ₹{base:,}/sqft ({loc['name']} average)\n"
        f"- {bt['bhk']}BHK adjustment: {adj_bhk:+d}%\n"
        f"- Floor premium: {adj_floor:+d}%\n"
        f"- Age/condition: {adj_age:+d}%\n\n"
        f"**Final: ₹{final_ppsf:,}/sqft × {sqft:,} = ₹{total_cr:.2f} Cr**\n\n"
        f"vs. Area Average: {((final_ppsf - base) / base * 100):+.0f}% "
        f"{'premium' if final_ppsf > base else 'discount'}.\n\n"
        f"Valuation confidence: {'HIGH' if loc['listings'] > 200 else 'MEDIUM'} (based on {loc['listings']} comparable listings)"
    )


def _resp_investment(loc, _=None):
    rating = "STRONG BUY" if loc['invest'] >= 80 else "BUY" if loc['invest'] >= 70 else "HOLD" if loc['invest'] >= 55 else "AVOID"
    rental = round(random.uniform(2.5, 4.5), 1)
    roi_3y = round(loc['trend'] * 3 + rental * 3, 0)
    return (
        f"**Investment Analysis: {loc['name']}**\n\n"
        f"**Rating: {rating}** — {loc['tagline']}\n\n"
        f"**ROI Projection (3-year):**\n"
        f"- Entry price: **₹{loc['price']:,}/sqft**\n"
        f"- Annual appreciation: **{loc['trend']:+.1f}%**\n"
        f"- Rental yield: **{rental}%** (estimated)\n"
        f"- Projected 3-year return: **{roi_3y:.0f}%** (capital + rental)\n\n"
        f"**Growth Drivers:**\n"
        f"- {loc['archetype'].replace('_', ' ').title()} archetype ({loc['stage']} stage)\n"
        f"- {loc['pois']} POIs and {loc['transport']} transport links\n"
        f"- Metro: {loc['metro_name']} ({loc['metro_dist']/1000:.1f}km)\n\n"
        f"**Risk: {loc['risk_level']}** ({loc['risk_score']}/100)\n"
        f"- Hazard: {loc['hazard']}/100\n"
        f"- Infrastructure stress: {loc['infra_stress']}/100\n\n"
        f"**Recommendation:** {'Enter now' if rating in ('STRONG BUY', 'BUY') else 'Wait for correction'}. "
        f"Best picks: 2BHK under ₹{int(loc['price'] * 1100 / 100000)}L.\n\n"
        f"Confidence: {'HIGH' if loc['listings'] > 200 else 'MEDIUM'} based on {loc['invest']}/100 investment score and {loc['listings']} listings."
    )


def _resp_recommendation(loc, _=None):
    # Pick 2 other localities as alternatives
    alts = [l for l in LOCALITIES if l['name'] != loc['name']]
    random.shuffle(alts)
    picks = [loc] + alts[:2]
    picks.sort(key=lambda x: x['invest'], reverse=True)
    lines = []
    for i, p in enumerate(picks):
        tag = " ⭐ Top Pick" if i == 0 else ""
        lines.append(
            f"**{i+1}. {p['name']}**{tag}\n"
            f"- ₹{p['price']:,}/sqft | Investment: {p['invest']}/100\n"
            f"- {p['tagline']}\n"
            f"- {'Pro' if i == 0 else 'Note'}: {p['archetype'].replace('_', ' ').title()} ({p['stage']})"
        )
    return (
        f"Based on your criteria, here are my top recommendations:\n\n"
        + "\n\n".join(lines)
        + f"\n\n**My pick: {picks[0]['name']}** — highest investment score ({picks[0]['invest']}/100) "
        f"with {picks[0]['trend']:+.1f}% growth.\n\n"
        f"Confidence: HIGH based on 788 locality profiles analyzed."
    )


def _resp_terrain(loc, _=None):
    flood_desc = {
        "LOW": "Low risk area with good drainage",
        "MEDIUM": "Moderate risk — check monsoon drainage before purchase",
        "HIGH": "⚠️ High flood risk — elevated ground floor recommended",
    }
    suit_desc = "suitable" if loc['terrain_suit'] >= 80 else "suitable with precautions" if loc['terrain_suit'] >= 60 else "challenging"
    return (
        f"**Terrain Analysis: {loc['name']}**\n\n"
        f"**Elevation:** {loc['elev']}m above sea level\n"
        f"**Slope:** {loc['slope']}° ({'Flat' if loc['slope'] < 2 else 'Gentle' if loc['slope'] < 4 else 'Moderate'})\n\n"
        f"**Flood Risk: {loc['flood']}** {'⚠️' if loc['flood'] != 'LOW' else ''}\n"
        f"- {flood_desc[loc['flood']]}\n"
        f"- Hazard score: {loc['hazard']}/100\n\n"
        f"**Construction Suitability: {loc['terrain_suit']}/100** — {suit_desc}\n\n"
        f"**Recommendation:** "
        f"{'Safe for standard construction.' if loc['flood'] == 'LOW' else 'Ensure proper drainage and elevated foundation (+1m).'}\n\n"
        f"Confidence: HIGH based on terrain grid data."
    )


def _resp_comparison(loc, loc_b=None):
    if not loc_b:
        loc_b = random.choice([l for l in LOCALITIES if l['name'] != loc['name']])
    diff_price = abs(loc['price'] - loc_b['price']) / max(loc['price'], loc_b['price']) * 100
    return (
        f"**{loc['name']} vs {loc_b['name']}**\n\n"
        f"| Factor | {loc['name']} | {loc_b['name']} |\n"
        f"|--------|---|---|\n"
        f"| Price/sqft | ₹{loc['price']:,} | ₹{loc_b['price']:,} |\n"
        f"| Trend | {loc['trend']:+.1f}% | {loc_b['trend']:+.1f}% |\n"
        f"| Walkability | {loc['walk']}/100 | {loc_b['walk']}/100 |\n"
        f"| Metro | {loc['metro_dist']/1000:.1f}km | {loc_b['metro_dist']/1000:.1f}km |\n"
        f"| Investment | {loc['invest']}/100 | {loc_b['invest']}/100 |\n"
        f"| Livability | {loc['livability']}/100 | {loc_b['livability']}/100 |\n\n"
        f"**Key Differences:**\n"
        f"1. **Price:** {loc['name'] if loc['price'] > loc_b['price'] else loc_b['name']} is {diff_price:.0f}% more expensive\n"
        f"2. **Growth:** {loc['name'] if loc['trend'] > loc_b['trend'] else loc_b['name']} has stronger appreciation\n"
        f"3. **Metro:** {loc['name'] if loc['metro_dist'] < loc_b['metro_dist'] else loc_b['name']} has better metro access\n\n"
        f"**Recommendations:**\n"
        f"- End-user: **{loc['name'] if loc['livability'] > loc_b['livability'] else loc_b['name']}** (livability {max(loc['livability'], loc_b['livability'])}/100)\n"
        f"- Investor: **{loc['name'] if loc['invest'] > loc_b['invest'] else loc_b['name']}** (investment {max(loc['invest'], loc_b['invest'])}/100)\n\n"
        f"Confidence: HIGH based on comprehensive data."
    )


def _resp_market_trend(loc, _=None):
    trend_dir = "Accelerating" if loc['trend'] > 8 else "Stable" if loc['trend'] > 5 else "Decelerating"
    low_p = int(loc['price'] * 0.75)
    high_p = int(loc['price'] * 1.35)
    return (
        f"**Market Trends: {loc['name']}**\n\n"
        f"**Current:** ₹{loc['price']:,}/sqft ({loc['trend']:+.1f}% YoY) | Demand: {loc['demand']} | {loc['listings']} listings\n\n"
        f"**Price Trajectory:**\n"
        f"- 12-month appreciation: **{loc['trend']:+.1f}%**\n"
        f"- Trend: **{trend_dir}**\n"
        f"- Range: ₹{low_p:,} (resale) to ₹{high_p:,} (new premium)\n\n"
        f"**Supply-Demand:**\n"
        f"- Demand level: {loc['demand']}\n"
        f"- Active supply: {loc['listings']} listings\n"
        f"- Infrastructure: {loc['pois']} POIs, metro {loc['metro_dist']/1000:.1f}km\n\n"
        f"**Outlook (6-12 months):**\n"
        f"Expect **{loc['trend']*0.8:+.0f}-{loc['trend']*1.2:+.0f}%** appreciation. "
        f"{loc['archetype'].replace('_', ' ').title()} dynamics support continued growth.\n\n"
        f"Confidence: {'HIGH' if loc['listings'] > 200 else 'MEDIUM'} based on {loc['listings']} listings and market data."
    )


def _resp_simulate(loc, _=None):
    event = random.choice(INFRA_EVENTS)
    impact = round(random.uniform(10, 25), 0)
    timeline = random.choice(["18-24", "24-36"])
    radius = round(random.uniform(1.5, 3.0), 1)
    return (
        f"**Simulating: {event} near {loc['name']}**\n\n"
        f"**Impact Analysis:**\n"
        f"- Property value: **+{impact:.0f}-{impact+8:.0f}%** within 500m\n"
        f"- Timeline: {timeline} months post-announcement\n"
        f"- Affected radius: {radius}km\n"
        f"- Confidence: {'HIGH' if impact < 18 else 'MEDIUM'}\n\n"
        f"**Causal Chain:**\n"
        f"1. {event} announced →\n"
        f"2. Improved connectivity/infrastructure →\n"
        f"3. Demand increases from professionals →\n"
        f"4. Rental yields rise, then capital values follow\n\n"
        f"**Risk Factors:**\n"
        f"- Actual completion may face delays\n"
        f"- Construction phase may cause temporary 5-8% dip\n\n"
        f"**Recommendation:**\n"
        f"Entry within 6 months of announcement. Current price: ₹{loc['price']:,}/sqft.\n\n"
        f"Confidence: MEDIUM based on historical infrastructure impact patterns."
    )


def _resp_general():
    return (
        "I can help you with:\n"
        "- **Navigation**: Explore any Bangalore locality in 3D\n"
        "- **Property Search**: Find listings by budget, BHK, location\n"
        "- **Area Analysis**: Investment potential, infrastructure, livability\n"
        "- **Valuation**: Estimate fair market value\n"
        "- **Investment**: ROI analysis, growth potential, risk assessment\n"
        "- **Simulations**: 'What-if' scenarios for infrastructure\n"
        "- **3D Analysis**: View quality, shadow, floor recommendations\n"
        "- **Comparisons**: Side-by-side area analysis\n"
        "- **Market Trends**: Price trajectories, supply-demand\n\n"
        "Try asking: 'Analyze Koramangala for investment' or 'Find 2BHK under 80 lakhs in Whitefield'"
    )


_RESPONSE_BUILDERS = {
    "navigate": _resp_navigate,
    "analyze_area": _resp_analyze_area,
    "analyze_building": _resp_analyze_building,
    "property_search": _resp_property_search,
    "valuation": _resp_valuation,
    "investment": _resp_investment,
    "recommendation": _resp_recommendation,
    "terrain": _resp_terrain,
    "comparison": _resp_comparison,
    "market_trend": _resp_market_trend,
    "simulate": _resp_simulate,
}


# =============================================================================
# 6. EXAMPLE BUILDER — assembles complete training example
# =============================================================================

def make_example(intent):
    """Generate a complete chat-format training example."""
    loc = random.choice(LOCALITIES)
    loc_b = None

    if intent == "comparison":
        others = [l for l in LOCALITIES if l['name'] != loc['name']]
        loc_b = random.choice(others)

    # Build facts
    facts_str = build_facts_string(loc, intent, loc_b)

    # Build system message (matches _build_llm_messages in production)
    system_msg = build_system_message(intent, facts_str)

    # Build user query
    query = make_query(intent, loc, loc_b)

    # Build response
    response = make_response(intent, loc, facts_str, loc_b)

    return {
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": query},
            {"role": "assistant", "content": response},
        ]
    }
