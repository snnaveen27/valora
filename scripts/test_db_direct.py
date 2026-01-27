import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from database.db_service import DatabaseService

db_path = Path(__file__).parent.parent / 'src' / 'data' / 'valora.db'
db = DatabaseService(str(db_path))

print(f"Database: {db_path}")
print(f"Exists: {db_path.exists()}")
print("=" * 60)

# Test direct query
print("\nTest 1: Direct POI query")
result = db.execute("SELECT * FROM pois LIMIT 5")
print(f"Result type: {type(result)}")
print(f"Result length: {len(result)}")
if result:
    print(f"First row: {result[0]}")
    print(f"Keys: {list(result[0].keys())}")

print("\n" + "=" * 60)
print("\nTest 2: Count query")
count_result = db.execute("SELECT COUNT(*) as cnt FROM pois")
print(f"POI count: {count_result[0]['cnt']}")

print("\n" + "=" * 60)
print("\nTest 3: Transport query")
transport = db.execute("SELECT * FROM transport_stops LIMIT 5")
print(f"Transport length: {len(transport)}")
if transport:
    print(f"First transport: {transport[0]}")

print("\n" + "=" * 60)
print("\nTest 4: Places query")
places = db.execute("SELECT * FROM places LIMIT 5")
print(f"Places length: {len(places)}")
if places:
    print(f"First place: {places[0]}")
