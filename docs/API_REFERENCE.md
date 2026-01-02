# API Reference

> **Version:** 2.1 | **Last Updated:** December 18, 2024

Base URLs:
- **Backend API:** `http://localhost:8000`
- **Chat API:** `http://localhost:3001` (legacy Express)

---

## Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Backend health check |
| `/api/health` | GET | Chat API health check |

---

## Properties

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/properties` | GET | List all properties |
| `/api/properties/all` | GET | Get all properties with spatial data |
| `/api/properties/by-area` | GET | Get properties within a bounding box |
| `/api/properties/stats` | GET | Property statistics summary |
| `/api/properties/list` | GET | Paginated property list |
| `/api/properties/top` | GET | Top properties by criteria |

### Query Parameters
- `city` — Filter by city
- `locality` — Filter by locality
- `min_price`, `max_price` — Price range
- `property_type` — Type filter (apartment, villa, plot, etc.)
- `limit`, `offset` — Pagination

---

## Market Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/market/summary` | GET | Market overview statistics |
| `/api/market/hotspots` | GET | Investment hotspot areas |
| `/api/analytics/price-distribution` | GET | Price distribution data |

---

## Predictions (DMPE)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/predict/price` | POST | Predict property price |
| `/api/predict/rental-yield` | POST | Predict rental yield |
| `/api/predict/demand` | POST | Predict demand index |
| `/api/predict/comprehensive` | POST | Full prediction with all metrics |

### Request Body (Price Prediction)
```json
{
  "area_sqft": 1200,
  "bedrooms": 3,
  "bathrooms": 2,
  "floor": 5,
  "total_floors": 12,
  "age_years": 3,
  "latitude": 12.9716,
  "longitude": 77.5946,
  "locality": "Whitefield",
  "property_type": "apartment"
}
```

### Response
```json
{
  "predicted_price": 8500000,
  "confidence": 0.85,
  "price_range": {
    "low": 7800000,
    "high": 9200000
  },
  "factors": {
    "location_premium": 0.15,
    "infrastructure_score": 0.72,
    "demand_index": 0.68
  }
}
```

---

## Map & Spatial

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/map/geocode` | GET | Geocode address to coordinates |
| `/api/map/reverse-geocode` | GET | Reverse geocode coordinates |
| `/api/map/analyze-polygon` | POST | Analyze properties within polygon |
| `/api/map/buffer-zone` | POST | Create buffer zone analysis |
| `/api/map/isochrone` | POST | Generate isochrone polygons |
| `/api/map/layers` | GET | Get available map layers |

### Polygon Analysis Request
```json
{
  "polygon": {
    "type": "Polygon",
    "coordinates": [[[77.5, 12.9], [77.6, 12.9], [77.6, 13.0], [77.5, 13.0], [77.5, 12.9]]]
  }
}
```

---

## Multi-Agent System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/multi-agent/chat` | POST | Chat with AI assistant |
| `/api/multi-agent/analyze-document` | POST | Analyze uploaded document |
| `/api/multi-agent/geospatial-query` | POST | Spatial analysis query |
| `/api/multi-agent/predictive-trends` | POST | Get predictive trends |
| `/api/multi-agent/comprehensive-analysis` | POST | Full analysis report |

### Chat Request
```json
{
  "message": "Compare Whitefield and Sarjapur for investment",
  "session_id": "user-123",
  "context": {
    "polygon": null,
    "filters": {}
  }
}
```

### Chat Response
```json
{
  "response": "Based on current market data...",
  "confidence": 0.82,
  "map_action": {
    "type": "highlight_zones",
    "zones": ["Whitefield", "Sarjapur"]
  },
  "recommendations": [...],
  "sources": [...]
}
```

---

## Recommendations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/recommendations` | POST | Get property recommendations |
| `/api/recommendations/top-investments` | GET | Top investment opportunities |
| `/api/recommendations/similar-properties/{id}` | GET | Similar properties |
| `/api/recommendations/personalized` | POST | Personalized recommendations |

---

## City Intelligence ✅ IMPLEMENTED

**File:** `backend/api/city_intel_endpoints.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/city-intel/locality/{locality}` | GET | Locality state snapshot |
| `/api/city-intel/localities` | GET | List all localities |
| `/api/city-intel/growth-phase/{locality}` | GET | Growth phase classification |
| `/api/city-intel/risk/{locality}` | GET | Risk assessment |
| `/api/city-intel/scenario/simulate` | POST | Infrastructure impact simulation |
| `/api/city-intel/narrative/{locality}` | GET | AI-generated narrative |
| `/api/city-intel/dashboard` | GET | Combined dashboard data |
| `/api/city-intel/feedback/log-prediction` | POST | Log prediction for tracking |
| `/api/city-intel/feedback/submit` | POST | Submit actual value feedback |
| `/api/city-intel/feedback/performance` | GET | Model performance metrics |

### Locality State Request
```bash
curl http://localhost:8000/api/city-intel/locality/Whitefield?city=bangalore
```

### Locality State Response
```json
{
  "success": true,
  "source": "database",
  "data": {
    "locality": "Whitefield",
    "city": "bangalore",
    "market_metrics": {
      "avg_price_sqft": 7800,
      "median_price": 9500000,
      "price_change_12m": 14.2
    },
    "supply_demand": {
      "active_listings": 245,
      "absorption_rate": 4.2,
      "days_on_market_avg": 45
    },
    "growth_phase": "accelerating",
    "risk_index_overall": 0.25
  }
}
```

