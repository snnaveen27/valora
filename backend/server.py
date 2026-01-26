"""
Valora AI Backend Server
- Geocoding via local Nominatim
- Place resolution for GIS AI Agent
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import statistics
import httpx
import json
from pathlib import Path
from collections import OrderedDict
import time
import os
from dotenv import load_dotenv
from area_analyzer import AreaAnalyzer
from local_geocoder import get_local_geocoder
import multi_source_scraper

# Load environment variables
load_dotenv()

# Initialize services - gracefully handle missing folders (database is primary source)
osm_data_dir = Path(__file__).parent.parent / 'src' / 'data' / 'osm_extracted'
terrain_dir = Path(__file__).parent.parent / 'src' / 'data' / 'terrain'
properties_dir = Path(__file__).parent.parent / 'src' / 'data' / 'posted_properties'

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
    from terrain_service import TerrainService
    terrain_service = TerrainService(terrain_dir)
    print("[OK] Terrain service initialized")
except Exception as e:
    print(f"[WARNING] Terrain service not available: {e}")
    terrain_service = None

# Import and initialize property service (uses database, folder is optional)
try:
    from property_service import get_property_service
    property_service = get_property_service(properties_dir)
    print("[OK] Property service initialized (uses database)")
except Exception as e:
    print(f"[WARNING] Property service not available: {e}")
    property_service = None

# Phase 1: Import and initialize RAG, Valuation, and Spatial Reasoning services
data_dir = Path(__file__).parent.parent / 'src' / 'data'

try:
    from rag_service import get_rag_service
    rag_service = get_rag_service(data_dir)
    RAG_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] RAG service not available: {e}")
    rag_service = None
    RAG_AVAILABLE = False

# Import and initialize simulation & digital twin
try:
    from simulation_engine import get_simulation_engine, ScenarioInput
    from narrative_generator import get_narrative_generator
    from digital_twin import get_digital_twin, StateChange
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
    from valuation_model import get_valuation_model
    valuation_model = get_valuation_model(data_dir)
    VALUATION_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] Valuation model not available: {e}")
    valuation_model = None
    VALUATION_AVAILABLE = False

try:
    from spatial_reasoning import get_spatial_service
    spatial_service = get_spatial_service(data_dir)
    SPATIAL_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] Spatial reasoning not available: {e}")
    spatial_service = None
    SPATIAL_AVAILABLE = False

# Phase 2: GIS Multi-Agent Orchestrator
from gis_agents import get_gis_orchestrator, IntentRouter, Intent, _compute_market_facts
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
from admin_routes import router as admin_router
app.include_router(admin_router)

# CORS for frontend
_default_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
]
_origins_env = os.getenv("FRONTEND_ORIGINS", "")
_allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()] or _default_origins

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
    """Load tileset index - prefer database, fallback to files"""
    global tileset_index
    
    # Try database first (check if buildings have polygon data)
    try:
        from database.query_service import get_query_service
        query_service = get_query_service()
        
        # Check if database has polygon data
        test_query = query_service.db.execute(
            "SELECT COUNT(*) as cnt FROM buildings WHERE polygon_coords IS NOT NULL LIMIT 1"
        )
        has_polygons = test_query[0]['cnt'] > 0 if test_query else False
        
        if has_polygons:
            # Load tileset structure from data.zip or generate grid
            tileset_path = Path(__file__).parent.parent / 'src' / 'data' / 'data.zip'
            if tileset_path.exists():
                try:
                    import zipfile
                    with zipfile.ZipFile(tileset_path, 'r') as z:
                        tileset_index = json.loads(z.read('3dtiles/tileset.json'))
                    # Mark as database source
                    tileset_index['source'] = 'database'
                    print(f"[OK] Using database for buildings: {len(tileset_index['tiles'])} tiles, {tileset_index['totalBuildings']} buildings")
                    return
                except Exception as e:
                    print(f"[WARNING] Failed to load tileset structure: {e}")
            
            # Generate tile grid
            tiles = {}
            tile_size = 0.01
            for lng_start in range(7740, 7780):
                for lat_start in range(1280, 1310):
                    lng = lng_start / 100
                    lat = lat_start / 100
                    tile_id = f"{lng_start}_{lat_start}"
                    tiles[tile_id] = {
                        'min_lng': lng, 'max_lng': lng + tile_size,
                        'min_lat': lat, 'max_lat': lat + tile_size,
                        'max_height': 30, 'count': 0
                    }
            
            tileset_index = {
                'tiles': tiles,
                'totalBuildings': query_service.get_database_stats().get('buildings', 0),
                'source': 'database'
            }
            print(f"[OK] Using database for buildings: {len(tiles)} tiles")
            return
    except Exception as e:
        print(f"[WARNING] Database check failed: {e}")
    
    # Fallback to file-based tiles
    tileset_path = Path(__file__).parent.parent / 'src' / 'data' / 'data.zip'
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
tiles_dir = Path(__file__).parent.parent / 'src' / 'data' / '3dtiles' / 'tiles'
if tiles_dir.exists():
    app.mount("/tiles", StaticFiles(directory=str(tiles_dir)), name="tiles")

# Nominatim config (local instance)
NOMINATIM_URL = os.getenv("NOMINATIM_URL", "http://localhost:8088")

# Bangalore bounding box for biasing results
BANGALORE_BBOX = {
    "viewbox": "77.3,13.2,78.0,12.7",  # lon_min,lat_max,lon_max,lat_min
    "bounded": 1
}

# LLM Configuration (supports OpenRouter and Local LLM)
LLM_CONFIG_FILE = Path(__file__).parent / 'llm_config.json'

def load_llm_config():
    """Load LLM config from file or return defaults."""
    defaults = {
        'provider': 'openrouter',  # 'openrouter' or 'local'
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
        except Exception as e:
            print(f"[WARNING] Failed to load LLM config: {e}")
    return defaults

def save_llm_config(config: dict):
    """Save LLM config to file."""
    try:
        with open(LLM_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save LLM config: {e}")
        return False

# Load config at startup
llm_config = load_llm_config()
print(f"[OK] LLM Provider: {llm_config['provider']}")

# Legacy env vars for compatibility
OPENROUTER_API_KEY = llm_config.get('openrouter_api_key') or os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = llm_config.get('openrouter_model', "meta-llama/llama-3.2-3b-instruct:free")
OPENROUTER_MODEL_REASONING = os.getenv("OPENROUTER_MODEL_REASONING", "meta-llama/llama-3.2-3b-instruct:free")
OPENROUTER_MODEL_VISION = os.getenv("OPENROUTER_MODEL_VISION", "qwen/qwen2.5-vl-7b-instruct:free")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Mapbox configuration
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY", "")

class PlaceResult(BaseModel):
    place_id: int
    name: str
    display_name: str
    lat: float
    lng: float
    type: str
    importance: float

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[Dict[str, Any]] = None  # Map state, selected building, location, etc.
    bbox: Optional[List[float]] = None

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
        "mapbox_api_key": MAPBOX_API_KEY
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
        zip_path = Path(__file__).parent.parent / 'src' / 'data' / 'data.zip'
        
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
        
        # Direct query - NO LIMIT - get ALL buildings in tile bounds
        db_path = Path(__file__).parent.parent / 'src' / 'data' / 'valora.db'
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT osm_id, name, building_type, height, levels, 
                   latitude as lat, longitude as lng, polygon_coords
            FROM buildings
            WHERE polygon_coords IS NOT NULL
              AND latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
        """, (min_lat, max_lat, min_lng, max_lng))
        buildings = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Convert to GeoJSON
        features = []
        for b in (buildings or []):
            height = b.get('height') or 10
            
            try:
                coords = json.loads(b['polygon_coords'])
                geometry = {'type': 'Polygon', 'coordinates': [coords]}
            except:
                continue
            
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
                    "avg_price_per_sqft": round(market.get('avg_price_per_sqft', 0)),
                    "median_price": round(market.get('median_price', 0)),
                    "price_trend_pct": round(market.get('price_trend_pct', 0), 1),
                    "active_listings": market.get('active_listings', 0),
                    "demand_level": market.get('demand_level', 'Medium'),
                    "price_range": {
                        "min": round(market.get('min_price', 0)),
                        "max": round(market.get('max_price', 0))
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
            if val_result.get('success'):
                result["valuation"] = {
                    "estimated_price_2bhk_1200sqft": val_result.get('estimated_price'),
                    "price_per_sqft": val_result.get('price_per_sqft'),
                    "confidence": val_result.get('confidence', 'medium'),
                    "price_range": val_result.get('price_range'),
                    "key_factors": val_result.get('factors', [])[:5]
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
    
    if result.get("micro_economics", {}).get("rental_yield_estimate", 0) > 5:
        recommendations.append(f"Strong rental yield potential: {result['micro_economics']['rental_yield_estimate']}%")
    
    if result.get("spatial", {}).get("transport_count", 0) > 5:
        recommendations.append("Excellent public transport connectivity")
    
    if result.get("market", {}).get("demand_level") == "High":
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


@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest):
    """
    Phase 2 GIS AI Agent with Multi-Agent Orchestration.
    
    Architecture:
    1. IntentRouter classifies user query
    2. GIS Orchestrator dispatches to deterministic agents (Spatial, Terrain, Property, RAG)
    3. Agents collect grounded facts from real data
    4. LLM synthesizes narrative from facts (never invents data)
    5. Dashboard populated entirely from computed facts
    
    Supports both OpenRouter (cloud) and Local LLM (offline) providers.
    """
    import re as re_module
    from admin_routes import get_active_llm_config
    
    # Get current LLM config
    current_llm_config = get_active_llm_config()
    llm_provider = current_llm_config.get('provider', 'openrouter')
    
    # Validate config based on provider
    if llm_provider == 'openrouter':
        api_key = current_llm_config.get('openrouter_api_key', '')
        if not api_key:
            raise HTTPException(status_code=503, detail="OpenRouter API key not configured. Go to Admin Panel > Config to set it up.")
    else:
        local_url = current_llm_config.get('local_url', '')
        if not local_url:
            raise HTTPException(status_code=503, detail="Local LLM URL not configured. Go to Admin Panel > Config to set it up.")
    
    # Extract user query
    user_query = ""
    if request.messages:
        user_query = request.messages[-1].content
    
    context = request.context or {}
    
    # =========================================================================
    # PHASE 2: Multi-Agent Fact Gathering (all deterministic, no LLM)
    # =========================================================================
    facts, intent, ui_actions, digital_twin_state, reasoning_trace = gis_orchestrator.gather_facts(
        query=user_query,
        context=context,
    )
    
    # Build dashboard from grounded facts
    title = facts.location_name or "Analysis"
    if intent == Intent.ANALYZE_BUILDING and facts.building_type:
        title = f"{facts.building_type.title()} Building Analysis"
    elif intent == Intent.PROPERTY_SEARCH:
        title = f"Properties near {facts.location_name or 'Location'}"
    elif intent == Intent.SIMULATE:
        title = f"Simulation: {facts.location_name or 'Area'}"
    
    dashboard = facts.to_dashboard(title=title)
    
    # Add simulation results to dashboard if present
    simulation_data = None
    if facts.simulation_results:
        simulation_data = facts.simulation_results
        dashboard["simulation"] = simulation_data
    
    # Add viewport info if available
    viewport = context.get('viewport')
    if viewport:
        viewport_context = f"\n**Viewport:** Center ~{viewport.get('center', {}).get('lat', 12.97):.2f}, {viewport.get('center', {}).get('lng', 77.64):.2f}, {viewport.get('buildingsCount', 0)} buildings loaded"
    else:
        viewport_context = ""
    
    # =========================================================================
    # PHASE 2: LLM Narrative Synthesis (facts only, no invention)
    # =========================================================================
    system_prompt = gis_orchestrator.build_system_prompt(intent)
    
    # Build context from grounded facts
    facts_context = facts.to_context_string()
    
    # Add simulation facts if present
    if simulation_data:
        facts_context += f"\n\n**Simulation Results:**\n{json.dumps(simulation_data['impacts'], indent=2)}"

    full_system = system_prompt + "\n\n**GROUNDED FACTS (use ONLY these):**\n" + facts_context + viewport_context
    
    messages_with_context = [{"role": "system", "content": full_system}]
    
    for msg in request.messages:
        messages_with_context.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # Call LLM for narrative synthesis only (supports OpenRouter or Local LLM)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if llm_provider == 'openrouter':
                # OpenRouter (cloud)
                response = await client.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {current_llm_config.get('openrouter_api_key', '')}",
                        "HTTP-Referer": "http://localhost:3000",
                        "X-Title": "Valora AI - GIS Intelligence"
                    },
                    json={
                        "model": current_llm_config.get('openrouter_model', OPENROUTER_MODEL),
                        "messages": messages_with_context,
                        "temperature": 0.5,
                        "max_tokens": 600
                    }
                )
            else:
                # Local LLM (offline)
                response = await client.post(
                    current_llm_config.get('local_url', 'http://127.0.0.1:11434/v1/chat/completions'),
                    json={
                        "model": current_llm_config.get('local_model', 'llama3.2'),
                        "messages": messages_with_context,
                        "temperature": 0.5,
                        "max_tokens": 600,
                        "stream": False
                    }
                )
            
            if response.status_code != 200:
                provider_name = "OpenRouter" if llm_provider == 'openrouter' else "Local LLM"
                raise HTTPException(status_code=response.status_code, detail=f"{provider_name} error: {response.text[:200]}")
            
            result = response.json()
            ai_message = result['choices'][0]['message']['content']
            
            # Extract SIDEBAR content if present
            sidebar_content = ""
            if "[SIDEBAR]" in ai_message and "[/SIDEBAR]" in ai_message:
                match = re_module.search(r"\[SIDEBAR\](.*?)\[/SIDEBAR\]", ai_message, re_module.DOTALL)
                if match:
                    sidebar_content = match.group(1).strip()
                    ai_message = re_module.sub(r"\[SIDEBAR\].*?\[/SIDEBAR\]", "", ai_message, flags=re_module.DOTALL).strip()
            
            if sidebar_content:
                dashboard["ai_analysis"] = sidebar_content
            
            # Ensure dashboard has title
            if not dashboard.get("title"):
                dashboard["title"] = title

            # Manage credits (deduct 1 for chat)
            user_id = context.get('user_id', 'user_demo')
            credit_resp = await manage_credits(CreditAction(user_id=user_id, action='deduct', reason='chat'))
            
            # Add simulation and twin state to response
            return {
                "success": True,
                "message": ai_message,
                "intent": intent.value,  # Expose detected intent
                "dashboard": dashboard if dashboard.get('title') or dashboard.get('cards') else None,
                "ui_actions": ui_actions,
                "simulation": simulation_data,
                "digital_twin_state": digital_twin_state,
                "user_credits": credit_resp if credit_resp.get('success') else None,
                "facts_summary": {  # Expose key facts for transparency
                    "location": facts.location_name,
                    "poi_count": facts.poi_count,
                    "accessibility": facts.accessibility_score,
                    "walkability": facts.walkability_score,
                    "avg_price_sqft": facts.avg_price_per_sqft,
                    "active_listings": facts.active_listings,
                },
                "reasoning_trace": reasoning_trace,  # Chain-of-thought visibility
                "usage": result.get('usage', {})
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

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
    Index all data sources into Pinecone vector database.
    
    - force: If true, clears existing index before re-indexing
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    try:
        results = rag_service.index_all(properties_dir, osm_data_dir, force_reindex=force)
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


# ============== BUILDING ANALYSIS ENDPOINT ==============

class BuildingAnalysisRequest(BaseModel):
    lat: float
    lng: float
    height: Optional[float] = None
    levels: Optional[int] = None
    buildingType: Optional[str] = "building"
    area: Optional[float] = None
    name: Optional[str] = None

_cache_building_analysis = TTLCache(maxsize=256, ttl_seconds=600)

@app.post("/api/building/analyze")
async def analyze_building(request: BuildingAnalysisRequest):
    """
    Comprehensive building analysis using Phase 1 services.
    Auto-triggered when user clicks a building on the map.
    
    Returns:
    - Spatial summary (POIs, transport, accessibility/walkability scores)
    - Valuation estimate and market stats
    - AI-generated insights
    - Price trends and area importance
    """
    import re
    
    lat, lng = request.lat, request.lng
    cache_key = f"{round(lat, 5)}|{round(lng, 5)}|{request.height}|{request.buildingType}"
    
    cached = _cache_building_analysis.get(cache_key)
    if cached is not None:
        return cached
    
    result = {
        "success": True,
        "building": {
            "lat": lat,
            "lng": lng,
            "height": request.height,
            "levels": request.levels,
            "type": request.buildingType,
            "area": request.area,
            "name": request.name
        },
        "spatial": None,
        "valuation": None,
        "market": None,
        "ai_analysis": None,
        "area_importance": None,
        "recommendations": []
    }
    
    # 1. Spatial Analysis (Phase 1)
    if SPATIAL_AVAILABLE:
        try:
            summary = spatial_service.get_summary(lat, lng, radius_m=1000)
            result["spatial"] = {
                "total_features": summary.total_features,
                "by_category": summary.by_category,
                "nearest": summary.nearest,
                "accessibility_score": summary.accessibility_score,
                "walkability_score": summary.walkability_score,
                "amenity_density": summary.amenity_density
            }
            
            # Store spatial factors for AI to analyze
            result["area_importance"] = {
                "factors": {
                    "accessibility": summary.accessibility_score,
                    "walkability": summary.walkability_score,
                    "amenity_density": round(summary.amenity_density, 2),
                    "total_features": summary.total_features,
                    "poi_count": summary.by_category.get('poi', 0),
                    "transport_count": summary.by_category.get('transport', 0)
                }
            }
        except Exception as e:
            print(f"Spatial analysis error: {e}")
    
    # 2. Valuation (Phase 1)
    if VALUATION_AVAILABLE:
        try:
            # Estimate property value
            covered_area = request.area or 1000
            levels = request.levels or max(1, int((request.height or 10) / 3))
            bedrooms = max(1, levels)  # Rough estimate
            
            prop_type = "residential"
            if request.buildingType and any(t in request.buildingType.lower() for t in ['commercial', 'office', 'retail', 'shop']):
                prop_type = "commercial"
            
            valuation = valuation_model.valuate(
                lat=lat,
                lng=lng,
                bedrooms=bedrooms,
                bathrooms=max(1, bedrooms - 1),
                covered_area=covered_area,
                floors=levels,
                property_type=prop_type
            )
            
            result["valuation"] = {
                "estimated_price": valuation.estimated_price,
                "price_per_sqft": valuation.price_per_sqft,
                "confidence": valuation.confidence,
                "price_range": {
                    "low": valuation.price_range[0],
                    "high": valuation.price_range[1]
                },
                "factors": valuation.factors,
                "comparables": valuation.comparables[:3]  # Top 3 comparables
            }
            
            # Market stats - let AI interpret the data
            market = valuation_model.get_market_stats(lat, lng, radius_km=1.5)
            if market and market.get('total_properties', 0) > 0:
                result["market"] = {
                    "avg_price": market.get('avg_price', 0),
                    "avg_price_per_sqft": market.get('avg_price_per_sqft', 0),
                    "total_properties": market.get('total_properties', 0),
                    "price_range": {
                        "min": market.get('min_price', 0),
                        "max": market.get('max_price', 0)
                    },
                    "price_variance": market.get('max_price', 0) - market.get('min_price', 0) if market.get('max_price', 0) and market.get('min_price', 0) else 0
                }
        except Exception as e:
            print(f"Valuation error: {e}")
    
    # 3. AI-Generated Analysis
    if OPENROUTER_API_KEY:
        try:
            # Build context for AI
            context_parts = []
            context_parts.append(f"""**Building Details:**
- Location: {lat:.5f}, {lng:.5f}
- Height: {request.height or 'Unknown'}m ({request.levels or 'Unknown'} floors)
- Type: {request.buildingType or 'Unknown'}
- Area: {request.area or 'Unknown'}m²""")
            
            if result["spatial"]:
                s = result["spatial"]
                context_parts.append(f"""**Spatial Analysis (1km radius):**
- Total Features: {s['total_features']}
- POIs: {s['by_category'].get('poi', 0)}
- Transport: {s['by_category'].get('transport', 0)}
- Accessibility Score: {s['accessibility_score']}/100
- Walkability Score: {s['walkability_score']}/100
- Amenity Density: {s['amenity_density']:.2f}/sqkm""")
            
            if result["valuation"]:
                v = result["valuation"]
                context_parts.append(f"""**Valuation Estimate:**
- Estimated Price: ₹{v['estimated_price']:,.0f}
- Price/sqft: ₹{v['price_per_sqft']:,.0f}
- Confidence: {v['confidence']*100:.0f}%
- Range: ₹{v['price_range']['low']:,.0f} - ₹{v['price_range']['high']:,.0f}""")
            
            if result["market"]:
                m = result["market"]
                context_parts.append(f"""**Market Stats (1.5km):**
- Avg Price: ₹{m['avg_price']:,.0f}
- Avg Price/sqft: ₹{m['avg_price_per_sqft']:,.0f}
- Properties: {m['total_properties']}
- Price Range: ₹{m['price_range']['min']:,.0f} - ₹{m['price_range']['max']:,.0f}
- Price Variance: ₹{m['price_variance']:,.0f}""")
            
            if result["area_importance"]:
                ai = result["area_importance"]['factors']
                context_parts.append(f"""**Area Metrics:**
- Accessibility Score: {ai['accessibility']}/100
- Walkability Score: {ai['walkability']}/100
- Amenity Density: {ai['amenity_density']}/sqkm
- POI Count: {ai['poi_count']}
- Transport Count: {ai['transport_count']}""")
            
            # Get RAG context if available
            if RAG_AVAILABLE:
                rag_context = rag_service.get_context_for_query(
                    f"property investment {request.buildingType} near {lat}, {lng}",
                    lat=lat, lng=lng, radius_km=2.0, max_results=5
                )
                if rag_context:
                    context_parts.append(f"**Nearby Properties (RAG):**\n{rag_context}")
            
            analysis_prompt = """You are Valora AI, a real estate intelligence system. Analyze this building location in Bangalore.

**CRITICAL: Output ONLY valid JSON. No extra text before or after.**

Calculate ALL metrics from the data provided:

1. **area_importance_score** (0-100): Synthesize accessibility (weight: 35%), walkability (30%), amenity density (20%), POI count (10%), transport count (5%)
2. **area_grade**: A+ (≥90), A (≥80), B+ (≥70), B (≥60), C (≥50), D (≥40), F (<40)
3. **growth_estimate_1y** (%): Estimate market growth based on: location quality, price variance, amenity density, accessibility. Prime locations (A/A+) = 10-15%, Good (B+/B) = 6-10%, Average (C/D) = 3-6%
4. **demand_index**: High (A+/A + low vacancy), Medium (B+/B/C), Low (D/F or high variance)
5. **analysis**: 4-5 paragraphs with **Location Quality**, **Investment Potential**, **Livability**, **Key Risks**, **Recommendation** (Buy/Hold/Avoid)
6. **recommendations**: 2-4 specific insights based on actual data (e.g., "485 POIs within 1km - exceptional amenity access")

**Output ONLY this JSON (no markdown, no text before/after):**
{
  "area_importance_score": <number>,
  "area_grade": "<letter>",
  "growth_estimate_1y": <number>,
  "demand_index": "<High|Medium|Low>",
  "analysis": "<paragraphs>",
  "recommendations": ["<specific insight 1>", "<specific insight 2>"]
}"""

            messages = [
                {"role": "system", "content": analysis_prompt},
                {"role": "user", "content": "\n\n".join(context_parts)}
            ]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "HTTP-Referer": "http://localhost:3000",
                        "X-Title": "Valora AI - Building Analysis"
                    },
                    json={
                        "model": OPENROUTER_MODEL,
                        "messages": messages,
                        "temperature": 0.5,  # Lower temp for more consistent JSON
                        "max_tokens": 1200  # Increased for full JSON response
                    }
                )
                
                if response.status_code == 200:
                    ai_result = response.json()
                    ai_content = ai_result['choices'][0]['message']['content'].strip()
                    
                    # Try to parse JSON response from AI
                    try:
                        import re
                        ai_data = None
                        
                        # Try parsing as direct JSON first
                        if ai_content.startswith('{'):
                            try:
                                ai_data = json.loads(ai_content)
                            except:
                                pass
                        
                        # Try extracting from markdown code block
                        if not ai_data:
                            json_match = re.search(r'```(?:json)?\s*(\{.+?\})\s*```', ai_content, re.DOTALL)
                            if json_match:
                                ai_data = json.loads(json_match.group(1))
                        
                        # Try finding any JSON object in the response
                        if not ai_data:
                            json_match = re.search(r'(\{[^{}]*"area_importance_score"[^{}]*\})', ai_content, re.DOTALL)
                            if json_match:
                                ai_data = json.loads(json_match.group(1))
                        
                        if ai_data:
                            # Use AI-calculated metrics
                            result["area_importance"]["score"] = ai_data.get("area_importance_score", 0)
                            result["area_importance"]["grade"] = ai_data.get("area_grade", "C")
                            
                            if result.get("market"):
                                result["market"]["growth_1y"] = ai_data.get("growth_estimate_1y", 0)
                                result["market"]["demand_index"] = ai_data.get("demand_index", "Medium")
                            
                            result["ai_analysis"] = ai_data.get("analysis", "")
                            result["recommendations"] = ai_data.get("recommendations", [])
                        else:
                            # Fallback: store raw text, use defaults
                            print(f"[WARNING] Could not parse AI JSON, using raw text")
                            result["ai_analysis"] = ai_content
                            # Set minimal defaults if AI didn't provide structured data
                            if "score" not in result.get("area_importance", {}):
                                result["area_importance"]["score"] = 50
                                result["area_importance"]["grade"] = "C"
                    except Exception as parse_err:
                        print(f"AI response parsing error: {parse_err}")
                        result["ai_analysis"] = ai_content
                        if "score" not in result.get("area_importance", {}):
                            result["area_importance"]["score"] = 50
                            result["area_importance"]["grade"] = "C"
        except Exception as e:
            print(f"AI analysis error: {e}")
            result["ai_analysis"] = None
    
    # Recommendations are now generated by AI, not hardcoded
    # If AI didn't provide recommendations, leave empty
    if "recommendations" not in result or not result["recommendations"]:
        result["recommendations"] = []
    
    _cache_building_analysis.set(cache_key, result)
    return result


