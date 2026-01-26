"""
Prediction Output Schema for City Intelligence Engine
Standardized format for all forecasts and assessments with confidence calibration.

Features:
1. Structured prediction format with confidence intervals
2. Multi-domain support (population, traffic, real estate, etc.)
3. Calibrated probability estimates
4. Visual-ready output format
5. Narrative integration support
"""

from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, date
import json
import math


class PredictionDomain(Enum):
    """Domains for predictions."""
    PROPERTY_VALUE = "property_value"
    POPULATION = "population"
    TRAFFIC = "traffic"
    INFRASTRUCTURE = "infrastructure"
    EMPLOYMENT = "employment"
    ENVIRONMENT = "environment"
    QUALITY_OF_LIFE = "quality_of_life"
    MARKET = "market"


class TimeHorizon(Enum):
    """Time horizons for predictions."""
    IMMEDIATE = "immediate"      # 0-6 months
    SHORT_TERM = "short_term"    # 6-18 months
    MEDIUM_TERM = "medium_term"  # 18 months - 3 years
    LONG_TERM = "long_term"      # 3-10 years
    STRATEGIC = "strategic"      # 10+ years


class ConfidenceLevel(Enum):
    """Confidence level categories."""
    VERY_HIGH = "very_high"     # >90%
    HIGH = "high"               # 75-90%
    MODERATE = "moderate"       # 50-75%
    LOW = "low"                 # 25-50%
    VERY_LOW = "very_low"       # <25%


@dataclass
class ConfidenceInterval:
    """A confidence interval for a numeric prediction."""
    lower: float
    point_estimate: float
    upper: float
    confidence_level: float = 0.95  # e.g., 95% CI
    
    def __str__(self):
        return f"{self.point_estimate:.2f} [{self.lower:.2f} - {self.upper:.2f}] ({self.confidence_level*100:.0f}% CI)"
    
    def to_dict(self):
        return {
            'lower': self.lower,
            'point_estimate': self.point_estimate,
            'upper': self.upper,
            'confidence_level': self.confidence_level,
        }


@dataclass
class PredictionMetadata:
    """Metadata about a prediction."""
    model_name: str = "city_intelligence_engine"
    model_version: str = "1.0"
    generated_at: str = ""
    data_sources: List[str] = field(default_factory=list)
    methodology: str = ""
    limitations: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()


@dataclass
class DataQualityMetrics:
    """Quality metrics for the data used in prediction."""
    completeness: float = 0.0      # % of required data available
    recency: float = 0.0           # How recent is the data (0-1)
    consistency: float = 0.0       # Internal consistency
    coverage: float = 0.0          # Geographic/temporal coverage
    
    def overall_quality(self) -> float:
        return (self.completeness + self.recency + self.consistency + self.coverage) / 4


