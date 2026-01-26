"""
Complete Apify Property Ingestion Pipeline
1. Fetches ALL run IDs from Apify API
2. Downloads all datasets
3. Normalizes and uploads to database
4. Cleans up temporary files
"""

import os
import sys
import json
import requests
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
from dotenv import load_dotenv

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

load_dotenv()

from backend.database.db_service import DatabaseService

# Configuration
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
APIFY_BASE_URL = "https://api.apify.com/v2"

# Directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "src" / "data" / "valora.db"
TEMP_DIR = BASE_DIR / "scripts" / "ingest" / "temp_apify_downloads"
POSTED_PROPERTIES_DIR = BASE_DIR / "src" / "data" / "posted_properties"


def fetch_all_actor_runs() -> List[Dict]:
    """Fetch all actor runs from Apify API."""
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
    all_runs = []
    
    print("🔍 Fetching all actor runs from Apify API...")
    
    offset = 0
    limit = 1000
    
    while True:
        url = f"{APIFY_BASE_URL}/actor-runs?offset={offset}&limit={limit}&desc=1"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()["data"]
            items = data.get("items", [])
            
            if not items:
                break
            
            all_runs.extend(items)
            print(f"  📥 Fetched {len(all_runs)} runs...")
            
            total = data.get("total", 0)
            if len(all_runs) >= total:
                break
            
            offset += limit
            
        except Exception as e:
            print(f"  ❌ Error fetching runs: {e}")
            break
    
    return all_runs


def download_dataset(run_id: str, dataset_id: str) -> Optional[List[Dict]]:
    """Download dataset items from Apify."""
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
    
    try:
        # Get dataset info
        dataset_url = f"{APIFY_BASE_URL}/datasets/{dataset_id}"
        dataset_response = requests.get(dataset_url, headers=headers, timeout=30)
        dataset_response.raise_for_status()
        
        dataset_info = dataset_response.json()["data"]
        item_count = dataset_info.get("itemCount", 0)
        
        if item_count == 0:
            return None
        
        # Download all items
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
        
        return all_items
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None
        return None
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return None


def detect_platform_from_item(item: Dict) -> str:
    """Detect platform from item data content."""
    # Check URL patterns
    url = str(item.get("url", "") or item.get("propertyUrl", "") or item.get("pageUrl", "")).lower()
    
    if "magicbricks" in url:
        return "magicbricks"
    elif "99acres" in url:
        return "99acres"
    elif "housing.com" in url:
        return "housing"
    elif "nobroker" in url:
        return "nobroker"
    
    # Check source field
    source = str(item.get("source", "")).lower()
    if "magicbricks" in source:
        return "magicbricks"
    elif "99acres" in source:
        return "99acres"
    elif "housing" in source:
        return "housing"
    elif "nobroker" in source:
        return "nobroker"
    
    # Check for platform-specific fields
    if item.get("mbId") or item.get("magicbricksId"):
        return "magicbricks"
    elif item.get("acresId") or "99acres" in str(item.get("id", "")):
        return "99acres"
    elif item.get("housingId"):
        return "housing"
    elif item.get("nbId") or item.get("nobrokerPropertyId"):
        return "nobroker"
    
    # Check data structure patterns
    raw_str = json.dumps(item).lower()
    if "magicbricks" in raw_str:
        return "magicbricks"
    elif "99acres" in raw_str or "99 acres" in raw_str:
        return "99acres"
    elif "housing.com" in raw_str:
        return "housing"
    elif "nobroker" in raw_str:
        return "nobroker"
    
    return "unknown"


