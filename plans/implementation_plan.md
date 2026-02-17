 # Valora AI - Detailed Implementation Plan

**Version:** 1.1  
**Date:** February 16, 2026  
**Status:** Ready for Implementation

---

## Overview

This document provides detailed implementation specifications for 4 HIGH priority enhancements:

1. **Tiered Planning System** - 4-tier query planning (SAME for Free & Pro users)
2. **Sequential Model Management** - 6GB VRAM optimization
3. **UI Tab System** - Free vs Pro tier rendering (different tabs, same planning)
4. **Payment Integration** - Stripe subscriptions

### Key Clarification

**Planning System:** 4 tiers (Template → Few-shot → Specialist → Self-learning) is **SAME for all users**. This optimization benefits everyone.

**User Tiers (Free vs Pro):** Only affects:
- Query limits (credits)
- UI tabs shown (limited vs full content)
- NOT the planning logic

---

## Enhancement 1: Tiered Planning System

### 1.1 Architecture Overview

```
User Query
    ↓
┌─────────────────────────────────────────┐
│ TIER 1: Rule Templates                  │
│ • Pattern matching on intent            │
│ • Pre-defined task sequences            │
│ • Coverage: 60% of queries              │
│ • Speed: <5ms                           │
│ • No LLM needed                         │
└─────────────────────────────────────────┘
    ↓ (if no match)
┌─────────────────────────────────────────┐
│ TIER 2: Few-Shot Prompts                │
│ • Qwen3 with example prompts            │
│ • Coverage: 25% of queries              │
│ • Speed: ~50ms                          │
└─────────────────────────────────────────┘
    ↓ (if complex)
┌─────────────────────────────────────────┐
│ TIER 3: Specialist LoRA                 │
│ • Phi-4 with domain adapters            │
│ • Coverage: 10% of queries              │
│ • Speed: ~100ms                         │
└─────────────────────────────────────────┘
    ↓ (continuous)
┌─────────────────────────────────────────┐
│ TIER 4: Self-Learning                   │
│ • Learn from production edits           │
│ • Auto-promote to Tier 1                │
└─────────────────────────────────────────┘
```

### 1.2 File Structure

```
backend/ai/
├── tiered_planner.py          # NEW: Main orchestrator
├── tier1_templates.py         # NEW: Rule templates
├── tier2_fewshot.py           # NEW: Few-shot prompts
├── tier3_specialist.py        # NEW: LoRA specialist
└── self_learning.py           # MODIFY: Tier 4 integration
```

### 1.3 Implementation Details

#### 1.3.1 File: `backend/ai/tiered_planner.py`

```python
"""
Tiered Planning System - 4-Tier Query Planning
Automatically selects the optimal planning strategy based on query complexity.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import time
import logging

logger = logging.getLogger("valora.tiered_planner")


class PlanningTier(Enum):
    TIER_1_TEMPLATE = 1   # Rule-based, no LLM
    TIER_2_FEWSHOT = 2    # Qwen3 few-shot
    TIER_3_SPECIALIST = 3 # Phi-4 LoRA
    TIER_4_LEARNING = 4   # Self-learning


@dataclass
class TaskNode:
    """A single task in the execution graph."""
    id: str
    type: str
    model_hint: Optional[str] = None
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskGraph:
    """A graph of tasks to execute."""
    tasks: List[TaskNode]
    tier: PlanningTier
    intent: str
    confidence: float = 1.0
    
    def sorted_by_priority(self) -> List[TaskNode]:
        return sorted(self.tasks, key=lambda t: t.priority)


class TieredPlanner:
    """
    Main orchestrator for tiered planning.
    
    Tries tiers in order: 1 → 2 → 3
    Tier 4 runs as background learning.
    """
    
    # Intents that require specialist (Tier 3)
    SPECIALIST_INTENTS = {
        'valuation', 'roi_analysis', 'risk_assessment', 
        'legal', 'compliance', 'investment_deep'
    }
    
    def __init__(self):
        from ai.tier1_templates import Tier1Templates
        from ai.tier2_fewshot import Tier2FewShot
        from ai.tier3_specialist import Tier3Specialist
        
        self.tier1 = Tier1Templates()
        self.tier2 = Tier2FewShot()
        self.tier3 = Tier3Specialist()
        
        # Stats tracking
        self.stats = {
            'tier1_hits': 0,
            'tier2_hits': 0,
            'tier3_hits': 0,
            'total_queries': 0
        }
    
    def create_graph(
        self, 
        query: str, 
        intent: str, 
        agent_facts: Dict[str, Any],
        user_tier: str = 'free'
    ) -> TaskGraph:
        """
        Create a task graph using tiered planning.
        
        Args:
            query: User's natural language query
            intent: Classified intent (property_search, valuation, etc.)
            agent_facts: Grounded facts from GIS agents
            user_tier: User's subscription tier (free/pro)
        
        Returns:
            TaskGraph with tasks to execute
        """
        self.stats['total_queries'] += 1
        start_time = time.time()
        
        # Try Tier 1 first (fastest)
        graph = self._try_tier1(intent, agent_facts)
        if graph:
            self.stats['tier1_hits'] += 1
            logger.info(f"Tier 1 match for intent: {intent}")
            return graph
        
        # Check if specialist intent (Tier 3)
        if self._is_specialist_intent(intent):
            graph = self._try_tier3(query, intent, agent_facts)
            if graph:
                self.stats['tier3_hits'] += 1
                logger.info(f"Tier 3 specialist for intent: {intent}")
                return graph
        
        # Fall back to Tier 2 (few-shot)
        graph = self._try_tier2(query, intent, agent_facts)
        if graph:
            self.stats['tier2_hits'] += 1
            logger.info(f"Tier 2 few-shot for intent: {intent}")
            return graph
        
        # Last resort: Tier 3 with generic specialist
        graph = self._try_tier3(query, intent, agent_facts, fallback=True)
        self.stats['tier3_hits'] += 1
        return graph
    
    def _try_tier1(self, intent: str, agent_facts: Dict) -> Optional[TaskGraph]:
        """Try to match a Tier 1 template."""
        template = self.tier1.get_template(intent, agent_facts)
        if template:
            tasks = [
                TaskNode(
                    id=f"t_{i+1}",
                    type=task['type'],
                    model_hint=task.get('model'),
                    priority=task.get('priority', i+1),
                    params=task.get('params', {}),
                    provenance={'tier': 1, 'template': intent}
                )
                for i, task in enumerate(template['tasks'])
            ]
            return TaskGraph(tasks=tasks, tier=PlanningTier.TIER_1_TEMPLATE, intent=intent)
        return None
    
    def _try_tier2(self, query: str, intent: str, agent_facts: Dict) -> Optional[TaskGraph]:
        """Use few-shot prompting with Qwen3."""
        return self.tier2.create_graph(query, intent, agent_facts)
    
    def _try_tier3(self, query: str, intent: str, agent_facts: Dict, fallback: bool = False) -> Optional[TaskGraph]:
        """Use Phi-4 specialist with LoRA."""
        domain = self._get_specialist_domain(intent)
        return self.tier3.create_graph(query, intent, agent_facts, domain)
    
    def _is_specialist_intent(self, intent: str) -> bool:
        return intent in self.SPECIALIST_INTENTS
    
    def _get_specialist_domain(self, intent: str) -> str:
        mapping = {
            'valuation': 'valuation',
            'roi_analysis': 'roi',
            'risk_assessment': 'risk',
            'legal': 'legal',
            'compliance': 'compliance',
            'investment_deep': 'roi'
        }
        return mapping.get(intent, 'general')
    
    def get_stats(self) -> Dict[str, Any]:
        """Get planning statistics."""
        total = self.stats['total_queries']
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            'tier1_coverage': self.stats['tier1_hits'] / total,
            'tier2_coverage': self.stats['tier2_hits'] / total,
            'tier3_coverage': self.stats['tier3_hits'] / total
        }


# Singleton instance
_planner_instance = None

def get_tiered_planner() -> TieredPlanner:
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = TieredPlanner()
    return _planner_instance
```

