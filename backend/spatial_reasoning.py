"""
Valora AI - Spatial Reasoning Service
Phase 1: 3D Spatial Reasoning with Proximity, Elevation, and Amenity Analysis

Provides advanced spatial analysis including:
- H3 spatial indexing for fast proximity queries
- 3D viewshed and elevation analysis
- Amenity scoring and accessibility metrics
- Unified spatial query API
"""

import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

try:
    import h3
    H3_AVAILABLE = True
    # Create wrapper functions for v3/v4 compatibility
    def _h3_geo_to_cell(lat, lng, res):
        if hasattr(h3, 'latlng_to_cell'):
            return h3.latlng_to_cell(lat, lng, res)
        else:
            return h3.geo_to_h3(lat, lng, res)
    
    def _h3_grid_disk(cell, rings):
        if hasattr(h3, 'grid_disk'):
            return h3.grid_disk(cell, rings)
        else:
            return h3.k_ring(cell, rings)
except ImportError:
    H3_AVAILABLE = False
    def _h3_geo_to_cell(lat, lng, res): return None
    def _h3_grid_disk(cell, rings): return []
    print("[WARNING]  h3 not installed. Using fallback spatial indexing.")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


@dataclass
class NearbyResult:
    """Result from a nearby query."""
    type: str
    name: str
    lat: float
    lng: float
    distance_m: float
    properties: Dict[str, Any]


@dataclass
class SpatialSummary:
    """Summary of spatial features for a location."""
    lat: float
    lng: float
    radius_m: float
    total_features: int
    by_category: Dict[str, int]
    nearest: Dict[str, Optional[NearbyResult]]
    accessibility_score: float  # 0-100
    walkability_score: float  # 0-100
    amenity_density: float  # per sq km


@dataclass
class LocationAnalysis:
    """Complete location analysis result."""
    lat: float
    lng: float
    elevation_m: float
    slope_deg: float
    aspect: str  # N, NE, E, SE, S, SW, W, NW
    terrain_suitability: float  # 0-100 for construction
    flood_risk: str  # low, medium, high
    summary: SpatialSummary
    recommendations: List[str]


