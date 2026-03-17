# Qwen 3.5-9B Reasoning Style Enrichment Plan

## Executive Summary

This plan outlines the transformation of the current dataset's reasoning style from terse, robotic summaries to detailed "inner monologue" style reasoning that aligns with Qwen 3.5-9B's expected Chain of Thought (CoT) output format.

---

## 1. Understanding Qwen 3.5-9B Reasoning Style

### 1.1 Key Characteristics

Based on analysis of Qwen 3.5-9B and similar reasoning models:

| Characteristic | Current Dataset | Qwen 3.5-9B Expected |
|----------------|-----------------|----------------------|
| **Length** | 1-2 sentences | 5-15 sentences with detailed steps |
| **Tone** | Robotic, action-focused | Conversational, exploratory |
| **Reasoning** | No visible chain | Explicit step-by-step chain |
| **Fact Usage** | Implied | Explicit grounding in provided facts |
| **Self-Correction** | None | May show checking/correction |
| **Spatial Reasoning** | Absent | Detailed spatial analysis |

### 1.2 Example Transformation

**Current (Robotic):**
```
</think>
Searching properties in Malleshwaram.
Market: ₹15,000/sqft, 120 active listings, HIGH demand.
</think>
```

**Expected (Qwen Style - Expanded):**
```
</think>
The user is looking for properties in Malleshwaram with specific requirements. Let me analyze what I know from the grounded facts:

1. First, I need to recall the market conditions for Malleshwaram from the provided data - it's listed at ₹15,000/sqft with 120 active listings and HIGH demand status.

2. For property search, I should consider:
   - The price per sqft compared to the area average
   - The demand level (HIGH means competitive market)
   - Available inventory in the requested configuration
   
3. Looking at the grounded facts, I see multiple properties available. Let me filter for 1BHK options and sort by price efficiency.

4. The market data shows Malleshwaram is a premium heritage residential area, so I should emphasize properties near metro (400m) and with good amenities given the high demand.
</think>
```

---

## 2. Current Dataset Analysis

### 2.1 Dataset Structure

- **train.json**: ~3,510 training examples (~9.5MB)
- **eval.json**: ~390 evaluation examples (~1MB)
- **System Prompt**: Instructs to use <think> tags but doesn't emphasize "deep thinking"
- **Intents**: 13 types (analyze_area, property_search, comparison, investment, simulate, valuation, navigate, analyze_building, market_trend, terrain, recommendation, general, conversational)

### 2.2 Reasoning Block Patterns by Intent

| Intent | Current Reasoning Pattern | Target Pattern |
|--------|-------------------------|----------------|
| property_search | "Searching properties in X" | Filter → Analyze market → Rank by criteria → Select top picks |
| terrain | "Terrain analysis for X" | Elevation analysis → Slope assessment → Flood risk evaluation → Construction recommendation |
| analyze_building | "Building analysis in X" | Sky view assessment → Shadow analysis → Optimal floor calculation → Building context |
| navigate | "Navigate to X" | Location context → Area character → Walkability/metro analysis → POI summary |
| recommendation | "User needs recommendations" | Criteria matching → Score calculation → Ranking → Recommendation |

---

## 3. Implementation Plan

### 3.1 Phase 1: System Prompt Enhancement

**Task**: Update the system prompt to explicitly encourage "Deep Thinking" behavior

**Changes Required**:
- Add "Deep Thinking" section to prompt
- Emphasize step-by-step spatial reasoning
- Instruct model to "talk through" grounded facts before answering
- Add examples of expected reasoning depth

### 3.2 Phase 2: Reasoning Templates Development

**Task**: Create detailed reasoning templates for each intent type

**Templates to Create**:
1. **Property Search Template**: Market analysis → Filter criteria → Price analysis → Ranking → Selection rationale
2. **Terrain Analysis Template**: Elevation context → Slope implications → Flood risk assessment → Construction recommendation
3. **Building Analysis Template**: Spatial model construction → View analysis → Shadow calculation → Optimal floor reasoning
4. **Navigation Template**: Location context → Area characterization → Connectivity analysis → POI synthesis
5. **Recommendation Template**: Criteria extraction → Score calculation → Alternative comparison → Final recommendation
6. **Comparison Template**: Area A analysis → Area B analysis → Comparative scoring → Trade-off discussion
7. **Investment Template**: Price analysis → Growth indicators → Risk assessment → Strategy recommendation
8. **Valuation Template**: Property analysis → Market comparison → Price justification → Confidence assessment

### 3.3 Phase 3: Dataset Transformation

**Task**: Apply reasoning enrichment to train.json and eval.json

**Approach**:
- Use LLM-assisted expansion (prompt existing <think> content to expand)
- Create transformation rules for systematic enrichment
- Validate quality through sampling

### 3.4 Phase 4: Validation

**Task**: Ensure enriched reasoning is high quality and consistent

**Validation Criteria**:
- Reasoning blocks are 3-10x longer than current
- Each step explicitly references grounded facts
- Spatial reasoning shows step-by-step analysis
- Tone is conversational, not robotic

---

## 4. Technical Implementation

### 4.1 Transformation Script Design

```python
# Pseudo-code for reasoning expansion
EXPANSION_PROMPT = """
Expand this terse reasoning into detailed "Deep Thinking" style:
- Show step-by-step spatial reasoning
- Explicitly reference grounded facts
- Talk through the problem before solution
- Use conversational, exploratory tone

Original reasoning: {original_thinking}
Grounded facts: {grounded_facts}
Intent type: {intent_type}
"""

def expand_reasoning(example):
    # Extract components
    original_thinking = example["thinking"]
    grounded_facts = extract_facts(example["context"])
    intent_type = example["intent"]
    
    # Expand using LLM
    expanded = llm.expand(original_thinking, grounded_facts, intent_type)
    
    return {"thinking": expanded, ...}
```

### 4.2 Quality Assurance

- Random sampling of 10% of enriched examples for manual review
- Automated checks for minimum length (100+ chars)
- Pattern matching for required reasoning elements
- Consistency checks across intent types

---

## 5. Expected Outcomes

### 5.1 Dataset Improvements

| Metric | Before | After |
|--------|--------|-------|
| Avg reasoning length | ~50 chars | ~400-600 chars |
| Steps shown per response | 0-1 | 4-8 |
| Fact citations | Implicit | Explicit |
| Spatial reasoning detail | None | Full analysis |

### 5.2 Model Behavior Improvements

- More detailed Chain of Thought output
- Better grounding in provided facts
- Improved spatial reasoning for GIS tasks
- More natural, conversational responses

---

## 6. Timeline Estimate

| Phase | Tasks | Effort |
|-------|-------|--------|
| Phase 1 | System prompt update | Low |
| Phase 2 | Template development | Medium |
| Phase 3 | Dataset transformation | High |
| Phase 4 | Validation | Medium |

---

## 7. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Token limit issues | Limit expanded reasoning to ~600 chars |
| Inconsistent quality | Manual review of sample + automated checks |
| Over-length training | Adjust max_seq_length in training config |
| Template rigidity | Add variety in expansion prompts |

---

## 8. Next Steps

1. **Approve this plan** → Proceed to Phase 1
2. **Request modifications** → Specify changes needed
3. **Defer implementation** → Schedule for later

---

*Created: 2026-03-09*
*For: Qwen3.5-9B Fine-Tuning Dataset v2.1*
