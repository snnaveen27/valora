"""
LLM Service Module
Provides abstracted LLM access with support for multiple providers.

Current: OpenRouter (GPT-4, Claude, DeepSeek)
Future: Hybrid fine-tuned Qwen models with teacher-based auto-tuning
"""

from backend.services.llm.llm_provider import (
    LLMService,
    LLMProvider,
    ModelType,
    ModelConfig,
    LLMResponse,
    llm_service,
    chat,
    chat_with_context,
    MODEL_REGISTRY
)

from backend.services.llm.auto_tuning import (
    AutoTuningPipeline,
    TuningConfig,
    TuningTask,
    TrainingExample,
    create_tuning_pipeline,
    SAMPLE_TRAINING_INPUTS
)

__all__ = [
    # Main service
    "LLMService",
    "llm_service",
    
    # Enums
    "LLMProvider",
    "ModelType",
    "TuningTask",
    
    # Data classes
    "ModelConfig",
    "LLMResponse",
    "TuningConfig",
    "TrainingExample",
    
    # Functions
    "chat",
    "chat_with_context",
    "create_tuning_pipeline",
    
    # Constants
    "MODEL_REGISTRY",
    "SAMPLE_TRAINING_INPUTS"
]
