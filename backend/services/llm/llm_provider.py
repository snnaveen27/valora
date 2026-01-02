"""
LLM Provider Abstraction Layer
Supports multiple LLM backends: OpenRouter, Local Fine-tuned Models, Hybrid Setup
Designed for seamless switching between providers and automatic model tuning.

Future Architecture:
- Student Models: Qwen3-VL-32B (vision), Qwen3-72B (reasoning)
- Teacher Model: GPT-4/Claude for auto-tuning student models
- Routing: Intelligent task-based model selection
"""

import os
import json
import logging
import httpx
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENROUTER = "openrouter"
    QWEN_LOCAL = "qwen_local"       # Self-hosted Qwen models
    OLLAMA = "ollama"               # Ollama local models
    VLLM = "vllm"                   # vLLM inference server
    HYBRID = "hybrid"               # Intelligent routing between models


class ModelType(str, Enum):
    """Model capability types for routing"""
    GENERAL = "general"             # General purpose tasks
    VISION = "vision"               # Image understanding
    REASONING = "reasoning"         # Complex reasoning
    CODE = "code"                   # Code generation
    EMBEDDING = "embedding"         # Text embeddings


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    name: str
    provider: LLMProvider
    model_id: str
    model_type: ModelType = ModelType.GENERAL
    max_tokens: int = 4096
    temperature: float = 0.7
    context_window: int = 32768
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    endpoint: Optional[str] = None
    api_key_env: Optional[str] = None
    supports_vision: bool = False
    supports_function_calling: bool = True
    is_fine_tuned: bool = False
    fine_tune_task: Optional[str] = None


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# Model Registry - All available models
# ============================================================

MODEL_REGISTRY: Dict[str, ModelConfig] = {
    # OpenRouter Models (Current)
    "gpt-4o": ModelConfig(
        name="GPT-4o",
        provider=LLMProvider.OPENROUTER,
        model_id="openai/gpt-4o",
        model_type=ModelType.GENERAL,
        max_tokens=4096,
        context_window=128000,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        supports_vision=True,
        api_key_env="OPENROUTER_API_KEY"
    ),
    "claude-3.5-sonnet": ModelConfig(
        name="Claude 3.5 Sonnet",
        provider=LLMProvider.OPENROUTER,
        model_id="anthropic/claude-3.5-sonnet",
        model_type=ModelType.REASONING,
        max_tokens=8192,
        context_window=200000,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        supports_vision=True,
        api_key_env="OPENROUTER_API_KEY"
    ),
    "deepseek-chat": ModelConfig(
        name="DeepSeek Chat",
        provider=LLMProvider.OPENROUTER,
        model_id="deepseek/deepseek-chat",
        model_type=ModelType.GENERAL,
        max_tokens=4096,
        context_window=32768,
        cost_per_1k_input=0.00014,
        cost_per_1k_output=0.00028,
        api_key_env="OPENROUTER_API_KEY"
    ),
    
    # Future: Qwen Fine-tuned Models (Student Models)
    "qwen3-vl-32b": ModelConfig(
        name="Qwen3 VL 32B (Fine-tuned)",
        provider=LLMProvider.QWEN_LOCAL,
        model_id="qwen3-vl-32b-valora",
        model_type=ModelType.VISION,
        max_tokens=4096,
        context_window=32768,
        supports_vision=True,
        is_fine_tuned=True,
        fine_tune_task="real_estate_vision",
        endpoint="http://localhost:8080/v1"
    ),
    "qwen3-72b": ModelConfig(
        name="Qwen3 72B (Fine-tuned)",
        provider=LLMProvider.QWEN_LOCAL,
        model_id="qwen3-72b-valora",
        model_type=ModelType.REASONING,
        max_tokens=8192,
        context_window=131072,
        is_fine_tuned=True,
        fine_tune_task="real_estate_reasoning",
        endpoint="http://localhost:8081/v1"
    ),
    "qwen3-next-80b": ModelConfig(
        name="Qwen3 Next 80B (Fine-tuned)",
        provider=LLMProvider.QWEN_LOCAL,
        model_id="qwen3-next-80b-valora",
        model_type=ModelType.REASONING,
        max_tokens=8192,
        context_window=131072,
        is_fine_tuned=True,
        fine_tune_task="real_estate_advanced",
        endpoint="http://localhost:8082/v1"
    ),
    
    # Teacher Model for Auto-Tuning
    "teacher-gpt4": ModelConfig(
        name="Teacher GPT-4 (Auto-Tuning)",
        provider=LLMProvider.OPENROUTER,
        model_id="openai/gpt-4-turbo",
        model_type=ModelType.REASONING,
        max_tokens=4096,
        context_window=128000,
        cost_per_1k_input=0.01,
        cost_per_1k_output=0.03,
        api_key_env="OPENROUTER_API_KEY"
    )
}


