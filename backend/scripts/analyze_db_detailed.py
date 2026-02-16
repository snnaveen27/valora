"""Detailed database analysis"""
import sqlite3
import json
from pathlib import Path

db_path = Path(__file__).parent.parent / 'storage' / 'valora.db'
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check property sources
print("=== PROPERTY SOURCES ===")
cursor.execute("SELECT source, COUNT(*) as cnt FROM properties GROUP BY source")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]:,}")

# Analyze raw_data from MagicBricks (main source)
print("\n=== RAW_DATA FIELDS ANALYSIS ===")
cursor.execute("SELECT raw_data FROM properties WHERE source = 'magicbricks' AND raw_data IS NOT NULL LIMIT 1")
row = cursor.fetchone()
if row and row[0]:
    data = json.loads(row[0])
    print(f"MagicBricks raw_data has {len(data)} fields:")
    for key in sorted(data.keys()):
        val = data[key]
        if val:
            val_type = type(val).__name__
            if isinstance(val, dict):
                print(f"  {key}: dict with {len(val)} keys")
            elif isinstance(val, list):
                print(f"  {key}: list with {len(val)} items")
            elif isinstance(val, str) and len(val) > 50:
                print(f"  {key}: str ({len(val)} chars)")
            else:
                print(f"  {key}: {val_type} = {str(val)[:50]}")

# Check for amenities data
print("\n=== AMENITIES IN RAW_DATA ===")
cursor.execute("SELECT raw_data FROM properties WHERE raw_data LIKE '%amenities%' LIMIT 3")
for row in cursor.fetchall():
    data = json.loads(row[0])
    if 'amenities' in data:
        print(f"  amenities: {data['amenities']}")

# Check photos data
print("\n=== PHOTOS IN PROPERTIES ===")
cursor.execute("SELECT raw_data FROM properties WHERE raw_data LIKE '%photos%' LIMIT 2")
count = 0
for row in cursor.fetchall():
    data = json.loads(row[0])
    if 'photos' in data and data['photos']:
        photos = data['photos']
        if isinstance(photos, list) and len(photos) > 0:
            print(f"  Property has {len(photos)} photos")
            if isinstance(photos[0], dict):
                print(f"    First photo keys: {list(photos[0].keys())}")
            count += 1
            if count >= 2:
                break

# Check nearby_places in raw_data
print("\n=== NEARBY PLACES IN RAW_DATA ===")
cursor.execute("SELECT raw_data FROM properties WHERE raw_data LIKE '%nearby%' OR raw_data LIKE '%landmark%' LIMIT 2")
for row in cursor.fetchall():
    data = json.loads(row[0])
    for key in ['nearby', 'nearbyPlaces', 'landmarks', 'nearby_places', 'locality_info']:
        if key in data and data[key]:
            print(f"  {key}: {str(data[key])[:200]}")

# Check gov_data types
print("\n=== GOV_DATA ANALYSIS ===")
cursor.execute("SELECT source_file, COUNT(*) as cnt FROM gov_data GROUP BY source_file")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} records")

# Sample gov_data content
cursor.execute("SELECT raw_data FROM gov_data LIMIT 1")
row = cursor.fetchone()
if row:
    data = json.loads(row[0])
    print(f"  Fields: {list(data.keys())}")

# Terrain grid coverage
print("\n=== TERRAIN GRID COVERAGE ===")
cursor.execute("SELECT MIN(center_lat), MAX(center_lat), MIN(center_lng), MAX(center_lng) FROM terrain_grid")
row = cursor.fetchone()
print(f"  Lat range: {row[0]:.3f} to {row[1]:.3f}")
print(f"  Lng range: {row[2]:.3f} to {row[3]:.3f}")
cursor.execute("SELECT flood_risk, COUNT(*) FROM terrain_grid GROUP BY flood_risk")
print("  Flood risk distribution:")
for row in cursor.fetchall():
    print(f"    {row[0]}: {row[1]}")

# Buildings with metadata
print("\n=== BUILDINGS SOURCE_DATA ===")
cursor.execute("SELECT source_data FROM buildings WHERE source_data IS NOT NULL LIMIT 1")
row = cursor.fetchone()
if row and row[0]:
    try:
        data = json.loads(row[0])
        print(f"  Building source_data keys: {list(data.keys())[:15]}")
    except:
        print(f"  Building source_data: {row[0][:100]}")

# Named buildings
cursor.execute("SELECT COUNT(*) FROM buildings WHERE name IS NOT NULL AND name != ''")
print(f"\n  Named buildings: {cursor.fetchone()[0]:,}")

cursor.execute("SELECT name, building_type, height FROM buildings WHERE name IS NOT NULL AND name != '' LIMIT 5")
print("  Examples:")
for row in cursor.fetchall():
    print(f"    {row[0]}: {row[1]}, {row[2]}m")

conn.close()
