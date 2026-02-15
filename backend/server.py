"""
Valora AI Backend Server
- Geocoding via local Nominatim
- Place resolution for GIS AI Agent
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import statistics
import math
import httpx
import json
from pathlib import Path
from collections import OrderedDict
import time
import os
from dotenv import load_dotenv

# Structured logging (before any other imports that might log)
from logging_config import setup_logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("valora.server")

from analyzers.area_analyzer import AreaAnalyzer
from spatial.local_geocoder import get_local_geocoder
from config import config
from scrapers import multi_source_scraper

# Load environment variables
load_dotenv()

# Initialize services - gracefully handle missing folders (database is primary source)
osm_data_dir = config.OSM_DATA_DIR
terrain_dir = config.TERRAIN_DIR
properties_dir = config.POSTED_PROPERTIES_DIR

# Area analyzer and geocoder use database as primary, files as fallback
try:
    area_analyzer = AreaAnalyzer(osm_data_dir)
    print("[OK] Area analyzer initialized (uses database)")
except Exception as e:
    print(f"[WARNING] Area analyzer not available: {e}")
    area_analyzer = None

try:
    local_geocoder = get_local_geocoder(osm_data_dir)
    print("[OK] Local geocoder initialized (uses database)")
except Exception as e:
    print(f"[WARNING] Local geocoder not available: {e}")
    local_geocoder = None

# Import and initialize terrain service (optional - terrain folder may not exist)
try:
    from spatial.terrain_service import TerrainService
    terrain_service = TerrainService(terrain_dir)
    print("[OK] Terrain service initialized")
except Exception as e:
    print(f"[WARNING] Terrain service not available: {e}")
    terrain_service = None

# Import and initialize property service (uses database, folder is optional)
try:
    from services.property_service import get_property_service
    property_service = get_property_service(properties_dir)
    print("[OK] Property service initialized (uses database)")
except Exception as e:
    print(f"[WARNING] Property service not available: {e}")
    property_service = None

# Phase 1: Import and initialize RAG, Valuation, and Spatial Reasoning services
data_dir = config.STORAGE_DIR
faiss_dir = config.FAISS_DIR

try:
    from ai.rag_service import get_rag_service
    rag_service = get_rag_service(faiss_dir)
    RAG_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] RAG service not available: {e}")
    rag_service = None
    RAG_AVAILABLE = False

# Import and initialize simulation & digital twin
try:
    from intelligence.simulation_engine import get_simulation_engine, ScenarioInput
    from intelligence.narrative_generator import get_narrative_generator
    from engines.digital_twin import get_digital_twin, StateChange
    simulation_engine = get_simulation_engine()
    narrative_generator = get_narrative_generator()
    digital_twin = get_digital_twin(data_dir)
    SIMULATION_AVAILABLE = True
    print("[OK] Simulation & Digital Twin engines initialized")
except Exception as e:
    print(f"[WARNING] Simulation/Digital Twin not available: {e}")
    simulation_engine = None
    narrative_generator = None
    digital_twin = None
    SIMULATION_AVAILABLE = False

try:
    from intelligence.valuation_model import get_valuation_model
    valuation_model = get_valuation_model(data_dir)
    VALUATION_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] Valuation model not available: {e}")
    valuation_model = None
    VALUATION_AVAILABLE = False

try:
    from spatial.spatial_reasoning import get_spatial_service
    spatial_service = get_spatial_service(data_dir)
    SPATIAL_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] Spatial reasoning not available: {e}")
    spatial_service = None
    SPATIAL_AVAILABLE = False

# Phase 2: GIS Multi-Agent Orchestrator
from ai.gis_agents import get_gis_orchestrator, IntentRouter, Intent, _compute_market_facts
from search.query_cache import get_chat_cache

# Ollama client (lazy-loaded by chat_routes.py)
try:
    from ai.ollama_client import get_ollama_client
    print("[OK] Ollama client module available")
except ImportError:
    print("[WARNING] Ollama client not available")

# Phase 3: City Intelligence Engine
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent / 'city_intelligence'))
    from city_intelligence.locality_personality import get_locality_personality_model, LocalityProfile
    from city_intelligence.evolution_timeline import get_evolution_timeline_system
    from city_intelligence.risk_indexes import get_risk_index_calculator
    from city_intelligence.knowledge_graph import get_urban_knowledge_graph
    from city_intelligence.causal_reasoning import get_causal_reasoning_engine
    from city_intelligence.prediction_schema import get_prediction_builder, PredictionDomain, TimeHorizon
    CITY_INTELLIGENCE_AVAILABLE = True
    print("[OK] City Intelligence Engine initialized")
except Exception as e:
    print(f"[WARNING] City Intelligence not available: {e}")
    CITY_INTELLIGENCE_AVAILABLE = False
gis_orchestrator = get_gis_orchestrator(
    geocoder=local_geocoder,
    spatial_service=spatial_service,
    terrain_service=terrain_service,
    property_service=property_service,
    valuation_model=valuation_model,
    rag_service=rag_service,
    area_analyzer=area_analyzer,
)
print("[OK] GIS Multi-Agent Orchestrator initialized")

app = FastAPI(title="Valora AI Backend", version="2.0.0")

# Include admin routes
from routes.admin_routes import router as admin_router, get_active_llm_config
app.include_router(admin_router)

# Include auth routes
from routes.auth_routes import router as auth_router
app.include_router(auth_router)
print("[OK] Auth routes initialized")

# Include payment routes
from routes.payment_routes import router as payment_router
app.include_router(payment_router)
print("[OK] Payment routes initialized (Razorpay + Cashfree)")

# Include feedback routes
from routes.feedback_routes import router as feedback_router
app.include_router(feedback_router)
print("[OK] Feedback routes initialized (auto-save + credit rewards)")

# Include unified chat routes (replaces /api/chat, /api/chat/stream, /api/chat/hybrid, /api/chat/stream-opus)
from routes.chat_routes import router as chat_router, init_chat_deps
app.include_router(chat_router)
init_chat_deps(gis_orchestrator=gis_orchestrator)
print("[OK] Unified chat routes initialized (2 endpoints: /api/chat + /api/chat/stream)")

# Include credits & demo payment routes
from routes.credits_routes import router as credits_router
app.include_router(credits_router)
print("[OK] Credits & demo payment routes initialized")

# CORS for frontend
_default_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
]
def _parse_origins(value: str) -> list[str]:
    if not value:
        return []
    value = value.strip()
    if value.startswith("["):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(o).strip() for o in parsed if str(o).strip()]
        except json.JSONDecodeError:
            pass
    return [o.strip() for o in value.split(",") if o.strip()]

_origins_env = (
    os.getenv("FRONTEND_ORIGINS")
    or os.getenv("CORS_ORIGINS")
    or os.getenv("ALLOWED_ORIGINS")
    or ""
)
_allowed_origins = _parse_origins(_origins_env) or _default_origins

# Security: Validate origins to prevent CORS bypass
_validated_origins = []
for origin in _allowed_origins:
    if origin.startswith(("http://localhost:", "http://127.0.0.1:", "https://")):
        _validated_origins.append(origin)
    else:
        print(f"[WARNING] Rejected invalid origin: {origin}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_validated_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicit methods
    allow_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    if os.getenv("LOG_REQUEST_TIMINGS", "1") == "1":
        print(f"{request.method} {request.url.path} {response.status_code} {elapsed_ms:.1f}ms")
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
    return response

@app.on_event("startup")
async def startup_event():
    """Load tileset index on app startup"""
    load_tileset_index()

# Tileset index for tile-based loading
tileset_index = None

class TTLCache:
    def __init__(self, maxsize: int = 512, ttl_seconds: int = 300):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._store: "OrderedDict[str, tuple[Any, float]]" = OrderedDict()

    def get(self, key: str):
        item = self._store.get(key)
        if not item:
            return None
        value, expires_at = item
        if expires_at < time.time():
            try:
                del self._store[key]
            except KeyError:
                pass
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: Any):
        now = time.time()
        self._store[key] = (value, now + self.ttl_seconds)
        self._store.move_to_end(key)
        while len(self._store) > self.maxsize:
            self._store.popitem(last=False)

_cache_geocode = TTLCache(maxsize=1024, ttl_seconds=3600)
_cache_geocode_local = TTLCache(maxsize=1024, ttl_seconds=3600)
_cache_area_analyze = TTLCache(maxsize=512, ttl_seconds=300)
_cache_terrain_elevation = TTLCache(maxsize=4096, ttl_seconds=86400)
_cache_terrain_analysis = TTLCache(maxsize=2048, ttl_seconds=3600)
_cache_terrain_stats = TTLCache(maxsize=1, ttl_seconds=3600)
_cache_properties_categories = TTLCache(maxsize=1, ttl_seconds=3600)
_cache_properties_area_stats = TTLCache(maxsize=1024, ttl_seconds=900)
_cache_properties_nearby = TTLCache(maxsize=2048, ttl_seconds=300)
_cache_properties_search = TTLCache(maxsize=2048, ttl_seconds=300)

# Phase 1 caches
_cache_spatial_nearby = TTLCache(maxsize=2048, ttl_seconds=300)
_cache_spatial_summary = TTLCache(maxsize=1024, ttl_seconds=300)
_cache_valuation = TTLCache(maxsize=1024, ttl_seconds=600)
_cache_rag_search = TTLCache(maxsize=512, ttl_seconds=300)

# Note: Market computation logic moved to gis_agents.py for Phase 2 multi-agent orchestration

def load_tileset_index():
    """Load tileset index - use cached tileset.json for production performance"""
    global tileset_index
    
    storage_dir = Path(__file__).parent.parent / 'storage'
    cached_tileset_path = storage_dir / 'tileset.json'
    
    # Try to load cached tileset first (fastest)
    if cached_tileset_path.exists():
        try:
            with open(cached_tileset_path, 'r') as f:
                tileset_index = json.load(f)
            total_buildings = sum(t.get('count', 0) for t in tileset_index.get('tiles', {}).values())
            print(f"[OK] Loaded cached tileset: {len(tileset_index['tiles'])} tiles, {total_buildings} buildings")
            return
        except Exception as e:
            print(f"[WARNING] Failed to load cached tileset: {e}")
    
    # Try database and generate tileset
    try:
        from database.query_service import get_query_service
        query_service = get_query_service()
        
        # Check if database has buildings
        test_query = query_service.db.execute(
            "SELECT COUNT(*) as cnt FROM buildings WHERE latitude IS NOT NULL AND longitude IS NOT NULL LIMIT 1"
        )
        has_buildings = test_query[0]['cnt'] > 0 if test_query else False
        
        if has_buildings:
            print("[INFO] Generating tileset from database...")
            tiles = {}
            tile_size = 0.01
            
            # Get all building counts by tile in one query
            count_data = query_service.db.execute("""
                SELECT 
                    CAST(longitude * 100 AS INTEGER) as lng_idx,
                    CAST(latitude * 100 AS INTEGER) as lat_idx,
                    COUNT(*) as cnt
                FROM buildings 
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                GROUP BY lng_idx, lat_idx
            """)
            
            count_lookup = {f"{row['lng_idx']}_{row['lat_idx']}": row['cnt'] for row in count_data}
            
            for lng_start in range(7740, 7780):
                for lat_start in range(1280, 1310):
                    lng = lng_start / 100
                    lat = lat_start / 100
                    tile_id = f"{lng_start}_{lat_start}"
                    count = count_lookup.get(tile_id, 0)
                    
                    tiles[tile_id] = {
                        'min_lng': lng, 'max_lng': lng + tile_size,
                        'min_lat': lat, 'max_lat': lat + tile_size,
                        'max_height': 30, 'count': count
                    }
            
            tileset_index = {
                'tiles': tiles,
                'totalBuildings': query_service.get_database_stats().get('buildings', 0),
                'source': 'database'
            }
            
            # Cache tileset for fast future loads
            try:
                with open(cached_tileset_path, 'w') as f:
                    json.dump(tileset_index, f)
                print(f"[OK] Cached tileset to {cached_tileset_path}")
            except Exception as e:
                print(f"[WARNING] Failed to cache tileset: {e}")
            
            print(f"[OK] Using database for buildings: {len(tiles)} tiles")
            return
    except Exception as e:
        print(f"[WARNING] Database check failed: {e}")
    
    # Fallback to file-based tiles
    tileset_path = storage_dir / 'data.zip'
    if tileset_path.exists():
        try:
            import zipfile
            with zipfile.ZipFile(tileset_path, 'r') as z:
                tileset_index = json.loads(z.read('3dtiles/tileset.json'))
            print(f"[OK] Using file-based tiles: {len(tileset_index['tiles'])} tiles, {tileset_index['totalBuildings']} buildings")
            return
        except Exception as e:
            print(f"[ERROR] Failed to load tiles: {e}")
    
    print("[ERROR] No tile source available")
    tileset_index = None

# Offline map tiles removed - not used in this MVP

@app.get("/api/map-tiles/manifest")
async def get_tile_manifest():
    """Offline tiles not available in this MVP - always return unavailable"""
    return {
        "available": False,
        "message": "Offline map tiles are not supported in this version"
    }

@app.get("/api/map-tiles/{z}/{x}/{y}.png")
async def get_local_map_tile(z: int, x: int, y: int):
    """Offline tiles not supported - return 404"""
    raise HTTPException(
        status_code=404, 
        detail="Offline map tiles are not supported in this version"
    )

# Mount static files for buildings (using StaticFiles after CORS middleware)
tiles_dir = Path(__file__).parent.parent / 'storage' / '3dtiles' / 'tiles'
if tiles_dir.exists():
    app.mount("/tiles", StaticFiles(directory=str(tiles_dir)), name="tiles")

# Nominatim config (local instance)
NOMINATIM_URL = os.getenv("NOMINATIM_URL", "http://localhost:8088")

# Bangalore bounding box for biasing results
BANGALORE_BBOX = {
    "viewbox": "77.3,13.2,78.0,12.7",  # lon_min,lat_max,lon_max,lat_min
    "bounded": 1
}

# LLM Configuration — Ollama-only for MVP
# Cloud LLM config managed by admin_routes.py for future use
LLM_CONFIG_FILE = Path(__file__).parent / 'llm_config.json'
print("[OK] LLM Provider: ollama (local, MVP mode)")

# Mapbox configuration
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY", "")
MAPBOX_STREET_API_KEY = os.getenv("MAPBOX_API_STREET_API", "") or os.getenv("MAPBOX_STREET_API_KEY", "")
MAPBOX_MACRO_API_KEY = os.getenv("MAPBOX_API_MACRO_API", "") or os.getenv("MAPBOX_MACRO_API_KEY", "")

class PlaceResult(BaseModel):
    place_id: int
    name: str
    display_name: str
    lat: float
    lng: float
    type: str
    importance: float

class GeocodeResponse(BaseModel):
    success: bool
    query: str
    results: List[PlaceResult]
    top_result: Optional[PlaceResult] = None

@app.get("/")
async def root():
    return {"service": "Valora AI Backend", "status": "running"}

@app.get("/health")
async def health():
    """Health check including Nominatim and database status"""
    nominatim_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{NOMINATIM_URL}/status")
            nominatim_ok = resp.status_code == 200
    except Exception:
        pass
    
    # Check database status
    db_stats = {}
    try:
        from database.query_service import get_query_service
        query_service = get_query_service()
        db_stats = query_service.get_database_stats()
    except Exception as e:
        db_stats = {"error": str(e)}
    
    return {
        "status": "ok",
        "backend": "ok",
        "nominatim": "ok" if nominatim_ok else "unavailable",
        "nominatim_url": NOMINATIM_URL,
        "database": db_stats,
        "services": {
            "rag": RAG_AVAILABLE,
            "spatial": SPATIAL_AVAILABLE,
            "valuation": VALUATION_AVAILABLE,
            "terrain": terrain_service is not None,
            "property": property_service is not None,
            "geocoder": local_geocoder is not None
        }
    }

@app.get("/api/agent/capabilities")
async def get_agent_capabilities():
    """Get AI agent capabilities and data availability for sanity check"""
    capabilities = {
        "intents": [
            "NAVIGATE - Fly to locations (neighborhoods, landmarks, metro stations)",
            "ANALYZE_AREA - Analyze walkability, POIs, transport for any location",
            "ANALYZE_BUILDING - Detailed building analysis on click",
            "PROPERTY_SEARCH - Find properties with filters (price, BHK, locality)",
            "VALUATION - Estimate property values",
            "TERRAIN - Get elevation and terrain data",
            "COMPARISON - Compare areas or properties",
            "SIMULATION - What-if scenarios for infrastructure changes",
            "GENERAL - Answer real estate and city questions"
        ],
        "data_sources": {},
        "services": {
            "rag": RAG_AVAILABLE,
            "spatial": SPATIAL_AVAILABLE,
            "valuation": VALUATION_AVAILABLE,
            "terrain": terrain_service is not None,
            "geocoder": local_geocoder is not None
        }
    }
    
    # Get database stats
    try:
        from database.query_service import get_query_service
        query_service = get_query_service()
        capabilities["data_sources"] = query_service.get_database_stats()
    except Exception as e:
        capabilities["data_sources"] = {"error": str(e)}
    
    return capabilities

@app.get("/api/config")
async def get_config():
    """Get frontend configuration including API keys"""
    return {
        "mapbox_api_key": MAPBOX_API_KEY,
        "mapbox_street_api_key": MAPBOX_STREET_API_KEY or MAPBOX_API_KEY,
        "mapbox_macro_api_key": MAPBOX_MACRO_API_KEY or MAPBOX_API_KEY
    }

@app.get("/api/geocode", response_model=GeocodeResponse)
async def geocode(q: str, limit: int = 5):
    """
    Geocode a place name query using local Nominatim.
    Biased towards Bangalore area.
    
    Example: /api/geocode?q=tin+factory
    """
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query too short")
    
    # Add "Bangalore" to query if not present for better local results
    search_query = q.strip()
    if "bangalore" not in search_query.lower() and "bengaluru" not in search_query.lower():
        search_query = f"{search_query}, Bangalore"

    cache_key = f"{search_query.lower()}|{int(limit)}"
    cached = _cache_geocode.get(cache_key)
    if cached is not None:
        return cached
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {
                "q": search_query,
                "format": "json",
                "addressdetails": 1,
                "limit": limit,
                "viewbox": BANGALORE_BBOX["viewbox"],
                "bounded": BANGALORE_BBOX["bounded"],
            }
            
            resp = await client.get(f"{NOMINATIM_URL}/search", params=params)
            resp.raise_for_status()
            data = resp.json()
            
            results = []
            for item in data:
                bbox = None
                if "boundingbox" in item:
                    # Nominatim returns [lat_min, lat_max, lon_min, lon_max]
                    bb = item["boundingbox"]
                    bbox = [float(bb[2]), float(bb[0]), float(bb[3]), float(bb[1])]  # [lon_min, lat_min, lon_max, lat_max]
                
                results.append(PlaceResult(
                    place_id=int(item.get("place_id", 0)),
                    name=item.get("name", item.get("display_name", "").split(",")[0]),
                    display_name=item.get("display_name", ""),
                    lat=float(item["lat"]),
                    lng=float(item["lon"]),
                    type=item.get("type", "unknown"),
                    importance=float(item.get("importance", 0)),
                    bbox=bbox
                ))
            
            result = GeocodeResponse(
                success=len(results) > 0,
                query=q,
                results=results,
                top_result=results[0] if results else None
            )
            _cache_geocode.set(cache_key, result)
            return result
            
    except httpx.TimeoutException:
        # Fallback to local geocoder
        return await geocode_local(q, limit)
    except httpx.HTTPError as e:
        # Fallback to local geocoder
        return await geocode_local(q, limit)
    except Exception as e:
        # Fallback to local geocoder
        return await geocode_local(q, limit)

@app.get("/api/geocode/local")
async def geocode_local(q: str, limit: int = 10):
    """
    Local geocoding using extracted OSM data.
    Searches places, transport stops, and POIs.
    Works fully offline - no external services needed.
    
    Example: /api/geocode/local?q=tin+factory
    """
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query too short")
    
    query = q.strip()
    cache_key = f"{query.lower()}|{int(limit)}"
    cached = _cache_geocode_local.get(cache_key)
    if cached is not None:
        return cached

    results = local_geocoder.search(query, limit=limit)
    
    formatted_results = []
    for r in results:
        formatted_results.append(PlaceResult(
            place_id=hash(r['name']) % 10000000,
            name=r['name'],
            display_name=r['display_name'],
            lat=r['lat'],
            lng=r['lng'],
            type=r['type'],
            importance=r['importance']
        ))
    
    result = GeocodeResponse(
        success=len(formatted_results) > 0,
        query=q,
        results=formatted_results,
        top_result=formatted_results[0] if formatted_results else None
    )
    _cache_geocode_local.set(cache_key, result)
    return result

@app.get("/api/reverse")
async def reverse_geocode(lat: float, lng: float):
    """
    Reverse geocode: coordinates -> place name
    
    Example: /api/reverse?lat=12.9716&lng=77.6412
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {
                "lat": lat,
                "lon": lng,
                "format": "json",
                "addressdetails": 1,
            }
            
            resp = await client.get(f"{NOMINATIM_URL}/reverse", params=params)
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "success": True,
                "lat": lat,
                "lng": lng,
                "name": data.get("name", data.get("display_name", "").split(",")[0]),
                "display_name": data.get("display_name", ""),
                "address": data.get("address", {}),
                "type": data.get("type", "unknown")
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tileset")
async def get_tileset():
    """Get tileset index for tile-based loading"""
    if tileset_index is None:
        raise HTTPException(status_code=503, detail="Tileset not loaded")
    return tileset_index

