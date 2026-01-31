"""
Property Image Downloader for Valora
Downloads property images from database links, maps them to properties,
and stores locally for AI training and reasoning.
"""

import sqlite3
import json
import os
import sys
import hashlib
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import logging
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DB_PATH = PROJECT_DIR / "src" / "data" / "valora.db"
IMAGES_DIR = PROJECT_DIR / "data" / "property_images"
METADATA_PATH = IMAGES_DIR / "image_metadata.json"
TRAINING_DATA_PATH = IMAGES_DIR / "training_data.jsonl"


@dataclass
class PropertyImage:
    """Represents a downloaded property image with metadata."""
    property_id: str
    image_url: str
    local_path: str
    image_hash: str
    source: str
    download_time: str
    file_size: int
    property_data: Dict  # Subset of property info for training


class PropertyImageDownloader:
    """Downloads and organizes property images for AI training."""
    
    def __init__(self, db_path: Path = DB_PATH, images_dir: Path = IMAGES_DIR):
        self.db_path = db_path
        self.images_dir = images_dir
        self.metadata: Dict[str, PropertyImage] = {}
        self.stats = {
            "total_properties": 0,
            "properties_with_images": 0,
            "total_image_urls": 0,
            "downloaded": 0,
            "failed": 0,
            "skipped": 0
        }
        
        # Create directories
        self.images_dir.mkdir(parents=True, exist_ok=True)
        (self.images_dir / "by_property").mkdir(exist_ok=True)
        (self.images_dir / "by_locality").mkdir(exist_ok=True)
        (self.images_dir / "by_type").mkdir(exist_ok=True)
        
        # Load existing metadata
        self._load_metadata()
    
    def _load_metadata(self):
        """Load existing metadata if available."""
        if METADATA_PATH.exists():
            try:
                with open(METADATA_PATH, 'r') as f:
                    data = json.load(f)
                    self.metadata = {k: PropertyImage(**v) for k, v in data.items()}
                logger.info(f"Loaded {len(self.metadata)} existing image records")
            except Exception as e:
                logger.warning(f"Could not load metadata: {e}")
    
    def _save_metadata(self):
        """Save metadata to disk."""
        with open(METADATA_PATH, 'w') as f:
            json.dump({k: asdict(v) for k, v in self.metadata.items()}, f, indent=2)
        logger.info(f"Saved metadata for {len(self.metadata)} images")
    
    def get_properties_with_images(self, limit: Optional[int] = None) -> List[Dict]:
        """Fetch properties that have image URLs."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT 
                property_id, source, title, description, property_type, listing_type,
                locality, area_name, city, latitude, longitude,
                bedrooms, bathrooms, total_area_sqft, price, price_per_sqft,
                images, photos_data, builder_name, source_url
            FROM properties 
            WHERE images IS NOT NULL 
              AND images != '[]' 
              AND images != ''
              AND images != 'null'
            ORDER BY 
                CASE WHEN source = 'magicbricks' THEN 0 ELSE 1 END,
                property_id
        """
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        properties = []
        for row in rows:
            prop = dict(row)
            # Parse images JSON
            try:
                prop['image_urls'] = json.loads(prop.get('images') or '[]')
            except:
                prop['image_urls'] = []
            
            # Parse photos_data if available (NoBroker format)
            try:
                prop['photos_data'] = json.loads(prop.get('photos_data') or '[]')
            except:
                prop['photos_data'] = []
            
            if prop['image_urls']:
                properties.append(prop)
        
        return properties
    
    def analyze_images(self) -> Dict:
        """Analyze image URLs in database without downloading."""
        properties = self.get_properties_with_images()
        
        self.stats["total_properties"] = len(properties)
        
        source_stats = {}
        locality_stats = {}
        type_stats = {}
        url_domains = {}
        
        for prop in properties:
            source = prop.get('source', 'unknown')
            locality = prop.get('locality') or prop.get('area_name') or 'unknown'
            prop_type = prop.get('property_type', 'unknown')
            
            image_urls = prop.get('image_urls', [])
            self.stats["total_image_urls"] += len(image_urls)
            
            # Count by source
            if source not in source_stats:
                source_stats[source] = {"properties": 0, "images": 0}
            source_stats[source]["properties"] += 1
            source_stats[source]["images"] += len(image_urls)
            
            # Count by locality
            if locality not in locality_stats:
                locality_stats[locality] = {"properties": 0, "images": 0}
            locality_stats[locality]["properties"] += 1
            locality_stats[locality]["images"] += len(image_urls)
            
            # Count by type
            if prop_type not in type_stats:
                type_stats[prop_type] = {"properties": 0, "images": 0}
            type_stats[prop_type]["properties"] += 1
            type_stats[prop_type]["images"] += len(image_urls)
            
            # Analyze URL domains
            for url in image_urls:
                try:
                    domain = urlparse(url).netloc
                    url_domains[domain] = url_domains.get(domain, 0) + 1
                except:
                    pass
        
        self.stats["properties_with_images"] = len(properties)
        
        return {
            "stats": self.stats,
            "by_source": source_stats,
            "by_locality": dict(sorted(locality_stats.items(), key=lambda x: x[1]["images"], reverse=True)[:20]),
            "by_type": type_stats,
            "url_domains": dict(sorted(url_domains.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def _get_image_filename(self, property_id: str, url: str, index: int) -> str:
        """Generate a consistent filename for an image."""
        # Get extension from URL
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        if '.jpg' in path or '.jpeg' in path:
            ext = '.jpg'
        elif '.png' in path:
            ext = '.png'
        elif '.webp' in path:
            ext = '.webp'
        else:
            ext = '.jpg'  # Default
        
        # Create filename: property_id_index_hash.ext
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"{property_id}_{index:02d}_{url_hash}{ext}"
    
    async def _download_image(
        self, 
        session: aiohttp.ClientSession, 
        url: str, 
        save_path: Path,
        property_id: str
    ) -> Tuple[bool, Optional[str], int]:
        """Download a single image."""
        try:
            # Simple headers - avoid triggering anti-bot
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/*,*/*',
            }
            
            timeout = aiohttp.ClientTimeout(total=60, connect=30)
            
            async with session.get(url, headers=headers, timeout=timeout, ssl=False) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Validate it's actually an image (check magic bytes)
                    if len(content) < 500:
                        logger.warning(f"Image too small ({len(content)} bytes): {url[:50]}")
                        return False, None, 0
                    
                    # Check for common image magic bytes
                    is_image = (
                        content[:3] == b'\xff\xd8\xff' or  # JPEG
                        content[:8] == b'\x89PNG\r\n\x1a\n' or  # PNG
                        content[:4] == b'RIFF' or  # WebP
                        content[:4] == b'GIF8'  # GIF
                    )
                    
                    if not is_image:
                        logger.warning(f"Not an image file: {url[:50]}")
                        return False, None, 0
                    
                    # Save file
                    async with aiofiles.open(save_path, 'wb') as f:
                        await f.write(content)
                    
                    # Calculate hash
                    image_hash = hashlib.md5(content).hexdigest()
                    
                    return True, image_hash, len(content)
                else:
                    logger.warning(f"HTTP {response.status} for {url[:60]}")
                    return False, None, 0
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout: {url[:60]}")
            return False, None, 0
        except Exception as e:
            logger.warning(f"Error: {e} - {url[:60]}")
            return False, None, 0
    
    async def download_property_images(
        self, 
        property_data: Dict,
        max_images_per_property: int = 5
    ) -> List[PropertyImage]:
        """Download images for a single property."""
        property_id = property_data['property_id']
        image_urls = property_data.get('image_urls', [])[:max_images_per_property]
        
        if not image_urls:
            return []
        
        # Create property-specific directory
        prop_dir = self.images_dir / "by_property" / property_id
        prop_dir.mkdir(exist_ok=True)
        
        # Create locality directory with symlinks
        locality = property_data.get('locality') or property_data.get('area_name') or 'unknown'
        locality_safe = "".join(c if c.isalnum() or c in ' -_' else '_' for c in locality)[:50]
        locality_dir = self.images_dir / "by_locality" / locality_safe
        locality_dir.mkdir(exist_ok=True)
        
        downloaded_images = []
        
        async with aiohttp.ClientSession() as session:
            for idx, url in enumerate(image_urls):
                # Check if already downloaded
                url_hash = hashlib.md5(url.encode()).hexdigest()
                if url_hash in self.metadata:
                    self.stats["skipped"] += 1
                    continue
                
                filename = self._get_image_filename(property_id, url, idx)
                save_path = prop_dir / filename
                
                success, image_hash, file_size = await self._download_image(
                    session, url, save_path, property_id
                )
                
                if success:
                    self.stats["downloaded"] += 1
                    
                    # Create property data subset for training
                    training_data = {
                        "property_id": property_id,
                        "source": property_data.get("source"),
                        "property_type": property_data.get("property_type"),
                        "listing_type": property_data.get("listing_type"),
                        "locality": locality,
                        "city": property_data.get("city"),
                        "bedrooms": property_data.get("bedrooms"),
                        "bathrooms": property_data.get("bathrooms"),
                        "area_sqft": property_data.get("total_area_sqft"),
                        "price": property_data.get("price"),
                        "price_per_sqft": property_data.get("price_per_sqft"),
                        "latitude": property_data.get("latitude"),
                        "longitude": property_data.get("longitude")
                    }
                    
                    prop_image = PropertyImage(
                        property_id=property_id,
                        image_url=url,
                        local_path=str(save_path.relative_to(PROJECT_DIR)),
                        image_hash=image_hash,
                        source=property_data.get("source", "unknown"),
                        download_time=datetime.now().isoformat(),
                        file_size=file_size,
                        property_data=training_data
                    )
                    
                    self.metadata[url_hash] = prop_image
                    downloaded_images.append(prop_image)
                    
                    # Create symlink in locality dir
                    try:
                        locality_link = locality_dir / filename
                        if not locality_link.exists():
                            locality_link.symlink_to(save_path)
                    except:
                        pass  # Symlinks may not work on Windows
                else:
                    self.stats["failed"] += 1
        
        return downloaded_images
    
    async def download_all_images(
        self,
        limit: Optional[int] = None,
        max_images_per_property: int = 5,
        batch_size: int = 10
    ):
        """Download images for all properties with images."""
        properties = self.get_properties_with_images(limit)
        total = len(properties)
        
        logger.info(f"Starting download for {total} properties")
        
        for i in range(0, total, batch_size):
            batch = properties[i:i+batch_size]
            
            tasks = [
                self.download_property_images(prop, max_images_per_property)
                for prop in batch
            ]
            
            await asyncio.gather(*tasks)
            
            # Save metadata periodically
            if (i + batch_size) % 50 == 0:
                self._save_metadata()
                logger.info(f"Progress: {i+batch_size}/{total} properties processed")
                logger.info(f"  Downloaded: {self.stats['downloaded']}, Failed: {self.stats['failed']}, Skipped: {self.stats['skipped']}")
        
        # Final save
        self._save_metadata()
        self._generate_training_data()
        
        return self.stats
    
    def _generate_training_data(self):
        """Generate JSONL training data file for AI models."""
        logger.info("Generating training data file...")
        
        with open(TRAINING_DATA_PATH, 'w', encoding='utf-8') as f:
            for url_hash, prop_image in self.metadata.items():
                record = {
                    "image_path": prop_image.local_path,
                    "property_id": prop_image.property_id,
                    "source": prop_image.source,
                    **prop_image.property_data
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        logger.info(f"Generated training data: {TRAINING_DATA_PATH}")
    
    def get_training_summary(self) -> Dict:
        """Get summary of downloaded images for training."""
        by_source = {}
        by_locality = {}
        by_type = {}
        
        for prop_image in self.metadata.values():
            source = prop_image.source
            locality = prop_image.property_data.get('locality', 'unknown')
            prop_type = prop_image.property_data.get('property_type', 'unknown')
            
            by_source[source] = by_source.get(source, 0) + 1
            by_locality[locality] = by_locality.get(locality, 0) + 1
            by_type[prop_type] = by_type.get(prop_type, 0) + 1
        
        return {
            "total_images": len(self.metadata),
            "by_source": by_source,
            "by_locality": dict(sorted(by_locality.items(), key=lambda x: x[1], reverse=True)[:20]),
            "by_property_type": by_type,
            "training_file": str(TRAINING_DATA_PATH),
            "images_directory": str(self.images_dir)
        }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download property images for AI training")
    parser.add_argument("--analyze", action="store_true", help="Analyze images without downloading")
    parser.add_argument("--download", action="store_true", help="Download images")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of properties")
    parser.add_argument("--max-images", type=int, default=5, help="Max images per property")
    parser.add_argument("--summary", action="store_true", help="Show training data summary")
    
    args = parser.parse_args()
    
    downloader = PropertyImageDownloader()
    
    if args.analyze or (not args.download and not args.summary):
        print("\n" + "="*60)
        print("PROPERTY IMAGE ANALYSIS")
        print("="*60)
        
        analysis = downloader.analyze_images()
        
        print(f"\n📊 Overall Stats:")
        print(f"   Properties with images: {analysis['stats']['properties_with_images']}")
        print(f"   Total image URLs: {analysis['stats']['total_image_urls']}")
        
        print(f"\n📁 By Source:")
        for source, data in analysis['by_source'].items():
            print(f"   {source}: {data['properties']} properties, {data['images']} images")
        
        print(f"\n🏠 By Property Type:")
        for ptype, data in analysis['by_type'].items():
            print(f"   {ptype}: {data['properties']} properties, {data['images']} images")
        
        print(f"\n🌐 Top Image Domains:")
        for domain, count in list(analysis['url_domains'].items())[:10]:
            print(f"   {domain}: {count} images")
        
        print(f"\n📍 Top Localities:")
        for locality, data in list(analysis['by_locality'].items())[:10]:
            print(f"   {locality}: {data['images']} images")
    
    if args.download:
        print("\n" + "="*60)
        print("DOWNLOADING IMAGES")
        print("="*60)
        
        try:
            stats = asyncio.run(downloader.download_all_images(
                limit=args.limit,
                max_images_per_property=args.max_images
            ))
            
            print(f"\n✅ Download Complete!")
            print(f"   Downloaded: {stats['downloaded']}")
            print(f"   Failed: {stats['failed']}")
            print(f"   Skipped (already exists): {stats['skipped']}")
            print(f"\n   Images saved to: {IMAGES_DIR}")
            print(f"   Training data: {TRAINING_DATA_PATH}")
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
    
    if args.summary:
        print("\n" + "="*60)
        print("TRAINING DATA SUMMARY")
        print("="*60)
        
        summary = downloader.get_training_summary()
        print(f"\n📷 Total Images: {summary['total_images']}")
        print(f"\n📁 By Source:")
        for source, count in summary['by_source'].items():
            print(f"   {source}: {count}")
        print(f"\n📄 Training File: {summary['training_file']}")
        print(f"📁 Images Dir: {summary['images_directory']}")


if __name__ == "__main__":
    main()
