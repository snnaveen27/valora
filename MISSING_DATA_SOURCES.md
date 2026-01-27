# Valora AI - Data Status & Sources

**Last Updated**: January 27, 2026

This document tracks all data sources, ingestion status, and enhancement options for the Valora AI City Intelligence Platform.

---

## 📊 DATA SUMMARY

| Category | Records | Status |
|----------|---------|--------|
| **Properties** | 42,452 | ✅ Complete |
| **POIs** | 26,961+ | ✅ Complete |
| **Roads** | 334,784 | ✅ Complete |
| **Buildings** | 1,200 tiles | ✅ Complete |
| **Transport Stops** | 4,253 | ✅ Complete |
| **Real Estate Agents** | 51 | ✅ Complete |
| **AQI Data** | 1,550 records | ✅ Complete |
| **Watersheds** | 607 zones | ✅ Complete |
| **OpenCity Datasets** | 516 datasets | 🔄 Downloading |

---

## ✅ COMPLETED DATA

### 1. Property Data ✅
- **Records**: 42,452 properties
- **Sources**: MagicBricks (23,226), 99acres (18,685), Housing.com (536), NoBroker (5)
- **Features**: Price tracking, duplicate handling, location-based grouping
- **Script**: `scripts/track_price_changes.py`

### 2. Road Network ✅
- **Records**: 334,784 roads
- **Source**: bengaluru.pbf (OpenStreetMap)
- **Coverage**: Complete Bangalore road network

### 3. Points of Interest (POIs) ✅
| Category | Count | Source |
|----------|-------|--------|
| Schools | 2,007 | OpenCity + Google Maps |
| Hospitals | 150 | OpenCity + Google Maps |
| Restaurants | 288 | Google Maps |
| Banks/ATMs | 102 | Google Maps |
| Parks | 54 | Google Maps |
| Gyms | 52 | Google Maps |
| Worship | 70 | Google Maps |
| Fuel Stations | 56 | Google Maps |
| Public Toilets | 479 | OpenCity |
| Indira Canteens | 177 | OpenCity |
| Other | 23,467 | OSM |

### 4. Real Estate Agents ✅
- **Records**: 51 agents with ratings
- **Data**: Name, phone, rating, reviews, location
- **Source**: Google Maps Scraper

### 5. Environmental Data ✅
- **AQI Records**: 1,550 (2017-2025)
- **Watersheds**: 607 micro-watersheds
- **Source**: data_extra folder

### 6. Transport ✅
- **Metro Stations**: 29
- **Bus Stops**: 4,224
- **Source**: OSM + OpenCity

---

## 🔄 CURRENTLY DOWNLOADING

### OpenCity.in Datasets (516 total)
Smart downloader running with anti-ban measures:
- Rate limiting (2-5s delays)
- Batch pauses (20s every 10 downloads)
- Auto-retry with exponential backoff
- Auto-ingestion to database

**Priority GIS Datasets:**
| Dataset | Size | Status |
|---------|------|--------|
| Cadastral Maps | 96 MB | ✅ Downloaded |
| Slope Map | 5.6 MB | ✅ Downloaded |
| Groundwater Potential | 5.7 MB | ✅ Downloaded |
| Metro Stations KML | 79 KB | ✅ Downloaded |
| CCTV Cameras | 792 KB | ✅ Downloaded |
| Economic Census | 32 MB | ✅ Downloaded |
| BWSSB Boundaries | 1.7 MB | ✅ Downloaded |
| Ward Boundaries | 🔄 In Progress |
| Land Use Maps | 🔄 In Progress |

**Scripts:**
```bash
# Smart downloader (running)
python scripts/smart_opencity_downloader.py

# Priority GIS datasets
python scripts/download_priority_gis.py

# Organize after download
python scripts/organize_and_enhance_data.py
```

---

## 🔄 APIFY INTEGRATION

### Active Scrapers
| Platform | Actor | Use |
|----------|-------|-----|
| MagicBricks | `ecomscrape~magicbricks-property-search-scraper` | Properties |
| 99acres | `fatihtahta~99acres-scraper` | Properties |
| Housing.com | `ecomscrape~housing-dot-com-scraper` | Properties |
| NoBroker | `ecomscrape~nobroker-scraper` | Rentals |
| **Google Maps** | `apify/google-maps-scraper` | POIs with reviews |

