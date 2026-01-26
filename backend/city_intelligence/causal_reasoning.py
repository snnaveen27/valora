"""
Causal Reasoning Engine for City Intelligence Engine
Explicit cause-effect reasoning for urban planning decisions.

Features:
1. Causal rules: infrastructure → impact chains
2. What-if reasoning with explicit causality
3. Policy impact propagation
4. Confidence-weighted reasoning
5. Explainable decision chains
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class CauseCategory(Enum):
    """Categories of causal factors."""
    INFRASTRUCTURE = "infrastructure"      # Roads, metro, utilities
    POLICY = "policy"                      # Zoning, regulations
    ECONOMIC = "economic"                  # Jobs, businesses
    DEMOGRAPHIC = "demographic"            # Population, migration
    ENVIRONMENTAL = "environmental"        # Climate, terrain
    MARKET = "market"                      # Real estate market forces


class EffectCategory(Enum):
    """Categories of effects."""
    PROPERTY_VALUE = "property_value"
    TRAFFIC = "traffic"
    POPULATION = "population"
    EMPLOYMENT = "employment"
    QUALITY_OF_LIFE = "quality_of_life"
    ENVIRONMENT = "environment"
    INFRASTRUCTURE_LOAD = "infrastructure_load"


class ImpactDirection(Enum):
    """Direction of impact."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


@dataclass
class CausalFactor:
    """A causal factor in reasoning."""
    factor_id: str
    category: CauseCategory
    name: str
    description: str
    magnitude: float = 0.5        # 0-1, strength of the factor
    confidence: float = 0.7       # 0-1, certainty


@dataclass
class CausalEffect:
    """An effect produced by a cause."""
    effect_id: str
    category: EffectCategory
    name: str
    description: str
    impact_direction: ImpactDirection
    magnitude: float = 0.5
    time_horizon: str = "medium"  # immediate, short, medium, long
    confidence: float = 0.7


@dataclass
class CausalRule:
    """A cause-effect rule."""
    rule_id: str
    name: str
    cause: CausalFactor
    effects: List[CausalEffect]
    conditions: List[str] = field(default_factory=list)  # When this rule applies
    evidence: List[str] = field(default_factory=list)    # Supporting evidence


@dataclass
class ReasoningStep:
    """A step in a reasoning chain."""
    step_number: int
    description: str
    cause: str
    effect: str
    confidence: float
    evidence: str = ""


@dataclass
class ReasoningChain:
    """A complete reasoning chain."""
    query: str
    steps: List[ReasoningStep] = field(default_factory=list)
    conclusion: str = ""
    overall_confidence: float = 0.5
    caveats: List[str] = field(default_factory=list)
    

