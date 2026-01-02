"""
Growth Phase Classifier
Classifies localities into growth phases: Emerging, Accelerating, Mature, Saturated
Supports multi-city deployment with city-specific thresholds.
"""

import logging
from enum import Enum
from typing import Dict, Tuple, Any, Optional
from dataclasses import dataclass

# Import city configuration
try:
    from backend.config.cities import city_manager, get_city_config, CityConfig
except ImportError:
    from config.cities import city_manager, get_city_config, CityConfig

logger = logging.getLogger(__name__)


class GrowthPhase(Enum):
    """Growth phase classification for localities"""
    EMERGING = "emerging"
    ACCELERATING = "accelerating"
    MATURE = "mature"
    SATURATED = "saturated"


@dataclass
class ClassificationResult:
    """Result from growth phase classification"""
    phase: GrowthPhase
    confidence: float
    drivers: Dict[str, Any]
    signals: Dict[str, str]


class GrowthPhaseClassifier:
    """
    Rules-based classifier for locality growth phase.
    
    Phase Definitions:
    - EMERGING: Low density, high growth potential, low prices, new infra coming
    - ACCELERATING: Rising density, sustained high growth, infra improving
    - MATURE: High density, moderate growth, stable prices, full infra
    - SATURATED: Very high density, low/negative growth, price stagnation
    """
    
    # Thresholds (to be tuned based on Bangalore data)
    THRESHOLDS = {
        'price_growth_high': 12.0,       # >12% annual = high growth
        'price_growth_moderate': 5.0,    # 5-12% = moderate
        'price_growth_low': 2.0,         # <2% = low
        'price_growth_negative': 0.0,    # <0% = declining
        'density_high': 0.7,             # normalized 0-1
        'density_moderate': 0.5,
        'density_low': 0.3,
        'infra_high': 0.7,
        'infra_moderate': 0.5,
        'infra_low': 0.4,
        'absorption_high': 0.6,
        'absorption_moderate': 0.4,
        'absorption_low': 0.3,
        'inventory_high': 9.0,           # months
        'inventory_moderate': 6.0,
        'inventory_low': 3.0,
    }
    
    def __init__(self, city_id: Optional[str] = None):
        self.city_id = city_id or city_manager.current_city
        self.city_config = get_city_config(self.city_id)
        logger.info(f"GrowthPhaseClassifier initialized for city: {self.city_id}")
    
    def classify(self, metrics: Dict[str, Any]) -> Tuple[GrowthPhase, float, Dict[str, Any]]:
        """
        Classify a locality based on its metrics.
        
        Args:
            metrics: Dict with keys:
                - price_change_12m: Annual price change %
                - building_density: Normalized 0-1 (or use proxy)
                - infrastructure_score: Normalized 0-1
                - absorption_rate: Rate of sales (0-1)
                - inventory_months: Months of supply
                - active_listings: Number of listings
                - days_on_market_avg: Average DOM
                
        Returns:
            (phase, confidence, drivers)
        """
        try:
            phase = self._determine_phase(metrics)
            confidence = self._calculate_confidence(metrics, phase)
            drivers = self._identify_drivers(metrics, phase)
            
            return phase, confidence, drivers
            
        except Exception as e:
            logger.error(f"Error in classification: {e}")
            return GrowthPhase.MATURE, 0.5, {"error": str(e)}
    
    def classify_detailed(self, metrics: Dict[str, Any]) -> ClassificationResult:
        """Get detailed classification result with signals."""
        phase, confidence, drivers = self.classify(metrics)
        signals = self._generate_signals(metrics, phase)
        
        return ClassificationResult(
            phase=phase,
            confidence=confidence,
            drivers=drivers,
            signals=signals
        )
    
    def _determine_phase(self, m: Dict[str, Any]) -> GrowthPhase:
        """Determine growth phase using decision tree logic."""
        
        # Extract metrics with defaults
        price_growth = m.get('price_change_12m', 0) or 0
        density = m.get('building_density') or m.get('density_proxy', 0.5)
        infra = m.get('infrastructure_score', 0.5) or 0.5
        absorption = m.get('absorption_rate', 0.5) or 0.5
        inventory = m.get('inventory_months', 6) or 6
        dom = m.get('days_on_market_avg', 60) or 60
        
        # Normalize density if not already 0-1
        if density > 1:
            density = min(1.0, density / 100)
        
        # Decision tree
        
        # Check for SATURATED first (declining market)
        if price_growth < self.THRESHOLDS['price_growth_negative']:
            return GrowthPhase.SATURATED
        
        if density > self.THRESHOLDS['density_high']:
            # High density area
            if price_growth < self.THRESHOLDS['price_growth_low']:
                return GrowthPhase.SATURATED
            elif price_growth < self.THRESHOLDS['price_growth_moderate']:
                return GrowthPhase.MATURE
            else:
                # High density but still growing fast - unusual, likely MATURE
                return GrowthPhase.MATURE
        
        elif density < self.THRESHOLDS['density_low']:
            # Low density area
            if price_growth > self.THRESHOLDS['price_growth_high']:
                return GrowthPhase.ACCELERATING
            elif price_growth > self.THRESHOLDS['price_growth_moderate']:
                return GrowthPhase.EMERGING
            else:
                return GrowthPhase.EMERGING
        
        else:
            # Moderate density
            if price_growth > self.THRESHOLDS['price_growth_high']:
                return GrowthPhase.ACCELERATING
            elif price_growth > self.THRESHOLDS['price_growth_moderate']:
                if absorption > self.THRESHOLDS['absorption_high']:
                    return GrowthPhase.ACCELERATING
                return GrowthPhase.MATURE
            elif price_growth > self.THRESHOLDS['price_growth_low']:
                return GrowthPhase.MATURE
            else:
                return GrowthPhase.SATURATED
    
    def _calculate_confidence(self, metrics: Dict[str, Any], phase: GrowthPhase) -> float:
        """Calculate confidence based on data quality and signal strength."""
        
        confidence = 0.5  # Base confidence
        
        # Data quality factors
        data_quality = metrics.get('data_quality_score', 0.7)
        confidence += data_quality * 0.2
        
        # Signal strength - how clearly metrics point to this phase
        price_growth = metrics.get('price_change_12m', 0) or 0
        
        if phase == GrowthPhase.EMERGING:
            if price_growth > 3 and price_growth < 8:
                confidence += 0.1
        elif phase == GrowthPhase.ACCELERATING:
            if price_growth > 10:
                confidence += 0.15
        elif phase == GrowthPhase.MATURE:
            if 3 < price_growth < 10:
                confidence += 0.1
        elif phase == GrowthPhase.SATURATED:
            if price_growth < 2:
                confidence += 0.15
        
        # Check for data completeness
        required_fields = ['price_change_12m', 'infrastructure_score', 'absorption_rate']
        present = sum(1 for f in required_fields if metrics.get(f) is not None)
        confidence += (present / len(required_fields)) * 0.1
        
        return min(0.95, max(0.3, confidence))
    
    def _identify_drivers(self, metrics: Dict[str, Any], phase: GrowthPhase) -> Dict[str, Any]:
        """Identify top contributing factors for the classification."""
        
        drivers = {
            "primary": None,
            "secondary": None,
            "supporting_signals": [],
            "phase_description": self._get_phase_description(phase)
        }
        
        price_growth = metrics.get('price_change_12m', 0) or 0
        infra = metrics.get('infrastructure_score', 0.5) or 0.5
        absorption = metrics.get('absorption_rate', 0.5) or 0.5
        
        # Identify primary driver
        if abs(price_growth) > 10:
            drivers["primary"] = {
                "factor": "price_growth",
                "value": price_growth,
                "interpretation": f"{price_growth:.1f}% annual price change"
            }
        elif infra < 0.4:
            drivers["primary"] = {
                "factor": "infrastructure",
                "value": infra,
                "interpretation": "Low infrastructure score indicates early development"
            }
        else:
            drivers["primary"] = {
                "factor": "market_balance",
                "value": absorption,
                "interpretation": f"Market absorption rate of {absorption:.0%}"
            }
        
        # Identify secondary driver
        if phase == GrowthPhase.ACCELERATING:
            drivers["secondary"] = {
                "factor": "demand_momentum",
                "interpretation": "Strong demand signals across multiple metrics"
            }
        elif phase == GrowthPhase.SATURATED:
            drivers["secondary"] = {
                "factor": "supply_pressure",
                "interpretation": "High inventory relative to demand"
            }
        
        # Add supporting signals
        if price_growth > 8:
            drivers["supporting_signals"].append("Strong price appreciation")
        if absorption > 0.6:
            drivers["supporting_signals"].append("High market absorption")
        if infra > 0.7:
            drivers["supporting_signals"].append("Well-developed infrastructure")
        if metrics.get('inventory_months', 6) > 9:
            drivers["supporting_signals"].append("High inventory levels")
        
        return drivers
    
    def _generate_signals(self, metrics: Dict[str, Any], phase: GrowthPhase) -> Dict[str, str]:
        """Generate human-readable signals for the classification."""
        
        signals = {}
        
        price_growth = metrics.get('price_change_12m', 0) or 0
        infra = metrics.get('infrastructure_score', 0.5) or 0.5
        absorption = metrics.get('absorption_rate', 0.5) or 0.5
        inventory = metrics.get('inventory_months', 6) or 6
        
        # Price signal
        if price_growth > 12:
            signals["price"] = "🔥 Very high growth (>12% YoY)"
        elif price_growth > 8:
            signals["price"] = "📈 Strong growth (8-12% YoY)"
        elif price_growth > 5:
            signals["price"] = "📊 Moderate growth (5-8% YoY)"
        elif price_growth > 0:
            signals["price"] = "➡️ Stable (0-5% YoY)"
        else:
            signals["price"] = "📉 Declining (<0% YoY)"
        
        # Infrastructure signal
        if infra > 0.8:
            signals["infrastructure"] = "🏗️ Excellent infrastructure"
        elif infra > 0.6:
            signals["infrastructure"] = "🏢 Good infrastructure"
        elif infra > 0.4:
            signals["infrastructure"] = "🔨 Developing infrastructure"
        else:
            signals["infrastructure"] = "🌱 Early-stage infrastructure"
        
        # Demand signal
        if absorption > 0.7:
            signals["demand"] = "🔥 Very high demand"
        elif absorption > 0.5:
            signals["demand"] = "📈 Strong demand"
        elif absorption > 0.3:
            signals["demand"] = "📊 Moderate demand"
        else:
            signals["demand"] = "📉 Low demand"
        
        # Supply signal
        if inventory < 3:
            signals["supply"] = "⚠️ Undersupply"
        elif inventory < 6:
            signals["supply"] = "✅ Balanced supply"
        elif inventory < 9:
            signals["supply"] = "📦 High inventory"
        else:
            signals["supply"] = "⚠️ Oversupply"
        
        return signals
    
    def _get_phase_description(self, phase: GrowthPhase) -> str:
        """Get description for a growth phase."""
        
        descriptions = {
            GrowthPhase.EMERGING: (
                "Early-stage development area with low density and growing infrastructure. "
                "High potential for appreciation but higher risk. Suitable for long-term investors."
            ),
            GrowthPhase.ACCELERATING: (
                "Rapidly developing area with strong price momentum and improving infrastructure. "
                "Prime opportunity for capital appreciation. High demand from investors and end-users."
            ),
            GrowthPhase.MATURE: (
                "Well-established area with stable prices and full infrastructure. "
                "Lower appreciation potential but stable returns. Good for rental yield focus."
            ),
            GrowthPhase.SATURATED: (
                "Fully developed area with limited growth potential. "
                "May see stagnation or decline. Consider for specific use cases only."
            )
        }
        
        return descriptions.get(phase, "Unknown phase")
    
    def get_investment_advice(self, phase: GrowthPhase) -> Dict[str, Any]:
        """Get investment advice based on growth phase."""
        
        advice = {
            GrowthPhase.EMERGING: {
                "recommendation": "Buy and hold long-term",
                "risk_level": "High",
                "expected_returns": "High (10-20% annual appreciation possible)",
                "holding_period": "5-10 years",
                "suitable_for": ["Risk-tolerant investors", "Land banking", "Long-term wealth creation"]
            },
            GrowthPhase.ACCELERATING: {
                "recommendation": "Strong buy for capital appreciation",
                "risk_level": "Medium-High",
                "expected_returns": "High (8-15% annual appreciation)",
                "holding_period": "3-5 years",
                "suitable_for": ["Growth investors", "Pre-launch investments", "Flipping with renovation"]
            },
            GrowthPhase.MATURE: {
                "recommendation": "Buy for rental yield",
                "risk_level": "Low-Medium",
                "expected_returns": "Moderate (4-8% annual appreciation + 3-5% rental yield)",
                "holding_period": "3-7 years",
                "suitable_for": ["Rental income seekers", "Conservative investors", "End-users"]
            },
            GrowthPhase.SATURATED: {
                "recommendation": "Selective buying only",
                "risk_level": "Medium (capital preservation risk)",
                "expected_returns": "Low (0-4% appreciation, 3-4% rental yield)",
                "holding_period": "Only if specific requirement",
                "suitable_for": ["Specific location requirement", "Distressed deals only"]
            }
        }
        
        return advice.get(phase, {})
