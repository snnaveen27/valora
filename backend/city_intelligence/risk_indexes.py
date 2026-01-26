"""
Risk and Speculation Indexes for City Intelligence Engine
Composite indicators to flag vulnerabilities and speculative pressures.

Features:
1. Natural hazard risk (flood, heat, seismic)
2. Infrastructure stress index
3. Social vulnerability index
4. Market speculation index
5. Policy/regulatory risk
6. Investment risk composite
"""

import sqlite3
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(Enum):
    """Risk severity levels."""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"


@dataclass
class HazardRisk:
    """Natural hazard risk assessment."""
    flood_risk: float = 0.0        # 0-100
    heat_risk: float = 0.0         # Urban heat island effect
    waterlogging_risk: float = 0.0
    air_quality_risk: float = 0.0
    seismic_risk: float = 10.0     # Bangalore is low seismic zone
    
    composite_score: float = 0.0
    
    def calculate_composite(self):
        weights = {'flood': 0.35, 'heat': 0.2, 'waterlogging': 0.25, 'air': 0.15, 'seismic': 0.05}
        self.composite_score = (
            self.flood_risk * weights['flood'] +
            self.heat_risk * weights['heat'] +
            self.waterlogging_risk * weights['waterlogging'] +
            self.air_quality_risk * weights['air'] +
            self.seismic_risk * weights['seismic']
        )


@dataclass
class InfrastructureStress:
    """Infrastructure capacity stress indicators."""
    road_congestion: float = 0.0      # Traffic stress
    water_stress: float = 0.0         # Water supply adequacy
    power_stress: float = 0.0         # Power reliability
    sewage_stress: float = 0.0        # Sewage/drainage capacity
    public_transport_gap: float = 0.0 # PT accessibility
    
    composite_score: float = 0.0
    
    def calculate_composite(self):
        weights = {'road': 0.3, 'water': 0.25, 'power': 0.15, 'sewage': 0.15, 'pt': 0.15}
        self.composite_score = (
            self.road_congestion * weights['road'] +
            self.water_stress * weights['water'] +
            self.power_stress * weights['power'] +
            self.sewage_stress * weights['sewage'] +
            self.public_transport_gap * weights['pt']
        )


@dataclass
class SocialVulnerability:
    """Social vulnerability indicators (inspired by FEMA NRI)."""
    income_inequality: float = 0.0      # Gini-like measure
    affordable_housing_gap: float = 0.0 # Housing affordability
    healthcare_access_gap: float = 0.0  # Healthcare accessibility
    education_gap: float = 0.0          # Education accessibility
    employment_volatility: float = 0.0  # Job market stability
    
    composite_score: float = 0.0
    
    def calculate_composite(self):
        weights = {'income': 0.2, 'housing': 0.3, 'health': 0.2, 'edu': 0.15, 'emp': 0.15}
        self.composite_score = (
            self.income_inequality * weights['income'] +
            self.affordable_housing_gap * weights['housing'] +
            self.healthcare_access_gap * weights['health'] +
            self.education_gap * weights['edu'] +
            self.employment_volatility * weights['emp']
        )


@dataclass
class MarketSpeculation:
    """Real estate market speculation indicators."""
    price_volatility: float = 0.0       # Price standard deviation
    price_income_ratio: float = 0.0     # Price vs local income
    rental_yield_compression: float = 0.0  # Falling yields = speculation
    new_supply_absorption_gap: float = 0.0 # Supply vs demand mismatch
    investor_buyer_ratio: float = 0.0   # Investors vs end-users
    price_momentum: float = 0.0         # Rapid price acceleration
    
    composite_score: float = 0.0
    bubble_probability: float = 0.0
    
    def calculate_composite(self):
        weights = {
            'volatility': 0.2, 'price_income': 0.25, 'yield': 0.15,
            'supply': 0.15, 'investor': 0.15, 'momentum': 0.1
        }
        self.composite_score = (
            self.price_volatility * weights['volatility'] +
            self.price_income_ratio * weights['price_income'] +
            self.rental_yield_compression * weights['yield'] +
            self.new_supply_absorption_gap * weights['supply'] +
            self.investor_buyer_ratio * weights['investor'] +
            self.price_momentum * weights['momentum']
        )
        
        # Bubble probability heuristic
        if self.composite_score > 70:
            self.bubble_probability = 0.7
        elif self.composite_score > 50:
            self.bubble_probability = 0.4
        elif self.composite_score > 30:
            self.bubble_probability = 0.2
        else:
            self.bubble_probability = 0.1


