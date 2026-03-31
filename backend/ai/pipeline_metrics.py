"""
Valora AI - V2 Pipeline Metrics
Durable SQLite-backed metrics for the section analysis v2 pipeline.

Tracks per-run stats (latency, cache, cost, confidence), per-section latency,
and hallucination events. All writes are fire-and-forget; failures never
propagate into the pipeline.
"""

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("valora.pipeline_metrics")

_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "database")
_DB_PATH = os.path.join(_DB_DIR, "pipeline_metrics.db")

_LOCK = threading.Lock()
_INSTANCE: Optional["PipelineMetrics"] = None


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------

class PipelineMetrics:
    """Durable metrics collector for the v2 section-analysis pipeline."""

    def __init__(self, db_path: str = _DB_PATH) -> None:
        self._db_path = db_path
        _ensure_dir(db_path)
        self._init_db()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS pipeline_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        lat REAL,
                        lng REAL,
                        latency_ms INTEGER,
                        sections TEXT,
                        cache_hits INTEGER DEFAULT 0,
                        cache_misses INTEGER DEFAULT 0,
                        model_calls INTEGER DEFAULT 0,
                        tokens_used INTEGER DEFAULT 0,
                        cost_estimate REAL DEFAULT 0,
                        has_contradictions INTEGER DEFAULT 0,
                        confidence_score REAL DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS section_latencies (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        section_name TEXT NOT NULL,
                        latency_ms INTEGER NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS hallucination_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        section_name TEXT NOT NULL,
                        feature TEXT NOT NULL,
                        expected_value TEXT,
                        actual_value TEXT,
                        resolved INTEGER DEFAULT 0
                    );

                    CREATE INDEX IF NOT EXISTS idx_pipeline_runs_ts
                        ON pipeline_runs(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_section_latencies_ts
                        ON section_latencies(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_section_latencies_name
                        ON section_latencies(section_name);
                    CREATE INDEX IF NOT EXISTS idx_hallucination_ts
                        ON hallucination_events(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_hallucination_section
                        ON hallucination_events(section_name);
                """)
        except Exception:
            logger.exception("[PipelineMetrics] Failed to initialise DB")

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------

    def record_pipeline_run(
        self,
        latency_ms: int,
        sections: List[str],
        cache_hits: int = 0,
        cache_misses: int = 0,
        model_calls: int = 0,
        tokens_used: int = 0,
        cost_estimate: float = 0.0,
        has_contradictions: bool = False,
        confidence_score: float = 0.0,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
    ) -> None:
        """Persist a full pipeline execution snapshot."""
        try:
            with _LOCK, sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO pipeline_runs
                        (timestamp, lat, lng, latency_ms, sections,
                         cache_hits, cache_misses, model_calls, tokens_used,
                         cost_estimate, has_contradictions, confidence_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        time.time(),
                        lat,
                        lng,
                        latency_ms,
                        json.dumps(sections),
                        cache_hits,
                        cache_misses,
                        model_calls,
                        tokens_used,
                        cost_estimate,
                        int(has_contradictions),
                        confidence_score,
                    ),
                )
        except Exception:
            logger.exception("[PipelineMetrics] record_pipeline_run failed")

    def record_section_latency(self, section_name: str, latency_ms: int) -> None:
        """Track latency for a single section."""
        try:
            with _LOCK, sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT INTO section_latencies (timestamp, section_name, latency_ms) VALUES (?, ?, ?)",
                    (time.time(), section_name, latency_ms),
                )
        except Exception:
            logger.exception("[PipelineMetrics] record_section_latency failed")

    def record_hallucination_detected(
        self,
        section_name: str,
        feature: str,
        expected: str,
        actual: str,
    ) -> None:
        """Record a hallucination event."""
        try:
            with _LOCK, sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO hallucination_events
                        (timestamp, section_name, feature, expected_value, actual_value)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (time.time(), section_name, feature, expected, actual),
                )
        except Exception:
            logger.exception("[PipelineMetrics] record_hallucination_detected failed")

    def record_cache_hit(self, section_name: str) -> None:
        """Convenience: log a per-section cache hit."""
        self.record_section_latency(section_name, 0)

    def record_cache_miss(self, section_name: str) -> None:
        """Convenience: log a per-section cache miss (latency=0 placeholder)."""
        self.record_section_latency(section_name, 0)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def _cutoff(self, hours: float) -> float:
        return time.time() - hours * 3600

    def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Aggregated stats over *hours*."""
        try:
            cutoff = self._cutoff(hours)
            with _LOCK, sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    """
                    SELECT
                        COUNT(*),
                        AVG(latency_ms),
                        MIN(latency_ms),
                        MAX(latency_ms),
                        SUM(cache_hits),
                        SUM(cache_misses),
                        SUM(model_calls),
                        SUM(tokens_used),
                        SUM(cost_estimate),
                        SUM(has_contradictions),
                        AVG(confidence_score)
                    FROM pipeline_runs
                    WHERE timestamp >= ?
                    """,
                    (cutoff,),
                ).fetchone()

                section_rows = conn.execute(
                    """
                    SELECT section_name, COUNT(*), AVG(latency_ms)
                    FROM section_latencies
                    WHERE timestamp >= ?
                    GROUP BY section_name
                    """,
                    (cutoff,),
                ).fetchall()

                hall_rows = conn.execute(
                    "SELECT COUNT(*) FROM hallucination_events WHERE timestamp >= ?",
                    (cutoff,),
                ).fetchone()

            count = row[0] or 0
            section_breakdown = {
                r[0]: {"count": r[1], "avg_latency_ms": round(r[2] or 0, 2)}
                for r in section_rows
            }

            return {
                "period_hours": hours,
                "total_runs": count,
                "avg_latency_ms": round(row[1] or 0, 2),
                "min_latency_ms": int(row[2] or 0),
                "max_latency_ms": int(row[3] or 0),
                "total_cache_hits": int(row[4] or 0),
                "total_cache_misses": int(row[5] or 0),
                "total_model_calls": int(row[6] or 0),
                "total_tokens_used": int(row[7] or 0),
                "total_cost_estimate": round(row[8] or 0, 6),
                "total_contradictions": int(row[9] or 0),
                "avg_confidence_score": round(row[10] or 0, 4),
                "total_hallucination_events": int(hall_rows[0] or 0),
                "section_breakdown": section_breakdown,
            }
        except Exception:
            logger.exception("[PipelineMetrics] get_stats failed")
            return {"error": "stats_unavailable"}

    def get_p95_latency(self, hours: int = 24) -> float:
        """P95 pipeline latency over *hours*."""
        try:
            cutoff = self._cutoff(hours)
            with _LOCK, sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT latency_ms FROM pipeline_runs WHERE timestamp >= ? ORDER BY latency_ms",
                    (cutoff,),
                ).fetchall()
            if not rows:
                return 0.0
            vals = [r[0] for r in rows]
            idx = int(len(vals) * 0.95)
            return float(vals[min(idx, len(vals) - 1)])
        except Exception:
            logger.exception("[PipelineMetrics] get_p95_latency failed")
            return 0.0

    def get_hallucination_rate(self, hours: int = 24) -> float:
        """Hallucination events per pipeline run as a percentage."""
        try:
            cutoff = self._cutoff(hours)
            with _LOCK, sqlite3.connect(self._db_path) as conn:
                runs = conn.execute(
                    "SELECT COUNT(*) FROM pipeline_runs WHERE timestamp >= ?",
                    (cutoff,),
                ).fetchone()[0]
                halls = conn.execute(
                    "SELECT COUNT(*) FROM hallucination_events WHERE timestamp >= ?",
                    (cutoff,),
                ).fetchone()[0]
            return round(halls / runs * 100, 4) if runs > 0 else 0.0
        except Exception:
            logger.exception("[PipelineMetrics] get_hallucination_rate failed")
            return 0.0

    def get_cache_hit_rate(self, hours: int = 24) -> float:
        """Cache hit rate as a percentage over *hours*."""
        try:
            cutoff = self._cutoff(hours)
            with _LOCK, sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT SUM(cache_hits), SUM(cache_misses) FROM pipeline_runs WHERE timestamp >= ?",
                    (cutoff,),
                ).fetchone()
            hits = int(row[0] or 0)
            misses = int(row[1] or 0)
            total = hits + misses
            return round(hits / total * 100, 4) if total > 0 else 0.0
        except Exception:
            logger.exception("[PipelineMetrics] get_cache_hit_rate failed")
            return 0.0

    def get_cost_per_query(self, hours: int = 24) -> float:
        """Average estimated cost per query over *hours*."""
        try:
            cutoff = self._cutoff(hours)
            with _LOCK, sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT AVG(cost_estimate) FROM pipeline_runs WHERE timestamp >= ?",
                    (cutoff,),
                ).fetchone()
            return round(row[0] or 0, 6)
        except Exception:
            logger.exception("[PipelineMetrics] get_cost_per_query failed")
            return 0.0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

