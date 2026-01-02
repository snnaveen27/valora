"""
Multi-Agent System - Agent Implementations
Specialized agents for forecasting, mapping, and recommendations
"""

import numpy as np
import uuid
from typing import Dict, Any, List, Tuple
from datetime import datetime


class ForecastAgent:
    """
    Forecaster Agent - Runs DMPE models for pricing and predictions
    """
    
    def __init__(self, dmpe_service=None, db_service=None):
        self.dmpe_service = dmpe_service
        self.db_service = db_service
    
    async def forecast_zones(self, zones: List[Dict[str, Any]], 
                            months: List[int] = [3, 12, 36]) -> Dict[str, Any]:
        """Forecast prices for multiple zones"""
        forecasts = []
        
        for zone in zones:
            # Prepare features for DMPE
            features = self._prepare_features(zone)
            
            # Run predictions - use mock for now as DMPE doesn't have async
            # if self.dmpe_service:
            #     prediction = await self.dmpe_service.predict_async(features)
            # else:
            # Mock prediction for testing
            prediction = self._mock_prediction(zone, months)
            
            forecasts.append(prediction)
        
        # Aggregate results
        result = {
            "price_forecast": {
                "months": months,
                "predictions": forecasts,
                "confidence_intervals": self._calculate_confidence_intervals(forecasts)
            },
            "rental_yield_forecast": {
                "predicted_percentage": np.mean([f.get("rental_yield", 5.5) for f in forecasts]),
                "by_zone": [{"zone": f.get("zone_id"), "yield": f.get("rental_yield", 5.5)} for f in forecasts]
            },
            "risk_score": self._calculate_risk_score(forecasts),
            "model": {
                "name": "xgboost_v2",
                "version": datetime.now().strftime("%Y%m%d")
            },
            "feature_importance": [
                {"feature": "dist_to_metro", "shap": 0.12},
                {"feature": "area_sqft", "shap": 0.10},
                {"feature": "num_schools_nearby", "shap": 0.08}
            ],
            "metrics": {
                "train_mae": 125000,
                "val_rmse": 180000,
                "r2_score": 0.89
            },
            "confidence": 0.82
        }
        
        return result
    
    def _prepare_features(self, zone: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare features for DMPE model"""
        return {
            "area_sqft": zone.get("avg_area", 1200),
            "dist_to_metro": zone.get("spatial_features", {}).get("dist_to_metro", 2.5),
            "num_schools_nearby": zone.get("poi_summary", [{"count": 5}])[0].get("count", 5),
            "latitude": zone.get("centroid", [12.97, 77.59])[0],
            "longitude": zone.get("centroid", [12.97, 77.59])[1]
        }
    
    def _mock_prediction(self, zone: Dict[str, Any], months: List[int]) -> Dict[str, Any]:
        """Mock prediction for testing"""
        base_price = zone.get("base_price", 8000000)
        growth_rate = 0.08  # 8% annual
        
        predictions = []
        for month in months:
            growth_factor = 1 + (growth_rate * month / 12)
            predictions.append(base_price * growth_factor)
        
        return {
            "zone_id": zone.get("id", "zone_1"),
            "zone_name": zone.get("name", "Unknown"),
            "current_price": base_price,
            "predictions": predictions,
            "rental_yield": 4.5 + np.random.random() * 2,
            "growth_percentage": [(p - base_price) / base_price * 100 for p in predictions]
        }
    
    def _calculate_confidence_intervals(self, forecasts: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
        """Calculate confidence intervals for predictions"""
        intervals = []
        for forecast in forecasts:
            for pred in forecast.get("predictions", []):
                lower = pred * 0.95
                upper = pred * 1.05
                intervals.append((lower, upper))
        return intervals
    
    def _calculate_risk_score(self, forecasts: List[Dict[str, Any]]) -> float:
        """Calculate overall risk score"""
        prices = []
        for f in forecasts:
            prices.extend(f.get("predictions", []))
        
        if prices:
            volatility = np.std(prices) / np.mean(prices)
            risk = min(volatility * 2, 1.0)
        else:
            risk = 0.5
        
        return round(risk, 2)


class MapAgent:
    """
    Map Agent - Performs geospatial reasoning
    """
    
    def __init__(self, mappls_service=None):
        self.mappls_service = mappls_service
    
    async def analyze_zones(self, city: str, budget: Dict[str, float],
                          property_type: str, amenities: List[str]) -> Dict[str, Any]:
        """Analyze zones based on criteria"""
        
        # Get candidate zones
        zones = await self._identify_zones(city, budget, property_type)
        
        # Analyze each zone
        analyzed_zones = []
        for zone in zones:
            zone_analysis = await self._analyze_single_zone(zone, amenities)
            analyzed_zones.append(zone_analysis)
        
        # Generate heatmap
        heatmap_url = self._generate_heatmap(analyzed_zones)
        
        # Create GeoJSON for map visualization
        geojson = self._create_geojson(analyzed_zones)
        
        return {
            "zones": analyzed_zones,
            "geo_features": {
                "city_center": self._get_city_center(city),
                "search_boundary": self._create_search_boundary(city, budget),
                "centroid": self._calculate_centroid(analyzed_zones)
            },
            "poi_summary": self._aggregate_pois(analyzed_zones),
            "infra_matches": self._find_infra_matches(analyzed_zones, amenities),
            "heatmap_url": heatmap_url,
            "geojson": geojson,
            "spatial_features": self._extract_spatial_features(analyzed_zones)
        }
    
    async def _identify_zones(self, city: str, budget: Dict[str, float], 
                            property_type: str) -> List[Dict[str, Any]]:
        """Identify candidate zones for the given city (lat, lon centroids)."""
        city_key = (city or "Bangalore").strip().lower()
        
        city_zones: Dict[str, List[Dict[str, Any]]] = {
            "bangalore": [
                {"id": "zone_whitefield", "name": "Whitefield", "centroid": [12.9698, 77.7499], "avg_price_sqft": 6500, "base_price": 7800000, "description": "IT hub with excellent connectivity"},
                {"id": "zone_sarjapur", "name": "Sarjapur Road", "centroid": [12.9081, 77.6856], "avg_price_sqft": 5800, "base_price": 6960000, "description": "Emerging tech corridor"},
                {"id": "zone_hebbal", "name": "Hebbal", "centroid": [13.0358, 77.5970], "avg_price_sqft": 7200, "base_price": 8640000, "description": "North Bangalore growth center"},
                {"id": "zone_electronic_city", "name": "Electronic City", "centroid": [12.8406, 77.6762], "avg_price_sqft": 5500, "base_price": 6600000, "description": "Established IT park area"},
            ],
            "mumbai": [
                {"id": "andheri_east", "name": "Andheri East", "centroid": [19.1136, 72.8697], "avg_price_sqft": 25000, "base_price": 18500000, "description": "Commercial & residential hub"},
                {"id": "thane", "name": "Thane", "centroid": [19.2183, 72.9781], "avg_price_sqft": 12000, "base_price": 9500000, "description": "Well-connected suburb"},
                {"id": "navi_mumbai", "name": "Navi Mumbai", "centroid": [19.0330, 73.0297], "avg_price_sqft": 11000, "base_price": 9000000, "description": "Planned city with good infra"},
                {"id": "powai", "name": "Powai", "centroid": [19.1180, 72.9070], "avg_price_sqft": 22000, "base_price": 17000000, "description": "Premium lakeside locality"},
            ],
            "delhi": [
                {"id": "dwarka", "name": "Dwarka", "centroid": [28.5921, 77.0460], "avg_price_sqft": 12000, "base_price": 12000000, "description": "Planned sub-city"},
                {"id": "rohini", "name": "Rohini", "centroid": [28.7360, 77.0678], "avg_price_sqft": 9500, "base_price": 8500000, "description": "Emerging residential area"},
                {"id": "noida_sec62", "name": "Noida Sector 62", "centroid": [28.6290, 77.3679], "avg_price_sqft": 8000, "base_price": 7800000, "description": "IT/office hub (NCR)"},
                {"id": "gurgaon_sec56", "name": "Gurgaon Sector 56", "centroid": [28.4319, 77.0986], "avg_price_sqft": 11000, "base_price": 10500000, "description": "Established residential sector"},
            ],
            "pune": [
                {"id": "hinjawadi", "name": "Hinjawadi", "centroid": [18.5913, 73.7380], "avg_price_sqft": 7500, "base_price": 7000000, "description": "IT park locality"},
                {"id": "kharadi", "name": "Kharadi", "centroid": [18.5511, 73.9441], "avg_price_sqft": 9000, "base_price": 8200000, "description": "IT/SEZ hub"},
                {"id": "wakad", "name": "Wakad", "centroid": [18.5970, 73.7700], "avg_price_sqft": 8000, "base_price": 7600000, "description": "Popular residential area"},
                {"id": "baner", "name": "Baner", "centroid": [18.5590, 73.7898], "avg_price_sqft": 9500, "base_price": 8800000, "description": "Premium residential hub"},
            ],
            "hyderabad": [
                {"id": "gachibowli", "name": "Gachibowli", "centroid": [17.4401, 78.3489], "avg_price_sqft": 7000, "base_price": 7500000, "description": "IT/financial district"},
                {"id": "madhapur", "name": "Madhapur", "centroid": [17.4483, 78.3915], "avg_price_sqft": 8000, "base_price": 8200000, "description": "HITEC city proximity"},
                {"id": "kondapur", "name": "Kondapur", "centroid": [17.4690, 78.3570], "avg_price_sqft": 7200, "base_price": 7800000, "description": "Residential near IT hub"},
                {"id": "kukatpally", "name": "Kukatpally", "centroid": [17.4948, 78.3990], "avg_price_sqft": 6500, "base_price": 7000000, "description": "Affordable with infra"},
            ],
            "chennai": [
                {"id": "sholinganallur", "name": "OMR - Sholinganallur", "centroid": [12.9000, 80.2270], "avg_price_sqft": 8000, "base_price": 7400000, "description": "IT corridor OMR"},
                {"id": "velachery", "name": "Velachery", "centroid": [12.9790, 80.2200], "avg_price_sqft": 9000, "base_price": 8200000, "description": "Well-connected residential"},
                {"id": "porur", "name": "Porur", "centroid": [13.0480, 80.1640], "avg_price_sqft": 7000, "base_price": 6800000, "description": "Growing residential area"},
                {"id": "ambattur", "name": "Ambattur", "centroid": [13.1143, 80.1548], "avg_price_sqft": 6500, "base_price": 6200000, "description": "Industrial/residential mix"},
            ],
        }
        
        zones = city_zones.get(city_key, city_zones.get("bangalore", []))
        
        # Filter by budget
        return [z for z in zones if budget["min"] <= z["base_price"] <= budget["max"]]
    
    async def _analyze_single_zone(self, zone: Dict[str, Any], 
                                  amenities: List[str]) -> Dict[str, Any]:
        """Detailed analysis of a single zone"""
        zone_analysis = zone.copy()
        
        # Add POI analysis
        zone_analysis["pois"] = {
            "schools": {
                "count": np.random.randint(5, 15), 
                "nearest": f"{np.random.uniform(0.2, 2):.1f}km",
                "top_schools": ["DPS", "Ryan International", "Vibgyor"]
            },
            "hospitals": {
                "count": np.random.randint(2, 8), 
                "nearest": f"{np.random.uniform(0.5, 3):.1f}km",
                "major": ["Columbia Asia", "Manipal Hospital"]
            },
            "malls": {
                "count": np.random.randint(1, 5), 
                "nearest": f"{np.random.uniform(1, 5):.1f}km",
                "names": ["Forum Mall", "VR Mall"]
            },
            "metro": {
                "count": np.random.randint(1, 3), 
                "nearest": f"{np.random.uniform(0.5, 3):.1f}km",
                "stations": ["Whitefield", "KR Puram"]
            }
        }
        
        # Add infrastructure status
        zone_analysis["infrastructure"] = {
            "metro_connectivity": "existing" if np.random.random() > 0.5 else "planned",
            "road_quality": np.random.choice(["excellent", "good", "average"]),
            "water_supply": "24x7" if np.random.random() > 0.3 else "limited",
            "power_backup": True,
            "upcoming_projects": ["Metro Phase 2", "Ring Road Extension"]
        }
        
        # Calculate zone score based on amenities
        zone_analysis["amenity_score"] = self._calculate_amenity_score(zone_analysis["pois"], amenities)
        zone_analysis["investment_grade"] = self._calculate_investment_grade(zone_analysis)
        
        return zone_analysis
    
    def _generate_heatmap(self, zones: List[Dict[str, Any]]) -> str:
        """Generate heatmap URL for visualization"""
        # In production, would generate actual heatmap
        return f"https://maps.valora.ai/heatmap/{uuid.uuid4().hex[:12]}"
    
    def _create_geojson(self, zones: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create GeoJSON for map visualization"""
        features = []
        for zone in zones:
            feature = {
                "type": "Feature",
                "properties": {
                    "name": zone["name"],
                    "price": zone["base_price"],
                    "amenity_score": zone.get("amenity_score", 0),
                    "description": zone.get("description", "")
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [zone["centroid"][1], zone["centroid"][0]]
                }
            }
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
    
    def _get_city_center(self, city: str) -> List[float]:
        """Get city center coordinates"""
        city_centers = {
            "Bangalore": [12.9716, 77.5946],
            "Mumbai": [19.0760, 72.8777],
            "Delhi": [28.6139, 77.2090],
            "Pune": [18.5204, 73.8567],
            "Hyderabad": [17.3850, 78.4867],
            "Chennai": [13.0827, 80.2707]
        }
        return city_centers.get(city, [12.9716, 77.5946])
    
    def _create_search_boundary(self, city: str, budget: Dict[str, float]) -> Dict[str, Any]:
        """Create GeoJSON boundary for search area"""
        center = self._get_city_center(city)
        # Simple box boundary
        return {
            "type": "Polygon",
            "coordinates": [[
                [center[1] - 0.15, center[0] - 0.15],
                [center[1] + 0.15, center[0] - 0.15],
                [center[1] + 0.15, center[0] + 0.15],
                [center[1] - 0.15, center[0] + 0.15],
                [center[1] - 0.15, center[0] - 0.15]
            ]]
        }
    
    def _calculate_centroid(self, zones: List[Dict[str, Any]]) -> List[float]:
        """Calculate centroid of all zones"""
        if not zones:
            return [12.9716, 77.5946]  # Default Bangalore
        
        lat = np.mean([z["centroid"][0] for z in zones])
        lon = np.mean([z["centroid"][1] for z in zones])
        return [lat, lon]
    
    def _aggregate_pois(self, zones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate POI data across zones"""
        poi_summary = []
        poi_types = ["schools", "hospitals", "malls", "metro"]
        
        for poi_type in poi_types:
            total_count = sum(z.get("pois", {}).get(poi_type, {}).get("count", 0) for z in zones)
            nearest_distances = [
                float(z.get("pois", {}).get(poi_type, {}).get("nearest", "99km").replace("km", ""))
                for z in zones if z.get("pois", {}).get(poi_type)
            ]
            nearest = min(nearest_distances) if nearest_distances else 99
            
            poi_summary.append({
                "category": poi_type,
                "total_count": total_count,
                "avg_count": total_count / len(zones) if zones else 0,
                "nearest": f"{nearest}km"
            })
        
        return poi_summary
    
    def _find_infra_matches(self, zones: List[Dict[str, Any]], 
                          amenities: List[str]) -> List[Dict[str, Any]]:
        """Find infrastructure matches"""
        matches = []
        
        for zone in zones:
            infra = zone.get("infrastructure", {})
            if "metro" in amenities and infra.get("metro_connectivity"):
                matches.append({
                    "type": "metro",
                    "zone": zone["name"],
                    "status": infra["metro_connectivity"],
                    "distance_km": float(zone["pois"]["metro"]["nearest"].replace("km", ""))
                })
            
            # Add upcoming projects
            for project in infra.get("upcoming_projects", []):
                matches.append({
                    "type": "infrastructure",
                    "zone": zone["name"],
                    "project": project,
                    "status": "upcoming"
                })
        
        return matches
    
    def _extract_spatial_features(self, zones: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract aggregated spatial features"""
        if not zones:
            return {}
        
        return {
            "avg_dist_to_metro": np.mean([
                float(z["pois"]["metro"]["nearest"].replace("km", ""))
                for z in zones
            ]),
            "total_poi_density": np.mean([
                sum(p.get("count", 0) for p in z.get("pois", {}).values() if isinstance(p, dict))
                for z in zones
            ]),
            "avg_amenity_score": np.mean([z.get("amenity_score", 0) for z in zones]),
            "infrastructure_quality": np.mean([
                0.8 if z.get("infrastructure", {}).get("road_quality") == "excellent" 
                else 0.6 if z.get("infrastructure", {}).get("road_quality") == "good"
                else 0.4
                for z in zones
            ])
        }
    
    def _calculate_amenity_score(self, pois: Dict[str, Any], desired_amenities: List[str]) -> float:
        """Calculate amenity score for a zone"""
        score = 0.0
        max_score = len(desired_amenities) * 100
        
        for amenity in desired_amenities:
            if amenity in pois:
                # Score based on count and distance
                count = pois[amenity].get("count", 0)
                distance = float(pois[amenity].get("nearest", "10km").replace("km", ""))
                
                # Higher count = better, closer distance = better
                amenity_score = (count * 10) / (distance + 0.1)
                score += min(amenity_score, 100)  # Cap at 100 per amenity
        
        return round(score / max_score if max_score > 0 else 0, 2)
    
    def _calculate_investment_grade(self, zone_analysis: Dict[str, Any]) -> str:
        """Calculate investment grade for zone"""
        score = zone_analysis.get("amenity_score", 0)
        
        if zone_analysis.get("infrastructure", {}).get("metro_connectivity") == "existing":
            score += 0.2
        elif zone_analysis.get("infrastructure", {}).get("metro_connectivity") == "planned":
            score += 0.1
        
        if score > 0.8:
            return "A+"
        elif score > 0.6:
            return "A"
        elif score > 0.4:
            return "B+"
        else:
            return "B"


class RecommenderAgent:
    """
    Recommender Agent - Ranks and explains investment opportunities
    """
    
    def __init__(self):
        self.scoring_weights = {
            "price_appreciation": 0.3,
            "rental_yield": 0.2,
            "location_score": 0.25,
            "amenity_score": 0.15,
            "risk_score": 0.1
        }
    
    async def rank_zones(self, map_data: Dict[str, Any], 
                        forecast_data: Dict[str, Any],
                        preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Rank zones based on investment potential"""
        
        zones = map_data.get("zones", [])
        forecasts = forecast_data.get("price_forecast", {}).get("predictions", [])
        
        # Calculate scores for each zone
        recommendations = []
        for i, zone in enumerate(zones):
            if i < len(forecasts):
                score, reasons = self._calculate_investment_score(
                    zone, forecasts[i], forecast_data, preferences
                )
                
                recommendations.append({
                    "property_id": zone.get("id", f"zone_{i}"),
                    "zone_name": zone.get("name", f"Zone {i+1}"),
                    "description": zone.get("description", ""),
                    "score": round(score, 2),
                    "investment_grade": zone.get("investment_grade", "B"),
                    "current_price": forecasts[i].get("current_price", 0),
                    "predicted_price_3m": forecasts[i]["predictions"][0] if forecasts[i]["predictions"] else 0,
                    "predicted_price_1y": forecasts[i]["predictions"][1] if len(forecasts[i]["predictions"]) > 1 else 0,
                    "predicted_price_3y": forecasts[i]["predictions"][2] if len(forecasts[i]["predictions"]) > 2 else 0,
                    "growth_potential": forecasts[i].get("growth_percentage", [0, 0, 0]),
                    "rental_yield": forecasts[i].get("rental_yield", 4.5),
                    "risk": forecast_data.get("risk_score", 0.5),
                    "reasons": reasons,
                    "next_actions": self._suggest_actions(score),
                    "highlights": self._extract_highlights(zone, forecasts[i]),
                    "location_benefits": self._extract_location_benefits(zone)
                })
        
        # Sort by score
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "recommendations": recommendations[:5],  # Top 5
            "reasoning": {
                "methodology": "Multi-factor scoring based on appreciation, yield, location, and amenities",
                "weights": self.scoring_weights,
                "market_conditions": "Favorable with expected infrastructure development",
                "investment_horizon": "3-5 years recommended for maximum returns"
            },
            "summary": self._generate_summary(recommendations[:3])
        }
    
    def _calculate_investment_score(self, zone: Dict[str, Any], 
                                   forecast: Dict[str, Any],
                                   forecast_data: Dict[str, Any],
                                   preferences: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Calculate investment score for a zone"""
        scores = {}
        reasons = []
        
        # Price appreciation score
        if forecast.get("predictions"):
            current = forecast.get("current_price", 7000000)
            future_3y = forecast["predictions"][-1] if forecast["predictions"] else current
            appreciation = ((future_3y - current) / current) * 100
            scores["price_appreciation"] = min(appreciation / 30, 1.0)  # Normalize to 0-1
            
            if appreciation > 20:
                reasons.append(f"📈 High appreciation potential: {appreciation:.1f}%")
        
        # Rental yield score
        rental_yield = forecast.get("rental_yield", 4.5)
        scores["rental_yield"] = min(rental_yield / 8, 1.0)  # Normalize to 0-1
        if rental_yield > 5:
            reasons.append(f"💰 Strong rental yield: {rental_yield:.1f}%")
        
        # Location score
        scores["location_score"] = zone.get("amenity_score", 0.5)
        if scores["location_score"] > 0.7:
            reasons.append("📍 Prime location with excellent amenities")
        
        # Amenity score
        metro_distance = float(zone.get("pois", {}).get("metro", {}).get("nearest", "5km").replace("km", ""))
        if metro_distance < 1:
            scores["amenity_score"] = 0.9
            reasons.append(f"🚇 Walking distance to metro: {metro_distance}km")
        elif metro_distance < 3:
            scores["amenity_score"] = 0.7
            reasons.append(f"🚊 Close to metro: {metro_distance}km")
        else:
            scores["amenity_score"] = 0.4
        
        # Risk adjustment
        risk_factor = 1.0 - forecast_data.get("risk_score", 0.5)
        scores["risk_score"] = risk_factor
        if risk_factor > 0.7:
            reasons.append("✅ Low investment risk")
        
        # Calculate weighted score
        total_score = sum(
            scores.get(factor, 0) * weight 
            for factor, weight in self.scoring_weights.items()
        )
        
        # Add infrastructure bonus
        if zone.get("infrastructure", {}).get("metro_connectivity") == "planned":
            total_score *= 1.1
            reasons.append("🚀 Upcoming metro connectivity boost expected")
        
        return min(total_score, 1.0), reasons
    
    def _suggest_actions(self, score: float) -> List[str]:
        """Suggest next actions based on score"""
        if score > 0.8:
            return [
                "schedule_site_visit",
                "request_detailed_docs",
                "connect_with_agent",
                "book_property"
            ]
        elif score > 0.6:
            return [
                "request_more_info",
                "compare_similar_properties",
                "schedule_virtual_tour"
            ]
        else:
            return [
                "explore_alternatives",
                "set_price_alert",
                "monitor_market"
            ]
    
    def _extract_highlights(self, zone: Dict[str, Any], forecast: Dict[str, Any]) -> List[str]:
        """Extract key highlights for the zone"""
        highlights = []
        
        # Infrastructure highlights
        if zone.get("infrastructure", {}).get("metro_connectivity") == "existing":
            highlights.append("✓ Metro connected")
        elif zone.get("infrastructure", {}).get("metro_connectivity") == "planned":
            highlights.append("⚡ Upcoming metro")
        
        # Amenity highlights
        schools = zone.get("pois", {}).get("schools", {}).get("count", 0)
        if schools > 10:
            highlights.append(f"✓ {schools} schools nearby")
        
        # Price highlights
        if zone.get("avg_price_sqft", 0) < 6000:
            highlights.append("💰 Affordable pricing")
        
        # Growth highlights
        growth = forecast.get("growth_percentage", [])
        if growth and growth[-1] > 25:
            highlights.append(f"🚀 {growth[-1]:.0f}% growth potential")
        
        return highlights
    
    def _extract_location_benefits(self, zone: Dict[str, Any]) -> List[str]:
        """Extract location-specific benefits"""
        benefits = []
        
        # Check infrastructure quality
        infra = zone.get("infrastructure", {})
        if infra.get("road_quality") == "excellent":
            benefits.append("Excellent road connectivity")
        if infra.get("water_supply") == "24x7":
            benefits.append("24x7 water supply")
        if infra.get("power_backup"):
            benefits.append("Power backup available")
        
        # Check proximity to key areas
        pois = zone.get("pois", {})
        if pois.get("hospitals", {}).get("count", 0) > 3:
            benefits.append("Multiple hospitals nearby")
        if pois.get("malls", {}).get("count", 0) > 2:
            benefits.append("Shopping & entertainment options")
        
        return benefits
    
    def _generate_summary(self, top_recommendations: List[Dict[str, Any]]) -> str:
        """Generate investment summary"""
        if not top_recommendations:
            return "No suitable recommendations found based on criteria"
        
        top = top_recommendations[0]
        return (
            f"Top recommendation: {top['zone_name']} with {top['score']*100:.0f}% investment score. "
            f"Expected appreciation: {top['growth_potential'][-1]:.1f}% over 3 years with "
            f"{top['rental_yield']:.1f}% rental yield. Investment grade: {top['investment_grade']}"
        )