@dataclass
class PredictionOutput:
    """
    Standardized prediction output format.
    Supports both numeric and categorical predictions.
    """
    # Identification
    prediction_id: str
    domain: PredictionDomain
    subject: str                   # What is being predicted (e.g., "Whitefield property prices")
    
    # Time context
    base_date: str                 # When the prediction was made
    target_date: str               # What date/period is being predicted
    time_horizon: TimeHorizon
    
    # The prediction
    prediction_type: str           # "numeric", "categorical", "trend", "scenario"
    
    # Numeric prediction fields
    point_estimate: Optional[float] = None
    confidence_interval: Optional[ConfidenceInterval] = None
    unit: str = ""                 # e.g., "INR/sqft", "minutes", "people"
    
    # Categorical prediction fields
    predicted_category: Optional[str] = None
    category_probabilities: Dict[str, float] = field(default_factory=dict)
    
    # Trend prediction fields
    trend_direction: Optional[str] = None    # "increasing", "decreasing", "stable", "volatile"
    trend_magnitude: Optional[float] = None  # Rate of change
    
    # Confidence and quality
    overall_confidence: float = 0.5
    confidence_level: ConfidenceLevel = ConfidenceLevel.MODERATE
    data_quality: DataQualityMetrics = field(default_factory=DataQualityMetrics)
    
    # Explanation
    reasoning: List[str] = field(default_factory=list)
    key_assumptions: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    # Comparison (if applicable)
    baseline_value: Optional[float] = None
    change_from_baseline: Optional[float] = None
    change_percentage: Optional[float] = None
    
    # Scenarios
    scenarios: Dict[str, Any] = field(default_factory=dict)  # best/worst/base case
    
    # Metadata
    metadata: PredictionMetadata = field(default_factory=PredictionMetadata)
    
    def __post_init__(self):
        # Set confidence level from overall_confidence
        if self.overall_confidence > 0.9:
            self.confidence_level = ConfidenceLevel.VERY_HIGH
        elif self.overall_confidence > 0.75:
            self.confidence_level = ConfidenceLevel.HIGH
        elif self.overall_confidence > 0.5:
            self.confidence_level = ConfidenceLevel.MODERATE
        elif self.overall_confidence > 0.25:
            self.confidence_level = ConfidenceLevel.LOW
        else:
            self.confidence_level = ConfidenceLevel.VERY_LOW
    
    def to_narrative(self) -> str:
        """Convert prediction to natural language narrative."""
        parts = []
        
        # Subject and time
        parts.append(f"**Prediction for {self.subject}**")
        parts.append(f"Target period: {self.target_date} ({self.time_horizon.value.replace('_', ' ')})")
        
        # The prediction itself
        if self.prediction_type == "numeric" and self.point_estimate is not None:
            if self.confidence_interval:
                parts.append(
                    f"Forecast: **{self.point_estimate:,.2f} {self.unit}** "
                    f"(95% CI: {self.confidence_interval.lower:,.2f} - {self.confidence_interval.upper:,.2f})"
                )
            else:
                parts.append(f"Forecast: **{self.point_estimate:,.2f} {self.unit}**")
            
            if self.change_percentage is not None:
                direction = "increase" if self.change_percentage > 0 else "decrease"
                parts.append(f"This represents a **{abs(self.change_percentage):.1f}% {direction}** from baseline")
        
        elif self.prediction_type == "categorical" and self.predicted_category:
            prob = self.category_probabilities.get(self.predicted_category, 0)
            parts.append(f"Most likely outcome: **{self.predicted_category}** ({prob*100:.0f}% probability)")
        
        elif self.prediction_type == "trend":
            parts.append(f"Trend direction: **{self.trend_direction}**")
            if self.trend_magnitude:
                parts.append(f"Rate of change: {self.trend_magnitude:+.1f}% per year")
        
        # Confidence
        parts.append(f"\nConfidence: {self.confidence_level.value.replace('_', ' ')} ({self.overall_confidence*100:.0f}%)")
        
        # Reasoning
        if self.reasoning:
            parts.append("\n**Key factors:**")
            for reason in self.reasoning[:3]:
                parts.append(f"- {reason}")
        
        # Risks
        if self.risk_factors:
            parts.append("\n**Risk factors:**")
            for risk in self.risk_factors[:3]:
                parts.append(f"- ⚠️ {risk}")
        
        return "\n".join(parts)
    
    def to_dashboard_card(self) -> Dict[str, Any]:
        """Convert to dashboard card format."""
        card = {
            'title': self.subject,
            'domain': self.domain.value,
            'time_horizon': self.time_horizon.value,
            'confidence': self.overall_confidence,
            'confidence_label': self.confidence_level.value,
        }
        
        if self.prediction_type == "numeric" and self.point_estimate is not None:
            card['value'] = self.point_estimate
            card['unit'] = self.unit
            if self.change_percentage is not None:
                card['change'] = self.change_percentage
                card['change_direction'] = 'up' if self.change_percentage > 0 else 'down'
            if self.confidence_interval:
                card['range'] = [self.confidence_interval.lower, self.confidence_interval.upper]
        
        elif self.prediction_type == "categorical":
            card['category'] = self.predicted_category
            card['probabilities'] = self.category_probabilities
        
        elif self.prediction_type == "trend":
            card['trend'] = self.trend_direction
            card['magnitude'] = self.trend_magnitude
        
        return card
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result['domain'] = self.domain.value
        result['time_horizon'] = self.time_horizon.value
        result['confidence_level'] = self.confidence_level.value
        if self.confidence_interval:
            result['confidence_interval'] = self.confidence_interval.to_dict()
        result['metadata'] = asdict(self.metadata)
        result['data_quality'] = asdict(self.data_quality)
        return result


