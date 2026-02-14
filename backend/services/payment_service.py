"""
Valora AI - Dummy Payment Service
Minimal stub for development without actual payment processing.
"""

from enum import Enum
from typing import Optional, Dict, Any

# Dummy constants
RAZORPAY_KEY_ID = "dummy_key_id"
RAZORPAY_KEY_SECRET = "dummy_secret"
CASHFREE_APP_ID = "dummy_app_id"
CASHFREE_SECRET_KEY = "dummy_secret"
CASHFREE_ENV = "TEST"
STRIPE_SECRET_KEY = "dummy_secret"
STRIPE_PUBLISHABLE_KEY = "dummy_key"
STRIPE_WEBHOOK_SECRET = "dummy_webhook_secret"

LAUNCH_PROMO = {
    "active": True,
    "discount_percent": 80,
    "promo_code": "LAUNCH80",
    "valid_until": "2026-03-31",
    "description": "80% off for early adopters!",
}

class PaymentGateway(Enum):
    RAZORPAY = "razorpay"
    CASHFREE = "cashfree"
    STRIPE = "stripe"

PLANS = {
    "pro_monthly": {
        "name": "Pro Monthly",
        "base_price_inr": 2999,
        "promo_price_inr": 599,
        "units_per_month": 1000,
        "billing_period": "monthly",
        "features": ["full_search", "area_analysis", "valuation", "report_export", "explainability"],
    },
    "pro_annual": {
        "name": "Pro Annual",
        "base_price_inr": 29990,
        "promo_price_inr": 5998,
        "units_per_month": 1000,
        "billing_period": "yearly",
        "features": ["full_search", "area_analysis", "valuation", "report_export", "explainability"],
    },
    "team_monthly": {
        "name": "Team Monthly (per seat)",
        "base_price_inr": 4999,
        "promo_price_inr": 999,
        "units_per_month": 3000,
        "billing_period": "monthly",
        "features": ["all_pro_features", "shared_shortlists", "team_admin", "audit_trails"],
    },
    "team_annual": {
        "name": "Team Annual (per seat)",
        "base_price_inr": 49990,
        "promo_price_inr": 9998,
        "units_per_month": 3000,
        "billing_period": "yearly",
        "features": ["all_pro_features", "shared_shortlists", "team_admin", "audit_trails"],
    },
}

TOPUP_PACKS = {
    "starter": {
        "name": "Starter Pack",
        "units": 100,
        "base_price_inr": 299,
        "promo_price_inr": 59,
    },
    "standard": {
        "name": "Standard Pack",
        "units": 300,
        "base_price_inr": 699,
        "promo_price_inr": 139,
    },
    "bulk": {
        "name": "Bulk Pack",
        "units": 1000,
        "base_price_inr": 1999,
        "promo_price_inr": 399,
    },
}

class DummyPaymentService:
    """Dummy payment service that logs but doesn't process payments."""
    
    def __init__(self):
        print("[DUMMY] Payment service initialized (no actual payments)")
    
    def get_plans_with_pricing(self) -> Dict:
        """Return plans with dummy pricing."""
        return {
            plan_id: {
                **plan_config,
                "current_price_inr": plan_config["promo_price_inr"],
                "is_promo_price": True,
                "discount_percent": 80,
                "promo_code": "LAUNCH80",
            }
            for plan_id, plan_config in PLANS.items()
        }
    
    def get_topup_packs_with_pricing(self) -> Dict:
        """Return top-up packs with dummy pricing."""
        return {
            pack_id: {
                **pack_config,
                "current_price_inr": pack_config["promo_price_inr"],
                "is_promo_price": True,
                "discount_percent": 80,
            }
            for pack_id, pack_config in TOPUP_PACKS.items()
        }
    
    def get_promo_info(self) -> Dict:
        """Return promo info."""
        return {
            "active": True,
            "discount_percent": 80,
            "promo_code": "LAUNCH80",
            "valid_until": "2026-03-31",
            "days_left": 30,
            "description": "80% off for early adopters!",
        }
    
    def create_subscription(self, gateway: PaymentGateway, plan_id: str, user_id: int, 
                           customer_email: str, customer_phone: str, customer_name: str, 
                           quantity: int = 1) -> Optional[Dict]:
        """Dummy subscription creation."""
        print(f"[DUMMY] Create subscription: {plan_id} for user {user_id} via {gateway.value}")
        return {
            "id": f"dummy_sub_{user_id}_{plan_id}",
            "status": "created",
            "gateway": gateway.value,
            "plan_id": plan_id,
        }
    
    def create_topup_order(self, gateway: PaymentGateway, pack_id: str, user_id: int,
                          customer_email: str, customer_phone: str = "9999999999") -> Optional[Dict]:
        """Dummy top-up order creation."""
        print(f"[DUMMY] Create top-up: {pack_id} for user {user_id} via {gateway.value}")
        pack = TOPUP_PACKS.get(pack_id, {})
        return {
            "id": f"dummy_topup_{user_id}_{pack_id}",
            "amount": pack.get("promo_price_inr", 0),
            "units": pack.get("units", 0),
            "gateway": gateway.value,
        }

# Singleton instance
_payment_service = None

def get_payment_service() -> DummyPaymentService:
    """Get singleton dummy payment service instance."""
    global _payment_service
    if _payment_service is None:
        _payment_service = DummyPaymentService()
    return _payment_service
