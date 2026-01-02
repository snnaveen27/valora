#!/usr/bin/env python
"""
Property Data Loader
Load all organized property files into the database
"""

import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import hashlib

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.database.multiconnection import mdb
import sqlalchemy as sa
from sqlalchemy import text

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_property_csv(csv_path: Path, property_type: str) -> int:
    """Load a single property CSV file"""
    try:
        logger.info(f"Loading {csv_path.name}...")
        df = pd.read_csv(csv_path)
        
        if df.empty:
            logger.warning(f"Empty file: {csv_path.name}")
            return 0
        
        # Standardize column names
        df.columns = df.columns.str.lower().str.strip()
        
        loaded_count = 0
        
        with mdb.spatial() as session:
            for idx, row in df.iterrows():
                try:
                    # Extract coordinates from location column or individual columns
                    lat, lon = None, None
                    
                    if 'location' in df.columns and not pd.isna(row.get('location')):
                        # Parse "lat,lon" format
                        location_str = str(row['location'])
                        if ',' in location_str:
                            parts = location_str.split(',')
                            try:
                                lat = float(parts[0].strip())
                                lon = float(parts[1].strip())
                            except:
                                pass
                    
                    # Fallback to individual columns
                    if lat is None:
                        lat = row.get('latitude') or row.get('lat')
                    if lon is None:
                        lon = row.get('longitude') or row.get('lon') or row.get('lng')
                    
                    if pd.isna(lat) or pd.isna(lon) or lat is None or lon is None:
                        continue
                    
                    # Generate property ID from key fields
                    prop_key = f"{row.get('name', '')}|{lat}|{lon}|{row.get('price', 0)}"
                    property_id = hashlib.sha256(prop_key.encode()).hexdigest()[:32]
                    
                    # Insert into property_locations
                    session.execute(text("""
                        INSERT INTO property_locations (
                            property_id, location, city, locality, 
                            created_at, updated_at
                        )
                        VALUES (
                            :pid, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 
                            :city, :locality, NOW(), NOW()
                        )
                        ON CONFLICT (property_id) DO UPDATE SET
                            updated_at = NOW(),
                            location = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                    """), {
                        "pid": property_id,
                        "lat": float(lat),
                        "lon": float(lon),
                        "city": row.get('city_name', row.get('city', 'Bangalore')),
                        "locality": row.get('locality', row.get('address', 'Unknown'))
                    })
                    
                    loaded_count += 1
                    
                    if loaded_count % 100 == 0:
                        session.commit()
                        logger.info(f"  Loaded {loaded_count} properties...")
                
                except Exception as e:
                    logger.error(f"Error loading row {idx}: {e}")
                    continue
            
            session.commit()
        
        logger.info(f"✅ Loaded {loaded_count} properties from {csv_path.name}")
        return loaded_count
        
    except Exception as e:
        logger.error(f"❌ Error loading {csv_path.name}: {e}")
        return 0


def determine_property_type(file_path: Path) -> str:
    """Determine property type from file path"""
    path_str = str(file_path).lower()
    
    if 'flat' in path_str or 'apartment' in path_str:
        return 'flat'
    elif 'house' in path_str:
        return 'house'
    elif 'villa' in path_str:
        return 'villa'
    elif 'plot' in path_str:
        return 'plot'
    elif 'office' in path_str:
        return 'office'
    elif 'shop' in path_str or 'showroom' in path_str:
        return 'shop'
    elif 'warehouse' in path_str or 'godown' in path_str:
        return 'warehouse'
    elif 'industrial' in path_str:
        return 'industrial'
    elif 'agricultural' in path_str:
        return 'agricultural'
    elif 'farmhouse' in path_str:
        return 'farmhouse'
    else:
        return 'residential'


def create_tables_if_not_exist():
    """Ensure required tables exist"""
    logger.info("Checking database tables...")
    
    with mdb.spatial() as session:
        # Add city and locality columns if they don't exist
        try:
            session.execute(text("""
                ALTER TABLE property_locations 
                ADD COLUMN IF NOT EXISTS city VARCHAR(100),
                ADD COLUMN IF NOT EXISTS locality VARCHAR(200)
            """))
            session.commit()
            logger.info("✅ Ensured city and locality columns exist")
        except Exception as e:
            logger.warning(f"Could not add columns: {e}")


def compute_spatial_features():
    """Compute spatial features for loaded properties"""
    logger.info("\n🔄 Computing spatial features...")
    
    with mdb.spatial() as session:
        # Upsert spatial features
        result = session.execute(text("""
            INSERT INTO property_spatial_features (
                property_id, 
                nearest_poi_distance,
                poi_density_1km,
                poi_density_3km,
                created_at,
                updated_at
            )
            SELECT 
                pl.property_id,
                (SELECT MIN(ST_Distance(pl.location::geography, p.location::geography))
                 FROM pois p) as nearest_poi_distance,
                (SELECT COUNT(*) FROM pois p 
                 WHERE ST_DWithin(pl.location::geography, p.location::geography, 1000)) as poi_density_1km,
                (SELECT COUNT(*) FROM pois p 
                 WHERE ST_DWithin(pl.location::geography, p.location::geography, 3000)) as poi_density_3km,
                NOW(),
                NOW()
            FROM property_locations pl
            WHERE NOT EXISTS (
                SELECT 1 FROM property_spatial_features psf 
                WHERE psf.property_id = pl.property_id
            )
            ON CONFLICT (property_id) DO UPDATE SET
                updated_at = NOW(),
                nearest_poi_distance = EXCLUDED.nearest_poi_distance,
                poi_density_1km = EXCLUDED.poi_density_1km,
                poi_density_3km = EXCLUDED.poi_density_3km
        """))
        
        session.commit()
        count = result.rowcount
        logger.info(f"✅ Computed spatial features for {count} properties")


def main():
    """Main loader function"""
    logger.info("=" * 80)
    logger.info("Property Data Loader")
    logger.info("=" * 80)
    
    # Create tables if needed
    create_tables_if_not_exist()
    
    # Find all property CSV files
    properties_dir = Path("data/raw/properties")
    csv_files = []
    
    for subfolder in ['residential', 'commercial', 'other']:
        subfolder_path = properties_dir / subfolder
        if subfolder_path.exists():
            csv_files.extend(list(subfolder_path.rglob("*.csv")))
    
    logger.info(f"\nFound {len(csv_files)} CSV files to process\n")
    
    total_loaded = 0
    
    # Load each file
    for csv_file in csv_files:
        property_type = determine_property_type(csv_file)
        count = load_property_csv(csv_file, property_type)
        total_loaded += count
    
    logger.info("\n" + "=" * 80)
    logger.info(f"✅ TOTAL LOADED: {total_loaded} properties")
    logger.info("=" * 80)
    
    # Compute spatial features
    if total_loaded > 0:
        compute_spatial_features()
    
    # Show summary
    logger.info("\n📊 Database Summary:")
    with mdb.spatial() as session:
        result = session.execute(text("SELECT COUNT(*) FROM property_locations"))
        total = result.scalar()
        logger.info(f"   Total properties in DB: {total}")
        
        result = session.execute(text("SELECT COUNT(DISTINCT city) FROM property_locations"))
        cities = result.scalar()
        logger.info(f"   Cities: {cities}")
        
        result = session.execute(text("SELECT COUNT(*) FROM property_spatial_features"))
        features = result.scalar()
        logger.info(f"   Spatial features computed: {features}")
    
    logger.info("\n🎉 Property loading complete!")


if __name__ == "__main__":
    main()
