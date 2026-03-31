"""
Building 3D Analysis Engine for Valora AI
Phase 1.1: 3D Spatial Intelligence

Features:
- Height-aware proximity analysis
- Shadow impact calculations (simplified)
- View obstruction analysis
- Building density contribution
- Floor-level accessibility metrics
- Vertical distance to amenities
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import math
from pathlib import Path


@dataclass
class Building3DAnalysis:
    """Results from 3D building analysis."""
    building_id: str = ""
    building_type: str = ""
    height_m: float = 0.0
    floors: int = 0
    latitude: float = 0.0
    longitude: float = 0.0
    
    # 3D Metrics
    shadow_impact_score: float = 0.0  # 0-100, lower is better (less shadowed)
    view_obstruction_score: float = 0.0  # 0-100, lower is better (more open views)
    density_contribution: float = 0.0  # Building's contribution to local density
    floor_accessibility: Dict[str, float] = field(default_factory=dict)  # Per-floor metrics
    
    # Nearby Analysis
    taller_neighbors: int = 0
    shorter_neighbors: int = 0
    avg_neighbor_height: float = 0.0
    
    # Amenity Access (vertical distance considered)
    ground_floor_amenities: int = 0
    rooftop_accessible: bool = False
    elevator_likely: bool = False
    
    # Phase 1.3: 3D Proximity Intelligence (complete)
    eye_level_neighbors: List[Dict[str, Any]] = field(default_factory=list)  # Buildings at same height
    rooftop_amenities: List[str] = field(default_factory=list)  # Detected rooftop features
    vertical_transport_access: Dict[str, Any] = field(default_factory=dict)  # Metro/bus vertical distance
    nearest_metro_3d: Optional[Dict[str, Any]] = None  # Nearest metro with vertical distance
    nearest_bus_3d: Optional[Dict[str, Any]] = None  # Nearest bus with vertical distance
    
    # View Analysis
    estimated_view_quality: str = "unknown"  # "excellent", "good", "moderate", "poor"
    view_directions: List[str] = field(default_factory=list)  # ["north", "east", etc.]
    
    # Viewshed Analysis (Phase 1.2)
    viewshed_result: Optional[Dict[str, Any]] = None
    sky_view_factor: float = 0.0
    visible_landmarks: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "building_id": self.building_id,
            "building_type": self.building_type,
            "height_m": self.height_m,
            "floors": self.floors,
            "location": {"lat": self.latitude, "lng": self.longitude},
            "shadow_impact": {
                "score": self.shadow_impact_score,
                "rating": "good" if self.shadow_impact_score < 30 else "moderate" if self.shadow_impact_score < 60 else "significant"
            },
            "view_obstruction": {
                "score": self.view_obstruction_score,
                "rating": "open" if self.view_obstruction_score < 30 else "partial" if self.view_obstruction_score < 60 else "obstructed"
            },
            "density_contribution": self.density_contribution,
            "neighbors": {
                "taller": self.taller_neighbors,
                "shorter": self.shorter_neighbors,
                "avg_height": self.avg_neighbor_height
            },
            "floor_accessibility": self.floor_accessibility,
            "ground_amenities": self.ground_floor_amenities,
            "elevator_likely": self.elevator_likely,
            "view_quality": self.estimated_view_quality,
            "view_directions": self.view_directions
        }


class BuildingAnalyzer:
    """3D Building Analysis Engine."""
    
    # Average floor height in meters
    FLOOR_HEIGHT_M = 3.0
    
    # Sun angle for shadow calculation (simplified, assuming ~45 degree afternoon sun)
    SUN_ANGLE = 45
    
    # Radius for neighbor analysis (meters)
    NEIGHBOR_RADIUS = 100
    
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
            print(f"[BuildingAnalyzer] Database init error: {e}")
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in meters."""
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _estimate_floors(self, height_m: float) -> int:
        """Estimate number of floors from height."""
        if height_m <= 0:
            return 1
        return max(1, int(height_m / self.FLOOR_HEIGHT_M))
    
    def _get_direction(self, from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> str:
        """Get cardinal direction from one point to another."""
        lat_diff = to_lat - from_lat
        lng_diff = to_lng - from_lng
        
        # Calculate bearing
        bearing = math.degrees(math.atan2(lng_diff, lat_diff))
        bearing = (bearing + 360) % 360
        
        # Convert to cardinal direction
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        index = round(bearing / 45) % 8
        return directions[index]
    
    def _get_vertical_transport_access(self, lat: float, lng: float, building_height: float) -> Dict[str, Any]:
        """
        Calculate 3D distance to nearest transport (metro/bus).
        Considers vertical distance from upper floors to ground-level transport.
        """
        result = {
            'nearest_metro': None,
            'nearest_bus': None,
            'vertical_penalty_factor': 1.0 + (building_height / 100)  # Higher floors = longer to reach ground
        }
        
        if not self.db_service:
            return result
        
        radius_deg = 2000 / 111000  # 2km radius
        
        try:
            # Find nearest metro
            metro_query = """
                SELECT name, latitude, longitude FROM transport
                WHERE type IN ('metro', 'subway', 'metro_station')
                AND latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                LIMIT 5
            """
            metros = self.db_service.execute(metro_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            )) or []
            
            if metros:
                nearest_metro = None
                min_dist = float('inf')
                for m in metros:
                    if m.get('latitude') and m.get('longitude'):
                        dist = self._haversine_distance(lat, lng, m['latitude'], m['longitude'])
                        if dist < min_dist:
                            min_dist = dist
                            nearest_metro = m
                
                if nearest_metro:
                    # Calculate 3D distance (horizontal + vertical)
                    horizontal_dist = min_dist
                    vertical_dist = building_height  # Need to go down to ground level
                    # Walking speed: 5 km/h horizontal, 1 floor/30 sec vertical
                    horizontal_time_min = (horizontal_dist / 1000) / 5 * 60
                    vertical_time_min = (building_height / self.FLOOR_HEIGHT_M) * 0.5  # 30 sec per floor
                    total_time = horizontal_time_min + vertical_time_min
                    
                    result['nearest_metro'] = {
                        'name': nearest_metro.get('name', 'Metro Station'),
                        'horizontal_distance_m': round(horizontal_dist),
                        'vertical_distance_m': round(building_height),
                        'total_walk_time_min': round(total_time, 1),
                        'direction': self._get_direction(lat, lng, nearest_metro['latitude'], nearest_metro['longitude'])
                    }
            
            # Find nearest bus stop
            bus_query = """
                SELECT name, latitude, longitude FROM transport
                WHERE type IN ('bus', 'bus_stop', 'bus_station')
                AND latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                LIMIT 5
            """
            buses = self.db_service.execute(bus_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            )) or []
            
            if buses:
                nearest_bus = None
                min_dist = float('inf')
                for b in buses:
                    if b.get('latitude') and b.get('longitude'):
                        dist = self._haversine_distance(lat, lng, b['latitude'], b['longitude'])
                        if dist < min_dist:
                            min_dist = dist
                            nearest_bus = b
                
                if nearest_bus:
                    horizontal_dist = min_dist
                    horizontal_time_min = (horizontal_dist / 1000) / 5 * 60
                    vertical_time_min = (building_height / self.FLOOR_HEIGHT_M) * 0.5
                    total_time = horizontal_time_min + vertical_time_min
                    
                    result['nearest_bus'] = {
                        'name': nearest_bus.get('name', 'Bus Stop'),
                        'horizontal_distance_m': round(horizontal_dist),
                        'vertical_distance_m': round(building_height),
                        'total_walk_time_min': round(total_time, 1),
                        'direction': self._get_direction(lat, lng, nearest_bus['latitude'], nearest_bus['longitude'])
                    }
        except Exception as e:
            print(f"[BuildingAnalyzer] Vertical transport error: {e}")
        
        return result
    
    def _get_nearby_buildings(self, lat: float, lng: float, radius_m: float = 100) -> List[Dict]:
        """Get buildings within radius of a point."""
        if not self.db_service:
            return []
        
        # Convert radius to approximate degrees (at Bangalore latitude)
        radius_deg = radius_m / 111000  # ~111km per degree
        
        try:
            query = """
                SELECT osm_id, building_type, height, levels, latitude, longitude
                FROM buildings
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                AND latitude IS NOT NULL
                AND longitude IS NOT NULL
            """
            results = self.db_service.execute(query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            
            # Filter by actual distance and exclude the target building
            nearby = []
            for b in results:
                dist = self._haversine_distance(lat, lng, b['latitude'], b['longitude'])
                if dist <= radius_m and dist > 1:  # Exclude self (dist > 1m)
                    b['distance_m'] = dist
                    nearby.append(b)
            
            return nearby
        except Exception as e:
            print(f"[BuildingAnalyzer] Error getting nearby buildings: {e}")
            return []
    
    def _calculate_shadow_impact(self, height: float, neighbors: List[Dict], direction: str = "south") -> float:
        """
        Calculate shadow impact score based on taller buildings.
        Higher score = more shadowed.
        """
        if not neighbors:
            return 0.0
        
        # Find buildings that could cast shadows (taller and in sun direction)
        shadow_score = 0.0
        
        for n in neighbors:
            n_height = n.get('height') or 0
            n_dist = n.get('distance_m', 100)
            
            if n_height > height:
                # Taller building - calculate shadow reach
                height_diff = n_height - height
                shadow_length = height_diff / math.tan(math.radians(self.SUN_ANGLE))
                
                if n_dist < shadow_length:
                    # This building is within shadow zone
                    impact = (1 - n_dist / shadow_length) * 100
                    shadow_score = max(shadow_score, impact)
        
        return min(100, shadow_score)
    
    def _calculate_view_obstruction(self, height: float, neighbors: List[Dict]) -> Tuple[float, List[str]]:
        """
        Calculate view obstruction score and open view directions.
        """
        if not neighbors:
            return 0.0, ["north", "south", "east", "west"]
        
        # Divide into 4 quadrants
        quadrants = {
            "north": [],
            "south": [],
            "east": [],
            "west": []
        }
        
        for n in neighbors:
            n_lat = n.get('latitude', 0)
            n_lng = n.get('longitude', 0)
            # Determine quadrant based on relative position
            # This is simplified - north is higher lat, east is higher lng
            if n_lat > 0:  # Relative to center
                pass  # Would need center lat/lng to properly calculate
        
        # For now, calculate overall obstruction
        taller_count = sum(1 for n in neighbors if (n.get('height') or 0) > height)
        total_neighbors = len(neighbors)
        
        if total_neighbors == 0:
            return 0.0, ["north", "south", "east", "west"]
        
        obstruction_score = (taller_count / total_neighbors) * 100
        
        # Estimate open directions (simplified)
        open_directions = []
        if obstruction_score < 50:
            open_directions = ["north", "south", "east", "west"]
        elif obstruction_score < 75:
            open_directions = ["north", "south"]  # Assume some directions blocked
        else:
            open_directions = []
        
        return obstruction_score, open_directions
    
    def _calculate_density_contribution(self, height: float, neighbors: List[Dict], area_sqm: float = 10000) -> float:
        """
        Calculate this building's contribution to local density.
        Returns percentage of total vertical space in area.
        """
        if not neighbors:
            return 100.0  # Only building in area
        
        total_height = height
        for n in neighbors:
            total_height += (n.get('height') or 3)
        
        if total_height == 0:
            return 0.0
        
        return (height / total_height) * 100
    
    def _estimate_view_quality(self, height: float, obstruction_score: float, floors: int) -> str:
        """Estimate overall view quality."""
        # Higher floors generally have better views
        floor_bonus = min(30, floors * 3)  # Up to 30 bonus points
        
        # Base score: lower obstruction = better view
        base_score = 100 - obstruction_score + floor_bonus
        
        if base_score >= 90:
            return "excellent"
        elif base_score >= 70:
            return "good"
        elif base_score >= 50:
            return "moderate"
        else:
            return "poor"
    
    def _get_ground_floor_amenities(self, lat: float, lng: float, radius_m: float = 50) -> int:
        """Count ground-floor accessible amenities (POIs within walking distance)."""
        if not self.db_service:
            return 0
        
        radius_deg = radius_m / 111000
        
        try:
            query = """
                SELECT COUNT(*) as cnt FROM pois
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            result = self.db_service.execute(query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            return result[0]['cnt'] if result else 0
        except:
            return 0
    
    def analyze_building(self, lat: float, lng: float, height: float = None, 
                        building_type: str = None, building_id: str = None) -> Building3DAnalysis:
        """
        Perform comprehensive 3D analysis of a building.
        
        Args:
            lat: Latitude of building
            lng: Longitude of building
            height: Building height in meters (optional, will look up if not provided)
            building_type: Type of building (optional)
            building_id: OSM ID or other identifier (optional)
        
        Returns:
            Building3DAnalysis with all computed metrics
        """
        analysis = Building3DAnalysis()
        analysis.latitude = lat
        analysis.longitude = lng
        analysis.building_id = building_id or f"{lat:.5f}_{lng:.5f}"
        analysis.building_type = building_type or "unknown"
        
        # If height not provided, try to look it up
        if height is None:
            height = self._lookup_building_height(lat, lng)
        
        analysis.height_m = height or 10.0  # Default 10m if unknown
        analysis.floors = self._estimate_floors(analysis.height_m)
        
        # Get nearby buildings for context
        neighbors = self._get_nearby_buildings(lat, lng, self.NEIGHBOR_RADIUS)
        
        # Analyze neighbors
        if neighbors:
            neighbor_heights = [(n.get('height') or 3) for n in neighbors]
            analysis.taller_neighbors = sum(1 for h in neighbor_heights if h > analysis.height_m)
            analysis.shorter_neighbors = sum(1 for h in neighbor_heights if h < analysis.height_m)
            analysis.avg_neighbor_height = sum(neighbor_heights) / len(neighbor_heights)
        
        # Calculate 3D metrics
        analysis.shadow_impact_score = self._calculate_shadow_impact(analysis.height_m, neighbors)
        obstruction, open_dirs = self._calculate_view_obstruction(analysis.height_m, neighbors)
        analysis.view_obstruction_score = obstruction
        analysis.view_directions = open_dirs
        analysis.density_contribution = self._calculate_density_contribution(analysis.height_m, neighbors)
        
        # View quality estimation
        analysis.estimated_view_quality = self._estimate_view_quality(
            analysis.height_m, 
            analysis.view_obstruction_score,
            analysis.floors
        )
        
        # Floor-level accessibility
        analysis.floor_accessibility = self._calculate_floor_accessibility(analysis.floors, lat, lng)
        
        # Ground-floor amenities
        analysis.ground_floor_amenities = self._get_ground_floor_amenities(lat, lng)
        
        # Elevator likelihood (buildings > 4 floors typically have elevators)
        analysis.elevator_likely = analysis.floors > 4
        
        # Phase 1.3: 3D Proximity Intelligence (complete)
        # Eye-level neighbors (buildings within ±3m of our height)
        if neighbors:
            height_tolerance = 3.0  # meters
            for n in neighbors:
                levels = n.get('levels')
                fallback_height = (float(levels) * self.FLOOR_HEIGHT_M) if levels not in (None, "") else 0.0
                n_height = float(n.get('height') or fallback_height)
                if abs(n_height - analysis.height_m) <= height_tolerance:
                    n_lat = n.get('latitude')
                    n_lng = n.get('longitude')
                    if n_lat and n_lng:
                        dist = self._haversine_distance(lat, lng, n_lat, n_lng)
                        analysis.eye_level_neighbors.append({
                            'distance_m': round(dist),
                            'height_m': n_height,
                            'direction': self._get_direction(lat, lng, n_lat, n_lng),
                            'type': n.get('building_type', 'unknown')
                        })
            analysis.eye_level_neighbors = sorted(analysis.eye_level_neighbors, key=lambda x: x['distance_m'])[:5]
        
        # Rooftop amenities detection (buildings with likely rooftop features)
        if analysis.floors >= 5:
            analysis.rooftop_accessible = True
            # Check for nearby tall buildings that might have rooftop restaurants/pools
            if analysis.floors >= 10:
                analysis.rooftop_amenities.append("potential_rooftop_access")
            if analysis.building_type in ['hotel', 'commercial', 'mixed']:
                analysis.rooftop_amenities.append("likely_rooftop_restaurant")
            if analysis.sky_view_factor >= 0.6:
                analysis.rooftop_amenities.append("good_rooftop_views")
        
        # Vertical transport access (3D distance to metro/bus)
        analysis.vertical_transport_access = self._get_vertical_transport_access(lat, lng, analysis.height_m)
        if analysis.vertical_transport_access.get('nearest_metro'):
            analysis.nearest_metro_3d = analysis.vertical_transport_access['nearest_metro']
        if analysis.vertical_transport_access.get('nearest_bus'):
            analysis.nearest_bus_3d = analysis.vertical_transport_access['nearest_bus']
        
        # Phase 1.2: Viewshed Analysis
        try:
            from analyzers.viewshed_analyzer import get_viewshed_analyzer
            viewshed = get_viewshed_analyzer()
            vs_result = viewshed.analyze_viewshed(lat, lng, floor=analysis.floors)
            analysis.viewshed_result = vs_result.to_dict()
            analysis.sky_view_factor = vs_result.sky_view_factor
            analysis.visible_landmarks = [l['name'] for l in vs_result.visible_landmarks[:5]]
            
            # Update view quality based on viewshed
            if vs_result.openness_score >= 80:
                analysis.estimated_view_quality = "excellent"
            elif vs_result.openness_score >= 60:
                analysis.estimated_view_quality = "good"
            elif vs_result.openness_score >= 40:
                analysis.estimated_view_quality = "moderate"
            else:
                analysis.estimated_view_quality = "poor"
            
            # Update open view directions
            analysis.view_directions = [r.direction for r in vs_result.rays if r.view_quality == "open"]
        except Exception as e:
            print(f"[BuildingAnalyzer] Viewshed error: {e}")
        
        return analysis
    
    def _lookup_building_height(self, lat: float, lng: float) -> Optional[float]:
        """Look up building height from database."""
        if not self.db_service:
            return None
        
        radius_deg = 0.0001  # Very small radius to find exact building
        
        try:
            query = """
                SELECT height, levels FROM buildings
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                LIMIT 1
            """
            result = self.db_service.execute(query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            if result:
                height = result[0].get('height')
                levels = result[0].get('levels')
                if height:
                    return float(height)
                elif levels:
                    return float(levels) * self.FLOOR_HEIGHT_M
        except:
            pass
        return None
    
    def _calculate_floor_accessibility(self, floors: int, lat: float, lng: float) -> Dict[str, float]:
        """
        Calculate accessibility metrics per floor level.
        Higher floors = more stairs/elevator time but potentially better views.
        """
        accessibility = {}
        
        for floor in range(1, floors + 1):
            # Time to reach floor (assuming 30 seconds per floor by stairs, 5 by elevator)
            stairs_time = floor * 30  # seconds
            elevator_time = floor * 5 + 30  # 30 sec wait + 5 sec per floor
            
            # Convenience score (100 = ground floor, decreases with height)
            if floor <= 4:
                convenience = 100 - (floor - 1) * 10  # 100, 90, 80, 70
            else:
                convenience = 60 - (floor - 4) * 5  # Decreases more slowly with elevator
            
            accessibility[f"floor_{floor}"] = {
                "stairs_time_sec": stairs_time,
                "elevator_time_sec": elevator_time if floors > 4 else None,
                "convenience_score": max(20, convenience)
            }
        
        return accessibility
    
    def analyze_building_context(self, lat: float, lng: float) -> Dict[str, Any]:
        """
        Analyze building in urban context - for use by AI agents.
        Returns a summary suitable for LLM context.
        """
        analysis = self.analyze_building(lat, lng)
        
        # Generate natural language summary
        summary_parts = []
        
        # Height context
        if analysis.floors > 10:
            summary_parts.append(f"This is a high-rise building ({analysis.floors} floors, {analysis.height_m:.1f}m)")
        elif analysis.floors > 5:
            summary_parts.append(f"This is a mid-rise building ({analysis.floors} floors, {analysis.height_m:.1f}m)")
        else:
            summary_parts.append(f"This is a low-rise building ({analysis.floors} floors, {analysis.height_m:.1f}m)")
        
        # Neighbor context
        if analysis.taller_neighbors > analysis.shorter_neighbors:
            summary_parts.append(f"surrounded by taller buildings ({analysis.taller_neighbors} taller neighbors)")
        elif analysis.shorter_neighbors > analysis.taller_neighbors:
            summary_parts.append(f"one of the taller buildings in the area ({analysis.shorter_neighbors} shorter neighbors)")
        
        # View quality
        summary_parts.append(f"View quality: {analysis.estimated_view_quality}")
        
        # Shadow impact
        if analysis.shadow_impact_score > 50:
            summary_parts.append("Significant shadow impact from neighboring buildings")
        elif analysis.shadow_impact_score > 20:
            summary_parts.append("Moderate shadow impact")
        else:
            summary_parts.append("Good sun exposure")
        
        # Amenities
        if analysis.ground_floor_amenities > 5:
            summary_parts.append(f"Excellent ground-floor amenity access ({analysis.ground_floor_amenities} POIs within 50m)")
        elif analysis.ground_floor_amenities > 0:
            summary_parts.append(f"Some nearby amenities ({analysis.ground_floor_amenities} POIs within 50m)")
        
        return {
            "analysis": analysis.to_dict(),
            "summary": ". ".join(summary_parts) + ".",
            "highlights": {
                "view_quality": analysis.estimated_view_quality,
                "shadow_rating": "good" if analysis.shadow_impact_score < 30 else "moderate" if analysis.shadow_impact_score < 60 else "significant",
                "density_percentile": f"{analysis.density_contribution:.0f}%",
                "floor_count": analysis.floors,
                "elevator": "yes" if analysis.elevator_likely else "no",
                "nearby_amenities": analysis.ground_floor_amenities
            }
        }


# Singleton instance
_building_analyzer = None

def get_building_analyzer() -> BuildingAnalyzer:
    """Get or create building analyzer singleton."""
    global _building_analyzer
    if _building_analyzer is None:
        _building_analyzer = BuildingAnalyzer()
    return _building_analyzer
