"""
Valora AI - Market Sentiment API Routes (SUPPORTING INTELLIGENCE)

IMPORTANT: This is SECONDARY to broker workflow features.
Market sentiment should support shortlisted decisions, NOT dominate the tab.

Valora wins on broker workflow + explainable reasoning, not consumer-style 
sentiment dashboard.

Signal Recording (No credit required):
    POST   /api/sentiment/signal                    - Record user interaction signal

Market Sentiment (5 credits) - SUPPORTS decisions, not primary:
    GET    /api/sentiment/locality/{locality_id}    - Get sentiment for locality
    GET    /api/sentiment/city/{city}              - Get sentiment for city
    GET    /api/sentiment/investment-score/{locality_id} - Get investment score

Price Analysis - Decision Support:
    GET    /api/sentiment/price-momentum/{locality_id}   - Get price momentum
    GET    /api/sentiment/price-history/{locality_id}     - Get price history

Market Metrics - Decision Support:
    GET    /api/sentiment/rental-yield/{locality_id}     - Get rental yield
    GET    /api/sentiment/days-on-market/{locality_id}   - Get average days on market

Trends - Secondary:
    GET    /api/sentiment/trending               - Get trending localities
    GET    /api/sentiment/trends/{locality_id}   - Get historical trends (10 credits)
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Header
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime

from auth.user_auth import User
from routes.auth_routes import require_auth
from services.sentiment_engine import (
    SentimentEngine,
    get_sentiment_engine,
    CREDIT_COSTS
)
from ai.credits_rate_limiter import get_rate_limiter

logger = logging.getLogger("valora.sentiment_routes")

router = APIRouter(prefix="/api/sentiment", tags=["Market Sentiment (Supporting)"])


# ============================================================================
# REQUEST MODELS
# ============================================================================

class SignalType(str, Enum):
    """Types of user signals for sentiment tracking."""
    PROPERTY_VIEW = "property_view"
    PROPERTY_SAVE = "property_save"
    PROPERTY_SHARE = "property_share"
    ANALYSIS_REQUEST = "analysis_request"
    SEARCH = "search"


class SignalRequest(BaseModel):
    """Request to record a user interaction signal."""
    signal_type: SignalType = Field(..., description="Type of user interaction")
    locality_id: Optional[str] = Field(None, description="Locality ID (optional)")
    property_id: Optional[str] = Field(None, description="Property ID (optional)")
    signal_data: Optional[Dict[str, Any]] = Field(None, description="Additional signal data")


class SentimentRequest(BaseModel):
    """Request to calculate sentiment for a locality."""
    locality_id: str = Field(..., description="Locality ID")
    force_refresh: bool = Field(False, description="Force recalculation")


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class SignalResponse(BaseModel):
    """Response for signal recording."""
    success: bool
    signal_id: Optional[str] = None
    message: str


class SentimentScoreResponse(BaseModel):
    """Response for sentiment score."""
    locality_id: str
    overall_score: float
    components: Dict[str, Any]
    calculated_at: str


class MarketSentimentResponse(BaseModel):
    """Response for market sentiment data."""
    locality_id: str
    locality_name: Optional[str]
    city: Optional[str]
    sentiment_score: Optional[float]
    price_current: Optional[float]
    price_change_pct: Optional[float]
    price_momentum: Optional[str]
    demand_score: Optional[float]
    supply_score: Optional[float]
    investment_score: Optional[float]
    days_on_market_avg: Optional[int]
    price_per_sqft_avg: Optional[float]
    inventory_count: Optional[int]
    new_listings_30d: Optional[int]
    rental_yield_avg: Optional[float]
    updated_at: Optional[str]


class InvestmentScoreResponse(BaseModel):
    """Response for investment score."""
    locality_id: str
    investment_score: float
    sentiment_score: Optional[float]
    price_momentum: Optional[str]
    demand_score: Optional[float]
    supply_score: Optional[float]


class PriceMomentumResponse(BaseModel):
    """Response for price momentum analysis."""
    locality_id: str
    current_price: Optional[float]
    locality_name: Optional[str]
    change_30d: Optional[float]
    change_90d: Optional[float]
    change_180d: Optional[float]
    change_1yr: Optional[float]
    momentum: str
    analyzed_at: str


class PriceHistoryResponse(BaseModel):
    """Response for price history."""
    locality_id: str
    current_price: Optional[float]
    price_per_sqft: Optional[float]
    price_trends: List[Dict[str, Any]]
    analyzed_at: str


class RentalYieldResponse(BaseModel):
    """Response for rental yield."""
    locality_id: str
    rental_yield: Dict[str, Optional[float]]
    calculated_at: str


class DaysOnMarketResponse(BaseModel):
    """Response for days on market."""
    locality_id: str
    days_on_market_avg: Optional[int]
    calculated_at: str


class TrendingLocalitiesResponse(BaseModel):
    """Response for trending localities."""
    trending: List[Dict[str, Any]]
    count: int
    analyzed_at: str


class SentimentTrendsResponse(BaseModel):
    """Response for historical sentiment trends."""
    locality_id: str
    trends: List[Dict[str, Any]]
    count: int
    analyzed_at: str


class CreditCheckResponse(BaseModel):
    """Response for credit check."""
    allowed: bool
    credits_required: int
    credits_available: int
    message: str


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    credits_required: Optional[int] = None
    credits_available: Optional[int] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_sentiment_engine() -> SentimentEngine:
    """Get the SentimentEngine instance."""
    return get_sentiment_engine()


async def _check_credits(user: User, action: str) -> tuple[bool, int, int]:
    """
    Check if user has enough credits for an action.
    
    Args:
        user: Current user
        action: Action name (must match CREDIT_COSTS keys)
    
    Returns:
        Tuple of (allowed, credits_required, credits_available)
    """
    engine = _get_sentiment_engine()
    credits_required = engine.get_credit_cost(action)
    
    # Get user's current balance
    rl = get_rate_limiter()
    user_data = rl.get_or_create_user(user.id)
    credits_available = user_data.get('total_available', 0)
    
    if credits_required == 0:
        return True, credits_required, credits_available
    
    if credits_available < credits_required:
        return False, credits_required, credits_available
    
    return True, credits_required, credits_available


async def _deduct_credits(user: User, action: str) -> bool:
    """
    Deduct credits for an action.
    
    Args:
        user: Current user
        action: Action name
    
    Returns:
        True if successful
    """
    engine = _get_sentiment_engine()
    credits_required = engine.get_credit_cost(action)
    
    if credits_required == 0:
        return True
    
    try:
        rl = get_rate_limiter()
        rl.deduct_credits(user.id, credits_required, action)
        logger.info(f"[Sentiment] Deducted {credits_required} credits from {user.id} for {action}")
        return True
    except Exception as e:
        logger.error(f"[Sentiment] Failed to deduct credits: {e}")
        return False


# ============================================================================
# SIGNAL RECORDING ENDPOINTS (No credit required)
# ============================================================================

@router.post("/signal", response_model=SignalResponse)
async def record_signal(
    request: SignalRequest,
    user_hash: Optional[str] = Query(None, description="Anonymized user hash (optional for authenticated users)")
):
    """
    Record a user interaction signal for sentiment analysis.
    
    This endpoint does NOT require authentication or credits.
    It tracks user engagement signals to calculate market sentiment.
    
    Signal types:
    - property_view: User viewed a property
    - property_save: User saved/favorited a property
    - property_share: User shared a property
    - analysis_request: User requested detailed analysis
    - search: User performed a search
    """
    try:
        engine = _get_sentiment_engine()
        
        # Use user_id as user_hash if provided, otherwise use the hash
        user_identifier = user_hash or f"anon_{datetime.now().timestamp()}"
        
        signal_id = engine.process_signal(
            signal_type=request.signal_type.value,
            user_hash=user_identifier,
            locality_id=request.locality_id,
            property_id=request.property_id,
            signal_data=request.signal_data
        )
        
        if signal_id:
            return SignalResponse(
                success=True,
                signal_id=signal_id,
                message=f"Signal recorded successfully"
            )
        else:
            return SignalResponse(
                success=False,
                message="Failed to record signal"
            )
    
    except Exception as e:
        logger.error(f"[Sentiment] Error recording signal: {e}")
        return SignalResponse(
            success=False,
            message=f"Error: {str(e)}"
        )


# ============================================================================
# MARKET SENTIMENT ENDPOINTS (5 credits)
# ============================================================================

@router.get("/locality/{locality_id}", response_model=MarketSentimentResponse)
async def get_locality_sentiment(
    locality_id: str = Path(..., description="Locality ID"),
    user: User = Depends(require_auth)
):
    """
    Get detailed market sentiment for a locality.
    
    Requires 5 credits to access.
    
    Returns:
        Comprehensive sentiment data including scores, prices, metrics
    """
    # Check credits
    allowed, required, available = await _check_credits(user, 'view_detailed_sentiment')
    
    if not allowed:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Insufficient credits",
                "credits_required": required,
                "credits_available": available,
                "message": f"This endpoint requires {required} credits. You have {available} credits."
            }
        )
    
    try:
        engine = _get_sentiment_engine()
        
        # Get market sentiment data
        sentiment_data = engine.get_market_sentiment(locality_id=locality_id)
        
        if not sentiment_data:
            # Try to create new sentiment data
            conn = engine._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT locality_name, city FROM locality_state WHERE locality_id = ?",
                (locality_id,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                raise HTTPException(status_code=404, detail="Locality not found")
            
            # Create new sentiment record
            engine.create_market_sentiment(
                locality_id=locality_id,
                locality_name=row['locality_name'],
                city=row.get('city')
            )
            sentiment_data = engine.get_market_sentiment(locality_id=locality_id)
        
        latest = sentiment_data[0] if sentiment_data else {}
        
        # Deduct credits
        await _deduct_credits(user, 'view_detailed_sentiment')
        
        return MarketSentimentResponse(
            locality_id=locality_id,
            locality_name=latest.get('locality_name'),
            city=latest.get('city'),
            sentiment_score=latest.get('sentiment_score'),
            price_current=latest.get('price_current'),
            price_change_pct=latest.get('price_change_pct'),
            price_momentum=latest.get('price_momentum'),
            demand_score=latest.get('demand_score'),
            supply_score=latest.get('supply_score'),
            investment_score=latest.get('investment_score'),
            days_on_market_avg=latest.get('days_on_market_avg'),
            price_per_sqft_avg=latest.get('price_per_sqft_avg'),
            inventory_count=latest.get('inventory_count'),
            new_listings_30d=latest.get('new_listings_30d'),
            rental_yield_avg=latest.get('rental_yield_avg'),
            updated_at=latest.get('updated_at')
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Sentiment] Error getting locality sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/city/{city}", response_model=List[MarketSentimentResponse])
async def get_city_sentiment(
    city: str = Path(..., description="City name"),
    limit: int = Query(50, ge=1, le=100, description="Maximum localities to return"),
    user: User = Depends(require_auth)
):
    """
    Get market sentiment for all localities in a city.
    
    Requires 5 credits to access.
    """
    # Check credits
    allowed, required, available = await _check_credits(user, 'view_detailed_sentiment')
    
    if not allowed:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Insufficient credits",
                "credits_required": required,
                "credits_available": available,
                "message": f"This endpoint requires {required} credits. You have {available} credits."
            }
        )
    
    try:
        engine = _get_sentiment_engine()
        
        # Get sentiment data for city
        sentiment_data = engine.get_market_sentiment(city=city, limit=limit)
        
        if not sentiment_data:
            # Initialize localities for the city
            engine.initialize_localities(city=city)
            sentiment_data = engine.get_market_sentiment(city=city, limit=limit)
        
        # Deduct credits
        await _deduct_credits(user, 'view_detailed_sentiment')
        
        return [
            MarketSentimentResponse(
                locality_id=item.get('locality_id'),
                locality_name=item.get('locality_name'),
                city=item.get('city'),
                sentiment_score=item.get('sentiment_score'),
                price_current=item.get('price_current'),
                price_change_pct=item.get('price_change_pct'),
                price_momentum=item.get('price_momentum'),
                demand_score=item.get('demand_score'),
                supply_score=item.get('supply_score'),
                investment_score=item.get('investment_score'),
                days_on_market_avg=item.get('days_on_market_avg'),
                price_per_sqft_avg=item.get('price_per_sqft_avg'),
                inventory_count=item.get('inventory_count'),
                new_listings_30d=item.get('new_listings_30d'),
                rental_yield_avg=item.get('rental_yield_avg'),
                updated_at=item.get('updated_at')
            )
            for item in sentiment_data
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Sentiment] Error getting city sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/investment-score/{locality_id}", response_model=InvestmentScoreResponse)
async def get_investment_score(
    locality_id: str = Path(..., description="Locality ID"),
    user: User = Depends(require_auth)
):
    """
    Get investment score for a locality.
    
    Requires 5 credits to access.
    
    Returns:
        Investment score based on sentiment, demand, supply, and price momentum
    """
    # Check credits
    allowed, required, available = await _check_credits(user, 'view_detailed_sentiment')
    
    if not allowed:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Insufficient credits",
                "credits_required": required,
                "credits_available": available,
                "message": f"This endpoint requires {required} credits. You have {available} credits."
            }
        )
    
    try:
        engine = _get_sentiment_engine()
        
        # Get investment score
        investment_score = engine.calculate_investment_score(locality_id)
        component_scores = engine.get_component_scores(locality_id)
        
        # Get market sentiment for additional data
        sentiment_data = engine.get_market_sentiment(locality_id=locality_id)
        latest = sentiment_data[0] if sentiment_data else {}
        
        # Deduct credits
        await _deduct_credits(user, 'view_detailed_sentiment')
        
        return InvestmentScoreResponse(
            locality_id=locality_id,
            investment_score=investment_score,
            sentiment_score=latest.get('sentiment_score'),
            price_momentum=latest.get('price_momentum'),
            demand_score=component_scores.get('demand'),
            supply_score=component_scores.get('supply')
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Sentiment] Error getting investment score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PRICE ANALYSIS ENDPOINTS (Free)
# ============================================================================

@router.get("/price-momentum/{locality_id}", response_model=PriceMomentumResponse)
async def get_price_momentum(
    locality_id: str = Path(..., description="Locality ID"),
    force_refresh: bool = Query(False, description="Force recalculation")
):
    """
    Get price momentum analysis for a locality.
    
    This endpoint is free to access.
    """
    try:
        engine = _get_sentiment_engine()
        
        momentum = engine.analyze_price_momentum(locality_id, force_refresh=force_refresh)
        
        return PriceMomentumResponse(
            locality_id=locality_id,
            current_price=momentum.get('current_price'),
            locality_name=momentum.get('locality_name'),
            change_30d=momentum.get('change_30d'),
            change_90d=momentum.get('change_90d'),
            change_180d=momentum.get('change_180d'),
            change_1yr=momentum.get('change_1yr'),
            momentum=momentum.get('momentum', 'neutral'),
            analyzed_at=momentum.get('analyzed_at', datetime.now().isoformat())
        )
    
    except Exception as e:
        logger.error(f"[Sentiment] Error getting price momentum: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price-history/{locality_id}", response_model=PriceHistoryResponse)
async def get_price_history(
    locality_id: str = Path(..., description="Locality ID"),
    days: int = Query(90, ge=30, le=365, description="Number of days to look back")
):
    """
    Get price history for a locality.
    
    This endpoint is free to access.
    """
    try:
        engine = _get_sentiment_engine()
        
        # Get current prices
        current_price = engine.calculate_price_per_sqft(locality_id)
        price_per_sqft = engine.calculate_price_per_sqft(locality_id)
        
        # Get trend data
        trends = engine.get_trend_data(locality_id, limit=days)
        
        return PriceHistoryResponse(
            locality_id=locality_id,
            current_price=current_price,
            price_per_sqft=price_per_sqft,
            price_trends=trends,
            analyzed_at=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"[Sentiment] Error getting price history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MARKET METRICS ENDPOINTS (Free)
# ============================================================================

@router.get("/rental-yield/{locality_id}", response_model=RentalYieldResponse)
async def get_rental_yield(
    locality_id: str = Path(..., description="Locality ID")
):
    """
    Get rental yield for a locality.
    
    This endpoint is free to access.
    """
    try:
        engine = _get_sentiment_engine()
        
        rental_yield = engine.calculate_rental_yield(locality_id)
        
        return RentalYieldResponse(
            locality_id=locality_id,
            rental_yield=rental_yield,
            calculated_at=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"[Sentiment] Error getting rental yield: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/days-on-market/{locality_id}", response_model=DaysOnMarketResponse)
async def get_days_on_market(
    locality_id: str = Path(..., description="Locality ID")
):
    """
    Get average days on market for a locality.
    
    This endpoint is free to access.
    """
    try:
        engine = _get_sentiment_engine()
        
        days_on_market = engine.calculate_days_on_market(locality_id)
        
        return DaysOnMarketResponse(
            locality_id=locality_id,
            days_on_market_avg=days_on_market,
            calculated_at=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"[Sentiment] Error getting days on market: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TRENDS ENDPOINTS
# ============================================================================

@router.get("/trending", response_model=TrendingLocalitiesResponse)
async def get_trending_localities(
    city: Optional[str] = Query(None, description="Filter by city"),
    limit: int = Query(10, ge=1, le=50, description="Maximum localities to return")
):
    """
    Get trending localities based on market sentiment.
    
    This endpoint is free to access.
    """
    try:
        engine = _get_sentiment_engine()
        
        trending = engine.get_trending_localities(city=city, limit=limit)
        
        return TrendingLocalitiesResponse(
            trending=trending,
            count=len(trending),
            analyzed_at=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"[Sentiment] Error getting trending localities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/{locality_id}", response_model=SentimentTrendsResponse)
async def get_sentiment_trends(
    locality_id: str = Path(..., description="Locality ID"),
    days: int = Query(30, ge=7, le=90, description="Number of days to look back"),
    user: User = Depends(require_auth)
):
    """
    Get historical sentiment trends for a locality.
    
    Requires 10 credits to access.
    """
    # Check credits
    allowed, required, available = await _check_credits(user, 'access_historical_trends')
    
    if not allowed:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Insufficient credits",
                "credits_required": required,
                "credits_available": available,
                "message": f"This endpoint requires {required} credits. You have {available} credits."
            }
        )
    
    try:
        engine = _get_sentiment_engine()
        
        # Get trend data
        trends = engine.get_trend_data(locality_id, limit=days)
        
        # If no trends exist, record current trend
        if not trends:
            engine.record_daily_trend(locality_id)
            trends = engine.get_trend_data(locality_id, limit=days)
        
        # Deduct credits
        await _deduct_credits(user, 'access_historical_trends')
        
        return SentimentTrendsResponse(
            locality_id=locality_id,
            trends=trends,
            count=len(trends),
            analyzed_at=datetime.now().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Sentiment] Error getting sentiment trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CREDIT CHECK ENDPOINT
# ============================================================================

@router.get("/credits/check", response_model=CreditCheckResponse)
async def check_credits(
    action: str = Query(..., description="Action to check credits for"),
    user: User = Depends(require_auth)
):
    """
    Check if user has enough credits for a sentiment action.
    
    Useful for frontend to check before making API calls.
    """
    engine = _get_sentiment_engine()
    credits_required = engine.get_credit_cost(action)
    
    rl = get_rate_limiter()
    user_data = rl.get_or_create_user(user.id)
    credits_available = user_data.get('total_available', 0)
    
    allowed = credits_available >= credits_required
    
    return CreditCheckResponse(
        allowed=allowed,
        credits_required=credits_required,
        credits_available=credits_available,
        message=f"{action} requires {credits_required} credits" if not allowed else "OK"
    )


# ============================================================================
# SCORE CALCULATION ENDPOINT (Free)
# ============================================================================

@router.get("/score/{locality_id}", response_model=SentimentScoreResponse)
async def get_sentiment_score(
    locality_id: str = Path(..., description="Locality ID"),
    force_refresh: bool = Query(False, description="Force recalculation")
):
    """
    Get sentiment score breakdown for a locality.
    
    This endpoint is free to access.
    """
    try:
        engine = _get_sentiment_engine()
        
        score_data = engine.calculate_sentiment_score(locality_id, force_refresh=force_refresh)
        
        return SentimentScoreResponse(
            locality_id=locality_id,
            overall_score=score_data.get('overall_score'),
            components=score_data.get('components', {}),
            calculated_at=score_data.get('calculated_at', datetime.now().isoformat())
        )
    
    except Exception as e:
        logger.error(f"[Sentiment] Error getting sentiment score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COMPONENT SCORES ENDPOINT (Free)
# ============================================================================

@router.get("/components/{locality_id}")
async def get_component_scores(
    locality_id: str = Path(..., description="Locality ID")
):
    """
    Get component scores (demand, supply, investment) for a locality.
    
    This endpoint is free to access.
    """
    try:
        engine = _get_sentiment_engine()
        
        components = engine.get_component_scores(locality_id)
        
        return {
            "success": True,
            "locality_id": locality_id,
            "components": components,
            "calculated_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"[Sentiment] Error getting component scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MARKET METRICS ENDPOINT (Free)
# ============================================================================

@router.get("/metrics/{locality_id}")
async def get_market_metrics(
    locality_id: str = Path(..., description="Locality ID")
):
    """
    Get comprehensive market metrics for a locality.
    
    This endpoint is free to access.
    """
    try:
        engine = _get_sentiment_engine()
        
        metrics = engine.get_market_metrics(locality_id)
        
        return {
            "success": True,
            "locality_id": locality_id,
            "metrics": metrics,
            "calculated_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"[Sentiment] Error getting market metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# INITIALIZATION ENDPOINT (Admin/Internal)
# ============================================================================

@router.post("/initialize")
async def initialize_sentiment_data(
    city: Optional[str] = Query(None, description="City to initialize (optional)"),
    user: User = Depends(require_auth)
):
    """
    Initialize sentiment data for localities.
    
    This is an admin/internal endpoint that refreshes all sentiment data.
    """
    # Check if user is admin
    from auth.user_auth import UserRole
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        engine = _get_sentiment_engine()
        
        result = engine.initialize_localities(city=city)
        
        return {
            "success": True,
            "message": f"Initialized {result['success_count']} localities",
            "details": result
        }
    
    except Exception as e:
        logger.error(f"[Sentiment] Error initializing sentiment data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh/{locality_id}")
async def refresh_locality_sentiment(
    locality_id: str = Path(..., description="Locality ID to refresh"),
    user: User = Depends(require_auth)
):
    """
    Refresh sentiment data for a specific locality.
    
    This is an admin/internal endpoint.
    """
    # Check if user is admin
    from auth.user_auth import UserRole
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        engine = _get_sentiment_engine()
        
        result = engine.refresh_locality(locality_id)
        
        return {
            "success": result,
            "message": f"Refreshed sentiment for {locality_id}" if result else "Failed to refresh"
        }
    
    except Exception as e:
        logger.error(f"[Sentiment] Error refreshing locality: {e}")
        raise HTTPException(status_code=500, detail=str(e))
