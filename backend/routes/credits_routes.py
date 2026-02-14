"""
Valora AI - Credits & Demo Payment Routes
Self-contained endpoints for credits management, usage tracking, and demo payments.
Wired directly to CreditsRateLimiter (SQLite-backed).

Endpoints:
  GET  /api/credits/{user_id}              - Get balance & usage stats
  POST /api/credits/purchase               - Demo purchase (instant credits)
  POST /api/credits/upgrade                - Demo tier upgrade
  GET  /api/credits/plans                  - Available plans & pricing
  GET  /api/credits/topup-packs            - Available top-up packs
  GET  /api/credits/{user_id}/history      - Payment & usage history
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai.credits_rate_limiter import get_rate_limiter

logger = logging.getLogger("valora.credits")

router = APIRouter(prefix="/api/credits", tags=["credits"])


# ---------------------------------------------------------------------------
# Plans & pricing (same as payment_service.py but self-contained)
# ---------------------------------------------------------------------------
PLANS = {
    "free": {
        "name": "Free",
        "price_inr": 0,
        "monthly_credits": 500,
        "local_daily": 50,
        "cloud_daily": 10,
        "features": ["basic_search", "area_overview", "5_queries_day"],
    },
    "pro_monthly": {
        "name": "Pro Monthly",
        "price_inr": 599,
        "original_price_inr": 2999,
        "monthly_credits": 5000,
        "local_daily": 500,
        "cloud_daily": 100,
        "features": ["full_search", "area_analysis", "valuation", "report_export", "explainability"],
    },
    "pro_annual": {
        "name": "Pro Annual",
        "price_inr": 5998,
        "original_price_inr": 29990,
        "monthly_credits": 5000,
        "local_daily": 500,
        "cloud_daily": 100,
        "billing_period": "yearly",
        "features": ["full_search", "area_analysis", "valuation", "report_export", "explainability"],
    },
    "team_monthly": {
        "name": "Team Monthly",
        "price_inr": 999,
        "original_price_inr": 4999,
        "monthly_credits": 20000,
        "local_daily": 2000,
        "cloud_daily": 500,
        "features": ["all_pro", "shared_shortlists", "team_admin", "audit_trails"],
    },
}

TOPUP_PACKS = {
    "starter": {"name": "Starter", "units": 100, "price_inr": 59, "original_price_inr": 299},
    "standard": {"name": "Standard", "units": 300, "price_inr": 139, "original_price_inr": 699},
    "bulk": {"name": "Bulk", "units": 1000, "price_inr": 399, "original_price_inr": 1999},
}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class PurchaseRequest(BaseModel):
    user_id: str
    pack_id: str  # starter, standard, bulk
    payment_method: str = "demo"  # demo, razorpay, stripe (only demo works for MVP)


class UpgradeRequest(BaseModel):
    user_id: str
    plan_id: str  # pro_monthly, pro_annual, team_monthly
    payment_method: str = "demo"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/plans")
async def get_plans():
    """Get available subscription plans with pricing."""
    return {
        "success": True,
        "plans": PLANS,
        "promo": {
            "active": True,
            "discount_percent": 80,
            "code": "LAUNCH80",
            "valid_until": "2026-03-31",
            "description": "80% off for early adopters!",
        },
    }


@router.get("/topup-packs")
async def get_topup_packs():
    """Get available top-up credit packs."""
    return {
        "success": True,
        "packs": TOPUP_PACKS,
        "currency": "INR",
    }


@router.get("/{user_id}")
async def get_credits(user_id: str):
    """Get user's current credit balance and usage stats."""
    rl = get_rate_limiter()
    user = rl.get_or_create_user(user_id)
    stats = rl.get_usage_stats(user_id, days=30)

    return {
        "success": True,
        "user_id": user_id,
        "tier": user["tier"],
        "credits": {
            "total": user["total_credits"],
            "used": user["used_credits"],
            "remaining": user["remaining_credits"],
            "reset_at": user["reset_at"],
        },
        "usage": {
            "total_queries_30d": stats["total_queries"],
            "by_action": stats["usage_by_action"],
            "daily": stats["daily_usage"][:7],  # last 7 days
        },
        "tier_limits": get_rate_limiter().TIER_CREDITS.get(user["tier"], {}),
    }


