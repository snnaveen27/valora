"""
Agentic Memory — SQLite-backed persistent memory for the Agentic Loop.
Stores tool results keyed by (location, tool_name) so the agent can recall
previous analysis without re-running tools. Includes TTL-based expiration.
"""

import sqlite3
import json
import time
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("valora.agentic_memory")

from config import config
_DB_PATH = config.DB_PATH.parent / "agentic_memory.db"
_DEFAULT_TTL = 3600  # 1 hour — location data doesn't change rapidly
_MAX_ENTRIES = 5000

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT NOT NULL UNIQUE,
    location TEXT,
    tool_name TEXT NOT NULL,
    params_hash TEXT NOT NULL,
    result_json TEXT NOT NULL,
    confidence REAL DEFAULT 0,
    hit_count INTEGER DEFAULT 0,
    created_at REAL NOT NULL,
    last_accessed REAL NOT NULL,
    ttl_seconds REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memory_key ON memory(cache_key);
CREATE INDEX IF NOT EXISTS idx_memory_location ON memory(location);
CREATE INDEX IF NOT EXISTS idx_memory_tool ON memory(tool_name);

CREATE TABLE IF NOT EXISTS query_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    location TEXT,
    intent TEXT,
    tools_used TEXT,
    step_count INTEGER DEFAULT 0,
    confidence REAL DEFAULT 0,
    response_time_ms INTEGER DEFAULT 0,
    success INTEGER DEFAULT 1,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_qlog_location ON query_log(location);
