"""
Property Service for Valora AI
Provides real estate property queries from posted_properties data
"""

import json
import math
from pathlib import Path
from typing import Optional, List, Dict, Any
from functools import lru_cache


class PropertyService:
    """Service for querying real estate property listings"""
    
    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / 'src' / 'data' / 'posted_properties'
        self.data_dir = data_dir
        self.properties = {}
        self.property_index = {}  # Spatial index for nearby queries
        self._load_properties()
    
    def _load_properties(self):
        """Load all property files into memory"""
        property_files = {
            'residential_apartment': 'bangalore-residential-apartment.json',
            'residential_apartment_rent': 'bangalore-residential-apartment-rent.json',
            'residential_house': 'bangalore-residential-house.json',
            'residential_house_rent': 'bangalore-residential-house-rent.json',
            'residential_plot': 'bangalore-residential-plot.json',
            'commercial_land': 'bangalore-commercial-land.json',
            'commercial_office': 'bangalore-commercial-officespace.json',
            'commercial_shop_rent': 'bangalore-commercial-shop-rent.json',
            'commercial_warehouse': 'bangalore-commercial-warehouse.json',
            'commercial_industrial_building': 'bangalore-commercial-industrialbuilding.json',
            'commercial_industrial_shed': 'bangalore-commercial-industrialshed.json',
            'agricultural_land': 'bangalore-agriculturalland.json',
            'agricultural_farmhouse': 'bangalore-farmhouse.json',
        }
        
        total_loaded = 0
        for category, filename in property_files.items():
            filepath = self.data_dir / filename
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.properties[category] = data
                        total_loaded += len(data)
                        
                        # Build spatial index
                        for prop in data:
                            if prop.get('location'):
                                try:
                                    lat, lng = map(float, prop['location'].split(','))
                                    prop['_lat'] = lat
                                    prop['_lng'] = lng
                                    prop['_category'] = category
                                except:
                                    pass
                except Exception as e:
                    print(f"⚠️ Failed to load {filename}: {e}")
            else:
                print(f"⚠️ Property file not found: {filename}")
        
        print(f"✅ Loaded {total_loaded} properties across {len(self.properties)} categories")
    
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
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_bedrooms: Optional[int] = None,
        max_bedrooms: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search properties with filters
        
        Args:
            lat, lng: Center point for radius search
            radius_m: Search radius in meters (default 2000m)
            category: 'residential', 'commercial', 'agricultural'
            property_type: 'apartment', 'house', 'plot', 'land', etc.
            min_price, max_price: Price range filter
            min_bedrooms, max_bedrooms: Bedroom count filter
            limit: Maximum results to return
        
        Returns:
            List of matching properties sorted by distance (if location provided)
        """
        results = []
        
        # Determine which categories to search
        categories_to_search = []
        if category:
            categories_to_search = [k for k in self.properties.keys() if category in k]
        else:
            categories_to_search = list(self.properties.keys())
        
        if property_type:
            categories_to_search = [k for k in categories_to_search if property_type in k]
        
        for cat in categories_to_search:
            for prop in self.properties.get(cat, []):
                # Location filter
                if lat is not None and lng is not None:
                    prop_lat = prop.get('_lat')
                    prop_lng = prop.get('_lng')
                    if prop_lat is None or prop_lng is None:
                        continue
                    distance = self._haversine_distance(lat, lng, prop_lat, prop_lng)
                    if distance > radius_m:
                        continue
                    prop['_distance'] = distance
                
                # Price filter
                price = prop.get('price')
                if price:
                    if min_price and price < min_price:
                        continue
                    if max_price and price > max_price:
                        continue
                
                # Bedroom filter
                bedrooms = prop.get('bedrooms')
                if bedrooms:
                    if min_bedrooms and bedrooms < min_bedrooms:
                        continue
                    if max_bedrooms and bedrooms > max_bedrooms:
                        continue
                
                results.append(prop)
        
        # Sort by distance if location provided
        if lat is not None and lng is not None:
            results.sort(key=lambda x: x.get('_distance', float('inf')))
        else:
            # Sort by price
            results.sort(key=lambda x: x.get('price', 0) or 0)
        
        return results[:limit]
    
    def get_by_id(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get a property by its ID"""
        for category, props in self.properties.items():
            for prop in props:
                if str(prop.get('id')) == str(property_id):
                    return prop
        return None
    
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
        """Get count of properties by category"""
        return {cat: len(props) for cat, props in self.properties.items()}


# Singleton instance
_property_service = None

def get_property_service(data_dir: Path = None) -> PropertyService:
    """Get or create PropertyService singleton"""
    global _property_service
    if _property_service is None:
        _property_service = PropertyService(data_dir)
    return _property_service
