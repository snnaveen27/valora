"""
Valora AI - Intelligent Model Router (Learning-Aware)

Auto-selects the optimal model (local Ollama, Ollama Cloud, or OpenRouter) based on:
  1. Query complexity (word count, multi-intent signals, technical depth)
  2. Intent type (simulation/comparison need heavy reasoning)
  3. Image presence (routes to vision models)
  4. Conversation context (long threads benefit from larger context)
  5. Available models (dynamically discovered from Ollama + OpenRouter)
  6. Historical performance (SQLite-tracked latency, success rate, quality)

IMPORTANT: When user provides explicit model selection via dropdown, 
that selection is ALWAYS respected and complexity-based routing is BYPASSED.

Cloud provider priority: OpenRouter -> Ollama Cloud (fallback)
Default local: qwen3:4b-instruct
"""

import logging
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("valora.model_router")

# OpenRouter model mapping — canonical IDs
OPENROUTER_MODELS = {
    "reasoning": "deepseek/deepseek-chat",
    "reasoning_heavy": "deepseek/deepseek-reasoner",
    "vision": "qwen/qwen2.5-vl-72b-instruct",
    "code": "anthropic/claude-sonnet-4",
}


# ---------------------------------------------------------------------------
# Model capability descriptors
# ---------------------------------------------------------------------------
@dataclass
class ModelCapability:
    """Describes what a model is good at."""
    id: str
    provider: str = "ollama"         # "ollama" | "openrouter"
    is_cloud: bool = False
    is_vision: bool = False
    reasoning_tier: int = 1          # 1=basic, 2=good, 3=excellent
    context_window: int = 4096
    speed_tier: int = 3              # 1=slow, 2=medium, 3=fast
    cost_tier: int = 1               # 1=free/local, 2=cheap, 3=expensive
    param_billions: float = 0.0


_MODEL_CAPABILITIES: Dict[str, ModelCapability] = {}


def _infer_capability(model_name: str) -> ModelCapability:
    """Infer model capability from its name."""
    nl = model_name.lower()

    # OpenRouter models (contain "/" in name)
    if "/" in model_name:
        is_vision = any(v in nl for v in ["vl", "vision", "llava"])
        reasoning = 3 if any(r in nl for r in ["deepseek", "claude", "gpt-4", "reasoner"]) else 2
        return ModelCapability(
            id=model_name, provider="openrouter", is_cloud=True,
            is_vision=is_vision, reasoning_tier=reasoning,
            context_window=128000, speed_tier=2,
            cost_tier=2, param_billions=0.0,
        )

    # Ollama models
    is_cloud = ":cloud" in nl or nl.endswith("-cloud")
    is_vision = any(v in nl for v in ["-vl", "vl:", "vision", "llava", "llama4"])

    reasoning = 1
    if any(r in nl for r in ["235b", "128x", "72b"]):
        reasoning = 3
    elif any(r in nl for r in ["32b", "30b", "34b", "next"]):
        reasoning = 2
    elif any(r in nl for r in ["deepseek", "kimi", "r1"]):
        reasoning = 3

    params = 0.0
    pm = re.search(r"(\d+\.?\d*)b", nl)
    if pm:
        params = float(pm.group(1))

    speed = 3
    if is_cloud:
        speed = 2 if params < 50 else 1
    elif params > 30:
        speed = 1

    ctx = 4096
    if "235b" in nl or "128x" in nl:
        ctx = 131072
    elif is_cloud:
        ctx = 32768
    elif params >= 30:
        ctx = 16384

    return ModelCapability(
        id=model_name, provider="ollama", is_cloud=is_cloud,
        is_vision=is_vision, reasoning_tier=reasoning,
        context_window=ctx, speed_tier=speed,
        cost_tier=1 if not is_cloud else (2 if params < 100 else 3),
        param_billions=params,
    )


def get_model_capability(model_name: str) -> ModelCapability:
    if model_name not in _MODEL_CAPABILITIES:
        _MODEL_CAPABILITIES[model_name] = _infer_capability(model_name)
    return _MODEL_CAPABILITIES[model_name]


# ---------------------------------------------------------------------------
# Learning-Aware Performance Tracker (SQLite — thread-local pool)
# ---------------------------------------------------------------------------
from config import config
_PERF_DB = config.DB_PATH.parent / "model_performance.db"

_PERF_INIT_SQL = """
CREATE TABLE IF NOT EXISTS model_perf (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,
    intent TEXT,
    complexity_score REAL,
    latency_ms INTEGER,
    success INTEGER DEFAULT 1,
    tokens_generated INTEGER DEFAULT 0,
    timestamp REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_model ON model_perf(model);
CREATE INDEX IF NOT EXISTS idx_intent ON model_perf(intent);
"""

