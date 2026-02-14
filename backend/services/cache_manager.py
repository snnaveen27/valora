"""
Redis Caching Layer for Performance Optimization
Caches frequent queries and LLM responses
"""
import json
import pickle
import hashlib
from typing import Optional, Any, Callable
from functools import wraps
import time

# Try to import redis, fallback to in-memory if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("[CACHE] Redis not available, using in-memory cache")

class CacheManager:
    """
    Multi-layer caching system
    - L1: In-memory (fastest, per-process)
    - L2: Redis (shared across processes)
    """
    
    def __init__(self, host='localhost', port=6379, db=0):
        self.memory_cache = {}  # L1 cache
        self.redis_client = None
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    decode_responses=False,
                    socket_connect_timeout=2
                )
                self.redis_client.ping()
                print("[CACHE] Redis connected successfully")
            except Exception as e:
                print(f"[CACHE] Redis connection failed: {e}, using in-memory only")
                self.redis_client = None
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments"""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        # Try L1 (memory) first
        if key in self.memory_cache:
            value, expiry = self.memory_cache[key]
            if time.time() < expiry:
                return value
            else:
                del self.memory_cache[key]
        
        # Try L2 (Redis)
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    value = pickle.loads(data)
                    # Also store in L1 for faster access
                    return value
            except Exception as e:
                print(f"[CACHE] Redis get error: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600, l1_ttl: int = 300):
        """Set value in cache with TTL"""
        # Set in L1 (memory) with shorter TTL
        self.memory_cache[key] = (value, time.time() + l1_ttl)
        
        # Set in L2 (Redis)
        if self.redis_client:
            try:
                serialized = pickle.dumps(value)
                self.redis_client.setex(key, ttl, serialized)
            except Exception as e:
                print(f"[CACHE] Redis set error: {e}")
    
    def delete(self, key: str):
        """Delete from all cache layers"""
        if key in self.memory_cache:
            del self.memory_cache[key]
        
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                print(f"[CACHE] Redis delete error: {e}")
    
    def clear_pattern(self, pattern: str):
        """Clear cache by pattern"""
        # Clear from memory
        keys_to_delete = [k for k in self.memory_cache.keys() if pattern in k]
        for k in keys_to_delete:
            del self.memory_cache[k]
        
        # Clear from Redis
        if self.redis_client:
            try:
                for key in self.redis_client.scan_iter(match=f"*{pattern}*"):
                    self.redis_client.delete(key)
            except Exception as e:
                print(f"[CACHE] Redis clear error: {e}")

# Global cache instance
cache_manager = CacheManager()

def cache_result(ttl: int = 3600, prefix: str = ""):
    """
    Decorator to cache function results
    
    Usage:
        @cache_result(ttl=3600, prefix="intent")
        async def classify_intent(query: str):
            return await llm.classify(query)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_manager._generate_key(
                prefix or func.__name__,
                *args,
                **kwargs
            )
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                print(f"[CACHE] Hit for {func.__name__}")
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            cache_manager.set(cache_key, result, ttl)
            print(f"[CACHE] Stored {func.__name__}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = cache_manager._generate_key(
                prefix or func.__name__,
                *args,
                **kwargs
            )
            
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return async_wrapper if func.__code__.co_flags & 0x80 else sync_wrapper
    return decorator

# Specific cache configurations
class CacheConfig:
    """Cache TTL configurations"""
    
    INTENT_CLASSIFICATION = 1800  # 30 minutes
    AREA_DATA = 86400  # 24 hours
    BUILDING_DATA = 3600  # 1 hour
    MARKET_STATS = 1800  # 30 minutes
    LLM_RESPONSE = 600  # 10 minutes
    USER_SESSION = 3600  # 1 hour
    GEOCODING = 86400  # 24 hours
    
    @staticmethod
    def clear_area_cache(locality: str):
        """Clear cache for specific area"""
        cache_manager.clear_pattern(locality.lower())
