"""
Advanced Prediction Engine with Time-based Forecasting
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import json
import logging
from sqlalchemy import text
from backend.database.multiconnection import mdb
from backend.services.mappls_integration import MapplsService
from backend.services.dmpe_engine import DMPEEngine
import math

logger = logging.getLogger(__name__)

class AdvancedPredictionEngine:
    """
    Advanced prediction engine with temporal forecasting,
    neighborhood analysis, and comprehensive property insights
    """
    
    def __init__(self):
        self.mappls_service = MapplsService()
        self.dmpe_engine = DMPEEngine()
        
        # Growth rates and trends (annual %)
        self.growth_rates = {
            'Whitefield': 12.5,
            'HSR Layout': 11.8,
            'Koramangala': 10.5,
            'Electronic City': 13.2,
            'Marathahalli': 11.2,
            'Indiranagar': 9.8,
            'BTM Layout': 10.2,
            'JP Nagar': 9.5,
            'Hebbal': 14.1,
            'Sarjapur Road': 13.8,
            'default': 10.0
        }
        
        # Infrastructure impact multipliers
        self.infra_multipliers = {
            'metro_station': 1.15,
            'tech_park': 1.12,
            'school': 1.08,
            'hospital': 1.06,
            'mall': 1.10,
            'park': 1.05,
            'highway': 0.95  # Noise factor
        }
        
        # Time-based market cycles
        self.market_cycles = {
            'boom': {'years': [2024, 2025, 2028, 2029], 'multiplier': 1.15},
            'stable': {'years': [2026, 2027], 'multiplier': 1.0},
            'correction': {'years': [2030], 'multiplier': 0.92}
        }
    
    def predict_property_value(self, lat: float, lon: float, months_from_now: int, 
                               property_details: Optional[Dict] = None) -> Dict:
        """
        Predict property value at a specific time point
        """
        try:
            # Get current property value and features
            current_value = self._get_current_value(lat, lon, property_details)
            location_features = self._analyze_location(lat, lon)
            
            # Calculate time-based appreciation
            years = months_from_now / 12.0
            locality = location_features.get('locality', 'default')
            base_growth = self.growth_rates.get(locality, self.growth_rates['default'])
            
            # Apply infrastructure multipliers
            infra_score = location_features.get('infrastructure_score', 1.0)
            growth_rate = base_growth * (1 + (infra_score - 1) * 0.5)
            
            # Apply market cycle adjustments
            future_year = datetime.now().year + int(years)
            cycle_multiplier = self._get_cycle_multiplier(future_year)
            
            # Calculate future value
            if months_from_now >= 0:
                # Future prediction
                future_value = current_value * (1 + growth_rate/100) ** years * cycle_multiplier
                confidence = max(0.95 - abs(years) * 0.05, 0.5)  # Confidence decreases over time
            else:
                # Historical estimation
                future_value = current_value / (1 + growth_rate/100) ** abs(years)
                confidence = 0.85
            
            # Calculate additional metrics
            roi = ((future_value - current_value) / current_value) * 100 if months_from_now > 0 else 0
            monthly_appreciation = (growth_rate * cycle_multiplier) / 12
            
            return {
                'current_value': current_value,
                'predicted_value': future_value,
                'value_change': future_value - current_value,
                'percentage_change': roi,
                'monthly_appreciation': monthly_appreciation,
                'annual_growth_rate': growth_rate,
                'confidence_score': confidence,
                'market_cycle': self._get_market_cycle(future_year),
                'location_features': location_features,
                'prediction_factors': {
                    'base_growth': base_growth,
                    'infrastructure_boost': infra_score,
                    'cycle_adjustment': cycle_multiplier,
                    'time_horizon': f"{abs(months_from_now)} months {'future' if months_from_now > 0 else 'past'}"
                }
            }
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {
                'error': str(e),
                'current_value': 0,
                'predicted_value': 0
            }
    
    def analyze_coordinate(self, lat: float, lon: float) -> Dict:
        """
        Comprehensive analysis of any coordinate in Bangalore
        """
        try:
            # Get location details
            location_features = self._analyze_location(lat, lon)
            
            # Get nearby POIs from Mappls and cache
            nearby_pois = self._get_and_cache_nearby_pois(lat, lon)
            
            # Analyze property density and pricing
            property_analysis = self._analyze_nearby_properties(lat, lon)
            
            # Calculate importance score
            importance_score = self._calculate_importance_score(
                location_features, nearby_pois, property_analysis
            )
            
            # Generate investment insights
            investment_insights = self._generate_investment_insights(
                location_features, property_analysis, importance_score
            )
            
            # Predict future potential
            future_potential = self._predict_future_potential(lat, lon, location_features)
            
            return {
                'coordinates': {'lat': lat, 'lon': lon},
                'locality': location_features.get('locality', 'Unknown'),
                'zone': location_features.get('zone', 'Unknown'),
                'importance_score': importance_score,
                'location_features': location_features,
                'nearby_pois': nearby_pois,
                'property_analysis': property_analysis,
                'investment_insights': investment_insights,
                'future_potential': future_potential,
                'recommendations': self._generate_recommendations(importance_score, investment_insights),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Coordinate analysis error: {e}")
            return {'error': str(e)}
    
    def analyze_property_click(self, property_id: str) -> Dict:
        """
        Comprehensive analysis when a property is clicked on the map
        """
        try:
            with mdb.spatial() as session:
                # Get property details
                result = session.execute(text("""
                    SELECT 
                        property_id,
                        ST_Y(location) as lat,
                        ST_X(location) as lon,
                        city,
                        locality
                    FROM property_locations
                    WHERE property_id = :pid
                """), {'pid': property_id})
                
                property_data = result.fetchone()
                if not property_data:
                    return {'error': 'Property not found'}
                
                lat, lon = property_data[1], property_data[2]
                
                # Get comprehensive analysis
                coord_analysis = self.analyze_coordinate(lat, lon)
                
                # Add property-specific insights
                property_insights = {
                    'property_id': property_id,
                    'location': {'lat': lat, 'lon': lon},
                    'city': property_data[3],
                    'locality': property_data[4],
                    **coord_analysis,
                    'price_trends': self._get_price_trends(lat, lon),
                    'comparable_properties': self._find_comparable_properties(lat, lon, property_id),
                    'investment_score': self._calculate_investment_score(coord_analysis),
                    'rental_yield_estimate': self._estimate_rental_yield(coord_analysis)
                }
                
                return property_insights
                
        except Exception as e:
            logger.error(f"Property analysis error: {e}")
            return {'error': str(e)}
    
    def forecast_area_trends(self, area_name: str, months_ahead: int = 60) -> Dict:
        """
        Forecast trends for an entire area
        """
        try:
            trends = []
            current_date = datetime.now()
            
            for month in range(0, months_ahead + 1, 6):  # 6-month intervals
                future_date = current_date + timedelta(days=month * 30)
                
                # Calculate predicted metrics
                growth_rate = self.growth_rates.get(area_name, self.growth_rates['default'])
                years = month / 12.0
                
                # Price prediction
                price_multiplier = (1 + growth_rate/100) ** years
                
                # Demand prediction (cyclical with growth)
                demand_score = 70 + 20 * math.sin(month/6) + years * 5
                demand_score = min(100, max(0, demand_score))
                
                # Supply prediction
                supply_score = 50 + years * 8  # Increasing supply over time
                supply_score = min(100, max(0, supply_score))
                
                # Investment score
                investment_score = (demand_score * 0.4 + (100 - supply_score) * 0.3 + 
                                  growth_rate * 2 + 10)
                investment_score = min(100, max(0, investment_score))
                
                trends.append({
                    'month': month,
                    'date': future_date.strftime('%Y-%m'),
                    'price_index': price_multiplier * 100,
                    'demand_score': demand_score,
                    'supply_score': supply_score,
                    'investment_score': investment_score,
                    'growth_rate': growth_rate,
                    'market_sentiment': self._get_market_sentiment(investment_score)
                })
            
            return {
                'area': area_name,
                'forecast_period': f"{months_ahead} months",
                'trends': trends,
                'summary': {
                    'expected_appreciation': f"{(trends[-1]['price_index'] - 100):.1f}%",
                    'avg_investment_score': np.mean([t['investment_score'] for t in trends]),
                    'recommendation': self._get_area_recommendation(trends)
                }
            }
            
        except Exception as e:
            logger.error(f"Forecast error: {e}")
            return {'error': str(e)}
    
    def _analyze_location(self, lat: float, lon: float) -> Dict:
        """
        Analyze location features using GIS data
        """
        try:
            with mdb.spatial() as session:
                # Get zone and ward information
                zone_result = session.execute(text("""
                    SELECT zone_name 
                    FROM gis_zone 
                    WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                    LIMIT 1
                """), {'lat': lat, 'lon': lon})
                
                zone = zone_result.scalar() or 'Unknown'
                
                # Get infrastructure count within 2km
                infra_result = session.execute(text("""
                    SELECT 
                        COUNT(CASE WHEN amenity = 'school' THEN 1 END) as schools,
                        COUNT(CASE WHEN amenity = 'hospital' THEN 1 END) as hospitals,
                        COUNT(CASE WHEN amenity = 'restaurant' THEN 1 END) as restaurants,
                        COUNT(CASE WHEN amenity = 'bank' THEN 1 END) as banks
                    FROM gis_osm_pois
                    WHERE ST_DWithin(
                        geom::geography,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        2000
                    )
                """), {'lat': lat, 'lon': lon})
                
                infra = infra_result.fetchone() or (0, 0, 0, 0)
                
                # Calculate infrastructure score
                infra_score = min(100, (
                    infra[0] * 10 +  # schools
                    infra[1] * 8 +   # hospitals
                    infra[2] * 2 +   # restaurants
                    infra[3] * 5     # banks
                ))
                
                # Determine locality (simplified)
                locality = self._get_locality_name(lat, lon)
                
                return {
                    'zone': zone,
                    'locality': locality,
                    'infrastructure_score': infra_score / 100,
                    'amenities': {
                        'schools': infra[0],
                        'hospitals': infra[1],
                        'restaurants': infra[2],
                        'banks': infra[3]
                    }
                }
                
        except Exception as e:
            logger.error(f"Location analysis error: {e}")
            return {
                'zone': 'Unknown',
                'locality': 'Unknown',
                'infrastructure_score': 1.0
            }
    
    def _get_and_cache_nearby_pois(self, lat: float, lon: float) -> List[Dict]:
        """
        Get nearby POIs from Mappls and cache them
        """
        try:
            # Get POIs from Mappls
            pois = self.mappls_service.get_nearby_pois(lat, lon, radius=2000)
            
            # Cache POIs in database
            if pois and len(pois) > 0:
                with mdb.spatial() as session:
                    for poi in pois[:20]:  # Limit to 20 POIs
                        # Check if POI already exists
                        exists = session.execute(text("""
                            SELECT 1 FROM pois 
                            WHERE name = :name 
                            AND ST_DWithin(location::geography, 
                                         ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, 
                                         50)
                        """), {
                            'name': poi.get('name', 'Unknown'),
                            'lat': poi.get('lat', lat),
                            'lon': poi.get('lon', lon)
                        }).scalar()
                        
                        if not exists:
                            # Insert new POI
                            session.execute(text("""
                                INSERT INTO pois (name, category, location, address, created_at)
                                VALUES (:name, :category, 
                                       ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                                       :address, NOW())
                            """), {
                                'name': poi.get('name', 'Unknown'),
                                'category': poi.get('category', 'general'),
                                'lat': poi.get('lat', lat),
                                'lon': poi.get('lon', lon),
                                'address': poi.get('address', '')
                            })
                    
                    session.commit()
                    logger.info(f"Cached {len(pois)} POIs for location ({lat}, {lon})")
            
            return pois[:10] if pois else []
            
        except Exception as e:
            logger.error(f"POI caching error: {e}")
            return []
    
    def _analyze_nearby_properties(self, lat: float, lon: float, radius: int = 1000) -> Dict:
        """
        Analyze properties within radius
        """
        try:
            with mdb.spatial() as session:
                result = session.execute(text("""
                    SELECT 
                        COUNT(*) as total_properties,
                        AVG(ST_Distance(location::geography, 
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)) as avg_distance
                    FROM property_locations
                    WHERE ST_DWithin(
                        location::geography,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        :radius
                    )
                """), {'lat': lat, 'lon': lon, 'radius': radius})
                
                data = result.fetchone()
                
                return {
                    'property_count': data[0] if data else 0,
                    'property_density': (data[0] / (3.14 * (radius/1000) ** 2)) if data and data[0] > 0 else 0,
                    'avg_distance': data[1] if data and data[1] else 0
                }
                
        except Exception as e:
            logger.error(f"Property analysis error: {e}")
            return {
                'property_count': 0,
                'property_density': 0,
                'avg_distance': 0
            }
    
    def _calculate_importance_score(self, location_features: Dict, 
                                   nearby_pois: List, 
                                   property_analysis: Dict) -> float:
        """
        Calculate importance score for a location
        """
        score = 0
        
        # Infrastructure contribution (40%)
        score += location_features.get('infrastructure_score', 0) * 40
        
        # POI density contribution (20%)
        poi_score = min(100, len(nearby_pois) * 10)
        score += poi_score * 0.2
        
        # Property density contribution (20%)
        density_score = min(100, property_analysis.get('property_density', 0) * 10)
        score += density_score * 0.2
        
        # Zone importance (20%)
        zone = location_features.get('zone', 'Unknown')
        zone_scores = {
            'Central': 100,
            'East': 85,
            'South': 90,
            'North': 80,
            'West': 75,
            'Unknown': 50
        }
        score += zone_scores.get(zone, 50) * 0.2
        
        return min(100, max(0, score))
    
    def _generate_investment_insights(self, location_features: Dict, 
                                     property_analysis: Dict, 
                                     importance_score: float) -> Dict:
        """
        Generate investment insights
        """
        insights = {
            'investment_grade': self._get_investment_grade(importance_score),
            'key_strengths': [],
            'key_weaknesses': [],
            'opportunities': [],
            'risks': []
        }
        
        # Analyze strengths
        if location_features.get('infrastructure_score', 0) > 0.7:
            insights['key_strengths'].append('Excellent infrastructure')
        if property_analysis.get('property_density', 0) > 50:
            insights['key_strengths'].append('High development activity')
        if importance_score > 80:
            insights['key_strengths'].append('Prime location')
        
        # Analyze weaknesses
        if location_features.get('infrastructure_score', 0) < 0.3:
            insights['key_weaknesses'].append('Poor infrastructure')
        if property_analysis.get('property_count', 0) < 10:
            insights['key_weaknesses'].append('Low market activity')
        
        # Opportunities
        if importance_score > 60 and property_analysis.get('property_density', 0) < 30:
            insights['opportunities'].append('Emerging area with growth potential')
        if location_features.get('zone') in ['East', 'North']:
            insights['opportunities'].append('Upcoming development corridor')
        
        # Risks
        if importance_score < 40:
            insights['risks'].append('Low appreciation potential')
        if property_analysis.get('property_density', 0) > 100:
            insights['risks'].append('Market saturation risk')
        
        return insights
    
    def _predict_future_potential(self, lat: float, lon: float, 
                                 location_features: Dict) -> Dict:
        """
        Predict future potential of the area
        """
        locality = location_features.get('locality', 'default')
        growth_rate = self.growth_rates.get(locality, self.growth_rates['default'])
        
        # Calculate potential scores
        potential = {
            '1_year': growth_rate,
            '3_years': growth_rate * 3 * 0.95,  # Slight decay
            '5_years': growth_rate * 5 * 0.9,   # More decay
            'development_probability': min(100, 50 + location_features.get('infrastructure_score', 0) * 30),
            'investment_horizon': 'Long-term' if growth_rate > 11 else 'Medium-term'
        }
        
        return potential
    
    def _generate_recommendations(self, importance_score: float, 
                                 investment_insights: Dict) -> List[str]:
        """
        Generate actionable recommendations
        """
        recommendations = []
        
        if importance_score > 80:
            recommendations.append("Excellent location for immediate investment")
        elif importance_score > 60:
            recommendations.append("Good location for medium-term investment")
        else:
            recommendations.append("Consider for long-term investment only")
        
        if len(investment_insights.get('key_strengths', [])) > 2:
            recommendations.append("Strong fundamentals support price appreciation")
        
        if len(investment_insights.get('opportunities', [])) > 0:
            recommendations.append("Monitor upcoming developments in the area")
        
        if len(investment_insights.get('risks', [])) > 1:
            recommendations.append("Exercise caution and conduct thorough due diligence")
        
        return recommendations
    
    def _get_current_value(self, lat: float, lon: float, 
                          property_details: Optional[Dict] = None) -> float:
        """
        Estimate current property value
        """
        # Base price per sqft for Bangalore
        base_price = 6500
        
        # Adjust based on location
        location_multiplier = 1.0
        
        # Use property details if provided
        if property_details:
            area_sqft = property_details.get('area_sqft', 1200)
            return base_price * area_sqft * location_multiplier
        
        # Default estimate
        return base_price * 1200 * location_multiplier  # Assume 1200 sqft
    
    def _get_cycle_multiplier(self, year: int) -> float:
        """
        Get market cycle multiplier for a given year
        """
        for cycle_type, cycle_data in self.market_cycles.items():
            if year in cycle_data['years']:
                return cycle_data['multiplier']
        return 1.0
    
    def _get_market_cycle(self, year: int) -> str:
        """
        Get market cycle name for a given year
        """
        for cycle_type, cycle_data in self.market_cycles.items():
            if year in cycle_data['years']:
                return cycle_type
        return 'stable'
    
    def _get_locality_name(self, lat: float, lon: float) -> str:
        """
        Get locality name from coordinates
        """
        # Simplified locality detection based on coordinates
        localities = {
            (12.9716, 77.5946): 'Whitefield',
            (12.9121, 77.6446): 'HSR Layout',
            (12.9352, 77.6245): 'Koramangala',
            (12.8468, 77.6616): 'Electronic City',
            (12.9568, 77.7012): 'Marathahalli',
            (12.9783, 77.6408): 'Indiranagar',
            (12.9165, 77.6101): 'BTM Layout',
            (12.9226, 77.5870): 'JP Nagar',
            (13.0358, 77.5970): 'Hebbal',
            (12.9044, 77.6992): 'Sarjapur Road'
        }
        
        # Find nearest locality
        min_dist = float('inf')
        nearest_locality = 'Unknown'
        
        for coords, name in localities.items():
            dist = math.sqrt((lat - coords[0])**2 + (lon - coords[1])**2)
            if dist < min_dist:
                min_dist = dist
                nearest_locality = name
        
        return nearest_locality if min_dist < 0.05 else 'Bangalore'
    
    def _get_price_trends(self, lat: float, lon: float) -> Dict:
        """
        Get historical price trends
        """
        # Simulated trends
        return {
            'last_year': '+8.5%',
            'last_3_years': '+28.2%',
            'last_5_years': '+52.1%',
            'trend': 'upward'
        }
    
    def _find_comparable_properties(self, lat: float, lon: float, 
                                   property_id: str) -> List[Dict]:
        """
        Find comparable properties nearby
        """
        try:
            with mdb.spatial() as session:
                result = session.execute(text("""
                    SELECT 
                        property_id,
                        ST_Y(location) as lat,
                        ST_X(location) as lon,
                        ST_Distance(location::geography, 
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) as distance
                    FROM property_locations
                    WHERE property_id != :pid
                    AND ST_DWithin(
                        location::geography,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        500
                    )
                    ORDER BY distance
                    LIMIT 5
                """), {'lat': lat, 'lon': lon, 'pid': property_id})
                
                comparables = []
                for row in result:
                    comparables.append({
                        'property_id': row[0],
                        'distance': f"{row[3]:.0f}m",
                        'similarity_score': max(0, 100 - row[3]/5)
                    })
                
                return comparables
                
        except Exception as e:
            logger.error(f"Comparable properties error: {e}")
            return []
    
    def _calculate_investment_score(self, analysis: Dict) -> float:
        """
        Calculate investment score
        """
        importance = analysis.get('importance_score', 50)
        future = analysis.get('future_potential', {}).get('1_year', 10)
        
        score = importance * 0.6 + future * 3
        return min(100, max(0, score))
    
    def _estimate_rental_yield(self, analysis: Dict) -> float:
        """
        Estimate rental yield
        """
        importance = analysis.get('importance_score', 50)
        base_yield = 3.5  # Base rental yield %
        
        # Adjust based on importance
        if importance > 80:
            return base_yield + 1.5
        elif importance > 60:
            return base_yield + 0.8
        else:
            return base_yield
    
    def _get_investment_grade(self, score: float) -> str:
        """
        Get investment grade
        """
        if score >= 90:
            return 'AAA'
        elif score >= 80:
            return 'AA'
        elif score >= 70:
            return 'A'
        elif score >= 60:
            return 'BBB'
        elif score >= 50:
            return 'BB'
        else:
            return 'B'
    
    def _get_market_sentiment(self, score: float) -> str:
        """
        Get market sentiment
        """
        if score >= 80:
            return 'Very Bullish'
        elif score >= 65:
            return 'Bullish'
        elif score >= 50:
            return 'Neutral'
        elif score >= 35:
            return 'Bearish'
        else:
            return 'Very Bearish'
    
    def _get_area_recommendation(self, trends: List[Dict]) -> str:
        """
        Get area recommendation based on trends
        """
        avg_score = np.mean([t['investment_score'] for t in trends])
        
        if avg_score >= 75:
            return 'Strong Buy'
        elif avg_score >= 60:
            return 'Buy'
        elif avg_score >= 45:
            return 'Hold'
        elif avg_score >= 30:
            return 'Sell'
        else:
            return 'Strong Sell'
