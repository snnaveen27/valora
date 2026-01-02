"""
Risk Index Calculator
Computes composite risk scores for localities: Flood, Infrastructure, Liquidity
Supports multi-city deployment.
"""

import logging
from typing import Dict, Tuple, Any, Optional
from dataclasses import dataclass

# Import city configuration
try:
    from backend.config.cities import city_manager, get_city_config, CityConfig
except ImportError:
    from config.cities import city_manager, get_city_config, CityConfig

logger = logging.getLogger(__name__)


@dataclass
class RiskScore:
    """Risk assessment result for a locality"""
    flood: float           # 0-1, higher = more risk
    infrastructure: float  # 0-1, higher = more strain
    liquidity: float       # 0-1, higher = harder to sell
    regulatory: float      # 0-1, higher = more regulatory risk
    overall: float         # Weighted combination
    risk_level: str        # low, moderate, high, very_high
    drivers: Dict[str, Any]
    mitigation: list


class RiskIndexCalculator:
    """
    Calculates risk indices for localities.
    
    Risk Types:
    
    1. Flood Risk:
       - Distance to water bodies (lakes, streams)
       - Historical flood data
       - Drainage infrastructure
       - Low-lying areas flag
    
    2. Infrastructure Risk:
       - High growth + low infra score = strain
       - Road density vs traffic
       - Power/water infrastructure gaps
       - Public transport capacity
    
    3. Liquidity Risk:
       - Days on market (high = illiquid)
       - Inventory months (high = oversupply)
       - Transaction velocity
       - Price volatility
    
    4. Regulatory Risk:
       - Zoning changes
       - RERA compliance
       - Approval delays
       - Land disputes
    """
    
    # Risk weights (can be tuned)
    WEIGHTS = {
        'flood': 0.20,
        'infrastructure': 0.30,
        'liquidity': 0.35,
        'regulatory': 0.15
    }
    
    # Thresholds
    THRESHOLDS = {
        'water_distance_high_risk': 500,     # meters
        'water_distance_medium_risk': 1000,
        'water_distance_low_risk': 2000,
        'dom_high_risk': 120,                # days
        'dom_medium_risk': 90,
        'inventory_high_risk': 12,           # months
        'inventory_medium_risk': 9,
        'growth_high': 10,                   # %
        'infra_low': 0.4,
    }
    
    def __init__(self, city_id: Optional[str] = None):
        self.city_id = city_id or city_manager.current_city
        self.city_config = get_city_config(self.city_id)
        logger.info(f"RiskIndexCalculator initialized for city: {self.city_id}")
    
    def calculate(self, metrics: Dict[str, Any], spatial_data: Optional[Dict[str, Any]] = None) -> RiskScore:
        """
        Calculate all risk indices for a locality.
        
        Args:
            metrics: Locality state metrics (from LocalityStateService)
            spatial_data: GIS-derived features (water distance, etc.)
        """
        spatial_data = spatial_data or {}
        
        try:
            flood = self._calculate_flood_risk(spatial_data)
            infra = self._calculate_infra_risk(metrics)
            liquidity = self._calculate_liquidity_risk(metrics)
            regulatory = self._calculate_regulatory_risk(metrics, spatial_data)
            
            # Weighted overall score
            overall = (
                self.WEIGHTS['flood'] * flood +
                self.WEIGHTS['infrastructure'] * infra +
                self.WEIGHTS['liquidity'] * liquidity +
                self.WEIGHTS['regulatory'] * regulatory
            )
            
            risk_level = self._categorize_risk(overall)
            drivers = self._identify_risk_drivers(flood, infra, liquidity, regulatory, metrics)
            mitigation = self._suggest_mitigation(flood, infra, liquidity, regulatory)
            
            return RiskScore(
                flood=round(flood, 3),
                infrastructure=round(infra, 3),
                liquidity=round(liquidity, 3),
                regulatory=round(regulatory, 3),
                overall=round(overall, 3),
                risk_level=risk_level,
                drivers=drivers,
                mitigation=mitigation
            )
            
        except Exception as e:
            logger.error(f"Error calculating risk: {e}")
            return RiskScore(
                flood=0.5, infrastructure=0.5, liquidity=0.5, regulatory=0.5,
                overall=0.5, risk_level="moderate",
                drivers={"error": str(e)}, mitigation=[]
            )
    
    def _calculate_flood_risk(self, spatial: Dict[str, Any]) -> float:
        """
        Calculate flood risk from spatial features.
        
        Factors:
        - Distance to water bodies (lakes, streams, rivers)
        - Low-lying terrain
        - Historical flood events
        - Drainage infrastructure
        """
        water_dist = spatial.get('distance_to_water_body', 5000)
        elevation = spatial.get('elevation_relative', 0)  # Negative = low-lying
        has_drainage = spatial.get('drainage_score', 0.5)
        flood_history = spatial.get('flood_events_5y', 0)
        
        # Distance factor
        if water_dist < self.THRESHOLDS['water_distance_high_risk']:
            distance_risk = 0.9
        elif water_dist < self.THRESHOLDS['water_distance_medium_risk']:
            distance_risk = 0.6
        elif water_dist < self.THRESHOLDS['water_distance_low_risk']:
            distance_risk = 0.3
        else:
            distance_risk = 0.1
        
        # Elevation factor
        if elevation < -5:  # Very low-lying
            elevation_risk = 0.8
        elif elevation < 0:
            elevation_risk = 0.5
        else:
            elevation_risk = 0.2
        
        # Drainage factor (inverse - good drainage = low risk)
        drainage_risk = 1 - has_drainage
        
        # Historical factor
        history_risk = min(1.0, flood_history * 0.3)
        
        # Weighted combination
        flood_risk = (
            0.4 * distance_risk +
            0.25 * elevation_risk +
            0.2 * drainage_risk +
            0.15 * history_risk
        )
        
        return min(1.0, max(0.0, flood_risk))
    
    def _calculate_infra_risk(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate infrastructure strain risk.
        
        High growth + low infrastructure = high strain risk
        """
        growth = (metrics.get('price_change_12m', 0) or 0) / 100
        infra = metrics.get('infrastructure_score', 0.5) or 0.5
        connectivity = metrics.get('connectivity_score', 0.5) or 0.5
        
        # Growth pressure
        if growth > 0.15:  # >15% growth
            growth_pressure = 0.9
        elif growth > 0.10:
            growth_pressure = 0.7
        elif growth > 0.05:
            growth_pressure = 0.4
        else:
            growth_pressure = 0.2
        
        # Infrastructure gap
        infra_gap = 1 - infra
        connectivity_gap = 1 - connectivity
        
        # Strain = high growth + low infrastructure
        strain = growth_pressure * (infra_gap * 0.6 + connectivity_gap * 0.4)
        
        return min(1.0, max(0.0, strain))
    
    def _calculate_liquidity_risk(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate liquidity risk from market dynamics.
        
        High liquidity risk = hard to sell property
        """
        dom = metrics.get('days_on_market_avg', 60) or 60
        inventory = metrics.get('inventory_months', 6) or 6
        absorption = metrics.get('absorption_rate', 0.5) or 0.5
        listings = metrics.get('active_listings', 100) or 100
        
        # Days on market factor
        if dom > self.THRESHOLDS['dom_high_risk']:
            dom_risk = 0.9
        elif dom > self.THRESHOLDS['dom_medium_risk']:
            dom_risk = 0.6
        elif dom > 60:
            dom_risk = 0.4
        else:
            dom_risk = 0.2
        
        # Inventory factor
        if inventory > self.THRESHOLDS['inventory_high_risk']:
            inventory_risk = 0.9
        elif inventory > self.THRESHOLDS['inventory_medium_risk']:
            inventory_risk = 0.6
        elif inventory > 6:
            inventory_risk = 0.4
        else:
            inventory_risk = 0.2
        
        # Absorption factor (inverse - high absorption = low risk)
        absorption_risk = 1 - absorption
        
        # Combined liquidity risk
        liquidity_risk = (
            0.35 * dom_risk +
            0.35 * inventory_risk +
            0.30 * absorption_risk
        )
        
        return min(1.0, max(0.0, liquidity_risk))
    
    def _calculate_regulatory_risk(self, metrics: Dict[str, Any], spatial: Dict[str, Any]) -> float:
        """
        Calculate regulatory and legal risk.
        
        Factors:
        - Zoning stability
        - RERA compliance
        - Land title clarity
        - Approval delays
        """
        # These would come from actual data in production
        zoning_stability = spatial.get('zoning_stability', 0.7)
        rera_compliance = spatial.get('rera_compliance_rate', 0.8)
        title_clarity = spatial.get('title_clarity_score', 0.8)
        approval_delay = spatial.get('avg_approval_delay_months', 6)
        
        # Zoning risk
        zoning_risk = 1 - zoning_stability
        
        # Compliance risk
        compliance_risk = 1 - rera_compliance
        
        # Title risk
        title_risk = 1 - title_clarity
        
        # Approval delay risk
        if approval_delay > 18:
            delay_risk = 0.8
        elif approval_delay > 12:
            delay_risk = 0.5
        elif approval_delay > 6:
            delay_risk = 0.3
        else:
            delay_risk = 0.1
        
        # Combined regulatory risk
        regulatory_risk = (
            0.25 * zoning_risk +
            0.30 * compliance_risk +
            0.25 * title_risk +
            0.20 * delay_risk
        )
        
        return min(1.0, max(0.0, regulatory_risk))
    
    def _categorize_risk(self, overall: float) -> str:
        """Categorize overall risk level."""
        if overall < 0.25:
            return "low"
        elif overall < 0.45:
            return "moderate"
        elif overall < 0.65:
            return "high"
        return "very_high"
    
    def _identify_risk_drivers(
        self, 
        flood: float, 
        infra: float, 
        liquidity: float, 
        regulatory: float,
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Identify the main risk drivers."""
        
        risks = [
            ("flood", flood, "Flood/water-related risk"),
            ("infrastructure", infra, "Infrastructure strain"),
            ("liquidity", liquidity, "Market liquidity risk"),
            ("regulatory", regulatory, "Regulatory/legal risk")
        ]
        
        # Sort by risk level
        risks.sort(key=lambda x: x[1], reverse=True)
        
        drivers = {
            "primary_risk": {
                "type": risks[0][0],
                "score": risks[0][1],
                "description": risks[0][2]
            },
            "secondary_risk": {
                "type": risks[1][0],
                "score": risks[1][1],
                "description": risks[1][2]
            },
            "risk_breakdown": {
                "flood": flood,
                "infrastructure": infra,
                "liquidity": liquidity,
                "regulatory": regulatory
            }
        }
        
        # Add specific warnings
        warnings = []
        if flood > 0.6:
            warnings.append("High flood risk - verify flood history and insurance")
        if infra > 0.6:
            warnings.append("Infrastructure strain - may face service quality issues")
        if liquidity > 0.6:
            warnings.append("Low liquidity - may take longer to sell")
        if regulatory > 0.5:
            warnings.append("Regulatory concerns - verify all approvals")
        
        drivers["warnings"] = warnings
        
        return drivers
    
    def _suggest_mitigation(
        self, 
        flood: float, 
        infra: float, 
        liquidity: float, 
        regulatory: float
    ) -> list:
        """Suggest risk mitigation strategies."""
        
        mitigation = []
        
        if flood > 0.5:
            mitigation.append("Verify flood insurance availability and cost")
            mitigation.append("Check historical flood data for the area")
            mitigation.append("Consider ground floor properties with caution")
        
        if infra > 0.5:
            mitigation.append("Research upcoming infrastructure projects")
            mitigation.append("Factor in potential traffic/commute issues")
            mitigation.append("Check water and power supply reliability")
        
        if liquidity > 0.5:
            mitigation.append("Consider longer investment horizon")
            mitigation.append("Negotiate better entry price for liquidity discount")
            mitigation.append("Focus on properties with unique selling points")
        
        if regulatory > 0.4:
            mitigation.append("Conduct thorough title search")
            mitigation.append("Verify RERA registration")
            mitigation.append("Check for any pending litigation")
            mitigation.append("Get legal opinion on approvals")
        
        if not mitigation:
            mitigation.append("Standard due diligence recommended")
        
        return mitigation
    
    def get_risk_summary(self, risk_score: RiskScore) -> str:
        """Generate a human-readable risk summary."""
        
        level_descriptions = {
            "low": "This locality has low overall risk, making it suitable for most investors.",
            "moderate": "This locality has moderate risk levels. Standard due diligence is recommended.",
            "high": "This locality has elevated risk. Careful evaluation and additional due diligence required.",
            "very_high": "This locality has very high risk. Only suitable for risk-tolerant investors with deep local knowledge."
        }
        
        summary = level_descriptions.get(risk_score.risk_level, "Risk assessment unavailable.")
        
        if risk_score.drivers.get("warnings"):
            summary += " Key concerns: " + "; ".join(risk_score.drivers["warnings"][:2])
        
        return summary
