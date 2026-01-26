"""
Ingest GeoJSON data from osm_extracted folder into database
Populates pois, places, and transport_stops tables
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database.db_service import DatabaseService


def ingest_pois(db: DatabaseService, geojson_path: Path) -> int:
    """Ingest POIs from GeoJSON file."""
    print(f"\n{'='*70}")
    print(f"INGESTING POIs FROM: {geojson_path.name}")
    print('='*70)
    
    if not geojson_path.exists():
        print(f"[WARNING] File not found: {geojson_path}")
        return 0
    
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    print(f"[INFO] Found {len(features):,} POI features")
    
    pois_batch = []
    
    for feature in features:
        props = feature.get('properties', {})
        geom = feature.get('geometry', {})
        coords = geom.get('coordinates', [0, 0])
        
        # Extract basic info
        poi_id = props.get('id') or props.get('osm_id') or f"osm_{len(pois_batch)}"
        name = props.get('name') or 'Unnamed'
        category = props.get('amenity') or props.get('shop') or props.get('tourism') or props.get('leisure') or 'other'
        subcategory = props.get('cuisine') or props.get('sport') or ''
        
        # Skip if no valid coordinates
        if not coords or len(coords) < 2:
            continue
        
        poi = {
            'poi_id': str(poi_id),
            'source': 'osm',
            'name': str(name)[:200] if name else 'Unnamed',
            'category': str(category)[:100] if category else 'other',
            'subcategory': str(subcategory)[:100] if subcategory else '',
            'latitude': coords[1] if len(coords) > 1 else None,
            'longitude': coords[0] if len(coords) > 0 else None,
            'address': props.get('addr:full', '') or props.get('address', ''),
            'locality': props.get('addr:suburb', ''),
            'area_name': props.get('addr:neighbourhood', ''),
            'phone': props.get('phone', ''),
            'website': props.get('website', ''),
            'opening_hours': props.get('opening_hours', ''),
            'source_data': json.dumps(props)
        }
        
        pois_batch.append(poi)
        
        # Batch insert
        if len(pois_batch) >= 1000:
            try:
                db.insert_many('pois', pois_batch)
                print(f"  Inserted {len(pois_batch):,} POIs...")
            except Exception as e:
                print(f"[ERROR] Failed to insert batch: {e}")
            pois_batch = []
    
    # Insert remaining
    if pois_batch:
        try:
            db.insert_many('pois', pois_batch)
            print(f"  Inserted {len(pois_batch):,} POIs...")
        except Exception as e:
            print(f"[ERROR] Failed to insert final batch: {e}")
    
    # Get final count
    result = db.execute("SELECT COUNT(*) as count FROM pois")
    total = result[0]['count'] if result else 0
    
    print(f"[OK] Total POIs in database: {total:,}")
    return total


def ingest_places(db: DatabaseService, geojson_path: Path) -> int:
    """Ingest places from GeoJSON file."""
    print(f"\n{'='*70}")
    print(f"INGESTING PLACES FROM: {geojson_path.name}")
    print('='*70)
    
    if not geojson_path.exists():
        print(f"[WARNING] File not found: {geojson_path}")
        return 0
    
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    print(f"[INFO] Found {len(features):,} place features")
    
    places_batch = []
    
    for feature in features:
        props = feature.get('properties', {})
        geom = feature.get('geometry', {})
        coords = geom.get('coordinates', [0, 0])
        
        # Extract centroid for polygons
        if geom.get('type') == 'Polygon' and coords:
            # Simple centroid calculation
            lngs = [c[0] for ring in coords for c in ring]
            lats = [c[1] for ring in coords for c in ring]
            center_lng = sum(lngs) / len(lngs) if lngs else 0
            center_lat = sum(lats) / len(lats) if lats else 0
        elif geom.get('type') == 'Point':
            center_lng = coords[0]
            center_lat = coords[1]
        else:
            center_lng = 0
            center_lat = 0
        
        place_id = props.get('id') or props.get('osm_id') or f"place_{len(places_batch)}"
        name = props.get('name', 'Unnamed')
        place_type = props.get('place') or props.get('boundary') or props.get('admin_level') or 'neighbourhood'
        
        # Parse population
        population = 0
        pop_str = props.get('population', '0')
        if isinstance(pop_str, (int, float)):
            population = int(pop_str)
        elif isinstance(pop_str, str):
            # Handle ">5,000" format
            pop_str = pop_str.replace('>', '').replace(',', '').strip()
            try:
                population = int(pop_str)
            except:
                population = 0
        
        place = {
            'place_id': str(place_id),
            'source': 'osm',
            'name': str(name)[:200] if name else 'Unnamed',
            'display_name': str(props.get('display_name') or name or 'Unnamed')[:300],
            'place_type': str(place_type)[:100] if place_type else 'neighbourhood',
            'parent_place': props.get('addr:city', '') or props.get('is_in', ''),
            'center_latitude': center_lat,
            'center_longitude': center_lng,
            'population': population,
            'attributes': json.dumps(props)
        }
        
        places_batch.append(place)
        
        if len(places_batch) >= 500:
            try:
                db.insert_many('places', places_batch)
                print(f"  Inserted {len(places_batch):,} places...")
            except Exception as e:
                print(f"[ERROR] Failed to insert batch: {e}")
            places_batch = []
    
    if places_batch:
        try:
            db.insert_many('places', places_batch)
            print(f"  Inserted {len(places_batch):,} places...")
        except Exception as e:
            print(f"[ERROR] Failed to insert final batch: {e}")
    
    result = db.execute("SELECT COUNT(*) as count FROM places")
    total = result[0]['count'] if result else 0
    
    print(f"[OK] Total places in database: {total:,}")
    return total


def ingest_transport(db: DatabaseService, geojson_path: Path) -> int:
    """Ingest transport stops from GeoJSON file."""
    print(f"\n{'='*70}")
    print(f"INGESTING TRANSPORT FROM: {geojson_path.name}")
    print('='*70)
    
    if not geojson_path.exists():
        print(f"[WARNING] File not found: {geojson_path}")
        return 0
    
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    print(f"[INFO] Found {len(features):,} transport features")
    
    transport_batch = []
    
    for feature in features:
        props = feature.get('properties', {})
        geom = feature.get('geometry', {})
        coords = geom.get('coordinates', [0, 0])
        
        stop_id = props.get('id') or props.get('osm_id') or f"transport_{len(transport_batch)}"
        name = props.get('name', 'Unnamed')
        
        # Determine transport type
        transport_type = 'unknown'
        if props.get('railway'):
            transport_type = 'metro' if 'metro' in str(props.get('railway')).lower() else 'train'
        elif props.get('highway') == 'bus_stop':
            transport_type = 'bus'
        elif props.get('amenity') == 'bus_station':
            transport_type = 'bus'
        elif props.get('public_transport'):
            transport_type = str(props.get('public_transport'))
        
        line_name = props.get('line', '') or props.get('ref', '')
        
        # Ensure all fields are strings
        name_str = str(name) if name else 'Unnamed'
        transport_type_str = str(transport_type) if transport_type else 'unknown'
        line_name_str = str(line_name) if line_name else ''
        
        stop = {
            'stop_id': str(stop_id),
            'source': 'osm',
            'name': name_str[:200],
            'transport_type': transport_type_str[:100],
            'line_name': line_name_str[:100],
            'latitude': coords[1] if len(coords) > 1 else None,
            'longitude': coords[0] if len(coords) > 0 else None,
            'address': str(props.get('addr:full') or ''),
            'area_name': str(props.get('addr:neighbourhood') or ''),
            'operational': 1,
            'attributes': json.dumps(props)
        }
        
        transport_batch.append(stop)
        
        if len(transport_batch) >= 500:
            try:
                db.insert_many('transport_stops', transport_batch)
                print(f"  Inserted {len(transport_batch):,} stops...")
            except Exception as e:
                print(f"[ERROR] Failed to insert batch: {e}")
            transport_batch = []
    
    if transport_batch:
        try:
            db.insert_many('transport_stops', transport_batch)
            print(f"  Inserted {len(transport_batch):,} stops...")
        except Exception as e:
            print(f"[ERROR] Failed to insert final batch: {e}")
    
    result = db.execute("SELECT COUNT(*) as count FROM transport_stops")
    total = result[0]['count'] if result else 0
    
    print(f"[OK] Total transport stops in database: {total:,}")
    return total


def main():
    """Main ingestion process."""
    print("\n" + "="*70)
    print("VALORA DATABASE - GEOJSON INGESTION")
    print("="*70)
    
    # Initialize database
    db_path = Path(__file__).parent.parent.parent / 'src' / 'data' / 'valora.db'
    data_dir = Path(__file__).parent.parent.parent / 'src' / 'data' / 'osm_extracted'
    
    db = DatabaseService(str(db_path))
    
    # Ensure schema exists
    print("\n[INFO] Ensuring database schema...")
    db.initialize_schema(force=False)
    
    # Clear existing data
    print("\n[INFO] Clearing existing POI/Place/Transport data...")
    try:
        db.execute("DELETE FROM pois")
        db.execute("DELETE FROM places")
        db.execute("DELETE FROM transport_stops")
        print("[OK] Cleared existing data")
    except Exception as e:
        print(f"[WARNING] Could not clear data: {e}")
    
    # Ingest data
    pois_count = ingest_pois(db, data_dir / 'pois.geojson')
    places_count = ingest_places(db, data_dir / 'places.geojson')
    transport_count = ingest_transport(db, data_dir / 'transport.geojson')
    
    # Summary
    print("\n" + "="*70)
    print("INGESTION COMPLETE")
    print("="*70)
    print(f"POIs: {pois_count:,}")
    print(f"Places: {places_count:,}")
    print(f"Transport Stops: {transport_count:,}")
    print(f"Total: {pois_count + places_count + transport_count:,}")
    print()


if __name__ == "__main__":
    main()
