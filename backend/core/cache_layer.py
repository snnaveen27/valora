"""
Intelligent Caching Layer for Valora AI

Production-grade caching with:
1. Query result caching (swarm analysis, chat responses)
2. Embedding caching (frequent search terms)
3. Partial result caching (area stats, market trends)
4. TTL-based expiration with data freshness awareness
"""

import hashlib
import json
import pickle
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from collections import OrderedDict
from functools import wraps


@dataclass
class CacheEntry:
    """A single cache entry with metadata."""
    key: str
    value: Any
    created_at: float
    ttl_seconds: float
    hit_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    source: str = "unknown"
    size_bytes: int = 0
    
    @property
    def is_expired(self) -> bool:
        return time.time() > (self.created_at + self.ttl_seconds)
    
    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at
    
    def touch(self):
        """Update access time and hit count."""
        self.last_accessed = time.time()
        self.hit_count += 1


class LRUCache:
    """
    Thread-safe LRU cache with TTL support.
    
    Features:
    - Automatic eviction of least recently used items
    - TTL-based expiration
    - Memory-aware sizing
    - Statistics tracking
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: float = 100.0,
        default_ttl: float = 300.0
    ):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._current_memory = 0
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache, returns None if not found or expired."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            if entry.is_expired:
                self._remove(key)
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            self._hits += 1
            
            return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        source: str = "unknown"
    ):
        """Set value in cache with optional TTL."""
        ttl = ttl or self.default_ttl
        
        # Estimate size
        try:
            size_bytes = len(pickle.dumps(value))
        except:
            size_bytes = 1024  # Default estimate
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl_seconds=ttl,
            source=source,
            size_bytes=size_bytes
        )
        
        with self._lock:
            # Remove old entry if exists
            if key in self._cache:
                self._remove(key)
            
            # Evict if needed
            while (
                len(self._cache) >= self.max_size or
                self._current_memory + size_bytes > self.max_memory_bytes
            ):
                if not self._cache:
                    break
                self._evict_oldest()
            
            self._cache[key] = entry
            self._current_memory += size_bytes
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        with self._lock:
            if key in self._cache:
                self._remove(key)
                return True
            return False
    
    def clear(self):
        """Clear all entries."""
        with self._lock:
            self._cache.clear()
            self._current_memory = 0
    
    def _remove(self, key: str):
        """Remove entry and update memory tracking."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._current_memory -= entry.size_bytes
    
    def _evict_oldest(self):
        """Evict the least recently used entry."""
        if self._cache:
            key = next(iter(self._cache))
            self._remove(key)
            self._evictions += 1
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries, returns count removed."""
        removed = 0
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items() if v.is_expired
            ]
            for key in expired_keys:
                self._remove(key)
                removed += 1
        return removed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "memory_mb": self._current_memory / (1024 * 1024),
                "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "evictions": self._evictions,
            }


class EmbeddingCache:
    """
    Specialized cache for embeddings with semantic similarity lookup.
    
    Features:
    - Cache embeddings for frequent search terms
    - Approximate matching for similar queries
    - Batch retrieval support
    """
    
    def __init__(self, max_size: int = 10000, ttl_seconds: float = 3600.0):
        self._cache = LRUCache(
            max_size=max_size,
            max_memory_mb=200.0,  # Embeddings can be large
            default_ttl=ttl_seconds
        )
        self._query_hashes: Dict[str, str] = {}  # normalized query -> cache key
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for better cache hits."""
        # Lowercase, strip, collapse whitespace
        normalized = " ".join(query.lower().strip().split())
        return normalized
    
    def _make_key(self, query: str) -> str:
        """Create cache key from query."""
        normalized = self._normalize_query(query)
        return f"emb:{hashlib.md5(normalized.encode()).hexdigest()}"
    
    def get(self, query: str) -> Optional[List[float]]:
        """Get cached embedding for query."""
        key = self._make_key(query)
        return self._cache.get(key)
    
    def set(self, query: str, embedding: List[float]):
        """Cache embedding for query."""
        key = self._make_key(query)
        self._cache.set(key, embedding, source="embedding")
    
    def get_batch(self, queries: List[str]) -> Tuple[Dict[str, List[float]], List[str]]:
        """
        Get cached embeddings for multiple queries.
        Returns (cached_dict, uncached_queries).
        """
        cached = {}
        uncached = []
        
        for query in queries:
            embedding = self.get(query)
            if embedding is not None:
                cached[query] = embedding
            else:
                uncached.append(query)
        
        return cached, uncached
    
    def set_batch(self, query_embeddings: Dict[str, List[float]]):
        """Cache multiple embeddings at once."""
        for query, embedding in query_embeddings.items():
            self.set(query, embedding)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics."""
        stats = self._cache.get_stats()
        stats["type"] = "embedding"
        return stats


class QueryResultCache:
    """
    Cache for query results (swarm analysis, chat responses).
    
    Features:
    - Context-aware caching (different context = different result)
    - Result freshness tracking
    - Partial invalidation on data changes
    """
    
    # TTL by query type (seconds)
    TTL_CONFIG = {
        "swarm_analysis": 600,      # 10 minutes
        "chat_response": 300,       # 5 minutes
        "property_search": 300,     # 5 minutes
        "area_analysis": 1800,      # 30 minutes (changes less often)
        "market_trends": 3600,      # 1 hour (aggregated data)
        "valuation": 1800,          # 30 minutes
        "infrastructure": 3600,     # 1 hour (static data)
        "default": 300,
    }
    
    def __init__(self, max_size: int = 500, max_memory_mb: float = 100.0):
        self._cache = LRUCache(
            max_size=max_size,
            max_memory_mb=max_memory_mb,
            default_ttl=300.0
        )
        self._data_version = 0  # Increment on data changes
    
    def _make_key(self, query: str, context: Dict[str, Any], query_type: str) -> str:
        """Create cache key from query + context."""
        # Include relevant context fields
        context_parts = []
        for key in sorted(['selectedLocation', 'selectedBuilding', 'viewport']):
            if key in context:
                val = context[key]
                if isinstance(val, dict):
                    # Just use identifying fields
                    context_parts.append(f"{key}:{val.get('id', val.get('name', ''))}")
                else:
                    context_parts.append(f"{key}:{val}")
        
        context_str = "|".join(context_parts)
        combined = f"{query_type}:{query.lower().strip()}:{context_str}:v{self._data_version}"
        return f"qr:{hashlib.md5(combined.encode()).hexdigest()}"
    
    def get(
        self,
        query: str,
        context: Dict[str, Any],
        query_type: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """Get cached query result."""
        key = self._make_key(query, context, query_type)
        return self._cache.get(key)
    
    def set(
        self,
        query: str,
        context: Dict[str, Any],
        result: Dict[str, Any],
        query_type: str = "default"
    ):
        """Cache query result."""
        key = self._make_key(query, context, query_type)
        ttl = self.TTL_CONFIG.get(query_type, self.TTL_CONFIG["default"])
        self._cache.set(key, result, ttl=ttl, source=query_type)
    
    def invalidate_on_data_change(self):
        """Invalidate cache when underlying data changes."""
        self._data_version += 1
        # Old keys won't match new version
    
    def get_stats(self) -> Dict[str, Any]:
        """Get query result cache statistics."""
        stats = self._cache.get_stats()
        stats["type"] = "query_result"
        stats["data_version"] = self._data_version
        return stats


class PartialResultCache:
    """
    Cache for expensive partial computations.
    
    Features:
    - Long TTL for semi-static data
    - Namespace-based organization
    - Dependency tracking for invalidation
    """
    
    # TTL by namespace (seconds)
    NAMESPACE_TTL = {
        "area_stats": 3600,         # 1 hour
        "market_trends": 7200,      # 2 hours
        "infrastructure_counts": 7200,  # 2 hours
        "poi_aggregates": 3600,     # 1 hour
        "property_counts": 1800,    # 30 minutes
        "valuation_models": 86400,  # 24 hours (model params change rarely)
    }
    
    def __init__(self, max_size: int = 2000, max_memory_mb: float = 150.0):
        self._cache = LRUCache(
            max_size=max_size,
            max_memory_mb=max_memory_mb,
            default_ttl=3600.0
        )
        self._dependencies: Dict[str, set] = {}  # key -> dependent keys
    
    def _make_key(self, namespace: str, identifier: str) -> str:
        """Create cache key."""
        return f"pr:{namespace}:{identifier}"
    
    def get(self, namespace: str, identifier: str) -> Optional[Any]:
        """Get cached partial result."""
        key = self._make_key(namespace, identifier)
        return self._cache.get(key)
    
    def set(
        self,
        namespace: str,
        identifier: str,
        value: Any,
        depends_on: Optional[List[str]] = None
    ):
        """Cache partial result with optional dependencies."""
        key = self._make_key(namespace, identifier)
        ttl = self.NAMESPACE_TTL.get(namespace, 3600)
        self._cache.set(key, value, ttl=ttl, source=namespace)
        
        # Track dependencies
        if depends_on:
            for dep in depends_on:
                if dep not in self._dependencies:
                    self._dependencies[dep] = set()
                self._dependencies[dep].add(key)
    
    def invalidate_namespace(self, namespace: str):
        """Invalidate all entries in a namespace."""
        with self._cache._lock:
            keys_to_remove = [
                k for k in self._cache._cache.keys()
                if k.startswith(f"pr:{namespace}:")
            ]
            for key in keys_to_remove:
                self._cache.delete(key)
    
    def invalidate_dependents(self, key: str):
        """Invalidate all entries that depend on a key."""
        if key in self._dependencies:
            for dep_key in self._dependencies[key]:
                self._cache.delete(dep_key)
            del self._dependencies[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get partial result cache statistics."""
        stats = self._cache.get_stats()
        stats["type"] = "partial_result"
        stats["dependency_count"] = len(self._dependencies)
        return stats


