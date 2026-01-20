"""
Extract building footprints and heights from Bengaluru OSM PBF file
Outputs to GeoJSON format for fast loading in Cesium
"""

import osmium
import json
import sys
from pathlib import Path
from collections import defaultdict

class BuildingHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.buildings = []
        self.ways_cache = {}
        self.nodes_cache = {}
        
    def node(self, n):
        """Cache node locations"""
        self.nodes_cache[n.id] = (n.location.lon, n.location.lat)
    
    def way(self, w):
        """Extract building ways"""
        if 'building' not in w.tags:
            return
        
        # Get building height (default to 10m if not specified)
        height = None
        if 'height' in w.tags:
            try:
                height_str = w.tags['height'].replace('m', '').strip()
                height = float(height_str)
            except:
                pass
        
        # Estimate from building:levels
        if height is None and 'building:levels' in w.tags:
            try:
                levels = int(w.tags['building:levels'])
                height = levels * 3.5  # ~3.5m per floor
            except:
                pass
        
        # Default height based on building type
        if height is None:
            building_type = w.tags.get('building', 'yes')
            if building_type in ['house', 'residential', 'yes']:
                height = 6.0
            elif building_type in ['commercial', 'retail', 'office']:
                height = 12.0
            elif building_type in ['industrial', 'warehouse']:
                height = 8.0
            elif building_type in ['apartments', 'hotel']:
                height = 25.0
            else:
                height = 10.0
        
        # Get coordinates from nodes
        coords = []
        for node_ref in w.nodes:
            if node_ref.ref in self.nodes_cache:
                coords.append(self.nodes_cache[node_ref.ref])
        
        if len(coords) < 3:
            return
        
        # Close the polygon if not already closed
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        
        building = {
            'type': 'Feature',
            'properties': {
                'height': height,
                'building_type': w.tags.get('building', 'yes'),
                'name': w.tags.get('name', ''),
                'osm_id': w.id
            },
            'geometry': {
                'type': 'Polygon',
                'coordinates': [coords]
            }
        }
        
        self.buildings.append(building)
        
        if len(self.buildings) % 1000 == 0:
            print(f"Extracted {len(self.buildings)} buildings...")


def extract_buildings(pbf_path, output_path):
    """Extract buildings from PBF and save to GeoJSON"""
    print(f"Reading OSM data from: {pbf_path}")
    
    handler = BuildingHandler()
    handler.apply_file(str(pbf_path), locations=True)
    
    print(f"\nTotal buildings extracted: {len(handler.buildings)}")
    
    # Create GeoJSON FeatureCollection
    geojson = {
        'type': 'FeatureCollection',
        'features': handler.buildings
    }
    
    # Save to file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(geojson, f)
    
    print(f"Saved {len(handler.buildings)} buildings to: {output_path}")
    
    # Print statistics
    heights = [b['properties']['height'] for b in handler.buildings]
    print(f"\nStatistics:")
    print(f"  Min height: {min(heights):.1f}m")
    print(f"  Max height: {max(heights):.1f}m")
    print(f"  Avg height: {sum(heights)/len(heights):.1f}m")


if __name__ == '__main__':
    pbf_path = Path(__file__).parent.parent / 'src' / 'data' / 'bengaluru.osm.pbf'
    output_path = Path(__file__).parent.parent / 'src' / 'data' / 'buildings.geojson'
    
    if not pbf_path.exists():
        print(f"ERROR: PBF file not found at {pbf_path}")
        print("Please ensure bengaluru.osm.pbf is in src/data/")
        sys.exit(1)
    
    extract_buildings(pbf_path, output_path)
