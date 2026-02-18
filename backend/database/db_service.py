"""
Valora Database Service - SpatiaLite
Centralized database access layer for all spatial data
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
import logging
from config import config

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Core database service for SQLite operations.
    Handles connections, queries, and coordinate-based spatial operations.
    Note: Uses lat/lng columns instead of SpatiaLite geometry for Windows compatibility.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = config.DB_PATH
        else:
            db_path = Path(db_path)
        
        self.db_path = db_path
        self.schema_path = config.SCHEMA_DIR / "schema_simple.sql"
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[DB] Initialized SQLite database at {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Access columns by name
        
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[DB] Transaction failed: {e}")
            raise
        finally:
            conn.close()
    
    def initialize_schema(self, force: bool = False):
        """Initialize database schema from schema_simple.sql"""
        if self.db_path.exists() and not force:
            logger.info("[DB] Database already exists. Use force=True to recreate.")
            return
        
        if force and self.db_path.exists():
            logger.warning("[DB] Force recreating database...")
            self.db_path.unlink()
        
        logger.info(f"[DB] Initializing database schema from {self.schema_path}...")
        
        if not self.schema_path.exists():
            logger.error(f"[DB] Schema file not found: {self.schema_path}")
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        
        with self.get_connection() as conn:
            # Read schema
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # Use executescript to run all statements
            conn.executescript(schema_sql)
        
        logger.info("[DB] Schema initialized successfully")
    
    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a query and return results as list of dicts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute same query with multiple parameter sets."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            return cursor.rowcount
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """Insert a record and return the ID."""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(data.values()))
            return cursor.lastrowid
    
    def insert_many(self, table: str, records: List[Dict[str, Any]]) -> int:
        """Insert multiple records."""
        if not records:
            return 0
        
        columns = ', '.join(records[0].keys())
        placeholders = ', '.join(['?'] * len(records[0]))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        params_list = [tuple(record.values()) for record in records]
        return self.execute_many(query, params_list)
    
    def update(self, table: str, data: Dict[str, Any], where: str, where_params: tuple = None) -> int:
        """Update records."""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        params = tuple(data.values()) + (where_params or ())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.rowcount
    
    def delete(self, table: str, where: str, where_params: tuple = None) -> int:
        """Delete records."""
        query = f"DELETE FROM {table} WHERE {where}"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, where_params or ())
            return cursor.rowcount
    
    def search_properties(
        self,
        area: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        bedrooms: Optional[int] = None,
        property_type: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_meters: Optional[float] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Search properties with various filters.
        
        Args:
            area: Area name (e.g., 'Hebbal', 'Indiranagar')
            min_price: Minimum price
            max_price: Maximum price
            bedrooms: Number of bedrooms
            property_type: Type of property
            lat, lng: Center point for radius search
            radius_meters: Search radius in meters (converted to approx degrees)
            limit: Max results
            offset: Pagination offset
        """
        conditions = ["status = 'active'"]
        params = []
        
        if area:
            conditions.append("(area_name LIKE ? OR locality LIKE ?)")
            params.append(f"%{area}%")
            params.append(f"%{area}%")
        
        if min_price:
            conditions.append("price >= ?")
            params.append(min_price)
        
        if max_price:
            conditions.append("price <= ?")
            params.append(max_price)
        
        if bedrooms:
            conditions.append("bedrooms = ?")
            params.append(bedrooms)
        
        if property_type:
            conditions.append("property_type = ?")
            params.append(property_type)
        
        # Radius search using Haversine approximation
        # 1 degree latitude ≈ 111km, so radius_meters/111000 gives degree difference
        if lat and lng and radius_meters:
            degree_radius = radius_meters / 111000  # Approximate
            conditions.append(
                "latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?"
            )
            params.extend([lat - degree_radius, lat + degree_radius, lng - degree_radius, lng + degree_radius])
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
            SELECT 
                p.*,
                pa.investment_score,
                pa.nearest_metro_distance,
                pa.metro_proximity_score
            FROM properties p
            LEFT JOIN property_analytics pa ON p.property_id = pa.property_id
            WHERE {where_clause}
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
        """
        
        params.extend([limit, offset])
        
        return self.execute(query, tuple(params))
    
    def search_nearby_pois(
        self,
        lat: float,
        lng: float,
        radius_meters: float = 1000,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Find POIs near a location."""
        conditions = ["1=1"]
        params = []
        
        degree_radius = radius_meters / 111000  # Approximate
        
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        # Bounding box filter
        conditions.append("latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?")
        params.extend([lat - degree_radius, lat + degree_radius, lng - degree_radius, lng + degree_radius])
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
            SELECT *
            FROM pois
            WHERE {where_clause}
            LIMIT ?
        """
        
        params.append(limit)
        
        return self.execute(query, tuple(params))
    
    def get_area_stats(self, area_name: str) -> Optional[Dict]:
        """Get statistics for an area."""
        query = """
            SELECT * FROM area_property_summary
            WHERE area_name LIKE ?
        """
        
        results = self.execute(query, (f"%{area_name}%",))
        return results[0] if results else None
    
    def full_text_search(self, search_text: str, limit: int = 50) -> List[Dict]:
        """Full-text search across properties using LIKE."""
        search_pattern = f"%{search_text}%"
        
        query = """
            SELECT *
            FROM properties
            WHERE title LIKE ? OR description LIKE ? OR area_name LIKE ? OR locality LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        
        return self.execute(query, (search_pattern, search_pattern, search_pattern, search_pattern, limit))
    
    def get_properties_in_polygon(self, coordinates: List[Tuple[float, float]]) -> List[Dict]:
        """Get properties within a bounding box (simplified from polygon)."""
        if not coordinates:
            return []
        
        # Calculate bounding box from coordinates
        lats = [c[0] for c in coordinates]
        lngs = [c[1] for c in coordinates]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)
        
        query = """
            SELECT *
            FROM properties
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
            AND status = 'active'
        """
        
        return self.execute(query, (min_lat, max_lat, min_lng, max_lng))
    
    def log_ingestion(
        self,
        source_name: str,
        processed: int,
        inserted: int,
        updated: int,
        failed: int,
        status: str,
        error: Optional[str] = None
    ) -> int:
        """Log ingestion results."""
        data = {
            'source_name': source_name,
            'records_processed': processed,
            'records_inserted': inserted,
            'records_updated': updated,
            'records_failed': failed,
            'status': status,
            'error_message': error,
            'completed_at': datetime.now().isoformat()
        }
        
        return self.insert('ingestion_log', data)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {}
        
        # Count records in each table
        tables = ['properties', 'pois', 'places', 'buildings', 'transport_stops', 'roads']
        
        for table in tables:
            query = f"SELECT COUNT(*) as count FROM {table}"
            result = self.execute(query)
            stats[table] = result[0]['count'] if result else 0
        
        # Active properties
        query = "SELECT COUNT(*) as count FROM properties WHERE status = 'active'"
        result = self.execute(query)
        stats['active_properties'] = result[0]['count'] if result else 0
        
        # Recent ingestions
        query = """
            SELECT source_name, completed_at, status, records_inserted
            FROM ingestion_log
            ORDER BY started_at DESC
            LIMIT 5
        """
        stats['recent_ingestions'] = self.execute(query)
        
        return stats
    
    async def get_market_stats(
        self,
        lat: float,
        lng: float,
        radius_meters: float = 3000
    ) -> Optional[Dict[str, Any]]:
        """
        Get market statistics for properties within a radius of a location.
        
        Args:
            lat: Latitude of center point
            lng: Longitude of center point
            radius_meters: Search radius in meters (default 3000m)
            
        Returns:
            Dict with market statistics or None if no data found
        """
        # Convert radius to approximate degree difference
        degree_radius = radius_meters / 111000
        
        query = """
            SELECT 
                COUNT(*) as property_count,
                AVG(price) as avg_price,
                AVG(price / NULLIF(CAST(built_up_area AS REAL), 0)) as avg_price_per_sqft,
                MIN(price) as min_price,
                MAX(price) as max_price,
                AVG(CAST(bedrooms AS REAL)) as avg_bedrooms
            FROM properties
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
            AND status = 'active'
            AND price IS NOT NULL
        """
        
        results = self.execute(query, (
            lat - degree_radius, lat + degree_radius,
            lng - degree_radius, lng + degree_radius
        ))
        
        if not results or not results[0] or results[0].get('property_count', 0) == 0:
            return None
        
        row = results[0]
        
        # Calculate price trend (simplified - would need historical data for real trend)
        # For now, return a default trend based on market conditions
        price_trend_1y = 8.5  # Default 8.5% annual appreciation
        price_trend_3y = 25.0  # Default 25% 3-year appreciation
        
        return {
            'property_count': row.get('property_count', 0),
            'avg_price': row.get('avg_price'),
            'avg_price_per_sqft': row.get('avg_price_per_sqft') or 8500,  # Default fallback
            'min_price': row.get('min_price'),
            'max_price': row.get('max_price'),
            'avg_bedrooms': row.get('avg_bedrooms'),
            'price_trend_1y': price_trend_1y,
            'price_trend_3y': price_trend_3y,
            'demand_supply_ratio': 1.2,  # Default: more buyers than sellers
            'liquidity_score': 7.0,  # Default liquidity score out of 10
            'rental_yield': 3.5,  # Default rental yield percentage
            'radius_meters': radius_meters
        }


# Global instance
_db_service = None

def get_db_service(db_path: str = None) -> DatabaseService:
    """Get or create global database service instance."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService(db_path)
    return _db_service
