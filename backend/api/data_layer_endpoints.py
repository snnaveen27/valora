"""
Data Layer API Endpoints
Provides REST API for data source management, uploads, and monitoring
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-layer", tags=["Data Layer"])

# Import services (lazy to avoid circular imports)
def get_data_source_manager():
    from backend.services.data_layer import DataSourceManager
    return DataSourceManager()

def get_ingestion_service():
    from backend.services.data_layer import IngestionService
    return IngestionService()

def get_file_upload_handler():
    from backend.services.data_layer import FileUploadHandler
    return FileUploadHandler()

def get_stream_manager():
    from backend.services.data_layer import StreamManager
    return StreamManager()

def get_folder_watcher():
    from backend.services.data_layer import FolderWatcher
    return FolderWatcher()

def get_data_quality_service():
    from backend.services.data_layer import DataQualityService
    return DataQualityService()


# Pydantic models
class DataSourceCreate(BaseModel):
    name: str
    source_type: str
    category: Optional[str] = None
    connection_config: Optional[dict] = None
    sync_frequency: Optional[str] = "manual"
    city_id: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = []


class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    sync_frequency: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class IngestionJobCreate(BaseModel):
    source_id: str
    job_type: str
    parameters: Optional[dict] = None


class StreamSubscriptionCreate(BaseModel):
    source_id: str
    stream_type: str
    endpoint_url: str
    config: Optional[dict] = None


class FolderWatcherCreate(BaseModel):
    source_id: str
    watch_path: str
    file_pattern: Optional[str] = "*"
    recursive: Optional[bool] = False
    auto_process: Optional[bool] = True


class IssueResolution(BaseModel):
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None


# ============================================================================
# Data Sources Endpoints
# ============================================================================

@router.get("/sources")
async def get_data_sources(
    city_id: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Get all data sources with optional filters"""
    manager = get_data_source_manager()
    sources = await manager.get_all_sources(city_id)
    
    if source_type:
        sources = [s for s in sources if s.get('source_type') == source_type]
    if status:
        sources = [s for s in sources if s.get('status') == status]
    
    return {"sources": sources, "count": len(sources)}


@router.get("/sources/{source_id}")
async def get_data_source(source_id: str):
    """Get a specific data source"""
    manager = get_data_source_manager()
    source = await manager.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/sources")
async def create_data_source(data: DataSourceCreate):
    """Create a new data source"""
    manager = get_data_source_manager()
    source = await manager.create_source(data.dict())
    return source


@router.patch("/sources/{source_id}")
async def update_data_source(source_id: str, data: DataSourceUpdate):
    """Update a data source"""
    manager = get_data_source_manager()
    source = await manager.update_source(source_id, data.dict(exclude_none=True))
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.delete("/sources/{source_id}")
async def delete_data_source(source_id: str):
    """Delete a data source"""
    manager = get_data_source_manager()
    success = await manager.delete_source(source_id)
    if not success:
        raise HTTPException(status_code=404, detail="Source not found")
    return {"message": "Source deleted"}


@router.post("/sources/{source_id}/health-check")
async def check_source_health(source_id: str):
    """Check health of a data source"""
    manager = get_data_source_manager()
    health = await manager.check_health(source_id)
    return health


@router.get("/statistics")
async def get_statistics(city_id: Optional[str] = Query(None)):
    """Get overall data layer statistics"""
    manager = get_data_source_manager()
    stats = await manager.get_statistics(city_id)
    return stats


# ============================================================================
# Ingestion Jobs Endpoints
# ============================================================================

@router.get("/jobs")
async def get_ingestion_jobs(
    source_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50)
):
    """Get ingestion jobs"""
    service = get_ingestion_service()
    jobs = await service.get_jobs(source_id, status, limit)
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/jobs/active")
async def get_active_jobs():
    """Get currently running jobs"""
    service = get_ingestion_service()
    jobs = await service.get_active_jobs()
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/jobs/{job_id}")
async def get_ingestion_job(job_id: str):
    """Get a specific job"""
    service = get_ingestion_service()
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs")
async def create_ingestion_job(data: IngestionJobCreate):
    """Create and start an ingestion job"""
    service = get_ingestion_service()
    job = await service.create_job(data.source_id, data.job_type, data.parameters)
    await service.start_job(job['id'])
    return job


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job"""
    service = get_ingestion_service()
    job = await service.cancel_job(job_id)
    if not job:
        raise HTTPException(status_code=400, detail="Cannot cancel job")
    return job


# ============================================================================
# File Upload Endpoints
# ============================================================================

@router.post("/uploads")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(...),
    city_id: Optional[str] = Form(None)
):
    """Upload a data file"""
    handler = get_file_upload_handler()
    
    content = await file.read()
    upload = await handler.upload_file(
        file_content=content,
        filename=file.filename,
        category=category,
        city_id=city_id
    )
    
    return upload


@router.get("/uploads")
async def get_uploads(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    city_id: Optional[str] = Query(None),
    limit: int = Query(50)
):
    """Get uploaded files"""
    handler = get_file_upload_handler()
    uploads = await handler.get_uploads(category, status, city_id, limit)
    return {"uploads": uploads, "count": len(uploads)}


@router.get("/uploads/{upload_id}")
async def get_upload(upload_id: str):
    """Get upload details"""
    handler = get_file_upload_handler()
    upload = await handler.get_upload(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload


@router.post("/uploads/{upload_id}/validate")
async def validate_upload(upload_id: str):
    """Validate an uploaded file"""
    handler = get_file_upload_handler()
    try:
        upload = await handler.validate_file(upload_id)
        return upload
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/uploads/{upload_id}/process")
async def process_upload(upload_id: str, column_mapping: Optional[dict] = None):
    """Process a validated upload"""
    handler = get_file_upload_handler()
    try:
        upload = await handler.process_upload(upload_id, column_mapping)
        return upload
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/uploads/{upload_id}")
async def delete_upload(upload_id: str):
    """Delete an upload"""
    handler = get_file_upload_handler()
    success = await handler.delete_upload(upload_id)
    if not success:
        raise HTTPException(status_code=404, detail="Upload not found")
    return {"message": "Upload deleted"}


# ============================================================================
# Stream Endpoints
# ============================================================================

@router.get("/streams")
async def get_streams(
    source_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Get stream subscriptions"""
    manager = get_stream_manager()
    streams = await manager.get_subscriptions(source_id, status)
    return {"streams": streams, "count": len(streams)}


