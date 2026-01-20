# Nominatim Offline Geocoder Setup

This guide explains how to set up a local Nominatim instance for offline place search in Valora AI.

## Prerequisites

- **Docker Desktop** installed and running
- At least **8GB RAM** available for Docker
- **50GB+ disk space** for the database (Southern India zone)

## Quick Start

### 1. Start Nominatim (First Time - Import)

```bash
cd windsurf-project
docker-compose up -d
```

**First run will:**
1. Download the Southern India OSM extract (~1.5GB)
2. Import into PostgreSQL (takes 1-4 hours depending on your machine)
3. Start the Nominatim API on port 8088

**Monitor import progress:**
```bash
docker-compose logs -f nominatim
```

### 2. Verify Nominatim is Running

```bash
curl http://localhost:8088/status
```

Should return: `{"status":0,"message":"OK",...}`

### 3. Test a Search

```bash
curl "http://localhost:8088/search?q=tin+factory+bangalore&format=json"
```

Should return JSON with lat/lng for Tin Factory.

### 4. Start the Backend

```bash
# Windows
START_BACKEND.bat

# Or manually
cd backend
pip install -r requirements.txt
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Start the Frontend

```bash
# Windows
START_FRONTEND.bat

# Or manually
npm run dev
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend       │────▶│   Nominatim     │
│   (React)       │     │   (FastAPI)     │     │   (Docker)      │
│   :3000         │     │   :8000         │     │   :8088         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## API Endpoints

### Backend API (localhost:8000)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check (includes Nominatim status) |
| `GET /api/geocode?q=<query>` | Search for a place |
| `GET /api/reverse?lat=<lat>&lng=<lng>` | Reverse geocode |

### Example Geocode Response

```json
{
  "success": true,
  "query": "tin factory",
  "results": [...],
  "top_result": {
    "place_id": 123456,
    "name": "Tin Factory",
    "display_name": "Tin Factory, Swamy Vivekananda Road, Bangalore, Karnataka, India",
    "lat": 13.0123,
    "lng": 77.6234,
    "type": "bus_stop",
    "importance": 0.35,
    "bbox": [77.62, 13.01, 77.63, 13.02]
  }
}
```

## Using a Smaller Extract (Faster Import)

For faster setup, you can use a Bangalore-only extract:

1. Download from BBBike: https://extract.bbbike.org/
2. Select Bangalore area and download as `.osm.pbf`
3. Place in `data/nominatim/` folder
4. Update `docker-compose.yml`:

```yaml
environment:
  PBF_PATH: /nominatim/data/bangalore.osm.pbf
volumes:
  - ./data/nominatim:/nominatim/data
```

## Troubleshooting

### Import is stuck or very slow
- Increase Docker memory to 8GB+
- Use a smaller extract (Bangalore only instead of Southern India)

### "Nominatim unavailable" in app
- Check if container is running: `docker ps`
- Check logs: `docker-compose logs nominatim`
- Verify port 8088 is accessible

### Search returns no results
- Import may not be complete yet
- Try broader search terms
- Check if the place exists in OSM data

### Container keeps restarting
- Check logs for errors
- Ensure enough disk space
- Try removing volume and reimporting: `docker-compose down -v && docker-compose up -d`

## Data Coverage

The default setup uses **Southern India** OSM data, which includes:
- Karnataka (Bangalore)
- Tamil Nadu
- Kerala
- Andhra Pradesh
- Telangana

This covers all major Bangalore localities, landmarks, roads, and POIs.

## Stopping Nominatim

```bash
docker-compose stop
```

Data is persisted in a Docker volume, so next start will be instant.

## Removing Everything

```bash
docker-compose down -v
```

This removes the container AND the imported data. Next start will re-import.
