# Valora Database Schema Reference

> **For Developers & AI Agents** - Complete schema reference with field descriptions, indexes, and query patterns.

---

## 📊 Database Overview

| Table | Records | Purpose | Key Queries |
|-------|---------|---------|-------------|
| `properties` | 42,452 | Real estate listings | Search, filter, valuation |
| `buildings` | 686,370 | 3D building footprints | Spatial analysis, visualization |
| `pois` | 23,467 | Points of interest | Amenity search, scoring |
| `transport_stops` | 4,253 | Metro, bus stops | Commute analysis |
| `places` | 1,077 | Localities/neighborhoods | Geocoding, area stats |
| `terrain_grid` | 875 | Terrain analysis | Flood risk, elevation |
| `gov_data` | 12,767 | Government data | Population, schools |
| `property_analytics` | 0 | Computed scores | Investment scoring |
| `price_history` | 0 | Historical prices | Trend analysis |
| `roads` | 0 | Road network | Routing (future) |

---

## 🏠 properties

**Purpose:** Core property listings from multiple sources (99acres, MagicBricks, NoBroker, etc.)

### Fields

| Column | Type | Indexed | Description | Example Values |
|--------|------|---------|-------------|----------------|
| `id` | INTEGER | PK | Auto-increment ID | 1, 2, 3 |
| `property_id` | TEXT | ✅ UNIQUE | Source-specific ID | `99acres_12345` |
| `source` | TEXT | ✅ | Data source | `99acres`, `magicbricks`, `nobroker` |
| `raw_data` | TEXT | | Complete JSON from source | `{...}` |
| **Basic Info** |
| `title` | TEXT | | Listing title | "3BHK Apartment in Whitefield" |
| `description` | TEXT | | Full description | "Spacious apartment..." |
| `property_type` | TEXT | ✅ | Type of property | `apartment`, `villa`, `plot`, `pg` |
| `listing_type` | TEXT | ✅ | Sale or rent | `sale`, `rent` |
| **Location** |
| `address` | TEXT | | Full address | "123 MG Road, Bangalore" |
| `locality` | TEXT | ✅ | Sub-area name | `HSR Layout`, `Indiranagar` |
| `area_name` | TEXT | ✅ | Broader area | `Whitefield`, `Koramangala` |
| `city` | TEXT | | City name | `Bangalore` |
| `pincode` | TEXT | ✅* | Postal code | `560001` |
| `latitude` | REAL | ✅ (composite) | GPS latitude | `12.9716` |
| `longitude` | REAL | ✅ (composite) | GPS longitude | `77.5946` |
| **Specs** |
| `bedrooms` | INTEGER | ✅ | Number of bedrooms | `1`, `2`, `3`, `4` |
| `bathrooms` | INTEGER | | Number of bathrooms | `1`, `2`, `3` |
| `balconies` | INTEGER | | Number of balconies | `0`, `1`, `2` |
| `total_area_sqft` | REAL | | Total area in sqft | `1200.5` |
| `carpet_area_sqft` | REAL | | Carpet area | `950.0` |
| `floor_number` | INTEGER | | Floor number | `0` (ground), `5`, `12` |
| `total_floors` | INTEGER | | Building floors | `4`, `12`, `20` |
| `furnishing` | TEXT | | Furnishing status | `unfurnished`, `semi`, `fully` |
| `facing` | TEXT | | Direction facing | `east`, `north`, `corner` |
| `age_years` | INTEGER | | Property age | `0` (new), `5`, `10` |
| `parking` | TEXT | | Parking info | `covered`, `open`, `2 covered` |
| **Pricing** |
| `price` | REAL | ✅ | Price in INR | `7500000` (75 lakhs) |
| `price_per_sqft` | REAL | | Price per sqft | `6250` |
| `price_display` | TEXT | | Formatted price | `₹75 Lac`, `₹1.2 Cr` |
| `maintenance_monthly` | REAL | | Monthly maintenance | `5000` |
| `deposit` | REAL | | Security deposit | `200000` |
| **Amenities** |
| `amenities` | TEXT | | JSON array | `["gym", "pool", "security"]` |
| `amenities_map` | TEXT | | JSON object | `{"LIFT": true, "GYM": false}` |
| **Status** |
| `status` | TEXT | ✅ | Listing status | `active`, `sold`, `expired` |
| `posted_at` | TIMESTAMP | | When posted | `2026-01-15 10:30:00` |
| `created_at` | TIMESTAMP | ✅ | DB insert time | `2026-01-20 14:22:00` |

### Schema v2 Extensions (Enhanced Fields)

| Column | Type | Indexed | Description | Use Case |
|--------|------|---------|-------------|----------|
| `property_category` | TEXT | ✅ | High-level category | `residential`, `commercial`, `plot`, `pg` |
| `property_subtype` | TEXT | ✅ | Specific type | `flat`, `villa`, `office`, `warehouse` |
| `bhk` | TEXT | ✅ | BHK configuration | `1BHK`, `2BHK`, `3BHK+Study` |
| `rent_monthly` | REAL | | Monthly rent | `25000` |
| `pg_type` | TEXT | ✅ | PG gender type | `boys`, `girls`, `coed` |
| `room_type` | TEXT | | PG room type | `single`, `double`, `triple` |
| `plot_area_sqft` | REAL | | Plot size | `2400` (30x80) |
| `plot_facing` | TEXT | | Plot direction | `east`, `north`, `corner` |
| `commercial_type` | TEXT | ✅ | Commercial sub-type | `office`, `shop`, `showroom` |

