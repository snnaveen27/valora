-- ============================================================================
-- Spatial Database Schema (PostGIS only)
-- Stores POIs and precomputed spatial features for properties
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Property locations (point geometry for distance queries)
CREATE TABLE IF NOT EXISTS property_locations (
    property_id UUID PRIMARY KEY,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_property_locations_loc ON property_locations USING GIST(location);

-- POIs master
CREATE TABLE IF NOT EXISTS pois (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL, -- metro, hospital, school, mall, airport, railway, etc.
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pois_category ON pois(category);
CREATE INDEX IF NOT EXISTS idx_pois_location ON pois USING GIST(location);

-- Extend POIs with source information for de-duplication
ALTER TABLE IF EXISTS pois ADD COLUMN IF NOT EXISTS source VARCHAR(50);
ALTER TABLE IF EXISTS pois ADD COLUMN IF NOT EXISTS source_id VARCHAR(100);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pois_source_id ON pois(source_id) WHERE source_id IS NOT NULL;

-- Precomputed spatial features per property
CREATE TABLE IF NOT EXISTS property_spatial_features (
    property_id UUID PRIMARY KEY,
    distance_to_metro NUMERIC(10,2),
    distance_to_hospital NUMERIC(10,2),
    distance_to_school NUMERIC(10,2),
    distance_to_mall NUMERIC(10,2),
    distance_to_airport NUMERIC(10,2),
    distance_to_railway NUMERIC(10,2),
    poi_density_1km NUMERIC(10,2),
    poi_density_3km NUMERIC(10,2),
    infrastructure_score NUMERIC(5,2),
    connectivity_score NUMERIC(5,2),
    lifestyle_score NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Helper: nearest POI distance by category
CREATE OR REPLACE FUNCTION nearest_poi_distance(p GEOGRAPHY, poi_cat VARCHAR)
RETURNS NUMERIC AS $$
DECLARE
    d NUMERIC;
BEGIN
    SELECT MIN(ST_Distance(p, location))
    INTO d
    FROM pois
    WHERE category = poi_cat;

    IF d IS NULL THEN
        RETURN NULL;
    END IF;
    -- return in meters
    RETURN d;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Upsert spatial features given property id and coordinates
CREATE OR REPLACE FUNCTION upsert_property_spatial_features(
    p_property_id UUID,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION
) RETURNS BOOLEAN AS $$
DECLARE
    p GEOGRAPHY := ST_SetSRID(ST_MakePoint(lon, lat), 4326)::GEOGRAPHY;
    d_metro NUMERIC;
    d_hospital NUMERIC;
    d_school NUMERIC;
    d_mall NUMERIC;
    d_airport NUMERIC;
    d_railway NUMERIC;
    density1 NUMERIC;
    density3 NUMERIC;
    infra NUMERIC;
    conn NUMERIC;
    life NUMERIC;
BEGIN
    -- upsert property location
    INSERT INTO property_locations(property_id, location, created_at, updated_at)
    VALUES (p_property_id, p, NOW(), NOW())
    ON CONFLICT (property_id) DO UPDATE SET location = EXCLUDED.location, updated_at = NOW();

    -- distances (meters)
    d_metro := nearest_poi_distance(p, 'metro');
    d_hospital := nearest_poi_distance(p, 'hospital');
    d_school := nearest_poi_distance(p, 'school');
    d_mall := nearest_poi_distance(p, 'mall');
    d_airport := nearest_poi_distance(p, 'airport');
    d_railway := nearest_poi_distance(p, 'railway');

    -- densities
    SELECT COUNT(*) INTO density1 FROM pois WHERE ST_DWithin(location, p, 1000);
    SELECT COUNT(*) INTO density3 FROM pois WHERE ST_DWithin(location, p, 3000);

    -- simple scores
    infra := 0;
    IF d_metro IS NOT NULL THEN infra := infra + LEAST(100, 10000 / NULLIF(d_metro,0)); END IF;
    IF d_hospital IS NOT NULL THEN infra := infra + LEAST(100, 10000 / NULLIF(d_hospital,0)); END IF;
    IF d_school IS NOT NULL THEN infra := infra + LEAST(100, 10000 / NULLIF(d_school,0)); END IF;
    infra := LEAST(100, infra / 3.0);

    conn := 0;
    IF d_metro IS NOT NULL THEN conn := conn + LEAST(100, 10000 / NULLIF(d_metro,0)); END IF;
    IF d_airport IS NOT NULL THEN conn := conn + LEAST(100, 15000 / NULLIF(d_airport,0)); END IF;
    IF d_railway IS NOT NULL THEN conn := conn + LEAST(100, 12000 / NULLIF(d_railway,0)); END IF;
    conn := LEAST(100, conn / 3.0);

    life := 0;
    IF d_mall IS NOT NULL THEN life := life + LEAST(100, 8000 / NULLIF(d_mall,0)); END IF;
    life := LEAST(100, life + LEAST(100, density3 * 2));
    life := LEAST(100, life);

    INSERT INTO property_spatial_features (
        property_id, distance_to_metro, distance_to_hospital, distance_to_school,
        distance_to_mall, distance_to_airport, distance_to_railway,
        poi_density_1km, poi_density_3km, infrastructure_score, connectivity_score, lifestyle_score,
        created_at, updated_at
    ) VALUES (
        p_property_id, d_metro, d_hospital, d_school, d_mall, d_airport, d_railway,
        density1, density3, infra, conn, life, NOW(), NOW()
    )
    ON CONFLICT (property_id) DO UPDATE SET
        distance_to_metro = EXCLUDED.distance_to_metro,
        distance_to_hospital = EXCLUDED.distance_to_hospital,
        distance_to_school = EXCLUDED.distance_to_school,
        distance_to_mall = EXCLUDED.distance_to_mall,
        distance_to_airport = EXCLUDED.distance_to_airport,
        distance_to_railway = EXCLUDED.distance_to_railway,
        poi_density_1km = EXCLUDED.poi_density_1km,
        poi_density_3km = EXCLUDED.poi_density_3km,
        infrastructure_score = EXCLUDED.infrastructure_score,
        connectivity_score = EXCLUDED.connectivity_score,
        lifestyle_score = EXCLUDED.lifestyle_score,
        updated_at = NOW();

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Mappls caching tables (geocode, reverse, nearby POIs)
CREATE TABLE IF NOT EXISTS mappls_geocode_cache (
    address_hash VARCHAR(64) PRIMARY KEY,
    address TEXT,
    result JSONB,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mappls_reverse_cache (
    key_hash VARCHAR(64) PRIMARY KEY,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    result JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mappls_poi_cache (
    tile_lat DOUBLE PRECISION,
    tile_lon DOUBLE PRECISION,
    radius_m INTEGER,
    category VARCHAR(100),
    keywords TEXT,
    keywords_hash VARCHAR(64),
    result JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    PRIMARY KEY (tile_lat, tile_lon, radius_m, category, keywords_hash)
);
CREATE INDEX IF NOT EXISTS idx_mappls_poi_cache_expires ON mappls_poi_cache(expires_at);
