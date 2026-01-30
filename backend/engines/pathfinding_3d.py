"""
Valora AI - 3D Pathfinding Engine
A* algorithm for walking route calculation with building obstacles.

Features:
- Grid-based pathfinding avoiding buildings
- Elevation-aware routing (penalizes steep slopes)
- Walking distance and time estimation
- Route waypoints for visualization
- Multi-destination routing
"""

import math
import heapq
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field


@dataclass
class PathNode:
    """A node in the pathfinding grid."""
    lat: float
    lng: float
    elevation: float = 0.0
    walkable: bool = True
    g_cost: float = float('inf')  # Cost from start
    h_cost: float = 0.0  # Heuristic cost to end
    parent: Optional['PathNode'] = None
    
    @property
    def f_cost(self) -> float:
        """Total cost (g + h)."""
        return self.g_cost + self.h_cost
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost
    
    def __hash__(self):
        return hash((round(self.lat, 6), round(self.lng, 6)))
    
    def __eq__(self, other):
        if not isinstance(other, PathNode):
            return False
        return (round(self.lat, 6), round(self.lng, 6)) == (round(other.lat, 6), round(other.lng, 6))


@dataclass
class PathResult:
    """Result of pathfinding calculation."""
    found: bool
    start: Tuple[float, float]
    end: Tuple[float, float]
    distance_m: float = 0.0
    walking_time_min: float = 0.0
    elevation_gain_m: float = 0.0
    elevation_loss_m: float = 0.0
    waypoints: List[Tuple[float, float, float]] = field(default_factory=list)  # (lat, lng, elevation)
    buildings_avoided: int = 0
    difficulty: str = "easy"  # easy, moderate, challenging
    route_description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "found": self.found,
            "start": {"lat": self.start[0], "lng": self.start[1]},
            "end": {"lat": self.end[0], "lng": self.end[1]},
            "distance_m": round(self.distance_m, 1),
            "walking_time_min": round(self.walking_time_min, 1),
            "elevation_gain_m": round(self.elevation_gain_m, 1),
            "elevation_loss_m": round(self.elevation_loss_m, 1),
            "waypoints": [{"lat": w[0], "lng": w[1], "elevation": w[2]} for w in self.waypoints],
            "buildings_avoided": self.buildings_avoided,
            "difficulty": self.difficulty,
            "description": self.route_description
        }


