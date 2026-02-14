"""
Rate Limiting Middleware for Valora API

This middleware provides IP-based burst/DDoS protection only.
Per-user credit-based rate limiting is handled by CreditsRateLimiter
in ai/credits_rate_limiter.py (checked inside chat endpoints).
"""
import logging
import time
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict
import os

logger = logging.getLogger("valora.rate_limit")

# Paths exempt from rate limiting
_EXEMPT_PATHS = frozenset(["/health", "/", "/api/debug"])


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    IP-based burst protection middleware.

    Prevents a single IP from flooding the API.  This does NOT handle
    per-user credit accounting — that lives in CreditsRateLimiter.

    Defaults: 200 requests/hour per IP (configurable via RATE_LIMIT_BURST env).
    """

    def __init__(self, app):
        super().__init__(app)
        self.requests: Dict[str, list] = {}  # IP -> [timestamp, ...]
        self.window = 3600  # 1 hour sliding window
        self.burst_limit = int(os.getenv("RATE_LIMIT_BURST", "200"))
        self._cleanup_counter = 0

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        # Extract client IP (respect proxy headers)
        client_ip = request.headers.get("X-Forwarded-For", request.client.host)
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()

        now = time.time()

        # Evict stale entries for this IP
        if client_ip in self.requests:
            self.requests[client_ip] = [
                ts for ts in self.requests[client_ip]
                if now - ts < self.window
            ]

        request_count = len(self.requests.get(client_ip, []))

        if request_count >= self.burst_limit:
            retry_after = self._retry_after(client_ip, now)
            logger.warning(f"Rate limit hit: {client_ip} ({request_count}/{self.burst_limit})")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too many requests",
                    "limit": self.burst_limit,
                    "window": "1 hour",
                    "retry_after": retry_after,
                },
            )

        # Record request
        self.requests.setdefault(client_ip, []).append(now)

        # Periodic global cleanup (every 100 requests)
        self._cleanup_counter += 1
        if self._cleanup_counter >= 100:
            self._cleanup_counter = 0
            self._global_cleanup(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.burst_limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.burst_limit - request_count - 1))
        response.headers["X-RateLimit-Reset"] = str(int(now + self.window))
        return response

    def _retry_after(self, client_ip: str, now: float) -> int:
        entries = self.requests.get(client_ip, [])
        if not entries:
            return 0
        return max(0, int(self.window - (now - min(entries))))

    def _global_cleanup(self, now: float):
        """Remove all entries older than the window across all IPs."""
        stale = [ip for ip, ts_list in self.requests.items() if not ts_list or now - max(ts_list) > self.window]
        for ip in stale:
            del self.requests[ip]
