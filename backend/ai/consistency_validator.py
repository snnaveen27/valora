"""
Valora AI - Consistency Validator
Validates section analysis results for contradictions before final synthesis
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class Contradiction:
    section_a: str
    section_b: str
    field_a: str
    field_b: str
    value_a: Any
    value_b: Any
    severity: str
    resolution: str
    message: str


@dataclass
class ValidationResult:
    has_contradictions: bool
    contradictions: List[Contradiction]
    low_confidence_sections: List[str]
    needs_fallback: bool
    confidence: float
    resolution_summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_contradictions": self.has_contradictions,
            "contradictions": [
                {
                    "sections": [c.section_a, c.section_b],
                    "field_a": c.field_a,
                    "field_b": c.field_b,
                    "value_a": str(c.value_a),
                    "value_b": str(c.value_b),
                    "severity": c.severity,
                    "resolution": c.resolution,
                    "message": c.message
                }
                for c in self.contradictions
            ],
            "low_confidence_sections": self.low_confidence_sections,
            "needs_fallback": self.needs_fallback,
            "confidence": self.confidence,
            "resolution_summary": self.resolution_summary
        }


class ConsistencyValidator:
    """Validates section analysis results for contradictions"""
    
    def validate(self, section_results: Dict[str, Any]) -> ValidationResult:
        contradictions = []
        low_confidence = []
        resolution_actions = []
        
        terrain = section_results.get("terrain")
        infrastructure = section_results.get("infrastructure")
        market = section_results.get("market")
        risk = section_results.get("risk")
        urban_form = section_results.get("urban_form")
        
        contradictions.extend(self._check_terrain_risk_contradictions(terrain, risk))
        contradictions.extend(self._check_market_infrastructure_contradictions(market, infrastructure))
        contradictions.extend(self._check_urban_market_contradictions(urban_form, market))
        contradictions.extend(self._check_market_risk_contradictions(market, risk))
        contradictions.extend(self._check_terrain_infrastructure_contradictions(terrain, infrastructure))
        
        for section, data in section_results.items():
            if not data:
                continue
            confidence = data.get("confidence")
            if confidence == "LOW" or confidence == 0.3:
                low_confidence.append(section)
        
        for c in contradictions:
            if c.severity == "error":
                if c.resolution == "trust_risk_section":
                    resolution_actions.append(f"Risk section takes precedence for {c.section_b}")
                else:
                    resolution_actions.append(f"Flagged for review: {c.message}")
        
        has_errors = len([c for c in contradictions if c.severity == "error"]) > 1
        needs_fallback = has_errors or len(low_confidence) > 2
        
        confidence = self._calculate_overall_confidence(
            section_results, contradictions, low_confidence
        )
        
        summary = "; ".join(resolution_actions) if resolution_actions else "All sections consistent"
        
        return ValidationResult(
            has_contradictions=len(contradictions) > 0,
            contradictions=contradictions,
            low_confidence_sections=low_confidence,
            needs_fallback=needs_fallback,
            confidence=confidence,
            resolution_summary=summary
        )
    
    def _check_terrain_risk_contradictions(
        self,
        terrain: Optional[Dict],
        risk: Optional[Dict]
    ) -> List[Contradiction]:
        contradictions = []
        if not terrain or not risk:
            return contradictions
        
        terrain_flood = terrain.get("flood_risk")
        risk_flood = None
        
        if risk.get("risk_profile"):
            risk_flood = risk["risk_profile"].get("flood_risk")
        elif risk.get("flood_risk"):
            risk_flood = risk.get("flood_risk")
            
        if terrain_flood and risk_flood:
            high_risk_levels = ["VERY_HIGH", "SEVERE", "HIGH_RISK", "HIGH"]
            terrain_high = terrain_flood.upper() if isinstance(terrain_flood, str) else ""
            risk_high = risk_flood.upper() if isinstance(risk_flood, str) else ""
            
            terrain_in_high = any(level in terrain_high for level in high_risk_levels)
            risk_in_high = any(level in risk_high for level in high_risk_levels)
            
            if terrain_in_high != risk_in_high:
                contradictions.append(Contradiction(
                    section_a="terrain",
                    section_b="risk",
                    field_a="flood_risk",
                    field_b="flood_risk",
                    value_a=terrain_flood,
                    value_b=risk_flood,
                    severity="error",
                    resolution="trust_risk_section",
                    message=f"Flood risk assessment differs: terrain={terrain_flood}, risk={risk_flood}"
))
        return contradictions
    
    def _check_market_risk_contradictions(
        self,
        market: Optional[Dict],
        risk: Optional[Dict]
    ) -> List[Contradiction]:
        contradictions = []
        if not market or not risk:
            return contradictions
        
        demand = str(market.get("demand_level", ""))
        risk_score = None
        
        if risk.get("risk_profile"):
            risk_score = risk["risk_profile"].get("overall_risk_score")
        elif risk.get("overall_risk_score"):
            risk_score = risk.get("overall_risk_score")
        
        try:
            risk_score = float(risk_score) if risk_score else 0
        except (ValueError, TypeError):
            risk_score = 0
        
        high_demand_terms = ["high", "very high", "strong", "very_high", "high_demand"]
        is_high_demand = any(term in demand.lower() for term in high_demand_terms)
        
        if is_high_demand and risk_score > 70:
            contradictions.append(Contradiction(
                section_a="market",
                section_b="risk",
                field_a="demand_level",
                field_b="overall_risk_score",
                value_a=demand,
                value_b=risk_score,
                severity="error",
                resolution="flag_for_review",
                message=f"Market shows high demand but risk score is high ({risk_score})"
            ))
        return contradictions
    
    def _check_market_infrastructure_contradictions(
        self,
        market: Optional[Dict],
        infrastructure: Optional[Dict]
    ) -> List[Contradiction]:
        """Check for contradictions between market demand and infrastructure."""
        contradictions = []
        if not market or not infrastructure:
            return contradictions
        
        demand = str(market.get("demand_level", ""))
        transit_score = None
        
        if infrastructure.get("transit_score"):
            transit_score = infrastructure.get("transit_score")
        
        try:
            transit_score = float(transit_score) if transit_score else 50
        except (ValueError, TypeError):
            transit_score = 50
        
        high_demand_terms = ["high", "very high", "strong", "very_high", "high_demand"]
        is_high_demand = any(term in demand.lower() for term in high_demand_terms)
        
        if is_high_demand and transit_score < 30:
            contradictions.append(Contradiction(
                section_a="market",
                section_b="infrastructure",
                field_a="demand_level",
                field_b="transit_score",
                value_a=demand,
                value_b=transit_score,
                severity="warning",
                resolution="flag_for_review",
                message=f"Market shows high demand but transit score is low ({transit_score})"
            ))
        return contradictions
    
    def _check_urban_market_contradictions(
        self,
        urban_form: Optional[Dict],
        market: Optional[Dict]
    ) -> List[Contradiction]:
        """Check for contradictions between urban form and market data."""
        contradictions = []
        if not urban_form or not market:
            return contradictions
        
        max_height = urban_form.get("max_height_m")
        avg_price_sqft = market.get("avg_price_sqft") or market.get("avg_price_per_sqft")
        
        try:
            max_height = float(max_height) if max_height else 0
            avg_price_sqft = float(avg_price_sqft) if avg_price_sqft else 0
        except (ValueError, TypeError):
            return contradictions
        
        # High-rise area with very low prices is suspicious
        if max_height > 100 and avg_price_sqft > 0 and avg_price_sqft < 5000:
            contradictions.append(Contradiction(
                section_a="urban_form",
                section_b="market",
                field_a="max_height_m",
                field_b="avg_price_sqft",
                value_a=max_height,
                value_b=avg_price_sqft,
                severity="warning",
                resolution="flag_for_review",
                message=f"High-rise area (max {max_height}m) but very low prices (₹{avg_price_sqft}/sqft)"
            ))
        return contradictions
    
    def _check_terrain_infrastructure_contradictions(
        self,
        terrain: Optional[Dict],
        infrastructure: Optional[Dict]
    ) -> List[Contradiction]:
        contradictions = []
        if not terrain or not infrastructure:
            return contradictions
        
        terrain_suitability = terrain.get("construction_suitability") or terrain.get("suitability_score")
        road_distance = infrastructure.get("road_distance_m")
        
        try:
            terrain_suitability = float(terrain_suitability) if terrain_suitability else 50
            road_distance = float(road_distance) if road_distance else 500
        except (ValueError, TypeError):
            return contradictions
        
        if terrain_suitability < 30 and road_distance < 100:
            contradictions.append(Contradiction(
                section_a="terrain",
                section_b="infrastructure",
                field_a="construction_suitability",
                field_b="road_distance_m",
                value_a=terrain_suitability,
                value_b=road_distance,
                severity="warning",
                resolution="flag_for_review",
                message=f"Terrain has low construction suitability but roads are close"
            ))
        return contradictions
    
    def _calculate_overall_confidence(
        self,
        section_results: Dict,
        contradictions: List[Contradiction],
        low_confidence: List[str]
    ) -> float:
        base_confidence = 1.0
        
        error_count = len([c for c in contradictions if c.severity == "error"])
        warning_count = len([c for c in contradictions if c.severity == "warning"])
        
        base_confidence -= (error_count * 0.15)
        base_confidence -= (warning_count * 0.05)
        base_confidence -= (len(low_confidence) * 0.1)
        
        return max(0.0, base_confidence)


def validate_sections(section_results: Dict[str, Any]) -> ValidationResult:
    validator = ConsistencyValidator()
    return validator.validate(section_results)


async def validate_sections_async(section_results: Dict[str, Any]) -> ValidationResult:
    validator = ConsistencyValidator()
    return validator.validate(section_results)
