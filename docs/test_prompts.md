# Valora AI - Test Prompts & Benchmarks

This document contains testable prompts to verify all Valora AI capabilities across phases.
Use these prompts to benchmark system performance, accuracy, and reliability.

---

## How to Use This Benchmark

1. **Manual Testing**: Use prompts in the chat interface
2. **API Testing**: Use curl/Postman with the provided API calls
3. **Scoring**: Rate each response 1-5 (1=fail, 5=perfect)
4. **Tracking**: Record scores in the results table at the end

---

## Phase 0 — Core Platform Tests

### 0.1 Geocoding & Navigation

| ID | Prompt | Expected Behavior | API Test |
|----|--------|-------------------|----------|
| P0-01 | "Show me Indiranagar" | Map flies to Indiranagar, place marker appears | `GET /api/geocode?q=Indiranagar` |
| P0-02 | "Navigate to Whitefield" | Map flies to Whitefield tech hub area | `GET /api/geocode?q=Whitefield` |
| P0-03 | "Go to Kempegowda Airport" | Map flies to Bangalore airport | `GET /api/geocode?q=Airport` |
| P0-04 | "Show me Tin Factory" | Map flies to Tin Factory junction | `GET /api/geocode?q=Tin+Factory` |
| P0-05 | "Take me to MG Road metro" | Map flies to MG Road metro station | `GET /api/geocode?q=MG+Road+metro` |
| P0-06 | "Find Phoenix Mall" | Map flies to Phoenix Marketcity | `GET /api/geocode?q=Phoenix+Mall` |

### 0.2 Geocoding Disambiguation

| ID | Prompt | Expected Behavior | Pass Criteria |
|----|--------|-------------------|---------------|
| P0-07 | "Show me Park" | Multiple options shown (disambiguation UI) | User sees 2+ options to choose |
| P0-08 | "Go to Hospital" | Multiple hospital options shown | Disambiguation with hospital names |
| P0-09 | "Navigate to School" | Multiple school options shown | Options include school names |

### 0.3 Map UX Controls

| ID | Action | Expected Behavior | Pass Criteria |
|----|--------|-------------------|---------------|
| P0-10 | Navigate then click "Back" | Returns to previous camera view | Camera returns to last position |
| P0-11 | Click "Reset View" | Returns to default Indiranagar view | Camera at default position |
| P0-12 | Navigate to location | Place marker with label appears | Blue marker + name visible |

### 0.4 Area Analysis

| ID | Prompt | Expected Behavior | API Test |
|----|--------|-------------------|----------|
| P0-13 | "Analyze Koramangala" | Dashboard shows POIs, transport, terrain | `GET /api/area/analyze?lat=12.9352&lng=77.6245` |
| P0-14 | "What's in Hebbal?" | Area analysis with nearby amenities | `GET /api/area/analyze?lat=13.0359&lng=77.5946` |
| P0-15 | Click on map location | Analysis panel updates with location data | Dashboard cards update |

### 0.5 Terrain Analysis

| ID | API Test | Expected Response | Pass Criteria |
|----|----------|-------------------|---------------|
| P0-16 | `GET /api/terrain/elevation?lat=12.97&lng=77.59` | Elevation in meters | Returns numeric elevation |
| P0-17 | `GET /api/terrain/analysis?lat=12.97&lng=77.59` | Slope, aspect, suitability | All fields present |
| P0-18 | `GET /api/terrain/stats` | Overall terrain statistics | Min/max/avg elevation |

---

## Phase 1 — Spatial Knowledge Layer Tests

### 1.1 Unified Spatial Query API

| ID | API Test | Expected Response | Pass Criteria |
|----|----------|-------------------|---------------|
| P1-01 | `GET /api/spatial/nearby?lat=12.9716&lng=77.5946&radius=1000` | List of nearby POIs, transport, places | Count > 0, results array |
| P1-02 | `GET /api/spatial/summary?lat=12.9716&lng=77.5946&radius=1000` | Accessibility/walkability scores | Scores 0-100 |
| P1-03 | `GET /api/spatial/contains?lat=12.9716&lng=77.5946` | Zone/city/state info | Returns zone name |
| P1-04 | `GET /api/spatial/analyze?lat=12.9716&lng=77.5946` | Complete location analysis | Terrain + spatial data |

### 1.2 Spatial Summary Verification

