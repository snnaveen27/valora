"""
Digital Employee Scheduler Service

Lightweight in-process scheduler that periodically:
- Scans property alerts
- Executes due scheduled tasks
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from services.digital_employee_service import get_digital_employee_service

logger = logging.getLogger("valora.digital_scheduler")


class DigitalEmployeeScheduler:
    _instance: "DigitalEmployeeScheduler | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self.poll_interval_seconds = max(10, int(os.getenv("DIGITAL_EMPLOYEE_SCHEDULER_INTERVAL", "30")))
        self.last_cycle_metrics: Dict[str, Any] = {}

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="digital_employee_scheduler")
        logger.info("[DigitalScheduler] Started (interval=%ss)", self.poll_interval_seconds)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("[DigitalScheduler] Stopped")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                self.last_cycle_metrics = await self.run_once()
            except Exception:
                logger.exception("[DigitalScheduler] Cycle failed")
            await asyncio.sleep(self.poll_interval_seconds)

    async def run_once(self) -> Dict[str, Any]:
        service = get_digital_employee_service()
        alert_metrics = service.run_alert_scan_cycle()
        task_metrics = service.run_scheduled_tasks_cycle()
        metrics = {
            "alerts": alert_metrics,
            "scheduled_tasks": task_metrics,
        }
        logger.debug("[DigitalScheduler] Cycle metrics: %s", metrics)
        return metrics

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "poll_interval_seconds": self.poll_interval_seconds,
            "last_cycle_metrics": self.last_cycle_metrics,
        }


_scheduler: Optional[DigitalEmployeeScheduler] = None


def get_digital_scheduler() -> DigitalEmployeeScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = DigitalEmployeeScheduler()
    return _scheduler

