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
    
    # Force load data
    geocoder.load_data()
    print(f'Places loaded: {len(geocoder.places)}')
    print(f'Transport loaded: {len(geocoder.transport)}')
    print(f'POIs loaded: {len(geocoder.pois)}')
    
    # Test reverse geocoding
    lat, lng = 12.9701, 77.7522
    result = geocoder.reverse(lat, lng)
    print(f'Reverse geocode result for {lat}, {lng}: {result}')
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
