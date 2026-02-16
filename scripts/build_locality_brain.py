"""
Valora AI - Locality Brain Builder
Aggregates data from raw tables into the locality_state store.
This is the "offline brain building" job that precomputes intelligence.

Run: python scripts/build_locality_brain.py
Schedule: Daily or weekly via cron
"""

import sqlite3
import json
import math
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple

# Database path
DB_PATH = Path(__file__).parent.parent / "storage" / "valora.db"

# Bangalore localities (wards/neighborhoods) - will be auto-detected from data
KNOWN_LOCALITIES = []


def get_db_connection(db_path: str = None) -> sqlite3.Connection:
    """Get database connection with row factory."""
    db = db_path or str(DB_PATH)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def discover_localities(conn: sqlite3.Connection) -> List[Dict]:
    """Discover localities from multiple sources (places, POIs, properties)."""
    cursor = conn.cursor()
    
    # First, get localities from places table (most accurate coordinates)
    cursor.execute("""
        SELECT 
            name,
            city_id,
            center_latitude as lat,
            center_longitude as lng,
            property_count
        FROM places
        WHERE center_latitude IS NOT NULL 
          AND center_longitude IS NOT NULL
          AND name IS NOT NULL
    """)
    
    places_data = {row['name'].lower(): {
        'name': row['name'],
        'city_id': row['city_id'] or 'BLR',
        'center_lat': row['lat'],
        'center_lng': row['lng'],
        'property_count': row['property_count'] or 0
    } for row in cursor.fetchall()}
    
    # Then get localities from properties (for coverage)
    cursor.execute("""
        SELECT 
            locality,
            city_id,
            COUNT(*) as property_count,
            AVG(latitude) as avg_lat,
            AVG(longitude) as avg_lng
        FROM properties
        WHERE locality IS NOT NULL AND locality != ''
        GROUP BY locality, city_id
        HAVING COUNT(*) >= 5
        ORDER BY property_count DESC
    """)
    
    localities = []
    for row in cursor.fetchall():
        name = row['locality']
        name_lower = name.lower()
        
        # Use places coordinates if available (more accurate), else use property avg
        if name_lower in places_data:
            places_info = places_data[name_lower]
            localities.append({
                'id': name_lower.replace(' ', '_').replace(',', ''),
                'name': name,
                'city_id': row['city_id'] or places_info['city_id'] or 'BLR',
                'property_count': row['property_count'],
                'center_lat': places_info['center_lat'],  # Use places coords
                'center_lng': places_info['center_lng'],
            })
        else:
            localities.append({
                'id': name_lower.replace(' ', '_').replace(',', ''),
                'name': name,
                'city_id': row['city_id'] or 'BLR',
                'property_count': row['property_count'],
                'center_lat': row['avg_lat'],
                'center_lng': row['avg_lng'],
            })
    
    print(f"Discovered {len(localities)} localities ({len(places_data)} with places coords)")
    return localities


def compute_market_metrics(conn: sqlite3.Connection, locality_name: str, city_id: str = 'BLR') -> Dict[str, Any]:
    """Compute market metrics for a locality."""
    cursor = conn.cursor()
    
    # Current market stats
    cursor.execute("""
        SELECT 
            AVG(price_per_sqft) as avg_price_sqft,
            COUNT(*) as active_listings,
            AVG(price) as avg_price
        FROM properties
        WHERE locality = ? AND (city_id = ? OR city_id IS NULL)
    """, (locality_name, city_id))
    
    row = cursor.fetchone()
    
    if not row or row['active_listings'] == 0:
        return {
            'avg_price_sqft': None,
            'median_price_sqft': None,
            'active_listings': 0,
            'demand_level': 'unknown',
            'supply_level': 'unknown',
        }
    
    # Compute median
    cursor.execute("""
        SELECT price_per_sqft
        FROM properties
        WHERE locality = ? AND price_per_sqft IS NOT NULL
        ORDER BY price_per_sqft
        LIMIT 1 OFFSET (
            SELECT COUNT(*) / 2 FROM properties 
            WHERE locality = ? AND price_per_sqft IS NOT NULL
        )
    """, (locality_name, locality_name))
    
    median_row = cursor.fetchone()
    median_price = median_row['price_per_sqft'] if median_row else row['avg_price_sqft']
    
    # Determine demand/supply levels based on listing count
    active = row['active_listings']
    if active > 100:
        supply_level = 'oversupply'
    elif active > 50:
        supply_level = 'balanced'
    else:
        supply_level = 'undersupply'
    
    # Demand based on price vs city average
    cursor.execute("SELECT AVG(price_per_sqft) as city_avg FROM properties WHERE city_id = ?", (city_id,))
    city_avg = cursor.fetchone()['city_avg'] or row['avg_price_sqft']
    
    if row['avg_price_sqft'] and city_avg:
        price_ratio = row['avg_price_sqft'] / city_avg
        if price_ratio > 1.3:
            demand_level = 'high'
        elif price_ratio > 0.9:
            demand_level = 'medium'
        else:
            demand_level = 'low'
    else:
        demand_level = 'medium'
    
    return {
        'avg_price_sqft': round(row['avg_price_sqft'], 2) if row['avg_price_sqft'] else None,
        'median_price_sqft': round(median_price, 2) if median_price else None,
        'active_listings': row['active_listings'],
        'demand_level': demand_level,
        'supply_level': supply_level,
    }


