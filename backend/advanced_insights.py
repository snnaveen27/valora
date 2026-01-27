"""
Advanced Insights Service - Unified Intelligence Layer for Valora AI

Merges and enhances:
1. Price Tracking & Trends
2. Property Valuation with ML
3. Area Insights & Livability
4. Market Intelligence
5. Investment Analysis
6. Predictive Analytics

This replaces separate insights modules with a unified, powerful system.
"""

import sqlite3
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from collections import defaultdict

try:
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


@dataclass
class PriceTrend:
    """Price trend analysis for a property or area."""
    current_price: float
    price_30_days_ago: Optional[float] = None
    price_90_days_ago: Optional[float] = None
    change_30_days: Optional[float] = None
    change_90_days: Optional[float] = None
    percent_change_30: Optional[float] = None
    percent_change_90: Optional[float] = None
    trend_direction: str = "stable"  # up, down, stable
    volatility: float = 0.0
    forecast_30_days: Optional[float] = None


@dataclass
class MarketIntelligence:
    """Market intelligence for an area."""
    locality: str
    avg_price: float
    avg_price_per_sqft: float
    median_price: float
    price_range: Tuple[float, float]
    total_listings: int
    new_listings_30_days: int
    price_trend: str  # appreciating, depreciating, stable
    appreciation_rate: float  # % per month
    demand_score: float  # 0-100
    supply_score: float  # 0-100
    market_heat: str  # hot, warm, cool, cold
    best_time_to_buy: bool
    comparable_localities: List[str]


@dataclass
class InvestmentInsight:
    """Investment analysis for a property."""
    property_id: str
    current_value: float
    estimated_value_1yr: float
    estimated_value_3yr: float
    roi_potential: float  # %
    rental_yield: float  # %
    appreciation_potential: str  # high, medium, low
    risk_level: str  # low, medium, high
    investment_score: float  # 0-100
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class AdvancedAreaInsight:
    """Comprehensive area insights combining all data sources."""
    lat: float
    lng: float
    locality: str
    
    # Price Intelligence
    price_trend: Optional[PriceTrend] = None
    market_intel: Optional[MarketIntelligence] = None
    
    # Infrastructure Scores (0-100)
    connectivity_score: float = 0.0
    amenities_score: float = 0.0
    safety_score: float = 0.0
    education_score: float = 0.0
    healthcare_score: float = 0.0
    green_space_score: float = 0.0
    
    # Terrain & Environment
    elevation_m: float = 0.0
    flood_risk: str = "unknown"
    terrain_suitability: float = 0.0
    
    # Infrastructure Counts
    metro_stations: int = 0
    bus_stops: int = 0
    schools: int = 0
    hospitals: int = 0
    restaurants: int = 0
    parks: int = 0
    malls: int = 0
    
    # Distances (km)
    nearest_metro_km: float = 999.0
    nearest_hospital_km: float = 999.0
    nearest_school_km: float = 999.0
    nearest_mall_km: float = 999.0
    
    # Government Data
    population_density: Optional[float] = None
    water_supply: str = "unknown"
    
    # Overall Scores
    livability_score: float = 0.0
    investment_score: float = 0.0
    family_friendly_score: float = 0.0
    
    # AI Insights
    key_highlights: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Summary
    summary: str = ""


