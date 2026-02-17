"""
Cognitive Workflow Engine for Smart Report
Implements adaptive reasoning, temporal context, and confidence calibration
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import math

logger = logging.getLogger(__name__)


# ============================================
# ENUMS AND DATA CLASSES
# ============================================

class MarketPhase(Enum):
    GROWTH = "growth"
    STABLE = "stable"
    DECLINE = "decline"
    RECOVERY = "recovery"


class ReasoningMode(Enum):
    ANALYTICAL = "analytical"      # Data-driven, detailed
    COMPARATIVE = "comparative"    # Side-by-side, relative
    PREDICTIVE = "predictive"      # Scenario-based, probabilistic
    ADVISORY = "advisory"          # Action-oriented, prescriptive


class ConfidenceLevel(Enum):
    VERY_HIGH = "very_high"  # 80-100%
    HIGH = "high"            # 60-80%
    MEDIUM = "medium"        # 40-60%
    LOW = "low"              # 20-40%
    VERY_LOW = "very_low"    # 0-20%


@dataclass
class TemporalContext:
    """Adaptive temporal context for market analysis"""
    current_phase: MarketPhase = MarketPhase.STABLE
    seasonal_factor: float = 1.0
    momentum_score: float = 0.5
    trend_direction: str = "neutral"
    cycle_position: float = 0.5  # 0 = bottom, 1 = top
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'current_phase': self.current_phase.value,
            'seasonal_factor': self.seasonal_factor,
            'momentum_score': self.momentum_score,
            'trend_direction': self.trend_direction,
            'cycle_position': self.cycle_position,
            'last_updated': self.last_updated.isoformat()
        }


@dataclass
class ConfidenceBreakdown:
    """Detailed confidence scoring"""
    overall_score: float = 0.75
    data_quality: float = 0.80
    model_certainty: float = 0.70
    historical_accuracy: float = 0.75
    spatial_confidence: float = 0.85
    temporal_confidence: float = 0.70
    
    def calculate_weighted_score(self) -> float:
        weights = {
            'data_quality': 0.25,
            'model_certainty': 0.20,
            'historical_accuracy': 0.20,
            'spatial_confidence': 0.20,
            'temporal_confidence': 0.15
        }
        return (
            self.data_quality * weights['data_quality'] +
            self.model_certainty * weights['model_certainty'] +
            self.historical_accuracy * weights['historical_accuracy'] +
            self.spatial_confidence * weights['spatial_confidence'] +
            self.temporal_confidence * weights['temporal_confidence']
        )
    
    def to_dict(self) -> Dict:
        return {
            'overall_score': self.overall_score,
            'data_quality': self.data_quality,
            'model_certainty': self.model_certainty,
            'historical_accuracy': self.historical_accuracy,
            'spatial_confidence': self.spatial_confidence,
            'temporal_confidence': self.temporal_confidence,
            'weighted_score': self.calculate_weighted_score()
        }


@dataclass
class MicroContext:
    """Micro-context awareness for local nuances"""
    street_score: float = 0.5
    building_quality: float = 0.5
    amenity_proximity: float = 0.5
    micro_market_tier: str = "average"
    noise_level: str = "moderate"
    traffic_impact: str = "moderate"
    
    def to_dict(self) -> Dict:
        return {
            'street_score': self.street_score,
            'building_quality': self.building_quality,
            'amenity_proximity': self.amenity_proximity,
            'micro_market_tier': self.micro_market_tier,
            'noise_level': self.noise_level,
            'traffic_impact': self.traffic_impact
        }


# ============================================
# ADAPTIVE TEMPORAL CONTEXT ENGINE
# ============================================

class AdaptiveTemporalContext:
    """
    Understands WHEN things change
    - Market phase detection
    - Seasonal adjustments
    - Trend momentum tracking
    - Historical pattern recognition
    """
    
    def __init__(self):
        self.history_window_days = 365
        self.seasonal_patterns = self._load_seasonal_patterns()
    
    def _load_seasonal_patterns(self) -> Dict:
        """Load seasonal adjustment factors"""
        return {
            1: 0.95,   # January - post-holiday slowdown
            2: 0.98,   # February
            3: 1.02,   # March - fiscal year end
            4: 1.05,   # April - new fiscal year
            5: 1.03,   # May
            6: 0.97,   # June - monsoon begins
            7: 0.94,   # July - monsoon
            8: 0.95,   # August - monsoon
            9: 1.01,   # September - festival season begins
            10: 1.08,  # October - festival season
            11: 1.06,  # November - festival season
            12: 1.00   # December - year end
        }
    
    async def analyze_temporal_context(
        self,
        market_data: Dict[str, Any],
        historical_data: Optional[List[Dict]] = None
    ) -> TemporalContext:
        """Analyze and return temporal context"""
        
        # Detect market phase
        phase = await self._detect_market_phase(market_data, historical_data)
        
        # Calculate seasonal factor
        current_month = datetime.now().month
        seasonal_factor = self.seasonal_patterns.get(current_month, 1.0)
        
        # Calculate momentum
        momentum = self._calculate_momentum(market_data, historical_data)
        
        # Determine trend direction
        trend = self._determine_trend(momentum)
        
        # Calculate cycle position
        cycle_pos = self._calculate_cycle_position(market_data, phase)
        
        return TemporalContext(
            current_phase=phase,
            seasonal_factor=seasonal_factor,
            momentum_score=momentum,
            trend_direction=trend,
            cycle_position=cycle_pos
        )
    
    async def _detect_market_phase(
        self,
        market_data: Dict,
        historical_data: Optional[List[Dict]]
    ) -> MarketPhase:
        """Detect current market phase"""
        
        price_trend = market_data.get('price_trend_1y', 0)
        demand_index = market_data.get('demand_index', 50)
        inventory_days = market_data.get('avg_days_on_market', 60)
        
        # Growth phase indicators
        if price_trend > 10 and demand_index > 60 and inventory_days < 45:
            return MarketPhase.GROWTH
        
        # Decline phase indicators
        if price_trend < -5 or (demand_index < 40 and inventory_days > 90):
            return MarketPhase.DECLINE
        
        # Recovery phase indicators
        if price_trend > 0 and demand_index > 50 and inventory_days < 75:
            return MarketPhase.RECOVERY
        
        return MarketPhase.STABLE
    
    def _calculate_momentum(
        self,
        market_data: Dict,
        historical_data: Optional[List[Dict]]
    ) -> float:
        """Calculate market momentum score (0-1)"""
        
        price_trend = market_data.get('price_trend_1y', 0)
        demand_change = market_data.get('demand_change', 0)
        
        # Normalize to 0-1 scale
        price_momentum = min(1, max(0, (price_trend + 20) / 40))
        demand_momentum = min(1, max(0, (demand_change + 20) / 40))
        
        return (price_momentum * 0.6 + demand_momentum * 0.4)
    
    def _determine_trend(self, momentum: float) -> str:
        """Determine trend direction from momentum"""
        if momentum > 0.65:
            return "bullish"
        elif momentum > 0.55:
            return "slightly_bullish"
        elif momentum < 0.35:
            return "bearish"
        elif momentum < 0.45:
            return "slightly_bearish"
        return "neutral"
    
    def _calculate_cycle_position(
        self,
        market_data: Dict,
        phase: MarketPhase
    ) -> float:
        """Calculate position in market cycle (0=bottom, 1=top)"""
        
        phase_positions = {
            MarketPhase.DECLINE: 0.2,
            MarketPhase.RECOVERY: 0.4,
            MarketPhase.STABLE: 0.5,
            MarketPhase.GROWTH: 0.8
        }
        
        base_position = phase_positions.get(phase, 0.5)
        
        # Adjust based on price trend
        price_trend = market_data.get('price_trend_1y', 0)
        adjustment = min(0.15, max(-0.15, price_trend / 100))
        
        return min(1.0, max(0.0, base_position + adjustment))


# ============================================
# ADAPTIVE REASONING LAYER
# ============================================

class AdaptiveReasoningLayer:
    """
    Determines HOW to think about the problem
    - Query intent classification
    - Reasoning mode selection
    - Confidence calibration
    - Evidence weighting
    """
    
    def __init__(self):
        self.intent_mode_mapping = {
            'investment_analysis': ReasoningMode.ANALYTICAL,
            'area_comparison': ReasoningMode.COMPARATIVE,
            'roi_projection': ReasoningMode.PREDICTIVE,
            'recommendation': ReasoningMode.ADVISORY,
            'risk_assessment': ReasoningMode.ANALYTICAL,
            'market_trend': ReasoningMode.PREDICTIVE
        }
    
    async def classify_intent(self, query: str) -> str:
        """Classify user query intent"""
        query_lower = query.lower()
        
        if any(w in query_lower for w in ['invest', 'buy', 'worth']):
            return 'investment_analysis'
        elif any(w in query_lower for w in ['compare', 'versus', 'vs', 'better']):
            return 'area_comparison'
        elif any(w in query_lower for w in ['return', 'roi', 'profit', 'yield']):
            return 'roi_projection'
        elif any(w in query_lower for w in ['recommend', 'should i', 'suggest']):
            return 'recommendation'
        elif any(w in query_lower for w in ['risk', 'safe', 'danger', 'problem']):
            return 'risk_assessment'
        elif any(w in query_lower for w in ['trend', 'future', 'growth', 'decline']):
            return 'market_trend'
        
        return 'investment_analysis'
    
    def select_reasoning_mode(self, intent: str) -> ReasoningMode:
        """Select appropriate reasoning mode for intent"""
        return self.intent_mode_mapping.get(intent, ReasoningMode.ANALYTICAL)
    
    async def calibrate_confidence(
        self,
        data_quality: float,
        model_output: Dict,
        historical_accuracy: float = 0.75
    ) -> ConfidenceBreakdown:
        """Calibrate confidence scores based on multiple factors"""
        
        # Data quality confidence
        dq_confidence = min(1.0, data_quality)
        
        # Model certainty (based on output consistency)
        model_certainty = self._calculate_model_certainty(model_output)
        
        # Spatial confidence (based on location data completeness)
        spatial_conf = self._calculate_spatial_confidence(model_output)
        
        # Temporal confidence (based on data freshness)
        temporal_conf = self._calculate_temporal_confidence(model_output)
        
        breakdown = ConfidenceBreakdown(
            data_quality=dq_confidence,
            model_certainty=model_certainty,
            historical_accuracy=historical_accuracy,
            spatial_confidence=spatial_conf,
            temporal_confidence=temporal_conf
        )
        
        breakdown.overall_score = breakdown.calculate_weighted_score()
        
        return breakdown
    
    def _calculate_model_certainty(self, output: Dict) -> float:
        """Calculate model certainty from output"""
        # Check for conflicting signals
        verdict = output.get('verdict', 'HOLD')
        confidence = output.get('confidence', 0.5)
        
        # Higher confidence = higher certainty
        base_certainty = confidence
        
        # Adjust for verdict type
        if verdict == 'HOLD':
            base_certainty *= 0.9  # HOLD is inherently less certain
        
        return min(1.0, base_certainty)
    
    def _calculate_spatial_confidence(self, output: Dict) -> float:
        """Calculate spatial data confidence"""
        spatial_data = output.get('spatial_data', {})
        
        if not spatial_data:
            return 0.5
        
        # Check for key spatial indicators
        has_pois = bool(spatial_data.get('pois'))
        has_connectivity = 'connectivity_score' in spatial_data
        has_walkability = 'walkability_score' in spatial_data
        
        score = 0.5
        if has_pois:
            score += 0.2
        if has_connectivity:
            score += 0.15
        if has_walkability:
            score += 0.15
        
        return min(1.0, score)
    
    def _calculate_temporal_confidence(self, output: Dict) -> float:
        """Calculate temporal data confidence"""
        # Check data freshness
        market_data = output.get('market_data', {})
        
        if not market_data:
            return 0.5
        
        # Check for trend data
        has_trend = 'price_trend_1y' in market_data
        has_historical = 'price_trend_3y' in market_data
        
        score = 0.5
        if has_trend:
            score += 0.25
        if has_historical:
            score += 0.25
        
        return min(1.0, score)


# ============================================
# SPATIAL RELATIONSHIP REASONING
# ============================================

class SpatialRelationshipReasoning:
    """
    Understands location relationships
    - Distance decay modeling
    - Accessibility scoring
    - Neighborhood clustering
    - Growth corridor detection
    """
    
    def __init__(self):
        self.distance_decay_factor = 0.1  # Exponential decay
    
    async def analyze_spatial_relationships(
        self,
        lat: float,
        lng: float,
        pois: List[Dict],
        infrastructure: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze spatial relationships for a location"""
        
        # Calculate distance-weighted scores
        poi_scores = self._calculate_poi_scores(lat, lng, pois)
        
        # Calculate accessibility
        accessibility = self._calculate_accessibility(lat, lng, infrastructure)
        
        # Detect neighborhood cluster
        cluster = self._detect_neighborhood_cluster(lat, lng, pois)
        
        # Identify growth corridors
        corridors = self._identify_growth_corridors(lat, lng, infrastructure)
        
        return {
            'poi_scores': poi_scores,
            'accessibility_score': accessibility,
            'neighborhood_cluster': cluster,
            'growth_corridors': corridors,
            'spatial_grade': self._calculate_spatial_grade(poi_scores, accessibility)
        }
    
    def _calculate_poi_scores(
        self,
        lat: float,
        lng: float,
        pois: List[Dict]
    ) -> Dict[str, float]:
        """Calculate distance-weighted POI scores"""
        
        categories = {
            'education': [],
            'healthcare': [],
            'shopping': [],
            'transport': [],
            'recreation': []
        }
        
        for poi in pois:
            category = poi.get('category', 'other')
            distance = poi.get('distance_m', 1000)
            
            # Apply distance decay
            decay = math.exp(-self.distance_decay_factor * distance / 1000)
            
            if category in categories:
                categories[category].append(decay)
        
        # Calculate weighted scores per category
        scores = {}
        for cat, values in categories.items():
            if values:
                scores[cat] = sum(values) / len(values)
            else:
                scores[cat] = 0.0
        
        return scores
    
    def _calculate_accessibility(
        self,
        lat: float,
        lng: float,
        infrastructure: List[Dict]
    ) -> float:
        """Calculate overall accessibility score"""
        
        if not infrastructure:
            return 0.5
        
        scores = []
        weights = {
            'metro': 1.5,
            'bus': 1.0,
            'highway': 1.2,
            'airport': 0.8,
            'railway': 1.1
        }
        
        for infra in infrastructure:
            infra_type = infra.get('type', 'other')
            distance = infra.get('distance_m', 5000)
            
            weight = weights.get(infra_type, 1.0)
            decay = math.exp(-self.distance_decay_factor * distance / 1000)
            
            scores.append(decay * weight)
        
        if scores:
            return min(1.0, sum(scores) / len(scores))
        return 0.5
    
    def _detect_neighborhood_cluster(
        self,
        lat: float,
        lng: float,
        pois: List[Dict]
    ) -> str:
        """Detect neighborhood type based on POI composition"""
        
        poi_types = {}
        for poi in pois:
            ptype = poi.get('type', 'other')
            poi_types[ptype] = poi_types.get(ptype, 0) + 1
        
        # Classify based on dominant POI types
        if poi_types.get('office', 0) > 5:
            return 'commercial_hub'
        elif poi_types.get('school', 0) > 3:
            return 'family_residential'
        elif poi_types.get('mall', 0) > 2:
            return 'retail_district'
        elif poi_types.get('tech_park', 0) > 0:
            return 'tech_corridor'
        
        return 'mixed_use'
    
    def _identify_growth_corridors(
        self,
        lat: float,
        lng: float,
        infrastructure: List[Dict]
    ) -> List[Dict]:
        """Identify potential growth corridors"""
        
        corridors = []
        
        for infra in infrastructure:
            if infra.get('type') in ['metro', 'highway', 'tech_park']:
                corridors.append({
                    'type': infra.get('type'),
                    'name': infra.get('name', 'Unknown'),
                    'distance': infra.get('distance_m', 0),
                    'growth_potential': 'high' if infra.get('distance_m', 5000) < 2000 else 'moderate'
                })
        
        return corridors[:3]  # Top 3 corridors
    
    def _calculate_spatial_grade(
        self,
        poi_scores: Dict[str, float],
        accessibility: float
    ) -> str:
        """Calculate overall spatial grade"""
        
        avg_poi = sum(poi_scores.values()) / len(poi_scores) if poi_scores else 0
        combined = (avg_poi + accessibility) / 2
        
        if combined > 0.8:
            return 'A+'
        elif combined > 0.7:
            return 'A'
        elif combined > 0.6:
            return 'B+'
        elif combined > 0.5:
            return 'B'
        elif combined > 0.4:
            return 'C'
        return 'D'


# ============================================
# MICRO-CONTEXT AWARENESS
# ============================================

class MicroContextAwareness:
    """
    Captures local nuances
    - Street-level analysis
    - Building-level insights
    - Amenity proximity scoring
    - Micro-market detection
    """
    
    async def analyze_micro_context(
        self,
        lat: float,
        lng: float,
        property_data: Optional[Dict] = None,
        street_data: Optional[Dict] = None
    ) -> MicroContext:
        """Analyze micro-context for a specific location"""
        
        # Street-level scoring
        street_score = await self._analyze_street_level(lat, lng, street_data)
        
        # Building quality assessment
        building_quality = self._assess_building_quality(property_data)
        
        # Amenity proximity
        amenity_prox = self._calculate_amenity_proximity(lat, lng, property_data)
        
        # Micro-market tier
        micro_tier = self._determine_micro_market_tier(
            street_score, building_quality, amenity_prox
        )
        
        return MicroContext(
            street_score=street_score,
            building_quality=building_quality,
            amenity_proximity=amenity_prox,
            micro_market_tier=micro_tier,
            noise_level=self._estimate_noise_level(street_data),
            traffic_impact=self._estimate_traffic_impact(street_data)
        )
    
    async def _analyze_street_level(
        self,
        lat: float,
        lng: float,
        street_data: Optional[Dict]
    ) -> float:
        """Analyze street-level characteristics"""
        
        if not street_data:
            return 0.5
        
        score = 0.5
        
        # Road width factor
        if street_data.get('road_width_m', 0) > 15:
            score += 0.15
        elif street_data.get('road_width_m', 0) > 10:
            score += 0.1
        
        # Street lighting
        if street_data.get('has_street_lighting'):
            score += 0.1
        
        # Footpath quality
        if street_data.get('footpath_quality') == 'good':
            score += 0.1
        
        # Drainage
        if street_data.get('drainage') == 'covered':
            score += 0.1
        
        return min(1.0, score)
    
    def _assess_building_quality(self, property_data: Optional[Dict]) -> float:
        """Assess building quality from property data"""
        
        if not property_data:
            return 0.5
        
        score = 0.5
        
        # Age factor
        age_years = property_data.get('age_years', 10)
        if age_years < 5:
            score += 0.2
        elif age_years < 10:
            score += 0.1
        elif age_years > 20:
            score -= 0.1
        
        # Amenities
        amenities = property_data.get('amenities', [])
        if len(amenities) > 5:
            score += 0.15
        elif len(amenities) > 2:
            score += 0.1
        
        # Maintenance
        if property_data.get('maintenance_quality') == 'good':
            score += 0.15
        
        return min(1.0, max(0.0, score))
    
    def _calculate_amenity_proximity(
        self,
        lat: float,
        lng: float,
        property_data: Optional[Dict]
    ) -> float:
        """Calculate amenity proximity score"""
        
        if not property_data:
            return 0.5
        
        nearby = property_data.get('nearby_amenities', [])
        
        if not nearby:
            return 0.5
        
        score = 0.0
        weights = {
            'grocery': 0.2,
            'pharmacy': 0.15,
            'atm': 0.1,
            'restaurant': 0.1,
            'gym': 0.1,
            'park': 0.15,
            'school': 0.2
        }
        
        for amenity in nearby:
            amenity_type = amenity.get('type', 'other')
            distance = amenity.get('distance_m', 1000)
            
            if distance < 500:  # Within 5 min walk
                score += weights.get(amenity_type, 0.05)
            elif distance < 1000:  # Within 10 min walk
                score += weights.get(amenity_type, 0.05) * 0.5
        
        return min(1.0, score)
    
    def _determine_micro_market_tier(
        self,
        street_score: float,
        building_quality: float,
        amenity_prox: float
    ) -> str:
        """Determine micro-market tier"""
        
        combined = (street_score + building_quality + amenity_prox) / 3
        
        if combined > 0.8:
            return 'premium'
        elif combined > 0.65:
            return 'above_average'
        elif combined > 0.5:
            return 'average'
        elif combined > 0.35:
            return 'below_average'
        return 'emerging'
    
    def _estimate_noise_level(self, street_data: Optional[Dict]) -> str:
        """Estimate noise level"""
        if not street_data:
            return 'moderate'
        
        traffic = street_data.get('traffic_density', 'medium')
        if traffic == 'high':
            return 'high'
        elif traffic == 'low':
            return 'low'
        return 'moderate'
    
    def _estimate_traffic_impact(self, street_data: Optional[Dict]) -> str:
        """Estimate traffic impact"""
        if not street_data:
            return 'moderate'
        
        road_type = street_data.get('road_type', 'local')
        if road_type == 'main_road':
            return 'high'
        elif road_type == 'interior':
            return 'low'
        return 'moderate'


# ============================================
# CONFLICT RESOLUTION
# ============================================

class ConflictResolution:
    """
    Handles contradictory signals
    - Signal detection
    - Conflict classification
    - Resolution strategy
    - Transparent reporting
    """
    
    async def detect_and_resolve_conflicts(
        self,
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect and resolve conflicting signals"""
        
        conflicts = self._detect_conflicts(analysis_data)
        
        if not conflicts:
            return {
                'has_conflicts': False,
                'conflicts': [],
                'resolution': None
            }
        
        resolution = await self._resolve_conflicts(conflicts, analysis_data)
        
        return {
            'has_conflicts': True,
            'conflicts': conflicts,
            'resolution': resolution
        }
    
    def _detect_conflicts(self, data: Dict) -> List[Dict]:
        """Detect conflicting signals in analysis"""
        
        conflicts = []
        
        # Price vs Trend conflict
        price_position = data.get('price_position', 'fair')
        trend = data.get('trend_direction', 'neutral')
        
        if price_position == 'expensive' and trend == 'bullish':
            conflicts.append({
                'type': 'price_trend',
                'description': 'High price but bullish trend',
                'signals': ['Price above market', 'Strong demand growth'],
                'severity': 'moderate'
            })
        
        # Risk vs Return conflict
        risk_level = data.get('risk_level', 'MEDIUM')
        expected_return = data.get('expected_return', 15)
        
        if risk_level == 'HIGH' and expected_return > 20:
            conflicts.append({
                'type': 'risk_return',
                'description': 'High risk with high return projection',
                'signals': ['Elevated risk factors', 'Strong return potential'],
                'severity': 'high'
            })
        
        # Liquidity vs Demand conflict
        liquidity = data.get('liquidity_score', 50)
        demand = data.get('demand_index', 50)
        
        if liquidity < 40 and demand > 60:
            conflicts.append({
                'type': 'liquidity_demand',
                'description': 'Low liquidity but high demand',
                'signals': ['Properties take longer to sell', 'High buyer interest'],
                'severity': 'low'
            })
        
        return conflicts
    
    async def _resolve_conflicts(
        self,
        conflicts: List[Dict],
        data: Dict
    ) -> Dict[str, Any]:
        """Resolve detected conflicts"""
        
        resolutions = []
        
        for conflict in conflicts:
            if conflict['type'] == 'price_trend':
                resolutions.append({
                    'conflict': conflict['type'],
                    'resolution': 'hold_for_appreciation',
                    'reasoning': 'High price justified by strong trend momentum',
                    'recommendation': 'Consider if investment horizon is 3+ years'
                })
            
            elif conflict['type'] == 'risk_return':
                resolutions.append({
                    'conflict': conflict['type'],
                    'resolution': 'risk_adjusted_analysis',
                    'reasoning': 'High returns compensate for elevated risk',
                    'recommendation': 'Suitable for risk-tolerant investors only'
                })
            
            elif conflict['type'] == 'liquidity_demand':
                resolutions.append({
                    'conflict': conflict['type'],
                    'resolution': 'timing_strategy',
                    'reasoning': 'High demand may improve liquidity over time',
                    'recommendation': 'Plan for longer holding period'
                })
        
        return {
            'resolutions': resolutions,
            'overall_assessment': self._calculate_overall_assessment(conflicts)
        }
    
    def _calculate_overall_assessment(self, conflicts: List[Dict]) -> str:
        """Calculate overall conflict assessment"""
        
        if not conflicts:
            return 'clear'
        
        severities = [c.get('severity', 'low') for c in conflicts]
        
        if 'high' in severities:
            return 'requires_careful_analysis'
        elif 'moderate' in severities:
            return 'mixed_signals'
        return 'minor_conflicts'


# ============================================
# COGNITIVE WORKFLOW ENGINE (MAIN)
# ============================================

class CognitiveWorkflowEngine:
    """
    Main cognitive workflow engine that orchestrates all reasoning components
    """
    
    def __init__(self):
        self.temporal_engine = AdaptiveTemporalContext()
        self.reasoning_layer = AdaptiveReasoningLayer()
        self.spatial_reasoning = SpatialRelationshipReasoning()
        self.micro_context = MicroContextAwareness()
        self.conflict_resolver = ConflictResolution()
    
    async def analyze(
        self,
        lat: float,
        lng: float,
        query: str,
        market_data: Dict[str, Any],
        spatial_data: Dict[str, Any],
        property_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Run full cognitive analysis"""
        
        # 1. Classify intent and select reasoning mode
        intent = await self.reasoning_layer.classify_intent(query)
        mode = self.reasoning_layer.select_reasoning_mode(intent)
        
        # 2. Analyze temporal context
        temporal_context = await self.temporal_engine.analyze_temporal_context(
            market_data, None
        )
        
        # 3. Analyze spatial relationships
        spatial_analysis = await self.spatial_reasoning.analyze_spatial_relationships(
            lat, lng,
            spatial_data.get('pois', []),
            spatial_data.get('infrastructure', [])
        )
        
        # 4. Analyze micro-context
        micro = await self.micro_context.analyze_micro_context(
            lat, lng, property_data, spatial_data.get('street_data')
        )
        
        # 5. Calibrate confidence
        confidence = await self.reasoning_layer.calibrate_confidence(
            data_quality=spatial_data.get('data_quality', 0.8),
            model_output={
                'verdict': market_data.get('verdict', 'HOLD'),
                'confidence': market_data.get('confidence', 0.75),
                'spatial_data': spatial_data,
                'market_data': market_data
            }
        )
        
        # 6. Detect and resolve conflicts
        conflict_analysis = await self.conflict_resolver.detect_and_resolve_conflicts({
            'price_position': market_data.get('price_position'),
            'trend_direction': temporal_context.trend_direction,
            'risk_level': market_data.get('risk_level'),
            'expected_return': market_data.get('expected_return'),
            'liquidity_score': market_data.get('liquidity_score'),
            'demand_index': market_data.get('demand_index')
        })
        
        return {
            'intent': intent,
            'reasoning_mode': mode.value,
            'temporal_context': temporal_context.to_dict(),
            'spatial_analysis': spatial_analysis,
            'micro_context': micro.to_dict(),
            'confidence': confidence.to_dict(),
            'conflict_analysis': conflict_analysis,
            'analysis_timestamp': datetime.now().isoformat()
        }


# Singleton instance
_cognitive_engine = None

def get_cognitive_engine() -> CognitiveWorkflowEngine:
    """Get or create cognitive workflow engine instance"""
    global _cognitive_engine
    if _cognitive_engine is None:
        _cognitive_engine = CognitiveWorkflowEngine()
    return _cognitive_engine
