"""Initialize the database with schema."""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "backend" / "database" / "valora.db"
schema_path = Path(__file__).parent.parent / "backend" / "database" / "schema_simple.sql"

print(f"DB path: {db_path}")
print(f"Schema path: {schema_path}")

# Delete old DB if exists
if db_path.exists():
    db_path.unlink()
    print("Deleted old database")

# Read schema
with open(schema_path, 'r', encoding='utf-8') as f:
    schema = f.read()

# Create database
conn = sqlite3.connect(str(db_path))
conn.executescript(schema)
conn.commit()

# Verify tables
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print(f"Tables created: {tables}")

# Add new columns for property categorization
new_columns = [
    "ALTER TABLE properties ADD COLUMN property_category TEXT",
    "ALTER TABLE properties ADD COLUMN property_subtype TEXT", 
    "ALTER TABLE properties ADD COLUMN bhk TEXT",
    "ALTER TABLE properties ADD COLUMN rent_monthly REAL",
]

for sql in new_columns:
    try:
        cursor.execute(sql)
        print(f"Added column: {sql.split()[-2]}")
    except Exception as e:
        print(f"Column exists or error: {e}")

# Add indexes
indexes = [
    "CREATE INDEX IF NOT EXISTS idx_properties_category ON properties(property_category)",
    "CREATE INDEX IF NOT EXISTS idx_properties_subtype ON properties(property_subtype)",
    "CREATE INDEX IF NOT EXISTS idx_properties_pincode ON properties(pincode)",
    "CREATE INDEX IF NOT EXISTS idx_properties_bhk ON properties(bhk)",
]

for sql in indexes:
    try:
        cursor.execute(sql)
    except:
        pass

conn.commit()
conn.close()

print("\n✅ Database initialized successfully!")
