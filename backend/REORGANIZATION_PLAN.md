# Backend Reorganization Plan

## Proposed Structure

```
backend/
├── ai/                          # AI & LLM services
│   ├── gis_agents.py
│   ├── multi_agent_orchestrator.py
│   ├── rag_service.py
│   ├── ai_context.py
│   ├── advanced_reasoning.py
│   ├── multimodal_reasoning.py
│   └── task_planner.py
│
├── spatial/                     # Spatial analysis
│   ├── spatial_reasoning.py
│   ├── spatial_inference.py
│   ├── spatial_3d_reasoning.py
│   ├── spatial_nlp.py
│   ├── spatial_memory.py
│   ├── spatial_memory_graph.py
│   └── terrain_service.py
│
├── analyzers/                   # Data analyzers
│   ├── area_analyzer.py
│   ├── building_analyzer.py
│   ├── network_analyzer.py
│   ├── temporal_analyzer.py
│   ├── viewshed_analyzer.py
│   ├── visual_analyzer.py
│   └── raster_analysis.py
│
├── services/                    # Business services
│   ├── property_service.py
│   ├── locality_service.py
│   ├── apify_service.py
│   ├── payment_service.py
│   ├── enhanced_data_service.py
│   └── realtime_data.py
│
├── intelligence/                # Intelligence engines
│   ├── advanced_insights.py
│   ├── simulation_engine.py
│   ├── narrative_generator.py
│   ├── predictive_model.py
│   ├── valuation_model.py
│   ├── regulatory_intelligence.py
│   └── transaction_intelligence.py
│
├── engines/                     # Specialized engines
│   ├── solar_engine.py
│   ├── occlusion_engine.py
│   ├── pathfinding_3d.py
│   ├── counterfactual_3d.py
│   └── digital_twin.py
│
├── search/                      # Search & indexing
│   ├── hybrid_search.py
│   ├── vector_optimizer.py
│   ├── local_vector_store.py
│   ├── incremental_indexer.py
│   └── query_suggestions.py
│
├── data/                        # Data operations
│   ├── data_collector.py
│   ├── data_enhancer.py
│   ├── learning_loop.py
│   ├── fact_verifier.py
│   ├── insight_cache.py
│   └── query_cache.py
│
├── routes/                      # API routes
│   ├── auth_routes.py
│   ├── admin_routes.py
│   ├── payment_routes.py
│   └── (other route files)
│
├── auth/                        # Authentication
│   ├── user_auth.py
│   └── auth.py
│
├── geo/                         # Geocoding & location
│   ├── local_geocoder.py
│   └── (related files)
│
├── monitoring/                  # Monitoring & ops
│   ├── observability.py
│   └── eval_harness.py
│
├── scrapers/                    # Data scrapers
│   ├── multi_source_scraper.py
│   ├── production_ingestion.py
│   └── import_apify_run.py
│
├── migrations/                  # Database migrations
│   ├── migrate_insight_cache.py
│   ├── migrate_pricing_to_db.py
│   └── (other migrations)
│
├── scripts/                     # Utility scripts
│   ├── analyze_database.py
│   ├── analyze_db_detailed.py
│   └── export_to_faiss.py
│
├── database/                    # Existing - keep as is
├── city_intelligence/           # Existing - keep as is
├── middleware/                  # Existing - keep as is
├── config/                      # Existing - keep as is
├── utils/                       # Existing - keep as is
│
└── server.py                    # Main server - stays in root
└── requirements.txt             # Dependencies - stays in root
```

## Migration Strategy

1. Create new folders
2. Copy files (don't move yet - safer)
3. Update imports in copied files
4. Test server starts
5. If working, delete originals
6. If broken, revert and fix imports

## Critical Files (Don't Move)
- server.py (main entry point)
- requirements.txt
- admin_config.json
- llm_config.json
