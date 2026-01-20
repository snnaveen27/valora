# Valora AI — City Intelligence Platform Roadmap

<div align="center">

**🏙️ AI Digital Twin | 🗺️ Urban Planning Copilot | 🔬 City-Scale Simulator | 💻 Spatial Operating System**

</div>

This roadmap documents the evolution of Valora into a **production-grade 3D City Intelligence Platform** with multi-agent AI orchestration, real-time simulation, and cinematic 3D storytelling.

## Vision

Valora AI transforms how we understand and interact with cities:

- **AI Digital Twin**: Living digital replica of urban environments with real-time data
- **Urban Planning Copilot**: AI-assisted analysis for developers, investors, and planners
- **City-Scale Simulator**: Test infrastructure scenarios with LLM-reasoned impact analysis
- **Spatial Operating System**: Unified API layer for all spatial intelligence needs

## How to use this document

- Update **Status** fields as you progress.
- Keep phases sequential; do not start the next phase until the current phase exit criteria are met.
- Treat **Exit criteria** as your definition of "done".

---

## Status Tracker

| Phase | Name | Target | Status | Notes |
|------:|------|--------|--------|------|
| 0 | Stabilize Core Platform | 1–2 weeks | **✅ Completed** | Geocoding, caching, map UX, data registry |
| 1 | Spatial Knowledge Layer (RAG for GIS) | 2–4 weeks | **✅ Completed** | RAG, ML valuation, spatial reasoning |
| 2 | Multi‑Agent Orchestration | 2–4 weeks | **✅ Completed** | IntentRouter, GISAgentOrchestrator, AgentFacts |
| 3 | True 3D Reasoning + Map‑Aware Interaction | 3–6 weeks | **✅ Completed** | 3D overlays, viewport context, scene analytics |
| 4 | Simulation + Digital Twin | 3–6 weeks | **✅ Completed** | What-if engine, storyboards, real-time state tracking |
| 5 | Productization (Production Grade) | 2–4 weeks | **✅ Completed** | Credit system, security hardening, complete API |
| 6 | Advanced AI (Spatial LM & Multimodal) | 6–12 months | **🔄 Planned** | Vision models, real-time data, agent-based modeling |
| 7 | Global Expansion & Evaluation | Ongoing | **🔄 Planned** | Multi-city support, continuous benchmarking |

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

### Implementation (Completed Jan 2026)

#### Core Components
- **`OverlayEngine`** (`src/components/OverlayEngine.jsx`): AI-driven 3D overlay system for visual annotations
- **`SceneAnalyzer`** (`backend/scene_analyzer.py`): Viewport-aware analytics (height distribution, visibility, density)
- **3D Overlay Types**: Circles, polygons, arrows, labels, paths, heatmaps

#### Deliverables 
- **Scene context pipeline**
  - Frontend sends camera position/heading/pitch, viewport bbox, loaded tile ids, selected entity.
  - Backend receives scene context with every query for viewport-aware reasoning.
- **3D analytics**
  - Building height distribution in viewport.
  - "Visibility in frustum" (what is actually on screen).
  - Skyline descriptors and density analysis.
- **AI-Driven 3D Overlays**
  - **Shapes**: Circles (radius rings), polygons (area boundaries), buffers
  - **Annotations**: Labels, markers, pins with dynamic positioning
  - **Paths**: Lines, arrows, corridors (proposed infrastructure)
  - **Heatmaps**: Density overlays, slope/hillshade, risk zones
  - **Animation support**: Fade in/out, pulse, draw-along-path

#### Key Files
- `src/components/OverlayEngine.jsx` - 3D overlay rendering system
- `backend/scene_analyzer.py` - Viewport-aware scene analytics
- `backend/gis_agents.py` - Enhanced with overlay generation capabilities

### Exit criteria 
- "What am I looking at?" correctly summarizes what's in the viewport.
- "Compare these two areas" works with map-driven selections.
- AI can generate visual overlays (circles, arrows, labels) to explain analysis.

---

## Phase 4 — Simulation + Cinematic Storyboarding (3–6 weeks)

### Objective
Enable scenario planning: infrastructure changes, zoning changes, market assumptions, and visual storyboards.

### Implementation (Completed Jan 2026)

