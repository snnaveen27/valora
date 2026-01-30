# Valora AI - Redundant & Deprecated Code Audit

**Last Updated:** January 30, 2026  
**Status:** Active audit - items marked for cleanup or consolidation

---

## Summary

| Category | Redundant Files | Action |
|----------|----------------|--------|
| Test Files | 7 | Consolidate into `valora_test_suite.py` |
| Utility Functions | 19 | Extract to `utils/geo.py` |
| Spatial Services | 4 | Keep 2, deprecate 2 |
| Analysis Scripts | 5 | Keep 2, remove 3 |
| Documentation | 3 | Consolidate into README |

---

## 1. DUPLICATE TEST FILES (Action: DEPRECATE)

These test files are now **superseded** by the unified test suite.

| File | Location | Status | Replacement |
|------|----------|--------|-------------|
| `test_gis_agents.py` | backend/ | **DEPRECATED** | `scripts/valora_test_suite.py` |
| `test_intents.py` | backend/ | **DEPRECATED** | `scripts/valora_test_suite.py` |
| `test_faiss.py` | backend/ | **DEPRECATED** | `scripts/valora_test_suite.py` |
| `test_user_queries.py` | backend/ | **DEPRECATED** | `scripts/valora_test_suite.py` |
| `quick_test.py` | scripts/ | **DEPRECATED** | `scripts/valora_test_suite.py` |
| `test_db_direct.py` | scripts/ | **DEPRECATED** | `scripts/valora_test_suite.py` |
| `test_query_service.py` | scripts/ | **DEPRECATED** | `scripts/valora_test_suite.py` |

### Recommended Action
```bash
# Move to deprecated folder or delete
mkdir -p backend/_deprecated
mv backend/test_gis_agents.py backend/_deprecated/
mv backend/test_intents.py backend/_deprecated/
mv backend/test_faiss.py backend/_deprecated/
mv backend/test_user_queries.py backend/_deprecated/
mv scripts/quick_test.py backend/_deprecated/
mv scripts/test_db_direct.py backend/_deprecated/
mv scripts/test_query_service.py backend/_deprecated/
```

---

## 2. DUPLICATE UTILITY FUNCTIONS (Action: EXTRACT TO SHARED MODULE)

The `_haversine_distance()` function is duplicated in **19 files**:

| File | Has Haversine | Should Import From |
|------|---------------|-------------------|
| `advanced_insights.py` | ✓ | `utils/geo.py` |
| `building_analyzer.py` | ✓ | `utils/geo.py` |
| `counterfactual_3d.py` | ✓ | `utils/geo.py` |
| `database/query_service.py` | ✓ | `utils/geo.py` |
| `hybrid_search.py` | ✓ | `utils/geo.py` |
| `network_analyzer.py` | ✓ | `utils/geo.py` |
| `occlusion_engine.py` | ✓ | `utils/geo.py` |
| `property_service.py` | ✓ | `utils/geo.py` |
| `rag_service.py` | ✓ | `utils/geo.py` |
| `realtime_data.py` | ✓ | `utils/geo.py` |
| `regulatory_intelligence.py` | ✓ | `utils/geo.py` |
| `solar_engine.py` | ✓ | `utils/geo.py` |
| `spatial_inference.py` | ✓ | `utils/geo.py` |
| `spatial_memory.py` | ✓ | `utils/geo.py` |
| `spatial_memory_graph.py` | ✓ | `utils/geo.py` |
| `spatial_reasoning.py` | ✓ | `utils/geo.py` |
| `transaction_intelligence.py` | ✓ | `utils/geo.py` |
| `valuation_model.py` | ✓ | `utils/geo.py` |
| `viewshed_analyzer.py` | ✓ | `utils/geo.py` |

### Recommended Action
Create `backend/utils/geo.py` with shared geo utilities:
- `haversine_distance(lat1, lng1, lat2, lng2) -> float`
- `bearing(lat1, lng1, lat2, lng2) -> float`
- `direction_from_bearing(bearing) -> str`
- `meters_to_degrees(meters) -> float`

