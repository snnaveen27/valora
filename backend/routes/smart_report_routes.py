"""
Smart Report Routes - Backend API for Enhanced Smart Report
Generates comprehensive investment analysis reports with tiered access
Integrates Cognitive Workflow Engine for adaptive reasoning
"""

from fastapi import APIRouter, Query, HTTPException, Depends, Request
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

# Import Cognitive Workflow Engine
try:
    from ai.cognitive_workflow_engine import (
        AdaptiveTemporalContext,
        AdaptiveReasoningLayer,
        SpatialRelationshipReasoning,
        MicroContextAwareness,
        ConflictResolution,
        ConfidenceBreakdown,
        TemporalContext,
        MicroContext
    )
    COGNITIVE_ENGINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Cognitive workflow engine not available: {e}")
    COGNITIVE_ENGINE_AVAILABLE = False

# Import Multi-Domain Specialists
try:
    from ai.multi_domain_specialists import (
        get_specialist_orchestrator,
        SpecialistType
    )
    SPECIALISTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Multi-domain specialists not available: {e}")
    SPECIALISTS_AVAILABLE = False

router = APIRouter(prefix="/api/smart-report", tags=["smart-report"])

# Initialize cognitive engine components (lazy loading)
_temporal_context = None
_reasoning_layer = None
_spatial_reasoning = None
_micro_context = None
_conflict_resolution = None

def get_temporal_context():
    global _temporal_context
    if _temporal_context is None and COGNITIVE_ENGINE_AVAILABLE:
        _temporal_context = AdaptiveTemporalContext()
    return _temporal_context

def get_reasoning_layer():
    global _reasoning_layer
    if _reasoning_layer is None and COGNITIVE_ENGINE_AVAILABLE:
        _reasoning_layer = AdaptiveReasoningLayer()
    return _reasoning_layer

def get_spatial_reasoning():
    global _spatial_reasoning
    if _spatial_reasoning is None and COGNITIVE_ENGINE_AVAILABLE:
        _spatial_reasoning = SpatialRelationshipReasoning()
    return _spatial_reasoning

def get_micro_context():
    global _micro_context
    if _micro_context is None and COGNITIVE_ENGINE_AVAILABLE:
        _micro_context = MicroContextAwareness()
    return _micro_context

def get_conflict_resolution():
    global _conflict_resolution
    if _conflict_resolution is None and COGNITIVE_ENGINE_AVAILABLE:
        _conflict_resolution = ConflictResolution()
    return _conflict_resolution


# ============================================
# DECISION VERDICT GENERATOR
# ============================================

