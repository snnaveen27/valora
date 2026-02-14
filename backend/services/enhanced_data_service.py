"""
Enhanced Data Service for Valora AI
Integrates all data sources: gov_data, terrain, analytics, POIs.

Provides unified access to:
1. Government data (population, water, schools)
2. Terrain analysis (flood risk, elevation, slope)
3. Pre-computed property analytics
4. Categorized POIs and transport
5. Named buildings for context
"""

import sqlite3
import json
from pathlib import Path
from config import config
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import math


@dataclass
class AreaInsights:
    """Comprehensive insights about an area."""
    lat: float
    lng: float
    radius_m: float
    
    # Government data
    population: Optional[int] = None
    households: Optional[int] = None
    water_supply: Optional[str] = None
    school_enrollment: Optional[int] = None
    
    # Terrain
    elevation_m: Optional[float] = None
    slope_deg: Optional[float] = None
    flood_risk: str = "unknown"
    terrain_type: str = "unknown"
    suitability_score: Optional[float] = None
    
    # Infrastructure
    metro_count: int = 0
    bus_stops: int = 0
    schools: int = 0
    hospitals: int = 0
    restaurants: int = 0
    parks: int = 0
    
    # Named landmarks
    landmarks: List[str] = field(default_factory=list)
    
    # Warnings
    warnings: List[str] = field(default_factory=list)
    
    # Summary
    livability_score: float = 0.0
    summary: str = ""


@dataclass 
class PropertyEnrichedData:
    """Enriched property data with all analytics."""
    property_id: str
    
    # Basic info
    title: str = ""
    price: float = 0
    bedrooms: int = 0
    area_sqft: float = 0
    
    # Location
    lat: Optional[float] = None
    lng: Optional[float] = None
    locality: str = ""
    
    # Amenities (extracted)
    amenities: List[str] = field(default_factory=list)
    
    # Pre-computed analytics
    metro_score: float = 0
    school_score: float = 0
    hospital_score: float = 0
    investment_score: float = 0
    
    # Distances
    nearest_metro_m: float = 0
    nearest_school_m: float = 0
    nearest_hospital_m: float = 0
    
    # Terrain warnings
    flood_risk: str = "unknown"
    terrain_warnings: List[str] = field(default_factory=list)
    
    # Nearby landmarks
    nearby_landmarks: List[str] = field(default_factory=list)


