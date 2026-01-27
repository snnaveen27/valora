"""
Smart Property Ingestion from Apify Downloads
Handles all property types: Residential, Plot/Land, Commercial, PG/Hostel
Handles all listing types: Sale, Rent, Lease

Features:
- Smart property categorization
- Type-specific field extraction
- Deduplication by property_id and URL
- Pincode indexing
- FAISS vector indexing for semantic search
"""

import os
import sys
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.db_service import DatabaseService

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "posted_properties"
DB_PATH = BASE_DIR / "src" / "data" / "valora.db"
FAISS_DIR = BASE_DIR / "src" / "data" / "faiss_store"


# ============================================================================
# PROPERTY CATEGORIZATION RULES
# ============================================================================

RESIDENTIAL_KEYWORDS = [
    'flat', 'apartment', 'bhk', 'house', 'villa', 'bungalow', 'penthouse',
    'duplex', 'triplex', 'builder floor', 'independent floor', 'studio',
    '1rk', 'residential', 'home'
]

PLOT_KEYWORDS = [
    'plot', 'land', 'site', 'residential land', 'farm', 'agriculture',
    'industrial land', 'commercial plot'
]

COMMERCIAL_KEYWORDS = [
    'office', 'shop', 'showroom', 'warehouse', 'godown', 'factory',
    'industrial', 'commercial', 'retail', 'coworking', 'business center',
    'manufacturing', 'bare shell', 'ready to move office'
]

PG_KEYWORDS = [
    'pg', 'paying guest', 'hostel', 'boys pg', 'girls pg', 'co-living',
    'coliving', 'shared accommodation'
]


def categorize_property(text: str) -> Tuple[str, str]:
    """
    Categorize property into category and subtype.
    Returns: (category, subtype)
    Categories: residential, plot, commercial, pg
    """
    text = text.lower()
    
    # PG/Hostel - Check first as it's specific
    for kw in PG_KEYWORDS:
        if kw in text:
            if 'girl' in text:
                return 'pg', 'girls_pg'
            elif 'boy' in text:
                return 'pg', 'boys_pg'
            else:
                return 'pg', 'coed_pg'
    
    # Commercial
    for kw in COMMERCIAL_KEYWORDS:
        if kw in text:
            if 'office' in text or 'coworking' in text:
                return 'commercial', 'office'
            elif 'shop' in text:
                return 'commercial', 'shop'
            elif 'showroom' in text:
                return 'commercial', 'showroom'
            elif 'warehouse' in text or 'godown' in text:
                return 'commercial', 'warehouse'
            elif 'factory' in text or 'manufacturing' in text:
                return 'commercial', 'factory'
            else:
                return 'commercial', 'commercial_other'
    
    # Plot/Land
    for kw in PLOT_KEYWORDS:
        if kw in text:
            if 'farm' in text or 'agriculture' in text:
                return 'plot', 'agricultural_land'
            elif 'industrial' in text:
                return 'plot', 'industrial_land'
            elif 'commercial' in text:
                return 'plot', 'commercial_plot'
            else:
                return 'plot', 'residential_plot'
    
    # Residential (default for BHK patterns)
    for kw in RESIDENTIAL_KEYWORDS:
        if kw in text:
            if 'villa' in text or 'bungalow' in text:
                return 'residential', 'villa'
            elif 'penthouse' in text:
                return 'residential', 'penthouse'
            elif 'duplex' in text:
                return 'residential', 'duplex'
            elif 'builder floor' in text or 'independent floor' in text:
                return 'residential', 'builder_floor'
            elif 'house' in text or 'independent house' in text:
                return 'residential', 'independent_house'
            elif 'studio' in text or '1rk' in text:
                return 'residential', 'studio'
            else:
                return 'residential', 'apartment'
    
    # Check for BHK pattern
    if re.search(r'\d+\s*bhk', text):
        return 'residential', 'apartment'
    
    return 'other', 'other'


