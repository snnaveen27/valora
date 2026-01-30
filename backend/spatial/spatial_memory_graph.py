"""
Valora AI - Spatial Memory Graph
Precomputes and caches spatial relationships between buildings for fast queries.

Relationships:
- BLOCKS_VIEW: Building A blocks view from Building B in direction D
- SHADOWS: Building A casts shadow on Building B at time T
- OVERLOOKS: Building A has view of landmark L
- ADJACENT_TO: Building A is within 50m of Building B
- WITHIN_WALK: Entity A is within N minutes walk of Entity B
- IN_LOCALITY: Building A is in locality L

This enables queries like:
- "Which buildings block the lake view?"
- "Buildings behind the mall"
- "Properties overlooking the metro line"
"""

import sqlite3
import math
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class RelationType(Enum):
    """Types of spatial relationships."""
    BLOCKS_VIEW = "blocks_view"
    SHADOWS = "shadows"
    OVERLOOKS = "overlooks"
    ADJACENT_TO = "adjacent_to"
    WITHIN_WALK = "within_walk"
    IN_LOCALITY = "in_locality"
    FACES_DIRECTION = "faces_direction"
    TALLER_THAN = "taller_than"
    NEAR_LANDMARK = "near_landmark"


@dataclass
class SpatialRelation:
    """A spatial relationship between two entities."""
    relation_type: str
    source_id: str
    source_type: str  # building, poi, locality
    target_id: str
    target_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    # Properties can include: direction, distance_m, height_diff, time_range, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SpatialNode:
    """A node in the spatial graph (building, POI, locality)."""
    node_id: str
    node_type: str
    lat: float
    lng: float
    height: float = 0.0
    name: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)


