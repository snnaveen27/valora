"""
Extract roads from OSM PBF file using Python osmium library.
"""
import osmium
import json
import sqlite3
from pathlib import Path
from collections import defaultdict

class RoadHandler(osmium.SimpleHandler):
    """Handler to extract road data from OSM PBF."""
    
    def __init__(self):
        super().__init__()
        self.roads = []
        self.node_coords = {}  # Store node coordinates for way geometry
        
    def node(self, n):
        """Store node coordinates."""
        self.node_coords[n.id] = (n.location.lon, n.location.lat)
    
    def way(self, w):
        """Extract highway ways."""
        if 'highway' not in w.tags:
            return
        
        # Get coordinates for this way
        coords = []
        for node in w.nodes:
            if node.ref in self.node_coords:
                coords.append(self.node_coords[node.ref])
        
        if len(coords) < 2:
            return
        
        road = {
            'osm_id': w.id,
            'name': w.tags.get('name', ''),
            'highway': w.tags.get('highway', 'unknown'),
            'surface': w.tags.get('surface', ''),
            'lanes': w.tags.get('lanes', ''),
            'oneway': w.tags.get('oneway', 'no'),
            'maxspeed': w.tags.get('maxspeed', ''),
            'ref': w.tags.get('ref', ''),
            'start_lng': coords[0][0],
            'start_lat': coords[0][1],
            'end_lng': coords[-1][0],
            'end_lat': coords[-1][1],
            'num_points': len(coords)
        }
        
        self.roads.append(road)

def extract_roads(pbf_path):
    """Extract roads from PBF file."""
    print(f"  Reading PBF file: {pbf_path}")
    print(f"  File size: {pbf_path.stat().st_size / (1024*1024):.1f} MB")
    
    handler = RoadHandler()
    
    # First pass: collect node coordinates
    print("  Pass 1: Collecting node coordinates...")
    handler.apply_file(str(pbf_path), locations=True)
    
    print(f"  Extracted {len(handler.roads):,} roads")
    return handler.roads

def ingest_roads_to_db(roads, db_path):
    """Insert roads into database."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Ensure roads table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            road_id TEXT UNIQUE,
            name TEXT,
            road_type TEXT,
            surface TEXT,
            lanes INTEGER,
            oneway BOOLEAN,
            max_speed INTEGER,
            ref_code TEXT,
            start_lat REAL,
            start_lng REAL,
            end_lat REAL,
            end_lng REAL,
            num_points INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check existing count
    cursor.execute("SELECT COUNT(*) FROM roads")
    existing = cursor.fetchone()[0]
    print(f"  Existing roads in DB: {existing:,}")
    
    inserted = 0
    skipped = 0
    
    for road in roads:
        road_id = f"osm_{road['osm_id']}"
        
        # Parse lanes
        lanes = None
        if road['lanes']:
            try:
                lanes = int(road['lanes'])
            except:
                pass
        
        # Parse maxspeed
        maxspeed = None
        if road['maxspeed']:
            try:
                maxspeed = int(str(road['maxspeed']).replace('km/h', '').replace('mph', '').strip())
            except:
                pass
        
        # Parse oneway
        oneway = road['oneway'].lower() in ['yes', '1', 'true']
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO roads 
                (road_id, name, road_type, surface, lanes, oneway, max_speed, ref_code,
                 start_lat, start_lng, end_lat, end_lng, num_points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                road_id,
                road['name'],
                road['highway'],
                road['surface'],
                lanes,
                oneway,
                maxspeed,
                road['ref'],
                road['start_lat'],
                road['start_lng'],
                road['end_lat'],
                road['end_lng'],
                road['num_points']
            ))
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            skipped += 1
        
        if (inserted + skipped) % 10000 == 0:
            conn.commit()
            print(f"    Progress: {inserted + skipped:,} processed ({inserted:,} inserted)")
    
    conn.commit()
    
    # Final count
    cursor.execute("SELECT COUNT(*) FROM roads")
    final = cursor.fetchone()[0]
    
    conn.close()
    return inserted, final

def main():
    # Check for PBF file in multiple locations
    project_root = Path(__file__).parent.parent
    possible_paths = [
        project_root / 'src' / 'data' / 'data_backup_temp' / 'raw' / 'bengaluru.pbf',
        project_root / 'src' / 'data' / 'data_backup' / 'raw' / 'bengaluru.pbf',
        project_root / 'src' / 'data' / 'raw' / 'bengaluru.pbf',
        project_root / 'src' / 'data' / 'bengaluru.pbf',
    ]
    
    pbf_path = None
    for p in possible_paths:
        if p.exists():
            pbf_path = p
            break
    
    if not pbf_path:
        print("❌ PBF file not found!")
        print("Please place bengaluru.pbf in one of these locations:")
        for p in possible_paths:
            print(f"  - {p}")
        return
    
    db_path = project_root / 'src' / 'data' / 'valora.db'
    
    print("=" * 70)
    print("ROAD EXTRACTION FROM OSM PBF (Python)")
    print("=" * 70)
    
    print(f"\nPBF: {pbf_path}")
    print(f"Database: {db_path}")
    
    print("\n[1/2] Extracting roads from PBF...")
    try:
        roads = extract_roads(pbf_path)
    except Exception as e:
        print(f"❌ Error extracting roads: {e}")
        print("\nThis might be because the osmium Python library needs additional setup.")
        print("Try installing: pip install osmium")
        return
    
    if not roads:
        print("❌ No roads extracted")
        return
    
    print(f"\n[2/2] Inserting {len(roads):,} roads into database...")
    inserted, total = ingest_roads_to_db(roads, db_path)
    
    print(f"\n{'='*70}")
    print(f"✅ COMPLETE")
    print(f"   Inserted: {inserted:,} new roads")
    print(f"   Total roads in DB: {total:,}")
    print(f"{'='*70}")
    
    # Show road type distribution
    road_types = defaultdict(int)
    for road in roads:
        road_types[road['highway']] += 1
    
    print("\nRoad types extracted:")
    for rt, count in sorted(road_types.items(), key=lambda x: -x[1])[:15]:
        print(f"  {rt:20} {count:>8,}")

if __name__ == '__main__':
    main()
