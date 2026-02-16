"""
Smart OpenCity.in Dataset Downloader for Valora AI
Downloads all Bengaluru datasets with anti-ban measures and auto-ingestion.

Features:
- Rate limiting with random delays
- Exponential backoff on failures
- Resume capability (skips already downloaded)
- Auto-ingestion into database
- Progress tracking and logging
"""

import os
import requests
import json
import time
import random
import sqlite3
import csv
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('opencity_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "valora.db"
DOWNLOAD_DIR = BASE_DIR / "storage" / "opencity_downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# CKAN API
CKAN_API = "https://data.opencity.in/api/3/action"

# Smart download settings
MIN_DELAY = 2.0      # Minimum delay between requests (seconds)
MAX_DELAY = 5.0      # Maximum delay between requests
BATCH_SIZE = 10      # Pause longer after this many downloads
BATCH_PAUSE = 15     # Longer pause between batches (seconds)
MAX_RETRIES = 3      # Max retries per resource
BACKOFF_FACTOR = 2   # Exponential backoff multiplier

# Preferred formats
PREFERRED_FORMATS = ['geojson', 'json', 'csv', 'xlsx', 'xls']

# Session with headers to look like a browser
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
})


def smart_delay(batch_count=0):
    """Add random delay to avoid detection."""
    base_delay = random.uniform(MIN_DELAY, MAX_DELAY)
    
    # Add jitter
    jitter = random.uniform(0, 1)
    delay = base_delay + jitter
    
    # Longer pause after batch
    if batch_count > 0 and batch_count % BATCH_SIZE == 0:
        delay += random.uniform(BATCH_PAUSE, BATCH_PAUSE + 5)
        logger.info(f"Batch pause: {delay:.1f}s")
    
    time.sleep(delay)


