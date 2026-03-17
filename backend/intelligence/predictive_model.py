"""
Predictive Analytics Model for Valora AI
Phase 4.2: Property value prediction and forecasting

Features:
- 3-5 year value predictions
- Infrastructure impact forecasting
- Demographic trend analysis
- Market cycle prediction
- Investment timing recommendations
- Risk assessment

Note: Uses statistical methods. For ML (Prophet/LSTM), 
install additional dependencies: pip install prophet torch
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math
import json
from pathlib import Path


@dataclass
class PricePrediction:
    """Price prediction result."""
    current_price: float
    predicted_prices: Dict[int, float]  # {year: price}
    confidence_intervals: Dict[int, Tuple[float, float]]  # {year: (low, high)}
    annual_growth_rate: float
    risk_level: str  # low, moderate, high
    factors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class InvestmentRecommendation:
    """Investment recommendation."""
    location_name: str
    overall_score: float  # 0-100
    recommendation: str  # strong_buy, buy, hold, sell, strong_sell
    timing: str  # good_time, wait, urgent
    expected_roi_5yr: float
    risk_factors: List[str] = field(default_factory=list)
    positive_factors: List[str] = field(default_factory=list)
    comparable_areas: List[str] = field(default_factory=list)


@dataclass
class MarketCycle:
    """Market cycle analysis."""
    current_phase: str  # expansion, peak, contraction, trough
    phase_duration_months: int
    estimated_months_remaining: int
    cycle_position: float  # 0-1 (0=trough, 0.25=expansion, 0.5=peak, 0.75=contraction)
    recommendation: str


class PredictiveModel:
    """
    Predictive analytics for property values.
    Uses statistical methods with infrastructure and demographic factors.
    """
    
    # Bangalore historical appreciation rates by area type
    AREA_APPRECIATION_RATES = {
        'emerging': 0.12,       # 12% annual for emerging areas
        'developing': 0.10,    # 10% for developing
        'mature': 0.06,        # 6% for mature
        'saturated': 0.03,     # 3% for saturated
        'default': 0.08        # 8% Bangalore average
    }
    
    # Infrastructure impact multipliers
    INFRASTRUCTURE_MULTIPLIERS = {
        'metro_within_500m': 1.25,
        'metro_within_1km': 1.15,
        'metro_planned': 1.08,
        'highway_nearby': 1.10,
        'airport_15km': 1.12,
        'it_park_nearby': 1.18,
        'tech_corridor': 1.20,
        'cbd_5km': 1.15,
        'school_nearby': 1.05,
        'hospital_nearby': 1.05,
        'mall_nearby': 1.03,
    }
    
    # Market cycle parameters (Bangalore real estate ~7-10 year cycle)
    CYCLE_LENGTH_MONTHS = 96  # 8 years average
    
    def __init__(self):
        self.db_service = None
        self._init_database()
        
        # ML model availability
        self.ml_available = False
        self._check_ml_availability()
    
    def _init_database(self):
        """Initialize database connection."""
        try:
            from database.db_service import DatabaseService
            from backend.config import config
            self.db_service = DatabaseService(str(config.DB_PATH))
        except Exception as e:
            print(f"[PredictiveModel] Database init error: {e}")
    
    def _check_ml_availability(self):
        """Check if ML libraries are available."""
        try:
            import numpy as np
            self.np = np
            self.ml_available = True
        except:
            self.ml_available = False
    
    def predict_price(self, lat: float, lng: float,
                      current_price: float = None,
                      years: int = 5) -> PricePrediction:
        """
        Predict future property prices.
        
        Args:
            lat, lng: Location coordinates
            current_price: Current price per sqft (optional)
            years: Number of years to predict
            
        Returns:
            PricePrediction with forecasted values
        """
        # Get or estimate current price
        if current_price is None:
            current_price = self._estimate_current_price(lat, lng)
        
        # Get area development stage
        area_type = self._classify_area(lat, lng)
        base_growth = self.AREA_APPRECIATION_RATES.get(area_type, 0.08)
        
        # Get infrastructure multipliers
        infra_factors = self._get_infrastructure_factors(lat, lng)
        total_multiplier = 1.0
        for factor, mult in infra_factors.items():
            if mult > 1.0:
                total_multiplier *= mult
        
        # Adjust growth rate
        adjusted_growth = base_growth * min(total_multiplier, 1.5)  # Cap at 50% boost
        
        # Apply market cycle adjustment
        cycle = self.analyze_market_cycle()
        cycle_adjustment = self._get_cycle_adjustment(cycle)
        final_growth = adjusted_growth * cycle_adjustment
        
        # Calculate predictions
        predicted_prices = {}
        confidence_intervals = {}
        
        for year in range(1, years + 1):
            # Compound growth
            predicted = current_price * ((1 + final_growth) ** year)
            predicted_prices[year] = round(predicted, 2)
            
            # Confidence interval (widens with time)
            uncertainty = 0.05 * year  # 5% per year
            low = predicted * (1 - uncertainty)
            high = predicted * (1 + uncertainty)
            confidence_intervals[year] = (round(low, 2), round(high, 2))
        
        # Assess risk
        risk_level = self._assess_risk(lat, lng, final_growth)
        
        # Compile factors
        factors = [
            {"name": "Area Type", "value": area_type, "impact": f"+{(base_growth*100):.1f}% base"},
            {"name": "Market Cycle", "value": cycle.current_phase, "impact": f"{(cycle_adjustment-1)*100:+.1f}%"},
        ]
        for factor, mult in infra_factors.items():
            if mult > 1.0:
                factors.append({
                    "name": factor.replace('_', ' ').title(),
                    "value": "Yes",
                    "impact": f"+{(mult-1)*100:.0f}%"
                })
        
        return PricePrediction(
            current_price=current_price,
            predicted_prices=predicted_prices,
            confidence_intervals=confidence_intervals,
            annual_growth_rate=round(final_growth * 100, 2),
            risk_level=risk_level,
            factors=factors
        )
    
    def _estimate_current_price(self, lat: float, lng: float) -> float:
        """Estimate current price per sqft for location."""
        if not self.db_service:
            return 8000  # Bangalore average
        
        radius_deg = 1000 / 111000
        
        try:
            query = """
                SELECT AVG(price / NULLIF(area, 0)) as avg_price_sqft
                FROM properties
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                AND price > 0 AND area > 0
            """
            result = self.db_service.execute(query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            
            if result and result[0]['avg_price_sqft']:
                return float(result[0]['avg_price_sqft'])
        except:
            pass
        
        return 8000  # Default
    
    def _classify_area(self, lat: float, lng: float) -> str:
        """Classify area development stage."""
        if not self.db_service:
            return 'default'
        
        radius_deg = 2000 / 111000
        
        try:
            # Count buildings
            query = """
                SELECT COUNT(*) as cnt FROM buildings
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            result = self.db_service.execute(query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            building_count = result[0]['cnt'] if result else 0
            
            # Check for metro
            metro_query = """
                SELECT COUNT(*) as cnt FROM transport
                WHERE type IN ('metro', 'metro_station')
                AND latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            metro_result = self.db_service.execute(metro_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            has_metro = (metro_result[0]['cnt'] if metro_result else 0) > 0
            
            # Classify
            if building_count > 300 and has_metro:
                return 'saturated'
            elif building_count > 200:
                return 'mature'
            elif building_count > 100:
                return 'developing'
            else:
                return 'emerging'
            
        except:
            return 'default'
    
    def _get_infrastructure_factors(self, lat: float, lng: float) -> Dict[str, float]:
        """Get infrastructure multipliers for location."""
        factors = {}
        
        if not self.db_service:
            return factors
        
        try:
            # Check for metro
            metro_query = """
                SELECT MIN(
                    (latitude - ?) * (latitude - ?) + 
                    (longitude - ?) * (longitude - ?)
                ) * 111000 * 111000 as dist_sq
                FROM transport
                WHERE type IN ('metro', 'metro_station')
            """
            result = self.db_service.execute(metro_query, (lat, lat, lng, lng))
            if result and result[0]['dist_sq']:
                dist = math.sqrt(result[0]['dist_sq'])
                if dist < 500:
                    factors['metro_within_500m'] = self.INFRASTRUCTURE_MULTIPLIERS['metro_within_500m']
                elif dist < 1000:
                    factors['metro_within_1km'] = self.INFRASTRUCTURE_MULTIPLIERS['metro_within_1km']
            
            # Check for IT parks / offices
            it_query = """
                SELECT COUNT(*) as cnt FROM pois
                WHERE category IN ('office', 'commercial', 'it_park')
                AND latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            radius_deg = 2000 / 111000
            it_result = self.db_service.execute(it_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            if it_result and it_result[0]['cnt'] > 5:
                factors['it_park_nearby'] = self.INFRASTRUCTURE_MULTIPLIERS['it_park_nearby']
            
            # Check for schools
            school_query = """
                SELECT COUNT(*) as cnt FROM pois
                WHERE category IN ('school', 'education', 'college')
                AND latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            school_result = self.db_service.execute(school_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            if school_result and school_result[0]['cnt'] > 2:
                factors['school_nearby'] = self.INFRASTRUCTURE_MULTIPLIERS['school_nearby']
            
            # Check for hospitals
            hospital_query = """
                SELECT COUNT(*) as cnt FROM pois
                WHERE category IN ('hospital', 'clinic', 'healthcare')
                AND latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            hospital_result = self.db_service.execute(hospital_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            if hospital_result and hospital_result[0]['cnt'] > 0:
                factors['hospital_nearby'] = self.INFRASTRUCTURE_MULTIPLIERS['hospital_nearby']
            
        except Exception as e:
            print(f"[PredictiveModel] Infrastructure factor error: {e}")
        
        return factors
    
    def analyze_market_cycle(self, reference_date: datetime = None) -> MarketCycle:
        """
        Analyze current position in market cycle.
        Bangalore real estate follows ~8-year cycles.
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # Reference point: Bangalore market peaked around 2014, 2022
        # Trough around 2018, expected next around 2026
        reference_peak = datetime(2022, 1, 1)
        months_since_peak = (reference_date - reference_peak).days / 30
        
        # Calculate position in cycle
        cycle_position = (months_since_peak % self.CYCLE_LENGTH_MONTHS) / self.CYCLE_LENGTH_MONTHS
        
        # Determine phase
        if cycle_position < 0.25:
            phase = "contraction"
            months_remaining = int((0.25 - cycle_position) * self.CYCLE_LENGTH_MONTHS)
        elif cycle_position < 0.5:
            phase = "trough"
            months_remaining = int((0.5 - cycle_position) * self.CYCLE_LENGTH_MONTHS)
        elif cycle_position < 0.75:
            phase = "expansion"
            months_remaining = int((0.75 - cycle_position) * self.CYCLE_LENGTH_MONTHS)
        else:
            phase = "peak"
            months_remaining = int((1.0 - cycle_position) * self.CYCLE_LENGTH_MONTHS)
        
        # Generate recommendation
        if phase == "trough":
            recommendation = "STRONG BUY - Market at lowest point, best time to invest"
        elif phase == "expansion":
            recommendation = "BUY - Market rising, good time to enter"
        elif phase == "peak":
            recommendation = "HOLD/SELL - Market at peak, consider taking profits"
        else:
            recommendation = "WAIT - Market contracting, prices may fall further"
        
        return MarketCycle(
            current_phase=phase,
            phase_duration_months=int(self.CYCLE_LENGTH_MONTHS / 4),
            estimated_months_remaining=months_remaining,
            cycle_position=round(cycle_position, 2),
            recommendation=recommendation
        )
    
    def _get_cycle_adjustment(self, cycle: MarketCycle) -> float:
        """Get growth rate adjustment based on market cycle."""
        if cycle.current_phase == "expansion":
            return 1.2  # 20% boost during expansion
        elif cycle.current_phase == "peak":
            return 0.8  # 20% reduction at peak
        elif cycle.current_phase == "contraction":
            return 0.6  # 40% reduction during contraction
        else:  # trough
            return 1.0  # Normal at trough
    
    def _assess_risk(self, lat: float, lng: float, growth_rate: float) -> str:
        """Assess investment risk level."""
        risk_score = 0
        
        # High growth = higher risk
        if growth_rate > 0.15:
            risk_score += 30
        elif growth_rate > 0.10:
            risk_score += 20
        elif growth_rate > 0.05:
            risk_score += 10
        
        # Area classification
        area_type = self._classify_area(lat, lng)
        if area_type == 'emerging':
            risk_score += 30
        elif area_type == 'developing':
            risk_score += 20
        elif area_type == 'mature':
            risk_score += 10
        # Saturated = lowest risk
        
        # Market cycle
        cycle = self.analyze_market_cycle()
        if cycle.current_phase in ['peak', 'contraction']:
            risk_score += 20
        
        # Determine level
        if risk_score >= 60:
            return "high"
        elif risk_score >= 30:
            return "moderate"
        else:
            return "low"
    
    def get_investment_recommendation(self, lat: float, lng: float,
                                      current_price: float = None,
                                      budget_lakhs: float = None,
                                      location_name: str = None) -> InvestmentRecommendation:
        """
        Get comprehensive investment recommendation.
        
        Args:
            lat, lng: Location coordinates
            current_price: Current price per sqft
            budget_lakhs: Budget in lakhs
            location_name: Location name for display
            
        Returns:
            InvestmentRecommendation with analysis
        """
        if not location_name:
            location_name = f"Area at {lat:.4f}, {lng:.4f}"
        
        # Get price prediction
        prediction = self.predict_price(lat, lng, current_price, years=5)
        
        # Get market cycle
        cycle = self.analyze_market_cycle()
        
        # Calculate 5-year ROI
        if prediction.current_price > 0:
            price_5yr = prediction.predicted_prices.get(5, prediction.current_price)
            roi_5yr = ((price_5yr - prediction.current_price) / prediction.current_price) * 100
        else:
            roi_5yr = prediction.annual_growth_rate * 5
        
        # Determine recommendation
        positive_factors = []
        risk_factors = []
        
        # Check infrastructure
        infra_factors = self._get_infrastructure_factors(lat, lng)
        if 'metro_within_500m' in infra_factors:
            positive_factors.append("Metro station within 500m")
        if 'metro_within_1km' in infra_factors:
            positive_factors.append("Metro station within 1km")
        if 'it_park_nearby' in infra_factors:
            positive_factors.append("Near IT park/tech hub")
        if 'school_nearby' in infra_factors:
            positive_factors.append("Good schools nearby")
        if 'hospital_nearby' in infra_factors:
            positive_factors.append("Healthcare facilities nearby")
        
        # Area type factors
        area_type = self._classify_area(lat, lng)
        if area_type == 'emerging':
            positive_factors.append("Emerging area with high growth potential")
            risk_factors.append("New area - limited track record")
        elif area_type == 'developing':
            positive_factors.append("Actively developing area")
        elif area_type == 'saturated':
            risk_factors.append("Limited growth potential in saturated area")
        
        # Market cycle factors
        if cycle.current_phase == 'trough':
            positive_factors.append("Market at bottom - ideal entry point")
        elif cycle.current_phase == 'expansion':
            positive_factors.append("Market in growth phase")
        elif cycle.current_phase == 'peak':
            risk_factors.append("Market at peak - limited upside")
        else:
            risk_factors.append("Market contracting - consider waiting")
        
        # Risk level
        if prediction.risk_level == 'high':
            risk_factors.append("High volatility expected")
        
        # Calculate overall score
        score = 50  # Base score
        score += len(positive_factors) * 8
        score -= len(risk_factors) * 10
        score += min(roi_5yr / 5, 20)  # ROI contribution
        
        if cycle.current_phase in ['trough', 'expansion']:
            score += 10
        elif cycle.current_phase in ['peak', 'contraction']:
            score -= 10
        
        score = max(0, min(100, score))
        
        # Determine recommendation
        if score >= 80:
            recommendation = "strong_buy"
            timing = "good_time"
        elif score >= 60:
            recommendation = "buy"
            timing = "good_time"
        elif score >= 40:
            recommendation = "hold"
            timing = "wait"
        elif score >= 20:
            recommendation = "sell"
            timing = "urgent"
        else:
            recommendation = "strong_sell"
            timing = "urgent"
        
        return InvestmentRecommendation(
            location_name=location_name,
            overall_score=round(score, 1),
            recommendation=recommendation,
            timing=timing,
            expected_roi_5yr=round(roi_5yr, 1),
            risk_factors=risk_factors,
            positive_factors=positive_factors,
            comparable_areas=self._get_comparable_areas(area_type)
        )
    
    def _get_comparable_areas(self, area_type: str) -> List[str]:
        """Get comparable areas based on development stage."""
        comparables = {
            'emerging': ['Devanahalli', 'Sarjapur Road', 'Yelahanka'],
            'developing': ['Marathahalli', 'HSR Layout', 'BTM Layout'],
            'mature': ['Indiranagar', 'Koramangala', 'Jayanagar'],
            'saturated': ['MG Road', 'Brigade Road', 'Residency Road']
        }
        return comparables.get(area_type, ['Whitefield', 'Electronic City'])
    
    def get_full_analysis(self, lat: float, lng: float,
                         current_price: float = None,
                         location_name: str = None) -> Dict[str, Any]:
        """
        Get complete predictive analysis for a location.
        """
        prediction = self.predict_price(lat, lng, current_price, years=5)
        recommendation = self.get_investment_recommendation(lat, lng, current_price, location_name=location_name)
        cycle = self.analyze_market_cycle()
        
        return {
            "location": {
                "lat": lat,
                "lng": lng,
                "name": location_name or f"{lat:.4f}, {lng:.4f}"
            },
            "price_prediction": {
                "current": prediction.current_price,
                "predicted": prediction.predicted_prices,
                "confidence_intervals": prediction.confidence_intervals,
                "annual_growth": f"{prediction.annual_growth_rate}%",
                "risk": prediction.risk_level,
                "factors": prediction.factors
            },
            "investment": {
                "score": recommendation.overall_score,
                "recommendation": recommendation.recommendation.upper().replace('_', ' '),
                "timing": recommendation.timing,
                "expected_roi_5yr": f"{recommendation.expected_roi_5yr}%",
                "positive_factors": recommendation.positive_factors,
                "risk_factors": recommendation.risk_factors,
                "comparable_areas": recommendation.comparable_areas
            },
            "market_cycle": {
                "phase": cycle.current_phase,
                "position": f"{cycle.cycle_position * 100:.0f}%",
                "months_remaining": cycle.estimated_months_remaining,
                "recommendation": cycle.recommendation
            },
            "generated_at": datetime.now().isoformat(),
            "methodology": "Statistical forecasting with infrastructure adjustment"
        }


# Singleton instance
_predictive_model = None


def get_predictive_model() -> PredictiveModel:
    """Get or create predictive model singleton."""
    global _predictive_model
    if _predictive_model is None:
        _predictive_model = PredictiveModel()
    return _predictive_model
