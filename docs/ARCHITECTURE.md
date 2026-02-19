# Valora Architecture
> **System Architecture, AI Components, and Developer Guide — February 2026**

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Architecture Overview](#2-architecture-overview)
3. [Intelligent Model Router](#3-intelligent-model-router)
4. [Core Components](#4-core-components)
5. [Enhanced Conversation System](#5-enhanced-conversation-system)
6. [UI Tab System & Monetization](#6-ui-tab-system--monetization)
7. [Task Graph Engine](#7-task-graph-engine)
8. [Resilience & Observability](#8-resilience--observability)
9. [API Reference](#9-api-reference)
10. [Data Layer](#10-data-layer)
11. [Testing](#11-testing)
12. [Configuration](#12-configuration)

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

- **Local-first**: Default `valora-2025v1` via Ollama — fast, free, always available
- **Cloud toggle**: User enables cloud in the UI → router auto-selects optimal cloud model
- **Cloud priority**: OpenRouter (primary) → Ollama Cloud (fallback)
- **Truth Firewall**: LLM only narrates verified facts from GIS agents — never invents data
- **Learning-aware**: SQLite tracks model latency/success → influences future selection

### 2.2 Request Flow

```
User Query  [request_id generated]
    ↓
┌──────────────────────────────────────────────────────────────┐
│  0. PRODUCTION PIPELINE SETUP                                │
│     CancellationToken for graceful shutdown                  │
│     TraceContext for request lifecycle tracking              │
│     ConnectionPool for HTTP session reuse                    │
├──────────────────────────────────────────────────────────────┤
│  1. INTENT CLASSIFICATION (IntentRouter + Confidence)        │
│     Pattern matching → LLM fallback for ambiguous queries    │
│     Returns confidence score (0.0-1.0) + secondary intent    │
│     Low confidence (< 0.6) → needs_clarification flag        │
├──────────────────────────────────────────────────────────────┤
│  1b. SEMANTIC CACHE CHECK (NEW)                              │
│     Embedding-based similarity matching (threshold: 0.92)    │
│     Finds cached responses for paraphrased queries           │
│     Cache hit → return stored response immediately           │
├──────────────────────────────────────────────────────────────┤
│  1c. EXACT CACHE CHECK (QueryCache)                          │
│     Exact query + intent match → instant response            │
├──────────────────────────────────────────────────────────────┤
│  1d. COLLECTIVE LEARNING CHECK (NEW)                         │
│     Get learned tool sequences for this intent               │
│     Check failure patterns to avoid                          │
│     Emit learning_insight SSE event                          │
├──────────────────────────────────────────────────────────────┤
│  2. GIS AGENTS (Parallel Fact Gathering - NEW)               │
│     Concurrent execution: Spatial · Terrain · Property       │
│     Dependency-aware task scheduling                         │
│     → Grounded facts from database (never LLM-generated)     │
│     → 3-4x faster for complex queries                        │
├──────────────────────────────────────────────────────────────┤
│  3. INTELLIGENT MODEL ROUTER (cost-aware + learning)         │
│     Query complexity scoring (0.0–1.0)                        │
│     + Cloud toggle check (cloud_enabled)                    │
│     + User tier adjustment (free → higher threshold)        │
│     + Learning bonus from SQLite perf tracker               │
│     → Selects: local qwen3 | Ollama cloud | OpenRouter      │
├──────────────────────────────────────────────────────────────┤
│  4. CIRCUIT BREAKER CHECK                                    │
│     Ollama / OpenRouter breaker → fallback if OPEN          │
├──────────────────────────────────────────────────────────────┤
│  5. LLM STREAMING (with Connection Pooling - NEW)            │
│     SSE events: intent → task_progress → model_selection   │
│     → thinking → content → verification → metadata → done   │
│     Shared aiohttp session for HTTP requests                 │
├──────────────────────────────────────────────────────────────┤
│  6. POST-LLM FACT VERIFICATION (Truth Firewall)             │
│     Extract claims → verify against GIS facts                │
│     → Emit verification SSE event                           │
├──────────────────────────────────────────────────────────────┤
│  7. LEARNING EVENT RECORDING (NEW)                           │
│     Record success/failure event with:                       │
│     - Query, intent, tools used, latency, confidence         │
│     - Store in collective_learnings table                    │
│     - Update semantic cache with response                    │
├──────────────────────────────────────────────────────────────┤
│  8. PERFORMANCE RECORDING + CACHE STORE                      │
│     model + intent + latency + success → SQLite             │
│     response → QueryCache (10-min TTL)                      │
│     response → SemanticCache (similarity-based)             │
│     pipeline_metrics + trace SSE event emitted               │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 Data Scale

| Metric | Count |
|--------|-------|
| Properties | 42,452 |
| Buildings | 686,370 |
| POIs | 26,961 |
| Transport Stops | 4,253 |
| Roads | 334,784 |
| Open Datasets | 455,066 |
| **Total** | **1.5M+** |

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
| 0.0 – 0.34 | Local `qwen3:4b-instruct` | 0.0 – 0.54 |
| 0.35 – 0.59 | Fastest cloud model (medium) | 0.55 – 0.79 |
| 0.60 – 1.0 | Best reasoning cloud model (high) | 0.80 – 1.0 |
| Images attached | Best vision model | Same |

**Cost-aware routing**: Free-tier users have thresholds raised by +0.20, so only truly complex queries escalate to cloud. This conserves their limited daily cloud credits.

### 3.3 Model Strategy

**Local Models (Ollama):**
| Model | VRAM | Purpose |
|-------|------|---------|
| `valora-2025v1` | 4.0 GB | General execution (default) |
| `phi-4` | 4.8 GB | Specialist planner, validation, valuation, legal |

**Cloud Models (for heavy reasoning):**
- **OpenRouter**: `deepseek/deepseek-chat`, `deepseek/deepseek-reasoner`, `qwen/qwen2.5-vl-72b-instruct`
- **Ollama Cloud**: `kimi-k2.5:cloud`, `deepseek-v3.2:cloud`, `qwen3-vl:235b-instruct-cloud`

**Sequential Model Management** (`backend/ai/sequential_model_manager.py`):
- Only one model loaded at a time (6GB VRAM constraint)
- Automatic switching with SSE notifications
- 4-second switch overhead
- `valora-2025v1` for general tasks
- `phi-4` for specialist tasks (valuation, validation, legal, compliance)

### 3.4 Cloud Toggle (Frontend)

`src/components/chat/ChatInputBar.jsx` has a toggle that sets `llm_config.cloud_enabled`:
- **OFF** (default): Only local models available to router
- **ON**: Router can escalate to cloud models based on complexity

### 3.5 Learning-Aware Routing

**File:** `storage/database/model_performance.db` (SQLite)

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
| Ollama (local) | `ai/ollama_client.py` | Default `valora-2025v1`, specialist `phi-4`, port 11434 |
| OpenRouter | `routes/chat_routes.py` (`_stream_openrouter`) | Cloud streaming via API |

### 4.3 Backend File Structure

```
backend/
├── ai/
│   ├── model_router.py             # Intelligent model selection (learning-aware)
│   ├── gis_agents.py              # GIS Agent Orchestrator + IntentRouter
│   ├── ollama_client.py            # Local LLM (Ollama)
│   ├── unified_valora_brain.py    # Main brain integration
│   ├── brain_task_integration.py   # Brain + task execution
│   ├── production_task_planner.py  # Task planning and execution
│   ├── task_decomposer.py         # Task decomposition
│   ├── task_orchestrator.py        # Task orchestration
│   ├── multi_stage_executor.py     # Multi-stage execution
│   ├── sequential_model_manager.py # Sequential model management
│   ├── task_monitor.py            # Task monitoring
│   ├── task_graph.py              # Task graph management
│   ├── task_templates.py           # Task templates
│   ├── prompts.py                 # Intent-specific system prompts
│   ├── systematic_prompts.py      # Systematic prompt engineering
│   ├── decomposition_prompts.py    # Decomposition prompts
│   ├── response_templates.py       # Response templates
│   ├── rag_service.py             # FAISS vector search + embeddings
│   ├── fact_verifier.py           # Truth Firewall (post-LLM verification)
│   ├── tools_registry.py          # Dynamic tool system
│   ├── credits_rate_limiter.py    # Credit system
│   ├── pattern_learner.py          # Pattern learning
│   ├── self_learning.py            # Self-learning system
│   ├── enhanced_learning.py        # Enhanced learning engine (NEW)
│   ├── query_pipeline.py           # Production pipeline infrastructure (NEW)
│   ├── template_generator.py      # Template generation
│   ├── smart_tab_renderer.py      # Smart tab rendering
│   ├── streaming_intent_classifier.py  # Streaming intent classification
│   ├── query_refiner.py           # Query refinement
│   ├── multimodal_reasoning.py    # Multimodal reasoning
│   ├── parallel_executor.py        # Parallel execution
│   ├── llm_health_monitor.py      # LLM health monitoring
│   ├── model_router.py            # Model routing
│   ├── agentic_loop.py            # Agentic loop
│   ├── agentic_memory.py          # Agentic memory
│   └── unified_credits.py        # Unified credits system
├── core/
│   ├── circuit_breaker.py         # Circuit breaker pattern for LLM calls
│   ├── sqlite_pool.py              # Thread-local SQLite connection manager
│   └── cache_layer.py             # Core caching utilities
├── database/
│   ├── db_service.py              # Core database service
│   ├── query_service.py           # Query execution
│   ├── connection_pool.py          # Connection pooling
│   ├── pricing_db.py              # Pricing database
│   ├── api_routes.py              # Database API routes
│   ├── ingest_geojson_data.py     # GeoJSON ingestion
│   ├── ingest_apify_properties.py # Apify property ingestion
│   ├── index_to_pinecone.py       # Pinecone indexing
│   └── apify_transformers.py      # Apify data transformers
├── search/
│   ├── hybrid_search.py           # Hybrid search
│   ├── vector_store.py            # Vector store
│   ├── query_cache.py             # Query caching
│   ├── incremental_indexer.py     # Incremental indexing
│   └── query_suggestions.py       # Query suggestions
├── middleware/
│   ├── rate_limit.py              # Rate limiting
│   ├── security_headers.py        # Security headers
│   ├── usage_middleware.py        # Usage tracking
│   └── validation.py              # Input validation
├── routes/
│   ├── chat_routes.py             # /api/chat + /api/chat/stream (primary)
│   ├── auth_routes.py             # Login, signup, user management
│   ├── admin_routes.py            # System status, config, tests
│   ├── credits_routes.py          # Credit balance, purchase, upgrade
│   ├── payment_routes.py         # Razorpay, Cashfree, Stripe webhooks
│   ├── feedback_routes.py         # Auto-save feedback + credit rewards
│   ├── database_routes.py         # Database management
│   ├── smart_report_routes.py     # Smart report generation
│   └── task_routes.py             # Task routes
├── analyzers/
│   ├── area_analyzer.py           # Area analysis
│   ├── building_analyzer.py       # Building analysis
│   ├── network_analyzer.py        # Network analysis
│   ├── raster_analysis.py         # Raster analysis
│   ├── temporal_analyzer.py       # Temporal analysis
│   ├── viewshed_analyzer.py       # Viewshed analysis
│   └── visual_analyzer.py         # Visual analysis
├── spatial/
│   ├── local_geocoder.py          # Local geocoding
│   ├── terrain_service.py         # Terrain service
│   ├── spatial_reasoning.py       # Spatial reasoning
│   ├── spatial_inference.py       # Spatial inference
│   ├── spatial_nlp.py             # Spatial NLP
│   ├── spatial_memory.py          # Spatial memory
│   ├── spatial_memory_graph.py   # Spatial memory graph
│   ├── spatial_3d_reasoning.py    # 3D spatial reasoning
│   └── advanced_analysis.py       # Advanced spatial analysis
├── city_intelligence/
│   ├── locality_personality.py    # Locality personality analysis
│   ├── risk_indexes.py           # Risk indexes
│   ├── causal_reasoning.py        # Causal reasoning
│   ├── prediction_schema.py       # Prediction schema
│   ├── knowledge_graph.py         # Knowledge graph
│   └── evolution_timeline.py     # Evolution timeline
├── intelligence/
│   ├── valuation_model.py         # Valuation model
│   ├── predictive_model.py        # Predictive model
│   ├── transaction_intelligence.py # Transaction intelligence
│   ├── narrative_generator.py     # Narrative generation
│   ├── regulatory_intelligence.py # Regulatory intelligence
│   └── simulation_engine.py       # Simulation engine
├── services/
│   ├── property_service.py       # Property service
│   ├── locality_service.py        # Locality service
│   ├── apify_service.py           # Apify service
│   ├── cache_manager.py           # Cache manager
│   ├── payment_service.py         # Payment service
│   └── enhanced_data_service.py   # Enhanced data service
├── scrapers/
│   ├── multi_source_scraper.py    # Multi-source scraping
│   └── production_ingestion.py   # Production ingestion
├── auth/
│   ├── auth.py                    # Authentication
│   ├── jwt_handler.py             # JWT handling
│   └── user_auth.py               # User authentication
├── monitoring/
│   ├── health_check.py            # Health checks
│   ├── observability.py           # Observability
│   └── eval_harness.py            # Evaluation harness
├── migrations/
│   └── ...                        # Database migrations
├── server.py                       # FastAPI app + router initialization
├── config.py                      # Configuration
├── logging_config.py              # Logging configuration
├── tool_executor.py               # Tool executor
├── usage_tracker.py               # Usage tracking
└── requirements.txt
```

### 4.4 Frontend File Structure

```
src/
├── components/
│   ├── MainApp.jsx                # Main application component
│   ├── AdminPanel.jsx             # Admin panel
│   ├── AnalysisPanel.jsx          # Area/building analysis display
│   ├── ChatPanel.jsx              # Main chat panel
│   ├── SmartTabsContainer.jsx     # Smart tabs container
│   ├── SmartTab.jsx               # Smart tab component
│   ├── TopTaskBanner.jsx          # Task banner
│   ├── LoginPage.jsx              # Login page
│   ├── SignupPage.jsx             # Signup page
│   ├── CreditBalance.jsx          # Credit balance display
│   ├── UsageDashboard.jsx         # Usage dashboard
│   ├── DatabasePanel.jsx          # Database management panel
│   ├── PropertyTypeScraper.jsx    # Property scraper
│   ├── EnhancedMultiSourceScraper.jsx # Multi-source scraper
│   ├── ScenarioSimulator.jsx      # Scenario simulation
│   ├── DrawingTools.jsx           # Map drawing tools
│   ├── ElevationChart.jsx         # Elevation chart
│   ├── PriceTimeSeriesChart.jsx   # Price time series
│   └── chat/
│       ├── EnhancedChatPanel.jsx  # Enhanced chat panel + SSE streaming
│       ├── ChatInputBar.jsx       # Cloud toggle + input
│       ├── ChatMessage.jsx        # Chat message display
│       ├── ChatSidebar.jsx        # Chat sidebar
│       ├── ChatSessionManager.jsx # Session management
│       ├── WindsurfThinkingPanel.jsx # Task banner + model display
│       ├── IntelligentAIThinking.jsx # AI thinking display
│       ├── AIThinkingTasks.jsx     # AI thinking tasks
│       └── MessageFeedback.jsx     # Message feedback
├── contexts/
│   └── AuthContext.jsx            # Authentication context
├── spatial/
│   └── OnlineOSMMap.jsx            # Cesium 3D map + terrain
├── utils/
│   └── performance.js             # Performance utilities
├── App.jsx                        # Root app component
├── main.jsx                       # Entry point
└── index.css                      # Global styles
```

---

## 5. Enhanced Conversation System

### 5.1 Overview

The Enhanced Conversation System provides intelligent, context-aware interactions with tiered analysis options, multi-language support, and personalized user experiences.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ENHANCED CONVERSATION FLOW                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  USER QUERY (any language)                                               │
│      │                                                                   │
│      ▼                                                                   │
│  ┌───────────────────────────┐                                          │
│  │  Multilingual Intent      │  • Hindi, Kannada, Tamil, Telugu, Malayalam
│  │  Detector                 │  • Script detection + transliteration     │
│  │  (multilingual_intent.py) │  • Mixed language support (Hinglish)      │
│  └───────────┬───────────────┘                                          │
│              │                                                           │
│              ▼                                                           │
│  ┌───────────────────────────┐                                          │
│  │  Conversation Memory      │  • Previous queries & locations           │
│  │  (conversation_memory.py) │  • User preferences & behavior            │
│  │                           │  • Pronoun resolution ("it", "there")     │
│  └───────────┬───────────────┘                                          │
│              │                                                           │
│              ▼                                                           │
│  ┌───────────────────────────┐                                          │
│  │  Analysis Opportunity     │  • Investment evaluation detection        │
│  │  Detector                 │  • Price trend inquiry detection          │
│  │  (analysis_opportunity_   │  • Area comparison detection              │
│  │   detector.py)            │  • 10 sub-intent types                    │
│  └───────────┬───────────────┘                                          │
│              │                                                           │
│              ▼                                                           │
│  ┌───────────────────────────┐      ┌────────────────────────┐         │
│  │  A/B Testing Manager      │◄────►│  User Segment          │         │
│  │  (prompt_ab_testing.py)   │      │  • NEW_USER            │         │
│  │                           │      │  • CASUAL_USER         │         │
│  │  • Multi-armed bandit     │      │  • ACTIVE_USER         │         │
│  │  • Variant tracking       │      │  • POWER_USER          │         │
│  └───────────┬───────────────┘      └────────────────────────┘         │
│              │                                                           │
│              ▼                                                           │
│  ┌───────────────────────────┐                                          │
│  │  Tiered Options Builder   │                                          │
│  │                           │                                          │
│  │  • Quick Overview (Free)  │  ← Basic area summary                    │
│  │  • Area Analysis (3 cr)   │  ← Detailed neighborhood insights        │
│  │  • Investment Report (200)│  ← Comprehensive 9-section analysis      │
│  └───────────┬───────────────┘                                          │
│              │                                                           │
│              ▼                                                           │
│  ┌───────────────────────────┐                                          │
│  │  Frontend Components      │                                          │
│  │                           │                                          │
│  │  • TieredOptionsDisplay   │  ← Clickable option cards                │
│  │  • OnboardingModal        │  ← New user preferences                  │
│  │  • ChatInputBar (lang)    │  ← Language selector                     │
│  │  • Glow effect (15s)      │  ← New response notification             │
│  └───────────────────────────┘                                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Tiered Analysis Options

| Tier | Credits | Description | Includes |
|------|---------|-------------|----------|
| **Quick Overview** | 0 (Free) | Basic area summary | Location highlights, Key amenities, Price range |
| **Area Analysis** | 3 | Detailed neighborhood insights | Full amenity analysis, Connectivity score, Price trends |
| **Investment Report** | 200 | Comprehensive 9-section analysis | Executive summary, Market analysis, Risk assessment, ROI projections |

### 5.3 Sub-Intent Detection

| Sub-Intent | Example Query |
|------------|---------------|
| `INVESTMENT_EVALUATION` | "Is Hebbal good for investment?" |
| `PRICE_TREND_INQUIRY` | "What's the price trend in Whitefield?" |
| `AREA_COMPARISON` | "Compare HSR Layout and Indiranagar" |
| `ROI_INQUIRY` | "What ROI can I expect in JP Nagar?" |
| `MARKET_OUTLOOK` | "How is the market in Electronic City?" |
| `AREA_LIVABILITY` | "Is Koramangala good for families?" |
| `EXPLICIT_REPORT` | "Generate report for Hebbal" |

### 5.4 Multi-Language Support

**Supported Languages:**
| Language | Code | Script Detection |
|----------|------|------------------|
| English | `en` | Latin |
| Hindi | `hi` | Devanagari (हिन्दी) |
| Kannada | `kn` | Kannada (ಕನ್ನಡ) |
| Tamil | `ta` | Tamil (தமிழ்) |
| Telugu | `te` | Telugu (తెలుగు) |
| Malayalam | `ml` | Malayalam (മലയാളം) |

**Example:**
```
User: "हेब्बल में निवेश अच्छा है?" (Hindi: Is Hebbal good for investment?)
System: Detects Hindi → Transliterates "हेब्बल" → "Hebbal" → Shows tiered options
```

### 5.5 Conversation Memory

**File:** `backend/ai/conversation_memory.py`

Stores per-user context:
- Last locations discussed
- Analysis types used
- User preferences (investment focus, budget range)
- Pronoun resolution ("it", "there", "that area")

**Example:**
```
User: "Is Hebbal good for investment?"
System: Stores Hebbal in session context
User: "What about schools there?"
System: Resolves "there" → Hebbal → Shows school information
```

### 5.6 Location Disambiguation

**File:** `backend/spatial/local_geocoder.py`

When location is ambiguous:
```
User: "How is the market in Richmond?"
System: "I found multiple locations:
        1. Richmond Town (Bangalore)
        2. Richmond Road (Bangalore)
        Which one would you like to analyze?"
```

### 5.7 A/B Testing for Prompts

**File:** `backend/ai/prompt_ab_testing.py`

Multi-armed bandit approach for prompt optimization:
- 10% exploration (random variant)
- 90% exploitation (best performing variant)
- Tracks: shown, clicked, converted events
- User segment-aware variants

### 5.8 New User Onboarding

**File:** `src/components/OnboardingModal.jsx`

4-step wizard collecting:
1. Primary interest (Investment/Rental/Commercial/Residential)
2. Preferred areas in Bangalore
3. Budget range
4. Language preference

### 5.9 Key Files

**Backend:**
| File | Purpose |
|------|---------|
| `backend/ai/conversation_memory.py` | Session context & pronoun resolution |
| `backend/ai/analysis_opportunity_detector.py` | Sub-intent detection & tiered options |
| `backend/ai/multilingual_intent.py` | Multi-language intent detection |
| `backend/ai/prompt_ab_testing.py` | A/B testing for prompts |
| `backend/spatial/local_geocoder.py` | Location disambiguation |

**Frontend:**
| File | Purpose |
|------|---------|
| `src/components/chat/TieredOptionsDisplay.jsx` | Tiered options UI |
| `src/components/OnboardingModal.jsx` | New user onboarding |
| `src/components/chat/ChatInputBar.jsx` | Language selector |
| `src/styles/chat-glow.css` | New response glow effect |

---

## 6. UI Tab System & Monetization

### 6.1 Tiered Tab Access

**File:** `src/components/SmartTabsContainer.jsx`

```javascript
const TIER_CONFIG = {
  free: {
    name: 'Free',
    tabs: {
      'decision_verdict': 'limited',      // Limited content
      'market_snapshot': 'limited',       // Limited content
      'spatial_intelligence': 'preview',  // Blurred preview
      'risk_analysis': 'locked',          // Locked
      'roi_projection': 'locked',         // Locked
      'comparables': 'locked',            // Locked
      'strategy': 'locked',               // Locked
      'client_pitch': 'locked'            // Locked
    }
  },
  pro: {
    name: 'Pro',
    tabs: {
      'decision_verdict': 'full',         // Full access
      'market_snapshot': 'full',          // Full access
      'spatial_intelligence': 'full',     // Full access
      'risk_analysis': 'full',            // Full access
      'roi_projection': 'full',           // Full access
      'comparables': 'full',              // Full access
      'strategy': 'full',                 // Full access
      'client_pitch': 'full'              // Full access
    }
  }
}
```

### 6.2 Tab Types

| Type | Behavior |
|------|----------|
| `limited` | Shows partial content with upgrade prompt |
| `preview` | Blurred content preview to entice upgrade |
| `locked` | Shows 🔒 icon with upgrade button |
| `full` | Complete access to all data |

### 6.3 Tab Definitions

| Tab ID | Free | Pro | Purpose |
|--------|------|-----|---------|
| **Decision Verdict** | Limited | Full | BUY/HOLD/AVOID + reasoning |
| **Market Snapshot** | Limited | Full | Price trends, demand/supply |
| **Spatial Intelligence** | Preview | Full | POIs, connectivity, walkability |
| **Risk Analysis** | 🔒 Locked | Full | Flood, legal, market risks |
| **ROI Projection** | 🔒 Locked | Full | 3-year scenarios |
| **Comparables** | 🔒 Locked | Full | Similar listings |
| **Strategy** | 🔒 Locked | Full | Entry/exit strategy |
| **Client Pitch** | 🔒 Locked | Full | Broker presentation |

### 6.4 Upgrade Flow

**File:** `src/components/SmartTab.jsx`

```jsx
// Locked tab shows upgrade prompt
if (isLocked) {
  return (
    <div className="smart-tab locked">
      <div className="locked-icon">🔒</div>
      <h3>{title}</h3>
      <ul className="upgrade-benefits">
        <li>Full analysis & insights</li>
        <li>ROI projections</li>
        <li>Risk assessment</li>
      </ul>
      <button onClick={onUpgrade} className="upgrade-button">
        Upgrade to Pro
      </button>
    </div>
  );
}
```

---

## 7. Task Graph Engine

### 7.1 Task Node Structure

**File:** `backend/ai/task_graph.py`

```python
@dataclass
class TaskNode:
    id: str
    type: str
    model_hint: Optional[str] = None
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)
    timeout_ms: int = 15000
    retries: int = 0
    max_retries: int = 3
    provenance: dict = field(default_factory=dict)
```

### 7.2 Task Dependency Graph

```python
class TaskDependencyGraph:
    """Manages task dependencies and execution order"""
    
    def add_task(self, task: TaskNode):
        """Add task to graph"""
        
    def get_ready_tasks(self) -> List[TaskNode]:
        """Get tasks ready to execute (dependencies satisfied)"""
        
    def mark_complete(self, task_id: str):
        """Mark task as complete, update dependencies"""
        
    def get_parallel_groups(self) -> List[List[TaskNode]]:
        """Group tasks that can run in parallel"""
```

### 7.3 Task Graph Builder

```python
class TaskGraphBuilder:
    """Fluent API for building task graphs"""
    
    def add_task(self, task_type: str, model_hint: str = None) -> "TaskGraphBuilder":
        """Add a task to the graph"""
        
    def with_dependency(self, depends_on: str) -> "TaskGraphBuilder":
        """Add dependency to last task"""
        
    def build(self) -> TaskDependencyGraph:
        """Build the final graph"""
```

---

## 8. Resilience & Observability

### 8.1 Circuit Breakers

**File:** `backend/core/circuit_breaker.py`

Protects against cascading failures when LLM providers are down.

| Breaker | Threshold | Recovery |
|---------|-----------|----------|
| `ollama` | 3 failures | 30s timeout |
| `openrouter` | 5 failures | 60s timeout |

States: **CLOSED** → (failures exceed threshold) → **OPEN** → (recovery timeout) → **HALF_OPEN** → (success) → **CLOSED**

When open, requests fall back to `_generate_fallback_response()` which synthesizes a basic response from grounded facts only.

### 8.2 Chat Response Cache

**File:** `backend/search/query_cache.py` → `get_chat_cache()`

- Keyed on `query + intent` (avoids stale cross-intent hits)
- LRU eviction with 10-minute TTL
- Wired into both `/api/chat` and `/api/chat/stream`
- Cache hits skip the entire LLM pipeline (facts + routing + streaming)
- Cache stores: message, dashboard, ui_actions, facts, verification

### 5.3 Post-LLM Fact Verification

**File:** `backend/ai/fact_verifier.py`

After LLM generates a response, the Truth Firewall extracts verifiable claims (prices, distances, counts, spatial, sunlight, zoning) and checks them against the grounded facts already gathered by GIS agents.

- Emits a `verification` SSE event with: total claims, verified count, status, warnings
- Included in the `metadata` event and cached responses
- Tolerances: 15% for prices, 20% for distances, 10% for counts

### 5.4 SQLite Connection Pooling

**File:** `backend/core/sqlite_pool.py`

Thread-local connection manager preventing `database is locked` errors.

| Pool Name | Database | Consumers |
|-----------|----------|-----------|
| `model_perf` | `model_performance.db` | Model router |
| `agentic_memory` | `agentic_memory.db` | Agentic loop |
| `credits` | `valora_credits.db` | Credits rate limiter |
| `users` | `users.db` | Authentication |
| `memory` | `valora_memory.db` | Conversation memory |

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

## 8. API Reference

### 6.1 Chat Endpoints

**Streaming (primary):**
```http
POST /api/chat/stream
Content-Type: application/json

{
  "messages": [{"role": "user", "content": "Find 2BHK in Whitefield"}],
  "context": {
    "user_id": "user_123",
    "llm_config": {"provider": "ollama", "local_model": "valora-2025v1", "cloud_enabled": false}
  }
}
```

**SSE Events:**
```
data: {"type": "status", "content": "Connected"}
data: {"type": "intent_detected", "intent": "property_search", "task_graph": {...}}
data: {"type": "task_progress", ...}
data: {"type": "model_selection", "model": "valora-2025v1", "is_cloud": false, "complexity_score": 0.15}
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

### 6.2 Analysis Endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/area/analyze` | GET | Analyze area around coordinates (lng, lat, radius) |
| `/api/viewport/analyze` | GET | Quick viewport analysis for map center |
| `/api/building/analyze` | GET | Analyze building at coordinates |

### 6.3 Other Endpoints

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

## 9. Data Layer

### 7.1 Databases

All databases are **SQLite** (no PostgreSQL):

| Database | File | Purpose |
|----------|------|---------|
| Main DB | `valora.db` | Properties, POIs, buildings, transport, roads, terrain |
| Users | `users.db` | User accounts, sessions |
| Credits | `valora_credits.db` | Credit balances, payments, usage |
| Model Performance | `model_performance.db` | Learning-aware routing data |
| Agentic Memory | `agentic_memory.db` | Agentic loop memory |
| Valora Memory | `valora_memory.db` | Conversation memory |
| Self Learning | `self_learning.db` | Self-learning data |
| Enhanced Learning | `enhanced_learning.db` | Cross-session learning, A/B tests, failure patterns |
| Query Patterns | `valora_patterns.db` | Learned query patterns |
| Pricing | `pricing.db` | Pricing data |

### 7.2 Main Database Tables

| Table | Count | Description |
|-------|-------|-------------|
| `properties` | 42,452 | Property listings |
| `buildings` | 686,370 | Building footprints |
| `pois` | 26,961 | Points of interest |
| `transport_stops` | 4,253 | Transit stops |
| `roads` | 334,784 | Road segments |
| `places` | - | Localities/areas |
| `property_analytics` | - | Property analytics |
| `terrain_grid` | - | Terrain elevation data |
| `terrain_elevation` | - | Terrain elevation points |

### 7.3 Terrain

- **Provider**: SQLite terrain tables (no external dependencies)
- **Coverage**: Bengaluru (77.15–78.30°E, 12.50–13.55°N)
- **Cache**: LRU 200 tiles (~4MB), 4 concurrent requests max
- **Exaggeration**: 0.5×–3.0× via UI slider

### 7.4 Vector Search

- **Technology**: FAISS (Facebook AI Similarity Search)
- **Dimensions**: 384-dimensional embeddings
- **Index**: `storage/pois.faiss`, `storage/properties.faiss`, `storage/places.faiss`, `storage/transport.faiss`

---

## 10. Testing

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

## 11. Configuration

### 9.1 Environment (`backend/.env`)

```bash
OPENROUTER_API_KEY=sk-or-v1-...     # Cloud LLM (optional)
LOCAL_LLM_URL=http://127.0.0.1:11434/v1/chat/completions
LOCAL_LLM_MODEL=valora-2025v1
JWT_SECRET=your-secret-key
```

### 9.2 Frontend Cloud Toggle

The `ChatInputBar` has a toggle button:
- **Local** (default): Only `valora-2025v1` (general) and `phi-4` (specialist) used, no cloud API calls
- **Cloud**: Model router auto-selects from local + cloud pool based on query complexity

No model dropdown — the intelligent router handles selection automatically.

---

## 12. Production Pipeline & Enhanced Learning (NEW)

### 12.1 Production Query Pipeline

**File:** `backend/ai/query_pipeline.py`

The production pipeline provides infrastructure improvements for robust query handling:

| Component | Class | Purpose |
|-----------|-------|---------|
| **Intent Confidence** | `IntentClassifierWithConfidence` | Returns confidence scores (0.0-1.0) for intent classification |
| **Request Tracing** | `RequestTrace`, `TraceContext` | Tracks timing for each pipeline stage |
| **Cancellation Tokens** | `CancellationToken` | Proper async cancellation with cleanup callbacks |
| **Connection Pooling** | `ConnectionPool` | Shared `aiohttp.ClientSession` with keep-alive |
| **Semantic Caching** | `SemanticCache` | Similarity-based cache matching (threshold: 0.92) |
| **Parallel Fact Gathering** | `ParallelFactGatherer` | Concurrent execution of independent agents |

### 12.2 Enhanced Learning Engine

**File:** `backend/ai/enhanced_learning.py`

Advanced self-learning capabilities beyond the base `self_learning.py`:

| Feature | Method | Description |
|---------|--------|-------------|
| **Collective Learning** | `get_collective_recommendations()` | Aggregates learnings across all users (anonymized) |
| **Semantic Clustering** | `discover_new_intent_patterns()` | Auto-discovers new intent categories from low-confidence queries |
| **Failure Avoidance** | `get_failure_avoidance()` | Returns patterns to avoid based on past failures |
| **A/B Testing** | `create_ab_experiment()`, `get_ab_test_variant()` | Framework for testing different approaches |
| **Improvement Tracking** | `get_improvement_trend()` | Tracks improvement metrics over time |
| **Entity Corrections** | `learn_entity_correction()` | Learns from entity extraction corrections |
| **Query Rewriting** | `get_query_rewriting_suggestions()` | Suggests successful rephrasings |

### 12.3 Enhanced Learning Database Schema

**File:** `enhanced_learning.db`

| Table | Purpose |
|-------|---------|
| `collective_learnings` | Aggregated patterns across users |
| `query_clusters` | Semantic clusters of similar queries |
| `cluster_members` | Individual queries in clusters |
| `failure_patterns` | Learned failure modes (timeouts, errors, low ratings) |
| `improvement_history` | Track improvement metrics over time |
| `ab_experiments` | A/B test configurations |
| `ab_outcomes` | A/B test results |
| `entity_corrections` | User corrections for entity extraction |
| `query_rewrites` | Successful query rephrasings |

### 12.4 Learning Event Flow

```
Query Received
    ↓
┌─────────────────────────────────────────────────────────────┐
│  1. Check Collective Recommendations                         │
│     → Get learned tool sequences for this intent            │
│     → Emit learning_insight SSE event                       │
├─────────────────────────────────────────────────────────────┤
│  2. Check Failure Avoidance                                 │
│     → Get patterns to avoid                                 │
│     → Log warnings if approaching known failures            │
├─────────────────────────────────────────────────────────────┤
│  3. Execute Query (with parallel fact gathering)            │
├─────────────────────────────────────────────────────────────┤
│  4. Record Learning Event                                   │
│     → Store in collective_learnings                         │
│     → Update semantic cache                                 │
│     → Track in improvement_history                          │
├─────────────────────────────────────────────────────────────┤
│  5. Periodic Analysis (background)                          │
│     → Discover new intent patterns                          │
│     → Promote A/B test winners                              │
│     → Calculate improvement trends                          │
└─────────────────────────────────────────────────────────────┘
```

### 12.5 SSE Events for Learning

New SSE events emitted during query processing:

```javascript
// Learning insight event
data: {
  "type": "learning_insight",
  "insight_type": "collective_recommendations",
  "recommendations": {
    "tool_sequence": ["geocode", "spatial", "market"],
    "success_rate": 0.92,
    "sample_count": 150
  }
}

// Failure avoidance event
data: {
  "type": "learning_insight",
  "insight_type": "failure_avoidance",
  "patterns_to_avoid": [
    {"pattern": "complex_simulation_timeout", "suggestion": "Use simpler model"}
  ]
}

// Done event with learning insights
data: {
  "type": "done",
  "learning_insights": {
    "collective_recommendations_used": true,
    "failure_patterns_avoided": 2
  }
}
```

---

*Valora AI — Production architecture with learning-aware model routing, circuit breakers, fact verification, request tracing, and enhanced self-learning. February 2026.*
