-- City Intelligence & Prediction Feedback Schema
-- Production-ready database tables for Valora City Intelligence Engine

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- =====================================================
-- LOCALITY STATE TABLES
-- =====================================================

-- Locality master table
CREATE TABLE IF NOT EXISTS localities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL DEFAULT 'bangalore',
    ward_number VARCHAR(50),
    zone VARCHAR(100),
    pincode VARCHAR(10),
    boundary GEOMETRY(POLYGON, 4326),
    center_point GEOMETRY(POINT, 4326),
    area_sqkm DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, city)
);

-- Locality state snapshots (current market state)
CREATE TABLE IF NOT EXISTS locality_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    locality_id UUID REFERENCES localities(id) ON DELETE CASCADE,
    
    -- Market Metrics
    avg_price_sqft DECIMAL(12, 2),
    median_price DECIMAL(15, 2),
    price_change_1m DECIMAL(6, 2),
    price_change_3m DECIMAL(6, 2),
    price_change_6m DECIMAL(6, 2),
    price_change_12m DECIMAL(6, 2),
    
    -- Supply/Demand
    active_listings INTEGER DEFAULT 0,
    absorption_rate DECIMAL(6, 2),
    days_on_market_avg DECIMAL(8, 1),
    inventory_months DECIMAL(5, 1),
    
    -- Classifications
    growth_phase VARCHAR(50) CHECK (growth_phase IN ('emerging', 'accelerating', 'mature', 'saturated')),
    investor_type VARCHAR(50),
    
    -- Risk Indices (0-1 scale)
    risk_index_flood DECIMAL(4, 3),
    risk_index_infra DECIMAL(4, 3),
    risk_index_liquidity DECIMAL(4, 3),
    risk_index_regulatory DECIMAL(4, 3),
    risk_index_market DECIMAL(4, 3),
    risk_index_overall DECIMAL(4, 3),
    
    -- Forecasts
    price_forecast_6m DECIMAL(15, 2),
    price_forecast_1y DECIMAL(15, 2),
    price_forecast_3y DECIMAL(15, 2),
    forecast_confidence DECIMAL(4, 3),
    
    -- Metadata
    computed_at TIMESTAMP DEFAULT NOW(),
    data_freshness_score DECIMAL(4, 3),
    
    UNIQUE(locality_id)
);

-- Locality state time series (historical snapshots)
CREATE TABLE IF NOT EXISTS locality_state_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    locality_id UUID REFERENCES localities(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    avg_price_sqft DECIMAL(12, 2),
    growth_phase VARCHAR(50),
    risk_index_overall DECIMAL(4, 3),
    price_forecast_1y DECIMAL(15, 2),
    active_listings INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(locality_id, snapshot_date)
);

-- =====================================================
-- PREDICTION FEEDBACK TABLES
-- =====================================================

-- Prediction records
CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id VARCHAR(50) UNIQUE NOT NULL,
    prediction_type VARCHAR(50) NOT NULL CHECK (prediction_type IN ('price', 'rental_yield', 'demand', 'growth', 'risk')),
    
    -- Location
    property_id VARCHAR(100),
    locality_id UUID REFERENCES localities(id),
    locality_name VARCHAR(255) NOT NULL,
    city VARCHAR(100) DEFAULT 'bangalore',
    
    -- Prediction details
    predicted_value DECIMAL(15, 2) NOT NULL,
    prediction_date TIMESTAMP NOT NULL DEFAULT NOW(),
    target_date TIMESTAMP NOT NULL,
    confidence DECIMAL(4, 3) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    features_used JSONB,
    
    -- Feedback
    actual_value DECIMAL(15, 2),
    feedback_status VARCHAR(50) DEFAULT 'pending' CHECK (feedback_status IN ('pending', 'verified', 'disputed', 'expired')),
    error_percentage DECIMAL(8, 2),
    verified_date TIMESTAMP,
    feedback_source VARCHAR(50),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Model performance metrics (aggregated)
CREATE TABLE IF NOT EXISTS model_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_version VARCHAR(50) NOT NULL,
    prediction_type VARCHAR(50) NOT NULL,
    locality_id UUID REFERENCES localities(id),
    
    -- Metrics
    total_predictions INTEGER DEFAULT 0,
    verified_predictions INTEGER DEFAULT 0,
    mean_absolute_error DECIMAL(15, 2),
    mean_percentage_error DECIMAL(8, 2),
    median_error DECIMAL(8, 2),
    accuracy_5pct DECIMAL(4, 3),
    accuracy_10pct DECIMAL(4, 3),
    accuracy_20pct DECIMAL(4, 3),
    bias DECIMAL(8, 2),
    
    -- Time window
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    computed_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(model_version, prediction_type, locality_id, period_start, period_end)
);

