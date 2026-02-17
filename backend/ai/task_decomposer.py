"""
Task Decomposer - NLP-based Task Extraction from Natural Language
Extracts actionable tasks from user queries using LLM assistance.
"""

import asyncio
import json
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from ai.task_graph import TaskNode, TaskDependencyGraph, TaskGraphBuilder
from ai.task_templates import TaskTemplate, TemplateLibrary, get_template_library
from ai.decomposition_prompts import (
    format_decomposition_prompt,
    validate_decomposition_output,
    get_example_for_intent,
    TOOL_CAPABILITIES
)


@dataclass
class DecomposedTask:
    """
    A task extracted from natural language query.
    """
    id: str
    action: str                          # e.g., search, analyze, compare, navigate
    entity: str                          # e.g., property, area, POI
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_span: str = ""                # Original text that generated this task
    dependencies: List[str] = field(default_factory=list)
    task_type: str = "generic"           # map_action, gis_operation, llm_call, data_fetch
    priority: int = 1
    
    def to_task_node(self) -> TaskNode:
        """Convert to TaskNode for graph insertion"""
        return TaskNode(
            id=self.id,
            action=self.action,
            entity=self.entity,
            parameters=self.parameters,
            confidence=self.confidence,
            source_span=self.source_span,
            dependencies=self.dependencies,
            task_type=self.task_type,
            priority=self.priority
        )


@dataclass
class DecompositionResult:
    """
    Result of task decomposition.
    """
    tasks: List[DecomposedTask]
    overall_confidence: float
    reasoning: str
    method: str                          # "template", "llm", "hybrid", "fallback"
    template_used: Optional[str] = None
    execution_time_ms: int = 0
    warnings: List[str] = field(default_factory=list)
    
    def to_task_graph(self) -> TaskDependencyGraph:
        """Convert decomposition result to a task dependency graph"""
        # Create a fresh builder for each conversion
        builder = TaskGraphBuilder()
        
        for task in self.tasks:
            builder.task(
                action=task.action,
                entity=task.entity,
                parameters=task.parameters,
                dependencies=task.dependencies,
                priority=task.priority,
                task_type=task.task_type,
                confidence=task.confidence,
                source_span=task.source_span,
                task_id=task.id
            )
        
        return builder.build()