@dataclass
class PolicyRisk:
    """Policy and regulatory risk indicators."""
    zoning_change_risk: float = 0.0      # Risk of adverse zoning changes
    master_plan_deviation: float = 0.0   # How much area deviates from plan
    litigation_density: float = 0.0      # Property disputes
    approval_uncertainty: float = 0.0    # Building approval delays
    tax_policy_risk: float = 0.0         # Property tax changes
    
    composite_score: float = 0.0
    
    def calculate_composite(self):
        weights = {'zoning': 0.25, 'master': 0.2, 'litigation': 0.2, 'approval': 0.2, 'tax': 0.15}
        self.composite_score = (
            self.zoning_change_risk * weights['zoning'] +
            self.master_plan_deviation * weights['master'] +
            self.litigation_density * weights['litigation'] +
            self.approval_uncertainty * weights['approval'] +
            self.tax_policy_risk * weights['tax']
        )


@dataclass
class RiskProfile:
    """Complete risk profile for a locality."""
    locality_id: str
    name: str
    lat: float = 0.0
    lng: float = 0.0
    
    # Component risks
    hazard: HazardRisk = field(default_factory=HazardRisk)
    infrastructure: InfrastructureStress = field(default_factory=InfrastructureStress)
    social: SocialVulnerability = field(default_factory=SocialVulnerability)
    speculation: MarketSpeculation = field(default_factory=MarketSpeculation)
    policy: PolicyRisk = field(default_factory=PolicyRisk)
    
    # Composite scores
    overall_risk_score: float = 0.0
    investment_risk_score: float = 0.0
    livability_risk_score: float = 0.0
    
    # Risk level classifications
    overall_risk_level: RiskLevel = RiskLevel.MODERATE
    investment_risk_level: RiskLevel = RiskLevel.MODERATE
    
    # Warnings and recommendations
    critical_warnings: List[str] = field(default_factory=list)
    risk_mitigations: List[str] = field(default_factory=list)
    
    # Metadata
    confidence: float = 0.5
    data_sources: List[str] = field(default_factory=list)
    
    def calculate_composites(self):
        """Calculate all composite scores."""
        self.hazard.calculate_composite()
        self.infrastructure.calculate_composite()
        self.social.calculate_composite()
        self.speculation.calculate_composite()
        self.policy.calculate_composite()
        
        # Overall risk (all factors)
        self.overall_risk_score = (
            self.hazard.composite_score * 0.2 +
            self.infrastructure.composite_score * 0.25 +
            self.social.composite_score * 0.15 +
            self.speculation.composite_score * 0.25 +
            self.policy.composite_score * 0.15
        )
        
        # Investment risk (financial focus)
        self.investment_risk_score = (
            self.speculation.composite_score * 0.4 +
            self.policy.composite_score * 0.25 +
            self.infrastructure.composite_score * 0.2 +
            self.hazard.composite_score * 0.15
        )
        
        # Livability risk (resident focus)
        self.livability_risk_score = (
            self.hazard.composite_score * 0.3 +
            self.infrastructure.composite_score * 0.35 +
            self.social.composite_score * 0.35
        )
        
        # Determine risk levels
        self.overall_risk_level = self._score_to_level(self.overall_risk_score)
        self.investment_risk_level = self._score_to_level(self.investment_risk_score)
        
        # Generate warnings
        self._generate_warnings()
    
    def _score_to_level(self, score: float) -> RiskLevel:
        if score < 20:
            return RiskLevel.VERY_LOW
        elif score < 35:
            return RiskLevel.LOW
        elif score < 50:
            return RiskLevel.MODERATE
        elif score < 65:
            return RiskLevel.HIGH
        elif score < 80:
            return RiskLevel.VERY_HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _generate_warnings(self):
        """Generate critical warnings based on risk scores."""
        self.critical_warnings = []
        self.risk_mitigations = []
        
        if self.hazard.flood_risk > 60:
            self.critical_warnings.append("⚠️ HIGH FLOOD RISK: Area prone to flooding during monsoon")
            self.risk_mitigations.append("Check flood insurance options; avoid ground floor")
        
        if self.infrastructure.water_stress > 70:
            self.critical_warnings.append("💧 WATER SCARCITY: Significant water supply challenges")
            self.risk_mitigations.append("Verify water source; consider borewell backup")
        
        if self.infrastructure.road_congestion > 70:
            self.critical_warnings.append("🚗 SEVERE CONGESTION: Major traffic issues")
            self.risk_mitigations.append("Factor commute time; consider WFH flexibility")
        
        if self.speculation.bubble_probability > 0.5:
            self.critical_warnings.append("📈 SPECULATION ALERT: High bubble risk in property prices")
            self.risk_mitigations.append("Exercise caution; don't over-leverage")
        
        if self.policy.litigation_density > 60:
            self.critical_warnings.append("⚖️ LEGAL RISK: High property dispute density")
            self.risk_mitigations.append("Thorough title verification essential")
    
    def get_summary(self) -> str:
        """Get risk summary text."""
        return (
            f"{self.name} Risk Profile:\n"
            f"- Overall Risk: {self.overall_risk_level.value} ({self.overall_risk_score:.0f}/100)\n"
            f"- Investment Risk: {self.investment_risk_level.value} ({self.investment_risk_score:.0f}/100)\n"
            f"- Hazard Risk: {self.hazard.composite_score:.0f}/100\n"
            f"- Infrastructure Stress: {self.infrastructure.composite_score:.0f}/100\n"
            f"- Speculation Index: {self.speculation.composite_score:.0f}/100"
        )


