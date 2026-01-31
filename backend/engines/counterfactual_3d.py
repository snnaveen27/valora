"""
Valora AI - Counterfactual 3D Impact Analysis
What-if scenarios with true 3D spatial impacts.

Features:
- Infrastructure addition impact on views/shadows
- Building height change simulations
- Density change scenarios
- View corridor preservation analysis
- Shadow impact on surrounding properties
"""

import sqlite3
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ImpactedProperty:
    """A property impacted by a counterfactual scenario."""
    property_id: str
    property_type: str
    lat: float
    lng: float
    distance_m: float
    current_view_quality: str
    projected_view_quality: str
    current_sunlight_hours: float
    projected_sunlight_hours: float
    value_impact_pct: float  # Positive = appreciation, negative = depreciation
    impact_severity: str  # low, medium, high


@dataclass
class ShadowImpact:
    """Shadow impact from a new/modified structure."""
    affected_area_sqm: float
    buildings_affected: int
    properties_affected: int
    worst_affected_direction: str
    shadow_length_m: float
    peak_shadow_hours: List[int]


@dataclass
class ViewCorridorImpact:
    """Impact on view corridors."""
    corridors_blocked: int
    corridors_preserved: int
    landmarks_obscured: List[str]
    best_remaining_views: List[str]


@dataclass
class Counterfactual3DResult:
    """Complete 3D impact analysis for a scenario."""
    scenario_type: str
    scenario_description: str
    location_lat: float
    location_lng: float
    
    # New structure details
    new_height_m: float = 0
    new_footprint_sqm: float = 0
    
    # Impact analysis
    impacted_properties: List[ImpactedProperty] = field(default_factory=list)
    shadow_impact: Optional[ShadowImpact] = None
    view_corridor_impact: Optional[ViewCorridorImpact] = None
    
    # Aggregate metrics
    total_properties_affected: int = 0
    avg_value_impact_pct: float = 0
    net_area_impact_sqm: float = 0
    
    # Before/after comparison
    before_metrics: Dict[str, Any] = field(default_factory=dict)
    after_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    approval_likelihood: str = "medium"  # low, medium, high
    
    # Narrative
    summary: str = ""


