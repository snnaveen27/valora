"""
Evolution Timeline System for City Intelligence Engine
Tracks each locality's development history and projected trajectory.

Features:
1. Historical milestones tracking (decade by decade)
2. Infrastructure event timeline
3. Development phase detection
4. Future projection based on momentum
5. Comparative timeline analysis
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime, date
import json


class DevelopmentPhase(Enum):
    """Major development phases in locality evolution."""
    AGRICULTURAL = "agricultural"       # Farmland, villages
    EARLY_SUBURBAN = "early_suburban"   # Initial residential development
    SUBURBAN_GROWTH = "suburban_growth" # Rapid residential expansion
    COMMERCIAL_EMERGENCE = "commercial" # Commercial centers appearing
    IT_TECH_BOOM = "it_tech_boom"       # Tech parks, IT companies
    INFRASTRUCTURE_UPGRADE = "infra"    # Metro, flyovers, roads
    DENSIFICATION = "densification"     # High-rise, vertical growth
    MATURE_URBAN = "mature_urban"       # Fully urbanized
    REDEVELOPMENT = "redevelopment"     # Urban renewal


@dataclass
class HistoricalMilestone:
    """A significant event in locality history."""
    year: int
    event: str
    category: str  # infrastructure, development, policy, economic
    impact: str    # transformative, major, moderate, minor
    description: str = ""
    source: str = ""


@dataclass
class ProjectedMilestone:
    """A projected future event."""
    year: int
    event: str
    category: str
    probability: float  # 0-1
    impact_if_realized: str
    dependencies: List[str] = field(default_factory=list)


@dataclass
class LocalityTimeline:
    """Complete timeline for a locality."""
    locality_id: str
    name: str
    
    # Historical data
    founding_era: str = "Unknown"  # e.g., "Pre-1900", "1950s", "1990s"
    original_character: str = ""   # What it was originally
    
    # Phase history
    phases: List[Tuple[int, int, DevelopmentPhase]] = field(default_factory=list)  # (start_year, end_year, phase)
    
    # Milestones
    historical_milestones: List[HistoricalMilestone] = field(default_factory=list)
    projected_milestones: List[ProjectedMilestone] = field(default_factory=list)
    
    # Current state
    current_phase: DevelopmentPhase = DevelopmentPhase.SUBURBAN_GROWTH
    phase_start_year: int = 2010
    
    # Momentum indicators
    development_velocity: float = 0.0  # Rate of change (0-10)
    infrastructure_momentum: float = 0.0  # Infrastructure investment trend
    population_momentum: float = 0.0  # Population growth trend
    
    # Projections
    projected_phase_2030: Optional[DevelopmentPhase] = None
    projected_population_2030: Optional[int] = None
    key_catalysts: List[str] = field(default_factory=list)  # Events that will drive change
    key_risks: List[str] = field(default_factory=list)  # Events that could derail
    
    def get_decade_summary(self, decade: int) -> str:
        """Get summary for a specific decade (e.g., 1990, 2000, 2010)."""
        milestones = [m for m in self.historical_milestones 
                     if decade <= m.year < decade + 10]
        
        if not milestones:
            return f"No major developments recorded in the {decade}s"
        
        events = [f"- {m.year}: {m.event}" for m in milestones]
        return f"**{decade}s:**\n" + "\n".join(events)
    
    def get_full_narrative(self) -> str:
        """Generate full historical narrative."""
        parts = []
        parts.append(f"# {self.name} Evolution Timeline\n")
        parts.append(f"**Original Character:** {self.original_character}")
        parts.append(f"**Founding Era:** {self.founding_era}\n")
        
        # Phase history
        if self.phases:
            parts.append("## Development Phases")
            for start, end, phase in self.phases:
                end_str = str(end) if end else "present"
                parts.append(f"- {start}-{end_str}: {phase.value.replace('_', ' ').title()}")
        
        # Historical milestones by decade
        if self.historical_milestones:
            parts.append("\n## Key Milestones")
            decades = sorted(set(m.year // 10 * 10 for m in self.historical_milestones))
            for decade in decades:
                parts.append(self.get_decade_summary(decade))
        
        # Future projections
        if self.projected_milestones:
            parts.append("\n## Projected Developments")
            for pm in self.projected_milestones:
                prob_str = f"{pm.probability*100:.0f}%"
                parts.append(f"- {pm.year}: {pm.event} (Probability: {prob_str})")
        
        return "\n".join(parts)


class EvolutionTimelineSystem:
    """
    Builds and manages locality evolution timelines.
    """
    
    # Curated Bangalore locality histories
    BANGALORE_HISTORIES = {
        'whitefield': {
            'name': 'Whitefield',
            'founding_era': '1882',
            'original_character': 'Anglo-Indian settlement and farmland',
            'phases': [
                (1882, 1990, DevelopmentPhase.AGRICULTURAL),
                (1990, 2000, DevelopmentPhase.IT_TECH_BOOM),
                (2000, 2015, DevelopmentPhase.SUBURBAN_GROWTH),
                (2015, 2023, DevelopmentPhase.INFRASTRUCTURE_UPGRADE),
                (2023, None, DevelopmentPhase.MATURE_URBAN),
            ],
            'historical_milestones': [
                HistoricalMilestone(1882, "Founded as Anglo-Indian settlement", "development", "transformative",
                                   "D.S. White establishes Whitefield as a settlement for retired Anglo-Indians"),
                HistoricalMilestone(1994, "ITPB (IT Park Bangalore) established", "economic", "transformative",
                                   "India's first IT park triggers tech boom"),
                HistoricalMilestone(1999, "SAP Labs opens", "economic", "major",
                                   "Major MNC establishes presence"),
                HistoricalMilestone(2005, "Forum Value Mall opens", "development", "major",
                                   "First major retail development"),
                HistoricalMilestone(2011, "Phoenix Marketcity opens", "development", "major",
                                   "Largest mall in the area"),
                HistoricalMilestone(2017, "Metro Purple Line construction begins", "infrastructure", "transformative",
                                   "Game-changing connectivity project"),
                HistoricalMilestone(2023, "Metro Purple Line operational to Whitefield", "infrastructure", "transformative",
                                   "Direct metro connectivity to city center"),
            ],
            'projected_milestones': [
                ProjectedMilestone(2025, "Peripheral Ring Road completion", "infrastructure", 0.7,
                                  "major", ["Land acquisition", "Environmental clearance"]),
                ProjectedMilestone(2027, "Metro Yellow Line extension", "infrastructure", 0.6,
                                  "major", ["DPR approval", "Funding"]),
                ProjectedMilestone(2030, "Complete urban saturation", "development", 0.8,
                                  "moderate", []),
            ],
            'current_phase': DevelopmentPhase.MATURE_URBAN,
            'development_velocity': 6.5,
            'key_catalysts': ['Metro operational', 'ORR connectivity', 'IT sector growth'],
            'key_risks': ['Water scarcity', 'Traffic congestion', 'Over-densification'],
        },
        'koramangala': {
            'name': 'Koramangala',
            'founding_era': '1970s',
            'original_character': 'BDA planned residential layout',
            'phases': [
                (1970, 1990, DevelopmentPhase.EARLY_SUBURBAN),
                (1990, 2005, DevelopmentPhase.SUBURBAN_GROWTH),
                (2005, 2015, DevelopmentPhase.COMMERCIAL_EMERGENCE),
                (2015, None, DevelopmentPhase.MATURE_URBAN),
            ],
            'historical_milestones': [
                HistoricalMilestone(1970, "BDA develops Koramangala layout", "development", "transformative"),
                HistoricalMilestone(1985, "Jyoti Nivas College established", "development", "major"),
                HistoricalMilestone(2007, "Flipkart founded in Koramangala", "economic", "transformative",
                                   "Marks beginning of startup era"),
                HistoricalMilestone(2010, "Forum Mall opens", "development", "major"),
                HistoricalMilestone(2014, "Swiggy founded", "economic", "major"),
                HistoricalMilestone(2015, "Cult.fit launched", "economic", "moderate"),
                HistoricalMilestone(2020, "HSR-Koramangala elevated corridor proposed", "infrastructure", "major"),
            ],
            'projected_milestones': [
                ProjectedMilestone(2026, "Elevated corridor completion", "infrastructure", 0.5, "major"),
                ProjectedMilestone(2028, "Metro connectivity", "infrastructure", 0.4, "transformative"),
            ],
            'current_phase': DevelopmentPhase.MATURE_URBAN,
            'development_velocity': 4.0,
            'key_catalysts': ['Startup ecosystem', 'Young demographics', 'F&B scene'],
            'key_risks': ['Parking crisis', 'Commercial encroachment', 'Gentrification'],
        },
        'sarjapur_road': {
            'name': 'Sarjapur Road',
            'founding_era': 'Pre-2000 (rural)',
            'original_character': 'Agricultural land and villages',
            'phases': [
                (1990, 2005, DevelopmentPhase.AGRICULTURAL),
                (2005, 2012, DevelopmentPhase.EARLY_SUBURBAN),
                (2012, 2020, DevelopmentPhase.SUBURBAN_GROWTH),
                (2020, None, DevelopmentPhase.DENSIFICATION),
            ],
            'historical_milestones': [
                HistoricalMilestone(2005, "Wipro campus established", "economic", "transformative",
                                   "Triggers real estate boom"),
                HistoricalMilestone(2008, "First major apartment projects launched", "development", "major"),
                HistoricalMilestone(2012, "Rainbow Drive layout developed", "development", "major"),
                HistoricalMilestone(2015, "Road widening completed", "infrastructure", "moderate"),
                HistoricalMilestone(2018, "Total Mall opens", "development", "moderate"),
                HistoricalMilestone(2020, "Severe traffic congestion becomes daily norm", "development", "major",
                                   "Infrastructure fails to keep pace with growth"),
            ],
            'projected_milestones': [
                ProjectedMilestone(2026, "Metro extension to Sarjapur", "infrastructure", 0.6, "transformative"),
                ProjectedMilestone(2027, "PRR junction completion", "infrastructure", 0.5, "major"),
                ProjectedMilestone(2030, "Population doubles from 2020", "development", 0.7, "major"),
            ],
            'current_phase': DevelopmentPhase.DENSIFICATION,
            'development_velocity': 8.5,
            'key_catalysts': ['IT corridor expansion', 'Metro extension', 'Affordable housing'],
            'key_risks': ['Severe traffic', 'Water crisis', 'Infrastructure deficit'],
        },
        'electronic_city': {
            'name': 'Electronic City',
            'founding_era': '1978',
            'original_character': 'Designated IT/Industrial park',
            'phases': [
                (1978, 1990, DevelopmentPhase.EARLY_SUBURBAN),
                (1990, 2005, DevelopmentPhase.IT_TECH_BOOM),
                (2005, 2015, DevelopmentPhase.SUBURBAN_GROWTH),
                (2015, None, DevelopmentPhase.MATURE_URBAN),
            ],
            'historical_milestones': [
                HistoricalMilestone(1978, "KEONICS establishes Electronic City", "development", "transformative"),
                HistoricalMilestone(1983, "Infosys sets up first office", "economic", "transformative"),
                HistoricalMilestone(1990, "Wipro establishes campus", "economic", "major"),
                HistoricalMilestone(1998, "Biocon campus established", "economic", "major"),
                HistoricalMilestone(2010, "ELCITA expressway opens", "infrastructure", "transformative"),
                HistoricalMilestone(2013, "Phase 2 expansion completed", "development", "major"),
            ],
            'projected_milestones': [
                ProjectedMilestone(2025, "Metro Yellow Line operational", "infrastructure", 0.8, "transformative"),
                ProjectedMilestone(2028, "Phase 3 development", "development", 0.6, "major"),
            ],
            'current_phase': DevelopmentPhase.MATURE_URBAN,
            'development_velocity': 5.0,
            'key_catalysts': ['Metro connectivity', 'Expressway', 'IT anchor tenants'],
            'key_risks': ['Distance from city', 'Limited social infrastructure'],
        },
        'indiranagar': {
            'name': 'Indiranagar',
            'founding_era': '1970s',
            'original_character': 'Defense colony layout',
            'phases': [
                (1970, 1990, DevelopmentPhase.EARLY_SUBURBAN),
                (1990, 2005, DevelopmentPhase.SUBURBAN_GROWTH),
                (2005, 2015, DevelopmentPhase.COMMERCIAL_EMERGENCE),
                (2015, None, DevelopmentPhase.MATURE_URBAN),
            ],
            'historical_milestones': [
                HistoricalMilestone(1970, "Defense Ministry develops layout", "development", "transformative"),
                HistoricalMilestone(1995, "100 Feet Road commercialization begins", "development", "major"),
                HistoricalMilestone(2005, "Boutique and cafe culture emerges", "development", "major"),
                HistoricalMilestone(2011, "Metro Green Line operational", "infrastructure", "transformative"),
                HistoricalMilestone(2015, "Peak gentrification", "development", "major"),
            ],
            'projected_milestones': [
                ProjectedMilestone(2025, "Complete commercial saturation of main roads", "development", 0.9, "moderate"),
            ],
            'current_phase': DevelopmentPhase.MATURE_URBAN,
            'development_velocity': 3.0,
            'key_catalysts': ['Metro access', 'Premium positioning', 'F&B/retail'],
            'key_risks': ['Affordability crisis', 'Parking', 'Over-commercialization'],
        },
        'hsr_layout': {
            'name': 'HSR Layout',
            'founding_era': '1985',
            'original_character': 'BDA planned residential layout',
            'phases': [
                (1985, 2000, DevelopmentPhase.EARLY_SUBURBAN),
                (2000, 2010, DevelopmentPhase.SUBURBAN_GROWTH),
                (2010, 2020, DevelopmentPhase.COMMERCIAL_EMERGENCE),
                (2020, None, DevelopmentPhase.DENSIFICATION),
            ],
            'historical_milestones': [
                HistoricalMilestone(1985, "HSR Layout developed by BDA", "development", "transformative"),
                HistoricalMilestone(2005, "Agara Lake restoration", "development", "moderate"),
                HistoricalMilestone(2010, "Startup co-working spaces emerge", "economic", "moderate"),
                HistoricalMilestone(2015, "Sector 1-7 fully developed", "development", "major"),
            ],
            'projected_milestones': [
                ProjectedMilestone(2026, "Metro connectivity via extension", "infrastructure", 0.5, "transformative"),
                ProjectedMilestone(2028, "High-rise corridor along ORR", "development", 0.7, "major"),
            ],
            'current_phase': DevelopmentPhase.DENSIFICATION,
            'development_velocity': 6.0,
            'key_catalysts': ['IT proximity', 'Family-friendly', 'Lake'],
            'key_risks': ['Water table depletion', 'Internal road congestion'],
        },
    }
    
    def __init__(self):
        self.timelines_cache: Dict[str, LocalityTimeline] = {}
    
    def get_timeline(self, locality_name: str) -> Optional[LocalityTimeline]:
        """Get or build a locality timeline."""
        key = locality_name.lower().replace(' ', '_').replace('-', '_')
        
        if key in self.timelines_cache:
            return self.timelines_cache[key]
        
        timeline = self._build_timeline(locality_name)
        if timeline:
            self.timelines_cache[key] = timeline
        
        return timeline
    
    def _build_timeline(self, locality_name: str) -> Optional[LocalityTimeline]:
        """Build timeline from curated data."""
        key = locality_name.lower().replace(' ', '_').replace('-', '_')
        
        if key not in self.BANGALORE_HISTORIES:
            # Return basic timeline
            return LocalityTimeline(
                locality_id=key,
                name=locality_name.title(),
                founding_era="Unknown",
                original_character="No historical data available",
            )
        
        data = self.BANGALORE_HISTORIES[key]
        
        timeline = LocalityTimeline(
            locality_id=key,
            name=data['name'],
            founding_era=data['founding_era'],
            original_character=data['original_character'],
            current_phase=data.get('current_phase', DevelopmentPhase.SUBURBAN_GROWTH),
            development_velocity=data.get('development_velocity', 5.0),
            key_catalysts=data.get('key_catalysts', []),
            key_risks=data.get('key_risks', []),
        )
        
        # Add phases
        for start, end, phase in data.get('phases', []):
            timeline.phases.append((start, end, phase))
        
        # Add historical milestones
        for m in data.get('historical_milestones', []):
            timeline.historical_milestones.append(m)
        
        # Add projected milestones
        for pm in data.get('projected_milestones', []):
            timeline.projected_milestones.append(pm)
        
        return timeline
    
    def compare_evolution(self, locality1: str, locality2: str) -> Dict[str, Any]:
        """Compare evolution of two localities."""
        t1 = self.get_timeline(locality1)
        t2 = self.get_timeline(locality2)
        
        if not t1 or not t2:
            return {"error": "One or both localities not found"}
        
        return {
            'localities': [t1.name, t2.name],
            'founding': {t1.name: t1.founding_era, t2.name: t2.founding_era},
            'current_phase': {t1.name: t1.current_phase.value, t2.name: t2.current_phase.value},
            'development_velocity': {t1.name: t1.development_velocity, t2.name: t2.development_velocity},
            'milestone_count': {t1.name: len(t1.historical_milestones), t2.name: len(t2.historical_milestones)},
            'key_catalysts': {t1.name: t1.key_catalysts, t2.name: t2.key_catalysts},
            'analysis': self._generate_evolution_comparison(t1, t2),
        }
    
    def _generate_evolution_comparison(self, t1: LocalityTimeline, t2: LocalityTimeline) -> str:
        """Generate comparative analysis text."""
        parts = []
        
        # Age comparison
        try:
            year1 = int(t1.founding_era[:4]) if t1.founding_era[0].isdigit() else 2000
            year2 = int(t2.founding_era[:4]) if t2.founding_era[0].isdigit() else 2000
            if year1 < year2:
                parts.append(f"{t1.name} is older ({t1.founding_era}) than {t2.name} ({t2.founding_era})")
            elif year2 < year1:
                parts.append(f"{t2.name} is older ({t2.founding_era}) than {t1.name} ({t1.founding_era})")
        except:
            pass
        
        # Velocity comparison
        if t1.development_velocity > t2.development_velocity + 2:
            parts.append(f"{t1.name} is developing faster (velocity: {t1.development_velocity})")
        elif t2.development_velocity > t1.development_velocity + 2:
            parts.append(f"{t2.name} is developing faster (velocity: {t2.development_velocity})")
        
        # Phase comparison
        if t1.current_phase != t2.current_phase:
            parts.append(f"{t1.name} is in {t1.current_phase.value} phase while {t2.name} is in {t2.current_phase.value}")
        
        return "; ".join(parts) if parts else "Both localities have similar evolution patterns"
    
    def project_future(self, locality_name: str, target_year: int = 2030) -> Dict[str, Any]:
        """Project locality's future state."""
        timeline = self.get_timeline(locality_name)
        
        if not timeline:
            return {"error": "Locality not found"}
        
        years_ahead = target_year - datetime.now().year
        
        # Project phase
        if timeline.development_velocity > 7:
            # Fast developing - will advance phases quickly
            projected_phase = DevelopmentPhase.DENSIFICATION
        elif timeline.development_velocity > 5:
            projected_phase = DevelopmentPhase.MATURE_URBAN
        else:
            projected_phase = timeline.current_phase
        
        # Get projected milestones within timeframe
        relevant_projections = [
            pm for pm in timeline.projected_milestones
            if pm.year <= target_year
        ]
        
        return {
            'locality': timeline.name,
            'current_phase': timeline.current_phase.value,
            'projected_phase': projected_phase.value,
            'target_year': target_year,
            'years_ahead': years_ahead,
            'development_velocity': timeline.development_velocity,
            'projected_milestones': [
                {
                    'year': pm.year,
                    'event': pm.event,
                    'probability': pm.probability,
                    'impact': pm.impact_if_realized,
                }
                for pm in relevant_projections
            ],
            'key_catalysts': timeline.key_catalysts,
            'key_risks': timeline.key_risks,
            'confidence': 0.6 if years_ahead <= 5 else 0.4,
        }


# Singleton
_timeline_system = None


def get_evolution_timeline_system() -> EvolutionTimelineSystem:
    """Get singleton timeline system."""
    global _timeline_system
    if _timeline_system is None:
        _timeline_system = EvolutionTimelineSystem()
    return _timeline_system