---

## 3. OVERLAPPING SPATIAL SERVICES (Action: CONSOLIDATE)

### Current State (4 files with overlapping functionality)

| File | Purpose | Lines | Keep? |
|------|---------|-------|-------|
| `spatial_reasoning.py` | H3 indexing, proximity queries | 625 | **KEEP** (core) |
| `spatial_3d_reasoning.py` | True 3D analysis, viewshed, shadow | 588 | **KEEP** (core) |
| `spatial_memory.py` | Session-based location memory | 359 | **MERGE** into `spatial_3d_reasoning.py` |
| `spatial_memory_graph.py` | Precomputed relationships graph | 634 | **KEEP** (distinct purpose) |

### Relationship Diagram
```
┌─────────────────────┐     ┌──────────────────────┐
│ spatial_reasoning   │     │ spatial_3d_reasoning │
│ (H3 + proximity)    │────▶│ (3D + viewshed)      │
└─────────────────────┘     └──────────────────────┘
                                      │
                                      ▼
                            ┌──────────────────────┐
                            │ spatial_memory_graph │
                            │ (precomputed rels)   │
                            └──────────────────────┘
```

### `spatial_memory.py` Analysis
- **Session tracking** - useful but could be simpler
- **Preference learning** - overlaps with `ai_context.py`
- **Recommendation**: Merge into `ai_context.py` or simplify

---

## 4. ANALYSIS/DEBUG SCRIPTS (Action: CLEANUP)

| File | Purpose | Keep? |
|------|---------|-------|
| `analyze_database.py` | DB stats | **KEEP** (useful for debugging) |
| `analyze_db_detailed.py` | Raw data inspection | **REMOVE** (one-time script) |
| `analyze_backup.py` | Backup analysis | **REMOVE** (one-time script) |
| `analyze_scripts.py` | Script analyzer | **REMOVE** (one-time script) |
| `check_db.py` | DB health check | **MERGE** into `analyze_database.py` |
| `check_db_status.py` | Quick status | **MERGE** into `analyze_database.py` |
| `check_system_status.py` | System health | **KEEP** (useful) |
| `verify_system.py` | Verification | **MERGE** into `check_system_status.py` |

### Recommended Consolidated Structure
```
scripts/
├── valora_test_suite.py      # All tests
├── system_health.py          # Merged: check_system_status + verify_system
├── db_analysis.py            # Merged: analyze_database + check_db*
├── ingest/                   # Data ingestion scripts
└── _deprecated/              # Old scripts (for reference)
```

---

## 5. INGESTION SCRIPTS (Action: ORGANIZE)

Multiple ingestion scripts with overlapping patterns:

| File | Data Source | Status |
|------|-------------|--------|
| `ingest_backup_data.py` | Backup files | KEEP |
| `ingest_building_polygons.py` | Building data | KEEP |
| `ingest_extra_data.py` | Misc data | REVIEW |
| `ingest_opencity_data.py` | OpenCity | KEEP |
| `ingest_posted_properties.py` | Properties | KEEP |
| `ingest_price_history.py` | Price history | KEEP |
| `production_ingestion.py` | Combined | **PREFER** (unified) |
| `import_apify_run.py` | Apify data | MERGE into production_ingestion |
| `process_all_backup.py` | Backup processor | MERGE |

### Recommendation
Use `production_ingestion.py` as the main entry point with sub-modules.

---

## 6. DOCUMENTATION FILES (Action: CONSOLIDATE)

