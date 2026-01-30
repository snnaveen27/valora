"""
Comprehensive Bangalore Data Scraper for Valora GIS Agent
Scrapes all essential POI categories to make Valora fully understand Bangalore.
"""

import os
import json
import requests
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
APIFY_BASE_URL = "https://api.apify.com/v2"
ACTOR_ID = "nwua9Gu5YrADL7ZDj"  # apify/google-maps-scraper

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "src" / "data" / "valora.db"
DATA_DIR = BASE_DIR / "src" / "data" / "google_maps_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# All POI categories needed for comprehensive Bangalore coverage
SCRAPE_CONFIG = [
    # Already scraped: schools (90), hospitals (65), malls (57)
    
    # Parks & Recreation
    {"category": "park", "searches": ["parks", "gardens", "playgrounds"], "limit": 100},
    
    # Food & Dining
    {"category": "restaurant", "searches": ["restaurants", "cafes", "food courts"], "limit": 150},
    
    # Financial
    {"category": "bank", "searches": ["banks", "ATMs"], "limit": 100},
    
    # Fitness
    {"category": "gym", "searches": ["gyms", "fitness centers", "yoga studios"], "limit": 80},
    
    # Entertainment
    {"category": "entertainment", "searches": ["movie theaters", "cinema halls", "gaming zones"], "limit": 50},
    
    # Transport
    {"category": "transport", "searches": ["metro stations Bangalore", "BMTC bus stands", "auto stands"], "limit": 100},
    
    # Education (more)
    {"category": "college", "searches": ["colleges", "universities", "coaching centers"], "limit": 80},
    
    # Places of worship
    {"category": "worship", "searches": ["temples", "churches", "mosques"], "limit": 100},
    
    # Petrol/Gas
    {"category": "fuel", "searches": ["petrol pumps", "gas stations", "EV charging stations"], "limit": 80},
    
    # Police/Emergency
    {"category": "emergency", "searches": ["police stations", "fire stations"], "limit": 50},
    
    # Post offices & Government
    {"category": "government", "searches": ["post offices", "passport offices", "RTO offices"], "limit": 50},
]


