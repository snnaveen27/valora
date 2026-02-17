# Valora AI - Complete Implementation Plan v3.0

**Version:** 3.0  
**Date:** February 16, 2026  
**Status:** Ready for Implementation

---

## Executive Summary

Valora AI is a **planner-first cognitive system** with:
- Multi-step reasoning orchestration
- Iterative agent execution
- Tool-centric micro-reasoning architecture
- Tiered learning and cognitive workflow engine

---

## 1. Core System Architecture

```
USER → detect user profile
    ↓
SPECIALIST MODE (dynamic)
├── Planner
├── Investor
├── GIS Analyst
├── Building Analyst
└── Navigator
    ↓
ADAPTIVE REASONING LAYER
├── Adaptive Temporal Context (WHEN things change)
├── Spatial Relationship Reasoning (HIGH IMPACT)
├── Micro-Context Awareness (VERY powerful)
├── Confidence Calibration Logic
├── Conflict Resolution Training (ADVANCED)
├── Temporal Phase Awareness
├── Reasoning Modes
├── Spatial Graph Thinking
├── Data Freshness Awareness
└── Unknown Handling
    ↓
GROUNDED FACTS (Truth Firewall)
├── 1.6M+ deterministic records
└── GIS Agents
    ↓
ANALYSIS PANEL (Smart Tabs)
```

---

## 2. Smart Tab System (Analysis Panel)

### 2.1 Tab Structure

| # | Tab | Purpose | Answers |
|---|-----|---------|---------|
| 1 | **Decision Verdict** | BUY/HOLD/AVOID + reasoning | "What should I do?" |
| 2 | **Market Snapshot** | Price trends, demand/supply | "Is market strong?" |
| 3 | **Spatial Intelligence** | Infrastructure, connectivity | "Why does location matter?" |
| 4 | **Risk Analysis** | Flood, legal, oversupply risks | "What could go wrong?" |
| 5 | **ROI Projection** | 3-year scenarios | "What returns can I expect?" |
| 6 | **Comparable Properties** | Similar listings | "Is this fairly priced?" |
| 7 | **Strategy & Recommendations** | Entry/exit strategy | "How should I proceed?" |
| 8 | **Data Transparency** | Truth Firewall verification | "Can I trust this data?" |
| 9 | **Client Pitch** | Broker presentation | "How do I present this?" |

### 2.2 Decision Verdict Tab (First Tab - Most Important)

```jsx
// Tab 1: Decision Verdict
{
  verdict: "BUY" | "HOLD" | "AVOID",
  confidence_score: 85,  // 0-100%
  risk_level: "MODERATE",
  time_horizon: "3-5 years",
  
  sections: {
    top_reasons: [
      "Strong infrastructure growth",
      "Below market price by 12%",
      "High rental yield potential"
    ],
    key_risks: [
      "Metro Phase 2 delay possible",
      "Slightly elevated flood zone"
    ],
    strategy_recommendation: {
      entry_price: "₹8,500-9,000/sqft",
      hold_duration: "5-7 years",
      exit_strategy: "Sell when metro completes"
    }
  }
}
```

### 2.3 Market Snapshot Tab

```jsx
// Tab 2: Market Snapshot
{
  avg_price_sqft: 8500,
  price_trend: {
    "1Y": "+8%",
    "3Y": "+24%"
  },
  demand_supply: "HIGH DEMAND",
  rental_yield: "3.8%",
  liquidity_score: 72,  // How fast properties sell
  
  visuals: ["line_chart", "trend_indicators"]
}
```

### 2.4 Spatial Intelligence Tab

```jsx
// Tab 3: Spatial Intelligence
{
  nearby_infrastructure: [
    { name: "Metro Station", distance: "0.8km", status: "operational" },
    { name: "Tech Park", distance: "2.1km", status: "operational" }
  ],
  connectivity: {
    metro: true,
    highway: true,
    airport_distance: "35km"
  },
  pois: {
    schools: 5,
    hospitals: 3,
    malls: 2,
    offices: 12
  },
  walkability_score: 78,
  development_hotspots: ["Sarjapur Road extension", "Metro Phase 2"]
}
```

### 2.5 Risk Analysis Tab

```jsx
// Tab 4: Risk Analysis
{
  overall_risk_score: 35,  // 0-100 (lower = safer)
  
  risks: {
    flood: { level: "LOW", score: 15 },
    environmental: { level: "MODERATE", score: 40 },
    oversupply: { level: "LOW", score: 20 },
    legal: { level: "LOW", score: 10 },
    infrastructure_delay: { level: "MODERATE", score: 45 }
  },
  
  mitigation_suggestions: [
    "Check RERA compliance",
    "Verify flood zone classification"
  ]
}
```

