# Unified PostgreSQL Database System

## Overview

This database system provides a robust, extensible foundation for the real estate platform. It uses PostgreSQL with PostGIS for geospatial capabilities and supports both structured and unstructured data.

## Features

- **Unified Storage**: All data (properties, transactions, POIs, market stats) in one database
- **Geospatial Support**: PostGIS for location-based queries and spatial analysis
- **Intelligent ETL**: Automatically extracts metadata from filenames and folder structure
- **Flexible Schema**: JSONB fields for unstructured data
- **Performance Optimized**: Indexes, materialized views, and connection pooling
- **AI-Ready**: Designed to support multi-agent AI systems

## Quick Start

### 1. Install PostgreSQL with PostGIS

**Windows:**
```powershell
# Install PostgreSQL from https://www.postgresql.org/download/windows/
# Or using Chocolatey:
choco install postgresql14 postgis

# Start PostgreSQL service
net start postgresql-x64-14
```

**macOS:**
```bash
brew install postgresql@14 postgis
brew services start postgresql@14
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install postgresql-14 postgresql-14-postgis-3
sudo systemctl start postgresql
```

### 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE realestate;

# Connect to the new database
\c realestate

# Create PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

# Exit
\q
```

### 3. Configure Environment

Create/update `.env` file in project root:

```env
# Database Configuration
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/realestate

# Or with full connection string:
# DATABASE_URL=postgresql://username:password@host:port/database

# Optional: Connection pool settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

### 4. Initialize Database Schema

```bash
cd backend
python -m database.init_db
```

This will:
- Create all tables
- Set up indexes and constraints
- Create views and materialized views
- Create stored procedures and triggers
- Initialize reference data

### 5. Ingest Data

```bash
# Place CSV files in data/raw/ directory
# The system will intelligently extract metadata from:
# - Filenames (e.g., "bangalore_2bhk_flats_2024.csv")
# - Folder structure (e.g., "data/raw/mumbai/commercial/")

# Run ETL
python -m services.run_etl
```

## Database Schema

### Core Tables

#### properties
Main table storing all property listings with:
- Core attributes (price, area, bedrooms, etc.)
- Location (city, locality, coordinates)
- Geospatial data (PostGIS geography type)
- Flexible metadata (JSONB)
- Data quality tracking

#### transactions
Actual sale/rental transactions for model validation

#### pois
Points of interest (metro, hospitals, schools, malls)

#### property_spatial_features
Precomputed distances and density metrics

#### market_statistics
Aggregated market metrics by city/locality/property type

#### projects
Builder projects and developments

### Supporting Tables

- `rental_listings`: Rental-specific data
- `macro_indicators`: Economic indicators
- `zoning_data`: Land use and planning data
- `ml_models`: Model versioning and tracking
- `prediction_logs`: Prediction history for monitoring
- `raw_data_staging`: ETL tracking

## Intelligent Metadata Extraction

The system automatically extracts information from filenames and paths:

### Examples

```
File: bangalore_2bhk_flats_magicbricks_2024.csv
Extracted:
- City: Bangalore
- Property Type: residential
- Property Subtype: 2bhk
- Source: magicbricks
- Date: 2024-01-01

File: data/raw/mumbai/commercial/office_bandra_rent.csv
Extracted:
- City: Mumbai
- Property Type: commercial
- Property Subtype: office_space
- Locality: bandra (if not in file)
- Listing Type: rent
```

### Supported Patterns

**Cities**: bangalore, mumbai, delhi, pune, hyderabad, chennai, etc.

**Property Types**:
- Residential: 1bhk, 2bhk, 3bhk, 4bhk, 5bhk, flat, apartment, house, villa, plot
- Commercial: office, shop, showroom, warehouse, godown, industrial
- Other: agricultural, farm house

**Sources**: magicbricks, 99acres, housing, makaan, registry, scraped

**Listing Types**: sale, rent, lease

## Data Quality

The system tracks data quality with:
- **data_quality_score**: 0-1 score based on completeness
- **missing_fields**: JSONB array of missing critical fields
- **metadata validation**: Automatic checks during ingestion

Critical fields:
- price
- area_sqft
- city
- locality
- property_type

## Querying

### Basic Queries

```python
from backend.database.connection import db_manager
from sqlalchemy import text

# Get properties in a city
with db_manager.get_session() as session:
    result = session.execute(
        text("SELECT * FROM properties WHERE city = :city LIMIT 10"),
        {"city": "Bangalore"}
    )
    properties = result.fetchall()
```

