"""
Apify Service for Valora - MagicBricks Property Scraper
Provides backend API for frontend-controlled scraping with real-time progress tracking.
"""

import os
import json
import requests
import time
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

load_dotenv()

# === CONFIGURATION ===
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
APIFY_BASE_URL = "https://api.apify.com/v2"

# MagicBricks Actor (from user's Apify console)
ACTOR_ID = "ecomscrape~magicbricks-property-search-scraper"

# Directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "storage"
PROPERTIES_DIR = DATA_DIR / "posted_properties"
RAW_DATA_DIR = BASE_DIR / "scripts" / "ingest" / "raw_data"
STATUS_FILE = DATA_DIR / "ingestion_status.json"
HISTORY_FILE = DATA_DIR / "scrape_history.json"

# Create directories
PROPERTIES_DIR.mkdir(parents=True, exist_ok=True)
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# === SCRAPER STATE ===
@dataclass
class ScrapeState:
    status: str = "idle"  # idle, starting, running, completed, failed, stopped
    run_id: Optional[str] = None
    dataset_id: Optional[str] = None
    started_at: Optional[str] = None
    message: str = ""
    category: str = ""
    location: str = ""
    items_found: int = 0
    items_processed: int = 0
    items_valid: int = 0
    elapsed_seconds: int = 0
    eta_seconds: Optional[int] = None
    progress_percent: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

# Global state
current_scrape = ScrapeState()
scrape_thread: Optional[threading.Thread] = None
stop_requested = False