class RiskIndexCalculator:
    """
    Calculates risk indexes for localities using available data.
    """
    
    # Bangalore locality risk profiles (curated estimates)
    BANGALORE_RISKS = {
        'whitefield': {
            'hazard': {'flood': 45, 'heat': 55, 'waterlogging': 50, 'air': 60},
            'infrastructure': {'road': 75, 'water': 70, 'power': 40, 'sewage': 55, 'pt': 30},
            'speculation': {'volatility': 35, 'price_income': 65, 'momentum': 40},
        },
        'koramangala': {
            'hazard': {'flood': 35, 'heat': 50, 'waterlogging': 40, 'air': 55},
            'infrastructure': {'road': 70, 'water': 50, 'power': 35, 'sewage': 45, 'pt': 40},
            'speculation': {'volatility': 25, 'price_income': 80, 'momentum': 20},
        },
        'sarjapur_road': {
            'hazard': {'flood': 40, 'heat': 50, 'waterlogging': 45, 'air': 50},
            'infrastructure': {'road': 85, 'water': 75, 'power': 45, 'sewage': 65, 'pt': 70},
            'speculation': {'volatility': 50, 'price_income': 55, 'momentum': 65},
        },
        'electronic_city': {
            'hazard': {'flood': 30, 'heat': 45, 'waterlogging': 35, 'air': 45},
            'infrastructure': {'road': 55, 'water': 55, 'power': 35, 'sewage': 45, 'pt': 55},
            'speculation': {'volatility': 30, 'price_income': 45, 'momentum': 25},
        },
        'indiranagar': {
            'hazard': {'flood': 25, 'heat': 45, 'waterlogging': 30, 'air': 50},
            'infrastructure': {'road': 60, 'water': 40, 'power': 30, 'sewage': 35, 'pt': 25},
            'speculation': {'volatility': 20, 'price_income': 90, 'momentum': 15},
        },
        'hsr_layout': {
            'hazard': {'flood': 35, 'heat': 45, 'waterlogging': 40, 'air': 45},
            'infrastructure': {'road': 55, 'water': 60, 'power': 35, 'sewage': 50, 'pt': 60},
            'speculation': {'volatility': 35, 'price_income': 60, 'momentum': 40},
        },
        'jayanagar': {
            'hazard': {'flood': 30, 'heat': 40, 'waterlogging': 35, 'air': 45},
            'infrastructure': {'road': 50, 'water': 45, 'power': 30, 'sewage': 40, 'pt': 35},
            'speculation': {'volatility': 15, 'price_income': 70, 'momentum': 10},
        },
        'hebbal': {
            'hazard': {'flood': 50, 'heat': 50, 'waterlogging': 55, 'air': 55},
            'infrastructure': {'road': 65, 'water': 55, 'power': 40, 'sewage': 50, 'pt': 50},
            'speculation': {'volatility': 40, 'price_income': 55, 'momentum': 45},
        },
    }
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
        self.profiles_cache: Dict[str, RiskProfile] = {}
    
    def get_risk_profile(self, locality_name: str, lat: float = None, lng: float = None) -> RiskProfile:
        """Get or calculate risk profile for a locality."""
        key = locality_name.lower().replace(' ', '_').replace('-', '_')
        
        if key in self.profiles_cache:
            return self.profiles_cache[key]
        
        profile = self._calculate_profile(locality_name, lat, lng)
        self.profiles_cache[key] = profile
        
        return profile
    
    def _calculate_profile(self, locality_name: str, lat: float = None, lng: float = None) -> RiskProfile:
        """Calculate risk profile from available data."""
        key = locality_name.lower().replace(' ', '_').replace('-', '_')
        
        profile = RiskProfile(
            locality_id=key,
            name=locality_name.title(),
            lat=lat or 0.0,
            lng=lng or 0.0,
        )
        
        # Use curated data if available
        if key in self.BANGALORE_RISKS:
            curated = self.BANGALORE_RISKS[key]
            
            hazard = curated.get('hazard', {})
            profile.hazard.flood_risk = hazard.get('flood', 30)
            profile.hazard.heat_risk = hazard.get('heat', 40)
            profile.hazard.waterlogging_risk = hazard.get('waterlogging', 35)
            profile.hazard.air_quality_risk = hazard.get('air', 45)
            
            infra = curated.get('infrastructure', {})
            profile.infrastructure.road_congestion = infra.get('road', 50)
            profile.infrastructure.water_stress = infra.get('water', 50)
            profile.infrastructure.power_stress = infra.get('power', 35)
            profile.infrastructure.sewage_stress = infra.get('sewage', 45)
            profile.infrastructure.public_transport_gap = infra.get('pt', 50)
            
            spec = curated.get('speculation', {})
            profile.speculation.price_volatility = spec.get('volatility', 30)
            profile.speculation.price_income_ratio = spec.get('price_income', 50)
            profile.speculation.price_momentum = spec.get('momentum', 30)
        
        # Enrich from database
        if lat and lng:
            self._enrich_from_database(profile, lat, lng)
        
        # Calculate composites
        profile.calculate_composites()
        
        return profile
    
    def _enrich_from_database(self, profile: RiskProfile, lat: float, lng: float):
        """Enrich risk data from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get terrain flood risk
            cursor.execute("""
                SELECT flood_risk, suitability_score
                FROM terrain_grid
                ORDER BY ABS(center_lat - ?) + ABS(center_lng - ?)
                LIMIT 1
            """, (lat, lng))
            
            row = cursor.fetchone()
            if row:
                flood_map = {'low': 20, 'medium': 50, 'high': 80}
                profile.hazard.flood_risk = flood_map.get(row['flood_risk'], 40)
                
                # Waterlogging correlates with flood risk
                profile.hazard.waterlogging_risk = profile.hazard.flood_risk * 0.8
            
            # Check metro access for transport gap
            radius_deg = 2000 / 111000
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM transport_stops
                WHERE transport_type = 'metro'
                AND latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
            
            row = cursor.fetchone()
            metro_count = row['cnt'] if row else 0
            
            # More metros = lower transport gap
            if metro_count >= 2:
                profile.infrastructure.public_transport_gap = 20
            elif metro_count == 1:
                profile.infrastructure.public_transport_gap = 40
            else:
                profile.infrastructure.public_transport_gap = 70
            
            conn.close()
        except Exception as e:
            print(f"[RiskIndex] Database enrichment error: {e}")
    
    def get_risk_comparison(self, localities: List[str]) -> Dict[str, Any]:
        """Compare risks across multiple localities."""
        profiles = [self.get_risk_profile(loc) for loc in localities]
        
        comparison = {
            'localities': [p.name for p in profiles],
            'overall_risk': {p.name: p.overall_risk_score for p in profiles},
            'investment_risk': {p.name: p.investment_risk_score for p in profiles},
            'hazard_risk': {p.name: p.hazard.composite_score for p in profiles},
            'infrastructure_stress': {p.name: p.infrastructure.composite_score for p in profiles},
            'speculation_index': {p.name: p.speculation.composite_score for p in profiles},
            'safest': min(profiles, key=lambda p: p.overall_risk_score).name,
            'riskiest': max(profiles, key=lambda p: p.overall_risk_score).name,
        }
        
        return comparison


# Singleton
_risk_calculator = None


def get_risk_index_calculator() -> RiskIndexCalculator:
    """Get singleton risk calculator."""
    global _risk_calculator
    if _risk_calculator is None:
        _risk_calculator = RiskIndexCalculator()
    return _risk_calculator
