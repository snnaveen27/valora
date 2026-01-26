-- Valora SQLite Database Schema (Simple - No SpatiaLite)
-- Uses lat/lng columns instead of geometry for Windows compatibility

-- ============================================================================
-- PROPERTIES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    source_file TEXT,
    
    -- COMPLETE RAW DATA (nothing is lost)
    raw_data TEXT NOT NULL,
    
    -- Basic Info (normalized for querying)
    title TEXT,
    description TEXT,
    property_type TEXT,
    listing_type TEXT,
    
    -- Location
    address TEXT,
    locality TEXT,
    area_name TEXT,
    city TEXT DEFAULT 'Bangalore',
    state TEXT DEFAULT 'Karnataka',
    pincode TEXT,
    latitude REAL,
    longitude REAL,
    
    -- Specs
    bedrooms INTEGER,
    bathrooms INTEGER,
    balconies INTEGER,
    total_area_sqft REAL,
    carpet_area_sqft REAL,
    floor_number INTEGER,
    total_floors INTEGER,
    furnishing TEXT,
    facing TEXT,
    age_years INTEGER,
    parking TEXT,
    
    -- Pricing
    price REAL,
    price_per_sqft REAL,
    price_display TEXT,
    maintenance_monthly REAL,
    deposit REAL,
    negotiable BOOLEAN,
    
    -- Amenities (JSON array)
    amenities TEXT,
    amenities_map TEXT,
    
    -- Contact/Builder
    builder_name TEXT,
    owner_name TEXT,
    owner_type TEXT,
    contact_name TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    
    -- Media (JSON arrays)
    images TEXT,
    photos_data TEXT,
    video_url TEXT,
    virtual_tour_url TEXT,
    
    -- Status
    status TEXT DEFAULT 'active',
    possession_status TEXT,
    verified BOOLEAN DEFAULT 0,
    featured BOOLEAN DEFAULT 0,
    premium BOOLEAN DEFAULT 0,
    
    -- Source-specific fields (JSON)
    source_specific TEXT,
    
    -- Nearby/Landmarks (JSON)
    landmarks TEXT,
    nearby_places TEXT,
    
    -- Scores/Analytics
    property_score REAL,
    locality_growth_rate REAL,
    investment_score REAL,
    
    -- URLs
    source_url TEXT,
    page_url TEXT,
    project_url TEXT,
    
    -- Timestamps
    posted_at TIMESTAMP,
    scraped_at TIMESTAMP,
    available_from TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Search optimization
    search_text TEXT
);

-- Indexes for properties
CREATE INDEX IF NOT EXISTS idx_properties_area ON properties(area_name);
CREATE INDEX IF NOT EXISTS idx_properties_locality ON properties(locality);
CREATE INDEX IF NOT EXISTS idx_properties_type ON properties(property_type);
CREATE INDEX IF NOT EXISTS idx_properties_listing ON properties(listing_type);
CREATE INDEX IF NOT EXISTS idx_properties_price ON properties(price);
CREATE INDEX IF NOT EXISTS idx_properties_bedrooms ON properties(bedrooms);
CREATE INDEX IF NOT EXISTS idx_properties_status ON properties(status);
CREATE INDEX IF NOT EXISTS idx_properties_source ON properties(source);
CREATE INDEX IF NOT EXISTS idx_properties_created ON properties(created_at);
CREATE INDEX IF NOT EXISTS idx_properties_coords ON properties(latitude, longitude);

-- ============================================================================
-- POINTS OF INTEREST (POI)
-- ============================================================================

