"""
Data processing and feature engineering for real estate data.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from geopy.geocoders import Nominatim
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    FunctionTransformer,
    OneHotEncoder,
    StandardScaler,
    MinMaxScaler
)

class DataProcessor:
    """Process and transform real estate data."""
    
    def __init__(
        self,
        numeric_features: Optional[List[str]] = None,
        categorical_features: Optional[List[str]] = None,
        text_features: Optional[List[str]] = None,
        date_features: Optional[List[str]] = None,
        target_column: Optional[str] = None,
        drop_columns: Optional[List[str]] = None
    ):
        """Initialize the data processor.
        
        Args:
            numeric_features: List of numeric feature names
            categorical_features: List of categorical feature names
            text_features: List of text feature names
            date_features: List of date feature names
            target_column: Name of the target column
            drop_columns: List of columns to drop
        """
        self.numeric_features = numeric_features or []
        self.categorical_features = categorical_features or []
        self.text_features = text_features or []
        self.date_features = date_features or []
        self.target_column = target_column
        self.drop_columns = drop_columns or []
        
        # Initialize transformers
        self._init_transformers()
    
    def _init_transformers(self) -> None:
        """Initialize the transformers."""
        # Numeric pipeline
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])
        
        # Categorical pipeline
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
        ])
        
        # Text pipeline (simple for now, can be extended)
        text_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='constant', fill_value='')),
            ('text_cleaner', FunctionTransformer(self._clean_text, validate=False))
        ])
        
        # Date pipeline
        date_transformer = Pipeline(steps=[
            ('date_processor', FunctionTransformer(self._process_dates, validate=False))
        ])
        
        # Combine all transformers
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, self.numeric_features),
                ('cat', categorical_transformer, self.categorical_features),
                ('text', text_transformer, self.text_features),
                ('date', date_transformer, self.date_features)
            ],
            remainder='drop'  # Drop columns not specified in any transformer
        )
    
    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> 'DataProcessor':
        """Fit the preprocessor on the data."""
        self.preprocessor.fit(X, y)
        return self
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform the data."""
        # Make a copy to avoid modifying the original data
        X_transformed = X.copy()
        
        # Apply preprocessing
        processed_data = self.preprocessor.transform(X_transformed)
        
        # Get feature names after transformation
        feature_names = self.get_feature_names_out()
        
        # Convert to DataFrame
        processed_df = pd.DataFrame(
            processed_data,
            columns=feature_names,
            index=X_transformed.index
        )
        
        return processed_df
    
    def fit_transform(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> pd.DataFrame:
        """Fit and transform the data."""
        return self.fit(X, y).transform(X)
    
    def get_feature_names_out(self) -> List[str]:
        """Get feature names after transformation."""
        feature_names = []
        
        # Get feature names from each transformer
        for name, transformer, features in self.preprocessor.transformers_:
            if name == 'num':
                feature_names.extend(features)
            elif name == 'cat':
                # Get one-hot encoded feature names
                if hasattr(transformer.named_steps['onehot'], 'get_feature_names_out'):
                    cat_features = transformer.named_steps['onehot'].get_feature_names_out(features)
                    feature_names.extend(cat_features)
                else:
                    # Fallback for older scikit-learn versions
                    for feature in features:
                        feature_names.append(f"{feature}_cat")
            elif name == 'text':
                # For text features, just use the original names
                feature_names.extend(features)
            elif name == 'date':
                # For date features, add derived feature names
                for feature in features:
                    feature_names.extend([
                        f"{feature}_year",
                        f"{feature}_month",
                        f"{feature}_day",
                        f"{feature}_dayofweek",
                        f"{feature}_dayofyear"
                    ])
        
        return feature_names
    
    @staticmethod
    def _clean_text(X: pd.Series) -> pd.Series:
        """Clean text data."""
        if not isinstance(X, pd.Series):
            X = pd.Series(X)
        
        # Convert to string and lowercase
        X = X.astype(str).str.lower()
        
        # Remove special characters and extra whitespace
        X = X.str.replace(r'[^\w\s]', ' ', regex=True)
        X = X.str.replace(r'\s+', ' ', regex=True).str.strip()
        
        return X
    
    @staticmethod
    def _process_dates(X: pd.Series) -> np.ndarray:
        """Extract features from dates."""
        if not isinstance(X, pd.Series):
            X = pd.Series(X)
        
        # Convert to datetime
        dates = pd.to_datetime(X, errors='coerce')
        
        # Extract date components
        date_features = pd.DataFrame({
            'year': dates.dt.year,
            'month': dates.dt.month,
            'day': dates.dt.day,
            'dayofweek': dates.dt.dayofweek,
            'dayofyear': dates.dt.dayofyear
        })
        
        # Fill missing values with median
        date_features = date_features.fillna(date_features.median())
        
        return date_features.values


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Custom feature engineering for real estate data."""
    
    def __init__(self, add_derived_features: bool = True):
        """Initialize the feature engineer."""
        self.add_derived_features = add_derived_features
        self.geolocator = Nominatim(user_agent="valora_dmpe")
    
    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> 'FeatureEngineer':
        """Fit the feature engineer."""
        return self
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform the data by adding features."""
        X_transformed = X.copy()
        
        if not self.add_derived_features:
            return X_transformed
        
        # Add derived features if the required columns exist
        if 'area' in X_transformed.columns and 'bedrooms' in X_transformed.columns:
            X_transformed['price_per_sqft'] = X_transformed['price'] / X_transformed['area']
            X_transformed['bedroom_ratio'] = X_transformed['bedrooms'] / X_transformed['area']
        
        if 'latitude' in X_transformed.columns and 'longitude' in X_transformed.columns:
            # Add distance to city center (example: assuming 0,0 is city center)
            X_transformed['distance_to_center'] = np.sqrt(
                X_transformed['latitude']**2 + X_transformed['longitude']**2
            )
        
        # Add time-based features if date column exists
        date_columns = [col for col in X_transformed.columns if 'date' in col.lower()]
        for date_col in date_columns:
            try:
                dates = pd.to_datetime(X_transformed[date_col])
                X_transformed[f'{date_col}_year'] = dates.dt.year
                X_transformed[f'{date_col}_month'] = dates.dt.month
                X_transformed[f'{date_col}_day'] = dates.dt.day
                X_transformed[f'{date_col}_dayofweek'] = dates.dt.dayofweek
            except:
                pass
        
        return X_transformed
    
    def get_feature_names_out(self, input_features=None):
        """Get output feature names for transformation."""
        # This is a simplified version - in practice, you'd want to generate
        # the actual feature names based on the transformations
        return ['feature_1', 'feature_2']  # Replace with actual feature names
