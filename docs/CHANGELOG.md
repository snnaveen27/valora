# Changelog

All notable changes to the Valora City Intelligence Engine are documented in this file.

---

## [2.1.0] - 2024-12-18

### Summary
Major release introducing the **City Intelligence Engine** with knowledge substrate, reasoning layer, narrative generation, and memory systems. This version represents a complete, production-ready platform.

### Added

#### City Intelligence Module
- **LocalityStateService** (`backend/services/city_intel/locality_state_service.py`) - Ward-level market snapshots with real-time metrics
- **GrowthPhaseClassifier** (`backend/services/city_intel/growth_phase_classifier.py`) - Classifies localities as Emerging/Accelerating/Mature/Saturated
- **RiskIndexCalculator** (`backend/services/city_intel/risk_index_calculator.py`) - Composite risk scoring (Flood, Infrastructure, Liquidity, Regulatory)
- **ScenarioSimulator** (`backend/services/city_intel/scenario_simulator.py`) - Infrastructure what-if analysis with timeline projections
- **NarrativeGenerator** (`backend/services/city_intel/narrative_generator.py`) - LLM-powered natural language explanations

#### Digital Twin Viewer
- **DigitalTwinViewer** (`src/components/DigitalTwinViewer.jsx`) - 3D property visualization using Three.js/React Three Fiber
- Floor-by-floor interactive view with occupancy colors
- Day/night mode, auto-rotate, orbit controls
- Environmental metrics (AQI, noise, green cover)
- Investment analysis panels

#### Multi-Agent Orchestrator
- **ValoraOrchestrator** (`backend/services/multi_agent_orchestrator.py`) - Unified coordination of 20+ specialized agents
- Planner → Executor → Critic → Narrator pipeline
- Geospatial command processing with natural language
- City intelligence service integration

#### Voice Interface
- **DeepgramService** (`backend/services/voice/deepgram_service.py`) - Speech-to-text and TTS
- Real-time WebSocket streaming transcription
- Multi-language support (en-IN, hi, ta, te, kn, mr)
- Real estate keyword boosting for accuracy
- **VoiceInput** component (`src/components/VoiceInput.jsx`)

#### Data Scraping Pipeline
- **ScrapingScheduler** (`backend/services/scraping/scraping_scheduler.py`) - Cron-based Apify job management
- Default scheduled jobs: Localities (weekly), POIs (monthly), News (daily), Prices (daily)
- Run history tracking and manual trigger support

#### LLM Self-Learning
- **LLMProvider** (`backend/services/llm/llm_provider.py`) - Multi-provider abstraction layer
- **SelfLearning** (`backend/services/llm/self_learning.py`) - Feedback collection and quality scoring
- **AutoTuning** (`backend/services/llm/auto_tuning.py`) - Teacher-student fine-tuning pipeline

#### Database Enhancements
- City Intelligence schema (`backend/database/schemas/city_intel/schema_city_intel.sql`)
- Tables: `localities`, `locality_state`, `locality_state_history`, `predictions`, `model_performance`, `calibration_suggestions`, `infrastructure_events`, `scenario_simulations`
- Repository layer with connection pooling (`backend/database/repositories/city_intel_repository.py`)

#### API Endpoints
- `/api/city-intel/locality/{locality}` - Locality profile
- `/api/city-intel/growth-phase/{locality}` - Growth phase classification
- `/api/city-intel/risk/{locality}` - Risk assessment
- `/api/city-intel/scenario/simulate` - Infrastructure impact simulation
- `/api/city-intel/narrative/{locality}` - AI-generated narratives
- `/api/voice/*` - Voice transcription and TTS endpoints
- `/api/scraping/*` - Scraping job management
- `/api/llm/*` - LLM provider and learning endpoints
- `/api/digital-twin/*` - 3D building data endpoints

### Changed
- **Admin Dashboard** reorganized with architecture-aligned tabs: Data Layer, Knowledge Layer, Intelligence Layer, Orchestration
- **Multi-city support** via `backend/config/cities.py` - Bangalore, Mumbai, Delhi, Hyderabad, Chennai, Pune
- **API Reference** updated to reflect all implemented endpoints

### Fixed
- Multi-agent orchestrator indentation errors in `_aggregate_results`
- Empty chat responses now fallback to LLM properly
- Pinecone import made optional to prevent crashes

### Technical Debt Addressed
- Removed obsolete `unused/` folder
- Removed duplicate chat components
- Unified frontend to single `ChatPanelMultiAgent`

---

## [2.0.0] - 2024-11-15

### Added
- VALORA-DMPE+ architecture documentation
- Raster Agent for satellite imagery analysis (U-Net, NDVI/NDBI)
- Graph Agent for property network analysis (GraphSAGE)
- Complete agent stacks: Valuation, Forecasting, Spatial, Risk, Explainability

### Changed
- Unified DMPE, Digital Twins, and Multi-Agent System into coherent architecture
- 5-layer architecture: Presentation → Orchestration → Intelligence → Knowledge → Data

---

## [1.0.0] - 2024-10-01

### Added
- Initial Valora AI platform
- DMPE (Dynamic Market Prediction Engine)
- Mappls map integration
- Basic chat interface with OpenRouter
- Property search and recommendations
- PostGIS spatial database

---

## Version Naming

- **Major** (X.0.0): Breaking changes or major architecture overhauls
- **Minor** (0.X.0): New features, backward compatible
- **Patch** (0.0.X): Bug fixes, minor improvements
