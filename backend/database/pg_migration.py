"""
PostgreSQL Migration Module for Phase 3 Scaling

This module provides:
1. Schema migration from SQLite to PostgreSQL + PostGIS
2. Data migration with batch processing
3. A compatibility layer that abstracts the database backend

Usage:
    # Check if PostgreSQL is available
    from database.pg_migration import check_pg_available, migrate_schema
    
    if check_pg_available():
        migrate_schema()  # Creates PostgreSQL tables
        migrate_data(batch_size=1000)  # Copies data from SQLite
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# PostgreSQL connection config (from environment)
PG_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", "5432")),
    "database": os.getenv("PG_DATABASE", "valora"),
    "user": os.getenv("PG_USER", "valora"),
    "password": os.getenv("PG_PASSWORD", ""),
}


def check_pg_available() -> bool:
    """Check if PostgreSQL driver and server are available."""
    try:
        import psycopg2
        conn = psycopg2.connect(**PG_CONFIG)
        conn.close()
        logger.info("[PG] PostgreSQL available")
        return True
    except ImportError:
        logger.debug("[PG] psycopg2 not installed (pip install psycopg2-binary)")
        return False
    except Exception as e:
        logger.debug(f"[PG] PostgreSQL not reachable: {e}")
        return False


# PostgreSQL schema (PostGIS-enabled)
PG_SCHEMA = """
-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Properties table
CREATE TABLE IF NOT EXISTS properties (
    id SERIAL PRIMARY KEY,
    property_id VARCHAR(255) UNIQUE,
    title TEXT,
    description TEXT,
    price NUMERIC,
    price_per_sqft NUMERIC,
    total_area_sqft NUMERIC,
    bedrooms INTEGER,
    bathrooms INTEGER,
    property_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',
    locality VARCHAR(255),
    area_name VARCHAR(255),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    source VARCHAR(100),
    url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    scraped_at TIMESTAMP
);

-- Spatial index
CREATE INDEX IF NOT EXISTS idx_properties_geom ON properties USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_properties_locality ON properties (locality);
CREATE INDEX IF NOT EXISTS idx_properties_status ON properties (status);
CREATE INDEX IF NOT EXISTS idx_properties_price ON properties (price);

