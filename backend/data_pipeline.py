"""
Comprehensive Data Processing Pipeline for Valora AI
Processes raw property data and enriches it with all required fields
"""

import pandas as pd
import numpy as np
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib
from pathlib import Path
import requests
from sentence_transformers import SentenceTransformer
from geopy.distance import geodesic
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValoraDataPipeline:
    """Complete data processing pipeline for Valora AI"""
    
    def __init__(self):
        self.raw_data_path = Path("data/raw")
        self.processed_data_path = Path("data/processed")
        self.models_path = Path("data/models")
        
        # Ensure directories exist
        self.processed_data_path.mkdir(parents=True, exist_ok=True)
        self.models_path.mkdir(parents=True, exist_ok=True)
        
        # Load embedding model (lightweight)
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model loaded successfully")
        except:
            logger.warning("Could not load embedding model - will use API fallback")
            self.embedding_model = None
    
    def load_all_raw_data(self) -> pd.DataFrame:
        """Load and combine all raw property data files"""
        all_properties = []
        
        # List of property types to load
        property_files = [
            'bangalore-residential-apartment.csv',
            'bangalore-residential-apartment-rent.csv',
            'bangalore-residential-house.csv',
            'bangalore-residential-house-rent.csv',
            'bangalore-residential-plot.csv',
            'bangalore-commercial-officespace.csv',
            'bangalore-commercial-shop-rent.csv',
            'bangalore-commercial-warehouse.csv',
            'bangalore-farmhouse.csv'
        ]
        
        for file_name in property_files:
            file_path = self.raw_data_path / file_name
            if file_path.exists():
                try:
                    df = pd.read_csv(file_path)
                    # Extract property type from filename
                    property_type = file_name.replace('bangalore-', '').replace('.csv', '')
                    df['property_category'] = property_type
                    all_properties.append(df)
                    logger.info(f"Loaded {len(df)} properties from {file_name}")
                except Exception as e:
                    logger.error(f"Error loading {file_name}: {e}")
        
        if all_properties:
            combined_df = pd.concat(all_properties, ignore_index=True)
            logger.info(f"Total properties loaded: {len(combined_df)}")
            return combined_df
        else:
            logger.error("No property data found")
            return pd.DataFrame()
    
    def process_properties(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and enrich property data"""
        
        # 1. Clean and standardize fields
        df['property_id'] = df['id'].astype(str)
        df['city'] = 'Bangalore'
        
        # 2. Extract locality from name/address
        df['locality'] = df.apply(self._extract_locality, axis=1)
        
        # 3. Parse property type
        df['property_type'] = df['property_category'].apply(self._parse_property_type)
        
        # 4. Determine listing type (sale/rent)
        df['listing_type'] = df['property_category'].apply(
            lambda x: 'rent' if 'rent' in x.lower() else 'sale'
        )
        
        # 5. Clean numeric fields
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['area_sqft'] = pd.to_numeric(df['covered_area'], errors='coerce')
        df['bedrooms'] = pd.to_numeric(df['bedrooms'], errors='coerce')
        df['bathrooms'] = pd.to_numeric(df['bathrooms'], errors='coerce')
        
        # 6. Parse location (lat, lng)
        if 'location' in df.columns:
            location_data = df['location'].apply(self._parse_location)
            df['latitude'] = location_data.apply(lambda x: x[0] if x else None)
            df['longitude'] = location_data.apply(lambda x: x[1] if x else None)
        
        # 7. Parse dates
        df['listing_date'] = pd.to_datetime(df['posted_date'], errors='coerce')
        df['updated_date'] = datetime.now()
        
        # 8. Parse amenities
        df['amenities'] = df['amenities'].apply(self._parse_amenities)
        
        # 9. Calculate price per sqft
        df['price_per_sqft'] = df.apply(
            lambda row: row['price'] / row['area_sqft'] 
            if pd.notna(row['price']) and pd.notna(row['area_sqft']) and row['area_sqft'] > 0 
            else None, axis=1
        )
        
        # 10. Add missing fields with defaults
        df['floor'] = pd.to_numeric(df.get('floors', 0), errors='coerce')
        df['total_floors'] = pd.to_numeric(df.get('floors', 0), errors='coerce')
        df['age_years'] = pd.to_numeric(df.get('operating_since', 0), errors='coerce')
        df['parking_spaces'] = pd.to_numeric(df.get('balconies', 0), errors='coerce')
        
        # 11. Generate description if missing
        df['description'] = df.apply(
            lambda row: row.get('description', '') or self._generate_description(row), axis=1
        )
        
        return df
    
    def _extract_locality(self, row) -> str:
        """Extract locality from various fields"""
        # Priority: explicit locality > name parsing > address parsing
        
        # Common Bangalore localities
        localities = [
            'Whitefield', 'Koramangala', 'HSR Layout', 'Marathahalli',
            'Electronic City', 'Indiranagar', 'Hebbal', 'BTM Layout',
            'JP Nagar', 'Sarjapur', 'Yeshwanthpur', 'Yelahanka',
            'Bannerghatta', 'Jayanagar', 'Malleshwaram', 'Bellandur',
            'Richmond Town', 'CV Raman Nagar', 'Rajaji Nagar',
            'Kanakapura Road', 'Tumkur Road', 'Bagalur', 'Thanisandra',
            'MSR Nagar', 'Rajarajeshwari Nagar', 'Soukya Road',
            'Carmelaram', 'Panathur', 'Chambenahalli'
        ]
        
        # Check in name field
        name = str(row.get('name', '')).lower()
        for locality in localities:
            if locality.lower() in name:
                return locality
        
        # Check in address field
        address = str(row.get('address', '')).lower()
        for locality in localities:
            if locality.lower() in address:
                return locality
        
        # Check in url field
        url = str(row.get('url', '')).lower()
        for locality in localities:
            if locality.lower().replace(' ', '-') in url:
                return locality
        
        return 'Unknown'
    
    def _parse_property_type(self, category: str) -> str:
        """Standardize property type"""
        category = str(category).lower()
        
        if 'apartment' in category:
            return 'residential_apartment'
        elif 'house' in category:
            return 'residential_house'
        elif 'villa' in category:
            return 'residential_villa'
        elif 'plot' in category:
            return 'residential_plot'
        elif 'office' in category:
            return 'commercial_office'
        elif 'shop' in category:
            return 'commercial_shop'
        elif 'warehouse' in category:
            return 'commercial_warehouse'
        elif 'farmhouse' in category:
            return 'farmhouse'
        else:
            return 'other'
    
    def _parse_location(self, location_str: str) -> Optional[tuple]:
        """Parse location string to (lat, lng)"""
        if pd.isna(location_str):
            return None
        
        try:
            # Format: "12.9716,77.5946"
            parts = str(location_str).split(',')
            if len(parts) == 2:
                lat = float(parts[0].strip())
                lng = float(parts[1].strip())
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return (lat, lng)
        except:
            pass
        
        return None
    
    def _parse_amenities(self, amenities_str: str) -> List[str]:
        """Parse amenities string to list"""
        if pd.isna(amenities_str):
            return []
        
        # Split by comma and clean
        amenities = str(amenities_str).split(',')
        cleaned = []
        
        for amenity in amenities:
            clean = amenity.strip().lower()
            # Standardize common amenities
            if 'gym' in clean or 'fitness' in clean:
                cleaned.append('gym')
            if 'pool' in clean or 'swimming' in clean:
                cleaned.append('pool')
            if 'security' in clean or 'guard' in clean:
                cleaned.append('security')
            if 'park' in clean:
                cleaned.append('parking')
            if 'lift' in clean or 'elevator' in clean:
                cleaned.append('elevator')
            if 'garden' in clean:
                cleaned.append('garden')
            if 'club' in clean:
                cleaned.append('clubhouse')
        
        return list(set(cleaned))  # Remove duplicates
    
    def _generate_description(self, row) -> str:
        """Generate property description if missing"""
        parts = []
        
        # Basic info
        if pd.notna(row.get('bedrooms')):
            parts.append(f"{int(row['bedrooms'])} BHK")
        
        parts.append(row.get('property_type', 'property').replace('_', ' '))
        
        if pd.notna(row.get('area_sqft')):
            parts.append(f"with {int(row['area_sqft'])} sqft area")
        
        # Location
        locality = row.get('locality')
        if locality and locality != 'Unknown':
            parts.append(f"in {locality}, Bangalore")
        
        # Price
        if pd.notna(row.get('price')):
            price_cr = row['price'] / 10000000
            if price_cr >= 1:
                parts.append(f"priced at ₹{price_cr:.2f} Cr")
            else:
                price_lakh = row['price'] / 100000
                parts.append(f"priced at ₹{price_lakh:.1f} Lakhs")
        
        # Amenities
        amenities = row.get('amenities', [])
        if amenities:
            parts.append(f"with amenities like {', '.join(amenities[:3])}")
        
        return ". ".join(parts) + "."
    
    def generate_embeddings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate embeddings for property descriptions"""
        logger.info("Generating embeddings for properties...")
        
        if self.embedding_model:
            # Use local model
            descriptions = df['description'].fillna('').tolist()
            embeddings = self.embedding_model.encode(descriptions, show_progress_bar=True)
            df['description_embedding'] = embeddings.tolist()
        else:
            # Use HuggingFace API as fallback
            logger.warning("Using API fallback for embeddings - not implemented")
            df['description_embedding'] = None
        
        return df
    
    def compute_locality_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute aggregate metrics per locality"""
        logger.info("Computing locality metrics...")
        
        metrics = []
        
        for locality in df['locality'].unique():
            if locality == 'Unknown':
                continue
            
            locality_df = df[df['locality'] == locality]
            
            for property_type in locality_df['property_type'].unique():
                type_df = locality_df[locality_df['property_type'] == property_type]
                
                for listing_type in ['sale', 'rent']:
                    listing_df = type_df[type_df['listing_type'] == listing_type]
                    
                    if len(listing_df) > 0:
                        metric = {
                            'locality': locality,
                            'property_type': property_type,
                            'listing_type': listing_type,
                            'avg_price': listing_df['price'].mean(),
                            'median_price': listing_df['price'].median(),
                            'min_price': listing_df['price'].min(),
                            'max_price': listing_df['price'].max(),
                            'avg_price_per_sqft': listing_df['price_per_sqft'].mean(),
                            'median_price_per_sqft': listing_df['price_per_sqft'].median(),
                            'sample_count': len(listing_df),
                            'month_year': datetime.now().strftime('%Y-%m'),
                            'avg_area_sqft': listing_df['area_sqft'].mean(),
                            'avg_bedrooms': listing_df['bedrooms'].mean()
                        }
                        metrics.append(metric)
        
        metrics_df = pd.DataFrame(metrics)
        logger.info(f"Computed metrics for {len(metrics_df)} locality-type combinations")
        
        return metrics_df
    
    def compute_investment_scores(self, df: pd.DataFrame, metrics_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate investment scores for each locality"""
        logger.info("Computing investment scores...")
        
        scores = []
        
        for locality in df['locality'].unique():
            if locality == 'Unknown':
                continue
            
            locality_metrics = metrics_df[metrics_df['locality'] == locality]
            locality_properties = df[df['locality'] == locality]
            
            # Calculate various scores
            score = {
                'locality': locality,
                'investment_score': 0,
                'rental_yield_percentage': 0,
                'liquidity_score': 0,
                'infrastructure_score': 0,
                'connectivity_score': 0,
                'demand_index': 0,
                'risk_score': 0
            }
            
            # Investment score based on multiple factors
            factors = []
            
            # Price appreciation potential (lower avg price = higher potential)
            avg_price = locality_metrics['avg_price'].mean()
            if avg_price > 0:
                price_factor = min(100, (10000000 / avg_price) * 50)  # Normalize to 0-50
                factors.append(price_factor)
            
            # Listing volume (more listings = more liquid market)
            volume_factor = min(50, len(locality_properties) * 2)  # Normalize to 0-50
            factors.append(volume_factor)
            
            score['investment_score'] = np.mean(factors) if factors else 50
            
            # Rental yield calculation
            sale_df = locality_metrics[locality_metrics['listing_type'] == 'sale']
            rent_df = locality_metrics[locality_metrics['listing_type'] == 'rent']
            
            if len(sale_df) > 0 and len(rent_df) > 0:
                avg_sale_price = sale_df['avg_price'].mean()
                avg_rent = rent_df['avg_price'].mean()
                if avg_sale_price > 0:
                    score['rental_yield_percentage'] = (avg_rent * 12 / avg_sale_price) * 100
            
            # Other scores (simplified)
            score['liquidity_score'] = min(100, len(locality_properties) * 5)
            score['infrastructure_score'] = 70  # Default, can be enhanced with POI data
            score['connectivity_score'] = 75  # Default, can be enhanced with transit data
            score['demand_index'] = min(100, len(locality_properties) * 3)
            score['risk_score'] = max(0, 100 - score['investment_score'])
            
            scores.append(score)
        
        scores_df = pd.DataFrame(scores)
        logger.info(f"Computed investment scores for {len(scores_df)} localities")
        
        return scores_df
    
    def load_poi_data(self) -> pd.DataFrame:
        """Load and process POI data"""
        poi_file = self.raw_data_path / 'dataset_crawler-google-places_2025-11-10_00-21-30-144.csv'
        
        if poi_file.exists():
            try:
                poi_df = pd.read_csv(poi_file, low_memory=False)
                logger.info(f"Loaded {len(poi_df)} POI records")
                
                # Process POI data
                poi_df['poi_id'] = poi_df.index.astype(str)
                poi_df['city'] = 'Bangalore'
                
                # Standardize categories - handle if 'types' column exists
                if 'types' in poi_df.columns:
                    poi_df['category'] = poi_df['types'].apply(self._categorize_poi)
                else:
                    # Try other columns that might contain category info
                    poi_df['category'] = 'other'
                    if 'category' in poi_df.columns:
                        poi_df['category'] = poi_df['category'].apply(self._categorize_poi)
                    elif 'title' in poi_df.columns:
                        poi_df['category'] = poi_df['title'].apply(self._categorize_poi)
                
                return poi_df
            except Exception as e:
                logger.error(f"Error loading POI data: {e}")
        
        return pd.DataFrame()
    
    def _categorize_poi(self, types_str: str) -> str:
        """Categorize POI based on Google types"""
        if pd.isna(types_str):
            return 'other'
        
        types_str = str(types_str).lower()
        
        if 'school' in types_str or 'university' in types_str:
            return 'school'
        elif 'hospital' in types_str or 'clinic' in types_str or 'medical' in types_str:
            return 'hospital'
        elif 'mall' in types_str or 'shopping' in types_str:
            return 'mall'
        elif 'metro' in types_str or 'station' in types_str:
            return 'metro_station'
        elif 'park' in types_str:
            return 'park'
        elif 'restaurant' in types_str or 'cafe' in types_str:
            return 'restaurant'
        else:
            return 'other'
    
    def compute_distance_matrix(self, properties_df: pd.DataFrame, poi_df: pd.DataFrame) -> pd.DataFrame:
        """Compute distance from properties to nearest POIs"""
        logger.info("Computing distance matrix...")
        
        # Check if we have POI data
        if poi_df.empty or 'category' not in poi_df.columns:
            logger.warning("No POI data available for distance computation")
            # Return empty dataframe with expected columns
            return pd.DataFrame(columns=['property_id', 'distance_to_metro_m', 
                                        'distance_to_hospital_m', 'distance_to_school_m', 
                                        'distance_to_mall_m'])
        
        # Sample properties to avoid memory issues
        sample_size = min(1000, len(properties_df))
        sample_df = properties_df.sample(n=sample_size, random_state=42)
        
        distance_data = []
        
        for _, prop in sample_df.iterrows():
            if pd.isna(prop['latitude']) or pd.isna(prop['longitude']):
                continue
            
            prop_coords = (prop['latitude'], prop['longitude'])
            
            distances = {
                'property_id': prop['property_id'],
                'distance_to_metro_m': float('inf'),
                'distance_to_hospital_m': float('inf'),
                'distance_to_school_m': float('inf'),
                'distance_to_mall_m': float('inf')
            }
            
            # Find nearest POI of each category
            for category in ['metro_station', 'hospital', 'school', 'mall']:
                category_pois = poi_df[poi_df['category'] == category]
                
                for _, poi in category_pois.iterrows():
                    # Check for lat/lng columns with various names
                    lat = poi.get('latitude') or poi.get('lat') or poi.get('location.lat')
                    lng = poi.get('longitude') or poi.get('lng') or poi.get('location.lng')
                    
                    if pd.notna(lat) and pd.notna(lng):
                        poi_coords = (lat, lng)
                        try:
                            distance = geodesic(prop_coords, poi_coords).meters
                            key = f'distance_to_{category.split("_")[0]}_m'
                            if distance < distances[key]:
                                distances[key] = distance
                        except:
                            pass
            
            # Convert inf to None
            for key in distances:
                if distances[key] == float('inf'):
                    distances[key] = None
            
            distance_data.append(distances)
        
        distance_df = pd.DataFrame(distance_data) if distance_data else pd.DataFrame()
        logger.info(f"Computed distances for {len(distance_df)} properties")
        
        return distance_df
    
    def save_processed_data(self, properties_df, metrics_df, scores_df, distance_df, poi_df):
        """Save all processed data to files"""
        logger.info("Saving processed data...")
        
        # Save main datasets
        properties_df.to_csv(self.processed_data_path / 'properties_bangalore.csv', index=False)
        metrics_df.to_csv(self.processed_data_path / 'locality_metrics.csv', index=False)
        scores_df.to_csv(self.processed_data_path / 'investment_scores.csv', index=False)
        distance_df.to_csv(self.processed_data_path / 'distance_matrix.csv', index=False)
        poi_df.to_csv(self.processed_data_path / 'bangalore_poi.csv', index=False)
        
        # Save summary JSON
        summary = {
            'processing_date': datetime.now().isoformat(),
            'total_properties': len(properties_df),
            'localities': properties_df['locality'].nunique(),
            'property_types': properties_df['property_type'].unique().tolist(),
            'total_pois': len(poi_df),
            'metrics_computed': len(metrics_df),
            'investment_scores': len(scores_df)
        }
        
        with open(self.processed_data_path / 'processing_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info("All data saved successfully")
    
    def run_pipeline(self):
        """Run the complete data processing pipeline"""
        logger.info("Starting Valora Data Pipeline...")
        
        # 1. Load raw data
        properties_df = self.load_all_raw_data()
        if properties_df.empty:
            logger.error("No data to process")
            return
        
        # 2. Process properties
        properties_df = self.process_properties(properties_df)
        logger.info(f"Processed {len(properties_df)} properties")
        
        # 3. Generate embeddings (optional - can be slow)
        # properties_df = self.generate_embeddings(properties_df)
        
        # 4. Compute locality metrics
        metrics_df = self.compute_locality_metrics(properties_df)
        
        # 5. Compute investment scores
        scores_df = self.compute_investment_scores(properties_df, metrics_df)
        
        # 6. Load POI data
        poi_df = self.load_poi_data()
        
        # 7. Compute distance matrix (sample)
        distance_df = self.compute_distance_matrix(properties_df, poi_df)
        
        # 8. Save all processed data
        self.save_processed_data(properties_df, metrics_df, scores_df, distance_df, poi_df)
        
        logger.info("Pipeline completed successfully!")
        
        return {
            'properties': properties_df,
            'metrics': metrics_df,
            'scores': scores_df,
            'distances': distance_df,
            'pois': poi_df
        }


if __name__ == "__main__":
    pipeline = ValoraDataPipeline()
    results = pipeline.run_pipeline()
    
    # Print summary
    if results:
        print("\n=== Pipeline Results ===")
        print(f"Properties processed: {len(results['properties'])}")
        print(f"Localities found: {results['properties']['locality'].nunique()}")
        print(f"Property types: {results['properties']['property_type'].unique()}")
        print(f"Metrics computed: {len(results['metrics'])}")
        print(f"Investment scores: {len(results['scores'])}")
        print(f"POIs loaded: {len(results['pois'])}")
        print("\nTop 5 investment localities:")
        print(results['scores'].nlargest(5, 'investment_score')[['locality', 'investment_score', 'rental_yield_percentage']])
