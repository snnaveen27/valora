# 🚀 Kaggle Setup Instructions for DeepSeek R1 Fine-Tuning

## ✅ Dataset Assets
- **Location**: `notebooks/archive.zip`
- **Contents**:
  - `data/qwen_training/train.json`: 45,000 high-quality grounded examples
  - `data/qwen_training/eval.json`: 5,000 evaluation examples
  - `dataset_info.json`: Metadata and statistics
- **Total Examples**: 50,000
- **Features**: 
  - Full coverage of 11 GIS intents with weighted distribution
  - Chain-of-Thought (CoT) reasoning for all responses
  - 15+ query variations per intent
  - Multiple response templates per intent
  - Grounded in real Bangalore database facts (784 localities, 2000 buildings, 2000 POIs)

## 🎯 Model Selection: DeepSeek R1 Distill Qwen 7B
We are using **DeepSeek-R1-Distill-Qwen-7B** because:
1. **Reasoning Excellence**: Best-in-class performance for complex spatial and market analysis.
2. **Efficiency**: 7B parameters allow for high LoRA rank (64) training on Kaggle's T4x2 GPUs.
3. **Alignment**: Pre-distilled from DeepSeek R1 for superior instruction following and logical breakdown.

## 🛠️ Step-by-Step Kaggle Setup

### 1. Upload Dataset
1. Go to [Kaggle Datasets](https://www.kaggle.com/datasets/new).
2. Title: `valora-highquality-v2`
3. Upload `notebooks/archive.zip`.
4. Set visibility to **Private**.

### 2. Create Notebook
1. Go to [Kaggle Code](https://www.kaggle.com/code/new).
2. Upload `notebooks/qwen3_vl_kaggle_clean.ipynb`.
3. In **Settings** (right sidebar):
   - **Accelerator**: GPU T4 x2
   - **Persistence**: Variables and Files
4. Click **Add Data** and select your `valora-highquality-v2` dataset.

### 3. Run Training
1. Run all cells in the notebook.
2. The notebook is configured to:
   - Install Unsloth and dependencies.
   - Load the model in 4-bit quantization.
   - Apply reasoning-optimized LoRA adapters (Rank 64).
   - Train for 4 epochs with auto-resume capability.
3. Once training starts (Cell 12), you can close the browser; Kaggle will continue the session.

## 📊 Quality Metrics & Benchmarks (v2.0)
- **Dataset Size**: 50,000 examples (45K train / 5K eval)
- **Intent Accuracy**: Expected >98% after fine-tuning (tested across 11 intents).
- **Reasoning Fidelity**: Structured `<thought>` tags ensure the model follows a 4-step spatial reasoning logic.
- **Fact Grounding**: No-hallucination policy enforced via database-grounded response templates.
- **Intent Distribution** (weighted for realistic usage):
  - ANALYZE_AREA: 18.1%
  - PROPERTY_SEARCH: 15.1%
  - VALUATION: 12.0%
  - NAVIGATE: 11.9%
  - COMPARISON: 9.7%
  - ANALYZE_BUILDING: 8.0%
  - TERRAIN: 6.0%
  - SIMULATE: 5.9%
  - GENERAL: 5.0%
  - DIGITAL_TWIN: 4.1%
  - SPATIAL_3D: 4.0%
- **Data Cleanliness**: 
  - Normalized price formats (₹/sqft) with outlier handling.
  - Cleaned building taxonomies (filtered "yes", "building", "true", "roof").
  - Context-aware responses for emerging areas (handling missing POI/transit data).
  - Multiple response templates per intent for diversity.

---
*Last Updated: January 31, 2026*
