-- ============================================================================
-- Data Layer Schema - Valora Platform
-- Tracks all data sources: streaming, uploads, scraped, folder-based
-- ============================================================================

-- Data sources registry
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source identification
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'streaming', 'upload', 'scraped', 'folder', 'api'
    category VARCHAR(100), -- 'properties', 'transactions', 'pois', 'gis', 'market'
    
    -- Connection details (JSONB for flexibility)
    connection_config JSONB, -- API endpoints, folder paths, stream URLs, etc.
    
    -- Status
    status VARCHAR(50) DEFAULT 'active', -- active, paused, error, disabled
    health_status VARCHAR(50) DEFAULT 'unknown', -- healthy, degraded, unhealthy, unknown
    last_health_check TIMESTAMP,
    
    -- Sync settings
    sync_frequency VARCHAR(50), -- realtime, hourly, daily, weekly, manual
    last_sync_at TIMESTAMP,
    next_sync_at TIMESTAMP,
    
    -- Statistics
    total_records BIGINT DEFAULT 0,
    records_today BIGINT DEFAULT 0,
    records_this_week BIGINT DEFAULT 0,
    records_this_month BIGINT DEFAULT 0,
    
    -- Quality metrics
    avg_quality_score NUMERIC(3, 2) DEFAULT 0,
    error_rate NUMERIC(5, 4) DEFAULT 0,
    
    -- City association
    city_id VARCHAR(100),
    
    -- Metadata
    description TEXT,
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by UUID
);

CREATE INDEX idx_data_sources_type ON data_sources(source_type);
CREATE INDEX idx_data_sources_status ON data_sources(status);
CREATE INDEX idx_data_sources_city ON data_sources(city_id);

-- Ingestion jobs tracking
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Job identification
    source_id UUID REFERENCES data_sources(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL, -- 'full_sync', 'incremental', 'upload', 'stream_batch'
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Progress
    total_records INTEGER DEFAULT 0,
    processed_records INTEGER DEFAULT 0,
    success_records INTEGER DEFAULT 0,
    failed_records INTEGER DEFAULT 0,
    skipped_records INTEGER DEFAULT 0,
    
    -- Quality metrics
    avg_quality_score NUMERIC(3, 2),
    validation_errors JSONB DEFAULT '[]',
    
    -- Error tracking
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER DEFAULT 0,
    
    -- Metadata
    triggered_by VARCHAR(50), -- 'scheduler', 'manual', 'api', 'webhook'
    parameters JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ingestion_jobs_source ON ingestion_jobs(source_id);
CREATE INDEX idx_ingestion_jobs_status ON ingestion_jobs(status);
CREATE INDEX idx_ingestion_jobs_created ON ingestion_jobs(created_at DESC);

-- File uploads tracking
CREATE TABLE IF NOT EXISTS file_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- File information
    original_filename VARCHAR(500) NOT NULL,
    stored_filename VARCHAR(500) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    file_type VARCHAR(100), -- csv, json, xlsx, geojson, shapefile, etc.
    mime_type VARCHAR(100),
    
    -- Processing status
    status VARCHAR(50) DEFAULT 'uploaded', -- uploaded, processing, completed, failed
    processed_at TIMESTAMP,
    
    -- Content metadata
    category VARCHAR(100), -- properties, transactions, pois, boundaries
    city_id VARCHAR(100),
    record_count INTEGER,
    
    -- Validation
    validation_status VARCHAR(50), -- pending, valid, invalid, partial
    validation_errors JSONB DEFAULT '[]',
    column_mapping JSONB, -- maps file columns to DB fields
    
    -- Association
    source_id UUID REFERENCES data_sources(id),
    job_id UUID REFERENCES ingestion_jobs(id),
    
    -- User tracking
    uploaded_by UUID,
    approved_by UUID,
    approved_at TIMESTAMP,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_file_uploads_status ON file_uploads(status);
CREATE INDEX idx_file_uploads_city ON file_uploads(city_id);
CREATE INDEX idx_file_uploads_created ON file_uploads(created_at DESC);

-- Stream subscriptions (for real-time data)
CREATE TABLE IF NOT EXISTS stream_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source association
    source_id UUID REFERENCES data_sources(id) ON DELETE CASCADE,
    
    -- Stream configuration
    stream_type VARCHAR(50), -- 'websocket', 'kafka', 'webhook', 'sse', 'polling'
    endpoint_url TEXT,
    authentication JSONB, -- encrypted auth config
    
    -- Status
    status VARCHAR(50) DEFAULT 'active', -- active, paused, error
    connection_status VARCHAR(50) DEFAULT 'disconnected', -- connected, disconnected, reconnecting
    last_message_at TIMESTAMP,
    
    -- Metrics
    messages_received BIGINT DEFAULT 0,
    messages_processed BIGINT DEFAULT 0,
    messages_failed BIGINT DEFAULT 0,
    avg_latency_ms INTEGER,
    
    -- Backpressure handling
    buffer_size INTEGER DEFAULT 1000,
    current_buffer_usage INTEGER DEFAULT 0,
    
    -- Reconnection settings
    auto_reconnect BOOLEAN DEFAULT TRUE,
    reconnect_attempts INTEGER DEFAULT 0,
    max_reconnect_attempts INTEGER DEFAULT 10,
    reconnect_delay_ms INTEGER DEFAULT 5000,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Folder watchers (for folder-based data)
CREATE TABLE IF NOT EXISTS folder_watchers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source association
    source_id UUID REFERENCES data_sources(id) ON DELETE CASCADE,
    
    -- Folder configuration
    watch_path TEXT NOT NULL,
    file_pattern VARCHAR(255) DEFAULT '*', -- glob pattern
    recursive BOOLEAN DEFAULT FALSE,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active', -- active, paused, error
    last_scan_at TIMESTAMP,
    
    -- Processing rules
    auto_process BOOLEAN DEFAULT TRUE,
    process_action VARCHAR(50) DEFAULT 'ingest', -- ingest, archive, notify
    archive_path TEXT,
    
    -- Statistics
    files_discovered INTEGER DEFAULT 0,
    files_processed INTEGER DEFAULT 0,
    files_pending INTEGER DEFAULT 0,
    files_failed INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Scrapers configuration
CREATE TABLE IF NOT EXISTS scrapers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source association
    source_id UUID REFERENCES data_sources(id) ON DELETE CASCADE,
    
    -- Scraper configuration
    name VARCHAR(255) NOT NULL,
    scraper_type VARCHAR(50), -- 'apify', 'custom', 'puppeteer', 'scrapy'
    target_url TEXT,
    config JSONB, -- scraper-specific configuration
    
    -- Scheduling
    schedule_cron VARCHAR(100),
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active', -- active, paused, error, disabled
    
    -- Metrics
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    avg_records_per_run INTEGER DEFAULT 0,
    avg_duration_seconds INTEGER DEFAULT 0,
    
    -- Rate limiting
    rate_limit_requests_per_min INTEGER DEFAULT 60,
    concurrent_requests INTEGER DEFAULT 1,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Data quality issues log
CREATE TABLE IF NOT EXISTS data_quality_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference
    source_id UUID REFERENCES data_sources(id),
    job_id UUID REFERENCES ingestion_jobs(id),
    record_id UUID, -- reference to the actual record if available
    
    -- Issue details
    issue_type VARCHAR(100), -- 'missing_field', 'invalid_format', 'out_of_range', 'duplicate', 'inconsistent'
    severity VARCHAR(50), -- 'error', 'warning', 'info'
    field_name VARCHAR(255),
    
    -- Context
    expected_value TEXT,
    actual_value TEXT,
    message TEXT,
    
    -- Resolution
    status VARCHAR(50) DEFAULT 'open', -- open, resolved, ignored
    resolved_at TIMESTAMP,
    resolved_by UUID,
    resolution_note TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_data_quality_issues_source ON data_quality_issues(source_id);
CREATE INDEX idx_data_quality_issues_status ON data_quality_issues(status);
CREATE INDEX idx_data_quality_issues_created ON data_quality_issues(created_at DESC);

-- Data layer metrics (time-series for dashboard)
CREATE TABLE IF NOT EXISTS data_layer_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Time bucket
    recorded_at TIMESTAMP DEFAULT NOW(),
    bucket_type VARCHAR(20) DEFAULT 'hourly', -- hourly, daily, weekly
    
    -- Source reference (NULL for aggregate)
    source_id UUID REFERENCES data_sources(id),
    
    -- Volume metrics
    records_ingested BIGINT DEFAULT 0,
    records_updated BIGINT DEFAULT 0,
    records_deleted BIGINT DEFAULT 0,
    
    -- Quality metrics
    avg_quality_score NUMERIC(3, 2),
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    
    -- Performance metrics
    avg_ingestion_time_ms INTEGER,
    max_ingestion_time_ms INTEGER,
    
    -- Storage metrics
    storage_used_bytes BIGINT DEFAULT 0,
    
    UNIQUE(recorded_at, bucket_type, source_id)
);

