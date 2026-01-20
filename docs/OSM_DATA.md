# OSM Extracted Data - Bengaluru

This folder contains comprehensive OpenStreetMap data extracted from `bengaluru.osm.pbf`.

It has two layers:

- **raw/**: full dump of *everything* in the PBF (nodes/ways/relations + all tags) in streaming **JSONL** format
- **derived/**: convenient GIS layers (roads/pois/landuse/etc.) in **GeoJSON** format

## 📁 Folder Structure

```
osm_extracted/
├── index.json
├── raw/
│   ├── nodes.jsonl
│   ├── ways.jsonl
│   └── relations.jsonl
└── derived/
    ├── roads.geojson
    ├── places.geojson
    ├── pois.geojson
    ├── landuse.geojson
    ├── natural.geojson
    ├── transport.geojson
    ├── boundaries.geojson
    └── buildings_metadata.geojson
```

## Raw (FULL PBF dump)

The `raw/` folder is the authoritative offline dataset.

- `raw/nodes.jsonl`: one JSON object per line
- `raw/ways.jsonl`: one JSON object per line
- `raw/relations.jsonl`: one JSON object per line

Each record stores:

- `id`
- `tags` (all tags)
- geometry/refs (`lon/lat` for nodes, `nodes/coords` for ways, `members` for relations)

This format is intentionally **streaming** (JSONL) so it can be processed without loading everything into RAM.

## 📊 Data Categories

## Derived GIS layers

### 1. **derived/roads.geojson**
All road networks with detailed attributes:
- **Types**: motorway, trunk, primary, secondary, tertiary, residential, service
- **Attributes**: name, lanes, maxspeed, surface, geometry
- **Use cases**: Navigation, routing, 3D labels

### 2. **derived/places.geojson**
Place names and settlements:
- **Types**: city, town, suburb, neighbourhood, locality
- **Attributes**: name, population, admin level
- **Use cases**: Map labels, location search, context

### 3. **derived/pois.geojson**
Points of interest:
- **Amenities**: restaurants, hospitals, schools, banks, ATMs
- **Shops**: supermarkets, malls, retail stores
- **Tourism**: attractions, hotels, viewpoints
- **Use cases**: Search, recommendations, analysis

### 4. **derived/landuse.geojson**
Land use and leisure areas:
- **Types**: residential, commercial, industrial, retail
- **Leisure**: parks, playgrounds, sports centers
- **Use cases**: Urban planning, zoning analysis

### 5. **derived/natural.geojson**
Natural features:
- **Types**: water bodies, forests, grassland, wetlands
- **Use cases**: Environmental analysis, green space mapping

### 6. **derived/transport.geojson**
Public transportation:
- **Stops**: bus stops, metro stations, railway stations
- **Routes**: bus routes, metro lines
- **Use cases**: Transit planning, accessibility analysis

### 7. **derived/boundaries.geojson**
Administrative boundaries:
- **Types**: city, ward, district boundaries
- **Attributes**: admin level, name
- **Use cases**: Jurisdiction mapping, statistical analysis

### 8. **derived/buildings_metadata.geojson**
Buildings with additional metadata:
- **Attributes**: name, type, height, levels
- **Use cases**: Building search, landmark identification

## 🔍 Index File (index.json)

The `index.json` file contains:
```json
{
  "generated": "timestamp",
  "source": "path/to/bengaluru.osm.pbf",
  "raw_counts": {
    "nodes": 0,
    "ways": 0,
    "relations": 0
  },
  "derived_counts": {
    "roads": 0,
    "places": 0
  },
  "raw_files": ["raw/nodes.jsonl", "raw/ways.jsonl", "raw/relations.jsonl"],
  "derived_files": ["derived/roads.geojson", "derived/places.geojson"]
}
```

## 🚀 Usage Examples

### Backend API Integration
```python
# Load roads for viewport
with open('osm_extracted/derived/roads.geojson') as f:
    roads = json.load(f)
    
# Filter by bbox
viewport_roads = [
    feature for feature in roads['features']
    if is_in_bbox(feature['geometry'], bbox)
]
```

### Frontend 3D Labels
```javascript
// Load place names for 3D rendering
const places = await fetch('/data/osm_extracted/derived/places.geojson')
const data = await places.json()

data.features.forEach(feature => {
  const [lng, lat] = feature.geometry.coordinates
  add3DLabel(feature.properties.name, lng, lat)
})
```

### AI Context
```javascript
// Provide POI context to Valora AI
const pois = await fetch('/data/osm_extracted/derived/pois.geojson')
const nearbyPOIs = filterByDistance(pois, userLocation, 500) // 500m radius

// Send to AI for context-aware responses
```

## 🔄 Regeneration

To regenerate the data (e.g., after updating the PBF):

```bash
cd scripts
python extract_all_osm_data.py
```

This will:
1. Parse the latest `bengaluru.osm.pbf`
2. Extract all features by category
3. Save organized GeoJSON files
4. Update the index

## 📈 Statistics

After extraction, check `index.json` for:
- Total features extracted
- Features per category
- Generation timestamp
- Source file info

## 🎯 Future Use Cases

This structured data enables:
- **3D Map Labels**: Dynamic labels from `roads.geojson` and `places.geojson`
- **Search**: Full-text search across all POIs
- **Routing**: Use `roads.geojson` for offline navigation
- **Analysis**: Urban density, green space coverage, transit accessibility
- **AI Context**: Rich geographic context for Valora AI
- **Offline Maps**: Complete offline basemap with labels

## 📝 Notes

- All files are in **GeoJSON format** (standard, easy to parse)
- Coordinates are in **WGS84** (EPSG:4326)
- Files are **human-readable** (JSON with indentation)
- **Geometry types**: Point, LineString, Polygon
- **UTF-8 encoding** for international characters

## ⚠️ File size notes

- `raw/*.jsonl` can be **hundreds of MB**. Use **streaming** processing (read line-by-line), do not `json.load()` the whole file.
- Some derived layers (especially `derived/buildings_metadata.geojson`) are also large; for production, prefer viewport-based APIs or tiling.
