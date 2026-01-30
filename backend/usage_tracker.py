"""
Valora AI - Usage Tracker
Compute-based pricing: Users pay with compute units for actions.
Automatic data collection for product improvement.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

from database.db_service import DatabaseService

logger = logging.getLogger(__name__)

# Training data directory
TRAINING_DATA_DIR = Path(__file__).parent / "training_data"
TRAINING_DATA_DIR.mkdir(exist_ok=True)

# Pricing configuration file
PRICING_CONFIG_FILE = Path(__file__).parent / "config" / "pricing_config.json"

def _load_pricing_config() -> Dict:
    """Load pricing configuration from JSON file."""
    try:
        if PRICING_CONFIG_FILE.exists():
            with open(PRICING_CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"[UsageTracker] Pricing config not found at {PRICING_CONFIG_FILE}, using defaults")
            return {}
    except Exception as e:
        logger.error(f"[UsageTracker] Failed to load pricing config: {e}")
        return {}

def _save_pricing_config(config: Dict) -> bool:
    """Save pricing configuration to JSON file."""
    try:
        PRICING_CONFIG_FILE.parent.mkdir(exist_ok=True)
        with open(PRICING_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"[UsageTracker] Pricing config saved")
        return True
    except Exception as e:
        logger.error(f"[UsageTracker] Failed to save pricing config: {e}")
        return False

# Load pricing from config file
_pricing_config = _load_pricing_config()

# Compute costs per action type (in units)
# ALIGNED WITH BUSINESS_MODEL_AND_PLAN.md Section 6.1
# Loaded from config/pricing_config.json (admin-editable)
COMPUTE_COSTS = _pricing_config.get("action_costs", {
    # Fallback defaults if config not found
    "chat_query": 1,
    "chat_multiagent": 1,
    "chat_simulation": 25,
    "area_analysis": 3,
    "building_analysis": 3,
    "viewport_analysis": 3,
    "location_analysis": 3,
    "comparison": 3,
    "valuation": 10,
    "investment_analysis": 10,
    "simulation_basic": 25,
    "simulation_advanced": 25,
    "storyboard_generation": 15,
    "scenario_analysis": 25,
    "property_search": 2,
    "poi_search": 2,
    "map_navigation": 0,
    "viewport_load": 0,
    "tileset_load": 0,
    "report_export": 20,
    "dashboard_snapshot": 10,
    "pdf_generation": 20,
    "infrastructure_card": 3,
    "investment_card": 10,
    "livability_card": 3,
    "market_card": 3,
    "terrain_card": 3,
    "spatial_card": 3,
    "comparison_card": 3,
    "locality_brain": 3,
    "growth_prediction": 10,
    "risk_assessment": 10,
    "explainability": 1,
    "fact_verification": 1,
    "causal_reasoning": 10,
})

# Tier-based monthly unit limits (from BUSINESS_MODEL_AND_PLAN.md Section 6.1)
TIER_MONTHLY_LIMITS = _pricing_config.get("tier_monthly_limits", {
    "free": 50,
    "pro": 1000,
    "team": 3000,
    "enterprise": -1,
    "admin": -1,
})

# Free actions (no charge)
FREE_ACTIONS = [
    "map_navigation",
    "tileset_load",
    "health_check",
    "user_profile",
    "logout",
]


@dataclass
class UsageEvent:
    """Single usage event."""
    user_id: int
    action_type: str
    units_charged: int
    metadata: Dict[str, Any]
    timestamp: str
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def anonymize(self) -> Dict:
        """Return anonymized version for training data."""
        return {
            "user_id_hash": self._hash_user_id(),
            "action_type": self.action_type,
            "units_charged": self.units_charged,
            "metadata": self._anonymize_metadata(),
            "timestamp": self.timestamp,
            "session_id_hash": hashlib.sha256(
                (self.session_id or "").encode()
            ).hexdigest()[:16] if self.session_id else None,
        }
    
    def _hash_user_id(self) -> str:
        """Hash user ID for privacy."""
        return hashlib.sha256(str(self.user_id).encode()).hexdigest()[:16]
    
    def _anonymize_metadata(self) -> Dict:
        """Remove PII from metadata."""
        anonymized = self.metadata.copy()
        
        # Remove sensitive fields
        sensitive_keys = [
            "email", "phone", "name", "address", "user_name",
            "customer_id", "payment_id", "api_key"
        ]
        for key in sensitive_keys:
            anonymized.pop(key, None)
        
        # Generalize location data
        if "lat" in anonymized and "lng" in anonymized:
            # Round to 2 decimals (~1km precision)
            anonymized["lat"] = round(anonymized["lat"], 2)
            anonymized["lng"] = round(anonymized["lng"], 2)
        
        return anonymized


class UsageTracker:
    """
    Central usage tracking system.
    
    Features:
    - Track all user actions with compute costs
    - Deduct units from user balance
    - Collect anonymized data for training
    - Provide usage analytics
    - SECURITY: Rate limiting, balance protection, tier limits
    """
    
    # Security: Rate limiting (requests per minute per user)
    RATE_LIMIT_WINDOW = 60  # seconds
    RATE_LIMIT_MAX_REQUESTS = 100  # max requests per window
    
    def __init__(self, db_path: str = None):
        from user_auth import get_user_database
        self.user_db = get_user_database()
        self.db = DatabaseService(db_path) if db_path else DatabaseService()
        self._rate_limit_cache = {}  # {user_id: [(timestamp, count)]}
        self._init_tables()
    
    def _init_tables(self):
        """Initialize usage tracking tables."""
        try:
            # Usage events table
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    units_charged INTEGER NOT NULL,
                    metadata_json TEXT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # User balances table
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS user_balances (
                    user_id INTEGER PRIMARY KEY,
                    units_available INTEGER DEFAULT 0,
                    units_used_lifetime INTEGER DEFAULT 0,
                    units_earned INTEGER DEFAULT 0,
                    last_topup_date TEXT,
                    last_usage_date TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Training contributions table
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS training_contributions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id_hash TEXT NOT NULL,
                    contribution_type TEXT NOT NULL,
                    data_quality_score REAL DEFAULT 1.0,
                    units_earned INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT
                )
            """)
            
            # Create indexes
            self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_events_user 
                ON usage_events(user_id, timestamp)
            """)
            self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_events_action 
                ON usage_events(action_type, timestamp)
            """)
            
            logger.info("[UsageTracker] Tables initialized")
        except Exception as e:
            logger.error(f"[UsageTracker] Table init failed: {e}")
    
    def get_action_cost(self, action_type: str) -> int:
        """Get compute cost for an action type."""
        # SECURITY: Validate action_type to prevent injection
        if not action_type or not isinstance(action_type, str):
            return 1
        # Sanitize: only allow alphanumeric and underscore
        sanitized = ''.join(c for c in action_type if c.isalnum() or c == '_')
        return COMPUTE_COSTS.get(sanitized, 1)  # Default 1 unit
    
    def is_free_action(self, action_type: str) -> bool:
        """Check if action is free."""
        return action_type in FREE_ACTIONS or self.get_action_cost(action_type) == 0
    
    def _check_rate_limit(self, user_id: int) -> Tuple[bool, str]:
        """
        SECURITY: Check if user has exceeded rate limit.
        Returns (allowed, message)
        """
        import time as time_module
        current_time = time_module.time()
        
        # Clean old entries
        if user_id in self._rate_limit_cache:
            self._rate_limit_cache[user_id] = [
                (ts, count) for ts, count in self._rate_limit_cache[user_id]
                if current_time - ts < self.RATE_LIMIT_WINDOW
            ]
        else:
            self._rate_limit_cache[user_id] = []
        
        # Count requests in window
        total_requests = sum(count for _, count in self._rate_limit_cache[user_id])
        
        if total_requests >= self.RATE_LIMIT_MAX_REQUESTS:
            return False, f"Rate limit exceeded. Max {self.RATE_LIMIT_MAX_REQUESTS} requests per minute."
        
        # Add this request
        self._rate_limit_cache[user_id].append((current_time, 1))
        return True, "OK"
    
    def check_tier_monthly_limit(self, user_id: int) -> Tuple[bool, int, int]:
        """
        Check if user has exceeded their tier's monthly unit limit.
        Returns (allowed, units_used_this_month, monthly_limit)
        """
        try:
            # Get user tier
            user = self.user_db.get_user_by_id(user_id)
            if not user:
                return False, 0, 0
            
            tier = user.tier.value if hasattr(user.tier, 'value') else str(user.tier)
            monthly_limit = TIER_MONTHLY_LIMITS.get(tier, 50)  # Default to free tier
            
            # Unlimited for enterprise/admin
            if monthly_limit == -1:
                return True, 0, -1
            
            # Get usage this month
            from datetime import datetime
            first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0).isoformat()
            
            result = self.db.execute("""
                SELECT COALESCE(SUM(units_charged), 0) as total
                FROM usage_events
                WHERE user_id = ? AND timestamp >= ?
            """, (user_id, first_of_month))
            
            units_used = result[0]["total"] if result else 0
            
            if units_used >= monthly_limit:
                return False, units_used, monthly_limit
            
            return True, units_used, monthly_limit
        except Exception as e:
            logger.error(f"[UsageTracker] Tier limit check failed: {e}")
            return True, 0, 50  # Allow on error, default to free limit
    
    def _validate_user_id(self, user_id: int) -> bool:
        """SECURITY: Validate user_id is a positive integer."""
        if not isinstance(user_id, int) or user_id <= 0:
            logger.warning(f"[SECURITY] Invalid user_id attempted: {user_id}")
            return False
        return True
    
    def _validate_units(self, units: int) -> bool:
        """SECURITY: Validate units is a reasonable positive integer."""
        if not isinstance(units, int) or units < 0 or units > 100000:
            logger.warning(f"[SECURITY] Invalid units value attempted: {units}")
            return False
        return True
    
    def get_user_balance(self, user_id: int) -> Dict[str, Any]:
        """Get user's unit balance."""
        try:
            result = self.db.execute(
                "SELECT * FROM user_balances WHERE user_id = ?",
                (user_id,)
            )
            
            if result:
                return {
                    "user_id": result[0]["user_id"],
                    "units_available": result[0]["units_available"],
                    "units_used_lifetime": result[0]["units_used_lifetime"],
                    "units_earned": result[0]["units_earned"],
                    "last_topup_date": result[0]["last_topup_date"],
                    "last_usage_date": result[0]["last_usage_date"],
                }
            else:
                # Initialize balance for new user
                self._initialize_user_balance(user_id)
                return {
                    "user_id": user_id,
                    "units_available": 0,
                    "units_used_lifetime": 0,
                    "units_earned": 0,
                    "last_topup_date": None,
                    "last_usage_date": None,
                }
        except Exception as e:
            logger.error(f"[UsageTracker] Get balance failed: {e}")
            return {"error": str(e)}
    
    def _initialize_user_balance(self, user_id: int, initial_units: int = 0):
        """Initialize balance for new user."""
        try:
            self.db.execute("""
                INSERT OR IGNORE INTO user_balances (user_id, units_available)
                VALUES (?, ?)
            """, (user_id, initial_units))
            logger.info(f"[UsageTracker] Initialized balance for user {user_id}: {initial_units} units")
        except Exception as e:
            logger.error(f"[UsageTracker] Initialize balance failed: {e}")
    
    def add_units(
        self,
        user_id: int,
        units: int,
        source: str = "topup",
        transaction_id: str = None
    ) -> bool:
        """
        Add units to user balance.
        SECURITY: Validates inputs, logs all additions with audit trail.
        """
        try:
            # SECURITY: Input validation
            if not self._validate_user_id(user_id):
                logger.warning(f"[SECURITY] Invalid user_id in add_units: {user_id}")
                return False
            
            if not self._validate_units(units):
                logger.warning(f"[SECURITY] Invalid units in add_units: {units}")
                return False
            
            # SECURITY: Validate source
            allowed_sources = [
                "topup", "admin_grant", "stripe_purchase", "razorpay_purchase",
                "cashfree_purchase", "reward:feedback", "reward:ground_truth",
                "initial_grant", "promo", "refund"
            ]
            if source not in allowed_sources and not source.startswith("reward:"):
                logger.warning(f"[SECURITY] Invalid source in add_units: {source}")
                return False
            
            # SECURITY: Max single addition limit (prevent manipulation)
            MAX_SINGLE_ADDITION = 10000
            if units > MAX_SINGLE_ADDITION:
                logger.warning(f"[SECURITY] Units exceed max single addition: {units}")
                return False
            
            balance = self.get_user_balance(user_id)
            
            if "error" in balance:
                self._initialize_user_balance(user_id, units)
                return True
            
            self.db.execute("""
                UPDATE user_balances
                SET units_available = units_available + ?,
                    last_topup_date = ?
                WHERE user_id = ?
            """, (units, datetime.now().isoformat(), user_id))
            
            # SECURITY: Audit trail - log the addition with full details
            self.user_db.log_usage(
                user_id,
                "units_added",
                f"+{units} units from {source} (txn: {transaction_id})"
            )
            
            # SECURITY: Also log to usage_events for audit
            self._log_event(user_id, "balance_topup", 0, {
                "units_added": units,
                "source": source,
                "transaction_id": transaction_id
            })
            
            logger.info(f"[UsageTracker] Added {units} units to user {user_id} (source: {source})")
            return True
        except Exception as e:
            logger.error(f"[UsageTracker] Add units failed: {e}")
            return False
    
    def deduct_units(
        self,
        user_id: int,
        units: int,
        action_type: str,
        allow_negative: bool = False
    ) -> Tuple[bool, str]:
        """
        Deduct units from user balance.
        Returns (success, message)
        """
        try:
            balance = self.get_user_balance(user_id)
            
            if "error" in balance:
                return False, "Failed to get user balance"
            
            available = balance["units_available"]
            
            if available < units and not allow_negative:
                return False, f"Insufficient units. Have: {available}, Need: {units}"
            
            self.db.execute("""
                UPDATE user_balances
                SET units_available = units_available - ?,
                    units_used_lifetime = units_used_lifetime + ?,
                    last_usage_date = ?
                WHERE user_id = ?
            """, (units, units, datetime.now().isoformat(), user_id))
            
            logger.info(f"[UsageTracker] Deducted {units} units from user {user_id} for {action_type}")
            return True, f"Charged {units} units"
        except Exception as e:
            logger.error(f"[UsageTracker] Deduct units failed: {e}")
            return False, str(e)
    
    def track_action(
        self,
        user_id: int,
        action_type: str,
        metadata: Dict[str, Any] = None,
        session_id: str = None,
        custom_cost: int = None
    ) -> Tuple[bool, str, int]:
        """
        Track a user action and charge units.
        Returns (success, message, units_charged)
        
        SECURITY: Includes rate limiting, tier limits, and input validation.
        """
        try:
            # SECURITY: Validate user_id
            if not self._validate_user_id(user_id):
                return False, "Invalid user ID", 0
            
            # SECURITY: Rate limiting check
            rate_ok, rate_msg = self._check_rate_limit(user_id)
            if not rate_ok:
                logger.warning(f"[SECURITY] Rate limit exceeded for user {user_id}")
                return False, rate_msg, 0
            
            # Get cost
            units = custom_cost if custom_cost is not None else self.get_action_cost(action_type)
            
            # Free actions - always allowed
            if self.is_free_action(action_type) or units == 0:
                self._log_event(user_id, action_type, 0, metadata, session_id)
                return True, "Free action", 0
            
            # SECURITY: Check tier-based monthly limit
            tier_ok, units_used, monthly_limit = self.check_tier_monthly_limit(user_id)
            if not tier_ok:
                return False, f"Monthly limit reached ({units_used}/{monthly_limit} units). Please upgrade your plan.", units
            
            # Check remaining units in monthly limit
            if monthly_limit > 0:  # Not unlimited
                remaining_in_tier = monthly_limit - units_used
                if remaining_in_tier < units:
                    return False, f"Would exceed monthly limit. Remaining: {remaining_in_tier}, Required: {units}", units
            
            # Deduct units
            success, message = self.deduct_units(user_id, units, action_type)
            
            if not success:
                return False, message, units
            
            # Log event
            self._log_event(user_id, action_type, units, metadata, session_id)
            
            # Collect training data (async in production)
            self._collect_training_data(user_id, action_type, metadata, session_id)
            
            return True, f"Success: {units} units charged", units
        except Exception as e:
            logger.error(f"[UsageTracker] Track action failed: {e}")
            return False, str(e), 0
    
    def _log_event(
        self,
        user_id: int,
        action_type: str,
        units_charged: int,
        metadata: Dict[str, Any] = None,
        session_id: str = None
    ):
        """Log usage event to database."""
        try:
            self.db.execute("""
                INSERT INTO usage_events 
                (user_id, action_type, units_charged, metadata_json, timestamp, session_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                action_type,
                units_charged,
                json.dumps(metadata) if metadata else None,
                datetime.now().isoformat(),
                session_id
            ))
        except Exception as e:
            logger.error(f"[UsageTracker] Log event failed: {e}")
    
    def _collect_training_data(
        self,
        user_id: int,
        action_type: str,
        metadata: Dict[str, Any] = None,
        session_id: str = None
    ):
        """Collect anonymized training data."""
        try:
            event = UsageEvent(
                user_id=user_id,
                action_type=action_type,
                units_charged=self.get_action_cost(action_type),
                metadata=metadata or {},
                timestamp=datetime.now().isoformat(),
                session_id=session_id
            )
            
            # Anonymize and save
            anonymized = event.anonymize()
            
            # Append to JSONL file
            training_file = TRAINING_DATA_DIR / "usage_training.jsonl"
            with open(training_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(anonymized, ensure_ascii=False) + "\n")
            
        except Exception as e:
            logger.error(f"[UsageTracker] Collect training data failed: {e}")
    
    def get_user_usage_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for a user."""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Total usage
            result = self.db.execute("""
                SELECT 
                    COUNT(*) as event_count,
                    SUM(units_charged) as total_units,
                    MIN(timestamp) as first_event,
                    MAX(timestamp) as last_event
                FROM usage_events
                WHERE user_id = ? AND timestamp >= ?
            """, (user_id, since_date))
            
            stats = result[0] if result else {}
            
            # Usage by action type
            action_stats = self.db.execute("""
                SELECT action_type, COUNT(*) as count, SUM(units_charged) as units
                FROM usage_events
                WHERE user_id = ? AND timestamp >= ?
                GROUP BY action_type
                ORDER BY units DESC
                LIMIT 10
            """, (user_id, since_date))
            
            # Current balance
            balance = self.get_user_balance(user_id)
            
            return {
                "period_days": days,
                "event_count": stats.get("event_count", 0),
                "total_units_used": stats.get("total_units", 0),
                "first_event": stats.get("first_event"),
                "last_event": stats.get("last_event"),
                "top_actions": [
                    {
                        "action": row["action_type"],
                        "count": row["count"],
                        "units": row["units"]
                    } for row in action_stats
                ],
                "current_balance": balance.get("units_available", 0),
                "lifetime_usage": balance.get("units_used_lifetime", 0),
                "units_earned": balance.get("units_earned", 0),
            }
        except Exception as e:
            logger.error(f"[UsageTracker] Get usage stats failed: {e}")
            return {"error": str(e)}
    
    def get_global_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get global usage statistics (admin function)."""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Total events and units
            result = self.db.execute("""
                SELECT 
                    COUNT(*) as total_events,
                    SUM(units_charged) as total_units,
                    COUNT(DISTINCT user_id) as active_users
                FROM usage_events
                WHERE timestamp >= ?
            """, (since_date,))
            
            global_stats = result[0] if result else {}
            
            # Top actions
            top_actions = self.db.execute("""
                SELECT action_type, COUNT(*) as count, SUM(units_charged) as units
                FROM usage_events
                WHERE timestamp >= ?
                GROUP BY action_type
                ORDER BY count DESC
                LIMIT 10
            """, (since_date,))
            
            # Revenue (total units charged)
            total_units = global_stats.get("total_units", 0)
            # Assuming ₹2 per unit (promo price)
            estimated_revenue = total_units * 2
            
            return {
                "period_days": days,
                "total_events": global_stats.get("total_events", 0),
                "total_units_charged": total_units,
                "active_users": global_stats.get("active_users", 0),
                "estimated_revenue_inr": estimated_revenue,
                "top_actions": [
                    {
                        "action": row["action_type"],
                        "count": row["count"],
                        "units": row["units"],
                        "avg_cost": round(row["units"] / row["count"], 2) if row["count"] > 0 else 0
                    } for row in top_actions
                ],
            }
        except Exception as e:
            logger.error(f"[UsageTracker] Get global stats failed: {e}")
            return {"error": str(e)}
    
    def award_units(
        self,
        user_id: int,
        units: int,
        reason: str,
        contribution_type: str = "feedback"
    ) -> bool:
        """Award units to user for data contribution."""
        try:
            # Add to balance
            self.add_units(user_id, units, source=f"reward:{contribution_type}")
            
            # Update earned count
            self.db.execute("""
                UPDATE user_balances
                SET units_earned = units_earned + ?
                WHERE user_id = ?
            """, (units, user_id))
            
            # Log contribution
            user_id_hash = hashlib.sha256(str(user_id).encode()).hexdigest()[:16]
            self.db.execute("""
                INSERT INTO training_contributions
                (user_id_hash, contribution_type, units_earned, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id_hash,
                contribution_type,
                units,
                datetime.now().isoformat(),
                json.dumps({"reason": reason})
            ))
            
            logger.info(f"[UsageTracker] Awarded {units} units to user {user_id} for {contribution_type}")
            return True
        except Exception as e:
            logger.error(f"[UsageTracker] Award units failed: {e}")
            return False


# Singleton instance
_usage_tracker = None

def get_usage_tracker() -> UsageTracker:
    """Get or create usage tracker singleton."""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker
