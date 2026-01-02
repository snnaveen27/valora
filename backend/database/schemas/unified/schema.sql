-- ============================================================================
-- Unified PostgreSQL Schema for Real Estate Platform
-- Supports structured, unstructured, and geospatial data
-- ============================================================================

-- Initialize PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS vector; -- For vector embeddings

-- ============================================================================
-- CORE PROPERTY TABLES
-- ============================================================================

-- Main properties table (MVP fields)
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core identification
    listing_id VARCHAR(255) UNIQUE,
    source VARCHAR(100) NOT NULL, -- magicbricks, 99acres, scraped, registry, etc.
    source_url TEXT,
    
    -- Location (structured)
    city VARCHAR(100),
    locality VARCHAR(255),
    sub_locality VARCHAR(255),
    address TEXT,
    pincode VARCHAR(20),
    ward VARCHAR(100),
    
    -- Geospatial (PostGIS)
    location GEOGRAPHY(POINT, 4326), -- lat/lng
    boundary GEOGRAPHY(POLYGON, 4326), -- property boundary if available
    
    -- Property core
    property_type VARCHAR(100), -- apartment, house, plot, office, shop, etc.
    property_subtype VARCHAR(100), -- 1bhk, 2bhk, villa, warehouse, etc.
    listing_type VARCHAR(50), -- sale, rent, lease
    
    -- Physical attributes
    area_sqft NUMERIC(12, 2),
    bedrooms INTEGER,
    bathrooms INTEGER,
    balconies INTEGER,
    floor INTEGER,
    total_floors INTEGER,
    built_year INTEGER,
    age_years INTEGER,
    parking_spaces INTEGER,
    furnishing VARCHAR(50), -- furnished, semi-furnished, unfurnished
    
    -- Pricing
    price NUMERIC(15, 2),
    price_per_sqft NUMERIC(10, 2),
    maintenance_charges NUMERIC(10, 2),
    security_deposit NUMERIC(15, 2),
    
    -- Listing metadata
    listing_date TIMESTAMP,
    updated_date TIMESTAMP,
    possession_status VARCHAR(50), -- ready, under-construction, upcoming
    seller_type VARCHAR(50), -- owner, agent, builder
    
    -- Additional features (JSONB for flexibility)
    amenities JSONB, -- array of amenity names
    photos JSONB, -- array of photo URLs
    metadata JSONB, -- any additional unstructured data
    
    -- Derived/computed fields
    size_category VARCHAR(50),
    price_per_room NUMERIC(12, 2),
    
    -- ETL metadata
    raw_filename VARCHAR(500),
    extracted_metadata JSONB, -- metadata extracted from filename/path
    data_quality_score NUMERIC(3, 2), -- 0-1 score
    missing_fields JSONB, -- list of missing critical fields
    
    -- Vector embeddings for AI/ML (pgvector)
    description_embedding VECTOR(1536), -- For property description similarity
    amenities_embedding VECTOR(1536),   -- For amenities-based recommendations
    location_embedding VECTOR(1536),    -- For location-based semantic search
    combined_embedding VECTOR(1536),    -- Combined features for similarity
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT valid_price CHECK (price >= 0),
    CONSTRAINT valid_area CHECK (area_sqft > 0 OR area_sqft IS NULL)
);

CREATE INDEX idx_properties_city ON properties(city);
CREATE INDEX idx_properties_locality ON properties(locality);
CREATE INDEX idx_properties_type ON properties(property_type);
CREATE INDEX idx_properties_price ON properties(price);
CREATE INDEX idx_properties_location ON properties USING GIST(location);
CREATE INDEX idx_properties_listing_date ON properties(listing_date);
CREATE INDEX idx_properties_source ON properties(source);
CREATE INDEX idx_properties_metadata ON properties USING GIN(metadata);

-- Vector indexes for similarity search (pgvector)
CREATE INDEX idx_properties_description_vector ON properties USING ivfflat (description_embedding vector_cosine_ops);
CREATE INDEX idx_properties_amenities_vector ON properties USING ivfflat (amenities_embedding vector_cosine_ops);
CREATE INDEX idx_properties_location_vector ON properties USING ivfflat (location_embedding vector_cosine_ops);
CREATE INDEX idx_properties_combined_vector ON properties USING ivfflat (combined_embedding vector_cosine_ops);

-- ============================================================================
-- TRANSACTION DATA (High Value)
-- ============================================================================

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID REFERENCES properties(id),
    
    -- Transaction details
    transaction_type VARCHAR(50), -- sale, rental_agreement, lease
    sale_price NUMERIC(15, 2),
    sale_date DATE NOT NULL,
    registry_id VARCHAR(255) UNIQUE,
    instrument_type VARCHAR(100),
    
    -- Parties (hashed for privacy)
    buyer_hash VARCHAR(255),
    seller_hash VARCHAR(255),
    
    -- Derived metrics
    realized_appreciation_pct NUMERIC(8, 2),
    time_to_sale_days INTEGER,
    
    -- Metadata
    source VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transactions_property ON transactions(property_id);
CREATE INDEX idx_transactions_date ON transactions(sale_date);
CREATE INDEX idx_transactions_registry ON transactions(registry_id);

-- ============================================================================
-- RENTAL DATA
-- ============================================================================

CREATE TABLE rental_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID REFERENCES properties(id),
    
    -- Rental specifics
    monthly_rent NUMERIC(12, 2),
    lease_duration_months INTEGER,
    furnished_status VARCHAR(50),
    rental_yield_pct NUMERIC(5, 2),
    
    -- Metadata
    listing_date TIMESTAMP,
    source VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- POI & INFRASTRUCTURE (MVP)
-- ============================================================================