class PredictionBuilder:
    """
    Builder for creating calibrated predictions.
    """
    
    def __init__(self):
        self.prediction_count = 0
    
    def create_numeric_prediction(
        self,
        subject: str,
        domain: PredictionDomain,
        point_estimate: float,
        unit: str,
        target_date: str,
        time_horizon: TimeHorizon = TimeHorizon.MEDIUM_TERM,
        uncertainty_pct: float = 0.15,  # Default 15% uncertainty
        baseline: float = None,
        reasoning: List[str] = None,
        assumptions: List[str] = None,
        risks: List[str] = None,
        data_sources: List[str] = None,
    ) -> PredictionOutput:
        """Create a numeric prediction with confidence interval."""
        
        self.prediction_count += 1
        pred_id = f"pred_{datetime.now().strftime('%Y%m%d')}_{self.prediction_count:04d}"
        
        # Calculate confidence interval
        margin = point_estimate * uncertainty_pct
        ci = ConfidenceInterval(
            lower=point_estimate - margin,
            point_estimate=point_estimate,
            upper=point_estimate + margin,
            confidence_level=0.95
        )
        
        # Calculate confidence based on time horizon and uncertainty
        base_confidence = 0.85 - (uncertainty_pct * 2)  # Lower confidence for higher uncertainty
        
        horizon_penalty = {
            TimeHorizon.IMMEDIATE: 0,
            TimeHorizon.SHORT_TERM: 0.05,
            TimeHorizon.MEDIUM_TERM: 0.1,
            TimeHorizon.LONG_TERM: 0.2,
            TimeHorizon.STRATEGIC: 0.3,
        }
        
        overall_confidence = max(0.2, base_confidence - horizon_penalty.get(time_horizon, 0.1))
        
        # Calculate change from baseline
        change = None
        change_pct = None
        if baseline is not None and baseline != 0:
            change = point_estimate - baseline
            change_pct = (change / baseline) * 100
        
        prediction = PredictionOutput(
            prediction_id=pred_id,
            domain=domain,
            subject=subject,
            base_date=datetime.now().strftime("%Y-%m-%d"),
            target_date=target_date,
            time_horizon=time_horizon,
            prediction_type="numeric",
            point_estimate=point_estimate,
            confidence_interval=ci,
            unit=unit,
            overall_confidence=overall_confidence,
            baseline_value=baseline,
            change_from_baseline=change,
            change_percentage=change_pct,
            reasoning=reasoning or [],
            key_assumptions=assumptions or [],
            risk_factors=risks or [],
            metadata=PredictionMetadata(
                data_sources=data_sources or [],
                methodology="Statistical extrapolation with expert rules",
            ),
        )
        
        return prediction
    
    def create_trend_prediction(
        self,
        subject: str,
        domain: PredictionDomain,
        trend_direction: str,
        trend_magnitude: float,
        target_date: str,
        time_horizon: TimeHorizon = TimeHorizon.MEDIUM_TERM,
        confidence: float = 0.7,
        reasoning: List[str] = None,
    ) -> PredictionOutput:
        """Create a trend prediction."""
        
        self.prediction_count += 1
        pred_id = f"pred_{datetime.now().strftime('%Y%m%d')}_{self.prediction_count:04d}"
        
        prediction = PredictionOutput(
            prediction_id=pred_id,
            domain=domain,
            subject=subject,
            base_date=datetime.now().strftime("%Y-%m-%d"),
            target_date=target_date,
            time_horizon=time_horizon,
            prediction_type="trend",
            trend_direction=trend_direction,
            trend_magnitude=trend_magnitude,
            overall_confidence=confidence,
            reasoning=reasoning or [],
        )
        
        return prediction
    
    def create_scenario_prediction(
        self,
        subject: str,
        domain: PredictionDomain,
        base_case: float,
        best_case: float,
        worst_case: float,
        unit: str,
        target_date: str,
        time_horizon: TimeHorizon = TimeHorizon.MEDIUM_TERM,
        scenario_probabilities: Dict[str, float] = None,
        reasoning: List[str] = None,
    ) -> PredictionOutput:
        """Create a scenario-based prediction."""
        
        self.prediction_count += 1
        pred_id = f"pred_{datetime.now().strftime('%Y%m%d')}_{self.prediction_count:04d}"
        
        if scenario_probabilities is None:
            scenario_probabilities = {'base': 0.6, 'best': 0.2, 'worst': 0.2}
        
        # Expected value
        expected = (
            base_case * scenario_probabilities.get('base', 0.6) +
            best_case * scenario_probabilities.get('best', 0.2) +
            worst_case * scenario_probabilities.get('worst', 0.2)
        )
        
        prediction = PredictionOutput(
            prediction_id=pred_id,
            domain=domain,
            subject=subject,
            base_date=datetime.now().strftime("%Y-%m-%d"),
            target_date=target_date,
            time_horizon=time_horizon,
            prediction_type="scenario",
            point_estimate=expected,
            unit=unit,
            scenarios={
                'base_case': {'value': base_case, 'probability': scenario_probabilities.get('base', 0.6)},
                'best_case': {'value': best_case, 'probability': scenario_probabilities.get('best', 0.2)},
                'worst_case': {'value': worst_case, 'probability': scenario_probabilities.get('worst', 0.2)},
            },
            confidence_interval=ConfidenceInterval(
                lower=worst_case,
                point_estimate=expected,
                upper=best_case,
                confidence_level=0.9
            ),
            overall_confidence=0.65,  # Scenario predictions have moderate confidence
            reasoning=reasoning or [],
        )
        
        return prediction


# Singleton builder
_prediction_builder = None


def get_prediction_builder() -> PredictionBuilder:
    """Get singleton prediction builder."""
    global _prediction_builder
    if _prediction_builder is None:
        _prediction_builder = PredictionBuilder()
    return _prediction_builder
