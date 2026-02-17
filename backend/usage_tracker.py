"""
Valora AI - Usage Tracker (DEPRECATED)

This module is deprecated. All functionality has been moved to the unified
credits system in ai/unified_credits.py.

This file provides backward compatibility by redirecting to the new system.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Deprecation warning
logger.warning(
    "[DEPRECATED] usage_tracker.py is deprecated. "
    "Use ai.unified_credits.UnifiedCreditsManager instead."
)

# Training data directory (kept for compatibility)
TRAINING_DATA_DIR = Path(__file__).parent / "training_data"
TRAINING_DATA_DIR.mkdir(exist_ok=True)


def _load_pricing_config() -> Dict:
    """Load pricing configuration from database."""
    try:
        from database.pricing_db import get_pricing_db
        pricing_db = get_pricing_db()
        return pricing_db.get_config()
    except Exception as e:
        logger.error(f"[UsageTracker] Failed to load pricing config: {e}")
        return {}


def _save_pricing_config(config: Dict, updated_by: str = "system") -> bool:
    """Save pricing configuration to database."""
    try:
        from database.pricing_db import get_pricing_db
        pricing_db = get_pricing_db()
        return pricing_db.save_config(config, updated_by)
    except Exception as e:
        logger.error(f"[UsageTracker] Failed to save pricing config: {e}")
        return False


# Load pricing from database for backward compatibility
_pricing_config = _load_pricing_config()

# Compute costs per action type (kept for backward compatibility)
COMPUTE_COSTS = _pricing_config.get("action_costs", {
    "chat_query": 1,
    "chat_multiagent": 2,
    "chat_simulation": 10,
    "area_analysis": 3,
    "building_analysis": 3,
    "viewport_analysis": 1,
    "location_analysis": 3,
    "comparison": 3,
    "valuation": 5,
    "simulation_basic": 10,
    "simulation_advanced": 25,
    "property_search": 1,
    "poi_search": 1,
    "map_navigation": 0,
    "viewport_load": 0,
    "tileset_load": 0,
    "report_export": 10,
    "pdf_generation": 10,
})

# Tier-based monthly unit limits
TIER_MONTHLY_LIMITS = _pricing_config.get("tier_monthly_limits", {
    "free": 50,
    "pro": 500,
})


class UsageTracker:
    """
    DEPRECATED: Use ai.unified_credits.UnifiedCreditsManager instead.
    
    This class provides backward compatibility by delegating to the unified system.
    """
    
    def __init__(self, db_path: str = None, user_db=None):
        """Initialize with backward compatibility."""
        logger.warning(
            "[DEPRECATED] UsageTracker is deprecated. "
            "Use ai.unified_credits.get_credits_manager() instead."
        )
        from ai.unified_credits import get_credits_manager
        self._manager = get_credits_manager()
        self.db = None  # Not used anymore
        self.user_db = user_db
    
    def _init_tables(self):
        """No-op - tables are managed by unified system."""
        pass
    
    def _grant_admin_credits(self):
        """No-op - admin credits are handled by unified system."""
        pass
    
    def check_tier_monthly_limit(self, user_id: int) -> Tuple[bool, int, int]:
        """Check tier monthly limit."""
        # Convert int user_id to string for unified system
        user_id_str = str(user_id)
        user = self._manager.get_or_create_user(user_id_str)
        
        tier_config = self._manager.TIERS.get(user['tier'], self._manager.TIERS['free'])
        monthly_limit = tier_config['monthly_credits']
        used = user['used_credits']
        
        return (used < monthly_limit, used, monthly_limit)
    
    def get_user_balance(self, user_id: int) -> Dict[str, Any]:
        """Get user balance."""
        user_id_str = str(user_id)
        balance = self._manager.get_balance(user_id_str)
        
        return {
            'units_available': balance['total_available'],
            'units_used_lifetime': balance['used_credits'],
            'tier': balance['tier']
        }
    
    def initialize_balance(self, user_id: int, initial_units: int = 50):
        """Initialize user balance."""
        user_id_str = str(user_id)
        self._manager.get_or_create_user(user_id_str)
    
    def add_units(self, user_id: int, units: int, source: str = "purchase") -> bool:
        """Add units to user balance."""
        user_id_str = str(user_id)
        result = self._manager.add_credits(user_id_str, units, source=source)
        return result.get('success', False)
    
    def deduct_units(self, user_id: int, units: int, action_type: str = "api_call") -> Tuple[bool, str]:
        """Deduct units from user balance."""
        user_id_str = str(user_id)
        result = self._manager.charge_credits(user_id_str, action=action_type)
        
        if result.get('success'):
            return (True, f"Charged {units} units")
        else:
            return (False, result.get('error', 'Insufficient credits'))
    
    def track_action(
        self,
        user_id: int,
        action_type: str,
        metadata: Dict = None,
        session_id: str = None
    ) -> Tuple[bool, str, int]:
        """Track an action and charge credits."""
        user_id_str = str(user_id)
        result = self._manager.charge_credits(
            user_id_str,
            action=action_type,
            session_id=session_id,
            metadata=metadata
        )
        
        if result.get('success'):
            return (True, "Success", result.get('credits_charged', 0))
        else:
            return (False, result.get('error', 'Failed'), 0)
    
    def _log_event(self, user_id: int, action_type: str, units: int, metadata: Dict = None):
        """Log event - handled by charge_credits in unified system."""
        pass
    
    def get_user_usage_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get user usage statistics."""
        user_id_str = str(user_id)
        return self._manager.get_usage_stats(user_id_str, days=days)
    
    def get_global_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get global usage statistics."""
        return self._manager.get_global_stats(days=days)
    
    def collect_training_data(self, user_id: int, query: str, response: str, feedback: str = None):
        """Collect training data - no-op in unified system."""
        pass
    
    def award_training_contribution(self, user_id_hash: str, contribution_type: str, units: int = 5):
        """Award training contribution - no-op in unified system."""
        pass


# Singleton instance
_usage_tracker = None


def get_usage_tracker() -> UsageTracker:
    """Get or create usage tracker singleton (deprecated)."""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker
