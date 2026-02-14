import sys
import os
sys.path.append('.')
from spatial.local_geocoder import get_local_geocoder
from pathlib import Path

# Use the same path as server.py (relative to backend directory)
osm_data_dir = Path('../src/data/osm_extracted')
print(f'Using OSM data dir: {osm_data_dir.absolute()}')
print(f'Current working dir: {os.getcwd()}')

# Test geocoder with error handling
try:
    geocoder = get_local_geocoder(osm_data_dir)
    print(f'Geocoder loaded: {geocoder is not None}')
    print(f'Places loaded: {len(geocoder.places)}')
    print(f'Transport loaded: {len(geocoder.transport)}')
    print(f'POIs loaded: {len(geocoder.pois)}')
except Exception as e:
    print(f'Error loading geocoder: {e}')
    import traceback
    traceback.print_exc()

# Debug: check if Whitefield data is loaded in all lists
whitefield_places = [p for p in geocoder.places if 'whitefield' in p['name'].lower()]
whitefield_transport = [p for p in geocoder.transport if 'whitefield' in p['name'].lower()]
whitefield_pois = [p for p in geocoder.pois if 'whitefield' in p['name'].lower()]
print(f'Whitefield in places: {len(whitefield_places)}')
print(f'Whitefield in transport: {len(whitefield_transport)}')
print(f'Whitefield in pois: {len(whitefield_pois)}')
if whitefield_places:
    print(f'First place: {whitefield_places[0]}')
if whitefield_transport:
    print(f'First transport: {whitefield_transport[0]}')
if whitefield_pois:
    print(f'First POI: {whitefield_pois[0]}')

# Debug: manual distance check
from math import radians, cos, sin, asin, sqrt
def distance(lat1, lng1, lat2, lng2):
    dLat = radians(lat2 - lat1)
    dLng = radians(lng2 - lng1)
    a = sin(dLat/2) * sin(dLat/2) + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLng/2) * sin(dLng/2)
    return 6371 * 2 * asin(sqrt(a))

# Check all locations for distance
all_locations = []
all_locations.extend(geocoder.places)
all_locations.extend(geocoder.transport)
all_locations.extend(geocoder.pois)

nearest = None
nearest_dist = 2.0
for loc in all_locations[:5]:  # Check first 5
    if loc.get('lat') and loc.get('lng'):
        dist = distance(lat, lng, loc['lat'], loc['lng'])
        print(f"{loc['name']}: {dist:.3f}km")
        if dist < nearest_dist:
            nearest_dist = dist
            nearest = loc

print(f'Nearest in first 5: {nearest}')

# Now test the actual reverse method
result = geocoder.reverse(lat, lng)
print(f'Reverse geocode result: {result}')
