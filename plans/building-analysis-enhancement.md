# Building Analysis Enhancement Plan

## Interaction Model

### Left Click → Area/Locality Analysis
- **Purpose**: General area analysis based on selected location
- **Behavior**: Current existing functionality
- **Features**: POI counts, transport, accessibility, market overview

### Right Click → Building/Object Analysis
- **Purpose**: Detailed 3D reasoning analysis for specific building or object
- **Behavior**: Highlight building, show detailed analysis panel
- **Features**: Shadow analysis, view quality, 3D neighbors, investment metrics

### Micro Analysis → Pro Users Only
- **Purpose**: Very detailed and accurate analysis
- **Trigger**: Special button or API endpoint with user authentication
- **Features**: Floor-wise valuation, solar potential, structural analysis

---

## Implementation Plan

### Phase 1: Right-Click Building Selection

#### 1.1 Add Right-Click Handler
**File**: `src/spatial/OnlineOSMMap.jsx`

```javascript
// Right-click handler for building selection
viewer.screenSpaceEventHandler.setInputAction((click) => {
  // Check if clicked on a building entity
  const pickedObject = viewer.scene.pick(click.position)
  
  if (pickedObject && pickedObject.id && pickedObject.id.polygon) {
    // Right-clicked on a building
    const buildingData = selectBuilding(pickedObject.id)
    if (buildingData) {
      // Trigger detailed building analysis
      analyzeBuildingDetailed(buildingData)
    }
  }
}, Cesium.ScreenSpaceEventType.RIGHT_CLICK)
```

#### 1.2 Building Highlighting Function
```javascript
// Function to select and highlight a building
const selectBuilding = (entity) => {
  // Deselect previous building first
  deselectBuilding()
  
  if (!entity || !entity.polygon) return null
  
  // Store reference to selected entity
  selectedBuildingEntityRef.current = entity
  
  // Highlight with amber color
  entity.polygon.material = Cesium.Color.fromCssColorString('#fbbf24').withAlpha(0.9)
  entity.polygon.outline = true
  entity.polygon.outlineColor = Cesium.Color.fromCssColorString('#f59e0b')
  
  // Get building data from entity properties
  return {
    coordinates: {
      lat: entity.properties?.lat?.getValue(),
      lng: entity.properties?.lng?.getValue()
    },
    height: entity.properties?.height?.getValue(),
    levels: entity.properties?.levels?.getValue(),
    buildingType: entity.properties?.type?.getValue(),
    area: entity.properties?.area?.getValue(),
    name: entity.properties?.name?.getValue()
  }
}
```

---

### Phase 2: Detailed Building Analysis Endpoint

#### 2.1 New Endpoint: `/api/building/detailed`
**File**: `backend/server.py`

```python
class DetailedBuildingAnalysisRequest(BaseModel):
    lat: float
    lng: float
    height: Optional[float] = 10
    levels: Optional[int] = 3
    buildingType: Optional[str] = "building"
    area: Optional[float] = None
    name: Optional[str] = None

@app.post("/api/building/detailed")
async def analyze_building_detailed(request: DetailedBuildingAnalysisRequest):
    """
    Detailed 3D reasoning analysis for a specific building.
    Triggered by right-click on building.
    """
    result = {
        "success": True,
        "building": {...},
        "analysis_3d": {
            "shadow_analysis": {...},
            "view_quality": {...},
            "neighbors_3d": {...},
            "solar_potential": {...},
            "investment_score": {...}
        }
    }
    return result
```

#### 2.2 New Endpoint: `/api/building/micro` (Pro Users)
**File**: `backend/server.py`

