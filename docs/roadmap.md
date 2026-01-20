# Valora — 3D Reasoning GIS AI (Multi‑Agent) Roadmap

This roadmap is a living plan to evolve Valora into a production-grade **3D reasoning GIS AI** with a **multi-agent** architecture.

## How to use this document

- Update **Status** fields as you progress.
- Keep phases sequential; do not start the next phase until the current phase exit criteria are met.
- Treat **Exit criteria** as your definition of “done”.

---

## Status Tracker

| Phase | Name | Target | Status | Notes |
|------:|------|--------|--------|------|
| 0 | Stabilize Core Platform | 1–2 weeks | **Completed** | Geocoding, caching, map UX, data registry |
| 1 | Spatial Knowledge Layer (RAG for GIS) | 2–4 weeks | **Completed** | RAG, ML valuation, spatial reasoning |
| 2 | Multi‑Agent Orchestration | 2–4 weeks | **Completed** | IntentRouter, GISAgentOrchestrator, AgentFacts |
| 3 | True 3D Reasoning + Map‑Aware Interaction | 3–6 weeks | Not Started | |
| 4 | Simulation + “What‑If” Reasoning | 3–6 weeks | Not Started | |
| 5 | Productization (offline-first, perf, eval, governance) | Ongoing | Not Started | |
| 6 | Advanced AI Capabilities (Spatial LM, SAM, Multimodal) | Ongoing | Not Started | |
| 7 | Evaluation & Continuous Improvement | Ongoing | Not Started | |

---

## Phase 0 — Stabilize Core Platform (1–2 weeks)

### Objective
Make core navigation, analysis, and data-loading **reliable**, **fast**, and **consistent**.

### Deliverables
- **Geocoding quality & disambiguation**
  - Return top candidates + confidence.
  - When confidence is low, show UI selection instead of jumping.
- **Map UX**
  - Consistent `flyTo` framing.
  - Place marker/label at target.
  - “Back to last view” and “Reset view”.
- **Data health & observability**
  - Single index describing all local datasets: OSM extracted, tiles, terrain, govt datasets.
  - Basic logging (timings) for geocode/analyze/terrain.
- **Caching**
  - Response caching for hot endpoints (`/api/geocode`, `/api/area/analyze`, `/api/terrain/*`).

### Exit criteria
- Place search works for common queries (e.g. airport, tech parks, metro stops) with correct targeting.
- P95 API timings (local):
  - geocode < 200ms
  - terrain < 100ms
  - area analyze < 1s

---

## Phase 1 — Spatial Knowledge Layer (RAG for GIS) (2–4 weeks) 

### Objective
Turn raw GIS layers into a **queryable knowledge system** for the AI (spatial + semantic retrieval).

### Deliverables 
- **Spatial index** 
  - H3 hexagonal indexing for POIs, transport, places (resolution 9 ~100m)
  - Fast proximity queries via `spatial_reasoning.py`
- **Vector search (RAG)** 
  - Pinecone vector database integration
  - Sentence-transformer embeddings (all-MiniLM-L6-v2)
  - Semantic search across properties, POIs, places, transport
- **ML Property Valuation** 
  - Gradient Boosting model with spatial features
  - Price prediction based on location, amenities, metro proximity
  - Market comparables and statistics
- **Unified spatial query API** 
  - `GET /api/spatial/nearby?lat=&lng=&radius=&layers=`
  - `GET /api/spatial/contains?lat=&lng=`
  - `GET /api/spatial/summary?lat=&lng=&radius=`
  - `GET /api/spatial/analyze?lat=&lng=`
- **Valuation API** 
  - `POST /api/valuation/estimate`
  - `GET /api/valuation/market-stats`
- **RAG API** 
  - `GET /api/rag/search`
  - `POST /api/rag/index`
  - `GET /api/rag/context`

### Exit criteria 
- The AI can answer with grounded, repeatable facts:
  - "Within 1km: X hospitals, Y schools, Z bus stops" 
  - "This point is inside Zone ___" 
  - "Estimated property value: ₹X based on spatial features" 

---

## Phase 2 — Multi‑Agent Orchestration (2–4 weeks) 

### Objective
Introduce specialized agents with a strict contract so the system is robust and scalable.

### Implementation (Completed Jan 2026)

