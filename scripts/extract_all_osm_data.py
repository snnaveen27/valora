"""
Comprehensive OSM Data Extraction for Bengaluru
Extracts all useful features from PBF and organizes into structured folders:
- roads/ (highways, streets)
- places/ (cities, neighborhoods, localities)
- pois/ (amenities, shops, tourism)
- landuse/ (parks, residential, commercial)
- natural/ (water bodies, forests)
- transport/ (metro, bus stops, railways)
- boundaries/ (administrative boundaries)
"""

import osmium
import json
from pathlib import Path
from collections import defaultdict
import sys


class RawOSMWriter:
    def __init__(self, raw_dir: Path):
        raw_dir.mkdir(parents=True, exist_ok=True)
        self.nodes_fp = (raw_dir / 'nodes.jsonl').open('w', encoding='utf-8')
        self.ways_fp = (raw_dir / 'ways.jsonl').open('w', encoding='utf-8')
        self.relations_fp = (raw_dir / 'relations.jsonl').open('w', encoding='utf-8')
        self.counts = defaultdict(int)

    def close(self):
        try:
            self.nodes_fp.close()
        except Exception:
            pass
        try:
            self.ways_fp.close()
        except Exception:
            pass
        try:
            self.relations_fp.close()
        except Exception:
            pass

    def write_node(self, n_id, lon, lat, tags):
        self.nodes_fp.write(json.dumps({
            'type': 'node',
            'id': n_id,
            'lon': lon,
            'lat': lat,
            'tags': tags
        }, ensure_ascii=False) + '\n')
        self.counts['nodes'] += 1

    def write_way(self, w_id, node_ids, coords, tags):
        self.ways_fp.write(json.dumps({
            'type': 'way',
            'id': w_id,
            'nodes': node_ids,
            'coords': coords,
            'tags': tags
        }, ensure_ascii=False) + '\n')
        self.counts['ways'] += 1

    def write_relation(self, r_id, members, tags):
        self.relations_fp.write(json.dumps({
            'type': 'relation',
            'id': r_id,
            'members': members,
            'tags': tags
        }, ensure_ascii=False) + '\n')
        self.counts['relations'] += 1

