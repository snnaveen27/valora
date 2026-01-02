"""
Property endpoints for fetching and analyzing properties
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from sqlalchemy import text
from backend.database.multiconnection import mdb
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/properties", tags=["properties"])

@router.get("/all")
async def get_all_properties(
    limit: int = Query(1000, description="Maximum number of properties to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """
    Fetch all properties with their locations
    """
    try:
        with mdb.spatial() as session:
            result = session.execute(text("""
                SELECT 
                    property_id,
                    ST_Y(location::geometry) as latitude,
                    ST_X(location::geometry) as longitude,
                    city,
                    locality
                FROM property_locations
                ORDER BY property_id
                LIMIT :limit OFFSET :offset
            """), {'limit': limit, 'offset': offset})
            
            properties = []
            for row in result:
                properties.append({
                    'property_id': row[0],
                    'latitude': row[1],
                    'longitude': row[2],
                    'lat': row[1],  # Alias for compatibility
                    'lon': row[2],  # Alias for compatibility
                    'city': row[3],
                    'locality': row[4]
                })
            
            return {
                'properties': properties,
                'count': len(properties),
                'limit': limit,
                'offset': offset
            }
            
    except Exception as e:
        logger.error(f"Error fetching properties: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/by-area")
async def get_properties_by_area(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: int = Query(1000, description="Radius in meters")
):
    """
    Get properties within a radius of a point
    """
    try:
        with mdb.spatial() as session:
            result = session.execute(text("""
                SELECT 
                    property_id,
                    ST_Y(location::geometry) as latitude,
                    ST_X(location::geometry) as longitude,
                    city,
                    locality,
                    ST_Distance(location::geography, 
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) as distance
                FROM property_locations
                WHERE ST_DWithin(
                    location::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                    :radius
                )
                ORDER BY distance
                LIMIT 100
            """), {'lat': lat, 'lon': lon, 'radius': radius})
            
            properties = []
            for row in result:
                properties.append({
                    'property_id': row[0],
                    'latitude': row[1],
                    'longitude': row[2],
                    'city': row[3],
                    'locality': row[4],
                    'distance': row[5]
                })
            
            return {
                'properties': properties,
                'count': len(properties),
                'center': {'lat': lat, 'lon': lon},
                'radius': radius
            }
            
    except Exception as e:
        logger.error(f"Error fetching area properties: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_property_stats():
    """
    Get property statistics
    """
    try:
        with mdb.spatial() as session:
            # Total properties
            total_result = session.execute(text("SELECT COUNT(*) FROM property_locations"))
            total = total_result.scalar()
            
            # Cities count
            cities_result = session.execute(text("SELECT COUNT(DISTINCT city) FROM property_locations"))
            cities = cities_result.scalar()
            
            # Localities count
            localities_result = session.execute(text("SELECT COUNT(DISTINCT locality) FROM property_locations"))
            localities = localities_result.scalar()
            
            # Top localities
            top_localities_result = session.execute(text("""
                SELECT locality, COUNT(*) as count 
                FROM property_locations 
                WHERE locality IS NOT NULL 
                GROUP BY locality 
                ORDER BY count DESC 
                LIMIT 10
            """))
            
            top_localities = []
            for row in top_localities_result:
                top_localities.append({
                    'locality': row[0],
                    'count': row[1]
                })
            
            return {
                'total_properties': total,
                'cities': cities,
                'localities': localities,
                'top_localities': top_localities
            }
            
    except Exception as e:
        logger.error(f"Error fetching property stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
