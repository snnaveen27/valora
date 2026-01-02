# Valora v2.0 - Unified Data Layer

This directory contains all data for the Valora City Intelligence Engine.
Organized for multi-city scalability with support for streaming, uploads, scraped, and folder-based data.

## Directory Structure

```
data/
├── cities/                    # City-specific data (organized by city)
│   ├── bangalore/
│   │   ├── raw/              # Raw scraped data
│   │   ├── processed/        # Cleaned data for ML
│   │   ├── models/           # City-specific trained models
│   │   ├── gis/              # GIS/spatial data
│   │   └── cache/            # API cache
│   ├── mumbai/
│   ├── delhi/
│   ├── hyderabad/
│   ├── chennai/
│   └── pune/
│
├── ingestion/                 # Data ingestion by source type
│   ├── streaming/            # Real-time data streams
│   │   ├── buffer/           # Stream buffer for processing
│   │   ├── processed/        # Processed stream data
│   │   └── failed/           # Failed stream records
│   ├── scraped/              # Web scraped data
│   │   ├── magicbricks/      # MagicBricks scraper output
│   │   ├── 99acres/          # 99acres scraper output
│   │   ├── housing/          # Housing.com scraper output
│   │   └── archive/          # Archived scraper runs
│   ├── api/                  # External API data
│   │   ├── mappls/           # Mappls geocoding/POI cache
│   │   ├── registry/         # Property registry data
│   │   └── government/       # Government data sources
│   └── manual/               # Manually curated data
│       ├── corrections/      # Manual data corrections
│       └── enrichment/       # Manual data enrichment
│
├── uploads/                   # User uploaded files
│   ├── pending/              # Awaiting validation
│   ├── validated/            # Validated, ready to process
│   ├── processed/            # Successfully ingested
│   ├── failed/               # Failed validation/processing
│   └── archive/              # Archived uploads
│
├── shared/                    # Cross-city shared data
│   ├── embeddings/           # Vector embeddings
│   ├── models/               # Shared base models
│   ├── config/               # Configuration files
│   └── cache/                # Shared cache
│
├── exports/                   # Exported reports/data
│   ├── reports/              # Generated reports
│   ├── api_exports/          # API export requests
│   └── scheduled/            # Scheduled export outputs
│
├── staging/                   # Data staging area
│   ├── validation/           # Awaiting validation
│   ├── transform/            # In transformation pipeline
│   └── review/               # Manual review queue
│
├── raw/                       # (Legacy) Old raw data location
│   ├── properties/           # Property listings
│   ├── transactions/         # Transaction data
│   ├── gis/                  # GIS/spatial data
│   ├── pois/                 # Points of interest
│   ├── market/               # Market data
│   └── external/             # External data sources
│
├── processed/                 # Processed/cleaned data
│   ├── training/             # ML training datasets
│   ├── features/             # Feature-engineered data
│   └── analytics/            # Analytics-ready data
│
└── models/                    # Trained ML models
    ├── production/           # Production models
    ├── staging/              # Models under testing
    ├── backups/              # Model backups
    └── metrics/              # Model performance metrics
```

## City Data Structure

Each city folder contains:

| Folder | Contents |
|--------|----------|
| `raw/` | Scraped listings, transactions, POI data |
| `processed/` | Cleaned training data, feature-engineered datasets |
| `models/` | City-specific ML models (price, rental, demand) |
| `gis/` | Ward boundaries, zone data, spatial features |
| `cache/` | API response cache, temporary data |

## Supported Cities

| City | Status | Data |
|------|--------|------|
| Bangalore | ✅ Active | ✅ Available |
| Mumbai | ✅ Active | ⏳ Pending |
| Delhi NCR | ✅ Active | ⏳ Pending |
| Hyderabad | ✅ Active | ⏳ Pending |
| Chennai | ✅ Active | ⏳ Pending |
| Pune | ✅ Active | ⏳ Pending |

## Usage

### Using DataPathManager

```python
from backend.config import get_city_data_path, data_path_manager

# Get paths for a specific city
bangalore_paths = get_city_data_path("bangalore")
print(bangalore_paths.raw)       # data/cities/bangalore/raw
print(bangalore_paths.models)    # data/cities/bangalore/models

# Get specific file paths
price_model = data_path_manager.get_price_model("bangalore")
training_data = data_path_manager.get_training_data("mumbai")

# Check data availability
status = data_path_manager.get_city_data_status("bangalore")
print(status)  # {'has_raw_data': True, 'has_models': True, ...}
```

### Ensure Directory Structure

```python
from backend.config import ensure_data_structure

# Create all city directories
ensure_data_structure()

# Or for specific cities
ensure_data_structure(['bangalore', 'mumbai'])
```

## Data Pipeline

1. **Ingestion**: Raw data → `ingestion/{source_type}/` or `cities/{city}/raw/`
2. **Staging**: Validation → `staging/validation/`
3. **Processing**: Cleaned data → `cities/{city}/processed/` or `processed/`
4. **Training**: Models → `cities/{city}/models/` or `models/`
5. **Serving**: Load from city-specific paths

## Data Source Types

| Type | Description | Location |
|------|-------------|----------|
| **Streaming** | Real-time data feeds (WebSocket, Kafka) | `ingestion/streaming/` |
| **Scraped** | Web scrapers (MagicBricks, 99acres) | `ingestion/scraped/` |
| **API** | External APIs (Mappls, Registry) | `ingestion/api/` |
| **Upload** | User-uploaded files (CSV, Excel, GeoJSON) | `uploads/` |
| **Folder** | Auto-watched folders | `ingestion/manual/` |

## Using the Data Layer Service

```python
from backend.services.data_layer import (
    DataSourceManager,
    IngestionService,
    FileUploadHandler,
    StreamManager,
    FolderWatcher,
    DataQualityService
)

# Manage data sources
manager = DataSourceManager()
sources = await manager.get_all_sources()

# Create ingestion job
ingestion = IngestionService()
job = await ingestion.create_job('src-001', 'incremental')

# Handle file uploads
handler = FileUploadHandler()
upload = await handler.upload_file(content, 'data.csv', 'properties')

# Monitor data quality
quality = DataQualityService()
issues = await quality.get_issues(status='open')
```

## Admin Dashboard

Access the **Data Layer** tab in the Admin Dashboard to:

- **Overview**: View all data sources, records, and quality metrics
- **Sources**: Manage data sources (scrapers, APIs, streams, folders)
- **Uploads**: Upload and process data files
- **Quality**: Monitor and resolve data quality issues
- **Jobs**: Track ingestion jobs and their status

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/data-layer/sources` | GET | List all data sources |
| `/api/data-layer/sources` | POST | Create new data source |
| `/api/data-layer/uploads` | POST | Upload data file |
| `/api/data-layer/jobs` | GET | List ingestion jobs |
| `/api/data-layer/quality/issues` | GET | List quality issues |
| `/api/data-layer/dashboard` | GET | Get dashboard data |

## Adding a New City

1. Add city config to `backend/config/cities.py`
2. Run `ensure_data_structure(['new_city'])`
3. Load raw data to `data/cities/new_city/raw/`
4. Load GIS data to `data/cities/new_city/gis/`
5. Run training pipeline

## Adding a New Data Source

1. Go to Admin Dashboard → Data Layer → Add Source
2. Select source type (API, Scraper, Folder, Stream)
3. Configure connection settings
4. Set sync frequency
5. Monitor health and quality

## Legacy Data

Old data in `data/raw/` and `data/processed/` is preserved for backward compatibility.
New data should use the organized structure above.

---

*Last updated: Valora v2.0 - December 2024*