def detect_listing_type(item: Dict) -> str:
    """Detect if property is for sale, rent, or lease."""
    # Combine all text fields
    text = ' '.join([
        str(item.get('url', '')),
        str(item.get('pageUrl', '')),
        str(item.get('from_url', '')),
        str(item.get('title', '')),
        str(item.get('name', '')),
        str(item.get('propertyType', '')),
        str(item.get('property_type', '')),
        str(item.get('type', ''))
    ]).lower()
    
    if 'lease' in text:
        return 'lease'
    elif 'rent' in text:
        return 'rent'
    elif 'buy' in text or 'sale' in text or 'for-sale' in text:
        return 'sale'
    
    # Check price indicators
    price_str = str(item.get('priceRange', '') or item.get('price_display', '')).lower()
    if '/month' in price_str or 'per month' in price_str:
        return 'rent'
    
    return 'sale'  # Default


def extract_bhk(text: str) -> Optional[str]:
    """Extract BHK configuration from text."""
    if not text:
        return None
    
    text = str(text).upper()
    
    # Patterns: "2 BHK", "2BHK", "BHK2", "2 Bedroom"
    patterns = [
        r'(\d+(?:\.\d+)?)\s*BHK',
        r'BHK\s*(\d+)',
        r'(\d+)\s*BEDROOM',
        r'(\d+)\s*BR\b'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return f"{match.group(1)}BHK"
    
    return None


def extract_pincode(text: str) -> Optional[str]:
    """Extract 6-digit Indian pincode."""
    if not text:
        return None
    # Karnataka pincodes: 56xxxx, 58xxxx, 59xxxx
    # Also check for other South Indian pincodes
    match = re.search(r'\b(5[6-9]\d{4}|6[0-4]\d{4}|4[0-4]\d{4})\b', str(text))
    return match.group(1) if match else None


def parse_price(price_val) -> Optional[float]:
    """Parse price to numeric value."""
    if price_val is None:
        return None
    
    if isinstance(price_val, (int, float)):
        return float(price_val)
    
    price_str = str(price_val).replace('₹', '').replace(',', '').replace('Rs', '').strip()
    
    multiplier = 1
    if 'Cr' in price_str or 'cr' in price_str:
        multiplier = 10000000
        price_str = re.sub(r'[Cc]r\.?', '', price_str)
    elif 'Lac' in price_str or 'lac' in price_str or ' L' in price_str:
        multiplier = 100000
        price_str = re.sub(r'[Ll]ac|[Ll]\.?\s', '', price_str)
    elif 'K' in price_str or 'k' in price_str:
        multiplier = 1000
        price_str = price_str.replace('K', '').replace('k', '')
    
    match = re.search(r'[\d.]+', price_str)
    if match:
        try:
            return float(match.group()) * multiplier
        except:
            pass
    return None


def parse_area(area_val) -> Optional[float]:
    """Parse area to sqft value."""
    if area_val is None:
        return None
    
    if isinstance(area_val, (int, float)):
        return float(area_val)
    
    area_str = str(area_val).lower().replace(',', '')
    match = re.search(r'[\d.]+', area_str)
    if match:
        try:
            return float(match.group())
        except:
            pass
    return None


def parse_int(val) -> Optional[int]:
    """Parse integer value."""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    
    match = re.search(r'\d+', str(val))
    if match:
        try:
            return int(match.group())
        except:
            pass
    return None


def detect_source(item: Dict) -> str:
    """Detect data source from item structure."""
    keys = set(item.keys())
    
    if 'latitude' in keys and 'amenities_map' in keys:
        return 'nobroker'
    if 'polygons_hash' in keys or ('coords' in keys and 'min_price' in keys):
        return 'housing'
    if 'location' in keys and 'price_per_sq_ft' in keys and 'city_name' in keys:
        return 'magicbricks'
    if 'scrapedAt' in keys and 'priceRange' in keys:
        return '99acres'
    
    url = str(item.get('url', '') or item.get('from_url', '') or item.get('pageUrl', '')).lower()
    if 'housing.com' in url:
        return 'housing'
    elif '99acres' in url:
        return '99acres'
    elif 'magicbricks' in url:
        return 'magicbricks'
    elif 'nobroker' in url:
        return 'nobroker'
    
    return 'unknown'


def extract_coordinates(item: Dict) -> Tuple[Optional[float], Optional[float]]:
    """Extract latitude and longitude from various formats."""
    lat, lng = None, None
    
    # Direct fields
    lat = item.get('latitude') or item.get('lat')
    lng = item.get('longitude') or item.get('lng') or item.get('lon')
    
    # MagicBricks: "12.83,77.67"
    if not lat and 'location' in item:
        loc = str(item.get('location', ''))
        if ',' in loc:
            parts = loc.split(',')
            try:
                lat = float(parts[0])
                lng = float(parts[1])
            except:
                pass
    
    # Housing.com: coords object
    if not lat and 'coords' in item:
        coords = item.get('coords', {})
        if isinstance(coords, dict):
            lat = coords.get('lat')
            lng = coords.get('lng') or coords.get('lon')
    
    # Convert to float
    try:
        lat = float(lat) if lat else None
        lng = float(lng) if lng else None
    except:
        lat, lng = None, None
    
    return lat, lng


def extract_locality(item: Dict, source: str) -> Tuple[str, str, str]:
    """Extract locality, area_name, city from item."""
    locality = ''
    area_name = ''
    city = 'Bangalore'
    
    if source == 'housing':
        polygons = item.get('polygons_hash', {})
        if isinstance(polygons, dict):
            loc_data = polygons.get('locality', {})
            if isinstance(loc_data, dict):
                locality = loc_data.get('name', '')
            city_data = polygons.get('city', {})
            if isinstance(city_data, dict):
                city = city_data.get('name', 'Bangalore')
    
    elif source == '99acres':
        title = item.get('title', '')
        match = re.search(r'in\s+([^,]+),\s*(\w+)', title)
        if match:
            locality = match.group(1)
            city = match.group(2)
    
    elif source == 'magicbricks':
        city = item.get('city_name', 'Bangalore')
        # Try to extract from address
        address = item.get('address', '')
        if address and ',' in address:
            locality = address.split(',')[0]
    
    elif source == 'nobroker':
        locality = item.get('locality', '') or item.get('nb_locality', '')
        city = item.get('city', 'Bangalore')
    
    # Fallback
    if not locality:
        locality = item.get('locality', '') or item.get('area', '') or item.get('areaName', '')
    
    area_name = locality  # Use locality as area_name if not specified
    
    return locality[:200], area_name[:200], city[:100]


def transform_item(item: Dict, source_file: str) -> Dict:
    """Transform any item to normalized database format."""
    source = detect_source(item)
    
    # Get property type text for categorization
    prop_type_text = ' '.join([
        str(item.get('propertyType', '')),
        str(item.get('property_type', '')),
        str(item.get('type', '')),
        str(item.get('title', '')),
        str(item.get('name', '')),
        str(item.get('subtitle', ''))
    ])
    
    # Categorize property
    category, subtype = categorize_property(prop_type_text)
    listing_type = detect_listing_type(item)
    
    # Generate unique property ID
    item_id = item.get('id', '')
    if not item_id:
        item_id = hashlib.md5(json.dumps(item, sort_keys=True).encode()).hexdigest()[:16]
    prop_id = f"{source}_{item_id}"
    
    # Extract coordinates
    lat, lng = extract_coordinates(item)
    
    # Extract location
    locality, area_name, city = extract_locality(item, source)
    
    # Extract BHK
    bhk = extract_bhk(prop_type_text)
    
    # Parse prices
    price = parse_price(
        item.get('price') or 
        item.get('min_price') or 
        item.get('max_price') or 
        item.get('priceRange')
    )
    
    price_per_sqft = parse_price(
        item.get('price_per_sq_ft') or 
        item.get('pricePerSqft') or 
        item.get('price_per_sqft')
    )
    
    # Parse area
    area = parse_area(
        item.get('covered_area') or 
        item.get('carpet_area') or 
        item.get('property_size') or
        item.get('total_area')
    )
    
    # For 99acres, area is sometimes in bedrooms field
    if not area and source == '99acres':
        bedrooms_text = item.get('bedrooms', '')
        if 'sqft' in str(bedrooms_text).lower():
            area = parse_area(bedrooms_text)
    
    # Parse bedrooms/bathrooms
    bedrooms = parse_int(item.get('bedrooms') or item.get('bedroom'))
    if not bedrooms and bhk:
        bedrooms = parse_int(bhk)
    
    bathrooms = parse_int(item.get('bathrooms') or item.get('bathroom'))
    
    # Get title and description
    title = str(item.get('title', '') or item.get('name', '') or item.get('property_title', ''))[:500]
    description = str(item.get('description', '') or item.get('seo_description', ''))[:5000]
    
    # Build source URL
    url = item.get('url', '') or item.get('source_url', '') or item.get('detail_url', '')
    if url and not url.startswith('http'):
        if source == 'housing':
            url = f"https://housing.com{url}"
        elif source == 'magicbricks':
            url = f"https://www.magicbricks.com/{url}"
    
    # Extract pincode from all text
    all_text = json.dumps(item)
    pincode = extract_pincode(all_text)
    
    # Price display
    price_display = str(item.get('priceRange', '') or item.get('price_display_value', '') or item.get('formatted_price', ''))[:100]
    if not price_display and price:
        if price >= 10000000:
            price_display = f"₹{price/10000000:.2f} Cr"
        elif price >= 100000:
            price_display = f"₹{price/100000:.2f} Lac"
        else:
            price_display = f"₹{price:,.0f}"
    
    # Amenities
    amenities = item.get('amenities', [])
    if isinstance(amenities, list):
        amenities = json.dumps(amenities)
    elif not amenities:
        amenities = json.dumps([])
    
    # Images
    images = item.get('images', []) or item.get('image_url', [])
    if isinstance(images, str):
        images = [images]
    if isinstance(images, list):
        images = json.dumps(images[:10])  # Limit to 10 images
    else:
        images = json.dumps([])
    
    # Owner info
    owner_name = item.get('owner_name', '') or item.get('sellerName', '')
    builder_name = item.get('company_name', '') or item.get('builder_name', '')
    owner_type = item.get('postedBy', '') or item.get('owner_type', '') or ('builder' if builder_name else 'owner')
    
    # Possession status
    possession = item.get('possessionStatus', '') or item.get('possession_status', '') or item.get('current_possession_status', '')
    
    # Build search text for full-text search
    search_text = f"{title} {locality} {city} {category} {subtype} {bhk or ''} {prop_type_text}"[:1000]
    
    # Rent-specific fields
    rent_monthly = None
    if listing_type == 'rent':
        rent_monthly = price
        if '/month' not in str(price_display).lower() and price and price > 500000:
            # Likely annual or total price, not monthly rent
            rent_monthly = None
    
    # Type-specific fields as JSON
    type_specific = {}
    if category == 'commercial':
        type_specific = {
            'seating_capacity': parse_int(item.get('seating_capacity')),
            'cabins': parse_int(item.get('cabins')),
            'washrooms': parse_int(item.get('washrooms')),
            'pantry': bool(item.get('pantry')),
            'power_backup': item.get('power_backup'),
        }
    elif category == 'pg':
        type_specific = {
            'meals_included': bool(item.get('meals_included')),
            'ac_available': bool(item.get('ac_available') or item.get('ac')),
            'wifi_available': bool(item.get('wifi_available') or item.get('wifi')),
            'room_type': item.get('room_type'),
        }
    elif category == 'plot':
        type_specific = {
            'plot_dimensions': item.get('plot_dimensions') or item.get('dimensions'),
            'approved_by': item.get('approved_by'),
            'is_corner_plot': bool(item.get('is_corner') or 'corner' in prop_type_text.lower()),
        }
    
    return {
        'property_id': prop_id,
        'source': source,
        'source_file': source_file,
        'raw_data': json.dumps(item, ensure_ascii=False),
        
        # Categorization
        'property_category': category,
        'property_subtype': subtype,
        'property_type': prop_type_text[:100],
        'listing_type': listing_type,
        'bhk': bhk,
        
        # Location
        'title': title,
        'description': description,
        'address': str(item.get('address', '') or item.get('fullAddress', ''))[:500],
        'locality': locality,
        'area_name': area_name,
        'city': city,
        'state': item.get('state', 'Karnataka')[:50],
        'pincode': pincode,
        'latitude': lat,
        'longitude': lng,
        
        # Specs
        'bedrooms': bedrooms,
        'bathrooms': bathrooms,
        'balconies': parse_int(item.get('balconies')),
        'total_area_sqft': area,
        'carpet_area_sqft': parse_area(item.get('carpet_area')),
        'floor_number': parse_int(item.get('floor') or item.get('floor_number')),
        'total_floors': parse_int(item.get('total_floor') or item.get('total_floors')),
        'furnishing': str(item.get('furnishing', '') or item.get('furnishing_status', ''))[:100],
        'facing': str(item.get('facing', ''))[:50],
        'age_years': parse_int(item.get('property_age') or item.get('age')),
        'parking': str(item.get('parking', '') or item.get('parking_desc', ''))[:100],
        
        # Pricing
        'price': price,
        'price_per_sqft': price_per_sqft,
        'price_display': price_display,
        'rent_monthly': rent_monthly,
        'maintenance_monthly': parse_price(item.get('maintenance') or item.get('maintenance_monthly')),
        'deposit': parse_price(item.get('deposit') or item.get('security_deposit')),
        'negotiable': 1 if item.get('negotiable') else 0,
        
        # Amenities & Images
        'amenities': amenities,
        'images': images,
        
        # Contact/Builder
        'builder_name': builder_name[:200] if builder_name else '',
        'owner_name': owner_name[:200] if owner_name else '',
        'owner_type': str(owner_type)[:100],
        
        # Status
        'status': 'active' if item.get('active', True) else 'inactive',
        'possession_status': str(possession)[:100],
        'verified': 1 if item.get('verified') else 0,
        
        # Type-specific (stored as JSON)
        'source_specific': json.dumps(type_specific),
        
        # URLs
        'source_url': str(url)[:500],
        
        # Timestamps
        'scraped_at': item.get('scrapedAt') or item.get('posted_date') or datetime.now().isoformat(),
        
        # Search
        'search_text': search_text
    }


def upgrade_schema(db: DatabaseService):
    """Add new columns to existing schema if they don't exist."""
    new_columns = [
        ('property_category', 'TEXT'),
        ('property_subtype', 'TEXT'),
        ('bhk', 'TEXT'),
        ('rent_monthly', 'REAL'),
    ]
    
    for col_name, col_type in new_columns:
        try:
            db.execute(f"ALTER TABLE properties ADD COLUMN {col_name} {col_type}")
            print(f"  ✅ Added column: {col_name}")
        except Exception as e:
            if 'duplicate column' not in str(e).lower():
                pass  # Column already exists
    
    # Create indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_properties_category ON properties(property_category)",
        "CREATE INDEX IF NOT EXISTS idx_properties_subtype ON properties(property_subtype)",
        "CREATE INDEX IF NOT EXISTS idx_properties_pincode ON properties(pincode)",
        "CREATE INDEX IF NOT EXISTS idx_properties_bhk ON properties(bhk)",
        "CREATE INDEX IF NOT EXISTS idx_prop_cat_listing ON properties(property_category, listing_type)",
        "CREATE INDEX IF NOT EXISTS idx_prop_cat_price ON properties(property_category, price)",
    ]
    
    for idx_sql in indexes:
        try:
            db.execute(idx_sql)
        except:
            pass


