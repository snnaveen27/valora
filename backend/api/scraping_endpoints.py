"""
Data Scraping API Endpoints
Manage Apify scraping jobs, schedules, and status.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scraping", tags=["Data Scraping"])

# Import scraping services
try:
    from backend.services.scraping import (
        scraping_scheduler, ScrapingSource, JobFrequency, JobStatus
    )
    SCRAPING_AVAILABLE = True
except ImportError as e:
    SCRAPING_AVAILABLE = False
    scraping_scheduler = None
    logger.warning(f"Scraping services not available: {e}")


# ===================== Request Models =====================

class CreateJobRequest(BaseModel):
    name: str = Field(..., description="Job name")
    source: str = Field(..., description="google_maps, property_listings, news_articles")
    frequency: str = Field(default="once", description="once, hourly, daily, weekly, monthly")
    cron_expression: Optional[str] = Field(default=None, description="Cron expression for custom scheduling")
    input_config: Optional[Dict[str, Any]] = Field(default=None, description="Apify actor input configuration")


class UpdateJobRequest(BaseModel):
    name: Optional[str] = None
    frequency: Optional[str] = None
    cron_expression: Optional[str] = None
    input_config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


# ===================== Status Endpoints =====================

@router.get("/status")
async def get_scraping_status() -> Dict[str, Any]:
    """Get overall scraping system status"""
    if not SCRAPING_AVAILABLE:
        return {
            "available": False,
            "error": "Scraping services not loaded"
        }
    
    return {
        "available": True,
        **scraping_scheduler.get_status()
    }


@router.get("/dashboard")
async def get_dashboard_data() -> Dict[str, Any]:
    """Get comprehensive dashboard data for admin UI"""
    if not SCRAPING_AVAILABLE:
        return {
            "available": False,
            "jobs": [],
            "recent_runs": [],
            "status": {}
        }
    
    return scraping_scheduler.get_dashboard_data()


# ===================== Job Management =====================

@router.get("/jobs")
async def list_jobs(
    source: Optional[str] = Query(default=None, description="Filter by source")
) -> Dict[str, Any]:
    """List all scraping jobs"""
    if not SCRAPING_AVAILABLE:
        return {"jobs": []}
    
    source_enum = None
    if source:
        try:
            source_enum = ScrapingSource(source)
        except ValueError:
            pass
    
    jobs = scraping_scheduler.list_jobs(source_enum)
    
    return {
        "count": len(jobs),
        "jobs": [
            {
                "id": j.id,
                "name": j.name,
                "source": j.source.value,
                "status": j.status.value,
                "frequency": j.frequency.value,
                "cron_expression": j.cron_expression,
                "enabled": j.enabled,
                "next_run": j.next_run,
                "last_run": j.last_run,
                "run_count": j.run_count,
                "success_count": j.success_count,
                "failure_count": j.failure_count,
                "records_fetched": j.records_fetched,
                "error_message": j.error_message
            }
            for j in jobs
        ]
    }


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> Dict[str, Any]:
    """Get job details"""
    if not SCRAPING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scraping services not available")
    
    job = scraping_scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job.id,
        "name": job.name,
        "source": job.source.value,
        "status": job.status.value,
        "frequency": job.frequency.value,
        "cron_expression": job.cron_expression,
        "actor_id": job.actor_id,
        "input_config": job.input_config,
        "enabled": job.enabled,
        "created_at": job.created_at,
        "next_run": job.next_run,
        "last_run": job.last_run,
        "run_count": job.run_count,
        "success_count": job.success_count,
        "failure_count": job.failure_count,
        "records_fetched": job.records_fetched,
        "error_message": job.error_message
    }


@router.post("/jobs")
async def create_job(request: CreateJobRequest) -> Dict[str, Any]:
    """Create a new scraping job"""
    if not SCRAPING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scraping services not available")
    
    try:
        source = ScrapingSource(request.source)
        frequency = JobFrequency(request.frequency)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid value: {e}")
    
    job = scraping_scheduler.create_job(
        name=request.name,
        source=source,
        frequency=frequency,
        input_config=request.input_config,
        cron_expression=request.cron_expression
    )
    
    return {
        "success": True,
        "job_id": job.id,
        "message": f"Job '{job.name}' created successfully"
    }


@router.put("/jobs/{job_id}")
async def update_job(job_id: str, request: UpdateJobRequest) -> Dict[str, Any]:
    """Update job configuration"""
    if not SCRAPING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scraping services not available")
    
    updates = {k: v for k, v in request.dict().items() if v is not None}
    
    if "frequency" in updates:
        try:
            updates["frequency"] = JobFrequency(updates["frequency"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid frequency")
    
    job = scraping_scheduler.update_job(job_id, **updates)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "success": True,
        "message": "Job updated"
    }


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str) -> Dict[str, Any]:
    """Delete a scraping job"""
    if not SCRAPING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scraping services not available")
    
    success = scraping_scheduler.delete_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "success": True,
        "message": "Job deleted"
    }


@router.post("/jobs/{job_id}/toggle")
async def toggle_job(job_id: str) -> Dict[str, Any]:
    """Enable/disable a job"""
    if not SCRAPING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scraping services not available")
    
    job = scraping_scheduler.toggle_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "success": True,
        "enabled": job.enabled,
        "message": f"Job {'enabled' if job.enabled else 'disabled'}"
    }


# ===================== Job Execution =====================

@router.post("/jobs/{job_id}/run")
async def run_job(job_id: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Manually trigger a job run"""
    if not SCRAPING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scraping services not available")
    
    job = scraping_scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Run in background
    background_tasks.add_task(scraping_scheduler.run_job, job_id)
    
    return {
        "success": True,
        "message": f"Job '{job.name}' started",
        "job_id": job_id
    }


@router.get("/runs")
async def get_recent_runs(
    limit: int = Query(default=20, le=100)
) -> Dict[str, Any]:
    """Get recent run history"""
    if not SCRAPING_AVAILABLE:
        return {"runs": []}
    
    runs = scraping_scheduler.get_recent_runs(limit)
    
    return {
        "count": len(runs),
        "runs": [
            {
                "id": r.id,
                "job_id": r.job_id,
                "status": r.status.value,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "duration_seconds": r.duration_seconds,
                "records_fetched": r.records_fetched,
                "error_message": r.error_message
            }
            for r in runs
        ]
    }


# ===================== Scheduler Control =====================

@router.post("/scheduler/start")
async def start_scheduler() -> Dict[str, Any]:
    """Start the background scheduler"""
    if not SCRAPING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scraping services not available")
    
    scraping_scheduler.start_scheduler()
    
    return {
        "success": True,
        "message": "Scheduler started"
    }


@router.post("/scheduler/stop")
async def stop_scheduler() -> Dict[str, Any]:
    """Stop the background scheduler"""
    if not SCRAPING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Scraping services not available")
    
    scraping_scheduler.stop_scheduler()
    
    return {
        "success": True,
        "message": "Scheduler stopped"
    }


# ===================== Sources =====================

@router.get("/sources")
async def list_sources() -> Dict[str, Any]:
    """List available scraping sources"""
    return {
        "sources": [
            {"id": "google_maps", "name": "Google Maps", "description": "POIs, reviews, locations"},
            {"id": "property_listings", "name": "Property Listings", "description": "Real estate listings from portals"},
            {"id": "news_articles", "name": "News Articles", "description": "Real estate news and updates"},
            {"id": "government_data", "name": "Government Data", "description": "Official records and statistics"},
            {"id": "social_media", "name": "Social Media", "description": "Social sentiment and trends"}
        ]
    }
