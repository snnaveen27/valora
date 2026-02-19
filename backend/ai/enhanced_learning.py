"""
Enhanced Self-Learning Engine for Valora AI

Features:
1. Cross-session collective learning (anonymized aggregation)
2. Semantic pattern clustering for intent discovery
3. Negative learning from failures
4. Continuous improvement with A/B testing
5. Query understanding evolution

This module extends the existing SelfLearningEngine with advanced capabilities
for learning from user interactions, failures, and successful patterns.
"""

import json
import time
import logging
import sqlite3
import asyncio
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
from abc import ABC, abstractmethod

logger = logging.getLogger("valora.enhanced_learning")

# Database path - stored alongside existing self_learning.db
from config import config
_DB_PATH = config.DB_PATH.parent / "enhanced_learning.db"


# =============================================================================
# Database Schema
# =============================================================================

_INIT_SQL = """
-- Cross-session collective learnings (anonymized aggregation)
CREATE TABLE IF NOT EXISTS collective_learnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_hash TEXT NOT NULL,
    intent TEXT NOT NULL,
    query_pattern TEXT,
    tool_sequence TEXT,
    success_rate REAL DEFAULT 0.0,
    avg_latency_ms INTEGER DEFAULT 0,
    sample_count INTEGER DEFAULT 1,
    last_updated REAL NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(pattern_hash, intent)
);
CREATE INDEX IF NOT EXISTS idx_cl_pattern ON collective_learnings(pattern_hash);
CREATE INDEX IF NOT EXISTS idx_cl_intent ON collective_learnings(intent);

-- Semantic clusters of similar queries
CREATE TABLE IF NOT EXISTS query_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id TEXT NOT NULL UNIQUE,
    cluster_name TEXT,
    centroid_query TEXT,
    representative_queries TEXT,  -- JSON list of sample queries
    dominant_intent TEXT,
    confidence REAL DEFAULT 0.0,
    member_count INTEGER DEFAULT 0,
    avg_success_rate REAL DEFAULT 0.0,
    created_at REAL NOT NULL,
    last_updated REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_qc_cluster ON query_clusters(cluster_id);
CREATE INDEX IF NOT EXISTS idx_qc_intent ON query_clusters(dominant_intent);

-- Cluster members (individual queries assigned to clusters)
CREATE TABLE IF NOT EXISTS cluster_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    query_text TEXT,
    intent TEXT,
    confidence REAL DEFAULT 0.0,
    was_successful INTEGER DEFAULT 1,
    created_at REAL NOT NULL,
    UNIQUE(cluster_id, query_hash)
);
CREATE INDEX IF NOT EXISTS idx_cm_cluster ON cluster_members(cluster_id);

-- Failure patterns (learned from errors, timeouts, low ratings)
CREATE TABLE IF NOT EXISTS failure_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_hash TEXT NOT NULL,
    query_pattern TEXT,
    intent TEXT,
    tool_name TEXT,
    failure_type TEXT,  -- 'timeout', 'error', 'low_rating', 'user_correction'
    failure_count INTEGER DEFAULT 1,
    last_failure_at REAL NOT NULL,
    recovery_suggestion TEXT,
    created_at REAL NOT NULL,
    UNIQUE(pattern_hash, intent, tool_name, failure_type)
);
CREATE INDEX IF NOT EXISTS idx_fp_pattern ON failure_patterns(pattern_hash);
CREATE INDEX IF NOT EXISTS idx_fp_intent ON failure_patterns(intent);
CREATE INDEX IF NOT EXISTS idx_fp_type ON failure_patterns(failure_type);

-- Improvement history (track metrics over time)
CREATE TABLE IF NOT EXISTS improvement_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    sample_count INTEGER DEFAULT 1,
    metadata TEXT,
    created_at REAL NOT NULL,
    UNIQUE(date, metric_name)
);
CREATE INDEX IF NOT EXISTS idx_ih_date ON improvement_history(date);
CREATE INDEX IF NOT EXISTS idx_ih_metric ON improvement_history(metric_name);

-- A/B experiments
CREATE TABLE IF NOT EXISTS ab_experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL UNIQUE,
    experiment_name TEXT,
    intent TEXT,
    variant_a TEXT,  -- JSON description of variant A
    variant_b TEXT,  -- JSON description of variant B
    status TEXT DEFAULT 'running',  -- 'running', 'completed', 'paused'
    created_at REAL NOT NULL,
    completed_at REAL
);
CREATE INDEX IF NOT EXISTS idx_ab_exp ON ab_experiments(experiment_id);

-- A/B experiment outcomes
CREATE TABLE IF NOT EXISTS ab_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL,
    variant TEXT NOT NULL,  -- 'A' or 'B'
    success INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    avg_latency_ms INTEGER DEFAULT 0,
    avg_rating REAL DEFAULT 0.0,
    last_updated REAL NOT NULL,
    UNIQUE(experiment_id, variant)
);
CREATE INDEX IF NOT EXISTS idx_ab_out_exp ON ab_outcomes(experiment_id);

-- Entity corrections (user corrections for entity extraction)
CREATE TABLE IF NOT EXISTS entity_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    correction_hash TEXT NOT NULL,
    original_text TEXT,
    corrected_text TEXT,
    entity_type TEXT,  -- 'location', 'price', 'bhk', 'amenity', etc.
    query_context TEXT,
    correction_count INTEGER DEFAULT 1,
    last_corrected_at REAL NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(correction_hash, entity_type)
);
CREATE INDEX IF NOT EXISTS idx_ec_hash ON entity_corrections(correction_hash);
CREATE INDEX IF NOT EXISTS idx_ec_type ON entity_corrections(entity_type);

-- Query rewrites (successful rephrasings)
CREATE TABLE IF NOT EXISTS query_rewrites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_query TEXT NOT NULL,
    rewritten_query TEXT NOT NULL,
    intent TEXT,
    success_rate REAL DEFAULT 0.0,
    use_count INTEGER DEFAULT 1,
    last_used REAL NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_qr_original ON query_rewrites(original_query);

-- Low confidence queries (for intent discovery)
CREATE TABLE IF NOT EXISTS low_confidence_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    predicted_intent TEXT,
    confidence REAL,
    actual_intent TEXT,  -- Filled in if corrected
    user_feedback TEXT,
    resolved INTEGER DEFAULT 0,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lcq_resolved ON low_confidence_queries(resolved);

-- User sessions (for per-user personalization layer)
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id_hash TEXT NOT NULL,  -- Anonymized user ID
    session_id TEXT,
    query_count INTEGER DEFAULT 0,
    preferred_tools TEXT,  -- JSON list
    preferred_intents TEXT,  -- JSON list
    avg_rating REAL DEFAULT 0.0,
    last_active REAL NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_us_user ON user_sessions(user_id_hash);
"""


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class LearningEvent:
    """A single learning event"""
    event_type: str  # "success", "failure", "feedback", "correction"
    query: str
    intent: str
    tools_used: List[str]
    outcome: Dict[str, Any]
    user_rating: Optional[int] = None
    latency_ms: int = 0
    timestamp: float = field(default_factory=time.time)
    user_id: Optional[str] = None  # Will be hashed for privacy
    session_id: Optional[str] = None
    error_type: Optional[str] = None  # For failures
    confidence: float = 0.0