def main():
    print("=" * 70)
    print("📦 SMART PROPERTY INGESTION")
    print("   Residential | Plot | Commercial | PG")
    print("   Sale | Rent | Lease")
    print("=" * 70)
    
    # Initialize database
    print(f"\n📂 Database: {DB_PATH}")
    db = DatabaseService(str(DB_PATH))
    db.initialize_schema(force=False)
    
    # Upgrade schema with new columns
    print("\n🔧 Upgrading schema...")
    upgrade_schema(db)
    print("  ✅ Schema ready")
    
    # Get existing IDs
    existing_ids = set()
    existing_urls = set()
    try:
        result = db.execute("SELECT property_id, source_url FROM properties")
        for row in result:
            existing_ids.add(row['property_id'])
            if row['source_url']:
                existing_urls.add(row['source_url'])
        print(f"📊 Existing properties: {len(existing_ids):,}")
    except:
        pass
    
    # Find JSON files
    json_files = [f for f in DATA_DIR.glob("*.json") if f.name != 'download_summary.txt']
    print(f"📁 Found {len(json_files)} JSON files")
    
    # Statistics
    stats = {
        'files': 0,
        'total': 0,
        'inserted': 0,
        'duplicates': 0,
        'errors': 0,
        'by_category': defaultdict(lambda: {'total': 0, 'inserted': 0}),
        'by_listing': defaultdict(lambda: {'total': 0, 'inserted': 0}),
        'by_source': defaultdict(lambda: {'total': 0, 'inserted': 0})
    }
    
    # Process files
    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] {json_file.name}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list) or not data:
                print("  ⏭️  Empty or invalid")
                continue
            
            stats['files'] += 1
            stats['total'] += len(data)
            
            # Transform items
            batch = []
            for item in data:
                try:
                    transformed = transform_item(item, json_file.name)
                    
                    # Skip duplicates
                    if transformed['property_id'] in existing_ids:
                        stats['duplicates'] += 1
                        continue
                    if transformed['source_url'] and transformed['source_url'] in existing_urls:
                        stats['duplicates'] += 1
                        continue
                    
                    batch.append(transformed)
                    existing_ids.add(transformed['property_id'])
                    if transformed['source_url']:
                        existing_urls.add(transformed['source_url'])
                    
                    # Track stats
                    cat = transformed['property_category']
                    listing = transformed['listing_type']
                    src = transformed['source']
                    
                    stats['by_category'][cat]['total'] += 1
                    stats['by_listing'][listing]['total'] += 1
                    stats['by_source'][src]['total'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
            
            # Insert batch
            if batch:
                try:
                    db.insert_many('properties', batch)
                    stats['inserted'] += len(batch)
                    
                    for item in batch:
                        stats['by_category'][item['property_category']]['inserted'] += 1
                        stats['by_listing'][item['listing_type']]['inserted'] += 1
                        stats['by_source'][item['source']]['inserted'] += 1
                    
                    print(f"  ✅ Inserted {len(batch)} properties")
                except Exception as e:
                    print(f"  ❌ Insert error: {e}")
                    stats['errors'] += len(batch)
            else:
                print(f"  ⏭️  All duplicates")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            stats['errors'] += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 INGESTION COMPLETE")
    print("=" * 70)
    
    print(f"\n📁 Files: {stats['files']}")
    print(f"📦 Total items: {stats['total']:,}")
    print(f"✅ Inserted: {stats['inserted']:,}")
    print(f"⏭️  Duplicates: {stats['duplicates']:,}")
    print(f"❌ Errors: {stats['errors']}")
    
    print(f"\n📊 By Category:")
    for cat, s in sorted(stats['by_category'].items()):
        print(f"  • {cat}: {s['inserted']:,} inserted")
    
    print(f"\n📊 By Listing Type:")
    for lt, s in sorted(stats['by_listing'].items()):
        print(f"  • {lt}: {s['inserted']:,} inserted")
    
    print(f"\n📊 By Source:")
    for src, s in sorted(stats['by_source'].items()):
        print(f"  • {src}: {s['inserted']:,} inserted")
    
    # Database verification
    print(f"\n📊 Database Stats:")
    try:
        r = db.execute("SELECT COUNT(*) as c FROM properties")
        print(f"  • Total: {r[0]['c']:,}")
        
        r = db.execute("SELECT property_category, COUNT(*) as c FROM properties GROUP BY property_category")
        print(f"  • By category:")
        for row in r:
            print(f"    - {row['property_category'] or 'unknown'}: {row['c']:,}")
        
        r = db.execute("SELECT listing_type, COUNT(*) as c FROM properties GROUP BY listing_type")
        print(f"  • By listing:")
        for row in r:
            print(f"    - {row['listing_type'] or 'unknown'}: {row['c']:,}")
        
        r = db.execute("SELECT COUNT(DISTINCT pincode) as c FROM properties WHERE pincode IS NOT NULL")
        print(f"  • Unique pincodes: {r[0]['c']}")
        
        r = db.execute("SELECT COUNT(*) as c FROM properties WHERE latitude IS NOT NULL")
        print(f"  • With coordinates: {r[0]['c']:,}")
        
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()
