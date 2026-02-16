"""
Data Enhancer for Valora AI
Extracts and indexes underutilized data from the database.

Features:
1. Extract amenities from property raw_data
2. Populate property_analytics cache
3. Fix POI categories
4. Fix transport types
5. Link gov_data to areas
6. Compute place statistics
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


class DataEnhancer:
    """Enhances database with extracted and computed data."""
    
    # Amenity mapping (raw key -> display name)
    AMENITY_MAP = {
        'LIFT': 'Lift/Elevator',
        'GYM': 'Gymnasium',
        'POOL': 'Swimming Pool',
        'SECURITY': 'Security',
        'INTERCOM': 'Intercom',
        'PARK': 'Park/Garden',
        'CLUB': 'Club House',
        'CPA': 'Covered Parking',
        'GP': 'Guest Parking',
        'FS': 'Fire Safety',
        'STP': 'Sewage Treatment',
        'RWH': 'Rain Water Harvesting',
        'VP': 'Visitor Parking',
        'AC': 'Air Conditioning',
        'INTERNET': 'Internet/WiFi',
        'SERVANT': 'Servant Room',
        'SC': 'Sports Court',
        'HK': 'House Keeping',
        'PB': 'Power Backup',
    }
    
    # POI category mapping based on name patterns
    POI_CATEGORY_PATTERNS = {
        'school': ['school', 'academy', 'vidyalaya', 'public school', 'high school', 'primary'],
        'college': ['college', 'university', 'institute', 'iit', 'iim', 'iisc'],
        'hospital': ['hospital', 'medical', 'clinic', 'health centre', 'nursing home'],
        'restaurant': ['restaurant', 'cafe', 'hotel', 'dhaba', 'food', 'kitchen', 'biryani'],
        'bank': ['bank', 'atm', 'sbi', 'hdfc', 'icici', 'axis', 'canara'],
        'mall': ['mall', 'shopping', 'forum', 'phoenix', 'orion'],
        'supermarket': ['supermarket', 'grocery', 'bigbasket', 'more', 'reliance fresh', 'dmart'],
        'temple': ['temple', 'mandir', 'kovil', 'devasthana'],
        'church': ['church', 'cathedral', 'chapel'],
        'mosque': ['mosque', 'masjid', 'dargah'],
        'park': ['park', 'garden', 'lake', 'playground'],
        'gym': ['gym', 'fitness', 'workout', 'cult'],
        'petrol': ['petrol', 'fuel', 'gas station', 'hp', 'indian oil', 'bharat petroleum'],
        'pharmacy': ['pharmacy', 'medical store', 'chemist', 'apollo', 'medplus'],
        'police': ['police', 'station'],
        'post_office': ['post office', 'postal'],
        'it_park': ['tech park', 'it park', 'software', 'infosys', 'wipro', 'tcs'],
    }
    
    # Transport type patterns
    TRANSPORT_TYPE_PATTERNS = {
        'metro': ['metro', 'namma metro', 'purple line', 'green line'],
        'bus': ['bus', 'bmtc', 'volvo', 'bus stop', 'bus station'],
        'railway': ['railway', 'train', 'station', 'junction'],
        'airport': ['airport', 'kia', 'kempegowda'],
    }
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'storage' / 'valora.db'
        self.db_path = str(db_path)
        self.conn = None
        self.stats = {
            'amenities_extracted': 0,
            'analytics_computed': 0,
            'pois_categorized': 0,
            'transport_typed': 0,
            'places_updated': 0,
        }
    
    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def run_all_enhancements(self) -> Dict[str, int]:
        """Run all data enhancement tasks."""
        self.connect()
        try:
            print("[DataEnhancer] Starting all enhancements...")
            
            # 1. Extract amenities
            print("[DataEnhancer] Extracting amenities...")
            self.extract_amenities()
            
            # 2. Fix POI categories
            print("[DataEnhancer] Categorizing POIs...")
            self.categorize_pois()
            
            # 3. Fix transport types
            print("[DataEnhancer] Typing transport stops...")
            self.type_transport_stops()
            
            # 4. Compute place statistics
            print("[DataEnhancer] Computing place stats...")
            self.compute_place_stats()
            
            # 5. Populate property analytics
            print("[DataEnhancer] Computing property analytics...")
            self.compute_property_analytics()
            
            self.conn.commit()
            print(f"[DataEnhancer] Complete! Stats: {self.stats}")
            return self.stats
        finally:
            self.close()
    
    def extract_amenities(self):
        """Extract amenities from raw_data to amenities column."""
        cursor = self.conn.cursor()
        
        # Get properties with raw_data containing amenities
        cursor.execute("""
            SELECT property_id, raw_data 
            FROM properties 
            WHERE raw_data LIKE '%amenities%'
            AND (amenities IS NULL OR amenities = '' OR amenities = '[]')
        """)
        
        batch = []
        for row in cursor.fetchall():
            try:
                raw = json.loads(row['raw_data'])
                amenities_raw = raw.get('amenities', {})
                
                if isinstance(amenities_raw, dict):
                    # Convert to list of available amenities
                    amenities_list = []
                    for key, value in amenities_raw.items():
                        if value is True:
                            display_name = self.AMENITY_MAP.get(key, key)
                            amenities_list.append(display_name)
                    
                    if amenities_list:
                        batch.append((json.dumps(amenities_list), row['property_id']))
                        self.stats['amenities_extracted'] += 1
                
                elif isinstance(amenities_raw, list):
                    batch.append((json.dumps(amenities_raw), row['property_id']))
                    self.stats['amenities_extracted'] += 1
                    
            except (json.JSONDecodeError, TypeError):
                continue
            
            # Batch update
            if len(batch) >= 500:
                cursor.executemany(
                    "UPDATE properties SET amenities = ? WHERE property_id = ?",
                    batch
                )
                batch = []
        
        # Final batch
        if batch:
            cursor.executemany(
                "UPDATE properties SET amenities = ? WHERE property_id = ?",
                batch
            )
    
    def categorize_pois(self):
        """Categorize POIs based on name patterns."""
        cursor = self.conn.cursor()
        
        # Get POIs with 'other' or NULL category
        cursor.execute("""
            SELECT id, name FROM pois 
            WHERE category IS NULL OR category = 'other' OR category = ''
        """)
        
        batch = []
        for row in cursor.fetchall():
            name_lower = row['name'].lower() if row['name'] else ''
            
            category = 'other'
            subcategory = None
            
            for cat, patterns in self.POI_CATEGORY_PATTERNS.items():
                for pattern in patterns:
                    if pattern in name_lower:
                        category = cat
                        subcategory = pattern
                        break
                if category != 'other':
                    break
            
            if category != 'other':
                batch.append((category, subcategory, row['id']))
                self.stats['pois_categorized'] += 1
            
            if len(batch) >= 500:
                cursor.executemany(
                    "UPDATE pois SET category = ?, subcategory = ? WHERE id = ?",
                    batch
                )
                batch = []
        
        if batch:
            cursor.executemany(
                "UPDATE pois SET category = ?, subcategory = ? WHERE id = ?",
                batch
            )
    
    def type_transport_stops(self):
        """Determine transport type based on name patterns."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT id, name FROM transport_stops 
            WHERE transport_type IS NULL OR transport_type = 'unknown' OR transport_type = ''
        """)
        
        batch = []
        for row in cursor.fetchall():
            name_lower = row['name'].lower() if row['name'] else ''
            
            transport_type = 'bus'  # Default to bus
            
            for t_type, patterns in self.TRANSPORT_TYPE_PATTERNS.items():
                for pattern in patterns:
                    if pattern in name_lower:
                        transport_type = t_type
                        break
                if transport_type != 'bus':
                    break
            
            batch.append((transport_type, row['id']))
            self.stats['transport_typed'] += 1
            
            if len(batch) >= 500:
                cursor.executemany(
                    "UPDATE transport_stops SET transport_type = ? WHERE id = ?",
                    batch
                )
                batch = []
        
        if batch:
            cursor.executemany(
                "UPDATE transport_stops SET transport_type = ? WHERE id = ?",
                batch
            )
    
    def compute_place_stats(self):
        """Compute property statistics for each place."""
        cursor = self.conn.cursor()
        
        # Get places
        cursor.execute("SELECT place_id, name FROM places")
        places = cursor.fetchall()
        
        for place in places:
            place_name = place['name']
            
            # Count properties in this place
            cursor.execute("""
                SELECT 
                    COUNT(*) as count,
                    AVG(price) as avg_price,
                    AVG(price_per_sqft) as avg_ppsf
                FROM properties 
                WHERE (locality LIKE ? OR area_name LIKE ?)
                AND price > 0
            """, (f"%{place_name}%", f"%{place_name}%"))
            
            stats = cursor.fetchone()
            if stats and stats['count'] > 0:
                cursor.execute("""
                    UPDATE places SET 
                        property_count = ?,
                        avg_price = ?,
                        avg_price_per_sqft = ?
                    WHERE place_id = ?
                """, (stats['count'], stats['avg_price'], stats['avg_ppsf'], place['place_id']))
                self.stats['places_updated'] += 1
    
    def compute_property_analytics(self):
        """Pre-compute analytics for properties with coordinates."""
        cursor = self.conn.cursor()
        
        # Get properties with coordinates that don't have analytics
        cursor.execute("""
            SELECT p.property_id, p.latitude, p.longitude
            FROM properties p
            LEFT JOIN property_analytics pa ON p.property_id = pa.property_id
            WHERE p.latitude IS NOT NULL 
            AND p.longitude IS NOT NULL
            AND pa.id IS NULL
            LIMIT 1000
        """)
        
        properties = cursor.fetchall()
        
        for prop in properties:
            lat, lng = prop['latitude'], prop['longitude']
            
            # Compute metro proximity
            cursor.execute("""
                SELECT MIN(
                    (latitude - ?) * (latitude - ?) * 111000 * 111000 +
                    (longitude - ?) * (longitude - ?) * 111000 * 111000 * 0.94
                ) as dist_sq
                FROM transport_stops
                WHERE transport_type = 'metro'
            """, (lat, lat, lng, lng))
            
            metro_result = cursor.fetchone()
            metro_dist = (metro_result['dist_sq'] ** 0.5) if metro_result and metro_result['dist_sq'] else 10000
            metro_score = max(0, 100 - (metro_dist / 50))  # 100 at 0m, 0 at 5km
            
            # Compute school proximity
            cursor.execute("""
                SELECT MIN(
                    (latitude - ?) * (latitude - ?) * 111000 * 111000 +
                    (longitude - ?) * (longitude - ?) * 111000 * 111000 * 0.94
                ) as dist_sq
                FROM pois
                WHERE category = 'school'
            """, (lat, lat, lng, lng))
            
            school_result = cursor.fetchone()
            school_dist = (school_result['dist_sq'] ** 0.5) if school_result and school_result['dist_sq'] else 5000
            school_score = max(0, 100 - (school_dist / 30))
            
            # Compute hospital proximity
            cursor.execute("""
                SELECT MIN(
                    (latitude - ?) * (latitude - ?) * 111000 * 111000 +
                    (longitude - ?) * (longitude - ?) * 111000 * 111000 * 0.94
                ) as dist_sq
                FROM pois
                WHERE category = 'hospital'
            """, (lat, lat, lng, lng))
            
            hospital_result = cursor.fetchone()
            hospital_dist = (hospital_result['dist_sq'] ** 0.5) if hospital_result and hospital_result['dist_sq'] else 8000
            hospital_score = max(0, 100 - (hospital_dist / 50))
            
            # Compute investment score (weighted average)
            investment_score = (metro_score * 0.4 + school_score * 0.3 + hospital_score * 0.3)
            
            # Insert analytics
            try:
                cursor.execute("""
                    INSERT INTO property_analytics (
                        property_id, metro_proximity_score, school_proximity_score,
                        hospital_proximity_score, nearest_metro_distance,
                        nearest_school_distance, nearest_hospital_distance,
                        investment_score, calculated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prop['property_id'],
                    min(100, metro_score),
                    min(100, school_score),
                    min(100, hospital_score),
                    metro_dist,
                    school_dist,
                    hospital_dist,
                    min(100, investment_score),
                    datetime.now().isoformat()
                ))
                self.stats['analytics_computed'] += 1
            except sqlite3.IntegrityError:
                pass  # Already exists
        
        return self.stats


def run_data_enhancement():
    """Run all data enhancements."""
    enhancer = DataEnhancer()
    return enhancer.run_all_enhancements()


if __name__ == "__main__":
    stats = run_data_enhancement()
    print(f"\nEnhancement complete: {stats}")