def get_status() -> Dict[str, Any]:
    """Get current scrape status for API."""
    global current_scrape
    return {
        **asdict(current_scrape),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def update_status(
    status: str = None,
    message: str = None,
    items_found: int = None,
    items_processed: int = None,
    items_valid: int = None,
    progress_percent: float = None,
    eta_seconds: int = None,
    error: str = None
):
    """Update scrape state and write to status file."""
    global current_scrape
    
    if status:
        current_scrape.status = status
    if message:
        current_scrape.message = message
    if items_found is not None:
        current_scrape.items_found = items_found
    if items_processed is not None:
        current_scrape.items_processed = items_processed
    if items_valid is not None:
        current_scrape.items_valid = items_valid
    if progress_percent is not None:
        current_scrape.progress_percent = progress_percent
    if eta_seconds is not None:
        current_scrape.eta_seconds = eta_seconds
    if error:
        current_scrape.errors.append(error)
    
    # Calculate elapsed time
    if current_scrape.started_at:
        started = datetime.fromisoformat(current_scrape.started_at.replace('Z', '+00:00'))
        current_scrape.elapsed_seconds = int((datetime.now(timezone.utc) - started).total_seconds())
    
    # Write to status file
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(get_status(), f, indent=2)


def normalize_magicbricks_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize MagicBricks actor output to Valora schema."""
    try:
        # Extract coordinates
        lat = item.get("latitude") or item.get("lat") or item.get("geo", {}).get("lat")
        lng = item.get("longitude") or item.get("lng") or item.get("lon") or item.get("geo", {}).get("lng")
        
        # Try alternative location fields
        if not lat or not lng:
            location_data = item.get("location", {})
            if isinstance(location_data, dict):
                lat = location_data.get("lat") or location_data.get("latitude")
                lng = location_data.get("lng") or location_data.get("longitude")
        
        # Skip items without coordinates
        if not lat or not lng:
            return None
        
        # Extract price (handle various formats)
        price = item.get("price") or item.get("priceValue") or 0
        if isinstance(price, str):
            price = int(''.join(filter(str.isdigit, price)) or 0)
        
        # Extract area
        area = item.get("area") or item.get("carpetArea") or item.get("builtUpArea") or item.get("superBuiltUpArea") or 0
        if isinstance(area, str):
            area = int(''.join(filter(str.isdigit, area)) or 0)
        
        return {
            "id": item.get("id") or item.get("propertyId") or f"mb_{hash(str(item))}",
            "name": item.get("title") or item.get("propertyName") or item.get("name") or "Property",
            "price": int(price),
            "price_per_sq_ft": int(item.get("pricePerSqft") or item.get("pricePerSqFt") or 0),
            "bedrooms": int(item.get("bedrooms") or item.get("bhk") or item.get("bedroom") or 0),
            "bathrooms": int(item.get("bathrooms") or item.get("bathroom") or 0),
            "covered_area": int(area),
            "location": f"{lat},{lng}",
            "latitude": float(lat),
            "longitude": float(lng),
            "address": item.get("address") or item.get("locality") or item.get("location"),
            "locality": item.get("locality") or item.get("society"),
            "city": item.get("city") or "Bangalore",
            "description": item.get("description"),
            "posted_on": item.get("postedOn") or item.get("postedDate"),
            "property_type": item.get("propertyType") or item.get("type"),
            "transaction_type": item.get("transactionType") or item.get("listingType"),
            "furnishing": item.get("furnishing") or item.get("furnishingStatus"),
            "floor": item.get("floor") or item.get("floorNumber"),
            "total_floors": item.get("totalFloors"),
            "age": item.get("age") or item.get("propertyAge"),
            "facing": item.get("facing"),
            "amenities": item.get("amenities") or [],
            "images": item.get("images") or item.get("photos") or [],
            "url": item.get("url") or item.get("propertyUrl"),
            "source": "magicbricks",
            "source_actor": ACTOR_ID,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "raw_data": item
        }
    except Exception as e:
        print(f"[Normalize] Error: {e}")
        return None


def run_scrape_async(config: Dict[str, Any]):
    """Run scrape in background thread."""
    global current_scrape, stop_requested
    
    try:
        stop_requested = False
        current_scrape = ScrapeState(
            status="starting",
            started_at=datetime.now(timezone.utc).isoformat(),
            category=config.get("category", "buy"),
            location=config.get("location", "Bangalore"),
            message="Initializing scraper..."
        )
        update_status()
        
        # Prepare actor input based on MagicBricks actor schema
        actor_input = {
            "searchType": config.get("search_type", "buy"),  # buy, rent, pg
            "location": config.get("location", "Bangalore"),
            "propertyType": config.get("property_type", "residential"),
            "maxItems": config.get("max_items", 1000),
            "minPrice": config.get("min_price"),
            "maxPrice": config.get("max_price"),
            "minBedrooms": config.get("min_bedrooms"),
            "maxBedrooms": config.get("max_bedrooms"),
        }
        
        # Remove None values
        actor_input = {k: v for k, v in actor_input.items() if v is not None}
        
        headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
        
        # Start actor run
        update_status(status="running", message="Starting Apify actor...")
        
        run_url = f"{APIFY_BASE_URL}/acts/{ACTOR_ID}/runs"
        response = requests.post(run_url, json=actor_input, headers=headers, timeout=60)
        response.raise_for_status()
        
        run_data = response.json()["data"]
        run_id = run_data["id"]
        dataset_id = run_data["defaultDatasetId"]
        
        current_scrape.run_id = run_id
        current_scrape.dataset_id = dataset_id
        update_status(message=f"Actor started (Run ID: {run_id})")
        
        # Poll for completion
        start_time = time.time()
        last_item_count = 0
        items_per_second = 0
        
        while not stop_requested:
            # Check run status
            status_url = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
            status_response = requests.get(status_url, headers=headers, timeout=30)
            status_response.raise_for_status()
            
            run_status = status_response.json()["data"]
            actor_status = run_status["status"]
            
            # Get current item count from dataset
            dataset_url = f"{APIFY_BASE_URL}/datasets/{dataset_id}"
            dataset_response = requests.get(dataset_url, headers=headers, timeout=30)
            if dataset_response.ok:
                dataset_info = dataset_response.json()["data"]
                item_count = dataset_info.get("itemCount", 0)
                current_scrape.items_found = item_count
                
                # Calculate ETA
                elapsed = time.time() - start_time
                if elapsed > 10 and item_count > last_item_count:
                    items_per_second = item_count / elapsed
                    max_items = config.get("max_items", 1000)
                    remaining = max_items - item_count
                    if items_per_second > 0 and remaining > 0:
                        current_scrape.eta_seconds = int(remaining / items_per_second)
                    
                    # Progress percent (based on max_items or estimate)
                    current_scrape.progress_percent = min(95, (item_count / max_items) * 100)
                
                last_item_count = item_count
            
            update_status(
                message=f"Scraping... {current_scrape.items_found} items found ({actor_status})",
                progress_percent=current_scrape.progress_percent
            )
            
            if actor_status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                break
            
            time.sleep(5)  # Poll every 5 seconds
        
        if stop_requested:
            # Abort the run
            abort_url = f"{APIFY_BASE_URL}/actor-runs/{run_id}/abort"
            requests.post(abort_url, headers=headers, timeout=30)
            update_status(status="stopped", message="Scrape stopped by user")
            return
        
        if actor_status != "SUCCEEDED":
            update_status(status="failed", message=f"Actor failed: {actor_status}")
            return
        
        # Fetch all items from dataset
        update_status(status="running", message="Downloading results...", progress_percent=95)
        
        all_items = []
        offset = 0
        limit = 1000
        
        while True:
            items_url = f"{APIFY_BASE_URL}/datasets/{dataset_id}/items?offset={offset}&limit={limit}"
            items_response = requests.get(items_url, headers=headers, timeout=60)
            items_response.raise_for_status()
            
            items = items_response.json()
            if not items:
                break
            
            all_items.extend(items)
            offset += limit
            
            update_status(message=f"Downloaded {len(all_items)} items...")
        
        # Save raw data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_file = RAW_DATA_DIR / f"magicbricks_{config.get('location', 'unknown')}_{timestamp}.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        
        # Normalize items
        update_status(message="Normalizing data...", progress_percent=97)
        
        normalized = []
        for item in all_items:
            norm = normalize_magicbricks_item(item)
            if norm:
                normalized.append(norm)
            current_scrape.items_processed += 1
        
        current_scrape.items_valid = len(normalized)
        
        # Save normalized data
        category = config.get("category", "residential")
        location = config.get("location", "bangalore").lower().replace(" ", "-")
        output_file = PROPERTIES_DIR / f"{location}-{category}-{timestamp}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
        
        # Also append to main file
        main_file = PROPERTIES_DIR / f"{location}-{category}.json"
        existing = []
        if main_file.exists():
            with open(main_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        
        # Merge and dedupe by ID
        existing_ids = {item.get("id") for item in existing}
        new_items = [item for item in normalized if item.get("id") not in existing_ids]
        merged = existing + new_items
        
        with open(main_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        
        # Update history
        save_history({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "location": config.get("location"),
            "category": category,
            "items_scraped": len(all_items),
            "items_valid": len(normalized),
            "items_new": len(new_items),
            "total_in_db": len(merged),
            "run_id": run_id,
            "elapsed_seconds": int(time.time() - start_time)
        })
        
        update_status(
            status="completed",
            message=f"Completed! {len(normalized)} valid items, {len(new_items)} new added to database",
            progress_percent=100,
            items_valid=len(normalized)
        )
        
    except Exception as e:
        update_status(status="failed", message=str(e), error=str(e))
        print(f"[Scrape Error] {e}")


def save_history(entry: Dict[str, Any]):
    """Save scrape history entry."""
    history = []
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    
    history.append(entry)
    
    # Keep last 100 entries
    history = history[-100:]
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def get_history() -> List[Dict[str, Any]]:
    """Get scrape history."""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def start_scrape(config: Dict[str, Any]) -> Dict[str, Any]:
    """Start a new scrape (called from API)."""
    global scrape_thread, current_scrape
    
    if not APIFY_TOKEN:
        return {"success": False, "error": "APIFY_API_TOKEN not configured"}
    
    if current_scrape.status == "running":
        return {"success": False, "error": "A scrape is already running"}
    
    # Start background thread
    scrape_thread = threading.Thread(target=run_scrape_async, args=(config,), daemon=True)
    scrape_thread.start()
    
    return {"success": True, "message": "Scrape started"}


def stop_scrape() -> Dict[str, Any]:
    """Stop current scrape."""
    global stop_requested
    
    if current_scrape.status != "running":
        return {"success": False, "error": "No scrape is running"}
    
    stop_requested = True
    return {"success": True, "message": "Stop requested"}


def get_data_stats() -> Dict[str, Any]:
    """Get statistics about stored data."""
    stats = {
        "total_properties": 0,
        "files": [],
        "by_location": {},
        "by_category": {}
    }
    
    for file in PROPERTIES_DIR.glob("*.json"):
        if file.name == "ingestion_status.json":
            continue
        
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                count = len(data) if isinstance(data, list) else 0
                stats["total_properties"] += count
                stats["files"].append({
                    "name": file.name,
                    "count": count,
                    "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })
                
                # Parse location and category from filename
                parts = file.stem.split("-")
                if len(parts) >= 2:
                    location = parts[0]
                    category = parts[1] if len(parts) > 1 else "unknown"
                    
                    stats["by_location"][location] = stats["by_location"].get(location, 0) + count
                    stats["by_category"][category] = stats["by_category"].get(category, 0) + count
        except Exception as e:
            print(f"[Stats] Error reading {file}: {e}")
    
    return stats


# Configuration options for frontend dropdowns
SCRAPE_OPTIONS = {
    "search_types": [
        {"value": "buy", "label": "Buy"},
        {"value": "rent", "label": "Rent"},
        {"value": "pg", "label": "PG/Co-living"}
    ],
    "property_types": [
        {"value": "residential", "label": "Residential"},
        {"value": "commercial", "label": "Commercial"},
        {"value": "plot", "label": "Plot/Land"}
    ],
    "locations": [
        {"value": "Bangalore", "label": "Bangalore"},
        {"value": "Mumbai", "label": "Mumbai"},
        {"value": "Delhi", "label": "Delhi"},
        {"value": "Hyderabad", "label": "Hyderabad"},
        {"value": "Chennai", "label": "Chennai"},
        {"value": "Pune", "label": "Pune"},
        {"value": "Kolkata", "label": "Kolkata"},
        {"value": "Ahmedabad", "label": "Ahmedabad"},
        {"value": "Gurgaon", "label": "Gurgaon"},
        {"value": "Noida", "label": "Noida"}
    ],
    "max_items_options": [
        {"value": 100, "label": "100 (Quick Test)"},
        {"value": 500, "label": "500"},
        {"value": 1000, "label": "1,000"},
        {"value": 2500, "label": "2,500"},
        {"value": 5000, "label": "5,000"},
        {"value": 10000, "label": "10,000 (Large)"}
    ],
    "bedroom_options": [
        {"value": None, "label": "Any"},
        {"value": 1, "label": "1 BHK"},
        {"value": 2, "label": "2 BHK"},
        {"value": 3, "label": "3 BHK"},
        {"value": 4, "label": "4 BHK"},
        {"value": 5, "label": "5+ BHK"}
    ]
}


def get_scrape_options() -> Dict[str, Any]:
    """Get configuration options for frontend."""
    return SCRAPE_OPTIONS