CREATE TABLE pois (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- POI details
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL, -- metro, hospital, school, mall, airport, etc.
    subcategory VARCHAR(100),
    
    -- Location
    location GEOGRAPHY(POINT, 4326),
    city VARCHAR(100),
    address TEXT,
    
    -- Metadata
    rating NUMERIC(2, 1),
    capacity INTEGER, -- for schools, hospitals
    metadata JSONB,
    
    -- Data provenance
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pois_location ON pois USING GIST(location);
CREATE INDEX idx_pois_category ON pois(category);
CREATE INDEX idx_pois_city ON pois(city);

-- ============================================================================
-- SPATIAL FEATURES (Precomputed for performance)
-- ============================================================================

CREATE TABLE property_spatial_features (
    property_id UUID PRIMARY KEY REFERENCES properties(id),
    
    -- Distance to key POIs (in km)
    distance_to_metro NUMERIC(8, 2),
    distance_to_hospital NUMERIC(8, 2),
    distance_to_school NUMERIC(8, 2),
    distance_to_mall NUMERIC(8, 2),
    distance_to_airport NUMERIC(8, 2),
    distance_to_railway NUMERIC(8, 2),
    
    -- Density metrics (within radius)
    poi_density_1km INTEGER,
    poi_density_3km INTEGER,
    poi_density_5km INTEGER,
    
    -- Composite scores
    infrastructure_score NUMERIC(3, 2),
    connectivity_score NUMERIC(3, 2),
    lifestyle_score NUMERIC(3, 2),
    
    -- Metadata
    computed_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

-- ============================================================================
-- MARKET AGGREGATES & ANALYTICS
-- ============================================================================

CREATE TABLE market_statistics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Scope
    city VARCHAR(100) NOT NULL,
    locality VARCHAR(255),
    property_type VARCHAR(100),
    
    -- Time period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- Price statistics
    avg_price NUMERIC(15, 2),
    median_price NUMERIC(15, 2),
    min_price NUMERIC(15, 2),
    max_price NUMERIC(15, 2),
    std_price NUMERIC(15, 2),
    avg_price_per_sqft NUMERIC(10, 2),
    
    -- Market dynamics
    listings_count INTEGER,
    transactions_count INTEGER,
    avg_days_on_market NUMERIC(8, 2),
    absorption_rate NUMERIC(5, 2),
    inventory_months NUMERIC(5, 2),
    
    -- Growth metrics
    price_growth_3m NUMERIC(6, 2), -- percentage
    price_growth_6m NUMERIC(6, 2),
    price_growth_12m NUMERIC(6, 2),
    
    -- Derived
    liquidity_index NUMERIC(5, 2),
    volatility NUMERIC(5, 2),
    
    -- Metadata
    sample_size INTEGER,
    confidence_level NUMERIC(3, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_market_stats_city ON market_statistics(city);
CREATE INDEX idx_market_stats_locality ON market_statistics(locality);
CREATE INDEX idx_market_stats_period ON market_statistics(period_start, period_end);

-- ============================================================================
-- MACROECONOMIC INDICATORS
-- ============================================================================

CREATE TABLE macro_indicators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Time period
    indicator_date DATE NOT NULL,
    city VARCHAR(100), -- NULL for national indicators
    
    -- Economic metrics
    interest_rate_benchmark NUMERIC(5, 2),
    home_loan_rate NUMERIC(5, 2),
    cpi NUMERIC(8, 2),
    inflation_rate NUMERIC(5, 2),
    gdp_growth NUMERIC(5, 2),
    construction_cost_index NUMERIC(8, 2),
    
    -- Employment & demand
    unemployment_rate NUMERIC(5, 2),
    job_growth NUMERIC(5, 2),
    
    -- Metadata
    source VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_macro_date ON macro_indicators(indicator_date);
CREATE INDEX idx_macro_city ON macro_indicators(city);

-- ============================================================================
-- BUILDING/PROJECT METADATA (High Value)
-- ============================================================================

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Project details
    project_name VARCHAR(255) NOT NULL,
    developer_name VARCHAR(255),
    location GEOGRAPHY(POINT, 4326),
    city VARCHAR(100),
    locality VARCHAR(255),
    
    -- Project status
    project_phase VARCHAR(50), -- prelaunch, under-construction, ready
    launch_date DATE,
    completion_date DATE,
    
    -- Scale
    total_units INTEGER,
    towers INTEGER,
    
    -- Approvals
    rera_number VARCHAR(100),
    approvals JSONB, -- various approval numbers
    
    -- Metadata
    amenities JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_projects_developer ON projects(developer_name);
CREATE INDEX idx_projects_city ON projects(city);
CREATE INDEX idx_projects_location ON projects USING GIST(location);

-- ============================================================================
-- ZONING & PLANNING (High Value)
-- ============================================================================

CREATE TABLE zoning_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Geographic scope
    zone_name VARCHAR(255),
    city VARCHAR(100),
    boundary GEOGRAPHY(POLYGON, 4326),
    
    -- Zoning details
    land_use_category VARCHAR(100), -- residential, commercial, industrial, mixed
    permissible_far NUMERIC(5, 2),
    height_restriction_meters NUMERIC(8, 2),
    
    -- Planning changes
    rezoning_status VARCHAR(50),
    rezoning_date DATE,
    
    -- Metadata
    source VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_zoning_boundary ON zoning_data USING GIST(boundary);
CREATE INDEX idx_zoning_city ON zoning_data(city);

-- ============================================================================
-- EXTERNAL DATA INTEGRATION (Nice-to-Have)
-- ============================================================================

-- Satellite/imagery derived features
CREATE TABLE satellite_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    location GEOGRAPHY(POINT, 4326),
    observation_date DATE NOT NULL,
    
    -- Derived metrics
    nightlight_intensity NUMERIC(8, 2),
    construction_activity_score NUMERIC(5, 2),
    greenness_index NUMERIC(5, 2),
    change_detection_score NUMERIC(5, 2),
    
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Search & sentiment signals
CREATE TABLE sentiment_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    locality VARCHAR(255),
    city VARCHAR(100),
    signal_date DATE NOT NULL,
    
    -- Sentiment metrics
    search_volume_index NUMERIC(8, 2),
    social_sentiment_score NUMERIC(5, 2), -- -1 to 1
    news_sentiment_score NUMERIC(5, 2),
    
    source VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- RAW DATA STAGING (for ETL)
-- ============================================================================

CREATE TABLE raw_data_staging (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- File metadata
    filename VARCHAR(500) NOT NULL,
    filepath TEXT NOT NULL,
    file_size_bytes BIGINT,
    file_hash VARCHAR(64), -- SHA256
    
    -- Extracted metadata from filename/path
    extracted_city VARCHAR(100),
    extracted_property_type VARCHAR(100),
    extracted_source VARCHAR(100),
    extracted_date DATE,
    
    -- Processing status
    status VARCHAR(50), -- pending, processing, completed, failed
    records_count INTEGER,
    records_processed INTEGER,
    records_failed INTEGER,
    
    -- Raw data (for small files) or reference
    raw_data JSONB, -- store small datasets
    
    -- Processing logs
    processing_log TEXT,
    error_log TEXT,
    
    -- Timestamps
    uploaded_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_raw_staging_status ON raw_data_staging(status);
CREATE INDEX idx_raw_staging_filename ON raw_data_staging(filename);

-- ============================================================================
-- ML MODEL METADATA & TRACKING
-- ============================================================================

CREATE TABLE ml_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Model identification
    model_name VARCHAR(100) NOT NULL, -- price_model, rental_yield_model, demand_model
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50), -- xgboost, gradient_boosting, etc.
    
    -- Training metadata
    trained_at TIMESTAMP NOT NULL,
    training_samples INTEGER,
    training_duration_seconds NUMERIC(10, 2),
    
    -- Performance metrics
    metrics JSONB, -- mae, rmse, r2, mape, etc.
    feature_importance JSONB,
    
    -- Model artifacts
    model_path TEXT,
    scaler_path TEXT,
    
    -- Status
    is_active BOOLEAN DEFAULT FALSE,
    deployed_at TIMESTAMP,
    
    -- Metadata
    hyperparameters JSONB,
    features_used JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ml_models_name ON ml_models(model_name);
CREATE INDEX idx_ml_models_active ON ml_models(is_active);

-- ============================================================================
-- PREDICTION LOGS (for monitoring & retraining)
-- ============================================================================

CREATE TABLE prediction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Request details
    property_id UUID REFERENCES properties(id),
    model_id UUID REFERENCES ml_models(id),
    
    -- Input features
    input_features JSONB NOT NULL,
    
    -- Predictions
    predicted_price NUMERIC(15, 2),
    predicted_rental_yield NUMERIC(5, 2),
    predicted_demand_index NUMERIC(5, 2),
    confidence_score NUMERIC(3, 2),
    
    -- Actual outcome (for model validation)
    actual_price NUMERIC(15, 2),
    actual_rental_yield NUMERIC(5, 2),
    
    -- Metadata
    prediction_timestamp TIMESTAMP DEFAULT NOW(),
    api_endpoint VARCHAR(255),
    user_id VARCHAR(255),
    metadata JSONB
);

CREATE INDEX idx_prediction_logs_property ON prediction_logs(property_id);
CREATE INDEX idx_prediction_logs_timestamp ON prediction_logs(prediction_timestamp);
CREATE INDEX idx_prediction_logs_model ON prediction_logs(model_id);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Active listings with spatial features
CREATE VIEW active_listings_enriched AS
SELECT 
    p.*,
    sf.distance_to_metro,
    sf.distance_to_hospital,
    sf.distance_to_school,
    sf.infrastructure_score,
    sf.connectivity_score,
    ms.avg_price AS locality_avg_price,
    ms.avg_price_per_sqft AS locality_avg_price_per_sqft,
    ms.price_growth_12m AS locality_growth_12m
FROM properties p
LEFT JOIN property_spatial_features sf ON p.id = sf.property_id
LEFT JOIN LATERAL (
    SELECT * FROM market_statistics
    WHERE city = p.city AND locality = p.locality
    ORDER BY period_end DESC LIMIT 1
) ms ON TRUE
WHERE p.listing_type IN ('sale', 'rent');

-- Investment hotspots view
CREATE VIEW investment_hotspots AS
SELECT 
    city,
    locality,
    COUNT(*) as listing_count,
    AVG(price) as avg_price,
    AVG(price_per_sqft) as avg_price_per_sqft,
    AVG(psf.infrastructure_score) as avg_infra_score,
    MAX(ms.price_growth_12m) as growth_12m,
    AVG(ms.absorption_rate) as absorption_rate,
    AVG(ms.liquidity_index) as liquidity_index
FROM properties p
LEFT JOIN property_spatial_features psf ON p.id = psf.property_id
LEFT JOIN market_statistics ms ON p.city = ms.city AND p.locality = ms.locality
WHERE p.listing_type = 'sale'
GROUP BY city, locality
HAVING COUNT(*) >= 10
ORDER BY growth_12m DESC, avg_infra_score DESC;

-- ============================================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- ============================================================================

CREATE MATERIALIZED VIEW mv_city_summary AS
SELECT 
    city,
    COUNT(*) as total_listings,
    COUNT(DISTINCT locality) as localities_count,
    AVG(price) as avg_price,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) as median_price,
    AVG(price_per_sqft) as avg_price_per_sqft,
    MAX(updated_at) as last_updated
FROM properties
WHERE listing_type = 'sale'
GROUP BY city;

CREATE UNIQUE INDEX ON mv_city_summary(city);

-- Refresh command (run periodically):
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_city_summary;

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_properties_updated_at BEFORE UPDATE ON properties
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Calculate derived fields on insert/update
CREATE OR REPLACE FUNCTION calculate_property_derived_fields()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate price per sqft
    IF NEW.price IS NOT NULL AND NEW.area_sqft IS NOT NULL AND NEW.area_sqft > 0 THEN
        NEW.price_per_sqft = NEW.price / NEW.area_sqft;
    END IF;
    
    -- Calculate age from built_year
    IF NEW.built_year IS NOT NULL THEN
        NEW.age_years = EXTRACT(YEAR FROM CURRENT_DATE) - NEW.built_year;
    END IF;
    
    -- Calculate price per room
    IF NEW.price IS NOT NULL AND NEW.bedrooms IS NOT NULL AND NEW.bedrooms > 0 THEN
        NEW.price_per_room = NEW.price / NEW.bedrooms;
    END IF;
    
    -- Categorize size
    IF NEW.bedrooms IS NOT NULL THEN
        NEW.size_category = CASE
            WHEN NEW.bedrooms = 1 THEN '1BHK'
            WHEN NEW.bedrooms = 2 THEN '2BHK'
            WHEN NEW.bedrooms = 3 THEN '3BHK'
            WHEN NEW.bedrooms = 4 THEN '4BHK'
            WHEN NEW.bedrooms >= 5 THEN '5+BHK'
            ELSE 'Studio'
        END;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_derived_fields
BEFORE INSERT OR UPDATE ON properties
FOR EACH ROW EXECUTE FUNCTION calculate_property_derived_fields();

-- Function to calculate spatial features for a property
CREATE OR REPLACE FUNCTION calculate_spatial_features(prop_id UUID)
RETURNS VOID AS $$
DECLARE
    prop_location GEOGRAPHY;
BEGIN
    -- Get property location
    SELECT location INTO prop_location FROM properties WHERE id = prop_id;
    
    IF prop_location IS NULL THEN
        RETURN;
    END IF;
    
    -- Calculate distances and insert/update spatial features
    INSERT INTO property_spatial_features (
        property_id,
        distance_to_metro,
        distance_to_hospital,
        distance_to_school,
        distance_to_mall,
        poi_density_1km,
        poi_density_3km
    )
    SELECT 
        prop_id,
        (SELECT MIN(ST_Distance(prop_location, location)) / 1000 FROM pois WHERE category = 'metro'),
        (SELECT MIN(ST_Distance(prop_location, location)) / 1000 FROM pois WHERE category = 'hospital'),
        (SELECT MIN(ST_Distance(prop_location, location)) / 1000 FROM pois WHERE category = 'school'),
        (SELECT MIN(ST_Distance(prop_location, location)) / 1000 FROM pois WHERE category = 'mall'),
        (SELECT COUNT(*) FROM pois WHERE ST_DWithin(prop_location, location, 1000)),
        (SELECT COUNT(*) FROM pois WHERE ST_DWithin(prop_location, location, 3000))
    ON CONFLICT (property_id) DO UPDATE SET
        distance_to_metro = EXCLUDED.distance_to_metro,
        distance_to_hospital = EXCLUDED.distance_to_hospital,
        distance_to_school = EXCLUDED.distance_to_school,
        distance_to_mall = EXCLUDED.distance_to_mall,
        poi_density_1km = EXCLUDED.poi_density_1km,
        poi_density_3km = EXCLUDED.poi_density_3km,
        computed_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA & CONFIGURATION
-- ============================================================================

-- Add common POI categories
CREATE TABLE poi_categories (
    category VARCHAR(100) PRIMARY KEY,
    display_name VARCHAR(255),
    icon VARCHAR(50),
    priority INTEGER
);

INSERT INTO poi_categories (category, display_name, icon, priority) VALUES
('metro', 'Metro Station', 'train', 1),
('hospital', 'Hospital', 'hospital', 2),
('school', 'School', 'school', 3),
('mall', 'Shopping Mall', 'shopping', 4),
('airport', 'Airport', 'airplane', 5),
('railway', 'Railway Station', 'train', 6),
('bus_stop', 'Bus Stop', 'bus', 7),
('atm', 'ATM', 'money', 8),
('bank', 'Bank', 'bank', 9),
('restaurant', 'Restaurant', 'food', 10),
('park', 'Park', 'tree', 11),
('gym', 'Gym', 'fitness', 12);

-- Property type mappings (for intelligent extraction)
CREATE TABLE property_type_mappings (
    keyword VARCHAR(100) PRIMARY KEY,
    standard_type VARCHAR(100) NOT NULL,
    standard_subtype VARCHAR(100)
);

INSERT INTO property_type_mappings (keyword, standard_type, standard_subtype) VALUES
('flat', 'residential', 'apartment'),
('apartment', 'residential', 'apartment'),
('1bhk', 'residential', '1bhk'),
('2bhk', 'residential', '2bhk'),
('3bhk', 'residential', '3bhk'),
('4bhk', 'residential', '4bhk'),
('5bhk', 'residential', '5bhk'),
('house', 'residential', 'house'),
('villa', 'residential', 'villa'),
('plot', 'residential', 'plot'),
('office', 'commercial', 'office_space'),
('shop', 'commercial', 'shop'),
('showroom', 'commercial', 'showroom'),
('warehouse', 'commercial', 'warehouse'),
('godown', 'commercial', 'warehouse'),
('industrial', 'commercial', 'industrial'),
('agricultural', 'other', 'agricultural_land'),
('farm', 'other', 'farm_house');

-- ============================================================================
-- VECTOR SIMILARITY SEARCH FUNCTIONS (pgvector)
-- ============================================================================

-- Function to find similar properties by description
CREATE OR REPLACE FUNCTION find_similar_properties_by_description(
    property_id UUID,
    similarity_threshold FLOAT DEFAULT 0.7,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    similar_property_id UUID,
    city VARCHAR(100),
    locality VARCHAR(255),
    price NUMERIC(15, 2),
    area_sqft NUMERIC(12, 2),
    bedrooms INTEGER,
    similarity_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.city,
        p.locality,
        p.price,
        p.area_sqft,
        p.bedrooms,
        1 - (p.description_embedding <=> target.description_embedding) as similarity
    FROM properties p, properties target
    WHERE target.id = property_id
    AND p.id != property_id
    AND p.description_embedding IS NOT NULL
    AND target.description_embedding IS NOT NULL
    AND (1 - (p.description_embedding <=> target.description_embedding)) >= similarity_threshold
    ORDER BY similarity DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to find similar properties by combined features
CREATE OR REPLACE FUNCTION find_similar_properties_combined(
    property_id UUID,
    city_filter VARCHAR(100) DEFAULT NULL,
    price_min NUMERIC(15, 2) DEFAULT NULL,
    price_max NUMERIC(15, 2) DEFAULT NULL,
    similarity_threshold FLOAT DEFAULT 0.6,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    similar_property_id UUID,
    city VARCHAR(100),
    locality VARCHAR(255),
    price NUMERIC(15, 2),
    area_sqft NUMERIC(12, 2),
    bedrooms INTEGER,
    similarity_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.city,
        p.locality,
        p.price,
        p.area_sqft,
        p.bedrooms,
        1 - (p.combined_embedding <=> target.combined_embedding) as similarity
    FROM properties p, properties target
    WHERE target.id = property_id
    AND p.id != property_id
    AND p.combined_embedding IS NOT NULL
    AND target.combined_embedding IS NOT NULL
    AND (1 - (p.combined_embedding <=> target.combined_embedding)) >= similarity_threshold
    AND (city_filter IS NULL OR p.city = city_filter)
    AND (price_min IS NULL OR p.price >= price_min)
    AND (price_max IS NULL OR p.price <= price_max)
    ORDER BY similarity DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update embeddings for a property
CREATE OR REPLACE FUNCTION update_property_embeddings(
    property_id UUID,
    description_vec VECTOR(1536) DEFAULT NULL,
    amenities_vec VECTOR(1536) DEFAULT NULL,
    location_vec VECTOR(1536) DEFAULT NULL,
    combined_vec VECTOR(1536) DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE properties 
    SET 
        description_embedding = COALESCE(description_vec, description_embedding),
        amenities_embedding = COALESCE(amenities_vec, amenities_embedding),
        location_embedding = COALESCE(location_vec, location_embedding),
        combined_embedding = COALESCE(combined_vec, combined_embedding)
    WHERE id = property_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function for semantic property search
CREATE OR REPLACE FUNCTION semantic_property_search(
    query_embedding VECTOR(1536),
    city_filter VARCHAR(100) DEFAULT NULL,
    property_type_filter VARCHAR(100) DEFAULT NULL,
    min_price NUMERIC(15, 2) DEFAULT NULL,
    max_price NUMERIC(15, 2) DEFAULT NULL,
    limit_count INTEGER DEFAULT 20
)
RETURNS TABLE (
    property_id UUID,
    city VARCHAR(100),
    locality VARCHAR(255),
    property_type VARCHAR(100),
    price NUMERIC(15, 2),
    area_sqft NUMERIC(12, 2),
    bedrooms INTEGER,
    similarity_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.city,
        p.locality,
        p.property_type,
        p.price,
        p.area_sqft,
        p.bedrooms,
        1 - (p.combined_embedding <=> query_embedding) as similarity
    FROM properties p
    WHERE p.combined_embedding IS NOT NULL
    AND (city_filter IS NULL OR p.city = city_filter)
    AND (property_type_filter IS NULL OR p.property_type = property_type_filter)
    AND (min_price IS NULL OR p.price >= min_price)
    AND (max_price IS NULL OR p.price <= max_price)
    ORDER BY similarity DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON DATABASE postgres IS 'Unified Real Estate Database with PostGIS and Vector support';
