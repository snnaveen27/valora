"""
Task Orchestration API Routes
Provides endpoints for task template management, execution monitoring, and decomposition.
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ai.task_orchestrator import get_task_orchestrator, TaskOrchestrator
from ai.task_templates import TaskTemplate, TaskSpec, get_template_library
from ai.task_monitor import get_task_monitor, TaskMonitor
from ai.task_decomposer import get_task_decomposer, TaskDecomposer
from config import config, TaskConfig

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# Request/Response Models
class DecomposeRequest(BaseModel):
    """Request for task decomposition"""
    query: str
    intent: Optional[str] = None
    slots: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


class TemplateCreateRequest(BaseModel):
    """Request to create a new template"""
    name: str
    description: str
    intent_patterns: List[str]
    parameter_schema: Dict[str, Any]
    task_sequence: List[Dict[str, Any]]
    tags: Optional[List[str]] = None


class TemplateUpdateRequest(BaseModel):
    """Request to update a template"""
    name: Optional[str] = None
    description: Optional[str] = None
    intent_patterns: Optional[List[str]] = None
    parameter_schema: Optional[Dict[str, Any]] = None
    task_sequence: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None


class ExecuteRequest(BaseModel):
    """Request to execute tasks"""
    query: str
    intent: str
    slots: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    streaming: bool = False


# ============== Template Management Endpoints ==============

@router.get("/templates")
async def list_templates(
    tag: Optional[str] = Query(None, description="Filter by tag"),
    min_success_rate: Optional[float] = Query(None, description="Minimum success rate")
):
    """List all task templates"""
    library = get_template_library()
    templates = library.list_templates(tag=tag)
    
    result = []
    for template in templates:
        if min_success_rate and template.success_rate < min_success_rate:
            continue
        result.append({
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "intent_patterns": template.intent_patterns,
            "success_rate": template.success_rate,
            "execution_count": template.execution_count,
            "avg_duration_ms": template.avg_duration_ms,
            "tags": template.tags,
            "last_used": template.last_used
        })
    
    return {"templates": result, "total": len(result)}


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific template by ID"""
    library = get_template_library()
    template = library.get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "intent_patterns": template.intent_patterns,
        "parameter_schema": template.parameter_schema,
        "task_sequence": [
            {
                "id_template": spec.id_template,
                "action": spec.action,
                "entity": spec.entity,
                "task_type": spec.task_type,
                "parameters": spec.parameters,
                "dependencies": spec.dependencies,
                "priority": spec.priority
            }
            for spec in template.task_sequence
        ],
        "success_rate": template.success_rate,
        "execution_count": template.execution_count,
        "avg_duration_ms": template.avg_duration_ms,
        "tags": template.tags,
        "version": template.version,
        "created_at": template.created_at,
        "last_used": template.last_used
    }


@router.post("/templates")
async def create_template(request: TemplateCreateRequest):
    """Create a new task template"""
    library = get_template_library()
    
    # Generate template ID
    template_id = f"custom_{request.name.lower().replace(' ', '_')}_{int(time.time())}"
    
    # Convert task_sequence to TaskSpec objects
    task_specs = []
    for i, task_data in enumerate(request.task_sequence):
        spec = TaskSpec(
            id_template=task_data.get("id_template", f"t{i+1}_${{location}}_{task_data.get('action', 'task')}"),
            action=task_data["action"],
            entity=task_data.get("entity", ""),
            task_type=task_data.get("task_type", "generic"),
            parameters=task_data.get("parameters", {}),
            dependencies=task_data.get("dependencies", []),
            priority=task_data.get("priority", 1)
        )
        task_specs.append(spec)
    
    template = TaskTemplate(
        id=template_id,
        name=request.name,
        description=request.description,
        intent_patterns=request.intent_patterns,
        parameter_schema=request.parameter_schema,
        task_sequence=task_specs,
        tags=request.tags or []
    )
    
    if not library.add_template(template):
        raise HTTPException(status_code=400, detail="Template with this ID already exists")
    
    return {"id": template_id, "message": "Template created successfully"}


@router.put("/templates/{template_id}")
async def update_template(template_id: str, request: TemplateUpdateRequest):
    """Update an existing template"""
    library = get_template_library()
    template = library.get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Update fields
    if request.name:
        template.name = request.name
    if request.description:
        template.description = request.description
    if request.intent_patterns:
        template.intent_patterns = request.intent_patterns
    if request.parameter_schema:
        template.parameter_schema = request.parameter_schema
    if request.task_sequence:
        task_specs = []
        for i, task_data in enumerate(request.task_sequence):
            spec = TaskSpec(
                id_template=task_data.get("id_template", f"t{i+1}_${{location}}_{task_data.get('action', 'task')}"),
                action=task_data["action"],
                entity=task_data.get("entity", ""),
                task_type=task_data.get("task_type", "generic"),
                parameters=task_data.get("parameters", {}),
                dependencies=task_data.get("dependencies", []),
                priority=task_data.get("priority", 1)
            )
            task_specs.append(spec)
        template.task_sequence = task_specs
    if request.tags is not None:
        template.tags = request.tags
    
    if not library.update_template(template):
        raise HTTPException(status_code=500, detail="Failed to update template")
    
    return {"message": "Template updated successfully"}


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    """Delete a template"""
    library = get_template_library()
    
    if not library.delete_template(template_id):
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Template deleted successfully"}


