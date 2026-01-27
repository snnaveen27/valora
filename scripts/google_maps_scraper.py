"""
Google Maps Scraper via Apify
Scrapes schools, hospitals, restaurants, etc. from Google Maps for Bangalore.
Uses apify/google-maps-scraper actor.
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

# Actor ID for Google Maps Scraper
ACTOR_ID = "nwua9Gu5YrADL7ZDj"  # apify/google-maps-scraper

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "src" / "data" / "valora.db"
DATA_DIR = BASE_DIR / "src" / "data" / "google_maps_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def run_google_maps_scraper(search_terms: list, location: str = "Bangalore, Karnataka, India", 
                           max_results: int = 100) -> dict:
    """
    Run Google Maps scraper for given search terms.
    
    Args:
        search_terms: List of search queries like ["schools", "hospitals"]
        location: Location to search in
        max_results: Max results per search term
    
    Returns:
        Run info dict with run_id and dataset_id
    """
    if not APIFY_TOKEN:
        print("❌ APIFY_API_TOKEN not set!")
        print("   Set it in .env file: APIFY_API_TOKEN=your_token")
        return None
    
    headers = {
        "Authorization": f"Bearer {APIFY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Build search queries
    search_queries = [f"{term} in {location}" for term in search_terms]
    
    # Actor input configuration
    actor_input = {
        "searchStringsArray": search_queries,
        "maxCrawledPlacesPerSearch": max_results,
        "language": "en",
        "deeperCityScrape": False,
        "includeReviews": False,  # Skip reviews to speed up
        "includeImages": False,
        "scrapeDirectories": False,
        "maxImages": 0,
        "maxReviews": 0,
        "oneReviewPerRow": False,
        "personalData": False
    }
    
    print(f"🚀 Starting Google Maps scraper...")
    print(f"   Search queries: {search_queries}")
    print(f"   Max results per query: {max_results}")
    
    # Start the actor run
    url = f"{APIFY_BASE_URL}/acts/{ACTOR_ID}/runs"
    
    try:
        response = requests.post(url, headers=headers, json=actor_input, timeout=30)
        response.raise_for_status()
        
        run_data = response.json()["data"]
        run_id = run_data["id"]
        
        print(f"✓ Actor started! Run ID: {run_id}")
        print(f"   Status: {run_data['status']}")
        
        return {
            "run_id": run_id,
            "status": run_data["status"],
            "started_at": run_data.get("startedAt"),
            "search_terms": search_terms
        }
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text if e.response else 'No response'}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def check_run_status(run_id: str) -> dict:
    """Check status of an actor run."""
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
    
    url = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()["data"]
        return {
            "status": data["status"],
            "dataset_id": data.get("defaultDatasetId"),
            "finished_at": data.get("finishedAt"),
            "stats": data.get("stats", {})
        }
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return {"status": "error", "error": str(e)}


def wait_for_completion(run_id: str, check_interval: int = 10, max_wait: int = 600) -> dict:
    """Wait for actor run to complete."""
    print(f"\n⏳ Waiting for run {run_id} to complete...")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status = check_run_status(run_id)
        
        if status["status"] == "SUCCEEDED":
            print(f"✓ Run completed successfully!")
            return status
        elif status["status"] in ["FAILED", "ABORTED", "TIMED-OUT"]:
            print(f"❌ Run failed with status: {status['status']}")
            return status
        
        elapsed = int(time.time() - start_time)
        print(f"   Status: {status['status']} (elapsed: {elapsed}s)")
        time.sleep(check_interval)
    
    print(f"❌ Timeout waiting for run to complete")
    return {"status": "timeout"}


def download_results(dataset_id: str) -> list:
    """Download results from dataset."""
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
    
    url = f"{APIFY_BASE_URL}/datasets/{dataset_id}/items"
    
    all_items = []
    offset = 0
    limit = 1000
    
    print(f"\n📥 Downloading results from dataset {dataset_id}...")
    
    while True:
        try:
            response = requests.get(
                url, 
                headers=headers, 
                params={"offset": offset, "limit": limit},
                timeout=60
            )
            response.raise_for_status()
            
            items = response.json()
            if not items:
                break
            
            all_items.extend(items)
            print(f"   Downloaded {len(all_items)} items...")
            
            if len(items) < limit:
                break
            
            offset += limit
            
        except Exception as e:
            print(f"❌ Error downloading: {e}")
            break
    
    print(f"✓ Total items downloaded: {len(all_items)}")
    return all_items


def ingest_to_database(items: list, category: str) -> dict:
    """Ingest Google Maps data to POIs table."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    stats = {"total": len(items), "inserted": 0, "updated": 0, "skipped": 0}
    
    print(f"\n💾 Ingesting {len(items)} items to database...")
    
    for item in items:
        try:
            # Extract data
            name = item.get("title", "")
            lat = item.get("location", {}).get("lat")
            lng = item.get("location", {}).get("lng")
            
            if not name or not lat or not lng:
                stats["skipped"] += 1
                continue
            
            poi_id = f"gmaps_{item.get('placeId', '')}"
            address = item.get("address", "")
            phone = item.get("phone", "")
            website = item.get("website", "")
            rating = item.get("totalScore")
            reviews_count = item.get("reviewsCount")
            price_level = item.get("price")
            
            # Determine subcategory from categories
            categories = item.get("categories", [])
            subcategory = categories[0] if categories else ""
            
            # Check if exists
            cursor.execute("SELECT poi_id FROM pois WHERE poi_id = ?", (poi_id,))
            exists = cursor.fetchone()
            
            source_data = json.dumps({
                "place_id": item.get("placeId"),
                "categories": categories,
                "rating": rating,
                "reviews_count": reviews_count,
                "price_level": price_level,
                "phone": phone,
                "website": website,
                "opening_hours": item.get("openingHours"),
                "url": item.get("url")
            })
            
            if exists:
                # Update existing
                cursor.execute("""
                    UPDATE pois SET 
                        name = ?, latitude = ?, longitude = ?,
                        subcategory = ?, source_data = ?
                    WHERE poi_id = ?
                """, (name, lat, lng, subcategory, source_data, poi_id))
                stats["updated"] += 1
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO pois (poi_id, name, category, subcategory, 
                                     latitude, longitude, source, source_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (poi_id, name, category, subcategory, lat, lng, 
                      "google_maps", source_data))
                stats["inserted"] += 1
                
        except Exception as e:
            stats["skipped"] += 1
    
    conn.commit()
    conn.close()
    
    print(f"✓ Ingestion complete:")
    print(f"   Inserted: {stats['inserted']}")
    print(f"   Updated: {stats['updated']}")
    print(f"   Skipped: {stats['skipped']}")
    
    return stats