class ComprehensiveOSMExtractor(osmium.SimpleHandler):
    def __init__(self, raw_writer: RawOSMWriter):
        super().__init__()
        self.raw = raw_writer
        self.data = {
            'roads': [],
            'places': [],
            'pois': [],
            'landuse': [],
            'natural': [],
            'transport': [],
            'boundaries': [],
            'buildings_metadata': []  # Additional building metadata beyond geometry
        }
        self.stats = defaultdict(int)
        
    def node(self, n):
        """Extract ALL nodes to raw, and also derive point features"""
        if not n.location.valid():
            return

        tags = {tag.k: tag.v for tag in n.tags}
        name = tags.get('name')
        lng, lat = n.location.lon, n.location.lat

        # Raw dump (everything)
        self.raw.write_node(n.id, lng, lat, tags)
        
        # Places (cities, towns, neighborhoods)
        if 'place' in tags:
            self.data['places'].append({
                'id': n.id,
                'name': name,
                'type': 'place',
                'subtype': tags.get('place'),
                'population': tags.get('population'),
                'lng': lng,
                'lat': lat,
                'tags': tags
            })
            self.stats['places'] += 1
        
        # Amenities (restaurants, hospitals, schools, etc.)
        elif 'amenity' in tags:
            self.data['pois'].append({
                'id': n.id,
                'name': name,
                'type': 'amenity',
                'subtype': tags.get('amenity'),
                'lng': lng,
                'lat': lat,
                'tags': tags
            })
            self.stats['amenities'] += 1
        
        # Shops
        elif 'shop' in tags:
            self.data['pois'].append({
                'id': n.id,
                'name': name,
                'type': 'shop',
                'subtype': tags.get('shop'),
                'lng': lng,
                'lat': lat,
                'tags': tags
            })
            self.stats['shops'] += 1
        
        # Tourism
        elif 'tourism' in tags:
            self.data['pois'].append({
                'id': n.id,
                'name': name,
                'type': 'tourism',
                'subtype': tags.get('tourism'),
                'lng': lng,
                'lat': lat,
                'tags': tags
            })
            self.stats['tourism'] += 1
        
        # Public transport stops
        elif 'public_transport' in tags or 'railway' in tags:
            self.data['transport'].append({
                'id': n.id,
                'name': name,
                'type': 'transport',
                'subtype': tags.get('public_transport') or tags.get('railway'),
                'lng': lng,
                'lat': lat,
                'tags': tags
            })
            self.stats['transport_stops'] += 1
    
    def way(self, w):
        """Extract ALL ways to raw, and also derive linear/area features"""
        tags = {tag.k: tag.v for tag in w.tags}
        name = tags.get('name')

        # Raw dump (everything)
        node_ids = [n.ref for n in w.nodes]
        coords = []
        for n in w.nodes:
            if n.location.valid():
                coords.append([n.location.lon, n.location.lat])
        self.raw.write_way(w.id, node_ids, coords, tags)

        # For derived outputs, we need coords to compute centroid.
        if not coords:
            return

        centroid_lng = sum(c[0] for c in coords) / len(coords)
        centroid_lat = sum(c[1] for c in coords) / len(coords)
        
        # Roads/Highways (include ALL, even unnamed)
        if 'highway' in tags:
            highway_type = tags.get('highway')
            self.data['roads'].append({
                'id': w.id,
                'name': name,
                'type': 'road',
                'subtype': highway_type,
                'centroid': {'lng': centroid_lng, 'lat': centroid_lat},
                'geometry': coords,
                'lanes': tags.get('lanes'),
                'maxspeed': tags.get('maxspeed'),
                'surface': tags.get('surface'),
                'tags': tags
            })
            self.stats[f'road_{highway_type}'] += 1
        
        # Landuse
        elif 'landuse' in tags:
            self.data['landuse'].append({
                'id': w.id,
                'name': name,
                'type': 'landuse',
                'subtype': tags.get('landuse'),
                'centroid': {'lng': centroid_lng, 'lat': centroid_lat},
                'geometry': coords,
                'tags': tags
            })
            self.stats['landuse'] += 1
        
        # Natural features
        elif 'natural' in tags or 'water' in tags:
            self.data['natural'].append({
                'id': w.id,
                'name': name,
                'type': 'natural',
                'subtype': tags.get('natural') or tags.get('water'),
                'centroid': {'lng': centroid_lng, 'lat': centroid_lat},
                'geometry': coords,
                'tags': tags
            })
            self.stats['natural'] += 1
        
        # Leisure (parks, playgrounds, etc.)
        elif 'leisure' in tags:
            self.data['landuse'].append({
                'id': w.id,
                'name': name,
                'type': 'leisure',
                'subtype': tags.get('leisure'),
                'centroid': {'lng': centroid_lng, 'lat': centroid_lat},
                'geometry': coords,
                'tags': tags
            })
            self.stats['leisure'] += 1
        
        # Buildings metadata (include ALL buildings)
        elif 'building' in tags:
            self.data['buildings_metadata'].append({
                'id': w.id,
                'name': name,
                'type': 'building',
                'subtype': tags.get('building'),
                'centroid': {'lng': centroid_lng, 'lat': centroid_lat},
                'height': tags.get('height'),
                'levels': tags.get('building:levels'),
                'tags': tags
            })
            self.stats['named_buildings'] += 1
    
    def relation(self, r):
        """Extract ALL relations to raw, and also derive boundaries/routes"""
        tags = {tag.k: tag.v for tag in r.tags}
        name = tags.get('name')

        # Raw dump (everything)
        members = []
        for m in r.members:
            members.append({
                'type': m.type,
                'ref': m.ref,
                'role': m.role
            })
        self.raw.write_relation(r.id, members, tags)
        
        # Administrative boundaries
        if tags.get('boundary') == 'administrative':
            self.data['boundaries'].append({
                'id': r.id,
                'name': name,
                'type': 'boundary',
                'subtype': 'administrative',
                'admin_level': tags.get('admin_level'),
                'tags': tags
            })
            self.stats['boundaries'] += 1
        
        # Public transport routes
        elif tags.get('type') == 'route' and tags.get('route') in ['bus', 'train', 'subway']:
            self.data['transport'].append({
                'id': r.id,
                'name': name,
                'type': 'route',
                'subtype': tags.get('route'),
                'ref': tags.get('ref'),
                'operator': tags.get('operator'),
                'tags': tags
            })
            self.stats['transport_routes'] += 1

