"""
Network Analysis Engine for Valora AI
Phase 6.1: Advanced Geospatial - Road network analysis

Features:
- Shortest path calculations
- Isochrone generation (15-min walkability zones)
- Public transport accessibility scoring
- Network centrality metrics
- Walk/drive time estimation
"""

from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
import math
import heapq
from collections import defaultdict


@dataclass
class NetworkNode:
    """A node in the transport network (intersection or POI)."""
    id: str
    lat: float
    lng: float
    node_type: str = "intersection"  # intersection, metro, bus_stop, poi
    name: str = ""


@dataclass
class NetworkEdge:
    """An edge in the transport network (road segment)."""
    from_node: str
    to_node: str
    distance_m: float
    road_type: str = "residential"  # highway, primary, secondary, residential, footway
    walk_time_min: float = 0.0
    drive_time_min: float = 0.0
    is_walkable: bool = True
    is_drivable: bool = True


@dataclass
class IschroneResult:
    """Result of isochrone calculation."""
    center_lat: float
    center_lng: float
    time_minutes: int
    mode: str  # walk, drive, transit
    boundary_points: List[Tuple[float, float]] = field(default_factory=list)
    reachable_pois: List[Dict[str, Any]] = field(default_factory=list)
    coverage_area_sqkm: float = 0.0