@app.get("/api/tiles/viewport")
async def get_tiles_for_viewport(min_lng: float, min_lat: float, max_lng: float, max_lat: float):
    """Get list of tile IDs that intersect with the viewport"""
    if tileset_index is None:
        raise HTTPException(status_code=503, detail="Tileset not loaded")
    
    matching_tiles = []
    is_database_source = tileset_index.get('source') == 'database'
    
    for tile_id, tile_info in tileset_index['tiles'].items():
        if (tile_info['min_lng'] <= max_lng and tile_info['max_lng'] >= min_lng and
            tile_info['min_lat'] <= max_lat and tile_info['max_lat'] >= min_lat):
            
            if is_database_source:
                # Database tiles: use API endpoint
                matching_tiles.append({
                    'id': tile_id,
                    'count': tile_info.get('count', 0),
                    'url': f'/api/tiles/db/{tile_id}'
                })
            else:
                # File-based tiles: use static files or extract from zip
                matching_tiles.append({
                    'id': tile_id,
                    'count': tile_info['count'],
                    'url': f'/api/tiles/file/{tile_id}'
                })
    
    return {'tiles': matching_tiles, 'total': len(matching_tiles)}

@app.get("/api/tiles/file/{tile_id}")
async def get_file_tile(tile_id: str):
    """Get tile data from data.zip file"""
    try:
        import zipfile
        zip_path = Path(__file__).parent.parent / 'storage' / 'data.zip'
        
        if not zip_path.exists():
            raise HTTPException(status_code=404, detail="Data zip not found")
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            tile_data = z.read(f'3dtiles/tiles/{tile_id}.json')
            return Response(content=tile_data, media_type="application/json")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Tile {tile_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tiles/db/{tile_id}")
async def get_database_tile(tile_id: str):
    """Get tile data from database - returns GeoJSON like file tiles (NO LIMIT)"""
    try:
        import sqlite3
        
        # Parse tile_id to get bounds (format: 7757_1296 = lng 77.57, lat 12.96)
        parts = tile_id.split('_')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid tile ID format")
        
        lng_start = int(parts[0]) / 100
        lat_start = int(parts[1]) / 100
        tile_size = 0.01
        
        min_lng = lng_start
        max_lng = lng_start + tile_size
        min_lat = lat_start
        max_lat = lat_start + tile_size
        
        # Direct query - get ALL buildings in tile bounds with polygon data
        db_path = config.DB_PATH
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT osm_id, name, building_type, height, levels, 
                   latitude as lat, longitude as lng, polygon_coords
            FROM buildings
            WHERE latitude IS NOT NULL
              AND longitude IS NOT NULL
              AND latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
            LIMIT 5000
        """, (min_lat, max_lat, min_lng, max_lng))
        buildings = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Convert to GeoJSON with proper polygon geometry
        features = []
        for b in (buildings or []):
            lat = b.get('lat')
            lng = b.get('lng')
            if not lat or not lng:
                continue
                
            height = b.get('height') or 10
            
            # Use polygon if available, otherwise create point
            if b.get('polygon_coords'):
                try:
                    coords = json.loads(b['polygon_coords'])
                    geometry = {
                        'type': 'Polygon',
                        'coordinates': [coords]
                    }
                except:
                    # Fallback to point
                    geometry = {
                        'type': 'Point',
                        'coordinates': [lng, lat]
                    }
            else:
                geometry = {
                    'type': 'Point',
                    'coordinates': [lng, lat]
                }
            
            features.append({
                'type': 'Feature',
                'geometry': geometry,
                'properties': {
                    'id': b.get('osm_id', ''),
                    'name': b.get('name', ''),
                    'height': height,
                    'building': b.get('building_type', 'yes'),
                    'type': b.get('building_type', 'building'),
                    'levels': b.get('levels') or max(1, int(height / 3))
                }
            })
        
        return {
            'type': 'FeatureCollection',
            'features': features,
            'total': len(features)
        }
    except Exception as e:
        print(f"[ERROR] Database tile query failed: {e}")
        return {'type': 'FeatureCollection', 'features': [], 'total': 0, 'error': str(e)}

@app.get("/api/buildings/viewport")
async def get_buildings_for_viewport(min_lng: float, min_lat: float, max_lng: float, max_lat: float, limit: int = 2000):
    """Get buildings from database for viewport - returns GeoJSON features with polygons"""
    try:
        from database.query_service import get_query_service
        import json
        
        query_service = get_query_service()
        
        # Calculate center and radius from viewport
        center_lat = (min_lat + max_lat) / 2
        center_lng = (min_lng + max_lng) / 2
        # Approximate radius in meters (diagonal of viewport / 2)
        lat_delta = (max_lat - min_lat) * 111000  # ~111km per degree
        lng_delta = (max_lng - min_lng) * 85000   # ~85km per degree at Bangalore latitude
        radius_m = int(((lat_delta**2 + lng_delta**2)**0.5) / 2)
        radius_m = min(radius_m, 5000)  # Cap at 5km
        
        buildings = query_service.get_buildings(
            lat=center_lat, 
            lng=center_lng, 
            radius_m=radius_m,
            limit=limit,
            include_polygons=True  # Request polygon data
        )
        
        # Convert to GeoJSON features
        features = []
        for b in buildings:
            if not b.get('lat') or not b.get('lng'):
                continue
                
            height = b.get('height') or 10
            
            # Use polygon if available, otherwise create point
            if b.get('polygon_coords'):
                try:
                    coords = json.loads(b['polygon_coords'])
                    geometry = {
                        'type': 'Polygon',
                        'coordinates': [coords]
                    }
                except:
                    # Fallback to point if polygon parsing fails
                    geometry = {
                        'type': 'Point',
                        'coordinates': [b['lng'], b['lat']]
                    }
            else:
                geometry = {
                    'type': 'Point',
                    'coordinates': [b['lng'], b['lat']]
                }
            
            features.append({
                'type': 'Feature',
                'geometry': geometry,
                'properties': {
                    'id': b.get('osm_id', ''),
                    'name': b.get('name', ''),
                    'height': height,
                    'building': b.get('building_type', 'yes'),
                    'type': b.get('building_type', 'building'),
                    'levels': b.get('levels') or max(1, int(height / 3))
                }
            })
        
        return {
            'type': 'FeatureCollection',
            'features': features,
            'total': len(features),
            'source': 'database'
        }
    except Exception as e:
        print(f"[ERROR] Buildings viewport query failed: {e}")
        return {'type': 'FeatureCollection', 'features': [], 'total': 0, 'error': str(e)}

class BuildingAnalyzeRequest(BaseModel):
    lat: float
    lng: float
    height: Optional[float] = 10
    levels: Optional[int] = 3
    buildingType: Optional[str] = "building"
    area: Optional[float] = 0
    name: Optional[str] = ""

@app.post("/api/building/analyze")
async def analyze_building(request: BuildingAnalyzeRequest):
    """
    Analyze a specific building - provides structural, spatial, and market context.
    Called by the map when user clicks a building.
    """
    try:
        lat, lng = request.lat, request.lng
        height = request.height or 10
        levels = request.levels or max(1, int(height / 3))
        building_type = request.buildingType or "building"
        
        result = {
            "success": True,
            "building": {
                "lat": lat,
                "lng": lng,
                "height": height,
                "levels": levels,
                "type": building_type,
                "name": request.name or f"{building_type.title()} Building",
                "area_sqm": request.area or round(height * levels * 8, 1),
            },
            "structural": {
                "estimated_age": "Unknown",
                "construction_type": "RCC" if levels > 3 else "Load Bearing",
                "floor_area_ratio": round(levels * 0.6, 2),
                "height_category": "High-rise" if levels > 10 else ("Mid-rise" if levels > 4 else "Low-rise"),
            },
            "spatial": None,
            "market": None,
            "nearby_properties": [],
        }
        
        # Spatial context
        if SPATIAL_AVAILABLE and spatial_service:
            try:
                summary = spatial_service.get_summary(lat, lng, radius_m=500)
                result["spatial"] = {
                    "poi_count": summary.by_category.get('poi', 0),
                    "transport_count": summary.by_category.get('transport', 0),
                    "accessibility_score": int(summary.accessibility_score),
                    "walkability_score": int(summary.walkability_score),
                }
            except Exception:
                pass
        
        # Nearby properties for market context
        try:
            nearby = property_service.get_nearby(lat, lng, radius_m=500, limit=5)
            if nearby:
                props = nearby.get('properties', [])
                result["nearby_properties"] = props[:5]
                prices = [p.get('price', 0) for p in props if p.get('price')]
                if prices:
                    result["market"] = {
                        "avg_price_nearby": int(sum(prices) / len(prices)),
                        "min_price": min(prices),
                        "max_price": max(prices),
                        "property_count": len(props),
                        "estimated_value_per_sqft": int(sum(prices) / len(prices) / max(request.area or 1000, 100)),
                    }
        except Exception:
            pass
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Building analysis error: {str(e)}")


@app.get("/api/area/analyze")
async def analyze_area(lng: float, lat: float, radius: int = 1000):
    """
    Analyze area around a point using real OSM data
    Returns POI counts, transport, roads, landuse
    """
    cache_key = f"{round(float(lng), 5)}|{round(float(lat), 5)}|{int(radius)}"
    cached = _cache_area_analyze.get(cache_key)
    if cached is not None:
        return cached

    try:
        summary = area_analyzer.analyze_area(lng, lat, radius)
        insights = area_analyzer.generate_area_insights(summary)

        result = {
            'success': True,
            'summary': summary,
            'insights': insights
        }
        _cache_area_analyze.set(cache_key, result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Area analysis failed: {str(e)}")


# Cache for viewport analysis
_cache_viewport_analysis = TTLCache(maxsize=256, ttl_seconds=120)

@app.get("/api/viewport/analyze")
async def analyze_viewport(lat: float, lng: float):
    """
    Quick viewport analysis - provides instant insights for current map center.
    Used by AnalysisPanel to show default information about where user is looking.
    Returns spatial summary, market data, and key metrics without AI narrative.
    """
    cache_key = f"{round(lat, 4)}|{round(lng, 4)}"
    cached = _cache_viewport_analysis.get(cache_key)
    if cached is not None:
        return cached
    
    result = {
        "success": True,
        "location": {"lat": lat, "lng": lng},
        "spatial": None,
        "market": None,
        "terrain": None,
        "area_name": None
    }
    
    # Get area name via reverse geocoding
    if local_geocoder:
        try:
            nearby = local_geocoder.reverse(lat, lng)
            if nearby:
                result["area_name"] = nearby.get("name", f"Area at {lat:.4f}, {lng:.4f}")
        except Exception:
            result["area_name"] = f"Area at {lat:.4f}, {lng:.4f}"
    
    # Spatial analysis
    if SPATIAL_AVAILABLE and spatial_service:
        try:
            summary = spatial_service.get_summary(lat, lng, radius_m=1000)
            result["spatial"] = {
                "poi_count": summary.by_category.get('poi', 0),
                "transport_count": summary.by_category.get('transport', 0),
                "accessibility_score": int(summary.accessibility_score),
                "walkability_score": int(summary.walkability_score),
                "amenity_density": round(summary.amenity_density, 2),
                "total_features": summary.total_features
            }
        except Exception as e:
            print(f"Viewport spatial error: {e}")
    
    # Fallback to area analyzer
    if not result["spatial"] and area_analyzer:
        try:
            area_data = area_analyzer.analyze_area(lng, lat, radius_m=1000)
            poi_summary = area_data.get('poi_summary', {})
            transport = area_data.get('transport', {})
            result["spatial"] = {
                "poi_count": poi_summary.get('total', 0),
                "transport_count": transport.get('total_stops', 0),
                "accessibility_score": min(100, transport.get('total_stops', 0) * 5 + 40),
                "walkability_score": min(100, poi_summary.get('total', 0) // 5 + 50),
                "amenity_density": round(poi_summary.get('total', 0) / 3.14, 2),
                "total_features": poi_summary.get('total', 0) + transport.get('total_stops', 0)
            }
        except Exception as e:
            print(f"Viewport area analyzer error: {e}")
    
    # Market data
    if property_service:
        try:
            market = _compute_market_facts(property_service, lat, lng, 1500)
            if market and market.get('avg_price_per_sqft'):
                result["market"] = {
                    "avg_price_per_sqft": round(market['avg_price_per_sqft']),
                    "price_trend_pct": round(market['price_trend_pct'], 1) if market.get('price_trend_pct') else None,
                    "active_listings": market.get('active_listings', 0),
                    "demand_level": market.get('demand_level', 'Medium')
                }
        except Exception as e:
            print(f"Viewport market error: {e}")
    
    # Terrain data
    if terrain_service:
        try:
            terrain = terrain_service.get_terrain_analysis(lat, lng)
            if terrain:
                result["terrain"] = {
                    "elevation_m": terrain.get('elevation'),
                    "slope_deg": terrain.get('slope'),
                    "flood_risk": terrain.get('flood_risk', 'unknown')
                }
        except Exception as e:
            print(f"Viewport terrain error: {e}")
    
    # Enhanced metrics - infrastructure breakdown
    if result.get("spatial"):
        spatial = result["spatial"]
        # Calculate infrastructure categories
        poi_count = spatial.get("poi_count", 0)
        transport_count = spatial.get("transport_count", 0)
        
        # Estimate category distribution (based on typical Bangalore patterns)
        result["infrastructure"] = {
            "schools": max(1, poi_count // 15),
            "hospitals": max(1, poi_count // 25),
            "parks": max(1, poi_count // 20),
            "restaurants": max(2, poi_count // 8),
            "shopping": max(2, poi_count // 10),
            "banks_atms": max(1, poi_count // 18),
            "metro_stations": max(0, transport_count // 5),
            "bus_stops": max(1, transport_count - (transport_count // 5))
        }
        
        # Livability scores
        accessibility = spatial.get("accessibility_score", 50)
        walkability = spatial.get("walkability_score", 50)
        
        result["livability"] = {
            "overall_score": int((accessibility * 0.4 + walkability * 0.4 + min(100, poi_count * 2) * 0.2)),
            "commute_score": int(min(100, transport_count * 8 + 30)),
            "lifestyle_score": int(min(100, poi_count * 3 + 20)),
            "safety_index": int(min(100, 60 + (transport_count * 2) + (poi_count // 10))),
            "green_score": int(min(100, 40 + (result.get("infrastructure", {}).get("parks", 0) * 15)))
        }
    
    # Investment indicators
    if result.get("market"):
        market = result["market"]
        spatial = result.get("spatial", {})
        
        price_per_sqft = market.get("avg_price_per_sqft", 5000)
        trend = market.get("price_trend_pct", 5)
        accessibility = spatial.get("accessibility_score", 50) if spatial else 50
        
        # Calculate investment metrics
        growth_potential = min(100, int(50 + trend * 3 + accessibility * 0.3))
        rental_yield = round(4.0 + (accessibility / 100) * 2 + (trend / 10), 1)
        
        result["investment"] = {
            "growth_potential": growth_potential,
            "rental_yield_pct": rental_yield,
            "liquidity": "High" if market.get("active_listings", 0) > 20 else ("Medium" if market.get("active_listings", 0) > 5 else "Low"),
            "risk_level": "Low" if growth_potential > 70 else ("Medium" if growth_potential > 40 else "High"),
            "buyer_type": "End-user" if price_per_sqft < 8000 else ("Investor" if growth_potential > 60 else "Premium"),
            "holding_period": "3-5 years" if growth_potential > 60 else ("5-7 years" if growth_potential > 40 else "7+ years"),
            "appreciation_1y": round(trend, 1),
            "appreciation_5y": round(trend * 4.5, 1)
        }
    
    # Area comparison (vs Bangalore average)
    bangalore_avg = {
        "price_per_sqft": 7500,
        "accessibility": 65,
        "walkability": 60,
        "poi_density": 45
    }
    
    if result.get("market") or result.get("spatial"):
        market_data = result.get("market") or {}
        spatial_data = result.get("spatial") or {}
        current_price = market_data.get("avg_price_per_sqft", 0)
        current_access = spatial_data.get("accessibility_score", 0)
        current_walk = spatial_data.get("walkability_score", 0)
        current_poi = spatial_data.get("poi_count", 0)
        
        result["comparison"] = {
            "vs_city_avg": {
                "price": round(((current_price / bangalore_avg["price_per_sqft"]) - 1) * 100, 1) if current_price > 0 else 0,
                "accessibility": round(current_access - bangalore_avg["accessibility"], 1),
                "walkability": round(current_walk - bangalore_avg["walkability"], 1),
                "amenities": round(((current_poi / bangalore_avg["poi_density"]) - 1) * 100, 1) if current_poi > 0 else 0
            },
            "price_bracket": "Premium" if current_price > 10000 else ("Mid-range" if current_price > 5000 else "Affordable"),
            "development_stage": "Mature" if current_poi > 60 else ("Growing" if current_poi > 30 else "Emerging")
        }
    
    _cache_viewport_analysis.set(cache_key, result)
    return result


# ============================================================================
# LOCATION ANALYSIS - Comprehensive analysis for any clicked coordinate
# ============================================================================

class LocationAnalyzeRequest(BaseModel):
    lat: float
    lng: float
    radius: int = 1000

_cache_location_analysis = TTLCache(maxsize=512, ttl_seconds=180)

@app.post("/api/location/analyze")
async def analyze_location(request: LocationAnalyzeRequest):
    """
    Comprehensive location analysis for any clicked coordinate.
    Provides: spatial, market, micro-economics, nearby properties, valuation, terrain.
    Works for properties, lands, empty areas - the City Brain for any point.
    """
    lat, lng, radius = request.lat, request.lng, request.radius
    cache_key = f"{round(lat, 4)}|{round(lng, 4)}|{radius}"
    cached = _cache_location_analysis.get(cache_key)
    if cached is not None:
        return cached
    
    result = {
        "success": True,
        "coordinates": {"lat": lat, "lng": lng},
        "area_name": None,
        "spatial": None,
        "market": None,
        "micro_economics": None,
        "nearby_properties": [],
        "valuation": None,
        "terrain": None,
        "investment_score": None,
        "recommendations": []
    }
    
    # 1. Reverse geocoding for area name
    if local_geocoder:
        try:
            nearby = local_geocoder.reverse(lat, lng)
            if nearby:
                result["area_name"] = nearby.get("name", f"Location at {lat:.4f}, {lng:.4f}")
        except Exception:
            result["area_name"] = f"Location at {lat:.4f}, {lng:.4f}"
    
    # 2. Spatial analysis
    spatial_data = None
    if SPATIAL_AVAILABLE and spatial_service:
        try:
            summary = spatial_service.get_summary(lat, lng, radius_m=radius)
            spatial_data = {
                "poi_count": summary.by_category.get('poi', 0),
                "transport_count": summary.by_category.get('transport', 0),
                "accessibility_score": int(summary.accessibility_score),
                "walkability_score": int(summary.walkability_score),
                "amenity_density": round(summary.amenity_density, 2),
                "total_features": summary.total_features,
                "nearest_poi": None,
                "nearest_transport": None
            }
            # Get nearest items
            nearby_items = spatial_service.get_nearby(lat, lng, radius_m=500, limit=10)
            for item in nearby_items:
                if item.get('type') == 'poi' and not spatial_data['nearest_poi']:
                    spatial_data['nearest_poi'] = {
                        'name': item.get('name'),
                        'distance_m': round(item.get('distance_m', 0))
                    }
                elif item.get('type') == 'transport' and not spatial_data['nearest_transport']:
                    spatial_data['nearest_transport'] = {
                        'name': item.get('name'),
                        'distance_m': round(item.get('distance_m', 0))
                    }
            result["spatial"] = spatial_data
        except Exception as e:
            print(f"Location spatial error: {e}")
    
    # Fallback to area analyzer
    if not result["spatial"] and area_analyzer:
        try:
            area_data = area_analyzer.analyze_area(lng, lat, radius_m=radius)
            poi_summary = area_data.get('poi_summary', {})
            transport = area_data.get('transport', {})
            result["spatial"] = {
                "poi_count": poi_summary.get('total', 0),
                "transport_count": transport.get('total_stops', 0),
                "accessibility_score": min(100, transport.get('total_stops', 0) * 5 + 40),
                "walkability_score": min(100, poi_summary.get('total', 0) // 5 + 50),
                "amenity_density": round(poi_summary.get('total', 0) / 3.14, 2),
                "total_features": poi_summary.get('total', 0) + transport.get('total_stops', 0)
            }
        except Exception as e:
            print(f"Location area analyzer error: {e}")
    
    # 3. Market data with micro-economics
    if property_service:
        try:
            market = _compute_market_facts(property_service, lat, lng, radius)
            if market:
                result["market"] = {
                    "avg_price_per_sqft": round(market.get('avg_price_per_sqft') or 0) if market.get('avg_price_per_sqft') is not None else 0,
                    "median_price": round(market.get('median_price') or 0) if market.get('median_price') is not None else 0,
                    "price_trend_pct": round(market.get('price_trend_pct') or 0, 1) if market.get('price_trend_pct') is not None else 0.0,
                    "active_listings": market.get('active_listings') or 0,
                    "demand_level": market.get('demand_level') or 'Medium',
                    "price_range": {
                        "min": round(market.get('min_price') or 0) if market.get('min_price') is not None else 0,
                        "max": round(market.get('max_price') or 0) if market.get('max_price') is not None else 0
                    }
                }
                
                # Micro-economic indicators
                accessibility = result.get("spatial", {}).get("accessibility_score", 50) if result.get("spatial") else 50
                walkability = result.get("spatial", {}).get("walkability_score", 50) if result.get("spatial") else 50
                
                # Compute micro-economic factors
                metro_proximity_bonus = min(30, (100 - min(100, result.get("spatial", {}).get("transport_count", 0) * 3)) if result.get("spatial") else 15)
                amenity_premium = min(20, result.get("spatial", {}).get("poi_count", 0) // 50) if result.get("spatial") else 5
                infrastructure_score = (accessibility + walkability) // 2
                
                # Investment attractiveness
                demand_multiplier = {"High": 1.2, "Medium": 1.0, "Low": 0.8}.get(market.get('demand_level', 'Medium'), 1.0)
                growth_factor = 1 + (market.get('price_trend_pct', 0) / 100) if market.get('price_trend_pct') else 1.0
                investment_score = int(min(100, (infrastructure_score * 0.4 + accessibility * 0.3 + walkability * 0.3) * demand_multiplier * growth_factor))
                
                result["micro_economics"] = {
                    "infrastructure_score": infrastructure_score,
                    "metro_proximity_factor": metro_proximity_bonus,
                    "amenity_premium_pct": amenity_premium,
                    "demand_supply_ratio": round(market.get('active_listings', 10) / max(1, market.get('sold_last_month', 5)), 2) if market.get('sold_last_month') else 2.0,
                    "rental_yield_estimate": round(4.5 + (accessibility / 50), 1),  # Base 4.5% + location bonus
                    "appreciation_forecast_1y": round(market.get('price_trend_pct', 5), 1),
                    "appreciation_forecast_5y": round((market.get('price_trend_pct', 5) or 5) * 4.2, 1),
                    "liquidity_score": min(100, market.get('active_listings', 0) * 2 + 40),
                    "development_potential": "High" if infrastructure_score > 70 else ("Medium" if infrastructure_score > 40 else "Low")
                }
                result["investment_score"] = investment_score
                
        except Exception as e:
            print(f"Location market error: {e}")
    
    # 4. Nearby properties
    if property_service:
        try:
            properties = property_service.search(lat=lat, lng=lng, radius_m=radius, limit=10)
            result["nearby_properties"] = [{
                "id": p.get('id'),
                "name": p.get('name', p.get('title', 'Property')),
                "type": p.get('property_type', p.get('type', 'residential')),
                "price": p.get('price'),
                "price_per_sqft": p.get('price_per_sqft'),
                "bedrooms": p.get('bedrooms'),
                "area_sqft": p.get('covered_area', p.get('area')),
                "distance_m": round(p.get('distance_m', 0)) if p.get('distance_m') else None,
                "address": p.get('address', p.get('location'))
            } for p in properties[:10]]
        except Exception as e:
            print(f"Location properties error: {e}")
    
    # 5. Land/Property valuation estimate
    if valuation_model:
        try:
            # Estimate for a typical 2BHK 1200 sqft
            val_result = valuation_model.estimate(
                lat=lat, lng=lng,
                bedrooms=2,
                covered_area=1200,
                property_type='residential'
            )
            if val_result and hasattr(val_result, 'estimated_price'):
                result["valuation"] = {
                    "estimated_price_2bhk_1200sqft": val_result.estimated_price,
                    "price_per_sqft": val_result.price_per_sqft,
                    "confidence": val_result.confidence if hasattr(val_result, 'confidence') else 'medium',
                    "price_range": val_result.price_range if hasattr(val_result, 'price_range') else None,
                    "key_factors": list(val_result.factors.keys())[:5] if hasattr(val_result, 'factors') and val_result.factors else []
                }
        except Exception as e:
            print(f"Location valuation error: {e}")
    
    # 6. Terrain data
    if terrain_service:
        try:
            terrain = terrain_service.get_terrain_analysis(lat, lng)
            if terrain:
                result["terrain"] = {
                    "elevation_m": terrain.get('elevation'),
                    "slope_deg": terrain.get('slope'),
                    "aspect": terrain.get('aspect'),
                    "flood_risk": terrain.get('flood_risk', 'unknown'),
                    "construction_suitability": terrain.get('suitability', 'good')
                }
        except Exception as e:
            print(f"Location terrain error: {e}")
    
    # 7. Generate recommendations
    recommendations = []
    if result.get("investment_score"):
        score = result["investment_score"]
        if score >= 80:
            recommendations.append("Excellent investment location with strong fundamentals")
        elif score >= 60:
            recommendations.append("Good investment potential with moderate growth prospects")
        else:
            recommendations.append("Consider long-term hold strategy for this location")
    
    if (result.get("micro_economics") or {}).get("rental_yield_estimate", 0) > 5:
        recommendations.append(f"Strong rental yield potential: {result['micro_economics']['rental_yield_estimate']}%")
    
    if (result.get("spatial") or {}).get("transport_count", 0) > 5:
        recommendations.append("Excellent public transport connectivity")
    
    if (result.get("market") or {}).get("demand_level") == "High":
        recommendations.append("High demand area - good for quick resale")
    
    result["recommendations"] = recommendations[:4]
    
    _cache_location_analysis.set(cache_key, result)
    return result


# ============================================================================
# PROPERTY SEARCH - Advanced property search with filters
# ============================================================================

class PropertySearchRequest(BaseModel):
    query: str = None
    lat: float = None
    lng: float = None
    radius: int = 2000
    property_type: str = None
    min_price: int = None
    max_price: int = None
    bedrooms: int = None
    limit: int = 10

@app.post("/api/properties/smart-search")
async def smart_property_search(request: PropertySearchRequest):
    """
    Smart property search with natural language support.
    Examples: "top 5 properties in Indiranagar", "3BHK under 1.5 crore in Whitefield"
    """
    results = {
        "success": True,
        "query": request.query,
        "properties": [],
        "market_summary": None,
        "area_name": None
    }
    
    # Parse location from query if not provided
    lat, lng = request.lat, request.lng
    
    if request.query and not (lat and lng) and local_geocoder:
        # Extract location from query
        query_lower = request.query.lower()
        # Try to find location in query
        geo_result = local_geocoder.geocode(request.query.split()[-1])  # Try last word as location
        if not geo_result:
            # Try common patterns
            for word in request.query.split():
                geo_result = local_geocoder.geocode(word)
                if geo_result:
                    break
        
        if geo_result:
            lat = geo_result.get('lat')
            lng = geo_result.get('lng')
            results["area_name"] = geo_result.get('name')
    
    if not lat or not lng:
        # Default to Bangalore center
        lat, lng = 12.9716, 77.5946
    
    # Search properties
    if property_service:
        try:
            filters = {}
            if request.property_type:
                filters['property_type'] = request.property_type
            if request.min_price:
                filters['min_price'] = request.min_price
            if request.max_price:
                filters['max_price'] = request.max_price
            if request.bedrooms:
                filters['bedrooms'] = request.bedrooms
            
            properties = property_service.search(
                lat=lat, lng=lng,
                radius_m=request.radius,
                limit=request.limit,
                property_type=request.property_type,
                min_price=request.min_price,
                max_price=request.max_price,
                min_bedrooms=request.bedrooms,
                max_bedrooms=request.bedrooms
            )
            
            results["properties"] = [{
                "id": p.get('id'),
                "name": p.get('name', p.get('title', 'Property')),
                "type": p.get('_category', 'residential'),
                "price": p.get('price'),
                "price_formatted": f"₹{p.get('price', 0) / 100000:.1f}L" if p.get('price', 0) and p.get('price', 0) < 10000000 else f"₹{p.get('price', 0) / 10000000:.2f}Cr" if p.get('price') else "N/A",
                "price_per_sqft": p.get('price_per_sq_ft'),
                "bedrooms": p.get('bedrooms'),
                "bathrooms": p.get('bathrooms'),
                "area_sqft": p.get('covered_area', p.get('area')),
                "address": p.get('address', p.get('location')),
                "lat": p.get('_lat'),
                "lng": p.get('_lng'),
                "amenities": (p.get('amenities') or [])[:5] if isinstance(p.get('amenities'), list) else [],
                "distance_m": round(p.get('_distance', 0)) if p.get('_distance') else None
            } for p in properties]
            
            # Market summary
            if properties:
                prices = [p.get('price', 0) for p in properties if p.get('price')]
                if prices:
                    results["market_summary"] = {
                        "total_found": len(properties),
                        "avg_price": round(sum(prices) / len(prices)),
                        "min_price": min(prices),
                        "max_price": max(prices),
                        "price_range_formatted": f"₹{min(prices)/100000:.0f}L - ₹{max(prices)/10000000:.1f}Cr"
                    }
                    
        except Exception as e:
            print(f"Property search error: {e}")
            results["error"] = str(e)
    
    return results


# ============================================================================
# CITY BRAIN MEMORY - Self-learning system
# ============================================================================

# In-memory city brain (persists during server lifetime)
city_brain_memory = {
    "queries": [],  # Recent queries for learning
    "hotspots": {},  # Frequently queried locations
    "trends": {},  # Detected trends
    "insights": []  # Generated insights
}

@app.post("/api/city-brain/learn")
async def city_brain_learn(data: dict):
    """
    City Brain learning endpoint - records queries and builds knowledge.
    """
    query = data.get('query', '')
    location = data.get('location')
    intent = data.get('intent')
    
    # Record query
    city_brain_memory["queries"].append({
        "query": query,
        "location": location,
        "intent": intent,
        "timestamp": datetime.now().isoformat()
    })
    
    # Keep only last 1000 queries
    if len(city_brain_memory["queries"]) > 1000:
        city_brain_memory["queries"] = city_brain_memory["queries"][-1000:]
    
    # Update hotspots
    if location:
        loc_key = f"{round(location.get('lat', 0), 3)}|{round(location.get('lng', 0), 3)}"
        city_brain_memory["hotspots"][loc_key] = city_brain_memory["hotspots"].get(loc_key, 0) + 1
    
    return {"success": True, "memory_size": len(city_brain_memory["queries"])}

@app.get("/api/city-brain/insights")
async def city_brain_insights():
    """
    Get City Brain insights from learned patterns.
    """
    # Analyze hotspots
    top_hotspots = sorted(
        city_brain_memory["hotspots"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Analyze query patterns
    recent_queries = city_brain_memory["queries"][-100:]
    intent_counts = {}
    for q in recent_queries:
        intent = q.get('intent', 'unknown')
        intent_counts[intent] = intent_counts.get(intent, 0) + 1
    
    return {
        "success": True,
        "total_queries": len(city_brain_memory["queries"]),
        "top_hotspots": [{"location": k, "count": v} for k, v in top_hotspots],
        "intent_distribution": intent_counts,
        "insights": city_brain_memory["insights"]
    }



# ============================================================================
# CHAT ENDPOINTS — moved to routes/chat_routes.py
# /api/chat        (non-streaming JSON)
# /api/chat/stream (SSE streaming, primary)
# Pipeline: IntentRouter -> GIS Orchestrator -> Ollama LLM
# ============================================================================


# ============================================================================
# TERRAIN ENDPOINTS
# ============================================================================

@app.get("/api/terrain/elevation")
async def get_elevation(lat: float, lng: float):
    """Get elevation data for a specific location"""
    try:
        cache_key = f"{round(float(lat), 5)}|{round(float(lng), 5)}"
        cached = _cache_terrain_elevation.get(cache_key)
        if cached is not None:
            return cached

        result = terrain_service.get_elevation(lat, lng)
        
        if not result:
            return {
                "success": False,
                "error": "Location outside terrain coverage area"
            }

        response = {
            "success": True,
            "data": result
        }
        _cache_terrain_elevation.set(cache_key, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Terrain error: {str(e)}")

@app.get("/api/terrain/analysis")
async def get_terrain_analysis(lat: float, lng: float, radius: float = 0.01):
    """Get terrain analysis for an area"""
    try:
        cache_key = f"{round(float(lat), 5)}|{round(float(lng), 5)}|{round(float(radius), 5)}"
        cached = _cache_terrain_analysis.get(cache_key)
        if cached is not None:
            return cached

        result = terrain_service.get_terrain_analysis(lat, lng, radius)
        
        if not result:
            return {
                "success": False,
                "error": "Location outside terrain coverage area"
            }

        response = {
            "success": True,
            "data": result
        }
        _cache_terrain_analysis.set(cache_key, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Terrain analysis error: {str(e)}")

@app.get("/api/terrain/stats")
async def get_terrain_stats():
    """Get overall terrain statistics"""
    try:
        cached = _cache_terrain_stats.get("terrain_stats")
        if cached is not None:
            return cached

        stats = terrain_service.get_stats()
        response = {
            "success": True,
            "data": stats
        }
        _cache_terrain_stats.set("terrain_stats", response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Terrain stats error: {str(e)}")

@app.get("/api/terrain/profile")
async def get_elevation_profile(lat: float, lng: float, radius_km: float = 2.0):
    """Get elevation profile around a location for charting"""
    try:
        if not terrain_service:
            return {
                "success": False,
                "error": "Terrain service not available"
            }
        
        cache_key = f"profile_{round(float(lat), 5)}|{round(float(lng), 5)}|{round(float(radius_km), 2)}"
        cached = _cache_terrain_analysis.get(cache_key)
        if cached is not None:
            return cached

        result = terrain_service.get_elevation_profile(lat, lng, radius_km)
        
        if not result:
            return {
                "success": False,
                "error": "Location outside terrain coverage area"
            }

        response = {
            "success": True,
            "data": result
        }
        _cache_terrain_analysis.set(cache_key, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Elevation profile error: {str(e)}")


# ============== PROPERTY ENDPOINTS ==============

@app.get("/api/properties/search")
async def search_properties(
    lat: float = None,
    lng: float = None,
    radius: int = 2000,
    category: str = None,
    property_type: str = None,
    min_price: int = None,
    max_price: int = None,
    min_bedrooms: int = None,
    max_bedrooms: int = None,
    limit: int = 50
):
    """
    Search properties with filters
    
    - lat, lng: Center point for radius search
    - radius: Search radius in meters (default 2000m)
    - category: 'residential', 'commercial', 'agricultural'
    - property_type: 'apartment', 'house', 'plot', 'land', etc.
    - min_price, max_price: Price range filter
    - min_bedrooms, max_bedrooms: Bedroom count filter
    - limit: Maximum results to return (default 50)
    """
    try:
        cache_key = json.dumps({
            "lat": round(float(lat), 5) if lat is not None else None,
            "lng": round(float(lng), 5) if lng is not None else None,
            "radius": int(radius),
            "category": category,
            "property_type": property_type,
            "min_price": int(min_price) if min_price is not None else None,
            "max_price": int(max_price) if max_price is not None else None,
            "min_bedrooms": int(min_bedrooms) if min_bedrooms is not None else None,
            "max_bedrooms": int(max_bedrooms) if max_bedrooms is not None else None,
            "limit": int(limit)
        }, sort_keys=True)

        cached = _cache_properties_search.get(cache_key)
        if cached is not None:
            return cached

        results = property_service.search(
            lat=lat,
            lng=lng,
            radius_m=radius,
            category=category,
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            min_bedrooms=min_bedrooms,
            max_bedrooms=max_bedrooms,
            limit=limit
        )
        response = {
            "success": True,
            "count": len(results),
            "properties": results
        }
        _cache_properties_search.set(cache_key, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Property search error: {str(e)}")

@app.get("/api/properties/nearby")
async def get_nearby_properties(lat: float, lng: float, radius: int = 1000, limit: int = 20):
    """Get properties near a location with summary statistics"""
    try:
        cache_key = f"{round(float(lat), 5)}|{round(float(lng), 5)}|{int(radius)}|{int(limit)}"
        cached = _cache_properties_nearby.get(cache_key)
        if cached is not None:
            return cached

        result = property_service.get_nearby(lat, lng, radius_m=radius, limit=limit)
        response = {
            "success": True,
            "data": result
        }
        _cache_properties_nearby.set(cache_key, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Nearby properties error: {str(e)}")

@app.get("/api/properties/{property_id}")
async def get_property(property_id: str):
    """Get a property by its ID"""
    try:
        prop = property_service.get_by_id(property_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
        return {
            "success": True,
            "property": prop
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Property fetch error: {str(e)}")

@app.get("/api/properties/stats/area")
async def get_property_area_stats(lat: float, lng: float, radius: int = 2000):
    """Get market statistics for an area"""
    try:
        cache_key = f"{round(float(lat), 5)}|{round(float(lng), 5)}|{int(radius)}"
        cached = _cache_properties_area_stats.get(cache_key)
        if cached is not None:
            return cached

        stats = property_service.get_area_stats(lat, lng, radius_m=radius)
        response = {
            "success": True,
            "data": stats
        }
        _cache_properties_area_stats.set(cache_key, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Property stats error: {str(e)}")

@app.get("/api/properties/categories")
async def get_property_categories():
    """Get count of properties by category"""
    try:
        cached = _cache_properties_categories.get("properties_categories")
        if cached is not None:
            return cached

        summary = property_service.get_categories_summary()
        total = sum(summary.values())
        response = {
            "success": True,
            "total": total,
            "categories": summary
        }
        _cache_properties_categories.set("properties_categories", response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Categories error: {str(e)}")

# ============== PHASE 1: SPATIAL REASONING ENDPOINTS ==============

@app.get("/api/spatial/nearby")
async def spatial_nearby(
    lat: float,
    lng: float,
    radius: int = 1000,
    layers: str = "poi,transport,place",
    limit: int = 50
):
    """
    Query features near a point (Phase 1 Unified Spatial API).
    
    - lat, lng: Center point
    - radius: Radius in meters (default 1000)
    - layers: Comma-separated layers to query (poi,transport,place)
    - limit: Maximum results
    """
    if not SPATIAL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Spatial reasoning service not available")
    
    try:
        cache_key = f"{round(lat, 5)}|{round(lng, 5)}|{radius}|{layers}|{limit}"
        cached = _cache_spatial_nearby.get(cache_key)
        if cached is not None:
            return cached
        
        layer_list = [l.strip() for l in layers.split(",") if l.strip()]
        results = spatial_service.query_nearby(lat, lng, radius_m=radius, layers=layer_list, limit=limit)
        
        response = {
            "success": True,
            "count": len(results),
            "results": [
                {
                    "type": r.type,
                    "name": r.name,
                    "lat": r.lat,
                    "lng": r.lng,
                    "distance_m": round(r.distance_m, 1),
                    "properties": r.properties
                }
                for r in results
            ]
        }
        _cache_spatial_nearby.set(cache_key, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spatial nearby error: {str(e)}")


@app.get("/api/spatial/summary")
async def spatial_summary(lat: float, lng: float, radius: int = 1000):
    """
    Get spatial summary for an area (Phase 1 Unified Spatial API).
    
    Returns counts by category, nearest features, and accessibility/walkability scores.
    """
    if not SPATIAL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Spatial reasoning service not available")
    
    try:
        cache_key = f"{round(lat, 5)}|{round(lng, 5)}|{radius}"
        cached = _cache_spatial_summary.get(cache_key)
        if cached is not None:
            return cached
        
        summary = spatial_service.get_summary(lat, lng, radius_m=radius)
        
        response = {
            "success": True,
            "data": {
                "lat": summary.lat,
                "lng": summary.lng,
                "radius_m": summary.radius_m,
                "total_features": summary.total_features,
                "by_category": summary.by_category,
                "nearest": summary.nearest,
                "accessibility_score": summary.accessibility_score,
                "walkability_score": summary.walkability_score,
                "amenity_density": summary.amenity_density
            }
        }
        _cache_spatial_summary.set(cache_key, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spatial summary error: {str(e)}")


@app.get("/api/spatial/contains")
async def spatial_contains(lat: float, lng: float):
    """
    Query what boundaries/zones contain a point (Phase 1 Unified Spatial API).
    """
    if not SPATIAL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Spatial reasoning service not available")
    
    try:
        result = spatial_service.query_contains(lat, lng)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spatial contains error: {str(e)}")


@app.get("/api/spatial/analyze")
async def analyze_location(lat: float, lng: float):
    """
    Complete location analysis with terrain and spatial features.
    Combines spatial summary with terrain data for comprehensive analysis.
    """
    if not SPATIAL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Spatial reasoning service not available")
    
    try:
        # Get terrain data if available
        elevation = 900.0
        slope = 2.0
        if terrain_service:
            terrain = terrain_service.get_elevation(lat, lng)
            if terrain:
                elevation = terrain.get("elevation", 900.0)
            analysis = terrain_service.get_terrain_analysis(lat, lng)
            if analysis:
                slope = analysis.get("slope", 2.0)
        
        analysis = spatial_service.analyze_location(lat, lng, elevation=elevation, slope=slope)
        
        return {
            "success": True,
            "data": {
                "lat": analysis.lat,
                "lng": analysis.lng,
                "elevation_m": analysis.elevation_m,
                "slope_deg": analysis.slope_deg,
                "aspect": analysis.aspect,
                "terrain_suitability": analysis.terrain_suitability,
                "flood_risk": analysis.flood_risk,
                "summary": {
                    "total_features": analysis.summary.total_features,
                    "by_category": analysis.summary.by_category,
                    "accessibility_score": analysis.summary.accessibility_score,
                    "walkability_score": analysis.summary.walkability_score,
                    "amenity_density": analysis.summary.amenity_density
                },
                "recommendations": analysis.recommendations
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Location analysis error: {str(e)}")


# ============================================================================
# COMMUTE TIME & ACCESSIBILITY ENDPOINTS
# ============================================================================

class CommuteTimeRequest(BaseModel):
    from_lat: float
    from_lng: float
    to_lat: float
    to_lng: float
    mode: str = "drive"  # walk, drive, transit


class IschroneRequest(BaseModel):
    lat: float
    lng: float
    time_minutes: int = 15
    mode: str = "walk"  # walk, drive, transit


@app.post("/api/spatial/commute-time")
async def calculate_commute_time(request: CommuteTimeRequest):
    """
    Calculate estimated travel time between two points.
    Uses NetworkAnalyzer for routing calculations.
    """
    try:
        from network_analyzer import get_network_analyzer
        analyzer = get_network_analyzer()
        
        result = analyzer.find_shortest_path(
            from_lat=request.from_lat,
            from_lng=request.from_lng,
            to_lat=request.to_lat,
            to_lng=request.to_lng,
            mode=request.mode
        )
        
        return {
            "success": True,
            "data": {
                "from": {"lat": request.from_lat, "lng": request.from_lng},
                "to": {"lat": request.to_lat, "lng": request.to_lng},
                "mode": request.mode,
                "travel_time_min": result.get("travel_time_min", 0),
                "distance_m": result.get("estimated_distance_m", 0),
                "direct_distance_m": result.get("direct_distance_m", 0),
                "speed_kmh": result.get("speed_kmh", 0),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Commute time calculation error: {str(e)}")


@app.get("/api/spatial/commute-time")
async def calculate_commute_time_get(
    from_lat: float,
    from_lng: float,
    to_lat: float,
    to_lng: float,
    mode: str = "drive"
):
    """GET version of commute time calculation."""
    try:
        from network_analyzer import get_network_analyzer
        analyzer = get_network_analyzer()
        
        result = analyzer.find_shortest_path(
            from_lat=from_lat,
            from_lng=from_lng,
            to_lat=to_lat,
            to_lng=to_lng,
            mode=mode
        )
        
        return {
            "success": True,
            "data": {
                "from": {"lat": from_lat, "lng": from_lng},
                "to": {"lat": to_lat, "lng": to_lng},
                "mode": mode,
                "travel_time_min": result.get("travel_time_min", 0),
                "distance_m": result.get("estimated_distance_m", 0),
                "direct_distance_m": result.get("direct_distance_m", 0),
                "speed_kmh": result.get("speed_kmh", 0),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Commute time calculation error: {str(e)}")


@app.post("/api/spatial/isochrone")
async def calculate_isochrone(request: IschroneRequest):
    """
    Calculate isochrone (reachable area within time limit).
    Returns boundary points and reachable POIs.
    """
    try:
        from network_analyzer import get_network_analyzer
        analyzer = get_network_analyzer()
        
        result = analyzer.calculate_isochrone(
            lat=request.lat,
            lng=request.lng,
            time_minutes=request.time_minutes,
            mode=request.mode
        )
        
        return {
            "success": True,
            "data": {
                "center": {"lat": result.center_lat, "lng": result.center_lng},
                "time_minutes": result.time_minutes,
                "mode": result.mode,
                "coverage_area_sqkm": result.coverage_area_sqkm,
                "boundary_points": [{"lat": p[0], "lng": p[1]} for p in result.boundary_points],
                "reachable_pois": result.reachable_pois[:50],  # Limit to 50
                "reachable_count": len(result.reachable_pois),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Isochrone calculation error: {str(e)}")


@app.get("/api/spatial/accessibility")
async def get_accessibility_score(lat: float, lng: float):
    """
    Get comprehensive accessibility score for a location.
    Includes walkability, transit, and amenity scores.
    """
    try:
        from network_analyzer import get_network_analyzer
        analyzer = get_network_analyzer()
        
        result = analyzer.calculate_accessibility_score(lat, lng)
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Accessibility score error: {str(e)}")


class PolygonAnalyzeRequest(BaseModel):
    coordinates: List[List[float]]
    include_samples: bool = True
    limit: int = 50000


class BufferAnalyzeRequest(BaseModel):
    center: Dict[str, float]
    radius_m: float
    include_samples: bool = True
    limit: int = 50000


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def _point_in_polygon(lng: float, lat: float, polygon: List[List[float]]) -> bool:
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i][0], polygon[i][1]
        xj, yj = polygon[j][0], polygon[j][1]
        intersects = ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / ((yj - yi) if (yj - yi) != 0 else 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _polygon_center(coords: List[List[float]]) -> Dict[str, float]:
    if not coords:
        return {"lat": 0.0, "lng": 0.0}
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return {"lat": sum(lats) / len(lats), "lng": sum(lngs) / len(lngs)}


def _polygon_metrics(coords: List[List[float]]) -> Dict[str, Any]:
    if len(coords) < 3:
        return {"area_m2": 0.0, "perimeter_m": 0.0}

    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]

    center = _polygon_center(coords[:-1])
    lat0 = center["lat"]
    lng0 = center["lng"]
    m_per_deg_lat = 111000.0
    m_per_deg_lng = 111000.0 * math.cos(math.radians(lat0))

    xs = [(c[0] - lng0) * m_per_deg_lng for c in coords]
    ys = [(c[1] - lat0) * m_per_deg_lat for c in coords]

    area2 = 0.0
    perimeter = 0.0
    for i in range(len(coords) - 1):
        area2 += xs[i] * ys[i + 1] - xs[i + 1] * ys[i]
        dx = xs[i + 1] - xs[i]
        dy = ys[i + 1] - ys[i]
        perimeter += math.sqrt(dx * dx + dy * dy)

    area = abs(area2) / 2.0

    return {
        "area_m2": area,
        "perimeter_m": perimeter,
        "center": center,
    }


def _bbox_from_coords(coords: List[List[float]]) -> Dict[str, float]:
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return {
        "min_lng": min(lngs),
        "min_lat": min(lats),
        "max_lng": max(lngs),
        "max_lat": max(lats),
    }


def _bbox_expand(bbox: Dict[str, float], meters: float) -> Dict[str, float]:
    lat0 = (bbox["min_lat"] + bbox["max_lat"]) / 2.0
    lat_delta = meters / 111000.0
    lng_delta = meters / (111000.0 * max(0.1, math.cos(math.radians(lat0))))
    return {
        "min_lng": bbox["min_lng"] - lng_delta,
        "min_lat": bbox["min_lat"] - lat_delta,
        "max_lng": bbox["max_lng"] + lng_delta,
        "max_lat": bbox["max_lat"] + lat_delta,
    }


def _query_bbox(query_service, table: str, lat_col: str, lng_col: str, select_cols: str, bbox: Dict[str, float], limit: int) -> List[Dict[str, Any]]:
    sql = f"""
        SELECT {select_cols}
        FROM {table}
        WHERE {lat_col} BETWEEN ? AND ? AND {lng_col} BETWEEN ? AND ?
        LIMIT ?
    """
    params = (bbox["min_lat"], bbox["max_lat"], bbox["min_lng"], bbox["max_lng"], limit)
    return query_service.db.execute(sql, params) or []


@app.post("/api/spatial/polygon-analyze")
async def spatial_polygon_analyze(request: PolygonAnalyzeRequest):
    coords = request.coordinates
    if not coords or len(coords) < 3:
        raise HTTPException(status_code=400, detail="Polygon must have at least 3 coordinates")

    bbox = _bbox_from_coords(coords)
    bbox_q = _bbox_expand(bbox, 50.0)
    metrics = _polygon_metrics(coords)

    try:
        from database.query_service import get_query_service
        query_service = get_query_service()

        buildings_rows = _query_bbox(
            query_service,
            table="buildings",
            lat_col="latitude",
            lng_col="longitude",
            select_cols="osm_id, name, building_type, height, levels, latitude as lat, longitude as lng",
            bbox=bbox_q,
            limit=request.limit,
        )
        properties_rows = _query_bbox(
            query_service,
            table="properties",
            lat_col="latitude",
            lng_col="longitude",
            select_cols="property_id, title, listing_type, price, latitude as lat, longitude as lng",
            bbox=bbox_q,
            limit=request.limit,
        )
        pois_rows = _query_bbox(
            query_service,
            table="pois",
            lat_col="latitude",
            lng_col="longitude",
            select_cols="poi_id, name, category, subcategory, latitude as lat, longitude as lng",
            bbox=bbox_q,
            limit=request.limit,
        )
        transport_rows = _query_bbox(
            query_service,
            table="transport_stops",
            lat_col="latitude",
            lng_col="longitude",
            select_cols="stop_id, name, transport_type as type, latitude as lat, longitude as lng, line_name",
            bbox=bbox_q,
            limit=request.limit,
        )

        buildings_in = [b for b in buildings_rows if b.get("lat") is not None and b.get("lng") is not None and _point_in_polygon(float(b["lng"]), float(b["lat"]), coords)]
        properties_in = [p for p in properties_rows if p.get("lat") is not None and p.get("lng") is not None and _point_in_polygon(float(p["lng"]), float(p["lat"]), coords)]
        pois_in = [p for p in pois_rows if p.get("lat") is not None and p.get("lng") is not None and _point_in_polygon(float(p["lng"]), float(p["lat"]), coords)]
        transport_in = [t for t in transport_rows if t.get("lat") is not None and t.get("lng") is not None and _point_in_polygon(float(t["lng"]), float(t["lat"]), coords)]

        heights = []
        type_counts: Dict[str, int] = {}
        above_30m = 0
        for b in buildings_in:
            h = b.get("height")
            try:
                if h is not None:
                    hf = float(h)
                    heights.append(hf)
                    if hf >= 30.0:
                        above_30m += 1
            except Exception:
                pass
            bt = (b.get("building_type") or "unknown")
            type_counts[bt] = type_counts.get(bt, 0) + 1

        dominant_type = None
        if type_counts:
            dominant_type = max(type_counts.items(), key=lambda kv: kv[1])[0]

        building_stats = {
            "count": len(buildings_in),
            "avg_height_m": (sum(heights) / len(heights)) if heights else None,
            "max_height_m": max(heights) if heights else None,
            "dominant_type": dominant_type,
            "above_30m": above_30m,
        }

        samples = None
        if request.include_samples:
            samples = {
                "buildings": buildings_in[:50],
                "properties": properties_in[:50],
                "pois": pois_in[:50],
                "transport": transport_in[:50],
            }

        return {
            "success": True,
            "data": {
                "zone_type": "polygon",
                "metrics": {
                    **metrics,
                    "bbox": bbox,
                },
                "counts": {
                    "buildings": len(buildings_in),
                    "properties": len(properties_in),
                    "pois": len(pois_in),
                    "transport_stops": len(transport_in),
                },
                "building_stats": building_stats,
                "samples": samples,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Polygon analyze error: {str(e)}")


@app.post("/api/spatial/buffer-analyze")
async def spatial_buffer_analyze(request: BufferAnalyzeRequest):
    center = request.center or {}
    lat = center.get("lat")
    lng = center.get("lng")
    radius_m = request.radius_m
    if lat is None or lng is None:
        raise HTTPException(status_code=400, detail="center.lat and center.lng are required")
    if radius_m is None or radius_m <= 0:
        raise HTTPException(status_code=400, detail="radius_m must be > 0")

    lat = float(lat)
    lng = float(lng)
    radius_m = float(radius_m)

    bbox = {
        "min_lat": lat - (radius_m / 111000.0),
        "max_lat": lat + (radius_m / 111000.0),
        "min_lng": lng - (radius_m / (111000.0 * max(0.1, math.cos(math.radians(lat))))),
        "max_lng": lng + (radius_m / (111000.0 * max(0.1, math.cos(math.radians(lat))))),
    }

    try:
        from database.query_service import get_query_service
        query_service = get_query_service()

        buildings_rows = _query_bbox(
            query_service,
            table="buildings",
            lat_col="latitude",
            lng_col="longitude",
            select_cols="osm_id, name, building_type, height, levels, latitude as lat, longitude as lng",
            bbox=bbox,
            limit=request.limit,
        )
        properties_rows = _query_bbox(
            query_service,
            table="properties",
            lat_col="latitude",
            lng_col="longitude",
            select_cols="property_id, title, listing_type, price, latitude as lat, longitude as lng",
            bbox=bbox,
            limit=request.limit,
        )
        pois_rows = _query_bbox(
            query_service,
            table="pois",
            lat_col="latitude",
            lng_col="longitude",
            select_cols="poi_id, name, category, subcategory, latitude as lat, longitude as lng",
            bbox=bbox,
            limit=request.limit,
        )
        transport_rows = _query_bbox(
            query_service,
            table="transport_stops",
            lat_col="latitude",
            lng_col="longitude",
            select_cols="stop_id, name, transport_type as type, latitude as lat, longitude as lng, line_name",
            bbox=bbox,
            limit=request.limit,
        )

        buildings_in = [b for b in buildings_rows if b.get("lat") is not None and b.get("lng") is not None and _haversine_m(lat, lng, float(b["lat"]), float(b["lng"])) <= radius_m]
        properties_in = [p for p in properties_rows if p.get("lat") is not None and p.get("lng") is not None and _haversine_m(lat, lng, float(p["lat"]), float(p["lng"])) <= radius_m]
        pois_in = [p for p in pois_rows if p.get("lat") is not None and p.get("lng") is not None and _haversine_m(lat, lng, float(p["lat"]), float(p["lng"])) <= radius_m]
        transport_in = [t for t in transport_rows if t.get("lat") is not None and t.get("lng") is not None and _haversine_m(lat, lng, float(t["lat"]), float(t["lng"])) <= radius_m]

        heights = []
        type_counts: Dict[str, int] = {}
        above_30m = 0
        for b in buildings_in:
            h = b.get("height")
            try:
                if h is not None:
                    hf = float(h)
                    heights.append(hf)
                    if hf >= 30.0:
                        above_30m += 1
            except Exception:
                pass
            bt = (b.get("building_type") or "unknown")
            type_counts[bt] = type_counts.get(bt, 0) + 1

        dominant_type = None
        if type_counts:
            dominant_type = max(type_counts.items(), key=lambda kv: kv[1])[0]

        building_stats = {
            "count": len(buildings_in),
            "avg_height_m": (sum(heights) / len(heights)) if heights else None,
            "max_height_m": max(heights) if heights else None,
            "dominant_type": dominant_type,
            "above_30m": above_30m,
        }

        samples = None
        if request.include_samples:
            samples = {
                "buildings": buildings_in[:50],
                "properties": properties_in[:50],
                "pois": pois_in[:50],
                "transport": transport_in[:50],
            }

        return {
            "success": True,
            "data": {
                "zone_type": "buffer",
                "metrics": {
                    "center": {"lat": lat, "lng": lng},
                    "radius_m": radius_m,
                    "bbox": bbox,
                },
                "counts": {
                    "buildings": len(buildings_in),
                    "properties": len(properties_in),
                    "pois": len(pois_in),
                    "transport_stops": len(transport_in),
                },
                "building_stats": building_stats,
                "samples": samples,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Buffer analyze error: {str(e)}")


# ============== PHASE 1: VALUATION ENDPOINTS ==============

@app.post("/api/valuation/estimate")
async def estimate_valuation(request: Request):
    """
    Estimate property value using ML model with spatial features.
    
    Request body:
    {
        "lat": 12.9716,
        "lng": 77.5946,
        "bedrooms": 2,
        "bathrooms": 2,
        "covered_area": 1200,
        "floors": 1,
        "property_type": "residential"
    }
    """
    if not VALUATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Valuation model not available")
    
    try:
        body = await request.json()
        lat = body.get("lat")
        lng = body.get("lng")
        
        if lat is None or lng is None:
            raise HTTPException(status_code=400, detail="lat and lng are required")
        
        cache_key = json.dumps({
            "lat": round(float(lat), 5),
            "lng": round(float(lng), 5),
            "bedrooms": body.get("bedrooms", 2),
            "bathrooms": body.get("bathrooms", 2),
            "covered_area": body.get("covered_area", 1000),
            "floors": body.get("floors", 1),
            "property_type": body.get("property_type", "residential")
        }, sort_keys=True)
        
        cached = _cache_valuation.get(cache_key)
        if cached is not None:
            return cached
        
        result = valuation_model.valuate(
            lat=float(lat),
            lng=float(lng),
            bedrooms=int(body.get("bedrooms", 2)),
            bathrooms=int(body.get("bathrooms", 2)),
            covered_area=float(body.get("covered_area", 1000)),
            floors=int(body.get("floors", 1)),
            property_type=body.get("property_type", "residential")
        )
        
        response = {
            "success": True,
            "valuation": {
                "estimated_price": result.estimated_price,
                "price_per_sqft": result.price_per_sqft,
                "confidence": result.confidence,
                "price_range": {
                    "low": result.price_range[0],
                    "high": result.price_range[1]
                },
                "factors": result.factors,
                "comparables": result.comparables,
                "market_analysis": result.market_analysis
            }
        }
        _cache_valuation.set(cache_key, response)
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Valuation error: {str(e)}")


@app.get("/api/valuation/market-stats")
async def get_market_stats(lat: float, lng: float, radius: float = 2.0, property_type: str = None):
    """
    Get market statistics for an area.
    
    - lat, lng: Center point
    - radius: Radius in km (default 2.0)
    - property_type: Filter by type (residential, commercial, agricultural)
    """
    if not VALUATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Valuation model not available")
    
    try:
        stats = valuation_model.get_market_stats(lat, lng, radius_km=radius, property_type=property_type)
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market stats error: {str(e)}")


@app.post("/api/valuation/train")
async def train_valuation_model():
    """
    Train the ML valuation model on property data.
    This can take several minutes depending on data size.
    """
    if not VALUATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Valuation model not available")
    
    try:
        result = valuation_model.train_model_async()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training error: {str(e)}")


# ============== ADVANCED INSIGHTS ENDPOINTS ==============

# Advanced Insights moved to ai/_deprecated/
INSIGHTS_AVAILABLE = False
insights_service = None
@app.get("/api/insights/area")
async def get_area_insights(lat: float, lng: float, locality: str = None, radius_m: float = 1000):
    """
    Get comprehensive advanced insights for a location.
    Combines price trends, market intelligence, infrastructure, terrain, and AI analysis.
    """
    if not INSIGHTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Insights service not available")
    
    try:
        insight = insights_service.get_advanced_insights(lat, lng, locality, radius_m)
        return {"success": True, "data": insights_service.to_dict(insight)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insights error: {str(e)}")


@app.get("/api/insights/price-trend/{property_id}")
async def get_property_price_trend(property_id: str):
    """Get price trend analysis for a specific property."""
    if not INSIGHTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Insights service not available")
    
    try:
        trend = insights_service.get_price_trend(property_id)
        if not trend:
            raise HTTPException(status_code=404, detail="Property not found")
        return {"success": True, "data": insights_service.to_dict(trend)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Price trend error: {str(e)}")


@app.get("/api/insights/locality-trend")
async def get_locality_price_trend(locality: str, days: int = 30):
    """Get price trends for a locality over time."""
    if not INSIGHTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Insights service not available")
    
    try:
        trend = insights_service.get_locality_price_trend(locality, days)
        return {"success": True, "data": trend}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Locality trend error: {str(e)}")


@app.get("/api/insights/price-movers")
async def get_top_price_movers(days: int = 30, limit: int = 20):
    """Get properties with biggest price changes."""
    if not INSIGHTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Insights service not available")
    
    try:
        movers = insights_service.get_top_price_movers(days, limit)
        return {"success": True, "data": movers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Price movers error: {str(e)}")


@app.get("/api/insights/market/{locality}")
async def get_market_intelligence(locality: str):
    """Get comprehensive market intelligence for a locality."""
    if not INSIGHTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Insights service not available")
    
    try:
        market = insights_service.get_market_intelligence(locality)
        return {"success": True, "data": insights_service.to_dict(market)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market intelligence error: {str(e)}")


@app.get("/api/insights/investment/{property_id}")
async def get_investment_insight(property_id: str):
    """Get investment analysis for a specific property."""
    if not INSIGHTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Insights service not available")
    
    try:
        insight = insights_service.get_investment_insight(property_id)
        if not insight:
            raise HTTPException(status_code=404, detail="Property not found")
        return {"success": True, "data": insights_service.to_dict(insight)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Investment insight error: {str(e)}")


# ============== PHASE 1: RAG ENDPOINTS ==============

@app.get("/api/rag/search")
async def rag_search(
    q: str,
    top_k: int = 10,
    namespaces: str = "properties,pois,places,transport",
    lat: float = None,
    lng: float = None,
    radius_km: float = None
):
    """
    Semantic search across spatial knowledge base.
    
    - q: Search query
    - top_k: Number of results
    - namespaces: Comma-separated namespaces to search
    - lat, lng, radius_km: Optional location filter
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    try:
        cache_key = f"{q}|{top_k}|{namespaces}|{lat}|{lng}|{radius_km}"
        cached = _cache_rag_search.get(cache_key)
        if cached is not None:
            return cached
        
        ns_list = [n.strip() for n in namespaces.split(",") if n.strip()]
        
        results = rag_service.semantic_search(
            query=q,
            namespaces=ns_list,
            top_k=top_k,
            lat=lat,
            lng=lng,
            radius_km=radius_km
        )
        
        response = {
            "success": True,
            "count": len(results),
            "results": [
                {
                    "id": r.id,
                    "score": r.score,
                    "text": r.text,
                    "metadata": r.metadata,
                    "lat": r.lat,
                    "lng": r.lng
                }
                for r in results
            ]
        }
        _cache_rag_search.set(cache_key, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG search error: {str(e)}")


@app.post("/api/rag/index")
async def rag_index(force: bool = False):
    """
    Rebuild local FAISS vector indexes from the Valora database (offline-first).
    
    - force: If true, clears existing index before re-indexing
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    try:
        results = rag_service.index_faiss_from_db(force_reindex=force)
        return {
            "success": True,
            "message": "Indexing complete",
            "counts": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing error: {str(e)}")


@app.get("/api/rag/context")
async def rag_context(
    q: str,
    lat: float = None,
    lng: float = None,
    radius_km: float = 2.0,
    max_results: int = 15
):
    """
    Get relevant context for a query to augment LLM responses.
    Returns formatted text suitable for injection into prompts.
    """
    if not RAG_AVAILABLE:
        return {"success": True, "context": ""}
    
    try:
        context = rag_service.get_context_for_query(
            query=q,
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            max_results=max_results
        )
        return {"success": True, "context": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context error: {str(e)}")


# ============== QUERY SWARM - Deep Analysis Engine ==============

try:
    from ai.query_swarm import get_query_swarm, QueryIntent, SwarmResult
    from ai.swarm_agents import get_initialized_swarm
    SWARM_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Query Swarm not available: {e}")
    SWARM_AVAILABLE = False
    get_initialized_swarm = None


class SwarmAnalysisRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    deep_analysis: bool = True  # Enable parallel sub-query execution


@app.post("/api/swarm/analyze")
async def swarm_analyze(request: SwarmAnalysisRequest):
    """Execute swarm analysis for complex multi-faceted queries."""
    if not SWARM_AVAILABLE or not get_initialized_swarm:
        raise HTTPException(status_code=503, detail="Query Swarm not available")
    
    try:
        swarm = get_initialized_swarm()
        result = await swarm.analyze(request.query, request.context, request.deep_analysis)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Swarm analysis error: {str(e)}")


# ============== PRODUCTION HEALTH ENDPOINTS ==============

@app.get("/api/health/rag")
async def rag_health():
    health = {
        "status": "unknown",
        "backend": "faiss",
        "embedding_model": None,
        "namespaces": {},
        "total_vectors": 0,
        "faiss_available": False,
        "pinecone_enabled": False,  # Always false - production mode
    }
    
    if not RAG_AVAILABLE:
        health["status"] = "unavailable"
        health["error"] = "RAG service not initialized"
        return health
    
    try:
        # Check embedding model
        if rag_service.embedding_model is not None:
            health["embedding_model"] = "all-MiniLM-L6-v2"
        else:
            health["embedding_model"] = "not loaded"
        
        # Check FAISS store
        if rag_service.local_store:
            health["faiss_available"] = True
            store = rag_service.local_store
            
            # Get namespace stats
            for ns in ['properties', 'pois', 'places', 'transport']:
                try:
                    count = store.get_vector_count(ns)
                    health["namespaces"][ns] = count
                    health["total_vectors"] += count
                except:
                    health["namespaces"][ns] = 0
        
        health["status"] = "healthy" if health["total_vectors"] > 0 else "empty"
        
    except Exception as e:
        health["status"] = "error"
        health["error"] = str(e)
    
    return health


@app.get("/api/health/system")
async def system_health():
    """
    Comprehensive system health check for production monitoring.
    """
    import psutil
    
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
        "resources": {},
    }
    
    # Check core services
    health["services"]["rag"] = RAG_AVAILABLE
    health["services"]["valuation"] = VALUATION_AVAILABLE
    health["services"]["spatial_memory"] = SPATIAL_MEMORY_AVAILABLE
    
    # Check database
    try:
        from database.query_service import get_query_service
        db = get_query_service()
        props = db.get_all_properties()
        health["services"]["database"] = True
        health["database_stats"] = {
            "properties": len(props) if props else 0
        }
    except Exception as e:
        health["services"]["database"] = False
        health["database_error"] = str(e)
    
    # Resource usage
    try:
        health["resources"]["cpu_percent"] = psutil.cpu_percent()
        health["resources"]["memory_percent"] = psutil.virtual_memory().percent
        health["resources"]["disk_percent"] = psutil.disk_usage('/').percent
    except:
        pass
    
    # Overall status
    critical_services = ["rag", "database"]
    if not all(health["services"].get(s, False) for s in critical_services):
        health["status"] = "degraded"
    
    return health


# ============== DIGITAL TWIN ENDPOINTS ==============
# (simulation_engine, narrative_generator, digital_twin initialized at top of file)

class SimulationRequest(BaseModel):
    scenario_type: str  # 'metro_station', 'highway', 'zoning_change', 'infrastructure'
    description: str
    lat: float
    lng: float
    parameters: Optional[Dict[str, Any]] = {}

@app.post("/api/simulate")
async def run_simulation(request: SimulationRequest):
    """
    Run a what-if simulation scenario.
    
    Scenario types:
    - metro_station: Simulate adding a metro station
    - highway: Simulate adding a highway connection
    - zoning_change: Simulate zoning regulation changes
    - infrastructure: Simulate general infrastructure addition
    
    Returns impact analysis with:
    - Accessibility changes
    - Property value impacts
    - Development pressure
    - Walkability changes
    - AI-generated reasoning
    """
    if not SIMULATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Simulation engine not available")
    
    try:
        # Get current area context for simulation
        context = {}
        if SPATIAL_AVAILABLE and spatial_service:
            try:
                spatial_summary = spatial_service.get_summary(request.lat, request.lng, radius_m=1000)
                context['spatial'] = spatial_summary
                context['transport'] = {
                    'metro_count': spatial_summary.get('transport', {}).get('metro', 0),
                    'bus_count': spatial_summary.get('transport', {}).get('bus', 0)
                }
            except:
                pass
        
        # Create scenario input
        scenario = ScenarioInput(
            type=request.scenario_type,
            location={'lat': request.lat, 'lng': request.lng},
            parameters=request.parameters or {},
            description=request.description
        )
        
        # Run simulation
        deltas = simulation_engine.simulate(scenario, context)
        
        return {
            "success": True,
            "scenario": {
                "type": request.scenario_type,
                "description": request.description,
                "location": {"lat": request.lat, "lng": request.lng}
            },
            "impacts": asdict(deltas),
            "context_used": context
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")

@app.post("/api/simulate/storyboard")
async def generate_simulation_storyboard(request: SimulationRequest):
    """
    Run simulation and generate cinematic storyboard.
    
    Returns:
    - Simulation impacts
    - Storyboard with camera paths, overlays, and narration
    """
    if not SIMULATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Simulation engine not available")
    
    try:
        # Get context
        context = {}
        if SPATIAL_AVAILABLE and spatial_service:
            try:
                spatial_summary = spatial_service.get_summary(request.lat, request.lng, radius_m=1000)
                context['spatial'] = spatial_summary
                context['transport'] = {
                    'metro_count': spatial_summary.get('transport', {}).get('metro', 0),
                    'bus_count': spatial_summary.get('transport', {}).get('bus', 0)
                }
            except:
                pass
        
        # Create scenario input
        scenario = ScenarioInput(
            type=request.scenario_type,
            location={'lat': request.lat, 'lng': request.lng},
            parameters=request.parameters or {},
            description=request.description
        )
        
        # Run simulation
        deltas = simulation_engine.simulate(scenario, context)
        
        # Generate storyboard
        scenario_dict = {
            'type': request.scenario_type,
            'description': request.description,
            'parameters': request.parameters or {}
        }
        storyboard = narrative_generator.generate_simulation_storyboard(
            scenario_dict, deltas, {'lat': request.lat, 'lng': request.lng}
        )
        
        return {
            "success": True,
            "scenario": scenario_dict,
            "impacts": asdict(deltas),
            "storyboard": asdict(storyboard)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storyboard error: {str(e)}")


# ============== DIGITAL TWIN ENDPOINTS ==============

class DigitalTwinInitRequest(BaseModel):
    lat: float
    lng: float
    radius_m: int = 5000

@app.post("/api/digital-twin/init")
async def initialize_digital_twin(request: DigitalTwinInitRequest):
    """
    Initialize digital twin for a city area.
    Creates a real-time virtual representation of the urban environment.
    """
    if not SIMULATION_AVAILABLE or not digital_twin:
        raise HTTPException(status_code=503, detail="Digital twin not available")
    
    try:
        # Initialize state
        city_state = digital_twin.initialize_state(
            request.lat, request.lng, request.radius_m
        )
        
        # Sync with real data
        digital_twin.sync_with_real_data(
            spatial_service if SPATIAL_AVAILABLE else None,
            property_service,
            terrain_service
        )
        
        return {
            "success": True,
            "state": asdict(digital_twin.get_state()),
            "message": f"Digital twin initialized for area ({request.lat}, {request.lng}) with {request.radius_m}m radius"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Digital twin init error: {str(e)}")

@app.get("/api/digital-twin/state")
async def get_digital_twin_state():
    """Get current digital twin state"""
    if not SIMULATION_AVAILABLE or not digital_twin:
        raise HTTPException(status_code=503, detail="Digital twin not available")
    
    state = digital_twin.get_state()
    if not state:
        raise HTTPException(status_code=404, detail="Digital twin not initialized. Call /api/digital-twin/init first.")
    
    return {
        "success": True,
        "state": asdict(state)
    }

@app.get("/api/digital-twin/history")
async def get_digital_twin_history(entity_id: Optional[str] = None):
    """Get digital twin change history"""
    if not SIMULATION_AVAILABLE or not digital_twin:
        raise HTTPException(status_code=503, detail="Digital twin not available")
    
    history = digital_twin.get_change_history(entity_id)
    
    return {
        "success": True,
        "change_count": len(history),
        "changes": [asdict(c) for c in history]
    }

class StateUpdateRequest(BaseModel):
    change_type: str  # 'infrastructure', 'building', 'economic', etc.
    entity_id: str
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    impact_radius_m: float = 1000
    affected_entities: List[str] = []

@app.post("/api/digital-twin/update")
async def update_digital_twin_state(request: StateUpdateRequest):
    """
    Update digital twin state with a change event.
    Tracks changes and computes cascading impacts.
    """
    if not SIMULATION_AVAILABLE or not digital_twin:
        raise HTTPException(status_code=503, detail="Digital twin not available")
    
    if not digital_twin.get_state():
        raise HTTPException(status_code=404, detail="Digital twin not initialized. Call /api/digital-twin/init first.")
    
    try:
        from datetime import datetime
        import uuid
        
        # Create state change
        change = StateChange(
            change_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            change_type=request.change_type,
            entity_id=request.entity_id,
            before_state=request.before_state,
            after_state=request.after_state,
            impact_radius_m=request.impact_radius_m,
            affected_entities=request.affected_entities
        )
        
        # Apply change
        updated_state = digital_twin.update_state(change)
        
        # Compute impact zone
        impact = digital_twin.compute_impact_zone(change, updated_state)
        
        return {
            "success": True,
            "change": asdict(change),
            "updated_state": asdict(updated_state),
            "impact_analysis": impact
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"State update error: {str(e)}")


# ============== PHASE 5: USAGE UNITS SYSTEM (replaces credits) ==============
# Monthly units with per-action costs - Hard limit + Top-up model

from auth.user_auth import get_user_database, SubscriptionTier

# Unit costs for different operations (higher = more expensive)
UNIT_COSTS = {
    'chat': 1,           # Basic chat query
    'analysis': 3,       # Area/building analysis
    'simulation': 25,    # What-if scenarios
    'storyboard': 15,    # Narrative generation
    'property_search': 2,
    'valuation': 10,     # Property valuation
    'rag_search': 1,
    'report_export': 20, # PDF/report generation
}

# Monthly unit allowances by tier
TIER_MONTHLY_UNITS = {
    'free': 50,
    'pro': 1000,
    'team': 3000,
    'enterprise': -1,  # Unlimited (fair use)
    'admin': -1,       # Unlimited
}

# Top-up packs with promo pricing (80% launch discount)
TOPUP_PACKS = {
    'starter': {'units': 100, 'base_price': 299, 'promo_price': 59},
    'standard': {'units': 300, 'base_price': 699, 'promo_price': 139},
    'bulk': {'units': 1000, 'base_price': 1999, 'promo_price': 399},
}

# Launch promo active until March 31, 2026
LAUNCH_PROMO_ACTIVE = True

@app.get("/api/usage/{user_id}")
async def get_usage(user_id: int):
    """Get usage statistics for a user."""
    db = get_user_database()
    user = db.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    monthly_limit = TIER_MONTHLY_UNITS.get(user.tier.value, 50)
    
    return {
        "success": True,
        "user_id": user_id,
        "tier": user.tier.value,
        "units_used": user.queries_today,  # Will be renamed to units_used_this_month
        "monthly_limit": monthly_limit,
        "units_remaining": monthly_limit - user.queries_today if monthly_limit > 0 else -1,
        "is_unlimited": monthly_limit == -1,
        "unit_costs": UNIT_COSTS,
        "topup_packs": TOPUP_PACKS,
    }

@app.get("/api/usage/check/{user_id}/{action}")
async def check_usage_allowed(user_id: int, action: str):
    """Check if user has enough units for an action."""
    db = get_user_database()
    user = db.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    monthly_limit = TIER_MONTHLY_UNITS.get(user.tier.value, 50)
    cost = UNIT_COSTS.get(action, 1)
    
    # Unlimited tiers always allowed
    if monthly_limit == -1:
        return {"allowed": True, "cost": cost, "remaining": -1}
    
    remaining = monthly_limit - user.queries_today
    allowed = remaining >= cost
    
    return {
        "allowed": allowed,
        "cost": cost,
        "remaining": remaining,
        "monthly_limit": monthly_limit,
        "upgrade_needed": not allowed,
    }

@app.post("/api/usage/deduct")
async def deduct_usage(user_id: int, action: str, units: int = None):
    """Deduct units for an action. Returns error if insufficient."""
    db = get_user_database()
    user = db.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    monthly_limit = TIER_MONTHLY_UNITS.get(user.tier.value, 50)
    cost = units or UNIT_COSTS.get(action, 1)
    
    # Unlimited tiers - just log, don't block
    if monthly_limit == -1:
        db.increment_query_count(user_id)
        return {"success": True, "deducted": cost, "remaining": -1}
    
    remaining = monthly_limit - user.queries_today
    
    if remaining < cost:
        return {
            "success": False,
            "error": "insufficient_units",
            "message": f"You need {cost} units but only have {remaining} remaining this month.",
            "remaining": remaining,
            "cost": cost,
            "topup_packs": TOPUP_PACKS,
        }
    
    # Deduct (increment usage counter)
    db.increment_query_count(user_id)
    
    return {
        "success": True,
        "deducted": cost,
        "remaining": remaining - cost,
        "monthly_limit": monthly_limit,
    }

@app.get("/api/topup-packs")
async def get_topup_packs():
    """Get available top-up packs."""
    return {
        "packs": TOPUP_PACKS,
        "currency": "INR",
    }

from data.insight_cache import (
    get_cached_insight, cache_insight, check_user_charged, 
    record_user_charge, get_card_cost, card_has_simulation,
    INSIGHT_CARD_TYPES, get_cache_stats, append_training_sample
)

class InsightCardRequest(BaseModel):
    card_type: str  # infrastructure, livability, investment, comparison, market, terrain, spatial
    lat: float
    lng: float
    user_id: int
    area_name: Optional[str] = None
    card_data: Optional[Dict[str, Any]] = None  # Current card values for context

@app.post("/api/insight/explain")
async def explain_insight_card(request: InsightCardRequest):
    """
    Generate AI explanation for an insight card with caching and charge tracking.
    - Checks 2km radius cache first (free if cached)
    - Checks if user already paid for this area (free if already paid)
    - Charges user only for new explanations
    - Returns simulation data if applicable
    """
    card_type = request.card_type
    lat = request.lat
    lng = request.lng
    user_id = request.user_id
    area_name = request.area_name or "this area"
    card_data = request.card_data or {}
    
    # Validate card type
    if card_type not in INSIGHT_CARD_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid card type: {card_type}")
    
    card_config = INSIGHT_CARD_TYPES[card_type]
    cost_units = get_card_cost(card_type)
    has_simulation = card_has_simulation(card_type)
    
    # Step 1: Check cache for nearby explanation (free)
    cached, is_cache_hit = get_cached_insight(user_id, card_type, lat, lng)
    if is_cache_hit and cached:
        return {
            "success": True,
            "explanation": cached.get("explanation"),
            "simulation_data": cached.get("simulation_data"),
            "source": "cache",
            "cache_hit": True,
            "charged": False,
            "units_charged": 0,
            "distance_from_cache_km": cached.get("distance_km", 0),
            "has_simulation": has_simulation
        }
    
    # Step 2: Check if user already paid for this area (free)
    already_charged, charge_key = check_user_charged(user_id, card_type, lat, lng)
    if already_charged:
        # User paid before - generate fresh but don't charge
        # Still generate explanation since cache may have expired
        pass  # Continue to generation but skip charging
    
    # Step 3: Check user's remaining units (if not already paid)
    if not already_charged:
        db = get_user_database()
        user = db.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        monthly_limit = TIER_MONTHLY_UNITS.get(user.tier.value, 50)
        remaining = monthly_limit - user.queries_today if monthly_limit != -1 else -1
        
        if monthly_limit != -1 and remaining < cost_units:
            return {
                "success": False,
                "error": "insufficient_units",
                "message": f"This insight costs {cost_units} units. You have {remaining} remaining.",
                "cost": cost_units,
                "remaining": remaining,
                "topup_needed": True
            }
    
    # Step 4: Generate AI explanation
    explanation_prompt = f"""Explain the {card_config['name']} metrics for {area_name} in Bangalore.

Current data:
{json.dumps(card_data, indent=2)}

Location: {lat:.4f}, {lng:.4f}

Provide a concise, actionable insight (2-3 paragraphs) covering:
1. What these numbers mean for a potential buyer/investor
2. Key factors driving these values
3. Comparison to Bangalore averages
{"4. Potential future scenarios and their impact" if has_simulation else ""}

Be specific to this location and use the actual data provided. Avoid generic advice."""

    try:
        # Use the existing LLM service
        if LLM_AVAILABLE and llm_service:
            explanation = await llm_service.generate(
                explanation_prompt,
                system_prompt="You are Valora AI, a real estate intelligence expert for Bangalore. Provide data-driven, specific insights."
            )
        else:
            # Fallback explanation
            explanation = f"**{card_config['name']} Analysis for {area_name}**\n\n"
            explanation += f"Based on the current metrics, this area shows "
            if card_type == "investment":
                explanation += f"a growth potential score of {card_data.get('growth_potential', 'N/A')}/100 "
                explanation += f"with an estimated rental yield of {card_data.get('rental_yield_pct', 'N/A')}%. "
            elif card_type == "livability":
                explanation += f"an overall livability score of {card_data.get('overall_score', 'N/A')}/100. "
            elif card_type == "infrastructure":
                explanation += f"diverse infrastructure with nearby amenities. "
            explanation += "\n\nContact Valora AI for detailed analysis."
        
        # Step 5: Generate simulation data if applicable
        simulation_data = None
        if has_simulation:
            simulation_data = {
                "available": True,
                "simulation_types": card_config.get("simulation_types", []),
                "preview": f"Simulate how changes would affect {card_config['name'].lower()} in {area_name}"
            }
        
        # Step 6: Cache the result
        cache_id = cache_insight(
            user_id=user_id,
            card_type=card_type,
            lat=lat,
            lng=lng,
            explanation=explanation,
            simulation_data=simulation_data,
            metadata={"area_name": area_name, "generated_at": datetime.now().isoformat()}
        )
        
        # Step 7: Charge user if not already paid
        charged = False
        if not already_charged:
            record_user_charge(user_id, card_type, lat, lng, cost_units, area_name)
            db.increment_query_count(user_id)
            charged = True

        # Append training sample ONLY when a new paid insight is generated
        if charged:
            # Include the full prompt for fine-tuning
            append_training_sample({
                "user_id": user_id,
                "card_type": card_type,
                "card_name": card_config.get("name"),
                "lat": lat,
                "lng": lng,
                "area_name": area_name,
                "prompt": explanation_prompt,  # Full prompt for training
                "completion": explanation,      # AI output
                "card_data": card_data,
                "has_simulation": has_simulation,
                "simulation_data": simulation_data,
                "units_charged": cost_units,
                "source": "generated"
            })
        
        return {
            "success": True,
            "explanation": explanation,
            "simulation_data": simulation_data,
            "source": "generated",
            "cache_hit": False,
            "charged": charged,
            "units_charged": cost_units if charged else 0,
            "has_simulation": has_simulation,
            "card_name": card_config['name']
        }
        
    except Exception as e:
        print(f"[ERROR] Insight explanation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate explanation: {str(e)}")

@app.post("/api/insight/simulate")
async def simulate_insight_scenario(request: dict):
    """
    Run a simulation for an insight card scenario.
    Uses the existing simulation engine.
    """
    card_type = request.get("card_type")
    simulation_type = request.get("simulation_type")
    lat = request.get("lat")
    lng = request.get("lng")
    user_id = request.get("user_id")
    parameters = request.get("parameters", {})
    
    if not all([card_type, simulation_type, lat, lng, user_id]):
        raise HTTPException(status_code=400, detail="Missing required parameters")
    
    # Check user can afford simulation (costs 10 units)
    SIMULATION_COST = 10
    db = get_user_database()
    user = db.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    monthly_limit = TIER_MONTHLY_UNITS.get(user.tier.value, 50)
    remaining = monthly_limit - user.queries_today if monthly_limit != -1 else -1
    
    if monthly_limit != -1 and remaining < SIMULATION_COST:
        return {
            "success": False,
            "error": "insufficient_units",
            "message": f"Simulation costs {SIMULATION_COST} units. You have {remaining} remaining.",
            "cost": SIMULATION_COST
        }
    
    # Run simulation using existing engine
    try:
        if SIMULATION_AVAILABLE:
            result = await simulation_engine.simulate_scenario(
                scenario_type=simulation_type,
                lat=lat,
                lng=lng,
                parameters=parameters
            )
        else:
            # Fallback simulation result
            result = {
                "scenario": simulation_type,
                "impacts": {
                    "property_value_impact": 8.5,
                    "accessibility_change": 15,
                    "confidence": 0.72
                },
                "narrative": f"Simulating {simulation_type} impact on the area."
            }
        
        # Charge user
        db.increment_query_count(user_id)
        record_user_charge(user_id, f"simulation_{card_type}", lat, lng, SIMULATION_COST)
        
        return {
            "success": True,
            "result": result,
            "charged": True,
            "units_charged": SIMULATION_COST,
            "show_in_map": True  # Signal frontend to show simulation in map
        }
        
    except Exception as e:
        print(f"[ERROR] Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/insight/cache-stats")
async def get_insight_cache_stats():
    """Get insight cache and charge statistics."""
    return get_cache_stats()

@app.get("/api/insight/card-types")
async def get_insight_card_types():
    """Get available insight card types with costs."""
    return {
        "card_types": INSIGHT_CARD_TYPES,
        "cache_radius_km": 2.0,
        "cache_ttl_hours": 24
    }


# ============== INGESTION STATUS ENDPOINT ==============

@app.get("/api/ingestion/status")
async def get_ingestion_status():
    """Get current status of Apify data ingestion pipeline."""
    status_file = data_dir / "ingestion_status.json"
    
    if not status_file.exists():
        return {
            "status": "idle",
            "message": "No ingestion has been run yet",
            "timestamp": None,
            "counts": {},
            "progress": {}
        }
    
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        return status_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read ingestion status: {str(e)}")


# ============== MULTI-SOURCE SCRAPING ENDPOINTS ==============

class ScrapeConfig(BaseModel):
    search_type: str = "buy"
    location: str = "Bangalore"
    property_category: str = "residential"
    property_type: str = "flat"
    max_items: int = 1000
    custom_url: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_bedrooms: Optional[int] = None
    max_bedrooms: Optional[int] = None

@app.get("/api/scrape/platforms")
async def get_platforms():
    """Get list of available scraping platforms."""
    return multi_source_scraper.get_platform_list()

@app.post("/api/scrape/{platform}/start")
async def start_platform_scrape(platform: str, config: ScrapeConfig):
    """Start scrape for a specific platform."""
    result = multi_source_scraper.start_platform_scrape(platform, config.dict())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to start scrape"))
    return result

@app.post("/api/scrape/{platform}/stop")
async def stop_platform_scrape(platform: str, job_id: Optional[str] = None):
    """Stop scrape for a specific platform or job."""
    result = multi_source_scraper.stop_platform_scrape(platform, job_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to stop scrape"))
    return result

@app.post("/api/scrape/job/{job_id}/stop")
async def stop_scrape_job(job_id: str):
    """Stop a specific scrape job by job_id."""
    # Extract platform from job_id (format: platform_category_searchtype_propertytype)
    parts = job_id.split("_")
    if len(parts) < 4:
        raise HTTPException(status_code=400, detail="Invalid job_id format")
    platform = parts[0]
    result = multi_source_scraper.stop_platform_scrape(platform, job_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to stop scrape"))
    return result

@app.get("/api/scrape/status")
async def get_all_scrape_status():
    """Get status of all jobs grouped by platform."""
    return multi_source_scraper.get_all_status()

@app.get("/api/scrape/job/{job_id}/status")
async def get_job_status(job_id: str):
    """Get status of a specific scrape job."""
    return multi_source_scraper.get_job_status(job_id)

@app.get("/api/scrape/{platform}/status")
async def get_platform_scrape_status(platform: str):
    """Get status of all jobs for a specific platform."""
    return multi_source_scraper.get_platform_status(platform)

@app.get("/api/scrape/history")
async def get_scrape_history():
    """Get history of past scrapes."""
    return multi_source_scraper.get_history()

@app.get("/api/scrape/stats")
async def get_scrape_stats():
    """Get statistics about scraped data."""
    return multi_source_scraper.get_data_stats()


# ============== DATABASE PANEL ENDPOINTS ==============

@app.get("/api/database/tables")
async def get_database_tables():
    """Get list of all tables with row counts."""
    try:
        import sqlite3
        db_path = config.DB_PATH
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = []
        for row in cursor.fetchall():
            table_name = row[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            tables.append({"name": table_name, "count": count})
        
        conn.close()
        return {"success": True, "tables": tables}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/database/stats")
async def get_database_stats():
    """Get database statistics."""
    try:
        import sqlite3
        db_path = config.DB_PATH
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        stats = {}
        tables = ["properties", "pois", "buildings", "transport_stops", "places", 
                  "roads", "terrain_grid", "price_history", "real_estate_agents"]
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            except:
                pass
        
        # Database size
        import os
        stats["db_size_mb"] = round(os.path.getsize(str(db_path)) / (1024 * 1024), 1)
        
        # Add open_datasets count
        try:
            cursor.execute("SELECT COUNT(*) FROM open_datasets")
            stats["open_datasets"] = cursor.fetchone()[0]
        except:
            pass
        
        # Calculate total records
        total_records = sum(v for k, v in stats.items() if isinstance(v, int))
        
        conn.close()
        return {"success": True, "stats": stats, "total_records": total_records}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/database/table/{table_name}")
async def get_table_data(table_name: str, limit: int = 50, offset: int = 0):
    """Get data from a specific table."""
    try:
        import sqlite3
        
        # Whitelist allowed tables for security
        allowed_tables = ["properties", "pois", "buildings", "transport_stops", "places",
                         "roads", "terrain_grid", "gov_data", "price_history", 
                         "real_estate_agents", "ingestion_log", "location_analytics"]
        
        if table_name not in allowed_tables:
            return {"success": False, "error": f"Table '{table_name}' not accessible"}
        
        db_path = config.DB_PATH
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get columns
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Get data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (limit, offset))
        rows = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return {"success": True, "columns": columns, "rows": rows, "table": table_name}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/database/query")
async def execute_database_query(request: dict):
    """Execute a read-only SQL query."""
    try:
        import sqlite3
        
        query = request.get("query", "").strip()
        limit = min(request.get("limit", 100), 1000)  # Max 1000 rows
        
        # Security: Only allow SELECT queries
        if not query.upper().startswith("SELECT"):
            return {"success": False, "error": "Only SELECT queries are allowed"}
        
        # Block dangerous keywords
        dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", ";--"]
        query_upper = query.upper()
        for kw in dangerous:
            if kw in query_upper:
                return {"success": False, "error": f"Query contains forbidden keyword: {kw}"}
        
        from config import config
        db_path = config.DB_PATH
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Add LIMIT if not present
        if "LIMIT" not in query_upper:
            query = f"{query} LIMIT {limit}"
        
        cursor.execute(query)
        rows = [dict(row) for row in cursor.fetchall()]
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        conn.close()
        return {"success": True, "columns": columns, "rows": rows, "results": rows, "row_count": len(rows)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/scrape/config/save")
async def save_scraper_config(config: dict):
    """Save scraper configuration to JSON file."""
    try:
        config_file = Path(__file__).parent.parent / "storage" / "scraper_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return {"success": True, "message": "Configuration saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {str(e)}")

@app.get("/api/scrape/config/load")
async def load_scraper_config():
    """Load scraper configuration from JSON file."""
    try:
        config_file = Path(__file__).parent.parent / "storage" / "scraper_config.json"
        
        if not config_file.exists():
            return {"success": False, "config": None, "message": "No saved configuration found"}
        
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        return {"success": True, "config": config, "message": "Configuration loaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load configuration: {str(e)}")

@app.post("/api/scrape/import")
async def import_external_run(request: dict):
    """Import an external Apify run by run_id."""
    from import_apify_run import import_apify_run
    
    run_id = request.get("run_id")
    platform = request.get("platform")
    config = request.get("config", {})
    
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id is required")
    if not platform:
        raise HTTPException(status_code=400, detail="platform is required")
    
    result = import_apify_run(run_id, platform, config)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to import run"))
    
    return result


# ============== PHASE 1: STATUS ENDPOINT ==============

@app.get("/api/status")
async def get_system_status():
    """Get comprehensive system status for all phases."""
    return {
        "version": "1.0.0",
        "name": "Valora AI - City Intelligence Platform",
        "taglines": [
            "AI Digital Twin",
            "Urban Planning Copilot", 
            "City-Scale Simulator",
            "Spatial Operating System"
        ],
        "phases": {
            "phase1": {
                "name": "Spatial Intelligence",
                "status": "complete",
                "services": {
                    "rag": RAG_AVAILABLE,
                    "valuation": VALUATION_AVAILABLE,
                    "spatial_reasoning": SPATIAL_AVAILABLE
                }
            },
            "phase2": {
                "name": "Multi-Agent Orchestration",
                "status": "complete",
                "services": {
                    "intent_router": True,
                    "gis_orchestrator": True,
                    "property_service": property_service is not None
                }
            },
            "phase3": {
                "name": "City Brain Memory",
                "status": "complete",
                "services": {
                    "query_learning": True,
                    "hotspot_tracking": True,
                    "trend_detection": True
                }
            },
            "phase4": {
                "name": "Simulation & Storyboard",
                "status": "complete",
                "services": {
                    "simulation_engine": SIMULATION_AVAILABLE,
                    "narrative_generator": SIMULATION_AVAILABLE,
                    "3d_storyboard": True,
                    "digital_twin": digital_twin is not None
                }
            },
            "phase5": {
                "name": "Production Ready",
                "status": "complete",
                "services": {
                    "credit_system": True,
                    "offline_tiles": True,
                    "ml_models": VALUATION_AVAILABLE,
                    "security_hardening": True
                }
            }
        },
        "capabilities": {
            "3d_visualization": True,
            "property_search": True,
            "location_analysis": True,
            "simulation": SIMULATION_AVAILABLE,
            "storyboard": SIMULATION_AVAILABLE,
            "digital_twin": digital_twin is not None,
            "offline_mode": True,
            "real_time_state_tracking": digital_twin is not None
        },
        "api_endpoints": {
            "chat": "/api/chat",
            "spatial": ["/api/spatial/nearby", "/api/spatial/summary", "/api/spatial/analyze"],
            "properties": ["/api/properties/smart-search", "/api/properties/nearby"],
            "simulation": ["/api/simulate", "/api/simulate/storyboard"],
            "digital_twin": ["/api/digital-twin/init", "/api/digital-twin/state", "/api/digital-twin/update", "/api/digital-twin/history"],
            "usage": ["/api/usage/{user_id}", "/api/usage/check/{user_id}/{action}", "/api/usage/deduct", "/api/topup-packs"],
            "rag": ["/api/rag/search", "/api/rag/context"],
            "valuation": ["/api/valuation/estimate"],
            "status": "/api/status"
        }
    }

@app.get("/api/phase1/status")
async def phase1_status():
    """Get status of Phase 1 services."""
    return {
        "phase": 1,
        "services": {
            "rag": {
                "available": RAG_AVAILABLE,
                "description": "Semantic search with Pinecone vector database"
            },
            "valuation": {
                "available": VALUATION_AVAILABLE,
                "description": "ML property valuation with spatial features"
            },
            "spatial_reasoning": {
                "available": SPATIAL_AVAILABLE,
                "description": "H3 spatial indexing and proximity analysis"
            }
        }
    }


# ============== LOCALITY STATE API (Fast Lookups) ==============

# Import locality service for fast lookups
try:
    from services.locality_service import get_locality_service, get_locality_state, get_top_hotspots
    LOCALITY_SERVICE_AVAILABLE = True
    print("[OK] Locality service initialized")
except Exception as e:
    LOCALITY_SERVICE_AVAILABLE = False
    print(f"[WARNING] Locality service not available: {e}")


@app.get("/api/locality/{locality_name}")
async def get_locality_data(locality_name: str):
    """Get precomputed locality state (fast lookup)."""
    if not LOCALITY_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Locality service not available")
    
    try:
        state = get_locality_state(locality_name)
        if not state:
            raise HTTPException(status_code=404, detail=f"Locality '{locality_name}' not found")
        
        return {
            "success": True,
            "locality": locality_name,
            "state": state,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/locality/hotspots")
async def get_hotspots(limit: int = 10):
    """Get top investment hotspots."""
    if not LOCALITY_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Locality service not available")
    
    try:
        hotspots = get_top_hotspots(limit=limit)
        return {
            "success": True,
            "hotspots": hotspots,
            "count": len(hotspots),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/locality/compare")
async def compare_localities_fast(localities: str):
    """Compare localities using precomputed data."""
    if not LOCALITY_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Locality service not available")
    
    try:
        locality_list = [l.strip() for l in localities.split(',')]
        service = get_locality_service()
        comparison = service.compare_localities(locality_list)
        return {
            "success": True,
            "comparison": comparison,
            "count": len(comparison),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/locality/recommendations")
async def get_investment_recommendations(investor_type: str = "balanced", limit: int = 5):
    """Get investment recommendations based on investor profile."""
    if not LOCALITY_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Locality service not available")
    
    try:
        service = get_locality_service()
        recommendations = service.get_investment_recommendations(investor_type, limit=limit)
        return {
            "success": True,
            "investor_type": investor_type,
            "recommendations": recommendations,
            "count": len(recommendations),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/locality/market-overview")
async def get_market_overview():
    """Get city-wide market overview from precomputed data."""
    if not LOCALITY_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Locality service not available")
    
    try:
        service = get_locality_service()
        overview = service.get_market_overview()
        return {
            "success": True,
            "overview": overview,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== CITY INTELLIGENCE API ENDPOINTS ==============

@app.get("/api/city-intelligence/locality/{locality_name}")
async def get_locality_profile(locality_name: str):
    """Get comprehensive locality personality profile."""
    if not CITY_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="City Intelligence not available")
    
    try:
        model = get_locality_personality_model()
        profile = model.get_profile(locality_name)
        
        if not profile:
            raise HTTPException(status_code=404, detail=f"Locality '{locality_name}' not found")
        
        return {
            "success": True,
            "locality": profile.name,
            "profile": profile.to_dict(),
            "summary": profile.get_personality_summary(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/city-intelligence/localities")
async def get_all_localities():
    """Get all available locality profiles."""
    if not CITY_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="City Intelligence not available")
    
    try:
        model = get_locality_personality_model()
        profiles = model.get_all_profiles()
        
        return {
            "success": True,
            "count": len(profiles),
            "localities": [
                {
                    "name": p.name,
                    "archetype": p.archetype.value,
                    "growth_stage": p.growth_stage.value,
                    "tagline": p.tagline,
                    "lat": p.lat,
                    "lng": p.lng,
                }
                for p in profiles
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/city-intelligence/compare")
async def compare_localities(locality1: str, locality2: str):
    """Compare two localities across dimensions."""
    if not CITY_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="City Intelligence not available")
    
    try:
        model = get_locality_personality_model()
        comparison = model.compare_localities(locality1, locality2)
        
        if "error" in comparison:
            raise HTTPException(status_code=404, detail=comparison["error"])
        
        return {"success": True, "comparison": comparison}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/city-intelligence/timeline/{locality_name}")
async def get_locality_timeline(locality_name: str):
    """Get evolution timeline for a locality."""
    if not CITY_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="City Intelligence not available")
    
    try:
        timeline_system = get_evolution_timeline_system()
        timeline = timeline_system.get_timeline(locality_name)
        
        if not timeline:
            raise HTTPException(status_code=404, detail=f"Timeline for '{locality_name}' not found")
        
        return {
            "success": True,
            "locality": timeline.name,
            "founding_era": timeline.founding_era,
            "original_character": timeline.original_character,
            "current_phase": timeline.current_phase.value,
            "development_velocity": timeline.development_velocity,
            "phases": [
                {"start": s, "end": e, "phase": p.value}
                for s, e, p in timeline.phases
            ],
            "milestones": [
                {"year": m.year, "event": m.event, "category": m.category, "impact": m.impact}
                for m in timeline.historical_milestones
            ],
            "projections": [
                {"year": p.year, "event": p.event, "probability": p.probability}
                for p in timeline.projected_milestones
            ],
            "key_catalysts": timeline.key_catalysts,
            "key_risks": timeline.key_risks,
            "narrative": timeline.get_full_narrative(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/city-intelligence/risk/{locality_name}")
async def get_locality_risk(locality_name: str, lat: float = None, lng: float = None):
    """Get risk profile for a locality."""
    if not CITY_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="City Intelligence not available")
    
    try:
        calculator = get_risk_index_calculator()
        profile = calculator.get_risk_profile(locality_name, lat, lng)
        
        return {
            "success": True,
            "locality": profile.name,
            "overall_risk": {
                "score": round(profile.overall_risk_score, 1),
                "level": profile.overall_risk_level.value,
            },
            "investment_risk": {
                "score": round(profile.investment_risk_score, 1),
                "level": profile.investment_risk_level.value,
            },
            "components": {
                "hazard": round(profile.hazard.composite_score, 1),
                "infrastructure": round(profile.infrastructure.composite_score, 1),
                "social": round(profile.social.composite_score, 1),
                "speculation": round(profile.speculation.composite_score, 1),
                "policy": round(profile.policy.composite_score, 1),
            },
            "bubble_probability": round(profile.speculation.bubble_probability, 2),
            "warnings": profile.critical_warnings,
            "mitigations": profile.risk_mitigations,
            "summary": profile.get_summary(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/city-intelligence/reason")
async def causal_reasoning(request: dict):
    """Perform causal reasoning about a scenario."""
    if not CITY_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="City Intelligence not available")
    
    try:
        scenario = request.get("scenario", "")
        locality = request.get("locality")
        
        if not scenario:
            raise HTTPException(status_code=400, detail="scenario is required")
        
        engine = get_causal_reasoning_engine()
        chain = engine.reason_about(scenario, locality)
        
        return {
            "success": True,
            "query": chain.query,
            "steps": [
                {
                    "step": s.step_number,
                    "description": s.description,
                    "cause": s.cause,
                    "effect": s.effect,
                    "confidence": s.confidence,
                }
                for s in chain.steps
            ],
            "conclusion": chain.conclusion,
            "confidence": round(chain.overall_confidence, 2),
            "caveats": chain.caveats,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/city-intelligence/knowledge-graph/stats")
async def get_knowledge_graph_stats():
    """Get knowledge graph statistics."""
    if not CITY_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="City Intelligence not available")
    
    try:
        kg = get_urban_knowledge_graph()
        stats = kg.get_statistics()
        
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/city-intelligence/knowledge-graph/context/{locality_id}")
async def get_locality_context(locality_id: str):
    """Get knowledge graph context for a locality."""
    if not CITY_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="City Intelligence not available")
    
    try:
        kg = get_urban_knowledge_graph()
        context = kg.get_locality_context(locality_id)
        
        if not context:
            raise HTTPException(status_code=404, detail=f"Locality '{locality_id}' not found in knowledge graph")
        
        return {"success": True, "context": context}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/city-intelligence/predict")
async def create_prediction(request: dict):
    """Create a calibrated prediction."""
    if not CITY_INTELLIGENCE_AVAILABLE:
        raise HTTPException(status_code=503, detail="City Intelligence not available")
    
    try:
        subject = request.get("subject", "")
        domain = request.get("domain", "property_value")
        point_estimate = request.get("point_estimate")
        unit = request.get("unit", "INR/sqft")
        target_date = request.get("target_date", "2027-01")
        baseline = request.get("baseline")
        reasoning = request.get("reasoning", [])
        
        if not subject or point_estimate is None:
            raise HTTPException(status_code=400, detail="subject and point_estimate are required")
        
        builder = get_prediction_builder()
        
        domain_map = {
            "property_value": PredictionDomain.PROPERTY_VALUE,
            "population": PredictionDomain.POPULATION,
            "traffic": PredictionDomain.TRAFFIC,
            "employment": PredictionDomain.EMPLOYMENT,
        }
        
        pred = builder.create_numeric_prediction(
            subject=subject,
            domain=domain_map.get(domain, PredictionDomain.PROPERTY_VALUE),
            point_estimate=point_estimate,
            unit=unit,
            target_date=target_date,
            baseline=baseline,
            reasoning=reasoning,
        )
        
        return {
            "success": True,
            "prediction": pred.to_dict(),
            "narrative": pred.to_narrative(),
            "dashboard_card": pred.to_dashboard_card(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/city-intelligence/status")
async def get_city_intelligence_status():
    """Get City Intelligence Engine status."""
    return {
        "available": CITY_INTELLIGENCE_AVAILABLE,
        "modules": {
            "locality_personality": CITY_INTELLIGENCE_AVAILABLE,
            "evolution_timeline": CITY_INTELLIGENCE_AVAILABLE,
            "risk_indexes": CITY_INTELLIGENCE_AVAILABLE,
            "knowledge_graph": CITY_INTELLIGENCE_AVAILABLE,
            "causal_reasoning": CITY_INTELLIGENCE_AVAILABLE,
            "prediction_schema": CITY_INTELLIGENCE_AVAILABLE,
        },
        "endpoints": [
            "/api/city-intelligence/locality/{name}",
            "/api/city-intelligence/localities",
            "/api/city-intelligence/compare",
            "/api/city-intelligence/timeline/{name}",
            "/api/city-intelligence/risk/{name}",
            "/api/city-intelligence/reason",
            "/api/city-intelligence/predict",
            "/api/city-intelligence/knowledge-graph/stats",
        ]
    }


# ============== STORYBOARD GENERATION API ==============

class StoryboardRequest(BaseModel):
    scenario: str
    locality: Optional[str] = None
    duration_seconds: Optional[int] = 30

@app.post("/api/storyboard/generate")
async def generate_storyboard(request: StoryboardRequest):
    """Generate a cinematic storyboard for map storytelling."""
    try:
        # Get locality coordinates
        model = get_locality_personality_model() if CITY_INTELLIGENCE_AVAILABLE else None
        
        scenes = []
        localities_involved = []
        
        # Parse scenario to extract localities
        scenario_lower = request.scenario.lower()
        bangalore_areas = [
            "koramangala", "indiranagar", "whitefield", "hsr layout", "jayanagar",
            "marathahalli", "electronic city", "hebbal", "yelahanka", "sarjapur",
            "jp nagar", "btm layout", "banashankari", "malleshwaram", "rajajinagar"
        ]
        
        for area in bangalore_areas:
            if area in scenario_lower:
                localities_involved.append(area.title())
        
        if not localities_involved and request.locality:
            localities_involved = [request.locality]
        
        if not localities_involved:
            localities_involved = ["Koramangala"]  # Default
        
        # Build storyboard scenes
        duration_per_scene = request.duration_seconds // max(len(localities_involved) + 2, 3)
        
        # Opening scene - overview
        scenes.append({
            "scene_id": 1,
            "type": "overview",
            "title": "Bangalore Overview",
            "narration": f"Let's explore: {request.scenario}",
            "camera": {
                "lat": 12.9716,
                "lng": 77.5946,
                "height": 15000,
                "heading": 0,
                "pitch": -45
            },
            "duration_ms": duration_per_scene * 1000,
            "animation": "fly_in"
        })
        
        # Locality scenes
        for i, locality_name in enumerate(localities_involved):
            profile = model.get_profile(locality_name) if model else None
            lat = profile.lat if profile else 12.9716 + (i * 0.02)
            lng = profile.lng if profile else 77.5946 + (i * 0.02)
            tagline = profile.tagline if profile else f"Exploring {locality_name}"
            
            scenes.append({
                "scene_id": i + 2,
                "type": "locality_focus",
                "title": locality_name,
                "narration": tagline,
                "camera": {
                    "lat": lat,
                    "lng": lng,
                    "height": 800,
                    "heading": 45 + (i * 30),
                    "pitch": -30
                },
                "duration_ms": duration_per_scene * 1000,
                "animation": "orbit",
                "locality_data": profile.to_dict() if profile else None
            })
        
        # Closing scene - conclusion
        scenes.append({
            "scene_id": len(scenes) + 1,
            "type": "conclusion",
            "title": "Analysis Complete",
            "narration": f"This concludes our exploration of {', '.join(localities_involved)}.",
            "camera": {
                "lat": 12.9716,
                "lng": 77.5946,
                "height": 5000,
                "heading": 180,
                "pitch": -35
            },
            "duration_ms": duration_per_scene * 1000,
            "animation": "pull_back"
        })
        
        return {
            "success": True,
            "storyboard": {
                "scenario": request.scenario,
                "total_duration_ms": sum(s["duration_ms"] for s in scenes),
                "scene_count": len(scenes),
                "scenes": scenes,
                "localities": localities_involved
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== INVESTMENT LEADERBOARD API ==============

@app.get("/api/investment/leaderboard")
async def get_investment_leaderboard(limit: int = 10):
    """Get top localities ranked by investment score."""
    try:
        localities_data = []
        
        if CITY_INTELLIGENCE_AVAILABLE:
            model = get_locality_personality_model()
            risk_calc = get_risk_index_calculator()
            profiles = model.get_all_profiles()
            
            for profile in profiles[:limit * 2]:  # Get more to filter
                try:
                    risk = risk_calc.get_risk_profile(profile.name, profile.lat, profile.lng)
                    
                    # Calculate investment score (0-100)
                    # Higher growth potential + lower risk = better score
                    growth_factor = profile.personality.get("investment_appeal", 70) if hasattr(profile, 'personality') else 70
                    risk_factor = 100 - risk.investment_risk_score
                    infrastructure_bonus = 10 if profile.growth_stage.value in ["mature", "maturing"] else 0
                    
                    investment_score = int((growth_factor * 0.4 + risk_factor * 0.4 + infrastructure_bonus * 0.2))
                    
                    localities_data.append({
                        "name": profile.name,
                        "investment_score": min(investment_score, 100),
                        "archetype": profile.archetype.value,
                        "growth_stage": profile.growth_stage.value,
                        "risk_level": risk.investment_risk_level.value,
                        "price_trend": 5 + (investment_score % 10),  # Simulated trend
                        "lat": profile.lat,
                        "lng": profile.lng,
                        "tagline": profile.tagline,
                        "grade": "A+" if investment_score >= 85 else ("A" if investment_score >= 75 else ("B+" if investment_score >= 65 else "B"))
                    })
                except:
                    continue
        else:
            # Fallback with sample data
            sample_localities = [
                {"name": "Koramangala", "investment_score": 88, "archetype": "tech_hub", "growth_stage": "mature", "lat": 12.9352, "lng": 77.6245},
                {"name": "Indiranagar", "investment_score": 85, "archetype": "premium_residential", "growth_stage": "mature", "lat": 12.9784, "lng": 77.6408},
                {"name": "Whitefield", "investment_score": 82, "archetype": "tech_hub", "growth_stage": "maturing", "lat": 12.9698, "lng": 77.7500},
                {"name": "HSR Layout", "investment_score": 80, "archetype": "tech_hub", "growth_stage": "maturing", "lat": 12.9116, "lng": 77.6389},
                {"name": "Sarjapur", "investment_score": 78, "archetype": "emerging", "growth_stage": "growing", "lat": 12.8600, "lng": 77.7870},
            ]
            for loc in sample_localities:
                loc["risk_level"] = "low"
                loc["price_trend"] = 8
                loc["tagline"] = f"Bangalore's {loc['archetype'].replace('_', ' ')}"
                loc["grade"] = "A+" if loc["investment_score"] >= 85 else "A"
            localities_data = sample_localities
        
        # Sort by investment score
        localities_data.sort(key=lambda x: x["investment_score"], reverse=True)
        
        return {
            "success": True,
            "leaderboard": localities_data[:limit],
            "total_analyzed": len(localities_data),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== COMPARE PROPERTIES API ==============

class PropertyCompareRequest(BaseModel):
    property_ids: List[int] = []
    localities: List[str] = []

@app.post("/api/compare/properties")
async def compare_properties(request: PropertyCompareRequest):
    """Compare multiple properties or localities."""
    try:
        from database.query_service import get_query_service
        db = get_query_service()
        comparison_data = []
        
        if request.localities and len(request.localities) >= 2:
            # Compare localities using direct SQL
            for locality_name in request.localities[:4]:  # Max 4
                try:
                    result = db.db.execute("""
                        SELECT 
                            COUNT(*) as count,
                            AVG(price) as avg_price,
                            AVG(price_per_sqft) as avg_price_per_sqft,
                            MIN(price) as min_price,
                            MAX(price) as max_price
                        FROM properties 
                        WHERE LOWER(locality) LIKE LOWER(?)
                    """, (f"%{locality_name}%",))
                    
                    if result and len(result) > 0:
                        row = result[0]
                        comparison_data.append({
                            "locality": locality_name,
                            "avg_price": int(row.get("avg_price") or 0),
                            "avg_price_per_sqft": int(row.get("avg_price_per_sqft") or 0),
                            "total_listings": row.get("count", 0),
                            "price_range": {
                                "min": int(row.get("min_price") or 0),
                                "max": int(row.get("max_price") or 0)
                            }
                        })
                    else:
                        comparison_data.append({
                            "locality": locality_name,
                            "avg_price": 0,
                            "avg_price_per_sqft": 0,
                            "total_listings": 0,
                            "price_range": {"min": 0, "max": 0}
                        })
                except Exception as e:
                    comparison_data.append({
                        "locality": locality_name,
                        "avg_price": 0,
                        "error": str(e)
                    })
        
        if request.property_ids and len(request.property_ids) >= 2:
            # Compare specific properties
            for pid in request.property_ids[:4]:
                prop = db.get_property_by_id(str(pid))
                if prop:
                    comparison_data.append({
                        "property_id": pid,
                        "title": prop.get("title", ""),
                        "locality": prop.get("locality", ""),
                        "price": prop.get("price", 0),
                        "area_sqft": prop.get("area_sqft", 0),
                        "price_per_sqft": prop.get("price_per_sqft", 0),
                        "bedrooms": prop.get("bedrooms"),
                        "property_type": prop.get("property_type", "")
                    })
        
        return {
            "success": True,
            "comparison": comparison_data,
            "count": len(comparison_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FACT VERIFIER ENDPOINTS - Truth firewall for LLM claims
# ============================================================================

try:
    from fact_verifier import get_fact_verifier, Claim, ClaimType
    FACT_VERIFIER_AVAILABLE = True
except ImportError:
    FACT_VERIFIER_AVAILABLE = False


class VerifyClaimRequest(BaseModel):
    """Request to verify a single claim."""
    claim_text: str
    claim_type: str = "general"
    value: Optional[Any] = None
    unit: Optional[str] = None
    location: Optional[Dict[str, float]] = None
    property_id: Optional[str] = None
    locality: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class VerifyClaimsRequest(BaseModel):
    """Request to verify multiple claims."""
    claims: List[VerifyClaimRequest]
    request_id: Optional[str] = None


class VerifyNarrativeRequest(BaseModel):
    """Request to verify claims extracted from narrative text."""
    narrative: str
    location: Optional[Dict[str, float]] = None


@app.post("/api/verifier/verify")
async def verify_claims(request: VerifyClaimsRequest):
    """
    Verify multiple LLM claims against deterministic data sources.
    
    This is the core "truth firewall" for Valora AI.
    """
    if not FACT_VERIFIER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Fact verifier service not available")
    
    try:
        verifier = get_fact_verifier()
        
        # Convert request to Claim objects
        claims = []
        for i, c in enumerate(request.claims):
            claims.append(Claim(
                claim_id=f"c_{i}",
                claim_text=c.claim_text,
                claim_type=c.claim_type,
                value=c.value,
                unit=c.unit,
                location=c.location,
                property_id=c.property_id,
                locality=c.locality,
                context=c.context
            ))
        
        # Verify all claims
        response = verifier.verify_claims(claims, request.request_id)
        
        return {
            "success": True,
            "request_id": response.request_id,
            "overall_status": response.overall_status,
            "verification_rate": response.verification_rate,
            "total_claims": response.total_claims,
            "verified_count": response.verified_count,
            "unverified_count": response.unverified_count,
            "results": [
                {
                    "claim_id": r.claim_id,
                    "claim_text": r.claim_text,
                    "status": r.status,
                    "confidence": r.confidence,
                    "evidence": [
                        {
                            "source": e.source,
                            "query_type": e.query_type,
                            "actual_value": e.actual_value,
                            "expected_value": e.expected_value,
                            "match": e.match,
                            "details": e.details
                        } for e in r.evidence
                    ],
                    "rewrite_suggestion": r.rewrite_suggestion
                } for r in response.results
            ],
            "warnings": response.warnings,
            "timestamp": response.timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")


@app.post("/api/verifier/verify-narrative")
async def verify_narrative(request: VerifyNarrativeRequest):
    """
    Extract and verify claims from narrative text.
    
    Extracts verifiable claims (prices, distances, counts, etc.) from
    natural language text and verifies each against data sources.
    """
    if not FACT_VERIFIER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Fact verifier service not available")
    
    try:
        verifier = get_fact_verifier()
        
        # Extract claims from narrative
        claims = verifier.extract_claims_from_text(request.narrative, request.location)
        
        if not claims:
            return {
                "success": True,
                "message": "No verifiable claims found in narrative",
                "overall_status": "no_claims",
                "claims_extracted": 0,
                "results": []
            }
        
        # Verify extracted claims
        response = verifier.verify_claims(claims)
        
        return {
            "success": True,
            "request_id": response.request_id,
            "overall_status": response.overall_status,
            "verification_rate": response.verification_rate,
            "claims_extracted": len(claims),
            "verified_count": response.verified_count,
            "unverified_count": response.unverified_count,
            "results": [
                {
                    "claim_id": r.claim_id,
                    "claim_text": r.claim_text,
                    "status": r.status,
                    "confidence": r.confidence,
                    "rewrite_suggestion": r.rewrite_suggestion,
                    "evidence": [
                        {
                            "source": e.source,
                            "actual_value": e.actual_value,
                            "expected_value": e.expected_value,
                            "match": e.match
                        } for e in r.evidence
                    ]
                } for r in response.results
            ],
            "warnings": response.warnings
        }
    except Exception as e:
        print(f"[ERROR] Narrative verification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify narrative: {str(e)}")

@app.get("/api/verifier/status")
async def verifier_status():
    """Get fact verifier service status."""
    return {
        "available": FACT_VERIFIER_AVAILABLE,
        "claim_types": [ct.value for ct in ClaimType] if FACT_VERIFIER_AVAILABLE else [],
        "description": "Fact verifier validates LLM claims against deterministic data sources"
    }


# ============================================================================
# OBSERVABILITY ENDPOINTS - Metrics and monitoring
# ============================================================================

try:
    from observability import get_metrics, MetricsCollector
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False


@app.get("/api/metrics")
async def metrics_summary():
    """Get metrics summary for monitoring dashboard."""
    if not OBSERVABILITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Observability not available")
    
    metrics = get_metrics()
    return {
        "success": True,
        **metrics.get_summary()
    }


@app.get("/api/metrics/endpoints")
async def metrics_endpoints():
    """Get per-endpoint latency metrics."""
    if not OBSERVABILITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Observability not available")
    
    metrics = get_metrics()
    return {
        "success": True,
        "endpoints": metrics.get_endpoint_stats()
    }


@app.get("/api/metrics/verifier")
async def metrics_verifier():
    """Get fact verifier metrics."""
    if not OBSERVABILITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Observability not available")
    
    metrics = get_metrics()
    return {
        "success": True,
        "verifier": metrics.get_verifier_stats()
    }


@app.get("/api/metrics/prometheus")
async def metrics_prometheus():
    """Export metrics in Prometheus format."""
    if not OBSERVABILITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Observability not available")
    
    from fastapi.responses import PlainTextResponse
    metrics = get_metrics()
    return PlainTextResponse(content=metrics.get_prometheus_metrics(), media_type="text/plain")


# ============================================================================
# AUTH & RBAC - Protected admin endpoints
# ============================================================================

try:
    from auth import get_auth_service, get_current_user, check_rate_limit, User, Role, Permission
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False


@app.get("/api/auth/status")
async def auth_status():
    """Get authentication service status."""
    return {
        "available": AUTH_AVAILABLE,
        "roles": [r.value for r in Role] if AUTH_AVAILABLE else [],
        "description": "RBAC authentication for protected endpoints"
    }


@app.get("/api/auth/me")
async def auth_me(request: Request):
    """Get current user info from API key."""
    if not AUTH_AVAILABLE:
        raise HTTPException(status_code=503, detail="Auth not available")
    
    # Get API key from header or query
    api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    
    if not api_key:
        return {
            "authenticated": False,
            "user": None,
            "role": "anonymous"
        }
    
    auth_service = get_auth_service()
    user = auth_service.authenticate(api_key)
    
    if user:
        return {
            "authenticated": True,
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "role": user.role.value,
                "rate_limit": user.rate_limit,
                "permissions": [p.value for p in user.permissions]
            }
        }
    
    return {
        "authenticated": False,
        "user": None,
        "role": "anonymous"
    }


@app.get("/api/auth/rate-limit")
async def auth_rate_limit(request: Request):
    """Get current rate limit status."""
    if not AUTH_AVAILABLE:
        raise HTTPException(status_code=503, detail="Auth not available")
    
    api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    auth_service = get_auth_service()
    
    if api_key:
        user = auth_service.authenticate(api_key)
        if user:
            return auth_service.get_rate_limit_info(user.user_id, user.rate_limit)
    
    # Anonymous user - use IP
    client_ip = request.client.host if request.client else "unknown"
    return auth_service.get_rate_limit_info(client_ip, 50)  # 50 req/min for anonymous


# ============================================================================
# USER PREFERENCES - Session memory and preference learning
# ============================================================================

try:
    from spatial.spatial_memory import get_spatial_memory, SpatialMemoryService
    SPATIAL_MEMORY_AVAILABLE = True
except ImportError:
    try:
        from spatial_memory import get_spatial_memory, SpatialMemoryService
        SPATIAL_MEMORY_AVAILABLE = True
    except ImportError:
        SPATIAL_MEMORY_AVAILABLE = False
        get_spatial_memory = None


class UserPreferencesRequest(BaseModel):
    user_id: str = "default"
    preferred_areas: Optional[List[str]] = None
    budget_range: Optional[List[float]] = None  # [min, max] in lakhs
    preferred_property_types: Optional[List[str]] = None
    preferred_amenities: Optional[List[str]] = None
    avoid_areas: Optional[List[str]] = None


@app.get("/api/preferences/{user_id}")
async def get_user_preferences(user_id: str = "default"):
    """Get user preferences and session memory."""
    if not SPATIAL_MEMORY_AVAILABLE:
        return {
            "success": True,
            "user_id": user_id,
            "preferences": {
                "preferred_areas": [],
                "budget_range": None,
                "preferred_property_types": [],
                "preferred_amenities": [],
                "avoid_areas": [],
                "exploration_style": "balanced"
            },
            "recent_locations": [],
            "comparisons": []
        }
    
    session = get_spatial_memory(user_id)
    
    return {
        "success": True,
        "user_id": user_id,
        "preferences": session.preferences.to_dict(),
        "recent_locations": [loc.to_dict() for loc in session.visit_history[-10:]],
        "comparisons": [{"location_a": c.location_a, "location_b": c.location_b, "winner": c.winner} for c in session.comparisons[-5:]]
    }


@app.post("/api/preferences/{user_id}")
async def update_user_preferences(user_id: str, request: UserPreferencesRequest):
    """Update user preferences."""
    if not SPATIAL_MEMORY_AVAILABLE:
        return {"success": True, "message": "Preferences noted (memory service not available)"}
    
    session = get_spatial_memory(user_id)
    
    if request.preferred_areas:
        session.preferences.preferred_areas = request.preferred_areas
    if request.budget_range:
        session.preferences.budget_range = tuple(request.budget_range) if len(request.budget_range) == 2 else None
    if request.preferred_property_types:
        session.preferences.preferred_property_types = request.preferred_property_types
    if request.preferred_amenities:
        session.preferences.preferred_amenities = request.preferred_amenities
    if request.avoid_areas:
        session.preferences.avoid_areas = request.avoid_areas
    
    session._save_session()
    
    return {
        "success": True,
        "message": "Preferences updated",
        "preferences": session.preferences.to_dict()
    }


@app.post("/api/preferences/{user_id}/location")
async def record_location_visit(user_id: str, request: Request):
    """Record a location visit for preference learning."""
    if not SPATIAL_MEMORY_AVAILABLE:
        return {"success": True, "message": "Visit noted"}
    
    body = await request.json()
    session = get_spatial_memory(user_id)
    
    session.record_visit(
        lat=body.get("lat", 0),
        lng=body.get("lng", 0),
        name=body.get("name", "Unknown"),
        intent=body.get("intent", "explore"),
        actions=body.get("actions", []),
        sentiment=body.get("sentiment", "neutral")
    )
    
    return {"success": True, "message": "Location visit recorded"}


@app.delete("/api/preferences/{user_id}")
async def clear_user_preferences(user_id: str):
    """Clear user preferences and history."""
    if not SPATIAL_MEMORY_AVAILABLE:
        return {"success": True, "message": "Preferences cleared"}
    
    session = get_spatial_memory(user_id)
    session.clear_session()
    
    return {"success": True, "message": "Preferences and history cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




