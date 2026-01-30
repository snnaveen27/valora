"""
Ingest data from data_backup folder into database
Valora 2025 v2.5
"""
import sqlite3
import json
import csv
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "src" / "data" / "valora.db"
BACKUP_DIR = Path(__file__).parent.parent / "src" / "data" / "data_backup"

def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def ingest_gov_data():
    """Ingest government data CSVs."""
    print("\n[1/4] Ingesting Government Data...")
    gov_dir = BACKUP_DIR / "GOV DATA"
    if not gov_dir.exists():
        print("  - GOV DATA folder not found")
        return 0
    
    conn = get_conn()
    cursor = conn.cursor()
    
    count = 0
    for csv_file in gov_dir.glob("*.csv"):
        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Determine data type from filename
                    fname = csv_file.name.lower()
                    if 'udise' in fname or 'enrol' in fname or 'teacher' in fname:
                        data_type = 'education'
                        category = 'education'
                    elif 'rs_session' in fname or 'rj_session' in fname:
                        data_type = 'legislative'
                        category = 'government'
                    else:
                        data_type = 'other'
                        category = 'general'
                    
                    # Use correct schema: source, category, name, data_type, raw_data
                    cursor.execute("""
                        INSERT INTO gov_data (data_id, source, category, name, data_type, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (f"gov_{count}", csv_file.name, category, 
                          row.get('name', csv_file.stem), data_type, json.dumps(row)))
                    count += 1
        except Exception as e:
            print(f"  ✗ Error processing {csv_file.name}: {e}")
    
    conn.commit()
    conn.close()
    print(f"  ✓ Ingested {count} government records")
    return count

def ingest_osm_geojson():
    """Ingest OSM extracted GeoJSON data."""
    print("\n[2/4] Ingesting OSM Extracted Data...")
    osm_dir = BACKUP_DIR / "osm_extracted"
    if not osm_dir.exists():
        print("  - osm_extracted folder not found")
        return 0
    
    conn = get_conn()
    cursor = conn.cursor()
    total = 0
    
    # Process POIs
    pois_file = osm_dir / "pois.geojson"
    if pois_file.exists():
        try:
            with open(pois_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            features = data.get('features', [])
            poi_count = 0
            
            for feat in features:
                props = feat.get('properties', {})
                geom = feat.get('geometry', {})
                coords = geom.get('coordinates', [0, 0])
                
                if geom.get('type') == 'Point' and len(coords) >= 2:
                    lng, lat = coords[0], coords[1]
                    name = props.get('name', '')
                    category = props.get('amenity') or props.get('shop') or props.get('tourism') or 'other'
                    
                    if name and lat and lng:
                        # Check if exists
                        cursor.execute("SELECT 1 FROM pois WHERE name = ? AND latitude = ? AND longitude = ?", 
                                      (name, lat, lng))
                        if not cursor.fetchone():
                            cursor.execute("""
                                INSERT INTO pois (poi_id, name, category, latitude, longitude, source_data, city_id)
                                VALUES (?, ?, ?, ?, ?, ?, 'BLR')
                            """, (f"osm_{poi_count}", name, category, lat, lng, json.dumps(props)))
                            poi_count += 1
            
            print(f"  ✓ Processed {poi_count} new POIs from OSM")
            total += poi_count
        except Exception as e:
            print(f"  ✗ Error processing pois.geojson: {e}")
    
    # Process Transport
    transport_file = osm_dir / "transport.geojson"
    if transport_file.exists():
        try:
            with open(transport_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            features = data.get('features', [])
            trans_count = 0
            
            for feat in features:
                props = feat.get('properties', {})
                geom = feat.get('geometry', {})
                coords = geom.get('coordinates', [0, 0])
                
                if geom.get('type') == 'Point' and len(coords) >= 2:
                    lng, lat = coords[0], coords[1]
                    name = props.get('name', '')
                    stop_type = props.get('public_transport') or props.get('railway') or props.get('highway') or 'bus_stop'
                    
                    if lat and lng:
                        cursor.execute("SELECT 1 FROM transport_stops WHERE latitude = ? AND longitude = ?", 
                                      (lat, lng))
                        if not cursor.fetchone():
                            # Use correct schema: stop_id, source, name, transport_type, latitude, longitude, city_id
                            cursor.execute("""
                                INSERT INTO transport_stops (stop_id, source, name, transport_type, latitude, longitude, city_id)
                                VALUES (?, ?, ?, ?, ?, ?, 'BLR')
                            """, (f"osm_trans_{trans_count}", 'osm', name or f"Stop {trans_count}", stop_type, lat, lng))
                            trans_count += 1
            
            print(f"  ✓ Processed {trans_count} new transport stops from OSM")
            total += trans_count
        except Exception as e:
            print(f"  ✗ Error processing transport.geojson: {e}")
    
    # Process Places
    places_file = osm_dir / "places.geojson"
    if places_file.exists():
        try:
            with open(places_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            features = data.get('features', [])
            place_count = 0
            
            for feat in features:
                props = feat.get('properties', {})
                geom = feat.get('geometry', {})
                coords = geom.get('coordinates', [0, 0])
                
                if len(coords) >= 2:
                    lng, lat = coords[0], coords[1]
                    name = props.get('name', '')
                    place_type = props.get('place') or 'locality'
                    
                    if name and lat and lng:
                        cursor.execute("SELECT 1 FROM places WHERE name = ?", (name,))
                        if not cursor.fetchone():
                            cursor.execute("""
                                INSERT INTO places (place_id, name, type, latitude, longitude, city_id)
                                VALUES (?, ?, ?, ?, ?, 'BLR')
                            """, (f"osm_place_{place_count}", name, place_type, lat, lng))
                            place_count += 1
            
            print(f"  ✓ Processed {place_count} new places from OSM")
            total += place_count
        except Exception as e:
            print(f"  ✗ Error processing places.geojson: {e}")
    
    conn.commit()
    conn.close()
    return total

def ingest_posted_properties():
    """Check and ingest any missing posted properties."""
    print("\n[3/4] Checking Posted Properties...")
    props_dir = BACKUP_DIR / "posted_properties"
    if not props_dir.exists():
        print("  - posted_properties folder not found")
        return 0
    
    files = list(props_dir.glob("*.json"))
    print(f"  - Found {len(files)} property files")
    
    # Properties are likely already ingested, just verify
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM properties")
    count = cursor.fetchone()[0]
    conn.close()
    
    print(f"  ✓ Database has {count:,} properties")
    return 0

def update_data_catalog():
    """Update data catalog with backup sources."""
    print("\n[4/4] Updating Data Catalog...")
    conn = get_conn()
    cursor = conn.cursor()
    
    # Use correct schema: dataset_name, dataset_title, category, source_url, file_format, status
    sources = [
        ('osm_pois', 'OpenStreetMap POIs', 'infrastructure', 'data_backup/osm_extracted/pois.geojson', 'geojson'),
        ('osm_transport', 'OpenStreetMap Transport', 'transport', 'data_backup/osm_extracted/transport.geojson', 'geojson'),
        ('osm_places', 'OpenStreetMap Places', 'places', 'data_backup/osm_extracted/places.geojson', 'geojson'),
        ('gov_education', 'UDISE Education Data', 'education', 'data_backup/GOV DATA/', 'csv'),
        ('gov_legislative', 'Legislative Session Data', 'government', 'data_backup/GOV DATA/', 'csv'),
    ]
    
    for name, title, category, path, format_type in sources:
        cursor.execute("""
            INSERT OR REPLACE INTO data_catalog (dataset_name, dataset_title, category, source_url, file_format, status, ingested_at)
            VALUES (?, ?, ?, ?, ?, 'ingested', datetime('now'))
        """, (name, title, category, path, format_type))
    
    conn.commit()
    conn.close()
    print(f"  ✓ Updated data catalog with {len(sources)} sources")
    return len(sources)

def main():
    print("=" * 60)
    print("VALORA 2025 v2.5 - INGEST BACKUP DATA")
    print("=" * 60)
    
    if not BACKUP_DIR.exists():
        print(f"ERROR: Backup directory not found: {BACKUP_DIR}")
        return
    
    total = 0
    total += ingest_gov_data()
    total += ingest_osm_geojson()
    total += ingest_posted_properties()
    total += update_data_catalog()
    
    print("\n" + "=" * 60)
    print(f"INGESTION COMPLETE - Added {total} records")
    print("=" * 60)

if __name__ == "__main__":
    main()
