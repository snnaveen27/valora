"""
Error Logging API Endpoints
Provides REST API for admin error monitoring.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.error_logging import (
    get_error_service, 
    ErrorSeverity, 
    ErrorCategory,
    log_error
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/errors", tags=["Error Logs"])


class ResolveRequest(BaseModel):
    """Request to resolve an error"""
    resolved_by: Optional[str] = Field(default="admin", description="Who resolved the error")


class ResolveAllRequest(BaseModel):
    """Request to resolve all errors"""
    category: Optional[str] = Field(default=None, description="Category to filter")
    resolved_by: Optional[str] = Field(default="admin", description="Who resolved the errors")


class TestErrorRequest(BaseModel):
    """Request to create a test error"""
    message: str = Field(default="Test error", description="Error message")
    severity: str = Field(default="error", description="Severity level")
    category: str = Field(default="system", description="Error category")


@router.get("/")
async def get_errors(
    limit: int = Query(default=50, ge=1, le=500, description="Max errors to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    resolved: Optional[bool] = Query(default=None, description="Filter by resolved status"),
    hours: Optional[int] = Query(default=None, description="Only errors from last N hours"),
    search: Optional[str] = Query(default=None, description="Search in message/details")
):
    """
    Get error logs with filtering and pagination.
    """
    try:
        service = get_error_service()
        
        # Parse severity
        sev = None
        if severity:
            try:
                sev = ErrorSeverity(severity.lower())
            except ValueError:
                pass
        
        # Parse category
        cat = None
        if category:
            try:
                cat = ErrorCategory(category.lower())
            except ValueError:
                pass
        
        # Calculate since datetime
        since = None
        if hours:
            since = datetime.now() - timedelta(hours=hours)
        
        errors = service.get_errors(
            limit=limit,
            offset=offset,
            severity=sev,
            category=cat,
            resolved=resolved,
            since=since,
            search=search
        )
        
        return {
            "success": True,
            "errors": errors,
            "count": len(errors),
            "filters": {
                "severity": severity,
                "category": category,
                "resolved": resolved,
                "hours": hours,
                "search": search
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get errors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_error_statistics():
    """
    Get error statistics for dashboard.
    """
    try:
        service = get_error_service()
        stats = service.get_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_error_categories():
    """Get available error categories"""
    return {
        "categories": [
            {"value": cat.value, "label": cat.value.replace("_", " ").title()}
            for cat in ErrorCategory
        ]
    }


@router.get("/severities")
async def get_error_severities():
    """Get available error severity levels"""
    return {
        "severities": [
            {"value": sev.value, "label": sev.value.title()}
            for sev in ErrorSeverity
        ]
    }


@router.get("/{error_id}")
async def get_error_detail(error_id: str):
    """
    Get detailed information about a specific error.
    """
    try:
        service = get_error_service()
        error = service.get_error_by_id(error_id)
        
        if not error:
            raise HTTPException(status_code=404, detail="Error not found")
        
        return {
            "success": True,
            "error": error
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{error_id}/resolve")
async def resolve_error(error_id: str, request: ResolveRequest):
    """
    Mark an error as resolved.
    """
    try:
        service = get_error_service()
        success = service.resolve_error(error_id, resolved_by=request.resolved_by)
        
        if not success:
            raise HTTPException(status_code=404, detail="Error not found")
        
        return {
            "success": True,
            "message": f"Error {error_id} resolved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resolve-all")
async def resolve_all_errors(request: ResolveAllRequest):
    """
    Resolve all errors, optionally filtered by category.
    """
    try:
        service = get_error_service()
        
        cat = None
        if request.category:
            try:
                cat = ErrorCategory(request.category.lower())
            except ValueError:
                pass
        
        count = service.resolve_all(category=cat, resolved_by=request.resolved_by)
        
        return {
            "success": True,
            "resolved_count": count,
            "message": f"Resolved {count} errors"
        }
        
    except Exception as e:
        logger.error(f"Failed to resolve all errors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-resolved")
async def clear_resolved_errors():
    """
    Clear all resolved errors from the log.
    """
    try:
        service = get_error_service()
        count = service.clear_resolved()
        
        return {
            "success": True,
            "cleared_count": count,
            "message": f"Cleared {count} resolved errors"
        }
        
    except Exception as e:
        logger.error(f"Failed to clear errors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/json")
async def export_errors_json(
    hours: Optional[int] = Query(default=None, description="Export errors from last N hours")
):
    """
    Export errors as JSON.
    """
    try:
        service = get_error_service()
        
        since = None
        if hours:
            since = datetime.now() - timedelta(hours=hours)
        
        json_data = service.export_errors(format="json", since=since)
        
        return {
            "success": True,
            "data": json_data
        }
        
    except Exception as e:
        logger.error(f"Failed to export errors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def create_test_error(request: TestErrorRequest):
    """
    Create a test error for debugging.
    """
    try:
        sev = ErrorSeverity.ERROR
        try:
            sev = ErrorSeverity(request.severity.lower())
        except ValueError:
            pass
        
        cat = ErrorCategory.SYSTEM
        try:
            cat = ErrorCategory(request.category.lower())
        except ValueError:
            pass
        
        error = log_error(
            message=request.message,
            category=cat,
            severity=sev,
            details="This is a test error created via API",
            metadata={"test": True}
        )
        
        return {
            "success": True,
            "error": error.to_dict(),
            "message": "Test error created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
