"""
Valora AI - Unified Chat Routes
Two endpoints only:
  /api/chat        - Non-streaming (JSON response)
  /api/chat/stream - Streaming SSE (primary for frontend)

Both use the same pipeline:
  1. IntentRouter classifies query (pattern-based, fast)
  2. GIS Orchestrator gathers grounded facts from real data
  3. Ollama LLM synthesizes narrative from facts only
  4. Response includes dashboard, ui_actions, facts for frontend

LLM: Local Ollama (qwen3:4b-instruct) default, Cloud (OpenRouter) for heavy reasoning.
"""

import json
import re
import time
import uuid
import asyncio
import logging
import sqlite3
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.circuit_breaker import CircuitBreakerOpen, get_circuit_breaker, CircuitBreakerConfig, get_all_circuit_status
from search.query_cache import get_chat_cache

logger = logging.getLogger("valora.chat")

router = APIRouter(tags=["chat"])

# Circuit breakers for LLM providers
_ollama_breaker = get_circuit_breaker("ollama", CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30))
_openrouter_breaker = get_circuit_breaker("openrouter", CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60))

# Chat response cache — avoids redundant LLM calls for identical queries
_chat_cache = get_chat_cache()

def _is_cloud_model(model_name: str) -> bool:
    """Check if the model name indicates an Ollama cloud model."""
    if not model_name:
        return False
    nl = model_name.lower()
    return ":cloud" in nl or nl.endswith("-cloud")


def _get_ollama_client_for_model(model_name: str):
    """Get an Ollama client configured for a specific model.
    Cloud models (e.g. kimi-k2.5:cloud) are served by Ollama transparently.
    """
    from ai.ollama_client import OllamaClient
    import json
    from pathlib import Path
    
    # Load config to get max_context
    config_path = Path(__file__).parent.parent / "llm_config.json"
    max_context = 8192  # default
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            max_context = config.get('max_context', 8192)
    except Exception as e:
        print(f"[chat_routes] Failed to load max_context from config: {e}")
    
    is_cloud = _is_cloud_model(model_name)
    return OllamaClient(
        model=model_name,
        timeout=180 if is_cloud else 120,
        max_context=max_context,
    )


# Cached available models (refreshed every 60s)
_cached_models: List[str] = []
_models_fetched_at: float = 0.0
_MODELS_CACHE_TTL = 60.0  # seconds


async def _fetch_available_models() -> List[str]:
    """Fetch available model names from Ollama /api/tags. Cached for 60s."""
    global _cached_models, _models_fetched_at
    now = time.time()
    if _cached_models and (now - _models_fetched_at) < _MODELS_CACHE_TTL:
        return _cached_models
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:11434/api/tags",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _cached_models = [m["name"] for m in data.get("models", [])]
                    _models_fetched_at = now
                    logger.info(f"[ModelRouter] Discovered {len(_cached_models)} Ollama models: {_cached_models}")
    except Exception as e:
        logger.warning(f"[ModelRouter] Failed to fetch Ollama models: {e}")
        if not _cached_models:
            _cached_models = ["qwen3:4b-instruct"]  # fallback
    return _cached_models