@router.post("/streams")
async def create_stream(data: StreamSubscriptionCreate):
    """Create a stream subscription"""
    manager = get_stream_manager()
    stream = await manager.create_subscription(
        data.source_id,
        data.stream_type,
        data.endpoint_url,
        data.config
    )
    return stream


@router.post("/streams/{subscription_id}/connect")
async def connect_stream(subscription_id: str):
    """Connect to a stream"""
    manager = get_stream_manager()
    try:
        stream = await manager.connect(subscription_id)
        return stream
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/streams/{subscription_id}/disconnect")
async def disconnect_stream(subscription_id: str):
    """Disconnect from a stream"""
    manager = get_stream_manager()
    try:
        stream = await manager.disconnect(subscription_id)
        return stream
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/streams/metrics")
async def get_stream_metrics(subscription_id: Optional[str] = Query(None)):
    """Get stream metrics"""
    manager = get_stream_manager()
    metrics = await manager.get_metrics(subscription_id)
    return metrics


# ============================================================================
# Folder Watcher Endpoints
# ============================================================================

@router.get("/folders")
async def get_folder_watchers(
    source_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Get folder watchers"""
    watcher = get_folder_watcher()
    watchers = await watcher.get_watchers(source_id, status)
    return {"watchers": watchers, "count": len(watchers)}


@router.post("/folders")
async def create_folder_watcher(data: FolderWatcherCreate):
    """Create a folder watcher"""
    watcher = get_folder_watcher()
    result = await watcher.create_watcher(
        data.source_id,
        data.watch_path,
        data.file_pattern,
        data.recursive,
        data.auto_process
    )
    return result


@router.post("/folders/{watcher_id}/scan")
async def scan_folder(watcher_id: str):
    """Scan folder for new files"""
    watcher = get_folder_watcher()
    try:
        result = await watcher.scan(watcher_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/folders/{watcher_id}/process")
async def process_folder_files(watcher_id: str):
    """Process pending files"""
    watcher = get_folder_watcher()
    try:
        result = await watcher.process_pending(watcher_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Data Quality Endpoints
# ============================================================================

@router.get("/quality/issues")
async def get_quality_issues(
    source_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100)
):
    """Get data quality issues"""
    service = get_data_quality_service()
    issues = await service.get_issues(source_id, status, severity, limit=limit)
    return {"issues": issues, "count": len(issues)}


@router.get("/quality/summary")
async def get_quality_summary(source_id: Optional[str] = Query(None)):
    """Get quality summary"""
    service = get_data_quality_service()
    summary = await service.get_quality_summary(source_id)
    return summary


@router.get("/quality/metrics")
async def get_quality_metrics(time_range: str = Query("7d")):
    """Get quality metrics over time"""
    service = get_data_quality_service()
    metrics = await service.get_metrics(time_range)
    return metrics


@router.post("/quality/issues/{issue_id}/resolve")
async def resolve_issue(issue_id: str, data: IssueResolution):
    """Resolve a quality issue"""
    service = get_data_quality_service()
    issue = await service.resolve_issue(issue_id, data.resolved_by, data.resolution_note)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.post("/quality/issues/{issue_id}/ignore")
async def ignore_issue(issue_id: str, data: IssueResolution):
    """Ignore a quality issue"""
    service = get_data_quality_service()
    issue = await service.ignore_issue(issue_id, data.resolved_by, data.resolution_note)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


# ============================================================================
# Combined Dashboard Endpoint
# ============================================================================

@router.get("/dashboard")
async def get_dashboard_data(city_id: Optional[str] = Query(None)):
    """Get all data for the admin dashboard data layer tab"""
    manager = get_data_source_manager()
    ingestion = get_ingestion_service()
    quality = get_data_quality_service()
    uploads = get_file_upload_handler()
    
    # Gather all data
    sources = await manager.get_all_sources(city_id)
    stats = await manager.get_statistics(city_id)
    jobs = await ingestion.get_jobs(limit=10)
    active_jobs = await ingestion.get_active_jobs()
    issues = await quality.get_issues(status='open', limit=10)
    quality_summary = await quality.get_quality_summary()
    recent_uploads = await uploads.get_uploads(limit=5)
    
    return {
        "sources": sources,
        "statistics": stats,
        "recent_jobs": jobs,
        "active_jobs": active_jobs,
        "open_issues": issues,
        "quality_summary": quality_summary,
        "recent_uploads": recent_uploads
    }
