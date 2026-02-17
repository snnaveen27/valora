"""
Valora Credits-Based Rate Limiting System
Backward-compatible wrapper around UnifiedCreditsManager.

This module provides the same API as before but delegates to the unified system.
All new code should use ai.unified_credits directly.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

logger = logging.getLogger("valora.credits")


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining_credits: int
    total_credits: int
    reset_time: Optional[float]
    reason: Optional[str] = None
    tier: str = "free"


@dataclass
class UsageRecord:
    """Record of API usage."""
    timestamp: float
    user_id: str
    action: str
    credits_used: int
    model: Optional[str] = None
    inference_id: Optional[str] = None
    success: bool = True


class CreditsRateLimiter:
    """
    Backward-compatible wrapper around UnifiedCreditsManager.
    
    This class provides the same API as the original CreditsRateLimiter
    but delegates all operations to the unified credits manager.
    """
    
    # Expose constants from unified manager
    @property
    def TIER_CREDITS(self):
        from ai.unified_credits import UnifiedCreditsManager
        return UnifiedCreditsManager.TIERS
    
    @property
    def LLM_CREDIT_COSTS(self):
        from ai.unified_credits import UnifiedCreditsManager
        return UnifiedCreditsManager.LLM_COSTS
    
    @property
    def TOP_UP_PACKAGES(self):
        from ai.unified_credits import UnifiedCreditsManager
        return UnifiedCreditsManager.TOP_UP_PACKAGES
    
    @property
    def ADMIN_USERS(self):
        from ai.unified_credits import UnifiedCreditsManager
        return UnifiedCreditsManager.ADMIN_USERS
    
    @property
    def db_path(self):
        return self._manager.db_path
    
    def __init__(self, db_path: str = None):
        """Initialize with optional db_path (ignored, uses unified manager)."""
        from ai.unified_credits import get_credits_manager
        self._manager = get_credits_manager()
    
    def _is_admin(self, user_id: str) -> bool:
        """Check if user is admin."""
        return self._manager._is_admin(user_id)
    
    def get_or_create_user(self, user_id: str, tier: str = None) -> Dict[str, Any]:
        """Get or create user credits record."""
        return self._manager.get_or_create_user(user_id)
    
    def check_credits(self, user_id: str, model: str) -> RateLimitResult:
        """Check if user has enough credits for an inference."""
        result = self._manager.check_credits(user_id, model=model)
        return RateLimitResult(
            allowed=result.success,
            remaining_credits=result.remaining_credits,
            total_credits=result.total_credits,
            reset_time=self.get_or_create_user(user_id).get('reset_at'),
            reason=result.reason,
            tier=result.tier
        )
    
    def deduct_credits(
        self,
        user_id: str,
        model: str,
        inference_id: str = None,
        query_type: str = None,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """Deduct credits for an LLM inference call."""
        result = self._manager.charge_credits(
            user_id=user_id,
            model=model,
            session_id=inference_id,
            metadata=metadata
        )
        return result
    
    def add_top_up(self, user_id: str, package: str) -> Dict[str, Any]:
        """Add credits from a top-up purchase."""
        return self._manager.process_top_up(user_id, package)
    
    def update_tier(self, user_id: str, tier: str):
        """Update user tier after payment."""
        # Tier updates are handled automatically in the unified system
        logger.info(f"[Credits] Tier update requested for {user_id} to {tier}")
    
    def get_balance(self, user_id: str) -> Dict[str, Any]:
        """Get user's credit balance."""
        return self._manager.get_balance(user_id)
    
    def get_inference_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get inference history for a user."""
        # Use usage stats instead
        stats = self._manager.get_usage_stats(user_id, days=30)
        return stats.get('usage_by_action', [])[:limit]
    
    def get_usage_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for a user."""
        return self._manager.get_usage_stats(user_id, days=days)
    
    def add_credits(self, user_id: str, credits: int, source: str = "purchase") -> bool:
        """Add credits to user (for purchases or admin grants)."""
        result = self._manager.add_credits(user_id, credits, source=source)
        return result.get('success', False)
    
    def process_dummy_payment(
        self,
        user_id: str,
        amount_inr: int,
        credits_to_add: int
    ) -> Dict[str, Any]:
        """Process dummy payment for testing."""
        import hashlib
        import time
        
        transaction_id = f"DUMMY_{hashlib.md5(f'{user_id}:{time.time()}'.encode()).hexdigest()[:12]}"
        
        # Add credits
        self._manager.add_credits(user_id, credits_to_add, source="purchase")
        
        return {
            'success': True,
            'transaction_id': transaction_id,
            'amount_inr': amount_inr,
            'credits_added': credits_to_add,
            'payment_method': 'dummy',
            'message': 'Payment processed successfully (dummy mode)'
        }
    
    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics (placeholder for compatibility)."""
        return {
            'total_errors': 0,
            'error_types': [],
            'failed_intents': [],
            'recent_errors': []
        }


# Singleton instance
_rate_limiter = None

def get_rate_limiter() -> CreditsRateLimiter:
    """Get singleton rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = CreditsRateLimiter()
    return _rate_limiter
