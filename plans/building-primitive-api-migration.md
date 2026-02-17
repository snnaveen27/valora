# Building Primitive API Migration Plan

## Overview

Migrate building rendering from Cesium Entity API to Primitive API for 10x performance improvement while preserving all 3D spatial analysis functionality.

## Current Implementation Issues

### Entity API Problems
- **High Memory**: Each building is a full JavaScript object with property tracking
- **Slow Rendering**: Entity properties evaluated every frame
- **Too Many Draw Calls**: 3000 entities = 3000+ separate draw calls
- **RAM Usage**: ~500MB for 3000 buildings

### Target Performance
- **Memory**: ~50MB for 3000 buildings (10x reduction)
- **Render Time**: ~5ms/frame (10x faster)
- **Draw Calls**: 1-10 total (batched)

---

## Architecture Changes

### 1. Data Structures

#### Current (Entity API)
```javascript
// Each building is a separate entity
viewer.entities.add({
  polygon: { hierarchy, material, extrudedHeight, ... },
  properties: { height, levels, type, name, address, lat, lng, area }
})
```

#### New (Primitive API)
```javascript
// Buildings stored in data structures separate from rendering
const buildingDataStore = useRef({
  // Map: buildingId -> building metadata
  metadata: new Map(),
  // Map: primitive index -> buildingId
  indexToId: new Map(),
  // Current primitive collection
  primitives: null
})

// Single primitive for ALL buildings
const primitive = new Cesium.Primitive({
  geometryInstances: [/* all building geometries */],
  appearance: new Cesium.PerInstanceColorAppearance()
})
```

### 2. Building ID System

Each building needs a unique ID for picking and analysis:

```javascript
// Generate unique ID from coordinates
const buildingId = `${lng.toFixed(6)}_${lat.toFixed(6)}_${height}`

// Store metadata separately
buildingDataStore.current.metadata.set(buildingId, {
  height, levels, type, name, address, lat, lng, area,
  coordinates: { lat, lng }
})
```

### 3. Picking System

Custom picking to detect which building was clicked:

```javascript
// On mouse click
const handler = new Cesium.ScreenSpaceEventHandler(viewer.canvas)
handler.setInputAction((movement) => {
  // Pick the primitive
  const pickedFeature = viewer.scene.pick(movement.position)
  
  if (pickedFeature && pickedFeature.primitive === buildingPrimitiveRef.current) {
    // Get the instance ID
    const instanceId = pickedFeature.id
    // Look up building metadata
    const buildingId = buildingDataStore.current.indexToId.get(instanceId)
    const buildingData = buildingDataStore.current.metadata.get(buildingId)
    
    // Trigger building click event
    window.dispatchEvent(new CustomEvent('valora-building-clicked', {
      detail: { building: buildingData }
    }))
  }
}, Cesium.ScreenSpaceEventType.LEFT_CLICK)
```

### 4. Building Selection Highlighting

Use a separate primitive for selected building highlight:

```javascript
// Selection primitive (single geometry, different color)
const selectionPrimitiveRef = useRef(null)

function highlightBuilding(buildingId) {
  const building = buildingDataStore.current.metadata.get(buildingId)
  // Create new primitive with highlight color
  // Remove old selection primitive
  // Add new selection primitive
}
```

---

## Implementation Steps

### Step 1: Create Building Data Store

```javascript
// New refs for Primitive API
const buildingPrimitiveRef = useRef(null)
const buildingDataStore = useRef({
  metadata: new Map(),
  indexToId: new Map(),
  nextInstanceId: 0
})
```

### Step 2: Create Geometry Instances

Replace entity creation with geometry instances:

```javascript
function createBuildingGeometry(building) {
  const { centroidLng, centroidLat, polygonHierarchy, height } = building
  
  return new Cesium.GeometryInstance({
    id: buildingId, // Unique ID for picking
    geometry: new Cesium.PolygonGeometry({
      polygonHierarchy: polygonHierarchy,
      extrudedHeight: height,
      vertexFormat: Cesium.PerInstanceColorAppearance.VERTEX_FORMAT
    }),
    attributes: {
      color: Cesium.ColorGeometryInstanceAttribute.fromColor(
        Cesium.Color.fromCssColorString(color).withAlpha(alpha)
      )
    }
  })
}
```

