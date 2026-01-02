"""
Ingestion Service - Handles data ingestion jobs
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    FULL_SYNC = "full_sync"
    INCREMENTAL = "incremental"
    UPLOAD = "upload"
    STREAM_BATCH = "stream_batch"


class IngestionService:
    """Manages data ingestion jobs"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self._active_jobs: Dict[str, dict] = {}
    
    async def create_job(self, source_id: str, job_type: str, parameters: dict = None) -> dict:
        """Create a new ingestion job"""
        job = {
            'id': str(uuid4()),
            'source_id': source_id,
            'job_type': job_type,
            'status': JobStatus.PENDING.value,
            'created_at': datetime.utcnow().isoformat(),
            'started_at': None,
            'completed_at': None,
            'total_records': 0,
            'processed_records': 0,
            'success_records': 0,
            'failed_records': 0,
            'skipped_records': 0,
            'avg_quality_score': None,
            'error_message': None,
            'parameters': parameters or {},
            'triggered_by': parameters.get('triggered_by', 'manual') if parameters else 'manual'
        }
        
        self._active_jobs[job['id']] = job
        logger.info(f"Created ingestion job: {job['id']} for source {source_id}")
        return job
    
    async def start_job(self, job_id: str) -> Optional[dict]:
        """Start an ingestion job"""
        job = self._active_jobs.get(job_id)
        if not job:
            return None
        
        job['status'] = JobStatus.RUNNING.value
        job['started_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Started ingestion job: {job_id}")
        return job
    
    async def update_progress(self, job_id: str, processed: int, success: int, failed: int) -> Optional[dict]:
        """Update job progress"""
        job = self._active_jobs.get(job_id)
        if not job:
            return None
        
        job['processed_records'] = processed
        job['success_records'] = success
        job['failed_records'] = failed
        
        return job
    
    async def complete_job(self, job_id: str, quality_score: float = None, error_message: str = None) -> Optional[dict]:
        """Complete an ingestion job"""
        job = self._active_jobs.get(job_id)
        if not job:
            return None
        
        job['status'] = JobStatus.COMPLETED.value if not error_message else JobStatus.FAILED.value
        job['completed_at'] = datetime.utcnow().isoformat()
        job['avg_quality_score'] = quality_score
        job['error_message'] = error_message
        
        if job['started_at']:
            started = datetime.fromisoformat(job['started_at'])
            job['duration_seconds'] = int((datetime.utcnow() - started).total_seconds())
        
        logger.info(f"Completed ingestion job: {job_id} - Status: {job['status']}")
        return job
    
    async def cancel_job(self, job_id: str) -> Optional[dict]:
        """Cancel a running job"""
        job = self._active_jobs.get(job_id)
        if not job or job['status'] not in [JobStatus.PENDING.value, JobStatus.RUNNING.value]:
            return None
        
        job['status'] = JobStatus.CANCELLED.value
        job['completed_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Cancelled ingestion job: {job_id}")
        return job
    
    async def get_job(self, job_id: str) -> Optional[dict]:
        """Get job details"""
        return self._active_jobs.get(job_id)
    
    async def get_jobs(self, source_id: str = None, status: str = None, limit: int = 50) -> List[dict]:
        """Get recent jobs with optional filters"""
        jobs = list(self._active_jobs.values())
        
        if source_id:
            jobs = [j for j in jobs if j['source_id'] == source_id]
        if status:
            jobs = [j for j in jobs if j['status'] == status]
        
        # Sort by created_at desc
        jobs.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Add mock historical jobs for demo
        if not jobs:
            jobs = self._get_mock_jobs(source_id, status)
        
        return jobs[:limit]
    
    async def get_active_jobs(self) -> List[dict]:
        """Get all currently running jobs"""
        return [j for j in self._active_jobs.values() if j['status'] == JobStatus.RUNNING.value]
    
    def _get_mock_jobs(self, source_id: str = None, status: str = None) -> List[dict]:
        """Return mock jobs for demo"""
        now = datetime.utcnow()
        jobs = [
            {
                'id': 'job-001',
                'source_id': 'src-001',
                'source_name': 'MagicBricks Scraper',
                'source_type': 'scraped',
                'job_type': 'incremental',
                'status': 'completed',
                'started_at': (now - timedelta(hours=2, minutes=15)).isoformat(),
                'completed_at': (now - timedelta(hours=2)).isoformat(),
                'duration_seconds': 900,
                'total_records': 156,
                'processed_records': 156,
                'success_records': 152,
                'failed_records': 4,
                'avg_quality_score': 0.92,
                'error_message': None
            },
            {
                'id': 'job-002',
                'source_id': 'src-002',
                'source_name': '99acres Scraper',
                'source_type': 'scraped',
                'job_type': 'incremental',
                'status': 'running',
                'started_at': (now - timedelta(minutes=12)).isoformat(),
                'completed_at': None,
                'duration_seconds': None,
                'total_records': 250,
                'processed_records': 178,
                'success_records': 175,
                'failed_records': 3,
                'avg_quality_score': 0.89,
                'error_message': None
            },
            {
                'id': 'job-003',
                'source_id': 'src-003',
                'source_name': 'Manual Uploads',
                'source_type': 'upload',
                'job_type': 'upload',
                'status': 'completed',
                'started_at': (now - timedelta(days=1, hours=3)).isoformat(),
                'completed_at': (now - timedelta(days=1, hours=2, minutes=45)).isoformat(),
                'duration_seconds': 900,
                'total_records': 450,
                'processed_records': 450,
                'success_records': 448,
                'failed_records': 2,
                'avg_quality_score': 0.95,
                'error_message': None
            },
            {
                'id': 'job-004',
                'source_id': 'src-007',
                'source_name': 'Real-time Price Stream',
                'source_type': 'streaming',
                'job_type': 'stream_batch',
                'status': 'running',
                'started_at': (now - timedelta(hours=6)).isoformat(),
                'completed_at': None,
                'duration_seconds': None,
                'total_records': 2340,
                'processed_records': 2340,
                'success_records': 2320,
                'failed_records': 20,
                'avg_quality_score': 0.91,
                'error_message': None
            },
            {
                'id': 'job-005',
                'source_id': 'src-001',
                'source_name': 'MagicBricks Scraper',
                'source_type': 'scraped',
                'job_type': 'full_sync',
                'status': 'failed',
                'started_at': (now - timedelta(days=2, hours=8)).isoformat(),
                'completed_at': (now - timedelta(days=2, hours=7, minutes=30)).isoformat(),
                'duration_seconds': 1800,
                'total_records': 5000,
                'processed_records': 2340,
                'success_records': 2280,
                'failed_records': 60,
                'avg_quality_score': 0.78,
                'error_message': 'Rate limit exceeded - retry in 1 hour'
            }
        ]
        
        if source_id:
            jobs = [j for j in jobs if j['source_id'] == source_id]
        if status:
            jobs = [j for j in jobs if j['status'] == status]
        
        return jobs


# Singleton instance
ingestion_service = IngestionService()
