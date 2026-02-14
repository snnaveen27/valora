"""
3D Spatial Reasoning Engine for Valora AI
True 3D understanding of urban space - not just lat/lng but height, volume, visibility.

Features:
1. 3D Neighbor Analysis - Who's above, below, beside?
2. Volumetric Reasoning - Building volumes and density
3. Visibility Cones - What can be seen from where?
4. Shadow Propagation - How shadows move through the day
5. Vertical Connectivity - Elevator/stairs access modeling
6. Skyline Analysis - Urban silhouette understanding
7. 3D Path Finding - Routes considering elevation
"""

import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, time
import sqlite3
import math
from pathlib import Path
from config import config


@dataclass
class Building3D:
    """3D representation of a building."""
    id: str
    lat: float
    lng: float
    height: float
    levels: int
    building_type: str
    name: Optional[str] = None
    footprint_area: float = 0.0  # sqm
    volume: float = 0.0  # cubic meters


@dataclass
class ViewCone:
    """A visibility cone from a point."""
    origin_lat: float
    origin_lng: float
    origin_height: float
    direction: float  # degrees from north
    spread: float  # degrees (half-angle)
    max_distance: float  # meters
    visible_buildings: List[str] = field(default_factory=list)
    blocked_by: Optional[str] = None


@dataclass
class ShadowZone:
    """Shadow cast by a building at a specific time."""
    building_id: str
    time: datetime
    shadow_length: float  # meters
    shadow_direction: float  # degrees from north
    affected_area: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class Spatial3DAnalysis:
    """Complete 3D spatial analysis result."""
    center_lat: float
    center_lng: float
    center_height: float
    
    # Neighbor analysis
    buildings_above: List[Dict] = field(default_factory=list)  # Taller within radius
    buildings_below: List[Dict] = field(default_factory=list)  # Shorter within radius
    buildings_at_level: List[Dict] = field(default_factory=list)  # Similar height
    
    # Volumetric
    total_volume_nearby: float = 0.0
    avg_height_nearby: float = 0.0
    max_height_nearby: float = 0.0
    density_score: float = 0.0  # 0-100
    
    # Visibility
    sky_view_factor: float = 0.0  # 0-1, how much sky is visible
    open_directions: List[str] = field(default_factory=list)  # N, NE, E, etc.
    view_quality: str = "unknown"  # excellent, good, moderate, poor
    
    # Skyline
    skyline_character: str = "mixed"  # low-rise, mid-rise, high-rise, mixed
    dominant_type: str = "residential"
    
    # Connectivity
    vertical_access_score: float = 0.0  # 0-100, how well-connected vertically
    nearest_elevator_building: Optional[str] = None
    
    # Reasoning explanation
    reasoning: List[str] = field(default_factory=list)


