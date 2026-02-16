"""
Digital Twin Engine - Real-time City State Management
Maintains a living digital replica of the city with real-time updates and state tracking
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
from pathlib import Path

@dataclass
class CityState:
    """Current state of the city digital twin"""
    timestamp: str
    location: Dict[str, float]  # {lat, lng}
    buildings: Dict[str, Any] = field(default_factory=dict)  # building_id -> building data
    infrastructure: Dict[str, Any] = field(default_factory=dict)  # infrastructure elements
    demographics: Dict[str, Any] = field(default_factory=dict)  # population, density
    economy: Dict[str, Any] = field(default_factory=dict)  # market data, prices
    environment: Dict[str, Any] = field(default_factory=dict)  # air quality, noise, green space
    transport: Dict[str, Any] = field(default_factory=dict)  # metro, bus, roads
    utilities: Dict[str, Any] = field(default_factory=dict)  # water, power, telecom
    
@dataclass
class StateChange:
    """A change event in the digital twin"""
    change_id: str
    timestamp: str
    change_type: str  # 'infrastructure', 'building', 'demographic', 'economic'
    entity_id: str
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    impact_radius_m: float
    affected_entities: List[str]

class DigitalTwin:
    """
    Digital Twin Engine - Maintains real-time city state
    
    A digital twin is a virtual representation that serves as the real-time digital counterpart
    of a physical object or process. For cities, it tracks:
    - Building inventory and characteristics
    - Infrastructure networks (transport, utilities)
    - Economic indicators (property values, market activity)
    - Environmental metrics (air quality, green space)
    - Demographic data (population, density)
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / 'storage'
        self.city_state = None
        self.change_history: List[StateChange] = []
        self.state_snapshots: Dict[str, CityState] = {}  # timestamp -> state
        
    def initialize_state(self, lat: float, lng: float, radius_m: float = 5000) -> CityState:
        """
        Initialize digital twin state for a city area
        
        Args:
            lat, lng: Center coordinates
            radius_m: Radius to include in twin
            
        Returns:
            Initial CityState
        """
        timestamp = datetime.now().isoformat()
        
        city_state = CityState(
            timestamp=timestamp,
            location={'lat': lat, 'lng': lng, 'radius_m': radius_m},
            buildings={},
            infrastructure={},
            demographics={},
            economy={},
            environment={},
            transport={},
            utilities={}
        )
        
        self.city_state = city_state
        self.state_snapshots[timestamp] = city_state
        
        return city_state
    
    def update_state(self, change: StateChange) -> CityState:
        """
        Apply a state change to the digital twin
        
        Args:
            change: StateChange describing the modification
            
        Returns:
            Updated CityState
        """
        if not self.city_state:
            raise ValueError("Digital twin not initialized. Call initialize_state() first.")
        
        # Record change
        self.change_history.append(change)
        
        # Apply change based on type
        if change.change_type == 'infrastructure':
            self.city_state.infrastructure[change.entity_id] = change.after_state
        elif change.change_type == 'building':
            self.city_state.buildings[change.entity_id] = change.after_state
        elif change.change_type == 'economic':
            self.city_state.economy[change.entity_id] = change.after_state
        elif change.change_type == 'demographic':
            self.city_state.demographics[change.entity_id] = change.after_state
        elif change.change_type == 'environment':
            self.city_state.environment[change.entity_id] = change.after_state
        elif change.change_type == 'transport':
            self.city_state.transport[change.entity_id] = change.after_state
        elif change.change_type == 'utilities':
            self.city_state.utilities[change.entity_id] = change.after_state
        
        # Update timestamp
        self.city_state.timestamp = change.timestamp
        
        # Create snapshot
        self.state_snapshots[change.timestamp] = self.city_state
        
        return self.city_state
    
    def get_state(self) -> Optional[CityState]:
        """Get current city state"""
        return self.city_state
    
    def get_state_at_time(self, timestamp: str) -> Optional[CityState]:
        """Get historical state at a specific timestamp"""
        return self.state_snapshots.get(timestamp)
    
    def get_change_history(self, entity_id: Optional[str] = None) -> List[StateChange]:
        """
        Get change history, optionally filtered by entity
        
        Args:
            entity_id: Optional entity ID to filter by
            
        Returns:
            List of StateChange objects
        """
        if entity_id:
            return [c for c in self.change_history if c.entity_id == entity_id]
        return self.change_history
    
    def compute_impact_zone(self, change: StateChange, current_state: CityState) -> Dict[str, Any]:
        """
        Compute the impact zone of a state change
        
        Args:
            change: The state change
            current_state: Current city state
            
        Returns:
            Impact analysis with affected entities and metrics
        """
        impact = {
            'change_id': change.change_id,
            'impact_radius_m': change.impact_radius_m,
            'affected_entities': change.affected_entities,
            'affected_count': len(change.affected_entities),
            'change_magnitude': self._compute_change_magnitude(change),
            'cascading_effects': []
        }
        
        # Analyze cascading effects based on change type
        if change.change_type == 'infrastructure':
            # Infrastructure changes affect transport, property values, accessibility
            impact['cascading_effects'].extend([
                {'type': 'transport', 'metric': 'accessibility', 'change': '+15%'},
                {'type': 'economic', 'metric': 'property_value', 'change': '+10%'},
                {'type': 'demographic', 'metric': 'foot_traffic', 'change': '+20%'}
            ])
        elif change.change_type == 'building':
            # New buildings affect density, utilities, traffic
            impact['cascading_effects'].extend([
                {'type': 'demographic', 'metric': 'density', 'change': '+5%'},
                {'type': 'utilities', 'metric': 'demand', 'change': '+8%'},
                {'type': 'transport', 'metric': 'traffic', 'change': '+3%'}
            ])
        
        return impact
    
    def _compute_change_magnitude(self, change: StateChange) -> float:
        """
        Compute the magnitude of a change (0-100)
        
        Args:
            change: StateChange to analyze
            
        Returns:
            Magnitude score
        """
        # Simple heuristic based on affected entities and radius
        base_magnitude = min(len(change.affected_entities) / 10.0 * 100, 100)
        radius_factor = min(change.impact_radius_m / 5000.0, 1.0)
        
        return base_magnitude * radius_factor
    
    def export_state(self, filepath: Optional[Path] = None) -> Dict[str, Any]:
        """
        Export current state to JSON
        
        Args:
            filepath: Optional path to save JSON file
            
        Returns:
            State as dictionary
        """
        if not self.city_state:
            return {}
        
        state_dict = asdict(self.city_state)
        
        if filepath:
            with open(filepath, 'w') as f:
                json.dump(state_dict, f, indent=2)
        
        return state_dict
    
    def load_state(self, filepath: Path) -> CityState:
        """
        Load state from JSON file
        
        Args:
            filepath: Path to JSON state file
            
        Returns:
            Loaded CityState
        """
        with open(filepath, 'r') as f:
            state_dict = json.load(f)
        
        self.city_state = CityState(**state_dict)
        return self.city_state
    
    def sync_with_real_data(self, spatial_service, property_service, terrain_service):
        """
        Sync digital twin with real data sources
        
        Args:
            spatial_service: Spatial reasoning service
            property_service: Property data service
            terrain_service: Terrain analysis service
        """
        if not self.city_state:
            raise ValueError("Digital twin not initialized")
        
        lat = self.city_state.location['lat']
        lng = self.city_state.location['lng']
        radius_m = self.city_state.location.get('radius_m', 5000)
        
        # Sync spatial data
        if spatial_service:
            spatial_summary = spatial_service.get_summary(lat, lng, radius_m=radius_m)
            # spatial_summary is a dict, not an object
            if isinstance(spatial_summary, dict):
                self.city_state.infrastructure['pois'] = spatial_summary.get('by_category', {}).get('poi', 0)
                self.city_state.transport['metro_count'] = spatial_summary.get('transport', {}).get('metro', 0)
                self.city_state.transport['bus_count'] = spatial_summary.get('transport', {}).get('bus', 0)
            else:
                # Handle if it's an object with attributes
                by_cat = getattr(spatial_summary, 'by_category', {})
                transport = getattr(spatial_summary, 'transport', {})
                self.city_state.infrastructure['pois'] = by_cat.get('poi', 0) if isinstance(by_cat, dict) else 0
                self.city_state.transport['metro_count'] = transport.get('metro', 0) if isinstance(transport, dict) else 0
                self.city_state.transport['bus_count'] = transport.get('bus', 0) if isinstance(transport, dict) else 0
        
        # Sync property data
        if property_service:
            nearby_props = property_service.get_nearby(lat, lng, radius_m=radius_m, limit=100)
            self.city_state.economy['total_properties'] = nearby_props.get('total_found', 0)
            self.city_state.economy['avg_price'] = nearby_props.get('stats', {}).get('avg_price', 0)
            self.city_state.economy['avg_price_per_sqft'] = nearby_props.get('stats', {}).get('avg_price_per_sqft', 0)
        
        # Sync terrain data
        if terrain_service:
            try:
                terrain_analysis = terrain_service.get_terrain_analysis(lat, lng)
                if terrain_analysis:
                    self.city_state.environment['elevation'] = terrain_analysis.get('elevation_mean', 0)
                    self.city_state.environment['slope'] = terrain_analysis.get('slope_mean', 0)
                    self.city_state.environment['terrain_type'] = terrain_analysis.get('terrain_classification', 'unknown')
            except Exception as e:
                # Terrain service might not have data for this location
                self.city_state.environment['elevation'] = 0
                self.city_state.environment['slope'] = 0
                self.city_state.environment['terrain_type'] = 'unknown'
        
        # Update timestamp
        self.city_state.timestamp = datetime.now().isoformat()


# Singleton instance
_digital_twin = None

def get_digital_twin(data_dir: Path = None) -> DigitalTwin:
    """Get or create digital twin singleton"""
    global _digital_twin
    if _digital_twin is None:
        _digital_twin = DigitalTwin(data_dir)
    return _digital_twin
