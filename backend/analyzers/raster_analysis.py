"""
Valora AI - Advanced Raster Analysis Engine
NumPy/SciPy-based terrain and flood risk analysis.

Features:
- Flood risk modeling with watershed analysis
- Terrain interpolation for data gaps
- Slope-based water flow simulation
- Flood insurance risk scoring
- Microclimate analysis
- Drainage pattern detection
"""

import math
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from backend.config import config

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("[WARNING] NumPy not available. Using fallback raster analysis.")

try:
    from scipy import ndimage
    from scipy.interpolate import griddata
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("[WARNING] SciPy not available. Advanced interpolation disabled.")


@dataclass
class FloodRiskResult:
    """Result of flood risk analysis."""
    location_lat: float
    location_lng: float
    
    # Risk scores (0-100)
    flood_risk_score: float = 0.0
    drainage_score: float = 100.0  # Higher = better drainage
    watershed_score: float = 0.0  # Higher = more water flows here
    
    # Risk factors
    elevation_percentile: float = 50.0  # Higher = safer
    slope_factor: float = 0.0  # Flat areas flood more
    depression_depth_m: float = 0.0  # Local depression depth
    distance_to_water_m: float = float('inf')
    
    # Insurance estimate
    flood_zone: str = "X"  # FEMA-style zones: A, AE, X, etc.
    insurance_multiplier: float = 1.0  # Base rate multiplier
    annual_flood_probability: float = 0.0  # Percentage
    
    # Recommendations
    risk_level: str = "low"  # low, moderate, high, very_high
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "location": {"lat": self.location_lat, "lng": self.location_lng},
            "flood_risk_score": round(self.flood_risk_score, 1),
            "drainage_score": round(self.drainage_score, 1),
            "watershed_score": round(self.watershed_score, 1),
            "elevation_percentile": round(self.elevation_percentile, 1),
            "slope_factor": round(self.slope_factor, 2),
            "depression_depth_m": round(self.depression_depth_m, 2),
            "distance_to_water_m": round(self.distance_to_water_m, 1) if self.distance_to_water_m < float('inf') else None,
            "flood_zone": self.flood_zone,
            "insurance_multiplier": round(self.insurance_multiplier, 2),
            "annual_flood_probability": round(self.annual_flood_probability, 2),
            "risk_level": self.risk_level,
            "recommendations": self.recommendations
        }


