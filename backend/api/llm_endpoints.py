"""
LLM Management API Endpoints
Control, monitor, and tune LLM models from admin dashboard.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["LLM Management"])

# Import LLM services
try:
    from backend.services.llm.llm_provider import (
        llm_service, LLMProvider, MODEL_REGISTRY
    )
    from backend.services.llm.self_learning import (
        learning_engine, InteractionType, FeedbackType
    )
    from backend.services.llm.auto_tuning import (
        create_tuning_pipeline, TuningTask, SAMPLE_TRAINING_INPUTS
    )
    LLM_AVAILABLE = True
except ImportError as e:
    LLM_AVAILABLE = False
    logger.warning(f"LLM services not available: {e}")


# ===================== Request Models =====================

class SwitchProviderRequest(BaseModel):
    provider: str = Field(..., description="Provider: openrouter, qwen_local, hybrid")


class FeedbackRequest(BaseModel):
    interaction_id: str
    feedback_type: str = Field(..., description="thumbs_up, thumbs_down, rating, correction")
    score: Optional[float] = None
    correction: Optional[str] = None


class LogInteractionRequest(BaseModel):
    user_id: str
    session_id: str
    interaction_type: str = "chat"
    user_input: str
    ai_response: str
    model_used: str
    latency_ms: float
    metadata: Optional[Dict[str, Any]] = None


class CreateExperimentRequest(BaseModel):
    name: str
    control_model: str
    challenger_model: str
    traffic_split: float = Field(default=0.1, ge=0.01, le=0.5)


class TriggerTrainingRequest(BaseModel):
    student_model: str = "qwen3-72b"
    task: str = "property_valuation"
    num_examples: int = 100


# ===================== Provider Management =====================

@router.get("/status")
async def get_llm_status() -> Dict[str, Any]:
    """Get current LLM system status"""
    if not LLM_AVAILABLE:
        return {"available": False, "error": "LLM services not loaded"}
    
    return {
        "available": True,
        "current_provider": llm_service.provider.value,
        "models_registered": len(MODEL_REGISTRY),
        "learning_stats": learning_engine.get_learning_stats()
    }


@router.get("/providers")
async def list_providers() -> Dict[str, Any]:
    """List available LLM providers"""
    return {
        "providers": [
            {
                "id": "openrouter",
                "name": "OpenRouter",
                "description": "Cloud LLM access (GPT-4, Claude, DeepSeek)",
                "status": "active",
                "is_current": llm_service.provider == LLMProvider.OPENROUTER if LLM_AVAILABLE else False
            },
            {
                "id": "qwen_local",
                "name": "Qwen Local",
                "description": "Self-hosted fine-tuned Qwen models",
                "status": "configured",
                "is_current": llm_service.provider == LLMProvider.QWEN_LOCAL if LLM_AVAILABLE else False
            },
            {
                "id": "hybrid",
                "name": "Hybrid Router",
                "description": "Intelligent routing between cloud and local models",
                "status": "configured",
                "is_current": llm_service.provider == LLMProvider.HYBRID if LLM_AVAILABLE else False
            }
        ]
    }


@router.post("/switch-provider")
async def switch_provider(request: SwitchProviderRequest) -> Dict[str, Any]:
    """Switch LLM provider"""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="LLM services not available")
    
    provider_map = {
        "openrouter": LLMProvider.OPENROUTER,
        "qwen_local": LLMProvider.QWEN_LOCAL,
        "hybrid": LLMProvider.HYBRID
    }
    
    if request.provider not in provider_map:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {request.provider}")
    
    llm_service.switch_provider(provider_map[request.provider])
    
    return {
        "success": True,
        "provider": request.provider,
        "message": f"Switched to {request.provider}"
    }


# ===================== Model Management =====================

@router.get("/models")
async def list_models() -> Dict[str, Any]:
    """List all registered models"""
    if not LLM_AVAILABLE:
        return {"models": []}
    
    models = llm_service.get_available_models()
    
    # Add performance data
    performance = learning_engine.get_model_performance()
    
    for model in models:
        perf = performance.get(model["id"], {})
        model["performance"] = {
            "total_interactions": perf.get("total_interactions", 0),
            "avg_latency_ms": round(perf.get("avg_latency_ms", 0), 1),
            "satisfaction_rate": round(perf.get("satisfaction_rate", 0) * 100, 1),
            "avg_quality_score": round(perf.get("avg_quality_score", 0), 2)
        }
    
    return {"models": models}


@router.get("/models/{model_id}/performance")
async def get_model_performance(model_id: str) -> Dict[str, Any]:
    """Get detailed performance for a specific model"""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="LLM services not available")
    
    performance = learning_engine.get_model_performance(model_id)
    
    if model_id not in performance:
        return {
            "model_id": model_id,
            "message": "No performance data available yet"
        }
    
    return {
        "model_id": model_id,
        "performance": performance[model_id]
    }


# ===================== Learning & Feedback =====================

@router.post("/interactions/log")
async def log_interaction(request: LogInteractionRequest) -> Dict[str, Any]:
    """Log an interaction for learning"""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="LLM services not available")
    
    try:
        interaction_type = InteractionType(request.interaction_type)
    except ValueError:
        interaction_type = InteractionType.CHAT
    
    interaction_id = await learning_engine.log_interaction(
        user_id=request.user_id,
        session_id=request.session_id,
        interaction_type=interaction_type,
        user_input=request.user_input,
        ai_response=request.ai_response,
        model_used=request.model_used,
        latency_ms=request.latency_ms,
        metadata=request.metadata
    )
    
    return {
        "success": True,
        "interaction_id": interaction_id
    }


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest) -> Dict[str, Any]:
    """Submit feedback for an interaction"""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="LLM services not available")
    
    try:
        feedback_type = FeedbackType(request.feedback_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid feedback type: {request.feedback_type}")
    
    success = await learning_engine.submit_feedback(
        interaction_id=request.interaction_id,
        feedback_type=feedback_type,
        score=request.score,
        correction=request.correction
    )
    
    return {"success": success}


@router.get("/learning/stats")
async def get_learning_stats() -> Dict[str, Any]:
    """Get learning system statistics"""
    if not LLM_AVAILABLE:
        return {"available": False}
    
    return learning_engine.get_learning_stats()


@router.get("/learning/drift")
async def check_drift() -> Dict[str, Any]:
    """Check for model performance drift"""
    if not LLM_AVAILABLE:
        return {"alerts": []}
    
    alerts = learning_engine.detect_drift()
    
    return {
        "alerts": alerts,
        "checked_at": datetime.now().isoformat()
    }


@router.post("/learning/generate-training")
async def generate_training_data() -> Dict[str, Any]:
    """Generate training data from high-quality interactions"""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="LLM services not available")
    
    count = await learning_engine.generate_training_batch()
    
    return {
        "success": True,
        "examples_generated": count
    }


@router.get("/learning/retrain-status")
async def check_retrain_status() -> Dict[str, Any]:
    """Check if retraining should be triggered"""
    if not LLM_AVAILABLE:
        return {"should_retrain": False, "reason": "LLM services not available"}
    
    should_retrain, reason = learning_engine.should_trigger_retraining()
    
    return {
        "should_retrain": should_retrain,
        "reason": reason
    }


# ===================== A/B Testing =====================

@router.post("/experiments/create")
async def create_experiment(request: CreateExperimentRequest) -> Dict[str, Any]:
    """Create a new A/B test experiment"""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="LLM services not available")
    
    experiment_id = learning_engine.create_experiment(
        name=request.name,
        control_model=request.control_model,
        challenger_model=request.challenger_model,
        traffic_split=request.traffic_split
    )
    
    return {
        "success": True,
        "experiment_id": experiment_id
    }


@router.get("/experiments")
async def list_experiments() -> Dict[str, Any]:
    """List all A/B test experiments"""
    if not LLM_AVAILABLE:
        return {"experiments": []}
    
    experiments = []
    for exp_id in learning_engine.active_experiments:
        result = learning_engine.get_experiment_results(exp_id)
        experiments.append(result)
    
    return {"experiments": experiments}


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str) -> Dict[str, Any]:
    """Get experiment results"""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="LLM services not available")
    
    result = learning_engine.get_experiment_results(experiment_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return result


# ===================== Training Management =====================

@router.get("/training/tasks")
async def list_training_tasks() -> Dict[str, Any]:
    """List available training tasks"""
    return {
        "tasks": [
            {"id": "property_valuation", "name": "Property Valuation", "examples": 3},
            {"id": "market_analysis", "name": "Market Analysis", "examples": 3},
            {"id": "investment_advice", "name": "Investment Advice", "examples": 3},
            {"id": "image_analysis", "name": "Image Analysis", "examples": 0},
            {"id": "location_intelligence", "name": "Location Intelligence", "examples": 0},
            {"id": "risk_assessment", "name": "Risk Assessment", "examples": 0},
            {"id": "narrative_generation", "name": "Narrative Generation", "examples": 0}
        ],
        "sample_inputs": SAMPLE_TRAINING_INPUTS if LLM_AVAILABLE else {}
    }


@router.post("/training/trigger")
async def trigger_training(request: TriggerTrainingRequest) -> Dict[str, Any]:
    """Trigger model fine-tuning pipeline"""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="LLM services not available")
    
    try:
        task = TuningTask(request.task)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid task: {request.task}")
    
    pipeline = create_tuning_pipeline(
        student_model=request.student_model,
        task=task
    )
    
    # Generate fine-tuning script
    script = pipeline.generate_finetune_script()
    serve_cmd = pipeline.generate_vllm_serve_command()
    
    return {
        "success": True,
        "message": f"Training pipeline created for {request.student_model}",
        "finetune_script": script,
        "serve_command": serve_cmd,
        "instructions": [
            "1. Run the fine-tuning script on a GPU server",
            "2. Monitor training with tensorboard",
            "3. After training, serve the model with vLLM",
            "4. Switch provider to 'qwen_local' or 'hybrid'"
        ]
    }


# ===================== Dashboard Data =====================

@router.get("/dashboard")
async def get_dashboard_data() -> Dict[str, Any]:
    """Get comprehensive dashboard data for admin UI"""
    if not LLM_AVAILABLE:
        return {
            "available": False,
            "current_provider": "unknown",
            "models": [],
            "learning": {},
            "experiments": []
        }
    
    performance = learning_engine.get_model_performance()
    models = llm_service.get_available_models()
    
    # Enhance models with performance data
    for model in models:
        perf = performance.get(model["id"], {})
        model["interactions"] = perf.get("total_interactions", 0)
        model["satisfaction"] = round(perf.get("satisfaction_rate", 0) * 100, 1)
        model["latency"] = round(perf.get("avg_latency_ms", 0), 0)
    
    learning_stats = learning_engine.get_learning_stats()
    drift_alerts = learning_engine.detect_drift()
    should_retrain, retrain_reason = learning_engine.should_trigger_retraining()
    
    experiments = [
        learning_engine.get_experiment_results(exp_id)
        for exp_id in learning_engine.active_experiments
    ]
    
    return {
        "available": True,
        "current_provider": llm_service.provider.value,
        "models": models,
        "learning": {
            **learning_stats,
            "drift_alerts": drift_alerts,
            "should_retrain": should_retrain,
            "retrain_reason": retrain_reason
        },
        "experiments": experiments
    }
