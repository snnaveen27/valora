"""
Data Processor Service
Handles data loading, cleaning, and feature engineering for DMPE
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Any, Optional
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DataProcessor:
    """Processes and prepares real estate data for analysis"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.processed_cache = {}

    def get_cached_datasets(self, refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """Load processed datasets from data/processed and cache them."""
        try:
            if self.processed_cache and not refresh:
                return self.processed_cache

            processed_dir = self.data_dir / "processed"
            if not processed_dir.exists():
                logger.warning(f"Processed directory not found: {processed_dir}")
                return {}

            datasets: Dict[str, pd.DataFrame] = {}
            for csv_file in processed_dir.glob("*.csv"):
                try:
                    df = pd.read_csv(csv_file)
                    key = csv_file.stem
                    datasets[key] = df
                except Exception as e:
                    logger.warning(f"Failed to read {csv_file.name}: {e}")

            self.processed_cache = datasets
            logger.info(f"Loaded {len(self.processed_cache)} processed datasets from {processed_dir}")
            return self.processed_cache
        except Exception as e:
            logger.error(f"Error loading cached datasets: {e}")
            return {}
    
    def load_training_data(self) -> pd.DataFrame:
        """Load and prepare training data for DMPE models"""
        try:
            # Check for existing processed data
            processed_file = self.data_dir / "processed" / "processed_training_data.csv"
            if processed_file.exists():
                logger.info("Loading existing processed training data")
                return pd.read_csv(processed_file)
            
            # Load MagicBricks data from unified raw folder
            magicbricks_data = self._load_magicbricks_data()
            if magicbricks_data is not None and len(magicbricks_data) > 0:
                logger.info(f"Loaded MagicBricks data: {len(magicbricks_data)} records")
                
                # Add synthetic features for training
                magicbricks_data = self._add_synthetic_features(magicbricks_data)
                
                # Save processed data
                processed_file.parent.mkdir(parents=True, exist_ok=True)
                magicbricks_data.to_csv(processed_file, index=False)
                logger.info(f"Saved processed MagicBricks training data")
                
                return magicbricks_data
            
            # Fallback to DMPE processor if MagicBricks data not available
            dmpe_path = Path("dmpe/src/valora/data")
            if dmpe_path.exists():
                from dmpe.src.valora.data.real_estate_processor import UnifiedRealEstateProcessor
                processor = UnifiedRealEstateProcessor()
                datasets = processor.process_all_data()
                
                # Combine all datasets
                all_data = []
                for key, df in datasets.items():
                    if df is not None and len(df) > 0:
                        df['dataset_source'] = key
                        all_data.append(df)
                
                if all_data:
                    combined_df = pd.concat(all_data, ignore_index=True)
                    
                    # Add synthetic features for training
                    combined_df = self._add_synthetic_features(combined_df)
                    
                    # Save processed data
                    processed_file.parent.mkdir(parents=True, exist_ok=True)
                    combined_df.to_csv(processed_file, index=False)
                    logger.info(f"Saved processed training data: {len(combined_df)} records")
                    
                    return combined_df
            
            # Generate synthetic data if no real data available
            logger.warning("No real data found, generating synthetic data")
            return self._generate_synthetic_data()
            
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return self._generate_synthetic_data()
    
    def _load_magicbricks_data(self) -> Optional[pd.DataFrame]:
        """Load MagicBricks data from unified raw data folder"""
        try:
            raw_dir = self.data_dir / "raw"
            if not raw_dir.exists():
                logger.warning(f"Raw data directory not found: {raw_dir}")
                return None
            
            # Load Bangalore residential apartment data (main dataset)
            apartment_file = raw_dir / "bangalore-residential-apartment.csv"
            if apartment_file.exists():
                logger.info(f"Loading MagicBricks apartment data from {apartment_file}")
                df = pd.read_csv(apartment_file)
                
                # Clean and standardize the data
                df = self._clean_magicbricks_data(df)
                return df
            else:
                logger.warning(f"MagicBricks apartment file not found: {apartment_file}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading MagicBricks data: {e}")
            return None
    
    def _clean_magicbricks_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize MagicBricks data"""
        try:
            # Remove rows with missing critical data
            df = df.dropna(subset=['price', 'area', 'location'])
            
            # Standardize column names
            column_mapping = {
                'price': 'price',
                'area': 'area_sqft',
                'location': 'locality',
                'bedroom': 'bedrooms',
                'bathroom': 'bathrooms',
                'price_per_sqft': 'price_per_sqft'
            }
            
            # Rename columns if they exist
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns and new_col not in df.columns:
                    df = df.rename(columns={old_col: new_col})
            
            # Ensure numeric columns are properly typed
            numeric_cols = ['price', 'area_sqft', 'bedrooms', 'bathrooms', 'price_per_sqft']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Add city column
            df['city'] = 'Bangalore'
            
            # Filter out unrealistic data
            if 'price' in df.columns:
                df = df[(df['price'] >= 1000000) & (df['price'] <= 100000000)]  # 10L to 10Cr
            
            if 'area_sqft' in df.columns:
                df = df[(df['area_sqft'] >= 300) & (df['area_sqft'] <= 10000)]  # 300sqft to 10000sqft
            
            logger.info(f"Cleaned MagicBricks data: {len(df)} records remaining")
            return df
            
        except Exception as e:
            logger.error(f"Error cleaning MagicBricks data: {e}")
            return df
    
    def _add_synthetic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add synthetic features for model training"""
        # Add rental data if not present
        if 'annual_rent' not in df.columns:
            # Estimate annual rent as 3-4% of property value
            df['annual_rent'] = df['price'] * np.random.uniform(0.03, 0.04, len(df))
        
        if 'rental_yield' not in df.columns:
            df['rental_yield'] = (df['annual_rent'] / df['price']) * 100
        
        # Add market features
        if 'days_on_market' not in df.columns:
            df['days_on_market'] = np.random.exponential(45, len(df))
        
        if 'price_growth_3m' not in df.columns:
            df['price_growth_3m'] = np.random.normal(2, 5, len(df))
        
        if 'price_growth_6m' not in df.columns:
            df['price_growth_6m'] = np.random.normal(4, 8, len(df))
        
        if 'listings_count' not in df.columns:
            df['listings_count'] = np.random.poisson(30, len(df))
        
        if 'absorption_rate' not in df.columns:
            df['absorption_rate'] = np.random.uniform(0.3, 0.8, len(df))
        
        # Add spatial features
        if 'distance_to_metro' not in df.columns:
            df['distance_to_metro'] = np.random.exponential(3, len(df))
        
        if 'distance_to_hospital' not in df.columns:
            df['distance_to_hospital'] = np.random.exponential(2, len(df))
        
        if 'distance_to_school' not in df.columns:
            df['distance_to_school'] = np.random.exponential(1.5, len(df))
        
        if 'distance_to_mall' not in df.columns:
            df['distance_to_mall'] = np.random.exponential(4, len(df))
        
        if 'poi_density' not in df.columns:
            df['poi_density'] = np.random.poisson(15, len(df))
        
        if 'infrastructure_score' not in df.columns:
            df['infrastructure_score'] = np.random.uniform(3, 9, len(df))
        
        # Add property features if missing
        if 'bathrooms' not in df.columns:
            df['bathrooms'] = df['bedrooms'].apply(lambda x: max(1, x - 1) if pd.notna(x) else 2)
        
        if 'parking_spaces' not in df.columns:
            df['parking_spaces'] = df['bedrooms'].apply(lambda x: max(1, x // 2) if pd.notna(x) else 1)
        
        if 'balconies' not in df.columns:
            df['balconies'] = np.random.poisson(1, len(df))
        
        if 'floor' not in df.columns:
            df['floor'] = np.random.randint(0, 15, len(df))
        
        if 'total_floors' not in df.columns:
            df['total_floors'] = df['floor'] + np.random.randint(0, 10, len(df))
        
        if 'built_year' not in df.columns:
            df['built_year'] = datetime.now().year - np.random.exponential(10, len(df)).astype(int)
        
        # Add market aggregates
        if 'avg_price_locality' not in df.columns:
            # Group by locality and calculate average
            if 'locality' in df.columns:
                locality_avg = df.groupby('locality')['price'].transform('mean')
                df['avg_price_locality'] = locality_avg
            else:
                df['avg_price_locality'] = df['price'] * np.random.uniform(0.9, 1.1, len(df))
        
        return df
    
    def _generate_synthetic_data(self, n_samples: int = 1000) -> pd.DataFrame:
        """Generate synthetic real estate data for testing"""
        np.random.seed(42)
        
        cities = ['Mumbai', 'Delhi', 'Bangalore', 'Pune', 'Chennai', 'Hyderabad']
        property_types = ['apartment', 'house', 'plot', 'commercial']
        localities = ['Downtown', 'Suburb North', 'Suburb South', 'IT Park Area', 'Old City']
        
        data = {
            'id': [f'PROP_{i:05d}' for i in range(n_samples)],
            'city': np.random.choice(cities, n_samples),
            'locality': np.random.choice(localities, n_samples),
            'property_type': np.random.choice(property_types, n_samples, p=[0.5, 0.3, 0.1, 0.1]),
            'bedrooms': np.random.choice([1, 2, 3, 4, 5], n_samples, p=[0.1, 0.35, 0.35, 0.15, 0.05]),
            'bathrooms': np.random.choice([1, 2, 3, 4], n_samples, p=[0.2, 0.5, 0.25, 0.05]),
            'area_sqft': np.random.uniform(500, 5000, n_samples),
            'floor': np.random.randint(0, 20, n_samples),
            'total_floors': np.random.randint(1, 25, n_samples),
            'built_year': np.random.randint(1990, 2024, n_samples),
            'parking_spaces': np.random.choice([0, 1, 2, 3], n_samples, p=[0.1, 0.4, 0.4, 0.1]),
            'balconies': np.random.choice([0, 1, 2], n_samples, p=[0.2, 0.6, 0.2]),
            
            # Location features
            'latitude': np.random.uniform(12.8, 13.2, n_samples),
            'longitude': np.random.uniform(77.4, 77.8, n_samples),
            
            # Spatial features
            'distance_to_metro': np.random.exponential(3, n_samples),
            'distance_to_hospital': np.random.exponential(2, n_samples),
            'distance_to_school': np.random.exponential(1.5, n_samples),
            'distance_to_mall': np.random.exponential(4, n_samples),
            'poi_density': np.random.poisson(15, n_samples),
            'infrastructure_score': np.random.uniform(3, 9, n_samples),
            
            # Market features
            'days_on_market': np.random.exponential(45, n_samples),
            'price_growth_3m': np.random.normal(2, 5, n_samples),
            'price_growth_6m': np.random.normal(4, 8, n_samples),
            'listings_count': np.random.poisson(30, n_samples),
            'absorption_rate': np.random.uniform(0.3, 0.8, n_samples),
        }
        
        df = pd.DataFrame(data)
        
        # Calculate price based on features
        base_price = 50000  # per sqft
        df['price'] = (
            base_price * df['area_sqft'] * 
            (1 + df['bedrooms'] * 0.1) * 
            (1 - df['distance_to_metro'] * 0.02) * 
            (1 + df['infrastructure_score'] * 0.05) *
            np.random.uniform(0.8, 1.2, n_samples)
        )
        
        # Add rental data
        df['annual_rent'] = df['price'] * np.random.uniform(0.025, 0.045, n_samples)
        df['rental_yield'] = (df['annual_rent'] / df['price']) * 100
        
        # Add average price by locality
        df['avg_price_locality'] = df.groupby('locality')['price'].transform('mean')
        
        return df
    
    def process_property_data(self, property_data: Dict) -> pd.DataFrame:
        """Process single property data for prediction"""
        df = pd.DataFrame([property_data])
        
        # Ensure all required columns exist
        required_columns = [
            'bedrooms', 'bathrooms', 'area_sqft', 'floor', 'total_floors',
            'parking_spaces', 'balconies', 'latitude', 'longitude'
        ]
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = np.nan
        
        # Fill missing values with defaults
        defaults = {
            'bedrooms': 2,
            'bathrooms': 2,
            'area_sqft': 1000,
            'floor': 0,
            'total_floors': 5,
            'parking_spaces': 1,
            'balconies': 1
        }
        
        df = df.fillna(defaults)
        
        return df
    
    def aggregate_market_data(self, city: str, locality: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate market data for a location"""
        # This would typically query a database
        # For now, return simulated aggregates
        return {
            'avg_price_psf': 5500,
            'median_price': 8500000,
            'total_listings': 1250,
            'avg_days_on_market': 45,
            'price_trend_3m': 2.5,
            'price_trend_6m': 5.2,
            'price_trend_1y': 8.7,
            'supply_demand_ratio': 0.7,
            'top_localities': [
                {'name': 'IT Corridor', 'avg_price': 6500},
                {'name': 'Downtown', 'avg_price': 7200},
                {'name': 'Suburbs', 'avg_price': 4800}
            ]
        }
    
    def calculate_property_metrics(self, property_data: Dict) -> Dict[str, Any]:
        """Calculate various property metrics"""
        metrics = {}
        
        # Price per sqft
        if 'price' in property_data and 'area_sqft' in property_data:
            metrics['price_per_sqft'] = property_data['price'] / max(property_data['area_sqft'], 1)
        
        # Carpet area (assuming 70% of built-up)
        if 'area_sqft' in property_data:
            metrics['carpet_area'] = property_data['area_sqft'] * 0.7
        
        # Property age
        if 'built_year' in property_data:
            metrics['age_years'] = datetime.now().year - property_data['built_year']
        
        # Size category
        area = property_data.get('area_sqft', 1000)
        if area < 750:
            metrics['size_category'] = 'Compact'
        elif area < 1500:
            metrics['size_category'] = 'Mid-size'
        elif area < 2500:
            metrics['size_category'] = 'Large'
        else:
            metrics['size_category'] = 'Luxury'
        
        return metrics
    
    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and clean dataframe"""
        # Remove duplicates
        df = df.drop_duplicates()
        
        # Remove rows with critical missing values
        critical_columns = ['price', 'area_sqft']
        for col in critical_columns:
            if col in df.columns:
                df = df[df[col].notna()]
        
        # Remove outliers
        if 'price' in df.columns:
            q1 = df['price'].quantile(0.01)
            q99 = df['price'].quantile(0.99)
            df = df[(df['price'] >= q1) & (df['price'] <= q99)]
        
        if 'area_sqft' in df.columns:
            df = df[(df['area_sqft'] > 100) & (df['area_sqft'] < 50000)]
        
        # Validate coordinates
        if 'latitude' in df.columns and 'longitude' in df.columns:
            # India's approximate bounds
            df = df[
                (df['latitude'].between(8, 35)) & 
                (df['longitude'].between(68, 97))
            ]
        
        return df
    
    def export_predictions(self, predictions: Dict, format: str = 'json') -> str:
        """Export predictions in various formats"""
        output_file = self.data_dir / f"predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        if format == 'json':
            with open(output_file, 'w') as f:
                json.dump(predictions, f, indent=2, default=str)
        elif format == 'csv':
            df = pd.DataFrame([predictions])
            df.to_csv(output_file, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return str(output_file)

    def query_properties(
        self,
        city: Optional[str] = None,
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_area: Optional[float] = None,
        max_area: Optional[float] = None,
        bedrooms: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query processed properties with filters and pagination."""
        try:
            datasets = self.get_cached_datasets()
            if not datasets:
                return []

            # Concatenate all city datasets
            frames = []
            for key, df in datasets.items():
                if city is None or city.lower() in key.lower() or ("city" in df.columns and (df["city"].astype(str).str.lower() == city.lower()).any()):
                    frames.append(df)

            if not frames:
                return []

            df_all = pd.concat(frames, ignore_index=True)

            # Apply filters
            if property_type and 'property_type' in df_all.columns:
                df_all = df_all[df_all['property_type'].astype(str).str.contains(property_type, case=False, na=False)]
            if min_price is not None and 'price' in df_all.columns:
                df_all = df_all[df_all['price'] >= min_price]
            if max_price is not None and 'price' in df_all.columns:
                df_all = df_all[df_all['price'] <= max_price]
            if min_area is not None and 'area_sqft' in df_all.columns:
                df_all = df_all[df_all['area_sqft'] >= min_area]
            if max_area is not None and 'area_sqft' in df_all.columns:
                df_all = df_all[df_all['area_sqft'] <= max_area]
            if bedrooms is not None and 'bedrooms' in df_all.columns:
                df_all = df_all[df_all['bedrooms'] == bedrooms]

            # Pagination
            df_page = df_all.iloc[offset:offset + limit].copy()

            # Post-process
            if 'price' in df_page.columns and 'area_sqft' in df_page.columns:
                with np.errstate(divide='ignore', invalid='ignore'):
                    df_page['price_per_sqft'] = (df_page['price'] / df_page['area_sqft']).replace([np.inf, -np.inf], 0).fillna(0)

            # Ensure primitives only
            records = df_page.fillna(0).to_dict('records')
            return records
        except Exception as e:
            logger.error(f"Error querying properties: {e}")
            return []
