import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from database.query_service import get_query_service

db = get_query_service()

print("Testing query service...")
print("=" * 60)

# Test POIs
pois = db.get_all_pois(limit=5)
print(f"\nPOIs returned: {len(pois)}")
if pois:
    print(f"Sample POI: {pois[0]}")
    print(f"POI keys: {list(pois[0].keys())}")

# Test Transport
transport = db.get_all_transport(limit=5)
print(f"\nTransport returned: {len(transport)}")
if transport:
    print(f"Sample transport: {transport[0]}")
    print(f"Transport keys: {list(transport[0].keys())}")

# Test Places
places = db.get_all_places(limit=5)
print(f"\nPlaces returned: {len(places)}")
if places:
    print(f"Sample place: {places[0]}")
    print(f"Place keys: {list(places[0].keys())}")

print("\n" + "=" * 60)
print("Testing complete!")
