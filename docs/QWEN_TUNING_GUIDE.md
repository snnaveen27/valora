# Qwen Model Fine-Tuning Guide for Valora AI

## Current Setup

Valora uses **Qwen3-VL (8B)** as the default local LLM via Ollama for:
- Real estate query understanding
- Spatial reasoning narratives
- Investment analysis responses
- Property recommendations

## Database Statistics (Available for Training)

| Data Type | Records | Description |
|-----------|---------|-------------|
| Properties | 42,452 | Real estate listings with prices, amenities |
| Buildings | 686,370 | 3D building footprints with heights |
| POIs | 26,961 | Points of interest (schools, hospitals, etc.) |
| Transport | 5,384 | Metro stations, bus stops |
| Roads | 334,784 | Road network data |
| Price History | 42,362 | Historical pricing trends |
| Open Datasets | 455,066 | Government open data |
| **Total** | **1,595,382** | Records available |

---

## Prompt for Another AI to Help Tune Qwen

Copy and paste this prompt to ask another AI (like Claude, GPT-4, etc.) for help:

---

### 🔧 PROMPT TO COPY:

```
I need help fine-tuning Qwen3-VL (8B) for a real estate AI assistant called "Valora" that operates in Bangalore, India. Here are the requirements:

## Use Case
Valora is an offline-first city intelligence platform that:
1. Answers real estate queries (property search, valuation, investment analysis)
2. Performs spatial reasoning (3D analysis, view quality, sunlight exposure)
3. Generates location narratives from structured data
4. Provides investment recommendations based on market trends

## Key Behaviors Needed
1. **Grounded Responses**: The model receives factual data from deterministic agents and should ONLY narrate/synthesize these facts - never invent numbers or statistics
2. **Bangalore Context**: Understand localities (Koramangala, Indiranagar, Whitefield, HSR Layout, etc.), price ranges in Lakhs/Crores, and local real estate terminology
3. **Structured Output**: Return responses in markdown with clear sections for analysis
4. **Concise Expert Tone**: Professional real estate advisor style, not verbose

## Data Available for Training
- 42,452 property listings (price, location, amenities, bedrooms, area)
- 686,370 buildings with 3D heights
- 26,961 POIs categorized by type
- 5,384 transport stops (metro, bus)
- Historical price data for 42,362 properties

## Example Input/Output Pairs Needed

### Example 1: Investment Query
**Input Context (from agents):**
```json
{
  "location": "Whitefield",
  "avg_price_sqft": 8500,
  "price_trend_6m": "+12%",
  "metro_distance_m": 800,
  "poi_count": 45,
  "growth_stage": "maturing"
}
```
**User Query:** "Is Whitefield good for investment?"

**Expected Output:**
"**Whitefield Investment Analysis**

Based on current market data:
- **Price**: ₹8,500/sqft (12% growth in 6 months)
- **Connectivity**: 800m from metro - excellent
- **Amenities**: 45 POIs nearby

**Recommendation**: Strong buy for appreciation. The maturing growth stage indicates stable returns with lower risk than emerging areas."

### Example 2: Property Search
**Input Context:**
```json
{
  "results": [
    {"name": "Prestige Lakeside", "price": 85, "bedrooms": 3, "area": 1800},
    {"name": "Brigade Metropolis", "price": 72, "bedrooms": 3, "area": 1650}
  ],
  "budget": 90,
  "search_area": "Whitefield"
}
```
**User Query:** "3BHK apartments under 90 lakhs in Whitefield"

**Expected Output:**
"Found 2 properties matching your criteria in Whitefield:

1. **Prestige Lakeside** - ₹85L | 3 BHK | 1,800 sqft
2. **Brigade Metropolis** - ₹72L | 3 BHK | 1,650 sqft

Both are within your ₹90L budget. Prestige Lakeside offers more space at ₹4,722/sqft."

## Questions
1. What's the best fine-tuning approach for Qwen3-VL 8B? (LoRA, QLoRA, full fine-tune?)
2. How many training examples should I prepare?
3. What format should the training data be in? (ChatML, Alpaca, ShareGPT?)
4. How do I ensure the model stays grounded and doesn't hallucinate?
5. Can you generate 20 example training pairs for these use cases?
6. What hyperparameters work best for real estate domain adaptation?
7. How can I leverage the vision capabilities of Qwen3-VL for property images?
```