```python
@app.post("/api/building/micro")
async def analyze_building_micro(
    request: DetailedBuildingAnalysisRequest,
    user: dict = Depends(get_current_pro_user)  # Requires pro subscription
):
    """
    Micro-level building analysis for pro users.
    Very detailed and accurate analysis.
    """
    result = {
        "success": True,
        "building": {...},
        "micro_analysis": {
            "floor_values": [...],  # Per-floor valuation
            "structural_analysis": {...},  # Construction quality
            "energy_efficiency": {...},  # Solar, insulation
            "regulatory_compliance": {...},  # Zoning, FAR
            "risk_assessment": {...}  # Flood, seismic, etc.
        }
    }
    return result
```

---

### Phase 3: Analysis Components

#### 3.1 Shadow Analysis
```python
def analyze_building_shadows(lat: float, lng: float, height: float) -> dict:
    """
    Calculate shadow impact for the building.
    Uses sun position based on current time simulation.
    """
    return {
        "shadow_length_m": 45.2,
        "shadow_direction": "NE",
        "affected_area_sqm": 1200,
        "shadow_hours_per_day": 4.5,
        "impact_on_neighbors": [...]
    }
```

#### 3.2 View Quality Analysis
```python
def analyze_building_views(lat: float, lng: float, height: float, levels: int) -> dict:
    """
    Analyze view quality for each floor using viewshed analysis.
    """
    return {
        "floor_views": [
            {"floor": 1, "quality": "limited", "score": 45},
            {"floor": 5, "quality": "good", "score": 72},
            {"floor": 10, "quality": "excellent", "score": 88}
        ],
        "best_floor": 10,
        "sky_view_factor": 0.65,
        "visible_landmarks": ["Park", "Lake", "Metro"]
    }
```

#### 3.3 3D Neighbor Analysis
```python
def analyze_3d_neighbors(lat: float, lng: float, height: float) -> dict:
    """
    Analyze 3D spatial relationships with nearby buildings.
    """
    return {
        "buildings_above": [...],  # Taller buildings
        "buildings_below": [...],  # Shorter buildings
        "buildings_at_level": [...],  # Similar height
        "privacy_score": 72,
        "light_access_score": 85
    }
```

---

### Phase 4: Frontend UI

#### 4.1 Building Analysis Panel
**File**: `src/components/AnalysisPanel.jsx`

Add new tab for "Building Analysis" when a building is selected:
- Building info card (height, levels, type)
- Shadow analysis visualization
- View quality chart per floor
- 3D neighbor diagram
- Investment score gauge

#### 4.2 Context Menu
**File**: `src/spatial/OnlineOSMMap.jsx`

Show context menu on right-click:
```
┌─────────────────────────────┐
│ 🏢 Building Analysis        │
│ 📊 View Quality             │
│ 🌑 Shadow Impact            │
│ 💰 Investment Score         │
│ ─────────────────────────── │
│ ⭐ Pro: Micro Analysis      │
└─────────────────────────────┘
```

---

## File Changes Summary

| File | Changes |
|------|---------|
| `src/spatial/OnlineOSMMap.jsx` | Add right-click handler, `selectBuilding()` |
| `backend/server.py` | Add `/api/building/detailed` and `/api/building/micro` |
| `backend/analyzers/building_analyzer.py` | Add shadow, view, neighbor analysis |
| `src/components/AnalysisPanel.jsx` | Add building analysis tab |
| `src/components/ContextMenu.jsx` | New component for right-click menu |

---

## Implementation Order

1. **Right-Click Handler** (Frontend)
   - Add `RIGHT_CLICK` event handler
   - Implement `selectBuilding()` highlighting
   - Test building selection works

2. **Detailed Analysis Endpoint** (Backend)
   - Create `/api/building/detailed` endpoint
   - Implement shadow, view, neighbor analysis
   - Test with sample coordinates

3. **Micro Analysis Endpoint** (Backend)
   - Create `/api/building/micro` endpoint with pro user check
   - Implement floor-wise valuation
   - Add regulatory and risk analysis

4. **Frontend Integration** (Frontend)
   - Update AnalysisPanel for building analysis
   - Add context menu component
   - Connect to backend endpoints

5. **Polish & Testing**
   - Add loading states
   - Error handling
   - Pro user upgrade prompts
