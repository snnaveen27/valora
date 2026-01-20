"""
Terrain Service - Provides elevation and terrain analysis data
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

class TerrainService:
    def __init__(self, terrain_dir: Path):
        self.terrain_dir = terrain_dir
        self.index_file = terrain_dir / 'elevation_index.json'
        self.index_data = None
        self.tiles = []
        self.loaded = False
        
    def load_index(self):
        """Load terrain tile index"""
        if self.loaded:
            return
            
        if not self.index_file.exists():
            print(f"[WARNING]  Terrain index not found: {self.index_file}")
            return
            
        with open(self.index_file, 'r') as f:
            self.index_data = json.load(f)
            self.tiles = self.index_data.get('tiles', [])
        
        print(f"[OK] Loaded terrain index: {len(self.tiles)} tiles")
        print(f"   Elevation range: {self.index_data['stats']['min_elevation']:.1f}m - {self.index_data['stats']['max_elevation']:.1f}m")
        
        self.loaded = True
    
    def get_tile_for_location(self, lat: float, lng: float) -> Optional[Dict]:
        """Find the tile containing the given location"""
        self.load_index()
        
        for tile in self.tiles:
            bounds = tile['bounds']
            if (bounds['west'] <= lng <= bounds['east'] and
                bounds['south'] <= lat <= bounds['north']):
                return tile
        
        return None
    
    def get_elevation(self, lat: float, lng: float) -> Optional[Dict]:
        """Get elevation data for a specific location"""
        tile = self.get_tile_for_location(lat, lng)
        
        if not tile:
            return None
        
        return {
            'lat': lat,
            'lng': lng,
            'elevation': tile['elevation']['mean'],  # Approximate with tile mean
            'elevation_range': {
                'min': tile['elevation']['min'],
                'max': tile['elevation']['max']
            },
            'slope': tile['slope']['mean'],
            'slope_range': {
                'min': tile['slope']['min'],
                'max': tile['slope']['max']
            },
            'tile_id': tile['tile_id']
        }
    
    def get_terrain_analysis(self, lat: float, lng: float, radius_deg: float = 0.01) -> Optional[Dict]:
        """Get terrain analysis for an area around a location"""
        self.load_index()
        
        # Find all tiles within radius
        nearby_tiles = []
        for tile in self.tiles:
            center = tile['center']
            dist = ((center['lat'] - lat)**2 + (center['lng'] - lng)**2)**0.5
            if dist <= radius_deg * 1.5:  # Include tiles within 1.5x radius
                nearby_tiles.append(tile)
        
        if not nearby_tiles:
            return None
        
        # Aggregate statistics
        elevations = [t['elevation']['mean'] for t in nearby_tiles]
        slopes = [t['slope']['mean'] for t in nearby_tiles]
        
        analysis = {
            'location': {'lat': lat, 'lng': lng},
            'radius_deg': radius_deg,
            'tiles_analyzed': len(nearby_tiles),
            'elevation': {
                'min': min(t['elevation']['min'] for t in nearby_tiles),
                'max': max(t['elevation']['max'] for t in nearby_tiles),
                'mean': np.mean(elevations),
                'std': np.std(elevations),
                'range': max(t['elevation']['max'] for t in nearby_tiles) - min(t['elevation']['min'] for t in nearby_tiles)
            },
            'slope': {
                'min': min(t['slope']['min'] for t in nearby_tiles),
                'max': max(t['slope']['max'] for t in nearby_tiles),
                'mean': np.mean(slopes),
                'std': np.std(slopes)
            },
            'terrain_classification': self._classify_terrain(np.mean(slopes)),
            'construction_suitability': self._assess_construction_suitability(np.mean(slopes), np.std(elevations))
        }
        
        return analysis
    
    def _classify_terrain(self, avg_slope: float) -> str:
        """Classify terrain based on average slope"""
        if avg_slope < 2:
            return 'flat'
        elif avg_slope < 5:
            return 'gentle'
        elif avg_slope < 10:
            return 'moderate'
        elif avg_slope < 15:
            return 'steep'
        else:
            return 'very_steep'
    
    def _assess_construction_suitability(self, avg_slope: float, elevation_std: float) -> Dict:
        """Assess construction suitability based on terrain"""
        # Simple heuristic scoring
        slope_score = max(0, 100 - avg_slope * 5)  # Penalize steep slopes
        flatness_score = max(0, 100 - elevation_std * 2)  # Penalize uneven terrain
        
        overall_score = (slope_score * 0.6 + flatness_score * 0.4)
        
        if overall_score >= 80:
            suitability = 'excellent'
            notes = 'Flat, stable terrain ideal for construction'
        elif overall_score >= 60:
            suitability = 'good'
            notes = 'Generally suitable with minor grading needed'
        elif overall_score >= 40:
            suitability = 'moderate'
            notes = 'Requires significant site preparation and grading'
        elif overall_score >= 20:
            suitability = 'challenging'
            notes = 'Steep terrain, requires extensive foundation work'
        else:
            suitability = 'difficult'
            notes = 'Very challenging terrain, high construction costs'
        
        return {
            'score': round(overall_score, 1),
            'rating': suitability,
            'notes': notes,
            'factors': {
                'slope_score': round(slope_score, 1),
                'flatness_score': round(flatness_score, 1)
            }
        }
    
    def get_stats(self) -> Dict:
        """Get overall terrain statistics"""
        self.load_index()
        
        if not self.index_data:
            return {}
        
        return {
            'loaded': self.loaded,
            'tile_count': len(self.tiles),
            'stats': self.index_data.get('stats', {}),
            'coverage': self.index_data['stats'].get('bounds', {})
        }
