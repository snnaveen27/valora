"""
Health Check Endpoint for Valora
Monitors all critical services and returns system status
"""

import sqlite3
import httpx
import asyncio
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from config import config
from monitoring.runtime_validation import validate_runtime

# Import circuit breakers
try:
    from core.circuit_breaker import get_all_circuit_status
    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False

# Import cache
try:
    from cache.tiered_cache import get_cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

# Import connection pool
try:
    from database.connection_pool import get_valora_pool, close_all_pools
    POOL_AVAILABLE = True
except ImportError:
    POOL_AVAILABLE = False


async def check_database() -> Dict[str, Any]:
    """Check database connectivity and stats"""
    try:
        if POOL_AVAILABLE:
            pool = get_valora_pool()
            # Quick test query
            result = pool.execute("SELECT COUNT(*) as count FROM properties LIMIT 1")
            count = result[0]["count"] if result else 0
            
            return {
                "status": "healthy",
                "properties_count": count,
                "pool_stats": pool.get_stats(),
                "response_time_ms": "<10"
            }
        else:
            # Fallback to direct connection
            db_path = find_database_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM properties")
            count = cursor.fetchone()[0]
            conn.close()
            
            return {
                "status": "healthy",
                "properties_count": count,
                "response_time_ms": "<50"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": None
        }


async def check_ollama() -> Dict[str, Any]:
    """Check Ollama LLM service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:11434/api/tags",
                timeout=5.0
            )
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "unknown") for m in data.get("models", [])]
                return {
                    "status": "healthy",
                    "models": models[:5],  # First 5 models
                    "response_time_ms": "<1000"
                }
            else:
                return {
                    "status": "degraded",
                    "error": f"HTTP {response.status_code}",
                    "response_time_ms": None
                }
    except httpx.ConnectError:
        return {
            "status": "unhealthy",
            "error": "Ollama not running on port 11434",
            "response_time_ms": None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": None
        }


async def check_cache() -> Dict[str, Any]:
    """Check cache system"""
    try:
        if CACHE_AVAILABLE:
            cache = get_cache()
            stats = cache.get_stats()
            return {
                "status": "healthy",
                "l1_size": stats.get("l1_size", 0),
                "hit_rate_percent": stats.get("hit_rate_percent", 0),
                "total_hits": stats.get("l1_hits", 0) + stats.get("l2_hits", 0),
                "misses": stats.get("misses", 0)
            }
        else:
            return {
                "status": "disabled",
                "note": "Cache not available"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_circuit_breakers() -> Dict[str, Any]:
    """Check circuit breaker status"""
    if CIRCUIT_BREAKER_AVAILABLE:
        return {
            "status": "active",
            "circuits": get_all_circuit_status()
        }
    return {
        "status": "disabled",
        "note": "Circuit breaker not available"
    }


def find_database_path() -> str:
    """Find the database file"""
    possible_paths = [
        "backend/valora.db",
        "valora.db",
        "backend/database/valora.db",
        "database/valora.db"
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            return path
    
    return possible_paths[0]


async def health_check() -> Dict[str, Any]:
    """
    Full system health check
    
    Returns:
        {
            "status": "healthy|degraded|unhealthy",
            "timestamp": "2026-02-07T...",
            "services": {
                "database": {...},
                "ollama": {...},
                "cache": {...},
                "circuit_breakers": {...}
            },
            "version": "2.0.0"
        }
    """
    start_time = datetime.now()
    
    # Check all services in parallel
    results = await asyncio.gather(
        check_database(),
        check_ollama(),
        check_cache(),
        return_exceptions=True
    )
    
    database_status, ollama_status, cache_status = results
    
    # Handle exceptions
    if isinstance(database_status, Exception):
        database_status = {"status": "error", "error": str(database_status)}
    if isinstance(ollama_status, Exception):
        ollama_status = {"status": "error", "error": str(ollama_status)}
    if isinstance(cache_status, Exception):
        cache_status = {"status": "error", "error": str(cache_status)}
    
    # Determine overall status
    all_statuses = [
        database_status.get("status", "unknown"),
        ollama_status.get("status", "unknown"),
        cache_status.get("status", "unknown")
    ]
    
    if "unhealthy" in all_statuses:
        overall_status = "unhealthy"
    elif "degraded" in all_statuses:
        overall_status = "degraded"
    elif all(s == "healthy" for s in all_statuses if s != "disabled"):
        overall_status = "healthy"
    else:
        overall_status = "unknown"
    
    elapsed = (datetime.now() - start_time).total_seconds() * 1000
    runtime_validation = validate_runtime(config.MODELS_DIR)
    if runtime_validation["status"] == "unhealthy":
        overall_status = "unhealthy"
    elif runtime_validation["status"] == "degraded" and overall_status == "healthy":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "response_time_ms": round(elapsed, 2),
        "services": {
            "database": database_status,
            "ollama": ollama_status,
            "cache": cache_status,
            "circuit_breakers": check_circuit_breakers()
        },
        "runtime_validation": runtime_validation,
        "version": "2.0.0"
    }


async def ready_check() -> bool:
    """
    Quick readiness check for load balancers
    Returns True if system can accept requests
    """
    try:
        db_check = await check_database()
        runtime_validation = validate_runtime(config.MODELS_DIR)
        return db_check.get("status") == "healthy" and runtime_validation.get("status") != "unhealthy"
    except:
        return False