#### Core Components
- **`IntentRouter`**: Classifies queries into 8 intents (NAVIGATE, ANALYZE_AREA, ANALYZE_BUILDING, PROPERTY_SEARCH, VALUATION, TERRAIN, COMPARISON, GENERAL)
- **`GISAgentOrchestrator`**: Dispatches to deterministic agents, collects grounded facts
- **`AgentFacts`**: Structured dataclass holding all computed facts (no LLM invention)

#### Agent Roles (Implemented)
- **Router Agent**: `IntentRouter.classify()` - regex-based intent detection
- **Geocoder Agent**: Uses `local_geocoder` for place resolution
- **Spatial Analyst Agent**: `spatial_service.get_summary()` - POIs, transport, accessibility/walkability scores
- **Terrain Agent**: `terrain_service` - elevation, slope, flood risk, construction suitability
- **Property Agent**: `property_service` - market stats computed from real listings
- **Valuation Agent**: `valuation_model.valuate()` - ML-based price estimation
- **RAG Agent**: `rag_service.search()` - semantic search across knowledge base

#### Data Flow
1. User query → `IntentRouter.classify()` determines intent
2. `GISAgentOrchestrator.gather_facts()` dispatches to relevant agents
3. Agents collect deterministic facts from real data sources
4. Facts converted to context string + dashboard via `AgentFacts`
5. LLM receives ONLY grounded facts for narrative synthesis
6. Response includes: message, intent, dashboard, ui_actions, facts_summary

#### Key Files
- `backend/gis_agents.py` - Multi-agent system (IntentRouter, AgentFacts, GISAgentOrchestrator)
- `backend/server.py` - `/api/chat` refactored to use orchestrator
- `backend/test_gis_agents.py` - Test suite for intent classification and facts

### Exit criteria 
- A single user request can reliably trigger multi-step reasoning:
  - "Is this area good for apartments?" → POIs + transport + terrain + basic market heuristics.

---

## Phase 3 — True 3D Reasoning + Map‑Aware Interaction (3–6 weeks)

### Objective
Make the AI aware of and able to reason about the **3D scene**, not just coordinates.

### Deliverables
- **Scene context pipeline**
  - Frontend sends camera position/heading/pitch, viewport bbox, loaded tile ids, selected entity.
- **3D analytics**
  - Building height distribution in viewport.
  - “Visibility in frustum” (what is actually on screen).
  - Simple occlusion proxies / skyline descriptors.
- **Explainable overlays**
  - Highlight boundaries/areas.
  - Radius rings and result pins.
  - Heatmaps for density and slope/hillshade overlays.

### Exit criteria
- “What am I looking at?” correctly summarizes what’s in the viewport.
- “Compare these two areas” works with map-driven selections.

---

## Phase 4 — Simulation + “What‑If” Reasoning (3–6 weeks)

### Objective
Enable scenario planning: infrastructure changes, zoning changes, market assumptions, and visual storyboards.

### Deliverables
- **Simulation Engine**
  - Structured scenario inputs: “add metro station”, “increase FAR”, “new highway”.
  - Output deltas: accessibility, amenity density, expected development pressure.
- **Narrative / storyboard layer**
  - Camera path, overlays per scene, explanation per step.

### Exit criteria
- “What if a metro station is added here?” produces:
  - a clear set of measurable deltas
  - a 3D cinematic walkthrough

---

## Phase 5 — Productization (Offline-first, Performance, Evaluation, Governance) (Ongoing)

### Objective
Make it shippable: offline-first, fast, evaluated, and explainable.

### Deliverables
- **Offline-first packaging**
  - Local tiles (or MBTiles), offline geocoding, offline datasets.
- **Evaluation harness**
  - Test queries for geocode accuracy, spatial summaries, and reasoning correctness.
  - Regression tests for known important locations.
- **Safety & correctness**
  - Deterministic APIs are source-of-truth.
  - LLM never invents numbers; must cite computed values.
- **Performance**
  - Precomputed indexes, streaming tiles, progressive rendering.

### Exit criteria
- Repeatable results, measurable accuracy, and predictable performance.

---

## Phase 6 — Advanced AI Capabilities (Research & Integration) (Ongoing)

### Objective
Integrate cutting-edge spatial AI models and multimodal reasoning for next-generation GIS intelligence.

### Deliverables
- **Spatial Language Models (Spatial LM)**
  - Fine-tune LLMs on spatial reasoning tasks (distance, direction, containment, topology).
  - Integrate models like GeoLM, Spatial-Bench, or custom fine-tuned variants.
  - Enable natural language → spatial query translation.
