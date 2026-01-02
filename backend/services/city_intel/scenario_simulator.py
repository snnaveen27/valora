"""
Scenario Simulator
What-if analysis for infrastructure changes and market events.
Supports multi-city deployment.
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Import city configuration
try:
    from backend.config.cities import city_manager, get_city_config, CityConfig
except ImportError:
    from config.cities import city_manager, get_city_config, CityConfig

logger = logging.getLogger(__name__)


@dataclass
class InfraEvent:
    """Infrastructure event for simulation"""
    event_type: str      # metro, highway, it_park, airport, mall, hospital
    name: str            # Event name (e.g., "Purple Line Extension")
    location: Tuple[float, float]  # (lat, lon)
    impact_radius_km: float
    timeline_years: float  # Years until operational
    investment_crores: Optional[float] = None
    status: str = "announced"  # announced, approved, under_construction, operational


@dataclass
class ScenarioResult:
    """Result from scenario simulation"""
    event: InfraEvent
    winners: List[Dict[str, Any]]      # Wards that benefit
    losers: List[Dict[str, Any]]       # Wards that may decline
    spillover: List[Dict[str, Any]]    # Secondary effects
    price_impact_pct: Dict[str, float] # Ward-wise price impact
    confidence: float
    narrative: str
    simulation_date: datetime


class ScenarioSimulator:
    """
    Simulates infrastructure impact on localities.
    
    Methodology:
    1. Identify affected wards within impact radius
    2. Apply impact multipliers based on distance and event type
    3. Model spillover effects (nearby wards absorb overflow)
    4. Adjust for capacity constraints (saturated areas = limited upside)
    5. Generate narrative explanation
    """
    
    # Impact multipliers by event type and distance band
    IMPACT_MULTIPLIERS = {
        'metro': {
            '0-1km': 1.20,   # 20% appreciation within 1km
            '1-2km': 1.12,
            '2-3km': 1.08,
            '3-5km': 1.04,
            '5-10km': 1.02
        },
        'highway': {
            '0-2km': 1.12,
            '2-5km': 1.08,
            '5-10km': 1.04,
            '10-20km': 1.02
        },
        'it_park': {
            '0-3km': 1.15,
            '3-5km': 1.10,
            '5-10km': 1.06,
            '10-15km': 1.03
        },
        'airport': {
            '0-5km': 1.10,
            '5-10km': 1.08,
            '10-20km': 1.05,
            '20-30km': 1.02
        },
        'mall': {
            '0-2km': 1.08,
            '2-5km': 1.05,
            '5-8km': 1.02
        },
        'hospital': {
            '0-2km': 1.06,
            '2-5km': 1.04,
            '5-8km': 1.02
        }
    }
    
    # Timeline adjustment - impact reduces if far in future
    TIMELINE_FACTORS = {
        0: 1.0,      # Operational now
        1: 0.85,     # 1 year away
        2: 0.70,     # 2 years away
        3: 0.55,     # 3 years away
        5: 0.40,     # 5 years away
        10: 0.20     # 10 years away
    }
    
    def __init__(self, db_engine=None, city_id: Optional[str] = None):
        self.db_engine = db_engine
        self.city_id = city_id or city_manager.current_city
        self.city_config = get_city_config(self.city_id)
        logger.info(f"ScenarioSimulator initialized for city: {self.city_id}")
    
    def simulate(
        self, 
        event: InfraEvent, 
        current_states: List[Dict[str, Any]]
    ) -> ScenarioResult:
        """
        Simulate the impact of an infrastructure event.
        
        Args:
            event: The infrastructure change to simulate
            current_states: Current locality_state for all wards
            
        Returns:
            ScenarioResult with winners, losers, and narrative
        """
        try:
            # Step 1: Identify affected wards
            affected = self._identify_affected_wards(event, current_states)
            
            # Step 2: Calculate impact for each ward
            impacts = self._calculate_impact(event, affected)
            
            # Step 3: Adjust for growth phase (saturated = limited upside)
            adjusted_impacts = self._adjust_for_capacity(impacts)
            
            # Step 4: Model spillover effects
            spillover = self._model_spillover(adjusted_impacts, current_states)
            
            # Step 5: Categorize winners and losers
            winners = [w for w in adjusted_impacts if w['impact_pct'] > 2]
            losers = [w for w in adjusted_impacts if w['impact_pct'] < -1]
            
            # Sort by impact
            winners = sorted(winners, key=lambda x: x['impact_pct'], reverse=True)[:10]
            losers = sorted(losers, key=lambda x: x['impact_pct'])[:5]
            
            # Price impact dictionary
            price_impact = {w['ward_id']: w['impact_pct'] for w in adjusted_impacts}
            
            # Generate narrative
            narrative = self._generate_narrative(event, winners, losers, spillover)
            
            return ScenarioResult(
                event=event,
                winners=winners,
                losers=losers,
                spillover=spillover,
                price_impact_pct=price_impact,
                confidence=self._estimate_confidence(event),
                narrative=narrative,
                simulation_date=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in scenario simulation: {e}")
            return ScenarioResult(
                event=event,
                winners=[],
                losers=[],
                spillover=[],
                price_impact_pct={},
                confidence=0.3,
                narrative=f"Simulation error: {str(e)}",
                simulation_date=datetime.now()
            )
    
    def simulate_multiple(
        self, 
        events: List[InfraEvent], 
        current_states: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Simulate multiple events and aggregate impact."""
        
        combined_impact = {}
        results = []
        
        for event in events:
            result = self.simulate(event, current_states)
            results.append(result)
            
            # Aggregate impacts
            for ward_id, impact in result.price_impact_pct.items():
                if ward_id in combined_impact:
                    # Compound effects (not simply additive)
                    combined_impact[ward_id] = (
                        (1 + combined_impact[ward_id]/100) * (1 + impact/100) - 1
                    ) * 100
                else:
                    combined_impact[ward_id] = impact
        
        # Sort to find biggest beneficiaries
        sorted_impact = sorted(
            combined_impact.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return {
            "individual_results": results,
            "combined_impact": combined_impact,
            "top_beneficiaries": sorted_impact[:10],
            "top_losers": sorted_impact[-5:],
            "simulation_date": datetime.now().isoformat()
        }
    
    def _identify_affected_wards(
        self, 
        event: InfraEvent, 
        current_states: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify wards within the impact radius."""
        
        affected = []
        event_lat, event_lon = event.location
        max_radius = event.impact_radius_km
        
        for ward in current_states:
            ward_lat = ward.get('centroid_lat', ward.get('latitude', 12.9716))
            ward_lon = ward.get('centroid_lon', ward.get('longitude', 77.5946))
            
            # Calculate distance (simplified)
            distance_km = self._haversine_distance(
                event_lat, event_lon, ward_lat, ward_lon
            )
            
            if distance_km <= max_radius:
                affected.append({
                    **ward,
                    'distance_km': distance_km
                })
        
        logger.info(f"Found {len(affected)} wards within {max_radius}km of {event.name}")
        return affected
    
    def _calculate_impact(
        self, 
        event: InfraEvent, 
        affected_wards: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate price impact for each affected ward."""
        
        impacts = []
        multipliers = self.IMPACT_MULTIPLIERS.get(event.event_type, {})
        timeline_factor = self._get_timeline_factor(event.timeline_years)
        
        for ward in affected_wards:
            distance = ward['distance_km']
            
            # Find applicable multiplier
            base_multiplier = 1.0
            for distance_band, mult in multipliers.items():
                min_dist, max_dist = self._parse_distance_band(distance_band)
                if min_dist <= distance < max_dist:
                    base_multiplier = mult
                    break
            
            # Apply timeline adjustment
            adjusted_multiplier = 1 + (base_multiplier - 1) * timeline_factor
            impact_pct = (adjusted_multiplier - 1) * 100
            
            impacts.append({
                'ward_id': ward.get('ward_id', 'unknown'),
                'ward_name': ward.get('ward_name', 'Unknown'),
                'distance_km': round(distance, 2),
                'base_multiplier': base_multiplier,
                'timeline_factor': timeline_factor,
                'impact_pct': round(impact_pct, 2),
                'growth_phase': ward.get('growth_phase', 'mature'),
                'current_price': ward.get('avg_price_sqft')
            })
        
        return impacts
    
    def _adjust_for_capacity(self, impacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Adjust impact based on growth phase (capacity constraints)."""
        
        adjusted = []
        
        for ward in impacts:
            phase = ward.get('growth_phase', 'mature')
            impact = ward['impact_pct']
            
            # Capacity adjustment factors
            if phase == 'saturated':
                # Limited upside in saturated areas
                adjusted_impact = impact * 0.4
                adjustment_reason = "Limited upside due to saturation"
            elif phase == 'mature':
                # Moderate response
                adjusted_impact = impact * 0.7
                adjustment_reason = "Moderate response in mature area"
            elif phase == 'accelerating':
                # Strong response
                adjusted_impact = impact * 1.1
                adjustment_reason = "Enhanced impact in accelerating area"
            else:  # emerging
                # High potential but uncertain
                adjusted_impact = impact * 1.2
                adjustment_reason = "High potential in emerging area"
            
            adjusted.append({
                **ward,
                'raw_impact_pct': impact,
                'impact_pct': round(adjusted_impact, 2),
                'adjustment_reason': adjustment_reason
            })
        
        return adjusted
    
    def _model_spillover(
        self, 
        impacts: List[Dict[str, Any]], 
        all_states: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Model secondary spillover effects."""
        
        spillover = []
        
        # Find wards with high impact
        high_impact_wards = [w for w in impacts if w['impact_pct'] > 10]
        
        for hi_ward in high_impact_wards:
            # Spillover narrative
            spillover.append({
                'source_ward': hi_ward['ward_name'],
                'effect': 'price_pressure',
                'description': (
                    f"High appreciation in {hi_ward['ward_name']} may push "
                    f"demand to adjacent lower-priced areas"
                ),
                'magnitude': 'moderate'
            })
        
        # Check for potential negative spillover
        losers = [w for w in impacts if w['impact_pct'] < 0]
        for loser in losers:
            spillover.append({
                'source_ward': loser['ward_name'],
                'effect': 'demand_shift',
                'description': (
                    f"Reduced attractiveness of {loser['ward_name']} "
                    f"may shift demand elsewhere"
                ),
                'magnitude': 'mild'
            })
        
        return spillover
    
    def _generate_narrative(
        self, 
        event: InfraEvent, 
        winners: List[Dict[str, Any]], 
        losers: List[Dict[str, Any]],
        spillover: List[Dict[str, Any]]
    ) -> str:
        """Generate human-readable narrative for the scenario."""
        
        event_descriptions = {
            'metro': 'metro station/line',
            'highway': 'highway/expressway',
            'it_park': 'IT park/tech hub',
            'airport': 'airport',
            'mall': 'shopping mall',
            'hospital': 'hospital/healthcare facility'
        }
        
        event_desc = event_descriptions.get(event.event_type, event.event_type)
        
        # Build narrative
        narrative = f"**{event.name}** ({event_desc})\n\n"
        narrative += f"Timeline: {event.timeline_years:.1f} years to completion\n"
        narrative += f"Impact radius: {event.impact_radius_km}km\n\n"
        
        # Winners section
        if winners:
            narrative += "**Top Beneficiaries:**\n"
            for i, w in enumerate(winners[:5], 1):
                narrative += (
                    f"{i}. {w['ward_name']} - +{w['impact_pct']:.1f}% expected "
                    f"({w['distance_km']:.1f}km away)\n"
                )
            narrative += "\n"
        
        # Losers section
        if losers:
            narrative += "**Areas with Potential Negative Impact:**\n"
            for w in losers[:3]:
                narrative += f"- {w['ward_name']}: {w['impact_pct']:.1f}%\n"
            narrative += "\n"
        
        # Investment advice
        narrative += "**Investment Implications:**\n"
        if winners and winners[0]['impact_pct'] > 10:
            narrative += (
                f"- Strong investment opportunity within 3km of the {event_desc}\n"
                f"- Consider entry before construction visibility increases prices\n"
            )
        else:
            narrative += f"- Moderate opportunity with selective targeting recommended\n"
        
        return narrative
    
    def _estimate_confidence(self, event: InfraEvent) -> float:
        """Estimate confidence in the simulation."""
        
        base_confidence = 0.6
        
        # Higher confidence for operational or under-construction
        if event.status == 'operational':
            base_confidence += 0.2
        elif event.status == 'under_construction':
            base_confidence += 0.15
        elif event.status == 'approved':
            base_confidence += 0.1
        
        # Lower confidence for longer timelines
        if event.timeline_years > 5:
            base_confidence -= 0.15
        elif event.timeline_years > 3:
            base_confidence -= 0.1
        
        return min(0.9, max(0.3, base_confidence))
    
    def _get_timeline_factor(self, years: float) -> float:
        """Get timeline adjustment factor."""
        
        if years <= 0:
            return 1.0
        elif years <= 1:
            return 0.85
        elif years <= 2:
            return 0.70
        elif years <= 3:
            return 0.55
        elif years <= 5:
            return 0.40
        else:
            return 0.20
    
    def _parse_distance_band(self, band: str) -> Tuple[float, float]:
        """Parse distance band string like '0-2km' into (min, max)."""
        
        band = band.replace('km', '').strip()
        parts = band.split('-')
        return float(parts[0]), float(parts[1])
    
    def _haversine_distance(
        self, 
        lat1: float, lon1: float, 
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in km."""
        
        R = 6371  # Earth's radius in km
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)
        
        a = (
            np.sin(delta_lat/2)**2 + 
            np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon/2)**2
        )
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c
    
    # Predefined scenarios by city
    
    @staticmethod
    def get_city_scenarios(city_id: str = "bangalore") -> List[InfraEvent]:
        """Get predefined scenarios for a city."""
        
        scenarios = {
            "bangalore": [
                InfraEvent(
                    event_type="metro",
                    name="Namma Metro Yellow Line Extension",
                    location=(12.9352, 77.6245),
                    impact_radius_km=8,
                    timeline_years=3,
                    investment_crores=5000,
                    status="under_construction"
                ),
                InfraEvent(
                    event_type="highway",
                    name="Peripheral Ring Road (PRR)",
                    location=(12.9716, 77.5946),
                    impact_radius_km=15,
                    timeline_years=5,
                    investment_crores=20000,
                    status="approved"
                ),
                InfraEvent(
                    event_type="it_park",
                    name="Global Tech Park - Devanahalli",
                    location=(13.2100, 77.7066),
                    impact_radius_km=10,
                    timeline_years=2,
                    investment_crores=2000,
                    status="under_construction"
                ),
                InfraEvent(
                    event_type="airport",
                    name="Second Runway - KIA",
                    location=(13.1979, 77.7063),
                    impact_radius_km=20,
                    timeline_years=1,
                    investment_crores=3000,
                    status="under_construction"
                )
            ],
            "mumbai": [
                InfraEvent(
                    event_type="metro",
                    name="Mumbai Metro Line 3 (Aqua Line)",
                    location=(19.0760, 72.8777),
                    impact_radius_km=5,
                    timeline_years=2,
                    investment_crores=23000,
                    status="under_construction"
                ),
                InfraEvent(
                    event_type="highway",
                    name="Mumbai Trans Harbour Link",
                    location=(19.0330, 72.9132),
                    impact_radius_km=12,
                    timeline_years=1,
                    investment_crores=18000,
                    status="under_construction"
                ),
            ],
            "hyderabad": [
                InfraEvent(
                    event_type="metro",
                    name="Hyderabad Metro Phase 2",
                    location=(17.4400, 78.4982),
                    impact_radius_km=6,
                    timeline_years=4,
                    investment_crores=8000,
                    status="approved"
                ),
                InfraEvent(
                    event_type="it_park",
                    name="Pharma City",
                    location=(17.2500, 78.6000),
                    impact_radius_km=15,
                    timeline_years=5,
                    investment_crores=15000,
                    status="under_construction"
                ),
            ],
        }
        
        return scenarios.get(city_id.lower(), [])
    
    @staticmethod
    def get_bangalore_scenarios() -> List[InfraEvent]:
        """Get predefined scenarios for Bangalore. (Legacy method)"""
        return ScenarioSimulator.get_city_scenarios("bangalore")