def run_scraper(searches: list, max_results: int = 100) -> dict:
    """Run Google Maps scraper."""
    if not APIFY_TOKEN:
        return None
    
    headers = {
        "Authorization": f"Bearer {APIFY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    search_queries = [f"{term} in Bangalore, Karnataka, India" for term in searches]
    
    actor_input = {
        "searchStringsArray": search_queries,
        "maxCrawledPlacesPerSearch": max_results,
        "language": "en",
        "deeperCityScrape": False,
        "includeReviews": False,
        "includeImages": False,
        "scrapeDirectories": False,
        "maxImages": 0,
        "maxReviews": 0,
        "personalData": False
    }
    
    url = f"{APIFY_BASE_URL}/acts/{ACTOR_ID}/runs"
    
    try:
        response = requests.post(url, headers=headers, json=actor_input, timeout=30)
        response.raise_for_status()
        run_data = response.json()["data"]
        return {"run_id": run_data["id"], "status": run_data["status"]}
    except Exception as e:
        print(f"  ❌ Error starting scraper: {e}")
        return None


def wait_for_run(run_id: str, max_wait: int = 300) -> dict:
    """Wait for run to complete."""
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
    start = time.time()
    
    while time.time() - start < max_wait:
        try:
            response = requests.get(f"{APIFY_BASE_URL}/actor-runs/{run_id}", headers=headers, timeout=30)
            data = response.json()["data"]
            
            if data["status"] == "SUCCEEDED":
                return {"status": "SUCCEEDED", "dataset_id": data.get("defaultDatasetId")}
            elif data["status"] in ["FAILED", "ABORTED", "TIMED-OUT"]:
                return {"status": data["status"]}
            
            time.sleep(10)
        except:
            time.sleep(5)
    
    return {"status": "TIMEOUT"}


def download_dataset(dataset_id: str) -> list:
    """Download dataset items."""
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
    items = []
    offset = 0
    
    while True:
        try:
            response = requests.get(
                f"{APIFY_BASE_URL}/datasets/{dataset_id}/items",
                headers=headers,
                params={"offset": offset, "limit": 1000},
                timeout=60
            )
            batch = response.json()
            if not batch:
                break
            items.extend(batch)
            if len(batch) < 1000:
                break
            offset += 1000
        except:
            break
    
    return items


def ingest_pois(items: list, category: str) -> dict:
    """Ingest POIs to database."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    stats = {"inserted": 0, "updated": 0, "skipped": 0}
    
    for item in items:
        try:
            name = item.get("title", "")
            lat = item.get("location", {}).get("lat")
            lng = item.get("location", {}).get("lng")
            
            if not name or not lat or not lng:
                stats["skipped"] += 1
                continue
            
            poi_id = f"gmaps_{item.get('placeId', '')}"
            categories = item.get("categories", [])
            subcategory = categories[0] if categories else ""
            
            source_data = json.dumps({
                "place_id": item.get("placeId"),
                "categories": categories,
                "rating": item.get("totalScore"),
                "reviews_count": item.get("reviewsCount"),
                "address": item.get("address"),
                "phone": item.get("phone"),
                "website": item.get("website"),
                "url": item.get("url")
            })
            
            cursor.execute("SELECT poi_id FROM pois WHERE poi_id = ?", (poi_id,))
            
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE pois SET name = ?, latitude = ?, longitude = ?,
                        category = ?, subcategory = ?, source_data = ?
                    WHERE poi_id = ?
                """, (name, lat, lng, category, subcategory, source_data, poi_id))
                stats["updated"] += 1
            else:
                cursor.execute("""
                    INSERT INTO pois (poi_id, name, category, subcategory,
                                     latitude, longitude, source, source_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (poi_id, name, category, subcategory, lat, lng, "google_maps", source_data))
                stats["inserted"] += 1
                
        except Exception as e:
            stats["skipped"] += 1
    
    conn.commit()
    conn.close()
    return stats


def scrape_category(config: dict) -> dict:
    """Scrape a single category."""
    category = config["category"]
    searches = config["searches"]
    limit = config["limit"]
    
    print(f"\n  🔍 {category.upper()}: {searches}")
    
    # Start scraper
    run = run_scraper(searches, limit)
    if not run:
        return {"status": "failed", "error": "Could not start scraper"}
    
    print(f"     Run ID: {run['run_id']}")
    
    # Wait for completion
    result = wait_for_run(run["run_id"])
    
    if result["status"] != "SUCCEEDED":
        print(f"     ❌ Failed: {result['status']}")
        return {"status": "failed", "error": result["status"]}
    
    # Download
    items = download_dataset(result["dataset_id"])
    print(f"     Downloaded: {len(items)} items")
    
    # Save raw
    output_file = DATA_DIR / f"{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    
    # Ingest
    stats = ingest_pois(items, category)
    print(f"     ✓ Inserted: {stats['inserted']}, Updated: {stats['updated']}")
    
    return {"status": "success", "items": len(items), "stats": stats}


def main():
    print("=" * 70)
    print("VALORA AI - COMPREHENSIVE BANGALORE DATA SCRAPER")
    print("=" * 70)
    
    if not APIFY_TOKEN:
        print("\n❌ APIFY_API_TOKEN not set!")
        return
    
    total_stats = {"categories": 0, "items": 0, "inserted": 0}
    
    for i, config in enumerate(SCRAPE_CONFIG):
        print(f"\n[{i+1}/{len(SCRAPE_CONFIG)}] Scraping {config['category']}...")
        
        result = scrape_category(config)
        
        if result["status"] == "success":
            total_stats["categories"] += 1
            total_stats["items"] += result["items"]
            total_stats["inserted"] += result["stats"]["inserted"]
        
        # Small delay between categories
        time.sleep(2)
    
    print("\n" + "=" * 70)
    print("SCRAPING COMPLETE - SUMMARY")
    print("=" * 70)
    print(f"Categories scraped: {total_stats['categories']}/{len(SCRAPE_CONFIG)}")
    print(f"Total items: {total_stats['items']}")
    print(f"New POIs inserted: {total_stats['inserted']}")
    
    # Show final POI counts
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT category, COUNT(*) FROM pois GROUP BY category ORDER BY COUNT(*) DESC")
    
    print("\nFinal POI counts by category:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,}")
    
    cursor.execute("SELECT COUNT(*) FROM pois")
    total = cursor.fetchone()[0]
    print(f"\n  TOTAL POIs: {total:,}")
    conn.close()


if __name__ == "__main__":
    main()