### Scripts
- `scripts/google_maps_scraper.py` - POIs with reviews
- `scripts/scrape_agents_reviews.py` - Agents + reviews
- `scripts/scrape_all_bangalore_data.py` - Comprehensive POI scraper

---

## 📍 GIS LAYERS (Priority)

### Ward Boundaries & Administrative
- [ ] BBMP Ward Boundaries (198 wards)
- [ ] Assembly Constituencies
- [ ] BBMP Zones (8 zones)
- [x] BWSSB Division Boundaries

### Land Use & Zoning (BDA)
- [ ] BDA Revised Master Plan 2031
- [ ] Land Use Classification Maps
- [ ] FSI/FAR Zones
- [ ] Green Belt Areas

### Cadastral & Property
- [x] BBMP Cadastral Maps (71 MB)
- [x] Bengaluru Urban Cadastral (24 MB)
- [ ] Survey Numbers

### Infrastructure
- [x] Metro Stations & Lines
- [ ] Major Road Network
- [ ] Flyovers & Underpasses
- [ ] Water Supply Network
- [ ] Sewerage Network

---

## 🟡 MEDIUM PRIORITY

### 3. Traffic & Commute Data

**Google Maps API (requires API key)**
- https://developers.google.com/maps/documentation/distance-matrix
- Distance Matrix API for commute times

**TomTom Traffic API**
- https://developer.tomtom.com/traffic-api/traffic-api-documentation

**OpenStreetMap Traffic Data**
- https://wiki.openstreetmap.org/wiki/Key:traffic

---

### 4. School & Education Data

**UDISE+ Portal (Official)**
- https://udiseplus.gov.in/
- Download district-wise school data

**School Ratings**
- https://www.justdial.com/Bangalore/Schools
- Scrape or manual collection needed

---

### 5. Crime Statistics

**NCRB Data**
- https://ncrb.gov.in/
- Crime in India annual reports
- District-wise crime data

**Karnataka Police**
- https://www.ksp.gov.in/
- May have locality-specific data

---

### 6. Air Quality Index

**CPCB Real-time AQI**
- https://app.cpcbccr.com/AQI_India/
- API available for real-time data

**OpenAQ**
- https://openaq.org/
- https://api.openaq.org/v2/locations?city=Bangalore

---

### 7. Infrastructure Projects

**BMRCL (Metro)**
- https://english.bmrc.co.in/
- Metro expansion plans, new stations

**BBMP (Municipal)**
- https://bbmp.gov.in/
- Road projects, infrastructure development

**BDA (Development Authority)**
- https://bdabangalore.org/
- Master plans, zoning updates

---

## 🟢 NICE TO HAVE

### 8. Rental Market Data

**NoBroker**
- https://www.nobroker.in/
- Rental listings (scraping needed)

**Nestaway**
- https://www.nestaway.com/
- Rental data

---

### 9. Satellite Imagery

**Google Earth Engine**
- https://earthengine.google.com/
- Historical satellite imagery

**Sentinel Hub**
- https://www.sentinel-hub.com/
- Free satellite imagery

---

### 10. Census Demographics

**Census India**
- https://censusindia.gov.in/
- Population, demographics by ward

**Karnataka Open Data**
- https://data.karnataka.gov.in/
- Various government datasets

---

## 📥 After Downloading

Place downloaded files in: `src/data/downloads/`

Then run the appropriate ingestion script:
```bash
# For roads
python scripts/extract_roads_from_pbf.py

# For price history (create CSV first)
python scripts/ingest_price_history.py

# For other data
python scripts/ingest_custom_data.py <filename>
```

---

## 🔧 Quick Links Summary

| Data Type | Primary Source |
|-----------|---------------|
| Roads | https://download.geofabrik.de/asia/india/southern-zone.html |
| Prices | https://www.kaggle.com/datasets/amitabhajoy/bengaluru-house-price-data |
| Schools | https://udiseplus.gov.in/ |
| Crime | https://ncrb.gov.in/ |
| AQI | https://app.cpcbccr.com/AQI_India/ |
| Metro | https://english.bmrc.co.in/ |
| Census | https://censusindia.gov.in/ |
| Rentals | https://www.nobroker.in/ |

---

**Note**: Some data sources may require registration, API keys, or manual scraping. Government portals are the most reliable for official data.
