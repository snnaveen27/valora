"""
Valora AI Package - Production Architecture (v3.0)

Active pipeline:
- gis_agents: GIS Agent Orchestrator — deterministic fact gathering
- agentic_loop: Autonomous reasoning with Think→Act→Observe→Reflect
- agentic_memory: SQLite-backed persistent memory for tool results
- self_learning: Tracks tool effectiveness, learns optimal sequences
- tools_registry: Dynamic tool registry with enable/disable at runtime
- ollama_client: Local LLM client (Ollama/Qwen3 4B)
- model_router: Intelligent model selection (local vs cloud)
- fact_verifier: Truth Firewall enforcement
- rag_service: Vector search for properties/documents
- credits_rate_limiter: Usage metering per user tier

DEPRECATED (not in active pipeline, kept for reference):
- unified_valora_brain: Legacy orchestrator (replaced by chat_routes pipeline)
- valora_brain_core: Legacy intent classification (replaced by IntentRouter)
- production_task_planner: Legacy task planner (replaced by agentic_loop)
- pattern_learner: Legacy pattern matching (replaced by self_learning)
- query_refiner: Legacy query refinement (unused)
- streaming_intent_classifier: Legacy classifier stub (unused)
- multimodal_reasoning: Only used by unified_valora_brain (unused)
- response_templates: Only used by gis_agents for format hints

Usage:
    from ai.gis_agents import IntentRouter, Intent, get_gis_orchestrator
    from ai.agentic_loop import get_agentic_loop
    from ai.tools_registry import get_tool_registry
    from ai.agentic_memory import get_agentic_memory
    from ai.self_learning import get_self_learning_engine
"""

from .gis_agents import get_gis_orchestrator, IntentRouter, Intent, AgentFacts
from .fact_verifier import get_fact_verifier
from .agentic_loop import get_agentic_loop
from .tools_registry import get_tool_registry
from .agentic_memory import get_agentic_memory
from .self_learning import get_self_learning_engine

__all__ = [
    # GIS Agents (core pipeline)
    'get_gis_orchestrator',
    'IntentRouter',
    'Intent',
    'AgentFacts',
    # Agentic System
    'get_agentic_loop',
    'get_tool_registry',
    'get_agentic_memory',
    'get_self_learning_engine',
    # Fact Verification
    'get_fact_verifier',
]

__version__ = "3.0.0"
