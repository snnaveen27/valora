"""
Configuration module for Valora City Intelligence Engine
"""

from .cities import (
    CityConfig,
    CityManager,
    CityBoundingBox,
    SupportedCity,
    CITY_CONFIGS,
    city_manager,
    get_city_config,
    get_default_center,
    get_sample_areas
)

from .data_paths import (
    DataPathManager,
    CityDataPaths,
    SharedDataPaths,
    data_path_manager,
    get_city_data_path,
    get_shared_data_path,
    ensure_data_structure,
    DATA_ROOT,
    PROJECT_ROOT
)

__all__ = [
    # City configuration
    'CityConfig',
    'CityManager', 
    'CityBoundingBox',
    'SupportedCity',
    'CITY_CONFIGS',
    'city_manager',
    'get_city_config',
    'get_default_center',
    'get_sample_areas',
    # Data paths
    'DataPathManager',
    'CityDataPaths',
    'SharedDataPaths',
    'data_path_manager',
    'get_city_data_path',
    'get_shared_data_path',
    'ensure_data_structure',
    'DATA_ROOT',
    'PROJECT_ROOT'
]
