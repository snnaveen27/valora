"""
City Configuration Module
Centralized configuration for multi-city support.
Add new cities here to scale the platform.
"""

import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class SupportedCity(Enum):
    """Supported cities in the platform"""
    BANGALORE = "bangalore"
    MUMBAI = "mumbai"
    DELHI = "delhi"
    HYDERABAD = "hyderabad"
    CHENNAI = "chennai"
    PUNE = "pune"
    KOLKATA = "kolkata"


@dataclass
class CityBoundingBox:
    """Geographic bounding box for a city"""
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    
    def contains(self, lat: float, lon: float) -> bool:
        """Check if a point is within this bounding box"""
        return (self.min_lat <= lat <= self.max_lat and 
                self.min_lon <= lon <= self.max_lon)
    
    def center(self) -> tuple:
        """Get center point of bounding box"""
        return (
            (self.min_lat + self.max_lat) / 2,
            (self.min_lon + self.max_lon) / 2
        )


@dataclass
class CityConfig:
    """Configuration for a single city"""
    # Basic info
    city_id: str
    city_name: str
    state: str
    country: str = "India"
    
    # Geographic
    center_lat: float = 0.0
    center_lon: float = 0.0
    default_zoom: int = 12
    bounding_box: Optional[CityBoundingBox] = None
    
    # Market characteristics
    currency: str = "INR"
    currency_symbol: str = "₹"
    avg_price_sqft_range: tuple = (3000, 15000)
    typical_rental_yield: tuple = (2.5, 5.0)
    
    # Data sources
    gis_table_prefix: str = ""
    ward_table: str = ""
    zone_table: str = ""
    
    # Sample localities for testing/defaults
    sample_localities: List[str] = field(default_factory=list)
    
    # Infrastructure thresholds (city-specific)
    metro_impact_radius_km: float = 5.0
    highway_impact_radius_km: float = 10.0
    
    # Active status
    is_active: bool = True
    data_available: bool = False


# City configurations
CITY_CONFIGS: Dict[str, CityConfig] = {
    "bangalore": CityConfig(
        city_id="bangalore",
        city_name="Bangalore",
        state="Karnataka",
        center_lat=12.9716,
        center_lon=77.5946,
        default_zoom=12,
        bounding_box=CityBoundingBox(
            min_lat=12.7342,
            max_lat=13.1737,
            min_lon=77.3791,
            max_lon=77.8826
        ),
        avg_price_sqft_range=(4000, 12000),
        typical_rental_yield=(2.5, 4.5),
        gis_table_prefix="gis_bbmp",
        ward_table="gis_bbmp_wards",
        zone_table="gis_bbmp_zones",
        sample_localities=[
            "Koramangala", "Whitefield", "Electronic City", 
            "Indiranagar", "HSR Layout", "BTM Layout",
            "Marathahalli", "Jayanagar", "Bannerghatta Road",
            "Hebbal", "Yelahanka", "Sarjapur Road"
        ],
        metro_impact_radius_km=5.0,
        is_active=True,
        data_available=True
    ),
    
    "mumbai": CityConfig(
        city_id="mumbai",
        city_name="Mumbai",
        state="Maharashtra",
        center_lat=19.0760,
        center_lon=72.8777,
        default_zoom=11,
        bounding_box=CityBoundingBox(
            min_lat=18.8928,
            max_lat=19.2704,
            min_lon=72.7758,
            max_lon=72.9866
        ),
        avg_price_sqft_range=(15000, 50000),
        typical_rental_yield=(2.0, 3.5),
        gis_table_prefix="gis_mcgm",
        ward_table="gis_mcgm_wards",
        zone_table="gis_mcgm_zones",
        sample_localities=[
            "Bandra", "Andheri", "Powai", "Worli",
            "Lower Parel", "Goregaon", "Thane", "Navi Mumbai"
        ],
        metro_impact_radius_km=3.0,  # Denser city, smaller impact radius
        is_active=True,
        data_available=False  # Data not yet loaded
    ),
    
    "delhi": CityConfig(
        city_id="delhi",
        city_name="Delhi NCR",
        state="Delhi",
        center_lat=28.6139,
        center_lon=77.2090,
        default_zoom=11,
        bounding_box=CityBoundingBox(
            min_lat=28.4041,
            max_lat=28.8837,
            min_lon=76.8381,
            max_lon=77.3467
        ),
        avg_price_sqft_range=(8000, 25000),
        typical_rental_yield=(2.0, 4.0),
        gis_table_prefix="gis_dda",
        ward_table="gis_dda_wards",
        zone_table="gis_dda_zones",
        sample_localities=[
            "Dwarka", "Gurgaon", "Noida", "Greater Noida",
            "Vasant Kunj", "Saket", "Rohini", "Faridabad"
        ],
        is_active=True,
        data_available=False
    ),
    
    "hyderabad": CityConfig(
        city_id="hyderabad",
        city_name="Hyderabad",
        state="Telangana",
        center_lat=17.3850,
        center_lon=78.4867,
        default_zoom=12,
        bounding_box=CityBoundingBox(
            min_lat=17.2403,
            max_lat=17.5603,
            min_lon=78.2478,
            max_lon=78.6578
        ),
        avg_price_sqft_range=(4000, 10000),
        typical_rental_yield=(3.0, 5.0),
        gis_table_prefix="gis_ghmc",
        ward_table="gis_ghmc_wards",
        zone_table="gis_ghmc_zones",
        sample_localities=[
            "Gachibowli", "HITEC City", "Kondapur", "Madhapur",
            "Banjara Hills", "Jubilee Hills", "Kukatpally", "Miyapur"
        ],
        is_active=True,
        data_available=False
    ),
    
    "chennai": CityConfig(
        city_id="chennai",
        city_name="Chennai",
        state="Tamil Nadu",
        center_lat=13.0827,
        center_lon=80.2707,
        default_zoom=12,
        bounding_box=CityBoundingBox(
            min_lat=12.8996,
            max_lat=13.2354,
            min_lon=80.0769,
            max_lon=80.3089
        ),
        avg_price_sqft_range=(5000, 12000),
        typical_rental_yield=(3.0, 5.0),
        gis_table_prefix="gis_gcc",
        ward_table="gis_gcc_wards",
        zone_table="gis_gcc_zones",
        sample_localities=[
            "OMR", "Adyar", "Velachery", "Anna Nagar",
            "T. Nagar", "Porur", "Tambaram", "Sholinganallur"
        ],
        is_active=True,
        data_available=False
    ),
    
    "pune": CityConfig(
        city_id="pune",
        city_name="Pune",
        state="Maharashtra",
        center_lat=18.5204,
        center_lon=73.8567,
        default_zoom=12,
        bounding_box=CityBoundingBox(
            min_lat=18.4088,
            max_lat=18.6346,
            min_lon=73.7316,
            max_lon=73.9876
        ),
        avg_price_sqft_range=(5000, 12000),
        typical_rental_yield=(3.0, 5.0),
        gis_table_prefix="gis_pmc",
        ward_table="gis_pmc_wards",
        zone_table="gis_pmc_zones",
        sample_localities=[
            "Hinjewadi", "Kharadi", "Wakad", "Baner",
            "Koregaon Park", "Viman Nagar", "Hadapsar", "Kothrud"
        ],
        is_active=True,
        data_available=False
    ),
}


