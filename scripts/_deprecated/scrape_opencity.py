"""
Scrape and download datasets from data.opencity.in for Bengaluru.
Downloads CSV, GeoJSON, and other formats automatically.
"""

import os
import requests
import json
import time
from pathlib import Path
from urllib.parse import urljoin

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = BASE_DIR / "src" / "data" / "opencity_downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# CKAN API base URL
CKAN_API = "https://data.opencity.in/api/3/action"

# Priority datasets to download (most useful for real estate)
PRIORITY_DATASETS = [
    "bengaluru-metro-stations",
    "bengaluru-schools",
    "bengaluru-hospitals", 
    "bengaluru-slopes",
    "bengaluru-parking-lots",
    "bengaluru-public-toilets",
    "bengaluru-streetlights",
    "bengaluru-cctv-cameras",
    "bengaluru-indira-canteens",
    "bengaluru-groundwater-potential",
    "bengaluru-urban-slums",
    "bengaluru-trees",
    "borewells-in-bengaluru",
    "bengaluru-ward-boundaries",
    "bengaluru-lakes",
    "bengaluru-bus-stops",
    "bengaluru-fire-stations",
    "bengaluru-police-stations",
]

# Preferred file formats (in order of preference)
PREFERRED_FORMATS = ['geojson', 'json', 'csv', 'xlsx', 'xls', 'shp']


def search_datasets(query="bengaluru", limit=100):
    """Search for datasets matching query."""
    url = f"{CKAN_API}/package_search"
    params = {
        "q": query,
        "rows": limit,
        "sort": "score desc"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            return data["result"]["results"]
        return []
    except Exception as e:
        print(f"❌ Search error: {e}")
        return []


def get_dataset_details(dataset_name):
    """Get full details of a dataset including resources."""
    url = f"{CKAN_API}/package_show"
    params = {"id": dataset_name}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            return data["result"]
        return None
    except Exception as e:
        print(f"  ❌ Error getting {dataset_name}: {e}")
        return None


def download_resource(resource, dataset_name):
    """Download a single resource file."""
    url = resource.get("url")
    format_type = resource.get("format", "").lower()
    name = resource.get("name", "data")
    
    if not url:
        return None
    
    # Create filename
    ext = format_type if format_type else "dat"
    filename = f"{dataset_name}_{name}.{ext}".replace(" ", "_").replace("/", "_")
    filepath = DOWNLOAD_DIR / filename
    
    # Skip if already downloaded
    if filepath.exists():
        print(f"    ⏭️  Already exists: {filename}")
        return filepath
    
    try:
        print(f"    📥 Downloading: {filename}")
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        size_kb = filepath.stat().st_size / 1024
        print(f"    ✓ Downloaded: {filename} ({size_kb:.1f} KB)")
        return filepath
        
    except Exception as e:
        print(f"    ❌ Download failed: {e}")
        return None


def download_dataset(dataset_name):
    """Download all resources from a dataset."""
    print(f"\n📦 Dataset: {dataset_name}")
    
    details = get_dataset_details(dataset_name)
    if not details:
        return []
    
    resources = details.get("resources", [])
    if not resources:
        print("  ⚠️  No resources found")
        return []
    
    # Sort resources by preferred format
    def format_priority(r):
        fmt = r.get("format", "").lower()
        try:
            return PREFERRED_FORMATS.index(fmt)
        except ValueError:
            return 999
    
    resources.sort(key=format_priority)
    
    downloaded = []
    for resource in resources:
        fmt = resource.get("format", "").lower()
        if fmt in PREFERRED_FORMATS or not PREFERRED_FORMATS:
            filepath = download_resource(resource, dataset_name)
            if filepath:
                downloaded.append(filepath)
    
    return downloaded


def download_priority_datasets():
    """Download all priority datasets."""
    print("=" * 70)
    print("OPENCITY.IN - BENGALURU DATASETS DOWNLOADER")
    print("=" * 70)
    
    all_downloaded = []
    
    for dataset_name in PRIORITY_DATASETS:
        files = download_dataset(dataset_name)
        all_downloaded.extend(files)
        time.sleep(0.5)  # Rate limiting
    
    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    print(f"Total files downloaded: {len(all_downloaded)}")
    print(f"Download directory: {DOWNLOAD_DIR}")
    
    return all_downloaded


def list_all_bengaluru_datasets():
    """List all available Bengaluru datasets."""
    print("=" * 70)
    print("AVAILABLE BENGALURU DATASETS")
    print("=" * 70)
    
    datasets = search_datasets("bengaluru", limit=200)
    
    print(f"\nFound {len(datasets)} datasets:\n")
    
    for i, ds in enumerate(datasets, 1):
        name = ds.get("name", "")
        title = ds.get("title", "")
        resources = ds.get("resources", [])
        formats = list(set(r.get("format", "").upper() for r in resources if r.get("format")))
        
        print(f"{i:3}. {name}")
        print(f"     Title: {title}")
        print(f"     Formats: {', '.join(formats) or 'Unknown'}")
        print()
    
    return datasets


def download_by_format(format_type="geojson", limit=50):
    """Download all datasets with a specific format."""
    print(f"=" * 70)
    print(f"DOWNLOADING ALL {format_type.upper()} DATASETS")
    print("=" * 70)
    
    datasets = search_datasets("bengaluru", limit=limit)
    downloaded = []
    
    for ds in datasets:
        name = ds.get("name", "")
        resources = ds.get("resources", [])
        
        for resource in resources:
            fmt = resource.get("format", "").lower()
            if fmt == format_type.lower():
                filepath = download_resource(resource, name)
                if filepath:
                    downloaded.append(filepath)
                time.sleep(0.3)
    
    print(f"\n✓ Downloaded {len(downloaded)} {format_type} files")
    return downloaded


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "list":
            list_all_bengaluru_datasets()
        elif cmd == "geojson":
            download_by_format("geojson")
        elif cmd == "csv":
            download_by_format("csv")
        elif cmd == "all":
            download_priority_datasets()
        else:
            # Download specific dataset
            download_dataset(cmd)
    else:
        # Default: download priority datasets
        download_priority_datasets()