def get_pipeline_metrics() -> PipelineMetrics:
    """Return the singleton PipelineMetrics instance."""
    global _INSTANCE
    with _LOCK:
        if _INSTANCE is None:
            _INSTANCE = PipelineMetrics()
    return _INSTANCE


# ---------------------------------------------------------------------------
# Integration helper
# ---------------------------------------------------------------------------

def record_v2_pipeline_result(result: Dict[str, Any]) -> None:
    """
    Extract metrics from a v2 pipeline result dict and persist them.

    Expected keys in *result* (all optional – missing values default to 0):
        metadata.total_ms, metadata.lat, metadata.lng,
        metadata.sections, metadata.cache_hits, metadata.cache_misses,
        metadata.model_calls, metadata.tokens_used, metadata.cost_estimate,
        validation.has_contradictions, validation.confidence,
    """
    try:
        meta = result.get("metadata", {})
        validation = result.get("validation", {})
        sections = meta.get("sections", [])

        pm = get_pipeline_metrics()
        pm.record_pipeline_run(
            latency_ms=int(meta.get("total_ms", 0)),
            sections=sections,
            cache_hits=int(meta.get("cache_hits", 0)),
            cache_misses=int(meta.get("cache_misses", 0)),
            model_calls=int(meta.get("model_calls", 0)),
            tokens_used=int(meta.get("tokens_used", 0)),
            cost_estimate=float(meta.get("cost_estimate", 0)),
            has_contradictions=bool(validation.get("has_contradictions", False)),
            confidence_score=float(validation.get("confidence", 0)),
            lat=meta.get("lat"),
            lng=meta.get("lng"),
        )
    except Exception:
        logger.exception("[PipelineMetrics] record_v2_pipeline_result failed")
