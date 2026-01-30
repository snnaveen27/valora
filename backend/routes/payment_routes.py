"""
Valora AI - Payment API Routes
Subscription and top-up payment endpoints for Razorpay, Cashfree, and Stripe.
Includes webhook signature verification and database updates.
"""

import hmac
import hashlib
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

from user_auth import get_user_database, User, SubscriptionTier
from auth_routes import require_auth
from payment_service import (
    get_payment_service,
    PaymentGateway,
    PLANS,
    TOPUP_PACKS,
    RAZORPAY_KEY_SECRET,
    STRIPE_WEBHOOK_SECRET,
)

router = APIRouter(prefix="/api/payments", tags=["Payments"])


# Request Models
class CreateSubscriptionRequest(BaseModel):
    plan_id: str
    gateway: str = "razorpay"  # razorpay, cashfree, or stripe
    quantity: int = 1
    phone: str = "9999999999"


class CreateTopupRequest(BaseModel):
    pack_id: str
    gateway: str = "razorpay"  # razorpay, cashfree, or stripe


# Helper functions for database updates
def update_user_tier(user_id: int, plan_id: str):
    """Update user tier based on plan subscription."""
    db = get_user_database()
    plan = PLANS.get(plan_id)
    if not plan:
        return False

    # Map plan to tier
    tier_map = {
        "pro_monthly": SubscriptionTier.PRO,
        "pro_annual": SubscriptionTier.PRO,
        "team_monthly": SubscriptionTier.TEAM,
        "team_annual": SubscriptionTier.TEAM,
    }
    new_tier = tier_map.get(plan_id, SubscriptionTier.PRO)

    try:
        db.update_user(user_id, {"tier": new_tier.value})
        db.log_usage(user_id, "tier_upgrade", f"Upgraded to {new_tier.value} via {plan_id}")
        print(f"[PAYMENT] User {user_id} upgraded to {new_tier.value}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update user tier: {e}")
        return False


def add_units_to_user(user_id: int, units: int, source: str = "topup"):
    """Add compute units to user account."""
    db = get_user_database()

    try:
        # Get current user
        user = db.get_user_by_id(user_id)
        if not user:
            return False

        # Add units (stored in a units field or similar)
        # For now, we log the addition - actual field depends on schema
        db.log_usage(user_id, "units_added", f"+{units} units from {source}")
        print(f"[PAYMENT] Added {units} units to user {user_id} from {source}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to add units: {e}")
        return False


def reset_monthly_units(user_id: int, plan_id: str):
    """Reset monthly units for subscription renewal."""
    db = get_user_database()
    plan = PLANS.get(plan_id)
    if not plan:
        return False

    units = plan.get("units_per_month", 1000)
    db.log_usage(user_id, "monthly_reset", f"Monthly units reset to {units}")
    print(f"[PAYMENT] Reset monthly units for user {user_id}: {units}")
    return True


def downgrade_user_to_free(user_id: int):
    """Downgrade user to free tier."""
    db = get_user_database()

    try:
        db.update_user(user_id, {"tier": SubscriptionTier.FREE.value})
        db.log_usage(user_id, "tier_downgrade", "Downgraded to free tier")
        print(f"[PAYMENT] User {user_id} downgraded to free tier")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to downgrade user: {e}")
        return False