### Indexes

```sql
idx_properties_area (area_name)
idx_properties_locality (locality)
idx_properties_type (property_type)
idx_properties_listing (listing_type)
idx_properties_price (price)
idx_properties_bedrooms (bedrooms)
idx_properties_status (status)
idx_properties_source (source)
idx_properties_created (created_at)
idx_properties_coords (latitude, longitude)
-- Schema v2 additions:
idx_properties_category (property_category)
idx_properties_subtype (property_subtype)
idx_properties_bhk (bhk)
idx_properties_pg_type (pg_type)
idx_prop_cat_listing (property_category, listing_type)
idx_prop_cat_price (property_category, price)
```

### Common Query Patterns

```sql
-- Rent vs Buy filter
SELECT * FROM properties WHERE listing_type = 'rent' AND area_name = 'Koramangala';

-- BHK filter
SELECT * FROM properties WHERE bedrooms = 2 AND price < 8000000;

-- PG/Hostel search
SELECT * FROM properties WHERE property_category = 'pg' AND pg_type = 'girls';

-- Plot search
SELECT * FROM properties WHERE property_category = 'plot' AND plot_area_sqft >= 2400;

-- Radius search (bounding box)
SELECT * FROM properties 
WHERE latitude BETWEEN ? AND ? 
AND longitude BETWEEN ? AND ?
AND listing_type = 'sale';

-- Full-text search (basic)
SELECT * FROM properties 
WHERE title LIKE '%whitefield%' OR description LIKE '%whitefield%';
```

---

## 📍 pois (Points of Interest)

**Purpose:** Amenities, shops, schools, hospitals, etc.

### Fields

| Column | Type | Indexed | Description | Example Values |
|--------|------|---------|-------------|----------------|
| `poi_id` | TEXT | ✅ UNIQUE | Unique POI ID | `osm_poi_12345` |
| `name` | TEXT | | POI name | "Phoenix Marketcity" |
| `category` | TEXT | ✅ | Main category | `shopping`, `education`, `healthcare` |
| `subcategory` | TEXT | | Sub-category | `mall`, `school`, `hospital` |
| `latitude` | REAL | ✅ (composite) | GPS latitude | `12.9850` |
| `longitude` | REAL | ✅ (composite) | GPS longitude | `77.6410` |
| `area_name` | TEXT | ✅ | Area location | `Whitefield` |
| `rating` | REAL | | User rating | `4.2` |
| `reviews_count` | INTEGER | | Number of reviews | `1250` |

### Query Patterns

```sql
-- Find schools near location
SELECT * FROM pois 
WHERE category = 'education' 
AND latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?;

-- Count POIs by category in area
SELECT category, COUNT(*) as cnt FROM pois 
WHERE area_name = 'Koramangala' GROUP BY category;
```

---

## 🚇 transport_stops

**Purpose:** Metro stations, bus stops, railway stations

### Fields

| Column | Type | Indexed | Description | Example Values |
|--------|------|---------|-------------|----------------|
| `stop_id` | TEXT | ✅ UNIQUE | Unique stop ID | `metro_blr_001` |
| `name` | TEXT | | Stop name | "Indiranagar Metro" |
| `transport_type` | TEXT | ✅ | Transport mode | `metro`, `bus`, `railway` |
| `line_name` | TEXT | | Line/route name | `Purple Line`, `Route 500` |
| `latitude` | REAL | ✅ (composite) | GPS latitude | `12.9784` |
| `longitude` | REAL | ✅ (composite) | GPS longitude | `77.6408` |

### Query Patterns

```sql
-- Find nearest metro station
SELECT *, 
  (ABS(latitude - ?) + ABS(longitude - ?)) as approx_dist
FROM transport_stops 
WHERE transport_type = 'metro'
ORDER BY approx_dist LIMIT 1;
```

---

## 🏢 buildings

**Purpose:** 3D building footprints for visualization and analysis

### Fields

| Column | Type | Indexed | Description | Example Values |
|--------|------|---------|-------------|----------------|
| `osm_id` | TEXT | ✅ UNIQUE | OSM building ID | `way/123456789` |
| `building_type` | TEXT | ✅ | Building use | `residential`, `commercial`, `retail` |
| `name` | TEXT | | Building name | "Gold Strike Apartments" |
| `height` | REAL | | Height in meters | `38.5` |
| `levels` | INTEGER | | Number of floors | `12` |
| `latitude` | REAL | ✅ (composite) | Centroid lat | `12.9650` |
| `longitude` | REAL | ✅ (composite) | Centroid lng | `77.7120` |

---

## 🗺️ places

**Purpose:** Localities, neighborhoods, areas for geocoding

