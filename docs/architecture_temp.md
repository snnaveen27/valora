# Valora AI — Production Architecture v4.0
**Complete Production-Grade Architecture**  
*Unified architecture combining Adaptive Cognitive Loop, Reasoning State Machine, 3-Layer Agent Brain, Domain Resolver, UI Schema Builder, and production implementation details.*

**Generated:** February 14, 2026  
**Version:** 4.0 (Unified Production Release)

---

## Executive Summary

Valora AI is a production-grade adaptive cognition system that combines:
- **Grounded Spatial Intelligence**: 1.6M+ deterministic facts (686K buildings, 42K properties, 27K POIs)
- **Adaptive Multi-Step Reasoning**: Self-improving cognitive loop with graph-based task orchestration
- **Truth Firewall**: Separation of deterministic facts from LLM reasoning prevents hallucination
- **Intelligent Model Routing**: Learning-aware selection between local (Qwen3-4B) and cloud models
- **Production Reliability**: Circuit breakers, state machines, timeouts, retries, observability
- **Graph-Driven UI**: Deterministic, explainable interface generated from reasoning graph

**Target Audience**: Architects, ML Engineers, Backend Engineers, Frontend Engineers, SREs, Product Owners

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Request Flow Architecture](#2-request-flow-architecture)
3. [Core Design Principles](#3-core-design-principles)
4. [3-Layer Agent Brain](#4-3-layer-agent-brain)
5. [Domain Resolver & Cognitive Modes](#5-domain-resolver--cognitive-modes)
6. [Adaptive Cognitive Loop](#6-adaptive-cognitive-loop)
7. [Reasoning State Machine](#7-reasoning-state-machine)
8. [Planner & Task Graph](#8-planner--task-graph)
9. [Intelligent Model Router](#9-intelligent-model-router)
10. [Micro-Reasoners & Specialist Modes](#10-micro-reasoners--specialist-modes)
11. [Truth Firewall & GIS Agents](#11-truth-firewall--gis-agents)
12. [UI Schema Builder](#12-ui-schema-builder)
13. [Meta-Cognition & Adaptive UX](#13-meta-cognition--adaptive-ux)
14. [Execution Engine](#14-execution-engine)
15. [Fact Verification](#15-fact-verification)
16. [Data Layer](#16-data-layer)
17. [API Architecture](#17-api-architecture)
18. [Resilience & Circuit Breakers](#18-resilience--circuit-breakers)
19. [Observability & Metrics](#19-observability--metrics)
20. [Security & Compliance](#20-security--compliance)
21. [Testing Strategy](#21-testing-strategy)
22. [Deployment Patterns](#22-deployment-patterns)
23. [File Structure](#23-file-structure)
24. [Configuration Reference](#24-configuration-reference)
25. [Appendices](#25-appendices)
26. [Change Log](#26-change-log)

---

## 1. System Overview

### 1.1 Core Architecture Principle

```
Truth Firewall + Adaptive Cognition + Intelligent Routing + Learning System = Production AI
```

### 1.2 Key Capabilities

| Capability | Implementation | Status |
|------------|---------------|--------|
| **Local-First LLM** | Qwen3-4B (Ollama) | ✅ Production |
| **Cloud Escalation** | OpenRouter → Ollama Cloud | ✅ Production |
| **Deterministic Facts** | 1.6M+ spatial records | ✅ Production |
| **Adaptive Reasoning** | Task Graph + Self-Evaluation | ✅ Production |
| **Learning Router** | SQLite performance tracking | ✅ Production |
| **Truth Verification** | Post-LLM fact checking | ✅ Production |
| **Graph-Driven UI** | Schema builder from tasks | 🚧 In Development |
| **Meta-Cognition** | Adaptive UX monitoring | 🚧 Planned |

### 1.3 Data Scale

| Resource | Count | Technology |
|----------|-------|------------|
| Properties | 42,452 | SQLite + SpatialLite |
| Buildings | 686,370 | SQLite + SpatialLite |
| POIs | 26,961 | SQLite + SpatialLite |
| Transport Nodes | 5,384 | SQLite + SpatialLite |
| Road Segments | 334,784 | SQLite + SpatialLite |
| Vector Embeddings | 77,000 | FAISS (384-dim) |
| Terrain Tiles | 33×33 heightmaps | PostgreSQL + PostGIS |
| **Total Records** | **1.6M+** | Multi-database |

---

## 2. Request Flow Architecture

### 2.1 Complete Pipeline

```
User Query [request_id: a1b2c3d4e5f6]
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: REQUEST INITIALIZATION                                │
├─────────────────────────────────────────────────────────────────┤
│ • Generate request_id (12-char UUID prefix)                    │
│ • Load session_context (user_id, conversation_memory)          │
│ • Start timing metrics collection                              │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: DOMAIN RESOLUTION & INTENT CLASSIFICATION             │
├─────────────────────────────────────────────────────────────────┤
│ • Domain Resolver: real_estate | finance | city_planning       │
│ • Intent Router: navigate | analyze | search | compare | etc.  │
│ • Cognitive Mode: analysis | plan | simulate | advice          │
│ • Slot Extraction: locations, constraints, preferences         │
│ Timeline: ~5-15ms (deterministic rules + LLM fallback)         │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: CACHE CHECK                                           │
├─────────────────────────────────────────────────────────────────┤
│ • Key: query + intent + domain                                 │
│ • LRU + TTL (10 minutes)                                       │
│ • Cache HIT → return stored response (skip all below)          │
│ • Cache MISS → continue to facts gathering                     │
│ Timeline: ~1-3ms                                               │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 4: GIS AGENT ORCHESTRATION (Truth Firewall Input)       │
├─────────────────────────────────────────────────────────────────┤
│ Deterministic Agents (run in parallel):                        │
│ • Geocoder: lat/lng resolution, fuzzy matching                 │
│ • Spatial: POI counts, buffers, building density               │
│ • Terrain: elevation, slope, flood risk                        │
│ • Property: listings, price history, market data               │
│ • RAG: vector search for builder history, regulations          │
│ • City Intelligence: locality personality, risk indexes        │
│ Output: AgentFacts (typed, timestamped, sourced)               │
│ Timeline: ~80-200ms (database + vector search)                 │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 5: PLANNING & TASK GRAPH CONSTRUCTION                    │
├─────────────────────────────────────────────────────────────────┤
│ • Rule-based Planner (fast templates for common intents)       │
│ • LLM-assisted Planner (complex multi-step requests)           │
│ • Task Graph: DAG with metadata, dependencies, ui_hints        │
│ • Initial graph validation (max_depth, branching limits)       │
│ • State: INITIALIZING → PLANNING → READY                       │
│ Timeline: ~10-50ms (deterministic) or ~500ms (LLM-assisted)    │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 6: ADAPTIVE COGNITIVE LOOP (Core Reasoning)              │
├─────────────────────────────────────────────────────────────────┤
│ WHILE task_graph NOT finished:                                 │
│   1. TASK EXECUTION                                            │
│      • Pull next task from graph                               │
│      • Model Router selects LLM (local vs cloud)               │
│      • Execute micro-reasoner with AgentFacts                  │
│      • Stream SSE: task_progress, model_selection              │
│      State: READY → EXECUTING_TASK                             │
│                                                                 │
│   2. SELF-EVALUATION (Reviewer)                                │
│      • Validate output against AgentFacts                      │
│      • Check cross-task consistency                            │
│      • Compute confidence score                                │
│      • Decide: accept | retry | edit_graph | escalate          │
│      State: EXECUTING_TASK → REVIEWING                         │
│                                                                 │
│   3. ADAPTIVE ACTION                                           │
│      accept → mark completed, continue                         │
│      retry → adjust params, backoff, re-execute                │
│      edit_graph → insert/modify/reorder tasks                  │
│      escalate → switch to cloud model or specialist            │
│      State: REVIEWING → READY | RETRYING | EDITING_GRAPH       │
│                                                                 │
│   4. FACT VERIFICATION                                         │
│      • Extract claims (prices, distances, counts)              │
│      • Verify against AgentFacts (±tolerances)                 │
│      • Emit verification SSE event                             │
│      • If verified_ratio < threshold → add fetch_facts task    │
│                                                                 │
│   5. META-COGNITION (Monitoring)                               │
│      • Track confidence trends                                 │
│      • Monitor user engagement signals                         │
│      • Adjust verbosity, UI complexity                         │
│      • Insert clarification questions if ambiguous             │
│                                                                 │
│ Timeline: ~2-10 seconds (depends on task count & complexity)   │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 7: UI SCHEMA GENERATION                                  │
├─────────────────────────────────────────────────────────────────┤
│ • UI Schema Builder converts Task Graph → ui_schema JSON       │
│ • Always include anchor "Overview" tab                         │
│ • Map tasks to tabs via ui_hints (max 6 dynamic tabs)          │
│ • Generate sanitized previews for premium tabs                 │
│ • Include provenance: source_tasks, fact_refs                  │
│ • Validate: no PII exposure, stable structure                  │
│ State: COMPLETING → GENERATE_UI_SCHEMA → UI_VALIDATION         │
│ Timeline: ~20-100ms                                            │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 8: RESPONSE ASSEMBLY & STREAMING                         │
├─────────────────────────────────────────────────────────────────┤
│ SSE Events Emitted:                                            │
│ • status: "Connected"                                          │
│ • intent_detected: {intent, task_graph_summary}                │
│ • task_progress: {task_id, status, output_summary} (multiple)  │
│ • model_selection: {model, is_cloud, complexity_score}         │
│ • thinking: {content} (optional, for reasoning transparency)   │
│ • content: {content} (streaming user-facing text)              │
│ • verification: {total_claims, verified, status, warnings}     │
│ • ui_schema_ready: {ui_schema} (if graph-driven UI enabled)    │
│ • metadata: {intent, dashboard, ui_actions, facts}             │
│ • pipeline_metrics: {intent_ms, facts_ms, route_ms, llm_ms}    │
│ • done: {request_id, success, summary, thinking_time}          │
│ State: COMPLETING → DONE                                       │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 9: PERSISTENCE & LEARNING                                │
├─────────────────────────────────────────────────────────────────┤
│ • Cache response (QueryCache, 10-min TTL)                      │
│ • Record model performance (model_performance.db)              │
│ • Update conversation memory                                   │
│ • Persist ui_schema for replay (ui_schema_store)               │
│ • Log audit trail (raw outputs, graph edits, verifications)    │
│ Timeline: ~5-20ms                                              │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 10: TELEMETRY & MONITORING                               │
├─────────────────────────────────────────────────────────────────┤
│ • OpenTelemetry spans (all layers)                             │
│ • Metrics: latency, success rate, verification rate            │
│ • Alerts: circuit breaker opens, verification failures         │
│ • Request dumps on deadman timeout                             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Failure Paths

```
Circuit Breaker OPEN
    ↓
State: FALLBACK
    ↓
Generate deterministic response from AgentFacts only
    ↓
No LLM calls, pure fact synthesis
    ↓
Return with warning banner

---

Task Timeout
    ↓
Retry with exponential backoff (max 3 retries)
    ↓
If still failing → ESCALATE (switch to cloud model)
    ↓
If escalation fails → FALLBACK
    ↓
Return partial results with status indicator

---

Verification Failure (verified_ratio < threshold)
    ↓
Reviewer inserts fetch_more_facts task
    ↓
Re-execute with additional data
    ↓
If still failing → surface discrepancy to user with both values

---

Deadman Timeout (request > 300s)
    ↓
Alert SRE with request_id + context dump
    ↓
State: FAILED
    ↓
Return error payload with support ticket
```

---

## 3. Core Design Principles

### 3.1 Architectural Tenets

1. **Local-First, Cloud-Optional**
   - Default to `qwen3-4b` (local Ollama) for 80% of queries
   - Cloud escalation only when complexity demands it
   - User controls cloud toggle (privacy, cost control)

2. **Truth Firewall**
   - LLM never generates facts — only narratives
   - All numeric claims sourced from deterministic GIS agents
   - Post-LLM verification enforces this separation

3. **Micro-Reasoning Pattern**
   - Break complex requests into many small LLM passes
   - Each pass: focused prompt, strict JSON output, ~100-500 tokens
   - Enables targeted retries, better verification, cost control

4. **Adaptive Execution**
   - Planner output is not immutable
   - Reviewer can edit task graph during execution
   - Self-healing: detect missing data → insert fetch tasks

5. **Graph-Driven UI**
   - UI is deterministic visualization of reasoning graph
   - No hand-coded response templates
   - Explainable: every UI element traces to source tasks

6. **Learning-Aware Routing**
   - SQLite tracks model performance per intent
   - Router uses historical success/latency to bias selection
   - Continuous improvement without manual tuning

7. **Observability-First**
   - Every request gets unique `request_id`
   - SSE events stream internal state to frontend
   - OpenTelemetry spans for full distributed tracing

8. **Fail-Safe Deterministic Fallback**
   - When LLMs fail, always have a deterministic response path
   - Synthesize from AgentFacts only
   - Never leave user with generic error message

---

## 4. 3-Layer Agent Brain

### 4.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   LAYER 3: EXPERIENCE                       │
│                   (COMMUNICATION)                           │
├─────────────────────────────────────────────────────────────┤
│ • UI Schema Builder (Graph Interpreter)                    │
│ • Explanation Generator (Why? provenance)                  │
│ • Conversation Interface (chat + memory)                   │
│ • Visualization Engine (charts, maps, PDF)                 │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                   LAYER 2: EXECUTION                        │
│                      (DOING)                                │
├─────────────────────────────────────────────────────────────┤
│ • GIS Agents (Geocoder, Spatial, Terrain, Property, RAG)   │
│ • Simulation Engines (infrastructure, absorption)          │
│ • External Connectors (listings, municipal data)           │
│ • Task Executors (worker pool, parallel execution)         │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                   LAYER 1: COGNITIVE CORE                   │
│                     (THINKING)                              │
├─────────────────────────────────────────────────────────────┤
│ • Domain Resolver                                          │
│ • Intent Router                                            │
│ • Planner (rule-based + LLM-assisted)                      │
│ • Task Graph & Adaptive Cognitive Loop                     │
│ • Reasoning State Machine                                  │
│ • Micro-Reasoners (modes: analyst, simulator, planner)     │
│ • Reviewer / Self-Check                                    │
│ • Meta-Cognition (monitoring & adaptation)                 │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Layer Responsibilities

**Layer 1 — Cognitive Core (THINKING)**
- *Input*: User query, session context
- *Output*: Task Graph, execution plan, cognitive decisions
- *Technologies*: Python, LLMs (local + cloud), SQLite
- *Metrics*: Planning time, graph complexity, edit frequency

**Layer 2 — Execution System (DOING)**
- *Input*: Task Graph, AgentFacts requirements
- *Output*: Grounded facts, simulation results, external data
- *Technologies*: SQLite/SpatialLite, PostgreSQL/PostGIS, FAISS, APIs
- *Metrics*: Agent latency, fact coverage, cache hit ratio

**Layer 3 — Experience Layer (COMMUNICATION)**
- *Input*: Task Graph results, AgentFacts, user preferences
- *Output*: UI schema, explanations, visualizations, PDFs
- *Technologies*: React, Cesium, Chart.js, PDF generators
- *Metrics*: UI generation time, user engagement, comprehension signals

### 4.3 Inter-Layer Communication

```python
# Cognitive Core → Execution System
task = {
    "id": "t1",
    "type": "fetch_market_data",
    "input_facts": ["location", "timeframe"],
    "required_outputs": ["price_trend", "volume"]
}
executor.run(task) → AgentFacts

# Execution System → Cognitive Core
agent_facts = {
    "price_trend": {"values": [...], "source": "property_db", "timestamp": "2026-02-14T12:00:00Z"},
    "volume": {"count": 42, "source": "listings_api", "timestamp": "2026-02-14T12:00:00Z"}
}
reviewer.verify(task.output, agent_facts) → verification_result

# Cognitive Core → Experience Layer
task_graph_results = {
    "tasks": [{"id": "t1", "output": {...}, "ui_hint": {...}}, ...],
    "verification": {"verified_ratio": 0.85},
    "confidence": 0.78
}
ui_schema_builder.generate(task_graph_results) → ui_schema

# Experience Layer → User
ui_schema = {
    "anchor_tab": {"id": "overview", "label": "Investment Verdict", ...},
    "tabs": [{"id": "market", "label": "Market Trends", ...}, ...],
    "provenance": {"source_tasks": ["t1", "t2"], "fact_refs": [...]}
}
```

---

## 5. Domain Resolver & Cognitive Modes

### 5.1 Purpose

Early domain detection ensures:
- Correct planners and task templates are applied
- Appropriate GIS agents are activated
- Domain-specific UI components are selected
- Safety policies and validation rules are enforced

### 5.2 Domain Types

| Domain | Example Query | Agents | UI Templates |
|--------|---------------|--------|--------------|
| `real_estate` | "Find 2BHK in Whitefield" | Geocoder, Spatial, Property | Property cards, maps |
| `finance` | "Portfolio analysis" | Market data, RAG | Charts, tables |
| `city_planning` | "Metro impact simulation" | Spatial, Terrain, Simulator | 3D maps, impact panels |
| `project_management` | "Launch roadmap for Valora" | RAG, Timeline | Gantt, milestones |

### 5.3 Cognitive Modes

| Mode | Description | Typical Graph Depth |
|------|-------------|---------------------|
| `analysis` | Analyze area/building | 3-5 tasks |
| `plan` | Multi-step planning | 5-10 tasks |
| `compare` | Compare options | 4-6 tasks |
| `simulate` | What-if scenarios | 6-12 tasks |
| `advice` | Investment recommendations | 5-8 tasks |
| `navigate` | Spatial exploration | 2-3 tasks |

### 5.4 Implementation Pattern

```python
class DomainResolver:
    def resolve(self, query: str, context: dict) -> DomainContext:
        # 1. Deterministic rules (keyword matching)
        if any(kw in query.lower() for kw in ['find', 'property', 'bhk', 'apartment']):
            domain = 'real_estate'
            cognitive_mode = 'search'
        
        # 2. Intent classifier (fallback)
        elif self._is_ambiguous(query):
            intent_result = self.intent_classifier.classify(query)
            domain = intent_result['domain']
            cognitive_mode = intent_result['mode']
        
        # 3. LLM disambiguation (last resort)
        else:
            llm_result = self.llm.disambiguate(query, context)
            domain = llm_result['domain']
            cognitive_mode = llm_result['mode']
        
        # 4. Resolve persona and privacy mode
        persona = self._infer_persona(context.user_profile)
        privacy_mode = context.user_preferences.get('privacy_mode', 'standard')
        
        return DomainContext(
            domain=domain,
            cognitive_mode=cognitive_mode,
            persona=persona,
            privacy_mode=privacy_mode
        )
```

### 5.5 Session Persistence

```python
session_context = {
    "user_id": "user_123",
    "domain": "real_estate",
    "cognitive_mode": "analysis",
    "persona": "broker",
    "privacy_mode": "standard",
    "conversation_history": [...]
}
```

Domain persists across conversation turns for consistency.

---

## 6. Adaptive Cognitive Loop

### 6.1 Core Loop Pseudocode

```python
def adaptive_cognitive_loop(request_id, user_query, domain_context):
    # Initialize
    agent_facts = gis_orchestrator.gather_facts(user_query, domain_context)
    task_graph = planner.create_graph(user_query, agent_facts, domain_context)
    rsm = ReasoningStateMachine(request_id, task_graph)
    
    # Main loop
    while not task_graph.is_finished():
        # 1. Execute next task
        task = task_graph.next_task()
        rsm.transition("EXECUTING_TASK", task_id=task.id)
        
        try:
            result = executor.execute(task, agent_facts)
            persist_raw_output(request_id, task.id, result)
            emit_sse("task_progress", task_id=task.id, status="completed")
            
        except TimeoutError:
            if task.retries < task.max_retries:
                rsm.transition("RETRYING", task_id=task.id)
                continue
            else:
                rsm.transition("ESCALATING", task_id=task.id)
                task = escalate_task(task)  # Switch to cloud model
                continue
        
        # 2. Self-evaluation
        rsm.transition("REVIEWING", task_id=task.id)
        review = reviewer.self_check(task, result, agent_facts, task_graph)
        
        # 3. Adaptive action
        if review.action == "accept":
            task_graph.mark_completed(task.id, result)
            rsm.transition("READY")
            
        elif review.action == "retry":
            task.update_params(review.suggested_changes)
            task.incr_retries()
            rsm.transition("RETRYING")
            backoff_sleep(task.retries)
            continue
            
        elif review.action == "edit_graph":
            if task_graph.edit_count < config.max_graph_edits:
                task_graph.apply_changes(review.graph_edits)
                task_graph.incr_edit_count()
                rsm.transition("EDITING_GRAPH")
                emit_sse("graph_edited", reason=review.reason, edits=review.graph_edits)
                rsm.transition("READY")
            else:
                # Prevent runaway edits
                rsm.transition("FALLBACK")
                break
                
        elif review.action == "escalate":
            task_graph.insert(review.escalation_tasks, position=task_graph.current_index + 1)
            rsm.transition("ESCALATING")
            rsm.transition("READY")
        
        # 4. Fact verification
        if result.get('claims'):
            verification = fact_verifier.verify(result['claims'], agent_facts)
            emit_sse("verification", verification=verification)
            
            if verification.verified_ratio < config.verification_threshold:
                # Insert task to fetch missing facts
                fetch_task = create_fetch_facts_task(verification.missing_facts)
                task_graph.insert(fetch_task, position=task_graph.current_index + 1)
        
        # 5. Meta-cognition monitoring
        meta_cognition.monitor(task, result, review, agent_facts)
        if meta_cognition.should_adapt_ux():
            ui_adjustments = meta_cognition.get_adjustments()
            task_graph.update_ui_hints(ui_adjustments)
    
    # Generate UI schema
    rsm.transition("GENERATE_UI_SCHEMA")
    ui_schema = ui_schema_builder.generate(task_graph, agent_facts, domain_context)
    
    # Complete
    rsm.transition("COMPLETING")
    results = task_graph.collect_results()
    emit_sse("done", request_id=request_id, results=results, ui_schema=ui_schema)
    rsm.transition("DONE")
    
    return results, ui_schema
```

### 6.2 Reviewer Self-Check Logic

```python
class Reviewer:
    def self_check(self, task, result, agent_facts, task_graph):
        # Validate against grounded facts
        fact_match = self._verify_against_facts(result, agent_facts)
        
        # Check cross-task consistency
        consistency = self._check_consistency(result, task_graph.completed_tasks)
        
        # Compute confidence
        confidence = self._compute_confidence(result, fact_match, consistency)
        
        # Decide action
        if confidence > 0.8 and fact_match.verified_ratio > 0.85:
            return ReviewResult(action="accept", confidence=confidence)
        
        elif task.retries < task.max_retries and confidence > 0.5:
            return ReviewResult(
                action="retry",
                suggested_changes={"prompt_adjustments": self._suggest_prompt_fixes(result)},
                confidence=confidence
            )
        
        elif fact_match.missing_facts:
            return ReviewResult(
                action="edit_graph",
                graph_edits=[{
                    "op": "insert",
                    "task": self._create_fetch_facts_task(fact_match.missing_facts),
                    "position": task_graph.current_index + 1
                }],
                reason="missing_facts",
                confidence=confidence
            )
        
        elif confidence < 0.3 and config.cloud_enabled:
            return ReviewResult(
                action="escalate",
                escalation_tasks=[self._create_cloud_reasoning_task(task)],
                reason="low_confidence",
                confidence=confidence
            )
        
        else:
            # Accept with low confidence
            return ReviewResult(action="accept", confidence=confidence, warnings=["low_confidence"])
```

### 6.3 Self-Check Output Schema

```json
{
  "action": "edit_graph",
  "reason": "missing_facts",
  "confidence": 0.65,
  "verified_ratio": 0.4,
  "missing_facts": ["recent_price_trend", "metro_timeline"],
  "graph_edits": [
    {
      "op": "insert",
      "task": {
        "id": "t_fetch_1",
        "type": "fetch_market_data",
        "input_facts": ["location", "timeframe"],
        "required_outputs": ["recent_price_trend"]
      },
      "position": 3
    }
  ],
  "warnings": ["partial_verification"],
  "suggested_changes": {
    "prompt_adjustments": "Add explicit price range constraint"
  }
}
```

---

## 7. Reasoning State Machine

### 7.1 State Diagram

```
     ┌─────────────────┐
     │  INITIALIZING   │ ← Entry point
     └────────┬────────┘
              │ facts_ready
              ↓
     ┌─────────────────┐
     │    PLANNING     │
     └────────┬────────┘
              │ plan_success
              ↓
     ┌─────────────────┐
     │     READY       │ ←──────────────────┐
     └────────┬────────┘                     │
              │ has_next_task                │
              ↓                              │
     ┌─────────────────┐                     │
     │ EXECUTING_TASK  │                     │
     └────────┬────────┘                     │
              │ task_done                    │
              ↓                              │
     ┌─────────────────┐                     │
     │   REVIEWING     │                     │
     └────────┬────────┘                     │
              │                              │
      ┌───────┴───────────────────────────┐  │
      │                                   │  │
      │ accept     retry    edit_graph  escalate
      │                                   │  │
      ↓                ↓          ↓       ↓  │
   [mark             RETRYING  EDITING  ESCALATING
  complete]           │ │       GRAPH     │  │
      │               │ │         │       │  │
      └───────────────┴─┴─────────┴───────┴──┘
                      all lead back to READY
              
     ┌─────────────────┐
     │  GENERATE_UI    │ ← When task_graph.is_finished()
     │     SCHEMA      │
     └────────┬────────┘
              │ schema_ready
              ↓
     ┌─────────────────┐
     │ UI_VALIDATION   │
     └────────┬────────┘
              │ valid
              ↓
     ┌─────────────────┐
     │   COMPLETING    │
     └────────┬────────┘
              │ response_ready
              ↓
     ┌─────────────────┐
     │      DONE       │ ← Exit (success)
     └─────────────────┘

     ┌─────────────────┐
     │    FALLBACK     │ ← On severe failures
     └────────┬────────┘
              │ fallback_ready
              ↓
     ┌─────────────────┐
     │      DONE       │ ← Exit (fallback)
     └─────────────────┘

     ┌─────────────────┐
     │     FAILED      │ ← Deadman timeout or unrecoverable
     └─────────────────┘
```

### 7.2 State Transition Table

| From State | Event | Guard | To State | Action |
|-----------|-------|-------|----------|--------|
| INITIALIZING | facts_ready | true | PLANNING | plan() |
| PLANNING | plan_success | graph_valid | READY | enqueue_tasks() |
| PLANNING | plan_failure | true | FAILED | emit_error() |
| READY | has_next_task | true | EXECUTING_TASK | pull_task() |
| READY | no_tasks | true | GENERATE_UI_SCHEMA | start_ui_gen() |
| EXECUTING_TASK | task_done | valid_output | REVIEWING | persist_output() |
| EXECUTING_TASK | timeout | retries < max | RETRYING | backoff() |
| EXECUTING_TASK | timeout | retries >= max | ESCALATING | escalate() |
| REVIEWING | accept | verified >= 0.8 | READY | mark_complete() |
| REVIEWING | retry | retries < max | RETRYING | adjust_params() |
| REVIEWING | edit_graph | edits < max_edits | EDITING_GRAPH | apply_edits() |
| REVIEWING | escalate | cloud_enabled | ESCALATING | insert_cloud_task() |
| REVIEWING | fallback | critical_failure | FALLBACK | synth_fallback() |
| RETRYING | backoff_done | true | EXECUTING_TASK | retry_task() |
| EDITING_GRAPH | edits_applied | true | READY | continue() |
| ESCALATING | escalation_ready | true | READY | continue() |
| FALLBACK | fallback_ready | true | DONE | emit_response() |
| GENERATE_UI_SCHEMA | schema_ready | true | UI_VALIDATION | validate_schema() |
| UI_VALIDATION | valid | true | COMPLETING | finalize() |
| UI_VALIDATION | invalid | true | FALLBACK | use_default_ui() |
| COMPLETING | response_ready | true | DONE | emit_sse_done() |
| ANY | watchdog_trigger | elapsed > deadman | FAILED | alert_sre() |

### 7.3 Reliability Engineering Layers

**1. Execution Safety Controller**
```python
class ExecutionSafetyController:
    def __init__(self):
        self.task_timeout_ms = 15000
        self.max_retries = 3
        self.max_tokens = 2000
        self.grace_period_ms = 2000
    
    def execute_with_safety(self, task, executor):
        watchdog = threading.Timer(
            (self.task_timeout_ms + self.grace_period_ms) / 1000,
            self._abort_task,
            args=[task.id]
        )
        watchdog.start()
        
        try:
            result = executor.run(task, timeout_ms=self.task_timeout_ms)
            watchdog.cancel()
            
            if not self._validate_output(result):
                raise InvalidOutputError()
            
            return result
            
        except TimeoutError:
            watchdog.cancel()
            if task.retries < self.max_retries:
                return self._retry_with_backoff(task, executor)
            else:
                return self._escalate_or_fallback(task)
```

**2. Circuit Breaker Layer**
```python
class CircuitBreaker:
    def __init__(self, name, failure_threshold=3, recovery_timeout=30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = None
    
    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                self.failure_count = 0
            else:
                raise CircuitBreakerOpenError(f"{self.name} circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                emit_alert(f"Circuit breaker {self.name} opened")
            
            raise e
```

**3. Task Graph Validator**
```python
class TaskGraphValidator:
    def __init__(self):
        self.max_depth = 30
        self.max_branching = 5
        self.max_iterations = 100
        self.max_edits_per_request = 12
    
    def validate(self, task_graph):
        # Check depth
        if task_graph.max_depth() > self.max_depth:
            raise GraphTooDeepError(f"Max depth {self.max_depth} exceeded")
        
        # Check branching
        for node in task_graph.nodes:
            if len(node.children) > self.max_branching:
                raise GraphTooWideError(f"Max branching {self.max_branching} exceeded")
        
        # Check for cycles
        if self._has_cycle(task_graph):
            raise CyclicGraphError("Task graph contains cycles")
        
        # Check total iterations
        if task_graph.estimated_iterations() > self.max_iterations:
            raise TooManyIterationsError(f"Max iterations {self.max_iterations} exceeded")
        
        return True
    
    def validate_edit(self, edit, task_graph):
        # Simulate edit
        test_graph = task_graph.copy()
        test_graph.apply_edit(edit)
        
        # Validate new graph
        return self.validate(test_graph)
```

**4. Cost & Credit Controller**
```python
class CostController:
    def __init__(self, user_id, user_tier):
        self.user_id = user_id
        self.user_tier = user_tier
        self.credits_db = get_credits_db()
        self.tier_limits = {
            'free': {'daily_cloud_calls': 10, 'monthly_cloud_calls': 100},
            'pro': {'daily_cloud_calls': 1000, 'monthly_cloud_calls': 10000},
            'enterprise': {'daily_cloud_calls': float('inf'), 'monthly_cloud_calls': float('inf')}
        }
    
    def check_and_deduct(self, action, estimated_cost):
        balance = self.credits_db.get_balance(self.user_id)
        limits = self.tier_limits[self.user_tier]
        
        # Check tier limits
        if action == 'cloud_llm_call':
            daily_usage = self.credits_db.get_daily_usage(self.user_id, action)
            if daily_usage >= limits['daily_cloud_calls']:
                raise DailyLimitExceededError(f"Daily cloud calls limit reached: {limits['daily_cloud_calls']}")
        
        # Check balance
        if balance < estimated_cost:
            raise InsufficientCreditsError(f"Balance: {balance}, Required: {estimated_cost}")
        
        # Deduct
        self.credits_db.deduct(self.user_id, estimated_cost, action)
        return True
```

**5. Deadman & Alerting**
```python
class DeadmanMonitor:
    def __init__(self, deadman_timeout_s=300):
        self.deadman_timeout_s = deadman_timeout_s
        self.active_requests = {}
    
    def start_monitoring(self, request_id, context):
        self.active_requests[request_id] = {
            'start_time': time.time(),
            'context': context,
            'last_heartbeat': time.time()
        }
        
        threading.Timer(
            self.deadman_timeout_s,
            self._check_deadman,
            args=[request_id]
        ).start()
    
    def heartbeat(self, request_id):
        if request_id in self.active_requests:
            self.active_requests[request_id]['last_heartbeat'] = time.time()
    
    def complete(self, request_id):
        if request_id in self.active_requests:
            del self.active_requests[request_id]
    
    def _check_deadman(self, request_id):
        if request_id not in self.active_requests:
            return  # Already completed
        
        req_info = self.active_requests[request_id]
        elapsed = time.time() - req_info['start_time']
        
        if elapsed > self.deadman_timeout_s:
            # Dump context for postmortem
            dump_path = self._dump_request_context(request_id, req_info['context'])
            
            # Alert SRE
            alert_sre(
                severity="HIGH",
                message=f"Deadman timeout triggered for {request_id}",
                dump_path=dump_path,
                elapsed_s=elapsed
            )
            
            # Mark as failed
            del self.active_requests[request_id]
```

### 7.4 Configuration Defaults

```yaml
# Reasoning State Machine Configuration
reasoning_state_machine:
  max_task_retries: 3
  task_timeout_ms: 15000
  deadman_timeout_s: 300
  max_graph_depth: 30
  max_graph_edits_per_request: 12
  verification_threshold: 0.75
  grace_period_ms: 2000

# Circuit Breakers
circuit_breakers:
  ollama:
    failure_threshold: 3
    recovery_timeout_s: 30
  openrouter:
    failure_threshold: 5
    recovery_timeout_s: 60

# Cost Control
cost_control:
  free_tier:
    daily_cloud_calls: 10
    monthly_cloud_calls: 100
    escalation_threshold_bonus: 0.20
  pro_tier:
    daily_cloud_calls: 1000
    monthly_cloud_calls: 10000
    escalation_threshold_bonus: 0.0
  enterprise_tier:
    daily_cloud_calls: unlimited
    monthly_cloud_calls: unlimited
    escalation_threshold_bonus: -0.10

# Task Graph Limits
task_graph:
  max_depth: 30
  max_branching: 5
  max_iterations: 100
  max_dynamic_tabs: 6
```

---

## 8. Planner & Task Graph

### 8.1 Task Node Schema

```python
@dataclass
class TaskNode:
    id: str                          # Unique identifier (e.g., "t_1")
    type: str                        # Task type (e.g., "compute_valuation")
    input_facts: List[str]           # Required fact keys from AgentFacts
    required_outputs: List[str]      # Expected output keys
    model_hint: str                  # Suggested model ("qwen3-4b", "cloud")
    timeout_ms: int = 15000          # Task-specific timeout
    retries: int = 0                 # Current retry count
    max_retries: int = 3             # Max retry attempts
    parallelizable: bool = False     # Can run in parallel with others
    dependencies: List[str] = []     # Task IDs that must complete first
    ui_hint: Optional[dict] = None   # UI generation metadata
    domain: Optional[str] = None     # Domain context
    cognitive_mode: Optional[str] = None  # Cognitive mode context

@dataclass
class UIHint:
    suggest_tab: str                 # Suggested UI tab name
    priority: int                    # 0-100, higher = more important
    premium_flag: bool = False       # Requires premium access
    ui_role: str = "panel"          # "panel" | "card" | "chart" | "map"
    ui_group: Optional[str] = None   # Group similar tabs together
```

### 8.2 Example Task Graph

```json
{
  "request_id": "a1b2c3d4e5f6",
  "domain": "real_estate",
  "cognitive_mode": "investment",
  "tasks": [
    {
      "id": "t_1",
      "type": "fetch_market_data",
      "input_facts": ["location", "timeframe"],
      "required_outputs": ["price_trend", "volume", "avg_days_on_market"],
      "model_hint": "qwen3-4b",
      "timeout_ms": 10000,
      "max_retries": 3,
      "parallelizable": true,
      "ui_hint": {
        "suggest_tab": "Market Trends",
        "priority": 80,
        "premium_flag": false,
        "ui_role": "chart"
      }
    },
    {
      "id": "t_2",
      "type": "compute_valuation",
      "input_facts": ["area_stats", "comps", "price_trend"],
      "required_outputs": ["estimated_value", "price_range", "confidence"],
      "model_hint": "qwen3-4b",
      "timeout_ms": 15000,
      "max_retries": 3,
      "dependencies": ["t_1"],
      "ui_hint": {
        "suggest_tab": "Investment Verdict",
        "priority": 100,
        "premium_flag": false,
        "ui_role": "card"
      }
    },
    {
      "id": "t_3",
      "type": "simulate_infra",
      "input_facts": ["infra_plans", "area_stats"],
      "required_outputs": ["infra_impact_summary", "timeline"],
      "model_hint": "cloud",
      "timeout_ms": 20000,
      "max_retries": 2,
      "dependencies": ["t_1"],
      "ui_hint": {
        "suggest_tab": "Infrastructure Impact",
        "priority": 60,
        "premium_flag": true,
        "ui_role": "panel"
      }
    }
  ],
  "max_edits": 12,
  "edit_count": 0
}
```

### 8.3 Planner Types

**Rule-Based Planner (Fast)**
```python
class RuleBasedPlanner:
    def __init__(self):
        self.templates = {
            'property_search': [
                {'type': 'fetch_listings', 'priority': 1},
                {'type': 'filter_by_criteria', 'priority': 2},
                {'type': 'rank_by_score', 'priority': 3}
            ],
            'analyze_area': [
                {'type': 'fetch_area_stats', 'priority': 1},
                {'type': 'compute_livability_score', 'priority': 2},
                {'type': 'identify_risks', 'priority': 3}
            ],
            'valuation': [
                {'type': 'fetch_comps', 'priority': 1},
                {'type': 'fetch_market_trend', 'priority': 1, 'parallelizable': True},
                {'type': 'compute_valuation', 'priority': 2, 'dependencies': ['fetch_comps', 'fetch_market_trend']}
            ]
        }
    
    def create_graph(self, intent, agent_facts, domain_context):
        template = self.templates.get(intent, [])
        tasks = []
        
        for i, task_template in enumerate(template):
            task = TaskNode(
                id=f"t_{i+1}",
                type=task_template['type'],
                input_facts=self._infer_input_facts(task_template, agent_facts),
                required_outputs=self._infer_outputs(task_template),
                model_hint="qwen3-4b",
                parallelizable=task_template.get('parallelizable', False),
                dependencies=task_template.get('dependencies', []),
                ui_hint=self._generate_ui_hint(task_template)
            )
            tasks.append(task)
        
        return TaskGraph(tasks=tasks, domain=domain_context.domain)
```

**LLM-Assisted Planner (Complex)**
```python
class LLMAssistedPlanner:
    def create_graph(self, query, agent_facts, domain_context):
        prompt = f"""
You are a task planner for Valora AI. Create a task graph to answer this query.

Query: {query}
Domain: {domain_context.domain}
Cognitive Mode: {domain_context.cognitive_mode}

Available Facts: {list(agent_facts.keys())}

Rules:
- Break into 3-10 tasks
- Each task: type, input_facts, required_outputs
- Mark parallelizable tasks
- Specify dependencies
- Add ui_hints (suggest_tab, priority, ui_role)

Output JSON only: {{"tasks": [...]}}
"""
        
        response = self.llm.generate(prompt, temperature=0.3, max_tokens=1500)
        task_data = json.loads(response)
        
        tasks = [TaskNode(**task) for task in task_data['tasks']]
        return TaskGraph(tasks=tasks, domain=domain_context.domain)
```

### 8.4 Graph Editing Operations

```python
class TaskGraph:
    def apply_edit(self, edit):
        if edit['op'] == 'insert':
            self.tasks.insert(edit['position'], TaskNode(**edit['task']))
            
        elif edit['op'] == 'replace':
            idx = self._find_task_index(edit['task_id'])
            self.tasks[idx] = TaskNode(**edit['task'])
            
        elif edit['op'] == 'remove':
            idx = self._find_task_index(edit['task_id'])
            del self.tasks[idx]
            
        elif edit['op'] == 'reorder':
            old_idx = self._find_task_index(edit['task_id'])
            task = self.tasks.pop(old_idx)
            self.tasks.insert(edit['new_position'], task)
        
        self.edit_count += 1
        self._log_edit(edit)
```

---

## 9. Intelligent Model Router

### 9.1 Routing Algorithm

```python
class IntelligentModelRouter:
    def __init__(self):
        self.model_perf_db = get_model_perf_db()
        self.thresholds = {
            'low': 0.34,
            'medium': 0.59,
            'high': 1.0
        }
        self.tier_adjustments = {
            'free': 0.20,
            'pro': 0.0,
            'enterprise': -0.10
        }
    
    def select_model(self, query, intent, user_tier, cloud_enabled, has_images=False):
        # 1. Compute base complexity score
        base_score = self._compute_complexity(query, intent)
        
        # 2. Apply learned bias
        learned_bias = self._get_learned_bias(intent)
        
        # 3. Apply tier adjustment
        tier_bonus = self.tier_adjustments.get(user_tier, 0.0)
        
        # 4. Final score
        final_score = base_score + learned_bias + tier_bonus
        final_score = max(0.0, min(1.0, final_score))  # Clamp to [0, 1]
        
        # 5. Route based on score
        if has_images:
            return self._select_vision_model(final_score, cloud_enabled)
        
        if final_score <= self.thresholds['low']:
            return {
                'model': 'qwen3:8b',
                'provider': 'ollama',
                'is_cloud': False,
                'complexity_score': final_score
            }
        
        elif final_score <= self.thresholds['medium']:
            if cloud_enabled:
                return {
                    'model': 'deepseek/deepseek-chat',
                    'provider': 'openrouter',
                    'is_cloud': True,
                    'complexity_score': final_score
                }
            else:
                return {
                    'model': 'qwen3:8b',
                    'provider': 'ollama',
                    'is_cloud': False,
                    'complexity_score': final_score,
                    'note': 'cloud_disabled'
                }
        
        else:  # High complexity
            if cloud_enabled:
                return {
                    'model': 'deepseek/deepseek-reasoner',
                    'provider': 'openrouter',
                    'is_cloud': True,
                    'complexity_score': final_score
                }
            else:
                return {
                    'model': 'qwen3:8b',
                    'provider': 'ollama',
                    'is_cloud': False,
                    'complexity_score': final_score,
                    'note': 'cloud_disabled_high_complexity'
                }
    
    def _compute_complexity(self, query, intent):
        score = 0.0
        
        # Intent-based scoring
        intent_weights = {
            'simulate': 0.35,
            'comparison': 0.35,
            'investment': 0.25,
            'valuation': 0.15,
            'analyze_area': 0.15,
            'property_search': 0.10,
            'navigate': 0.05
        }
        score += intent_weights.get(intent, 0.10)
        
        # Reasoning signals
        reasoning_patterns = [
            r'compare\s+\w+\s+(with|to|vs)',
            r'what\s+if',
            r'simulate',
            r'estimate\s+\w+\s+considering',
            r'analyze\s+.{20,}',  # Long analysis requests
            r'multiple\s+(criteria|factors)',
            r'trade[-\s]?off'
        ]
        
        for pattern in reasoning_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                score += 0.08
        
        # Query length
        word_count = len(query.split())
        if word_count > 30:
            score += 0.10
        elif word_count > 50:
            score += 0.15
        
        return min(score, 1.0)
    
    def _get_learned_bias(self, intent):
        # Query last 20 records for this intent
        records = self.model_perf_db.query(
            "SELECT model, latency_ms, success FROM model_perf WHERE intent = ? ORDER BY timestamp DESC LIMIT 20",
            (intent,)
        )
        
        if not records:
            return 0.0
        
        # Compute success rate and avg latency per model
        model_stats = {}
        for record in records:
            model = record['model']
            if model not in model_stats:
                model_stats[model] = {'successes': 0, 'total': 0, 'latencies': []}
            
            model_stats[model]['total'] += 1
            if record['success']:
                model_stats[model]['successes'] += 1
            model_stats[model]['latencies'].append(record['latency_ms'])
        
        # Compute bias
        # If local model has high success rate and low latency → negative bias (prefer local)
        # If local model has low success rate or high latency → positive bias (prefer cloud)
        
        if 'qwen3:8b' in model_stats:
            local_stats = model_stats['qwen3:8b']
            success_rate = local_stats['successes'] / local_stats['total']
            avg_latency = sum(local_stats['latencies']) / len(local_stats['latencies'])
            
            if success_rate > 0.9 and avg_latency < 3000:
                return -0.15  # Strong preference for local
            elif success_rate > 0.7 and avg_latency < 5000:
                return -0.05  # Slight preference for local
            elif success_rate < 0.5 or avg_latency > 8000:
                return 0.15   # Prefer cloud
        
        return 0.0
    
    def _select_vision_model(self, complexity_score, cloud_enabled):
        if cloud_enabled:
            return {
                'model': 'qwen/qwen2.5-vl-72b-instruct',
                'provider': 'openrouter',
                'is_cloud': True,
                'complexity_score': complexity_score
            }
        else:
            # Local vision model (if available)
            return {
                'model': 'llava:13b',
                'provider': 'ollama',
                'is_cloud': False,
                'complexity_score': complexity_score
            }
```

### 9.2 Model Performance Tracking

```python
class ModelPerformanceTracker:
    def __init__(self):
        self.db = get_model_perf_db()
        self._init_db()
    
    def _init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS model_perf (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                intent TEXT NOT NULL,
                complexity_score REAL,
                latency_ms INTEGER,
                success INTEGER,
                tokens_generated INTEGER,
                timestamp REAL,
                user_tier TEXT,
                cloud_enabled INTEGER
            )
        """)
        
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_intent 
            ON model_perf(model, intent, timestamp DESC)
        """)
    
    def record(self, model, intent, complexity_score, latency_ms, success, 
               tokens_generated, user_tier, cloud_enabled):
        self.db.execute("""
            INSERT INTO model_perf 
            (model, intent, complexity_score, latency_ms, success, 
             tokens_generated, timestamp, user_tier, cloud_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            model, intent, complexity_score, latency_ms, int(success),
            tokens_generated, time.time(), user_tier, int(cloud_enabled)
        ))
        self.db.commit()
```

### 9.3 Cloud Provider Priority

```python
CLOUD_MODELS = {
    'openrouter': {
        'reasoning_high': 'deepseek/deepseek-reasoner',
        'reasoning_medium': 'deepseek/deepseek-chat',
        'vision': 'qwen/qwen2.5-vl-72b-instruct'
    },
    'ollama_cloud': {
        'reasoning_high': 'deepseek-v3.2:cloud',
        'reasoning_medium': 'kimi-k2.5:cloud',
        'vision': 'qwen3-vl:235b-instruct-cloud'
    }
}

def get_cloud_model(capability, provider_preference='openrouter'):
    # Try OpenRouter first
    if os.getenv('OPENROUTER_API_KEY'):
        return CLOUD_MODELS['openrouter'][capability], 'openrouter'
    
    # Fallback to Ollama Cloud
    return CLOUD_MODELS['ollama_cloud'][capability], 'ollama_cloud'
```

---

## 10. Micro-Reasoners & Specialist Modes

### 10.1 Micro-Reasoner Pattern

**Principles:**
- Short, focused prompts (200-500 tokens)
- Strict JSON output contracts
- Single responsibility per reasoner
- Reference AgentFacts explicitly
- Return `MISSING_DATA` if facts unavailable

### 10.2 System Prompt Template

```python
MICRO_REASONER_PROMPT = """
SYSTEM:
You are Valora Micro-Reasoner in {mode} mode.

You receive:
- facts: JSON object from deterministic GIS agents
- task: JSON describing the specific task

Constraints:
1. Use ONLY values found in facts to produce numeric claims
2. If facts are missing required data, return {{"status": "MISSING_DATA", "missing_keys": [...]}}
3. Output MUST be valid JSON with these fields:
   - result: your main output
   - claims: list of verifiable claims [{{"type": "price|distance|count|spatial", "value": ..., "unit": ..., "source_fact": ...}}]
   - ui_summary: {{"title": "...", "bullets": [...], "confidence": 0.0-1.0}}
   - confidence: 0.0-1.0 (your confidence in the result)

Facts provided:
{facts_json}

Task:
{task_json}

Generate JSON response:
"""
```

### 10.3 Specialist Modes

| Mode | Use Case | System Prompt Focus | Example Output |
|------|----------|---------------------|----------------|
| `investment_analyst` | Property valuation, ROI | Financial analysis, risk assessment | `{"result": {"verdict": "BUY", "expected_roi": 0.12}, "confidence": 0.78}` |
| `gis_analyst` | Spatial analysis, location scoring | Geometry, distances, POI analysis | `{"result": {"walkability_score": 85}, "confidence": 0.92}` |
| `simulator` | What-if scenarios, projections | Scenario modeling, impact analysis | `{"result": {"price_impact": "+15%", "timeline": "2-3 years"}, "confidence": 0.65}` |
| `broker_pitch` | User-facing narratives | Persuasive, benefit-focused language | `{"result": {"pitch": "Prime location..."}, "confidence": 0.88}` |
| `policy_research` | Regulations, compliance | Legal accuracy, citation of sources | `{"result": {"regulations": [...]}, "confidence": 0.95}` |

### 10.4 Example Micro-Reasoner Execution

```python
def execute_micro_reasoner(task, agent_facts, mode='investment_analyst'):
    # Prepare prompt
    facts_json = json.dumps(agent_facts.to_dict(), indent=2)
    task_json = json.dumps({
        'type': task.type,
        'input_facts': task.input_facts,
        'required_outputs': task.required_outputs
    }, indent=2)
    
    prompt = MICRO_REASONER_PROMPT.format(
        mode=mode,
        facts_json=facts_json,
        task_json=task_json
    )
    
    # Call LLM
    response = llm.generate(
        prompt,
        temperature=0.3,
        max_tokens=1000,
        response_format='json'
    )
    
    # Parse and validate
    try:
        result = json.loads(response)
        
        # Check for MISSING_DATA
        if result.get('status') == 'MISSING_DATA':
            return {
                'status': 'MISSING_DATA',
                'missing_keys': result['missing_keys'],
                'action': 'insert_fetch_task'
            }
        
        # Validate schema
        assert 'result' in result
        assert 'claims' in result
        assert 'ui_summary' in result
        assert 'confidence' in result
        
        return result
        
    except (json.JSONDecodeError, AssertionError) as e:
        # Invalid output → trigger retry with stricter prompt
        return {
            'status': 'INVALID_OUTPUT',
            'error': str(e),
            'action': 'retry_with_strict_prompt'
        }
```

### 10.5 Output Contract

```json
{
  "result": {
    "estimated_value": 8500000,
    "price_range": [7800000, 9200000],
    "verdict": "FAIR_PRICE"
  },
  "claims": [
    {
      "type": "price",
      "claim": "Estimated value is ₹85L",
      "value": 8500000,
      "unit": "INR",
      "source_fact": "comps.avg_price_per_sqft",
      "verified": true,
      "confidence": 0.85
    },
    {
      "type": "spatial",
      "claim": "Metro station 900m away",
      "value": 900,
      "unit": "m",
      "source_fact": "spatial.nearest_metro",
      "verified": true,
      "confidence": 0.95
    }
  ],
  "ui_summary": {
    "title": "Fair Price — 78% Confidence",
    "bullets": [
      "Estimated value: ₹85L (range ₹78L-₹92L)",
      "Metro proximity: 900m",
      "Below area average by 5%"
    ],
    "confidence": 0.78
  },
  "confidence": 0.78
}
```

---

## 11. Truth Firewall & GIS Agents

### 11.1 Architecture

```
User Query
    ↓
┌─────────────────────────────────────────────┐
│         GIS AGENT ORCHESTRATOR              │
├─────────────────────────────────────────────┤
│ Intent → Agent Selection → Parallel Exec    │
└─────────────────────────────────────────────┘
    ↓
┌────────────┬─────────────┬───────────┬──────────────┬─────────┐
│  Geocoder  │   Spatial   │  Terrain  │  Property    │   RAG   │
├────────────┼─────────────┼───────────┼──────────────┼─────────┤
│ lat/lng    │ POI counts  │ elevation │ listings     │ vector  │
│ fuzzy      │ buffers     │ slope     │ price hist   │ search  │
│ matching   │ building    │ flood     │ market data  │ docs    │
│            │ density     │ risk      │              │         │
└────────────┴─────────────┴───────────┴──────────────┴─────────┘
    ↓
┌─────────────────────────────────────────────┐
│           AGENT FACTS (Typed)               │
├─────────────────────────────────────────────┤
│ {                                           │
│   "location": {...},                        │
│   "spatial": {...},                         │
│   "terrain": {...},                         │
│   "properties": [...],                      │
│   "context": {...}                          │
│ }                                           │
│ All values: timestamped, sourced, units     │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│         TRUTH FIREWALL (Verification)       │
├─────────────────────────────────────────────┤
│ LLM Output → Extract Claims → Verify        │
│ Against AgentFacts → Annotate verified      │
└─────────────────────────────────────────────┘
    ↓
Verified Response
```

### 11.2 GIS Agent Implementations

**Geocoder Agent**
```python
class GeocoderAgent:
    def __init__(self, world_db):
        self.db = world_db
    
    def resolve_location(self, query_location):
        # 1. Exact match
        result = self.db.query(
            "SELECT * FROM localities WHERE name = ? LIMIT 1",
            (query_location,)
        )
        
        if result:
            return self._format_location(result[0])
        
        # 2. Fuzzy match
        results = self.db.query(
            "SELECT * FROM localities WHERE name LIKE ? LIMIT 5",
            (f"%{query_location}%",)
        )
        
        if results:
            # Rank by similarity
            best_match = max(results, key=lambda r: self._similarity(query_location, r['name']))
            return self._format_location(best_match)
        
        # 3. Fallback: geocode via external API (Nominatim)
        lat, lng = self._geocode_external(query_location)
        return {
            'name': query_location,
            'lat': lat,
            'lng': lng,
            'source': 'external_geocode',
            'timestamp': time.time()
        }
```

**Spatial Agent**
```python
class SpatialAgent:
    def __init__(self, world_db):
        self.db = world_db
    
    def analyze_area(self, lat, lng, radius_m=1000):
        # POI counts
        pois = self.db.query("""
            SELECT category, COUNT(*) as count
            FROM pois
            WHERE ST_Distance(geom, ST_MakePoint(?, ?)) <= ?
            GROUP BY category
        """, (lng, lat, radius_m))
        
        # Building density
        buildings = self.db.query("""
            SELECT COUNT(*) as count, AVG(height) as avg_height
            FROM buildings
            WHERE ST_Distance(geom, ST_MakePoint(?, ?)) <= ?
        """, (lng, lat, radius_m))
        
        # Transport nodes
        transport = self.db.query("""
            SELECT type, MIN(ST_Distance(geom, ST_MakePoint(?, ?))) as distance
            FROM transport_nodes
            WHERE ST_Distance(geom, ST_MakePoint(?, ?)) <= ?
            GROUP BY type
        """, (lng, lat, lng, lat, radius_m * 3))
        
        return {
            'pois': {poi['category']: poi['count'] for poi in pois},
            'building_count': buildings[0]['count'],
            'avg_building_height': buildings[0]['avg_height'],
            'transport': {t['type']: t['distance'] for t in transport},
            'radius_m': radius_m,
            'timestamp': time.time(),
            'source': 'spatial_db'
        }
```

**Property Agent**
```python
class PropertyAgent:
    def __init__(self, property_db):
        self.db = property_db
    
    def search_listings(self, location, filters):
        query = """
            SELECT * FROM properties
            WHERE locality = ?
            AND bedrooms >= ?
            AND price BETWEEN ? AND ?
            ORDER BY price ASC
            LIMIT 50
        """
        
        results = self.db.query(query, (
            location,
            filters.get('min_bedrooms', 0),
            filters.get('min_price', 0),
            filters.get('max_price', 1e10)
        ))
        
        return {
            'listings': [self._format_property(p) for p in results],
            'count': len(results),
            'avg_price': sum(p['price'] for p in results) / len(results) if results else None,
            'timestamp': time.time(),
            'source': 'property_db'
        }
    
    def get_comps(self, lat, lng, property_type, radius_m=2000):
        query = """
            SELECT * FROM properties
            WHERE property_type = ?
            AND ST_Distance(geom, ST_MakePoint(?, ?)) <= ?
            AND sold_date > ?
            ORDER BY sold_date DESC
            LIMIT 10
        """
        
        six_months_ago = time.time() - (6 * 30 * 24 * 3600)
        
        results = self.db.query(query, (property_type, lng, lat, radius_m, six_months_ago))
        
        return {
            'comps': [self._format_property(p) for p in results],
            'avg_price_per_sqft': self._compute_avg_psf(results),
            'timestamp': time.time(),
            'source': 'property_db'
        }
```

**RAG Agent**
```python
class RAGAgent:
    def __init__(self, vector_db, embedding_model):
        self.vector_db = vector_db
        self.embedding_model = embedding_model
    
    def search_context(self, query, top_k=5):
        # Generate embedding
        query_embedding = self.embedding_model.encode(query)
        
        # Search FAISS index
        distances, indices = self.vector_db.search(query_embedding, top_k)
        
        # Retrieve documents
        docs = [self.vector_db.get_document(idx) for idx in indices]
        
        return {
            'documents': docs,
            'scores': distances.tolist(),
            'count': len(docs),
            'timestamp': time.time(),
            'source': 'rag_vector_db'
        }
```

### 11.3 AgentFacts Schema

```python
@dataclass
class AgentFacts:
    location: dict                # Geocoder output
    spatial: dict                 # Spatial analysis
    terrain: Optional[dict]       # Terrain data
    properties: Optional[list]    # Property listings
    rag_context: Optional[list]   # RAG documents
    city_intelligence: Optional[dict]  # Locality personality
    timestamp: float              # Generation time
    
    def to_dict(self):
        return {
            k: v for k, v in asdict(self).items()
            if v is not None
        }
    
    def to_context_string(self):
        """Serialize for LLM prompts"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
```

### 11.4 Truth Firewall (Fact Verifier)

```python
class FactVerifier:
    def __init__(self):
        self.tolerances = {
            'price': 0.15,      # ±15%
            'distance': 0.20,   # ±20%
            'count': 0.10,      # ±10%
            'percentage': 0.05  # ±5 percentage points
        }
    
    def verify(self, claims, agent_facts):
        results = []
        
        for claim in claims:
            verification = self._verify_claim(claim, agent_facts)
            results.append(verification)
        
        verified_count = sum(1 for r in results if r['verified'])
        
        return {
            'total_claims': len(claims),
            'verified': verified_count,
            'verified_ratio': verified_count / len(claims) if claims else 1.0,
            'status': self._compute_status(verified_count, len(claims)),
            'claims': results,
            'warnings': self._generate_warnings(results)
        }
    
    def _verify_claim(self, claim, agent_facts):
        claim_type = claim['type']
        claim_value = claim['value']
        source_fact_path = claim.get('source_fact', '')
        
        # Navigate to fact value
        fact_value = self._get_nested_value(agent_facts, source_fact_path)
        
        if fact_value is None:
            return {
                'claim': claim['claim'],
                'verified': False,
                'reason': 'fact_not_found',
                'confidence': 0.0
            }
        
        # Check tolerance
        tolerance = self.tolerances.get(claim_type, 0.10)
        
        if claim_type in ['price', 'distance', 'count']:
            diff_ratio = abs(claim_value - fact_value) / fact_value
            verified = diff_ratio <= tolerance
        else:
            verified = claim_value == fact_value
        
        return {
            'claim': claim['claim'],
            'verified': verified,
            'claim_value': claim_value,
            'fact_value': fact_value,
            'diff_ratio': diff_ratio if claim_type in ['price', 'distance', 'count'] else None,
            'confidence': 1.0 - diff_ratio if verified else 0.0
        }
    
    def _compute_status(self, verified, total):
        ratio = verified / total if total > 0 else 0
        
        if ratio >= 0.9:
            return 'verified'
        elif ratio >= 0.7:
            return 'mostly_verified'
        elif ratio >= 0.5:
            return 'partially_verified'
        else:
            return 'verification_failed'
```

---

## 12. UI Schema Builder

### 12.1 Purpose

Convert Task Graph + Results → Deterministic UI JSON Schema

**Goals:**
- Always include anchor "Overview" tab
- Map tasks to tabs via `ui_hint` metadata
- Limit to max 6 dynamic tabs (configurable)
- Generate sanitized previews for premium tabs
- Include provenance (source_tasks, fact_refs)
- Validate: no PII, stable structure

### 12.2 Generation Algorithm

```python
class UISchemaBuilder:
    def __init__(self):
        self.max_tabs = 6
        self.ui_min_priority = 20
    
    def generate(self, task_graph, task_results, agent_facts, user_tier, locale='en'):
        # 1. Generate anchor tab (always present)
        anchor = self._synthesize_overview(task_results, agent_facts)
        
        # 2. Collect tab candidates from tasks
        candidates = []
        for task in task_graph.tasks:
            if not task.ui_hint:
                continue
            
            if task.ui_hint['priority'] < self.ui_min_priority:
                continue
            
            result = task_results.get(task.id)
            if not result:
                continue
            
            candidates.append({
                'task': task,
                'hint': task.ui_hint,
                'summary': result.get('ui_summary'),
                'result': result
            })
        
        # 3. Deduplicate and merge similar tabs
        merged = self._deduplicate_merge(candidates)
        
        # 4. Select top N tabs
        sorted_candidates = sorted(merged, key=lambda c: c['hint']['priority'], reverse=True)
        selected = sorted_candidates[:self.max_tabs]
        
        # 5. Generate tab specs
        tabs = []
        for candidate in selected:
            tab = self._generate_tab_spec(candidate, user_tier, locale)
            tabs.append(tab)
        
        # 6. Validate and return
        ui_schema = {
            'request_id': task_graph.request_id,
            'ui_schema': {
                'anchor_tab': anchor,
                'tabs': tabs,
                'generated_at': datetime.utcnow().isoformat() + 'Z'
            }
        }
        
        self._validate_schema(ui_schema)
        return ui_schema
    
    def _synthesize_overview(self, task_results, agent_facts):
        # Generate verdict-style summary card
        # This is the primary view the user sees
        
        return {
            'id': 'overview',
            'label': 'Overview',
            'type': 'verdict_card',
            'content': {
                'title': self._generate_title(task_results),
                'verdict': self._compute_verdict(task_results),
                'confidence': self._aggregate_confidence(task_results),
                'key_insights': self._extract_key_insights(task_results),
                'quick_stats': self._format_quick_stats(agent_facts)
            },
            'source_tasks': [task_id for task_id in task_results.keys()],
            'premium': False
        }
    
    def _generate_tab_spec(self, candidate, user_tier, locale):
        hint = candidate['hint']
        summary = candidate['summary']
        result = candidate['result']
        
        # Check if premium and user doesn't have access
        is_premium = hint.get('premium_flag', False)
        has_access = user_tier in ['pro', 'enterprise'] or not is_premium
        
        tab = {
            'id': self._slugify(hint['suggest_tab']),
            'label': self._localize(hint['suggest_tab'], locale),
            'type': hint.get('ui_role', 'panel'),
            'source_tasks': [candidate['task'].id],
            'premium': is_premium
        }
        
        if has_access:
            # Full content
            tab['content'] = self._format_content(result, hint['ui_role'])
        else:
            # Sanitized preview
            tab['preview'] = self._make_sanitized_preview(summary, result)
        
        return tab
    
    def _make_sanitized_preview(self, summary, result):
        """Generate safe preview without revealing premium content"""
        
        if not summary:
            return {
                'text': 'Upgrade to view detailed analysis',
                'bullets': []
            }
        
        # Extract first sentence + 2-3 bullets
        title = summary.get('title', 'Analysis available')
        bullets = summary.get('bullets', [])[:3]
        
        # Scrub PII and sensitive data
        title = self._scrub_pii(title)
        bullets = [self._scrub_pii(b) for b in bullets]
        
        return {
            'text': title,
            'bullets': bullets
        }
    
    def _scrub_pii(self, text):
        """Remove PII from preview text"""
        # Remove emails, phone numbers, specific addresses
        text = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', '[email]', text)
        text = re.sub(r'\b\d{10}\b', '[phone]', text)
        text = re.sub(r'\b\d{5,6}\b', '[pincode]', text)
        return text
    
    def _deduplicate_merge(self, candidates):
        """Merge similar tab candidates"""
        merged = []
        seen_labels = set()
        
        for candidate in candidates:
            label = candidate['hint']['suggest_tab'].lower()
            
            if label in seen_labels:
                # Find existing and merge
                existing = next(c for c in merged if c['hint']['suggest_tab'].lower() == label)
                existing['result'] = self._merge_results(existing['result'], candidate['result'])
            else:
                merged.append(candidate)
                seen_labels.add(label)
        
        return merged
    
    def _validate_schema(self, ui_schema):
        """Ensure schema is valid and safe"""
        assert 'anchor_tab' in ui_schema['ui_schema']
        assert len(ui_schema['ui_schema']['tabs']) <= self.max_tabs
        
        # Check for PII in preview fields
        for tab in ui_schema['ui_schema']['tabs']:
            if 'preview' in tab:
                assert not self._contains_pii(tab['preview']['text'])
```

### 12.3 UI Schema Example

```json
{
  "request_id": "a1b2c3d4e5f6",
  "ui_schema": {
    "anchor_tab": {
      "id": "overview",
      "label": "Overview",
      "type": "verdict_card",
      "content": {
        "title": "Investment Verdict: Whitefield",
        "verdict": "BUY",
        "confidence": 0.82,
        "key_insights": [
          "Metro Phase 3 planned within 900m",
          "15% below area average price",
          "Strong rental demand (occupancy 92%)"
        ],
        "quick_stats": {
          "avg_price_psf": 7200,
          "metro_distance": 900,
          "school_count": 12
        }
      },
      "source_tasks": ["t_1", "t_2", "t_3"],
      "premium": false
    },
    "tabs": [
      {
        "id": "market-trends",
        "label": "Market Trends",
        "type": "chart",
        "source_tasks": ["t_1"],
        "premium": false,
        "content": {
          "chart_type": "line",
          "data": {
            "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
            "datasets": [
              {
                "label": "Avg Price (₹L)",
                "data": [75, 78, 76, 79, 82, 85]
              }
            ]
          }
        }
      },
      {
        "id": "infrastructure-impact",
        "label": "Infrastructure Impact",
        "type": "panel",
        "source_tasks": ["t_3"],
        "premium": true,
        "preview": {
          "text": "Metro Phase 3 impact analysis available",
          "bullets": [
            "Projected completion: 2027",
            "Expected price appreciation: 12-18%",
            "3 stations within 2km radius"
          ]
        }
      },
      {
        "id": "risk-analysis",
        "label": "Risk Analysis",
        "type": "panel",
        "source_tasks": ["t_4"],
        "premium": true,
        "preview": {
          "text": "Comprehensive risk assessment with mitigation strategies",
          "bullets": [
            "Flood risk: Low (elevation 920m)",
            "Legal compliance: Verified",
            "Market volatility: Moderate"
          ]
        }
      }
    ],
    "generated_at": "2026-02-14T12:30:00Z"
  }
}
```

---

## 13. Meta-Cognition & Adaptive UX

### 13.1 Purpose

System self-monitors and adapts UI/UX based on:
- Task-level confidence trends
- User engagement signals
- Session complexity
- Cost budget constraints

### 13.2 Monitoring Metrics

```python
class MetaCognition:
    def __init__(self):
        self.metrics = {
            'avg_confidence': 0.0,
            'verification_ratio': 0.0,
            'user_engagement_score': 0.0,
            'session_complexity': 0.0,
            'cost_consumed': 0.0
        }
        self.thresholds = {
            'low_confidence': 0.6,
            'low_verification': 0.7,
            'high_complexity': 0.7,
            'budget_warning': 0.8
        }
    
    def monitor(self, task, result, review, agent_facts):
        # Update metrics
        self.metrics['avg_confidence'] = self._update_average(
            self.metrics['avg_confidence'],
            result.get('confidence', 0.5)
        )
        
        verification = review.get('verification', {})
        self.metrics['verification_ratio'] = verification.get('verified_ratio', 1.0)
        
        self.metrics['session_complexity'] = self._compute_complexity(task)
        
        # Check for adaptation triggers
        if self.metrics['avg_confidence'] < self.thresholds['low_confidence']:
            self._suggest_clarification()
        
        if self.metrics['verification_ratio'] < self.thresholds['low_verification']:
            self._suggest_fetch_more_facts()
        
        if self.metrics['session_complexity'] > self.thresholds['high_complexity']:
            self._suggest_simplify_ui()
    
    def should_adapt_ux(self):
        return (
            self.metrics['avg_confidence'] < self.thresholds['low_confidence'] or
            self.metrics['verification_ratio'] < self.thresholds['low_verification']
        )
    
    def get_adjustments(self):
        adjustments = {}
        
        # Verbosity adjustment
        if self.metrics['avg_confidence'] < 0.5:
            adjustments['verbosity'] = 'detailed'  # Explain uncertainties
        else:
            adjustments['verbosity'] = 'concise'
        
        # UI complexity adjustment
        if self.metrics['user_engagement_score'] < 0.3:
            adjustments['ui_tabs'] = 'collapsed'  # Single summary tab
        else:
            adjustments['ui_tabs'] = 'expanded'
        
        # Verification display
        if self.metrics['verification_ratio'] < 0.7:
            adjustments['show_verification_tab'] = True
        
        return adjustments
```

### 13.3 Adaptive Actions

| Condition | Action | Implementation |
|-----------|--------|----------------|
| Low confidence across tasks | Insert clarification question | Add `clarify_user_intent` task |
| Low verification ratio | Add verification summary tab | Modify `ui_schema` |
| High complexity + free tier | Simplify UI, collapse tabs | Reduce `max_tabs` to 3 |
| Low engagement signals | Reduce verbosity, highlight key points | Adjust prompt temperature |
| Budget near limit | Switch to local models only | Force `cloud_enabled=False` |

---

## 14. Execution Engine

### 14.1 Architecture

```python
class ExecutionEngine:
    def __init__(self):
        self.worker_pool = ThreadPoolExecutor(max_workers=5)
        self.safety_controller = ExecutionSafetyController()
        self.circuit_breakers = {
            'ollama': CircuitBreaker('ollama', failure_threshold=3, recovery_timeout=30),
            'openrouter': CircuitBreaker('openrouter', failure_threshold=5, recovery_timeout=60)
        }
    
    def execute(self, task, agent_facts):
        # 1. Pre-checks
        self._validate_task(task)
        self._check_fact_availability(task, agent_facts)
        
        # 2. Route to appropriate executor
        if task.type.startswith('fetch_'):
            return self._execute_agent_task(task, agent_facts)
        elif task.type in ['compute_', 'analyze_', 'simulate_']:
            return self._execute_llm_task(task, agent_facts)
        else:
            return self._execute_custom_task(task, agent_facts)
    
    def _execute_llm_task(self, task, agent_facts):
        # Select model
        model_config = model_router.select_model(
            query=task.description,
            intent=task.type,
            user_tier=task.user_tier,
            cloud_enabled=task.cloud_enabled
        )
        
        # Get circuit breaker
        breaker = self.circuit_breakers[model_config['provider']]
        
        # Execute with safety
        def _call_llm():
            return micro_reasoner.execute(
                task=task,
                agent_facts=agent_facts,
                model=model_config['model'],
                provider=model_config['provider']
            )
        
        try:
            result = self.safety_controller.execute_with_safety(
                task,
                lambda t: breaker.call(_call_llm)
            )
            return result
            
        except CircuitBreakerOpenError:
            # Fallback to deterministic response
            return self._generate_fallback(task, agent_facts)
    
    def execute_parallel(self, tasks, agent_facts):
        """Execute parallelizable tasks"""
        futures = []
        
        for task in tasks:
            if task.parallelizable:
                future = self.worker_pool.submit(self.execute, task, agent_facts)
                futures.append((task.id, future))
        
        # Collect results
        results = {}
        for task_id, future in futures:
            try:
                results[task_id] = future.result(timeout=30)
            except Exception as e:
                results[task_id] = {'error': str(e), 'status': 'failed'}
        
        return results
```

### 14.2 SSE Streaming

```python
async def stream_sse_events(request_id, task_graph, agent_facts):
    # Connection status
    yield sse_event('status', {'content': 'Connected', 'request_id': request_id})
    
    # Intent detected
    yield sse_event('intent_detected', {
        'intent': task_graph.intent,
        'task_count': len(task_graph.tasks),
        'request_id': request_id
    })
    
    # Task execution loop
    for task in task_graph.tasks:
        # Model selection
        model_config = model_router.select_model(...)
        yield sse_event('model_selection', {
            'model': model_config['model'],
            'is_cloud': model_config['is_cloud'],
            'complexity_score': model_config['complexity_score'],
            'request_id': request_id
        })
        
        # Task progress
        yield sse_event('task_progress', {
            'task_id': task.id,
            'task_type': task.type,
            'status': 'executing',
            'request_id': request_id
        })
        
        # Execute task
        result = executor.execute(task, agent_facts)
        
        # Content streaming (if text generation)
        if 'content' in result:
            for chunk in result['content_chunks']:
                yield sse_event('content', {
                    'content': chunk,
                    'request_id': request_id
                })
        
        # Verification
        if 'claims' in result:
            verification = fact_verifier.verify(result['claims'], agent_facts)
            yield sse_event('verification', {
                'verification': verification,
                'request_id': request_id
            })
        
        # Task completion
        yield sse_event('task_progress', {
            'task_id': task.id,
            'status': 'completed',
            'request_id': request_id
        })
    
    # Pipeline metrics
    yield sse_event('pipeline_metrics', {
        'metrics': {
            'intent_ms': 5,
            'facts_ms': 120,
            'route_ms': 2,
            'llm_ms': 2800,
            'total_ms': 3100
        },
        'request_id': request_id
    })
    
    # Done
    yield sse_event('done', {
        'request_id': request_id,
        'success': True,
        'thinking_time': 3.1
    })
```

---

## 15. Fact Verification

(See section 11.4 for detailed implementation)

### 15.1 Verification Flow

```
LLM Output
    ↓
Extract Claims (regex + structured parsing)
    ↓
For each claim:
    ↓
    Identify claim type (price, distance, count, spatial, etc.)
    ↓
    Locate source fact in AgentFacts
    ↓
    Compare with tolerance (±15% price, ±20% distance, etc.)
    ↓
    Annotate: verified: true|false, confidence: 0.0-1.0
    ↓
Aggregate results
    ↓
Emit verification SSE event
```

### 15.2 Verification SSE Event

```json
{
  "type": "verification",
  "verification": {
    "total_claims": 5,
    "verified": 4,
    "verified_ratio": 0.8,
    "status": "mostly_verified",
    "claims": [
      {
        "claim": "Metro station 900m away",
        "verified": true,
        "claim_value": 900,
        "fact_value": 920,
        "diff_ratio": 0.022,
        "confidence": 0.978
      },
      {
        "claim": "Average price ₹85L",
        "verified": true,
        "claim_value": 8500000,
        "fact_value": 8600000,
        "diff_ratio": 0.012,
        "confidence": 0.988
      }
    ],
    "warnings": []
  },
  "request_id": "a1b2c3d4e5f6"
}
```

---

## 16. Data Layer

### 16.1 Database Architecture

```
┌─────────────────────────────────────────────────────┐
│              APPLICATION LAYER                      │
├─────────────────────────────────────────────────────┤
│ • FastAPI Routes                                    │
│ • GIS Agents                                        │
│ • Model Router                                      │
└─────────────────────────────────────────────────────┘
                         ↕
┌──────────────┬──────────────┬──────────────┬─────────────────┐
│   World DB   │  Terrain DB  │  Vector DB   │  Operational    │
│  (Spatial)   │  (PostGIS)   │  (FAISS)     │  (SQLite)       │
├──────────────┼──────────────┼──────────────┼─────────────────┤
│ • Buildings  │ • Heightmaps │ • Embeddings │ • Model Perf    │
│ • Properties │ • Tiles      │ • 77K docs   │ • Conversation  │
│ • POIs       │ • 33×33 grid │ • 384-dim    │ • Credits       │
│ • Transport  │              │              │ • Query Cache   │
│ • Roads      │              │              │ • User Auth     │
└──────────────┴──────────────┴──────────────┴─────────────────┘
```

### 16.2 Database Details

**World DB (SQLite + SpatialLite)**
```sql
CREATE TABLE buildings (
    id INTEGER PRIMARY KEY,
    geom GEOMETRY(Polygon),
    height REAL,
    floors INTEGER,
    locality TEXT
);

CREATE TABLE properties (
    id INTEGER PRIMARY KEY,
    geom GEOMETRY(Point),
    price INTEGER,
    bedrooms INTEGER,
    area_sqft REAL,
    locality TEXT,
    listing_date REAL,
    sold_date REAL
);

CREATE TABLE pois (
    id INTEGER PRIMARY KEY,
    geom GEOMETRY(Point),
    category TEXT,
    name TEXT
);

CREATE SPATIAL INDEX idx_buildings_geom ON buildings(geom);
CREATE SPATIAL INDEX idx_properties_geom ON properties(geom);
CREATE SPATIAL INDEX idx_pois_geom ON pois(geom);
```

**Terrain DB (PostgreSQL + PostGIS)**
```sql
CREATE TABLE terrain_tiles (
    tile_id TEXT PRIMARY KEY,
    lon_min REAL,
    lon_max REAL,
    lat_min REAL,
    lat_max REAL,
    heightmap JSONB,  -- 33×33 array
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_terrain_bbox ON terrain_tiles 
USING GIST (
    ST_MakeEnvelope(lon_min, lat_min, lon_max, lat_max, 4326)
);
```

**Model Performance DB (SQLite)**
```sql
CREATE TABLE model_perf (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,
    intent TEXT NOT NULL,
    complexity_score REAL,
    latency_ms INTEGER,
    success INTEGER,
    tokens_generated INTEGER,
    timestamp REAL,
    user_tier TEXT,
    cloud_enabled INTEGER
);

CREATE INDEX idx_model_intent ON model_perf(model, intent, timestamp DESC);
```

**Query Cache (Redis or SQLite)**
```python
# Redis preferred for distributed deployments
redis_client.setex(
    key=f"chat_cache:{query_hash}:{intent}",
    time=600,  # 10 minutes
    value=json.dumps(response)
)

# SQLite fallback for single-instance
CREATE TABLE query_cache (
    cache_key TEXT PRIMARY KEY,
    response TEXT,
    expires_at REAL
);
```

### 16.3 Connection Pooling

```python
class SQLiteConnectionPool:
    def __init__(self, db_path, pool_size=5):
        self.db_path = db_path
        self.pool_size = pool_size
        self.pool = queue.Queue(maxsize=pool_size)
        self.local = threading.local()
        
        # Initialize pool
        for _ in range(pool_size):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self.pool.put(conn)
    
    def get_connection(self):
        # Thread-local connection
        if not hasattr(self.local, 'conn'):
            self.local.conn = self.pool.get()
        return self.local.conn
    
    def release_connection(self, conn):
        self.pool.put(conn)
```

---

## 17. API Architecture

### 17.1 Endpoints

**Chat Endpoints**
```
POST /api/chat/stream         # SSE streaming (primary)
POST /api/chat                # Synchronous fallback
GET  /api/chat/history        # Conversation history
DELETE /api/chat/history      # Clear history
```

**User & Auth**
```
POST /api/auth/signup         # Create account
POST /api/auth/login          # Email/password login
POST /api/auth/logout         # Invalidate session
GET  /api/auth/me             # Current user profile
GET  /api/auth/tiers          # Subscription tiers
```

**Credits & Payments**
```
GET  /api/credits/{user_id}   # Credit balance
POST /api/credits/purchase    # Buy credits
POST /api/credits/upgrade     # Upgrade tier
GET  /api/credits/plans       # Available plans
POST /api/payments/subscribe  # Create subscription
POST /api/payments/verify     # Verify payment
```

**Admin**
```
GET  /api/admin/health        # System health
GET  /api/admin/status        # Full status (auth required)
POST /api/admin/run-tests     # Run test suite
GET  /api/admin/metrics       # Operational metrics
```

**Feedback**
```
POST /api/feedback/submit     # Submit feedback + earn credits
GET  /api/feedback/list       # User's feedback history
```

### 17.2 Request/Response Schemas

**Chat Request**
```json
{
  "messages": [
    {"role": "user", "content": "Find 2BHK in Whitefield under 80L"}
  ],
  "context": {
    "user_id": "user_123",
    "conversation_id": "conv_456",
    "llm_config": {
      "provider": "ollama",
      "local_model": "qwen3:8b",
      "cloud_enabled": false
    },
    "ui_preferences": {
      "verbosity": "concise",
      "show_provenance": true
    }
  }
}
```

**Chat Response (Non-Streaming)**
```json
{
  "request_id": "a1b2c3d4e5f6",
  "message": "I found 15 properties matching your criteria...",
  "dashboard": {
    "type": "property_search",
    "data": {...}
  },
  "ui_actions": [
    {"type": "show_map", "data": {...}},
    {"type": "show_list", "data": {...}}
  ],
  "facts": {
    "location": {...},
    "properties": [...],
    ...
  },
  "verification": {
    "total_claims": 3,
    "verified": 3,
    "status": "verified"
  },
  "metadata": {
    "intent": "property_search",
    "model": "qwen3:8b",
    "is_cloud": false,
    "thinking_time": 2.3,
    "pipeline_metrics": {...}
  }
}
```

### 17.3 Rate Limiting

**IP-Based (Middleware)**
```python
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host
    
    # Check burst limit
    if not rate_limiter.allow(ip, limit=200, window=3600):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded. Try again later."}
        )
    
    response = await call_next(request)
    return response
```

**Credits-Based (Endpoint)**
```python
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    user_id = request.context.user_id
    user_tier = get_user_tier(user_id)
    
    # Check daily limit
    if not credits_limiter.check_limit(user_id, user_tier, action='chat'):
        raise HTTPException(
            status_code=429,
            detail="Daily chat limit reached. Upgrade for more."
        )
    
    # Deduct credit
    credits_limiter.deduct(user_id, cost=1, action='chat')
    
    # Process request...
```

---

## 18. Resilience & Circuit Breakers

(See section 7.3 for detailed implementation)

### 18.1 Circuit Breaker States

```
CLOSED (normal operation)
    ↓ (failure_count >= threshold)
OPEN (reject all requests)
    ↓ (recovery_timeout elapsed)
HALF_OPEN (allow one test request)
    ↓ (success)
CLOSED
```

### 18.2 Fallback Strategy

```python
def _generate_fallback_response(task, agent_facts):
    """Generate deterministic response from facts only"""
    
    if task.type == 'property_search':
        properties = agent_facts.get('properties', [])
        return {
            'status': 'fallback',
            'message': f"Found {len(properties)} properties (LLM unavailable, showing facts only)",
            'properties': properties,
            'note': 'Narrative generation unavailable. Showing raw data.'
        }
    
    elif task.type == 'analyze_area':
        spatial = agent_facts.get('spatial', {})
        return {
            'status': 'fallback',
            'message': 'Area statistics (LLM unavailable)',
            'stats': spatial,
            'note': 'Analysis unavailable. Showing raw metrics.'
        }
    
    else:
        return {
            'status': 'fallback',
            'message': 'LLM temporarily unavailable. Please try again.',
            'facts': agent_facts
        }
```

---

## 19. Observability & Metrics

### 19.1 Metrics to Track

**Latency Metrics**
```python
metrics = {
    'intent_ms': 5,              # Intent classification
    'facts_ms': 120,             # GIS agent orchestration
    'route_ms': 2,               # Model selection
    'llm_ms': 2800,              # LLM generation
    'verification_ms': 15,       # Fact verification
    'ui_gen_ms': 50,             # UI schema generation
    'total_ms': 3100             # End-to-end
}
```

**Success Metrics**
```python
metrics = {
    'verification_pass_rate': 0.92,       # % of claims verified
    'model_success_rate': 0.95,           # % of LLM calls succeeding
    'cache_hit_ratio': 0.35,              # % of cache hits
    'avg_graph_edits_per_request': 1.2,   # Adaptive loop stability
    'circuit_breaker_open_rate': 0.002    # % of time breakers are open
}
```

**Cost Metrics**
```python
metrics = {
    'avg_tokens_per_request': 850,
    'cloud_escalation_rate': 0.15,  # % of requests using cloud
    'cost_per_request_usd': 0.003
}
```

### 19.2 Tracing with OpenTelemetry

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Initialize tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Add exporter
span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317"))
trace.get_tracer_provider().add_span_processor(span_processor)

# Usage
@tracer.start_as_current_span("gis_agent_orchestration")
def orchestrate_agents(query, intent):
    with tracer.start_as_current_span("geocoder"):
        location = geocoder.resolve(query)
    
    with tracer.start_as_current_span("spatial_analysis"):
        spatial = spatial_agent.analyze(location)
    
    # ...
    return agent_facts
```

### 19.3 Alerting Rules

```yaml
alerts:
  - name: high_verification_failure_rate
    condition: verification_pass_rate < 0.75
    severity: WARNING
    action: notify_slack
  
  - name: circuit_breaker_open
    condition: circuit_breaker_state == "OPEN"
    severity: CRITICAL
    action: page_oncall
  
  - name: high_graph_edit_rate
    condition: avg_graph_edits_per_request > 5
    severity: WARNING
    action: notify_slack
  
  - name: deadman_timeout
    condition: request_duration > 300s
    severity: CRITICAL
    action: dump_context_and_page
```

---

## 20. Security & Compliance

### 20.1 Authentication & Authorization

```python
# JWT-based auth
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.get_user(user_id)
    return user

# RBAC
def require_role(role: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user')
            if user.role != role:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### 20.2 Data Privacy

**PII Scrubbing**
```python
def scrub_pii_before_cloud(text):
    """Remove PII before sending to cloud LLMs"""
    
    # Email addresses
    text = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', '[EMAIL]', text)
    
    # Phone numbers
    text = re.sub(r'\b\d{10}\b', '[PHONE]', text)
    text = re.sub(r'\+\d{1,3}-\d{10}\b', '[PHONE]', text)
    
    # Aadhaar numbers
    text = re.sub(r'\b\d{4}\s\d{4}\s\d{4}\b', '[AADHAAR]', text)
    
    # Specific addresses (keep locality, scrub house number)
    text = re.sub(r'\b\d+,?\s+[A-Z][a-z]+\s+(Street|Road|Avenue)\b', '[ADDRESS]', text)
    
    return text
```

**Data Retention**
```python
# Auto-delete old data
def cleanup_old_data():
    # Conversation memory: 90 days
    db.execute("DELETE FROM conversation_memory WHERE timestamp < ?", 
               (time.time() - 90 * 24 * 3600,))
    
    # Model performance: 180 days
    db.execute("DELETE FROM model_perf WHERE timestamp < ?",
               (time.time() - 180 * 24 * 3600,))
    
    # Query cache: 10 minutes (handled by TTL)
    
    # Audit logs: 90 days (configurable per tenant)
    db.execute("DELETE FROM audit_logs WHERE timestamp < ?",
               (time.time() - 90 * 24 * 3600,))
```

### 20.3 Secrets Management

```bash
# Environment variables (.env)
OPENROUTER_API_KEY=sk-or-v1-...
JWT_SECRET=...
DATABASE_URL=...
REDIS_URL=...

# Production: Use Vault or AWS Secrets Manager
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='ap-south-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])
```

---

## 21. Testing Strategy

### 21.1 Test Suites

**Unit Tests**
```python
# tests/test_intent_router.py
def test_intent_classification():
    router = IntentRouter()
    
    assert router.classify("Find 2BHK in Whitefield") == 'property_search'
    assert router.classify("Analyze Koramangala for investment") == 'investment'
    assert router.classify("Compare Whitefield vs HSR") == 'comparison'

# tests/test_model_router.py
def test_complexity_scoring():
    router = IntelligentModelRouter()
    
    score = router._compute_complexity("Find 2BHK", "property_search")
    assert score <= 0.34  # Should route to local
    
    score = router._compute_complexity("Simulate metro impact on prices", "simulate")
    assert score >= 0.35  # Should consider cloud
```

**Integration Tests**
```python
# tests/test_valora_suite.py
def test_end_to_end_property_search():
    request = {
        "messages": [{"role": "user", "content": "Find 2BHK in Whitefield under 80L"}],
        "context": {"user_id": "test_user", "llm_config": {...}}
    }
    
    response = client.post("/api/chat", json=request)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data['metadata']['intent'] == 'property_search'
    assert 'properties' in data['facts']
    assert data['verification']['status'] == 'verified'
```

**Regression Tests**
```python
# tests/test_adaptive_loop.py
def test_no_runaway_graph_edits():
    # Ensure adaptive loop doesn't create infinite edits
    task_graph = create_test_graph()
    max_edits = 12
    
    edit_count = 0
    while not task_graph.is_finished():
        review = reviewer.self_check(...)
        if review.action == "edit_graph":
            edit_count += 1
        
        assert edit_count <= max_edits, "Runaway graph edits detected"
```

### 21.2 Test Coverage

```
Section                          Tests    Pass Rate
─────────────────────────────────────────────────────
Intent Classification            40       100%
Model Routing                    8        100%
Learning-Aware Routing           2        100%
API Endpoints                    7        71%
Slot Extraction                  3        100%
Stress Tests                     3        100%
Truth Firewall                   5        100%
Adaptive Loop                    4        100%
─────────────────────────────────────────────────────
TOTAL                           72        97.2%
```

---

## 22. Deployment Patterns

### 22.1 Single-Host (Development)

```
┌─────────────────────────────────────────────┐
│           Single EC2 Instance               │
├─────────────────────────────────────────────┤
│ • FastAPI (Uvicorn + Gunicorn)             │
│ • Ollama (qwen3:8b)                        │
│ • SQLite + SpatialLite                     │
│ • FAISS (in-process)                       │
│ • Redis (single instance)                  │
└─────────────────────────────────────────────┘
```

**Setup**
```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y spatialite-bin redis-server

# Install Ollama
curl https://ollama.ai/install.sh | sh
ollama pull qwen3:8b

# Install Python deps
pip install -r requirements.txt

# Run server
gunicorn server:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 22.2 Production (Kubernetes)

```
┌─────────────────────────────────────────────────────────────────┐
│                      KUBERNETES CLUSTER                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────┐   │
│  │  Chat API     │  │  Agents API   │  │  Executor API    │   │
│  │  (3 replicas) │  │  (2 replicas) │  │  (5 replicas)    │   │
│  └───────────────┘  └───────────────┘  └──────────────────┘   │
│                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────┐   │
│  │ Model Router  │  │ UI Builder    │  │  Admin API       │   │
│  │  (2 replicas) │  │  (2 replicas) │  │  (1 replica)     │   │
│  └───────────────┘  └───────────────┘  └──────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                 │
├─────────────────────────────────────────────────────────────────┤
│ • PostgreSQL (World DB + Terrain)                              │
│ • Redis Cluster (Cache + Session)                              │
│ • FAISS Nodes (Vector Search)                                  │
│ • S3 (Model checkpoints, UI schemas)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                      LLM LAYER                                  │
├─────────────────────────────────────────────────────────────────┤
│ • Ollama Node Pool (GPU nodes, qwen3:8b)                       │
│ • OpenRouter API (cloud fallback)                              │
└─────────────────────────────────────────────────────────────────┘
```

**Kubernetes Manifests**

```yaml
# chat-api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chat-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: chat-api
  template:
    metadata:
      labels:
        app: chat-api
    spec:
      containers:
      - name: chat-api
        image: valora/chat-api:v4.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: valora-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: valora-secrets
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

```yaml
# ollama-nodepool.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: ollama
spec:
  selector:
    matchLabels:
      app: ollama
  template:
    metadata:
      labels:
        app: ollama
    spec:
      nodeSelector:
        gpu: "true"
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        volumeMounts:
        - name: models
          mountPath: /root/.ollama
        resources:
          limits:
            nvidia.com/gpu: 1
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ollama-models-pvc
```

### 22.3 Auto-Scaling

```yaml
# executor-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: executor-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: executor-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: queue_depth
      target:
        type: AverageValue
        averageValue: "10"
```

---

## 23. File Structure

```
valora-ai/
├── backend/
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── model_router.py              # Intelligent model selection
│   │   ├── gis_agents.py                # GIS Agent Orchestrator
│   │   ├── domain_resolver.py           # Domain & cognitive mode detection
│   │   ├── planner.py                   # Task Graph planner
│   │   ├── adaptive_controller.py       # Adaptive Cognitive Loop
│   │   ├── micro_reasoners.py           # Micro-reasoner execution
│   │   ├── reviewer.py                  # Self-check / review logic
│   │   ├── ollama_client.py             # Local LLM client
│   │   ├── prompts.py                   # Intent-specific prompts
│   │   ├── rag_service.py               # FAISS vector search
│   │   ├── fact_verifier.py             # Truth Firewall
│   │   ├── ui_schema_builder.py         # Graph → UI schema
│   │   ├── meta_cognition.py            # Adaptive UX monitoring
│   │   └── credits_rate_limiter.py      # Credit system
│   ├── core/
│   │   ├── circuit_breaker.py           # Circuit breaker pattern
│   │   ├── sqlite_pool.py               # Thread-local connection pool
│   │   ├── reasoning_state_machine.py   # RSM supervisor
│   │   └── cache_layer.py               # Caching utilities
│   ├── search/
│   │   └── query_cache.py               # LRU+TTL cache
│   ├── middleware/
│   │   └── rate_limit.py                # IP-based rate limiting
│   ├── routes/
│   │   ├── chat_routes.py               # /api/chat endpoints
│   │   ├── auth_routes.py               # Authentication
│   │   ├── admin_routes.py              # Admin endpoints
│   │   ├── credits_routes.py            # Credit management
│   │   ├── payment_routes.py            # Payment webhooks
│   │   └── feedback_routes.py           # Feedback + rewards
│   ├── city_intelligence/               # Locality personality
│   ├── analyzers/                       # Area, building analysis
│   ├── auth/                            # JWT, user database
│   ├── tests/
│   │   ├── test_valora_suite.py         # Main test suite
│   │   ├── test_adaptive_loop.py        # Regression tests
│   │   └── test_results_complete.md     # Auto-generated report
│   ├── server.py                        # FastAPI app
│   ├── model_performance.db             # Learning-aware routing
│   └── requirements.txt
│
├── src/                                  # Frontend (React)
│   ├── components/
│   │   ├── chat/
│   │   │   ├── EnhancedChatPanel.jsx    # Main chat + SSE
│   │   │   ├── ChatInputBar.jsx         # Cloud toggle + input
│   │   │   └── WindsurfThinkingPanel.jsx # Task banner
│   │   ├── AdminPanel.jsx
│   │   └── AnalysisPanel.jsx
│   ├── spatial/
│   │   └── OnlineOSMMap.jsx             # Cesium 3D map
│   └── App.jsx
│
├── docs/
│   ├── architecture_v4.0.md             # This document
│   ├── api_reference.md                 # API documentation
│   ├── deployment_guide.md              # Deployment instructions
│   └── sre_runbook.md                   # Operational runbook
│
└── docker/
    ├── Dockerfile.api
    ├── Dockerfile.ollama
    └── docker-compose.yml
```

---

## 24. Configuration Reference

### 24.1 Environment Variables

```bash
# Backend
OPENROUTER_API_KEY=sk-or-v1-...
LOCAL_LLM_URL=http://127.0.0.1:11434/v1/chat/completions
LOCAL_LLM_MODEL=qwen3:8b

# Databases
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/valora
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Reasoning State Machine
RSM_MAX_TASK_RETRIES=3
RSM_TASK_TIMEOUT_MS=15000
RSM_DEADMAN_TIMEOUT_S=300
RSM_MAX_GRAPH_DEPTH=30
RSM_MAX_GRAPH_EDITS=12
RSM_VERIFICATION_THRESHOLD=0.75

# Model Router
ROUTER_THRESHOLD_LOW=0.34
ROUTER_THRESHOLD_MEDIUM=0.59
ROUTER_FREE_TIER_BONUS=0.20

# Circuit Breakers
CB_OLLAMA_THRESHOLD=3
CB_OLLAMA_RECOVERY_S=30
CB_OPENROUTER_THRESHOLD=5
CB_OPENROUTER_RECOVERY_S=60

# UI Schema Builder
UI_MAX_TABS=6
UI_MIN_PRIORITY=20

# Cache
CACHE_TTL_SECONDS=600
CACHE_MAX_SIZE=1000

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
ENABLE_METRICS=true
ENABLE_TRACING=true
```

### 24.2 Configuration File

```yaml
# config/production.yaml
system:
  environment: production
  log_level: INFO
  debug: false

reasoning_state_machine:
  max_task_retries: 3
  task_timeout_ms: 15000
  deadman_timeout_s: 300
  max_graph_depth: 30
  max_graph_edits_per_request: 12
  verification_threshold: 0.75
  grace_period_ms: 2000

model_router:
  default_provider: ollama
  thresholds:
    low: 0.34
    medium: 0.59
    high: 1.0
  tier_adjustments:
    free: 0.20
    pro: 0.0
    enterprise: -0.10

circuit_breakers:
  ollama:
    failure_threshold: 3
    recovery_timeout_s: 30
  openrouter:
    failure_threshold: 5
    recovery_timeout_s: 60

ui_schema_builder:
  max_tabs: 6
  ui_min_priority: 20
  enable_previews: true
  scrub_pii: true

cache:
  query_cache:
    ttl_seconds: 600
    max_size: 1000
  rag_cache:
    ttl_seconds: 3600
    max_size: 500

credits:
  tiers:
    free:
      daily_cloud_calls: 10
      monthly_cloud_calls: 100
      cost_per_chat: 1
    pro:
      daily_cloud_calls: 1000
      monthly_cloud_calls: 10000
      cost_per_chat: 0.5
    enterprise:
      daily_cloud_calls: unlimited
      monthly_cloud_calls: unlimited
      cost_per_chat: 0

observability:
  enable_metrics: true
  enable_tracing: true
  metrics_port: 9090
  traces_endpoint: "http://localhost:4317"
```

---

## 25. Appendices

### 25.1 System Prompts

**Planner Prompt**
```
SYSTEM:
You are the Valora Task Planner. Create an execution plan for this query.

Domain: {domain}
Cognitive Mode: {cognitive_mode}
Available Facts: {fact_keys}

Rules:
1. Break into 3-10 tasks
2. Each task needs: type, input_facts, required_outputs, ui_hint
3. Mark parallelizable tasks
4. Specify dependencies
5. Assign priority (0-100) for UI hints

Output JSON: {"tasks": [...]}
```

**Micro-Reasoner Prompt**
```
SYSTEM:
You are Valora Micro-Reasoner in {mode} mode.

Constraints:
- Use ONLY values from facts for numeric claims
- If facts missing, return {{"status": "MISSING_DATA", "missing_keys": [...]}}
- Output JSON: {{result, claims[], ui_summary, confidence}}

Facts: {facts_json}
Task: {task_json}
```

**Reviewer Prompt**
```
SYSTEM:
You are the Valora Reviewer. Evaluate task output.

Check:
1. Facts match (verify against agent_facts)
2. Cross-task consistency
3. Confidence level
4. Missing data

Output JSON: {{action: "accept|retry|edit_graph|escalate", reason, confidence, suggested_changes}}
```

### 25.2 Database Schemas

**Users Table**
```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    tier TEXT DEFAULT 'free',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

**Credits Table**
```sql
CREATE TABLE credits (
    user_id TEXT PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    daily_usage INTEGER DEFAULT 0,
    monthly_usage INTEGER DEFAULT 0,
    last_reset_daily TIMESTAMP,
    last_reset_monthly TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

**UI Schema Store**
```sql
CREATE TABLE ui_schemas (
    request_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    ui_schema JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX idx_ui_schemas_user ON ui_schemas(user_id, created_at DESC);
```

### 25.3 Glossary

| Term | Definition |
|------|------------|
| **AgentFacts** | Typed, timestamped, sourced data from deterministic GIS agents |
| **Adaptive Cognitive Loop** | Self-improving execution loop that can edit task graphs during runtime |
| **Circuit Breaker** | Resilience pattern that prevents cascading failures |
| **Cognitive Mode** | High-level execution strategy (analysis, plan, simulate, etc.) |
| **Domain Resolver** | Component that determines domain and cognitive mode from query |
| **Micro-Reasoner** | Small, focused LLM pass with strict input/output contract |
| **Reasoning State Machine** | Supervisor that enforces execution lifecycle and reliability |
| **Task Graph** | DAG of tasks with dependencies, metadata, and UI hints |
| **Truth Firewall** | Separation layer between deterministic facts and LLM reasoning |
| **UI Schema** | Deterministic JSON specification of UI layout derived from Task Graph |

---

## 26. Change Log

### v4.0 (2026-02-14) — Unified Production Release
- Consolidated three architecture documents into single unified version
- Added complete file structure and deployment patterns
- Expanded observability section with OpenTelemetry integration
- Added comprehensive configuration reference
- Included production-ready Kubernetes manifests
- Added detailed API reference with request/response schemas
- Expanded testing strategy with coverage metrics
- Added security & compliance section

### v3.3 (2026-02-14)
- Added Domain Resolver & Cognitive Modes
- Introduced 3-Layer Agent Brain
- Added Meta-Cognition & Adaptive UX
- Introduced UI Schema Builder (graph-driven UI)

### v3.1 (2026-02-14)
- Added Reasoning State Machine
- Introduced Reliability Engineering Layers
- Added circuit breakers, timeouts, deadman monitoring

### v3.0 (2026-02-14)
- Introduced Adaptive Cognitive Loop
- Added micro-reasoners pattern
- Expanded execution engine

### v2.0 (2026-02-13)
- Added Intelligent Model Router
- Introduced Truth Firewall
- Learning-aware routing with SQLite

### v1.0 (2026-02-10)
- Initial architecture
- Basic LLM integration
- GIS agents

---

## Final Notes

This unified v4.0 architecture document provides a complete, production-ready blueprint for Valora AI. Key next steps:

1. **Immediate Implementation Priorities**
   - Implement Reasoning State Machine supervisor
   - Build Domain Resolver
   - Create UI Schema Builder microservice
   - Add Meta-Cognition monitoring

2. **Operational Readiness**
   - Set up OpenTelemetry tracing
   - Configure circuit breakers with proper thresholds
   - Implement SRE runbook procedures
   - Set up alerting rules

3. **Documentation Deliverables**
   - API reference guide
   - Deployment guide with step-by-step instructions
   - SRE runbook with incident response procedures
   - Developer onboarding guide

4. **Testing & Quality Assurance**
   - Expand test coverage to 98%+
   - Add performance benchmarks
   - Create load testing suite
   - Set up CI/CD pipeline with automated testing

5. **Future Enhancements**
   - Multi-language support (UI Schema localization)
   - Advanced caching strategies (GraphQL-style field caching)
   - Model fine-tuning based on production data
   - Real-time collaboration features

---

**Document Version:** 4.0  
**Last Updated:** February 14, 2026  
**Maintained By:** Valora AI Architecture Team  
**License:** Proprietary

---

*End of Valora AI Production Architecture v4.0*