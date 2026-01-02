"""
Seed Sample Data for Valora Platform
Loads sample localities, properties, and market data for testing.

Usage:
    python scripts/seed_data.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load environment variables
load_dotenv()

def seed_localities(conn):
    """Seed sample Bangalore localities"""
    localities_data = [
        ('Whitefield', 'bangalore', 'East', '560066', 12.9698, 77.7499, 'Tech hub with IT parks'),
        ('Koramangala', 'bangalore', 'South', '560034', 12.9352, 77.6245, 'Startup hub and commercial center'),
        ('Indiranagar', 'bangalore', 'East', '560038', 12.9716, 77.6412, 'Premium residential area'),
        ('HSR Layout', 'bangalore', 'South', '560102', 12.9082, 77.6476, 'Residential with good infrastructure'),
        ('Sarjapur Road', 'bangalore', 'South', '560035', 12.9010, 77.6874, 'Emerging IT corridor'),
        ('Electronic City', 'bangalore', 'South', '560100', 12.8399, 77.6770, 'Major IT hub'),
        ('Marathahalli', 'bangalore', 'East', '560037', 12.9591, 77.7012, 'Residential and commercial'),
        ('Jayanagar', 'bangalore', 'South', '560041', 12.9250, 77.5838, 'Established residential area'),
        ('Bannerghatta Road', 'bangalore', 'South', '560076', 12.8996, 77.5969, 'Growing residential area'),
        ('Yelahanka', 'bangalore', 'North', '560064', 13.1007, 77.5963, 'Near airport, rapid growth'),
        ('Bellandur', 'bangalore', 'South', '560103', 12.9266, 77.6784, 'IT offices and residential'),
        ('Hebbal', 'bangalore', 'North', '560024', 13.0358, 77.5970, 'Commercial and residential mix'),
    ]
    
    print("🏙️  Seeding Localities...")
    count = 0
    for name, city, zone, pincode, lat, lng, desc in localities_data:
        try:
            conn.execute(text("""
                INSERT INTO localities (name, city, zone, pincode, center_point)
                VALUES (:name, :city, :zone, :pincode, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                ON CONFLICT (name, city) DO NOTHING
            """), {'name': name, 'city': city, 'zone': zone, 'pincode': pincode, 'lat': lat, 'lng': lng})
            conn.commit()
            count += 1
        except Exception as e:
            print(f"  ⚠️  {name}: {str(e)[:50]}")
    
    print(f"  ✅ Seeded {count} localities")

def seed_properties(conn):
    """Seed sample properties"""
    print("\n🏠 Seeding Sample Properties...")
    
    property_types = ['apartment', 'house', 'villa', 'plot']
    localities = ['Whitefield', 'Koramangala', 'Indiranagar', 'HSR Layout', 'Bellandur']
    
    count = 0
    for i in range(50):  # Create 50 sample properties
        locality = random.choice(localities)
        prop_type = random.choice(property_types)
        
        # Generate realistic property data
        bedrooms = random.choice([1, 2, 2, 3, 3, 3, 4]) if prop_type == 'apartment' else random.choice([2, 3, 4, 5])
        area_sqft = bedrooms * random.randint(400, 600)
        price_per_sqft = random.randint(4000, 8000) if locality in ['Koramangala', 'Indiranagar'] else random.randint(3000, 6000)
        price = area_sqft * price_per_sqft
        
        try:
            conn.execute(text("""
                INSERT INTO properties (
                    listing_id, source, city, locality, property_type,
                    bedrooms, bathrooms, area_sqft, price, price_per_sqft,
                    listing_type, listing_date, furnishing
                ) VALUES (
                    :listing_id, 'seed', 'bangalore', :locality, :prop_type,
                    :bedrooms, :bathrooms, :area_sqft, :price, :price_per_sqft,
                    'sale', :listing_date, :furnishing
                )
            """), {
                'listing_id': f'SEED_{i+1:04d}',
                'locality': locality,
                'prop_type': prop_type,
                'bedrooms': bedrooms,
                'bathrooms': bedrooms,
                'area_sqft': area_sqft,
                'price': price,
                'price_per_sqft': price_per_sqft,
                'listing_date': datetime.now() - timedelta(days=random.randint(1, 90)),
                'furnishing': random.choice(['furnished', 'semi-furnished', 'unfurnished'])
            })
            conn.commit()
            count += 1
        except Exception as e:
            print(f"  ⚠️  Property {i+1}: {str(e)[:50]}")
    
    print(f"  ✅ Seeded {count} properties")

def seed_locality_state(conn):
    """Seed locality state data"""
    print("\n📊 Seeding Locality State Data...")
    
    localities = ['Whitefield', 'Koramangala', 'Indiranagar', 'HSR Layout']
    
    count = 0
    for locality_name in localities:
        try:
            # Get locality_id
            result = conn.execute(text("""
                SELECT id FROM localities WHERE name = :name AND city = 'bangalore'
            """), {'name': locality_name})
            
            locality_id = result.fetchone()
            if not locality_id:
                continue
            
            locality_id = locality_id[0]
            
            # Insert state data
            conn.execute(text("""
                INSERT INTO locality_state (
                    locality_id, avg_price_sqft, median_price,
                    price_change_1m, price_change_3m, price_change_6m,
                    active_listings, absorption_rate, days_on_market_avg,
                    growth_phase, risk_index_overall,
                    price_forecast_6m, price_forecast_1y
                ) VALUES (
                    :locality_id, :avg_price, :median_price,
                    :change_1m, :change_3m, :change_6m,
                    :active, :absorption, :days_on_market,
                    :growth, :risk,
                    :forecast_6m, :forecast_1y
                )
                ON CONFLICT (locality_id) DO NOTHING
            """), {
                'locality_id': locality_id,
                'avg_price': random.randint(4500, 7500),
                'median_price': random.randint(60000000, 120000000),
                'change_1m': round(random.uniform(-2, 5), 2),
                'change_3m': round(random.uniform(0, 8), 2),
                'change_6m': round(random.uniform(2, 12), 2),
                'active': random.randint(50, 300),
                'absorption': round(random.uniform(0.3, 0.9), 2),
                'days_on_market': random.randint(30, 90),
                'growth': random.choice(['emerging', 'accelerating', 'mature']),
                'risk': round(random.uniform(0.2, 0.6), 3),
                'forecast_6m': random.randint(65000000, 130000000),
                'forecast_1y': random.randint(70000000, 140000000)
            })
            conn.commit()
            count += 1
        except Exception as e:
            print(f"  ⚠️  {locality_name}: {str(e)[:50]}")
    
    print(f"  ✅ Seeded {count} locality states")

def main():
    """Main seeding function"""
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url or '[PROJECT-REF]' in db_url:
        print("❌ ERROR: Please configure DATABASE_URL in .env first")
        return False
    
    print("🌱 Seeding Sample Data for Valora Platform")
    print("=" * 60)
    
    try:
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            seed_localities(conn)
            seed_properties(conn)
            seed_locality_state(conn)
        
        print("\n" + "=" * 60)
        print("✅ Sample Data Seeding Complete!")
        print("=" * 60)
        print("\n📊 You can now:")
        print("1. View data in Supabase Dashboard → Table Editor")
        print("2. Start the application and test features")
        print("3. Use Admin Dashboard → Data Layer to monitor")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
