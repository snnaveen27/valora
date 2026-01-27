"""Check database state."""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "src" / "data" / "valora.db"
print(f"DB: {db_path}")
print(f"Size: {db_path.stat().st_size / 1024 / 1024:.1f} MB")

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check columns
cursor.execute("PRAGMA table_info(properties)")
cols = [r[1] for r in cursor.fetchall()]
print(f"\nColumns ({len(cols)}): {cols[:10]}...")
print(f"Has property_category: {'property_category' in cols}")
print(f"Has bhk: {'bhk' in cols}")

# Count
cursor.execute("SELECT COUNT(*) FROM properties")
print(f"\nTotal properties: {cursor.fetchone()[0]:,}")

# By source
cursor.execute("SELECT source, COUNT(*) as c FROM properties GROUP BY source ORDER BY c DESC")
print("\nBy source:")
for row in cursor.fetchall():
    print(f"  {row['source']}: {row['c']:,}")

# By category if exists
if 'property_category' in cols:
    cursor.execute("SELECT property_category, COUNT(*) as c FROM properties GROUP BY property_category ORDER BY c DESC")
    print("\nBy category:")
    for row in cursor.fetchall():
        print(f"  {row['property_category'] or 'null'}: {row['c']:,}")

# By listing type
cursor.execute("SELECT listing_type, COUNT(*) as c FROM properties GROUP BY listing_type ORDER BY c DESC")
print("\nBy listing type:")
for row in cursor.fetchall():
    print(f"  {row['listing_type'] or 'null'}: {row['c']:,}")

# Duplicates check
cursor.execute("SELECT property_id, COUNT(*) as c FROM properties GROUP BY property_id HAVING c > 1")
dups = cursor.fetchall()
print(f"\nDuplicate property_ids: {len(dups)}")

cursor.execute("SELECT source_url, COUNT(*) as c FROM properties WHERE source_url IS NOT NULL AND source_url != '' GROUP BY source_url HAVING c > 1")
url_dups = cursor.fetchall()
print(f"Duplicate URLs: {len(url_dups)}")

# Pincodes
cursor.execute("SELECT COUNT(DISTINCT pincode) FROM properties WHERE pincode IS NOT NULL")
print(f"\nUnique pincodes: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM properties WHERE latitude IS NOT NULL")
print(f"With coordinates: {cursor.fetchone()[0]:,}")

conn.close()
print("\n✅ Check complete")
