"""
Valora AI — Fine-Tuning Dataset Generator v2
Aligned with production pipeline:
  - Chat format (system/user/assistant) matching /api/chat
  - Facts in to_context_string() format
  - Condensed training system prompt + intent instructions
  - All production fields included
"""

import json
import random
from pathlib import Path
from datetime import datetime

from _ft_data_helpers import (
    LOCALITIES, make_example, INTENT_INSTRUCTIONS
)

# =============================================================================
# CONFIG
# =============================================================================

OUTPUT_DIR = Path(__file__).parent.parent / "notebooks" / "fine_tuning_dataset"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
EVAL_RATIO = 0.1  # 10% for evaluation

# Intent distribution (total ~3600 examples)
INTENT_DISTRIBUTION = {
    "analyze_area":     500,
    "property_search":  500,
    "comparison":       350,
    "investment":       350,
    "simulate":         300,
    "valuation":        300,
    "navigate":         250,
    "analyze_building": 250,
    "market_trend":     250,
    "terrain":          200,
    "recommendation":   150,
    "general":          100,
    "conversational":   100,
}


def generate_dataset():
    random.seed(SEED)
    
    all_examples = []
    intent_counts = {}
    
    for intent, count in INTENT_DISTRIBUTION.items():
        print(f"  Generating {count:>4} examples for {intent}...")
        intent_examples = []
        for _ in range(count):
            try:
                ex = make_example(intent)
                intent_examples.append(ex)
            except Exception as e:
                print(f"    ERROR generating {intent}: {e}")
                continue
        
        all_examples.extend(intent_examples)
        intent_counts[intent] = len(intent_examples)
    
    # Shuffle
    random.shuffle(all_examples)
    
    # Split train/eval
    n_eval = max(1, int(len(all_examples) * EVAL_RATIO))
    eval_set = all_examples[:n_eval]
    train_set = all_examples[n_eval:]
    
    # Write files
    train_path = OUTPUT_DIR / "train.json"
    eval_path = OUTPUT_DIR / "eval.json"
    info_path = OUTPUT_DIR / "dataset_info.json"
    
    with open(train_path, "w", encoding="utf-8") as f:
        json.dump(train_set, f, indent=2, ensure_ascii=False)
    
    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(eval_set, f, indent=2, ensure_ascii=False)
    
    total = len(all_examples)
    info = {
        "name": "valora-qwen3-4b-v2.0",
        "version": "2.0.0",
        "created": datetime.now().isoformat(),
        "model_target": "Qwen3-4B-Instruct",
        "total_examples": total,
        "train_examples": len(train_set),
        "eval_examples": len(eval_set),
        "intents": list(INTENT_DISTRIBUTION.keys()),
        "distribution": intent_counts,
        "features": [
            "grounded_facts_production_format",
            "think_tags",
            "bangalore_only",
            "intent_specific_prompts",
            "indian_formatting",
            "chat_format_api_chat",
            "to_context_string_aligned",
            "all_production_fields",
        ],
        "source_localities": len(LOCALITIES),
        "alignment": {
            "facts_format": "AgentFacts.to_context_string()",
            "system_prompt": "condensed SYSTEM_CONSTITUTION + intent instruction",
            "llm_call": "/api/chat with messages array",
            "response_format": "<think> reasoning + structured response",
        },
    }
    
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "=" * 60)
    print("  DATASET GENERATED — v2.0 (Production-Aligned)")
    print("=" * 60)
    print(f"  Total:    {total}")
    print(f"  Train:    {len(train_set)}")
    print(f"  Eval:     {len(eval_set)}")
    print(f"  Intents:  {len(intent_counts)}")
    print(f"  Localities: {len(LOCALITIES)}")
    print()
    for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
        print(f"    {intent:<20} {count:>4}")
    print()
    print(f"  Train: {train_path}")
    print(f"  Eval:  {eval_path}")
    print(f"  Info:  {info_path}")
    print("=" * 60)
    
    # Validate a sample
    print("\n  SAMPLE VALIDATION:")
    sample = random.choice(train_set)
    msgs = sample["messages"]
    sys_len = len(msgs[0]["content"])
    usr_len = len(msgs[1]["content"])
    ast_len = len(msgs[2]["content"])
    has_facts = "**GROUNDED FACTS" in msgs[0]["content"]
    has_think = "<think>" in msgs[2]["content"] or msgs[2]["content"].startswith("Hello") or msgs[2]["content"].startswith("I can help") or msgs[2]["content"].startswith("You're") or msgs[2]["content"].startswith("Good") or msgs[2]["content"].startswith("Glad")
    has_bold = "**" in msgs[0]["content"]
    has_indent = "  - " in msgs[0]["content"]
    print(f"    System: {sys_len} chars | User: {usr_len} chars | Assistant: {ast_len} chars")
    print(f"    Has GROUNDED FACTS header: {has_facts}")
    print(f"    Has **bold** headers: {has_bold}")
    print(f"    Has '  - ' indented bullets: {has_indent}")
    print(f"    Has <think> or conversational: {has_think}")
    print(f"    Roles: {[m['role'] for m in msgs]}")


if __name__ == "__main__":
    generate_dataset()
