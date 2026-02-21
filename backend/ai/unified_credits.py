"""
Valora Unified Credits System
Production-ready credit management with:
- Simple 2-tier system: Free (50 credits) and Pro (500 credits)
- Admin users get Pro tier automatically
- Top-up credits that never expire
- Monthly credit reset with rollover for Pro
- Unified tracking for all API usage
"""

import logging
import sqlite3
import time
import hashlib
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("valora.credits")


@dataclass
class CreditResult:
    """Result of credit operation."""
    success: bool
    remaining_credits: int
    total_credits: int
    credits_used: int = 0
    reason: Optional[str] = None
    tier: str = "free"


class UnifiedCreditsManager:
    """
    Production-ready unified credit management system.
    
    TIERS:
    - Free: 50 credits/month
    - Pro: 500 credits/month + rollover
    
    CREDIT COSTS:
    - Local LLM (Ollama): 2 credits
    - Cloud LLM: 5 credits
    - API actions: Variable (see ACTION_COSTS)
    
    SPECIAL:
    - Admin users automatically get Pro tier
    - Top-up credits never expire
    - Pro tier gets rollover of unused monthly credits
    """
    
    # Tier configuration
    TIERS = {
        'free': {
            'monthly_credits': 50,
            'rollover': False,
            'features': ['basic_search', 'area_overview', 'chat']
        },
        'pro': {
            'monthly_credits': 500,
            'rollover': True,
            'max_rollover': 500,
            'features': ['full_search', 'area_analysis', 'valuation', 'simulation', 'report_export']
        }
    }
    
    # LLM credit costs
    LLM_COSTS = {
        'local': 2,   # Ollama local models
        'cloud': 5,   # Cloud models (deepseek, openrouter)
    }
    
    # API action costs (for non-LLM operations)
    ACTION_COSTS = {
        'chat_query': 1,
        'chat_multiagent': 2,
        'chat_simulation': 10,
        'area_analysis': 3,
        'building_analysis': 9,  # 3x area_analysis as building analysis is more detailed
        'viewport_analysis': 1,
        'location_analysis': 3,
        'comparison': 3,
        'valuation': 5,
        'simulation_basic': 10,
        'simulation_advanced': 25,
        'property_search': 1,
        'poi_search': 1,
        'report_export': 10,
        'pdf_generation': 10,
        'detailed_report': 200,  # Comprehensive AI-powered report with all tabs
        'feedback_reward': -5,  # Negative = credits earned
    }
    
    # Top-up packages (INR)
    TOP_UP_PACKAGES = {
        'starter': {'price': 59, 'credits': 100, 'bonus': 0},
        'standard': {'price': 139, 'credits': 300, 'bonus': 30},
        'power': {'price': 399, 'credits': 1000, 'bonus': 200},
    }
    
    # Admin users (auto-upgraded to Pro)
    ADMIN_USERS = ['admin', 'admin@valora.ai', 'nvnsa', '1', 'Admin']
    
    # Pro users with initial credits (email -> initial credits)
    PRO_USER_CREDITS = {
        'prouser@valora.ai': 2000,  # Pro user with 2000 credits
    }
    
    # Local model patterns
    LOCAL_MODELS = ['qwen', 'phi', 'llama', 'mistral', 'valora-2025v1']
    
    # Database schema
    _SCHEMA = """
    -- User credit balances
    CREATE TABLE IF NOT EXISTS user_credits (
        user_id TEXT PRIMARY KEY,
        tier TEXT DEFAULT 'free',
        monthly_credits INTEGER DEFAULT 0,
        top_up_credits INTEGER DEFAULT 0,
        used_credits INTEGER DEFAULT 0,
        rollover_credits INTEGER DEFAULT 0,
        total_earned INTEGER DEFAULT 0,  -- From feedback, referrals
        monthly_reset_at REAL,
        created_at REAL,
        updated_at REAL
    );
    
    -- All usage logging (unified)
    CREATE TABLE IF NOT EXISTS usage_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        timestamp REAL NOT NULL,
        action_type TEXT NOT NULL,
        credits_charged INTEGER NOT NULL,
        model TEXT,
        query_type TEXT,
        session_id TEXT,
        metadata TEXT,
        success BOOLEAN DEFAULT 1
    );
    
    -- Payment history
    CREATE TABLE IF NOT EXISTS payment_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        timestamp REAL NOT NULL,
        amount_inr INTEGER,
        credits_added INTEGER,
        payment_method TEXT,
        transaction_id TEXT,
        status TEXT DEFAULT 'completed'
    );
    
    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_log(user_id, timestamp);
    CREATE INDEX IF NOT EXISTS idx_usage_action ON usage_log(action_type, timestamp);
    CREATE INDEX IF NOT EXISTS idx_payment_user ON payment_history(user_id, timestamp);
    """
    
    def __init__(self, db_path: str = None):
        """Initialize the unified credits manager."""
        if db_path is None:
            from config import config
            db_path = str(config.DB_PATH.parent / "valora_credits.db")
        self.db_path = db_path
        self._init_db()
        logger.info(f"[Credits] Unified credits manager initialized: {db_path}")
    
    def _init_db(self):
        """Initialize database with schema."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        
        cursor = conn.cursor()
        
        # Check for schema migration
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_credits'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(user_credits)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Add missing columns
            if 'total_earned' not in columns:
                logger.info("[Credits] Adding total_earned column to user_credits")
                cursor.execute("ALTER TABLE user_credits ADD COLUMN total_earned INTEGER DEFAULT 0")
        
        # Create tables
        conn.executescript(self._SCHEMA)
        conn.commit()
        conn.close()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn
    
    def _is_admin(self, user_id: str) -> bool:
        """Check if user is admin."""
        return user_id.lower() in [a.lower() for a in self.ADMIN_USERS]
    
    def _get_llm_type(self, model: str) -> str:
        """Determine if model is local or cloud."""
        model_lower = model.lower() if model else ''
        if any(local in model_lower for local in self.LOCAL_MODELS):
            return 'local'
        return 'cloud'
    
    def get_action_cost(self, action: str) -> int:
        """Get credit cost for an action."""
        return self.ACTION_COSTS.get(action, 1)
    
    def get_llm_cost(self, model: str) -> int:
        """Get credit cost for an LLM call."""
        llm_type = self._get_llm_type(model)
        return self.LLM_COSTS[llm_type]
    
    # =========================================================================
    # USER MANAGEMENT
    # =========================================================================
    
    def get_or_create_user(self, user_id: str) -> Dict[str, Any]:
        """Get or create user credit record."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Determine tier (admin = pro, pro users = pro)
        is_admin = self._is_admin(user_id)
        is_pro_user = user_id.lower() in [u.lower() for u in self.PRO_USER_CREDITS.keys()]
        tier = 'pro' if (is_admin or is_pro_user) else 'free'
        tier_config = self.TIERS[tier]
        
        cursor.execute("SELECT * FROM user_credits WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        now = time.time()
        
        if row:
            current_tier = row['tier']
            monthly_reset_at = row['monthly_reset_at'] or 0
            
            # Upgrade admin users to pro
            if is_admin and current_tier != 'pro':
                logger.info(f"[Credits] Upgrading admin user {user_id} to Pro")
                cursor.execute("""
                    UPDATE user_credits 
                    SET tier = 'pro', monthly_credits = ?, updated_at = ?
                    WHERE user_id = ?
                """, (tier_config['monthly_credits'], now, user_id))
                conn.commit()
                current_tier = 'pro'
            
            # Upgrade pro users to pro tier and grant initial credits if not already granted
            if is_pro_user and current_tier != 'pro':
                initial_top_up = self.PRO_USER_CREDITS.get(user_id.lower(), 0)
                logger.info(f"[Credits] Upgrading pro user {user_id} to Pro with {initial_top_up} initial credits")
                cursor.execute("""
                    UPDATE user_credits 
                    SET tier = 'pro', monthly_credits = ?, top_up_credits = ?, updated_at = ?
                    WHERE user_id = ?
                """, (tier_config['monthly_credits'], initial_top_up, now, user_id))
                conn.commit()
                current_tier = 'pro'
            
            tier_config = self.TIERS.get(current_tier, self.TIERS['free'])
            
            # Check for monthly reset
            if now - monthly_reset_at > 30 * 24 * 3600:
                rollover = 0
                if tier_config.get('rollover'):
                    remaining = (row['monthly_credits'] or 0) + (row['rollover_credits'] or 0) - (row['used_credits'] or 0)
                    rollover = min(remaining, tier_config.get('max_rollover', 500))
                
                cursor.execute("""
                    UPDATE user_credits
                    SET monthly_credits = ?,
                        rollover_credits = ?,
                        used_credits = 0,
                        monthly_reset_at = ?,
                        updated_at = ?
                    WHERE user_id = ?
                """, (tier_config['monthly_credits'], rollover, now, now, user_id))
                conn.commit()
                
                monthly_credits = tier_config['monthly_credits']
                rollover_credits = rollover
                used_credits = 0
            else:
                monthly_credits = row['monthly_credits'] or 0
                rollover_credits = row['rollover_credits'] or 0
                used_credits = row['used_credits'] or 0
            
            top_up_credits = row['top_up_credits'] or 0
            total_earned = row['total_earned'] or 0
            total_available = monthly_credits + rollover_credits + top_up_credits + total_earned - used_credits
            
            conn.close()
            
            return {
                'user_id': user_id,
                'tier': current_tier,
                'is_admin': is_admin,
                'monthly_credits': monthly_credits,
                'rollover_credits': rollover_credits,
                'top_up_credits': top_up_credits,
                'total_earned': total_earned,
                'used_credits': used_credits,
                'total_available': max(0, total_available),
                'reset_at': (monthly_reset_at or now) + 30 * 24 * 3600
            }
        
        # Create new user
        # Check if pro user gets initial credits
        initial_top_up = 0
        if is_pro_user:
            initial_top_up = self.PRO_USER_CREDITS.get(user_id.lower(), 0)
            if initial_top_up > 0:
                logger.info(f"[Credits] Granting {initial_top_up} initial credits to pro user {user_id}")
        
        cursor.execute("""
            INSERT INTO user_credits 
            (user_id, tier, monthly_credits, top_up_credits, monthly_reset_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, tier, tier_config['monthly_credits'], initial_top_up, now, now, now))
        conn.commit()
        conn.close()
        
        return {
            'user_id': user_id,
            'tier': tier,
            'is_admin': is_admin,
            'monthly_credits': tier_config['monthly_credits'],
            'rollover_credits': 0,
            'top_up_credits': initial_top_up,
            'total_earned': 0,
            'used_credits': 0,
            'total_available': tier_config['monthly_credits'] + initial_top_up,
            'reset_at': now + 30 * 24 * 3600
        }
    
    # =========================================================================
    # CREDIT OPERATIONS
    # =========================================================================
    
    def check_credits(self, user_id: str, action: str = None, model: str = None) -> CreditResult:
        """Check if user has enough credits for an action."""
        user = self.get_or_create_user(user_id)
        
        # Determine cost
        if model:
            cost = self.get_llm_cost(model)
        elif action:
            cost = self.get_action_cost(action)
        else:
            cost = 1
        
        # Negative cost means earning credits
        if cost < 0:
            return CreditResult(
                success=True,
                remaining_credits=user['total_available'],
                total_credits=user['monthly_credits'] + user['top_up_credits'],
                credits_used=0,
                tier=user['tier']
            )
        
        if user['total_available'] < cost:
            return CreditResult(
                success=False,
                remaining_credits=user['total_available'],
                total_credits=user['monthly_credits'] + user['top_up_credits'],
                credits_used=cost,
                reason=f"Insufficient credits. Need {cost}, have {user['total_available']}",
                tier=user['tier']
            )
        
        return CreditResult(
            success=True,
            remaining_credits=user['total_available'] - cost,
            total_credits=user['monthly_credits'] + user['top_up_credits'],
            credits_used=cost,
            tier=user['tier']
        )
    
    def charge_credits(
        self,
        user_id: str,
        action: str = None,
        model: str = None,
        session_id: str = None,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """Charge credits for an action or LLM call."""
        user = self.get_or_create_user(user_id)
        
        # Determine cost and type
        if model:
            cost = self.get_llm_cost(model)
            action_type = f"llm_{self._get_llm_type(model)}"
        elif action:
            cost = self.get_action_cost(action)
            action_type = action
        else:
            cost = 1
            action_type = 'unknown'
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Handle negative cost (earning credits)
        if cost < 0:
            credits_earned = abs(cost)
            cursor.execute("""
                UPDATE user_credits
                SET total_earned = total_earned + ?, updated_at = ?
                WHERE user_id = ?
            """, (credits_earned, time.time(), user_id))
            
            # Log the earning
            cursor.execute("""
                INSERT INTO usage_log (user_id, timestamp, action_type, credits_charged, session_id, metadata, success)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (user_id, time.time(), action_type, -credits_earned, session_id, json.dumps(metadata) if metadata else None))
            
            conn.commit()
            updated = self.get_or_create_user(user_id)
            conn.close()
            
            return {
                'success': True,
                'credits_earned': credits_earned,
                'action': action_type,
                'remaining_credits': updated['total_available']
            }
        
        # Check if enough credits
        if user['total_available'] < cost:
            conn.close()
            return {
                'success': False,
                'error': 'insufficient_credits',
                'required': cost,
                'available': user['total_available']
            }
        
        # Deduct credits (priority: top_up first, then monthly)
        if user['top_up_credits'] >= cost:
            cursor.execute("""
                UPDATE user_credits
                SET top_up_credits = top_up_credits - ?, updated_at = ?
                WHERE user_id = ?
            """, (cost, time.time(), user_id))
        else:
            remaining = cost - user['top_up_credits']
            cursor.execute("""
                UPDATE user_credits
                SET top_up_credits = 0, used_credits = used_credits + ?, updated_at = ?
                WHERE user_id = ?
            """, (remaining, time.time(), user_id))
        
        # Log usage
        cursor.execute("""
            INSERT INTO usage_log (user_id, timestamp, action_type, credits_charged, model, session_id, metadata, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (user_id, time.time(), action_type, cost, model, session_id, json.dumps(metadata) if metadata else None))
        
        conn.commit()
        updated = self.get_or_create_user(user_id)
        conn.close()
        
        return {
            'success': True,
            'credits_charged': cost,
            'action': action_type,
            'model': model,
            'remaining_credits': updated['total_available']
        }
    
    def add_credits(self, user_id: str, credits: int, source: str = "purchase") -> Dict[str, Any]:
        """Add credits to user account."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Ensure user exists
        self.get_or_create_user(user_id)
        
        # Add to top_up_credits (never expire)
        cursor.execute("""
            UPDATE user_credits
            SET top_up_credits = top_up_credits + ?, updated_at = ?
            WHERE user_id = ?
        """, (credits, time.time(), user_id))
        
        # Log as payment if purchase
        if source == "purchase":
            cursor.execute("""
                INSERT INTO payment_history (user_id, timestamp, credits_added, payment_method, status)
                VALUES (?, ?, ?, 'top_up', 'completed')
            """, (user_id, time.time(), credits))
        
        conn.commit()
        updated = self.get_or_create_user(user_id)
        conn.close()
        
        logger.info(f"[Credits] Added {credits} credits to {user_id} (source: {source})")
        
        return {
            'success': True,
            'credits_added': credits,
            'source': source,
            'new_balance': updated['total_available']
        }
    
    def award_feedback_credits(self, user_id: str, quality_score: int = 3) -> Dict[str, Any]:
        """Award credits for feedback submission."""
        # Base reward: 5 credits, bonus for high quality
        base_credits = 5
        bonus = max(0, quality_score - 3) * 2  # +2 per point above 3
        total_credits = base_credits + bonus
        
        return self.add_credits(user_id, total_credits, source="feedback")
    
    # =========================================================================
    # TOP-UP & PAYMENTS
    # =========================================================================
    
    def process_top_up(self, user_id: str, package_id: str, payment_method: str = "demo") -> Dict[str, Any]:
        """Process a top-up purchase."""
        package = self.TOP_UP_PACKAGES.get(package_id)
        if not package:
            return {'success': False, 'error': 'Invalid package'}
        
        total_credits = package['credits'] + package['bonus']
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Ensure user exists
        self.get_or_create_user(user_id)
        
        # Add credits
        cursor.execute("""
            UPDATE user_credits
            SET top_up_credits = top_up_credits + ?, updated_at = ?
            WHERE user_id = ?
        """, (total_credits, time.time(), user_id))
        
        # Log payment
        transaction_id = f"TXN_{hashlib.md5(f'{user_id}:{time.time()}'.encode()).hexdigest()[:12]}"
        cursor.execute("""
            INSERT INTO payment_history 
            (user_id, timestamp, amount_inr, credits_added, payment_method, transaction_id, status)
            VALUES (?, ?, ?, ?, ?, ?, 'completed')
        """, (user_id, time.time(), package['price'], total_credits, payment_method, transaction_id))
        
        conn.commit()
        updated = self.get_or_create_user(user_id)
        conn.close()
        
        logger.info(f"[Credits] Top-up: {user_id} bought {package_id} (+{total_credits} credits)")
        
        return {
            'success': True,
            'transaction_id': transaction_id,
            'package': package_id,
            'credits_added': total_credits,
            'amount_inr': package['price'],
            'new_balance': updated['total_available']
        }
    
    # =========================================================================
    # QUERIES & STATS
    # =========================================================================
    
    def get_balance(self, user_id: str) -> Dict[str, Any]:
        """Get user's credit balance."""
        user = self.get_or_create_user(user_id)
        return {
            'user_id': user['user_id'],
            'tier': user['tier'],
            'is_admin': user['is_admin'],
            'monthly_credits': user['monthly_credits'],
            'rollover_credits': user['rollover_credits'],
            'top_up_credits': user['top_up_credits'],
            'total_earned': user['total_earned'],
            'total_available': user['total_available'],
            'used_credits': user['used_credits'],
            'next_reset': user['reset_at']
        }
    
    def get_credit_tier(self, user_id: str) -> str:
        """
        Get user's credit tier for response customization.
        
        Returns the credit tier based on available credits:
        - 'high': >= 200 credits (can afford detailed report)
        - 'medium': >= 10 credits (can afford most operations)
        - 'low': >= 3 credits (can afford basic analysis)
        - 'none': < 3 credits (only free operations)
        
        Args:
            user_id: The user identifier
            
        Returns:
            str: One of 'high', 'medium', 'low', or 'none'
        """
        user = self.get_or_create_user(user_id)
        credits = user['total_available']
        
        if credits >= 200:
            return 'high'
        elif credits >= 10:
            return 'medium'
        elif credits >= 3:
            return 'low'
        return 'none'
    
    def get_usage_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for a user."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        since = time.time() - (days * 24 * 3600)
        
        # Usage by action
        cursor.execute("""
            SELECT action_type, COUNT(*) as count, SUM(credits_charged) as total_credits
            FROM usage_log
            WHERE user_id = ? AND timestamp >= ? AND credits_charged > 0
            GROUP BY action_type
        """, (user_id, since))
        
        usage_by_action = [
            {'action': row['action_type'], 'count': row['count'], 'credits': row['total_credits'] or 0}
            for row in cursor.fetchall()
        ]
        
        # Daily usage
        cursor.execute("""
            SELECT DATE(timestamp, 'unixepoch') as day, 
                   COUNT(*) as count, 
                   SUM(credits_charged) as credits
            FROM usage_log
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY day
            ORDER BY day DESC
        """, (user_id, since))
        
        daily_usage = [
            {'date': row['day'], 'queries': row['count'], 'credits': row['credits'] or 0}
            for row in cursor.fetchall()
        ]
        
        # Credits earned
        cursor.execute("""
            SELECT SUM(ABS(credits_charged)) as earned
            FROM usage_log
            WHERE user_id = ? AND timestamp >= ? AND credits_charged < 0
        """, (user_id, since))
        
        earned_row = cursor.fetchone()
        credits_earned = earned_row['earned'] or 0 if earned_row else 0
        
        conn.close()
        
        user = self.get_or_create_user(user_id)
        
        return {
            'user_id': user_id,
            'tier': user['tier'],
            'remaining_credits': user['total_available'],
            'total_credits': user['monthly_credits'] + user['top_up_credits'],
            'period_days': days,
            'usage_by_action': usage_by_action,
            'daily_usage': daily_usage,
            'total_queries': sum(u['count'] for u in usage_by_action),
            'total_credits_used': sum(u['credits'] for u in usage_by_action),
            'credits_earned': credits_earned
        }
    
    def get_payment_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get payment history for a user."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, amount_inr, credits_added, payment_method, transaction_id, status
            FROM payment_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        history = [
            {
                'timestamp': row['timestamp'],
                'amount_inr': row['amount_inr'],
                'credits_added': row['credits_added'],
                'method': row['payment_method'],
                'transaction_id': row['transaction_id'],
                'status': row['status']
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return history
    
    def get_global_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get global usage statistics (admin only)."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        since = time.time() - (days * 24 * 3600)
        
        # Total queries
        cursor.execute("""
            SELECT COUNT(*) as total, SUM(credits_charged) as credits
            FROM usage_log
            WHERE timestamp >= ? AND credits_charged > 0
        """, (since,))
        
        row = cursor.fetchone()
        total_queries = row['total'] or 0
        total_credits = row['credits'] or 0
        
        # Active users
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM usage_log
            WHERE timestamp >= ?
        """, (since,))
        
        active_users = cursor.fetchone()['count'] or 0
        
        # Top actions
        cursor.execute("""
            SELECT action_type, COUNT(*) as count
            FROM usage_log
            WHERE timestamp >= ?
            GROUP BY action_type
            ORDER BY count DESC
            LIMIT 10
        """, (since,))
        
        top_actions = [
            {'action': row['action_type'], 'count': row['count']}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            'period_days': days,
            'total_queries': total_queries,
            'total_credits_used': total_credits,
            'active_users': active_users,
            'top_actions': top_actions
        }


# Singleton instance
_credits_manager = None

def get_credits_manager() -> UnifiedCreditsManager:
    """Get singleton credits manager instance."""
    global _credits_manager
    if _credits_manager is None:
        _credits_manager = UnifiedCreditsManager()
    return _credits_manager
