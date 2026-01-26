"""
Real-Time Data Service for Valora AI
Phase 4.1: Live data integration (offline-compatible)

Features:
- Traffic condition estimation (using local data patterns)
- Weather impact modeling (seasonal patterns)
- Construction activity tracking
- Recent transaction tracking
- Time-of-day activity patterns

Note: This is designed for OFFLINE operation.
Uses local patterns and estimations when external APIs unavailable.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math
import json
from pathlib import Path


@dataclass
class TrafficCondition:
    """Current traffic condition estimate."""
    location_name: str
    lat: float
    lng: float
    congestion_level: str  # low, moderate, high, severe
    congestion_score: float  # 0-100
    estimated_delay_min: float
    peak_hours: bool
    typical_for_time: bool
    nearby_hotspots: List[str] = field(default_factory=list)


@dataclass
class WeatherImpact:
    """Weather impact on property/area."""
    season: str  # summer, monsoon, winter, spring
    current_conditions: str  # sunny, cloudy, rainy, stormy
    temperature_range: Tuple[float, float]
    humidity_level: str  # low, moderate, high
    flood_risk: str  # none, low, moderate, high
    air_quality: str  # good, moderate, poor, hazardous
    impact_on_property: Dict[str, str] = field(default_factory=dict)


@dataclass
class ConstructionActivity:
    """Construction activity in area."""
    location_name: str
    active_projects: int
    project_types: List[str]
    estimated_completion: str
    noise_impact: str  # none, low, moderate, high
    traffic_impact: str
    future_value_impact: str  # positive, neutral, negative


class RealTimeDataService:
    """
    Provides real-time data estimates using local patterns.
    Works fully offline using historical patterns and estimations.
    """
    
    # Bangalore traffic patterns by hour (0-23)
    TRAFFIC_PATTERNS = {
        0: 0.1, 1: 0.05, 2: 0.05, 3: 0.05, 4: 0.1, 5: 0.2,
        6: 0.4, 7: 0.7, 8: 0.9, 9: 1.0, 10: 0.8, 11: 0.7,
        12: 0.6, 13: 0.6, 14: 0.6, 15: 0.7, 16: 0.8, 17: 0.95,
        18: 1.0, 19: 0.9, 20: 0.7, 21: 0.5, 22: 0.3, 23: 0.2
    }
    
    # Traffic hotspots in Bangalore (known congestion areas)
    TRAFFIC_HOTSPOTS = {
        'silk_board': (12.9177, 77.6238),
        'kr_puram': (13.0012, 77.6855),
        'marathahalli': (12.9591, 77.6971),
        'hebbal': (13.0358, 77.5970),
        'electronic_city': (12.8399, 77.6770),
        'whitefield': (12.9698, 77.7500),
        'koramangala': (12.9352, 77.6245),
        'indiranagar': (12.9716, 77.6412),
        'mg_road': (12.9758, 77.6045),
        'majestic': (12.9767, 77.5713)
    }
    
    # Bangalore seasonal patterns
    SEASONS = {
        (3, 4, 5): 'summer',      # March-May
        (6, 7, 8, 9): 'monsoon',  # June-September
        (10, 11): 'post_monsoon', # October-November
        (12, 1, 2): 'winter'      # December-February
    }
    
    # Temperature ranges by season (Bangalore)
    TEMPERATURE_RANGES = {
        'summer': (25, 38),
        'monsoon': (20, 28),
        'post_monsoon': (18, 28),
        'winter': (15, 27)
    }
    
    def __init__(self):
        self.db_service = None
        self._init_database()
        
        # Cache for recent queries
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes
    
    def _init_database(self):
        """Initialize database connection."""
        try:
            from database.db_service import DatabaseService
            db_path = Path(__file__).parent / 'database' / '..' / '..' / 'src' / 'data' / 'valora.db'
            self.db_service = DatabaseService(str(db_path.resolve()))
        except Exception as e:
            print(f"[RealTimeDataService] Database init error: {e}")
    
    def get_traffic_conditions(self, lat: float, lng: float, 
                               location_name: str = None) -> TrafficCondition:
        """
        Get estimated traffic conditions for a location.
        Uses time-of-day patterns and proximity to known hotspots.
        """
        now = datetime.now()
        hour = now.hour
        
        # Base congestion from time pattern
        base_congestion = self.TRAFFIC_PATTERNS.get(hour, 0.5)
        
        # Adjust for day of week (weekends are lighter)
        if now.weekday() >= 5:  # Saturday, Sunday
            base_congestion *= 0.6
        
        # Check proximity to traffic hotspots
        nearby_hotspots = []
        hotspot_factor = 0
        
        for name, (h_lat, h_lng) in self.TRAFFIC_HOTSPOTS.items():
            dist = self._haversine_distance(lat, lng, h_lat, h_lng)
            if dist < 2000:  # Within 2km
                nearby_hotspots.append(name.replace('_', ' ').title())
                # Closer = more impact
                hotspot_factor += (1 - dist / 2000) * 0.3
        
        # Calculate final congestion
        congestion_score = min(100, (base_congestion + hotspot_factor) * 100)
        
        # Determine level
        if congestion_score < 25:
            level = "low"
        elif congestion_score < 50:
            level = "moderate"
        elif congestion_score < 75:
            level = "high"
        else:
            level = "severe"
        
        # Estimate delay
        delay_min = congestion_score * 0.3  # Rough estimate
        
        # Is this peak hours?
        peak_hours = hour in [8, 9, 17, 18, 19]
        
        return TrafficCondition(
            location_name=location_name or f"Location {lat:.4f}, {lng:.4f}",
            lat=lat,
            lng=lng,
            congestion_level=level,
            congestion_score=round(congestion_score, 1),
            estimated_delay_min=round(delay_min, 1),
            peak_hours=peak_hours,
            typical_for_time=True,  # We're using typical patterns
            nearby_hotspots=nearby_hotspots
        )
    
    def get_weather_impact(self, lat: float, lng: float) -> WeatherImpact:
        """
        Get weather impact estimation for location.
        Uses seasonal patterns for Bangalore.
        """
        now = datetime.now()
        month = now.month
        
        # Determine season
        season = 'post_monsoon'
        for months, s in self.SEASONS.items():
            if month in months:
                season = s
                break
        
        # Get temperature range
        temp_range = self.TEMPERATURE_RANGES.get(season, (20, 30))
        
        # Estimate current conditions based on season
        if season == 'monsoon':
            conditions = "rainy"
            humidity = "high"
            flood_risk = self._estimate_flood_risk(lat, lng)
            air_quality = "moderate"
        elif season == 'summer':
            conditions = "sunny"
            humidity = "moderate"
            flood_risk = "none"
            air_quality = "moderate"
        elif season == 'winter':
            conditions = "pleasant"
            humidity = "low"
            flood_risk = "none"
            air_quality = "good"
        else:
            conditions = "cloudy"
            humidity = "moderate"
            flood_risk = "low"
            air_quality = "good"
        
        # Impact on property
        impacts = {}
        if season == 'monsoon':
            impacts['exterior'] = "Check for water seepage"
            impacts['roads'] = "May be waterlogged"
            impacts['viewing'] = "Carry umbrella"
        elif season == 'summer':
            impacts['comfort'] = "AC essential"
            impacts['water'] = "Check water supply"
            impacts['viewing'] = "Best in morning/evening"
        else:
            impacts['viewing'] = "Good time to visit"
            impacts['comfort'] = "Pleasant weather"
        
        return WeatherImpact(
            season=season,
            current_conditions=conditions,
            temperature_range=temp_range,
            humidity_level=humidity,
            flood_risk=flood_risk,
            air_quality=air_quality,
            impact_on_property=impacts
        )
    
    def _estimate_flood_risk(self, lat: float, lng: float) -> str:
        """Estimate flood risk based on location."""
        # Known low-lying areas in Bangalore (simplified)
        flood_prone_areas = [
            (12.9177, 77.6238, 'silk_board'),
            (12.9352, 77.6245, 'koramangala_low'),
            (13.0358, 77.5970, 'hebbal_lake'),
        ]
        
        for f_lat, f_lng, _ in flood_prone_areas:
            dist = self._haversine_distance(lat, lng, f_lat, f_lng)
            if dist < 1000:
                return "moderate"
            elif dist < 2000:
                return "low"
        
        return "none"
    
    def get_construction_activity(self, lat: float, lng: float,
                                  radius_m: float = 1000) -> ConstructionActivity:
        """
        Get construction activity in area.
        Estimates based on building data and area development stage.
        """
        location_name = f"Area around {lat:.4f}, {lng:.4f}"
        
        # Check database for recent buildings or development indicators
        active_projects = 0
        project_types = []
        
        if self.db_service:
            radius_deg = radius_m / 111000
            
            try:
                # Count new-looking buildings (high-rise, apartments)
                query = """
                    SELECT building_type, COUNT(*) as cnt FROM buildings
                    WHERE latitude BETWEEN ? AND ?
                    AND longitude BETWEEN ? AND ?
                    AND building_type IN ('apartments', 'commercial', 'construction')
                    GROUP BY building_type
                """
                results = self.db_service.execute(query, (
                    lat - radius_deg, lat + radius_deg,
                    lng - radius_deg, lng + radius_deg
                )) or []
                
                for r in results:
                    if r['cnt'] > 5:
                        project_types.append(r['building_type'])
                        active_projects += 1
                
            except:
                pass
        
        # Estimate development stage
        if active_projects > 3:
            noise_impact = "moderate"
            traffic_impact = "moderate"
            future_value = "positive"
            completion = "Ongoing development"
        elif active_projects > 0:
            noise_impact = "low"
            traffic_impact = "low"
            future_value = "positive"
            completion = "Limited activity"
        else:
            noise_impact = "none"
            traffic_impact = "none"
            future_value = "neutral"
            completion = "Stable area"
        
        return ConstructionActivity(
            location_name=location_name,
            active_projects=active_projects,
            project_types=project_types if project_types else ["general"],
            estimated_completion=completion,
            noise_impact=noise_impact,
            traffic_impact=traffic_impact,
            future_value_impact=future_value
        )
    
    def get_activity_pattern(self, lat: float, lng: float,
                            activity_type: str = "general") -> Dict[str, Any]:
        """
        Get activity patterns for a location throughout the day.
        
        Args:
            lat, lng: Location coordinates
            activity_type: "residential", "commercial", "general"
            
        Returns:
            Activity pattern data
        """
        # Base patterns
        if activity_type == "commercial":
            # Commercial areas peak during work hours
            pattern = {
                'morning': {'level': 'high', 'hours': '9am-12pm'},
                'afternoon': {'level': 'high', 'hours': '12pm-5pm'},
                'evening': {'level': 'moderate', 'hours': '5pm-8pm'},
                'night': {'level': 'low', 'hours': '8pm-9am'},
                'peak_activity': '10am-2pm',
                'quiet_time': 'after 8pm'
            }
        elif activity_type == "residential":
            # Residential areas have morning/evening activity
            pattern = {
                'morning': {'level': 'moderate', 'hours': '6am-9am'},
                'afternoon': {'level': 'low', 'hours': '9am-4pm'},
                'evening': {'level': 'high', 'hours': '5pm-9pm'},
                'night': {'level': 'quiet', 'hours': '9pm-6am'},
                'peak_activity': '6pm-8pm',
                'quiet_time': '10am-4pm'
            }
        else:
            # Mixed pattern
            pattern = {
                'morning': {'level': 'moderate', 'hours': '7am-12pm'},
                'afternoon': {'level': 'moderate', 'hours': '12pm-5pm'},
                'evening': {'level': 'high', 'hours': '5pm-9pm'},
                'night': {'level': 'low', 'hours': '9pm-7am'},
                'peak_activity': '6pm-8pm',
                'quiet_time': 'late night'
            }
        
        # Add current status
        hour = datetime.now().hour
        if 9 <= hour < 17:
            current_period = "business_hours"
        elif 17 <= hour < 21:
            current_period = "evening"
        elif 6 <= hour < 9:
            current_period = "morning"
        else:
            current_period = "night"
        
        pattern['current_period'] = current_period
        pattern['current_time'] = datetime.now().strftime('%H:%M')
        
        return pattern
    
    def get_comprehensive_snapshot(self, lat: float, lng: float,
                                   location_name: str = None) -> Dict[str, Any]:
        """
        Get comprehensive real-time snapshot of a location.
        Combines traffic, weather, construction, and activity data.
        """
        traffic = self.get_traffic_conditions(lat, lng, location_name)
        weather = self.get_weather_impact(lat, lng)
        construction = self.get_construction_activity(lat, lng)
        activity = self.get_activity_pattern(lat, lng)
        
        # Calculate overall livability score
        livability_factors = []
        
        # Traffic impact
        if traffic.congestion_level == 'low':
            livability_factors.append(90)
        elif traffic.congestion_level == 'moderate':
            livability_factors.append(70)
        elif traffic.congestion_level == 'high':
            livability_factors.append(50)
        else:
            livability_factors.append(30)
        
        # Weather/air quality
        if weather.air_quality == 'good':
            livability_factors.append(90)
        elif weather.air_quality == 'moderate':
            livability_factors.append(70)
        else:
            livability_factors.append(50)
        
        # Flood risk
        if weather.flood_risk == 'none':
            livability_factors.append(100)
        elif weather.flood_risk == 'low':
            livability_factors.append(80)
        else:
            livability_factors.append(60)
        
        # Construction noise
        if construction.noise_impact == 'none':
            livability_factors.append(100)
        elif construction.noise_impact == 'low':
            livability_factors.append(85)
        else:
            livability_factors.append(65)
        
        livability_score = sum(livability_factors) / len(livability_factors)
        
        return {
            "location": {
                "lat": lat,
                "lng": lng,
                "name": location_name
            },
            "timestamp": datetime.now().isoformat(),
            "traffic": {
                "level": traffic.congestion_level,
                "score": traffic.congestion_score,
                "delay_min": traffic.estimated_delay_min,
                "peak_hours": traffic.peak_hours,
                "hotspots": traffic.nearby_hotspots
            },
            "weather": {
                "season": weather.season,
                "conditions": weather.current_conditions,
                "temperature": weather.temperature_range,
                "humidity": weather.humidity_level,
                "air_quality": weather.air_quality,
                "flood_risk": weather.flood_risk
            },
            "construction": {
                "active_projects": construction.active_projects,
                "noise_impact": construction.noise_impact,
                "future_value": construction.future_value_impact
            },
            "activity": activity,
            "livability_score": round(livability_score, 1),
            "data_source": "local_patterns",
            "note": "Estimates based on typical Bangalore patterns (offline mode)"
        }
    
    def _haversine_distance(self, lat1: float, lon1: float, 
                           lat2: float, lon2: float) -> float:
        """Calculate distance in meters between two points."""
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c


# Singleton instance
_realtime_service = None


def get_realtime_data_service() -> RealTimeDataService:
    """Get or create real-time data service singleton."""
    global _realtime_service
    if _realtime_service is None:
        _realtime_service = RealTimeDataService()
    return _realtime_service
