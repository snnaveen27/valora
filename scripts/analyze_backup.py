"""Analyze backup data files to understand structure."""
import json
from pathlib import Path

backup_dir = Path(__file__).parent.parent / 'storage' / 'data_backup'

print(f"Backup directory: {backup_dir}")
print("=" * 70)

# Check buildings.geojson
buildings_file = backup_dir / 'buildings.geojson'
if buildings_file.exists():
    print(f"\n📁 buildings.geojson ({buildings_file.stat().st_size / (1024*1024):.2f} MB)")
    
    with open(buildings_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        print(f"  Type: dict")
        print(f"  Keys: {list(data.keys())}")
        
        if 'features' in data:
            features = data['features']
            print(f"  Features count: {len(features):,}")
            
            if features:
                sample = features[0]
                print(f"  Sample feature type: {sample.get('type')}")
                print(f"  Sample geometry type: {sample.get('geometry', {}).get('type')}")
                props = sample.get('properties', {})
                print(f"  Sample properties keys: {list(props.keys())[:15]}")
                
                # Count by type if available
                types = {}
                for f in features[:10000]:
                    t = f.get('properties', {}).get('building') or f.get('properties', {}).get('amenity') or 'unknown'
                    types[t] = types.get(t, 0) + 1
                print(f"  Sample types (first 10k): {dict(list(types.items())[:10])}")
    elif isinstance(data, list):
        print(f"  Type: list")
        print(f"  Items count: {len(data):,}")
        if data:
            print(f"  Sample item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'N/A'}")

# Check other files
for json_file in backup_dir.glob('*.json'):
    if json_file.name != 'buildings.geojson':
        print(f"\n📁 {json_file.name} ({json_file.stat().st_size / 1024:.2f} KB)")
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                print(f"  Keys: {list(data.keys())[:10]}")
            elif isinstance(data, list):
                print(f"  Items: {len(data)}")
        except:
            print("  Could not parse")

print("\n" + "=" * 70)
