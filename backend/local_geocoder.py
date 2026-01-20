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
        ]
        
    def load_data(self):
        """Load all searchable OSM data"""
        if self.loaded:
            return
            
        print("📍 Loading local geocoder data...")
        
        # Load places (neighborhoods, suburbs, localities)
        places_file = self.derived_dir / 'places.geojson'
        if places_file.exists():
            with open(places_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for feature in data.get('features', []):
                    props = feature.get('properties', {})
                    coords = feature.get('geometry', {}).get('coordinates', [])
                    if props.get('name') and len(coords) >= 2:
                        self.places.append({
                            'name': props['name'],
                            'type': props.get('subtype', 'place'),
                            'lat': coords[1],
                            'lng': coords[0],
                            'tags': props.get('tags', {}),
                            'source': 'places'
                        })
            print(f"  ✓ Loaded {len(self.places)} places")
        
        # Load transport (bus stops, metro stations)
        transport_file = self.derived_dir / 'transport.geojson'
        if transport_file.exists():
            with open(transport_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                seen_names = set()
                for feature in data.get('features', []):
                    props = feature.get('properties', {})
                    coords = feature.get('geometry', {}).get('coordinates', [])
                    name = props.get('name')
                    if name and len(coords) >= 2:
                        # Deduplicate by name (keep first occurrence)
                        name_key = name.lower()
                        if name_key not in seen_names:
                            seen_names.add(name_key)
                            self.transport.append({
                                'name': name,
                                'type': props.get('subtype', 'transport'),
                                'lat': coords[1],
                                'lng': coords[0],
                                'tags': props.get('tags', {}),
                                'source': 'transport'
                            })
                        # Also check alt_name
                        alt_name = props.get('tags', {}).get('alt_name')
                        if alt_name:
                            alt_key = alt_name.lower()
                            if alt_key not in seen_names:
                                seen_names.add(alt_key)
                                self.transport.append({
                                    'name': alt_name,
                                    'type': props.get('subtype', 'transport'),
                                    'lat': coords[1],
                                    'lng': coords[0],
                                    'tags': props.get('tags', {}),
                                    'source': 'transport'
                                })
            print(f"  ✓ Loaded {len(self.transport)} transport stops")
        
        # Load POIs (landmarks, shops, hospitals, etc.)
        pois_file = self.derived_dir / 'pois.geojson'
        if pois_file.exists():
            with open(pois_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for feature in data.get('features', []):
                    props = feature.get('properties', {})
                    coords = feature.get('geometry', {}).get('coordinates', [])
                    name = props.get('name')
                    if name and len(coords) >= 2:
                        self.pois.append({
                            'name': name,
                            'type': props.get('subtype', 'poi'),
                            'lat': coords[1],
                            'lng': coords[0],
                            'tags': props.get('tags', {}),
                            'source': 'pois'
                        })
            print(f"  ✓ Loaded {len(self.pois)} POIs")
        
        self.loaded = True
        total = len(self.places) + len(self.transport) + len(self.pois)
        print(f"📍 Local geocoder ready: {total} searchable locations")
    
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
