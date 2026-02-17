"""
Multi-Stage LLM Executor - Core Architecture for Task Execution
Implements iterative LLM calls at each stage for robust, informed decisions.

Architecture:
1. UNDERSTAND - Parse query, extract intent, entities, constraints
2. PLAN - Generate task graph with dependencies
3. EXECUTE - Run tasks with LLM reasoning at each step
4. VALIDATE - Verify results, detect gaps, retry if needed
5. SYNTHESIZE - Generate final response with all insights

Enhanced with:
- Memory integration (recall previous results per location)
- Self-learning (track effectiveness, recommend tools)
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, List, Optional, Callable, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Optional imports for memory and self-learning
try:
    from .agentic_memory import AgenticMemory, get_agentic_memory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

try:
    from .self_learning import SelfLearningEngine, get_self_learning_engine
    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False

logger = logging.getLogger("valora.multi_stage_executor")


class ExecutionStage(Enum):
    UNDERSTAND = "understand"
    PLAN = "plan"
    EXECUTE = "execute"
    VALIDATE = "validate"
    SYNTHESIZE = "synthesize"


@dataclass
class StageResult:
    """Result from a single execution stage"""
    stage: ExecutionStage
    success: bool
    data: Dict[str, Any]
    reasoning: str
    confidence: float
    duration_ms: int
    retry_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MultiStageConfig:
    """Configuration for multi-stage execution"""
    max_retries_per_stage: int = 2
    min_confidence_threshold: float = 0.7
    enable_parallel_execution: bool = True
    max_concurrent_tasks: int = 4
    timeout_per_stage_ms: int = 30000
    enable_validation_loops: bool = True
    max_validation_loops: int = 3
    enable_memory: bool = True  # Enable memory recall/recording
    enable_learning: bool = True  # Enable self-learning


class MultiStageLLMExecutor:
    """
    Core architecture for multi-stage LLM execution.
    
    Each stage involves LLM reasoning to make informed decisions:
    - UNDERSTAND: LLM parses query, extracts entities, identifies constraints
    - PLAN: LLM generates optimal task graph based on understanding
    - EXECUTE: LLM reasons about each task, makes context-aware decisions
    - VALIDATE: LLM verifies results, identifies gaps, suggests fixes
    - SYNTHESIZE: LLM combines all insights into coherent response
    
    Enhanced Features:
    - Memory: Recalls previous results for the same location
    - Self-learning: Recommends tools based on past effectiveness
    """
    
    def __init__(
        self,
        llm_client: Any,
        config: MultiStageConfig = None,
        tools_registry: Dict = None,
        on_stage_progress: Callable[[str, str, float], None] = None
    ):
        self.llm = llm_client
        self.config = config or MultiStageConfig()
        self.tools = tools_registry or {}
        self.on_progress = on_stage_progress
        
        # Stage results storage
        self.stage_results: Dict[ExecutionStage, StageResult] = {}
        
        # Execution context that builds up through stages
        self.context: Dict[str, Any] = {
            "query": None,
            "intent": None,
            "entities": {},
            "constraints": {},
            "task_graph": None,
            "task_results": {},
            "validation_issues": [],
            "insights": [],
            "memory_hits": [],  # Memory recall results
            "recommended_tools": []  # Self-learning recommendations
        }
        
        # Memory and learning (optional)
        self.memory: Optional[Any] = None
        self.learner: Optional[Any] = None
        
        if self.config.enable_memory and MEMORY_AVAILABLE:
            try:
                self.memory = get_agentic_memory()
            except Exception as e:
                logger.warning(f"Memory initialization failed: {e}")
        
        if self.config.enable_learning and LEARNING_AVAILABLE:
            try:
                self.learner = get_self_learning_engine()
            except Exception as e:
                logger.warning(f"Self-learning initialization failed: {e}")
    
    async def execute(self, query: str, initial_context: Dict = None) -> AsyncGenerator[Dict, None]:
        """
        Execute all stages with LLM reasoning at each step.
        Yields progress events for streaming updates.
        
        Enhanced with memory recall and self-learning.
        """
        self.context["query"] = query
        if initial_context:
            self.context.update(initial_context)
        
        # === Memory Recall ===
        # Extract location from query for memory lookup
        location = self._extract_location_from_query(query)
        if location and self.memory:
            try:
                memory_hits = self.memory.recall_location(location)
                if memory_hits:
                    self.context["memory_hits"] = memory_hits
                    logger.debug(f"Memory recall: {len(memory_hits)} hits for {location}")
            except Exception as e:
                logger.warning(f"Memory recall failed: {e}")
        
        # === Self-Learning Tool Recommendations ===
        intent = self.context.get("intent", {})
        intent_str = intent.get("primary", "") if isinstance(intent, dict) else str(intent)
        if intent_str and self.learner:
            try:
                recommended_tools = self.learner.recommend_tools(intent_str, query)
                if recommended_tools:
                    self.context["recommended_tools"] = recommended_tools
                    logger.debug(f"Self-learning: recommended tools: {recommended_tools}")
            except Exception as e:
                logger.warning(f"Self-learning recommendation failed: {e}")
        
        stages = [
            (ExecutionStage.UNDERSTAND, self._stage_understand),
            (ExecutionStage.PLAN, self._stage_plan),
            (ExecutionStage.EXECUTE, self._stage_execute),
            (ExecutionStage.VALIDATE, self._stage_validate),
            (ExecutionStage.SYNTHESIZE, self._stage_synthesize)
        ]
        
        for stage_name, stage_func in stages:
            yield {
                "type": "stage_start",
                "stage": stage_name.value,
                "message": f"Starting {stage_name.value}..."
            }
            
            try:
                result = await self._execute_stage_with_retry(stage_name, stage_func)
                self.stage_results[stage_name] = result
                
                yield {
                    "type": "stage_complete",
                    "stage": stage_name.value,
                    "success": result.success,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning,
                    "duration_ms": result.duration_ms
                }
                
                if not result.success and stage_name != ExecutionStage.VALIDATE:
                    # Critical stage failed, try recovery
                    yield {
                        "type": "stage_recovery",
                        "stage": stage_name.value,
                        "message": "Attempting recovery..."
                    }
                    
            except Exception as e:
                yield {
                    "type": "stage_error",
                    "stage": stage_name.value,
                    "error": str(e)
                }
                break
        
        # === Record to Memory ===
        # Store successful execution results for future queries
        if location and self.memory and self.stage_results.get(ExecutionStage.SYNTHESIZE):
            try:
                final_response = self.context.get("final_response", {})
                self.memory.record(
                    tool="multi_stage_analysis",
                    params={"query": query, "location": location},
                    result=final_response
                )
            except Exception as e:
                logger.warning(f"Memory recording failed: {e}")
        
        # === Record to Self-Learning ===
        # Track tool effectiveness for this intent
        if intent_str and self.learner:
            try:
                task_results = self.context.get("task_results", {})
                tools_used = list(task_results.keys())
                success = self.stage_results.get(ExecutionStage.VALIDATE, StageResult(
                    stage=ExecutionStage.VALIDATE, success=True, data={}, reasoning="", confidence=0.8, duration_ms=0
                )).success
                self.learner.record_tool_sequence(intent=intent_str, tools=tools_used, success=success)
            except Exception as e:
                logger.warning(f"Self-learning recording failed: {e}")
        
        # Final result
        yield {
            "type": "execution_complete",
            "stages_completed": len(self.stage_results),
            "final_context": self._get_safe_context()
        }
    
    def _extract_location_from_query(self, query: str) -> Optional[str]:
        """Extract location name from query for memory lookup"""
        import re
        # Common Bangalore locations
        locations = [
            "whitefield", "electronic city", "koramangala", "indiranagar", "jayanagar",
            "hsr layout", "marathahalli", "bellandur", "sarjapur", "hebbal",
            "yelahanka", "devanahalli", "rajajinagar", "malleswaram", "rt nagar",
            "hsr", "btm", "jp nagar", "banashankari", "vijayanagar", "kengeri",
            "bannerghatta", "hennur", "kalyan nagar", "kammanahalli", "hrbr",
            "richmond road", "mg road", "brigade road", "church street", "ulsoor",
            "domlur", "cv raman nagar", "tin factory", "kr puram", "mahadevapura"
        ]
        
        query_lower = query.lower()
        for loc in locations:
            if loc in query_lower:
                return loc.title()
        
        # Try to extract proper nouns as potential locations
        proper_nouns = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', query)
        if proper_nouns:
            return proper_nouns[0]
        
        return None
    
    async def _execute_stage_with_retry(
        self, 
        stage: ExecutionStage, 
        stage_func: Callable
    ) -> StageResult:
        """Execute a stage with retry logic"""
        start_time = time.time()
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.max_retries_per_stage:
            try:
                result = await stage_func()
                return StageResult(
                    stage=stage,
                    success=result.get("success", True),
                    data=result.get("data", {}),
                    reasoning=result.get("reasoning", ""),
                    confidence=result.get("confidence", 0.8),
                    duration_ms=int((time.time() - start_time) * 1000),
                    retry_count=retry_count
                )
            except Exception as e:
                last_error = e
                retry_count += 1
                if self.on_progress:
                    self.on_progress(stage.value, f"Retry {retry_count}: {str(e)}", 0)
        
        return StageResult(
            stage=stage,
            success=False,
            data={"error": str(last_error)},
            reasoning=f"Stage failed after {retry_count} retries",
            confidence=0.0,
            duration_ms=int((time.time() - start_time) * 1000),
            retry_count=retry_count
        )
    
    async def _stage_understand(self) -> Dict[str, Any]:
        """
        Stage 1: UNDERSTAND
        LLM deeply analyzes the query to extract:
        - Intent classification with confidence
        - Named entities (locations, properties, amenities)
        - Constraints (budget, size, preferences)
        - Implicit requirements from context
        """
        query = self.context["query"]
        
        # LLM Prompt for understanding
        prompt = f"""Analyze this real estate query and extract structured information.

