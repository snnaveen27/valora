"""
Data Scraping Scheduler Service
Manages scheduled scraping jobs using Apify with cron-like scheduling.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import hashlib
import threading
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Scraping job statuses"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class JobFrequency(str, Enum):
    """Job scheduling frequency"""
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ScrapingSource(str, Enum):
    """Data sources for scraping"""
    GOOGLE_MAPS = "google_maps"
    PROPERTY_LISTINGS = "property_listings"
    NEWS_ARTICLES = "news_articles"
    GOVERNMENT_DATA = "government_data"
    SOCIAL_MEDIA = "social_media"


@dataclass
class ScrapingJob:
    """Single scraping job"""
    id: str
    name: str
    source: ScrapingSource
    status: JobStatus = JobStatus.PENDING
    frequency: JobFrequency = JobFrequency.ONCE
    cron_expression: Optional[str] = None
    actor_id: str = "compass/crawler-google-places"
    input_config: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    next_run: Optional[str] = None
    last_run: Optional[str] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    records_fetched: int = 0
    error_message: Optional[str] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScrapingRun:
    """Single execution of a scraping job"""
    id: str
    job_id: str
    status: JobStatus
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: float = 0
    records_fetched: int = 0
    apify_run_id: Optional[str] = None
    error_message: Optional[str] = None
    output_file: Optional[str] = None


# Apify Actor IDs for different scraping tasks
APIFY_ACTORS = {
    ScrapingSource.GOOGLE_MAPS: "compass/crawler-google-places",
    ScrapingSource.PROPERTY_LISTINGS: "apify/web-scraper",
    ScrapingSource.NEWS_ARTICLES: "apify/google-search-scraper",
    ScrapingSource.GOVERNMENT_DATA: "apify/web-scraper",
    ScrapingSource.SOCIAL_MEDIA: "apify/instagram-scraper"
}


class ScrapingScheduler:
    """
    Manages scheduled scraping jobs with Apify integration.
    Supports cron-like scheduling for automated data collection.
    """
    
    def __init__(self):
        self.api_token = os.getenv("APIFY_API_TOKEN") or os.getenv("APIFY_API_KEY")
        self.client = ApifyClient(self.api_token) if self.api_token else None
        
        self.jobs: Dict[str, ScrapingJob] = {}
        self.runs: List[ScrapingRun] = []
        self.data_dir = Path("data/scraped")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._scheduler_running = False
        self._scheduler_thread = None
        
        # Stats - must be initialized before _init_default_jobs
        self.stats = {
            "total_jobs": 0,
            "active_jobs": 0,
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "total_records": 0,
            "last_run_time": None
        }
        
        # Initialize default jobs (after stats is initialized)
        self._init_default_jobs()
        
        logger.info(f"Scraping scheduler initialized. Apify client: {'Ready' if self.client else 'Not configured'}")
    
    def _init_default_jobs(self):
        """Initialize default scraping jobs"""
        default_jobs = [
            {
                "name": "Bangalore Localities - Google Maps",
                "source": ScrapingSource.GOOGLE_MAPS,
                "frequency": JobFrequency.WEEKLY,
                "cron_expression": "0 2 * * 0",  # Every Sunday 2 AM
                "actor_id": "compass/crawler-google-places",
                "input_config": {
                    "searchStringsArray": [
                        "real estate Whitefield Bangalore",
                        "real estate Koramangala Bangalore",
                        "real estate HSR Layout Bangalore",
                        "real estate Electronic City Bangalore",
                        "real estate Sarjapur Bangalore"
                    ],
                    "maxCrawledPlacesPerSearch": 50,
                    "language": "en",
                    "countryCode": "IN"
                }
            },
            {
                "name": "Bangalore Infrastructure POIs",
                "source": ScrapingSource.GOOGLE_MAPS,
                "frequency": JobFrequency.MONTHLY,
                "cron_expression": "0 3 1 * *",  # 1st of every month 3 AM
                "actor_id": "compass/crawler-google-places",
                "input_config": {
                    "searchStringsArray": [
                        "metro station Bangalore",
                        "hospitals Bangalore",
                        "schools Bangalore",
                        "shopping malls Bangalore",
                        "tech parks Bangalore"
                    ],
                    "maxCrawledPlacesPerSearch": 100,
                    "language": "en",
                    "countryCode": "IN"
                }
            },
            {
                "name": "Real Estate News",
                "source": ScrapingSource.NEWS_ARTICLES,
                "frequency": JobFrequency.DAILY,
                "cron_expression": "0 6 * * *",  # Every day 6 AM
                "actor_id": "apify/google-search-scraper",
                "input_config": {
                    "queries": "Bangalore real estate news",
                    "maxPagesPerQuery": 3,
                    "resultsPerPage": 10
                }
            },
            {
                "name": "Property Price Updates",
                "source": ScrapingSource.PROPERTY_LISTINGS,
                "frequency": JobFrequency.DAILY,
                "cron_expression": "0 4 * * *",  # Every day 4 AM
                "actor_id": "apify/web-scraper",
                "input_config": {
                    "startUrls": [
                        {"url": "https://www.99acres.com/property-in-bangalore-ffid"},
                        {"url": "https://www.magicbricks.com/property-for-sale/residential-real-estate?proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment&cityName=Bangalore"}
                    ],
                    "maxRequestsPerCrawl": 100
                }
            }
        ]
        
        for job_config in default_jobs:
            job_id = hashlib.md5(job_config["name"].encode()).hexdigest()[:12]
            
            # Calculate next run time based on frequency
            next_run = self._calculate_next_run(
                JobFrequency(job_config["frequency"]),
                job_config.get("cron_expression")
            )
            
            job = ScrapingJob(
                id=job_id,
                name=job_config["name"],
                source=ScrapingSource(job_config["source"]),
                frequency=JobFrequency(job_config["frequency"]),
                cron_expression=job_config.get("cron_expression"),
                actor_id=job_config["actor_id"],
                input_config=job_config["input_config"],
                next_run=next_run,
                status=JobStatus.SCHEDULED
            )
            self.jobs[job_id] = job
        
        self._update_stats()
    
    def _calculate_next_run(self, frequency: JobFrequency, cron_expr: str = None) -> str:
        """Calculate next run time based on frequency"""
        now = datetime.now()
        
        if frequency == JobFrequency.HOURLY:
            next_run = now + timedelta(hours=1)
        elif frequency == JobFrequency.DAILY:
            next_run = now + timedelta(days=1)
            next_run = next_run.replace(hour=4, minute=0, second=0)
        elif frequency == JobFrequency.WEEKLY:
            days_ahead = 7 - now.weekday()
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=2, minute=0, second=0)
        elif frequency == JobFrequency.MONTHLY:
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_run = now.replace(month=now.month + 1, day=1)
            next_run = next_run.replace(hour=3, minute=0, second=0)
        else:
            next_run = now + timedelta(minutes=5)
        
        return next_run.isoformat()
    
    def _update_stats(self):
        """Update scheduler statistics"""
        self.stats["total_jobs"] = len(self.jobs)
        self.stats["active_jobs"] = len([j for j in self.jobs.values() if j.enabled])
        self.stats["total_runs"] = len(self.runs)
        self.stats["successful_runs"] = len([r for r in self.runs if r.status == JobStatus.COMPLETED])
        self.stats["failed_runs"] = len([r for r in self.runs if r.status == JobStatus.FAILED])
        self.stats["total_records"] = sum(j.records_fetched for j in self.jobs.values())
    
    # ===========================================
    # Job Management
    # ===========================================
    
    def create_job(
        self,
        name: str,
        source: ScrapingSource,
        frequency: JobFrequency = JobFrequency.ONCE,
        input_config: Dict[str, Any] = None,
        cron_expression: str = None
    ) -> ScrapingJob:
        """Create a new scraping job"""
        job_id = hashlib.md5(f"{name}{datetime.now()}".encode()).hexdigest()[:12]
        
        job = ScrapingJob(
            id=job_id,
            name=name,
            source=source,
            frequency=frequency,
            cron_expression=cron_expression,
            actor_id=APIFY_ACTORS.get(source, "apify/web-scraper"),
            input_config=input_config or {},
            next_run=self._calculate_next_run(frequency, cron_expression),
            status=JobStatus.SCHEDULED if frequency != JobFrequency.ONCE else JobStatus.PENDING
        )
        
        self.jobs[job_id] = job
        self._update_stats()
        
        logger.info(f"Created scraping job: {name} ({job_id})")
        return job
    
    def get_job(self, job_id: str) -> Optional[ScrapingJob]:
        """Get job by ID"""
        return self.jobs.get(job_id)
    
    def list_jobs(self, source: ScrapingSource = None) -> List[ScrapingJob]:
        """List all jobs, optionally filtered by source"""
        jobs = list(self.jobs.values())
        if source:
            jobs = [j for j in jobs if j.source == source]
        return jobs
    
    def update_job(self, job_id: str, **kwargs) -> Optional[ScrapingJob]:
        """Update job configuration"""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        
        return job
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._update_stats()
            return True
        return False
    
    def toggle_job(self, job_id: str) -> Optional[ScrapingJob]:
        """Enable/disable a job"""
        job = self.jobs.get(job_id)
        if job:
            job.enabled = not job.enabled
            self._update_stats()
        return job
    
    # ===========================================
    # Job Execution
    # ===========================================
    
    async def run_job(self, job_id: str) -> Optional[ScrapingRun]:
        """Execute a scraping job"""
        job = self.jobs.get(job_id)
        if not job:
            logger.error(f"Job not found: {job_id}")
            return None
        
        if not self.client:
            logger.error("Apify client not configured")
            job.status = JobStatus.FAILED
            job.error_message = "Apify API token not configured"
            return None
        
        # Create run record
        run_id = hashlib.md5(f"{job_id}{datetime.now()}".encode()).hexdigest()[:12]
        run = ScrapingRun(
            id=run_id,
            job_id=job_id,
            status=JobStatus.RUNNING,
            started_at=datetime.now().isoformat()
        )
        self.runs.append(run)
        
        # Update job status
        job.status = JobStatus.RUNNING
        job.started_at = run.started_at
        job.run_count += 1
        
        try:
            logger.info(f"Starting scraping job: {job.name} ({job_id})")
            
            # Run Apify actor
            actor_run = self.client.actor(job.actor_id).call(run_input=job.input_config)
            
            run.apify_run_id = actor_run.get("id")
            
            # Get results from dataset
            dataset_id = actor_run.get("defaultDatasetId")
            if dataset_id:
                items = list(self.client.dataset(dataset_id).iterate_items())
                run.records_fetched = len(items)
                
                # Save results
                output_file = self.data_dir / f"{job.source.value}_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(items, f, indent=2, ensure_ascii=False)
                run.output_file = str(output_file)
                
                logger.info(f"Scraped {len(items)} records, saved to {output_file}")
            
            # Update job and run
            run.status = JobStatus.COMPLETED
            run.completed_at = datetime.now().isoformat()
            run.duration_seconds = (
                datetime.fromisoformat(run.completed_at) - 
                datetime.fromisoformat(run.started_at)
            ).total_seconds()
            
            job.status = JobStatus.COMPLETED
            job.completed_at = run.completed_at
            job.last_run = run.completed_at
            job.success_count += 1
            job.records_fetched += run.records_fetched
            job.error_message = None
            
            # Schedule next run if recurring
            if job.frequency != JobFrequency.ONCE:
                job.next_run = self._calculate_next_run(job.frequency, job.cron_expression)
                job.status = JobStatus.SCHEDULED
            
        except Exception as e:
            logger.error(f"Scraping job failed: {e}")
            run.status = JobStatus.FAILED
            run.error_message = str(e)
            run.completed_at = datetime.now().isoformat()
            
            job.status = JobStatus.FAILED
            job.failure_count += 1
            job.error_message = str(e)
            
            # Still schedule next run for recurring jobs
            if job.frequency != JobFrequency.ONCE:
                job.next_run = self._calculate_next_run(job.frequency, job.cron_expression)
        
        self._update_stats()
        self.stats["last_run_time"] = datetime.now().isoformat()
        
        return run
    
    async def run_job_now(self, job_id: str) -> Optional[ScrapingRun]:
        """Immediately run a job (bypass schedule)"""
        return await self.run_job(job_id)
    
    # ===========================================
    # Scheduler
    # ===========================================
    
    def start_scheduler(self):
        """Start the background scheduler"""
        if self._scheduler_running:
            return
        
        self._scheduler_running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        logger.info("Scraping scheduler started")
    
    def stop_scheduler(self):
        """Stop the background scheduler"""
        self._scheduler_running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("Scraping scheduler stopped")
    
    def _scheduler_loop(self):
        """Background scheduler loop"""
        while self._scheduler_running:
            try:
                now = datetime.now()
                
                for job in self.jobs.values():
                    if not job.enabled:
                        continue
                    
                    if job.status == JobStatus.SCHEDULED and job.next_run:
                        next_run_time = datetime.fromisoformat(job.next_run)
                        
                        if now >= next_run_time:
                            # Run the job
                            asyncio.run(self.run_job(job.id))
                
                # Sleep for 1 minute between checks
                for _ in range(60):
                    if not self._scheduler_running:
                        break
                    threading.Event().wait(1)
                    
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
    
    # ===========================================
    # Status & Reporting
    # ===========================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            "scheduler_running": self._scheduler_running,
            "apify_configured": self.client is not None,
            "stats": self.stats,
            "jobs_summary": {
                "total": len(self.jobs),
                "enabled": len([j for j in self.jobs.values() if j.enabled]),
                "running": len([j for j in self.jobs.values() if j.status == JobStatus.RUNNING]),
                "scheduled": len([j for j in self.jobs.values() if j.status == JobStatus.SCHEDULED]),
                "failed": len([j for j in self.jobs.values() if j.status == JobStatus.FAILED])
            }
        }
    
    def get_recent_runs(self, limit: int = 10) -> List[ScrapingRun]:
        """Get recent run history"""
        return sorted(self.runs, key=lambda r: r.started_at, reverse=True)[:limit]
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for admin dashboard"""
        return {
            "status": self.get_status(),
            "jobs": [asdict(j) for j in self.jobs.values()],
            "recent_runs": [asdict(r) for r in self.get_recent_runs(10)],
            "next_scheduled": self._get_next_scheduled_jobs(5),
            "sources": {
                source.value: len([j for j in self.jobs.values() if j.source == source])
                for source in ScrapingSource
            }
        }
    
    def _get_next_scheduled_jobs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get next scheduled jobs"""
        scheduled = [
            {"job_id": j.id, "name": j.name, "next_run": j.next_run, "source": j.source.value}
            for j in self.jobs.values()
            if j.enabled and j.next_run and j.status == JobStatus.SCHEDULED
        ]
        return sorted(scheduled, key=lambda x: x["next_run"])[:limit]


# ===========================================
# Singleton Instance
# ===========================================

scraping_scheduler = ScrapingScheduler()
