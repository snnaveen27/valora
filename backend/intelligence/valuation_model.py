"""
Valora AI - ML Property Valuation Model
Phase 1: Dynamic Property Valuations with Spatial Features

Uses machine learning to predict property prices based on:
- Property features (bedrooms, area, amenities)
- Spatial features (proximity to metro, hospitals, schools)
- Terrain features (elevation, slope)
- Market comparables
"""

import os
import json
import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import math

try:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("[WARNING]  ML libraries not installed. Valuation features will be limited.")


@dataclass
class ValuationResult:
    """Property valuation result."""
    estimated_price: float
    price_per_sqft: float
    confidence: float  # 0-1
    price_range: Tuple[float, float]  # (low, high)
    factors: Dict[str, float]  # Feature importance
    comparables: List[Dict[str, Any]]  # Similar properties
    market_analysis: Dict[str, Any]


@dataclass
class SpatialFeatures:
    """Spatial features for a location."""
    lat: float
    lng: float
    elevation: float = 0.0
    slope: float = 0.0
    dist_to_metro: float = 999.0  # km
    dist_to_hospital: float = 999.0
    dist_to_school: float = 999.0
    dist_to_mall: float = 999.0
    dist_to_park: float = 999.0
    nearby_pois: int = 0
    nearby_transport: int = 0
    road_density: float = 0.0


