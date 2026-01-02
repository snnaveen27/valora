"""
Geospatial Agent for Valora AI
Handles polygon/polyline drawing, spatial analysis, and GIS layer integration
"""

import json
import logging
from typing import Dict, List, Any, Tuple, Optional
from shapely.geometry import Point, Polygon, LineString, MultiPolygon
from shapely.ops import transform
import geopandas as gpd
from sqlalchemy import text
import numpy as np
from geopy.distance import geodesic

logger = logging.getLogger(__name__)


class GeospatialAgent:
    """Agent specialized in geospatial analysis and polygon drawing"""
    
    def __init__(self, db_engine=None):
        self.db_engine = db_engine
        self.gis_layers = {}
        self._load_gis_layers()
    
    def _load_gis_layers(self):
        """Load available GIS layers from PostGIS"""
        if not self.db_engine:
            return
        
        try:
            with self.db_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema='public' 
                    AND table_name LIKE 'gis_%'
                """))
                for row in result:
                    self.gis_layers[row[0]] = True
                logger.info(f"Loaded {len(self.gis_layers)} GIS layers")
        except Exception as e:
            logger.error(f"Error loading GIS layers: {e}")
    
    def interpret_drawing_command(self, command: str) -> Dict[str, Any]:
        """
        Interpret natural language drawing commands
        Examples:
        - "Draw a polygon around Whitefield"
        - "Create 2km buffer around Manyata Tech Park"
        - "Show catchment area within 5km of Koramangala"
        - "Mark investment zone between HSR Layout and BTM"
        """
        command_lower = command.lower()
        
        # Detect drawing type
        if any(word in command_lower for word in ["polygon", "boundary", "area", "zone"]):
            draw_type = "polygon"
        elif any(word in command_lower for word in ["line", "route", "path", "road"]):
            draw_type = "polyline"
        elif any(word in command_lower for word in ["buffer", "radius", "catchment", "within"]):
            draw_type = "buffer"
        elif any(word in command_lower for word in ["circle", "around"]):
            draw_type = "circle"
        else:
            draw_type = "polygon"  # default
        
        # Extract location references
        locations = self._extract_locations(command)
        
        # Extract distance/radius if mentioned
        radius = self._extract_distance(command)
        
        # Determine purpose/category
        purpose = self._determine_purpose(command)
        
        return {
            "type": draw_type,
            "locations": locations,
            "radius_meters": radius,
            "purpose": purpose,
            "original_command": command,
            "suggested_actions": self._suggest_actions(draw_type, purpose)
        }
    
    def _extract_locations(self, command: str) -> List[str]:
        """Extract location names from command"""
        # Known Bangalore localities (extend this list)
        localities = [
            "whitefield", "koramangala", "indiranagar", "btm", "hsr layout",
            "electronic city", "marathahalli", "hebbal", "yelahanka", "jp nagar",
            "jayanagar", "malleswaram", "rajajinagar", "mg road", "brigade road",
            "manyata tech park", "bagmane tech park", "ecospace", "ub city",
            "forum mall", "phoenix marketcity", "orion mall", "mantri mall"
        ]
        
        found_locations = []
        command_lower = command.lower()
        for locality in localities:
            if locality in command_lower:
                found_locations.append(locality.title())
        
        return found_locations
    
    def _extract_distance(self, command: str) -> Optional[float]:
        """Extract distance/radius from command"""
        import re
        
        # Look for patterns like "2km", "500m", "3 kilometers"
        patterns = [
            r'(\d+(?:\.\d+)?)\s*km',
            r'(\d+(?:\.\d+)?)\s*kilometer',
            r'(\d+(?:\.\d+)?)\s*m\b',
            r'(\d+(?:\.\d+)?)\s*meter'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, command.lower())
            if match:
                value = float(match.group(1))
                if 'km' in pattern or 'kilometer' in pattern:
                    return value * 1000  # Convert to meters
                else:
                    return value
        
        return None
    
    def _determine_purpose(self, command: str) -> str:
        """Determine the purpose of the drawing"""
        command_lower = command.lower()
        
        if any(word in command_lower for word in ["investment", "invest", "opportunity"]):
            return "investment_zone"
        elif any(word in command_lower for word in ["catchment", "coverage", "service"]):
            return "catchment_area"
        elif any(word in command_lower for word in ["property", "plot", "land", "site"]):
            return "property_boundary"
        elif any(word in command_lower for word in ["compare", "versus", "vs", "between"]):
            return "comparison"
        elif any(word in command_lower for word in ["flood", "risk", "hazard"]):
            return "risk_zone"
        elif any(word in command_lower for word in ["green", "park", "nature"]):
            return "green_zone"
        else:
            return "analysis"
    
    def _suggest_actions(self, draw_type: str, purpose: str) -> List[str]:
        """Suggest follow-up actions based on drawing type and purpose"""
        actions = []
        
        if purpose == "investment_zone":
            actions.extend([
                "analyze_property_prices",
                "calculate_roi",
                "find_growth_trends",
                "identify_upcoming_projects"
            ])
        elif purpose == "catchment_area":
            actions.extend([
                "count_properties",
                "analyze_demographics",
                "find_amenities",
                "calculate_accessibility_score"
            ])
        elif purpose == "property_boundary":
            actions.extend([
                "get_property_details",
                "calculate_area",
                "check_zoning",
                "find_nearby_pois"
            ])
        
        return actions
    
    def create_polygon(self, points: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Create a polygon from coordinates and analyze it"""
        if len(points) < 3:
            return {"error": "Need at least 3 points for a polygon"}
        
        polygon = Polygon(points)
        
        # Calculate properties
        area_sqm = self._calculate_geodesic_area(polygon)
        perimeter_m = self._calculate_geodesic_perimeter(polygon)
        centroid = polygon.centroid
        
        # Find intersecting GIS layers
        intersections = self._find_layer_intersections(polygon)
        
        # Analyze properties within polygon
        properties_analysis = self._analyze_properties_in_polygon(polygon)
        
        return {
            "type": "polygon",
            "coordinates": points,
            "area_sqm": area_sqm,
            "area_acres": area_sqm / 4047,
            "perimeter_m": perimeter_m,
            "centroid": [centroid.y, centroid.x],
            "intersecting_layers": intersections,
            "properties_analysis": properties_analysis,
            "geojson": {
                "type": "Polygon",
                "coordinates": [points]
            }
        }
    
    def create_buffer(self, center: Tuple[float, float], radius_meters: float) -> Dict[str, Any]:
        """Create a buffer/circle around a point"""
        point = Point(center[1], center[0])  # lon, lat
        
        # Create buffer polygon (approximate)
        num_points = 64
        angles = np.linspace(0, 2 * np.pi, num_points)
        buffer_points = []
        
        for angle in angles:
            # Calculate point at distance and bearing
            bearing = np.degrees(angle)
            dest = geodesic(meters=radius_meters).destination(
                (center[0], center[1]), bearing
            )
            buffer_points.append((dest.longitude, dest.latitude))
        
        buffer_polygon = Polygon(buffer_points)
        
        # Analyze
        properties_analysis = self._analyze_properties_in_polygon(buffer_polygon)
        
        return {
            "type": "buffer",
            "center": center,
            "radius_meters": radius_meters,
            "area_sqm": np.pi * radius_meters ** 2,
            "properties_analysis": properties_analysis,
            "geojson": {
                "type": "Polygon",
                "coordinates": [[(p[1], p[0]) for p in buffer_points]]  # Convert to lat,lon
            }
        }
    
    def _calculate_geodesic_area(self, polygon: Polygon) -> float:
        """Calculate geodesic area of polygon in square meters"""
        coords = list(polygon.exterior.coords)
        if len(coords) < 3:
            return 0
        
        # Simplified area calculation
        # For more accuracy, use pyproj or geopy
        lat_center = np.mean([c[1] for c in coords])
        lon_to_m = 111320.0 * np.cos(np.radians(lat_center))
        lat_to_m = 110540.0
        
        # Convert to meters
        coords_m = [(c[0] * lon_to_m, c[1] * lat_to_m) for c in coords]
        polygon_m = Polygon(coords_m)
        
        return polygon_m.area
    
    def _calculate_geodesic_perimeter(self, polygon: Polygon) -> float:
        """Calculate geodesic perimeter in meters"""
        coords = list(polygon.exterior.coords)
        perimeter = 0
        
        for i in range(len(coords) - 1):
            p1 = (coords[i][1], coords[i][0])  # lat, lon
            p2 = (coords[i + 1][1], coords[i + 1][0])
            perimeter += geodesic(p1, p2).meters
        
        return perimeter
    
    def _find_layer_intersections(self, polygon: Polygon) -> Dict[str, Any]:
        """Find GIS layers that intersect with the polygon"""
        intersections = {}
        
        if not self.db_engine:
            return intersections
        
        try:
            # Convert polygon to WKT
            wkt = polygon.wkt
            
            # Check key layers
            key_layers = ['gis_zone', 'gis_bbmp', 'gis_taluk', 'gis_town']
            
            with self.db_engine.connect() as conn:
                for layer in key_layers:
                    if layer not in self.gis_layers:
                        continue
                    
                    try:
                        result = conn.execute(text(f"""
                            SELECT COUNT(*) as count,
                                   ST_Area(ST_Intersection(geom, ST_GeomFromText(:wkt, 4326))) as intersection_area
                            FROM {layer}
                            WHERE ST_Intersects(geom, ST_GeomFromText(:wkt, 4326))
                        """), {"wkt": wkt})
                        
                        row = result.fetchone()
                        if row and row[0] > 0:
                            intersections[layer] = {
                                "count": row[0],
                                "intersection_area": row[1]
                            }
                    except Exception as e:
                        logger.warning(f"Error checking layer {layer}: {e}")
        
        except Exception as e:
            logger.error(f"Error finding layer intersections: {e}")
        
        return intersections
    
    def _analyze_properties_in_polygon(self, polygon: Polygon) -> Dict[str, Any]:
        """Analyze properties within a polygon"""
        analysis = {
            "total_properties": 0,
            "avg_price_per_sqft": 0,
            "price_range": {"min": 0, "max": 0},
            "property_types": {},
            "top_localities": [],
            "amenities_score": 0,
            "infrastructure_score": 0,
            "investment_potential": 0
        }
        
        if not self.db_engine:
            return analysis
        
        try:
            wkt = polygon.wkt
            
            with self.db_engine.connect() as conn:
                # Count properties in polygon
                result = conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM property_locations
                    WHERE ST_Within(location::geometry, ST_GeomFromText(:wkt, 4326))
                """), {"wkt": wkt})
                
                count = result.scalar()
                analysis["total_properties"] = count or 0
                
                # Get POI density
                result = conn.execute(text("""
                    SELECT 
                        category,
                        COUNT(*) as count
                    FROM pois
                    WHERE ST_Within(location::geometry, ST_GeomFromText(:wkt, 4326))
                    GROUP BY category
                """), {"wkt": wkt})
                
                poi_counts = {}
                for row in result:
                    poi_counts[row[0]] = row[1]
                
                # Calculate scores
                if poi_counts:
                    analysis["amenities_score"] = min(100, sum([
                        poi_counts.get('mall', 0) * 10,
                        poi_counts.get('hospital', 0) * 8,
                        poi_counts.get('school', 0) * 5
                    ]))
                    
                    analysis["infrastructure_score"] = min(100, sum([
                        poi_counts.get('metro', 0) * 15,
                        poi_counts.get('railway', 0) * 10,
                        poi_counts.get('airport', 0) * 5
                    ]))
                
                # Investment potential (simplified)
                analysis["investment_potential"] = (
                    analysis["amenities_score"] * 0.3 +
                    analysis["infrastructure_score"] * 0.5 +
                    min(100, analysis["total_properties"] / 10) * 0.2
                )
        
        except Exception as e:
            logger.error(f"Error analyzing properties in polygon: {e}")
        
        return analysis
    
    def suggest_optimal_zones(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest optimal zones based on criteria"""
        suggestions = []
        
        # Example criteria: budget, property_type, purpose, min_area
        budget = criteria.get("budget", {})
        property_type = criteria.get("property_type", "residential")
        purpose = criteria.get("purpose", "investment")
        
        # Query GIS layers and properties to find optimal zones
        if self.db_engine:
            try:
                with self.db_engine.connect() as conn:
                    # Find zones with good metrics
                    result = conn.execute(text("""
                        SELECT 
                            z.id,
                            ST_AsGeoJSON(z.geom) as geometry,
                            ST_Area(z.geom::geography) as area_sqm,
                            COUNT(DISTINCT p.property_id) as property_count,
                            AVG(f.infrastructure_score) as avg_infra_score
                        FROM gis_zone z
                        LEFT JOIN property_locations p ON ST_Contains(z.geom, p.location::geometry)
                        LEFT JOIN property_spatial_features f ON p.property_id = f.property_id
                        GROUP BY z.id, z.geom
                        HAVING COUNT(p.property_id) > 0
                        ORDER BY avg_infra_score DESC NULLS LAST
                        LIMIT 5
                    """))
                    
                    for row in result:
                        suggestions.append({
                            "zone_id": row[0],
                            "geometry": json.loads(row[1]) if row[1] else None,
                            "area_sqm": row[2],
                            "property_count": row[3],
                            "infrastructure_score": row[4] or 0,
                            "recommendation_score": self._calculate_recommendation_score(
                                row[4] or 0, row[3], purpose
                            )
                        })
            
            except Exception as e:
                logger.error(f"Error suggesting zones: {e}")
        
        return sorted(suggestions, key=lambda x: x.get("recommendation_score", 0), reverse=True)
    
    def _calculate_recommendation_score(self, infra_score: float, property_count: int, purpose: str) -> float:
        """Calculate recommendation score for a zone"""
        base_score = infra_score
        
        if purpose == "investment":
            # For investment, moderate property count is good (not too saturated)
            if 10 <= property_count <= 50:
                base_score += 20
            elif property_count < 10:
                base_score += 10  # Emerging area
            else:
                base_score -= 10  # Might be saturated
        
        elif purpose == "residential":
            # For residential, good infrastructure is key
            base_score *= 1.5
        
        elif purpose == "commercial":
            # For commercial, high density areas are better
            if property_count > 50:
                base_score += 30
        
        return min(100, base_score)
    
    def compare_zones(self, polygons: List[Polygon]) -> Dict[str, Any]:
        """Compare multiple zones/polygons"""
        comparison = {
            "zones": [],
            "best_for_investment": None,
            "best_for_residential": None,
            "best_infrastructure": None,
            "summary": {}
        }
        
        for i, polygon in enumerate(polygons):
            zone_analysis = self._analyze_properties_in_polygon(polygon)
            zone_analysis["zone_id"] = i + 1
            zone_analysis["area_sqm"] = self._calculate_geodesic_area(polygon)
            comparison["zones"].append(zone_analysis)
        
        # Determine best zones
        if comparison["zones"]:
            comparison["best_for_investment"] = max(
                comparison["zones"], 
                key=lambda x: x.get("investment_potential", 0)
            )["zone_id"]
            
            comparison["best_infrastructure"] = max(
                comparison["zones"],
                key=lambda x: x.get("infrastructure_score", 0)
            )["zone_id"]
            
            comparison["best_for_residential"] = max(
                comparison["zones"],
                key=lambda x: x.get("amenities_score", 0) + x.get("infrastructure_score", 0)
            )["zone_id"]
        
        return comparison
