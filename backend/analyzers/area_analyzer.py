"""
Area Analysis Engine for Valora AI
Generates real-time area summaries from DATABASE
"""

import json
from pathlib import Path
from typing import Dict, List, Any
import math

class AreaAnalyzer:
    def __init__(self, osm_data_dir: Path):
        self.osm_dir = osm_data_dir
        self.derived_dir = osm_data_dir / 'derived'
        
        # Cache for loaded data
        self._pois_cache = None
        self._roads_cache = None
        self._transport_cache = None
        self._landuse_cache = None
        self._db = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database connection"""
        try:
            try:
                from backend.database.query_service import get_query_service
            except ImportError:
                from database.query_service import get_query_service
            self._db = get_query_service()
        except:
            self._db = None
        
    def _load_geojson(self, filename: str):
        """Load and cache GeoJSON file (fallback)"""
        filepath = self.derived_dir / filename
        if not filepath.exists():
            return {'features': []}
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_pois(self):
        if self._pois_cache is None:
            if self._db:
                # Load from database
                pois = self._db.get_all_pois()
                self._pois_cache = {'features': [
                    {'properties': {'name': p.get('name'), 'category': p.get('category'), 'subcategory': p.get('subcategory')},
                     'geometry': {'type': 'Point', 'coordinates': [p.get('lng'), p.get('lat')]}}
                    for p in pois if p.get('lat') and p.get('lng')
                ]}
            else:
                self._pois_cache = self._load_geojson('pois.geojson')
        return self._pois_cache
    
    def _get_roads(self):
        if self._roads_cache is None:
            self._roads_cache = self._load_geojson('roads.geojson')
        return self._roads_cache
    
    def _get_transport(self):
        if self._transport_cache is None:
            if self._db:
                transport = self._db.get_all_transport()
                self._transport_cache = {'features': [
                    {'properties': {'name': t.get('name'), 'type': t.get('type'), 'category': t.get('type')},
                     'geometry': {'type': 'Point', 'coordinates': [t.get('lng'), t.get('lat')]}}
                    for t in transport if t.get('lat') and t.get('lng')
                ]}
            else:
                self._transport_cache = self._load_geojson('transport.geojson')
        return self._transport_cache
    
    def _get_landuse(self):
        if self._landuse_cache is None:
            self._landuse_cache = self._load_geojson('landuse.geojson')
        return self._landuse_cache
    
    def _distance(self, lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """Calculate distance in meters using Haversine formula"""
        R = 6371000  # Earth radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _in_radius(self, feature, center_lng: float, center_lat: float, radius_m: float) -> bool:
        """Check if feature is within radius of center point"""
        coords = feature['geometry']['coordinates']
        
        if feature['geometry']['type'] == 'Point':
            dist = self._distance(coords[0], coords[1], center_lng, center_lat)
            return dist <= radius_m
        elif feature['geometry']['type'] == 'LineString':
            # Check if any point is within radius
            for coord in coords:
                dist = self._distance(coord[0], coord[1], center_lng, center_lat)
                if dist <= radius_m:
                    return True
        elif feature['geometry']['type'] == 'Polygon':
            # Check if any point in outer ring is within radius
            for coord in coords[0]:
                dist = self._distance(coord[0], coord[1], center_lng, center_lat)
                if dist <= radius_m:
                    return True
        
        return False
    
    def analyze_area(self, lng: float, lat: float, radius_m: float = 1000) -> Dict[str, Any]:
        """
        Analyze area around a point
        Returns real-time analysis based on OSM data
        """
        
        # Get POIs in radius
        pois_data = self._get_pois()
        nearby_pois = [f for f in pois_data['features'] if self._in_radius(f, lng, lat, radius_m)]
        
        # Categorize POIs
        poi_counts = {}
        top_pois = []
        for poi in nearby_pois:
            props = poi['properties']
            poi_type = props.get('type') or props.get('category', 'unknown')
            subtype = props.get('subtype') or props.get('subcategory', 'unknown')
            
            key = f"{poi_type}_{subtype}"
            poi_counts[key] = poi_counts.get(key, 0) + 1
            
            if props.get('name'):
                coords = poi['geometry']['coordinates']
                dist = self._distance(coords[0], coords[1], lng, lat)
                top_pois.append({
                    'name': props['name'],
                    'type': poi_type,
                    'subtype': subtype,
                    'distance_m': round(dist)
                })
        
        # Sort by distance and take top 10
        top_pois.sort(key=lambda x: x['distance_m'])
        top_pois = top_pois[:10]
        
        # Get transport in radius
        transport_data = self._get_transport()
        nearby_transport = [f for f in transport_data['features'] if self._in_radius(f, lng, lat, radius_m)]
        
        transport_stops = []
        for t in nearby_transport:
            props = t['properties']
            t_type = props.get('type') or props.get('category', '')
            if props.get('name'):
                coords = t['geometry']['coordinates']
                dist = self._distance(coords[0], coords[1], lng, lat)
                transport_stops.append({
                    'name': props['name'],
                    'type': props.get('subtype', 'unknown'),
                    'distance_m': round(dist)
                })
        
        transport_stops.sort(key=lambda x: x['distance_m'])
        transport_stops = transport_stops[:5]
        
        # Get roads in radius
        roads_data = self._get_roads()
        nearby_roads = [f for f in roads_data['features'] if self._in_radius(f, lng, lat, radius_m)]
        
        road_profile = {}
        for road in nearby_roads:
            props = road['properties']
            road_type = props.get('subtype', 'unknown')
            road_profile[road_type] = road_profile.get(road_type, 0) + 1
        
        # Get landuse in radius
        landuse_data = self._get_landuse()
        nearby_landuse = [f for f in landuse_data['features'] if self._in_radius(f, lng, lat, radius_m)]
        
        landuse_mix = {}
        for lu in nearby_landuse:
            props = lu['properties']
            lu_type = props.get('subtype', 'unknown')
            landuse_mix[lu_type] = landuse_mix.get(lu_type, 0) + 1
        
        # Build summary
        summary = {
            'center': {'lng': lng, 'lat': lat},
            'radius_m': radius_m,
            'poi_summary': {
                'total': len(nearby_pois),
                'by_category': poi_counts,
                'top_nearby': top_pois
            },
            'transport': {
                'total_stops': len(transport_stops),
                'nearest_stops': transport_stops
            },
            'roads': {
                'total': len(nearby_roads),
                'by_type': road_profile
            },
            'landuse': {
                'total': len(nearby_landuse),
                'by_type': landuse_mix
            }
        }
        
        return summary
    
    def generate_area_insights(self, summary: Dict[str, Any]) -> str:
        """
        Generate human-readable insights from area summary
        """
        insights = []
        
        # POI insights
        poi_total = summary['poi_summary']['total']
        if poi_total > 0:
            insights.append(f"📍 **{poi_total} POIs** within {summary['radius_m']}m radius")
            
            # Top categories
            categories = summary['poi_summary']['by_category']
            if categories:
                top_cat = sorted(categories.items(), key=lambda x: -x[1])[:3]
                cat_str = ", ".join([f"{k.replace('_', ' ')}: {v}" for k, v in top_cat])
                insights.append(f"   Top categories: {cat_str}")
        
        # Transport insights
        transport = summary['transport']
        if transport['nearest_stops']:
            nearest = transport['nearest_stops'][0]
            insights.append(f"🚇 Nearest transit: **{nearest['name']}** ({nearest['distance_m']}m away)")
        
        # Road insights
        roads = summary['roads']
        if roads['by_type']:
            major_roads = sum(v for k, v in roads['by_type'].items() if k in ['motorway', 'trunk', 'primary', 'secondary'])
            if major_roads > 0:
                insights.append(f"🛣️ **{major_roads} major roads** in area (good connectivity)")
        
        # Landuse insights
        landuse = summary['landuse']
        if landuse['by_type']:
            dominant = max(landuse['by_type'].items(), key=lambda x: x[1])
            insights.append(f"🏘️ Dominant landuse: **{dominant[0]}**")
        
        return "\n".join(insights) if insights else "No significant features found in this area."
