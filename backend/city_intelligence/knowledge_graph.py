"""
Urban Knowledge Graph for City Intelligence Engine
Semantic representation of city entities and relationships.

Features:
1. Entity types: localities, buildings, infrastructure, POIs
2. Relationship types: contains, connects, adjacent, serves
3. Spatial relationships: near, within, overlaps
4. Hierarchical structure: city > zone > locality > micro-area
5. Query interface for reasoning
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import math


class EntityType(Enum):
    """Types of entities in the urban knowledge graph."""
    CITY = "city"
    ZONE = "zone"                    # North, South, East, West, Central
    LOCALITY = "locality"            # Koramangala, Whitefield, etc.
    MICRO_AREA = "micro_area"        # Koramangala 4th Block
    BUILDING = "building"
    POI = "poi"
    TRANSPORT_NODE = "transport_node"  # Metro station, bus stop
    ROAD = "road"
    INFRASTRUCTURE = "infrastructure"  # Water plant, power station
    LANDMARK = "landmark"


class RelationType(Enum):
    """Types of relationships between entities."""
    # Hierarchical
    CONTAINS = "contains"            # City contains Zone
    PART_OF = "part_of"              # Locality is part of Zone
    
    # Spatial
    ADJACENT_TO = "adjacent_to"      # Koramangala adjacent to HSR
    NEAR = "near"                    # Within 1km
    CONNECTED_BY = "connected_by"    # Connected by road/metro
    
    # Functional
    SERVES = "serves"                # Metro station serves locality
    LOCATED_IN = "located_in"        # POI located in locality
    EMPLOYS = "employs"              # IT park employs people from locality
    
    # Temporal
    DEVELOPED_BEFORE = "developed_before"
    DEVELOPED_AFTER = "developed_after"


@dataclass
class Entity:
    """An entity in the knowledge graph."""
    entity_id: str
    entity_type: EntityType
    name: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.entity_id)


@dataclass
class Relationship:
    """A relationship between two entities."""
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0              # Strength of relationship
    attributes: Dict[str, Any] = field(default_factory=dict)


class UrbanKnowledgeGraph:
    """
    Knowledge graph representing Bangalore's urban structure.
    Supports semantic queries and spatial reasoning.
    """
    
    # Bangalore zone definitions
    BANGALORE_ZONES = {
        'north': {
            'name': 'North Bangalore',
            'center': (13.05, 77.59),
            'localities': ['hebbal', 'yelahanka', 'nagawara', 'hennur', 'kalyan_nagar'],
        },
        'south': {
            'name': 'South Bangalore', 
            'center': (12.90, 77.58),
            'localities': ['jayanagar', 'jp_nagar', 'banashankari', 'btm_layout', 'electronic_city'],
        },
        'east': {
            'name': 'East Bangalore',
            'center': (12.97, 77.70),
            'localities': ['whitefield', 'marathahalli', 'kr_puram', 'mahadevapura', 'varthur'],
        },
        'west': {
            'name': 'West Bangalore',
            'center': (12.97, 77.52),
            'localities': ['rajajinagar', 'malleswaram', 'vijayanagar', 'yeshwanthpur'],
        },
        'central': {
            'name': 'Central Bangalore',
            'center': (12.97, 77.60),
            'localities': ['koramangala', 'indiranagar', 'mg_road', 'brigade_road', 'cubbon_park'],
        },
        'southeast': {
            'name': 'Southeast Bangalore',
            'center': (12.92, 77.65),
            'localities': ['hsr_layout', 'sarjapur_road', 'bellandur', 'haralur'],
        },
    }
    
    # Locality adjacency map
    ADJACENCIES = {
        'koramangala': ['hsr_layout', 'indiranagar', 'btm_layout', 'ejipura'],
        'whitefield': ['marathahalli', 'varthur', 'kr_puram', 'mahadevapura'],
        'indiranagar': ['koramangala', 'domlur', 'cv_raman_nagar', 'old_airport_road'],
        'hsr_layout': ['koramangala', 'sarjapur_road', 'btm_layout', 'bellandur'],
        'sarjapur_road': ['hsr_layout', 'bellandur', 'carmelaram', 'electronic_city'],
        'electronic_city': ['sarjapur_road', 'bommanahalli', 'hebbagodi'],
        'jayanagar': ['jp_nagar', 'basavanagudi', 'btm_layout', 'banashankari'],
        'hebbal': ['yelahanka', 'nagawara', 'manyata_tech_park', 'kempapura'],
        'marathahalli': ['whitefield', 'bellandur', 'domlur', 'varthur'],
    }
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
        
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        self.entity_index: Dict[EntityType, Set[str]] = defaultdict(set)
        self.adjacency_index: Dict[str, Set[str]] = defaultdict(set)
        
        self._initialize_graph()
    
    def _initialize_graph(self):
        """Initialize the knowledge graph with base structure."""
        # Add city
        self.add_entity(Entity(
            entity_id='bangalore',
            entity_type=EntityType.CITY,
            name='Bangalore',
            lat=12.9716,
            lng=77.5946,
            attributes={'population': 12000000, 'area_sqkm': 741}
        ))
        
        # Add zones
        for zone_id, zone_data in self.BANGALORE_ZONES.items():
            self.add_entity(Entity(
                entity_id=zone_id,
                entity_type=EntityType.ZONE,
                name=zone_data['name'],
                lat=zone_data['center'][0],
                lng=zone_data['center'][1],
            ))
            
            # Zone is part of city
            self.add_relationship(Relationship(
                source_id='bangalore',
                target_id=zone_id,
                relation_type=RelationType.CONTAINS,
            ))
        
        # Add localities
        self._add_localities_from_db()
        
        # Add adjacencies
        for locality, neighbors in self.ADJACENCIES.items():
            for neighbor in neighbors:
                self.add_relationship(Relationship(
                    source_id=locality,
                    target_id=neighbor,
                    relation_type=RelationType.ADJACENT_TO,
                ))
    
    def _add_localities_from_db(self):
        """Add localities from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT place_id, name, latitude, longitude, property_count
                FROM places
                WHERE place_type = 'neighbourhood'
            """)
            
            for row in cursor.fetchall():
                locality_id = row['name'].lower().replace(' ', '_').replace('-', '_')
                
                self.add_entity(Entity(
                    entity_id=locality_id,
                    entity_type=EntityType.LOCALITY,
                    name=row['name'],
                    lat=row['latitude'],
                    lng=row['longitude'],
                    attributes={'property_count': row['property_count'] or 0}
                ))
                
                # Find which zone it belongs to
                zone = self._find_zone(row['latitude'], row['longitude'])
                if zone:
                    self.add_relationship(Relationship(
                        source_id=zone,
                        target_id=locality_id,
                        relation_type=RelationType.CONTAINS,
                    ))
            
            conn.close()
        except Exception as e:
            print(f"[KnowledgeGraph] Error loading localities: {e}")
    
    def _find_zone(self, lat: float, lng: float) -> Optional[str]:
        """Find which zone a coordinate belongs to."""
        if not lat or not lng:
            return None
        
        min_dist = float('inf')
        closest_zone = None
        
        for zone_id, zone_data in self.BANGALORE_ZONES.items():
            center = zone_data['center']
            dist = math.sqrt((lat - center[0])**2 + (lng - center[1])**2)
            if dist < min_dist:
                min_dist = dist
                closest_zone = zone_id
        
        return closest_zone
    
    def add_entity(self, entity: Entity):
        """Add an entity to the graph."""
        self.entities[entity.entity_id] = entity
        self.entity_index[entity.entity_type].add(entity.entity_id)
    
    def add_relationship(self, relationship: Relationship):
        """Add a relationship to the graph."""
        self.relationships.append(relationship)
        
        # Update adjacency index for bidirectional relationships
        if relationship.relation_type in [RelationType.ADJACENT_TO, RelationType.NEAR]:
            self.adjacency_index[relationship.source_id].add(relationship.target_id)
            self.adjacency_index[relationship.target_id].add(relationship.source_id)
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self.entities.get(entity_id)
    
    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a specific type."""
        return [self.entities[eid] for eid in self.entity_index[entity_type]]
    
    def get_relationships(self, entity_id: str, 
                         relation_type: RelationType = None,
                         direction: str = 'both') -> List[Relationship]:
        """Get relationships for an entity."""
        results = []
        
        for rel in self.relationships:
            if direction in ['both', 'outgoing'] and rel.source_id == entity_id:
                if relation_type is None or rel.relation_type == relation_type:
                    results.append(rel)
            if direction in ['both', 'incoming'] and rel.target_id == entity_id:
                if relation_type is None or rel.relation_type == relation_type:
                    results.append(rel)
        
        return results
    
    def get_adjacent(self, entity_id: str) -> List[str]:
        """Get adjacent entities."""
        return list(self.adjacency_index.get(entity_id, set()))
    
    def get_contained(self, container_id: str) -> List[Entity]:
        """Get entities contained in a container."""
        contained_ids = []
        for rel in self.relationships:
            if rel.source_id == container_id and rel.relation_type == RelationType.CONTAINS:
                contained_ids.append(rel.target_id)
        
        return [self.entities[eid] for eid in contained_ids if eid in self.entities]
    
    def get_container(self, entity_id: str) -> Optional[Entity]:
        """Get the container of an entity."""
        for rel in self.relationships:
            if rel.target_id == entity_id and rel.relation_type == RelationType.CONTAINS:
                return self.entities.get(rel.source_id)
        return None
    
    def find_path(self, from_id: str, to_id: str, 
                  max_hops: int = 5) -> Optional[List[str]]:
        """Find a path between two entities using BFS."""
        if from_id not in self.entities or to_id not in self.entities:
            return None
        
        if from_id == to_id:
            return [from_id]
        
        visited = {from_id}
        queue = [(from_id, [from_id])]
        
        while queue:
            current, path = queue.pop(0)
            
            if len(path) > max_hops:
                continue
            
            # Get all connected entities
            neighbors = self.adjacency_index.get(current, set())
            
            for neighbor in neighbors:
                if neighbor == to_id:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def query_spatial(self, lat: float, lng: float, 
                     radius_km: float = 2.0,
                     entity_types: List[EntityType] = None) -> List[Entity]:
        """Query entities within a radius of a point."""
        results = []
        radius_deg = radius_km / 111.0  # Approximate conversion
        
        for entity in self.entities.values():
            if entity.lat is None or entity.lng is None:
                continue
            
            if entity_types and entity.entity_type not in entity_types:
                continue
            
            dist = math.sqrt((entity.lat - lat)**2 + (entity.lng - lng)**2)
            if dist <= radius_deg:
                results.append(entity)
        
        return results
    
    def get_locality_context(self, locality_id: str) -> Dict[str, Any]:
        """Get rich context for a locality."""
        entity = self.get_entity(locality_id)
        if not entity:
            return {}
        
        context = {
            'name': entity.name,
            'type': entity.entity_type.value,
            'coordinates': {'lat': entity.lat, 'lng': entity.lng},
            'attributes': entity.attributes,
        }
        
        # Get zone
        container = self.get_container(locality_id)
        if container:
            context['zone'] = container.name
        
        # Get adjacent localities
        adjacent = self.get_adjacent(locality_id)
        context['adjacent_localities'] = [
            self.entities[adj].name for adj in adjacent 
            if adj in self.entities
        ]
        
        # Get relationships
        rels = self.get_relationships(locality_id)
        context['relationship_count'] = len(rels)
        
        return context
    
    def semantic_search(self, query: str) -> List[Entity]:
        """Simple semantic search for entities."""
        query_lower = query.lower()
        results = []
        
        for entity in self.entities.values():
            # Match by name
            if query_lower in entity.name.lower():
                results.append(entity)
                continue
            
            # Match by attributes
            for key, value in entity.attributes.items():
                if isinstance(value, str) and query_lower in value.lower():
                    results.append(entity)
                    break
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            'total_entities': len(self.entities),
            'total_relationships': len(self.relationships),
            'entities_by_type': {
                etype.value: len(eids) 
                for etype, eids in self.entity_index.items()
            },
            'relationships_by_type': {
                rtype.value: sum(1 for r in self.relationships if r.relation_type == rtype)
                for rtype in RelationType
            },
        }


# Singleton
_knowledge_graph = None


def get_urban_knowledge_graph() -> UrbanKnowledgeGraph:
    """Get singleton knowledge graph."""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = UrbanKnowledgeGraph()
    return _knowledge_graph
