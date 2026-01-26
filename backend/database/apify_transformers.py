"""
Comprehensive Apify Data Transformers v2
- Stores ALL raw data as JSON (nothing is lost)
- Extracts normalized fields for querying
- Handles all field variations per source
"""
import json
import hashlib
import re
from typing import Dict, Any, Optional, List
from datetime import datetime


def parse_indian_price(price_str: str) -> Optional[float]:
    """Parse Indian price formats like ₹9.32 Cr, ₹45 Lac, ₹50,000"""
    if not price_str:
        return None
    
    try:
        # Already a number
        if isinstance(price_str, (int, float)):
            return float(price_str)
        
        price_str = str(price_str).strip()
        
        # Remove currency symbols and commas
        clean = re.sub(r'[₹,\s]', '', price_str)
        
        # Handle Crore
        if 'cr' in clean.lower():
            num = re.search(r'([\d.]+)', clean)
            if num:
                return float(num.group(1)) * 10000000
        
        # Handle Lac/Lakh
        if 'lac' in clean.lower() or 'lakh' in clean.lower():
            num = re.search(r'([\d.]+)', clean)
            if num:
                return float(num.group(1)) * 100000
        
        # Handle K (thousands)
        if 'k' in clean.lower():
            num = re.search(r'([\d.]+)', clean)
            if num:
                return float(num.group(1)) * 1000
        
        # Plain number
        num = re.search(r'([\d.]+)', clean)
        if num:
            return float(num.group(1))
            
    except Exception:
        pass
    
    return None


