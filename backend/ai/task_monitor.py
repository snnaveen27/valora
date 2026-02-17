"""
Task Monitor - Real-time Task Progress Tracking
Provides monitoring, metrics collection, and progress reporting for task execution.
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import sqlite3
import os


class MetricType(Enum):
    """Types of metrics tracked"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class TaskMetric:
    """A single metric measurement"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp,
            "tags": self.tags
        }


@dataclass
class TaskExecutionRecord:
    """Record of a single task execution"""
    task_id: str
    execution_id: str
    action: str
    entity: str
    task_type: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: int = 0
    error: Optional[str] = None
    retry_count: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)
    result_summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "execution_id": self.execution_id,
            "action": self.action,
            "entity": self.entity,
            "task_type": self.task_type,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "retry_count": self.retry_count,
            "parameters": self.parameters,
            "result_summary": self.result_summary
        }


@dataclass
class ExecutionSession:
    """A complete execution session with multiple tasks"""
    session_id: str
    query: str
    intent: str
    started_at: str
    completed_at: Optional[str] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_duration_ms: int = 0
    success: bool = False
    task_records: List[TaskExecutionRecord] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "query": self.query,
            "intent": self.intent,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "total_duration_ms": self.total_duration_ms,
            "success": self.success,
            "task_records": [r.to_dict() for r in self.task_records]
        }


class TaskMonitor:
    """
    Real-time task monitoring and metrics collection.
    
    Features:
    - Task status tracking
    - Execution time metrics
    - Error rate tracking
    - Cache hit rate monitoring
    - Resource usage tracking
    - Historical data persistence
    """
    
    def __init__(self, db_path: str = "valora_monitoring.db", retention_days: int = 30):
        self.db_path = db_path
        self.retention_days = retention_days
        
        # Current session
        self._current_session: Optional[ExecutionSession] = None
        
        # Metrics storage
        self._metrics: List[TaskMetric] = []
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._timers: Dict[str, List[float]] = defaultdict(list)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Real-time stats
        self._task_status: Dict[str, str] = {}
        self._active_tasks: Dict[str, TaskExecutionRecord] = {}
        
        # Callbacks for real-time updates
        self._status_callbacks: List[Callable] = []
        self._metric_callbacks: List[Callable] = []
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for monitoring data"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # Execution sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_sessions (
                    session_id TEXT PRIMARY KEY,
                    query TEXT,
                    intent TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    total_tasks INTEGER,
                    completed_tasks INTEGER,
                    failed_tasks INTEGER,
                    total_duration_ms INTEGER,
                    success INTEGER
                )
            """)
            
            # Task executions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    execution_id TEXT,
                    session_id TEXT,
                    action TEXT,
                    entity TEXT,
                    task_type TEXT,
                    status TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_ms INTEGER,
                    error TEXT,
                    retry_count INTEGER,
                    parameters TEXT,
                    result_summary TEXT,
                    FOREIGN KEY (session_id) REFERENCES execution_sessions(session_id)
                )
            """)
            
            # Metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    value REAL,
                    type TEXT,
                    timestamp TEXT,
                    tags TEXT
                )
            """)
            
            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_started 
                ON execution_sessions(started_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_session 
                ON task_executions(session_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp 
                ON metrics(name, timestamp)
            """)
            
            conn.commit()
    
    def start_session(self, query: str, intent: str) -> str:
        """Start a new execution session"""
        # Reset per-session state to ensure clean state for each query
        self._task_status = {}
        self._active_tasks = {}
        
        session_id = f"session_{int(time.time() * 1000)}"
        
        self._current_session = ExecutionSession(
            session_id=session_id,
            query=query,
            intent=intent,
            started_at=datetime.now().isoformat()
        )
        
        # Persist session
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO execution_sessions 
                (session_id, query, intent, started_at, total_tasks, 
                 completed_tasks, failed_tasks, total_duration_ms, success)
                VALUES (?, ?, ?, ?, 0, 0, 0, 0, 0)
            """, (
                session_id,
                query,
                intent,
                self._current_session.started_at
            ))
            conn.commit()
        
        self._emit_status("session_started", {"session_id": session_id, "query": query})
        
        return session_id
    
    def end_session(self, success: bool = True) -> Optional[ExecutionSession]:
        """End the current execution session"""
        if not self._current_session:
            return None
        
        self._current_session.completed_at = datetime.now().isoformat()
        self._current_session.success = success
        
        # Calculate duration
        start = datetime.fromisoformat(self._current_session.started_at)
        end = datetime.fromisoformat(self._current_session.completed_at)
        self._current_session.total_duration_ms = int((end - start).total_seconds() * 1000)
        
        # Persist updates
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE execution_sessions 
                SET completed_at=?, total_tasks=?, completed_tasks=?, 
                    failed_tasks=?, total_duration_ms=?, success=?
                WHERE session_id=?
            """, (
                self._current_session.completed_at,
                self._current_session.total_tasks,
                self._current_session.completed_tasks,
                self._current_session.failed_tasks,
                self._current_session.total_duration_ms,
                1 if success else 0,
                self._current_session.session_id
            ))
            conn.commit()
        
        session = self._current_session
        self._current_session = None
        
        self._emit_status("session_ended", {"session_id": session.session_id, "success": success})
        
        return session
    
    def start_task(self, task: Any) -> str:
        """Record task start"""
        execution_id = f"exec_{task.id}_{int(time.time() * 1000)}"
        
        record = TaskExecutionRecord(
            task_id=task.id,
            execution_id=execution_id,
            action=task.action,
            entity=task.entity,
            task_type=task.task_type,
            status="running",
            started_at=datetime.now().isoformat(),
            parameters=task.parameters
        )
        
        self._active_tasks[task.id] = record
        self._task_status[task.id] = "running"
        
        if self._current_session:
            self._current_session.total_tasks += 1
        
        # Persist task start
        self._persist_task_start(record)
        
        self._emit_status("task_started", {"task_id": task.id, "action": task.action})
        
        return execution_id
    
    def complete_task(self, task_id: str, result: Any = None, error: str = None) -> None:
        """Record task completion"""
        if task_id not in self._active_tasks:
            return
        
        record = self._active_tasks[task_id]
        record.completed_at = datetime.now().isoformat()
        record.status = "failed" if error else "completed"
        record.error = error
        
        # Calculate duration
        start = datetime.fromisoformat(record.started_at)
        end = datetime.fromisoformat(record.completed_at)
        record.duration_ms = int((end - start).total_seconds() * 1000)
        
        # Extract result summary
        if result:
            if isinstance(result, dict):
                record.result_summary = result.get("summary", str(result)[:200])
            else:
                record.result_summary = str(result)[:200]
        
        # Update status
        self._task_status[task_id] = record.status
        del self._active_tasks[task_id]
        
        # Update session
        if self._current_session:
            self._current_session.task_records.append(record)
            if record.status == "completed":
                self._current_session.completed_tasks += 1
            else:
                self._current_session.failed_tasks += 1
        
        # Persist task completion
        self._persist_task_complete(record)
        
        # Record metrics
        self.record_metric(
            f"task_duration_{record.task_type}",
            record.duration_ms,
            MetricType.TIMER,
            {"action": record.action, "status": record.status}
        )
        
        self._emit_status("task_completed", {
            "task_id": task_id,
            "status": record.status,
            "duration_ms": record.duration_ms
        })
    
    def _persist_task_start(self, record: TaskExecutionRecord) -> None:
        """Persist task start to database"""
        session_id = self._current_session.session_id if self._current_session else None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO task_executions 
                (task_id, execution_id, session_id, action, entity, task_type, 
                 status, started_at, parameters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.task_id,
                record.execution_id,
                session_id,
                record.action,
                record.entity,
                record.task_type,
                record.status,
                record.started_at,
                json.dumps(record.parameters)
            ))
            conn.commit()
    
    def _persist_task_complete(self, record: TaskExecutionRecord) -> None:
        """Persist task completion to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE task_executions 
                SET status=?, completed_at=?, duration_ms=?, error=?, 
                    retry_count=?, result_summary=?
                WHERE execution_id=?
            """, (
                record.status,
                record.completed_at,
                record.duration_ms,
                record.error,
                record.retry_count,
                record.result_summary,
                record.execution_id
            ))
            conn.commit()
    
    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a metric measurement"""
        metric = TaskMetric(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags or {}
        )
        
        self._metrics.append(metric)
        
        # Update aggregated values
        if metric_type == MetricType.COUNTER:
            self._counters[name] += value
        elif metric_type == MetricType.GAUGE:
            self._gauges[name] = value
        elif metric_type == MetricType.TIMER:
            self._timers[name].append(value)
        elif metric_type == MetricType.HISTOGRAM:
            self._histograms[name].append(value)
        
        # Persist metric
        self._persist_metric(metric)
        
        # Emit callback
        self._emit_metric(metric)
    
    def _persist_metric(self, metric: TaskMetric) -> None:
        """Persist metric to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO metrics (name, value, type, timestamp, tags)
                VALUES (?, ?, ?, ?, ?)
            """, (
                metric.name,
                metric.value,
                metric.metric_type.value,
                metric.timestamp,
                json.dumps(metric.tags)
            ))
            conn.commit()
    
    def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric"""
        self.record_metric(name, 1, MetricType.COUNTER, tags)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric"""
        self.record_metric(name, value, MetricType.GAUGE, tags)
    
    def record_timer(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timer metric"""
        self.record_metric(name, duration_ms, MetricType.TIMER, tags)
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        """Get current status of a task"""
        return self._task_status.get(task_id)
    
    def get_active_tasks(self) -> List[str]:
        """Get list of currently active task IDs"""
        return list(self._active_tasks.keys())
    
    def get_session_progress(self) -> Dict[str, Any]:
        """Get progress of current session"""
        if not self._current_session:
            return {"active": False}
        
        return {
            "active": True,
            "session_id": self._current_session.session_id,
            "query": self._current_session.query,
            "total_tasks": self._current_session.total_tasks,
            "completed_tasks": self._current_session.completed_tasks,
            "failed_tasks": self._current_session.failed_tasks,
            "progress_percent": (
                self._current_session.completed_tasks / 
                max(1, self._current_session.total_tasks) * 100
            ),
            "active_tasks": list(self._active_tasks.keys())
        }
    
    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get aggregated statistics for the specified time period"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Session stats
            session_cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_sessions,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_sessions,
                    AVG(total_duration_ms) as avg_duration_ms,
                    SUM(total_tasks) as total_tasks,
                    SUM(completed_tasks) as completed_tasks,
                    SUM(failed_tasks) as failed_tasks
                FROM execution_sessions
                WHERE started_at >= ?
            """, (cutoff,))
            
            session_row = session_cursor.fetchone()
            
            # Task type stats
            task_cursor = conn.execute("""
                SELECT 
                    task_type,
                    COUNT(*) as count,
                    AVG(duration_ms) as avg_duration,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM task_executions
                WHERE started_at >= ?
                GROUP BY task_type
            """, (cutoff,))
            
            task_stats = []
            for row in task_cursor.fetchall():
                task_stats.append({
                    "task_type": row[0],
                    "count": row[1],
                    "avg_duration_ms": int(row[2] or 0),
                    "completed": row[3],
                    "failed": row[4],
                    "success_rate": row[3] / max(1, row[1])
                })
            
            # Error stats
            error_cursor = conn.execute("""
                SELECT error, COUNT(*) as count
                FROM task_executions
                WHERE status = 'failed' AND started_at >= ?
                GROUP BY error
                ORDER BY count DESC
                LIMIT 10
            """, (cutoff,))
            
            errors = [{"error": row[0], "count": row[1]} for row in error_cursor.fetchall()]
        
        total_sessions = session_row[0] or 0
        successful_sessions = session_row[1] or 0
        
        return {
            "period_hours": hours,
            "sessions": {
                "total": total_sessions,
                "successful": successful_sessions,
                "success_rate": successful_sessions / max(1, total_sessions),
                "avg_duration_ms": int(session_row[2] or 0)
            },
            "tasks": {
                "total": session_row[3] or 0,
                "completed": session_row[4] or 0,
                "failed": session_row[5] or 0,
                "by_type": task_stats
            },
            "top_errors": errors,
            "counters": dict(self._counters),
            "gauges": dict(self._gauges)
        }
    
    def get_timer_statistics(self, name: str) -> Dict[str, float]:
        """Get statistics for a timer metric"""
        values = self._timers.get(name, [])
        
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p95": 0}
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        
        return {
            "count": count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "avg": sum(sorted_values) / count,
            "p95": sorted_values[int(count * 0.95)] if count > 0 else 0
        }
    
    def register_status_callback(self, callback: Callable) -> None:
        """Register a callback for status updates"""
        self._status_callbacks.append(callback)
    
    def register_metric_callback(self, callback: Callable) -> None:
        """Register a callback for metric updates"""
        self._metric_callbacks.append(callback)
    
    def _emit_status(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit status event to callbacks"""
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            **data
        }
        
        for callback in self._status_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(event))
                else:
                    callback(event)
            except Exception as e:
                print(f"[TaskMonitor] Callback error: {e}")
    
    def _emit_metric(self, metric: TaskMetric) -> None:
        """Emit metric to callbacks"""
        for callback in self._metric_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(metric.to_dict()))
                else:
                    callback(metric.to_dict())
            except Exception as e:
                print(f"[TaskMonitor] Callback error: {e}")
    
    def cleanup_old_data(self) -> int:
        """Remove data older than retention period"""
        cutoff = (datetime.now() - timedelta(days=self.retention_days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Delete old metrics
            conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff,))
            
            # Delete old task executions
            conn.execute("DELETE FROM task_executions WHERE started_at < ?", (cutoff,))
            
            # Delete old sessions
            conn.execute("DELETE FROM execution_sessions WHERE started_at < ?", (cutoff,))
            
            conn.commit()
            
            # Get deleted count
            cursor = conn.execute("SELECT changes()")
            deleted = cursor.fetchone()[0]
        
        return deleted
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        data = {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "timers": {k: self.get_timer_statistics(k) for k in self._timers},
            "histograms": dict(self._histograms)
        }
        
        if format == "json":
            return json.dumps(data, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")


# Singleton instance for TaskMonitor (stateless between queries - uses DB for persistence)
_monitor_instance: Optional[TaskMonitor] = None

def get_task_monitor(db_path: str = "valora_monitoring.db") -> TaskMonitor:
    """
    Get or create singleton TaskMonitor instance.
    Note: TaskMonitor uses database for persistence and resets in-memory state 
    for each session via start_session()/end_session() calls.
    """
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = TaskMonitor(db_path=db_path)
    return _monitor_instance
