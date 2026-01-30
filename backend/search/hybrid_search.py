"""
Hybrid Search: Combines SQL filtering with RAG semantic search
Best of both worlds: structured queries + semantic understanding
"""

from typing import List, Dict, Any, Optional
from pathlib import Path


class HybridSearchEngine:
    """Combines database filtering with RAG semantic search."""
    
    def __init__(self, db_service, rag_service):
        self.db = db_service
        self.rag = rag_service
    
    def search_properties(
        self,
        query: str,
        # Location filters
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_m: Optional[int] = None,
        locality: Optional[str] = None,
        # Property filters
        property_type: Optional[str] = None,
        listing_type: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_bedrooms: Optional[int] = None,
        max_bedrooms: Optional[int] = None,
        # Search parameters
        use_rag: bool = True,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining RAG semantic search with SQL filtering.
        
        Strategy:
        1. If use_rag: RAG finds semantically similar properties (top 200)
        2. SQL filters those by price, bedrooms, location, etc.
        3. Returns final filtered and ranked results
        """
        
        # Strategy 1: RAG-first (semantic understanding)
        if use_rag and query and self.rag and self.rag.index:
            return self._rag_first_search(
                query, lat, lng, radius_m, locality,
                property_type, listing_type,
                min_price, max_price, min_bedrooms, max_bedrooms,
                limit
            )
        
        # Strategy 2: SQL-only (structured filtering)
        return self._sql_only_search(
            lat, lng, radius_m, locality,
            property_type, listing_type,
            min_price, max_price, min_bedrooms, max_bedrooms,
            limit
        )
    
    def _rag_first_search(
        self,
        query: str,
        lat: Optional[float],
        lng: Optional[float],
        radius_m: Optional[int],
        locality: Optional[str],
        property_type: Optional[str],
        listing_type: Optional[str],
        min_price: Optional[int],
        max_price: Optional[int],
        min_bedrooms: Optional[int],
        max_bedrooms: Optional[int],
        limit: int
    ) -> List[Dict]:
        """RAG-first: semantic search then filter."""
        
        # Step 1: Semantic search (cast wide net - top 200)
        rag_results = self.rag.search(
            query,
            top_k=200,
            namespace="properties",
            include_metadata=True
        )
        
        if not rag_results:
            # Fallback to SQL
            return self._sql_only_search(
                lat, lng, radius_m, locality,
                property_type, listing_type,
                min_price, max_price, min_bedrooms, max_bedrooms,
                limit
            )
        
        # Extract property IDs
        property_ids = [r.id for r in rag_results]
        
        # Step 2: Fetch full property data from DB
        placeholders = ','.join(['?' for _ in property_ids])
        query_sql = f"""
            SELECT * FROM properties 
            WHERE property_id IN ({placeholders})
        """
        properties = self.db.execute(query_sql, tuple(property_ids)) or []
        
        # Step 3: Apply filters
        filtered = []
        for prop in properties:
            # Price filter
            if min_price and (not prop.get('price') or prop['price'] < min_price):
                continue
            if max_price and (not prop.get('price') or prop['price'] > max_price):
                continue
            
            # Bedrooms filter
            if min_bedrooms and (not prop.get('bedrooms') or prop['bedrooms'] < min_bedrooms):
                continue
            if max_bedrooms and (not prop.get('bedrooms') or prop['bedrooms'] > max_bedrooms):
                continue
            
            # Property type filter
            if property_type and prop.get('property_type') != property_type:
                continue
            
            # Listing type filter
            if listing_type and prop.get('listing_type') != listing_type:
                continue
            
            # Locality filter
            if locality:
                loc = prop.get('locality', '') or prop.get('area_name', '')
                if locality.lower() not in loc.lower():
                    continue
            
            # Location filter
            if lat and lng and radius_m:
                prop_lat = prop.get('latitude')
                prop_lng = prop.get('longitude')
                if prop_lat and prop_lng:
                    dist = self._haversine(lat, lng, prop_lat, prop_lng)
                    if dist > radius_m:
                        continue
                    prop['_distance'] = dist
            
            # Add RAG score
            rag_match = next((r for r in rag_results if r.id == prop.get('property_id')), None)
            if rag_match:
                prop['_rag_score'] = rag_match.score
                prop['_hybrid_score'] = rag_match.score  # Can combine with other signals
            
            filtered.append(prop)
        
        # Step 4: Sort by hybrid score (RAG score + distance penalty)
        filtered.sort(key=lambda x: x.get('_hybrid_score', 0), reverse=True)
        
        return filtered[:limit]
    
    def _sql_only_search(
        self,
        lat: Optional[float],
        lng: Optional[float],
        radius_m: Optional[int],
        locality: Optional[str],
        property_type: Optional[str],
        listing_type: Optional[str],
        min_price: Optional[int],
        max_price: Optional[int],
        min_bedrooms: Optional[int],
        max_bedrooms: Optional[int],
        limit: int
    ) -> List[Dict]:
        """SQL-only fallback search."""
        
        return self.db.search_properties(
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            locality=locality,
            property_type=property_type,
            listing_type=listing_type,
            min_price=min_price,
            max_price=max_price,
            min_bedrooms=min_bedrooms,
            max_bedrooms=max_bedrooms,
            limit=limit
        )
    
    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in meters."""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371000  # Earth radius in meters
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c


def get_hybrid_search(db_service=None, rag_service=None):
    """Factory to create hybrid search engine."""
    if db_service is None:
        try:
            from backend.database.query_service import get_query_service
        except ImportError:
            from database.query_service import get_query_service
        db_service = get_query_service()
    
    if rag_service is None:
        try:
            from backend.rag_service import get_rag_service
        except ImportError:
            from rag_service import get_rag_service
        rag_service = get_rag_service(Path(__file__).parent.parent / 'src' / 'data')
    
    return HybridSearchEngine(db_service, rag_service)
