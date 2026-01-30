"""
Terrain Service - Provides elevation and terrain analysis data
Uses DATABASE as primary source (terrain_grid table)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import numpy as np
except ImportError:
    np = None

class TerrainService:
    def __init__(self, terrain_dir: Path):
        self.terrain_dir = terrain_dir
        self.db = None
        self.loaded = False
        self._init_db()
        
    def _init_db(self):
        """Initialize database connection"""
        try:
            # Try both import paths (running from project root vs backend dir)
            try:
                from backend.database.db_service import DatabaseService
            except ImportError:
                from database.db_service import DatabaseService
            db_path = self.terrain_dir.parent / 'valora.db'
            self.db = DatabaseService(str(db_path))
            
            # Check if terrain_grid table exists
            result = self.db.execute("SELECT COUNT(*) as cnt FROM terrain_grid")
            count = result[0]['cnt'] if result else 0
            if count > 0:
                print(f"[OK] Terrain service using database ({count:,} grid cells)")
                self.loaded = True
            else:
                print("[WARNING] terrain_grid table empty, terrain analysis limited")
        except Exception as e:
            print(f"[WARNING] Database not available for terrain: {e}")
            self.db = None
    
    def _get_nearest_grid_cell(self, lat: float, lng: float) -> Optional[Dict]:
        """Get nearest terrain grid cell from database"""
        if not self.db:
            return None
        
        # Query nearest grid cell (within ~1km)
        result = self.db.execute("""
            SELECT grid_id, center_lat, center_lng, elevation_m, slope_deg, 
                   aspect_deg, flood_risk, terrain_type, suitability_score
            FROM terrain_grid
            WHERE center_lat BETWEEN ? AND ?
              AND center_lng BETWEEN ? AND ?
            ORDER BY ABS(center_lat - ?) + ABS(center_lng - ?)
            LIMIT 1
        """, (lat - 0.01, lat + 0.01, lng - 0.01, lng + 0.01, lat, lng))
        
        return result[0] if result else None
    
    def get_elevation(self, lat: float, lng: float) -> Optional[Dict]:
        """Get elevation data for a specific location from database"""
        cell = self._get_nearest_grid_cell(lat, lng)
        
        if not cell:
            return None
        
        return {
            'lat': lat,
            'lng': lng,
            'elevation': cell.get('elevation_m', 920),
            'elevation_range': {
                'min': cell.get('elevation_m', 920) - 20,
                'max': cell.get('elevation_m', 920) + 20
            },
            'slope': cell.get('slope_deg', 3),
            'slope_range': {
                'min': max(0, cell.get('slope_deg', 3) - 2),
                'max': cell.get('slope_deg', 3) + 2
            },
            'grid_id': cell.get('grid_id')
        }
    
    def get_terrain_analysis(self, lat: float, lng: float, radius_deg: float = 0.01) -> Optional[Dict]:
        """Get terrain analysis for an area around a location from database"""
        if not self.db:
            return None
        
        # Query all grid cells within radius
        result = self.db.execute("""
            SELECT elevation_m, slope_deg, flood_risk, terrain_type, suitability_score
            FROM terrain_grid
            WHERE center_lat BETWEEN ? AND ?
              AND center_lng BETWEEN ? AND ?
        """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
        
        if not result:
            return None
        
        # Aggregate statistics
        elevations = [r['elevation_m'] for r in result if r.get('elevation_m')]
        slopes = [r['slope_deg'] for r in result if r.get('slope_deg')]
        flood_risks = [r['flood_risk'] for r in result]
        suitabilities = [r['suitability_score'] for r in result if r.get('suitability_score')]
        
        if not elevations:
            return None
        
        # Calculate stats
        elev_mean = sum(elevations) / len(elevations)
        slope_mean = sum(slopes) / len(slopes) if slopes else 3.0
        suit_mean = sum(suitabilities) / len(suitabilities) if suitabilities else 70.0
        
        # Determine dominant flood risk
        risk_counts = {}
        for r in flood_risks:
            risk_counts[r] = risk_counts.get(r, 0) + 1
        dominant_risk = max(risk_counts, key=risk_counts.get) if risk_counts else 'unknown'
        
        analysis = {
            'location': {'lat': lat, 'lng': lng},
            'radius_deg': radius_deg,
            'cells_analyzed': len(result),
            'elevation_mean': round(elev_mean, 1),
            'elevation_min': min(elevations),
            'elevation_max': max(elevations),
            'slope_mean': round(slope_mean, 1),
            'slope_min': min(slopes) if slopes else 0,
            'slope_max': max(slopes) if slopes else 10,
            'flood_risk': dominant_risk,
            'suitability_score': round(suit_mean, 1),
            'terrain_classification': self._classify_terrain(slope_mean),
            'construction_suitability': self._assess_construction_suitability(slope_mean, max(elevations) - min(elevations) if len(elevations) > 1 else 0)
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
    
    def get_elevation_profile(self, lat: float, lng: float, radius_km: float = 2.0, samples: int = 20) -> Optional[Dict]:
        """Get elevation profile around a location for charting
        
        Args:
            lat: Center latitude
            lng: Center longitude
            radius_km: Radius in kilometers to sample
            samples: Number of sample points in each direction (N, S, E, W)
        
        Returns:
            Dict with elevation profile data for charting
        """
        if not self.db:
            return None
        
        # Convert km to degrees (approximate)
        radius_deg = radius_km / 111.0  # 1 degree ≈ 111 km
        step = radius_deg / samples
        
        # Sample points in 4 directions: North, South, East, West
        profiles = {
            'north': [],
            'south': [],
            'east': [],
            'west': []
        }
        
        # North-South profile (varying latitude)
        for i in range(-samples, samples + 1):
            sample_lat = lat + (i * step)
            cell = self._get_nearest_grid_cell(sample_lat, lng)
            if cell:
                profiles['north' if i >= 0 else 'south'].append({
                    'distance_km': abs(i * step * 111.0),
                    'elevation_m': cell.get('elevation_m', 920),
                    'lat': sample_lat,
                    'lng': lng
                })
        
        # East-West profile (varying longitude)
        for i in range(-samples, samples + 1):
            sample_lng = lng + (i * step)
            cell = self._get_nearest_grid_cell(lat, sample_lng)
            if cell:
                profiles['east' if i >= 0 else 'west'].append({
                    'distance_km': abs(i * step * 111.0),
                    'elevation_m': cell.get('elevation_m', 920),
                    'lat': lat,
                    'lng': sample_lng
                })
        
        # Combine into single profile for simplified chart
        all_points = []
        
        # West to East
        for p in reversed(profiles['west']):
            all_points.append({
                'distance_km': -p['distance_km'],
                'elevation_m': p['elevation_m'],
                'direction': 'W'
            })
        
        # Center point
        center_cell = self._get_nearest_grid_cell(lat, lng)
        if center_cell:
            all_points.append({
                'distance_km': 0,
                'elevation_m': center_cell.get('elevation_m', 920),
                'direction': 'Center'
            })
        
        # East
        for p in profiles['east']:
            if p['distance_km'] > 0:  # Skip center
                all_points.append({
                    'distance_km': p['distance_km'],
                    'elevation_m': p['elevation_m'],
                    'direction': 'E'
                })
        
        if not all_points:
            return None
        
        # Calculate statistics
        elevations = [p['elevation_m'] for p in all_points]
        
        return {
            'center': {'lat': lat, 'lng': lng},
            'radius_km': radius_km,
            'profile': all_points,
            'statistics': {
                'min_elevation': min(elevations),
                'max_elevation': max(elevations),
                'avg_elevation': sum(elevations) / len(elevations),
                'elevation_range': max(elevations) - min(elevations),
                'sample_count': len(all_points)
            }
        }
    
    def get_stats(self) -> Dict:
        """Get overall terrain statistics from database"""
        if not self.db:
            return {'loaded': False}
        
        try:
            result = self.db.execute("""
                SELECT 
                    COUNT(*) as cell_count,
                    AVG(elevation_m) as avg_elevation,
                    MIN(elevation_m) as min_elevation,
                    MAX(elevation_m) as max_elevation,
                    AVG(slope_deg) as avg_slope,
                    AVG(suitability_score) as avg_suitability
                FROM terrain_grid
            """)
            
            if not result:
                return {'loaded': False}
            
            stats = result[0]
            return {
                'loaded': self.loaded,
                'cell_count': stats.get('cell_count', 0),
                'elevation': {
                    'min': round(stats.get('min_elevation', 850), 1),
                    'max': round(stats.get('max_elevation', 980), 1),
                    'avg': round(stats.get('avg_elevation', 920), 1)
                },
                'slope_avg': round(stats.get('avg_slope', 3), 1),
                'suitability_avg': round(stats.get('avg_suitability', 70), 1),
                'source': 'database'
            }
        except Exception as e:
            return {'loaded': False, 'error': str(e)}
