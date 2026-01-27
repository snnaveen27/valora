# Valora AI Version History

## Version 2025.2.5 (January 2026)

### 🚀 Major Features
- **Multi-City Architecture**: Added `city_id` support to all tables for city expansion
- **Cities Table**: New table for managing multiple cities
- **System Metadata**: Version tracking and configuration management
- **Incremental FAISS Updates**: No more clearing indexes, deduplication support

### 📊 Data Enhancements
- **1.6M+ Total Records** across all database tables
- **455,066 Open Datasets** from OpenCity.in Bengaluru
- **5,384 Transport Stops** including metro and bus
- **12,767 Government Records** (education, legislative data)
- **Comprehensive GIS Layers**: Ward boundaries, cadastral, infrastructure

### 🧪 Testing
- **29 Sanity Tests** with 28 passing (1 skipped for chat)
- City support verification
- Data integrity checks
- Version verification tests

### 🛠️ Technical Improvements
- FAISS incremental updates (skip duplicates)
- Database backup automation
- Feature audit tooling
- Data organization scripts

### 📁 New Scripts
- `scripts/migrate_city_support.py` - City expansion migration
- `scripts/ingest_backup_data.py` - Backup data ingestion
- `scripts/feature_audit.py` - System feature audit
- `scripts/check_db_status.py` - Database status checker

---

## Version 2025.2.0 (January 2026)

### Features
- Advanced Insights Service
- Database Panel UI
- Real Estate Agents data
- Price tracking and history
- Market intelligence APIs

---

## Version 2025.1.0 (January 2026)

### Initial Release
- 3D CesiumJS visualization
- AI chat with GIS agents
- Property search and valuation
- RAG-powered semantic search
- Simulation engine
- Digital twin capabilities

---

## Upgrade Notes

### From 2025.2.0 to 2025.2.5
1. Run city migration: `python scripts/migrate_city_support.py`
2. Ingest backup data: `python scripts/ingest_backup_data.py`
3. Update FAISS indexes: `python backend/export_to_faiss.py`
4. Restart backend server

### Database Schema Changes (v2.5)
- Added `city_id` column to: properties, pois, buildings, roads, transport_stops, places, terrain_grid, open_datasets, price_history
- New tables: `cities`, `system_metadata`
- New indexes for city-based queries

---

## Roadmap

### Version 2025.3.0 (Planned)
- [ ] Mumbai city data
- [ ] Delhi city data
- [ ] Enhanced property matching
- [ ] Mobile app support

### Version 2026.1.0 (Future)
- [ ] Pan-India coverage (Top 20 cities)
- [ ] Real-time price feeds
- [ ] AR/VR property tours
- [ ] International expansion