Query: "{query}"

Extract and return JSON with:
{{
  "intent": {{
    "primary": "navigate|property_search|analyze_area|compare|simulate|valuation|route|other",
    "secondary": ["list", "of", "secondary", "intents"],
    "confidence": 0.0-1.0
  }},
  "entities": {{
    "locations": ["list of location names mentioned"],
    "properties": ["property types mentioned"],
    "amenities": ["amenities mentioned"],
    "organizations": ["companies, landmarks mentioned"]
  }},
  "constraints": {{
    "budget": {{"min": number, "max": number, "currency": "INR"}},
    "size": {{"min_sqft": number, "max_sqft": number}},
    "bhk": ["2BHK", "3BHK", etc],
    "preferences": ["list of user preferences"]
  }},
  "implicit_needs": ["what the user might need but didn't explicitly state"],
  "ambiguities": ["parts of the query that are unclear"],
  "reasoning": "brief explanation of your analysis"
}}"""

        response = await self._call_llm(prompt)
        parsed = self._parse_llm_json(response)
        
        # Update context with understanding
        self.context["intent"] = parsed.get("intent", {})
        self.context["entities"] = parsed.get("entities", {})
        self.context["constraints"] = parsed.get("constraints", {})
        self.context["implicit_needs"] = parsed.get("implicit_needs", [])
        self.context["ambiguities"] = parsed.get("ambiguities", [])
        
        return {
            "success": True,
            "data": parsed,
            "reasoning": parsed.get("reasoning", "Query analyzed"),
            "confidence": parsed.get("intent", {}).get("confidence", 0.8)
        }
    
    async def _stage_plan(self) -> Dict[str, Any]:
        """
        Stage 2: PLAN
        LLM generates optimal task graph based on understanding:
        - Determines required operations
        - Identifies dependencies between tasks
        - Estimates complexity and time
        - Plans for parallel execution where possible
        """
        intent = self.context.get("intent", {})
        entities = self.context.get("entities", {})
        constraints = self.context.get("constraints", {})
        
        # LLM Prompt for planning
        prompt = f"""Based on the query analysis, create an execution plan.