class Counterfactual3DEngine:
    """
    Analyzes 3D impacts of hypothetical urban changes.
    Integrates with occlusion and solar engines for accurate analysis.
    """
    
    # Infrastructure heights (typical)
    INFRASTRUCTURE_HEIGHTS = {
        'metro_station': 15,
        'metro_elevated': 12,
        'flyover': 10,
        'it_park': 50,
        'mall': 30,
        'hospital': 25,
        'school': 12,
        'park': 0,
        'high_rise_residential': 60,
        'commercial_tower': 80,
    }
    
    # Infrastructure footprints (sqm)
    INFRASTRUCTURE_FOOTPRINTS = {
        'metro_station': 2000,
        'metro_elevated': 500,
        'flyover': 1000,
        'it_park': 10000,
        'mall': 8000,
        'hospital': 5000,
        'school': 3000,
        'park': 5000,
        'high_rise_residential': 2000,
        'commercial_tower': 3000,
    }
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
        
        # Lazy-load engines
        self._occlusion = None
        self._solar = None
    
    def _get_occlusion(self):
        if self._occlusion is None:
            try:
                from occlusion_engine import get_occlusion_engine
                self._occlusion = get_occlusion_engine()
            except ImportError:
                pass
        return self._occlusion
    
    def _get_solar(self):
        if self._solar is None:
            try:
                from solar_engine import get_solar_engine
                self._solar = get_solar_engine()
            except ImportError:
                pass
        return self._solar
    
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _get_direction(self, from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> str:
        dlat = to_lat - from_lat
        dlng = to_lng - from_lng
        angle = math.degrees(math.atan2(dlng, dlat))
        if angle < 0:
            angle += 360
        
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        index = round(angle / 45) % 8
        return directions[index]
    
    def _calculate_shadow_length(self, height: float, sun_altitude: float) -> float:
        if sun_altitude <= 0:
            return 0
        return height / math.tan(math.radians(sun_altitude))
    
    def _get_nearby_properties(self, lat: float, lng: float, radius_m: float) -> List[Dict]:
        """Get properties near a location."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            radius_deg = radius_m / 111000
            
            cursor.execute("""
                SELECT id, title, latitude, longitude, price, bedrooms, total_area_sqft, property_type
                FROM properties
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                LIMIT 100
            """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
            
            properties = []
            for row in cursor.fetchall():
                dist = self._haversine_distance(lat, lng, row['latitude'], row['longitude'])
                if dist <= radius_m:
                    properties.append({
                        'id': str(row['id']),
                        'title': row['title'],
                        'lat': row['latitude'],
                        'lng': row['longitude'],
                        'price': row['price'],
                        'bedrooms': row['bedrooms'],
                        'area': row['total_area_sqft'],
                        'type': row['property_type'],
                        'distance': dist
                    })
            
            conn.close()
            return properties
            
        except Exception as e:
            print(f"[Counterfactual] Error getting properties: {e}")
            return []
    
    def _get_nearby_buildings(self, lat: float, lng: float, radius_m: float) -> List[Dict]:
        """Get buildings near a location."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            radius_deg = radius_m / 111000
            
            cursor.execute("""
                SELECT osm_id, name, height, building_type, latitude, longitude
                FROM buildings
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                AND height > 0
                LIMIT 200
            """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
            
            buildings = []
            for row in cursor.fetchall():
                dist = self._haversine_distance(lat, lng, row['latitude'], row['longitude'])
                if dist <= radius_m:
                    buildings.append({
                        'id': str(row['osm_id']),
                        'name': row['name'],
                        'height': row['height'],
                        'type': row['building_type'],
                        'lat': row['latitude'],
                        'lng': row['longitude'],
                        'distance': dist
                    })
            
            conn.close()
            return buildings
            
        except Exception as e:
            print(f"[Counterfactual] Error getting buildings: {e}")
            return []
    
    def analyze_new_construction(
        self,
        lat: float,
        lng: float,
        infrastructure_type: str,
        height_m: float = None,
        footprint_sqm: float = None,
        description: str = ""
    ) -> Counterfactual3DResult:
        """
        Analyze 3D impacts of new construction.
        
        Args:
            lat, lng: Location of new construction
            infrastructure_type: Type of infrastructure
            height_m: Override height (uses default if not provided)
            footprint_sqm: Override footprint
            description: Scenario description
            
        Returns:
            Counterfactual3DResult with complete impact analysis
        """
        # Get structure dimensions
        if height_m is None:
            height_m = self.INFRASTRUCTURE_HEIGHTS.get(infrastructure_type, 30)
        if footprint_sqm is None:
            footprint_sqm = self.INFRASTRUCTURE_FOOTPRINTS.get(infrastructure_type, 2000)
        
        result = Counterfactual3DResult(
            scenario_type=infrastructure_type,
            scenario_description=description or f"New {infrastructure_type} at location",
            location_lat=lat,
            location_lng=lng,
            new_height_m=height_m,
            new_footprint_sqm=footprint_sqm
        )
        
        # Get current state (before)
        occlusion = self._get_occlusion()
        solar = self._get_solar()
        
        # Analyze impact on nearby properties
        impact_radius = max(500, height_m * 3)  # Shadow can reach ~3x height
        properties = self._get_nearby_properties(lat, lng, impact_radius)
        buildings = self._get_nearby_buildings(lat, lng, impact_radius)
        
        impacted = []
        total_value_impact = 0
        
        for prop in properties:
            # Direction from new structure to property
            direction = self._get_direction(lat, lng, prop['lat'], prop['lng'])
            distance = prop['distance']
            
            # Estimate current view quality
            current_view = 'good'  # Baseline assumption
            
            # Calculate if new structure blocks view
            # If property is shorter than new structure and within shadow range
            angle_to_top = math.degrees(math.atan2(height_m, distance)) if distance > 0 else 90
            
            if angle_to_top > 30:
                projected_view = 'poor'
                view_impact = 'high'
            elif angle_to_top > 15:
                projected_view = 'moderate'
                view_impact = 'medium'
            else:
                projected_view = 'good'
                view_impact = 'low'
            
            # Sunlight impact
            current_sunlight = 8  # Baseline hours
            projected_sunlight = current_sunlight
            
            # If in shadow direction (E, SE, S, SW, W during different times)
            shadow_directions = ['E', 'SE', 'S', 'SW', 'W']
            if direction in shadow_directions and distance < height_m * 2:
                sunlight_reduction = min(3, (height_m / distance) * 2) if distance > 0 else 3
                projected_sunlight = max(4, current_sunlight - sunlight_reduction)
            
            # Value impact
            value_change = 0
            if projected_view == 'poor':
                value_change -= 15
            elif projected_view == 'moderate':
                value_change -= 5
            
            if projected_sunlight < current_sunlight - 1:
                value_change -= 5
            
            # Positive impacts (e.g., metro station adds value)
            if infrastructure_type == 'metro_station' and distance < 1000:
                value_change += 20 - (distance / 100)  # +20% at 0m, decreasing
            elif infrastructure_type == 'park':
                value_change += 10 - (distance / 100)
            elif infrastructure_type == 'mall' and distance < 500:
                value_change += 5
            
            value_change = max(-30, min(30, value_change))  # Cap at ±30%
            total_value_impact += value_change
            
            impacted.append(ImpactedProperty(
                property_id=prop['id'],
                property_type=prop['type'] or 'residential',
                lat=prop['lat'],
                lng=prop['lng'],
                distance_m=round(distance),
                current_view_quality=current_view,
                projected_view_quality=projected_view,
                current_sunlight_hours=current_sunlight,
                projected_sunlight_hours=round(projected_sunlight, 1),
                value_impact_pct=round(value_change, 1),
                impact_severity='high' if abs(value_change) > 15 else 'medium' if abs(value_change) > 5 else 'low'
            ))
        
        result.impacted_properties = impacted
        result.total_properties_affected = len(impacted)
        result.avg_value_impact_pct = round(total_value_impact / max(1, len(impacted)), 1)
        
        # Shadow impact analysis
        avg_sun_altitude = 60  # Approximate for Bangalore midday
        shadow_length = self._calculate_shadow_length(height_m, avg_sun_altitude)
        shadow_area = footprint_sqm + (shadow_length * math.sqrt(footprint_sqm))
        
        buildings_in_shadow = [b for b in buildings if b['distance'] < shadow_length]
        
        result.shadow_impact = ShadowImpact(
            affected_area_sqm=round(shadow_area),
            buildings_affected=len(buildings_in_shadow),
            properties_affected=len([p for p in impacted if p.projected_sunlight_hours < p.current_sunlight_hours]),
            worst_affected_direction='W',  # Morning shadow to west
            shadow_length_m=round(shadow_length),
            peak_shadow_hours=[8, 9, 16, 17]  # Morning and evening
        )
        
        # View corridor impact
        blocked_landmarks = []
        if height_m > 40:
            blocked_landmarks = ['Partial skyline obstruction']
        
        result.view_corridor_impact = ViewCorridorImpact(
            corridors_blocked=len([p for p in impacted if p.projected_view_quality == 'poor']),
            corridors_preserved=len([p for p in impacted if p.projected_view_quality == 'good']),
            landmarks_obscured=blocked_landmarks,
            best_remaining_views=['N', 'NE']  # Away from structure
        )
        
        # Before/after metrics
        result.before_metrics = {
            'avg_view_quality': 'good',
            'avg_sunlight_hours': 8,
            'building_count': len(buildings)
        }
        
        result.after_metrics = {
            'avg_view_quality': 'moderate' if result.avg_value_impact_pct < -5 else 'good',
            'avg_sunlight_hours': round(sum(p.projected_sunlight_hours for p in impacted) / max(1, len(impacted)), 1),
            'building_count': len(buildings) + 1
        }
        
        # Recommendations
        recommendations = []
        if height_m > 50:
            recommendations.append("Consider reducing height to minimize shadow impact")
        if len(buildings_in_shadow) > 10:
            recommendations.append("Significant shadow impact - compensatory measures recommended")
        if infrastructure_type in ['metro_station', 'park']:
            recommendations.append("Positive community impact - expedited approval likely")
        if result.avg_value_impact_pct < -10:
            recommendations.append("Negative value impact may face community opposition")
        
        result.recommendations = recommendations
        
        # Approval likelihood
        if infrastructure_type in ['metro_station', 'park', 'hospital', 'school']:
            result.approval_likelihood = 'high'
        elif result.avg_value_impact_pct < -15:
            result.approval_likelihood = 'low'
        else:
            result.approval_likelihood = 'medium'
        
        # Generate summary
        result.summary = self._generate_summary(result)
        
        return result
    
    def analyze_height_change(
        self,
        lat: float,
        lng: float,
        current_height_m: float,
        new_height_m: float
    ) -> Counterfactual3DResult:
        """Analyze impact of changing a building's height."""
        height_diff = new_height_m - current_height_m
        
        return self.analyze_new_construction(
            lat, lng,
            infrastructure_type='height_change',
            height_m=abs(height_diff),
            description=f"Height change from {current_height_m}m to {new_height_m}m"
        )
    
    def analyze_density_change(
        self,
        lat: float,
        lng: float,
        radius_m: float,
        far_increase: float
    ) -> Counterfactual3DResult:
        """
        Analyze impact of FAR/density increase in an area.
        
        Args:
            lat, lng: Center of area
            radius_m: Affected radius
            far_increase: FAR increase (e.g., 0.5 = 50% more buildable)
        """
        # Estimate average height increase from FAR change
        avg_height_increase = far_increase * 15  # Rough estimate
        
        result = self.analyze_new_construction(
            lat, lng,
            infrastructure_type='density_increase',
            height_m=avg_height_increase,
            footprint_sqm=math.pi * radius_m * radius_m * 0.1,  # 10% coverage
            description=f"FAR increase of {far_increase} in {radius_m}m radius"
        )
        
        result.recommendations.append(f"Area-wide FAR increase of {far_increase} will affect {result.total_properties_affected} properties")
        
        return result
    
    def _generate_summary(self, result: Counterfactual3DResult) -> str:
        """Generate natural language summary."""
        parts = []
        
        parts.append(f"**Scenario:** {result.scenario_description}")
        parts.append(f"**Height:** {result.new_height_m}m | **Footprint:** {result.new_footprint_sqm:,.0f} sqm")
        
        if result.total_properties_affected > 0:
            parts.append(f"\n**Impact:** {result.total_properties_affected} properties affected")
            parts.append(f"**Avg Value Change:** {result.avg_value_impact_pct:+.1f}%")
        
        if result.shadow_impact:
            parts.append(f"\n**Shadow:** {result.shadow_impact.shadow_length_m}m max, affecting {result.shadow_impact.buildings_affected} buildings")
        
        if result.view_corridor_impact:
            parts.append(f"**Views:** {result.view_corridor_impact.corridors_blocked} corridors blocked")
        
        parts.append(f"\n**Approval Likelihood:** {result.approval_likelihood.upper()}")
        
        return "\n".join(parts)


# Singleton
_counterfactual_3d = None


def get_counterfactual_3d() -> Counterfactual3DEngine:
    """Get or create counterfactual 3D engine singleton."""
    global _counterfactual_3d
    if _counterfactual_3d is None:
        _counterfactual_3d = Counterfactual3DEngine()
    return _counterfactual_3d
