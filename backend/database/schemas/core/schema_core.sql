-- ============================================================================
-- Core Database Schema (No PostGIS, No pgvector)
-- Contains core entities: properties, transactions, market stats, staging
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- for fuzzy search

-- Properties (core attributes only)
CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identification
    listing_id VARCHAR(255) UNIQUE,
    source VARCHAR(100) NOT NULL,
    source_url TEXT,

    -- Location (structured only)
    city VARCHAR(100),
    locality VARCHAR(255),
    sub_locality VARCHAR(255),
    address TEXT,
    pincode VARCHAR(20),
    ward VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,

    -- Property core
    property_type VARCHAR(100),
    property_subtype VARCHAR(100),
    listing_type VARCHAR(50),

    -- Physical attributes
    area_sqft NUMERIC(12,2),
    bedrooms INTEGER,
    bathrooms INTEGER,
    balconies INTEGER,
    floor INTEGER,
    total_floors INTEGER,
    built_year INTEGER,
    age_years INTEGER,
    parking_spaces INTEGER,
    furnishing VARCHAR(50),

    -- Pricing
    price NUMERIC(15,2),
    price_per_sqft NUMERIC(10,2),
    maintenance_charges NUMERIC(10,2),
    security_deposit NUMERIC(15,2),

    -- Listing metadata
    listing_date TIMESTAMP,
    updated_date TIMESTAMP,
    possession_status VARCHAR(50),
    seller_type VARCHAR(50),

    -- Flexible data
    amenities JSONB,
    photos JSONB,
    metadata JSONB,

    -- Derived/computed
    size_category VARCHAR(50),
    price_per_room NUMERIC(12,2),

    -- Data quality and ETL
    raw_filename VARCHAR(500),
    extracted_metadata JSONB,
    data_quality_score NUMERIC(3,2),
    missing_fields JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_price CHECK (price >= 0),
    CONSTRAINT valid_area CHECK (area_sqft > 0 OR area_sqft IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_properties_city ON properties(city);
CREATE INDEX IF NOT EXISTS idx_properties_locality ON properties(locality);
CREATE INDEX IF NOT EXISTS idx_properties_type ON properties(property_type);
CREATE INDEX IF NOT EXISTS idx_properties_price ON properties(price);
CREATE INDEX IF NOT EXISTS idx_properties_listing_date ON properties(listing_date);
CREATE INDEX IF NOT EXISTS idx_properties_source ON properties(source);
CREATE INDEX IF NOT EXISTS idx_properties_metadata ON properties USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_properties_latitude ON properties(latitude);
CREATE INDEX IF NOT EXISTS idx_properties_longitude ON properties(longitude);

-- Raw data staging (ETL tracking)
CREATE TABLE IF NOT EXISTS raw_data_staging (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(500) NOT NULL,
    filepath TEXT,
    file_size_bytes BIGINT,
    file_hash VARCHAR(128) UNIQUE,
    extracted_city VARCHAR(100),
    extracted_property_type VARCHAR(100),
    extracted_source VARCHAR(100),
    extracted_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'uploaded',
    records_count INTEGER,
    records_processed INTEGER,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    error_log TEXT
);
CREATE INDEX IF NOT EXISTS idx_staging_status ON raw_data_staging(status);
CREATE INDEX IF NOT EXISTS idx_staging_uploaded_at ON raw_data_staging(uploaded_at);

-- Trigger: update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_properties_updated_at ON properties;
CREATE TRIGGER update_properties_updated_at BEFORE UPDATE ON properties
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Derived field calculations
CREATE OR REPLACE FUNCTION calculate_property_derived_fields()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.price IS NOT NULL AND NEW.area_sqft IS NOT NULL AND NEW.area_sqft > 0 THEN
    NEW.price_per_sqft = NEW.price / NEW.area_sqft;
  END IF;
  IF NEW.built_year IS NOT NULL THEN
    NEW.age_years = EXTRACT(YEAR FROM CURRENT_DATE) - NEW.built_year;
  END IF;
  IF NEW.price IS NOT NULL AND NEW.bedrooms IS NOT NULL AND NEW.bedrooms > 0 THEN
    NEW.price_per_room = NEW.price / NEW.bedrooms;
  END IF;
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

DROP TRIGGER IF EXISTS trigger_calculate_derived_fields ON properties;
CREATE TRIGGER trigger_calculate_derived_fields
BEFORE INSERT OR UPDATE ON properties
FOR EACH ROW EXECUTE FUNCTION calculate_property_derived_fields();

-- Market statistics (aggregates)
CREATE TABLE IF NOT EXISTS market_statistics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city VARCHAR(100) NOT NULL,
    locality VARCHAR(255),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    avg_price NUMERIC(15,2),
    median_price NUMERIC(15,2),
    avg_price_per_sqft NUMERIC(10,2),
    listings_count INTEGER,
    avg_days_on_market NUMERIC(10,2),
    absorption_rate NUMERIC(6,3),
    price_growth_3m NUMERIC(6,3),
    price_growth_6m NUMERIC(6,3),
    price_growth_12m NUMERIC(6,3),
    sample_size INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_market_city ON market_statistics(city);
CREATE INDEX IF NOT EXISTS idx_market_city_loc ON market_statistics(city, locality);
CREATE INDEX IF NOT EXISTS idx_market_period ON market_statistics(period_end);
