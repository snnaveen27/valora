"""
Ingest historical price data from CSV files into the database.
Supports multiple CSV formats from Kaggle and other sources.

Expected CSV formats:
1. Kaggle format: area_type,availability,location,size,society,total_sqft,bath,balcony,price
2. Custom format: property_id,date,price,locality,area_sqft,bedrooms,property_type
"""
import csv
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import re

def ensure_price_history_table(cursor):
    """Create price_history table if not exists."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT UNIQUE,
            property_id TEXT,
            price REAL,
            price_per_sqft REAL,
            locality TEXT,
            area_sqft REAL,
            bedrooms INTEGER,
            bathrooms INTEGER,
            property_type TEXT,
            listing_type TEXT,
            record_date DATE,
            source TEXT,
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def parse_size(size_str):
    """Parse bedrooms from size string like '2 BHK' or '3 Bedroom'."""
    if not size_str:
        return None
    match = re.search(r'(\d+)', str(size_str))
    return int(match.group(1)) if match else None

def parse_sqft(sqft_str):
    """Parse square feet from string, handling ranges like '1200 - 1500'."""
    if not sqft_str:
        return None
    try:
        # Handle range like "1200 - 1500"
        if '-' in str(sqft_str):
            parts = str(sqft_str).split('-')
            return (float(parts[0].strip()) + float(parts[1].strip())) / 2
        return float(str(sqft_str).replace(',', '').strip())
    except:
        return None

def parse_price(price_str):
    """Parse price, handling lakhs/crores notation."""
    if not price_str:
        return None
    try:
        price_str = str(price_str).lower().replace(',', '').strip()
        
        # Handle crores
        if 'cr' in price_str or 'crore' in price_str:
            num = float(re.search(r'[\d.]+', price_str).group())
            return num * 10000000
        
        # Handle lakhs
        if 'lakh' in price_str or 'lac' in price_str:
            num = float(re.search(r'[\d.]+', price_str).group())
            return num * 100000
        
        return float(price_str)
    except:
        return None

def ingest_kaggle_format(cursor, csv_path):
    """Ingest Kaggle Bangalore house price data format."""
    print(f"  Processing Kaggle format: {csv_path.name}")
    
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"  Found {len(rows):,} records")
    
    inserted = 0
    for i, row in enumerate(rows):
        record_id = f"kaggle_{csv_path.stem}_{i}"
        
        locality = row.get('location', '')
        size = parse_size(row.get('size', ''))
        sqft = parse_sqft(row.get('total_sqft', ''))
        price = parse_price(row.get('price', ''))
        bath = row.get('bath', '')
        area_type = row.get('area_type', '')
        
        # Calculate price per sqft
        price_per_sqft = None
        if price and sqft and sqft > 0:
            price_per_sqft = price / sqft
        
        # Parse bathrooms
        bathrooms = None
        if bath:
            try:
                bathrooms = int(float(bath))
            except:
                pass
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO price_history 
                (record_id, price, price_per_sqft, locality, area_sqft, 
                 bedrooms, bathrooms, property_type, source, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record_id,
                price,
                price_per_sqft,
                locality,
                sqft,
                size,
                bathrooms,
                area_type,
                'kaggle',
                json.dumps(row)
            ))
            if cursor.rowcount > 0:
                inserted += 1
        except Exception as e:
            pass
    
    return inserted

def ingest_custom_format(cursor, csv_path):
    """Ingest custom CSV format with date field."""
    print(f"  Processing custom format: {csv_path.name}")
    
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"  Found {len(rows):,} records")
    
    inserted = 0
    for i, row in enumerate(rows):
        record_id = f"custom_{csv_path.stem}_{i}"
        
        # Try different field names
        price = parse_price(row.get('price') or row.get('expected_price') or row.get('amount'))
        sqft = parse_sqft(row.get('area_sqft') or row.get('area') or row.get('carpet_area') or row.get('super_area'))
        locality = row.get('locality') or row.get('location') or row.get('area_name')
        bedrooms = parse_size(row.get('bedrooms') or row.get('bhk') or row.get('size'))
        bathrooms = row.get('bathrooms') or row.get('bath')
        prop_type = row.get('property_type') or row.get('type')
        date_str = row.get('date') or row.get('listing_date') or row.get('posted_date')
        
        # Parse date
        record_date = None
        if date_str:
            for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%Y/%m/%d']:
                try:
                    record_date = datetime.strptime(date_str, fmt).date()
                    break
                except:
                    continue
        
        # Calculate price per sqft
        price_per_sqft = None
        if price and sqft and sqft > 0:
            price_per_sqft = price / sqft
        
        # Parse bathrooms
        if bathrooms:
            try:
                bathrooms = int(float(bathrooms))
            except:
                bathrooms = None
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO price_history 
                (record_id, price, price_per_sqft, locality, area_sqft, 
                 bedrooms, bathrooms, property_type, record_date, source, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record_id,
                price,
                price_per_sqft,
                locality,
                sqft,
                bedrooms,
                bathrooms,
                prop_type,
                record_date,
                'custom_csv',
                json.dumps(row)
            ))
            if cursor.rowcount > 0:
                inserted += 1
        except Exception as e:
            pass
    
    return inserted

def main():
    project_root = Path(__file__).parent.parent
    db_path = project_root / 'storage' / 'valora.db'
    
    # Look for CSV files in multiple locations
    search_dirs = [
        project_root / 'storage' / 'downloads',
        project_root / 'storage' / 'price_history',
        project_root / 'data' / 'downloads',
        project_root / 'downloads',
    ]
    
    print("=" * 70)
    print("PRICE HISTORY INGESTION")
    print("=" * 70)
    print(f"Database: {db_path}")
    
    # Find CSV files
    csv_files = []
    for search_dir in search_dirs:
        if search_dir.exists():
            csv_files.extend(search_dir.glob('*.csv'))
    
    if not csv_files:
        print("\n❌ No CSV files found!")
        print("\nPlace your price history CSV files in one of these folders:")
        for d in search_dirs:
            print(f"  - {d}")
        print("\nSupported formats:")
        print("  1. Kaggle Bangalore house price data")
        print("  2. Custom CSV with columns: price, locality, area_sqft, bedrooms, date")
        print("\nDownload from:")
        print("  - https://www.kaggle.com/datasets/amitabhajoy/bengaluru-house-price-data")
        return
    
    print(f"\nFound {len(csv_files)} CSV file(s)")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    ensure_price_history_table(cursor)
    
    # Check existing count
    cursor.execute("SELECT COUNT(*) FROM price_history")
    existing = cursor.fetchone()[0]
    print(f"Existing records: {existing:,}")
    
    total_inserted = 0
    
    for csv_file in csv_files:
        print(f"\n[Processing] {csv_file.name}")
        
        # Detect format by checking headers
        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().lower()
        
        if 'total_sqft' in first_line and 'availability' in first_line:
            inserted = ingest_kaggle_format(cursor, csv_file)
        else:
            inserted = ingest_custom_format(cursor, csv_file)
        
        conn.commit()
        total_inserted += inserted
        print(f"  ✓ Inserted {inserted:,} records")
    
    # Final count
    cursor.execute("SELECT COUNT(*) FROM price_history")
    final = cursor.fetchone()[0]
    
    print(f"\n{'='*70}")
    print(f"✅ COMPLETE")
    print(f"   Total inserted: {total_inserted:,}")
    print(f"   Total in DB: {final:,}")
    print(f"{'='*70}")
    
    conn.close()

if __name__ == '__main__':
    main()
