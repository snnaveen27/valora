"""
Sentiment Engine for Community Pulse - Phase 3: Sentiment Dashboard

This service handles market sentiment analysis, price trends, and investment intelligence.
It processes user signals, calculates sentiment scores, analyzes price momentum, and 
provides market metrics for localities in the Valora real estate platform.
"""

import sqlite3
import json
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from functools import lru_cache
from collections import defaultdict
import importlib.util
try:
    from config import config
except ImportError:
    try:
        from backend.config import config
    except ImportError:
        # Fallback - use environment variable or default path
        import os
        config = type('obj', (object,), {
            'DB_PATH': os.environ.get('DB_PATH', 'storage/database/valora.db')
        })()

# Import schema directly to avoid package __init__ circular imports
import importlib.util
schema_spec = importlib.util.spec_from_file_location(
    "community_pulse_schema", 
    Path(__file__).parent.parent / "database" / "community_pulse_schema.py"
)
if schema_spec and schema_spec.loader:
    schema_module = importlib.util.module_from_spec(schema_spec)
    schema_spec.loader.exec_module(schema_module)
    CommunityPulseDB = schema_module.CommunityPulseDB
    record_signal = schema_module.record_signal
    get_signals_by_locality = schema_module.get_signals_by_locality
    get_aggregated_signals = schema_module.get_aggregated_signals
    create_market_sentiment = schema_module.create_market_sentiment
    get_market_sentiment = schema_module.get_market_sentiment
    update_market_sentiment = schema_module.update_market_sentiment
    get_sentiment_history = schema_module.get_sentiment_history
    get_trending_localities = schema_module.get_trending_localities
    record_trend = schema_module.record_trend
    get_trends = schema_module.get_trends
    calculate_sentiment_score = schema_module.calculate_sentiment_score
else:
    raise ImportError("Could not load community_pulse_schema module")

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

# Signal weights for sentiment calculation
SIGNAL_WEIGHTS = {
    'property_view': 1,
    'property_save': 3,
    'property_share': 5,
    'analysis_request': 4,
    'search': 2
}

# Sentiment score weights (must sum to 1.0)
SENTIMENT_WEIGHTS = {
    'user_signals': 0.40,      # User signals weight
    'locality_reviews': 0.30,  # Locality reviews sentiment
    'price_trends': 0.20,      # Price trends
    'market_activity': 0.10   # Market activity
}

# Credit costs for API access
CREDIT_COSTS = {
    'view_detailed_sentiment': 5,
    'access_historical_trends': 10
}

# Cache TTL settings (in seconds)
CACHE_TTL = {
    'sentiment_score': 300,    # 5 minutes
    'price_momentum': 600,    # 10 minutes
    'trending_localities': 900 # 15 minutes
}


# ============================================================================
# SENTIMENT ENGINE CLASS
# ============================================================================

