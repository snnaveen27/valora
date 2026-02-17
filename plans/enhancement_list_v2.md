# Valora AI - Enhancement List (Simplified)

**Focus:** HIGH Priority Only  
**Tiers:** Free + Pro (No Unlimited)  
**Date:** February 16, 2026

---

## Tier Structure (Simplified)

| Tier | Price | Queries/Month | Features |
|------|-------|---------------|----------|
| **Free** | $0 | 50 | Limited verdict + Basic market snapshot |
| **Pro** | $19/month | 500 | Full analysis + ROI + Risk + Comparables |

---

## HIGH Priority Enhancements (4 Items)

### 1. TIERED PLANNING SYSTEM (4 Tiers)

**What it does:** Routes queries through 4 planning tiers based on complexity
- Tier 1: Rule Templates (60% coverage, <5ms) - No LLM needed
- Tier 2: Few-Shot Prompts (25% coverage, ~50ms) - Qwen3
- Tier 3: Specialist LoRA (10% coverage, ~100ms) - Phi-4
- Tier 4: Self-Learning (continuous improvement)

**Files to Create/Modify:**
- [ ] `backend/ai/tiered_planner.py` - NEW: 4-tier fallback logic
- [ ] `backend/ai/tier1_templates.py` - NEW: Rule templates for common intents
- [ ] `backend/ai/tier2_fewshot.py` - NEW: Few-shot prompt library
- [ ] `backend/ai/self_learning.py` - MODIFY: Connect Tier 4 promotion

**Key Implementation:**
```python
class TieredPlanner:
    def create_graph(self, query, intent, agent_facts):
        # Try Tier 1 first (fastest)
        graph = self.try_tier1(intent, agent_facts)
        if graph:
            return graph  # 60% of queries end here
        
        # Fall back to Tier 2
        graph = self.try_tier2(query, intent, agent_facts)
        if graph:
            return graph
        
        # Fall back to Tier 3 (specialist)
        graph = self.try_tier3(query, intent, agent_facts)
        return graph
```

---

### 2. SEQUENTIAL MODEL MANAGEMENT (6GB VRAM)

**What it does:** Manages model loading/unloading for limited VRAM
- Detects available VRAM
- Loads only one model at a time
- Batches tasks to minimize model switches
- Emits SSE events during model switching

**Files to Create/Modify:**
- [ ] `backend/ai/sequential_model_manager.py` - NEW: Model lifecycle
- [ ] `backend/ai/task_batcher.py` - NEW: Group tasks by model
- [ ] `backend/routes/chat_routes.py` - MODIFY: Add model switch SSE events

**Key Implementation:**
```python
class SequentialModelManager:
    MODELS = {
        'qwen3-8b': {'vram': 5.5, 'purpose': 'general'},
        'phi-4': {'vram': 4.8, 'purpose': 'specialist'}
    }
    
    def ensure_model(self, model_name):
        if self.current_model == model_name:
            return  # Already loaded
        
        # Unload current, load new (4s overhead)
        emit_sse('model_switching', {'to': model_name})
        ollama.stop(self.current_model)
        ollama.run(model_name)
        emit_sse('model_loaded', {'model': model_name})
```

---

### 3. UI TAB SYSTEM (Free vs Pro)

**What it does:** Renders different tabs based on user tier

| Tab | Free | Pro |
|-----|------|-----|
| Decision Verdict | ✅ Limited (verdict only) | ✅ Full (verdict + reasoning) |
| Market Snapshot | ✅ Basic | ✅ Full trends |
| Risk Analysis | 🔒 Locked | ✅ Full |
| ROI Projection | 🔒 Locked | ✅ Full |
| Comparables | 🔒 Locked | ✅ Full |

**Files to Create/Modify:**
- [ ] `backend/ai/ui_tab_renderer.py` - NEW: Tiered tab generation
- [ ] `src/components/TabPanel.jsx` - NEW: Tab display component
- [ ] `src/components/LockedTab.jsx` - NEW: Upgrade prompt for locked tabs
- [ ] `backend/routes/chat_routes.py` - MODIFY: Return tab structure

