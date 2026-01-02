"""
Auto-Tuning Pipeline for Fine-tuned LLM Models
Teacher-Student Architecture for Continuous Model Improvement

Architecture:
- Teacher Model: GPT-4/Claude (high quality, expensive)
- Student Models: Qwen3-VL-32B, Qwen3-72B, Qwen3-Next-80B (fine-tuned, local)
- Pipeline: Teacher generates training data → Student models learn → Evaluation → Deploy
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class TuningTask(str, Enum):
    """Fine-tuning task categories"""
    PROPERTY_VALUATION = "property_valuation"
    MARKET_ANALYSIS = "market_analysis"
    INVESTMENT_ADVICE = "investment_advice"
    IMAGE_ANALYSIS = "image_analysis"
    LOCATION_INTELLIGENCE = "location_intelligence"
    RISK_ASSESSMENT = "risk_assessment"
    NARRATIVE_GENERATION = "narrative_generation"


@dataclass
class TrainingExample:
    """Single training example for fine-tuning"""
    id: str
    task: TuningTask
    input_text: str
    output_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 1.0
    teacher_model: str = "gpt-4"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TuningConfig:
    """Configuration for model fine-tuning"""
    student_model: str
    teacher_model: str = "teacher-gpt4"
    task: TuningTask = TuningTask.PROPERTY_VALUATION
    num_examples: int = 1000
    learning_rate: float = 2e-5
    epochs: int = 3
    batch_size: int = 4
    max_length: int = 2048
    lora_rank: int = 16
    lora_alpha: int = 32
    output_dir: str = "data/models/fine_tuned"


class AutoTuningPipeline:
    """
    Automated fine-tuning pipeline using teacher-student architecture.
    
    Workflow:
    1. Collect real user interactions
    2. Teacher model generates high-quality responses
    3. Create training dataset
    4. Fine-tune student model with LoRA
    5. Evaluate and deploy
    """
    
    def __init__(self, config: TuningConfig):
        self.config = config
        self.training_data: List[TrainingExample] = []
        self.data_dir = Path("data/training")
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    # ===========================================
    # Task-specific Prompt Templates
    # ===========================================
    
    TASK_PROMPTS = {
        TuningTask.PROPERTY_VALUATION: """You are an expert Indian real estate valuation AI. Given property details, provide:
1. Estimated market value with confidence range
2. Price per sqft analysis
3. Comparable property references
4. Key value drivers and detractors
5. Investment recommendation

Be precise, data-driven, and consider local market factors.""",

        TuningTask.MARKET_ANALYSIS: """You are an expert real estate market analyst for Indian cities. Analyze:
1. Current market trends and momentum
2. Price movement patterns (1M, 3M, 6M, 12M)
3. Supply-demand dynamics
4. Growth phase classification
5. Future outlook with confidence levels

Use specific data points and locality comparisons.""",

        TuningTask.INVESTMENT_ADVICE: """You are a real estate investment advisor specializing in Indian property markets. Provide:
1. Investment grade assessment (A+ to C)
2. Risk-return analysis
3. Rental yield projections
4. Capital appreciation potential
5. Portfolio fit recommendations

Consider investor profile, market timing, and location fundamentals.""",

        TuningTask.IMAGE_ANALYSIS: """You are an expert at analyzing property images for real estate assessment. Analyze:
1. Property condition and quality
2. Finishing and fixtures grade
3. Space utilization efficiency
4. Natural lighting assessment
5. Maintenance requirements
6. Estimated renovation costs if needed

Be specific about visible features and their impact on value.""",

        TuningTask.LOCATION_INTELLIGENCE: """You are a location intelligence expert for Indian real estate. Analyze:
1. Connectivity (metro, roads, airport)
2. Social infrastructure (schools, hospitals, shopping)
3. Employment hubs proximity
4. Future development projects
5. Livability score factors

Provide specific distances and impact on property values.""",

        TuningTask.RISK_ASSESSMENT: """You are a real estate risk analyst. Assess:
1. Market risk (price volatility, liquidity)
2. Location risk (flooding, infrastructure)
3. Regulatory risk (approvals, compliance)
4. Developer risk (track record, financials)
5. Overall risk score with breakdown

Be quantitative where possible with risk percentages.""",

        TuningTask.NARRATIVE_GENERATION: """You are a real estate content expert. Generate:
1. Compelling property descriptions
2. Neighborhood narratives
3. Investment thesis summaries
4. Market outlook reports
5. Buyer/investor recommendations

Use engaging language while maintaining accuracy."""
    }
    
    # ===========================================
    # Training Data Generation
    # ===========================================
    
    async def generate_training_example(
        self,
        user_input: str,
        task: TuningTask,
        context: Optional[Dict[str, Any]] = None
    ) -> TrainingExample:
        """Generate a single training example using teacher model"""
        from backend.services.llm.llm_provider import llm_service
        
        system_prompt = self.TASK_PROMPTS.get(task, self.TASK_PROMPTS[TuningTask.PROPERTY_VALUATION])
        
        # Add context if provided
        if context:
            system_prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        response = await llm_service.chat(
            messages=messages,
            model=self.config.teacher_model,
            temperature=0.3  # Low temp for consistent training data
        )
        
        example = TrainingExample(
            id=f"train_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.training_data)}",
            task=task,
            input_text=user_input,
            output_text=response.content,
            metadata={
                "context": context,
                "teacher_response_time_ms": response.latency_ms,
                "teacher_cost_usd": response.cost_usd
            },
            teacher_model=self.config.teacher_model
        )
        
        self.training_data.append(example)
        return example
    
    async def generate_batch_training_data(
        self,
        examples: List[Dict[str, Any]],
        task: TuningTask
    ) -> List[TrainingExample]:
        """Generate training data in batch"""
        results = []
        for ex in examples:
            try:
                result = await self.generate_training_example(
                    user_input=ex["input"],
                    task=task,
                    context=ex.get("context")
                )
                results.append(result)
                logger.info(f"Generated training example: {result.id}")
            except Exception as e:
                logger.error(f"Failed to generate example: {e}")
        return results
    
    # ===========================================
    # Dataset Management
    # ===========================================
    
    def save_training_data(self, filename: str = None) -> str:
        """Save training data to JSONL file"""
        if not filename:
            filename = f"training_{self.config.student_model}_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        filepath = self.data_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for example in self.training_data:
                # Convert to chat format for fine-tuning
                chat_format = {
                    "messages": [
                        {"role": "system", "content": self.TASK_PROMPTS.get(example.task, "")},
                        {"role": "user", "content": example.input_text},
                        {"role": "assistant", "content": example.output_text}
                    ],
                    "metadata": {
                        "id": example.id,
                        "task": example.task.value,
                        "quality_score": example.quality_score
                    }
                }
                f.write(json.dumps(chat_format, ensure_ascii=False) + '\n')
        
        logger.info(f"Saved {len(self.training_data)} examples to {filepath}")
        return str(filepath)
    
    def load_training_data(self, filepath: str) -> int:
        """Load training data from JSONL file"""
        loaded = 0
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                messages = data["messages"]
                metadata = data.get("metadata", {})
                
                example = TrainingExample(
                    id=metadata.get("id", f"loaded_{loaded}"),
                    task=TuningTask(metadata.get("task", "property_valuation")),
                    input_text=messages[1]["content"],  # user message
                    output_text=messages[2]["content"],  # assistant message
                    quality_score=metadata.get("quality_score", 1.0)
                )
                self.training_data.append(example)
                loaded += 1
        
        logger.info(f"Loaded {loaded} examples from {filepath}")
        return loaded
    
    # ===========================================
    # Fine-tuning Commands (for external execution)
    # ===========================================
    
    def generate_finetune_script(self) -> str:
        """Generate fine-tuning script for the student model"""
        script = f'''#!/bin/bash
# Auto-generated fine-tuning script for {self.config.student_model}
# Generated at: {datetime.now().isoformat()}

# Activate environment
source venv/bin/activate

# Install dependencies if needed
pip install transformers peft accelerate bitsandbytes

# Run fine-tuning with LoRA
python -m transformers.trainer \\
    --model_name_or_path {self.config.student_model} \\
    --train_file data/training/training_{self.config.student_model}*.jsonl \\
    --output_dir {self.config.output_dir}/{self.config.student_model} \\
    --num_train_epochs {self.config.epochs} \\
    --per_device_train_batch_size {self.config.batch_size} \\
    --learning_rate {self.config.learning_rate} \\
    --max_seq_length {self.config.max_length} \\
    --lora_r {self.config.lora_rank} \\
    --lora_alpha {self.config.lora_alpha} \\
    --lora_dropout 0.05 \\
    --fp16 True \\
    --gradient_checkpointing True \\
    --save_strategy "epoch" \\
    --logging_steps 10

echo "Fine-tuning complete! Model saved to {self.config.output_dir}/{self.config.student_model}"
'''
        return script
    
    def generate_vllm_serve_command(self) -> str:
        """Generate vLLM serving command for fine-tuned model"""
        return f'''# Serve fine-tuned model with vLLM
python -m vllm.entrypoints.openai.api_server \\
    --model {self.config.output_dir}/{self.config.student_model} \\
    --port 8080 \\
    --tensor-parallel-size 2 \\
    --gpu-memory-utilization 0.9 \\
    --max-model-len {self.config.max_length}
'''
    
    # ===========================================
    # Evaluation
    # ===========================================
    
    async def evaluate_student_model(
        self,
        test_examples: List[Dict[str, Any]],
        task: TuningTask
    ) -> Dict[str, Any]:
        """Evaluate student model against teacher"""
        from backend.services.llm.llm_provider import llm_service, LLMProvider
        
        results = {
            "total": len(test_examples),
            "scores": [],
            "avg_latency_teacher_ms": 0,
            "avg_latency_student_ms": 0,
            "cost_savings_pct": 0
        }
        
        teacher_latencies = []
        student_latencies = []
        teacher_costs = []
        
        for example in test_examples:
            # Get teacher response
            llm_service.switch_provider(LLMProvider.OPENROUTER)
            teacher_resp = await llm_service.chat(
                [{"role": "user", "content": example["input"]}],
                model=self.config.teacher_model
            )
            teacher_latencies.append(teacher_resp.latency_ms)
            teacher_costs.append(teacher_resp.cost_usd)
            
            # Get student response
            llm_service.switch_provider(LLMProvider.QWEN_LOCAL)
            student_resp = await llm_service.chat(
                [{"role": "user", "content": example["input"]}],
                model=self.config.student_model
            )
            student_latencies.append(student_resp.latency_ms)
            
            # Simple similarity score (in production, use proper evaluation)
            score = self._compute_similarity(teacher_resp.content, student_resp.content)
            results["scores"].append(score)
        
        results["avg_latency_teacher_ms"] = sum(teacher_latencies) / len(teacher_latencies)
        results["avg_latency_student_ms"] = sum(student_latencies) / len(student_latencies)
        results["avg_score"] = sum(results["scores"]) / len(results["scores"])
        results["total_teacher_cost"] = sum(teacher_costs)
        results["cost_savings_pct"] = 100  # Local models = 100% API cost savings
        
        return results
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Simple similarity score (placeholder for proper evaluation)"""
        # In production, use: ROUGE, BERTScore, or custom metrics
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union) if union else 0.0


