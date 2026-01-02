"""
ETL Service for Airflow Integration
Handles data ingestion from Airflow pipeline to DMPE system
"""

import os
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

from backend.services.data_processor import DataProcessor
from backend.utils.logger import LoggerMixin

logger = logging.getLogger(__name__)


class ETLService(LoggerMixin):
    """
    ETL Service that bridges Airflow data pipelines with DMPE
    Handles data ingestion, transformation, and preparation for model training
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.staging_dir = self.data_dir / "staging"
        
        self.raw_dir.mkdir(exist_ok=True)
        self.processed_dir.mkdir(exist_ok=True)
        self.staging_dir.mkdir(exist_ok=True)
        
        self.data_processor = DataProcessor(str(self.data_dir))
        
        self.log_info("ETL Service initialized")
    
    def ingest_scraped_data(self, source_file: str) -> Dict[str, Any]:
        """
        Ingest data from Airflow scraping pipeline
        
        Args:
            source_file: Path to CSV file with scraped data
            
        Returns:
            Dictionary with ingestion results
        """
        self.log_info(f"Ingesting scraped data from: {source_file}")
        
        try:
            # Load scraped data
            df = pd.read_csv(source_file)
            initial_count = len(df)
            
            self.log_info(f"Loaded {initial_count} records from source")
            
            # Add ingestion metadata
            df['ingested_at'] = datetime.now()
            df['source_file'] = source_file
            df['etl_version'] = '1.0'
            
            # Save to raw directory
            raw_file = self.raw_dir / f"raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(raw_file, index=False)
            
            self.log_info(f"Saved raw data to: {raw_file}")
            
            return {
                'status': 'success',
                'records_ingested': initial_count,
                'raw_file': str(raw_file),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_error(f"Failed to ingest data: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def transform_for_dmpe(self, raw_file: str) -> Dict[str, Any]:
        """
        Transform raw scraped data to DMPE-compatible format
        
        Args:
            raw_file: Path to raw CSV file
            
        Returns:
            Dictionary with transformation results
        """
        self.log_info(f"Transforming data from: {raw_file}")
        
        try:
            df = pd.read_csv(raw_file)
            initial_count = len(df)
            
            # Standardize column names
            column_mapping = {
                'title': 'property_name',
                'area_sqft': 'area_sqft',
                'price': 'price',
                'bedrooms': 'bedrooms',
                'locality': 'locality',
                'city': 'city',
                'property_type': 'property_type',
                'url': 'listing_url'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Add missing DMPE required fields
            if 'bathrooms' not in df.columns:
                df['bathrooms'] = df['bedrooms'].apply(lambda x: max(1, x - 1) if pd.notna(x) else 2)
            
            if 'parking_spaces' not in df.columns:
                df['parking_spaces'] = df['bedrooms'].apply(lambda x: max(1, x // 2) if pd.notna(x) else 1)
            
            if 'balconies' not in df.columns:
                df['balconies'] = 1
            
            if 'floor' not in df.columns:
                df['floor'] = 0
            
            if 'total_floors' not in df.columns:
                df['total_floors'] = 10
            
            if 'built_year' not in df.columns:
                df['built_year'] = datetime.now().year - 5
            
            # Add synthetic spatial features if coordinates missing
            df = self._add_spatial_features(df)
            
            # Add market features
            df = self._add_market_features(df)
            
            # Validate and clean
            df = self.data_processor.validate_data(df)
            
            final_count = len(df)
            
            # Save transformed data
            transformed_file = self.processed_dir / f"transformed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(transformed_file, index=False)
            
            self.log_info(f"Transformed {final_count}/{initial_count} records")
            self.log_info(f"Saved to: {transformed_file}")
            
            return {
                'status': 'success',
                'initial_records': initial_count,
                'transformed_records': final_count,
                'transformation_rate': f"{(final_count/initial_count)*100:.2f}%",
                'output_file': str(transformed_file),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_error(f"Transformation failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def merge_with_training_data(self, new_data_file: str) -> Dict[str, Any]:
        """
        Merge new data with existing training dataset
        
        Args:
            new_data_file: Path to transformed data file
            
        Returns:
            Dictionary with merge results
        """
        self.log_info("Merging with existing training data")
        
        try:
            # Load new data
            new_df = pd.read_csv(new_data_file)
            new_count = len(new_df)
            
            # Load existing training data
            training_file = self.data_dir / "processed" / "processed_training_data.csv"
            
            if training_file.exists():
                existing_df = pd.read_csv(training_file)
                existing_count = len(existing_df)
                
                self.log_info(f"Existing training data: {existing_count} records")
                
                # Combine datasets
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                
                # Remove duplicates based on URL if available
                if 'listing_url' in combined_df.columns:
                    combined_df = combined_df.drop_duplicates(subset=['listing_url'], keep='last')
                
                # Keep only recent data (e.g., last 2 years)
                if 'scraped_at' in combined_df.columns:
                    cutoff_date = datetime.now() - timedelta(days=730)
                    combined_df['scraped_at'] = pd.to_datetime(combined_df['scraped_at'])
                    combined_df = combined_df[combined_df['scraped_at'] > cutoff_date]
                
                final_count = len(combined_df)
                
            else:
                self.log_info("No existing training data found, creating new dataset")
                combined_df = new_df
                existing_count = 0
                final_count = new_count
            
            # Save updated training data
            combined_df.to_csv(training_file, index=False)
            
            self.log_info(f"Training data updated: {final_count} total records")
            
            return {
                'status': 'success',
                'existing_records': existing_count,
                'new_records': new_count,
                'final_records': final_count,
                'net_addition': final_count - existing_count,
                'training_file': str(training_file),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_error(f"Merge failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def run_full_etl_pipeline(self, source_file: str) -> Dict[str, Any]:
        """
        Run complete ETL pipeline: Ingest → Transform → Merge
        
        Args:
            source_file: Path to source data file from Airflow
            
        Returns:
            Dictionary with pipeline results
        """
        self.log_info("=" * 60)
        self.log_info("Starting full ETL pipeline")
        self.log_info("=" * 60)
        
        results = {
            'pipeline_started': datetime.now().isoformat(),
            'source_file': source_file,
            'stages': {}
        }
        
        try:
            # Stage 1: Ingest
            self.log_info("\n--- Stage 1: Data Ingestion ---")
            ingest_result = self.ingest_scraped_data(source_file)
            results['stages']['ingestion'] = ingest_result
            
            if ingest_result['status'] != 'success':
                results['pipeline_status'] = 'failed'
                return results
            
            # Stage 2: Transform
            self.log_info("\n--- Stage 2: Data Transformation ---")
            transform_result = self.transform_for_dmpe(ingest_result['raw_file'])
            results['stages']['transformation'] = transform_result
            
            if transform_result['status'] != 'success':
                results['pipeline_status'] = 'failed'
                return results
            
            # Stage 3: Merge
            self.log_info("\n--- Stage 3: Merge with Training Data ---")
            merge_result = self.merge_with_training_data(transform_result['output_file'])
            results['stages']['merge'] = merge_result
            
            if merge_result['status'] != 'success':
                results['pipeline_status'] = 'failed'
                return results
            
            # Pipeline success
            results['pipeline_status'] = 'success'
            results['pipeline_completed'] = datetime.now().isoformat()
            results['summary'] = {
                'total_records_added': merge_result.get('net_addition', 0),
                'final_training_records': merge_result.get('final_records', 0),
                'training_file': merge_result.get('training_file')
            }
            
            self.log_info("\n" + "=" * 60)
            self.log_info("ETL Pipeline completed successfully")
            self.log_info(f"Added {results['summary']['total_records_added']} new records")
            self.log_info("=" * 60)
            
            return results
            
        except Exception as e:
            self.log_error(f"ETL Pipeline failed: {e}", exc_info=True)
            results['pipeline_status'] = 'error'
            results['error'] = str(e)
            return results
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get statistics about ETL pipeline runs"""
        try:
            stats = {
                'raw_files': len(list(self.raw_dir.glob('*.csv'))),
                'processed_files': len(list(self.processed_dir.glob('*.csv'))),
                'staging_files': len(list(self.staging_dir.glob('*.csv')))
            }
            
            # Get training data info
            training_file = self.data_dir / "processed" / "processed_training_data.csv"
            if training_file.exists():
                df = pd.read_csv(training_file)
                stats['training_records'] = len(df)
                stats['training_file_size'] = training_file.stat().st_size / (1024 * 1024)  # MB
                stats['training_last_updated'] = datetime.fromtimestamp(
                    training_file.stat().st_mtime
                ).isoformat()
            else:
                stats['training_records'] = 0
            
            return stats
            
        except Exception as e:
            self.log_error(f"Failed to get stats: {e}")
            return {}
    
    def _add_spatial_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add spatial features for properties without coordinates"""
        
        # If no coordinates, add synthetic ones based on city
        if 'latitude' not in df.columns or 'longitude' not in df.columns:
            city_coords = {
                'Bangalore': (12.9716, 77.5946),
                'Mumbai': (19.0760, 72.8777),
                'Delhi': (28.7041, 77.1025),
                'Pune': (18.5204, 73.8567),
                'Hyderabad': (17.3850, 78.4867),
                'Chennai': (13.0827, 80.2707)
            }
            
            df['latitude'] = df['city'].map(lambda x: city_coords.get(x, (12.9716, 77.5946))[0])
            df['longitude'] = df['city'].map(lambda x: city_coords.get(x, (12.9716, 77.5946))[1])
        
        # Add synthetic spatial features
        if 'distance_to_metro' not in df.columns:
            df['distance_to_metro'] = pd.np.random.exponential(3, len(df))
        
        if 'distance_to_hospital' not in df.columns:
            df['distance_to_hospital'] = pd.np.random.exponential(2, len(df))
        
        if 'poi_density' not in df.columns:
            df['poi_density'] = pd.np.random.poisson(15, len(df))
        
        if 'infrastructure_score' not in df.columns:
            df['infrastructure_score'] = pd.np.random.uniform(3, 9, len(df))
        
        return df
    
    def _add_market_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add market-related features"""
        
        if 'days_on_market' not in df.columns:
            df['days_on_market'] = pd.np.random.exponential(45, len(df))
        
        if 'price_growth_3m' not in df.columns:
            df['price_growth_3m'] = pd.np.random.normal(2, 5, len(df))
        
        if 'listings_count' not in df.columns:
            df['listings_count'] = pd.np.random.poisson(30, len(df))
        
        if 'absorption_rate' not in df.columns:
            df['absorption_rate'] = pd.np.random.uniform(0.3, 0.8, len(df))
        
        # Calculate rental yield estimate
        if 'annual_rent' not in df.columns and 'price' in df.columns:
            df['annual_rent'] = df['price'] * pd.np.random.uniform(0.03, 0.04, len(df))
            df['rental_yield'] = (df['annual_rent'] / df['price']) * 100
        
        return df