class ValoraCache:
    """
    Unified caching interface for Valora AI.
    
    Combines all cache types with a single API.
    """
    
    def __init__(self):
        self.embeddings = EmbeddingCache(max_size=10000, ttl_seconds=3600)
        self.query_results = QueryResultCache(max_size=500, max_memory_mb=100)
        self.partial_results = PartialResultCache(max_size=2000, max_memory_mb=150)
        
        # Background cleanup
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def _maybe_cleanup(self):
        """Run periodic cleanup if needed."""
        if time.time() - self._last_cleanup > self._cleanup_interval:
            self.cleanup()
            self._last_cleanup = time.time()
    
    def cleanup(self):
        """Clean up expired entries from all caches."""
        self.embeddings._cache.cleanup_expired()
        self.query_results._cache.cleanup_expired()
        self.partial_results._cache.cleanup_expired()
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get combined statistics from all caches."""
        return {
            "embeddings": self.embeddings.get_stats(),
            "query_results": self.query_results.get_stats(),
            "partial_results": self.partial_results.get_stats(),
            "last_cleanup": datetime.fromtimestamp(self._last_cleanup).isoformat(),
        }
    
    def clear_all(self):
        """Clear all caches."""
        self.embeddings._cache.clear()
        self.query_results._cache.clear()
        self.partial_results._cache.clear()


# Singleton instance
_valora_cache: Optional[ValoraCache] = None
_cache_lock = threading.Lock()


def get_cache() -> ValoraCache:
    """Get or create the global cache instance."""
    global _valora_cache
    if _valora_cache is None:
        with _cache_lock:
            if _valora_cache is None:
                _valora_cache = ValoraCache()
    return _valora_cache


def cached_embedding(func: Callable) -> Callable:
    """Decorator to cache embedding results."""
    @wraps(func)
    def wrapper(text: str, *args, **kwargs):
        cache = get_cache()
        
        # Check cache
        cached = cache.embeddings.get(text)
        if cached is not None:
            return cached
        
        # Compute and cache
        result = func(text, *args, **kwargs)
        if result is not None:
            cache.embeddings.set(text, result)
        
        return result
    return wrapper


def cached_query(query_type: str = "default"):
    """Decorator to cache query results."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(query: str, context: Dict[str, Any] = None, *args, **kwargs):
            cache = get_cache()
            context = context or {}
            
            # Check cache
            cached = cache.query_results.get(query, context, query_type)
            if cached is not None:
                cached["_cached"] = True
                return cached
            
            # Compute and cache
            result = func(query, context, *args, **kwargs)
            if result is not None:
                cache.query_results.set(query, context, result, query_type)
            
            return result
        return wrapper
    return decorator


def cached_partial(namespace: str):
    """Decorator to cache partial results."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(identifier: str, *args, **kwargs):
            cache = get_cache()
            
            # Check cache
            cached = cache.partial_results.get(namespace, identifier)
            if cached is not None:
                return cached
            
            # Compute and cache
            result = func(identifier, *args, **kwargs)
            if result is not None:
                cache.partial_results.set(namespace, identifier, result)
            
            return result
        return wrapper
    return decorator
