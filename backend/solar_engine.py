"""
Valora AI - Solar Engine
Time-aware sun position and shadow analysis for Bangalore.

Features:
- Solar position by date, time, and season
- Shadow length and direction calculation
- Sunlight hours per floor/façade
- Morning vs evening sun exposure
- Seasonal sunlight comparison (winter vs summer)
- Natural light quality scoring
"""

import sqlite3
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta


# Bangalore coordinates
BANGALORE_LAT = 12.9716
BANGALORE_LNG = 77.5946


@dataclass
class SunPosition:
    """Sun position at a specific time."""
    datetime: datetime
    altitude: float  # Degrees above horizon (0-90)
    azimuth: float   # Degrees from North (0-360)
    is_daylight: bool
    
    @property
    def direction(self) -> str:
        """Cardinal direction of sun."""
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        index = round(self.azimuth / 45) % 8
        return directions[index]


@dataclass
class ShadowInfo:
    """Shadow cast by a building at a specific time."""
    time: datetime
    shadow_length_m: float
    shadow_direction: str  # Direction shadow points (opposite of sun)
    shadow_azimuth: float
    sun_altitude: float
    impact_severity: str  # low, medium, high


@dataclass
class SunlightAnalysis:
    """Complete sunlight analysis for a location."""
    location_lat: float
    location_lng: float
    floor: int
    date: date
    
    # Timeline
    sunrise: time
    sunset: time
    daylight_hours: float
    
    # Hourly sun positions
    hourly_sun: List[SunPosition] = field(default_factory=list)
    
    # Shadow impacts
    shadow_timeline: List[ShadowInfo] = field(default_factory=list)
    
    # Sunlight by direction
    sunlight_by_direction: Dict[str, float] = field(default_factory=dict)  # Direction -> hours
    
    # Comfort metrics
    morning_sun_quality: str = "unknown"  # good, moderate, poor
    evening_sun_quality: str = "unknown"
    best_sunlight_hours: List[int] = field(default_factory=list)
    
    # Summary
    natural_light_score: float = 0  # 0-100
    summary: str = ""


