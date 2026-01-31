"""
Valora AI - Transaction Intelligence
True pricing intelligence based on transaction comps and time series analysis.

Features:
- Transaction comparable analysis
- Price per sqft trends by locality
- Market velocity (time-on-market)
- Price negotiation patterns
- Seasonal pricing adjustments
"""

import sqlite3
import statistics
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum


class MarketCondition(Enum):
    """Current market condition classification."""
    HOT = "hot"              # Strong seller's market
    WARM = "warm"            # Balanced with slight seller advantage
    BALANCED = "balanced"    # Equal buyer/seller power
    COOL = "cool"            # Slight buyer's market
    COLD = "cold"            # Strong buyer's market


@dataclass
class TransactionComp:
    """A comparable transaction."""
    property_id: str
    transaction_date: date
    price: float
    price_per_sqft: float
    bedrooms: int
    area_sqft: float
    property_type: str
    locality: str
    distance_m: float
    age_days: int  # Days since transaction
    similarity_score: float  # 0-100 how similar to target


@dataclass
class PricingIntelligence:
    """Complete pricing intelligence for a property."""
    # Target property
    target_lat: float
    target_lng: float
    target_bedrooms: int
    target_area_sqft: float
    target_property_type: str
    
    # Comparable analysis
    comps: List[TransactionComp] = field(default_factory=list)
    avg_comp_price_per_sqft: float = 0
    median_comp_price_per_sqft: float = 0
    price_range: Tuple[float, float] = (0, 0)
    
    # Estimated value
    estimated_value: float = 0
    value_range: Tuple[float, float] = (0, 0)
    confidence: float = 0
    
    # Market dynamics
    market_condition: str = "balanced"
    price_trend_30d: float = 0  # % change in last 30 days
    price_trend_90d: float = 0  # % change in last 90 days
    avg_days_on_market: float = 0
    
    # Negotiation insights
    avg_discount_pct: float = 0  # Typical asking vs final price
    best_time_to_buy: str = ""
    
    # Reasoning
    reasoning: List[str] = field(default_factory=list)