### Scenario Simulation Request
```bash
curl -X POST http://localhost:8000/api/city-intel/scenario/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "locality": "Whitefield",
    "city": "bangalore",
    "infrastructure_event": "metro",
    "distance_km": 1.0,
    "timeline_months": 24
  }'
```

### Scenario Simulation Response
```json
{
  "success": true,
  "data": {
    "locality": "Whitefield",
    "infrastructure": "metro",
    "projected_impact": {
      "price_appreciation_pct": 12.0,
      "rental_yield_change_pct": 7.2,
      "demand_increase_pct": 14.4
    },
    "timeline_breakdown": [
      {"month": 6, "cumulative_impact_pct": 2.4},
      {"month": 12, "cumulative_impact_pct": 5.4},
      {"month": 24, "cumulative_impact_pct": 10.8}
    ],
    "confidence": 0.75
  }
}
```

---

## Digital Twin ✅ IMPLEMENTED

**File:** `backend/api/digital_twin_endpoints.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/digital-twin/building/{id}` | GET | Building 3D data |
| `/api/digital-twin/floor/{id}` | GET | Floor details |
| `/api/digital-twin/unit/{id}` | GET | Unit information |
| `/api/digital-twin/environmental/{id}` | GET | Environmental metrics |

---

## Voice ✅ IMPLEMENTED

**File:** `backend/api/voice_endpoints.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/voice/health` | GET | Service health check |
| `/api/voice/transcribe` | POST | Transcribe base64 audio |
| `/api/voice/transcribe/upload` | POST | Transcribe uploaded file |
| `/api/voice/tts` | POST | Text-to-speech synthesis |
| `/api/voice/stream` | WebSocket | Real-time streaming |
| `/api/voice/commands` | GET | List voice commands |
| `/api/voice/languages` | GET | Supported languages |

### Transcription Request
```bash
curl -X POST http://localhost:8000/api/voice/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "audio_base64": "<base64_encoded_audio>",
    "content_type": "audio/wav",
    "language": "en-IN"
  }'
```

---

## Data Scraping ✅ IMPLEMENTED

**File:** `backend/api/scraping_endpoints.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scraping/status` | GET | System status |
| `/api/scraping/dashboard` | GET | Dashboard data |
| `/api/scraping/jobs` | GET | List all jobs |
| `/api/scraping/jobs/{id}` | GET | Job details |
| `/api/scraping/jobs` | POST | Create new job |
| `/api/scraping/jobs/{id}/run` | POST | Trigger manual run |
| `/api/scraping/jobs/{id}/history` | GET | Run history |

---

## LLM & Learning ✅ IMPLEMENTED

**File:** `backend/api/llm_endpoints.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/llm/providers` | GET | List providers |
| `/api/llm/providers/active` | GET | Get active provider |
| `/api/llm/providers/active` | POST | Set active provider |
| `/api/llm/feedback` | POST | Submit feedback |
| `/api/llm/learning/stats` | GET | Learning pipeline stats |
| `/api/llm/training/trigger` | POST | Trigger retraining |

---

## Data Layer ✅ IMPLEMENTED

**File:** `backend/api/data_layer_endpoints.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/data-layer/sources` | GET/POST | Data source CRUD |
| `/api/data-layer/jobs` | GET/POST | Ingestion jobs |
| `/api/data-layer/uploads` | POST | File uploads |
| `/api/data-layer/quality/issues` | GET | Quality issues |
| `/api/data-layer/dashboard` | GET | Dashboard data |

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": true,
  "message": "Description of what went wrong",
  "code": "ERROR_CODE",
  "details": {}
}
```

### Common Error Codes
- `400` — Bad request (invalid parameters)
- `404` — Resource not found
- `500` — Internal server error
- `503` — Service unavailable

---

## Rate Limits

- **Standard:** 100 requests/minute
- **Predictions:** 20 requests/minute
- **Chat:** 30 requests/minute

---

## Authentication ✅ IMPLEMENTED

**File:** `backend/api/auth_endpoints.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | User registration |
| `/api/auth/login` | POST | User login |
| `/api/auth/logout` | POST | User logout |
| `/api/auth/me` | GET | Current user info |
| `/api/auth/refresh` | POST | Refresh token |

For production, add API key header:
```
Authorization: Bearer <jwt_token>
```

---

## Multi-Agent Chat Example Flow

### 1. User Prompt
```json
{"message": "Compare Whitefield and Sarjapur for investment"}
```

### 2. Planner Creates Tasks
```json
{
  "tasks": [
    {"id": "t1", "type": "locality_analysis", "params": {"locality": "Whitefield"}},
    {"id": "t2", "type": "locality_analysis", "params": {"locality": "Sarjapur"}},
    {"id": "t3", "type": "comparison", "depends_on": ["t1", "t2"]}
  ]
}
```

### 3. Agent Outputs
```json
{
  "t1": {"growth_phase": "accelerating", "risk_score": 0.25, "price_sqft": 7800},
  "t2": {"growth_phase": "emerging", "risk_score": 0.35, "price_sqft": 6500},
  "t3": {"winner": "Sarjapur", "reason": "Higher growth potential, 15% lower entry price"}
}
```

### 4. Narrated Response
```json
{
  "response": "Based on my analysis, Sarjapur offers better investment potential. While Whitefield is more established with ₹7,800/sqft avg price, Sarjapur at ₹6,500/sqft is in an emerging growth phase with 18.5% YoY appreciation vs Whitefield's 14.2%. Sarjapur's higher risk (0.35 vs 0.25) is offset by its growth runway.",
  "confidence": 0.82,
  "map_action": {"type": "highlight_zones", "zones": ["Whitefield", "Sarjapur"]}
}
```
