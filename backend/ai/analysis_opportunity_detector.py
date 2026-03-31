"""
Valora AI - Analysis Opportunity Detector

Detects opportunities to offer analysis services based on user queries.
Provides tiered analysis options with different credit costs.
"""

import re
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger("valora.analysis_opportunity")


class AnalysisSubIntent(Enum):
    """Sub-intents for analysis-related queries."""
    
    # Investment-related
    INVESTMENT_EVALUATION = "investment_evaluation"    # "Is X good for investment?"
    INVESTMENT_COMPARISON = "investment_comparison"    # "Which is better for investment?"
    ROI_INQUIRY = "roi_inquiry"                        # "What's the ROI potential?"
    
    # Market analysis
    PRICE_TREND_INQUIRY = "price_trend_inquiry"        # "Price trends in X"
    MARKET_OUTLOOK = "market_outlook"                  # "How's the market in X?"
    
    # Area evaluation
    AREA_LIVABILITY = "area_livability"                # "Is X good for families?"
    AREA_DEVELOPMENT = "area_development"              # "Future of X area"
    AREA_COMPARISON = "area_comparison"                # "Compare X and Y"
    
    # Explicit requests
    EXPLICIT_REPORT = "explicit_report"                # "Generate report"
    EXPLICIT_ANALYSIS = "explicit_analysis"            # "Analyze this area"


@dataclass
class AnalysisTier:
    """Represents a tier of analysis with associated cost and features."""
    tier_id: str
    name: str
    credits: int
    description: str
    includes: List[str] = field(default_factory=list)
    estimated_time: str = "Instant"
    action: str = ""


@dataclass
class OpportunityResult:
    """Result of analysis opportunity detection."""
    opportunity_type: str  # 'report', 'area_analysis', 'comparison_report'
    confidence: float
    sub_intent: AnalysisSubIntent
    location: Optional[str] = None
    location2: Optional[str] = None  # For comparison queries
    lat: Optional[float] = None
    lng: Optional[float] = None
    suggested_tiers: List[str] = field(default_factory=list)
    contextual_hooks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# Define analysis tiers
ANALYSIS_TIERS = {
    'quick_overview': AnalysisTier(
        tier_id='quick_overview',
        name='Quick Overview',
        credits=0,
        description='Basic area summary with key highlights',
        includes=['Location highlights', 'Key amenities', 'Price range'],
        estimated_time='Instant',
        action='area_overview'
    ),
    'area_analysis': AnalysisTier(
        tier_id='area_analysis',
        name='Area Analysis',
        credits=3,
        description='Detailed neighborhood insights with POIs and connectivity',
        includes=['Full amenity analysis', 'Connectivity score', 'Price trends', 'Investment potential'],
        estimated_time='~30 seconds',
        action='area_analysis'
    ),
    'investment_report': AnalysisTier(
        tier_id='investment_report',
        name='Investment Report',
        credits=200,
        description='Comprehensive 9-section analysis with ROI projections',
        includes=['Executive summary', 'Market analysis', 'Risk assessment', 'ROI projections', 'Recommendations'],
        estimated_time='~2 minutes',
        action='generate_report'
    )
}

# Comparison-specific tiers
COMPARISON_TIERS = {
    'quick_comparison': AnalysisTier(
        tier_id='quick_comparison',
        name='Quick Comparison',
        credits=0,
        description='Side-by-side key metrics',
        includes=['Price comparison', 'Basic amenities', 'Connectivity'],
        estimated_time='Instant',
        action='quick_comparison'
    ),
    'detailed_comparison': AnalysisTier(
        tier_id='detailed_comparison',
        name='Detailed Comparison',
        credits=6,  # 3 credits per area
        description='In-depth analysis of both areas',
        includes=['Full area analysis for both', 'Investment scoring', 'Detailed comparison'],
        estimated_time='~1 minute',
        action='detailed_comparison'
    ),
    'comparison_reports': AnalysisTier(
        tier_id='comparison_reports',
        name='Investment Reports (Both)',
        credits=400,  # 200 credits per report
        description='Full investment reports for both locations',
        includes=['Complete 9-section reports', 'ROI comparison', 'Risk analysis'],
        estimated_time='~4 minutes',
        action='comparison_reports'
    )
}