| File | Content | Action |
|------|---------|--------|
| `README.md` | Main docs | **KEEP** - make primary |
| `ARCHITECTURE.md` | System design | **KEEP** - technical reference |
| `DATABASE_OPPORTUNITIES.md` | Data gaps | **MERGE** into DATA_STATUS.md |
| `DATA_STATUS.md` | Data state | **KEEP** |
| `DYNAMIC_TASKS_EXAMPLES.md` | Task examples | **MERGE** into README |
| `INVESTOR_PITCH.md` | Business pitch | **KEEP** (separate audience) |
| `MISSING_DATA_SOURCES.md` | Data gaps | **MERGE** into DATA_STATUS.md |
| `QUERIES_LIST.md` | Query examples | **KEEP** (reference) |
| `SCHEMA_REFERENCE.md` | DB schema | **KEEP** |
| `VERSION.md` | Changelog | **KEEP** |

### Recommended Structure
```
docs/
├── README.md                  # Getting started
├── ARCHITECTURE.md            # System design
├── DATA_STATUS.md             # Data state + opportunities + missing
├── SCHEMA_REFERENCE.md        # DB schema
├── QUERIES_LIST.md            # Query examples
└── business/
    └── INVESTOR_PITCH.md      # Business docs
```

---

## 7. SERVICES WITH SIMILAR NAMES (Clarification)

| Service | File | Purpose | Keep? |
|---------|------|---------|-------|
| `LocalityService` | `locality_service.py` | Locality profiles | **KEEP** |
| `EnhancedDataService` | `enhanced_data_service.py` | Area insights | **KEEP** |
| `AdvancedInsightsService` | `advanced_insights.py` | Market intelligence | **REVIEW** - overlaps with enhanced_data |
| `PropertyService` | `property_service.py` | Property search | **KEEP** |
| `RAGService` | `rag_service.py` | Vector search | **KEEP** |

### Potential Overlap
- `EnhancedDataService` vs `AdvancedInsightsService` - similar area analysis
- Consider merging into single `AreaIntelligenceService`

---

## 8. VECTOR STORE FILES (Action: KEEP BOTH FOR NOW)

| File | Purpose | Status |
|------|---------|--------|
| `local_vector_store.py` | FAISS local store | **KEEP** (offline mode) |
| `rag_service.py` | Hybrid search + Pinecone | **KEEP** (production mode) |
| `hybrid_search.py` | Hybrid retrieval | **KEEP** (used by RAG) |
| `vector_optimizer.py` | Index optimization | **KEEP** |
| `export_to_faiss.py` | FAISS export | **KEEP** |
| `build_faiss_index.py` | Index builder | **MERGE** into export_to_faiss |
| `update_faiss_indexes.py` | Index updater | **MERGE** into export_to_faiss |

---

## 9. SCRAPERS (Action: CONSOLIDATE)

| File | Source | Status |
|------|--------|--------|
| `multi_source_scraper.py` | Multiple sources | **KEEP** (unified) |
| `apify_service.py` | Apify integration | **KEEP** |
| `google_maps_scraper.py` | Google Maps | **MERGE** into multi_source |
| `scrape_agents_reviews.py` | Agent reviews | **MERGE** into multi_source |
| `scrape_all_bangalore_data.py` | Bangalore data | **MERGE** into multi_source |
| `scrape_opencity.py` | OpenCity | **MERGE** into multi_source |
| `smart_opencity_downloader.py` | OpenCity smart | **MERGE** |

---

## 10. CITY INTELLIGENCE (Action: KEEP)

The `city_intelligence/` folder is well-organized:
- `locality_personality.py` - Locality archetypes
- `evolution_timeline.py` - Growth phases
- `risk_indexes.py` - Risk calculation
- `causal_reasoning.py` - Causal analysis
- `knowledge_graph.py` - Knowledge graph

**Status:** Good organization, no redundancy.

---

## Action Priority

### Phase 1 (Immediate) ✅ COMPLETED
1. ✅ Create `backend/_deprecated/` folder
2. ✅ Move deprecated test files (7 files moved)
3. ✅ `backend/utils/geo.py` already exists with shared functions

