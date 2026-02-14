"""
Narrative Generator - Cinematic Storyboard Creation
Generates 3D storyboards with camera paths, overlays, and narration
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from .simulation_engine import ScenarioDeltas

@dataclass
class StoryboardStep:
    """Single step in a cinematic storyboard"""
    title: str
    narration: str
    camera: Dict  # {lat, lng, height, heading, pitch}
    overlays: List[Dict]  # Overlay commands for OverlayEngine
    analysis_explanation: Dict  # Data for Analysis panel
    duration: int  # Duration in milliseconds
    audio_url: Optional[str] = None

@dataclass
class Storyboard:
    """Complete cinematic storyboard"""
    title: str
    description: str
    steps: List[StoryboardStep]
    total_duration: int

class NarrativeGenerator:
    """Generates cinematic storyboards for simulations and analysis"""
    
    def generate_simulation_storyboard(self, scenario_input: Dict, 
                                      scenario_deltas: ScenarioDeltas,
                                      location: Dict[str, float]) -> Storyboard:
        """
        Generate a storyboard for a simulation scenario
        
        Args:
            scenario_input: The scenario configuration
            scenario_deltas: Computed impacts from simulation
            location: {lat, lng} of scenario location
            
        Returns:
            Complete Storyboard with camera paths and overlays
        """
        steps = []
        
        # Step 1: Overview - Show current state
        steps.append(self._create_overview_step(location))
        
        # Step 2: Scenario Introduction
        steps.append(self._create_scenario_intro_step(scenario_input, location))
        
        # Step 3: Impact Analysis - Accessibility
        if abs(scenario_deltas.accessibility_change) > 10:
            steps.append(self._create_accessibility_step(scenario_deltas, location))
        
        # Step 4: Impact Analysis - Development
        if scenario_deltas.development_pressure > 50:
            steps.append(self._create_development_step(scenario_deltas, location))
        
        # Step 5: Impact Analysis - Property Values
        if abs(scenario_deltas.property_value_impact) > 5:
            steps.append(self._create_property_value_step(scenario_deltas, location))
        
        # Step 6: Summary and Conclusion
        steps.append(self._create_summary_step(scenario_deltas, location))
        
        total_duration = sum(step.duration for step in steps)
        
        return Storyboard(
            title=f"Simulation: {scenario_input.get('description', 'Urban Scenario')}",
            description=f"Impact analysis for {scenario_input.get('type', 'scenario')}",
            steps=steps,
            total_duration=total_duration
        )
    
    def _create_overview_step(self, location: Dict[str, float]) -> StoryboardStep:
        """Create overview step showing current state"""
        return StoryboardStep(
            title="Current State Overview",
            narration="Let's examine the current state of this area before the proposed changes.",
            camera={
                "lat": location['lat'],
                "lng": location['lng'],
                "height": 2000,
                "heading": 0,
                "pitch": -60,
                "duration": 3
            },
            overlays=[
                {
                    "type": "circle",
                    "data": {
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "radius": 1000
                    },
                    "style": {
                        "color": [0, 0.7, 1, 1],  # Cyan
                        "opacity": 0.2
                    }
                },
                {
                    "type": "label",
                    "data": {
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "text": "Analysis Area (1km radius)"
                    },
                    "style": {
                        "fontSize": 16
                    }
                }
            ],
            analysis_explanation={
                "title": "Current State",
                "metrics": [
                    {"label": "Analysis Radius", "value": "1 km"},
                    {"label": "Focus", "value": "Baseline conditions"}
                ]
            },
            duration=4000
        )
    
    def _create_scenario_intro_step(self, scenario: Dict, location: Dict[str, float]) -> StoryboardStep:
        """Create scenario introduction step"""
        scenario_type = scenario.get('type', 'infrastructure')
        description = scenario.get('description', 'New development')
        
        return StoryboardStep(
            title="Proposed Scenario",
            narration=f"We're proposing to add {description} at this location. Let's analyze the potential impacts.",
            camera={
                "lat": location['lat'],
                "lng": location['lng'],
                "height": 800,
                "heading": 45,
                "pitch": -45,
                "duration": 2.5
            },
            overlays=[
                {
                    "type": "marker",
                    "data": {
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "icon": "📍"
                    },
                    "style": {
                        "color": [1, 0, 0, 1],  # Red
                        "scale": 2.0
                    }
                },
                {
                    "type": "label",
                    "data": {
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "text": description
                    },
                    "style": {
                        "fontSize": 18,
                        "color": [1, 1, 0, 1]  # Yellow
                    }
                }
            ],
            analysis_explanation={
                "title": "Proposed Change",
                "metrics": [
                    {"label": "Type", "value": scenario_type},
                    {"label": "Description", "value": description}
                ]
            },
            duration=5000
        )
    
    def _create_accessibility_step(self, deltas: ScenarioDeltas, location: Dict[str, float]) -> StoryboardStep:
        """Create accessibility impact step"""
        change = deltas.accessibility_change
        direction = "improve" if change > 0 else "reduce"
        
        return StoryboardStep(
            title="Accessibility Impact",
            narration=f"This change would {direction} accessibility by {abs(change):.1f}%. "
                     f"Transit connectivity and walkability are key factors.",
            camera={
                "lat": location['lat'] + 0.005,
                "lng": location['lng'] + 0.005,
                "height": 1200,
                "heading": 90,
                "pitch": -50,
                "duration": 2.5
            },
            overlays=[
                {
                    "type": "circle",
                    "data": {
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "radius": 500
                    },
                    "style": {
                        "color": [0, 1, 0, 1] if change > 0 else [1, 0.5, 0, 1],
                        "opacity": 0.3
                    }
                },
                {
                    "type": "label",
                    "data": {
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "text": f"Accessibility: {'+' if change > 0 else ''}{change:.1f}%"
                    },
                    "style": {
                        "fontSize": 16,
                        "color": [0, 1, 0, 1] if change > 0 else [1, 0.5, 0, 1]
                    }
                }
            ],
            analysis_explanation={
                "title": "Accessibility Analysis",
                "metrics": [
                    {"label": "Change", "value": f"{'+' if change > 0 else ''}{change:.1f}%"},
                    {"label": "Walkability", "value": f"{'+' if deltas.walkability_change > 0 else ''}{deltas.walkability_change:.1f}%"},
                    {"label": "Impact", "value": "Positive" if change > 0 else "Negative"}
                ],
                "explanation": deltas.reasoning
            },
            duration=6000
        )
    
    def _create_development_step(self, deltas: ScenarioDeltas, location: Dict[str, float]) -> StoryboardStep:
        """Create development pressure step"""
        pressure = deltas.development_pressure
        
        return StoryboardStep(
            title="Development Pressure",
            narration=f"Development pressure is estimated at {pressure:.1f} out of 100. "
                     f"This indicates {'high' if pressure > 70 else 'moderate' if pressure > 40 else 'low'} "
                     f"likelihood of new construction and investment.",
            camera={
                "lat": location['lat'] - 0.005,
                "lng": location['lng'],
                "height": 1500,
                "heading": 180,
                "pitch": -55,
                "duration": 2.5
            },
            overlays=[
                {
                    "type": "circle",
                    "data": {
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "radius": 800
                    },
                    "style": {
                        "color": [1, 0.5, 0, 1],  # Orange
                        "opacity": 0.25
                    }
                },
                {
                    "type": "label",
                    "data": {
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "text": f"Development Pressure: {pressure:.1f}/100"
                    },
                    "style": {
                        "fontSize": 16,
                        "color": [1, 0.5, 0, 1]
                    }
                }
            ],
            analysis_explanation={
                "title": "Development Analysis",
                "metrics": [
                    {"label": "Pressure Score", "value": f"{pressure:.1f}/100"},
                    {"label": "Likelihood", "value": "High" if pressure > 70 else "Moderate" if pressure > 40 else "Low"},
                    {"label": "Amenity Change", "value": f"{'+' if deltas.amenity_density_change > 0 else ''}{deltas.amenity_density_change:.1f}%"}
                ]
            },
            duration=6000
        )
    
    def _create_property_value_step(self, deltas: ScenarioDeltas, location: Dict[str, float]) -> StoryboardStep:
        """Create property value impact step"""
        impact = deltas.property_value_impact
        
        return StoryboardStep(
            title="Property Value Impact",
            narration=f"Property values in the area are projected to {'increase' if impact > 0 else 'decrease'} "
                     f"by approximately {abs(impact):.1f}%. This is based on accessibility, amenities, and development trends.",
            camera={
                "lat": location['lat'],
                "lng": location['lng'] - 0.005,
                "height": 1000,
                "heading": 270,
                "pitch": -45,
                "duration": 2.5
            },
            overlays=[
                {
                    "type": "circle",
                    "data": {
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "radius": 600
                    },
                    "style": {
                        "color": [0, 1, 0, 1] if impact > 0 else [1, 0, 0, 1],
                        "opacity": 0.25
                    }
                },
                {
                    "type": "label",
                    "data": {
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "text": f"Property Value: {'+' if impact > 0 else ''}{impact:.1f}%"
                    },
                    "style": {
                        "fontSize": 18,
                        "color": [0, 1, 0, 1] if impact > 0 else [1, 0, 0, 1]
                    }
                }
            ],
            analysis_explanation={
                "title": "Property Value Analysis",
                "metrics": [
                    {"label": "Projected Change", "value": f"{'+' if impact > 0 else ''}{impact:.1f}%"},
                    {"label": "Confidence", "value": f"{deltas.confidence * 100:.0f}%"},
                    {"label": "Timeframe", "value": "3-5 years"}
                ],
                "explanation": deltas.reasoning
            },
            duration=6000
        )
    
    def _create_summary_step(self, deltas: ScenarioDeltas, location: Dict[str, float]) -> StoryboardStep:
        """Create summary step"""
        overall_positive = (deltas.accessibility_change + deltas.property_value_impact + 
                          deltas.walkability_change) > 0
        
        return StoryboardStep(
            title="Summary",
            narration=f"In summary, this scenario shows {'overall positive' if overall_positive else 'mixed'} impacts. "
                     f"Key factors include accessibility changes, development pressure, and property value trends. "
                     f"Confidence level: {deltas.confidence * 100:.0f}%.",
            camera={
                "lat": location['lat'],
                "lng": location['lng'],
                "height": 2500,
                "heading": 0,
                "pitch": -70,
                "duration": 3
            },
            overlays=[
                {
                    "type": "circle",
                    "data": {
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "radius": 1200
                    },
                    "style": {
                        "color": [0, 1, 0, 1] if overall_positive else [1, 0.5, 0, 1],
                        "opacity": 0.2
                    }
                },
                {
                    "type": "label",
                    "data": {
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "text": "Impact Zone"
                    },
                    "style": {
                        "fontSize": 16
                    }
                }
            ],
            analysis_explanation={
                "title": "Summary",
                "metrics": [
                    {"label": "Overall Impact", "value": "Positive" if overall_positive else "Mixed"},
                    {"label": "Accessibility", "value": f"{'+' if deltas.accessibility_change > 0 else ''}{deltas.accessibility_change:.1f}%"},
                    {"label": "Property Value", "value": f"{'+' if deltas.property_value_impact > 0 else ''}{deltas.property_value_impact:.1f}%"},
                    {"label": "Development", "value": f"{deltas.development_pressure:.1f}/100"},
                    {"label": "Confidence", "value": f"{deltas.confidence * 100:.0f}%"}
                ],
                "explanation": deltas.reasoning
            },
            duration=7000
        )

# Singleton instance
_narrative_generator = None

def get_narrative_generator() -> NarrativeGenerator:
    """Get or create narrative generator singleton"""
    global _narrative_generator
    if _narrative_generator is None:
        _narrative_generator = NarrativeGenerator()
    return _narrative_generator
