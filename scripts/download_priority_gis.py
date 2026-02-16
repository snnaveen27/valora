"""
Download Priority GIS Datasets for Real Estate Analysis
Focuses on: BDA Master Plan, Ward Boundaries, Cadastral, Land Use, Transport
"""

import os
import requests
import json
import time
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = BASE_DIR / "storage" / "gis_priority"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

CKAN_API = "https://data.opencity.in/api/3/action"

# Priority GIS datasets for real estate
PRIORITY_GIS_DATASETS = [
    # Ward Boundaries & Administrative
    "bengaluru-ward-map",
    "bengaluru-ward-boundaries", 
    "bengaluru-assembly-constituencies",
    "bbmp-ward-map",
    "bbmp-zones",
    
    # Land Use & Zoning (BDA)
    "bengaluru-land-use-map",
    "bengaluru-master-plan",
    "bda-master-plan",
    "bengaluru-zoning",
    "bengaluru-revised-master-plan-2031",
    "bengaluru-rmp-2031",
    
    # Cadastral & Property
    "bengaluru-cadastral-maps",
    "bengaluru-property-boundaries",
    "bengaluru-survey-maps",
    
    # Transport & Roads
    "bengaluru-road-network",
    "bengaluru-roads",
    "bengaluru-metro-lines",
    "bengaluru-metro-stations",
    "bengaluru-bus-routes",
    "bengaluru-flyovers",
    
    # Infrastructure
    "bengaluru-water-supply",
    "bengaluru-sewerage",
    "bengaluru-drainage",
    "bengaluru-electricity",
    
    # Natural Features
    "bengaluru-lakes",
    "bengaluru-water-bodies",
    "bengaluru-green-cover",
    "bengaluru-parks",
    
    # Demographics
    "bengaluru-population",
    "bengaluru-census",
    "bengaluru-demographics",
]

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
})


def search_gis_datasets():
    """Search for GIS-related datasets."""
    gis_terms = [
        "ward boundary", "land use", "master plan", "cadastral",
        "road network", "zoning", "BDA", "BBMP zone"
    ]
    
    found_datasets = []
    
    for term in gis_terms:
        try:
            response = session.get(
                f"{CKAN_API}/package_search",
                params={"q": f"bengaluru {term}", "rows": 50},
                timeout=30
            )
            if response.ok:
                data = response.json()
                if data.get("success"):
                    results = data["result"]["results"]
                    for r in results:
                        if r["name"] not in [d["name"] for d in found_datasets]:
                            found_datasets.append({
                                "name": r["name"],
                                "title": r["title"],
                                "search_term": term
                            })
            time.sleep(1)
        except Exception as e:
            print(f"  Error searching {term}: {e}")
    
    return found_datasets


def download_dataset(dataset_name):
    """Download a specific dataset."""
    try:
        response = session.get(
            f"{CKAN_API}/package_show",
            params={"id": dataset_name},
            timeout=30
        )
        
        if not response.ok:
            return None
            
        data = response.json()
        if not data.get("success"):
            return None
        
        resources = data["result"].get("resources", [])
        downloaded = []
        
        for resource in resources:
            url = resource.get("url")
            fmt = resource.get("format", "").lower()
            name = resource.get("name", "data")
            
            if not url:
                continue
            
            # Prefer spatial formats
            if fmt not in ['geojson', 'json', 'kml', 'kmz', 'shp', 'csv', 'xlsx']:
                continue
            
            safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
            filename = f"{dataset_name}_{safe_name}.{fmt}"[:150]
            filepath = DOWNLOAD_DIR / filename
            
            if filepath.exists():
                print(f"    Skip (exists): {filename}")
                downloaded.append(filepath)
                continue
            
            try:
                print(f"    Downloading: {filename}")
                r = session.get(url, timeout=120, stream=True)
                r.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                
                size = filepath.stat().st_size / 1024
                print(f"    ✓ {filename} ({size:.1f} KB)")
                downloaded.append(filepath)
                
            except Exception as e:
                print(f"    ❌ Failed: {e}")
            
            time.sleep(random.uniform(1, 3))
        
        return downloaded
        
    except Exception as e:
        print(f"  Error: {e}")
        return None


def main():
    print("=" * 70)
    print("PRIORITY GIS DATASETS DOWNLOADER")
    print("=" * 70)
    
    # First, search for relevant GIS datasets
    print("\n[1/3] Searching for GIS datasets...")
    found = search_gis_datasets()
    print(f"Found {len(found)} relevant datasets")
    
    # Save found datasets list
    with open(DOWNLOAD_DIR / "found_gis_datasets.json", "w") as f:
        json.dump(found, f, indent=2)
    
    # Download priority datasets
    print("\n[2/3] Downloading priority datasets...")
    all_datasets = PRIORITY_GIS_DATASETS + [d["name"] for d in found]
    unique_datasets = list(dict.fromkeys(all_datasets))  # Remove duplicates
    
    total_downloaded = 0
    
    for i, name in enumerate(unique_datasets):
        print(f"\n[{i+1}/{len(unique_datasets)}] {name}")
        files = download_dataset(name)
        if files:
            total_downloaded += len(files)
        time.sleep(random.uniform(2, 4))
    
    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    print(f"Total files downloaded: {total_downloaded}")
    print(f"Download directory: {DOWNLOAD_DIR}")


if __name__ == "__main__":
    main()
