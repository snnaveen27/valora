"""
Valora AI - Occlusion Engine
True line-of-sight and view corridor analysis using building geometry.

Features:
- Ray intersection against building footprints
- Line-of-sight between two 3D points
- View corridor analysis to landmarks
- Percentage view blockage calculation
- Multi-direction visibility scoring
"""

import sqlite3
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Ray3D:
    """A 3D ray from origin in a direction."""
    origin_lat: float
    origin_lng: float
    origin_height: float
    direction_azimuth: float  # 0 = North, 90 = East
    direction_elevation: float  # 0 = horizontal, 90 = straight up
    max_distance_m: float = 2000


@dataclass
class Intersection:
    """Result of ray-building intersection."""
    hit: bool
    building_id: Optional[str] = None
    building_name: Optional[str] = None
    building_height: float = 0
    distance_m: float = 0
    hit_height: float = 0  # Height at intersection point
    blocking_percentage: float = 0  # How much of view angle is blocked


@dataclass
class LineOfSightResult:
    """Result of line-of-sight check between two points."""
    clear: bool  # True if no obstruction
    blockers: List[Dict[str, Any]] = field(default_factory=list)
    total_blockage_percent: float = 0
    visibility_score: float = 100  # 100 = fully visible, 0 = blocked


@dataclass
class ViewCorridorResult:
    """Analysis of view corridor to a target."""
    target_name: str
    target_lat: float
    target_lng: float
    distance_m: float
    direction: str
    clear_path: bool
    blockers: List[Dict[str, Any]] = field(default_factory=list)
    visibility_percent: float = 100
    best_floor_for_view: int = 1
    reasoning: str = ""


