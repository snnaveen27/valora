"""
Multi-Agent Real Estate Intelligence System - Core Agents
Valora v1.0 - Production-Ready Multi-Agent Orchestration
"""

import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of specialized agents in the system"""
    PLANNER = "planner"
    FORECASTER = "forecaster"
    MAP_AGENT = "map_agent"
    RECOMMENDER = "recommender"
    CRITIC = "critic"


class TaskStatus(Enum):
    """Status of individual tasks"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATED = "validated"


@dataclass
class Task:
    """Individual task in the plan"""
    id: str
    agent: AgentType
    action: str
    input_schema: Dict[str, Any]
    expected_output_schema: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    output: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class Plan:
    """Execution plan for multi-agent coordination"""
    id: str
    user_intent: str
    tasks: List[Task]
    created_at: datetime
    status: str = "planning"
    final_result: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    provenance: List[Dict[str, Any]] = None
    human_actions: List[str] = None
    
    def __post_init__(self):
        if self.provenance is None:
            self.provenance = []
        if self.human_actions is None:
            self.human_actions = []


class PlannerAgent:
    """
    Planner Agent - Understands intent and orchestrates task execution
    """
    
    def __init__(self):
        self.task_templates = {
            "find_zones": ["map_analysis", "forecast_prices", "rank_recommendations"],
            "analyze_property": ["get_property_details", "forecast_single", "risk_assessment"],
            "compare_areas": ["multi_area_mapping", "comparative_forecast", "recommendation_matrix"],
            "market_trends": ["historical_analysis", "trend_forecast", "opportunity_detection"]
        }
    
    async def create_plan(self, user_intent: str, context: Dict[str, Any]) -> Plan:
        """Create execution plan from user intent"""
        plan_id = str(uuid.uuid4())
        
        # Parse intent to determine task sequence
        tasks = self._decompose_intent(user_intent, context)
        
        plan = Plan(
            id=plan_id,
            user_intent=user_intent,
            tasks=tasks,
            created_at=datetime.now()
        )
        
        logger.info(f"Created plan {plan_id} with {len(tasks)} tasks")
        return plan
    
    def _decompose_intent(self, intent: str, context: Dict[str, Any]) -> List[Task]:
        """Decompose user intent into executable tasks"""
        tasks = []
        intent_lower = intent.lower()
        
        # Determine task sequence based on intent
        # Build the default search pipeline for general property queries too
        if (
            "find" in intent_lower
            or "show" in intent_lower
            or "search" in intent_lower
            or "recommend" in intent_lower
            or "suggest" in intent_lower
            or ("zone" in intent_lower or "area" in intent_lower)
            or any(k in intent_lower for k in [
                "property", "properties", "apartment", "flat", "bhk", "house", "villa", "plot"
            ])
        ):
            # Task 1: Map Analysis
            tasks.append(Task(
                id=f"task_{uuid.uuid4().hex[:8]}",
                agent=AgentType.MAP_AGENT,
                action="analyze_zones",
                input_schema={
                    "city": self._extract_city(intent),
                    "budget": self._extract_budget(intent),
                    "property_type": self._extract_property_type(intent),
                    "amenities": self._extract_amenities(intent)
                },
                expected_output_schema={
                    "geo_features": dict,
                    "poi_summary": list,
                    "infra_matches": list,
                    "heatmap_url": str,
                    "spatial_features": dict
                }
            ))
            
            # Task 2: Forecast Prices
            tasks.append(Task(
                id=f"task_{uuid.uuid4().hex[:8]}",
                agent=AgentType.FORECASTER,
                action="forecast_zones",
                input_schema={
                    "zones": "from_previous",
                    "forecast_months": [3, 12, 36],
                    "include_rental": True
                },
                expected_output_schema={
                    "price_forecast": dict,
                    "rental_yield_forecast": dict,
                    "risk_score": float,
                    "model": dict,
                    "confidence": float
                }
            ))
            
            # Task 3: Generate Recommendations
            tasks.append(Task(
                id=f"task_{uuid.uuid4().hex[:8]}",
                agent=AgentType.RECOMMENDER,
                action="rank_zones",
                input_schema={
                    "map_data": "from_task_1",
                    "forecast_data": "from_task_2",
                    "user_preferences": context.get("preferences", {})
                },
                expected_output_schema={
                    "recommendations": list,
                    "reasoning": dict
                }
            ))
            
            # Task 4: Validate Results
            tasks.append(Task(
                id=f"task_{uuid.uuid4().hex[:8]}",
                agent=AgentType.CRITIC,
                action="validate_results",
                input_schema={
                    "all_outputs": "from_previous_tasks"
                },
                expected_output_schema={
                    "status": str,
                    "errors": list,
                    "warnings": list
                }
            ))
        
        return tasks
    
    def _extract_city(self, intent: str) -> str:
        """Extract city from intent"""
        cities = ["bangalore", "bengaluru", "mumbai", "delhi", "pune", "hyderabad", "chennai"]
        intent_lower = intent.lower()
        for city in cities:
            if city in intent_lower:
                # Canonicalize synonyms
                if city in ("bangalore", "bengaluru"):
                    return "Bangalore"
                return city.capitalize()
        return "Bangalore"  # Default
    
    def _extract_budget(self, intent: str) -> Dict[str, float]:
        """Extract budget from intent"""
        import re
        # Look for patterns like "1 Cr", "50 L", "1.5 Cr"
        pattern = r'(\d+(?:\.\d+)?)\s*(cr|crore|l|lakh|lac)'
        matches = re.findall(pattern, intent.lower())
        
        if matches:
            value, unit = matches[0]
            value = float(value)
            if 'cr' in unit:
                value *= 10000000  # Convert crores to rupees
            else:
                value *= 100000  # Convert lakhs to rupees
            
            return {"min": 0, "max": value}
        
        return {"min": 5000000, "max": 15000000}  # Default 50L - 1.5Cr
    
    def _extract_property_type(self, intent: str) -> str:
        """Extract property type from intent"""
        types = {
            "1 bhk": "1BHK",
            "2 bhk": "2BHK", 
            "3 bhk": "3BHK",
            "4 bhk": "4BHK",
            "villa": "Villa",
            "apartment": "Apartment",
            "flat": "Apartment",
            "plot": "Plot"
        }
        
        intent_lower = intent.lower()
        for key, value in types.items():
            if key in intent_lower:
                return value
        
        return "3BHK"  # Default based on user's example
    
    def _extract_amenities(self, intent: str) -> List[str]:
        """Extract desired amenities from intent"""
        amenities = []
        intent_lower = intent.lower()
        
        amenity_keywords = {
            "metro": ["metro", "subway", "rail"],
            "school": ["school", "education"],
            "hospital": ["hospital", "medical", "healthcare"],
            "mall": ["mall", "shopping"],
            "park": ["park", "garden", "green"],
            "gym": ["gym", "fitness"],
            "pool": ["pool", "swimming"]
        }
        
        for amenity, keywords in amenity_keywords.items():
            if any(keyword in intent_lower for keyword in keywords):
                amenities.append(amenity)
        
        # Default amenities if none specified
        if not amenities:
            amenities = ["metro", "school", "hospital"]
        
        return amenities


