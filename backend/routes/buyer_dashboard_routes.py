"""Buyer Dashboard Routes - Property tracking, ROI analysis, saved searches, alerts."""

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/buyer-dashboard", tags=["buyer-dashboard"])


@router.get("/metrics")
async def get_buyer_metrics(user_id: str = Query(...)):
    """Get buyer dashboard metrics. Returns demo data for now."""
    return {
        "watchlist": {
            "total": 8,
            "priceDropped": 2,
            "newMatches": 3,
            "avgPriceChange": -1.2,
        },
        "properties": [
            {"id": 1, "name": "3BHK in Whitefield", "locality": "Whitefield", "price": "₹1.2Cr", "priceChange": -2, "status": "watching"},
            {"id": 2, "name": "2BHK in HSR Layout", "locality": "HSR Layout", "price": "₹85L", "priceChange": 0, "status": "visited"},
            {"id": 3, "name": "4BHK in Koramangala", "locality": "Koramangala", "price": "₹2.5Cr", "priceChange": -5, "status": "watching"},
            {"id": 4, "name": "2BHK in Electronic City", "locality": "Electronic City", "price": "₹55L", "priceChange": 3, "status": "shortlisted"},
        ],
        "saved_searches": [
            {"id": 1, "name": "3BHK under ₹1.5Cr", "locality": "Whitefield, Sarjapur", "results": 12, "newResults": 3},
            {"id": 2, "name": "2BHK near Metro", "locality": "HSR, Koramangala", "results": 8, "newResults": 1},
            {"id": 3, "name": "Villa under ₹3Cr", "locality": "North Bangalore", "results": 5, "newResults": 2},
        ],
        "price_alerts": [
            {"id": 1, "locality": "Whitefield", "threshold": "₹7,000/sqft", "current": "₹7,200/sqft", "triggered": False},
            {"id": 2, "locality": "Electronic City", "threshold": "₹5,500/sqft", "current": "₹5,400/sqft", "triggered": True},
            {"id": 3, "locality": "Sarjapur Road", "threshold": "₹6,000/sqft", "current": "₹6,500/sqft", "triggered": False},
        ],
        "insights": {
            "avgRentalYield": 3.2,
            "priceAppreciation": 4.5,
            "topLocality": "Whitefield",
            "riskLevel": "Moderate",
        },
        "activity": [
            {"day": "Mon", "views": 5, "saves": 1},
            {"day": "Tue", "views": 8, "saves": 2},
            {"day": "Wed", "views": 3, "saves": 0},
            {"day": "Thu", "views": 12, "saves": 3},
            {"day": "Fri", "views": 7, "saves": 1},
            {"day": "Sat", "views": 15, "saves": 4},
            {"day": "Sun", "views": 6, "saves": 2},
        ],
    }
