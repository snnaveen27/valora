"""
Valora AI - Data Ingestion Scripts
===================================

Consolidated ingestion module. Use run_ingestion.py for unified access.

Scripts:
- ingest_backup_data.py      - Government/backup data
- ingest_building_polygons.py - Building footprints
- ingest_extra_data.py       - Miscellaneous data
- ingest_opencity_data.py    - OpenCity datasets
- ingest_posted_properties.py - Property listings
- ingest_price_history.py    - Historical prices

Main production service:
- backend/production_ingestion.py - Unified ingestion with deduplication
"""