### Phase 2 (This Week) ✅ COMPLETED
1. ✅ Merged documentation files → `DATA_STATUS.md`
   - Deleted: `DATABASE_OPPORTUNITIES.md`, `MISSING_DATA_SOURCES.md`
2. ✅ Consolidated ingestion scripts → `scripts/ingest/`
   - Moved 6 ingest_*.py files to scripts/ingest/
3. ✅ Reviewed `AdvancedInsightsService` vs `EnhancedDataService`:
   - **AdvancedInsightsService**: Market/investment focus (USED in server.py)
   - **EnhancedDataService**: Data enrichment (NOT used in production)
   - **Verdict**: Complementary, not duplicative. Keep both.
   - **Action**: Consider integrating EnhancedDataService into gis_agents.py

### Phase 3 (Later) ✅ COMPLETED
1. ✅ Consolidated scraper files → `scripts/_deprecated/`
   - Moved: google_maps_scraper.py, scrape_agents_reviews.py, scrape_all_bangalore_data.py, scrape_opencity.py
   - Main scraper: `backend/multi_source_scraper.py`
2. ✅ Unified vector store scripts → `scripts/_deprecated/`
   - Moved: build_faiss_index.py, update_faiss_indexes.py
   - Main script: `backend/export_to_faiss.py`
3. ✅ Reviewed `spatial_memory.py` vs `ai_context.py`:
   - **spatial_memory.py**: Session tracking, preferences, comparisons
   - **ai_context.py**: Self-learning, patterns, knowledge graph
   - **Verdict**: Complementary. Keep separate for now.

---

## File Counts After Cleanup (Actual - Jan 30, 2026)

| Action | Files | Details |
|--------|-------|---------|
| Moved to `backend/_deprecated/` | 7 | test_*.py, quick_test.py |
| Moved to `scripts/_deprecated/` | 6 | scrapers, faiss scripts |
| Moved to `scripts/ingest/` | 6 | ingest_*.py files |
| Deleted | 2 | DATABASE_OPPORTUNITIES.md, MISSING_DATA_SOURCES.md |

| Location | Before | After | Change |
|----------|--------|-------|--------|
| backend/*.py | 54 | 48 | -6 (to _deprecated) |
| scripts/*.py | 39 | 27 | -12 (to ingest/ and _deprecated/) |
| Root *.md | 10 | 8 | -2 (merged) |

**Total:** 20 files reorganized/removed for cleaner structure

---

## ✨ New Implementations (Jan 30, 2026)

### 1. CinemaOverlay Component ✅
- **File:** `src/components/CinemaOverlay.jsx`
- **Features:**
  - Letterbox cinematic bars
  - Narration panel with controls
  - Play/Pause/Stop buttons
  - Progress bar
  - ESC to exit

### 2. DrawingTools Component ✅
- **File:** `src/components/DrawingTools.jsx`
- **Features:**
  - Draw polygon areas on map
  - Create buffer zones with radius
  - Clear drawings
  - Configurable buffer radius (500m-10km)

### 3. Map Drawing Integration ✅
- **File:** `src/spatial/OnlineOSMMap.jsx`
- **Features:**
  - Polygon drawing with click-to-add-points
  - Buffer zone visualization (ellipse overlay)
  - Right-click to finish polygon
  - Events dispatched for analysis

### 4. Cinema Mode in MainApp ✅
- **File:** `src/components/MainApp.jsx`
- **Features:**
  - Cinema mode state management
  - Narration updates via UI commands
  - Auto-triggered by simulations

### 5. User Preference Memory API ✅
- **File:** `backend/server.py`
- **Endpoints:**
  - `GET /api/preferences/{user_id}` - Get preferences
  - `POST /api/preferences/{user_id}` - Update preferences
  - `POST /api/preferences/{user_id}/location` - Record visits
  - `DELETE /api/preferences/{user_id}` - Clear history
- **Features:**
  - Preferred areas, budget, property types
  - Location visit tracking
  - Comparison history