@router.post("/purchase")
async def purchase_credits(request: PurchaseRequest):
    """
    Demo credit purchase. Instantly adds credits to account.
    In production, this would integrate with Razorpay/Stripe.
    """
    pack = TOPUP_PACKS.get(request.pack_id)
    if not pack:
        raise HTTPException(status_code=400, detail=f"Invalid pack: {request.pack_id}")

    rl = get_rate_limiter()

    # Ensure user exists
    rl.get_or_create_user(request.user_id)

    # Process demo payment
    result = rl.process_dummy_payment(
        user_id=request.user_id,
        amount_inr=pack["price_inr"],
        credits_to_add=pack["units"],
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail="Payment processing failed")

    # Get updated balance
    user = rl.get_or_create_user(request.user_id)

    logger.info(f"[PURCHASE] User {request.user_id} bought {pack['name']} (+{pack['units']} credits)")

    return {
        "success": True,
        "transaction_id": result["transaction_id"],
        "pack": pack["name"],
        "credits_added": pack["units"],
        "amount_charged_inr": pack["price_inr"],
        "payment_method": request.payment_method,
        "new_balance": {
            "total": user["total_credits"],
            "remaining": user["remaining_credits"],
        },
        "message": f"Added {pack['units']} credits to your account!",
    }


@router.post("/upgrade")
async def upgrade_tier(request: UpgradeRequest):
    """
    Demo tier upgrade. Instantly upgrades user tier and resets credits.
    In production, this would create a Razorpay/Stripe subscription.
    """
    plan = PLANS.get(request.plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {request.plan_id}")

    if request.plan_id == "free":
        raise HTTPException(status_code=400, detail="Cannot 'upgrade' to free tier. Use /downgrade instead.")

    rl = get_rate_limiter()

    # Map plan to tier
    tier_map = {
        "pro_monthly": "pro",
        "pro_annual": "pro",
        "team_monthly": "team",
        "team_annual": "team",
    }
    new_tier = tier_map.get(request.plan_id, "pro")

    # Update tier in credits DB
    import sqlite3, time
    conn = sqlite3.connect(rl.db_path)
    cursor = conn.cursor()

    # Ensure user exists
    rl.get_or_create_user(request.user_id)

    # Update tier and reset credits
    tier_config = rl.TIER_CREDITS.get(new_tier, rl.TIER_CREDITS["free"])
    cursor.execute("""
        UPDATE user_credits
        SET tier = ?, total_credits = ?, used_credits = 0, monthly_reset_at = ?, updated_at = ?
        WHERE user_id = ?
    """, (new_tier, tier_config["monthly_credits"], time.time(), time.time(), request.user_id))
    conn.commit()

    # Log the upgrade as a payment
    cursor.execute("""
        INSERT INTO payment_history (user_id, timestamp, amount_inr, credits_added, payment_method, transaction_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        request.user_id, time.time(), plan["price_inr"],
        tier_config["monthly_credits"], "demo_upgrade",
        f"UPGRADE_{request.user_id}_{new_tier}_{int(time.time())}",
        "completed",
    ))
    conn.commit()
    conn.close()

    logger.info(f"[UPGRADE] User {request.user_id} upgraded to {new_tier} ({request.plan_id})")

    return {
        "success": True,
        "user_id": request.user_id,
        "new_tier": new_tier,
        "plan": plan["name"],
        "monthly_credits": tier_config["monthly_credits"],
        "price_inr": plan["price_inr"],
        "features": plan["features"],
        "message": f"Upgraded to {plan['name']}! You now have {tier_config['monthly_credits']} credits/month.",
    }


@router.post("/downgrade/{user_id}")
async def downgrade_to_free(user_id: str):
    """Downgrade user back to free tier."""
    rl = get_rate_limiter()

    import sqlite3, time
    conn = sqlite3.connect(rl.db_path)
    cursor = conn.cursor()

    free_config = rl.TIER_CREDITS["free"]
    cursor.execute("""
        UPDATE user_credits
        SET tier = 'free', total_credits = ?, used_credits = 0, monthly_reset_at = ?, updated_at = ?
        WHERE user_id = ?
    """, (free_config["monthly_credits"], time.time(), time.time(), user_id))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "user_id": user_id,
        "new_tier": "free",
        "monthly_credits": free_config["monthly_credits"],
        "message": "Downgraded to Free tier.",
    }


@router.get("/{user_id}/history")
async def get_payment_history(user_id: str):
    """Get payment and usage history for a user."""
    import sqlite3
    rl = get_rate_limiter()

    conn = sqlite3.connect(rl.db_path)
    cursor = conn.cursor()

    # Payment history
    cursor.execute("""
        SELECT timestamp, amount_inr, credits_added, payment_method, transaction_id, status
        FROM payment_history
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT 20
    """, (user_id,))

    payments = [
        {
            "timestamp": row[0],
            "amount_inr": row[1],
            "credits_added": row[2],
            "method": row[3],
            "transaction_id": row[4],
            "status": row[5],
        }
        for row in cursor.fetchall()
    ]

    conn.close()

    # Usage stats
    stats = rl.get_usage_stats(user_id, days=30)

    return {
        "success": True,
        "user_id": user_id,
        "payments": payments,
        "usage_stats": stats,
    }
