"""
Template Generator - Auto-generate Task Templates from Successful Executions
Analyzes execution patterns and creates reusable templates.
"""

import json
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import sqlite3
import os

from ai.task_templates import TaskTemplate, TaskSpec, TemplateLibrary
from ai.task_graph import TaskNode


@dataclass
class ExecutionPattern:
    """A pattern extracted from execution history"""
    pattern_id: str
    intent: str
    task_sequence: List[Dict[str, Any]]
    parameter_patterns: Dict[str, Any]
    success_count: int = 0
    total_count: int = 0
    avg_duration_ms: int = 0
    first_seen: str = ""
    last_seen: str = ""
    
    @property
    def success_rate(self) -> float:
        return self.success_count / max(1, self.total_count)


@dataclass
class TemplateCandidate:
    """A candidate template generated from patterns"""
    name: str
    description: str
    intent_patterns: List[str]
    parameter_schema: Dict[str, Any]
    task_sequence: List[TaskSpec]
    confidence: float
    source_pattern_id: str
    sample_count: int


class TemplateGenerator:
    """
    Automatically generates task templates from successful execution patterns.
    
    Process:
    1. Analyze successful task sequences
    2. Extract common patterns
    3. Parameterize templates
    4. Validate and store templates
    """
    
    def __init__(
        self,
        template_library: Optional[TemplateLibrary] = None,
        db_path: str = "valora_templates.db",
        min_samples: int = 5,
        min_success_rate: float = 0.8
    ):
        self.template_library = template_library or TemplateLibrary(db_path)
        self.db_path = db_path
        self.min_samples = min_samples
        self.min_success_rate = min_success_rate
        
        # Pattern storage
        self._patterns: Dict[str, ExecutionPattern] = {}
        
        # Statistics
        self._templates_generated = 0
        self._patterns_analyzed = 0
    
    def analyze_execution(
        self,
        tasks: List[TaskNode],
        intent: str,
        success: bool,
        duration_ms: int
    ) -> Optional[str]:
        """
        Analyze a single execution and update patterns.
        
        Returns:
            Pattern ID if a pattern was identified, None otherwise
        """
        if not tasks:
            return None
        
        self._patterns_analyzed += 1
        
        # Generate pattern signature
        signature = self._generate_signature(tasks, intent)
        
        if signature not in self._patterns:
            # Create new pattern
            self._patterns[signature] = ExecutionPattern(
                pattern_id=signature,
                intent=intent,
                task_sequence=[self._task_to_pattern(t) for t in tasks],
                parameter_patterns=self._extract_parameter_patterns(tasks),
                first_seen=datetime.now().isoformat()
            )
        
        # Update pattern statistics
        pattern = self._patterns[signature]
        pattern.total_count += 1
        if success:
            pattern.success_count += 1
        
        # Update average duration
        pattern.avg_duration_ms = (
            (pattern.avg_duration_ms * (pattern.total_count - 1) + duration_ms) 
            / pattern.total_count
        )
        pattern.last_seen = datetime.now().isoformat()
        
        return signature
    
    def _generate_signature(self, tasks: List[TaskNode], intent: str) -> str:
        """Generate a unique signature for a task sequence"""
        # Create signature from task types and actions
        task_signature = "|".join(
            f"{t.task_type}:{t.action}:{t.entity}" 
            for t in tasks
        )
        
        # Include dependency structure
        dep_signature = "|".join(
            f"{t.id}:{','.join(sorted(t.dependencies))}"
            for t in tasks
        )
        
        return f"{intent}:{task_signature}:{dep_signature}"
    
    def _task_to_pattern(self, task: TaskNode) -> Dict[str, Any]:
        """Convert a task to a pattern representation"""
        return {
            "action": task.action,
            "entity": task.entity,
            "task_type": task.task_type,
            "parameters": self._parameterize(task.parameters),
            "dependencies": task.dependencies,
            "priority": task.priority
        }
    
    def _parameterize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert concrete parameters to parameterized form"""
        parameterized = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                # Check if it's a location-like value
                if self._is_location(value):
                    parameterized[key] = "${location}"
                elif self._is_numeric_string(value):
                    parameterized[key] = f"${{{key}}}"
                else:
                    parameterized[key] = f"${{{key}}}"
            elif isinstance(value, (int, float)):
                parameterized[key] = f"${{{key}}}"
            elif isinstance(value, dict):
                parameterized[key] = self._parameterize(value)
            elif isinstance(value, list):
                parameterized[key] = [self._parameterize({"item": v})["item"] for v in value]
            else:
                parameterized[key] = f"${{{key}}}"
        
        return parameterized
    
    def _is_location(self, value: str) -> bool:
        """Check if a string value looks like a location"""
        location_patterns = [
            r'\b(nagar|layout|colony|town|city|area|sector|block|street)\b',
            r'\b(bangalore|bengaluru|delhi|mumbai|chennai|hyderabad|kolkata)\b'
        ]
        
        for pattern in location_patterns:
            if re.search(pattern, value.lower()):
                return True
        
        return False
    
    def _is_numeric_string(self, value: str) -> bool:
        """Check if a string represents a number"""
        try:
            float(value.replace(',', ''))
            return True
        except ValueError:
            return False
    
    def _extract_parameter_patterns(self, tasks: List[TaskNode]) -> Dict[str, Any]:
        """Extract parameter patterns from tasks"""
        patterns = {}
        
        for task in tasks:
            for key, value in task.parameters.items():
                if key not in patterns:
                    patterns[key] = set()
                
                if isinstance(value, str):
                    patterns[key].add("string")
                elif isinstance(value, int):
                    patterns[key].add("integer")
                elif isinstance(value, float):
                    patterns[key].add("number")
                elif isinstance(value, bool):
                    patterns[key].add("boolean")
                elif isinstance(value, list):
                    patterns[key].add("array")
                elif isinstance(value, dict):
                    patterns[key].add("object")
        
        # Convert sets to lists
        return {k: list(v) for k, v in patterns.items()}
    
    def generate_templates(self) -> List[TaskTemplate]:
        """
        Generate templates from accumulated patterns.
        
        Returns:
            List of generated templates
        """
        generated = []
        
        for pattern_id, pattern in self._patterns.items():
            # Check if pattern meets criteria
            if pattern.total_count < self.min_samples:
                continue
            
            if pattern.success_rate < self.min_success_rate:
                continue
            
            # Generate template candidate
            candidate = self._create_candidate(pattern)
            
            if candidate:
                # Create template
                template = self._candidate_to_template(candidate)
                
                # Add to library
                if self.template_library.add_template(template):
                    generated.append(template)
                    self._templates_generated += 1
        
        return generated
    
    def _create_candidate(self, pattern: ExecutionPattern) -> Optional[TemplateCandidate]:
        """Create a template candidate from a pattern"""
        # Generate name from intent and actions
        actions = [t["action"] for t in pattern.task_sequence]
        name = f"{pattern.intent}_{'_'.join(actions[:3])}"
        
        # Generate description
        description = f"Auto-generated template for {pattern.intent} intent"
        
        # Generate intent patterns
        intent_patterns = [
            re.escape(pattern.intent),
            f".*{pattern.intent}.*"
        ]
        
        # Build parameter schema
        parameter_schema = self._build_parameter_schema(pattern)
        
        # Convert task sequence to TaskSpecs
        task_specs = []
        for i, task_data in enumerate(pattern.task_sequence):
            spec = TaskSpec(
                id_template=f"t{i+1}_${{location}}_{task_data['action']}",
                action=task_data["action"],
                entity=task_data["entity"],
                task_type=task_data["task_type"],
                parameters=task_data["parameters"],
                dependencies=task_data.get("dependencies", []),
                priority=task_data.get("priority", 1)
            )
            task_specs.append(spec)
        
        return TemplateCandidate(
            name=name,
            description=description,
            intent_patterns=intent_patterns,
            parameter_schema=parameter_schema,
            task_sequence=task_specs,
            confidence=pattern.success_rate,
            source_pattern_id=pattern.pattern_id,
            sample_count=pattern.total_count
        )
    
    def _build_parameter_schema(self, pattern: ExecutionPattern) -> Dict[str, Any]:
        """Build JSON schema for template parameters"""
        properties = {}
        required = []
        
        # Extract parameters from task sequence
        for task_data in pattern.task_sequence:
            for key, value in task_data.get("parameters", {}).items():
                if key not in properties:
                    # Infer type from parameter pattern
                    if isinstance(value, str):
                        if value.startswith("${") and value.endswith("}"):
                            param_name = value[2:-1]
                            properties[param_name] = {"type": "string"}
                            if param_name in ["location", "location_a", "location_b"]:
                                required.append(param_name)
                    elif isinstance(value, dict):
                        for k, v in value.items():
                            if isinstance(v, str) and v.startswith("${"):
                                param_name = v[2:-1]
                                properties[param_name] = {"type": "string"}
        
        return {
            "type": "object",
            "properties": properties,
            "required": list(set(required))
        }
    
    def _candidate_to_template(self, candidate: TemplateCandidate) -> TaskTemplate:
        """Convert a candidate to a full template"""
        template_id = f"auto_{candidate.name}_{int(time.time())}"
        
        return TaskTemplate(
            id=template_id,
            name=candidate.name,
            description=candidate.description,
            intent_patterns=candidate.intent_patterns,
            parameter_schema=candidate.parameter_schema,
            task_sequence=candidate.task_sequence,
            success_rate=candidate.confidence,
            avg_duration_ms=0,
            execution_count=candidate.sample_count,
            tags=["auto-generated"],
            version=1
        )
    
    def analyze_from_database(self, db_path: str) -> int:
        """
        Analyze execution history from database.
        
        Returns:
            Number of patterns identified
        """
        if not os.path.exists(db_path):
            return 0
        
        patterns_found = 0
        
        with sqlite3.connect(db_path) as conn:
            # Get completed sessions
            cursor = conn.execute("""
                SELECT session_id, query, intent, success, total_duration_ms
                FROM execution_sessions
                WHERE completed_at IS NOT NULL
                ORDER BY started_at DESC
            """)
            
            sessions = cursor.fetchall()
            
            for session in sessions:
                session_id, query, intent, success, duration = session
                
                # Get tasks for this session
                task_cursor = conn.execute("""
                    SELECT task_id, action, entity, task_type, status, 
                           duration_ms, parameters, error
                    FROM task_executions
                    WHERE session_id = ?
                    ORDER BY started_at
                """, (session_id,))
                
                tasks = []
                for task_row in task_cursor.fetchall():
                    task = TaskNode(
                        id=task_row[0],
                        action=task_row[1],
                        entity=task_row[2],
                        task_type=task_row[3],
                        parameters=json.loads(task_row[6]) if task_row[6] else {}
                    )
                    tasks.append(task)
                
                if tasks:
                    pattern_id = self.analyze_execution(
                        tasks=tasks,
                        intent=intent or "unknown",
                        success=bool(success),
                        duration_ms=duration or 0
                    )
                    if pattern_id:
                        patterns_found += 1
        
        return patterns_found
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about identified patterns"""
        if not self._patterns:
            return {
                "total_patterns": 0,
                "patterns_meeting_criteria": 0,
                "templates_generated": self._templates_generated
            }
        
        meeting_criteria = sum(
            1 for p in self._patterns.values()
            if p.total_count >= self.min_samples and p.success_rate >= self.min_success_rate
        )
        
        return {
            "total_patterns": len(self._patterns),
            "patterns_meeting_criteria": meeting_criteria,
            "templates_generated": self._templates_generated,
            "patterns_analyzed": self._patterns_analyzed,
            "top_patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "intent": p.intent,
                    "success_rate": p.success_rate,
                    "sample_count": p.total_count
                }
                for p in sorted(
                    self._patterns.values(),
                    key=lambda x: x.success_rate * x.total_count,
                    reverse=True
                )[:10]
            ]
        }
    
    def suggest_template_improvements(
        self,
        template_id: str
    ) -> List[Dict[str, Any]]:
        """
        Suggest improvements for an existing template based on patterns.
        
        Returns:
            List of improvement suggestions
        """
        template = self.template_library.get_template(template_id)
        if not template:
            return []
        
        suggestions = []
        
        # Find matching patterns
        for pattern in self._patterns.values():
            if pattern.intent != template_id.split("_")[0]:
                continue
            
            # Check if pattern has better success rate
            if pattern.success_rate > template.success_rate + 0.1:
                suggestions.append({
                    "type": "higher_success_pattern",
                    "pattern_id": pattern.pattern_id,
                    "current_rate": template.success_rate,
                    "pattern_rate": pattern.success_rate,
                    "message": f"Pattern {pattern.pattern_id} has {pattern.success_rate:.1%} success rate vs template's {template.success_rate:.1%}"
                })
            
            # Check for missing tasks
            template_actions = {t.action for t in template.task_sequence}
            pattern_actions = {t["action"] for t in pattern.task_sequence}
            
            missing = pattern_actions - template_actions
            if missing:
                suggestions.append({
                    "type": "missing_actions",
                    "pattern_id": pattern.pattern_id,
                    "missing_actions": list(missing),
                    "message": f"Pattern includes actions not in template: {missing}"
                })
        
        return suggestions


# Singleton instance
_generator_instance: Optional[TemplateGenerator] = None

def get_template_generator(
    template_library: Optional[TemplateLibrary] = None
) -> TemplateGenerator:
    """Get or create singleton TemplateGenerator instance"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = TemplateGenerator(template_library=template_library)
    return _generator_instance
