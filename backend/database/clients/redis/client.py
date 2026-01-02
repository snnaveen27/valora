"""
Redis cache client (optional).

If redis-py is not installed or REDIS_URL is not configured, this falls back
to a safe in-memory cache so imports do not break.
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

try:
    import redis  # type: ignore
    _REDIS_AVAILABLE = True
except Exception:
    redis = None
    _REDIS_AVAILABLE = False


class SafeRedisCache:
    def __init__(self, url: Optional[str] = None, namespace: str = "valora"):
        self.namespace = namespace
        self.url = url or os.getenv("REDIS_URL")
        self._client = None
        self._memory: dict[str, tuple[Any, Optional[float]]] = {}

        if _REDIS_AVAILABLE and self.url:
            try:
                self._client = redis.Redis.from_url(self.url)
                # quick ping to verify connectivity
                self._client.ping()
            except Exception:
                self._client = None

    def _make_key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    def get(self, key: str) -> Any:
        namespaced = self._make_key(key)
        if self._client is not None:
            try:
                val = self._client.get(namespaced)
                return None if val is None else val
            except Exception:
                pass
        # memory fallback with ttl handling
        item = self._memory.get(namespaced)
        if not item:
            return None
        value, expires_at = item
        if expires_at is not None and time.time() > expires_at:
            self._memory.pop(namespaced, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        namespaced = self._make_key(key)
        if self._client is not None:
            try:
                if ttl_seconds is not None:
                    return bool(self._client.setex(namespaced, ttl_seconds, value))
                return bool(self._client.set(namespaced, value))
            except Exception:
                pass
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        self._memory[namespaced] = (value, expires_at)
        return True

    def delete(self, key: str) -> None:
        namespaced = self._make_key(key)
        if self._client is not None:
            try:
                self._client.delete(namespaced)
                return
            except Exception:
                pass
        self._memory.pop(namespaced, None)

    def ping(self) -> bool:
        if self._client is not None:
            try:
                self._client.ping()
                return True
            except Exception:
                return False
        return True