class CriticAgent:
    """
    Critic Agent - Validates outputs and ensures quality
    """
    
    def __init__(self):
        self.validation_rules = {
            "price_range": (1000000, 50000000),  # 10L to 5Cr
            "rental_yield_range": (2.0, 8.0),  # 2% to 8%
            "risk_score_range": (0.0, 1.0),
            "confidence_range": (0.0, 1.0)
        }
    
    async def validate_results(self, outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate all agent outputs"""
        errors = []
        warnings = []
        
        for output in outputs:
            # Schema validation
            schema_errors = self._validate_schema(output)
            errors.extend(schema_errors)
            
            # Numeric validation
            numeric_warnings = self._validate_numerics(output)
            warnings.extend(numeric_warnings)
        
        status = "pass" if not errors else "fail"
        
        return {
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "confidence": 0.9 if not errors else 0.4,
            "validation_timestamp": datetime.now().isoformat()
        }
    
    def _validate_schema(self, output: Dict[str, Any]) -> List[str]:
        """Validate output schema"""
        errors = []
        # Add schema validation logic here
        return errors
    
    def _validate_numerics(self, output: Dict[str, Any]) -> List[str]:
        """Validate numeric values"""
        warnings = []
        
        # Check price values
        if "predicted_price" in output:
            price = output["predicted_price"]
            min_price, max_price = self.validation_rules["price_range"]
            if not (min_price <= price <= max_price):
                warnings.append(f"Price {price} outside expected range")
        
        # Check rental yield
        if "rental_yield" in output:
            yield_val = output["rental_yield"]
            min_yield, max_yield = self.validation_rules["rental_yield_range"]
            if not (min_yield <= yield_val <= max_yield):
                warnings.append(f"Rental yield {yield_val}% outside expected range")
        
        return warnings
