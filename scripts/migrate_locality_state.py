"""
Valora AI - Locality State Store Migration
Creates tables for the Knowledge Layer architecture.
Non-breaking: Only ADDS new tables, doesn't modify existing ones.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Database path
DB_PATH = Path(__file__).parent.parent / "src" / "data" / "valora.db"


def migrate_locality_state(db_path: str = None):
    """Create locality state tables for the knowledge layer."""
    db = db_path or str(DB_PATH)
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("LOCALITY STATE STORE MIGRATION")
    print("=" * 60)
    
    # 1. Current Locality State (latest snapshot per ward/locality)
    print("\n[1/4] Creating locality_state table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locality_state (
            locality_id TEXT PRIMARY KEY,
            locality_name TEXT NOT NULL,
            city_id TEXT DEFAULT 'BLR',
            locality_type TEXT DEFAULT 'ward',  -- ward, zone, neighborhood
            snapshot_date DATE NOT NULL,
            
            -- Geographic bounds
            center_lat REAL,
            center_lng REAL,
            
            -- Market Metrics
            avg_price_sqft REAL,
            median_price_sqft REAL,
            price_trend_1m REAL,
            price_trend_3m REAL,
            price_trend_6m REAL,
            price_trend_12m REAL,
            active_listings INTEGER DEFAULT 0,
            listings_trend_1m REAL,
            avg_rental_yield REAL,
            demand_level TEXT,  -- high, medium, low
            supply_level TEXT,  -- oversupply, balanced, undersupply
            
            -- Spatial Features
            poi_count INTEGER DEFAULT 0,
            transport_count INTEGER DEFAULT 0,
            metro_count INTEGER DEFAULT 0,
            bus_count INTEGER DEFAULT 0,
            school_count INTEGER DEFAULT 0,
            hospital_count INTEGER DEFAULT 0,
            park_count INTEGER DEFAULT 0,
            mall_count INTEGER DEFAULT 0,
            
            -- Computed Scores (0-100)
            accessibility_score REAL,
            walkability_score REAL,
            livability_score REAL,
            infrastructure_score REAL,
            connectivity_score REAL,
            
            -- Intelligence Labels (precomputed)
            growth_phase TEXT,  -- emerging, growing, maturing, mature, declining
            growth_phase_confidence REAL,
            investor_type TEXT,  -- conservative, balanced, aggressive, speculative
            risk_index REAL,
            risk_level TEXT,  -- low, medium, high, very_high
            hotspot_score REAL,
            hotspot_rank INTEGER,
            
            -- Locality Character
            archetype TEXT,  -- tech_hub, family_suburb, premium_enclave, etc.
            primary_demographic TEXT,
            avg_income_bracket TEXT,
            
            -- Data Quality
            data_completeness REAL,  -- 0-1 (how much data we have)
            confidence_score REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Indexing
            UNIQUE(locality_id, city_id)
        )
    """)
    print("   ✓ locality_state table created")
    
    # 2. Historical Locality State (time series)
    print("\n[2/4] Creating locality_state_ts table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locality_state_ts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            locality_id TEXT NOT NULL,
            city_id TEXT DEFAULT 'BLR',
            snapshot_date DATE NOT NULL,
            
            -- Same metrics as locality_state
            avg_price_sqft REAL,
            median_price_sqft REAL,
            active_listings INTEGER,
            demand_level TEXT,
            supply_level TEXT,
            
            poi_count INTEGER,
            transport_count INTEGER,
            
            accessibility_score REAL,
            walkability_score REAL,
            livability_score REAL,
            
            growth_phase TEXT,
            risk_index REAL,
            hotspot_score REAL,
            
            confidence_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(locality_id, city_id, snapshot_date)
        )
    """)
    print("   ✓ locality_state_ts table created")
    
    # 3. Prediction Logs (for learning loop)
    print("\n[3/4] Creating prediction_logs table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            locality_id TEXT NOT NULL,
            city_id TEXT DEFAULT 'BLR',
            
            -- When prediction was made and for when
            prediction_date DATE NOT NULL,
            target_date DATE NOT NULL,
            prediction_horizon TEXT,  -- 1m, 3m, 6m, 12m
            
            -- What we predicted
            predicted_price_change REAL,
            predicted_demand_level TEXT,
            predicted_growth_phase TEXT,
            
            -- Reasoning
            confidence REAL,
            key_drivers TEXT,  -- JSON array of drivers
            reasoning_summary TEXT,
            
            -- Actual outcomes (filled when target_date arrives)
            actual_price_change REAL,
            actual_demand_level TEXT,
            prediction_error REAL,
            
            -- Evaluation
            evaluated_at TIMESTAMP,
            accuracy_score REAL,
            
            -- Metadata
            model_version TEXT DEFAULT 'v1.0',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✓ prediction_logs table created")
    
    # 4. Feature Store (precomputed features for fast lookup)
    print("\n[4/4] Creating feature_store table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feature_store (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,  -- locality, property, poi
            entity_id TEXT NOT NULL,
            city_id TEXT DEFAULT 'BLR',
            
            feature_name TEXT NOT NULL,
            feature_value REAL,
            feature_value_text TEXT,
            feature_value_json TEXT,
            
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            valid_until TIMESTAMP,
            
            UNIQUE(entity_type, entity_id, city_id, feature_name)
        )
    """)
    print("   ✓ feature_store table created")
    
    # Create indexes for fast lookups
    print("\n[5/5] Creating indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_locality_state_city ON locality_state(city_id)",
        "CREATE INDEX IF NOT EXISTS idx_locality_state_growth ON locality_state(growth_phase)",
        "CREATE INDEX IF NOT EXISTS idx_locality_state_hotspot ON locality_state(hotspot_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_locality_state_ts_date ON locality_state_ts(snapshot_date)",
        "CREATE INDEX IF NOT EXISTS idx_locality_state_ts_locality ON locality_state_ts(locality_id, snapshot_date)",
        "CREATE INDEX IF NOT EXISTS idx_prediction_logs_date ON prediction_logs(prediction_date)",
        "CREATE INDEX IF NOT EXISTS idx_prediction_logs_target ON prediction_logs(target_date)",
        "CREATE INDEX IF NOT EXISTS idx_feature_store_entity ON feature_store(entity_type, entity_id)",
    ]
    for idx in indexes:
        cursor.execute(idx)
    print("   ✓ Indexes created")
    
    conn.commit()
    
    # Verify tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'locality%' OR name LIKE 'prediction%' OR name LIKE 'feature%'")
    tables = [r[0] for r in cursor.fetchall()]
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"Tables created: {', '.join(tables)}")
    
    conn.close()
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = None
    
    migrate_locality_state(db_path)
