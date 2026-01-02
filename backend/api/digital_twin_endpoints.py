"""
Digital Twin API Endpoints
Provides 3D building data, floor information, and environmental metrics for visualization.
Part of VALORA City Intelligence Engine
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import random

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/digital-twin", tags=["Digital Twin"])


# ===================== Request/Response Models =====================

class BuildingRequest(BaseModel):
    property_id: str = Field(..., description="Property ID")
    include_floors: bool = Field(default=True, description="Include floor-level data")
    include_environmental: bool = Field(default=True, description="Include environmental metrics")


class FloorUpdateRequest(BaseModel):
    property_id: str
    floor_number: int
    occupancy: Optional[float] = None
    avg_price: Optional[float] = None
    avg_rent: Optional[float] = None


# ===================== Building Data Endpoints =====================

@router.get("/building/{property_id}")
async def get_building_data(
    property_id: str,
    include_floors: bool = Query(default=True),
    include_environmental: bool = Query(default=True)
) -> Dict[str, Any]:
    """Get complete 3D building data for digital twin visualization"""
    
    # In production, this would fetch from database
    # For now, generate realistic building data
    
    # Determine building characteristics based on property_id hash
    seed = hash(property_id) % 1000
    random.seed(seed)
    
    floors = random.randint(8, 25)
    units_per_floor = random.choice([2, 4, 6, 8])
    base_price = random.randint(6000, 15000)
    year_built = random.randint(2015, 2024)
    
    building_data = {
        "property_id": property_id,
        "name": f"Property {property_id[:8]}",
        "address": "Whitefield, Bangalore",
        
        # 3D Model parameters
        "model": {
            "floors": floors,
            "width": 4 + (units_per_floor / 2),
            "depth": 4 + (units_per_floor / 4),
            "floor_height": 0.4,
            "gap": 0.05
        },
        
        # Building metadata
        "metadata": {
            "total_floors": floors,
            "total_units": floors * units_per_floor,
            "units_per_floor": units_per_floor,
            "year_built": year_built,
            "building_age": 2024 - year_built,
            "price_per_sqft": base_price,
            "avg_unit_size_sqft": random.randint(1000, 2500),
            "total_built_up_sqft": floors * units_per_floor * random.randint(1200, 2000),
            "occupancy_rate": round(random.uniform(0.65, 0.95), 2),
            "developer": random.choice(["Prestige", "Sobha", "Brigade", "Godrej", "Puravankara"]),
            "building_type": random.choice(["Residential", "Commercial", "Mixed Use"]),
            "amenities": random.sample([
                "Swimming Pool", "Gym", "Clubhouse", "Children's Play Area",
                "Jogging Track", "Tennis Court", "24/7 Security", "Power Backup",
                "Covered Parking", "Landscaped Gardens", "Community Hall", "Indoor Games"
            ], k=random.randint(5, 8))
        }
    }
    
    # Add floor-level data
    if include_floors:
        building_data["floors"] = []
        for i in range(floors):
            floor_num = i + 1
            # Higher floors typically have higher prices and occupancy variance
            price_multiplier = 1 + (i * 0.02)  # 2% increase per floor
            
            floor_data = {
                "floor_number": floor_num,
                "units": units_per_floor,
                "occupancy": round(random.uniform(0.5, 1.0), 2),
                "avg_price": int(base_price * price_multiplier * random.randint(1000, 1500)),
                "avg_rent": int(25000 + (i * 1500) + random.randint(-2000, 3000)),
                "price_per_sqft": int(base_price * price_multiplier),
                "available_units": random.randint(0, units_per_floor),
                "unit_types": get_unit_types(floor_num, floors),
                "amenities": get_floor_amenities(floor_num, floors),
                "view_direction": get_view_direction(floor_num, floors),
                "floor_plan_url": f"/api/floor-plans/{property_id}/floor-{floor_num}.pdf"
            }
            building_data["floors"].append(floor_data)
    
    # Add environmental data
    if include_environmental:
        building_data["environmental"] = {
            "temperature": round(random.uniform(24, 32), 1),
            "humidity": random.randint(50, 80),
            "aqi": random.randint(30, 120),
            "noise_level_db": random.randint(40, 70),
            "sunlight_hours": round(random.uniform(4, 8), 1),
            "ventilation_score": round(random.uniform(0.6, 1.0), 2),
            "green_cover_nearby_pct": random.randint(10, 40),
            "last_updated": datetime.now().isoformat()
        }
    
    # Investment metrics
    building_data["investment"] = {
        "rental_yield_pct": round(random.uniform(2.5, 4.5), 2),
        "appreciation_1y_pct": round(random.uniform(5, 15), 1),
        "appreciation_3y_pct": round(random.uniform(15, 40), 1),
        "liquidity_score": round(random.uniform(0.6, 0.95), 2),
        "investment_grade": random.choice(["A+", "A", "A-", "B+", "B"]),
        "risk_score": round(random.uniform(0.15, 0.40), 2)
    }
    
    return {
        "success": True,
        "data": building_data
    }


@router.get("/building/{property_id}/floor/{floor_number}")
async def get_floor_details(
    property_id: str,
    floor_number: int
) -> Dict[str, Any]:
    """Get detailed information for a specific floor"""
    
    seed = hash(f"{property_id}-{floor_number}") % 1000
    random.seed(seed)
    
    units = []
    unit_count = random.choice([2, 4, 6])
    
    for i in range(unit_count):
        unit = {
            "unit_id": f"{property_id}-{floor_number}-{i+1}",
            "unit_number": f"{floor_number}{chr(65+i)}",  # e.g., "5A", "5B"
            "type": random.choice(["2BHK", "3BHK", "4BHK"]),
            "size_sqft": random.randint(1000, 2500),
            "facing": random.choice(["North", "South", "East", "West", "North-East", "South-West"]),
            "price": random.randint(6000000, 20000000),
            "rent": random.randint(25000, 75000),
            "status": random.choice(["available", "occupied", "reserved", "sold"]),
            "bedrooms": random.randint(2, 4),
            "bathrooms": random.randint(2, 4),
            "balconies": random.randint(1, 3),
            "parking_slots": random.randint(1, 2),
            "furnishing": random.choice(["Unfurnished", "Semi-Furnished", "Fully Furnished"]),
            "possession_date": "Immediate" if random.random() > 0.5 else "3 months",
            "floor_plan_url": f"/api/floor-plans/{property_id}/unit-{floor_number}{chr(65+i)}.pdf"
        }
        units.append(unit)
    
    return {
        "success": True,
        "data": {
            "property_id": property_id,
            "floor_number": floor_number,
            "total_units": unit_count,
            "available_units": sum(1 for u in units if u["status"] == "available"),
            "occupied_units": sum(1 for u in units if u["status"] == "occupied"),
            "units": units,
            "common_areas": {
                "lobby_size_sqft": random.randint(200, 500),
                "elevator_count": random.randint(2, 4),
                "staircase_count": 2,
                "fire_exit": True
            },
            "utilities": {
                "power_backup": "100%",
                "water_supply": "24/7",
                "gas_pipeline": random.choice([True, False]),
                "garbage_chute": floor_number > 3
            }
        }
    }


@router.get("/building/{property_id}/environmental")
async def get_environmental_data(
    property_id: str,
    floor_number: Optional[int] = None
) -> Dict[str, Any]:
    """Get real-time environmental data for the building"""
    
    seed = hash(f"{property_id}-env") % 1000
    random.seed(seed)
    
    # Base environmental data
    env_data = {
        "property_id": property_id,
        "timestamp": datetime.now().isoformat(),
        "overall": {
            "temperature_c": round(random.uniform(24, 32), 1),
            "humidity_pct": random.randint(50, 80),
            "aqi": random.randint(30, 120),
            "aqi_category": get_aqi_category(random.randint(30, 120)),
            "uv_index": random.randint(3, 10),
            "wind_speed_kmh": round(random.uniform(5, 25), 1),
            "wind_direction": random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
        },
        "energy": {
            "solar_generation_kw": round(random.uniform(0, 50), 1) if 6 <= datetime.now().hour <= 18 else 0,
            "grid_consumption_kw": round(random.uniform(100, 300), 1),
            "backup_power_pct": random.randint(80, 100),
            "energy_efficiency_rating": random.choice(["A", "A+", "B", "B+"])
        },
        "water": {
            "tank_level_pct": random.randint(40, 95),
            "daily_consumption_liters": random.randint(10000, 50000),
            "recycled_water_pct": random.randint(20, 60),
            "rainwater_harvested_liters": random.randint(0, 5000)
        },
        "safety": {
            "fire_system_status": "Active",
            "cctv_cameras_online": random.randint(20, 40),
            "security_personnel_on_duty": random.randint(4, 8),
            "last_safety_drill": "2024-11-15"
        }
    }
    
    # Add floor-specific data if requested
    if floor_number:
        env_data["floor_specific"] = {
            "floor_number": floor_number,
            "temperature_c": round(random.uniform(23, 30), 1),
            "humidity_pct": random.randint(45, 75),
            "noise_level_db": random.randint(35, 60),
            "light_level_lux": random.randint(200, 800),
            "co2_level_ppm": random.randint(400, 800),
            "occupancy_detected": random.choice([True, False])
        }
    
    return {
        "success": True,
        "data": env_data
    }


@router.get("/buildings/nearby")
async def get_nearby_buildings(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius_km: float = Query(default=2.0, description="Search radius in km"),
    limit: int = Query(default=10, description="Maximum results")
) -> Dict[str, Any]:
    """Get nearby buildings for 3D city view"""
    
    # Generate mock nearby buildings
    buildings = []
    for i in range(min(limit, 15)):
        offset_lat = random.uniform(-0.01, 0.01) * radius_km
        offset_lng = random.uniform(-0.01, 0.01) * radius_km
        
        building = {
            "property_id": f"prop_{i+1:04d}",
            "name": f"{random.choice(['Prestige', 'Sobha', 'Brigade', 'Embassy'])} {random.choice(['Towers', 'Heights', 'Residency', 'Park'])}",
            "location": {
                "lat": lat + offset_lat,
                "lng": lng + offset_lng
            },
            "distance_km": round(random.uniform(0.1, radius_km), 2),
            "floors": random.randint(8, 25),
            "price_per_sqft": random.randint(6000, 15000),
            "occupancy": round(random.uniform(0.6, 0.95), 2),
            "building_type": random.choice(["Residential", "Commercial", "Mixed Use"]),
            "has_3d_model": random.choice([True, True, True, False])  # 75% have 3D models
        }
        buildings.append(building)
    
    # Sort by distance
    buildings.sort(key=lambda x: x["distance_km"])
    
    return {
        "success": True,
        "center": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
        "count": len(buildings),
        "buildings": buildings
    }


@router.get("/building/{property_id}/comparison")
async def get_building_comparison(
    property_id: str,
    compare_with: List[str] = Query(default=[], description="Property IDs to compare with")
) -> Dict[str, Any]:
    """Compare multiple buildings for investment analysis"""
    
    if not compare_with:
        compare_with = [f"prop_{i:04d}" for i in range(1, 4)]
    
    comparisons = []
    all_ids = [property_id] + compare_with[:4]  # Max 5 buildings
    
    for pid in all_ids:
        seed = hash(pid) % 1000
        random.seed(seed)
        
        comp = {
            "property_id": pid,
            "name": f"{random.choice(['Prestige', 'Sobha', 'Brigade'])} {random.choice(['Towers', 'Heights'])}",
            "price_per_sqft": random.randint(6000, 15000),
            "floors": random.randint(8, 25),
            "total_units": random.randint(50, 200),
            "occupancy_pct": random.randint(60, 95),
            "rental_yield_pct": round(random.uniform(2.5, 4.5), 2),
            "appreciation_1y_pct": round(random.uniform(5, 15), 1),
            "investment_grade": random.choice(["A+", "A", "A-", "B+", "B"]),
            "amenities_count": random.randint(5, 12),
            "year_built": random.randint(2015, 2024),
            "developer_rating": round(random.uniform(3.5, 5.0), 1)
        }
        comparisons.append(comp)
    
    return {
        "success": True,
        "primary": property_id,
        "comparisons": comparisons
    }


# ===================== Helper Functions =====================

def get_unit_types(floor_num: int, total_floors: int) -> List[str]:
    """Get unit types based on floor level"""
    if floor_num >= total_floors - 2:  # Top floors
        return ["3BHK", "4BHK", "Penthouse"]
    elif floor_num >= total_floors // 2:  # Upper half
        return ["2BHK", "3BHK", "4BHK"]
    else:  # Lower half
        return ["2BHK", "3BHK"]


def get_floor_amenities(floor_num: int, total_floors: int) -> List[str]:
    """Get amenities based on floor level"""
    base = ["Balcony", "Modular Kitchen"]
    if floor_num >= total_floors - 3:
        base.extend(["Premium View", "Private Terrace"])
    if floor_num >= total_floors // 2:
        base.append("Study Room")
    return base


def get_view_direction(floor_num: int, total_floors: int) -> str:
    """Get view quality based on floor level"""
    if floor_num >= total_floors - 2:
        return "Panoramic City View"
    elif floor_num >= total_floors // 2:
        return "Partial City View"
    else:
        return "Garden View"


def get_aqi_category(aqi: int) -> str:
    """Get AQI category"""
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Moderate"
    elif aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    elif aqi <= 200:
        return "Unhealthy"
    else:
        return "Very Unhealthy"
