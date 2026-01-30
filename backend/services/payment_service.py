"""
Valora AI - Payment Service
Razorpay + Cashfree + Stripe integration for subscriptions and top-ups.
Supports usage-based billing with 80% launch promo.
Stripe: Optimized for AI/LLM token usage tracking with metered billing.
"""

import os
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Environment variables for API keys (use test keys for sandbox)
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_xxxxxxxxxxxxx")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "xxxxxxxxxxxxxxxxxxxxxxxx")
CASHFREE_APP_ID = os.environ.get("CASHFREE_APP_ID", "xxxxxxxxxxxxxxxxxxxxx")
CASHFREE_SECRET_KEY = os.environ.get("CASHFREE_SECRET_KEY", "xxxxxxxxxxxxxxxxxxxxxxxx")
CASHFREE_ENV = os.environ.get("CASHFREE_ENV", "TEST")  # TEST or PROD

# Stripe API keys (use test keys for sandbox)
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_xxxxxxxxxxxxx")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "pk_test_xxxxxxxxxxxxx")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_xxxxxxxxxxxxx")
STRIPE_METER_EVENT_NAME = "valora_compute_units"  # For usage-based billing

# 80% Launch Promo - Active until March 31, 2026
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


class SubscriptionStatus(Enum):
    CREATED = "created"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    PENDING = "pending"
    HALTED = "halted"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    EXPIRED = "expired"


# Pricing Plans (with promo pricing)
PLANS = {
    "pro_monthly": {
        "name": "Pro Monthly",
        "base_price_inr": 2999,
        "promo_price_inr": 599,  # 80% off
        "units_per_month": 1000,
        "billing_period": "monthly",
        "features": ["full_search", "area_analysis", "valuation", "report_export", "explainability"],
    },
    "pro_annual": {
        "name": "Pro Annual",
        "base_price_inr": 29990,  # ~2 months free
        "promo_price_inr": 5998,  # 80% off
        "units_per_month": 1000,
        "billing_period": "yearly",
        "features": ["full_search", "area_analysis", "valuation", "report_export", "explainability"],
    },
    "team_monthly": {
        "name": "Team Monthly (per seat)",
        "base_price_inr": 4999,
        "promo_price_inr": 999,  # 80% off
        "units_per_month": 3000,
        "billing_period": "monthly",
        "features": ["all_pro_features", "shared_shortlists", "team_admin", "audit_trails"],
    },
    "team_annual": {
        "name": "Team Annual (per seat)",
        "base_price_inr": 49990,
        "promo_price_inr": 9998,  # 80% off
        "units_per_month": 3000,
        "billing_period": "yearly",
        "features": ["all_pro_features", "shared_shortlists", "team_admin", "audit_trails"],
    },
}

# Top-up packs (with promo pricing)
TOPUP_PACKS = {
    "starter": {
        "name": "Starter Pack",
        "units": 100,
        "base_price_inr": 299,
        "promo_price_inr": 59,  # 80% off
    },
    "standard": {
        "name": "Standard Pack",
        "units": 300,
        "base_price_inr": 699,
        "promo_price_inr": 139,  # 80% off
    },
    "bulk": {
        "name": "Bulk Pack",
        "units": 1000,
        "base_price_inr": 1999,
        "promo_price_inr": 399,  # 80% off
    },
}


def get_active_price(base_price: int, promo_price: int) -> tuple[int, bool]:
    """Get the active price based on promo status."""
    if LAUNCH_PROMO["active"]:
        valid_until = datetime.strptime(LAUNCH_PROMO["valid_until"], "%Y-%m-%d")
        if datetime.now() <= valid_until:
            return promo_price, True
    return base_price, False


