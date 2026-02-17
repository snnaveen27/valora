# Valora AI - Enhancement List

**Analysis Date:** February 16, 2026  
**Architecture Version:** 4.2 Production  
**Current State:** Partial Implementation

---

## Executive Summary

The current codebase has solid foundations for many components but lacks the **tiered planning system**, **sequential model management**, and **monetization-ready UI tabs** specified in the architecture. Below is a prioritized enhancement list.

---

## 1. TIERED PLANNING SYSTEM (4 Tiers) - MISSING

**Architecture Spec:**
```
Tier 1: Rule Templates (60% coverage, <5ms)
Tier 2: Few-Shot Prompts (25% coverage, ~50ms with Qwen3)
Tier 3: Specialist LoRA (10% coverage, ~100ms with Phi-4)
Tier 4: Self-Learning (continuous improvement)
```

**Current State:**
- [`task_templates.py`](backend/ai/task_templates.py) - Has template system but NOT tiered fallback
- [`production_task_planner.py`](backend/ai/production_task_planner.py) - Has task patterns but NOT 4-tier logic
- [`self_learning.py`](backend/ai/self_learning.py) - Has learning but NOT Tier 4 integration

**Enhancement Required:**
- [ ] **1.1** Create `backend/ai/tiered_planner.py` with 4-tier fallback logic
- [ ] **1.2** Implement Tier 1 rule templates for common intents (property_search, analyze_area, valuation, investment)
- [ ] **1.3** Implement Tier 2 few-shot prompt library with Qwen3 integration
- [ ] **1.4** Implement Tier 3 Phi-4 LoRA specialist domains (valuation, legal, compliance, roi_analysis)
- [ ] **1.5** Connect Tier 4 self-learning to auto-promote patterns to Tier 1

---

## 2. SEQUENTIAL MODEL MANAGEMENT (6GB VRAM) - MISSING

**Architecture Spec:**
```python
class SequentialModelManager:
    - ensure_model() - Load model, switching if necessary
    - switch_overhead_s = 4.0
    - Models: qwen3-8b (5.5GB), phi-4 (4.8GB)
```

**Current State:**
- [`model_router.py`](backend/ai/model_router.py) - Has model selection but NOT sequential loading
- No VRAM-aware model switching logic

**Enhancement Required:**
- [ ] **2.1** Create `backend/ai/sequential_model_manager.py`
- [ ] **2.2** Implement VRAM detection and model size tracking
- [ ] **2.3** Implement model unload/load with SSE notifications
- [ ] **2.4** Create `TaskBatcher` to group tasks by model (minimize switches)
- [ ] **2.5** Add model switch overhead estimation to response timing

---

## 3. UI TAB SYSTEM WITH MONETIZATION - MISSING

**Architecture Spec:**
```
Free: Decision Verdict (limited) + Market Snapshot (limited)
Pro: + Risk Analysis + ROI + Comparables (full)
Enterprise: + Spatial Intelligence (deep) + Strategy + Client Pitch
```

**Current State:**
- [`credits_rate_limiter.py`](backend/ai/credits_rate_limiter.py) - Has tier system (free/pro/team/enterprise)
- [`EnhancedChatPanel.jsx`](src/components/chat/EnhancedChatPanel.jsx) - Has chat UI but NOT tab system
- No tiered tab rendering logic

**Enhancement Required:**
- [ ] **3.1** Create `backend/ai/ui_tab_renderer.py` for tiered tab generation
- [ ] **3.2** Implement tab definitions: decision_verdict, market_snapshot, spatial_intelligence, risk_analysis, roi_projection, comparable_properties, strategy_recommendations, client_pitch
- [ ] **3.3** Create frontend `TabPanel.jsx` component for tab display
- [ ] **3.4** Implement locked tab UI with upgrade prompts
- [ ] **3.5** Add tier-based content filtering (limited vs full vs deep)

---

## 4. STATE MACHINE ORCHESTRATOR - PARTIAL

**Architecture Spec:**
```
States: NEW_REQUEST → FACT_COLLECTION → PLANNING → PREVIEW_READY → 
        WAIT_USER_CONFIRM → EXECUTING → VERIFYING → ASSEMBLING → COMPLETE
```

