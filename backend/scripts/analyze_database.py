"""
Database Analysis Script for Valora
Analyzes existing data to identify opportunities for feature improvements.
"""

import sqlite3
import json
from pathlib import Path

def analyze_database():
    db_path = Path(__file__).parent.parent / 'storage' / 'valora.db'
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 60)
    print("VALORA DATABASE ANALYSIS")
    print("=" * 60)
    
    # 1. Table counts
    print("\n## TABLE COUNTS")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    table_counts = {}
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        table_counts[table] = count
        print(f"  {table}: {count:,} rows")
    
    # 2. Properties analysis
    print("\n## PROPERTIES TABLE ANALYSIS")
    if table_counts.get('properties', 0) > 0:
        # Column usage
        cursor.execute("PRAGMA table_info(properties)")
        columns = [row[1] for row in cursor.fetchall()]
        
        print(f"  Total columns: {len(columns)}")
        
        # Check which columns have data
        print("\n  ### Column Data Coverage:")
        for col in columns:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM properties WHERE {col} IS NOT NULL AND {col} != ''")
                filled = cursor.fetchone()[0]
                total = table_counts['properties']
                pct = (filled / total * 100) if total > 0 else 0
                if pct > 0:
                    print(f"    {col}: {filled:,} ({pct:.0f}%)")
            except:
                pass
        
        # Sample data
        print("\n  ### Sample Property Data:")
        cursor.execute("SELECT property_type, bedrooms, price, locality, amenities, images FROM properties LIMIT 3")
        for row in cursor.fetchall():
            print(f"    Type: {row[0]}, BHK: {row[1]}, Price: {row[2]}, Area: {row[3]}")
            if row[4]:
                try:
                    amenities = json.loads(row[4]) if row[4] else []
                    print(f"      Amenities: {len(amenities) if isinstance(amenities, list) else 'JSON'}")
                except:
                    print(f"      Amenities: {row[4][:50]}...")
            if row[5]:
                try:
                    images = json.loads(row[5]) if row[5] else []
                    print(f"      Images: {len(images) if isinstance(images, list) else 'has data'}")
                except:
                    print(f"      Images: has data")
    
    # 3. POIs analysis
    print("\n## POIS TABLE ANALYSIS")
    if table_counts.get('pois', 0) > 0:
        cursor.execute("SELECT category, COUNT(*) as cnt FROM pois GROUP BY category ORDER BY cnt DESC LIMIT 15")
        print("  ### Categories:")
        for row in cursor.fetchall():
            print(f"    {row[0]}: {row[1]:,}")
        
        cursor.execute("SELECT subcategory, COUNT(*) as cnt FROM pois WHERE subcategory IS NOT NULL GROUP BY subcategory ORDER BY cnt DESC LIMIT 10")
        print("\n  ### Subcategories (top 10):")
        for row in cursor.fetchall():
            print(f"    {row[0]}: {row[1]:,}")
    
    # 4. Buildings analysis
    print("\n## BUILDINGS TABLE ANALYSIS")
    if table_counts.get('buildings', 0) > 0:
        cursor.execute("SELECT building_type, COUNT(*) as cnt FROM buildings GROUP BY building_type ORDER BY cnt DESC LIMIT 10")
        print("  ### Building Types:")
        for row in cursor.fetchall():
            print(f"    {row[0]}: {row[1]:,}")
        
        cursor.execute("SELECT COUNT(*) FROM buildings WHERE height IS NOT NULL AND height > 0")
        with_height = cursor.fetchone()[0]
        print(f"\n  Buildings with height data: {with_height:,} ({with_height/table_counts['buildings']*100:.1f}%)")
        
        cursor.execute("SELECT AVG(height), MAX(height), AVG(levels) FROM buildings WHERE height > 0")
        row = cursor.fetchone()
        print(f"  Avg height: {row[0]:.1f}m, Max: {row[1]:.1f}m, Avg levels: {row[2]:.1f}")
    
    # 5. Transport analysis
    print("\n## TRANSPORT_STOPS TABLE ANALYSIS")
    if table_counts.get('transport_stops', 0) > 0:
        cursor.execute("SELECT transport_type, COUNT(*) as cnt FROM transport_stops GROUP BY transport_type ORDER BY cnt DESC")
        print("  ### Transport Types:")
        for row in cursor.fetchall():
            print(f"    {row[0]}: {row[1]:,}")
    
    # 6. Places analysis
    print("\n## PLACES TABLE ANALYSIS")
    if table_counts.get('places', 0) > 0:
        cursor.execute("SELECT place_type, COUNT(*) as cnt FROM places GROUP BY place_type ORDER BY cnt DESC LIMIT 10")
        print("  ### Place Types:")
        for row in cursor.fetchall():
            print(f"    {row[0]}: {row[1]:,}")
        
        cursor.execute("SELECT COUNT(*) FROM places WHERE avg_price_per_sqft IS NOT NULL")
        with_price = cursor.fetchone()[0]
        print(f"\n  Places with price data: {with_price:,}")
    
    # 7. Price history
    print("\n## PRICE_HISTORY TABLE ANALYSIS")
    if table_counts.get('price_history', 0) > 0:
        cursor.execute("SELECT COUNT(DISTINCT property_id) FROM price_history")
        unique_props = cursor.fetchone()[0]
        print(f"  Properties with history: {unique_props:,}")
        
        cursor.execute("SELECT MIN(recorded_at), MAX(recorded_at) FROM price_history")
        row = cursor.fetchone()
        print(f"  Date range: {row[0]} to {row[1]}")
    
    # 8. Property analytics
    print("\n## PROPERTY_ANALYTICS TABLE ANALYSIS")
    if table_counts.get('property_analytics', 0) > 0:
        cursor.execute("SELECT COUNT(*) FROM property_analytics WHERE investment_score IS NOT NULL")
        with_score = cursor.fetchone()[0]
        print(f"  Properties with investment score: {with_score:,}")
    
    # 9. Roads analysis
    print("\n## ROADS TABLE ANALYSIS")
    if table_counts.get('roads', 0) > 0:
        cursor.execute("SELECT road_type, COUNT(*) as cnt FROM roads GROUP BY road_type ORDER BY cnt DESC LIMIT 10")
        print("  ### Road Types:")
        for row in cursor.fetchall():
            print(f"    {row[0]}: {row[1]:,}")
    
    # 10. Check for underutilized data
    print("\n" + "=" * 60)
    print("UNDERUTILIZED DATA OPPORTUNITIES")
    print("=" * 60)
    
    opportunities = []
    
    # Check amenities in properties
    cursor.execute("SELECT COUNT(*) FROM properties WHERE amenities IS NOT NULL AND amenities != '[]'")
    amenities_count = cursor.fetchone()[0]
    if amenities_count > 0:
        opportunities.append(f"- {amenities_count:,} properties have AMENITIES data (can enhance search/filters)")
    
    # Check images
    cursor.execute("SELECT COUNT(*) FROM properties WHERE images IS NOT NULL AND images != '[]'")
    images_count = cursor.fetchone()[0]
    if images_count > 0:
        opportunities.append(f"- {images_count:,} properties have IMAGE URLs (ready for visual AI)")
    
    # Check landmarks
    cursor.execute("SELECT COUNT(*) FROM properties WHERE landmarks IS NOT NULL")
    landmarks_count = cursor.fetchone()[0]
    if landmarks_count > 0:
        opportunities.append(f"- {landmarks_count:,} properties have LANDMARKS data (enhance location context)")
    
    # Check nearby_places
    cursor.execute("SELECT COUNT(*) FROM properties WHERE nearby_places IS NOT NULL")
    nearby_count = cursor.fetchone()[0]
    if nearby_count > 0:
        opportunities.append(f"- {nearby_count:,} properties have NEARBY_PLACES data (already scraped!)")
    
    # Check raw_data
    cursor.execute("SELECT COUNT(*) FROM properties WHERE raw_data IS NOT NULL")
    raw_count = cursor.fetchone()[0]
    if raw_count > 0:
        opportunities.append(f"- {raw_count:,} properties have RAW_DATA (may contain unused fields)")
    
    # Check POI ratings
    cursor.execute("SELECT COUNT(*) FROM pois WHERE rating IS NOT NULL AND rating > 0")
    rated_pois = cursor.fetchone()[0]
    if rated_pois > 0:
        opportunities.append(f"- {rated_pois:,} POIs have RATINGS (can use for quality scoring)")
    
    # Check POI reviews
    cursor.execute("SELECT COUNT(*) FROM pois WHERE reviews_count IS NOT NULL AND reviews_count > 0")
    reviewed_pois = cursor.fetchone()[0]
    if reviewed_pois > 0:
        opportunities.append(f"- {reviewed_pois:,} POIs have REVIEW COUNTS (popularity indicator)")
    
    # Check building heights
    cursor.execute("SELECT COUNT(*) FROM buildings WHERE height IS NOT NULL AND height > 0")
    height_buildings = cursor.fetchone()[0]
    if height_buildings > 0:
        opportunities.append(f"- {height_buildings:,} buildings have HEIGHT data (3D analysis ready)")
    
    # Check price history
    if table_counts.get('price_history', 0) > 0:
        opportunities.append(f"- {table_counts['price_history']:,} price history records (trend analysis)")
    
    for opp in opportunities:
        print(opp)
    
    conn.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    analyze_database()
