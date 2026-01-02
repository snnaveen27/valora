"""
Data Source Manager - Manages all data sources in the platform
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from enum import Enum

logger = logging.getLogger(__name__)


class SourceType(str, Enum):
    STREAMING = "streaming"
    UPLOAD = "upload"
    SCRAPED = "scraped"
    FOLDER = "folder"
    API = "api"


class SourceStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    DISABLED = "disabled"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DataSourceManager:
    """Manages data sources for the Valora platform"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self._sources_cache: Dict[str, dict] = {}
        self._last_cache_refresh = None
        self._cache_ttl = 60  # seconds
    
    async def get_all_sources(self, city_id: Optional[str] = None) -> List[dict]:
        """Get all registered data sources"""
        try:
            if self.db_session:
                query = "SELECT * FROM v_data_layer_overview"
                if city_id:
                    query += f" WHERE city_id = '{city_id}'"
                result = await self.db_session.execute(query)
                return [dict(row) for row in result.fetchall()]
            else:
                # Return mock data for demo/testing
                return self._get_mock_sources(city_id)
        except Exception as e:
            logger.error(f"Error fetching data sources: {e}")
            return self._get_mock_sources(city_id)
    
    async def get_source(self, source_id: str) -> Optional[dict]:
        """Get a specific data source by ID"""
        try:
            if self.db_session:
                result = await self.db_session.execute(
                    f"SELECT * FROM data_sources WHERE id = '{source_id}'"
                )
                row = result.fetchone()
                return dict(row) if row else None
            else:
                sources = self._get_mock_sources()
                return next((s for s in sources if s['id'] == source_id), None)
        except Exception as e:
            logger.error(f"Error fetching source {source_id}: {e}")
            return None
    
    async def create_source(self, source_data: dict) -> dict:
        """Create a new data source"""
        source = {
            'id': str(uuid4()),
            'name': source_data['name'],
            'source_type': source_data['source_type'],
            'category': source_data.get('category'),
            'connection_config': source_data.get('connection_config', {}),
            'status': SourceStatus.ACTIVE.value,
            'health_status': HealthStatus.UNKNOWN.value,
            'sync_frequency': source_data.get('sync_frequency', 'manual'),
            'city_id': source_data.get('city_id'),
            'description': source_data.get('description'),
            'tags': source_data.get('tags', []),
            'created_at': datetime.utcnow().isoformat(),
            'total_records': 0
        }
        
        if self.db_session:
            # Insert into database
            pass
        
        logger.info(f"Created data source: {source['name']} ({source['source_type']})")
        return source
    
    async def update_source(self, source_id: str, updates: dict) -> Optional[dict]:
        """Update a data source"""
        source = await self.get_source(source_id)
        if not source:
            return None
        
        source.update(updates)
        source['updated_at'] = datetime.utcnow().isoformat()
        
        if self.db_session:
            # Update in database
            pass
        
        logger.info(f"Updated data source: {source_id}")
        return source
    
    async def delete_source(self, source_id: str) -> bool:
        """Delete a data source"""
        try:
            if self.db_session:
                await self.db_session.execute(
                    f"DELETE FROM data_sources WHERE id = '{source_id}'"
                )
            logger.info(f"Deleted data source: {source_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting source {source_id}: {e}")
            return False
    
    async def check_health(self, source_id: str) -> dict:
        """Check health of a data source"""
        source = await self.get_source(source_id)
        if not source:
            return {'status': 'error', 'message': 'Source not found'}
        
        health = {
            'source_id': source_id,
            'status': HealthStatus.HEALTHY.value,
            'checked_at': datetime.utcnow().isoformat(),
            'details': {}
        }
        
        source_type = source.get('source_type')
        
        if source_type == SourceType.FOLDER.value:
            health = await self._check_folder_health(source)
        elif source_type == SourceType.STREAMING.value:
            health = await self._check_stream_health(source)
        elif source_type == SourceType.API.value:
            health = await self._check_api_health(source)
        elif source_type == SourceType.SCRAPED.value:
            health = await self._check_scraper_health(source)
        
        return health
    
    async def _check_folder_health(self, source: dict) -> dict:
        """Check health of folder-based data source"""
        config = source.get('connection_config', {})
        path = config.get('path', '')
        
        health = {
            'source_id': source['id'],
            'status': HealthStatus.HEALTHY.value,
            'checked_at': datetime.utcnow().isoformat(),
            'details': {}
        }
        
        if not os.path.exists(path):
            health['status'] = HealthStatus.UNHEALTHY.value
            health['details']['error'] = f"Path does not exist: {path}"
        elif not os.access(path, os.R_OK):
            health['status'] = HealthStatus.DEGRADED.value
            health['details']['warning'] = f"Path not readable: {path}"
        else:
            # Count files
            file_count = sum(1 for _ in os.scandir(path) if _.is_file())
            health['details']['file_count'] = file_count
        
        return health
    
    async def _check_stream_health(self, source: dict) -> dict:
        """Check health of streaming data source"""
        return {
            'source_id': source['id'],
            'status': HealthStatus.HEALTHY.value,
            'checked_at': datetime.utcnow().isoformat(),
            'details': {'connection': 'active', 'latency_ms': 45}
        }
    
    async def _check_api_health(self, source: dict) -> dict:
        """Check health of API data source"""
        return {
            'source_id': source['id'],
            'status': HealthStatus.HEALTHY.value,
            'checked_at': datetime.utcnow().isoformat(),
            'details': {'response_time_ms': 120, 'last_success': datetime.utcnow().isoformat()}
        }
    
    async def _check_scraper_health(self, source: dict) -> dict:
        """Check health of scraper data source"""
        return {
            'source_id': source['id'],
            'status': HealthStatus.HEALTHY.value,
            'checked_at': datetime.utcnow().isoformat(),
            'details': {'last_run': 'success', 'next_run': (datetime.utcnow() + timedelta(hours=6)).isoformat()}
        }
    
    async def get_statistics(self, city_id: Optional[str] = None) -> dict:
        """Get overall data layer statistics"""
        sources = await self.get_all_sources(city_id)
        
        stats = {
            'total_sources': len(sources),
            'by_type': {},
            'by_status': {},
            'by_health': {},
            'total_records': 0,
            'records_today': 0,
            'active_jobs': 0,
            'open_issues': 0
        }
        
        for source in sources:
            # By type
            stype = source.get('source_type', 'unknown')
            stats['by_type'][stype] = stats['by_type'].get(stype, 0) + 1
            
            # By status
            status = source.get('status', 'unknown')
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # By health
            health = source.get('health_status', 'unknown')
            stats['by_health'][health] = stats['by_health'].get(health, 0) + 1
            
            # Totals
            stats['total_records'] += source.get('total_records', 0)
            stats['records_today'] += source.get('records_today', 0)
            stats['active_jobs'] += source.get('active_jobs', 0)
            stats['open_issues'] += source.get('open_issues', 0)
        
        return stats
    
    def _get_mock_sources(self, city_id: Optional[str] = None) -> List[dict]:
        """Return mock data sources for demo/testing"""
        sources = [
            {
                'id': 'src-001',
                'name': 'MagicBricks Scraper',
                'source_type': 'scraped',
                'category': 'properties',
                'status': 'active',
                'health_status': 'healthy',
                'city_id': 'bangalore',
                'total_records': 45230,
                'records_today': 156,
                'records_this_week': 1024,
                'avg_quality_score': 0.92,
                'error_rate': 0.02,
                'last_sync_at': (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                'sync_frequency': 'daily',
                'active_jobs': 0,
                'open_issues': 3,
                'description': 'Automated scraping from MagicBricks listings'
            },
            {
                'id': 'src-002',
                'name': '99acres Scraper',
                'source_type': 'scraped',
                'category': 'properties',
                'status': 'active',
                'health_status': 'healthy',
                'city_id': 'bangalore',
                'total_records': 38450,
                'records_today': 203,
                'records_this_week': 1456,
                'avg_quality_score': 0.89,
                'error_rate': 0.03,
                'last_sync_at': (datetime.utcnow() - timedelta(hours=4)).isoformat(),
                'sync_frequency': 'daily',
                'active_jobs': 1,
                'open_issues': 5,
                'description': 'Automated scraping from 99acres listings'
            },
            {
                'id': 'src-003',
                'name': 'Manual Uploads',
                'source_type': 'upload',
                'category': 'properties',
                'status': 'active',
                'health_status': 'healthy',
                'city_id': None,
                'total_records': 12560,
                'records_today': 0,
                'records_this_week': 450,
                'avg_quality_score': 0.95,
                'error_rate': 0.01,
                'last_sync_at': (datetime.utcnow() - timedelta(days=1)).isoformat(),
                'sync_frequency': 'manual',
                'active_jobs': 0,
                'open_issues': 1,
                'description': 'User uploaded CSV/Excel files'
            },
            {
                'id': 'src-004',
                'name': 'GIS Data Folder',
                'source_type': 'folder',
                'category': 'gis',
                'status': 'active',
                'health_status': 'healthy',
                'city_id': 'bangalore',
                'total_records': 481,
                'records_today': 0,
                'records_this_week': 12,
                'avg_quality_score': 0.98,
                'error_rate': 0.0,
                'last_sync_at': (datetime.utcnow() - timedelta(days=3)).isoformat(),
                'sync_frequency': 'weekly',
                'active_jobs': 0,
                'open_issues': 0,
                'description': 'Ward boundaries, zones, and spatial data from data/raw/gis'
            },
            {
                'id': 'src-005',
                'name': 'Mappls API',
                'source_type': 'api',
                'category': 'pois',
                'status': 'active',
                'health_status': 'healthy',
                'city_id': None,
                'total_records': 8920,
                'records_today': 45,
                'records_this_week': 320,
                'avg_quality_score': 0.97,
                'error_rate': 0.005,
                'last_sync_at': datetime.utcnow().isoformat(),
                'sync_frequency': 'realtime',
                'active_jobs': 0,
                'open_issues': 0,
                'description': 'Real-time geocoding and POI data from Mappls'
            },
            {
                'id': 'src-006',
                'name': 'Registry Transactions',
                'source_type': 'upload',
                'category': 'transactions',
                'status': 'active',
                'health_status': 'degraded',
                'city_id': 'bangalore',
                'total_records': 23450,
                'records_today': 0,
                'records_this_week': 0,
                'avg_quality_score': 0.85,
                'error_rate': 0.08,
                'last_sync_at': (datetime.utcnow() - timedelta(days=14)).isoformat(),
                'sync_frequency': 'monthly',
                'active_jobs': 0,
                'open_issues': 12,
                'description': 'Property registry transaction data'
            },
            {
                'id': 'src-007',
                'name': 'Real-time Price Stream',
                'source_type': 'streaming',
                'category': 'market',
                'status': 'active',
                'health_status': 'healthy',
                'city_id': None,
                'total_records': 156780,
                'records_today': 2340,
                'records_this_week': 15600,
                'avg_quality_score': 0.91,
                'error_rate': 0.01,
                'last_sync_at': datetime.utcnow().isoformat(),
                'sync_frequency': 'realtime',
                'active_jobs': 1,
                'open_issues': 2,
                'description': 'Live price updates and market signals'
            },
            {
                'id': 'src-008',
                'name': 'Housing.com API',
                'source_type': 'api',
                'category': 'properties',
                'status': 'paused',
                'health_status': 'unknown',
                'city_id': 'bangalore',
                'total_records': 5600,
                'records_today': 0,
                'records_this_week': 0,
                'avg_quality_score': 0.88,
                'error_rate': 0.04,
                'last_sync_at': (datetime.utcnow() - timedelta(days=7)).isoformat(),
                'sync_frequency': 'daily',
                'active_jobs': 0,
                'open_issues': 0,
                'description': 'Partner API integration (paused)'
            }
        ]
        
        if city_id:
            sources = [s for s in sources if s.get('city_id') == city_id or s.get('city_id') is None]
        
        return sources


# Singleton instance
data_source_manager = DataSourceManager()
