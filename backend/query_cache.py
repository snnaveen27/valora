"""
Query Response Cache
Caches frequent queries to reduce Pinecone API calls and improve response time
"""

import hashlib
import json
import time
from typing import Any, Optional, Dict
from collections import OrderedDict
from dataclasses import dataclass, asdict


@dataclass
class CachedResponse:
    """Cached query response."""
    query_hash: str
    response: Any
    timestamp: float
    hit_count: int = 0
    
    def is_expired(self, ttl_seconds: int = 300) -> bool:
        """Check if cache entry is expired (default 5 min TTL)."""
        return (time.time() - self.timestamp) > ttl_seconds
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'query_hash': self.query_hash,
            'response': self.response,
            'timestamp': self.timestamp,
            'hit_count': self.hit_count,
            'age_seconds': int(time.time() - self.timestamp)
        }


class QueryCache:
    """LRU cache for query responses with TTL."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of cached entries
            ttl_seconds: Time-to-live for cache entries (default 5 minutes)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, CachedResponse] = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def _hash_query(self, query: str, **kwargs) -> str:
        """Create a hash key from query and parameters."""
        # Combine query with sorted kwargs
        cache_key = {
            'query': query,
            **{k: v for k, v in sorted(kwargs.items()) if v is not None}
        }
        key_str = json.dumps(cache_key, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, query: str, **kwargs) -> Optional[Any]:
        """Get cached response if available and not expired."""
        query_hash = self._hash_query(query, **kwargs)
        
        if query_hash in self.cache:
            cached = self.cache[query_hash]
            
            # Check if expired
            if cached.is_expired(self.ttl_seconds):
                self.cache.pop(query_hash)
                self.misses += 1
                return None
            
            # Move to end (LRU)
            self.cache.move_to_end(query_hash)
            cached.hit_count += 1
            self.hits += 1
            return cached.response
        
        self.misses += 1
        return None
    
    def set(self, query: str, response: Any, **kwargs) -> None:
        """Cache a response."""
        query_hash = self._hash_query(query, **kwargs)
        
        # Create cache entry
        cached = CachedResponse(
            query_hash=query_hash,
            response=response,
            timestamp=time.time(),
            hit_count=0
        )
        
        # Add to cache
        self.cache[query_hash] = cached
        self.cache.move_to_end(query_hash)
        
        # Evict oldest if over max size
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
    
    def invalidate(self, query: str = None, **kwargs) -> None:
        """Invalidate cache entry or all entries."""
        if query is None:
            # Clear all
            self.cache.clear()
        else:
            query_hash = self._hash_query(query, **kwargs)
            self.cache.pop(query_hash, None)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        # Get top queries by hit count
        top_queries = sorted(
            self.cache.values(),
            key=lambda x: x.hit_count,
            reverse=True
        )[:5]
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate_pct': round(hit_rate, 2),
            'ttl_seconds': self.ttl_seconds,
            'top_queries': [c.to_dict() for c in top_queries]
        }
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        expired_keys = [
            key for key, cached in self.cache.items()
            if cached.is_expired(self.ttl_seconds)
        ]
        
        for key in expired_keys:
            self.cache.pop(key)
        
        return len(expired_keys)


# Global cache instances
_rag_cache: Optional[QueryCache] = None
_property_cache: Optional[QueryCache] = None


def get_rag_cache() -> QueryCache:
    """Get or create RAG query cache."""
    global _rag_cache
    if _rag_cache is None:
        _rag_cache = QueryCache(max_size=500, ttl_seconds=300)  # 5 min TTL
    return _rag_cache


def get_property_cache() -> QueryCache:
    """Get or create property search cache."""
    global _property_cache
    if _property_cache is None:
        _property_cache = QueryCache(max_size=1000, ttl_seconds=180)  # 3 min TTL
    return _property_cache