def compute_spatial_features(conn: sqlite3.Connection, lat: float, lng: float, radius_m: int = 1500) -> Dict[str, Any]:
    """Compute spatial features for a location."""
    # Handle None or invalid coordinates
    if lat is None or lng is None:
        return {
            'poi_count': 0,
            'transport_count': 0,
            'metro_count': 0,
            'bus_count': 0,
            'school_count': 0,
            'hospital_count': 0,
            'park_count': 0,
            'mall_count': 0,
            'accessibility_score': 30.0,
            'walkability_score': 30.0,
            'livability_score': 30.0,
        }
    
    cursor = conn.cursor()
    
    # Approximate degree to meters (at Bangalore latitude)
    deg_per_m = 1 / 111000
    radius_deg = radius_m * deg_per_m
    
    min_lat, max_lat = lat - radius_deg, lat + radius_deg
    min_lng, max_lng = lng - radius_deg, lng + radius_deg
    
    # Count POIs by type (using correct column names: latitude, longitude)
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN category = 'education' OR category LIKE '%school%' THEN 1 ELSE 0 END) as schools,
            SUM(CASE WHEN category = 'health' OR category LIKE '%hospital%' THEN 1 ELSE 0 END) as hospitals,
            SUM(CASE WHEN category = 'park' OR category = 'recreation' THEN 1 ELSE 0 END) as parks,
            SUM(CASE WHEN category = 'shopping' OR category LIKE '%mall%' THEN 1 ELSE 0 END) as malls
        FROM pois
        WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?
    """, (min_lat, max_lat, min_lng, max_lng))
    
    poi_row = cursor.fetchone()
    
    # Count transport (using correct column names: latitude, longitude, transport_type)
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN transport_type = 'metro' OR transport_type LIKE '%Metro%' THEN 1 ELSE 0 END) as metro,
            SUM(CASE WHEN transport_type = 'bus' OR transport_type LIKE '%Bus%' THEN 1 ELSE 0 END) as bus
        FROM transport_stops
        WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?
    """, (min_lat, max_lat, min_lng, max_lng))
    
    transport_row = cursor.fetchone()
    
    # Compute scores
    poi_count = poi_row['total'] or 0
    transport_count = transport_row['total'] or 0
    metro_count = transport_row['metro'] or 0
    
    # Accessibility score (0-100)
    accessibility = min(100, (metro_count * 20) + (transport_count * 5) + (poi_count * 0.5))
    
    # Walkability score (0-100)
    walkability = min(100, (poi_count * 2) + (transport_count * 10))
    
    # Livability score (0-100)
    schools = poi_row['schools'] or 0
    hospitals = poi_row['hospitals'] or 0
    parks = poi_row['parks'] or 0
    livability = min(100, (schools * 10) + (hospitals * 15) + (parks * 5) + (poi_count * 0.3))
    
    return {
        'poi_count': poi_count,
        'transport_count': transport_count,
        'metro_count': metro_count,
        'bus_count': transport_row['bus'] or 0,
        'school_count': schools,
        'hospital_count': hospitals,
        'park_count': parks,
        'mall_count': poi_row['malls'] or 0,
        'accessibility_score': round(accessibility, 1),
        'walkability_score': round(walkability, 1),
        'livability_score': round(livability, 1),
    }


