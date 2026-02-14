# Valora Architecture
> **System Architecture, AI Components, and Developer Guide — February 2026**

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Architecture Overview](#2-architecture-overview)
3. [Intelligent Model Router](#3-intelligent-model-router)
4. [Core Components](#4-core-components)
5. [Resilience & Observability](#5-resilience--observability)
6. [API Reference](#6-api-reference)
7. [Data Layer](#7-data-layer)
8. [Testing](#8-testing)
9. [Configuration](#9-configuration)

---

## 1. Quick Start

```bash
# Backend
pip install -r backend/requirements.txt
cd backend && python server.py        # http://localhost:8000

# Frontend
npm install && npm run dev            # http://localhost:5173
```

Try: "Find 2BHK in Whitefield under 80L" or "Compare Koramangala vs HSR Layout"

---

## 2. Architecture Overview

### 2.1 Core Principle

> **Truth Firewall + Intelligent Model Routing + Learning-Aware Selection = Production AI**

- **Local-first**: Default `qwen3:8b` via Ollama — fast, free, always available
- **Cloud toggle**: User enables cloud in the UI → router auto-selects optimal cloud model
- **Cloud priority**: OpenRouter (primary) → Ollama Cloud (fallback)
- **Truth Firewall**: LLM only narrates verified facts from GIS agents — never invents data
- **Learning-aware**: SQLite tracks model latency/success → influences future selection

### 2.2 Request Flow

```
User Query  [request_id generated]
    ↓
┌──────────────────────────────────────────────────────────────┐
│  1. INTENT CLASSIFICATION (IntentRouter)                     │
│     Pattern matching → LLM fallback for ambiguous queries    │
├──────────────────────────────────────────────────────────────┤
│  1b. CACHE CHECK (QueryCache)                                │
│     Cache hit → return stored response immediately           │
├──────────────────────────────────────────────────────────────┤
│  2. GIS AGENTS (Deterministic Fact Gathering)                │
│     Geocoder · Spatial · Terrain · Property · RAG            │
│     → Grounded facts from database (never LLM-generated)    │
├──────────────────────────────────────────────────────────────┤
│  3. INTELLIGENT MODEL ROUTER (cost-aware)                    │
│     Query complexity scoring (0.0–1.0)                       │
│     + Cloud toggle check (cloud_enabled)                     │
│     + User tier adjustment (free → higher threshold)         │
│     + Learning bonus from SQLite perf tracker                │
│     → Selects: local qwen3:8b | Ollama cloud | OpenRouter   │
├──────────────────────────────────────────────────────────────┤
│  4. CIRCUIT BREAKER CHECK                                    │
│     Ollama / OpenRouter breaker → fallback if OPEN           │
├──────────────────────────────────────────────────────────────┤
│  5. LLM STREAMING                                            │
│     SSE events: intent → task_progress → model_selection     │
│     → thinking → content → verification → metadata → done    │
├──────────────────────────────────────────────────────────────┤
│  6. POST-LLM FACT VERIFICATION (Truth Firewall)              │
│     Extract claims → verify against GIS facts                │
│     → Emit verification SSE event                            │
├──────────────────────────────────────────────────────────────┤
│  7. PERFORMANCE RECORDING + CACHE STORE                      │
│     model + intent + latency + success → SQLite              │
│     response → QueryCache (10-min TTL)                       │
│     pipeline_metrics SSE event emitted                       │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 Data Scale

| Metric | Count |
|--------|-------|
| Properties | 42,452 |
| Buildings | 686,370 |
| POIs | 26,961 |
| Transport | 5,384 |
| Roads | 334,784 |
| **Total** | **1.6M+** |

---

## 3. Intelligent Model Router

**File:** `backend/ai/model_router.py`

### 3.1 How It Works

The router scores query complexity (0.0–1.0) using:
- **Intent type**: simulate/comparison/investment = heavy (+0.35), analyze/search/valuation = medium (+0.15)
- **Reasoning signals**: regex patterns for multi-step, financial, comparative queries
- **Image presence**: routes to vision models (+0.4)
- **Conversation depth**: long threads need more context
- **Learned bonus**: SQLite tracks success/latency per model+intent → ±0.3 adjustment

### 3.2 Escalation Thresholds

| Score Range | Action | Free-tier Adjusted |
|-------------|--------|--------------------|
| 0.0 – 0.34 | Local `qwen3:8b` | 0.0 – 0.54 |
| 0.35 – 0.59 | Fastest cloud model (medium) | 0.55 – 0.79 |
| 0.60 – 1.0 | Best reasoning cloud model (high) | 0.80 – 1.0 |
| Images attached | Best vision model | Same |

**Cost-aware routing**: Free-tier users have thresholds raised by +0.20, so only truly complex queries escalate to cloud. This conserves their limited daily cloud credits.

### 3.3 Cloud Provider Priority

1. **OpenRouter** (if `OPENROUTER_API_KEY` is set): `deepseek/deepseek-chat`, `deepseek/deepseek-reasoner`, `qwen/qwen2.5-vl-72b-instruct`
2. **Ollama Cloud** (fallback): `kimi-k2.5:cloud`, `deepseek-v3.2:cloud`, `qwen3-vl:235b-instruct-cloud`
3. **Local** (always available): `qwen3:8b`

### 3.4 Cloud Toggle (Frontend)

`ChatInputBar.jsx` has a toggle that sets `llm_config.cloud_enabled`:
- **OFF** (default): Only local models available to router
- **ON**: Router can escalate to cloud models based on complexity

### 3.5 Learning-Aware Routing

**File:** `backend/model_performance.db` (SQLite)

```sql
CREATE TABLE model_perf (
    model TEXT, intent TEXT, complexity_score REAL,
    latency_ms INTEGER, success INTEGER, tokens_generated INTEGER,
    timestamp REAL
);
```

After each query, the system records model performance. When selecting models, the router queries the last 20 records per model+intent and computes a bonus (−0.3 to +0.3) based on success rate and latency.

---

## 4. Core Components

### 4.1 GIS Agent Orchestrator (`ai/gis_agents.py`)

Deterministic agents that collect grounded facts.

**Intent Types:**
| Intent | Example |
|--------|---------|
| `navigate` | "Show me Indiranagar" |
| `analyze_area` | "Analyze Whitefield for livability" |
| `analyze_building` | "Analyze this building's shadow" |
| `property_search` | "Find 2BHK under 80L in Whitefield" |
| `valuation` | "Estimate value of 1200 sqft" |
| `terrain` | "Show terrain around Whitefield" |
| `comparison` | "Compare Koramangala vs HSR" |
| `simulate` | "What if metro comes to Whitefield?" |
| `investment` | "Best areas for investment" |
| `market_trend` | "Price trend in Koramangala" |

**GIS Agents:** Geocoder, Spatial, Terrain, Property, RAG, City Intelligence

### 4.2 LLM Clients

| Client | File | Purpose |
|--------|------|---------|
| Ollama (local) | `ai/ollama_client.py` | Default `qwen3:8b`, port 11434 |
| OpenRouter | `routes/chat_routes.py` (`_stream_openrouter`) | Cloud streaming via API |

### 4.3 File Structure

```
backend/
├── ai/
│   ├── model_router.py             # Intelligent model selection (learning-aware)
│   ├── gis_agents.py               # GIS Agent Orchestrator + IntentRouter
│   ├── ollama_client.py            # Local LLM (Ollama)
│   ├── prompts.py                  # Intent-specific system prompts
│   ├── rag_service.py              # FAISS vector search + embeddings
│   ├── fact_verifier.py            # Truth Firewall (post-LLM verification)
│   ├── tools_registry.py           # Dynamic tool system
│   └── credits_rate_limiter.py     # Credit system (thread-local SQLite)
├── core/
│   ├── circuit_breaker.py          # Circuit breaker pattern for LLM calls
│   ├── sqlite_pool.py             # Thread-local SQLite connection manager
│   └── cache_layer.py             # Core caching utilities
├── search/
│   └── query_cache.py             # LRU+TTL cache (RAG, property, chat)
├── middleware/
│   └── rate_limit.py              # IP-based burst/DDoS protection only
├── routes/
│   ├── chat_routes.py              # /api/chat + /api/chat/stream (primary)
│   ├── auth_routes.py              # Login, signup, user management
│   ├── admin_routes.py             # System status, config, tests
│   ├── credits_routes.py           # Credit balance, purchase, upgrade
│   ├── payment_routes.py           # Razorpay, Cashfree, Stripe webhooks
│   └── feedback_routes.py          # Auto-save feedback + credit rewards
├── city_intelligence/              # Locality personality, risk indexes
├── analyzers/                      # Area, building, terrain analysis
├── auth/                           # JWT auth, user database
├── tests/
│   ├── test_valora_suite.py        # Unified test suite (96.9% pass rate)
│   └── test_results_complete.md    # Auto-generated test report
├── server.py                       # FastAPI app + router initialization
├── model_performance.db            # Learning-aware routing data (SQLite)
└── requirements.txt
```

```
src/
├── components/
│   ├── chat/
│   │   ├── EnhancedChatPanel.jsx   # Main chat panel + SSE streaming
│   │   ├── ChatInputBar.jsx        # Cloud toggle + input
│   │   └── WindsurfThinkingPanel.jsx # Task banner + model display
│   ├── AdminPanel.jsx              # System admin
│   └── AnalysisPanel.jsx           # Area analysis display
├── spatial/
│   └── OnlineOSMMap.jsx            # Cesium 3D map + terrain
└── App.jsx
```

---

## 5. Resilience & Observability

### 5.1 Circuit Breakers

**File:** `core/circuit_breaker.py`

Protects against cascading failures when LLM providers are down.

| Breaker | Threshold | Recovery |
|---------|-----------|----------|
| `ollama` | 3 failures | 30s timeout |
| `openrouter` | 5 failures | 60s timeout |

States: **CLOSED** → (failures exceed threshold) → **OPEN** → (recovery timeout) → **HALF_OPEN** → (success) → **CLOSED**

When open, requests fall back to `_generate_fallback_response()` which synthesizes a basic response from grounded facts only.

### 5.2 Chat Response Cache

**File:** `search/query_cache.py` → `get_chat_cache()`

- Keyed on `query + intent` (avoids stale cross-intent hits)
- LRU eviction with 10-minute TTL
- Wired into both `/api/chat` and `/api/chat/stream`
- Cache hits skip the entire LLM pipeline (facts + routing + streaming)
- Cache stores: message, dashboard, ui_actions, facts, verification

### 5.3 Post-LLM Fact Verification

**File:** `ai/fact_verifier.py`

After LLM generates a response, the Truth Firewall extracts verifiable claims (prices, distances, counts, spatial, sunlight, zoning) and checks them against the grounded facts already gathered by GIS agents.

- Emits a `verification` SSE event with: total claims, verified count, status, warnings
- Included in the `metadata` event and cached responses
- Tolerances: 15% for prices, 20% for distances, 10% for counts

### 5.4 SQLite Connection Pooling

**File:** `core/sqlite_pool.py`

Thread-local connection manager preventing `database is locked` errors.

| Pool Name | Database | Consumers |
|-----------|----------|----------|
| `model_perf` | `model_performance.db` | Model router |
| `conversation_memory` | `conversation_memory.db` | Chat routes |
| `credits` | `valora_credits.db` | Credits rate limiter |

All connections use **WAL mode** + **5s busy timeout** for concurrent read/write.

### 5.5 Rate Limiting (Two Layers)

| Layer | File | Scope | Purpose |
|-------|------|-------|---------|
| **IP burst** | `middleware/rate_limit.py` | Per-IP, 200 req/hr | DDoS/abuse protection |
| **Credits** | `ai/credits_rate_limiter.py` | Per-user, tier-based | Business logic limits |

The middleware handles infrastructure protection only. Per-user accounting (daily/monthly limits, credit costs per action) lives in the credits system, checked inside chat endpoints.

### 5.6 Request Tracing

Every streaming request gets a 12-char `request_id` (UUID prefix) that is:
- Logged at each pipeline stage with timing
- Included in every SSE event (`request_id` field)
- Emitted as a `pipeline_metrics` event before `done`

**Metrics collected:** `intent_ms`, `facts_ms`, `route_ms`, `llm_ms`, `total_ms`, `model`, `provider`, `escalated`

---

## 6. API Reference

### 5.1 Chat Endpoints

**Streaming (primary):**
```http
POST /api/chat/stream
Content-Type: application/json

{
  "messages": [{"role": "user", "content": "Find 2BHK in Whitefield"}],
  "context": {
    "user_id": "user_123",
    "llm_config": {"provider": "ollama", "local_model": "qwen3:8b", "cloud_enabled": false}
  }
}
```

**SSE Events:**
```
data: {"type": "status", "content": "Connected"}
data: {"type": "intent_detected", "intent": "property_search", "task_graph": {...}}
data: {"type": "task_progress", ...}
data: {"type": "model_selection", "model": "qwen3:8b", "is_cloud": false, "complexity_score": 0.15}
data: {"type": "thinking", "content": "..."}
data: {"type": "content", "content": "I found 15 matching..."}
data: {"type": "metadata", "intent": "property_search", "dashboard": {...}, "ui_actions": [...]}
data: {"type": "verification", "verification": {"total_claims": 3, "verified": 2, "status": "partially_verified"}}
data: {"type": "pipeline_metrics", "metrics": {"intent_ms": 5, "facts_ms": 120, "route_ms": 2, "llm_ms": 2800, "total_ms": 3100}}
data: {"type": "done", "thinking_time": 3.1, "request_id": "a1b2c3d4e5f6"}
```

**Non-streaming:**
```http
POST /api/chat
```

### 5.2 Other Endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/admin/health` | GET | System health check |
| `/api/admin/status` | GET | Full system status (admin) |
| `/api/admin/run-tests` | POST | Run backend health tests (admin) |
| `/api/auth/login` | POST | Email/password login |
| `/api/auth/signup` | POST | Create account |
| `/api/auth/me` | GET | Current user profile |
| `/api/auth/tiers` | GET | Subscription tiers |
| `/api/credits/{user_id}` | GET | Credit balance |
| `/api/credits/plans` | GET | Subscription plans |
| `/api/credits/purchase` | POST | Buy credits |
| `/api/credits/upgrade` | POST | Upgrade tier |
| `/api/payments/subscribe` | POST | Create subscription |
| `/api/payments/verify` | POST | Verify payment |
| `/api/feedback/submit` | POST | Submit feedback + earn credits |

---

## 7. Data Layer

### 6.1 Databases

| Database | Tech | Purpose |
|----------|------|---------|
| World DB | SQLite + SpatialLite | 686K buildings, 42K properties, 27K POIs |
| Terrain | PostgreSQL | 33×33 heightmaps per tile |
| Vector Search | FAISS | 77K embeddings (384-dim) |
| Model Performance | SQLite | Learning-aware routing data |
| User Auth | SQLite | Users, sessions, usage logs |
| Credits | SQLite | Balances, payments, usage |

### 6.2 Terrain

- **Provider**: `DatabaseTerrainProvider` (native, no external dependencies)
- **Coverage**: Bengaluru (77.15–78.30°E, 12.50–13.55°N)
- **Cache**: LRU 200 tiles (~4MB), 4 concurrent requests max
- **Exaggeration**: 0.5×–3.0× via UI slider

---

## 8. Testing

**Run:**
```bash
cd backend
python -m tests.test_valora_suite          # Unit + integration tests
python -m tests.test_valora_suite --live   # + live LLM streaming
```

**Coverage (8 sections, 64 tests):**
| Section | Tests | Pass Rate |
|---------|-------|-----------|
| Intent Classification | 40 | 100% |
| Model Routing | 8 | 100% |
| Learning-Aware Routing | 2 | 100% |
| API Endpoints | 7 | 71% (2 infra issues) |
| Slot Extraction | 3 | 100% |
| Stress Tests | 3 | 100% |
| OpenRouter Config | 1 | 100% |
| **Total** | **64** | **96.9%** |

Report auto-generated at `backend/tests/test_results_complete.md`.

---

## 9. Configuration

### 8.1 Environment (`backend/.env`)

```bash
OPENROUTER_API_KEY=sk-or-v1-...     # Cloud LLM (optional)
LOCAL_LLM_URL=http://127.0.0.1:11434/v1/chat/completions
LOCAL_LLM_MODEL=qwen3:8b
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/valora
JWT_SECRET=your-secret-key
```

### 8.2 Frontend Cloud Toggle

The `ChatInputBar` has a toggle button:
- **Local** (default): Only `qwen3:8b` used, no cloud API calls
- **Cloud**: Model router auto-selects from local + cloud pool based on query complexity

No model dropdown — the intelligent router handles selection automatically.

---

*Valora AI — Production architecture with learning-aware model routing, circuit breakers, fact verification, and request tracing. February 2026.*
