"""
Local Geocoder using extracted OSM data
Searches places, transport, POIs, roads for any location in Bangalore
No external dependencies - fully offline
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import re
from difflib import SequenceMatcher

class LocalGeocoder:
    def __init__(self, osm_data_dir: Path):
        self.osm_data_dir = osm_data_dir
        self.derived_dir = osm_data_dir / 'derived'
        self.places = []
        self.transport = []
        self.pois = []
        self.loaded = False
        
        # Static fallback for major landmarks and neighborhoods
        self.static_landmarks = [
            # Airports
            {
                'name': 'Kempegowda International Airport',
                'aliases': ['airport', 'bangalore airport', 'blr airport', 'kia', 'kempegowda airport'],
                'lat': 13.1986, 'lng': 77.7066,
                'type': 'airport', 'source': 'static', 'importance': 1.0
            },
            {
                'name': 'Bengaluru International Airport',
                'aliases': ['international airport'],
                'lat': 13.1986, 'lng': 77.7066,
                'type': 'airport', 'source': 'static', 'importance': 1.0
            },
            
            # Major Neighborhoods
            {
                'name': 'Whitefield',
                'aliases': ['white field', 'whitefield bangalore'],
                'lat': 12.9698, 'lng': 77.7499,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'Indiranagar',
                'aliases': ['indira nagar', 'indiranagar bangalore'],
                'lat': 12.9716, 'lng': 77.6412,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'Hebbal',
                'aliases': ['hebbal bangalore'],
                'lat': 13.0359, 'lng': 77.5946,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'Koramangala',
                'aliases': ['koramangala bangalore', 'koramangla'],
                'lat': 12.9352, 'lng': 77.6245,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'Jayanagar',
                'aliases': ['jaya nagar', 'jayanagar bangalore'],
                'lat': 12.9250, 'lng': 77.5800,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'MG Road',
                'aliases': ['mg road bangalore', 'mahatma gandhi road', 'brigade road'],
                'lat': 12.9758, 'lng': 77.6066,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'Malleshwaram',
                'aliases': ['malleshwaram bangalore', 'malleswaram'],
                'lat': 13.0035, 'lng': 77.5685,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            
            # Malls and Landmarks
            {
                'name': 'Phoenix Marketcity',
                'aliases': ['phoenix mall', 'marketcity'],
                'lat': 12.9952, 'lng': 77.6969,
                'type': 'mall', 'source': 'static', 'importance': 0.95
            },
            {
                'name': 'Orion Mall',
                'aliases': ['orion'],
                'lat': 13.0102, 'lng': 77.5562,
                'type': 'mall', 'source': 'static', 'importance': 0.95
            },
            
            # Tech Hubs
            {
                'name': 'Manyata Tech Park',
                'aliases': ['manyata', 'manyata business park'],
                'lat': 13.0474, 'lng': 77.6212,
                'type': 'tech_park', 'source': 'static', 'importance': 0.95
            },
            {
                'name': 'Electronic City',
                'aliases': ['e-city', 'ecity', 'electronic city bangalore'],
                'lat': 12.8456, 'lng': 77.6603,
                'type': 'tech_hub', 'source': 'static', 'importance': 0.95
            },
            
            # Additional Major Neighborhoods
            {
                'name': 'Sarjapur Road',
                'aliases': ['sarjapur', 'sarjapura', 'sarjapur bangalore', 'sarjapura road'],
                'lat': 12.9100, 'lng': 77.6800,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'HSR Layout',
                'aliases': ['hsr', 'hsr layout bangalore'],
                'lat': 12.9116, 'lng': 77.6474,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'BTM Layout',
                'aliases': ['btm', 'btm layout bangalore'],
                'lat': 12.9166, 'lng': 77.6101,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'Bellandur',
                'aliases': ['bellandur bangalore', 'bellundur'],
                'lat': 12.9260, 'lng': 77.6762,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'Marathahalli',
                'aliases': ['marathalli', 'marathahalli bangalore'],
                'lat': 12.9591, 'lng': 77.7010,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'Yelahanka',
                'aliases': ['yelahanka bangalore', 'yalahanka'],
                'lat': 13.1007, 'lng': 77.5963,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'JP Nagar',
                'aliases': ['jp nagar bangalore', 'jayaprakash nagar'],
                'lat': 12.9063, 'lng': 77.5857,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'Banashankari',
                'aliases': ['banashankari bangalore', 'bsk'],
                'lat': 12.9255, 'lng': 77.5468,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'Mahadevapura',
                'aliases': ['mahadevpura', 'mahadevapura bangalore'],
                'lat': 12.9914, 'lng': 77.6940,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'Silk Board',
                'aliases': ['silk board junction', 'silkboard'],
                'lat': 12.9177, 'lng': 77.6238,
                'type': 'junction', 'source': 'static', 'importance': 0.95
            },
            {
                'name': 'Basavanagudi',
                'aliases': ['basavanagudi bangalore', 'bull temple road'],
                'lat': 12.9422, 'lng': 77.5755,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'Rajajinagar',
                'aliases': ['rajaji nagar', 'rajajinagar bangalore'],
                'lat': 12.9914, 'lng': 77.5521,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.98
            },
            {
                'name': 'Devanahalli',
                'aliases': ['devanahalli bangalore', 'devanhalli'],
                'lat': 13.2473, 'lng': 77.7135,
                'type': 'neighborhood', 'source': 'static', 'importance': 0.95
            },
            
            # Major Landmarks
            {
                'name': 'Cubbon Park',
                'aliases': ['cubbon park bangalore'],
                'lat': 12.9763, 'lng': 77.5929,
                'type': 'park', 'source': 'static', 'importance': 0.95
            },
            {
                'name': 'Lalbagh Garden',
                'aliases': ['lalbagh', 'lal bagh', 'lalbagh botanical garden'],
                'lat': 12.9507, 'lng': 77.5848,
                'type': 'park', 'source': 'static', 'importance': 0.95
            },
            {
                'name': 'Bangalore Palace',
                'aliases': ['palace grounds', 'bangalore palace grounds'],
                'lat': 12.9988, 'lng': 77.5922,
                'type': 'landmark', 'source': 'static', 'importance': 0.95
            },
            {
                'name': 'Vidhana Soudha',
                'aliases': ['vidhan soudha', 'vidhana soudha bangalore'],
                'lat': 12.9795, 'lng': 77.5912,
                'type': 'landmark', 'source': 'static', 'importance': 0.95
            },
        ]
        
    def load_data(self):
        """Load all searchable data from DATABASE"""
        if self.loaded:
            return
            
        print("[INFO] Loading local geocoder data from database...")
        
        try:
            try:
                from backend.database.query_service import get_query_service
            except ImportError:
                from database.query_service import get_query_service
            db = get_query_service()
            
            # Load places from database
            places_data = db.get_all_places()
            for p in places_data:
                if p.get('name') and p.get('lat') and p.get('lng'):
                    self.places.append({
                        'name': p['name'],
                        'type': p.get('type', 'place'),
                        'lat': p['lat'],
                        'lng': p['lng'],
                        'tags': {},
                        'source': 'places'
                    })
            print(f"  [OK] Loaded {len(self.places)} places from DB")
            
            # Load transport from database
            transport_data = db.get_all_transport()
            seen_names = set()
            for t in transport_data:
                name = t.get('name')
                if name and t.get('lat') and t.get('lng'):
                    name_key = name.lower()
                    if name_key not in seen_names:
                        seen_names.add(name_key)
                        self.transport.append({
                            'name': name,
                            'type': t.get('type', 'transport'),
                            'lat': t['lat'],
                            'lng': t['lng'],
                            'tags': {},
                            'source': 'transport'
                        })
            print(f"  [OK] Loaded {len(self.transport)} transport stops from DB")
            
            # Load POIs from database
            pois_data = db.get_all_pois()
            for poi in pois_data:
                name = poi.get('name')
                if name and poi.get('lat') and poi.get('lng'):
                    self.pois.append({
                        'name': name,
                        'type': poi.get('subcategory') or poi.get('category') or 'poi',
                        'lat': poi['lat'],
                        'lng': poi['lng'],
                        'tags': {},
                        'source': 'pois'
                    })
            print(f"  [OK] Loaded {len(self.pois)} POIs from DB")
            
        except Exception as e:
            print(f"[ERROR] Failed to load from database: {e}")
            import traceback
            traceback.print_exc()
            self._load_from_files()
        
        self.loaded = True
        total = len(self.places) + len(self.transport) + len(self.pois)
        print(f"[OK] Local geocoder ready: {total} searchable locations")
    
    def _load_from_files(self):
        """Fallback: Load from GeoJSON files"""
        places_file = self.derived_dir / 'places.geojson'
        if places_file.exists():
            with open(places_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for feature in data.get('features', []):
                    props = feature.get('properties', {})
                    coords = feature.get('geometry', {}).get('coordinates', [])
                    if props.get('name') and len(coords) >= 2:
                        self.places.append({
                            'name': props['name'], 'type': props.get('subtype', 'place'),
                            'lat': coords[1], 'lng': coords[0], 'tags': {}, 'source': 'places'
                        })
        
        transport_file = self.derived_dir / 'transport.geojson'
        if transport_file.exists():
            with open(transport_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for feature in data.get('features', []):
                    props = feature.get('properties', {})
                    coords = feature.get('geometry', {}).get('coordinates', [])
                    if props.get('name') and len(coords) >= 2:
                        self.transport.append({
                            'name': props['name'], 'type': props.get('subtype', 'transport'),
                            'lat': coords[1], 'lng': coords[0], 'tags': {}, 'source': 'transport'
                        })
        
        pois_file = self.derived_dir / 'pois.geojson'
        if pois_file.exists():
            with open(pois_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for feature in data.get('features', []):
                    props = feature.get('properties', {})
                    coords = feature.get('geometry', {}).get('coordinates', [])
                    if props.get('name') and len(coords) >= 2:
                        self.pois.append({
                            'name': props['name'], 'type': props.get('subtype', 'poi'),
                            'lat': coords[1], 'lng': coords[0], 'tags': {}, 'source': 'pois'
                        })
    
    def _similarity(self, a: str, b: str) -> float:
        """Calculate string similarity score"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def _match_score(self, query: str, name: str) -> float:
        """Calculate match score for a query against a name"""
        query_lower = query.lower().strip()
        name_lower = name.lower().strip()
        
        # Exact match
        if query_lower == name_lower:
            return 1.0
        
        # Query is contained in name
        if query_lower in name_lower:
            return 0.9
        
        # Name is contained in query
        if name_lower in query_lower:
            return 0.85
        
        # Word-level matching
        query_words = set(query_lower.split())
        name_words = set(name_lower.split())
        common_words = query_words & name_words
        if common_words:
            return 0.7 + (0.2 * len(common_words) / max(len(query_words), len(name_words)))
        
        # Fuzzy similarity
        return self._similarity(query_lower, name_lower) * 0.6
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for locations matching the query"""
        self.load_data()
        
        if not query or len(query.strip()) < 2:
            return []
        
        query = query.strip()
        results = []
        
        # Search all sources with scoring
        all_locations = []
        
        # Check static landmarks first (highest priority)
        query_lower = query.lower()
        for landmark in self.static_landmarks:
            # Check name match
            name_score = self._match_score(query, landmark['name'])
            # Check aliases
            alias_score = 0
            for alias in landmark.get('aliases', []):
                alias_score = max(alias_score, self._match_score(query, alias))
            
            best_score = max(name_score, alias_score)
            if best_score > 0.3:
                all_locations.append({
                    'name': landmark['name'],
                    'lat': landmark['lat'],
                    'lng': landmark['lng'],
                    'type': landmark['type'],
                    'source': landmark['source'],
                    'tags': {},
                    'score': best_score * 1.5,  # Boost static landmarks
                    'importance': landmark['importance']
                })
        
        # Places get priority boost
        for loc in self.places:
            score = self._match_score(query, loc['name'])
            if score > 0.3:
                all_locations.append({**loc, 'score': score * 1.2, 'importance': 0.9})
        
        # Transport stops
        for loc in self.transport:
            score = self._match_score(query, loc['name'])
            if score > 0.3:
                all_locations.append({**loc, 'score': score * 1.1, 'importance': 0.8})
        
        # POIs
        for loc in self.pois:
            score = self._match_score(query, loc['name'])
            if score > 0.3:
                all_locations.append({**loc, 'score': score, 'importance': 0.7})
        
        # Sort by score (descending)
        all_locations.sort(key=lambda x: x['score'], reverse=True)
        
        # Format results
        for loc in all_locations[:limit]:
            results.append({
                'name': loc['name'],
                'display_name': f"{loc['name']}, Bangalore ({loc['source']})",
                'lat': loc['lat'],
                'lng': loc['lng'],
                'type': loc['type'],
                'source': loc['source'],
                'importance': loc['importance'],
                'score': loc['score']
            })
        
        return results
    
    def reverse(self, lat: float, lng: float, radius_km: float = 2.0) -> Optional[Dict[str, Any]]:
        """
        Reverse geocode: find nearest place to coordinates.
        Returns dict with name, type, lat, lng.
        """
        # Simple distance calculation
        def distance(p1_lat, p1_lng, p2_lat, p2_lng):
            from math import radians, cos, sin, asin, sqrt
            dLat = radians(p2_lat - p1_lat)
            dLng = radians(p2_lng - p1_lng)
            a = sin(dLat/2) * sin(dLat/2) + cos(radians(p1_lat)) * cos(radians(p2_lat)) * sin(dLng/2) * sin(dLng/2)
            return 6371 * 2 * asin(sqrt(a))
        
        nearest = None
        nearest_dist = radius_km
        
        # Check all locations
        all_locations = []
        all_locations.extend(self.places)
        all_locations.extend(self.transport)
        all_locations.extend(self.pois)
        
        for loc in all_locations:
            if loc.get('lat') and loc.get('lng'):
                dist = distance(lat, lng, loc['lat'], loc['lng'])
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = loc
        
        if nearest:
            return {
                'name': nearest['name'],
                'type': nearest.get('type', 'place'),
                'lat': nearest['lat'],
                'lng': nearest['lng'],
                'distance_km': nearest_dist
            }
        
        return None
    
    def geocode(self, query: str) -> Optional[Dict[str, Any]]:
        """Get the best match for a query"""
        results = self.search(query, limit=1)
        return results[0] if results else None


# Singleton instance
_geocoder: Optional[LocalGeocoder] = None

def get_local_geocoder(osm_data_dir: Path) -> LocalGeocoder:
    global _geocoder
    if _geocoder is None:
        _geocoder = LocalGeocoder(osm_data_dir)
    return _geocoder
