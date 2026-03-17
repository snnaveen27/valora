"""
Digital Employee Service

Production-oriented automation backend for:
- Property alerts
- Scheduled tasks
- Lead management
- Automation activity/audit logs
- Lightweight command parsing + execution
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import config
from core.sqlite_pool import get_pool
from database.query_service import get_query_service

logger = logging.getLogger("valora.digital_employee")


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS property_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',
    name TEXT NOT NULL,
    criteria_json TEXT NOT NULL,
    frequency TEXT NOT NULL DEFAULT 'instant',
    channels_json TEXT NOT NULL DEFAULT '["in_app"]',
    is_active INTEGER NOT NULL DEFAULT 1,
    last_checked_at REAL,
    last_triggered_at REAL,
    last_match_fingerprint TEXT,
    trigger_count INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',
    name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    schedule_json TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    requires_confirmation INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    next_run_at REAL,
    last_run_at REAL,
    run_count INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    source TEXT DEFAULT 'manual',
    status TEXT NOT NULL DEFAULT 'new',
    notes TEXT,
    last_contact_at REAL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS automation_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    action TEXT NOT NULL,
    details_json TEXT,
    status TEXT NOT NULL DEFAULT 'success',
    error_message TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS automation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheduled_task_id INTEGER NOT NULL,
    run_key TEXT NOT NULL UNIQUE,
    started_at REAL NOT NULL,
    finished_at REAL,
    status TEXT NOT NULL DEFAULT 'running',
    summary TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS runtime_execution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    command_text TEXT NOT NULL,
    intent TEXT,
    runtime_requested TEXT NOT NULL DEFAULT 'native',
    runtime_selected TEXT NOT NULL DEFAULT 'native',
    fallback_used INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'success',
    error_message TEXT,
    latency_ms INTEGER,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS social_message_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    recipient TEXT NOT NULL,
    template_key TEXT,
    content_text TEXT NOT NULL,
    variables_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'draft',
    runtime_selected TEXT NOT NULL DEFAULT 'native',
    created_at REAL NOT NULL,
    confirmed_at REAL,
    sent_at REAL,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_alerts_user ON property_alerts(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_alerts_schedule ON property_alerts(is_active, frequency, last_checked_at);
CREATE INDEX IF NOT EXISTS idx_tasks_user ON scheduled_tasks(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_tasks_next_run ON scheduled_tasks(is_active, next_run_at);
CREATE INDEX IF NOT EXISTS idx_leads_user ON leads(user_id, status);
CREATE INDEX IF NOT EXISTS idx_activity_user ON automation_activity(user_id, created_at);
"""


@dataclass
class TierPolicy:
    max_alerts: Optional[int]
    max_scheduled_tasks: Optional[int]
    allow_email: bool
    auto_execute_tasks: bool
    instant_alert_interval_seconds: int
    max_daily_alert_notifications: Optional[int]


