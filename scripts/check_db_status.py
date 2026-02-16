"""Check database status and missing data."""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "storage" / "valora.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cursor.fetchall()]

print("=" * 60)
print("DATABASE STATUS")
print("=" * 60)

total_records = 0
for table in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        total_records += count
        print(f"  {table}: {count:,}")
    except:
        print(f"  {table}: ERROR")

print("-" * 60)
print(f"  TOTAL RECORDS: {total_records:,}")
print("=" * 60)

# Check for key indexes
print("\nKEY INDEXES:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
indexes = [r[0] for r in cursor.fetchall()]
print(f"  Total indexes: {len(indexes)}")

conn.close()
