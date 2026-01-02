"""
Data Service for Valora AI
Provides access to processed property data, metrics, and investment scores
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from functools import lru_cache

logger = logging.getLogger(__name__)

class ValoraDataService:
    """Central data service for processed property data"""
    
    def __init__(self):
        self.processed_path = Path("data/processed")
        self.properties_df = None
        self.metrics_df = None
        self.scores_df = None
        self.poi_df = None
        self.distance_df = None
        
        # Load all data on initialization
        self.load_all_data()
    
    @lru_cache(maxsize=1)
    def load_all_data(self):
        """Load all processed data files"""
        try:
            # Load properties
            properties_file = self.processed_path / 'properties_bangalore.csv'
            if properties_file.exists():
                self.properties_df = pd.read_csv(properties_file)
                logger.info(f"Loaded {len(self.properties_df)} properties")
            else:
                logger.warning("Properties file not found")
                self.properties_df = pd.DataFrame()
            
            # Load metrics
            metrics_file = self.processed_path / 'locality_metrics.csv'
            if metrics_file.exists():
                self.metrics_df = pd.read_csv(metrics_file)
                logger.info(f"Loaded metrics for {len(self.metrics_df)} locality-type combinations")
            else:
                self.metrics_df = pd.DataFrame()
            
            # Load investment scores
            scores_file = self.processed_path / 'investment_scores.csv'
            if scores_file.exists():
                self.scores_df = pd.read_csv(scores_file)
                logger.info(f"Loaded investment scores for {len(self.scores_df)} localities")
            else:
                self.scores_df = pd.DataFrame()
            
            # Load POI data
            poi_file = self.processed_path / 'bangalore_poi.csv'
            if poi_file.exists():
                self.poi_df = pd.read_csv(poi_file)
                logger.info(f"Loaded {len(self.poi_df)} POIs")
            else:
                self.poi_df = pd.DataFrame()
            
            # Load distance matrix
            distance_file = self.processed_path / 'distance_matrix.csv'
            if distance_file.exists():
                self.distance_df = pd.read_csv(distance_file)
                logger.info(f"Loaded distance matrix for {len(self.distance_df)} properties")
            else:
                self.distance_df = pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def search_properties(self, 
                         locality: Optional[str] = None,
                         property_type: Optional[str] = None,
                         listing_type: Optional[str] = None,
                         bedrooms: Optional[int] = None,
                         min_price: Optional[float] = None,
                         max_price: Optional[float] = None,
                         min_area: Optional[float] = None,
                         max_area: Optional[float] = None,
                         limit: int = 100) -> List[Dict]:
        """Search properties with filters"""
        
        if self.properties_df.empty:
            return []
        
        df = self.properties_df.copy()
        
        # Apply filters
        if locality:
            df = df[df['locality'].str.contains(locality, case=False, na=False)]
        
        if property_type:
            df = df[df['property_type'] == property_type]
        
        if listing_type:
            df = df[df['listing_type'] == listing_type]
        
        if bedrooms:
            df = df[df['bedrooms'] == bedrooms]
        
        if min_price:
            df = df[df['price'] >= min_price]
        
        if max_price:
            df = df[df['price'] <= max_price]
        
        if min_area:
            df = df[df['area_sqft'] >= min_area]
        
        if max_area:
            df = df[df['area_sqft'] <= max_area]
        
        # Sort by price
        df = df.sort_values('price')
        
        # Limit results
        df = df.head(limit)
        
        # Convert to dict
        results = df.to_dict('records')
        
        # Clean NaN values
        for result in results:
            for key in result:
                if pd.isna(result[key]):
                    result[key] = None
        
        return results
    
    def get_locality_metrics(self, locality: str) -> Dict[str, Any]:
        """Get metrics for a specific locality"""
        
        if self.metrics_df.empty:
            return {}
        
        locality_data = self.metrics_df[
            self.metrics_df['locality'].str.contains(locality, case=False, na=False)
        ]
        
        if locality_data.empty:
            return {}
        
        # Aggregate across property types
        metrics = {
            'locality': locality,
            'avg_price': locality_data['avg_price'].mean(),
            'median_price': locality_data['median_price'].median(),
            'min_price': locality_data['min_price'].min(),
            'max_price': locality_data['max_price'].max(),
            'avg_price_per_sqft': locality_data['avg_price_per_sqft'].mean(),
            'total_properties': locality_data['sample_count'].sum(),
            'property_types': locality_data['property_type'].unique().tolist()
        }
        
        # Clean NaN values
        for key in metrics:
            if isinstance(metrics[key], float) and pd.isna(metrics[key]):
                metrics[key] = None
        
        return metrics
    
    def get_investment_scores(self, localities: Optional[List[str]] = None) -> List[Dict]:
        """Get investment scores for localities"""
        
        if self.scores_df.empty:
            return []
        
        df = self.scores_df.copy()
        
        if localities:
            # Filter to requested localities
            df = df[df['locality'].isin(localities)]
        
        # Sort by investment score
        df = df.sort_values('investment_score', ascending=False)
        
        return df.to_dict('records')
    
    def compare_localities(self, locality1: str, locality2: str) -> Dict[str, Any]:
        """Compare two localities"""
        
        metrics1 = self.get_locality_metrics(locality1)
        metrics2 = self.get_locality_metrics(locality2)
        
        if not metrics1 or not metrics2:
            return {'error': 'One or both localities not found'}
        
        # Get investment scores
        scores = self.scores_df[
            self.scores_df['locality'].isin([locality1, locality2])
        ].set_index('locality').to_dict('index')
        
        comparison = {
            'locality1': {
                'name': locality1,
                'metrics': metrics1,
                'investment_score': scores.get(locality1, {}).get('investment_score', 0),
                'rental_yield': scores.get(locality1, {}).get('rental_yield_percentage', 0)
            },
            'locality2': {
                'name': locality2,
                'metrics': metrics2,
                'investment_score': scores.get(locality2, {}).get('investment_score', 0),
                'rental_yield': scores.get(locality2, {}).get('rental_yield_percentage', 0)
            },
            'recommendation': self._generate_recommendation(metrics1, metrics2, scores)
        }
        
        return comparison
    
    def _generate_recommendation(self, metrics1: Dict, metrics2: Dict, scores: Dict) -> str:
        """Generate investment recommendation"""
        
        score1 = scores.get(list(scores.keys())[0] if scores else '', {}).get('investment_score', 0)
        score2 = scores.get(list(scores.keys())[-1] if len(scores) > 1 else '', {}).get('investment_score', 0)
        
        if score1 > score2:
            return f"{metrics1['locality']} has a higher investment score and may offer better returns"
        elif score2 > score1:
            return f"{metrics2['locality']} has a higher investment score and may offer better returns"
        else:
            return "Both localities have similar investment potential"
    
    def get_market_summary(self) -> Dict[str, Any]:
        """Get overall market summary"""
        
        if self.properties_df.empty:
            return {}
        
        summary = {
            'total_properties': len(self.properties_df),
            'localities': self.properties_df['locality'].nunique(),
            'avg_price': self.properties_df['price'].mean(),
            'median_price': self.properties_df['price'].median(),
            'price_range': {
                'min': self.properties_df['price'].min(),
                'max': self.properties_df['price'].max()
            },
            'top_localities_by_volume': self.properties_df['locality'].value_counts().head(5).to_dict(),
            'property_type_distribution': self.properties_df['property_type'].value_counts().to_dict(),
            'listing_type_distribution': self.properties_df['listing_type'].value_counts().to_dict(),
            'bedroom_distribution': self.properties_df['bedrooms'].value_counts().to_dict()
        }
        
        return summary
    
    def get_top_properties(self, 
                          category: str = 'affordable',
                          limit: int = 10) -> List[Dict]:
        """Get top properties by category"""
        
        if self.properties_df.empty:
            return []
        
        df = self.properties_df.copy()
        
        # Remove properties with missing critical fields
        df = df.dropna(subset=['price', 'area_sqft', 'locality'])
        
        if category == 'affordable':
            # Properties with best price per sqft
            df = df[df['price_per_sqft'].notna()]
            df = df.sort_values('price_per_sqft').head(limit)
        
        elif category == 'luxury':
            # Most expensive properties
            df = df.sort_values('price', ascending=False).head(limit)
        
        elif category == 'investment':
            # Properties in high investment score localities
            if not self.scores_df.empty:
                top_localities = self.scores_df.nlargest(5, 'investment_score')['locality'].tolist()
                df = df[df['locality'].isin(top_localities)]
                df = df.sort_values('price').head(limit)
        
        elif category == 'family':
            # 3+ BHK properties
            df = df[df['bedrooms'] >= 3]
            df = df.sort_values('price').head(limit)
        
        else:
            # Default: newest listings
            df = df.head(limit)
        
        return df.to_dict('records')
    
    def analyze_roi(self, locality: str, property_type: str = 'residential_apartment') -> Dict[str, Any]:
        """Analyze ROI for a locality and property type"""
        
        if self.metrics_df.empty or self.scores_df.empty:
            return {}
        
        # Get metrics for the specific combination
        metrics = self.metrics_df[
            (self.metrics_df['locality'].str.contains(locality, case=False, na=False)) &
            (self.metrics_df['property_type'] == property_type)
        ]
        
        if metrics.empty:
            return {}
        
        # Get investment scores
        scores = self.scores_df[
            self.scores_df['locality'].str.contains(locality, case=False, na=False)
        ]
        
        sale_metrics = metrics[metrics['listing_type'] == 'sale']
        rent_metrics = metrics[metrics['listing_type'] == 'rent']
        
        roi_analysis = {
            'locality': locality,
            'property_type': property_type,
            'avg_sale_price': sale_metrics['avg_price'].mean() if not sale_metrics.empty else 0,
            'avg_rent': rent_metrics['avg_price'].mean() if not rent_metrics.empty else 0,
            'rental_yield': scores['rental_yield_percentage'].iloc[0] if not scores.empty else 0,
            'investment_score': scores['investment_score'].iloc[0] if not scores.empty else 0,
            'price_appreciation_estimate': 8.5,  # Default estimate
            'payback_period_years': 0,
            'recommendation': ''
        }
        
        # Calculate payback period
        if roi_analysis['avg_rent'] > 0 and roi_analysis['avg_sale_price'] > 0:
            annual_rent = roi_analysis['avg_rent'] * 12
            roi_analysis['payback_period_years'] = roi_analysis['avg_sale_price'] / annual_rent
        
        # Generate recommendation
        if roi_analysis['rental_yield'] > 4:
            roi_analysis['recommendation'] = 'Excellent rental yield - Good for rental income'
        elif roi_analysis['investment_score'] > 70:
            roi_analysis['recommendation'] = 'High investment potential - Good for appreciation'
        else:
            roi_analysis['recommendation'] = 'Moderate investment opportunity'
        
        return roi_analysis
    
    def get_nearby_pois(self, latitude: float, longitude: float, radius_m: float = 5000) -> List[Dict]:
        """Get nearby POIs for a location"""
        
        if self.poi_df.empty:
            return []
        
        # Simple distance calculation (can be optimized with spatial indexing)
        from geopy.distance import geodesic
        
        pois = []
        location = (latitude, longitude)
        
        for _, poi in self.poi_df.iterrows():
            if 'latitude' in poi and 'longitude' in poi:
                if pd.notna(poi['latitude']) and pd.notna(poi['longitude']):
                    poi_location = (poi['latitude'], poi['longitude'])
                    try:
                        distance = geodesic(location, poi_location).meters
                        if distance <= radius_m:
                            poi_dict = poi.to_dict()
                            poi_dict['distance_m'] = distance
                            pois.append(poi_dict)
                    except:
                        pass
        
        # Sort by distance
        pois.sort(key=lambda x: x['distance_m'])
        
        return pois[:50]  # Limit to 50 nearest
    
    def forecast_prices(self, locality: str, months: int = 12) -> Dict[str, Any]:
        """Simple price forecasting"""
        
        if self.metrics_df.empty:
            return {}
        
        locality_metrics = self.metrics_df[
            self.metrics_df['locality'].str.contains(locality, case=False, na=False)
        ]
        
        if locality_metrics.empty:
            return {}
        
        current_avg_price = locality_metrics['avg_price'].mean()
        
        # Simple linear projection (can be replaced with ML model)
        annual_growth_rate = 0.085  # 8.5% default
        monthly_growth_rate = annual_growth_rate / 12
        
        forecast = {
            'locality': locality,
            'current_avg_price': current_avg_price,
            'forecast': []
        }
        
        for month in range(1, months + 1):
            forecasted_price = current_avg_price * (1 + monthly_growth_rate * month)
            forecast['forecast'].append({
                'month': month,
                'price': forecasted_price,
                'growth_percentage': (monthly_growth_rate * month * 100)
            })
        
        return forecast


# Singleton instance
data_service = ValoraDataService()

# Export functions for direct use
def get_data_service() -> ValoraDataService:
    """Get the singleton data service instance"""
    return data_service

def search_properties(**kwargs) -> List[Dict]:
    """Search properties"""
    return data_service.search_properties(**kwargs)

def get_locality_metrics(locality: str) -> Dict[str, Any]:
    """Get locality metrics"""
    return data_service.get_locality_metrics(locality)

def get_market_summary() -> Dict[str, Any]:
    """Get market summary"""
    return data_service.get_market_summary()

def compare_localities(locality1: str, locality2: str) -> Dict[str, Any]:
    """Compare two localities"""
    return data_service.compare_localities(locality1, locality2)

def analyze_roi(locality: str, property_type: str = 'residential_apartment') -> Dict[str, Any]:
    """Analyze ROI"""
    return data_service.analyze_roi(locality, property_type)