### 2.6 ROI Projection Tab

```jsx
// Tab 5: ROI Projection
{
  projection_3year: {
    best_case: { price: 11500, return: "+35%" },
    expected: { price: 10200, return: "+20%" },
    worst_case: { price: 8800, return: "+3%" }
  },
  
  rental_yield_scenarios: {
    conservative: "3.2%",
    expected: "3.8%",
    optimistic: "4.5%"
  },
  
  entry_exit: {
    recommended_entry: "₹8,200-8,800/sqft",
    target_exit: "₹11,000+/sqft",
    hold_period: "4-6 years"
  }
}
```

### 2.7 Comparable Properties Tab

```jsx
// Tab 6: Comparable Properties
{
  comparables: [
    {
      project: "Prestige Lakeside",
      price_sqft: 9200,
      distance: "0.5km",
      similarity: 92
    },
    {
      project: "Brigade Cosmopolis",
      price_sqft: 8800,
      distance: "1.2km",
      similarity: 85
    }
  ],
  
  price_analysis: {
    subject_property: 8500,
    area_average: 8900,
    percentile: "35th"  // Below average = good value
  }
}
```

### 2.8 Strategy & Recommendations Tab

```jsx
// Tab 7: Strategy & Recommendations
{
  investment_strategy: {
    entry_timing: "NOW - prices stable",
    negotiation_range: "₹8,200-8,600/sqft",
    portfolio_fit: "Good for long-term growth"
  },
  
  action_items: [
    "Verify RERA approval",
    "Check rental agreement terms",
    "Negotiate 3-5% below asking"
  ],
  
  timeline: {
    due_diligence: "2 weeks",
    closing: "4-6 weeks"
  }
}
```

### 2.9 Data Transparency Tab

```jsx
// Tab 8: Data Transparency (Truth Firewall)
{
  data_sources: [
    { source: "BBMP", type: "Building records", freshness: "Updated 2 days ago" },
    { source: "RERA", type: "Project approvals", freshness: "Updated weekly" },
    { source: "MagicBricks", type: "Listings", freshness: "Updated daily" }
  ],
  
  confidence_breakdown: {
    price_data: { confidence: 92, source: "aggregated" },
    infrastructure: { confidence: 88, source: "government" },
    projections: { confidence: 65, source: "model_estimated" }
  },
  
  missing_data_warnings: [
    "Flood zone data not available for this micro-location"
  ],
  
  verification_status: "VERIFIED"  // Truth Firewall result
}
```

### 2.10 Client Pitch Tab (Broker Killer)

```jsx
// Tab 9: Client Pitch (Premium Feature)
{
  presentation_mode: true,
  
  client_summary: {
    headline: "Whitefield 3BHK - Strong Investment Opportunity",
    key_points: ["20% below market", "Metro connectivity", "High rental demand"],
    ask: "₹1.2 Cr",
    expected_return: "18-25% in 3 years"
  },
  
  shareable_report: {
    pdf_export: true,
    whatsapp_share: true,
    email_template: true
  }
}
```

---

## 3. Tiered Tab Strategy

### 3.1 Free Tier (Hook Layer)

**Goal:** Demonstrate intelligence, trigger curiosity, drive upgrade

| Tab | Access | Content |
|-----|--------|---------|
| Decision Verdict | LIMITED | Verdict + 2-3 reasons only |
| Market Snapshot | LIMITED | Basic price/trend only |
| Spatial Intelligence | PREVIEW | Few highlights, blurred details |
| Risk Analysis | 🔒 LOCKED | Upgrade prompt |
| ROI Projection | 🔒 LOCKED | Upgrade prompt |
| Comparables | 🔒 LOCKED | Upgrade prompt |
| Strategy | 🔒 LOCKED | Upgrade prompt |
| Data Transparency | 🔒 LOCKED | Upgrade prompt |
| Client Pitch | 🔒 LOCKED | Upgrade prompt |

### 3.2 Pro Tier ($19/month)

**Goal:** Deliver real value, make users feel smart

| Tab | Access | Content |
|-----|--------|---------|
| Decision Verdict | FULL | Complete reasoning + strategy |
| Market Snapshot | FULL | All indicators + charts |
| Spatial Intelligence | FULL | Complete GIS insights |
| Risk Analysis | FULL | All risk factors + scores |
| ROI Projection | FULL | 3-year projections + scenarios |
| Comparables | FULL | All similar properties |
| Strategy | FULL | Entry/exit recommendations |
| Data Transparency | FULL | Truth Firewall verification |
| Client Pitch | 🔒 LOCKED | Premium upgrade |

