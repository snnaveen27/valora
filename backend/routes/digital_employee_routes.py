"""
Digital Employee API Routes

Primary prefix:
- /api/digital-employee

Compatibility prefixes:
- /api/automations
- /api/leads
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth.user_auth import User
from routes.auth_routes import require_auth
from services.digital_employee_service import get_digital_employee_service
from services.scheduler_service import get_digital_scheduler


router = APIRouter(prefix="/api/digital-employee", tags=["digital-employee"])
automations_router = APIRouter(prefix="/api/automations", tags=["digital-employee"])
leads_router = APIRouter(prefix="/api/leads", tags=["digital-employee"])


class AlertCreateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    criteria: Dict[str, Any]
    frequency: str = "instant"
    channels: List[str] = Field(default_factory=lambda: ["in_app"])


class AlertUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    criteria: Optional[Dict[str, Any]] = None
    frequency: Optional[str] = None
    channels: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ScheduledTaskCreateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    task_type: str
    schedule: Dict[str, Any]
    payload: Dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: Optional[bool] = None


class ScheduledTaskUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    task_type: Optional[str] = None
    schedule: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    requires_confirmation: Optional[bool] = None
    is_active: Optional[bool] = None


class LeadCreateRequest(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = "manual"
    status: Optional[str] = "new"
    notes: Optional[str] = None


class LeadUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    last_contact_at: Optional[float] = None


class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)


class AutomationEmailRequest(BaseModel):
    recipient_email: str
    locality: Optional[str] = None
    day_of_week: int = Field(default=0, ge=0, le=6)
    time: str = Field(default="09:00")
    requires_confirmation: bool = False


def _get_service_and_tier(user: User):
    service = get_digital_employee_service()
    tier = service.resolve_tier(user.tier.value if user and user.tier else "free", user.email)
    return service, tier


def _translate_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@router.get("/summary")
async def get_digital_employee_summary(user: User = Depends(require_auth)):
    service, tier = _get_service_and_tier(user)
    return {
        "success": True,
        "summary": service.get_dashboard_snapshot(user_id=user.email, tier=tier),
    }


@router.get("/alerts")
async def list_alerts(
    include_inactive: bool = Query(False),
    user: User = Depends(require_auth),
):
    service, _ = _get_service_and_tier(user)
    return {"success": True, "alerts": service.list_alerts(user.email, include_inactive=include_inactive)}


@router.post("/alerts")
async def create_alert(request: AlertCreateRequest, user: User = Depends(require_auth)):
    service, tier = _get_service_and_tier(user)
    try:
        alert = service.create_alert(user_id=user.email, tier=tier, payload=request.model_dump())
        return {"success": True, "alert": alert}
    except Exception as exc:
        raise _translate_exception(exc)


@router.put("/alerts/{alert_id}")
async def update_alert(alert_id: int, request: AlertUpdateRequest, user: User = Depends(require_auth)):
    service, tier = _get_service_and_tier(user)
    try:
        alert = service.update_alert(
            user_id=user.email,
            tier=tier,
            alert_id=alert_id,
            payload=request.model_dump(exclude_none=True),
        )
        return {"success": True, "alert": alert}
    except Exception as exc:
        raise _translate_exception(exc)


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, user: User = Depends(require_auth)):
    service, _ = _get_service_and_tier(user)
    try:
        service.delete_alert(user_id=user.email, alert_id=alert_id)
        return {"success": True}
    except Exception as exc:
        raise _translate_exception(exc)


@router.get("/scheduled-tasks")
async def list_scheduled_tasks(
    include_inactive: bool = Query(False),
    user: User = Depends(require_auth),
):
    service, _ = _get_service_and_tier(user)
    tasks = service.list_scheduled_tasks(user.email, include_inactive=include_inactive)
    return {"success": True, "tasks": tasks}


@router.post("/scheduled-tasks")
async def create_scheduled_task(request: ScheduledTaskCreateRequest, user: User = Depends(require_auth)):
    service, tier = _get_service_and_tier(user)
    try:
        task = service.create_scheduled_task(user_id=user.email, tier=tier, payload=request.model_dump())
        return {"success": True, "task": task}
    except Exception as exc:
        raise _translate_exception(exc)


@router.put("/scheduled-tasks/{task_id}")
async def update_scheduled_task(task_id: int, request: ScheduledTaskUpdateRequest, user: User = Depends(require_auth)):
    service, tier = _get_service_and_tier(user)
    try:
        task = service.update_scheduled_task(
            user_id=user.email,
            tier=tier,
            task_id=task_id,
            payload=request.model_dump(exclude_none=True),
        )
        return {"success": True, "task": task}
    except Exception as exc:
        raise _translate_exception(exc)


@router.delete("/scheduled-tasks/{task_id}")
async def delete_scheduled_task(task_id: int, user: User = Depends(require_auth)):
    service, _ = _get_service_and_tier(user)
    try:
        service.delete_scheduled_task(user_id=user.email, task_id=task_id)
        return {"success": True}
    except Exception as exc:
        raise _translate_exception(exc)


@router.get("/leads")
async def list_leads(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    user: User = Depends(require_auth),
):
    service, _ = _get_service_and_tier(user)
    return {"success": True, "leads": service.list_leads(user.email, status=status, limit=limit)}


@router.post("/leads")
async def create_lead(request: LeadCreateRequest, user: User = Depends(require_auth)):
    service, _ = _get_service_and_tier(user)
    try:
        lead = service.create_lead(user_id=user.email, payload=request.model_dump())
        return {"success": True, "lead": lead}
    except Exception as exc:
        raise _translate_exception(exc)


@router.put("/leads/{lead_id}")
async def update_lead(lead_id: int, request: LeadUpdateRequest, user: User = Depends(require_auth)):
    service, _ = _get_service_and_tier(user)
    try:
        lead = service.update_lead(user_id=user.email, lead_id=lead_id, payload=request.model_dump(exclude_none=True))
        return {"success": True, "lead": lead}
    except Exception as exc:
        raise _translate_exception(exc)


@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: int, user: User = Depends(require_auth)):
    service, _ = _get_service_and_tier(user)
    try:
        service.delete_lead(user_id=user.email, lead_id=lead_id)
        return {"success": True}
    except Exception as exc:
        raise _translate_exception(exc)


@router.get("/activity")
async def list_activity(
    limit: int = Query(default=100, ge=1, le=500),
    entity_type: Optional[str] = Query(default=None),
    user: User = Depends(require_auth),
):
    service, _ = _get_service_and_tier(user)
    activity = service.list_activity(user_id=user.email, limit=limit, entity_type=entity_type)
    return {"success": True, "activity": activity}


@router.post("/commands/parse")
async def parse_command(request: CommandRequest, user: User = Depends(require_auth)):
    service, _ = _get_service_and_tier(user)
    parsed = service.parse_command(request.command)
    return {"success": True, "parsed": parsed}


@router.post("/commands/parse-and-execute")
async def parse_and_execute_command(request: CommandRequest, user: User = Depends(require_auth)):
    service, tier = _get_service_and_tier(user)
    result = service.parse_and_execute_command(user_id=user.email, tier=tier, command=request.command)
    return {"success": True, **result}


@router.get("/scheduler/status")
async def scheduler_status(user: User = Depends(require_auth)):
    scheduler = get_digital_scheduler()
    return {"success": True, "scheduler": scheduler.status()}


@router.post("/scheduler/run-once")
async def scheduler_run_once(user: User = Depends(require_auth)):
    scheduler = get_digital_scheduler()
    metrics = await scheduler.run_once()
    return {"success": True, "metrics": metrics}


# -------------------------------------------------------------------------
# Compatibility endpoints
# -------------------------------------------------------------------------
@automations_router.get("/alerts")
async def list_automation_alerts(
    include_inactive: bool = Query(False),
    user: User = Depends(require_auth),
):
    return await list_alerts(include_inactive=include_inactive, user=user)


@automations_router.post("/alerts")
async def create_automation_alert(request: AlertCreateRequest, user: User = Depends(require_auth)):
    return await create_alert(request=request, user=user)


@automations_router.get("/schedule")
async def list_automation_schedule(
    include_inactive: bool = Query(False),
    user: User = Depends(require_auth),
):
    return await list_scheduled_tasks(include_inactive=include_inactive, user=user)


@automations_router.post("/schedule")
async def create_automation_schedule(request: ScheduledTaskCreateRequest, user: User = Depends(require_auth)):
    return await create_scheduled_task(request=request, user=user)


@automations_router.post("/emails")
async def create_automation_email(request: AutomationEmailRequest, user: User = Depends(require_auth)):
    service, tier = _get_service_and_tier(user)
    payload = {
        "name": f"Weekly Market Report - {request.locality or 'Default Area'}",
        "task_type": "weekly_market_report",
        "schedule": {
            "type": "weekly",
            "day_of_week": request.day_of_week,
            "time": request.time,
        },
        "payload": {
            "recipient_email": request.recipient_email,
            "locality": request.locality,
            "channels": ["email", "in_app"],
        },
        "requires_confirmation": request.requires_confirmation,
    }
    try:
        task = service.create_scheduled_task(user_id=user.email, tier=tier, payload=payload)
        return {"success": True, "task": task}
    except Exception as exc:
        raise _translate_exception(exc)


@leads_router.get("")
async def list_leads_compat(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    user: User = Depends(require_auth),
):
    return await list_leads(status=status, limit=limit, user=user)


@leads_router.post("")
async def create_leads_compat(request: LeadCreateRequest, user: User = Depends(require_auth)):
    return await create_lead(request=request, user=user)


@leads_router.put("/{lead_id}")
async def update_leads_compat(lead_id: int, request: LeadUpdateRequest, user: User = Depends(require_auth)):
    return await update_lead(lead_id=lead_id, request=request, user=user)


@leads_router.delete("/{lead_id}")
async def delete_leads_compat(lead_id: int, user: User = Depends(require_auth)):
    return await delete_lead(lead_id=lead_id, user=user)