**Current State:**
- [`task_orchestrator.py`](backend/ai/task_orchestrator.py) - Has orchestration but NOT state machine pattern
- [`agentic_loop.py`](backend/ai/agentic_loop.py) - Has Think→Act→Observe→Reflect but NOT request states

**Enhancement Required:**
- [ ] **4.1** Create `backend/ai/state_machine.py` with FSM implementation
- [ ] **4.2** Implement state transitions with SSE events
- [ ] **4.3** Add PREVIEW_READY state for user confirmation flow
- [ ] **4.4** Create state recovery logic for FAILED state

---

## 5. PHI-4 LoRA SPECIALIST MODELS - MISSING

**Architecture Spec:**
```
PHI4_SPECIALIST_DOMAINS = ['valuation', 'legal', 'compliance', 'roi_analysis', 'risk_assessment']
LoRA adapters at /models/phi4-{domain}-lora
```

**Current State:**
- No LoRA integration exists
- Model router supports Phi-4 but not with LoRA adapters

**Enhancement Required:**
- [ ] **5.1** Create LoRA adapter loading infrastructure
- [ ] **5.2** Train/fine-tune Phi-4 LoRA adapters for specialist domains
- [ ] **5.3** Implement domain detection for specialist routing
- [ ] **5.4** Add LoRA path configuration to `llm_config.json`

---

## 6. INTENT DETECTION WITH TIERED CACHE - PARTIAL

**Architecture Spec:**
```
Intent Detection: Pattern matching (1-5ms)
Cache: 10-min TTL, 60% hit rate for Tier 1
```

**Current State:**
- [`chat_routes.py`](backend/routes/chat_routes.py) - Has cache via `get_chat_cache()`
- No explicit intent detection timing metrics

**Enhancement Required:**
- [ ] **6.1** Create dedicated `IntentDetector` class with pattern matching
- [ ] **6.2** Add intent detection timing metrics
- [ ] **6.3** Implement tiered cache (Tier 1 templates cached separately)
- [ ] **6.4** Add cache hit rate monitoring

---

## 7. TRUTH FIREWALL ENHANCEMENT - PARTIAL

**Architecture Spec:**
```
1.6M+ records (686K buildings, 42K properties, 27K POIs)
TOLERANCES = {price: 0.15, distance: 0.20, count: 0.10}
```

**Current State:**
- [`gis_agents.py`](backend/ai/gis_agents.py) - Has multi-agent system
- [`fact_verifier.py`](backend/ai/fact_verifier.py) - Has verification with tolerances

**Enhancement Required:**
- [ ] **7.1** Verify data counts match architecture spec (1.6M+ records)
- [ ] **7.2** Add parallel GIS agent execution with ThreadPoolExecutor
- [ ] **7.3** Implement AgentFacts typed output structure
- [ ] **7.4** Add verification pass/fail threshold (75% verified = PASS)

---

## 8. PAYMENT INTEGRATION (Stripe) - MISSING

**Architecture Spec:**
```
Free: $0 (50 queries/month)
Pro: $19/month (500 queries)
Enterprise: $299/month (unlimited)
```

**Current State:**
- [`credits_rate_limiter.py`](backend/ai/credits_rate_limiter.py) - Has dummy payment system
- [`PaymentCheckout.jsx`](src/components/PaymentCheckout.jsx) - Has UI component

**Enhancement Required:**
- [ ] **8.1** Integrate Stripe SDK in backend
- [ ] **8.2** Create payment routes (`/api/payments/*`)
- [ ] **8.3** Implement webhook handling for payment confirmation
- [ ] **8.4** Connect tier upgrades to payment success

---

## 9. UPGRADE TRIGGERS - MISSING

**Architecture Spec:**
```python
UPGRADE_TRIGGERS = {
    'free_to_pro': ['click_locked_tab', 'query_limit_reached', 'complex_query_attempted'],
    'pro_to_enterprise': ['api_access_requested', 'broker_pitch_clicked']
}
```

**Current State:**
- No upgrade trigger system exists

**Enhancement Required:**
- [ ] **9.1** Create `backend/ai/upgrade_triggers.py`
- [ ] **9.2** Implement locked tab click detection
- [ ] **9.3** Add query limit reached modal
- [ ] **9.4** Create upgrade prompt UI component

---

## 10. USAGE TRACKING & BILLING - PARTIAL

