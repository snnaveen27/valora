"""
Valora AI - Insight Cache Service (Production-Level SpatiaLite)
Caches AI-generated insight explanations with 2km radius deduplication.
Tracks user charges for card interactions to prevent duplicate billing.
Uses SpatiaLite database for production-level performance and reliability.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

from database.db_service import DatabaseService

logger = logging.getLogger(__name__)

# Training data log (JSONL - optimal for ML pipelines)
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
INSIGHT_TRAINING_LOG_FILE = CACHE_DIR / "insight_training_log.jsonl"

# Cache configuration
CACHE_RADIUS_KM = 2.0  # 2km radius for location deduplication
CACHE_TTL_DAYS = 30  # Cache expires after 30 days
CHARGE_DEDUP_DAYS = 30  # User charge deduplication window
INSIGHT_COST_UNITS = 5  # Default cost in compute units

# Database instance (singleton)
_db_instance = None

def get_db() -> DatabaseService:
    """Get or create database service singleton."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseService()
        logger.info("[InsightCache] Initialized database connection")
    return _db_instance


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great circle distance between two points on earth (in km)."""
    R = 6371  # Earth's radius in km
    
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def cleanup_expired_cache():
    """Remove expired cache entries from database."""
    try:
        db = get_db()
        query = "DELETE FROM insight_cache WHERE expires_at < ?"
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (datetime.now().isoformat(),))
            deleted = cursor.rowcount
            if deleted > 0:
                logger.info(f"[InsightCache] Cleaned up {deleted} expired cache entries")
    except Exception as e:
        logger.error(f"[InsightCache] Cleanup failed: {e}")


def find_nearby_cached_insight(
    user_id: int,
    card_type: str,
    lat: float,
    lng: float
) -> Optional[Dict]:
    """Find a cached insight within 2km radius for a specific user."""
    try:
        db = get_db()
        
        # Query for nearby cache entries (user-scoped, not expired)
        query = """
            SELECT id, latitude, longitude, explanation, simulation_data, 
                   metadata, cached_at, hit_count
            FROM insight_cache
            WHERE user_id = ? 
              AND card_type = ?
              AND expires_at > ?
        """
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id, card_type, datetime.now().isoformat()))
            
            for row in cursor.fetchall():
                entry_lat = row['latitude']
                entry_lng = row['longitude']
                distance = haversine_distance(lat, lng, entry_lat, entry_lng)
                
                if distance <= CACHE_RADIUS_KM:
                    return {
                        "id": row['id'],
                        "explanation": row['explanation'],
                        "simulation_data": json.loads(row['simulation_data']) if row['simulation_data'] else None,
                        "metadata": json.loads(row['metadata']) if row['metadata'] else {},
                        "cached_at": row['cached_at'],
                        "hit_count": row['hit_count'],
                        "cache_hit": True,
                        "distance_km": round(distance, 2)
                    }
        
        return None
    except Exception as e:
        logger.error(f"[InsightCache] Find nearby failed: {e}")
        return None


def get_cached_insight(
    user_id: int,
    card_type: str,
    lat: float,
    lng: float
) -> Tuple[Optional[Dict], bool]:
    """
    Get a cached insight explanation if available within 2km.
    Returns (cached_data, is_cache_hit)
    """
    try:
        # Periodic cleanup (every 10th request probabilistically)
        import random
        if random.random() < 0.1:
            cleanup_expired_cache()
        
        # Look for nearby cached insight (user-scoped)
        nearby = find_nearby_cached_insight(user_id, card_type, lat, lng)
        if nearby:
            return nearby, True
        
        return None, False
    except Exception as e:
        logger.error(f"[InsightCache] Get cached insight failed: {e}")
        return None, False


def cache_insight(
    user_id: int,
    card_type: str,
    lat: float,
    lng: float,
    explanation: str,
    simulation_data: Optional[Dict] = None,
    metadata: Optional[Dict] = None
) -> int:
    """
    Cache an insight explanation in database.
    Returns the cache entry ID.
    """
    try:
        db = get_db()
        
        expires_at = datetime.now() + timedelta(days=CACHE_TTL_DAYS)
        
        data = {
            "user_id": user_id,
            "card_type": card_type,
            "latitude": lat,
            "longitude": lng,
            "area_name": metadata.get("area_name") if metadata else None,
            "explanation": explanation,
            "simulation_data": json.dumps(simulation_data) if simulation_data else None,
            "metadata": json.dumps(metadata) if metadata else None,
            "expires_at": expires_at.isoformat(),
            "hit_count": 0
        }
        
        cache_id = db.insert("insight_cache", data)
        logger.info(f"[InsightCache] Cached insight {cache_id} for user {user_id}, card {card_type}")
        return cache_id
        
    except Exception as e:
        logger.error(f"[InsightCache] Cache insert failed: {e}")
        return -1


def increment_cache_hit(cache_id: int):
    """Increment the hit count for a cached insight."""
    try:
        db = get_db()
        query = """
            UPDATE insight_cache 
            SET hit_count = hit_count + 1,
                last_hit_at = ?
            WHERE id = ?
        """
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (datetime.now().isoformat(), cache_id))
    except Exception as e:
        logger.error(f"[InsightCache] Increment hit failed: {e}")


def append_training_sample(sample: Dict[str, Any]) -> None:
    """Append a single training sample to a local JSONL file."""
    try:
        payload = {**sample, "logged_at": datetime.now().isoformat()}
        with open(INSIGHT_TRAINING_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[WARNING] Failed to append training sample: {e}")


def check_user_charged(
    user_id: int,
    card_type: str,
    lat: float,
    lng: float
) -> Tuple[bool, Optional[str]]:
    """
    Check if user has already been charged for this insight within 2km.
    Returns (already_charged, charge_key)
    """
    try:
        db = get_db()
        
        # Query for charges within deduplication window
        query = """
            SELECT id, latitude, longitude, charge_key
            FROM user_charges
            WHERE user_id = ?
              AND card_type = ?
              AND valid_until > ?
        """
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id, card_type, datetime.now().isoformat()))
            
            for row in cursor.fetchall():
                charge_lat = row['latitude']
                charge_lng = row['longitude']
                distance = haversine_distance(lat, lng, charge_lat, charge_lng)
                
                if distance <= CACHE_RADIUS_KM:
                    return True, row['charge_key']
        
        return False, None
    except Exception as e:
        logger.error(f"[InsightCache] Check user charged failed: {e}")
        return False, None


def record_user_charge(
    user_id: int,
    card_type: str,
    lat: float,
    lng: float,
    units_charged: int = INSIGHT_COST_UNITS,
    area_name: str = None
) -> Dict:
    """
    Record that a user has been charged for an insight explanation.
    Returns charge record.
    """
    try:
        db = get_db()
        
        charge_key = f"{card_type}:{user_id}:{lat:.3f}:{lng:.3f}:{datetime.now().timestamp()}"
        valid_until = datetime.now() + timedelta(days=CHARGE_DEDUP_DAYS)
        
        data = {
            "user_id": user_id,
            "card_type": card_type,
            "latitude": lat,
            "longitude": lng,
            "area_name": area_name,
            "units_charged": units_charged,
            "charge_key": charge_key,
            "valid_until": valid_until.isoformat()
        }
        
        charge_id = db.insert("user_charges", data)
        logger.info(f"[InsightCache] Recorded charge {charge_id} for user {user_id}: {units_charged} units")
        
        return {
            "id": charge_id,
            "charge_key": charge_key,
            "units_charged": units_charged,
            "charged_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"[InsightCache] Record charge failed: {e}")
        return {"error": str(e)}


def get_user_charge_stats(user_id: int) -> Dict:
    """Get charge statistics for a user from database view."""
    try:
        db = get_db()
        
        # Use the summary view we created in schema
        query = "SELECT * FROM user_charge_summary WHERE user_id = ?"
        results = db.execute(query, (user_id,))
        
        if results:
            stats = results[0]
            
            # Get recent charges
            recent_query = """
                SELECT card_type, latitude, longitude, area_name, 
                       units_charged, charged_at
                FROM user_charges
                WHERE user_id = ?
                ORDER BY charged_at DESC
                LIMIT 10
            """
            recent = db.execute(recent_query, (user_id,))
            
            return {
                "total_charged": stats.get("total_units", 0),
                "charge_count": stats.get("total_charges", 0),
                "first_charge": stats.get("first_charge"),
                "last_charge": stats.get("last_charge"),
                "unique_card_types": stats.get("unique_card_types", 0),
                "recent_charges": recent
            }
        else:
            return {
                "total_charged": 0,
                "charge_count": 0,
                "recent_charges": []
            }
    except Exception as e:
        logger.error(f"[InsightCache] Get user stats failed: {e}")
        return {"error": str(e)}


# Card type definitions with costs and simulation support
INSIGHT_CARD_TYPES = {
    "infrastructure": {
        "name": "Infrastructure Analysis",
        "cost_units": 5,
        "has_simulation": True,
        "simulation_types": ["metro_addition", "road_widening", "new_school"]
    },
    "livability": {
        "name": "Livability Score",
        "cost_units": 5,
        "has_simulation": True,
        "simulation_types": ["park_addition", "crime_reduction", "traffic_improvement"]
    },
    "investment": {
        "name": "Investment Metrics",
        "cost_units": 8,
        "has_simulation": True,
        "simulation_types": ["price_forecast", "demand_surge", "supply_increase"]
    },
    "comparison": {
        "name": "Area Comparison",
        "cost_units": 5,
        "has_simulation": False,
        "simulation_types": []
    },
    "market": {
        "name": "Market Overview",
        "cost_units": 5,
        "has_simulation": True,
        "simulation_types": ["price_change", "demand_shift"]
    },
    "terrain": {
        "name": "Terrain & Risk",
        "cost_units": 3,
        "has_simulation": True,
        "simulation_types": ["flood_risk", "elevation_impact"]
    },
    "spatial": {
        "name": "Spatial Analysis",
        "cost_units": 5,
        "has_simulation": True,
        "simulation_types": ["poi_addition", "transport_improvement"]
    }
}


def get_card_cost(card_type: str) -> int:
    """Get the cost in units for a card type."""
    return INSIGHT_CARD_TYPES.get(card_type, {}).get("cost_units", INSIGHT_COST_UNITS)


def card_has_simulation(card_type: str) -> bool:
    """Check if a card type supports simulation."""
    return INSIGHT_CARD_TYPES.get(card_type, {}).get("has_simulation", False)


def get_cache_stats() -> Dict:
    """Get cache statistics from database."""
    try:
        db = get_db()
        
        # Cache stats
        cache_query = """
            SELECT 
                COUNT(*) as total_cached,
                COUNT(DISTINCT user_id) as unique_users,
                SUM(hit_count) as total_hits,
                AVG(hit_count) as avg_hits_per_entry
            FROM insight_cache
            WHERE expires_at > ?
        """
        cache_stats = db.execute(cache_query, (datetime.now().isoformat(),))
        
        # Charge stats
        charge_query = """
            SELECT 
                COUNT(*) as total_charges,
                COUNT(DISTINCT user_id) as charged_users,
                SUM(units_charged) as total_units
            FROM user_charges
        """
        charge_stats = db.execute(charge_query)
        
        # Training log stats
        training_samples = 0
        if INSIGHT_TRAINING_LOG_FILE.exists():
            training_samples = sum(1 for _ in open(INSIGHT_TRAINING_LOG_FILE))
        
        return {
            "total_cached_insights": cache_stats[0].get("total_cached", 0) if cache_stats else 0,
            "unique_users_cached": cache_stats[0].get("unique_users", 0) if cache_stats else 0,
            "total_cache_hits": cache_stats[0].get("total_hits", 0) if cache_stats else 0,
            "avg_hits_per_entry": round(cache_stats[0].get("avg_hits_per_entry", 0), 2) if cache_stats else 0,
            "total_charges": charge_stats[0].get("total_charges", 0) if charge_stats else 0,
            "total_users_charged": charge_stats[0].get("charged_users", 0) if charge_stats else 0,
            "total_units_charged": charge_stats[0].get("total_units", 0) if charge_stats else 0,
            "training_samples": training_samples,
            "cache_ttl_days": CACHE_TTL_DAYS,
            "cache_radius_km": CACHE_RADIUS_KM,
            "charge_dedup_days": CHARGE_DEDUP_DAYS
        }
    except Exception as e:
        logger.error(f"[InsightCache] Get cache stats failed: {e}")
        return {"error": str(e)}
