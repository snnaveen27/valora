"""
Dynamic Task Planning and Real-time Progress Tracking
Generates query-specific task lists and tracks progress dynamically.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    """Represents a single task in the execution plan"""
    id: str
    step: str
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "step": self.step,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
        }


class DynamicTaskPlanner:
    """
    Generates query-specific task plans based on intent and query analysis.
    Tracks task progress in real-time as agents execute.
    """
    
    def __init__(self):
        self.tasks: List[Task] = []
        self.current_task_id: Optional[str] = None
    
    def generate_plan(self, query: str, intent: str, context: Dict[str, Any]) -> List[Task]:
        """
        Generate a dynamic, query-specific task plan.
        Returns tasks that will be executed in sequence.
        """
        self.tasks = []
        task_counter = 0
        
        # Defensive: ensure context is never None
        if context is None:
            context = {}
        
        def add_task(step: str) -> str:
            nonlocal task_counter
            task_id = f"task_{task_counter}"
            task_counter += 1
            task = Task(id=task_id, step=step)
            self.tasks.append(task)
            return task_id
        
        # Common: Query understanding
        add_task(f"Understanding query: '{query[:50]}...'")
        
        # Intent-specific task generation
        if intent == "navigate":
            location = self._extract_location_from_query(query)
            add_task(f"Geocoding location: {location}")
            add_task(f"Preparing map navigation to {location}")
            add_task("Loading nearby points of interest")
        
        elif intent == "analyze_area":
            location = (context or {}).get('selectedPlace', {}).get('name') or self._extract_location_from_query(query)
            add_task(f"Analyzing area: {location}")
            add_task("Gathering spatial data (POIs, transport)")
            add_task("Calculating accessibility and walkability scores")
            add_task("Fetching market data and price trends")
            add_task("Analyzing terrain and flood risk")
            add_task("Generating locality intelligence profile")
            add_task("Computing risk assessment")
            add_task("Synthesizing comprehensive analysis")
        
        elif intent == "property_search":
            location = self._extract_location_from_query(query)
            filters = self._extract_filters_from_query(query)
            add_task(f"Searching properties in {location}")
            if filters.get('budget'):
                add_task(f"Filtering by budget: {filters['budget']}")
            if filters.get('bedrooms'):
                add_task(f"Filtering by bedrooms: {filters['bedrooms']}")
            add_task("Retrieving property listings from database")
            add_task("Calculating distances and amenities")
            add_task("Ranking properties by relevance")
            add_task("Preparing property map markers")
        
        elif intent == "comparison":
            locations = self._extract_comparison_locations(query)
            for loc in locations:
                add_task(f"Analyzing {loc}")
            add_task("Computing comparative metrics")
            add_task("Generating side-by-side comparison")
        
        elif intent == "simulate":
            scenario = self._extract_scenario_from_query(query)
            add_task(f"Understanding scenario: {scenario}")
            add_task("Gathering baseline data for simulation")
            add_task("Running causal reasoning engine")
            add_task("Simulating infrastructure impact")
            add_task("Calculating price appreciation changes")
            add_task("Generating simulation storyboard")
            add_task("Preparing 3D visualization narrative")
        
        elif intent == "analyze_building":
            add_task("Analyzing selected building structure")
            add_task("Computing 3D spatial context")
            add_task("Analyzing view quality and sky view factor")
            add_task("Evaluating shadow impact")
            add_task("Finding optimal floor recommendation")
            add_task("Estimating building valuation")
        
        elif intent == "valuation":
            add_task("Gathering property comparables")
            add_task("Analyzing market trends")
            add_task("Running valuation model")
            add_task("Computing price per sqft estimates")
        
        elif intent == "terrain":
            add_task("Fetching elevation data")
            add_task("Analyzing slope and topography")
            add_task("Assessing flood risk")
            add_task("Evaluating construction suitability")
        
        else:  # general
            add_task("Processing natural language query")
            add_task("Gathering relevant context")
            add_task("Generating AI response")
        
        # Common: Final synthesis
        add_task("Synthesizing AI narrative response")
        
        return self.tasks
    
    def start_task(self, task_id: str):
        """Mark a task as in progress"""
        for task in self.tasks:
            if task.id == task_id:
                task.status = TaskStatus.IN_PROGRESS
                task.start_time = datetime.now()
                self.current_task_id = task_id
                break
    
    def complete_task(self, task_id: str, result: Optional[str] = None):
        """Mark a task as completed with optional result"""
        for task in self.tasks:
            if task.id == task_id:
                task.status = TaskStatus.COMPLETED
                task.end_time = datetime.now()
                task.result = result
                break
    
    def fail_task(self, task_id: str, error: str):
        """Mark a task as failed with error message"""
        for task in self.tasks:
            if task.id == task_id:
                task.status = TaskStatus.FAILED
                task.end_time = datetime.now()
                task.error = error
                break
    
    def skip_task(self, task_id: str, reason: str):
        """Mark a task as skipped with reason"""
        for task in self.tasks:
            if task.id == task_id:
                task.status = TaskStatus.SKIPPED
                task.end_time = datetime.now()
                task.result = reason
                break
    
    def get_tasks_snapshot(self) -> List[Dict[str, Any]]:
        """Get current state of all tasks for frontend"""
        return [task.to_dict() for task in self.tasks]
    
    def get_progress_percentage(self) -> int:
        """Calculate overall progress percentage"""
        if not self.tasks:
            return 0
        completed = sum(1 for t in self.tasks if t.status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED])
        return int((completed / len(self.tasks)) * 100)
    
    # Helper methods for query parsing
    def _extract_location_from_query(self, query: str) -> str:
        """Extract location name from query"""
        import re
        query_lower = query.lower()
        
        # Patterns to extract location
        patterns = [
            r'(?:in|near|at|around)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:show me|go to|find|analyze)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(1)
        
        # Fallback: look for capitalized words
        words = query.split()
        for word in words:
            if word[0].isupper() and len(word) > 3:
                return word
        
        return "specified area"
    
    def _extract_filters_from_query(self, query: str) -> Dict[str, Any]:
        """Extract search filters from query"""
        import re
        filters = {}
        
        # Budget extraction
        budget_match = re.search(r'under\s+(\d+)\s*(lakh|lac|cr|crore)', query.lower())
        if budget_match:
            amount = int(budget_match.group(1))
            unit = budget_match.group(2)
            if 'cr' in unit:
                amount *= 10000000
            else:
                amount *= 100000
            filters['budget'] = f"₹{amount/100000:.0f}L"
        
        # Bedrooms extraction
        bhk_match = re.search(r'(\d+)\s*bhk', query.lower())
        if bhk_match:
            filters['bedrooms'] = f"{bhk_match.group(1)}BHK"
        
        return filters
    
    def _extract_comparison_locations(self, query: str) -> List[str]:
        """Extract locations being compared"""
        import re
        
        # Look for "X vs Y" or "X and Y"
        vs_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:vs|versus|and)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', query)
        if vs_match:
            return [vs_match.group(1), vs_match.group(2)]
        
        # Fallback: find all capitalized sequences
        locations = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', query)
        return locations[:2] if len(locations) >= 2 else ["Location 1", "Location 2"]
    
    def _extract_scenario_from_query(self, query: str) -> str:
        """Extract simulation scenario description"""
        # Remove "what if" or "simulate" prefix
        import re
        scenario = re.sub(r'^(what if|simulate|if)\s+', '', query.lower(), flags=re.IGNORECASE)
        return scenario[:80] + "..." if len(scenario) > 80 else scenario


# Global instance for task tracking
_task_planner_instance: Optional[DynamicTaskPlanner] = None


def get_task_planner() -> DynamicTaskPlanner:
    """Get or create task planner instance"""
    global _task_planner_instance
    if _task_planner_instance is None:
        _task_planner_instance = DynamicTaskPlanner()
    return _task_planner_instance


def reset_task_planner():
    """Reset task planner for new query"""
    global _task_planner_instance
    _task_planner_instance = DynamicTaskPlanner()
    return _task_planner_instance
