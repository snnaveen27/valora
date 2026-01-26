"""
Spatial Inference Engine for Valora AI
Reasons about spatial relationships and generates explanations.

Key Capabilities:
1. Spatial Factor Analysis - Why is this location good/bad?
2. Comparative Reasoning - How do locations compare spatially?
3. Proximity Impact - How does nearness affect value?
4. Connectivity Analysis - How well-connected is this location?
5. Development Potential - What does spatial context suggest?

No external models needed - uses rule-based inference with local data.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math


class LocationFactor(Enum):
    """Factors that affect location quality."""
    METRO_ACCESS = "metro_access"
    ROAD_CONNECTIVITY = "road_connectivity"
    SCHOOL_PROXIMITY = "school_proximity"
    HOSPITAL_PROXIMITY = "hospital_proximity"
    COMMERCIAL_PROXIMITY = "commercial_proximity"
    GREEN_SPACE = "green_space"
    AIRPORT_ACCESS = "airport_access"
    IT_HUB_PROXIMITY = "it_hub_proximity"
    WATER_BODY = "water_body"
    DENSITY = "density"
    NOISE_LEVEL = "noise_level"
    AIR_QUALITY = "air_quality"


@dataclass
class FactorScore:
    """Score for a location factor."""
    factor: LocationFactor
    score: float  # 0-100
    raw_value: Any  # e.g., distance in meters
    description: str
    impact: str  # positive, negative, neutral
    weight: float = 1.0


@dataclass
class LocationInference:
    """Inference result for a location."""
    lat: float
    lng: float
    overall_score: float
    factors: List[FactorScore] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    investment_outlook: str = "neutral"
    target_buyer: str = "general"
    reasoning_chain: List[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Result of comparing two locations."""
    location_a: Tuple[float, float]
    location_b: Tuple[float, float]
    winner: str  # "A", "B", or "tie"
    score_a: float
    score_b: float
    factor_comparison: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    summary: str = ""
    detailed_analysis: List[str] = field(default_factory=list)


