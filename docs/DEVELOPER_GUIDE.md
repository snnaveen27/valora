# Developer Guide

## Prerequisites

- **Node.js** 18+
- **Python** 3.11+
- **PostgreSQL** 15+ with PostGIS 3.4
- **Git**

---

## Quick Setup

```bash
# 1. Clone and enter project
cd windsurf-project

# 2. Install Node dependencies
npm install

# 3. Create Python virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 6. Initialize database
python backend/database/init_multidb.py

# 7. Start all services
python start.py
```

---

## Environment Variables

```env
# Database
CORE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/realestate_core
SPATIAL_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/realestate_spatial
VECTOR_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/realestate_vectors

# APIs
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free
MAPPLS_API_KEY=your_mappls_key
VITE_MAPPLS_API_KEY=your_mappls_key

# Ports
PORT=3001
VITE_PORT=3000
```

---

## Database Setup

### Create Databases

```sql
CREATE DATABASE realestate_core;
CREATE DATABASE realestate_spatial;
CREATE DATABASE realestate_vectors;
```

### Enable Extensions

```sql
-- In realestate_spatial
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- In realestate_vectors
CREATE EXTENSION IF NOT EXISTS vector;

-- In all databases
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

### Initialize Schemas

```bash
python backend/database/init_multidb.py
```

---

## Data Ingestion

### Load Property Data

```bash
# Place CSV files in data/raw/properties/
# Then run:
python scripts/utilities/load_properties.py
```

### Run ETL Pipeline

```bash
python backend/services/run_etl.py --pattern "*.csv" --compute-spatial
```

### Load GIS Data

GIS layers should be loaded into the spatial database using QGIS or ogr2ogr:

```bash
# Example: Load ward boundaries
ogr2ogr -f "PostgreSQL" \
  PG:"host=localhost dbname=realestate_spatial user=postgres" \
  bbmp_wards.geojson \
  -nln gis_wards \
  -overwrite
```

---

## Running Services

### Option 1: All-in-One

```bash
python start.py
```

### Option 2: Individual Services

```bash
# Terminal 1: Backend API
python -m uvicorn backend.api.main:app --port 8000 --reload

# Terminal 2: Chat Server
npm start

# Terminal 3: Frontend
npm run dev
```

---

## Project Structure

```
windsurf-project/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── map_endpoints.py     # Map/spatial routes
│   │   ├── property_endpoints.py
│   │   ├── prediction_endpoints.py
│   │   ├── recommendation_endpoints.py
│   │   └── multi_agent_endpoints.py
│   ├── services/
│   │   ├── dmpe_engine.py       # Core prediction engine
│   │   ├── dmpe_enhanced.py     # GIS-enhanced predictions
│   │   ├── geospatial_agent.py  # Spatial analysis
│   │   ├── multi_agent_orchestrator.py
│   │   ├── advanced_prediction_engine.py
│   │   ├── etl_service.py       # Data ingestion
│   │   └── agents/              # Specialized agents
│   ├── database/
│   │   ├── connection.py        # Single DB manager
│   │   ├── multiconnection.py   # Multi-DB manager
│   │   ├── init_db.py
│   │   ├── init_multidb.py
│   │   └── schemas/             # SQL schema files
│   └── models/                  # Trained ML models
├── src/
│   ├── components/
│   │   ├── ChatPanelMultiAgent.jsx
│   │   ├── InteractiveMapView.jsx
│   │   └── ...
│   ├── App.jsx
│   └── main.jsx
├── scripts/
│   ├── startup/                 # Service launchers
│   ├── utilities/               # Data loading, checks
│   └── tests/                   # Test scripts
├── data/
│   ├── raw/                     # Raw CSV files
│   └── processed/               # Processed data
└── docs/                        # Documentation
```

---

## Adding New Endpoints

1. Create route file in `backend/api/`
2. Define FastAPI router
3. Register in `backend/api/main.py`

```python
# backend/api/my_endpoints.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/my-feature", tags=["my-feature"])

@router.get("/")
async def my_endpoint():
    return {"message": "Hello"}

# backend/api/main.py
from backend.api.my_endpoints import router as my_router
app.include_router(my_router)
```

---

## Adding New Agents

1. Create agent file in `backend/services/agents/`
2. Implement agent class with `process()` method
3. Register in orchestrator

```python
# backend/services/agents/my_agent.py
class MyAgent:
    def __init__(self):
        pass
    
    async def process(self, query: str, context: dict) -> dict:
        # Agent logic here
        return {"result": "..."}

# Register in multi_agent_orchestrator.py
from backend.services.agents.my_agent import MyAgent
self.my_agent = MyAgent()
```

---

## Testing

```bash
# Run all tests
python -m pytest backend/tests/

# Test specific module
python -m pytest backend/tests/test_dmpe.py

# Test with coverage
python -m pytest --cov=backend backend/tests/

# Manual API tests
python scripts/tests/test_complete_system.py
```

---

## Code Style

- **Python:** Black formatter, 88 char line length
- **JavaScript:** ESLint + Prettier
- **SQL:** Uppercase keywords, lowercase identifiers

```bash
# Format Python
black backend/

# Lint JavaScript
npm run lint
```

---

## Debugging

### Backend Logs

```bash
# Set log level
export LOG_LEVEL=DEBUG
python -m uvicorn backend.api.main:app --port 8000 --reload
```

### Database Queries

```python
# Enable SQLAlchemy echo
engine = create_engine(url, echo=True)
```

### Frontend

- React DevTools in browser
- Network tab for API calls
- Console for errors

---

## Common Issues

### Port Already in Use

```bash
# Find and kill process
netstat -ano | findstr :8000
taskkill /F /PID <pid>
```

### PostGIS Not Found

```sql
-- Check if installed
SELECT PostGIS_Version();

-- Install if missing
CREATE EXTENSION postgis;
```

### Import Errors

```bash
# Ensure PYTHONPATH is set
set PYTHONPATH=%cd%  # Windows
export PYTHONPATH=$(pwd)  # Linux/Mac
```

---

## Deployment

### Build Frontend

```bash
npm run build
# Output in dist/
```

### Docker (Planned)

```bash
docker-compose up -d
```

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure proper database credentials
- [ ] Set up SSL/TLS
- [ ] Configure CORS for production domain
- [ ] Set up monitoring/logging
- [ ] Configure rate limiting
