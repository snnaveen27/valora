"""
Valora AI - Locality State Service
Fast lookups from precomputed locality_state store.
This replaces expensive real-time computations with instant lookups.
"""

import sqlite3
from typing import Dict, Any, List, Optional
from pathlib import Path
from functools import lru_cache
from datetime import datetime

# Database path
DB_PATH = Path(__file__).parent.parent / "src" / "data" / "valora.db"


class LocalityService:
    """Service for fast locality state lookups."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._cache = {}  # In-memory cache
        self._cache_time = None
        self._cache_ttl = 300  # 5 minutes
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _should_refresh_cache(self) -> bool:
        """Check if cache should be refreshed."""
        if not self._cache_time:
            return True
        elapsed = (datetime.now() - self._cache_time).total_seconds()
        return elapsed > self._cache_ttl
    
    def get_locality_state(self, locality_name: str, city_id: str = 'BLR') -> Optional[Dict[str, Any]]:
        """
        Get precomputed state for a locality.
        FAST: Single row lookup instead of multiple expensive queries.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Try exact match first
        cursor.execute("""
            SELECT * FROM locality_state 
            WHERE locality_name = ? AND city_id = ?
        """, (locality_name, city_id))
        
        row = cursor.fetchone()
        
        # Try fuzzy match if exact fails
        if not row:
            cursor.execute("""
                SELECT * FROM locality_state 
                WHERE locality_name LIKE ? AND city_id = ?
                ORDER BY data_completeness DESC
                LIMIT 1
            """, (f"%{locality_name}%", city_id))
            row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_locality_by_id(self, locality_id: str) -> Optional[Dict[str, Any]]:
        """Get locality state by ID."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM locality_state WHERE locality_id = ?", (locality_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_nearby_locality(self, lat: float, lng: float, radius_km: float = 2.0) -> Optional[Dict[str, Any]]:
        """Find nearest locality to coordinates."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Approximate degree conversion
        deg_radius = radius_km / 111.0
        
        cursor.execute("""
            SELECT *, 
                   ((center_lat - ?) * (center_lat - ?) + (center_lng - ?) * (center_lng - ?)) as dist_sq
            FROM locality_state
            WHERE center_lat BETWEEN ? AND ?
              AND center_lng BETWEEN ? AND ?
              AND center_lat IS NOT NULL
              AND center_lng IS NOT NULL
            ORDER BY dist_sq ASC
            LIMIT 1
        """, (
            lat, lat, lng, lng,
            lat - deg_radius, lat + deg_radius,
            lng - deg_radius, lng + deg_radius
        ))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_top_hotspots(self, city_id: str = 'BLR', limit: int = 10) -> List[Dict[str, Any]]:
        """Get top localities by hotspot score."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT locality_name, growth_phase, hotspot_score, risk_level, archetype,
                   avg_price_sqft, active_listings, accessibility_score
            FROM locality_state
            WHERE city_id = ?
            ORDER BY hotspot_score DESC
            LIMIT ?
        """, (city_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_localities_by_growth_phase(self, growth_phase: str, city_id: str = 'BLR') -> List[Dict[str, Any]]:
        """Get localities in a specific growth phase."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT locality_name, hotspot_score, risk_level, archetype, avg_price_sqft
            FROM locality_state
            WHERE growth_phase = ? AND city_id = ?
            ORDER BY hotspot_score DESC
        """, (growth_phase, city_id))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_localities_by_archetype(self, archetype: str, city_id: str = 'BLR') -> List[Dict[str, Any]]:
        """Get localities by archetype (tech_hub, family_suburb, etc.)."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT locality_name, growth_phase, hotspot_score, risk_level, avg_price_sqft
            FROM locality_state
            WHERE archetype = ? AND city_id = ?
            ORDER BY hotspot_score DESC
        """, (archetype, city_id))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_investment_recommendations(self, investor_type: str = 'balanced', city_id: str = 'BLR', limit: int = 5) -> List[Dict[str, Any]]:
        """Get investment recommendations based on investor profile."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Match investor type to suitable localities
        if investor_type == 'conservative':
            cursor.execute("""
                SELECT locality_name, growth_phase, hotspot_score, risk_level, risk_index, archetype, avg_price_sqft
                FROM locality_state
                WHERE city_id = ? AND risk_level IN ('low', 'medium') AND growth_phase IN ('mature', 'maturing')
                ORDER BY hotspot_score DESC
                LIMIT ?
            """, (city_id, limit))
        elif investor_type == 'aggressive':
            cursor.execute("""
                SELECT locality_name, growth_phase, hotspot_score, risk_level, risk_index, archetype, avg_price_sqft
                FROM locality_state
                WHERE city_id = ? AND growth_phase IN ('emerging', 'growing')
                ORDER BY hotspot_score DESC
                LIMIT ?
            """, (city_id, limit))
        else:  # balanced
            cursor.execute("""
                SELECT locality_name, growth_phase, hotspot_score, risk_level, risk_index, archetype, avg_price_sqft
                FROM locality_state
                WHERE city_id = ? AND risk_level IN ('low', 'medium', 'high')
                ORDER BY hotspot_score DESC
                LIMIT ?
            """, (city_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_locality_timeline(self, locality_id: str, months: int = 12) -> List[Dict[str, Any]]:
        """Get historical state for a locality."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT snapshot_date, avg_price_sqft, active_listings, growth_phase, 
                   hotspot_score, risk_index
            FROM locality_state_ts
            WHERE locality_id = ?
            ORDER BY snapshot_date DESC
            LIMIT ?
        """, (locality_id, months))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def compare_localities(self, locality_names: List[str], city_id: str = 'BLR') -> List[Dict[str, Any]]:
        """Compare multiple localities side by side."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        placeholders = ','.join(['?' for _ in locality_names])
        cursor.execute(f"""
            SELECT locality_name, growth_phase, hotspot_score, risk_level, risk_index,
                   archetype, investor_type, avg_price_sqft, active_listings,
                   accessibility_score, walkability_score, livability_score,
                   metro_count, poi_count
            FROM locality_state
            WHERE locality_name IN ({placeholders}) AND city_id = ?
        """, (*locality_names, city_id))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_market_overview(self, city_id: str = 'BLR') -> Dict[str, Any]:
        """Get city-wide market overview from precomputed data."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_localities,
                AVG(avg_price_sqft) as city_avg_price,
                SUM(active_listings) as total_listings,
                AVG(hotspot_score) as avg_hotspot_score,
                COUNT(CASE WHEN growth_phase = 'emerging' THEN 1 END) as emerging_count,
                COUNT(CASE WHEN growth_phase = 'growing' THEN 1 END) as growing_count,
                COUNT(CASE WHEN growth_phase = 'maturing' THEN 1 END) as maturing_count,
                COUNT(CASE WHEN growth_phase = 'mature' THEN 1 END) as mature_count
            FROM locality_state
            WHERE city_id = ?
        """, (city_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else {}


# Singleton instance
_locality_service = None

def get_locality_service(db_path: str = None) -> LocalityService:
    """Get or create locality service singleton."""
    global _locality_service
    if _locality_service is None:
        _locality_service = LocalityService(db_path)
    return _locality_service


# Convenience functions for backward compatibility
def get_locality_state(locality_name: str, city_id: str = 'BLR') -> Optional[Dict[str, Any]]:
    """Quick lookup of locality state."""
    return get_locality_service().get_locality_state(locality_name, city_id)


def get_nearby_locality(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    """Find nearest locality to coordinates."""
    return get_locality_service().get_nearby_locality(lat, lng)


def get_top_hotspots(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top investment hotspots."""
    return get_locality_service().get_top_hotspots(limit=limit)
