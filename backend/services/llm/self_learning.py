"""
Self-Learning Intelligence System
Continuous improvement through user feedback, interaction analysis, and automatic model tuning.

Features:
- Interaction logging and quality scoring
- Automatic training data generation from high-quality interactions
- Model performance tracking and drift detection
- Scheduled retraining triggers
- A/B testing for model comparisons
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import hashlib
import random

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """Types of user feedback"""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"
    CORRECTION = "correction"
    IMPLICIT_POSITIVE = "implicit_positive"  # User followed recommendation
    IMPLICIT_NEGATIVE = "implicit_negative"  # User ignored/rejected


class InteractionType(str, Enum):
    """Types of interactions"""
    CHAT = "chat"
    VALUATION = "valuation"
    MARKET_ANALYSIS = "market_analysis"
    INVESTMENT_ADVICE = "investment_advice"
    PROPERTY_SEARCH = "property_search"
    LOCATION_QUERY = "location_query"


@dataclass
class Interaction:
    """Single user-AI interaction"""
    id: str
    user_id: str
    session_id: str
    interaction_type: InteractionType
    user_input: str
    ai_response: str
    model_used: str
    latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    feedback: Optional[FeedbackType] = None
    feedback_score: Optional[float] = None
    correction_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0  # Computed quality score
    used_for_training: bool = False


@dataclass
class ModelPerformance:
    """Track model performance over time"""
    model_id: str
    period_start: str
    period_end: str
    total_interactions: int = 0
    positive_feedback: int = 0
    negative_feedback: int = 0
    avg_latency_ms: float = 0.0
    avg_quality_score: float = 0.0
    error_rate: float = 0.0
    user_satisfaction: float = 0.0


@dataclass
class LearningConfig:
    """Configuration for self-learning system"""
    min_quality_for_training: float = 0.8
    auto_retrain_threshold: int = 1000  # New examples before retraining
    feedback_weight: float = 0.6
    implicit_signal_weight: float = 0.4
    quality_decay_days: int = 90  # Old data less relevant
    a_b_test_traffic_split: float = 0.1  # 10% to challenger model
    drift_detection_window_days: int = 7
    drift_threshold: float = 0.15  # 15% performance drop triggers alert


class SelfLearningEngine:
    """
    Self-learning engine that improves AI intelligence over time.
    
    Learning Signals:
    1. Explicit feedback (thumbs up/down, ratings, corrections)
    2. Implicit signals (user actions after recommendations)
    3. Interaction patterns (follow-up questions, session length)
    4. A/B test results
    """
    
    def __init__(self, config: LearningConfig = None):
        self.config = config or LearningConfig()
        self.interactions: List[Interaction] = []
        self.performance_history: List[ModelPerformance] = []
        self.data_dir = Path("data/learning")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory caches
        self._quality_cache: Dict[str, float] = {}
        self._model_stats: Dict[str, Dict[str, Any]] = {}
        
        # A/B test state
        self.active_experiments: Dict[str, Dict[str, Any]] = {}
        
        # Learning metrics
        self.metrics = {
            "total_interactions": 0,
            "total_feedback": 0,
            "training_examples_generated": 0,
            "models_retrained": 0,
            "drift_alerts": 0
        }
    
    # ===========================================
    # Interaction Logging
    # ===========================================
    
    async def log_interaction(
        self,
        user_id: str,
        session_id: str,
        interaction_type: InteractionType,
        user_input: str,
        ai_response: str,
        model_used: str,
        latency_ms: float,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Log a new interaction for learning"""
        interaction_id = hashlib.md5(
            f"{user_id}{session_id}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        interaction = Interaction(
            id=interaction_id,
            user_id=user_id,
            session_id=session_id,
            interaction_type=interaction_type,
            user_input=user_input,
            ai_response=ai_response,
            model_used=model_used,
            latency_ms=latency_ms,
            metadata=metadata or {}
        )
        
        # Compute initial quality score
        interaction.quality_score = self._compute_initial_quality(interaction)
        
        self.interactions.append(interaction)
        self.metrics["total_interactions"] += 1
        
        # Update model stats
        self._update_model_stats(model_used, latency_ms)
        
        # Check for training data generation
        await self._maybe_generate_training_data(interaction)
        
        logger.info(f"Logged interaction {interaction_id} for model {model_used}")
        return interaction_id
    
    async def submit_feedback(
        self,
        interaction_id: str,
        feedback_type: FeedbackType,
        score: float = None,
        correction: str = None
    ) -> bool:
        """Submit feedback for an interaction"""
        interaction = self._find_interaction(interaction_id)
        if not interaction:
            logger.warning(f"Interaction {interaction_id} not found")
            return False
        
        interaction.feedback = feedback_type
        interaction.feedback_score = score
        interaction.correction_text = correction
        
        # Recompute quality score with feedback
        interaction.quality_score = self._compute_quality_with_feedback(interaction)
        
        self.metrics["total_feedback"] += 1
        
        # High-quality corrections become training data immediately
        if correction and feedback_type == FeedbackType.CORRECTION:
            await self._create_training_example_from_correction(interaction)
        
        logger.info(f"Feedback submitted for {interaction_id}: {feedback_type.value}")
        return True
    
    async def log_implicit_signal(
        self,
        interaction_id: str,
        signal_type: str,
        signal_data: Dict[str, Any]
    ) -> bool:
        """Log implicit signals (user behavior after AI response)"""
        interaction = self._find_interaction(interaction_id)
        if not interaction:
            return False
        
        # Interpret implicit signals
        if signal_type == "recommendation_followed":
            interaction.feedback = FeedbackType.IMPLICIT_POSITIVE
            interaction.quality_score = min(1.0, interaction.quality_score + 0.2)
        elif signal_type == "recommendation_ignored":
            interaction.feedback = FeedbackType.IMPLICIT_NEGATIVE
            interaction.quality_score = max(0.0, interaction.quality_score - 0.1)
        elif signal_type == "session_continued":
            # User continued the session = response was useful
            interaction.quality_score = min(1.0, interaction.quality_score + 0.05)
        elif signal_type == "property_viewed":
            # User viewed property from search results
            interaction.quality_score = min(1.0, interaction.quality_score + 0.15)
        
        interaction.metadata["implicit_signals"] = interaction.metadata.get("implicit_signals", [])
        interaction.metadata["implicit_signals"].append({
            "type": signal_type,
            "data": signal_data,
            "timestamp": datetime.now().isoformat()
        })
        
        return True
    
    # ===========================================
    # Quality Scoring
    # ===========================================
    
    def _compute_initial_quality(self, interaction: Interaction) -> float:
        """Compute initial quality score based on response characteristics"""
        score = 0.5  # Base score
        
        response = interaction.ai_response
        
        # Length appropriateness
        word_count = len(response.split())
        if 50 <= word_count <= 500:
            score += 0.1
        elif word_count < 20 or word_count > 1000:
            score -= 0.1
        
        # Contains specific data (numbers, prices)
        if any(c.isdigit() for c in response):
            score += 0.1
        
        # Contains structure (bullet points, sections)
        if any(marker in response for marker in ['•', '-', '1.', '2.', '###']):
            score += 0.05
        
        # Low latency bonus
        if interaction.latency_ms < 1000:
            score += 0.1
        elif interaction.latency_ms > 5000:
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _compute_quality_with_feedback(self, interaction: Interaction) -> float:
        """Recompute quality score incorporating feedback"""
        base_score = interaction.quality_score
        
        if interaction.feedback == FeedbackType.THUMBS_UP:
            return min(1.0, base_score + 0.3)
        elif interaction.feedback == FeedbackType.THUMBS_DOWN:
            return max(0.0, base_score - 0.4)
        elif interaction.feedback == FeedbackType.RATING and interaction.feedback_score:
            # Normalize rating to 0-1 scale
            return (interaction.feedback_score / 5.0) * 0.6 + base_score * 0.4
        elif interaction.feedback == FeedbackType.CORRECTION:
            return 0.2  # Low score, but correction is valuable
        elif interaction.feedback == FeedbackType.IMPLICIT_POSITIVE:
            return min(1.0, base_score + 0.2)
        elif interaction.feedback == FeedbackType.IMPLICIT_NEGATIVE:
            return max(0.0, base_score - 0.15)
        
        return base_score
    
    # ===========================================
    # Training Data Generation
    # ===========================================
    
    async def _maybe_generate_training_data(self, interaction: Interaction):
        """Check if interaction qualifies as training data"""
        if interaction.quality_score >= self.config.min_quality_for_training:
            # Will be added to training set after feedback window
            pass  # Handled in periodic processing
    
    async def _create_training_example_from_correction(self, interaction: Interaction):
        """Create training example from user correction"""
        if not interaction.correction_text:
            return
        
        from backend.services.llm.auto_tuning import TrainingExample, TuningTask
        
        # Map interaction type to tuning task
        task_map = {
            InteractionType.VALUATION: TuningTask.PROPERTY_VALUATION,
            InteractionType.MARKET_ANALYSIS: TuningTask.MARKET_ANALYSIS,
            InteractionType.INVESTMENT_ADVICE: TuningTask.INVESTMENT_ADVICE,
            InteractionType.CHAT: TuningTask.NARRATIVE_GENERATION
        }
        
        task = task_map.get(interaction.interaction_type, TuningTask.PROPERTY_VALUATION)
        
        example = TrainingExample(
            id=f"correction_{interaction.id}",
            task=task,
            input_text=interaction.user_input,
            output_text=interaction.correction_text,  # Use corrected response
            quality_score=1.0,  # Human corrections are highest quality
            metadata={
                "source": "user_correction",
                "original_response": interaction.ai_response,
                "interaction_id": interaction.id
            }
        )
        
        # Save to training file
        self._save_training_example(example)
        self.metrics["training_examples_generated"] += 1
    
    async def generate_training_batch(self) -> int:
        """Generate training data from high-quality interactions"""
        from backend.services.llm.auto_tuning import TrainingExample, TuningTask
        
        # Get interactions with feedback that meet quality threshold
        qualified = [
            i for i in self.interactions
            if i.quality_score >= self.config.min_quality_for_training
            and i.feedback is not None
            and not i.used_for_training
        ]
        
        count = 0
        for interaction in qualified:
            task_map = {
                InteractionType.VALUATION: TuningTask.PROPERTY_VALUATION,
                InteractionType.MARKET_ANALYSIS: TuningTask.MARKET_ANALYSIS,
                InteractionType.INVESTMENT_ADVICE: TuningTask.INVESTMENT_ADVICE,
            }
            
            task = task_map.get(interaction.interaction_type, TuningTask.PROPERTY_VALUATION)
            
            example = TrainingExample(
                id=f"auto_{interaction.id}",
                task=task,
                input_text=interaction.user_input,
                output_text=interaction.ai_response,
                quality_score=interaction.quality_score,
                metadata={"source": "auto_generated", "feedback": interaction.feedback.value}
            )
            
            self._save_training_example(example)
            interaction.used_for_training = True
            count += 1
        
        self.metrics["training_examples_generated"] += count
        logger.info(f"Generated {count} training examples from interactions")
        return count
    
    def _save_training_example(self, example):
        """Save training example to file"""
        filepath = self.data_dir / f"training_auto_{datetime.now().strftime('%Y%m')}.jsonl"
        
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(example), ensure_ascii=False) + '\n')
    
    # ===========================================
    # Model Performance & Drift Detection
    # ===========================================
    
    def _update_model_stats(self, model_id: str, latency_ms: float):
        """Update running statistics for a model"""
        if model_id not in self._model_stats:
            self._model_stats[model_id] = {
                "total": 0,
                "latencies": [],
                "positive": 0,
                "negative": 0
            }
        
        stats = self._model_stats[model_id]
        stats["total"] += 1
        stats["latencies"].append(latency_ms)
        
        # Keep only recent latencies
        if len(stats["latencies"]) > 1000:
            stats["latencies"] = stats["latencies"][-500:]
    
    def get_model_performance(self, model_id: str = None) -> Dict[str, Any]:
        """Get current model performance metrics"""
        if model_id:
            models = [model_id]
        else:
            models = list(self._model_stats.keys())
        
        results = {}
        for mid in models:
            stats = self._model_stats.get(mid, {})
            if not stats:
                continue
            
            # Get recent interactions for this model
            recent = [
                i for i in self.interactions
                if i.model_used == mid
                and datetime.fromisoformat(i.timestamp) > datetime.now() - timedelta(days=7)
            ]
            
            positive = sum(1 for i in recent if i.feedback in [FeedbackType.THUMBS_UP, FeedbackType.IMPLICIT_POSITIVE])
            negative = sum(1 for i in recent if i.feedback in [FeedbackType.THUMBS_DOWN, FeedbackType.IMPLICIT_NEGATIVE])
            total_with_feedback = positive + negative
            
            results[mid] = {
                "total_interactions": stats.get("total", 0),
                "avg_latency_ms": sum(stats.get("latencies", [0])) / max(1, len(stats.get("latencies", [1]))),
                "satisfaction_rate": positive / max(1, total_with_feedback),
                "avg_quality_score": sum(i.quality_score for i in recent) / max(1, len(recent)),
                "positive_feedback": positive,
                "negative_feedback": negative
            }
        
        return results
    
    def detect_drift(self) -> List[Dict[str, Any]]:
        """Detect performance drift in models"""
        alerts = []
        window = timedelta(days=self.config.drift_detection_window_days)
        
        for model_id in self._model_stats.keys():
            # Compare recent vs historical performance
            recent = [
                i for i in self.interactions
                if i.model_used == model_id
                and datetime.fromisoformat(i.timestamp) > datetime.now() - window
            ]
            
            historical = [
                i for i in self.interactions
                if i.model_used == model_id
                and datetime.now() - timedelta(days=30) < datetime.fromisoformat(i.timestamp) <= datetime.now() - window
            ]
            
            if len(recent) < 50 or len(historical) < 50:
                continue
            
            recent_quality = sum(i.quality_score for i in recent) / len(recent)
            historical_quality = sum(i.quality_score for i in historical) / len(historical)
            
            drift = (historical_quality - recent_quality) / max(0.01, historical_quality)
            
            if drift > self.config.drift_threshold:
                alert = {
                    "model_id": model_id,
                    "drift_percentage": round(drift * 100, 2),
                    "recent_quality": round(recent_quality, 3),
                    "historical_quality": round(historical_quality, 3),
                    "recommendation": "Consider retraining or switching models",
                    "timestamp": datetime.now().isoformat()
                }
                alerts.append(alert)
                self.metrics["drift_alerts"] += 1
        
        return alerts
    
    # ===========================================
    # A/B Testing
    # ===========================================
    
    def create_experiment(
        self,
        name: str,
        control_model: str,
        challenger_model: str,
        traffic_split: float = 0.1
    ) -> str:
        """Create A/B test experiment"""
        experiment_id = hashlib.md5(f"{name}{datetime.now()}".encode()).hexdigest()[:8]
        
        self.active_experiments[experiment_id] = {
            "name": name,
            "control": control_model,
            "challenger": challenger_model,
            "traffic_split": traffic_split,
            "started_at": datetime.now().isoformat(),
            "control_interactions": 0,
            "challenger_interactions": 0,
            "control_quality_sum": 0.0,
            "challenger_quality_sum": 0.0,
            "status": "active"
        }
        
        logger.info(f"Created experiment {experiment_id}: {control_model} vs {challenger_model}")
        return experiment_id
    
    def get_experiment_model(self, experiment_id: str) -> str:
        """Get model for this request based on experiment"""
        exp = self.active_experiments.get(experiment_id)
        if not exp or exp["status"] != "active":
            return None
        
        # Random assignment based on traffic split
        if random.random() < exp["traffic_split"]:
            return exp["challenger"]
        return exp["control"]
    
    def record_experiment_result(
        self,
        experiment_id: str,
        model_used: str,
        quality_score: float
    ):
        """Record result for experiment"""
        exp = self.active_experiments.get(experiment_id)
        if not exp:
            return
        
        if model_used == exp["control"]:
            exp["control_interactions"] += 1
            exp["control_quality_sum"] += quality_score
        else:
            exp["challenger_interactions"] += 1
            exp["challenger_quality_sum"] += quality_score
    
    def get_experiment_results(self, experiment_id: str) -> Dict[str, Any]:
        """Get experiment results"""
        exp = self.active_experiments.get(experiment_id)
        if not exp:
            return {}
        
        control_avg = exp["control_quality_sum"] / max(1, exp["control_interactions"])
        challenger_avg = exp["challenger_quality_sum"] / max(1, exp["challenger_interactions"])
        
        improvement = (challenger_avg - control_avg) / max(0.01, control_avg) * 100
        
        return {
            "experiment_id": experiment_id,
            "name": exp["name"],
            "control_model": exp["control"],
            "challenger_model": exp["challenger"],
            "control_interactions": exp["control_interactions"],
            "challenger_interactions": exp["challenger_interactions"],
            "control_avg_quality": round(control_avg, 3),
            "challenger_avg_quality": round(challenger_avg, 3),
            "improvement_pct": round(improvement, 2),
            "winner": exp["challenger"] if improvement > 5 else exp["control"] if improvement < -5 else "inconclusive",
            "status": exp["status"]
        }
    
    # ===========================================
    # Utilities
    # ===========================================
    
    def _find_interaction(self, interaction_id: str) -> Optional[Interaction]:
        """Find interaction by ID"""
        for i in self.interactions:
            if i.id == interaction_id:
                return i
        return None
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get overall learning system statistics"""
        return {
            **self.metrics,
            "total_models": len(self._model_stats),
            "active_experiments": len([e for e in self.active_experiments.values() if e["status"] == "active"]),
            "pending_training_examples": len([
                i for i in self.interactions
                if i.quality_score >= self.config.min_quality_for_training
                and not i.used_for_training
            ]),
            "config": asdict(self.config)
        }
    
    def should_trigger_retraining(self) -> Tuple[bool, str]:
        """Check if retraining should be triggered"""
        pending = len([
            i for i in self.interactions
            if i.quality_score >= self.config.min_quality_for_training
            and not i.used_for_training
        ])
        
        if pending >= self.config.auto_retrain_threshold:
            return True, f"Threshold reached: {pending} examples ready"
        
        drift_alerts = self.detect_drift()
        if drift_alerts:
            return True, f"Drift detected in {len(drift_alerts)} models"
        
        return False, "No retraining needed"


# ===========================================
# Singleton Instance
# ===========================================

learning_engine = SelfLearningEngine()