-- POIs table
CREATE TABLE IF NOT EXISTS pois (
    id SERIAL PRIMARY KEY,
    name TEXT,
    category VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    address TEXT,
    rating NUMERIC,
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pois_geom ON pois USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_pois_category ON pois (category);

-- Buildings table
CREATE TABLE IF NOT EXISTS buildings (
    id SERIAL PRIMARY KEY,
    building_id VARCHAR(255) UNIQUE,
    name TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    height_m NUMERIC,
    floors INTEGER,
    building_type VARCHAR(100),
    locality VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_buildings_geom ON buildings USING GIST (geom);

-- Places table
CREATE TABLE IF NOT EXISTS places (
    id SERIAL PRIMARY KEY,
    name TEXT,
    category VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    address TEXT,
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_places_geom ON places USING GIST (geom);

-- Transport stops
CREATE TABLE IF NOT EXISTS transport_stops (
    id SERIAL PRIMARY KEY,
    name TEXT,
    type VARCHAR(50),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    route_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transport_geom ON transport_stops USING GIST (geom);

-- Ingestion log
CREATE TABLE IF NOT EXISTS ingestion_log (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(255),
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    status VARCHAR(50),
    error_message TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Locality state
CREATE TABLE IF NOT EXISTS locality_state (
    id SERIAL PRIMARY KEY,
    locality_name VARCHAR(255) UNIQUE,
    poi_count INTEGER DEFAULT 0,
    transport_count INTEGER DEFAULT 0,
    property_count INTEGER DEFAULT 0,
    avg_price_per_sqft NUMERIC,
    growth_phase VARCHAR(50),
    last_updated TIMESTAMP DEFAULT NOW()
);
"""


def migrate_schema(pg_config: dict = None) -> bool:
    """Create PostgreSQL schema."""
    try:
        import psycopg2
        config = pg_config or PG_CONFIG
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        cursor.execute(PG_SCHEMA)
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("[PG] Schema created successfully")
        return True
    except Exception as e:
        logger.error(f"[PG] Schema migration failed: {e}")
        return False


def migrate_data(
    sqlite_path: str,
    pg_config: dict = None,
    batch_size: int = 1000,
    tables: List[str] = None,
) -> Dict[str, Any]:
    """
    Migrate data from SQLite to PostgreSQL.
    
    Args:
        sqlite_path: Path to SQLite database
        pg_config: PostgreSQL connection config
        batch_size: Number of rows per insert batch
        tables: List of tables to migrate (None = all)
    
    Returns:
        Migration statistics
    """
    try:
        import psycopg2
    except ImportError:
        return {"success": False, "error": "psycopg2 not installed"}
    
    config = pg_config or PG_CONFIG
    stats = {"migrated": {}, "errors": []}
    
    if tables is None:
        tables = ["properties", "pois", "buildings", "places", "transport_stops"]
    
    try:
        # Connect to both databases
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        pg_conn = psycopg2.connect(**config)
        pg_cursor = pg_conn.cursor()
        
        for table in tables:
            try:
                # Read from SQLite
                cursor = sqlite_conn.cursor()
                cursor.execute(f"SELECT * FROM {table}")
                
                rows = cursor.fetchall()
                if not rows:
                    stats["migrated"][table] = 0
                    continue
                
                columns = [desc[0] for desc in cursor.description]
                
                # Remove 'id' column (PostgreSQL uses SERIAL)
                if 'id' in columns:
                    id_idx = columns.index('id')
                    columns = [c for c in columns if c != 'id']
                
                # Add geom column for spatial tables
                has_lat = 'latitude' in columns
                has_lng = 'longitude' in columns
                
                migrated = 0
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    
                    for row in batch:
                        values = []
                        geom_sql = None
                        
                        for col in columns:
                            if col == 'geom':
                                continue
                            val = row[col]
                            values.append(val)
                        
                        # Generate geom from lat/lng
                        if has_lat and has_lng:
                            lat = row['latitude']
                            lng = row['longitude']
                            if lat and lng:
                                geom_sql = f"ST_SetSRID(ST_MakePoint({lng}, {lat}), 4326)"
                        
                        placeholders = ', '.join(['%s'] * len(values))
                        col_list = ', '.join(columns)
                        
                        if geom_sql:
                            col_list += ', geom'
                            placeholders += f', {geom_sql}'
                        
                        # Upsert
                        update_cols = ', '.join([f"{c} = EXCLUDED.{c}" for c in columns if c != 'id'])
                        pg_cursor.execute(f"""
                            INSERT INTO {table} ({col_list})
                            VALUES ({placeholders})
                            ON CONFLICT DO NOTHING
                        """, values)
                    
                    pg_conn.commit()
                    migrated += len(batch)
                
                stats["migrated"][table] = migrated
                logger.info(f"[PG] Migrated {migrated} rows from {table}")
                
            except Exception as e:
                stats["errors"].append(f"{table}: {str(e)}")
                logger.error(f"[PG] Error migrating {table}: {e}")
                pg_conn.rollback()
        
        sqlite_conn.close()
        pg_conn.close()
        
        stats["success"] = len(stats["errors"]) == 0
        return stats
        
    except Exception as e:
        logger.error(f"[PG] Migration failed: {e}")
        return {"success": False, "error": str(e)}


def get_pg_db_service(pg_config: dict = None):
    """
    Get a PostgreSQL-backed database service.
    Returns None if PostgreSQL is not available.
    """
    if not check_pg_available():
        return None
    
    # Import here to avoid hard dependency
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return _PostgresService(pg_config or PG_CONFIG)
    except ImportError:
        return None


class _PostgresService:
    """PostgreSQL database service with same interface as SQLite DatabaseService."""
    
    def __init__(self, config: dict):
        self.config = config
    
    def _get_conn(self):
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(**self.config, cursor_factory=RealDictCursor)
    
    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(row) for row in rows]
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"
        
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(query, tuple(data.values()))
        row_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        return row_id