### Fields

| Column | Type | Indexed | Description | Example Values |
|--------|------|---------|-------------|----------------|
| `place_id` | TEXT | ✅ UNIQUE | Place identifier | `blr_koramangala` |
| `name` | TEXT | | Place name | "Koramangala" |
| `place_type` | TEXT | | Type of place | `locality`, `suburb`, `neighborhood` |
| `center_latitude` | REAL | | Center lat | `12.9352` |
| `center_longitude` | REAL | | Center lng | `77.6245` |
| `population` | INTEGER | | Population count | `150000` |
| `avg_price_per_sqft` | REAL | | Avg price/sqft | `12500` |

---

## 📈 property_analytics (Computed)

**Purpose:** Pre-computed scores and metrics for fast retrieval

### Fields

| Column | Type | Indexed | Description |
|--------|------|---------|-------------|
| `property_id` | TEXT | ✅ FK | Links to properties |
| `metro_proximity_score` | REAL | | 0-100 score |
| `school_proximity_score` | REAL | | 0-100 score |
| `hospital_proximity_score` | REAL | | 0-100 score |
| `nearest_metro_distance` | REAL | | Distance in meters |
| `investment_score` | REAL | ✅ | 0-100 score |
| `area_price_trend` | REAL | | % change |

---

## 📉 price_history

**Purpose:** Track property price changes over time

### Fields

| Column | Type | Indexed | Description |
|--------|------|---------|-------------|
| `property_id` | TEXT | ✅ FK | Links to properties |
| `price` | REAL | | Price at time |
| `price_per_sqft` | REAL | | Price/sqft at time |
| `recorded_at` | TIMESTAMP | ✅ | When recorded |

---

## 🌍 terrain_grid

**Purpose:** Terrain analysis grid cells for flood risk, elevation

### Key Fields

| Column | Type | Description |
|--------|------|-------------|
| `grid_id` | TEXT | Grid cell ID |
| `flood_risk` | TEXT | `high`, `medium`, `low` |
| `elevation_m` | REAL | Elevation in meters |

---

## 🏛️ gov_data

**Purpose:** Government data (schools, population, infrastructure)

### Key Fields

| Column | Type | Description |
|--------|------|-------------|
| `record_id` | TEXT | Record identifier |
| `data_type` | TEXT | `school`, `population`, `infrastructure` |
| `attributes` | TEXT | JSON attributes |

---

## 📋 Views (Pre-defined)

### area_property_summary
Aggregated property stats by area:
- `property_count`, `avg_price`, `avg_price_per_sqft`
- `for_sale`, `for_rent` counts

### property_type_summary
Stats grouped by property_type and listing_type

### source_summary
Records per data source with timestamps

---

## 🔍 Query Service Methods

### PropertyService.search()
```python
def search(
    lat: float = None,
    lng: float = None,
    radius_m: int = 2000,
    property_type: str = None,      # apartment, villa, plot, pg
    listing_type: str = None,       # sale, rent  <-- ADD THIS
    property_category: str = None,  # residential, commercial, pg, plot <-- ADD THIS
    min_price: int = None,
    max_price: int = None,
    min_bedrooms: int = None,
    max_bedrooms: int = None,
    bhk: str = None,                # 1BHK, 2BHK, 3BHK <-- ADD THIS
    pg_type: str = None,            # boys, girls, coed <-- ADD THIS
    query: str = None,              # Full-text search
    limit: int = 50
) -> List[Dict]
```

### DatabaseQueryService Methods
- `search_properties()` - Main property search
- `get_pois()` - POI search by location/category
- `get_transport()` - Transport stops search
- `get_buildings()` - Building footprints
- `get_places()` - Locality lookup
- `get_metro_stations()` - Metro-specific query

---

## ⚠️ Known Gaps

| Gap | Impact | Status |
|-----|--------|--------|
| `listing_type` not in PropertyService.search() | Rent queries fail | **TODO** |
| `property_category`, `pg_type` unused | PG/Plot queries fail | **TODO** |
| `search_text` not indexed | Slow full-text search | **TODO** |
| `places.name` not indexed | Slow geocoding | Low priority |
| `roads` table empty | No routing | Future |
| `price_history` empty | No trends | Future |

---

## 🧪 Test Queries

### Rent vs Buy
```
"2BHK for rent in Koramangala" → listing_type='rent', bedrooms=2, area_name='Koramangala'
"apartments for sale under 1 crore" → listing_type='sale', price < 10000000
```

### PG/Hostel
```
"girls PG in HSR Layout" → property_category='pg', pg_type='girls', locality='HSR Layout'
"bachelor friendly PG near Whitefield" → property_category='pg', area_name='Whitefield'
```

### Plots
```
"plots in Yelahanka" → property_category='plot', area_name='Yelahanka'
"BDA approved sites" → approved_by LIKE '%BDA%'
```

### Commercial
```
"office space in MG Road" → property_category='commercial', commercial_type='office'
"warehouse in Peenya" → commercial_type='warehouse', area_name='Peenya'
```

---

*Last Updated: January 2026*