class SpatialInferenceEngine:
    """
    Reasons about spatial relationships to generate insights.
    """
    
    # Factor weights for different buyer profiles
    BUYER_PROFILES = {
        'family': {
            LocationFactor.SCHOOL_PROXIMITY: 2.0,
            LocationFactor.HOSPITAL_PROXIMITY: 1.5,
            LocationFactor.GREEN_SPACE: 1.5,
            LocationFactor.NOISE_LEVEL: 1.5,
            LocationFactor.METRO_ACCESS: 1.0,
        },
        'professional': {
            LocationFactor.IT_HUB_PROXIMITY: 2.0,
            LocationFactor.METRO_ACCESS: 1.8,
            LocationFactor.AIRPORT_ACCESS: 1.5,
            LocationFactor.COMMERCIAL_PROXIMITY: 1.3,
        },
        'investor': {
            LocationFactor.METRO_ACCESS: 2.0,
            LocationFactor.IT_HUB_PROXIMITY: 1.8,
            LocationFactor.DENSITY: 1.5,
            LocationFactor.ROAD_CONNECTIVITY: 1.5,
        },
        'retiree': {
            LocationFactor.HOSPITAL_PROXIMITY: 2.0,
            LocationFactor.GREEN_SPACE: 1.8,
            LocationFactor.NOISE_LEVEL: 1.5,
            LocationFactor.AIR_QUALITY: 1.5,
        },
    }
    
    # Distance thresholds for scoring (in meters)
    DISTANCE_THRESHOLDS = {
        LocationFactor.METRO_ACCESS: {
            'excellent': 500,
            'good': 1000,
            'fair': 2000,
            'poor': 5000,
        },
        LocationFactor.SCHOOL_PROXIMITY: {
            'excellent': 500,
            'good': 1000,
            'fair': 2000,
            'poor': 3000,
        },
        LocationFactor.HOSPITAL_PROXIMITY: {
            'excellent': 1000,
            'good': 2000,
            'fair': 5000,
            'poor': 10000,
        },
        LocationFactor.IT_HUB_PROXIMITY: {
            'excellent': 2000,
            'good': 5000,
            'fair': 10000,
            'poor': 15000,
        },
        LocationFactor.AIRPORT_ACCESS: {
            'excellent': 15000,
            'good': 25000,
            'fair': 40000,
            'poor': 60000,
        },
        LocationFactor.GREEN_SPACE: {
            'excellent': 300,
            'good': 500,
            'fair': 1000,
            'poor': 2000,
        },
    }
    
    def __init__(self, db_service=None, spatial_service=None):
        self.db_service = db_service
        self.spatial_service = spatial_service
    
    def analyze_location(self, lat: float, lng: float,
                        buyer_profile: str = 'general') -> LocationInference:
        """
        Analyze a location and generate inferences.
        
        Args:
            lat, lng: Location coordinates
            buyer_profile: Target buyer type
            
        Returns:
            LocationInference with scores and reasoning
        """
        inference = LocationInference(lat=lat, lng=lng, overall_score=0)
        
        # Get weights for buyer profile
        weights = self.BUYER_PROFILES.get(buyer_profile, {})
        
        # Analyze each factor
        factors = []
        
        # 1. Metro Access
        metro_score = self._analyze_metro_access(lat, lng)
        if metro_score:
            metro_score.weight = weights.get(LocationFactor.METRO_ACCESS, 1.0)
            factors.append(metro_score)
            inference.reasoning_chain.append(
                f"Metro access: {metro_score.description} (score: {metro_score.score:.0f})"
            )
        
        # 2. School Proximity
        school_score = self._analyze_schools(lat, lng)
        if school_score:
            school_score.weight = weights.get(LocationFactor.SCHOOL_PROXIMITY, 1.0)
            factors.append(school_score)
            inference.reasoning_chain.append(
                f"Schools: {school_score.description} (score: {school_score.score:.0f})"
            )
        
        # 3. Hospital Proximity
        hospital_score = self._analyze_hospitals(lat, lng)
        if hospital_score:
            hospital_score.weight = weights.get(LocationFactor.HOSPITAL_PROXIMITY, 1.0)
            factors.append(hospital_score)
            inference.reasoning_chain.append(
                f"Healthcare: {hospital_score.description} (score: {hospital_score.score:.0f})"
            )
        
        # 4. IT Hub Proximity
        it_score = self._analyze_it_hubs(lat, lng)
        if it_score:
            it_score.weight = weights.get(LocationFactor.IT_HUB_PROXIMITY, 1.0)
            factors.append(it_score)
            inference.reasoning_chain.append(
                f"IT hubs: {it_score.description} (score: {it_score.score:.0f})"
            )
        
        # 5. Commercial Proximity
        commercial_score = self._analyze_commercial(lat, lng)
        if commercial_score:
            commercial_score.weight = weights.get(LocationFactor.COMMERCIAL_PROXIMITY, 1.0)
            factors.append(commercial_score)
            inference.reasoning_chain.append(
                f"Commercial: {commercial_score.description} (score: {commercial_score.score:.0f})"
            )
        
        # 6. Density Analysis
        density_score = self._analyze_density(lat, lng)
        if density_score:
            density_score.weight = weights.get(LocationFactor.DENSITY, 1.0)
            factors.append(density_score)
            inference.reasoning_chain.append(
                f"Density: {density_score.description} (score: {density_score.score:.0f})"
            )
        
        inference.factors = factors
        
        # Calculate overall score
        if factors:
            total_weight = sum(f.weight for f in factors)
            weighted_sum = sum(f.score * f.weight for f in factors)
            inference.overall_score = weighted_sum / total_weight if total_weight > 0 else 50
        
        # Identify strengths and weaknesses
        for factor in factors:
            if factor.score >= 75:
                inference.strengths.append(factor.description)
            elif factor.score <= 35:
                inference.weaknesses.append(factor.description)
        
        # Determine investment outlook
        inference.investment_outlook = self._determine_outlook(inference)
        
        # Determine target buyer
        inference.target_buyer = self._determine_target_buyer(inference)
        
        return inference
    
    def _analyze_metro_access(self, lat: float, lng: float) -> Optional[FactorScore]:
        """Analyze metro station proximity."""
        # Try to get from database
        distance = self._get_nearest_distance(lat, lng, 'metro')
        
        if distance is None:
            # Estimate based on known Bangalore metro network
            distance = self._estimate_metro_distance(lat, lng)
        
        score = self._distance_to_score(distance, LocationFactor.METRO_ACCESS)
        impact = "positive" if score >= 60 else "negative" if score <= 40 else "neutral"
        
        if distance < 500:
            desc = f"Excellent metro access ({distance:.0f}m to station)"
        elif distance < 1000:
            desc = f"Good metro access ({distance:.0f}m to station)"
        elif distance < 2000:
            desc = f"Fair metro access ({distance:.0f}m to station)"
        else:
            desc = f"Limited metro access ({distance/1000:.1f}km to station)"
        
        return FactorScore(
            factor=LocationFactor.METRO_ACCESS,
            score=score,
            raw_value=distance,
            description=desc,
            impact=impact,
        )
    
    def _analyze_schools(self, lat: float, lng: float) -> Optional[FactorScore]:
        """Analyze school proximity."""
        distance = self._get_nearest_distance(lat, lng, 'school')
        
        if distance is None:
            distance = 1500  # Default estimate
        
        # Also count schools within 2km
        count = self._count_nearby(lat, lng, 'school', 2000)
        
        score = self._distance_to_score(distance, LocationFactor.SCHOOL_PROXIMITY)
        
        # Boost score if many schools nearby
        if count > 5:
            score = min(100, score + 15)
        elif count > 2:
            score = min(100, score + 10)
        
        impact = "positive" if score >= 60 else "negative" if score <= 40 else "neutral"
        
        if count > 5:
            desc = f"Excellent school options ({count} schools within 2km)"
        elif count > 2:
            desc = f"Good school options ({count} schools within 2km)"
        elif count > 0:
            desc = f"Limited school options ({count} school within 2km)"
        else:
            desc = "Few schools in immediate vicinity"
        
        return FactorScore(
            factor=LocationFactor.SCHOOL_PROXIMITY,
            score=score,
            raw_value={'distance': distance, 'count': count},
            description=desc,
            impact=impact,
        )
    
    def _analyze_hospitals(self, lat: float, lng: float) -> Optional[FactorScore]:
        """Analyze hospital/healthcare proximity."""
        distance = self._get_nearest_distance(lat, lng, 'hospital')
        
        if distance is None:
            distance = 3000  # Default estimate
        
        score = self._distance_to_score(distance, LocationFactor.HOSPITAL_PROXIMITY)
        impact = "positive" if score >= 60 else "negative" if score <= 40 else "neutral"
        
        if distance < 1000:
            desc = f"Excellent healthcare access ({distance:.0f}m to hospital)"
        elif distance < 2000:
            desc = f"Good healthcare access ({distance:.0f}m to hospital)"
        elif distance < 5000:
            desc = f"Adequate healthcare access ({distance/1000:.1f}km to hospital)"
        else:
            desc = f"Limited healthcare access ({distance/1000:.1f}km to hospital)"
        
        return FactorScore(
            factor=LocationFactor.HOSPITAL_PROXIMITY,
            score=score,
            raw_value=distance,
            description=desc,
            impact=impact,
        )
    
    def _analyze_it_hubs(self, lat: float, lng: float) -> Optional[FactorScore]:
        """Analyze IT hub proximity (important for Bangalore)."""
        # Known IT hubs in Bangalore
        it_hubs = [
            (12.8399, 77.6770, 'Electronic City'),
            (12.9698, 77.7500, 'Whitefield'),
            (12.9300, 77.6800, 'Outer Ring Road'),
            (12.9352, 77.6245, 'Koramangala'),
            (13.0200, 77.6400, 'Manyata Tech Park'),
            (12.9784, 77.6408, 'Indiranagar'),
        ]
        
        # Find nearest IT hub
        min_distance = float('inf')
        nearest_hub = None
        
        for hub_lat, hub_lng, name in it_hubs:
            dist = self._haversine(lat, lng, hub_lat, hub_lng)
            if dist < min_distance:
                min_distance = dist
                nearest_hub = name
        
        score = self._distance_to_score(min_distance, LocationFactor.IT_HUB_PROXIMITY)
        impact = "positive" if score >= 60 else "negative" if score <= 40 else "neutral"
        
        if min_distance < 2000:
            desc = f"In IT corridor ({nearest_hub}, {min_distance/1000:.1f}km)"
        elif min_distance < 5000:
            desc = f"Good IT hub access ({nearest_hub}, {min_distance/1000:.1f}km)"
        elif min_distance < 10000:
            desc = f"Reasonable IT hub access ({nearest_hub}, {min_distance/1000:.1f}km)"
        else:
            desc = f"Far from IT hubs ({min_distance/1000:.1f}km)"
        
        return FactorScore(
            factor=LocationFactor.IT_HUB_PROXIMITY,
            score=score,
            raw_value={'distance': min_distance, 'hub': nearest_hub},
            description=desc,
            impact=impact,
        )
    
    def _analyze_commercial(self, lat: float, lng: float) -> Optional[FactorScore]:
        """Analyze commercial area proximity."""
        count = self._count_nearby(lat, lng, 'commercial', 1000)
        
        if count > 20:
            score = 90
            desc = "Very high commercial density (urban core)"
        elif count > 10:
            score = 75
            desc = "Good commercial access"
        elif count > 5:
            score = 60
            desc = "Moderate commercial presence"
        elif count > 0:
            score = 45
            desc = "Limited commercial options"
        else:
            score = 30
            count = self._count_nearby(lat, lng, 'commercial', 2000)
            desc = f"Primarily residential ({count} shops within 2km)"
        
        impact = "positive" if score >= 60 else "neutral"
        
        return FactorScore(
            factor=LocationFactor.COMMERCIAL_PROXIMITY,
            score=score,
            raw_value=count,
            description=desc,
            impact=impact,
        )
    
    def _analyze_density(self, lat: float, lng: float) -> Optional[FactorScore]:
        """Analyze building/population density."""
        building_count = self._count_nearby(lat, lng, 'building', 500)
        
        # Score depends on perspective - moderate density is often best
        if building_count > 100:
            score = 50  # Very dense - can be good or bad
            desc = "High density urban area"
            impact = "neutral"
        elif building_count > 50:
            score = 75  # Good density
            desc = "Well-developed area with good infrastructure"
            impact = "positive"
        elif building_count > 20:
            score = 70
            desc = "Moderate density, balanced development"
            impact = "positive"
        elif building_count > 5:
            score = 55
            desc = "Developing area, lower density"
            impact = "neutral"
        else:
            score = 40
            desc = "Low density, possibly underdeveloped"
            impact = "negative"
        
        return FactorScore(
            factor=LocationFactor.DENSITY,
            score=score,
            raw_value=building_count,
            description=desc,
            impact=impact,
        )
    
    def _get_nearest_distance(self, lat: float, lng: float, poi_type: str) -> Optional[float]:
        """Get distance to nearest POI of given type."""
        if not self.db_service:
            return None
        
        try:
            radius_deg = 5000 / 111000  # 5km search
            
            type_mapping = {
                'metro': ['metro', 'metro_station', 'subway'],
                'school': ['school', 'college', 'education'],
                'hospital': ['hospital', 'clinic', 'healthcare'],
                'commercial': ['shop', 'mall', 'retail', 'commercial'],
            }
            
            types = type_mapping.get(poi_type, [poi_type])
            type_clause = ' OR '.join([f"category = '{t}'" for t in types])
            
            query = f"""
                SELECT latitude, longitude,
                    (latitude - ?) * (latitude - ?) + 
                    (longitude - ?) * (longitude - ?) as dist_sq
                FROM pois
                WHERE ({type_clause})
                AND latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                ORDER BY dist_sq
                LIMIT 1
            """
            
            result = self.db_service.execute(query, (
                lat, lat, lng, lng,
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            
            if result and result[0]:
                poi_lat = result[0]['latitude']
                poi_lng = result[0]['longitude']
                return self._haversine(lat, lng, poi_lat, poi_lng)
        except:
            pass
        
        return None
    
    def _count_nearby(self, lat: float, lng: float, poi_type: str, radius_m: float) -> int:
        """Count POIs of given type within radius."""
        if not self.db_service:
            return 0
        
        try:
            radius_deg = radius_m / 111000
            
            if poi_type == 'building':
                query = """
                    SELECT COUNT(*) as cnt FROM buildings
                    WHERE latitude BETWEEN ? AND ?
                    AND longitude BETWEEN ? AND ?
                """
            else:
                type_mapping = {
                    'school': ['school', 'college', 'education'],
                    'hospital': ['hospital', 'clinic', 'healthcare'],
                    'commercial': ['shop', 'mall', 'retail', 'commercial'],
                }
                types = type_mapping.get(poi_type, [poi_type])
                type_clause = ' OR '.join([f"category = '{t}'" for t in types])
                
                query = f"""
                    SELECT COUNT(*) as cnt FROM pois
                    WHERE ({type_clause})
                    AND latitude BETWEEN ? AND ?
                    AND longitude BETWEEN ? AND ?
                """
            
            result = self.db_service.execute(query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            
            return result[0]['cnt'] if result else 0
        except:
            return 0
    
    def _estimate_metro_distance(self, lat: float, lng: float) -> float:
        """Estimate metro distance based on known stations."""
        # Bangalore metro stations (subset)
        metro_stations = [
            (12.9784, 77.6408),  # Indiranagar
            (12.9352, 77.6245),  # Koramangala (planned)
            (13.0358, 77.5970),  # Hebbal
            (12.9778, 77.5716),  # Majestic
            (12.9763, 77.5929),  # Cubbon Park
            (12.9756, 77.6066),  # MG Road
            (12.9916, 77.5438),  # Vijayanagar
            (12.9308, 77.5838),  # Jayanagar
        ]
        
        min_dist = float('inf')
        for station_lat, station_lng in metro_stations:
            dist = self._haversine(lat, lng, station_lat, station_lng)
            min_dist = min(min_dist, dist)
        
        return min_dist
    
    def _distance_to_score(self, distance: float, factor: LocationFactor) -> float:
        """Convert distance to score based on thresholds."""
        thresholds = self.DISTANCE_THRESHOLDS.get(factor, {
            'excellent': 500,
            'good': 1000,
            'fair': 2000,
            'poor': 5000,
        })
        
        if distance <= thresholds['excellent']:
            return 95
        elif distance <= thresholds['good']:
            # Linear interpolation
            ratio = (distance - thresholds['excellent']) / (thresholds['good'] - thresholds['excellent'])
            return 95 - (ratio * 20)  # 95 to 75
        elif distance <= thresholds['fair']:
            ratio = (distance - thresholds['good']) / (thresholds['fair'] - thresholds['good'])
            return 75 - (ratio * 25)  # 75 to 50
        elif distance <= thresholds['poor']:
            ratio = (distance - thresholds['fair']) / (thresholds['poor'] - thresholds['fair'])
            return 50 - (ratio * 25)  # 50 to 25
        else:
            return max(10, 25 - (distance - thresholds['poor']) / 1000 * 5)
    
    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points in meters."""
        R = 6371000  # Earth radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _determine_outlook(self, inference: LocationInference) -> str:
        """Determine investment outlook based on factors."""
        score = inference.overall_score
        
        # Check for metro access (key appreciation driver in Bangalore)
        metro_score = next((f.score for f in inference.factors 
                          if f.factor == LocationFactor.METRO_ACCESS), 50)
        it_score = next((f.score for f in inference.factors 
                        if f.factor == LocationFactor.IT_HUB_PROXIMITY), 50)
        
        if metro_score >= 80 and it_score >= 60:
            return "strong_growth"
        elif score >= 70 and metro_score >= 60:
            return "good_growth"
        elif score >= 60:
            return "stable"
        elif score >= 45:
            return "moderate"
        else:
            return "cautious"
    
    def _determine_target_buyer(self, inference: LocationInference) -> str:
        """Determine ideal buyer profile for location."""
        factor_scores = {f.factor: f.score for f in inference.factors}
        
        it_score = factor_scores.get(LocationFactor.IT_HUB_PROXIMITY, 0)
        metro_score = factor_scores.get(LocationFactor.METRO_ACCESS, 0)
        school_score = factor_scores.get(LocationFactor.SCHOOL_PROXIMITY, 0)
        hospital_score = factor_scores.get(LocationFactor.HOSPITAL_PROXIMITY, 0)
        
        if it_score >= 70 and metro_score >= 60:
            return "IT professionals"
        elif school_score >= 70 and hospital_score >= 60:
            return "families"
        elif hospital_score >= 80:
            return "retirees"
        elif metro_score >= 80:
            return "commuters"
        else:
            return "general buyers"
    
    def compare_locations(self, loc_a: Tuple[float, float],
                         loc_b: Tuple[float, float],
                         buyer_profile: str = 'general') -> ComparisonResult:
        """
        Compare two locations for investment/living.
        
        Args:
            loc_a, loc_b: (lat, lng) tuples
            buyer_profile: Target buyer type
            
        Returns:
            ComparisonResult with detailed analysis
        """
        # Analyze both locations
        inference_a = self.analyze_location(loc_a[0], loc_a[1], buyer_profile)
        inference_b = self.analyze_location(loc_b[0], loc_b[1], buyer_profile)
        
        # Determine winner
        score_diff = inference_a.overall_score - inference_b.overall_score
        if score_diff > 5:
            winner = "A"
        elif score_diff < -5:
            winner = "B"
        else:
            winner = "tie"
        
        # Factor comparison
        factor_comparison = {}
        factors_a = {f.factor: f.score for f in inference_a.factors}
        factors_b = {f.factor: f.score for f in inference_b.factors}
        
        for factor in set(factors_a.keys()) | set(factors_b.keys()):
            factor_comparison[factor.value] = (
                factors_a.get(factor, 0),
                factors_b.get(factor, 0)
            )
        
        # Generate detailed analysis
        analysis = []
        
        for factor_name, (score_a, score_b) in factor_comparison.items():
            diff = score_a - score_b
            if abs(diff) > 10:
                better = "Location A" if diff > 0 else "Location B"
                analysis.append(f"**{factor_name.replace('_', ' ').title()}**: {better} is significantly better (+{abs(diff):.0f} points)")
            elif abs(diff) > 5:
                better = "Location A" if diff > 0 else "Location B"
                analysis.append(f"**{factor_name.replace('_', ' ').title()}**: {better} has slight edge")
        
        # Summary
        if winner == "A":
            summary = f"Location A scores higher ({inference_a.overall_score:.0f} vs {inference_b.overall_score:.0f}). Better for {inference_a.target_buyer}."
        elif winner == "B":
            summary = f"Location B scores higher ({inference_b.overall_score:.0f} vs {inference_a.overall_score:.0f}). Better for {inference_b.target_buyer}."
        else:
            summary = f"Both locations are comparable ({inference_a.overall_score:.0f} vs {inference_b.overall_score:.0f}). Choice depends on specific priorities."
        
        return ComparisonResult(
            location_a=loc_a,
            location_b=loc_b,
            winner=winner,
            score_a=inference_a.overall_score,
            score_b=inference_b.overall_score,
            factor_comparison=factor_comparison,
            summary=summary,
            detailed_analysis=analysis,
        )
    
    def explain_location(self, lat: float, lng: float,
                        buyer_profile: str = 'general') -> str:
        """
        Generate natural language explanation of a location.
        """
        inference = self.analyze_location(lat, lng, buyer_profile)
        
        parts = []
        
        # Overall assessment
        if inference.overall_score >= 75:
            parts.append(f"This is an **excellent location** (score: {inference.overall_score:.0f}/100).")
        elif inference.overall_score >= 60:
            parts.append(f"This is a **good location** (score: {inference.overall_score:.0f}/100).")
        elif inference.overall_score >= 45:
            parts.append(f"This is a **decent location** (score: {inference.overall_score:.0f}/100).")
        else:
            parts.append(f"This location has **some challenges** (score: {inference.overall_score:.0f}/100).")
        
        # Strengths
        if inference.strengths:
            parts.append("\n**Strengths:**")
            for strength in inference.strengths[:3]:
                parts.append(f"- {strength}")
        
        # Weaknesses
        if inference.weaknesses:
            parts.append("\n**Considerations:**")
            for weakness in inference.weaknesses[:3]:
                parts.append(f"- {weakness}")
        
        # Investment outlook
        outlook_text = {
            'strong_growth': 'Strong appreciation potential due to metro/IT hub proximity',
            'good_growth': 'Good appreciation expected with improving infrastructure',
            'stable': 'Stable area with steady value retention',
            'moderate': 'Moderate growth potential, depends on future development',
            'cautious': 'Limited near-term appreciation, long-term investment horizon needed',
        }
        parts.append(f"\n**Investment Outlook:** {outlook_text.get(inference.investment_outlook, 'Neutral')}")
        
        # Target buyer
        parts.append(f"\n**Ideal For:** {inference.target_buyer.title()}")
        
        return "\n".join(parts)


# Singleton instance
_inference_engine = None


def get_inference_engine(db_service=None, spatial_service=None) -> SpatialInferenceEngine:
    """Get or create inference engine singleton."""
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = SpatialInferenceEngine(db_service, spatial_service)
    return _inference_engine