class AnalysisOpportunityDetector:
    """
    Detects opportunities to offer analysis services based on user queries.
    
    Evaluates queries for investment intent, price trends, area comparison, etc.
    and returns appropriate analysis options.
    """
    
    # Patterns indicating potential report/analysis opportunity
    INVESTMENT_PATTERNS = [
        r'\b(is|are)\s+\w+\s+(good|better|best)\s+for\s+investment\b',
        r'\b(should|i)\s+(buy|invest)\s+(in|at)\b',
        r'\b(worth|worthwhile)\s+(buying|investing)\b',
        r'\b(roi|return on investment)\s+(potential|in|for)\b',
        r'\b(investment|investing)\s+(potential|opportunity|prospects)\b',
        r'\b(good|bad|smart|safe)\s+(investment|buy)\b',
        r'\b(appreciation|growth)\s+(potential|prospects)\b',
    ]
    
    MARKET_TREND_PATTERNS = [
        r'\b(price|market)\s+(trend|trends|outlook|forecast)\s+(in|for|of)\b',
        r'\b(how\s+is\s+the\s+market|what\s+about\s+prices)\b',
        r'\b(market\s+(going|heading|moving)|price\s+movement)\b',
        r'\b(future\s+(price|value|growth)|projection)\b',
        r'\b(appreciation|depreciation)\s+(rate|history)\b',
    ]
    
    AREA_EVALUATION_PATTERNS = [
        r'\b(how\s+is|what\s+about|tell\s+me\s+about)\s+\w+\s+(area|locality|neighborhood)\b',
        r'\b(pros\s+and\s+cons|advantages|disadvantages)\s+(of|in|for)\b',
        r'\b(is|are)\s+\w+\s+(good|safe|nice|decent)\s+(area|locality|place)\b',
        r'\b(livability|liveable|family.?friendly)\b',
        r'\b(safe|safety|crime)\s+(area|neighborhood|locality)\b',
        r'\b(for\s+(families|singles|retirees|students|kids|professionals))\b',
    ]
    
    COMPARISON_PATTERNS = [
        r'\b(compare|versus|vs)\s+.+?\s+(and|vs|versus|with)\b',
        r'\b(which\s+(area|location|place|locality)\s+is\s+better)\b',
        r'\b(difference\s+between|pros and cons of)\s+.+?\s+and\b',
        r'\b(better\s+(investment|area|choice|option))\s*(\?)?$',
    ]
    
    ROI_PATTERNS = [
        r'\b(roi|return on investment|return)\s+(potential|rate|expected)\b',
        r'\b(how\s+much\s+(return|profit|gain))\b',
        r'\b(expected|projected)\s+(returns?|appreciation)\b',
        r'\b(investment\s+(horizon|period|timeline))\b',
    ]
    
    EXPLICIT_REPORT_PATTERNS = [
        r'\b(generate|create|make|get)\s+(a\s+)?(detailed\s+)?reports?\b',
        r'\b(reports?\s+(for|about|on|generation))\b',
        r'\b(investment|property|area)\s+reports?\b',
        r'\b(full|comprehensive|detailed)\s+(analysis|reports?)\b',
    ]
    
    # Known Bangalore localities for extraction
    KNOWN_LOCALITIES = [
        'Koramangala', 'Indiranagar', 'Whitefield', 'HSR Layout', 'Jayanagar', 'JP Nagar',
        'Marathahalli', 'Sarjapur', 'Electronic City', 'Hebbal', 'Yelahanka', 'Banashankari',
        'Rajajinagar', 'Malleshwaram', 'Basavanagudi', 'BTM Layout', 'Bellandur', 'Brookefield',
        'KR Puram', 'Mahadevpura', 'Hennur', 'Thanisandra', 'Nagarbhavi', 'Vijayanagar',
        'Bannerghatta', 'Kanakapura', 'Mysore Road', 'Tumkur Road', 'Old Airport Road',
        'MG Road', 'Brigade Road', 'Commercial Street', 'Cunningham Road', 'Residency Road',
        'Domlur', 'HAL', 'CV Raman Nagar', 'Banaswadi', 'Kalyan Nagar', 'HRBR Layout',
        'Sadashivanagar', 'Sanjaynagar', 'RT Nagar', 'HBR Layout', 'Kasturi Nagar',
        'Ramamurthy Nagar', 'Horamavu', 'Bagalur', 'Anekal', 'Chandapura', 'Attibele',
        'Silk Board', 'Tin Factory', 'Majestic', 'Kempegowda', 'Yeshwanthpur'
    ]
    
    def __init__(self):
        """Initialize the detector with compiled patterns."""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency."""
        self._compiled_investment = [re.compile(p, re.IGNORECASE) for p in self.INVESTMENT_PATTERNS]
        self._compiled_market = [re.compile(p, re.IGNORECASE) for p in self.MARKET_TREND_PATTERNS]
        self._compiled_area = [re.compile(p, re.IGNORECASE) for p in self.AREA_EVALUATION_PATTERNS]
        self._compiled_comparison = [re.compile(p, re.IGNORECASE) for p in self.COMPARISON_PATTERNS]
        self._compiled_roi = [re.compile(p, re.IGNORECASE) for p in self.ROI_PATTERNS]
        self._compiled_report = [re.compile(p, re.IGNORECASE) for p in self.EXPLICIT_REPORT_PATTERNS]
    
    def detect_opportunity(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[OpportunityResult]:
        """
        Detect if query presents an analysis opportunity.
        
        Args:
            query: User's query text
            context: Optional context including location, conversation history, etc.
            
        Returns:
            OpportunityResult if opportunity detected, None otherwise
        """
        context = context or {}
        q_lower = query.lower()
        
        # Extract location information
        location, location2, lat, lng = self._extract_locations(query, context)
        
        # Check for explicit report request first (highest priority)
        for pattern in self._compiled_report:
            if pattern.search(query):
                return self._create_opportunity(
                    opportunity_type='report',
                    sub_intent=AnalysisSubIntent.EXPLICIT_REPORT,
                    location=location,
                    lat=lat,
                    lng=lng,
                    confidence=0.95,
                    suggested_tiers=['quick_overview', 'area_analysis', 'investment_report']
                )
        
        # Check for comparison queries
        for pattern in self._compiled_comparison:
            if pattern.search(query):
                return self._create_opportunity(
                    opportunity_type='comparison_report',
                    sub_intent=AnalysisSubIntent.AREA_COMPARISON,
                    location=location,
                    location2=location2,
                    lat=lat,
                    lng=lng,
                    confidence=0.85,
                    suggested_tiers=['quick_comparison', 'detailed_comparison', 'comparison_reports'],
                    is_comparison=True
                )
        
        # Check for ROI-specific queries
        for pattern in self._compiled_roi:
            if pattern.search(query):
                return self._create_opportunity(
                    opportunity_type='report',
                    sub_intent=AnalysisSubIntent.ROI_INQUIRY,
                    location=location,
                    lat=lat,
                    lng=lng,
                    confidence=0.85,
                    suggested_tiers=['area_analysis', 'investment_report'],
                    contextual_hooks=['roi_analysis']
                )
        
        # Check for investment evaluation queries
        for pattern in self._compiled_investment:
            if pattern.search(query):
                return self._create_opportunity(
                    opportunity_type='report',
                    sub_intent=AnalysisSubIntent.INVESTMENT_EVALUATION,
                    location=location,
                    lat=lat,
                    lng=lng,
                    confidence=0.80,
                    suggested_tiers=['quick_overview', 'area_analysis', 'investment_report'],
                    contextual_hooks=['investment_scoring']
                )
        
        # Check for market trend queries
        for pattern in self._compiled_market:
            if pattern.search(query):
                return self._create_opportunity(
                    opportunity_type='area_analysis',
                    sub_intent=AnalysisSubIntent.PRICE_TREND_INQUIRY,
                    location=location,
                    lat=lat,
                    lng=lng,
                    confidence=0.75,
                    suggested_tiers=['quick_overview', 'area_analysis', 'investment_report'],
                    contextual_hooks=['market_trends']
                )
        
        # Check for area evaluation queries
        for pattern in self._compiled_area:
            if pattern.search(query):
                # Determine if livability-focused
                livability_keywords = ['family', 'families', 'safe', 'safety', 'livability', 'liveable']
                is_livability = any(kw in q_lower for kw in livability_keywords)
                
                return self._create_opportunity(
                    opportunity_type='area_analysis',
                    sub_intent=AnalysisSubIntent.AREA_LIVABILITY if is_livability else AnalysisSubIntent.AREA_DEVELOPMENT,
                    location=location,
                    lat=lat,
                    lng=lng,
                    confidence=0.70,
                    suggested_tiers=['quick_overview', 'area_analysis'],
                    contextual_hooks=['livability_analysis'] if is_livability else ['area_development']
                )
        
        return None
    
    def _extract_locations(
        self, 
        query: str, 
        context: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[float]]:
        """
        Extract location names and coordinates from query and context.
        
        Returns:
            Tuple of (location, location2, lat, lng)
        """
        location = None
        location2 = None
        lat = None
        lng = None
        
        # First check context for location
        if context:
            location = context.get('location_name')
            lat = context.get('lat')
            lng = context.get('lng')

        coords = self._extract_coordinates(query)
        if coords:
            lat, lng = coords
            if not location:
                location = f"Area at {lat:.5f}, {lng:.5f}"
        
        # Extract from query using known localities
        q_lower = query.lower()
        found_localities = []
        
        for locality in self.KNOWN_LOCALITIES:
            if locality.lower() in q_lower:
                found_localities.append(locality)
        
        if found_localities:
            if not location:
                location = found_localities[0]
            if len(found_localities) > 1:
                location2 = found_localities[1]
        
        # Try pattern-based extraction if no locality found
        if not location:
            location = self._extract_place_from_patterns(query)
        
        return location, location2, lat, lng

    def _extract_coordinates(self, query: str) -> Optional[Tuple[float, float]]:
        """Extract explicit lat/lng pairs from a free-form query."""
        patterns = [
            r"\b(?:coordinates?|coords?)\s*(?:at|of|for)?\s*(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\b",
            r"\b(?:lat|latitude)\s*[:=]?\s*(-?\d{1,2}\.\d+)\s*[, ]+\s*(?:lng|lon|long|longitude)\s*[:=]?\s*(-?\d{1,3}\.\d+)\b",
            r"(?<!\d)(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)(?!\d)",
        ]
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if not match:
                continue
            try:
                lat = float(match.group(1))
                lng = float(match.group(2))
            except (TypeError, ValueError):
                continue
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return lat, lng
        return None
    
    def _extract_place_from_patterns(self, query: str) -> Optional[str]:
        """Extract place name using pattern matching."""
        patterns = [
            r'(?:in|at|near|around|for)\s+([A-Z][a-zA-Z\s]+?)(?:\s*$|\s*\?|\s+area|\s+locality)',
            r'(?:is|are)\s+([A-Z][a-zA-Z\s]+?)\s+(?:a\s+)?(?:good|bad|safe|nice)',
            r'(?:invest|buy)\s+(?:in|at)\s+([A-Z][a-zA-Z\s]+?)(?:\s*$|\s*\?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                place = match.group(1).strip()
                # Clean up common suffixes
                place = re.sub(r'\s*(area|location|place|neighborhood|locality)$', '', place, flags=re.IGNORECASE)
                if place and len(place) > 2:
                    return place
        
        return None
    
    def _create_opportunity(
        self,
        opportunity_type: str,
        sub_intent: AnalysisSubIntent,
        location: Optional[str],
        confidence: float,
        suggested_tiers: List[str],
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        location2: Optional[str] = None,
        is_comparison: bool = False,
        contextual_hooks: Optional[List[str]] = None
    ) -> OpportunityResult:
        """Create an OpportunityResult with the given parameters."""
        return OpportunityResult(
            opportunity_type=opportunity_type,
            confidence=confidence,
            sub_intent=sub_intent,
            location=location,
            location2=location2,
            lat=lat,
            lng=lng,
            suggested_tiers=suggested_tiers,
            contextual_hooks=contextual_hooks or [],
            metadata={'is_comparison': is_comparison}
        )
    
    def get_tier_details(self, tier_id: str, is_comparison: bool = False) -> Optional[AnalysisTier]:
        """
        Get details for a specific tier.
        
        Args:
            tier_id: The tier identifier
            is_comparison: Whether to use comparison tiers
            
        Returns:
            AnalysisTier if found, None otherwise
        """
        tiers = COMPARISON_TIERS if is_comparison else ANALYSIS_TIERS
        return tiers.get(tier_id)
    
    def get_available_tiers(
        self, 
        tier_ids: List[str], 
        is_comparison: bool = False
    ) -> List[AnalysisTier]:
        """
        Get list of available tiers for the given tier IDs.
        
        Args:
            tier_ids: List of tier identifiers
            is_comparison: Whether to use comparison tiers
            
        Returns:
            List of AnalysisTier objects
        """
        tiers = COMPARISON_TIERS if is_comparison else ANALYSIS_TIERS
        return [tiers[tid] for tid in tier_ids if tid in tiers]
    
    def build_tiered_options(
        self,
        opportunity: OpportunityResult,
        user_credits: int
    ) -> List[Dict[str, Any]]:
        """
        Build tiered options for UI display based on opportunity and user credits.
        
        Args:
            opportunity: The detected opportunity
            user_credits: User's current credit balance
            
        Returns:
            List of option dictionaries for UI display
        """
        is_comparison = opportunity.metadata.get('is_comparison', False)
        tiers = self.get_available_tiers(opportunity.suggested_tiers, is_comparison)
        
        options = []
        for tier in tiers:
            option = {
                'id': tier.tier_id,
                'label': tier.name,
                'description': tier.description,
                'credits': tier.credits,
                'action': tier.action,
                'available': user_credits >= tier.credits,
                'includes': tier.includes,
                'estimated_time': tier.estimated_time
            }
            options.append(option)
        
        return options


@dataclass
class UserBehaviorProfile:
    """User behavior profile for smart recommendations."""
    user_id: str
    investment_focus: float = 0.0  # 0-1 score
    price_range_min: Optional[float] = None
    price_range_max: Optional[float] = None
    preferred_localities: List[str] = field(default_factory=list)
    analysis_types_used: Dict[str, int] = field(default_factory=dict)
    engagement_score: float = 0.0
    total_sessions: int = 0
    total_queries: int = 0
    last_active: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SmartRecommendation:
    """A smart recommendation based on user behavior."""
    recommendation_id: str
    title: str
    description: str
    action_type: str  # 'analysis', 'comparison', 'report', 'exploration'
    target_location: Optional[str] = None
    target_location2: Optional[str] = None
    tier_suggestion: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class UserBehaviorTracker:
    """
    Tracks user behavior patterns for smart recommendations.
    
    Features:
    - Track investment focus, price range preferences
    - Generate proactive recommendations based on patterns
    - Suggest relevant analyses user hasn't tried yet
    """
    
    def __init__(self):
        self._profiles: Dict[str, UserBehaviorProfile] = {}
    
    def get_or_create_profile(self, user_id: str) -> UserBehaviorProfile:
        """Get or create a user behavior profile."""
        if user_id not in self._profiles:
            self._profiles[user_id] = UserBehaviorProfile(user_id=user_id)
        return self._profiles[user_id]
    
    def update_profile(
        self,
        user_id: str,
        intent: str,
        location: Optional[str] = None,
        price_range: Optional[Dict[str, float]] = None,
        analysis_type: Optional[str] = None
    ):
        """
        Update user behavior profile based on interaction.
        
        Args:
            user_id: User identifier
            intent: Classified intent
            location: Location mentioned
            price_range: Price range if mentioned
            analysis_type: Type of analysis performed
        """
        profile = self.get_or_create_profile(user_id)
        
        # Update investment focus
        investment_intents = {
            'investment', 'roi_inquiry', 'investment_evaluation',
            'investment_comparison', 'market_trend'
        }
        if intent in investment_intents:
            profile.investment_focus = min(1.0, profile.investment_focus + 0.1)
        else:
            profile.investment_focus = max(0.0, profile.investment_focus - 0.02)
        
        # Update price range
        if price_range:
            if price_range.get('min'):
                if profile.price_range_min is None:
                    profile.price_range_min = price_range['min']
                else:
                    profile.price_range_min = min(profile.price_range_min, price_range['min'])
            if price_range.get('max'):
                if profile.price_range_max is None:
                    profile.price_range_max = price_range['max']
                else:
                    profile.price_range_max = max(profile.price_range_max, price_range['max'])
        
        # Update preferred localities
        if location and location not in profile.preferred_localities:
            profile.preferred_localities.insert(0, location)
            profile.preferred_localities = profile.preferred_localities[:10]
        
        # Update analysis types used
        if analysis_type:
            profile.analysis_types_used[analysis_type] = \
                profile.analysis_types_used.get(analysis_type, 0) + 1
        
        # Update engagement metrics
        profile.total_queries += 1
        profile.engagement_score = min(1.0, profile.engagement_score + 0.05)
        profile.last_active = datetime.utcnow().isoformat()
    
    def generate_recommendations(
        self,
        user_id: str,
        current_context: Optional[Dict[str, Any]] = None
    ) -> List[SmartRecommendation]:
        """
        Generate proactive recommendations based on user behavior patterns.
        
        Args:
            user_id: User identifier
            current_context: Current conversation context
            
        Returns:
            List of SmartRecommendation objects
        """
        profile = self.get_or_create_profile(user_id)
        recommendations = []
        context = current_context or {}
        
        # Recommendation 1: Suggest investment analysis for investment-focused users
        if profile.investment_focus > 0.5 and 'investment_report' not in profile.analysis_types_used:
            loc = context.get('last_location') or (profile.preferred_localities[0] if profile.preferred_localities else None)
            if loc:
                recommendations.append(SmartRecommendation(
                    recommendation_id=f"inv_{loc}_{user_id}",
                    title=f"Investment Analysis for {loc}",
                    description=f"Based on your interest in investments, I can provide a detailed ROI analysis for {loc}.",
                    action_type='report',
                    target_location=loc,
                    tier_suggestion='investment_report',
                    confidence=0.85,
                    reason="User shows strong investment focus but hasn't used investment report feature"
                ))
        
        # Recommendation 2: Suggest comparison for users exploring multiple areas
        if len(profile.preferred_localities) >= 2:
            loc1, loc2 = profile.preferred_localities[:2]
            if f"compare_{loc1}_{loc2}" not in profile.analysis_types_used:
                recommendations.append(SmartRecommendation(
                    recommendation_id=f"compare_{loc1}_{loc2}_{user_id}",
                    title=f"Compare {loc1} vs {loc2}",
                    description=f"You've been exploring both {loc1} and {loc2}. Would you like a detailed comparison?",
                    action_type='comparison',
                    target_location=loc1,
                    target_location2=loc2,
                    tier_suggestion='detailed_comparison',
                    confidence=0.75,
                    reason="User has shown interest in multiple localities"
                ))
        
        # Recommendation 3: Suggest area analysis for new locations
        if context.get('last_location') and context.get('last_location') not in profile.preferred_localities[:3]:
            loc = context['last_location']
            recommendations.append(SmartRecommendation(
                recommendation_id=f"area_{loc}_{user_id}",
                title=f"Explore {loc}",
                description=f"Would you like me to analyze {loc} for amenities, connectivity, and investment potential?",
                action_type='analysis',
                target_location=loc,
                tier_suggestion='area_analysis',
                confidence=0.70,
                reason="User is exploring a new location"
            ))
        
        # Recommendation 4: Suggest market trends for price-conscious users
        if profile.price_range_max and profile.price_range_min:
            price_spread = profile.price_range_max - profile.price_range_min
            if price_spread > 5000000:  # 50 lakh spread
                loc = profile.preferred_localities[0] if profile.preferred_localities else None
                if loc:
                    recommendations.append(SmartRecommendation(
                        recommendation_id=f"trend_{loc}_{user_id}",
                        title=f"Market Trends in {loc}",
                        description=f"Given your price range interest, would you like to see market trends and price forecasts for {loc}?",
                        action_type='analysis',
                        target_location=loc,
                        tier_suggestion='area_analysis',
                        confidence=0.65,
                        reason="User has shown interest in varied price ranges"
                    ))
        
        # Recommendation 5: Suggest unused analysis types
        available_analyses = {'area_analysis', 'investment_report', 'terrain_analysis', 'market_trend'}
        unused = available_analyses - set(profile.analysis_types_used.keys())
        
        if unused and profile.preferred_localities:
            loc = profile.preferred_localities[0]
            if 'terrain_analysis' in unused and profile.engagement_score > 0.3:
                recommendations.append(SmartRecommendation(
                    recommendation_id=f"terrain_{loc}_{user_id}",
                    title=f"Terrain Analysis for {loc}",
                    description=f"Discover elevation, flood risk, and construction suitability for {loc}.",
                    action_type='analysis',
                    target_location=loc,
                    tier_suggestion='area_analysis',
                    confidence=0.60,
                    reason="User hasn't explored terrain analysis yet"
                ))
        
        # Sort by confidence
        recommendations.sort(key=lambda r: r.confidence, reverse=True)
        
        return recommendations[:3]  # Return top 3 recommendations
    
    def get_profile_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of the user's behavior profile."""
        profile = self.get_or_create_profile(user_id)
        return {
            'investment_focus': profile.investment_focus,
            'price_range': {
                'min': profile.price_range_min,
                'max': profile.price_range_max
            },
            'preferred_localities': profile.preferred_localities[:5],
            'analysis_types_used': list(profile.analysis_types_used.keys()),
            'engagement_score': profile.engagement_score,
            'total_queries': profile.total_queries
        }


# Singleton instance
_detector_instance: Optional[AnalysisOpportunityDetector] = None
_behavior_tracker_instance: Optional[UserBehaviorTracker] = None


def get_analysis_opportunity_detector() -> AnalysisOpportunityDetector:
    """Get or create the singleton detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AnalysisOpportunityDetector()
    return _detector_instance


def get_behavior_tracker() -> UserBehaviorTracker:
    """Get or create the singleton behavior tracker instance."""
    global _behavior_tracker_instance
    if _behavior_tracker_instance is None:
        _behavior_tracker_instance = UserBehaviorTracker()
    return _behavior_tracker_instance
