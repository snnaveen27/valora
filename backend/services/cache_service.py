"""
Cloud Cache Service - Upstash Redis Integration
Provides caching layer for API responses, geocoding, and expensive computations.
"""

import os
import json
import logging
from typing import Optional, Any, Dict
from datetime import timedelta

logger = logging.getLogger(__name__)

# Try to import Redis clients
try:
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Install with: pip install redis")

try:
    from upstash_redis import Redis as UpstashRedis
    UPSTASH_AVAILABLE = True
except ImportError:
    UPSTASH_AVAILABLE = False
    logger.info("Upstash Redis client not available (optional)")


class CacheService:
    """
    Intelligent cache service that works with:
    1. Upstash Redis (cloud, primary)
    2. Local Redis (fallback)
    3. In-memory dict (fallback if Redis unavailable)
    """
    
    def __init__(self):
        self.client = None
        self.use_memory_cache = False
        self.memory_cache: Dict[str, Any] = {}
        
        # Try Upstash REST API first (no special client needed, just HTTP)
        upstash_url = os.getenv('UPSTASH_REDIS_REST_URL')
        upstash_token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
        
        if upstash_url and upstash_token:
            try:
                # Use standard Redis client with Upstash URL
                redis_url = os.getenv('REDIS_URL')
                if redis_url and REDIS_AVAILABLE:
                    self.client = Redis.from_url(
                        redis_url,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5
                    )
                    self.client.ping()  # Test connection
                    logger.info("✅ Connected to Upstash Redis (cloud)")
                    return
            except Exception as e:
                logger.warning(f"Upstash connection failed: {str(e)}")
        
        # Try local Redis
        if REDIS_AVAILABLE:
            try:
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', 6379))
                redis_password = os.getenv('REDIS_PASSWORD', None)
                
                self.client = Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                self.client.ping()
                logger.info(f"✅ Connected to local Redis ({redis_host}:{redis_port})")
                return
            except Exception as e:
                logger.warning(f"Local Redis connection failed: {str(e)}")
        
        # Fallback to in-memory cache
        logger.warning("⚠️  Using in-memory cache (Redis unavailable)")
        self.use_memory_cache = True
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        try:
            if self.use_memory_cache:
                return self.memory_cache.get(key)
            
            if self.client:
                val = self.client.get(key)
                if val:
                    try:
                        return json.loads(val)
                    except:
                        return val
            return None
        except Exception as e:
            logger.error(f"Cache get error for key '{key}': {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """
        Set cached value with TTL
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default: 1 hour)
        """
        try:
            if self.use_memory_cache:
                self.memory_cache[key] = value
                # In-memory cache doesn't support TTL, would need background cleanup
                return True
            
            if self.client:
                # Serialize value
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value)
                else:
                    value_str = str(value)
                
                self.client.setex(key, ttl, value_str)
                return True
            return False
        except Exception as e:
            logger.error(f"Cache set error for key '{key}': {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete cached value"""
        try:
            if self.use_memory_cache:
                self.memory_cache.pop(key, None)
                return True
            
            if self.client:
                self.client.delete(key)
                return True
            return False
        except Exception as e:
            logger.error(f"Cache delete error for key '{key}': {str(e)}")
            return False
    
    def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern (e.g., 'geocode:*')"""
        try:
            if self.use_memory_cache:
                # Simple pattern matching for in-memory
                keys_to_delete = [k for k in self.memory_cache.keys() if pattern.replace('*', '') in k]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                return len(keys_to_delete)
            
            if self.client:
                keys = self.client.keys(pattern)
                if keys:
                    self.client.delete(*keys)
                    return len(keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error: {str(e)}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            if self.use_memory_cache:
                return {
                    'type': 'memory',
                    'keys': len(self.memory_cache),
                    'hit_rate': 'N/A',
                    'memory_usage': 'N/A'
                }
            
            if self.client:
                info = self.client.info()
                return {
                    'type': 'redis',
                    'keys': info.get('db0', {}).get('keys', 0) if 'db0' in info else 0,
                    'hit_rate': info.get('keyspace_hits', 0) / max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1), 1),
                    'memory_usage': info.get('used_memory_human', 'N/A'),
                    'connected_clients': info.get('connected_clients', 0)
                }
            
            return {'type': 'none', 'status': 'unavailable'}
        except Exception as e:
            logger.error(f"Cache stats error: {str(e)}")
            return {'type': 'error', 'error': str(e)}


# Global cache instance
cache = CacheService()


# Convenience functions
def cache_get(key: str) -> Optional[Any]:
    """Get cached value"""
    return cache.get(key)


def cache_set(key: str, value: Any, ttl: int = 3600):
    """Set cached value with TTL"""
    return cache.set(key, value, ttl)


def cache_delete(key: str) -> bool:
    """Delete cached value"""
    return cache.delete(key)


def cache_clear_pattern(pattern: str):
    """Clear all keys matching pattern"""
    return cache.clear_pattern(pattern)


def cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return cache.get_stats()


# Cache decorators for common patterns
def cached_property_search(ttl: int = 3600):
    """Decorator to cache property search results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key from function args
            cache_key = f"property_search:{json.dumps(kwargs, sort_keys=True)}"
            
            # Try cache first
            cached = cache_get(cache_key)
            if cached is not None:
                return cached
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


def cached_geocode(ttl: int = 604800):  # 7 days
    """Decorator to cache geocoding results"""
    def decorator(func):
        def wrapper(address: str, *args, **kwargs):
            cache_key = f"geocode:{address.lower()}"
            
            cached = cache_get(cache_key)
            if cached is not None:
                return cached
            
            result = func(address, *args, **kwargs)
            cache_set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