def classify_growth_phase(market: Dict, spatial: Dict) -> Tuple[str, float]:
    """Classify locality growth phase based on metrics."""
    # Factors for growth phase (with null safety)
    price = market.get('avg_price_sqft') or 0
    listings = market.get('active_listings') or 0
    demand = market.get('demand_level') or 'medium'
    accessibility = spatial.get('accessibility_score') or 50
    poi_count = spatial.get('poi_count') or 0
    
    # Score components
    infrastructure_maturity = min(100, (poi_count or 0) * 2 + (accessibility or 0))
    market_activity = min(100, (listings or 0) * 2)
    
    # Classify
    if infrastructure_maturity < 30 and market_activity < 20:
        phase = 'emerging'
        confidence = 0.7
    elif infrastructure_maturity < 50 and market_activity < 50:
        phase = 'growing'
        confidence = 0.75
    elif infrastructure_maturity < 70 and demand == 'high':
        phase = 'maturing'
        confidence = 0.8
    elif infrastructure_maturity >= 70 and demand in ['high', 'medium']:
        phase = 'mature'
        confidence = 0.85
    else:
        phase = 'stable'
        confidence = 0.7
    
    return phase, confidence


def compute_risk_index(market: Dict, spatial: Dict) -> Tuple[float, str]:
    """Compute risk index for a locality."""
    risk_score = 50  # Base risk
    
    # Market risk factors
    if market.get('supply_level') == 'oversupply':
        risk_score += 15
    if market.get('demand_level') == 'low':
        risk_score += 10
    if (market.get('active_listings') or 0) > 200:
        risk_score += 10  # Oversaturated market
    
    # Positive factors (reduce risk)
    if (spatial.get('metro_count') or 0) > 0:
        risk_score -= 15
    if (spatial.get('accessibility_score') or 0) > 70:
        risk_score -= 10
    if market.get('demand_level') == 'high':
        risk_score -= 15
    
    # Bound to 0-100
    risk_score = max(0, min(100, risk_score))
    
    # Risk level
    if risk_score < 30:
        risk_level = 'low'
    elif risk_score < 50:
        risk_level = 'medium'
    elif risk_score < 70:
        risk_level = 'high'
    else:
        risk_level = 'very_high'
    
    return risk_score, risk_level


def classify_investor_type(market: Dict, spatial: Dict, risk: float) -> str:
    """Classify recommended investor type for locality."""
    growth_phase = market.get('growth_phase', 'stable')
    demand = market.get('demand_level', 'medium')
    
    if growth_phase == 'mature' and risk < 40 and demand in ['high', 'medium']:
        return 'conservative'
    elif growth_phase in ['maturing', 'mature'] and risk < 60:
        return 'balanced'
    elif growth_phase in ['growing', 'emerging'] and risk < 70:
        return 'aggressive'
    else:
        return 'speculative'


def classify_archetype(market: Dict, spatial: Dict) -> str:
    """Classify locality archetype based on characteristics."""
    poi_count = spatial.get('poi_count') or 0
    metro_count = spatial.get('metro_count') or 0
    price = market.get('avg_price_sqft') or 0
    schools = spatial.get('school_count') or 0
    malls = spatial.get('mall_count') or 0
    
    # Classification rules
    if price > 15000 and metro_count > 0:
        return 'premium_enclave'
    elif poi_count > 50 and metro_count > 0:
        return 'tech_hub'
    elif schools > 3 and (spatial.get('park_count') or 0) > 1:
        return 'family_suburb'
    elif malls > 2:
        return 'commercial_center'
    elif metro_count > 0:
        return 'transit_oriented'
    elif price < 8000:
        return 'affordable_zone'
    else:
        return 'mixed_use'