# ---------------------------------------------------------------------------
# OpenRouter streaming helper
# ---------------------------------------------------------------------------
async def _stream_openrouter(messages: list, model: str, temperature: float, max_tokens: int):
    """Stream from OpenRouter API. Yields text chunks. Accepts proper messages array."""
    import os
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key or api_key == "sk-or-v1-your-api-key-here":
        raise Exception("OpenRouter API key not configured")

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://valora.ai",
        "X-Title": "Valora AI",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload, headers=headers,
                timeout=aiohttp.ClientTimeout(total=180),
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise Exception(f"OpenRouter {resp.status}: {error[:200]}")
                async for line in resp.content:
                    line_str = line.decode("utf-8", errors="ignore").strip()
                    if not line_str or not line_str.startswith("data:"):
                        continue
                    data_str = line_str[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        chunk = delta.get("content", "")
                        if chunk:
                            yield chunk
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.warning(f"[OpenRouter] Streaming failed: {e} — will fall back to Ollama cloud")
        raise


# ---------------------------------------------------------------------------
# Request model (same shape the frontend already sends)
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None


# ---------------------------------------------------------------------------
# Service singletons — injected by server.py at startup via init_chat_deps()
# ---------------------------------------------------------------------------
_gis_orchestrator = None
_ollama_client = None


def init_chat_deps(gis_orchestrator=None, ollama_client=None):
    """Called by server.py to inject the initialized services."""
    global _gis_orchestrator, _ollama_client
    if gis_orchestrator is not None:
        _gis_orchestrator = gis_orchestrator
    if ollama_client is not None:
        _ollama_client = ollama_client


def _get_gis_orchestrator():
    global _gis_orchestrator
    if _gis_orchestrator is None:
        # Fallback: import from server module if not injected
        try:
            import server
            _gis_orchestrator = server.gis_orchestrator
        except (ImportError, AttributeError):
            from ai.gis_agents import get_gis_orchestrator
            _gis_orchestrator = get_gis_orchestrator()
    return _gis_orchestrator


def _get_ollama_client():
    global _ollama_client
    if _ollama_client is None:
        from ai.ollama_client import get_ollama_client
        _ollama_client = get_ollama_client()
    return _ollama_client


def _get_rate_limiter():
    """Get credits rate limiter singleton."""
    from ai.credits_rate_limiter import get_rate_limiter
    return get_rate_limiter()


def _check_credits(user_id: str, action: str = "local_query"):
    """Check if user has credits. Returns (allowed, result)."""
    try:
        rl = _get_rate_limiter()
        result = rl.check_rate_limit(user_id, action)
        return result.allowed, result
    except Exception as e:
        logger.warning(f"Credits check failed (allowing): {e}")
        return True, None  # fail-open for MVP


def _deduct_credits(user_id: str, action: str = "local_query", intent: str = None):
    """Deduct credits after successful query."""
    try:
        rl = _get_rate_limiter()
        rl.record_usage(user_id, action, success=True, query_type=intent)
    except Exception as e:
        logger.warning(f"Credits deduction failed: {e}")


# ---------------------------------------------------------------------------
# Conversation memory — SQLite-backed persistent store keyed by thread_id
# ---------------------------------------------------------------------------
_MEMORY_DB = Path(__file__).parent.parent / "conversation_memory.db"
_MAX_HISTORY = 10  # keep last 10 turns (20 messages) per thread

_MEMORY_INIT_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp REAL NOT NULL,
    intent TEXT
);
CREATE INDEX IF NOT EXISTS idx_thread ON conversations(thread_id);
"""

def _get_memory_conn():
    """Get thread-local connection to conversation_memory.db."""
    try:
        from core.sqlite_pool import get_pool
        pool = get_pool("conversation_memory", str(_MEMORY_DB), _MEMORY_INIT_SQL)
        return pool.get()
    except Exception:
        conn = sqlite3.connect(str(_MEMORY_DB))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn


def _get_conversation_history(thread_id: Optional[str]) -> List[Dict[str, str]]:
    if not thread_id:
        return []
    try:
        conn = _get_memory_conn()
        rows = conn.execute(
            "SELECT role, content FROM conversations WHERE thread_id = ? ORDER BY id DESC LIMIT ?",
            (thread_id, _MAX_HISTORY * 2),
        ).fetchall()
        # Reverse to chronological order
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    except Exception as e:
        logger.warning(f"Failed to load conversation history: {e}")
        return []


def _store_conversation_turn(thread_id: Optional[str], user_msg: str, assistant_msg: str, intent: str = None):
    if not thread_id:
        return
    try:
        conn = _get_memory_conn()
        now = time.time()
        conn.execute(
            "INSERT INTO conversations (thread_id, role, content, timestamp, intent) VALUES (?, ?, ?, ?, ?)",
            (thread_id, "user", user_msg, now, intent),
        )
        conn.execute(
            "INSERT INTO conversations (thread_id, role, content, timestamp, intent) VALUES (?, ?, ?, ?, ?)",
            (thread_id, "assistant", assistant_msg, now, intent),
        )
        conn.commit()
        # Prune old messages beyond limit
        conn.execute("""
            DELETE FROM conversations WHERE id NOT IN (
                SELECT id FROM conversations WHERE thread_id = ? ORDER BY id DESC LIMIT ?
            ) AND thread_id = ?
        """, (thread_id, _MAX_HISTORY * 2, thread_id))
        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to store conversation turn: {e}")


def _extract_previous_location(thread_id: Optional[str]) -> Optional[str]:
    """Extract the last mentioned location from conversation history for context carry."""
    history = _get_conversation_history(thread_id)
    if not history:
        return None
    # Walk backwards through user messages looking for location references
    from ai.valora_brain_core import ValoraBrainCore
    brain = ValoraBrainCore()
    for msg in reversed(history):
        if msg["role"] == "user":
            intent_result = brain.classify_intent(msg["content"])
            loc = intent_result.slots.get("location")
            if loc:
                return loc
    return None


# ---------------------------------------------------------------------------
# Zone analysis fast-path (polygon / buffer — no LLM needed)
# ---------------------------------------------------------------------------
def _try_zone_fast_path(user_query: str, context: Dict) -> Optional[Dict]:
    """Return a zone analysis response if the query is about a drawn polygon/buffer."""
    polygon_analysis = context.get("polygonAnalysis")
    buffer_analysis = context.get("bufferAnalysis")
    zone_analysis = polygon_analysis or buffer_analysis
    if not zone_analysis or not user_query:
        return None

    ql = user_query.lower()
    if not any(k in ql for k in ["polygon", "buffer", "zone", "inside this", "drawn"]):
        return None

    zone_type = zone_analysis.get("zone_type") or ("polygon" if polygon_analysis else "buffer")
    metrics = zone_analysis.get("metrics", {}) or {}
    counts = zone_analysis.get("counts", {}) or {}
    building_stats = zone_analysis.get("building_stats", {}) or {}

    lines = [f"**Custom Zone Analysis ({zone_type})**"]
    if zone_type == "polygon":
        if metrics.get("area_m2") is not None:
            lines.append(f"- **Area:** {metrics['area_m2']:,.0f} m²")
        if metrics.get("perimeter_m") is not None:
            lines.append(f"- **Perimeter:** {metrics['perimeter_m']:,.0f} m")
    else:
        if metrics.get("radius_m") is not None:
            lines.append(f"- **Radius:** {metrics['radius_m']:,.0f} m")

    lines.append(f"- **Buildings:** {counts.get('buildings', 0)}")
    lines.append(f"- **Properties:** {counts.get('properties', 0)}")
    lines.append(f"- **POIs:** {counts.get('pois', 0)}")
    lines.append(f"- **Transport Stops:** {counts.get('transport_stops', 0)}")

    if building_stats:
        if building_stats.get("avg_height_m") is not None:
            lines.append(f"- **Avg building height:** {building_stats['avg_height_m']:.1f} m")
        if building_stats.get("max_height_m") is not None:
            lines.append(f"- **Max building height:** {building_stats['max_height_m']:.1f} m")
        if building_stats.get("dominant_type"):
            lines.append(f"- **Dominant building type:** {building_stats['dominant_type']}")

    return {
        "success": True,
        "message": "\n".join(lines),
        "intent": "analyze_area",
        "dashboard": {
            "title": f"Zone Analysis ({zone_type})",
            "cards": [{"title": "Counts", "items": [
                {"label": "Buildings", "value": counts.get("buildings", 0)},
                {"label": "Properties", "value": counts.get("properties", 0)},
                {"label": "POIs", "value": counts.get("pois", 0)},
                {"label": "Transport", "value": counts.get("transport_stops", 0)},
            ]}],
        },
        "ui_actions": [],
        "facts": {"zone_type": zone_type, "zone_metrics": metrics, "zone_counts": counts},
        "facts_summary": {
            "zone_type": zone_type,
            "buildings": counts.get("buildings", 0),
            "properties": counts.get("properties", 0),
        },
        "cached": False,
        "fast_response": True,
    }


# ---------------------------------------------------------------------------
# Greeting fast-path — instant responses, no LLM needed
# ---------------------------------------------------------------------------
_GREETING_PATTERNS = {
    "hi", "hello", "hey", "hii", "hiii", "yo", "sup",
    "good morning", "good afternoon", "good evening",
    "how are you", "how r u", "what's up", "whats up",
    "are you there", "anyone there",
    "namaste", "namaskar",
}

_GREETING_RESPONSES = [
    "Hello! I'm Valora AI, your Bangalore real estate intelligence assistant. Ask me anything about properties, areas, prices, or navigate the 3D map!",
    "Hi there! I can help you analyze any area in Bangalore, search properties, compare locations, and much more. What would you like to know?",
    "Hey! Ready to explore Bangalore's real estate? Try asking me to analyze an area, find properties, or compare neighborhoods.",
]

_HELP_PATTERNS = {"help", "what can you do", "how to use", "features", "commands"}

_HELP_RESPONSE = """I'm **Valora AI** — your Bangalore real estate intelligence platform. Here's what I can do:

- **Navigate**: "Show me Koramangala" or "Go to Whitefield"
- **Search properties**: "Find 2BHK apartments near Indiranagar under 80L"
- **Analyze areas**: "Tell me about HSR Layout" or "Analyze Jayanagar"
- **Compare**: "Compare Whitefield vs Electronic City"
- **Investment**: "Is Sarjapur Road good for investment?"
- **Simulate**: "What if a metro station opens in Yelahanka?"
- **Building analysis**: Click any building on the map and ask about it

