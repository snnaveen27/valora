"""
Mappls Integration Service
Handles all interactions with Mappls APIs for geospatial features
"""

import os
import requests
import logging
from typing import Dict, List, Any, Optional, Tuple
from geopy.distance import geodesic
import numpy as np
from functools import lru_cache
import time
import json
import hashlib
from datetime import datetime, timedelta

try:
    from backend.database.multiconnection import mdb as db_manager_multi
except Exception:
    db_manager_multi = None

logger = logging.getLogger(__name__)

class MapplsService:
    """Service for Mappls API integration"""
    
    def __init__(self):
        self.api_key = (
            os.getenv('MAPPLS_API_KEY')
            or os.getenv('MAPPLS_STATIC_KEY')
            or os.getenv('MAPPLE_STATIC_KEY')
            or os.getenv('VITE_MAPPLS_API_KEY')
            or os.getenv('VITE_MAPPLS_STATIC_KEY')
            or os.getenv('VITE_MAPPLE_STATIC_KEY')
            or ''
        )
        self.base_url = "https://apis.mappls.com"
        self.session = requests.Session()
        self.cache = {}
        self.rate_limit_delay = 0.1  # seconds between requests
        self.last_request_time = 0
        # Cache policy
        self.geocode_ttl_days = 30
        self.reverse_ttl_days = 30
        self.poi_ttl_hours = 24
        # Spatial tiling (~1km ~ 0.01 deg). Adjust as needed.
        self.tile_deg = 0.01
    
    def is_connected(self) -> bool:
        """Check if Mappls API is accessible"""
        return bool(self.api_key)
    
    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    @lru_cache(maxsize=1000)
    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """Convert address to coordinates with DB cache when available"""
        if not address:
            return None
        # Check DB cache first
        if db_manager_multi:
            addr_norm = address.strip().lower()
            addr_hash = hashlib.sha256(addr_norm.encode('utf-8')).hexdigest()
            with db_manager_multi.spatial() as s:
                row = s.execute(
                    "SELECT latitude, longitude, expires_at FROM mappls_geocode_cache WHERE address_hash=:h",
                    {"h": addr_hash},
                ).fetchone()
                if row and (row[2] is None or row[2] > datetime.utcnow()):
                    try:
                        return (float(row[0]), float(row[1]))
                    except Exception:
                        pass
        if not self.api_key:
            return None
        try:
            self._rate_limit()
            url = f"{self.base_url}/advancedmaps/v1/{self.api_key}/geocode"
            params = {'address': address}
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'copResults' in data and data['copResults']:
                    result = data['copResults'][0]
                    lat, lon = float(result['latitude']), float(result['longitude'])
                    if db_manager_multi:
                        with db_manager_multi.spatial() as s:
                            s.execute(
                                """
                                INSERT INTO mappls_geocode_cache(address_hash, address, result, latitude, longitude, created_at, expires_at)
                                VALUES (:h, :a, :r, :lat, :lon, NOW(), :exp)
                                ON CONFLICT (address_hash) DO UPDATE SET result=:r, latitude=:lat, longitude=:lon, expires_at=:exp
                                """,
                                {
                                    "h": hashlib.sha256(address.strip().lower().encode('utf-8')).hexdigest(),
                                    "a": address,
                                    "r": json.dumps(result),
                                    "lat": lat,
                                    "lon": lon,
                                    "exp": datetime.utcnow() + timedelta(days=self.geocode_ttl_days),
                                },
                            )
                    return (lat, lon)
            return None
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None
    
    @lru_cache(maxsize=1000)
    def reverse_geocode(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Convert coordinates to address with DB cache when available"""
        if lat is None or lon is None:
            return None
        if db_manager_multi:
            key = f"{round(lat,5)},{round(lon,5)}"
            key_hash = hashlib.sha256(key.encode('utf-8')).hexdigest()
            with db_manager_multi.spatial() as s:
                row = s.execute(
                    "SELECT result, expires_at FROM mappls_reverse_cache WHERE key_hash=:h",
                    {"h": key_hash},
                ).fetchone()
                if row and (row[1] is None or row[1] > datetime.utcnow()):
                    try:
                        return json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    except Exception:
                        pass
        if not self.api_key:
            return None
        try:
            self._rate_limit()
            url = f"{self.base_url}/advancedmaps/v1/{self.api_key}/rev_geocode"
            params = {'lat': lat, 'lng': lon}
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'results' in data and data['results']:
                    result = data['results'][0]
                    out = {
                        'formatted_address': result.get('formatted_address'),
                        'locality': result.get('locality'),
                        'city': result.get('city'),
                        'district': result.get('district'),
                        'state': result.get('state'),
                        'pincode': result.get('pincode')
                    }
                    if db_manager_multi:
                        with db_manager_multi.spatial() as s:
                            s.execute(
                                """
                                INSERT INTO mappls_reverse_cache(key_hash, latitude, longitude, result, created_at, expires_at)
                                VALUES (:h, :lat, :lon, :r, NOW(), :exp)
                                ON CONFLICT (key_hash) DO UPDATE SET result=:r, expires_at=:exp
                                """,
                                {
                                    "h": hashlib.sha256(f"{round(lat,5)},{round(lon,5)}".encode('utf-8')).hexdigest(),
                                    "lat": lat,
                                    "lon": lon,
                                    "r": json.dumps(out),
                                    "exp": datetime.utcnow() + timedelta(days=self.reverse_ttl_days),
                                },
                            )
                    return out
            return None
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
            return None
    
    def nearby_search(self, lat: float, lon: float, keywords: str = None, 
                     radius: int = 5000, category: str = None) -> List[Dict[str, Any]]:
        """Search for nearby POIs with DB caching and persistence into pois table"""
        if lat is None or lon is None:
            return []
        # Compute tile key for caching
        tile_lat = round(lat / self.tile_deg) * self.tile_deg
        tile_lon = round(lon / self.tile_deg) * self.tile_deg
        kw_norm = (keywords or '').strip().lower()
        cat_norm = (category or '').strip().lower()
        kw_hash = hashlib.sha256(kw_norm.encode('utf-8')).hexdigest() if kw_norm else hashlib.sha256(b'').hexdigest()

        # Attempt DB cache
        if db_manager_multi:
            with db_manager_multi.spatial() as s:
                row = s.execute(
                    """
                    SELECT result, expires_at FROM mappls_poi_cache
                    WHERE tile_lat=:tlat AND tile_lon=:tlon AND radius_m=:r AND category=:c AND keywords_hash=:kh
                    """,
                    {"tlat": tile_lat, "tlon": tile_lon, "r": radius, "c": cat_norm or None, "kh": kw_hash},
                ).fetchone()
                if row and (row[1] is None or row[1] > datetime.utcnow()):
                    try:
                        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        return self._process_poi_results(data, lat, lon)
                    except Exception:
                        pass

        # Fallback/API call
        if not self.api_key:
            return []
        try:
            self._rate_limit()
            url = f"{self.base_url}/advancedmaps/v1/{self.api_key}/nearby"
            params = {'refLocation': f"{lat},{lon}", 'radius': radius}
            if kw_norm:
                params['keywords'] = kw_norm
            if cat_norm:
                params['category'] = cat_norm
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                raw_list = data.get('suggestedLocations', [])
                # Persist into POI cache and pois table
                if db_manager_multi:
                    with db_manager_multi.spatial() as s:
                        s.execute(
                            """
                            INSERT INTO mappls_poi_cache(tile_lat, tile_lon, radius_m, category, keywords, keywords_hash, result, created_at, expires_at)
                            VALUES (:tlat, :tlon, :r, :c, :k, :kh, :res, NOW(), :exp)
                            ON CONFLICT (tile_lat, tile_lon, radius_m, category, keywords_hash)
                            DO UPDATE SET result=:res, expires_at=:exp
                            """,
                            {
                                "tlat": tile_lat,
                                "tlon": tile_lon,
                                "r": radius,
                                "c": cat_norm or None,
                                "k": kw_norm or None,
                                "kh": kw_hash,
                                "res": json.dumps(raw_list),
                                "exp": datetime.utcnow() + timedelta(hours=self.poi_ttl_hours),
                            },
                        )
                        # Upsert into pois table
                        for poi in raw_list[:500]:
                            try:
                                name = poi.get('placeName') or poi.get('poi'),
                                name = name[0] if isinstance(name, tuple) else (name if isinstance(name, str) else '')
                                plat = float(poi.get('latitude', 0))
                                plon = float(poi.get('longitude', 0))
                                if not plat or not plon:
                                    continue
                                source_id = poi.get('eLoc') or hashlib.sha256(f"{name}|{plat}|{plon}".encode('utf-8')).hexdigest()
                                s.execute(
                                    """
                                    INSERT INTO pois(id, name, category, location, metadata, created_at, source, source_id)
                                    VALUES (gen_random_uuid(), :n, :cat, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::GEOGRAPHY, :m, NOW(), 'mappls', :sid)
                                    ON CONFLICT (source_id) DO NOTHING
                                    """,
                                    {
                                        "n": name or 'Unknown',
                                        "cat": poi.get('category', '') or (poi.get('type','') or ''),
                                        "lon": plon,
                                        "lat": plat,
                                        "m": json.dumps(poi),
                                        "sid": source_id,
                                    },
                                )
                            except Exception:
                                continue
                return self._process_poi_results(raw_list, lat, lon)
            return []
        except Exception as e:
            logger.error(f"Nearby search error: {e}")
            return []
    
    def _process_poi_results(self, pois: List[Dict], ref_lat: float, ref_lon: float) -> List[Dict[str, Any]]:
        """Process POI results and calculate distances"""
        processed_pois = []
        
        for poi in pois:
            try:
                poi_data = {
                    'name': poi.get('placeName', 'Unknown'),
                    'type': poi.get('type', 'Unknown'),
                    'category': poi.get('category', 'Unknown'),
                    'address': poi.get('placeAddress', ''),
                    'latitude': float(poi.get('latitude', 0)),
                    'longitude': float(poi.get('longitude', 0))
                }
                
                # Calculate distance
                if poi_data['latitude'] and poi_data['longitude']:
                    distance = geodesic(
                        (ref_lat, ref_lon),
                        (poi_data['latitude'], poi_data['longitude'])
                    ).kilometers
                    poi_data['distance_km'] = round(distance, 2)
                else:
                    poi_data['distance_km'] = None
                
                processed_pois.append(poi_data)
                
            except Exception as e:
                logger.debug(f"Error processing POI: {e}")
                continue
        
        # Sort by distance
        processed_pois.sort(key=lambda x: x.get('distance_km', float('inf')))
        
        return processed_pois
    
    def calculate_spatial_features(self, lat: float, lon: float) -> Dict[str, Any]:
        """Calculate comprehensive spatial features for a location"""
        features = {
            'distance_to_metro': 10.0,
            'distance_to_hospital': 5.0,
            'distance_to_school': 3.0,
            'distance_to_mall': 7.0,
            'distance_to_airport': 25.0,
            'distance_to_railway': 8.0,
            'poi_density': 0,
            'infrastructure_score': 5.0,
            'connectivity_score': 5.0,
            'lifestyle_score': 5.0
        }
        
        if not self.api_key:
            return features
        
        try:
            # Search for different POI categories
            categories = {
                'metro,railway,station': ['distance_to_metro', 'distance_to_railway'],
                'hospital,medical,clinic': ['distance_to_hospital'],
                'school,college,university': ['distance_to_school'],
                'mall,shopping,market': ['distance_to_mall'],
                'airport': ['distance_to_airport']
            }
            
            all_pois = []
            
            for keywords, feature_keys in categories.items():
                pois = self.nearby_search(lat, lon, keywords=keywords, radius=10000)
                all_pois.extend(pois)
                
                # Update distances for each feature
                for poi in pois[:3]:  # Consider top 3 nearest
                    distance = poi.get('distance_km', 10)
                    for feature_key in feature_keys:
                        features[feature_key] = min(features[feature_key], distance)
            
            # Calculate POI density
            features['poi_density'] = len(all_pois)
            
            # Calculate scores
            features['infrastructure_score'] = self._calculate_infrastructure_score(features)
            features['connectivity_score'] = self._calculate_connectivity_score(features)
            features['lifestyle_score'] = self._calculate_lifestyle_score(features)
            
        except Exception as e:
            logger.error(f"Error calculating spatial features: {e}")
        
        return features
    
    def _calculate_infrastructure_score(self, features: Dict) -> float:
        """Calculate infrastructure score (0-10)"""
        score = 10.0
        
        # Deduct points for distance to key infrastructure
        score -= min(3, features['distance_to_hospital'] / 5)
        score -= min(2, features['distance_to_school'] / 3)
        score -= min(2, features['distance_to_mall'] / 7)
        
        # Add points for POI density
        score += min(3, features['poi_density'] / 20)
        
        return max(0, min(10, score))
    
    def _calculate_connectivity_score(self, features: Dict) -> float:
        """Calculate connectivity score (0-10)"""
        score = 10.0
        
        # Deduct points for distance to transport
        score -= min(4, features['distance_to_metro'] / 3)
        score -= min(2, features['distance_to_railway'] / 5)
        score -= min(2, features['distance_to_airport'] / 15)
        
        return max(0, min(10, score))
    
    def _calculate_lifestyle_score(self, features: Dict) -> float:
        """Calculate lifestyle score (0-10)"""
        score = 5.0
        
        # Bonus for proximity to amenities
        if features['distance_to_mall'] < 3:
            score += 2
        if features['distance_to_school'] < 2:
            score += 1.5
        if features['distance_to_hospital'] < 3:
            score += 1.5
        
        return max(0, min(10, score))
    
    def get_route_distance(self, origin: Tuple[float, float], 
                          destination: Tuple[float, float]) -> Optional[Dict[str, Any]]:
        """Get route distance and time between two points"""
        if not self.api_key:
            return None
        
        try:
            self._rate_limit()
            url = f"{self.base_url}/advancedmaps/v1/{self.api_key}/route_adv/driving"
            
            params = {
                'start': f"{origin[0]},{origin[1]}",
                'destination': f"{destination[0]},{destination[1]}",
                'geometries': 'polyline',
                'overview': 'simplified'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'routes' in data and data['routes']:
                    route = data['routes'][0]
                    return {
                        'distance_km': route.get('distance', 0) / 1000,
                        'duration_minutes': route.get('duration', 0) / 60,
                        'traffic_delay': route.get('weight', 0) / 60
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Route distance error: {e}")
            return None
    
    def create_heatmap_data(self, properties: List[Dict], metric: str = 'price') -> List[Dict[str, Any]]:
        """Create heatmap data for visualization"""
        heatmap_data = []
        
        for prop in properties:
            if 'latitude' in prop and 'longitude' in prop and metric in prop:
                heatmap_data.append({
                    'lat': prop['latitude'],
                    'lng': prop['longitude'],
                    'weight': prop[metric],
                    'radius': 20  # pixels
                })
        
        return heatmap_data
    
    def identify_clusters(self, properties: List[Dict], min_properties: int = 5) -> List[Dict[str, Any]]:
        """Identify property clusters for hotspot analysis"""
        from sklearn.cluster import DBSCAN
        
        if len(properties) < min_properties:
            return []
        
        # Extract coordinates
        coords = []
        valid_properties = []
        for prop in properties:
            if 'latitude' in prop and 'longitude' in prop:
                coords.append([prop['latitude'], prop['longitude']])
                valid_properties.append(prop)
        
        if len(coords) < min_properties:
            return []
        
        # Perform clustering
        coords_array = np.array(coords)
        clustering = DBSCAN(eps=0.01, min_samples=min_properties).fit(coords_array)
        
        # Process clusters
        clusters = []
        unique_labels = set(clustering.labels_)
        
        for label in unique_labels:
            if label == -1:  # Skip noise points
                continue
            
            cluster_mask = clustering.labels_ == label
            cluster_props = [valid_properties[i] for i in range(len(valid_properties)) if cluster_mask[i]]
            
            # Calculate cluster statistics
            cluster_coords = coords_array[cluster_mask]
            center_lat = cluster_coords[:, 0].mean()
            center_lon = cluster_coords[:, 1].mean()
            
            # Calculate average metrics
            avg_price = np.mean([p.get('price', 0) for p in cluster_props])
            avg_psf = np.mean([p.get('price_per_sqft', 0) for p in cluster_props])
            
            clusters.append({
                'cluster_id': int(label),
                'center': {'lat': center_lat, 'lng': center_lon},
                'property_count': len(cluster_props),
                'avg_price': avg_price,
                'avg_price_per_sqft': avg_psf,
                'properties': cluster_props
            })
        
        return clusters
    
    def get_area_demographics(self, lat: float, lon: float, radius: int = 5000) -> Dict[str, Any]:
        """Get demographic insights for an area (simulated)"""
        # This would typically integrate with demographic data APIs
        # For now, return simulated data based on location
        
        return {
            'population_density': np.random.randint(5000, 20000),
            'avg_income_bracket': np.random.choice(['Low', 'Middle', 'High'], p=[0.3, 0.5, 0.2]),
            'dominant_age_group': np.random.choice(['18-25', '26-35', '36-50', '50+'], p=[0.2, 0.4, 0.3, 0.1]),
            'employment_hubs': np.random.randint(3, 15),
            'education_index': np.random.uniform(0.4, 0.9),
            'commercial_activity': np.random.choice(['Low', 'Medium', 'High'], p=[0.2, 0.5, 0.3])
        }
