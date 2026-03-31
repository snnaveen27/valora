"""
Viewshed Analysis Engine for Valora AI
Phase 1.2: View Quality and Visibility Analysis

Features:
- Ray-casting based visibility from a point
- Floor-level view quality estimation
- Direction-based view analysis (N/S/E/W)
- Landmark visibility detection
- Sky view factor calculation
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import math


@dataclass
class ViewRay:
    """A single view ray from observer to a direction"""
    direction: str  # "N", "NE", "E", "SE", "S", "SW", "W", "NW"
    azimuth_deg: float  # 0 = North, 90 = East
    max_distance_m: float  # How far the view extends
    blocked_at_m: Optional[float] = None  # Distance where blocked
    blocked_by: Optional[str] = None  # What blocks it (building, terrain)
    view_quality: str = "open"  # "open", "partial", "blocked"


@dataclass
class ViewshedResult:
    """Complete viewshed analysis result"""
    observer_lat: float
    observer_lng: float
    observer_height_m: float  # Height above ground (floor level)
    floor_number: int
    
    # View rays in 8 cardinal directions
    rays: List[ViewRay] = field(default_factory=list)
    
    # Aggregate metrics
    sky_view_factor: float = 0.0  # 0-1, how much sky is visible
    openness_score: float = 0.0  # 0-100
    best_view_direction: str = ""
    worst_view_direction: str = ""
    
    # Visible landmarks
    visible_landmarks: List[Dict[str, Any]] = field(default_factory=list)
    
    # Summary
    view_description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "location": {"lat": self.observer_lat, "lng": self.observer_lng},
            "floor": self.floor_number,
            "height_m": self.observer_height_m,
            "rays": [
                {
                    "direction": r.direction,
                    "azimuth": r.azimuth_deg,
                    "max_distance": r.max_distance_m,
                    "blocked_at": r.blocked_at_m,
                    "blocked_by": r.blocked_by,
                    "quality": r.view_quality
                }
                for r in self.rays
            ],
            "sky_view_factor": self.sky_view_factor,
            "openness_score": self.openness_score,
            "best_view": self.best_view_direction,
            "worst_view": self.worst_view_direction,
            "visible_landmarks": self.visible_landmarks,
            "description": self.view_description
        }


class ViewshedAnalyzer:
    """
    Analyzes what can be seen from a given location and floor level.
    Uses simplified ray-casting against nearby buildings.
    """
    
    # Cardinal directions with azimuths
    DIRECTIONS = [
        ("N", 0),
        ("NE", 45),
        ("E", 90),
        ("SE", 135),
        ("S", 180),
        ("SW", 225),
        ("W", 270),
        ("NW", 315),
    ]
    
    # Floor height in meters
    FLOOR_HEIGHT_M = 3.0
    
    # Maximum view distance in meters
    MAX_VIEW_DISTANCE = 2000
    
    def __init__(self):
        self.db_service = None
        self._init_database()
    
    def _init_database(self):
        """Initialize database connection."""
        try:
            from database.db_service import DatabaseService
            from pathlib import Path
            from backend.config import config
            self.db_service = DatabaseService(str(config.DB_PATH))
        except Exception as e:
            print(f"[ViewshedAnalyzer] Database init error: {e}")
    
    def _get_nearby_buildings(self, lat: float, lng: float, radius_m: float) -> List[Dict]:
        """Get buildings within radius."""
        if not self.db_service:
            return []
        
        radius_deg = radius_m / 111000
        
        try:
            query = """
                SELECT osm_id, building_type, height, levels, latitude, longitude
                FROM buildings
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            results = self.db_service.execute(query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            return results or []
        except:
            return []
    
    def _get_landmarks(self, lat: float, lng: float, radius_m: float) -> List[Dict]:
        """Get notable landmarks/POIs within radius."""
        if not self.db_service:
            return []
        
        radius_deg = radius_m / 111000
        
        try:
            query = """
                SELECT name, category, latitude, longitude
                FROM pois
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                AND name IS NOT NULL
                AND name != ''
            """
            results = self.db_service.execute(query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            return results or []
        except:
            return []
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in meters."""
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing from point 1 to point 2 in degrees."""
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        dlon = math.radians(lon2 - lon1)
        
        x = math.sin(dlon) * math.cos(lat2_r)
        y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon)
        
        bearing = math.atan2(x, y)
        return (math.degrees(bearing) + 360) % 360
    
    def _get_direction_for_bearing(self, bearing: float) -> str:
        """Get cardinal direction for a bearing."""
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        index = round(bearing / 45) % 8
        return directions[index]
    
    def _cast_ray(self, observer_lat: float, observer_lng: float, 
                  observer_height: float, azimuth: float,
                  buildings: List[Dict]) -> ViewRay:
        """
        Cast a ray in a direction and check for obstructions.
        
        Args:
            observer_lat, observer_lng: Observer position
            observer_height: Observer height above ground in meters
            azimuth: Direction in degrees (0 = North)
            buildings: List of nearby buildings
            
        Returns:
            ViewRay with obstruction info
        """
        direction = self._get_direction_for_bearing(azimuth)
        ray = ViewRay(
            direction=direction,
            azimuth_deg=azimuth,
            max_distance_m=self.MAX_VIEW_DISTANCE,
            view_quality="open"
        )
        
        # Check each building in this direction
        min_blocking_distance = self.MAX_VIEW_DISTANCE
        blocking_building = None
        
        for building in buildings:
            b_lat = building.get('latitude')
            b_lng = building.get('longitude')
            levels = building.get('levels')
            fallback_height = (float(levels) * self.FLOOR_HEIGHT_M) if levels not in (None, "") else 10.0
            b_height = float(building.get('height') or fallback_height)
            
            if not b_lat or not b_lng:
                continue
            
            # Calculate bearing to building
            bearing = self._calculate_bearing(observer_lat, observer_lng, b_lat, b_lng)
            
            # Check if building is in this ray's direction (within 22.5 degrees)
            angle_diff = abs(bearing - azimuth)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            
            if angle_diff <= 22.5:
                # Building is in this direction
                distance = self._haversine_distance(observer_lat, observer_lng, b_lat, b_lng)
                
                if distance < 10:  # Skip very close (probably same building)
                    continue
                
                # Check if building blocks view (taller than our eye level at that distance)
                # Simple model: view angle to top of building
                if b_height > observer_height:
                    # Building is taller - it blocks
                    if distance < min_blocking_distance:
                        min_blocking_distance = distance
                        blocking_building = building.get('building_type', 'building')
        
        if min_blocking_distance < self.MAX_VIEW_DISTANCE:
            ray.blocked_at_m = min_blocking_distance
            ray.blocked_by = blocking_building
            
            # Determine view quality based on blocking distance
            if min_blocking_distance < 50:
                ray.view_quality = "blocked"
            elif min_blocking_distance < 200:
                ray.view_quality = "partial"
            else:
                ray.view_quality = "open"
        
        return ray
    
    def _calculate_sky_view_factor(self, rays: List[ViewRay], observer_height: float) -> float:
        """
        Estimate sky view factor based on ray analysis.
        SVF = proportion of sky visible from location.
        """
        total_openness = 0
        
        for ray in rays:
            if ray.view_quality == "open":
                total_openness += 1.0
            elif ray.view_quality == "partial":
                total_openness += 0.5
            # blocked = 0
        
        base_svf = total_openness / len(rays) if rays else 0
        
        # Adjust for height (higher floors have better sky view)
        height_bonus = min(0.3, observer_height / 100)  # Up to 30% bonus
        
        return min(1.0, base_svf + height_bonus)
    
    def _find_visible_landmarks(self, observer_lat: float, observer_lng: float,
                                 observer_height: float, rays: List[ViewRay],
                                 landmarks: List[Dict]) -> List[Dict]:
        """Find landmarks that are likely visible from this location."""
        visible = []
        
        for landmark in landmarks:
            l_lat = landmark.get('latitude')
            l_lng = landmark.get('longitude')
            
            if not l_lat or not l_lng:
                continue
            
            distance = self._haversine_distance(observer_lat, observer_lng, l_lat, l_lng)
            bearing = self._calculate_bearing(observer_lat, observer_lng, l_lat, l_lng)
            direction = self._get_direction_for_bearing(bearing)
            
            # Find the ray for this direction
            ray_for_direction = None
            for ray in rays:
                if ray.direction == direction:
                    ray_for_direction = ray
                    break
            
            # Check if landmark is within unblocked distance
            if ray_for_direction:
                blocking_dist = ray_for_direction.blocked_at_m or self.MAX_VIEW_DISTANCE
                if distance < blocking_dist:
                    visible.append({
                        "name": landmark.get('name'),
                        "category": landmark.get('category'),
                        "distance_m": round(distance),
                        "direction": direction
                    })
        
        return sorted(visible, key=lambda x: x['distance_m'])[:10]
    
    def analyze_viewshed(self, lat: float, lng: float, 
                         floor: int = 1, building_height: float = None) -> ViewshedResult:
        """
        Analyze viewshed from a specific location and floor.
        
        Args:
            lat, lng: Observer location
            floor: Floor number (1-indexed)
            building_height: Total building height (optional)
            
        Returns:
            ViewshedResult with complete analysis
        """
        # Calculate observer height
        observer_height = (floor - 1) * self.FLOOR_HEIGHT_M + 1.5  # Eye level
        
        result = ViewshedResult(
            observer_lat=lat,
            observer_lng=lng,
            observer_height_m=observer_height,
            floor_number=floor
        )
        
        # Get nearby buildings
        buildings = self._get_nearby_buildings(lat, lng, self.MAX_VIEW_DISTANCE)
        
        # Cast rays in 8 directions
        for direction, azimuth in self.DIRECTIONS:
            ray = self._cast_ray(lat, lng, observer_height, azimuth, buildings)
            result.rays.append(ray)
        
        # Calculate metrics
        result.sky_view_factor = self._calculate_sky_view_factor(result.rays, observer_height)
        
        # Find best and worst views
        open_rays = [r for r in result.rays if r.view_quality == "open"]
        blocked_rays = [r for r in result.rays if r.view_quality == "blocked"]
        
        if open_rays:
            # Best view = furthest open view
            best = max(open_rays, key=lambda r: r.blocked_at_m or self.MAX_VIEW_DISTANCE)
            result.best_view_direction = best.direction
        
        if blocked_rays:
            # Worst view = closest blocking
            worst = min(blocked_rays, key=lambda r: r.blocked_at_m or 0)
            result.worst_view_direction = worst.direction
        
        # Calculate openness score
        open_count = len([r for r in result.rays if r.view_quality == "open"])
        partial_count = len([r for r in result.rays if r.view_quality == "partial"])
        result.openness_score = ((open_count * 100) + (partial_count * 50)) / 8
        
        # Find visible landmarks
        landmarks = self._get_landmarks(lat, lng, self.MAX_VIEW_DISTANCE)
        result.visible_landmarks = self._find_visible_landmarks(
            lat, lng, observer_height, result.rays, landmarks
        )
        
        # Generate description
        result.view_description = self._generate_description(result)
        
        return result
    
    def _generate_description(self, result: ViewshedResult) -> str:
        """Generate natural language description of the view."""
        parts = []
        
        # Overall assessment
        if result.openness_score >= 80:
            parts.append(f"Excellent panoramic views from floor {result.floor_number}")
        elif result.openness_score >= 60:
            parts.append(f"Good views from floor {result.floor_number}")
        elif result.openness_score >= 40:
            parts.append(f"Moderate views from floor {result.floor_number}")
        else:
            parts.append(f"Limited views from floor {result.floor_number}")
        
        # Best direction
        if result.best_view_direction:
            parts.append(f"Best views toward the {result.best_view_direction}")
        
        # Blocked directions
        blocked = [r.direction for r in result.rays if r.view_quality == "blocked"]
        if blocked:
            parts.append(f"Views blocked toward {', '.join(blocked)}")
        
        # Visible landmarks
        if result.visible_landmarks:
            landmark_names = [l['name'] for l in result.visible_landmarks[:3]]
            parts.append(f"Can see: {', '.join(landmark_names)}")
        
        # Sky view
        if result.sky_view_factor >= 0.7:
            parts.append("Excellent sky exposure and natural light")
        elif result.sky_view_factor >= 0.4:
            parts.append("Good natural light")
        else:
            parts.append("Limited natural light due to surrounding buildings")
        
        return ". ".join(parts) + "."
    
    def compare_floors(self, lat: float, lng: float, 
                       floors: List[int] = None) -> Dict[str, Any]:
        """
        Compare view quality across different floors.
        
        Args:
            lat, lng: Building location
            floors: List of floor numbers to compare (default: 1, 5, 10, 15, 20)
            
        Returns:
            Comparison results
        """
        if floors is None:
            floors = [1, 5, 10, 15, 20]
        
        results = []
        for floor in floors:
            analysis = self.analyze_viewshed(lat, lng, floor)
            results.append({
                "floor": floor,
                "openness_score": analysis.openness_score,
                "sky_view_factor": analysis.sky_view_factor,
                "best_direction": analysis.best_view_direction,
                "visible_landmarks_count": len(analysis.visible_landmarks)
            })
        
        # Find optimal floor (best value considering that higher floors cost more)
        # Simple model: diminishing returns after floor 10
        best_value_floor = 1
        best_value = 0
        for r in results:
            # Value = openness * (1 - premium penalty)
            premium_penalty = max(0, (r['floor'] - 10) * 0.02)  # 2% penalty per floor above 10
            value = r['openness_score'] * (1 - premium_penalty)
            if value > best_value:
                best_value = value
                best_value_floor = r['floor']
        
        return {
            "floors_compared": results,
            "best_value_floor": best_value_floor,
            "recommendation": f"Floor {best_value_floor} offers the best balance of view quality and value"
        }


# Singleton instance
_viewshed_analyzer = None


def get_viewshed_analyzer() -> ViewshedAnalyzer:
    """Get or create viewshed analyzer singleton."""
    global _viewshed_analyzer
    if _viewshed_analyzer is None:
        _viewshed_analyzer = ViewshedAnalyzer()
    return _viewshed_analyzer