def _get_perf_conn():
    """Get thread-local connection to model_performance.db."""
    try:
        from core.sqlite_pool import get_pool
        pool = get_pool("model_perf", str(_PERF_DB), _PERF_INIT_SQL)
        return pool.get()
    except Exception:
        # Fallback: direct connection if pool not available
        conn = sqlite3.connect(str(_PERF_DB))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn


def record_model_performance(
    model: str, intent: str, complexity_score: float,
    latency_ms: int, success: bool = True, tokens: int = 0,
):
    """Record a model's performance for learning-aware routing."""
    try:
        conn = _get_perf_conn()
        conn.execute(
            "INSERT INTO model_perf (model, intent, complexity_score, latency_ms, success, tokens_generated, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (model, intent, complexity_score, latency_ms, int(success), tokens, time.time()),
        )
        conn.commit()
        # Prune old records (keep last 500)
        conn.execute("""
            DELETE FROM model_perf WHERE id NOT IN (
                SELECT id FROM model_perf ORDER BY id DESC LIMIT 500
            )
        """)
        conn.commit()
    except Exception as e:
        logger.debug(f"[ModelRouter] Failed to record perf: {e}")


def _get_model_score_bonus(model: str, intent: str) -> float:
    """Get a learned bonus/penalty for a model based on historical performance.
    Returns a value from -0.3 to +0.3 that adjusts the model's selection priority."""
    try:
        conn = _get_perf_conn()
        rows = conn.execute(
            "SELECT latency_ms, success FROM model_perf "
            "WHERE model = ? AND intent = ? ORDER BY id DESC LIMIT 20",
            (model, intent),
        ).fetchall()
        if len(rows) < 3:
            return 0.0  # Not enough data
        successes = sum(1 for _, s in rows if s)
        success_rate = successes / len(rows)
        avg_latency = sum(lat for lat, _ in rows) / len(rows)
        # Good model: high success, low latency -> positive bonus
        bonus = (success_rate - 0.7) * 0.5  # +0.15 for 100%, -0.1 for 50%
        if avg_latency > 30000:  # > 30s avg -> penalty
            bonus -= 0.1
        elif avg_latency < 5000:  # < 5s avg -> bonus
            bonus += 0.05
        return max(-0.3, min(0.3, bonus))
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# OpenRouter availability check
# ---------------------------------------------------------------------------
def _openrouter_available() -> bool:
    """Check if OpenRouter API key is configured."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    return bool(key) and key != "sk-or-v1-your-api-key-here"


# ---------------------------------------------------------------------------
# Query complexity scoring
# ---------------------------------------------------------------------------
@dataclass
class QueryAnalysis:
    word_count: int = 0
    has_images: bool = False
    multi_intent: bool = False
    needs_deep_reasoning: bool = False
    needs_vision: bool = False
    needs_large_context: bool = False
    complexity_score: float = 0.0
    reasoning: str = ""


_DEEP_REASONING_SIGNALS = [
    r"\bwhat if\b", r"\bsimulat", r"\bscenario\b", r"\bforecast\b",
    r"\bpredict\b", r"\bproject\b", r"\bmodel\b.*\bimpact\b",
    r"\bvs\.?\b", r"\bversus\b", r"\bcompare\b", r"\bbetter\b.*\bor\b",
    r"\bwhich\b.*\bbetter\b", r"\bpros\b.*\bcons\b",
    r"\broi\b", r"\bcagr\b", r"\birr\b", r"\byield\b",
    r"\bappreciat", r"\bdepreciat", r"\binvestment\b.*\bthesis\b",
    r"\balso\b.*\b(tell|show|find|analyze)\b",
    r"\band\b.*\b(also|additionally|plus)\b",
    r"\bdetailed\b", r"\bin-depth\b", r"\bcomprehensive\b",
    r"\bthorough\b", r"\bexhaustive\b",
    r"\bbut\b.*\balso\b", r"\bhowever\b", r"\bon\s+the\s+other\s+hand\b",
    r"\btrade-?off\b", r"\bbalance\b.*\bbetween\b",
]

_VISION_SIGNALS = [
    r"\bphoto\b", r"\bimage\b", r"\bpicture\b", r"\bfloor\s*plan\b",
    r"\bscreenshot\b", r"\blook\s+at\b.*\bthis\b", r"\banalyze\b.*\bthis\b",
    r"\bwhat\b.*\bsee\b", r"\bidentify\b", r"\bocr\b", r"\bread\b.*\btext\b",
]

_LARGE_CONTEXT_SIGNALS = [
    r"\ball\b.*\bproperties\b", r"\bentire\b", r"\bfull\b.*\breport\b",
    r"\bhistory\b", r"\btime\s*series\b", r"\btrend\b.*\b(year|month)\b",
    r"\blong\s*term\b", r"\b\d+\s*year\b",
]


def analyze_query(
    user_query: str, intent, context: Dict[str, Any], history_length: int = 0,
) -> QueryAnalysis:
    from ai.gis_agents import Intent

    ql = user_query.lower()
    words = user_query.split()
    analysis = QueryAnalysis(word_count=len(words))
    score = 0.0
    reasons = []

    # 1. Images
    images = context.get("images") or context.get("image") or context.get("attachedImages") or []
    if images:
        analysis.has_images = True
        analysis.needs_vision = True
        score += 0.4
        reasons.append("images attached")

    # 2. Intent complexity
    heavy = {Intent.SIMULATE, Intent.COMPARISON, Intent.INVESTMENT}
    medium = {Intent.ANALYZE_AREA, Intent.ANALYZE_BUILDING, Intent.PROPERTY_SEARCH, Intent.VALUATION, Intent.MARKET_TREND}
    if intent in heavy:
        score += 0.35
        analysis.needs_deep_reasoning = True
        reasons.append(f"{intent.value} -> heavy")
    elif intent in medium:
        score += 0.15
        reasons.append(f"{intent.value} -> moderate")

    # 3. Deep reasoning signals
    deep_hits = sum(1 for p in _DEEP_REASONING_SIGNALS if re.search(p, ql))
    if deep_hits >= 3:
        score += 0.3
        analysis.needs_deep_reasoning = True
        analysis.multi_intent = True
        reasons.append(f"{deep_hits} reasoning signals")
    elif deep_hits >= 1:
        score += 0.1 * deep_hits
        if deep_hits >= 2:
            analysis.multi_intent = True
        reasons.append(f"{deep_hits} signal(s)")

    # 4. Vision signals + images
    if sum(1 for p in _VISION_SIGNALS if re.search(p, ql)) >= 1 and analysis.has_images:
        score += 0.1
        reasons.append("vision keywords + images")

    # 5. Query length
    if len(words) > 40:
        score += 0.15
        reasons.append(f"{len(words)} words")
    elif len(words) > 20:
        score += 0.05

    # 6. Conversation depth
    if history_length > 8:
        score += 0.1
        analysis.needs_large_context = True
        reasons.append(f"{history_length} turns")
    elif history_length > 4:
        score += 0.05

    # 7. Large context signals
    if sum(1 for p in _LARGE_CONTEXT_SIGNALS if re.search(p, ql)) >= 1:
        score += 0.1
        analysis.needs_large_context = True
        reasons.append("large-context")

    analysis.complexity_score = min(1.0, score)
    analysis.reasoning = "; ".join(reasons) if reasons else "simple query"
    return analysis


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------
@dataclass
class ModelSelection:
    model: str
    provider: str = "ollama"         # "ollama" | "openrouter"
    is_cloud: bool = False
    is_vision: bool = False
    reasoning: str = ""
    complexity_score: float = 0.0
    max_tokens: int = 2000
    temperature: float = 0.5
    escalated: bool = False


# Default thresholds (pro/team/enterprise users)
CLOUD_ESCALATION_THRESHOLD = 0.35
HEAVY_CLOUD_THRESHOLD = 0.6

# Higher thresholds for free-tier users — only escalate for truly complex queries
_FREE_TIER_ESCALATION_BOOST = 0.20  # +0.20 → effectively 0.55 / 0.80


def select_model(
    query_analysis: QueryAnalysis,
    available_models: List[str],
    intent=None,
    user_tier: str = "pro",
) -> ModelSelection:
    """Select optimal model. Uses learned performance data to adjust ranking."""
    from ai.gis_agents import Intent

    caps = {m: get_model_capability(m) for m in available_models}
    intent_str = intent.value if intent else "general"

    # Apply learned bonuses to reasoning tiers
    def adjusted_tier(cap):
        bonus = _get_model_score_bonus(cap.id, intent_str)
        return cap.reasoning_tier + bonus

    vision_models = sorted(
        [c for c in caps.values() if c.is_vision],
        key=lambda c: adjusted_tier(c), reverse=True,
    )
    reasoning_models = sorted(
        [c for c in caps.values() if c.is_cloud and not c.is_vision],
        key=lambda c: adjusted_tier(c), reverse=True,
    )
    local_models = sorted(
        [c for c in caps.values() if not c.is_cloud],
        key=lambda c: adjusted_tier(c), reverse=True,
    )

    score = query_analysis.complexity_score
    reasons = []

    # Cost-aware: raise thresholds for free-tier users
    tier_boost = _FREE_TIER_ESCALATION_BOOST if user_tier == "free" else 0.0
    esc_threshold = CLOUD_ESCALATION_THRESHOLD + tier_boost
    heavy_threshold = HEAVY_CLOUD_THRESHOLD + tier_boost
    if tier_boost > 0:
        reasons.append(f"free-tier boost +{tier_boost:.2f}")

    # 1. Vision
    if query_analysis.needs_vision and vision_models:
        best = vision_models[0]
        reasons.append(f"vision -> {best.id}")
        return ModelSelection(
            model=best.id, provider=best.provider, is_cloud=best.is_cloud,
            is_vision=True, reasoning=" | ".join([query_analysis.reasoning] + reasons),
            complexity_score=score, max_tokens=8192, temperature=0.6,
            escalated=best.is_cloud,
        )

    # 2. High complexity
    if score >= heavy_threshold and reasoning_models:
        best = reasoning_models[0]
        reasons.append(f"high ({score:.2f}) -> {best.id}")
        return ModelSelection(
            model=best.id, provider=best.provider, is_cloud=True,
            reasoning=" | ".join([query_analysis.reasoning] + reasons),
            complexity_score=score, max_tokens=8192, temperature=0.6,
            escalated=True,
        )

    # 3. Medium complexity
    if score >= esc_threshold and reasoning_models:
        lighter = sorted(reasoning_models, key=lambda c: c.speed_tier, reverse=True)
        best = lighter[0]
        reasons.append(f"medium ({score:.2f}) -> {best.id}")
        return ModelSelection(
            model=best.id, provider=best.provider, is_cloud=True,
            reasoning=" | ".join([query_analysis.reasoning] + reasons),
            complexity_score=score, max_tokens=4096, temperature=0.5,
            escalated=True,
        )

    # 4. Local
    default_local = "qwen3:4b-instruct"
    if local_models:
        default_local = local_models[0].id

    max_tokens = 4096
    if intent in {Intent.SIMULATE, Intent.COMPARISON, Intent.INVESTMENT,
                  Intent.ANALYZE_AREA, Intent.PROPERTY_SEARCH}:
        max_tokens = 8192
    elif intent in {Intent.ANALYZE_BUILDING, Intent.VALUATION, Intent.MARKET_TREND}:
        max_tokens = 4096

    reasons.append(f"local ({score:.2f}) -> {default_local}")
    return ModelSelection(
        model=default_local, provider="ollama",
        reasoning=" | ".join([query_analysis.reasoning] + reasons),
        complexity_score=score, max_tokens=max_tokens, temperature=0.5,
    )


# ---------------------------------------------------------------------------
# Convenience: one-call route function
# ---------------------------------------------------------------------------
def route_model(
    user_query: str,
    intent,
    context: Dict[str, Any],
    available_models: List[str],
    history_length: int = 0,
    user_override: Optional[str] = None,
    user_tier: str = "pro",
) -> ModelSelection:
    """Analyze query + select model. Adds OpenRouter models when available.

    user_override = user's preferred model (from frontend dropdown).
    When provided, this model is ALWAYS used regardless of query complexity.
    The automated complexity-based escalation is BYPASSED when user has made a selection.
    user_tier = user's subscription tier (free/pro/team/enterprise).
    Free-tier users have higher escalation thresholds to conserve cloud credits.
    """
    # If OpenRouter is configured, add its models to the pool
    enriched = list(available_models)
    if _openrouter_available():
        for role, model_id in OPENROUTER_MODELS.items():
            if model_id not in enriched:
                enriched.append(model_id)

    analysis = analyze_query(user_query, intent, context, history_length)
    selection = select_model(analysis, enriched, intent, user_tier=user_tier)

    # If user has explicitly selected a model, ALWAYS respect that choice
    # Skip complexity-based escalation entirely when user has made a selection
    logger.info(f"[ModelRouter] user_override received: {user_override}, enriched models: {enriched[:5]}...")
    if user_override:
        # Check if user's selection is available (handle suffixes like :latest)
        user_model_base = user_override.split(':')[0] if ':' in user_override else user_override
        matched_model = None
        for m in enriched:
            m_base = m.split(':')[0] if ':' in m else m
            if m == user_override or m_base == user_model_base:
                matched_model = m
                break
        
        if matched_model:
            cap = get_model_capability(matched_model)
            logger.info(f"[ModelRouter] Using user's selected model: {matched_model} (bypassing complexity routing)")
            return ModelSelection(
                model=matched_model,
                provider=cap.provider,
                is_cloud=cap.is_cloud,
                is_vision=cap.is_vision,
                reasoning=f"user selected {matched_model} | bypassing auto-routing",
                complexity_score=analysis.complexity_score,
                max_tokens=8192 if cap.is_cloud else 4096,
                temperature=0.6 if cap.is_cloud else 0.5,
                escalated=False,  # Not escalated - user chose this
            )
        else:
            logger.warning(f"[ModelRouter] User selected model {user_override} not in available models, falling back to routing")

    logger.info(
        f"[ModelRouter] score={analysis.complexity_score:.2f} "
        f"model={selection.model} provider={selection.provider} "
        f"escalated={selection.escalated} reason='{selection.reasoning}'"
    )
    return selection
