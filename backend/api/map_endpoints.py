"""
Map-related API endpoints for advanced geospatial operations
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Tuple
import logging
import re
from difflib import get_close_matches
try:
    from shapely.geometry import Point, Polygon, shape
    from shapely.ops import transform
    import pyproj
    SHAPELY_AVAILABLE = True
except Exception:
    SHAPELY_AVAILABLE = False
    Point = None
    Polygon = None
    shape = None
    transform = None
    pyproj = None
from functools import partial

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/maps", tags=["maps"])

class GeocodingRequest(BaseModel):
    """Request for geocoding an address"""
    address: str
    
class PolygonAnalysisRequest(BaseModel):
    """Request for analyzing a polygon area"""
    polygon: List[List[float]] = Field(..., description="List of [lat, lng] coordinates")
    area_sqkm: Optional[float] = Field(None, description="Pre-calculated area in sq km")
    analysis_type: str = Field("comprehensive", description="Type: comprehensive, properties, demographics")

class BufferZoneRequest(BaseModel):
    """Request for creating buffer zones"""
    center: List[float] = Field(..., description="[lat, lng] center point")
    radius_km: float = Field(..., description="Radius in kilometers")
    analysis_points: Optional[int] = Field(8, description="Number of points for analysis")

class IsochoneRequest(BaseModel):
    """Request for creating isochrone (travel time) polygons"""
    origin: List[float] = Field(..., description="[lat, lng] origin point")
    mode: str = Field("driving", description="Travel mode: driving, walking, transit")
    time_minutes: List[int] = Field([5, 10, 15], description="Travel time intervals")

class LayerRequest(BaseModel):
    """Request for layer data"""
    layer_type: str = Field(..., description="Layer type: heatmap, clusters, transit, amenities")
    bounds: Optional[List[List[float]]] = None
    zoom_level: Optional[int] = 12

@router.get("/geocode")
async def geocode_address(address: str = Query(...)) -> Dict[str, Any]:
    """
    Geocode an address to coordinates
    """
    try:
        # Import services
        from backend.services.mappls_integration import MapplsService
        from backend.services.external_apis import external_api_service
        from backend.services.map_command_processor import MapCommandProcessor
        
        # Try our Bangalore database first
        map_processor = MapCommandProcessor()
        location_match = map_processor.fuzzy_match_location(address)
        
        if location_match and location_match["confidence"] > 0.7:
            return {
                "status": "success",
                "address": location_match["name"],
                "coordinates": location_match["coordinates"],
                "source": "bangalore_db",
                "confidence": location_match["confidence"]
            }
        
        # Try Mappls geocoding with Bangalore context
        mappls = MapplsService()
        # Add Bangalore context if not already present
        search_address = address
        if "bangalore" not in address.lower() and "bengaluru" not in address.lower():
            search_address = f"{address}, Bangalore"
        
        coords = mappls.geocode(search_address)
        if coords:
            return {
                "status": "success",
                "address": address,
                "coordinates": list(coords),
                "source": "mappls",
                "search_query": search_address
            }
        
        # Fallback to mock data for common locations
        mock_locations = {
            # Bangalore areas - from processed data
            "sarjapur": [12.9010, 77.7760],
            "panathur": [12.9437, 77.7208],
            "hebbal": [13.0358, 77.5970],
            "rajaji nagar": [12.9917, 77.5523],
            "rajarajeshwari nagar": [12.9179, 77.5184],
            "whitefield": [12.9698, 77.7499],
            "kanakapura road": [12.8684, 77.5638],
            "carmelaram": [12.9278, 77.7547],
            "bagalur": [13.1634, 77.6396],
            "soukya road": [13.0925, 77.7258],
            "tumkur road": [13.0299, 77.5304],
            "chambenahalli": [12.9625, 77.7844],
            "koramangala": [12.9352, 77.6245],
            "electronic city": [12.8406, 77.6762],
            "indiranagar": [12.9719, 77.6412],
            "jayanagar": [12.9308, 77.5838],
            "malleshwaram": [13.0012, 77.5649],
            "btm layout": [12.9166, 77.6101],
            "hsr layout": [12.9121, 77.6446],
            "marathahalli": [12.9591, 77.7011],
            "jp nagar": [12.9078, 77.5850],
            "yeshwanthpur": [13.0207, 77.5385],
            "yelahanka": [13.1007, 77.5963],
            "bannerghatta": [12.8004, 77.5855],
            "bellandur": [12.9249, 77.6733],
            "domlur": [12.9616, 77.6387],
            "frazer town": [12.9896, 77.6188],
            "rt nagar": [13.0251, 77.5967],
            "kalyan nagar": [13.0287, 77.6397],
            "old madras road": [13.0049, 77.6721],
            "horamavu": [13.0216, 77.6561],
            "kr puram": [12.9990, 77.6958],
            "brookefield": [12.9716, 77.7127],
            "varthur": [12.9333, 77.7500],
            "kadugodi": [12.9897, 77.7571],
            "ramamurthy nagar": [13.0145, 77.6763],
            "cv raman nagar": [12.9842, 77.6614],
            "hoodi": [12.9928, 77.7178],
            "mahadevapura": [12.9919, 77.6975],
            # Other cities
            "bangalore": [12.9716, 77.5946],
            "bengaluru": [12.9716, 77.5946],
            "mumbai": [19.0760, 72.8777],
            "delhi": [28.6139, 77.2090],
            "hyderabad": [17.3850, 78.4867],
            "pune": [18.5204, 73.8567],
            "chennai": [13.0827, 80.2707],
            "kolkata": [22.5726, 88.3639],
            "gurgaon": [28.4595, 77.0266],
            "noida": [28.5355, 77.3910]
        }
        
        address_lower = address.lower().strip()

        # 1) Try direct substring match on known locations
        for location, coords in mock_locations.items():
            if location in address_lower:
                return {
                    "status": "success",
                    "address": address,
                    "coordinates": coords,
                    "source": "mock"
                }

        # 2) Try parsing as explicit coordinates: "lat,lng"
        try:
            coord_match = re.search(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", address_lower)
            if coord_match:
                lat = float(coord_match.group(1))
                lng = float(coord_match.group(2))
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return {
                        "status": "success",
                        "address": address,
                        "coordinates": [lat, lng],
                        "source": "input_coords"
                    }
        except Exception as e:
            logger.debug(f"Coordinate parse failed: {e}")

        # 3) Fuzzy match common typos and synonyms
        synonyms = {
            "bangalor": "bangalore",
            "banglore": "bangalore",
            "blr": "bangalore",
            "bengaluru": "bengaluru",
            "delhi ncr": "delhi",
            "gurugram": "gurgaon",
            "whitfield": "whitefield",
            "koramangla": "koramangala",
            "hsr": "hsr layout",
            "btm": "btm layout",
            "e city": "electronic city",
            "ecity": "electronic city",
            "kr puram": "kr puram",
            "rr nagar": "rajarajeshwari nagar",
            "rajaji": "rajaji nagar"
        }
        for syn, target in synonyms.items():
            if syn in address_lower and target in mock_locations:
                return {
                    "status": "success",
                    "address": address,
                    "coordinates": mock_locations[target],
                    "source": "synonym"
                }

        # 4) Fuzzy match with lower threshold for typos
        try:
            best = get_close_matches(address_lower, list(mock_locations.keys()), n=1, cutoff=0.6)
            if best:
                match_key = best[0]
                logger.info(f"Fuzzy matched '{address}' to '{match_key}'")
                return {
                    "status": "success",
                    "address": address,
                    "coordinates": mock_locations[match_key],
                    "source": "fuzzy",
                    "matched_to": match_key
                }
        except Exception as e:
            logger.debug(f"Fuzzy match failed: {e}")
        
        # Default to Bangalore center
        return {
            "status": "partial",
            "address": address,
            "coordinates": [12.9716, 77.5946],
            "source": "default",
            "message": "Could not geocode exact location, showing city center"
        }
        
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/polygon/analyze")
async def analyze_polygon(request: PolygonAnalysisRequest) -> Dict[str, Any]:
    """
    Analyze a drawn polygon for properties, demographics, and investment potential
    """
    try:
        from backend.services.multi_agent_orchestrator import ValoraOrchestrator
        from backend.services.dmpe_engine import DMPEEngine
        
        orchestrator = ValoraOrchestrator()
        dmpe = DMPEEngine()

        points = request.polygon or []
        center = [12.9716, 77.5946]
        area = float(request.area_sqkm) if request.area_sqkm else 0.0
        perimeter_km = 0.0

        if points:
            if SHAPELY_AVAILABLE and Polygon is not None and pyproj is not None:
                poly = Polygon([(p[1], p[0]) for p in points])
                if not request.area_sqkm:
                    geod = pyproj.Geod(ellps='WGS84')
                    area = abs(geod.geometry_area_perimeter(poly)[0]) / 1_000_000
                centroid = poly.centroid
                center = [centroid.y, centroid.x]
                perimeter_km = round(poly.length * 111, 2)
            else:
                try:
                    lat_sum = sum(p[0] for p in points)
                    lon_sum = sum(p[1] for p in points)
                    center = [lat_sum / len(points), lon_sum / len(points)]
                    s = 0.0
                    for i in range(len(points)):
                        j = (i + 1) % len(points)
                        s += points[i][1] * points[j][0] - points[j][1] * points[i][0]
                    area = abs(s) / 2 * 111 * 111
                    per = 0.0
                    for i in range(len(points)):
                        j = (i + 1) % len(points)
                        dlat = points[j][0] - points[i][0]
                        dlon = points[j][1] - points[i][1]
                        per += (dlat * dlat + dlon * dlon) ** 0.5 * 111
                    perimeter_km = round(per, 2)
                except Exception:
                    pass
        
        # Analyze properties within polygon
        analysis = {
            "polygon_info": {
                "area_sqkm": round(area, 2),
                "perimeter_km": perimeter_km,
                "center": center,
                "vertices": len(request.polygon)
            },
            "properties": await analyze_properties_in_polygon(poly, center),
            "demographics": await analyze_demographics_in_polygon(poly, center),
            "infrastructure": await analyze_infrastructure_in_polygon(poly, center),
            "investment_metrics": await calculate_investment_metrics(poly, center, dmpe),
            "recommendations": []
        }
        
        # Generate recommendations based on analysis
        if analysis["investment_metrics"]["growth_potential"] > 15:
            analysis["recommendations"].append({
                "type": "high_growth",
                "message": "This area shows high growth potential (>15% expected)",
                "confidence": 0.85
            })
        
        if analysis["infrastructure"]["metro_stations"] > 0:
            analysis["recommendations"].append({
                "type": "metro_connectivity",
                "message": f"Excellent connectivity with {analysis['infrastructure']['metro_stations']} metro stations",
                "confidence": 0.9
            })
        
        return {
            "status": "success",
            "analysis": analysis,
            "timestamp": str(pd.Timestamp.now())
        }
        
    except Exception as e:
        logger.error(f"Polygon analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/buffer/create")
async def create_buffer_zone(request: BufferZoneRequest) -> Dict[str, Any]:
    """
    Create buffer zones around a point with analysis
    """
    try:
        from backend.services.mappls_integration import MapplsService
        import math
        
        mappls = MapplsService()
        center_point = Point(request.center[1], request.center[0])  # (lng, lat)
        
        # Create buffer polygon
        # Approximate degrees per km at this latitude
        lat_rad = math.radians(request.center[0])
        m_per_deg_lat = 111132.954
        m_per_deg_lon = 111132.954 * math.cos(lat_rad)
        
        buffer_deg = request.radius_km * 1000 / ((m_per_deg_lat + m_per_deg_lon) / 2)
        buffer_poly = center_point.buffer(buffer_deg)
        
        # Get points on the buffer circumference
        analysis_points = []
        for i in range(request.analysis_points):
            angle = (2 * math.pi * i) / request.analysis_points
            x = request.center[1] + buffer_deg * math.cos(angle)
            y = request.center[0] + buffer_deg * math.sin(angle)
            analysis_points.append([y, x])
        
        # Analyze POIs within buffer
        pois = await analyze_pois_in_buffer(request.center, request.radius_km, mappls)
        
        return {
            "status": "success",
            "buffer": {
                "center": request.center,
                "radius_km": request.radius_km,
                "boundary_points": analysis_points,
                "area_sqkm": round(math.pi * request.radius_km ** 2, 2)
            },
            "analysis": {
                "total_pois": len(pois),
                "poi_categories": categorize_pois(pois),
                "accessibility_score": calculate_accessibility_score(pois),
                "investment_grade": determine_investment_grade(pois, request.radius_km)
            },
            "pois": pois[:20]  # Return top 20 POIs
        }
        
    except Exception as e:
        logger.error(f"Buffer zone error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/isochrone/generate")
async def generate_isochrone(request: IsochoneRequest) -> Dict[str, Any]:
    """
    Generate isochrone polygons showing reachable areas within given time
    """
    try:
        # This would integrate with a routing service like Mappls or Mapbox
        # For now, we'll create approximate circular isochrones
        
        isochrones = []
        speeds = {
            "walking": 5,    # km/h
            "driving": 40,   # km/h average in city
            "transit": 25    # km/h average
        }
        
        speed_kmh = speeds.get(request.mode, 30)
        
        for time_min in request.time_minutes:
            radius_km = (speed_kmh * time_min) / 60
            
            # Create circular approximation
            points = []
            for i in range(36):  # 36 points for smooth circle
                angle = (2 * math.pi * i) / 36
                lat = request.origin[0] + (radius_km / 111) * math.sin(angle)
                lng = request.origin[1] + (radius_km / 111) * math.cos(angle) / math.cos(math.radians(request.origin[0]))
                points.append([lat, lng])
            
            isochrones.append({
                "time_minutes": time_min,
                "mode": request.mode,
                "polygon": points,
                "radius_km": round(radius_km, 2)
            })
        
        return {
            "status": "success",
            "origin": request.origin,
            "isochrones": isochrones,
            "coverage_analysis": {
                "total_area_sqkm": round(math.pi * (isochrones[-1]["radius_km"] ** 2), 2),
                "reachable_zones": await get_reachable_zones(request.origin, isochrones)
            }
        }
        
    except Exception as e:
        logger.error(f"Isochrone generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/layers/data")
async def get_layer_data(request: LayerRequest) -> Dict[str, Any]:
    """
    Get data for specific map layers (heatmap, clusters, etc.)
    """
    try:
        from backend.services.mappls_integration import MapplsService
        import pandas as pd
        import numpy as np
        
        mappls = MapplsService()
        
        layer_data = {
            "type": request.layer_type,
            "data": []
        }
        
        if request.layer_type == "heatmap":
            # Generate heatmap data for property prices
            properties = await get_properties_in_bounds(request.bounds)
            layer_data["data"] = [
                {
                    "lat": p["latitude"],
                    "lng": p["longitude"],
                    "weight": p["price"] / 10000000  # Normalize price
                }
                for p in properties
                if p.get("latitude") and p.get("longitude")
            ]
            
        elif request.layer_type == "clusters":
            # Get property clusters
            properties = await get_properties_in_bounds(request.bounds)
            clusters = mappls.identify_clusters(properties)
            layer_data["data"] = clusters
            
        elif request.layer_type == "transit":
            # Get transit routes and stops
            if request.bounds:
                center = [
                    (request.bounds[0][0] + request.bounds[1][0]) / 2,
                    (request.bounds[0][1] + request.bounds[1][1]) / 2
                ]
            else:
                center = [12.9716, 77.5946]  # Default Bangalore
            
            transit_data = mappls.nearby_search(
                center[0], center[1],
                keywords="metro,bus stop,railway",
                radius=5000
            )
            layer_data["data"] = transit_data
            
        elif request.layer_type == "amenities":
            # Get amenities layer
            if request.bounds:
                center = [
                    (request.bounds[0][0] + request.bounds[1][0]) / 2,
                    (request.bounds[0][1] + request.bounds[1][1]) / 2
                ]
            else:
                center = [12.9716, 77.5946]
            
            amenities = mappls.nearby_search(
                center[0], center[1],
                keywords="hospital,school,mall,park",
                radius=3000
            )
            layer_data["data"] = amenities
        
        return {
            "status": "success",
            "layer": layer_data,
            "item_count": len(layer_data["data"]),
            "zoom_level": request.zoom_level
        }
        
    except Exception as e:
        logger.error(f"Layer data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compare/zones")
async def compare_zones(
    zones: List[str] = Query(...),
    metrics: List[str] = Query(default=["price", "growth", "amenities"])
) -> Dict[str, Any]:
    """
    Compare multiple zones/areas
    """
    try:
        from backend.services.multi_agent_orchestrator import ValoraOrchestrator
        
        orchestrator = ValoraOrchestrator()
        comparisons = []
        
        for zone in zones:
            # Get zone analysis
            analysis = await orchestrator.map_agent.analyze_zones(
                city="Bangalore",  # Default city
                budget={"min": 0, "max": 100000000},
                property_type="all",
                amenities=["all"]
            )
            
            # Extract comparison metrics
            zone_data = {
                "zone": zone,
                "metrics": {}
            }
            
            if "price" in metrics:
                zone_data["metrics"]["avg_price_sqft"] = get_zone_price(zone)
            
            if "growth" in metrics:
                zone_data["metrics"]["growth_potential"] = get_zone_growth(zone)
            
            if "amenities" in metrics:
                zone_data["metrics"]["amenity_score"] = get_zone_amenities(zone)
            
            comparisons.append(zone_data)
        
        # Rank zones by composite score
        for comp in comparisons:
            comp["composite_score"] = calculate_composite_score(comp["metrics"])
        
        comparisons.sort(key=lambda x: x["composite_score"], reverse=True)
        
        return {
            "status": "success",
            "comparisons": comparisons,
            "best_zone": comparisons[0]["zone"] if comparisons else None,
            "metrics_analyzed": metrics
        }
        
    except Exception as e:
        logger.error(f"Zone comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def analyze_properties_in_polygon(poly: Polygon, center: List[float]) -> Dict[str, Any]:
    """Analyze properties within a polygon"""
    # Simulated analysis - would query actual database
    import random
    
    return {
        "total_properties": random.randint(50, 500),
        "avg_price_sqft": random.randint(4000, 12000),
        "property_types": {
            "apartments": random.randint(20, 200),
            "villas": random.randint(5, 50),
            "plots": random.randint(10, 100)
        },
        "price_range": {
            "min": 3000000,
            "max": 50000000,
            "median": 12000000
        }
    }

async def analyze_demographics_in_polygon(poly: Polygon, center: List[float]) -> Dict[str, Any]:
    """Analyze demographics within a polygon"""
    import random
    
    return {
        "population_density": random.randint(5000, 25000),
        "avg_income_level": random.choice(["High", "Medium-High", "Medium"]),
        "age_distribution": {
            "18-30": 30,
            "31-45": 40,
            "46-60": 20,
            "60+": 10
        },
        "employment_hubs": random.randint(5, 20)
    }

async def analyze_infrastructure_in_polygon(poly: Polygon, center: List[float]) -> Dict[str, Any]:
    """Analyze infrastructure within a polygon"""
    import random
    
    return {
        "metro_stations": random.randint(0, 3),
        "bus_stops": random.randint(10, 50),
        "hospitals": random.randint(2, 10),
        "schools": random.randint(5, 25),
        "malls": random.randint(1, 5),
        "connectivity_score": random.uniform(6, 9)
    }

async def calculate_investment_metrics(poly: Polygon, center: List[float], dmpe) -> Dict[str, Any]:
    """Calculate investment metrics for a polygon"""
    import random
    
    return {
        "growth_potential": random.uniform(10, 25),
        "rental_yield": random.uniform(3, 6),
        "appreciation_forecast_3y": random.uniform(25, 45),
        "investment_grade": random.choice(["A+", "A", "B+", "B"]),
        "risk_score": random.uniform(0.2, 0.6)
    }

async def analyze_pois_in_buffer(center: List[float], radius_km: float, mappls) -> List[Dict[str, Any]]:
    """Analyze POIs within a buffer zone"""
    pois = mappls.nearby_search(
        center[0], center[1],
        radius=int(radius_km * 1000)
    )
    return pois

def categorize_pois(pois: List[Dict[str, Any]]) -> Dict[str, int]:
    """Categorize POIs by type"""
    categories = {}
    for poi in pois:
        cat = poi.get("category", "other")
        categories[cat] = categories.get(cat, 0) + 1
    return categories

def calculate_accessibility_score(pois: List[Dict[str, Any]]) -> float:
    """Calculate accessibility score based on POIs"""
    score = min(10, len(pois) / 10)  # Simple scoring
    return round(score, 2)

def determine_investment_grade(pois: List[Dict[str, Any]], radius_km: float) -> str:
    """Determine investment grade based on POI density"""
    density = len(pois) / (3.14 * radius_km ** 2)
    if density > 50:
        return "A+"
    elif density > 30:
        return "A"
    elif density > 15:
        return "B+"
    else:
        return "B"

async def get_reachable_zones(origin: List[float], isochrones: List[Dict]) -> List[str]:
    """Get zones reachable within isochrones"""
    zones = ["Whitefield", "Koramangala", "Hebbal", "Electronic City"]
    # Would calculate actual reachable zones
    return zones[:len(isochrones)]

async def get_properties_in_bounds(bounds: Optional[List[List[float]]]) -> List[Dict[str, Any]]:
    """Get properties within map bounds"""
    # Simulated - would query actual database
    import random
    
    properties = []
    for i in range(20):
        properties.append({
            "id": f"prop_{i}",
            "latitude": 12.9716 + random.uniform(-0.1, 0.1),
            "longitude": 77.5946 + random.uniform(-0.1, 0.1),
            "price": random.randint(5000000, 50000000),
            "area_sqft": random.randint(800, 3000),
            "type": random.choice(["apartment", "villa", "plot"])
        })
    return properties

def get_zone_price(zone: str) -> float:
    """Get average price for a zone"""
    zone_prices = {
        "whitefield": 6500,
        "koramangala": 9000,
        "hebbal": 7200,
        "electronic city": 5500
    }
    return zone_prices.get(zone.lower(), 6000)

def get_zone_growth(zone: str) -> float:
    """Get growth potential for a zone"""
    import random
    return random.uniform(10, 25)

def get_zone_amenities(zone: str) -> float:
    """Get amenity score for a zone"""
    import random
    return random.uniform(6, 9)

def calculate_composite_score(metrics: Dict[str, float]) -> float:
    """Calculate composite score from metrics"""
    weights = {
        "avg_price_sqft": 0.3,
        "growth_potential": 0.4,
        "amenity_score": 0.3
    }
    
    score = 0
    for key, weight in weights.items():
        if key in metrics:
            # Normalize and weight
            if key == "avg_price_sqft":
                # Lower price is better
                normalized = 10 - (metrics[key] / 1000)
            else:
                # Higher is better
                normalized = metrics[key]
            score += normalized * weight
    
    return round(score, 2)

import math
import pandas as pd