def detect_platform(actor_id: str, run_data: Dict) -> str:
    """Detect platform from actor ID or run data."""
    actor_id_lower = actor_id.lower() if actor_id else ""
    
    # Check actor ID patterns from Apify
    if "magicbricks" in actor_id_lower or "magi" in actor_id_lower:
        return "magicbricks"
    elif "housing" in actor_id_lower or "hou" in actor_id_lower:
        return "housing"
    elif "99acres" in actor_id_lower or "fatihtahta" in actor_id_lower:
        return "99acres"
    elif "nobroker" in actor_id_lower or "nobro" in actor_id_lower:
        return "nobroker"
    elif "commonfloor" in actor_id_lower:
        return "commonfloor"
    elif "squareyards" in actor_id_lower:
        return "squareyards"
    
    # Try to detect from actor name patterns
    if "ecomscrape" in actor_id_lower:
        if "magic" in actor_id_lower:
            return "magicbricks"
        elif "hous" in actor_id_lower:
            return "housing"
        elif "nobro" in actor_id_lower:
            return "nobroker"
    
    return "unknown"


def generate_property_id(item: Dict, platform: str, lat: float = None, lng: float = None) -> str:
    """
    Generate unique property ID with smart deduplication.
    
    Strategy: platform + property_type + bedrooms + rounded_coordinates
    This prevents:
    - Same property re-posted with different price → same ID (deduplicates)
    - Same property on different platforms → different IDs (keeps both)
    - Nearby but different properties → different IDs (coordinates differ)
    """
    # Get property characteristics
    prop_type = str(item.get("propertyType") or item.get("property_type") or item.get("type") or "unknown").lower()
    prop_type = prop_type.replace(" ", "_")[:20]
    
    bedrooms = item.get("bedrooms") or item.get("bhk") or item.get("bedroom") or 0
    if isinstance(bedrooms, str):
        try:
            bedrooms = int(''.join(c for c in bedrooms if c.isdigit()) or 0)
        except:
            bedrooms = 0
    
    # Round coordinates to 4 decimal places (~11m precision)
    lat_rounded = round(lat, 4) if lat else 0
    lng_rounded = round(lng, 4) if lng else 0
    
    # If we have coordinates, use coordinate-based ID
    if lat and lng and lat != 0 and lng != 0:
        # Format: platform_type_bhk_lat_lng
        coord_id = f"{platform}_{prop_type}_{bedrooms}bhk_{lat_rounded}_{lng_rounded}"
        return coord_id
    
    # Fallback: Try various ID fields
    prop_id = (
        item.get("id") or 
        item.get("propertyId") or 
        item.get("property_id") or
        item.get("listingId") or
        ""
    )
    
    if prop_id:
        return f"{platform}_{prop_id}"
    
    # Last resort: Generate from content hash
    content = json.dumps(item, sort_keys=True)
    hash_id = hashlib.md5(content.encode()).hexdigest()[:16]
    return f"{platform}_{hash_id}"


def extract_coordinates(item: Dict) -> tuple:
    """Extract latitude and longitude from item."""
    lat = None
    lng = None
    
    # Direct fields
    lat = item.get("latitude") or item.get("lat") or item.get("Latitude")
    lng = item.get("longitude") or item.get("lng") or item.get("lon") or item.get("Longitude")
    
    # Nested location object
    if not lat or not lng:
        location = item.get("location", {})
        if isinstance(location, dict):
            lat = location.get("lat") or location.get("latitude")
            lng = location.get("lng") or location.get("longitude") or location.get("lon")
    
    # Geo object
    if not lat or not lng:
        geo = item.get("geo", {})
        if isinstance(geo, dict):
            lat = geo.get("lat") or geo.get("latitude")
            lng = geo.get("lng") or geo.get("longitude")
    
    # Coordinates array
    if not lat or not lng:
        coords = item.get("coordinates", [])
        if isinstance(coords, list) and len(coords) >= 2:
            lng, lat = coords[0], coords[1]
    
    # Convert to float
    try:
        lat = float(lat) if lat else None
        lng = float(lng) if lng else None
    except (ValueError, TypeError):
        lat, lng = None, None
    
    return lat, lng


