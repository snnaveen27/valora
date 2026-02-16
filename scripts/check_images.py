"""Check image URLs in database."""
import sqlite3
import json
from pathlib import Path

db_path = Path(__file__).parent.parent / "storage" / "valora.db"
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get sample images from MagicBricks (most images)
cursor.execute("""
    SELECT property_id, source, images, locality 
    FROM properties 
    WHERE images IS NOT NULL 
      AND images != '[]' 
      AND images != ''
      AND source = 'magicbricks'
    LIMIT 10
""")

for row in cursor.fetchall():
    print(f"\n{'='*60}")
    print(f"Property: {row['property_id']}")
    print(f"Source: {row['source']}")
    print(f"Locality: {row['locality']}")
    try:
        images = json.loads(row['images'])
        print(f"Images ({len(images)}):")
        for img in images[:3]:
            print(f"  - {img[:100]}...")
    except Exception as e:
        print(f"Parse error: {e}")
        print(f"Raw: {row['images'][:200]}")

conn.close()
