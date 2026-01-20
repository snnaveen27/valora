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

# Load environment variables
load_dotenv()

# Initialize area analyzer, local geocoder, and terrain service
osm_data_dir = Path(__file__).parent.parent / 'src' / 'data' / 'osm_extracted'
terrain_dir = Path(__file__).parent.parent / 'src' / 'data' / 'terrain'
properties_dir = Path(__file__).parent.parent / 'src' / 'data' / 'posted_properties'
area_analyzer = AreaAnalyzer(osm_data_dir)
local_geocoder = get_local_geocoder(osm_data_dir)

# Import and initialize terrain service
from terrain_service import TerrainService
terrain_service = TerrainService(terrain_dir)

# Import and initialize property service
from property_service import get_property_service
property_service = get_property_service(properties_dir)

# Phase 1: Import and initialize RAG, Valuation, and Spatial Reasoning services
data_dir = Path(__file__).parent.parent / 'src' / 'data'

try:
    from rag_service import get_rag_service
    rag_service = get_rag_service(data_dir)
    RAG_AVAILABLE = True
except Exception as e:
    print(f"⚠️  RAG service not available: {e}")
    rag_service = None
    RAG_AVAILABLE = False

try:
    from valuation_model import get_valuation_model
    valuation_model = get_valuation_model(data_dir)
    VALUATION_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Valuation model not available: {e}")
    valuation_model = None
    VALUATION_AVAILABLE = False

try:
    from spatial_reasoning import get_spatial_service
    spatial_service = get_spatial_service(data_dir)
    SPATIAL_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Spatial reasoning not available: {e}")
    spatial_service = None
    SPATIAL_AVAILABLE = False

# Phase 2: GIS Multi-Agent Orchestrator
from gis_agents import get_gis_orchestrator, IntentRouter, Intent
gis_orchestrator = get_gis_orchestrator(
    geocoder=local_geocoder,
    spatial_service=spatial_service,
    terrain_service=terrain_service,
    property_service=property_service,
    valuation_model=valuation_model,
    rag_service=rag_service,
    area_analyzer=area_analyzer,
)
print("✅ GIS Multi-Agent Orchestrator initialized")

app = FastAPI(title="Valora AI Backend", version="2.0.0")

# CORS for frontend
_default_origins = [
    "http://localhost:3000",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3002",
]
_origins_env = os.getenv("FRONTEND_ORIGINS", "")
_allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()] or _default_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
_cache_mappls_tiles = TTLCache(maxsize=512, ttl_seconds=86400)
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
    """Load tileset index for tile-based building loading"""
    global tileset_index
    tileset_path = Path(__file__).parent.parent / 'src' / 'data' / '3dtiles' / 'tileset.json'
    
    if not tileset_path.exists():
        print("⚠️  Tileset not found. Run: python scripts/generate_3dtiles.py")
        return
    
    with open(tileset_path) as f:
        tileset_index = json.load(f)
    
    print(f"✅ Loaded tileset index: {len(tileset_index['tiles'])} tiles, {tileset_index['totalBuildings']} buildings")

# Mount static files for tiles
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

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

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
    """Health check including Nominatim status"""
    nominatim_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{NOMINATIM_URL}/status")
            nominatim_ok = resp.status_code == 200
    except Exception:
        pass
    
    return {
        "backend": "ok",
        "nominatim": "ok" if nominatim_ok else "unavailable",
        "nominatim_url": NOMINATIM_URL
    }

@app.get("/api/config")
async def get_config():
    """Get frontend configuration including API keys"""
    return {
        "has_mappls": bool(os.getenv("MAPPLS_API_KEY"))
    }

@app.get("/api/mappls/tiles/{z}/{x}/{y}.png")
async def get_mappls_tile(z: int, x: int, y: int):
    """Proxy MapPLS tiles through backend to avoid browser CORS issues."""
    mappls_key = os.getenv("MAPPLS_API_KEY")
    if not mappls_key:
        raise HTTPException(status_code=503, detail="MAPPLS_API_KEY not configured")

    cache_key = f"{z}/{x}/{y}"
    cached = _cache_mappls_tiles.get(cache_key)
    if cached is not None:
        content, content_type = cached
        return Response(content=content, media_type=content_type)

    tile_url = f"https://apis.mappls.com/advancedmaps/v1/{mappls_key}/still_map_layer/{z}/{x}/{y}.png"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            upstream = await client.get(tile_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MapPLS tile fetch failed: {str(e)}")

    if upstream.status_code != 200:
        raise HTTPException(status_code=upstream.status_code, detail="MapPLS tile fetch failed")

    content_type = upstream.headers.get("content-type", "image/png")
    _cache_mappls_tiles.set(cache_key, (upstream.content, content_type))
    return Response(content=upstream.content, media_type=content_type)

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
    for tile_id, tile_info in tileset_index['tiles'].items():
        # Check if tile intersects viewport
        if (tile_info['min_lng'] <= max_lng and tile_info['max_lng'] >= min_lng and
            tile_info['min_lat'] <= max_lat and tile_info['max_lat'] >= min_lat):
            matching_tiles.append({
                'id': tile_id,
                'count': tile_info['count'],
                'url': f'/tiles/{tile_id}.json'
            })
    
    return {
        'tiles': matching_tiles,
        'total': len(matching_tiles)
    }

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
    """
    import re as re_module
    
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=503, detail="OpenRouter API key not configured")
    
    # Extract user query
    user_query = ""
    if request.messages:
        user_query = request.messages[-1].content
    
    context = request.context or {}
    
    # =========================================================================
    # PHASE 2: Multi-Agent Fact Gathering (all deterministic, no LLM)
    # =========================================================================
    facts, intent, ui_actions = gis_orchestrator.gather_facts(
        query=user_query,
        context=context,
    )
    
    # Build dashboard from grounded facts
    title = facts.location_name or "Analysis"
    if intent == Intent.ANALYZE_BUILDING and facts.building_type:
        title = f"{facts.building_type.title()} Building Analysis"
    elif intent == Intent.PROPERTY_SEARCH:
        title = f"Properties near {facts.location_name or 'Location'}"
    
    dashboard = facts.to_dashboard(title=title)
    
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
    
    full_system = system_prompt + "\n\n**GROUNDED FACTS (use ONLY these):**\n" + facts_context + viewport_context
    
    messages_with_context = [{"role": "system", "content": full_system}]
    
    for msg in request.messages:
        messages_with_context.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # Call LLM for narrative synthesis only
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "Valora AI - GIS Intelligence"
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": messages_with_context,
                    "temperature": 0.5,  # Lower temp for factual synthesis
                    "max_tokens": 600
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"OpenRouter API error: {response.text}")
            
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

            return {
                "success": True,
                "message": ai_message,
                "intent": intent.value,  # Expose detected intent
                "dashboard": dashboard if dashboard.get('title') or dashboard.get('cards') else None,
                "ui_actions": ui_actions,
                "facts_summary": {  # Expose key facts for transparency
                    "location": facts.location_name,
                    "poi_count": facts.poi_count,
                    "accessibility": facts.accessibility_score,
                    "walkability": facts.walkability_score,
                    "avg_price_sqft": facts.avg_price_per_sqft,
                    "active_listings": facts.active_listings,
                },
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
                            print(f"⚠️  Could not parse AI JSON, using raw text")
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


# ============== PHASE 1: STATUS ENDPOINT ==============

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