class EnhancedDataService:
    """
    Unified data access layer integrating all enhanced data sources.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = config.DB_PATH
        self.db_path = str(db_path)
    
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_area_insights(self, lat: float, lng: float, 
                         radius_m: float = 1000) -> AreaInsights:
        """Get comprehensive insights about an area."""
        insights = AreaInsights(lat=lat, lng=lng, radius_m=radius_m)
        conn = self._connect()
        cursor = conn.cursor()
        
        try:
            # 1. Terrain data
            self._add_terrain_data(cursor, lat, lng, insights)
            
            # 2. Government data (find nearest village/habitation)
            self._add_gov_data(cursor, lat, lng, insights)
            
            # 3. POI counts by category
            self._add_poi_counts(cursor, lat, lng, radius_m, insights)
            
            # 4. Named landmarks
            self._add_landmarks(cursor, lat, lng, radius_m, insights)
            
            # 5. Transport
            self._add_transport_counts(cursor, lat, lng, radius_m, insights)
            
            # 6. Generate warnings
            self._generate_warnings(insights)
            
            # 7. Calculate livability score
            self._calculate_livability(insights)
            
            # 8. Generate summary
            insights.summary = self._generate_area_summary(insights)
            
        finally:
            conn.close()
        
        return insights
    
    def _add_terrain_data(self, cursor, lat: float, lng: float, 
                         insights: AreaInsights):
        """Add terrain data to insights."""
        cursor.execute("""
            SELECT elevation_m, slope_deg, flood_risk, terrain_type, suitability_score,
                   ABS(center_lat - ?) + ABS(center_lng - ?) as dist
            FROM terrain_grid
            ORDER BY dist
            LIMIT 1
        """, (lat, lng))
        
        row = cursor.fetchone()
        if row:
            insights.elevation_m = row['elevation_m']
            insights.slope_deg = row['slope_deg']
            insights.flood_risk = row['flood_risk'] or 'unknown'
            insights.terrain_type = row['terrain_type'] or 'unknown'
            insights.suitability_score = row['suitability_score']
    
    def _add_gov_data(self, cursor, lat: float, lng: float,
                     insights: AreaInsights):
        """Add government data to insights."""
        # Try to find relevant gov_data by parsing raw_data
        cursor.execute("""
            SELECT raw_data FROM gov_data
            WHERE data_type = 'other'
            LIMIT 100
        """)
        
        # Parse and find population data
        for row in cursor.fetchall():
            try:
                data = json.loads(row['raw_data'])
                if 'total_current_pop' in data:
                    pop = int(data.get('total_current_pop', 0))
                    if pop > 0 and insights.population is None:
                        insights.population = pop
                        insights.households = int(data.get('households', 0))
                        water_status = data.get('ispws', 'Unknown')
                        insights.water_supply = 'PWS Available' if water_status == 'Yes' else 'Limited'
                        break
            except:
                continue
    
    def _add_poi_counts(self, cursor, lat: float, lng: float, 
                       radius_m: float, insights: AreaInsights):
        """Add POI counts by category."""
        radius_deg = radius_m / 111000
        
        cursor.execute("""
            SELECT category, COUNT(*) as cnt
            FROM pois
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
            GROUP BY category
        """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
        
        for row in cursor.fetchall():
            cat = row['category']
            cnt = row['cnt']
            if cat == 'school':
                insights.schools = cnt
            elif cat == 'hospital':
                insights.hospitals = cnt
            elif cat == 'restaurant':
                insights.restaurants = cnt
            elif cat == 'park':
                insights.parks = cnt
    
    def _add_landmarks(self, cursor, lat: float, lng: float,
                      radius_m: float, insights: AreaInsights):
        """Add named landmarks nearby."""
        radius_deg = radius_m / 111000
        
        cursor.execute("""
            SELECT name FROM buildings
            WHERE name IS NOT NULL AND name != ''
            AND latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
            AND (building_type IN ('apartments', 'commercial', 'retail', 'office') 
                 OR height > 30)
            LIMIT 10
        """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
        
        insights.landmarks = [row['name'] for row in cursor.fetchall()]
    
    def _add_transport_counts(self, cursor, lat: float, lng: float,
                             radius_m: float, insights: AreaInsights):
        """Add transport stop counts."""
        radius_deg = radius_m / 111000
        
        cursor.execute("""
            SELECT transport_type, COUNT(*) as cnt
            FROM transport_stops
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
            GROUP BY transport_type
        """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
        
        for row in cursor.fetchall():
            t_type = row['transport_type']
            if t_type == 'metro':
                insights.metro_count = row['cnt']
            elif t_type == 'bus':
                insights.bus_stops = row['cnt']
    
    def _generate_warnings(self, insights: AreaInsights):
        """Generate area warnings."""
        if insights.flood_risk == 'high':
            insights.warnings.append("⚠️ HIGH FLOOD RISK: This area has elevated flood risk")
        elif insights.flood_risk == 'medium':
            insights.warnings.append("⚡ MODERATE FLOOD RISK: Some flood concerns during monsoon")
        
        if insights.slope_deg and insights.slope_deg > 10:
            insights.warnings.append(f"🏔️ Hilly terrain: {insights.slope_deg:.1f}° slope")
        
        if insights.water_supply == 'Limited':
            insights.warnings.append("💧 Water supply may be limited in this area")
        
        if insights.metro_count == 0 and insights.bus_stops < 3:
            insights.warnings.append("🚌 Limited public transport connectivity")
    
    def _calculate_livability(self, insights: AreaInsights):
        """Calculate livability score (0-100)."""
        score = 50  # Base score
        
        # Transport bonus
        score += min(15, insights.metro_count * 5 + insights.bus_stops * 0.5)
        
        # Amenities bonus
        score += min(10, insights.schools * 2)
        score += min(5, insights.hospitals * 2.5)
        score += min(5, insights.parks * 2)
        score += min(5, insights.restaurants * 0.2)
        
        # Terrain penalty
        if insights.flood_risk == 'high':
            score -= 15
        elif insights.flood_risk == 'medium':
            score -= 5
        
        # Suitability bonus
        if insights.suitability_score:
            score += (insights.suitability_score - 50) * 0.2
        
        insights.livability_score = max(0, min(100, score))
    
    def _generate_area_summary(self, insights: AreaInsights) -> str:
        """Generate human-readable area summary."""
        parts = []
        
        # Livability
        if insights.livability_score >= 80:
            parts.append("Excellent livability")
        elif insights.livability_score >= 60:
            parts.append("Good livability")
        elif insights.livability_score >= 40:
            parts.append("Moderate livability")
        else:
            parts.append("Basic livability")
        
        # Transport
        if insights.metro_count > 0:
            parts.append(f"{insights.metro_count} metro station(s)")
        if insights.bus_stops > 0:
            parts.append(f"{insights.bus_stops} bus stops")
        
        # Amenities
        amenities = []
        if insights.schools:
            amenities.append(f"{insights.schools} schools")
        if insights.hospitals:
            amenities.append(f"{insights.hospitals} hospitals")
        if amenities:
            parts.append(", ".join(amenities))
        
        # Terrain
        if insights.elevation_m:
            parts.append(f"Elevation: {insights.elevation_m:.0f}m")
        
        return " | ".join(parts)
    
    def get_enriched_property(self, property_id: str) -> Optional[PropertyEnrichedData]:
        """Get enriched property data with all analytics."""
        conn = self._connect()
        cursor = conn.cursor()
        
        try:
            # Get base property data
            cursor.execute("""
                SELECT p.*, pa.metro_proximity_score, pa.school_proximity_score,
                       pa.hospital_proximity_score, pa.investment_score,
                       pa.nearest_metro_distance, pa.nearest_school_distance,
                       pa.nearest_hospital_distance
                FROM properties p
                LEFT JOIN property_analytics pa ON p.property_id = pa.property_id
                WHERE p.property_id = ?
            """, (property_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            data = PropertyEnrichedData(
                property_id=property_id,
                title=row['title'] or '',
                price=row['price'] or 0,
                bedrooms=row['bedrooms'] or 0,
                area_sqft=row['total_area_sqft'] or 0,
                lat=row['latitude'],
                lng=row['longitude'],
                locality=row['locality'] or row['area_name'] or '',
            )
            
            # Parse amenities
            if row['amenities']:
                try:
                    data.amenities = json.loads(row['amenities'])
                except:
                    pass
            
            # Analytics
            data.metro_score = row['metro_proximity_score'] or 0
            data.school_score = row['school_proximity_score'] or 0
            data.hospital_score = row['hospital_proximity_score'] or 0
            data.investment_score = row['investment_score'] or 0
            data.nearest_metro_m = row['nearest_metro_distance'] or 0
            data.nearest_school_m = row['nearest_school_distance'] or 0
            data.nearest_hospital_m = row['nearest_hospital_distance'] or 0
            
            # Add terrain warnings if coordinates available
            if data.lat and data.lng:
                cursor.execute("""
                    SELECT flood_risk, terrain_type, suitability_score
                    FROM terrain_grid
                    ORDER BY ABS(center_lat - ?) + ABS(center_lng - ?)
                    LIMIT 1
                """, (data.lat, data.lng))
                
                terrain = cursor.fetchone()
                if terrain:
                    data.flood_risk = terrain['flood_risk'] or 'unknown'
                    if data.flood_risk == 'high':
                        data.terrain_warnings.append("⚠️ High flood risk area")
                    elif data.flood_risk == 'medium':
                        data.terrain_warnings.append("⚡ Moderate flood risk")
                
                # Get nearby landmarks
                radius_deg = 500 / 111000  # 500m radius
                cursor.execute("""
                    SELECT name FROM buildings
                    WHERE name IS NOT NULL AND name != ''
                    AND latitude BETWEEN ? AND ?
                    AND longitude BETWEEN ? AND ?
                    LIMIT 5
                """, (data.lat - radius_deg, data.lat + radius_deg,
                      data.lng - radius_deg, data.lng + radius_deg))
                
                data.nearby_landmarks = [r['name'] for r in cursor.fetchall()]
            
            return data
            
        finally:
            conn.close()
    
    def search_with_amenities(self, amenity_filter: List[str],
                             lat: float = None, lng: float = None,
                             radius_km: float = 5,
                             limit: int = 20) -> List[Dict]:
        """Search properties by amenities."""
        conn = self._connect()
        cursor = conn.cursor()
        
        try:
            query = "SELECT * FROM properties WHERE amenities IS NOT NULL"
            params = []
            
            # Add amenity filters (check if amenity is in JSON array)
            for amenity in amenity_filter:
                query += f" AND amenities LIKE ?"
                params.append(f"%{amenity}%")
            
            # Add location filter
            if lat and lng:
                radius_deg = radius_km / 111
                query += " AND latitude BETWEEN ? AND ?"
                query += " AND longitude BETWEEN ? AND ?"
                params.extend([lat - radius_deg, lat + radius_deg,
                              lng - radius_deg, lng + radius_deg])
            
            query += f" LIMIT {limit}"
            
            cursor.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'property_id': row['property_id'],
                    'title': row['title'],
                    'price': row['price'],
                    'bedrooms': row['bedrooms'],
                    'locality': row['locality'] or row['area_name'],
                    'amenities': json.loads(row['amenities']) if row['amenities'] else []
                })
            
            return results
            
        finally:
            conn.close()
    
    def get_flood_risk_properties(self, risk_level: str = 'high',
                                  limit: int = 50) -> List[Dict]:
        """Get properties in flood risk areas."""
        conn = self._connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT p.property_id, p.title, p.price, p.latitude, p.longitude,
                       p.locality, t.flood_risk, t.suitability_score
                FROM properties p
                JOIN terrain_grid t ON (
                    ABS(t.center_lat - p.latitude) < 0.005 AND
                    ABS(t.center_lng - p.longitude) < 0.005
                )
                WHERE t.flood_risk = ?
                AND p.latitude IS NOT NULL
                LIMIT ?
            """, (risk_level, limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            conn.close()


# Singleton
_data_service = None


def get_enhanced_data_service() -> EnhancedDataService:
    """Get singleton data service."""
    global _data_service
    if _data_service is None:
        _data_service = EnhancedDataService()
    return _data_service