class TaskDecomposer:
    """
    NLP-based task decomposer that extracts actionable tasks from natural language.
    
    Uses a hybrid approach:
    1. Template matching for known patterns
    2. LLM-based decomposition for complex queries
    3. Fallback to rule-based extraction
    """
    
    def __init__(
        self,
        template_library: Optional[TemplateLibrary] = None,
        llm_client: Optional[Any] = None,
        confidence_threshold: float = 0.7,
        max_tasks_per_query: int = 10
    ):
        self.template_library = template_library or get_template_library()
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold
        self.max_tasks_per_query = max_tasks_per_query
        
        # Statistics
        self.decompositions_total = 0
        self.template_matches = 0
        self.llm_decompositions = 0
        self.fallback_decompositions = 0
        
        # Action verb mappings for rule-based extraction
        self._action_verbs = {
            "navigate": ["go to", "navigate", "show me", "take me", "fly to"],
            "search": ["find", "search", "look for", "show", "get"],
            "analyze": ["analyze", "study", "examine", "evaluate", "assess"],
            "compare": ["compare", "contrast", "difference", "versus", "vs"],
            "route": ["route", "directions", "how to reach", "path from"],
            "simulate": ["simulate", "what if", "predict", "forecast"]
        }
        
        # Entity patterns
        self._entity_patterns = {
            "property": [r"\d+bhk", r"apartment", r"house", r"villa", r"flat", r"property"],
            "area": [r"area", r"locality", r"neighborhood", r"region"],
            "poi": [r"poi", r"point of interest", r"place", r"spot"]
        }
    
    async def decompose(
        self,
        query: str,
        intent: str,
        slots: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> DecompositionResult:
        """
        Decompose a user query into actionable tasks.
        
        Args:
            query: User's natural language query
            intent: Detected intent
            slots: Extracted slots/entities
            context: Additional context from conversation
        
        Returns:
            DecompositionResult with extracted tasks
        """
        start_time = time.time()
        self.decompositions_total += 1
        
        # Step 1: Try template matching first
        template_result = self._try_template_match(intent, slots)
        if template_result and template_result.overall_confidence >= self.confidence_threshold:
            self.template_matches += 1
            template_result.execution_time_ms = int((time.time() - start_time) * 1000)
            return template_result
        
        # Step 2: Try LLM-based decomposition
        if self.llm_client:
            llm_result = await self._llm_decompose(query, intent, slots, context)
            if llm_result and llm_result.overall_confidence >= self.confidence_threshold:
                self.llm_decompositions += 1
                llm_result.execution_time_ms = int((time.time() - start_time) * 1000)
                return llm_result
        
        # Step 3: Fallback to rule-based decomposition
        fallback_result = self._fallback_decompose(query, intent, slots)
        self.fallback_decompositions += 1
        fallback_result.execution_time_ms = int((time.time() - start_time) * 1000)
        return fallback_result
    
    def _try_template_match(
        self,
        intent: str,
        slots: Dict[str, Any]
    ) -> Optional[DecompositionResult]:
        """Try to match query to an existing template"""
        # Find matching templates
        matching_templates = self.template_library.find_matching_templates(intent)
        
        for template in matching_templates:
            # Validate parameters
            is_valid, errors = template.validate_parameters(slots)
            
            if is_valid:
                # Render tasks from template
                task_dicts = template.render_tasks(slots)
                
                tasks = []
                for task_data in task_dicts:
                    task = DecomposedTask(
                        id=task_data["id"],
                        action=task_data["action"],
                        entity=task_data["entity"],
                        parameters=task_data["parameters"],
                        dependencies=task_data.get("dependencies", []),
                        task_type=task_data.get("task_type", "generic"),
                        priority=task_data.get("priority", 1),
                        confidence=0.95  # High confidence for template matches
                    )
                    tasks.append(task)
                
                return DecompositionResult(
                    tasks=tasks,
                    overall_confidence=template.success_rate if template.execution_count > 0 else 0.9,
                    reasoning=f"Matched template: {template.name}",
                    method="template",
                    template_used=template.id
                )
        
        return None
    
    async def _llm_decompose(
        self,
        query: str,
        intent: str,
        slots: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[DecompositionResult]:
        """Use LLM to decompose complex queries"""
        try:
            # Format prompt
            prompt = format_decomposition_prompt(
                query=query,
                intent=intent,
                slots=slots,
                context=context,
                include_examples=True
            )
            
            # Call LLM
            if hasattr(self.llm_client, 'generate'):
                response = await self.llm_client.generate(prompt)
            elif hasattr(self.llm_client, 'chat'):
                response = await self.llm_client.chat([
                    {"role": "system", "content": "You are a task decomposition expert."},
                    {"role": "user", "content": prompt}
                ])
            else:
                # Synchronous fallback
                response = self.llm_client(prompt)
            
            # Parse response
            result = self._parse_llm_response(response)
            
            if result:
                result.method = "llm"
                return result
            
        except Exception as e:
            print(f"[TaskDecomposer] LLM decomposition failed: {e}")
        
        return None
    
    def _parse_llm_response(self, response: str) -> Optional[DecompositionResult]:
        """Parse LLM response into DecompositionResult"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                return None
            
            data = json.loads(json_match.group())
            
            # Validate output
            is_valid, errors = validate_decomposition_output(data)
            if not is_valid:
                print(f"[TaskDecomposer] Validation errors: {errors}")
                return None
            
            # Convert to DecomposedTask objects
            tasks = []
            for task_data in data.get("tasks", []):
                task = DecomposedTask(
                    id=task_data["id"],
                    action=task_data["action"],
                    entity=task_data["entity"],
                    parameters=task_data.get("parameters", {}),
                    dependencies=task_data.get("dependencies", []),
                    task_type=task_data.get("task_type", "generic"),
                    priority=task_data.get("priority", 1),
                    confidence=task_data.get("confidence", 0.8),
                    source_span=task_data.get("source_span", "")
                )
                tasks.append(task)
            
            return DecompositionResult(
                tasks=tasks,
                overall_confidence=data.get("overall_confidence", 0.8),
                reasoning=data.get("reasoning", "LLM decomposition"),
                method="llm",
                warnings=errors if not is_valid else []
            )
            
        except json.JSONDecodeError as e:
            print(f"[TaskDecomposer] JSON parse error: {e}")
            return None
    
    def _fallback_decompose(
        self,
        query: str,
        intent: str,
        slots: Dict[str, Any]
    ) -> DecompositionResult:
        """Fallback rule-based decomposition"""
        tasks = []
        task_counter = 0
        
        # Detect action from query
        detected_action = self._detect_action(query, intent)
        
        # Detect entities
        entities = self._detect_entities(query, slots)
        
        # Generate tasks based on intent
        if intent == "navigate":
            location = slots.get("location", "")
            if location:
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_geocode",
                    action="geocode",
                    entity="location",
                    task_type="gis_operation",
                    parameters={"location": location},
                    confidence=0.9,
                    source_span=location
                ))
                
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_flyto",
                    action="flyTo",
                    entity="location",
                    task_type="map_action",
                    parameters={"location": location, "zoom": 16},
                    dependencies=[f"t{task_counter-1}_geocode"],
                    confidence=0.85,
                    source_span=query
                ))
        
        elif intent == "property_search":
            location = slots.get("location", "")
            bhk = slots.get("bhk")
            budget = slots.get("budget")
            
            if location:
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_geocode",
                    action="geocode",
                    entity="location",
                    task_type="gis_operation",
                    parameters={"location": location},
                    confidence=0.9,
                    source_span=location
                ))
                
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_flyto",
                    action="flyTo",
                    entity="location",
                    task_type="map_action",
                    parameters={"location": location, "zoom": 15},
                    dependencies=[f"t{task_counter-1}_geocode"],
                    confidence=0.85,
                    source_span=location
                ))
                
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_query",
                    action="spatialQuery",
                    entity="property",
                    task_type="gis_operation",
                    parameters={
                        "location": location,
                        "radius": 2000,
                        "filters": {"bhk": bhk, "budget_max": budget}
                    },
                    dependencies=[f"t{task_counter-2}_geocode"],
                    confidence=0.8,
                    source_span=query
                ))
        
        elif intent == "analyze_area":
            location = slots.get("location", "")
            if location:
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_geocode",
                    action="geocode",
                    entity="location",
                    task_type="gis_operation",
                    parameters={"location": location},
                    confidence=0.9,
                    source_span=location
                ))
                
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_flyto",
                    action="flyTo",
                    entity="location",
                    task_type="map_action",
                    parameters={"location": location, "zoom": 15},
                    dependencies=[f"t{task_counter-1}_geocode"],
                    confidence=0.85,
                    source_span=location
                ))
                
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_metrics",
                    action="areaMetrics",
                    entity="area",
                    task_type="gis_operation",
                    parameters={
                        "location": location,
                        "metrics": ["price_trend", "livability", "connectivity", "risk"]
                    },
                    dependencies=[f"t{task_counter-2}_geocode"],
                    confidence=0.85,
                    source_span=query
                ))
        
        elif intent == "comparison":
            loc_a = slots.get("location_a", slots.get("location", ""))
            loc_b = slots.get("location_b", "")
            
            if loc_a:
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_geocode_a",
                    action="geocode",
                    entity="location_a",
                    task_type="gis_operation",
                    parameters={"location": loc_a},
                    confidence=0.9,
                    source_span=loc_a
                ))
                
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_metrics_a",
                    action="areaMetrics",
                    entity="area_a",
                    task_type="gis_operation",
                    parameters={"location": loc_a},
                    dependencies=[f"t{task_counter-1}_geocode_a"],
                    confidence=0.85,
                    source_span=loc_a
                ))
            
            if loc_b:
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_geocode_b",
                    action="geocode",
                    entity="location_b",
                    task_type="gis_operation",
                    parameters={"location": loc_b},
                    confidence=0.9,
                    source_span=loc_b
                ))
                
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_metrics_b",
                    action="areaMetrics",
                    entity="area_b",
                    task_type="gis_operation",
                    parameters={"location": loc_b},
                    dependencies=[f"t{task_counter-1}_geocode_b"],
                    confidence=0.85,
                    source_span=loc_b
                ))
        
        elif intent == "route_analysis":
            from_loc = slots.get("from_location", "")
            to_loc = slots.get("to_location", "")
            
            if from_loc:
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_geocode_from",
                    action="geocode",
                    entity="start",
                    task_type="gis_operation",
                    parameters={"location": from_loc},
                    confidence=0.9,
                    source_span=from_loc
                ))
            
            if to_loc:
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_geocode_to",
                    action="geocode",
                    entity="end",
                    task_type="gis_operation",
                    parameters={"location": to_loc},
                    confidence=0.9,
                    source_span=to_loc
                ))
            
            if from_loc and to_loc:
                task_counter += 1
                tasks.append(DecomposedTask(
                    id=f"t{task_counter}_route",
                    action="routeAnalysis",
                    entity="route",
                    task_type="gis_operation",
                    parameters={"from": from_loc, "to": to_loc, "mode": "driving"},
                    dependencies=["t1_geocode_from", "t2_geocode_to"],
                    confidence=0.85,
                    source_span=query
                ))
        
        # Default fallback if no tasks generated
        if not tasks:
            location = slots.get("location", "")
            if location:
                tasks.append(DecomposedTask(
                    id="t1_default",
                    action="flyTo",
                    entity="location",
                    task_type="map_action",
                    parameters={"location": location},
                    confidence=0.6,
                    source_span=query
                ))
        
        return DecompositionResult(
            tasks=tasks[:self.max_tasks_per_query],
            overall_confidence=0.75,  # Lower confidence for fallback
            reasoning="Rule-based fallback decomposition",
            method="fallback",
            warnings=["Used fallback decomposition - may not be optimal"]
        )
    
    def _detect_action(self, query: str, intent: str) -> str:
        """Detect the primary action from query"""
        query_lower = query.lower()
        
        for action, verbs in self._action_verbs.items():
            for verb in verbs:
                if verb in query_lower:
                    return action
        
        # Map intent to action
        intent_action_map = {
            "navigate": "navigate",
            "property_search": "search",
            "analyze_area": "analyze",
            "comparison": "compare",
            "route_analysis": "route",
            "simulate": "simulate"
        }
        
        return intent_action_map.get(intent, "search")
    
    def _detect_entities(self, query: str, slots: Dict[str, Any]) -> List[str]:
        """Detect entity types from query"""
        entities = []
        query_lower = query.lower()
        
        for entity_type, patterns in self._entity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    entities.append(entity_type)
                    break
        
        # Add entities from slots
        if "bhk" in slots or "property" in slots:
            if "property" not in entities:
                entities.append("property")
        
        if "location" in slots:
            if "area" not in entities:
                entities.append("area")
        
        return entities
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get decomposer statistics"""
        return {
            "total_decompositions": self.decompositions_total,
            "template_matches": self.template_matches,
            "llm_decompositions": self.llm_decompositions,
            "fallback_decompositions": self.fallback_decompositions,
            "template_match_rate": self.template_matches / max(1, self.decompositions_total),
            "llm_rate": self.llm_decompositions / max(1, self.decompositions_total),
            "fallback_rate": self.fallback_decompositions / max(1, self.decompositions_total)
        }


# Singleton instance
_task_decomposer: Optional[TaskDecomposer] = None

def get_task_decomposer(
    template_library: Optional[TemplateLibrary] = None,
    llm_client: Optional[Any] = None
) -> TaskDecomposer:
    """Get or create singleton TaskDecomposer instance"""
    global _task_decomposer
    if _task_decomposer is None:
        _task_decomposer = TaskDecomposer(
            template_library=template_library,
            llm_client=llm_client
        )
    return _task_decomposer
