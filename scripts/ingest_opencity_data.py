"""
Ingest downloaded OpenCity.in datasets into Valora database.
"""

import sqlite3
import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "src" / "data" / "valora.db"
OPENCITY_DIR = BASE_DIR / "src" / "data" / "opencity_downloads"


def ingest_schools():
    """Ingest BBMP schools data."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    count = 0
    
    # BBMP Schools (main file)
    for schools_file in OPENCITY_DIR.glob("bengaluru-schools*.csv"):
        try:
            with open(schools_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('School Name') or row.get('School_Name') or row.get('school_name') or row.get('Name', '')
                    if not name:
                        continue
                    
                    ward = row.get('Block') or row.get('Ward_Name') or row.get('ward') or ''
                    address = row.get('Address') or row.get('address') or ''
                    coords = row.get('Coordinates', '')
                    
                    # Parse coordinates if available (POINT(lng lat) format)
                    lat, lng = None, None
                    if coords and 'POINT' in coords:
                        try:
                            coords_clean = coords.replace('POINT(', '').replace(')', '')
                            lng, lat = map(float, coords_clean.split())
                        except:
                            pass
                    
                    poi_id = f"opencity_school_{count}"
                    source_data = json.dumps(row)
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO pois 
                        (poi_id, name, category, subcategory, latitude, longitude, source, source_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (poi_id, name, 'school', f'BBMP School - {ward}', lat, lng, 'opencity', source_data))
                    count += 1
            print(f"  ✓ Processed {schools_file.name}: {count} total")
        except Exception as e:
            print(f"  ❌ Schools error: {e}")
    
    conn.commit()
    conn.close()
    return count


def ingest_hospitals():
    """Ingest BBMP hospitals data."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    count = 0
    
    hospital_files = list(OPENCITY_DIR.glob("bengaluru-hospitals*.csv"))
    
    for file_path in hospital_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('Hospital_Name') or row.get('Name') or row.get('name', '')
                    if not name:
                        continue
                    
                    ward = row.get('Ward') or row.get('ward') or ''
                    address = row.get('Address') or row.get('address') or ''
                    
                    poi_id = f"opencity_hospital_{count}"
                    source_data = json.dumps(row)
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO pois 
                        (poi_id, name, category, subcategory, source, source_data)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (poi_id, name, 'hospital', f'BBMP Hospital - {ward}', 'opencity', source_data))
                    count += 1
        except Exception as e:
            print(f"  ❌ Hospital file error: {e}")
    
    print(f"  ✓ Hospitals: {count}")
    conn.commit()
    conn.close()
    return count


def ingest_toilets():
    """Ingest public toilets data."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    count = 0
    
    toilets_file = OPENCITY_DIR / "bengaluru-public-toilets_BBMP_Existing_Toilets.csv"
    if toilets_file.exists():
        try:
            with open(toilets_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    location = row.get('Location') or row.get('location') or row.get('Address', '')
                    ward = row.get('Ward') or row.get('ward') or ''
                    
                    name = f"Public Toilet - {location[:50]}" if location else f"Public Toilet #{count}"
                    
                    poi_id = f"opencity_toilet_{count}"
                    source_data = json.dumps(row)
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO pois 
                        (poi_id, name, category, subcategory, source, source_data)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (poi_id, name, 'toilet', f'Public Toilet - {ward}', 'opencity', source_data))
                    count += 1
            print(f"  ✓ Toilets: {count}")
        except Exception as e:
            print(f"  ❌ Toilets error: {e}")
    
    conn.commit()
    conn.close()
    return count


def ingest_canteens():
    """Ingest Indira Canteens data."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    count = 0
    
    canteens_file = OPENCITY_DIR / "bengaluru-indira-canteens_Indira_Canteens_List_2023.csv"
    if canteens_file.exists():
        try:
            with open(canteens_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    location = row.get('Location') or row.get('location') or row.get('Address', '')
                    ward = row.get('Ward') or row.get('ward') or ''
                    
                    name = f"Indira Canteen - {ward}" if ward else f"Indira Canteen - {location[:30]}"
                    
                    poi_id = f"opencity_canteen_{count}"
                    source_data = json.dumps(row)
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO pois 
                        (poi_id, name, category, subcategory, source, source_data)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (poi_id, name, 'restaurant', 'Indira Canteen', 'opencity', source_data))
                    count += 1
            print(f"  ✓ Canteens: {count}")
        except Exception as e:
            print(f"  ❌ Canteens error: {e}")
    
    conn.commit()
    conn.close()
    return count


