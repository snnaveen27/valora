"""
Task Dependency Graph - DAG-based Task Orchestration
Implements proper dependency management with cycle detection and parallel execution support.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict, deque
import asyncio
import json


@dataclass
class TaskNode:
    """
    A node in the task dependency graph.
    Represents a single task with its execution state.
    """
    id: str
    action: str                          # e.g., search, analyze, compare, navigate
    entity: str                          # e.g., property, area, POI
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_span: str = ""                # Original text that generated this task
    dependencies: List[str] = field(default_factory=list)
    
    # Execution state
    status: str = "pending"              # pending, running, completed, failed, cancelled
    priority: int = 1                    # 1=high, 2=medium, 3=low
    estimated_duration_ms: int = 1000
    actual_duration_ms: Optional[int] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Task type for execution routing
    task_type: str = "generic"           # map_action, gis_operation, llm_call, data_fetch
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "action": self.action,
            "entity": self.entity,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "source_span": self.source_span,
            "dependencies": self.dependencies,
            "status": self.status,
            "priority": self.priority,
            "estimated_duration_ms": self.estimated_duration_ms,
            "actual_duration_ms": self.actual_duration_ms,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "task_type": self.task_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskNode":
        """Create TaskNode from dictionary"""
        return cls(
            id=data["id"],
            action=data["action"],
            entity=data.get("entity", ""),
            parameters=data.get("parameters", {}),
            confidence=data.get("confidence", 1.0),
            source_span=data.get("source_span", ""),
            dependencies=data.get("dependencies", []),
            status=data.get("status", "pending"),
            priority=data.get("priority", 1),
            estimated_duration_ms=data.get("estimated_duration_ms", 1000),
            actual_duration_ms=data.get("actual_duration_ms"),
            result=data.get("result"),
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 2),
            created_at=data.get("created_at", datetime.now().isoformat()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            task_type=data.get("task_type", "generic")
        )


class TaskDependencyGraph:
    """
    Directed Acyclic Graph for task dependencies.
    Supports cycle detection, topological sorting, and parallel task grouping.
    """
    
    def __init__(self):
        self.nodes: Dict[str, TaskNode] = {}
        self.edges: Dict[str, Set[str]] = defaultdict(set)    # task_id -> set of dependent task ids
        self.reverse_edges: Dict[str, Set[str]] = defaultdict(set)  # task_id -> set of tasks that depend on it
        
        # Execution tracking
        self._execution_levels: Optional[List[List[str]]] = None
        self._current_level: int = 0
        
    def add_task(self, task: TaskNode) -> bool:
        """
        Add a task node to the graph.
        Returns True if successful, False if task ID already exists.
        """
        if task.id in self.nodes:
            return False
        
        self.nodes[task.id] = task
        
        # Add dependency edges
        for dep_id in task.dependencies:
            if dep_id in self.nodes:
                self.edges[dep_id].add(task.id)
                self.reverse_edges[task.id].add(dep_id)
        
        # Invalidate cached execution levels
        self._execution_levels = None
        
        return True
    
    def remove_task(self, task_id: str) -> bool:
        """
        Remove a task from the graph.
        Returns True if successful, False if task not found.
        """
        if task_id not in self.nodes:
            return False
        
        # Remove all edges involving this task
        for dep_id in list(self.reverse_edges[task_id]):
            self.edges[dep_id].discard(task_id)
        
        for dependent_id in list(self.edges[task_id]):
            self.reverse_edges[dependent_id].discard(task_id)
        
        # Remove from edge dictionaries
        del self.edges[task_id]
        del self.reverse_edges[task_id]
        
        # Remove node
        del self.nodes[task_id]
        
        # Invalidate cached execution levels
        self._execution_levels = None
        
        return True
    
    def update_dependencies(self, task_id: str, new_dependencies: List[str]) -> bool:
        """
        Update dependencies for a task.
        Returns True if successful, False if task not found or cycle detected.
        """
        if task_id not in self.nodes:
            return False
        
        # Store old dependencies
        old_deps = set(self.nodes[task_id].dependencies)
        new_deps = set(new_dependencies)
        
        # Temporarily update
        self.nodes[task_id].dependencies = new_dependencies
        
        # Update edges
        for dep_id in old_deps - new_deps:
            self.edges[dep_id].discard(task_id)
            self.reverse_edges[task_id].discard(dep_id)
        
        for dep_id in new_deps - old_deps:
            if dep_id in self.nodes:
                self.edges[dep_id].add(task_id)
                self.reverse_edges[task_id].add(dep_id)
        
        # Check for cycles
        if self.detect_cycles():
            # Revert changes
            self.nodes[task_id].dependencies = list(old_deps)
            for dep_id in new_deps - old_deps:
                self.edges[dep_id].discard(task_id)
                self.reverse_edges[task_id].discard(dep_id)
            for dep_id in old_deps - new_deps:
                if dep_id in self.nodes:
                    self.edges[dep_id].add(task_id)
                    self.reverse_edges[task_id].add(dep_id)
            return False
        
        # Invalidate cached execution levels
        self._execution_levels = None
        
        return True
    
    def detect_cycles(self) -> bool:
        """
        Detect if the graph contains any cycles.
        Uses DFS with coloring: WHITE (0), GRAY (1), BLACK (2)
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {task_id: WHITE for task_id in self.nodes}
        
        def dfs(node_id: str) -> bool:
            """Returns True if cycle detected"""
            color[node_id] = GRAY
            
            for neighbor in self.edges[node_id]:
                if color[neighbor] == GRAY:
                    return True  # Back edge found - cycle!
                if color[neighbor] == WHITE and dfs(neighbor):
                    return True
            
            color[node_id] = BLACK
            return False
        
        for task_id in self.nodes:
            if color[task_id] == WHITE:
                if dfs(task_id):
                    return True
        
        return False
    
    def topological_sort(self) -> List[str]:
        """
        Return tasks in topological order.
        Raises ValueError if graph contains cycles.
        """
        if self.detect_cycles():
            raise ValueError("Cannot perform topological sort on graph with cycles")
        
        # Kahn's algorithm
        in_degree = {task_id: 0 for task_id in self.nodes}
        
        for task_id in self.nodes:
            for dependent_id in self.edges[task_id]:
                in_degree[dependent_id] += 1
        
        # Start with nodes that have no dependencies
        queue = deque([task_id for task_id, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node_id = queue.popleft()
            result.append(node_id)
            
            for dependent_id in self.edges[node_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)
        
        return result
    
    def get_execution_levels(self) -> List[List[str]]:
        """
        Group tasks by execution level for parallel execution.
        Tasks in the same level can be executed concurrently.
        Returns list of lists, where each inner list is a level.
        """
        if self._execution_levels is not None:
            return self._execution_levels
        
        if self.detect_cycles():
            raise ValueError("Cannot compute execution levels on graph with cycles")
        
        # Calculate in-degree for each node
        in_degree = {task_id: len(self.reverse_edges[task_id]) for task_id in self.nodes}
        
        # Track which tasks are ready (all dependencies satisfied)
        ready = [task_id for task_id, degree in in_degree.items() if degree == 0]
        
        levels = []
        processed = set()
        
        while ready:
            # All ready tasks form the current level
            current_level = sorted(ready, key=lambda t: self.nodes[t].priority)
            levels.append(current_level)
            
            # Mark as processed
            processed.update(current_level)
            
            # Find next ready tasks
            next_ready = []
            for task_id in current_level:
                for dependent_id in self.edges[task_id]:
                    if dependent_id not in processed:
                        # Check if all dependencies are now satisfied
                        if all(dep in processed for dep in self.reverse_edges[dependent_id]):
                            if dependent_id not in next_ready:
                                next_ready.append(dependent_id)
            
            ready = next_ready
        
        self._execution_levels = levels
        return levels
    
    def get_parallel_tasks(self) -> List[List[TaskNode]]:
        """
        Get tasks grouped for parallel execution.
        Returns list of lists of TaskNode objects.
        """
        levels = self.get_execution_levels()
        return [[self.nodes[task_id] for task_id in level] for level in levels]
    
    def get_ready_tasks(self, completed: Set[str], running: Set[str]) -> List[TaskNode]:
        """
        Get tasks that are ready to execute given current state.
        A task is ready if all its dependencies are completed and it's not already running/completed.
        """
        ready = []
        for task_id, task in self.nodes.items():
            if task_id in completed or task_id in running:
                continue
            if task.status != "pending":
                continue
            
            # Check all dependencies are completed
            if all(dep_id in completed for dep_id in self.reverse_edges[task_id]):
                ready.append(task)
        
        # Sort by priority
        return sorted(ready, key=lambda t: t.priority)
    
    def get_dependent_tasks(self, task_id: str) -> List[str]:
        """Get all tasks that depend on the given task"""
        return list(self.edges[task_id])
    
    def get_dependencies(self, task_id: str) -> List[str]:
        """Get all dependencies of the given task"""
        return list(self.reverse_edges[task_id])
    
    def mark_task_running(self, task_id: str) -> bool:
        """Mark a task as running"""
        if task_id not in self.nodes:
            return False
        self.nodes[task_id].status = "running"
        self.nodes[task_id].started_at = datetime.now().isoformat()
        return True
    
    def mark_task_completed(self, task_id: str, result: Any = None) -> bool:
        """Mark a task as completed with optional result"""
        if task_id not in self.nodes:
            return False
        self.nodes[task_id].status = "completed"
        self.nodes[task_id].result = result
        self.nodes[task_id].completed_at = datetime.now().isoformat()
        return True
    
    def mark_task_failed(self, task_id: str, error: str) -> bool:
        """Mark a task as failed with error message"""
        if task_id not in self.nodes:
            return False
        self.nodes[task_id].status = "failed"
        self.nodes[task_id].error = error
        self.nodes[task_id].completed_at = datetime.now().isoformat()
        return True
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        """Get the status of a task"""
        if task_id not in self.nodes:
            return None
        return self.nodes[task_id].status
    
    def get_progress(self) -> Dict[str, Any]:
        """Get overall progress statistics"""
        status_counts = defaultdict(int)
        for task in self.nodes.values():
            status_counts[task.status] += 1
        
        total = len(self.nodes)
        completed = status_counts["completed"]
        
        return {
            "total_tasks": total,
            "completed": completed,
            "running": status_counts["running"],
            "pending": status_counts["pending"],
            "failed": status_counts["failed"],
            "progress_percent": (completed / total * 100) if total > 0 else 0,
            "execution_levels": len(self.get_execution_levels()) if total > 0 else 0
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary"""
        return {
            "nodes": {task_id: task.to_dict() for task_id, task in self.nodes.items()},
            "edges": {task_id: list(deps) for task_id, deps in self.edges.items()},
            "execution_levels": self.get_execution_levels()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskDependencyGraph":
        """Deserialize graph from dictionary"""
        graph = cls()
        
        # Add all nodes first
        for task_id, task_data in data["nodes"].items():
            graph.add_task(TaskNode.from_dict(task_data))
        
        return graph
    
    def visualize_ascii(self) -> str:
        """Generate ASCII visualization of the graph"""
        levels = self.get_execution_levels()
        lines = ["Task Dependency Graph:", "=" * 40]
        
        for i, level in enumerate(levels):
            lines.append(f"\nLevel {i + 1}:")
            for task_id in level:
                task = self.nodes[task_id]
                deps = ", ".join(self.reverse_edges[task_id]) if self.reverse_edges[task_id] else "none"
                lines.append(f"  [{task.status}] {task_id} ({task.action}) - deps: {deps}")
        
        return "\n".join(lines)


class TaskGraphBuilder:
    """
    Builder class for constructing task dependency graphs.
    Provides fluent API for graph construction.
    
    Note: Each TaskGraphBuilder instance creates a fresh graph.
    For each new query, create a new TaskGraphBuilder instance.
    """
    
    def __init__(self):
        self.graph = TaskDependencyGraph()
        self._task_counter = 0
    
    def task(
        self,
        action: str,
        entity: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        priority: int = 1,
        task_type: str = "generic",
        confidence: float = 1.0,
        source_span: str = "",
        task_id: Optional[str] = None
    ) -> "TaskGraphBuilder":
        """Add a task to the graph"""
        self._task_counter += 1
        
        if task_id is None:
            task_id = f"t{self._task_counter}_{action}"
        
        task = TaskNode(
            id=task_id,
            action=action,
            entity=entity,
            parameters=parameters or {},
            dependencies=dependencies or [],
            priority=priority,
            task_type=task_type,
            confidence=confidence,
            source_span=source_span
        )
        
        self.graph.add_task(task)
        return self
    
    def build(self) -> TaskDependencyGraph:
        """Build and return the graph"""
        if self.graph.detect_cycles():
            raise ValueError("Built graph contains cycles")
        return self.graph
    
    def reset(self) -> "TaskGraphBuilder":
        """
        Reset builder for new graph.
        Note: It's recommended to create a new TaskGraphBuilder instance instead.
        """
        self.graph = TaskDependencyGraph()
        self._task_counter = 0
        return self


# Note: TaskDependencyGraph should NOT be a singleton - each query needs a fresh graph
# Use create_task_graph() for each new query to ensure clean state

def get_task_graph() -> TaskDependencyGraph:
    """
    Create a new TaskDependencyGraph instance.
    Note: This returns a NEW instance each time to ensure clean state for each query.
    """
    return TaskDependencyGraph()

def create_task_graph() -> TaskDependencyGraph:
    """Create a new TaskDependencyGraph instance (alias for get_task_graph)"""
    return TaskDependencyGraph()
