"""
Notification Service

Currently supports in-app notifications by writing to automation activity log.
"""

from __future__ import annotations

from typing import Dict, Any

from services.digital_employee_service import get_digital_employee_service


class NotificationService:
    def __init__(self):
        self._service = get_digital_employee_service()

    def notify(self, user_id: str, action: str, details: Dict[str, Any]) -> None:
        self._service._log_activity(  # Internal helper is used to keep one audit stream.
            user_id=user_id,
            entity_type="notification",
            entity_id=None,
            action=action,
            details=details,
            status="success",
        )


_notification_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service

