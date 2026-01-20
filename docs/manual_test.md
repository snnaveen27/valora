# Valora AI - Manual Testing Guide

This document provides comprehensive manual testing scenarios for all features implemented up to Phase 5. Use this to verify system behavior, accuracy, and UX.

## 📋 Pre-Test Checklist
- [ ] Backend is running: `http://localhost:8000`
- [ ] Frontend is running: `http://localhost:3001` (or 3000)
- [ ] OpenRouter API Key is configured in `.env`
- [ ] Pinecone index is connected and populated
- [ ] Local tiles directory exists: `src/data/map_tiles` (for offline testing)

---

## Phase 0: Core Platform (Navigation & Data)

### 0.1 Map Navigation & View
- **Test Case**: Initial load view.
- **Steps**:
  1. Open the app in browser.
  2. Verify map centers on Bangalore (Indiranagar area by default).
  3. Verify 3D buildings load correctly.
- **Expected Result**: 3D building models appear with correct heights and gray coloring.

### 0.2 Geocoding & FlyTo
- **Test Case**: Natural language navigation.
- **Steps**:
  1. Type "Show me Hebbal" in chat.
  2. Click Send.
- **Expected Result**: Map smoothly flies to Hebbal. A blue marker appears at the location.

### 0.3 Building Selection
- **Test Case**: Click-to-analyze building.
- **Steps**:
  1. Click on any 3D building model.
- **Expected Result**: Building highlights in blue. Analysis panel (right) opens and shows building details (height, levels, name if available).

---

## Phase 1: Spatial Intelligence (RAG & ML)

### 1.1 Spatial RAG Search
- **Test Case**: Semantic query for POIs.
- **Steps**:
  1. Type "Find some good cafes in Indiranagar" in chat.
- **Expected Result**: AI returns specific names of cafes from the OSM knowledge base. Dashboard shows "Nearest POIs" with cafe names.

### 1.2 ML Property Valuation
- **Test Case**: Real-time price estimation.
- **Steps**:
  1. Navigate to a residential area (e.g., Koramangala).
  2. Click a building.
  3. Look for "Valuation Estimate" in the analysis panel.
- **Expected Result**: A ₹ value is displayed based on location and proximity to metro/amenities.

---

## Phase 2: Multi-Agent Orchestration

### 2.1 Intent Detection
- **Test Case**: Switching between different task types.
- **Steps**:
  1. Query 1: "Take me to MG Road" (NAVIGATE)
  2. Query 2: "What is the terrain like here?" (TERRAIN)
  3. Query 3: "Are there 3BHK apartments nearby?" (PROPERTY_SEARCH)
- **Expected Result**: AI correctly identifies each intent and calls the relevant specialized agent.

### 2.2 Fact Grounding
- **Test Case**: Verifying "No Hallucination".
- **Steps**:
  1. Ask "How many bus stops are within 500m of this building?"
- **Expected Result**: AI gives a specific number (e.g., "7 bus stops") that matches the spatial summary facts.

---

## Phase 3: True 3D Reasoning

### 3.1 AI-Driven Overlays
- **Test Case**: Visual annotations.
- **Steps**:
  1. Ask "Analyze the accessibility of this area."
- **Expected Result**: Map shows 3D circles (radius zones) or arrows pointing to transport hubs.

### 3.2 Viewport Awareness
- **Test Case**: "What am I looking at?"
- **Steps**:
  1. Zoom out to see a large area.
  2. Ask "What is in my current view?"
- **Expected Result**: AI summarizes building height distribution and major landmarks currently visible on screen.

---

## Phase 4: Simulation & Digital Twin

### 4.1 What-If Simulation
- **Test Case**: Adding infrastructure.
- **Steps**:
  1. Type "What if we add a metro station here?"
- **Expected Result**: Analysis panel shows "Impact Deltas" (e.g., Accessibility +40%, Property Value +25%).

### 4.2 Cinematic Storyboard
- **Test Case**: Immersive walkthrough.
- **Steps**:
  1. Trigger a simulation (as above).
  2. Click "Play Storyboard" (if button visible) or wait for auto-play.
- **Expected Result**: Camera moves automatically through a sequence of views. Voice narration plays. 3D overlays explain each step.

### 4.3 Digital Twin State
- **Test Case**: Real-time state tracking.
- **Steps**:
  1. Open browser console or use API tool.
  2. Call `GET /api/digital-twin/state`.