| ID | Prompt/API | Expected Data | Pass Criteria |
|----|------------|---------------|---------------|
| P1-05 | "What's near Indiranagar?" | POI counts, nearest amenities | Shows hospital, school, transport distances |
| P1-06 | `GET /api/spatial/summary?lat=12.9352&lng=77.6245` | Koramangala summary | accessibility_score present |
| P1-07 | `GET /api/spatial/summary?lat=13.0359&lng=77.5946` | Hebbal summary | walkability_score present |

### 1.3 Property Valuation API

| ID | API Test | Expected Response | Pass Criteria |
|----|----------|-------------------|---------------|
| P1-08 | `POST /api/valuation/estimate` with `{"lat":12.9716,"lng":77.5946,"bedrooms":2,"covered_area":1200}` | Price estimate with range | estimated_price > 0 |
| P1-09 | `POST /api/valuation/estimate` with `{"lat":12.8456,"lng":77.66,"bedrooms":3,"covered_area":1500,"property_type":"residential"}` | Electronic City valuation | Lower price than central areas |
| P1-10 | `POST /api/valuation/estimate` with `{"lat":12.9758,"lng":77.6066,"bedrooms":2,"covered_area":1000}` | MG Road valuation | Higher price (central location) |
| P1-11 | `GET /api/valuation/market-stats?lat=12.97&lng=77.59&radius=2` | Market statistics | avg_price, total_properties |

### 1.4 Valuation Prompt Tests

| ID | Prompt | Expected Behavior | Pass Criteria |
|----|--------|-------------------|---------------|
| P1-12 | "What's a 2BHK worth in Indiranagar?" | Price estimate with factors | Shows ₹ amount, factors |
| P1-13 | "Estimate price for 1500 sqft apartment in Whitefield" | Whitefield valuation | Price range shown |
| P1-14 | "Compare property prices in Koramangala vs Electronic City" | Comparative analysis | Shows price difference |

### 1.5 RAG Semantic Search

| ID | API Test | Expected Response | Pass Criteria |
|----|----------|-------------------|---------------|
| P1-15 | `GET /api/rag/search?q=apartments+near+metro&top_k=5` | Semantic search results | Results with scores |
| P1-16 | `GET /api/rag/search?q=commercial+office+space&top_k=10` | Office space listings | Commercial properties |
| P1-17 | `GET /api/rag/search?q=schools+hospitals+nearby&top_k=5` | POI results | Education/health POIs |
| P1-18 | `GET /api/rag/context?q=investment+potential+Hebbal` | LLM context string | Formatted context text |

### 1.6 RAG Integration Tests

| ID | Prompt | Expected Behavior | Pass Criteria |
|----|--------|-------------------|---------------|
| P1-19 | "Find luxury apartments with swimming pool" | Semantic search + results | Properties with amenities |
| P1-20 | "Show me properties near tech parks" | Location-aware search | Properties near IT hubs |
| P1-21 | "What restaurants are in Koramangala?" | POI semantic search | Restaurant POIs |

### 1.7 Phase 1 Status Check

| ID | API Test | Expected Response | Pass Criteria |
|----|----------|-------------------|---------------|
| P1-22 | `GET /api/phase1/status` | Service availability | All services: available=true |

---

## Phase 2 — Multi-Agent Orchestration Tests (Future)

### 2.1 Router Agent

| ID | Prompt | Expected Routing | Pass Criteria |
|----|--------|------------------|---------------|
| P2-01 | "Is this area good for apartments?" | Routes to: Spatial + Terrain + Market agents | Multi-step reasoning |
| P2-02 | "Compare Indiranagar and Whitefield" | Routes to: Geocoder + Analyst (x2) + Narrative | Comparative analysis |
| P2-03 | "What's the construction suitability here?" | Routes to: Terrain + Spatial agents | Terrain-focused response |

### 2.2 Agent Coordination

| ID | Prompt | Expected Agents | Pass Criteria |
|----|--------|-----------------|---------------|
| P2-04 | "Analyze investment potential of Sarjapur Road" | Geocoder → Spatial → Market → Narrative | Complete investment analysis |
| P2-05 | "Find best locations for a cafe" | Spatial → POI density → Narrative | Location recommendations |

---

## Phase 3 — 3D Reasoning Tests (Future)

### 3.1 Viewport Awareness

| ID | Prompt | Expected Behavior | Pass Criteria |
|----|--------|-------------------|---------------|
| P3-01 | "What am I looking at?" | Describes visible buildings/area | Accurate viewport description |
| P3-02 | "How many buildings are on screen?" | Count of visible buildings | Approximate count |
| P3-03 | "What's the tallest building here?" | Identifies tallest in viewport | Height information |