def extract_price(item: Dict) -> tuple:
    """Extract price and price per sqft."""
    price = None
    price_per_sqft = None
    
    # Price
    price_raw = (
        item.get("price") or 
        item.get("Price") or 
        item.get("priceValue") or
        item.get("expectedPrice") or
        item.get("totalPrice") or
        0
    )
    
    if isinstance(price_raw, str):
        # Remove currency symbols and commas
        price_raw = price_raw.replace("₹", "").replace(",", "").replace("Rs", "").strip()
        # Handle Cr, Lac, K
        multiplier = 1
        if "Cr" in price_raw or "cr" in price_raw:
            multiplier = 10000000
            price_raw = price_raw.replace("Cr", "").replace("cr", "")
        elif "Lac" in price_raw or "lac" in price_raw or "L" in price_raw:
            multiplier = 100000
            price_raw = price_raw.replace("Lac", "").replace("lac", "").replace("L", "")
        elif "K" in price_raw or "k" in price_raw:
            multiplier = 1000
            price_raw = price_raw.replace("K", "").replace("k", "")
        
        try:
            price = float(''.join(c for c in price_raw if c.isdigit() or c == '.')) * multiplier
        except:
            price = None
    elif isinstance(price_raw, (int, float)):
        price = float(price_raw)
    
    # Price per sqft
    price_per_sqft_raw = item.get("pricePerSqft") or item.get("pricePerSqFt") or item.get("price_per_sqft")
    if price_per_sqft_raw:
        try:
            if isinstance(price_per_sqft_raw, str):
                price_per_sqft = float(''.join(c for c in price_per_sqft_raw if c.isdigit() or c == '.'))
            else:
                price_per_sqft = float(price_per_sqft_raw)
        except:
            price_per_sqft = None
    
    return price, price_per_sqft


def extract_area(item: Dict) -> tuple:
    """Extract total area and carpet area."""
    total_area = None
    carpet_area = None
    
    # Total area
    total_raw = (
        item.get("area") or 
        item.get("builtUpArea") or 
        item.get("superBuiltUpArea") or
        item.get("totalArea") or
        item.get("size") or
        0
    )
    
    if isinstance(total_raw, str):
        try:
            total_area = float(''.join(c for c in total_raw if c.isdigit() or c == '.'))
        except:
            total_area = None
    elif isinstance(total_raw, (int, float)):
        total_area = float(total_raw)
    
    # Carpet area
    carpet_raw = item.get("carpetArea") or item.get("carpet_area")
    if carpet_raw:
        try:
            if isinstance(carpet_raw, str):
                carpet_area = float(''.join(c for c in carpet_raw if c.isdigit() or c == '.'))
            else:
                carpet_area = float(carpet_raw)
        except:
            carpet_area = None
    
    return total_area, carpet_area


