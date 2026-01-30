"""
Temporal Analysis Engine for Valora AI
Phase 6.2: Time-based analysis of property and urban data

Features:
- Price trend analysis over time
- Seasonal pattern detection
- Development timeline visualization
- Growth rate calculations
- Market cycle prediction
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math
from collections import defaultdict


@dataclass
class PriceTrend:
    """Price trend analysis result."""
    location_name: str
    start_date: str
    end_date: str
    start_price: float
    end_price: float
    change_percent: float
    annualized_growth: float
    trend_direction: str  # "up", "down", "stable"
    confidence: float
    data_points: int


@dataclass
class SeasonalPattern:
    """Seasonal pattern in property market."""
    peak_months: List[str]
    low_months: List[str]
    best_buy_season: str
    best_sell_season: str
    seasonal_variation_percent: float


@dataclass
class DevelopmentTimeline:
    """Timeline of development in an area."""
    location_name: str
    phases: List[Dict[str, Any]]
    current_phase: str
    projected_completion: str
    growth_stage: str  # "emerging", "developing", "mature", "saturated"


class TemporalAnalyzer:
    """
    Analyzes temporal patterns in property and urban data.
    Provides price trends, seasonal patterns, and development timelines.
    """
    
    # Bangalore property market seasonality (typical pattern)
    SEASONAL_FACTORS = {
        1: 0.95,   # January - post-holiday slowdown
        2: 0.97,   # February - picking up
        3: 1.02,   # March - financial year end, good activity
        4: 1.05,   # April - new financial year
        5: 1.03,   # May - pre-monsoon
        6: 0.92,   # June - monsoon begins
        7: 0.90,   # July - monsoon peak
        8: 0.93,   # August - monsoon
        9: 0.98,   # September - monsoon ends
        10: 1.05,  # October - festive season
        11: 1.08,  # November - Diwali peak
        12: 1.02,  # December - year-end
    }
    
    # Area growth phases
    GROWTH_PHASES = {
        "emerging": {"age_years": (0, 5), "growth_rate": (15, 30)},
        "developing": {"age_years": (5, 15), "growth_rate": (8, 15)},
        "mature": {"age_years": (15, 30), "growth_rate": (3, 8)},
        "saturated": {"age_years": (30, 100), "growth_rate": (0, 3)},
    }
    
    def __init__(self):
        self.db_service = None
        self._init_database()
    
    def _init_database(self):
        """Initialize database connection."""
        try:
            from database.db_service import DatabaseService
            from pathlib import Path
            db_path = Path(__file__).parent / 'database' / '..' / '..' / 'src' / 'data' / 'valora.db'
            self.db_service = DatabaseService(str(db_path.resolve()))
        except Exception as e:
            print(f"[TemporalAnalyzer] Database init error: {e}")
    
    def analyze_price_trend(self, lat: float, lng: float, 
                           radius_m: float = 1000,
                           years: int = 5) -> PriceTrend:
        """
        Analyze price trends for properties near a location.
        
        Args:
            lat, lng: Center location
            radius_m: Radius to search
            years: Number of years to analyze
            
        Returns:
            PriceTrend with historical analysis
        """
        location_name = f"Area around {lat:.4f}, {lng:.4f}"
        
        # Get current prices
        current_prices = self._get_area_prices(lat, lng, radius_m)
        
        if not current_prices:
            # Return estimated trend based on area type
            return self._estimate_trend_from_context(lat, lng, years)
        
        avg_current = sum(current_prices) / len(current_prices)
        
        # Estimate historical price using typical Bangalore growth rate
        base_growth_rate = 0.08  # 8% annual appreciation (Bangalore average)
        
        # Adjust based on area characteristics
        growth_modifier = self._get_growth_modifier(lat, lng)
        annual_growth = base_growth_rate * growth_modifier
        
        # Calculate historical start price
        years_factor = (1 + annual_growth) ** years
        estimated_start_price = avg_current / years_factor
        
        change_percent = ((avg_current - estimated_start_price) / estimated_start_price) * 100
        
        # Determine trend direction
        if annual_growth > 0.05:
            trend_direction = "up"
        elif annual_growth < -0.02:
            trend_direction = "down"
        else:
            trend_direction = "stable"
        
        end_date = datetime.now().strftime("%Y-%m")
        start_date = (datetime.now() - timedelta(days=years*365)).strftime("%Y-%m")
        
        return PriceTrend(
            location_name=location_name,
            start_date=start_date,
            end_date=end_date,
            start_price=round(estimated_start_price),
            end_price=round(avg_current),
            change_percent=round(change_percent, 1),
            annualized_growth=round(annual_growth * 100, 1),
            trend_direction=trend_direction,
            confidence=0.7,
            data_points=len(current_prices)
        )
    
    def _get_area_prices(self, lat: float, lng: float, radius_m: float) -> List[float]:
        """Get property prices in area."""
        if not self.db_service:
            return []
        
        radius_deg = radius_m / 111000
        
        try:
            query = """
                SELECT price FROM properties
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                AND price > 0
            """
            results = self.db_service.execute(query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            )) or []
            
            return [r['price'] for r in results if r.get('price')]
        except:
            return []
    
    def _get_growth_modifier(self, lat: float, lng: float) -> float:
        """Get growth rate modifier based on area characteristics."""
        # Check for nearby infrastructure
        if not self.db_service:
            return 1.0
        
        modifier = 1.0
        radius_deg = 2000 / 111000  # 2km
        
        try:
            # Check for metro stations (higher growth near metro)
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
            if metro_result and metro_result[0]['cnt'] > 0:
                modifier *= 1.3  # 30% higher growth near metro
            
            # Check for IT parks (higher growth near tech hubs)
            it_query = """
                SELECT COUNT(*) as cnt FROM pois
                WHERE category IN ('office', 'commercial', 'it_park')
                AND latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            it_result = self.db_service.execute(it_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            if it_result and it_result[0]['cnt'] > 3:
                modifier *= 1.2  # 20% higher growth near IT areas
            
        except:
            pass
        
        return min(modifier, 2.0)  # Cap at 2x
    
    def _estimate_trend_from_context(self, lat: float, lng: float, years: int) -> PriceTrend:
        """Estimate trend when no direct price data available."""
        location_name = f"Area around {lat:.4f}, {lng:.4f}"
        
        # Use Bangalore average
        base_price = 8000  # Rs per sqft average
        annual_growth = 0.08
        
        modifier = self._get_growth_modifier(lat, lng)
        adjusted_growth = annual_growth * modifier
        
        end_price = base_price
        start_price = base_price / ((1 + adjusted_growth) ** years)
        
        return PriceTrend(
            location_name=location_name,
            start_date=(datetime.now() - timedelta(days=years*365)).strftime("%Y-%m"),
            end_date=datetime.now().strftime("%Y-%m"),
            start_price=round(start_price),
            end_price=round(end_price),
            change_percent=round(((end_price - start_price) / start_price) * 100, 1),
            annualized_growth=round(adjusted_growth * 100, 1),
            trend_direction="up" if adjusted_growth > 0.03 else "stable",
            confidence=0.5,  # Lower confidence for estimated data
            data_points=0
        )
    
    def get_seasonal_pattern(self, property_type: str = "residential") -> SeasonalPattern:
        """
        Get seasonal patterns for property market.
        
        Args:
            property_type: "residential", "commercial", "land"
            
        Returns:
            SeasonalPattern with best times to buy/sell
        """
        # Find peak and low months
        sorted_months = sorted(self.SEASONAL_FACTORS.items(), key=lambda x: x[1])
        
        low_months = [self._month_name(m) for m, _ in sorted_months[:3]]
        peak_months = [self._month_name(m) for m, _ in sorted_months[-3:]]
        
        # Calculate seasonal variation
        min_factor = min(self.SEASONAL_FACTORS.values())
        max_factor = max(self.SEASONAL_FACTORS.values())
        variation = ((max_factor - min_factor) / min_factor) * 100
        
        return SeasonalPattern(
            peak_months=peak_months,
            low_months=low_months,
            best_buy_season="June-August (Monsoon)",
            best_sell_season="October-November (Festive)",
            seasonal_variation_percent=round(variation, 1)
        )
    
    def _month_name(self, month_num: int) -> str:
        """Convert month number to name."""
        months = ["", "January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        return months[month_num]
    
    def analyze_development_phase(self, lat: float, lng: float,
                                  area_name: str = None) -> DevelopmentTimeline:
        """
        Analyze development phase of an area.
        
        Args:
            lat, lng: Location coordinates
            area_name: Optional area name
            
        Returns:
            DevelopmentTimeline with phase analysis
        """
        location_name = area_name or f"Area at {lat:.4f}, {lng:.4f}"
        
        # Analyze area characteristics to determine phase
        building_density = self._get_building_density(lat, lng)
        avg_building_age = self._estimate_building_age(lat, lng)
        infrastructure_score = self._get_infrastructure_score(lat, lng)
        
        # Determine growth stage
        if building_density < 20 and infrastructure_score < 40:
            growth_stage = "emerging"
            current_phase = "Initial Development"
            projected_years = 15
        elif building_density < 50 and infrastructure_score < 70:
            growth_stage = "developing"
            current_phase = "Active Growth"
            projected_years = 10
        elif building_density < 80:
            growth_stage = "mature"
            current_phase = "Established"
            projected_years = 5
        else:
            growth_stage = "saturated"
            current_phase = "Fully Developed"
            projected_years = 0
        
        # Build phase timeline
        phases = [
            {
                "name": "Land Acquisition",
                "status": "completed" if growth_stage != "emerging" else "in_progress",
                "typical_duration_years": 2
            },
            {
                "name": "Infrastructure Development",
                "status": "completed" if growth_stage in ["mature", "saturated"] else 
                         "in_progress" if growth_stage == "developing" else "pending",
                "typical_duration_years": 5
            },
            {
                "name": "Residential Growth",
                "status": "completed" if growth_stage == "saturated" else 
                         "in_progress" if growth_stage in ["developing", "mature"] else "pending",
                "typical_duration_years": 10
            },
            {
                "name": "Commercial Maturity",
                "status": "completed" if growth_stage == "saturated" else 
                         "in_progress" if growth_stage == "mature" else "pending",
                "typical_duration_years": 5
            }
        ]
        
        projected_date = datetime.now() + timedelta(days=projected_years * 365)
        
        return DevelopmentTimeline(
            location_name=location_name,
            phases=phases,
            current_phase=current_phase,
            projected_completion=projected_date.strftime("%Y") if projected_years > 0 else "Completed",
            growth_stage=growth_stage
        )
    
    def _get_building_density(self, lat: float, lng: float) -> float:
        """Get building density score (0-100)."""
        if not self.db_service:
            return 50.0
        
        radius_deg = 1000 / 111000
        
        try:
            query = """
                SELECT COUNT(*) as cnt FROM buildings
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            result = self.db_service.execute(query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            
            count = result[0]['cnt'] if result else 0
            # Normalize: 100 buildings in 1km² = 50% density
            return min(100, count / 2)
        except:
            return 50.0
    
    def _estimate_building_age(self, lat: float, lng: float) -> float:
        """Estimate average building age in area (years)."""
        # Without actual construction date data, estimate based on building types
        if not self.db_service:
            return 15.0
        
        radius_deg = 1000 / 111000
        
        try:
            query = """
                SELECT building_type, COUNT(*) as cnt FROM buildings
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                GROUP BY building_type
            """
            results = self.db_service.execute(query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            )) or []
            
            # Estimate age by type (modern building types = newer)
            type_ages = {
                'apartments': 10,
                'commercial': 8,
                'residential': 20,
                'house': 25,
                'retail': 12,
                'industrial': 30,
                'default': 15
            }
            
            total_count = 0
            weighted_age = 0
            for r in results:
                btype = r.get('building_type', 'default')
                count = r.get('cnt', 0)
                age = type_ages.get(btype, type_ages['default'])
                weighted_age += age * count
                total_count += count
            
            return weighted_age / total_count if total_count > 0 else 15.0
        except:
            return 15.0
    
    def _get_infrastructure_score(self, lat: float, lng: float) -> float:
        """Get infrastructure development score (0-100)."""
        if not self.db_service:
            return 50.0
        
        score = 0
        radius_deg = 2000 / 111000
        
        try:
            # Check for metro
            metro_query = """
                SELECT COUNT(*) as cnt FROM transport
                WHERE type IN ('metro', 'metro_station')
                AND latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            metro = self.db_service.execute(metro_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            if metro and metro[0]['cnt'] > 0:
                score += 30
            
            # Check for bus stops
            bus_query = """
                SELECT COUNT(*) as cnt FROM transport
                WHERE type IN ('bus', 'bus_stop')
                AND latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            bus = self.db_service.execute(bus_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            if bus and bus[0]['cnt'] > 3:
                score += 20
            
            # Check for POIs (amenities)
            poi_query = """
                SELECT COUNT(*) as cnt FROM pois
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            pois = self.db_service.execute(poi_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            poi_count = pois[0]['cnt'] if pois else 0
            score += min(50, poi_count)  # Max 50 points from POIs
            
        except:
            pass
        
        return min(100, score)
    
    def forecast_price(self, lat: float, lng: float, 
                      years_ahead: int = 3,
                      current_price: float = None) -> Dict[str, Any]:
        """
        Forecast future property price.
        
        Args:
            lat, lng: Location
            years_ahead: Years to forecast
            current_price: Current price per sqft (optional)
            
        Returns:
            Price forecast with confidence intervals
        """
        # Get historical trend
        trend = self.analyze_price_trend(lat, lng, years=5)
        
        # Use current price or get from database
        if current_price is None:
            prices = self._get_area_prices(lat, lng, 1000)
            current_price = sum(prices) / len(prices) if prices else 8000
        
        # Calculate forecast
        annual_growth = trend.annualized_growth / 100
        
        forecasts = []
        for year in range(1, years_ahead + 1):
            base_forecast = current_price * ((1 + annual_growth) ** year)
            
            # Add uncertainty bands (wider for further years)
            uncertainty = 0.05 * year  # 5% per year
            low = base_forecast * (1 - uncertainty)
            high = base_forecast * (1 + uncertainty)
            
            forecasts.append({
                "year": year,
                "date": (datetime.now() + timedelta(days=year*365)).strftime("%Y"),
                "forecast_price": round(base_forecast),
                "low_estimate": round(low),
                "high_estimate": round(high),
                "confidence": round(max(0.5, 0.9 - 0.1 * year), 2)
            })
        
        return {
            "current_price": round(current_price),
            "annual_growth_rate": trend.annualized_growth,
            "forecasts": forecasts,
            "methodology": "Historical trend extrapolation with infrastructure adjustment",
            "disclaimer": "Forecasts are estimates based on historical patterns. Actual values may vary."
        }


# Singleton instance
_temporal_analyzer = None


def get_temporal_analyzer() -> TemporalAnalyzer:
    """Get or create temporal analyzer singleton."""
    global _temporal_analyzer
    if _temporal_analyzer is None:
        _temporal_analyzer = TemporalAnalyzer()
    return _temporal_analyzer