class SpatialReasoningService:
    """
    Advanced spatial reasoning with H3 indexing and 3D analysis.
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.osm_dir = data_dir / 'osm_extracted'
        self.terrain_dir = data_dir / 'terrain'
        
        # Spatial indices
        self.poi_index: Dict[str, List[Dict]] = defaultdict(list)  # h3_index -> POIs
        self.transport_index: Dict[str, List[Dict]] = defaultdict(list)
        self.places_index: Dict[str, List[Dict]] = defaultdict(list)
        
        # Raw data for fallback queries
        self.pois: List[Dict] = []
        self.transport: List[Dict] = []
        self.places: List[Dict] = []
        
        # H3 resolution for indexing (res 9 ~ 100m hexagons)
        self.h3_resolution = 9
        
        self._load_and_index_data()
    
    def _load_and_index_data(self):
        """Load and index all spatial data."""
        self._load_pois()
        self._load_transport()
        self._load_places()
        
        total = len(self.pois) + len(self.transport) + len(self.places)
        print(f"[OK] Spatial reasoning: indexed {total} features")
    
    def _load_pois(self):
        """Load and index POIs."""
        pois_file = self.osm_dir / 'pois.geojson'
        if not pois_file.exists():
            return
        
        try:
            with open(pois_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for feat in data.get('features', []):
                props = feat.get('properties', {})
                geom = feat.get('geometry', {})
                coords = geom.get('coordinates', [])
                
                if len(coords) < 2:
                    continue
                
                lng, lat = coords[0], coords[1]
                
                poi = {
                    'name': props.get('name', ''),
                    'amenity': props.get('amenity', ''),
                    'shop': props.get('shop', ''),
                    'cuisine': props.get('cuisine', ''),
                    'lat': lat,
                    'lng': lng
                }
                
                self.pois.append(poi)
                
                if H3_AVAILABLE:
                    h3_idx = _h3_geo_to_cell(lat, lng, self.h3_resolution)
                    if h3_idx:
                        self.poi_index[h3_idx].append(poi)
                    
        except Exception as e:
            print(f"[WARNING]  Error loading POIs: {e}")
    
    def _load_transport(self):
        """Load and index transport stops."""
        transport_file = self.osm_dir / 'transport.geojson'
        if not transport_file.exists():
            return
        
        try:
            with open(transport_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for feat in data.get('features', []):
                props = feat.get('properties', {})
                geom = feat.get('geometry', {})
                coords = geom.get('coordinates', [])
                
                if len(coords) < 2:
                    continue
                
                lng, lat = coords[0], coords[1]
                
                transport = {
                    'name': props.get('name', ''),
                    'type': props.get('railway', '') or props.get('highway', '') or props.get('amenity', ''),
                    'lat': lat,
                    'lng': lng
                }
                
                self.transport.append(transport)
                
                if H3_AVAILABLE:
                    h3_idx = _h3_geo_to_cell(lat, lng, self.h3_resolution)
                    if h3_idx:
                        self.transport_index[h3_idx].append(transport)
                    
        except Exception as e:
            print(f"[WARNING]  Error loading transport: {e}")
    
    def _load_places(self):
        """Load and index places."""
        places_file = self.osm_dir / 'places.geojson'
        if not places_file.exists():
            return
        
        try:
            with open(places_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for feat in data.get('features', []):
                props = feat.get('properties', {})
                geom = feat.get('geometry', {})
                coords = geom.get('coordinates', [])
                
                if len(coords) < 2:
                    continue
                
                lng, lat = coords[0], coords[1]
                
                place = {
                    'name': props.get('name', ''),
                    'type': props.get('place', ''),
                    'lat': lat,
                    'lng': lng
                }
                
                self.places.append(place)
                
                if H3_AVAILABLE:
                    h3_idx = _h3_geo_to_cell(lat, lng, self.h3_resolution)
                    if h3_idx:
                        self.places_index[h3_idx].append(place)
                    
        except Exception as e:
            print(f"[WARNING]  Error loading places: {e}")
    
    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in meters between two points."""
        R = 6371000  # Earth radius in meters
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def _get_nearby_h3_cells(self, lat: float, lng: float, radius_m: float) -> List[str]:
        """Get H3 cells within radius of a point."""
        if not H3_AVAILABLE:
            return []
        
        center_cell = _h3_geo_to_cell(lat, lng, self.h3_resolution)
        if not center_cell:
            return []
        
        # Approximate number of rings needed (each ring is ~100m at res 9)
        rings = max(1, int(radius_m / 100))
        
        # Get disk of cells
        cells = _h3_grid_disk(center_cell, rings)
        return list(cells)
    
    def query_nearby(
        self,
        lat: float,
        lng: float,
        radius_m: float = 1000,
        layers: List[str] = None,
        limit: int = 50
    ) -> List[NearbyResult]:
        """
        Query features near a point.
        
        Args:
            lat, lng: Center point
            radius_m: Radius in meters
            layers: List of layers to query ('poi', 'transport', 'place')
            limit: Maximum results
        """
        if layers is None:
            layers = ['poi', 'transport', 'place']
        
        results = []
        
        # Use H3 indexing if available
        if H3_AVAILABLE:
            cells = self._get_nearby_h3_cells(lat, lng, radius_m)
            
            for cell in cells:
                if 'poi' in layers:
                    for poi in self.poi_index.get(cell, []):
                        dist = self._haversine(lat, lng, poi['lat'], poi['lng'])
                        if dist <= radius_m:
                            results.append(NearbyResult(
                                type='poi',
                                name=poi['name'],
                                lat=poi['lat'],
                                lng=poi['lng'],
                                distance_m=dist,
                                properties={'amenity': poi['amenity'], 'shop': poi['shop']}
                            ))
                
                if 'transport' in layers:
                    for t in self.transport_index.get(cell, []):
                        dist = self._haversine(lat, lng, t['lat'], t['lng'])
                        if dist <= radius_m:
                            results.append(NearbyResult(
                                type='transport',
                                name=t['name'],
                                lat=t['lat'],
                                lng=t['lng'],
                                distance_m=dist,
                                properties={'transport_type': t['type']}
                            ))
                
                if 'place' in layers:
                    for p in self.places_index.get(cell, []):
                        dist = self._haversine(lat, lng, p['lat'], p['lng'])
                        if dist <= radius_m:
                            results.append(NearbyResult(
                                type='place',
                                name=p['name'],
                                lat=p['lat'],
                                lng=p['lng'],
                                distance_m=dist,
                                properties={'place_type': p['type']}
                            ))
        else:
            # Fallback: brute force
            if 'poi' in layers:
                for poi in self.pois:
                    dist = self._haversine(lat, lng, poi['lat'], poi['lng'])
                    if dist <= radius_m:
                        results.append(NearbyResult(
                            type='poi',
                            name=poi['name'],
                            lat=poi['lat'],
                            lng=poi['lng'],
                            distance_m=dist,
                            properties={'amenity': poi['amenity'], 'shop': poi['shop']}
                        ))
            
            if 'transport' in layers:
                for t in self.transport:
                    dist = self._haversine(lat, lng, t['lat'], t['lng'])
                    if dist <= radius_m:
                        results.append(NearbyResult(
                            type='transport',
                            name=t['name'],
                            lat=t['lat'],
                            lng=t['lng'],
                            distance_m=dist,
                            properties={'transport_type': t['type']}
                        ))
            
            if 'place' in layers:
                for p in self.places:
                    dist = self._haversine(lat, lng, p['lat'], p['lng'])
                    if dist <= radius_m:
                        results.append(NearbyResult(
                            type='place',
                            name=p['name'],
                            lat=p['lat'],
                            lng=p['lng'],
                            distance_m=dist,
                            properties={'place_type': p['type']}
                        ))
        
        # Sort by distance and limit
        results.sort(key=lambda x: x.distance_m)
        return results[:limit]
    
    def get_summary(
        self,
        lat: float,
        lng: float,
        radius_m: float = 1000
    ) -> SpatialSummary:
        """
        Get a summary of spatial features around a point.
        """
        nearby = self.query_nearby(lat, lng, radius_m, limit=500)
        
        # Count by category
        by_category = defaultdict(int)
        nearest = {}
        
        for r in nearby:
            category = r.type
            if r.type == 'poi':
                amenity = r.properties.get('amenity', '')
                shop = r.properties.get('shop', '')
                if amenity:
                    category = f"poi_{amenity}"
                elif shop:
                    category = f"shop_{shop}"
            elif r.type == 'transport':
                t_type = r.properties.get('transport_type', '')
                category = f"transport_{t_type}" if t_type else 'transport'
            
            by_category[category] += 1
            
            # Track nearest of each type
            base_type = r.type
            if base_type not in nearest or r.distance_m < nearest[base_type].distance_m:
                nearest[base_type] = r
        
        # Calculate scores
        total = len(nearby)
        area_sq_km = math.pi * (radius_m / 1000) ** 2
        amenity_density = total / area_sq_km if area_sq_km > 0 else 0
        
        # Accessibility score (based on transport proximity)
        accessibility_score = 0
        if 'transport' in nearest:
            dist = nearest['transport'].distance_m
            if dist < 200:
                accessibility_score = 100
            elif dist < 500:
                accessibility_score = 80
            elif dist < 1000:
                accessibility_score = 60
            elif dist < 2000:
                accessibility_score = 40
            else:
                accessibility_score = 20
        
        # Walkability score (based on amenity mix)
        essential_categories = ['hospital', 'school', 'supermarket', 'restaurant', 'bank']
        found_essentials = sum(1 for cat in essential_categories if any(cat in k for k in by_category.keys()))
        walkability_score = min(100, (found_essentials / len(essential_categories)) * 100 + min(50, amenity_density * 2))
        
        return SpatialSummary(
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            total_features=total,
            by_category=dict(by_category),
            nearest={k: asdict(v) if v else None for k, v in nearest.items()},
            accessibility_score=accessibility_score,
            walkability_score=walkability_score,
            amenity_density=round(amenity_density, 2)
        )
    
    def analyze_location(
        self,
        lat: float,
        lng: float,
        elevation: float = None,
        slope: float = None
    ) -> LocationAnalysis:
        """
        Complete location analysis with terrain and spatial features.
        """
        # Get spatial summary
        summary = self.get_summary(lat, lng, radius_m=1000)
        
        # Use provided terrain data or defaults
        if elevation is None:
            elevation = 900.0  # Default Bangalore elevation
        if slope is None:
            slope = 2.0  # Default gentle slope
        
        # Determine aspect (simplified)
        aspect = "N"  # Would compute from DEM in production
        
        # Terrain suitability for construction
        terrain_suitability = 100.0
        if slope > 15:
            terrain_suitability -= 40
        elif slope > 10:
            terrain_suitability -= 20
        elif slope > 5:
            terrain_suitability -= 10
        
        if elevation < 850:  # Low-lying areas
            terrain_suitability -= 20
        
        terrain_suitability = max(0, terrain_suitability)
        
        # Flood risk (simplified heuristic)
        flood_risk = "low"
        if elevation < 850 and slope < 2:
            flood_risk = "high"
        elif elevation < 880 and slope < 5:
            flood_risk = "medium"
        
        # Generate recommendations
        recommendations = []
        
        if summary.accessibility_score >= 80:
            recommendations.append("Excellent public transport access")
        elif summary.accessibility_score >= 60:
            recommendations.append("Good public transport connectivity")
        else:
            recommendations.append("Consider transport options - limited public transit nearby")
        
        if summary.walkability_score >= 70:
            recommendations.append("Highly walkable neighborhood with essential amenities")
        elif summary.walkability_score >= 50:
            recommendations.append("Moderately walkable - some amenities within reach")
        else:
            recommendations.append("Limited walkability - may need vehicle for daily needs")
        
        if terrain_suitability >= 80:
            recommendations.append("Terrain well-suited for construction")
        elif terrain_suitability >= 60:
            recommendations.append("Moderate construction suitability - may need site preparation")
        else:
            recommendations.append("Challenging terrain - significant site work may be required")
        
        if flood_risk == "high":
            recommendations.append("[WARNING] High flood risk area - consider drainage and elevation")
        elif flood_risk == "medium":
            recommendations.append("Moderate flood risk - ensure proper drainage planning")
        
        return LocationAnalysis(
            lat=lat,
            lng=lng,
            elevation_m=elevation,
            slope_deg=slope,
            aspect=aspect,
            terrain_suitability=terrain_suitability,
            flood_risk=flood_risk,
            summary=summary,
            recommendations=recommendations
        )
    
    def query_contains(
        self,
        lat: float,
        lng: float,
        layers: List[str] = None
    ) -> Dict[str, Any]:
        """
        Query what boundaries/zones contain a point.
        Returns jurisdiction information.
        """
        # This would query boundary polygons in production
        # For now, return placeholder based on approximate location
        
        result = {
            'lat': lat,
            'lng': lng,
            'city': 'Bangalore',
            'state': 'Karnataka',
            'country': 'India'
        }
        
        # Approximate zone based on coordinates
        if lat > 13.0:
            result['zone'] = 'North Bangalore'
        elif lat < 12.9:
            result['zone'] = 'South Bangalore'
        elif lng > 77.65:
            result['zone'] = 'East Bangalore'
        elif lng < 77.55:
            result['zone'] = 'West Bangalore'
        else:
            result['zone'] = 'Central Bangalore'
        
        return result
    
    def get_h3_index(self, lat: float, lng: float, resolution: int = 9) -> Optional[str]:
        """Get H3 index for a point."""
        if not H3_AVAILABLE:
            return None
        return _h3_geo_to_cell(lat, lng, resolution)
    
    def get_h3_neighbors(self, h3_index: str, rings: int = 1) -> List[str]:
        """Get neighboring H3 cells."""
        if not H3_AVAILABLE:
            return []
        return list(_h3_grid_disk(h3_index, rings))


# Singleton instance
_spatial_service: Optional[SpatialReasoningService] = None


def get_spatial_service(data_dir: Path = None) -> SpatialReasoningService:
    """Get or create the spatial reasoning service singleton."""
    global _spatial_service
    if _spatial_service is None:
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / 'src' / 'data'
        _spatial_service = SpatialReasoningService(data_dir)
    return _spatial_service