### 3.3 Premium Tier ($49/month) - Optional Future

**Goal:** Professional-grade intelligence

| Tab | Access | Content |
|-----|--------|---------|
| All Pro Tabs | FULL | Everything in Pro |
| Client Pitch | FULL | Broker presentation mode |
| Advanced Spatial | FULL | Growth heatmaps, predictions |
| API Access | FULL | For integration |

---

## 4. Credit System

### 4.1 Simple LLM-Based Pricing

| LLM Type | Credits | Models |
|----------|---------|--------|
| **Local** | 2 | qwen, phi (Ollama) |
| **Cloud** | 5 | deepseek, openrouter |

### 4.2 Plans

| Plan | Price | Credits | Features |
|------|-------|---------|----------|
| **Free** | $0 | 50/month | Local LLM, 3 tabs |
| **Pro** | $19/month | 500/month + rollover | All LLMs, 8 tabs |
| **Top-ups** | $5-$25 | 100-800 credits | Never expire |

---

## 5. Implementation Files

### 5.1 New Files (8)

| File | Purpose |
|------|---------|
| `backend/ai/sequential_model_manager.py` | Model lifecycle |
| `backend/ai/task_batcher.py` | Task batching |
| `backend/ai/smart_tab_renderer.py` | Tab generation |
| `backend/ai/cognitive_workflow.py` | Adaptive reasoning |
| `backend/routes/payment_routes.py` | Stripe + top-ups |
| `backend/services/stripe_service.py` | Stripe helper |
| `src/components/SmartTab.jsx` | Tab component |
| `src/components/CreditBalance.jsx` | Credit display |

### 5.2 Modified Files (4)

| File | Changes |
|------|---------|
| `backend/routes/chat_routes.py` | SSE events, tab rendering |
| `backend/ai/credits_rate_limiter.py` | Top-ups, rollover |
| `backend/ai/task_orchestrator.py` | Credit tracking per LLM call |
| `src/components/AnalysisPanel.jsx` | Smart Tab section |

---

## 6. Adaptive Reasoning Features

### 6.1 Cognitive Workflow Engine

```python
class CognitiveWorkflowEngine:
    """
    Adaptive reasoning with temporal context.
    """
    
    def __init__(self):
        self.reasoning_modes = [
            'spatial_graph_thinking',
            'temporal_phase_awareness',
            'confidence_calibration',
            'conflict_resolution',
            'micro_context_awareness'
        ]
    
    def analyze(self, query, facts, user_profile):
        # Detect specialist mode needed
        specialist = self.detect_specialist(query)
        
        # Apply adaptive reasoning
        reasoning = self.apply_reasoning_layers(
            query=query,
            facts=facts,
            mode=specialist
        )
        
        # Calibrate confidence
        reasoning = self.calibrate_confidence(reasoning)
        
        return reasoning
```

### 6.2 Multi-Domain Specialists

```python
SPECIALIST_MODES = {
    'planner': {
        'focus': 'investment_strategy',
        'tabs': ['decision_verdict', 'strategy']
    },
    'investor': {
        'focus': 'roi_analysis',
        'tabs': ['roi_projection', 'risk_analysis']
    },
    'gis_analyst': {
        'focus': 'spatial_intelligence',
        'tabs': ['spatial_intelligence', 'market_snapshot']
    },
    'building_analyst': {
        'focus': 'property_evaluation',
        'tabs': ['comparables', 'risk_analysis']
    },
    'navigator': {
        'focus': 'location_guidance',
        'tabs': ['spatial_intelligence', 'market_snapshot']
    }
}
```

---

## 7. Summary

### Architecture Flow
```
User Query
    ↓
Detect User Profile + Specialist Mode
    ↓
Adaptive Reasoning Layer
    ↓
Truth Firewall (Grounded Facts)
    ↓
Smart Tab Generation (based on tier)
    ↓
Analysis Panel Display
```

### Key Innovations
1. **Decision Verdict First** - Answers "What should I do?" immediately
2. **Tiered Tab Strategy** - Free = Hook, Pro = Value, Premium = Power
3. **LLM-Based Credits** - 2 for local, 5 for cloud
4. **Truth Firewall** - Data transparency builds trust
5. **Client Pitch Tab** - Broker killer feature

---

*Implementation Plan v3.0 - February 16, 2026*