class RazorpayService:
    """Razorpay payment gateway integration."""
    
    def __init__(self):
        self.key_id = RAZORPAY_KEY_ID
        self.key_secret = RAZORPAY_KEY_SECRET
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Razorpay client."""
        try:
            import razorpay
            self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
            print("[OK] Razorpay client initialized")
        except ImportError:
            print("[WARNING] razorpay package not installed")
        except Exception as e:
            print(f"[WARNING] Razorpay init failed: {e}")
    
    def create_plan(self, plan_id: str) -> Optional[Dict]:
        """Create a subscription plan in Razorpay."""
        if not self.client:
            return None
        
        plan_config = PLANS.get(plan_id)
        if not plan_config:
            return None
        
        price, is_promo = get_active_price(
            plan_config["base_price_inr"],
            plan_config["promo_price_inr"]
        )
        
        period = "monthly" if plan_config["billing_period"] == "monthly" else "yearly"
        interval = 1 if period == "monthly" else 12
        
        try:
            razorpay_plan = self.client.plan.create({
                "period": period,
                "interval": interval,
                "item": {
                    "name": plan_config["name"],
                    "amount": price * 100,  # Razorpay uses paise
                    "currency": "INR",
                    "description": f"Valora AI {plan_config['name']} - {plan_config['units_per_month']} units/month"
                },
                "notes": {
                    "valora_plan_id": plan_id,
                    "is_promo": str(is_promo),
                    "promo_code": LAUNCH_PROMO["promo_code"] if is_promo else "",
                }
            })
            return razorpay_plan
        except Exception as e:
            print(f"[ERROR] Razorpay create_plan failed: {e}")
            return None
    
    def create_subscription(
        self,
        plan_id: str,
        customer_email: str,
        customer_phone: str,
        customer_name: str,
        quantity: int = 1
    ) -> Optional[Dict]:
        """Create a subscription for a customer."""
        if not self.client:
            return None
        
        try:
            # First create plan if not exists (in production, plans are pre-created)
            # For sandbox, we create on-the-fly
            plan = self.create_plan(plan_id)
            if not plan:
                return None
            
            subscription = self.client.subscription.create({
                "plan_id": plan["id"],
                "customer_notify": True,
                "quantity": quantity,
                "total_count": 12,  # 12 billing cycles
                "notes": {
                    "customer_email": customer_email,
                    "customer_name": customer_name,
                    "valora_plan": plan_id,
                }
            })
            return subscription
        except Exception as e:
            print(f"[ERROR] Razorpay create_subscription failed: {e}")
            return None
    
    def create_order(self, amount_inr: int, receipt: str, notes: Dict = None) -> Optional[Dict]:
        """Create a one-time payment order (for top-ups)."""
        if not self.client:
            return None
        
        try:
            order = self.client.order.create({
                "amount": amount_inr * 100,  # paise
                "currency": "INR",
                "receipt": receipt,
                "notes": notes or {},
            })
            return order
        except Exception as e:
            print(f"[ERROR] Razorpay create_order failed: {e}")
            return None
    
    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Verify Razorpay payment signature."""
        try:
            self.client.utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            })
            return True
        except Exception:
            return False
    
    def verify_subscription_signature(self, subscription_id: str, payment_id: str, signature: str) -> bool:
        """Verify Razorpay subscription signature."""
        try:
            self.client.utility.verify_subscription_payment_signature({
                "razorpay_subscription_id": subscription_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            })
            return True
        except Exception:
            return False