#### Core Components
- **`SimulationEngine`** (`backend/simulation_engine.py`): What-If scenario engine with ScenarioDeltas
- **`NarrativeGenerator`** (`backend/narrative_generator.py`): Storyboard generator with camera paths and overlays
- **`AnimationController`** (`src/components/AnimationController.jsx`): Storyboard animation system
- **`AudioNarrator`** (`backend/audio_narrator.py`): TTS pipeline for voiceover generation
- **`CinemaOverlay`** (`src/components/CinemaOverlay.jsx`): Immersive storyboard playback UI

#### Deliverables 
- **Simulation Engine**
  - Structured scenario inputs: "add metro station", "increase FAR", "new highway".
  - Output deltas: accessibility, amenity density, expected development pressure.
  - LLM-reasoned impact analysis (grounded in computed facts).
- **Narrative / storyboard layer**
  - Camera path, overlays per scene, explanation per step.
  - Each step includes: claim(s) + supporting computed facts/metrics (from ScenarioDeltas/agents).
  - Step-wise `analysis_explanation` payload for Analysis panel (what changed, why, evidence).
  - Overlay commands: circles, arrows, labels, paths, heatmaps per step.
- **Audio narration for storyboards**
  - Voiceover per storyboard step (aligned with narration text and timing).
  - Offline/local TTS pipeline (pyttsx3) for playback in cinematic mode.
  - Voice playback synchronized to storyboard steps (play/pause/seek/jump-to-step).
- **Animation System**
  - Smooth camera transitions between storyboard steps.
  - Overlay fade in/out, pulse, draw-along-path animations.
  - Timeline controls for storyboard playback.

#### Key Files
- `backend/simulation_engine.py` - What-If scenario engine
- `backend/narrative_generator.py` - Storyboard generator
- `backend/audio_narrator.py` - TTS voiceover pipeline
- `src/components/AnimationController.jsx` - Animation orchestration
- `src/components/CinemaOverlay.jsx` - Cinematic playback UI
- `backend/multi_agent_orchestrator.py` - Enhanced with simulation intent

### Exit criteria 
- "What if a metro station is added here?" produces:
  - a clear set of measurable deltas
  - a 3D cinematic walkthrough with smooth camera transitions
  - voice narration that plays in sync with the storyboard
  - an Analysis tab breakdown per step (claims + metrics/evidence)
  - visual overlays (circles, arrows, labels) explaining the impact

---

## Phase 5 — Productization (Production Grade) (2–4 weeks)

### Objective
Make it shippable: offline-first, fast, evaluated, and explainable with usage tracking.

### Implementation (✅ Completed Jan 2026)

#### Core Components
- **Credit System** (`/api/credits`): Windsurf-style usage tracking with per-operation costs
- **Production Offline Tiles**: Tilemaker-based high-quality map tile generation
- **Online/Offline Toggle**: Seamless switch between online OSM and local tiles
- **Complete API Suite**: 25+ production endpoints for all platform capabilities
- **System Status**: `/api/status` endpoint with comprehensive health check

#### Deliverables
- **Credit System (Usage Tracking)** ✅
  - Per-user credit balance with 100 free credits
  - Operation costs: chat (1), analysis (2), simulation (5), storyboard (10), valuation (3)
  - Credit history and usage analytics
  - `/api/credits` - manage credits (check/add/deduct)
  - `/api/credits/{user_id}` - get user balance and costs
  
- **Production-Grade Offline Tiles** ✅
  - Tilemaker integration for OSM tile rendering
  - Production-quality tiles matching online OSM quality
  - Tile caching with TTL cache (1000 tiles, 1hr TTL)
  - Tile manifest API (`/api/map-tiles/manifest`)
  - Local tile server endpoint (`/api/map-tiles/{z}/{x}/{y}.png`)
  - Zoom levels 10-16 (optimized for performance)
  - Browser caching headers (24hr cache-control)
  - Automatic tile availability detection
  - **No placeholder tiles in production** - requires real tilemaker installation
  
- **Online/Offline Mode** ✅
  - Default: Online mode (OpenStreetMap public tiles)
  - Toggle in map UI with WiFi icon
  - Frontend checks tile availability on load
  - Seamless switching without page reload
  - Proper zoom level handling (10-16 offline, unlimited online)
  - Bounding box restriction for offline (Bangalore: 77.3-78.0°E, 12.7-13.2°N)
  - Error messaging when offline tiles unavailable
  - Offline geocoding via local OSM data
  
- **Complete API Suite** ✅
  - `/api/simulate` - What-if simulation
  - `/api/simulate/storyboard` - Simulation with cinematic storyboard
  - `/api/status` - System health with all phase statuses
  - `/api/map-tiles/manifest` - Offline tile availability check
  - All Phase 1-4 endpoints production-ready
  
- **Safety & correctness** ✅
  - Deterministic APIs are source-of-truth
  - LLM never invents numbers; must cite computed values
  - Grounded facts architecture prevents hallucination
  - Production tile quality enforced (no placeholders)

#### Key Files
- `backend/server.py` - Credit system, tile serving with caching, manifest API
- `src/spatial/OnlineOSMMap.jsx` - Online/offline toggle with availability detection
- `scripts/generate_offline_tiles.py` - Production tile generator (tilemaker)
- `scripts/INSTALL_DEPENDENCIES.md` - Tilemaker installation guide
- `SETUP_OFFLINE_TILES.bat` - Automated setup script

#### Installation Scripts ✅
- **Tilemaker Setup**: `SETUP_OFFLINE_TILES.bat` - Auto-installs tilemaker
- **Manual Guide**: `scripts/INSTALL_DEPENDENCIES.md` - Step-by-step instructions
- **Tile Generator**: `scripts/generate_offline_tiles.py` - Production tile generation
- **Manifest Generator**: Auto-generates `manifest.json` for frontend validation

### Exit criteria
- ✅ Credit system tracks usage per user
- ✅ Online/offline toggle works seamlessly in UI
- ✅ Production-quality tiles (tilemaker) required and enforced
- ✅ Tile caching and performance optimization implemented
- ✅ All endpoints return consistent, grounded results
- ✅ System status endpoint shows all phases complete
- ✅ Offline tiles match online OSM quality (when generated with tilemaker)
- ✅ No placeholder tiles allowed in production environment

---

## Phase 6 — Advanced AI Capabilities (Research & Integration) (Ongoing)

### Objective
Integrate cutting-edge spatial AI models and multimodal reasoning for next-generation GIS intelligence.

### Deliverables

#### 6.1 Spatial Language Models (Spatial LM)
- **Fine-tuned Spatial Reasoning**
  - Train on spatial tasks: distance calculation, direction, containment, topology
  - Integrate GeoLM, Spatial-Bench, or custom models
  - Natural language → spatial query translation
  - Complex spatial reasoning: "What's between X and Y?"
  
#### 6.2 Vision Models for 3D Scene Understanding
- **SAM (Segment Anything Model) Integration**
  - 3D building/object segmentation from viewport
  - Automatic feature extraction from map screenshots
  - Building footprint detection and classification
- **Depth Estimation & Occlusion**
  - Monocular depth estimation for 3D scene understanding
  - Visibility analysis and occlusion reasoning
  - Height estimation from imagery
- **Visual Question Answering**
  - "What am I looking at?" from map screenshots
  - Building type classification from appearance
  - Urban pattern recognition

#### 6.3 Advanced Vector Search & Hybrid Retrieval
- **Enhanced RAG Pipeline**
  - Multi-vector embeddings (text + spatial + visual)
  - Hybrid search: semantic + spatial + fuzzy matching
  - Cross-lingual support (English + Kannada + Hindi)
  - Contextual re-ranking based on user intent
- **Knowledge Graph Integration**
  - Entity relationships (building → owner → developer)
  - Temporal knowledge (historical changes, development timeline)
  - Causal reasoning (infrastructure → property value impact)

#### 6.4 Multimodal Reasoning
- **Text + Vision + Spatial Fusion**
  - Screenshot analysis with spatial context
  - "Is this area greener than the one I just looked at?" → vision + landuse data
  - Comparative analysis across different viewports
- **Temporal Multimodal Analysis**
  - Before/after comparison from satellite imagery
  - Change detection and trend analysis
  - Predictive modeling based on historical patterns

#### 6.5 Reinforcement Learning for Navigation
- **Optimal Camera Path Learning**
  - Learn best viewpoints for area exploration
  - Automated "tour" generation
  - Personalized navigation based on user preferences
- **Interactive Exploration Agent**
  - Suggest next areas to explore
  - Adaptive zoom and angle selection
  - Context-aware camera movements

#### 6.6 Real-Time Data Integration
- **Live Data Streams**
  - Traffic data integration (Google Maps API, TomTom)
  - Air quality sensors (CPCB, PurpleAir)
  - Weather data (OpenWeatherMap)
  - Public transport real-time tracking
- **Event Detection**
  - Construction activity monitoring
  - Traffic incident detection
  - Market anomaly alerts
  - Demographic shifts

#### 6.7 Advanced Simulation Capabilities
- **Agent-Based Modeling**
  - Simulate pedestrian/vehicle movement
  - Economic agent behavior (buyers, sellers, developers)
  - Infrastructure utilization patterns
- **System Dynamics Modeling**
  - Long-term urban growth simulation
  - Resource consumption forecasting
  - Environmental impact modeling
- **Monte Carlo Simulation**
  - Uncertainty quantification in predictions
  - Risk analysis for development projects
  - Sensitivity analysis for policy changes

### Exit criteria
- ✅ Spatial LM answers complex queries with >90% accuracy
- ✅ Vision model segments buildings/roads with >85% IoU
- ✅ Multimodal queries work seamlessly across text/vision/spatial
- ✅ Real-time data updates within 5 minutes
- ✅ Simulation accuracy validated against historical data

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

---

## Backlog: Missing Capabilities (To Implement)

### Map Visualization Enhancements
| Feature | Priority | Description |
|---------|----------|-------------|
| **Transport Layer** | High | Render bus stops, metro stations as 3D markers on map |
| **Property Markers** | High | Show property search results as clickable pins on map |
| **Heat Maps** | Medium | Price density, accessibility score overlays |
| **Route Visualization** | Medium | Show walking/driving routes to selected POIs |
| **Building Clustering** | Low | Group buildings at low zoom levels for performance |

### AI Agent Improvements
| Feature | Priority | Description |
|---------|----------|-------------|
| **Compound Query Parsing** | High | Handle "go to X and show Y" as two-step action |
| **Query Disambiguation** | High | Ask clarifying questions for ambiguous locations |
| **Conversation Memory** | Medium | Remember context across multi-turn conversations |
| **Follow-up Suggestions** | Medium | Suggest related queries after each response |
| **Voice Input/Output** | Low | Speech-to-text and TTS for narration |

### Property Search Enhancements
| Feature | Priority | Description |
|---------|----------|-------------|
| **Filter UI Panel** | High | Visual filters for price, BHK, area, category |
| **Property Cards** | High | Rich property cards with images in Analysis Panel |
| **Saved Searches** | Medium | Save and recall property search queries |
| **Price Alerts** | Low | Notify when properties match criteria |
| **Comparison View** | Medium | Side-by-side property comparison |

### Offline Mode (Critical for MVP)
| Feature | Priority | Description |
|---------|----------|-------------|
| **Local MBTiles Serving** | Critical | Serve map tiles from local MBTiles file |
| **Tile Caching** | High | Cache online tiles for offline use |
| **Data Sync Status** | Medium | Show last sync time and data freshness |
| **Offline Indicator** | High | Clear UI indicator when in offline mode |

### Digital Twin Enhancements
| Feature | Priority | Description |
|---------|----------|-------------|
| **Time Slider** | Medium | View city state at different time points |
| **Scenario Comparison** | High | Compare multiple what-if scenarios side-by-side |
| **Export Reports** | Medium | Generate PDF reports from simulations |
| **Collaborative Editing** | Low | Multiple users annotating same digital twin |

### Performance & Scale
| Feature | Priority | Description |
|---------|----------|-------------|
| **Building LOD** | Medium | Level-of-detail for buildings at different zoom |
| **Tile Streaming** | Medium | Progressive loading of 3D tiles |
| **Query Caching** | High | Cache frequent AI queries with TTL |
| **WebWorker Processing** | Low | Offload heavy computations to web workers |

---

## Implementation Notes

### Transport Layer Implementation
```javascript
// Proposed implementation in OnlineOSMMap.jsx
const loadTransportMarkers = async () => {
  const response = await fetch(`${API_BASE}/api/spatial/transport`)
  const data = await response.json()
  data.stops.forEach(stop => {
    viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(stop.lng, stop.lat),
      billboard: { image: stop.type === 'metro' ? metroIcon : busIcon },
      label: { text: stop.name }
    })
  })
}
```

### Offline Tiles Strategy
1. Generate MBTiles from OSM PBF using `tippecanoe`
2. Serve tiles via FastAPI endpoint `/api/tiles/{z}/{x}/{y}.png`
3. Configure Cesium to use local tile server
4. Fallback to cached tiles when offline
