"""
Agent and market coverage routes.

These endpoints provide production implementations for:
- /api/agent/preferences/upsert
- /api/agent/recommendations
- /api/agent/feedback
- /api/market/coverage
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth.user_auth import User
from config import config
from core.sqlite_pool import get_pool
from database.query_service import get_query_service
from routes.auth_routes import require_auth


router = APIRouter(tags=["agent"])


_AGENT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agent_preferences (
    user_id TEXT PRIMARY KEY,
    budget_min REAL,
    budget_max REAL,
    typology TEXT,
    commute TEXT,
    risk_tolerance TEXT,
    intent_horizon TEXT,
    must_have_filters TEXT DEFAULT '[]',
    preferred_localities TEXT DEFAULT '[]',
    updated_at REAL NOT NULL,
    profile_version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS agent_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    recommendation_id TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT,
    confidence_delta REAL DEFAULT 0,
    metadata_json TEXT DEFAULT '{}',
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_feedback_user ON agent_feedback(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_feedback_reco ON agent_feedback(recommendation_id);
"""


def _get_conn():
    db_path = config.DB_PATH.parent / "agent_state.db"
    pool = get_pool("agent_state", str(db_path), _AGENT_SCHEMA_SQL)
    return pool.get()


def _json_or_default(value: Optional[str], default: Any):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _parse_timestamp_to_epoch(value: Any) -> Optional[float]:
    """Parse common SQLite/ISO timestamp forms into epoch seconds."""
    if not value:
        return None
    raw = str(value).strip()
    try:
        # Handles "2026-03-05 10:11:12" and similar formats.
        return datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S").timestamp()
    except Exception:
        pass
    try:
        # Handles ISO strings, including trailing Z.
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


class PreferenceProfile(BaseModel):
    budget_min: Optional[float] = Field(default=None, ge=0)
    budget_max: Optional[float] = Field(default=None, ge=0)
    typology: Optional[str] = None
    commute: Optional[str] = None
    risk_tolerance: Optional[str] = None
    intent_horizon: Optional[str] = None
    must_have_filters: List[str] = Field(default_factory=list)
    preferred_localities: List[str] = Field(default_factory=list)


class PreferencesUpsertRequest(BaseModel):
    profile: PreferenceProfile


class FeedbackRequest(BaseModel):
    recommendation_id: str = Field(min_length=1, max_length=120)
    action: str = Field(min_length=1, max_length=40)
    reason: Optional[str] = Field(default=None, max_length=500)
    metadata: Dict[str, Any] = Field(default_factory=dict)


@dataclass
class _RecommendationScore:
    score: float
    confidence_score: float
    rationale: List[str]
    risk_flags: List[str]