class SentimentEngine:
    """
    Main sentiment analysis engine for market sentiment, price trends,
    and investment intelligence.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize the SentimentEngine.
        
        Args:
            db_path: Optional path to database file. Uses main DB if not specified.
        """
        self.db_path = db_path or str(config.DB_PATH)
        self.db = CommunityPulseDB(self.db_path)
        
        # In-memory cache for expensive calculations
        self._cache = {}
        self._cache_time = {}
        
        logger.info(f"[SentimentEngine] Initialized with database at {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache_time:
            return False
        
        ttl = CACHE_TTL.get(key, 300)
        elapsed = (datetime.now() - self._cache_time[key]).total_seconds()
        return elapsed < ttl
    
    def _set_cache(self, key: str, value: Any) -> None:
        """Set cache entry with current timestamp."""
        self._cache[key] = value
        self._cache_time[key] = datetime.now()
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """Get cache entry if valid."""
        if self._is_cache_valid(key):
            return self._cache.get(key)
        return None
    
    def _clear_cache(self, key: str = None) -> None:
        """Clear cache entries."""
        if key:
            self._cache.pop(key, None)
            self._cache_time.pop(key, None)
        else:
            self._cache.clear()
            self._cache_time.clear()
    
    # =========================================================================
    # SIGNAL PROCESSING
    # =========================================================================
    
    def process_signal(
        self,
        signal_type: str,
        user_hash: str,
        locality_id: str = None,
        property_id: str = None,
        signal_data: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Process a user signal for sentiment analysis.
        
        Args:
            signal_type: Type of signal (property_view, property_save, property_share, 
                        analysis_request, search)
            user_hash: Anonymized user identifier
            locality_id: Optional locality ID
            property_id: Optional property ID
            signal_data: Additional signal data
        
        Returns:
            Signal ID if successful, None otherwise
        """
        # Validate signal type
        if signal_type not in SIGNAL_WEIGHTS:
            logger.warning(f"[SentimentEngine] Unknown signal type: {signal_type}")
            return None
        
        # Record the signal
        signal_id = record_signal(
            self.db,
            signal_type=signal_type,
            user_hash=user_hash,
            locality_id=locality_id,
            property_id=property_id,
            signal_data=signal_data
        )
        
        if signal_id:
            # Invalidate relevant caches
            if locality_id:
                self._clear_cache(f"signals_{locality_id}")
            self._clear_cache("aggregated_signals")
        
        return signal_id
    
    def get_signals_for_locality(
        self,
        locality_id: str,
        signal_type: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get signals for a specific locality.
        
        Args:
            locality_id: Locality ID
            signal_type: Optional signal type filter
            limit: Maximum records
        
        Returns:
            List of signal records
        """
        cache_key = f"signals_{locality_id}_{signal_type}_{limit}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        signals = get_signals_by_locality(
            self.db,
            locality_id=locality_id,
            signal_type=signal_type,
            limit=limit
        )
        
        self._set_cache(cache_key, signals)
        return signals
    
    def get_aggregated_signals(
        self,
        locality_id: str = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get aggregated signal counts for a locality or overall.
        
        Args:
            locality_id: Optional locality ID
            days: Number of days to aggregate
        
        Returns:
            Dict with aggregated signal counts
        """
        if locality_id:
            cache_key = f"agg_signals_{locality_id}_{days}"
        else:
            cache_key = f"agg_signals_all_{days}"
        
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        aggregated = get_aggregated_signals(
            self.db,
            locality_id=locality_id,
            days=days
        )
        
        self._set_cache(cache_key, aggregated)
        return aggregated
    
    def calculate_activity_score(
        self,
        locality_id: str = None,
        days: int = 30
    ) -> float:
        """
        Calculate activity score from aggregated signals.
        
        Args:
            locality_id: Optional locality ID
            days: Number of days to analyze
        
        Returns:
            Activity score (0-100)
        """
        signals = self.get_aggregated_signals(locality_id, days)
        
        if not signals or signals.get('total', 0) == 0:
            return 0.0
        
        # Calculate weighted score
        weighted_sum = 0
        total_weight = 0
        
        for signal_type, weight in SIGNAL_WEIGHTS.items():
            count = signals.get(signal_type, 0)
            weighted_sum += count * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        # Normalize to 0-100 scale
        max_possible = signals.get('total', 1) * max(SIGNAL_WEIGHTS.values())
        score = (weighted_sum / max_possible) * 100 if max_possible > 0 else 0
        
        return min(100.0, max(0.0, score))
    
    # =========================================================================
    # SENTIMENT SCORE CALCULATION
    # =========================================================================
    
    def calculate_user_signals_score(
        self,
        locality_id: str,
        days: int = 30
    ) -> float:
        """
        Calculate sentiment score from user signals (40% weight).
        
        Args:
            locality_id: Locality ID
            days: Number of days to analyze
        
        Returns:
            Score (0-100)
        """
        return self.calculate_activity_score(locality_id, days)
    
    def get_locality_reviews_sentiment(
        self,
        locality_id: str
    ) -> float:
        """
        Get sentiment from locality reviews (30% weight).
        
        Args:
            locality_id: Locality ID
        
        Returns:
            Sentiment score (0-100)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Get average rating from locality_reviews
            cursor.execute("""
                SELECT AVG(overall_rating) as avg_rating,
                       COUNT(*) as review_count
                FROM locality_reviews
                WHERE locality_id = ? AND status = 'active'
            """, (locality_id,))
            
            row = cursor.fetchone()
            
            if not row or row['avg_rating'] is None:
                return 50.0  # Neutral if no reviews
            
            # Convert 1-5 rating to 0-100 scale
            avg_rating = row['avg_rating']
            review_count = row['review_count']
            
            # Weight by review count (more reviews = more confidence)
            base_score = (avg_rating / 5.0) * 100
            
            # Boost for verified reviews
            cursor.execute("""
                SELECT COUNT(*) as verified_count
                FROM locality_reviews
                WHERE locality_id = ? AND status = 'active' AND is_verified = 1
            """, (locality_id,))
            
            verified_row = cursor.fetchone()
            verified_boost = 0
            if verified_row and verified_row['verified_count']:
                verified_ratio = verified_row['verified_count'] / review_count
                verified_boost = verified_ratio * 10  # Up to 10 point boost
            
            return min(100.0, base_score + verified_boost)
        
        finally:
            conn.close()
    
    def get_price_trends_score(
        self,
        locality_id: str
    ) -> float:
        """
        Get sentiment from price trends (20% weight).
        
        Args:
            locality_id: Locality ID
        
        Returns:
            Score (0-100)
        """
        # Get price momentum
        momentum = self.analyze_price_momentum(locality_id)
        
        if not momentum or not momentum.get('current_price'):
            return 50.0  # Neutral if no data
        
        # Base score on momentum
        momentum_score = 50.0
        
        price_change = momentum.get('change_30d', 0)
        
        if price_change > 10:
            momentum_score = 80.0  # Strong growth
        elif price_change > 5:
            momentum_score = 65.0  # Moderate growth
        elif price_change > 0:
            momentum_score = 55.0  # Slight growth
        elif price_change > -5:
            momentum_score = 45.0  # Slight decline
        elif price_change > -10:
            momentum_score = 30.0  # Moderate decline
        else:
            momentum_score = 20.0  # Strong decline
        
        return momentum_score
    
    def get_market_activity_score(
        self,
        locality_id: str
    ) -> float:
        """
        Get market activity score (10% weight).
        
        Args:
            locality_id: Locality ID
        
        Returns:
            Score (0-100)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Check recent transactions and listings
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN created_at >= datetime('now', '-30 days') THEN 1 END) as recent_listings,
                    COUNT(*) as total_listings
                FROM properties
                WHERE locality_id = ? AND status = 'active'
            """, (locality_id,))
            
            row = cursor.fetchone()
            
            if not row or row['total_listings'] == 0:
                return 30.0  # Low activity
            
            recent_listings = row['recent_listings'] or 0
            total_listings = row['total_listings'] or 1
            
            # Calculate activity ratio
            activity_ratio = recent_listings / max(total_listings, 1)
            
            # Score based on activity
            if activity_ratio > 0.3:
                return 80.0  # High activity
            elif activity_ratio > 0.15:
                return 65.0  # Moderate activity
            elif activity_ratio > 0.05:
                return 50.0  # Normal activity
            else:
                return 35.0  # Low activity
        
        finally:
            conn.close()
    
    def calculate_sentiment_score(
        self,
        locality_id: str,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate overall sentiment score (0-100) from all components.
        
        Args:
            locality_id: Locality ID
            force_refresh: Force recalculation even if cached
        
        Returns:
            Dict with overall score and component scores
        """
        cache_key = f"sentiment_score_{locality_id}"
        
        if not force_refresh:
            cached = self._get_cache(cache_key)
            if cached is not None:
                return cached
        
        # Calculate component scores
        user_signals_score = self.calculate_user_signals_score(locality_id)
        locality_reviews_score = self.get_locality_reviews_sentiment(locality_id)
        price_trends_score = self.get_price_trends_score(locality_id)
        market_activity_score = self.get_market_activity_score(locality_id)
        
        # Calculate weighted overall score
        overall_score = (
            user_signals_score * SENTIMENT_WEIGHTS['user_signals'] +
            locality_reviews_score * SENTIMENT_WEIGHTS['locality_reviews'] +
            price_trends_score * SENTIMENT_WEIGHTS['price_trends'] +
            market_activity_score * SENTIMENT_WEIGHTS['market_activity']
        )
        
        result = {
            'overall_score': round(overall_score, 2),
            'components': {
                'user_signals': {
                    'score': round(user_signals_score, 2),
                    'weight': SENTIMENT_WEIGHTS['user_signals'],
                    'contribution': round(
                        user_signals_score * SENTIMENT_WEIGHTS['user_signals'], 2
                    )
                },
                'locality_reviews': {
                    'score': round(locality_reviews_score, 2),
                    'weight': SENTIMENT_WEIGHTS['locality_reviews'],
                    'contribution': round(
                        locality_reviews_score * SENTIMENT_WEIGHTS['locality_reviews'], 2
                    )
                },
                'price_trends': {
                    'score': round(price_trends_score, 2),
                    'weight': SENTIMENT_WEIGHTS['price_trends'],
                    'contribution': round(
                        price_trends_score * SENTIMENT_WEIGHTS['price_trends'], 2
                    )
                },
                'market_activity': {
                    'score': round(market_activity_score, 2),
                    'weight': SENTIMENT_WEIGHTS['market_activity'],
                    'contribution': round(
                        market_activity_score * SENTIMENT_WEIGHTS['market_activity'], 2
                    )
                }
            },
            'calculated_at': datetime.now().isoformat()
        }
        
        self._set_cache(cache_key, result)
        return result
    
    # =========================================================================
    # COMPONENT SCORES
    # =========================================================================
    
    def calculate_demand_score(self, locality_id: str) -> float:
        """
        Calculate demand score based on views, saves, searches.
        
        Args:
            locality_id: Locality ID
        
        Returns:
            Demand score (0-100)
        """
        signals = self.get_aggregated_signals(locality_id, days=30)
        
        if not signals or signals.get('total', 0) == 0:
            return 0.0
        
        # Demand indicators
        views = signals.get('property_view', 0)
        saves = signals.get('property_save', 0)
        searches = signals.get('search', 0)
        
        # Weighted demand calculation
        demand_score = (
            views * 1.0 +
            saves * 3.0 +  # Saves indicate strong intent
            searches * 2.0
        )
        
        # Normalize to 0-100
        max_demand = signals.get('total', 1) * 5
        return min(100.0, (demand_score / max_demand) * 100) if max_demand > 0 else 0.0
    
    def calculate_supply_score(self, locality_id: str) -> float:
        """
        Calculate supply score based on new listings and inventory.
        
        Args:
            locality_id: Locality ID
        
        Returns:
            Supply score (0-100)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Get listing counts
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_listings,
                    COUNT(CASE WHEN created_at >= datetime('now', '-30 days') THEN 1 END) as new_listings
                FROM properties
                WHERE locality_id = ? AND status = 'active'
            """, (locality_id,))
            
            row = cursor.fetchone()
            
            if not row or row['total_listings'] == 0:
                return 0.0
            
            total = row['total_listings']
            new_30d = row['new_listings'] or 0
            
            # Supply is high when there are many listings
            # But very high supply can indicate oversupply
            supply_ratio = new_30d / max(total, 1)
            
            if supply_ratio > 0.5:
                return 90.0  # High supply (rapid inventory growth)
            elif supply_ratio > 0.3:
                return 70.0  # Good supply
            elif supply_ratio > 0.1:
                return 50.0  # Balanced supply
            elif supply_ratio > 0.05:
                return 30.0  # Low supply
            else:
                return 15.0  # Very low supply
        
        finally:
            conn.close()
    
    def calculate_investment_score(self, locality_id: str) -> float:
        """
        Calculate investment score based on price trends and rental yields.
        
        Args:
            locality_id: Locality ID
        
        Returns:
            Investment score (0-100)
        """
        # Get market sentiment data
        sentiment_data = self.get_market_sentiment(locality_id)
        
        if not sentiment_data:
            return 50.0  # Neutral if no data
        
        latest = sentiment_data[0]  # Most recent
        
        # Base score from sentiment score
        sentiment_score = latest.get('sentiment_score', 50)
        
        # Adjust for momentum
        momentum = latest.get('price_momentum', 'neutral')
        
        if momentum == 'bullish':
            investment_score = sentiment_score + 10
        elif momentum == 'bearish':
            investment_score = sentiment_score - 10
        else:
            investment_score = sentiment_score
        
        return min(100.0, max(0.0, investment_score))
    
    def get_component_scores(self, locality_id: str) -> Dict[str, float]:
        """
        Get all component scores for a locality.
        
        Args:
            locality_id: Locality ID
        
        Returns:
            Dict with demand, supply, and investment scores
        """
        return {
            'demand': round(self.calculate_demand_score(locality_id), 2),
            'supply': round(self.calculate_supply_score(locality_id), 2),
            'investment': round(self.calculate_investment_score(locality_id), 2)
        }
    
    # =========================================================================
    # PRICE MOMENTUM ANALYSIS
    # =========================================================================
    
    def analyze_price_momentum(
        self,
        locality_id: str,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze price changes over various time periods.
        
        Args:
            locality_id: Locality ID
            force_refresh: Force recalculation
        
        Returns:
            Dict with price momentum analysis
        """
        cache_key = f"price_momentum_{locality_id}"
        
        if not force_refresh:
            cached = self._get_cache(cache_key)
            if cached is not None:
                return cached
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Try to get price data from locality_state table
            cursor.execute("""
                SELECT avg_price_sqft, locality_name
                FROM locality_state
                WHERE locality_id = ?
            """, (locality_id,))
            
            row = cursor.fetchone()
            
            if not row:
                return {
                    'current_price': None,
                    'change_30d': None,
                    'change_90d': None,
                    'change_180d': None,
                    'change_1yr': None,
                    'momentum': 'neutral'
                }
            
            current_price = row['avg_price_sqft']
            
            # Calculate momentum based on recent activity
            # This is simplified - in production would need historical price data
            signals = self.get_aggregated_signals(locality_id, days=30)
            activity_factor = 0
            
            if signals and signals.get('total', 0) > 0:
                # Higher activity suggests price pressure
                activity_factor = min(10, signals['total'] / 10)
            
            # Estimate changes based on sentiment
            sentiment_data = self.get_market_sentiment(locality_id)
            
            change_30d = activity_factor
            change_90d = activity_factor * 2.5
            change_180d = activity_factor * 4
            change_1yr = activity_factor * 7
            
            # Determine momentum
            if change_30d > 5:
                momentum = 'bullish'
            elif change_30d < -5:
                momentum = 'bearish'
            else:
                momentum = 'neutral'
            
            result = {
                'current_price': current_price,
                'locality_name': row['locality_name'],
                'change_30d': round(change_30d, 2),
                'change_90d': round(change_90d, 2),
                'change_180d': round(change_180d, 2),
                'change_1yr': round(change_1yr, 2),
                'momentum': momentum,
                'analyzed_at': datetime.now().isoformat()
            }
            
            self._set_cache(cache_key, result)
            return result
        
        finally:
            conn.close()
    
    def get_price_change_percentage(
        self,
        locality_id: str,
        period: str = '30d'
    ) -> float:
        """
        Get price change percentage for a specific period.
        
        Args:
            locality_id: Locality ID
            period: Period (30d, 90d, 180d, 1yr)
        
        Returns:
            Price change percentage
        """
        momentum = self.analyze_price_momentum(locality_id)
        
        period_key = f'change_{period}'
        return momentum.get(period_key, 0.0)
    
    # =========================================================================
    # TREND ANALYSIS
    # =========================================================================
    
    def record_daily_trend(
        self,
        locality_id: str,
        trend_date: str = None
    ) -> Optional[str]:
        """
        Record daily sentiment trend for a locality.
        
        Args:
            locality_id: Locality ID
            trend_date: Date for the trend (YYYY-MM-DD). Uses today if not specified.
        
        Returns:
            Trend ID if successful, None otherwise
        """
        if trend_date is None:
            trend_date = datetime.now().strftime('%Y-%m-%d')
        
        # Get aggregated data for the day
        signals = self.get_aggregated_signals(locality_id, days=1)
        sentiment_score_data = self.calculate_sentiment_score(locality_id)
        
        # Get average price
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT AVG(price) as avg_price
                FROM properties
                WHERE locality_id = ? AND status = 'active'
            """, (locality_id,))
            
            row = cursor.fetchone()
            avg_price = row['avg_price'] if row else None
        
        finally:
            conn.close()
        
        activity_count = signals.get('total', 0) if signals else 0
        search_volume = signals.get('search', 0) if signals else 0
        
        return record_trend(
            self.db,
            locality_id=locality_id,
            trend_date=trend_date,
            sentiment_score=sentiment_score_data.get('overall_score'),
            price_avg=avg_price,
            activity_count=activity_count,
            search_volume=search_volume
        )
    
    def get_trend_data(
        self,
        locality_id: str,
        start_date: str = None,
        end_date: str = None,
        limit: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Get sentiment trends for a locality.
        
        Args:
            locality_id: Locality ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum records
        
        Returns:
            List of trend records
        """
        return get_trends(
            self.db,
            locality_id=locality_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    
    def calculate_moving_average(
        self,
        locality_id: str,
        window: int = 7
    ) -> Optional[float]:
        """
        Calculate moving average for sentiment score.
        
        Args:
            locality_id: Locality ID
            window: Number of days for moving average
        
        Returns:
            Moving average score, or None if insufficient data
        """
        trends = self.get_trend_data(locality_id, limit=window)
        
        if not trends or len(trends) < window // 2:
            return None
        
        scores = [t['sentiment_score'] for t in trends if t.get('sentiment_score')]
        
        if not scores:
            return None
        
        return sum(scores) / len(scores)
    
    def get_trending_localities(
        self,
        city: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get trending localities based on sentiment.
        
        Args:
            city: Optional city filter
            limit: Maximum localities to return
        
        Returns:
            List of trending localities
        """
        cache_key = f"trending_{city}_{limit}"
        
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        trending = get_trending_localities(
            self.db,
            city=city,
            limit=limit
        )
        
        self._set_cache(cache_key, trending)
        return trending
    
    # =========================================================================
    # MARKET METRICS
    # =========================================================================
    
    def calculate_days_on_market(self, locality_id: str) -> Optional[int]:
        """
        Calculate average days on market for a locality.
        
        Args:
            locality_id: Locality ID
        
        Returns:
            Average days on market, or None if no data
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT AVG(
                    CAST((julianday('now') - julianday(created_at)) AS INTEGER)
                ) as avg_days
                FROM properties
                WHERE locality_id = ? 
                  AND status = 'active'
                  AND created_at IS NOT NULL
            """, (locality_id,))
            
            row = cursor.fetchone()
            return int(row['avg_days']) if row and row['avg_days'] else None
        
        finally:
            conn.close()
    
    def calculate_price_per_sqft(self, locality_id: str) -> Optional[float]:
        """
        Calculate average price per sqft for a locality.
        
        Args:
            locality_id: Locality ID
        
        Returns:
            Average price per sqft, or None if no data
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # First try from properties table
            cursor.execute("""
                SELECT AVG(price_per_sqft) as avg_ppsft
                FROM properties
                WHERE locality_id = ? 
                  AND status = 'active'
                  AND price_per_sqft IS NOT NULL
            """, (locality_id,))
            
            row = cursor.fetchone()
            
            if row and row['avg_ppsft']:
                return round(row['avg_ppsft'], 2)
            
            # Fallback to locality_state
            cursor.execute("""
                SELECT avg_price_sqft
                FROM locality_state
                WHERE locality_id = ?
            """, (locality_id,))
            
            row = cursor.fetchone()
            return round(row['avg_price_sqft'], 2) if row and row['avg_price_sqft'] else None
        
        finally:
            conn.close()
    
    def calculate_rental_yield(
        self,
        locality_id: str
    ) -> Dict[str, Optional[float]]:
        """
        Calculate rental yields for a locality.
        
        Args:
            locality_id: Locality ID
        
        Returns:
            Dict with min, max, and average rental yields
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Get price and rental data
            cursor.execute("""
                SELECT 
                    AVG(price) as avg_price,
                    AVG(expected_rent) as avg_rent
                FROM properties
                WHERE locality_id = ? 
                  AND status = 'active'
                  AND price IS NOT NULL
                  AND expected_rent IS NOT NULL
            """, (locality_id,))
            
            row = cursor.fetchone()
            
            if not row or not row['avg_price'] or not row['avg_rent']:
                return {'min': None, 'max': None, 'avg': None}
            
            # Calculate annual yield
            annual_rent = row['avg_rent'] * 12
            avg_yield = (annual_rent / row['avg_price']) * 100
            
            # Estimate min/max (simplified)
            return {
                'min': round(avg_yield * 0.7, 2),
                'max': round(avg_yield * 1.3, 2),
                'avg': round(avg_yield, 2)
            }
        
        finally:
            conn.close()
    
    def get_inventory_count(self, locality_id: str) -> int:
        """
        Get current inventory count for a locality.
        
        Args:
            locality_id: Locality ID
        
        Returns:
            Number of active listings
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM properties
                WHERE locality_id = ? AND status = 'active'
            """, (locality_id,))
            
            row = cursor.fetchone()
            return row['count'] if row else 0
        
        finally:
            conn.close()
    
    def get_new_listings_count(
        self,
        locality_id: str,
        days: int = 30
    ) -> int:
        """
        Get count of new listings in the last N days.
        
        Args:
            locality_id: Locality ID
            days: Number of days to look back
        
        Returns:
            Number of new listings
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM properties
                WHERE locality_id = ? 
                  AND status = 'active'
                  AND created_at >= datetime('now', '-' || ? || ' days')
            """, (locality_id, days))
            
            row = cursor.fetchone()
            return row['count'] if row else 0
        
        finally:
            conn.close()
    
    def get_market_metrics(self, locality_id: str) -> Dict[str, Any]:
        """
        Get comprehensive market metrics for a locality.
        
        Args:
            locality_id: Locality ID
        
        Returns:
            Dict with all market metrics
        """
        return {
            'days_on_market_avg': self.calculate_days_on_market(locality_id),
            'price_per_sqft': self.calculate_price_per_sqft(locality_id),
            'rental_yield': self.calculate_rental_yield(locality_id),
            'inventory_count': self.get_inventory_count(locality_id),
            'new_listings_30d': self.get_new_listings_count(locality_id, 30),
            'new_listings_90d': self.get_new_listings_count(locality_id, 90)
        }
    
    # =========================================================================
    # MARKET SENTIMENT CRUD
    # =========================================================================
    
    def create_market_sentiment(
        self,
        locality_id: str,
        locality_name: str,
        city: str = None,
        **kwargs
    ) -> Optional[str]:
        """
        Create a new market sentiment record.
        
        Args:
            locality_id: Locality ID
            locality_name: Locality name
            city: City name
            **kwargs: Additional fields
        
        Returns:
            Sentiment record ID if successful, None otherwise
        """
        # Calculate scores
        sentiment_score = self.calculate_sentiment_score(locality_id)
        component_scores = self.get_component_scores(locality_id)
        market_metrics = self.get_market_metrics(locality_id)
        price_momentum = self.analyze_price_momentum(locality_id)
        
        return create_market_sentiment(
            self.db,
            locality_id=locality_id,
            locality_name=locality_name,
            city=city,
            price_current=price_momentum.get('current_price'),
            price_change_pct=price_momentum.get('change_30d'),
            price_momentum=price_momentum.get('momentum'),
            sentiment_score=sentiment_score.get('overall_score'),
            demand_score=component_scores.get('demand'),
            supply_score=component_scores.get('supply'),
            investment_score=component_scores.get('investment'),
            days_on_market_avg=market_metrics.get('days_on_market_avg'),
            price_per_sqft_avg=market_metrics.get('price_per_sqft'),
            inventory_count=market_metrics.get('inventory_count'),
            new_listings_30d=market_metrics.get('new_listings_30d'),
            rental_yield_avg=market_metrics.get('rental_yield', {}).get('avg'),
            rental_yield_min=market_metrics.get('rental_yield', {}).get('min'),
            rental_yield_max=market_metrics.get('rental_yield', {}).get('max'),
            sentiment_breakdown=sentiment_score.get('components'),
            trend_indicators=price_momentum,
            **kwargs
        )
    
    def get_market_sentiment(
        self,
        locality_id: str = None,
        city: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get market sentiment records.
        
        Args:
            locality_id: Optional locality filter
            city: Optional city filter
            limit: Maximum records
        
        Returns:
            List of market sentiment records
        """
        return get_market_sentiment(
            self.db,
            locality_id=locality_id,
            city=city,
            limit=limit
        )
    
    def update_market_sentiment(
        self,
        locality_id: str,
        **kwargs
    ) -> bool:
        """
        Update a market sentiment record.
        
        Args:
            locality_id: Locality ID
            **kwargs: Fields to update
        
        Returns:
            True if successful, False otherwise
        """
        return update_market_sentiment(
            self.db,
            locality_id,
            **kwargs
        )
    
    def get_sentiment_history(
        self,
        locality_id: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get historical sentiment records for a locality.
        
        Args:
            locality_id: Locality ID
            limit: Maximum records
        
        Returns:
            List of historical sentiment records
        """
        return get_sentiment_history(
            self.db,
            locality_id=locality_id,
            limit=limit
        )
    
    # =========================================================================
    # INITIALIZATION AND REFRESH
    # =========================================================================
    
    def initialize_localities(self, city: str = None) -> Dict[str, Any]:
        """
        Initialize/refresh sentiment data for all localities.
        
        Args:
            city: Optional city filter
        
        Returns:
            Dict with initialization results
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Get all localities
            if city:
                cursor.execute("""
                    SELECT locality_id, locality_name, city
                    FROM locality_state
                    WHERE city = ?
                    ORDER BY hotspot_score DESC
                """, (city,))
            else:
                cursor.execute("""
                    SELECT locality_id, locality_name, city
                    FROM locality_state
                    ORDER BY hotspot_score DESC
                """)
            
            localities = cursor.fetchall()
            
            success_count = 0
            error_count = 0
            errors = []
            
            for loc in localities:
                try:
                    # Create or update sentiment record
                    result = self.create_market_sentiment(
                        locality_id=loc['locality_id'],
                        locality_name=loc['locality_name'],
                        city=loc.get('city')
                    )
                    
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                
                except Exception as e:
                    error_count += 1
                    errors.append({
                        'locality_id': loc['locality_id'],
                        'error': str(e)
                    })
                    logger.error(f"[SentimentEngine] Failed to initialize {loc['locality_id']}: {e}")
            
            # Clear all caches
            self._clear_cache()
            
            return {
                'success_count': success_count,
                'error_count': error_count,
                'total': len(localities),
                'errors': errors[:10]  # Limit error details
            }
        
        finally:
            conn.close()
    
    def refresh_locality(self, locality_id: str) -> bool:
        """
        Refresh sentiment data for a specific locality.
        
        Args:
            locality_id: Locality ID
        
        Returns:
            True if successful, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Get locality info
            cursor.execute("""
                SELECT locality_id, locality_name, city
                FROM locality_state
                WHERE locality_id = ?
            """, (locality_id,))
            
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"[SentimentEngine] Locality not found: {locality_id}")
                return False
            
            # Create updated sentiment
            result = self.create_market_sentiment(
                locality_id=row['locality_id'],
                locality_name=row['locality_name'],
                city=row.get('city')
            )
            
            # Clear caches for this locality
            self._clear_cache(f"sentiment_score_{locality_id}")
            self._clear_cache(f"price_momentum_{locality_id}")
            
            return result is not None
        
        finally:
            conn.close()
    
    # =========================================================================
    # CREDIT COST CHECK
    # =========================================================================
    
    def get_credit_cost(self, action: str) -> int:
        """
        Get credit cost for an action.
        
        Args:
            action: Action name
        
        Returns:
            Credit cost, or 0 if not found
        """
        return CREDIT_COSTS.get(action, 0)
    
    def check_credit_access(
        self,
        user_credits: int,
        action: str
    ) -> tuple[bool, str]:
        """
        Check if user has enough credits for an action.
        
        Args:
            user_credits: User's current credit balance
            action: Action to perform
        
        Returns:
            Tuple of (allowed, message)
        """
        cost = self.get_credit_cost(action)
        
        if cost == 0:
            return True, "No credit cost"
        
        if user_credits < cost:
            return False, f"Insufficient credits. Need {cost}, have {user_credits}"
        
        return True, f"Action costs {cost} credits"


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_sentiment_engine = None


def get_sentiment_engine(db_path: str = None) -> SentimentEngine:
    """
    Get or create SentimentEngine singleton.
    
    Args:
        db_path: Optional database path
    
    Returns:
        SentimentEngine instance
    """
    global _sentiment_engine
    if _sentiment_engine is None:
        _sentiment_engine = SentimentEngine(db_path)
    return _sentiment_engine


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def process_signal(
    signal_type: str,
    user_hash: str,
    locality_id: str = None,
    property_id: str = None,
    signal_data: Dict[str, Any] = None
) -> Optional[str]:
    """Process a user signal."""
    return get_sentiment_engine().process_signal(
        signal_type, user_hash, locality_id, property_id, signal_data
    )


def get_sentiment(locality_id: str) -> Dict[str, Any]:
    """Get sentiment score for a locality."""
    return get_sentiment_engine().calculate_sentiment_score(locality_id)


def get_market_metrics(locality_id: str) -> Dict[str, Any]:
    """Get market metrics for a locality."""
    return get_sentiment_engine().get_market_metrics(locality_id)


def get_price_momentum(locality_id: str) -> Dict[str, Any]:
    """Get price momentum analysis for a locality."""
    return get_sentiment_engine().analyze_price_momentum(locality_id)


def get_trending_localities(city: str = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Get trending localities."""
    return get_sentiment_engine().get_trending_localities(city, limit)
