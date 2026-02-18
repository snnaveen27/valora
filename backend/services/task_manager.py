"""
Task Manager Service - Manages long-running report generation tasks
Provides task creation, progress tracking, and result storage
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskProgress:
    """Progress information for a task"""
    current_step: int = 0
    total_steps: int = 0
    current_tab: str = ""
    completed_tabs: List[str] = field(default_factory=list)
    percentage: float = 0.0
    message: str = ""
    started_at: Optional[datetime] = None
    estimated_remaining_seconds: Optional[int] = None


@dataclass
class Task:
    """Represents a long-running task"""
    task_id: str
    task_type: str
    status: TaskStatus
    progress: TaskProgress
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    credits_charged: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for API response"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "progress": {
                "current": self.progress.current_step,
                "total": self.progress.total_steps,
                "percentage": round(self.progress.percentage, 1),
                "current_tab": self.progress.current_tab,
                "completed_tabs": self.progress.completed_tabs,
                "message": self.progress.message,
                "estimated_remaining_seconds": self.progress.estimated_remaining_seconds
            },
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "user_id": self.user_id,
            "credits_charged": self.credits_charged
        }


class TaskManager:
    """
    Manages long-running tasks with progress tracking
    
    Features:
    - Task creation and tracking
    - Progress updates
    - Result storage
    - Task cancellation
    - Automatic cleanup of old tasks
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.tasks: Dict[str, Task] = {}
        self._cleanup_interval = 3600  # 1 hour
        self._task_ttl = 86400  # 24 hours
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_old_tasks())
        
        logger.info("TaskManager initialized")
    
    def create_task(
        self,
        task_type: str,
        total_steps: int,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        credits_charged: int = 0
    ) -> Task:
        """
        Create a new task
        
        Args:
            task_type: Type of task (e.g., 'report_generation')
            total_steps: Total number of steps in the task
            user_id: Optional user ID for the task
            metadata: Optional metadata for the task
            credits_charged: Credits charged for this task
            
        Returns:
            Task: The created task
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        
        progress = TaskProgress(
            current_step=0,
            total_steps=total_steps,
            current_tab="initializing",
            message="Task created, waiting to start..."
        )
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            progress=progress,
            user_id=user_id,
            metadata=metadata or {},
            credits_charged=credits_charged
        )
        
        self.tasks[task_id] = task
        logger.info(f"Created task {task_id} of type {task_type}")
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.tasks.get(task_id)
    
    def update_progress(
        self,
        task_id: str,
        current_step: Optional[int] = None,
        current_tab: Optional[str] = None,
        message: Optional[str] = None,
        completed_tab: Optional[str] = None
    ) -> bool:
        """
        Update task progress
        
        Args:
            task_id: Task ID to update
            current_step: Current step number
            current_tab: Current tab being processed
            message: Progress message
            completed_tab: Tab that was just completed
            
        Returns:
            bool: True if update was successful
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for progress update")
            return False
        
        if current_step is not None:
            task.progress.current_step = current_step
            
        if current_tab is not None:
            task.progress.current_tab = current_tab
            
        if message is not None:
            task.progress.message = message
            
        if completed_tab is not None:
            if completed_tab not in task.progress.completed_tabs:
                task.progress.completed_tabs.append(completed_tab)
        
        # Calculate percentage
        if task.progress.total_steps > 0:
            task.progress.percentage = (task.progress.current_step / task.progress.total_steps) * 100
        
        # Estimate remaining time
        if task.progress.started_at and task.progress.current_step > 0:
            elapsed = (datetime.now() - task.progress.started_at).total_seconds()
            time_per_step = elapsed / task.progress.current_step
            remaining_steps = task.progress.total_steps - task.progress.current_step
            task.progress.estimated_remaining_seconds = int(time_per_step * remaining_steps)
        
        task.updated_at = datetime.now()
        task.status = TaskStatus.PROCESSING
        
        logger.debug(f"Updated task {task_id}: {task.progress.percentage:.1f}% - {task.progress.current_tab}")
        return True
    
    def start_task(self, task_id: str) -> bool:
        """Mark task as started"""
        task = self.tasks.get(task_id)
        if not task:
            return False
            
        task.status = TaskStatus.PROCESSING
        task.progress.started_at = datetime.now()
        task.progress.message = "Processing..."
        task.updated_at = datetime.now()
        
        logger.info(f"Started task {task_id}")
        return True
    
    def complete_task(self, task_id: str, result: Dict[str, Any]) -> bool:
        """Mark task as completed with result"""
        task = self.tasks.get(task_id)
        if not task:
            return False
            
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.progress.current_step = task.progress.total_steps
        task.progress.percentage = 100.0
        task.progress.message = "Task completed successfully"
        task.updated_at = datetime.now()
        
        logger.info(f"Completed task {task_id}")
        return True
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark task as failed with error message"""
        task = self.tasks.get(task_id)
        if not task:
            return False
            
        task.status = TaskStatus.FAILED
        task.error = error
        task.progress.message = f"Task failed: {error}"
        task.updated_at = datetime.now()
        
        logger.error(f"Failed task {task_id}: {error}")
        return True
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        task = self.tasks.get(task_id)
        if not task:
            return False
            
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            return False
            
        task.status = TaskStatus.CANCELLED
        task.progress.message = "Task cancelled by user"
        task.updated_at = datetime.now()
        
        # Cancel the async task if running
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            del self._running_tasks[task_id]
        
        logger.info(f"Cancelled task {task_id}")
        return True
    
    def register_async_task(self, task_id: str, async_task: asyncio.Task):
        """Register an asyncio task for cancellation support"""
        self._running_tasks[task_id] = async_task
    
    async def _cleanup_old_tasks(self):
        """Periodically clean up old tasks"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                
                now = datetime.now()
                expired_tasks = [
                    task_id for task_id, task in self.tasks.items()
                    if (now - task.created_at).total_seconds() > self._task_ttl
                ]
                
                for task_id in expired_tasks:
                    del self.tasks[task_id]
                    if task_id in self._running_tasks:
                        del self._running_tasks[task_id]
                    
                if expired_tasks:
                    logger.info(f"Cleaned up {len(expired_tasks)} expired tasks")
                    
            except Exception as e:
                logger.error(f"Error in task cleanup: {e}")


# Singleton instance
_task_manager = None


def get_task_manager() -> TaskManager:
    """Get the singleton TaskManager instance"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
