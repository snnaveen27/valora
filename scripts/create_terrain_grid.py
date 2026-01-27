"""
Create terrain_grid table and populate with basic terrain data for Bangalore region.
"""
import sqlite3
from pathlib import Path
import random

def main():
    db_path = Path(__file__).parent.parent / 'src' / 'data' / 'valora.db'
    
    print(f"Database: {db_path}")
    print("=" * 70)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create terrain_grid table
    print("\n[1/3] Creating terrain_grid table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS terrain_grid (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grid_id TEXT UNIQUE NOT NULL,
            center_lat REAL NOT NULL,
            center_lng REAL NOT NULL,
            elevation_m REAL DEFAULT 920,
            slope_deg REAL DEFAULT 2.0,
            aspect_deg REAL DEFAULT 0,
            flood_risk TEXT DEFAULT 'low',
            terrain_type TEXT DEFAULT 'urban',
            suitability_score REAL DEFAULT 75,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    
    # Check if already populated
    cursor.execute("SELECT COUNT(*) FROM terrain_grid")
    existing = cursor.fetchone()[0]
    
    if existing > 0:
        print(f"      Table already has {existing:,} rows")
        conn.close()
        return
    
    # Generate grid for Bangalore region (12.85-13.10 lat, 77.45-77.80 lng)
    print("\n[2/3] Generating terrain grid for Bangalore...")
    
    grid_size = 0.01  # ~1km grid cells
    rows = []
    
    # Bangalore terrain characteristics
    # - Average elevation: 920m
    # - Higher in south (Bannerghatta), lower in north
    # - Flood-prone areas: Bellandur, Varthur, low-lying areas
    
    flood_prone_areas = [
        (12.93, 77.67),  # Bellandur
        (12.94, 77.74),  # Varthur
        (12.96, 77.64),  # Marathahalli low areas
        (12.91, 77.60),  # Koramangala lake area
    ]
    
    for lat_idx in range(1285, 1310):  # 12.85 to 13.10
        for lng_idx in range(7745, 7780):  # 77.45 to 77.80
            lat = lat_idx / 100
            lng = lng_idx / 100
            grid_id = f"grid_{lat_idx}_{lng_idx}"
            
            # Base elevation (higher in south)
            base_elevation = 920 + (1300 - lat_idx) * 0.5 + random.uniform(-10, 10)
            
            # Slope (steeper near hills)
            slope = 2.0 + random.uniform(0, 3)
            if lat < 12.90:  # Bannerghatta area
                slope += 3
            
            # Aspect (random)
            aspect = random.uniform(0, 360)
            
            # Flood risk
            flood_risk = 'low'
            for fp_lat, fp_lng in flood_prone_areas:
                if abs(lat - fp_lat) < 0.03 and abs(lng - fp_lng) < 0.03:
                    flood_risk = 'high' if random.random() < 0.6 else 'medium'
                    break
            
            # Terrain type
            if lat < 12.88:
                terrain_type = 'hilly'
            elif flood_risk == 'high':
                terrain_type = 'wetland'
            else:
                terrain_type = 'urban'
            
            # Suitability score
            suitability = 75
            if flood_risk == 'high':
                suitability -= 25
            elif flood_risk == 'medium':
                suitability -= 10
            if slope > 5:
                suitability -= 10
            suitability += random.uniform(-5, 5)
            suitability = max(30, min(95, suitability))
            
            rows.append((
                grid_id, lat, lng, base_elevation, slope, aspect,
                flood_risk, terrain_type, suitability
            ))
    
    print(f"      Generated {len(rows):,} grid cells")
    
    # Insert data
    print("\n[3/3] Inserting terrain data...")
    cursor.executemany("""
        INSERT OR IGNORE INTO terrain_grid 
        (grid_id, center_lat, center_lng, elevation_m, slope_deg, aspect_deg,
         flood_risk, terrain_type, suitability_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM terrain_grid")
    final_count = cursor.fetchone()[0]
    
    print(f"\n{'='*70}")
    print(f"✅ COMPLETE: {final_count:,} terrain grid cells created")
    print(f"{'='*70}")
    
    conn.close()

if __name__ == '__main__':
    main()
