-- Migration: Add AI Orchestration Tables for Layer 5 (Opus Architecture)
-- Run this to add tables for agent sessions, streaming events, and tool executions
-- Date: February 2026

-- ============================================================================
-- AI ORCHESTRATION TABLES (Layer 5: Opus Architecture)
-- ============================================================================

-- Agent Sessions - Track agentic loop executions
CREATE TABLE IF NOT EXISTS agent_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    user_id INTEGER,
    query TEXT NOT NULL,
    intent_classified TEXT,
    confidence REAL,
    
    -- Session state
    status TEXT DEFAULT 'active', -- active, completed, failed, cancelled
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Results
    final_response TEXT,
    tools_used INTEGER DEFAULT 0,
    iterations INTEGER DEFAULT 0,
    
    -- Metadata
    metadata TEXT, -- JSON: {model_used, latency_ms, token_count}
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_sessions_user ON agent_sessions(user_id, started_at);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_status ON agent_sessions(status);

-- Streaming Events - Real-time event log for frontend
CREATE TABLE IF NOT EXISTS streaming_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- agent_start, agent_thinking, agent_action, agent_observation, agent_reflection, agent_final, content, done
    
    -- Event data
    payload TEXT, -- JSON: event-specific data
    sequence INTEGER, -- Order within session
    
    -- Timing
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES agent_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_streaming_events_session ON streaming_events(session_id, sequence);
CREATE INDEX IF NOT EXISTS idx_streaming_events_type ON streaming_events(event_type);

-- Tool Executions - Log all tool calls for debugging/optimization
CREATE TABLE IF NOT EXISTS tool_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    category TEXT,
    
    -- Input/Output
    parameters TEXT, -- JSON
    result TEXT, -- JSON (truncated if large)
    error TEXT,
    
    -- Performance
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    
    -- Status
    success BOOLEAN DEFAULT 0,
    cached BOOLEAN DEFAULT 0,
    
    FOREIGN KEY (session_id) REFERENCES agent_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tool_executions_session ON tool_executions(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_tool ON tool_executions(tool_name, started_at);
CREATE INDEX IF NOT EXISTS idx_tool_executions_category ON tool_executions(category);

-- Intent Patterns - Learned patterns for intent classification improvement
CREATE TABLE IF NOT EXISTS intent_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL, -- Regex or keyword pattern
    intent_type TEXT NOT NULL,
    confidence_boost REAL DEFAULT 0.1,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP
);

-- Spatial Index - R-tree for fast spatial queries (using regular index on lat/lng)
CREATE INDEX IF NOT EXISTS idx_properties_lat_lng ON properties(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_properties_location ON properties(area_name, locality);

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Verify tables created
SELECT 'Tables created:' as status;
SELECT name FROM sqlite_master WHERE type='table' AND name IN ('agent_sessions', 'streaming_events', 'tool_executions', 'intent_patterns');
