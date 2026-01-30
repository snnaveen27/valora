"""
Property Service for Valora AI
Provides real estate property queries from DATABASE (not files)
"""

import math
from pathlib import Path
from typing import Optional, List, Dict, Any


class PropertyService:
    """Service for querying real estate property listings from database"""
    
    def __init__(self, data_dir: Path = None):
        # data_dir kept for backward compatibility but not used
        self._db = None
        self._hybrid_search = None
        self._cache = None
        self._initialized = False
        self._init_database()
        self._init_hybrid_search()
    
    def _init_database(self):
        """Initialize database connection"""
        if self._initialized:
            return
        try:
            # Try both import paths (running from project root vs backend dir)
            try:
                from backend.database.query_service import get_query_service
            except ImportError:
                from database.query_service import get_query_service
            self._db = get_query_service()
            count = self._db.get_properties_count()
            print(f"[OK] PropertyService: Connected to database with {count:,} properties")
            self._initialized = True
        except Exception as e:
            print(f"[WARNING] PropertyService: Database not available - {e}")
            self._db = None
    
    def _init_hybrid_search(self):
        """Initialize hybrid search and caching"""
        try:
            try:
                from backend.hybrid_search import get_hybrid_search
                from backend.query_cache import get_property_cache
            except ImportError:
                from hybrid_search import get_hybrid_search
                from query_cache import get_property_cache
            self._hybrid_search = get_hybrid_search(self._db, None)
            self._cache = get_property_cache()
            print("[OK] PropertyService: Hybrid search & caching enabled")
        except Exception as e:
            print(f"[INFO] PropertyService: Hybrid search not available - {e}")
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points in meters"""
        R = 6371000  # Earth's radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def search(
        self,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_m: int = 2000,
        category: Optional[str] = None,
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
        limit: int = 50,
        query: Optional[str] = None,  # For semantic search
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search properties with filters using DATABASE + optional RAG hybrid search.
        
        Args:
            listing_type: 'sale' or 'rent'
            property_category: 'residential', 'commercial', 'plot', 'pg'
            property_subtype: 'flat', 'villa', 'office', 'warehouse', etc.
            pg_type: 'boys', 'girls', 'coed' (for PG/hostels)
            bhk: '1BHK', '2BHK', '3BHK', etc.
            text_query: Full-text search across title, description, locality
        """
        if not self._db:
            return []
        
        # Check cache first
        if use_cache and self._cache:
            cached = self._cache.get(
                query or text_query or "search",
                lat=lat, lng=lng, radius_m=radius_m,
                property_type=property_type, listing_type=listing_type,
                property_category=property_category, pg_type=pg_type, bhk=bhk,
                min_price=min_price, max_price=max_price, 
                min_bedrooms=min_bedrooms, max_bedrooms=max_bedrooms, limit=limit
            )
            if cached is not None:
                return cached
        
        # Use hybrid search if query provided and available
        if query and self._hybrid_search:
            results = self._hybrid_search.search_properties(
                query=query,
                lat=lat,
                lng=lng,
                radius_m=radius_m,
                property_type=property_type,
                listing_type=listing_type,
                property_category=property_category,
                property_subtype=property_subtype,
                pg_type=pg_type,
                bhk=bhk,
                min_price=min_price,
                max_price=max_price,
                min_bedrooms=min_bedrooms,
                max_bedrooms=max_bedrooms,
                use_rag=True,
                limit=limit
            )
        else:
            # Fallback to standard database query
            results = self._db.search_properties(
                lat=lat,
                lng=lng,
                radius_m=radius_m,
                property_type=property_type,
                listing_type=listing_type,
                property_category=property_category,
                property_subtype=property_subtype,
                pg_type=pg_type,
                bhk=bhk,
                min_price=min_price,
                max_price=max_price,
                min_bedrooms=min_bedrooms,
                max_bedrooms=max_bedrooms,
                locality=locality,
                text_query=text_query,
                limit=limit
            )
        
        # Add computed fields for compatibility
        for prop in results:
            prop['_lat'] = prop.get('latitude')
            prop['_lng'] = prop.get('longitude')
            prop['_category'] = prop.get('property_type', 'unknown')
        
        return results
    
    def get_by_id(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get a property by its ID"""
        if not self._db:
            return None
        return self._db.get_property_by_id(property_id)
    
    def get_nearby(
        self,
        lat: float,
        lng: float,
        radius_m: int = 1000,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get properties near a location with summary statistics"""
        nearby = self.search(lat=lat, lng=lng, radius_m=radius_m, limit=limit * 3)
        
        # Group by category
        by_category = {}
        for prop in nearby:
            cat = prop.get('_category', 'unknown')
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(prop)
        
        # Calculate stats
        prices = [p.get('price', 0) for p in nearby if p.get('price')]
        price_per_sqft = [p.get('price_per_sq_ft', 0) for p in nearby if p.get('price_per_sq_ft')]
        
        return {
            'total_found': len(nearby),
            'properties': nearby[:limit],
            'by_category': {k: len(v) for k, v in by_category.items()},
            'stats': {
                'avg_price': sum(prices) / len(prices) if prices else 0,
                'min_price': min(prices) if prices else 0,
                'max_price': max(prices) if prices else 0,
                'avg_price_per_sqft': sum(price_per_sqft) / len(price_per_sqft) if price_per_sqft else 0,
            }
        }
    
    def get_area_stats(self, lat: float, lng: float, radius_m: int = 2000) -> Dict[str, Any]:
        """Get market statistics for an area"""
        nearby = self.search(lat=lat, lng=lng, radius_m=radius_m, limit=500)
        
        # Categorize
        residential = [p for p in nearby if 'residential' in p.get('_category', '')]
        commercial = [p for p in nearby if 'commercial' in p.get('_category', '')]
        agricultural = [p for p in nearby if 'agricultural' in p.get('_category', '')]
        
        def calc_stats(props):
            if not props:
                return {'count': 0, 'avg_price': 0, 'avg_price_per_sqft': 0}
            prices = [p.get('price', 0) for p in props if p.get('price')]
            ppsf = [p.get('price_per_sq_ft', 0) for p in props if p.get('price_per_sq_ft')]
            return {
                'count': len(props),
                'avg_price': sum(prices) / len(prices) if prices else 0,
                'min_price': min(prices) if prices else 0,
                'max_price': max(prices) if prices else 0,
                'avg_price_per_sqft': sum(ppsf) / len(ppsf) if ppsf else 0,
            }
        
        return {
            'total_properties': len(nearby),
            'residential': calc_stats(residential),
            'commercial': calc_stats(commercial),
            'agricultural': calc_stats(agricultural),
            'price_trends': {
                'under_50L': len([p for p in nearby if p.get('price', 0) and p['price'] < 5000000]),
                '50L_to_1Cr': len([p for p in nearby if p.get('price', 0) and 5000000 <= p['price'] < 10000000]),
                '1Cr_to_2Cr': len([p for p in nearby if p.get('price', 0) and 10000000 <= p['price'] < 20000000]),
                '2Cr_to_5Cr': len([p for p in nearby if p.get('price', 0) and 20000000 <= p['price'] < 50000000]),
                'above_5Cr': len([p for p in nearby if p.get('price', 0) and p['price'] >= 50000000]),
            }
        }
    
    def get_categories_summary(self) -> Dict[str, int]:
        """Get count of properties by source"""
        if not self._db:
            return {}
        return self._db.get_properties_by_source()


# Singleton instance
_property_service = None

def get_property_service(data_dir: Path = None) -> PropertyService:
    """Get or create PropertyService singleton"""
    global _property_service
    if _property_service is None:
        _property_service = PropertyService(data_dir)
    return _property_service