#### 1.3.2 File: `backend/ai/tier1_templates.py`

```python
"""
Tier 1 Templates - Rule-based task sequences.
No LLM needed, pure pattern matching.
"""

from typing import Dict, List, Any, Optional
import re


# Pre-defined task templates for common intents
TIER1_TEMPLATES = {
    'property_search': {
        'tasks': [
            {'type': 'geocode_location', 'model': None, 'priority': 1},
            {'type': 'fetch_listings', 'model': None, 'priority': 2},
            {'type': 'filter_by_budget', 'model': None, 'priority': 3},
            {'type': 'rank_by_score', 'model': 'qwen3', 'priority': 4}
        ],
        'required_facts': ['location', 'budget']
    },
    'analyze_area': {
        'tasks': [
            {'type': 'geocode_location', 'model': None, 'priority': 1},
            {'type': 'fetch_area_stats', 'model': None, 'priority': 2},
            {'type': 'fetch_pois', 'model': None, 'priority': 3},
            {'type': 'compute_livability', 'model': 'qwen3', 'priority': 4}
        ],
        'required_facts': ['location']
    },
    'valuation': {
        'tasks': [
            {'type': 'fetch_property_details', 'model': None, 'priority': 1},
            {'type': 'fetch_comps', 'model': None, 'priority': 2},
            {'type': 'compute_valuation', 'model': 'phi-4', 'priority': 3},
            {'type': 'verify_calculation', 'model': 'phi-4', 'priority': 4}
        ],
        'required_facts': ['property_id', 'location']
    },
    'investment': {
        'tasks': [
            {'type': 'fetch_market_data', 'model': None, 'priority': 1},
            {'type': 'compute_roi', 'model': 'phi-4', 'priority': 2},
            {'type': 'risk_assessment', 'model': 'phi-4', 'priority': 3}
        ],
        'required_facts': ['location']
    },
    'compare_areas': {
        'tasks': [
            {'type': 'geocode_locations', 'model': None, 'priority': 1, 'params': {'multi': True}},
            {'type': 'fetch_area_stats', 'model': None, 'priority': 2, 'params': {'multi': True}},
            {'type': 'compute_comparison', 'model': 'qwen3', 'priority': 3}
        ],
        'required_facts': ['locations']
    }
}


class Tier1Templates:
    """
    Tier 1 template matching.
    
    Matches intents to pre-defined task sequences.
    Returns None if no template matches (falls through to Tier 2).
    """
    
    def __init__(self):
        self.templates = TIER1_TEMPLATES
        self._match_cache = {}
    
    def get_template(self, intent: str, agent_facts: Dict[str, Any]) -> Optional[Dict]:
        """
        Get a template for the given intent.
        
        Args:
            intent: The classified intent
            agent_facts: Available facts from GIS agents
        
        Returns:
            Template dict with tasks, or None if no match
        """
        template = self.templates.get(intent)
        if not template:
            return None
        
        # Check if required facts are available
        required = template.get('required_facts', [])
        for fact in required:
            if fact not in agent_facts or not agent_facts[fact]:
                return None
        
        return template
    
    def add_template(self, intent: str, tasks: List[Dict], required_facts: List[str] = None):
        """Add a new template (used by Tier 4 self-learning)."""
        self.templates[intent] = {
            'tasks': tasks,
            'required_facts': required_facts or []
        }
    
    def get_all_intents(self) -> List[str]:
        """Get all supported intents."""
        return list(self.templates.keys())
```

#### 1.3.3 File: `backend/ai/tier2_fewshot.py`