def _load_preference_row(user_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    row = conn.execute(
        """
        SELECT user_id, budget_min, budget_max, typology, commute, risk_tolerance,
               intent_horizon, must_have_filters, preferred_localities, updated_at, profile_version
        FROM agent_preferences
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    if not row:
        return None
    return dict(row)


def _normalize_profile(profile: PreferenceProfile) -> Dict[str, Any]:
    budget_min = profile.budget_min
    budget_max = profile.budget_max
    if budget_min is not None and budget_max is not None and budget_min > budget_max:
        budget_min, budget_max = budget_max, budget_min

    return {
        "budget_min": budget_min,
        "budget_max": budget_max,
        "typology": (profile.typology or "").strip() or None,
        "commute": (profile.commute or "").strip() or None,
        "risk_tolerance": (profile.risk_tolerance or "").strip() or None,
        "intent_horizon": (profile.intent_horizon or "").strip() or None,
        "must_have_filters": profile.must_have_filters or [],
        "preferred_localities": profile.preferred_localities or [],
    }


@router.post("/api/agent/preferences/upsert")
async def upsert_preferences(
    request: PreferencesUpsertRequest,
    user: User = Depends(require_auth),
):
    profile = _normalize_profile(request.profile)
    now_ts = time.time()
    conn = _get_conn()

    existing = _load_preference_row(user.email)
    next_version = 1 if not existing else int(existing.get("profile_version", 0)) + 1

    conn.execute(
        """
        INSERT INTO agent_preferences (
            user_id, budget_min, budget_max, typology, commute, risk_tolerance,
            intent_horizon, must_have_filters, preferred_localities, updated_at, profile_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            budget_min = excluded.budget_min,
            budget_max = excluded.budget_max,
            typology = excluded.typology,
            commute = excluded.commute,
            risk_tolerance = excluded.risk_tolerance,
            intent_horizon = excluded.intent_horizon,
            must_have_filters = excluded.must_have_filters,
            preferred_localities = excluded.preferred_localities,
            updated_at = excluded.updated_at,
            profile_version = excluded.profile_version
        """,
        (
            user.email,
            profile["budget_min"],
            profile["budget_max"],
            profile["typology"],
            profile["commute"],
            profile["risk_tolerance"],
            profile["intent_horizon"],
            json.dumps(profile["must_have_filters"]),
            json.dumps(profile["preferred_localities"]),
            now_ts,
            next_version,
        ),
    )
    conn.commit()

    return {
        "success": True,
        "user_id": user.email,
        "profile_version": next_version,
        "normalized_profile": profile,
        "updated_at": now_ts,
    }


def _score_recommendation(
    prop: Dict[str, Any],
    prefs: Dict[str, Any],
) -> _RecommendationScore:
    score = 50.0
    rationale: List[str] = []
    risk_flags: List[str] = []
    confidence = 55.0

    price = prop.get("price")
    locality = (prop.get("locality") or prop.get("area_name") or "").strip()
    bedrooms = prop.get("bedrooms")
    ptype = (prop.get("property_type") or "").strip().lower()

    budget_min = prefs.get("budget_min")
    budget_max = prefs.get("budget_max")
    if price and budget_min is not None and budget_max is not None:
        if budget_min <= price <= budget_max:
            score += 20
            confidence += 10
            rationale.append("Price fits the configured budget range.")
        else:
            score -= 15
            risk_flags.append("budget_mismatch")

    preferred_localities = [x.lower() for x in (prefs.get("preferred_localities") or [])]
    if locality and preferred_localities:
        if locality.lower() in preferred_localities:
            score += 15
            confidence += 10
            rationale.append("Property is in a preferred locality.")

    typology = (prefs.get("typology") or "").lower()
    if typology:
        # Simple typology match against bedrooms and property type.
        bhk_token = "".join(ch for ch in typology if ch.isdigit())
        if bhk_token and bedrooms and str(bedrooms) == bhk_token:
            score += 10
            confidence += 8
            rationale.append("Bedroom configuration matches preferred typology.")
        if typology in ptype:
            score += 8
            confidence += 5
            rationale.append("Property type aligns with preferred typology.")

    if not prop.get("scraped_at"):
        risk_flags.append("freshness_unknown")
    else:
        confidence += 5

    score = max(0.0, min(100.0, score))
    confidence = max(0.0, min(100.0, confidence))
    if not rationale:
        rationale.append("Recommendation based on available structured property signals.")
    return _RecommendationScore(score, confidence, rationale, risk_flags)


@router.get("/api/agent/recommendations")
async def get_recommendations(
    profile_version: Optional[int] = Query(default=None, ge=1),
    locality: Optional[str] = Query(default=None),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    property_type: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_auth),
):
    prefs_row = _load_preference_row(user.email)
    if profile_version and prefs_row and int(prefs_row.get("profile_version", 0)) != profile_version:
        raise HTTPException(status_code=409, detail="profile_version mismatch")

    prefs = {
        "budget_min": min_price if min_price is not None else (prefs_row or {}).get("budget_min"),
        "budget_max": max_price if max_price is not None else (prefs_row or {}).get("budget_max"),
        "typology": (prefs_row or {}).get("typology"),
        "preferred_localities": _json_or_default((prefs_row or {}).get("preferred_localities"), []),
    }

    query_service = get_query_service()
    candidates = query_service.search_properties(
        locality=locality,
        min_price=int(prefs["budget_min"]) if prefs["budget_min"] is not None else None,
        max_price=int(prefs["budget_max"]) if prefs["budget_max"] is not None else None,
        property_type=property_type,
        limit=limit * 3,
    )

    ranked = []
    for prop in candidates:
        score_obj = _score_recommendation(prop, prefs)
        freshness_ts = prop.get("scraped_at") or prop.get("updated_at") or prop.get("created_at")
        rec_id = str(prop.get("property_id") or prop.get("id"))
        ranked.append(
            {
                "recommendation_id": rec_id,
                "property": {
                    "property_id": prop.get("property_id"),
                    "title": prop.get("title"),
                    "locality": prop.get("locality") or prop.get("area_name"),
                    "price": prop.get("price"),
                    "bedrooms": prop.get("bedrooms"),
                    "property_type": prop.get("property_type"),
                    "lat": prop.get("latitude"),
                    "lng": prop.get("longitude"),
                    "source_url": prop.get("source_url"),
                },
                "rank_score": round(score_obj.score, 2),
                "confidence_score": round(score_obj.confidence_score, 2),
                "rationale": score_obj.rationale,
                "evidence_sources": ["properties_table", "preferences_profile"],
                "freshness_ts": freshness_ts,
                "risk_flags": score_obj.risk_flags,
            }
        )

    ranked.sort(key=lambda x: x["rank_score"], reverse=True)
    ranked = ranked[:limit]

    return {
        "success": True,
        "user_id": user.email,
        "profile_version": int((prefs_row or {}).get("profile_version", 0)) if prefs_row else None,
        "count": len(ranked),
        "recommendations": ranked,
    }


@router.post("/api/agent/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    user: User = Depends(require_auth),
):
    allowed_actions = {"save", "reject", "contacted", "closed"}
    action = request.action.strip().lower()
    if action not in allowed_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

    confidence_delta_map = {
        "save": 0.08,
        "contacted": 0.05,
        "closed": 0.12,
        "reject": -0.10,
    }
    delta = confidence_delta_map.get(action, 0.0)
    now_ts = time.time()

    conn = _get_conn()
    cur = conn.execute(
        """
        INSERT INTO agent_feedback (
            user_id, recommendation_id, action, reason, confidence_delta, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user.email,
            request.recommendation_id,
            action,
            request.reason,
            delta,
            json.dumps(request.metadata),
            now_ts,
        ),
    )
    conn.commit()

    return {
        "success": True,
        "learning_event_id": cur.lastrowid,
        "updated_confidence_metadata": {
            "recommendation_id": request.recommendation_id,
            "action": action,
            "confidence_delta": delta,
            "recorded_at": now_ts,
        },
    }


@router.get("/api/market/coverage")
async def get_market_coverage(user: User = Depends(require_auth)):
    top_localities = [
        "Whitefield",
        "Sarjapur Road",
        "Electronic City",
        "HSR Layout",
        "Koramangala",
        "Indiranagar",
        "Bellandur",
        "Marathahalli",
        "Hebbal",
        "Yelahanka",
        "JP Nagar",
        "Kanakapura Road",
    ]

    query_service = get_query_service()
    coverage = []
    now_ts = time.time()
    for locality in top_localities:
        rows = query_service.db.execute(
            """
            SELECT
                COUNT(*) as listing_count,
                COUNT(DISTINCT COALESCE(source, 'unknown')) as source_count,
                MAX(COALESCE(scraped_at, updated_at, created_at)) as last_update
            FROM properties
            WHERE LOWER(COALESCE(locality, area_name, '')) LIKE LOWER(?)
            """,
            (f"%{locality}%",),
        )
        row = rows[0] if rows else {}
        listing_count = int(row.get("listing_count") or 0)
        source_count = int(row.get("source_count") or 0)
        last_update = row.get("last_update")

        # Freshness heuristic from latest timestamp when available.
        days_stale = None
        parsed = _parse_timestamp_to_epoch(last_update)
        if parsed is not None:
            days_stale = (now_ts - parsed) / 86400.0

        confidence_band = "low"
        if listing_count >= 50 and source_count >= 2 and (days_stale is None or days_stale <= 7):
            confidence_band = "high"
        elif listing_count >= 20 and source_count >= 1 and (days_stale is None or days_stale <= 30):
            confidence_band = "medium"

        coverage.append(
            {
                "locality": locality,
                "listing_count": listing_count,
                "source_count": source_count,
                "freshness_ts": last_update,
                "confidence_band": confidence_band,
            }
        )

    high = sum(1 for x in coverage if x["confidence_band"] == "high")
    medium = sum(1 for x in coverage if x["confidence_band"] == "medium")
    low = sum(1 for x in coverage if x["confidence_band"] == "low")
    return {
        "success": True,
        "scope": "bengaluru_top12",
        "summary": {
            "total_localities": len(coverage),
            "high_confidence": high,
            "medium_confidence": medium,
            "low_confidence": low,
        },
        "coverage": coverage,
        "generated_at": now_ts,
    }
