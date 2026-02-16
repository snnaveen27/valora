"""
Multi-Source Real Estate Scraper for Valora
Supports: MagicBricks, Housing.com, 99acres, NoBroker
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

# Actor configurations for different platforms
ACTORS = {
    "magicbricks": {
        "id": "OGrVzUv64ImXJ1Cen",
        "name": "MagicBricks",
        "icon": "🏠",
        "input_format": "urls"  # Uses urls, max_items_per_url, proxy
    },
    "housing": {
        "id": "2r88Kn1xhj9HiIvR8",
        "name": "Housing.com",
        "icon": "🏘️",
        "input_format": "urls"  # Uses urls, max_items_per_url, proxy
    },
    "99acres": {
        "id": "9dRXq58LQVDRUzLQp",  # Numeric ID as shown in Python example
        "name": "99acres",
        "icon": "🏗️",
        "input_format": "startUrls"  # Uses startUrls, locations, propertyType
    },
    "nobroker": {
        "id": "cwk6KCUCDc1iM1gUS",
        "name": "NoBroker",
        "icon": "🔑",
        "input_format": "urls"  # Uses urls, max_items_per_url, proxy
    }
}

# Directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "storage"
PROPERTIES_DIR = DATA_DIR / "posted_properties"
RAW_DATA_DIR = BASE_DIR / "scripts" / "ingest" / "raw_data"
STATUS_FILE = DATA_DIR / "multi_scrape_status.json"
HISTORY_FILE = DATA_DIR / "scrape_history.json"
MANIFEST_FILE = PROPERTIES_DIR / "index.json"

# Create directories
PROPERTIES_DIR.mkdir(parents=True, exist_ok=True)
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _safe_slug(value: Any) -> str:
    s = str(value or "unknown").strip().lower()
    return s.replace("/", "-").replace("\\", "-").replace(" ", "-")


def update_manifest(entry: Dict[str, Any]):
    manifest = {"schema_version": 1, "updated_at": datetime.now(timezone.utc).isoformat(), "datasets": []}
    if MANIFEST_FILE.exists():
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                manifest = json.load(f) or manifest
        except Exception:
            manifest = manifest

    if not isinstance(manifest, dict):
        manifest = {"schema_version": 1, "updated_at": datetime.now(timezone.utc).isoformat(), "datasets": []}

    datasets = manifest.get("datasets")
    if not isinstance(datasets, list):
        datasets = []

    datasets.append(entry)
    manifest["datasets"] = datasets[-500:]
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

# === SCRAPER STATE ===
@dataclass
class ScrapeJobState:
    """State for a single scrape job (can run multiple simultaneously)."""
    job_id: str  # unique ID: {platform}_{category}_{search_type}_{property_type}
    platform: str
    status: str = "idle"  # idle, starting, running, completed, failed, stopped, resumable
    run_id: Optional[str] = None
    dataset_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    message: str = ""
    location: str = ""
    search_type: str = ""
    property_category: str = ""
    property_type: str = ""
    items_found: int = 0
    items_processed: int = 0
    items_valid: int = 0
    items_new: int = 0
    elapsed_seconds: int = 0
    eta_seconds: Optional[int] = None
    progress_percent: float = 0.0
    errors: List[str] = None
    resumable: bool = False
    previous_dataset_ids: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.previous_dataset_ids is None:
            self.previous_dataset_ids = []


def make_job_id(platform: str, category: str, search_type: str, property_type: str) -> str:
    """Create unique job ID from scrape parameters."""
    return f"{_safe_slug(platform)}_{_safe_slug(category)}_{_safe_slug(search_type)}_{_safe_slug(property_type)}"


# Global state - dynamic dict of active/recent jobs
job_states: Dict[str, ScrapeJobState] = {}
job_states_lock = threading.Lock()

scrape_threads: Dict[str, Optional[threading.Thread]] = {}
stop_flags: Dict[str, bool] = {}


def get_all_status() -> Dict[str, Any]:
    """Get status of all jobs grouped by platform."""
    with job_states_lock:
        # Group jobs by platform
        platforms_status = {platform: [] for platform in ACTORS.keys()}
        for job_id, state in job_states.items():
            if state.platform in platforms_status:
                platforms_status[state.platform].append(asdict(state))
        
        # Also include summary per platform
        platform_summaries = {}
        for platform in ACTORS.keys():
            jobs = platforms_status[platform]
            running_jobs = [j for j in jobs if j["status"] in ("running", "starting")]
            platform_summaries[platform] = {
                "platform": platform,
                "total_jobs": len(jobs),
                "running_jobs": len(running_jobs),
                "status": "running" if running_jobs else "idle",
                "jobs": jobs
            }
        
        return {
            "platforms": platform_summaries,
            "all_jobs": {job_id: asdict(state) for job_id, state in job_states.items()},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def get_platform_status(platform: str) -> Dict[str, Any]:
    """Get status of all jobs for a specific platform."""
    if platform not in ACTORS:
        return {"error": f"Unknown platform: {platform}"}
    
    with job_states_lock:
        jobs = [asdict(state) for state in job_states.values() if state.platform == platform]
        running_jobs = [j for j in jobs if j["status"] in ("running", "starting")]
        
        return {
            "platform": platform,
            "total_jobs": len(jobs),
            "running_jobs": len(running_jobs),
            "status": "running" if running_jobs else "idle",
            "jobs": jobs,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get status of a specific job."""
    with job_states_lock:
        if job_id not in job_states:
            return {"error": f"Unknown job: {job_id}", "status": "idle"}
        return {
            **asdict(job_states[job_id]),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def update_job_status(
    job_id: str,
    status: str = None,
    message: str = None,
    items_found: int = None,
    items_processed: int = None,
    items_valid: int = None,
    items_new: int = None,
    progress_percent: float = None,
    eta_seconds: int = None,
    error: str = None,
    run_id: str = None,
    dataset_id: str = None
):
    """Update job scrape state and write to status file."""
    with job_states_lock:
        if job_id not in job_states:
            return
        
        state = job_states[job_id]
        
        if status:
            state.status = status
            if status == "completed":
                state.completed_at = datetime.now(timezone.utc).isoformat()
        if message:
            state.message = message
        if items_found is not None:
            state.items_found = items_found
        if items_processed is not None:
            state.items_processed = items_processed
        if items_valid is not None:
            state.items_valid = items_valid
        if items_new is not None:
            state.items_new = items_new
        if progress_percent is not None:
            state.progress_percent = progress_percent
        if eta_seconds is not None:
            state.eta_seconds = eta_seconds
        if error:
            state.errors.append(error)
        if run_id:
            state.run_id = run_id
        if dataset_id:
            state.dataset_id = dataset_id
        
        # Calculate elapsed time
        if state.started_at:
            started = datetime.fromisoformat(state.started_at.replace('Z', '+00:00'))
            state.elapsed_seconds = int((datetime.now(timezone.utc) - started).total_seconds())
    
    # Write to status file (outside lock to avoid blocking)
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(get_all_status(), f, indent=2)
    except Exception as e:
        print(f"[Status] Error writing status file: {e}")


def build_search_url(platform: str, config: Dict[str, Any]) -> str:
    """Build search URL for each platform based on configuration."""
    location = config.get("location", "Bangalore").replace(" ", "-")
    search_type = config.get("search_type", "buy")
    property_type = config.get("property_type", "flat")
    property_category = config.get("property_category", "residential")  # FIXED: Extract from config
    bedrooms = config.get("min_bedrooms")
    
    # Debug: Log URL building for 99acres
    if platform == "99acres":
        print(f"[99acres] Building URL - category: {property_category}, type: {property_type}, search: {search_type}")
    
    if platform == "magicbricks":
        # Map search types to MagicBricks URL format
        search_type_map = {
            "buy": "sale",
            "rent": "rent",
            "pg": "rent",  # PG uses rent endpoint
            "lease": "rent"  # Lease uses rent endpoint
        }
        url_search_type = search_type_map.get(search_type, "sale")
        
        # Map property types to MagicBricks format
        prop_type_map = {
            # Residential
            "flat": "Multistorey-Apartment",
            "house-villa": "Residential-House",
            "plot": "Residential-Plot",
            "pg": "PG",
            "coliving": "PG",
            # Commercial
            "office": "Office-Space",
            "shop": "Shop-Showroom",
            "commercial-land": "Commercial-Land",
            "warehouse": "Warehouse-Godown",
            "industrial-building": "Industrial-Building",
            "industrial-shed": "Industrial-Shed",
            # Other
            "agricultural-land": "Agricultural-Land",
            "farm-house": "Farm-House"
        }
        
        proptype = prop_type_map.get(property_type, "Multistorey-Apartment")
        bedroom_param = f"&bedroom={bedrooms}" if bedrooms else ""
        
        return f"https://www.magicbricks.com/property-for-{url_search_type}/residential-real-estate?proptype={proptype}&cityName={location}{bedroom_param}"
    
    elif platform == "housing":
        # Housing.com URL patterns vary by search type
        location_slug = location.lower().replace(" ", "-")
        
        # Map search types to Housing.com URL format
        search_type_map = {
            "buy": "buy",
            "rent": "rent",
            "pg": "hostels-pg",
            "flatmates": "flatmates",
            "lease": "rent"  # Commercial lease uses rent
        }
        url_search_type = search_type_map.get(search_type, "buy")
        
        # Map property types to Housing.com format
        prop_type_map = {
            # Residential Buy
            "apartment": "apartment",
            "independent-house": "independent-house",
            "independent-floor": "independent-floor",
            "plot": "plot",
            "studio": "studio-apartment",
            "duplex": "duplex",
            "penthouse": "penthouse",
            "villa": "villa",
            "agricultural-land": "agricultural-land",
            # Commercial
            "ready-office": "ready-to-move-office-space",
            "bare-shell-office": "bare-shell-office-space",
            "shop": "shop",
            "showroom": "showroom",
            "commercial-plot": "commercial-land",
            "warehouse": "warehouse",
            "other": "other-property-type",
            # PG & Flatmates
            "pg": "pg",
            "flatmates": "flatmates"
        }
        
        property_slug = prop_type_map.get(property_type, "apartment")
        
        # Build URL based on search type
        if search_type in ["pg", "flatmates"]:
            # PG and flatmates have different URL structure
            return f"https://housing.com/in/{url_search_type}/{location_slug}"
        else:
            # Buy/Rent URLs include property type
            return f"https://housing.com/in/{url_search_type}/{property_slug}/{location_slug}"
    
    elif platform == "99acres":
        # 99acres URL patterns
        location_slug = location.lower().replace(" ", "-")
        
        # Map search types to 99acres URL format
        search_type_map = {
            "buy": "buy",
            "rent": "rent",
            "lease": "rent"  # Commercial lease uses rent
        }
        url_search_type = search_type_map.get(search_type, "buy")
        
        # Map property types to 99acres format
        prop_type_map = {
            # Residential
            "flat-apartment": "apartment-flat",
            "builder-floor": "independent-builder-floor",
            "independent-house-villa": "independent-house-villa",
            "residential-land": "residential-land",
            "studio-apartment": "studio-apartment",
            "farm-house": "farm-house",
            "serviced-apartments": "serviced-apartments",
            "other-residential": "other",
            # Commercial Buy
            "ready-to-move-office": "ready-to-move-office",
            "bare-shell-office": "bare-shell-office",
            "shop-retail": "shop-showroom",
            "commercial-land": "commercial-land",
            "agricultural-land": "agricultural-land",
            "industrial-land": "industrial-land",
            "warehouse": "warehouse",
            "cold-storage": "cold-storage",
            "factory-manufacturing": "industrial-building",
            "hotel-resort": "hotel-resort",
            "other-commercial": "other",
            # Commercial Lease
            "office-space": "office-space",
            "co-working-office": "coworking-space",
            "other-commercial-space": "other",
            "residential-plot": "residential-land",
            "commercial-plot": "commercial-land",
            "industrial-plot": "industrial-land"
        }
        
        property_slug = prop_type_map.get(property_type, "apartment-flat")
        
        # Build URL based on category
        if property_category == "commercial":
            return f"https://www.99acres.com/search/property/{url_search_type}/commercial-{property_slug}/{location_slug}"
        else:
            return f"https://www.99acres.com/search/property/{url_search_type}/{property_slug}/{location_slug}"
    
    elif platform == "nobroker":
        # NoBroker URL patterns
        location_slug = location.lower().replace(" ", "-")
        
        # Map search types to NoBroker URL format
        search_type_map = {
            "buy": "sale",
            "rent": "rent"
        }
        url_search_type = search_type_map.get(search_type, "sale")
        
        # Map property types to NoBroker format
        prop_type_map = {
            # Residential
            "full-house": "1rk-1bhk-2bhk-3bhk-3plus-bhk-house",
            "land-plot": "plot",
            "pg-hostel": "pg",
            "flatmates": "flatmates",
            # Commercial
            "office-space": "office-space",
            "co-working": "coworking-space",
            "shop": "shop",
            "showroom": "showroom",
            "industrial-building": "industrial-building",
            "industrial-shed": "industrial-shed",
            "godown-warehouse": "warehouse",
            "other-business": "other-business",
            "restaurant-cafe": "restaurant-cafe"
        }
        
        property_slug = prop_type_map.get(property_type, "1rk-1bhk-2bhk-3bhk-3plus-bhk-house")
        
        # Build URL - NoBroker uses property type in URL
        return f"https://www.nobroker.in/property/{url_search_type}/{property_slug}/{location_slug}"
    
    return ""


def prepare_actor_input(platform: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare actor input based on platform-specific format."""
    max_items = config.get("max_items", 1000)
    
    if platform in ["magicbricks", "housing", "nobroker"]:
        # These actors use urls, max_items_per_url, proxy format
        return {
            "urls": [build_search_url(platform, config)],
            "max_items_per_url": max_items,
            "max_retries_per_url": 2,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
                "apifyProxyCountry": "US"
            }
        }
    
    elif platform == "99acres":
        # 99acres uses startUrls, locations, propertyType format
        return {
            "startUrls": [build_search_url(platform, config)],
            "locations": None,
            "propertyType": config.get("search_type", "buy"),
            "minPrice": config.get("min_price"),
            "maxPrice": config.get("max_price"),
            "bedrooms": config.get("min_bedrooms"),
            "maxItems": max_items,
            "sortBy": "relevance"
        }
    
    return {}


def normalize_property_item(item: Dict[str, Any], platform: str) -> Optional[Dict[str, Any]]:
    """Normalize property data from different platforms to Valora schema."""
    try:
        # Extract coordinates - try multiple field names
        lat = None
        lng = None
        
        # Common field patterns
        lat = (item.get("latitude") or item.get("lat") or 
               item.get("geo", {}).get("lat") or
               item.get("location", {}).get("lat") or
               item.get("coordinates", {}).get("latitude"))
        
        lng = (item.get("longitude") or item.get("lng") or item.get("lon") or
               item.get("geo", {}).get("lng") or item.get("geo", {}).get("lon") or
               item.get("location", {}).get("lng") or item.get("location", {}).get("lon") or
               item.get("coordinates", {}).get("longitude"))
        
        if lat is None or lng is None:
            coords = item.get("coordinates")
            if isinstance(coords, dict):
                lat = lat or coords.get("lat") or coords.get("latitude")
                lng = lng or coords.get("lng") or coords.get("lon") or coords.get("longitude")
            elif isinstance(coords, (list, tuple)) and len(coords) >= 2:
                # Common patterns: GeoJSON uses [lng, lat]
                lng = lng or coords[0]
                lat = lat or coords[1]
        
        if lat is None or lng is None:
            loc_coords = (item.get("location", {}).get("coordinates") or
                          item.get("geo", {}).get("coordinates"))
            if isinstance(loc_coords, (list, tuple)) and len(loc_coords) >= 2:
                lng = lng or loc_coords[0]
                lat = lat or loc_coords[1]
        
        if lat is None or lng is None:
            latlng = item.get("latLng") or item.get("lat_lng") or item.get("latlng")
            if isinstance(latlng, str):
                parts = [p.strip() for p in latlng.replace(";", ",").split(",") if p.strip()]
                if len(parts) >= 2:
                    lat = lat or parts[0]
                    lng = lng or parts[1]
        
        # Skip items without coordinates
        if lat is None or lng is None:
            return None

        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except Exception:
            return None
        
        # Extract price (handle various formats)
        price = item.get("price") or item.get("priceValue") or item.get("rent") or 0
        if isinstance(price, str):
            price = int(''.join(filter(str.isdigit, price)) or 0)
        
        # Extract area
        area = (item.get("area") or item.get("carpetArea") or 
                item.get("builtUpArea") or item.get("superBuiltUpArea") or
                item.get("builtupArea") or item.get("size") or 0)
        if isinstance(area, str):
            area = int(''.join(filter(str.isdigit, area)) or 0)
        
        # Extract bedrooms
        bedrooms = (item.get("bedrooms") or item.get("bhk") or 
                   item.get("bedroom") or item.get("beds") or 0)
        if isinstance(bedrooms, str):
            bedrooms = int(''.join(filter(str.isdigit, bedrooms)) or 0)
        
        # Extract bathrooms
        bathrooms = (item.get("bathrooms") or item.get("bathroom") or 
                    item.get("baths") or 0)
        if isinstance(bathrooms, str):
            bathrooms = int(''.join(filter(str.isdigit, bathrooms)) or 0)
        
        return {
            "id": item.get("id") or item.get("propertyId") or f"{platform}_{hash(str(item))}",
            "name": item.get("title") or item.get("propertyName") or item.get("name") or "Property",
            "price": int(price),
            "price_per_sq_ft": int(item.get("pricePerSqft") or item.get("pricePerSqFt") or item.get("rate") or 0),
            "bedrooms": int(bedrooms),
            "bathrooms": int(bathrooms),
            "covered_area": int(area),
            "location": f"{lat_f},{lng_f}",
            "latitude": lat_f,
            "longitude": lng_f,
            "address": item.get("address") or item.get("locality") or item.get("location"),
            "locality": item.get("locality") or item.get("society") or item.get("area"),
            "city": item.get("city") or "Bangalore",
            "description": item.get("description") or item.get("desc"),
            "posted_on": item.get("postedOn") or item.get("postedDate") or item.get("listedDate"),
            "property_type": item.get("propertyType") or item.get("type") or item.get("category"),
            "transaction_type": item.get("transactionType") or item.get("listingType") or item.get("purpose"),
            "furnishing": item.get("furnishing") or item.get("furnishingStatus"),
            "floor": item.get("floor") or item.get("floorNumber"),
            "total_floors": item.get("totalFloors"),
            "age": item.get("age") or item.get("propertyAge") or item.get("constructionAge"),
            "facing": item.get("facing"),
            "amenities": item.get("amenities") or item.get("features") or [],
            "images": item.get("images") or item.get("photos") or item.get("imageUrls") or [],
            "url": item.get("url") or item.get("propertyUrl") or item.get("link"),
            "source": platform,
            "source_actor": ACTORS[platform]["id"],
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "raw_data": item
        }
    except Exception as e:
        print(f"[{platform}] Normalize error: {e}")
        return None


def fetch_dataset_items(dataset_id: str, headers: Dict[str, str], job_id: Optional[str] = None) -> List[Dict[str, Any]]:
    all_items: List[Dict[str, Any]] = []
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

        if job_id:
            update_job_status(job_id, message=f"Downloaded {len(all_items)} items...")

    return all_items


def run_job_scrape_async(job_id: str, platform: str, config: Dict[str, Any]):
    """Run scrape for a specific job in background thread."""
    try:
        stop_flags[job_id] = False
        
        # Initialize job state
        with job_states_lock:
            job_states[job_id] = ScrapeJobState(
                job_id=job_id,
                platform=platform,
                status="starting",
                started_at=datetime.now(timezone.utc).isoformat(),
                location=config.get("location", "Bangalore"),
                search_type=config.get("search_type", "buy"),
                property_category=config.get("property_category", "residential"),
                property_type=config.get("property_type", "unknown"),
                message="Initializing scraper...",
                errors=[]
            )
        
        update_job_status(job_id)
        
        # Prepare actor input based on platform
        actor_input = prepare_actor_input(platform, config)
        
        headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
        actor_id = ACTORS[platform]["id"]
        
        # Start actor run
        update_job_status(job_id, status="running", message="Starting Apify actor...")
        
        run_url = f"{APIFY_BASE_URL}/acts/{actor_id}/runs"
        response = requests.post(run_url, json=actor_input, headers=headers, timeout=60)
        response.raise_for_status()
        
        run_data = response.json()["data"]
        run_id = run_data["id"]
        dataset_id = run_data["defaultDatasetId"]
        
        update_job_status(
            job_id,
            message=f"Actor started (Run ID: {run_id})",
            run_id=run_id,
            dataset_id=dataset_id
        )
        
        # Poll for completion
        start_time = time.time()
        last_item_count = 0
        actor_status = "UNKNOWN"
        
        while not stop_flags.get(job_id, False):
            # Check run status
            status_url = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
            status_response = requests.get(status_url, headers=headers, timeout=30)
            status_response.raise_for_status()
            
            run_status = status_response.json()["data"]
            actor_status = run_status["status"]
            
            # Get current item count
            dataset_url = f"{APIFY_BASE_URL}/datasets/{dataset_id}"
            dataset_response = requests.get(dataset_url, headers=headers, timeout=30)
            if dataset_response.ok:
                dataset_info = dataset_response.json()["data"]
                item_count = dataset_info.get("itemCount", 0)
                
                # Calculate ETA
                elapsed = time.time() - start_time
                if elapsed > 10 and item_count > last_item_count:
                    items_per_second = item_count / elapsed
                    max_items = config.get("max_items", 1000)
                    remaining = max_items - item_count
                    eta = int(remaining / items_per_second) if items_per_second > 0 and remaining > 0 else None
                    progress = min(95, (item_count / max_items) * 100)
                else:
                    eta = None
                    progress = 0
                
                update_job_status(
                    job_id,
                    message=f"Scraping... {item_count} items found ({actor_status})",
                    items_found=item_count,
                    progress_percent=progress,
                    eta_seconds=eta
                )
                
                last_item_count = item_count
            
            if actor_status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                break
            
            time.sleep(5)

        was_stopped = stop_flags.get(job_id, False)
        if was_stopped:
            abort_url = f"{APIFY_BASE_URL}/actor-runs/{run_id}/abort"
            try:
                requests.post(abort_url, headers=headers, timeout=30)
            except Exception:
                pass
            actor_status = "ABORTED"

        if actor_status == "SUCCEEDED":
            update_job_status(job_id, message="Downloading results...", progress_percent=95)
        else:
            update_job_status(job_id, message=f"Actor ended: {actor_status}. Downloading available results...", progress_percent=95)

        all_items = []
        try:
            # Fetch items from current run
            all_items = fetch_dataset_items(dataset_id, headers, job_id)
            
            # If this is a resumed job, also fetch from previous datasets
            with job_states_lock:
                if job_id in job_states and job_states[job_id].previous_dataset_ids:
                    prev_datasets = job_states[job_id].previous_dataset_ids
                    update_job_status(job_id, message=f"Resuming: fetching from {len(prev_datasets)} previous dataset(s)...")
                    
                    for prev_dataset_id in prev_datasets:
                        try:
                            prev_items = fetch_dataset_items(prev_dataset_id, headers)
                            all_items.extend(prev_items)
                            update_job_status(job_id, message=f"Merged {len(prev_items)} items from previous run...")
                        except Exception as prev_e:
                            print(f"[{job_id}] Could not fetch from previous dataset {prev_dataset_id}: {prev_e}")
        except Exception as e:
            update_job_status(job_id, message=f"Failed to download dataset items: {e}")
            all_items = []

        # Save raw data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_file = RAW_DATA_DIR / f"{platform}_{config.get('location', 'unknown')}_{timestamp}.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        
        # Normalize items
        update_job_status(job_id, message="Normalizing data...", progress_percent=97)
        
        normalized = []
        skipped_no_coords = 0
        for item in all_items:
            norm = normalize_property_item(item, platform)
            if norm:
                normalized.append(norm)
            else:
                skipped_no_coords += 1

        update_job_status(job_id, items_processed=len(all_items), items_valid=len(normalized))
        
        # Save normalized data
        # Structure: src/data/posted_properties/{source}/{YYYY-MM-DD}/{location}_{search-type}_{category}_{property-type}/
        location_slug = _safe_slug(config.get("location", "bangalore"))
        search_type = _safe_slug(config.get("search_type", "buy"))
        category = _safe_slug(config.get("property_category", "residential"))
        property_type = _safe_slug(config.get("property_type", "unknown"))
        
        # Date-based organization for tracking
        scrape_date = datetime.now().strftime("%Y-%m-%d")
        dataset_name = f"{location_slug}_{search_type}_{category}_{property_type}"
        
        # Source subfolder → Date subfolder → Dataset subfolder
        dataset_dir = PROPERTIES_DIR / _safe_slug(platform) / scrape_date / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)

        run_file = dataset_dir / f"data_{timestamp}.json"
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)

        # Also maintain a latest.json at source level for quick access
        source_dir = PROPERTIES_DIR / _safe_slug(platform)
        main_file = source_dir / f"{dataset_name}_latest.json"
        existing = []
        if main_file.exists():
            with open(main_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        
        # Dedupe by ID
        existing_ids = {item.get("id") for item in existing}
        new_items = [item for item in normalized if item.get("id") not in existing_ids]
        merged = existing + new_items

        with open(main_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        meta = {
            "schema_version": 1,
            "job_id": job_id,
            "platform": platform,
            "platform_name": ACTORS.get(platform, {}).get("name"),
            "actor_id": ACTORS.get(platform, {}).get("id"),
            "scrape_date": scrape_date,
            "location": config.get("location"),
            "search_type": config.get("search_type"),
            "property_category": config.get("property_category"),
            "property_type": config.get("property_type"),
            "dataset_name": dataset_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "dataset_id": dataset_id,
            "items_scraped": len(all_items),
            "items_valid": len(normalized),
            "items_new": len(new_items),
            "total_in_dataset": len(merged),
            "paths": {
                "data_file": str(run_file.relative_to(BASE_DIR)).replace("\\", "/"),
                "latest_file": str(main_file.relative_to(BASE_DIR)).replace("\\", "/"),
                "raw_file": str(raw_file.relative_to(BASE_DIR)).replace("\\", "/"),
                "dataset_dir": str(dataset_dir.relative_to(BASE_DIR)).replace("\\", "/")
            },
            "storage_structure": {
                "source": _safe_slug(platform),
                "date": scrape_date,
                "dataset": dataset_name
            }
        }
        meta_file = dataset_dir / f"metadata_{timestamp}.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        # Also save a README in the dataset directory for documentation
        readme_file = dataset_dir / "README.txt"
        readme_content = f"""Dataset Information
==================
Job ID: {job_id}
Platform: {ACTORS.get(platform, {}).get('name')} ({platform})
Scrape Date: {scrape_date}
Location: {config.get('location')}
Search Type: {config.get('search_type')}
Category: {config.get('property_category')}
Property Type: {config.get('property_type')}

Files in this directory:
- data_{timestamp}.json: Normalized property data from this scrape run
- metadata_{timestamp}.json: Detailed metadata about this scrape
- README.txt: This file

Statistics:
- Items Scraped: {len(all_items)}
- Valid Items: {len(normalized)}
- New Items Added: {len(new_items)}
- Total in Latest Dataset: {len(merged)}

For the latest merged dataset, see:
{str(main_file.relative_to(BASE_DIR)).replace(chr(92), '/')}
"""
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        # Update history
        history_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id,
            "platform": platform,
            "location": config.get("location"),
            "search_type": config.get("search_type"),
            "property_category": config.get("property_category"),
            "property_type": config.get("property_type"),
            "items_scraped": len(all_items),
            "items_valid": len(normalized),
            "items_new": len(new_items),
            "total_in_db": len(merged),
            "run_id": run_id,
            "elapsed_seconds": int(time.time() - start_time),
            "paths": meta.get("paths"),
        }
        save_history(history_entry)
        update_manifest(meta)
        
        if actor_status == "SUCCEEDED":
            final_status = "completed"
            final_msg = f"Completed! {len(normalized)} valid items, {len(new_items)} new added"
            resumable = False
        elif actor_status == "ABORTED":
            final_status = "stopped"
            final_msg = f"Stopped by user. Saved {len(all_items)} raw items, {len(normalized)} valid"
            resumable = False
        elif actor_status == "TIMED-OUT":
            final_status = "resumable"
            final_msg = f"Timed out. Saved {len(all_items)} raw items, {len(normalized)} valid. You can resume."
            resumable = True
        else:
            final_status = "failed"
            final_msg = f"Actor failed: {actor_status}. Saved {len(all_items)} raw items, {len(normalized)} valid"
            resumable = actor_status in ["TIMED-OUT"]

        if skipped_no_coords:
            final_msg = f"{final_msg} (skipped {skipped_no_coords} without coords)"

        with job_states_lock:
            if job_id in job_states:
                job_states[job_id].resumable = resumable
                if resumable and dataset_id:
                    if dataset_id not in job_states[job_id].previous_dataset_ids:
                        job_states[job_id].previous_dataset_ids.append(dataset_id)

        update_job_status(
            job_id,
            status=final_status,
            message=final_msg,
            progress_percent=100,
            items_new=len(new_items)
        )

    except Exception as e:
        update_job_status(job_id, status="failed", message=str(e), error=str(e))
        print(f"[{job_id}] Scrape error: {e}")


def save_history(entry: Dict[str, Any]):
    """Save scrape history entry."""
    history = []
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    
    history.append(entry)
    history = history[-100:]  # Keep last 100
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def get_history() -> List[Dict[str, Any]]:
    """Get scrape history."""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def start_platform_scrape(platform: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Start scrape for a specific platform and property type combination."""
    if not APIFY_TOKEN:
        return {"success": False, "error": "APIFY_API_TOKEN not configured"}
    
    if platform not in ACTORS:
        return {"success": False, "error": f"Unknown platform: {platform}"}
    
    # Create unique job ID
    job_id = make_job_id(
        platform,
        config.get("property_category", "residential"),
        config.get("search_type", "buy"),
        config.get("property_type", "unknown")
    )
    
    # Check if this exact job is already running
    with job_states_lock:
        if job_id in job_states and job_states[job_id].status in ("running", "starting"):
            return {"success": False, "error": f"This scrape job is already running", "job_id": job_id}
    
    # Start background thread
    thread = threading.Thread(
        target=run_job_scrape_async,
        args=(job_id, platform, config),
        daemon=True
    )
    thread.start()
    scrape_threads[job_id] = thread
    
    return {
        "success": True, 
        "message": f"{ACTORS[platform]['name']} scrape started",
        "job_id": job_id
    }


def stop_platform_scrape(platform: str, job_id: str = None) -> Dict[str, Any]:
    """Stop scrape for a specific platform or job."""
    if platform not in ACTORS:
        return {"success": False, "error": f"Unknown platform: {platform}"}
    
    if job_id:
        # Stop specific job
        with job_states_lock:
            if job_id not in job_states:
                return {"success": False, "error": f"Job not found: {job_id}"}
            if job_states[job_id].status not in ("running", "starting"):
                return {"success": False, "error": f"Job is not running: {job_id}"}
        
        stop_flags[job_id] = True
        return {"success": True, "message": f"Stop requested for job: {job_id}", "job_id": job_id}
    else:
        # Stop all running jobs for this platform
        stopped_jobs = []
        with job_states_lock:
            for jid, state in job_states.items():
                if state.platform == platform and state.status in ("running", "starting"):
                    stop_flags[jid] = True
                    stopped_jobs.append(jid)
        
        if not stopped_jobs:
            return {"success": False, "error": f"No {ACTORS[platform]['name']} scrapes are running"}
        
        return {"success": True, "message": f"Stop requested for {len(stopped_jobs)} jobs", "jobs": stopped_jobs}


def get_data_stats() -> Dict[str, Any]:
    """Get statistics about stored data."""
    stats = {
        "total_properties": 0,
        "files": [],
        "by_location": {},
        "by_platform": {},
        "by_category": {}
    }

    for file in PROPERTIES_DIR.rglob("*.json"):
        if file.name == "index.json" or file.name.endswith(".meta.json"):
            continue

        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                count = len(data) if isinstance(data, list) else 0
                stats["total_properties"] += count
                stats["files"].append({
                    "name": str(file.relative_to(PROPERTIES_DIR)).replace("\\", "/"),
                    "count": count,
                    "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })

                rel_parts = file.relative_to(PROPERTIES_DIR).parts
                if len(rel_parts) >= 5:
                    p_platform = rel_parts[0]
                    p_location = rel_parts[1]
                    p_search_type = rel_parts[2]
                    p_category = rel_parts[3]
                    stats["by_location"][p_location] = stats["by_location"].get(p_location, 0) + count
                    stats["by_platform"][p_platform] = stats["by_platform"].get(p_platform, 0) + count
                    stats["by_category"][f"{p_search_type}:{p_category}"] = stats["by_category"].get(f"{p_search_type}:{p_category}", 0) + count
        except Exception as e:
            print(f"[Stats] Error reading {file}: {e}")
    
    return stats


def get_platform_list() -> List[Dict[str, Any]]:
    """Get list of available platforms."""
    return [
        {
            "id": platform,
            "name": info["name"],
            "icon": info["icon"],
            "actor_id": info["id"]
        }
        for platform, info in ACTORS.items()
    ]
