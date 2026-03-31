"""Developer Dashboard Routes - Project analytics, demand density, pricing intelligence."""

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/developer-dashboard", tags=["developer-dashboard"])


@router.get("/metrics")
async def get_developer_metrics(user_id: str = Query(...)):
    """Get developer dashboard metrics. Returns demo data for now."""
    return {
        "projects": {
            "active": 3,
            "planned": 2,
            "completed": 7,
            "totalUnits": 1240,
        },
        "market_data": {
            "avgPricePerSqft": 6850,
            "priceChange": 4.2,
            "demandIndex": 78,
            "supplyIndex": 62,
            "absorptionRate": 68,
            "inventoryMonths": 8.5,
        },
        "micro_markets": [
            {"name": "Whitefield", "demand": 85, "avgPrice": 7200, "supply": 70, "trend": "up"},
            {"name": "Sarjapur Road", "demand": 78, "avgPrice": 6500, "supply": 65, "trend": "up"},
            {"name": "Electronic City", "demand": 72, "avgPrice": 5800, "supply": 80, "trend": "stable"},
            {"name": "Hebbal", "demand": 80, "avgPrice": 8100, "supply": 45, "trend": "up"},
            {"name": "Kanakapura Road", "demand": 65, "avgPrice": 5200, "supply": 90, "trend": "down"},
        ],
        "competitors": [
            {"name": "Prestige Group", "projects": 4, "avgPrice": 8500, "units": 320},
            {"name": "Brigade Group", "projects": 3, "avgPrice": 7800, "units": 280},
            {"name": "Sobha Limited", "projects": 2, "avgPrice": 9200, "units": 180},
        ],
        "weekly_leads": [
            {"day": "Mon", "inquiries": 12, "siteVisits": 4},
            {"day": "Tue", "inquiries": 18, "siteVisits": 6},
            {"day": "Wed", "inquiries": 15, "siteVisits": 5},
            {"day": "Thu", "inquiries": 22, "siteVisits": 8},
            {"day": "Fri", "inquiries": 20, "siteVisits": 7},
            {"day": "Sat", "inquiries": 28, "siteVisits": 12},
            {"day": "Sun", "inquiries": 10, "siteVisits": 3},
        ],
    }
