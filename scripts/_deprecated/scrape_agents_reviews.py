"""
Scrape Real Estate Agents and POI Reviews/Ratings for Valora AI
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


def ensure_agents_table():
    """Create real estate agents table."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS real_estate_agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT UNIQUE,
            name TEXT NOT NULL,
            company TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            address TEXT,
            latitude REAL,
            longitude REAL,
            rating REAL,
            reviews_count INTEGER,
            specialization TEXT,
            areas_served TEXT,
            source TEXT DEFAULT 'google_maps',
            source_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agents_rating ON real_estate_agents(rating DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agents_area ON real_estate_agents(areas_served)")
    
    conn.commit()
    conn.close()


def run_scraper_with_reviews(searches: list, max_results: int = 100, include_reviews: bool = True) -> dict:
    """Run Google Maps scraper with reviews enabled."""
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
        "includeReviews": include_reviews,
        "includeImages": False,
        "scrapeDirectories": False,
        "maxImages": 0,
        "maxReviews": 5 if include_reviews else 0,  # Get top 5 reviews per place
        "reviewsSort": "newest",
        "personalData": False
    }
    
    url = f"{APIFY_BASE_URL}/acts/{ACTOR_ID}/runs"
    
    try:
        response = requests.post(url, headers=headers, json=actor_input, timeout=30)
        response.raise_for_status()
        run_data = response.json()["data"]
        return {"run_id": run_data["id"], "status": run_data["status"]}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def wait_for_run(run_id: str, max_wait: int = 600) -> dict:
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
            
            elapsed = int(time.time() - start)
            print(f"     Status: {data['status']} ({elapsed}s)")
            time.sleep(15)
        except:
            time.sleep(10)
    
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