class PropertyValuationModel:
    """
    ML-based property valuation model with spatial reasoning.
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        from config import config
        self.properties_dir = config.DATA_DIR / 'posted_properties'
        self.osm_dir = config.DATA_DIR / 'osm_extracted'
        from config import config
        self.model_dir = config.MODELS_DIR
        
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.properties_df = None
        
        # POI/transport data for spatial features
        self.pois = []
        self.transport = []
        self.metro_stations = []
        
        self._ensure_model_dir()
        self._load_spatial_data()
        # Load existing model if available, otherwise use heuristics
        # Training is deferred to avoid blocking server startup
        self._load_model_if_exists()
    
    def _ensure_model_dir(self):
        """Ensure model directory exists."""
        self.model_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_spatial_data(self):
        """Load POIs and transport data from DATABASE for spatial feature computation."""
        try:
            try:
                from backend.database.query_service import get_query_service
            except ImportError:
                from database.query_service import get_query_service
            db = get_query_service()
            
            # Load POIs from database
            pois_data = db.get_all_pois()
            for poi in pois_data:
                if poi.get('lat') and poi.get('lng'):
                    self.pois.append({
                        'name': poi.get('name', ''),
                        'amenity': poi.get('category', ''),
                        'shop': poi.get('subcategory', ''),
                        'lat': poi['lat'],
                        'lng': poi['lng']
                    })
            print(f"[OK] Loaded {len(self.pois)} POIs from DB for spatial features")
            
            # Load transport from database
            transport_data = db.get_all_transport()
            for t in transport_data:
                if t.get('lat') and t.get('lng'):
                    t_type = t.get('type', '')
                    t_name = t.get('name', '')
                    entry = {
                        'name': t_name,
                        'type': t_type,
                        'lat': t['lat'],
                        'lng': t['lng']
                    }
                    self.transport.append(entry)
                    if 'metro' in t_type.lower() or 'metro' in t_name.lower():
                        self.metro_stations.append(entry)
            print(f"[OK] Loaded {len(self.transport)} transport from DB ({len(self.metro_stations)} metro)")
            
        except Exception as e:
            print(f"[WARNING] Database not available, falling back to files: {e}")
            self._load_spatial_data_from_files()
    
    def _load_spatial_data_from_files(self):
        """Fallback: Load POIs and transport from GeoJSON files."""
        pois_file = self.osm_dir / 'pois.geojson'
        if pois_file.exists():
            try:
                with open(pois_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for feat in data.get('features', []):
                    props = feat.get('properties', {})
                    coords = feat.get('geometry', {}).get('coordinates', [])
                    if len(coords) >= 2:
                        self.pois.append({'name': props.get('name', ''), 'amenity': props.get('amenity', ''),
                                          'lat': coords[1], 'lng': coords[0]})
            except Exception as e:
                print(f"[WARNING] Error loading POIs from file: {e}")
        
        transport_file = self.osm_dir / 'transport.geojson'
        if transport_file.exists():
            try:
                with open(transport_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for feat in data.get('features', []):
                    props = feat.get('properties', {})
                    coords = feat.get('geometry', {}).get('coordinates', [])
                    if len(coords) >= 2:
                        t_type = props.get('railway', '') or props.get('highway', '') or ''
                        t_name = props.get('name', '') or ''
                        entry = {'name': t_name, 'type': t_type, 'lat': coords[1], 'lng': coords[0]}
                        self.transport.append(entry)
                        if 'metro' in t_type.lower() or 'metro' in t_name.lower():
                            self.metro_stations.append(entry)
            except Exception as e:
                print(f"[WARNING] Error loading transport from file: {e}")
    
    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in km between two points."""
        R = 6371
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def compute_spatial_features(self, lat: float, lng: float) -> SpatialFeatures:
        """Compute spatial features for a location."""
        features = SpatialFeatures(lat=lat, lng=lng)
        
        # Distance to nearest metro
        if self.metro_stations:
            min_dist = min(self._haversine(lat, lng, m['lat'], m['lng']) for m in self.metro_stations)
            features.dist_to_metro = min_dist
        
        # Count nearby POIs and compute distances to key amenities
        hospitals = []
        schools = []
        malls = []
        parks = []
        
        for poi in self.pois:
            dist = self._haversine(lat, lng, poi['lat'], poi['lng'])
            
            if dist <= 2.0:  # Within 2km
                features.nearby_pois += 1
            
            amenity = poi.get('amenity', '').lower()
            shop = poi.get('shop', '').lower()
            
            if 'hospital' in amenity or 'clinic' in amenity:
                hospitals.append(dist)
            elif 'school' in amenity or 'college' in amenity:
                schools.append(dist)
            elif 'mall' in shop or 'supermarket' in shop:
                malls.append(dist)
            elif 'park' in amenity:
                parks.append(dist)
        
        if hospitals:
            features.dist_to_hospital = min(hospitals)
        if schools:
            features.dist_to_school = min(schools)
        if malls:
            features.dist_to_mall = min(malls)
        if parks:
            features.dist_to_park = min(parks)
        
        # Count nearby transport
        for t in self.transport:
            if self._haversine(lat, lng, t['lat'], t['lng']) <= 1.0:
                features.nearby_transport += 1
        
        return features
    
    def _load_properties_data(self) -> pd.DataFrame:
        """Load all properties into a DataFrame."""
        if not ML_AVAILABLE:
            return None
        
        all_properties = []
        
        for json_file in self.properties_dir.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    properties = json.load(f)
                
                category = json_file.stem.replace('bangalore-', '').replace('-', '_')
                
                for prop in properties:
                    # Parse location
                    lat, lng = None, None
                    loc = prop.get('location', '')
                    if loc and ',' in loc:
                        try:
                            lat, lng = map(float, loc.split(','))
                        except:
                            continue
                    
                    if lat is None or lng is None:
                        continue
                    
                    price = prop.get('price', 0)
                    if not price or price <= 0:
                        continue
                    
                    all_properties.append({
                        'id': prop.get('id', ''),
                        'category': category,
                        'price': price,
                        'price_per_sqft': prop.get('price_per_sq_ft', 0),
                        'bedrooms': prop.get('bedrooms', 0) or 0,
                        'bathrooms': prop.get('bathrooms', 0) or 0,
                        'covered_area': prop.get('covered_area', 0) or 0,
                        'floors': prop.get('floors', 0) or 0,
                        'lat': lat,
                        'lng': lng,
                        'name': prop.get('name', ''),
                        'amenities': prop.get('amenities', '')
                    })
                    
            except Exception as e:
                print(f"[WARNING]  Error loading {json_file.name}: {e}")
        
        if not all_properties:
            return None
        
        df = pd.DataFrame(all_properties)
        print(f"[OK] Loaded {len(df)} properties for training")
        return df
    
    def _prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Prepare feature matrix and target vector."""
        feature_names = [
            'bedrooms', 'bathrooms', 'covered_area', 'floors',
            'lat', 'lng',
            'dist_to_metro', 'dist_to_hospital', 'dist_to_school',
            'dist_to_mall', 'nearby_pois', 'nearby_transport',
            'is_residential', 'is_commercial', 'is_agricultural'
        ]
        
        features = []
        targets = []
        
        for _, row in df.iterrows():
            spatial = self.compute_spatial_features(row['lat'], row['lng'])
            
            feat = [
                row['bedrooms'],
                row['bathrooms'],
                row['covered_area'],
                row['floors'],
                row['lat'],
                row['lng'],
                spatial.dist_to_metro,
                spatial.dist_to_hospital,
                spatial.dist_to_school,
                spatial.dist_to_mall,
                spatial.nearby_pois,
                spatial.nearby_transport,
                1 if 'residential' in row['category'] else 0,
                1 if 'commercial' in row['category'] else 0,
                1 if 'agricultural' in row['category'] else 0
            ]
            
            features.append(feat)
            targets.append(row['price'])
        
        return np.array(features), np.array(targets), feature_names
    
    def _train_model(self, df: pd.DataFrame) -> bool:
        """Train the valuation model."""
        if not ML_AVAILABLE:
            return False
        
        print("🔧 Training valuation model...")
        
        X, y, feature_names = self._prepare_features(df)
        self.feature_names = feature_names
        
        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train Gradient Boosting model
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print(f"[OK] Model trained: MAE=₹{mae:,.0f}, R²={r2:.3f}")
        
        # Save model
        self._save_model()
        
        return True
    
    def _save_model(self):
        """Save model and scaler to disk."""
        if self.model is None:
            return
        
        model_path = self.model_dir / 'valuation_model.pkl'
        scaler_path = self.model_dir / 'valuation_scaler.pkl'
        features_path = self.model_dir / 'valuation_features.json'
        
        joblib.dump(self.model, model_path)
        joblib.dump(self.scaler, scaler_path)
        with open(features_path, 'w') as f:
            json.dump(self.feature_names, f)
        
        print(f"[OK] Model saved to {self.model_dir}")
    
    def _load_model(self) -> bool:
        """Load model from disk."""
        model_path = self.model_dir / 'valuation_model.pkl'
        scaler_path = self.model_dir / 'valuation_scaler.pkl'
        features_path = self.model_dir / 'valuation_features.json'
        
        if not all(p.exists() for p in [model_path, scaler_path, features_path]):
            return False
        
        try:
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            with open(features_path, 'r') as f:
                self.feature_names = json.load(f)
            print("[OK] Loaded valuation model from disk")
            return True
        except Exception as e:
            print(f"[WARNING]  Error loading model: {e}")
            return False
    
    def _load_model_if_exists(self):
        """Load existing model if available, otherwise use heuristics."""
        if not ML_AVAILABLE:
            print("[WARNING]  ML not available. Valuation will use heuristics.")
            return
        
        if self._load_model():
            return
        
        print("ℹ️  No trained model found. Using heuristics. Call /api/valuation/train to train model.")
    
    def train_model_async(self) -> Dict[str, Any]:
        """Train the model (can be called via API)."""
        if not ML_AVAILABLE:
            return {"success": False, "error": "ML libraries not available"}
        
        df = self._load_properties_data()
        if df is None or len(df) < 100:
            return {"success": False, "error": "Not enough property data"}
        
        self.properties_df = df
        success = self._train_model(df)
        return {"success": success, "properties_trained": len(df) if success else 0}
    
    def _load_or_train_model(self):
        """Load existing model or train a new one (legacy, not used on startup)."""
        if not ML_AVAILABLE:
            print("[WARNING]  ML not available. Valuation will use heuristics.")
            return
        
        if self._load_model():
            return
        
        df = self._load_properties_data()
        if df is not None and len(df) > 100:
            self.properties_df = df
            self._train_model(df)
        else:
            print("[WARNING]  Not enough data to train model. Using heuristics.")
    
    def _heuristic_valuation(
        self,
        lat: float,
        lng: float,
        bedrooms: int = 2,
        covered_area: float = 1000,
        property_type: str = 'residential'
    ) -> ValuationResult:
        """Fallback heuristic valuation when ML is not available."""
        # Base price per sqft by area (rough Bangalore estimates)
        base_price_per_sqft = 8000  # Base for outer areas
        
        # Adjust by location (distance from city center ~12.97, 77.59)
        dist_from_center = self._haversine(lat, lng, 12.97, 77.59)
        if dist_from_center < 5:
            base_price_per_sqft = 15000
        elif dist_from_center < 10:
            base_price_per_sqft = 12000
        elif dist_from_center < 15:
            base_price_per_sqft = 9000
        
        # Adjust by property type
        if 'commercial' in property_type:
            base_price_per_sqft *= 1.3
        elif 'agricultural' in property_type:
            base_price_per_sqft *= 0.3
        
        # Compute spatial features for adjustments
        spatial = self.compute_spatial_features(lat, lng)
        
        # Adjust by proximity to metro
        if spatial.dist_to_metro < 0.5:
            base_price_per_sqft *= 1.2
        elif spatial.dist_to_metro < 1:
            base_price_per_sqft *= 1.1
        
        estimated_price = base_price_per_sqft * covered_area
        
        return ValuationResult(
            estimated_price=estimated_price,
            price_per_sqft=base_price_per_sqft,
            confidence=0.5,  # Low confidence for heuristic
            price_range=(estimated_price * 0.7, estimated_price * 1.3),
            factors={
                'location': 0.4,
                'area': 0.3,
                'metro_proximity': 0.15,
                'property_type': 0.15
            },
            comparables=[],
            market_analysis={
                'method': 'heuristic',
                'note': 'ML model not available, using location-based heuristics'
            }
        )
    
    def valuate(
        self,
        lat: float,
        lng: float,
        bedrooms: int = 2,
        bathrooms: int = 2,
        covered_area: float = 1000,
        floors: int = 1,
        property_type: str = 'residential'
    ) -> ValuationResult:
        """
        Valuate a property based on its features and location.
        """
        if self.model is None or self.scaler is None:
            return self._heuristic_valuation(lat, lng, bedrooms, covered_area, property_type)
        
        # Compute spatial features
        spatial = self.compute_spatial_features(lat, lng)
        
        # Prepare feature vector
        features = np.array([[
            bedrooms,
            bathrooms,
            covered_area,
            floors,
            lat,
            lng,
            spatial.dist_to_metro,
            spatial.dist_to_hospital,
            spatial.dist_to_school,
            spatial.dist_to_mall,
            spatial.nearby_pois,
            spatial.nearby_transport,
            1 if 'residential' in property_type else 0,
            1 if 'commercial' in property_type else 0,
            1 if 'agricultural' in property_type else 0
        ]])
        
        # Scale and predict
        features_scaled = self.scaler.transform(features)
        predicted_price = self.model.predict(features_scaled)[0]
        
        # Get feature importances
        importances = dict(zip(self.feature_names, self.model.feature_importances_))
        
        # Compute confidence based on how close the input is to training data
        confidence = 0.75  # Base confidence
        
        # Price per sqft
        price_per_sqft = predicted_price / covered_area if covered_area > 0 else 0
        
        # Price range (±15%)
        price_range = (predicted_price * 0.85, predicted_price * 1.15)
        
        # Find comparables
        comparables = self._find_comparables(lat, lng, bedrooms, covered_area, property_type)
        
        return ValuationResult(
            estimated_price=predicted_price,
            price_per_sqft=price_per_sqft,
            confidence=confidence,
            price_range=price_range,
            factors=importances,
            comparables=comparables,
            market_analysis={
                'method': 'ml_gradient_boosting',
                'spatial_features': {
                    'dist_to_metro_km': round(spatial.dist_to_metro, 2),
                    'dist_to_hospital_km': round(spatial.dist_to_hospital, 2),
                    'dist_to_school_km': round(spatial.dist_to_school, 2),
                    'nearby_pois': spatial.nearby_pois,
                    'nearby_transport': spatial.nearby_transport
                }
            }
        )
    
    def _find_comparables(
        self,
        lat: float,
        lng: float,
        bedrooms: int,
        covered_area: float,
        property_type: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Find comparable properties."""
        if self.properties_df is None:
            return []
        
        df = self.properties_df.copy()
        
        # Filter by type
        if 'residential' in property_type:
            df = df[df['category'].str.contains('residential')]
        elif 'commercial' in property_type:
            df = df[df['category'].str.contains('commercial')]
        
        # Filter by bedrooms (±1)
        if bedrooms > 0:
            df = df[(df['bedrooms'] >= bedrooms - 1) & (df['bedrooms'] <= bedrooms + 1)]
        
        # Filter by area (±30%)
        if covered_area > 0:
            df = df[
                (df['covered_area'] >= covered_area * 0.7) & 
                (df['covered_area'] <= covered_area * 1.3)
            ]
        
        if len(df) == 0:
            return []
        
        # Calculate distances and sort
        df['distance'] = df.apply(
            lambda r: self._haversine(lat, lng, r['lat'], r['lng']),
            axis=1
        )
        df = df.sort_values('distance')
        
        # Return top comparables
        comparables = []
        for _, row in df.head(max_results).iterrows():
            comparables.append({
                'name': row['name'][:100],
                'price': row['price'],
                'price_per_sqft': row['price_per_sqft'],
                'bedrooms': row['bedrooms'],
                'covered_area': row['covered_area'],
                'distance_km': round(row['distance'], 2)
            })
        
        return comparables
    
    def estimate(
        self,
        lat: float,
        lng: float,
        bedrooms: int = 2,
        bathrooms: int = 2,
        covered_area: float = 1000,
        floors: int = 1,
        property_type: str = 'residential'
    ) -> ValuationResult:
        """Alias for valuate() method for API compatibility."""
        return self.valuate(lat, lng, bedrooms, bathrooms, covered_area, floors, property_type)
    
    def get_market_stats(
        self,
        lat: float,
        lng: float,
        radius_km: float = 2.0,
        property_type: str = None
    ) -> Dict[str, Any]:
        """Get market statistics for an area."""
        if self.properties_df is None:
            return {'error': 'No property data available'}
        
        df = self.properties_df.copy()
        
        # Filter by type
        if property_type:
            df = df[df['category'].str.contains(property_type)]
        
        # Filter by radius
        df['distance'] = df.apply(
            lambda r: self._haversine(lat, lng, r['lat'], r['lng']),
            axis=1
        )
        df = df[df['distance'] <= radius_km]
        
        if len(df) == 0:
            return {
                'total_properties': 0,
                'message': f'No properties found within {radius_km}km'
            }
        
        return {
            'total_properties': len(df),
            'avg_price': float(df['price'].mean()),
            'median_price': float(df['price'].median()),
            'min_price': float(df['price'].min()),
            'max_price': float(df['price'].max()),
            'avg_price_per_sqft': float(df['price_per_sqft'].mean()),
            'avg_bedrooms': float(df['bedrooms'].mean()),
            'avg_covered_area': float(df['covered_area'].mean()),
            'by_category': df['category'].value_counts().to_dict()
        }


# Singleton instance
_valuation_model: Optional[PropertyValuationModel] = None


def get_valuation_model(data_dir: Path = None) -> PropertyValuationModel:
    """Get or create the valuation model singleton."""
    global _valuation_model
    if _valuation_model is None:
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / 'storage'
        _valuation_model = PropertyValuationModel(data_dir)
    return _valuation_model