```python
"""
Tier 2 Few-Shot Prompts - Qwen3 with examples.
"""

from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger("valora.tier2_fewshot")


# Few-shot examples for different intents
FEW_SHOT_EXAMPLES = {
    'comparison': """
Example 1:
Query: "Compare Whitefield vs Koramangala for investment"
Task Graph:
[
  {"type": "fetch_area_stats", "locations": ["whitefield", "koramangala"]},
  {"type": "fetch_market_trends", "parallel": true},
  {"type": "compute_comparison_matrix", "model": "qwen3"},
  {"type": "generate_verdict", "model": "qwen3"}
]

Example 2:
Query: "HSR Layout or Electronic City which is better for families?"
Task Graph:
[
  {"type": "fetch_area_stats", "locations": ["hsr_layout", "electronic_city"]},
  {"type": "fetch_schools_hospitals", "parallel": true},
  {"type": "compute_family_score", "model": "qwen3"},
  {"type": "generate_comparison", "model": "qwen3"}
]
""",

    'simulate': """
Example:
Query: "What if metro comes to Sarjapur in 2027?"
Task Graph:
[
  {"type": "fetch_infra_plans"},
  {"type": "fetch_historical_metro_impact"},
  {"type": "simulate_price_change", "model": "phi-4"},
  {"type": "estimate_timeline"}
]
""",

    'general': """
Example:
Query: "Tell me about Indiranagar"
Task Graph:
[
  {"type": "geocode_location"},
  {"type": "fetch_area_stats"},
  {"type": "fetch_pois"},
  {"type": "generate_summary", "model": "qwen3"}
]
"""
}


class Tier2FewShot:
    """
    Tier 2 planning using few-shot prompts with Qwen3.
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.examples = FEW_SHOT_EXAMPLES
    
    def create_graph(self, query: str, intent: str, agent_facts: Dict[str, Any]) -> Optional['TaskGraph']:
        """
        Create a task graph using few-shot prompting.
        """
        from ai.tiered_planner import TaskGraph, TaskNode, PlanningTier
        
        # Get relevant examples
        examples = self._get_examples(intent)
        
        # Build prompt
        prompt = self._build_prompt(query, intent, agent_facts, examples)
        
        # Call Qwen3
        try:
            response = self._call_llm(prompt)
            task_data = json.loads(response)
            
            tasks = [
                TaskNode(
                    id=f"t_{i+1}",
                    type=t.get('type', 'unknown'),
                    model_hint=t.get('model'),
                    priority=i+1,
                    provenance={'tier': 2}
                )
                for i, t in enumerate(task_data.get('tasks', []))
            ]
            
            return TaskGraph(
                tasks=tasks, 
                tier=PlanningTier.TIER_2_FEWSHOT, 
                intent=intent,
                confidence=0.85
            )
        except Exception as e:
            logger.error(f"Tier 2 planning failed: {e}")
            return None
    
    def _get_examples(self, intent: str) -> str:
        """Get few-shot examples for the intent."""
        # Try exact match first
        if intent in self.examples:
            return self.examples[intent]
        # Fall back to general
        return self.examples.get('general', '')
    
    def _build_prompt(self, query: str, intent: str, agent_facts: Dict, examples: str) -> str:
        """Build the few-shot prompt."""
        return f"""{examples}

Now create a task graph for:
Query: {query}
Intent: {intent}
Available Facts: {list(agent_facts.keys())}

Output JSON only: {{"tasks": [{{"type": "...", "model": "..."}}]}}"""
    
    def _call_llm(self, prompt: str) -> str:
        """Call Qwen3 LLM."""
        if self.llm_client:
            return self.llm_client.generate(prompt)
        
        # Use Ollama client
        from ai.ollama_client import OllamaClient
        client = OllamaClient(model="qwen3:4b-instruct")
        return client.generate(prompt)
```

#### 1.3.4 File: `backend/ai/tier3_specialist.py`

```python
"""
Tier 3 Specialist - Phi-4 with LoRA adapters.
"""

from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger("valora.tier3_specialist")


# Specialist domains and their LoRA paths
SPECIALIST_DOMAINS = {
    'valuation': {
        'lora_path': '/models/phi4-valuation-lora',
        'description': 'Property valuation and pricing analysis'
    },
    'roi': {
        'lora_path': '/models/phi4-roi-lora',
        'description': 'ROI projections and investment analysis'
    },
    'risk': {
        'lora_path': '/models/phi4-risk-lora',
        'description': 'Risk assessment and mitigation'
    },
    'legal': {
        'lora_path': '/models/phi4-legal-lora',
        'description': 'Legal and compliance analysis'
    }
}


class Tier3Specialist:
    """
    Tier 3 planning using Phi-4 with LoRA adapters.
    Used for complex, domain-specific queries.
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.domains = SPECIALIST_DOMAINS
    
    def create_graph(
        self, 
        query: str, 
        intent: str, 
        agent_facts: Dict[str, Any],
        domain: str = 'general'
    ) -> Optional['TaskGraph']:
        """
        Create a task graph using Phi-4 specialist.
        """
        from ai.tiered_planner import TaskGraph, TaskNode, PlanningTier
        
        # Build specialist prompt
        prompt = self._build_prompt(query, intent, agent_facts, domain)
        
        try:
            # Call Phi-4 (optionally with LoRA)
            response = self._call_llm(prompt, domain)
            task_data = json.loads(response)
            
            tasks = [
                TaskNode(
                    id=f"t_{i+1}",
                    type=t.get('type', 'unknown'),
                    model_hint='phi-4',  # All tasks use Phi-4
                    priority=i+1,
                    provenance={'tier': 3, 'domain': domain}
                )
                for i, t in enumerate(task_data.get('tasks', []))
            ]
            
            return TaskGraph(
                tasks=tasks,
                tier=PlanningTier.TIER_3_SPECIALIST,
                intent=intent,
                confidence=0.92
            )
        except Exception as e:
            logger.error(f"Tier 3 planning failed: {e}")
            return None
    
    def _build_prompt(self, query: str, intent: str, agent_facts: Dict, domain: str) -> str:
        """Build the specialist prompt."""
        domain_info = self.domains.get(domain, {})
        
        return f"""You are a {domain} specialist planner for real estate analysis.

Domain: {domain}
Description: {domain_info.get('description', 'General analysis')}

Query: {query}
Intent: {intent}
Available Facts: {list(agent_facts.keys())}

Create a detailed task graph with:
- All required validation steps
- Phi-4 model hints for critical calculations
- Verification tasks for numeric outputs

Output JSON only: {{"tasks": [{{"type": "...", "model": "phi-4"}}]}}"""
    
    def _call_llm(self, prompt: str, domain: str) -> str:
        """Call Phi-4 with optional LoRA adapter."""
        # For now, use standard Phi-4
        # TODO: Add LoRA adapter loading
        from ai.ollama_client import OllamaClient
        client = OllamaClient(model="phi-4")
        return client.generate(prompt)
```

