"""
Multi-Domain Specialist Architecture for Smart Report
Implements specialized agents for different analysis domains
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ============================================
# SPECIALIST TYPES AND INTERFACES
# ============================================

class SpecialistType(Enum):
    PLANNER = "planner"           # Task orchestration
    INVESTOR = "investor"         # ROI focus
    GIS_ANALYST = "gis_analyst"   # Spatial focus
    BUILDING = "building"         # Property focus
    NAVIGATOR = "navigator"       # Location focus
    RISK = "risk"                 # Risk analysis
    MARKET = "market"             # Market analysis


@dataclass
class SpecialistResult:
    """Result from a specialist analysis"""
    specialist_type: SpecialistType
    success: bool
    data: Dict[str, Any]
    confidence: float
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time_ms: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'specialist': self.specialist_type.value,
            'success': self.success,
            'data': self.data,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'timestamp': self.timestamp.isoformat(),
            'execution_time_ms': self.execution_time_ms
        }


class BaseSpecialist(ABC):
    """Base class for all specialists"""
    
    def __init__(self, specialist_type: SpecialistType):
        self.specialist_type = specialist_type
        self.capabilities: List[str] = []
    
    @abstractmethod
    async def analyze(
        self,
        context: Dict[str, Any],
        lat: float,
        lng: float
    ) -> SpecialistResult:
        """Perform specialist analysis"""
        pass
    
    def get_capabilities(self) -> List[str]:
        return self.capabilities


# ============================================
# PLANNER SPECIALIST
# ============================================

class PlannerSpecialist(BaseSpecialist):
    """
    Task orchestration specialist
    - Coordinates other specialists
    - Manages analysis workflow
    - Prioritizes tasks
    """
    
    def __init__(self):
        super().__init__(SpecialistType.PLANNER)
        self.capabilities = [
            'task_decomposition',
            'workflow_orchestration',
            'priority_management',
            'result_synthesis'
        ]
    
    async def analyze(
        self,
        context: Dict[str, Any],
        lat: float,
        lng: float
    ) -> SpecialistResult:
        start_time = datetime.now()
        
        try:
            # Create analysis plan
            plan = self._create_analysis_plan(context)
            
            # Determine priority order
            priorities = self._prioritize_tasks(plan, context)
            
            # Estimate resource requirements
            estimates = self._estimate_resources(plan)
            
            data = {
                'plan': plan,
                'priorities': priorities,
                'estimates': estimates,
                'recommended_sequence': self._get_sequence(priorities)
            }
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return SpecialistResult(
                specialist_type=self.specialist_type,
                success=True,
                data=data,
                confidence=0.95,
                reasoning="Analysis plan created based on query intent and available data",
                execution_time_ms=int(execution_time)
            )
            
        except Exception as e:
            logger.error(f"Planner specialist error: {e}")
            return SpecialistResult(
                specialist_type=self.specialist_type,
                success=False,
                data={},
                confidence=0.0,
                reasoning=f"Planning failed: {str(e)}"
            )
    
    def _create_analysis_plan(self, context: Dict) -> List[Dict]:
        """Create analysis plan based on context"""
        query = context.get('query', '').lower()
        plan = []
        
        # Always include market analysis
        plan.append({
            'task': 'market_analysis',
            'specialist': 'market',
            'required': True
        })
        
        # Add spatial analysis for location queries
        if any(w in query for w in ['location', 'area', 'neighborhood', 'near']):
            plan.append({
                'task': 'spatial_analysis',
                'specialist': 'gis_analyst',
                'required': True
            })
        
        # Add investment analysis for investment queries
        if any(w in query for w in ['invest', 'buy', 'roi', 'return']):
            plan.append({
                'task': 'investment_analysis',
                'specialist': 'investor',
                'required': True
            })
        
        # Add risk analysis for risk queries
        if any(w in query for w in ['risk', 'safe', 'danger']):
            plan.append({
                'task': 'risk_analysis',
                'specialist': 'risk',
                'required': True
            })
        
        # Add building analysis for property queries
        if any(w in query for w in ['building', 'property', 'apartment']):
            plan.append({
                'task': 'building_analysis',
                'specialist': 'building',
                'required': False
            })
        
        return plan
    
    def _prioritize_tasks(self, plan: List[Dict], context: Dict) -> List[Dict]:
        """Prioritize tasks based on context"""
        # Sort by required flag and relevance
        prioritized = sorted(plan, key=lambda x: (not x.get('required', False), 0))
        return prioritized
    
    def _estimate_resources(self, plan: List[Dict]) -> Dict:
        """Estimate resource requirements"""
        return {
            'estimated_time_ms': len(plan) * 500,
            'api_calls': len(plan),
            'data_sources': len(set(p['specialist'] for p in plan))
        }
    
    def _get_sequence(self, priorities: List[Dict]) -> List[str]:
        """Get execution sequence"""
        return [p['task'] for p in priorities]


# ============================================
# INVESTOR SPECIALIST
# ============================================

class InvestorSpecialist(BaseSpecialist):
    """
    ROI-focused specialist
    - Return calculations
    - Investment metrics
    - Portfolio analysis
    """
    
    def __init__(self):
        super().__init__(SpecialistType.INVESTOR)
        self.capabilities = [
            'roi_calculation',
            'yield_analysis',
            'portfolio_fit',
            'entry_exit_timing'
        ]
    
    async def analyze(
        self,
        context: Dict[str, Any],
        lat: float,
        lng: float
    ) -> SpecialistResult:
        start_time = datetime.now()
        
        try:
            market_data = context.get('market_data', {})
            
            # Calculate ROI metrics
            roi = self._calculate_roi(market_data)
            
            # Analyze yield
            yield_analysis = self._analyze_yield(market_data)
            
            # Assess portfolio fit
            portfolio_fit = self._assess_portfolio_fit(context)
            
            # Determine entry/exit timing
            timing = self._analyze_timing(market_data)
            
            data = {
                'roi': roi,
                'yield_analysis': yield_analysis,
                'portfolio_fit': portfolio_fit,
                'timing': timing,
                'investment_score': self._calculate_investment_score(roi, yield_analysis, timing)
            }
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return SpecialistResult(
                specialist_type=self.specialist_type,
                success=True,
                data=data,
                confidence=0.85,
                reasoning="Investment analysis based on market data and ROI projections",
                execution_time_ms=int(execution_time)
            )
            
        except Exception as e:
            logger.error(f"Investor specialist error: {e}")
            return SpecialistResult(
                specialist_type=self.specialist_type,
                success=False,
                data={},
                confidence=0.0,
                reasoning=f"Investment analysis failed: {str(e)}"
            )
    
    def _calculate_roi(self, market_data: Dict) -> Dict:
        """Calculate ROI projections"""
        base_price = market_data.get('avg_price_per_sqft', 8500)
        growth_rate = market_data.get('price_trend_1y', 10)
        
        return {
            '3_year_expected': f"+{growth_rate * 2}%",
            '5_year_expected': f"+{growth_rate * 3.5}%",
            'annualized_return': f"{growth_rate}%"
        }
    
    def _analyze_yield(self, market_data: Dict) -> Dict:
        """Analyze rental yield"""
        return {
            'gross_yield': market_data.get('rental_yield', '3.5%'),
            'net_yield': '2.8%',
            'yield_trend': 'stable'
        }
    
    def _assess_portfolio_fit(self, context: Dict) -> Dict:
        """Assess portfolio fit"""
        return {
            'diversification_score': 75,
            'risk_contribution': 'moderate',
            'recommendation': 'Good for long-term growth portfolio'
        }
    
    def _analyze_timing(self, market_data: Dict) -> Dict:
        """Analyze entry/exit timing"""
        trend = market_data.get('price_trend_1y', 0)
        
        if trend > 10:
            entry = 'favorable_now'
        elif trend > 5:
            entry = 'good'
        else:
            entry = 'wait_for_dip'
        
        return {
            'entry_timing': entry,
            'exit_horizon': '3-5 years',
            'market_cycle': 'growth' if trend > 5 else 'stable'
        }
    
    def _calculate_investment_score(self, roi: Dict, yield_data: Dict, timing: Dict) -> int:
        """Calculate overall investment score"""
        score = 50
        
        # Add points for good ROI
        if '+' in roi.get('3_year_expected', ''):
            try:
                val = int(roi['3_year_expected'].replace('+', '').replace('%', ''))
                score += min(25, val)
            except:
                pass
        
        # Add points for good timing
        if timing.get('entry_timing') == 'favorable_now':
            score += 15
        elif timing.get('entry_timing') == 'good':
            score += 10
        
        return min(100, score)


# ============================================
# GIS ANALYST SPECIALIST
# ============================================

class GISAnalystSpecialist(BaseSpecialist):
    """
    Spatial analysis specialist
    - POI analysis
    - Connectivity scoring
    - Walkability assessment
    - Growth corridor detection
    """
    
    def __init__(self):
        super().__init__(SpecialistType.GIS_ANALYST)
        self.capabilities = [
            'poi_analysis',
            'connectivity_scoring',
            'walkability_assessment',
            'growth_detection'
        ]
    
    async def analyze(
        self,
        context: Dict[str, Any],
        lat: float,
        lng: float
    ) -> SpecialistResult:
        start_time = datetime.now()
        
        try:
            spatial_data = context.get('spatial_data', {})
            
            # Analyze POIs
            poi_analysis = self._analyze_pois(spatial_data)
            
            # Calculate connectivity
            connectivity = self._calculate_connectivity(spatial_data)
            
            # Assess walkability
            walkability = self._assess_walkability(spatial_data)
            
            # Detect growth areas
            growth = self._detect_growth_areas(lat, lng, spatial_data)
            
            data = {
                'poi_analysis': poi_analysis,
                'connectivity': connectivity,
                'walkability': walkability,
                'growth_areas': growth,
                'spatial_score': self._calculate_spatial_score(poi_analysis, connectivity, walkability)
            }
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return SpecialistResult(
                specialist_type=self.specialist_type,
                success=True,
                data=data,
                confidence=0.90,
                reasoning="Spatial analysis based on POI data and connectivity metrics",
                execution_time_ms=int(execution_time)
            )
            
        except Exception as e:
            logger.error(f"GIS specialist error: {e}")
            return SpecialistResult(
                specialist_type=self.specialist_type,
                success=False,
                data={},
                confidence=0.0,
                reasoning=f"Spatial analysis failed: {str(e)}"
            )
    
    def _analyze_pois(self, spatial_data: Dict) -> Dict:
        """Analyze POI distribution"""
        pois = spatial_data.get('pois', {})
        
        return {
            'total_count': sum(pois.values()) if isinstance(pois, dict) else 0,
            'categories': pois,
            'density': 'high' if sum(pois.values()) > 20 else 'moderate' if isinstance(pois, dict) else 'low'
        }
    
    def _calculate_connectivity(self, spatial_data: Dict) -> Dict:
        """Calculate connectivity score"""
        infra = spatial_data.get('infrastructure', [])
        
        metro_access = any(i.get('type') == 'metro' for i in infra)
        highway_access = any(i.get('type') == 'highway' for i in infra)
        
        score = 50
        if metro_access:
            score += 25
        if highway_access:
            score += 15
        
        return {
            'score': score,
            'metro_access': metro_access,
            'highway_access': highway_access,
            'grade': 'A' if score > 80 else 'B' if score > 60 else 'C'
        }
    
    def _assess_walkability(self, spatial_data: Dict) -> Dict:
        """Assess walkability"""
        score = spatial_data.get('walkability_score', 70)
        
        return {
            'score': score,
            'grade': 'A' if score > 80 else 'B' if score > 60 else 'C',
            'description': 'Very walkable' if score > 80 else 'Somewhat walkable' if score > 60 else 'Car dependent'
        }
    
    def _detect_growth_areas(self, lat: float, lng: float, spatial_data: Dict) -> List[Dict]:
        """Detect growth areas nearby"""
        # Simplified detection based on infrastructure
        growth_areas = []
        
        infra = spatial_data.get('infrastructure', [])
        for i in infra:
            if i.get('type') in ['metro', 'tech_park', 'highway']:
                growth_areas.append({
                    'type': i.get('type'),
                    'name': i.get('name', 'Unknown'),
                    'growth_potential': 'high'
                })
        
        return growth_areas[:3]
    
    def _calculate_spatial_score(self, poi: Dict, connectivity: Dict, walkability: Dict) -> int:
        """Calculate overall spatial score"""
        score = 0
        
        # POI contribution
        if poi.get('density') == 'high':
            score += 30
        elif poi.get('density') == 'moderate':
            score += 20
        else:
            score += 10
        
        # Connectivity contribution
        score += connectivity.get('score', 50) // 3
        
        # Walkability contribution
        score += walkability.get('score', 70) // 3
        
        return min(100, score)


# ============================================
# RISK SPECIALIST
# ============================================

class RiskSpecialist(BaseSpecialist):
    """
    Risk analysis specialist
    - Risk scoring
    - Hazard assessment
    - Mitigation recommendations
    """
    
    def __init__(self):
        super().__init__(SpecialistType.RISK)
        self.capabilities = [
            'risk_scoring',
            'hazard_assessment',
            'mitigation_planning',
            'compliance_check'
        ]
    
    async def analyze(
        self,
        context: Dict[str, Any],
        lat: float,
        lng: float
    ) -> SpecialistResult:
        start_time = datetime.now()
        
        try:
            risk_data = context.get('risk_data', {})
            terrain_data = context.get('terrain_data', {})
            
            # Assess environmental risks
            environmental = self._assess_environmental_risks(terrain_data)
            
            # Assess market risks
            market = self._assess_market_risks(context.get('market_data', {}))
            
            # Assess legal risks
            legal = self._assess_legal_risks(context)
            
            # Generate mitigation strategies
            mitigation = self._generate_mitigation(environmental, market, legal)
            
            data = {
                'environmental': environmental,
                'market': market,
                'legal': legal,
                'mitigation': mitigation,
                'overall_risk_score': self._calculate_overall_risk(environmental, market, legal)
            }
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return SpecialistResult(
                specialist_type=self.specialist_type,
                success=True,
                data=data,
                confidence=0.80,
                reasoning="Risk assessment based on environmental, market, and legal factors",
                execution_time_ms=int(execution_time)
            )
            
        except Exception as e:
            logger.error(f"Risk specialist error: {e}")
            return SpecialistResult(
                specialist_type=self.specialist_type,
                success=False,
                data={},
                confidence=0.0,
                reasoning=f"Risk analysis failed: {str(e)}"
            )
    
    def _assess_environmental_risks(self, terrain_data: Dict) -> Dict:
        """Assess environmental risks"""
        flood_zone = terrain_data.get('flood_zone', 'low')
        
        return {
            'flood_risk': 'HIGH' if flood_zone == 'high' else 'MODERATE' if flood_zone == 'moderate' else 'LOW',
            'flood_score': 75 if flood_zone == 'high' else 40 if flood_zone == 'moderate' else 15,
            'landslide_risk': 'LOW',
            'pollution_level': 'MODERATE'
        }
    
    def _assess_market_risks(self, market_data: Dict) -> Dict:
        """Assess market risks"""
        volatility = market_data.get('volatility', 10)
        
        return {
            'price_volatility': 'HIGH' if volatility > 15 else 'MODERATE' if volatility > 8 else 'LOW',
            'liquidity_risk': 'LOW',
            'demand_risk': 'LOW'
        }
    
    def _assess_legal_risks(self, context: Dict) -> Dict:
        """Assess legal risks"""
        return {
            'title_risk': 'MODERATE',
            'zoning_risk': 'LOW',
            'rera_compliance': 'VERIFIED'
        }
    
    def _generate_mitigation(self, environmental: Dict, market: Dict, legal: Dict) -> List[str]:
        """Generate mitigation strategies"""
        strategies = []
        
        if environmental.get('flood_risk') in ['HIGH', 'MODERATE']:
            strategies.append('Review flood zone mapping and drainage plans')
        
        if market.get('price_volatility') == 'HIGH':
            strategies.append('Consider longer holding period to ride out volatility')
        
        if legal.get('title_risk') == 'MODERATE':
            strategies.append('Conduct thorough title search and verification')
        
        strategies.extend([
            'Verify RERA registration',
            'Check for pending litigation',
            'Review all encumbrances'
        ])
        
        return strategies
    
    def _calculate_overall_risk(self, environmental: Dict, market: Dict, legal: Dict) -> int:
        """Calculate overall risk score"""
        score = 0
        
        # Environmental contribution
        score += environmental.get('flood_score', 15)
        
        # Market contribution
        if market.get('price_volatility') == 'HIGH':
            score += 25
        elif market.get('price_volatility') == 'MODERATE':
            score += 15
        else:
            score += 10
        
        # Legal contribution
        if legal.get('title_risk') == 'HIGH':
            score += 25
        elif legal.get('title_risk') == 'MODERATE':
            score += 15
        else:
            score += 10
        
        return min(100, score)


# ============================================
# MARKET SPECIALIST
# ============================================

class MarketSpecialist(BaseSpecialist):
    """
    Market analysis specialist
    - Price trends
    - Demand analysis
    - Market indicators
    """
    
    def __init__(self):
        super().__init__(SpecialistType.MARKET)
        self.capabilities = [
            'price_analysis',
            'demand_forecasting',
            'market_timing',
            'comparable_analysis'
        ]
    
    async def analyze(
        self,
        context: Dict[str, Any],
        lat: float,
        lng: float
    ) -> SpecialistResult:
        start_time = datetime.now()
        
        try:
            market_data = context.get('market_data', {})
            
            # Analyze price trends
            price_trends = self._analyze_price_trends(market_data)
            
            # Analyze demand
            demand = self._analyze_demand(market_data)
            
            # Analyze market timing
            timing = self._analyze_market_timing(market_data)
            
            data = {
                'price_trends': price_trends,
                'demand': demand,
                'timing': timing,
                'market_score': self._calculate_market_score(price_trends, demand)
            }
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return SpecialistResult(
                specialist_type=self.specialist_type,
                success=True,
                data=data,
                confidence=0.88,
                reasoning="Market analysis based on price trends and demand indicators",
                execution_time_ms=int(execution_time)
            )
            
        except Exception as e:
            logger.error(f"Market specialist error: {e}")
            return SpecialistResult(
                specialist_type=self.specialist_type,
                success=False,
                data={},
                confidence=0.0,
                reasoning=f"Market analysis failed: {str(e)}"
            )
    
    def _analyze_price_trends(self, market_data: Dict) -> Dict:
        """Analyze price trends"""
        return {
            'current_price': market_data.get('avg_price_per_sqft', 8500),
            '1y_change': f"+{market_data.get('price_trend_1y', 10)}%",
            '3y_change': f"+{market_data.get('price_trend_3y', 30)}%",
            'trend': 'appreciating' if market_data.get('price_trend_1y', 0) > 5 else 'stable'
        }
    
    def _analyze_demand(self, market_data: Dict) -> Dict:
        """Analyze demand"""
        demand_index = market_data.get('demand_index', 60)
        
        return {
            'index': demand_index,
            'level': 'HIGH' if demand_index > 70 else 'MODERATE' if demand_index > 50 else 'LOW',
            'trend': 'increasing'
        }
    
    def _analyze_market_timing(self, market_data: Dict) -> Dict:
        """Analyze market timing"""
        trend = market_data.get('price_trend_1y', 0)
        
        return {
            'phase': 'growth' if trend > 8 else 'stable' if trend > 3 else 'correction',
            'recommendation': 'Good time to buy' if trend < 15 else 'Market heating up'
        }
    
    def _calculate_market_score(self, trends: Dict, demand: Dict) -> int:
        """Calculate market score"""
        score = 50
        
        if trends.get('trend') == 'appreciating':
            score += 20
        
        if demand.get('level') == 'HIGH':
            score += 20
        elif demand.get('level') == 'MODERATE':
            score += 10
        
        return min(100, score)


# ============================================
# SPECIALIST ROUTER
# ============================================

class SpecialistRouter:
    """
    Routes queries to appropriate specialists
    """
    
    def __init__(self):
        self.specialists = {
            SpecialistType.PLANNER: PlannerSpecialist(),
            SpecialistType.INVESTOR: InvestorSpecialist(),
            SpecialistType.GIS_ANALYST: GISAnalystSpecialist(),
            SpecialistType.RISK: RiskSpecialist(),
            SpecialistType.MARKET: MarketSpecialist()
        }
        
        self.query_mapping = {
            'invest': [SpecialistType.INVESTOR, SpecialistType.MARKET, SpecialistType.RISK],
            'buy': [SpecialistType.INVESTOR, SpecialistType.MARKET],
            'location': [SpecialistType.GIS_ANALYST, SpecialistType.MARKET],
            'area': [SpecialistType.GIS_ANALYST, SpecialistType.MARKET],
            'risk': [SpecialistType.RISK, SpecialistType.MARKET],
            'price': [SpecialistType.MARKET, SpecialistType.INVESTOR],
            'roi': [SpecialistType.INVESTOR, SpecialistType.MARKET],
            'compare': [SpecialistType.MARKET, SpecialistType.GIS_ANALYST],
            'recommend': [SpecialistType.PLANNER, SpecialistType.INVESTOR]
        }
    
    def route(self, query: str) -> List[SpecialistType]:
        """Route query to appropriate specialists"""
        query_lower = query.lower()
        
        for keyword, specialists in self.query_mapping.items():
            if keyword in query_lower:
                return specialists
        
        # Default routing
        return [SpecialistType.MARKET, SpecialistType.GIS_ANALYST]
    
    def get_specialist(self, specialist_type: SpecialistType) -> Optional[BaseSpecialist]:
        """Get specialist by type"""
        return self.specialists.get(specialist_type)


# ============================================
# SPECIALIST ORCHESTRATOR
# ============================================

class SpecialistOrchestrator:
    """
    Orchestrates multiple specialists for comprehensive analysis
    """
    
    def __init__(self):
        self.router = SpecialistRouter()
    
    async def analyze(
        self,
        query: str,
        lat: float,
        lng: float,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run multi-specialist analysis"""
        
        # Route to appropriate specialists
        specialist_types = self.router.route(query)
        
        # Run specialists in parallel
        tasks = []
        for stype in specialist_types:
            specialist = self.router.get_specialist(stype)
            if specialist:
                tasks.append(specialist.analyze(context, lat, lng))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        specialist_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Specialist {specialist_types[i]} failed: {result}")
            elif isinstance(result, SpecialistResult):
                specialist_results.append(result)
        
        # Synthesize results
        synthesis = self._synthesize_results(specialist_results)
        
        return {
            'query': query,
            'specialists_used': [s.specialist_type.value for s in specialist_results],
            'specialist_results': [s.to_dict() for s in specialist_results],
            'synthesis': synthesis,
            'timestamp': datetime.now().isoformat()
        }
    
    def _synthesize_results(self, results: List[SpecialistResult]) -> Dict[str, Any]:
        """Synthesize results from multiple specialists"""
        
        if not results:
            return {'summary': 'No analysis results available'}
        
        # Calculate weighted confidence
        total_confidence = sum(r.confidence for r in results)
        avg_confidence = total_confidence / len(results) if results else 0
        
        # Extract key insights
        insights = []
        for result in results:
            if result.success:
                insights.append({
                    'specialist': result.specialist_type.value,
                    'key_finding': result.reasoning,
                    'confidence': result.confidence
                })
        
        return {
            'overall_confidence': avg_confidence,
            'insights': insights,
            'summary': self._generate_summary(results)
        }
    
    def _generate_summary(self, results: List[SpecialistResult]) -> str:
        """Generate summary from results"""
        summaries = []
        
        for result in results:
            if result.success:
                specialist_name = result.specialist_type.value.replace('_', ' ').title()
                summaries.append(f"{specialist_name}: {result.reasoning}")
        
        return " | ".join(summaries) if summaries else "Analysis completed"


# Singleton instance
_orchestrator = None

def get_specialist_orchestrator() -> SpecialistOrchestrator:
    """Get or create specialist orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SpecialistOrchestrator()
    return _orchestrator
