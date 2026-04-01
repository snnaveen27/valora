"""
Enhanced Unified Valora Brain with Task Orchestration Integration
Extends the existing brain with the new NLP-driven task orchestration system.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import psutil
import time

# Import existing components
from ai.valora_brain_core import get_valora_brain, QueryIntent, MapAction, GISOperation
from ai.production_task_planner import get_production_task_planner, Task, TaskExecutionResult
from ai.pattern_learner import get_pattern_learner
from ai.systematic_prompts import get_prompt_for_intent, format_prompt
from ai.agentic_loop import get_agentic_loop, AgenticLoop
from ai.query_refiner import get_query_refiner, QueryRefiner
from ai.llm_health_monitor import get_health_monitor, LocalLLMHealthMonitor
from ai.multimodal_reasoning import get_multimodal_reasoner, MultiModalReasoner
from ai.rag_service import get_rag_service, SearchResult

# Import new task orchestration components
from ai.task_orchestrator import TaskOrchestrator, OrchestratorResult, get_task_orchestrator
from ai.task_graph import TaskDependencyGraph, TaskNode
from ai.task_templates import TaskTemplate
from config import config, TaskConfig


@dataclass
class EnhancedUnifiedResult:
    """Complete result from enhanced unified Valora Brain"""
    query: str
    intent: str
    confidence: float
    slots: Dict[str, Any]
    map_actions: List[Dict]
    gis_operations: List[Dict]
    tasks: List[Dict]
    task_results: List[Dict]
    narrative: str
    execution_time_ms: int
    used_cloud_llm: bool
    used_learned_pattern: bool
    used_agentic_loop: bool = False
    used_task_orchestrator: bool = False
    orchestration_method: str = "legacy"
    parallel_execution: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class EnhancedUnifiedBrain:
    """
    Enhanced Unified Valora Brain with Task Orchestration.
    
    Integrates:
    - Brain Core (intent classification)
    - Pattern Learner (caching)
    - Task Orchestrator (NEW - NLP-driven task management)
    - Agentic Loop (complex reasoning)
    - RAG Service (context retrieval)
    
    State Management:
    - Each query creates fresh TaskDependencyGraph and ParallelTaskExecutor instances
    - TaskMonitor resets per-session state in start_session()
    - Statistics are cumulative across queries (for monitoring purposes)
    """
    
    def __init__(self, use_task_orchestrator: bool = True):
        # Core components
        self.brain = get_valora_brain()
        self.task_planner = get_production_task_planner()
        self.pattern_learner = get_pattern_learner()
        
        # Advanced reasoning components
        self.agentic_loop = get_agentic_loop()
        self.query_refiner = get_query_refiner()
        self.llm_health_monitor = get_health_monitor()
        self.multimodal_reasoner = get_multimodal_reasoner()
        self.rag_service = get_rag_service()
        
        # NEW: Task Orchestrator
        # Note: TaskOrchestrator creates fresh instances for each query internally
        self._use_task_orchestrator = use_task_orchestrator
        self._task_config = config.TASK_CONFIG
        self._task_orchestrator: Optional[TaskOrchestrator] = None
        
        if use_task_orchestrator and self._task_config.is_enabled("nlp_task_decomposition"):
            self._task_orchestrator = get_task_orchestrator(
                task_config=self._task_config
            )
        
        # Local LLM reference
        self._local_llm = None
        
        # Execution stats (cumulative across queries)
        self.query_count = 0
        self.total_execution_time = 0
        self.agentic_queries = 0
        self.refined_queries = 0
        self.llm_health_failures = 0
        self.orchestrated_queries = 0
        
        # Resource telemetry
        self.peak_cpu_percent = 0.0
        self.peak_memory_percent = 0.0
        self.total_tokens_used = 0
        self.resource_samples = []
        
        # Query cache
        self._query_cache: Dict[str, Dict] = {}
        self._cache_max_size = 100
        self._cache_ttl_seconds = 300
    
    async def process_streaming(
        self,
        query: str,
        user_id: str = "anonymous",
        use_cloud_assistance: bool = True,
        context: Optional[Dict] = None,
        thread_id: Optional[str] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Process query with streaming updates for real-time UI feedback.
        Uses new task orchestrator when enabled.
        """
        start_time = datetime.now()
        start_cpu = psutil.cpu_percent(interval=None)
        start_mem = psutil.virtual_memory().percent
        
        yield {
            "type": "intent_classification_start",
            "query": query,
            "timestamp": start_time.isoformat()
        }
        
        # Check cache
        cache_key = self._get_cache_key(query, context)
        cached = self._get_cached_result(cache_key)
        if cached:
            yield {
                "type": "cache_hit",
                "message": "Returning cached result",
                "cache_age_ms": cached.get("age_ms", 0)
            }
            yield cached["event"]
            return
        
        # Yield: Processing started
        yield {
            "type": "intent_classification_start",
            "query": query,
            "timestamp": start_time.isoformat(),
            "telemetry": {
                "cpu_percent": start_cpu,
                "memory_percent": start_mem
            }
        }
        
        # Query Refinement
        refined_query = query
        if self.query_refiner:
            safe_context = context if context is not None else {}
            refined_result = self.query_refiner.refine(query, safe_context)
            if refined_result.missing_critical:
                yield {
                    "type": "query_refinement",
                    "status": "ambiguous_detected",
                    "original_query": query,
                    "missing_slots": [s.value for s in refined_result.missing_critical],
                    "suggestions": refined_result.suggested_clarifications
                }
            if refined_result.enriched_context:
                context = {**safe_context, **refined_result.enriched_context}
        
        # Pattern Cache Check
        pattern = self.pattern_learner.find_matching_pattern(refined_query) if self.pattern_learner else None
        used_learned_pattern = pattern and pattern.confidence > 0.85
        
        yield {
            "type": "pattern_match",
            "matched": used_learned_pattern,
            "intent": pattern.intent if pattern else None,
            "confidence": pattern.confidence if pattern else 0
        }
        
        # Intent Classification
        intent_result = await self.brain.process(refined_query, context)
        
        yield {
            "type": "intent_detected",
            "intent": intent_result.intent_type,
            "confidence": intent_result.confidence,
            "slots": intent_result.slots,
            "method": "pattern" if used_learned_pattern else "brain_core"
        }
        
        # Multi-Modal Reasoning
        multimodal_context = None
        if self.multimodal_reasoner and context:
            lat = context.get('lat')
            lng = context.get('lng')
            if lat is not None and lng is not None:
                yield {"type": "multimodal_analysis_started"}
                multimodal_result = self.multimodal_reasoner.reason(
                    query=query, lat=lat, lng=lng,
                    viewport=context.get('viewport'),
                    buildings_in_view=context.get('buildings_in_view')
                )
                multimodal_context = multimodal_result
                yield {
                    "type": "multimodal_analysis_complete",
                    "intent": multimodal_result.get('intent'),
                    "entities": multimodal_result.get('entities'),
                    "confidence": multimodal_result.get('confidence')
                }
        
        # RAG Context Retrieval
        rag_context = ""
        if self.rag_service:
            lat = context.get('lat') if context else None
            lng = context.get('lng') if context else None
            yield {"type": "rag_retrieval_started"}
            rag_context = self.rag_service.get_context_for_query(
                query=query, lat=lat, lng=lng,
                radius_km=2.0, max_results=10
            )
            yield {
                "type": "rag_retrieval_complete",
                "has_context": len(rag_context) > 0,
                "context_length": len(rag_context)
            }
        
        # Decide: Use Task Orchestrator or Legacy Path
        use_orchestrator = (
            self._task_orchestrator is not None and
            self._task_config.is_enabled("nlp_task_decomposition")
        )
        
        if use_orchestrator:
            # NEW: Use Task Orchestrator with streaming
            self.orchestrated_queries += 1
            
            yield {
                "type": "task_orchestration_started",
                "method": "nlp_driven",
                "parallel_execution": self._task_config.is_enabled("parallel_task_execution")
            }
            
            # Process with orchestrator
            orchestration_events = []
            orchestrator_result = None
            
            async for event in self._task_orchestrator.process_streaming(
                query=query,
                intent=intent_result.intent_type,
                slots=intent_result.slots,
                context=context
            ):
                # Yield orchestrator events
                yield event
                orchestration_events.append(event)
                
                if event.get("type") == "orchestration_complete":
                    orchestrator_result = event
            
            # Generate narrative
            yield {"type": "thinking_start", "message": "Generating response..."}
            
            narrative = await self._generate_narrative(
                query=query,
                intent_result=intent_result,
                task_results=[],  # Results are in orchestrator_result
                rag_context=rag_context,
                orchestrator_result=orchestrator_result
            )
            
            yield {"type": "thinking_end"}
            yield {"type": "content", "content": narrative}
            
            # Final result
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            result = {
                "intent": intent_result.intent_type,
                "confidence": intent_result.confidence,
                "narrative": narrative,
                "map_actions": self._extract_map_actions(orchestration_events),
                "execution_time_ms": execution_time,
                "used_cloud_llm": False,
                "used_learned_pattern": used_learned_pattern,
                "used_agentic_loop": False,
                "used_task_orchestrator": True,
                "orchestration_method": "nlp_driven",
                "parallel_execution": self._task_config.is_enabled("parallel_task_execution")
            }
            
            yield {"type": "done", "result": result}
            
        else:
            # LEGACY PATH: Use existing task planner
            used_agentic_loop = False
            if self._should_use_agentic_loop(query, intent_result):
                used_agentic_loop = True
                self.agentic_queries += 1
                yield {
                    "type": "agentic_loop_triggered",
                    "reason": "Complex multi-step query detected"
                }
                
                llm_client = await self._get_local_llm()
                if self.llm_health_monitor:
                    health = self.llm_health_monitor.get_health()
                    if not health.get('is_healthy', False):
                        self.llm_health_failures += 1
                        yield {
                            "type": "llm_health_warning",
                            "status": health.get('status', 'unknown')
                        }
                
                async for agent_event in self.agentic_loop.run(query, llm_client, context, streaming=True):
                    yield agent_event
                
                yield {"type": "agentic_loop_complete", "status": "success"}
            
            # Create Task Plan (legacy)
            tasks = await self.task_planner.create_task_plan(
                query=query,
                intent=intent_result.intent_type,
                slots=intent_result.slots,
                use_cloud_assistance=False
            )
            
            yield {
                "type": "task_plan_created",
                "total_tasks": len(tasks),
                "estimated_duration_ms": sum(t.estimated_duration_ms for t in tasks),
                "uses_cloud_llm": False
            }
            
            # Execute Tasks (legacy sequential)
            results = []
            for i, task in enumerate(tasks):
                yield {
                    "type": "task_started",
                    "task_id": task.id,
                    "task_name": task.name,
                    "task_type": task.type,
                    "task_description": task.description,
                    "progress": f"{i+1}/{len(tasks)}"
                }
                
                result = await self.task_planner._execute_task_with_retry(task)
                results.append(result)
                
                if result.success:
                    task.status = "completed"
                    task.result = result.result
                    summary = result.result.get('summary', 'Done') if isinstance(result.result, dict) else 'Done'
                    yield {
                        "type": "task_completed",
                        "task_id": result.task_id,
                        "task_name": task.name,
                        "summary": summary,
                        "duration_ms": result.duration_ms,
                        "progress": f"{i+1}/{len(tasks)}"
                    }
                else:
                    task.status = "failed"
                    task.error = result.error
                    yield {
                        "type": "task_failed",
                        "task_id": result.task_id,
                        "task_name": task.name,
                        "error": result.error,
                        "progress": f"{i+1}/{len(tasks)}"
                    }
            
            # Learn from execution
            self.task_planner._learn_from_execution(tasks, results)
            
            # Generate narrative
            yield {"type": "thinking_start", "message": "Generating response..."}
            
            narrative = await self._generate_narrative(
                query=query,
                intent_result=intent_result,
                task_results=results,
                rag_context=rag_context
            )
            
            yield {"type": "thinking_end"}
            yield {"type": "content", "content": narrative}
            
            # Final result
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            result = {
                "intent": intent_result.intent_type,
                "confidence": intent_result.confidence,
                "narrative": narrative,
                "map_actions": [t.params for t in tasks if t.type == "map_action"],
                "execution_time_ms": execution_time,
                "used_cloud_llm": False,
                "used_learned_pattern": used_learned_pattern,
                "used_agentic_loop": used_agentic_loop,
                "used_task_orchestrator": False,
                "orchestration_method": "legacy"
            }
            
            yield {"type": "done", "result": result}
        
        # Update stats
        self.query_count += 1
        self.total_execution_time += execution_time
    
    def _extract_map_actions(self, events: List[Dict]) -> List[Dict]:
        """Extract map actions from orchestration events"""
        map_actions = []
        for event in events:
            if event.get("type") == "task_completed":
                result = event.get("result", {})
                if isinstance(result, dict) and result.get("task_type") == "map_action":
                    map_actions.append(result.get("parameters", {}))
        return map_actions
    
    def _get_cache_key(self, query: str, context: Optional[Dict]) -> str:
        """Generate cache key from query and context"""
        import hashlib
        context_str = json.dumps(context or {}, sort_keys=True)
        combined = f"{query}:{context_str}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict]:
        """Get cached result if still valid"""
        if cache_key not in self._query_cache:
            return None
        
        cached = self._query_cache[cache_key]
        age_ms = int((datetime.now() - datetime.fromisoformat(cached["timestamp"])).total_seconds() * 1000)
        
        if age_ms > self._cache_ttl_seconds * 1000:
            del self._query_cache[cache_key]
            return None
        
        cached["age_ms"] = age_ms
        return cached
    
    def _should_use_agentic_loop(self, query: str, intent_result: Any) -> bool:
        """Determine if agentic loop should be used"""
        complex_indicators = [
            "analyze", "compare", "evaluate", "recommend",
            "best", "worst", "pros and cons", "detailed"
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in complex_indicators)
    
    async def _get_local_llm(self):
        """Get local LLM client"""
        if self._local_llm is None:
            from ai.ollama_client import get_ollama_client
            self._local_llm = get_ollama_client()
        return self._local_llm
    
    async def _generate_narrative(
        self,
        query: str,
        intent_result: Any,
        task_results: List,
        rag_context: str = "",
        orchestrator_result: Optional[Dict] = None
    ) -> str:
        """Generate human-readable narrative response"""
        # If orchestrator result provided, use its narrative
        if orchestrator_result:
            return orchestrator_result.get("narrative", "Task completed successfully.")
        
        # Legacy narrative generation
        intent = intent_result.intent_type
        slots = intent_result.slots
        
        narratives = {
            "navigate": f"I've navigated to {slots.get('location', 'the requested location')}.",
            "property_search": f"Found properties matching your criteria in {slots.get('location', 'the area')}.",
            "analyze_area": f"Here's the analysis for {slots.get('location', 'the area')}.",
            "comparison": f"Here's the comparison between the requested areas.",
            "route_analysis": f"Here's the route information you requested.",
            "default": "I've processed your request."
        }
        
        return narratives.get(intent, narratives["default"])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get brain statistics"""
        stats = {
            "query_count": self.query_count,
            "total_execution_time_ms": self.total_execution_time,
            "avg_execution_time_ms": self.total_execution_time / max(1, self.query_count),
            "agentic_queries": self.agentic_queries,
            "orchestrated_queries": self.orchestrated_queries,
            "llm_health_failures": self.llm_health_failures,
            "task_orchestrator_enabled": self._task_orchestrator is not None
        }
        
        if self._task_orchestrator:
            stats["orchestrator_stats"] = self._task_orchestrator.get_statistics()
        
        return stats


# Singleton instance
_enhanced_brain_instance: Optional[EnhancedUnifiedBrain] = None

def get_enhanced_unified_brain(use_task_orchestrator: bool = True) -> EnhancedUnifiedBrain:
    """Get or create singleton EnhancedUnifiedBrain instance"""
    global _enhanced_brain_instance
    if _enhanced_brain_instance is None:
        _enhanced_brain_instance = EnhancedUnifiedBrain(
            use_task_orchestrator=use_task_orchestrator
        )
    return _enhanced_brain_instance