class SpatialMemoryGraph:
    """
    In-memory spatial relationship graph with SQLite persistence.
    Enables fast queries for spatial relationships between entities.
    """
    
    # Distance thresholds
    ADJACENT_THRESHOLD_M = 50
    NEARBY_THRESHOLD_M = 200
    WALK_SPEED_M_PER_MIN = 80  # ~5 km/h average walk speed
    
    # Directions
    DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
        
        # In-memory graph structures
        self._nodes: Dict[str, SpatialNode] = {}
        self._relations: List[SpatialRelation] = []
        self._index_by_source: Dict[str, List[int]] = {}  # source_id -> relation indices
        self._index_by_target: Dict[str, List[int]] = {}  # target_id -> relation indices
        self._index_by_type: Dict[str, List[int]] = {}    # relation_type -> relation indices
        
        # Spatial index (grid-based)
        self._grid_size = 0.001  # ~111m cells
        self._spatial_grid: Dict[Tuple[int, int], Set[str]] = {}
        
        self._initialized = False
    
    def _get_grid_cell(self, lat: float, lng: float) -> Tuple[int, int]:
        """Get grid cell for coordinates."""
        return (int(lat / self._grid_size), int(lng / self._grid_size))
    
    def _get_nearby_cells(self, lat: float, lng: float, radius_m: float) -> List[Tuple[int, int]]:
        """Get all grid cells within radius."""
        radius_deg = radius_m / 111000
        cells_radius = int(radius_deg / self._grid_size) + 1
        center_cell = self._get_grid_cell(lat, lng)
        
        cells = []
        for di in range(-cells_radius, cells_radius + 1):
            for dj in range(-cells_radius, cells_radius + 1):
                cells.append((center_cell[0] + di, center_cell[1] + dj))
        return cells
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in meters."""
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _get_direction(self, from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> str:
        """Get cardinal direction from one point to another."""
        dlat = to_lat - from_lat
        dlng = to_lng - from_lng
        
        angle = math.degrees(math.atan2(dlng, dlat))
        if angle < 0:
            angle += 360
        
        index = round(angle / 45) % 8
        return self.DIRECTIONS[index]
    
    def _get_opposite_direction(self, direction: str) -> str:
        """Get opposite direction."""
        opposites = {
            'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E',
            'NE': 'SW', 'SW': 'NE', 'NW': 'SE', 'SE': 'NW'
        }
        return opposites.get(direction, 'N')
    
    def initialize(self, sample_size: int = 10000) -> Dict[str, int]:
        """
        Initialize graph from database.
        
        Args:
            sample_size: Maximum buildings to load (for performance)
            
        Returns:
            Statistics about loaded data
        """
        if self._initialized:
            return {'status': 'already_initialized'}
        
        stats = {'buildings': 0, 'pois': 0, 'localities': 0, 'relations': 0}
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Load buildings (sample for performance)
            cursor.execute(f"""
                SELECT osm_id, name, height, levels, building_type, latitude, longitude
                FROM buildings
                WHERE height > 0 AND latitude IS NOT NULL
                ORDER BY height DESC
                LIMIT {sample_size}
            """)
            
            for row in cursor.fetchall():
                node = SpatialNode(
                    node_id=str(row['osm_id']),
                    node_type='building',
                    lat=row['latitude'],
                    lng=row['longitude'],
                    height=row['height'] or 0,
                    name=row['name'],
                    properties={
                        'levels': row['levels'],
                        'building_type': row['building_type']
                    }
                )
                self._add_node(node)
                stats['buildings'] += 1
            
            # Load POIs (landmarks)
            cursor.execute("""
                SELECT osm_id, name, category, latitude, longitude
                FROM pois
                WHERE name IS NOT NULL AND name != ''
                AND latitude IS NOT NULL
                LIMIT 5000
            """)
            
            for row in cursor.fetchall():
                node = SpatialNode(
                    node_id=f"poi_{row['osm_id']}",
                    node_type='poi',
                    lat=row['latitude'],
                    lng=row['longitude'],
                    name=row['name'],
                    properties={'category': row['category']}
                )
                self._add_node(node)
                stats['pois'] += 1
            
            # Load localities
            cursor.execute("""
                SELECT locality_id, locality_name, center_lat, center_lng
                FROM locality_state
                WHERE center_lat IS NOT NULL
            """)
            
            for row in cursor.fetchall():
                node = SpatialNode(
                    node_id=row['locality_id'],
                    node_type='locality',
                    lat=row['center_lat'],
                    lng=row['center_lng'],
                    name=row['locality_name']
                )
                self._add_node(node)
                stats['localities'] += 1
            
            conn.close()
            
            # Build relationships
            stats['relations'] = self._build_relationships()
            
            self._initialized = True
            print(f"[SpatialGraph] Initialized: {stats}")
            
        except Exception as e:
            print(f"[SpatialGraph] Error initializing: {e}")
        
        return stats
    
    def _add_node(self, node: SpatialNode):
        """Add a node to the graph."""
        self._nodes[node.node_id] = node
        
        # Add to spatial grid
        cell = self._get_grid_cell(node.lat, node.lng)
        if cell not in self._spatial_grid:
            self._spatial_grid[cell] = set()
        self._spatial_grid[cell].add(node.node_id)
    
    def _add_relation(self, relation: SpatialRelation):
        """Add a relation to the graph."""
        idx = len(self._relations)
        self._relations.append(relation)
        
        # Index by source
        if relation.source_id not in self._index_by_source:
            self._index_by_source[relation.source_id] = []
        self._index_by_source[relation.source_id].append(idx)
        
        # Index by target
        if relation.target_id not in self._index_by_target:
            self._index_by_target[relation.target_id] = []
        self._index_by_target[relation.target_id].append(idx)
        
        # Index by type
        if relation.relation_type not in self._index_by_type:
            self._index_by_type[relation.relation_type] = []
        self._index_by_type[relation.relation_type].append(idx)
    
    def _build_relationships(self) -> int:
        """Build spatial relationships between nodes."""
        count = 0
        buildings = [n for n in self._nodes.values() if n.node_type == 'building']
        
        # For each building, find relationships
        for i, bldg in enumerate(buildings):
            if i % 1000 == 0:
                print(f"[SpatialGraph] Processing building {i}/{len(buildings)}")
            
            # Get nearby nodes
            nearby_cells = self._get_nearby_cells(bldg.lat, bldg.lng, self.NEARBY_THRESHOLD_M)
            nearby_ids = set()
            for cell in nearby_cells:
                if cell in self._spatial_grid:
                    nearby_ids.update(self._spatial_grid[cell])
            
            for other_id in nearby_ids:
                if other_id == bldg.node_id:
                    continue
                
                other = self._nodes.get(other_id)
                if not other:
                    continue
                
                distance = self._haversine_distance(bldg.lat, bldg.lng, other.lat, other.lng)
                
                # ADJACENT_TO: Within 50m
                if distance <= self.ADJACENT_THRESHOLD_M:
                    direction = self._get_direction(bldg.lat, bldg.lng, other.lat, other.lng)
                    self._add_relation(SpatialRelation(
                        relation_type=RelationType.ADJACENT_TO.value,
                        source_id=bldg.node_id,
                        source_type=bldg.node_type,
                        target_id=other_id,
                        target_type=other.node_type,
                        properties={
                            'distance_m': round(distance),
                            'direction': direction
                        }
                    ))
                    count += 1
                
                # TALLER_THAN: If other is a building and we're significantly taller
                if other.node_type == 'building' and distance <= self.NEARBY_THRESHOLD_M:
                    height_diff = bldg.height - other.height
                    if height_diff > 5:  # At least 5m taller
                        direction = self._get_direction(bldg.lat, bldg.lng, other.lat, other.lng)
                        self._add_relation(SpatialRelation(
                            relation_type=RelationType.TALLER_THAN.value,
                            source_id=bldg.node_id,
                            source_type='building',
                            target_id=other_id,
                            target_type='building',
                            properties={
                                'height_diff_m': round(height_diff, 1),
                                'distance_m': round(distance),
                                'direction': direction
                            }
                        ))
                        count += 1
                        
                        # BLOCKS_VIEW: Taller building blocks view FROM shorter building
                        # The taller building blocks the shorter building's view in that direction
                        opposite_dir = self._get_opposite_direction(direction)
                        self._add_relation(SpatialRelation(
                            relation_type=RelationType.BLOCKS_VIEW.value,
                            source_id=bldg.node_id,  # Blocker
                            source_type='building',
                            target_id=other_id,  # Blocked
                            target_type='building',
                            properties={
                                'blocked_direction': opposite_dir,
                                'blocker_height': bldg.height,
                                'blocked_height': other.height,
                                'distance_m': round(distance)
                            }
                        ))
                        count += 1
                
                # NEAR_LANDMARK: Building near a notable POI
                if other.node_type == 'poi' and distance <= 500:
                    self._add_relation(SpatialRelation(
                        relation_type=RelationType.NEAR_LANDMARK.value,
                        source_id=bldg.node_id,
                        source_type='building',
                        target_id=other_id,
                        target_type='poi',
                        properties={
                            'distance_m': round(distance),
                            'landmark_name': other.name,
                            'category': other.properties.get('category')
                        }
                    ))
                    count += 1
        
        return count
    
    def query_relations(
        self,
        relation_type: str = None,
        source_id: str = None,
        target_id: str = None,
        direction: str = None,
        max_distance_m: float = None,
        limit: int = 100
    ) -> List[SpatialRelation]:
        """
        Query relationships with filters.
        
        Args:
            relation_type: Filter by relationship type
            source_id: Filter by source entity
            target_id: Filter by target entity
            direction: Filter by direction (N, NE, E, etc.)
            max_distance_m: Filter by maximum distance
            limit: Maximum results
            
        Returns:
            List of matching relations
        """
        # Start with all relations or indexed subset
        if source_id and source_id in self._index_by_source:
            indices = self._index_by_source[source_id]
        elif target_id and target_id in self._index_by_target:
            indices = self._index_by_target[target_id]
        elif relation_type and relation_type in self._index_by_type:
            indices = self._index_by_type[relation_type]
        else:
            indices = range(len(self._relations))
        
        results = []
        for idx in indices:
            if len(results) >= limit:
                break
            
            rel = self._relations[idx]
            
            # Apply filters
            if relation_type and rel.relation_type != relation_type:
                continue
            if source_id and rel.source_id != source_id:
                continue
            if target_id and rel.target_id != target_id:
                continue
            if direction and rel.properties.get('direction') != direction:
                continue
            if max_distance_m and rel.properties.get('distance_m', 0) > max_distance_m:
                continue
            
            results.append(rel)
        
        return results
    
    def find_view_blockers(
        self,
        lat: float,
        lng: float,
        floor_height_m: float,
        direction: str = None,
        radius_m: float = 200
    ) -> List[Dict[str, Any]]:
        """
        Find buildings that block view from a location.
        
        Args:
            lat, lng: Observer location
            floor_height_m: Observer height above ground
            direction: Optional direction to check (if None, check all)
            radius_m: Search radius
            
        Returns:
            List of blocking buildings with details
        """
        blockers = []
        
        # Find buildings in radius
        nearby_cells = self._get_nearby_cells(lat, lng, radius_m)
        nearby_ids = set()
        for cell in nearby_cells:
            if cell in self._spatial_grid:
                nearby_ids.update(self._spatial_grid[cell])
        
        for node_id in nearby_ids:
            node = self._nodes.get(node_id)
            if not node or node.node_type != 'building':
                continue
            
            distance = self._haversine_distance(lat, lng, node.lat, node.lng)
            if distance > radius_m or distance < 10:  # Skip very close (same building)
                continue
            
            # Check if building is taller than observer
            if node.height > floor_height_m:
                bldg_direction = self._get_direction(lat, lng, node.lat, node.lng)
                
                if direction and bldg_direction != direction:
                    continue
                
                # Calculate blocking angle
                height_diff = node.height - floor_height_m
                blocking_angle = math.degrees(math.atan(height_diff / distance))
                
                blockers.append({
                    'building_id': node_id,
                    'name': node.name,
                    'height': node.height,
                    'distance_m': round(distance),
                    'direction': bldg_direction,
                    'height_diff': round(height_diff, 1),
                    'blocking_angle': round(blocking_angle, 1),
                    'blocking_severity': 'high' if blocking_angle > 30 else 'medium' if blocking_angle > 15 else 'low'
                })
        
        # Sort by blocking severity
        blockers.sort(key=lambda x: x['blocking_angle'], reverse=True)
        return blockers
    
    def find_buildings_behind(
        self,
        reference_lat: float,
        reference_lng: float,
        viewpoint_lat: float,
        viewpoint_lng: float,
        radius_m: float = 500
    ) -> List[Dict[str, Any]]:
        """
        Find buildings "behind" a reference point from a viewpoint.
        
        Args:
            reference_lat, reference_lng: Reference point (e.g., "the mall")
            viewpoint_lat, viewpoint_lng: Observer viewpoint
            radius_m: Search radius from reference
            
        Returns:
            List of buildings behind the reference
        """
        # Direction from viewpoint to reference
        ref_direction = self._get_direction(viewpoint_lat, viewpoint_lng, reference_lat, reference_lng)
        
        # Get buildings near reference
        nearby_cells = self._get_nearby_cells(reference_lat, reference_lng, radius_m)
        nearby_ids = set()
        for cell in nearby_cells:
            if cell in self._spatial_grid:
                nearby_ids.update(self._spatial_grid[cell])
        
        behind = []
        for node_id in nearby_ids:
            node = self._nodes.get(node_id)
            if not node or node.node_type != 'building':
                continue
            
            # Check if building is in same direction from viewpoint (i.e., "behind" reference)
            bldg_direction = self._get_direction(viewpoint_lat, viewpoint_lng, node.lat, node.lng)
            
            if bldg_direction == ref_direction:
                # Check if further from viewpoint than reference
                dist_to_ref = self._haversine_distance(viewpoint_lat, viewpoint_lng, reference_lat, reference_lng)
                dist_to_bldg = self._haversine_distance(viewpoint_lat, viewpoint_lng, node.lat, node.lng)
                
                if dist_to_bldg > dist_to_ref:
                    behind.append({
                        'building_id': node_id,
                        'name': node.name,
                        'height': node.height,
                        'distance_from_reference': round(self._haversine_distance(
                            reference_lat, reference_lng, node.lat, node.lng
                        )),
                        'direction': bldg_direction
                    })
        
        behind.sort(key=lambda x: x['distance_from_reference'])
        return behind
    
    def find_overlooks(
        self,
        lat: float,
        lng: float,
        min_height: float = 30,
        radius_m: float = 2000
    ) -> List[Dict[str, Any]]:
        """
        Find what landmarks a tall building can overlook.
        
        Args:
            lat, lng: Building location
            min_height: Minimum building height to consider
            radius_m: View radius
            
        Returns:
            List of landmarks potentially visible
        """
        # Find POIs in radius
        nearby_cells = self._get_nearby_cells(lat, lng, radius_m)
        nearby_ids = set()
        for cell in nearby_cells:
            if cell in self._spatial_grid:
                nearby_ids.update(self._spatial_grid[cell])
        
        overlooks = []
        for node_id in nearby_ids:
            node = self._nodes.get(node_id)
            if not node or node.node_type != 'poi':
                continue
            
            distance = self._haversine_distance(lat, lng, node.lat, node.lng)
            if distance > radius_m:
                continue
            
            direction = self._get_direction(lat, lng, node.lat, node.lng)
            
            overlooks.append({
                'landmark_id': node_id,
                'name': node.name,
                'category': node.properties.get('category'),
                'distance_m': round(distance),
                'direction': direction
            })
        
        overlooks.sort(key=lambda x: x['distance_m'])
        return overlooks
    
    def get_node(self, node_id: str) -> Optional[SpatialNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            'total_nodes': len(self._nodes),
            'buildings': sum(1 for n in self._nodes.values() if n.node_type == 'building'),
            'pois': sum(1 for n in self._nodes.values() if n.node_type == 'poi'),
            'localities': sum(1 for n in self._nodes.values() if n.node_type == 'locality'),
            'total_relations': len(self._relations),
            'relations_by_type': {k: len(v) for k, v in self._index_by_type.items()},
            'grid_cells': len(self._spatial_grid),
            'initialized': self._initialized
        }


# Singleton instance
_spatial_graph = None


def get_spatial_graph() -> SpatialMemoryGraph:
    """Get or create the spatial memory graph singleton."""
    global _spatial_graph
    if _spatial_graph is None:
        _spatial_graph = SpatialMemoryGraph()
    return _spatial_graph


def initialize_spatial_graph(sample_size: int = 10000) -> Dict[str, int]:
    """Initialize the spatial graph with database data."""
    graph = get_spatial_graph()
    return graph.initialize(sample_size=sample_size)