**Architecture Spec:**
```
Track: queries per month, model usage, cache hits
Billing: Monthly invoicing for enterprise
```

**Current State:**
- [`usage_tracker.py`](backend/usage_tracker.py) - Has usage tracking
- [`credits_rate_limiter.py`](backend/ai/credits_rate_limiter.py) - Has usage log table

**Enhancement Required:**
- [ ] **10.1** Add monthly query count aggregation
- [ ] **10.2** Implement billing invoice generation
- [ ] **10.3** Create usage dashboard for users
- [ ] **10.4** Add model usage cost tracking

---

## 11. API DESIGN ENHANCEMENT - PARTIAL

**Architecture Spec:**
```http
POST /api/chat/stream
SSE Events: status, intent_detected, model_loaded, task_progress, content, verification, done
```

**Current State:**
- [`chat_routes.py`](backend/routes/chat_routes.py) - Has `/api/chat/stream` endpoint
- SSE events exist but not all specified events

**Enhancement Required:**
- [ ] **11.1** Add `intent_detected` SSE event
- [ ] **11.2** Add `model_loaded` SSE event for model switching
- [ ] **11.3** Add `verification` SSE event with pass/fail status
- [ ] **11.4** Standardize SSE event format

---

## 12. TESTING & QUALITY - PARTIAL

**Architecture Spec:**
```
65 tests, 98% pass rate
Benchmarks: Tier 1 coverage >60%, Avg response <3s
```

**Current State:**
- [`test_valora_suite.py`](backend/tests/test_valora_suite.py) - Has test suite

**Enhancement Required:**
- [ ] **12.1** Add tests for tiered planner (Tier 1-4)
- [ ] **12.2** Add tests for sequential model manager
- [ ] **12.3** Add tests for UI tab rendering
- [ ] **12.4** Add performance benchmarks

---

## 13. DOCKER DEPLOYMENT - PARTIAL

**Architecture Spec:**
```yaml
services: backend, ollama
VRAM_GB=6, SEQUENTIAL_MODE=true
```

**Current State:**
- [`docker-compose.yml`](docker-compose.yml) - Exists but needs verification

**Enhancement Required:**
- [ ] **13.1** Add environment variables for tiered planning
- [ ] **13.2** Add GPU resource configuration
- [ ] **13.3** Add model pre-pulling in Dockerfile
- [ ] **13.4** Add health checks for model availability

---

## Summary Table

| # | Enhancement | Priority | Effort | Dependencies |
|---|-------------|----------|--------|--------------|
| 1 | Tiered Planning System | HIGH | High | None |
| 2 | Sequential Model Management | HIGH | Medium | None |
| 3 | UI Tab System with Monetization | HIGH | High | #1, #4 |
| 4 | State Machine Orchestrator | MEDIUM | Medium | None |
| 5 | Phi-4 LoRA Specialist Models | MEDIUM | High | #2 |
| 6 | Intent Detection with Cache | MEDIUM | Low | None |
| 7 | Truth Firewall Enhancement | MEDIUM | Low | None |
| 8 | Payment Integration (Stripe) | HIGH | Medium | #3 |
| 9 | Upgrade Triggers | MEDIUM | Low | #3 |
| 10 | Usage Tracking & Billing | MEDIUM | Medium | #8 |
| 11 | API Design Enhancement | LOW | Low | None |
| 12 | Testing & Quality | LOW | Medium | All |
| 13 | Docker Deployment | LOW | Low | None |

---

## Recommended Implementation Order

**Phase 1 (Core Revenue):**
1. Tiered Planning System (#1)
2. Sequential Model Management (#2)
3. UI Tab System (#3)
4. Payment Integration (#8)

**Phase 2 (Enhancement):**
5. State Machine Orchestrator (#4)
6. Upgrade Triggers (#9)
7. Usage Tracking & Billing (#10)

**Phase 3 (Optimization):**
8. Phi-4 LoRA Specialist Models (#5)
9. Intent Detection Enhancement (#6)
10. Truth Firewall Enhancement (#7)

**Phase 4 (Polish):**
11. API Design Enhancement (#11)
12. Testing & Quality (#12)
13. Docker Deployment (#13)

---

*Generated from architecture analysis - February 16, 2026*