@dataclass
class QueryCluster:
    """Represents a semantic cluster of similar queries"""
    cluster_id: str
    cluster_name: str
    centroid_query: str
    representative_queries: List[str]
    dominant_intent: str
    confidence: float
    member_count: int
    avg_success_rate: float


@dataclass
class FailurePattern:
    """A learned failure pattern"""
    pattern_hash: str
    query_pattern: str
    intent: str
    tool_name: str
    failure_type: str
    failure_count: int
    recovery_suggestion: str


@dataclass
class ABExperiment:
    """An A/B test experiment"""
    experiment_id: str
    experiment_name: str
    intent: str
    variant_a: Dict[str, Any]
    variant_b: Dict[str, Any]
    status: str = "running"


@dataclass
class EntityCorrection:
    """A user correction for entity extraction"""
    original_text: str
    corrected_text: str
    entity_type: str
    query_context: str


@dataclass
class ImprovementMetric:
    """A tracked improvement metric"""
    date: str
    metric_name: str
    metric_value: float
    sample_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Embedding Helper (Simple implementation without external dependencies)
# =============================================================================

class SimpleEmbedding:
    """
    Simple embedding implementation using character n-grams.
    For production, replace with sentence-transformers or OpenAI embeddings.
    """
    
    @staticmethod
    def text_to_vector(text: str, dim: int = 128) -> List[float]:
        """Convert text to a simple embedding vector using n-grams."""
        text = text.lower().strip()
        # Create n-gram features
        ngrams = set()
        for n in [2, 3, 4]:
            for i in range(len(text) - n + 1):
                ngrams.add(text[i:i+n])
        
        # Hash n-grams to vector positions
        vector = [0.0] * dim
        for ngram in ngrams:
            pos = hash(ngram) % dim
            vector[pos] += 1.0
        
        # Normalize
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)


# =============================================================================
# Main Enhanced Learning Engine
# =============================================================================

