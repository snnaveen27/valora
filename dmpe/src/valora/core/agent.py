"""
Core agent implementation for the Dynamic Market Prediction Engine (DMPE).

This module contains the main Agent class that handles real estate market predictions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModelType(Enum):
    """Supported model types for prediction."""
    XGBOOST = 'xgboost'
    RANDOM_FOREST = 'random_forest'

@dataclass
class ModelConfig:
    """Configuration for prediction models."""
    model_type: ModelType
    target: str = 'price'
    features: List[str] = field(default_factory=list)
    test_size: float = 0.2
    random_state: int = 42
    model_params: Dict[str, Any] = field(default_factory=dict)

class DataPreprocessor:
    """Handles data preprocessing for the prediction engine."""
    
    def __init__(self):
        self.scalers = {}
        self.encoders = {}
        self.feature_stats = {}
    
    def preprocess(self, data: pd.DataFrame, config: ModelConfig) -> pd.DataFrame:
        """Preprocess the input data."""
        df = data.copy()
        
        # Handle missing values
        df = self._handle_missing_values(df)
        
        # Process features
        for feature in config.features:
            if df[feature].dtype == 'object':
                df = self._encode_categorical(df, feature)
            else:
                df = self._scale_feature(df, feature)
        
        return df
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in the dataframe."""
        # For numeric columns, fill with median
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            median_val = df[col].median()
            df[col].fillna(median_val, inplace=True)
            self.feature_stats[col] = {'median': median_val}
        
        # For categorical columns, fill with mode
        cat_cols = df.select_dtypes(include=['object']).columns
        for col in cat_cols:
            mode_val = df[col].mode()[0] if not df[col].mode().empty else 'unknown'
            df[col].fillna(mode_val, inplace=True)
        
        return df
    
    def _encode_categorical(self, df: pd.DataFrame, col: str) -> pd.DataFrame:
        """Encode categorical features."""
        if col not in self.encoders:
            self.encoders[col] = {}
            unique_vals = df[col].unique()
            self.encoders[col] = {val: idx for idx, val in enumerate(unique_vals, 1)}
        
        df[col] = df[col].map(self.encoders[col])
        return df
    
    def _scale_feature(self, df: pd.DataFrame, col: str) -> pd.DataFrame:
        """Scale numerical features."""
        if col not in self.scalers:
            self.scalers[col] = {
                'min': df[col].min(),
                'max': df[col].max()
            }
        
        min_val = self.scalers[col]['min']
        max_val = self.scalers[col]['max']
        
        if max_val > min_val:  # Avoid division by zero
            df[col] = (df[col] - min_val) / (max_val - min_val)
        
        return df