def normalize_property(item: Dict, platform: str, run_id: str) -> Dict:
    """Normalize a property item to database schema."""
    # Detect platform from item content if not detected from actor
    if platform == "unknown":
        platform = detect_platform_from_item(item)
    
    lat, lng = extract_coordinates(item)
    property_id = generate_property_id(item, platform, lat, lng)
    price, price_per_sqft = extract_price(item)
    total_area, carpet_area = extract_area(item)
    
    # Extract bedrooms
    bedrooms = item.get("bedrooms") or item.get("bhk") or item.get("bedroom") or item.get("BHK")
    if isinstance(bedrooms, str):
        try:
            bedrooms = int(''.join(c for c in bedrooms if c.isdigit()) or 0)
        except:
            bedrooms = None
    
    # Extract bathrooms
    bathrooms = item.get("bathrooms") or item.get("bathroom")
    if isinstance(bathrooms, str):
        try:
            bathrooms = int(''.join(c for c in bathrooms if c.isdigit()) or 0)
        except:
            bathrooms = None
    
    # Listing type
    listing_type = item.get("transactionType") or item.get("listingType") or item.get("type") or item.get("searchType")
    if listing_type:
        listing_type = listing_type.lower()
        if "rent" in listing_type:
            listing_type = "rent"
        elif "buy" in listing_type or "sale" in listing_type:
            listing_type = "sale"
        elif "lease" in listing_type:
            listing_type = "lease"
    
    # Property type
    property_type = item.get("propertyType") or item.get("property_type") or item.get("type")
    if property_type:
        property_type = str(property_type).lower()
    
    # Amenities
    amenities = item.get("amenities") or item.get("Amenities") or []
    if isinstance(amenities, list):
        amenities = json.dumps(amenities)
    elif not isinstance(amenities, str):
        amenities = json.dumps([])
    
    # Images
    images = item.get("images") or item.get("photos") or item.get("Images") or []
    if isinstance(images, list):
        images = json.dumps(images)
    elif not isinstance(images, str):
        images = json.dumps([])
    
    # Posted date
    posted_at = item.get("postedOn") or item.get("postedDate") or item.get("posted_on")
    
    return {
        "property_id": property_id,
        "source": platform,
        "source_file": f"apify_run_{run_id}",
        "raw_data": json.dumps(item, ensure_ascii=False),
        "title": str(item.get("title") or item.get("propertyName") or item.get("name") or "Property")[:500],
        "description": str(item.get("description") or "")[:5000],
        "property_type": property_type[:100] if property_type else None,
        "listing_type": listing_type[:50] if listing_type else None,
        "address": str(item.get("address") or item.get("fullAddress") or "")[:500],
        "locality": str(item.get("locality") or item.get("society") or item.get("Locality") or "")[:200],
        "area_name": str(item.get("area") if isinstance(item.get("area"), str) else item.get("areaName") or item.get("suburb") or "")[:200],
        "city": str(item.get("city") or item.get("City") or "Bangalore")[:100],
        "state": "Karnataka",
        "pincode": str(item.get("pincode") or item.get("zipcode") or "")[:10],
        "latitude": lat,
        "longitude": lng,
        "bedrooms": int(bedrooms) if bedrooms else None,
        "bathrooms": int(bathrooms) if bathrooms else None,
        "balconies": int(item.get("balconies") or 0) if item.get("balconies") else None,
        "total_area_sqft": total_area,
        "carpet_area_sqft": carpet_area,
        "floor_number": int(item.get("floor") or item.get("floorNumber") or 0) if item.get("floor") or item.get("floorNumber") else None,
        "total_floors": int(item.get("totalFloors") or 0) if item.get("totalFloors") else None,
        "furnishing": str(item.get("furnishing") or item.get("furnishingStatus") or "")[:100],
        "facing": str(item.get("facing") or "")[:50],
        "age_years": int(item.get("age") or item.get("propertyAge") or 0) if item.get("age") or item.get("propertyAge") else None,
        "parking": str(item.get("parking") or "")[:100],
        "price": price,
        "price_per_sqft": price_per_sqft,
        "price_display": str(item.get("priceDisplay") or item.get("price_display") or "")[:100],
        "maintenance_monthly": float(item.get("maintenance") or 0) if item.get("maintenance") else None,
        "deposit": float(item.get("deposit") or item.get("securityDeposit") or 0) if item.get("deposit") or item.get("securityDeposit") else None,
        "negotiable": 1 if item.get("negotiable") else 0,
        "amenities": amenities,
        "builder_name": str(item.get("builderName") or item.get("builder") or "")[:200],
        "owner_name": str(item.get("ownerName") or item.get("sellerName") or "")[:200],
        "owner_type": str(item.get("ownerType") or item.get("postedBy") or "")[:100],
        "images": images,
        "status": "active",
        "possession_status": str(item.get("possessionStatus") or item.get("possession") or "")[:100],
        "verified": 1 if item.get("verified") else 0,
        "source_url": str(item.get("url") or item.get("propertyUrl") or item.get("pageUrl") or "")[:500],
        "posted_at": posted_at,
        "scraped_at": datetime.now().isoformat(),
        "search_text": f"{item.get('title', '')} {item.get('locality', '')} {item.get('city', '')} {item.get('propertyType', '')}"[:1000]
    }


def sanitize_path(name: str) -> str:
    """Sanitize string for use in file/directory names."""
    # Replace invalid characters
    invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|', ' ']
    result = str(name).lower()
    for char in invalid_chars:
        result = result.replace(char, '_')
    # Remove multiple underscores
    while '__' in result:
        result = result.replace('__', '_')
    # Trim underscores from ends
    result = result.strip('_')
    return result[:100] if result else "unknown"