**Key Implementation:**
```python
UI_TABS = {
    'free': [
        {'id': 'decision_verdict', 'type': 'limited'},
        {'id': 'market_snapshot', 'type': 'limited'},
        {'id': 'risk_analysis', 'type': 'locked'},  # Shows upgrade prompt
        {'id': 'roi_projection', 'type': 'locked'},
        {'id': 'comparables', 'type': 'locked'},
    ],
    'pro': [
        {'id': 'decision_verdict', 'type': 'full'},
        {'id': 'market_snapshot', 'type': 'full'},
        {'id': 'risk_analysis', 'type': 'full'},
        {'id': 'roi_projection', 'type': 'full'},
        {'id': 'comparables', 'type': 'full'},
    ]
}
```

---

### 4. PAYMENT INTEGRATION (Stripe)

**What it does:** Handles subscription payments via Stripe
- Subscribe to Pro ($19/month)
- Manage subscription (cancel, upgrade)
- Webhook handling for payment events

**Files to Create/Modify:**
- [ ] `backend/routes/payment_routes.py` - NEW: Stripe endpoints
- [ ] `backend/services/stripe_service.py` - NEW: Stripe integration
- [ ] `src/components/PaymentCheckout.jsx` - MODIFY: Connect to Stripe
- [ ] `backend/ai/credits_rate_limiter.py` - MODIFY: Connect to Stripe

**Key Implementation:**
```python
# backend/routes/payment_routes.py
@router.post("/create-checkout-session")
async def create_checkout_session(user_id: str):
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{
            "price": "price_pro_monthly",  # $19/month
            "quantity": 1
        }],
        success_url=f"{FRONTEND_URL}/success",
        cancel_url=f"{FRONTEND_URL}/cancel"
    )
    return {"url": session.url}

@router.post("/webhook")
async def stripe_webhook(request: Request):
    # Handle: checkout.session.completed, customer.subscription.deleted
    pass
```

---

## Implementation Order

```
Phase 1: Foundation
├── 1.1 Create tiered_planner.py with Tier 1 templates
├── 1.2 Create sequential_model_manager.py
└── 1.3 Add model switch SSE events

Phase 2: UI & Monetization
├── 3.1 Create ui_tab_renderer.py
├── 3.2 Create TabPanel.jsx + LockedTab.jsx
└── 4.1 Create Stripe payment routes

Phase 3: Integration
├── 1.3 Add Tier 2 few-shot prompts
├── 1.4 Add Tier 3 specialist routing
└── 4.2 Connect payment to tier system
```

---

## Files Summary

### New Files (8)
1. `backend/ai/tiered_planner.py`
2. `backend/ai/tier1_templates.py`
3. `backend/ai/tier2_fewshot.py`
4. `backend/ai/sequential_model_manager.py`
5. `backend/ai/task_batcher.py`
6. `backend/ai/ui_tab_renderer.py`
7. `backend/routes/payment_routes.py`
8. `backend/services/stripe_service.py`

### Modified Files (4)
1. `backend/ai/self_learning.py` - Tier 4 integration
2. `backend/routes/chat_routes.py` - SSE events + tab structure
3. `src/components/PaymentCheckout.jsx` - Stripe integration
4. `backend/ai/credits_rate_limiter.py` - Stripe connection

### Frontend Components (2)
1. `src/components/TabPanel.jsx` - Tab display
2. `src/components/LockedTab.jsx` - Upgrade prompt

---

## Next Steps

Please confirm:
1. **Tier Structure:** Free (50 queries) vs Pro ($19/month, 500 queries) - OK?
2. **Tab Distribution:** 2 tabs for Free, 5 tabs for Pro - OK?
3. **Payment:** Stripe integration - OK?
4. **Any changes** to the implementation order?

Once confirmed, I will create detailed implementation specifications for each enhancement.
