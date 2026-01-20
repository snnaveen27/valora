# Terrain Data - Digital Elevation Model (DEM)

This directory contains processed terrain data extracted from `dem_bengaluru.tif`.

## Contents

### Elevation Index
- **`elevation_index.json`** - Tile index with 504 elevation tiles
  - Each tile covers 0.05° × 0.05° area
  - Contains elevation statistics (min/max/mean)
  - Contains slope statistics (min/max/mean)
  - Enables fast spatial queries

### Derived Products
- **`slope.tif`** - Slope in degrees (0-90°)
- **`aspect.tif`** - Aspect/orientation in degrees (0-360°, 0=North)
- **`hillshade.tif`** - Hillshade visualization for terrain rendering

## Coverage

**Spatial Extent:**
- West: 77.15°E
- East: 78.30°E
- South: 12.50°N
- North: 13.55°N

**Elevation Range:**
- Minimum: 474.3m
- Maximum: 1477.2m
- Mean: 829.2m

## API Endpoints

### Get Elevation
```bash
GET /api/terrain/elevation?lat=12.9716&lng=77.5946
```

Returns:
```json
{
  "success": true,
  "data": {
    "lat": 12.9716,
    "lng": 77.5946,
    "elevation": 904.9,
    "elevation_range": { "min": 848.9, "max": 951.9 },
    "slope": 4.3,
    "slope_range": { "min": 0.0, "max": 25.2 },
    "tile_id": 224
  }
}
```

### Get Terrain Analysis
```bash
GET /api/terrain/analysis?lat=12.9716&lng=77.5946&radius=0.02
```

Returns:
```json
{
  "success": true,
  "data": {
    "location": { "lat": 12.9716, "lng": 77.5946 },
    "radius_deg": 0.02,
    "tiles_analyzed": 1,
    "elevation": {
      "min": 848.9, "max": 951.9, "mean": 904.9,
      "std": 0.0, "range": 103.0
    },
    "slope": {
      "min": 0.0, "max": 25.2, "mean": 4.3, "std": 0.0
    },
    "terrain_classification": "gentle",
    "construction_suitability": {
      "score": 87.1,
      "rating": "excellent",
      "notes": "Flat, stable terrain ideal for construction",
      "factors": {
        "slope_score": 78.4,
        "flatness_score": 100.0
      }
    }
  }
}
```

### Get Terrain Stats
```bash
GET /api/terrain/stats
```

## Terrain Classification

| Avg Slope | Classification |
|-----------|----------------|
| < 2°      | Flat           |
| 2-5°      | Gentle         |
| 5-10°     | Moderate       |
| 10-15°    | Steep          |
| > 15°     | Very Steep     |

## Construction Suitability Scoring

**Score Components:**
- **Slope Score** (60% weight): Lower slopes = higher score
- **Flatness Score** (40% weight): Lower elevation variance = higher score

**Ratings:**
- **Excellent** (80-100): Flat, stable terrain ideal for construction
- **Good** (60-80): Generally suitable with minor grading needed
- **Moderate** (40-60): Requires significant site preparation
- **Challenging** (20-40): Steep terrain, extensive foundation work
- **Difficult** (0-20): Very challenging, high construction costs

## Usage in Valora AI

The terrain service is automatically integrated into:
1. **Area Analysis** - Provides elevation context for locations
2. **Construction Assessment** - Evaluates site suitability
3. **AI Chat** - Can answer terrain-related queries
4. **Dashboard** - Shows terrain metrics for selected areas

## Data Source

- **Original DEM**: `dem_bengaluru.tif` (60.8 MB)
- **Resolution**: ~30m (0.00028° per pixel)
- **Format**: GeoTIFF, EPSG:4326 (WGS84)
- **Processing**: Python with rasterio, numpy

## Regeneration

To regenerate terrain data from a new DEM:

```bash
python scripts/extract_dem_data.py
```

This will:
1. Load the DEM file
2. Calculate slope and aspect
3. Generate hillshade
4. Create 504 elevation tiles
5. Save derived products and index