---

## Fine-Tuning Approaches

### Option 1: LoRA (Recommended)
- Low memory requirement
- Fast training (1-2 hours)
- Good for domain adaptation
- Works well with Qwen3-VL's multimodal architecture

```bash
# Using Unsloth for fast LoRA
pip install unsloth
```

### Option 2: QLoRA
- Even lower memory (fits on 8GB GPU)
- 4-bit quantization
- Slightly lower quality

### Option 3: Full Fine-Tune
- Highest quality
- Requires 40GB+ VRAM
- Longer training time

## Training Data Format (ChatML)

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are Valora, a real estate AI assistant for Bangalore. Only use the provided facts to answer. Never invent statistics."
    },
    {
      "role": "user", 
      "content": "[CONTEXT: {\"location\":\"Koramangala\", \"avg_price\":12000}]\n\nWhat are prices like here?"
    },
    {
      "role": "assistant",
      "content": "In Koramangala, current average prices are ₹12,000/sqft - one of the premium localities in Bangalore."
    }
  ]
}
```

## Creating Training Data from Valora Database

```python
# Extract training examples from your database
import sqlite3
import json

conn = sqlite3.connect('backend/database/valora.db')

# Get diverse property examples
properties = conn.execute('''
    SELECT locality, AVG(price), AVG(covered_area), COUNT(*)
    FROM posted_properties 
    GROUP BY locality 
    HAVING COUNT(*) > 10
''').fetchall()

# Generate training pairs
training_data = []
for locality, avg_price, avg_area, count in properties:
    training_data.append({
        "messages": [
            {"role": "system", "content": "You are Valora..."},
            {"role": "user", "content": f"Tell me about {locality}"},
            {"role": "assistant", "content": f"**{locality}** has {count} listings with avg price ₹{avg_price:,.0f}..."}
        ]
    })
```

## Ollama Modelfile for Custom Qwen3-VL

After fine-tuning, create a custom Modelfile:

```dockerfile
FROM qwen3-vl:8b

# Set system prompt
SYSTEM """You are Valora, an expert real estate AI for Bangalore, India.
You ONLY use provided factual data. Never invent statistics.
Respond in concise markdown with clear sections.
You can analyze property images when provided."""

# Tune parameters
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_ctx 8192
```

Then: `ollama create valora-qwen3-vl -f Modelfile`

## Recommended Training Scale

| Dataset Size | Training Time | Quality |
|-------------|---------------|---------|
| 100 examples | 30 min | Basic |
| 500 examples | 2 hours | Good |
| 2000 examples | 6 hours | Excellent |
| 5000+ examples | 12+ hours | Production-ready |

## Evaluation Metrics

1. **Grounding Score**: Does response only use provided facts?
2. **Format Compliance**: Proper markdown structure?
3. **Domain Accuracy**: Correct Bangalore terminology?
4. **Conciseness**: No verbose preambles?

---

## Quick Start

1. Ensure Ollama is running with Qwen3-VL:
   ```bash
   ollama pull qwen3-vl:8b
   ollama run qwen3-vl:8b
   ```

2. Valora is configured to use Qwen3-VL by default at:
   - URL: `http://127.0.0.1:11434/v1/chat/completions`
   - Model: `qwen3-vl:8b`

3. Test the setup:
   ```bash
   curl http://localhost:8000/api/admin/llm-config
   ```

## Vision Capabilities (Qwen3-VL)

Qwen3-VL can analyze property images for:
- Building condition assessment
- Interior quality evaluation
- Amenity verification
- Neighborhood visual analysis

Example usage:
```python
# Send image with query
response = llm_client.chat(
    model="qwen3-vl:8b",
    messages=[
        {"role": "user", "content": "Analyze this property image", "images": ["property.jpg"]}
    ]
)
```

## Contact

For questions about fine-tuning Valora's Qwen model, refer to:
- [Unsloth Documentation](https://github.com/unslothai/unsloth)
- [Qwen Fine-tuning Guide](https://qwen.readthedocs.io/)
- [Ollama Custom Models](https://ollama.ai/blog/how-to-prompt-code-llama)