-- Calibration suggestions
CREATE TABLE IF NOT EXISTS calibration_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    suggestion_id VARCHAR(50) UNIQUE NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    prediction_type VARCHAR(50) NOT NULL,
    
    issue_type VARCHAR(50) NOT NULL CHECK (issue_type IN ('bias', 'high_variance', 'drift', 'locality_specific')),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT NOT NULL,
    suggested_action TEXT NOT NULL,
    affected_localities TEXT[], -- Array of locality names
    sample_size INTEGER NOT NULL,
    
    status VARCHAR(50) DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'resolved', 'dismissed')),
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(255),
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- SCENARIO SIMULATION TABLES
-- =====================================================

-- Infrastructure events
CREATE TABLE IF NOT EXISTS infrastructure_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('metro', 'highway', 'tech_park', 'hospital', 'mall', 'airport', 'railway')),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    location GEOMETRY(POINT, 4326),
    impact_radius_km DECIMAL(6, 2),
    
    -- Timeline
    announcement_date DATE,
    construction_start DATE,
    expected_completion DATE,
    actual_completion DATE,
    status VARCHAR(50) DEFAULT 'announced' CHECK (status IN ('announced', 'approved', 'construction', 'completed', 'cancelled')),
    
    -- Impact factors
    base_price_impact_pct DECIMAL(6, 2),
    rental_impact_pct DECIMAL(6, 2),
    demand_impact_pct DECIMAL(6, 2),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Scenario simulations log
CREATE TABLE IF NOT EXISTS scenario_simulations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255),
    locality_id UUID REFERENCES localities(id),
    infrastructure_event_id UUID REFERENCES infrastructure_events(id),
    
    -- Simulation parameters
    distance_km DECIMAL(6, 2),
    timeline_months INTEGER,
    custom_params JSONB,
    
    -- Results
    projected_price_impact_pct DECIMAL(6, 2),
    projected_rental_impact_pct DECIMAL(6, 2),
    projected_demand_impact_pct DECIMAL(6, 2),
    confidence DECIMAL(4, 3),
    timeline_breakdown JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Localities indexes
CREATE INDEX IF NOT EXISTS idx_localities_city ON localities(city);
CREATE INDEX IF NOT EXISTS idx_localities_name ON localities(name);
CREATE INDEX IF NOT EXISTS idx_localities_boundary ON localities USING GIST(boundary);

-- Locality state indexes
CREATE INDEX IF NOT EXISTS idx_locality_state_locality ON locality_state(locality_id);
CREATE INDEX IF NOT EXISTS idx_locality_state_growth_phase ON locality_state(growth_phase);

-- Predictions indexes
CREATE INDEX IF NOT EXISTS idx_predictions_type ON predictions(prediction_type);
CREATE INDEX IF NOT EXISTS idx_predictions_locality ON predictions(locality_name, city);
CREATE INDEX IF NOT EXISTS idx_predictions_status ON predictions(feedback_status);
CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date);
CREATE INDEX IF NOT EXISTS idx_predictions_model ON predictions(model_version);
CREATE INDEX IF NOT EXISTS idx_predictions_verified ON predictions(verified_date) WHERE verified_date IS NOT NULL;

-- Model performance indexes
CREATE INDEX IF NOT EXISTS idx_model_perf_version ON model_performance(model_version);
CREATE INDEX IF NOT EXISTS idx_model_perf_type ON model_performance(prediction_type);

-- Calibration indexes
CREATE INDEX IF NOT EXISTS idx_calibration_status ON calibration_suggestions(status);
CREATE INDEX IF NOT EXISTS idx_calibration_severity ON calibration_suggestions(severity);

-- Infrastructure events indexes
CREATE INDEX IF NOT EXISTS idx_infra_events_type ON infrastructure_events(event_type);
CREATE INDEX IF NOT EXISTS idx_infra_events_status ON infrastructure_events(status);
CREATE INDEX IF NOT EXISTS idx_infra_events_location ON infrastructure_events USING GIST(location);

-- =====================================================
-- TRIGGERS FOR UPDATED_AT
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_localities_updated_at
    BEFORE UPDATE ON localities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_predictions_updated_at
    BEFORE UPDATE ON predictions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_infra_events_updated_at
    BEFORE UPDATE ON infrastructure_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SEED DATA: BANGALORE LOCALITIES
-- =====================================================

INSERT INTO localities (name, city, zone, pincode) VALUES
    ('Whitefield', 'bangalore', 'East', '560066'),
    ('Koramangala', 'bangalore', 'South', '560034'),
    ('HSR Layout', 'bangalore', 'South', '560102'),
    ('Sarjapur', 'bangalore', 'South-East', '562125'),
    ('Electronic City', 'bangalore', 'South', '560100'),
    ('Indiranagar', 'bangalore', 'East', '560038'),
    ('Marathahalli', 'bangalore', 'East', '560037'),
    ('Bellandur', 'bangalore', 'South-East', '560103'),
    ('Jayanagar', 'bangalore', 'South', '560041'),
    ('Banashankari', 'bangalore', 'South', '560070'),
    ('Rajajinagar', 'bangalore', 'West', '560010'),
    ('Malleshwaram', 'bangalore', 'North-West', '560003'),
    ('Yelahanka', 'bangalore', 'North', '560064'),
    ('Hebbal', 'bangalore', 'North', '560024'),
    ('Bannerghatta Road', 'bangalore', 'South', '560076')
