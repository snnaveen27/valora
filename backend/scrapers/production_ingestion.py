"""
Production-Ready Data Ingestion Pipeline for Valora AI

Handles:
1. Duplicate locations with different prices (different listings)
2. Same property re-scraped over time (price history tracking)
3. Multiple sources (Apify, manual CSV, external APIs)
4. Coordinate-based location grouping for analytics

Key Concepts:
- property_id: Unique identifier for a listing (platform + location + type)
- listing_id: Unique for each scrape/source occurrence
- location_key: Normalized lat/lng for grouping nearby properties
- price_history: Tracks all price observations over time
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass
class PropertyListing:
    """Represents a single property listing."""
    listing_id: str
    property_id: str  # Deduplicated ID
    source: str  # apify, manual, csv, external
    source_file: str
    source_url: str
    
    # Core property info
    title: str
    price: float
    price_per_sqft: float
    bedrooms: int
    bathrooms: int
    area_sqft: float
    property_type: str
    listing_type: str  # sale, rent
    
    # Location
    latitude: float
    longitude: float
    locality: str
    address: str
    
    # Location key for grouping (rounded coords)
    location_key: str
    
    # Metadata
    scraped_at: datetime
    posted_at: Optional[datetime]
    raw_data: Dict
    
    # Flags
    is_duplicate: bool = False
    duplicate_of: str = None


class ProductionIngestionService:
    """
    Production-ready ingestion service with proper duplicate handling
    and price history tracking.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
        self._ensure_tables()
    
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_tables(self):
        """Ensure all required tables exist with proper schema."""
        conn = self._connect()
        cursor = conn.cursor()
        
        # Ingestion log - tracks all ingestion runs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT UNIQUE,
                source TEXT NOT NULL,
                source_file TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'running',
                total_records INTEGER DEFAULT 0,
                new_records INTEGER DEFAULT 0,
                updated_records INTEGER DEFAULT 0,
                duplicate_records INTEGER DEFAULT 0,
                error_records INTEGER DEFAULT 0,
                notes TEXT
            )
        """)
        
        # Price history with proper indexing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id TEXT NOT NULL,
                listing_id TEXT,
                price REAL,
                price_per_sqft REAL,
                locality TEXT,
                location_key TEXT,
                area_sqft REAL,
                bedrooms INTEGER,
                property_type TEXT,
                source TEXT,
                snapshot_date DATE NOT NULL,
                scraped_at TIMESTAMP,
                raw_price_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(property_id, snapshot_date, source)
            )
        """)
        
        # Location analytics - aggregated stats by location
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS location_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_key TEXT UNIQUE,
                latitude REAL,
                longitude REAL,
                locality TEXT,
                total_listings INTEGER DEFAULT 0,
                avg_price REAL,
                min_price REAL,
                max_price REAL,
                avg_price_per_sqft REAL,
                price_trend TEXT DEFAULT 'stable',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_property ON price_history(property_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_location ON price_history(location_key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(snapshot_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_locality ON price_history(locality)")
        
        conn.commit()
        conn.close()
    
    def _generate_location_key(self, lat: float, lng: float, precision: int = 4) -> str:
        """
        Generate a location key for grouping nearby properties.
        precision=4 gives ~11m resolution (good for building-level grouping)
        precision=3 gives ~111m resolution (good for block-level grouping)
        """
        if not lat or not lng:
            return "unknown"
        return f"{round(lat, precision)}_{round(lng, precision)}"
    
    def _generate_listing_id(self, raw_data: Dict, source: str, scraped_at: datetime) -> str:
        """Generate unique listing ID for each scrape occurrence."""
        # Include timestamp to make each scrape unique
        content = f"{source}_{scraped_at.isoformat()}_{json.dumps(raw_data, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _generate_property_id(self, lat: float, lng: float, bedrooms: int, 
                             property_type: str, source: str) -> str:
        """
        Generate deduplicated property ID.
        Same property = same location + same config + same source platform
        """
        location_key = self._generate_location_key(lat, lng, precision=4)
        prop_type = (property_type or "unknown").lower().replace(" ", "_")[:15]
        return f"{source}_{prop_type}_{bedrooms}bhk_{location_key}"
    
    def ingest_property(self, raw_data: Dict, source: str, source_file: str = None,
                       scraped_at: datetime = None) -> Tuple[str, str, bool]:
        """
        Ingest a single property with proper duplicate handling.
        
        Returns: (property_id, listing_id, is_new)
        """
        if scraped_at is None:
            scraped_at = datetime.now()
        
        # Extract fields (handle various formats from different sources)
        lat = self._extract_float(raw_data, ['latitude', 'lat', 'geo_lat'])
        lng = self._extract_float(raw_data, ['longitude', 'lng', 'lon', 'geo_lng'])
        
        price = self._extract_price(raw_data)
        area = self._extract_float(raw_data, ['area', 'area_sqft', 'total_area_sqft', 'carpet_area', 'builtup_area', 'superBuiltupArea'])
        bedrooms = self._extract_int(raw_data, ['bedrooms', 'bhk', 'bedroom', 'beds'])
        bathrooms = self._extract_int(raw_data, ['bathrooms', 'bathroom', 'baths'])
        
        property_type = self._extract_str(raw_data, ['property_type', 'propertyType', 'type'])
        listing_type = self._extract_str(raw_data, ['listing_type', 'listingType', 'transaction_type'])
        locality = self._extract_str(raw_data, ['locality', 'location', 'area_name', 'localityName'])
        address = self._extract_str(raw_data, ['address', 'full_address', 'propertyAddress'])
        title = self._extract_str(raw_data, ['title', 'name', 'propertyTitle', 'heading'])
        source_url = self._extract_str(raw_data, ['url', 'source_url', 'propertyUrl', 'pageUrl'])
        
        # Calculate price per sqft
        price_per_sqft = None
        if price and area and area > 0:
            price_per_sqft = price / area
        
        # Generate IDs
        listing_id = self._generate_listing_id(raw_data, source, scraped_at)
        property_id = self._generate_property_id(lat, lng, bedrooms or 0, property_type, source)
        location_key = self._generate_location_key(lat, lng)
        
        conn = self._connect()
        cursor = conn.cursor()
        
        try:
            # Check if this exact property exists
            cursor.execute("""
                SELECT property_id, price FROM properties 
                WHERE property_id = ?
            """, (property_id,))
            
            existing = cursor.fetchone()
            is_new = existing is None
            
            if is_new:
                # Insert new property
                cursor.execute("""
                    INSERT INTO properties (
                        property_id, source, source_file, raw_data,
                        title, price, price_per_sqft, bedrooms, bathrooms,
                        total_area_sqft, property_type, listing_type,
                        latitude, longitude, locality, address,
                        source_url, scraped_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    property_id, source, source_file, json.dumps(raw_data),
                    title, price, price_per_sqft, bedrooms, bathrooms,
                    area, property_type, listing_type,
                    lat, lng, locality, address,
                    source_url, scraped_at, datetime.now()
                ))
            else:
                # Update existing property if price changed
                old_price = existing['price']
                if price and old_price and abs(price - old_price) > 1:
                    cursor.execute("""
                        UPDATE properties SET
                            price = ?, price_per_sqft = ?, 
                            raw_data = ?, scraped_at = ?, updated_at = ?
                        WHERE property_id = ?
                    """, (price, price_per_sqft, json.dumps(raw_data), 
                          scraped_at, datetime.now(), property_id))
            
            # Always record in price history (tracks price over time)
            cursor.execute("""
                INSERT OR REPLACE INTO price_history (
                    property_id, listing_id, price, price_per_sqft,
                    locality, location_key, area_sqft, bedrooms,
                    property_type, source, snapshot_date, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                property_id, listing_id, price, price_per_sqft,
                locality, location_key, area, bedrooms,
                property_type, source, date.today(), scraped_at
            ))
            
            conn.commit()
            return property_id, listing_id, is_new
            
        finally:
            conn.close()
    
    def ingest_batch(self, records: List[Dict], source: str, 
                    source_file: str = None, run_id: str = None) -> Dict[str, int]:
        """
        Ingest a batch of records with progress tracking.
        
        Returns: Stats dict with counts
        """
        if run_id is None:
            run_id = f"{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        conn = self._connect()
        cursor = conn.cursor()
        
        # Log ingestion start
        cursor.execute("""
            INSERT INTO ingestion_log (run_id, source, source_file, total_records)
            VALUES (?, ?, ?, ?)
        """, (run_id, source, source_file, len(records)))
        conn.commit()
        conn.close()
        
        stats = {
            'total': len(records),
            'new': 0,
            'updated': 0,
            'duplicate': 0,
            'error': 0
        }
        
        for i, record in enumerate(records):
            try:
                property_id, listing_id, is_new = self.ingest_property(
                    record, source, source_file, datetime.now()
                )
                
                if is_new:
                    stats['new'] += 1
                else:
                    stats['duplicate'] += 1
                    
            except Exception as e:
                stats['error'] += 1
            
            # Progress logging
            if (i + 1) % 1000 == 0:
                print(f"  Progress: {i+1}/{len(records)} ({stats['new']} new, {stats['duplicate']} dup)")
        
        # Update ingestion log
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ingestion_log SET
                completed_at = ?, status = 'completed',
                new_records = ?, updated_records = ?,
                duplicate_records = ?, error_records = ?
            WHERE run_id = ?
        """, (datetime.now(), stats['new'], stats['updated'],
              stats['duplicate'], stats['error'], run_id))
        conn.commit()
        conn.close()
        
        return stats
    
    def update_location_analytics(self):
        """Update location-based analytics for all locations."""
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO location_analytics 
            (location_key, latitude, longitude, locality, 
             total_listings, avg_price, min_price, max_price, avg_price_per_sqft)
            SELECT 
                ROUND(latitude, 4) || '_' || ROUND(longitude, 4) as location_key,
                ROUND(AVG(latitude), 6) as latitude,
                ROUND(AVG(longitude), 6) as longitude,
                locality,
                COUNT(*) as total_listings,
                ROUND(AVG(price), 2) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price,
                ROUND(AVG(price_per_sqft), 2) as avg_price_per_sqft
            FROM properties
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            AND price > 0
            GROUP BY location_key, locality
        """)
        
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM location_analytics")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def get_price_trends_by_location(self, location_key: str = None, 
                                     locality: str = None,
                                     days: int = 90) -> List[Dict]:
        """Get price trends for a location over time."""
        conn = self._connect()
        cursor = conn.cursor()
        
        if location_key:
            cursor.execute("""
                SELECT snapshot_date, AVG(price) as avg_price, 
                       AVG(price_per_sqft) as avg_ppsf, COUNT(*) as listings
                FROM price_history
                WHERE location_key = ?
                AND snapshot_date >= date('now', '-' || ? || ' days')
                GROUP BY snapshot_date
                ORDER BY snapshot_date
            """, (location_key, days))
        elif locality:
            cursor.execute("""
                SELECT snapshot_date, AVG(price) as avg_price,
                       AVG(price_per_sqft) as avg_ppsf, COUNT(*) as listings
                FROM price_history
                WHERE locality LIKE ?
                AND snapshot_date >= date('now', '-' || ? || ' days')
                GROUP BY snapshot_date
                ORDER BY snapshot_date
            """, (f"%{locality}%", days))
        else:
            return []
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    # Helper extraction methods
    def _extract_float(self, data: Dict, keys: List[str]) -> Optional[float]:
        for key in keys:
            val = data.get(key)
            if val is not None:
                try:
                    return float(val)
                except:
                    pass
        return None
    
    def _extract_int(self, data: Dict, keys: List[str]) -> Optional[int]:
        for key in keys:
            val = data.get(key)
            if val is not None:
                try:
                    if isinstance(val, str):
                        # Extract digits from string like "2 BHK"
                        import re
                        match = re.search(r'\d+', val)
                        if match:
                            return int(match.group())
                    return int(val)
                except:
                    pass
        return None
    
    def _extract_str(self, data: Dict, keys: List[str]) -> Optional[str]:
        for key in keys:
            val = data.get(key)
            if val:
                return str(val).strip()
        return None
    
    def _extract_price(self, data: Dict) -> Optional[float]:
        """Extract price handling Indian formats."""
        import re
        
        price_keys = ['price', 'expected_price', 'asking_price', 'rent', 'propertyPrice']
        
        for key in price_keys:
            val = data.get(key)
            if val is None:
                continue
                
            if isinstance(val, (int, float)):
                return float(val)
            
            val = str(val).lower().replace(',', '').strip()
            
            # Handle Crore
            if 'cr' in val:
                match = re.search(r'([\d.]+)', val)
                if match:
                    return float(match.group(1)) * 10000000
            
            # Handle Lac/Lakh
            if 'lac' in val or 'lakh' in val:
                match = re.search(r'([\d.]+)', val)
                if match:
                    return float(match.group(1)) * 100000
            
            # Plain number
            match = re.search(r'([\d.]+)', val)
            if match:
                return float(match.group(1))
        
        return None


# Singleton instance
_ingestion_service = None

def get_ingestion_service() -> ProductionIngestionService:
    """Get singleton instance."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = ProductionIngestionService()
    return _ingestion_service