All insights are grounded in real data — I never make up numbers."""


def _try_greeting_fast_path(user_query: str) -> Optional[Dict]:
    """Return instant response for greetings/help without hitting LLM."""
    ql = user_query.lower().strip().rstrip("!?.)")
    
    if ql in _GREETING_PATTERNS or any(ql.startswith(g) for g in _GREETING_PATTERNS):
        import random
        return {
            "success": True,
            "message": random.choice(_GREETING_RESPONSES),
            "intent": "greeting",
            "dashboard": None,
            "ui_actions": [],
            "facts": {},
            "facts_summary": {},
            "cached": False,
            "fast_response": True,
        }
    
    if ql in _HELP_PATTERNS or any(h in ql for h in _HELP_PATTERNS):
        return {
            "success": True,
            "message": _HELP_RESPONSE,
            "intent": "help",
            "dashboard": None,
            "ui_actions": [],
            "facts": {},
            "facts_summary": {},
            "cached": False,
            "fast_response": True,
        }
    
    return None


# ---------------------------------------------------------------------------
# Shared pipeline: classify → gather facts → build prompt → call LLM
# ---------------------------------------------------------------------------
def _classify_intent(user_query: str, context: Dict):
    """Classify intent using pattern matcher, with LLM fallback for ambiguous queries."""
    from ai.gis_agents import IntentRouter, Intent
    selected_building = context.get("selectedBuilding")
    selected_location = context.get("selectedLocation") or context.get("selectedPlace")
    intent = IntentRouter.classify(
        user_query,
        has_building=bool(selected_building),
        has_location=bool(selected_location),
    )
    # If pattern matcher couldn't classify (returns GENERAL), try LLM fallback
    if intent == Intent.GENERAL:
        try:
            llm_intent = _llm_classify_intent(user_query)
            if llm_intent and llm_intent != Intent.GENERAL:
                logger.info(f"LLM reclassified '{user_query[:50]}' from GENERAL → {llm_intent.value}")
                return llm_intent
        except Exception as e:
            logger.debug(f"LLM intent fallback failed (using GENERAL): {e}")
    return intent


def _llm_classify_intent(user_query: str):
    """Use Ollama LLM to classify ambiguous queries. Synchronous wrapper for async client."""
    from ai.gis_agents import Intent
    import asyncio

    INTENT_MAP = {
        "navigate": Intent.NAVIGATE,
        "analyze_area": Intent.ANALYZE_AREA,
        "analyze_building": Intent.ANALYZE_BUILDING,
        "property_search": Intent.PROPERTY_SEARCH,
        "valuation": Intent.VALUATION,
        "terrain": Intent.TERRAIN,
        "comparison": Intent.COMPARISON,
        "simulate": Intent.SIMULATE,
        "investment": Intent.INVESTMENT,
        "market_trend": Intent.MARKET_TREND,
        "general": Intent.GENERAL,
    }

    try:
        client = _get_ollama_client()
        # Run the async classify_intent in a new event loop if needed
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're inside an async context — use a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, client.classify_intent(user_query))
                intent_str, confidence = future.result(timeout=10)
        else:
            intent_str, confidence = asyncio.run(client.classify_intent(user_query))

        if confidence >= 0.5 and intent_str in INTENT_MAP:
            return INTENT_MAP[intent_str]
    except Exception as e:
        logger.debug(f"LLM classify failed: {e}")

    return None


def _gather_facts(user_query: str, context: Dict, intent):
    """Run GIS orchestrator to collect grounded facts."""
    orchestrator = _get_gis_orchestrator()
    facts, intent_out, ui_actions, digital_twin_state, reasoning_trace = orchestrator.gather_facts(
        query=user_query,
        context=context,
        intent=intent,
        task_planner=None,
    )
    return facts, intent_out, ui_actions, digital_twin_state, reasoning_trace


def _build_dashboard(facts, intent):
    """Build dashboard dict from AgentFacts."""
    from ai.gis_agents import Intent
    title = facts.location_name or "Analysis"
    if intent == Intent.ANALYZE_BUILDING and facts.building_type:
        title = f"{facts.building_type.title()} Building Analysis"
    elif intent == Intent.PROPERTY_SEARCH:
        title = f"Properties near {facts.location_name or 'Location'}"
    elif intent == Intent.SIMULATE:
        title = f"Simulation: {facts.location_name or 'Area'}"
    return facts.to_dashboard(title=title)


def _build_llm_messages(user_query: str, request: ChatRequest, facts, intent, context: Dict, history: List[Dict]):
    """Build the messages array for the LLM call."""
    orchestrator = _get_gis_orchestrator()
    system_prompt = orchestrator.build_system_prompt(intent)
    facts_context = facts.to_context_string()

    # Viewport context (camera position + viewport bounds)
    viewport_ctx = ""
    map_center = context.get("mapCenter")
    viewport_bounds = context.get("viewportBounds")
    if map_center:
        viewport_ctx = f"\n\n**VIEWPORT:** Camera at {map_center.get('lat', 12.97):.4f}, {map_center.get('lng', 77.64):.4f} (height {map_center.get('height', 0):.0f}m)"
    if viewport_bounds:
        viewport_ctx += f"\n**VISIBLE AREA:** {viewport_bounds.get('south', 0):.4f}–{viewport_bounds.get('north', 0):.4f}N, {viewport_bounds.get('west', 0):.4f}–{viewport_bounds.get('east', 0):.4f}E"

    # Zone context
    zone_ctx = ""
    try:
        za = context.get("polygonAnalysis") or context.get("bufferAnalysis")
        if za:
            zone_ctx = "\n\n**DRAWN ZONE:**\n" + json.dumps({
                "zone_type": za.get("zone_type", "polygon"),
                "metrics": za.get("metrics", {}),
                "counts": za.get("counts", {}),
                "building_stats": za.get("building_stats", {}),
            }, indent=2)
    except Exception:
        pass

    # Analysis panel context
    analysis_ctx = ""
    current_analysis = context.get("currentAnalysis", {})
    viewport_analysis = context.get("viewportAnalysis", {})
    if current_analysis or viewport_analysis:
        parts = []
        area_name = current_analysis.get("areaName") or viewport_analysis.get("area_name")
        if area_name:
            parts.append(f"**Current Area:** {area_name}")
        market = current_analysis.get("market") or viewport_analysis.get("market")
        if market:
            parts.append(f"**Market:** ₹{market.get('avg_price_per_sqft', 0):,}/sqft, {market.get('demand_level', 'Medium')} demand")
        spatial = current_analysis.get("spatial") or viewport_analysis.get("spatial")
        if spatial:
            parts.append(f"**Infrastructure:** {spatial.get('poi_count', 0)} POIs, {spatial.get('transport_count', 0)} transport, Walkability {spatial.get('walkability_score', 0)}/100")
        if parts:
            analysis_ctx = "\n\n**ANALYSIS PANEL DATA:**\n" + "\n".join(parts)

    full_system = (
        system_prompt
        + "\n\n**GROUNDED FACTS (use ONLY these):**\n"
        + facts_context
        + viewport_ctx
        + analysis_ctx
        + zone_ctx
    )

    messages = [{"role": "system", "content": full_system}]

    # Inject conversation history for context carry
    for h in history[-6:]:  # last 3 turns
        messages.append({"role": h["role"], "content": h["content"]})

    # Current conversation messages
    for msg in request.messages:
        messages.append({"role": msg.role, "content": msg.content})

    return messages


def _build_facts_data(facts) -> Dict:
    """Build the facts dict for the response."""
    return {
        "location_name": facts.location_name,
        "lat": facts.lat,
        "lng": facts.lng,
        "poi_count": facts.poi_count,
        "transport_count": facts.transport_count,
        "accessibility_score": facts.accessibility_score,
        "walkability_score": facts.walkability_score,
        "amenity_density": facts.amenity_density,
        "avg_price_per_sqft": facts.avg_price_per_sqft,
        "price_trend_pct": facts.price_trend_pct,
        "active_listings": facts.active_listings,
        "demand_level": facts.demand_level,
        "elevation_m": facts.elevation_m,
        "flood_risk": facts.flood_risk,
        "sky_view_factor": facts.sky_view_factor,
        "view_quality": facts.view_quality,
        "skyline_character": facts.skyline_character,
        "optimal_floor": facts.optimal_floor,
        "locality_archetype": facts.locality_archetype,
        "locality_growth_stage": facts.locality_growth_stage,
        "locality_tagline": facts.locality_tagline,
        "locality_personality": facts.locality_personality,
        "overall_risk_score": facts.overall_risk_score,
        "risk_level": facts.risk_level,
        "risk_profile": facts.risk_profile,
        "risk_warnings": facts.risk_warnings,
        "causal_analysis": facts.causal_analysis,
        "confidence_score": facts.confidence_score,
        "location_score": facts.location_score,
        "location_strengths": facts.location_strengths,
        "location_weaknesses": facts.location_weaknesses,
        "investment_outlook": facts.investment_outlook,
    }


def _strip_thinking_tags(text: str) -> tuple:
    """Strip <think>...</think> tags, return (clean_text, thinking_content)."""
    thinking = ""
    clean = text
    if "<think>" in text.lower():
        match = re.search(r"<think>(.*?)</think>", text, re.DOTALL | re.IGNORECASE)
        if match:
            thinking = match.group(1).strip()
            clean = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    return clean, thinking


def _generate_fallback_response(intent, facts) -> str:
    """Generate a basic response from grounded facts when LLM fails."""
    from ai.gis_agents import Intent
    name = facts.location_name or "this area"
    parts = []
    if intent == Intent.NAVIGATE:
        if facts.lat and facts.lng:
            parts.append(f"Navigating to **{name}** ({facts.lat:.4f}, {facts.lng:.4f}).")
    elif intent == Intent.PROPERTY_SEARCH:
        parts.append(f"**Property Search near {name}**")
        if facts.active_listings:
            parts.append(f"Found {facts.active_listings} active listings.")
        if facts.avg_price_per_sqft:
            parts.append(f"Average price: ₹{facts.avg_price_per_sqft:,.0f}/sqft.")
    elif intent == Intent.ANALYZE_AREA:
        parts.append(f"**Area Analysis: {name}**")
        if facts.poi_count is not None:
            parts.append(f"POIs: {facts.poi_count}, Transport: {facts.transport_count or 0}")
        if facts.walkability_score is not None:
            parts.append(f"Walkability: {facts.walkability_score}/100")
    else:
        parts.append(f"Analysis for **{name}**.")
        if facts.avg_price_per_sqft:
            parts.append(f"Avg price: ₹{facts.avg_price_per_sqft:,.0f}/sqft.")

    return "\n".join(parts) if parts else f"Analysis complete for {name}."


def _verify_llm_output(llm_text: str, facts) -> Optional[Dict[str, Any]]:
    """Run post-LLM fact verification (Truth Firewall).
    
    Extracts verifiable claims from LLM output and checks them against
    the grounded facts already gathered by GIS agents.
    Returns a verification summary dict, or None if no claims found.
    """
    try:
        from ai.fact_verifier import get_fact_verifier
        verifier = get_fact_verifier()

        location = None
        if facts.lat and facts.lng:
            location = {"lat": facts.lat, "lng": facts.lng}

        claims = verifier.extract_claims_from_text(llm_text, location=location)
        if not claims:
            return None

        result = verifier.verify_claims(claims)
        return {
            "total_claims": result.total_claims,
            "verified": result.verified_count,
            "unverified": result.unverified_count,
            "status": result.overall_status,
            "verification_rate": round(result.verification_rate, 1),
            "warnings": result.warnings[:3] if result.warnings else [],
        }
    except Exception as e:
        logger.debug(f"Fact verification skipped: {e}")
        return None


# ---------------------------------------------------------------------------
# Endpoint 1: /api/chat  (non-streaming, JSON response)
# ---------------------------------------------------------------------------
@router.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Non-streaming chat endpoint. Returns full JSON response.
    Used as fallback when streaming is not available.
    
    Pipeline: IntentRouter → GIS Orchestrator → Ollama → JSON
    """
    user_query = request.messages[-1].content if request.messages else ""
    context = request.context or {}
    thread_id = context.get("thread_id")
    user_id = context.get("user_id", "anonymous")

    # Greeting fast-path (no LLM, no credits needed)
    greeting_resp = _try_greeting_fast_path(user_query)
    if greeting_resp:
        _store_conversation_turn(thread_id, user_query, greeting_resp["message"], intent="greeting")
        return greeting_resp

    # Credits check
    allowed, rate_result = _check_credits(user_id)
    if not allowed:
        return {
            "success": False,
            "message": rate_result.reason or "Credit limit reached. Please upgrade or wait for reset.",
            "intent": "rate_limited",
            "credits": {
                "remaining": rate_result.remaining_credits,
                "total": rate_result.total_credits,
                "tier": rate_result.tier,
            },
        }

    # Zone fast-path
    zone_resp = _try_zone_fast_path(user_query, context)
    if zone_resp:
        return zone_resp

    # Context carry: inject previous location if query uses pronouns
    ql = user_query.lower()
    if any(w in ql for w in ["there", "that area", "that place", "same area", "this area"]):
        prev_loc = _extract_previous_location(thread_id)
        if prev_loc and prev_loc.lower() not in ql:
            user_query = f"{user_query} (referring to {prev_loc})"

    # 1. Classify intent
    intent = _classify_intent(user_query, context)

    # 1b. Check cache (keyed on query + intent)
    cache_key_extra = f"intent={intent.value}"
    cached_resp = _chat_cache.get(user_query, namespace=cache_key_extra)
    if cached_resp is not None:
        logger.info(f"[Cache] HIT for '{user_query[:50]}' intent={intent.value}")
        _store_conversation_turn(thread_id, request.messages[-1].content, cached_resp["message"], intent=intent.value)
        cached_resp["cached"] = True
        return cached_resp

    # 2. Gather grounded facts
    t0 = time.time()
    facts, intent, ui_actions, digital_twin_state, reasoning_trace = _gather_facts(user_query, context, intent)
    fact_time = time.time() - t0

    # 3. Build dashboard
    dashboard = _build_dashboard(facts, intent)

    # 4. Build LLM messages
    history = _get_conversation_history(thread_id)
    messages = _build_llm_messages(user_query, request, facts, intent, context, history)

    # 5. Call Ollama LLM via /api/chat (proper role separation)
    ai_message = ""
    chain_of_thought = None
    llm_cfg = context.get("llm_config", {})
    user_model = llm_cfg.get("local_model")
    try:
        if not _ollama_breaker.can_execute():
            raise CircuitBreakerOpen("Ollama circuit is OPEN — skipping LLM call")
        client = _get_ollama_client_for_model(user_model) if user_model else _get_ollama_client()
        raw = await client.chat(messages=messages, temperature=0.5, max_tokens=800)
        ai_message, chain_of_thought = _strip_thinking_tags(raw or "")
        _ollama_breaker.record_success()
    except CircuitBreakerOpen:
        logger.warning("Ollama circuit open — using fallback response")
        ai_message = _generate_fallback_response(intent, facts)
    except Exception as e:
        _ollama_breaker.record_failure()
        logger.error(f"LLM error: {e}")
        ai_message = _generate_fallback_response(intent, facts)

    if not ai_message.strip():
        ai_message = _generate_fallback_response(intent, facts)

    # 6. Post-LLM fact verification (Truth Firewall)
    verification = _verify_llm_output(ai_message, facts)

    # Store conversation turn
    _store_conversation_turn(thread_id, request.messages[-1].content, ai_message, intent=intent.value)

    # Deduct credits
    _deduct_credits(user_id, "local_query", intent.value)

    response = {
        "success": True,
        "message": ai_message,
        "intent": intent.value,
        "dashboard": dashboard if dashboard.get("title") or dashboard.get("cards") else None,
        "ui_actions": ui_actions,
        "simulation": facts.simulation_results,
        "digital_twin_state": digital_twin_state,
        "facts": _build_facts_data(facts),
        "facts_summary": {
            "location": facts.location_name,
            "poi_count": facts.poi_count,
            "accessibility": facts.accessibility_score,
            "walkability": facts.walkability_score,
            "avg_price_sqft": facts.avg_price_per_sqft,
            "active_listings": facts.active_listings,
        },
        "reasoning_trace": reasoning_trace,
        "chain_of_thought": chain_of_thought,
        "verification": verification,
        "cached": False,
    }

    # Store in cache (keyed on query + intent, 10-min TTL)
    try:
        cache_key_extra = f"intent={intent.value}"
        _chat_cache.set(user_query, response, namespace=cache_key_extra)
    except Exception:
        pass

    return response