class Pathfinding3D:
    """
    A* pathfinding engine for urban environments.
    Calculates walking routes avoiding buildings and considering elevation.
    """
    
    # Grid resolution (meters per cell)
    GRID_RESOLUTION_M = 10
    
    # Walking speed (m/s) - average pedestrian
    WALKING_SPEED_MS = 1.4
    
    # Slope penalty factors
    SLOPE_PENALTIES = {
        (0, 5): 1.0,      # Flat - no penalty
        (5, 10): 1.2,     # Gentle slope - 20% slower
        (10, 15): 1.5,    # Moderate slope - 50% slower
        (15, 25): 2.0,    # Steep - 100% slower
        (25, 100): 3.0    # Very steep - 200% slower
    }
    
    # Directions for 8-connected grid (dx, dy in grid cells)
    DIRECTIONS = [
        (0, 1), (1, 0), (0, -1), (-1, 0),  # Cardinal
        (1, 1), (1, -1), (-1, 1), (-1, -1)  # Diagonal
    ]
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in meters using Haversine formula."""
        R = 6371000  # Earth radius in meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _meters_to_degrees(self, meters: float, lat: float) -> Tuple[float, float]:
        """Convert meters to approximate degrees at given latitude."""
        lat_deg = meters / 111000  # ~111km per degree latitude
        lng_deg = meters / (111000 * math.cos(math.radians(lat)))  # Adjust for latitude
        return lat_deg, lng_deg
    
    def _get_building_obstacles(self, min_lat: float, max_lat: float, 
                                 min_lng: float, max_lng: float) -> Set[Tuple[int, int]]:
        """Get grid cells occupied by buildings."""
        obstacles = set()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query buildings in the bounding box
            cursor.execute("""
                SELECT latitude, longitude, height
                FROM buildings
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                AND height > 0
            """, (min_lat, max_lat, min_lng, max_lng))
            
            # Convert to grid cells
            lat_range = max_lat - min_lat
            lng_range = max_lng - min_lng
            
            for row in cursor.fetchall():
                lat, lng, height = row
                # Convert to grid indices
                grid_y = int((lat - min_lat) / lat_range * 100)
                grid_x = int((lng - min_lng) / lng_range * 100)
                
                # Add building footprint (approximate as 2x2 cells for small buildings)
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        obstacles.add((grid_x + dx, grid_y + dy))
            
            conn.close()
            
        except Exception as e:
            print(f"[Pathfinding] Error getting obstacles: {e}")
        
        return obstacles
    
    def _get_elevation(self, lat: float, lng: float) -> float:
        """Get elevation at a point from terrain grid."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT elevation_m
                FROM terrain_grid
                WHERE center_lat BETWEEN ? AND ?
                AND center_lng BETWEEN ? AND ?
                ORDER BY ABS(center_lat - ?) + ABS(center_lng - ?)
                LIMIT 1
            """, (lat - 0.01, lat + 0.01, lng - 0.01, lng + 0.01, lat, lng))
            
            row = cursor.fetchone()
            conn.close()
            
            return row[0] if row else 920.0  # Default Bangalore elevation
            
        except Exception:
            return 920.0
    
    def _get_slope_penalty(self, elevation_diff: float, distance: float) -> float:
        """Calculate movement penalty based on slope."""
        if distance == 0:
            return 1.0
        
        slope_percent = abs(elevation_diff / distance) * 100
        
        for (min_slope, max_slope), penalty in self.SLOPE_PENALTIES.items():
            if min_slope <= slope_percent < max_slope:
                return penalty
        
        return 3.0  # Very steep default
    
    def _heuristic(self, node: PathNode, goal: PathNode) -> float:
        """Heuristic function for A* (Euclidean distance)."""
        return self._haversine_distance(node.lat, node.lng, goal.lat, goal.lng)
    
    def find_path(self, start_lat: float, start_lng: float,
                  end_lat: float, end_lng: float,
                  avoid_buildings: bool = True) -> PathResult:
        """
        Find walking path between two points using A* algorithm.
        
        Args:
            start_lat, start_lng: Starting coordinates
            end_lat, end_lng: Destination coordinates
            avoid_buildings: Whether to route around buildings
            
        Returns:
            PathResult with route details
        """
        result = PathResult(
            found=False,
            start=(start_lat, start_lng),
            end=(end_lat, end_lng)
        )
        
        # Calculate bounding box with padding
        padding = 0.005  # ~500m padding
        min_lat = min(start_lat, end_lat) - padding
        max_lat = max(start_lat, end_lat) + padding
        min_lng = min(start_lng, end_lng) - padding
        max_lng = max(start_lng, end_lng) + padding
        
        # Get building obstacles
        obstacles = set()
        if avoid_buildings:
            obstacles = self._get_building_obstacles(min_lat, max_lat, min_lng, max_lng)
            result.buildings_avoided = len(obstacles) // 9  # Approximate building count
        
        # Create start and goal nodes
        start_elev = self._get_elevation(start_lat, start_lng)
        end_elev = self._get_elevation(end_lat, end_lng)
        
        start_node = PathNode(lat=start_lat, lng=start_lng, elevation=start_elev)
        goal_node = PathNode(lat=end_lat, lng=end_lng, elevation=end_elev)
        
        start_node.g_cost = 0
        start_node.h_cost = self._heuristic(start_node, goal_node)
        
        # A* algorithm
        open_set = [start_node]
        closed_set: Set[PathNode] = set()
        node_map: Dict[Tuple[float, float], PathNode] = {(start_lat, start_lng): start_node}
        
        # Grid step size
        lat_step, lng_step = self._meters_to_degrees(self.GRID_RESOLUTION_M, start_lat)
        
        iterations = 0
        max_iterations = 10000
        
        while open_set and iterations < max_iterations:
            iterations += 1
            
            # Get node with lowest f_cost
            current = heapq.heappop(open_set)
            
            # Check if we reached the goal (within tolerance)
            if self._haversine_distance(current.lat, current.lng, goal_node.lat, goal_node.lng) < self.GRID_RESOLUTION_M:
                # Reconstruct path
                path = []
                node = current
                total_gain = 0
                total_loss = 0
                
                while node:
                    path.append((node.lat, node.lng, node.elevation))
                    if node.parent:
                        elev_diff = node.elevation - node.parent.elevation
                        if elev_diff > 0:
                            total_gain += elev_diff
                        else:
                            total_loss += abs(elev_diff)
                    node = node.parent
                
                path.reverse()
                
                # Calculate total distance
                total_distance = 0
                for i in range(1, len(path)):
                    total_distance += self._haversine_distance(
                        path[i-1][0], path[i-1][1],
                        path[i][0], path[i][1]
                    )
                
                # Simplify path (keep every 5th point plus start/end)
                simplified_path = [path[0]]
                for i in range(5, len(path)-1, 5):
                    simplified_path.append(path[i])
                if len(path) > 1:
                    simplified_path.append(path[-1])
                
                result.found = True
                result.distance_m = total_distance
                result.walking_time_min = (total_distance / self.WALKING_SPEED_MS) / 60
                result.elevation_gain_m = total_gain
                result.elevation_loss_m = total_loss
                result.waypoints = simplified_path
                
                # Determine difficulty
                if total_gain + total_loss < 20:
                    result.difficulty = "easy"
                elif total_gain + total_loss < 50:
                    result.difficulty = "moderate"
                else:
                    result.difficulty = "challenging"
                
                # Generate description
                result.route_description = self._generate_route_description(result)
                
                return result
            
            closed_set.add(current)
            
            # Explore neighbors
            for dx, dy in self.DIRECTIONS:
                neighbor_lat = current.lat + dy * lat_step
                neighbor_lng = current.lng + dx * lng_step
                
                # Check bounds
                if not (min_lat <= neighbor_lat <= max_lat and min_lng <= neighbor_lng <= max_lng):
                    continue
                
                # Check for obstacle
                grid_y = int((neighbor_lat - min_lat) / (max_lat - min_lat) * 100)
                grid_x = int((neighbor_lng - min_lng) / (max_lng - min_lng) * 100)
                
                if (grid_x, grid_y) in obstacles:
                    continue
                
                # Get or create neighbor node
                neighbor_key = (round(neighbor_lat, 6), round(neighbor_lng, 6))
                if neighbor_key in node_map:
                    neighbor = node_map[neighbor_key]
                else:
                    neighbor_elev = self._get_elevation(neighbor_lat, neighbor_lng)
                    neighbor = PathNode(lat=neighbor_lat, lng=neighbor_lng, elevation=neighbor_elev)
                    node_map[neighbor_key] = neighbor
                
                if neighbor in closed_set:
                    continue
                
                # Calculate movement cost
                base_distance = self._haversine_distance(current.lat, current.lng, neighbor_lat, neighbor_lng)
                elev_diff = neighbor.elevation - current.elevation
                slope_penalty = self._get_slope_penalty(elev_diff, base_distance)
                
                tentative_g = current.g_cost + base_distance * slope_penalty
                
                if tentative_g < neighbor.g_cost:
                    neighbor.parent = current
                    neighbor.g_cost = tentative_g
                    neighbor.h_cost = self._heuristic(neighbor, goal_node)
                    
                    if neighbor not in open_set:
                        heapq.heappush(open_set, neighbor)
        
        # No path found - return straight line distance
        straight_distance = self._haversine_distance(start_lat, start_lng, end_lat, end_lng)
        result.distance_m = straight_distance
        result.walking_time_min = (straight_distance / self.WALKING_SPEED_MS) / 60
        result.waypoints = [(start_lat, start_lng, start_elev), (end_lat, end_lng, end_elev)]
        result.route_description = "Direct route (pathfinding limit reached)"
        
        return result
    
    def _generate_route_description(self, result: PathResult) -> str:
        """Generate human-readable route description."""
        parts = []
        
        # Distance
        if result.distance_m < 1000:
            parts.append(f"{result.distance_m:.0f}m walk")
        else:
            parts.append(f"{result.distance_m/1000:.1f}km walk")
        
        # Time
        parts.append(f"~{result.walking_time_min:.0f} minutes")
        
        # Elevation
        if result.elevation_gain_m > 10:
            parts.append(f"{result.elevation_gain_m:.0f}m elevation gain")
        
        # Difficulty
        if result.difficulty != "easy":
            parts.append(f"({result.difficulty} terrain)")
        
        # Buildings avoided
        if result.buildings_avoided > 0:
            parts.append(f"avoiding {result.buildings_avoided} buildings")
        
        return ", ".join(parts)
    
    def find_path_to_nearest(self, start_lat: float, start_lng: float,
                             poi_type: str, max_distance_m: float = 2000) -> PathResult:
        """
        Find walking path to nearest POI of given type.
        
        Args:
            start_lat, start_lng: Starting coordinates
            poi_type: Type of POI to find (metro, school, hospital, etc.)
            max_distance_m: Maximum search radius
            
        Returns:
            PathResult to nearest POI
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find nearest POI
            lat_range = max_distance_m / 111000
            lng_range = max_distance_m / (111000 * math.cos(math.radians(start_lat)))
            
            cursor.execute("""
                SELECT name, lat, lng, category
                FROM pois
                WHERE lat BETWEEN ? AND ?
                AND lng BETWEEN ? AND ?
                AND (category LIKE ? OR subcategory LIKE ? OR name LIKE ?)
                LIMIT 10
            """, (
                start_lat - lat_range, start_lat + lat_range,
                start_lng - lng_range, start_lng + lng_range,
                f"%{poi_type}%", f"%{poi_type}%", f"%{poi_type}%"
            ))
            
            pois = cursor.fetchall()
            conn.close()
            
            if not pois:
                return PathResult(
                    found=False,
                    start=(start_lat, start_lng),
                    end=(start_lat, start_lng),
                    route_description=f"No {poi_type} found within {max_distance_m}m"
                )
            
            # Find nearest
            nearest = min(pois, key=lambda p: self._haversine_distance(start_lat, start_lng, p[1], p[2]))
            
            # Find path
            result = self.find_path(start_lat, start_lng, nearest[1], nearest[2])
            result.route_description = f"Route to {nearest[0] or poi_type}: " + result.route_description
            
            return result
            
        except Exception as e:
            return PathResult(
                found=False,
                start=(start_lat, start_lng),
                end=(start_lat, start_lng),
                route_description=f"Error finding path: {str(e)}"
            )


# Singleton instance
_pathfinding_instance = None

def get_pathfinding_service(db_path: str = None) -> Pathfinding3D:
    """Get or create pathfinding service instance."""
    global _pathfinding_instance
    if _pathfinding_instance is None:
        _pathfinding_instance = Pathfinding3D(db_path)
    return _pathfinding_instance