def parse_bhk(text: str) -> Optional[int]:
    """Extract BHK number from various formats"""
    if not text:
        return None
    
    text = str(text).upper()
    
    # Direct BHK patterns
    patterns = [
        r'(\d+(?:\.\d+)?)\s*BHK',
        r'BHK\s*(\d+)',
        r'(\d+)\s*(?:BEDROOM|BED|BR)',
        r'(\d+)\s*RK',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(float(match.group(1)))
    
    return None


def parse_area_sqft(text: str) -> Optional[float]:
    """Parse area in sqft from various formats"""
    if not text:
        return None
    
    try:
        if isinstance(text, (int, float)):
            return float(text)
        
        text = str(text).lower()
        
        # Extract number and unit
        match = re.search(r'([\d,.]+)\s*(sq\.?\s*ft|sqft|sft|sq\.?\s*m|sqm|sq\.?\s*yd|sqyd)', text)
        if match:
            num = float(match.group(1).replace(',', ''))
            unit = match.group(2).lower()
            
            if 'sqm' in unit or 'sq m' in unit:
                return num * 10.764  # sqm to sqft
            elif 'sqyd' in unit or 'sq yd' in unit:
                return num * 9  # sqyd to sqft
            else:
                return num
        
        # Just number - assume sqft
        num = re.search(r'([\d,.]+)', text)
        if num:
            return float(num.group(1).replace(',', ''))
            
    except Exception:
        pass
    
    return None


def extract_locality(text: str) -> Optional[str]:
    """Extract locality/area name from title or address"""
    if not text:
        return None
    
    # Common Bangalore locality patterns
    patterns = [
        r'in\s+([A-Za-z\s]+?)(?:,|$)',
        r'at\s+([A-Za-z\s]+?)(?:,|$)',
        r'(?:near|opp\.?|opposite)\s+([A-Za-z\s]+?)(?:,|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            locality = match.group(1).strip()
            if len(locality) > 3:
                return locality
    
    return None


def parse_timestamp(ts: Any) -> Optional[str]:
    """Parse various timestamp formats to ISO string"""
    if not ts:
        return None
    
    try:
        if isinstance(ts, (int, float)):
            # Milliseconds timestamp
            if ts > 1e12:
                ts = ts / 1000
            return datetime.fromtimestamp(ts).isoformat()
        elif isinstance(ts, str):
            # ISO format
            return ts
    except Exception:
        pass
    
    return None


class Transformer99Acres:
    """
    Transform 99acres data.
    Fields: id, title, priceRange, pricePerSqft, description, bedrooms, bathrooms,
            floorSize, areaType, possessionStatus, postedBy, propertyType, url, pageUrl, scrapedAt
    """
    
    @staticmethod
    def transform(raw: Dict, source_file: str = "") -> Dict[str, Any]:
        raw_id = raw.get('id', '')
        property_id = f"99acres_{raw_id}" if raw_id else f"99acres_{hashlib.md5(json.dumps(raw, sort_keys=True).encode()).hexdigest()[:12]}"
        
        # Parse fields
        title = raw.get('title', '')
        price = parse_indian_price(raw.get('priceRange'))
        price_per_sqft = parse_indian_price(raw.get('pricePerSqft'))
        
        # Note: 99acres has swapped fields in some cases
        # bedrooms field contains area, floorSize contains BHK
        bedrooms = parse_bhk(raw.get('floorSize')) or parse_bhk(raw.get('propertyType')) or parse_bhk(title)
        bathrooms_text = raw.get('bathrooms', '')
        area_sqft = parse_area_sqft(raw.get('bedrooms')) or parse_area_sqft(bathrooms_text)
        
        # Extract locality from title
        locality = extract_locality(title)
        
        # Determine property and listing type
        prop_type_raw = raw.get('propertyType', '').lower()
        property_type = 'apartment'
        if 'house' in prop_type_raw or 'villa' in prop_type_raw:
            property_type = 'house'
        elif 'plot' in prop_type_raw or 'land' in prop_type_raw:
            property_type = 'land'
        elif 'office' in prop_type_raw or 'commercial' in prop_type_raw:
            property_type = 'commercial'
        
        # Listing type from URL or context
        url = raw.get('pageUrl', '') or raw.get('url', '')
        listing_type = 'sale'
        if 'rent' in url.lower():
            listing_type = 'rent'
        elif 'lease' in url.lower():
            listing_type = 'lease'
        
        return {
            'property_id': property_id,
            'source': '99acres',
            'source_file': source_file,
            'raw_data': json.dumps(raw, ensure_ascii=False),
            
            'title': title,
            'description': raw.get('description'),
            'property_type': property_type,
            'listing_type': listing_type,
            
            'locality': locality,
            'area_name': locality,
            'city': 'Bangalore',
            
            'bedrooms': bedrooms,
            'total_area_sqft': area_sqft,
            
            'price': price,
            'price_per_sqft': price_per_sqft,
            'price_display': raw.get('priceRange'),
            
            'possession_status': raw.get('possessionStatus'),
            'builder_name': raw.get('postedBy'),
            
            'source_url': raw.get('url'),
            'page_url': raw.get('pageUrl'),
            'scraped_at': raw.get('scrapedAt'),
            
            'search_text': f"{title} {raw.get('description', '')} {locality or ''}"
        }


class TransformerHousing:
    """
    Transform Housing.com data.
    Very complex nested structure with 186+ fields including:
    - coords, polygons_hash, details, features, seller, address, etc.
    """
    
    @staticmethod
    def transform(raw: Dict, source_file: str = "") -> Dict[str, Any]:
        raw_id = raw.get('id', '')
        property_id = f"housing_{raw_id}" if raw_id else f"housing_{hashlib.md5(json.dumps(raw, sort_keys=True).encode()).hexdigest()[:12]}"
        
        # Extract coordinates
        coords = raw.get('coords', [])
        lat = float(coords[0]) if coords and len(coords) > 0 else None
        lng = float(coords[1]) if coords and len(coords) > 1 else None
        
        # Extract from polygons_hash
        polygons = raw.get('polygons_hash', {})
        locality_data = polygons.get('locality', {})
        city_data = polygons.get('city', {})
        region_data = polygons.get('housing_region', {})
        
        locality = locality_data.get('name')
        city = city_data.get('name', 'Bangalore')
        region = region_data.get('name')
        
        # Extract from property_information
        prop_info = raw.get('property_information', {})
        bedrooms = prop_info.get('bedrooms')
        bathrooms = prop_info.get('bathrooms')
        area_text = prop_info.get('area', '')
        area_sqft = parse_area_sqft(area_text)
        
        # Also try subtitle for BHK
        subtitle = raw.get('subtitle', '')
        if not bedrooms:
            bedrooms = parse_bhk(subtitle)
        
        # Price
        min_price = raw.get('min_price')
        max_price = raw.get('max_price')
        price = min_price or max_price
        price_display = raw.get('price_display_value')
        
        # Details
        details = raw.get('details', {})
        avg_price_value = details.get('avg_price_value')
        
        # Features extraction
        features = raw.get('features', [])
        features_dict = {f.get('id'): f.get('description') for f in features if f.get('id')}
        
        # Seller info
        seller_list = raw.get('seller', [])
        seller = seller_list[0] if seller_list else {}
        owner_name = seller.get('name')
        owner_type = seller.get('type')
        
        # Address
        address_data = raw.get('address', {})
        address = address_data.get('long_address') or address_data.get('address')
        
        # Builder/Brand
        brands = raw.get('brands', [])
        builder_name = brands[0].get('name') if brands else None
        
        # Images
        images = []
        image_url = raw.get('image_url')
        if image_url:
            images.append(image_url)
        details_images = details.get('images', [])
        for img_group in details_images:
            for img in img_group.get('images', []):
                if img.get('src'):
                    images.append(img.get('src'))
        
        # Property type from subtitle
        property_type = 'apartment'
        if 'villa' in subtitle.lower():
            property_type = 'villa'
        elif 'house' in subtitle.lower():
            property_type = 'house'
        elif 'plot' in subtitle.lower():
            property_type = 'land'
        
        # Nearby places
        nearby = raw.get('near_by_places', [])
        
        # Source-specific data
        source_specific = {
            'emi': raw.get('emi'),
            'insights': raw.get('insights'),
            'highlights': raw.get('highlights'),
            'is_most_contacted': raw.get('is_most_contacted'),
            'is_active_property': raw.get('is_active_property'),
            'property_tags': raw.get('property_tags'),
        }
        
        return {
            'property_id': property_id,
            'source': 'housing',
            'source_file': source_file,
            'raw_data': json.dumps(raw, ensure_ascii=False),
            
            'title': raw.get('name'),
            'description': raw.get('description'),
            'property_type': property_type,
            'listing_type': 'sale',
            
            'address': address,
            'locality': locality,
            'area_name': locality or region,
            'city': city,
            'latitude': lat,
            'longitude': lng,
            
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'total_area_sqft': area_sqft,
            
            'price': price,
            'price_per_sqft': avg_price_value,
            'price_display': price_display,
            
            'possession_status': raw.get('current_possession_status'),
            'builder_name': builder_name,
            'owner_name': owner_name,
            'owner_type': owner_type,
            
            'images': json.dumps(images[:10]) if images else None,
            'nearby_places': json.dumps(nearby) if nearby else None,
            'source_specific': json.dumps(source_specific),
            
            'source_url': raw.get('url'),
            'page_url': raw.get('from_url'),
            'posted_at': raw.get('posted_date'),
            
            'search_text': f"{raw.get('name', '')} {subtitle} {locality or ''} {address or ''}"
        }


class TransformerMagicBricks:
    """
    Transform MagicBricks data.
    30 fields including: id, name, price, price_per_sq_ft, description,
    location (lat,lng string), landmark_details, bedrooms, bathrooms, etc.
    """
    
    @staticmethod
    def transform(raw: Dict, source_file: str = "") -> Dict[str, Any]:
        raw_id = raw.get('id', '')
        property_id = f"mb_{raw_id}" if raw_id else f"mb_{hashlib.md5(json.dumps(raw, sort_keys=True).encode()).hexdigest()[:12]}"
        
        # Parse location string "lat,lng"
        location = raw.get('location', '')
        lat, lng = None, None
        if location and ',' in str(location):
            try:
                parts = str(location).split(',')
                lat = float(parts[0].strip())
                lng = float(parts[1].strip())
            except:
                pass
        
        # Price (already numeric)
        price = raw.get('price')
        price_per_sqft = raw.get('price_per_sq_ft')
        
        # Extract property type from name
        name = raw.get('name', '')
        property_type = 'apartment'
        if 'villa' in name.lower():
            property_type = 'villa'
        elif 'house' in name.lower() or 'independent' in name.lower():
            property_type = 'house'
        elif 'plot' in name.lower():
            property_type = 'land'
        elif 'office' in name.lower() or 'commercial' in name.lower():
            property_type = 'commercial'
        
        # Listing type from URL
        from_url = raw.get('from_url', '')
        listing_type = 'sale'
        if 'rent' in from_url.lower():
            listing_type = 'rent'
        
        # Bedrooms - try direct field first, then parse from name
        bedrooms = raw.get('bedrooms')
        if not bedrooms:
            bedrooms = parse_bhk(name)
        
        # Area
        area_sqft = raw.get('covered_area') or raw.get('carpet_area')
        
        # Landmarks
        landmarks = raw.get('landmark_details', [])
        
        # Extract locality from name
        locality = extract_locality(name) or raw.get('city_name')
        
        return {
            'property_id': property_id,
            'source': 'magicbricks',
            'source_file': source_file,
            'raw_data': json.dumps(raw, ensure_ascii=False),
            
            'title': name,
            'description': raw.get('description'),
            'property_type': property_type,
            'listing_type': listing_type,
            
            'address': raw.get('address'),
            'locality': locality,
            'area_name': locality,
            'city': raw.get('city_name', 'Bangalore'),
            'latitude': lat,
            'longitude': lng,
            
            'bedrooms': bedrooms,
            'bathrooms': raw.get('bathrooms'),
            'balconies': raw.get('balconies'),
            'total_area_sqft': area_sqft,
            'carpet_area_sqft': raw.get('carpet_area'),
            'total_floors': raw.get('floors'),
            'facing': raw.get('facing'),
            
            'price': price,
            'price_per_sqft': price_per_sqft,
            
            'builder_name': raw.get('company_name'),
            'owner_name': raw.get('owner_name'),
            
            'images': json.dumps([raw.get('image_url')]) if raw.get('image_url') else None,
            'landmarks': json.dumps(landmarks) if landmarks else None,
            'amenities': json.dumps(raw.get('amenities')) if raw.get('amenities') else None,
            
            'source_url': raw.get('url'),
            'page_url': raw.get('from_url'),
            'posted_at': raw.get('posted_date'),
            
            'search_text': f"{name} {raw.get('description', '')[:200]} {raw.get('address', '')} {locality or ''}"
        }


class TransformerNoBroker:
    """
    Transform NoBroker data.
    Most complex: 238 fields including aea__ (agent extended attributes),
    photos array, score, amenities_map, videos, etc.
    """
    
    @staticmethod
    def transform(raw: Dict, source_file: str = "") -> Dict[str, Any]:
        raw_id = raw.get('id', '')
        property_id = f"nb_{raw_id}" if raw_id else f"nb_{hashlib.md5(json.dumps(raw, sort_keys=True).encode()).hexdigest()[:12]}"
        
        # Coordinates (direct fields)
        lat = raw.get('latitude')
        lng = raw.get('longitude')
        
        # Price
        price = raw.get('price')
        if isinstance(price, str):
            price = parse_indian_price(price)
        
        expected_rent = raw.get('expected_rent')
        deposit = raw.get('formatted_deposit')
        if deposit:
            deposit = parse_indian_price(deposit)
        
        # Determine listing type from index_name
        index_name = raw.get('index_name', '').lower()
        listing_type = 'sale'
        if 'rent' in index_name:
            listing_type = 'rent'
        elif 'lease' in index_name:
            listing_type = 'lease'
        
        # BHK from type fields
        type_field = raw.get('type', '')
        type_desc = raw.get('type_desc', '')
        bedrooms = parse_bhk(type_field) or parse_bhk(type_desc)
        
        # Property type
        prop_type = raw.get('prop_type', '').lower()
        property_type = 'apartment'
        if 'villa' in prop_type or 'house' in prop_type:
            property_type = 'house'
        elif 'plot' in prop_type or 'land' in prop_type:
            property_type = 'land'
        
        # Locality
        locality = raw.get('nb_locality') or raw.get('locality')
        
        # Photos - extract image URLs
        photos = raw.get('photos', [])
        images = []
        photos_data = []
        for photo in photos[:10]:  # Limit to 10
            images_map = photo.get('images_map', {})
            if images_map.get('large'):
                images.append(f"https://nobroker.in/static/{images_map['large']}")
            photos_data.append({
                'large': images_map.get('large'),
                'medium': images_map.get('medium'),
                'thumbnail': images_map.get('thumbnail'),
                'title': photo.get('title'),
                'state': photo.get('state')
            })
        
        # Videos
        videos = raw.get('video_unit', [])
        video_url = None
        if videos:
            video_url = videos[0].get('original') or videos[0].get('high')
        
        # Amenities map
        amenities_map = raw.get('amenities_map', {})
        amenities_list = raw.get('amenities', '')
        
        # Score data
        score = raw.get('score', {})
        
        # AEA (Agent Extended Attributes) - source specific
        aea = raw.get('aea__', {})
        
        # Furnishing
        furnishing = raw.get('furnishing')
        
        # Source specific fields
        source_specific = {
            'property_score': raw.get('property_score'),
            'locality_growth_rate': raw.get('locality_growth_rate'),
            'score': score,
            'aea': aea,
            'highlights': raw.get('high_lights'),
            'negotiable': raw.get('negotiable'),
            'premium': raw.get('premium'),
            'verified': raw.get('verified'),
            'loan_available': raw.get('loan_available'),
            'under_loan': raw.get('under_loan'),
            'ownership_type': raw.get('ownership_type'),
            'lease_type': raw.get('lease_type_new'),
        }
        
        return {
            'property_id': property_id,
            'source': 'nobroker',
            'source_file': source_file,
            'raw_data': json.dumps(raw, ensure_ascii=False),
            
            'title': raw.get('title') or raw.get('property_title'),
            'description': raw.get('seo_description'),
            'property_type': property_type,
            'listing_type': listing_type,
            
            'address': raw.get('address'),
            'locality': locality,
            'area_name': locality,
            'city': raw.get('city', 'Bangalore'),
            'latitude': lat,
            'longitude': lng,
            
            'bedrooms': bedrooms,
            'bathrooms': raw.get('bathroom'),
            'total_area_sqft': raw.get('property_size'),
            'floor_number': raw.get('floor'),
            'total_floors': raw.get('total_floor'),
            'furnishing': furnishing,
            'facing': raw.get('facing_desc') or raw.get('facing'),
            'age_years': raw.get('property_age') if raw.get('property_age', -1) >= 0 else None,
            'parking': raw.get('parking_desc') or raw.get('parking'),
            
            'price': price or expected_rent,
            'price_display': raw.get('formatted_price'),
            'deposit': deposit,
            'maintenance_monthly': parse_indian_price(raw.get('formatted_maintenance_amount')),
            'negotiable': raw.get('negotiable'),
            
            'amenities': amenities_list,
            'amenities_map': json.dumps(amenities_map) if amenities_map else None,
            
            'owner_name': raw.get('owner_name'),
            'owner_type': 'owner' if not raw.get('buyer_property') else 'agent',
            
            'images': json.dumps(images) if images else None,
            'photos_data': json.dumps(photos_data) if photos_data else None,
            'video_url': video_url,
            
            'verified': raw.get('verified'),
            'premium': raw.get('premium'),
            'property_score': raw.get('property_score'),
            'locality_growth_rate': raw.get('locality_growth_rate'),
            
            'source_specific': json.dumps(source_specific),
            
            'source_url': raw.get('url') or raw.get('short_url'),
            'page_url': raw.get('detail_url') or raw.get('from_url'),
            'project_url': raw.get('project_url'),
            'posted_at': parse_timestamp(raw.get('creation_date')),
            'available_from': parse_timestamp(raw.get('available_from')),
            
            'search_text': f"{raw.get('title', '')} {raw.get('property_title', '')} {locality or ''} {raw.get('society', '')}"
        }


# Transformer mapping
TRANSFORMERS = {
    '99acres': Transformer99Acres,
    'housing': TransformerHousing,
    'magicbricks': TransformerMagicBricks,
    'nobroker': TransformerNoBroker,
}


def get_transformer(source: str):
    """Get transformer class for a source."""
    return TRANSFORMERS.get(source.lower())