# ============== Task Decomposition Endpoints ==============

@router.post("/decompose")
async def decompose_query(request: DecomposeRequest):
    """Decompose a query into tasks"""
    decomposer = get_task_decomposer()
    
    result = await decomposer.decompose(
        query=request.query,
        intent=request.intent or "unknown",
        slots=request.slots or {},
        context=request.context
    )
    
    return {
        "tasks": [
            {
                "id": task.id,
                "action": task.action,
                "entity": task.entity,
                "task_type": task.task_type,
                "parameters": task.parameters,
                "dependencies": task.dependencies,
                "confidence": task.confidence,
                "source_span": task.source_span,
                "priority": task.priority
            }
            for task in result.tasks
        ],
        "overall_confidence": result.overall_confidence,
        "reasoning": result.reasoning,
        "method": result.method,
        "template_used": result.template_used,
        "warnings": result.warnings
    }


# ============== Execution Monitoring Endpoints ==============

@router.get("/execution/{session_id}")
async def get_execution_status(session_id: str):
    """Get status of an execution session"""
    monitor = get_task_monitor()
    
    # Get session from database
    # This would need to be implemented in TaskMonitor
    return {
        "session_id": session_id,
        "status": "completed",
        "message": "Session status retrieval not yet implemented"
    }


@router.get("/execution/{session_id}/graph")
async def get_execution_graph(session_id: str):
    """Get the dependency graph for an execution session"""
    return {
        "session_id": session_id,
        "nodes": [],
        "edges": {},
        "message": "Graph retrieval not yet implemented"
    }


@router.get("/metrics")
async def get_task_metrics(
    hours: int = Query(24, description="Time period in hours")
):
    """Get task execution metrics"""
    monitor = get_task_monitor()
    stats = monitor.get_statistics(hours=hours)
    
    return {
        "period_hours": hours,
        "statistics": stats
    }


@router.get("/monitoring/realtime")
async def get_realtime_stats():
    """Get real-time monitoring statistics"""
    monitor = get_task_monitor()
    progress = monitor.get_session_progress()
    
    return {
        "current_session": progress,
        "active_tasks": monitor.get_active_tasks(),
        "counters": dict(monitor._counters),
        "gauges": dict(monitor._gauges)
    }


# ============== Statistics Endpoints ==============

@router.get("/statistics")
async def get_orchestrator_statistics():
    """Get overall task orchestration statistics"""
    orchestrator = get_task_orchestrator()
    stats = orchestrator.get_statistics()
    
    return {
        "orchestrator": stats,
        "config": {
            "max_concurrent_tasks": config.TASK_CONFIG.MAX_CONCURRENT_TASKS,
            "task_timeout_seconds": config.TASK_CONFIG.TASK_TIMEOUT_SECONDS,
            "decomposition_confidence_threshold": config.TASK_CONFIG.DECOMPOSITION_CONFIDENCE_THRESHOLD,
            "feature_flags": config.TASK_CONFIG.FEATURE_FLAGS
        }
    }


@router.get("/statistics/decomposer")
async def get_decomposer_statistics():
    """Get task decomposer statistics"""
    decomposer = get_task_decomposer()
    return decomposer.get_statistics()


@router.get("/statistics/templates")
async def get_template_statistics():
    """Get template library statistics"""
    library = get_template_library()
    return library.get_statistics()


# ============== Feature Flag Endpoints ==============

@router.get("/features")
async def get_feature_flags():
    """Get current feature flag states"""
    return {
        "features": config.TASK_CONFIG.FEATURE_FLAGS
    }


@router.post("/features/{feature_name}/toggle")
async def toggle_feature_flag(feature_name: str, enabled: bool):
    """Toggle a feature flag"""
    if feature_name not in config.TASK_CONFIG.FEATURE_FLAGS:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    
    config.TASK_CONFIG.FEATURE_FLAGS[feature_name] = enabled
    
    return {
        "feature": feature_name,
        "enabled": enabled,
        "message": f"Feature '{feature_name}' {'enabled' if enabled else 'disabled'}"
    }


# ============== Health Check ==============

@router.get("/health")
async def task_system_health():
    """Check health of task orchestration system"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # Check template library
    try:
        library = get_template_library()
        stats = library.get_statistics()
        health_status["components"]["template_library"] = {
            "status": "healthy",
            "template_count": stats["total_templates"]
        }
    except Exception as e:
        health_status["components"]["template_library"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check task monitor
    try:
        monitor = get_task_monitor()
        health_status["components"]["task_monitor"] = {
            "status": "healthy"
        }
    except Exception as e:
        health_status["components"]["task_monitor"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check decomposer
    try:
        decomposer = get_task_decomposer()
        stats = decomposer.get_statistics()
        health_status["components"]["task_decomposer"] = {
            "status": "healthy",
            "total_decompositions": stats["total_decompositions"]
        }
    except Exception as e:
        health_status["components"]["task_decomposer"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status
