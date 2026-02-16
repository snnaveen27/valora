"""
Process ALL remaining backup data and copy files to correct locations.
"""
import json
import sqlite3
import shutil
from pathlib import Path

def get_db_connection():
    db_path = Path(__file__).parent.parent / 'storage' / 'valora.db'
    return sqlite3.connect(str(db_path))

def process_terrain_elevation_index(backup_dir):
    """Process terrain elevation index and update terrain_grid."""
    index_file = backup_dir / 'terrain' / 'elevation_index.json'
    
    if not index_file.exists():
        print("  ❌ elevation_index.json not found")
        return 0
    
    print(f"  Loading {index_file.name}...")
    with open(index_file, 'r') as f:
        data = json.load(f)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updated = 0
    
    # Check structure
    if isinstance(data, dict):
        if 'cells' in data:
            cells = data['cells']
        elif 'grid' in data:
            cells = data['grid']
        else:
            cells = [data]
    elif isinstance(data, list):
        cells = data
    else:
        print(f"  Unknown data format: {type(data)}")
        return 0
    
    print(f"  Found {len(cells) if isinstance(cells, list) else 'N/A'} elevation cells")
    
    if isinstance(cells, list):
        for cell in cells:
            if not isinstance(cell, dict):
                continue
            
            lat = cell.get('lat') or cell.get('center_lat') or cell.get('latitude')
            lng = cell.get('lng') or cell.get('center_lng') or cell.get('longitude')
            elev = cell.get('elevation') or cell.get('elevation_m') or cell.get('elev')
            
            if lat and lng and elev:
                cursor.execute("""
                    UPDATE terrain_grid 
                    SET elevation_m = ?
                    WHERE ABS(center_lat - ?) < 0.01 AND ABS(center_lng - ?) < 0.01
                """, (float(elev), float(lat), float(lng)))
                updated += cursor.rowcount
    
    conn.commit()
    conn.close()
    return updated

def copy_mbtiles(backup_dir, data_dir):
    """Copy MBTiles for offline map tiles."""
    src = backup_dir / 'raw' / 'bengaluru_mb.mbtiles'
    dst = data_dir / 'bengaluru.mbtiles'
    
    if not src.exists():
        print("  ❌ bengaluru_mb.mbtiles not found")
        return False
    
    if dst.exists():
        print(f"  ✓ MBTiles already exists at destination")
        return True
    
    print(f"  Copying {src.stat().st_size / (1024*1024):.1f} MB...")
    shutil.copy2(src, dst)
    print(f"  ✓ Copied to {dst}")
    return True

def copy_tileset_json(backup_dir, data_dir):
    """Copy 3D tileset.json for building tiles."""
    src = backup_dir / '3dtiles' / 'tileset.json'
    dst_dir = data_dir / '3dtiles'
    dst = dst_dir / 'tileset.json'
    
    if not src.exists():
        print("  ❌ tileset.json not found in backup")
        return False
    
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    if dst.exists():
        print(f"  ✓ tileset.json already exists")
        return True
    
    shutil.copy2(src, dst)
    print(f"  ✓ Copied tileset.json to {dst}")
    return True

def copy_terrain_files(backup_dir, data_dir):
    """Copy terrain TIF files."""
    terrain_src = backup_dir / 'terrain'
    terrain_dst = data_dir / 'terrain'
    
    if not terrain_src.exists():
        print("  ❌ terrain folder not found")
        return 0
    
    terrain_dst.mkdir(parents=True, exist_ok=True)
    
    copied = 0
    for tif_file in terrain_src.glob('*.tif'):
        dst_file = terrain_dst / tif_file.name
        if not dst_file.exists():
            print(f"  Copying {tif_file.name} ({tif_file.stat().st_size / (1024*1024):.1f} MB)...")
            shutil.copy2(tif_file, dst_file)
            copied += 1
        else:
            print(f"  ✓ {tif_file.name} already exists")
    
    # Copy elevation_index.json too
    idx_src = terrain_src / 'elevation_index.json'
    idx_dst = terrain_dst / 'elevation_index.json'
    if idx_src.exists() and not idx_dst.exists():
        shutil.copy2(idx_src, idx_dst)
        copied += 1
    
    return copied

def copy_dem_file(backup_dir, data_dir):
    """Copy DEM elevation file."""
    src = backup_dir / 'raw' / 'dem_bengaluru.tif'
    dst_dir = data_dir / 'terrain'
    dst = dst_dir / 'dem_bengaluru.tif'
    
    if not src.exists():
        print("  ❌ dem_bengaluru.tif not found")
        return False
    
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    if dst.exists():
        print(f"  ✓ DEM file already exists")
        return True
    
    print(f"  Copying DEM ({src.stat().st_size / (1024*1024):.1f} MB)...")
    shutil.copy2(src, dst)
    print(f"  ✓ Copied DEM to {dst}")
    return True

def main():
    backup_dir = Path(__file__).parent.parent / 'storage' / 'data_backup'
    data_dir = Path(__file__).parent.parent / 'storage'
    
    print("=" * 70)
    print("PROCESSING ALL BACKUP DATA")
    print("=" * 70)
    
    # 1. Process terrain elevation index
    print("\n[1/5] Processing Terrain Elevation Index...")
    updated = process_terrain_elevation_index(backup_dir)
    print(f"  ✅ Updated {updated} terrain cells with elevation data")
    
    # 2. Copy MBTiles
    print("\n[2/5] Copying MBTiles for Offline Maps...")
    copy_mbtiles(backup_dir, data_dir)
    
    # 3. Copy 3D tileset
    print("\n[3/5] Copying 3D Tileset Configuration...")
    copy_tileset_json(backup_dir, data_dir)
    
    # 4. Copy terrain files
    print("\n[4/5] Copying Terrain TIF Files...")
    copied = copy_terrain_files(backup_dir, data_dir)
    print(f"  ✅ Copied {copied} terrain files")
    
    # 5. Copy DEM file
    print("\n[5/5] Copying DEM Elevation File...")
    copy_dem_file(backup_dir, data_dir)
    
    print("\n" + "=" * 70)
    print("✅ ALL BACKUP DATA PROCESSED")
    print("=" * 70)

if __name__ == '__main__':
    main()
