-- Database Performance Optimization for Valora - SQLite + SpatialLite
-- Run these SQL commands to optimize database performance

-- ============================================================================
-- 1. PRAGMA SETTINGS (Run at connection start)
-- ============================================================================

-- WAL Mode: Write-Ahead Logging for concurrent read/write (2-3x write performance)
PRAGMA journal_mode=WAL;

-- Memory Mapping: Let OS handle caching (adjust based on system RAM)
PRAGMA mmap_size=30000000000;

-- Page Size: Optimal for modern SSDs
PRAGMA page_size=4096;

-- Cache Size: 64MB per connection (256MB total for 4 connections)
PRAGMA cache_size=-64000;

-- Synchronous Mode: Balance safety/speed
PRAGMA synchronous=NORMAL;

-- Temp Store: Use memory for temporary tables
PRAGMA temp_store=memory;

-- ============================================================================
-- 2. AI ORCHESTRATION INDEXES (Layer 5 - Opus)
-- ============================================================================

-- Agent session lookups by user and time
CREATE INDEX IF NOT EXISTS idx_agent_sessions_user ON agent_sessions(user_id, started_at);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_status ON agent_sessions(status);

-- Streaming events ordered by session and sequence
CREATE INDEX IF NOT EXISTS idx_streaming_events_session ON streaming_events(session_id, sequence);
CREATE INDEX IF NOT EXISTS idx_streaming_events_type ON streaming_events(event_type);

-- Tool execution analytics
CREATE INDEX IF NOT EXISTS idx_tool_executions_session ON tool_executions(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_tool ON tool_executions(tool_name, started_at);
CREATE INDEX IF NOT EXISTS idx_tool_executions_category ON tool_executions(category);

-- Intent pattern lookups
CREATE INDEX IF NOT EXISTS idx_intent_patterns_type ON intent_patterns(intent_type, confidence_boost);

-- Insight cache lookups
CREATE INDEX IF NOT EXISTS idx_insight_cache_user ON insight_cache(user_id, card_type);
CREATE INDEX IF NOT EXISTS idx_insight_cache_location ON insight_cache(user_id, latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_insight_cache_expires ON insight_cache(expires_at);

-- ============================================================================
-- 3. PROPERTIES TABLE INDEXES (Updated for schema_simple.sql)
-- ============================================================================

-- Primary lookups by locality/area
CREATE INDEX IF NOT EXISTS idx_properties_locality ON properties(locality);
CREATE INDEX IF NOT EXISTS idx_properties_area ON properties(area_name);

-- Combined location index for search
CREATE INDEX IF NOT EXISTS idx_properties_location ON properties(area_name, locality);

-- Spatial queries (coordinates) - CRITICAL for 3D map
CREATE INDEX IF NOT EXISTS idx_properties_lat_lng ON properties(latitude, longitude);

-- Price-based queries
CREATE INDEX IF NOT EXISTS idx_properties_price ON properties(price) WHERE price IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_properties_price_per_sqft ON properties(price_per_sqft);

-- BHK/Bedroom filtering (common search criteria)
CREATE INDEX IF NOT EXISTS idx_properties_bhk ON properties(bhk);
CREATE INDEX IF NOT EXISTS idx_properties_bedrooms ON properties(bedrooms);

-- Property type filtering
CREATE INDEX IF NOT EXISTS idx_properties_type ON properties(property_type, listing_type);

-- Status filtering (active properties)
CREATE INDEX IF NOT EXISTS idx_properties_status ON properties(status) WHERE status = 'active';

-- Combined index for common search pattern
CREATE INDEX IF NOT EXISTS idx_properties_search ON 
    properties(property_type, listing_type, locality, price, bedrooms) 
    WHERE status = 'active';

-- ============================================================================
-- 4. BUILDINGS TABLE INDEXES
-- ============================================================================

-- Primary lookups
CREATE INDEX IF NOT EXISTS idx_buildings_locality ON buildings(locality);

-- Spatial queries (coordinates)
CREATE INDEX IF NOT EXISTS idx_buildings_coords ON buildings(latitude, longitude);

-- Height-based queries (for 3D analysis)
CREATE INDEX IF NOT EXISTS idx_buildings_height ON buildings(height);

-- Type-based filtering
CREATE INDEX IF NOT EXISTS idx_buildings_type ON buildings(building_type);

-- ============================================================================
-- 5. ANALYZE (Update query planner statistics)
-- ============================================================================

ANALYZE;

-- ============================================================================
-- MAINTENANCE NOTES
-- ============================================================================
-- Run VACUUM monthly during low traffic: sqlite3 valora.db "VACUUM;"
-- Run ANALYZE weekly: sqlite3 valora.db "ANALYZE;"
-- Checkpoint WAL: PRAGMA wal_checkpoint(TRUNCATE);
-- ============================================================================