### 1.4 Integration Points

1. **In [`chat_routes.py`](backend/routes/chat_routes.py):**
   - Replace direct task creation with `TieredPlanner.create_graph()`
   - Add tier statistics to response metadata

2. **In [`self_learning.py`](backend/ai/self_learning.py):**
   - Add `promote_to_tier1()` method
   - Track template success rates

---

## Enhancement 2: Sequential Model Management

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│ Task Batcher                                        │
│ • Groups tasks by required model                    │
│ • Minimizes model switches                          │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Sequential Model Manager                            │
│ • Tracks current loaded model                       │
│ • Unloads/loads models as needed                    │
│ • Emits SSE events during switches                  │
│ • VRAM-aware (6GB limit)                            │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Model Execution                                     │
│ • Execute batch with current model                  │
│ • Switch to next model if needed                    │
└─────────────────────────────────────────────────────┘
```

### 2.2 File Structure

```
backend/ai/
├── sequential_model_manager.py  # NEW: Model lifecycle
└── task_batcher.py              # NEW: Group tasks by model
```

### 2.3 Implementation Details

#### 2.3.1 File: `backend/ai/sequential_model_manager.py`

```python
"""
Sequential Model Manager - Manages model loading for 6GB VRAM.
Only one model loaded at a time, with smart switching.
"""

import subprocess
import time
import logging
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("valora.model_manager")


class ModelStatus(Enum):
    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"


@dataclass
class ModelInfo:
    name: str
    vram_required_gb: float
    purpose: str
    status: ModelStatus = ModelStatus.NOT_LOADED


