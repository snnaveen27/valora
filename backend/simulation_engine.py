"""
Simulation Engine - What-If Scenario Planning
Enables testing of urban scenarios with LLM-reasoned impact analysis

Phase 2.3: Enhanced with Causal Graphs for realistic impact modeling
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
import json
import math


# =============================================================================
# CAUSAL GRAPH MODEL (Phase 2.3)
# =============================================================================

@dataclass
class CausalEffect:
    """Represents a cause-effect relationship"""
    target: str  # What is affected
    base_impact: float  # Base impact value (-100 to +100)
    decay_radius_m: float  # Distance at which impact halves
    delay_months: int = 0  # Time delay before effect manifests
    confidence: float = 0.8  # Confidence in this effect


class CausalGraph:
    """
    Models cause-effect relationships in urban infrastructure.
    
    Each infrastructure type has defined effects on various factors,
    with distance decay and optional time delays.
    """
    
    # Causal relationships: infrastructure_type -> list of effects
    CAUSAL_MODELS: Dict[str, List[CausalEffect]] = {
        'metro_station': [
            CausalEffect('property_value', +25.0, 1000, delay_months=6),
            CausalEffect('foot_traffic', +50.0, 500, delay_months=0),
            CausalEffect('travel_time', -30.0, 2000, delay_months=0),
            CausalEffect('noise', +15.0, 200, delay_months=0),
            CausalEffect('commercial_activity', +35.0, 500, delay_months=12),
            CausalEffect('residential_demand', +20.0, 1000, delay_months=6),
            CausalEffect('walkability', +25.0, 800, delay_months=0),
            CausalEffect('parking_demand', -20.0, 500, delay_months=3),
        ],
        'highway': [
            CausalEffect('property_value', +12.0, 2000, delay_months=12),
            CausalEffect('connectivity', +40.0, 5000, delay_months=0),
            CausalEffect('noise', +40.0, 300, delay_months=0),
            CausalEffect('air_quality', -25.0, 500, delay_months=0),
            CausalEffect('residential_appeal', -15.0, 400, delay_months=0),
            CausalEffect('commercial_logistics', +50.0, 3000, delay_months=6),
            CausalEffect('walkability', -30.0, 500, delay_months=0),
            CausalEffect('travel_time', -35.0, 10000, delay_months=0),
        ],
        'it_park': [
            CausalEffect('property_value', +30.0, 2000, delay_months=18),
            CausalEffect('employment', +60.0, 3000, delay_months=6),
            CausalEffect('rental_demand', +40.0, 2000, delay_months=12),
            CausalEffect('commercial_activity', +35.0, 1500, delay_months=12),
            CausalEffect('traffic', +30.0, 2000, delay_months=6),
            CausalEffect('restaurant_demand', +45.0, 1000, delay_months=6),
            CausalEffect('public_transport_demand', +25.0, 2000, delay_months=12),
        ],
        'mall': [
            CausalEffect('property_value', +20.0, 1500, delay_months=12),
            CausalEffect('commercial_activity', +60.0, 1000, delay_months=3),
            CausalEffect('foot_traffic', +70.0, 500, delay_months=0),
            CausalEffect('traffic', +45.0, 1500, delay_months=3),
            CausalEffect('noise', +20.0, 300, delay_months=0),
            CausalEffect('retail_competition', +30.0, 2000, delay_months=6),
            CausalEffect('entertainment_options', +50.0, 2000, delay_months=0),
        ],
        'hospital': [
            CausalEffect('property_value', +15.0, 1000, delay_months=12),
            CausalEffect('healthcare_access', +80.0, 5000, delay_months=0),
            CausalEffect('traffic', +25.0, 500, delay_months=0),
            CausalEffect('pharmacy_demand', +60.0, 1000, delay_months=3),
            CausalEffect('residential_appeal', +20.0, 1500, delay_months=6),
            CausalEffect('emergency_response', +40.0, 3000, delay_months=0),
        ],
        'school': [
            CausalEffect('property_value', +18.0, 1500, delay_months=12),
            CausalEffect('family_appeal', +50.0, 2000, delay_months=6),
            CausalEffect('traffic', +20.0, 500, delay_months=0),  # School rush hours
            CausalEffect('residential_demand', +25.0, 1500, delay_months=12),
            CausalEffect('tutoring_demand', +30.0, 1000, delay_months=6),
        ],
        'park': [
            CausalEffect('property_value', +12.0, 500, delay_months=6),
            CausalEffect('air_quality', +15.0, 1000, delay_months=0),
            CausalEffect('walkability', +20.0, 800, delay_months=0),
            CausalEffect('residential_appeal', +25.0, 500, delay_months=0),
            CausalEffect('noise', -10.0, 300, delay_months=0),
            CausalEffect('mental_health', +20.0, 1000, delay_months=0),
        ],
    }
    
    @classmethod
    def get_effects(cls, infrastructure_type: str) -> List[CausalEffect]:
        """Get causal effects for an infrastructure type."""
        return cls.CAUSAL_MODELS.get(infrastructure_type, [])
    
    @classmethod
    def calculate_impact_at_distance(cls, effect: CausalEffect, distance_m: float) -> float:
        """Calculate impact with distance decay (exponential)."""
        if distance_m <= 0:
            return effect.base_impact
        
        # Exponential decay: impact = base * e^(-distance / decay_radius)
        decay_factor = math.exp(-distance_m / effect.decay_radius_m)
        return effect.base_impact * decay_factor
    
    @classmethod
    def simulate_infrastructure(cls, infrastructure_type: str, 
                               target_distance_m: float = 0,
                               time_horizon_months: int = 12) -> Dict[str, Dict]:
        """
        Simulate all effects of adding infrastructure.
        
        Args:
            infrastructure_type: Type of infrastructure
            target_distance_m: Distance from infrastructure to target property
            time_horizon_months: Time horizon for considering delayed effects
            
        Returns:
            Dictionary of effects with their computed impacts
        """
        effects = cls.get_effects(infrastructure_type)
        results = {}
        
        for effect in effects:
            # Check if effect has manifested within time horizon
            if effect.delay_months > time_horizon_months:
                impact = 0.0
                status = 'pending'
            else:
                impact = cls.calculate_impact_at_distance(effect, target_distance_m)
                status = 'active'
            
            results[effect.target] = {
                'impact': round(impact, 2),
                'base_impact': effect.base_impact,
                'distance_decay': round(impact / effect.base_impact * 100, 1) if effect.base_impact != 0 else 0,
                'delay_months': effect.delay_months,
                'status': status,
                'confidence': effect.confidence
            }
        
        return results
    
    @classmethod
    def get_aggregate_property_impact(cls, infrastructure_type: str, 
                                      distance_m: float,
                                      time_horizon_months: int = 24) -> Tuple[float, str]:
        """
        Calculate aggregate property value impact with reasoning.
        """
        effects = cls.simulate_infrastructure(
            infrastructure_type, distance_m, time_horizon_months
        )
        
        # Direct property value effect
        property_effect = effects.get('property_value', {}).get('impact', 0)
        
        # Indirect effects that influence property value
        indirect_factors = {
            'walkability': 0.3,  # 30% weight
            'commercial_activity': 0.2,
            'residential_appeal': 0.25,
            'residential_demand': 0.25,
            'noise': -0.15,  # Negative weight
            'air_quality': 0.1,
        }
        
        indirect_impact = 0
        for factor, weight in indirect_factors.items():
            if factor in effects:
                indirect_impact += effects[factor]['impact'] * weight
        
        total_impact = property_effect + indirect_impact * 0.5  # Indirect effects are 50% as strong
        
        # Generate reasoning
        positive_factors = [f for f, e in effects.items() if e['impact'] > 5]
        negative_factors = [f for f, e in effects.items() if e['impact'] < -5]
        
        reasoning = f"Adding {infrastructure_type.replace('_', ' ')} at {distance_m:.0f}m distance: "
        if positive_factors:
            reasoning += f"Positive effects on {', '.join(positive_factors[:3])}. "
        if negative_factors:
            reasoning += f"Negative effects on {', '.join(negative_factors[:2])}. "
        reasoning += f"Net property value impact: {total_impact:+.1f}%"
        
        return round(total_impact, 1), reasoning


@dataclass
class ScenarioInput:
    """Input for a what-if scenario"""
    type: str  # 'metro_station', 'highway', 'zoning_change', 'infrastructure'
    location: Dict[str, float]  # {lat, lng}
    parameters: Dict  # Scenario-specific parameters
    description: str

@dataclass
class ScenarioDeltas:
    """Computed changes from scenario"""
    accessibility_change: float  # -100 to +100
    amenity_density_change: float  # -100 to +100
    development_pressure: float  # 0 to 100
    property_value_impact: float  # Percentage change
    traffic_impact: float  # -100 to +100
    walkability_change: float  # -100 to +100
    reasoning: str  # LLM-generated explanation
    confidence: float  # 0 to 1
    causal_effects: Optional[Dict[str, Dict]] = None  # Phase 2.3: Detailed causal effects

class SimulationEngine:
    """What-If scenario engine with grounded impact analysis"""
    
    def __init__(self):
        self.scenario_handlers = {
            'metro_station': self._simulate_metro_station,
            'highway': self._simulate_highway,
            'zoning_change': self._simulate_zoning_change,
            'infrastructure': self._simulate_infrastructure
        }
    
    def simulate(self, scenario: ScenarioInput, context: Dict) -> ScenarioDeltas:
        """
        Simulate a what-if scenario and compute deltas
        
        Args:
            scenario: The scenario to simulate
            context: Current area context (from spatial analysis)
            
        Returns:
            ScenarioDeltas with computed impacts
        """
        handler = self.scenario_handlers.get(scenario.type)
        if not handler:
            raise ValueError(f"Unknown scenario type: {scenario.type}")
        
        return handler(scenario, context)
    
    def _simulate_metro_station(self, scenario: ScenarioInput, context: Dict) -> ScenarioDeltas:
        """Simulate adding a metro station using CausalGraph"""
        # Use CausalGraph for realistic impact modeling
        distance_m = scenario.parameters.get('distance_m', 500)  # Default 500m from target
        time_horizon = scenario.parameters.get('time_horizon_months', 24)
        
        effects = CausalGraph.simulate_infrastructure('metro_station', distance_m, time_horizon)
        property_impact, causal_reasoning = CausalGraph.get_aggregate_property_impact(
            'metro_station', distance_m, time_horizon
        )
        
        # Extract effects from causal model
        accessibility_change = abs(effects.get('travel_time', {}).get('impact', 0))  # Reduced travel = better access
        amenity_density_change = effects.get('commercial_activity', {}).get('impact', 0) * 0.5
        walkability_change = effects.get('walkability', {}).get('impact', 0)
        traffic_impact = -effects.get('foot_traffic', {}).get('impact', 0) * 0.4  # More foot = less car
        
        # Development pressure based on property value impact
        development_pressure = min(95, 50 + property_impact * 1.5)
        
        # Adjust based on current context
        current_transit = context.get('transport', {}).get('metro_count', 0)
        if current_transit > 2:
            accessibility_change *= 0.6
            property_impact *= 0.5
            development_pressure *= 0.7
        
        # Build comprehensive reasoning
        reasoning = causal_reasoning + " "
        reasoning += self._generate_metro_reasoning(
            scenario, context, accessibility_change, property_impact
        )
        
        return ScenarioDeltas(
            accessibility_change=round(accessibility_change, 1),
            amenity_density_change=round(amenity_density_change, 1),
            development_pressure=round(development_pressure, 1),
            property_value_impact=round(property_impact, 1),
            traffic_impact=round(traffic_impact, 1),
            walkability_change=round(walkability_change, 1),
            reasoning=reasoning,
            confidence=0.85,
            causal_effects=effects  # Include detailed causal effects
        )
    
    def _simulate_highway(self, scenario: ScenarioInput, context: Dict) -> ScenarioDeltas:
        """Simulate adding a highway using CausalGraph"""
        distance_m = scenario.parameters.get('distance_m', 300)
        time_horizon = scenario.parameters.get('time_horizon_months', 24)
        
        effects = CausalGraph.simulate_infrastructure('highway', distance_m, time_horizon)
        property_impact, causal_reasoning = CausalGraph.get_aggregate_property_impact(
            'highway', distance_m, time_horizon
        )
        
        # Extract from causal model
        accessibility_change = effects.get('connectivity', {}).get('impact', 0)
        amenity_density_change = effects.get('air_quality', {}).get('impact', 0) * 0.5
        walkability_change = effects.get('walkability', {}).get('impact', 0)
        traffic_impact = effects.get('travel_time', {}).get('impact', 0) * -1  # Positive = capacity
        
        development_pressure = min(80, 40 + property_impact * 1.2)
        
        reasoning = causal_reasoning + " "
        reasoning += self._generate_highway_reasoning(
            scenario, context, accessibility_change, property_impact
        )
        
        return ScenarioDeltas(
            accessibility_change=round(accessibility_change, 1),
            amenity_density_change=round(amenity_density_change, 1),
            development_pressure=round(development_pressure, 1),
            property_value_impact=round(property_impact, 1),
            traffic_impact=round(traffic_impact, 1),
            walkability_change=round(walkability_change, 1),
            reasoning=reasoning,
            confidence=0.75,
            causal_effects=effects
        )
    
    def _simulate_zoning_change(self, scenario: ScenarioInput, context: Dict) -> ScenarioDeltas:
        """Simulate zoning regulation change"""
        # Extract zoning parameters
        far_increase = scenario.parameters.get('far_increase', 0)  # Floor Area Ratio
        
        accessibility_change = 0.0  # No direct impact
        amenity_density_change = 5.0 * far_increase  # More density = more amenities
        development_pressure = 50.0 + (far_increase * 10)
        property_value_impact = 10.0 + (far_increase * 5)
        traffic_impact = 15.0 * far_increase  # More density = more traffic
        walkability_change = 10.0 * far_increase  # More density = better walkability
        
        reasoning = f"Increasing FAR by {far_increase} allows {far_increase * 100}% more floor area, " \
                   f"leading to denser development and {property_value_impact}% property value increase."
        
        return ScenarioDeltas(
            accessibility_change=round(accessibility_change, 1),
            amenity_density_change=round(amenity_density_change, 1),
            development_pressure=round(development_pressure, 1),
            property_value_impact=round(property_value_impact, 1),
            traffic_impact=round(traffic_impact, 1),
            walkability_change=round(walkability_change, 1),
            reasoning=reasoning,
            confidence=0.70
        )
    
    def _simulate_infrastructure(self, scenario: ScenarioInput, context: Dict) -> ScenarioDeltas:
        """Simulate general infrastructure addition"""
        infra_type = scenario.parameters.get('infrastructure_type', 'general')
        
        # Default moderate impacts
        accessibility_change = 20.0
        amenity_density_change = 25.0
        development_pressure = 50.0
        property_value_impact = 15.0
        traffic_impact = 10.0
        walkability_change = 15.0
        
        reasoning = f"Adding {infra_type} infrastructure improves area amenities and accessibility, " \
                   f"with estimated {property_value_impact}% property value increase."
        
        return ScenarioDeltas(
            accessibility_change=round(accessibility_change, 1),
            amenity_density_change=round(amenity_density_change, 1),
            development_pressure=round(development_pressure, 1),
            property_value_impact=round(property_value_impact, 1),
            traffic_impact=round(traffic_impact, 1),
            walkability_change=round(walkability_change, 1),
            reasoning=reasoning,
            confidence=0.65
        )
    
    def _generate_metro_reasoning(self, scenario: ScenarioInput, context: Dict, 
                                  accessibility: float, value_impact: float) -> str:
        """Generate LLM-style reasoning for metro station scenario"""
        current_transit = context.get('transport', {}).get('metro_count', 0)
        
        reasoning = f"Adding a metro station at this location would provide significant transit connectivity. "
        
        if current_transit == 0:
            reasoning += f"This area currently has no metro access, so the impact would be transformative. "
        elif current_transit < 2:
            reasoning += f"With {current_transit} existing metro station(s) nearby, this adds valuable redundancy. "
        else:
            reasoning += f"The area already has {current_transit} metro stations, so marginal impact is lower. "
        
        reasoning += f"Expected accessibility improvement: +{accessibility}%. "
        reasoning += f"Property values likely to increase by ~{value_impact}% within 1km radius. "
        reasoning += f"Development pressure will rise significantly, attracting mixed-use projects."
        
        return reasoning
    
    def _generate_highway_reasoning(self, scenario: ScenarioInput, context: Dict,
                                    accessibility: float, value_impact: float) -> str:
        """Generate LLM-style reasoning for highway scenario"""
        reasoning = f"A new highway connection improves vehicular accessibility by +{accessibility}%, "
        reasoning += f"but may reduce walkability due to noise and barriers. "
        reasoning += f"Property values near highway exits typically see +{value_impact}% increase, "
        reasoning += f"while properties directly adjacent may see mixed impacts. "
        reasoning += f"Commercial development (warehouses, logistics) likely to increase."
        
        return reasoning

# Singleton instance
_simulation_engine = None

def get_simulation_engine() -> SimulationEngine:
    """Get or create simulation engine singleton"""
    global _simulation_engine
    if _simulation_engine is None:
        _simulation_engine = SimulationEngine()
    return _simulation_engine
