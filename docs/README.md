# Valora AI - City Intelligence Platform

<div align="center">

**🏙️ AI Digital Twin | 🗺️ Urban Planning Copilot | 🔬 City-Scale Simulator | 💻 Spatial Operating System**

[![Phase](https://img.shields.io/badge/Phase-5%20Complete-success)](docs/roadmap.md)
[![3D](https://img.shields.io/badge/3D-CesiumJS-blue)](https://cesium.com/)
[![AI](https://img.shields.io/badge/AI-Multi--Agent-purple)](backend/gis_agents.py)
[![Offline](https://img.shields.io/badge/Mode-Offline%20Ready-orange)](docs/OSM_DATA.md)

</div>

Valora AI is a **production-grade 3D City Intelligence Platform** that transforms urban data into actionable insights. Powered by multi-agent AI orchestration, real-time simulation, and cinematic 3D storytelling.

## 🚀 What is Valora AI?

- **AI Digital Twin**: A living digital replica of Bangalore with 686K+ 3D buildings, real-time property data, and spatial intelligence
- **Urban Planning Copilot**: AI-assisted analysis for developers, investors, and city planners with what-if simulation
- **City-Scale Simulator**: Test infrastructure scenarios (metro stations, highways, zoning changes) with LLM-reasoned impact analysis
- **Spatial Operating System**: Unified API layer for spatial queries, property valuations, and urban analytics

## ✨ Key Features

### Phase 5: Production Ready ✅ (Current)
- **Credit System**: Windsurf-style usage tracking with per-operation costs
- **Online/Offline Toggle**: Switch between online OSM tiles and local tile server
- **Complete API Suite**: 25+ endpoints for spatial, property, simulation, and RAG queries
- **ML Models**: Property valuation with gradient boosting + spatial features

### Phase 4: Simulation & Digital Twin ✅
- **What-If Simulation Engine**: Test urban scenarios (metro, highway, zoning) with computed impact deltas
- **Digital Twin**: Real-time city state management with change tracking and impact analysis
- **Cinematic Storyboards**: Auto-generated 3D narratives with camera choreography
- **AI-Driven Overlays**: Visual annotations (circles, arrows, labels) for analysis
- **State Change History**: Track all modifications with cascading effect analysis

### Phase 3: City Brain Memory ✅
- **Self-Learning System**: Tracks queries, hotspots, and trends
- **Pattern Recognition**: Identifies frequently analyzed locations
- **Insight Generation**: Automated market intelligence from usage patterns

### Phase 2: Multi-Agent Orchestration ✅
- **Intent Router**: Classifies user queries (navigate, analyze, search, simulate)
- **Specialized Agents**: Spatial, Terrain, Property, Valuation, RAG agents
- **Grounded Facts**: AI responses built on deterministic data, never hallucinated

### Phase 1: Spatial Intelligence ✅
- **RAG with Pinecone**: Semantic search across 29K+ indexed spatial features
- **ML Property Valuation**: Gradient boosting with H3 spatial features
- **Accessibility/Walkability Scores**: Based on transport and amenity proximity

### Phase 0: Core Platform ✅
- **3D Cesium Map**: 686K buildings in 724 tiles with click-to-analyze
- **Hybrid Geocoding**: Local OSM + static landmarks + Nominatim fallback
- **Real OSM Data**: 817K buildings, 335K roads, 33K POIs, 5K transport stops

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                            │
│   "Show me Hebbal" / Click Building / Ask Question                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React + Cesium)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ ChatPanel   │  │ 3D Map      │  │ Analysis    │                 │
│  │ (Intent     │  │ (Cesium)    │  │ Panel       │                 │
│  │  Detection) │  │             │  │ (Dashboard) │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
│         │                ▲                ▲                         │
│         │                │                │                         │
│         ▼                │                │                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    agentData (shared state)                  │   │
│  │  flyTo, selectedPlace, selectedBuilding, dashboard           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI :8000)                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │ /api/chat       │  │ /api/area/      │  │ /api/geocode    │     │
│  │ (LLM + Context) │  │ analyze         │  │ (Nominatim)     │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│         │                     │                                     │
│         ▼                     ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              AreaAnalyzer (OSM Data Engine)                  │   │
│  │  - Loads derived GeoJSON (roads, POIs, transport, landuse)   │   │
│  │  - Computes radius-based analysis                            │   │
│  │  - Generates dashboard payloads                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA LAYER (Offline)                           │
│  src/data/osm_extracted/      (817K buildings, 335K roads, 33K POIs)│
│  src/data/3dtiles/            (724 tiles, 686K 3D buildings)        │
│  src/data/terrain/            (DEM elevation, slope, aspect)        │
│  src/data/posted_properties/  (Real estate listings)                │
│  src/data/GOV DATA/           (Government datasets)                 │
│  src/data/data_registry.json  (Complete data index)                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Example: "Show me Hebbal"

1. **User types** "Show me Hebbal" in ChatPanel
2. **Frontend detects navigation intent** (regex match)
3. **Frontend resolves place** (local BANGALORE_AREAS fallback → Nominatim geocode)
4. **Map action executes IMMEDIATELY** (`setAgentData({ flyTo: {lat, lng} })`)
5. **Backend receives /api/chat** with `selectedPlace` context
6. **AreaAnalyzer** computes 1km radius analysis from OSM data
7. **Backend returns** `{ message, dashboard, ui_actions }`
8. **Frontend applies** dashboard to AnalysisPanel, shows AI response in chat

## Key Files

| File | Purpose |
|------|---------|
| `src/components/ChatPanel.jsx` | Intent detection, navigation, AI chat |
| `src/components/AnalysisPanel.jsx` | Dynamic dashboard rendering |
| `src/spatial/OnlineOSMMap.jsx` | Cesium 3D map, building selection |
| `src/components/MainApp.jsx` | Layout, shared state, UI command handling |
| `backend/server.py` | FastAPI endpoints, LLM integration |
| `backend/area_analyzer.py` | OSM data analysis engine |
| `backend/local_geocoder.py` | Offline geocoding from OSM data |
| `backend/terrain_service.py` | DEM-based terrain analysis |
| `backend/property_service.py` | Real estate property queries |
| `src/data/osm_extracted/` | Pre-extracted OSM data |
| `src/data/terrain/` | DEM-derived elevation tiles |
| `src/data/posted_properties/` | Real estate listings (13 categories) |
| `src/data/data_registry.json` | Complete data index for all datasets |

## Shared State (agentData)

```javascript
{
  flyTo: { lat, lng, zoom },        // Triggers map navigation
  selectedPlace: { name, lat, lng }, // Current navigated place
  selectedBuilding: { height, ... }, // Clicked building
  dashboard: {                       // Dynamic analysis data
    title: "Hebbal (OSM context)",
    cards: [{ label, value }],
    area: { top_pois, nearest_transit, ... }
  }
}
```

## Current Architecture
**Frontend + Backend + Local Nominatim Geocoder**

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend       │────▶│   Nominatim     │
│   (React/Vite)  │     │   (FastAPI)     │     │   (Docker)      │
│   :3000         │     │   :8000         │     │   :8088         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Core Components

**Frontend (`src/`)**
- `src/components/MainApp.jsx` - Layout orchestrator, owns `agentData` state
- `src/components/ChatPanel.jsx` - AI chat with dynamic geocoding
- `src/spatial/OnlineOSMMap.jsx` - Cesium 3D map, executes flyTo commands
- `src/components/AnalysisPanel.jsx` - Location analysis display

**Backend (`backend/`)**
- `backend/server.py` - FastAPI server with geocoding endpoints
- Proxies requests to local Nominatim instance
- Biases search results to Bangalore area

**Geocoder (Hybrid: Local OSM + Static Landmarks + Nominatim)**
- **Tier 1**: Static landmarks (Airport, major malls, tech parks) - always available
- **Tier 2**: Local OSM geocoder (4,871 places, 7,811 transport stops, 33,541 POIs)
- **Tier 3**: Nominatim Docker instance (optional, for additional coverage)
- **Coverage**: Extended Bangalore metro area (12.88°N - 13.09°N, 77.42°E - 77.76°E)
- **Works**: "Tin Factory", "Airport", "Hebbal", "Phoenix Mall", metro/bus stops, neighborhoods, outer suburbs
- **Fully offline capable** - works without Nominatim running

### Data Flow
1. **User asks** "Show me Tin Factory"
2. **ChatPanel** extracts place name → calls `/api/geocode`
3. **Backend** queries Nominatim → returns `{lat, lng, name, ...}`
4. **ChatPanel** sets `agentData.flyTo`
5. **Map** flies to location
6. **AnalysisPanel** can display place details

### Shared State (agentData)
- `flyTo`: `{ lat, lng, zoom }` - triggers map navigation
- `selectedPlace`: `{ name, lat, lng, display_name, ... }` - current place
- `clickedLocation`: `{ latitude, longitude }` - map click coords
- `mapCenter`, `mapLoaded` - map initialization state

## Tech Stack
- **Frontend**: React 18, Vite, Tailwind CSS
- **Backend**: FastAPI, Python 3.10+
- **Geocoder**: Nominatim (Docker) + Local OSM geocoder
- **3D Map**: CesiumJS
- **Terrain**: DEM (Digital Elevation Model) analysis with rasterio
- **UI Icons**: lucide-react

## Project Structure
```
├── backend/
│   ├── server.py          # FastAPI backend
│   └── requirements.txt   # Python dependencies
├── docs/
│   └── NOMINATIM_SETUP.md # Geocoder setup guide
├── src/
│   ├── components/
│   │   ├── AnalysisPanel.jsx
│   │   ├── ChatPanel.jsx
│   │   ├── ErrorBoundary.jsx
│   │   └── MainApp.jsx
│   ├── spatial/
│   │   └── OnlineOSMMap.jsx
│   ├── styles/
│   │   └── cesium.css
│   ├── App.jsx
│   └── main.jsx
├── docker-compose.yml     # Nominatim geocoder
├── START_BACKEND.bat      # Start backend server
└── START_FRONTEND.bat     # Start frontend dev server
```

## Getting Started

### Prerequisites
- **Node.js 18+** and npm
- **Python 3.10+** with pip
- **Docker Desktop** (for Nominatim geocoder)

### Step 1: Install Frontend Dependencies
```bash
npm install
```

### Step 2: Install Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
cd ..
```

### Step 3: Start Nominatim Geocoder (First Time)
```bash
docker-compose up -d
```
> ⚠️ First run downloads and imports OSM data (~1-4 hours). Monitor with `docker-compose logs -f nominatim`

### Step 4: Start Backend
```bash
START_BACKEND.bat
# Or: cd backend && python -m uvicorn server:app --port 8000 --reload
```

### Step 5: Start Frontend
```bash
START_FRONTEND.bat
# Or: npm run dev
```

### Verify Everything Works
1. Open http://localhost:3000
2. Type "Show me Tin Factory" in chat
3. Map should fly to Tin Factory, Bangalore

### Build
```bash
npm run build
```

### Preview
```bash
npm run preview
```

## Configuration Notes

### Environment Variables

Frontend (Vite):

- **`VITE_API_URL`**: Backend base URL used by the frontend (defaults to `http://localhost:8000`).

Backend (FastAPI):

- **`FRONTEND_ORIGINS`**: Comma-separated CORS allowlist (defaults to localhost dev origins).
- **`LOG_REQUEST_TIMINGS`**: Set to `1` to print per-request timings (default `1`). Set to `0` to disable.
### Cesium Assets
Cesium assets are served locally via Vite:
- `vite-plugin-static-copy` copies Cesium to `/cesium/`
- `CESIUM_BASE_URL` is set to `/cesium/`

### Cesium Ion Token
`src/spatial/OnlineOSMMap.jsx` currently sets a Cesium Ion access token directly in code. If Ion services are required later, move the token to environment configuration and **do not** hardcode it.

## Offline-First Requirement (Important)
Valora AI MVP is intended to be **fully offline**. The current demo map uses **online** OpenStreetMap tiles in `OnlineOSMMap.jsx`:
- `Cesium.OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' })`

For offline compliance:
1. Replace the online imagery provider with a local tile source.
2. Remove external API calls and external asset dependencies.
3. Ensure all tiles and data are served from localhost.

## Customization
- Add or edit Bangalore area shortcuts in `BANGALORE_AREAS` in `OnlineOSMMap.jsx`.
- Update initial camera defaults via `DEFAULT_LOCATION` in `OnlineOSMMap.jsx`.
- Adjust analysis content in `AnalysisPanel.jsx`.

## Troubleshooting
- **Blank Cesium map**: Verify `/cesium/` assets are served (see `vite.config.js`).
- **Map not responding**: Ensure the viewer is initialized and not destroyed.
- **Tiles not loading**: Check imagery provider URL and CORS if using local tiles.

## Real Estate Property Data

Valora includes comprehensive real estate listing data for Bangalore in `src/data/posted_properties/`:

### Property Categories

| Category | Type | File | Description |
|----------|------|------|-------------|
| **Residential** | Apartment (Sale) | `bangalore-residential-apartment.json` | Apartments for sale |
| **Residential** | Apartment (Rent) | `bangalore-residential-apartment-rent.json` | Apartments for rent |
| **Residential** | House (Sale) | `bangalore-residential-house.json` | Houses for sale |
| **Residential** | House (Rent) | `bangalore-residential-house-rent.json` | Houses for rent |
| **Residential** | Plot | `bangalore-residential-plot.json` | Residential plots |
| **Commercial** | Land | `bangalore-commercial-land.json` | Commercial land |
| **Commercial** | Office Space | `bangalore-commercial-officespace.json` | Office spaces |
| **Commercial** | Shop (Rent) | `bangalore-commercial-shop-rent.json` | Shops for rent |
| **Commercial** | Warehouse | `bangalore-commercial-warehouse.json` | Warehouses |
| **Commercial** | Industrial Building | `bangalore-commercial-industrialbuilding.json` | Industrial buildings |
| **Commercial** | Industrial Shed | `bangalore-commercial-industrialshed.json` | Industrial sheds |
| **Agricultural** | Land | `bangalore-agriculturalland.json` | Agricultural land |
| **Agricultural** | Farmhouse | `bangalore-farmhouse.json` | Farmhouses |

### Property Data Schema

Each property listing contains:
```json
{
  "id": "80969731",
  "name": "2BHK Multistorey Apartment...",
  "price": 14040000,
  "price_per_sq_ft": 12000,
  "location": "12.91235,77.680996",
  "bedrooms": 2,
  "bathrooms": 2,
  "covered_area": 1170,
  "amenities": "Swimming Pool, Gym...",
  "landmark_details": ["Hospital", "School", "Metro"],
  "owner_name": "Agent Name",
  "image_url": "https://..."
}
```

### Property API Endpoints (Implemented)
- `GET /api/properties/search` - Search properties by location/radius, price, category filters
- `GET /api/properties/nearby` - Find properties near a location (includes summary stats)
- `GET /api/properties/{id}` - Get property details by ID
- `GET /api/properties/stats/area` - Market statistics for an area
- `GET /api/properties/categories` - Property counts by category

### Phase 1: Spatial Query API (NEW)
- `GET /api/spatial/nearby` - Query POIs, transport, places near a point
- `GET /api/spatial/summary` - Counts by category, accessibility/walkability scores
- `GET /api/spatial/contains` - Get zone/jurisdiction for a point
- `GET /api/spatial/analyze` - Complete location analysis with terrain

### Phase 1: Valuation API (NEW)
- `POST /api/valuation/estimate` - ML-based property price estimation
- `GET /api/valuation/market-stats` - Market statistics for an area

### Phase 1: RAG API (NEW)
- `GET /api/rag/search` - Semantic search across spatial knowledge base
- `POST /api/rag/index` - Index all data into Pinecone
- `GET /api/rag/context` - Get relevant context for LLM augmentation
- `GET /api/phase1/status` - Check Phase 1 services availability

## Current Status: Phase 5 Complete ✅

Valora AI is now a **production-ready 3D City Intelligence Platform** with all core phases implemented:

| Phase | Name | Status | Key Features |
|-------|------|--------|--------------|
| **0** | Core Platform | ✅ Complete | 3D Map, Geocoding, OSM Data, Terrain |
| **1** | Spatial Intelligence | ✅ Complete | RAG, ML Valuation, H3 Indexing |
| **2** | Multi-Agent | ✅ Complete | Intent Router, GIS Orchestrator |
| **3** | City Brain | ✅ Complete | Query Learning, Hotspot Tracking |
| **4** | Simulation | ✅ Complete | What-If Engine, Storyboards |
| **5** | Production | ✅ Complete | Credit System, Offline Mode |

### API Endpoints (30+)

| Category | Endpoints | Description |
|----------|-----------|-------------|
| **Chat** | `/api/chat` | Multi-agent AI conversation |
| **Spatial** | `/api/spatial/nearby`, `/api/spatial/summary`, `/api/spatial/analyze` | Proximity queries |
| **Properties** | `/api/properties/smart-search`, `/api/properties/nearby` | Property search |
| **Simulation** | `/api/simulate`, `/api/simulate/storyboard` | What-if scenarios |
| **Digital Twin** | `/api/digital-twin/init`, `/api/digital-twin/state`, `/api/digital-twin/update`, `/api/digital-twin/history` | Real-time city state tracking |
| **Credits** | `/api/credits`, `/api/credits/{user_id}` | Usage tracking |
| **RAG** | `/api/rag/search`, `/api/rag/context`, `/api/rag/index` | Semantic search |
| **Valuation** | `/api/valuation/estimate`, `/api/valuation/market-stats` | ML price estimation |
| **Status** | `/api/status`, `/api/phase1/status` | System health check |

See `docs/NOMINATIM_SETUP.md` for detailed geocoder setup instructions.

## Testing & Benchmarks

See **`docs/test_prompts.md`** for comprehensive test prompts to verify all Valora AI capabilities:
- 40+ test cases across Phase 0 and Phase 1
- API endpoint examples (curl and PowerShell)
- Scoring templates for benchmark tracking
- Acceptance criteria by phase

## Roadmap

See **`docs/roadmap.md`** for the complete phased plan to evolve Valora into a production-grade **3D reasoning GIS AI** with multi-agent architecture, including:
- Phase 0-5: Core platform, spatial RAG, multi-agent orchestration, 3D reasoning, simulation
- Phase 6: Advanced AI (Spatial LM, SAM 3D, multimodal reasoning)
- Phase 7: Evaluation & continuous improvement

---

## Future-Proof Architecture

### Extensibility Points

Valora is designed with clear extension points for advanced capabilities:

**1. Data Layer Extensions**
- **New data sources**: Add govt datasets, satellite imagery, traffic data
- **Real-time feeds**: Transit APIs, weather, air quality sensors
- **Custom layers**: Property listings, zoning regulations, development plans

**2. AI Model Integration**
- **Spatial Language Models**: GeoLM, Spatial-Bench for advanced spatial reasoning
- **Vision Models**: SAM for 3D segmentation, depth estimation
- **Multimodal Models**: GPT-4V, Gemini for screenshot analysis
- **Domain-specific**: Fine-tuned models for real estate valuation

**3. Agent Architecture**
```
┌─────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT ORCHESTRATOR                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Router       │  │ Geocoder     │  │ Spatial      │      │
│  │ Agent        │  │ Agent        │  │ Analyst      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Terrain      │  │ Gov Data     │  │ Narrative    │      │
│  │ Agent        │  │ Agent        │  │ Agent        │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Spatial LM   │  │ Vision       │  │ Simulation   │      │
│  │ (Future)     │  │ (Future)     │  │ (Future)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Data Pipeline Architecture

**Current Pipeline:**
```
OSM PBF → extract_all_osm_data.py → raw/ + derived/ GeoJSON
                                   → generate_3dtiles.py → 3dtiles/
DEM TIF → extract_dem_data.py → terrain/ (elevation tiles)
```

**Future Pipeline (Extensible):**
```
┌─────────────────┐
│ Data Sources    │
│ • OSM PBF       │
│ • DEM           │
│ • Govt CSVs     │
│ • Satellite     │
│ • Real-time API │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ETL Layer       │
│ • Validation    │
│ • Normalization │
│ • Spatial Index │
│ • Vector Embed  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Storage         │
│ • GeoJSON       │
│ • Vector DB     │
│ • Spatial Index │
│ • Cache         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Query API       │
│ • Spatial       │
│ • Semantic      │
│ • Hybrid        │
└─────────────────┘
```

### Advanced AI Integration

**Spatial Language Models (Phase 6)**
- Fine-tune on spatial reasoning tasks (distance, direction, containment)
- Enable complex queries: "What's between the airport and city center?"
- Natural language → spatial query translation

**Vision Models (Phase 6)**
- SAM for 3D building/object segmentation from viewport
- Depth estimation and occlusion reasoning
- Visual question answering: "What am I looking at?"

**Multimodal Reasoning (Phase 6)**
- Combine text + vision + spatial data
- "Is this area greener than the one I just looked at?" → vision + OSM landuse

### Evaluation Framework (Phase 7)

**Geocoding Benchmark**
- 500+ test locations (landmarks, streets, POIs)
- Metrics: Top-1/Top-3 accuracy, MRR
- Target: >95% accuracy

**Spatial Analysis Benchmark**
- Ground truth for "nearby" queries
- Regression tests for known locations
- Target: <5% error vs. ground truth

**Reasoning Evaluation**
- Human-labeled dataset for recommendations
- Compare AI vs. expert judgments
- A/B testing for UX improvements

**Continuous Monitoring**
- Log all queries, responses, feedback
- Automated accuracy alerts
- User satisfaction tracking (target: >4.5/5)

### When to Add Advanced Capabilities

**Add Spatial LM when:**
- 3D tour generation becomes a requirement
- Visibility/occlusion analysis needed
- 3D simulation ("What if we add a building here?")

**Add Vision Models when:**
- Screenshot-based queries needed
- Automatic building/road detection required
- Visual comparison tasks emerge

**Add Vector Search when:**
- Semantic place search needed ("coffee shops with outdoor seating")
- Cross-lingual support required (English + Kannada)
- Fuzzy matching quality insufficient

**Current Recommendation:** The OpenRouter LLM + OSM AreaAnalyzer + Terrain Service combination is sufficient for MVP. Add advanced capabilities incrementally based on user needs and roadmap phases.