### 3.2 3D Scene Analysis

| ID | Prompt | Expected Behavior | Pass Criteria |
|----|--------|-------------------|---------------|
| P3-04 | "Describe the skyline" | Building height distribution | Skyline characteristics |
| P3-05 | "Is this area high-rise or low-rise?" | Building density assessment | Accurate classification |

---

## Phase 4 — Simulation Tests (Future)

### 4.1 What-If Scenarios

| ID | Prompt | Expected Behavior | Pass Criteria |
|----|--------|-------------------|---------------|
| P4-01 | "What if a metro station is added here?" | Impact analysis + visualization | Accessibility delta shown |
| P4-02 | "Simulate adding a hospital at this location" | Healthcare accessibility impact | Coverage improvement |
| P4-03 | "What if FAR is increased to 4.0?" | Development density impact | Building height simulation |

---

## API Endpoint Quick Reference

```bash
# Health Check
curl http://localhost:8000/health

# Phase 0 - Geocoding
curl "http://localhost:8000/api/geocode?q=Indiranagar"
curl "http://localhost:8000/api/geocode/local?q=metro+station"

# Phase 0 - Area Analysis
curl "http://localhost:8000/api/area/analyze?lat=12.97&lng=77.59"

# Phase 0 - Terrain
curl "http://localhost:8000/api/terrain/elevation?lat=12.97&lng=77.59"
curl "http://localhost:8000/api/terrain/analysis?lat=12.97&lng=77.59"

# Phase 1 - Spatial
curl "http://localhost:8000/api/spatial/nearby?lat=12.97&lng=77.59&radius=1000"
curl "http://localhost:8000/api/spatial/summary?lat=12.97&lng=77.59"
curl "http://localhost:8000/api/spatial/analyze?lat=12.97&lng=77.59"

# Phase 1 - Valuation
curl -X POST http://localhost:8000/api/valuation/estimate \
  -H "Content-Type: application/json" \
  -d '{"lat":12.97,"lng":77.59,"bedrooms":2,"covered_area":1200}'
curl "http://localhost:8000/api/valuation/market-stats?lat=12.97&lng=77.59"

# Phase 1 - RAG
curl "http://localhost:8000/api/rag/search?q=apartments&top_k=5"
curl "http://localhost:8000/api/rag/context?q=investment+analysis"
curl -X POST "http://localhost:8000/api/rag/index?force=false"

# Phase 1 - Status
curl http://localhost:8000/api/phase1/status

# Properties
curl "http://localhost:8000/api/properties/search?lat=12.97&lng=77.59&radius=2000"
curl "http://localhost:8000/api/properties/nearby?lat=12.97&lng=77.59"
curl "http://localhost:8000/api/properties/categories"
```

---

## PowerShell Test Commands

```powershell
# Health Check
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Phase 1 Status
Invoke-RestMethod -Uri "http://localhost:8000/api/phase1/status"

# Spatial Summary
Invoke-RestMethod -Uri "http://localhost:8000/api/spatial/summary?lat=12.9716&lng=77.5946&radius=1000" | ConvertTo-Json -Depth 5

# Valuation Estimate
$body = @{lat=12.9716; lng=77.5946; bedrooms=2; covered_area=1200; property_type="residential"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/valuation/estimate" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# RAG Search
Invoke-RestMethod -Uri "http://localhost:8000/api/rag/search?q=apartments+swimming+pool&top_k=5" | ConvertTo-Json -Depth 3
```

---

## Benchmark Results Template

### Test Run Information
- **Date**: ____________________
- **Tester**: ____________________
- **Backend Version**: 1.0.0
- **Frontend Version**: 1.0.0

### Phase 0 Scores

| Test ID | Score (1-5) | Notes |
|---------|-------------|-------|
| P0-01 | | |
| P0-02 | | |
| P0-03 | | |
| P0-04 | | |
| P0-05 | | |
| P0-06 | | |
| P0-07 | | |
| P0-08 | | |
| P0-09 | | |
| P0-10 | | |
| P0-11 | | |
| P0-12 | | |
| P0-13 | | |
| P0-14 | | |
| P0-15 | | |
| P0-16 | | |
| P0-17 | | |
| P0-18 | | |

**Phase 0 Average**: ___/5

### Phase 1 Scores

