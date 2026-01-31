"""
Property Image Service for Valora AI
Provides image access and metadata for AI training and reasoning.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass, asdict
import random

logger = logging.getLogger(__name__)

# Paths
SERVICE_DIR = Path(__file__).parent
BACKEND_DIR = SERVICE_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
IMAGES_DIR = PROJECT_DIR / "data" / "property_images"
METADATA_PATH = IMAGES_DIR / "image_metadata.json"
TRAINING_DATA_PATH = IMAGES_DIR / "training_data.jsonl"


@dataclass
class PropertyImageInfo:
    """Property image with metadata for AI."""
    property_id: str
    image_path: str
    source: str
    property_type: Optional[str]
    listing_type: Optional[str]
    locality: Optional[str]
    city: Optional[str]
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    area_sqft: Optional[float]
    price: Optional[float]
    price_per_sqft: Optional[float]
    latitude: Optional[float]
    longitude: Optional[float]


class PropertyImageService:
    """Service for accessing property images for AI training and reasoning."""
    
    def __init__(self):
        self.images_dir = IMAGES_DIR
        self.metadata: Dict[str, Dict] = {}
        self.training_data: List[Dict] = []
        self._load_data()
    
    def _load_data(self):
        """Load metadata and training data."""
        # Load metadata
        if METADATA_PATH.exists():
            try:
                with open(METADATA_PATH, 'r') as f:
                    self.metadata = json.load(f)
                logger.info(f"[ImageService] Loaded {len(self.metadata)} image records")
            except Exception as e:
                logger.warning(f"[ImageService] Could not load metadata: {e}")
        
        # Load training data
        if TRAINING_DATA_PATH.exists():
            try:
                with open(TRAINING_DATA_PATH, 'r') as f:
                    self.training_data = [json.loads(line) for line in f if line.strip()]
                logger.info(f"[ImageService] Loaded {len(self.training_data)} training records")
            except Exception as e:
                logger.warning(f"[ImageService] Could not load training data: {e}")
    
    def get_stats(self) -> Dict:
        """Get image collection statistics."""
        if not self.training_data:
            return {"total_images": 0, "message": "No images downloaded yet"}
        
        by_source = {}
        by_type = {}
        by_locality = {}
        by_listing = {}
        
        for record in self.training_data:
            source = record.get('source', 'unknown')
            prop_type = record.get('property_type', 'unknown')
            locality = record.get('locality', 'unknown')
            listing = record.get('listing_type', 'unknown')
            
            by_source[source] = by_source.get(source, 0) + 1
            by_type[prop_type] = by_type.get(prop_type, 0) + 1
            by_locality[locality] = by_locality.get(locality, 0) + 1
            by_listing[listing] = by_listing.get(listing, 0) + 1
        
        return {
            "total_images": len(self.training_data),
            "by_source": by_source,
            "by_property_type": dict(sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_locality": dict(sorted(by_locality.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_listing_type": by_listing,
            "images_directory": str(self.images_dir)
        }
    
    def get_images_for_property(self, property_id: str) -> List[Dict]:
        """Get all images for a specific property."""
        return [
            record for record in self.training_data
            if record.get('property_id') == property_id
        ]
    
    def get_images_by_locality(self, locality: str, limit: int = 10) -> List[Dict]:
        """Get images from a specific locality."""
        matches = [
            record for record in self.training_data
            if locality.lower() in str(record.get('locality', '')).lower()
        ]
        return matches[:limit]
    
    def get_images_by_type(self, property_type: str, limit: int = 10) -> List[Dict]:
        """Get images by property type."""
        matches = [
            record for record in self.training_data
            if property_type.lower() in str(record.get('property_type', '')).lower()
        ]
        return matches[:limit]
    
    def get_images_by_price_range(
        self, 
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get images by price range."""
        matches = []
        for record in self.training_data:
            price = record.get('price')
            if price is None:
                continue
            if min_price and price < min_price:
                continue
            if max_price and price > max_price:
                continue
            matches.append(record)
        return matches[:limit]
    
    def get_images_near_location(
        self,
        lat: float,
        lng: float,
        radius_km: float = 2.0,
        limit: int = 10
    ) -> List[Dict]:
        """Get images near a location."""
        from math import radians, cos, sin, asin, sqrt
        
        def haversine(lat1, lon1, lat2, lon2):
            """Calculate distance in km."""
            R = 6371
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            return 2 * R * asin(sqrt(a))
        
        matches = []
        for record in self.training_data:
            r_lat = record.get('latitude')
            r_lng = record.get('longitude')
            if r_lat and r_lng:
                dist = haversine(lat, lng, r_lat, r_lng)
                if dist <= radius_km:
                    record['_distance_km'] = round(dist, 2)
                    matches.append(record)
        
        matches.sort(key=lambda x: x.get('_distance_km', float('inf')))
        return matches[:limit]
    
    def get_random_samples(self, count: int = 10) -> List[Dict]:
        """Get random sample images for training."""
        if not self.training_data:
            return []
        return random.sample(self.training_data, min(count, len(self.training_data)))
    
    def get_training_batch(
        self,
        batch_size: int = 32,
        property_type: Optional[str] = None,
        listing_type: Optional[str] = None
    ) -> List[Dict]:
        """Get a batch of training data with optional filters."""
        filtered = self.training_data
        
        if property_type:
            filtered = [r for r in filtered if property_type.lower() in str(r.get('property_type', '')).lower()]
        
        if listing_type:
            filtered = [r for r in filtered if r.get('listing_type') == listing_type]
        
        if not filtered:
            return []
        
        return random.sample(filtered, min(batch_size, len(filtered)))
    
    def get_image_path(self, property_id: str, index: int = 0) -> Optional[Path]:
        """Get absolute path to a property image."""
        images = self.get_images_for_property(property_id)
        if images and index < len(images):
            rel_path = images[index].get('image_path')
            if rel_path:
                abs_path = PROJECT_DIR / rel_path
                if abs_path.exists():
                    return abs_path
        return None
    
    def prepare_vl_training_data(self) -> List[Dict]:
        """Prepare data for Vision-Language model training (Qwen3-VL format)."""
        vl_data = []
        
        for record in self.training_data:
            # Create description from metadata
            parts = []
            
            if record.get('property_type'):
                parts.append(record['property_type'].strip())
            
            if record.get('bedrooms'):
                parts.append(f"{record['bedrooms']} BHK")
            
            if record.get('area_sqft'):
                parts.append(f"{record['area_sqft']:.0f} sq.ft")
            
            if record.get('price'):
                price = record['price']
                if price >= 10000000:
                    parts.append(f"₹{price/10000000:.1f} Cr")
                elif price >= 100000:
                    parts.append(f"₹{price/100000:.1f} L")
                else:
                    parts.append(f"₹{price:.0f}")
            
            if record.get('locality'):
                parts.append(f"in {record['locality']}")
            
            description = " | ".join(parts) if parts else "Property image"
            
            vl_data.append({
                "image": str(PROJECT_DIR / record['image_path']),
                "conversations": [
                    {
                        "role": "user",
                        "content": "<image>\nDescribe this property image."
                    },
                    {
                        "role": "assistant",
                        "content": description
                    }
                ],
                "metadata": {
                    "property_id": record.get('property_id'),
                    "latitude": record.get('latitude'),
                    "longitude": record.get('longitude'),
                    "price": record.get('price'),
                    "bedrooms": record.get('bedrooms')
                }
            })
        
        return vl_data
    
    def export_for_training(self, output_path: Optional[Path] = None) -> Path:
        """Export training data in format suitable for model fine-tuning."""
        if output_path is None:
            output_path = IMAGES_DIR / "vl_training_data.json"
        
        vl_data = self.prepare_vl_training_data()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(vl_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[ImageService] Exported {len(vl_data)} records to {output_path}")
        return output_path


# Singleton instance
_image_service: Optional[PropertyImageService] = None


def get_image_service() -> PropertyImageService:
    """Get or create the image service singleton."""
    global _image_service
    if _image_service is None:
        _image_service = PropertyImageService()
    return _image_service