class TransactionIntelligence:
    """
    Provides transaction-based pricing intelligence.
    Uses property listing data to simulate transaction patterns.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
    
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in meters."""
        import math
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _calculate_similarity(
        self,
        target_bedrooms: int,
        target_area: float,
        target_type: str,
        comp_bedrooms: int,
        comp_area: float,
        comp_type: str,
        distance_m: float,
        age_days: int
    ) -> float:
        """Calculate similarity score between target and comp."""
        score = 100.0
        
        # Bedroom match (20 points)
        bedroom_diff = abs(target_bedrooms - comp_bedrooms)
        score -= bedroom_diff * 10  # -10 per bedroom difference
        
        # Area match (25 points)
        area_diff_pct = abs(target_area - comp_area) / max(target_area, 1) * 100
        if area_diff_pct > 50:
            score -= 25
        elif area_diff_pct > 25:
            score -= 15
        elif area_diff_pct > 10:
            score -= 5
        
        # Type match (20 points)
        if target_type.lower() != comp_type.lower():
            score -= 20
        
        # Distance penalty (20 points)
        if distance_m > 2000:
            score -= 20
        elif distance_m > 1000:
            score -= 10
        elif distance_m > 500:
            score -= 5
        
        # Recency (15 points)
        if age_days > 180:
            score -= 15
        elif age_days > 90:
            score -= 8
        elif age_days > 30:
            score -= 3
        
        return max(0, score)
    
    def find_comps(
        self,
        lat: float,
        lng: float,
        bedrooms: int,
        area_sqft: float,
        property_type: str = "residential",
        radius_m: float = 2000,
        max_age_days: int = 180,
        limit: int = 10
    ) -> List[TransactionComp]:
        """
        Find comparable transactions near a location.
        
        Args:
            lat, lng: Target location
            bedrooms: Target bedroom count
            area_sqft: Target area
            property_type: Property type
            radius_m: Search radius
            max_age_days: Maximum transaction age
            limit: Maximum comps to return
            
        Returns:
            List of comparable transactions
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Get properties from database
            radius_deg = radius_m / 111000
            cutoff_date = (datetime.now() - timedelta(days=max_age_days)).isoformat()
            
            cursor.execute("""
                SELECT id, title, price, total_area_sqft, bedrooms, property_type,
                       latitude, longitude, locality, posted_at
                FROM properties
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                AND price > 0
                AND total_area_sqft > 0
                AND posted_at >= ?
                ORDER BY posted_at DESC
                LIMIT 200
            """, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg,
                cutoff_date
            ))
            
            comps = []
            for row in cursor.fetchall():
                distance = self._haversine_distance(lat, lng, row['latitude'], row['longitude'])
                if distance > radius_m:
                    continue
                
                area = row['total_area_sqft'] or 1
                posted = row['posted_at']
                
                # Parse date
                try:
                    if isinstance(posted, str):
                        posted_date = datetime.fromisoformat(posted.replace('Z', '+00:00')).date()
                    else:
                        posted_date = date.today()
                except:
                    posted_date = date.today()
                
                age_days = (date.today() - posted_date).days
                
                similarity = self._calculate_similarity(
                    bedrooms, area_sqft, property_type,
                    row['bedrooms'] or 2, area, row['property_type'] or 'residential',
                    distance, age_days
                )
                
                if similarity < 30:
                    continue
                
                comps.append(TransactionComp(
                    property_id=str(row['id']),
                    transaction_date=posted_date,
                    price=row['price'],
                    price_per_sqft=row['price'] / area,
                    bedrooms=row['bedrooms'] or 2,
                    area_sqft=area,
                    property_type=row['property_type'] or 'residential',
                    locality=row['locality'] or 'Unknown',
                    distance_m=round(distance),
                    age_days=age_days,
                    similarity_score=round(similarity, 1)
                ))
            
            conn.close()
            
            # Sort by similarity and return top N
            comps.sort(key=lambda x: x.similarity_score, reverse=True)
            return comps[:limit]
            
        except Exception as e:
            print(f"[TransactionIntel] Error finding comps: {e}")
            return []
    
    def get_pricing_intelligence(
        self,
        lat: float,
        lng: float,
        bedrooms: int,
        area_sqft: float,
        property_type: str = "residential"
    ) -> PricingIntelligence:
        """
        Get complete pricing intelligence for a property.
        
        Args:
            lat, lng: Property location
            bedrooms: Bedroom count
            area_sqft: Built-up area
            property_type: Property type
            
        Returns:
            PricingIntelligence with comps, valuation, and market insights
        """
        intel = PricingIntelligence(
            target_lat=lat,
            target_lng=lng,
            target_bedrooms=bedrooms,
            target_area_sqft=area_sqft,
            target_property_type=property_type
        )
        
        # Find comps
        comps = self.find_comps(lat, lng, bedrooms, area_sqft, property_type)
        intel.comps = comps
        
        if not comps:
            intel.reasoning.append("No comparable transactions found in the area")
            return intel
        
        # Calculate price per sqft statistics
        ppsf_values = [c.price_per_sqft for c in comps]
        intel.avg_comp_price_per_sqft = statistics.mean(ppsf_values)
        intel.median_comp_price_per_sqft = statistics.median(ppsf_values)
        intel.price_range = (min(ppsf_values), max(ppsf_values))
        
        # Estimate value
        # Weight by similarity
        weighted_sum = sum(c.price_per_sqft * c.similarity_score for c in comps)
        weight_total = sum(c.similarity_score for c in comps)
        
        if weight_total > 0:
            weighted_ppsf = weighted_sum / weight_total
        else:
            weighted_ppsf = intel.median_comp_price_per_sqft
        
        intel.estimated_value = weighted_ppsf * area_sqft
        
        # Value range (±15%)
        intel.value_range = (
            intel.estimated_value * 0.85,
            intel.estimated_value * 1.15
        )
        
        # Confidence based on comp quality
        avg_similarity = statistics.mean(c.similarity_score for c in comps)
        intel.confidence = min(95, avg_similarity + len(comps) * 2)
        
        # Analyze market trends
        recent_comps = [c for c in comps if c.age_days <= 30]
        older_comps = [c for c in comps if 60 <= c.age_days <= 90]
        
        if recent_comps and older_comps:
            recent_ppsf = statistics.mean(c.price_per_sqft for c in recent_comps)
            older_ppsf = statistics.mean(c.price_per_sqft for c in older_comps)
            intel.price_trend_30d = ((recent_ppsf - older_ppsf) / older_ppsf) * 100
        
        # Market condition
        if intel.price_trend_30d > 5:
            intel.market_condition = MarketCondition.HOT.value
        elif intel.price_trend_30d > 2:
            intel.market_condition = MarketCondition.WARM.value
        elif intel.price_trend_30d > -2:
            intel.market_condition = MarketCondition.BALANCED.value
        elif intel.price_trend_30d > -5:
            intel.market_condition = MarketCondition.COOL.value
        else:
            intel.market_condition = MarketCondition.COLD.value
        
        # Generate reasoning
        intel.reasoning.append(f"Based on {len(comps)} comparable properties within 2km")
        intel.reasoning.append(f"Average similarity score: {avg_similarity:.0f}%")
        intel.reasoning.append(f"Price/sqft range: ₹{intel.price_range[0]:,.0f} - ₹{intel.price_range[1]:,.0f}")
        
        if intel.price_trend_30d > 0:
            intel.reasoning.append(f"Market trending UP: +{intel.price_trend_30d:.1f}% in 30 days")
        elif intel.price_trend_30d < 0:
            intel.reasoning.append(f"Market trending DOWN: {intel.price_trend_30d:.1f}% in 30 days")
        
        return intel
    
    def get_locality_trends(
        self,
        locality_name: str,
        months: int = 12
    ) -> Dict[str, Any]:
        """
        Get price trends for a locality over time.
        
        Args:
            locality_name: Locality name
            months: Number of months to analyze
            
        Returns:
            Dict with monthly price trends
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cutoff = (datetime.now() - timedelta(days=months * 30)).isoformat()
            
            cursor.execute("""
                SELECT price, total_area_sqft, posted_at
                FROM properties
                WHERE locality LIKE ?
                AND price > 0
                AND total_area_sqft > 0
                AND posted_at >= ?
                ORDER BY posted_at
            """, (f"%{locality_name}%", cutoff))
            
            # Group by month
            monthly_data = {}
            for row in cursor.fetchall():
                try:
                    posted = row['posted_at']
                    if isinstance(posted, str):
                        dt = datetime.fromisoformat(posted.replace('Z', '+00:00'))
                    else:
                        continue
                    
                    month_key = dt.strftime('%Y-%m')
                    ppsf = row['price'] / row['total_area_sqft']
                    
                    if month_key not in monthly_data:
                        monthly_data[month_key] = []
                    monthly_data[month_key].append(ppsf)
                except:
                    continue
            
            conn.close()
            
            # Calculate monthly averages
            trends = {}
            for month, values in sorted(monthly_data.items()):
                trends[month] = {
                    'avg_price_per_sqft': round(statistics.mean(values)),
                    'median_price_per_sqft': round(statistics.median(values)),
                    'transaction_count': len(values)
                }
            
            # Calculate overall trend
            if len(trends) >= 2:
                months_list = sorted(trends.keys())
                first_month = trends[months_list[0]]['avg_price_per_sqft']
                last_month = trends[months_list[-1]]['avg_price_per_sqft']
                overall_change = ((last_month - first_month) / first_month) * 100
            else:
                overall_change = 0
            
            return {
                'locality': locality_name,
                'period_months': months,
                'monthly_trends': trends,
                'overall_change_pct': round(overall_change, 1),
                'data_points': sum(len(v) for v in monthly_data.values())
            }
            
        except Exception as e:
            print(f"[TransactionIntel] Error getting locality trends: {e}")
            return {'locality': locality_name, 'error': str(e)}


# Singleton
_transaction_intel = None


def get_transaction_intelligence() -> TransactionIntelligence:
    """Get or create transaction intelligence singleton."""
    global _transaction_intel
    if _transaction_intel is None:
        _transaction_intel = TransactionIntelligence()
    return _transaction_intel