### Geospatial Queries

```python
# Find properties within 2km of a point
with db_manager.get_session() as session:
    result = session.execute(
        text("""
            SELECT id, locality, price,
                   ST_Distance(location, ST_GeogFromText(:point)) / 1000 as distance_km
            FROM properties
            WHERE ST_DWithin(location, ST_GeogFromText(:point), 2000)
            ORDER BY distance_km
        """),
        {"point": "POINT(77.5946 12.9716)"}  # Bangalore center
    )
```

### Using Views

```python
# Get enriched active listings
with db_manager.get_session() as session:
    result = session.execute(
        text("""
            SELECT * FROM active_listings_enriched
            WHERE city = :city
            AND price BETWEEN :min_price AND :max_price
        """),
        {"city": "Bangalore", "min_price": 5000000, "max_price": 15000000}
    )
```

## Performance Optimization

### Indexes

All critical columns are indexed:
- city, locality, property_type
- price ranges
- dates
- geospatial (GIST indexes)
- JSONB fields (GIN indexes)

### Materialized Views

Refresh periodically for performance:

```bash
# From command line
psql -U postgres -d realestate -c "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_city_summary"

# Or from Python
db_manager.refresh_materialized_views()
```

### Maintenance

Run regularly:

```python
db_manager.vacuum_analyze()  # Optimize tables
```

## API Integration

### FastAPI Endpoints

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from backend.database.connection import get_db

@app.get("/api/properties")
async def list_properties(
    city: str,
    db: Session = Depends(get_db)
):
    properties = db.execute(
        text("SELECT * FROM properties WHERE city = :city"),
        {"city": city}
    ).fetchall()
    return properties
```

## Extending the Schema

### Adding New Fields

1. Add column to schema.sql
2. Update intelligent_etl_service.py column mappings
3. Re-run migrations

### Adding New Tables

1. Define table in schema.sql
2. Create corresponding SQLAlchemy models if needed
3. Update ETL service to populate new table

## Monitoring

### Health Check

```python
from backend.database.connection import health_check

status = health_check()
# Returns:
# {
#     "status": "healthy",
#     "database_connected": true,
#     "postgis_enabled": true,
#     "pool_size": 10,
#     "checked_out_connections": 2
# }
```

### Query Performance

```sql
-- Show slow queries
SELECT * FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Show table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Backup and Restore

### Backup

```bash
# Full database backup
pg_dump -U postgres -d realestate -F c -f backup_$(date +%Y%m%d).dump

# Schema only
pg_dump -U postgres -d realestate -s -f schema_backup.sql

# Data only
pg_dump -U postgres -d realestate -a -f data_backup.sql
```

### Restore

```bash
# Restore from custom format
pg_restore -U postgres -d realestate_new backup_20240101.dump

# Restore from SQL
psql -U postgres -d realestate_new < schema_backup.sql
```

## Troubleshooting

### Connection Issues

```python
# Test connection
from backend.database.connection import db_manager

if not db_manager.test_connection():
    print("Check DATABASE_URL in .env file")
    print("Ensure PostgreSQL service is running")
```

### PostGIS Not Available

```bash
# Install PostGIS extension
psql -U postgres -d realestate
CREATE EXTENSION IF NOT EXISTS postgis;
```

### Performance Issues

1. Check indexes: `\di` in psql
2. Analyze query plans: `EXPLAIN ANALYZE SELECT ...`
3. Run VACUUM ANALYZE
4. Check connection pool settings

## Migration from CSV Files

The system automatically handles CSV files in `data/raw/`. Simply:

1. Place CSV files in `data/raw/`
2. Run `python -m services.run_etl`
3. Data will be ingested with metadata extraction
4. Original files are tracked in `raw_data_staging` table

## Future Enhancements

- [ ] Automatic schema migrations with Alembic
- [ ] Real-time data sync from external sources
- [ ] Advanced spatial analytics (heatmaps, clustering)
- [ ] Time-series optimizations (TimescaleDB extension)
- [ ] Full-text search (pg_trgm improvements)
- [ ] Data versioning and audit trails
- [ ] Multi-tenancy support
- [ ] Replication and high availability

## Support

For issues or questions:
1. Check logs in `backend/logs/`
2. Run database health check
3. Verify PostgreSQL/PostGIS installation
4. Check `.env` configuration