class CityManager:
    """
    Manager class for handling multi-city operations.
    Use this class to get city configurations throughout the application.
    """
    
    _instance = None
    _current_city: str = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._current_city = os.getenv("DEFAULT_CITY", "bangalore")
        return cls._instance
    
    @property
    def current_city(self) -> str:
        """Get the current active city"""
        return self._current_city
    
    @current_city.setter
    def current_city(self, city_id: str):
        """Set the current active city"""
        if city_id.lower() not in CITY_CONFIGS:
            raise ValueError(f"City '{city_id}' not supported. Available: {list(CITY_CONFIGS.keys())}")
        self._current_city = city_id.lower()
    
    def get_config(self, city_id: Optional[str] = None) -> CityConfig:
        """Get configuration for a city"""
        city_id = (city_id or self._current_city).lower()
        if city_id not in CITY_CONFIGS:
            raise ValueError(f"City '{city_id}' not supported")
        return CITY_CONFIGS[city_id]
    
    def get_center(self, city_id: Optional[str] = None) -> tuple:
        """Get center coordinates for a city"""
        config = self.get_config(city_id)
        return (config.center_lat, config.center_lon)
    
    def get_bounding_box(self, city_id: Optional[str] = None) -> CityBoundingBox:
        """Get bounding box for a city"""
        return self.get_config(city_id).bounding_box
    
    def get_sample_localities(self, city_id: Optional[str] = None) -> List[str]:
        """Get sample localities for a city"""
        return self.get_config(city_id).sample_localities
    
    def get_gis_tables(self, city_id: Optional[str] = None) -> Dict[str, str]:
        """Get GIS table names for a city"""
        config = self.get_config(city_id)
        return {
            "prefix": config.gis_table_prefix,
            "wards": config.ward_table,
            "zones": config.zone_table
        }
    
    def list_active_cities(self) -> List[str]:
        """List all active cities"""
        return [city_id for city_id, config in CITY_CONFIGS.items() if config.is_active]
    
    def list_cities_with_data(self) -> List[str]:
        """List cities that have data loaded"""
        return [city_id for city_id, config in CITY_CONFIGS.items() if config.data_available]
    
    def is_point_in_city(self, lat: float, lon: float, city_id: Optional[str] = None) -> bool:
        """Check if a point is within a city's bounding box"""
        bbox = self.get_bounding_box(city_id)
        return bbox.contains(lat, lon) if bbox else False
    
    def detect_city_from_coordinates(self, lat: float, lon: float) -> Optional[str]:
        """Detect which city a coordinate belongs to"""
        for city_id, config in CITY_CONFIGS.items():
            if config.bounding_box and config.bounding_box.contains(lat, lon):
                return city_id
        return None


# Global instance for easy access
city_manager = CityManager()


# Convenience functions
def get_city_config(city_id: Optional[str] = None) -> CityConfig:
    """Get city configuration"""
    return city_manager.get_config(city_id)


def get_default_center(city_id: Optional[str] = None) -> tuple:
    """Get default center coordinates"""
    return city_manager.get_center(city_id)


def get_sample_areas(city_id: Optional[str] = None) -> List[str]:
    """Get sample localities for a city"""
    return city_manager.get_sample_localities(city_id)
