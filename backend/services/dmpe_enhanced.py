"""
Enhanced DMPE Engine with GIS Layer Integration
Integrates ward boundaries, land use zones, metro alignments, and other GIS layers
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from sqlalchemy import text
from shapely.geometry import Point
from shapely.wkt import loads as wkt_loads

logger = logging.getLogger(__name__)


class EnhancedDMPE:
    """Enhanced DMPE with full GIS layer integration"""
    
    def __init__(self, base_dmpe=None, spatial_db=None):
        self.base_dmpe = base_dmpe
        self.spatial_db = spatial_db
        self.gis_features_cache = {}
    
    def predict_with_gis(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced prediction with GIS layer features
        """
        # Start with base DMPE prediction if available
        if self.base_dmpe:
            predictions = self.base_dmpe.predict(property_data)
        else:
            predictions = self._base_prediction(property_data)
        
        # Enhance with GIS features
        lat = property_data.get("latitude")
        lon = property_data.get("longitude")
        
        if lat and lon and self.spatial_db:
            gis_features = self._extract_gis_features(lat, lon)
            property_data.update(gis_features)
            
            # Adjust predictions based on GIS features
            predictions = self._adjust_predictions_with_gis(predictions, gis_features)
        
        return predictions
    
    def _extract_gis_features(self, lat: float, lon: float) -> Dict[str, Any]:
        """Extract features from GIS layers for a location"""
        features = {
            "ward_name": None,
            "zone_name": None,
            "land_use_type": None,
            "is_bbmp_area": False,
            "taluk_name": None,
            "distance_to_metro_alignment": None,
            "nearest_metro_station": None,
            "distance_to_water_body": None,
            "distance_to_green_zone": None,
            "building_density": 0,
            "road_density": 0,
            "is_flood_prone": False,
            "development_potential": 0,
            "zoning_category": None,
            "infrastructure_quality": 0
        }
        
        try:
            point_wkt = f"POINT({lon} {lat})"
            
            with self.spatial_db.connect() as conn:
                # Get ward information
                result = conn.execute(text("""
                    SELECT ward_name, zone_name
                    FROM gis_bbmp
                    WHERE ST_Contains(geom, ST_GeomFromText(:point, 4326))
                    LIMIT 1
                """), {"point": point_wkt})
                row = result.fetchone()
                if row:
                    features["ward_name"] = row[0]
                    features["is_bbmp_area"] = True
                
                # Get zone information
                result = conn.execute(text("""
                    SELECT zone_id
                    FROM gis_zone
                    WHERE ST_Contains(geom, ST_GeomFromText(:point, 4326))
                    LIMIT 1
                """), {"point": point_wkt})
                row = result.fetchone()
                if row:
                    features["zone_name"] = f"Zone_{row[0]}"
                
                # Get taluk information
                result = conn.execute(text("""
                    SELECT taluk_name
                    FROM gis_taluk
                    WHERE ST_Contains(geom, ST_GeomFromText(:point, 4326))
                    LIMIT 1
                """), {"point": point_wkt})
                row = result.fetchone()
                if row:
                    features["taluk_name"] = row[0]
                
                # Get land use type from OSM
                result = conn.execute(text("""
                    SELECT fclass
                    FROM gis_gis_osm_landuse_a_free_1
                    WHERE ST_Contains(geom, ST_GeomFromText(:point, 4326))
                    LIMIT 1
                """), {"point": point_wkt})
                row = result.fetchone()
                if row:
                    features["land_use_type"] = self._categorize_land_use(row[0])
                
                # Calculate building density (buildings within 500m)
                result = conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM gis_gis_osm_buildings_a_free_1
                    WHERE ST_DWithin(geom::geography, ST_GeomFromText(:point, 4326)::geography, 500)
                """), {"point": point_wkt})
                building_count = result.scalar() or 0
                features["building_density"] = min(100, building_count / 5)  # Normalize to 0-100
                
                # Calculate road density
                result = conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM gis_gis_osm_roads_free_1
                    WHERE ST_DWithin(geom::geography, ST_GeomFromText(:point, 4326)::geography, 1000)
                """), {"point": point_wkt})
                road_count = result.scalar() or 0
                features["road_density"] = min(100, road_count / 10)  # Normalize to 0-100
                
                # Distance to water body
                result = conn.execute(text("""
                    SELECT MIN(ST_Distance(geom::geography, ST_GeomFromText(:point, 4326)::geography))
                    FROM gis_gis_osm_water_a_free_1
                """), {"point": point_wkt})
                water_dist = result.scalar()
                features["distance_to_water_body"] = water_dist if water_dist else None
                
                # Distance to natural/green areas
                result = conn.execute(text("""
                    SELECT MIN(ST_Distance(geom::geography, ST_GeomFromText(:point, 4326)::geography))
                    FROM gis_gis_osm_natural_a_free_1
                """), {"point": point_wkt})
                green_dist = result.scalar()
                features["distance_to_green_zone"] = green_dist if green_dist else None
                
                # Calculate infrastructure quality score
                features["infrastructure_quality"] = self._calculate_infrastructure_score(features)
                
                # Calculate development potential
                features["development_potential"] = self._calculate_development_potential(features)
                
        except Exception as e:
            logger.error(f"Error extracting GIS features: {e}")
        
        return features
    
    def _categorize_land_use(self, fclass: str) -> str:
        """Categorize OSM land use class"""
        if not fclass:
            return "mixed"
        
        fclass_lower = fclass.lower()
        
        if any(term in fclass_lower for term in ["residential", "housing", "apartment"]):
            return "residential"
        elif any(term in fclass_lower for term in ["commercial", "retail", "shop", "office"]):
            return "commercial"
        elif any(term in fclass_lower for term in ["industrial", "factory", "warehouse"]):
            return "industrial"
        elif any(term in fclass_lower for term in ["park", "forest", "grass", "recreation"]):
            return "green"
        elif any(term in fclass_lower for term in ["education", "school", "university"]):
            return "institutional"
        else:
            return "mixed"
    
    def _calculate_infrastructure_score(self, features: Dict[str, Any]) -> float:
        """Calculate infrastructure quality score based on GIS features"""
        score = 0
        
        # BBMP area bonus
        if features["is_bbmp_area"]:
            score += 20
        
        # Road density contribution
        score += features["road_density"] * 0.3
        
        # Building density (moderate is good)
        if 20 <= features["building_density"] <= 60:
            score += 20
        elif features["building_density"] > 60:
            score += 10
        
        # Proximity to green zones
        if features["distance_to_green_zone"] and features["distance_to_green_zone"] < 2000:
            score += 15
        
        # Land use bonus
        if features["land_use_type"] in ["residential", "commercial"]:
            score += 15
        
        return min(100, score)
    
    def _calculate_development_potential(self, features: Dict[str, Any]) -> float:
        """Calculate development potential based on GIS analysis"""
        potential = 0
        
        # Low building density = high development potential
        if features["building_density"] < 30:
            potential += 30
        
        # Good road connectivity
        if features["road_density"] > 50:
            potential += 25
        
        # BBMP area
        if features["is_bbmp_area"]:
            potential += 20
        
        # Land use suitable for development
        if features["land_use_type"] in ["residential", "commercial", "mixed"]:
            potential += 15
        
        # Not too close to water bodies (building restrictions)
        if features["distance_to_water_body"] and features["distance_to_water_body"] > 500:
            potential += 10
        
        return min(100, potential)
    
    def _adjust_predictions_with_gis(self, predictions: Dict[str, Any], 
                                     gis_features: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust predictions based on GIS features"""
        
        # Adjust price based on zone and infrastructure
        if predictions.get("price"):
            price_multiplier = 1.0
            
            # BBMP area commands premium
            if gis_features["is_bbmp_area"]:
                price_multiplier *= 1.1
            
            # Infrastructure quality adjustment
            infra_score = gis_features["infrastructure_quality"]
            if infra_score > 70:
                price_multiplier *= 1.15
            elif infra_score < 30:
                price_multiplier *= 0.85
            
            # Land use type adjustment
            if gis_features["land_use_type"] == "commercial":
                price_multiplier *= 1.2
            elif gis_features["land_use_type"] == "industrial":
                price_multiplier *= 0.8
            
            predictions["price"]["predicted"] *= price_multiplier
            predictions["price"]["gis_adjusted"] = True
        
        # Adjust demand based on development potential
        if predictions.get("demand_index"):
            demand_adjustment = gis_features["development_potential"] / 100
            predictions["demand_index"]["predicted"] = (
                predictions["demand_index"]["predicted"] * 0.7 +
                gis_features["development_potential"] * 0.3
            )
        
        # Add GIS-specific investment metrics
        predictions["gis_metrics"] = {
            "infrastructure_quality": gis_features["infrastructure_quality"],
            "development_potential": gis_features["development_potential"],
            "location_premium": gis_features["is_bbmp_area"],
            "land_use_category": gis_features["land_use_type"],
            "building_density": gis_features["building_density"],
            "road_connectivity": gis_features["road_density"]
        }
        
        return predictions
    
    def _base_prediction(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Basic prediction when base DMPE is not available"""
        area = property_data.get("area_sqft", 1200)
        bedrooms = property_data.get("bedrooms", 2)
        
        # Simple price estimation
        base_price_per_sqft = 6000
        price = area * base_price_per_sqft
        
        # Adjust for bedrooms
        if bedrooms > 3:
            price *= 1.2
        elif bedrooms < 2:
            price *= 0.85
        
        return {
            "price": {
                "predicted": price,
                "confidence": 0.6,
                "range": [price * 0.9, price * 1.1]
            },
            "rental_yield": {
                "predicted_percentage": 3.5,
                "monthly_rental": price * 0.003
            },
            "demand_index": {
                "predicted": 65,
                "trend": "stable"
            },
            "investment_metrics": {
                "roi_percentage": 8.5,
                "payback_period_years": 12
            }
        }
    
    def analyze_location_with_gis(self, lat: float, lon: float) -> Dict[str, Any]:
        """Comprehensive location analysis using GIS layers"""
        analysis = {
            "location": [lat, lon],
            "gis_features": self._extract_gis_features(lat, lon),
            "nearby_zones": [],
            "accessibility": {},
            "development_status": "",
            "investment_grade": ""
        }
        
        # Analyze nearby zones
        if self.spatial_db:
            try:
                point_wkt = f"POINT({lon} {lat})"
                
                with self.spatial_db.connect() as conn:
                    # Find nearby zones within 2km
                    result = conn.execute(text("""
                        SELECT 
                            zone_id,
                            ST_Distance(geom::geography, ST_GeomFromText(:point, 4326)::geography) as distance
                        FROM gis_zone
                        WHERE ST_DWithin(geom::geography, ST_GeomFromText(:point, 4326)::geography, 2000)
                        ORDER BY distance
                        LIMIT 5
                    """), {"point": point_wkt})
                    
                    for row in result:
                        analysis["nearby_zones"].append({
                            "zone": f"Zone_{row[0]}",
                            "distance_meters": row[1]
                        })
            
            except Exception as e:
                logger.error(f"Error analyzing location: {e}")
        
        # Determine development status
        gis_features = analysis["gis_features"]
        if gis_features["building_density"] < 20:
            analysis["development_status"] = "emerging"
        elif gis_features["building_density"] < 50:
            analysis["development_status"] = "developing"
        elif gis_features["building_density"] < 80:
            analysis["development_status"] = "developed"
        else:
            analysis["development_status"] = "saturated"
        
        # Calculate investment grade
        score = (
            gis_features["infrastructure_quality"] * 0.4 +
            gis_features["development_potential"] * 0.3 +
            (100 if gis_features["is_bbmp_area"] else 50) * 0.3
        )
        
        if score > 80:
            analysis["investment_grade"] = "A+"
        elif score > 70:
            analysis["investment_grade"] = "A"
        elif score > 60:
            analysis["investment_grade"] = "B+"
        elif score > 50:
            analysis["investment_grade"] = "B"
        else:
            analysis["investment_grade"] = "C"
        
        return analysis
