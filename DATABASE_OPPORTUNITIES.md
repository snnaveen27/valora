# Valora Database Opportunities

## Current Data Summary

| Table | Records | Usage Status |
|-------|---------|--------------|
| properties | 42,202 | ✅ Active |
| buildings | 1,372,740 | ✅ Active (3D analysis) |
| pois | 29,240 | ✅ Active (spatial) |
| transport_stops | 5,384 | ✅ Active |
| places | 1,081 | 🔶 Partial |
| terrain_grid | 9,090 | ✅ Active (flood risk) |
| gov_data | 12,767 | 🔶 Partial (enhanced data service) |
| price_history | 0 | ❌ Empty |
| property_analytics | 0 | ❌ Empty |
| roads | 0 | ❌ Empty |

---

## ✨ Recent Enhancements (Jan 2026)

### AI-Driven Panel Orchestration
- **Chat Panel**: Locality cards inline with Explore/Ask buttons
- **Analysis Panel**: "Ask about this" buttons on insights
- **Map Panel**: Animated storytelling with narration overlay
- **Why? Tab**: SHAP-style explainability (feature bars, confidence gauge)

### City Intelligence Integration
- Locality profiling (10 archetypes)
- Growth stage detection (mature/maturing/growing/emerging)
- Risk index calculation (hazard + infrastructure + speculation)
- Causal reasoning for what-if scenarios

---

## HIGH PRIORITY: Immediate Improvements

### 1. Extract Property Amenities (Impact: HIGH)

**Current State:** Amenities stored as JSON in `raw_data`, not queryable

**Data Available:**
```json
{
  "LIFT": true,
  "GYM": false,
  "POOL": false,
  "SECURITY": true,
  "INTERCOM": true,
  "PARK": false,
  "STP": true  // Sewage Treatment
}
```

**Implementation:**
1. Add `amenities_parsed` column (JSON or separate table)
2. Create search filters: "with gym", "with pool", "gated community"
3. Add to property cards in UI

**Effort:** 4 hours

---

### 2. Populate Property Analytics Cache (Impact: HIGH)

**Current State:** Table exists but empty (0 records)

**Schema has:**
- `metro_proximity_score` (0-100)
- `school_proximity_score`
- `hospital_proximity_score`
- `nearest_metro_distance` (meters)
- `investment_score`
- `area_price_trend`

**Implementation:**
1. Create batch job to compute scores for all properties
2. Use existing `spatial_inference.py` for scoring
3. Cache results for fast retrieval

**Effort:** 3 hours

---

### 3. Use Government Data for Area Analysis (Impact: MEDIUM)

**Current State:** 12,767 records NOT used

**Data Available:**
- **Population:** Village-level population (general, SC, ST)
- **Households:** Count per habitation
- **Water Supply:** PWS connections, quality
- **Schools:** UDISE data (enrollment, teachers, infrastructure)

**Implementation:**
1. Link gov_data to places/areas by village/locality name
2. Add to area analysis: "This area has X population, Y schools"
3. Infrastructure quality scoring

**Effort:** 6 hours

---

### 4. Named Buildings for Better Context (Impact: MEDIUM)

**Current State:** 16,587 named buildings, not used in responses

**Examples:**
- "Gold Strike" (apartments, 38.5m)
- "City Market" (retail, 10.5m)
- "Radiance" (apartments, 38.5m)

**Implementation:**
1. Use in spatial descriptions: "Near Gold Strike apartments"
2. Landmark-based navigation
3. Building name search

**Effort:** 2 hours

---

## MEDIUM PRIORITY: Feature Enhancements

### 5. Price History Tracking (Impact: HIGH, Effort: HIGH)

**Current State:** Schema exists, 0 records

**Opportunity:**
1. Track price changes when properties are re-scraped
2. Enable: "This property dropped 5% in last month"
3. Area price trend calculations

**Effort:** 8 hours (needs scraping integration)

---

### 6. Terrain Data for Property Warnings (Impact: MEDIUM)

**Current State:** 9,090 grid cells with flood risk, partially used

**Data Available:**
```
Flood Risk Distribution:
- High: 1,357 cells
- Medium: 2,822 cells  
- Low: 4,911 cells
```

**Implementation:**
1. Show flood risk warning on property cards
2. "⚠️ This area has HIGH flood risk"
3. Filter: "Show only low flood risk areas"

**Effort:** 3 hours

---

### 7. Property Photos for Visual AI (Impact: HIGH)

**Current State:** Photo URLs in raw_data, not extracted

**Data Available:**
- Most properties have 1-5 photos
- Keys: `images_map`, `display_pic`, URLs

**Implementation:**
1. Extract photo URLs to `images` column
2. When Qwen VL ready: analyze quality, style
3. Visual property comparison

**Effort:** 4 hours (extraction) + visual AI integration

---

## LOW PRIORITY: Future Features

### 8. POI Ratings & Reviews

**Current State:** Schema has `rating`, `reviews_count` but POIs show "other" category

**Opportunity:**
- Re-categorize POIs properly
- Use ratings in recommendations: "Highly rated restaurant nearby"

### 9. Roads Network

**Current State:** Table empty

**Opportunity:**
- Import from OSM
- Enable route calculations
- Traffic-aware analysis

### 10. Places Price Data

**Current State:** `avg_price_per_sqft` exists but all NULL

**Opportunity:**
- Compute from property data
- "Koramangala: ₹12,500/sqft average"

---

## Implementation Priority Matrix

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Extract Amenities | HIGH | 4h | 🔴 P1 |
| Populate Analytics Cache | HIGH | 3h | 🔴 P1 |
| Use Gov Data | MEDIUM | 6h | 🟡 P2 |
| Named Buildings | MEDIUM | 2h | 🟡 P2 |
| Terrain Warnings | MEDIUM | 3h | 🟡 P2 |
| Photo Extraction | HIGH | 4h | 🟡 P2 |
| Price History | HIGH | 8h | 🟠 P3 |
| POI Recategorization | LOW | 4h | ⚪ P4 |

---

## Quick Wins (< 2 hours each)

1. **Show flood risk on properties** - Just query terrain_grid
2. **Use named buildings in descriptions** - Already in DB
3. **Area population from gov_data** - Simple join
4. **Amenity icons on property cards** - Parse existing JSON

---

## Data Quality Issues to Fix

1. **POIs all "other" category** - Need recategorization
2. **Transport type "unknown"** - 5,384 stops need typing
3. **Properties missing coordinates** - 50% have lat/lng
4. **Places missing price data** - Need computation

---

*Generated: Jan 2026*