class AdvancedInsightsService:
    """
    Unified Advanced Insights Service.
    Combines price tracking, valuation, area analysis, and market intelligence.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
        
        # Cache for performance
        self._locality_cache = {}
        self._price_cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_time = {}
    
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in km between two points."""
        R = 6371
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        dlat, dlng = lat2 - lat1, lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    # =========================================================================
    # PRICE TRACKING & TRENDS
    # =========================================================================
    
    def get_price_trend(self, property_id: str) -> Optional[PriceTrend]:
        """Get price trend for a specific property."""
        conn = self._connect()
        cursor = conn.cursor()
        
        try:
            # Get all price history for this property
            cursor.execute("""
                SELECT price, snapshot_date 
                FROM price_history 
                WHERE property_id = ?
                ORDER BY snapshot_date DESC
            """, (property_id,))
            
            rows = cursor.fetchall()
            if not rows:
                # Get current price from properties table
                cursor.execute("SELECT price FROM properties WHERE property_id = ?", (property_id,))
                prop = cursor.fetchone()
                if prop and prop['price']:
                    return PriceTrend(current_price=prop['price'])
                return None
            
            current_price = rows[0]['price']
            trend = PriceTrend(current_price=current_price)
            
            # Find prices at different points in time
            today = date.today()
            for row in rows:
                snap_date = datetime.strptime(row['snapshot_date'], '%Y-%m-%d').date()
                days_ago = (today - snap_date).days
                
                if 25 <= days_ago <= 35 and trend.price_30_days_ago is None:
                    trend.price_30_days_ago = row['price']
                elif 85 <= days_ago <= 95 and trend.price_90_days_ago is None:
                    trend.price_90_days_ago = row['price']
            
            # Calculate changes
            if trend.price_30_days_ago:
                trend.change_30_days = current_price - trend.price_30_days_ago
                trend.percent_change_30 = (trend.change_30_days / trend.price_30_days_ago) * 100
            
            if trend.price_90_days_ago:
                trend.change_90_days = current_price - trend.price_90_days_ago
                trend.percent_change_90 = (trend.change_90_days / trend.price_90_days_ago) * 100
            
            # Determine trend direction
            if trend.percent_change_30:
                if trend.percent_change_30 > 2:
                    trend.trend_direction = "up"
                elif trend.percent_change_30 < -2:
                    trend.trend_direction = "down"
            
            # Calculate volatility (standard deviation of price changes)
            if len(rows) >= 3:
                prices = [r['price'] for r in rows]
                if ML_AVAILABLE:
                    trend.volatility = float(np.std(prices) / np.mean(prices) * 100)
            
            # Simple forecast (linear extrapolation)
            if trend.percent_change_30:
                trend.forecast_30_days = current_price * (1 + trend.percent_change_30 / 100)
            
            return trend
            
        finally:
            conn.close()
    
    def get_locality_price_trend(self, locality: str, days: int = 30) -> Dict[str, Any]:
        """Get price trends for a locality."""
        conn = self._connect()
        cursor = conn.cursor()
        
        try:
            # Get current average price
            cursor.execute("""
                SELECT AVG(price) as avg_price, COUNT(*) as count
                FROM properties
                WHERE locality LIKE ? AND price > 0
            """, (f"%{locality}%",))
            
            current = cursor.fetchone()
            
            # Get historical average from price_history
            cursor.execute("""
                SELECT AVG(price) as avg_price, snapshot_date
                FROM price_history
                WHERE locality LIKE ? AND price > 0
                AND snapshot_date >= date('now', '-' || ? || ' days')
                GROUP BY snapshot_date
                ORDER BY snapshot_date
            """, (f"%{locality}%", days))
            
            history = cursor.fetchall()
            
            result = {
                'locality': locality,
                'current_avg_price': current['avg_price'] if current else 0,
                'total_properties': current['count'] if current else 0,
                'price_history': [
                    {'date': h['snapshot_date'], 'avg_price': h['avg_price']}
                    for h in history
                ],
                'trend': 'stable',
                'appreciation_rate': 0.0
            }
            
            if history and len(history) >= 2:
                first_price = history[0]['avg_price']
                last_price = history[-1]['avg_price']
                if first_price and last_price:
                    change = (last_price - first_price) / first_price * 100
                    result['appreciation_rate'] = round(change, 2)
                    if change > 2:
                        result['trend'] = 'appreciating'
                    elif change < -2:
                        result['trend'] = 'depreciating'
            
            return result
            
        finally:
            conn.close()
    
    def get_top_price_movers(self, days: int = 30, limit: int = 20) -> List[Dict]:
        """Get properties with biggest price changes."""
        conn = self._connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                WITH latest AS (
                    SELECT property_id, price, locality,
                           ROW_NUMBER() OVER (PARTITION BY property_id ORDER BY snapshot_date DESC) as rn
                    FROM price_history
                ),
                oldest AS (
                    SELECT property_id, price,
                           ROW_NUMBER() OVER (PARTITION BY property_id ORDER BY snapshot_date ASC) as rn
                    FROM price_history
                    WHERE snapshot_date >= date('now', '-' || ? || ' days')
                )
                SELECT l.property_id, l.locality,
                       o.price as old_price, l.price as new_price,
                       (l.price - o.price) as change,
                       ROUND(((l.price - o.price) * 100.0 / o.price), 2) as percent_change
                FROM latest l
                JOIN oldest o ON l.property_id = o.property_id
                WHERE l.rn = 1 AND o.rn = 1 AND o.price > 0
                ORDER BY ABS(percent_change) DESC
                LIMIT ?
            """, (days, limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    # =========================================================================
    # MARKET INTELLIGENCE
    # =========================================================================
    
    def get_market_intelligence(self, locality: str) -> MarketIntelligence:
        """Get comprehensive market intelligence for a locality."""
        conn = self._connect()
        cursor = conn.cursor()
        
        try:
            # Basic statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    AVG(price) as avg_price,
                    AVG(price_per_sqft) as avg_ppsf,
                    MIN(price) as min_price,
                    MAX(price) as max_price
                FROM properties
                WHERE locality LIKE ? AND price > 0
            """, (f"%{locality}%",))
            
            stats = cursor.fetchone()
            
            # Get median price
            cursor.execute("""
                SELECT price FROM properties
                WHERE locality LIKE ? AND price > 0
                ORDER BY price
                LIMIT 1 OFFSET (
                    SELECT COUNT(*) / 2 FROM properties 
                    WHERE locality LIKE ? AND price > 0
                )
            """, (f"%{locality}%", f"%{locality}%"))
            
            median = cursor.fetchone()
            median_price = median['price'] if median else (stats['avg_price'] or 0)
            
            # New listings (properties added in last 30 days)
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM properties
                WHERE locality LIKE ? 
                AND created_at >= date('now', '-30 days')
            """, (f"%{locality}%",))
            new_listings = cursor.fetchone()['cnt']
            
            # Price trend from history
            trend_data = self.get_locality_price_trend(locality, 30)
            
            # Calculate demand/supply scores
            demand_score = min(100, new_listings * 2)  # More new listings = more demand
            supply_score = min(100, stats['total'] / 10) if stats['total'] else 0
            
            # Market heat
            appreciation = trend_data.get('appreciation_rate', 0)
            if appreciation > 5:
                market_heat = 'hot'
            elif appreciation > 2:
                market_heat = 'warm'
            elif appreciation > -2:
                market_heat = 'cool'
            else:
                market_heat = 'cold'
            
            # Find comparable localities
            cursor.execute("""
                SELECT DISTINCT locality, AVG(price_per_sqft) as ppsf
                FROM properties
                WHERE price_per_sqft BETWEEN ? AND ?
                AND locality NOT LIKE ?
                GROUP BY locality
                HAVING COUNT(*) > 5
                ORDER BY ABS(ppsf - ?) ASC
                LIMIT 5
            """, (
                (stats['avg_ppsf'] or 5000) * 0.8,
                (stats['avg_ppsf'] or 5000) * 1.2,
                f"%{locality}%",
                stats['avg_ppsf'] or 5000
            ))
            
            comparable = [row['locality'] for row in cursor.fetchall()]
            
            return MarketIntelligence(
                locality=locality,
                avg_price=stats['avg_price'] or 0,
                avg_price_per_sqft=stats['avg_ppsf'] or 0,
                median_price=median_price,
                price_range=(stats['min_price'] or 0, stats['max_price'] or 0),
                total_listings=stats['total'] or 0,
                new_listings_30_days=new_listings,
                price_trend=trend_data.get('trend', 'stable'),
                appreciation_rate=appreciation,
                demand_score=demand_score,
                supply_score=supply_score,
                market_heat=market_heat,
                best_time_to_buy=(market_heat in ['cool', 'cold']),
                comparable_localities=comparable
            )
            
        finally:
            conn.close()
    
    # =========================================================================
    # ADVANCED AREA INSIGHTS
    # =========================================================================
    
    def get_advanced_insights(self, lat: float, lng: float, 
                             locality: str = None,
                             radius_m: float = 1000) -> AdvancedAreaInsight:
        """Get comprehensive advanced insights for a location."""
        conn = self._connect()
        cursor = conn.cursor()
        
        # Determine locality from nearest property if not provided
        if not locality:
            cursor.execute("""
                SELECT locality FROM properties
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY ABS(latitude - ?) + ABS(longitude - ?)
                LIMIT 1
            """, (lat, lng))
            row = cursor.fetchone()
            locality = row['locality'] if row else "Unknown"
        
        insight = AdvancedAreaInsight(lat=lat, lng=lng, locality=locality)
        radius_deg = radius_m / 111000
        
        try:
            # 1. Get terrain data
            self._add_terrain_insights(cursor, lat, lng, insight)
            
            # 2. Get infrastructure counts and scores
            self._add_infrastructure_insights(cursor, lat, lng, radius_deg, insight)
            
            # 3. Get distance to key amenities
            self._add_distance_insights(cursor, lat, lng, insight)
            
            # 4. Get government data
            self._add_gov_insights(cursor, lat, lng, insight)
            
            # 5. Get market intelligence
            if locality and locality != "Unknown":
                insight.market_intel = self.get_market_intelligence(locality)
            
            # 6. Calculate composite scores
            self._calculate_composite_scores(insight)
            
            # 7. Generate AI insights
            self._generate_ai_insights(insight)
            
            # 8. Generate summary
            insight.summary = self._generate_insight_summary(insight)
            
        finally:
            conn.close()
        
        return insight
    
    def _add_terrain_insights(self, cursor, lat: float, lng: float, 
                             insight: AdvancedAreaInsight):
        """Add terrain data to insights."""
        cursor.execute("""
            SELECT elevation_m, slope_deg, flood_risk, terrain_type, suitability_score
            FROM terrain_grid
            ORDER BY ABS(center_lat - ?) + ABS(center_lng - ?)
            LIMIT 1
        """, (lat, lng))
        
        row = cursor.fetchone()
        if row:
            insight.elevation_m = row['elevation_m'] or 0
            insight.flood_risk = row['flood_risk'] or 'unknown'
            insight.terrain_suitability = row['suitability_score'] or 0
    
    def _add_infrastructure_insights(self, cursor, lat: float, lng: float,
                                     radius_deg: float, insight: AdvancedAreaInsight):
        """Add infrastructure counts and calculate scores."""
        # POI counts - parse from source_data since category is 'other'
        cursor.execute("""
            SELECT name, source_data
            FROM pois
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
        """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
        
        # Count POIs by type from source_data or name
        for row in cursor.fetchall():
            name = (row['name'] or '').lower()
            poi_type = ''
            
            # Try to get type from source_data
            if row['source_data']:
                try:
                    data = json.loads(row['source_data'])
                    poi_type = (data.get('type', '') or data.get('subtype', '')).lower()
                except:
                    pass
            
            # Categorize by type or name keywords
            if 'school' in poi_type or 'school' in name or 'college' in name or 'university' in name:
                insight.schools += 1
            elif 'hospital' in poi_type or 'hospital' in name or 'clinic' in name or 'medical' in name:
                insight.hospitals += 1
            elif 'restaurant' in poi_type or 'restaurant' in name or 'cafe' in name or 'food' in name:
                insight.restaurants += 1
            elif 'park' in poi_type or 'park' in name or 'garden' in name:
                insight.parks += 1
            elif 'mall' in poi_type or 'mall' in name or 'shop' in poi_type or 'supermarket' in name:
                insight.malls += 1
        
        # Transport counts
        cursor.execute("""
            SELECT transport_type, COUNT(*) as cnt
            FROM transport_stops
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
            GROUP BY transport_type
        """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
        
        for row in cursor.fetchall():
            t_type = (row['transport_type'] or '').lower()
            if 'metro' in t_type:
                insight.metro_stations += row['cnt']
            elif 'bus' in t_type:
                insight.bus_stops += row['cnt']
        
        # Calculate scores
        insight.education_score = min(100, insight.schools * 15)
        insight.healthcare_score = min(100, insight.hospitals * 20)
        insight.amenities_score = min(100, (insight.restaurants + insight.malls) * 5)
        insight.green_space_score = min(100, insight.parks * 20)
        insight.connectivity_score = min(100, insight.metro_stations * 30 + insight.bus_stops * 5)
    
    def _add_distance_insights(self, cursor, lat: float, lng: float,
                              insight: AdvancedAreaInsight):
        """Calculate distances to nearest key amenities."""
        # Nearest metro
        cursor.execute("""
            SELECT latitude, longitude FROM transport_stops
            WHERE transport_type LIKE '%metro%' OR name LIKE '%Metro%'
            AND latitude IS NOT NULL
        """)
        metros = cursor.fetchall()
        if metros:
            insight.nearest_metro_km = min(
                self._haversine(lat, lng, m['latitude'], m['longitude'])
                for m in metros
            )
        
        # Nearest hospital
        cursor.execute("""
            SELECT latitude, longitude FROM pois
            WHERE category IN ('hospital', 'healthcare')
            AND latitude IS NOT NULL
        """)
        hospitals = cursor.fetchall()
        if hospitals:
            insight.nearest_hospital_km = min(
                self._haversine(lat, lng, h['latitude'], h['longitude'])
                for h in hospitals
            )
        
        # Nearest school
        cursor.execute("""
            SELECT latitude, longitude FROM pois
            WHERE category IN ('school', 'education')
            AND latitude IS NOT NULL
        """)
        schools = cursor.fetchall()
        if schools:
            insight.nearest_school_km = min(
                self._haversine(lat, lng, s['latitude'], s['longitude'])
                for s in schools
            )
    
    def _add_gov_insights(self, cursor, lat: float, lng: float,
                         insight: AdvancedAreaInsight):
        """Add government data insights."""
        # Get education data from gov_data
        cursor.execute("""
            SELECT raw_data FROM gov_data
            WHERE category = 'education'
            LIMIT 10
        """)
        
        for row in cursor.fetchall():
            try:
                data = json.loads(row['raw_data'])
                if 'total_current_pop' in data:
                    pop = float(data.get('total_current_pop', 0))
                    if pop > 0:
                        insight.population_density = pop
                        break
            except:
                continue
    
    def _calculate_composite_scores(self, insight: AdvancedAreaInsight):
        """Calculate composite scores."""
        # Livability score (weighted average)
        insight.livability_score = (
            insight.connectivity_score * 0.25 +
            insight.amenities_score * 0.15 +
            insight.education_score * 0.15 +
            insight.healthcare_score * 0.15 +
            insight.green_space_score * 0.10 +
            insight.terrain_suitability * 0.20
        )
        
        # Family friendly score
        insight.family_friendly_score = (
            insight.education_score * 0.35 +
            insight.healthcare_score * 0.25 +
            insight.green_space_score * 0.20 +
            (100 if insight.flood_risk == 'low' else 50 if insight.flood_risk == 'medium' else 20) * 0.20
        )
        
        # Investment score (needs market data)
        if insight.market_intel:
            appreciation = insight.market_intel.appreciation_rate
            investment_base = 50 + appreciation * 5
            insight.investment_score = min(100, max(0, investment_base + insight.connectivity_score * 0.3))
        else:
            insight.investment_score = insight.connectivity_score * 0.5 + insight.livability_score * 0.5
    
    def _generate_ai_insights(self, insight: AdvancedAreaInsight):
        """Generate AI-powered highlights, warnings, and recommendations."""
        # Highlights
        if insight.metro_stations > 0:
            insight.key_highlights.append(f"Excellent metro connectivity ({insight.metro_stations} stations nearby)")
        if insight.connectivity_score > 70:
            insight.key_highlights.append("High connectivity score - well connected area")
        if insight.education_score > 60:
            insight.key_highlights.append(f"Good educational infrastructure ({insight.schools} schools)")
        if insight.healthcare_score > 60:
            insight.key_highlights.append(f"Good healthcare access ({insight.hospitals} hospitals)")
        if insight.market_intel and insight.market_intel.appreciation_rate > 3:
            insight.key_highlights.append(f"Appreciating market ({insight.market_intel.appreciation_rate:.1f}% growth)")
        
        # Warnings
        if insight.flood_risk == 'high':
            insight.warnings.append("⚠️ High flood risk area - check during monsoon")
        if insight.nearest_hospital_km > 5:
            insight.warnings.append("⚠️ Hospitals are far (>5km) - consider emergency access")
        if insight.metro_stations == 0 and insight.bus_stops < 3:
            insight.warnings.append("⚠️ Limited public transport - may need own vehicle")
        if insight.market_intel and insight.market_intel.market_heat == 'hot':
            insight.warnings.append("⚠️ Hot market - prices may be inflated")
        
        # Recommendations
        if insight.investment_score > 70:
            insight.recommendations.append("✓ Good investment potential - consider for long-term")
        if insight.family_friendly_score > 70:
            insight.recommendations.append("✓ Suitable for families with children")
        if insight.market_intel and insight.market_intel.best_time_to_buy:
            insight.recommendations.append("✓ Good time to buy - market is cool/stable")
        if insight.connectivity_score > 80:
            insight.recommendations.append("✓ Great for working professionals (good commute)")
    
    def _generate_insight_summary(self, insight: AdvancedAreaInsight) -> str:
        """Generate a natural language summary."""
        parts = []
        
        # Location introduction
        parts.append(f"{insight.locality} is a")
        
        # Livability assessment
        if insight.livability_score >= 75:
            parts.append("highly livable area")
        elif insight.livability_score >= 50:
            parts.append("moderately livable area")
        else:
            parts.append("developing area")
        
        # Connectivity
        if insight.connectivity_score >= 70:
            parts.append("with excellent connectivity")
        elif insight.metro_stations > 0:
            parts.append("with metro access")
        
        # Market
        if insight.market_intel:
            if insight.market_intel.market_heat == 'hot':
                parts.append(". The market is currently hot with high demand")
            elif insight.market_intel.appreciation_rate > 0:
                parts.append(f". Property values are appreciating at {insight.market_intel.appreciation_rate:.1f}% monthly")
        
        # Key highlight
        if insight.key_highlights:
            parts.append(f". Key strength: {insight.key_highlights[0].lower()}")
        
        # Warning
        if insight.warnings:
            parts.append(f". Note: {insight.warnings[0]}")
        
        return " ".join(parts) + "."
    
    # =========================================================================
    # INVESTMENT ANALYSIS
    # =========================================================================
    
    def get_investment_insight(self, property_id: str) -> Optional[InvestmentInsight]:
        """Get investment analysis for a specific property."""
        conn = self._connect()
        cursor = conn.cursor()
        
        try:
            # Get property details
            cursor.execute("""
                SELECT property_id, price, locality, total_area_sqft, bedrooms,
                       latitude, longitude, property_type
                FROM properties
                WHERE property_id = ?
            """, (property_id,))
            
            prop = cursor.fetchone()
            if not prop:
                return None
            
            current_value = prop['price'] or 0
            
            # Get price trend
            price_trend = self.get_price_trend(property_id)
            
            # Get market intelligence
            market = None
            if prop['locality']:
                market = self.get_market_intelligence(prop['locality'])
            
            # Calculate projections
            monthly_appreciation = market.appreciation_rate if market else 0.5
            estimated_1yr = current_value * (1 + monthly_appreciation * 12 / 100)
            estimated_3yr = current_value * (1 + monthly_appreciation * 36 / 100)
            
            # ROI potential (3-year return)
            roi = ((estimated_3yr - current_value) / current_value * 100) if current_value > 0 else 0
            
            # Rental yield estimate (rough estimate based on market)
            rental_yield = 3.5  # Default 3.5% for Bangalore
            if prop['locality']:
                if 'koramangala' in prop['locality'].lower() or 'indiranagar' in prop['locality'].lower():
                    rental_yield = 4.0
                elif 'whitefield' in prop['locality'].lower() or 'marathahalli' in prop['locality'].lower():
                    rental_yield = 3.8
            
            # Determine appreciation potential
            if monthly_appreciation > 2:
                appreciation_potential = 'high'
            elif monthly_appreciation > 0.5:
                appreciation_potential = 'medium'
            else:
                appreciation_potential = 'low'
            
            # Risk level
            risk_level = 'medium'
            if market and market.market_heat == 'hot':
                risk_level = 'high'
            elif market and market.market_heat == 'cold':
                risk_level = 'low'
            
            # Investment score
            investment_score = min(100, 50 + roi / 2)
            
            # Pros and cons
            pros = []
            cons = []
            
            if appreciation_potential == 'high':
                pros.append("High appreciation potential")
            if rental_yield > 3.5:
                pros.append(f"Good rental yield ({rental_yield}%)")
            if market and market.total_listings > 50:
                pros.append("Active market with good liquidity")
            
            if risk_level == 'high':
                cons.append("Market may be overheated")
            if rental_yield < 3:
                cons.append("Below average rental yield")
            if not market or market.total_listings < 20:
                cons.append("Limited market activity")
            
            # Recommendation
            if investment_score > 70:
                recommendation = "Strong buy - good investment potential with manageable risk"
            elif investment_score > 50:
                recommendation = "Hold/Buy - decent investment, monitor market trends"
            else:
                recommendation = "Caution - evaluate carefully before investing"
            
            return InvestmentInsight(
                property_id=property_id,
                current_value=current_value,
                estimated_value_1yr=estimated_1yr,
                estimated_value_3yr=estimated_3yr,
                roi_potential=roi,
                rental_yield=rental_yield,
                appreciation_potential=appreciation_potential,
                risk_level=risk_level,
                investment_score=investment_score,
                pros=pros,
                cons=cons,
                recommendation=recommendation
            )
            
        finally:
            conn.close()
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def to_dict(self, obj) -> Dict:
        """Convert dataclass to dictionary."""
        if hasattr(obj, '__dataclass_fields__'):
            return asdict(obj)
        return obj


# Singleton instance
_insights_service = None

def get_insights_service() -> AdvancedInsightsService:
    """Get singleton instance of Advanced Insights Service."""
    global _insights_service
    if _insights_service is None:
        _insights_service = AdvancedInsightsService()
    return _insights_service