def ingest_slums():
    """Ingest urban slums data."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    count = 0
    
    slums_file = OPENCITY_DIR / "bengaluru-urban-slums_Bengaluru_List_of_Slums_with_Amenities_-_2011.csv"
    if slums_file.exists():
        try:
            with open(slums_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('Slum_Name') or row.get('Name') or row.get('name', '')
                    if not name:
                        continue
                    
                    ward = row.get('Ward') or row.get('ward') or ''
                    
                    # Store in a separate table for slums
                    cursor.execute("""
                        INSERT OR IGNORE INTO open_datasets 
                        (dataset_id, dataset_name, category, data_type, raw_data)
                        VALUES (?, ?, ?, ?, ?)
                    """, (f"slum_{count}", name, 'urban_slum', 'location', json.dumps(row)))
                    count += 1
            print(f"  ✓ Slums: {count}")
        except Exception as e:
            print(f"  ❌ Slums error: {e}")
    
    conn.commit()
    conn.close()
    return count


def ingest_streetlights():
    """Ingest streetlights data."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    count = 0
    
    for file_path in OPENCITY_DIR.glob("bengaluru-streetlights*.csv"):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ward = row.get('Ward') or row.get('ward') or row.get('Ward_Name', '')
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO open_datasets 
                        (dataset_id, dataset_name, category, data_type, raw_data)
                        VALUES (?, ?, ?, ?, ?)
                    """, (f"streetlight_{count}", f"Streetlight - {ward}", 'infrastructure', 'streetlight', json.dumps(row)))
                    count += 1
        except Exception as e:
            print(f"  ❌ Streetlight file error: {e}")
    
    print(f"  ✓ Streetlights: {count}")
    conn.commit()
    conn.close()
    return count


def ingest_trees():
    """Ingest trees data."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    count = 0
    
    for file_path in OPENCITY_DIR.glob("bengaluru-trees*.csv"):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    species = row.get('Species') or row.get('Tree_Name') or row.get('tree', '')
                    location = row.get('Location') or row.get('Ward') or ''
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO open_datasets 
                        (dataset_id, dataset_name, category, data_type, raw_data)
                        VALUES (?, ?, ?, ?, ?)
                    """, (f"tree_{count}", f"{species} - {location}"[:100], 'environment', 'tree', json.dumps(row)))
                    count += 1
        except Exception as e:
            print(f"  ❌ Trees file error: {e}")
    
    print(f"  ✓ Trees: {count}")
    conn.commit()
    conn.close()
    return count


def main():
    print("=" * 70)
    print("VALORA AI - OPENCITY DATA INGESTION")
    print("=" * 70)
    
    print("\n[1/7] Ingesting schools...")
    schools = ingest_schools()
    
    print("\n[2/7] Ingesting hospitals...")
    hospitals = ingest_hospitals()
    
    print("\n[3/7] Ingesting toilets...")
    toilets = ingest_toilets()
    
    print("\n[4/7] Ingesting canteens...")
    canteens = ingest_canteens()
    
    print("\n[5/7] Ingesting slums data...")
    slums = ingest_slums()
    
    print("\n[6/7] Ingesting streetlights...")
    streetlights = ingest_streetlights()
    
    print("\n[7/7] Ingesting trees...")
    trees = ingest_trees()
    
    total = schools + hospitals + toilets + canteens + slums + streetlights + trees
    
    print("\n" + "=" * 70)
    print("INGESTION COMPLETE")
    print("=" * 70)
    print(f"Schools: {schools}")
    print(f"Hospitals: {hospitals}")
    print(f"Toilets: {toilets}")
    print(f"Canteens: {canteens}")
    print(f"Slums: {slums}")
    print(f"Streetlights: {streetlights}")
    print(f"Trees: {trees}")
    print(f"\nTOTAL: {total}")


if __name__ == "__main__":
    main()
