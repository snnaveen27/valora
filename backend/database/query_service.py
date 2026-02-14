"""
Database Query Service - Replace file-based data loading with database queries
All services will use this to access properties, POIs, places, transport, buildings
"""
import json
import math
from pathlib import Path
from typing import Optional, List, Dict, Any
from functools import lru_cache
import logging
from config import config

logger = logging.getLogger(__name__)

# Database path
DB_PATH = config.DB_PATH


class DatabaseQueryService:
    """Unified database query service for all data types."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        
        if self._initialized:
            return
        
        try:
            from backend.database.db_service import DatabaseService
        except ImportError:
            from database.db_service import DatabaseService
        self.db = DatabaseService(str(DB_PATH))
        self._initialized = True
        logger.info(f"[DB] Query service initialized: {DB_PATH}")
    
    # =========================================================================
    # PROPERTIES
    # =========================================================================
    
    def search_properties(
        self,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_m: int = 2000,
        property_type: Optional[str] = None,
        listing_type: Optional[str] = None,
        property_category: Optional[str] = None,
        property_subtype: Optional[str] = None,
        pg_type: Optional[str] = None,
        bhk: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_bedrooms: Optional[int] = None,
        max_bedrooms: Optional[int] = None,
        locality: Optional[str] = None,
        text_query: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search properties with filters.
        
        Args:
            listing_type: 'sale' or 'rent'
            property_category: 'residential', 'commercial', 'plot', 'pg'
            property_subtype: 'flat', 'villa', 'office', 'warehouse', etc.
            pg_type: 'boys', 'girls', 'coed' (for PG/hostels)
            bhk: '1BHK', '2BHK', '3BHK', etc.
            text_query: Full-text search across title, description, locality
        """
        
        conditions = ["1=1"]
        params = []
        
        if property_type:
            conditions.append("property_type LIKE ?")
            params.append(f"%{property_type}%")
        
        if listing_type:
            # Normalize rent variations
            normalized = listing_type.lower().strip()
            if normalized in ('rent', 'rental', 'lease', 'for rent'):
                normalized = 'rent'
            elif normalized in ('sale', 'buy', 'purchase', 'for sale'):
                normalized = 'sale'
            conditions.append("listing_type = ?")
            params.append(normalized)
        
        if property_category:
            conditions.append("property_category = ?")
            params.append(property_category.lower())
        
        if property_subtype:
            conditions.append("property_subtype LIKE ?")
            params.append(f"%{property_subtype}%")
        
        # pg_type column not yet in database - skip for now
        # if pg_type:
        #     conditions.append("pg_type = ?")
        #     params.append(pg_type.lower())
        
        if bhk:
            # Handle both '2BHK' and '2' formats
            bhk_normalized = bhk.upper().replace(' ', '')
            if not bhk_normalized.endswith('BHK'):
                bhk_normalized = f"{bhk_normalized}BHK"
            conditions.append("(bhk = ? OR bedrooms = ?)")
            params.append(bhk_normalized)
            # Extract number for bedrooms fallback
            try:
                bedrooms_num = int(''.join(filter(str.isdigit, bhk_normalized)))
                params.append(bedrooms_num)
            except:
                params.append(0)
        
        if min_price:
            conditions.append("price >= ?")
            params.append(min_price)
        
        if max_price:
            conditions.append("price <= ?")
            params.append(max_price)
        
        if min_bedrooms:
            conditions.append("bedrooms >= ?")
            params.append(min_bedrooms)
        
        if max_bedrooms:
            conditions.append("bedrooms <= ?")
            params.append(max_bedrooms)
        
        if locality:
            conditions.append("(locality LIKE ? OR area_name LIKE ?)")
            params.extend([f"%{locality}%", f"%{locality}%"])
        
        if text_query:
            # Full-text search with weighted ranking simulation
            search_pattern = f"%{text_query}%"
            conditions.append("(title LIKE ? OR description LIKE ? OR locality LIKE ? OR area_name LIKE ? OR amenities LIKE ?)")
            params.extend([search_pattern] * 5)
        
        # Spatial filter (bounding box approximation)
        if lat and lng and radius_m:
            # ~111km per degree lat, ~85km per degree lng at Bangalore
            lat_delta = radius_m / 111000
            lng_delta = radius_m / 85000
            conditions.append("latitude BETWEEN ? AND ?")
            conditions.append("longitude BETWEEN ? AND ?")
            params.extend([lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta])
        
        query = f"""
            SELECT id, property_id, source, title, description, property_type, listing_type,
                   address, locality, area_name, city, pincode, latitude, longitude,
                   bedrooms, bathrooms, balconies, total_area_sqft, carpet_area_sqft,
                   floor_number, total_floors, furnishing, facing, age_years, parking,
                   price, price_per_sqft, price_display, maintenance_monthly, deposit,
                   amenities, builder_name, owner_name, images, source_url,
                   posted_at, created_at,
                   property_category, property_subtype, bhk, rent_monthly
            FROM properties
            WHERE {' AND '.join(conditions)}
            LIMIT ?
        """
        params.append(limit)
        
        results = self.db.execute(query, tuple(params)) or []
        
        # Calculate distance if location provided
        if lat and lng:
            for r in results:
                if r.get('latitude') and r.get('longitude'):
                    r['_distance'] = self._haversine(lat, lng, r['latitude'], r['longitude'])
            results.sort(key=lambda x: x.get('_distance', float('inf')))
        
        return results
    
    def get_property_by_id(self, property_id: str) -> Optional[Dict]:
        """Get property by ID."""
        result = self.db.execute(
            "SELECT * FROM properties WHERE property_id = ?",
            (property_id,)
        )
        return result[0] if result else None
    
    def get_properties_count(self) -> int:
        """Get total property count."""
        result = self.db.execute("SELECT COUNT(*) as count FROM properties")
        return result[0]['count'] if result else 0
    
    def get_all_properties(self, limit: Optional[int] = None) -> List[Dict]:
        """Get all properties from database."""
        query = "SELECT * FROM properties ORDER BY property_id"
        if limit:
            query += f" LIMIT {limit}"
        return self.db.execute(query)
    
    def get_properties_by_source(self) -> Dict[str, int]:
        """Get property count by source."""
        result = self.db.execute(
            "SELECT source, COUNT(*) as cnt FROM properties GROUP BY source"
        )
        return {r['source']: r['cnt'] for r in result} if result else {}
    
    # =========================================================================
    # POIs
    # =========================================================================
    
    def get_pois(
        self,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_m: int = 1000,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get POIs near a location."""
        
        conditions = ["1=1"]
        params = []
        
        if category:
            conditions.append("(category LIKE ? OR subcategory LIKE ?)")
            params.extend([f"%{category}%", f"%{category}%"])
        
        if lat and lng and radius_m:
            lat_delta = radius_m / 111000
            lng_delta = radius_m / 85000
            conditions.append("latitude BETWEEN ? AND ?")
            conditions.append("longitude BETWEEN ? AND ?")
            params.extend([lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta])
        
        query = f"""
            SELECT poi_id, name, category, subcategory, latitude, longitude, address
            FROM pois
            WHERE {' AND '.join(conditions)}
            LIMIT ?
        """
        params.append(limit)
        
        results = self.db.execute(query, tuple(params)) or []
        
        if lat and lng:
            for r in results:
                if r.get('latitude') and r.get('longitude'):
                    r['_distance'] = self._haversine(lat, lng, r['latitude'], r['longitude'])
            results.sort(key=lambda x: x.get('_distance', float('inf')))
        
        return results
    
    def get_all_pois(self, limit: Optional[int] = None) -> List[Dict]:
        """Get all POIs with lat/lng aliases for spatial service compatibility."""
        query = """SELECT poi_id, name, category, subcategory, 
                   latitude as lat, longitude as lng, source_data
                   FROM pois ORDER BY poi_id"""
        if limit:
            query += f" LIMIT {limit}"
        return self.db.execute(query) or []
    
    # =========================================================================
    # PLACES
    # =========================================================================
    
    def get_places(
        self,
        name: Optional[str] = None,
        place_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get places/localities."""
        
        conditions = ["1=1"]
        params = []
        
        if name:
            conditions.append("name LIKE ?")
            params.append(f"%{name}%")
        
        if place_type:
            conditions.append("place_type = ?")
            params.append(place_type)
        
        query = f"""
            SELECT place_id, name, place_type, center_latitude as lat, center_longitude as lng, population
            FROM places
            WHERE {' AND '.join(conditions)}
            LIMIT ?
        """
        params.append(limit)
        
        return self.db.execute(query, tuple(params)) or []
    
    def get_all_places(self, limit: Optional[int] = None) -> List[Dict]:
        """Get all places with lat/lng aliases for spatial service compatibility."""
        query = """SELECT place_id, name, place_type as type,
                   center_latitude as lat, center_longitude as lng
                   FROM places ORDER BY place_id"""
        if limit:
            query += f" LIMIT {limit}"
        return self.db.execute(query) or []
    
    # =========================================================================
    # TRANSPORT
    # =========================================================================
    
    def get_transport(
        self,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_m: int = 2000,
        transport_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get transport stops near a location."""
        
        conditions = ["1=1"]
        params = []
        
        if transport_type:
            conditions.append("transport_type LIKE ?")
            params.append(f"%{transport_type}%")
        
        if lat and lng and radius_m:
            lat_delta = radius_m / 111000
            lng_delta = radius_m / 85000
            conditions.append("latitude BETWEEN ? AND ?")
            conditions.append("longitude BETWEEN ? AND ?")
            params.extend([lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta])
        
        query = f"""
            SELECT stop_id, name, transport_type as type, latitude as lat, longitude as lng, line_name
            FROM transport_stops
            WHERE {' AND '.join(conditions)}
            LIMIT ?
        """
        params.append(limit)
        
        results = self.db.execute(query, tuple(params)) or []
        
        if lat and lng:
            for r in results:
                if r.get('lat') and r.get('lng'):
                    r['_distance'] = self._haversine(lat, lng, r['lat'], r['lng'])
            results.sort(key=lambda x: x.get('_distance', float('inf')))
        
        return results
    
    def get_all_transport(self, limit: Optional[int] = None) -> List[Dict]:
        """Get all transport stops with lat/lng aliases for spatial service compatibility."""
        query = """SELECT stop_id, name, transport_type as type,
                   latitude as lat, longitude as lng, line_name
                   FROM transport_stops ORDER BY stop_id"""
        if limit:
            query += f" LIMIT {limit}"
        return self.db.execute(query) or []
    
    def get_metro_stations(self) -> List[Dict]:
        """Get metro stations specifically."""
        result = self.db.execute(
            """SELECT stop_id, name, latitude as lat, longitude as lng 
               FROM transport_stops 
               WHERE transport_type LIKE '%metro%' OR name LIKE '%Metro%'"""
        )
        return result or []
    
    # =========================================================================
    # BUILDINGS
    # =========================================================================
    
    def get_buildings(
        self,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_m: int = 500,
        building_type: Optional[str] = None,
        limit: int = 1000,
        include_polygons: bool = False
    ) -> List[Dict]:
        """Get buildings near a location."""
        
        conditions = ["1=1"]
        params = []
        
        if building_type:
            conditions.append("building_type LIKE ?")
            params.append(f"%{building_type}%")
        
        if lat and lng and radius_m:
            lat_delta = radius_m / 111000
            lng_delta = radius_m / 85000
            conditions.append("latitude BETWEEN ? AND ?")
            conditions.append("longitude BETWEEN ? AND ?")
            params.extend([lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta])
        
        # Include polygon_coords if requested
        select_cols = "osm_id, name, building_type, height, levels, latitude as lat, longitude as lng"
        if include_polygons:
            select_cols += ", polygon_coords"
            # Prioritize buildings with polygons
            conditions.append("polygon_coords IS NOT NULL")
        
        query = f"""
            SELECT {select_cols}
            FROM buildings
            WHERE {' AND '.join(conditions)}
            ORDER BY CASE WHEN polygon_coords IS NOT NULL THEN 0 ELSE 1 END
            LIMIT ?
        """
        params.append(limit)
        
        return self.db.execute(query, tuple(params)) or []
    
    def get_buildings_count(self) -> int:
        """Get total buildings count."""
        result = self.db.execute("SELECT COUNT(*) as cnt FROM buildings")
        return result[0]['cnt'] if result else 0
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get counts for all tables."""
        tables = ['properties', 'pois', 'places', 'transport_stops', 'buildings']
        stats = {}
        for table in tables:
            try:
                result = self.db.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                stats[table] = result[0]['cnt'] if result else 0
            except:
                stats[table] = 0
        return stats
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in meters between two points."""
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lng2 - lng1)
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


# Singleton instance
_query_service = None

def get_query_service() -> DatabaseQueryService:
    """Get singleton query service instance."""
    global _query_service
    if _query_service is None:
        _query_service = DatabaseQueryService()
    return _query_service