def fetch_with_retry(url, params=None, max_retries=MAX_RETRIES):
    """Fetch URL with retry and exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limited
                wait_time = BACKOFF_FACTOR ** (attempt + 2) * 10
                logger.warning(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            elif e.response.status_code == 404:
                return None
            else:
                wait_time = BACKOFF_FACTOR ** attempt * 2
                logger.warning(f"HTTP error {e.response.status_code}. Retry in {wait_time}s...")
                time.sleep(wait_time)
        except Exception as e:
            wait_time = BACKOFF_FACTOR ** attempt * 2
            logger.warning(f"Error: {e}. Retry in {wait_time}s...")
            time.sleep(wait_time)
    
    return None


def get_all_datasets(query="bengaluru"):
    """Get all datasets matching query."""
    logger.info(f"Fetching dataset list for: {query}")
    
    all_datasets = []
    offset = 0
    limit = 100
    
    while True:
        response = fetch_with_retry(
            f"{CKAN_API}/package_search",
            params={"q": query, "rows": limit, "start": offset}
        )
        
        if not response:
            break
            
        data = response.json()
        if not data.get("success"):
            break
            
        results = data["result"]["results"]
        if not results:
            break
            
        all_datasets.extend(results)
        logger.info(f"Fetched {len(all_datasets)} datasets...")
        
        if len(results) < limit:
            break
            
        offset += limit
        smart_delay()
    
    logger.info(f"Total datasets found: {len(all_datasets)}")
    return all_datasets


def get_dataset_resources(dataset_name):
    """Get resources for a specific dataset."""
    response = fetch_with_retry(
        f"{CKAN_API}/package_show",
        params={"id": dataset_name}
    )
    
    if not response:
        return []
    
    data = response.json()
    if not data.get("success"):
        return []
    
    return data["result"].get("resources", [])


def download_resource(resource, dataset_name, download_count):
    """Download a single resource."""
    url = resource.get("url")
    format_type = resource.get("format", "").lower()
    name = resource.get("name", "data")
    
    if not url:
        return None
    
    # Create safe filename
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
    ext = format_type if format_type else "dat"
    filename = f"{dataset_name}_{safe_name}.{ext}"[:200]  # Limit filename length
    filepath = DOWNLOAD_DIR / filename
    
    # Skip if already downloaded
    if filepath.exists() and filepath.stat().st_size > 0:
        logger.debug(f"Skip (exists): {filename}")
        return filepath
    
    try:
        response = session.get(url, timeout=60, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        size_kb = filepath.stat().st_size / 1024
        logger.info(f"Downloaded: {filename} ({size_kb:.1f} KB)")
        return filepath
        
    except Exception as e:
        logger.warning(f"Download failed for {filename}: {e}")
        return None


def ingest_file_to_db(filepath, dataset_name):
    """Ingest a downloaded file into the database."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    ext = filepath.suffix.lower()
    count = 0
    
    try:
        if ext == '.csv':
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cursor.execute("""
                        INSERT OR IGNORE INTO open_datasets 
                        (dataset_id, dataset_name, category, data_type, raw_data, source_url)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        f"{dataset_name}_{count}",
                        dataset_name,
                        'opencity',
                        ext[1:],
                        json.dumps(row),
                        str(filepath)
                    ))
                    count += 1
                    
        elif ext in ['.json', '.geojson']:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
                
            # Handle GeoJSON features
            if isinstance(data, dict) and 'features' in data:
                for feat in data['features']:
                    cursor.execute("""
                        INSERT OR IGNORE INTO open_datasets 
                        (dataset_id, dataset_name, category, data_type, raw_data, source_url)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        f"{dataset_name}_{count}",
                        dataset_name,
                        'opencity_geo',
                        'geojson',
                        json.dumps(feat),
                        str(filepath)
                    ))
                    count += 1
            elif isinstance(data, list):
                for item in data:
                    cursor.execute("""
                        INSERT OR IGNORE INTO open_datasets 
                        (dataset_id, dataset_name, category, data_type, raw_data, source_url)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        f"{dataset_name}_{count}",
                        dataset_name,
                        'opencity',
                        ext[1:],
                        json.dumps(item),
                        str(filepath)
                    ))
                    count += 1
                    
        conn.commit()
        
    except Exception as e:
        logger.warning(f"Ingest error for {filepath.name}: {e}")
    finally:
        conn.close()
    
    return count


def download_all_datasets():
    """Main function to download all datasets."""
    print("=" * 70)
    print("VALORA AI - SMART OPENCITY DOWNLOADER")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Download directory: {DOWNLOAD_DIR}")
    print("=" * 70)
    
    # Get all datasets
    datasets = get_all_datasets("bengaluru")
    
    if not datasets:
        logger.error("No datasets found!")
        return
    
    # Track progress
    stats = {
        "total_datasets": len(datasets),
        "processed": 0,
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "ingested": 0
    }
    
    # Save dataset list for reference
    with open(DOWNLOAD_DIR / "dataset_list.json", "w") as f:
        json.dump([{"name": d["name"], "title": d["title"]} for d in datasets], f, indent=2)
    
    # Process each dataset
    for i, dataset in enumerate(datasets):
        dataset_name = dataset.get("name", "")
        title = dataset.get("title", "")
        
        logger.info(f"\n[{i+1}/{len(datasets)}] {dataset_name}")
        logger.info(f"    Title: {title}")
        
        # Get resources
        smart_delay(i)
        resources = get_dataset_resources(dataset_name)
        
        if not resources:
            logger.info(f"    No resources found")
            stats["processed"] += 1
            continue
        
        # Filter preferred formats
        preferred_resources = [
            r for r in resources 
            if r.get("format", "").lower() in PREFERRED_FORMATS
        ]
        
        if not preferred_resources:
            preferred_resources = resources[:3]  # Take first 3 if no preferred
        
        # Download resources
        for resource in preferred_resources:
            smart_delay(stats["downloaded"])
            
            filepath = download_resource(resource, dataset_name, stats["downloaded"])
            
            if filepath:
                stats["downloaded"] += 1
                
                # Auto-ingest
                ingested = ingest_file_to_db(filepath, dataset_name)
                stats["ingested"] += ingested
            else:
                stats["failed"] += 1
        
        stats["processed"] += 1
        
        # Progress report every 50 datasets
        if (i + 1) % 50 == 0:
            logger.info(f"\n--- Progress: {i+1}/{len(datasets)} datasets ---")
            logger.info(f"    Downloaded: {stats['downloaded']}, Failed: {stats['failed']}")
            logger.info(f"    Records ingested: {stats['ingested']}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    print(f"Datasets processed: {stats['processed']}/{stats['total_datasets']}")
    print(f"Files downloaded: {stats['downloaded']}")
    print(f"Files failed: {stats['failed']}")
    print(f"Records ingested: {stats['ingested']}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Save stats
    with open(DOWNLOAD_DIR / "download_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    
    return stats


if __name__ == "__main__":
    download_all_datasets()
