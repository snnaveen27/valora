"""
Valora AI - Shared Geo Utilities
Centralized geographic calculations to avoid duplication.

Previously duplicated across 19+ files.
"""

import math
from typing import Tuple, Optional


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    
    Args:
        lat1, lng1: First point coordinates (degrees)
        lat2, lng2: Second point coordinates (degrees)
        
    Returns:
        Distance in meters
    """
    R = 6371000  # Earth's radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_phi / 2) ** 2 + 
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the initial bearing from point 1 to point 2.
    
    Args:
        lat1, lng1: Start point coordinates (degrees)
        lat2, lng2: End point coordinates (degrees)
        
    Returns:
        Bearing in degrees (0-360, 0 = North, 90 = East)
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lng2 - lng1)
    
    x = math.sin(delta_lambda) * math.cos(phi2)
    y = (math.cos(phi1) * math.sin(phi2) - 
         math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda))
    
    theta = math.atan2(x, y)
    bearing_deg = (math.degrees(theta) + 360) % 360
    
    return bearing_deg


def direction_from_bearing(bearing_deg: float) -> str:
    """
    Convert bearing in degrees to cardinal direction.
    
    Args:
        bearing_deg: Bearing in degrees (0-360)
        
    Returns:
        Cardinal direction string (N, NE, E, SE, S, SW, W, NW)
    """
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = round(bearing_deg / 45) % 8
    return directions[index]


def meters_to_degrees(meters: float, latitude: float = 12.97) -> float:
    """
    Convert meters to approximate degrees at a given latitude.
    
    Args:
        meters: Distance in meters
        latitude: Reference latitude (default: Bangalore)
        
    Returns:
        Approximate degrees
    """
    # 1 degree latitude ≈ 111km
    # 1 degree longitude ≈ 111km * cos(latitude)
    lat_deg = meters / 111000
    return lat_deg


def degrees_to_meters(degrees: float, latitude: float = 12.97) -> float:
    """
    Convert degrees to approximate meters at a given latitude.
    
    Args:
        degrees: Distance in degrees
        latitude: Reference latitude (default: Bangalore)
        
    Returns:
        Approximate meters
    """
    return degrees * 111000


def bounding_box(lat: float, lng: float, radius_m: float) -> Tuple[float, float, float, float]:
    """
    Calculate a bounding box around a point.
    
    Args:
        lat, lng: Center point
        radius_m: Radius in meters
        
    Returns:
        Tuple of (min_lat, max_lat, min_lng, max_lng)
    """
    delta = meters_to_degrees(radius_m, lat)
    # Adjust for longitude at this latitude
    lng_delta = delta / math.cos(math.radians(lat))
    
    return (
        lat - delta,
        lat + delta,
        lng - lng_delta,
        lng + lng_delta
    )


def point_in_bounding_box(
    lat: float, 
    lng: float, 
    min_lat: float, 
    max_lat: float, 
    min_lng: float, 
    max_lng: float
) -> bool:
    """Check if a point is within a bounding box."""
    return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng


def midpoint(lat1: float, lng1: float, lat2: float, lng2: float) -> Tuple[float, float]:
    """
    Calculate the midpoint between two coordinates.
    
    Returns:
        Tuple of (lat, lng) for the midpoint
    """
    return ((lat1 + lat2) / 2, (lng1 + lng2) / 2)


def destination_point(lat: float, lng: float, bearing_deg: float, distance_m: float) -> Tuple[float, float]:
    """
    Calculate the destination point given start, bearing, and distance.
    
    Args:
        lat, lng: Start point
        bearing_deg: Bearing in degrees
        distance_m: Distance in meters
        
    Returns:
        Tuple of (lat, lng) for destination
    """
    R = 6371000  # Earth radius in meters
    
    phi1 = math.radians(lat)
    lambda1 = math.radians(lng)
    theta = math.radians(bearing_deg)
    delta = distance_m / R
    
    phi2 = math.asin(
        math.sin(phi1) * math.cos(delta) +
        math.cos(phi1) * math.sin(delta) * math.cos(theta)
    )
    
    lambda2 = lambda1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2)
    )
    
    return (math.degrees(phi2), math.degrees(lambda2))


# Bangalore-specific constants
BANGALORE_CENTER = (12.9716, 77.5946)
BANGALORE_BOUNDS = {
    'min_lat': 12.7,
    'max_lat': 13.2,
    'min_lng': 77.3,
    'max_lng': 77.9
}


def is_in_bangalore(lat: float, lng: float) -> bool:
    """Check if coordinates are within Bangalore bounds."""
    return (
        BANGALORE_BOUNDS['min_lat'] <= lat <= BANGALORE_BOUNDS['max_lat'] and
        BANGALORE_BOUNDS['min_lng'] <= lng <= BANGALORE_BOUNDS['max_lng']
    )