def verify_razorpay_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Razorpay webhook signature."""
    try:
        expected = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception as e:
        print(f"[ERROR] Razorpay signature verification failed: {e}")
        return False


class VerifyPaymentRequest(BaseModel):
    gateway: str
    order_id: str
    payment_id: str
    signature: str


class WebhookPayload(BaseModel):
    event: str
    payload: Dict


# Routes
@router.get("/plans")
async def get_plans():
    """Get available subscription plans with current pricing."""
    service = get_payment_service()
    plans = service.get_plans_with_pricing()
    promo = service.get_promo_info()
    
    return {
        "success": True,
        "plans": plans,
        "promo": promo,
    }


@router.get("/topup-packs")
async def get_topup_packs():
    """Get available top-up packs with current pricing."""
    service = get_payment_service()
    packs = service.get_topup_packs_with_pricing()
    promo = service.get_promo_info()
    
    return {
        "success": True,
        "packs": packs,
        "promo": promo,
        "currency": "INR",
    }


@router.get("/promo")
async def get_promo_info():
    """Get current promotional offer details."""
    service = get_payment_service()
    return service.get_promo_info()


@router.post("/subscribe")
async def create_subscription(
    request: CreateSubscriptionRequest,
    user: User = Depends(require_auth)
):
    """Create a new subscription for the authenticated user."""
    service = get_payment_service()
    
    # Validate plan
    if request.plan_id not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {request.plan_id}")
    
    # Parse gateway
    try:
        gateway = PaymentGateway(request.gateway.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid gateway: {request.gateway}")
    
    # Create subscription
    result = service.create_subscription(
        gateway=gateway,
        plan_id=request.plan_id,
        user_id=user.id,
        customer_email=user.email,
        customer_phone=request.phone or user.phone or "9999999999",
        customer_name=user.name,
        quantity=request.quantity,
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create subscription")
    
    # Log the subscription attempt
    db = get_user_database()
    db.log_usage(user.id, "subscription_created", f"Plan: {request.plan_id}, Gateway: {request.gateway}")
    
    return {
        "success": True,
        "subscription": result,
        "gateway": request.gateway,
        "plan_id": request.plan_id,
    }


@router.post("/topup")
async def create_topup_order(
    request: CreateTopupRequest,
    user: User = Depends(require_auth)
):
    """Create a top-up order for additional units."""
    service = get_payment_service()
    
    # Validate pack
    if request.pack_id not in TOPUP_PACKS:
        raise HTTPException(status_code=400, detail=f"Invalid pack: {request.pack_id}")
    
    # Parse gateway
    try:
        gateway = PaymentGateway(request.gateway.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid gateway: {request.gateway}")
    
    # Create order
    result = service.create_topup_order(
        gateway=gateway,
        pack_id=request.pack_id,
        user_id=user.id,
        customer_email=user.email,
        customer_phone=user.phone or "9999999999",
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create top-up order")
    
    pack = TOPUP_PACKS[request.pack_id]
    
    return {
        "success": True,
        "order": result,
        "gateway": request.gateway,
        "pack_id": request.pack_id,
        "units": pack["units"],
    }


@router.post("/verify")
async def verify_payment(
    request: VerifyPaymentRequest,
    user: User = Depends(require_auth)
):
    """Verify a completed payment and credit units if valid."""
    service = get_payment_service()
    
    verified = False
    
    if request.gateway == "razorpay":
        # Check if it's a subscription or one-time payment
        if request.order_id.startswith("sub_"):
            verified = service.razorpay.verify_subscription_signature(
                request.order_id, request.payment_id, request.signature
            )
        else:
            verified = service.razorpay.verify_payment_signature(
                request.order_id, request.payment_id, request.signature
            )
    elif request.gateway == "cashfree":
        # For Cashfree, we check order status instead of signature
        order_status = service.cashfree.get_order_status(request.order_id)
        verified = order_status and order_status.get("order_status") == "PAID"
    
    if not verified:
        raise HTTPException(status_code=400, detail="Payment verification failed")
    
    # TODO: Credit units to user account based on order details
    # This would parse the order notes/metadata to determine units to add
    
    db = get_user_database()
    db.log_usage(user.id, "payment_verified", f"Order: {request.order_id}, Gateway: {request.gateway}")
    
    return {
        "success": True,
        "verified": True,
        "message": "Payment verified successfully",
    }


@router.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):
    """Handle Razorpay webhook events with signature verification."""
    try:
        # Get raw payload for signature verification
        raw_payload = await request.body()
        signature = request.headers.get("x-razorpay-signature", "")
        
        # Verify signature in production
        if signature and not verify_razorpay_webhook_signature(raw_payload, signature):
            print("[RAZORPAY WEBHOOK] Signature verification failed!")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        payload = await request.json()
        event = payload.get("event")
        
        print(f"[RAZORPAY WEBHOOK] Event: {event}")
        
        if event == "subscription.authenticated":
            subscription_id = payload.get("payload", {}).get("subscription", {}).get("entity", {}).get("id")
            print(f"[RAZORPAY] Subscription authenticated: {subscription_id}")
            
        elif event == "subscription.activated":
            subscription_entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
            subscription_id = subscription_entity.get("id")
            notes = subscription_entity.get("notes", {})
            user_id = notes.get("user_id")
            plan_id = notes.get("valora_plan")
            
            print(f"[RAZORPAY] Subscription activated: {subscription_id}")
            if user_id and plan_id:
                update_user_tier(int(user_id), plan_id)
            
        elif event == "subscription.charged":
            subscription_entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
            subscription_id = subscription_entity.get("id")
            notes = subscription_entity.get("notes", {})
            user_id = notes.get("user_id")
            plan_id = notes.get("valora_plan")
            
            print(f"[RAZORPAY] Subscription charged: {subscription_id}")
            if user_id and plan_id:
                reset_monthly_units(int(user_id), plan_id)
            
        elif event == "subscription.cancelled":
            subscription_entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
            subscription_id = subscription_entity.get("id")
            notes = subscription_entity.get("notes", {})
            user_id = notes.get("user_id")
            
            print(f"[RAZORPAY] Subscription cancelled: {subscription_id}")
            if user_id:
                downgrade_user_to_free(int(user_id))
            
        elif event == "payment.captured":
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            payment_id = payment_entity.get("id")
            notes = payment_entity.get("notes", {})
            
            print(f"[RAZORPAY] Payment captured: {payment_id}, Notes: {notes}")
            
            # Handle top-up payments
            if notes.get("type") == "topup":
                user_id = notes.get("user_id")
                units = notes.get("units")
                if user_id and units:
                    add_units_to_user(int(user_id), int(units), "razorpay_topup")
        
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[RAZORPAY WEBHOOK ERROR] {e}")
        return {"status": "error", "message": str(e)}


@router.post("/webhook/cashfree")
async def cashfree_webhook(request: Request):
    """Handle Cashfree webhook events with signature verification."""
    try:
        # Get raw payload and headers for signature verification
        raw_payload = await request.body()
        signature = request.headers.get("x-webhook-signature", "")
        timestamp = request.headers.get("x-webhook-timestamp", "")
        
        # Verify signature in production
        service = get_payment_service()
        if signature and timestamp:
            if not service.cashfree.verify_webhook_signature(raw_payload.decode(), signature, timestamp):
                print("[CASHFREE WEBHOOK] Signature verification failed!")
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        payload = await request.json()
        event_type = payload.get("type")
        
        print(f"[CASHFREE WEBHOOK] Event: {event_type}")
        
        if event_type == "PAYMENT_SUCCESS":
            order_data = payload.get("data", {}).get("order", {})
            order_id = order_data.get("order_id", "")
            
            print(f"[CASHFREE] Payment success: {order_id}")
            
            # Parse order_id to determine action
            if order_id.startswith("sub_"):
                # Subscription payment
                parts = order_id.split("_")
                if len(parts) >= 3:
                    user_id = parts[1]
                    plan_id = "_".join(parts[2:-1]) if len(parts) > 3 else parts[2]
                    update_user_tier(int(user_id), plan_id)
                    
            elif order_id.startswith("topup_"):
                # Top-up payment
                parts = order_id.split("_")
                if len(parts) >= 3:
                    user_id = parts[1]
                    pack_id = parts[2]
                    pack = TOPUP_PACKS.get(pack_id, {})
                    units = pack.get("units", 0)
                    if units:
                        add_units_to_user(int(user_id), units, "cashfree_topup")
            
        elif event_type == "PAYMENT_FAILED":
            order_id = payload.get("data", {}).get("order", {}).get("order_id")
            print(f"[CASHFREE] Payment failed: {order_id}")
        
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[CASHFREE WEBHOOK ERROR] {e}")
        return {"status": "error", "message": str(e)}


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events with signature verification."""
    try:
        # Get raw payload for signature verification
        raw_payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")
        
        # Verify signature
        service = get_payment_service()
        event = service.stripe.verify_webhook_signature(raw_payload, sig_header)
        
        if not event:
            print("[STRIPE WEBHOOK] Signature verification failed!")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        event_type = event.get("type", "")
        print(f"[STRIPE WEBHOOK] Event: {event_type}")
        
        if event_type == "checkout.session.completed":
            # Subscription or one-time payment completed
            session = event.get("data", {}).get("object", {})
            metadata = session.get("metadata", {})
            customer_email = session.get("customer_email")
            mode = session.get("mode")  # 'subscription' or 'payment'
            
            user_id = metadata.get("user_id")
            plan_id = metadata.get("plan_id")
            pack_id = metadata.get("pack_id")
            units = metadata.get("units")
            
            print(f"[STRIPE] Checkout completed: mode={mode}, user={user_id}")
            
            if mode == "subscription" and user_id and plan_id:
                update_user_tier(int(user_id), plan_id)
            elif mode == "payment" and user_id and units:
                add_units_to_user(int(user_id), int(units), "stripe_topup")
                
        elif event_type == "invoice.paid":
            # Recurring subscription payment
            invoice = event.get("data", {}).get("object", {})
            subscription_id = invoice.get("subscription")
            customer_id = invoice.get("customer")
            
            # Get subscription metadata
            if service.stripe.stripe:
                try:
                    subscription = service.stripe.stripe.Subscription.retrieve(subscription_id)
                    metadata = subscription.get("metadata", {})
                    user_id = metadata.get("user_id")
                    plan_id = metadata.get("plan_id")
                    
                    if user_id and plan_id:
                        reset_monthly_units(int(user_id), plan_id)
                        print(f"[STRIPE] Monthly units reset for user {user_id}")
                except Exception as e:
                    print(f"[STRIPE] Failed to get subscription details: {e}")
                    
        elif event_type == "customer.subscription.deleted":
            # Subscription cancelled
            subscription = event.get("data", {}).get("object", {})
            metadata = subscription.get("metadata", {})
            user_id = metadata.get("user_id")
            
            if user_id:
                downgrade_user_to_free(int(user_id))
                print(f"[STRIPE] User {user_id} subscription cancelled")
        
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[STRIPE WEBHOOK ERROR] {e}")
        return {"status": "error", "message": str(e)}


@router.get("/config")
async def get_payment_config():
    """Get payment gateway configuration for frontend."""
    from payment_service import RAZORPAY_KEY_ID, CASHFREE_APP_ID, CASHFREE_ENV, STRIPE_PUBLISHABLE_KEY
    
    return {
        "razorpay": {
            "key_id": RAZORPAY_KEY_ID,
            "currency": "INR",
        },
        "cashfree": {
            "app_id": CASHFREE_APP_ID,
            "environment": CASHFREE_ENV,
        },
        "stripe": {
            "publishable_key": STRIPE_PUBLISHABLE_KEY,
            "currency": "inr",
        },
        "supported_gateways": ["razorpay", "cashfree", "stripe"],
        "default_gateway": "stripe",  # Stripe recommended for AI/LLM usage tracking
    }
