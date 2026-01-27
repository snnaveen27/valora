"""
Admin API Routes
System management, monitoring, and configuration endpoints
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
import time
import asyncio
import httpx
import json
from pathlib import Path

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ============================================================================
# ADMIN CONFIG (PERSISTENT SETTINGS)
# ============================================================================

ADMIN_CONFIG_FILE = Path(__file__).parent / 'admin_config.json'


def _load_admin_config() -> dict:
    """Load admin config from file."""
    defaults = {
        "vector_backend": "pinecone",
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
_vector_backend = _admin_config.get("vector_backend", "pinecone")

# Processing jobs tracker
_active_jobs = []


class VectorBackendRequest(BaseModel):
    backend: str  # "pinecone" or "faiss"


class IndexingRequest(BaseModel):
    target: str  # "pinecone" or "faiss"


class LLMConfigRequest(BaseModel):
    provider: str  # "openrouter" or "local"
    openrouter_api_key: Optional[str] = ""
    openrouter_model: Optional[str] = "meta-llama/llama-3.2-3b-instruct:free"
    local_url: Optional[str] = "http://127.0.0.1:11434/v1/chat/completions"
    local_model: Optional[str] = "llama3.2"


class SanityCheckRequest(BaseModel):
    base_url: Optional[str] = "http://localhost:8000"
    include_chat: Optional[bool] = False


@router.get("/status")
async def get_system_status() -> Dict[str, Any]:
    """Get comprehensive system status."""
    status = {
        "backend": {"status": "healthy", "fastapi": True},
        "database": {"status": "unknown"},
        "pinecone": {"status": "unknown"},
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
        from pathlib import Path
        
        db = get_query_service()
        db_path = Path(__file__).parent / 'database' / '..' / '..' / 'src' / 'data' / 'valora.db'
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
    
    # Check Pinecone
    try:
        from rag_service import get_rag_service
        rag = get_rag_service()
        
        if rag.index:
            stats = rag.index.describe_index_stats()
            status["pinecone"] = {
                "status": "healthy",
                "vectors": stats.total_vector_count,
                "index": "valora-realestate"
            }
        else:
            status["pinecone"] = {"status": "degraded", "vectors": 0}
    except Exception as e:
        status["pinecone"] = {"status": "down", "error": str(e)}
    
    # Check FAISS
    try:
        from local_vector_store import get_local_store, FAISS_AVAILABLE
        
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
        from rag_service import EMBEDDINGS_AVAILABLE
        from advanced_reasoning import AdvancedReasoningEngine
        
        status["ai"] = {
            "status": "healthy",
            "embeddings": EMBEDDINGS_AVAILABLE,
            "reasoning": True
        }
    except Exception as e:
        status["ai"] = {"status": "degraded", "error": str(e)}
    
    # Check cache
    try:
        from query_cache import get_rag_cache
        cache = get_rag_cache()
        cache_stats = cache.get_stats()
        
        status["cache"] = {
            "status": "healthy",
            "entries": cache_stats.get("size", 0),
            "hitRate": int(cache_stats.get("hit_rate", 0) * 100)
        }
    except Exception as e:
        status["cache"] = {"status": "degraded", "entries": 0, "hitRate": 0}
    
    return status


@router.get("/vector-backend")
async def get_vector_backend() -> Dict[str, str]:
    """Get current vector search backend."""
    global _vector_backend
    return {"backend": _vector_backend}


@router.post("/vector-backend")
async def set_vector_backend(request: VectorBackendRequest) -> Dict[str, Any]:
    """Set vector search backend (pinecone or faiss)."""
    global _vector_backend
    
    if request.backend not in ["pinecone", "faiss"]:
        return {"success": False, "error": "Invalid backend. Use 'pinecone' or 'faiss'"}
    
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
        from rag_service import get_rag_service
        rag = get_rag_service()
        rag.prefer_faiss = (request.backend == "faiss")
    except:
        pass
    
    return {"success": True, "backend": _vector_backend}


@router.post("/run-tests")
async def run_system_tests() -> Dict[str, Any]:
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
    
    # Test 2: Pinecone connection
    test_start = time.time()
    try:
        from rag_service import get_rag_service
        rag = get_rag_service()
        if rag.index:
            stats = rag.index.describe_index_stats()
            tests.append({
                "name": "Pinecone Connection",
                "description": f"Connected with {stats.total_vector_count:,} vectors",
                "passed": True,
                "duration": int((time.time() - test_start) * 1000)
            })
        else:
            tests.append({
                "name": "Pinecone Connection",
                "description": "Index not initialized",
                "passed": False,
                "duration": int((time.time() - test_start) * 1000)
            })
    except Exception as e:
        tests.append({
            "name": "Pinecone Connection",
            "description": str(e),
            "passed": False,
            "duration": int((time.time() - test_start) * 1000)
        })
    
    # Test 3: FAISS availability
    test_start = time.time()
    try:
        from local_vector_store import get_local_store, FAISS_AVAILABLE
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
        from rag_service import get_rag_service
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
        from rag_service import get_rag_service
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
    
    # Test 7: Advanced Reasoning
    test_start = time.time()
    try:
        from advanced_reasoning import AdvancedReasoningEngine
        engine = AdvancedReasoningEngine()
        tests.append({
            "name": "Reasoning Engine",
            "description": "Engine initialized successfully",
            "passed": True,
            "duration": int((time.time() - test_start) * 1000)
        })
    except Exception as e:
        tests.append({
            "name": "Reasoning Engine",
            "description": str(e),
            "passed": False,
            "duration": int((time.time() - test_start) * 1000)
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


@router.post("/sanity-check")
async def run_realtime_sanity_check(request: SanityCheckRequest) -> Dict[str, Any]:
    tests = []
    start_time = time.time()

    base_url = (request.base_url or "http://localhost:8000").rstrip("/")

    async def _run(name: str, fn):
        t0 = time.time()
        try:
            passed, description, details = await fn()
            tests.append({
                "name": name,
                "description": description,
                "passed": bool(passed),
                "duration": int((time.time() - t0) * 1000),
                "details": details,
                "skipped": False,
            })
        except Exception as e:
            tests.append({
                "name": name,
                "description": f"{name} failed: {e}",
                "passed": False,
                "duration": int((time.time() - t0) * 1000),
                "details": None,
                "skipped": False,
            })

    async def _skip(name: str, description: str):
        tests.append({
            "name": name,
            "description": description,
            "passed": True,
            "duration": 0,
            "details": None,
            "skipped": True,
        })

    async with httpx.AsyncClient(timeout=20.0) as client:
        async def health():
            r = await client.get(f"{base_url}/health")
            r.raise_for_status()
            data = r.json()
            ok = isinstance(data, dict) and bool(data)
            return ok, "GET /health", {"status": data.get("status"), "nominatim": data.get("nominatim")}

        async def admin_status():
            r = await client.get(f"{base_url}/api/admin/status")
            r.raise_for_status()
            data = r.json()
            ok = isinstance(data, dict) and isinstance(data.get("backend"), dict) and isinstance(data.get("database"), dict)
            return ok, "GET /api/admin/status", {"backend": data.get("backend"), "database": data.get("database")}

        async def tileset():
            r = await client.get(f"{base_url}/api/tileset")
            r.raise_for_status()
            data = r.json()
            ok = isinstance(data, dict)
            return ok, "GET /api/tileset", {"keys": list(data.keys())[:10]}

        async def tiles_viewport():
            params = {"min_lng": 77.55, "min_lat": 12.90, "max_lng": 77.70, "max_lat": 13.05}
            r = await client.get(f"{base_url}/api/tiles/viewport", params=params)
            r.raise_for_status()
            data = r.json()
            ok = isinstance(data, dict) and isinstance(data.get("tiles"), list)
            return ok, "GET /api/tiles/viewport", {"total": data.get("total"), "tiles": len(data.get("tiles") or [])}

        async def viewport_analyze():
            r = await client.get(f"{base_url}/api/viewport/analyze", params={"lat": 12.9716, "lng": 77.5946})
            r.raise_for_status()
            data = r.json()
            ok = isinstance(data, dict) and isinstance(data.get("spatial"), dict)
            return ok, "GET /api/viewport/analyze", {"area_name": data.get("area_name")}

        async def location_analyze():
            r = await client.post(f"{base_url}/api/location/analyze", json={"lat": 12.9716, "lng": 77.5946})
            r.raise_for_status()
            data = r.json()
            ok = isinstance(data, dict) and (data.get("success") is True or "market" in data or "spatial" in data)
            return ok, "POST /api/location/analyze", {"keys": list(data.keys())[:10]}

        async def city_intel():
            r = await client.get(f"{base_url}/api/city-intelligence/locality/Indiranagar")
            r.raise_for_status()
            data = r.json()
            ok = isinstance(data, dict) and isinstance(data.get("profile"), dict)
            return ok, "GET /api/city-intelligence/locality/Indiranagar", {"has_profile": bool(data.get("profile"))}

        async def chat():
            payload = {"message": "Analyze Koramangala for investment and explain why.", "session_id": "admin_sanity"}
            r = await client.post(f"{base_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
            ok = bool(data.get("success")) and isinstance(data.get("message"), str)
            return ok, "POST /api/chat", {
                "intent": data.get("intent"),
                "has_facts": isinstance(data.get("facts"), dict),
                "has_storyboard": bool(data.get("storyboard")),
            }

        async def investment_leaderboard():
            r = await client.get(f"{base_url}/api/investment/leaderboard", params={"limit": 5})
            r.raise_for_status()
            data = r.json()
            ok = isinstance(data, dict) and isinstance(data.get("leaderboard"), list)
            return ok, "GET /api/investment/leaderboard", {"count": len(data.get("leaderboard", []))}

        async def storyboard_gen():
            payload = {"scenario": "Analyze Koramangala", "duration_seconds": 15}
            r = await client.post(f"{base_url}/api/storyboard/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            ok = isinstance(data, dict) and isinstance(data.get("storyboard"), dict)
            return ok, "POST /api/storyboard/generate", {"scenes": len(data.get("storyboard", {}).get("scenes", []))}

        async def compare_props():
            payload = {"localities": ["Koramangala", "Indiranagar"]}
            r = await client.post(f"{base_url}/api/compare/properties", json=payload)
            r.raise_for_status()
            data = r.json()
            ok = isinstance(data, dict) and isinstance(data.get("comparison"), list)
            return ok, "POST /api/compare/properties", {"count": len(data.get("comparison", []))}

        await _run("Backend Health", health)
        await _run("Admin Status", admin_status)
        await _run("Tileset Index", tileset)
        await _run("Tiles Viewport", tiles_viewport)
        await _run("Viewport Analyze", viewport_analyze)
        await _run("Location Analyze", location_analyze)
        await _run("City Intelligence", city_intel)
        await _run("Investment Leaderboard", investment_leaderboard)
        await _run("Storyboard Generation", storyboard_gen)
        await _run("Compare Properties", compare_props)

        if request.include_chat:
            await _run("Chat Orchestration", chat)
        else:
            await _skip("Chat Orchestration", "Skipped (include_chat=false)")

    passed = sum(1 for t in tests if t.get("passed") and not t.get("skipped"))
    failed = sum(1 for t in tests if (not t.get("passed")) and not t.get("skipped"))
    skipped = sum(1 for t in tests if t.get("skipped"))

    return {
        "base_url": base_url,
        "tests": tests,
        "total": len(tests),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration_ms": int((time.time() - start_time) * 1000),
    }


@router.get("/processing-status")
async def get_processing_status() -> Dict[str, Any]:
    """Get status of active processing jobs."""
    global _active_jobs
    return {"jobs": _active_jobs}


@router.post("/trigger-indexing")
async def trigger_indexing(request: IndexingRequest) -> Dict[str, Any]:
    """Trigger indexing job (Pinecone or FAISS)."""
    global _active_jobs
    
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

LLM_CONFIG_FILE = Path(__file__).parent / 'llm_config.json'

def _load_llm_config() -> dict:
    """Load LLM config from file."""
    import os
    defaults = {
        'provider': 'openrouter',
        'openrouter_api_key': os.getenv('OPENROUTER_API_KEY', ''),
        'openrouter_model': os.getenv('OPENROUTER_MODEL', 'meta-llama/llama-3.2-3b-instruct:free'),
        'local_url': os.getenv('LOCAL_LLM_URL', 'http://127.0.0.1:11434/v1/chat/completions'),
        'local_model': os.getenv('LOCAL_LLM_MODEL', 'llama3.2')
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
    """Set LLM configuration."""
    # Load existing config to preserve API key if masked
    existing = _load_llm_config()
    
    config = {
        'provider': request.provider,
        'openrouter_model': request.openrouter_model,
        'local_url': request.local_url,
        'local_model': request.local_model
    }
    
    # Only update API key if it's a real key (not masked)
    incoming_key = request.openrouter_api_key
    if incoming_key and isinstance(incoming_key, str) and incoming_key.startswith('...'):
        incoming_key = ""
    if incoming_key and isinstance(incoming_key, str) and incoming_key.strip():
        config['openrouter_api_key'] = incoming_key.strip()
    else:
        config['openrouter_api_key'] = existing.get('openrouter_api_key', '')
    
    if _save_llm_config(config):
        return {"success": True, "message": "Configuration saved"}
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