CREATE TABLE IF NOT EXISTS pois (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poi_id TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    
    -- Basic Info
    name TEXT NOT NULL,
    category TEXT,
    subcategory TEXT,
    
    -- Location
    address TEXT,
    locality TEXT,
    area_name TEXT,
    city TEXT DEFAULT 'Bangalore',
    pincode TEXT,
    latitude REAL,
    longitude REAL,
    
    -- Details
    rating REAL,
    reviews_count INTEGER,
    phone TEXT,
    website TEXT,
    opening_hours TEXT,
    
    -- Attributes
    attributes TEXT,
    
    -- Metadata
    source_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pois_category ON pois(category);
CREATE INDEX IF NOT EXISTS idx_pois_area ON pois(area_name);
CREATE INDEX IF NOT EXISTS idx_pois_coords ON pois(latitude, longitude);

-- ============================================================================
-- PLACES & NEIGHBORHOODS
-- ============================================================================

CREATE TABLE IF NOT EXISTS places (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    
    -- Basic Info
    name TEXT NOT NULL,
    display_name TEXT,
    place_type TEXT,
    
    -- Location
    parent_place TEXT,
    city TEXT DEFAULT 'Bangalore',
    center_latitude REAL,
    center_longitude REAL,
    
    -- Stats
    population INTEGER,
    area_sqkm REAL,
    density_per_sqkm REAL,
    
    -- Properties stats
    property_count INTEGER DEFAULT 0,
    avg_price_per_sqft REAL,
    avg_price REAL,
    
    -- Metadata
    attributes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- BUILDINGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS buildings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    osm_id TEXT UNIQUE,
    osm_type TEXT,
    
    -- Building info
    building_type TEXT,
    name TEXT,
    height REAL,
    levels INTEGER,
    
    -- Address
    address TEXT,
    street TEXT,
    locality TEXT,
    area_name TEXT,
    
    -- Location
    latitude REAL,
    longitude REAL,
    
    -- Metadata
    source_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_buildings_type ON buildings(building_type);
CREATE INDEX IF NOT EXISTS idx_buildings_area ON buildings(area_name);
CREATE INDEX IF NOT EXISTS idx_buildings_coords ON buildings(latitude, longitude);

-- ============================================================================
-- TRANSPORT STOPS
-- ============================================================================

CREATE TABLE IF NOT EXISTS transport_stops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stop_id TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    
    -- Basic Info
    name TEXT NOT NULL,
    transport_type TEXT,
    line_name TEXT,
    
    -- Location
    address TEXT,
    area_name TEXT,
    latitude REAL,
    longitude REAL,
    
    -- Details
    operational BOOLEAN DEFAULT 1,
    platform_count INTEGER,
    
    -- Metadata
    attributes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transport_type ON transport_stops(transport_type);
CREATE INDEX IF NOT EXISTS idx_transport_coords ON transport_stops(latitude, longitude);

-- ============================================================================
-- ROADS
-- ============================================================================

CREATE TABLE IF NOT EXISTS roads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    osm_id TEXT UNIQUE,
    
    -- Road info
    name TEXT,
    road_type TEXT,
    surface TEXT,
    lanes INTEGER,
    max_speed INTEGER,
    oneway BOOLEAN,
    
    -- Metadata
    source_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- PROPERTY ANALYTICS
-- ============================================================================

CREATE TABLE IF NOT EXISTS property_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id TEXT UNIQUE NOT NULL,
    
    -- Proximity scores (0-100)
    metro_proximity_score REAL,
    school_proximity_score REAL,
    hospital_proximity_score REAL,
    shopping_proximity_score REAL,
    
    -- Nearest distances (meters)
    nearest_metro_distance REAL,
    nearest_school_distance REAL,
    nearest_hospital_distance REAL,
    
    -- Area analytics
    area_avg_price REAL,
    area_price_trend REAL,
    
    -- Investment score (0-100)
    investment_score REAL,
    
    -- Metadata
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (property_id) REFERENCES properties(property_id)
);

CREATE INDEX IF NOT EXISTS idx_analytics_investment ON property_analytics(investment_score);

-- ============================================================================
-- PRICE HISTORY
-- ============================================================================

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id TEXT NOT NULL,
    price REAL NOT NULL,
    price_per_sqft REAL,
    listing_type TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (property_id) REFERENCES properties(property_id)
);

CREATE INDEX IF NOT EXISTS idx_price_history_property ON price_history(property_id);
CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(recorded_at);

-- ============================================================================
-- DATA SOURCE TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS data_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT UNIQUE NOT NULL,
    source_type TEXT,
    
    -- Stats
    total_records INTEGER DEFAULT 0,
    last_ingested_at TIMESTAMP,
    last_status TEXT,
    last_error TEXT,
    
    -- Config
    config TEXT,
    enabled BOOLEAN DEFAULT 1,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INGESTION LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS ingestion_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    
    -- Stats
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    
    -- Status
    status TEXT,
    error_message TEXT,
    
    -- Timing
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ingestion_source ON ingestion_log(source_name);
CREATE INDEX IF NOT EXISTS idx_ingestion_started ON ingestion_log(started_at);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Area property summary
CREATE VIEW IF NOT EXISTS area_property_summary AS
SELECT 
    area_name,
    COUNT(*) as property_count,
    AVG(price) as avg_price,
    AVG(price_per_sqft) as avg_price_per_sqft,
    MIN(price) as min_price,
    MAX(price) as max_price,
    AVG(bedrooms) as avg_bedrooms,
    SUM(CASE WHEN listing_type = 'sale' THEN 1 ELSE 0 END) as for_sale,
    SUM(CASE WHEN listing_type = 'rent' THEN 1 ELSE 0 END) as for_rent
FROM properties
WHERE status = 'active' AND area_name IS NOT NULL
GROUP BY area_name;

-- Source summary
CREATE VIEW IF NOT EXISTS source_summary AS
SELECT 
    source,
    COUNT(*) as total_count,
    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_count,
    AVG(price) as avg_price,
    MIN(created_at) as first_ingested,
    MAX(created_at) as last_ingested
FROM properties
GROUP BY source;

-- Property type summary
CREATE VIEW IF NOT EXISTS property_type_summary AS
SELECT 
    property_type,
    listing_type,
    COUNT(*) as count,
    AVG(price) as avg_price,
    AVG(price_per_sqft) as avg_price_per_sqft
FROM properties
WHERE status = 'active'
GROUP BY property_type, listing_type;
