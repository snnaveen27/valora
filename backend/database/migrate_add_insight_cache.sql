-- Migration: Add Insight Cache Tables
-- Run this to add insight cache tables to existing Valora database
-- Created: 2026-01-30

-- ============================================================================
-- INSIGHT CACHE - User-scoped AI insight explanations
-- ============================================================================

CREATE TABLE IF NOT EXISTS insight_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    card_type TEXT NOT NULL,
    
    -- Location (for 2km radius lookup)
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    area_name TEXT,
    
    -- Cache content
    explanation TEXT NOT NULL,
    simulation_data TEXT,  -- JSON
    metadata TEXT,         -- JSON
    
    -- Cache management
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    hit_count INTEGER DEFAULT 0,
    last_hit_at TIMESTAMP,
    
    -- Composite unique constraint: same user can't have duplicate cache for same card+location
    UNIQUE(user_id, card_type, latitude, longitude)
);

-- Indexes for fast cache lookups
CREATE INDEX IF NOT EXISTS idx_insight_cache_user ON insight_cache(user_id, card_type);
CREATE INDEX IF NOT EXISTS idx_insight_cache_location ON insight_cache(user_id, latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_insight_cache_expires ON insight_cache(expires_at);

-- ============================================================================
-- USER CHARGES - Track billing for insight cards
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_charges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    card_type TEXT NOT NULL,
    
    -- Location charged for
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    area_name TEXT,
    
    -- Charge details
    units_charged INTEGER NOT NULL,
    charged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    charge_key TEXT UNIQUE NOT NULL,
    
    -- Deduplication tracking
    valid_until TIMESTAMP NOT NULL
);

-- Indexes for charge lookups and deduplication
CREATE INDEX IF NOT EXISTS idx_user_charges_user ON user_charges(user_id, card_type);
CREATE INDEX IF NOT EXISTS idx_user_charges_location ON user_charges(user_id, latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_user_charges_valid ON user_charges(valid_until);

-- User charge summary view
CREATE VIEW IF NOT EXISTS user_charge_summary AS
SELECT 
    user_id,
    COUNT(*) as total_charges,
    SUM(units_charged) as total_units,
    MIN(charged_at) as first_charge,
    MAX(charged_at) as last_charge,
    COUNT(DISTINCT card_type) as unique_card_types
FROM user_charges
GROUP BY user_id;
