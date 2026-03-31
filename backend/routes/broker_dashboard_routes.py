"""Broker Dashboard Routes - Lead pipeline and activity metrics."""

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api/broker-dashboard", tags=["broker-dashboard"])


@router.get("/metrics")
async def get_broker_metrics(user_id: str = Query(...)):
    """Get broker dashboard metrics. Returns demo data for now."""
    return {
        "pipeline": {
            "stages": [
                {"id": "new", "label": "New Leads", "count": 12, "color": "from-blue-500 to-cyan-500", "icon": "🆕"},
                {"id": "contacted", "label": "Contacted", "count": 8, "color": "from-amber-500 to-orange-500", "icon": "📞"},
                {"id": "negotiating", "label": "Negotiating", "count": 5, "color": "from-purple-500 to-pink-500", "icon": "🤝"},
                {"id": "closed", "label": "Closed", "count": 3, "color": "from-emerald-500 to-green-500", "icon": "✅"},
            ],
            "total": 28,
            "conversionRate": 10.7,
        },
        "recent_leads": [
            {"id": 1, "name": "Rahul Sharma", "locality": "Whitefield", "budget": "₹85L", "status": "new"},
            {"id": 2, "name": "Priya Nair", "locality": "HSR Layout", "budget": "₹1.2Cr", "status": "contacted"},
            {"id": 3, "name": "Amit Patel", "locality": "Sarjapur Road", "budget": "₹65L", "status": "negotiating"},
            {"id": 4, "name": "Sneha Reddy", "locality": "Electronic City", "budget": "₹55L", "status": "new"},
            {"id": 5, "name": "Vikram Singh", "locality": "Koramangala", "budget": "₹2.1Cr", "status": "negotiating"},
        ],
        "alert_performance": {"totalAlerts": 15, "engaged": 9, "converted": 3, "engagementRate": 60},
        "weekly_activity": [
            {"day": "Mon", "queries": 8, "reports": 2},
            {"day": "Tue", "queries": 12, "reports": 3},
            {"day": "Wed", "queries": 6, "reports": 1},
            {"day": "Thu", "queries": 15, "reports": 4},
            {"day": "Fri", "queries": 10, "reports": 2},
            {"day": "Sat", "queries": 4, "reports": 1},
            {"day": "Sun", "queries": 2, "reports": 0},
        ],
        "credits": {"used": 342, "limit": 1000},
    }