# ============================================================
# Base LLM Client Interface
# ============================================================

class BaseLLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> LLMResponse:
        """Generate completion from messages"""
        pass
    
    @abstractmethod
    async def generate_with_functions(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        model: str,
        **kwargs
    ) -> LLMResponse:
        """Generate with function calling support"""
        pass


# ============================================================
# OpenRouter Client (Current Default)
# ============================================================

class OpenRouterClient(BaseLLMClient):
    """OpenRouter API client"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://valora.ai",
            "X-Title": "Valora AI"
        }
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek/deepseek-chat",
        **kwargs
    ) -> LLMResponse:
        start_time = datetime.now()
        
        config = MODEL_REGISTRY.get(model, MODEL_REGISTRY["deepseek-chat"])
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": config.model_id,
                    "messages": messages,
                    "max_tokens": kwargs.get("max_tokens", config.max_tokens),
                    "temperature": kwargs.get("temperature", config.temperature),
                    **kwargs
                }
            )
            
            data = response.json()
            latency = (datetime.now() - start_time).total_seconds() * 1000
            
            usage = data.get("usage", {})
            cost = (
                usage.get("prompt_tokens", 0) * config.cost_per_1k_input / 1000 +
                usage.get("completion_tokens", 0) * config.cost_per_1k_output / 1000
            )
            
            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=model,
                provider="openrouter",
                usage=usage,
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
                latency_ms=latency,
                cost_usd=cost
            )
    
    async def generate_with_functions(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        model: str = "deepseek/deepseek-chat",
        **kwargs
    ) -> LLMResponse:
        return await self.generate(
            messages=messages,
            model=model,
            tools=[{"type": "function", "function": f} for f in functions],
            **kwargs
        )


# ============================================================
# Local Qwen Client (Future - vLLM/Ollama Backend)
# ============================================================

class QwenLocalClient(BaseLLMClient):
    """Client for self-hosted Qwen models via vLLM or Ollama"""
    
    def __init__(self, endpoint: str = "http://localhost:8080/v1"):
        self.endpoint = endpoint
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str = "qwen3-72b",
        **kwargs
    ) -> LLMResponse:
        start_time = datetime.now()
        
        config = MODEL_REGISTRY.get(model)
        endpoint = config.endpoint if config else self.endpoint
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{endpoint}/chat/completions",
                    json={
                        "model": config.model_id if config else model,
                        "messages": messages,
                        "max_tokens": kwargs.get("max_tokens", 4096),
                        "temperature": kwargs.get("temperature", 0.7),
                        **kwargs
                    }
                )
                
                data = response.json()
                latency = (datetime.now() - start_time).total_seconds() * 1000
                
                return LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=model,
                    provider="qwen_local",
                    usage=data.get("usage", {}),
                    finish_reason=data["choices"][0].get("finish_reason", "stop"),
                    latency_ms=latency,
                    cost_usd=0.0,  # Self-hosted = no API cost
                    metadata={"is_fine_tuned": config.is_fine_tuned if config else False}
                )
            except Exception as e:
                logger.error(f"Qwen local generation failed: {e}")
                raise
    
    async def generate_with_functions(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        model: str = "qwen3-72b",
        **kwargs
    ) -> LLMResponse:
        return await self.generate(
            messages=messages,
            model=model,
            tools=[{"type": "function", "function": f} for f in functions],
            **kwargs
        )


# ============================================================
# Hybrid Router (Future - Intelligent Model Selection)
# ============================================================

class HybridLLMRouter:
    """
    Intelligent router that selects optimal model based on task.
    Routes between fine-tuned Qwen models and teacher model.
    """
    
    def __init__(self):
        self.openrouter = OpenRouterClient()
        self.qwen_client = QwenLocalClient()
        self.use_local_models = os.getenv("USE_LOCAL_MODELS", "false").lower() == "true"
        
        # Task to model mapping
        self.task_routing = {
            "property_valuation": "qwen3-72b",
            "image_analysis": "qwen3-vl-32b",
            "market_forecast": "qwen3-next-80b",
            "general_chat": "deepseek-chat",
            "complex_reasoning": "qwen3-next-80b",
            "auto_tuning": "teacher-gpt4"
        }
    
    def select_model(self, task: str, prefer_local: bool = True) -> str:
        """Select optimal model for task"""
        if not self.use_local_models or not prefer_local:
            # Fallback to OpenRouter models
            return "deepseek-chat"
        
        return self.task_routing.get(task, "qwen3-72b")
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        task: str = "general_chat",
        **kwargs
    ) -> LLMResponse:
        """Generate with automatic model selection"""
        model = self.select_model(task)
        config = MODEL_REGISTRY.get(model)
        
        if config and config.provider == LLMProvider.QWEN_LOCAL and self.use_local_models:
            return await self.qwen_client.generate(messages, model, **kwargs)
        else:
            return await self.openrouter.generate(messages, model, **kwargs)
    
    async def generate_training_data(
        self,
        student_model: str,
        task_examples: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Use teacher model to generate training data for student models.
        This enables continuous improvement of fine-tuned models.
        """
        training_data = []
        teacher = "teacher-gpt4"
        
        for example in task_examples:
            # Get teacher's response
            teacher_response = await self.openrouter.generate(
                messages=[
                    {"role": "system", "content": "You are an expert real estate AI assistant. Provide detailed, accurate responses."},
                    {"role": "user", "content": example["input"]}
                ],
                model=teacher,
                temperature=0.3  # Lower temp for consistent training data
            )
            
            training_data.append({
                "input": example["input"],
                "output": teacher_response.content,
                "task": example.get("task", "general"),
                "model": student_model,
                "teacher": teacher,
                "generated_at": datetime.now().isoformat()
            })
        
        return training_data