class ValoraAgent:
    """Main agent class for real estate market prediction."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Valora agent."""
        self.config = config or {}
        self.models: Dict[str, Any] = {}
        self.preprocessor = DataPreprocessor()
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for the agent."""
        self.logger = logging.getLogger('ValoraAgent')
        self.logger.setLevel(logging.INFO)
    
    def train_model(
        self,
        data: pd.DataFrame,
        model_name: str,
        config: Optional[ModelConfig] = None
    ) -> Dict[str, Any]:
        """Train a prediction model."""
        try:
            config = config or self._get_default_config()
            
            # Preprocess data
            processed_data = self.preprocessor.preprocess(data, config)
            
            # Split into features and target
            X = processed_data[config.features]
            y = processed_data[config.target]
            
            # Split into train and test sets
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=config.test_size, random_state=config.random_state
            )
            
            # Train model
            if config.model_type == ModelType.XGBOOST:
                model = self._train_xgboost(X_train, y_train, config)
            elif config.model_type == ModelType.RANDOM_FOREST:
                model = self._train_random_forest(X_train, y_train, config)
            else:
                raise ValueError(f"Unsupported model type: {config.model_type}")
            
            # Evaluate model
            metrics = self._evaluate_model(model, X_test, y_test)
            
            # Save model
            self.models[model_name] = {
                'model': model,
                'config': config,
                'metrics': metrics,
                'trained_at': datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Trained {config.model_type.value} model '{model_name}' with metrics: {metrics}")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error training model: {str(e)}", exc_info=True)
            raise
    
    def predict(
        self,
        model_name: str,
        input_data: Union[pd.DataFrame, Dict[str, Any]]
    ) -> Union[float, np.ndarray]:
        """Generate predictions using a trained model."""
        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' not found. Train the model first.")
        
        model_info = self.models[model_name]
        model = model_info['model']
        config = model_info['config']
        
        # Convert dict to DataFrame if needed
        if isinstance(input_data, dict):
            input_df = pd.DataFrame([input_data])
        else:
            input_df = input_data.copy()
        
        # Preprocess input data
        processed_data = self.preprocessor.preprocess(input_df, config)
        
        # Make predictions
        predictions = model.predict(processed_data[config.features])
        
        return predictions[0] if isinstance(input_data, dict) else predictions
    
    def save_model(self, model_name: str, path: Union[str, Path]) -> None:
        """Save a trained model to disk."""
        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' not found.")
        
        model_info = self.models[model_name]
        model_data = {
            'model_type': model_info['config'].model_type.value,
            'config': vars(model_info['config']),
            'metrics': model_info['metrics'],
            'trained_at': model_info['trained_at'],
            'preprocessor': {
                'scalers': model_info.get('preprocessor', {}).get('scalers', {}),
                'encoders': model_info.get('preprocessor', {}).get('encoders', {})
            }
        }
        
        # Save model and metadata
        model_path = Path(path) / f"{model_name}"
        model_path.mkdir(parents=True, exist_ok=True)
        
        # Save model
        joblib.dump(model_info['model'], model_path / 'model.joblib')
        
        # Save metadata
        with open(model_path / 'metadata.json', 'w') as f:
            json.dump(model_data, f, indent=2)
        
        self.logger.info(f"Saved model '{model_name}' to {model_path}")
    
    def load_model(self, model_name: str, path: Union[str, Path]) -> None:
        """Load a trained model from disk."""
        model_path = Path(path) / model_name
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model directory not found: {model_path}")
        
        # Load metadata
        with open(model_path / 'metadata.json', 'r') as f:
            model_data = json.load(f)
        
        # Load model
        model = joblib.load(model_path / 'model.joblib')
        
        # Reconstruct config
        config_data = model_data['config']
        config = ModelConfig(
            model_type=ModelType(config_data['model_type']),
            target=config_data['target'],
            features=config_data['features'],
            test_size=config_data['test_size'],
            random_state=config_data['random_state'],
            model_params=config_data['model_params']
        )
        
        # Store model
        self.models[model_name] = {
            'model': model,
            'config': config,
            'metrics': model_data['metrics'],
            'trained_at': model_data['trained_at']
        }
        
        # Restore preprocessor state if available
        if 'preprocessor' in model_data:
            self.preprocessor.scalers = model_data['preprocessor'].get('scalers', {})
            self.preprocessor.encoders = model_data['preprocessor'].get('encoders', {})
        
        self.logger.info(f"Loaded model '{model_name}' from {model_path}")
    
    def _train_xgboost(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        config: ModelConfig
    ) -> XGBRegressor:
        """Train an XGBoost model."""
        params = {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'random_state': config.random_state,
            **config.model_params
        }
        
        model = XGBRegressor(**params)
        model.fit(X_train, y_train)
        return model
    
    def _train_random_forest(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        config: ModelConfig
    ) -> RandomForestRegressor:
        """Train a Random Forest model."""
        params = {
            'n_estimators': 100,
            'max_depth': None,
            'random_state': config.random_state,
            **config.model_params
        }
        
        model = RandomForestRegressor(**params)
        model.fit(X_train, y_train)
        return model
    
    def _evaluate_model(
        self,
        model: Any,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict[str, float]:
        """Evaluate model performance."""
        y_pred = model.predict(X_test)
        
        return {
            'mae': mean_absolute_error(y_test, y_pred),
            'mse': mean_squared_error(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
            'r2': r2_score(y_test, y_pred)
        }
    
    def _get_default_config(self) -> ModelConfig:
        """Get default model configuration."""
        return ModelConfig(
            model_type=ModelType.XGBOOST,
            features=['area', 'bedrooms', 'bathrooms', 'location'],
            model_params={
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1
            }
        )