- **Expected Result**: Returns JSON with current city state (infrastructure, economy, environment counts).

---

## Phase 5: Production Readiness

### 5.1 Credit System (Usage Tracking)
- **Test Case**: Deducting credits.
- **Steps**:
  1. Check credits: `GET /api/credits/user123`. (Default 100)
  2. Perform a "Simulation" query.
  3. Check credits again.
- **Expected Result**: Balance should be 95 (100 - 5 for simulation).

### 5.2 Online/Offline Toggle
- **Test Case**: Switching tile sources.
- **Steps**:
  1. Locate the Network icon button in the map controls (top right).
  2. Click to toggle to Offline (Orange icon).
  3. Zoom into an area not previously cached.
- **Expected Result**: Map should show gray placeholder tiles (if local tiles not found) or local tiles (if provided). No requests to `tile.openstreetmap.org` should occur in offline mode.

---

## 🔒 Security & Vulnerability Check

### S1: CORS Validation
- **Steps**: Try to access the API from a different port (e.g., 3005) or domain.
- **Expected Result**: Request should be blocked by CORS policy.

### S2: Input Sanitization
- **Steps**: Send a query with script tags: `<script>alert('xss')</script>`.
- **Expected Result**: React escapes the text; alert does not fire. Backend handles it as a string.

### S3: Radius Enforcement
- **Steps**: Call `/api/spatial/nearby` with `radius_m=500000` (500km).
- **Expected Result**: Backend should limit it to a reasonable maximum (e.g., 10km) or return 400 error.

---

## 🏗️ Deep Bangalore Scenarios (Stress Test)

1. **The Tech Hub Test**: "Compare Outer Ring Road near Bellandur with Whitefield for office space."
2. **The Heritage Test**: "Show me landmarks in Malleshwaram and analyze walkability."
3. **The Transit Test**: "How does the upcoming Pink Line impact property values in Jayanagar?"
4. **The Flood Risk Test**: "Identify low-lying areas near Bellandur Lake and show terrain slope."

---

## 🧠 Advanced Spatial Awareness Tests

### A1. Property Search with Location Context
| Query | Expected Intent | Expected Behavior |
|-------|-----------------|-------------------|
| "Show me top properties in Hebbal" | PROPERTY_SEARCH | Returns properties near Hebbal with prices, geocodes location |
| "Top properties in Manyata Tech Park" | PROPERTY_SEARCH | Returns properties near Manyata, shows on map |
| "3BHK apartments under 1 crore in Whitefield" | PROPERTY_SEARCH | Filters by BHK and price, shows filtered results |
| "Commercial properties for rent in Koramangala" | PROPERTY_SEARCH | Returns commercial listings |
| "Best investment areas in Bangalore" | PROPERTY_SEARCH | Returns top areas with growth potential |

### A2. Multi-Agent Coordination Tests
| Query | Agents Involved | Expected Response |
|-------|-----------------|-------------------|
| "What is the flood risk and property value in this area?" | Terrain + Valuation | Combined terrain analysis + market data |
| "Compare accessibility of Indiranagar vs Koramangala" | Spatial + Comparison | Side-by-side accessibility scores |
| "Analyze this building and nearby amenities" | Building + Spatial | Building details + POI list |
| "What would happen if a metro station is built near this building?" | Simulation + Spatial | Impact deltas + current spatial context |

### A3. Viewport-Aware Queries
| Query | Expected Behavior |
|-------|-------------------|
| "What properties are in my current view?" | Uses mapCenter to find visible properties |
| "Summarize the buildings I'm looking at" | Analyzes buildings in current viewport |
| "What is the average height of buildings here?" | Calculates from visible building data |
| "Show me the tallest building in view" | Highlights tallest building in viewport |

---

## 💰 Valuation & Market Analysis Tests

### V1. Property Valuation Queries
| Query | Expected Response |
|-------|-------------------|
| "What is the price per sqft in Indiranagar?" | Returns avg price from property data |
| "How much is this building worth?" | Estimates value based on area, height, location |
| "Price trend in Koramangala over last year" | Returns price_trend_pct data |
| "Demand level in Whitefield" | Returns High/Medium/Low demand index |

### V2. Market Comparison Tests
| Query | Expected Data Points |
|-------|---------------------|
| "Compare prices: Hebbal vs Electronic City" | Two price comparisons with % difference |
| "Which area has better appreciation: HSR or BTM?" | Growth rates for both areas |
| "Most affordable areas for 2BHK in Bangalore" | Sorted list by price |

