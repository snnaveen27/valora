"""
Dynamic Market Prediction Engine (DMPE) - Enhanced Version
Predicts real-estate prices, rental yields, demand index, and market risk.
Integrates Mappls spatial features for geospatial reasoning.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import joblib
from pathlib import Path
import requests
from geopy.distance import geodesic

logger = logging.getLogger(__name__)

class DMPEEngine:
    """Enhanced Dynamic Market Prediction Engine with rental yield and demand forecasting"""
    
    def __init__(self, models_dir: str = "data/models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Model containers
        self.price_model = None
        self.rental_yield_model = None
        self.demand_model = None
        self.scalers = {}
        
        # Feature engineering parameters
        self.spatial_features = [
            'distance_to_metro', 'distance_to_hospital', 'distance_to_school',
            'distance_to_mall', 'poi_density', 'infrastructure_score'
        ]
        
        self.property_features = [
            'bedrooms', 'bathrooms', 'area_sqft', 'floor', 'total_floors',
            'age_years', 'parking_spaces', 'balconies'
        ]
        
        self.market_features = [
            'avg_price_locality', 'price_growth_3m', 'price_growth_6m',
            'listings_count', 'absorption_rate', 'days_on_market'
        ]
        
        # Load pre-trained models if available
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained models from disk"""
        try:
            price_model_path = self.models_dir / "price_model.pkl"
            rental_model_path = self.models_dir / "rental_yield_model.pkl"
            demand_model_path = self.models_dir / "demand_model.pkl"
            scalers_path = self.models_dir / "scalers.pkl"
            
            if price_model_path.exists():
                self.price_model = joblib.load(price_model_path)
                logger.info("Loaded price prediction model")
            
            if rental_model_path.exists():
                self.rental_yield_model = joblib.load(rental_model_path)
                logger.info("Loaded rental yield model")
            
            if demand_model_path.exists():
                self.demand_model = joblib.load(demand_model_path)
                logger.info("Loaded demand index model")
            
            if scalers_path.exists():
                self.scalers = joblib.load(scalers_path)
                logger.info("Loaded feature scalers")
                
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    def train_price_model(self, data: pd.DataFrame) -> Dict[str, float]:
        """Train price prediction model using XGBoost"""
        try:
            # Prepare features and target
            features = self._engineer_features(data)
            X = features[self.property_features + self.spatial_features + self.market_features]
            y = data['price']
            
            # Handle missing values
            X = X.fillna(X.median())
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            self.scalers['price'] = scaler
            
            # Train XGBoost model
            self.price_model = xgb.XGBRegressor(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=6,
                random_state=42
            )
            self.price_model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.price_model.predict(X_test_scaled)
            metrics = {
                'mae': mean_absolute_error(y_test, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
                'r2': r2_score(y_test, y_pred),
                'mape': np.mean(np.abs((y_test - y_pred) / y_test)) * 100
            }
            
            # Save model
            joblib.dump(self.price_model, self.models_dir / "price_model.pkl")
            logger.info(f"Price model trained with R²: {metrics['r2']:.3f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error training price model: {e}")
            return {}
    
    def train_rental_yield_model(self, data: pd.DataFrame) -> Dict[str, float]:
        """Train rental yield prediction model"""
        try:
            # Calculate rental yield if not present
            if 'rental_yield' not in data.columns:
                data['rental_yield'] = (data['annual_rent'] / data['price']) * 100
            
            # Filter for valid rental yield data
            rental_data = data[data['rental_yield'].notna() & (data['rental_yield'] > 0)]
            
            # Prepare features
            features = self._engineer_features(rental_data)
            X = features[self.property_features + self.spatial_features]
            y = rental_data['rental_yield']
            
            # Handle missing values
            X = X.fillna(X.median())
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            self.scalers['rental'] = scaler
            
            # Train Gradient Boosting model
            self.rental_yield_model = GradientBoostingRegressor(
                n_estimators=150,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
            self.rental_yield_model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.rental_yield_model.predict(X_test_scaled)
            metrics = {
                'mae': mean_absolute_error(y_test, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
                'r2': r2_score(y_test, y_pred)
            }
            
            # Save model
            joblib.dump(self.rental_yield_model, self.models_dir / "rental_yield_model.pkl")
            logger.info(f"Rental yield model trained with R²: {metrics['r2']:.3f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error training rental yield model: {e}")
            return {}
    
    def train_demand_model(self, data: pd.DataFrame) -> Dict[str, float]:
        """Train demand index prediction model"""
        try:
            # Calculate demand index based on multiple factors
            data['demand_index'] = self._calculate_demand_index(data)
            
            # Prepare features
            features = self._engineer_features(data)
            X = features[self.spatial_features + self.market_features]
            y = data['demand_index']
            
            # Handle missing values
            X = X.fillna(X.median())
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            self.scalers['demand'] = scaler
            
            # Train Random Forest model
            self.demand_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=8,
                random_state=42
            )
            self.demand_model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.demand_model.predict(X_test_scaled)
            metrics = {
                'mae': mean_absolute_error(y_test, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
                'r2': r2_score(y_test, y_pred)
            }
            
            # Save model
            joblib.dump(self.demand_model, self.models_dir / "demand_model.pkl")
            logger.info(f"Demand model trained with R²: {metrics['r2']:.3f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error training demand model: {e}")
            return {}
    
    def _calculate_demand_index(self, data: pd.DataFrame) -> pd.Series:
        """Calculate demand index based on multiple market indicators"""
        # Normalize various indicators to 0-100 scale
        demand_index = pd.Series(index=data.index, dtype=float)
        
        # Factor 1: Days on market (inverse relationship)
        if 'days_on_market' in data.columns:
            dom_score = 100 - (data['days_on_market'].clip(upper=180) / 180 * 100)
        else:
            dom_score = 50  # neutral if not available
        
        # Factor 2: Price growth momentum
        if 'price_growth_3m' in data.columns:
            growth_score = data['price_growth_3m'].clip(-20, 20) * 2.5 + 50
        else:
            growth_score = 50
        
        # Factor 3: Listings density (inverse - fewer listings = higher demand)
        if 'listings_count' in data.columns:
            density_score = 100 - (data['listings_count'].clip(upper=100) / 100 * 50)
        else:
            density_score = 50
        
        # Factor 4: Infrastructure score
        if 'infrastructure_score' in data.columns:
            infra_score = data['infrastructure_score'] * 10
        else:
            infra_score = 50
        
        # Weighted average
        demand_index = (
            dom_score * 0.3 + 
            growth_score * 0.3 + 
            density_score * 0.2 + 
            infra_score * 0.2
        )
        
        return demand_index.clip(0, 100)
    
    def _engineer_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Engineer features for model training and prediction"""
        features = data.copy()
        
        # Property age
        if 'built_year' in features.columns:
            features['age_years'] = datetime.now().year - features['built_year']
        else:
            features['age_years'] = 5  # default
        
        # Price per sqft
        if 'price' in features.columns and 'area_sqft' in features.columns:
            features['price_per_sqft'] = features['price'] / features['area_sqft'].replace(0, 1)
        
        # Fill missing spatial features with defaults
        for feat in self.spatial_features:
            if feat not in features.columns:
                features[feat] = np.random.normal(5, 2, len(features))  # simulated data
        
        # Fill missing market features
        for feat in self.market_features:
            if feat not in features.columns:
                if 'price' in feat:
                    features[feat] = np.random.normal(100000, 50000, len(features))
                else:
                    features[feat] = np.random.normal(50, 20, len(features))
        
        # Fill missing property features
        for feat in self.property_features:
            if feat not in features.columns:
                features[feat] = 2  # default value
        
        return features
    
    def fetch_mappls_spatial_features(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch spatial features using MapplsService with DB caching and POI persistence"""
        try:
            # Lazy import to avoid circular deps at startup
            from backend.services.mappls_integration import MapplsService
            svc = MapplsService()
            # This call internally caches to DB (when configured) and computes distances/scores
            features = svc.calculate_spatial_features(lat, lon)
            return features or self._default_spatial_features()
        except Exception as e:
            logger.error(f"Error fetching Mappls features: {e}")
            return self._default_spatial_features()
    
    def _process_mappls_response(self, data: Dict, lat: float, lon: float) -> Dict[str, Any]:
        """Process Mappls API response to extract spatial features"""
        features = {
            'distance_to_metro': 10.0,
            'distance_to_hospital': 5.0,
            'distance_to_school': 3.0,
            'distance_to_mall': 7.0,
            'poi_density': 0,
            'infrastructure_score': 5.0
        }
        
        if 'suggestedLocations' in data:
            pois = data['suggestedLocations']
            features['poi_density'] = len(pois)
            
            for poi in pois:
                poi_type = poi.get('type', '').lower()
                if 'lat' in poi and 'lng' in poi:
                    distance = geodesic((lat, lon), (poi['lat'], poi['lng'])).km
                    
                    if 'metro' in poi_type or 'station' in poi_type:
                        features['distance_to_metro'] = min(features['distance_to_metro'], distance)
                    elif 'hospital' in poi_type or 'medical' in poi_type:
                        features['distance_to_hospital'] = min(features['distance_to_hospital'], distance)
                    elif 'school' in poi_type or 'education' in poi_type:
                        features['distance_to_school'] = min(features['distance_to_school'], distance)
                    elif 'mall' in poi_type or 'shopping' in poi_type:
                        features['distance_to_mall'] = min(features['distance_to_mall'], distance)
            
            # Calculate infrastructure score (0-10)
            features['infrastructure_score'] = min(10, features['poi_density'] / 5)
        
        return features
    
    def _default_spatial_features(self) -> Dict[str, Any]:
        """Return default spatial features when API is unavailable"""
        return {
            'distance_to_metro': 5.0,
            'distance_to_hospital': 3.0,
            'distance_to_school': 2.0,
            'distance_to_mall': 4.0,
            'poi_density': 10,
            'infrastructure_score': 6.0
        }
    
    def predict(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive prediction including price, rental yield, and demand index
        """
        try:
            # Convert to DataFrame for processing
            df = pd.DataFrame([property_data])
            
            # Fetch Mappls spatial features if coordinates available
            if 'latitude' in property_data and 'longitude' in property_data:
                spatial_features = self.fetch_mappls_spatial_features(
                    property_data['latitude'], 
                    property_data['longitude']
                )
                for key, value in spatial_features.items():
                    df[key] = value
            
            # Engineer features
            features = self._engineer_features(df)
            
            predictions = {
                'timestamp': datetime.now().isoformat(),
                'property_id': property_data.get('id', 'unknown'),
                'location': {
                    'latitude': property_data.get('latitude'),
                    'longitude': property_data.get('longitude'),
                    'city': property_data.get('city', 'Unknown'),
                    'locality': property_data.get('locality', 'Unknown')
                }
            }
            
            # Price prediction
            if self.price_model and 'price' in self.scalers:
                X_price = features[self.property_features + self.spatial_features + self.market_features]
                X_price = X_price.fillna(X_price.median())
                X_price_scaled = self.scalers['price'].transform(X_price)
                
                price_pred = self.price_model.predict(X_price_scaled)[0]
                predictions['price'] = {
                    'predicted': float(price_pred),
                    'confidence': 0.85,  # Would be calculated from prediction intervals
                    'range': {
                        'min': float(price_pred * 0.9),
                        'max': float(price_pred * 1.1)
                    }
                }
            else:
                predictions['price'] = {
                    'predicted': property_data.get('price', 5000000),
                    'confidence': 0.5,
                    'error': 'Model not trained'
                }
            
            # Rental yield prediction
            if self.rental_yield_model and 'rental' in self.scalers:
                X_rental = features[self.property_features + self.spatial_features]
                X_rental = X_rental.fillna(X_rental.median())
                X_rental_scaled = self.scalers['rental'].transform(X_rental)
                
                rental_yield_pred = self.rental_yield_model.predict(X_rental_scaled)[0]
                predictions['rental_yield'] = {
                    'predicted_percentage': float(rental_yield_pred),
                    'annual_rental_income': float(price_pred * rental_yield_pred / 100) if 'price_pred' in locals() else None,
                    'confidence': 0.8
                }
            else:
                # Default rental yield calculation
                default_yield = 3.5  # Average rental yield
                predictions['rental_yield'] = {
                    'predicted_percentage': default_yield,
                    'annual_rental_income': property_data.get('price', 5000000) * default_yield / 100,
                    'confidence': 0.4,
                    'error': 'Model not trained'
                }
            
            # Demand index prediction
            if self.demand_model and 'demand' in self.scalers:
                X_demand = features[self.spatial_features + self.market_features]
                X_demand = X_demand.fillna(X_demand.median())
                X_demand_scaled = self.scalers['demand'].transform(X_demand)
                
                demand_pred = self.demand_model.predict(X_demand_scaled)[0]
                predictions['demand_index'] = {
                    'score': float(demand_pred),
                    'category': self._categorize_demand(demand_pred),
                    'trend': 'increasing' if demand_pred > 70 else 'stable' if demand_pred > 40 else 'decreasing',
                    'confidence': 0.75
                }
            else:
                # Calculate demand from available data
                demand_score = self._calculate_demand_index(df).iloc[0]
                predictions['demand_index'] = {
                    'score': float(demand_score),
                    'category': self._categorize_demand(demand_score),
                    'trend': 'stable',
                    'confidence': 0.5,
                    'error': 'Model not trained'
                }
            
            # Investment metrics
            predictions['investment_metrics'] = self._calculate_investment_metrics(predictions)
            
            # Market insights
            predictions['market_insights'] = self._generate_market_insights(predictions)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _categorize_demand(self, demand_score: float) -> str:
        """Categorize demand level"""
        if demand_score >= 80:
            return 'Very High'
        elif demand_score >= 65:
            return 'High'
        elif demand_score >= 45:
            return 'Moderate'
        elif demand_score >= 25:
            return 'Low'
        else:
            return 'Very Low'
    
    def _calculate_investment_metrics(self, predictions: Dict) -> Dict[str, Any]:
        """Calculate investment-related metrics"""
        metrics = {}
        
        if 'price' in predictions and 'rental_yield' in predictions:
            price = predictions['price']['predicted']
            rental_yield = predictions['rental_yield']['predicted_percentage']
            
            # ROI calculation
            metrics['roi_years'] = round(100 / rental_yield, 1) if rental_yield > 0 else None
            
            # Cap rate
            metrics['cap_rate'] = rental_yield
            
            # Monthly rental estimate
            metrics['estimated_monthly_rent'] = round(price * rental_yield / 100 / 12, 0)
            
            # Investment score (0-100)
            demand_score = predictions.get('demand_index', {}).get('score', 50)
            investment_score = (rental_yield * 10 + demand_score) / 2
            metrics['investment_score'] = min(100, max(0, investment_score))
            
            # Risk assessment
            if demand_score < 30:
                risk_level = 'High'
            elif demand_score < 60:
                risk_level = 'Medium'
            else:
                risk_level = 'Low'
            metrics['risk_level'] = risk_level
        
        return metrics
    
    def _generate_market_insights(self, predictions: Dict) -> List[str]:
        """Generate actionable market insights"""
        insights = []
        
        demand_score = predictions.get('demand_index', {}).get('score', 50)
        rental_yield = predictions.get('rental_yield', {}).get('predicted_percentage', 3.5)
        investment_score = predictions.get('investment_metrics', {}).get('investment_score', 50)
        
        if demand_score > 70:
            insights.append("High demand area - Good for quick sale/rent")
        elif demand_score < 30:
            insights.append("Low demand - Consider competitive pricing")
        
        if rental_yield > 4:
            insights.append(f"Excellent rental yield of {rental_yield:.1f}% - Above market average")
        elif rental_yield < 2.5:
            insights.append("Below average rental returns - Better for capital appreciation")
        
        if investment_score > 75:
            insights.append("Strong investment opportunity")
        elif investment_score < 40:
            insights.append("Careful evaluation recommended before investment")
        
        return insights
    
    def forecast_time_series(self, 
                            historical_data: pd.DataFrame,
                            periods: int = 12,
                            frequency: str = 'M') -> Dict[str, Any]:
        """Forecast future price trends using time series analysis"""
        try:
            from prophet import Prophet
            
            # Prepare data for Prophet
            df = historical_data[['date', 'price']].copy()
            df.columns = ['ds', 'y']
            
            # Initialize and fit model
            model = Prophet(
                seasonality_mode='multiplicative',
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False
            )
            model.fit(df)
            
            # Create future dataframe
            future = model.make_future_dataframe(periods=periods, freq=frequency)
            forecast = model.predict(future)
            
            # Extract predictions
            future_forecast = forecast[forecast['ds'] > df['ds'].max()]
            
            return {
                'forecast': future_forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_dict('records'),
                'trend': 'increasing' if forecast['trend'].iloc[-1] > forecast['trend'].iloc[-periods] else 'decreasing',
                'seasonality': model.seasonalities
            }
            
        except ImportError:
            logger.warning("Prophet not installed, using simple linear forecast")
            # Fallback to simple linear regression
            from sklearn.linear_model import LinearRegression
            
            X = np.arange(len(historical_data)).reshape(-1, 1)
            y = historical_data['price'].values
            
            model = LinearRegression()
            model.fit(X, y)
            
            future_X = np.arange(len(historical_data), len(historical_data) + periods).reshape(-1, 1)
            predictions = model.predict(future_X)
            
            return {
                'forecast': [{'period': i+1, 'predicted_price': p} for i, p in enumerate(predictions)],
                'trend': 'increasing' if model.coef_[0] > 0 else 'decreasing',
                'slope': float(model.coef_[0])
            }
        except Exception as e:
            logger.error(f"Forecasting error: {e}")
            return {'error': str(e)}
    
    def save_all_models(self):
        """Save all trained models and scalers"""
        try:
            if self.price_model:
                joblib.dump(self.price_model, self.models_dir / "price_model.pkl")
            if self.rental_yield_model:
                joblib.dump(self.rental_yield_model, self.models_dir / "rental_yield_model.pkl")
            if self.demand_model:
                joblib.dump(self.demand_model, self.models_dir / "demand_model.pkl")
            if self.scalers:
                joblib.dump(self.scalers, self.models_dir / "scalers.pkl")
            
            logger.info("All models saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving models: {e}")
            return False
