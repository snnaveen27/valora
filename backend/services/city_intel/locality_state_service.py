"""
Locality State Service
Computes and stores ward-level market snapshots for the City Intelligence Engine.
Supports multi-city deployment.
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Import city configuration
try:
    from backend.config.cities import city_manager, get_city_config, CityConfig
except ImportError:
    from config.cities import city_manager, get_city_config, CityConfig

logger = logging.getLogger(__name__)


@dataclass
class LocalityState:
    """Current state snapshot for a ward/locality"""
    ward_id: str
    ward_name: str
    zone_name: Optional[str] = None
    
    # Market Metrics
    avg_price_sqft: Optional[float] = None
    median_price: Optional[float] = None
    price_change_1m: Optional[float] = None
    price_change_3m: Optional[float] = None
    price_change_6m: Optional[float] = None
    price_change_12m: Optional[float] = None
    
    # Supply/Demand
    active_listings: Optional[int] = None
    absorption_rate: Optional[float] = None
    days_on_market_avg: Optional[float] = None
    inventory_months: Optional[float] = None
    
    # Rental Metrics
    avg_rental_yield: Optional[float] = None
    avg_rent_sqft: Optional[float] = None
    
    # Infrastructure
    infrastructure_score: Optional[float] = None
    connectivity_score: Optional[float] = None
    poi_density: Optional[float] = None
    distance_to_metro: Optional[float] = None
    
    # Classifications
    growth_phase: Optional[str] = None
    investor_type: Optional[str] = None
    
    # Risk Indices (0-1)
    risk_index_flood: Optional[float] = None
    risk_index_infra: Optional[float] = None
    risk_index_liquidity: Optional[float] = None
    risk_index_overall: Optional[float] = None
    
    # Forecasts
    price_forecast_1y: Optional[float] = None
    price_forecast_3y: Optional[float] = None
    forecast_confidence: Optional[float] = None
    
    # Metadata
    computed_at: Optional[datetime] = None
    data_quality_score: Optional[float] = None


class LocalityStateService:
    """
    Aggregates property and market data into ward-level snapshots.
    These snapshots power the City Intelligence Engine.
    Supports multi-city deployment.
    """
    
    def __init__(self, db_engine=None, city_id: Optional[str] = None):
        self.db_engine = db_engine
        self.city_id = city_id or city_manager.current_city
        self.city_config = get_city_config(self.city_id)
        self._cache = {}
        logger.info(f"LocalityStateService initialized for city: {self.city_id}")
    
    def compute_ward_metrics(self, ward_id: str) -> Dict[str, Any]:
        """
        Compute all metrics for a single ward.
        
        Returns dict with:
        - Market metrics (prices, changes)
        - Supply/demand (listings, absorption)
        - Infrastructure scores
        - Risk indices
        """
        if not self.db_engine:
            logger.warning("No database connection. Returning synthetic data.")
            return self._generate_synthetic_metrics(ward_id)
        
        try:
            metrics = {}
            
            # Query property data for this ward
            metrics.update(self._compute_price_metrics(ward_id))
            metrics.update(self._compute_supply_demand(ward_id))
            metrics.update(self._compute_infrastructure(ward_id))
            
            metrics['ward_id'] = ward_id
            metrics['computed_at'] = datetime.now()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error computing metrics for ward {ward_id}: {e}")
            return self._generate_synthetic_metrics(ward_id)
    
    def compute_all_wards(self) -> List[Dict[str, Any]]:
        """Compute metrics for all wards in the city."""
        ward_ids = self._get_all_ward_ids()
        results = []
        
        for ward_id in ward_ids:
            try:
                metrics = self.compute_ward_metrics(ward_id)
                results.append(metrics)
            except Exception as e:
                logger.error(f"Failed to compute metrics for ward {ward_id}: {e}")
        
        logger.info(f"Computed metrics for {len(results)} wards")
        return results
    
    def save_snapshot(self, ward_id: str, metrics: Dict[str, Any]) -> bool:
        """Save current state to locality_state table."""
        if not self.db_engine:
            logger.warning("No database connection. Caching locally.")
            self._cache[ward_id] = metrics
            return True
        
        try:
            # TODO: Implement database insert/update
            self._cache[ward_id] = metrics
            return True
        except Exception as e:
            logger.error(f"Error saving snapshot for ward {ward_id}: {e}")
            return False
    
    def save_historical_snapshot(self, ward_id: str, metrics: Dict[str, Any], snapshot_date: date) -> bool:
        """Save to locality_state_ts for time series."""
        if not self.db_engine:
            return False
        
        try:
            # TODO: Implement database insert
            return True
        except Exception as e:
            logger.error(f"Error saving historical snapshot for ward {ward_id}: {e}")
            return False
    
    def get_ward_state(self, ward_id: str) -> Optional[Dict[str, Any]]:
        """Get current state for a ward."""
        if ward_id in self._cache:
            return self._cache[ward_id]
        
        if not self.db_engine:
            return self._generate_synthetic_metrics(ward_id)
        
        try:
            # TODO: Query from database
            return None
        except Exception as e:
            logger.error(f"Error getting state for ward {ward_id}: {e}")
            return None
    
    def get_ward_timeline(self, ward_id: str, months: int = 24) -> List[Dict[str, Any]]:
        """Get historical snapshots for evolution timeline."""
        if not self.db_engine:
            return self._generate_synthetic_timeline(ward_id, months)
        
        try:
            # TODO: Query from database
            return []
        except Exception as e:
            logger.error(f"Error getting timeline for ward {ward_id}: {e}")
            return []
    
    def run_daily_update(self):
        """Scheduled job to update all ward states."""
        logger.info("Starting daily locality state update...")
        wards = self._get_all_ward_ids()
        
        success_count = 0
        for ward_id in wards:
            try:
                metrics = self.compute_ward_metrics(ward_id)
                if self.save_snapshot(ward_id, metrics):
                    self.save_historical_snapshot(ward_id, metrics, date.today())
                    success_count += 1
            except Exception as e:
                logger.error(f"Failed to update ward {ward_id}: {e}")
        
        logger.info(f"Completed update for {success_count}/{len(wards)} wards")
    
    # Private methods
    
    def _get_all_ward_ids(self) -> List[str]:
        """Get list of all ward IDs from database or return sample."""
        if not self.db_engine:
            # Return sample Bangalore wards
            return [
                "WARD_001", "WARD_002", "WARD_003", "WARD_004", "WARD_005",
                "WARD_010", "WARD_020", "WARD_030", "WARD_040", "WARD_050"
            ]
        
        try:
            # TODO: Query from gis_bbmp_wards table
            return []
        except Exception as e:
            logger.error(f"Error getting ward IDs: {e}")
            return []
    
    def _compute_price_metrics(self, ward_id: str) -> Dict[str, Any]:
        """Compute price-related metrics from properties table."""
        # TODO: Implement actual database queries
        return {
            'avg_price_sqft': None,
            'median_price': None,
            'price_change_1m': None,
            'price_change_3m': None,
            'price_change_6m': None,
            'price_change_12m': None
        }
    
    def _compute_supply_demand(self, ward_id: str) -> Dict[str, Any]:
        """Compute supply/demand metrics."""
        # TODO: Implement actual database queries
        return {
            'active_listings': None,
            'absorption_rate': None,
            'days_on_market_avg': None,
            'inventory_months': None
        }
    
    def _compute_infrastructure(self, ward_id: str) -> Dict[str, Any]:
        """Compute infrastructure scores from POI data."""
        # TODO: Implement actual database queries
        return {
            'infrastructure_score': None,
            'connectivity_score': None,
            'poi_density': None,
            'distance_to_metro': None
        }
    
    def _generate_synthetic_metrics(self, ward_id: str) -> Dict[str, Any]:
        """Generate synthetic metrics for testing."""
        import numpy as np
        
        return {
            'ward_id': ward_id,
            'ward_name': f"Ward {ward_id}",
            'zone_name': "Zone A",
            'avg_price_sqft': round(np.random.uniform(4000, 12000), 2),
            'median_price': round(np.random.uniform(5000000, 20000000), 2),
            'price_change_1m': round(np.random.uniform(-2, 3), 2),
            'price_change_3m': round(np.random.uniform(-3, 6), 2),
            'price_change_6m': round(np.random.uniform(-5, 10), 2),
            'price_change_12m': round(np.random.uniform(-5, 15), 2),
            'active_listings': int(np.random.uniform(50, 500)),
            'absorption_rate': round(np.random.uniform(0.3, 0.8), 2),
            'days_on_market_avg': round(np.random.uniform(30, 120), 1),
            'inventory_months': round(np.random.uniform(3, 12), 1),
            'avg_rental_yield': round(np.random.uniform(2.5, 5.0), 2),
            'infrastructure_score': round(np.random.uniform(0.4, 0.9), 2),
            'connectivity_score': round(np.random.uniform(0.3, 0.95), 2),
            'poi_density': round(np.random.uniform(10, 100), 1),
            'growth_phase': np.random.choice(['emerging', 'accelerating', 'mature', 'saturated']),
            'investor_type': np.random.choice(['speculative', 'stable_yield', 'defensive']),
            'risk_index_overall': round(np.random.uniform(0.2, 0.7), 2),
            'computed_at': datetime.now(),
            'data_quality_score': round(np.random.uniform(0.6, 0.95), 2)
        }
    
    def _generate_synthetic_timeline(self, ward_id: str, months: int) -> List[Dict[str, Any]]:
        """Generate synthetic historical data for testing."""
        import numpy as np
        from datetime import timedelta
        
        timeline = []
        base_price = np.random.uniform(5000, 10000)
        
        for i in range(months):
            snapshot_date = date.today() - timedelta(days=30 * (months - i - 1))
            price_trend = 1 + (i / months) * np.random.uniform(0.05, 0.15)
            
            timeline.append({
                'ward_id': ward_id,
                'snapshot_date': snapshot_date.isoformat(),
                'avg_price_sqft': round(base_price * price_trend, 2),
                'growth_phase': np.random.choice(['emerging', 'accelerating', 'mature']),
                'risk_index_overall': round(np.random.uniform(0.2, 0.6), 2)
            })
        
        return timeline
