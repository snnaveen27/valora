"""
Database Migration: Add City Support for Multi-City Expansion
Valora 2025 v2.5
"""
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "src" / "data" / "valora.db"

def migrate():
    """Add city support columns to key tables."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    print("=" * 60)
    print("VALORA 2025 v2.5 - CITY EXPANSION MIGRATION")
    print("=" * 60)
    
    # Create cities table
    print("\n[1/5] Creating cities table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cities (
            city_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            state TEXT,
            country TEXT DEFAULT 'India',
            latitude REAL,
            longitude REAL,
            bbox_north REAL,
            bbox_south REAL,
            bbox_east REAL,
            bbox_west REAL,
            timezone TEXT DEFAULT 'Asia/Kolkata',
            is_active INTEGER DEFAULT 1,
            data_version TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert Bangalore as default city
    cursor.execute("""
        INSERT OR IGNORE INTO cities (city_id, name, state, latitude, longitude, 
                                      bbox_north, bbox_south, bbox_east, bbox_west, data_version)
        VALUES ('BLR', 'Bengaluru', 'Karnataka', 12.9716, 77.5946,
                13.1500, 12.7500, 77.8000, 77.4000, '2025.2.5')
    """)
    print("  ✓ Cities table created, Bengaluru added as default")
    
    # Add city_id to key tables
    tables_to_update = [
        'properties', 'pois', 'buildings', 'roads', 'transport_stops',
        'places', 'terrain_grid', 'open_datasets', 'price_history'
    ]
    
    print("\n[2/5] Adding city_id column to tables...")
    for table in tables_to_update:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN city_id TEXT DEFAULT 'BLR'")
            print(f"  ✓ Added city_id to {table}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  - {table} already has city_id")
            else:
                print(f"  ✗ Error on {table}: {e}")
    
    # Add data versioning columns
    print("\n[3/5] Adding version tracking columns...")
    version_tables = ['properties', 'pois', 'buildings']
    for table in version_tables:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN data_version TEXT DEFAULT '2025.2.5'")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN last_updated TEXT DEFAULT CURRENT_TIMESTAMP")
            print(f"  ✓ Added versioning to {table}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  - {table} already has versioning")
    
    # Create city indexes
    print("\n[4/5] Creating city indexes for query performance...")
    indexes = [
        ("idx_properties_city", "properties", "city_id"),
        ("idx_pois_city", "pois", "city_id"),
        ("idx_buildings_city", "buildings", "city_id"),
        ("idx_roads_city", "roads", "city_id"),
        ("idx_transport_city", "transport_stops", "city_id"),
    ]
    for idx_name, table, column in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
            print(f"  ✓ Created {idx_name}")
        except Exception as e:
            print(f"  ✗ Error creating {idx_name}: {e}")
    
    # Create system metadata table
    print("\n[5/5] Creating system metadata table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_metadata (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        INSERT OR REPLACE INTO system_metadata (key, value, updated_at)
        VALUES ('version', '2025.2.5', datetime('now')),
               ('last_migration', 'city_support', datetime('now')),
               ('default_city', 'BLR', datetime('now'))
    """)
    print("  ✓ System metadata table created")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE - Ready for multi-city expansion!")
    print("=" * 60)
    print("\nSupported cities can be added to the 'cities' table.")
    print("All queries should filter by city_id for city-specific data.")

if __name__ == "__main__":
    migrate()
