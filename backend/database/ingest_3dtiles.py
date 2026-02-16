"""
Ingest 3D Tiles into Database
Reads all building tile files and inserts polygon geometries into the database
"""
import json
import sqlite3
from pathlib import Path
from typing import List, Dict

# Paths
TILES_DIR = Path(__file__).parent.parent.parent / 'storage' / '3dtiles' / 'tiles'
DB_PATH = Path(__file__).parent.parent.parent / 'storage' / 'valora.db'

def add_polygon_column():
    """Add polygon_coords column to buildings table if it doesn't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            ALTER TABLE buildings ADD COLUMN polygon_coords TEXT
        """)
        conn.commit()
        print("[OK] Added polygon_coords column to buildings table")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("[INFO] polygon_coords column already exists")
        else:
            raise
    finally:
        conn.close()

def ingest_tile_file(tile_path: Path) -> int:
    """Ingest buildings from a single tile file"""
    with open(tile_path, 'r') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    if not features:
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    inserted = 0
    updated = 0
    
    for feature in features:
        geom = feature.get('geometry', {})
        props = feature.get('properties', {})
        
        if geom.get('type') != 'Polygon' or not geom.get('coordinates'):
            continue
        
        # Extract polygon coordinates (first ring)
        coords = geom['coordinates'][0]
        
        # Calculate centroid
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        centroid_lng = sum(lons) / len(lons)
        centroid_lat = sum(lats) / len(lats)
        
        # Extract properties
        height = props.get('height', 10)
        building_type = props.get('building') or props.get('type', 'yes')
        name = props.get('name')
        levels = props.get('levels') or max(1, int(height / 3))
        osm_id = props.get('id', f'tile_{tile_path.stem}_{inserted}')
        
        # Store polygon as JSON
        polygon_json = json.dumps(coords)
        
        try:
            # Try to update existing building by osm_id
            cursor.execute("""
                UPDATE buildings 
                SET polygon_coords = ?, height = ?, levels = ?, building_type = ?, 
                    name = ?, latitude = ?, longitude = ?
                WHERE osm_id = ?
            """, (polygon_json, height, levels, building_type, name, centroid_lat, centroid_lng, osm_id))
            
            if cursor.rowcount > 0:
                updated += 1
            else:
                # Insert new building
                cursor.execute("""
                    INSERT INTO buildings (osm_id, building_type, name, height, levels, 
                                         latitude, longitude, polygon_coords, source_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (osm_id, building_type, name, height, levels, 
                      centroid_lat, centroid_lng, polygon_json, 
                      json.dumps({'tile': tile_path.stem, 'has_polygon': True})))
                inserted += 1
        except Exception as e:
            print(f"Error inserting building from {tile_path.name}: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    return inserted + updated

def main():
    """Main ingestion process"""
    print("=" * 60)
    print("3D Tiles Database Ingestion")
    print("=" * 60)
    
    # Step 1: Add polygon column
    add_polygon_column()
    
    # Step 2: Get all tile files
    if not TILES_DIR.exists():
        print(f"[ERROR] Tiles directory not found: {TILES_DIR}")
        return
    
    tile_files = list(TILES_DIR.glob('*.json'))
    print(f"[INFO] Found {len(tile_files)} tile files")
    
    # Step 3: Ingest tiles
    total_buildings = 0
    for i, tile_path in enumerate(tile_files, 1):
        count = ingest_tile_file(tile_path)
        total_buildings += count
        
        if i % 50 == 0:
            print(f"[PROGRESS] Processed {i}/{len(tile_files)} tiles ({total_buildings:,} buildings)")
    
    print(f"\n[COMPLETE] Ingested {total_buildings:,} buildings from {len(tile_files)} tiles")
    
    # Step 4: Verify
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM buildings WHERE polygon_coords IS NOT NULL")
    polygon_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM buildings")
    total_count = cursor.fetchone()[0]
    conn.close()
    
    print(f"[VERIFY] Total buildings: {total_count:,}")
    print(f"[VERIFY] Buildings with polygons: {polygon_count:,}")
    print(f"[VERIFY] Coverage: {polygon_count/total_count*100:.1f}%")

if __name__ == '__main__':
    main()