@dataclass
class TerrainAnalysisResult:
    """Result of advanced terrain analysis."""
    center_lat: float
    center_lng: float
    radius_m: float
    
    # Elevation statistics
    elevation_min: float = 0.0
    elevation_max: float = 0.0
    elevation_mean: float = 0.0
    elevation_std: float = 0.0
    elevation_median: float = 0.0
    
    # Slope statistics
    slope_min: float = 0.0
    slope_max: float = 0.0
    slope_mean: float = 0.0
    slope_dominant_direction: str = ""
    
    # Terrain classification
    terrain_type: str = "flat"
    terrain_roughness: float = 0.0  # 0-100, higher = rougher
    construction_suitability: float = 100.0  # 0-100
    
    # Drainage
    drainage_direction: str = ""
    drainage_quality: str = "good"
    water_accumulation_areas: int = 0
    
    # Grid data for visualization
    elevation_grid: Optional[List[List[float]]] = None
    slope_grid: Optional[List[List[float]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "location": {"lat": self.center_lat, "lng": self.center_lng},
            "radius_m": self.radius_m,
            "elevation": {
                "min": round(self.elevation_min, 1),
                "max": round(self.elevation_max, 1),
                "mean": round(self.elevation_mean, 1),
                "std": round(self.elevation_std, 2),
                "median": round(self.elevation_median, 1)
            },
            "slope": {
                "min": round(self.slope_min, 1),
                "max": round(self.slope_max, 1),
                "mean": round(self.slope_mean, 1),
                "dominant_direction": self.slope_dominant_direction
            },
            "terrain_type": self.terrain_type,
            "terrain_roughness": round(self.terrain_roughness, 1),
            "construction_suitability": round(self.construction_suitability, 1),
            "drainage": {
                "direction": self.drainage_direction,
                "quality": self.drainage_quality,
                "accumulation_areas": self.water_accumulation_areas
            }
        }


class RasterAnalysis:
    """
    Advanced raster analysis with NumPy/SciPy.
    Provides flood risk modeling, terrain interpolation, and drainage analysis.
    """
    
    # Flood zone definitions (FEMA-style)
    FLOOD_ZONES = {
        'A': {'probability': 1.0, 'multiplier': 3.0, 'description': 'High risk - 1% annual chance'},
        'AE': {'probability': 1.0, 'multiplier': 2.5, 'description': 'High risk with base flood elevation'},
        'AH': {'probability': 1.0, 'multiplier': 2.0, 'description': 'Shallow flooding'},
        'X500': {'probability': 0.2, 'multiplier': 1.5, 'description': 'Moderate risk - 0.2% annual chance'},
        'X': {'probability': 0.01, 'multiplier': 1.0, 'description': 'Low risk - minimal flood hazard'}
    }
    
    # Terrain classifications
    TERRAIN_TYPES = {
        (0, 2): 'flat',
        (2, 5): 'gentle',
        (5, 10): 'moderate',
        (10, 20): 'steep',
        (20, 100): 'very_steep'
    }
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = config.DB_PATH
        self.db_path = str(db_path)
    
    def _get_terrain_grid(self, lat: float, lng: float, radius_deg: float = 0.02) -> Tuple[Optional[Any], Dict]:
        """
        Get terrain data as a grid for analysis.
        
        Returns:
            Tuple of (elevation_array, metadata_dict)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT center_lat, center_lng, elevation_m, slope_deg, aspect_deg, flood_risk
                FROM terrain_grid
                WHERE center_lat BETWEEN ? AND ?
                AND center_lng BETWEEN ? AND ?
                ORDER BY center_lat, center_lng
            """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return None, {}
            
            # Convert to arrays
            lats = [r[0] for r in rows]
            lngs = [r[1] for r in rows]
            elevations = [r[2] or 920 for r in rows]
            slopes = [r[3] or 0 for r in rows]
            aspects = [r[4] or 0 for r in rows]
            flood_risks = [r[5] or 'low' for r in rows]
            
            metadata = {
                'min_lat': min(lats),
                'max_lat': max(lats),
                'min_lng': min(lngs),
                'max_lng': max(lngs),
                'count': len(rows),
                'elevations': elevations,
                'slopes': slopes,
                'aspects': aspects,
                'flood_risks': flood_risks,
                'lats': lats,
                'lngs': lngs
            }
            
            if NUMPY_AVAILABLE and len(rows) > 9:
                # Create regular grid
                grid_size = int(math.sqrt(len(rows)))
                if grid_size * grid_size <= len(rows):
                    elev_array = np.array(elevations[:grid_size*grid_size]).reshape(grid_size, grid_size)
                    slope_array = np.array(slopes[:grid_size*grid_size]).reshape(grid_size, grid_size)
                    metadata['elevation_grid'] = elev_array
                    metadata['slope_grid'] = slope_array
                    return elev_array, metadata
            
            return None, metadata
            
        except Exception as e:
            print(f"[RasterAnalysis] Error getting terrain grid: {e}")
            return None, {}
    
    def _calculate_flow_accumulation(self, elevation_grid: Any) -> Any:
        """
        Calculate water flow accumulation using D8 algorithm.
        Higher values = more water flows through this cell.
        """
        if not NUMPY_AVAILABLE or elevation_grid is None:
            return None
        
        rows, cols = elevation_grid.shape
        flow_acc = np.ones_like(elevation_grid)
        
        # D8 flow directions (indices into 3x3 neighborhood)
        # 5 6 7
        # 4 x 0
        # 3 2 1
        dx = [1, 1, 0, -1, -1, -1, 0, 1]
        dy = [0, 1, 1, 1, 0, -1, -1, -1]
        
        # Calculate flow direction for each cell
        flow_dir = np.zeros_like(elevation_grid, dtype=int)
        
        for i in range(1, rows - 1):
            for j in range(1, cols - 1):
                min_drop = 0
                min_dir = -1
                
                for d in range(8):
                    ni, nj = i + dy[d], j + dx[d]
                    drop = elevation_grid[i, j] - elevation_grid[ni, nj]
                    
                    if drop > min_drop:
                        min_drop = drop
                        min_dir = d
                
                flow_dir[i, j] = min_dir
        
        # Accumulate flow (simplified - iterate a few times)
        for _ in range(min(rows, cols)):
            for i in range(1, rows - 1):
                for j in range(1, cols - 1):
                    d = flow_dir[i, j]
                    if d >= 0:
                        ni, nj = i + dy[d], j + dx[d]
                        if 0 <= ni < rows and 0 <= nj < cols:
                            flow_acc[ni, nj] += flow_acc[i, j] * 0.1
        
        return flow_acc
    
    def _find_depressions(self, elevation_grid: Any) -> List[Tuple[int, int, float]]:
        """Find local depressions (potential flood areas)."""
        if not NUMPY_AVAILABLE or elevation_grid is None:
            return []
        
        depressions = []
        rows, cols = elevation_grid.shape
        
        # Use minimum filter to find local minima
        if SCIPY_AVAILABLE:
            local_min = ndimage.minimum_filter(elevation_grid, size=3)
            depression_mask = (elevation_grid == local_min)
            
            # Calculate depression depth
            local_max = ndimage.maximum_filter(elevation_grid, size=5)
            
            for i in range(1, rows - 1):
                for j in range(1, cols - 1):
                    if depression_mask[i, j]:
                        depth = local_max[i, j] - elevation_grid[i, j]
                        if depth > 0.5:  # Only significant depressions
                            depressions.append((i, j, depth))
        else:
            # Fallback without scipy
            for i in range(1, rows - 1):
                for j in range(1, cols - 1):
                    neighbors = [
                        elevation_grid[i-1, j-1], elevation_grid[i-1, j], elevation_grid[i-1, j+1],
                        elevation_grid[i, j-1], elevation_grid[i, j+1],
                        elevation_grid[i+1, j-1], elevation_grid[i+1, j], elevation_grid[i+1, j+1]
                    ]
                    if elevation_grid[i, j] < min(neighbors):
                        depth = max(neighbors) - elevation_grid[i, j]
                        if depth > 0.5:
                            depressions.append((i, j, depth))
        
        return depressions
    
    def _interpolate_elevation(self, lats: List[float], lngs: List[float], 
                                elevations: List[float], target_lat: float, 
                                target_lng: float) -> float:
        """Interpolate elevation at a specific point."""
        if not lats or not elevations:
            return 920.0  # Default Bangalore elevation
        
        if SCIPY_AVAILABLE and NUMPY_AVAILABLE and len(lats) >= 4:
            try:
                points = np.array(list(zip(lats, lngs)))
                values = np.array(elevations)
                target = np.array([[target_lat, target_lng]])
                
                result = griddata(points, values, target, method='linear')
                if result is not None and not np.isnan(result[0]):
                    return float(result[0])
            except Exception:
                pass
        
        # Fallback: nearest neighbor
        if lats:
            distances = [(abs(lat - target_lat) + abs(lng - target_lng), elev) 
                        for lat, lng, elev in zip(lats, lngs, elevations)]
            return min(distances, key=lambda x: x[0])[1]
        
        return 920.0
    
    def analyze_flood_risk(self, lat: float, lng: float, radius_m: float = 500) -> FloodRiskResult:
        """
        Comprehensive flood risk analysis for a location.
        
        Args:
            lat, lng: Location coordinates
            radius_m: Analysis radius in meters
            
        Returns:
            FloodRiskResult with detailed flood risk assessment
        """
        result = FloodRiskResult(location_lat=lat, location_lng=lng)
        
        # Convert radius to degrees
        radius_deg = radius_m / 111000
        
        # Get terrain data
        elev_grid, metadata = self._get_terrain_grid(lat, lng, radius_deg)
        
        if not metadata:
            result.risk_level = "unknown"
            result.recommendations = ["Insufficient terrain data for analysis"]
            return result
        
        elevations = metadata.get('elevations', [])
        slopes = metadata.get('slopes', [])
        flood_risks = metadata.get('flood_risks', [])
        
        if not elevations:
            return result
        
        # Calculate elevation percentile
        target_elev = self._interpolate_elevation(
            metadata.get('lats', []), metadata.get('lngs', []),
            elevations, lat, lng
        )
        
        if NUMPY_AVAILABLE:
            elev_array = np.array(elevations)
            # Calculate percentile rank (what % of elevations are <= target)
            result.elevation_percentile = float(np.sum(elev_array <= target_elev) / len(elev_array) * 100)
            elev_mean = float(np.mean(elev_array))
            elev_std = float(np.std(elev_array))
        else:
            sorted_elev = sorted(elevations)
            rank = sum(1 for e in sorted_elev if e <= target_elev)
            result.elevation_percentile = (rank / len(sorted_elev)) * 100
            elev_mean = sum(elevations) / len(elevations)
            elev_std = math.sqrt(sum((e - elev_mean) ** 2 for e in elevations) / len(elevations))
        
        # Calculate slope factor (flat areas flood more)
        target_slope = slopes[0] if slopes else 2.0
        result.slope_factor = max(0, 10 - target_slope) / 10  # 0-1, higher = flatter = more risk
        
        # Find depressions
        depressions = []
        if elev_grid is not None:
            depressions = self._find_depressions(elev_grid)
            result.water_accumulation_areas = len(depressions)
            
            # Check if location is in a depression
            grid_size = elev_grid.shape[0]
            lat_idx = int((lat - metadata['min_lat']) / (metadata['max_lat'] - metadata['min_lat']) * grid_size)
            lng_idx = int((lng - metadata['min_lng']) / (metadata['max_lng'] - metadata['min_lng']) * grid_size)
            
            for di, dj, depth in depressions:
                if abs(di - lat_idx) <= 2 and abs(dj - lng_idx) <= 2:
                    result.depression_depth_m = depth
                    break
        
        # Calculate watershed score
        if elev_grid is not None:
            flow_acc = self._calculate_flow_accumulation(elev_grid)
            if flow_acc is not None:
                max_flow = float(np.max(flow_acc))
                if max_flow > 0:
                    grid_size = flow_acc.shape[0]
                    lat_idx = min(grid_size - 1, max(0, int((lat - metadata['min_lat']) / (metadata['max_lat'] - metadata['min_lat']) * grid_size)))
                    lng_idx = min(grid_size - 1, max(0, int((lng - metadata['min_lng']) / (metadata['max_lng'] - metadata['min_lng']) * grid_size)))
                    result.watershed_score = float(flow_acc[lat_idx, lng_idx] / max_flow * 100)
        
        # Calculate drainage score (inverse of watershed + slope consideration)
        avg_slope = sum(slopes) / len(slopes) if slopes else 2.0
        result.drainage_score = min(100, avg_slope * 10 + (100 - result.watershed_score) * 0.5)
        
        # Check existing flood risk data
        high_risk_count = sum(1 for r in flood_risks if r in ['high', 'medium'])
        existing_risk_factor = high_risk_count / len(flood_risks) if flood_risks else 0
        
        # Calculate overall flood risk score
        risk_factors = [
            (100 - result.elevation_percentile) * 0.3,  # Low elevation = high risk
            result.slope_factor * 30,  # Flat terrain = high risk
            result.watershed_score * 0.2,  # High flow accumulation = high risk
            result.depression_depth_m * 10,  # Depressions = high risk
            existing_risk_factor * 20  # Existing risk data
        ]
        
        result.flood_risk_score = min(100, sum(risk_factors))
        
        # Determine flood zone
        if result.flood_risk_score >= 70:
            result.flood_zone = "A"
            result.risk_level = "very_high"
        elif result.flood_risk_score >= 50:
            result.flood_zone = "AH"
            result.risk_level = "high"
        elif result.flood_risk_score >= 30:
            result.flood_zone = "X500"
            result.risk_level = "moderate"
        else:
            result.flood_zone = "X"
            result.risk_level = "low"
        
        # Set insurance multiplier and probability
        zone_info = self.FLOOD_ZONES.get(result.flood_zone, self.FLOOD_ZONES['X'])
        result.insurance_multiplier = zone_info['multiplier']
        result.annual_flood_probability = zone_info['probability']
        
        # Generate recommendations
        result.recommendations = self._generate_flood_recommendations(result)
        
        return result
    
    def _generate_flood_recommendations(self, result: FloodRiskResult) -> List[str]:
        """Generate flood risk recommendations."""
        recommendations = []
        
        if result.risk_level == "very_high":
            recommendations.append("⚠️ Very high flood risk - consider flood insurance mandatory")
            recommendations.append("Elevate ground floor or consider different location")
        elif result.risk_level == "high":
            recommendations.append("⚠️ High flood risk - flood insurance strongly recommended")
            recommendations.append("Install sump pump and waterproofing")
        elif result.risk_level == "moderate":
            recommendations.append("Moderate flood risk - consider flood insurance")
        else:
            recommendations.append("✅ Low flood risk - standard insurance typically sufficient")
        
        if result.depression_depth_m > 1:
            recommendations.append(f"Location is in a depression ({result.depression_depth_m:.1f}m deep)")
        
        if result.slope_factor > 0.7:
            recommendations.append("Flat terrain may have drainage issues")
        
        if result.drainage_score < 50:
            recommendations.append("Poor natural drainage - ensure proper grading")
        
        return recommendations
    
    def analyze_terrain_advanced(self, lat: float, lng: float, radius_m: float = 500) -> TerrainAnalysisResult:
        """
        Advanced terrain analysis with statistics and drainage patterns.
        
        Args:
            lat, lng: Center coordinates
            radius_m: Analysis radius in meters
            
        Returns:
            TerrainAnalysisResult with detailed terrain metrics
        """
        result = TerrainAnalysisResult(center_lat=lat, center_lng=lng, radius_m=radius_m)
        
        radius_deg = radius_m / 111000
        elev_grid, metadata = self._get_terrain_grid(lat, lng, radius_deg)
        
        if not metadata:
            return result
        
        elevations = metadata.get('elevations', [])
        slopes = metadata.get('slopes', [])
        aspects = metadata.get('aspects', [])
        
        if not elevations:
            return result
        
        # Elevation statistics
        if NUMPY_AVAILABLE:
            elev_array = np.array(elevations)
            result.elevation_min = float(np.min(elev_array))
            result.elevation_max = float(np.max(elev_array))
            result.elevation_mean = float(np.mean(elev_array))
            result.elevation_std = float(np.std(elev_array))
            result.elevation_median = float(np.median(elev_array))
        else:
            result.elevation_min = min(elevations)
            result.elevation_max = max(elevations)
            result.elevation_mean = sum(elevations) / len(elevations)
            result.elevation_median = sorted(elevations)[len(elevations) // 2]
            result.elevation_std = math.sqrt(sum((e - result.elevation_mean) ** 2 for e in elevations) / len(elevations))
        
        # Slope statistics
        if slopes:
            if NUMPY_AVAILABLE:
                slope_array = np.array(slopes)
                result.slope_min = float(np.min(slope_array))
                result.slope_max = float(np.max(slope_array))
                result.slope_mean = float(np.mean(slope_array))
            else:
                result.slope_min = min(slopes)
                result.slope_max = max(slopes)
                result.slope_mean = sum(slopes) / len(slopes)
        
        # Dominant aspect (drainage direction)
        if aspects:
            directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
            avg_aspect = sum(aspects) / len(aspects)
            dir_idx = int((avg_aspect + 22.5) / 45) % 8
            result.slope_dominant_direction = directions[dir_idx]
            result.drainage_direction = directions[(dir_idx + 4) % 8]  # Opposite of slope
        
        # Terrain classification
        for (min_slope, max_slope), terrain_type in self.TERRAIN_TYPES.items():
            if min_slope <= result.slope_mean < max_slope:
                result.terrain_type = terrain_type
                break
        
        # Terrain roughness (based on elevation std dev)
        result.terrain_roughness = min(100, result.elevation_std * 10)
        
        # Construction suitability
        suitability = 100
        suitability -= min(50, result.slope_mean * 3)  # Penalize steep slopes
        suitability -= min(30, result.terrain_roughness * 0.3)  # Penalize rough terrain
        result.construction_suitability = max(0, suitability)
        
        # Drainage quality
        if result.slope_mean < 1:
            result.drainage_quality = "poor"
        elif result.slope_mean < 3:
            result.drainage_quality = "moderate"
        else:
            result.drainage_quality = "good"
        
        # Count water accumulation areas
        if elev_grid is not None:
            depressions = self._find_depressions(elev_grid)
            result.water_accumulation_areas = len(depressions)
        
        return result


# Singleton instance
_raster_instance = None

def get_raster_service(db_path: str = None) -> RasterAnalysis:
    """Get or create raster analysis service instance."""
    global _raster_instance
    if _raster_instance is None:
        _raster_instance = RasterAnalysis(db_path)
    return _raster_instance