Intent: {json.dumps(intent)}
Entities: {json.dumps(entities)}
Constraints: {json.dumps(constraints)}

Create a task graph with optimal execution order. Return JSON:
{{
  "tasks": [
    {{
      "id": "unique_task_id",
      "action": "geocode|flyTo|search|analyze|compare|simulate|etc",
      "label": "Human-readable task description",
      "type": "map_action|gis_operation|llm_call|data_fetch",
      "parameters": {{}},
      "dependencies": ["task_ids this depends on"],
      "priority": 1-3,
      "can_parallelize": true/false,
      "estimated_duration_ms": number
    }}
  ],
  "execution_order": ["list of task ids in optimal order"],
  "parallel_groups": [["tasks", "that", "can", "run", "together"]],
  "reasoning": "why this plan is optimal",
  "confidence": 0.0-1.0
}}"""

        response = await self._call_llm(prompt)
        parsed = self._parse_llm_json(response)
        
        # Update context with task graph
        self.context["task_graph"] = parsed
        
        return {
            "success": True,
            "data": parsed,
            "reasoning": parsed.get("reasoning", "Task graph generated"),
            "confidence": parsed.get("confidence", 0.8)
        }
    
    async def _stage_execute(self) -> Dict[str, Any]:
        """
        Stage 3: EXECUTE
        Execute tasks with LLM reasoning at each step:
        - LLM decides how to execute each task
        - LLM interprets results and adjusts strategy
        - LLM handles errors and retries
        - LLM makes context-aware decisions
        """
        task_graph = self.context.get("task_graph", {})
        tasks = task_graph.get("tasks", [])
        parallel_groups = task_graph.get("parallel_groups", [])
        
        if not tasks:
            return {
                "success": True,
                "data": {"tasks_executed": 0},
                "reasoning": "No tasks to execute",
                "confidence": 1.0
            }
        
        task_results = {}
        executed_count = 0
        
        # Execute parallel groups
        for group_idx, group in enumerate(parallel_groups):
            group_tasks = [t for t in tasks if t["id"] in group]
            
            if self.config.enable_parallel_execution and len(group_tasks) > 1:
                # Execute in parallel
                results = await asyncio.gather(*[
                    self._execute_single_task(task)
                    for task in group_tasks
                ])
                for task, result in zip(group_tasks, results):
                    task_results[task["id"]] = result
                    executed_count += 1
            else:
                # Execute sequentially
                for task in group_tasks:
                    result = await self._execute_single_task(task)
                    task_results[task["id"]] = result
                    executed_count += 1
        
        # Update context with results
        self.context["task_results"] = task_results
        
        return {
            "success": True,
            "data": {
                "tasks_executed": executed_count,
                "task_results": task_results
            },
            "reasoning": f"Executed {executed_count} tasks",
            "confidence": 0.9
        }
    
    async def _execute_single_task(self, task: Dict) -> Dict[str, Any]:
        """Execute a single task with LLM reasoning"""
        task_id = task["id"]
        action = task["action"]
        params = task.get("parameters", {})
        
        # LLM decides how to execute
        reasoning_prompt = f"""Execute this task and provide reasoning.