class Spatial3DReasoning:
    """
    True 3D spatial reasoning for urban analysis.
    Goes beyond 2D distance to understand vertical relationships.
    """
    
    # Height categories (meters)
    HEIGHT_CATEGORIES = {
        'ground': (0, 3),
        'low_rise': (3, 12),
        'mid_rise': (12, 35),
        'high_rise': (35, 100),
        'skyscraper': (100, float('inf'))
    }
    
    # Direction angles
    DIRECTIONS = {
        'N': 0, 'NE': 45, 'E': 90, 'SE': 135,
        'S': 180, 'SW': 225, 'W': 270, 'NW': 315
    }
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = config.DB_PATH
        self.db_path = str(db_path)
    
    def analyze_3d_context(self, lat: float, lng: float, 
                          floor_height: float = 0,
                          radius_m: float = 200) -> Spatial3DAnalysis:
        """
        Perform complete 3D spatial analysis at a point.
        
        Args:
            lat, lng: Center coordinates
            floor_height: Height above ground (meters)
            radius_m: Analysis radius
            
        Returns:
            Spatial3DAnalysis with all 3D metrics
        """
        analysis = Spatial3DAnalysis(
            center_lat=lat,
            center_lng=lng,
            center_height=floor_height
        )
        
        # Get nearby buildings
        buildings = self._get_buildings_in_radius(lat, lng, radius_m)
        
        if not buildings:
            analysis.reasoning.append("No buildings found in analysis radius")
            return analysis
        
        # Categorize by relative height
        for bldg in buildings:
            height_diff = bldg['height'] - floor_height
            distance = bldg['distance']
            
            bldg_info = {
                'id': bldg['id'],
                'name': bldg.get('name'),
                'height': bldg['height'],
                'distance': distance,
                'direction': self._get_direction(lat, lng, bldg['lat'], bldg['lng']),
                'height_diff': height_diff
            }
            
            if height_diff > 5:  # More than 5m taller
                analysis.buildings_above.append(bldg_info)
            elif height_diff < -5:  # More than 5m shorter
                analysis.buildings_below.append(bldg_info)
            else:
                analysis.buildings_at_level.append(bldg_info)
        
        # Volumetric analysis
        heights = [b['height'] for b in buildings if b['height'] > 0]
        if heights:
            analysis.avg_height_nearby = sum(heights) / len(heights)
            analysis.max_height_nearby = max(heights)
            
            # Estimate volume (simplified: height * estimated footprint)
            for bldg in buildings:
                footprint = 200  # Assume 200 sqm average footprint
                analysis.total_volume_nearby += bldg['height'] * footprint
        
        # Density score based on building count and heights
        building_count = len(buildings)
        analysis.density_score = min(100, building_count * 5 + analysis.avg_height_nearby * 2)
        
        # Sky view factor
        analysis.sky_view_factor = self._calculate_sky_view_factor(
            floor_height, analysis.buildings_above
        )
        
        # Open directions
        analysis.open_directions = self._find_open_directions(
            lat, lng, floor_height, buildings
        )
        
        # View quality
        analysis.view_quality = self._assess_view_quality(
            analysis.sky_view_factor,
            len(analysis.open_directions),
            floor_height,
            analysis.max_height_nearby
        )
        
        # Skyline character
        analysis.skyline_character = self._classify_skyline(heights)
        
        # Dominant building type
        analysis.dominant_type = self._get_dominant_type(buildings)
        
        # Vertical access score
        analysis.vertical_access_score = self._calculate_vertical_access(
            floor_height, buildings
        )
        
        # Generate reasoning
        analysis.reasoning = self._generate_reasoning(analysis, floor_height)
        
        return analysis
    
    def _get_buildings_in_radius(self, lat: float, lng: float, 
                                  radius_m: float) -> List[Dict]:
        """Get buildings within radius with distance."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Convert radius to approximate degrees
            radius_deg = radius_m / 111000
            
            cursor.execute("""
                SELECT 
                    osm_id as id,
                    name,
                    height,
                    levels,
                    building_type,
                    latitude as lat,
                    longitude as lng,
                    (
                        (latitude - ?) * (latitude - ?) * 111000 * 111000 +
                        (longitude - ?) * (longitude - ?) * 111000 * 111000 * 0.94
                    ) as dist_sq
                FROM buildings
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                AND height > 0
                ORDER BY dist_sq
                LIMIT 100
            """, (
                lat, lat, lng, lng,
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            
            buildings = []
            for row in cursor.fetchall():
                dist = math.sqrt(row['dist_sq']) if row['dist_sq'] else 0
                if dist <= radius_m:
                    buildings.append({
                        'id': row['id'],
                        'name': row['name'],
                        'height': row['height'] or 0,
                        'levels': row['levels'] or 1,
                        'building_type': row['building_type'],
                        'lat': row['lat'],
                        'lng': row['lng'],
                        'distance': dist
                    })
            
            conn.close()
            return buildings
        except Exception as e:
            print(f"[3D] Error getting buildings: {e}")
            return []
    
    def _get_direction(self, from_lat: float, from_lng: float,
                      to_lat: float, to_lng: float) -> str:
        """Get cardinal direction from one point to another."""
        dlat = to_lat - from_lat
        dlng = to_lng - from_lng
        
        angle = math.degrees(math.atan2(dlng, dlat))
        if angle < 0:
            angle += 360
        
        # Map to cardinal direction
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'N']
        index = round(angle / 45) % 8
        return directions[index]
    
    def _calculate_sky_view_factor(self, floor_height: float,
                                   buildings_above: List[Dict]) -> float:
        """
        Calculate sky view factor (0-1).
        Higher = more sky visible = better views.
        """
        if not buildings_above:
            return 1.0
        
        # Simple model: each tall nearby building blocks some sky
        blocked = 0.0
        for bldg in buildings_above:
            height_diff = bldg['height_diff']
            distance = max(bldg['distance'], 10)  # Avoid division issues
            
            # Angle to top of building
            angle = math.atan(height_diff / distance)
            
            # Each building blocks roughly 45 degrees / 8 directions
            blocking_factor = min(0.125, angle / (math.pi / 2) * 0.125)
            blocked += blocking_factor
        
        return max(0, 1.0 - blocked)
    
    def _find_open_directions(self, lat: float, lng: float,
                             floor_height: float,
                             buildings: List[Dict]) -> List[str]:
        """Find directions with open views (no tall obstructions)."""
        # Check each direction
        direction_blocked = {d: False for d in self.DIRECTIONS.keys()}
        
        for bldg in buildings:
            if bldg['height'] <= floor_height + 5:
                continue  # Not blocking
            
            direction = self._get_direction(lat, lng, bldg['lat'], bldg['lng'])
            
            # If building is close and tall, it blocks
            if bldg['distance'] < 50 and bldg['height'] > floor_height + 10:
                direction_blocked[direction] = True
        
        return [d for d, blocked in direction_blocked.items() if not blocked]
    
    def _assess_view_quality(self, sky_view: float, open_count: int,
                            floor_height: float, max_nearby: float) -> str:
        """Assess overall view quality."""
        score = 0
        
        # Sky view contribution (0-40)
        score += sky_view * 40
        
        # Open directions contribution (0-30)
        score += (open_count / 8) * 30
        
        # Height advantage contribution (0-30)
        if max_nearby > 0:
            height_ratio = floor_height / max_nearby
            score += min(30, height_ratio * 30)
        else:
            score += 30  # No tall buildings = good views
        
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "moderate"
        else:
            return "poor"
    
    def _classify_skyline(self, heights: List[float]) -> str:
        """Classify the skyline character."""
        if not heights:
            return "unknown"
        
        avg = sum(heights) / len(heights)
        max_h = max(heights)
        
        if avg < 12 and max_h < 20:
            return "low_rise"
        elif avg < 35 and max_h < 50:
            return "mid_rise"
        elif avg >= 35 or max_h >= 50:
            return "high_rise"
        else:
            return "mixed"
    
    def _get_dominant_type(self, buildings: List[Dict]) -> str:
        """Get the dominant building type."""
        type_counts = {}
        for bldg in buildings:
            btype = bldg.get('building_type', 'unknown')
            type_counts[btype] = type_counts.get(btype, 0) + 1
        
        if type_counts:
            return max(type_counts, key=type_counts.get)
        return "unknown"
    
    def _calculate_vertical_access(self, floor_height: float,
                                   buildings: List[Dict]) -> float:
        """
        Calculate vertical accessibility score.
        Higher floors = lower accessibility unless elevators nearby.
        """
        if floor_height <= 12:  # Low-rise, stairs OK
            return 90
        
        # Check for nearby high-rise (likely has elevator)
        has_highrise_nearby = any(
            b['height'] > 35 and b['distance'] < 100 
            for b in buildings
        )
        
        if has_highrise_nearby:
            return 80  # Good access
        elif floor_height <= 35:
            return 60  # Mid-rise, maybe stairs
        else:
            return 40  # High floor, needs elevator
    
    def _generate_reasoning(self, analysis: Spatial3DAnalysis,
                           floor_height: float) -> List[str]:
        """Generate human-readable 3D reasoning."""
        reasoning = []
        
        # Height context
        if floor_height > 0:
            reasoning.append(f"Analysis at {floor_height}m above ground level")
        
        # Neighbor summary
        above_count = len(analysis.buildings_above)
        below_count = len(analysis.buildings_below)
        
        if above_count == 0:
            reasoning.append("No taller buildings nearby - unobstructed upper views")
        elif above_count <= 3:
            reasoning.append(f"Only {above_count} taller building(s) - mostly open skyline")
        else:
            reasoning.append(f"{above_count} taller buildings create urban canyon effect")
        
        # Sky view
        if analysis.sky_view_factor > 0.8:
            reasoning.append("Excellent sky exposure - bright and airy")
        elif analysis.sky_view_factor > 0.5:
            reasoning.append("Good sky visibility with some obstruction")
        else:
            reasoning.append("Limited sky view - may feel enclosed")
        
        # Open directions
        if len(analysis.open_directions) >= 6:
            reasoning.append(f"Open views in most directions: {', '.join(analysis.open_directions)}")
        elif len(analysis.open_directions) >= 3:
            reasoning.append(f"Open views toward: {', '.join(analysis.open_directions)}")
        else:
            reasoning.append("Limited open views - surrounded by structures")
        
        # Skyline
        reasoning.append(f"Area character: {analysis.skyline_character.replace('_', '-')} development")
        
        # View quality conclusion
        if analysis.view_quality == "excellent":
            reasoning.append("⭐ Premium view potential - highly desirable floor")
        elif analysis.view_quality == "good":
            reasoning.append("✓ Good views for the area")
        elif analysis.view_quality == "moderate":
            reasoning.append("Average views - consider higher floors for better vistas")
        else:
            reasoning.append("Limited views - may be affected by nearby buildings")
        
        return reasoning
    
    def compare_floors(self, lat: float, lng: float,
                      floors: List[int], floor_height_m: float = 3.0
                      ) -> List[Dict[str, Any]]:
        """Compare 3D context across multiple floors."""
        results = []
        
        for floor in floors:
            height = floor * floor_height_m
            analysis = self.analyze_3d_context(lat, lng, height)
            
            results.append({
                'floor': floor,
                'height_m': height,
                'view_quality': analysis.view_quality,
                'sky_view_factor': analysis.sky_view_factor,
                'open_directions': analysis.open_directions,
                'buildings_above': len(analysis.buildings_above),
                'reasoning': analysis.reasoning[-1] if analysis.reasoning else ""
            })
        
        return results
    
    def find_best_floor(self, lat: float, lng: float,
                       max_floor: int = 20) -> Dict[str, Any]:
        """Find the optimal floor for views at a location."""
        best_floor = 1
        best_score = 0
        
        for floor in range(1, max_floor + 1):
            height = floor * 3.0
            analysis = self.analyze_3d_context(lat, lng, height)
            
            # Score based on view quality and sky view
            score = (
                analysis.sky_view_factor * 40 +
                len(analysis.open_directions) / 8 * 30 +
                (1 if analysis.view_quality == 'excellent' else 
                 0.7 if analysis.view_quality == 'good' else
                 0.4 if analysis.view_quality == 'moderate' else 0.1) * 30
            )
            
            # Diminishing returns for very high floors (accessibility)
            if floor > 15:
                score *= 0.95
            if floor > 20:
                score *= 0.9
            
            if score > best_score:
                best_score = score
                best_floor = floor
        
        analysis = self.analyze_3d_context(lat, lng, best_floor * 3.0)
        
        return {
            'recommended_floor': best_floor,
            'height_m': best_floor * 3.0,
            'view_quality': analysis.view_quality,
            'score': best_score,
            'reasoning': f"Floor {best_floor} offers the best balance of views and accessibility"
        }
    
    def get_shadow_impact(self, lat: float, lng: float,
                         hour: int = 10) -> Dict[str, Any]:
        """Analyze shadow impact at a location for given hour."""
        # Sun position varies by time (simplified for Bangalore ~13°N)
        # Morning: sun in east, shadows west
        # Noon: sun overhead, minimal shadows
        # Evening: sun in west, shadows east
        
        buildings = self._get_buildings_in_radius(lat, lng, 100)
        
        if hour < 10:
            shadow_dir = 'W'  # Morning shadows point west
            sun_angle = 30 + (hour - 6) * 10  # Low to medium
        elif hour < 14:
            shadow_dir = 'N'  # Midday, minimal shadows
            sun_angle = 70  # High sun
        else:
            shadow_dir = 'E'  # Evening shadows point east
            sun_angle = 70 - (hour - 14) * 10
        
        # Calculate shadow lengths
        shadow_sources = []
        for bldg in buildings:
            if bldg['height'] > 10:
                shadow_length = bldg['height'] / math.tan(math.radians(sun_angle))
                
                # Check if shadow reaches the point
                direction = self._get_direction(lat, lng, bldg['lat'], bldg['lng'])
                
                if direction == shadow_dir and bldg['distance'] < shadow_length:
                    shadow_sources.append({
                        'building': bldg['name'] or bldg['id'],
                        'height': bldg['height'],
                        'shadow_length': shadow_length,
                        'distance': bldg['distance']
                    })
        
        if shadow_sources:
            impact = "significant" if len(shadow_sources) > 2 else "moderate"
        else:
            impact = "minimal"
        
        return {
            'hour': hour,
            'shadow_direction': shadow_dir,
            'sun_angle': sun_angle,
            'impact': impact,
            'shadow_sources': shadow_sources,
            'recommendation': (
                "Good natural light" if impact == "minimal" else
                "Some shadow periods - consider morning/evening light" if impact == "moderate" else
                "Significant shadow impact - review sunlight hours"
            )
        }


# Singleton instance
_spatial_3d = None


def get_spatial_3d_reasoning() -> Spatial3DReasoning:
    """Get or create 3D reasoning singleton."""
    global _spatial_3d
    if _spatial_3d is None:
        _spatial_3d = Spatial3DReasoning()
    return _spatial_3d
