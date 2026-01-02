"""
Unified Real Estate Data Processor for DMPE
Handles comprehensive processing of real estate data across cities and property types
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import logging
from datetime import datetime, timedelta
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class PropertyType(Enum):
    """Standardized property types."""
    RESIDENTIAL_APARTMENT = "residential_apartment"
    RESIDENTIAL_HOUSE = "residential_house"
    RESIDENTIAL_PLOT = "residential_plot"
    COMMERCIAL_OFFICE = "commercial_office"
    COMMERCIAL_SHOP = "commercial_shop"
    COMMERCIAL_LAND = "commercial_land"
    COMMERCIAL_WAREHOUSE = "commercial_warehouse"
    COMMERCIAL_INDUSTRIAL = "commercial_industrial"
    AGRICULTURAL_LAND = "agricultural_land"
    FARMHOUSE = "farmhouse"

class ListingType(Enum):
    """Listing types."""
    SALE = "sale"
    RENT = "rent"

@dataclass
class PropertyConfig:
    """Configuration for property processing."""
    city: str
    property_type: PropertyType
    listing_type: ListingType
    currency: str = "INR"
    price_unit: str = "sq_ft"

class UnifiedRealEstateProcessor:
    """Unified processor for real estate data across cities and types."""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent.parent.parent / "data" / "raw"
        self.processed_data = {}
        self.city_configs = {}
        
    def detect_city_from_filename(self, filename: str) -> str:
        """Extract city name from filename."""
        # Remove file extension and common prefixes
        name = Path(filename).stem.lower()
        
        # Remove common prefixes
        prefixes = ["bangalore-", "mumbai-", "delhi-", "pune-", "hyderabad-"]
        for prefix in prefixes:
            if name.startswith(prefix):
                return prefix.replace("-", "").title()
        
        # Try to extract city from pattern
        parts = name.split("-")
        if len(parts) >= 2:
            return parts[0].title()
        
        return "Unknown"
    
    def detect_property_type(self, filename: str) -> Tuple[PropertyType, ListingType]:
        """Detect property type and listing type from filename."""
        name = Path(filename).stem.lower()
        
        # Check for rent
        listing_type = ListingType.RENT if "rent" in name else ListingType.SALE
        
        # Map patterns to property types
        type_patterns = {
            "residential-apartment": PropertyType.RESIDENTIAL_APARTMENT,
            "residential-house": PropertyType.RESIDENTIAL_HOUSE,
            "residential-house-rent": PropertyType.RESIDENTIAL_HOUSE,
            "residential-plot": PropertyType.RESIDENTIAL_PLOT,
            "commercial-office": PropertyType.COMMERCIAL_OFFICE,
            "commercial-shop": PropertyType.COMMERCIAL_SHOP,
            "commercial-shop-rent": PropertyType.COMMERCIAL_SHOP,
            "commercial-land": PropertyType.COMMERCIAL_LAND,
            "commercial-warehouse": PropertyType.COMMERCIAL_WAREHOUSE,
            "commercial-industrial": PropertyType.COMMERCIAL_INDUSTRIAL,
            "commercial-industrialbuilding": PropertyType.COMMERCIAL_INDUSTRIAL,
            "commercial-industrialshed": PropertyType.COMMERCIAL_INDUSTRIAL,
            "agricultural-land": PropertyType.AGRICULTURAL_LAND,
            "farmhouse": PropertyType.FARMHOUSE
        }
        
        for pattern, prop_type in type_patterns.items():
            if pattern in name:
                return prop_type, listing_type
        
        # Default fallback
        return PropertyType.RESIDENTIAL_APARTMENT, listing_type
    
    def load_datasets(self) -> Dict[str, pd.DataFrame]:
        """Load all real estate datasets with metadata."""
        datasets = {}
        
        # Get all JSON files
        json_files = list(self.data_dir.glob("*-*.json"))
        
        for file_path in json_files:
            try:
                # Extract metadata
                city = self.detect_city_from_filename(file_path.name)
                property_type, listing_type = self.detect_property_type(file_path.name)
                
                # Create unique key
                key = f"{city}_{property_type.value}_{listing_type.value}"
                
                # Load JSON data
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Convert to DataFrame with metadata
                df = pd.DataFrame(data)
                df['city'] = city
                df['property_type'] = property_type.value
                df['listing_type'] = listing_type.value
                
                datasets[key] = df
                
                # Store configuration
                self.city_configs[key] = PropertyConfig(
                    city=city,
                    property_type=property_type,
                    listing_type=listing_type
                )
                
                logger.info(f"Loaded {len(df)} records for {key}")
                
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
        
        return datasets
    
    def standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names across datasets."""
        df = df.copy()
        
        # Column mapping for standardization
        column_mapping = {
            'price': 'price',
            'price_per_sq_ft': 'price_per_sq_ft',
            'covered_area': 'area_sqft',
            'carpet_area': 'carpet_area_sqft',
            'bedrooms': 'bedrooms',
            'bathrooms': 'bathrooms',
            'balconies': 'balconies',
            'location': 'coordinates',
            'address': 'address',
            'posted_date': 'listing_date',
            'description': 'description',
            'amenities': 'amenities',
            'landmark_details': 'nearby_landmarks'
        }
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        return df
    
    def clean_price_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize price data."""
        df = df.copy()
        
        # Convert price to numeric
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['price_per_sq_ft'] = pd.to_numeric(df['price_per_sq_ft'], errors='coerce')
        
        # Calculate price per sqft if missing
        if 'area_sqft' in df.columns:
            # Ensure area is numeric before calculations
            df['area_sqft'] = pd.to_numeric(df['area_sqft'], errors='coerce')
            mask = (
                df['price_per_sq_ft'].isna()
                & df['price'].notna()
                & df['area_sqft'].notna()
                & (df['area_sqft'] > 0)
            )
            df.loc[mask, 'price_per_sq_ft'] = df.loc[mask, 'price'] / df.loc[mask, 'area_sqft']
        
        # Filter out unrealistic prices (adjustable by city/property type)
        price_limits = {
            'residential': {'min': 10000, 'max': 500000000},  # 10K to 50Cr
            'commercial': {'min': 50000, 'max': 1000000000},  # 50K to 100Cr
            'land': {'min': 100000, 'max': 2000000000}  # 1L to 200Cr
        }
        
        # Apply filters based on property type
        for idx, row in df.iterrows():
            if 'residential' in row['property_type']:
                limits = price_limits['residential']
            elif 'commercial' in row['property_type']:
                limits = price_limits['commercial']
            elif 'land' in row['property_type']:
                limits = price_limits['land']
            else:
                limits = price_limits['residential']  # default
            
            if row['price'] < limits['min'] or row['price'] > limits['max']:
                df.loc[idx, 'price'] = np.nan
        
        # Create standardized price columns
        df['price_lakhs'] = df['price'] / 100000
        df['price_cr'] = df['price'] / 10000000
        
        return df
    
    def extract_location_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract and standardize location features."""
        df = df.copy()
        
        # Parse coordinates
        if 'coordinates' in df.columns:
            coords = df['coordinates'].str.split(',', expand=True)
            df['latitude'] = pd.to_numeric(coords[0], errors='coerce')
            df['longitude'] = pd.to_numeric(coords[1], errors='coerce')
        
        # Extract area/locality from address
        if 'address' in df.columns:
            # Extract area name (second part of address)
            df['locality'] = df['address'].str.extract(r'([^,]+),([^,]+),')[1].str.strip()
            df['area_name'] = df['address'].str.extract(r'([^,]+),')[0].str.strip()
        
        # Count nearby landmarks
        if 'nearby_landmarks' in df.columns:
            df['landmark_count'] = df['nearby_landmarks'].apply(
                lambda x: len(x) if isinstance(x, list) else 0
            )
        
        return df
    
    def extract_property_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract property-specific features."""
        df = df.copy()
        
        # Convert numeric features
        numeric_columns = ['bedrooms', 'bathrooms', 'balconies', 'area_sqft', 'carpet_area_sqft']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calculate age from listing date
        if 'listing_date' in df.columns:
            # Parse as timezone-aware (UTC) and compute with a tz-aware 'now' to avoid naive/tz-aware errors
            df['listing_date'] = pd.to_datetime(df['listing_date'], errors='coerce', utc=True)
            df['days_since_listed'] = (pd.Timestamp.now(tz='UTC') - df['listing_date']).dt.days
        
        # Extract amenities count
        if 'amenities' in df.columns:
            df['amenities_count'] = df['amenities'].apply(
                lambda x: len(x) if isinstance(x, list) else 0
            )
        
        # Calculate efficiency metrics
        if 'area_sqft' in df.columns and 'bedrooms' in df.columns:
            df['area_per_bedroom'] = df['area_sqft'] / df['bedrooms'].replace(0, np.nan)
        
        if 'carpet_area_sqft' in df.columns and 'area_sqft' in df.columns:
            df['carpet_efficiency'] = df['carpet_area_sqft'] / df['area_sqft']
        
        return df
    
    def calculate_investment_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate investment and market metrics."""
        df = df.copy()
        
        # Price per bedroom
        if 'price' in df.columns and 'bedrooms' in df.columns:
            df['price_per_bedroom'] = df['price'] / df['bedrooms'].replace(0, np.nan)
        
        # Location score based on landmarks and connectivity
        if 'landmark_count' in df.columns:
            df['location_score'] = np.clip(df['landmark_count'] / 10, 0, 1)
        
        # Investment potential score
        features = []
        weights = []
        
        if 'location_score' in df.columns:
            features.append(df['location_score'])
            weights.append(0.4)
        
        if 'amenities_count' in df.columns:
            features.append((df['amenities_count'] / 20).clip(0, 1))
            weights.append(0.3)
        
        if 'price_per_sq_ft' in df.columns:
            # Value for money (lower than median is better)
            median_ppsqft = df['price_per_sq_ft'].median()
            value_score = (median_ppsqft / df['price_per_sq_ft']).clip(0, 2)
            features.append(value_score)
            weights.append(0.3)
        
        if features:
            df['investment_score'] = sum(f * w for f, w in zip(features, weights))
        else:
            df['investment_score'] = 0.5  # default neutral score
        
        # Market demand indicator (based on days listed)
        if 'days_since_listed' in df.columns:
            df['demand_indicator'] = np.where(
                df['days_since_listed'] < 30, 'High',
                np.where(df['days_since_listed'] < 90, 'Medium', 'Low')
            )
        
        return df
    
    def process_dataset(self, dataset_key: str, df: pd.DataFrame) -> pd.DataFrame:
        """Process a specific dataset with full pipeline."""
        logger.info(f"Processing {dataset_key} with {len(df)} records")
        
        # Apply processing pipeline
        df = self.standardize_columns(df)
        df = self.clean_price_data(df)
        df = self.extract_location_features(df)
        df = self.extract_property_features(df)
        df = self.calculate_investment_metrics(df)
        
        # Remove records with critical missing data
        required_columns = ['price', 'latitude', 'longitude']
        available_columns = [col for col in required_columns if col in df.columns]
        
        if available_columns:
            df = df.dropna(subset=available_columns)
        
        logger.info(f"Processed {len(df)} clean records for {dataset_key}")
        
        return df
    
    def process_all_data(self) -> Dict[str, pd.DataFrame]:
        """Process all real estate datasets."""
        datasets = self.load_datasets()
        processed_datasets = {}
        
        for key, df in datasets.items():
            try:
                processed_datasets[key] = self.process_dataset(key, df)
            except Exception as e:
                logger.error(f"Error processing {key}: {e}")
        
        return processed_datasets
    
    def save_processed_data(self, datasets: Dict[str, pd.DataFrame], output_dir: str = None):
        """Save processed datasets to files."""
        output_path = Path(output_dir) if output_dir else self.data_dir.parent / "processed"
        output_path.mkdir(exist_ok=True)
        
        for key, df in datasets.items():
            # Create safe filename
            safe_key = key.replace('/', '_').replace('\\', '_')
            output_file = output_path / f"processed_{safe_key}.csv"
            df.to_csv(output_file, index=False)
            logger.info(f"Saved processed data to {output_file}")
    
    def get_market_summary(self, datasets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Generate comprehensive market summary."""
        summary = {
            'total_properties': sum(len(df) for df in datasets.values()),
            'cities': list(set(df['city'].iloc[0] for df in datasets.values() if len(df) > 0)),
            'property_types': list(set(df['property_type'].iloc[0] for df in datasets.values() if len(df) > 0)),
            'listing_types': list(set(df['listing_type'].iloc[0] for df in datasets.values() if len(df) > 0)),
            'price_analysis': {},
            'location_analysis': {},
            'investment_insights': {}
        }
        
        # Analyze each dataset
        for key, df in datasets.items():
            if len(df) == 0:
                continue
                
            city = df['city'].iloc[0]
            prop_type = df['property_type'].iloc[0]
            
            if city not in summary['price_analysis']:
                summary['price_analysis'][city] = {}
            
            summary['price_analysis'][city][prop_type] = {
                'avg_price': float(df['price'].mean()),
                'median_price': float(df['price'].median()),
                'price_range': [float(df['price'].min()), float(df['price'].max())],
                'avg_price_per_sqft': float(df['price_per_sq_ft'].mean()) if 'price_per_sq_ft' in df.columns else None,
                'count': len(df)
            }
            
            # Investment insights
            if 'investment_score' in df.columns:
                if city not in summary['investment_insights']:
                    summary['investment_insights'][city] = {}
                
                summary['investment_insights'][city][prop_type] = {
                    'avg_investment_score': float(df['investment_score'].mean()),
                    'high_investment_properties': int((df['investment_score'] > 0.7).sum()),
                    'top_localities': df.groupby('locality')['investment_score'].mean().nlargest(5).to_dict() if 'locality' in df.columns else {}
                }
        
        return summary

if __name__ == "__main__":
    # Example usage
    processor = UnifiedRealEstateProcessor()
    datasets = processor.process_all_data()
    processor.save_processed_data(datasets)
    summary = processor.get_market_summary(datasets)
    
    print("Unified Real Estate Processing Complete!")
    print(f"Total properties processed: {summary['total_properties']}")
    print(f"Cities covered: {summary['cities']}")
    print(f"Property types: {summary['property_types']}")