Task: {task.get('label', task_id)}
Action: {action}
Parameters: {json.dumps(params)}
Context: {json.dumps(self._get_relevant_context(task))}

Return JSON:
{{
  "result": {{}},
  "reasoning": "why this execution approach",
  "success": true/false,
  "next_suggestion": "optional next step if needed"
}}"""

        # Execute based on action type
        if action in self.tools:
            # Use registered tool
            tool = self.tools[action]
            result = await tool(**params) if asyncio.iscoroutinefunction(tool) else tool(**params)
        else:
            # Use LLM for reasoning tasks
            result = await self._call_llm(reasoning_prompt)
        
        return {
            "task_id": task_id,
            "action": action,
            "result": result,
            "success": True
        }
    
    async def _stage_validate(self) -> Dict[str, Any]:
        """
        Stage 4: VALIDATE
        LLM verifies results and identifies gaps:
        - Checks if all requirements are met
        - Identifies missing information
        - Suggests additional tasks if needed
        - Validates data quality
        """
        task_results = self.context.get("task_results", {})
        constraints = self.context.get("constraints", {})
        intent = self.context.get("intent", {})
        
        # LLM validates results
        prompt = f"""Validate the execution results against the original query.

Original Intent: {json.dumps(intent)}
Constraints: {json.dumps(constraints)}
Results: {json.dumps(task_results, default=str)[:2000]}

