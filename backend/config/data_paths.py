"""
Data Paths Configuration
Centralized management of data directories for multi-city deployment.
"""

import os
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass

# Base directories
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_ROOT = PROJECT_ROOT / "data"


@dataclass
class CityDataPaths:
    """Data paths for a specific city"""
    city_id: str
    raw: Path
    processed: Path
    models: Path
    gis: Path
    cache: Path
    
    def ensure_exists(self):
        """Create all directories if they don't exist"""
        for path in [self.raw, self.processed, self.models, self.gis, self.cache]:
            path.mkdir(parents=True, exist_ok=True)
    
    def get_raw_file(self, filename: str) -> Path:
        """Get path to a raw data file"""
        return self.raw / filename
    
    def get_processed_file(self, filename: str) -> Path:
        """Get path to a processed data file"""
        return self.processed / filename
    
    def get_model_file(self, filename: str) -> Path:
        """Get path to a model file"""
        return self.models / filename
    
    def get_gis_file(self, filename: str) -> Path:
        """Get path to a GIS file"""
        return self.gis / filename


@dataclass  
class SharedDataPaths:
    """Shared data paths across all cities"""
    embeddings: Path
    models: Path
    config: Path
    cache: Path
    exports: Path
    uploads: Path
    
    def ensure_exists(self):
        """Create all directories if they don't exist"""
        for path in [self.embeddings, self.models, self.config, 
                     self.cache, self.exports, self.uploads]:
            path.mkdir(parents=True, exist_ok=True)


class DataPathManager:
    """
    Centralized manager for all data paths.
    Supports multi-city data organization.
    """
    
    # Directory structure
    CITY_SUBDIRS = ['raw', 'processed', 'models', 'gis', 'cache']
    SHARED_SUBDIRS = ['embeddings', 'models', 'config', 'cache']
    
    def __init__(self, data_root: Optional[Path] = None):
        self.data_root = Path(data_root) if data_root else DATA_ROOT
        self.cities_root = self.data_root / "cities"
        self.shared_root = self.data_root / "shared"
        self.exports_root = self.data_root / "exports"
        self.uploads_root = self.data_root / "uploads"
        
        # Legacy paths (for backward compatibility)
        self.legacy_raw = self.data_root / "raw"
        self.legacy_processed = self.data_root / "processed"
        self.legacy_models = self.data_root / "models"
        
        self._city_paths_cache: Dict[str, CityDataPaths] = {}
    
    def get_city_paths(self, city_id: str) -> CityDataPaths:
        """Get data paths for a specific city"""
        city_id = city_id.lower()
        
        if city_id not in self._city_paths_cache:
            city_root = self.cities_root / city_id
            self._city_paths_cache[city_id] = CityDataPaths(
                city_id=city_id,
                raw=city_root / "raw",
                processed=city_root / "processed",
                models=city_root / "models",
                gis=city_root / "gis",
                cache=city_root / "cache"
            )
        
        return self._city_paths_cache[city_id]
    
    def get_shared_paths(self) -> SharedDataPaths:
        """Get shared data paths"""
        return SharedDataPaths(
            embeddings=self.shared_root / "embeddings",
            models=self.shared_root / "models",
            config=self.shared_root / "config",
            cache=self.shared_root / "cache",
            exports=self.exports_root,
            uploads=self.uploads_root
        )
    
    def ensure_city_structure(self, city_id: str):
        """Create directory structure for a city"""
        paths = self.get_city_paths(city_id)
        paths.ensure_exists()
    
    def ensure_all_structures(self, city_ids: list):
        """Create directory structure for all cities"""
        for city_id in city_ids:
            self.ensure_city_structure(city_id)
        self.get_shared_paths().ensure_exists()
    
    # Convenience methods for common file types
    
    def get_properties_file(self, city_id: str, property_type: str = "all") -> Path:
        """Get path to properties data file"""
        paths = self.get_city_paths(city_id)
        return paths.raw / f"properties_{property_type}.csv"
    
    def get_transactions_file(self, city_id: str) -> Path:
        """Get path to transactions data file"""
        paths = self.get_city_paths(city_id)
        return paths.raw / "transactions.csv"
    
    def get_training_data(self, city_id: str) -> Path:
        """Get path to processed training data"""
        paths = self.get_city_paths(city_id)
        return paths.processed / "training_data.csv"
    
    def get_price_model(self, city_id: str, property_type: str = "residential") -> Path:
        """Get path to price prediction model"""
        paths = self.get_city_paths(city_id)
        return paths.models / f"price_model_{property_type}.joblib"
    
    def get_rental_model(self, city_id: str) -> Path:
        """Get path to rental yield model"""
        paths = self.get_city_paths(city_id)
        return paths.models / "rental_yield_model.joblib"
    
    def get_demand_model(self, city_id: str) -> Path:
        """Get path to demand model"""
        paths = self.get_city_paths(city_id)
        return paths.models / "demand_model.joblib"
    
    def get_ward_boundaries(self, city_id: str) -> Path:
        """Get path to ward boundaries GIS file"""
        paths = self.get_city_paths(city_id)
        return paths.gis / "ward_boundaries.geojson"
    
    def get_pois_file(self, city_id: str) -> Path:
        """Get path to POIs data file"""
        paths = self.get_city_paths(city_id)
        return paths.gis / "pois.geojson"
    
    # Legacy path methods (for backward compatibility)
    
    def get_legacy_raw_path(self) -> Path:
        """Get legacy raw data path (deprecated)"""
        return self.legacy_raw
    
    def get_legacy_models_path(self) -> Path:
        """Get legacy models path (deprecated)"""
        return self.legacy_models
    
    def list_available_cities(self) -> list:
        """List cities that have data directories"""
        if not self.cities_root.exists():
            return []
        return [d.name for d in self.cities_root.iterdir() if d.is_dir()]
    
    def get_city_data_status(self, city_id: str) -> Dict[str, bool]:
        """Check what data is available for a city"""
        paths = self.get_city_paths(city_id)
        
        return {
            "has_raw_data": any(paths.raw.glob("*.csv")) if paths.raw.exists() else False,
            "has_processed_data": any(paths.processed.glob("*.csv")) if paths.processed.exists() else False,
            "has_models": any(paths.models.glob("*.joblib")) if paths.models.exists() else False,
            "has_gis_data": any(paths.gis.glob("*.*")) if paths.gis.exists() else False,
        }


# Global instance
data_path_manager = DataPathManager()


# Convenience functions
def get_city_data_path(city_id: str) -> CityDataPaths:
    """Get data paths for a city"""
    return data_path_manager.get_city_paths(city_id)


def get_shared_data_path() -> SharedDataPaths:
    """Get shared data paths"""
    return data_path_manager.get_shared_paths()


def ensure_data_structure(city_ids: list = None):
    """Ensure data directory structure exists"""
    if city_ids is None:
        city_ids = ['bangalore', 'mumbai', 'delhi', 'hyderabad', 'chennai', 'pune']
    data_path_manager.ensure_all_structures(city_ids)