# ============== PHASE 4: SIMULATION & STORYBOARD ENDPOINTS ==============

try:
    from simulation_engine import get_simulation_engine, ScenarioInput
    from narrative_generator import get_narrative_generator
    from digital_twin import get_digital_twin, StateChange
    from dataclasses import asdict
    simulation_engine = get_simulation_engine()
    narrative_generator = get_narrative_generator()
    digital_twin = get_digital_twin()
    SIMULATION_AVAILABLE = True
    print("[OK] Simulation engine initialized")
    print("[OK] Digital twin engine initialized")
except Exception as e:
    print(f"[WARNING] Simulation engine not available: {e}")
    simulation_engine = None
    narrative_generator = None
    digital_twin = None
    SIMULATION_AVAILABLE = False

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


# ============== PHASE 5: CREDIT SYSTEM ==============

# In-memory credit tracking (production would use database)
user_credits = {}
DEFAULT_CREDITS = 100  # New users get 100 credits

class CreditAction(BaseModel):
    user_id: str
    action: str  # 'add', 'deduct', 'check'
    amount: Optional[int] = 0
    reason: Optional[str] = None

# Credit costs for different operations
CREDIT_COSTS = {
    'chat': 1,
    'analysis': 2,
    'simulation': 5,
    'storyboard': 10,
    'property_search': 1,
    'valuation': 3,
    'rag_search': 1
}