# ---------------------------------------------------------------------------
# Endpoint 2: /api/chat/stream  (SSE streaming — primary for frontend)
# ---------------------------------------------------------------------------
@router.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint with Server-Sent Events.
    Emits: intent_classification_start, intent_detected, task_progress,
           thinking, thinking_end, content, metadata, done, error
    
    Pipeline: IntentRouter → GIS Orchestrator → Ollama streaming → SSE
    """
    user_query = request.messages[-1].content if request.messages else ""
    context = request.context or {}
    user_id = context.get("user_id", "anonymous")

    # Credits check (before starting stream)
    allowed, rate_result = _check_credits(user_id)
    if not allowed:
        async def rate_limited_stream():
            data = {
                "type": "error",
                "content": rate_result.reason or "Credit limit reached.",
                "credits": {
                    "remaining": rate_result.remaining_credits,
                    "total": rate_result.total_credits,
                    "tier": rate_result.tier,
                },
            }
            yield f"data: {json.dumps(data)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'thinking_time': 0})}\n\n"
        return StreamingResponse(
            rate_limited_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    async def generate():
        start_time = time.time()
        thread_id = context.get("thread_id")
        request_id = str(uuid.uuid4())[:12]
        metrics = {}  # pipeline stage timings

        def _sse(data: dict) -> str:
            data.setdefault("request_id", request_id)
            return f"data: {json.dumps(data)}\n\n"

        logger.info(f"[{request_id}] Stream start: '{user_query[:60]}' user={user_id}")

        # Connected signal
        yield _sse({"type": "status", "content": "Connected", "thinking_time": 0})

        # Greeting fast-path (no LLM needed)
        greeting_resp = _try_greeting_fast_path(user_query)
        if greeting_resp:
            _store_conversation_turn(thread_id, user_query, greeting_resp["message"], intent="greeting")
            yield _sse({"type": "content", "content": greeting_resp["message"], "thinking_time": time.time() - start_time})
            yield _sse({"type": "done", "thinking_time": time.time() - start_time})
            return

        # Zone fast-path
        zone_resp = _try_zone_fast_path(user_query, context)
        if zone_resp:
            yield _sse({"type": "content", "content": zone_resp["message"], "thinking_time": time.time() - start_time})
            yield _sse({"type": "done", "thinking_time": time.time() - start_time})
            return

        # Context carry
        effective_query = user_query
        ql = user_query.lower()
        if any(w in ql for w in ["there", "that area", "that place", "same area", "this area"]):
            prev_loc = _extract_previous_location(thread_id)
            if prev_loc and prev_loc.lower() not in ql:
                effective_query = f"{user_query} (referring to {prev_loc})"

        # --- Phase 1: Intent Classification ---
        yield _sse({"type": "intent_classification_start", "query": user_query, "stage": "intent"})

        t_intent = time.time()
        intent = _classify_intent(effective_query, context)
        metrics["intent_ms"] = int((time.time() - t_intent) * 1000)

        # Cache check (keyed on query + intent) — skip entire pipeline if cached
        cache_key_extra = f"intent={intent.value}"
        cached_resp = _chat_cache.get(effective_query, namespace=cache_key_extra)
        if cached_resp is not None:
            logger.info(f"[Cache] STREAM HIT for '{effective_query[:50]}' intent={intent.value}")
            _store_conversation_turn(thread_id, user_query, cached_resp["message"], intent=intent.value)
            yield _sse({"type": "intent_detected", "intent": intent.value, "confidence": 0.85, "task_graph": None})
            yield _sse({"type": "content", "content": cached_resp["message"], "thinking_time": time.time() - start_time})
            if cached_resp.get("dashboard"):
                yield _sse({"type": "metadata", "ui_actions": cached_resp.get("ui_actions", []), "intent": intent.value, "dashboard": cached_resp["dashboard"], "facts": cached_resp.get("facts")})
            yield _sse({"type": "done", "thinking_time": time.time() - start_time, "cached": True})
            return

        # Build task graph for frontend banner (model selection step added dynamically later)
        task_labels = _get_task_labels(intent)
        # Prepend "Selecting optimal model" as first task
        task_labels = ["Selecting optimal AI model"] + task_labels
        tasks = [
            {"id": f"t{i+1}", "label": lbl, "status": "pending", "type": "action", "dependencies": []}
            for i, lbl in enumerate(task_labels)
        ]
        task_graph = {
            "query": user_query,
            "intent": intent.value,
            "confidence": 0.85,
            "tasks": tasks,
            "progress_percent": 0,
            "completed_count": 0,
            "total_count": len(tasks),
        }

        yield _sse({
            "type": "intent_detected",
            "intent": intent.value,
            "confidence": 0.85,
            "task_graph": task_graph,
        })

        # --- Phase 1b: Model Selection task (t1) ---
        total_tasks = len(tasks)
        # Mark model selection task as running
        tasks[0]["status"] = "running"
        yield _sse({
            "type": "task_started",
            "task_id": tasks[0]["id"],
            "task_name": tasks[0]["label"],
            "task_type": "model_selection",
            "task_description": tasks[0]["label"],
            "progress": f"1/{total_tasks}",
        })

        # --- Phase 2: Gather Facts (with per-task progress events) ---
        # fact tasks are indices 1..(total-2), last task is LLM generation
        fact_start_idx = 1
        fact_end_idx = total_tasks - 1  # exclusive; last task is generation

        # Start first fact task
        if fact_start_idx < total_tasks:
            tasks[fact_start_idx]["status"] = "running"
            yield _sse({
                "type": "task_started",
                "task_id": tasks[fact_start_idx]["id"],
                "task_name": tasks[fact_start_idx]["label"],
                "task_type": "fact_gathering",
                "task_description": tasks[fact_start_idx]["label"],
                "progress": f"2/{total_tasks}",
            })

        t_facts = time.time()
        try:
            facts, intent, ui_actions, digital_twin_state, reasoning_trace = _gather_facts(
                effective_query, context, intent
            )
        except Exception as e:
            logger.error(f"[{request_id}] Facts gathering error: {e}")
            yield _sse({"type": "error", "content": f"Facts gathering failed: {e}"})
            yield _sse({"type": "done", "thinking_time": time.time() - start_time})
            return
        metrics["facts_ms"] = int((time.time() - t_facts) * 1000)

        # Progressively complete fact tasks (indices 1..fact_end_idx-1)
        for i in range(fact_start_idx, fact_end_idx):
            tasks[i]["status"] = "complete"
            yield _sse({
                "type": "task_completed",
                "task_id": tasks[i]["id"],
                "task_name": tasks[i]["label"],
                "summary": f"Completed: {tasks[i]['label']}",
                "duration_ms": int((time.time() - start_time) * 1000),
                "progress": f"{i + 1}/{total_tasks}",
            })
            # Start next task
            if i + 1 < total_tasks:
                tasks[i + 1]["status"] = "running"
                yield _sse({
                    "type": "task_started",
                    "task_id": tasks[i + 1]["id"],
                    "task_name": tasks[i + 1]["label"],
                    "task_type": "reasoning" if i + 1 < fact_end_idx else "generation",
                    "task_description": tasks[i + 1]["label"],
                    "progress": f"{i + 2}/{total_tasks}",
                })

        # Build dashboard and LLM messages
        dashboard = _build_dashboard(facts, intent)
        history = _get_conversation_history(thread_id)
        messages = _build_llm_messages(effective_query, request, facts, intent, context, history)

        # --- Phase 2b: Autonomous Agentic Loop for complex queries ---
        from ai.gis_agents import Intent as _Intent

        # User-controlled autonomy: check context for explicit toggle
        _user_agentic_pref = context.get("agentic_mode")  # True/False/None
        _agentic_intents = {_Intent.COMPARISON, _Intent.SIMULATE, _Intent.INVESTMENT}
        _is_multi_part = any(kw in effective_query.lower() for kw in [
            " and also ", " plus ", " additionally ", "compare", " vs ", " versus ",
            "what if", "simulate", "scenario", "as well as",
        ])
        _auto_agentic = (intent in _agentic_intents) or (_is_multi_part and len(effective_query.split()) > 12)

        # Self-learning: check if learned data suggests agentic is beneficial
        _learned_agentic = None
        try:
            from ai.self_learning import get_self_learning_engine
            _learner = get_self_learning_engine()
            _learned_agentic, _learn_reason = _learner.should_use_agentic(
                intent.value if intent else "general", len(effective_query.split())
            )
        except Exception:
            pass

        # Final decision: user toggle > learned > auto-detection
        if _user_agentic_pref is True:
            _use_agentic = True
        elif _user_agentic_pref is False:
            _use_agentic = False
        elif _learned_agentic is not None:
            _use_agentic = _learned_agentic
        else:
            _use_agentic = _auto_agentic

        agentic_answer = None
        agentic_plan = None
        if _use_agentic:
            try:
                from ai.agentic_loop import get_agentic_loop
                from ai.ollama_client import get_ollama_client as _get_agentic_llm
                agentic_loop = get_agentic_loop(max_steps=5)
                agentic_llm = _get_agentic_llm()

                yield _sse({
                    "type": "agentic_start",
                    "message": f"Deep analysis: {effective_query[:80]}",
                    "thinking_time": time.time() - start_time,
                })

                # Pass intent to agentic loop context for self-learning
                _agentic_ctx = {**context, "intent": intent.value if intent else None}
                async for event in agentic_loop.run(
                    query=effective_query,
                    llm_client=agentic_llm,
                    context=_agentic_ctx,
                ):
                    etype = event.get("type", "")
                    if etype == "agent_action":
                        yield _sse({
                            "type": "agentic_action",
                            "step": event.get("step_number"),
                            "tool": event.get("action"),
                            "params": event.get("action_params"),
                            "thought": event.get("thought", "")[:200],
                            "thinking_time": time.time() - start_time,
                        })
                    elif etype == "agent_observation":
                        yield _sse({
                            "type": "agentic_observation",
                            "step": event.get("step_number"),
                            "observation": (event.get("observation") or "")[:300],
                            "thinking_time": time.time() - start_time,
                        })
                    elif etype == "agent_final":
                        agentic_answer = event.get("final_answer")
                        agentic_plan = event.get("plan")
                        yield _sse({
                            "type": "agentic_complete",
                            "confidence": event.get("confidence", 0),
                            "steps_taken": event.get("step_number", 0),
                            "thinking_time": time.time() - start_time,
                        })
                    elif etype == "agent_max_steps":
                        agentic_plan = event.get("plan")

                metrics["agentic"] = True
                metrics["agentic_steps"] = len(agentic_plan.get("steps", [])) if agentic_plan else 0
            except Exception as e:
                logger.warning(f"[{request_id}] Agentic loop error (falling back): {e}")
                metrics["agentic_error"] = str(e)

        # --- Phase 3: Intelligent Model Selection + LLM Streaming ---
        from ai.model_router import route_model

        llm_cfg = context.get("llm_config", {})
        cloud_enabled = llm_cfg.get("cloud_enabled", False)
        user_selected_model = llm_cfg.get("local_model")  # User's dropdown choice

        # When cloud is OFF, only offer local models to the router
        all_models = await _fetch_available_models()
        if cloud_enabled:
            available_models = all_models
        else:
            available_models = [m for m in all_models if not _is_cloud_model(m)]
            if not available_models:
                available_models = ["qwen3:4b-instruct"]

        history = _get_conversation_history(thread_id)

        # Get user tier for cost-aware routing
        _user_tier = "pro"
        try:
            rl = _get_rate_limiter()
            _user_info = rl.get_or_create_user(user_id)
            _user_tier = _user_info.get("tier", "pro")
        except Exception:
            pass

        t_route = time.time()
        model_sel = route_model(
            user_query=effective_query,
            intent=intent,
            context=context,
            available_models=available_models,
            history_length=len(history) // 2,
            user_override=user_selected_model,  # Respect user's model dropdown choice
            user_tier=_user_tier,
        )
        metrics["route_ms"] = int((time.time() - t_route) * 1000)

        # Complete model selection task (t1) with router reasoning
        tasks[0]["status"] = "complete"
        model_summary = f"Selected {model_sel.model}"
        if model_sel.escalated:
            model_summary += f" (escalated, complexity={model_sel.complexity_score:.2f})"
        yield _sse({
            "type": "task_completed",
            "task_id": tasks[0]["id"],
            "task_name": tasks[0]["label"],
            "summary": model_summary,
            "duration_ms": int((time.time() - start_time) * 1000),
            "progress": f"1/{total_tasks}",
        })

        # Emit model selection event so frontend can show which model + why
        yield _sse({
            "type": "model_selection",
            "model": model_sel.model,
            "is_cloud": model_sel.is_cloud,
            "is_vision": model_sel.is_vision,
            "escalated": model_sel.escalated,
            "complexity_score": round(model_sel.complexity_score, 2),
            "reasoning": model_sel.reasoning,
            "thinking_time": time.time() - start_time,
        })

        # If agentic loop produced an answer, inject it as extra context for the LLM
        if agentic_answer:
            agentic_ctx = (
                "\n\n**AUTONOMOUS RESEARCH (grounded tool results):**\n"
                + agentic_answer[:2000]
            )
            # Augment the system message with agentic findings
            if messages and messages[0]["role"] == "system":
                messages[0]["content"] += agentic_ctx

        content_buffer = ""
        thinking_buffer = ""
        in_thinking = False

        # Build prompt
        llm_start = time.time()
        llm_success = True
        token_count = 0

        # Circuit breaker check before LLM call
        provider_breaker = _openrouter_breaker if model_sel.provider == "openrouter" else _ollama_breaker
        if not provider_breaker.can_execute():
            logger.warning(f"Circuit breaker OPEN for {model_sel.provider} — using fallback")
            yield _sse({"type": "status", "content": f"{model_sel.provider} temporarily unavailable, using cached facts...", "thinking_time": time.time() - start_time})
            fallback = _generate_fallback_response(intent, facts)
            content_buffer = fallback
            llm_success = False
            yield _sse({"type": "content", "content": fallback, "thinking_time": time.time() - start_time})

        try:
            if content_buffer:  # Already handled by circuit breaker fallback
                pass
            elif model_sel.provider == "openrouter":
                # OpenRouter cloud — use chat completions API with proper messages
                logger.info(f"[OpenRouter] Using {model_sel.model} (score={model_sel.complexity_score:.2f})")
                yield _sse({"type": "status", "content": f"Reasoning with {model_sel.model} (OpenRouter)...", "thinking_time": time.time() - start_time})
                stream = _stream_openrouter(messages, model_sel.model, model_sel.temperature, model_sel.max_tokens)
            elif model_sel.is_cloud or model_sel.escalated:
                # Ollama cloud — use /api/chat with proper message roles
                logger.info(f"[OllamaCloud] Escalated to {model_sel.model} (score={model_sel.complexity_score:.2f})")
                yield _sse({"type": "status", "content": f"Reasoning with {model_sel.model}...", "thinking_time": time.time() - start_time})
                client = _get_ollama_client_for_model(model_sel.model)
                stream = client.chat_stream(messages=messages, temperature=model_sel.temperature, max_tokens=model_sel.max_tokens)
            else:
                # Local Ollama — use /api/chat with proper message roles
                client = _get_ollama_client()
                stream = client.chat_stream(messages=messages, temperature=model_sel.temperature, max_tokens=model_sel.max_tokens)

            async for chunk in stream:
                current_time = time.time() - start_time

                # Handle <think> tags in streaming
                if "<think>" in chunk.lower() and not in_thinking:
                    # Split at <think>
                    parts = re.split(r"<think>", chunk, maxsplit=1, flags=re.IGNORECASE)
                    if parts[0]:
                        content_buffer += parts[0]
                        yield _sse({"type": "content", "content": parts[0], "thinking_time": current_time})
                    in_thinking = True
                    yield _sse({"type": "thinking_start", "thinking_time": current_time})
                    if len(parts) > 1 and parts[1]:
                        thinking_buffer += parts[1]
                        yield _sse({"type": "thinking", "content": parts[1], "thinking_time": current_time})
                elif "</think>" in chunk.lower() and in_thinking:
                    parts = re.split(r"</think>", chunk, maxsplit=1, flags=re.IGNORECASE)
                    if parts[0]:
                        thinking_buffer += parts[0]
                        yield _sse({"type": "thinking", "content": parts[0], "thinking_time": current_time})
                    in_thinking = False
                    yield _sse({"type": "thinking_end", "thinking_time": current_time})
                    if len(parts) > 1 and parts[1]:
                        content_buffer += parts[1]
                        yield _sse({"type": "content", "content": parts[1], "thinking_time": current_time})
                elif in_thinking:
                    thinking_buffer += chunk
                    yield _sse({"type": "thinking", "content": chunk, "thinking_time": current_time})
                else:
                    content_buffer += chunk
                    yield _sse({"type": "content", "content": chunk, "thinking_time": current_time})

            if in_thinking:
                yield _sse({"type": "thinking_end", "thinking_time": time.time() - start_time})

            # Record success on circuit breaker
            if content_buffer.strip():
                provider_breaker.record_success()

        except Exception as e:
            llm_success = False
            provider_breaker.record_failure()
            logger.error(f"LLM streaming error ({model_sel.provider}/{model_sel.model}): {e}")

            # Fallback: if OpenRouter failed, try Ollama cloud; if that fails, use local
            if model_sel.provider == "openrouter" and model_sel.is_cloud:
                try:
                    # Find an Ollama cloud model as fallback
                    ollama_cloud = [m for m in all_models if _is_cloud_model(m)]
                    if ollama_cloud:
                        fb_model = ollama_cloud[0]
                        logger.info(f"[Fallback] OpenRouter failed → trying Ollama cloud {fb_model}")
                        yield _sse({"type": "status", "content": f"Falling back to {fb_model}...", "thinking_time": time.time() - start_time})
                        fb_client = _get_ollama_client_for_model(fb_model)
                        async for chunk in fb_client.chat_stream(messages=messages, temperature=model_sel.temperature, max_tokens=model_sel.max_tokens):
                            content_buffer += chunk
                            yield _sse({"type": "content", "content": chunk, "thinking_time": time.time() - start_time})
                        llm_success = True
                except Exception as fb_err:
                    logger.error(f"Ollama cloud fallback also failed: {fb_err}")

            if not content_buffer.strip():
                fallback = _generate_fallback_response(intent, facts)
                content_buffer = fallback
                yield _sse({"type": "content", "content": fallback, "thinking_time": time.time() - start_time})

        # If no content was generated, use fallback
        if not content_buffer.strip():
            fallback = _generate_fallback_response(intent, facts)
            content_buffer = fallback
            yield _sse({"type": "content", "content": fallback, "thinking_time": time.time() - start_time})

        # Record performance for learning-aware routing
        llm_latency_ms = int((time.time() - llm_start) * 1000)
        metrics["llm_ms"] = llm_latency_ms
        try:
            from ai.model_router import record_model_performance
            record_model_performance(
                model=model_sel.model, intent=intent.value,
                complexity_score=model_sel.complexity_score,
                latency_ms=llm_latency_ms, success=llm_success,
                tokens=len(content_buffer.split()),
            )
        except Exception:
            pass

        # Mark final generation task as complete
        if tasks and tasks[-1]["status"] != "complete":
            tasks[-1]["status"] = "complete"
            yield _sse({
                "type": "task_completed",
                "task_id": tasks[-1]["id"],
                "task_name": tasks[-1]["label"],
                "summary": f"Completed: {tasks[-1]['label']}",
                "duration_ms": int((time.time() - start_time) * 1000),
                "progress": f"{len(tasks)}/{len(tasks)}",
            })

        # Store conversation turn
        _store_conversation_turn(thread_id, request.messages[-1].content if request.messages else "", content_buffer, intent=intent.value)

        # Deduct credits (cloud queries cost more)
        credit_action = "cloud_query" if model_sel.escalated else "local_query"
        _deduct_credits(user_id, credit_action, intent.value)

        # Post-LLM fact verification (Truth Firewall)
        verification = _verify_llm_output(content_buffer, facts) if content_buffer.strip() else None
        if verification:
            yield _sse({"type": "verification", "verification": verification, "thinking_time": time.time() - start_time})

        # Emit metadata (dashboard, ui_actions, facts)
        facts_data = _build_facts_data(facts)
        resp_dashboard = dashboard if dashboard.get("title") or dashboard.get("cards") else None
        yield _sse({
            "type": "metadata",
            "ui_actions": ui_actions or [],
            "intent": intent.value,
            "dashboard": resp_dashboard,
            "facts": facts_data,
            "verification": verification,
        })

        # Store assembled response in cache for future identical queries
        if llm_success and content_buffer.strip():
            try:
                cache_response = {
                    "success": True,
                    "message": content_buffer,
                    "intent": intent.value,
                    "dashboard": resp_dashboard,
                    "ui_actions": ui_actions or [],
                    "facts": facts_data,
                    "verification": verification,
                }
                _chat_cache.set(effective_query, cache_response, namespace=f"intent={intent.value}")
            except Exception:
                pass

        # --- Phase 5: Proactive Suggestions ---
        try:
            from ai.tools_registry import _tool_proactive_suggestions
            location_name = facts.location_name if facts else None
            suggestions_result = _tool_proactive_suggestions(
                location=location_name,
                intent=intent.value if intent else None,
            )
            if suggestions_result and suggestions_result.get("suggestions"):
                yield _sse({
                    "type": "suggestions",
                    "suggestions": suggestions_result["suggestions"],
                    "thinking_time": time.time() - start_time,
                })
        except Exception as e:
            logger.debug(f"Proactive suggestions skipped: {e}")

        # Pipeline metrics
        total_time = time.time() - start_time
        metrics["total_ms"] = int(total_time * 1000)
        metrics["model"] = model_sel.model
        metrics["provider"] = model_sel.provider
        metrics["escalated"] = model_sel.escalated
        logger.info(f"[{request_id}] Pipeline done: {metrics}")
        yield _sse({"type": "pipeline_metrics", "metrics": metrics})

        # Done
        yield _sse({"type": "done", "thinking_time": total_time, "full_response": content_buffer})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Task labels per intent (for the frontend task banner)
# ---------------------------------------------------------------------------
def _get_task_labels(intent) -> List[str]:
    from ai.gis_agents import Intent
    mapping = {
        Intent.NAVIGATE: [
            "Resolving coordinates & geocoding",
            "Computing optimal camera trajectory",
            "Rendering 3D neighbourhood view",
        ],
        Intent.ANALYZE_AREA: [
            "Identifying micro-market boundaries",
            "Scanning POI density & walkability index",
            "Aggregating price per sqft from comparables",
            "Cross-referencing infrastructure pipeline",
            "Predicting neighbourhood growth trajectory",
            "Synthesizing investment narrative",
        ],
        Intent.ANALYZE_BUILDING: [
            "Extracting building footprint & 3D geometry",
            "Estimating replacement cost & depreciation",
            "Scoring amenity proximity & connectivity",
            "Forecasting rental yield & capital appreciation",
            "Composing valuation narrative",
        ],
        Intent.PROPERTY_SEARCH: [
            "Parsing search filters & constraints",
            "Querying spatial property index",
            "Ranking results by value-to-price ratio",
            "Computing neighbourhood quality scores",
            "Generating shortlist with reasoning",
        ],
        Intent.VALUATION: [
            "Loading comparable transactions (6-month window)",
            "Adjusting for location, age & amenities",
            "Running hedonic pricing regression",
            "Estimating confidence interval",
            "Generating valuation certificate",
        ],
        Intent.TERRAIN: [
            "Sampling elevation grid at 30m resolution",
            "Computing slope, aspect & flood risk zones",
            "Overlaying land-use classification",
            "Generating terrain intelligence report",
        ],
        Intent.COMPARISON: [
            "Profiling Area A — demographics & infra",
            "Profiling Area B — demographics & infra",
            "Normalizing metrics for fair comparison",
            "Identifying decisive differentiators",
            "Generating comparative verdict",
        ],
        Intent.SIMULATE: [
            "Defining scenario parameters & assumptions",
            "Running Monte Carlo price simulation",
            "Modelling infrastructure impact radius",
            "Computing ROI probability distribution",
            "Narrating scenario outcomes",
        ],
        Intent.INVESTMENT: [
            "Scanning macro & micro market signals",
            "Computing 5-year CAGR projection",
            "Assessing risk factors & liquidity",
            "Benchmarking against alternative assets",
            "Generating investment thesis",
        ],
        Intent.MARKET_TREND: [
            "Loading historical price time-series",
            "Detecting trend inflection points",
            "Forecasting 12-month price trajectory",
            "Generating market intelligence brief",
        ],
        Intent.GREETING: ["Preparing response"],
        Intent.GENERAL: [
            "Understanding query context",
            "Retrieving relevant spatial data",
            "Reasoning over real estate knowledge base",
            "Generating informed response",
        ],
    }
    return mapping.get(intent, ["Understanding query", "Gathering spatial context", "Generating response"])