class EnhancedLearningEngine:
    """
    Main enhanced learning engine that extends SelfLearningEngine.
    
    Features:
    - Cross-session collective learning
    - Semantic pattern clustering
    - Negative learning from failures
    - Continuous improvement with A/B testing
    - Query understanding evolution
    """
    
    def __init__(self, db_path: str = None):
        self._db_path = db_path or str(_DB_PATH)
        self._conn: Optional[sqlite3.Connection] = None
        self._embedding = SimpleEmbedding()
        
        # In-memory caches
        self._collective_cache: Dict[str, Dict] = {}
        self._failure_cache: Dict[str, List[FailurePattern]] = {}
        self._cluster_cache: Dict[str, QueryCluster] = {}
        self._ab_assignments: Dict[str, str] = {}  # query_hash -> variant
        
        # Initialize
        self._init_db()
        self._load_caches()
        
        # Integration with existing SelfLearningEngine
        self._base_engine = None
    
    def _init_db(self):
        """Initialize the database with schema."""
        try:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.executescript(_INIT_SQL)
            self._conn.commit()
            logger.info(f"[EnhancedLearning] Database initialized at {self._db_path}")
        except Exception as e:
            logger.error(f"[EnhancedLearning] Database init failed: {e}")
            self._conn = None
    
    def _get_conn(self) -> Optional[sqlite3.Connection]:
        """Get database connection."""
        if self._conn is None:
            self._init_db()
        return self._conn
    
    def _load_caches(self):
        """Load data into memory caches on startup."""
        conn = self._get_conn()
        if not conn:
            return
        
        try:
            # Load collective learnings
            rows = conn.execute(
                "SELECT pattern_hash, intent, tool_sequence, success_rate, sample_count "
                "FROM collective_learnings WHERE sample_count >= 3"
            ).fetchall()
            for row in rows:
                key = f"{row[0]}:{row[1]}"
                self._collective_cache[key] = {
                    "tool_sequence": json.loads(row[2]) if row[2] else [],
                    "success_rate": row[3],
                    "sample_count": row[4]
                }
            
            # Load failure patterns
            rows = conn.execute(
                "SELECT pattern_hash, query_pattern, intent, tool_name, failure_type, "
                "failure_count, recovery_suggestion FROM failure_patterns"
            ).fetchall()
            for row in rows:
                key = row[0]  # pattern_hash
                pattern = FailurePattern(
                    pattern_hash=row[0],
                    query_pattern=row[1],
                    intent=row[2],
                    tool_name=row[3],
                    failure_type=row[4],
                    failure_count=row[5],
                    recovery_suggestion=row[6]
                )
                if key not in self._failure_cache:
                    self._failure_cache[key] = []
                self._failure_cache[key].append(pattern)
            
            # Load query clusters
            rows = conn.execute(
                "SELECT cluster_id, cluster_name, centroid_query, representative_queries, "
                "dominant_intent, confidence, member_count, avg_success_rate FROM query_clusters"
            ).fetchall()
            for row in rows:
                cluster = QueryCluster(
                    cluster_id=row[0],
                    cluster_name=row[1],
                    centroid_query=row[2],
                    representative_queries=json.loads(row[3]) if row[3] else [],
                    dominant_intent=row[4],
                    confidence=row[5],
                    member_count=row[6],
                    avg_success_rate=row[7]
                )
                self._cluster_cache[row[0]] = cluster
            
            logger.info(
                f"[EnhancedLearning] Loaded {len(self._collective_cache)} collective patterns, "
                f"{len(self._failure_cache)} failure patterns, {len(self._cluster_cache)} clusters"
            )
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Cache load failed: {e}")
    
    # -------------------------------------------------------------------------
    # Integration with existing SelfLearningEngine
    # -------------------------------------------------------------------------
    
    def set_base_engine(self, engine):
        """Set the base SelfLearningEngine for integration."""
        self._base_engine = engine
    
    # -------------------------------------------------------------------------
    # 1. Cross-Session Collective Learning
    # -------------------------------------------------------------------------
    
    def record_learning_event(self, event: LearningEvent):
        """
        Record a learning event for analysis.
        
        This is the main entry point for all learning events.
        """
        conn = self._get_conn()
        if not conn:
            return
        
        try:
            # Hash user ID for privacy
            user_hash = self._hash_user_id(event.user_id) if event.user_id else "anonymous"
            
            # Update collective learnings
            self._update_collective_learning(conn, event)
            
            # Handle specific event types
            if event.event_type == "failure":
                self._record_failure_pattern(conn, event)
            elif event.event_type == "correction":
                self._record_entity_correction(conn, event)
            elif event.event_type == "feedback":
                self._record_feedback(conn, event)
            
            # Update improvement metrics
            self._update_improvement_metrics(conn, event)
            
            # Update user session
            self._update_user_session(conn, user_hash, event)
            
            # Record for clustering
            self._record_for_clustering(conn, event)
            
            conn.commit()
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Record event failed: {e}")
    
    def _update_collective_learning(self, conn: sqlite3.Connection, event: LearningEvent):
        """Update collective learning patterns."""
        pattern_hash = self._hash_query(event.query)
        query_pattern = self._query_to_pattern(event.query)
        tool_sequence = json.dumps(event.tools_used)
        
        # Check if pattern exists
        existing = conn.execute(
            "SELECT success_rate, avg_latency_ms, sample_count FROM collective_learnings "
            "WHERE pattern_hash = ? AND intent = ?",
            (pattern_hash, event.intent)
        ).fetchone()
        
        success = 1 if event.event_type == "success" else 0
        
        if existing:
            # Update with exponential moving average
            old_rate, old_latency, count = existing
            new_count = count + 1
            new_rate = old_rate + (success - old_rate) / new_count
            new_latency = int(old_latency + (event.latency_ms - old_latency) / new_count)
            
            conn.execute(
                "UPDATE collective_learnings SET success_rate = ?, avg_latency_ms = ?, "
                "sample_count = ?, last_updated = ?, query_pattern = ? "
                "WHERE pattern_hash = ? AND intent = ?",
                (new_rate, new_latency, new_count, time.time(), query_pattern,
                 pattern_hash, event.intent)
            )
        else:
            conn.execute(
                "INSERT INTO collective_learnings "
                "(pattern_hash, intent, query_pattern, tool_sequence, success_rate, "
                "avg_latency_ms, sample_count, last_updated, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)",
                (pattern_hash, event.intent, query_pattern, tool_sequence,
                 float(success), event.latency_ms, time.time(), time.time())
            )
    
    def get_collective_recommendations(self, intent: str, query: str = None) -> Dict:
        """
        Get recommendations from collective learning.
        
        Returns the best tool sequence and expected success rate for an intent.
        """
        conn = self._get_conn()
        if not conn:
            return {"tool_sequence": [], "success_rate": 0.0, "sample_count": 0}
        
        try:
            # First check cache
            if query:
                pattern_hash = self._hash_query(query)
                cache_key = f"{pattern_hash}:{intent}"
                if cache_key in self._collective_cache:
                    return self._collective_cache[cache_key]
            
            # Query database
            rows = conn.execute(
                "SELECT tool_sequence, success_rate, sample_count, avg_latency_ms "
                "FROM collective_learnings WHERE intent = ? "
                "ORDER BY (success_rate * sample_count) DESC LIMIT 5",
                (intent,)
            ).fetchall()
            
            if rows:
                best = rows[0]
                return {
                    "tool_sequence": json.loads(best[0]) if best[0] else [],
                    "success_rate": best[1],
                    "sample_count": best[2],
                    "avg_latency_ms": best[3]
                }
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Get collective recommendations failed: {e}")
        
        return {"tool_sequence": [], "success_rate": 0.0, "sample_count": 0}
    
    # -------------------------------------------------------------------------
    # 2. Semantic Pattern Clustering
    # -------------------------------------------------------------------------
    
    def _record_for_clustering(self, conn: sqlite3.Connection, event: LearningEvent):
        """Record a query for clustering analysis."""
        query_hash = self._hash_query(event.query)
        
        # Find best matching cluster
        best_cluster = None
        best_similarity = 0.0
        
        query_vector = self._embedding.text_to_vector(event.query)
        
        for cluster_id, cluster in self._cluster_cache.items():
            if cluster.centroid_query:
                centroid_vector = self._embedding.text_to_vector(cluster.centroid_query)
                similarity = self._embedding.cosine_similarity(query_vector, centroid_vector)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_cluster = cluster_id
        
        # If good match found, add to cluster
        if best_cluster and best_similarity > 0.7:
            conn.execute(
                "INSERT OR IGNORE INTO cluster_members "
                "(cluster_id, query_hash, query_text, intent, confidence, was_successful, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (best_cluster, query_hash, event.query[:500], event.intent,
                 best_similarity, 1 if event.event_type == "success" else 0, time.time())
            )
        else:
            # Create new cluster for low-confidence queries
            if event.confidence < 0.6:
                self._create_new_cluster(conn, event)
    
    def _create_new_cluster(self, conn: sqlite3.Connection, event: LearningEvent):
        """Create a new cluster for a low-confidence query."""
        cluster_id = f"cluster_{int(time.time())}_{hash(event.query) % 10000}"
        
        conn.execute(
            "INSERT OR IGNORE INTO query_clusters "
            "(cluster_id, cluster_name, centroid_query, representative_queries, "
            "dominant_intent, confidence, member_count, avg_success_rate, created_at, last_updated) "
            "VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
            (cluster_id, f"Auto-discovered {event.intent}", event.query[:500],
             json.dumps([event.query[:200]]), event.intent, event.confidence,
             1.0 if event.event_type == "success" else 0.0, time.time(), time.time())
        )
        
        # Add to cluster members
        query_hash = self._hash_query(event.query)
        conn.execute(
            "INSERT OR IGNORE INTO cluster_members "
            "(cluster_id, query_hash, query_text, intent, confidence, was_successful, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cluster_id, query_hash, event.query[:500], event.intent,
             event.confidence, 1 if event.event_type == "success" else 0, time.time())
        )
    
    def discover_new_intent_patterns(self, min_samples: int = 5, min_confidence: float = 0.5) -> List[Dict]:
        """
        Analyze low-confidence queries to discover new intent patterns.
        
        Returns a list of suggested new intent patterns.
        """
        conn = self._get_conn()
        if not conn:
            return []
        
        discovered_patterns = []
        
        try:
            # Get unresolved low-confidence queries
            rows = conn.execute(
                "SELECT query, predicted_intent, confidence, COUNT(*) as cnt "
                "FROM low_confidence_queries WHERE resolved = 0 AND confidence < ? "
                "GROUP BY query HAVING cnt >= ?",
                (min_confidence, min_samples)
            ).fetchall()
            
            for row in rows:
                query, predicted_intent, confidence, count = row
                
                # Find similar queries in clusters
                similar_queries = self._find_similar_queries(conn, query)
                
                if len(similar_queries) >= min_samples:
                    # Determine dominant intent from similar queries
                    intent_counts = defaultdict(int)
                    for sq in similar_queries:
                        intent_counts[sq['intent']] += 1
                    
                    dominant_intent = max(intent_counts.items(), key=lambda x: x[1])[0]
                    
                    discovered_patterns.append({
                        "query_pattern": self._query_to_pattern(query),
                        "suggested_intent": dominant_intent,
                        "confidence": confidence,
                        "sample_count": count,
                        "similar_queries": [sq['query'] for sq in similar_queries[:5]],
                        "intent_distribution": dict(intent_counts)
                    })
            
            logger.info(f"[EnhancedLearning] Discovered {len(discovered_patterns)} new intent patterns")
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Intent discovery failed: {e}")
        
        return discovered_patterns
    
    def _find_similar_queries(self, conn: sqlite3.Connection, query: str, threshold: float = 0.7) -> List[Dict]:
        """Find queries similar to the given query."""
        similar = []
        query_vector = self._embedding.text_to_vector(query)
        
        try:
            # Get queries from cluster members
            rows = conn.execute(
                "SELECT query_text, intent, confidence FROM cluster_members LIMIT 1000"
            ).fetchall()
            
            for row in rows:
                other_query, intent, confidence = row
                other_vector = self._embedding.text_to_vector(other_query)
                similarity = self._embedding.cosine_similarity(query_vector, other_vector)
                
                if similarity >= threshold:
                    similar.append({
                        "query": other_query,
                        "intent": intent,
                        "confidence": confidence,
                        "similarity": similarity
                    })
            
            similar.sort(key=lambda x: x["similarity"], reverse=True)
        except Exception:
            pass
        
        return similar
    
    def get_query_cluster(self, query: str) -> Optional[QueryCluster]:
        """Get the cluster for a query if one exists."""
        query_vector = self._embedding.text_to_vector(query)
        
        best_cluster = None
        best_similarity = 0.0
        
        for cluster in self._cluster_cache.values():
            if cluster.centroid_query:
                centroid_vector = self._embedding.text_to_vector(cluster.centroid_query)
                similarity = self._embedding.cosine_similarity(query_vector, centroid_vector)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_cluster = cluster
        
        if best_similarity > 0.6:
            return best_cluster
        return None
    
    # -------------------------------------------------------------------------
    # 3. Negative Learning from Failures
    # -------------------------------------------------------------------------
    
    def _record_failure_pattern(self, conn: sqlite3.Connection, event: LearningEvent):
        """Record a failure pattern for future avoidance."""
        pattern_hash = self._hash_query(event.query)
        query_pattern = self._query_to_pattern(event.query)
        failure_type = event.error_type or "unknown"
        
        # Record for each tool that failed
        for tool in event.tools_used:
            existing = conn.execute(
                "SELECT failure_count FROM failure_patterns "
                "WHERE pattern_hash = ? AND intent = ? AND tool_name = ? AND failure_type = ?",
                (pattern_hash, event.intent, tool, failure_type)
            ).fetchone()
            
            if existing:
                new_count = existing[0] + 1
                conn.execute(
                    "UPDATE failure_patterns SET failure_count = ?, last_failure_at = ? "
                    "WHERE pattern_hash = ? AND intent = ? AND tool_name = ? AND failure_type = ?",
                    (new_count, time.time(), pattern_hash, event.intent, tool, failure_type)
                )
            else:
                recovery = self._suggest_recovery(event)
                conn.execute(
                    "INSERT INTO failure_patterns "
                    "(pattern_hash, query_pattern, intent, tool_name, failure_type, "
                    "failure_count, last_failure_at, recovery_suggestion, created_at) "
                    "VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)",
                    (pattern_hash, query_pattern, event.intent, tool, failure_type,
                     time.time(), recovery, time.time())
                )
    
    def _suggest_recovery(self, event: LearningEvent) -> str:
        """Suggest a recovery strategy for a failure."""
        if event.error_type == "timeout":
            return "Consider using faster tools or reducing query complexity"
        elif event.error_type == "low_rating":
            return "Try alternative tool sequence or provide more context"
        elif event.error_type == "error":
            return "Check tool availability and parameters"
        return "Review and adjust approach"
    
    def get_failure_avoidance(self, query: str, intent: str) -> List[str]:
        """
        Get patterns to avoid based on past failures.
        
        Returns a list of tools/patterns that have failed for similar queries.
        """
        conn = self._get_conn()
        if not conn:
            return []
        
        avoid_patterns = []
        
        try:
            pattern_hash = self._hash_query(query)
            
            # Check cache first
            if pattern_hash in self._failure_cache:
                for pattern in self._failure_cache[pattern_hash]:
                    if pattern.intent == intent or pattern.intent is None:
                        avoid_patterns.append({
                            "tool": pattern.tool_name,
                            "failure_type": pattern.failure_type,
                            "count": pattern.failure_count,
                            "suggestion": pattern.recovery_suggestion
                        })
            
            # Also check database for similar patterns
            query_pattern = self._query_to_pattern(query)
            rows = conn.execute(
                "SELECT tool_name, failure_type, failure_count, recovery_suggestion "
                "FROM failure_patterns WHERE intent = ? AND failure_count >= 3 "
                "ORDER BY failure_count DESC LIMIT 10",
                (intent,)
            ).fetchall()
            
            for row in rows:
                avoid_patterns.append({
                    "tool": row[0],
                    "failure_type": row[1],
                    "count": row[2],
                    "suggestion": row[3]
                })
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Get failure avoidance failed: {e}")
        
        return avoid_patterns
    
    def record_timeout(self, query: str, intent: str, tool: str, latency_ms: int):
        """Record a timeout event."""
        event = LearningEvent(
            event_type="failure",
            query=query,
            intent=intent,
            tools_used=[tool],
            outcome={"timeout": True},
            latency_ms=latency_ms,
            error_type="timeout"
        )
        self.record_learning_event(event)
    
    def record_error(self, query: str, intent: str, tool: str, error_message: str):
        """Record an error event."""
        event = LearningEvent(
            event_type="failure",
            query=query,
            intent=intent,
            tools_used=[tool],
            outcome={"error": error_message},
            error_type="error"
        )
        self.record_learning_event(event)
    
    def record_low_rating(self, query: str, intent: str, tools: List[str], rating: int):
        """Record a low rating event."""
        event = LearningEvent(
            event_type="failure",
            query=query,
            intent=intent,
            tools_used=tools,
            outcome={"rating": rating},
            user_rating=rating,
            error_type="low_rating"
        )
        self.record_learning_event(event)
    
    # -------------------------------------------------------------------------
    # 4. Continuous Improvement Loop
    # -------------------------------------------------------------------------
    
    def _update_improvement_metrics(self, conn: sqlite3.Connection, event: LearningEvent):
        """Update improvement metrics for tracking over time."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Update success rate metric
        self._update_metric(conn, today, "success_rate",
                           1.0 if event.event_type == "success" else 0.0)
        
        # Update latency metric
        self._update_metric(conn, today, "avg_latency_ms", float(event.latency_ms))
        
        # Update rating metric if available
        if event.user_rating:
            self._update_metric(conn, today, "avg_rating", float(event.user_rating))
        
        # Update per-intent metrics
        self._update_metric(conn, today, f"intent_{event.intent}_success",
                           1.0 if event.event_type == "success" else 0.0)
    
    def _update_metric(self, conn: sqlite3.Connection, date: str, metric_name: str, value: float):
        """Update a single metric."""
        existing = conn.execute(
            "SELECT metric_value, sample_count FROM improvement_history "
            "WHERE date = ? AND metric_name = ?",
            (date, metric_name)
        ).fetchone()
        
        if existing:
            old_value, count = existing
            new_count = count + 1
            new_value = old_value + (value - old_value) / new_count
            conn.execute(
                "UPDATE improvement_history SET metric_value = ?, sample_count = ? "
                "WHERE date = ? AND metric_name = ?",
                (new_value, new_count, date, metric_name)
            )
        else:
            conn.execute(
                "INSERT INTO improvement_history "
                "(date, metric_name, metric_value, sample_count, created_at) "
                "VALUES (?, ?, ?, 1, ?)",
                (date, metric_name, value, time.time())
            )
    
    def get_improvement_trend(self, days: int = 30) -> Dict:
        """
        Get improvement metrics over time.
        
        Returns trends for success rate, latency, and ratings.
        """
        conn = self._get_conn()
        if not conn:
            return {}
        
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            rows = conn.execute(
                "SELECT date, metric_name, metric_value, sample_count "
                "FROM improvement_history WHERE date >= ? "
                "ORDER BY date ASC",
                (start_date,)
            ).fetchall()
            
            trends = defaultdict(list)
            for row in rows:
                trends[row[1]].append({
                    "date": row[0],
                    "value": row[2],
                    "sample_count": row[3]
                })
            
            # Calculate improvement percentages
            result = {}
            for metric, values in trends.items():
                if len(values) >= 2:
                    first_val = values[0]["value"]
                    last_val = values[-1]["value"]
                    if first_val > 0:
                        improvement = ((last_val - first_val) / first_val) * 100
                    else:
                        improvement = 0
                    result[metric] = {
                        "trend": values,
                        "improvement_pct": round(improvement, 2),
                        "current_value": last_val
                    }
            
            return result
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Get improvement trend failed: {e}")
            return {}
    
    # -------------------------------------------------------------------------
    # A/B Testing Framework
    # -------------------------------------------------------------------------
    
    def create_ab_experiment(self, experiment_id: str, experiment_name: str,
                            intent: str, variant_a: Dict, variant_b: Dict) -> bool:
        """Create a new A/B test experiment."""
        conn = self._get_conn()
        if not conn:
            return False
        
        try:
            conn.execute(
                "INSERT INTO ab_experiments "
                "(experiment_id, experiment_name, intent, variant_a, variant_b, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'running', ?)",
                (experiment_id, experiment_name, intent,
                 json.dumps(variant_a), json.dumps(variant_b), time.time())
            )
            
            # Initialize outcome tracking
            conn.execute(
                "INSERT INTO ab_outcomes (experiment_id, variant, success, total, last_updated) "
                "VALUES (?, 'A', 0, 0, ?)",
                (experiment_id, time.time())
            )
            conn.execute(
                "INSERT INTO ab_outcomes (experiment_id, variant, success, total, last_updated) "
                "VALUES (?, 'B', 0, 0, ?)",
                (experiment_id, time.time())
            )
            
            conn.commit()
            logger.info(f"[EnhancedLearning] Created A/B experiment: {experiment_id}")
            return True
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Create A/B experiment failed: {e}")
            return False
    
    def get_ab_test_variant(self, query: str, intent: str) -> str:
        """
        Get which variant to use for A/B testing.
        
        Uses consistent hashing to ensure same user gets same variant.
        """
        conn = self._get_conn()
        if not conn:
            return "A"
        
        try:
            # Find running experiment for this intent
            row = conn.execute(
                "SELECT experiment_id FROM ab_experiments "
                "WHERE intent = ? AND status = 'running' LIMIT 1",
                (intent,)
            ).fetchone()
            
            if not row:
                return "A"
            
            experiment_id = row[0]
            
            # Check if we already assigned this query
            query_hash = self._hash_query(query)
            cache_key = f"{experiment_id}:{query_hash}"
            
            if cache_key in self._ab_assignments:
                return self._ab_assignments[cache_key]
            
            # Assign variant based on hash (50/50 split)
            variant = "A" if hash(query_hash) % 2 == 0 else "B"
            self._ab_assignments[cache_key] = variant
            
            return variant
        except Exception:
            return "A"
    
    def record_ab_outcome(self, experiment_id: str, variant: str,
                         success: bool, latency_ms: int = 0, rating: float = 0.0):
        """Record an A/B test outcome."""
        conn = self._get_conn()
        if not conn:
            return
        
        try:
            row = conn.execute(
                "SELECT success, total, avg_latency_ms, avg_rating FROM ab_outcomes "
                "WHERE experiment_id = ? AND variant = ?",
                (experiment_id, variant)
            ).fetchone()
            
            if row:
                old_success, total, old_latency, old_rating = row
                new_total = total + 1
                new_success = old_success + (1 if success else 0)
                new_latency = int((old_latency * total + latency_ms) / new_total)
                new_rating = (old_rating * total + rating) / new_total
                
                conn.execute(
                    "UPDATE ab_outcomes SET success = ?, total = ?, "
                    "avg_latency_ms = ?, avg_rating = ?, last_updated = ? "
                    "WHERE experiment_id = ? AND variant = ?",
                    (new_success, new_total, new_latency, new_rating,
                     time.time(), experiment_id, variant)
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Record A/B outcome failed: {e}")
    
    def get_ab_experiment_results(self, experiment_id: str) -> Dict:
        """Get results of an A/B test experiment."""
        conn = self._get_conn()
        if not conn:
            return {}
        
        try:
            # Get experiment details
            exp_row = conn.execute(
                "SELECT experiment_name, intent, variant_a, variant_b, status FROM ab_experiments "
                "WHERE experiment_id = ?",
                (experiment_id,)
            ).fetchone()
            
            if not exp_row:
                return {}
            
            # Get outcomes
            rows = conn.execute(
                "SELECT variant, success, total, avg_latency_ms, avg_rating FROM ab_outcomes "
                "WHERE experiment_id = ?",
                (experiment_id,)
            ).fetchall()
            
            results = {
                "experiment_id": experiment_id,
                "experiment_name": exp_row[0],
                "intent": exp_row[1],
                "variant_a": json.loads(exp_row[2]),
                "variant_b": json.loads(exp_row[3]),
                "status": exp_row[4],
                "outcomes": {}
            }
            
            for row in rows:
                variant, success, total, latency, rating = row
                results["outcomes"][variant] = {
                    "success_count": success,
                    "total": total,
                    "success_rate": round(success / max(total, 1), 3),
                    "avg_latency_ms": latency,
                    "avg_rating": round(rating, 2)
                }
            
            # Determine winner if enough samples
            if "A" in results["outcomes"] and "B" in results["outcomes"]:
                a_rate = results["outcomes"]["A"]["success_rate"]
                b_rate = results["outcomes"]["B"]["success_rate"]
                a_total = results["outcomes"]["A"]["total"]
                b_total = results["outcomes"]["B"]["total"]
                
                if a_total >= 100 and b_total >= 100:
                    if a_rate > b_rate + 0.05:
                        results["winner"] = "A"
                    elif b_rate > a_rate + 0.05:
                        results["winner"] = "B"
                    else:
                        results["winner"] = "tie"
            
            return results
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Get A/B results failed: {e}")
            return {}
    
    def promote_ab_winner(self, experiment_id: str) -> bool:
        """Promote the winning variant and complete the experiment."""
        conn = self._get_conn()
        if not conn:
            return False
        
        try:
            results = self.get_ab_experiment_results(experiment_id)
            if "winner" not in results or results["winner"] == "tie":
                return False
            
            winner = results["winner"]
            winning_variant = results[f"variant_{winner.lower()}"]
            
            # Mark experiment as completed
            conn.execute(
                "UPDATE ab_experiments SET status = 'completed', completed_at = ? "
                "WHERE experiment_id = ?",
                (time.time(), experiment_id)
            )
            
            # Add winning pattern to collective learnings
            intent = results["intent"]
            if "tool_sequence" in winning_variant:
                conn.execute(
                    "INSERT INTO collective_learnings "
                    "(pattern_hash, intent, tool_sequence, success_rate, sample_count, last_updated, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (f"ab_{experiment_id}", intent,
                     json.dumps(winning_variant["tool_sequence"]),
                     results["outcomes"][winner]["success_rate"],
                     results["outcomes"][winner]["total"],
                     time.time(), time.time())
                )
            
            conn.commit()
            logger.info(f"[EnhancedLearning] Promoted variant {winner} for experiment {experiment_id}")
            return True
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Promote A/B winner failed: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # 5. Query Understanding Evolution
    # -------------------------------------------------------------------------
    
    def _record_entity_correction(self, conn: sqlite3.Connection, event: LearningEvent):
        """Record an entity extraction correction."""
        if "original" not in event.outcome or "corrected" not in event.outcome:
            return
        
        original = event.outcome["original"]
        corrected = event.outcome["corrected"]
        entity_type = event.outcome.get("entity_type", "unknown")
        
        correction_hash = self._hash_text(f"{original}:{corrected}")
        
        existing = conn.execute(
            "SELECT correction_count FROM entity_corrections "
            "WHERE correction_hash = ? AND entity_type = ?",
            (correction_hash, entity_type)
        ).fetchone()
        
        if existing:
            new_count = existing[0] + 1
            conn.execute(
                "UPDATE entity_corrections SET correction_count = ?, last_corrected_at = ? "
                "WHERE correction_hash = ? AND entity_type = ?",
                (new_count, time.time(), correction_hash, entity_type)
            )
        else:
            conn.execute(
                "INSERT INTO entity_corrections "
                "(correction_hash, original_text, corrected_text, entity_type, "
                "query_context, correction_count, last_corrected_at, created_at) "
                "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                (correction_hash, original, corrected, entity_type,
                 event.query[:500], time.time(), time.time())
            )
    
    def learn_entity_correction(self, original: str, corrected: str,
                               entity_type: str, query_context: str = ""):
        """Learn from an entity extraction correction."""
        event = LearningEvent(
            event_type="correction",
            query=query_context,
            intent="entity_extraction",
            tools_used=[],
            outcome={
                "original": original,
                "corrected": corrected,
                "entity_type": entity_type
            }
        )
        self.record_learning_event(event)
    
    def get_entity_corrections(self, entity_type: str = None) -> List[Dict]:
        """Get learned entity corrections."""
        conn = self._get_conn()
        if not conn:
            return []
        
        try:
            if entity_type:
                rows = conn.execute(
                    "SELECT original_text, corrected_text, correction_count "
                    "FROM entity_corrections WHERE entity_type = ? "
                    "ORDER BY correction_count DESC LIMIT 50",
                    (entity_type,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT original_text, corrected_text, entity_type, correction_count "
                    "FROM entity_corrections ORDER BY correction_count DESC LIMIT 50"
                ).fetchall()
            
            return [dict(row) for row in rows]
        except Exception:
            return []
    
    def get_query_rewriting_suggestions(self, query: str) -> List[str]:
        """
        Get successful rephrasings for a query pattern.
        
        Returns a list of alternative query formulations that have worked well.
        """
        conn = self._get_conn()
        if not conn:
            return []
        
        suggestions = []
        
        try:
            # Find similar queries that have been rewritten successfully
            query_pattern = self._query_to_pattern(query)
            
            rows = conn.execute(
                "SELECT rewritten_query, success_rate, use_count FROM query_rewrites "
                "WHERE original_query LIKE ? AND success_rate > 0.7 "
                "ORDER BY (success_rate * use_count) DESC LIMIT 5",
                (f"%{query_pattern[:50]}%",)
            ).fetchall()
            
            for row in rows:
                suggestions.append({
                    "rewritten_query": row[0],
                    "success_rate": row[1],
                    "use_count": row[2]
                })
            
            # Also check cluster representatives
            cluster = self.get_query_cluster(query)
            if cluster and cluster.representative_queries:
                for rep_query in cluster.representative_queries[:3]:
                    if rep_query not in [s["rewritten_query"] for s in suggestions]:
                        suggestions.append({
                            "rewritten_query": rep_query,
                            "success_rate": cluster.avg_success_rate,
                            "use_count": cluster.member_count
                        })
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Get rewriting suggestions failed: {e}")
        
        return suggestions
    
    def record_query_rewrite(self, original: str, rewritten: str,
                            intent: str, success: bool):
        """Record a successful query rewrite."""
        conn = self._get_conn()
        if not conn:
            return
        
        try:
            existing = conn.execute(
                "SELECT success_rate, use_count FROM query_rewrites "
                "WHERE original_query = ? AND rewritten_query = ?",
                (original, rewritten)
            ).fetchone()
            
            if existing:
                old_rate, count = existing
                new_count = count + 1
                new_rate = old_rate + ((1.0 if success else 0.0) - old_rate) / new_count
                conn.execute(
                    "UPDATE query_rewrites SET success_rate = ?, use_count = ?, last_used = ? "
                    "WHERE original_query = ? AND rewritten_query = ?",
                    (new_rate, new_count, time.time(), original, rewritten)
                )
            else:
                conn.execute(
                    "INSERT INTO query_rewrites "
                    "(original_query, rewritten_query, intent, success_rate, use_count, last_used, created_at) "
                    "VALUES (?, ?, ?, ?, 1, ?, ?)",
                    (original, rewritten, intent, 1.0 if success else 0.0, time.time(), time.time())
                )
            conn.commit()
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Record query rewrite failed: {e}")
    
    # -------------------------------------------------------------------------
    # User Session Management
    # -------------------------------------------------------------------------
    
    def _update_user_session(self, conn: sqlite3.Connection, user_hash: str, event: LearningEvent):
        """Update user session for personalization."""
        try:
            existing = conn.execute(
                "SELECT query_count, preferred_tools, preferred_intents, avg_rating "
                "FROM user_sessions WHERE user_id_hash = ?",
                (user_hash,)
            ).fetchone()
            
            if existing:
                count, tools_json, intents_json, old_rating = existing
                new_count = count + 1
                
                # Update preferred tools
                tools = json.loads(tools_json) if tools_json else []
                for tool in event.tools_used:
                    if tool not in tools:
                        tools.append(tool)
                    tools = tools[:20]  # Keep top 20
                
                # Update preferred intents
                intents = json.loads(intents_json) if intents_json else []
                if event.intent and event.intent not in intents:
                    intents.append(event.intent)
                    intents = intents[:20]
                
                # Update rating
                new_rating = old_rating
                if event.user_rating:
                    new_rating = old_rating + (event.user_rating - old_rating) / new_count
                
                conn.execute(
                    "UPDATE user_sessions SET query_count = ?, preferred_tools = ?, "
                    "preferred_intents = ?, avg_rating = ?, last_active = ? "
                    "WHERE user_id_hash = ?",
                    (new_count, json.dumps(tools), json.dumps(intents),
                     new_rating, time.time(), user_hash)
                )
            else:
                conn.execute(
                    "INSERT INTO user_sessions "
                    "(user_id_hash, session_id, query_count, preferred_tools, preferred_intents, "
                    "avg_rating, last_active, created_at) "
                    "VALUES (?, ?, 1, ?, ?, ?, ?, ?)",
                    (user_hash, event.session_id,
                     json.dumps(event.tools_used[:20]),
                     json.dumps([event.intent] if event.intent else []),
                     float(event.user_rating) if event.user_rating else 0.0,
                     time.time(), time.time())
                )
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Update user session failed: {e}")
    
    def get_user_preferences(self, user_id: str) -> Dict:
        """Get personalized preferences for a user."""
        conn = self._get_conn()
        if not conn:
            return {}
        
        user_hash = self._hash_user_id(user_id)
        
        try:
            row = conn.execute(
                "SELECT preferred_tools, preferred_intents, avg_rating, query_count "
                "FROM user_sessions WHERE user_id_hash = ?",
                (user_hash,)
            ).fetchone()
            
            if row:
                return {
                    "preferred_tools": json.loads(row[0]) if row[0] else [],
                    "preferred_intents": json.loads(row[1]) if row[1] else [],
                    "avg_rating": row[2],
                    "query_count": row[3]
                }
        except Exception:
            pass
        
        return {}
    
    # -------------------------------------------------------------------------
    # Feedback Recording
    # -------------------------------------------------------------------------
    
    def _record_feedback(self, conn: sqlite3.Connection, event: LearningEvent):
        """Record user feedback."""
        # Record low-confidence query if applicable
        if event.confidence < 0.6:
            conn.execute(
                "INSERT INTO low_confidence_queries "
                "(query, predicted_intent, confidence, user_feedback, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (event.query[:1000], event.intent, event.confidence,
                 event.outcome.get("feedback", ""), time.time())
            )
    
    def record_feedback(self, query: str, intent: str, rating: int,
                       feedback: str = "", tools_used: List[str] = None,
                       confidence: float = 1.0):
        """Record user feedback on a response."""
        event = LearningEvent(
            event_type="feedback",
            query=query,
            intent=intent,
            tools_used=tools_used or [],
            outcome={"feedback": feedback},
            user_rating=rating,
            confidence=confidence
        )
        self.record_learning_event(event)
        
        # Also record as failure if low rating
        if rating <= 2:
            self.record_low_rating(query, intent, tools_used or [], rating)
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    @staticmethod
    def _hash_user_id(user_id: str) -> str:
        """Hash a user ID for privacy."""
        if not user_id:
            return "anonymous"
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]
    
    @staticmethod
    def _hash_query(query: str) -> str:
        """Hash a query for pattern matching."""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    @staticmethod
    def _hash_text(text: str) -> str:
        """Hash arbitrary text."""
        return hashlib.md5(text.encode()).hexdigest()[:16]
    
    @staticmethod
    def _query_to_pattern(query: str) -> str:
        """Normalize a query to a reusable pattern."""
        q = query.lower().strip()
        # Replace specific locations with placeholder
        q = re.sub(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', '<LOC>', q)
        # Replace numbers
        q = re.sub(r'\d+', '<N>', q)
        # Replace prices
        q = re.sub(r'rs\.?\s*<N>\s*(lakh|crore|k|million)?', '<PRICE>', q)
        return q[:200]
    
    # -------------------------------------------------------------------------
    # Statistics and Admin
    # -------------------------------------------------------------------------
    
    def get_stats(self) -> Dict:
        """Get enhanced learning statistics."""
        conn = self._get_conn()
        if not conn:
            return {}
        
        try:
            stats = {}
            
            # Collective learnings
            row = conn.execute(
                "SELECT COUNT(*), SUM(sample_count), AVG(success_rate) FROM collective_learnings"
            ).fetchone()
            stats["collective_learnings"] = {
                "pattern_count": row[0],
                "total_samples": row[1] or 0,
                "avg_success_rate": round(row[2] or 0, 3)
            }
            
            # Query clusters
            row = conn.execute(
                "SELECT COUNT(*), SUM(member_count) FROM query_clusters"
            ).fetchone()
            stats["clusters"] = {
                "cluster_count": row[0],
                "total_members": row[1] or 0
            }
            
            # Failure patterns
            row = conn.execute(
                "SELECT COUNT(*), SUM(failure_count) FROM failure_patterns"
            ).fetchone()
            stats["failures"] = {
                "pattern_count": row[0],
                "total_failures": row[1] or 0
            }
            
            # A/B experiments
            row = conn.execute(
                "SELECT COUNT(*) FROM ab_experiments WHERE status = 'running'"
            ).fetchone()
            stats["ab_experiments"] = {
                "running": row[0]
            }
            
            # Entity corrections
            row = conn.execute(
                "SELECT COUNT(*), SUM(correction_count) FROM entity_corrections"
            ).fetchone()
            stats["entity_corrections"] = {
                "unique_corrections": row[0],
                "total_corrections": row[1] or 0
            }
            
            # User sessions
            row = conn.execute("SELECT COUNT(*) FROM user_sessions").fetchone()
            stats["users"] = {
                "unique_users": row[0]
            }
            
            # Improvement trend (last 7 days)
            trends = self.get_improvement_trend(days=7)
            stats["improvement_trend"] = trends
            
            return stats
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Get stats failed: {e}")
            return {}
    
    def get_discovered_intents_report(self) -> Dict:
        """Get a report of discovered intent patterns."""
        patterns = self.discover_new_intent_patterns()
        
        return {
            "discovered_patterns": patterns,
            "total_patterns": len(patterns),
            "recommendations": [
                {
                    "pattern": p["query_pattern"],
                    "suggested_action": f"Add as new intent: {p['suggested_intent']}"
                }
                for p in patterns[:5]
            ]
        }
    
    def reset(self):
        """Reset all learned data (admin action)."""
        conn = self._get_conn()
        if not conn:
            return
        
        try:
            tables = [
                "collective_learnings", "query_clusters", "cluster_members",
                "failure_patterns", "improvement_history", "ab_experiments",
                "ab_outcomes", "entity_corrections", "query_rewrites",
                "low_confidence_queries", "user_sessions"
            ]
            for table in tables:
                conn.execute(f"DELETE FROM {table}")
            conn.commit()
            
            # Clear caches
            self._collective_cache.clear()
            self._failure_cache.clear()
            self._cluster_cache.clear()
            self._ab_assignments.clear()
            
            logger.info("[EnhancedLearning] All data reset")
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Reset failed: {e}")
    
    def export_learnings(self) -> Dict:
        """Export all learnings for backup or analysis."""
        conn = self._get_conn()
        if not conn:
            return {}
        
        try:
            export = {}
            
            # Export collective learnings
            rows = conn.execute("SELECT * FROM collective_learnings").fetchall()
            export["collective_learnings"] = [dict(row) for row in rows]
            
            # Export clusters
            rows = conn.execute("SELECT * FROM query_clusters").fetchall()
            export["clusters"] = [dict(row) for row in rows]
            
            # Export failure patterns
            rows = conn.execute("SELECT * FROM failure_patterns").fetchall()
            export["failures"] = [dict(row) for row in rows]
            
            # Export entity corrections
            rows = conn.execute("SELECT * FROM entity_corrections").fetchall()
            export["corrections"] = [dict(row) for row in rows]
            
            return export
        except Exception as e:
            logger.debug(f"[EnhancedLearning] Export failed: {e}")
            return {}


# =============================================================================
# Singleton Instance
# =============================================================================

_engine: Optional[EnhancedLearningEngine] = None


def get_enhanced_learning_engine() -> EnhancedLearningEngine:
    """Get or create the enhanced learning engine singleton."""
    global _engine
    if _engine is None:
        _engine = EnhancedLearningEngine()
    return _engine


# =============================================================================
# Integration Helpers
# =============================================================================

def integrate_with_self_learning():
    """
    Integrate enhanced learning with existing SelfLearningEngine.
    
    Call this at startup to link the two engines.
    """
    try:
        from ai.self_learning import get_self_learning_engine
        base_engine = get_self_learning_engine()
        enhanced = get_enhanced_learning_engine()
        enhanced.set_base_engine(base_engine)
        logger.info("[EnhancedLearning] Integrated with SelfLearningEngine")
    except ImportError:
        logger.info("[EnhancedLearning] SelfLearningEngine not available, running standalone")


def record_chat_event(query: str, intent: str, tools_used: List[str],
                     success: bool, latency_ms: int, rating: int = None,
                     user_id: str = None, session_id: str = None,
                     confidence: float = 1.0):
    """
    Convenience function to record a chat event.
    
    Use this from chat_routes.py or other handlers.
    """
    engine = get_enhanced_learning_engine()
    event = LearningEvent(
        event_type="success" if success else "failure",
        query=query,
        intent=intent,
        tools_used=tools_used,
        outcome={},
        user_rating=rating,
        latency_ms=latency_ms,
        user_id=user_id,
        session_id=session_id,
        confidence=confidence
    )
    engine.record_learning_event(event)


# =============================================================================
# CLI Interface for Testing
# =============================================================================

if __name__ == "__main__":
    import sys
    
    engine = get_enhanced_learning_engine()
    
    print("Enhanced Learning Engine - CLI")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "stats":
            stats = engine.get_stats()
            print(json.dumps(stats, indent=2))
        
        elif cmd == "discover":
            patterns = engine.discover_new_intent_patterns()
            print(json.dumps(patterns, indent=2))
        
        elif cmd == "trend":
            trend = engine.get_improvement_trend()
            print(json.dumps(trend, indent=2))
        
        elif cmd == "reset":
            engine.reset()
            print("All data reset.")
        
        else:
            print(f"Unknown command: {cmd}")
            print("Available commands: stats, discover, trend, reset")
    else:
        # Interactive test
        print("\nRecording test events...")
        
        # Test success event
        event = LearningEvent(
            event_type="success",
            query="What is the price trend in Whitefield?",
            intent="price_trend",
            tools_used=["get_locality_data", "calculate_trend"],
            outcome={"result": "upward"},
            latency_ms=250,
            confidence=0.95
        )
        engine.record_learning_event(event)
        print("✓ Recorded success event")
        
        # Test failure event
        event = LearningEvent(
            event_type="failure",
            query="Compare areas near me",
            intent="comparison",
            tools_used=["get_nearby_areas"],
            outcome={"error": "Location not found"},
            latency_ms=5000,
            error_type="timeout",
            confidence=0.4
        )
        engine.record_learning_event(event)
        print("✓ Recorded failure event")
        
        # Test feedback
        engine.record_feedback(
            query="Show me properties in Koramangala",
            intent="property_search",
            rating=4,
            feedback="Good results",
            tools_used=["search_properties"],
            confidence=0.85
        )
        print("✓ Recorded feedback")
        
        # Test entity correction
        engine.learn_entity_correction(
            original="koramangala",
            corrected="Koramangala, Bangalore",
            entity_type="location",
            query_context="Show me properties in koramangala"
        )
        print("✓ Recorded entity correction")
        
        # Get stats
        stats = engine.get_stats()
        print(f"\nStats: {json.dumps(stats, indent=2)}")
        
        # Get recommendations
        rec = engine.get_collective_recommendations("price_trend")
        print(f"\nRecommendations for price_trend: {rec}")
        
        # Get failure avoidance
        avoid = engine.get_failure_avoidance("Compare areas near me", "comparison")
        print(f"\nFailure avoidance: {avoid}")
