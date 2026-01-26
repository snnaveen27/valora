"""
FastAPI Routes for SpatiaLite Database
Integrates database queries with the Valora backend
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from database.db_service import get_db_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/db", tags=["database"])


# ============================================================================
# Request/Response Models
# ============================================================================

class PropertySearchRequest(BaseModel):
    area: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    bedrooms: Optional[int] = None
    property_type: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    radius_meters: Optional[float] = None
    limit: int = 50
    offset: int = 0


class POISearchRequest(BaseModel):
    lat: float
    lng: float
    radius_meters: float = 1000
    category: Optional[str] = None
    limit: int = 20


class PropertyResponse(BaseModel):
    id: int
    property_id: str
    title: Optional[str]
    area_name: Optional[str]
    bedrooms: Optional[int]
    price: Optional[float]
    price_per_sqft: Optional[float]
    latitude: float
    longitude: float
    investment_score: Optional[float]


# ============================================================================
# Property Endpoints
# ============================================================================

@router.post("/properties/search")
async def search_properties(request: PropertySearchRequest):
    """
    Search properties with filters.
    
    Example:
    ```json
    {
        "area": "Hebbal",
        "bedrooms": 3,
        "max_price": 20000000,
        "limit": 20
    }
    ```
    """
    try:
        db = get_db_service()
        
        results = db.search_properties(
            area=request.area,
            min_price=request.min_price,
            max_price=request.max_price,
            bedrooms=request.bedrooms,
            property_type=request.property_type,
            lat=request.lat,
            lng=request.lng,
            radius_meters=request.radius_meters,
            limit=request.limit,
            offset=request.offset
        )
        
        return {
            "success": True,
            "count": len(results),
            "properties": results
        }
        
    except Exception as e:
        logger.error(f"Property search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}")
async def get_property(property_id: str):
    """Get property details by ID."""
    try:
        db = get_db_service()
        
        results = db.execute(
            """
            SELECT 
                p.*,
                ST_X(p.geom) as longitude,
                ST_Y(p.geom) as latitude,
                pa.investment_score,
                pa.metro_proximity_score,
                pa.school_proximity_score,
                pa.nearest_metro_distance
            FROM properties p
            LEFT JOIN property_analytics pa ON p.property_id = pa.property_id
            WHERE p.property_id = ?
            """,
            (property_id,)
        )
        
        if not results:
            raise HTTPException(status_code=404, detail="Property not found")
        
        return {
            "success": True,
            "property": results[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching property: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/area/{area_name}")
async def get_properties_by_area(
    area_name: str,
    limit: int = Query(50, ge=1, le=200)
):
    """Get all properties in a specific area."""
    try:
        db = get_db_service()
        
        results = db.search_properties(
            area=area_name,
            limit=limit
        )
        
        return {
            "success": True,
            "area": area_name,
            "count": len(results),
            "properties": results
        }
        
    except Exception as e:
        logger.error(f"Error fetching properties by area: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/nearby")
async def get_nearby_properties(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius: float = Query(1000, description="Radius in meters"),
    limit: int = Query(20, ge=1, le=100)
):
    """Find properties within radius of a point."""
    try:
        db = get_db_service()
        
        results = db.search_properties(
            lat=lat,
            lng=lng,
            radius_meters=radius,
            limit=limit
        )
        
        return {
            "success": True,
            "center": {"lat": lat, "lng": lng},
            "radius_meters": radius,
            "count": len(results),
            "properties": results
        }
        
    except Exception as e:
        logger.error(f"Error finding nearby properties: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# POI Endpoints
# ============================================================================

@router.post("/pois/nearby")
async def search_nearby_pois(request: POISearchRequest):
    """
    Find POIs near a location.
    
    Example:
    ```json
    {
        "lat": 13.0359,
        "lng": 77.5946,
        "radius_meters": 2000,
        "category": "school"
    }
    ```
    """
    try:
        db = get_db_service()
        
        results = db.search_nearby_pois(
            lat=request.lat,
            lng=request.lng,
            radius_meters=request.radius_meters,
            category=request.category,
            limit=request.limit
        )
        
        return {
            "success": True,
            "count": len(results),
            "pois": results
        }
        
    except Exception as e:
        logger.error(f"POI search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pois/categories")
async def get_poi_categories():
    """Get list of POI categories."""
    try:
        db = get_db_service()
        
        results = db.execute(
            """
            SELECT DISTINCT category, COUNT(*) as count
            FROM pois
            GROUP BY category
            ORDER BY count DESC
            """
        )
        
        return {
            "success": True,
            "categories": results
        }
        
    except Exception as e:
        logger.error(f"Error fetching POI categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Area Analytics Endpoints
# ============================================================================

@router.get("/areas/{area_name}/stats")
async def get_area_stats(area_name: str):
    """Get statistics for an area."""
    try:
        db = get_db_service()
        
        stats = db.get_area_stats(area_name)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Area not found")
        
        return {
            "success": True,
            "area": area_name,
            "stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching area stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/areas")
async def get_all_areas():
    """Get list of all areas with property counts."""
    try:
        db = get_db_service()
        
        results = db.execute(
            """
            SELECT * FROM area_property_summary
            ORDER BY property_count DESC
            """
        )
        
        return {
            "success": True,
            "count": len(results),
            "areas": results
        }
        
    except Exception as e:
        logger.error(f"Error fetching areas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Search & Discovery Endpoints
# ============================================================================

@router.get("/search")
async def full_text_search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=200)
):
    """
    Full-text search across properties.
    
    Searches in: title, description, address, locality, area_name, amenities
    """
    try:
        db = get_db_service()
        
        results = db.full_text_search(q, limit)
        
        return {
            "success": True,
            "query": q,
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-properties")
async def get_top_properties(
    sort_by: str = Query("investment_score", regex="^(investment_score|price|price_per_sqft|created_at)$"),
    limit: int = Query(20, ge=1, le=100)
):
    """Get top properties sorted by various criteria."""
    try:
        db = get_db_service()
        
        order_map = {
            "investment_score": "pa.investment_score DESC",
            "price": "p.price ASC",
            "price_per_sqft": "p.price_per_sqft ASC",
            "created_at": "p.created_at DESC"
        }
        
        results = db.execute(
            f"""
            SELECT 
                p.*,
                ST_X(p.geom) as longitude,
                ST_Y(p.geom) as latitude,
                pa.investment_score
            FROM properties p
            LEFT JOIN property_analytics pa ON p.property_id = pa.property_id
            WHERE p.status = 'active'
            ORDER BY {order_map[sort_by]}
            LIMIT ?
            """,
            (limit,)
        )
        
        return {
            "success": True,
            "sort_by": sort_by,
            "count": len(results),
            "properties": results
        }
        
    except Exception as e:
        logger.error(f"Error fetching top properties: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Database Statistics
# ============================================================================

@router.get("/stats")
async def get_database_stats():
    """Get comprehensive database statistics."""
    try:
        db = get_db_service()
        stats = db.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Database health check."""
    try:
        db = get_db_service()
        
        # Test query
        result = db.execute("SELECT COUNT(*) as count FROM properties")
        
        return {
            "success": True,
            "status": "healthy",
            "property_count": result[0]['count'] if result else 0
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }


# ============================================================================
# Spatial Queries
# ============================================================================

@router.post("/spatial/within-polygon")
async def properties_within_polygon(coordinates: List[List[float]]):
    """
    Get properties within a polygon boundary.
    
    Example:
    ```json
    [
        [13.0359, 77.5946],
        [13.0400, 77.6000],
        [13.0300, 77.6100],
        [13.0359, 77.5946]
    ]
    ```
    """
    try:
        db = get_db_service()
        
        results = db.get_properties_in_polygon(coordinates)
        
        return {
            "success": True,
            "count": len(results),
            "properties": results
        }
        
    except Exception as e:
        logger.error(f"Polygon query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spatial/distance")
async def calculate_distance(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float
):
    """Calculate distance between two points (returns meters)."""
    try:
        db = get_db_service()
        
        result = db.execute(
            """
            SELECT ST_Distance(
                MakePoint(?, ?, 4326),
                MakePoint(?, ?, 4326),
                1
            ) as distance_meters
            """,
            (lng1, lat1, lng2, lat2)
        )
        
        return {
            "success": True,
            "distance_meters": result[0]['distance_meters'] if result else 0
        }
        
    except Exception as e:
        logger.error(f"Distance calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
