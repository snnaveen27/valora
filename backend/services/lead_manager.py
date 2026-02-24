"""
Lead Manager

Thin wrapper around DigitalEmployeeService lead APIs.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

from services.digital_employee_service import get_digital_employee_service


class LeadManager:
    def __init__(self):
        self._service = get_digital_employee_service()

    def list(self, user_id: str, status: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        return self._service.list_leads(user_id=user_id, status=status, limit=limit)

    def create(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._service.create_lead(user_id=user_id, payload=payload)

    def update(self, user_id: str, lead_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._service.update_lead(user_id=user_id, lead_id=lead_id, payload=payload)

    def archive(self, user_id: str, lead_id: int) -> None:
        self._service.delete_lead(user_id=user_id, lead_id=lead_id)


_lead_manager: LeadManager | None = None


def get_lead_manager() -> LeadManager:
    global _lead_manager
    if _lead_manager is None:
        _lead_manager = LeadManager()
    return _lead_manager

