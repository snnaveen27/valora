"""
Payment Routes - Stripe integration endpoints.
Supports subscriptions and credit top-ups.
"""

import os
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("valora.payments")

router = APIRouter(prefix="/api/payments", tags=["payments"])

# Stripe configuration
STRIPE_API_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# Price IDs (create in Stripe Dashboard)
PRO_MONTHLY_PRICE_ID = os.environ.get("STRIPE_PRO_PRICE_ID", "price_pro_monthly")


class CreateCheckoutRequest(BaseModel):
    user_id: str
    tier: str = "pro"


class TopUpRequest(BaseModel):
    user_id: str
    package: str  # starter, standard, power


class CreditBalanceRequest(BaseModel):
    user_id: str


@router.post("/create-checkout-session")
async def create_checkout_session(request: CreateCheckoutRequest):
    """
    Create a Stripe Checkout session for Pro subscription.
    """
    if not STRIPE_API_KEY:
        # Demo mode - just update tier directly
        from ai.credits_rate_limiter import CreditsRateLimiter
        limiter = CreditsRateLimiter()
        limiter.update_tier(request.user_id, request.tier)
        
        return {
            "url": f"{FRONTEND_URL}/payment/success?demo=true",
            "session_id": "demo_session",
            "demo_mode": True
        }
    
    try:
        import stripe
        stripe.api_key = STRIPE_API_KEY
        
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{
                "price": PRO_MONTHLY_PRICE_ID,
                "quantity": 1
            }],
            metadata={
                "user_id": request.user_id,
                "tier": request.tier
            },
            success_url=f"{FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/payment/cancel"
        )
        
        logger.info(f"Created checkout session for user {request.user_id}")
        
        return {
            "url": session.url,
            "session_id": session.id
        }
        
    except Exception as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/top-up")
async def purchase_top_up(request: TopUpRequest):
    """Purchase credit top-up package."""
    from ai.credits_rate_limiter import CreditsRateLimiter
    
    limiter = CreditsRateLimiter()
    
    # Validate package
    packages = limiter.TOP_UP_PACKAGES
    if request.package not in packages:
        raise HTTPException(status_code=400, detail=f"Invalid package. Choose from: {list(packages.keys())}")
    
    pkg = packages[request.package]
    
    if not STRIPE_API_KEY:
        # Demo mode - just add credits
        result = limiter.add_top_up(request.user_id, request.package)
        return {
            "success": True,
            "demo_mode": True,
            **result
        }
    
    try:
        import stripe
        stripe.api_key = STRIPE_API_KEY
        
        # Create one-time payment
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Valora Credits - {request.package.title()}",
                        "description": f"{pkg['credits'] + pkg['bonus']} credits"
                    },
                    "unit_amount": pkg['price'] * 100
                },
                "quantity": 1
            }],
            metadata={
                "user_id": request.user_id,
                "type": "top_up",
                "package": request.package
            },
            success_url=f"{FRONTEND_URL}/payment/success",
            cancel_url=f"{FRONTEND_URL}/payment/cancel"
        )
        
        return {
            "url": session.url,
            "session_id": session.id
        }
        
    except Exception as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks."""
    if not STRIPE_API_KEY or not STRIPE_WEBHOOK_SECRET:
        return {"status": "demo_mode"}
    
    import stripe
    stripe.api_key = STRIPE_API_KEY
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle events
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await _handle_checkout_complete(session)
    
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        await _handle_subscription_cancelled(subscription)
    
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        await _handle_payment_failed(invoice)
    
    return {"status": "success"}


async def _handle_checkout_complete(session: dict):
    """Handle successful checkout."""
    metadata = session.get("metadata", {})
    user_id = metadata.get("user_id")
    checkout_type = metadata.get("type", "subscription")
    
    logger.info(f"Checkout complete for user {user_id}, type {checkout_type}")
    
    from ai.credits_rate_limiter import CreditsRateLimiter
    limiter = CreditsRateLimiter()
    
    if checkout_type == "top_up":
        package = metadata.get("package")
        if package:
            limiter.add_top_up(user_id, package)
    else:
        tier = metadata.get("tier", "pro")
        limiter.update_tier(user_id, tier)


async def _handle_subscription_cancelled(subscription: dict):
    """Handle subscription cancellation."""
    customer_id = subscription.get("customer")
    logger.info(f"Subscription cancelled for customer {customer_id}")


async def _handle_payment_failed(invoice: dict):
    """Handle failed payment."""
    customer_id = invoice.get("customer")
    logger.warning(f"Payment failed for customer {customer_id}")


@router.get("/balance/{user_id}")
async def get_credit_balance(user_id: str):
    """Get user's credit balance."""
    from ai.credits_rate_limiter import CreditsRateLimiter
    
    limiter = CreditsRateLimiter()
    balance = limiter.get_balance(user_id)
    
    return balance


# Also expose at /credits/balance for frontend compatibility (without /api prefix since router has /api/payments prefix)
@router.get("/credits/balance")
async def get_credit_balance_query(user_id: str):
    """Get user's credit balance (query param version for frontend)."""
    from ai.credits_rate_limiter import CreditsRateLimiter
    
    limiter = CreditsRateLimiter()
    balance = limiter.get_balance(user_id)
    
    return balance


@router.post("/credits/top-up")
async def top_up_credits_query(request: TopUpRequest):
    """Top-up credits (query param version for frontend)."""
    return await purchase_top_up(request)


@router.get("/history/{user_id}")
async def get_inference_history(user_id: str, limit: int = 50):
    """Get inference history for a user."""
    from ai.credits_rate_limiter import CreditsRateLimiter
    
    limiter = CreditsRateLimiter()
    history = limiter.get_inference_history(user_id, limit)
    
    return {
        "user_id": user_id,
        "history": history,
        "count": len(history)
    }


@router.post("/admin/add-credits")
async def admin_add_credits(user_id: str, credits: int, admin_key: str):
    """Admin endpoint to add credits to a user."""
    # Simple admin key check
    expected_key = os.environ.get("VALORA_ADMIN_KEY", "valora_admin_2025")
    if admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    from ai.credits_rate_limiter import CreditsRateLimiter
    limiter = CreditsRateLimiter()
    
    # Ensure user exists
    limiter.get_or_create_user(user_id)
    
    # Add credits as top-up
    conn = limiter._get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_credits
        SET top_up_credits = top_up_credits + ?, updated_at = ?
        WHERE user_id = ?
    """, (credits, __import__('time').time(), user_id))
    conn.commit()
    
    balance = limiter.get_balance(user_id)
    
    return {
        "success": True,
        "credits_added": credits,
        "new_balance": balance
    }


@router.post("/admin/monthly-hook")
async def trigger_monthly_hook_credits(admin_key: str):
    """Trigger monthly 50 credits for all users."""
    expected_key = os.environ.get("VALORA_ADMIN_KEY", "valora_admin_2025")
    if admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    from ai.credits_rate_limiter import CreditsRateLimiter
    limiter = CreditsRateLimiter()
    
    result = limiter.give_monthly_hook_credits()
    
    return result


@router.get("/packages")
async def get_top_up_packages():
    """Get available top-up packages."""
    from ai.credits_rate_limiter import CreditsRateLimiter
    limiter = CreditsRateLimiter()
    
    return {
        "packages": [
            {
                "id": k,
                "price": v["price"],
                "credits": v["credits"],
                "bonus": v["bonus"],
                "total": v["credits"] + v["bonus"]
            }
            for k, v in limiter.TOP_UP_PACKAGES.items()
        ]
    }
