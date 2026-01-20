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

## 📝 Recording Results
For each phase, mark:
- **PASS**: Feature works as expected.
- **FAIL**: Error occurred or behavior is incorrect.
- **N/A**: Data/service not available in current environment.
