"""
Organize Downloaded Data & Enhance AI Agent Integration
- Moves ingested files to data_extra
- Converts formats for system use
- Updates database with GIS layers
- Prepares data for AI agent analysis
"""

import sqlite3
import json
import shutil
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "valora.db"
DATA_EXTRA = BASE_DIR / "storage" / "data_extra"
OPENCITY_DIR = BASE_DIR / "storage" / "opencity_downloads"
GIS_PRIORITY_DIR = BASE_DIR / "storage" / "gis_priority"


def ensure_gis_tables():
    """Create enhanced GIS tables for new data layers."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Ward boundaries table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ward_boundaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_id TEXT UNIQUE,
            ward_name TEXT,
            ward_number INTEGER,
            zone TEXT,
            area_sqkm REAL,
            population INTEGER,
            boundary_geojson TEXT,
            properties TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Land use zones table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS land_use_zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id TEXT UNIQUE,
            zone_type TEXT,
            land_use_category TEXT,
            description TEXT,
            area_sqkm REAL,
            fsi_allowed REAL,
            height_limit REAL,
            boundary_geojson TEXT,
            properties TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Cadastral parcels table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cadastral_parcels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parcel_id TEXT UNIQUE,
            survey_number TEXT,
            village TEXT,
            taluk TEXT,
            district TEXT,
            area_sqm REAL,
            owner_type TEXT,
            land_type TEXT,
            boundary_geojson TEXT,
            properties TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Infrastructure layers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS infrastructure_layers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            layer_id TEXT UNIQUE,
            layer_type TEXT,
            name TEXT,
            category TEXT,
            status TEXT,
            latitude REAL,
            longitude REAL,
            geometry_geojson TEXT,
            properties TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Data catalog - tracks all ingested datasets
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_name TEXT UNIQUE,
            dataset_title TEXT,
            category TEXT,
            source_url TEXT,
            file_format TEXT,
            record_count INTEGER,
            file_size_kb REAL,
            ingested_at TIMESTAMP,
            last_updated TIMESTAMP,
            status TEXT DEFAULT 'active',
            notes TEXT
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ward_name ON ward_boundaries(ward_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_land_use ON land_use_zones(land_use_category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_parcel_survey ON cadastral_parcels(survey_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_infra_type ON infrastructure_layers(layer_type)")
    
    conn.commit()
    conn.close()
    print("✓ GIS tables created/verified")


def ingest_kml_to_geojson(kml_path):
    """Convert KML to GeoJSON-like structure for storage."""
    # Simple KML parser for coordinates
    try:
        with open(kml_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        import re
        coords_pattern = r'<coordinates>(.*?)</coordinates>'
        matches = re.findall(coords_pattern, content, re.DOTALL)
        
        features = []
        for i, coords_str in enumerate(matches):
            coords = []
            for point in coords_str.strip().split():
                parts = point.split(',')
                if len(parts) >= 2:
                    try:
                        lng, lat = float(parts[0]), float(parts[1])
                        coords.append([lng, lat])
                    except:
                        pass
            
            if coords:
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon" if len(coords) > 2 else "Point",
                        "coordinates": [coords] if len(coords) > 2 else coords[0]
                    },
                    "properties": {"id": i}
                })
        
        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        return None


def process_gis_files():
    """Process all downloaded GIS files."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    stats = {"ward": 0, "land_use": 0, "cadastral": 0, "infrastructure": 0, "catalog": 0}
    
    # Process files from both directories
    for data_dir in [OPENCITY_DIR, GIS_PRIORITY_DIR]:
        if not data_dir.exists():
            continue
            
        for filepath in data_dir.glob("*"):
            if filepath.is_dir():
                continue
                
            filename = filepath.name.lower()
            ext = filepath.suffix.lower()
            size_kb = filepath.stat().st_size / 1024
            
            # Catalog all files
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO data_catalog 
                    (dataset_name, file_format, file_size_kb, ingested_at, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (filepath.stem, ext[1:], size_kb, datetime.now(), 'active'))
                stats["catalog"] += 1
            except:
                pass
            
            # Process specific file types
            if 'ward' in filename or 'zone' in filename:
                if ext in ['.geojson', '.json']:
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            data = json.load(f)
                        features = data.get('features', [data] if 'geometry' in data else [])
                        for feat in features:
                            props = feat.get('properties', {})
                            geom = feat.get('geometry', {})
                            cursor.execute("""
                                INSERT OR IGNORE INTO ward_boundaries 
                                (ward_id, ward_name, boundary_geojson, properties, source)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                f"ward_{stats['ward']}",
                                props.get('name', props.get('WARD_NAME', f"Ward {stats['ward']}")),
                                json.dumps(geom),
                                json.dumps(props),
                                filepath.name
                            ))
                            stats["ward"] += 1
                    except:
                        pass
            
            elif 'land' in filename or 'use' in filename or 'master' in filename:
                if ext in ['.geojson', '.json']:
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            data = json.load(f)
                        features = data.get('features', [])
                        for feat in features:
                            props = feat.get('properties', {})
                            geom = feat.get('geometry', {})
                            cursor.execute("""
                                INSERT OR IGNORE INTO land_use_zones 
                                (zone_id, land_use_category, boundary_geojson, properties, source)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                f"lu_{stats['land_use']}",
                                props.get('land_use', props.get('LAND_USE', 'unknown')),
                                json.dumps(geom),
                                json.dumps(props),
                                filepath.name
                            ))
                            stats["land_use"] += 1
                    except:
                        pass
            
            elif 'cadastral' in filename or 'survey' in filename or 'parcel' in filename:
                # Large cadastral files - just catalog them
                stats["cadastral"] += 1
            
            elif any(x in filename for x in ['metro', 'road', 'bus', 'water', 'electric', 'drain']):
                if ext in ['.csv', '.json', '.geojson']:
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO infrastructure_layers 
                            (layer_id, layer_type, name, source)
                            VALUES (?, ?, ?, ?)
                        """, (
                            f"infra_{stats['infrastructure']}",
                            filename.split('_')[0] if '_' in filename else 'infrastructure',
                            filepath.stem,
                            filepath.name
                        ))
                        stats["infrastructure"] += 1
                    except:
                        pass
    
    conn.commit()
    conn.close()
    return stats


def move_processed_to_extra():
    """Move processed files to data_extra for archival."""
    DATA_EXTRA.mkdir(parents=True, exist_ok=True)
    
    moved = 0
    for data_dir in [OPENCITY_DIR, GIS_PRIORITY_DIR]:
        if not data_dir.exists():
            continue
        
        # Create archive subdirectory
        archive_dir = DATA_EXTRA / f"archive_{data_dir.name}"
        archive_dir.mkdir(exist_ok=True)
        
        for filepath in data_dir.glob("*"):
            if filepath.is_file() and filepath.suffix.lower() in ['.csv', '.json', '.geojson']:
                try:
                    dest = archive_dir / filepath.name
                    if not dest.exists():
                        shutil.copy2(filepath, dest)
                        moved += 1
                except:
                    pass
    
    return moved


def generate_data_summary():
    """Generate a summary of all available data."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    summary = {
        "generated_at": datetime.now().isoformat(),
        "tables": {}
    }
    
    tables = [
        "properties", "pois", "buildings", "roads", "transport_stops",
        "ward_boundaries", "land_use_zones", "cadastral_parcels",
        "infrastructure_layers", "aqi_data", "environmental_zones",
        "real_estate_agents", "data_catalog", "open_datasets"
    ]
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            summary["tables"][table] = count
        except:
            pass
    
    conn.close()
    
    # Save summary
    with open(BASE_DIR / "storage" / "data_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    return summary


def main():
    print("=" * 70)
    print("VALORA AI - DATA ORGANIZATION & ENHANCEMENT")
    print("=" * 70)
    
    print("\n[1/5] Creating GIS tables...")
    ensure_gis_tables()
    
    print("\n[2/5] Processing GIS files...")
    stats = process_gis_files()
    print(f"  Wards: {stats['ward']}")
    print(f"  Land Use: {stats['land_use']}")
    print(f"  Cadastral: {stats['cadastral']}")
    print(f"  Infrastructure: {stats['infrastructure']}")
    print(f"  Cataloged: {stats['catalog']}")
    
    print("\n[3/5] Moving processed files to data_extra...")
    moved = move_processed_to_extra()
    print(f"  Moved: {moved} files")
    
    print("\n[4/5] Generating data summary...")
    summary = generate_data_summary()
    
    print("\n[5/5] Data Summary:")
    for table, count in sorted(summary["tables"].items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  {table}: {count:,}")
    
    print("\n" + "=" * 70)
    print("ORGANIZATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
