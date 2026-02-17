"""
Sequential Model Manager - Manages model loading for 6GB VRAM.
Only one model loaded at a time, with smart switching.
"""

import subprocess
import time
import logging
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass
from enum import Enum
import asyncio

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
    - Credit tracking per inference
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
        ),
        'valora-2025v1': ModelInfo(
            name='valora-2025v1',
            vram_required_gb=4.0,
            purpose='general_execution'
        )
    }
    
    # Local models (2 credits per inference)
    LOCAL_MODELS = ['qwen3:4b-instruct', 'qwen3:8b', 'phi-4', 'valora-2025v1', 'qwen', 'phi']
    
    def __init__(
        self, 
        vram_gb: float = 6.0,
        sse_callback: Optional[Callable] = None,
        credits_limiter = None
    ):
        self.vram_gb = vram_gb
        self.sse_callback = sse_callback
        self.credits_limiter = credits_limiter
        self.current_model: Optional[str] = None
        self.switch_overhead_s = 4.0
        self._model_status: Dict[str, ModelStatus] = {
            name: ModelStatus.NOT_LOADED 
            for name in self.MODELS
        }
        self._inference_count = 0
    
    def is_local_model(self, model: str) -> bool:
        """Check if model is local (Ollama)."""
        model_lower = model.lower()
        return any(local in model_lower for local in self.LOCAL_MODELS)
    
    def get_model_type(self, model: str) -> str:
        """Get model type for credit calculation."""
        return 'local' if self.is_local_model(model) else 'cloud'
    
    def ensure_model(self, model_name: str, user_id: str = None) -> Dict[str, Any]:
        """
        Ensure the specified model is loaded.
        Switches models if necessary.
        
        Args:
            model_name: Name of the model to load
            user_id: User ID for credit check
        
        Returns:
            Dict with status and credit info
        """
        # Normalize model name
        model_name = self._normalize_model_name(model_name)
        
        # Check credits if user provided
        credit_cost = 2 if self.is_local_model(model_name) else 5
        
        if user_id and self.credits_limiter:
            from ai.credits_rate_limiter import CreditsRateLimiter
            if isinstance(self.credits_limiter, CreditsRateLimiter):
                balance = self.credits_limiter.get_balance(user_id)
                if balance['total_available'] < credit_cost:
                    return {
                        'success': False,
                        'error': 'insufficient_credits',
                        'required': credit_cost,
                        'available': balance['total_available']
                    }
        
        # Check if already loaded
        if self.current_model == model_name:
            logger.debug(f"Model {model_name} already loaded")
            return {
                'success': True,
                'model': model_name,
                'already_loaded': True,
                'credit_cost': credit_cost
            }
        
        # Check if model exists in our registry
        if model_name not in self.MODELS:
            logger.warning(f"Unknown model: {model_name}, attempting anyway")
        
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
            return {
                'success': True,
                'model': model_name,
                'already_loaded': False,
                'credit_cost': credit_cost
            }
        else:
            self._emit_sse('model_error', {'model': model_name})
            return {
                'success': False,
                'error': 'model_load_failed',
                'model': model_name
            }
    
    def _normalize_model_name(self, name: str) -> str:
        """Normalize model name to canonical form."""
        aliases = {
            'qwen3': 'qwen3:4b-instruct',
            'qwen': 'qwen3:4b-instruct',
            'phi4': 'phi-4',
            'phi': 'phi-4',
            'valora': 'valora-2025v1',
        }
        return aliases.get(name.lower(), name)
    
    def _unload_model(self, model_name: str):
        """Unload a model from VRAM."""
        logger.info(f"Unloading model: {model_name}")
        self._model_status[model_name] = ModelStatus.NOT_LOADED
        
        try:
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
            'inference_count': self._inference_count,
            'models': {
                name: {
                    'status': self._model_status.get(name, ModelStatus.NOT_LOADED).value,
                    'vram_required': self.MODELS[name].vram_required_gb if name in self.MODELS else 0,
                    'purpose': self.MODELS[name].purpose if name in self.MODELS else 'unknown'
                }
                for name in self.MODELS
            }
        }
    
    def record_inference(self, model: str, user_id: str, inference_id: str = None) -> Dict[str, Any]:
        """
        Record an inference and deduct credits.
        
        Args:
            model: Model used
            user_id: User ID
            inference_id: Unique inference ID
            
        Returns:
            Dict with deduction details
        """
        self._inference_count += 1
        
        if self.credits_limiter:
            return self.credits_limiter.deduct_credits(
                user_id=user_id,
                model=model,
                inference_id=inference_id or f"inf_{self._inference_count}"
            )
        
        return {
            'success': True,
            'credits_deducted': 2 if self.is_local_model(model) else 5,
            'model': model
        }


class TaskBatcher:
    """
    Groups tasks by their required model.
    Minimizes model switches during execution.
    """
    
    def __init__(self, default_model: str = 'qwen3:4b-instruct'):
        self.default_model = default_model
    
    def batch_by_model(self, tasks: List[Any]) -> List[Dict[str, Any]]:
        """
        Group tasks by model, respecting dependencies.
        
        Args:
            tasks: List of tasks with model_hint attribute
            
        Returns:
            List of batches with model and tasks
        """
        batches: List[Dict[str, Any]] = []
        current_batch: Optional[Dict[str, Any]] = None
        
        for task in tasks:
            # Determine required model
            required_model = getattr(task, 'model_hint', None) or self.default_model
            
            if current_batch and current_batch['model'] == required_model:
                current_batch['tasks'].append(task)
            else:
                if current_batch:
                    batches.append(current_batch)
                current_batch = {'model': required_model, 'tasks': [task]}
        
        if current_batch and current_batch['tasks']:
            batches.append(current_batch)
        
        logger.info(f"Created {len(batches)} batches from {len(tasks)} tasks")
        for i, batch in enumerate(batches):
            logger.debug(f"  Batch {i+1}: {batch['model']} ({len(batch['tasks'])} tasks)")
        
        return batches
    
    def estimate_switches(self, batches: List[Dict[str, Any]]) -> int:
        """Estimate number of model switches needed."""
        if not batches:
            return 0
        
        switches = 0
        prev_model = None
        
        for batch in batches:
            if prev_model and batch['model'] != prev_model:
                switches += 1
            prev_model = batch['model']
        
        return switches
    
    def estimate_credits(self, batches: List[Dict[str, Any]]) -> int:
        """Estimate total credits needed."""
        total = 0
        for batch in batches:
            model = batch['model']
            # Local = 2 credits, Cloud = 5 credits
            cost = 2 if any(m in model.lower() for m in ['qwen', 'phi', 'valora']) else 5
            total += cost * len(batch['tasks'])
        return total


# Singleton instances
_manager_instance = None
_batcher_instance = None


def get_model_manager(
    sse_callback: Callable = None,
    credits_limiter = None
) -> SequentialModelManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SequentialModelManager(
            sse_callback=sse_callback,
            credits_limiter=credits_limiter
        )
    return _manager_instance


def get_task_batcher() -> TaskBatcher:
    global _batcher_instance
    if _batcher_instance is None:
        _batcher_instance = TaskBatcher()
    return _batcher_instance