ON CONFLICT (name, city) DO NOTHING;

-- Insert initial locality states
INSERT INTO locality_state (locality_id, avg_price_sqft, median_price, price_change_12m, growth_phase, risk_index_overall, active_listings)
SELECT 
    id,
    CASE name
        WHEN 'Whitefield' THEN 7800
        WHEN 'Koramangala' THEN 12500
        WHEN 'HSR Layout' THEN 9200
        WHEN 'Sarjapur' THEN 6500
        WHEN 'Electronic City' THEN 5800
        WHEN 'Indiranagar' THEN 15000
        WHEN 'Marathahalli' THEN 7200
        WHEN 'Bellandur' THEN 8500
        WHEN 'Jayanagar' THEN 11000
        WHEN 'Banashankari' THEN 8000
        WHEN 'Rajajinagar' THEN 9500
        WHEN 'Malleshwaram' THEN 10500
        WHEN 'Yelahanka' THEN 5500
        WHEN 'Hebbal' THEN 7000
        WHEN 'Bannerghatta Road' THEN 6200
        ELSE 7000
    END,
    CASE name
        WHEN 'Koramangala' THEN 15000000
        WHEN 'Indiranagar' THEN 18000000
        WHEN 'HSR Layout' THEN 11000000
        ELSE 8500000
    END,
    CASE name
        WHEN 'Sarjapur' THEN 18.5
        WHEN 'Whitefield' THEN 14.2
        WHEN 'Electronic City' THEN 12.8
        WHEN 'Koramangala' THEN 8.5
        ELSE 10.0
    END,
    CASE name
        WHEN 'Sarjapur' THEN 'emerging'
        WHEN 'Whitefield' THEN 'accelerating'
        WHEN 'Electronic City' THEN 'accelerating'
        WHEN 'Koramangala' THEN 'mature'
        WHEN 'Indiranagar' THEN 'mature'
        WHEN 'Jayanagar' THEN 'mature'
        ELSE 'accelerating'
    END,
    CASE name
        WHEN 'Sarjapur' THEN 0.35
        WHEN 'Koramangala' THEN 0.18
        WHEN 'Indiranagar' THEN 0.15
        ELSE 0.25
    END,
    FLOOR(RANDOM() * 200 + 100)::INTEGER
FROM localities
WHERE city = 'bangalore'
ON CONFLICT (locality_id) DO NOTHING;

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================

-- Locality overview view
CREATE OR REPLACE VIEW v_locality_overview AS
SELECT 
    l.id,
    l.name,
    l.city,
    l.zone,
    ls.avg_price_sqft,
    ls.price_change_12m,
    ls.growth_phase,
    ls.risk_index_overall,
    ls.active_listings,
    ls.computed_at
FROM localities l
LEFT JOIN locality_state ls ON l.id = ls.locality_id;

-- Model accuracy view
CREATE OR REPLACE VIEW v_model_accuracy AS
SELECT 
    model_version,
    prediction_type,
    COUNT(*) as total_predictions,
    COUNT(*) FILTER (WHERE feedback_status = 'verified') as verified_count,
    AVG(ABS(error_percentage)) FILTER (WHERE feedback_status = 'verified') as mean_abs_error,
    AVG(error_percentage) FILTER (WHERE feedback_status = 'verified') as bias,
    COUNT(*) FILTER (WHERE feedback_status = 'verified' AND ABS(error_percentage) <= 10) * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE feedback_status = 'verified'), 0) as accuracy_10pct
FROM predictions
GROUP BY model_version, prediction_type;

-- Recent predictions view
CREATE OR REPLACE VIEW v_recent_predictions AS
SELECT 
    prediction_id,
    prediction_type,
    locality_name,
    city,
    predicted_value,
    actual_value,
    error_percentage,
    feedback_status,
    confidence,
    model_version,
    prediction_date,
    verified_date
FROM predictions
ORDER BY prediction_date DESC
LIMIT 100;

COMMENT ON TABLE localities IS 'Master table of all localities/wards';
COMMENT ON TABLE locality_state IS 'Current market state snapshot for each locality';
COMMENT ON TABLE predictions IS 'Individual prediction records for feedback tracking';
COMMENT ON TABLE model_performance IS 'Aggregated model performance metrics';
COMMENT ON TABLE calibration_suggestions IS 'AI-generated model calibration suggestions';