| Test ID | Score (1-5) | Notes |
|---------|-------------|-------|
| P1-01 | | |
| P1-02 | | |
| P1-03 | | |
| P1-04 | | |
| P1-05 | | |
| P1-06 | | |
| P1-07 | | |
| P1-08 | | |
| P1-09 | | |
| P1-10 | | |
| P1-11 | | |
| P1-12 | | |
| P1-13 | | |
| P1-14 | | |
| P1-15 | | |
| P1-16 | | |
| P1-17 | | |
| P1-18 | | |
| P1-19 | | |
| P1-20 | | |
| P1-21 | | |
| P1-22 | | |

**Phase 1 Average**: ___/5

### Overall Summary

| Phase | Tests | Passed (≥4) | Failed (<3) | Average |
|-------|-------|-------------|-------------|---------|
| Phase 0 | 18 | | | |
| Phase 1 | 22 | | | |
| **Total** | **40** | | | |

### Issues Found
1. 
2. 
3. 

### Recommendations
1. 
2. 
3. 

---

## Automated Test Script (Future)

```python
# tests/benchmark_valora.py
import requests
import json

BASE_URL = "http://localhost:8000"

def test_phase0_geocoding():
    """Test geocoding endpoints"""
    tests = [
        ("Indiranagar", True),
        ("Whitefield", True),
        ("Airport", True),
        ("NonExistentPlace12345", False)
    ]
    
    results = []
    for query, should_succeed in tests:
        resp = requests.get(f"{BASE_URL}/api/geocode?q={query}")
        data = resp.json()
        passed = (data.get("success") == should_succeed)
        results.append({"query": query, "passed": passed})
    
    return results

def test_phase1_spatial():
    """Test spatial endpoints"""
    resp = requests.get(f"{BASE_URL}/api/spatial/summary?lat=12.97&lng=77.59&radius=1000")
    data = resp.json()
    
    checks = {
        "has_success": data.get("success") == True,
        "has_accessibility_score": "accessibility_score" in data.get("data", {}),
        "has_walkability_score": "walkability_score" in data.get("data", {}),
        "has_total_features": data.get("data", {}).get("total_features", 0) > 0
    }
    
    return checks

def test_phase1_valuation():
    """Test valuation endpoint"""
    payload = {
        "lat": 12.97,
        "lng": 77.59,
        "bedrooms": 2,
        "covered_area": 1200,
        "property_type": "residential"
    }
    resp = requests.post(f"{BASE_URL}/api/valuation/estimate", json=payload)
    data = resp.json()
    
    checks = {
        "has_success": data.get("success") == True,
        "has_estimated_price": data.get("valuation", {}).get("estimated_price", 0) > 0,
        "has_price_range": "price_range" in data.get("valuation", {}),
        "has_factors": "factors" in data.get("valuation", {})
    }
    
    return checks

if __name__ == "__main__":
    print("Running Valora AI Benchmark...")
    
    print("\n=== Phase 0: Geocoding ===")
    for r in test_phase0_geocoding():
        status = "✅" if r["passed"] else "❌"
        print(f"{status} {r['query']}")
    
    print("\n=== Phase 1: Spatial ===")
    for check, passed in test_phase1_spatial().items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")
    
    print("\n=== Phase 1: Valuation ===")
    for check, passed in test_phase1_valuation().items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")
```

---

## Acceptance Criteria by Phase

### Phase 0 - PASS if:
- [ ] 90%+ geocoding queries return correct location
- [ ] Map navigation works for all 8 preset areas
- [ ] Disambiguation UI appears for ambiguous queries
- [ ] Back/Reset controls work correctly
- [ ] API response times < 200ms (geocode), < 1s (analyze)

### Phase 1 - PASS if:
- [ ] Spatial queries return data for any Bangalore location
- [ ] Accessibility/walkability scores computed (0-100)
- [ ] Valuation returns price estimates with confidence
- [ ] RAG search returns relevant results
- [ ] All Phase 1 services show available=true

### Phase 2 - PASS if (Future):
- [ ] Multi-step queries trigger correct agent chain
- [ ] Router correctly identifies query intent
- [ ] Agents produce grounded facts (not hallucinations)

### Phase 3 - PASS if (Future):
- [ ] Viewport-aware queries return visible building info
- [ ] 3D scene descriptions are accurate

### Phase 4 - PASS if (Future):
- [ ] What-if scenarios produce measurable deltas
- [ ] Simulation results include visualization data