class CausalReasoningEngine:
    """
    Performs explicit causal reasoning for urban planning questions.
    """
    
    # Urban causal rules based on planning knowledge
    URBAN_RULES = [
        # Metro Impact Rules
        CausalRule(
            rule_id="metro_property_value",
            name="Metro Station Property Value Impact",
            cause=CausalFactor(
                "metro_new", CauseCategory.INFRASTRUCTURE,
                "New Metro Station",
                "A new metro station opens within 1km",
                magnitude=0.8, confidence=0.9
            ),
            effects=[
                CausalEffect(
                    "property_increase", EffectCategory.PROPERTY_VALUE,
                    "Property Value Increase",
                    "Property values increase 15-30% within 500m",
                    ImpactDirection.POSITIVE, magnitude=0.7,
                    time_horizon="medium", confidence=0.85
                ),
                CausalEffect(
                    "traffic_local_decrease", EffectCategory.TRAFFIC,
                    "Local Traffic Reduction",
                    "Some reduction in car traffic as commuters shift to metro",
                    ImpactDirection.POSITIVE, magnitude=0.4,
                    time_horizon="short", confidence=0.7
                ),
                CausalEffect(
                    "commercial_growth", EffectCategory.EMPLOYMENT,
                    "Commercial Development",
                    "Retail and commercial establishments increase",
                    ImpactDirection.POSITIVE, magnitude=0.6,
                    time_horizon="medium", confidence=0.8
                ),
            ],
            conditions=["Metro line is operational", "Station has adequate capacity"],
            evidence=["Bangalore Metro Purple Line impact studies", "Global TOD research"]
        ),
        
        # Road Widening Rules
        CausalRule(
            rule_id="road_widening",
            name="Road Widening Impact",
            cause=CausalFactor(
                "road_widen", CauseCategory.INFRASTRUCTURE,
                "Road Widening Project",
                "Major road is widened from 2 to 4 lanes",
                magnitude=0.6, confidence=0.85
            ),
            effects=[
                CausalEffect(
                    "traffic_short_relief", EffectCategory.TRAFFIC,
                    "Short-term Traffic Relief",
                    "Initial reduction in congestion (1-2 years)",
                    ImpactDirection.POSITIVE, magnitude=0.5,
                    time_horizon="short", confidence=0.8
                ),
                CausalEffect(
                    "induced_demand", EffectCategory.TRAFFIC,
                    "Induced Demand",
                    "Traffic increases to fill new capacity (3-5 years)",
                    ImpactDirection.NEGATIVE, magnitude=0.6,
                    time_horizon="long", confidence=0.75
                ),
                CausalEffect(
                    "property_commercial", EffectCategory.PROPERTY_VALUE,
                    "Commercial Strip Development",
                    "Roadside commercial development increases",
                    ImpactDirection.MIXED, magnitude=0.5,
                    time_horizon="medium", confidence=0.7
                ),
            ],
            conditions=["No parallel public transit improvement"],
            evidence=["Induced demand research", "Bangalore ORR patterns"]
        ),
        
        # IT Park Rules
        CausalRule(
            rule_id="it_park",
            name="IT Park Development Impact",
            cause=CausalFactor(
                "it_park_new", CauseCategory.ECONOMIC,
                "New IT Park",
                "Major IT park or tech campus opens",
                magnitude=0.8, confidence=0.85
            ),
            effects=[
                CausalEffect(
                    "employment_increase", EffectCategory.EMPLOYMENT,
                    "Employment Growth",
                    "Significant job creation in area",
                    ImpactDirection.POSITIVE, magnitude=0.8,
                    time_horizon="short", confidence=0.9
                ),
                CausalEffect(
                    "residential_demand", EffectCategory.PROPERTY_VALUE,
                    "Residential Demand Surge",
                    "Housing demand and prices increase significantly",
                    ImpactDirection.POSITIVE, magnitude=0.7,
                    time_horizon="short", confidence=0.85
                ),
                CausalEffect(
                    "traffic_increase", EffectCategory.TRAFFIC,
                    "Traffic Congestion",
                    "Peak hour congestion increases substantially",
                    ImpactDirection.NEGATIVE, magnitude=0.7,
                    time_horizon="immediate", confidence=0.9
                ),
                CausalEffect(
                    "infrastructure_strain", EffectCategory.INFRASTRUCTURE_LOAD,
                    "Infrastructure Strain",
                    "Water, power, and sewage systems stressed",
                    ImpactDirection.NEGATIVE, magnitude=0.6,
                    time_horizon="medium", confidence=0.8
                ),
            ],
            conditions=["Area has development potential"],
            evidence=["Whitefield development pattern", "Electronic City history"]
        ),
        
        # Flood Risk Rules
        CausalRule(
            rule_id="flood_risk",
            name="Flood Risk Impact",
            cause=CausalFactor(
                "flood_prone", CauseCategory.ENVIRONMENTAL,
                "High Flood Risk Area",
                "Area identified as flood-prone (low-lying, near lake)",
                magnitude=0.7, confidence=0.8
            ),
            effects=[
                CausalEffect(
                    "property_discount", EffectCategory.PROPERTY_VALUE,
                    "Property Value Discount",
                    "Properties trade at 10-20% discount",
                    ImpactDirection.NEGATIVE, magnitude=0.5,
                    time_horizon="long", confidence=0.75
                ),
                CausalEffect(
                    "insurance_cost", EffectCategory.QUALITY_OF_LIFE,
                    "Higher Insurance/Maintenance",
                    "Higher costs for flood insurance and damage repair",
                    ImpactDirection.NEGATIVE, magnitude=0.4,
                    time_horizon="long", confidence=0.7
                ),
                CausalEffect(
                    "seasonal_disruption", EffectCategory.QUALITY_OF_LIFE,
                    "Monsoon Disruption",
                    "Commute and daily life disrupted during monsoon",
                    ImpactDirection.NEGATIVE, magnitude=0.6,
                    time_horizon="immediate", confidence=0.85
                ),
            ],
            conditions=["No major stormwater infrastructure upgrade"],
            evidence=["Bangalore monsoon flooding patterns", "ORR underpass issues"]
        ),
        
        # Population Growth Rules
        CausalRule(
            rule_id="pop_growth",
            name="Rapid Population Growth Impact",
            cause=CausalFactor(
                "pop_surge", CauseCategory.DEMOGRAPHIC,
                "Population Surge",
                "Area population grows >20% in 5 years",
                magnitude=0.7, confidence=0.8
            ),
            effects=[
                CausalEffect(
                    "demand_pressure", EffectCategory.PROPERTY_VALUE,
                    "Demand-Driven Price Rise",
                    "Property prices rise due to demand",
                    ImpactDirection.POSITIVE, magnitude=0.6,
                    time_horizon="short", confidence=0.8
                ),
                CausalEffect(
                    "infra_gap", EffectCategory.INFRASTRUCTURE_LOAD,
                    "Infrastructure Gap",
                    "Schools, hospitals, roads overwhelmed",
                    ImpactDirection.NEGATIVE, magnitude=0.7,
                    time_horizon="medium", confidence=0.85
                ),
                CausalEffect(
                    "water_stress", EffectCategory.ENVIRONMENT,
                    "Water Table Depletion",
                    "Groundwater extraction increases, table falls",
                    ImpactDirection.NEGATIVE, magnitude=0.6,
                    time_horizon="long", confidence=0.75
                ),
            ],
            conditions=["Infrastructure not scaled proportionally"],
            evidence=["Sarjapur Road growth pattern", "Whitefield water issues"]
        ),
        
        # Zoning Change Rules
        CausalRule(
            rule_id="zoning_commercial",
            name="Residential to Commercial Zoning Change",
            cause=CausalFactor(
                "zone_change", CauseCategory.POLICY,
                "Zoning Change to Commercial",
                "Area rezoned from residential to mixed-use/commercial",
                magnitude=0.6, confidence=0.75
            ),
            effects=[
                CausalEffect(
                    "land_value_spike", EffectCategory.PROPERTY_VALUE,
                    "Land Value Increase",
                    "Land values increase significantly for commercial potential",
                    ImpactDirection.POSITIVE, magnitude=0.7,
                    time_horizon="immediate", confidence=0.8
                ),
                CausalEffect(
                    "residential_displacement", EffectCategory.QUALITY_OF_LIFE,
                    "Residential Character Loss",
                    "Residential quiet and character affected",
                    ImpactDirection.NEGATIVE, magnitude=0.5,
                    time_horizon="medium", confidence=0.7
                ),
                CausalEffect(
                    "traffic_commercial", EffectCategory.TRAFFIC,
                    "Commercial Traffic",
                    "Delivery vehicles and customer traffic increase",
                    ImpactDirection.NEGATIVE, magnitude=0.5,
                    time_horizon="medium", confidence=0.75
                ),
            ],
            conditions=["Near major roads or commercial corridors"],
            evidence=["Indiranagar 100ft road transformation", "Koramangala commercialization"]
        ),
    ]
    
    def __init__(self):
        self.rules = {rule.rule_id: rule for rule in self.URBAN_RULES}
    
    def reason_about(self, scenario: str, locality: str = None) -> ReasoningChain:
        """
        Perform causal reasoning about a scenario.
        
        Args:
            scenario: Description of the scenario to reason about
            locality: Optional locality context
            
        Returns:
            ReasoningChain with explicit cause-effect steps
        """
        chain = ReasoningChain(query=scenario)
        
        # Identify relevant rules
        relevant_rules = self._identify_relevant_rules(scenario)
        
        if not relevant_rules:
            chain.conclusion = "No specific causal patterns identified for this scenario"
            chain.overall_confidence = 0.3
            return chain
        
        # Build reasoning chain
        step_num = 0
        confidences = []
        
        for rule in relevant_rules:
            step_num += 1
            
            # Add cause step
            chain.steps.append(ReasoningStep(
                step_number=step_num,
                description=f"Identify cause: {rule.cause.name}",
                cause=rule.cause.description,
                effect="(analyzing effects)",
                confidence=rule.cause.confidence,
                evidence=", ".join(rule.evidence[:2]) if rule.evidence else ""
            ))
            
            # Add effect steps
            for effect in rule.effects:
                step_num += 1
                direction_symbol = "↑" if effect.impact_direction == ImpactDirection.POSITIVE else "↓" if effect.impact_direction == ImpactDirection.NEGATIVE else "↔"
                
                chain.steps.append(ReasoningStep(
                    step_number=step_num,
                    description=f"Effect: {effect.name} ({effect.time_horizon} term)",
                    cause=rule.cause.name,
                    effect=f"{direction_symbol} {effect.description}",
                    confidence=effect.confidence,
                ))
                
                confidences.append(effect.confidence)
            
            # Add conditions as caveats
            for condition in rule.conditions:
                chain.caveats.append(f"Assuming: {condition}")
        
        # Generate conclusion
        chain.conclusion = self._generate_conclusion(relevant_rules)
        chain.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        return chain
    
    def _identify_relevant_rules(self, scenario: str) -> List[CausalRule]:
        """Identify rules relevant to the scenario."""
        scenario_lower = scenario.lower()
        relevant = []
        
        # Keyword matching to rules
        rule_keywords = {
            'metro_property_value': ['metro', 'station', 'rail', 'transit'],
            'road_widening': ['road', 'widen', 'lane', 'highway', 'flyover'],
            'it_park': ['it park', 'tech park', 'campus', 'it hub', 'tech hub'],
            'flood_risk': ['flood', 'water', 'rain', 'monsoon', 'waterlog'],
            'pop_growth': ['population', 'growth', 'migration', 'people', 'residents'],
            'zoning_commercial': ['zoning', 'commercial', 'mixed use', 'redevelop'],
        }
        
        for rule_id, keywords in rule_keywords.items():
            if any(kw in scenario_lower for kw in keywords):
                if rule_id in self.rules:
                    relevant.append(self.rules[rule_id])
        
        return relevant
    
    def _generate_conclusion(self, rules: List[CausalRule]) -> str:
        """Generate conclusion text from rules."""
        if not rules:
            return "No conclusion can be drawn."
        
        effects_summary = []
        for rule in rules:
            positive = [e for e in rule.effects if e.impact_direction == ImpactDirection.POSITIVE]
            negative = [e for e in rule.effects if e.impact_direction == ImpactDirection.NEGATIVE]
            
            if positive:
                effects_summary.append(f"Positive impacts: {', '.join(e.name for e in positive)}")
            if negative:
                effects_summary.append(f"Challenges: {', '.join(e.name for e in negative)}")
        
        return "; ".join(effects_summary)
    
    def analyze_infrastructure_impact(self, 
                                      infrastructure_type: str,
                                      locality: str,
                                      details: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze impact of infrastructure change on a locality.
        """
        scenario = f"New {infrastructure_type} in {locality}"
        chain = self.reason_about(scenario)
        
        # Categorize effects
        positive_effects = []
        negative_effects = []
        
        for step in chain.steps:
            if "↑" in step.effect:
                positive_effects.append(step.effect.replace("↑ ", ""))
            elif "↓" in step.effect:
                negative_effects.append(step.effect.replace("↓ ", ""))
        
        return {
            'infrastructure': infrastructure_type,
            'locality': locality,
            'reasoning_steps': len(chain.steps),
            'positive_effects': positive_effects,
            'negative_effects': negative_effects,
            'conclusion': chain.conclusion,
            'confidence': chain.overall_confidence,
            'caveats': chain.caveats,
            'full_chain': chain,
        }
    
    def compare_scenarios(self, 
                         scenario_a: str, 
                         scenario_b: str) -> Dict[str, Any]:
        """Compare two scenarios."""
        chain_a = self.reason_about(scenario_a)
        chain_b = self.reason_about(scenario_b)
        
        return {
            'scenario_a': scenario_a,
            'scenario_b': scenario_b,
            'confidence_a': chain_a.overall_confidence,
            'confidence_b': chain_b.overall_confidence,
            'steps_a': len(chain_a.steps),
            'steps_b': len(chain_b.steps),
            'recommendation': (
                f"Scenario A is better understood (confidence: {chain_a.overall_confidence:.0%})"
                if chain_a.overall_confidence > chain_b.overall_confidence
                else f"Scenario B is better understood (confidence: {chain_b.overall_confidence:.0%})"
            ),
        }
    
    def get_causal_factors(self, effect_type: EffectCategory) -> List[Dict[str, Any]]:
        """Get all causal factors that can produce a given effect type."""
        factors = []
        
        for rule in self.rules.values():
            for effect in rule.effects:
                if effect.category == effect_type:
                    factors.append({
                        'cause': rule.cause.name,
                        'cause_category': rule.cause.category.value,
                        'effect': effect.name,
                        'direction': effect.impact_direction.value,
                        'confidence': effect.confidence,
                    })
        
        return factors


# Singleton
_causal_engine = None


def get_causal_reasoning_engine() -> CausalReasoningEngine:
    """Get singleton causal reasoning engine."""
    global _causal_engine
    if _causal_engine is None:
        _causal_engine = CausalReasoningEngine()
    return _causal_engine
