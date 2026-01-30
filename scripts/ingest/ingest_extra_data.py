"""
Ingest extra data from data_extra folder into Valora database.
Handles: AQI data, Crime statistics, GeoJSON, and other datasets.
"""

import sqlite3
import json
import csv
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "src" / "data" / "valora.db"
DATA_EXTRA_DIR = BASE_DIR / "src" / "data" / "data_extra"


def ensure_tables():
    """Create tables for extra data."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # AQI data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aqi_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT DEFAULT 'Bengaluru',
            date DATE,
            aqi_value REAL,
            aqi_category TEXT,
            pm25 REAL,
            pm10 REAL,
            no2 REAL,
            so2 REAL,
            co REAL,
            o3 REAL,
            year INTEGER,
            month INTEGER,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Crime statistics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crime_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            district TEXT,
            crime_type TEXT,
            incidents INTEGER,
            victims INTEGER,
            crime_rate REAL,
            year INTEGER,
            source TEXT,
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Watersheds/environmental data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS environmental_zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id TEXT UNIQUE,
            zone_type TEXT,
            name TEXT,
            area_sqkm REAL,
            boundary_geojson TEXT,
            properties TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Generic datasets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS open_datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id TEXT,
            dataset_name TEXT,
            category TEXT,
            data_type TEXT,
            record_count INTEGER,
            source_url TEXT,
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_aqi_date ON aqi_data(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_crime_district ON crime_stats(district)")
    
    conn.commit()
    conn.close()
    print("✓ Tables created/verified")


def ingest_aqi_data():
    """Ingest AQI Excel files from 2017-2025."""
    if not PANDAS_AVAILABLE:
        print("⚠️  pandas not available, skipping AQI ingestion")
        return 0
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    total_records = 0
    months = ['January', 'February', 'March', 'April', 'May', 'June', 
              'July', 'August', 'September', 'October', 'November', 'December']
    
    for year in range(2017, 2026):
        pattern = f"AQI_daily_city_level_bengaluru_{year}*.xlsx"
        files = list(DATA_EXTRA_DIR.glob(pattern))
        
        for file_path in files:
            try:
                df = pd.read_excel(file_path)
                print(f"  Processing {file_path.name}: {len(df)} rows")
                
                # Data format: Day | January | February | ... | December
                for _, row in df.iterrows():
                    day = row.get('Day')
                    if pd.isna(day):
                        continue
                    day = int(day)
                    
                    for month_idx, month_name in enumerate(months, 1):
                        aqi_val = row.get(month_name)
                        if pd.isna(aqi_val):
                            continue
                        
                        try:
                            date_str = f"{year}-{month_idx:02d}-{day:02d}"
                            cursor.execute("""
                                INSERT OR IGNORE INTO aqi_data 
                                (city, date, aqi_value, year, month, source)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, ('Bengaluru', date_str, float(aqi_val), year, month_idx, file_path.name))
                            total_records += 1
                        except:
                            continue
                        
            except Exception as e:
                print(f"  ❌ Error reading {file_path.name}: {e}")
    
    conn.commit()
    conn.close()
    return total_records


def ingest_crime_data():
    """Ingest crime statistics CSV files."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    total_records = 0
    
    # File patterns and their crime types
    crime_files = [
        ('83f88f01-29e7-478b-921a-b5743c5b72ea.csv', 'murder_homicide'),
        ('91595449-b2cf-4653-ad7d-11f37d2b50f4.csv', 'assault_women'),
        ('b99f599f-6f5f-4e5f-a440-915d597a680f.csv', 'other'),
        ('ffce2bf3-1202-489d-8af5-f156c2e9b793.csv', 'other'),
    ]
    
    for filename, crime_type in crime_files:
        file_path = DATA_EXTRA_DIR / filename
        if not file_path.exists():
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    district = row.get('Districts', row.get('District', ''))
                    
                    if not district:
                        continue
                    
                    # Store raw data
                    raw_data = json.dumps(row)
                    
                    # Extract key metrics
                    incidents = 0
                    victims = 0
                    rate = 0.0
                    
                    for key, val in row.items():
                        if 'Incidence' in key or '- I' in key:
                            try:
                                incidents += int(val) if val else 0
                            except:
                                pass
                        if 'Victims' in key or '- V' in key:
                            try:
                                victims += int(val) if val else 0
                            except:
                                pass
                        if 'Rate' in key or '- R' in key:
                            try:
                                rate = float(val) if val else 0
                            except:
                                pass
                    
                    cursor.execute("""
                        INSERT INTO crime_stats 
                        (district, crime_type, incidents, victims, crime_rate, source, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (district, crime_type, incidents, victims, rate, filename, raw_data))
                    total_records += 1
                    
            print(f"  ✓ Processed {filename}")
            
        except Exception as e:
            print(f"  ❌ Error reading {filename}: {e}")
    
    conn.commit()
    conn.close()
    return total_records


def ingest_watersheds():
    """Ingest micro watersheds GeoJSON."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    geojson_file = DATA_EXTRA_DIR / "bengaluru_micro_watersheds.geojson"
    
    if not geojson_file.exists():
        print("  ⚠️  Watersheds GeoJSON not found")
        return 0
    
    try:
        with open(geojson_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        features = data.get('features', [])
        count = 0
        
        for feat in features:
            props = feat.get('properties', {})
            geom = feat.get('geometry', {})
            
            zone_id = props.get('id', f"ws_{count}")
            name = props.get('name', props.get('Name', f"Watershed {count}"))
            
            cursor.execute("""
                INSERT OR REPLACE INTO environmental_zones 
                (zone_id, zone_type, name, boundary_geojson, properties, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                zone_id, 'micro_watershed', name,
                json.dumps(geom), json.dumps(props), 'bengaluru_micro_watersheds.geojson'
            ))
            count += 1
        
        conn.commit()
        print(f"  ✓ Ingested {count} watersheds")
        return count
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return 0
    finally:
        conn.close()


def main():
    print("=" * 70)
    print("VALORA AI - EXTRA DATA INGESTION")
    print("=" * 70)
    
    print("\n[1/4] Creating tables...")
    ensure_tables()
    
    print("\n[2/4] Ingesting AQI data (2017-2025)...")
    aqi_count = ingest_aqi_data()
    print(f"  ✓ Total AQI records: {aqi_count}")
    
    print("\n[3/4] Ingesting crime statistics...")
    crime_count = ingest_crime_data()
    print(f"  ✓ Total crime records: {crime_count}")
    
    print("\n[4/4] Ingesting watersheds...")
    ws_count = ingest_watersheds()
    
    print("\n" + "=" * 70)
    print("INGESTION COMPLETE")
    print("=" * 70)
    print(f"AQI Records: {aqi_count}")
    print(f"Crime Records: {crime_count}")
    print(f"Watersheds: {ws_count}")


if __name__ == "__main__":
    main()