CREATE INDEX idx_data_layer_metrics_time ON data_layer_metrics(recorded_at DESC);
CREATE INDEX idx_data_layer_metrics_source ON data_layer_metrics(source_id);

-- Functions for updating timestamps
CREATE OR REPLACE FUNCTION update_data_layer_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update triggers
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_data_sources_updated') THEN
        CREATE TRIGGER trg_data_sources_updated
            BEFORE UPDATE ON data_sources
            FOR EACH ROW EXECUTE FUNCTION update_data_layer_timestamp();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_file_uploads_updated') THEN
        CREATE TRIGGER trg_file_uploads_updated
            BEFORE UPDATE ON file_uploads
            FOR EACH ROW EXECUTE FUNCTION update_data_layer_timestamp();
    END IF;
END $$;

-- View for data layer overview
CREATE OR REPLACE VIEW v_data_layer_overview AS
SELECT 
    ds.id,
    ds.name,
    ds.source_type,
    ds.category,
    ds.status,
    ds.health_status,
    ds.city_id,
    ds.total_records,
    ds.records_today,
    ds.avg_quality_score,
    ds.error_rate,
    ds.last_sync_at,
    ds.sync_frequency,
    (SELECT COUNT(*) FROM ingestion_jobs ij WHERE ij.source_id = ds.id AND ij.status = 'running') as active_jobs,
    (SELECT COUNT(*) FROM data_quality_issues dqi WHERE dqi.source_id = ds.id AND dqi.status = 'open') as open_issues
FROM data_sources ds;

-- View for recent ingestion activity
CREATE OR REPLACE VIEW v_recent_ingestions AS
SELECT 
    ij.id,
    ds.name as source_name,
    ds.source_type,
    ij.job_type,
    ij.status,
    ij.started_at,
    ij.completed_at,
    ij.duration_seconds,
    ij.total_records,
    ij.success_records,
    ij.failed_records,
    ij.avg_quality_score,
    ij.error_message
FROM ingestion_jobs ij
JOIN data_sources ds ON ds.id = ij.source_id
ORDER BY ij.created_at DESC
LIMIT 100;