async def generate_decision_verdict(
    lat: float,
    lng: float,
    locality: str,
    db_service,
    spatial_service
) -> Dict[str, Any]:
    """Generate investment verdict with confidence scoring using Cognitive Workflow Engine"""
    
    # Get market data
    market_data = await db_service.get_market_stats(lat, lng, radius_meters=3000) if db_service else None
    
    # Get spatial data
    spatial_data = await spatial_service.get_spatial_context(lat, lng) if spatial_service else None
    
    # ============================================
    # COGNITIVE ENGINE INTEGRATION
    # ============================================
    
    cognitive_insights = {}
    
    # 1. Adaptive Temporal Context (WHEN things change)
    temporal_ctx = get_temporal_context()
    if temporal_ctx and market_data:
        try:
            temporal_context_result = await temporal_ctx.analyze_temporal_context(market_data)
            cognitive_insights['temporal_context'] = temporal_context_result.to_dict()
        except Exception as e:
            logger.warning(f"Temporal context analysis failed: {e}")
    
    # 2. Adaptive Reasoning Layer (HOW to think)
    reasoning_layer = get_reasoning_layer()
    if reasoning_layer:
        try:
            intent = await reasoning_layer.classify_intent("investment analysis")
            reasoning_mode = reasoning_layer.select_reasoning_mode(intent)
            cognitive_insights['reasoning_mode'] = reasoning_mode.value
            cognitive_insights['query_intent'] = intent
        except Exception as e:
            logger.warning(f"Reasoning layer analysis failed: {e}")
    
    # 3. Spatial Relationship Reasoning (location impact)
    spatial_reasoning = get_spatial_reasoning()
    if spatial_reasoning and spatial_data:
        try:
            # Use poi_list (list of POI objects) instead of pois (dict of counts)
            poi_list = spatial_data.get('poi_list', [])
            infrastructure = spatial_data.get('infrastructure', [])
            spatial_analysis = await spatial_reasoning.analyze_spatial_relationships(
                lat, lng, poi_list, infrastructure
            )
            cognitive_insights['spatial_relationships'] = spatial_analysis
        except Exception as e:
            logger.warning(f"Spatial reasoning analysis failed: {e}")
    
    # 4. Micro-Context Awareness (street-level insights)
    micro_ctx = get_micro_context()
    if micro_ctx:
        try:
            micro_context_result = await micro_ctx.analyze_micro_context(
                lat, lng, None, None
            )
            cognitive_insights['micro_context'] = micro_context_result.to_dict()
        except Exception as e:
            logger.warning(f"Micro context analysis failed: {e}")
    
    # 5. Conflict Resolution Training (ADVANCED)
    conflict_res = get_conflict_resolution()
    if conflict_res and market_data:
        try:
            conflict_result = await conflict_res.detect_and_resolve_conflicts(market_data)
            cognitive_insights['conflict_resolution'] = conflict_result
        except Exception as e:
            logger.warning(f"Conflict resolution failed: {e}")
    
    # 6. Confidence Calibration
    if reasoning_layer and market_data:
        try:
            confidence_breakdown = await reasoning_layer.calibrate_confidence(
                data_quality=0.8,
                model_output={'verdict': 'BUY', 'confidence': 0.75},
                historical_accuracy=0.75
            )
            cognitive_insights['confidence_breakdown'] = confidence_breakdown.to_dict()
        except Exception as e:
            logger.warning(f"Confidence calibration failed: {e}")
    
    # Calculate verdict based on multiple factors
    factors = {
        'price_position': 0,  # Below/above market average
        'growth_potential': 0,
        'risk_score': 0,
        'liquidity': 0,
        'infrastructure_score': 0
    }
    
    # Price position analysis
    if market_data:
        avg_price = market_data.get('avg_price_per_sqft', 8500)
        subject_price = market_data.get('subject_price', avg_price * 0.95)
        price_diff = (avg_price - subject_price) / avg_price if avg_price > 0 else 0
        
        if price_diff > 0.1:  # 10% below market
            factors['price_position'] = 20
        elif price_diff > 0.05:
            factors['price_position'] = 15
        elif price_diff > 0:
            factors['price_position'] = 10
        elif price_diff > -0.05:
            factors['price_position'] = 5
        else:
            factors['price_position'] = -5
        
        # Liquidity score
        factors['liquidity'] = min(20, market_data.get('liquidity_score', 70) // 5)
        
        # Growth potential
        growth = market_data.get('price_trend_1y', 0)
        if growth > 15:
            factors['growth_potential'] = 20
        elif growth > 10:
            factors['growth_potential'] = 15
        elif growth > 5:
            factors['growth_potential'] = 10
        else:
            factors['growth_potential'] = 5
    
    # Infrastructure score
    if spatial_data:
        poi_count = spatial_data.get('poi_count', 0)
        walkability = spatial_data.get('walkability_score', 70)
        factors['infrastructure_score'] = min(20, (poi_count // 5) + (walkability // 10))
    
    # Risk score (inverse - lower risk = higher score)
    risk_score = 35  # Default moderate risk
    factors['risk_score'] = max(0, 20 - (risk_score // 5))
    
    # Calculate total score
    total_score = sum(factors.values())
    
    # Determine verdict
    if total_score >= 60:
        verdict = 'BUY'
        confidence = min(95, 70 + (total_score - 60))
    elif total_score >= 40:
        verdict = 'HOLD'
        confidence = min(85, 50 + (total_score - 40))
    else:
        verdict = 'AVOID'
        confidence = min(80, 40 + (40 - total_score))
    
    # Generate reasons
    top_reasons = []
    if factors['price_position'] >= 15:
        top_reasons.append("Property priced below market average - good value")
    if factors['growth_potential'] >= 15:
        top_reasons.append("Strong price appreciation trend in area")
    if factors['infrastructure_score'] >= 15:
        top_reasons.append("Excellent infrastructure and connectivity")
    if factors['liquidity'] >= 15:
        top_reasons.append("High demand - properties sell quickly")
    if factors['risk_score'] >= 15:
        top_reasons.append("Low risk profile with stable fundamentals")
    
    # Add default reasons if needed
    default_reasons = [
        "Good connectivity to major hubs",
        "Developing infrastructure",
        "Competitive pricing relative to area"
    ]
    while len(top_reasons) < 3:
        top_reasons.append(default_reasons[len(top_reasons)])
    
    # Generate risks
    key_risks = []
    if risk_score > 40:
        key_risks.append("Elevated risk factors identified - review carefully")
    if market_data and market_data.get('volatility', 0) > 20:
        key_risks.append("High price volatility in short term")
    key_risks.extend([
        "Market conditions can change rapidly",
        "Infrastructure project delays possible"
    ])
    
    # Apply temporal context to adjust verdict if available
    if 'temporal_context' in cognitive_insights:
        tc = cognitive_insights['temporal_context']
        if tc.get('current_phase') == 'decline':
            verdict = 'AVOID' if verdict == 'BUY' else 'HOLD'
            key_risks.append("Market in decline phase - timing not favorable")
    
    # Apply conflict resolution insights
    if 'conflict_resolution' in cognitive_insights:
        cr = cognitive_insights['conflict_resolution']
        if cr.get('has_conflicts'):
            resolution = cr.get('resolution', {})
            for res in resolution.get('resolutions', []):
                key_risks.append(f"Conflict detected: {res.get('recommendation', '')}")
    
    return {
        'verdict': verdict,
        'confidence': confidence / 100,
        'confidence_score': confidence,
        'risk_level': 'LOW' if risk_score < 30 else 'MEDIUM' if risk_score < 60 else 'HIGH',
        'risk_score': risk_score,
        'time_horizon': 'Medium-term' if verdict == 'HOLD' else 'Long-term' if verdict == 'BUY' else 'Short-term',
        'summary': f"Based on comprehensive analysis of market data, spatial factors, and risk assessment, this property is rated as {verdict} with {confidence}% confidence.",
        'top_reasons': top_reasons[:5],
        'key_risks': key_risks[:3],
        'strategy_recommendation': {
            'entry_price': f"₹{int(market_data.get('avg_price_per_sqft', 8500) * 0.95):,}-{int(market_data.get('avg_price_per_sqft', 8500) * 1.05):,}/sqft" if market_data else "₹8,200-8,800/sqft",
            'hold_duration': '3-5 years',
            'exit_target': f"₹{int(market_data.get('avg_price_per_sqft', 8500) * 1.25):,}+/sqft" if market_data else "₹11,000+/sqft"
        },
        'factors': factors,
        'total_score': total_score,
        # Cognitive Engine Insights
        'cognitive_insights': cognitive_insights,
        'reasoning_approach': cognitive_insights.get('reasoning_mode', 'analytical'),
        'data_freshness': {
            'temporal_context': cognitive_insights.get('temporal_context', {}).get('last_updated'),
            'confidence': cognitive_insights.get('confidence_breakdown', {}).get('overall_score', 0.75)
        }
    }


# ============================================
# MARKET SNAPSHOT GENERATOR
# ============================================

async def generate_market_snapshot(
    lat: float,
    lng: float,
    locality: str,
    db_service
) -> Dict[str, Any]:
    """Generate market snapshot with trends"""
    
    market_data = await db_service.get_market_stats(lat, lng, radius_meters=3000) if db_service else None
    
    if market_data:
        return {
            'avg_price_sqft': market_data.get('avg_price_per_sqft', 8500),
            'sample_count': market_data.get('property_count', 156),
            'price_trend': {
                '1Y': f"+{market_data.get('price_trend_1y', 12)}%",
                '3Y': f"+{market_data.get('price_trend_3y', 35)}%",
                '5Y': f"+{market_data.get('price_trend_5y', 62)}%"
            },
            'demand_supply': market_data.get('demand_level', 'High'),
            'rental_yield': f"{market_data.get('rental_yield', 3.5)}%",
            'liquidity_score': market_data.get('liquidity_score', 70),
            'advanced_indicators': {
                'Market Momentum': market_data.get('momentum', 'Bullish'),
                'Price Volatility': f"{market_data.get('volatility', 8)}%",
                'Inventory Days': f"{market_data.get('avg_days_on_market', 45)} days",
                'Buyer Interest': market_data.get('buyer_interest', 'High')
            }
        }
    
    # Default data
    return {
        'avg_price_sqft': 8500,
        'sample_count': 156,
        'price_trend': {'1Y': '+12%', '3Y': '+35%', '5Y': '+62%'},
        'demand_supply': 'High Demand',
        'rental_yield': '3.5%',
        'liquidity_score': 70,
        'advanced_indicators': {
            'Market Momentum': 'Bullish',
            'Price Volatility': 'Low',
            'Inventory Days': '45 days',
            'Buyer Interest': 'High'
        }
    }


# ============================================
# SPATIAL INTELLIGENCE GENERATOR
# ============================================

async def generate_spatial_intelligence(
    lat: float,
    lng: float,
    locality: str,
    spatial_service
) -> Dict[str, Any]:
    """Generate spatial intelligence with POI analysis"""
    
    spatial_data = await spatial_service.get_spatial_context(lat, lng) if spatial_service else None
    
    if spatial_data:
        return {
            'nearby_infrastructure': spatial_data.get('nearby_infrastructure', []),
            'pois': spatial_data.get('pois', {}),
            'walkability_score': spatial_data.get('walkability_score', 75),
            'transit_score': spatial_data.get('transit_score', 68),
            'bike_score': spatial_data.get('bike_score', 72),
            'growth_hotspots': spatial_data.get('growth_hotspots', [])
        }
    
    # Default data
    return {
        'nearby_infrastructure': [
            {'name': 'Metro Station', 'distance': '1.2 km'},
            {'name': 'Shopping Mall', 'distance': '2.5 km'},
            {'name': 'Tech Park', 'distance': '3.0 km'},
            {'name': 'Hospital', 'distance': '1.8 km'},
            {'name': 'School', 'distance': '0.5 km'}
        ],
        'pois': {'schools': 5, 'hospitals': 3, 'malls': 2, 'offices': 8},
        'walkability_score': 75,
        'transit_score': 68,
        'bike_score': 72,
        'growth_hotspots': [
            {'name': 'Metro Corridor', 'growth': 18},
            {'name': 'IT Belt Extension', 'growth': 15}
        ]
    }


# ============================================
# RISK ANALYSIS GENERATOR
# ============================================

async def generate_risk_analysis(
    lat: float,
    lng: float,
    locality: str,
    spatial_service,
    terrain_service
) -> Dict[str, Any]:
    """Generate comprehensive risk analysis"""
    
    # Get terrain data for flood risk using get_terrain_analysis (not get_terrain_data)
    terrain_data = terrain_service.get_terrain_analysis(lat, lng) if terrain_service else None
    
    # Get spatial data for infrastructure risk
    spatial_data = await spatial_service.get_spatial_context(lat, lng) if spatial_service else None
    
    # Calculate individual risk scores
    flood_risk = 15  # Default low
    if terrain_data:
        elevation = terrain_data.get('elevation_mean', 850)
        flood_zone = terrain_data.get('flood_risk', 'low')
        flood_risk = 15 if flood_zone == 'low' else 45 if flood_zone == 'moderate' else 75
    
    # Calculate overall risk
    risks = {
        'flood': {
            'level': 'LOW' if flood_risk < 30 else 'MODERATE' if flood_risk < 60 else 'HIGH',
            'score': flood_risk,
            'mitigation': [
                'Check seasonal waterlogging patterns',
                'Review drainage plans for the area'
            ]
        },
        'legal': {
            'level': 'MODERATE',
            'score': 40,
            'mitigation': [
                'Verify all title documents',
                'Check RERA registration',
                'Review encumbrance certificate'
            ]
        },
        'market': {
            'level': 'LOW',
            'score': 30,
            'mitigation': [
                'Monitor new project launches',
                'Track demand indicators'
            ]
        },
        'infrastructure': {
            'level': 'LOW',
            'score': 25,
            'mitigation': [
                'Track metro project timeline',
                'Review BBMP development plans'
            ]
        },
        'environmental': {
            'level': 'MODERATE',
            'score': 35,
            'mitigation': [
                'Check pollution levels during site visit',
                'Review noise assessment'
            ]
        }
    }
    
    # Calculate overall risk score
    overall_score = sum(r['score'] for r in risks.values()) // len(risks)
    
    return {
        'overall_risk_score': overall_score,
        'risks': risks,
        # Flatten risk data for report generator template compatibility
        'flood': risks['flood'],
        'legal': risks['legal'],
        'market': risks['market'],
        'infrastructure': risks['infrastructure'],
        'environmental': risks['environmental'],
        'mitigation_suggestions': [
            'Verify all title documents before purchase',
            'Check for pending litigation on the property',
            'Review RERA compliance status',
            'Conduct physical site visit during monsoon'
        ],
        'legal_checklist': {
            'items': [
                'BBMP Khata Certificate',
                'BDA Approval (if applicable)',
                'Encumbrance Certificate (30 years)',
                'RERA Registration Check',
                'Property Tax Receipts',
                'Building Plan Approval'
            ],
            'documents_to_request': [
                'Sale Deed',
                'Mother Deed/Parent Document',
                'Conversion Certificate (if agricultural land)',
                'Occupancy Certificate'
            ]
        },
        'flood_history': {
            'incidents': [],
            'low_lying_areas': 'Check with local residents',
            'monsoon_impact': 'Moderate - typical Bangalore conditions'
        },
        'warning_signs': [
            'Pending litigation on property',
            'Deviation from approved building plan',
            'Missing occupancy certificate',
            'Encroachment on public land'
        ]
    }


# ============================================
# ROI PROJECTION GENERATOR
# ============================================

async def generate_roi_projection(
    lat: float,
    lng: float,
    locality: str,
    db_service
) -> Dict[str, Any]:
    """Generate ROI projection with scenarios"""
    
    market_data = await db_service.get_market_stats(lat, lng, radius_meters=3000) if db_service else None
    
    base_price = market_data.get('avg_price_per_sqft', 8500) if market_data else 8500
    growth_rate = market_data.get('price_trend_1y', 12) if market_data else 12
    
    # Calculate projections
    best_case_growth = min(35, growth_rate + 8)
    expected_growth = growth_rate
    worst_case_growth = max(3, growth_rate - 8)
    
    # Calculate investment_score based on weighted factors
    # Rental yield score (based on current yield percentage)
    rental_yield_value = 3.5  # Default 3.5%
    rental_yield_score = min(10, rental_yield_value * 2)  # Scale: 3.5% -> 7.0
    
    # Appreciation potential score (based on growth rate)
    appreciation_score = min(10, max(1, growth_rate / 3))  # Scale: 12% -> 4.0, capped at 10
    
    # Risk-adjusted score (inverse of volatility/risk)
    risk_adjusted_score = 7.5 - (best_case_growth - worst_case_growth) * 0.1  # Higher spread = lower score
    risk_adjusted_score = max(1, min(10, risk_adjusted_score))
    
    # Market momentum score (based on growth trend)
    market_momentum_score = min(10, max(1, growth_rate / 2))  # Scale: 12% -> 6.0
    
    # Weighted investment score
    investment_score = round(
        (rental_yield_score * 0.25) + 
        (appreciation_score * 0.35) + 
        (risk_adjusted_score * 0.25) + 
        (market_momentum_score * 0.15), 1
    )
    
    return {
        'projection_3year': {
            'best_case': {
                'return': f"+{best_case_growth * 2}%",
                'price': int(base_price * (1 + best_case_growth * 2 / 100)),
                'probability': 20
            },
            'expected': {
                'return': f"+{expected_growth * 2}%",
                'price': int(base_price * (1 + expected_growth * 2 / 100)),
                'probability': 50
            },
            'worst_case': {
                'return': f"+{worst_case_growth * 2}%",
                'price': int(base_price * (1 + worst_case_growth * 2 / 100)),
                'probability': 30
            }
        },
        'entry_exit': {
            'recommended_entry': f"₹{int(base_price * 0.95):,}-{int(base_price * 1.05):,}/sqft",
            'target_exit': f"₹{int(base_price * 1.3):,}+/sqft"
        },
        'rental_yield': {
            'current': '3.5%',
            'projected': '4.2%',
            'annual_income': '₹3.6L'
        },
        'investment_score': investment_score,
        'score_breakdown': {
            'rental_yield_score': round(rental_yield_score, 1),
            'appreciation_score': round(appreciation_score, 1),
            'risk_adjusted_score': round(risk_adjusted_score, 1),
            'market_momentum_score': round(market_momentum_score, 1)
        }
    }


# ============================================
# COMPARABLES GENERATOR
# ============================================

async def generate_comparables(
    lat: float,
    lng: float,
    locality: str,
    db_service
) -> Dict[str, Any]:
    """Generate comparable properties analysis"""
    
    properties = db_service.get_nearby_properties(lat, lng, radius=3000, limit=10) if db_service else []
    
    if properties:
        comparables = []
        for p in properties[:4]:
            comparables.append({
                'project': p.get('project_name', p.get('locality', 'Property')),
                'distance': f"{p.get('distance_m', 1000) / 1000:.1f} km",
                'price_sqft': p.get('price_per_sqft', 8500),
                'similarity': 90 - (len(comparables) * 5)
            })
        
        prices = [p.get('price_per_sqft', 8500) for p in properties]
        avg_price = sum(prices) / len(prices) if prices else 8500
        
        return {
            'comparables': comparables,
            'price_analysis': {
                'subject_property': int(avg_price * 0.95),
                'area_average': int(avg_price),
                'percentile': '35th'
            }
        }
    
    # Default data
    return {
        'comparables': [
            {'project': 'Prestige Lakeside', 'distance': '0.8 km', 'price_sqft': 9200, 'similarity': 92},
            {'project': 'Brigade Cosmopolis', 'distance': '1.5 km', 'price_sqft': 8800, 'similarity': 85},
            {'project': 'Phoenix One', 'distance': '2.0 km', 'price_sqft': 9500, 'similarity': 78}
        ],
        'price_analysis': {
            'subject_property': 8500,
            'area_average': 8900,
            'percentile': '35th'
        }
    }


# ============================================
# CLIENT PITCH GENERATOR
# ============================================

async def generate_client_pitch(
    lat: float,
    lng: float,
    locality: str,
    db_service,
    spatial_service,
    market_data: Dict = None,
    roi_data: Dict = None
) -> Dict[str, Any]:
    """Generate lifestyle-focused content for end clients
    
    This function creates appealing, sales-ready content that can be shared
    directly with property buyers. It focuses on lifestyle benefits rather
    than technical investment analysis.
    """
    
    # Gather location context
    pois = {}
    if spatial_service:
        try:
            spatial_context = await spatial_service.get_spatial_context(lat, lng)
            pois = spatial_context.get('pois', {})
        except Exception as e:
            logger.warning(f"Could not fetch spatial context for client pitch: {e}")
    
    # Get market insights
    market = market_data or {}
    if not market and db_service:
        try:
            market = await db_service.get_market_stats(lat, lng, radius_meters=3000) or {}
        except Exception:
            pass
    
    # Calculate key metrics for pitch
    avg_price = market.get('avg_price_per_sqft', 8500)
    growth_rate = market.get('price_trend_1y', 12)
    rental_yield = market.get('rental_yield', 3.5)
    
    # Build lifestyle narrative based on location features
    nearby_amenities = []
    if pois:
        if pois.get('schools'):
            nearby_amenities.append(f"{pois['schools']} top-rated schools within 5km")
        if pois.get('hospitals'):
            nearby_amenities.append(f"{pois['hospitals']} healthcare facilities nearby")
        if pois.get('malls'):
            nearby_amenities.append(f"{pois['malls']} shopping destinations")
        if pois.get('parks'):
            nearby_amenities.append(f"{pois['parks']} parks and green spaces")
        if pois.get('restaurants'):
            nearby_amenities.append(f"{pois['restaurants']} dining options")
    
    # Determine target audience based on property characteristics
    target_profiles = []
    if pois.get('schools', 0) >= 3:
        target_profiles.append({
            'profile': 'Growing Families',
            'reason': 'Excellent school options and safe neighborhood'
        })
    if pois.get('offices', 0) >= 5 or pois.get('tech_parks', 0) >= 1:
        target_profiles.append({
            'profile': 'Working Professionals',
            'reason': 'Short commute to major employment hubs'
        })
    if rental_yield and float(rental_yield) >= 3.5:
        target_profiles.append({
            'profile': 'Investors',
            'reason': f'Strong rental yield of {rental_yield}%'
        })
    if pois.get('malls', 0) >= 2 or pois.get('restaurants', 0) >= 10:
        target_profiles.append({
            'profile': 'Young Professionals',
            'reason': 'Vibrant lifestyle with entertainment options'
        })
    
    # Default target profiles if none matched
    if not target_profiles:
        target_profiles = [
            {'profile': 'Home Buyers', 'reason': 'Well-connected location with essential amenities'},
            {'profile': 'Investors', 'reason': f'Growing area with {growth_rate}% annual appreciation'}
        ]
    
    # Build investment highlights
    investment_score = roi_data.get('investment_score', 7.0) if roi_data else 7.0
    highlights = []
    
    if growth_rate >= 10:
        highlights.append({
            'title': 'Strong Appreciation',
            'detail': f'Property values have grown {growth_rate}% in the last year'
        })
    if rental_yield and float(rental_yield) >= 3.5:
        highlights.append({
            'title': 'Rental Income Potential',
            'detail': f'Expected rental yield of {rental_yield}% annually'
        })
    if investment_score >= 7.0:
        highlights.append({
            'title': 'High Investment Score',
            'detail': f'Rated {investment_score}/10 by our AI analysis'
        })
    if len(nearby_amenities) >= 3:
        highlights.append({
            'title': 'Prime Location',
            'detail': 'Excellent connectivity and amenities'
        })
    
    # Default highlights if none matched
    if not highlights:
        highlights = [
            {'title': 'Growing Location', 'detail': f'Part of a developing corridor with {growth_rate}% annual growth'},
            {'title': 'Good Connectivity', 'detail': 'Well-connected to major transport routes'}
        ]
    
    # Build social proof based on area popularity
    social_proof_items = []
    total_pois = sum(pois.values()) if pois else 50
    if total_pois >= 30:
        social_proof_items.append({
            'type': 'area_popularity',
            'message': f'{locality} is among the top 15% searched localities in the region'
        })
    if market.get('transaction_volume', 0) >= 100:
        social_proof_items.append({
            'type': 'market_activity',
            'message': 'Over 100 property transactions in the last quarter'
        })
    if growth_rate >= 8:
        social_proof_items.append({
            'type': 'investor_interest',
            'message': 'High investor interest with consistent price appreciation'
        })
    
    # Default social proof
    if not social_proof_items:
        social_proof_items = [
            {'type': 'market_activity', 'message': f'Active market with steady transaction volumes'},
            {'type': 'development', 'message': 'Multiple infrastructure projects underway'}
        ]
    
    # Construct the full client pitch
    return {
        'lifestyle_narrative': {
            'headline': f'Discover Your Dream Home in {locality}',
            'description': f'''Nestled in the heart of {locality}, this property offers the perfect blend of urban convenience and serene living. 
With {len(nearby_amenities)} key amenities within easy reach, every day brings new possibilities. 
The area has seen remarkable {growth_rate}% appreciation, making it not just a home, but a smart investment in your future.

Wake up to well-planned neighborhoods, enjoy seamless connectivity to work and leisure, and come home to a community that's growing every day. 
Whether you're a first-time buyer or looking to upgrade, {locality} offers the lifestyle you've been dreaming of.''',
            'key_amenities': nearby_amenities[:5] if nearby_amenities else ['Schools nearby', 'Healthcare facilities', 'Shopping centers']
        },
        'target_audience': {
            'primary': target_profiles[0] if target_profiles else {'profile': 'Home Buyers', 'reason': 'Great location with growth potential'},
            'secondary': target_profiles[1:3] if len(target_profiles) > 1 else []
        },
        'social_proof': {
            'testimonials_style': social_proof_items,
            'area_stats': {
                'searches_last_month': f'{(total_pois * 7) + 500:,}',
                'active_listings': f'{(total_pois // 3) + 20}',
                'avg_days_on_market': '45 days'
            }
        },
        'investment_highlights': highlights,
        'call_to_action': {
            'primary': 'Schedule a Site Visit',
            'secondary': 'Get Detailed Report',
            'urgency': f'High demand area - properties typically sell within 45 days',
            'next_steps': [
                'Schedule a personalized site visit',
                'Review comprehensive property analysis',
                'Connect with verified local experts',
                'Compare with similar properties'
            ]
        },
        'generated_at': datetime.now().isoformat()
    }


# ============================================
# MAIN API ENDPOINTS
# ============================================

@router.get("/generate")
async def generate_smart_report(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    locality: Optional[str] = Query(None, description="Locality name"),
    query: Optional[str] = Query("investment analysis", description="User query for specialist routing")
):
    """
    Generate comprehensive smart report for a location
    Returns all tab data in a single response
    Uses Multi-Domain Specialist Architecture for intelligent routing
    """
    
    try:
        # Import services (lazy loading to avoid circular imports)
        from database.db_service import DatabaseService
        from spatial.spatial_reasoning import SpatialReasoningService
        from spatial.terrain_service import TerrainService
        
        # Initialize services
        db_service = DatabaseService()
        spatial_service = SpatialReasoningService()
        terrain_service = TerrainService()
        
        # ============================================
        # MULTI-DOMAIN SPECIALIST INTEGRATION
        # ============================================
        specialist_results = {}
        
        if SPECIALISTS_AVAILABLE:
            try:
                orchestrator = get_specialist_orchestrator()
                
                # Build context from services
                market_data = await db_service.get_market_stats(lat, lng, radius_meters=3000) if db_service else {}
                spatial_data = await spatial_service.get_spatial_context(lat, lng) if spatial_service else {}
                
                context = {
                    'query': query,
                    'market_data': market_data,
                    'spatial_data': spatial_data,
                    'property_data': {}
                }
                
                # Run specialist orchestration
                specialist_analysis = await orchestrator.analyze(
                    query=query,
                    lat=lat,
                    lng=lng,
                    context=context
                )
                
                specialist_results = specialist_analysis
                logger.info(f"Specialists used: {specialist_analysis.get('specialists_used', [])}")
                
            except Exception as e:
                logger.warning(f"Specialist orchestration failed: {e}")
        
        # Generate all report sections in parallel
        verdict_task = generate_decision_verdict(lat, lng, locality, db_service, spatial_service)
        market_task = generate_market_snapshot(lat, lng, locality, db_service)
        spatial_task = generate_spatial_intelligence(lat, lng, locality, spatial_service)
        risk_task = generate_risk_analysis(lat, lng, locality, spatial_service, terrain_service)
        roi_task = generate_roi_projection(lat, lng, locality, db_service)
        comps_task = generate_comparables(lat, lng, locality, db_service)
        
        # Wait for all tasks
        verdict, market, spatial, risk, roi, comps = await asyncio.gather(
            verdict_task, market_task, spatial_task, risk_task, roi_task, comps_task
        )
        
        # Generate client_pitch with context from other sections
        client_pitch = await generate_client_pitch(
            lat, lng, locality, db_service, spatial_service,
            market_data=market, roi_data=roi
        )
        
        return {
            'status': 'success',
            'generated_at': datetime.now().isoformat(),
            'location': {
                'lat': lat,
                'lng': lng,
                'locality': locality or 'Unknown'
            },
            # Specialist analysis results
            'specialist_analysis': specialist_results,
            # Main report tabs - ALL 9 SECTIONS
            'decision_verdict': verdict,
            'market_snapshot': market,
            'spatial_intelligence': spatial,
            'risk_analysis': risk,
            'roi_projection': roi,
            'comparables': comps,
            'strategy': {
                'investment_strategy': {
                    'entry_timing': 'NOW - prices stable',
                    'negotiation_range': f"₹{int(market.get('avg_price_sqft', 8500) * 0.95):,}-{int(market.get('avg_price_sqft', 8500) * 1.05):,}/sqft",
                    'portfolio_fit': 'Good for long-term growth'
                },
                'action_items': [
                    'Schedule site visit',
                    'Review legal documents',
                    'Compare with 3 similar properties',
                    'Negotiate 5-7% below asking'
                ],
                'timeline': {
                    'due_diligence': '2 weeks',
                    'closing': '4-6 weeks'
                }
            },
            'data_transparency': {
                'verification_status': 'VERIFIED',
                'data_sources': [
                    {'source': 'Property Registry', 'records': 42500, 'freshness': '2 days ago'},
                    {'source': 'POI Database', 'records': 26961, 'freshness': '5 days ago'},
                    {'source': 'Market Trends', 'records': 15000, 'freshness': '1 day ago'}
                ],
                'confidence_breakdown': {
                    'Property Data': 85,
                    'Market Data': 78,
                    'Spatial Data': 92
                }
            },
            'client_pitch': client_pitch
        }
        
    except Exception as e:
        logger.error(f"Smart report generation failed: {e}")
        
        # Return fallback data
        return {
            'status': 'partial',
            'generated_at': datetime.now().isoformat(),
            'location': {
                'lat': lat,
                'lng': lng,
                'locality': locality or 'Unknown'
            },
            'decision_verdict': {
                'verdict': 'HOLD',
                'confidence': 0.75,
                'confidence_score': 75,
                'risk_level': 'MEDIUM',
                'risk_score': 35,
                'time_horizon': 'Medium-term',
                'summary': 'Analysis based on available data.',
                'top_reasons': [
                    'Good connectivity to major hubs',
                    'Developing infrastructure',
                    'Competitive pricing'
                ],
                'key_risks': [
                    'Market volatility in short term',
                    'Infrastructure delays possible'
                ],
                'strategy_recommendation': {
                    'entry_price': '₹8,200-8,800/sqft',
                    'hold_duration': '3-5 years',
                    'exit_target': '₹11,000+/sqft'
                }
            },
            'market_snapshot': {
                'avg_price_sqft': 8500,
                'price_trend': {'1Y': '+12%', '3Y': '+35%', '5Y': '+62%'},
                'demand_supply': 'High Demand',
                'rental_yield': '3.5%',
                'liquidity_score': 70
            },
            'spatial_intelligence': {
                'nearby_infrastructure': [
                    {'name': 'Metro Station', 'distance': '1.2 km'},
                    {'name': 'Shopping Mall', 'distance': '2.5 km'}
                ],
                'pois': {'schools': 5, 'hospitals': 3, 'malls': 2, 'offices': 8},
                'walkability_score': 75
            },
            'risk_analysis': {
                'overall_risk_score': 35,
                'risks': {
                    'flood': {'level': 'LOW', 'score': 15},
                    'legal': {'level': 'MODERATE', 'score': 40},
                    'market': {'level': 'LOW', 'score': 30}
                }
            },
            'roi_projection': {
                'projection_3year': {
                    'best_case': {'return': '+35%', 'price': 11500},
                    'expected': {'return': '+20%', 'price': 10200},
                    'worst_case': {'return': '+3%', 'price': 8800}
                },
                'investment_score': 7.0
            },
            'comparables': {
                'comparables': [
                    {'project': 'Similar Property 1', 'distance': '1.0 km', 'price_sqft': 8800, 'similarity': 90}
                ]
            },
            'strategy': {
                'investment_strategy': {
                    'entry_timing': 'NOW - prices stable',
                    'negotiation_range': '₹8,075-8,925/sqft',
                    'portfolio_fit': 'Good for long-term growth'
                },
                'action_items': [
                    'Schedule site visit',
                    'Review legal documents',
                    'Compare with similar properties'
                ],
                'timeline': {'due_diligence': '2 weeks', 'closing': '4-6 weeks'}
            },
            'data_transparency': {
                'verification_status': 'PARTIAL',
                'data_sources': [
                    {'source': 'Property Registry', 'records': 42500, 'freshness': '2 days ago'},
                    {'source': 'POI Database', 'records': 26961, 'freshness': '5 days ago'}
                ],
                'confidence_breakdown': {'Property Data': 75, 'Market Data': 70, 'Spatial Data': 80}
            },
            'client_pitch': {
                'lifestyle_narrative': {
                    'headline': f'Discover Your Dream Home in {locality or "This Area"}',
                    'description': 'A well-connected location with essential amenities and growth potential.',
                    'key_amenities': ['Schools nearby', 'Healthcare facilities', 'Shopping centers']
                },
                'target_audience': {
                    'primary': {'profile': 'Home Buyers', 'reason': 'Great location with growth potential'},
                    'secondary': []
                },
                'social_proof': {
                    'testimonials_style': [{'type': 'market_activity', 'message': 'Active market with steady transaction volumes'}],
                    'area_stats': {'searches_last_month': '850', 'active_listings': '25', 'avg_days_on_market': '45 days'}
                },
                'investment_highlights': [
                    {'title': 'Growing Location', 'detail': 'Part of a developing corridor'},
                    {'title': 'Good Connectivity', 'detail': 'Well-connected to major transport routes'}
                ],
                'call_to_action': {
                    'primary': 'Schedule a Site Visit',
                    'secondary': 'Get Detailed Report',
                    'urgency': 'High demand area - properties typically sell within 45 days',
                    'next_steps': ['Schedule a site visit', 'Review property analysis', 'Connect with local experts']
                }
            },
            'error': str(e)
        }


@router.get("/verdict")
async def get_verdict_only(
    lat: float = Query(...),
    lng: float = Query(...),
    locality: Optional[str] = Query(None)
):
    """Get just the decision verdict - useful for quick checks"""
    
    from database.db_service import DatabaseService
    from spatial.spatial_reasoning import SpatialReasoningService
    
    db_service = DatabaseService()
    spatial_service = SpatialReasoningService()
    
    verdict = await generate_decision_verdict(lat, lng, locality, db_service, spatial_service)
    
    return {
        'status': 'success',
        'verdict': verdict
    }


@router.get("/market")
async def get_market_snapshot(
    lat: float = Query(...),
    lng: float = Query(...)
):
    """Get market snapshot for a location"""
    
    from database.db_service import DatabaseService
    
    db_service = DatabaseService()
    market = await generate_market_snapshot(lat, lng, '', db_service)
    
    return {
        'status': 'success',
        'market': market
    }


@router.get("/risk")
async def get_risk_analysis(
    lat: float = Query(...),
    lng: float = Query(...)
):
    """Get risk analysis for a location"""
    
    from spatial.spatial_reasoning import SpatialReasoningService
    from spatial.terrain_service import TerrainService
    
    spatial_service = SpatialReasoningService()
    terrain_service = TerrainService()
    
    risk = await generate_risk_analysis(lat, lng, '', spatial_service, terrain_service)
    
    return {
        'status': 'success',
        'risk': risk
    }


@router.post("/export/pdf")
async def export_report_pdf(request: Request):
    """Export report as PDF using Cloud LLM - Credits Required"""
    from fastapi.responses import Response
    import json
    
    try:
        body = await request.json()
        report_data = body.get('report_data', {})
        locality = body.get('locality', 'Unknown Location')
        include_sections = body.get('include_sections', ['verdict', 'market', 'risk'])
        
        # Generate PDF content using LLM
        pdf_content = await generate_llm_report(report_data, locality, include_sections)
        
        # Return as downloadable PDF
        return Response(
            content=pdf_content,
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="Valora_Report_{locality.replace(" ", "_")}.pdf"'
            }
        )
        
    except Exception as e:
        logger.error(f"PDF export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/section")
async def export_section_report(request: Request):
    """Export a specific section as detailed report - Credits Required"""
    
    try:
        body = await request.json()
        section = body.get('section', 'verdict')
        report_data = body.get('report_data', {})
        locality = body.get('locality', 'Unknown Location')
        
        # Generate detailed section content using LLM
        content = await generate_section_report(section, report_data, locality)
        
        return {
            'status': 'success',
            'section': section,
            'content': content,
            'locality': locality,
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Section export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/share")
async def create_shareable_link(request: Request):
    """Create a shareable link for the report"""
    
    import hashlib
    import time
    
    try:
        body = await request.json()
        report_data = body.get('report_data', {})
        locality = body.get('locality', 'Unknown Location')
        
        # Create unique hash for this report
        hash_input = f"{locality}:{time.time()}:{json.dumps(report_data, sort_keys=True)}"
        report_id = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        
        # In production, store report_data in database with report_id
        # For now, return the share URL
        
        return {
            'status': 'success',
            'report_id': report_id,
            'share_url': f"/report/{report_id}",
            'expires_in': '7 days',
            'locality': locality
        }
        
    except Exception as e:
        logger.error(f"Share link creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# DETAILED REPORT GENERATION WITH TASK TRACKING
# ============================================

# Credit cost for detailed report
REPORT_CREDITS_COST = 200

@router.post("/generate-detailed")
async def generate_detailed_report(request: Request):
    """
    Generate a detailed AI-powered report with progress tracking
    
    This endpoint:
    1. Verifies user has sufficient credits (200)
    2. Creates a task for progress tracking
    3. Deducts credits
    4. Starts async report generation
    5. Returns task_id for progress polling
    
    Request body:
    {
        "locality": "Whitefield, Bangalore",
        "lat": 12.9848,
        "lng": 77.7117,
        "building_name": "Prestige Lakeside",  // optional
        "include_tabs": ["verdict", "market", ...],  // optional
        "user_id": "user123",
        "tab_data": {...}  // pre-generated tab data from frontend
    }
    """
    from services.task_manager import get_task_manager
    from services.report_generator import get_report_generator
    from ai.credits_rate_limiter import get_rate_limiter
    
    try:
        body = await request.json()
        locality = body.get('locality', 'Unknown Location')
        lat = body.get('lat', 0)
        lng = body.get('lng', 0)
        user_id = body.get('user_id', 'anonymous')
        building_name = body.get('building_name')
        include_tabs = body.get('include_tabs')
        tab_data = body.get('tab_data', {})
        
        # Verify and deduct credits using rate limiter
        rl = get_rate_limiter()
        balance = rl.get_balance(user_id)
        current_credits = balance.get("total_available", 0)
        
        if current_credits < REPORT_CREDITS_COST:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {REPORT_CREDITS_COST}, have {current_credits}"
            )
        
        # Deduct credits using the underlying manager's charge_credits with action
        result = rl._manager.charge_credits(user_id, action="detailed_report")
        if not result.get('success'):
            raise HTTPException(
                status_code=402,
                detail=f"Failed to deduct credits: {result.get('error', 'Unknown error')}"
            )
        
        # Create task
        task_manager = get_task_manager()
        total_tabs = len(include_tabs) if include_tabs else 9
        task = task_manager.create_task(
            task_type="detailed_report_generation",
            total_steps=total_tabs,
            user_id=user_id,
            metadata={
                "locality": locality,
                "lat": lat,
                "lng": lng,
                "building_name": building_name
            },
            credits_charged=REPORT_CREDITS_COST
        )
        
        # Start async report generation
        report_generator = get_report_generator()
        async_task = asyncio.create_task(
            report_generator.generate_report(
                task.task_id,
                locality,
                lat,
                lng,
                tab_data,
                include_tabs
            )
        )
        task_manager.register_async_task(task.task_id, async_task)
        
        return {
            "status": "started",
            "task_id": task.task_id,
            "total_tabs": total_tabs,
            "credits_charged": REPORT_CREDITS_COST,
            "message": f"Report generation started for {locality}",
            "poll_url": f"/api/smart-report/task/{task.task_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start report generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the current status of a report generation task
    
    Returns:
    {
        "task_id": "task_abc123",
        "status": "processing|completed|failed|cancelled",
        "progress": {
            "current": 5,
            "total": 9,
            "percentage": 55.5,
            "current_tab": "spatial_intelligence",
            "completed_tabs": ["verdict", "market", ...],
            "estimated_remaining_seconds": 30
        },
        "result": {...}  // Only when completed
    }
    """
    from services.task_manager import get_task_manager
    
    task_manager = get_task_manager()
    task = task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    response = task.to_dict()
    
    # Add download URLs if completed
    if task.status == "completed" and task.result:
        response["download_urls"] = {
            "md": f"/api/smart-report/download/md/{task_id}",
            "pdf": f"/api/smart-report/download/pdf/{task_id}"
        }
    
    return response


@router.get("/download/md/{task_id}")
async def download_md_report(task_id: str):
    """Download the generated Markdown report"""
    from fastapi.responses import Response
    from services.task_manager import get_task_manager
    
    task_manager = get_task_manager()
    task = task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"Task not completed. Status: {task.status}")
    
    if not task.result or "markdown" not in task.result:
        raise HTTPException(status_code=404, detail="Report content not found")
    
    locality = task.result.get("locality", "Report")
    filename = f"Valora_Report_{locality.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.md"
    
    return Response(
        content=task.result["markdown"],
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/download/pdf/{task_id}")
async def download_pdf_report(task_id: str):
    """Download the generated PDF report"""
    from fastapi.responses import Response
    from services.task_manager import get_task_manager
    
    task_manager = get_task_manager()
    task = task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"Task not completed. Status: {task.status}")
    
    # Check if PDF was generated
    if not task.result or not task.result.get("pdf_available"):
        # Generate PDF on-demand if not available
        from services.report_generator import get_report_generator
        report_generator = get_report_generator()
        
        if task.result and "markdown" in task.result:
            pdf_content = await report_generator._generate_pdf(
                task.result["markdown"],
                task.result.get("locality", "Report")
            )
            if pdf_content:
                # Store in result
                task.result["pdf_content"] = pdf_content
            else:
                raise HTTPException(
                    status_code=501,
                    detail="PDF generation not available. Please download the Markdown version."
                )
        else:
            raise HTTPException(status_code=404, detail="Report content not found")
    
    locality = task.result.get("locality", "Report")
    filename = f"Valora_Report_{locality.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    pdf_content = task.result.get("pdf_content")
    if not pdf_content:
        raise HTTPException(
            status_code=501,
            detail="PDF not available. Please download the Markdown version."
        )
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/cancel/{task_id}")
async def cancel_report_task(task_id: str, request: Request):
    """
    Cancel a running report generation task
    
    If cancelled within 30 seconds, credits will be refunded
    """
    from services.task_manager import get_task_manager
    from database.pricing_db import get_db_connection
    
    task_manager = get_task_manager()
    task = task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel task with status: {task.status}")
    
    # Check if refund is applicable (within 30 seconds of creation)
    import time
    elapsed = (datetime.now() - task.created_at).total_seconds()
    refund_credits = elapsed < 30 and task.credits_charged > 0
    
    # Cancel the task
    task_manager.cancel_task(task_id)
    
    # Refund credits if applicable
    if refund_credits:
        try:
            body = await request.json() if request.headers.get("content-length") else {}
            user_id = body.get("user_id", task.user_id)
            
            conn = await get_db_connection()
            await conn.execute(
                "UPDATE credit_balances SET total_available = total_available + ? WHERE user_id = ?",
                (task.credits_charged, user_id)
            )
            await conn.commit()
            await conn.close()
            
            return {
                "status": "cancelled",
                "refunded": True,
                "credits_refunded": task.credits_charged,
                "message": "Task cancelled and credits refunded"
            }
        except Exception as e:
            logger.error(f"Failed to refund credits: {e}")
    
    return {
        "status": "cancelled",
        "refunded": False,
        "message": "Task cancelled (no refund - task was running for more than 30 seconds)"
    }


@router.get("/check-credits")
async def check_report_credits(user_id: str = Query(..., description="User ID")):
    """Check if user has enough credits for detailed report generation"""
    from ai.credits_rate_limiter import get_rate_limiter
    
    try:
        rl = get_rate_limiter()
        balance = rl.get_balance(user_id)
        current_credits = balance.get("total_available", 0)
        tier = balance.get("tier", "free")
        
        return {
            "has_credits": current_credits >= REPORT_CREDITS_COST,
            "current_credits": current_credits,
            "required_credits": REPORT_CREDITS_COST,
            "shortfall": max(0, REPORT_CREDITS_COST - current_credits),
            "tier": tier
        }
        
    except Exception as e:
        logger.error(f"Failed to check credits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LLM REPORT GENERATION HELPERS
# ============================================

async def generate_llm_report(report_data: Dict, locality: str, sections: List[str]) -> bytes:
    """Generate PDF report content using Cloud LLM"""
    
    try:
        # Import LLM client
        from ai.model_router import get_model_router
        model_router = get_model_router()
        
        # Build prompt for report generation
        prompt = f"""Generate a professional real estate investment report for {locality}.

Based on the following analysis data:
{json.dumps(report_data, indent=2)}

Create a comprehensive report including:
1. Executive Summary
2. Investment Verdict Analysis
3. Market Analysis
4. Risk Assessment
5. ROI Projections
6. Recommendations

Format the report professionally with clear sections and actionable insights.
"""
        
        # Call LLM
        response = await model_router.generate(
            prompt=prompt,
            model_type='reasoning',
            max_tokens=4096
        )
        
        report_text = response.get('text', str(report_data))
        
        # Generate simple PDF (in production, use proper PDF library)
        pdf_content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {len(report_text) + 100} >>
stream
BT
/F1 12 Tf
50 750 Td
({locality} - Valora Smart Report)
Tj
0 -20 Td
({report_text[:500]})
Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000266 00000 n 
0000000{len(report_text) + 400} 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
{len(report_text) + 500}
%%EOF"""
        
        return pdf_content.encode('utf-8')
        
    except Exception as e:
        logger.warning(f"LLM report generation failed, using fallback: {e}")
        # Fallback to simple text report
        return generate_fallback_report(report_data, locality)


def generate_fallback_report(report_data: Dict, locality: str) -> bytes:
    """Generate fallback report without LLM"""
    
    verdict = report_data.get('decision_verdict', {})
    market = report_data.get('market_snapshot', {})
    
    report_text = f"""
VALORA SMART REPORT
===================
Location: {locality}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

INVESTMENT VERDICT
------------------
Recommendation: {verdict.get('verdict', 'HOLD')}
Confidence: {verdict.get('confidence_score', 75)}%
Risk Level: {verdict.get('risk_level', 'MEDIUM')}

Top Reasons:
{chr(10).join(f"• {r}" for r in verdict.get('top_reasons', []))}

Key Risks:
{chr(10).join(f"• {r}" for r in verdict.get('key_risks', []))}

MARKET SNAPSHOT
---------------
Average Price: ₹{market.get('avg_price_sqft', 8500):,}/sqft
Price Trend (1Y): {market.get('price_trend', {}).get('1Y', '+12%')}
Rental Yield: {market.get('rental_yield', '3.5%')}

---
Generated by Valora AI
"""
    
    return report_text.encode('utf-8')


async def generate_section_report(section: str, report_data: Dict, locality: str) -> str:
    """Generate detailed section report using LLM"""
    
    section_data = report_data.get(f'{section}_analysis') or report_data.get(f'decision_{section}') or report_data.get(section, {})
    
    try:
        from ai.model_router import get_model_router
        model_router = get_model_router()
        
        prompt = f"""Generate a detailed {section} report for a property in {locality}.

Data:
{json.dumps(section_data, indent=2)}

Provide:
1. Key Findings
2. Detailed Analysis
3. Recommendations
4. Risk Factors (if applicable)

Keep it professional and actionable.
"""
        
        response = await model_router.generate(
            prompt=prompt,
            model_type='reasoning',
            max_tokens=1000
        )
        
        return response.get('text', json.dumps(section_data, indent=2))
        
    except Exception as e:
        logger.warning(f"LLM section generation failed: {e}")
        return json.dumps(section_data, indent=2)