---

## 🏙️ Digital Twin & Simulation Tests

### D1. Infrastructure Impact Simulations
| Scenario | Expected Deltas |
|----------|-----------------|
| "Add a metro station at current location" | Accessibility +30-40%, Property Value +20-25% |
| "Build a highway near this area" | Accessibility +30%, Walkability -25% |
| "Increase FAR by 2x in this zone" | Development pressure +70%, Traffic +30% |
| "Add a tech park near Hebbal" | Amenity density +25%, Property value +15% |

### D2. Storyboard Playback Tests
- **Test**: Trigger simulation and verify camera animation
- **Expected**: 3-5 keyframe transitions with voiceover events
- **Verify**: `valora-narration` events dispatched to window

### D3. Digital Twin State API
```bash
# Test commands
curl http://localhost:8000/api/digital-twin/state
curl http://localhost:8000/api/digital-twin/sync
```
Expected: JSON with infrastructure, economy, environment counts

---

## 🎯 Intent Classification Accuracy Tests

### I1. Edge Case Queries
| Query | Correct Intent | Common Misclassification |
|-------|---------------|-------------------------|
| "Show me properties in Hebbal" | PROPERTY_SEARCH | ~~NAVIGATE~~ |
| "Top apartments near Manyata" | PROPERTY_SEARCH | ~~NAVIGATE~~ |
| "Go to Koramangala and show apartments" | PROPERTY_SEARCH | ~~NAVIGATE~~ |
| "Navigate to Whitefield" | NAVIGATE | — |
| "What if metro comes to this area?" | SIMULATE | ~~GENERAL~~ |
| "Is this area safe from floods?" | TERRAIN | ~~GENERAL~~ |

### I2. Compound Queries
| Query | Expected Handling |
|-------|-------------------|
| "Show me Hebbal and list top properties there" | Geocode Hebbal → Property search |
| "Analyze terrain and suggest best building spots" | Terrain analysis → Recommendations |
| "Compare prices and accessibility of 3 areas" | Multi-comparison with both metrics |

---

## � Layer Toggle Tests

### L1. Buildings Layer
- **Test**: Toggle "3D Buildings" off and on
- **Expected**: All building polygons hide/show without page reload
- **Verify**: `tileEntitiesRef` entities have `show` property toggled

### L2. Base Map Toggle
- **Test**: Switch between OSM and Mapbox
- **Expected**: Imagery changes, camera position preserved
- **Verify**: No camera jump, smooth transition

### L3. Transport Layer (Pending)
- **Status**: UI toggle exists, layer not yet implemented
- **Future**: Should show bus stops, metro stations as markers

---

## 📊 Grounded Facts Verification

### G1. No Hallucination Test
For each AI response, verify:
- [ ] All numbers match `AgentFacts` data
- [ ] No invented property names
- [ ] Price ranges match property JSON data
- [ ] POI names exist in OSM data
- [ ] Transport counts match spatial analysis

### G2. Dashboard Consistency
- **Test**: Query property info, check Analysis Panel
- **Expected**: Dashboard cards match AI narrative exactly
- **Fields to verify**: POI count, Transport count, Accessibility score, Avg price

---

## �📝 Recording Results
For each phase, mark:
- **PASS**: Feature works as expected.
- **FAIL**: Error occurred or behavior is incorrect.
- **N/A**: Data/service not available in current environment.

---

## 🚀 Quick Regression Test Suite

Run these 10 queries in sequence to verify core functionality:

1. `"Show me Indiranagar"` → NAVIGATE, map flies to location
2. `"Top properties in Hebbal"` → PROPERTY_SEARCH, returns listings
3. `"What is the terrain like here?"` → TERRAIN, returns elevation/flood risk
4. `"3BHK apartments under 80 lakhs"` → PROPERTY_SEARCH with filters
5. `"Compare Whitefield and Koramangala"` → COMPARISON with metrics
6. `"What if a metro station is built here?"` → SIMULATE with deltas
7. `"Analyze this area"` → ANALYZE_AREA with spatial facts
8. `"Find cafes nearby"` → RAG search with POI results
9. `"What is in my current view?"` → Viewport analysis
10. `"Hello, what can you do?"` → GENERAL, capability overview
