# Dynamic Task System - Query-Specific Task Generation

This document demonstrates how the new dynamic task planning system generates **unique, realistic tasks** for each query type.

## System Overview

**Before (Old System):**
- ❌ Same generic tasks for all queries
- ❌ All tasks shown as "completed" immediately
- ❌ No real-time progress tracking

**After (New System):**
- ✅ Query-specific tasks generated dynamically
- ✅ Real-time progress tracking as agents execute
- ✅ Different task sequences for each intent type

---

## Example Task Sequences by Query Type

### 1. Navigation Query
**Query:** `"Go to Indiranagar"`

**Generated Tasks:**
1. Understanding query: 'Go to Indiranagar'
2. Geocoding location: Indiranagar
3. Preparing map navigation to Indiranagar
4. Loading nearby points of interest
5. Synthesizing AI narrative response

---

### 2. Area Analysis Query
**Query:** `"Analyze Koramangala for investment"`

**Generated Tasks:**
1. Understanding query: 'Analyze Koramangala for investment'
2. Analyzing area: Koramangala
3. Gathering spatial data (POIs, transport)
4. Calculating accessibility and walkability scores
5. Fetching market data and price trends
6. Analyzing terrain and flood risk
7. Generating locality intelligence profile
8. Computing risk assessment
9. Synthesizing comprehensive analysis
10. Synthesizing AI narrative response

---

### 3. Property Search Query
**Query:** `"Find 2BHK apartments in Whitefield under 80 lakhs"`

**Generated Tasks:**
1. Understanding query: 'Find 2BHK apartments in Whitefield under 80 lakhs'
2. Searching properties in Whitefield
3. Filtering by budget: ₹80L
4. Filtering by bedrooms: 2BHK
5. Retrieving property listings from database
6. Calculating distances and amenities
7. Ranking properties by relevance
8. Preparing property map markers
9. Synthesizing AI narrative response

---

### 4. Simulation Query (What-If)
**Query:** `"What if a metro station opens near Sarjapur Road?"`

**Generated Tasks:**
1. Understanding query: 'What if a metro station opens near Sarjapur Road?'
2. Understanding scenario: a metro station opens near sarjapur road?
3. Gathering baseline data for simulation
4. Running causal reasoning engine
5. Simulating infrastructure impact
6. Calculating price appreciation changes
7. Generating simulation storyboard
8. Preparing 3D visualization narrative
9. Synthesizing AI narrative response

---

### 5. Comparison Query
**Query:** `"Compare Whitefield vs Koramangala"`

**Generated Tasks:**
1. Understanding query: 'Compare Whitefield vs Koramangala'
2. Analyzing Whitefield
3. Analyzing Koramangala
4. Computing comparative metrics
5. Generating side-by-side comparison
6. Synthesizing AI narrative response

---

### 6. Building Analysis Query
**Query:** `"Analyze this building"` (with building selected)

**Generated Tasks:**
1. Understanding query: 'Analyze this building'
2. Analyzing selected building structure
3. Computing 3D spatial context
4. Analyzing view quality and sky view factor
5. Evaluating shadow impact
6. Finding optimal floor recommendation
7. Estimating building valuation
8. Synthesizing AI narrative response

---

### 7. Valuation Query
**Query:** `"What's the price of 2BHK in Indiranagar?"`

**Generated Tasks:**
1. Understanding query: 'What's the price of 2BHK in Indiranagar?'
2. Gathering property comparables
3. Analyzing market trends
4. Running valuation model
5. Computing price per sqft estimates
6. Synthesizing AI narrative response

---

### 8. Terrain Query
**Query:** `"Is Bellandur flood-prone?"`

**Generated Tasks:**
1. Understanding query: 'Is Bellandur flood-prone?'
2. Fetching elevation data
3. Analyzing slope and topography
4. Assessing flood risk
5. Evaluating construction suitability
6. Synthesizing AI narrative response

---

## Real-Time Progress Tracking

Tasks progress through these states:
- **pending** - Not started yet
- **in_progress** - Currently executing (shown with spinner)
- **completed** - Successfully completed (shown with ✓)
- **failed** - Error occurred (shown with ✗)
- **skipped** - Skipped due to unavailable data

### Visual Representation in UI:

```
📋 Tasks (5/8)

✓ Understanding query: 'Analyze Koramangala...'
✓ Analyzing area: Koramangala
✓ Gathering spatial data (POIs, transport)
✓ Calculating accessibility and walkability scores
✓ Fetching market data and price trends
⏳ Analyzing terrain and flood risk (in progress)
⏸ Generating locality intelligence profile
⏸ Computing risk assessment
```

---

## Technical Implementation

### Backend Components:

1. **`task_planner.py`** - Dynamic task generation engine
   - Generates query-specific task plans
   - Tracks task progress in real-time
   - Provides status snapshots for frontend

2. **`gis_agents.py`** - Agent orchestrator with task tracking
   - Calls `next_task()` after completing each agent operation
   - Updates task status as work progresses
   - Provides grounded facts for each task

3. **`server.py`** - API integration
   - Creates task planner for each query
   - Passes planner to orchestrator
   - Returns dynamic task snapshot in response

### Frontend Components:

**`ChatPanel.jsx`** - Already configured to display tasks
- `TaskListPanel` component renders task progress
- Real-time updates as tasks complete
- Visual indicators for each task state

---

## Key Benefits

1. **True Intelligence** - Each query gets a custom execution plan
2. **Transparency** - Users see exactly what the AI is doing
3. **Real-time Feedback** - Progress updates as agents work
4. **Educational** - Users learn how GIS analysis works
5. **Debugging** - Developers can see where issues occur

---

## Testing Recommendations

Test these diverse queries to verify dynamic task generation:

- **Navigation:** "Go to HSR Layout"
- **Analysis:** "Analyze Electronic City"
- **Search:** "Show me villas in Sarjapur under 2 crore"
- **Simulation:** "What if IT parks expand in Whitefield?"
- **Comparison:** "Compare HSR vs Marathahalli"
- **Building:** Click a building, then ask "Analyze this"
- **Valuation:** "Estimate price for 1500 sqft in Koramangala"
- **Terrain:** "What's the elevation in Hebbal?"

Each should show a **unique task sequence** tailored to that specific query type!