def scrape_and_ingest(search_terms: list, category: str, max_results: int = 100):
    """Full pipeline: scrape from Google Maps and ingest to database."""
    print("=" * 70)
    print(f"GOOGLE MAPS SCRAPER - {category.upper()}")
    print("=" * 70)
    
    # Start scraper
    run_info = run_google_maps_scraper(search_terms, max_results=max_results)
    
    if not run_info:
        return None
    
    # Wait for completion
    result = wait_for_completion(run_info["run_id"])
    
    if result["status"] != "SUCCEEDED":
        print(f"❌ Scrape failed: {result['status']}")
        return None
    
    # Download results
    items = download_results(result["dataset_id"])
    
    if not items:
        print("❌ No items downloaded")
        return None
    
    # Save raw data
    output_file = DATA_DIR / f"{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"✓ Raw data saved to: {output_file}")
    
    # Ingest to database
    stats = ingest_to_database(items, category)
    
    return {
        "run_id": run_info["run_id"],
        "dataset_id": result["dataset_id"],
        "items_count": len(items),
        "stats": stats
    }


def main():
    """Main function - scrape schools and hospitals."""
    print("\n" + "=" * 70)
    print("VALORA AI - GOOGLE MAPS DATA SCRAPER")
    print("=" * 70)
    
    if not APIFY_TOKEN:
        print("\n❌ APIFY_API_TOKEN not set!")
        print("   Please set it in your .env file:")
        print("   APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxx")
        return
    
    # Scrape schools
    print("\n[1/3] Scraping SCHOOLS...")
    schools_result = scrape_and_ingest(
        search_terms=["schools", "international schools", "CBSE schools", "ICSE schools"],
        category="school",
        max_results=50  # 50 per search term = ~200 total
    )
    
    # Scrape hospitals
    print("\n[2/3] Scraping HOSPITALS...")
    hospitals_result = scrape_and_ingest(
        search_terms=["hospitals", "multi-specialty hospitals", "clinics"],
        category="hospital",
        max_results=50
    )
    
    # Scrape malls/shopping
    print("\n[3/3] Scraping MALLS & SHOPPING...")
    malls_result = scrape_and_ingest(
        search_terms=["shopping malls", "supermarkets"],
        category="mall",
        max_results=30
    )
    
    # Summary
    print("\n" + "=" * 70)
    print("SCRAPING COMPLETE - SUMMARY")
    print("=" * 70)
    
    if schools_result:
        print(f"Schools: {schools_result['items_count']} scraped, {schools_result['stats']['inserted']} inserted")
    if hospitals_result:
        print(f"Hospitals: {hospitals_result['items_count']} scraped, {hospitals_result['stats']['inserted']} inserted")
    if malls_result:
        print(f"Malls: {malls_result['items_count']} scraped, {malls_result['stats']['inserted']} inserted")


if __name__ == "__main__":
    main()
