"""
Valora AI Package - Production Architecture (v3.1)

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

v2 Section Analysis Pipeline (NEW):
- spatial_feature_engine: Pre-compute deterministic features (anti-hallucination)
- section_prompts_v2: Feature-grounded prompt templates per section
- section_pipeline_v2: Full orchestrator (router → features → prompts → validator → synthesis)
- consistency_validator: Cross-section contradiction detection

v2 Production Additions:
- pipeline_metrics: Pipeline execution metrics (P95, cache rate, hallucination rate)
- drift_detector: Feature drift detection with baselines
- review_framework: Human-in-the-loop review queue



Usage:
    from ai.gis_agents import IntentRouter, Intent, get_gis_orchestrator
    from ai.agentic_loop import get_agentic_loop
    from ai.tools_registry import get_tool_registry
    from ai.agentic_memory import get_agentic_memory
    from ai.self_learning import get_self_learning_engine
    # v2 Pipeline:
    from ai.section_pipeline_v2 import run_section_analysis
    from ai.spatial_feature_engine import get_spatial_feature_engine
"""

from .gis_agents import get_gis_orchestrator, IntentRouter, Intent, AgentFacts
from .fact_verifier import get_fact_verifier
from .agentic_loop import get_agentic_loop
from .tools_registry import get_tool_registry
from .agentic_memory import get_agentic_memory
from .self_learning import get_self_learning_engine

# v2 Section Analysis Pipeline (lazy imports to avoid circular deps)
try:
    from .spatial_feature_engine import get_spatial_feature_engine, EvidenceReference
    from .section_pipeline_v2 import get_section_pipeline_v2, run_section_analysis
    from .consistency_validator import validate_sections
    from .pipeline_metrics import get_pipeline_metrics
    from .drift_detector import get_drift_detector
    from .review_framework import get_review_queue
    V2_PIPELINE_AVAILABLE = True
except ImportError:
    V2_PIPELINE_AVAILABLE = False
    get_spatial_feature_engine = None
    get_section_pipeline_v2 = None
    run_section_analysis = None
    validate_sections = None
    EvidenceReference = None
    get_pipeline_metrics = None
    get_drift_detector = None
    get_review_queue = None

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
    # v2 Section Analysis Pipeline
    'get_spatial_feature_engine',
    'get_section_pipeline_v2',
    'run_section_analysis',
    'validate_sections',
    'EvidenceReference',
    'V2_PIPELINE_AVAILABLE',
    'get_pipeline_metrics',
    'get_drift_detector',
    'get_review_queue',
]

__version__ = "3.1.0"
