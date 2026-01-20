"""
Scene Analyzer - Viewport-Aware 3D Analytics
Analyzes the 3D scene context including height distribution, visibility, and density
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path

@dataclass
class SceneContext:
    """Scene context from frontend"""
    camera_lat: float
    camera_lng: float
    camera_height: float
    camera_heading: float
    camera_pitch: float
    viewport_bbox: Dict[str, float]  # {north, south, east, west}
    loaded_tiles: List[str] = None
    selected_entity: Optional[str] = None

@dataclass
class SceneAnalytics:
    """Computed scene analytics"""
    building_count: int
    height_distribution: Dict[str, int]  # {low, mid, high, very_high}
    avg_height: float
    max_height: float
    density_score: float  # 0-100
    skyline_descriptor: str
    visible_area_km2: float
    dominant_building_type: str

class SceneAnalyzer:
    """Analyzes 3D scene context for viewport-aware reasoning"""
    
    def __init__(self, data_dir: str = "src/data"):
        self.data_dir = Path(data_dir)
        self.buildings_cache = None
    
    def analyze_scene(self, scene_context: SceneContext) -> SceneAnalytics:
        """
        Analyze the 3D scene based on viewport context
        
        Args:
            scene_context: Camera and viewport information from frontend
            
        Returns:
            SceneAnalytics with computed metrics
        """
        # Get buildings in viewport
        buildings = self._get_buildings_in_viewport(scene_context.viewport_bbox)
        
        if not buildings:
            return SceneAnalytics(
                building_count=0,
                height_distribution={"low": 0, "mid": 0, "high": 0, "very_high": 0},
                avg_height=0,
                max_height=0,
                density_score=0,
                skyline_descriptor="empty",
                visible_area_km2=self._calculate_bbox_area(scene_context.viewport_bbox),
                dominant_building_type="none"
            )
        
        # Compute height distribution
        height_dist = self._compute_height_distribution(buildings)
        
        # Compute statistics
        heights = [b.get('height', 0) for b in buildings if b.get('height')]
        avg_height = sum(heights) / len(heights) if heights else 0
        max_height = max(heights) if heights else 0
        
        # Compute density
        area_km2 = self._calculate_bbox_area(scene_context.viewport_bbox)
        density_score = min(100, (len(buildings) / area_km2) * 10) if area_km2 > 0 else 0
        
        # Determine skyline descriptor
        skyline = self._describe_skyline(height_dist, avg_height)
        
        # Determine dominant building type
        building_types = [b.get('type', 'unknown') for b in buildings]
        dominant_type = max(set(building_types), key=building_types.count) if building_types else 'unknown'
        
        return SceneAnalytics(
            building_count=len(buildings),
            height_distribution=height_dist,
            avg_height=round(avg_height, 1),
            max_height=round(max_height, 1),
            density_score=round(density_score, 1),
            skyline_descriptor=skyline,
            visible_area_km2=round(area_km2, 2),
            dominant_building_type=dominant_type
        )
    
    def generate_overlay_suggestions(self, scene_analytics: SceneAnalytics, 
                                    scene_context: SceneContext) -> List[Dict]:
        """
        Generate overlay suggestions based on scene analytics
        
        Returns:
            List of overlay commands for OverlayEngine
        """
        overlays = []
        
        # Add density heatmap if high density
        if scene_analytics.density_score > 50:
            overlays.append({
                "type": "label",
                "data": {
                    "lat": scene_context.camera_lat,
                    "lng": scene_context.camera_lng,
                    "text": f"High Density Area ({scene_analytics.building_count} buildings)"
                },
                "style": {
                    "color": [1, 0.5, 0, 1],  # Orange
                    "fontSize": 16
                }
            })
        
        # Add height distribution markers
        if scene_analytics.max_height > 50:
            overlays.append({
                "type": "marker",
                "data": {
                    "lat": scene_context.camera_lat,
                    "lng": scene_context.camera_lng,
                    "icon": "🏢"
                },
                "style": {
                    "color": [0, 0.5, 1, 1],  # Blue
                    "scale": 1.5
                }
            })
        
        return overlays
    
    def _get_buildings_in_viewport(self, bbox: Dict[str, float]) -> List[Dict]:
        """Get buildings within viewport bounding box"""
        # In production, this would query the 3D tiles or building database
        # For now, return mock data based on bbox
        
        # Estimate building count based on area
        area_km2 = self._calculate_bbox_area(bbox)
        estimated_count = int(area_km2 * 1000)  # ~1000 buildings per km²
        
        # Generate mock buildings
        buildings = []
        for i in range(min(estimated_count, 100)):  # Cap at 100 for performance
            buildings.append({
                "id": f"building_{i}",
                "height": 10 + (i % 50),  # Heights from 10-60m
                "type": ["residence", "commerce", "office"][i % 3]
            })
        
        return buildings
    
    def _compute_height_distribution(self, buildings: List[Dict]) -> Dict[str, int]:
        """Compute height distribution categories"""
        dist = {"low": 0, "mid": 0, "high": 0, "very_high": 0}
        
        for building in buildings:
            height = building.get('height', 0)
            if height < 15:
                dist["low"] += 1
            elif height < 30:
                dist["mid"] += 1
            elif height < 50:
                dist["high"] += 1
            else:
                dist["very_high"] += 1
        
        return dist
    
    def _calculate_bbox_area(self, bbox: Dict[str, float]) -> float:
        """Calculate approximate area of bounding box in km²"""
        # Simplified calculation (assumes flat earth for small areas)
        lat_diff = abs(bbox['north'] - bbox['south'])
        lng_diff = abs(bbox['east'] - bbox['west'])
        
        # Approximate conversion (1 degree ≈ 111 km at equator)
        area_km2 = (lat_diff * 111) * (lng_diff * 111)
        return area_km2
    
    def _describe_skyline(self, height_dist: Dict[str, int], avg_height: float) -> str:
        """Generate skyline descriptor"""
        total = sum(height_dist.values())
        if total == 0:
            return "flat"
        
        very_high_pct = (height_dist["very_high"] / total) * 100
        high_pct = (height_dist["high"] / total) * 100
        
        if very_high_pct > 30:
            return "high-rise dominated"
        elif very_high_pct + high_pct > 50:
            return "mixed high-rise"
        elif avg_height > 20:
            return "mid-rise urban"
        else:
            return "low-rise suburban"

# Singleton instance
_scene_analyzer = None

def get_scene_analyzer() -> SceneAnalyzer:
    """Get or create scene analyzer singleton"""
    global _scene_analyzer
    if _scene_analyzer is None:
        _scene_analyzer = SceneAnalyzer()
    return _scene_analyzer
