"""
Price Tracking System - Monitor property price changes over time.
Creates snapshots of current property prices and tracks changes.
"""
import sqlite3
from pathlib import Path
from datetime import datetime, date

def get_db_connection():
    db_path = Path(__file__).parent.parent / 'storage' / 'valora.db'
    return sqlite3.connect(str(db_path))

def ensure_price_history_table(cursor):
    """Create price_history table for tracking price changes."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id TEXT NOT NULL,
            price REAL,
            price_per_sqft REAL,
            locality TEXT,
            area_sqft REAL,
            bedrooms INTEGER,
            property_type TEXT,
            snapshot_date DATE NOT NULL,
            source TEXT DEFAULT 'price_tracker',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(property_id, snapshot_date)
        )
    """)
    
    # Create index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_history_property 
        ON price_history(property_id, snapshot_date DESC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_history_date 
        ON price_history(snapshot_date DESC)
    """)

def snapshot_current_prices(cursor, snapshot_date=None):
    """Take a snapshot of current property prices."""
    if snapshot_date is None:
        snapshot_date = date.today()
    
    # Get all properties with prices
    cursor.execute("""
        SELECT property_id, price, total_area_sqft, locality, bedrooms, property_type
        FROM properties
        WHERE price IS NOT NULL AND price > 0
    """)
    
    properties = cursor.fetchall()
    print(f"  Found {len(properties):,} properties with prices")
    
    inserted = 0
    updated = 0
    
    for prop in properties:
        property_id, price, area, locality, bedrooms, prop_type = prop
        
        # Calculate price per sqft
        price_per_sqft = None
        if area and area > 0:
            price_per_sqft = price / area
        
        try:
            cursor.execute("""
                INSERT INTO price_history 
                (property_id, price, price_per_sqft, locality, area_sqft, 
                 bedrooms, property_type, snapshot_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(property_id, snapshot_date) 
                DO UPDATE SET 
                    price = excluded.price,
                    price_per_sqft = excluded.price_per_sqft
            """, (
                property_id,
                price,
                price_per_sqft,
                locality,
                area,
                bedrooms,
                prop_type,
                snapshot_date
            ))
            
            if cursor.rowcount > 0:
                # Check if it was an insert or update
                cursor.execute("""
                    SELECT COUNT(*) FROM price_history 
                    WHERE property_id = ? AND snapshot_date = ?
                """, (property_id, snapshot_date))
                
                if cursor.fetchone()[0] == 1:
                    inserted += 1
                else:
                    updated += 1
        except Exception as e:
            pass
    
    return inserted, updated, len(properties)

def analyze_price_changes(cursor, days_back=30):
    """Analyze price changes over the specified period."""
    cursor.execute("""
        WITH latest_prices AS (
            SELECT 
                property_id,
                price,
                snapshot_date,
                ROW_NUMBER() OVER (PARTITION BY property_id ORDER BY snapshot_date DESC) as rn
            FROM price_history
            WHERE snapshot_date >= date('now', '-' || ? || ' days')
        ),
        oldest_prices AS (
            SELECT 
                property_id,
                price,
                snapshot_date,
                ROW_NUMBER() OVER (PARTITION BY property_id ORDER BY snapshot_date ASC) as rn
            FROM price_history
            WHERE snapshot_date >= date('now', '-' || ? || ' days')
        )
        SELECT 
            l.property_id,
            o.price as old_price,
            l.price as new_price,
            (l.price - o.price) as price_change,
            ROUND(((l.price - o.price) * 100.0 / o.price), 2) as percent_change,
            o.snapshot_date as first_date,
            l.snapshot_date as last_date
        FROM latest_prices l
        JOIN oldest_prices o ON l.property_id = o.property_id
        WHERE l.rn = 1 AND o.rn = 1
        AND l.snapshot_date != o.snapshot_date
        AND o.price > 0
        ORDER BY ABS(l.price - o.price) DESC
        LIMIT 20
    """, (days_back, days_back))
    
    return cursor.fetchall()

def get_price_statistics(cursor):
    """Get overall price statistics."""
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT property_id) as properties_tracked,
            COUNT(DISTINCT snapshot_date) as snapshots_taken,
            MIN(snapshot_date) as first_snapshot,
            MAX(snapshot_date) as last_snapshot,
            COUNT(*) as total_records
        FROM price_history
    """)
    
    return cursor.fetchone()

def main():
    print("=" * 70)
    print("PROPERTY PRICE TRACKING SYSTEM")
    print("=" * 70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure table exists
    print("\n[1/4] Setting up price tracking table...")
    ensure_price_history_table(cursor)
    conn.commit()
    print("  ✓ Table ready")
    
    # Get current statistics
    print("\n[2/4] Current tracking statistics...")
    stats = get_price_statistics(cursor)
    if stats:
        props, snapshots, first, last, total = stats
        print(f"  Properties tracked: {props:,}")
        print(f"  Snapshots taken: {snapshots:,}")
        print(f"  First snapshot: {first or 'None'}")
        print(f"  Last snapshot: {last or 'None'}")
        print(f"  Total records: {total:,}")
    
    # Take new snapshot
    print("\n[3/4] Taking price snapshot...")
    today = date.today()
    inserted, updated, total_props = snapshot_current_prices(cursor, today)
    conn.commit()
    print(f"  ✓ Snapshot complete for {today}")
    print(f"    New records: {inserted:,}")
    print(f"    Updated: {updated:,}")
    print(f"    Total properties: {total_props:,}")
    
    # Analyze recent changes
    print("\n[4/4] Analyzing price changes (last 30 days)...")
    changes = analyze_price_changes(cursor, days_back=30)
    
    if changes:
        print(f"\n  Top {len(changes)} price changes:")
        print(f"  {'Property ID':<20} {'Old Price':>12} {'New Price':>12} {'Change':>12} {'%':>8}")
        print("  " + "-" * 68)
        
        for change in changes[:10]:  # Show top 10
            prop_id, old, new, diff, pct, first_date, last_date = change
            print(f"  {prop_id:<20} ₹{old:>11,.0f} ₹{new:>11,.0f} ₹{diff:>11,.0f} {pct:>7.1f}%")
    else:
        print("  No price changes detected (need multiple snapshots)")
    
    print(f"\n{'='*70}")
    print("✅ PRICE TRACKING COMPLETE")
    print(f"{'='*70}")
    
    print("\nSchedule this script to run daily:")
    print("  Windows Task Scheduler:")
    print("    - Action: python scripts/track_price_changes.py")
    print("    - Trigger: Daily at midnight")
    print("\n  Linux cron:")
    print("    - 0 0 * * * cd /path/to/project && python scripts/track_price_changes.py")
    
    conn.close()

if __name__ == '__main__':
    main()