@app.post("/api/credits")
async def manage_credits(request: CreditAction):
    """
    Manage user credits (Windsurf-style usage tracking).
    
    Actions:
    - check: Get current credit balance
    - add: Add credits to account
    - deduct: Deduct credits for usage
    """
    user_id = request.user_id
    
    # Initialize user if not exists
    if user_id not in user_credits:
        user_credits[user_id] = {
            'balance': DEFAULT_CREDITS,
            'total_used': 0,
            'history': []
        }
    
    user = user_credits[user_id]
    
    if request.action == 'check':
        return {
            "success": True,
            "user_id": user_id,
            "balance": user['balance'],
            "total_used": user['total_used'],
            "recent_history": user['history'][-10:]
        }
    
    elif request.action == 'add':
        user['balance'] += request.amount
        user['history'].append({
            'action': 'add',
            'amount': request.amount,
            'reason': request.reason or 'Credit top-up',
            'balance_after': user['balance']
        })
        return {
            "success": True,
            "user_id": user_id,
            "amount_added": request.amount,
            "new_balance": user['balance']
        }
    
    elif request.action == 'deduct':
        cost = request.amount or CREDIT_COSTS.get(request.reason, 1)
        if user['balance'] < cost:
            return {
                "success": False,
                "error": "Insufficient credits",
                "balance": user['balance'],
                "cost": cost
            }
        user['balance'] -= cost
        user['total_used'] += cost
        user['history'].append({
            'action': 'deduct',
            'amount': cost,
            'reason': request.reason or 'Usage',
            'balance_after': user['balance']
        })
        return {
            "success": True,
            "user_id": user_id,
            "amount_deducted": cost,
            "new_balance": user['balance']
        }
    
    return {"success": False, "error": "Invalid action"}

@app.get("/api/credits/{user_id}")
async def get_credits(user_id: str):
    """Get credit balance for a user."""
    if user_id not in user_credits:
        user_credits[user_id] = {
            'balance': DEFAULT_CREDITS,
            'total_used': 0,
            'history': []
        }
    
    user = user_credits[user_id]
    return {
        "success": True,
        "user_id": user_id,
        "balance": user['balance'],
        "total_used": user['total_used'],
        "credit_costs": CREDIT_COSTS
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

@app.post("/api/scrape/config/save")
async def save_scraper_config(config: dict):
    """Save scraper configuration to JSON file."""
    try:
        config_file = Path(__file__).parent.parent / "src" / "data" / "scraper_config.json"
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
        config_file = Path(__file__).parent.parent / "src" / "data" / "scraper_config.json"
        
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
            "credits": ["/api/credits", "/api/credits/{user_id}"],
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