- **Vision Models for 3D Scene Understanding**
  - SAM (Segment Anything Model) for 3D building/object segmentation from viewport.
  - Depth estimation and occlusion reasoning.
  - Visual question answering over map screenshots.
- **Vector Embeddings & Semantic Search**
  - Embed all POI names, descriptions, categories, and tags.
  - Hybrid search: fuzzy string + semantic similarity + spatial proximity.
  - Cross-lingual support (English + Kannada place names).
- **Multimodal Reasoning**
  - Combine text (user query) + vision (map screenshot) + spatial data (coordinates, topology).
  - "Show me the tallest building in this view" → vision + height data.
- **Reinforcement Learning for Navigation**
  - Learn optimal camera paths for area exploration.
  - Personalized "tour" generation based on user preferences.

### Exit criteria
- Spatial LM can answer complex queries: "What's between the airport and the city center?"
- Vision model can identify and segment buildings/roads from 3D viewport.
- Multimodal queries work: "Is this area greener than the one I just looked at?"

---

## Phase 7 — Evaluation & Continuous Improvement (Ongoing)

### Objective
Build a rigorous evaluation framework to measure and improve system accuracy, reliability, and user satisfaction.

### Deliverables
- **Geocoding Benchmark**
  - Test set of 500+ Bangalore locations (landmarks, neighborhoods, streets, POIs).
  - Metrics: Top-1 accuracy, Top-3 accuracy, mean reciprocal rank (MRR).
- **Spatial Analysis Benchmark**
  - Ground truth for "nearby" queries (manually verified counts).
  - Regression tests for known locations.
- **Reasoning Evaluation**
  - Human-labeled dataset for "good for apartments", "construction suitability", etc.
  - Compare AI recommendations vs. expert judgments.
- **User Experience Metrics**
  - Task completion rate, time-to-answer, user satisfaction scores.
  - A/B testing for UX improvements.
- **Continuous Monitoring**
  - Log all queries, responses, and user feedback.
  - Automated alerts for accuracy degradation.

### Exit criteria
- Geocoding accuracy > 95% on benchmark.
- Spatial analysis results match ground truth within 5% error.
- User satisfaction score > 4.5/5.

---

## Property Data Integration (Completed)

### Real Estate Listings
Valora now includes comprehensive real estate property data for Bangalore:

| Category | Files | Description |
|----------|-------|-------------|
| **Residential** | 5 files | Apartments (sale/rent), Houses (sale/rent), Plots |
| **Commercial** | 6 files | Land, Office, Shop, Warehouse, Industrial |
| **Agricultural** | 2 files | Agricultural land, Farmhouses |

### Property API Endpoints (Implemented)
- `GET /api/properties/search` - Search with location, price, category filters
- `GET /api/properties/nearby` - Properties near a location with stats
- `GET /api/properties/{id}` - Get property by ID
- `GET /api/properties/stats/area` - Market statistics for an area
- `GET /api/properties/categories` - Property counts by category

### Property Data Schema
Each property includes: `id`, `name`, `price`, `price_per_sq_ft`, `location` (lat,lng), `bedrooms`, `bathrooms`, `covered_area`, `amenities`, `landmark_details`, `owner_name`, `image_url`

---

## Data Registry (Completed)

A comprehensive data index has been created at `src/data/data_registry.json`:

| Dataset | Description | Count |
|---------|-------------|-------|
| **osm_extracted** | Buildings, roads, POIs, transport | 1.26M features |
| **3dtiles** | 3D building tiles for Cesium | 724 tiles, 686K buildings |
| **terrain** | DEM elevation, slope, aspect | 30m SRTM resolution |
| **posted_properties** | Real estate listings | 13 categories |
| **government_data** | Education, infrastructure CSVs | 28 files |

---

## Near-term priorities (Recommended)

1. **Phase 0** disambiguation UI + confidence scoring
2. **Phase 0** place marker + back/reset view UX
3. **Phase 1** unified spatial query API (`nearby`, `summary`, `contains`)
4. **Phase 2** Router → Analyst → Narrative flow
5. **Phase 3** scene context (viewport-aware reasoning)
6. **Phase 6** (parallel) vector embeddings for semantic search
7. **Phase 7** (parallel) geocoding + analysis benchmark suite