def save_to_structured_files(properties_by_category: Dict, platform: str):
    """Save properties to structured files in posted_properties folder."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    platform = sanitize_path(platform)
    
    for category_key, properties in properties_by_category.items():
        if not properties:
            continue
        
        # Sanitize category key for valid path
        category_key = sanitize_path(category_key)
        
        # Create directory
        category_dir = POSTED_PROPERTIES_DIR / platform / category_key
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Save timestamped file
        data_file = category_dir / f"data_{timestamp}.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(properties, f, ensure_ascii=False, indent=2)
        
        # Save latest file
        latest_file = POSTED_PROPERTIES_DIR / platform / f"{category_key}_latest.json"
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(properties, f, ensure_ascii=False, indent=2)


def main():
    """Main execution function."""
    print("=" * 80)
    print("🚀 APIFY COMPLETE PROPERTY INGESTION PIPELINE")
    print("=" * 80)
    
    if not APIFY_TOKEN:
        print("❌ APIFY_API_TOKEN not found in environment variables")
        return
    
    # Create temp directory
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    POSTED_PROPERTIES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize database
    print(f"\n📦 Initializing database at: {DB_PATH}")
    db = DatabaseService(str(DB_PATH))
    db.initialize_schema(force=False)
    
    # Fetch all runs from API
    all_runs = fetch_all_actor_runs()
    
    if not all_runs:
        print("❌ No runs found")
        return
    
    print(f"\n✅ Found {len(all_runs)} total runs in Apify account")
    
    # Filter successful runs with datasets
    runs_with_datasets = []
    for run in all_runs:
        if run.get("status") == "SUCCEEDED" and run.get("defaultDatasetId"):
            runs_with_datasets.append({
                "run_id": run.get("id"),
                "dataset_id": run.get("defaultDatasetId"),
                "actor_id": run.get("actId", ""),
                "started_at": run.get("startedAt"),
                "finished_at": run.get("finishedAt")
            })
    
    print(f"✅ Found {len(runs_with_datasets)} successful runs with datasets")
    
    if not runs_with_datasets:
        print("❌ No datasets available to download")
        return
    
    # Statistics
    stats = {
        "runs_processed": 0,
        "runs_empty": 0,
        "runs_expired": 0,
        "runs_failed": 0,
        "total_items_downloaded": 0,
        "total_properties_inserted": 0,
        "total_properties_updated": 0,
        "duplicates_skipped": 0,
        "by_platform": defaultdict(lambda: {"downloaded": 0, "inserted": 0})
    }
    
    # Track existing property IDs
    existing_ids = set()
    try:
        result = db.execute("SELECT property_id FROM properties")
        existing_ids = {row["property_id"] for row in result}
        print(f"📊 Found {len(existing_ids)} existing properties in database")
    except Exception as e:
        print(f"⚠️  Could not fetch existing IDs: {e}")
    
    # Process each run
    print(f"\n🚀 Processing {len(runs_with_datasets)} datasets...\n")
    
    all_properties_by_platform = defaultdict(lambda: defaultdict(list))
    
    for idx, run in enumerate(runs_with_datasets, 1):
        run_id = run["run_id"]
        dataset_id = run["dataset_id"]
        actor_id = run["actor_id"]
        platform = detect_platform(actor_id, run)
        
        print(f"[{idx}/{len(runs_with_datasets)}] {platform} - Run: {run_id[:12]}...")
        
        # Download dataset
        items = download_dataset(run_id, dataset_id)
        
        if items is None:
            stats["runs_expired"] += 1
            print(f"  ⏰ Dataset expired or not found")
            continue
        
        if len(items) == 0:
            stats["runs_empty"] += 1
            print(f"  ⚠️  Empty dataset")
            continue
        
        stats["runs_processed"] += 1
        stats["total_items_downloaded"] += len(items)
        stats["by_platform"][platform]["downloaded"] += len(items)
        
        print(f"  📥 Downloaded {len(items)} items")
        
        # Normalize and prepare for insertion
        properties_batch = []
        
        for item in items:
            try:
                normalized = normalize_property(item, platform, run_id)
                
                # Skip duplicates
                if normalized["property_id"] in existing_ids:
                    stats["duplicates_skipped"] += 1
                    continue
                
                # Skip if no coordinates (optional)
                # if not normalized["latitude"] or not normalized["longitude"]:
                #     continue
                
                properties_batch.append(normalized)
                existing_ids.add(normalized["property_id"])
                
                # Organize for file storage
                listing_type = normalized.get("listing_type") or "unknown"
                prop_type = normalized.get("property_type") or "unknown"
                city = (normalized.get("city") or "bangalore").lower().replace(" ", "-")
                category_key = f"{city}_{listing_type}_{prop_type}"
                
                all_properties_by_platform[platform][category_key].append(item)
                
            except Exception as e:
                print(f"    ⚠️  Error normalizing item: {e}")
                continue
        
        # Batch insert to database
        if properties_batch:
            try:
                db.insert_many("properties", properties_batch)
                stats["total_properties_inserted"] += len(properties_batch)
                stats["by_platform"][platform]["inserted"] += len(properties_batch)
                print(f"  ✅ Inserted {len(properties_batch)} properties")
            except Exception as e:
                print(f"  ❌ Insert error: {e}")
                stats["runs_failed"] += 1
        
        print()
    
    # Save to structured files
    print("\n📁 Saving to structured files...")
    for platform, categories in all_properties_by_platform.items():
        save_to_structured_files(categories, platform)
        total_for_platform = sum(len(props) for props in categories.values())
        print(f"  ✅ {platform}: {len(categories)} categories, {total_for_platform} properties")
    
    # Cleanup temp directory
    print("\n🧹 Cleaning up temporary files...")
    if TEMP_DIR.exists():
        try:
            shutil.rmtree(TEMP_DIR)
            print(f"  ✅ Removed temp directory: {TEMP_DIR}")
        except Exception as e:
            print(f"  ⚠️  Could not remove temp directory: {e}")
    
    # Log ingestion
    try:
        db.log_ingestion(
            source_name="apify_bulk_import",
            processed=stats["total_items_downloaded"],
            inserted=stats["total_properties_inserted"],
            updated=stats["total_properties_updated"],
            failed=stats["runs_failed"],
            status="completed"
        )
    except Exception as e:
        print(f"⚠️  Could not log ingestion: {e}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("📊 INGESTION COMPLETE - SUMMARY")
    print("=" * 80)
    
    print(f"\n📥 Download Stats:")
    print(f"  • Runs processed: {stats['runs_processed']}")
    print(f"  • Runs empty: {stats['runs_empty']}")
    print(f"  • Runs expired/not found: {stats['runs_expired']}")
    print(f"  • Total items downloaded: {stats['total_items_downloaded']:,}")
    
    print(f"\n💾 Database Stats:")
    print(f"  • Properties inserted: {stats['total_properties_inserted']:,}")
    print(f"  • Duplicates skipped: {stats['duplicates_skipped']:,}")
    
    print(f"\n📊 By Platform:")
    for platform, pstats in sorted(stats["by_platform"].items()):
        print(f"  • {platform}: {pstats['downloaded']:,} downloaded, {pstats['inserted']:,} inserted")
    
    # Verify database
    print(f"\n📊 Database Verification:")
    try:
        result = db.execute("SELECT COUNT(*) as count FROM properties")
        total = result[0]["count"] if result else 0
        print(f"  • Total properties in database: {total:,}")
        
        result = db.execute("SELECT source, COUNT(*) as count FROM properties GROUP BY source")
        print(f"  • By source:")
        for row in result:
            print(f"    - {row['source']}: {row['count']:,}")
        
        result = db.execute("SELECT listing_type, COUNT(*) as count FROM properties GROUP BY listing_type")
        print(f"  • By listing type:")
        for row in result:
            lt = row['listing_type'] or 'unknown'
            print(f"    - {lt}: {row['count']:,}")
    except Exception as e:
        print(f"  ⚠️  Verification error: {e}")
    
    print(f"\n📁 Structured files saved to: {POSTED_PROPERTIES_DIR}")
    print("\n✨ Pipeline complete!")


if __name__ == "__main__":
    main()
