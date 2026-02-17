"""
Parallel Task Executor - Concurrent Task Execution Engine
Executes tasks in parallel based on dependency graph levels.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import traceback


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class TaskResult:
    """Result of a single task execution"""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    status: TaskStatus = TaskStatus.COMPLETED
    retry_count: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


@dataclass
class ExecutionResult:
    """Result of executing a task graph"""
    success: bool
    task_results: List[TaskResult]
    total_duration_ms: int
    tasks_completed: int
    tasks_failed: int
    tasks_skipped: int
    parallel_levels: int
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "task_results": [r.to_dict() for r in self.task_results],
            "total_duration_ms": self.total_duration_ms,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "tasks_skipped": self.tasks_skipped,
            "parallel_levels": self.parallel_levels,
            "execution_log": self.execution_log
        }


class ParallelTaskExecutor:
    """
    Executes tasks in parallel based on dependency graph.
    
    Features:
    - Concurrent execution of independent tasks
    - Semaphore-based concurrency limiting
    - Automatic retry with exponential backoff
    - Progress streaming via callbacks
    - Graceful failure handling
    """
    
    def __init__(
        self,
        max_concurrent: int = 4,
        default_timeout: float = 30.0,
        max_retries: int = 2,
        retry_delay: float = 1.0
    ):
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Execution state
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._completed_tasks: Set[str] = set()
        self._failed_tasks: Set[str] = set()
        self._running_tasks: Set[str] = set()
        self._results: Dict[str, TaskResult] = {}
        
        # Callbacks
        self._on_task_start: Optional[Callable] = None
        self._on_task_complete: Optional[Callable] = None
        self._on_task_fail: Optional[Callable] = None
        self._on_level_start: Optional[Callable] = None
        self._on_level_complete: Optional[Callable] = None
        
        # Task executors registry
        self._executors: Dict[str, Callable] = {}
        
        # Statistics
        self._total_executed = 0
        self._total_successful = 0
        self._total_failed = 0
    
    def register_executor(self, task_type: str, executor: Callable) -> None:
        """Register an executor function for a task type"""
        self._executors[task_type] = executor
    
    def set_callbacks(
        self,
        on_task_start: Optional[Callable] = None,
        on_task_complete: Optional[Callable] = None,
        on_task_fail: Optional[Callable] = None,
        on_level_start: Optional[Callable] = None,
        on_level_complete: Optional[Callable] = None
    ) -> None:
        """Set callback functions for execution events"""
        self._on_task_start = on_task_start
        self._on_task_complete = on_task_complete
        self._on_task_fail = on_task_fail
        self._on_level_start = on_level_start
        self._on_level_complete = on_level_complete
    
    async def execute_graph(
        self,
        graph: Any,  # TaskDependencyGraph
        timeout: Optional[float] = None
    ) -> ExecutionResult:
        """
        Execute all tasks in the dependency graph.
        
        Args:
            graph: TaskDependencyGraph instance
            timeout: Overall execution timeout
        
        Returns:
            ExecutionResult with all task results
        """
        start_time = time.time()
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Reset state
        self._completed_tasks = set()
        self._failed_tasks = set()
        self._running_tasks = set()
        self._results = {}
        
        execution_log = []
        task_results = []
        
        try:
            # Get execution levels
            levels = graph.get_parallel_tasks()
            total_levels = len(levels)
            
            # Execute level by level
            for level_idx, level_tasks in enumerate(levels):
                level_start = time.time()
                
                # Notify level start
                if self._on_level_start:
                    await self._safe_callback(
                        self._on_level_start,
                        level_idx + 1,
                        total_levels,
                        [t.id for t in level_tasks]
                    )
                
                execution_log.append({
                    "event": "level_start",
                    "level": level_idx + 1,
                    "tasks": [t.id for t in level_tasks],
                    "timestamp": datetime.now().isoformat()
                })
                
                # Execute tasks in this level concurrently
                level_results = await asyncio.gather(
                    *[self._execute_task_with_retry(task) for task in level_tasks],
                    return_exceptions=True
                )
                
                # Process results
                for task, result in zip(level_tasks, level_results):
                    if isinstance(result, Exception):
                        result = TaskResult(
                            task_id=task.id,
                            success=False,
                            error=str(result),
                            status=TaskStatus.FAILED
                        )
                    
                    self._results[task.id] = result
                    task_results.append(result)
                    
                    if result.success:
                        self._completed_tasks.add(task.id)
                        graph.mark_task_completed(task.id, result.result)
                    else:
                        self._failed_tasks.add(task.id)
                        graph.mark_task_failed(task.id, result.error or "Unknown error")
                
                level_duration = int((time.time() - level_start) * 1000)
                
                # Notify level complete
                if self._on_level_complete:
                    await self._safe_callback(
                        self._on_level_complete,
                        level_idx + 1,
                        total_levels,
                        level_duration
                    )
                
                execution_log.append({
                    "event": "level_complete",
                    "level": level_idx + 1,
                    "duration_ms": level_duration,
                    "tasks_completed": len([r for r in level_results if isinstance(r, TaskResult) and r.success]),
                    "tasks_failed": len([r for r in level_results if isinstance(r, TaskResult) and not r.success])
                })
                
                # Check if we should stop due to failures
                failed_critical = any(
                    not result.success and self._is_critical_task(level_tasks[i])
                    for i, result in enumerate(level_results)
                    if isinstance(result, TaskResult)
                )
                
                if failed_critical:
                    # Cancel remaining tasks
                    execution_log.append({
                        "event": "execution_stopped",
                        "reason": "critical_task_failed",
                        "timestamp": datetime.now().isoformat()
                    })
                    break
        
        except asyncio.TimeoutError:
            execution_log.append({
                "event": "timeout",
                "timestamp": datetime.now().isoformat()
            })
        
        total_duration = int((time.time() - start_time) * 1000)
        
        # Calculate statistics
        completed = len(self._completed_tasks)
        failed = len(self._failed_tasks)
        skipped = len(graph.nodes) - completed - failed
        
        # Update global stats
        self._total_executed += len(task_results)
        self._total_successful += completed
        self._total_failed += failed
        
        return ExecutionResult(
            success=failed == 0,
            task_results=task_results,
            total_duration_ms=total_duration,
            tasks_completed=completed,
            tasks_failed=failed,
            tasks_skipped=skipped,
            parallel_levels=len(levels) if 'levels' in dir() else 0,
            execution_log=execution_log
        )
    
    async def _execute_task_with_retry(self, task: Any) -> TaskResult:
        """Execute a single task with retry logic"""
        async with self._semaphore:
            self._running_tasks.add(task.id)
            
            # Notify task start
            if self._on_task_start:
                await self._safe_callback(self._on_task_start, task)
            
            started_at = datetime.now().isoformat()
            start_time = time.time()
            
            for attempt in range(task.max_retries + 1):
                try:
                    # Get executor for task type
                    executor = self._executors.get(task.task_type)
                    
                    if executor:
                        result = await asyncio.wait_for(
                            executor(task),
                            timeout=self.default_timeout
                        )
                    else:
                        # Default execution
                        result = await self._default_executor(task)
                    
                    duration = int((time.time() - start_time) * 1000)
                    
                    task_result = TaskResult(
                        task_id=task.id,
                        success=True,
                        result=result,
                        duration_ms=duration,
                        status=TaskStatus.COMPLETED,
                        retry_count=attempt,
                        started_at=started_at,
                        completed_at=datetime.now().isoformat()
                    )
                    
                    # Notify task complete
                    if self._on_task_complete:
                        await self._safe_callback(self._on_task_complete, task, task_result)
                    
                    return task_result
                    
                except asyncio.TimeoutError:
                    error_msg = f"Task timed out after {self.default_timeout}s"
                    
                except Exception as e:
                    error_msg = f"{str(e)}\n{traceback.format_exc()}"
                
                # Retry with exponential backoff
                if attempt < task.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(wait_time)
            
            # All retries exhausted
            duration = int((time.time() - start_time) * 1000)
            
            task_result = TaskResult(
                task_id=task.id,
                success=False,
                error=error_msg,
                duration_ms=duration,
                status=TaskStatus.FAILED,
                retry_count=task.max_retries,
                started_at=started_at,
                completed_at=datetime.now().isoformat()
            )
            
            # Notify task fail
            if self._on_task_fail:
                await self._safe_callback(self._on_task_fail, task, task_result)
            
            return task_result
    
    async def _default_executor(self, task: Any) -> Dict[str, Any]:
        """Default executor for tasks without registered executors"""
        return {
            "task_id": task.id,
            "action": task.action,
            "status": "completed",
            "summary": f"Executed {task.action} on {task.entity}"
        }
    
    async def _safe_callback(self, callback: Callable, *args) -> None:
        """Safely execute a callback, catching any exceptions"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            print(f"[ParallelExecutor] Callback error: {e}")
    
    def _is_critical_task(self, task: Any) -> bool:
        """Check if a task is critical (failure should stop execution)"""
        # Tasks with priority 1 are considered critical
        return task.priority == 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get executor statistics"""
        return {
            "total_executed": self._total_executed,
            "total_successful": self._total_successful,
            "total_failed": self._total_failed,
            "success_rate": self._total_successful / max(1, self._total_executed),
            "max_concurrent": self.max_concurrent,
            "default_timeout": self.default_timeout
        }
    
    async def execute_single_task(
        self,
        task: Any,
        executor: Optional[Callable] = None
    ) -> TaskResult:
        """
        Execute a single task outside of graph context.
        
        Args:
            task: Task to execute
            executor: Optional executor function
        
        Returns:
            TaskResult
        """
        if executor:
            self._executors[task.task_type] = executor
        
        return await self._execute_task_with_retry(task)


class StreamingExecutor(ParallelTaskExecutor):
    """
    Extended executor with streaming progress events.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._event_queue: Optional[asyncio.Queue] = None
    
    async def execute_graph_streaming(
        self,
        graph: Any,
        timeout: Optional[float] = None
    ):
        """
        Execute graph and yield progress events.
        
        Yields:
            Dict events with progress information
        """
        self._event_queue = asyncio.Queue()
        
        # Start execution in background
        execution_task = asyncio.create_task(
            self._execute_with_events(graph, timeout)
        )
        
        # Yield events as they come
        while True:
            event = await self._event_queue.get()
            yield event
            
            if event.get("type") == "execution_complete":
                break
        
        # Get final result
        result = await execution_task
        yield {
            "type": "final_result",
            "result": result.to_dict()
        }
    
    async def _execute_with_events(
        self,
        graph: Any,
        timeout: Optional[float]
    ) -> ExecutionResult:
        """Execute with event emission"""
        
        async def on_task_start(task):
            await self._event_queue.put({
                "type": "task_start",
                "task_id": task.id,
                "action": task.action,
                "timestamp": datetime.now().isoformat()
            })
        
        async def on_task_complete(task, result):
            await self._event_queue.put({
                "type": "task_complete",
                "task_id": task.id,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "timestamp": datetime.now().isoformat()
            })
        
        async def on_task_fail(task, result):
            await self._event_queue.put({
                "type": "task_fail",
                "task_id": task.id,
                "error": result.error,
                "timestamp": datetime.now().isoformat()
            })
        
        async def on_level_start(level, total, tasks):
            await self._event_queue.put({
                "type": "level_start",
                "level": level,
                "total_levels": total,
                "tasks": tasks,
                "timestamp": datetime.now().isoformat()
            })
        
        async def on_level_complete(level, total, duration_ms):
            await self._event_queue.put({
                "type": "level_complete",
                "level": level,
                "total_levels": total,
                "duration_ms": duration_ms,
                "timestamp": datetime.now().isoformat()
            })
        
        self.set_callbacks(
            on_task_start=on_task_start,
            on_task_complete=on_task_complete,
            on_task_fail=on_task_fail,
            on_level_start=on_level_start,
            on_level_complete=on_level_complete
        )
        
        result = await self.execute_graph(graph, timeout)
        
        await self._event_queue.put({
            "type": "execution_complete",
            "success": result.success,
            "total_duration_ms": result.total_duration_ms,
            "tasks_completed": result.tasks_completed,
            "tasks_failed": result.tasks_failed
        })
        
        return result


# Note: ParallelTaskExecutor should NOT be a singleton - each execution needs fresh state
# Use create_parallel_executor() for each new execution to ensure clean state

def get_parallel_executor(
    max_concurrent: int = 4,
    default_timeout: float = 30.0
) -> ParallelTaskExecutor:
    """
    Create a new ParallelTaskExecutor instance.
    Note: This returns a NEW instance each time to ensure clean state for each execution.
    """
    return ParallelTaskExecutor(
        max_concurrent=max_concurrent,
        default_timeout=default_timeout
    )

def create_parallel_executor(
    max_concurrent: int = 4,
    default_timeout: float = 30.0
) -> ParallelTaskExecutor:
    """Create a new ParallelTaskExecutor instance (alias for get_parallel_executor)"""
    return ParallelTaskExecutor(
        max_concurrent=max_concurrent,
        default_timeout=default_timeout
    )

def create_streaming_executor(
    max_concurrent: int = 4,
    default_timeout: float = 30.0
) -> StreamingExecutor:
    """Create a new StreamingExecutor instance"""
    return StreamingExecutor(
        max_concurrent=max_concurrent,
        default_timeout=default_timeout
    )