# ===========================================
# Sample Training Data Templates
# ===========================================

SAMPLE_TRAINING_INPUTS = {
    TuningTask.PROPERTY_VALUATION: [
        "What is the estimated value of a 3BHK apartment in Whitefield, Bangalore with 1500 sqft built-up area?",
        "Value this property: 2BHK flat in Koramangala, 1200 sqft, 5th floor, 10 years old, semi-furnished.",
        "Estimate the price for a villa in Sarjapur with 2400 sqft and 3000 sqft plot.",
    ],
    TuningTask.MARKET_ANALYSIS: [
        "What is the current market trend in HSR Layout, Bangalore?",
        "Analyze the real estate market in Electronic City for the past 6 months.",
        "Compare the market performance of Whitefield vs Sarjapur Road.",
    ],
    TuningTask.INVESTMENT_ADVICE: [
        "Should I invest in a 2BHK apartment in Bellandur for rental income?",
        "Is Devanahalli a good location for long-term investment?",
        "Compare investment potential: Koramangala vs Indiranagar for a budget of 1.5Cr.",
    ]
}


# ===========================================
# Convenience Functions
# ===========================================

def create_tuning_pipeline(
    student_model: str = "qwen3-72b",
    task: TuningTask = TuningTask.PROPERTY_VALUATION
) -> AutoTuningPipeline:
    """Create a tuning pipeline with default config"""
    config = TuningConfig(
        student_model=student_model,
        task=task
    )
    return AutoTuningPipeline(config)