### Step 3: Batch Create Primitive

```javascript
async function loadBuildingsAsPrimitive(tiles) {
  const geometryInstances = []
  
  for (const tile of tiles) {
    const buildings = await fetchTileData(tile)
    for (const building of buildings) {
      const instance = createBuildingGeometry(building)
      geometryInstances.push(instance)
      
      // Store metadata
      buildingDataStore.current.metadata.set(building.id, building.metadata)
    }
  }
  
  // Create single primitive
  const primitive = new Cesium.Primitive({
    geometryInstances: geometryInstances,
    appearance: new Cesium.PerInstanceColorAppearance({
      flat: true,
      translucent: true
    }),
    asynchronous: true
  })
  
  viewer.scene.primitives.add(primitive)
  buildingPrimitiveRef.current = primitive
}
```

### Step 4: Implement Custom Picking

```javascript
// Replace entity click handler with primitive picking
function setupPrimitivePicking() {
  const handler = new Cesium.ScreenSpaceEventHandler(viewer.canvas)
  
  handler.setInputAction((movement) => {
    const pickedFeature = viewer.scene.pick(movement.position)
    
    if (pickedFeature?.primitive === buildingPrimitiveRef.current) {
      const buildingId = pickedFeature.id
      const buildingData = buildingDataStore.current.metadata.get(buildingId)
      
      // Same event as before - no changes to analysis flow
      window.dispatchEvent(new CustomEvent('valora-building-clicked', {
        detail: { building: buildingData }
      }))
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
}
```

### Step 5: Preserve Analysis Flow

The `valora-building-clicked` event remains unchanged, so all existing analysis code works:

```javascript
// In EnhancedChatPanel.jsx - NO CHANGES NEEDED
const handleBuildingClick = async (e) => {
  const { building } = e.detail || {}
  // ... existing analysis code works exactly the same
}
```

---

## Files to Modify

### Primary Changes: `src/spatial/OnlineOSMMap.jsx`

1. **Add new refs** for Primitive API
2. **Replace `loadTile` function** to create geometry instances instead of entities
3. **Replace `clearAllBuildings`** to remove primitives instead of entities
4. **Add custom picking handler** for building selection
5. **Add selection highlighting** using separate primitive

### No Changes Needed

- `src/components/chat/EnhancedChatPanel.jsx` - Uses `valora-building-clicked` event
- `src/components/AnalysisPanel.jsx` - Uses `agentData.selectedBuilding`
- Backend APIs - No changes

---

## Performance Expectations

| Metric | Entity API | Primitive API |
|--------|-----------|---------------|
| RAM for 3000 buildings | ~500MB | ~50MB |
| Frame render time | ~50ms | ~5ms |
| Draw calls | 3000+ | 1-10 |
| Initial load time | ~3s | ~1s |

---

## Risk Mitigation

### Risk: Picking doesn't work correctly
**Mitigation**: Test picking immediately after primitive creation. Use `primitive.readyPromise` to ensure primitive is ready before enabling picking.

### Risk: Building selection highlighting is slow
**Mitigation**: Use a separate single-geometry primitive for selection highlight, not per-instance color changes.

### Risk: Memory leak with primitives
**Mitigation**: Properly call `viewer.scene.primitives.remove()` and `primitive.destroy()` when clearing buildings.

---

## Testing Checklist

- [ ] Buildings render correctly at correct locations
- [ ] Building click detection works
- [ ] Building metadata (height, type, etc.) is preserved
- [ ] Building analysis triggers correctly
- [ ] Selection highlighting works
- [ ] Clear buildings works without memory leak
- [ ] Performance is improved (check RAM and frame time)
- [ ] No console errors

---

## Implementation Order

1. Add new data structures and refs
2. Create `createBuildingGeometry` function
3. Modify `loadTile` to use geometry instances
4. Create `loadBuildingsAsPrimitive` function
5. Implement custom picking handler
6. Implement selection highlighting
7. Update `clearAllBuildings` function
8. Test all functionality