class CashfreeService:
    """Cashfree payment gateway integration."""
    
    def __init__(self):
        self.app_id = CASHFREE_APP_ID
        self.secret_key = CASHFREE_SECRET_KEY
        self.env = CASHFREE_ENV
        self.base_url = "https://sandbox.cashfree.com" if self.env == "TEST" else "https://api.cashfree.com"
        self._init_client()
    
    def _init_client(self):
        """Initialize Cashfree client."""
        try:
            import cashfree_pg
            from cashfree_pg.models.create_order_request import CreateOrderRequest
            from cashfree_pg.models.customer_details import CustomerDetails
            from cashfree_pg.models.order_meta import OrderMeta
            
            cashfree_pg.Cashfree.XClientId = self.app_id
            cashfree_pg.Cashfree.XClientSecret = self.secret_key
            cashfree_pg.Cashfree.XEnvironment = cashfree_pg.Cashfree.SANDBOX if self.env == "TEST" else cashfree_pg.Cashfree.PRODUCTION
            self.client = cashfree_pg.Cashfree
            self.CreateOrderRequest = CreateOrderRequest
            self.CustomerDetails = CustomerDetails
            self.OrderMeta = OrderMeta
            print("[OK] Cashfree client initialized (v5.0.5)")
        except ImportError:
            print("[WARNING] cashfree-pg package not installed")
            self.client = None
        except Exception as e:
            print(f"[WARNING] Cashfree init failed: {e}")
            self.client = None
    
    def create_order(
        self,
        order_id: str,
        amount_inr: float,
        customer_id: str,
        customer_email: str,
        customer_phone: str,
        return_url: str = "http://localhost:3000/payment/callback"
    ) -> Optional[Dict]:
        """Create a payment order in Cashfree."""
        if not self.client:
            return None
        
        try:
            customer = self.CustomerDetails(
                customer_id=customer_id,
                customer_email=customer_email,
                customer_phone=customer_phone,
            )
            
            order_meta = self.OrderMeta(
                return_url=return_url,
            )
            
            order_request = self.CreateOrderRequest(
                order_id=order_id,
                order_amount=amount_inr,
                order_currency="INR",
                customer_details=customer,
                order_meta=order_meta,
            )
            
            response = self.client.PGCreateOrder().create_order(order_request)
            return response.data.__dict__ if response.data else None
        except Exception as e:
            print(f"[ERROR] Cashfree create_order failed: {e}")
            return None
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get order status from Cashfree."""
        if not self.client:
            return None
        
        try:
            response = self.client.PGFetchOrder().fetch_order(order_id)
            return response.data.__dict__ if response.data else None
        except Exception as e:
            print(f"[ERROR] Cashfree get_order_status failed: {e}")
            return None
    
    def verify_webhook_signature(self, payload: str, signature: str, timestamp: str) -> bool:
        """Verify Cashfree webhook signature."""
        try:
            message = timestamp + payload
            expected_signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected_signature, signature)
        except Exception:
            return False


class StripeService:
    """
    Stripe payment gateway integration.
    Optimized for AI/LLM usage-based billing with metered subscriptions.
    Uses Stripe Meters API for tracking compute units automatically.
    """
    
    def __init__(self):
        self.secret_key = STRIPE_SECRET_KEY
        self.publishable_key = STRIPE_PUBLISHABLE_KEY
        self.webhook_secret = STRIPE_WEBHOOK_SECRET
        self.meter_event_name = STRIPE_METER_EVENT_NAME
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Stripe client."""
        try:
            import stripe
            stripe.api_key = self.secret_key
            self.stripe = stripe
            print("[OK] Stripe client initialized (usage-based billing enabled)")
        except ImportError:
            print("[WARNING] stripe package not installed")
            self.stripe = None
        except Exception as e:
            print(f"[WARNING] Stripe init failed: {e}")
            self.stripe = None
    
    def create_customer(self, email: str, name: str, metadata: Dict = None) -> Optional[Dict]:
        """Create a Stripe customer."""
        if not self.stripe:
            return None
        
        try:
            customer = self.stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {},
            )
            return customer
        except Exception as e:
            print(f"[ERROR] Stripe create_customer failed: {e}")
            return None
    
    def create_checkout_session(
        self,
        price_id: str,
        customer_email: str,
        success_url: str = "http://localhost:3000/payment/success",
        cancel_url: str = "http://localhost:3000/payment/cancel",
        mode: str = "subscription",  # 'subscription' or 'payment'
        metadata: Dict = None
    ) -> Optional[Dict]:
        """Create a Stripe Checkout session."""
        if not self.stripe:
            return None
        
        try:
            session = self.stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode=mode,
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata=metadata or {},
            )
            return {"id": session.id, "url": session.url}
        except Exception as e:
            print(f"[ERROR] Stripe create_checkout_session failed: {e}")
            return None
    
    def create_payment_intent(
        self,
        amount_inr: int,
        customer_email: str,
        metadata: Dict = None
    ) -> Optional[Dict]:
        """Create a Stripe PaymentIntent for one-time payments (top-ups)."""
        if not self.stripe:
            return None
        
        try:
            intent = self.stripe.PaymentIntent.create(
                amount=amount_inr * 100,  # Stripe uses paise
                currency="inr",
                receipt_email=customer_email,
                metadata=metadata or {},
            )
            return {
                "id": intent.id,
                "client_secret": intent.client_secret,
                "status": intent.status,
            }
        except Exception as e:
            print(f"[ERROR] Stripe create_payment_intent failed: {e}")
            return None
    
    def record_usage(self, customer_id: str, units: int, timestamp: int = None) -> Optional[Dict]:
        """
        Record usage for metered billing (compute units).
        This is the key feature for AI/LLM token tracking.
        Uses Stripe Billing Meters API.
        """
        if not self.stripe:
            return None
        
        try:
            # Create a meter event for usage tracking
            event = self.stripe.billing.MeterEvent.create(
                event_name=self.meter_event_name,
                payload={
                    "value": units,
                    "stripe_customer_id": customer_id,
                },
                timestamp=timestamp or int(datetime.now().timestamp()),
            )
            return {"id": event.id, "units": units}
        except Exception as e:
            print(f"[ERROR] Stripe record_usage failed: {e}")
            # Fallback to legacy usage records if meters not available
            try:
                # Legacy method - requires subscription_item_id
                print("[INFO] Falling back to legacy usage record method")
                return None
            except:
                return None
    
    def get_customer_usage(self, customer_id: str) -> Optional[Dict]:
        """Get usage summary for a customer."""
        if not self.stripe:
            return None
        
        try:
            # Get meter event summaries
            summaries = self.stripe.billing.MeterEventSummary.list(
                customer=customer_id,
                limit=10,
            )
            return {"summaries": [s.to_dict() for s in summaries.data]}
        except Exception as e:
            print(f"[ERROR] Stripe get_customer_usage failed: {e}")
            return None
    
    def verify_webhook_signature(self, payload: bytes, sig_header: str) -> Optional[Dict]:
        """Verify Stripe webhook signature and return event."""
        if not self.stripe:
            return None
        
        try:
            event = self.stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
        except self.stripe.error.SignatureVerificationError as e:
            print(f"[ERROR] Stripe webhook signature verification failed: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Stripe webhook error: {e}")
            return None
    
    def create_price(
        self,
        unit_amount: int,
        currency: str = "inr",
        recurring_interval: str = "month",
        product_name: str = "Valora AI Pro"
    ) -> Optional[Dict]:
        """Create a Stripe Price (for subscriptions)."""
        if not self.stripe:
            return None
        
        try:
            # First create a product
            product = self.stripe.Product.create(name=product_name)
            
            # Create a price for the product
            price = self.stripe.Price.create(
                unit_amount=unit_amount * 100,  # paise
                currency=currency,
                recurring={"interval": recurring_interval},
                product=product.id,
            )
            return {"price_id": price.id, "product_id": product.id}
        except Exception as e:
            print(f"[ERROR] Stripe create_price failed: {e}")
            return None
    
    def create_metered_price(
        self,
        unit_amount: int,
        currency: str = "inr",
        product_name: str = "Valora AI Compute Units"
    ) -> Optional[Dict]:
        """Create a metered Stripe Price for usage-based billing."""
        if not self.stripe:
            return None
        
        try:
            product = self.stripe.Product.create(name=product_name)
            
            price = self.stripe.Price.create(
                unit_amount=unit_amount,  # per unit price in paise
                currency=currency,
                recurring={
                    "interval": "month",
                    "usage_type": "metered",
                },
                product=product.id,
            )
            return {"price_id": price.id, "product_id": product.id}
        except Exception as e:
            print(f"[ERROR] Stripe create_metered_price failed: {e}")
            return None