def ingest_agents(items: list) -> dict:
    """Ingest real estate agents to database."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    stats = {"inserted": 0, "updated": 0, "skipped": 0}
    
    for item in items:
        try:
            name = item.get("title", "")
            lat = item.get("location", {}).get("lat")
            lng = item.get("location", {}).get("lng")
            
            if not name:
                stats["skipped"] += 1
                continue
            
            agent_id = f"gmaps_{item.get('placeId', '')}"
            phone = item.get("phone", "")
            website = item.get("website", "")
            address = item.get("address", "")
            rating = item.get("totalScore")
            reviews_count = item.get("reviewsCount")
            
            # Extract company name from title or categories
            categories = item.get("categories", [])
            company = name  # Usually the business name is the company
            
            # Extract reviews for insights
            reviews = item.get("reviews", [])
            reviews_text = [r.get("text", "") for r in reviews[:5] if r.get("text")]
            
            source_data = json.dumps({
                "place_id": item.get("placeId"),
                "categories": categories,
                "reviews": reviews_text,
                "opening_hours": item.get("openingHours"),
                "url": item.get("url")
            })
            
            cursor.execute("SELECT agent_id FROM real_estate_agents WHERE agent_id = ?", (agent_id,))
            
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE real_estate_agents SET 
                        name = ?, phone = ?, website = ?, address = ?,
                        latitude = ?, longitude = ?, rating = ?, reviews_count = ?,
                        source_data = ?
                    WHERE agent_id = ?
                """, (name, phone, website, address, lat, lng, rating, reviews_count,
                      source_data, agent_id))
                stats["updated"] += 1
            else:
                cursor.execute("""
                    INSERT INTO real_estate_agents 
                    (agent_id, name, company, phone, website, address,
                     latitude, longitude, rating, reviews_count, source_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (agent_id, name, company, phone, website, address,
                      lat, lng, rating, reviews_count, source_data))
                stats["inserted"] += 1
                
        except Exception as e:
            stats["skipped"] += 1
    
    conn.commit()
    conn.close()
    return stats


def update_pois_with_reviews(items: list, category: str) -> dict:
    """Update POIs with review data."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    stats = {"updated": 0, "skipped": 0}
    
    for item in items:
        try:
            place_id = item.get("placeId", "")
            poi_id = f"gmaps_{place_id}"
            
            rating = item.get("totalScore")
            reviews_count = item.get("reviewsCount")
            reviews = item.get("reviews", [])
            
            # Get top reviews text
            reviews_text = [r.get("text", "")[:500] for r in reviews[:5] if r.get("text")]
            
            # Update source_data with reviews
            cursor.execute("SELECT source_data FROM pois WHERE poi_id = ?", (poi_id,))
            row = cursor.fetchone()
            
            if row:
                try:
                    existing = json.loads(row[0]) if row[0] else {}
                except:
                    existing = {}
                
                existing["rating"] = rating
                existing["reviews_count"] = reviews_count
                existing["top_reviews"] = reviews_text
                
                cursor.execute("""
                    UPDATE pois SET source_data = ? WHERE poi_id = ?
                """, (json.dumps(existing), poi_id))
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
                
        except:
            stats["skipped"] += 1
    
    conn.commit()
    conn.close()
    return stats


def main():
    print("=" * 70)
    print("VALORA AI - AGENTS & REVIEWS SCRAPER")
    print("=" * 70)
    
    if not APIFY_TOKEN:
        print("\n❌ APIFY_API_TOKEN not set!")
        return
    
    # Ensure agents table exists
    ensure_agents_table()
    
    # 1. Scrape Real Estate Agents
    print("\n[1/2] Scraping REAL ESTATE AGENTS with reviews...")
    print("     Searches: real estate agents, property dealers, property consultants")
    
    run = run_scraper_with_reviews(
        searches=["real estate agents", "property dealers", "property consultants", 
                  "real estate brokers", "flat brokers"],
        max_results=100,
        include_reviews=True
    )
    
    if run:
        print(f"     Run ID: {run['run_id']}")
        result = wait_for_run(run["run_id"], max_wait=600)
        
        if result["status"] == "SUCCEEDED":
            items = download_dataset(result["dataset_id"])
            print(f"     Downloaded: {len(items)} agents")
            
            # Save raw
            output_file = DATA_DIR / f"agents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            
            # Ingest
            stats = ingest_agents(items)
            print(f"     ✓ Inserted: {stats['inserted']}, Updated: {stats['updated']}")
    
    # 2. Scrape top-rated schools/hospitals with reviews for quality insights
    print("\n[2/2] Scraping TOP-RATED places with reviews for quality analysis...")
    
    categories_to_update = [
        {"searches": ["best schools", "top rated schools"], "category": "school"},
        {"searches": ["best hospitals", "top rated hospitals"], "category": "hospital"},
        {"searches": ["best restaurants", "top rated restaurants"], "category": "restaurant"},
    ]
    
    for cat in categories_to_update:
        print(f"\n     Updating {cat['category']} with reviews...")
        
        run = run_scraper_with_reviews(
            searches=cat["searches"],
            max_results=50,
            include_reviews=True
        )
        
        if run:
            result = wait_for_run(run["run_id"], max_wait=300)
            
            if result["status"] == "SUCCEEDED":
                items = download_dataset(result["dataset_id"])
                print(f"     Downloaded: {len(items)} {cat['category']}s with reviews")
                
                stats = update_pois_with_reviews(items, cat["category"])
                print(f"     ✓ Updated {stats['updated']} POIs with review data")
    
    # Summary
    print("\n" + "=" * 70)
    print("SCRAPING COMPLETE")
    print("=" * 70)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM real_estate_agents")
    agents_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM real_estate_agents WHERE rating IS NOT NULL")
    rated_agents = cursor.fetchone()[0]
    
    print(f"\nReal Estate Agents: {agents_count}")
    print(f"Agents with ratings: {rated_agents}")
    
    # Show top agents
    cursor.execute("""
        SELECT name, rating, reviews_count, phone 
        FROM real_estate_agents 
        WHERE rating IS NOT NULL 
        ORDER BY rating DESC, reviews_count DESC 
        LIMIT 10
    """)
    
    print("\nTop 10 Rated Agents:")
    for row in cursor.fetchall():
        print(f"  ⭐ {row[1]:.1f} ({row[2]} reviews) - {row[0]} | {row[3] or 'No phone'}")
    
    conn.close()


if __name__ == "__main__":
    main()
