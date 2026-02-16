"""
Valora Credits-Based Rate Limiting System
Dummy payment system for testing - ready for real payment gateway integration
"""

import logging
import sqlite3
import time
import hashlib
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("valora.credits")


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining_credits: int
    total_credits: int
    reset_time: Optional[float]  # Unix timestamp when credits reset
    reason: Optional[str] = None
    tier: str = "free"


@dataclass
class UsageRecord:
    """Record of API usage."""
    timestamp: float
    user_id: str
    action: str  # 'local_query', 'cloud_query', 'batch_analysis', etc.
    credits_used: int
    query_type: Optional[str] = None
    success: bool = True


class CreditsRateLimiter:
    """
    Rate limiting based on credits system.
    Supports tier-based monthly allowances and top-up purchases.
    """
    
    # Tier-based monthly credit allowances
    TIER_CREDITS = {
        'free': {'monthly_credits': 500, 'local_daily': 50, 'cloud_daily': 10},
        'pro': {'monthly_credits': 5000, 'local_daily': 500, 'cloud_daily': 100},
        'team': {'monthly_credits': 20000, 'local_daily': 2000, 'cloud_daily': 500},
        'enterprise': {'monthly_credits': 100000, 'local_daily': -1, 'cloud_daily': -1},  # Unlimited
    }
    
    # Credit costs per action
    ACTION_COSTS = {
        'local_query': 1,
        'cloud_query': 5,
        'batch_analysis': 10,  # Per location in batch
        'viewport_analysis': 2,
        'location_analyze': 2,
        'city_intelligence': 3,
        'storyboard_generate': 20,
        'investment_leaderboard': 1,
    }
    
    _INIT_SQL = """
    CREATE TABLE IF NOT EXISTS user_credits (
        user_id TEXT PRIMARY KEY,
        tier TEXT DEFAULT 'free',
        total_credits INTEGER DEFAULT 0,
        used_credits INTEGER DEFAULT 0,
        monthly_reset_at REAL,
        created_at REAL,
        updated_at REAL
    );
    CREATE TABLE IF NOT EXISTS usage_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        timestamp REAL,
        action TEXT,
        credits_used INTEGER,
        query_type TEXT,
        success BOOLEAN DEFAULT 1,
        metadata TEXT
    );
    CREATE TABLE IF NOT EXISTS payment_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        timestamp REAL,
        amount_inr INTEGER,
        credits_added INTEGER,
        payment_method TEXT,
        transaction_id TEXT,
        status TEXT
    );
    CREATE TABLE IF NOT EXISTS error_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL,
        user_id TEXT,
        query TEXT,
        intent_attempted TEXT,
        error_type TEXT,
        error_message TEXT,
        context TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_log(user_id);
    CREATE INDEX IF NOT EXISTS idx_usage_time ON usage_log(timestamp);
    CREATE INDEX IF NOT EXISTS idx_error_time ON error_log(timestamp);
    CREATE INDEX IF NOT EXISTS idx_error_user ON error_log(user_id);
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            from config import config
            db_path = str(config.DB_PATH.parent / "valora_credits.db")
        self.db_path = db_path
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection to credits database."""
        try:
            from core.sqlite_pool import get_pool
            pool = get_pool("credits", self.db_path, self._INIT_SQL)
            return pool.get()
        except Exception:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            return conn
    
    def get_or_create_user(self, user_id: str, tier: str = "free") -> Dict[str, Any]:
        """Get or create user credits record."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_credits WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        now = time.time()
        
        if row:
            # Check if monthly reset needed
            monthly_reset_at = row[4] or 0
            tier_config = self.TIER_CREDITS.get(row[1], self.TIER_CREDITS['free'])
            
            # Reset if it's been over a month
            if now - monthly_reset_at > 30 * 24 * 3600:
                cursor.execute("""
                    UPDATE user_credits
                    SET used_credits = 0, monthly_reset_at = ?, updated_at = ?
                    WHERE user_id = ?
                """, (now, now, user_id))
                conn.commit()
                used_credits = 0
            else:
                used_credits = row[3]
            
            total_credits = tier_config['monthly_credits']
            remaining = total_credits - used_credits
            
            return {
                'user_id': user_id,
                'tier': row[1],
                'total_credits': total_credits,
                'used_credits': used_credits,
                'remaining_credits': remaining,
                'reset_at': monthly_reset_at + 30 * 24 * 3600
            }
        
        # Create new user
        tier_config = self.TIER_CREDITS.get(tier, self.TIER_CREDITS['free'])
        cursor.execute("""
            INSERT INTO user_credits 
            (user_id, tier, total_credits, used_credits, monthly_reset_at, created_at, updated_at)
            VALUES (?, ?, ?, 0, ?, ?, ?)
        """, (user_id, tier, tier_config['monthly_credits'], now, now, now))
        
        conn.commit()
        
        return {
            'user_id': user_id,
            'tier': tier,
            'total_credits': tier_config['monthly_credits'],
            'used_credits': 0,
            'remaining_credits': tier_config['monthly_credits'],
            'reset_at': now + 30 * 24 * 3600
        }
    
    def check_rate_limit(
        self,
        user_id: str,
        action: str,
        query_type: Optional[str] = None
    ) -> RateLimitResult:
        """
        Check if action is allowed within rate limits.
        
        Args:
            user_id: User identifier
            action: Action type (local_query, cloud_query, etc.)
            query_type: Optional specific query type for tracking
            
        Returns:
            RateLimitResult with allowed status and remaining credits
        """
        user = self.get_or_create_user(user_id)
        tier_config = self.TIER_CREDITS.get(user['tier'], self.TIER_CREDITS['free'])
        
        # Get cost for action
        cost = self.ACTION_COSTS.get(action, 1)
        
        # Check daily limits for specific action types
        if action == 'local_query' and tier_config['local_daily'] > 0:
            daily_used = self._get_daily_usage(user_id, action)
            if daily_used >= tier_config['local_daily']:
                return RateLimitResult(
                    allowed=False,
                    remaining_credits=user['remaining_credits'],
                    total_credits=user['total_credits'],
                    reset_time=user['reset_at'],
                    reason=f"Daily local query limit reached ({tier_config['local_daily']}/day)",
                    tier=user['tier']
                )
        
        if action == 'cloud_query' and tier_config['cloud_daily'] > 0:
            daily_used = self._get_daily_usage(user_id, action)
            if daily_used >= tier_config['cloud_daily']:
                return RateLimitResult(
                    allowed=False,
                    remaining_credits=user['remaining_credits'],
                    total_credits=user['total_credits'],
                    reset_time=user['reset_at'],
                    reason=f"Daily cloud query limit reached ({tier_config['cloud_daily']}/day). Upgrade to Pro for more.",
                    tier=user['tier']
                )
        
        # Check monthly credits
        if user['remaining_credits'] < cost:
            return RateLimitResult(
                allowed=False,
                remaining_credits=0,
                total_credits=user['total_credits'],
                reset_time=user['reset_at'],
                reason=f"Insufficient credits. Need {cost}, have {user['remaining_credits']}. Purchase more credits or wait for monthly reset.",
                tier=user['tier']
            )
        
        return RateLimitResult(
            allowed=True,
            remaining_credits=user['remaining_credits'] - cost,
            total_credits=user['total_credits'],
            reset_time=user['reset_at'],
            tier=user['tier']
        )
    
    def record_usage(
        self,
        user_id: str,
        action: str,
        success: bool = True,
        query_type: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Record credit usage for an action."""
        try:
            cost = self.ACTION_COSTS.get(action, 1)
            
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Log usage
            cursor.execute("""
                INSERT INTO usage_log (user_id, timestamp, action, credits_used, query_type, success, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                time.time(),
                action,
                cost,
                query_type,
                success,
                str(metadata) if metadata else None
            ))
            
            # Update user credits
            cursor.execute("""
                UPDATE user_credits
                SET used_credits = used_credits + ?, updated_at = ?
                WHERE user_id = ?
            """, (cost, time.time(), user_id))
            
            conn.commit()
            return True
        except Exception as e:
            logger.warning(f"Error recording usage: {e}")
            return False
    
    def _get_daily_usage(self, user_id: str, action: str) -> int:
        """Get usage count for today."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Start of today
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_ts = today.timestamp()
        
        cursor.execute("""
            SELECT COUNT(*) FROM usage_log
            WHERE user_id = ? AND action = ? AND timestamp >= ?
        """, (user_id, action, today_ts))
        
        count = cursor.fetchone()[0]
        return count
    
    def log_error(
        self,
        user_id: str,
        query: str,
        intent_attempted: Optional[str],
        error_type: str,
        error_message: str,
        context: Optional[Dict] = None
    ):
        """Log error for aggregation and pattern analysis."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO error_log (timestamp, user_id, query, intent_attempted, error_type, error_message, context)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            time.time(),
            user_id,
            query[:500],  # Limit query length
            intent_attempted,
            error_type,
            error_message[:500],
            str(context) if context else None
        ))
        
        conn.commit()
    
    def get_error_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get error statistics for the dashboard."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        since = time.time() - (days * 24 * 3600)
        
        # Error counts by type
        cursor.execute("""
            SELECT error_type, COUNT(*) as cnt
            FROM error_log
            WHERE timestamp >= ?
            GROUP BY error_type
            ORDER BY cnt DESC
        """, (since,))
        
        error_types = [
            {'type': row[0], 'count': row[1]}
            for row in cursor.fetchall()
        ]
        
        # Failed intents
        cursor.execute("""
            SELECT intent_attempted, COUNT(*) as cnt
            FROM error_log
            WHERE timestamp >= ? AND intent_attempted IS NOT NULL
            GROUP BY intent_attempted
            ORDER BY cnt DESC
        """, (since,))
        
        failed_intents = [
            {'intent': row[0], 'count': row[1]}
            for row in cursor.fetchall()
        ]
        
        # Recent errors
        cursor.execute("""
            SELECT timestamp, user_id, query, error_type, error_message
            FROM error_log
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 20
        """, (since,))
        
        recent_errors = [
            {
                'timestamp': row[0],
                'user_id': row[1],
                'query': row[2],
                'error_type': row[3],
                'error_message': row[4]
            }
            for row in cursor.fetchall()
        ]
        
        return {
            'period_days': days,
            'total_errors': sum(e['count'] for e in error_types),
            'error_types': error_types,
            'failed_intents': failed_intents,
            'recent_errors': recent_errors
        }
    
    def add_credits(self, user_id: str, credits: int, source: str = "purchase") -> bool:
        """Add credits to user (for purchases or admin grants)."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE user_credits
            SET total_credits = total_credits + ?, updated_at = ?
            WHERE user_id = ?
        """, (credits, time.time(), user_id))
        
        conn.commit()
        return True
    
    def process_dummy_payment(
        self,
        user_id: str,
        amount_inr: int,
        credits_to_add: int
    ) -> Dict[str, Any]:
        """
        Process dummy payment for testing.
        Returns success - ready to integrate with real payment gateway.
        """
        transaction_id = f"DUMMY_{hashlib.md5(f'{user_id}:{time.time()}'.encode()).hexdigest()[:12]}"
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Log payment attempt
        cursor.execute("""
            INSERT INTO payment_history (user_id, timestamp, amount_inr, credits_added, payment_method, transaction_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, time.time(), amount_inr, credits_to_add, 'dummy', transaction_id, 'completed'))
        
        conn.commit()
        
        # Add credits
        self.add_credits(user_id, credits_to_add, source="purchase")
        
        return {
            'success': True,
            'transaction_id': transaction_id,
            'amount_inr': amount_inr,
            'credits_added': credits_to_add,
            'payment_method': 'dummy',
            'message': 'Payment processed successfully (dummy mode)'
        }
    
    def get_usage_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for a user."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        since = time.time() - (days * 24 * 3600)
        
        # Usage by action
        cursor.execute("""
            SELECT action, COUNT(*) as cnt, SUM(credits_used) as total_credits
            FROM usage_log
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY action
        """, (user_id, since))
        
        usage_by_action = [
            {'action': row[0], 'count': row[1], 'credits': row[2]}
            for row in cursor.fetchall()
        ]
        
        # Daily usage
        cursor.execute("""
            SELECT DATE(timestamp, 'unixepoch') as day, COUNT(*) as cnt
            FROM usage_log
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY day
            ORDER BY day DESC
        """, (user_id, since))
        
        daily_usage = [
            {'date': row[0], 'queries': row[1]}
            for row in cursor.fetchall()
        ]
        
        user = self.get_or_create_user(user_id)
        
        return {
            'user_id': user_id,
            'tier': user['tier'],
            'remaining_credits': user['remaining_credits'],
            'total_credits': user['total_credits'],
            'period_days': days,
            'usage_by_action': usage_by_action,
            'daily_usage': daily_usage,
            'total_queries': sum(u['count'] for u in usage_by_action)
        }


# Singleton instance
_rate_limiter = None

def get_rate_limiter() -> CreditsRateLimiter:
    """Get singleton rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = CreditsRateLimiter()
    return _rate_limiter
