# Valora AI - 3D Reasoning GIS Platform for Real Estate

**City Intelligence Platform | Version 2.7 | January 2026**

[![Status](https://img.shields.io/badge/Status-Production%20Ready-green)]()
[![AI](https://img.shields.io/badge/AI-16%20Intent%20Types-blue)]()
[![3D](https://img.shields.io/badge/3D-CesiumJS-orange)]()
[![Data](https://img.shields.io/badge/Records-1.6M+-purple)]()
[![Offline](https://img.shields.io/badge/Mode-Offline%20First-brightgreen)]()

---

## Overview

Valora AI is an **offline-first 3D GIS + AI reasoning platform** for real estate intelligence in Bangalore. It combines deterministic spatial analysis with LLM-powered narratives.

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **3D Visualization** | CesiumJS city model with 686K buildings |
| **AI Reasoning** | 16-intent multi-agent system with chain-of-thought |
| **Knowledge Layer** | 788 precomputed locality profiles |
| **Offline-First** | All data local, no external API dependencies |
| **Visual AI** | Qwen VL for multimodal spatial analysis |

### Data Summary

| Category | Records |
|----------|---------|
| Buildings | 686,370 |
| Properties | 42,452 |
| POIs | 26,961 |
| Roads | 334,784 |
| Transport Stops | 5,384 |
| Locality States | 788 |
| **Total** | **1.6M+** |

---

## 📚 Documentation

Complete documentation is available in the [`docs/`](./docs/) folder:

- **[docs/README.md](./docs/README.md)** - Documentation overview and navigation
- **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - Complete system architecture
- **[docs/AI_LLM.md](./docs/AI_LLM.md)** - Hybrid AI architecture details
- **[docs/PRODUCTION_DEPLOYMENT.md](./docs/PRODUCTION_DEPLOYMENT.md)** - Production deployment guide

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+
- **Python** 3.11+
- **Ollama** (for local LLMs)

### Installation

```bash
# Clone and install
git clone <repo-url>
cd windsurf-project

# Frontend
npm install

# Backend
pip install -r backend/requirements.txt
```

### Setup Ollama (Required)

```bash
# Install from https://ollama.ai, then:
ollama pull deepseek-r1:8b    # Primary reasoning model
ollama pull qwen3-vl:8b       # Visual/multimodal queries
ollama pull llama3.2          # Fast responses
ollama serve
```

### Run the Application

```bash
# Start both frontend and backend
npm run dev

# Or separately:
# Terminal 1 - Backend
cd backend && uvicorn server:app --reload --port 8000

# Terminal 2 - Frontend
npm run dev:frontend
```

**Access:** http://localhost:3000

---

## Cesium Ion Enhancements (Optional)

Valora supports **optional Cesium Ion upgrades** that are off by default and can be enabled later without changing core behavior.

### 1) Configure Ion Token (Frontend)

Set in `.env`:

```
VITE_CESIUM_TOKEN=your-cesium-ion-token
```

### 2) Available Ion Asset IDs

| Asset | ID | Description |
|-------|-----|-------------|
| **Cesium World Terrain** | `1` | Default terrain (always used) |
| **Google Photorealistic 3D** | `2275207` | Ultra-realistic 3D buildings/terrain |
| **Cesium OSM Buildings** | `96188` | Global 3D buildings from OSM |
| **Google Satellite** | `3830182` | High-res satellite imagery |
| **Google Satellite + Labels** | `3830183` | Satellite with place names |
| **Google Roadmap** | `3830184` | Street map layer |
| **Bing Aerial** | `2` | Bing satellite imagery |
| **Bing Aerial + Labels** | `3` | Bing satellite with labels |
| **Bing Road** | `4` | Bing street map |

Configure in `.env`:

```bash
# Core assets
VITE_CESIUM_ION_TERRAIN_ASSET_ID=1
VITE_CESIUM_ION_PHOTOREALISTIC_ASSET_ID=2275207
VITE_CESIUM_ION_OSM_BUILDINGS_ASSET_ID=96188

# Google imagery
VITE_CESIUM_ION_GOOGLE_SATELLITE_ASSET_ID=3830182
VITE_CESIUM_ION_GOOGLE_SATELLITE_LABELS_ASSET_ID=3830183
VITE_CESIUM_ION_GOOGLE_ROADMAP_ASSET_ID=3830184

# Bing imagery
VITE_CESIUM_ION_BING_AERIAL_ASSET_ID=2
VITE_CESIUM_ION_BING_AERIAL_LABELS_ASSET_ID=3
VITE_CESIUM_ION_BING_ROAD_ASSET_ID=4
```

### 3) Enable Ion Features (UI)

Go to **Layers panel** and toggle:

| Feature | Description |
|---------|-------------|
| **Photorealistic 3D (Ion)** | Google's photorealistic 3D tiles with 2GB in-memory cache |
| **OSM Buildings (Ion)** | Global OSM building models |
| **Ion Imagery Overlay** | Dropdown to select Google/Bing basemaps |

> All Ion features are **off by default**. Your existing basemap + terrain logic remain unchanged unless you enable these toggles.

### 4) Local Caching (Education Use)

For offline use or education purposes, you can self-host photorealistic tiles:

```bash
# Set local tileset URL in .env
VITE_LOCAL_PHOTOREALISTIC_TILESET_URL=/ion-cache/tileset.json
```

**See full guide:** [`docs/CESIUM_ION_LOCAL_CACHING.md`](docs/CESIUM_ION_LOCAL_CACHING.md)

**Features:**
- **Enhanced in-memory cache:** 2GB RAM, 5000 tiles (automatic)
- **Self-hosted tiles:** Capture and serve locally for offline demos
- **Service worker cache:** Browser-based persistent caching

⚠️ **License Notice:** Local caching is for education/research only. Commercial use requires proper licensing.

---

## LLM Configuration

Valora uses a **3-model local architecture** via Ollama (8B models are sufficient):

| Mode | Model | Use Case |
|------|-------|----------|
| 🧠 **Deep** | `deepseek-r1:8b` | Complex reasoning, simulations |
| 👁️ **Visual** | `qwen3-vl:8b` | Multimodal, image analysis |
| ⚡ **Fast** | `llama3.2` | Navigation, greetings |

Switch models in the ChatPanel using the mode selector.

**Config file:** `backend/llm_config.json`
```json
{
  "provider": "local",
  "local_url": "http://127.0.0.1:11434/v1/chat/completions",
  "local_model": "deepseek-r1:8b"
}
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     VALORA AI PLATFORM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FRONTEND                          BACKEND                      │
│  ┌──────────────┐                 ┌──────────────────────────┐ │
│  │ React 18     │                 │ FastAPI Server           │ │
│  │ CesiumJS 3D  │◄───────────────►│                          │ │
│  │ TailwindCSS  │                 │ ┌────────────────────┐   │ │
│  └──────────────┘                 │ │ GIS Orchestrator   │   │ │
│                                   │ │ - Intent Router    │   │ │
│  DATA LAYER                       │ │ - Fact Gathering   │   │ │
│  ┌──────────────┐                 │ │ - LLM Narrative    │   │ │
│  │ SQLite DB    │                 │ └────────────────────┘   │ │
│  │ - 1.6M recs  │◄───────────────►│                          │ │
│  │ FAISS Vector │                 │ ┌────────────────────┐   │ │
│  │ - 77K embeds │                 │ │ City Intelligence  │   │ │
│  └──────────────┘                 │ │ - Locality Profiles│   │ │
│                                   │ │ - Risk Indexes     │   │ │
│  LLM LAYER                        │ │ - Causal Reasoning │   │ │
│  ┌──────────────┐                 │ └────────────────────┘   │ │
│  │ Ollama Local │                 │                          │ │
│  │ - DeepSeek   │                 │ ┌────────────────────┐   │ │
│  │ - Qwen VL    │                 │ │ 3D Spatial         │   │ │
│  │ - Llama 3    │                 │ │ - Building Analyzer│   │ │
│  └──────────────┘                 │ │ - Viewshed Analysis│   │ │
│                                   │ │ - Shadow/View      │   │ │
│                                   │ └────────────────────┘   │ │
│                                   └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principle

> **LLM only narrates, never invents data.**  
> All facts come from deterministic agents. The LLM synthesizes narratives from grounded facts.

---

## AI Capabilities

### Intent Classification (16 Types)

| Category | Intent | Example |
|----------|--------|---------|
| **Conversational** | `greeting`, `help`, `thanks`, `farewell` | "Hi", "What can you do?" |
| **Navigation** | `navigate` | "Show me Whitefield" |
| **Property** | `property_search`, `recommendation` | "3BHK under 1 crore in HSR" |
| **Analysis** | `analyze_area`, `analyze_building`, `valuation`, `market_trend` | "Analyze Koramangala" |
| **Advanced** | `investment`, `comparison`, `simulate`, `terrain` | "Compare Whitefield vs Electronic City" |
| **General** | `general` | Catch-all for other queries |

### Property Search Filters

Natural language queries support advanced filtering:

| Filter | Examples |
|--------|----------|
| **Listing Type** | "for rent", "for sale" |
| **Property Category** | "PG", "office space", "plots" |
| **BHK** | "3BHK", "2 bedroom" |
| **Budget** | "under 80 lakhs", "below 1 crore" |
| **Commute Time** | "within 30 min of Whitefield" |

### Reasoning Features

- **Chain-of-Thought**: Step-by-step reasoning traces
- **Fact Verification**: Cross-validates data consistency
- **Confidence Scoring**: 0-100 confidence with warnings
- **Causal Analysis**: Infrastructure → Impact chains

---

## Enhanced Conversation System

Valora features an intelligent conversation system with multi-language support, context awareness, and tiered analysis options.

### Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Language Support** | Hindi, Kannada, Tamil, Telugu, Malayalam + English |
| **Conversation Memory** | Remembers previous queries, locations, and preferences |
| **Tiered Analysis** | Free, 3-credit, and 200-credit analysis options |
| **Smart Recommendations** | Proactive suggestions based on user behavior |
| **Location Disambiguation** | Clarifies ambiguous location names |
| **New User Onboarding** | 4-step preference collection wizard |

### Supported Query Types

| Query Pattern | Example | Detected Intent |
|--------------|---------|-----------------|
| Investment evaluation | "Is Hebbal good for investment?" | `INVESTMENT_EVALUATION` |
| Price trends | "What's the price trend in Whitefield?" | `PRICE_TREND_INQUIRY` |
| Area comparison | "Compare HSR Layout and Indiranagar" | `AREA_COMPARISON` |
| Multi-language | "हेब्बल में निवेश अच्छा है?" (Hindi) | `INVESTMENT_EVALUATION` |

### Tiered Analysis Options

| Tier | Credits | Description |
|------|---------|-------------|
| **Quick Overview** | Free | Basic area summary with key highlights |
| **Area Analysis** | 3 | Detailed neighborhood insights with POIs and connectivity |
| **Investment Report** | 200 | Comprehensive 9-section analysis with ROI projections |

### Example Flow

```
User: "Is Hebbal good for investment?"

Valora: I can help you evaluate Hebbal! What level of analysis would you like?

        🔍 Quick Overview (FREE)
        📊 Area Analysis (3 credits)
        📈 Investment Report (200 credits)
        
        Your balance: 50 credits

User: [Selects "Area Analysis"]

Valora: [Generates detailed area analysis for Hebbal]
```

### Key Implementation Files

| File | Purpose |
|------|---------|
| [`backend/ai/conversation_memory.py`](backend/ai/conversation_memory.py) | Session context & pronoun resolution |
| [`backend/ai/analysis_opportunity_detector.py`](backend/ai/analysis_opportunity_detector.py) | Sub-intent detection & tiered options |
| [`backend/ai/multilingual_intent.py`](backend/ai/multilingual_intent.py) | Multi-language intent detection |
| [`backend/ai/prompt_ab_testing.py`](backend/ai/prompt_ab_testing.py) | A/B testing for prompts |
| [`src/components/chat/TieredOptionsDisplay.jsx`](src/components/chat/TieredOptionsDisplay.jsx) | Tiered options UI |
| [`src/components/OnboardingModal.jsx`](src/components/OnboardingModal.jsx) | New user onboarding |

---

## Project Structure

```
windsurf-project/
├── backend/
│   ├── server.py              # FastAPI main server
│   ├── gis_agents.py          # Multi-agent orchestrator
│   ├── advanced_reasoning.py  # Chain-of-thought engine
│   ├── simulation_engine.py   # What-if scenarios
│   ├── building_analyzer.py   # 3D building analysis
│   ├── locality_service.py    # Fast locality lookups
│   ├── property_service.py    # Property queries
│   ├── valuation_model.py     # Price estimation
│   ├── local_vector_store.py  # FAISS offline vectors
│   ├── llm_config.json        # LLM provider settings
│   ├── city_intelligence/     # Urban analytics modules
│   └── database/              # SQLite service
│
├── src/
│   ├── components/
│   │   ├── MainApp.jsx        # Main app
│   │   ├── ChatPanel.jsx      # AI chat interface
│   │   ├── AdminPanel.jsx     # Config panel
│   │   └── AnalysisPanel.jsx  # Analysis dashboard
│   └── spatial/
│       └── Cesium3DMap.jsx    # 3D map component
│
├── scripts/
│   ├── sanity_check.py        # E2E API tests
│   └── build_locality_brain.py # Precompute localities
│
└── package.json
```

---

## Database Schema

**Database:** SQLite (`src/data/valora.db`)

| Table | Records | Purpose |
|-------|---------|---------|
| `properties` | 42,452 | Real estate listings |
| `buildings` | 686,370 | 3D building footprints |
| `pois` | 26,961 | Points of interest |
| `places` | 1,077 | Named localities |
| `transport_stops` | 5,384 | Metro/bus stops |
| `roads` | 334,784 | Road network |
| `locality_state` | 788 | Precomputed intelligence |

---

## API Endpoints

### Core APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | AI chat with GIS context |
| `/api/location/analyze` | POST | Location analysis |
| `/api/viewport/analyze` | GET | Quick viewport analysis |
| `/api/geocode` | GET | Geocode locations |
| `/api/tiles/viewport` | GET | 3D tiles for viewport |

### Intelligence APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/city-intelligence/locality/{name}` | GET | Locality profile |
| `/api/simulate` | POST | What-if simulation |
| `/api/building/analyze` | POST | 3D building analysis |
| `/api/valuation/estimate` | POST | Price estimation |
| `/api/investment/leaderboard` | GET | Top investment areas |

---

## Testing

### Run Sanity Check

```bash
# Quick check (no chat)
python scripts/sanity_check.py --no-chat

# Full check with AI chat
python scripts/sanity_check.py --include-chat
```

### Expected Results

```
VALORA AI - REALTIME SANITY CHECK
======================================
Total: 30 | Passed: 30 | Failed: 0
```

### Performance Benchmarks

| Operation | Time |
|-----------|------|
| Locality Lookup | <10ms |
| Intent Classification | <50ms |
| Property Search | 200-400ms |
| Area Analysis | 1-2s |
| Chat (cached) | <500ms |
| Chat (LLM) | 3-8s |

---

## Example Queries

```
# Navigation
"Show me Koramangala"
"Go to Whitefield"

# Property Search
"3BHK apartments in Indiranagar under 1.5 crore"
"PG for girls near Manyata Tech Park"
"Villas in Sarjapur Road"

# Analysis
"Analyze Hebbal for investment"
"Is Bellandur flood-prone?"
"Compare Whitefield vs Electronic City"

# Simulation
"What if metro comes to Sarjapur?"
"Impact of new IT park in Devanahalli"
```

---

## Next-Gen Vision: True 3D Reasoning AI

Valora's evolution follows this principle:

> **Next-gen 3D AI = Geometry + Simulation + Memory + Causal Models**  
> **The LLM is only the narrator and planner.**

### Current Architecture (Implemented)

| Layer | Status | Components |
|-------|--------|------------|
| **3D World Engine** | ✅ | 686K buildings, terrain, viewshed |
| **Simulation Engine** | ✅ | Causal graph, what-if scenarios |
| **Knowledge Layer** | ✅ | 788 locality profiles, risk indexes |
| **Reasoning Brain** | ✅ | Multi-agent, chain-of-thought |

### Roadmap: Dual-Track Next-Gen Agent (Both)

Valora is built to become both:

- **Real Estate Co-pilot** (buyers, investors, brokers)
- **City Operator / Simulator** (what-if planning, policy, infrastructure)

**Shared Foundation (required for both tracks):**

| Foundation Capability | Why it matters |
|----------------------|----------------|
| **Tool Schema + Validation** | Reliable LLM tool-calling; minimal hallucinations |
| **Spatial Memory Graph** | Fast relational queries: blocks view, shadows, overlooks, within-walk |
| **True Occlusion + Views (Polygon/LOS)** | Human-like 3D visibility: "what blocks my view?" |
| **Time-Aware Sun & Shadow Timeline** | Floor/face sunlight, seasonal comfort analysis |
| **Offline Eval Harness** | Regression tests for spatial correctness and latency |

**Track A — Real Estate Co-pilot:**

- **Transaction comps + time series** (true pricing intelligence)
- **Regulatory intelligence** (FAR/zoning/buffer/setback rules + risk flags)
- **Due diligence agent** (checklists grounded in Valora data)

**Track B — City Operator / Simulator:**

- **Scenario DSL + constraints** ("add metro here", "change FAR")
- **Counterfactual 3D impacts** (views, shadows, noise, access)
- **Digital twin updates + cinematic storyboards**

---

## Trust & Security Layer (NEW - Jan 2026)

### Fact Verifier ("Truth Firewall")

All LLM responses are automatically verified against deterministic data sources:

```
POST /api/verifier/verify          # Verify explicit claims
POST /api/verifier/verify-narrative # Extract & verify from text
GET  /api/verifier/status          # Service status
```

**Claim Types Verified:**
- `price` - Price/sqft, property values
- `distance` - Distances to landmarks, metros
- `count` - POI counts, property counts
- `spatial` - View quality, sky view factor
- `sunlight` - Daylight hours, natural light
- `zoning` - FAR limits, zone types

**Chat Response includes verification:**
```json
{
  "message": "...",
  "verification": {
    "status": "verified|unverified|partially_verified",
    "rate": 85.5,
    "results": [...]
  }
}
```

### Authentication & RBAC

API key authentication with role-based access:

```
GET /api/auth/status     # Auth service status
GET /api/auth/me         # Current user info
GET /api/auth/rate-limit # Rate limit status
```

**Roles:**
| Role | Rate Limit | Permissions |
|------|------------|-------------|
| `superadmin` | 1000/min | All |
| `analyst` | 500/min | Read, Write, Simulate, Export |
| `viewer` | 200/min | Read, Chat |
| `external_api` | 100/min | Read, Chat |

**Usage:**
```bash
curl -H "X-API-Key: valora-dev-admin-key" http://localhost:8000/api/auth/me
```

### Observability & Metrics

```
GET /api/metrics           # Full metrics summary
GET /api/metrics/endpoints # Per-endpoint latency
GET /api/metrics/verifier  # Fact verifier stats
GET /api/metrics/prometheus # Prometheus format export
```

**Tracked Metrics:**
- Request latency (avg, p50, p95, p99)
- Verifier mismatch rate
- Error breakdown by type
- Uptime and request counts

---

## Testing

### Unified Test Suite

```bash
# Run all tests (100+ tests across 16 categories)
cd scripts
python valora_test_suite.py

# Run specific categories
python valora_test_suite.py --category verifier auth observability
python valora_test_suite.py --category spatial occlusion solar

# Save JSON report
python valora_test_suite.py --save
```

**Test Categories:**
`intent`, `spatial`, `occlusion`, `solar`, `graph`, `tool`, `property`, `locality`, `gis`, `transaction`, `regulatory`, `counterfactual`, `verifier`, `auth`, `observability`, `api`

---

## Configuration Files

| File | Purpose |
|------|---------|
| `backend/llm_config.json` | LLM provider settings |
| `backend/admin_config.json` | Vector backend (FAISS/Pinecone) |
| `.env` | Environment variables |

---

## License

Proprietary - All rights reserved

---

## Related Documents

- [ARCHITECTURE.md](./ARCHITECTURE.md) - **Next-Gen 3D GIS Agent Architecture** (start here for development)
- [INVESTOR_PITCH.md](./INVESTOR_PITCH.md) - Investor deck
- [SCHEMA_REFERENCE.md](./SCHEMA_REFERENCE.md) - Database schema details
