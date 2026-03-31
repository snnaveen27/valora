"""
Valora AI - Feature Drift Detector
Detects when computed features drift significantly from their historical baselines,
which could indicate data quality issues or environmental changes in the v2 pipeline.
"""

import json
import logging
import math
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("valora.drift_detector")

_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "database")
_DB_PATH = os.path.join(_DB_DIR, "feature_drift.db")

_LOCK = threading.Lock()
_INSTANCE: Optional["DriftDetector"] = None

_EMA_ALPHA = 0.3
_WARNING_THRESHOLD = 30.0
_CRITICAL_THRESHOLD = 50.0
_MIN_SAMPLES = 5


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FeatureSnapshot:
    timestamp: float
    lat: float
    lng: float
    section_name: str
    features: Dict[str, Any]


@dataclass
class DriftAlert:
    timestamp: float
    section_name: str
    feature_name: str
    baseline_value: Any
    current_value: Any
    drift_magnitude: float
    severity: str
    message: str


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------

class DriftDetector:
    """SQLite-backed drift detection for v2 section analysis features."""

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
                    CREATE TABLE IF NOT EXISTS feature_baselines (
                        key TEXT PRIMARY KEY,
                        section_name TEXT,
                        feature_name TEXT,
                        baseline_value REAL,
                        sample_count INTEGER DEFAULT 1,
                        last_updated REAL,
                        std_dev REAL DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS drift_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        section_name TEXT,
                        feature_name TEXT,
                        baseline_value REAL,
                        current_value REAL,
                        drift_magnitude REAL,
                        severity TEXT,
                        message TEXT,
                        acknowledged INTEGER DEFAULT 0
                    );

                    CREATE INDEX IF NOT EXISTS idx_baselines_section
                        ON feature_baselines(section_name);
                    CREATE INDEX IF NOT EXISTS idx_alerts_ts
                        ON drift_alerts(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_alerts_section
                        ON drift_alerts(section_name);
                    CREATE INDEX IF NOT EXISTS idx_alerts_severity
                        ON drift_alerts(severity);
                """)
        except Exception:
            logger.exception("[DriftDetector] Failed to initialise DB")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _round_coord(value: float) -> float:
        return round(value, 2)

    @staticmethod
    def _make_key(lat: float, lng: float, section_name: str, feature_name: str) -> str:
        lat_r = round(lat, 2)
        lng_r = round(lng, 2)
        return f"{lat_r}:{lng_r}:{section_name}:{feature_name}"

    @staticmethod
    def _is_numeric(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float)):
            return True
        return False

    # ------------------------------------------------------------------
    # Record features
    # ------------------------------------------------------------------

    def record_features(
        self,
        lat: float,
        lng: float,
        section_name: str,
        features: Dict[str, Any],
    ) -> None:
        """Record a feature computation and update baselines via EMA."""
        try:
            now = time.time()
            with _LOCK, sqlite3.connect(self._db_path) as conn:
                for feature_name, value in features.items():
                    if not self._is_numeric(value):
                        continue

                    numeric_val = float(value)
                    key = self._make_key(lat, lng, section_name, feature_name)

                    row = conn.execute(
                        "SELECT baseline_value, sample_count, std_dev FROM feature_baselines WHERE key = ?",
                        (key,),
                    ).fetchone()

                    if row is None:
                        conn.execute(
                            """
                            INSERT INTO feature_baselines
                                (key, section_name, feature_name, baseline_value, sample_count, last_updated, std_dev)
                            VALUES (?, ?, ?, ?, 1, ?, 0)
                            """,
                            (key, section_name, feature_name, numeric_val, now),
                        )
                    else:
                        old_baseline, sample_count, old_std = row
                        new_count = sample_count + 1

                        # Exponential moving average
                        new_baseline = _EMA_ALPHA * numeric_val + (1 - _EMA_ALPHA) * old_baseline

                        # Running standard deviation (Welford-style via EMA of squared diff)
                        diff = numeric_val - old_baseline
                        new_std = math.sqrt(
                            _EMA_ALPHA * diff * diff + (1 - _EMA_ALPHA) * old_std * old_std
                        )

                        conn.execute(
                            """
                            UPDATE feature_baselines
                            SET baseline_value = ?, sample_count = ?, last_updated = ?, std_dev = ?
                            WHERE key = ?
                            """,
                            (new_baseline, new_count, now, new_std, key),
                        )
        except Exception:
            logger.exception("[DriftDetector] record_features failed")

    # ------------------------------------------------------------------
    # Check drift
    # ------------------------------------------------------------------

    def check_drift(
        self,
        lat: float,
        lng: float,
        section_name: str,
        features: Dict[str, Any],
    ) -> List[DriftAlert]:
        """Compare current features against baselines and return alerts."""
        alerts: List[DriftAlert] = []
        try:
            now = time.time()
            with _LOCK, sqlite3.connect(self._db_path) as conn:
                for feature_name, value in features.items():
                    if not self._is_numeric(value):
                        continue

                    numeric_val = float(value)
                    key = self._make_key(lat, lng, section_name, feature_name)

                    row = conn.execute(
                        "SELECT baseline_value, sample_count FROM feature_baselines WHERE key = ?",
                        (key,),
                    ).fetchone()

                    if row is None:
                        continue

                    baseline, sample_count = row

                    if sample_count < _MIN_SAMPLES:
                        continue

                    denominator = max(abs(baseline), 1.0)
                    drift_magnitude = abs(numeric_val - baseline) / denominator * 100.0

                    severity = None
                    if drift_magnitude > _CRITICAL_THRESHOLD:
                        severity = "CRITICAL"
                    elif drift_magnitude > _WARNING_THRESHOLD:
                        severity = "WARNING"

                    if severity is None:
                        continue

                    message = (
                        f"{section_name}/{feature_name} drifted {drift_magnitude:.1f}% "
                        f"(baseline={baseline:.4f}, current={numeric_val:.4f})"
                    )

                    alert = DriftAlert(
                        timestamp=now,
                        section_name=section_name,
                        feature_name=feature_name,
                        baseline_value=baseline,
                        current_value=numeric_val,
                        drift_magnitude=drift_magnitude,
                        severity=severity,
                        message=message,
                    )
                    alerts.append(alert)

                    conn.execute(
                        """
                        INSERT INTO drift_alerts
                            (timestamp, section_name, feature_name, baseline_value,
                             current_value, drift_magnitude, severity, message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            now,
                            section_name,
                            feature_name,
                            baseline,
                            numeric_val,
                            drift_magnitude,
                            severity,
                            message,
                        ),
                    )
        except Exception:
            logger.exception("[DriftDetector] check_drift failed")
        return alerts

    # ------------------------------------------------------------------
    # Baselines
    # ------------------------------------------------------------------

    def get_baselines(
        self,
        lat: float,
        lng: float,
        section_name: str,
    ) -> Dict[str, Any]:
        """Get current baselines for a location/section."""
        baselines: Dict[str, Any] = {}
        try:
            lat_r = round(lat, 2)
            lng_r = round(lng, 2)
            prefix = f"{lat_r}:{lng_r}:{section_name}:"

            with _LOCK, sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT feature_name, baseline_value, sample_count, std_dev
                    FROM feature_baselines
                    WHERE key LIKE ?
                    """,
                    (prefix + "%",),
                ).fetchall()

                for feature_name, baseline_value, sample_count, std_dev in rows:
                    baselines[feature_name] = {
                        "baseline_value": baseline_value,
                        "sample_count": sample_count,
                        "std_dev": std_dev,
                    }
        except Exception:
            logger.exception("[DriftDetector] get_baselines failed")
        return baselines

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def get_recent_alerts(
        self,
        hours: int = 24,
        severity: Optional[str] = None,
    ) -> List[DriftAlert]:
        """Get recent drift alerts within the given time window."""
        alerts: List[DriftAlert] = []
        try:
            cutoff = time.time() - hours * 3600
            with _LOCK, sqlite3.connect(self._db_path) as conn:
                if severity:
                    rows = conn.execute(
                        """
                        SELECT timestamp, section_name, feature_name,
                               baseline_value, current_value, drift_magnitude,
                               severity, message
                        FROM drift_alerts
                        WHERE timestamp >= ? AND severity = ?
                        ORDER BY timestamp DESC
                        """,
                        (cutoff, severity),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT timestamp, section_name, feature_name,
                               baseline_value, current_value, drift_magnitude,
                               severity, message
                        FROM drift_alerts
                        WHERE timestamp >= ?
                        ORDER BY timestamp DESC
                        """,
                        (cutoff,),
                    ).fetchall()

                for row in rows:
                    alerts.append(DriftAlert(
                        timestamp=row[0],
                        section_name=row[1],
                        feature_name=row[2],
                        baseline_value=row[3],
                        current_value=row[4],
                        drift_magnitude=row[5],
                        severity=row[6],
                        message=row[7],
                    ))
        except Exception:
            logger.exception("[DriftDetector] get_recent_alerts failed")
        return alerts

    def acknowledge_alert(self, alert_id: int) -> None:
        """Mark an alert as acknowledged."""
        try:
            with _LOCK, sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "UPDATE drift_alerts SET acknowledged = 1 WHERE id = ?",
                    (alert_id,),
                )
        except Exception:
            logger.exception("[DriftDetector] acknowledge_alert failed")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_drift_summary(self, hours: int = 168) -> Dict[str, Any]:
        """Get weekly drift summary (default 168h = 7 days)."""
        summary: Dict[str, Any] = {
            "total_alerts": 0,
            "by_severity": {"WARNING": 0, "CRITICAL": 0},
            "by_section": {},
            "window_hours": hours,
        }
        try:
            cutoff = time.time() - hours * 3600
            with _LOCK, sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT severity, section_name, COUNT(*)
                    FROM drift_alerts
                    WHERE timestamp >= ?
                    GROUP BY severity, section_name
                    """,
                    (cutoff,),
                ).fetchall()

                for severity, section_name, count in rows:
                    summary["total_alerts"] += count
                    if severity in summary["by_severity"]:
                        summary["by_severity"][severity] += count
                    if section_name not in summary["by_section"]:
                        summary["by_section"][section_name] = {"WARNING": 0, "CRITICAL": 0}
                    if severity in summary["by_section"][section_name]:
                        summary["by_section"][section_name][severity] += count
        except Exception:
            logger.exception("[DriftDetector] get_drift_summary failed")
        return summary


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

def get_drift_detector() -> DriftDetector:
    """Return the module-level singleton DriftDetector instance."""
    global _INSTANCE
    if _INSTANCE is None:
        with _LOCK:
            if _INSTANCE is None:
                _INSTANCE = DriftDetector()
    return _INSTANCE


# ---------------------------------------------------------------------------
# Integration helper
# ---------------------------------------------------------------------------

def check_section_drift(
    lat: float,
    lng: float,
    section_name: str,
    features: Dict[str, Any],
) -> List[DriftAlert]:
    """Convenience function: record features and check for drift in one call."""
    detector = get_drift_detector()
    detector.record_features(lat, lng, section_name, features)
    return detector.check_drift(lat, lng, section_name, features)
