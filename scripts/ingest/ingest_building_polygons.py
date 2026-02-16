"""
Ingest Building Polygon Geometry from GeoJSON backup.
This script adds polygon_coords to the buildings table for proper 3D visualization.
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List
import sys

# Paths
GEOJSON_PATH = Path(__file__).parent.parent / "storage" / "data_backup_extracted" / "data_backup" / "buildings.geojson"
DB_PATH = Path(__file__).parent.parent / "storage" / "valora.db"


def add_polygon_column():
    """Add polygon_coords column if it doesn't exist."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(buildings)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'polygon_coords' not in columns:
        print("[+] Adding polygon_coords column to buildings table...")
        cursor.execute("ALTER TABLE buildings ADD COLUMN polygon_coords TEXT")
        conn.commit()
        print("[OK] Column added")
    else:
        print("[OK] polygon_coords column already exists")
    
    conn.close()


def load_geojson() -> Dict[str, Any]:
    """Load buildings GeoJSON file."""
    print(f"[+] Loading GeoJSON from {GEOJSON_PATH}...")
    
    if not GEOJSON_PATH.exists():
        print(f"[ERROR] GeoJSON file not found: {GEOJSON_PATH}")
        sys.exit(1)
    
    with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    print(f"[OK] Loaded {len(features):,} building features")
    return data


def extract_osm_id(properties: Dict) -> str:
    """Extract OSM ID from feature properties."""
    # Try different possible fields
    osm_id = properties.get('osm_id') or properties.get('id') or properties.get('@id') or properties.get('osmId')
    if osm_id:
        # Clean up format like "way/123456" -> "123456"
        if isinstance(osm_id, str) and '/' in osm_id:
            osm_id = osm_id.split('/')[-1]
        return str(osm_id)
    return None


def calculate_centroid(coords: List) -> tuple:
    """Calculate centroid from polygon coordinates."""
    if not coords or not coords[0]:
        return None, None
    
    ring = coords[0]  # Outer ring
    lngs = [c[0] for c in ring if len(c) >= 2]
    lats = [c[1] for c in ring if len(c) >= 2]
    
    if not lngs or not lats:
        return None, None
    
    return sum(lngs) / len(lngs), sum(lats) / len(lats)


def ingest_polygons(data: Dict[str, Any], batch_size: int = 5000):
    """Ingest polygon coordinates into database."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    features = data.get('features', [])
    
    # Build lookup by osm_id
    print("[+] Building OSM ID lookup from database...")
    cursor.execute("SELECT osm_id, id FROM buildings WHERE osm_id IS NOT NULL")
    osm_lookup = {str(row[0]): row[1] for row in cursor.fetchall()}
    print(f"[OK] Found {len(osm_lookup):,} buildings with OSM IDs")
    
    # Process features
    updates = []
    inserts = []
    matched = 0
    unmatched = 0
    
    print("[+] Processing GeoJSON features...")
    
    for i, feature in enumerate(features):
        if i % 50000 == 0 and i > 0:
            print(f"    Processed {i:,}/{len(features):,}...")
        
        geom = feature.get('geometry', {})
        props = feature.get('properties', {})
        
        if geom.get('type') != 'Polygon':
            continue
        
        coords = geom.get('coordinates', [])
        if not coords:
            continue
        
        osm_id = extract_osm_id(props)
        polygon_json = json.dumps(coords[0])  # Store outer ring
        
        # Extract properties
        height = props.get('height') or props.get('building:height')
        if height:
            try:
                height = float(str(height).replace('m', '').strip())
            except:
                height = None
        
        levels = props.get('building:levels') or props.get('levels')
        if levels:
            try:
                levels = int(levels)
            except:
                levels = None
        
        building_type = props.get('building') or props.get('type') or 'yes'
        name = props.get('name')
        
        # Calculate centroid
        lng, lat = calculate_centroid(coords)
        
        if osm_id and osm_id in osm_lookup:
            # Update existing building
            updates.append((polygon_json, osm_id))
            matched += 1
        elif lat and lng:
            # Insert new building
            inserts.append({
                'osm_id': osm_id,
                'polygon_coords': polygon_json,
                'latitude': lat,
                'longitude': lng,
                'height': height or (levels * 3 if levels else 10),
                'levels': levels,
                'building_type': building_type,
                'name': name,
            })
            unmatched += 1
    
    # Apply updates in batches
    print(f"\n[+] Updating {len(updates):,} existing buildings with polygon data...")
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        cursor.executemany("""
            UPDATE buildings SET polygon_coords = ? WHERE osm_id = ?
        """, batch)
        conn.commit()
        print(f"    Updated {min(i+batch_size, len(updates)):,}/{len(updates):,}")
    
    # Insert new buildings
    print(f"\n[+] Inserting {len(inserts):,} new buildings...")
    for i in range(0, len(inserts), batch_size):
        batch = inserts[i:i+batch_size]
        cursor.executemany("""
            INSERT INTO buildings (osm_id, polygon_coords, latitude, longitude, height, levels, building_type, name, city_id)
            VALUES (:osm_id, :polygon_coords, :latitude, :longitude, :height, :levels, :building_type, :name, 'BLR')
        """, batch)
        conn.commit()
        print(f"    Inserted {min(i+batch_size, len(inserts)):,}/{len(inserts):,}")
    
    # Final stats
    cursor.execute("SELECT COUNT(*) FROM buildings WHERE polygon_coords IS NOT NULL")
    with_polygons = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM buildings")
    total = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n" + "="*60)
    print(f"POLYGON INGESTION COMPLETE")
    print(f"="*60)
    print(f"Matched & updated: {matched:,}")
    print(f"New buildings added: {len(inserts):,}")
    print(f"Buildings with polygons: {with_polygons:,} / {total:,} ({100*with_polygons/total:.1f}%)")
    print(f"="*60)


def main():
    print("="*60)
    print("VALORA AI - Building Polygon Ingestion")
    print("="*60)
    
    # Step 1: Add column
    add_polygon_column()
    
    # Step 2: Load GeoJSON
    data = load_geojson()
    
    # Step 3: Ingest polygons
    ingest_polygons(data)
    
    print("\n[DONE] Polygon ingestion complete!")


if __name__ == "__main__":
    main()
