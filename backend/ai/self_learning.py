"""
Self-Learning Engine for Valora AI Agentic System.
Tracks tool effectiveness, learns optimal tool sequences per intent/location,
and adjusts routing heuristics based on historical performance.
"""

import json
import time
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger("valora.self_learning")

from config import config
_DB_PATH = config.DB_PATH.parent / "self_learning.db"

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS tool_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    location TEXT,
    intent TEXT,
    params_json TEXT,
    success INTEGER DEFAULT 1,
    data_richness REAL DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    was_useful INTEGER DEFAULT 1,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_to_tool ON tool_outcomes(tool_name);
CREATE INDEX IF NOT EXISTS idx_to_intent ON tool_outcomes(intent);

CREATE TABLE IF NOT EXISTS tool_sequences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent TEXT NOT NULL,
    query_pattern TEXT,
    tool_sequence TEXT NOT NULL,
    avg_confidence REAL DEFAULT 0,
    avg_steps REAL DEFAULT 0,
    use_count INTEGER DEFAULT 1,
    last_used REAL NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ts_intent ON tool_sequences(intent);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    intent TEXT,
    rating INTEGER DEFAULT 0,
    tools_used TEXT,
    agentic_mode INTEGER DEFAULT 0,
    created_at REAL NOT NULL
);
"""


class SelfLearningEngine:
    """Learns from agentic loop outcomes to improve future tool selection."""

    def __init__(self, db_path: str = None):
        self._db_path = db_path or str(_DB_PATH)
        self._conn: Optional[sqlite3.Connection] = None
        self._tool_scores: Dict[str, Dict] = {}  # in-memory cache
        self._intent_tool_map: Dict[str, List[str]] = {}  # learned intent→tools
        self._init_db()
        self._load_learned_patterns()

    def _init_db(self):
        try:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.executescript(_INIT_SQL)
            self._conn.commit()
        except Exception as e:
            logger.error(f"Self-learning DB init failed: {e}")
            self._conn = None

    def _get_conn(self) -> Optional[sqlite3.Connection]:
        if self._conn is None:
            self._init_db()
        return self._conn

    # -----------------------------------------------------------------------
    # Record outcomes
    # -----------------------------------------------------------------------

    def record_tool_outcome(self, tool_name: str, location: str = None,
                            intent: str = None, params: Dict = None,
                            success: bool = True, data_richness: float = 0.0,
                            latency_ms: int = 0, was_useful: bool = True):
        """Record the outcome of a single tool invocation."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            conn.execute("""
                INSERT INTO tool_outcomes
                (tool_name, location, intent, params_json, success, data_richness, latency_ms, was_useful, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tool_name, location, intent,
                json.dumps(params or {}),
                1 if success else 0,
                data_richness, latency_ms,
                1 if was_useful else 0,
                time.time()
            ))
            conn.commit()
            # Update in-memory scores
            self._update_tool_score(tool_name, success, data_richness, latency_ms, was_useful)
        except Exception as e:
            logger.debug(f"Record tool outcome failed: {e}")

    def record_tool_sequence(self, intent: str, query: str,
                             tool_sequence: List[str],
                             confidence: float = 0.0, steps: int = 0):
        """Record a successful tool sequence for an intent pattern."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            # Normalize query to a pattern
            pattern = self._query_to_pattern(query)
            seq_str = json.dumps(tool_sequence)

            # Check if this sequence already exists for this intent
            existing = conn.execute(
                "SELECT id, use_count, avg_confidence, avg_steps FROM tool_sequences "
                "WHERE intent = ? AND tool_sequence = ?",
                (intent, seq_str)
            ).fetchone()

            if existing:
                row_id, count, avg_conf, avg_st = existing
                new_count = count + 1
                new_conf = (avg_conf * count + confidence) / new_count
                new_steps = (avg_st * count + steps) / new_count
                conn.execute(
                    "UPDATE tool_sequences SET use_count = ?, avg_confidence = ?, avg_steps = ?, "
                    "last_used = ?, query_pattern = ? WHERE id = ?",
                    (new_count, new_conf, new_steps, time.time(), pattern, row_id)
                )
            else:
                conn.execute("""
                    INSERT INTO tool_sequences
                    (intent, query_pattern, tool_sequence, avg_confidence, avg_steps, use_count, last_used, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """, (intent, pattern, seq_str, confidence, steps, time.time(), time.time()))

            conn.commit()
        except Exception as e:
            logger.debug(f"Record tool sequence failed: {e}")

    def record_feedback(self, query: str, intent: str = None,
                        rating: int = 0, tools_used: List[str] = None,
                        agentic_mode: bool = False):
        """Record user feedback on a response."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            conn.execute("""
                INSERT INTO feedback (query, intent, rating, tools_used, agentic_mode, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (query, intent, rating, json.dumps(tools_used or []),
                  1 if agentic_mode else 0, time.time()))
            conn.commit()
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Learn & recommend
    # -----------------------------------------------------------------------

    def recommend_tools(self, intent: str, query: str = None) -> List[str]:
        """Recommend the best tool sequence for an intent based on learned patterns."""
        # Check learned intent→tool mapping first
        if intent in self._intent_tool_map:
            return self._intent_tool_map[intent]

        conn = self._get_conn()
        if not conn:
            return []
        try:
            rows = conn.execute(
                "SELECT tool_sequence, avg_confidence, use_count FROM tool_sequences "
                "WHERE intent = ? ORDER BY (avg_confidence * use_count) DESC LIMIT 3",
                (intent,)
            ).fetchall()
            if rows:
                best = json.loads(rows[0][0])
                return best
        except Exception:
            pass
        return []

    def get_tool_effectiveness(self, tool_name: str) -> Dict:
        """Get effectiveness score for a tool."""
        if tool_name in self._tool_scores:
            return self._tool_scores[tool_name]
        return {"score": 0.5, "success_rate": 0.0, "avg_latency_ms": 0, "total_uses": 0}

    def rank_tools_for_intent(self, intent: str, available_tools: List[str]) -> List[Tuple[str, float]]:
        """Rank available tools by learned effectiveness for an intent."""
        conn = self._get_conn()
        if not conn:
            return [(t, 0.5) for t in available_tools]
        try:
            ranked = []
            for tool in available_tools:
                row = conn.execute(
                    "SELECT AVG(was_useful), AVG(data_richness), COUNT(*) FROM tool_outcomes "
                    "WHERE tool_name = ? AND intent = ? AND created_at > ?",
                    (tool, intent, time.time() - 86400 * 30)  # last 30 days
                ).fetchone()
                if row and row[2] > 0:
                    usefulness = row[0] or 0.5
                    richness = row[1] or 0.5
                    score = (usefulness * 0.6 + richness * 0.4)
                    ranked.append((tool, round(score, 3)))
                else:
                    ranked.append((tool, 0.5))  # default score for unknown
            ranked.sort(key=lambda x: x[1], reverse=True)
            return ranked
        except Exception:
            return [(t, 0.5) for t in available_tools]

    def should_use_agentic(self, intent: str, query_length: int) -> Tuple[bool, str]:
        """Learned heuristic: should this query use the agentic loop?"""
        conn = self._get_conn()
        if not conn:
            return False, "no learning data"
        try:
            # Check if agentic mode has been beneficial for this intent
            agentic_stats = conn.execute(
                "SELECT AVG(rating), COUNT(*) FROM feedback WHERE intent = ? AND agentic_mode = 1",
                (intent,)
            ).fetchone()
            normal_stats = conn.execute(
                "SELECT AVG(rating), COUNT(*) FROM feedback WHERE intent = ? AND agentic_mode = 0",
                (intent,)
            ).fetchone()

            a_rating = agentic_stats[0] or 0 if agentic_stats else 0
            a_count = agentic_stats[1] or 0 if agentic_stats else 0
            n_rating = normal_stats[0] or 0 if normal_stats else 0
            n_count = normal_stats[1] or 0 if normal_stats else 0

            # Need at least 5 samples to make a learned decision
            if a_count >= 5 and n_count >= 5:
                if a_rating > n_rating * 1.1:
                    return True, f"learned: agentic rated {a_rating:.1f} vs normal {n_rating:.1f}"
                elif n_rating > a_rating * 1.1:
                    return False, f"learned: normal rated {n_rating:.1f} vs agentic {a_rating:.1f}"

            # Fall back to rule-based
            return None, "insufficient data for learned decision"
        except Exception:
            return None, "learning engine error"

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _update_tool_score(self, tool_name: str, success: bool,
                           data_richness: float, latency_ms: int, was_useful: bool):
        """Update in-memory tool effectiveness score."""
        if tool_name not in self._tool_scores:
            self._tool_scores[tool_name] = {
                "score": 0.5, "success_rate": 0.0, "avg_latency_ms": 0,
                "total_uses": 0, "useful_count": 0
            }
        s = self._tool_scores[tool_name]
        n = s["total_uses"]
        s["total_uses"] = n + 1
        s["success_rate"] = (s["success_rate"] * n + (1 if success else 0)) / (n + 1)
        s["avg_latency_ms"] = int((s["avg_latency_ms"] * n + latency_ms) / (n + 1))
        if was_useful:
            s["useful_count"] = s.get("useful_count", 0) + 1
        s["score"] = round(
            s["success_rate"] * 0.4 + (s["useful_count"] / max(s["total_uses"], 1)) * 0.4
            + min(1.0, data_richness) * 0.2, 3
        )

    def _load_learned_patterns(self):
        """Load learned patterns from DB into memory on startup."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            # Load top tool sequence per intent
            rows = conn.execute(
                "SELECT intent, tool_sequence FROM tool_sequences "
                "WHERE use_count >= 3 ORDER BY (avg_confidence * use_count) DESC"
            ).fetchall()
            for intent, seq_str in rows:
                if intent not in self._intent_tool_map:
                    self._intent_tool_map[intent] = json.loads(seq_str)

            # Load tool scores
            tools = conn.execute(
                "SELECT tool_name, AVG(success), AVG(data_richness), AVG(latency_ms), "
                "COUNT(*), SUM(was_useful) FROM tool_outcomes GROUP BY tool_name"
            ).fetchall()
            for name, avg_success, avg_rich, avg_lat, total, useful in tools:
                self._tool_scores[name] = {
                    "score": round((avg_success or 0) * 0.4 + ((useful or 0) / max(total, 1)) * 0.4 + (avg_rich or 0) * 0.2, 3),
                    "success_rate": round(avg_success or 0, 3),
                    "avg_latency_ms": int(avg_lat or 0),
                    "total_uses": total,
                    "useful_count": useful or 0,
                }
            logger.info(f"[SelfLearning] Loaded {len(self._intent_tool_map)} intent patterns, {len(self._tool_scores)} tool scores")
        except Exception as e:
            logger.debug(f"Load learned patterns failed: {e}")

    @staticmethod
    def _query_to_pattern(query: str) -> str:
        """Normalize a query to a reusable pattern."""
        import re
        q = query.lower().strip()
        # Replace specific locations with placeholder
        q = re.sub(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', '<LOC>', q)
        # Replace numbers
        q = re.sub(r'\d+', '<N>', q)
        return q[:200]

    # -----------------------------------------------------------------------
    # Stats / admin
    # -----------------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Get self-learning statistics for admin dashboard."""
        conn = self._get_conn()
        if not conn:
            return {}
        try:
            tool_count = conn.execute("SELECT COUNT(DISTINCT tool_name) FROM tool_outcomes").fetchone()[0]
            total_outcomes = conn.execute("SELECT COUNT(*) FROM tool_outcomes").fetchone()[0]
            seq_count = conn.execute("SELECT COUNT(*) FROM tool_sequences").fetchone()[0]
            feedback_count = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            avg_rating = conn.execute("SELECT AVG(rating) FROM feedback WHERE rating > 0").fetchone()[0]

            top_tools = conn.execute(
                "SELECT tool_name, COUNT(*), AVG(was_useful), AVG(latency_ms) FROM tool_outcomes "
                "GROUP BY tool_name ORDER BY COUNT(*) DESC LIMIT 10"
            ).fetchall()

            intent_patterns = conn.execute(
                "SELECT intent, tool_sequence, avg_confidence, use_count FROM tool_sequences "
                "ORDER BY use_count DESC LIMIT 10"
            ).fetchall()

            return {
                "tools_tracked": tool_count,
                "total_tool_outcomes": total_outcomes,
                "learned_sequences": seq_count,
                "feedback_entries": feedback_count,
                "avg_user_rating": round(avg_rating, 2) if avg_rating else None,
                "tool_effectiveness": [
                    {"tool": t, "uses": u, "usefulness": round(us or 0, 2), "avg_latency_ms": int(lat or 0)}
                    for t, u, us, lat in top_tools
                ],
                "learned_patterns": [
                    {"intent": i, "sequence": json.loads(s), "confidence": round(c, 2), "uses": u}
                    for i, s, c, u in intent_patterns
                ],
                "in_memory_scores": self._tool_scores,
            }
        except Exception:
            return {}

    def reset(self):
        """Reset all learned data (admin action)."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            conn.execute("DELETE FROM tool_outcomes")
            conn.execute("DELETE FROM tool_sequences")
            conn.execute("DELETE FROM feedback")
            conn.commit()
            self._tool_scores.clear()
            self._intent_tool_map.clear()
        except Exception:
            pass


# Singleton
_engine = None

def get_self_learning_engine() -> SelfLearningEngine:
    global _engine
    if _engine is None:
        _engine = SelfLearningEngine()
    return _engine