class NetworkAnalyzer:
    """
    Analyzes road/transport networks for accessibility metrics.
    Uses graph-based algorithms for shortest path and isochrone calculations.
    """
    
    # Walking speed in km/h (average pedestrian)
    WALK_SPEED_KMH = 5.0
    
    # Driving speeds by road type (km/h)
    DRIVE_SPEEDS = {
        'highway': 60,
        'primary': 40,
        'secondary': 30,
        'tertiary': 25,
        'residential': 20,
        'footway': 5,
        'default': 25
    }
    
    # Transit average speeds
    TRANSIT_SPEEDS = {
        'metro': 35,
        'bus': 20,
        'auto': 25
    }
    
    def __init__(self):
        self.db_service = None
        self.nodes: Dict[str, NetworkNode] = {}
        self.edges: Dict[str, List[NetworkEdge]] = defaultdict(list)  # adjacency list
        self._init_database()
    
    def _init_database(self):
        """Initialize database connection."""
        try:
            from database.db_service import DatabaseService
            from pathlib import Path
            from backend.config import config
            self.db_service = DatabaseService(str(config.DB_PATH))
        except Exception as e:
            print(f"[NetworkAnalyzer] Database init error: {e}")
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in meters between two points."""
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _build_local_network(self, center_lat: float, center_lng: float, 
                             radius_m: float = 2000) -> None:
        """
        Build a simplified road network around a center point.
        Uses POIs and transport points as nodes with estimated edges.
        """
        self.nodes.clear()
        self.edges.clear()
        
        if not self.db_service:
            return
        
        radius_deg = radius_m / 111000
        
        # Add center as a node
        center_id = "center"
        self.nodes[center_id] = NetworkNode(
            id=center_id,
            lat=center_lat,
            lng=center_lng,
            node_type="origin"
        )
        
        # Get transport nodes (metro, bus stops)
        try:
            transport_query = """
                SELECT name, type, latitude, longitude
                FROM transport
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            transports = self.db_service.execute(transport_query, (
                center_lat - radius_deg, center_lat + radius_deg,
                center_lng - radius_deg, center_lng + radius_deg
            )) or []
            
            for i, t in enumerate(transports):
                if t.get('latitude') and t.get('longitude'):
                    node_id = f"transport_{i}"
                    self.nodes[node_id] = NetworkNode(
                        id=node_id,
                        lat=t['latitude'],
                        lng=t['longitude'],
                        node_type=t.get('type', 'bus_stop'),
                        name=t.get('name', '')
                    )
        except Exception as e:
            print(f"[NetworkAnalyzer] Transport query error: {e}")
        
        # Get POI nodes
        try:
            poi_query = """
                SELECT name, category, latitude, longitude
                FROM pois
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                LIMIT 100
            """
            pois = self.db_service.execute(poi_query, (
                center_lat - radius_deg, center_lat + radius_deg,
                center_lng - radius_deg, center_lng + radius_deg
            )) or []
            
            for i, p in enumerate(pois):
                if p.get('latitude') and p.get('longitude'):
                    node_id = f"poi_{i}"
                    self.nodes[node_id] = NetworkNode(
                        id=node_id,
                        lat=p['latitude'],
                        lng=p['longitude'],
                        node_type="poi",
                        name=p.get('name', p.get('category', 'POI'))
                    )
        except Exception as e:
            print(f"[NetworkAnalyzer] POI query error: {e}")
        
        # Create edges between nearby nodes (simplified network)
        node_list = list(self.nodes.values())
        for i, node1 in enumerate(node_list):
            for node2 in node_list[i+1:]:
                dist = self._haversine_distance(node1.lat, node1.lng, node2.lat, node2.lng)
                
                # Only connect nodes within reasonable walking distance
                if dist <= 500:  # 500m max direct connection
                    walk_time = (dist / 1000) / self.WALK_SPEED_KMH * 60  # minutes
                    drive_time = (dist / 1000) / self.DRIVE_SPEEDS['residential'] * 60
                    
                    edge = NetworkEdge(
                        from_node=node1.id,
                        to_node=node2.id,
                        distance_m=dist,
                        walk_time_min=walk_time,
                        drive_time_min=drive_time
                    )
                    
                    # Add bidirectional edges
                    self.edges[node1.id].append(edge)
                    self.edges[node2.id].append(NetworkEdge(
                        from_node=node2.id,
                        to_node=node1.id,
                        distance_m=dist,
                        walk_time_min=walk_time,
                        drive_time_min=drive_time
                    ))
    
    def calculate_isochrone(self, lat: float, lng: float, 
                           time_minutes: int = 15,
                           mode: str = "walk") -> IschroneResult:
        """
        Calculate isochrone (reachable area within time limit).
        
        Args:
            lat, lng: Center point
            time_minutes: Time budget in minutes
            mode: "walk", "drive", or "transit"
            
        Returns:
            IschroneResult with boundary and reachable POIs
        """
        result = IschroneResult(
            center_lat=lat,
            center_lng=lng,
            time_minutes=time_minutes,
            mode=mode
        )
        
        # Estimate radius based on speed
        if mode == "walk":
            speed = self.WALK_SPEED_KMH
        elif mode == "drive":
            speed = self.DRIVE_SPEEDS['residential']
        else:
            speed = self.TRANSIT_SPEEDS.get('bus', 20)
        
        max_radius_m = (speed * time_minutes / 60) * 1000
        
        # Build local network
        self._build_local_network(lat, lng, max_radius_m)
        
        # Run Dijkstra from center to find reachable nodes
        reachable = self._dijkstra_all("center", time_minutes, mode)
        
        # Collect reachable POIs
        for node_id, travel_time in reachable.items():
            if node_id.startswith("poi_") or node_id.startswith("transport_"):
                node = self.nodes.get(node_id)
                if node:
                    result.reachable_pois.append({
                        "name": node.name,
                        "type": node.node_type,
                        "lat": node.lat,
                        "lng": node.lng,
                        "travel_time_min": round(travel_time, 1)
                    })
        
        # Sort by travel time
        result.reachable_pois = sorted(result.reachable_pois, key=lambda x: x['travel_time_min'])
        
        # Generate boundary points (simplified convex hull approximation)
        if reachable:
            boundary_nodes = []
            for node_id in reachable:
                node = self.nodes.get(node_id)
                if node:
                    boundary_nodes.append((node.lat, node.lng))
            
            # Simple boundary: furthest points in 8 directions
            result.boundary_points = self._compute_boundary(lat, lng, boundary_nodes)
            
            # Estimate coverage area
            result.coverage_area_sqkm = self._estimate_area(result.boundary_points)
        
        return result
    
    def _dijkstra_all(self, start_node: str, max_time: float, 
                      mode: str = "walk") -> Dict[str, float]:
        """
        Run Dijkstra's algorithm to find all reachable nodes within time limit.
        
        Args:
            start_node: Starting node ID
            max_time: Maximum travel time in minutes
            mode: Travel mode
            
        Returns:
            Dictionary of {node_id: travel_time}
        """
        distances = {start_node: 0}
        visited = set()
        pq = [(0, start_node)]  # (distance, node)
        
        while pq:
            current_dist, current_node = heapq.heappop(pq)
            
            if current_node in visited:
                continue
            visited.add(current_node)
            
            if current_dist > max_time:
                continue
            
            # Explore neighbors
            for edge in self.edges.get(current_node, []):
                if edge.to_node in visited:
                    continue
                
                # Get travel time based on mode
                if mode == "walk":
                    travel_time = edge.walk_time_min
                else:
                    travel_time = edge.drive_time_min
                
                new_dist = current_dist + travel_time
                
                if new_dist < max_time and (edge.to_node not in distances or new_dist < distances[edge.to_node]):
                    distances[edge.to_node] = new_dist
                    heapq.heappush(pq, (new_dist, edge.to_node))
        
        return distances
    
    def _compute_boundary(self, center_lat: float, center_lng: float,
                          points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Compute simplified boundary from reachable points."""
        if not points:
            return []
        
        # Find furthest points in 8 directions
        directions = {}
        for angle in range(0, 360, 45):
            directions[angle] = (center_lat, center_lng, 0)  # (lat, lng, distance)
        
        for lat, lng in points:
            dist = self._haversine_distance(center_lat, center_lng, lat, lng)
            angle = math.degrees(math.atan2(lng - center_lng, lat - center_lat))
            angle = (angle + 360) % 360
            
            # Find closest direction bucket
            bucket = round(angle / 45) * 45 % 360
            
            if dist > directions[bucket][2]:
                directions[bucket] = (lat, lng, dist)
        
        # Return boundary points
        boundary = []
        for angle in sorted(directions.keys()):
            lat, lng, dist = directions[angle]
            if dist > 0:
                boundary.append((lat, lng))
        
        return boundary
    
    def _estimate_area(self, boundary_points: List[Tuple[float, float]]) -> float:
        """Estimate area enclosed by boundary points in sq km."""
        if len(boundary_points) < 3:
            return 0.0
        
        # Shoelace formula for polygon area
        n = len(boundary_points)
        area = 0.0
        
        for i in range(n):
            j = (i + 1) % n
            # Convert to approximate meters
            lat1, lng1 = boundary_points[i]
            lat2, lng2 = boundary_points[j]
            
            x1 = lng1 * 111000 * math.cos(math.radians(lat1))
            y1 = lat1 * 111000
            x2 = lng2 * 111000 * math.cos(math.radians(lat2))
            y2 = lat2 * 111000
            
            area += x1 * y2 - x2 * y1
        
        area_sqm = abs(area) / 2
        return area_sqm / 1_000_000  # Convert to sq km
    
    def calculate_accessibility_score(self, lat: float, lng: float) -> Dict[str, Any]:
        """
        Calculate comprehensive accessibility score for a location.
        
        Returns scores for:
        - Walkability (15-min walk access)
        - Transit accessibility (metro/bus proximity)
        - Amenity access
        """
        # Calculate 15-min walk isochrone
        walk_isochrone = self.calculate_isochrone(lat, lng, time_minutes=15, mode="walk")
        
        # Calculate 10-min drive isochrone
        drive_isochrone = self.calculate_isochrone(lat, lng, time_minutes=10, mode="drive")
        
        # Count reachable amenities by type
        amenity_counts = defaultdict(int)
        for poi in walk_isochrone.reachable_pois:
            amenity_counts[poi['type']] += 1
        
        # Calculate scores (0-100)
        walkability_score = min(100, len(walk_isochrone.reachable_pois) * 2)
        
        transit_count = sum(1 for p in walk_isochrone.reachable_pois 
                           if p['type'] in ['metro', 'bus_stop', 'metro_station', 'bus_station'])
        transit_score = min(100, transit_count * 20)
        
        amenity_score = min(100, sum(amenity_counts.values()) * 3)
        
        # Overall accessibility
        overall_score = (walkability_score * 0.4 + transit_score * 0.35 + amenity_score * 0.25)
        
        return {
            "overall_score": round(overall_score, 1),
            "walkability_score": round(walkability_score, 1),
            "transit_score": round(transit_score, 1),
            "amenity_score": round(amenity_score, 1),
            "walk_15min": {
                "reachable_pois": len(walk_isochrone.reachable_pois),
                "coverage_sqkm": round(walk_isochrone.coverage_area_sqkm, 2),
                "transit_stops": transit_count
            },
            "drive_10min": {
                "reachable_pois": len(drive_isochrone.reachable_pois),
                "coverage_sqkm": round(drive_isochrone.coverage_area_sqkm, 2)
            },
            "amenity_breakdown": dict(amenity_counts),
            "rating": self._score_to_rating(overall_score)
        }
    
    def _score_to_rating(self, score: float) -> str:
        """Convert numeric score to rating."""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Moderate"
        elif score >= 20:
            return "Limited"
        else:
            return "Poor"
    
    def find_shortest_path(self, from_lat: float, from_lng: float,
                          to_lat: float, to_lng: float,
                          mode: str = "walk") -> Dict[str, Any]:
        """
        Find shortest path between two points.
        
        Args:
            from_lat, from_lng: Origin coordinates
            to_lat, to_lng: Destination coordinates
            mode: Travel mode
            
        Returns:
            Path details including distance, time, and waypoints
        """
        # Direct distance
        direct_dist = self._haversine_distance(from_lat, from_lng, to_lat, to_lng)
        
        # Estimate walking/driving factor (roads are typically 1.3-1.5x direct distance)
        road_factor = 1.4
        estimated_distance = direct_dist * road_factor
        
        # Calculate time
        if mode == "walk":
            speed = self.WALK_SPEED_KMH
        elif mode == "drive":
            speed = self.DRIVE_SPEEDS['residential']
        else:
            speed = self.TRANSIT_SPEEDS.get('bus', 20)
        
        travel_time_min = (estimated_distance / 1000) / speed * 60
        
        return {
            "from": {"lat": from_lat, "lng": from_lng},
            "to": {"lat": to_lat, "lng": to_lng},
            "mode": mode,
            "direct_distance_m": round(direct_dist),
            "estimated_distance_m": round(estimated_distance),
            "travel_time_min": round(travel_time_min, 1),
            "speed_kmh": speed,
            "waypoints": [
                {"lat": from_lat, "lng": from_lng, "type": "origin"},
                {"lat": to_lat, "lng": to_lng, "type": "destination"}
            ]
        }


# Singleton instance
_network_analyzer = None


def get_network_analyzer() -> NetworkAnalyzer:
    """Get or create network analyzer singleton."""
    global _network_analyzer
    if _network_analyzer is None:
        _network_analyzer = NetworkAnalyzer()
    return _network_analyzer
