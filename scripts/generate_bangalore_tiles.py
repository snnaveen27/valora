#!/usr/bin/env python3
"""
Generate pre-built Bangalore tiles for production deployment
This script exports all building tiles from database to individual JSON files
for fast static serving.

Usage:
    python scripts/generate_bangalore_tiles.py
    
Output:
    storage/tiles/bangalore/ - Individual tile JSON files
"""

import json
import sqlite3
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# Configuration
DB_PATH = Path(__file__).parent.parent / "storage" / "database" / "valora.db"
OUTPUT_DIR = Path(__file__).parent.parent / "storage" / "tiles" / "bangalore"
TILE_SIZE = 0.01  # 0.01 degrees ≈ 1km

# Bangalore extended bounds (approximate)
LNG_RANGE = range(7740, 7780)  # 77.40 to 77.80
LAT_RANGE = range(1280, 1310)  # 12.80 to 13.10


def get_db_connection():
    """Create database connection"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def generate_tile(tile_id: str, lng_start: int, lat_start: int) -> dict:
    """Generate a single tile from database"""
    try:
        lng = lng_start / 100
        lat = lat_start / 100
        min_lng = lng
        max_lng = lng + TILE_SIZE
        min_lat = lat
        max_lat = lat + TILE_SIZE
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query buildings in tile bounds
        cursor.execute("""
            SELECT osm_id, name, building_type, height, levels, 
                   latitude as lat, longitude as lng, polygon_coords
            FROM buildings
            WHERE latitude IS NOT NULL
              AND longitude IS NOT NULL
              AND latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
            LIMIT 5000
        """, (min_lat, max_lat, min_lng, max_lng))
        
        buildings = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Convert to GeoJSON features
        features = []
        for b in buildings:
            # Default height if not specified
            height = max(b.get('height') or 10, 3)
            
            # Check for polygon coordinates
            polygon_coords = b.get('polygon_coords')
            if polygon_coords:
                try:
                    import json
                    coords = json.loads(polygon_coords)
                    # Ensure closed polygon
                    if coords and coords[0] != coords[-1]:
                        coords.append(coords[0])
                    geometry = {
                        "type": "Polygon",
                        "coordinates": [coords]
                    }
                except:
                    # Fallback to point if polygon is invalid
                    geometry = {
                        "type": "Point", 
                        "coordinates": [b['lng'], b['lat']]
                    }
            else:
                geometry = {
                    "type": "Point",
                    "coordinates": [b['lng'], b['lat']]
                }
            
            # Create feature
            feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "osm_id": b.get('osm_id'),
                    "name": b.get('name'),
                    "building": b.get('building_type') or 'building',
                    "height": height,
                    "levels": b.get('levels') or max(1, round(height / 3)),
                    "type": b.get('building_type') or 'building'
                }
            }
            features.append(feature)
        
        # Create tile GeoJSON
        tile_data = {
            "type": "FeatureCollection",
            "tile_id": tile_id,
            "bounds": {
                "min_lng": min_lng,
                "max_lng": max_lng,
                "min_lat": min_lat,
                "max_lat": max_lat
            },
            "count": len(features),
            "features": features
        }
        
        return {
            "tile_id": tile_id,
            "success": True,
            "data": tile_data,
            "count": len(features)
        }
        
    except Exception as e:
        return {
            "tile_id": tile_id,
            "success": False,
            "error": str(e),
            "count": 0
        }


def save_tile(tile_result: dict):
    """Save tile to disk"""
    if not tile_result["success"]:
        return False
    
    tile_path = OUTPUT_DIR / f"{tile_result['tile_id']}.json"
    with open(tile_path, 'w') as f:
        json.dump(tile_result["data"], f)
    return True


def main():
    print("=" * 60)
    print("Bangalore Tile Generation")
    print("=" * 60)
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Check database
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)
    
    # Count total buildings
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM buildings WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    total_buildings = cursor.fetchone()['cnt']
    conn.close()
    print(f"Total buildings in database: {total_buildings:,}")
    
    # Generate tile list
    tiles_to_generate = []
    for lng_start in LNG_RANGE:
        for lat_start in LAT_RANGE:
            tile_id = f"{lng_start}_{lat_start}"
            tiles_to_generate.append((tile_id, lng_start, lat_start))
    
    total_tiles = len(tiles_to_generate)
    print(f"Total tiles to generate: {total_tiles}")
    print()
    
    # Generate tiles in parallel
    print("Generating tiles...")
    success_count = 0
    building_count = 0
    
    # Use multiprocessing for faster generation
    cpu_count = multiprocessing.cpu_count()
    workers = min(cpu_count, 8)  # Limit to 8 workers to avoid overwhelming the DB
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        future_to_tile = {
            executor.submit(generate_tile, tile_id, lng, lat): tile_id 
            for tile_id, lng, lat in tiles_to_generate
        }
        
        # Process results as they complete
        for i, future in enumerate(as_completed(future_to_tile)):
            result = future.result()
            tile_id = result["tile_id"]
            
            if result["success"]:
                save_tile(result)
                success_count += 1
                building_count += result["count"]
                
                if result["count"] > 0:
                    print(f"  [OK] {tile_id}: {result['count']:,} buildings")
            else:
                print(f"  [ERR] {tile_id}: {result.get('error', 'Unknown')}")
            
            # Progress update every 50 tiles
            if (i + 1) % 50 == 0:
                print(f"  ... Progress: {i + 1}/{total_tiles} tiles ({(i + 1) / total_tiles * 100:.1f}%)")
    
    print()
    print("=" * 60)
    print("Generation Complete")
    print("=" * 60)
    print(f"Tiles generated: {success_count}/{total_tiles}")
    print(f"Total buildings exported: {building_count:,}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    # Generate manifest
    manifest = {
        "region": "bangalore",
        "total_tiles": success_count,
        "total_buildings": building_count,
        "bounds": {
            "min_lng": 77.40,
            "max_lng": 77.80,
            "min_lat": 12.80,
            "max_lat": 13.10
        },
        "tile_size_degrees": TILE_SIZE,
        "generated_at": str(Path(__file__).stat().st_mtime)
    }
    
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Manifest saved to: {manifest_path}")
    print()
    print("To serve tiles statically, configure your web server to serve:")
    print(f"  {OUTPUT_DIR}/<tile_id>.json")
    print()


if __name__ == "__main__":
    main()