def save_category_data(category_name, data, output_dir):
    """Save category data as GeoJSON"""
    if not data:
        print(f"   ⚠️  No data for {category_name}")
        return
    
    features = []
    for item in data:
        geometry = None
        
        # Point geometry
        if 'lng' in item and 'lat' in item:
            geometry = {
                'type': 'Point',
                'coordinates': [item['lng'], item['lat']]
            }
        # LineString or Polygon geometry
        elif 'geometry' in item:
            coords = item['geometry']
            # Check if it's a closed polygon
            if len(coords) > 2 and coords[0] == coords[-1]:
                geometry = {
                    'type': 'Polygon',
                    'coordinates': [coords]
                }
            else:
                geometry = {
                    'type': 'LineString',
                    'coordinates': coords
                }
        # Centroid fallback
        elif 'centroid' in item:
            geometry = {
                'type': 'Point',
                'coordinates': [item['centroid']['lng'], item['centroid']['lat']]
            }
        
        if geometry:
            # Remove geometry from properties to avoid duplication
            properties = {k: v for k, v in item.items() if k not in ['lng', 'lat', 'geometry', 'centroid']}
            
            features.append({
                'type': 'Feature',
                'geometry': geometry,
                'properties': properties
            })
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    output_file = output_dir / f'{category_name}.geojson'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    
    print(f"   ✅ {category_name}: {len(features):,} features")

def main():
    print("🗺️  Comprehensive OSM Data Extraction for Bengaluru")
    print("=" * 60)
    
    pbf_path = Path(__file__).parent.parent / 'src' / 'data' / 'bengaluru.pbf'
    output_base = Path(__file__).parent.parent / 'src' / 'data' / 'osm_extracted'
    raw_dir = output_base / 'raw'
    derived_dir = output_base / 'derived'
    
    if not pbf_path.exists():
        print(f"❌ PBF file not found: {pbf_path}")
        return
    
    print(f"📂 Input: {pbf_path}")
    print(f"📁 Output: {output_base}")
    print()
    
    # Extract data
    print("🔄 Extracting data from PBF (FULL RAW + derived layers)...")
    output_base.mkdir(parents=True, exist_ok=True)
    derived_dir.mkdir(parents=True, exist_ok=True)
    raw_writer = RawOSMWriter(raw_dir)
    handler = ComprehensiveOSMExtractor(raw_writer)

    try:
        # locations=True is required to get node coordinates on ways
        handler.apply_file(str(pbf_path), locations=True)
    finally:
        raw_writer.close()
    
    print("\n📊 Extraction Statistics:")
    for key, count in sorted(handler.stats.items(), key=lambda x: -x[1]):
        print(f"   {key}: {count:,}")
    
    print("\n💾 Saving derived categorized data...")
    
    # Save each category
    for category, data in handler.data.items():
        if data:
            save_category_data(category, data, derived_dir)
    
    # Create index file
    index = {
        'generated': str(Path(pbf_path).stat().st_mtime),
        'source': str(pbf_path),
        'output': {
            'raw_dir': str(raw_dir),
            'derived_dir': str(derived_dir)
        },
        'raw_counts': dict(raw_writer.counts),
        'derived_counts': {
            category: len(data) for category, data in handler.data.items()
        },
        'derived_total_features': sum(len(data) for data in handler.data.values()),
        'raw_files': ['raw/nodes.jsonl', 'raw/ways.jsonl', 'raw/relations.jsonl'],
        'derived_files': [f'derived/{cat}.geojson' for cat in handler.data.keys() if handler.data[cat]]
    }
    
    index_file = output_base / 'index.json'
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)
    
    print(f"\n✅ Extraction complete!")
    print(f"📁 Data saved to: {output_base}")
    print(f"📋 Index file: {index_file}")
    print(f"\n📦 Derived features extracted: {index['derived_total_features']:,}")
    print(f"📦 Raw counts: nodes={index['raw_counts'].get('nodes', 0):,}, ways={index['raw_counts'].get('ways', 0):,}, relations={index['raw_counts'].get('relations', 0):,}")

if __name__ == '__main__':
    main()