def build_locality_state(conn: sqlite3.Connection, locality: Dict, snapshot_date: str) -> Dict[str, Any]:
    """Build complete locality state for a single locality."""
    name = locality['name']
    city_id = locality.get('city_id', 'BLR')
    lat = locality.get('center_lat', 12.97)
    lng = locality.get('center_lng', 77.59)
    
    # Compute all features
    market = compute_market_metrics(conn, name, city_id)
    spatial = compute_spatial_features(conn, lat, lng)
    
    # Compute intelligence labels
    growth_phase, growth_confidence = classify_growth_phase(market, spatial)
    risk_index, risk_level = compute_risk_index(market, spatial)
    investor_type = classify_investor_type({**market, 'growth_phase': growth_phase}, spatial, risk_index)
    archetype = classify_archetype(market, spatial)
    
    # Hotspot score (composite) - with null safety
    accessibility = spatial.get('accessibility_score') or 50
    livability = spatial.get('livability_score') or 50
    hotspot_score = (
        (100 - (risk_index or 50)) * 0.3 +
        accessibility * 0.3 +
        (100 if market.get('demand_level') == 'high' else 50) * 0.2 +
        livability * 0.2
    )
    
    # Data completeness
    data_completeness = sum([
        1 if market.get('avg_price_sqft') else 0,
        1 if (spatial.get('poi_count') or 0) > 0 else 0,
        1 if (spatial.get('transport_count') or 0) > 0 else 0,
        1 if lat and lng else 0,
    ]) / 4.0
    
    return {
        'locality_id': locality['id'],
        'locality_name': name,
        'city_id': city_id,
        'locality_type': 'neighborhood',
        'snapshot_date': snapshot_date,
        'center_lat': lat,
        'center_lng': lng,
        
        # Market
        **market,
        
        # Spatial
        **spatial,
        
        # Intelligence
        'growth_phase': growth_phase,
        'growth_phase_confidence': growth_confidence,
        'investor_type': investor_type,
        'risk_index': risk_index,
        'risk_level': risk_level,
        'hotspot_score': round(hotspot_score, 1),
        'archetype': archetype,
        
        # Data quality
        'data_completeness': data_completeness,
        'confidence_score': data_completeness * growth_confidence * 100,
    }


def save_locality_state(conn: sqlite3.Connection, state: Dict[str, Any]):
    """Save locality state to database."""
    cursor = conn.cursor()
    
    # Upsert into locality_state
    columns = list(state.keys())
    placeholders = ', '.join(['?' for _ in columns])
    update_clause = ', '.join([f"{col} = excluded.{col}" for col in columns if col != 'locality_id'])
    
    sql = f"""
        INSERT INTO locality_state ({', '.join(columns)})
        VALUES ({placeholders})
        ON CONFLICT(locality_id) DO UPDATE SET {update_clause}, last_updated = CURRENT_TIMESTAMP
    """
    
    cursor.execute(sql, list(state.values()))
    
    # Also save to time series
    ts_columns = ['locality_id', 'city_id', 'snapshot_date', 'avg_price_sqft', 'median_price_sqft',
                  'active_listings', 'demand_level', 'supply_level', 'poi_count', 'transport_count',
                  'accessibility_score', 'walkability_score', 'livability_score', 'growth_phase',
                  'risk_index', 'hotspot_score', 'confidence_score']
    
    ts_values = [state.get(col) for col in ts_columns]
    ts_placeholders = ', '.join(['?' for _ in ts_columns])
    
    cursor.execute(f"""
        INSERT OR IGNORE INTO locality_state_ts ({', '.join(ts_columns)})
        VALUES ({ts_placeholders})
    """, ts_values)


def build_all_localities(db_path: str = None):
    """Build locality state for all discovered localities."""
    conn = get_db_connection(db_path)
    
    print("=" * 60)
    print("LOCALITY BRAIN BUILDER")
    print("=" * 60)
    print(f"Database: {db_path or DB_PATH}")
    print(f"Started: {datetime.now().isoformat()}")
    
    # Discover localities
    localities = discover_localities(conn)
    
    if not localities:
        print("\n⚠️ No localities found in property data!")
        conn.close()
        return
    
    snapshot_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\nBuilding state for {len(localities)} localities...")
    print("-" * 60)
    
    success_count = 0
    error_count = 0
    
    for i, locality in enumerate(localities):
        try:
            state = build_locality_state(conn, locality, snapshot_date)
            save_locality_state(conn, state)
            success_count += 1
            
            # Progress indicator
            if (i + 1) % 10 == 0 or i == len(localities) - 1:
                print(f"   Processed {i + 1}/{len(localities)} localities")
                
        except Exception as e:
            error_count += 1
            print(f"   ⚠️ Error processing {locality['name']}: {e}")
    
    conn.commit()
    
    # Summary
    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    print(f"Success: {success_count} localities")
    print(f"Errors: {error_count} localities")
    print(f"Snapshot date: {snapshot_date}")
    
    # Show top hotspots
    cursor = conn.cursor()
    cursor.execute("""
        SELECT locality_name, growth_phase, hotspot_score, risk_level, archetype
        FROM locality_state
        ORDER BY hotspot_score DESC
        LIMIT 10
    """)
    
    print("\n📊 Top 10 Hotspots:")
    print("-" * 60)
    for row in cursor.fetchall():
        print(f"   {row['locality_name']}: {row['growth_phase']} | Score: {row['hotspot_score']} | Risk: {row['risk_level']} | {row['archetype']}")
    
    conn.close()


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    build_all_localities(db_path)
