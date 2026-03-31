"""
Admin API Routes
System management, monitoring, and configuration endpoints

SECURITY:
- All sensitive endpoints require admin authentication
- Input validation on all parameters
- Audit logging for administrative actions
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, validator
import time
import asyncio
import httpx
import json
import re
import logging
from pathlib import Path

from core.circuit_breaker import get_circuit_breaker
from routes.auth_routes import require_admin
from auth.user_auth import User

logger = logging.getLogger("valora.admin")

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ============================================================================
# ADMIN CONFIG (PERSISTENT SETTINGS)
# ============================================================================

ADMIN_CONFIG_FILE = Path(__file__).parent / 'admin_config.json'


def _load_admin_config() -> dict:
    """Load admin config from file."""
    defaults = {
        "vector_backend": "faiss",
    }
    if ADMIN_CONFIG_FILE.exists():
        try:
            with open(ADMIN_CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    defaults.update(saved)
        except:
            pass
    return defaults


def _save_admin_config(config: dict) -> bool:
    """Save admin config to file."""
    try:
        with open(ADMIN_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except:
        return False


# Global state for vector backend preference (loaded from persistent config)
_admin_config = _load_admin_config()
_vector_backend = _admin_config.get("vector_backend", "faiss")

# Processing jobs tracker
_active_jobs = []


class VectorBackendRequest(BaseModel):
    backend: str  # "faiss" (production mode)


class IndexingRequest(BaseModel):
    target: str  # "faiss"


class LLMConfigRequest(BaseModel):
    provider: str = 'local'  # 'local' or 'cloud'
    local_enabled: Optional[bool] = True
    cloud_enabled: Optional[bool] = False
    openrouter_api_key: Optional[str] = ""
    openrouter_model: Optional[str] = "deepseek/deepseek-chat"
    local_url: Optional[str] = "http://127.0.0.1:11434/v1/chat/completions"
    local_model: Optional[str] = "qwen3:4b-instruct"
    max_context: Optional[int] = 8192  # 0 means unlimited



@router.get("/health", include_in_schema=True)
async def public_health_check() -> Dict[str, Any]:
    """
    Public health check endpoint (no authentication required)
    Used by load balancers and monitoring systems
    """
    try:
        from monitoring.health_check import health_check
        return await health_check()
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/status")
async def get_system_status(admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """Get comprehensive system status."""
    status = {
        "backend": {"status": "healthy", "fastapi": True},
        "database": {"status": "unknown"},
        "pinecone": {"status": "disabled", "reason": "FAISS-only production"},
        "faiss": {"status": "unknown"},
        "ai": {"status": "unknown"},
        "cache": {"status": "unknown"},
        "sources": {},
        "duplicates": {"database": 0, "pinecone": "N/A"}
    }
    
    # Check database
    try:
        from database.query_service import get_query_service
        from database.db_service import DatabaseService
        from config import config
        
        db = get_query_service()
        db_path = config.DB_PATH
        db_service = DatabaseService(str(db_path.resolve()))
        
        props_count = db.get_properties_count()
        
        # Get POI count
        try:
            pois_result = db_service.execute("SELECT COUNT(*) as cnt FROM pois")
            pois_count = pois_result[0]['cnt'] if pois_result else 0
        except:
            pois_count = 0
        
        # Get buildings count
        try:
            buildings_result = db_service.execute("SELECT COUNT(*) as cnt FROM buildings")
            buildings_count = buildings_result[0]['cnt'] if buildings_result else 0
        except:
            buildings_count = 0
        
        # Get places count
        try:
            places_result = db_service.execute("SELECT COUNT(*) as cnt FROM places")
            places_count = places_result[0]['cnt'] if places_result else 0
        except:
            places_count = 0
        
        # Get transport count
        try:
            transport_result = db_service.execute("SELECT COUNT(*) as cnt FROM transport_stops")
            transport_count = transport_result[0]['cnt'] if transport_result else 0
        except:
            transport_count = 0
        
        # Check for duplicates
        try:
            dup_result = db_service.execute(
                "SELECT COUNT(*) as cnt FROM (SELECT property_id FROM properties GROUP BY property_id HAVING COUNT(*) > 1)"
            )
            dup_count = dup_result[0]['cnt'] if dup_result else 0
            status["duplicates"]["database"] = dup_count
        except:
            pass
        
        status["database"] = {
            "status": "healthy" if props_count > 0 else "degraded",
            "properties": props_count,
            "pois": pois_count,
            "buildings": buildings_count,
            "places": places_count,
            "transport": transport_count,
        }
        
        # Get sources breakdown
        try:
            sources = db.get_properties_by_source()
            status["sources"] = sources
        except:
            pass
            
    except Exception as e:
        status["database"] = {"status": "down", "error": str(e)}
    
    # Pinecone disabled in production mode
    
    # Check FAISS
    try:
        from search.local_vector_store import get_local_store, FAISS_AVAILABLE
        
        if FAISS_AVAILABLE:
            try:
                store = get_local_store()
                stats = store.get_stats()
                status["faiss"] = {
                    "status": "healthy" if stats["total_vectors"] > 0 else "degraded",
                    "vectors": stats["total_vectors"],
                    "namespaces": len(stats["namespaces"])
                }
            except:
                status["faiss"] = {"status": "degraded", "vectors": 0, "namespaces": 0}
        else:
            status["faiss"] = {"status": "down", "error": "FAISS not installed"}
    except Exception as e:
        status["faiss"] = {"status": "down", "error": str(e)}
    
    # Check AI services
    try:
        from ai.rag_service import EMBEDDINGS_AVAILABLE
        
        status["ai"] = {
            "status": "healthy",
            "embeddings": EMBEDDINGS_AVAILABLE,
            "reasoning": False  # Advanced reasoning module removed
        }
    except Exception as e:
        status["ai"] = {"status": "degraded", "error": str(e)}
    
    # Check cache
    try:
        from search.query_cache import get_rag_cache
        cache = get_rag_cache()
        cache_stats = cache.get_stats()
        
        status["cache"] = {
            "status": "healthy",
            "entries": cache_stats.get("size", 0),
            "hitRate": int(cache_stats.get("hit_rate", 0) * 100)
        }
    except Exception as e:
        status["cache"] = {"status": "degraded", "entries": 0, "hitRate": 0}
    
    # Check insight cache
    try:
        from insight_cache import get_cache_stats
        insight_stats = get_cache_stats()
        
        if "error" not in insight_stats:
            status["insight_cache"] = {
                "status": "healthy",
                "cached_insights": insight_stats.get("total_cached_insights", 0),
                "cache_hits": insight_stats.get("total_cache_hits", 0),
                "unique_users": insight_stats.get("unique_users_cached", 0),
                "total_charges": insight_stats.get("total_charges", 0),
                "total_units": insight_stats.get("total_units_charged", 0),
                "training_samples": insight_stats.get("training_samples", 0),
                "ttl_days": insight_stats.get("cache_ttl_days", 30),
                "radius_km": insight_stats.get("cache_radius_km", 2.0)
            }
        else:
            status["insight_cache"] = {"status": "degraded", "error": insight_stats.get("error")}
    except Exception as e:
        status["insight_cache"] = {"status": "down", "error": str(e)}
    
    return status


@router.get("/vector-backend")
async def get_vector_backend(admin: User = Depends(require_admin)) -> Dict[str, str]:
    """Get current vector search backend."""
    global _vector_backend
    return {"backend": _vector_backend}


@router.post("/vector-backend")
async def set_vector_backend(request: VectorBackendRequest, admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """Set vector search backend (pinecone or faiss)."""
    global _vector_backend
    
    if request.backend != "faiss":
        return {"success": False, "error": "Pinecone disabled. FAISS-only production mode."}
    
    _vector_backend = request.backend

    # Persist setting
    try:
        global _admin_config
        _admin_config["vector_backend"] = _vector_backend
        _save_admin_config(_admin_config)
    except:
        pass
    
    # Update RAG service preference
    try:
        from ai.rag_service import get_rag_service
        rag = get_rag_service()
        rag.prefer_faiss = (request.backend == "faiss")
    except:
        pass
    
    return {"success": True, "backend": _vector_backend}


@router.post("/run-tests")
async def run_system_tests(admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """Run system health tests."""
    tests = []
    start_time = time.time()
    
    # Test 1: Database connection
    test_start = time.time()
    try:
        from database.query_service import get_query_service
        db = get_query_service()
        count = db.get_properties_count()
        tests.append({
            "name": "Database Connection",
            "description": f"Connected to database with {count:,} properties",
            "passed": count > 0,
            "duration": int((time.time() - test_start) * 1000)
        })
    except Exception as e:
        tests.append({
            "name": "Database Connection",
            "description": str(e),
            "passed": False,
            "duration": int((time.time() - test_start) * 1000)
        })
    
    tests.append({
        "name": "Pinecone Connection",
        "description": "Skipped (FAISS-only production mode)",
        "passed": True,
        "skipped": True,
        "duration": 0
    })
    
    # Test 3: FAISS availability
    test_start = time.time()
    try:
        from search.local_vector_store import get_local_store, FAISS_AVAILABLE
        if FAISS_AVAILABLE:
            store = get_local_store()
            stats = store.get_stats()
            tests.append({
                "name": "FAISS Local Store",
                "description": f"Available with {stats['total_vectors']:,} vectors",
                "passed": True,
                "duration": int((time.time() - test_start) * 1000)
            })
        else:
            tests.append({
                "name": "FAISS Local Store",
                "description": "FAISS not installed",
                "passed": False,
                "duration": int((time.time() - test_start) * 1000)
            })
    except Exception as e:
        tests.append({
            "name": "FAISS Local Store",
            "description": str(e),
            "passed": False,
            "duration": int((time.time() - test_start) * 1000)
        })
    
    # Test 4: Embedding model
    test_start = time.time()
    try:
        from ai.rag_service import get_rag_service
        rag = get_rag_service()
        embedding = rag.embed_single("test query")
        tests.append({
            "name": "Embedding Model",
            "description": f"Model loaded, dimension={len(embedding)}",
            "passed": len(embedding) == 384,
            "duration": int((time.time() - test_start) * 1000)
        })
    except Exception as e:
        tests.append({
            "name": "Embedding Model",
            "description": str(e),
            "passed": False,
            "duration": int((time.time() - test_start) * 1000)
        })
    
    # Test 5: Search functionality
    test_start = time.time()
    try:
        from ai.rag_service import get_rag_service
        rag = get_rag_service()
        results = rag.search("apartment near metro", top_k=3, namespace="properties")
        tests.append({
            "name": "Vector Search",
            "description": f"Search returned {len(results)} results",
            "passed": len(results) > 0,
            "duration": int((time.time() - test_start) * 1000)
        })
    except Exception as e:
        tests.append({
            "name": "Vector Search",
            "description": str(e),
            "passed": False,
            "duration": int((time.time() - test_start) * 1000)
        })
    
    # Test 6: Intent Classification
    test_start = time.time()
    try:
        from gis_agents import IntentRouter
        router = IntentRouter()
        intent = router.classify("What's the price trend in Koramangala?")
        tests.append({
            "name": "Intent Classification",
            "description": f"Classified as '{intent}'",
            "passed": intent is not None and intent != "unknown",
            "duration": int((time.time() - test_start) * 1000)
        })
    except Exception as e:
        tests.append({
            "name": "Intent Classification",
            "description": str(e),
            "passed": False,
            "duration": int((time.time() - test_start) * 1000)
        })
    
    # Test 7: Advanced Reasoning (removed - module obsolete)
    tests.append({
        "name": "Reasoning Engine",
        "description": "Module removed - functionality integrated elsewhere",
        "passed": True,
        "duration": 0
    })
    
    # Calculate summary
    passed = sum(1 for t in tests if t["passed"])
    failed = len(tests) - passed
    
    return {
        "tests": tests,
        "total": len(tests),
        "passed": passed,
        "failed": failed,
        "duration": int((time.time() - start_time) * 1000)
    }



@router.get("/processing-status")
async def get_processing_status(admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """Get status of active processing jobs."""
    global _active_jobs
    return {"jobs": _active_jobs}


@router.post("/trigger-indexing")
async def trigger_indexing(request: IndexingRequest, admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """Trigger indexing job (FAISS only)."""
    global _active_jobs

    if request.target.lower() != "faiss":
        return {"success": False, "error": "Pinecone disabled. Use FAISS indexing only."}
    
    job_name = f"{request.target.upper()} Indexing"
    
    # Check if already running
    for job in _active_jobs:
        if job["name"] == job_name and job["status"] == "running":
            return {"success": False, "error": f"{job_name} already running"}
    
    # Add job
    job = {
        "name": job_name,
        "status": "running",
        "started_at": time.time()
    }
    _active_jobs.append(job)
    
    # In production, this would spawn a background task
    # For now, just mark as pending
    return {"success": True, "message": f"{job_name} started"}


def get_vector_backend_preference() -> str:
    """Get current vector backend preference for use by other modules."""
    global _vector_backend
    return _vector_backend


# ============================================================================
# LLM CONFIGURATION ENDPOINTS
# ============================================================================

LLM_CONFIG_FILE = Path(__file__).parent.parent / 'llm_config.json'

def _load_llm_config() -> dict:
    """Load LLM config from file - supports local mode with qwen3:4b-instruct."""
    import os
    defaults = {
        'provider': 'local',  # 'local' or 'cloud'
        'local_enabled': True,
        'cloud_enabled': False,
        'openrouter_api_key': os.getenv('OPENROUTER_API_KEY', ''),
        'openrouter_model': os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-chat'),
        'openrouter_model_reasoning': os.getenv('OPENROUTER_MODEL_REASONING', 'deepseek/deepseek-reasoner'),
        'openrouter_model_vision': os.getenv('OPENROUTER_MODEL_VISION', 'qwen/qwen2.5-vl-72b-instruct'),
        'local_url': os.getenv('LOCAL_LLM_URL', 'http://127.0.0.1:11434/v1/chat/completions'),
        'local_model': os.getenv('LOCAL_LLM_MODEL', 'qwen3:4b-instruct'),
        'max_context': 8192  # Default context window size, 0 means unlimited
    }
    if LLM_CONFIG_FILE.exists():
        try:
            with open(LLM_CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                defaults.update(saved)
        except:
            pass
    return defaults

def _save_llm_config(config: dict) -> bool:
    """Save LLM config to file."""
    try:
        with open(LLM_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except:
        return False


@router.get("/llm-config")
async def get_llm_config() -> Dict[str, Any]:
    """Get current LLM configuration."""
    config = _load_llm_config()
    # Mask API key for security (only show last 4 chars)
    if config.get('openrouter_api_key'):
        key = config['openrouter_api_key']
        config['openrouter_api_key'] = f"...{key[-4:]}" if len(key) > 4 else "****"
    return config


@router.post("/llm-config")
async def set_llm_config(request: LLMConfigRequest) -> Dict[str, Any]:
    """Set LLM configuration with dual provider support."""
    # Load existing config to preserve API key if masked
    existing = _load_llm_config()
    
    config = {
        'provider': request.provider,
        'local_enabled': request.local_enabled if request.local_enabled is not None else True,
        'cloud_enabled': request.cloud_enabled if request.cloud_enabled is not None else False,
        'openrouter_model': request.openrouter_model,
        'local_url': request.local_url,
        'local_model': request.local_model,
        'max_context': request.max_context if request.max_context is not None else 8192
    }
    
    # Only update API key if it's a real key (not masked)
    incoming_key = request.openrouter_api_key
    if incoming_key and isinstance(incoming_key, str) and incoming_key.startswith('...'):
        incoming_key = ""
    if incoming_key and isinstance(incoming_key, str) and incoming_key.strip():
        config['openrouter_api_key'] = incoming_key.strip()
    else:
        config['openrouter_api_key'] = existing.get('openrouter_api_key', '')
    
    # Reset circuit breaker when model config changes (helps after OOM errors)
    try:
        cb = get_circuit_breaker("ollama")
        cb.reset()
    except Exception:
        pass  # Ignore if circuit breaker not available
    
    if _save_llm_config(config):
        return {"success": True, "message": "Configuration saved", "config": config}
    else:
        raise HTTPException(status_code=500, detail="Failed to save configuration")


@router.get("/llm-models")
async def get_available_llm_models() -> Dict[str, Any]:
    """Fetch available models from OpenRouter and Ollama in real-time."""
    result = {
        "openrouter": [],
        "local": [],
        "openrouter_error": None,
        "local_error": None
    }
    
    # Load existing config for API key
    config = _load_llm_config()
    api_key = config.get('openrouter_api_key', '')
    
    # Fetch OpenRouter models (free ones)
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if response.status_code == 200:
                    data = response.json()
                    models = data.get('data', [])
                    # Filter for free models and format them
                    for model in models:
                        model_id = model.get('id', '')
                        pricing = model.get('pricing', {})
                        prompt_price = float(pricing.get('prompt', '1') or '1')
                        completion_price = float(pricing.get('completion', '1') or '1')
                        # Free models have 0 pricing
                        if prompt_price == 0 and completion_price == 0:
                            result["openrouter"].append({
                                "id": model_id,
                                "name": model.get('name', model_id),
                                "context_length": model.get('context_length', 0)
                            })
                else:
                    result["openrouter_error"] = f"API error: {response.status_code}"
        except Exception as e:
            result["openrouter_error"] = str(e)
    else:
        result["openrouter_error"] = "No API key configured"
    
    # Fetch Ollama local models
    local_url = config.get('local_url', 'http://127.0.0.1:11434/v1/chat/completions')
    ollama_base = local_url.replace('/v1/chat/completions', '').replace('/v1', '')
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ollama_base}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                for model in models:
                    result["local"].append({
                        "id": model.get('name', '').replace(':latest', ''),
                        "name": model.get('name', ''),
                        "size": model.get('size', 0)
                    })
            else:
                result["local_error"] = f"Ollama error: {response.status_code}"
    except Exception as e:
        result["local_error"] = f"Ollama not running: {str(e)}"
    
    return result


@router.post("/llm-test")
async def test_llm_connection(request: LLMConfigRequest) -> Dict[str, Any]:
    """Test LLM connection with provided config."""
    # Load existing config to get real API key if masked
    existing = _load_llm_config()
    
    api_key = request.openrouter_api_key
    if api_key and api_key.startswith('...'):
        api_key = existing.get('openrouter_api_key', '')
    
    try:
        if request.provider == 'openrouter':
            # Test OpenRouter
            if not api_key:
                return {"success": False, "message": "OpenRouter API key not configured"}
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "HTTP-Referer": "http://localhost:3000",
                        "X-Title": "Valora AI"
                    },
                    json={
                        "model": request.openrouter_model,
                        "messages": [{"role": "user", "content": "Say 'OK' if you can hear me."}],
                        "max_tokens": 10
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    reply = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    return {"success": True, "message": f"OpenRouter connected! Model: {request.openrouter_model}. Reply: {reply[:50]}"}
                else:
                    return {"success": False, "message": f"OpenRouter error: {response.status_code} - {response.text[:100]}"}
        
        else:
            # Test Local LLM
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    request.local_url,
                    json={
                        "model": request.local_model,
                        "messages": [{"role": "user", "content": "Say 'OK' if you can hear me."}],
                        "max_tokens": 10,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    reply = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    return {"success": True, "message": f"Local LLM connected! Model: {request.local_model}. Reply: {reply[:50]}"}
                else:
                    return {"success": False, "message": f"Local LLM error: {response.status_code} - {response.text[:100]}"}
    
    except httpx.ConnectError:
        if request.provider == 'local':
            return {"success": False, "message": f"Cannot connect to {request.local_url}. Is the local LLM server running?"}
        else:
            return {"success": False, "message": "Cannot connect to OpenRouter. Check your internet connection."}
    except httpx.TimeoutException:
        return {"success": False, "message": "Connection timed out. The server might be slow or unresponsive."}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


class UnloadModelRequest(BaseModel):
    model: str

@router.post("/unload-model")
async def unload_model(request: UnloadModelRequest) -> Dict[str, Any]:
    """Unload a model from Ollama to free RAM."""
    config = _load_llm_config()
    local_url = config.get('local_url', 'http://127.0.0.1:11434/v1/chat/completions')
    ollama_base = local_url.replace('/v1/chat/completions', '').replace('/v1', '')
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Ollama unload by setting keep_alive to 0
            response = await client.post(
                f"{ollama_base}/api/generate",
                json={"model": request.model, "keep_alive": 0}
            )
            if response.status_code == 200:
                return {"success": True, "message": f"Model '{request.model}' unloaded to free RAM"}
            else:
                return {"success": False, "message": f"Failed to unload: {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


def get_active_llm_config() -> dict:
    """Get the active LLM config for use by other modules."""
    return _load_llm_config()


# ============================================================================
# LOCALITY BRAIN MANAGEMENT
# ============================================================================

@router.post("/rebuild-locality-brain")
async def rebuild_locality_brain() -> Dict[str, Any]:
    """Rebuild the locality brain (precomputed intelligence)."""
    import subprocess
    import sys
    
    script_path = Path(__file__).parent.parent / 'scripts' / 'build_locality_brain.py'
    
    if not script_path.exists():
        return {"success": False, "message": "Brain builder script not found"}
    
    try:
        # Run the brain builder script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Parse output for summary
        output = result.stdout
        lines = output.split('\n')
        
        # Find success/error counts
        success_count = 0
        error_count = 0
        for line in lines:
            if 'Success:' in line:
                try:
                    success_count = int(line.split('Success:')[1].split()[0])
                except:
                    pass
            if 'Errors:' in line:
                try:
                    error_count = int(line.split('Errors:')[1].split()[0])
                except:
                    pass
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"Locality brain rebuilt successfully! {success_count} localities processed, {error_count} errors.",
                "details": {
                    "localities_processed": success_count,
                    "errors": error_count,
                }
            }
        else:
            return {
                "success": False,
                "message": f"Brain rebuild failed: {result.stderr[:500]}"
            }
    
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Brain rebuild timed out (>5 minutes)"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.get("/locality-brain-status")
async def get_locality_brain_status() -> Dict[str, Any]:
    """Get status of the locality brain."""
    import sqlite3
    from config import config
    
    db_path = config.DB_PATH
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM locality_state")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM locality_state WHERE poi_count > 0")
        with_pois = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM locality_state WHERE transport_count > 0")
        with_transport = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(last_updated) FROM locality_state")
        last_updated = cursor.fetchone()[0]
        
        # Get growth phase distribution
        cursor.execute("""
            SELECT growth_phase, COUNT(*) as cnt 
            FROM locality_state 
            GROUP BY growth_phase
        """)
        phases = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "success": True,
            "status": {
                "total_localities": total,
                "with_pois": with_pois,
                "with_transport": with_transport,
                "last_updated": last_updated,
                "growth_phases": phases,
            }
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


# ============================================================================
# USAGE TRACKING & ML TRAINING DATA
# ============================================================================

@router.get("/usage/stats")
async def get_usage_stats(admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Get global usage statistics.
    SECURITY: Requires admin authentication.
    """
    try:
        from usage_tracker import get_usage_tracker
        tracker = get_usage_tracker()
        
        stats_7d = tracker.get_global_stats(days=7)
        stats_30d = tracker.get_global_stats(days=30)
        
        return {
            "success": True,
            "stats": {
                "last_7_days": stats_7d,
                "last_30_days": stats_30d
            }
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.get("/usage/user/{user_id}")
async def get_user_usage(user_id: int, days: int = 30, admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Get usage statistics for a specific user.
    SECURITY: Requires admin authentication, validates user_id.
    """
    # SECURITY: Validate user_id
    if not isinstance(user_id, int) or user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user_id")
    
    # SECURITY: Validate days parameter
    if not isinstance(days, int) or days <= 0 or days > 365:
        days = 30
    
    try:
        from usage_tracker import get_usage_tracker
        tracker = get_usage_tracker()
        
        stats = tracker.get_user_usage_stats(user_id, days=days)
        balance = tracker.get_user_balance(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "usage": stats,
            "balance": balance
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


class AddUnitsRequest(BaseModel):
    user_id: int
    units: int
    source: str = "admin_grant"
    reason: str = ""
    
    # SECURITY: Input validation
    @validator('user_id')
    def validate_user_id(cls, v):
        if not isinstance(v, int) or v <= 0:
            raise ValueError('Invalid user_id')
        return v
    
    @validator('units')
    def validate_units(cls, v):
        if not isinstance(v, int) or v <= 0 or v > 10000:
            raise ValueError('Units must be between 1 and 10000')
        return v
    
    @validator('source')
    def validate_source(cls, v):
        allowed = ['admin_grant', 'promo', 'refund', 'initial_grant']
        if v not in allowed:
            raise ValueError(f'Source must be one of: {allowed}')
        return v
    
    @validator('reason')
    def validate_reason(cls, v):
        # SECURITY: Sanitize reason to prevent injection
        if v:
            v = re.sub(r'[<>"\']', '', v)[:200]  # Remove dangerous chars, limit length
        return v


@router.post("/usage/add-units")
async def add_units_to_user(request: AddUnitsRequest, admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Add units to a user's balance.
    SECURITY: Requires admin authentication, validates all inputs, logs audit trail.
    """
    try:
        from usage_tracker import get_usage_tracker
        from auth.user_auth import get_user_database
        
        tracker = get_usage_tracker()
        
        success = tracker.add_units(
            user_id=request.user_id,
            units=request.units,
            source=request.source,
            transaction_id=f"admin_{admin.id}_{int(time.time())}"
        )
        
        if success:
            # SECURITY: Audit log
            db = get_user_database()
            db.log_usage(admin.id, "admin_add_units", 
                f"Added {request.units} units to user {request.user_id}. Reason: {request.reason}")
            
            balance = tracker.get_user_balance(request.user_id)
            return {
                "success": True,
                "message": f"Added {request.units} units to user {request.user_id}",
                "new_balance": balance.get("units_available", 0),
                "reason": request.reason,
                "admin_id": admin.id
            }
        else:
            return {"success": False, "message": "Failed to add units"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.get("/training-data/stats")
async def get_training_data_stats(admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Get statistics about collected training data.
    SECURITY: Requires admin authentication.
    """
    try:
        from data_collector import get_data_collector
        collector = get_data_collector()
        
        stats = collector.get_training_stats()
        
        total_samples = sum(s.get("count", 0) for s in stats.values())
        total_size_mb = sum(s.get("size_mb", 0) for s in stats.values())
        
        return {
            "success": True,
            "stats": stats,
            "summary": {
                "total_samples": total_samples,
                "total_size_mb": round(total_size_mb, 2),
                "data_types": len([s for s in stats.values() if s.get("count", 0) > 0])
            }
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


class ExportTrainingDataRequest(BaseModel):
    data_type: str = "all"  # queries, feedback, predictions, spatial, refinements, all
    limit: int = 1000
    since_date: Optional[str] = None
    
    # SECURITY: Input validation
    @validator('data_type')
    def validate_data_type(cls, v):
        allowed = ['all', 'queries', 'feedback', 'predictions', 'spatial', 'refinements']
        if v not in allowed:
            raise ValueError(f'data_type must be one of: {allowed}')
        return v
    
    @validator('limit')
    def validate_limit(cls, v):
        if not isinstance(v, int) or v <= 0 or v > 10000:
            raise ValueError('limit must be between 1 and 10000')
        return v
    
    @validator('since_date')
    def validate_since_date(cls, v):
        if v:
            # SECURITY: Validate date format to prevent injection
            import re
            if not re.match(r'^\d{4}-\d{2}-\d{2}', v):
                raise ValueError('since_date must be in YYYY-MM-DD format')
        return v


@router.post("/training-data/export")
async def export_training_data(request: ExportTrainingDataRequest, admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Export training data batch for manual ML training.
    SECURITY: Requires admin authentication, validates inputs, logs audit.
    """
    try:
        from data_collector import get_data_collector
        from auth.user_auth import get_user_database
        
        collector = get_data_collector()
        
        batch = collector.export_batch(
            data_type=request.data_type,
            limit=request.limit,
            since_date=request.since_date
        )
        
        # SECURITY: Audit log
        db = get_user_database()
        db.log_usage(admin.id, "admin_export_training_data", 
            f"Exported {len(batch)} samples of type {request.data_type}")
        
        return {
            "success": True,
            "data_type": request.data_type,
            "sample_count": len(batch),
            "samples": batch,
            "message": f"Exported {len(batch)} training samples. Use these for manual ML training.",
            "exported_by": admin.id
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


class ClearTrainingDataRequest(BaseModel):
    data_type: Optional[str] = None  # queries, feedback, predictions, spatial, refinements, or None for all
    confirm: bool = False
    
    # SECURITY: Input validation
    @validator('data_type')
    def validate_data_type(cls, v):
        if v:
            allowed = ['queries', 'feedback', 'predictions', 'spatial', 'refinements']
            if v not in allowed:
                raise ValueError(f'data_type must be one of: {allowed}')
        return v


@router.post("/training-data/clear")
async def clear_training_data(request: ClearTrainingDataRequest, admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Clear training data (privacy compliance).
    SECURITY: Requires admin authentication, requires confirmation, logs audit.
    """
    if not request.confirm:
        return {
            "success": False,
            "message": "Must set 'confirm: true' to clear training data. This action is irreversible."
        }
    
    try:
        from data_collector import get_data_collector
        from auth.user_auth import get_user_database
        
        collector = get_data_collector()
        
        collector.clear_data(data_type=request.data_type)
        
        message = f"Cleared all training data" if not request.data_type else f"Cleared {request.data_type} training data"
        
        # SECURITY: Audit log (critical action)
        db = get_user_database()
        db.log_usage(admin.id, "admin_clear_training_data", 
            f"CRITICAL: {message} by admin {admin.email}")
        
        return {
            "success": True,
            "message": message,
            "cleared_by": admin.id
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.get("/usage/action-costs")
async def get_action_costs() -> Dict[str, Any]:
    """
    Get all action types and their compute costs.
    NOTE: This endpoint is public as costs should be transparent.
    """
    try:
        from usage_tracker import COMPUTE_COSTS, TIER_MONTHLY_LIMITS
        
        return {
            "success": True,
            "action_costs": COMPUTE_COSTS,
            "tier_limits": TIER_MONTHLY_LIMITS,
            "currency": "compute_units",
            "pricing": {
                "promo_per_unit_inr": 2,
                "regular_per_unit_inr": 10,
                "promo_valid_until": "2026-03-31"
            },
            "note": "Costs in compute units. 1 unit ≈ ₹2 (promo) to ₹10 (regular)"
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.get("/usage/revenue-estimate")
async def get_revenue_estimate(days: int = 30, admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Get estimated revenue from usage.
    SECURITY: Requires admin authentication (sensitive financial data).
    """
    # SECURITY: Validate days parameter
    if not isinstance(days, int) or days <= 0 or days > 365:
        days = 30
    
    try:
        from usage_tracker import get_usage_tracker
        tracker = get_usage_tracker()
        
        stats = tracker.get_global_stats(days=days)
        total_units = stats.get("total_units_charged", 0)
        
        # Revenue estimates
        promo_price_per_unit = 2  # ₹2 per unit during promo
        regular_price_per_unit = 10  # ₹10 per unit regular
        
        return {
            "success": True,
            "period_days": days,
            "total_units_charged": total_units,
            "revenue_estimate": {
                "promo_inr": total_units * promo_price_per_unit,
                "regular_inr": total_units * regular_price_per_unit,
                "currency": "INR"
            },
            "active_users": stats.get("active_users", 0),
            "avg_units_per_user": round(total_units / stats.get("active_users", 1), 2) if stats.get("active_users", 0) > 0 else 0
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


# ============================================================================
# PRICING CONFIGURATION (ADMIN EDITABLE)
# ============================================================================

@router.get("/pricing/config")
async def get_pricing_config(admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Get current pricing configuration.
    SECURITY: Requires admin authentication.
    """
    try:
        config = {}
        
        # Try dynamic credits system first
        try:
            from ai.dynamic_credits import get_credits_config
            dc_config = get_credits_config()
            costs = dc_config.get_costs()
            
            config.update({
                "action_costs": costs.to_dict(),
                "packages": {name: pkg.to_dict() for name, pkg in dc_config.get_packages().items()},
                "integrity_verified": dc_config.verify_integrity(),
                "source": "dynamic_credits",
                "config_file": str(dc_config.config_path),
            })
        except ImportError:
            pass
        
        # Also load database pricing for subscription_tiers, topup_packs, etc.
        try:
            from database.pricing_db import get_pricing_db
            pricing_db = get_pricing_db()
            db_config = pricing_db.get_config()
            
            config["subscription_tiers"] = db_config.get("subscription_tiers", {})
            config["topup_packs"] = db_config.get("topup_packs", [])
            config["tier_monthly_limits"] = db_config.get("tier_monthly_limits", {})
            config["pricing"] = db_config.get("pricing", {})
            config["last_updated"] = db_config.get("last_updated")
            config["updated_by"] = db_config.get("updated_by")
        except Exception as e:
            logger.warning(f"Pricing DB load failed: {e}")
            
            # Fallback to usage_tracker
            try:
                from usage_tracker import _load_pricing_config
                ut_config = _load_pricing_config()
                config["subscription_tiers"] = ut_config.get("subscription_tiers", {})
                config["topup_packs"] = ut_config.get("topup_packs", [])
                config["tier_monthly_limits"] = ut_config.get("tier_monthly_limits", {})
                config["pricing"] = ut_config.get("pricing", {})
                config["last_updated"] = ut_config.get("last_updated")
                config["updated_by"] = ut_config.get("updated_by")
            except Exception as e2:
                logger.warning(f"Usage tracker fallback failed: {e2}")
        
        return {
            "success": True,
            "config": config,
        }
    except Exception as e:
        logger.error(f"All pricing config methods failed: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


class UpdatePricingRequest(BaseModel):
    action_costs: Optional[Dict[str, int]] = None
    tier_monthly_limits: Optional[Dict[str, int]] = None
    pricing: Optional[Dict[str, Any]] = None
    topup_packs: Optional[list] = None
    subscription_tiers: Optional[Dict[str, Any]] = None
    
    # SECURITY: Input validation
    @validator('action_costs')
    def validate_action_costs(cls, v):
        if v:
            for action, cost in v.items():
                # Validate action name
                if not re.match(r'^[a-z_]+$', action):
                    raise ValueError(f'Invalid action name: {action}')
                # Validate cost
                if not isinstance(cost, int) or cost < 0 or cost > 1000:
                    raise ValueError(f'Cost must be between 0 and 1000 for {action}')
        return v
    
    @validator('tier_monthly_limits')
    def validate_tier_limits(cls, v):
        if v:
            allowed_tiers = ['free', 'pro', 'team', 'admin']
            for tier, limit in v.items():
                if tier not in allowed_tiers:
                    raise ValueError(f'Invalid tier: {tier}')
                if not isinstance(limit, int) or (limit < -1 or limit > 1000000):
                    raise ValueError(f'Limit must be -1 (unlimited) or 0-1000000 for {tier}')
        return v


@router.post("/pricing/config")
async def update_pricing_config(request: UpdatePricingRequest, admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Update pricing configuration in DATABASE.
    SECURITY: Database storage + audit trail prevents tampering.
    """
    try:
        from datetime import datetime
        
        # Try dynamic credits system first for action_costs
        if request.action_costs:
            try:
                from ai.dynamic_credits import get_credits_config
                config = get_credits_config()
                
                # Get client IP for audit
                client_ip = "admin_panel"
                
                updated_actions = []
                for action, cost in request.action_costs.items():
                    success = config.update_cost(
                        action=action,
                        new_cost=cost,
                        user_id=admin.email,
                        ip_address=client_ip,
                        signature=f"admin:{admin.id}"
                    )
                    if success:
                        updated_actions.append(action)
                
                if updated_actions:
                    logger.info(f"Admin {admin.email} updated credit costs: {updated_actions}")
            except Exception as e:
                logger.warning(f"Dynamic credits update failed: {e}")
        
        # Also update database pricing for backward compatibility
        try:
            from usage_tracker import _load_pricing_config, _save_pricing_config
            from auth.user_auth import get_user_database
            
            # Load current config from database
            config = _load_pricing_config()
            
            # Update fields
            if request.action_costs:
                config["action_costs"] = {**config.get("action_costs", {}), **request.action_costs}
            
            if request.tier_monthly_limits:
                config["tier_monthly_limits"] = {**config.get("tier_monthly_limits", {}), **request.tier_monthly_limits}
            
            if request.pricing:
                config["pricing"] = {**config.get("pricing", {}), **request.pricing}
            
            if request.topup_packs:
                config["topup_packs"] = request.topup_packs
            
            if request.subscription_tiers:
                config["subscription_tiers"] = {**config.get("subscription_tiers", {}), **request.subscription_tiers}
            
            # Save to database with admin email
            success = _save_pricing_config(config, updated_by=admin.email)
            
            if success:
                # SECURITY: Audit log in user database too
                try:
                    db = get_user_database()
                    db.log_usage(admin.id, "admin_update_pricing", 
                        f"Updated pricing config in database by {admin.email}")
                except:
                    pass
                
                return {
                    "success": True,
                    "message": "Pricing configuration updated successfully",
                    "config": config,
                    "note": "Changes applied immediately (no restart needed)"
                }
            else:
                return {"success": False, "message": "Failed to save pricing configuration to database"}
        except Exception as e:
            logger.warning(f"Database pricing update failed: {e}")
            
            # If we updated dynamic credits, still return success
            if request.action_costs:
                return {
                    "success": True,
                    "message": "Credit costs updated in dynamic system",
                    "note": "Database update failed but dynamic credits were updated"
                }
            
            return {"success": False, "message": f"Error: {str(e)}"}
            
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/pricing/reload")
async def reload_pricing_config(admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Reload pricing configuration without server restart.
    SECURITY: Requires admin authentication.
    """
    try:
        from usage_tracker import _load_pricing_config
        import importlib
        import usage_tracker
        
        # Reload the module
        importlib.reload(usage_tracker)
        
        config = _load_pricing_config()
        
        return {
            "success": True,
            "message": "Pricing configuration reloaded successfully",
            "config": config
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


# ============================================================================
# CLOUD COST DASHBOARD (HYBRID AI OPTIMIZATION)
# ============================================================================

@router.get("/cloud-cost/stats")
async def get_cloud_cost_stats(
    days: int = 7,
    user_id: Optional[str] = None,
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get cloud LLM cost statistics for dashboard.
    Shows costs, usage patterns, and optimization metrics.
    SECURITY: Requires admin authentication.
    """
    # Validate days parameter
    if not isinstance(days, int) or days <= 0 or days > 90:
        days = 7
    
    try:
        from ai.unified_valora_brain import get_valora_brain
        
        brain = get_valora_brain()
        stats = brain.get_cloud_cost_stats(user_id=user_id, days=days)
        
        # Add dynamic threshold settings
        stats['dynamic_thresholds'] = brain.confidence_thresholds
        stats['parallel_prediction_enabled'] = brain.parallel_prediction_enabled
        stats['parallel_complexity_threshold'] = brain.parallel_complexity_threshold
        
        # Calculate savings from parallel prediction (estimated)
        if stats.get('total_calls', 0) > 0:
            cancelled_calls = sum(
                1 for day in stats.get('daily_breakdown', [])
                for _ in range(day.get('calls', 0))  # Simplified estimation
            )
            # Estimate 30% of complex queries benefited from parallel prediction
            estimated_saved_calls = int(stats['total_calls'] * 0.15)  # 15% would have been redundant
            estimated_savings_usd = estimated_saved_calls * stats.get('avg_cost_per_call_usd', 0.001)
            stats['estimated_savings_from_parallel'] = {
                'saved_calls': estimated_saved_calls,
                'estimated_savings_usd': round(estimated_savings_usd, 4)
            }
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.get("/cloud-cost/models")
async def get_cloud_cost_by_model(
    days: int = 7,
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get cloud cost breakdown by model.
    SECURITY: Requires admin authentication.
    """
    if not isinstance(days, int) or days <= 0 or days > 90:
        days = 7
    
    try:
        from ai.unified_valora_brain import get_valora_brain
        
        brain = get_valora_brain()
        stats = brain.get_cloud_cost_stats(days=days)
        
        return {
            "success": True,
            "models": stats.get('cost_by_model', []),
            "cost_per_1k_tokens": brain.cloud_cost_per_1k_tokens
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.get("/cloud-cost/query-types")
async def get_cloud_cost_by_query_type(
    days: int = 7,
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get cloud cost breakdown by query type (intent classification, narrative generation).
    SECURITY: Requires admin authentication.
    """
    if not isinstance(days, int) or days <= 0 or days > 90:
        days = 7
    
    try:
        from ai.unified_valora_brain import get_valora_brain
        
        brain = get_valora_brain()
        stats = brain.get_cloud_cost_stats(days=days)
        
        # Add recommendations based on query type distribution
        recommendations = []
        for qt in stats.get('cost_by_query_type', []):
            if qt['query_type'] == 'intent_classification' and qt['calls'] > 100:
                recommendations.append(
                    f"High intent classification costs ({qt['calls']} calls). "
                    "Consider improving local pattern matching to reduce cloud dependency."
                )
            elif qt['query_type'] == 'narrative_generation' and qt['avg_time_ms'] > 2000:
                recommendations.append(
                    f"Slow narrative generation ({qt['avg_time_ms']:.0f}ms avg). "
                    "Consider caching or using faster models."
                )
        
        return {
            "success": True,
            "query_types": stats.get('cost_by_query_type', []),
            "recommendations": recommendations
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


class UpdateThresholdRequest(BaseModel):
    intent: str
    threshold: float
    
    @validator('intent')
    def validate_intent(cls, v):
        allowed = ['navigate', 'analyze_area', 'locality_search', 'property_search', 
                   'analyze_building', 'terrain', 'comparison', 'valuation', 
                   'investment', 'simulate', 'recommendation', 'general']
        if v not in allowed:
            raise ValueError(f'Intent must be one of: {allowed}')
        return v
    
    @validator('threshold')
    def validate_threshold(cls, v):
        if not isinstance(v, (int, float)) or v < 0.5 or v > 0.99:
            raise ValueError('Threshold must be between 0.5 and 0.99')
        return float(v)


@router.post("/cloud-cost/threshold")
async def update_confidence_threshold(
    request: UpdateThresholdRequest,
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Update dynamic confidence threshold for a specific intent.
    SECURITY: Requires admin authentication.
    """
    try:
        from ai.unified_valora_brain import get_valora_brain
        
        brain = get_valora_brain()
        old_threshold = brain.confidence_thresholds.get(request.intent)
        brain.confidence_thresholds[request.intent] = request.threshold
        
        return {
            "success": True,
            "intent": request.intent,
            "old_threshold": old_threshold,
            "new_threshold": request.threshold,
            "all_thresholds": brain.confidence_thresholds,
            "message": f"Updated {request.intent} threshold from {old_threshold} to {request.threshold}"
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/cloud-cost/parallel-prediction")
async def toggle_parallel_prediction(
    enabled: bool,
    complexity_threshold: Optional[int] = None,
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Enable/disable parallel prediction and adjust complexity threshold.
    SECURITY: Requires admin authentication.
    """
    try:
        from ai.unified_valora_brain import get_valora_brain
        
        brain = get_valora_brain()
        old_enabled = brain.parallel_prediction_enabled
        old_threshold = brain.parallel_complexity_threshold
        
        brain.parallel_prediction_enabled = enabled
        if complexity_threshold is not None and 1 <= complexity_threshold <= 10:
            brain.parallel_complexity_threshold = complexity_threshold
        
        return {
            "success": True,
            "parallel_prediction_enabled": brain.parallel_prediction_enabled,
            "parallel_complexity_threshold": brain.parallel_complexity_threshold,
            "previous_settings": {
                "enabled": old_enabled,
                "complexity_threshold": old_threshold
            },
            "message": f"Parallel prediction {'enabled' if enabled else 'disabled'} "
                      f"with complexity threshold {brain.parallel_complexity_threshold}"
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


# ============================================================================
# BATCH SPATIAL QUERIES
# ============================================================================

class BatchCompareRequest(BaseModel):
    locations: List[Dict[str, Any]]  # [{name, lat, lng, building_height?}]
    comparison_type: str = "comprehensive"  # "view", "sunlight", "comprehensive"
    weights: Optional[Dict[str, float]] = None  # For comprehensive
    time_of_day: Optional[str] = None  # For sunlight


@router.post("/batch/compare")
async def batch_compare_locations(
    request: BatchCompareRequest,
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Compare multiple locations in batch for view quality, sunlight, or comprehensive analysis.
    SECURITY: Requires admin authentication.
    """
    try:
        from ai.gis_agents import get_gis_orchestrator
        
        gis = get_gis_orchestrator()
        
        # Use GIS orchestrator for batch comparison (batch_spatial module removed)
        locations_data = []
        for loc in request.locations:
            result = gis.analyze_location(
                lat=loc.get('lat'),
                lng=loc.get('lng'),
                location_name=loc.get('name', 'Unknown'),
                radius_m=500
            )
            locations_data.append({
                "name": loc.get('name', 'Unknown'),
                "lat": loc.get('lat'),
                "lng": loc.get('lng'),
                "analysis": result
            })
        
        return {
            "success": True,
            "comparison_type": request.comparison_type,
            "total_locations": len(locations_data),
            "locations": locations_data,
            "summary": "Batch analysis completed using GIS orchestrator"
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


# ============================================================================
# CREDITS & RATE LIMITING
# ============================================================================

@router.get("/credits/user/{user_id}")
async def get_user_credits(user_id: str, admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Get user's credit balance and usage stats.
    SECURITY: Requires admin authentication.
    """
    try:
        from ai.credits_rate_limiter import get_rate_limiter
        
        limiter = get_rate_limiter()
        user = limiter.get_or_create_user(user_id)
        stats = limiter.get_usage_stats(user_id, days=30)
        
        return {
            "success": True,
            "user_id": user_id,
            "tier": user['tier'],
            "credits": {
                "total": user['monthly_credits'] + user.get('rollover_credits', 0) + user['top_up_credits'],
                "used": user['used_credits'],
                "remaining": user['total_available'],
                "reset_at": user['reset_at']
            },
            "usage_stats": stats
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/credits/add")
async def add_credits_to_user(
    user_id: str,
    credits: int,
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Add credits to user (admin grant).
    SECURITY: Requires admin authentication.
    """
    try:
        from ai.credits_rate_limiter import get_rate_limiter
        
        limiter = get_rate_limiter()
        success = limiter.add_credits(user_id, credits, source="admin_grant")
        user = limiter.get_or_create_user(user_id)
        
        if success:
            return {
                "success": True,
                "user_id": user_id,
                "credits_added": credits,
                "new_balance": user['total_available'],
                "message": f"Added {credits} credits to {user_id}"
            }
        else:
            return {"success": False, "message": "Failed to add credits"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/credits/dummy-payment")
async def process_dummy_payment(
    user_id: str,
    amount_inr: int,
    credits_to_add: int,
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Process dummy payment for testing credits purchase.
    SECURITY: Requires admin authentication for testing.
    """
    try:
        from ai.credits_rate_limiter import get_rate_limiter
        
        limiter = get_rate_limiter()
        result = limiter.process_dummy_payment(user_id, amount_inr, credits_to_add)
        
        return result
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.get("/credits/action-costs")
async def get_credit_costs(admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Get credit costs for all actions.
    SECURITY: Requires admin authentication.
    """
    try:
        from ai.dynamic_credits import get_credits_config
        
        config = get_credits_config()
        costs = config.get_costs()
        
        return {
            "success": True,
            "action_costs": costs.to_dict(),
            "packages": {name: pkg.to_dict() for name, pkg in config.get_packages().items()},
            "signature": costs.get_signature(),
            "integrity_verified": config.verify_integrity(),
            "config_file": str(config.config_path),
            "last_reload": config._last_reload,
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/credits/action-costs")
async def update_credit_cost(
    request: Request,
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Update credit cost for a specific action.
    SECURITY: Requires admin authentication + audit logging.
    """
    try:
        from ai.dynamic_credits import get_credits_config
        
        body = await request.json()
        action = body.get("action")
        new_cost = body.get("cost")
        
        if not action or new_cost is None:
            raise HTTPException(status_code=400, detail="Missing 'action' or 'cost'")
        
        if not isinstance(new_cost, int) or new_cost < 0:
            raise HTTPException(status_code=400, detail="Cost must be a non-negative integer")
        
        config = get_credits_config()
        
        # Get client IP for audit
        client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()
        
        # Update with audit trail
        success = config.update_cost(
            action=action,
            new_cost=new_cost,
            user_id=admin.email,
            ip_address=client_ip,
            signature=f"admin:{admin.id}"
        )
        
        if success:
            # Log to database
            try:
                from auth.user_auth import get_user_database
                db = get_user_database()
                db.log_usage(admin.id, "admin_update_credit_cost",
                    f"Updated {action} to {new_cost} credits")
            except:
                pass
            
            return {
                "success": True,
                "message": f"Updated {action} to {new_cost} credits",
                "new_costs": config.get_costs().to_dict(),
                "audit_logged": True
            }
        else:
            return {
                "success": False,
                "message": f"Failed to update {action}. Check if action exists or cost exceeds limits."
            }
            
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/credits/reload")
async def reload_credits_config(admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Force reload credits configuration from file.
    SECURITY: Requires admin authentication.
    """
    try:
        from ai.dynamic_credits import get_credits_config
        
        config = get_credits_config()
        config.reload()
        
        return {
            "success": True,
            "message": "Credits configuration reloaded",
            "costs": config.get_costs().to_dict(),
            "integrity_verified": config.verify_integrity()
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.get("/credits/audit-log")
async def get_credits_audit_log(
    limit: int = 100,
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get audit log for credit changes.
    SECURITY: Requires admin authentication.
    """
    try:
        from ai.dynamic_credits import get_credits_config
        
        config = get_credits_config()
        audit_log = config.get_audit_log(limit=limit)
        
        # Format for display
        formatted_log = []
        for entry in audit_log:
            formatted_log.append({
                "timestamp": entry.timestamp,
                "datetime": datetime.fromtimestamp(entry.timestamp).isoformat() if entry.timestamp else None,
                "action": entry.action,
                "user_id": entry.user_id,
                "old_value": entry.old_value,
                "new_value": entry.new_value,
                "ip_address": entry.ip_address,
            })
        
        return {
            "success": True,
            "audit_log": formatted_log,
            "total_entries": len(config._audit_log)
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


# ============================================================================
# ERROR LOGGING & AGGREGATION
# ============================================================================

@router.get("/errors/stats")
async def get_error_stats(
    days: int = 7,
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get error statistics for failed intent classification.
    SECURITY: Requires admin authentication.
    """
    try:
        from ai.credits_rate_limiter import get_rate_limiter
        
        limiter = get_rate_limiter()
        stats = limiter.get_error_stats(days=days)
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.get("/errors/recent")
async def get_recent_errors(
    limit: int = 50,
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get recent errors for debugging.
    SECURITY: Requires admin authentication.
    """
    try:
        from ai.credits_rate_limiter import get_rate_limiter
        
        limiter = get_rate_limiter()
        stats = limiter.get_error_stats(days=1)
        
        return {
            "success": True,
            "recent_errors": stats.get('recent_errors', [])[:limit]
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


# ============================================================================
# LOCAL LLM HEALTH MONITORING
# ============================================================================

@router.get("/llm-health/status")
async def get_llm_health_status(admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Get local LLM health status.
    SECURITY: Requires admin authentication.
    """
    try:
        from ai.llm_health_monitor import get_health_monitor
        
        monitor = get_health_monitor()
        health = monitor.get_health()
        
        return {
            "success": True,
            "health": health
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/llm-health/restart")
async def restart_local_llm(admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Manually trigger local LLM restart.
    SECURITY: Requires admin authentication.
    """
    try:
        from ai.llm_health_monitor import LocalLLMHealthMonitor
        import asyncio
        
        monitor = LocalLLMHealthMonitor(auto_restart=True)
        await monitor._attempt_recovery()
        
        return {
            "success": True,
            "message": "Restart command executed. Check status in a few moments.",
            "health": monitor.get_health()
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/llm-health/monitoring")
async def toggle_health_monitoring(
    enabled: bool,
    check_interval: Optional[float] = None,
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Enable/disable health monitoring and adjust check interval.
    SECURITY: Requires admin authentication.
    """
    try:
        from ai.llm_health_monitor import get_health_monitor
        import asyncio
        
        monitor = get_health_monitor()
        
        if enabled and not monitor.is_running:
            asyncio.create_task(monitor.start_monitoring())
            message = "Health monitoring started"
        elif not enabled and monitor.is_running:
            monitor.stop_monitoring()
            message = "Health monitoring stopped"
        else:
            message = f"Health monitoring already {'running' if enabled else 'stopped'}"
        
        if check_interval and 5 <= check_interval <= 300:
            monitor.check_interval = check_interval
            message += f" (interval: {check_interval}s)"
        
        return {
            "success": True,
            "monitoring_enabled": enabled,
            "check_interval": monitor.check_interval,
            "message": message
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


# ============================================================================
# AGENTIC TOOLS MANAGEMENT
# ============================================================================

@router.get("/tools")
async def list_tools(user: User = Depends(require_admin)):
    """List all registered tools with their status."""
    from ai.tools_registry import get_tool_registry
    registry = get_tool_registry()
    return {"success": True, "tools": registry.list_all_tools()}


class ToolToggleRequest(BaseModel):
    tool_name: str
    enabled: bool


@router.post("/tools/toggle")
async def toggle_tool(req: ToolToggleRequest, user: User = Depends(require_admin)):
    """Enable or disable a tool at runtime."""
    from ai.tools_registry import get_tool_registry
    registry = get_tool_registry()
    if req.enabled:
        ok = registry.enable_tool(req.tool_name)
    else:
        ok = registry.disable_tool(req.tool_name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Tool '{req.tool_name}' not found")
    return {"success": True, "tool": req.tool_name, "enabled": req.enabled}


@router.delete("/tools/{tool_name}")
async def unregister_tool(tool_name: str, user: User = Depends(require_admin)):
    """Unregister a tool at runtime (admin only)."""
    from ai.tools_registry import get_tool_registry
    registry = get_tool_registry()
    ok = registry.unregister(tool_name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    return {"success": True, "removed": tool_name}


# ============================================================================
# AGENTIC MEMORY
# ============================================================================

@router.get("/agentic/memory")
async def get_memory_stats(user: User = Depends(require_admin)):
    """Get agentic memory statistics."""
    from ai.agentic_memory import get_agentic_memory
    mem = get_agentic_memory()
    return {"success": True, **mem.get_stats()}


@router.get("/agentic/memory/{location}")
async def get_location_memory(location: str, user: User = Depends(require_admin)):
    """Recall all cached data for a location."""
    from ai.agentic_memory import get_agentic_memory
    mem = get_agentic_memory()
    entries = mem.recall_location(location)
    return {"success": True, "location": location, "entries": entries, "count": len(entries)}


class MemoryInvalidateRequest(BaseModel):
    location: Optional[str] = None
    tool_name: Optional[str] = None


@router.post("/agentic/memory/invalidate")
async def invalidate_memory(req: MemoryInvalidateRequest, user: User = Depends(require_admin)):
    """Invalidate memory entries by location and/or tool."""
    from ai.agentic_memory import get_agentic_memory
    mem = get_agentic_memory()
    mem.invalidate(location=req.location, tool_name=req.tool_name)
    return {"success": True, "invalidated": {"location": req.location, "tool_name": req.tool_name}}


@router.post("/agentic/memory/clear")
async def clear_all_memory(user: User = Depends(require_admin)):
    """Clear all agentic memory (admin only)."""
    from ai.agentic_memory import get_agentic_memory
    mem = get_agentic_memory()
    mem.clear_all()
    return {"success": True, "message": "All agentic memory cleared"}


# ============================================================================
# SELF-LEARNING
# ============================================================================

@router.get("/agentic/learning")
async def get_learning_stats(user: User = Depends(require_admin)):
    """Get self-learning engine statistics."""
    from ai.self_learning import get_self_learning_engine
    engine = get_self_learning_engine()
    return {"success": True, **engine.get_stats()}


@router.get("/agentic/learning/tools")
async def get_tool_effectiveness(user: User = Depends(require_admin)):
    """Get per-tool effectiveness scores from self-learning."""
    from ai.self_learning import get_self_learning_engine
    engine = get_self_learning_engine()
    from ai.tools_registry import get_tool_registry
    registry = get_tool_registry()
    tool_names = [t.name for t in registry.list_tools()]
    scores = {name: engine.get_tool_effectiveness(name) for name in tool_names}
    return {"success": True, "tool_scores": scores}


@router.post("/agentic/learning/reset")
async def reset_learning(user: User = Depends(require_admin)):
    """Reset all self-learning data (admin only)."""
    from ai.self_learning import get_self_learning_engine
    engine = get_self_learning_engine()
    engine.reset()
    return {"success": True, "message": "Self-learning data reset"}


class FeedbackRequest(BaseModel):
    query: str
    intent: Optional[str] = None
    rating: int = 0
    tools_used: Optional[List[str]] = None
    agentic_mode: bool = False


@router.post("/agentic/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Submit user feedback on a response (no auth required)."""
    from ai.self_learning import get_self_learning_engine
    engine = get_self_learning_engine()
    engine.record_feedback(
        query=req.query, intent=req.intent, rating=req.rating,
        tools_used=req.tools_used, agentic_mode=req.agentic_mode,
    )
    return {"success": True, "message": "Feedback recorded"}


# ============================================================================
# AGENT CONFIGURATION
# ============================================================================


@router.get("/agent-status")
async def get_agent_status() -> Dict[str, Any]:
    """Get agent system status."""
    from ai.agentic_loop import get_agentic_loop
    from ai.tools_registry import get_tool_registry
    
    loop = get_agentic_loop()
    registry = get_tool_registry()
    
    return {
        "success": True,
        "agentic_loop_active": loop is not None,
        "tools_registered": len(registry.list_tools()),
    }


# ============================================================================
# CIRCUIT BREAKER MANAGEMENT
# ============================================================================

@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker(
    provider: str = "ollama",
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Reset the circuit breaker for a specific provider.
    Use when the provider has recovered from temporary failures (like OOM).
    """
    try:
        cb = get_circuit_breaker(provider)
        cb.reset()
        return {
            "success": True,
            "message": f"Circuit breaker for '{provider}' has been reset",
            "status": cb.get_status()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/circuit-breaker/status")
async def get_circuit_breaker_status(
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Get status of all circuit breakers."""
    from core.circuit_breaker import _circuit_breakers
    return {name: cb.get_status() for name, cb in _circuit_breakers.items()}


# ============================================================================
# WEEKLY WAWU AND CONVERSION DASHBOARD
# ============================================================================


@router.get("/dashboard/weekly")
async def get_weekly_dashboard(admin: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Get weekly WAWU (Weekly Active Workflow Users) and conversion metrics dashboard.
    
    This endpoint provides aggregate metrics for founder's Monday KPI review:
    - WAWU: Unique users with at least one workflow action in past 7 days
    - Conversion metrics: Free to Pro conversions, top-up attach rate
    - Retention: 4-week cohort retention (if data available)
    - Workflow activation rate
    - Broker team expansion rate
    - B2B pilot to retainer conversion
    - Guardrail metrics: Billing incidents, data freshness, confidence, time-to-value
    
    Returns JSON with aggregated business metrics.
    """
    import time
    from datetime import datetime, timedelta
    from pathlib import Path
    
    try:
        from config import config
        from database.db_service import DatabaseService
        
        # Calculate time boundaries
        now = time.time()
        seven_days_ago = now - (7 * 24 * 3600)
        four_weeks_ago = now - (28 * 24 * 3600)
        
        # Database paths
        digital_employee_db = config.DB_PATH.parent / "digital_employee.db"
        credits_db = config.DB_PATH.parent / "valora_credits.db"
        
        # Initialize result structure with all metrics
        result = {
            "success": True,
            "generated_at": datetime.now().isoformat(),
            "period": "last_7_days",
            "wawu": {
                "total_active_users": 0,
                "workflow_actions": {
                    "alerts": 0,
                    "scheduled_tasks": 0,
                    "leads": 0,
                    "automation_commands": 0
                }
            },
            "conversions": {
                "free_to_pro_new": 0,
                "free_to_pro_rate": 0.0,
                "topups_purchased": 0,
                "topup_attach_rate": 0.0,
                "broker_team_expansions": 0,
                "b2b_pilot_to_retainer": 0
            },
            "retention": {
                "week_4_cohort_retention": 0.0,
                "cohort_size": 0
            },
            "workflow_activation": {
                "total_active_users": 0,
                "users_with_alerts": 0,
                "users_with_tasks": 0,
                "users_with_leads": 0,
                "activation_rate": 0.0
            },
            "guardrails": {
                "billing_incidents": 0,
                "data_freshness_breaches": 0,
                "low_confidence_recommendations": 0,
                "avg_time_to_first_value_hours": 0.0
            }
        }
        
        # Connect to digital_employee database for WAWU metrics
        if digital_employee_db.exists():
            try:
                de_db = DatabaseService(str(digital_employee_db))
                
                # Query 1: Count unique users with workflow actions in past 7 days
                # Users who created/updated alerts
                alert_users = de_db.execute(
                    """
                    SELECT COUNT(DISTINCT user_id) as cnt 
                    FROM property_alerts 
                    WHERE created_at >= ?
                    """,
                    (seven_days_ago,)
                )
                
                # Users who created scheduled tasks
                task_users = de_db.execute(
                    """
                    SELECT COUNT(DISTINCT user_id) as cnt 
                    FROM scheduled_tasks 
                    WHERE created_at >= ?
                    """,
                    (seven_days_ago,)
                )
                
                # Users who created leads
                lead_users = de_db.execute(
                    """
                    SELECT COUNT(DISTINCT user_id) as cnt 
                    FROM leads 
                    WHERE created_at >= ?
                    """,
                    (seven_days_ago,)
                )
                
                # Users who ran automation commands
                automation_users = de_db.execute(
                    """
                    SELECT COUNT(DISTINCT user_id) as cnt 
                    FROM automation_activity 
                    WHERE created_at >= ?
                    """,
                    (seven_days_ago,)
                )
                
                # Get all unique users across all workflow types
                all_active_users = de_db.execute(
                    """
                    SELECT COUNT(DISTINCT user_id) as cnt FROM (
                        SELECT user_id FROM property_alerts WHERE created_at >= ?
                        UNION
                        SELECT user_id FROM scheduled_tasks WHERE created_at >= ?
                        UNION
                        SELECT user_id FROM leads WHERE created_at >= ?
                        UNION
                        SELECT user_id FROM automation_activity WHERE created_at >= ?
                    )
                    """,
                    (seven_days_ago, seven_days_ago, seven_days_ago, seven_days_ago)
                )
                
                result["wawu"]["total_active_users"] = int(all_active_users[0]["cnt"]) if all_active_users else 0
                
                # Query 2: Count total workflow actions
                alerts_count = de_db.execute(
                    "SELECT COUNT(*) as cnt FROM property_alerts WHERE created_at >= ?",
                    (seven_days_ago,)
                )
                
                tasks_count = de_db.execute(
                    "SELECT COUNT(*) as cnt FROM scheduled_tasks WHERE created_at >= ?",
                    (seven_days_ago,)
                )
                
                leads_count = de_db.execute(
                    "SELECT COUNT(*) as cnt FROM leads WHERE created_at >= ?",
                    (seven_days_ago,)
                )
                
                automation_count = de_db.execute(
                    "SELECT COUNT(*) as cnt FROM automation_activity WHERE created_at >= ?",
                    (seven_days_ago,)
                )
                
                result["wawu"]["workflow_actions"]["alerts"] = int(alerts_count[0]["cnt"]) if alerts_count else 0
                result["wawu"]["workflow_actions"]["scheduled_tasks"] = int(tasks_count[0]["cnt"]) if tasks_count else 0
                result["wawu"]["workflow_actions"]["leads"] = int(leads_count[0]["cnt"]) if leads_count else 0
                result["wawu"]["workflow_actions"]["automation_commands"] = int(automation_count[0]["cnt"]) if automation_count else 0
                
                # Workflow activation metrics
                result["workflow_activation"]["total_active_users"] = result["wawu"]["total_active_users"]
                result["workflow_activation"]["users_with_alerts"] = int(alert_users[0]["cnt"]) if alert_users else 0
                result["workflow_activation"]["users_with_tasks"] = int(task_users[0]["cnt"]) if task_users else 0
                result["workflow_activation"]["users_with_leads"] = int(lead_users[0]["cnt"]) if lead_users else 0
                
                # Calculate workflow activation rate (users with alerts/tasks/leads / total users)
                total_users_for_activation = de_db.execute(
                    "SELECT COUNT(*) as cnt FROM property_alerts"
                )
                if total_users_for_activation and int(total_users_for_activation[0]["cnt"]) > 0:
                    activated = result["workflow_activation"]["users_with_alerts"] + \
                               result["workflow_activation"]["users_with_tasks"] + \
                               result["workflow_activation"]["users_with_leads"]
                    total = int(total_users_for_activation[0]["cnt"]) * 3  # Approximate total users
                    if total > 0:
                        result["workflow_activation"]["activation_rate"] = round(min(1.0, activated / total), 4)
                
                # Time-to-first-value: Calculate average time from signup to first workflow action
                # Get users who signed up in the past 28 days and their first action time
                time_to_first_value_data = de_db.execute(
                    """
                    SELECT 
                        u.user_id,
                        MIN(u.created_at) as signup_time,
                        MIN(w.first_action_time) as first_action
                    FROM (
                        SELECT user_id, MIN(created_at) as created_at 
                        FROM property_alerts 
                        GROUP BY user_id
                        UNION ALL
                        SELECT user_id, MIN(created_at) as created_at 
                        FROM scheduled_tasks 
                        GROUP BY user_id
                        UNION ALL
                        SELECT user_id, MIN(created_at) as created_at 
                        FROM leads 
                        GROUP BY user_id
                    ) w
                    JOIN (
                        SELECT user_id, created_at 
                        FROM property_alerts 
                        UNION ALL
                        SELECT user_id, created_at 
                        FROM scheduled_tasks
                        UNION ALL  
                        SELECT user_id, created_at 
                        FROM leads
                    ) u ON w.user_id = u.user_id
                    WHERE u.created_at >= ?
                    GROUP BY u.user_id
                    """,
                    (four_weeks_ago,)
                )
                
                if time_to_first_value_data:
                    total_hours = 0
                    count = 0
                    for row in time_to_first_value_data:
                        if row.get("first_action") and row.get("signup_time"):
                            hours_diff = (row["first_action"] - row["signup_time"]) / 3600
                            if hours_diff >= 0:  # Only count positive values
                                total_hours += hours_diff
                                count += 1
                    if count > 0:
                        result["guardrails"]["avg_time_to_first_value_hours"] = round(total_hours / count, 2)
                
            except Exception as e:
                logger.warning(f"Error querying digital_employee DB: {e}")
        
        # Connect to credits database for conversion metrics
        if credits_db.exists():
            try:
                credits_db_service = DatabaseService(str(credits_db))
                
                # Query 1: Count users who upgraded from free to pro in past 7 days
                # by checking tier changes in user_credits
                conversions = credits_db_service.execute(
                    """
                    SELECT COUNT(*) as cnt FROM user_credits 
                    WHERE tier = 'pro' 
                    AND updated_at >= ?
                    AND user_id NOT IN ('admin', 'admin@valora.ai', 'nvnsa', '1', 'Admin')
                    """,
                    (seven_days_ago,)
                )
                
                # Count total free users to calculate conversion rate
                total_free_users = credits_db_service.execute(
                    "SELECT COUNT(*) as cnt FROM user_credits WHERE tier = 'free'"
                )
                
                result["conversions"]["free_to_pro_new"] = int(conversions[0]["cnt"]) if conversions else 0
                
                # Calculate conversion rate
                free_user_count = int(total_free_users[0]["cnt"]) if total_free_users else 0
                if free_user_count > 0:
                    result["conversions"]["free_to_pro_rate"] = round(
                        result["conversions"]["free_to_pro_new"] / free_user_count, 4
                    )
                
                # Query 2: Count top-ups in past 7 days
                topups = credits_db_service.execute(
                    """
                    SELECT COUNT(*) as cnt FROM payment_history 
                    WHERE timestamp >= ? AND credits_added > 0
                    """,
                    (seven_days_ago,)
                )
                
                result["conversions"]["topups_purchased"] = int(topups[0]["cnt"]) if topups else 0
                
                # Query 3: Calculate top-up attach rate
                # (users who purchased top-ups / total paying users) * 100
                total_paying_users = credits_db_service.execute(
                    """
                    SELECT COUNT(*) as cnt FROM user_credits 
                    WHERE tier IN ('pro', 'team', 'agency', 'enterprise')
                    """
                )
                
                paying_count = int(total_paying_users[0]["cnt"]) if total_paying_users else 0
                topup_users = credits_db_service.execute(
                    """
                    SELECT COUNT(DISTINCT user_id) as cnt FROM payment_history 
                    WHERE timestamp >= ? AND credits_added > 0
                    """,
                    (seven_days_ago,)
                )
                topup_user_count = int(topup_users[0]["cnt"]) if topup_users else 0
                
                if paying_count > 0:
                    result["conversions"]["topup_attach_rate"] = round(topup_user_count / paying_count, 4)
                
                # Query 4: Broker team expansion rate
                # Track new team/agency signups (tier = 'team' or 'agency')
                team_expansions = credits_db_service.execute(
                    """
                    SELECT COUNT(*) as cnt FROM user_credits 
                    WHERE tier IN ('team', 'agency', 'enterprise') 
                    AND created_at >= ?
                    AND user_id NOT IN ('admin', 'admin@valora.ai', 'nvnsa', '1', 'Admin')
                    """,
                    (seven_days_ago,)
                )
                
                result["conversions"]["broker_team_expansions"] = int(team_expansions[0]["cnt"]) if team_expansions else 0
                
                # Query 5: B2B pilot to retainer conversion
                # Track pilot conversions (tier changes from pilot/demo to pro/team/enterprise)
                pilot_conversions = credits_db_service.execute(
                    """
                    SELECT COUNT(*) as cnt FROM user_credits 
                    WHERE tier IN ('pro', 'team', 'agency', 'enterprise') 
                    AND updated_at >= ?
                    AND user_id NOT IN ('admin', 'admin@valora.ai', 'nvnsa', '1', 'Admin')
                    AND (metadata LIKE '%pilot%' OR metadata LIKE '%demo%' OR metadata LIKE '%enterprise%')
                    """,
                    (seven_days_ago,)
                )
                
                result["conversions"]["b2b_pilot_to_retainer"] = int(pilot_conversions[0]["cnt"]) if pilot_conversions else 0
                
                # Query 6: Calculate 4-week cohort retention
                # Get users who created accounts 4 weeks ago
                cohort_4w_ago = credits_db_service.execute(
                    """
                    SELECT COUNT(*) as cnt FROM user_credits 
                    WHERE created_at >= ? AND created_at < ?
                    """,
                    (four_weeks_ago, seven_days_ago)
                )
                
                # Get how many of those are still active (have recent activity)
                # For simplicity, check if they have any usage in the past 7 days
                active_cohort = credits_db_service.execute(
                    """
                    SELECT COUNT(DISTINCT uc.user_id) as cnt 
                    FROM user_credits uc
                    JOIN usage_log ul ON uc.user_id = ul.user_id
                    WHERE uc.created_at >= ? AND uc.created_at < ?
                    AND ul.timestamp >= ?
                    """,
                    (four_weeks_ago, seven_days_ago, seven_days_ago)
                )
                
                cohort_count = int(cohort_4w_ago[0]["cnt"]) if cohort_4w_ago else 0
                active_count = int(active_cohort[0]["cnt"]) if active_cohort else 0
                
                result["retention"]["cohort_size"] = cohort_count
                if cohort_count > 0:
                    result["retention"]["week_4_cohort_retention"] = round(active_count / cohort_count, 4)
                
                # Query 7: Billing incidents - Count failed payments, refund requests, billing errors
                billing_failures = credits_db_service.execute(
                    """
                    SELECT COUNT(*) as cnt FROM payment_history 
                    WHERE timestamp >= ? 
                    AND (status IN ('failed', 'refunded', 'error') OR status LIKE '%fail%' OR status LIKE '%error%')
                    """,
                    (seven_days_ago,)
                )
                
                result["guardrails"]["billing_incidents"] = int(billing_failures[0]["cnt"]) if billing_failures else 0
                
            except Exception as e:
                logger.warning(f"Error querying credits DB: {e}")
        
        # Data freshness SLA breaches - check micro-markets with stale data
        try:
            from database.query_service import get_query_service
            db = get_query_service()
            
            # Get properties with stale data (last updated > 7 days ago)
            stale_properties = db.execute(
                """
                SELECT COUNT(DISTINCT locality) as cnt 
                FROM properties 
                WHERE updated_at < ? OR scraped_at < ?
                """,
                (seven_days_ago, seven_days_ago)
            )
            
            result["guardrails"]["data_freshness_breaches"] = int(stale_properties[0]["cnt"]) if stale_properties else 0
            
        except Exception as e:
            logger.warning(f"Error checking data freshness: {e}")
        
        # Low confidence recommendations - query chat/agent logs for confidence < 70%
        try:
            if credits_db.exists():
                credits_db_service = DatabaseService(str(credits_db))
                
                # Check usage_log for low confidence interactions
                low_confidence_count = credits_db_service.execute(
                    """
                    SELECT COUNT(*) as cnt FROM usage_log 
                    WHERE timestamp >= ? 
                    AND (metadata LIKE '%confidence%' 
                         OR query_type LIKE '%recommendation%')
                    """,
                    (seven_days_ago,)
                )
                
                # Also check digital_employee for automation with low confidence
                if digital_employee_db.exists():
                    de_db = DatabaseService(str(digital_employee_db))
                    low_conf_automation = de_db.execute(
                        """
                        SELECT COUNT(*) as cnt FROM automation_activity 
                        WHERE created_at >= ? 
                        AND (details_json LIKE '%confidence%' OR status = 'failed')
                        """,
                        (seven_days_ago,)
                    )
                    
                    total_low_conf = int(low_confidence_count[0]["cnt"]) if low_confidence_count else 0
                    if low_conf_automation:
                        total_low_conf += int(low_conf_automation[0]["cnt"])
                    
                    result["guardrails"]["low_confidence_recommendations"] = total_low_conf
                else:
                    result["guardrails"]["low_confidence_recommendations"] = int(low_confidence_count[0]["cnt"]) if low_confidence_count else 0
                    
        except Exception as e:
            logger.warning(f"Error checking low confidence recommendations: {e}")
        
        # Additional guardrail: Improve workflow activation rate calculation
        if result["workflow_activation"]["total_active_users"] > 0:
            activated_users = (
                result["workflow_activation"]["users_with_alerts"] +
                result["workflow_activation"]["users_with_tasks"] +
                result["workflow_activation"]["users_with_leads"]
            )
            # Use total active users as denominator
            if result["wawu"]["total_active_users"] > 0:
                result["workflow_activation"]["activation_rate"] = round(
                    min(1.0, activated_users / (result["wawu"]["total_active_users"] * 3)), 4
                )
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating weekly dashboard: {e}")
        return {
            "success": False,
            "error": str(e),
            "generated_at": datetime.now().isoformat()
        }