CREATE INDEX IF NOT EXISTS idx_qlog_intent ON query_log(intent);
"""


class AgenticMemory:
    """Persistent memory for agentic loop — caches tool results per location."""

    def __init__(self, db_path: str = None, default_ttl: int = _DEFAULT_TTL):
        self._db_path = db_path or str(_DB_PATH)
        self._default_ttl = default_ttl
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        try:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.executescript(_INIT_SQL)
            self._conn.commit()
        except Exception as e:
            logger.error(f"Failed to init agentic memory DB: {e}")
            self._conn = None

    def _get_conn(self) -> Optional[sqlite3.Connection]:
        if self._conn is None:
            self._init_db()
        return self._conn

    @staticmethod
    def _make_key(tool_name: str, params: Dict) -> str:
        """Generate a deterministic cache key from tool name + params."""
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        h = hashlib.md5(f"{tool_name}:{sorted_params}".encode()).hexdigest()[:12]
        return f"{tool_name}:{h}"

    @staticmethod
    def _params_hash(params: Dict) -> str:
        return hashlib.md5(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:16]

    # -----------------------------------------------------------------------
    # Core API
    # -----------------------------------------------------------------------

    def recall(self, tool_name: str, params: Dict) -> Optional[Dict]:
        """Recall a cached tool result. Returns None if not found or expired."""
        conn = self._get_conn()
        if not conn:
            return None
        try:
            key = self._make_key(tool_name, params)
            row = conn.execute(
                "SELECT result_json, created_at, ttl_seconds, confidence FROM memory WHERE cache_key = ?",
                (key,)
            ).fetchone()
            if not row:
                return None
            result_json, created_at, ttl, confidence = row
            # Check expiration
            if time.time() - created_at > ttl:
                conn.execute("DELETE FROM memory WHERE cache_key = ?", (key,))
                conn.commit()
                return None
            # Increment hit count and update last_accessed
            conn.execute(
                "UPDATE memory SET hit_count = hit_count + 1, last_accessed = ? WHERE cache_key = ?",
                (time.time(), key)
            )
            conn.commit()
            result = json.loads(result_json)
            result["_from_memory"] = True
            result["_memory_confidence"] = confidence
            return result
        except Exception as e:
            logger.debug(f"Memory recall failed: {e}")
            return None

    def store(self, tool_name: str, params: Dict, result: Dict,
              location: str = None, confidence: float = 0.0, ttl: int = None):
        """Store a tool result in memory."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            key = self._make_key(tool_name, params)
            now = time.time()
            ttl_val = ttl or self._default_ttl
            # Clean result of memory flags before storing
            clean_result = {k: v for k, v in result.items() if not k.startswith("_")}
            conn.execute("""
                INSERT OR REPLACE INTO memory
                (cache_key, location, tool_name, params_hash, result_json, confidence, hit_count, created_at, last_accessed, ttl_seconds)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """, (
                key,
                location or params.get("location", ""),
                tool_name,
                self._params_hash(params),
                json.dumps(clean_result, default=str),
                confidence,
                now, now, ttl_val
            ))
            conn.commit()
            self._prune_if_needed()
        except Exception as e:
            logger.debug(f"Memory store failed: {e}")

    def recall_location(self, location: str) -> List[Dict]:
        """Recall ALL cached results for a location (across tools)."""
        conn = self._get_conn()
        if not conn:
            return []
        try:
            rows = conn.execute(
                "SELECT tool_name, result_json, confidence, last_accessed FROM memory "
                "WHERE location = ? AND (? - created_at) < ttl_seconds ORDER BY last_accessed DESC LIMIT 20",
                (location, time.time())
            ).fetchall()
            results = []
            for tool_name, result_json, confidence, last_accessed in rows:
                results.append({
                    "tool": tool_name,
                    "data": json.loads(result_json),
                    "confidence": confidence,
                    "age_seconds": int(time.time() - last_accessed),
                })
            return results
        except Exception:
            return []

    def invalidate(self, location: str = None, tool_name: str = None):
        """Invalidate cached entries by location and/or tool."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            if location and tool_name:
                conn.execute("DELETE FROM memory WHERE location = ? AND tool_name = ?", (location, tool_name))
            elif location:
                conn.execute("DELETE FROM memory WHERE location = ?", (location,))
            elif tool_name:
                conn.execute("DELETE FROM memory WHERE tool_name = ?", (tool_name,))
            conn.commit()
        except Exception:
            pass

    def _prune_if_needed(self):
        """Remove expired entries and enforce max size."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            # Remove expired
            conn.execute("DELETE FROM memory WHERE (? - created_at) > ttl_seconds", (time.time(),))
            # Enforce max entries (remove least recently accessed)
            count = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
            if count > _MAX_ENTRIES:
                conn.execute("""
                    DELETE FROM memory WHERE id IN (
                        SELECT id FROM memory ORDER BY last_accessed ASC LIMIT ?
                    )
                """, (count - _MAX_ENTRIES,))
            conn.commit()
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Query logging (for self-learning)
    # -----------------------------------------------------------------------

    def log_query(self, query: str, location: str = None, intent: str = None,
                  tools_used: List[str] = None, step_count: int = 0,
                  confidence: float = 0.0, response_time_ms: int = 0, success: bool = True):
        """Log a completed query for self-learning analytics."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            conn.execute("""
                INSERT INTO query_log (query, location, intent, tools_used, step_count, confidence, response_time_ms, success, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query, location, intent,
                json.dumps(tools_used or []),
                step_count, confidence, response_time_ms,
                1 if success else 0, time.time()
            ))
            conn.commit()
        except Exception as e:
            logger.debug(f"Query log failed: {e}")

    def get_stats(self) -> Dict:
        """Get memory and query stats."""
        conn = self._get_conn()
        if not conn:
            return {}
        try:
            mem_count = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
            total_hits = conn.execute("SELECT SUM(hit_count) FROM memory").fetchone()[0] or 0
            query_count = conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]
            avg_confidence = conn.execute("SELECT AVG(confidence) FROM query_log WHERE success = 1").fetchone()[0] or 0
            avg_time = conn.execute("SELECT AVG(response_time_ms) FROM query_log").fetchone()[0] or 0
            top_locations = conn.execute(
                "SELECT location, COUNT(*) as cnt FROM query_log WHERE location IS NOT NULL "
                "GROUP BY location ORDER BY cnt DESC LIMIT 10"
            ).fetchall()
            top_tools = conn.execute(
                "SELECT tool_name, SUM(hit_count) as hits FROM memory GROUP BY tool_name ORDER BY hits DESC LIMIT 10"
            ).fetchall()
            return {
                "memory_entries": mem_count,
                "total_cache_hits": total_hits,
                "total_queries": query_count,
                "avg_confidence": round(avg_confidence, 1),
                "avg_response_ms": int(avg_time),
                "top_locations": [{"location": l, "count": c} for l, c in top_locations],
                "top_tools": [{"tool": t, "hits": h} for t, h in top_tools],
            }
        except Exception:
            return {}

    def clear_all(self):
        """Clear all memory (admin action)."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            conn.execute("DELETE FROM memory")
            conn.commit()
        except Exception:
            pass


# Singleton
_memory = None

def get_agentic_memory() -> AgenticMemory:
    global _memory
    if _memory is None:
        _memory = AgenticMemory()
    return _memory
