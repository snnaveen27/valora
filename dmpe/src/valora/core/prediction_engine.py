"""
DMPE Prediction Engine
Machine learning models for real estate price prediction and market analysis
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class PredictionModel:
    """Base class for prediction models."""
    
    def __init__(self, model_type: str = "xgboost"):
        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.feature_columns = []
        self.target_column = "price"
        self.is_trained = False
        
    def get_model(self):
        """Get the appropriate model based on type."""
        models = {
            "xgboost": XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            ),
            "random_forest": RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            ),
            "gradient_boost": GradientBoostingRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            ),
            "linear": LinearRegression(),
            "ridge": Ridge(alpha=1.0),
            "lasso": Lasso(alpha=1.0)
        }
        
        return models.get(self.model_type, models["xgboost"])
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Prepare features for training/prediction."""
        df = df.copy()
        
        # Select numeric features
        numeric_features = [
            'area_sqft', 'bedrooms', 'bathrooms', 'balconies',
            'amenities_count', 'landmark_count', 'days_since_listed',
            'latitude', 'longitude'
        ]
        
        # Select categorical features
        categorical_features = ['property_type', 'city', 'locality']
        
        # Filter available features
        available_numeric = [col for col in numeric_features if col in df.columns]
        available_categorical = [col for col in categorical_features if col in df.columns]
        
        # Handle categorical variables
        df_encoded = df[available_numeric].copy()
        
        for col in available_categorical:
            if df[col].dtype == 'object':
                # Use label encoding for high cardinality features
                le = LabelEncoder()
                df_encoded[f"{col}_encoded"] = le.fit_transform(df[col].astype(str))
        
        # Create interaction features
        if 'area_sqft' in df_encoded.columns and 'bedrooms' in df_encoded.columns:
            df_encoded['area_per_bedroom'] = df_encoded['area_sqft'] / df_encoded['bedrooms'].replace(0, np.nan)
        
        if 'latitude' in df_encoded.columns and 'longitude' in df_encoded.columns:
            df_encoded['distance_from_center'] = np.sqrt(
                (df_encoded['latitude'] - 12.9716)**2 + 
                (df_encoded['longitude'] - 77.5946)**2
            )  # Distance from Bangalore center
        
        # Fill missing values
        df_encoded = df_encoded.fillna(df_encoded.median())
        
        feature_columns = df_encoded.columns.tolist()
        
        return df_encoded, feature_columns
    
    def train(self, df: pd.DataFrame, target_column: str = "price"):
        """Train the prediction model."""
        self.target_column = target_column
        
        # Prepare features
        X, self.feature_columns = self.prepare_features(df)
        y = df[target_column]
        
        # Remove rows with missing target
        mask = y.notna()
        X, y = X[mask], y[mask]
        
        if len(X) < 100:
            logger.warning(f"Small dataset size: {len(X)} samples")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Create pipeline
        self.model = Pipeline([
            ('scaler', StandardScaler()),
            ('regressor', self.get_model())
        ])
        
        # Train model
        logger.info(f"Training {self.model_type} model with {len(X_train)} samples")
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        y_pred = self.model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        
        logger.info(f"Model trained - Train R²: {train_score:.3f}, Test R²: {test_score:.3f}")
        logger.info(f"MAE: {mae:,.0f}, RMSE: {rmse:,.0f}")
        
        self.is_trained = True
        
        return {
            'train_r2': train_score,
            'test_r2': test_score,
            'mae': mae,
            'rmse': rmse,
            'samples': len(X_train)
        }
    
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Make predictions on new data."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Prepare features using same columns
        X, _ = self.prepare_features(df)
        
        # Ensure same feature order
        X = X[self.feature_columns]
        
        # Make predictions
        predictions = self.model.predict(X)
        
        return predictions
    
    def predict_with_confidence(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Make predictions with confidence intervals."""
        predictions = self.predict(df)
        
        # Simple confidence estimation based on training error
        # For more accurate intervals, use quantile regression or bootstrapping
        confidence = np.full(len(predictions), 0.8)  # 80% confidence
        
        return predictions, confidence
    
    def save_model(self, filepath: str):
        """Save the trained model."""
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")
        
        model_data = {
            'model': self.model,
            'feature_columns': self.feature_columns,
            'target_column': self.target_column,
            'model_type': self.model_type,
            'metadata': {
                'trained_at': datetime.now().isoformat(),
                'is_trained': self.is_trained
            }
        }
        
        joblib.dump(model_data, filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load a trained model."""
        model_data = joblib.load(filepath)
        
        self.model = model_data['model']
        self.feature_columns = model_data['feature_columns']
        self.target_column = model_data['target_column']
        self.model_type = model_data['model_type']
        self.is_trained = model_data['metadata']['is_trained']
        
        logger.info(f"Model loaded from {filepath}")

class MarketPredictionEngine:
    """Main engine for real estate market predictions."""
    
    def __init__(self, models_dir: str = None):
        self.models_dir = Path(models_dir) if models_dir else Path(__file__).parent.parent.parent.parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        self.price_models = {}
        self.rental_models = {}
        self.market_analyzer = MarketAnalyzer()
        
    def train_price_models(self, datasets: Dict[str, pd.DataFrame]):
        """Train price prediction models for different property types."""
        price_datasets = {k: v for k, v in datasets.items() if 'sale' in k or 'rent' not in k}
        
        for key, df in price_datasets.items():
            if len(df) < 50:  # Minimum samples for training
                logger.warning(f"Skipping {key} - insufficient data ({len(df)} samples)")
                continue
            
            try:
                # Train multiple models and select best
                models_to_try = ['xgboost', 'random_forest', 'gradient_boost']
                best_model = None
                best_score = -np.inf
                
                for model_type in models_to_try:
                    model = PredictionModel(model_type)
                    metrics = model.train(df, 'price')
                    
                    if metrics['test_r2'] > best_score:
                        best_score = metrics['test_r2']
                        best_model = model
                
                if best_model:
                    self.price_models[key] = best_model
                    model_path = self.models_dir / f"price_model_{key.replace('/', '_')}.joblib"
                    best_model.save_model(str(model_path))
                    
                    logger.info(f"Trained price model for {key} - R²: {best_score:.3f}")
                
            except Exception as e:
                logger.error(f"Error training price model for {key}: {e}")
    
    def train_rental_models(self, datasets: Dict[str, pd.DataFrame]):
        """Train rental yield prediction models."""
        rental_datasets = {k: v for k, v in datasets.items() if 'rent' in k}
        
        for key, df in rental_datasets.items():
            if len(df) < 50:
                continue
            
            try:
                model = PredictionModel('xgboost')
                metrics = model.train(df, 'price')
                
                self.rental_models[key] = model
                model_path = self.models_dir / f"rental_model_{key.replace('/', '_')}.joblib"
                model.save_model(str(model_path))
                
                logger.info(f"Trained rental model for {key} - R²: {metrics['test_r2']:.3f}")
                
            except Exception as e:
                logger.error(f"Error training rental model for {key}: {e}")
    
    def predict_property_price(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict price for a single property."""
        df = pd.DataFrame([property_data])
        
        # Determine which model to use
        city = property_data.get('city', 'Unknown')
        prop_type = property_data.get('property_type', 'residential_apartment')
        listing_type = property_data.get('listing_type', 'sale')
        
        model_key = f"{city}_{prop_type}_{listing_type}"
        
        if model_key in self.price_models:
            model = self.price_models[model_key]
            prediction, confidence = model.predict_with_confidence(df)
            
            return {
                'predicted_price': float(prediction[0]),
                'confidence': float(confidence[0]),
                'model_used': model.model_type,
                'currency': 'INR'
            }
        else:
            # Fallback to generic model
            logger.warning(f"No specific model for {model_key}, using fallback")
            return self._fallback_prediction(property_data)
    
    def _fallback_prediction(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback prediction using simple heuristics."""
        area = property_data.get('area_sqft', 1000)
        bedrooms = property_data.get('bedrooms', 2)
        prop_type = property_data.get('property_type', 'residential_apartment')
        
        # Base rates per sqft (can be made city-specific)
        base_rates = {
            'residential_apartment': 12000,
            'residential_house': 8000,
            'commercial_office': 15000,
            'commercial_shop': 20000
        }
        
        base_rate = base_rates.get(prop_type, 10000)
        estimated_price = area * base_rate * (1 + bedrooms * 0.1)
        
        return {
            'predicted_price': estimated_price,
            'confidence': 0.5,
            'model_used': 'heuristic_fallback',
            'currency': 'INR'
        }
    
    def generate_market_forecast(self, datasets: Dict[str, pd.DataFrame], 
                                periods: int = 12) -> Dict[str, Any]:
        """Generate market forecasts for future periods."""
        forecast = {}
        
        for key, df in datasets.items():
            if len(df) < 100:
                continue
            
            # Simple time series forecast based on historical trends
            if 'listing_date' in df.columns:
                df['listing_date'] = pd.to_datetime(df['listing_date'])
                monthly_prices = df.groupby(df['listing_date'].dt.to_period('M'))['price'].mean()
                
                if len(monthly_prices) >= 3:
                    # Calculate trend
                    trend = np.polyfit(range(len(monthly_prices)), monthly_prices.values, 1)
                    
                    # Forecast future prices
                    future_periods = np.arange(len(monthly_prices), len(monthly_prices) + periods)
                    future_prices = np.polyval(trend, future_periods)
                    
                    forecast[key] = {
                        'current_avg_price': float(monthly_prices.iloc[-1]),
                        'forecast_1yr': float(future_prices[-1]) if periods >= 12 else None,
                        'forecast_3yr': float(future_prices[-1] * (1 + trend[0] * 24)) if periods >= 36 else None,
                        'trend_direction': 'increasing' if trend[0] > 0 else 'decreasing',
                        'monthly_growth_rate': float(trend[0])
                    }
        
        return forecast

class MarketAnalyzer:
    """Analyze market trends and generate insights."""
    
    def analyze_price_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze price trends in the dataset."""
        if len(df) == 0:
            return {}
        
        analysis = {
            'price_distribution': {
                'mean': float(df['price'].mean()),
                'median': float(df['price'].median()),
                'std': float(df['price'].std()),
                'min': float(df['price'].min()),
                'max': float(df['price'].max())
            },
            'price_per_sqft_stats': {
                'mean': float(df['price_per_sq_ft'].mean()) if 'price_per_sq_ft' in df.columns else None,
                'median': float(df['price_per_sq_ft'].median()) if 'price_per_sq_ft' in df.columns else None
            }
        }
        
        # Location-based analysis
        if 'locality' in df.columns:
            locality_stats = df.groupby('locality')['price'].agg(['mean', 'count', 'std'])
            top_localities = locality_stats.nlargest(10, 'mean')
            
            analysis['top_localities'] = {
                locality: {
                    'avg_price': float(row['mean']),
                    'property_count': int(row['count']),
                    'price_volatility': float(row['std'])
                }
                for locality, row in top_localities.iterrows()
            }
        
        # Investment analysis
        if 'investment_score' in df.columns:
            high_investment = df[df['investment_score'] > 0.7]
            analysis['investment_opportunities'] = {
                'high_score_properties': len(high_investment),
                'percentage': float(len(high_investment) / len(df) * 100),
                'avg_score': float(df['investment_score'].mean())
            }
        
        return analysis

if __name__ == "__main__":
    # Example usage
    from .data.real_estate_processor import UnifiedRealEstateProcessor
    
    # Load and process data
    processor = UnifiedRealEstateProcessor()
    datasets = processor.process_all_data()
    
    # Train prediction models
    engine = MarketPredictionEngine()
    engine.train_price_models(datasets)
    
    # Generate market forecast
    forecast = engine.generate_market_forecast(datasets)
    
    print("DMPE Prediction Engine Ready!")
    print(f"Trained models for {len(engine.price_models)} property types")
