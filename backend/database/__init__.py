"""
Valora Database Module
SpatiaLite-based spatial database for properties, POIs, and urban data
"""

from .db_service import DatabaseService, get_db_service
from .query_service import DatabaseQueryService, get_query_service

__all__ = [
    'DatabaseService',
    'get_db_service',
    'DatabaseQueryService',
    'get_query_service',
]

__version__ = '2.0.0'
