"""
Valora AI - Usage Tracking Middleware
Automatically tracks and charges for API usage.
"""

import time
import logging
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Endpoint to action type mapping
ENDPOINT_ACTION_MAP = {
    # Chat endpoints
    "/api/chat": "chat_multiagent",
    "/api/chat/simulation": "chat_simulation",
    
    # Analysis endpoints
    "/api/location/analyze": "location_analysis",
    "/api/viewport/analyze": "viewport_analysis",
    "/api/area/analyze": "area_analysis",
    "/api/building/analyze": "building_analysis",
    "/api/compare/properties": "comparison",
    "/api/valuation": "valuation",
    
    # Simulations
    "/api/storyboard/generate": "storyboard_generation",
    "/api/simulation/scenario": "scenario_analysis",
    
    # City Intelligence
    "/api/city-intelligence/locality": "locality_brain",
    "/api/city-intelligence/growth": "growth_prediction",
    "/api/city-intelligence/risk": "risk_assessment",
    
    # Reports
    "/api/report/export": "report_export",
    "/api/report/pdf": "pdf_generation",
    
    # Search
    "/api/property/search": "property_search",
    "/api/poi/search": "poi_search",
    
    # Data loading (mostly free)
    "/api/tiles": "tileset_load",
    "/api/tileset": "tileset_load",
    "/api/tiles/viewport": "viewport_load",
}

# Endpoints that should NOT be charged
FREE_ENDPOINTS = [
    "/health",
    "/api/health",
    "/api/debug",
    "/api/admin",
    "/api/auth",
    "/api/payments",
    "/docs",
    "/redoc",
    "/openapi.json",
]


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track API usage and charge units.
    
    Features:
    - Automatic action detection from endpoint
    - Unit charging before request processing
    - Response headers with charge info
    - Skip charging for free/admin endpoints
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._tracker = None
    
    def _get_tracker(self):
        """Lazy load tracker to avoid circular imports."""
        if self._tracker is None:
            from usage_tracker import get_usage_tracker
            self._tracker = get_usage_tracker()
        return self._tracker
    
    def _should_skip_tracking(self, path: str) -> bool:
        """Check if endpoint should skip tracking."""
        # Skip free endpoints
        for free_path in FREE_ENDPOINTS:
            if path.startswith(free_path):
                return True
        
        # Skip static files
        if any(ext in path for ext in ['.js', '.css', '.png', '.jpg', '.svg', '.ico']):
            return True
        
        return False
    
    def _get_action_type(self, path: str, method: str) -> Optional[str]:
        """Determine action type from endpoint path."""
        # Exact match
        if path in ENDPOINT_ACTION_MAP:
            return ENDPOINT_ACTION_MAP[path]
        
        # Prefix match
        for endpoint, action in ENDPOINT_ACTION_MAP.items():
            if path.startswith(endpoint):
                return action
        
        # Default based on method
        if method in ["POST", "PUT", "PATCH"]:
            return "api_write"
        elif method == "GET":
            return "api_read"
        
        return None
    
    def _extract_metadata(self, request: Request) -> dict:
        """Extract metadata from request for tracking."""
        metadata = {
            "path": request.url.path,
            "method": request.method,
            "client_host": request.client.host if request.client else None,
        }
        
        # Add query params (sanitized)
        if request.query_params:
            metadata["params"] = dict(request.query_params)
        
        return metadata
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with usage tracking."""
        path = request.url.path
        
        # Skip tracking for certain endpoints
        if self._should_skip_tracking(path):
            return await call_next(request)
        
        # Get user from request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        
        # Skip if no authenticated user
        if not user:
            return await call_next(request)
        
        # Determine action type
        action_type = self._get_action_type(path, request.method)
        
        if not action_type:
            return await call_next(request)
        
        # Extract metadata
        metadata = self._extract_metadata(request)
        
        # Track usage
        tracker = self._get_tracker()
        session_id = request.headers.get("x-session-id")
        
        success, message, units_charged = tracker.track_action(
            user_id=user.id,
            action_type=action_type,
            metadata=metadata,
            session_id=session_id
        )
        
        # If insufficient units or limit exceeded, return 402 with upgrade info
        # Per BUSINESS_MODEL_AND_PLAN.md Section 6.4:
        # - Map navigation remains available (read-only)
        # - AI queries blocked
        # - Reports/simulations blocked
        # - Upgrade/Top-up modal shown with promo pricing
        if not success:
            from fastapi.responses import JSONResponse
            
            # Get user's current balance and tier info
            tracker = self._get_tracker()
            balance = tracker.get_user_balance(user.id)
            tier_ok, units_used, monthly_limit = tracker.check_tier_monthly_limit(user.id)
            
            # Determine error type
            if "Rate limit" in message:
                error_code = "rate_limit_exceeded"
            elif "Monthly limit" in message or "exceed monthly" in message:
                error_code = "monthly_limit_exceeded"
            elif "Insufficient" in message:
                error_code = "insufficient_units"
            else:
                error_code = "usage_error"
            
            return JSONResponse(
                status_code=402,  # Payment Required
                content={
                    "success": False,
                    "error": error_code,
                    "message": message,
                    "units_required": units_charged,
                    "current_balance": balance.get("units_available", 0),
                    "monthly_usage": {
                        "used": units_used,
                        "limit": monthly_limit,
                        "remaining": max(0, monthly_limit - units_used) if monthly_limit > 0 else -1
                    },
                    # Upgrade options with promo pricing (per business model)
                    "upgrade_options": {
                        "topup_packs": [
                            {"name": "Starter", "units": 100, "price_inr": 59, "regular_price": 299},
                            {"name": "Standard", "units": 300, "price_inr": 139, "regular_price": 699},
                            {"name": "Bulk", "units": 1000, "price_inr": 399, "regular_price": 1999},
                        ],
                        "subscription_upgrade": {
                            "pro": {"units": 1000, "price_inr": 599, "regular_price": 2999},
                            "team": {"units": 3000, "price_inr": 999, "regular_price": 4999},
                        },
                        "promo_active": True,
                        "promo_discount": "80%",
                        "promo_valid_until": "2026-03-31",
                    },
                    "allowed_actions": [
                        "map_navigation",
                        "tileset_load",
                        "viewport_load",
                        "user_profile",
                        "logout"
                    ],
                    "blocked_actions": [
                        "chat_query",
                        "area_analysis",
                        "valuation",
                        "simulation",
                        "report_export"
                    ]
                },
                headers={
                    "X-Units-Required": str(units_charged),
                    "X-Current-Balance": str(balance.get("units_available", 0)),
                    "X-Error-Code": error_code,
                }
            )
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Add usage info to response headers
        response.headers["X-Units-Charged"] = str(units_charged)
        response.headers["X-Action-Type"] = action_type
        response.headers["X-Processing-Time-Ms"] = str(int(duration_ms))
        
        # Log usage to observability
        try:
            from observability import get_metrics
            metrics = get_metrics()
            metrics.record_request(path, duration_ms, response.status_code)
        except:
            pass
        
        return response


def get_usage_middleware() -> UsageTrackingMiddleware:
    """Get usage tracking middleware instance."""
    return UsageTrackingMiddleware
