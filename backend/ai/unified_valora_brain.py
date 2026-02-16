"""
Unified Valora Brain - Production Integration
Connects all components: Brain Core, Task Planner, Pattern Learner, Agentic Loop
Local Ollama (Qwen3 8B) only - no cloud LLM dependency.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime

# Import all components
import psutil
import time

from ai.valora_brain_core import get_valora_brain, QueryIntent, MapAction, GISOperation
from ai.production_task_planner import get_production_task_planner, Task, TaskExecutionResult
from ai.pattern_learner import get_pattern_learner
from ai.systematic_prompts import get_prompt_for_intent, format_prompt
from ai.agentic_loop import get_agentic_loop, AgenticLoop
from ai.query_refiner import get_query_refiner, QueryRefiner
from ai.llm_health_monitor import get_health_monitor, LocalLLMHealthMonitor
from ai.multimodal_reasoning import get_multimodal_reasoner, MultiModalReasoner  # NEW
from ai.rag_service import get_rag_service, SearchResult  # NEW

@dataclass
class UnifiedResult:
    """Complete result from unified Valora Brain"""
    query: str
    intent: str
    confidence: float
    slots: Dict[str, Any]
    map_actions: List[MapAction]
    gis_operations: List[GISOperation]
    tasks: List[Task]
    task_results: List[TaskExecutionResult]
    narrative: str
    execution_time_ms: int
    used_cloud_llm: bool
    used_learned_pattern: bool
    used_agentic_loop: bool = False  # NEW: Track agentic loop usage
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class UnifiedValoraBrain:
    """
    Production Unified Valora Brain
    Integrates: Brain Core → Pattern Learner → Task Planner → Execution
    """
    
    def __init__(self):
        # Core components
        self.brain = get_valora_brain()
        self.task_planner = get_production_task_planner()
        self.pattern_learner = get_pattern_learner()
        
        # Advanced reasoning components (newly wired)
        self.agentic_loop = get_agentic_loop()
        self.query_refiner = get_query_refiner()
        self.llm_health_monitor = get_health_monitor()
        self.multimodal_reasoner = get_multimodal_reasoner()  # NEW
        self.rag_service = get_rag_service()  # NEW
        
        # Local LLM only - Cloud LLM removed
        self._local_llm = None
        
        # Execution stats with telemetry
        self.query_count = 0
        self.total_execution_time = 0
        self.agentic_queries = 0
        self.refined_queries = 0  # NEW: Track query refinements
        self.llm_health_failures = 0  # NEW: Track LLM health issues
        
        # Resource telemetry tracking (NEW)
        self.peak_cpu_percent = 0.0
        self.peak_memory_percent = 0.0
        self.total_tokens_used = 0
        self.resource_samples = []
        
        # Query result cache (NEW)
        self._query_cache: Dict[str, Dict] = {}
        self._cache_max_size = 100
        self._cache_ttl_seconds = 300  # 5 minutes
        
        # Telemetry-based auto-tuning (NEW)
        self._agentic_query_patterns: Dict[str, Dict] = {}  # Track success of agentic queries by pattern
        self._normal_query_patterns: Dict[str, Dict] = {}   # Track success of normal queries by pattern
        self._auto_tuning_enabled = True
        self._min_samples_for_tuning = 5
    
    async def process_streaming(
        self,
        query: str,
        user_id: str = "anonymous",
        use_cloud_assistance: bool = True,
        context: Optional[Dict] = None,
        thread_id: Optional[str] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Process query with streaming updates for real-time UI feedback
        Yields progress events that frontend can display
        """
        start_time = datetime.now()
        start_cpu = psutil.cpu_percent(interval=None)
        start_mem = psutil.virtual_memory().percent
        
        # FAST PATH: Greetings & chitchat - respond instantly without LLM/RAG/tasks
        greeting_response = self._check_greeting_fast_path(query)
        if greeting_response:
            yield {
                "type": "intent_classification_start",
                "query": query,
                "timestamp": start_time.isoformat()
            }
            yield {
                "type": "intent_detected",
                "intent": "greeting",
                "confidence": 0.99,
                "slots": {},
                "method": "fast_path"
            }
            yield {"type": "content", "content": greeting_response}
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            yield {
                "type": "done",
                "result": {
                    "intent": "greeting",
                    "confidence": 0.99,
                    "narrative": greeting_response,
                    "map_actions": [],
                    "execution_time_ms": execution_time,
                    "used_cloud_llm": False,
                    "used_learned_pattern": False,
                    "used_agentic_loop": False
                }
            }
            return
        
        # Check query cache
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
        
        # Yield: Processing started with telemetry
        yield {
            "type": "intent_classification_start",
            "query": query,
            "timestamp": start_time.isoformat(),
            "telemetry": {
                "cpu_percent": start_cpu,
                "memory_percent": start_mem
            }
        }
        
        # Step 0.5: Query Refinement for Ambiguous Queries (NEW)
        refined_query = query
        refinement_applied = False
        if self.query_refiner:
            # Ensure context is not None before passing to refiner
            safe_context = context if context is not None else {}
            refined_result = self.query_refiner.refine(query, safe_context)
            # Check if query is ambiguous (has missing critical slots)
            if refined_result.missing_critical:
                yield {
                    "type": "query_refinement",
                    "status": "ambiguous_detected",
                    "original_query": query,
                    "missing_slots": [s.value for s in refined_result.missing_critical],
                    "suggestions": refined_result.suggested_clarifications
                }
            # Use enriched context if available
            if refined_result.enriched_context:
                if context is not None:
                    context = {**context, **refined_result.enriched_context}
                else:
                    context = refined_result.enriched_context
            # Update refined query (though we keep original for intent classification)
            refined_query = refined_result.original_query
        
        # Step 1: Pattern Cache Check (use refined query)
        pattern = self.pattern_learner.find_matching_pattern(refined_query) if self.pattern_learner else None
        
        if pattern and pattern.confidence > 0.85:
            yield {
                "type": "pattern_match",
                "matched": True,
                "intent": pattern.intent,
                "confidence": pattern.confidence,
                "source": "cache"
            }
            used_learned_pattern = True
        else:
            yield {
                "type": "pattern_match",
                "matched": False
            }
            used_learned_pattern = False
        
        # Step 2: Intent Classification with Brain Core (use refined query)
        intent_result = await self.brain.process(refined_query, context)
        
        # Emit intent_detected for TopTaskBanner
        yield {
            "type": "intent_detected",
            "intent": intent_result.intent_type,
            "confidence": intent_result.confidence,
            "slots": intent_result.slots,
            "method": "pattern" if used_learned_pattern else "brain_core"
        }
        
        # Step 2.1: Multi-Modal Reasoning (NEW)
        multimodal_context = None
        if self.multimodal_reasoner and context:
            lat = context.get('lat')
            lng = context.get('lng')
            viewport = context.get('viewport')
            buildings_in_view = context.get('buildings_in_view')
            
            if lat is not None and lng is not None:
                yield {"type": "multimodal_analysis_started"}
                
                multimodal_result = self.multimodal_reasoner.reason(
                    query=query,
                    lat=lat,
                    lng=lng,
                    viewport=viewport,
                    buildings_in_view=buildings_in_view
                )
                multimodal_context = multimodal_result
                
                yield {
                    "type": "multimodal_analysis_complete",
                    "intent": multimodal_result.get('intent'),
                    "entities": multimodal_result.get('entities'),
                    "confidence": multimodal_result.get('confidence'),
                    "response_guidance": multimodal_result.get('response_guidance')
                }
        
        # Step 2.2: RAG Context Retrieval (NEW)
        rag_context = ""
        if self.rag_service:
            lat = context.get('lat') if context else None
            lng = context.get('lng') if context else None
            
            yield {"type": "rag_retrieval_started"}
            
            rag_context = self.rag_service.get_context_for_query(
                query=query,
                lat=lat,
                lng=lng,
                radius_km=2.0,
                max_results=10
            )
            
            yield {
                "type": "rag_retrieval_complete",
                "has_context": len(rag_context) > 0,
                "context_length": len(rag_context)
            }
        
        # Step 2.5: Agentic Loop for Complex Queries (NEW)
        used_agentic_loop = False
        if self._should_use_agentic_loop(query, intent_result):
            used_agentic_loop = True
            self.agentic_queries += 1  # Increment counter immediately
            yield {
                "type": "agentic_loop_triggered",
                "reason": "Complex multi-step query detected",
                "count": self.agentic_queries
            }
            
            # Run Agentic Loop for complex reasoning
            llm_client = await self._get_local_llm()
            
            # Health check before using LLM (NEW)
            if self.llm_health_monitor:
                health = self.llm_health_monitor.get_health()
                if not health.get('is_healthy', False):
                    self.llm_health_failures += 1
                    yield {
                        "type": "llm_health_warning",
                        "status": health.get('status', 'unknown'),
                        "message": "LLM health check failed, using fallback mode"
                    }
            
            async for agent_event in self.agentic_loop.run(query, llm_client, context, streaming=True):
                yield agent_event
                
            # Agentic loop complete - enhance intent with findings
            yield {
                "type": "agentic_loop_complete",
                "status": "success"
            }
        
        # Step 3: Create Task Plan (local only)
        tasks = await self.task_planner.create_task_plan(
            query=query,
            intent=intent_result.intent_type,
            slots=intent_result.slots,
            use_cloud_assistance=False  # Cloud LLM disabled - local only
        )
        
        yield {
            "type": "task_plan_created",
            "total_tasks": len(tasks),
            "estimated_duration_ms": sum(t.estimated_duration_ms for t in tasks),
            "uses_cloud_llm": False
        }
        
        # Step 5: Execute Tasks with Streaming
        completed_count = 0
        task_results = []
        
        # Define callbacks that will yield events
        async def on_task_start(task: Task):
            nonlocal completed_count
            # This runs in the task planner context
            print(f"[Task] Started: {task.name}")
        
        async def on_task_complete(task: Task, result: TaskExecutionResult):
            nonlocal completed_count
            completed_count += 1
            print(f"[Task] Completed: {task.name} ({result.duration_ms}ms)")
        
        async def on_task_fail(task: Task, result: TaskExecutionResult):
            print(f"[Task] Failed: {task.name} - {result.error}")
        
        # Execute tasks one by one with interleaved start/complete events
        results = []
        for i, task in enumerate(tasks):
            # Yield start event
            yield {
                "type": "task_started",
                "task_id": task.id,
                "task_name": task.name,
                "task_type": task.type,
                "task_description": task.description,
                "progress": f"{i+1}/{len(tasks)}"
            }
            
            # Execute this single task
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
        
        # Step 6: Generate Narrative with streaming events
        yield {"type": "thinking_start", "message": "Generating response..."}
        
        narrative = await self._generate_narrative(
            query=query,
            intent_result=intent_result,
            task_results=results,
            rag_context=rag_context
        )
        
        yield {"type": "thinking_end"}
        
        # If narrative is an error, yield it as content
        if narrative.startswith("[Error:") or narrative.startswith("[LLM Error:"):
            yield {"type": "content", "content": narrative}
        else:
            yield {"type": "content", "content": narrative}
        
        # Step 7: Final Result
        end_time = datetime.now()
        execution_time = int((end_time - start_time).total_seconds() * 1000)
        
        unified_result = UnifiedResult(
            query=query,
            intent=intent_result.intent_type,
            confidence=intent_result.confidence,
            slots=intent_result.slots,
            map_actions=intent_result.map_actions,
            gis_operations=intent_result.gis_operations,
            tasks=tasks,
            task_results=results,
            narrative=narrative,
            execution_time_ms=execution_time,
            used_cloud_llm=False,
            used_learned_pattern=used_learned_pattern,
            used_agentic_loop=used_agentic_loop  # NEW: Track agentic loop usage
        )
        
        # Update telemetry stats
        self.query_count += 1
        self.total_execution_time += execution_time
        
        # Update pattern stats for auto-tuning (NEW)
        self._update_query_pattern_stats(
            query=query,
            intent_result=intent_result,
            used_agentic=used_agentic_loop,
            execution_time_ms=execution_time,
            success=True  # Could be determined from task_results
        )
        
        # Capture end resource metrics
        end_cpu = psutil.cpu_percent(interval=None)
        end_mem = psutil.virtual_memory().percent
        self.peak_cpu_percent = max(self.peak_cpu_percent, end_cpu)
        self.peak_memory_percent = max(self.peak_memory_percent, end_mem)
        
        # Store resource sample
        self.resource_samples.append({
            "query": query[:50],  # Truncate for memory
            "execution_time_ms": execution_time,
            "cpu_delta": end_cpu - start_cpu,
            "memory_percent": end_mem,
            "used_agentic": used_agentic_loop
        })
        
        # Keep only last 100 samples to prevent memory bloat
        if len(self.resource_samples) > 100:
            self.resource_samples = self.resource_samples[-100:]
        
        completion_event = {
            "type": "done",
            "result": {
                "intent": unified_result.intent,
                "confidence": unified_result.confidence,
                "narrative": unified_result.narrative,
                "map_actions": [
                    {
                        "action": a.action,
                        "params": a.params,
                        "purpose": a.purpose
                    }
                    for a in unified_result.map_actions
                ],
                "execution_time_ms": unified_result.execution_time_ms,
                "used_cloud_llm": unified_result.used_cloud_llm,
                "used_learned_pattern": unified_result.used_learned_pattern,
                "used_agentic_loop": used_agentic_loop
            },
            "telemetry": {
                "cpu_delta": round(end_cpu - start_cpu, 1),
                "memory_percent": round(end_mem, 1)
            }
        }
        
        # Build ui_actions from map_actions for frontend panel interaction
        ui_actions = []
        for ma in unified_result.map_actions:
            action_data = {"action": ma.action}
            if ma.params:
                action_data.update(ma.params)
            # Extract lat/lng from params for flyTo
            if ma.action == "flyTo" and ma.params:
                loc = ma.params.get("location", "")
                action_data["action"] = "flyTo"
            ui_actions.append(action_data)
        
        # Add load_buildings actions from task results
        print(f"[UnifiedBrain] Processing {len(unified_result.task_results)} task results for ui_actions")
        print(f"[UnifiedBrain] Task types: {[t.task_id for t in unified_result.task_results]}")
        for task_result in unified_result.task_results:
            print(f"[UnifiedBrain] Checking task {task_result.task_id}: success={task_result.success}, has_result={task_result.result is not None}")
            if task_result.success and task_result.result:
                result_data = task_result.result
                print(f"[UnifiedBrain] Task {task_result.task_id}: result_type={type(result_data)}, action={result_data.get('action') if isinstance(result_data, dict) else 'N/A'}")
                if isinstance(result_data, dict) and result_data.get("action") == "load_buildings":
                    coords = result_data.get("coordinates", {})
                    action_data = {
                        "action": "load_buildings",
                        "lat": coords.get("lat"),
                        "lng": coords.get("lng"),
                        "radius_km": result_data.get("radius_km", 2)
                    }
                    ui_actions.append(action_data)
                    print(f"[UnifiedBrain] ✅ Added load_buildings to ui_actions: {action_data}")
            else:
                print(f"[UnifiedBrain] Task {task_result.task_id} skipped: success={task_result.success}, result={task_result.result}")
        
        # Add tab switching based on intent
        tab_map = {
            "analyze_area": "insights",
            "building_analysis": "insights",
            "price_trend": "insights",
            "investment": "insights",
            "simulate": "simulation",
            "comparison": "insights",
        }
        if unified_result.intent in tab_map:
            ui_actions.append({"action": "switchTab", "value": tab_map[unified_result.intent]})
        
        # Yield metadata event for frontend panel/map integration
        print(f"[UnifiedBrain] 📤 Yielding metadata with {len(ui_actions)} ui_actions")
        yield {
            "type": "metadata",
            "ui_actions": ui_actions,
            "intent": unified_result.intent,
        }
        
        # Store in cache for future queries
        self._store_in_cache(cache_key, completion_event)
        
        # Yield completion with telemetry
        yield completion_event
    
    # Alias for server compatibility
    process_stream = process_streaming
    
    async def process(
        self,
        query: str,
        user_id: str = "anonymous",
        use_cloud_assistance: bool = True,
        context: Optional[Dict] = None
    ) -> UnifiedResult:
        """Non-streaming version for simple use cases - collects all data from streaming"""
        result_data = None
        slots_data = {}
        map_actions_data = []
        tasks_data = []
        task_results_data = []
        
        async for event in self.process_streaming(query, user_id, use_cloud_assistance, context):
            if event["type"] == "intent_classified":
                slots_data = event.get("slots", {})
            elif event["type"] == "task_plan_created":
                # Tasks are created but we get them from the stream
                pass
            elif event["type"] == "processing_complete":
                result_data = event["result"]
                map_actions_data = result_data.get("map_actions", [])
        
        # Convert map_actions back to objects
        from ai.valora_brain_core import MapAction
        map_actions_objects = [
            MapAction(
                action=a["action"],
                params=a.get("params", {}),
                purpose=a.get("purpose", ""),
                priority=1
            )
            for a in map_actions_data
        ]
        
        # Reconstruct UnifiedResult with full data
        return UnifiedResult(
            query=query,
            intent=result_data["intent"],
            confidence=result_data["confidence"],
            slots=slots_data,
            map_actions=map_actions_objects,
            gis_operations=[],  # Would need to track these during streaming
            tasks=[],  # Would need to track these during streaming
            task_results=[],  # Would need to track these during streaming
            narrative=result_data["narrative"],
            execution_time_ms=result_data["execution_time_ms"],
            used_cloud_llm=result_data["used_cloud_llm"],
            used_learned_pattern=result_data["used_learned_pattern"]
        )
    
    def _check_greeting_fast_path(self, query: str) -> Optional[str]:
        """
        Fast-path for greetings and simple chitchat.
        Returns a response string if matched, None otherwise.
        Avoids LLM/RAG/task pipeline for instant response (<10ms).
        """
        q = query.strip().lower().rstrip('!?.,:;')
        
        # Exact greetings
        greetings = {
            'hi', 'hello', 'hey', 'hii', 'hiii', 'yo', 'sup',
            'good morning', 'good afternoon', 'good evening', 'good night',
            'gm', 'namaste', 'howdy', 'hola', 'greetings'
        }
        if q in greetings:
            return (
                "Hello! I'm **Valora AI**, your Bangalore real estate intelligence assistant. "
                "I can help you with:\n\n"
                "- **Property search** — \"Show me 2BHK in Koramangala under 80L\"\n"
                "- **Area analysis** — \"How is Whitefield for investment?\"\n"
                "- **Price trends** — \"Price trend in Electronic City\"\n"
                "- **Comparisons** — \"Compare Indiranagar vs HSR Layout\"\n"
                "- **Simulations** — \"What if a metro opens near Sarjapur?\"\n\n"
                "What would you like to explore?"
            )
        
        # Conversational chitchat - "how are you", "what's up", etc.
        chitchat_phrases = [
            'how are you', 'how r u', 'how you doing', "how's it going",
            'whats up', "what's up", 'wassup', 'how do you do',
            'are you there', 'you there', 'are you alive', 'are you real',
            'tell me about yourself', 'introduce yourself',
            'good to see you', 'nice to meet you', 'pleased to meet you'
        ]
        if any(phrase in q for phrase in chitchat_phrases) or q in {'how are you', 'how r u'}:
            return (
                "I'm doing great, thank you for asking! I'm **Valora AI**, always ready to help "
                "with Bangalore real estate intelligence.\n\n"
                "I can search **42,000+ properties**, analyze **686K buildings**, and provide "
                "spatial insights across all Bangalore neighborhoods.\n\n"
                "What can I help you with today?"
            )
        
        # "What can you do" / help queries
        help_phrases = [
            'what can you do', 'what do you do', 'help', 'how can you help',
            'what are you', 'who are you', 'capabilities', 'features',
            'what should i ask', 'what can i ask'
        ]
        if any(phrase in q for phrase in help_phrases):
            return (
                "I'm **Valora AI** — a city intelligence platform for Bangalore real estate. "
                "Here's what I can do:\n\n"
                "🏠 **Property Search** — Find properties by area, budget, BHK, type\n"
                "📊 **Area Analysis** — Livability scores, infrastructure, demographics\n"
                "📈 **Price Trends** — Historical and projected price movements\n"
                "🔄 **Comparisons** — Side-by-side area or property comparisons\n"
                "💰 **Investment Analysis** — ROI, rental yield, growth potential\n"
                "🚇 **Infrastructure** — Metro, schools, hospitals nearby\n"
                "🏗️ **Simulations** — \"What if a metro station opens here?\"\n\n"
                "Try asking: **\"Show me top properties in HSR Layout\"**"
            )
        
        # Simple thanks
        thanks = {'thanks', 'thank you', 'thx', 'ty', 'thanks a lot', 'thank u'}
        if q in thanks:
            return "You're welcome! Let me know if you need anything else about Bangalore real estate."
        
        # Simple bye
        byes = {'bye', 'goodbye', 'see you', 'later', 'cya'}
        if q in byes:
            return "Goodbye! Come back anytime for Bangalore real estate insights. 👋"
        
        # Not a greeting — return None to continue normal pipeline
        return None
    
    async def _get_local_llm(self):
        """Get LLM client based on user's active model selection (Ollama)"""
        try:
            from routes.admin_routes import get_active_llm_config
            config = get_active_llm_config()
            
            # Get the active model from user's selection
            active_model = config.get('active_model', 'qwen3:4b-instruct')
            
            # Load max_context from config
            max_context = 8192  # default
            try:
                from pathlib import Path
                config_path = Path(__file__).parent.parent / "llm_config.json"
                with open(config_path) as f:
                    llm_config = json.load(f)
                    max_context = llm_config.get('max_context', 8192)
            except Exception as e:
                print(f"[UnifiedBrain] Failed to load max_context: {e}")
            
            # Use Ollama
            from ai.ollama_client import OllamaClient
            return OllamaClient(
                base_url="http://localhost:11434", 
                model=active_model,
                max_context=max_context
            )
        except Exception as e:
            print(f"[UnifiedBrain] LLM client not available: {e}")
            return None
    
    def _load_cloud_config(self) -> bool:
        """Load cloud LLM enabled status from config"""
        try:
            import json
            from pathlib import Path
            config_path = Path(__file__).parent.parent / "llm_config.json"
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                    return config.get("cloud_enabled", False)
        except Exception as e:
            print(f"[UnifiedBrain] Could not load cloud config: {e}")
        return False
    
    def _should_use_agentic_loop(self, query: str, intent_result: QueryIntent) -> bool:
        """Determine if query needs Agentic Loop with telemetry-based learning"""
        # Get query pattern signature
        pattern_key = self._get_query_pattern_key(query, intent_result)
        
        # Check if we have enough data to make smart decision
        if self._auto_tuning_enabled and pattern_key in self._agentic_query_patterns:
            agentic_data = self._agentic_query_patterns[pattern_key]
            normal_data = self._normal_query_patterns.get(pattern_key, {"count": 0, "avg_time": 4000})
            
            # Only use telemetry if we have enough samples
            if agentic_data.get("count", 0) >= self._min_samples_for_tuning:
                agentic_time = agentic_data.get("avg_time", 18000)
                normal_time = normal_data.get("avg_time", 4000)
                
                # If agentic is consistently slower without benefit, skip it
                if agentic_time > normal_time * 2 and agentic_data.get("success_rate", 1.0) < 0.9:
                    print(f"[AutoTuning] Skipping agentic for pattern '{pattern_key[:30]}...' - too slow ({agentic_time:.0f}ms vs {normal_time:.0f}ms)")
                    return False
        
        # Complex multi-part queries
        complex_keywords = ['and then', 'also', 'plus', 'compare with', 'vs', 'versus']
        if any(kw in query.lower() for kw in complex_keywords):
            return True
        
        # Multi-intent queries (e.g., search + compare + recommend)
        if len(intent_result.slots) > 3 and intent_result.intent_type in ['property_search', 'analyze_area']:
            return True
        
        # Simulation + analysis combination
        if intent_result.intent_type == 'simulate' and 'analyze' in query.lower():
            return True
        
        # Long queries (likely multi-step)
        if len(query.split()) > 15:
            return True
        
        return False
    
    def _get_query_pattern_key(self, query: str, intent_result: QueryIntent) -> str:
        """Generate a pattern key for query classification"""
        # Extract key elements: intent + slot count + length bracket
        length_bracket = "short" if len(query.split()) < 8 else ("medium" if len(query.split()) < 15 else "long")
        slot_count = len(intent_result.slots)
        return f"{intent_result.intent_type}:{slot_count}:{length_bracket}"
    
    def _update_query_pattern_stats(self, query: str, intent_result: QueryIntent, used_agentic: bool, execution_time_ms: int, success: bool = True):
        """Update statistics for query patterns to enable auto-tuning"""
        pattern_key = self._get_query_pattern_key(query, intent_result)
        
        if used_agentic:
            if pattern_key not in self._agentic_query_patterns:
                self._agentic_query_patterns[pattern_key] = {"count": 0, "avg_time": 0, "success_rate": 1.0, "total_time": 0}
            stats = self._agentic_query_patterns[pattern_key]
            stats["count"] += 1
            stats["total_time"] += execution_time_ms
            stats["avg_time"] = stats["total_time"] / stats["count"]
            old_success = stats["success_rate"]
            stats["success_rate"] = (old_success * 0.9) + (1.0 if success else 0.0) * 0.1
        else:
            if pattern_key not in self._normal_query_patterns:
                self._normal_query_patterns[pattern_key] = {"count": 0, "avg_time": 0, "total_time": 0}
            stats = self._normal_query_patterns[pattern_key]
            stats["count"] += 1
            stats["total_time"] += execution_time_ms
            stats["avg_time"] = stats["total_time"] / stats["count"]
    
    def get_tuning_stats(self) -> Dict[str, Any]:
        """Get auto-tuning statistics for analysis"""
        return {
            "auto_tuning_enabled": self._auto_tuning_enabled,
            "agentic_patterns_tracked": len(self._agentic_query_patterns),
            "normal_patterns_tracked": len(self._normal_query_patterns),
            "top_agentic_patterns": sorted(self._agentic_query_patterns.items(), key=lambda x: x[1].get("count", 0), reverse=True)[:5],
            "patterns_where_agentic_slower": [
                (k, v) for k, v in self._agentic_query_patterns.items()
                if v.get("avg_time", 0) > self._normal_query_patterns.get(k, {}).get("avg_time", 4000) * 1.5
            ]
        }
    
    async def _generate_narrative(
        self,
        query: str,
        intent_result: QueryIntent,
        task_results: List[TaskExecutionResult],
        rag_context: str = ""
    ) -> str:
        """Generate natural language response using LLM for production quality"""
        # Build context from task results
        successful_tasks = [r for r in task_results if r.success]
        failed_tasks = [r for r in task_results if not r.success]
        
        # Build grounded facts context with real data from task results
        facts_context = f"""
Query: {query}
Intent: {intent_result.intent_type}
Location: {intent_result.slots.get('location', 'unknown')}
"""
        
        # Include RAG context if available
        if rag_context:
            facts_context += f"\nRAG Knowledge Base Context:\n{rag_context[:1500]}\n"
        
        # Add detailed task results - include real DB data
        for task in successful_tasks[:5]:
            result = task.result if isinstance(task.result, dict) else {}
            task_name = f"Task {task.task_id}" if hasattr(task, 'task_id') else "Task"
            summary = result.get('summary', 'completed')
            facts_context += f"\n[{task_name}] {summary}"
            
            # Include property listings if available
            if result.get('properties'):
                facts_context += f"\nProperties found ({result.get('count', 0)} total):"
                for prop in result['properties'][:5]:
                    facts_context += f"\n  - {prop}"
            
            # Include area insights if available
            if result.get('insights'):
                facts_context += f"\nArea Insights:\n{result['insights']}"
            
            # Include POI/transport details
            if result.get('top_pois'):
                facts_context += f"\nNearby POIs: {', '.join(result['top_pois'][:5])}"
            if result.get('nearest_transport'):
                facts_context += f"\nTransit: {', '.join(result['nearest_transport'][:3])}"
        
        if failed_tasks:
            facts_context += f"\n\nNote: {len(failed_tasks)} operations failed."
        
        # Use LLM to generate narrative - NO FALLBACK, must use LLM
        try:
            llm_client = await self._get_local_llm()
            if not llm_client:
                return "[Error: LLM client not available. Please check Ollama is running.]"
            
            system_prompt = f"""You are Valora AI, Bangalore's city intelligence assistant.
You have access to real GIS data, property databases, and spatial analysis.

RULES:
- Base ALL claims on the grounded facts below. Never invent data.
- Be specific: mention exact numbers, areas, prices when available.
- Structure responses with clear sections using markdown.
- Keep responses concise (under 200 words) but informative.
- If data is insufficient, say so honestly and suggest what to ask.

GROUNDED FACTS:
{facts_context}"""
            
            # Combine system + user prompt for Ollama
            full_prompt = f"{system_prompt}\n\nUser: {query}\nAssistant:"
            
            response_text = await llm_client.generate(
                prompt=full_prompt,
                temperature=0.7,
                max_tokens=1024
            )
            if response_text:
                return response_text
            else:
                return "[Error: LLM returned empty response]"
        except Exception as e:
            error_msg = f"[LLM Error: {str(e)}]"
            print(f"[NARRATIVE] {error_msg}")
            return error_msg
    
    def _get_cache_key(self, query: str, context: Optional[Dict]) -> str:
        """Generate cache key from query and context"""
        import hashlib
        # Normalize query
        normalized = query.lower().strip()
        # Add context hash if available
        context_str = json.dumps(context, sort_keys=True) if context else ""
        key = f"{normalized}:{context_str}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict]:
        """Get result from cache if valid"""
        if cache_key not in self._query_cache:
            return None
        
        cached = self._query_cache[cache_key]
        age_seconds = (datetime.now() - cached["timestamp"]).total_seconds()
        
        # Check TTL
        if age_seconds > self._cache_ttl_seconds:
            del self._query_cache[cache_key]
            return None
        
        return {
            "event": cached["event"],
            "age_ms": int(age_seconds * 1000)
        }
    
    def _store_in_cache(self, cache_key: str, event: Dict):
        """Store result in cache with LRU eviction"""
        # Evict oldest if at capacity
        if len(self._query_cache) >= self._cache_max_size:
            oldest_key = min(self._query_cache.keys(), 
                           key=lambda k: self._query_cache[k]["timestamp"])
            del self._query_cache[oldest_key]
        
        self._query_cache[cache_key] = {
            "event": event,
            "timestamp": datetime.now()
        }
    
    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze telemetry data to identify bottlenecks"""
        if not self.resource_samples:
            return {"status": "no_data", "message": "No telemetry samples available"}
        
        # Calculate averages and identify slow queries
        agentic_samples = [s for s in self.resource_samples if s.get("used_agentic")]
        normal_samples = [s for s in self.resource_samples if not s.get("used_agentic")]
        
        avg_agentic_time = sum(s["execution_time_ms"] for s in agentic_samples) / len(agentic_samples) if agentic_samples else 0
        avg_normal_time = sum(s["execution_time_ms"] for s in normal_samples) / len(normal_samples) if normal_samples else 0
        
        # Find slowest queries
        sorted_by_time = sorted(self.resource_samples, key=lambda x: x["execution_time_ms"], reverse=True)
        slowest_queries = sorted_by_time[:5]
        
        # Identify high CPU usage queries
        high_cpu_queries = [s for s in self.resource_samples if s.get("cpu_delta", 0) > 20]
        
        # Calculate correlation between query length and execution time
        query_lengths = [len(s["query"].split()) for s in self.resource_samples]
        exec_times = [s["execution_time_ms"] for s in self.resource_samples]
        
        # Simple correlation check
        correlation = "high" if avg_agentic_time > avg_normal_time * 1.5 else "low"
        
        return {
            "status": "analyzed",
            "summary": {
                "total_samples": len(self.resource_samples),
                "agentic_samples": len(agentic_samples),
                "normal_samples": len(normal_samples),
                "avg_agentic_time_ms": round(avg_agentic_time, 1),
                "avg_normal_time_ms": round(avg_normal_time, 1),
                "agentic_overhead_ms": round(avg_agentic_time - avg_normal_time, 1),
                "peak_cpu": round(self.peak_cpu_percent, 1),
                "peak_memory": round(self.peak_memory_percent, 1),
                "agentic_correlation": correlation
            },
            "bottlenecks": {
                "slowest_queries": [
                    {"query": s["query"][:40], "time_ms": s["execution_time_ms"], "agentic": s.get("used_agentic")}
                    for s in slowest_queries
                ],
                "high_cpu_queries": len(high_cpu_queries),
                "memory_pressure": self.peak_memory_percent > 80
            },
            "recommendations": [
                "Consider caching for repeated queries" if len(self.resource_samples) > 50 else None,
                "Agentic loop adds significant overhead" if avg_agentic_time > avg_normal_time * 2 else None,
                "High memory usage detected - consider cleanup" if self.peak_memory_percent > 85 else None,
                "CPU spikes detected - consider throttling" if self.peak_cpu_percent > 50 else None
            ]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics with telemetry"""
        return {
            "components": {
                "brain_core": True,
                "task_planner": True,
                "pattern_learner": self.pattern_learner is not None,
                "cloud_llm": False,
                "agentic_loop": self.agentic_loop is not None,
                "query_refiner": self.query_refiner is not None,
                "llm_health_monitor": self.llm_health_monitor is not None,
                "multimodal_reasoner": self.multimodal_reasoner is not None,  # NEW
                "rag_service": self.rag_service is not None  # NEW
            },
            "task_planner": self.task_planner.get_stats() if self.task_planner else {},
            "pattern_learner": self.pattern_learner.get_stats() if self.pattern_learner else {},
            "performance": {
                "queries_processed": self.query_count,
                "avg_execution_time_ms": self.total_execution_time / max(self.query_count, 1),
                "agentic_queries": self.agentic_queries,
                "refined_queries": self.refined_queries,
                "llm_health_failures": self.llm_health_failures
            },
            "telemetry": {
                "peak_cpu_percent": round(self.peak_cpu_percent, 1),
                "peak_memory_percent": round(self.peak_memory_percent, 1),
                "resource_samples_count": len(self.resource_samples)
            },
            "auto_tuning": self.get_tuning_stats()  # NEW: Include tuning stats
        }


# Singleton
_unified_instance = None

def get_unified_valora_brain() -> UnifiedValoraBrain:
    """Get or create singleton unified brain"""
    global _unified_instance
    if _unified_instance is None:
        _unified_instance = UnifiedValoraBrain()
    return _unified_instance
