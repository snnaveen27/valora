"""
Simulation Engine - What-If Scenario Planning
Enables testing of urban scenarios with LLM-reasoned impact analysis
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json

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
        """Simulate adding a metro station"""
        # Base impacts from adding metro station
        accessibility_change = 40.0  # Significant improvement
        amenity_density_change = 15.0  # Moderate increase
        development_pressure = 75.0  # High development pressure
        property_value_impact = 25.0  # 25% increase
        traffic_impact = -20.0  # Reduced car traffic
        walkability_change = 30.0  # Improved walkability
        
        # Adjust based on current context
        current_transit = context.get('transport', {}).get('metro_count', 0)
        if current_transit > 2:
            # Already well-connected, lower impact
            accessibility_change *= 0.6
            property_value_impact *= 0.5
        
        reasoning = self._generate_metro_reasoning(
            scenario, context, accessibility_change, property_value_impact
        )
        
        return ScenarioDeltas(
            accessibility_change=round(accessibility_change, 1),
            amenity_density_change=round(amenity_density_change, 1),
            development_pressure=round(development_pressure, 1),
            property_value_impact=round(property_value_impact, 1),
            traffic_impact=round(traffic_impact, 1),
            walkability_change=round(walkability_change, 1),
            reasoning=reasoning,
            confidence=0.85
        )
    
    def _simulate_highway(self, scenario: ScenarioInput, context: Dict) -> ScenarioDeltas:
        """Simulate adding a highway"""
        accessibility_change = 30.0  # Improved car access
        amenity_density_change = -10.0  # Slight decrease (noise, pollution)
        development_pressure = 60.0  # Moderate-high development
        property_value_impact = 15.0  # Mixed impact
        traffic_impact = 50.0  # Increased traffic capacity
        walkability_change = -25.0  # Reduced walkability
        
        reasoning = self._generate_highway_reasoning(
            scenario, context, accessibility_change, property_value_impact
        )
        
        return ScenarioDeltas(
            accessibility_change=round(accessibility_change, 1),
            amenity_density_change=round(amenity_density_change, 1),
            development_pressure=round(development_pressure, 1),
            property_value_impact=round(property_value_impact, 1),
            traffic_impact=round(traffic_impact, 1),
            walkability_change=round(walkability_change, 1),
            reasoning=reasoning,
            confidence=0.75
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