class SequentialModelManager:
    """
    Manages model loading/unloading for limited VRAM environments.
    
    Features:
    - Only one model loaded at a time
    - Automatic switching with SSE notifications
    - VRAM tracking
    - Keepalive management
    """
    
    MODELS = {
        'qwen3:4b-instruct': ModelInfo(
            name='qwen3:4b-instruct',
            vram_required_gb=3.5,
            purpose='general_execution'
        ),
        'qwen3:8b': ModelInfo(
            name='qwen3:8b',
            vram_required_gb=5.5,
            purpose='general_execution'
        ),
        'phi-4': ModelInfo(
            name='phi-4',
            vram_required_gb=4.8,
            purpose='specialist_planner'
        )
    }
    
    def __init__(
        self, 
        vram_gb: float = 6.0,
        sse_callback: Optional[Callable] = None
    ):
        self.vram_gb = vram_gb
        self.sse_callback = sse_callback
        self.current_model: Optional[str] = None
        self.switch_overhead_s = 4.0
        self._model_status: Dict[str, ModelStatus] = {
            name: ModelStatus.NOT_LOADED 
            for name in self.MODELS
        }
    
    def ensure_model(self, model_name: str) -> bool:
        """
        Ensure the specified model is loaded.
        Switches models if necessary.
        
        Args:
            model_name: Name of the model to load
        
        Returns:
            True if model is ready, False on error
        """
        # Normalize model name
        model_name = self._normalize_model_name(model_name)
        
        # Check if already loaded
        if self.current_model == model_name:
            logger.debug(f"Model {model_name} already loaded")
            return True
        
        # Check if model exists
        if model_name not in self.MODELS:
            logger.warning(f"Unknown model: {model_name}")
            return False
        
        # Emit switching event
        self._emit_sse('model_switching', {
            'from': self.current_model,
            'to': model_name,
            'estimated_delay_s': self.switch_overhead_s
        })
        
        # Unload current model
        if self.current_model:
            self._unload_model(self.current_model)
        
        # Load new model
        success = self._load_model(model_name)
        
        if success:
            self.current_model = model_name
            self._emit_sse('model_loaded', {'model': model_name})
        else:
            self._emit_sse('model_error', {'model': model_name})
        
        return success
    
    def _normalize_model_name(self, name: str) -> str:
        """Normalize model name to canonical form."""
        # Handle common aliases
        aliases = {
            'qwen3': 'qwen3:4b-instruct',
            'qwen': 'qwen3:4b-instruct',
            'phi4': 'phi-4',
        }
        return aliases.get(name.lower(), name)
    
    def _unload_model(self, model_name: str):
        """Unload a model from VRAM."""
        logger.info(f"Unloading model: {model_name}")
        self._model_status[model_name] = ModelStatus.NOT_LOADED
        
        try:
            # Stop the model in Ollama
            result = subprocess.run(
                ['ollama', 'stop', model_name],
                capture_output=True,
                timeout=30
            )
            # Give VRAM time to clear
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error unloading model: {e}")
    
    def _load_model(self, model_name: str) -> bool:
        """Load a model into VRAM."""
        logger.info(f"Loading model: {model_name}")
        self._model_status[model_name] = ModelStatus.LOADING
        
        try:
            # Run the model (it will be kept alive)
            result = subprocess.run(
                ['ollama', 'run', model_name, '--keepalive', '10m'],
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self._model_status[model_name] = ModelStatus.LOADED
                return True
            else:
                self._model_status[model_name] = ModelStatus.ERROR
                logger.error(f"Model load failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self._model_status[model_name] = ModelStatus.ERROR
            logger.error(f"Model load timeout: {model_name}")
            return False
        except Exception as e:
            self._model_status[model_name] = ModelStatus.ERROR
            logger.error(f"Error loading model: {e}")
            return False
    
    def _emit_sse(self, event_type: str, data: Dict[str, Any]):
        """Emit an SSE event."""
        if self.sse_callback:
            self.sse_callback(event_type, data)
        logger.info(f"SSE: {event_type} - {data}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current model status."""
        return {
            'current_model': self.current_model,
            'vram_gb': self.vram_gb,
            'models': {
                name: {
                    'status': status.value,
                    'vram_required': self.MODELS[name].vram_required_gb,
                    'purpose': self.MODELS[name].purpose
                }
                for name, status in self._model_status.items()
            }
        }


# Singleton
_manager_instance = None

def get_model_manager(sse_callback: Callable = None) -> SequentialModelManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SequentialModelManager(sse_callback=sse_callback)
    return _manager_instance
```

#### 2.3.2 File: `backend/ai/task_batcher.py`

```python
"""
Task Batcher - Groups tasks by model to minimize switches.
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger("valora.task_batcher")


@dataclass
class TaskBatch:
    """A batch of tasks for a single model."""
    model: str
    tasks: List[Any] = field(default_factory=list)


class TaskBatcher:
    """
    Groups tasks by their required model.
    Minimizes model switches during execution.
    """
    
    def __init__(self, default_model: str = 'qwen3:4b-instruct'):
        self.default_model = default_model
    
    def batch_by_model(self, task_graph) -> List[TaskBatch]:
        """
        Group tasks by model, respecting dependencies.
        
        Args:
            task_graph: TaskGraph with tasks to batch
        
        Returns:
            List of TaskBatch objects
        """
        batches: List[TaskBatch] = []
        current_batch: Optional[TaskBatch] = None
        
        # Sort tasks by priority
        sorted_tasks = task_graph.sorted_by_priority()
        
        for task in sorted_tasks:
            # Determine required model
            required_model = getattr(task, 'model_hint', None) or self.default_model
            
            # Add to current batch or start new one
            if current_batch and current_batch.model == required_model:
                current_batch.tasks.append(task)
            else:
                if current_batch:
                    batches.append(current_batch)
                current_batch = TaskBatch(model=required_model, tasks=[task])
        
        # Add final batch
        if current_batch and current_batch.tasks:
            batches.append(current_batch)
        
        logger.info(f"Created {len(batches)} batches from {len(sorted_tasks)} tasks")
        for i, batch in enumerate(batches):
            logger.debug(f"  Batch {i+1}: {batch.model} ({len(batch.tasks)} tasks)")
        
        return batches
    
    def estimate_switches(self, batches: List[TaskBatch]) -> int:
        """Estimate number of model switches needed."""
        if not batches:
            return 0
        
        switches = 0
        prev_model = None
        
        for batch in batches:
            if prev_model and batch.model != prev_model:
                switches += 1
            prev_model = batch.model
        
        return switches


# Singleton
_batcher_instance = None

def get_task_batcher() -> TaskBatcher:
    global _batcher_instance
    if _batcher_instance is None:
        _batcher_instance = TaskBatcher()
    return _batcher_instance
```

### 2.4 Integration Points

1. **In [`chat_routes.py`](backend/routes/chat_routes.py):**
   ```python
   from ai.sequential_model_manager import get_model_manager
   from ai.task_batcher import get_task_batcher
   
   # In streaming endpoint:
   model_manager = get_model_manager(sse_callback=emit_sse)
   batcher = get_task_batcher()
   
   batches = batcher.batch_by_model(task_graph)
   for batch in batches:
       model_manager.ensure_model(batch.model)
       for task in batch.tasks:
           # Execute task
           pass
   ```

---

## Enhancement 3: UI Tab System

### 3.1 Architecture Overview

```
Query Response
    ↓
┌─────────────────────────────────────────────────────┐
│ UI Tab Renderer                                     │
│ • Determines tabs based on user tier                │
│ • Filters content (limited/full)                    │
│ • Adds locked tab placeholders                      │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Tab Structure                                       │
 │                                                     │
│ FREE:                                               │
│ ├── Decision Verdict (limited)                      │
│ ├── Market Snapshot (limited)                       │
│ ├── Risk Analysis 🔒                                │
│ ├── ROI Projection 🔒                               │
│ └── Comparables 🔒                                  │
│                                                     │
│ PRO:                                                │
│ ├── Decision Verdict (full)                         │
│ ├── Market Snapshot (full)                          │
│ ├── Risk Analysis (full)                            │
│ ├── ROI Projection (full)                           │
│ └── Comparables (full)                              │
└─────────────────────────────────────────────────────┘
```

### 3.2 File Structure

```
backend/ai/
└── ui_tab_renderer.py          # NEW: Tab generation

src/components/
├── TabPanel.jsx                # NEW: Tab display
└── LockedTab.jsx               # NEW: Upgrade prompt
```

### 3.3 Implementation Details

#### 3.3.1 File: `backend/ai/ui_tab_renderer.py`

```python
"""
UI Tab Renderer - Generates tiered tab structure.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger("valora.ui_tabs")


class TabType(Enum):
    LIMITED = "limited"     # Free tier, limited content
    FULL = "full"           # Pro tier, full content
    LOCKED = "locked"       # Locked, shows upgrade prompt
    PREVIEW = "preview"     # Preview with upgrade prompt


@dataclass
class Tab:
    """A single UI tab."""
    id: str
    title: str
    type: TabType
    content: Dict[str, Any] = field(default_factory=dict)
    icon: str = ""
    order: int = 0


# Tab definitions by tier
TABS_BY_TIER = {
    'free': [
        {'id': 'decision_verdict', 'type': 'limited', 'order': 1},
        {'id': 'market_snapshot', 'type': 'limited', 'order': 2},
        {'id': 'risk_analysis', 'type': 'locked', 'order': 3},
        {'id': 'roi_projection', 'type': 'locked', 'order': 4},
        {'id': 'comparables', 'type': 'locked', 'order': 5},
    ],
    'pro': [
        {'id': 'decision_verdict', 'type': 'full', 'order': 1},
        {'id': 'market_snapshot', 'type': 'full', 'order': 2},
        {'id': 'risk_analysis', 'type': 'full', 'order': 3},
        {'id': 'roi_projection', 'type': 'full', 'order': 4},
        {'id': 'comparables', 'type': 'full', 'order': 5},
    ]
}

# Tab metadata
TAB_METADATA = {
    'decision_verdict': {
        'title': 'Decision Verdict',
        'icon': 'gavel',
        'description': 'BUY / HOLD / AVOID recommendation'
    },
    'market_snapshot': {
        'title': 'Market Snapshot',
        'icon': 'chart-line',
        'description': 'Price trends and market dynamics'
    },
    'risk_analysis': {
        'title': 'Risk Analysis',
        'icon': 'exclamation-triangle',
        'description': 'Flood, legal, and market risks'
    },
    'roi_projection': {
        'title': 'ROI Projection',
        'icon': 'percentage',
        'description': '3-year return scenarios'
    },
    'comparables': {
        'title': 'Comparable Properties',
        'icon': 'building',
        'description': 'Similar listings in the area'
    }
}


class UITabRenderer:
    """
    Renders UI tabs based on user tier.
    """
    
    def __init__(self):
        self.tabs_by_tier = TABS_BY_TIER
        self.tab_metadata = TAB_METADATA
    
    def render(
        self, 
        results: Dict[str, Any], 
        user_tier: str,
        verification: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Render tabs for the given results and user tier.
        
        Args:
            results: Execution results from task graph
            user_tier: User's subscription tier (free/pro)
            verification: Optional fact verification results
        
        Returns:
            List of tab dictionaries
        """
        # Get tab configuration for tier
        tab_configs = self.tabs_by_tier.get(user_tier, self.tabs_by_tier['free'])
        
        rendered_tabs = []
        
        for config in tab_configs:
            tab_id = config['id']
            tab_type = TabType(config['type'])
            
            # Get metadata
            metadata = self.tab_metadata.get(tab_id, {})
            
            # Create tab
            tab = Tab(
                id=tab_id,
                title=metadata.get('title', tab_id.replace('_', ' ').title()),
                type=tab_type,
                icon=metadata.get('icon', ''),
                order=config['order']
            )
            
            # Generate content based on type
            if tab_type == TabType.LOCKED:
                tab.content = self._generate_locked_content(tab_id)
            elif tab_type == TabType.LIMITED:
                tab.content = self._generate_limited_content(tab_id, results)
            else:  # FULL
                tab.content = self._generate_full_content(tab_id, results, verification)
            
            rendered_tabs.append({
                'id': tab.id,
                'title': tab.title,
                'type': tab.type.value,
                'icon': tab.icon,
                'order': tab.order,
                'content': tab.content
            })
        
        # Sort by order
        rendered_tabs.sort(key=lambda t: t['order'])
        
        return rendered_tabs
    
    def _generate_locked_content(self, tab_id: str) -> Dict[str, Any]:
        """Generate content for a locked tab."""
        metadata = self.tab_metadata.get(tab_id, {})
        return {
            'locked': True,
            'title': metadata.get('title', ''),
            'description': metadata.get('description', ''),
            'upgrade_message': 'Upgrade to Pro to unlock this feature',
            'upgrade_cta': 'Upgrade Now'
        }
    
    def _generate_limited_content(self, tab_id: str, results: Dict) -> Dict[str, Any]:
        """Generate limited content for free tier."""
        if tab_id == 'decision_verdict':
            return {
                'verdict': results.get('verdict', 'HOLD'),
                'confidence': results.get('confidence', 0.7),
                'summary': results.get('summary', '')[:200],  # Truncated
                'limited': True,
                'full_available': True
            }
        elif tab_id == 'market_snapshot':
            return {
                'avg_price': results.get('avg_price'),
                'price_trend': results.get('price_trend'),
                'limited': True,
                'full_available': True
            }
        return {'limited': True}
    
    def _generate_full_content(
        self, 
        tab_id: str, 
        results: Dict, 
        verification: Optional[Dict]
    ) -> Dict[str, Any]:
        """Generate full content for pro tier."""
        content = results.get(tab_id, results)
        
        # Add verification badge
        if verification:
            content['verification'] = {
                'verified_ratio': verification.get('verified_ratio', 0),
                'status': verification.get('status', 'UNKNOWN')
            }
        
        return content


# Singleton
_renderer_instance = None

def get_ui_tab_renderer() -> UITabRenderer:
    global _renderer_instance
    if _renderer_instance is None:
        _renderer_instance = UITabRenderer()
    return _renderer_instance
```

#### 3.3.2 File: `src/components/TabPanel.jsx`

```jsx
/**
 * TabPanel - Displays tiered tabs with locked state support
 */

import React, { useState } from 'react';
import LockedTab from './LockedTab';

const TAB_ICONS = {
  'gavel': '⚖️',
  'chart-line': '📈',
  'exclamation-triangle': '⚠️',
  'percentage': '%',
  'building': '🏢'
};

export default function TabPanel({ tabs, onUpgrade, userTier }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!tabs || tabs.length === 0) {
    return <div className="no-results">No analysis available</div>;
  }

  return (
    <div className="tab-panel">
      {/* Tab Headers */}
      <div className="tab-headers">
        {tabs.map((tab, index) => (
          <button
            key={tab.id}
            className={`tab-header ${activeTab === index ? 'active' : ''} ${tab.type === 'locked' ? 'locked' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            <span className="tab-icon">{TAB_ICONS[tab.icon] || '📄'}</span>
            <span className="tab-title">{tab.title}</span>
            {tab.type === 'locked' && <span className="lock-icon">🔒</span>}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {tabs.map((tab, index) => (
          <div
            key={tab.id}
            className={`tab-pane ${activeTab === index ? 'active' : ''}`}
          >
            {tab.type === 'locked' ? (
              <LockedTab
                tab={tab}
                onUpgrade={onUpgrade}
              />
            ) : (
              <TabContent tab={tab} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function TabContent({ tab }) {
  const { content } = tab;

  // Decision Verdict
  if (tab.id === 'decision_verdict') {
    return (
      <div className="verdict-content">
        <div className={`verdict-badge ${content.verdict?.toLowerCase()}`}>
          {content.verdict}
        </div>
        <p className="verdict-summary">{content.summary}</p>
        {content.limited && (
          <p className="limited-notice">
            📊 Full analysis available with Pro
          </p>
        )}
      </div>
    );
  }

  // Market Snapshot
  if (tab.id === 'market_snapshot') {
    return (
      <div className="market-content">
        <div className="market-stat">
          <label>Avg Price</label>
          <span>₹{content.avg_price?.toLocaleString()}/sqft</span>
        </div>
        <div className="market-stat">
          <label>Trend</label>
          <span className={content.price_trend > 0 ? 'up' : 'down'}>
            {content.price_trend > 0 ? '↑' : '↓'} {Math.abs(content.price_trend)}%
          </span>
        </div>
      </div>
    );
  }

  // Default content
  return (
    <div className="generic-content">
      <pre>{JSON.stringify(content, null, 2)}</pre>
    </div>
  );
}
```

#### 3.3.3 File: `src/components/LockedTab.jsx`

```jsx
/**
 * LockedTab - Shows upgrade prompt for locked tabs
 */

import React from 'react';

export default function LockedTab({ tab, onUpgrade }) {
  const { content } = tab;

  return (
    <div className="locked-tab">
      <div className="locked-icon">🔒</div>
      <h3>{content.title}</h3>
      <p className="locked-description">{content.description}</p>
      
      <div className="locked-benefits">
        <h4>Unlock with Pro:</h4>
        <ul>
          <li>✓ Full {content.title.toLowerCase()}</li>
          <li>✓ Detailed analysis & insights</li>
          <li>✓ Data-backed recommendations</li>
          <li>✓ 500 queries per month</li>
        </ul>
      </div>

      <button className="upgrade-button" onClick={onUpgrade}>
        Upgrade to Pro — $19/month
      </button>
      
      <p className="upgrade-note">
        Cancel anytime. No commitment.
      </p>
    </div>
  );
}
```

### 3.4 Integration Points

1. **In [`chat_routes.py`](backend/routes/chat_routes.py):**
   ```python
   from ai.ui_tab_renderer import get_ui_tab_renderer
   
   # After execution:
   renderer = get_ui_tab_renderer()
   tabs = renderer.render(results, user_tier, verification)
   
   # In SSE response:
   yield f"data: {json.dumps({'type': 'tabs', 'tabs': tabs})}\n\n"
   ```

2. **In [`EnhancedChatPanel.jsx`](src/components/chat/EnhancedChatPanel.jsx):**
   - Replace single response display with `TabPanel` component
   - Handle `tabs` SSE event type

---

## Enhancement 4: Payment Integration

### 4.1 Architecture Overview

```
User clicks "Upgrade"
    ↓
┌─────────────────────────────────────────────────────┐
│ Frontend: PaymentCheckout.jsx                       │
│ • Calls /api/payments/create-checkout-session       │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Backend: payment_routes.py                          │
│ • Creates Stripe Checkout Session                   │
│ • Returns checkout URL                              │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Stripe Checkout                                     │
│ • User enters payment details                       │
│ • Processes payment                                 │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Webhook: /api/payments/webhook                      │
│ • Receives checkout.session.completed               │
│ • Upgrades user tier in database                    │
└─────────────────────────────────────────────────────┘
```

### 4.2 File Structure

```
backend/
├── routes/
│   └── payment_routes.py        # NEW: Stripe endpoints
└── services/
    └── stripe_service.py        # NEW: Stripe integration
```

### 4.3 Implementation Details

#### 4.3.1 File: `backend/routes/payment_routes.py`

```python
"""
Payment Routes - Stripe integration endpoints.
"""

import os
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger("valora.payments")

router = APIRouter(prefix="/api/payments", tags=["payments"])

# Stripe configuration
STRIPE_API_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# Price IDs (create in Stripe Dashboard)
PRO_MONTHLY_PRICE_ID = os.environ.get("STRIPE_PRO_PRICE_ID", "price_pro_monthly")


class CreateCheckoutRequest(BaseModel):
    user_id: str
    tier: str = "pro"


@router.post("/create-checkout-session")
async def create_checkout_session(request: CreateCheckoutRequest):
    """
    Create a Stripe Checkout session for Pro subscription.
    """
    import stripe
    stripe.api_key = STRIPE_API_KEY
    
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{
                "price": PRO_MONTHLY_PRICE_ID,
                "quantity": 1
            }],
            metadata={
                "user_id": request.user_id,
                "tier": request.tier
            },
            success_url=f"{FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/payment/cancel"
        )
        
        logger.info(f"Created checkout session for user {request.user_id}")
        
        return {
            "url": session.url,
            "session_id": session.id
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhooks.
    Events: checkout.session.completed, customer.subscription.deleted
    """
    import stripe
    stripe.api_key = STRIPE_API_KEY
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle events
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await handle_checkout_complete(session)
    
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        await handle_subscription_cancelled(subscription)
    
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        await handle_payment_failed(invoice)
    
    return {"status": "success"}


async def handle_checkout_complete(session: dict):
    """Handle successful checkout."""
    user_id = session.get("metadata", {}).get("user_id")
    tier = session.get("metadata", {}).get("tier", "pro")
    
    logger.info(f"Checkout complete for user {user_id}, tier {tier}")
    
    # Update user tier in database
    from ai.credits_rate_limiter import CreditsRateLimiter
    limiter = CreditsRateLimiter()
    limiter.update_tier(user_id, tier)
    
    # Record payment
    # TODO: Add to payment_history table


async def handle_subscription_cancelled(subscription: dict):
    """Handle subscription cancellation."""
    customer_id = subscription.get("customer")
    
    logger.info(f"Subscription cancelled for customer {customer_id}")
    
    # Downgrade user to free
    # TODO: Look up user by customer_id and downgrade


async def handle_payment_failed(invoice: dict):
    """Handle failed payment."""
    customer_id = invoice.get("customer")
    
    logger.warning(f"Payment failed for customer {customer_id}")
    
    # TODO: Send notification to user


@router.get("/subscription/{user_id}")
async def get_subscription(user_id: str):
    """Get subscription status for a user."""
    from ai.credits_rate_limiter import CreditsRateLimiter
    
    limiter = CreditsRateLimiter()
    status = limiter.get_user_status(user_id)
    
    return {
        "user_id": user_id,
        "tier": status.get("tier", "free"),
        "credits": status.get("remaining_credits", 0),
        "queries_used": status.get("used_credits", 0)
    }


@router.post("/cancel/{user_id}")
async def cancel_subscription(user_id: str):
    """Cancel a user's subscription."""
    # TODO: Get customer_id from database and cancel in Stripe
    logger.info(f"Cancel subscription requested for user {user_id}")
    return {"status": "cancelled"}
```

#### 4.3.2 File: `backend/services/stripe_service.py`

```python
"""
Stripe Service - Helper functions for Stripe operations.
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("valora.stripe")

# Initialize Stripe
import stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")


class StripeService:
    """
    Service class for Stripe operations.
    """
    
    def __init__(self):
        self.is_configured = bool(stripe.api_key)
    
    def create_customer(self, email: str, user_id: str) -> Optional[str]:
        """Create a Stripe customer for a user."""
        if not self.is_configured:
            return None
        
        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={"user_id": user_id}
            )
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create customer: {e}")
            return None
    
    def create_subscription(self, customer_id: str, price_id: str) -> Optional[Dict]:
        """Create a subscription for a customer."""
        if not self.is_configured:
            return None
        
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"]
            )
            return {
                "subscription_id": subscription.id,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            return None
    
    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription."""
        if not self.is_configured:
            return False
        
        try:
            stripe.Subscription.delete(subscription_id)
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return False
    
    def get_subscription(self, subscription_id: str) -> Optional[Dict]:
        """Get subscription details."""
        if not self.is_configured:
            return None
        
        try:
            sub = stripe.Subscription.retrieve(subscription_id)
            return {
                "status": sub.status,
                "current_period_end": sub.current_period_end,
                "cancel_at_period_end": sub.cancel_at_period_end
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get subscription: {e}")
            return None


# Singleton
_service_instance = None

def get_stripe_service() -> StripeService:
    global _service_instance
    if _service_instance is None:
        _service_instance = StripeService()
    return _service_instance
```

### 4.4 Environment Variables

Add to `.env`:
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
FRONTEND_URL=http://localhost:5173
```

### 4.5 Integration Points

1. **In [`server.py`](backend/server.py):**
   ```python
   from routes.payment_routes import router as payment_router
   app.include_router(payment_router)
   ```

2. **In [`credits_rate_limiter.py`](backend/ai/credits_rate_limiter.py):**
   ```python
   def update_tier(self, user_id: str, tier: str):
       """Update user tier after payment."""
       with self._get_conn() as conn:
           conn.execute("""
               UPDATE user_credits 
               SET tier = ?, 
                   total_credits = ?,
                   monthly_reset_at = ?
               WHERE user_id = ?
           """, (tier, self.TIER_CREDITS[tier]['monthly_credits'], 
                 time.time() + 30*24*3600, user_id))
   ```

---

## Summary

### New Files (12)

| File | Purpose |
|------|---------|
| `backend/ai/tiered_planner.py` | 4-tier planning orchestrator |
| `backend/ai/tier1_templates.py` | Rule templates |
| `backend/ai/tier2_fewshot.py` | Few-shot prompts |
| `backend/ai/tier3_specialist.py` | LoRA specialist |
| `backend/ai/sequential_model_manager.py` | Model lifecycle |
| `backend/ai/task_batcher.py` | Task batching |
| `backend/ai/ui_tab_renderer.py` | Tab generation |
| `backend/routes/payment_routes.py` | Stripe endpoints |
| `backend/services/stripe_service.py` | Stripe helper |
| `src/components/TabPanel.jsx` | Tab display |
| `src/components/LockedTab.jsx` | Upgrade prompt |

### Modified Files (4)

| File | Changes |
|------|---------|
| `backend/ai/self_learning.py` | Add Tier 4 promotion |
| `backend/routes/chat_routes.py` | Add SSE events, tab rendering |
| `backend/ai/credits_rate_limiter.py` | Add tier update method |
| `src/components/EnhancedChatPanel.jsx` | Add TabPanel |

---

*Implementation Plan v1.0 - February 16, 2026*