class PaymentService:
    """Unified payment service for Valora AI."""
    
    def __init__(self):
        self.razorpay = RazorpayService()
        self.cashfree = CashfreeService()
        self.stripe = StripeService()
    
    def get_plans_with_pricing(self) -> Dict:
        """Get all plans with current pricing (promo or base)."""
        plans_with_pricing = {}
        
        for plan_id, plan_config in PLANS.items():
            price, is_promo = get_active_price(
                plan_config["base_price_inr"],
                plan_config["promo_price_inr"]
            )
            plans_with_pricing[plan_id] = {
                **plan_config,
                "current_price_inr": price,
                "is_promo_price": is_promo,
                "discount_percent": LAUNCH_PROMO["discount_percent"] if is_promo else 0,
                "promo_code": LAUNCH_PROMO["promo_code"] if is_promo else None,
                "promo_valid_until": LAUNCH_PROMO["valid_until"] if is_promo else None,
            }
        
        return plans_with_pricing
    
    def get_topup_packs_with_pricing(self) -> Dict:
        """Get all top-up packs with current pricing."""
        packs_with_pricing = {}
        
        for pack_id, pack_config in TOPUP_PACKS.items():
            price, is_promo = get_active_price(
                pack_config["base_price_inr"],
                pack_config["promo_price_inr"]
            )
            packs_with_pricing[pack_id] = {
                **pack_config,
                "current_price_inr": price,
                "is_promo_price": is_promo,
                "discount_percent": LAUNCH_PROMO["discount_percent"] if is_promo else 0,
            }
        
        return packs_with_pricing
    
    def create_subscription(
        self,
        gateway: PaymentGateway,
        plan_id: str,
        user_id: int,
        customer_email: str,
        customer_phone: str,
        customer_name: str,
        quantity: int = 1
    ) -> Optional[Dict]:
        """Create a subscription using the specified gateway."""
        plan = PLANS.get(plan_id)
        if not plan:
            return None
        price, _ = get_active_price(plan["base_price_inr"], plan["promo_price_inr"])
        
        if gateway == PaymentGateway.RAZORPAY:
            return self.razorpay.create_subscription(
                plan_id, customer_email, customer_phone, customer_name, quantity
            )
        elif gateway == PaymentGateway.CASHFREE:
            order_id = f"sub_{user_id}_{plan_id}_{int(datetime.now().timestamp())}"
            return self.cashfree.create_order(
                order_id=order_id,
                amount_inr=float(price),
                customer_id=str(user_id),
                customer_email=customer_email,
                customer_phone=customer_phone,
            )
        elif gateway == PaymentGateway.STRIPE:
            # Stripe Checkout for subscriptions
            return self.stripe.create_checkout_session(
                price_id=f"price_{plan_id}",  # Pre-configured in Stripe Dashboard
                customer_email=customer_email,
                mode="subscription",
                metadata={
                    "user_id": str(user_id),
                    "plan_id": plan_id,
                    "units_per_month": plan["units_per_month"],
                }
            )
        return None
    
    def create_topup_order(
        self,
        gateway: PaymentGateway,
        pack_id: str,
        user_id: int,
        customer_email: str,
        customer_phone: str = "9999999999"
    ) -> Optional[Dict]:
        """Create a one-time top-up order."""
        pack = TOPUP_PACKS.get(pack_id)
        if not pack:
            return None
        
        price, _ = get_active_price(pack["base_price_inr"], pack["promo_price_inr"])
        order_id = f"topup_{user_id}_{pack_id}_{int(datetime.now().timestamp())}"
        
        if gateway == PaymentGateway.RAZORPAY:
            return self.razorpay.create_order(
                amount_inr=price,
                receipt=order_id,
                notes={
                    "user_id": str(user_id),
                    "pack_id": pack_id,
                    "units": pack["units"],
                    "type": "topup",
                }
            )
        elif gateway == PaymentGateway.CASHFREE:
            return self.cashfree.create_order(
                order_id=order_id,
                amount_inr=float(price),
                customer_id=str(user_id),
                customer_email=customer_email,
                customer_phone=customer_phone,
            )
        elif gateway == PaymentGateway.STRIPE:
            # Stripe PaymentIntent for one-time top-ups
            return self.stripe.create_payment_intent(
                amount_inr=price,
                customer_email=customer_email,
                metadata={
                    "user_id": str(user_id),
                    "pack_id": pack_id,
                    "units": pack["units"],
                    "type": "topup",
                }
            )
        return None
    
    def record_ai_usage(self, stripe_customer_id: str, units: int) -> Optional[Dict]:
        """
        Record AI/compute unit usage for Stripe metered billing.
        Call this after each AI action to track usage automatically.
        """
        return self.stripe.record_usage(stripe_customer_id, units)
    
    def get_promo_info(self) -> Dict:
        """Get current promo information."""
        if LAUNCH_PROMO["active"]:
            valid_until = datetime.strptime(LAUNCH_PROMO["valid_until"], "%Y-%m-%d")
            is_active = datetime.now() <= valid_until
            days_left = (valid_until - datetime.now()).days if is_active else 0
            
            return {
                "active": is_active,
                "discount_percent": LAUNCH_PROMO["discount_percent"],
                "promo_code": LAUNCH_PROMO["promo_code"],
                "valid_until": LAUNCH_PROMO["valid_until"],
                "days_left": max(0, days_left),
                "description": LAUNCH_PROMO["description"],
            }
        return {"active": False}


# Singleton instance
_payment_service = None

def get_payment_service() -> PaymentService:
    """Get singleton payment service instance."""
    global _payment_service
    if _payment_service is None:
        _payment_service = PaymentService()
    return _payment_service
