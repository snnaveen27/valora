"""
Task Orchestrator - Unified Task Orchestration Layer
Coordinates decomposition, execution, monitoring, and learning for all tasks.

Core Architecture: Multi-Stage LLM Execution
- UNDERSTAND: Parse query, extract intent, entities, constraints
- PLAN: Generate task graph with dependencies
- EXECUTE: Run tasks with LLM reasoning at each step
- VALIDATE: Verify results, detect gaps, retry if needed
- SYNTHESIZE: Generate final response with all insights
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json

from ai.task_graph import TaskDependencyGraph, TaskNode, TaskGraphBuilder
from ai.task_templates import TaskTemplate, TemplateLibrary, get_template_library
from ai.task_decomposer import TaskDecomposer, DecompositionResult, DecomposedTask, get_task_decomposer
from ai.parallel_executor import (
    ParallelTaskExecutor, 
    StreamingExecutor, 
    ExecutionResult,
    TaskResult,
    get_parallel_executor,
    create_streaming_executor
)
from ai.task_monitor import TaskMonitor, get_task_monitor
from ai.template_generator import TemplateGenerator, get_template_generator
from ai.multi_stage_executor import (
    MultiStageLLMExecutor, 
    MultiStageConfig, 
    ExecutionStage,
    get_multi_stage_executor
)
from config import config, TaskConfig


@dataclass
class OrchestratorResult:
    """Complete result from task orchestration"""
    query: str
    intent: str
    decomposition: DecompositionResult
    execution: ExecutionResult
    graph: Optional[TaskDependencyGraph] = None
    template_used: Optional[str] = None
    total_time_ms: int = 0
    success: bool = False
    narrative: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "decomposition": {
                "method": self.decomposition.method,
                "confidence": self.decomposition.overall_confidence,
                "task_count": len(self.decomposition.tasks)
            },
            "execution": self.execution.to_dict() if self.execution else None,
            "template_used": self.template_used,
            "total_time_ms": self.total_time_ms,
            "success": self.success,
            "narrative": self.narrative
        }


class TaskOrchestrator:
    """
    Unified task orchestration layer with Multi-Stage LLM Execution as core architecture.
    
    Core Architecture - Multi-Stage LLM Execution:
    1. UNDERSTAND - Parse query, extract intent, entities, constraints
    2. PLAN - Generate task graph with dependencies
    3. EXECUTE - Run tasks with LLM reasoning at each step
    4. VALIDATE - Verify results, detect gaps, retry if needed
    5. SYNTHESIZE - Generate final response with all insights
    
    Legacy Support:
    - Task decomposition from natural language (fallback)
    - Dependency graph construction
    - Parallel task execution
    - Progress monitoring and metrics
    - Template learning and generation
    
    Note: Each call to process() or process_streaming() creates fresh instances
    of the graph and executor to ensure clean state for each query.
    """
    
    def __init__(
        self,
        task_config: Optional[TaskConfig] = None,
        template_library: Optional[TemplateLibrary] = None,
        task_monitor: Optional[TaskMonitor] = None,
        llm_client: Optional[Any] = None
    ):
        self.config = task_config or config.TASK_CONFIG
        self.llm_client = llm_client
        
        # Initialize components - these are stateless or use DB for persistence
        self.template_library = template_library or get_template_library(
            str(config.TEMPLATE_DB_PATH)
        )
        
        self.task_decomposer = TaskDecomposer(
            template_library=self.template_library,
            llm_client=llm_client,
            confidence_threshold=self.config.DECOMPOSITION_CONFIDENCE_THRESHOLD,
            max_tasks_per_query=self.config.MAX_TASKS_PER_QUERY
        )
        
        self.task_monitor = task_monitor or get_task_monitor(
            str(config.MONITORING_DB_PATH)
        )
        
        self.template_generator = TemplateGenerator(
            template_library=self.template_library,
            min_samples=self.config.TEMPLATE_MIN_EXECUTIONS,
            min_success_rate=self.config.TEMPLATE_MIN_SUCCESS_RATE
        )
        
        # Task executors registry - these are stateless functions
        self._task_executors: Dict[str, Callable] = {}
        
        # Statistics - cumulative across all queries
        self._queries_processed = 0
        self._successful_queries = 0
        self._total_tasks_executed = 0
    
    def register_task_executor(self, task_type: str, executor: Callable) -> None:
        """Register an executor function for a task type"""
        self._task_executors[task_type] = executor
    
    def _create_multi_stage_executor(self) -> MultiStageLLMExecutor:
        """Create a configured multi-stage executor instance"""
        ms_config = MultiStageConfig(
            max_retries_per_stage=self.config.MAX_RETRIES,
            min_confidence_threshold=self.config.DECOMPOSITION_CONFIDENCE_THRESHOLD,
            enable_parallel_execution=self.config.is_enabled("parallel_task_execution"),
            max_concurrent_tasks=self.config.MAX_CONCURRENT_TASKS,
            timeout_per_stage_ms=self.config.TASK_TIMEOUT_SECONDS * 1000,
            enable_validation_loops=True,
            max_validation_loops=3
        )
        
        return MultiStageLLMExecutor(
            llm_client=self.llm_client,
            config=ms_config,
            tools_registry=self._task_executors.copy()
        )
    
    async def process(
        self,
        query: str,
        intent: str,
        slots: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> OrchestratorResult:
        """
        Process a query through the multi-stage LLM execution pipeline.
        
        Core Architecture - Multi-Stage Execution:
        1. UNDERSTAND - Parse query, extract intent, entities, constraints
        2. PLAN - Generate task graph with dependencies
        3. EXECUTE - Run tasks with LLM reasoning at each step
        4. VALIDATE - Verify results, detect gaps, retry if needed
        5. SYNTHESIZE - Generate final response with all insights
        
        Args:
            query: User's natural language query
            intent: Detected intent
            slots: Extracted slots/entities
            context: Additional context from conversation
        
        Returns:
            OrchestratorResult with complete execution details
        """
        start_time = time.time()
        self._queries_processed += 1
        
        # Start monitoring session
        session_id = self.task_monitor.start_session(query, intent)
        
        try:
            # Use multi-stage executor as core architecture
            if self.config.is_enabled("nlp_task_decomposition") and self.llm_client:
                return await self._process_multi_stage(query, intent, slots, context, start_time)
            
            # Fallback to legacy decomposition-based execution
            return await self._process_legacy(query, intent, slots, context, start_time)
            
        except Exception as e:
            # End session with failure
            self.task_monitor.end_session(success=False)
            
            # Return error result
            total_time_ms = int((time.time() - start_time) * 1000)
            
            return OrchestratorResult(
                query=query,
                intent=intent,
                decomposition=DecompositionResult(
                    tasks=[],
                    overall_confidence=0.0,
                    reasoning=f"Error: {str(e)}",
                    method="error"
                ),
                execution=ExecutionResult(
                    success=False,
                    task_results=[],
                    total_duration_ms=total_time_ms,
                    tasks_completed=0,
                    tasks_failed=1,
                    tasks_skipped=0,
                    parallel_levels=0
                ),
                total_time_ms=total_time_ms,
                success=False,
                narrative=f"An error occurred while processing your request: {str(e)}"
            )
    
    async def _process_multi_stage(
        self,
        query: str,
        intent: str,
        slots: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        start_time: float
    ) -> OrchestratorResult:
        """
        Process using multi-stage LLM execution as core architecture.
        
        This is the primary execution path that uses LLM reasoning at each stage.
        """
        # Create fresh multi-stage executor
        executor = self._create_multi_stage_executor()
        
        # Initial context from slots and intent
        initial_context = {
            "initial_intent": intent,
            "slots": slots,
            **(context or {})
        }
        
        # Execute all stages
        final_context = {}
        stage_results = {}
        
        async for event in executor.execute(query, initial_context):
            if event.get("type") == "stage_complete":
                stage = event.get("stage")
                stage_results[stage] = event
                
            elif event.get("type") == "execution_complete":
                final_context = event.get("final_context", {})
        
        # Extract results from stages
        understand_data = stage_results.get("understand", {}).get("data", {})
        plan_data = stage_results.get("plan", {}).get("data", {})
        execute_data = stage_results.get("execute", {}).get("data", {})
        validate_data = stage_results.get("validate", {}).get("data", {})
        synthesize_data = stage_results.get("synthesize", {}).get("data", {})
        
        # Build decomposition result from plan stage
        tasks = plan_data.get("tasks", [])
        decomposition = DecompositionResult(
            tasks=[
                DecomposedTask(
                    id=t.get("id", f"task_{i}"),
                    action=t.get("action", "unknown"),
                    entity=t.get("entity", ""),
                    parameters=t.get("parameters", {}),
                    confidence=t.get("confidence", 0.8),
                    source_span=query,
                    dependencies=t.get("dependencies", [])
                )
                for i, t in enumerate(tasks)
            ],
            overall_confidence=plan_data.get("confidence", 0.8),
            reasoning=plan_data.get("reasoning", "Generated via multi-stage planning"),
            method="multi_stage_llm"
        )
        
        # Build execution result from execute stage
        task_results = execute_data.get("task_results", {})
        execution = ExecutionResult(
            success=validate_data.get("is_complete", True),
            task_results=[
                TaskResult(
                    task_id=task_id,
                    success=result.get("success", True),
                    result=result.get("result"),
                    error=result.get("error"),
                    duration_ms=result.get("duration_ms", 0)
                )
                for task_id, result in task_results.items()
            ],
            total_duration_ms=int((time.time() - start_time) * 1000),
            tasks_completed=execute_data.get("tasks_executed", 0),
            tasks_failed=0,  # Will be calculated from results
            tasks_skipped=0,
            parallel_levels=len(plan_data.get("parallel_groups", []))
        )
        
        # Calculate success
        success = validate_data.get("is_complete", True) and execution.tasks_completed > 0
        
        if success:
            self._successful_queries += 1
        
        self._total_tasks_executed += execution.tasks_completed
        
        # Generate narrative from synthesize stage
        narrative = synthesize_data.get("response", self._generate_narrative(decomposition, execution))
        
        # End monitoring session
        self.task_monitor.end_session(success=success)
        
        total_time_ms = int((time.time() - start_time) * 1000)
        
        return OrchestratorResult(
            query=query,
            intent=intent,
            decomposition=decomposition,
            execution=execution,
            template_used=None,  # Multi-stage doesn't use templates
            total_time_ms=total_time_ms,
            success=success,
            narrative=narrative
        )
    
    async def _process_legacy(
        self,
        query: str,
        intent: str,
        slots: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        start_time: float
    ) -> OrchestratorResult:
        """
        Legacy processing using decomposition-based execution.
        
        This is the fallback path when multi-stage execution is disabled.
        """
        # Step 1: Decompose query into tasks
        decomposition = await self.task_decomposer.decompose(
            query=query,
            intent=intent,
            slots=slots,
            context=context
        )
        
        # Step 2: Build task dependency graph
        graph = decomposition.to_task_graph()
        
        # Step 3: Execute tasks
        executor = self._create_executor()
        execution = await executor.execute_graph(graph)
        
        # Step 4: Generate narrative from results
        narrative = self._generate_narrative(decomposition, execution)
        
        # Calculate total time
        total_time_ms = int((time.time() - start_time) * 1000)
        
        # Determine success
        success = execution.tasks_failed == 0
        
        if success:
            self._successful_queries += 1
        
        self._total_tasks_executed += execution.tasks_completed
        
        # Step 5: Learn from execution
        if self.config.is_enabled("auto_template_generation"):
            await self._learn_from_execution(
                graph=graph,
                execution=execution,
                intent=intent,
                success=success
            )
        
        # End monitoring session
        self.task_monitor.end_session(success=success)
        
        return OrchestratorResult(
            query=query,
            intent=intent,
            decomposition=decomposition,
            execution=execution,
            graph=graph,
            template_used=decomposition.template_used,
            total_time_ms=total_time_ms,
            success=success,
            narrative=narrative
        )
    
    async def process_streaming(
        self,
        query: str,
        intent: str,
        slots: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a query with streaming progress events.
        
        Uses multi-stage LLM execution as core architecture with streaming updates
        at each stage: UNDERSTAND → PLAN → EXECUTE → VALIDATE → SYNTHESIZE
        
        Yields:
            Progress event dictionaries
        """
        start_time = time.time()
        
        # Yield start event
        yield {
            "type": "orchestration_start",
            "query": query,
            "intent": intent,
            "architecture": "multi_stage_llm" if self.config.is_enabled("nlp_task_decomposition") else "legacy",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Use multi-stage executor as core architecture
            if self.config.is_enabled("nlp_task_decomposition") and self.llm_client:
                async for event in self._process_streaming_multi_stage(query, intent, slots, context, start_time):
                    yield event
            else:
                # Fallback to legacy streaming
                async for event in self._process_streaming_legacy(query, intent, slots, context, start_time):
                    yield event
            
        except Exception as e:
            yield {
                "type": "orchestration_error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _process_streaming_multi_stage(
        self,
        query: str,
        intent: str,
        slots: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        start_time: float
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming processing using multi-stage LLM execution.
        
        Yields detailed progress events for each stage.
        """
        # Create fresh multi-stage executor
        executor = self._create_multi_stage_executor()
        
        # Initial context from slots and intent
        initial_context = {
            "initial_intent": intent,
            "slots": slots,
            **(context or {})
        }
        
        stage_results = {}
        final_response = None
        
        # Execute all stages with streaming
        async for event in executor.execute(query, initial_context):
            # Transform multi-stage events to orchestration events
            if event.get("type") == "stage_start":
                yield {
                    "type": "stage_start",
                    "stage": event.get("stage"),
                    "message": event.get("message"),
                    "timestamp": datetime.now().isoformat()
                }
                
            elif event.get("type") == "stage_complete":
                stage = event.get("stage")
                stage_results[stage] = event
                
                yield {
                    "type": "stage_complete",
                    "stage": stage,
                    "success": event.get("success"),
                    "confidence": event.get("confidence"),
                    "reasoning": event.get("reasoning"),
                    "duration_ms": event.get("duration_ms"),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Yield stage-specific events for frontend
                if stage == "understand":
                    yield {
                        "type": "query_understood",
                        "intent": event.get("data", {}).get("intent", {}),
                        "entities": event.get("data", {}).get("entities", {}),
                        "constraints": event.get("data", {}).get("constraints", {}),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                elif stage == "plan":
                    tasks = event.get("data", {}).get("tasks", [])
                    parallel_groups = event.get("data", {}).get("parallel_groups", [])
                    
                    yield {
                        "type": "task_graph",
                        "tasks": tasks,
                        "parallel_groups": parallel_groups,
                        "reasoning": event.get("reasoning"),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                elif stage == "execute":
                    yield {
                        "type": "tasks_executed",
                        "tasks_executed": event.get("data", {}).get("tasks_executed", 0),
                        "task_results": event.get("data", {}).get("task_results", {}),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                elif stage == "validate":
                    yield {
                        "type": "validation_result",
                        "is_complete": event.get("data", {}).get("is_complete", True),
                        "coverage_score": event.get("data", {}).get("coverage_score", 1.0),
                        "missing_information": event.get("data", {}).get("missing_information", []),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                elif stage == "synthesize":
                    final_response = event.get("data", {})
                    yield {
                        "type": "response_synthesized",
                        "response": event.get("data", {}).get("response", ""),
                        "key_insights": event.get("data", {}).get("key_insights", []),
                        "recommendations": event.get("data", {}).get("recommendations", []),
                        "timestamp": datetime.now().isoformat()
                    }
                    
            elif event.get("type") == "stage_recovery":
                yield {
                    "type": "stage_recovery",
                    "stage": event.get("stage"),
                    "message": event.get("message"),
                    "timestamp": datetime.now().isoformat()
                }
                
            elif event.get("type") == "stage_error":
                yield {
                    "type": "stage_error",
                    "stage": event.get("stage"),
                    "error": event.get("error"),
                    "timestamp": datetime.now().isoformat()
                }
                
            elif event.get("type") == "execution_complete":
                total_time_ms = int((time.time() - start_time) * 1000)
                
                yield {
                    "type": "orchestration_complete",
                    "architecture": "multi_stage_llm",
                    "stages_completed": event.get("stages_completed", 0),
                    "success": stage_results.get("validate", {}).get("success", True),
                    "total_time_ms": total_time_ms,
                    "narrative": final_response.get("response", "") if final_response else "",
                    "timestamp": datetime.now().isoformat()
                }
    
    async def _process_streaming_legacy(
        self,
        query: str,
        intent: str,
        slots: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        start_time: float
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Legacy streaming processing using decomposition-based execution.
        """
        # Step 1: Decompose
        yield {
            "type": "decomposition_start",
            "timestamp": datetime.now().isoformat()
        }
        
        decomposition = await self.task_decomposer.decompose(
            query=query,
            intent=intent,
            slots=slots,
            context=context
        )
        
        yield {
            "type": "decomposition_complete",
            "method": decomposition.method,
            "task_count": len(decomposition.tasks),
            "confidence": decomposition.overall_confidence,
            "tasks": [
                {
                    "id": t.id,
                    "action": t.action,
                    "entity": t.entity,
                    "dependencies": t.dependencies
                }
                for t in decomposition.tasks
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        # Step 2: Build graph
        graph = decomposition.to_task_graph()
        levels = graph.get_parallel_tasks()
        
        yield {
            "type": "task_graph",
            "nodes": list(graph.nodes.keys()),
            "edges": {k: list(v) for k, v in graph.edges.items()},
            "parallel_groups": [[t.id for t in level] for level in levels],
            "timestamp": datetime.now().isoformat()
        }
        
        # Step 3: Execute with streaming
        executor = create_streaming_executor(
            max_concurrent=self.config.MAX_CONCURRENT_TASKS,
            default_timeout=self.config.TASK_TIMEOUT_SECONDS
        )
        
        # Register executors
        for task_type, executor_fn in self._task_executors.items():
            executor.register_executor(task_type, executor_fn)
        
        execution = None
        async for event in executor.execute_graph_streaming(graph):
            yield event
            
            if event.get("type") == "final_result":
                execution = ExecutionResult(
                    success=event["result"]["success"],
                    task_results=[
                        TaskResult(
                            task_id=r["task_id"],
                            success=r["success"],
                            result=r.get("result"),
                            error=r.get("error"),
                            duration_ms=r.get("duration_ms", 0)
                        )
                        for r in event["result"]["task_results"]
                    ],
                    total_duration_ms=event["result"]["total_duration_ms"],
                    tasks_completed=event["result"]["tasks_completed"],
                    tasks_failed=event["result"]["tasks_failed"],
                    tasks_skipped=event["result"]["tasks_skipped"],
                    parallel_levels=event["result"]["parallel_levels"]
                )
        
        # Step 4: Generate narrative
        narrative = self._generate_narrative(decomposition, execution)
        
        total_time_ms = int((time.time() - start_time) * 1000)
        
        yield {
            "type": "orchestration_complete",
            "architecture": "legacy",
            "success": execution.success if execution else False,
            "total_time_ms": total_time_ms,
            "narrative": narrative,
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_executor(self) -> ParallelTaskExecutor:
        """Create a configured executor instance"""
        executor = ParallelTaskExecutor(
            max_concurrent=self.config.MAX_CONCURRENT_TASKS,
            default_timeout=self.config.TASK_TIMEOUT_SECONDS,
            max_retries=self.config.MAX_RETRIES,
            retry_delay=self.config.RETRY_DELAY_SECONDS
        )
        
        # Register task executors
        for task_type, executor_fn in self._task_executors.items():
            executor.register_executor(task_type, executor_fn)
        
        return executor
    
    def _generate_narrative(
        self,
        decomposition: DecompositionResult,
        execution: ExecutionResult
    ) -> str:
        """Generate a human-readable narrative of the execution"""
        parts = []
        
        # Describe decomposition
        if decomposition.method == "template":
            parts.append(f"Used template '{decomposition.template_used}' for task planning.")
        elif decomposition.method == "llm":
            parts.append("Dynamically decomposed query into tasks using AI.")
        else:
            parts.append("Generated task plan using rule-based analysis.")
        
        # Describe execution
        if execution.success:
            parts.append(f"Successfully completed {execution.tasks_completed} tasks.")
        else:
            parts.append(
                f"Completed {execution.tasks_completed} tasks with {execution.tasks_failed} failures."
            )
        
        # Add timing info
        if execution.total_duration_ms > 0:
            parts.append(f"Total execution time: {execution.total_duration_ms}ms.")
        
        # Add parallel execution info
        if execution.parallel_levels > 1:
            parts.append(f"Executed across {execution.parallel_levels} parallel levels.")
        
        return " ".join(parts)
    
    async def _learn_from_execution(
        self,
        graph: TaskDependencyGraph,
        execution: ExecutionResult,
        intent: str,
        success: bool
    ) -> None:
        """Learn from execution for template generation"""
        # Convert graph nodes to list for pattern analysis
        tasks = list(graph.nodes.values())
        
        # Analyze execution pattern
        self.template_generator.analyze_execution(
            tasks=tasks,
            intent=intent,
            success=success,
            duration_ms=execution.total_duration_ms
        )
        
        # Periodically generate templates
        if self._queries_processed % 10 == 0:
            self.template_generator.generate_templates()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            "queries_processed": self._queries_processed,
            "successful_queries": self._successful_queries,
            "success_rate": self._successful_queries / max(1, self._queries_processed),
            "total_tasks_executed": self._total_tasks_executed,
            "decomposer_stats": self.task_decomposer.get_statistics(),
            "template_stats": self.template_library.get_statistics(),
            "template_generator_stats": self.template_generator.get_pattern_statistics()
        }
    
    def get_template_library(self) -> TemplateLibrary:
        """Get the template library instance"""
        return self.template_library
    
    def get_monitor(self) -> TaskMonitor:
        """Get the task monitor instance"""
        return self.task_monitor


# Singleton instance
_orchestrator_instance: Optional[TaskOrchestrator] = None

def get_task_orchestrator(
    task_config: Optional[TaskConfig] = None,
    llm_client: Optional[Any] = None
) -> TaskOrchestrator:
    """Get or create singleton TaskOrchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = TaskOrchestrator(
            task_config=task_config,
            llm_client=llm_client
        )
    return _orchestrator_instance