class OcclusionEngine:
    """
    Computes true line-of-sight and view occlusion using building geometry.
    Uses simplified bounding-box intersection for performance.
    """
    
    # Constants
    FLOOR_HEIGHT_M = 3.0
    DIRECTIONS = {
        'N': 0, 'NE': 45, 'E': 90, 'SE': 135,
        'S': 180, 'SW': 225, 'W': 270, 'NW': 315
    }
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
    
    def _get_buildings_in_corridor(
        self,
        from_lat: float,
        from_lng: float,
        to_lat: float,
        to_lng: float,
        corridor_width_m: float = 50
    ) -> List[Dict[str, Any]]:
        """Get buildings within a corridor between two points."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Bounding box for corridor
            min_lat = min(from_lat, to_lat) - corridor_width_m / 111000
            max_lat = max(from_lat, to_lat) + corridor_width_m / 111000
            min_lng = min(from_lng, to_lng) - corridor_width_m / 111000
            max_lng = max(from_lng, to_lng) + corridor_width_m / 111000
            
            cursor.execute("""
                SELECT osm_id, name, height, levels, building_type, 
                       latitude, longitude
                FROM buildings
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                AND height > 0
                ORDER BY height DESC
                LIMIT 200
            """, (min_lat, max_lat, min_lng, max_lng))
            
            buildings = []
            for row in cursor.fetchall():
                buildings.append({
                    'id': str(row['osm_id']),
                    'name': row['name'],
                    'height': row['height'] or 0,
                    'levels': row['levels'] or 1,
                    'type': row['building_type'],
                    'lat': row['latitude'],
                    'lng': row['longitude']
                })
            
            conn.close()
            return buildings
            
        except Exception as e:
            print(f"[Occlusion] Error getting buildings: {e}")
            return []
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in meters."""
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _get_direction(self, from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> str:
        """Get cardinal direction."""
        dlat = to_lat - from_lat
        dlng = to_lng - from_lng
        angle = math.degrees(math.atan2(dlng, dlat))
        if angle < 0:
            angle += 360
        
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        index = round(angle / 45) % 8
        return directions[index]
    
    def _point_in_line_corridor(
        self,
        point_lat: float,
        point_lng: float,
        line_start_lat: float,
        line_start_lng: float,
        line_end_lat: float,
        line_end_lng: float,
        corridor_width_m: float
    ) -> Tuple[bool, float]:
        """
        Check if point is within corridor of a line segment.
        Returns (is_in_corridor, distance_along_line).
        """
        # Vector from start to end
        dx = line_end_lng - line_start_lng
        dy = line_end_lat - line_start_lat
        line_len_sq = dx*dx + dy*dy
        
        if line_len_sq == 0:
            return False, 0
        
        # Project point onto line
        t = max(0, min(1, (
            (point_lng - line_start_lng) * dx +
            (point_lat - line_start_lat) * dy
        ) / line_len_sq))
        
        # Closest point on line
        closest_lng = line_start_lng + t * dx
        closest_lat = line_start_lat + t * dy
        
        # Distance from point to closest point on line
        dist = self._haversine_distance(point_lat, point_lng, closest_lat, closest_lng)
        
        # Distance along line
        dist_along = t * math.sqrt(line_len_sq) * 111000  # Approximate to meters
        
        return dist <= corridor_width_m, dist_along
    
    def check_line_of_sight(
        self,
        from_lat: float,
        from_lng: float,
        from_height: float,
        to_lat: float,
        to_lng: float,
        to_height: float = 0
    ) -> LineOfSightResult:
        """
        Check if there's clear line of sight between two 3D points.
        
        Args:
            from_lat, from_lng, from_height: Observer position
            to_lat, to_lng, to_height: Target position
            
        Returns:
            LineOfSightResult with blockers and visibility score
        """
        result = LineOfSightResult(clear=True)
        
        total_distance = self._haversine_distance(from_lat, from_lng, to_lat, to_lng)
        if total_distance < 10:
            return result  # Too close, assume clear
        
        # Get buildings in corridor
        corridor_width = 30  # meters
        buildings = self._get_buildings_in_corridor(
            from_lat, from_lng, to_lat, to_lng, corridor_width
        )
        
        for bldg in buildings:
            # Check if building is in the line corridor
            in_corridor, dist_along = self._point_in_line_corridor(
                bldg['lat'], bldg['lng'],
                from_lat, from_lng,
                to_lat, to_lng,
                corridor_width
            )
            
            if not in_corridor:
                continue
            
            # Skip if building is at start or end
            if dist_along < 20 or dist_along > total_distance - 20:
                continue
            
            # Calculate sight line height at building location
            t = dist_along / total_distance
            sight_height_at_bldg = from_height + t * (to_height - from_height)
            
            # Check if building blocks the sight line
            if bldg['height'] > sight_height_at_bldg:
                # This building blocks the view
                blocking_amount = bldg['height'] - sight_height_at_bldg
                blocking_percent = min(100, (blocking_amount / max(1, from_height)) * 100)
                
                result.blockers.append({
                    'building_id': bldg['id'],
                    'name': bldg['name'],
                    'height': bldg['height'],
                    'distance_m': round(dist_along),
                    'blocking_height': round(blocking_amount, 1),
                    'blocking_percent': round(blocking_percent, 1)
                })
                result.clear = False
        
        # Calculate total blockage
        if result.blockers:
            result.total_blockage_percent = min(100, sum(b['blocking_percent'] for b in result.blockers))
            result.visibility_score = max(0, 100 - result.total_blockage_percent)
            result.blockers.sort(key=lambda x: x['distance_m'])
        
        return result
    
    def find_view_blockers(
        self,
        lat: float,
        lng: float,
        floor_height_m: float,
        direction: str = None,
        radius_m: float = 300
    ) -> List[Dict[str, Any]]:
        """
        Find buildings that block view from a location in given direction(s).
        
        Args:
            lat, lng: Observer location
            floor_height_m: Observer height
            direction: Specific direction or None for all
            radius_m: Search radius
            
        Returns:
            List of blocking buildings with severity
        """
        directions_to_check = [direction] if direction else list(self.DIRECTIONS.keys())
        all_blockers = []
        
        for dir_name in directions_to_check:
            azimuth = self.DIRECTIONS.get(dir_name, 0)
            
            # Calculate endpoint in this direction
            rad = math.radians(azimuth)
            end_lat = lat + (radius_m / 111000) * math.cos(rad)
            end_lng = lng + (radius_m / 111000) * math.sin(rad) / math.cos(math.radians(lat))
            
            # Check line of sight
            los_result = self.check_line_of_sight(
                lat, lng, floor_height_m,
                end_lat, end_lng, 0
            )
            
            for blocker in los_result.blockers:
                blocker['direction'] = dir_name
                blocker['severity'] = (
                    'high' if blocker['blocking_percent'] > 50 else
                    'medium' if blocker['blocking_percent'] > 20 else
                    'low'
                )
                all_blockers.append(blocker)
        
        # Sort by blocking percentage
        all_blockers.sort(key=lambda x: x['blocking_percent'], reverse=True)
        return all_blockers
    
    def analyze_view_corridor(
        self,
        from_lat: float,
        from_lng: float,
        from_floor: int,
        target_lat: float,
        target_lng: float,
        target_name: str = "Target"
    ) -> ViewCorridorResult:
        """
        Analyze view corridor from building to a specific target (lake, park, landmark).
        
        Args:
            from_lat, from_lng: Building location
            from_floor: Floor number
            target_lat, target_lng: Target location
            target_name: Name of target
            
        Returns:
            ViewCorridorResult with blockage analysis
        """
        from_height = (from_floor - 1) * self.FLOOR_HEIGHT_M + 1.5  # Eye level
        
        distance = self._haversine_distance(from_lat, from_lng, target_lat, target_lng)
        direction = self._get_direction(from_lat, from_lng, target_lat, target_lng)
        
        # Check line of sight
        los_result = self.check_line_of_sight(
            from_lat, from_lng, from_height,
            target_lat, target_lng, 0
        )
        
        # Find best floor for this view
        best_floor = from_floor
        best_visibility = los_result.visibility_score
        
        for test_floor in range(1, 26):  # Test up to 25 floors
            test_height = (test_floor - 1) * self.FLOOR_HEIGHT_M + 1.5
            test_los = self.check_line_of_sight(
                from_lat, from_lng, test_height,
                target_lat, target_lng, 0
            )
            if test_los.visibility_score > best_visibility:
                best_visibility = test_los.visibility_score
                best_floor = test_floor
                if best_visibility >= 95:
                    break  # Good enough
        
        # Generate reasoning
        if los_result.clear:
            reasoning = f"Clear view to {target_name} from floor {from_floor}."
        elif los_result.visibility_score >= 70:
            reasoning = f"Partial view of {target_name} with minor obstructions."
        elif los_result.visibility_score >= 30:
            primary_blocker = los_result.blockers[0] if los_result.blockers else {}
            reasoning = f"View significantly blocked by {primary_blocker.get('name', 'building')} ({primary_blocker.get('height', '?')}m tall, {primary_blocker.get('distance_m', '?')}m away)."
        else:
            reasoning = f"View to {target_name} is mostly blocked. Consider floor {best_floor}+ for better views."
        
        return ViewCorridorResult(
            target_name=target_name,
            target_lat=target_lat,
            target_lng=target_lng,
            distance_m=round(distance),
            direction=direction,
            clear_path=los_result.clear,
            blockers=los_result.blockers,
            visibility_percent=los_result.visibility_score,
            best_floor_for_view=best_floor,
            reasoning=reasoning
        )
    
    def get_360_visibility(
        self,
        lat: float,
        lng: float,
        floor: int = 1,
        radius_m: float = 500
    ) -> Dict[str, Any]:
        """
        Get 360-degree visibility analysis from a location.
        
        Args:
            lat, lng: Location
            floor: Floor number
            radius_m: View distance
            
        Returns:
            Dict with visibility in each direction
        """
        floor_height = (floor - 1) * self.FLOOR_HEIGHT_M + 1.5
        
        direction_results = {}
        open_directions = []
        blocked_directions = []
        total_visibility = 0
        
        for dir_name, azimuth in self.DIRECTIONS.items():
            # Cast ray in this direction
            rad = math.radians(azimuth)
            end_lat = lat + (radius_m / 111000) * math.cos(rad)
            end_lng = lng + (radius_m / 111000) * math.sin(rad) / math.cos(math.radians(lat))
            
            los = self.check_line_of_sight(lat, lng, floor_height, end_lat, end_lng, 0)
            
            direction_results[dir_name] = {
                'visibility': los.visibility_score,
                'clear': los.clear,
                'blockers': len(los.blockers),
                'primary_blocker': los.blockers[0] if los.blockers else None
            }
            
            total_visibility += los.visibility_score
            
            if los.visibility_score >= 70:
                open_directions.append(dir_name)
            elif los.visibility_score < 30:
                blocked_directions.append(dir_name)
        
        avg_visibility = total_visibility / 8
        
        return {
            'floor': floor,
            'height_m': floor_height,
            'directions': direction_results,
            'open_directions': open_directions,
            'blocked_directions': blocked_directions,
            'average_visibility': round(avg_visibility, 1),
            'openness_score': round(len(open_directions) / 8 * 100, 1),
            'view_quality': (
                'excellent' if avg_visibility >= 80 else
                'good' if avg_visibility >= 60 else
                'moderate' if avg_visibility >= 40 else
                'poor'
            )
        }
    
    def can_see_landmark(
        self,
        from_lat: float,
        from_lng: float,
        from_floor: int,
        landmark_name: str
    ) -> Dict[str, Any]:
        """
        Check if a specific landmark can be seen from a location.
        Looks up landmark coordinates from POIs.
        
        Args:
            from_lat, from_lng: Observer location
            from_floor: Floor number
            landmark_name: Name of landmark to check
            
        Returns:
            Dict with visibility result
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name, latitude, longitude, category
                FROM pois
                WHERE name LIKE ?
                AND latitude IS NOT NULL
                LIMIT 1
            """, (f"%{landmark_name}%",))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {
                    'found': False,
                    'error': f"Landmark '{landmark_name}' not found in database"
                }
            
            corridor = self.analyze_view_corridor(
                from_lat, from_lng, from_floor,
                row['latitude'], row['longitude'],
                row['name']
            )
            
            return {
                'found': True,
                'landmark': row['name'],
                'category': row['category'],
                'distance_m': corridor.distance_m,
                'direction': corridor.direction,
                'can_see': corridor.clear_path,
                'visibility_percent': corridor.visibility_percent,
                'blockers': corridor.blockers,
                'best_floor': corridor.best_floor_for_view,
                'reasoning': corridor.reasoning
            }
            
        except Exception as e:
            return {'found': False, 'error': str(e)}


# Singleton
_occlusion_engine = None


def get_occlusion_engine() -> OcclusionEngine:
    """Get or create occlusion engine singleton."""
    global _occlusion_engine
    if _occlusion_engine is None:
        _occlusion_engine = OcclusionEngine()
    return _occlusion_engine