class SolarEngine:
    """
    Calculates sun position and shadow dynamics for Bangalore.
    Uses simplified solar position algorithm for offline operation.
    """
    
    # Bangalore location
    LATITUDE = 12.9716
    LONGITUDE = 77.5946
    TIMEZONE_OFFSET = 5.5  # IST = UTC+5:30
    
    # Floor height
    FLOOR_HEIGHT_M = 3.0
    
    # Directions
    DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
    
    def _calculate_sun_position(self, dt: datetime) -> SunPosition:
        """
        Calculate sun position using simplified algorithm.
        Based on NOAA Solar Calculator equations (simplified for offline use).
        """
        # Day of year
        day_of_year = dt.timetuple().tm_yday
        
        # Fractional year (radians)
        gamma = 2 * math.pi / 365 * (day_of_year - 1 + (dt.hour - 12) / 24)
        
        # Equation of time (minutes)
        eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) 
                          - 0.032077 * math.sin(gamma)
                          - 0.014615 * math.cos(2 * gamma) 
                          - 0.040849 * math.sin(2 * gamma))
        
        # Solar declination (radians)
        decl = 0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma) \
               - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma) \
               - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma)
        
        # Time offset (minutes)
        time_offset = eqtime + 4 * self.LONGITUDE - 60 * self.TIMEZONE_OFFSET
        
        # True solar time (minutes)
        tst = dt.hour * 60 + dt.minute + dt.second / 60 + time_offset
        
        # Hour angle (degrees)
        ha = (tst / 4) - 180
        
        # Solar zenith and altitude
        lat_rad = math.radians(self.LATITUDE)
        cos_zenith = (math.sin(lat_rad) * math.sin(decl) + 
                      math.cos(lat_rad) * math.cos(decl) * math.cos(math.radians(ha)))
        cos_zenith = max(-1, min(1, cos_zenith))
        zenith = math.degrees(math.acos(cos_zenith))
        altitude = 90 - zenith
        
        # Solar azimuth
        if altitude > 0:
            cos_azimuth = ((math.sin(decl) - math.sin(lat_rad) * math.cos(math.radians(zenith))) /
                          (math.cos(lat_rad) * math.sin(math.radians(zenith))))
            cos_azimuth = max(-1, min(1, cos_azimuth))
            azimuth = math.degrees(math.acos(cos_azimuth))
            
            if ha > 0:
                azimuth = 360 - azimuth
        else:
            azimuth = 0 if dt.hour < 12 else 180
        
        return SunPosition(
            datetime=dt,
            altitude=max(0, altitude),
            azimuth=azimuth,
            is_daylight=altitude > 0
        )
    
    def _calculate_sunrise_sunset(self, d: date) -> Tuple[time, time]:
        """Calculate sunrise and sunset times for a date."""
        # Simplified calculation for Bangalore
        # Sunrise varies ~6:00-6:30, Sunset varies ~6:00-6:45
        
        day_of_year = d.timetuple().tm_yday
        
        # Approximate variation (Bangalore is close to equator, small variation)
        # Summer: earlier sunrise, later sunset
        # Winter: later sunrise, earlier sunset
        
        # Offset from mean (minutes)
        offset = 15 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
        
        sunrise_minutes = 6 * 60 + 15 - offset  # ~6:00-6:30
        sunset_minutes = 18 * 60 + 15 + offset   # ~6:00-6:45
        
        sunrise = time(int(sunrise_minutes // 60), int(sunrise_minutes % 60))
        sunset = time(int(sunset_minutes // 60), int(sunset_minutes % 60))
        
        return sunrise, sunset
    
    def _get_shadow_direction(self, sun_azimuth: float) -> str:
        """Get direction shadow points (opposite of sun)."""
        shadow_azimuth = (sun_azimuth + 180) % 360
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        index = round(shadow_azimuth / 45) % 8
        return directions[index]
    
    def _calculate_shadow_length(self, building_height: float, sun_altitude: float) -> float:
        """Calculate shadow length from building height and sun altitude."""
        if sun_altitude <= 0:
            return 0
        return building_height / math.tan(math.radians(sun_altitude))
    
    def get_sun_position(self, dt: datetime = None) -> SunPosition:
        """Get current sun position."""
        if dt is None:
            dt = datetime.now()
        return self._calculate_sun_position(dt)
    
    def get_shadow_timeline(
        self,
        lat: float,
        lng: float,
        d: date = None,
        hours: List[int] = None
    ) -> List[ShadowInfo]:
        """
        Get shadow impact timeline for a location.
        
        Args:
            lat, lng: Location
            d: Date (defaults to today)
            hours: Hours to analyze (defaults to 6-18)
            
        Returns:
            List of shadow info for each hour
        """
        if d is None:
            d = date.today()
        if hours is None:
            hours = list(range(6, 19))  # 6 AM to 6 PM
        
        # Get nearby tall buildings that could cast shadows
        nearby_buildings = self._get_nearby_tall_buildings(lat, lng, radius_m=200)
        
        timeline = []
        for hour in hours:
            dt = datetime.combine(d, time(hour, 0))
            sun = self._calculate_sun_position(dt)
            
            if not sun.is_daylight:
                continue
            
            # Check shadow impact from nearby buildings
            max_impact = 0
            for bldg in nearby_buildings:
                shadow_len = self._calculate_shadow_length(bldg['height'], sun.altitude)
                
                # Check if shadow reaches our location
                # Simplified: check if building is in sun direction and close enough
                bldg_direction = self._get_direction_to(lat, lng, bldg['lat'], bldg['lng'])
                sun_dir = sun.direction
                
                # If building is roughly in sun's direction, shadow might hit us
                if self._directions_match(bldg_direction, sun_dir):
                    distance = self._haversine_distance(lat, lng, bldg['lat'], bldg['lng'])
                    if distance < shadow_len:
                        impact = min(100, (1 - distance / shadow_len) * 100)
                        max_impact = max(max_impact, impact)
            
            shadow_dir = self._get_shadow_direction(sun.azimuth)
            
            timeline.append(ShadowInfo(
                time=dt,
                shadow_length_m=0,  # This is for buildings casting shadow
                shadow_direction=shadow_dir,
                shadow_azimuth=(sun.azimuth + 180) % 360,
                sun_altitude=sun.altitude,
                impact_severity='high' if max_impact > 60 else 'medium' if max_impact > 30 else 'low'
            ))
        
        return timeline
    
    def _get_nearby_tall_buildings(self, lat: float, lng: float, radius_m: float) -> List[Dict]:
        """Get tall buildings that could cast shadows."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            radius_deg = radius_m / 111000
            
            cursor.execute("""
                SELECT osm_id, name, height, latitude, longitude
                FROM buildings
                WHERE height > 15
                AND latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                ORDER BY height DESC
                LIMIT 50
            """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
            
            buildings = []
            for row in cursor.fetchall():
                buildings.append({
                    'id': row['osm_id'],
                    'name': row['name'],
                    'height': row['height'],
                    'lat': row['latitude'],
                    'lng': row['longitude']
                })
            
            conn.close()
            return buildings
        except:
            return []
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in meters."""
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _get_direction_to(self, from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> str:
        """Get direction from one point to another."""
        dlat = to_lat - from_lat
        dlng = to_lng - from_lng
        angle = math.degrees(math.atan2(dlng, dlat))
        if angle < 0:
            angle += 360
        
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        index = round(angle / 45) % 8
        return directions[index]
    
    def _directions_match(self, dir1: str, dir2: str) -> bool:
        """Check if two directions are close (same or adjacent)."""
        idx1 = self.DIRECTIONS.index(dir1) if dir1 in self.DIRECTIONS else 0
        idx2 = self.DIRECTIONS.index(dir2) if dir2 in self.DIRECTIONS else 0
        diff = abs(idx1 - idx2)
        return diff <= 1 or diff >= 7  # Adjacent or same
    
    def analyze_sunlight(
        self,
        lat: float,
        lng: float,
        floor: int = 1,
        d: date = None
    ) -> SunlightAnalysis:
        """
        Comprehensive sunlight analysis for a location and floor.
        
        Args:
            lat, lng: Location
            floor: Floor number
            d: Date (defaults to today)
            
        Returns:
            SunlightAnalysis with complete sunlight data
        """
        if d is None:
            d = date.today()
        
        sunrise, sunset = self._calculate_sunrise_sunset(d)
        sunrise_dt = datetime.combine(d, sunrise)
        sunset_dt = datetime.combine(d, sunset)
        daylight_hours = (sunset_dt - sunrise_dt).total_seconds() / 3600
        
        analysis = SunlightAnalysis(
            location_lat=lat,
            location_lng=lng,
            floor=floor,
            date=d,
            sunrise=sunrise,
            sunset=sunset,
            daylight_hours=round(daylight_hours, 1)
        )
        
        # Get hourly sun positions
        sunlight_by_direction = {d: 0.0 for d in self.DIRECTIONS}
        best_hours = []
        
        for hour in range(6, 19):
            dt = datetime.combine(d, time(hour, 0))
            sun = self._calculate_sun_position(dt)
            analysis.hourly_sun.append(sun)
            
            if sun.is_daylight and sun.altitude > 10:
                # Good sunlight hour
                best_hours.append(hour)
                # Add sunlight to the direction sun is coming from
                sunlight_by_direction[sun.direction] += 1
        
        analysis.sunlight_by_direction = sunlight_by_direction
        analysis.best_sunlight_hours = best_hours
        
        # Get shadow timeline
        analysis.shadow_timeline = self.get_shadow_timeline(lat, lng, d)
        
        # Assess morning and evening sun
        morning_sun = [s for s in analysis.hourly_sun if 6 <= s.datetime.hour <= 10 and s.altitude > 15]
        evening_sun = [s for s in analysis.hourly_sun if 15 <= s.datetime.hour <= 18 and s.altitude > 10]
        
        analysis.morning_sun_quality = 'good' if len(morning_sun) >= 3 else 'moderate' if len(morning_sun) >= 2 else 'poor'
        analysis.evening_sun_quality = 'good' if len(evening_sun) >= 2 else 'moderate' if len(evening_sun) >= 1 else 'poor'
        
        # Natural light score
        shadow_impacts = [s for s in analysis.shadow_timeline if s.impact_severity == 'high']
        base_score = 70 + (floor * 2)  # Higher floors get more light
        shadow_penalty = len(shadow_impacts) * 10
        direction_bonus = sum(1 for h in sunlight_by_direction.values() if h >= 2) * 5
        
        analysis.natural_light_score = min(100, max(0, base_score - shadow_penalty + direction_bonus))
        
        # Summary
        if analysis.natural_light_score >= 80:
            analysis.summary = f"Excellent natural light. {len(best_hours)} hours of good sunlight. Best: {analysis.morning_sun_quality} morning, {analysis.evening_sun_quality} evening sun."
        elif analysis.natural_light_score >= 60:
            analysis.summary = f"Good natural light with some shadow periods. Morning sun: {analysis.morning_sun_quality}."
        elif analysis.natural_light_score >= 40:
            analysis.summary = f"Moderate natural light. Consider higher floors for better exposure."
        else:
            analysis.summary = f"Limited natural light due to surrounding buildings. Floor {floor + 5}+ recommended."
        
        return analysis
    
    def compare_seasons(
        self,
        lat: float,
        lng: float,
        floor: int = 1
    ) -> Dict[str, Any]:
        """
        Compare sunlight across seasons (winter vs summer).
        
        Args:
            lat, lng: Location
            floor: Floor number
            
        Returns:
            Dict with seasonal comparison
        """
        # Summer solstice (June 21) and Winter solstice (Dec 21)
        current_year = datetime.now().year
        summer = date(current_year, 6, 21)
        winter = date(current_year, 12, 21)
        equinox = date(current_year, 3, 21)
        
        summer_analysis = self.analyze_sunlight(lat, lng, floor, summer)
        winter_analysis = self.analyze_sunlight(lat, lng, floor, winter)
        equinox_analysis = self.analyze_sunlight(lat, lng, floor, equinox)
        
        return {
            'summer': {
                'date': str(summer),
                'daylight_hours': summer_analysis.daylight_hours,
                'sunrise': str(summer_analysis.sunrise),
                'sunset': str(summer_analysis.sunset),
                'natural_light_score': summer_analysis.natural_light_score,
                'best_directions': [d for d, h in summer_analysis.sunlight_by_direction.items() if h >= 2]
            },
            'winter': {
                'date': str(winter),
                'daylight_hours': winter_analysis.daylight_hours,
                'sunrise': str(winter_analysis.sunrise),
                'sunset': str(winter_analysis.sunset),
                'natural_light_score': winter_analysis.natural_light_score,
                'best_directions': [d for d, h in winter_analysis.sunlight_by_direction.items() if h >= 2]
            },
            'equinox': {
                'date': str(equinox),
                'daylight_hours': equinox_analysis.daylight_hours,
                'natural_light_score': equinox_analysis.natural_light_score
            },
            'recommendation': self._generate_season_recommendation(summer_analysis, winter_analysis),
            'floor': floor
        }
    
    def _generate_season_recommendation(
        self,
        summer: SunlightAnalysis,
        winter: SunlightAnalysis
    ) -> str:
        """Generate seasonal recommendation."""
        if summer.natural_light_score >= 70 and winter.natural_light_score >= 60:
            return "Year-round good natural light. Suitable for all seasons."
        elif summer.natural_light_score >= 70:
            return "Excellent summer light but reduced in winter. East-facing rooms preferred for winter mornings."
        elif winter.natural_light_score >= 60:
            return "Good winter light. Consider shading for summer afternoons."
        else:
            return "Limited natural light year-round. Higher floors or different orientation recommended."
    
    def get_facade_sunlight(
        self,
        lat: float,
        lng: float,
        floor: int = 1,
        d: date = None
    ) -> Dict[str, Any]:
        """
        Get sunlight hours by facade direction.
        
        Args:
            lat, lng: Building location
            floor: Floor number
            d: Date
            
        Returns:
            Dict with sunlight hours per facade
        """
        analysis = self.analyze_sunlight(lat, lng, floor, d)
        
        facades = {}
        for direction in ['N', 'E', 'S', 'W']:
            hours = analysis.sunlight_by_direction.get(direction, 0)
            
            # Also add adjacent directions
            adjacent = {
                'N': ['NE', 'NW'], 'E': ['NE', 'SE'],
                'S': ['SE', 'SW'], 'W': ['NW', 'SW']
            }
            for adj in adjacent.get(direction, []):
                hours += analysis.sunlight_by_direction.get(adj, 0) * 0.5
            
            facades[direction] = {
                'direct_sunlight_hours': round(hours, 1),
                'quality': 'excellent' if hours >= 4 else 'good' if hours >= 2 else 'limited',
                'best_time': self._get_best_time_for_direction(direction)
            }
        
        best_facade = max(facades.keys(), key=lambda d: facades[d]['direct_sunlight_hours'])
        
        return {
            'facades': facades,
            'best_facade': best_facade,
            'floor': floor,
            'date': str(d or date.today()),
            'recommendation': f"{best_facade}-facing rooms get the most natural light ({facades[best_facade]['direct_sunlight_hours']}h)."
        }
    
    def _get_best_time_for_direction(self, direction: str) -> str:
        """Get best sunlight time for a facade direction."""
        times = {
            'E': 'Morning (6-10 AM)',
            'W': 'Afternoon (2-6 PM)',
            'N': 'Diffused light (year-round)',
            'S': 'Midday (10 AM - 2 PM)'
        }
        return times.get(direction, 'Variable')


# Singleton
_solar_engine = None


def get_solar_engine() -> SolarEngine:
    """Get or create solar engine singleton."""
    global _solar_engine
    if _solar_engine is None:
        _solar_engine = SolarEngine()
    return _solar_engine