# ============================================================
# Main LLM Service (Entry Point)
# ============================================================

class LLMService:
    """
    Main LLM service with provider abstraction.
    Currently uses OpenRouter, ready for hybrid fine-tuned setup.
    """
    
    def __init__(self, provider: LLMProvider = LLMProvider.OPENROUTER):
        self.provider = provider
        self._init_client()
    
    def _init_client(self):
        if self.provider == LLMProvider.OPENROUTER:
            self._client = OpenRouterClient()
        elif self.provider == LLMProvider.QWEN_LOCAL:
            self._client = QwenLocalClient()
        elif self.provider == LLMProvider.HYBRID:
            self._client = HybridLLMRouter()
        else:
            self._client = OpenRouterClient()
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        task: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Specific model to use (optional)
            task: Task type for hybrid routing (optional)
            **kwargs: Additional generation parameters
        """
        if isinstance(self._client, HybridLLMRouter):
            return await self._client.generate(messages, task=task or "general_chat", **kwargs)
        else:
            return await self._client.generate(messages, model=model or "deepseek-chat", **kwargs)
    
    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate with function/tool calling"""
        return await self._client.generate_with_functions(
            messages=messages,
            functions=tools,
            model=model or "deepseek-chat",
            **kwargs
        )
    
    def switch_provider(self, provider: LLMProvider):
        """Switch LLM provider at runtime"""
        self.provider = provider
        self._init_client()
        logger.info(f"Switched LLM provider to: {provider}")
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models"""
        return [
            {
                "id": key,
                "name": config.name,
                "provider": config.provider.value,
                "type": config.model_type.value,
                "is_fine_tuned": config.is_fine_tuned,
                "supports_vision": config.supports_vision
            }
            for key, config in MODEL_REGISTRY.items()
        ]


# ============================================================
# Singleton Instance
# ============================================================

# Default to OpenRouter, can switch to HYBRID when local models are ready
llm_service = LLMService(provider=LLMProvider.OPENROUTER)


# ============================================================
# Convenience Functions
# ============================================================

async def chat(messages: List[Dict[str, str]], **kwargs) -> str:
    """Simple chat function"""
    response = await llm_service.chat(messages, **kwargs)
    return response.content


async def chat_with_context(
    user_message: str,
    system_prompt: str = "You are Valora AI, an expert real estate assistant for Indian property markets.",
    **kwargs
) -> str:
    """Chat with system context"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    response = await llm_service.chat(messages, **kwargs)
    return response.content