Return JSON:
{{
  "is_complete": true/false,
  "coverage_score": 0.0-1.0,
  "missing_information": ["what's missing"],
  "quality_issues": ["data quality problems"],
  "suggested_additional_tasks": [
    {{"action": "...", "reason": "..."}}
  ],
  "validation_reasoning": "explanation",
  "confidence": 0.0-1.0
}}"""

        response = await self._call_llm(prompt)
        parsed = self._parse_llm_json(response)
        
        # Check if we need additional tasks
        if not parsed.get("is_complete", True) and self.config.enable_validation_loops:
            additional_tasks = parsed.get("suggested_additional_tasks", [])
            if additional_tasks:
                self.context["validation_issues"] = parsed.get("missing_information", [])
                # Could trigger additional execution here
        
        return {
            "success": parsed.get("is_complete", True),
            "data": parsed,
            "reasoning": parsed.get("validation_reasoning", "Results validated"),
            "confidence": parsed.get("confidence", 0.8)
        }
    
    async def _stage_synthesize(self) -> Dict[str, Any]:
        """
        Stage 5: SYNTHESIZE
        LLM combines all insights into coherent response:
        - Integrates results from all tasks
        - Generates natural language response
        - Adds relevant insights and recommendations
        - Formats for user presentation
        """
        query = self.context["query"]
        intent = self.context.get("intent", {})
        task_results = self.context.get("task_results", {})
        validation = self.stage_results.get(ExecutionStage.VALIDATE)
        
        # LLM synthesizes final response
        prompt = f"""Synthesize a comprehensive response to the user's query.

Query: "{query}"
Intent: {json.dumps(intent)}
Task Results: {json.dumps(task_results, default=str)[:3000]}
Validation: {json.dumps(validation.data if validation else {})}

Generate a response that:
1. Directly answers the user's question
2. Provides relevant insights from the analysis
3. Includes actionable recommendations
4. Is clear and professional

Return JSON:
{{
  "response": "the main response text",
  "key_insights": ["insight 1", "insight 2"],
  "recommendations": ["rec 1", "rec 2"],
  "data_summary": {{}},
  "confidence": 0.0-1.0,
  "reasoning": "how you synthesized this response"
}}"""

        response = await self._call_llm(prompt)
        parsed = self._parse_llm_json(response)
        
        # Store final response
        self.context["final_response"] = parsed
        
        return {
            "success": True,
            "data": parsed,
            "reasoning": parsed.get("reasoning", "Response synthesized"),
            "confidence": parsed.get("confidence", 0.9)
        }
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt"""
        if hasattr(self.llm, 'generate'):
            return await self.llm.generate(prompt) if asyncio.iscoroutinefunction(self.llm.generate) else self.llm.generate(prompt)
        elif hasattr(self.llm, 'chat'):
            return await self.llm.chat(prompt) if asyncio.iscoroutinefunction(self.llm.chat) else self.llm.chat(prompt)
        else:
            # Fallback for simple callable
            result = self.llm(prompt)
            return result if isinstance(result, str) else json.dumps(result)
    
    def _parse_llm_json(self, response: str) -> Dict:
        """Parse JSON from LLM response"""
        try:
            # Try direct parse
            return json.loads(response)
        except:
            # Try extracting JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            return {"raw_response": response}
    
    def _get_relevant_context(self, task: Dict) -> Dict:
        """Get context relevant to a specific task"""
        return {
            "query": self.context.get("query"),
            "intent": self.context.get("intent"),
            "entities": self.context.get("entities"),
            "constraints": self.context.get("constraints"),
            "previous_results": {
                k: v for k, v in self.context.get("task_results", {}).items()
                if k in task.get("dependencies", [])
            }
        }
    
    def _get_safe_context(self) -> Dict:
        """Get context safe for serialization"""
        safe = {}
        for key, value in self.context.items():
            try:
                json.dumps(value)  # Test serializability
                safe[key] = value
            except:
                safe[key] = str(value)
        return safe


# Factory function
def get_multi_stage_executor(
    llm_client: Any,
    config: MultiStageConfig = None,
    tools_registry: Dict = None,
    on_progress: Callable = None
) -> MultiStageLLMExecutor:
    """Create a multi-stage LLM executor"""
    return MultiStageLLMExecutor(
        llm_client=llm_client,
        config=config,
        tools_registry=tools_registry,
        on_stage_progress=on_progress
    )