class DigitalEmployeeService:
    """Core digital employee service with SQLite-backed state."""

    TIER_POLICIES: Dict[str, TierPolicy] = {
        "free": TierPolicy(
            max_alerts=3,
            max_scheduled_tasks=5,
            allow_email=False,
            auto_execute_tasks=False,
            instant_alert_interval_seconds=3600,
            max_daily_alert_notifications=5,
        ),
        "pro": TierPolicy(
            max_alerts=None,
            max_scheduled_tasks=None,
            allow_email=True,
            auto_execute_tasks=True,
            instant_alert_interval_seconds=900,
            max_daily_alert_notifications=None,
        ),
    }

    ALERT_FREQUENCIES = {"instant", "daily", "weekly"}
    TASK_TYPES = {
        "property_alert_scan",
        "weekly_market_report",
        "lead_follow_up",
        "custom_task",
    }
    LEAD_STATUSES = {"new", "qualified", "contacted", "negotiating", "closed", "lost", "archived"}

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = config.DB_PATH.parent / "digital_employee.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._pool = get_pool("digital_employee", str(self.db_path), _SCHEMA_SQL)
        self._query_service = get_query_service()
        logger.info("[DigitalEmployee] Service initialized with DB: %s", self.db_path)

    # ---------------------------------------------------------------------
    # Tier and normalization helpers
    # ---------------------------------------------------------------------
    def resolve_tier(self, user_tier: Optional[str], user_id: str) -> str:
        normalized = (user_tier or "free").strip().lower()
        if normalized == "admin":
            normalized = "pro"

        try:
            from ai.unified_credits import get_credits_manager

            credits_tier = (get_credits_manager().get_or_create_user(user_id).get("tier") or "free").lower()
            if credits_tier == "pro":
                normalized = "pro"
        except Exception:
            pass

        return normalized if normalized in self.TIER_POLICIES else "free"

    def _tier_policy(self, tier: str) -> TierPolicy:
        return self.TIER_POLICIES.get(tier, self.TIER_POLICIES["free"])

    @staticmethod
    def _now() -> float:
        return time.time()

    @staticmethod
    def _json_load(value: Optional[str], default: Any) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except Exception:
            return default

    @staticmethod
    def _normalize_channels(channels: Optional[List[str]]) -> List[str]:
        if not channels:
            return ["in_app"]
        normalized = []
        for channel in channels:
            c = str(channel).strip().lower()
            if c in {"in_app", "email"} and c not in normalized:
                normalized.append(c)
        return normalized or ["in_app"]

    @staticmethod
    def _parse_price_to_inr(raw: Optional[str]) -> Optional[int]:
        if not raw:
            return None
        text = raw.lower().replace(",", "").strip()
        m = re.search(r"(\d+(?:\.\d+)?)\s*(cr|crore|l|lac|lakh)?", text)
        if not m:
            return None
        value = float(m.group(1))
        unit = (m.group(2) or "").strip()
        if unit in {"cr", "crore"}:
            return int(value * 10_000_000)
        if unit in {"l", "lac", "lakh"}:
            return int(value * 100_000)
        if value < 10_000:
            return int(value * 100_000)
        return int(value)

    def _normalize_alert_criteria(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}

        locality = str(criteria.get("locality", "")).strip()
        if locality:
            normalized["locality"] = locality

        bhk = criteria.get("bhk")
        if bhk is not None:
            try:
                bhk_int = int(bhk)
                if bhk_int > 0:
                    normalized["bhk"] = bhk_int
            except (TypeError, ValueError):
                pass

        property_type = str(criteria.get("property_type", "")).strip().lower()
        if property_type:
            normalized["property_type"] = property_type

        listing_type = str(criteria.get("listing_type", "sale")).strip().lower()
        if listing_type in {"sale", "rent"}:
            normalized["listing_type"] = listing_type
        else:
            normalized["listing_type"] = "sale"

        max_price = criteria.get("max_price")
        if max_price is None:
            max_price = criteria.get("max_price_inr")
        if max_price is None and criteria.get("max_price_lakh") is not None:
            try:
                max_price = int(float(criteria["max_price_lakh"]) * 100_000)
            except (TypeError, ValueError):
                max_price = None

        if max_price is not None:
            try:
                max_price_int = int(max_price)
                if max_price_int > 0:
                    normalized["max_price"] = max_price_int
            except (TypeError, ValueError):
                pass

        min_price = criteria.get("min_price")
        if min_price is not None:
            try:
                min_price_int = int(min_price)
                if min_price_int > 0:
                    normalized["min_price"] = min_price_int
            except (TypeError, ValueError):
                pass

        return normalized

    @staticmethod
    def _normalize_schedule(schedule: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(schedule, dict):
            raise ValueError("schedule must be an object")

        schedule_type = str(schedule.get("type", "interval")).strip().lower()
        if schedule_type not in {"interval", "daily", "weekly"}:
            raise ValueError("schedule.type must be one of interval/daily/weekly")

        normalized: Dict[str, Any] = {"type": schedule_type}

        if schedule_type == "interval":
            minutes = int(schedule.get("minutes", 60))
            minutes = max(5, min(minutes, 44_640))
            normalized["minutes"] = minutes
            return normalized

        time_value = str(schedule.get("time", "09:00")).strip()
        if not re.match(r"^\d{2}:\d{2}$", time_value):
            raise ValueError("schedule.time must be HH:MM")
        hh, mm = time_value.split(":")
        h_int = int(hh)
        m_int = int(mm)
        if not (0 <= h_int <= 23 and 0 <= m_int <= 59):
            raise ValueError("schedule.time out of range")
        normalized["time"] = f"{h_int:02d}:{m_int:02d}"

        if schedule_type == "weekly":
            day_of_week = int(schedule.get("day_of_week", 1))
            if day_of_week < 0 or day_of_week > 6:
                raise ValueError("schedule.day_of_week must be 0..6")
            normalized["day_of_week"] = day_of_week

        return normalized

    @staticmethod
    def _next_run_at(schedule: Dict[str, Any], now_ts: Optional[float] = None) -> float:
        now_ts = now_ts or time.time()
        now = datetime.fromtimestamp(now_ts)
        schedule_type = schedule["type"]

        if schedule_type == "interval":
            minutes = int(schedule.get("minutes", 60))
            return now_ts + (minutes * 60)

        hh, mm = schedule["time"].split(":")
        target = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)

        if schedule_type == "daily":
            if target <= now:
                target = target + timedelta(days=1)
            return target.timestamp()

        day_of_week = int(schedule.get("day_of_week", 1))
        days_ahead = (day_of_week - now.weekday()) % 7
        if days_ahead == 0 and target <= now:
            days_ahead = 7
        target = target + timedelta(days=days_ahead)
        return target.timestamp()

    def _alert_scan_interval_seconds(self, frequency: str, tier: str) -> int:
        if frequency == "daily":
            return 24 * 3600
        if frequency == "weekly":
            return 7 * 24 * 3600
        return self._tier_policy(tier).instant_alert_interval_seconds

    def _free_alert_notifications_exceeded(self, user_id: str, now_ts: float) -> bool:
        policy = self._tier_policy("free")
        if policy.max_daily_alert_notifications is None:
            return False
        since = now_ts - (24 * 3600)
        conn = self._pool.get()
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM automation_activity
            WHERE user_id = ? AND action = 'alert_triggered'
              AND status = 'success'
              AND created_at >= ?
            """,
            (user_id, since),
        ).fetchone()
        count = int((row["cnt"] if row else 0) or 0)
        return count >= policy.max_daily_alert_notifications

    def _log_activity(
        self,
        user_id: str,
        entity_type: str,
        entity_id: Optional[str],
        action: str,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        created_at: Optional[float] = None,
    ) -> None:
        conn = self._pool.get()
        conn.execute(
            """
            INSERT INTO automation_activity
            (user_id, entity_type, entity_id, action, details_json, status, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                entity_type,
                entity_id,
                action,
                json.dumps(details or {}, separators=(",", ":")),
                status,
                error_message,
                created_at or self._now(),
            ),
        )
        conn.commit()

    # ---------------------------------------------------------------------
    # Property alerts
    # ---------------------------------------------------------------------
    def list_alerts(self, user_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        conn = self._pool.get()
        query = """
            SELECT *
            FROM property_alerts
            WHERE user_id = ?
        """
        params: List[Any] = [user_id]
        if not include_inactive:
            query += " AND is_active = 1"
        query += " ORDER BY created_at DESC"

        rows = conn.execute(query, tuple(params)).fetchall()
        return [self._serialize_alert_row(r) for r in rows]

    def get_alert(self, user_id: str, alert_id: int) -> Optional[Dict[str, Any]]:
        conn = self._pool.get()
        row = conn.execute(
            "SELECT * FROM property_alerts WHERE id = ? AND user_id = ?",
            (alert_id, user_id),
        ).fetchone()
        return self._serialize_alert_row(row) if row else None

    def create_alert(self, user_id: str, tier: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        policy = self._tier_policy(tier)
        conn = self._pool.get()

        if policy.max_alerts is not None:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM property_alerts WHERE user_id = ? AND is_active = 1",
                (user_id,),
            ).fetchone()
            active_count = int((row["cnt"] if row else 0) or 0)
            if active_count >= policy.max_alerts:
                raise PermissionError(f"{tier.title()} tier allows up to {policy.max_alerts} active alerts.")

        raw_criteria = payload.get("criteria")
        if not isinstance(raw_criteria, dict):
            raise ValueError("criteria is required and must be an object")
        criteria = self._normalize_alert_criteria(raw_criteria)
        if not criteria:
            raise ValueError("criteria is empty after normalization")

        frequency = str(payload.get("frequency", "instant")).strip().lower()
        if frequency not in self.ALERT_FREQUENCIES:
            raise ValueError("frequency must be one of instant/daily/weekly")

        channels = self._normalize_channels(payload.get("channels"))
        if "email" in channels and not policy.allow_email:
            raise PermissionError("Email alerts are available on Pro tier only.")

        name = str(payload.get("name", "")).strip()
        if not name:
            location_hint = criteria.get("locality") or "Custom Alert"
            name = f"Alert: {location_hint}"
        name = name[:120]

        now_ts = self._now()
        cur = conn.execute(
            """
            INSERT INTO property_alerts
            (user_id, tier, name, criteria_json, frequency, channels_json, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                user_id,
                tier,
                name,
                json.dumps(criteria, separators=(",", ":")),
                frequency,
                json.dumps(channels, separators=(",", ":")),
                now_ts,
                now_ts,
            ),
        )
        conn.commit()

        alert_id = int(cur.lastrowid)
        self._log_activity(
            user_id=user_id,
            entity_type="alert",
            entity_id=str(alert_id),
            action="alert_created",
            details={"name": name, "frequency": frequency, "channels": channels, "criteria": criteria},
        )
        alert = self.get_alert(user_id, alert_id)
        if alert is None:
            raise RuntimeError("alert creation failed")
        return alert

    def update_alert(self, user_id: str, tier: str, alert_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get_alert(user_id, alert_id)
        if not existing:
            raise KeyError("alert not found")

        policy = self._tier_policy(tier)
        updates: Dict[str, Any] = {}

        if "name" in payload:
            updates["name"] = str(payload["name"] or "").strip()[:120] or existing["name"]

        if "frequency" in payload:
            frequency = str(payload["frequency"]).strip().lower()
            if frequency not in self.ALERT_FREQUENCIES:
                raise ValueError("frequency must be one of instant/daily/weekly")
            updates["frequency"] = frequency

        if "channels" in payload:
            channels = self._normalize_channels(payload.get("channels"))
            if "email" in channels and not policy.allow_email:
                raise PermissionError("Email alerts are available on Pro tier only.")
            updates["channels_json"] = json.dumps(channels, separators=(",", ":"))

        if "criteria" in payload:
            criteria = self._normalize_alert_criteria(payload.get("criteria") or {})
            if not criteria:
                raise ValueError("criteria is empty after normalization")
            updates["criteria_json"] = json.dumps(criteria, separators=(",", ":"))

        if "is_active" in payload:
            updates["is_active"] = 1 if bool(payload["is_active"]) else 0

        if not updates:
            return existing

        updates["updated_at"] = self._now()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [alert_id, user_id]

        conn = self._pool.get()
        conn.execute(
            f"UPDATE property_alerts SET {set_clause} WHERE id = ? AND user_id = ?",
            tuple(values),
        )
        conn.commit()

        self._log_activity(
            user_id=user_id,
            entity_type="alert",
            entity_id=str(alert_id),
            action="alert_updated",
            details={"fields": list(updates.keys())},
        )
        updated = self.get_alert(user_id, alert_id)
        if updated is None:
            raise RuntimeError("alert update failed")
        return updated

    def delete_alert(self, user_id: str, alert_id: int) -> None:
        conn = self._pool.get()
        cur = conn.execute(
            "UPDATE property_alerts SET is_active = 0, updated_at = ? WHERE id = ? AND user_id = ?",
            (self._now(), alert_id, user_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise KeyError("alert not found")

        self._log_activity(
            user_id=user_id,
            entity_type="alert",
            entity_id=str(alert_id),
            action="alert_deactivated",
        )

    def _serialize_alert_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": int(row["id"]),
            "user_id": row["user_id"],
            "tier": row["tier"],
            "name": row["name"],
            "criteria": self._json_load(row["criteria_json"], {}),
            "frequency": row["frequency"],
            "channels": self._json_load(row["channels_json"], ["in_app"]),
            "is_active": bool(row["is_active"]),
            "last_checked_at": row["last_checked_at"],
            "last_triggered_at": row["last_triggered_at"],
            "trigger_count": int(row["trigger_count"] or 0),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ---------------------------------------------------------------------
    # Scheduled tasks
    # ---------------------------------------------------------------------
    def list_scheduled_tasks(self, user_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        conn = self._pool.get()
        query = "SELECT * FROM scheduled_tasks WHERE user_id = ?"
        params: List[Any] = [user_id]
        if not include_inactive:
            query += " AND is_active = 1"
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, tuple(params)).fetchall()
        return [self._serialize_task_row(r) for r in rows]

    def get_scheduled_task(self, user_id: str, task_id: int) -> Optional[Dict[str, Any]]:
        conn = self._pool.get()
        row = conn.execute(
            "SELECT * FROM scheduled_tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        ).fetchone()
        return self._serialize_task_row(row) if row else None

    def create_scheduled_task(self, user_id: str, tier: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        policy = self._tier_policy(tier)
        conn = self._pool.get()

        if policy.max_scheduled_tasks is not None:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM scheduled_tasks WHERE user_id = ? AND is_active = 1",
                (user_id,),
            ).fetchone()
            active_count = int((row["cnt"] if row else 0) or 0)
            if active_count >= policy.max_scheduled_tasks:
                raise PermissionError(
                    f"{tier.title()} tier allows up to {policy.max_scheduled_tasks} active scheduled tasks."
                )

        task_type = str(payload.get("task_type", "")).strip().lower()
        if task_type not in self.TASK_TYPES:
            raise ValueError(f"task_type must be one of: {', '.join(sorted(self.TASK_TYPES))}")

        name = str(payload.get("name", "")).strip()[:120]
        if not name:
            name = f"{task_type.replace('_', ' ').title()} Task"

        schedule = self._normalize_schedule(payload.get("schedule") or {})
        task_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
        channels = self._normalize_channels(task_payload.get("channels"))
        if "email" in channels and not policy.allow_email:
            raise PermissionError("Email task delivery is available on Pro tier only.")
        task_payload["channels"] = channels

        requires_confirmation = bool(payload.get("requires_confirmation", not policy.auto_execute_tasks))
        next_run_at = self._next_run_at(schedule)
        now_ts = self._now()

        cur = conn.execute(
            """
            INSERT INTO scheduled_tasks
            (user_id, tier, name, task_type, schedule_json, payload_json, requires_confirmation,
             is_active, next_run_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                user_id,
                tier,
                name,
                task_type,
                json.dumps(schedule, separators=(",", ":")),
                json.dumps(task_payload, separators=(",", ":")),
                1 if requires_confirmation else 0,
                next_run_at,
                now_ts,
                now_ts,
            ),
        )
        conn.commit()

        task_id = int(cur.lastrowid)
        self._log_activity(
            user_id=user_id,
            entity_type="scheduled_task",
            entity_id=str(task_id),
            action="scheduled_task_created",
            details={
                "name": name,
                "task_type": task_type,
                "schedule": schedule,
                "requires_confirmation": requires_confirmation,
            },
        )
        task = self.get_scheduled_task(user_id, task_id)
        if task is None:
            raise RuntimeError("scheduled task creation failed")
        return task

    def update_scheduled_task(self, user_id: str, tier: str, task_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get_scheduled_task(user_id, task_id)
        if not existing:
            raise KeyError("scheduled task not found")

        policy = self._tier_policy(tier)
        updates: Dict[str, Any] = {}

        if "name" in payload:
            updates["name"] = str(payload.get("name") or "").strip()[:120] or existing["name"]

        if "task_type" in payload:
            task_type = str(payload["task_type"]).strip().lower()
            if task_type not in self.TASK_TYPES:
                raise ValueError(f"task_type must be one of: {', '.join(sorted(self.TASK_TYPES))}")
            updates["task_type"] = task_type

        if "schedule" in payload:
            schedule = self._normalize_schedule(payload.get("schedule") or {})
            updates["schedule_json"] = json.dumps(schedule, separators=(",", ":"))
            updates["next_run_at"] = self._next_run_at(schedule)

        if "payload" in payload:
            task_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
            channels = self._normalize_channels(task_payload.get("channels"))
            if "email" in channels and not policy.allow_email:
                raise PermissionError("Email task delivery is available on Pro tier only.")
            task_payload["channels"] = channels
            updates["payload_json"] = json.dumps(task_payload, separators=(",", ":"))

        if "requires_confirmation" in payload:
            updates["requires_confirmation"] = 1 if bool(payload["requires_confirmation"]) else 0

        if "is_active" in payload:
            updates["is_active"] = 1 if bool(payload["is_active"]) else 0

        if not updates:
            return existing

        updates["updated_at"] = self._now()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [task_id, user_id]

        conn = self._pool.get()
        conn.execute(
            f"UPDATE scheduled_tasks SET {set_clause} WHERE id = ? AND user_id = ?",
            tuple(values),
        )
        conn.commit()

        self._log_activity(
            user_id=user_id,
            entity_type="scheduled_task",
            entity_id=str(task_id),
            action="scheduled_task_updated",
            details={"fields": list(updates.keys())},
        )
        updated = self.get_scheduled_task(user_id, task_id)
        if updated is None:
            raise RuntimeError("scheduled task update failed")
        return updated

    def delete_scheduled_task(self, user_id: str, task_id: int) -> None:
        conn = self._pool.get()
        cur = conn.execute(
            "UPDATE scheduled_tasks SET is_active = 0, updated_at = ? WHERE id = ? AND user_id = ?",
            (self._now(), task_id, user_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise KeyError("scheduled task not found")

        self._log_activity(
            user_id=user_id,
            entity_type="scheduled_task",
            entity_id=str(task_id),
            action="scheduled_task_deactivated",
        )

    def _serialize_task_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": int(row["id"]),
            "user_id": row["user_id"],
            "tier": row["tier"],
            "name": row["name"],
            "task_type": row["task_type"],
            "schedule": self._json_load(row["schedule_json"], {}),
            "payload": self._json_load(row["payload_json"], {}),
            "requires_confirmation": bool(row["requires_confirmation"]),
            "is_active": bool(row["is_active"]),
            "next_run_at": row["next_run_at"],
            "last_run_at": row["last_run_at"],
            "run_count": int(row["run_count"] or 0),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ---------------------------------------------------------------------
    # Leads
    # ---------------------------------------------------------------------
    def list_leads(self, user_id: str, status: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        conn = self._pool.get()
        query = "SELECT * FROM leads WHERE user_id = ?"
        params: List[Any] = [user_id]
        if status:
            normalized_status = status.strip().lower()
            query += " AND status = ?"
            params.append(normalized_status)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(max(1, min(limit, 500)))
        rows = conn.execute(query, tuple(params)).fetchall()
        return [self._serialize_lead_row(r) for r in rows]

    def get_lead(self, user_id: str, lead_id: int) -> Optional[Dict[str, Any]]:
        conn = self._pool.get()
        row = conn.execute(
            "SELECT * FROM leads WHERE id = ? AND user_id = ?",
            (lead_id, user_id),
        ).fetchone()
        return self._serialize_lead_row(row) if row else None

    def create_lead(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        full_name = str(payload.get("full_name", "")).strip()
        if not full_name:
            raise ValueError("full_name is required")

        email = str(payload.get("email", "")).strip().lower() or None
        phone = str(payload.get("phone", "")).strip() or None
        source = str(payload.get("source", "manual")).strip().lower() or "manual"
        status = str(payload.get("status", "new")).strip().lower() or "new"
        if status not in self.LEAD_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(self.LEAD_STATUSES))}")

        notes = str(payload.get("notes", "")).strip() or None
        now_ts = self._now()

        conn = self._pool.get()
        cur = conn.execute(
            """
            INSERT INTO leads (user_id, full_name, email, phone, source, status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, full_name[:120], email, phone, source[:60], status, notes, now_ts, now_ts),
        )
        conn.commit()

        lead_id = int(cur.lastrowid)
        self._log_activity(
            user_id=user_id,
            entity_type="lead",
            entity_id=str(lead_id),
            action="lead_created",
            details={"full_name": full_name, "status": status, "source": source},
        )
        lead = self.get_lead(user_id, lead_id)
        if lead is None:
            raise RuntimeError("lead creation failed")
        return lead

    def update_lead(self, user_id: str, lead_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get_lead(user_id, lead_id)
        if not existing:
            raise KeyError("lead not found")

        updates: Dict[str, Any] = {}
        if "full_name" in payload:
            full_name = str(payload.get("full_name") or "").strip()
            if not full_name:
                raise ValueError("full_name cannot be empty")
            updates["full_name"] = full_name[:120]
        if "email" in payload:
            updates["email"] = str(payload.get("email") or "").strip().lower() or None
        if "phone" in payload:
            updates["phone"] = str(payload.get("phone") or "").strip() or None
        if "source" in payload:
            updates["source"] = str(payload.get("source") or "manual").strip().lower()[:60]
        if "status" in payload:
            status = str(payload.get("status") or "").strip().lower()
            if status not in self.LEAD_STATUSES:
                raise ValueError(f"status must be one of: {', '.join(sorted(self.LEAD_STATUSES))}")
            updates["status"] = status
        if "notes" in payload:
            updates["notes"] = str(payload.get("notes") or "").strip() or None
        if "last_contact_at" in payload:
            last_contact = payload.get("last_contact_at")
            if last_contact is not None:
                try:
                    updates["last_contact_at"] = float(last_contact)
                except (TypeError, ValueError):
                    raise ValueError("last_contact_at must be unix timestamp")

        if not updates:
            return existing

        updates["updated_at"] = self._now()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [lead_id, user_id]

        conn = self._pool.get()
        conn.execute(f"UPDATE leads SET {set_clause} WHERE id = ? AND user_id = ?", tuple(values))
        conn.commit()

        self._log_activity(
            user_id=user_id,
            entity_type="lead",
            entity_id=str(lead_id),
            action="lead_updated",
            details={"fields": list(updates.keys())},
        )
        updated = self.get_lead(user_id, lead_id)
        if updated is None:
            raise RuntimeError("lead update failed")
        return updated

    def delete_lead(self, user_id: str, lead_id: int) -> None:
        conn = self._pool.get()
        cur = conn.execute(
            "UPDATE leads SET status = 'archived', updated_at = ? WHERE id = ? AND user_id = ?",
            (self._now(), lead_id, user_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise KeyError("lead not found")
        self._log_activity(
            user_id=user_id,
            entity_type="lead",
            entity_id=str(lead_id),
            action="lead_archived",
        )

    @staticmethod
    def _serialize_lead_row(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": int(row["id"]),
            "user_id": row["user_id"],
            "full_name": row["full_name"],
            "email": row["email"],
            "phone": row["phone"],
            "source": row["source"],
            "status": row["status"],
            "notes": row["notes"],
            "last_contact_at": row["last_contact_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ---------------------------------------------------------------------
    # Activity + dashboard
    # ---------------------------------------------------------------------
    def list_activity(
        self,
        user_id: str,
        limit: int = 100,
        entity_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conn = self._pool.get()
        query = "SELECT * FROM automation_activity WHERE user_id = ?"
        params: List[Any] = [user_id]
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(1, min(limit, 500)))

        rows = conn.execute(query, tuple(params)).fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "id": int(row["id"]),
                    "user_id": row["user_id"],
                    "entity_type": row["entity_type"],
                    "entity_id": row["entity_id"],
                    "action": row["action"],
                    "details": self._json_load(row["details_json"], {}),
                    "status": row["status"],
                    "error_message": row["error_message"],
                    "created_at": row["created_at"],
                }
            )
        return result

    def get_dashboard_snapshot(self, user_id: str, tier: str) -> Dict[str, Any]:
        conn = self._pool.get()
        alerts_count_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM property_alerts WHERE user_id = ? AND is_active = 1",
            (user_id,),
        ).fetchone()
        tasks_count_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM scheduled_tasks WHERE user_id = ? AND is_active = 1",
            (user_id,),
        ).fetchone()
        leads_count_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM leads WHERE user_id = ? AND status != 'archived'",
            (user_id,),
        ).fetchone()

        upcoming_rows = conn.execute(
            """
            SELECT id, name, task_type, next_run_at
            FROM scheduled_tasks
            WHERE user_id = ? AND is_active = 1 AND next_run_at IS NOT NULL
            ORDER BY next_run_at ASC
            LIMIT 5
            """,
            (user_id,),
        ).fetchall()

        policy = self._tier_policy(tier)
        return {
            "tier": tier,
            "policy": {
                "max_alerts": policy.max_alerts,
                "max_scheduled_tasks": policy.max_scheduled_tasks,
                "allow_email": policy.allow_email,
                "auto_execute_tasks": policy.auto_execute_tasks,
            },
            "counts": {
                "active_alerts": int((alerts_count_row["cnt"] if alerts_count_row else 0) or 0),
                "active_scheduled_tasks": int((tasks_count_row["cnt"] if tasks_count_row else 0) or 0),
                "active_leads": int((leads_count_row["cnt"] if leads_count_row else 0) or 0),
            },
            "upcoming_tasks": [
                {
                    "id": int(r["id"]),
                    "name": r["name"],
                    "task_type": r["task_type"],
                    "next_run_at": r["next_run_at"],
                }
                for r in upcoming_rows
            ],
            "recent_activity": self.list_activity(user_id=user_id, limit=10),
        }

    # ---------------------------------------------------------------------
    # Command parsing + execution
    # ---------------------------------------------------------------------
    def parse_command(self, command: str) -> Dict[str, Any]:
        text = (command or "").strip()
        if not text:
            return {"handled": False}
        lower = text.lower()
        def _extract_locality() -> Optional[str]:
            locality_match = re.search(
                r"\b(?:in|near|around|for|at)\s+([a-zA-Z][a-zA-Z\s]{1,40}?)(?:\s+(under|below|with|when|every|from|to|is)\b|$)",
                text,
                re.I,
            )
            if locality_match:
                return locality_match.group(1).strip().title()
            return None

        def _extract_alert_criteria() -> Dict[str, Any]:
            criteria: Dict[str, Any] = {}
            locality = _extract_locality()
            if locality:
                criteria["locality"] = locality

            bhk_match = re.search(r"(\d+)\s*bhk", lower)
            if bhk_match:
                criteria["bhk"] = int(bhk_match.group(1))

            max_price_match = re.search(r"(?:under|below|max|less than|drops below)\s*₹?\s*([\d\.,]+\s*(?:cr|crore|l|lac|lakh)?)", lower)
            if max_price_match:
                max_price = self._parse_price_to_inr(max_price_match.group(1))
                if max_price:
                    criteria["max_price"] = max_price

            min_price_match = re.search(r"(?:above|min|greater than|over)\s*₹?\s*([\d\.,]+\s*(?:cr|crore|l|lac|lakh)?)", lower)
            if min_price_match:
                min_price = self._parse_price_to_inr(min_price_match.group(1))
                if min_price:
                    criteria["min_price"] = min_price

            radius_match = re.search(r"(?:within|nearby)\s*(\d{2,5})\s*(m|meter|meters|km)", lower)
            if radius_match:
                radius_val = int(radius_match.group(1))
                unit = radius_match.group(2)
                criteria["radius_m"] = radius_val * 1000 if unit == "km" else radius_val

            if "metro" in lower:
                criteria["near_metro"] = True
            if "parking" in lower:
                criteria["has_parking"] = True
            if "new launch" in lower or "pre-launch" in lower:
                criteria["new_launch"] = True

            yield_match = re.search(r"rental yield\s*(?:exceeds|above|over|>=?)\s*(\d+(?:\.\d+)?)\s*%?", lower)
            if yield_match:
                criteria["min_rental_yield"] = float(yield_match.group(1))

            return criteria

        # -----------------------------------------------------------------
        # Read/list commands
        # -----------------------------------------------------------------
        if re.search(r"\b(show|list|view)\b.*\b(active\s+)?alerts?\b", lower) or "my alerts" in lower:
            return {"handled": True, "intent": "list_alerts", "executable": True}

        if re.search(r"\b(show|list|view)\b.*\b(leads?)\b", lower):
            return {"handled": True, "intent": "list_leads", "executable": True}

        if (
            re.search(r"\b(show|list|view)\b.*\b(scheduled tasks?|tasks?|schedule)\b", lower)
            or "what tasks do i have today" in lower
            or "today's schedule" in lower
            or "show today's schedule" in lower
        ):
            return {"handled": True, "intent": "list_scheduled_tasks", "executable": True}

        if "show recent activity" in lower or "activity feed" in lower:
            return {"handled": True, "intent": "list_activity", "executable": True}

        if (
            "pending follow-ups" in lower
            or "performance summary" in lower
            or "productivity report" in lower
            or "conversion rate" in lower
            or "how many leads this week" in lower
            or "top performing areas" in lower
            or "agent leaderboard" in lower
            or "revenue generated" in lower
            or "properties sold" in lower
        ):
            return {"handled": True, "intent": "dashboard_summary", "executable": True}

        # -----------------------------------------------------------------
        # Update/delete commands
        # -----------------------------------------------------------------
        if "pause all" in lower and "alert" in lower:
            return {"handled": True, "intent": "deactivate_all_alerts", "executable": True}

        if re.search(r"\b(delete|remove|pause|deactivate)\b.*\balert", lower):
            alert_id_match = re.search(r"\balert\s*#?(\d+)\b", lower)
            locality_hint = _extract_locality()
            return {
                "handled": True,
                "intent": "deactivate_alert",
                "executable": True,
                "payload": {
                    "alert_id": int(alert_id_match.group(1)) if alert_id_match else None,
                    "locality_hint": locality_hint,
                    "name_hint": text,
                },
            }

        if re.search(r"\b(cancel|delete|remove)\b.*\b(weekly report|scheduled task|schedule)\b", lower):
            return {"handled": True, "intent": "deactivate_weekly_report", "executable": True}

        if (
            "update lead status" in lower
            or "mark lead as" in lower
            or "set lead to" in lower
            or "convert lead to deal" in lower
            or "mark lead as not interested" in lower
        ):
            status_map = {
                "hot": "qualified",
                "qualified": "qualified",
                "contacted": "contacted",
                "negotiating": "negotiating",
                "deal": "closed",
                "closed": "closed",
                "converted": "closed",
                "not interested": "lost",
                "cold": "lost",
                "lost": "lost",
            }
            target_status = None
            for key, mapped in status_map.items():
                if key in lower:
                    target_status = mapped
                    break
            if target_status is None:
                return {
                    "handled": True,
                    "intent": "update_lead_status",
                    "executable": False,
                    "reason": "Could not infer target lead status.",
                }
            return {
                "handled": True,
                "intent": "update_lead_status",
                "executable": True,
                "payload": {"status": target_status, "lead_hint": text},
            }

        if "add notes to this lead" in lower or lower.startswith("add note") or "add notes" in lower:
            note_match = re.search(r"(?:add notes? to (?:this )?lead|add note)\s*[:\-]?\s*(.+)$", text, re.I)
            note_value = (note_match.group(1).strip() if note_match else "").strip() or "Updated via chat command."
            return {
                "handled": True,
                "intent": "add_lead_note",
                "executable": True,
                "payload": {"note": note_value, "lead_hint": text},
            }

        if re.search(r"\b(delete|remove|archive)\b.*\blead\b", lower):
            return {"handled": True, "intent": "archive_lead", "executable": True, "payload": {"lead_hint": text}}

        # -----------------------------------------------------------------
        # Create alert commands
        # -----------------------------------------------------------------
        if any(
            phrase in lower
            for phrase in [
                "alert me",
                "set up alert",
                "set up a property alert",
                "setup alert",
                "create alert",
                "notify me",
                "track price changes",
                "track this property",
                "track new launches",
                "alert when",
                "notify when",
            ]
        ) or lower.startswith("alert "):
            criteria = _extract_alert_criteria()
            if not criteria:
                return {
                    "handled": True,
                    "intent": "create_alert",
                    "executable": False,
                    "reason": "Missing usable alert criteria (location/budget/BHK).",
                }

            frequency = "instant"
            if "daily" in lower:
                frequency = "daily"
            elif "weekly" in lower:
                frequency = "weekly"

            channels = ["in_app"]
            if "email" in lower:
                channels = ["in_app", "email"]

            location_hint = criteria.get("locality", "Custom")
            return {
                "handled": True,
                "intent": "create_alert",
                "executable": True,
                "payload": {
                    "name": f"Alert: {location_hint}",
                    "frequency": frequency,
                    "criteria": criteria,
                    "channels": channels,
                },
            }

        # -----------------------------------------------------------------
        # Scheduling / reminder commands
        # -----------------------------------------------------------------
        if (
            "weekly report" in lower
            or lower.startswith("schedule")
            or lower.startswith("remind me")
            or "daily market summary" in lower
            or "monthly investment report" in lower
            or "follow up" in lower
            or "follow-up" in lower
            or "site visit" in lower
            or "monitor price trends" in lower
            or "track inventory levels" in lower
            or "monitor rental yields" in lower
            or "send weekly market report" in lower
            or "schedule email" in lower
        ):
            email_match = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", text)
            locality = _extract_locality()

            day_map = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            day = 0
            for day_name, day_idx in day_map.items():
                if day_name in lower:
                    day = day_idx
                    break

            # Default schedule = weekly Monday 09:00
            schedule: Dict[str, Any] = {"type": "weekly", "day_of_week": day, "time": "09:00"}

            time_match = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", lower)
            if time_match:
                hh = int(time_match.group(1))
                mm = int(time_match.group(2) or 0)
                ampm = time_match.group(3)
                if ampm == "pm" and hh < 12:
                    hh += 12
                if ampm == "am" and hh == 12:
                    hh = 0
                hh = max(0, min(hh, 23))
                mm = max(0, min(mm, 59))
                schedule["time"] = f"{hh:02d}:{mm:02d}"
            else:
                hhmm_match = re.search(r"\b(\d{1,2}):(\d{2})\b", lower)
                if hhmm_match:
                    hh = max(0, min(int(hhmm_match.group(1)), 23))
                    mm = max(0, min(int(hhmm_match.group(2)), 59))
                    schedule["time"] = f"{hh:02d}:{mm:02d}"

            in_days_match = re.search(r"\bin\s+(\d+)\s+days?\b", lower)
            if in_days_match:
                schedule = {"type": "interval", "minutes": max(5, int(in_days_match.group(1)) * 24 * 60)}
            elif "tomorrow" in lower:
                schedule = {"type": "interval", "minutes": 24 * 60}
            elif "next week" in lower:
                schedule = {"type": "interval", "minutes": 7 * 24 * 60}
            elif "monthly" in lower:
                schedule = {"type": "interval", "minutes": 30 * 24 * 60}
            elif "daily" in lower:
                schedule = {"type": "daily", "time": schedule.get("time", "09:00")}

            task_type = "weekly_market_report"
            task_name = "Weekly Market Report"
            task_payload: Dict[str, Any] = {
                "recipient_email": email_match.group(1).lower() if email_match else None,
                "locality": locality,
            }

            if "follow up" in lower or "follow-up" in lower:
                task_type = "lead_follow_up"
                task_name = "Lead Follow-up"
                task_payload["note"] = text
            elif "site visit" in lower:
                task_type = "custom_task"
                task_name = "Site Visit Reminder"
                task_payload["note"] = text
            elif "monthly investment report" in lower:
                task_type = "weekly_market_report"
                task_name = "Monthly Investment Report"
            elif (
                "monitor price trends" in lower
                or "track inventory levels" in lower
                or "monitor rental yields" in lower
            ):
                task_type = "weekly_market_report"
                task_name = "Market Intelligence Monitor"
                task_payload["note"] = text
            elif "daily market summary" in lower:
                task_type = "weekly_market_report"
                task_name = "Daily Market Summary"

            channels = ["in_app"]
            if email_match or "email" in lower:
                channels = ["email", "in_app"]
            task_payload["channels"] = channels

            payload = {
                "name": task_name,
                "task_type": task_type,
                "schedule": schedule,
                "payload": task_payload,
                "requires_confirmation": False,
            }
            return {
                "handled": True,
                "intent": "create_scheduled_task",
                "executable": True,
                "payload": payload,
            }

        # -----------------------------------------------------------------
        # Create lead commands
        # -----------------------------------------------------------------
        if (
            lower.startswith("add lead")
            or lower.startswith("new lead")
            or "add a lead" in lower
            or lower.startswith("create lead")
            or "create a lead" in lower
        ):
            email_match = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", text)
            phone_match = re.search(r"(\+?\d[\d\s\-]{7,}\d)", text)
            name_match = re.search(
                r"(?:add lead|new lead|add a lead|create lead|create a lead)\s*[:\-]?\s*([A-Za-z][A-Za-z\s]{1,60}?)(?:,|$|\s+\+?\d|\s+[A-Za-z0-9._%+-]+@)",
                text,
                re.I,
            )

            full_name = (name_match.group(1).strip() if name_match else "").strip() or "New Lead"
            return {
                "handled": True,
                "intent": "create_lead",
                "executable": True,
                "payload": {
                    "full_name": full_name,
                    "email": email_match.group(1).lower() if email_match else None,
                    "phone": phone_match.group(1).strip() if phone_match else None,
                    "source": "chat",
                    "status": "new",
                },
            }

        return {"handled": False}

    def parse_and_execute_command(self, user_id: str, tier: str, command: str) -> Dict[str, Any]:
        parsed = self.parse_command(command)
        if not parsed.get("handled"):
            return {"handled": False}

        if not parsed.get("executable", True):
            return {
                "handled": True,
                "executed": False,
                "intent": parsed.get("intent"),
                "reason": parsed.get("reason") or "Command recognized but not executable.",
            }

        intent = parsed.get("intent")
        payload = parsed.get("payload") or {}

        try:
            if intent == "list_alerts":
                alerts = self.list_alerts(user_id=user_id, include_inactive=False)
                return {
                    "handled": True,
                    "executed": True,
                    "intent": intent,
                    "summary": f"You have {len(alerts)} active alert(s).",
                    "entity": {"alerts": alerts[:25]},
                }

            if intent == "deactivate_all_alerts":
                alerts = self.list_alerts(user_id=user_id, include_inactive=False)
                deactivated = 0
                for alert in alerts:
                    self.delete_alert(user_id=user_id, alert_id=int(alert["id"]))
                    deactivated += 1
                return {
                    "handled": True,
                    "executed": True,
                    "intent": intent,
                    "summary": f"Paused {deactivated} alert(s).",
                }

            if intent == "deactivate_alert":
                alerts = self.list_alerts(user_id=user_id, include_inactive=False)
                target = None
                alert_id = payload.get("alert_id")
                locality_hint = str(payload.get("locality_hint") or "").strip().lower()
                name_hint = str(payload.get("name_hint") or "").strip().lower()

                if alert_id:
                    target = next((a for a in alerts if int(a["id"]) == int(alert_id)), None)
                if target is None and locality_hint:
                    target = next(
                        (
                            a for a in alerts
                            if locality_hint in str(a.get("name", "")).lower()
                            or locality_hint in str((a.get("criteria") or {}).get("locality", "")).lower()
                        ),
                        None,
                    )
                if target is None and name_hint:
                    target = next((a for a in alerts if str(a.get("name", "")).lower() in name_hint), None)
                if target is None and len(alerts) == 1:
                    target = alerts[0]
                if target is None:
                    return {
                        "handled": True,
                        "executed": False,
                        "intent": intent,
                        "reason": "Could not find a matching alert to deactivate.",
                    }
                self.delete_alert(user_id=user_id, alert_id=int(target["id"]))
                return {
                    "handled": True,
                    "executed": True,
                    "intent": intent,
                    "summary": f"Paused alert '{target['name']}'.",
                    "entity": target,
                }

            if intent == "deactivate_weekly_report":
                tasks = self.list_scheduled_tasks(user_id=user_id, include_inactive=False)
                matches = [
                    t for t in tasks
                    if t.get("task_type") == "weekly_market_report"
                    or "weekly" in str(t.get("name", "")).lower()
                    or "report" in str(t.get("name", "")).lower()
                ]
                if not matches:
                    return {
                        "handled": True,
                        "executed": False,
                        "intent": intent,
                        "reason": "No active weekly report task found.",
                    }
                for task in matches:
                    self.delete_scheduled_task(user_id=user_id, task_id=int(task["id"]))
                return {
                    "handled": True,
                    "executed": True,
                    "intent": intent,
                    "summary": f"Cancelled {len(matches)} weekly report task(s).",
                }

            if intent == "create_alert":
                created = self.create_alert(user_id=user_id, tier=tier, payload=payload)
                return {
                    "handled": True,
                    "executed": True,
                    "intent": intent,
                    "summary": f"Created alert '{created['name']}' with {created['frequency']} checks.",
                    "entity": created,
                }
            if intent == "create_scheduled_task":
                created = self.create_scheduled_task(user_id=user_id, tier=tier, payload=payload)
                return {
                    "handled": True,
                    "executed": True,
                    "intent": intent,
                    "summary": f"Scheduled task '{created['name']}' ({created['task_type']}).",
                    "entity": created,
                }

            if intent == "list_scheduled_tasks":
                tasks = self.list_scheduled_tasks(user_id=user_id, include_inactive=False)
                return {
                    "handled": True,
                    "executed": True,
                    "intent": intent,
                    "summary": f"You have {len(tasks)} active scheduled task(s).",
                    "entity": {"tasks": tasks[:25]},
                }

            if intent == "create_lead":
                created = self.create_lead(user_id=user_id, payload=payload)
                return {
                    "handled": True,
                    "executed": True,
                    "intent": intent,
                    "summary": f"Lead '{created['full_name']}' added to your pipeline.",
                    "entity": created,
                }

            if intent == "list_leads":
                leads = self.list_leads(user_id=user_id, status=None, limit=200)
                return {
                    "handled": True,
                    "executed": True,
                    "intent": intent,
                    "summary": f"You have {len(leads)} lead(s) in your pipeline.",
                    "entity": {"leads": leads[:50]},
                }

            if intent == "list_activity":
                activity = self.list_activity(user_id=user_id, limit=50)
                return {
                    "handled": True,
                    "executed": True,
                    "intent": intent,
                    "summary": f"Fetched {len(activity)} recent activity event(s).",
                    "entity": {"activity": activity},
                }

            if intent == "dashboard_summary":
                summary = self.get_dashboard_snapshot(user_id=user_id, tier=tier)
                return {
                    "handled": True,
                    "executed": True,
                    "intent": intent,
                    "summary": "Loaded your agent dashboard summary.",
                    "entity": summary,
                }

            if intent in {"update_lead_status", "add_lead_note", "archive_lead"}:
                leads = self.list_leads(user_id=user_id, status=None, limit=200)
                active_leads = [lead for lead in leads if lead.get("status") != "archived"]
                lead_hint = str(payload.get("lead_hint") or "").strip().lower()
                target = None

                lead_id = payload.get("lead_id")
                if lead_id is not None:
                    target = next((lead for lead in active_leads if int(lead["id"]) == int(lead_id)), None)
                if target is None and lead_hint:
                    target = next((lead for lead in active_leads if str(lead.get("full_name", "")).lower() in lead_hint), None)
                if target is None and active_leads:
                    target = active_leads[0]

                if target is None:
                    return {
                        "handled": True,
                        "executed": False,
                        "intent": intent,
                        "reason": "No active lead found to update.",
                    }

                if intent == "update_lead_status":
                    updated = self.update_lead(
                        user_id=user_id,
                        lead_id=int(target["id"]),
                        payload={"status": payload.get("status")},
                    )
                    return {
                        "handled": True,
                        "executed": True,
                        "intent": intent,
                        "summary": f"Lead '{updated['full_name']}' status updated to {updated['status']}.",
                        "entity": updated,
                    }

                if intent == "add_lead_note":
                    existing_notes = str(target.get("notes") or "").strip()
                    new_note = str(payload.get("note") or "").strip()
                    merged_notes = f"{existing_notes}\n{new_note}".strip() if existing_notes else new_note
                    updated = self.update_lead(
                        user_id=user_id,
                        lead_id=int(target["id"]),
                        payload={"notes": merged_notes},
                    )
                    return {
                        "handled": True,
                        "executed": True,
                        "intent": intent,
                        "summary": f"Added note to lead '{updated['full_name']}'.",
                        "entity": updated,
                    }

                self.delete_lead(user_id=user_id, lead_id=int(target["id"]))
                return {
                    "handled": True,
                    "executed": True,
                    "intent": intent,
                    "summary": f"Archived lead '{target['full_name']}'.",
                    "entity": target,
                }
        except (PermissionError, ValueError, KeyError) as exc:
            return {
                "handled": True,
                "executed": False,
                "intent": intent,
                "reason": str(exc),
            }
        except Exception as exc:
            logger.exception("[DigitalEmployee] Command execution failed")
            return {
                "handled": True,
                "executed": False,
                "intent": intent,
                "reason": f"Automation command failed: {exc}",
            }

        return {
            "handled": True,
            "executed": False,
            "intent": intent,
            "reason": "Unsupported command intent.",
        }

    # ---------------------------------------------------------------------
    # Scheduler cycles
    # ---------------------------------------------------------------------
    def run_alert_scan_cycle(self, now_ts: Optional[float] = None) -> Dict[str, int]:
        now_ts = now_ts or self._now()
        conn = self._pool.get()
        rows = conn.execute(
            "SELECT * FROM property_alerts WHERE is_active = 1 ORDER BY id ASC"
        ).fetchall()

        scanned = 0
        triggered = 0
        errors = 0

        for row in rows:
            tier = row["tier"] or "free"
            last_checked_at = row["last_checked_at"] or 0
            interval_sec = self._alert_scan_interval_seconds(row["frequency"], tier)
            if now_ts - float(last_checked_at) < interval_sec:
                continue

            scanned += 1
            try:
                if self._scan_single_alert(row=row, now_ts=now_ts):
                    triggered += 1
            except Exception as exc:
                errors += 1
                logger.exception("[DigitalEmployee] Alert scan failed for alert_id=%s", row["id"])
                self._log_activity(
                    user_id=row["user_id"],
                    entity_type="alert",
                    entity_id=str(row["id"]),
                    action="alert_scan_failed",
                    details={"error": str(exc)},
                    status="error",
                    error_message=str(exc),
                    created_at=now_ts,
                )

        return {"scanned": scanned, "triggered": triggered, "errors": errors}

    def _scan_single_alert(self, row: sqlite3.Row, now_ts: float) -> bool:
        alert_id = int(row["id"])
        user_id = row["user_id"]
        tier = row["tier"] or "free"
        criteria = self._json_load(row["criteria_json"], {})
        channels = self._json_load(row["channels_json"], ["in_app"])

        search_args: Dict[str, Any] = {"limit": 20}
        locality = criteria.get("locality")
        if locality:
            search_args["locality"] = locality
        if criteria.get("bhk") is not None:
            search_args["bhk"] = f"{int(criteria['bhk'])}BHK"
        if criteria.get("max_price") is not None:
            search_args["max_price"] = int(criteria["max_price"])
        if criteria.get("min_price") is not None:
            search_args["min_price"] = int(criteria["min_price"])
        if criteria.get("property_type"):
            search_args["property_type"] = criteria["property_type"]
        if criteria.get("listing_type"):
            search_args["listing_type"] = criteria["listing_type"]

        matches = self._query_service.search_properties(**search_args)
        top_matches = []
        for item in matches[:5]:
            top_matches.append(
                {
                    "id": item.get("property_id") or item.get("id"),
                    "title": item.get("title"),
                    "price": item.get("price"),
                    "locality": item.get("locality"),
                }
            )

        fingerprint = json.dumps(
            {"count": len(matches), "top_ids": [m["id"] for m in top_matches]},
            separators=(",", ":"),
        )
        previous_fingerprint = row["last_match_fingerprint"]

        suppressed = False
        should_trigger = bool(matches) and fingerprint != previous_fingerprint
        if should_trigger and tier == "free" and self._free_alert_notifications_exceeded(user_id, now_ts):
            suppressed = True
            should_trigger = False

        conn = self._pool.get()
        if should_trigger:
            conn.execute(
                """
                UPDATE property_alerts
                SET last_checked_at = ?, last_triggered_at = ?, last_match_fingerprint = ?,
                    trigger_count = trigger_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (now_ts, now_ts, fingerprint, now_ts, alert_id),
            )
            conn.commit()

            details = {
                "match_count": len(matches),
                "top_matches": top_matches,
                "channels": channels,
                "criteria": criteria,
            }
            self._log_activity(
                user_id=user_id,
                entity_type="alert",
                entity_id=str(alert_id),
                action="alert_triggered",
                details=details,
                created_at=now_ts,
            )

            if "email" in channels and self._tier_policy(tier).allow_email:
                try:
                    from services.email_automation import get_email_automation_service

                    email_service = get_email_automation_service()
                    summary_lines = []
                    for match in top_matches:
                        title = match.get("title") or "Property"
                        locality_txt = match.get("locality") or "Unknown area"
                        price_txt = f"₹{int(match['price']):,}" if match.get("price") else "Price unavailable"
                        summary_lines.append(f"- {title} ({locality_txt}) — {price_txt}")
                    body = (
                        f"Alert '{row['name']}' matched {len(matches)} properties.\n\n"
                        + "\n".join(summary_lines)
                    )
                    recipient = f"{user_id}"
                    email_service.send_text_email(
                        to_email=recipient,
                        subject=f"[Valora] Property alert: {row['name']}",
                        body=body,
                    )
                except Exception as exc:
                    self._log_activity(
                        user_id=user_id,
                        entity_type="alert",
                        entity_id=str(alert_id),
                        action="alert_email_failed",
                        details={"error": str(exc)},
                        status="error",
                        error_message=str(exc),
                        created_at=now_ts,
                    )
            return True

        conn.execute(
            """
            UPDATE property_alerts
            SET last_checked_at = ?, last_match_fingerprint = ?, updated_at = ?
            WHERE id = ?
            """,
            (now_ts, fingerprint, now_ts, alert_id),
        )
        conn.commit()

        if suppressed:
            self._log_activity(
                user_id=user_id,
                entity_type="alert",
                entity_id=str(alert_id),
                action="alert_suppressed",
                details={"reason": "free_tier_daily_limit"},
                status="warning",
                created_at=now_ts,
            )
        return False

    def run_scheduled_tasks_cycle(self, now_ts: Optional[float] = None) -> Dict[str, int]:
        now_ts = now_ts or self._now()
        conn = self._pool.get()
        rows = conn.execute(
            """
            SELECT *
            FROM scheduled_tasks
            WHERE is_active = 1 AND next_run_at IS NOT NULL AND next_run_at <= ?
            ORDER BY next_run_at ASC
            LIMIT 100
            """,
            (now_ts,),
        ).fetchall()

        executed = 0
        pending_confirmation = 0
        failed = 0

        for row in rows:
            result = self._execute_single_scheduled_task(row=row, now_ts=now_ts)
            status = result.get("status")
            if status == "executed":
                executed += 1
            elif status == "pending_confirmation":
                pending_confirmation += 1
            elif status == "failed":
                failed += 1

        return {
            "executed": executed,
            "pending_confirmation": pending_confirmation,
            "failed": failed,
        }

    def _execute_single_scheduled_task(self, row: sqlite3.Row, now_ts: float) -> Dict[str, Any]:
        task_id = int(row["id"])
        user_id = row["user_id"]
        tier = row["tier"] or "free"
        task_type = row["task_type"]
        requires_confirmation = bool(row["requires_confirmation"])
        schedule = self._json_load(row["schedule_json"], {"type": "interval", "minutes": 60})
        payload = self._json_load(row["payload_json"], {})
        run_key = f"{task_id}:{int(row['next_run_at'] or now_ts)}"

        conn = self._pool.get()
        try:
            conn.execute(
                """
                INSERT INTO automation_runs (scheduled_task_id, run_key, started_at, status)
                VALUES (?, ?, ?, 'running')
                """,
                (task_id, run_key, now_ts),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return {"status": "skipped_duplicate"}

        if requires_confirmation and not self._tier_policy(tier).auto_execute_tasks:
            summary = "Skipped auto-run: manual confirmation required on free tier."
            self._finish_run(run_key, "pending_confirmation", summary, None, now_ts)
            self._advance_task_schedule(task_id, schedule, now_ts, increment_run=False)
            self._log_activity(
                user_id=user_id,
                entity_type="scheduled_task",
                entity_id=str(task_id),
                action="scheduled_task_pending_confirmation",
                details={"task_type": task_type, "summary": summary},
                status="warning",
                created_at=now_ts,
            )
            return {"status": "pending_confirmation"}

        try:
            summary = self._execute_task_logic(task_type, user_id, task_id, payload, now_ts)
            self._finish_run(run_key, "success", summary, None, now_ts)
            self._advance_task_schedule(task_id, schedule, now_ts, increment_run=True)
            self._log_activity(
                user_id=user_id,
                entity_type="scheduled_task",
                entity_id=str(task_id),
                action="scheduled_task_executed",
                details={"task_type": task_type, "summary": summary},
                created_at=now_ts,
            )
            return {"status": "executed", "summary": summary}
        except Exception as exc:
            logger.exception("[DigitalEmployee] Scheduled task failed: task_id=%s", task_id)
            self._finish_run(run_key, "failed", None, str(exc), now_ts)
            self._advance_task_schedule(task_id, schedule, now_ts, increment_run=False)
            self._log_activity(
                user_id=user_id,
                entity_type="scheduled_task",
                entity_id=str(task_id),
                action="scheduled_task_failed",
                details={"task_type": task_type, "error": str(exc)},
                status="error",
                error_message=str(exc),
                created_at=now_ts,
            )
            return {"status": "failed", "error": str(exc)}

    def _finish_run(
        self,
        run_key: str,
        status: str,
        summary: Optional[str],
        error_message: Optional[str],
        now_ts: float,
    ) -> None:
        conn = self._pool.get()
        conn.execute(
            """
            UPDATE automation_runs
            SET finished_at = ?, status = ?, summary = ?, error_message = ?
            WHERE run_key = ?
            """,
            (now_ts, status, summary, error_message, run_key),
        )
        conn.commit()

    def _advance_task_schedule(self, task_id: int, schedule: Dict[str, Any], now_ts: float, increment_run: bool) -> None:
        next_run_at = self._next_run_at(schedule, now_ts=now_ts + 1)
        conn = self._pool.get()
        if increment_run:
            conn.execute(
                """
                UPDATE scheduled_tasks
                SET last_run_at = ?, next_run_at = ?, run_count = run_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (now_ts, next_run_at, now_ts, task_id),
            )
        else:
            conn.execute(
                """
                UPDATE scheduled_tasks
                SET next_run_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (next_run_at, now_ts, task_id),
            )
        conn.commit()

    def _execute_task_logic(
        self,
        task_type: str,
        user_id: str,
        task_id: int,
        payload: Dict[str, Any],
        now_ts: float,
    ) -> str:
        if task_type == "property_alert_scan":
            result = self.run_alert_scan_cycle(now_ts=now_ts)
            return f"Scanned alerts (scanned={result['scanned']}, triggered={result['triggered']})."

        if task_type == "weekly_market_report":
            locality = payload.get("locality") or "your selected area"
            recipient = payload.get("recipient_email") or user_id
            channels = payload.get("channels") or ["in_app"]
            summary = f"Prepared weekly market summary for {locality}."
            if "email" in channels:
                try:
                    from services.email_automation import get_email_automation_service

                    email_service = get_email_automation_service()
                    subject = f"[Valora] Weekly Market Report - {locality}"
                    body = (
                        f"Hello,\n\n"
                        f"Your weekly automated report for {locality} is ready.\n"
                        f"- Generated at: {datetime.fromtimestamp(now_ts).isoformat()}\n"
                        f"- Task ID: {task_id}\n\n"
                        f"Open Valora Agent tab for full activity and details.\n"
                    )
                    email_service.send_text_email(to_email=recipient, subject=subject, body=body)
                    summary += f" Email sent to {recipient}."
                except Exception as exc:
                    summary += f" Email send failed: {exc}"
            return summary

        if task_type == "lead_follow_up":
            lead_id = payload.get("lead_id")
            if lead_id is None:
                return "Lead follow-up task ran with no lead_id payload."
            conn = self._pool.get()
            conn.execute(
                """
                UPDATE leads
                SET last_contact_at = ?, status = CASE WHEN status = 'new' THEN 'contacted' ELSE status END, updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (now_ts, now_ts, int(lead_id), user_id),
            )
            conn.commit()
            return f"Lead follow-up recorded for lead_id={lead_id}."

        note = str(payload.get("note", "Custom scheduled task executed.")).strip()
        return note


_digital_employee_service: Optional[DigitalEmployeeService] = None


def get_digital_employee_service() -> DigitalEmployeeService:
    global _digital_employee_service
    if _digital_employee_service is None:
        _digital_employee_service = DigitalEmployeeService()
    return _digital_employee_service
