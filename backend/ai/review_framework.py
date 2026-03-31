"""
Valora AI - Human-in-the-Loop Review Framework
Manages review queue for v2 section analysis pipeline results that need human verification.
"""

import json
import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional

logger = logging.getLogger("valora.review_framework")

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "storage", "database", "review_queue.db"
)


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"
    AUTO_APPROVED = "AUTO_APPROVED"


@dataclass
class ReviewItem:
    review_id: str
    timestamp: float
    query: str
    lat: float
    lng: float
    pipeline_result: Dict[str, Any]
    status: ReviewStatus
    flag_reasons: List[str]
    reviewer_notes: Optional[str] = None
    reviewed_at: Optional[float] = None
    confidence_score: float = 0.0
    contradictions: List[Dict[str, Any]] = field(default_factory=list)


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS review_items (
    review_id TEXT PRIMARY KEY,
    timestamp REAL NOT NULL,
    query TEXT,
    lat REAL, lng REAL,
    pipeline_result TEXT,
    status TEXT DEFAULT 'PENDING',
    flag_reasons TEXT,
    reviewer_notes TEXT,
    reviewed_at REAL,
    confidence_score REAL,
    contradictions TEXT
);
CREATE INDEX IF NOT EXISTS idx_review_status ON review_items(status);
CREATE INDEX IF NOT EXISTS idx_review_timestamp ON review_items(timestamp);
"""


class ReviewQueue:
    """Manages the human review queue backed by SQLite."""

    def __init__(self, db_path: str = None):
        self._db_path = db_path or DB_PATH
        self._ensure_db()

    def _ensure_db(self):
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.executescript(_SCHEMA_SQL)
            conn.commit()
            logger.info(f"Review queue DB initialized at {self._db_path}")
        finally:
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_item(self, row: sqlite3.Row) -> ReviewItem:
        return ReviewItem(
            review_id=row["review_id"],
            timestamp=row["timestamp"],
            query=row["query"],
            lat=row["lat"],
            lng=row["lng"],
            pipeline_result=json.loads(row["pipeline_result"]) if row["pipeline_result"] else {},
            status=ReviewStatus(row["status"]),
            flag_reasons=json.loads(row["flag_reasons"]) if row["flag_reasons"] else [],
            reviewer_notes=row["reviewer_notes"],
            reviewed_at=row["reviewed_at"],
            confidence_score=row["confidence_score"] or 0.0,
            contradictions=json.loads(row["contradictions"]) if row["contradictions"] else [],
        )

    def flag_for_review(
        self,
        query: str,
        lat: float,
        lng: float,
        pipeline_result: Dict[str, Any],
        contradictions: List[Dict[str, Any]],
        confidence: float,
    ) -> Optional[ReviewItem]:
        """Auto-flag items meeting criteria for human review. Returns the item if flagged, None otherwise."""
        flag_reasons = self._evaluate_flag_criteria(pipeline_result, contradictions, confidence)
        if not flag_reasons:
            return None

        review_id = uuid.uuid4().hex[:12]
        now = time.time()

        item = ReviewItem(
            review_id=review_id,
            timestamp=now,
            query=query,
            lat=lat,
            lng=lng,
            pipeline_result=pipeline_result,
            status=ReviewStatus.PENDING,
            flag_reasons=flag_reasons,
            confidence_score=confidence,
            contradictions=contradictions,
        )

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO review_items
                   (review_id, timestamp, query, lat, lng, pipeline_result, status,
                    flag_reasons, reviewer_notes, reviewed_at, confidence_score, contradictions)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.review_id,
                    item.timestamp,
                    item.query,
                    item.lat,
                    item.lng,
                    json.dumps(item.pipeline_result, default=str),
                    item.status.value,
                    json.dumps(item.flag_reasons),
                    item.reviewer_notes,
                    item.reviewed_at,
                    item.confidence_score,
                    json.dumps(item.contradictions),
                ),
            )
            conn.commit()
            logger.info(f"Flagged review {review_id} for query='{query[:50]}' reasons={flag_reasons}")
        finally:
            conn.close()

        return item

    def _evaluate_flag_criteria(
        self,
        pipeline_result: Dict[str, Any],
        contradictions: List[Dict[str, Any]],
        confidence: float,
    ) -> List[str]:
        reasons = []

        if confidence < 0.6:
            reasons.append(f"low_confidence:{confidence:.2f}")

        has_contradictions = len(contradictions) > 0
        if has_contradictions and confidence < 0.8:
            reasons.append(f"contradictions_with_confidence:{confidence:.2f}")

        validation = pipeline_result.get("validation", {})
        low_conf_sections = validation.get("low_confidence_sections", [])
        if len(low_conf_sections) > 2:
            reasons.append(f"too_many_low_confidence_sections:{len(low_conf_sections)}")

        return reasons

    def get_pending_reviews(self, limit: int = 20) -> List[ReviewItem]:
        """Get items pending review, oldest first."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM review_items WHERE status = 'PENDING' ORDER BY timestamp ASC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._row_to_item(r) for r in rows]
        finally:
            conn.close()

    def approve_review(self, review_id: str, reviewer_notes: Optional[str] = None) -> bool:
        """Mark a review item as approved."""
        return self._update_status(review_id, ReviewStatus.APPROVED, reviewer_notes)

    def reject_review(self, review_id: str, reviewer_notes: Optional[str] = None) -> bool:
        """Mark a review item as rejected (pipeline result discarded)."""
        return self._update_status(review_id, ReviewStatus.REJECTED, reviewer_notes)

    def modify_review(
        self, review_id: str, modified_result: Dict[str, Any], reviewer_notes: str
    ) -> bool:
        """Store a modified pipeline result and mark as MODIFIED."""
        conn = self._get_conn()
        try:
            now = time.time()
            cursor = conn.execute(
                """UPDATE review_items
                   SET status = ?, pipeline_result = ?, reviewer_notes = ?, reviewed_at = ?
                   WHERE review_id = ?""",
                (
                    ReviewStatus.MODIFIED.value,
                    json.dumps(modified_result, default=str),
                    reviewer_notes,
                    now,
                    review_id,
                ),
            )
            if cursor.rowcount == 0:
                logger.warning(f"modify_review: review_id={review_id} not found")
                return False
            conn.commit()
            logger.info(f"Review {review_id} modified and approved")
            return True
        finally:
            conn.close()

    def auto_approve_stale(self, hours: int = 48) -> int:
        """Auto-approve items that have been pending longer than the given hours. Returns count updated."""
        cutoff = time.time() - (hours * 3600)
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """UPDATE review_items
                   SET status = ?, reviewed_at = ?, reviewer_notes = 'auto-approved: stale'
                   WHERE status = 'PENDING' AND timestamp < ?""",
                (ReviewStatus.AUTO_APPROVED.value, time.time(), cutoff),
            )
            conn.commit()
            count = cursor.rowcount
            if count > 0:
                logger.info(f"Auto-approved {count} stale review items (>{hours}h)")
            return count
        finally:
            conn.close()

    def get_review_stats(self) -> Dict[str, int]:
        """Get counts grouped by status."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM review_items GROUP BY status"
            ).fetchall()
            stats = {row["status"]: row["cnt"] for row in rows}
            stats["TOTAL"] = sum(stats.values())
            return stats
        finally:
            conn.close()

    def _update_status(
        self, review_id: str, status: ReviewStatus, reviewer_notes: Optional[str]
    ) -> bool:
        conn = self._get_conn()
        try:
            now = time.time()
            cursor = conn.execute(
                """UPDATE review_items
                   SET status = ?, reviewed_at = ?, reviewer_notes = COALESCE(?, reviewer_notes)
                   WHERE review_id = ?""",
                (status.value, now, reviewer_notes, review_id),
            )
            if cursor.rowcount == 0:
                logger.warning(f"_update_status: review_id={review_id} not found")
                return False
            conn.commit()
            logger.info(f"Review {review_id} status updated to {status.value}")
            return True
        finally:
            conn.close()


# =============================================================================
# Singleton
# =============================================================================

_review_queue_instance: Optional[ReviewQueue] = None


def get_review_queue() -> ReviewQueue:
    """Get the singleton review queue instance."""
    global _review_queue_instance
    if _review_queue_instance is None:
        _review_queue_instance = ReviewQueue()
    return _review_queue_instance


# =============================================================================
# Integration helper
# =============================================================================

def check_and_flag_review(
    query: str, lat: float, lng: float, v2_result: Dict[str, Any]
) -> bool:
    """
    Takes a v2 pipeline result, extracts confidence and contradictions,
    and flags it for review if criteria are met.

    Returns True if the item was flagged for review.
    """
    validation = v2_result.get("validation", {})
    confidence = validation.get("confidence", 1.0)
    contradictions = validation.get("contradictions", [])

    queue = get_review_queue()
    item = queue.flag_for_review(
        query=query,
        lat=lat,
        lng=lng,
        pipeline_result=v2_result,
        contradictions=contradictions,
        confidence=confidence,
    )
    return item is not None
