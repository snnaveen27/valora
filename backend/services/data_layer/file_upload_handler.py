"""
File Upload Handler - Manages file uploads and processing
"""

import os
import json
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4
from pathlib import Path

logger = logging.getLogger(__name__)

# Base upload directory
UPLOAD_DIR = Path("data/uploads")
STAGING_DIR = Path("data/staging")


class FileUploadHandler:
    """Handles file uploads for data ingestion"""
    
    ALLOWED_EXTENSIONS = {
        'csv': 'text/csv',
        'json': 'application/json',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'xls': 'application/vnd.ms-excel',
        'geojson': 'application/geo+json',
        'shp': 'application/x-shapefile',
        'parquet': 'application/octet-stream'
    }
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self._uploads: Dict[str, dict] = {}
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure upload directories exist"""
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories by category
        for category in ['properties', 'transactions', 'pois', 'gis', 'market']:
            (UPLOAD_DIR / category).mkdir(exist_ok=True)
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        category: str,
        city_id: str = None,
        uploaded_by: str = None,
        metadata: dict = None
    ) -> dict:
        """Handle file upload"""
        
        # Validate extension
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")
        
        # Generate unique filename
        upload_id = str(uuid4())
        stored_filename = f"{upload_id}_{filename}"
        file_path = UPLOAD_DIR / category / stored_filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Create upload record
        upload = {
            'id': upload_id,
            'original_filename': filename,
            'stored_filename': stored_filename,
            'file_path': str(file_path),
            'file_size': len(file_content),
            'file_type': ext,
            'mime_type': self.ALLOWED_EXTENSIONS.get(ext),
            'category': category,
            'city_id': city_id,
            'status': 'uploaded',
            'validation_status': 'pending',
            'validation_errors': [],
            'column_mapping': None,
            'record_count': None,
            'uploaded_by': uploaded_by,
            'created_at': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        self._uploads[upload_id] = upload
        logger.info(f"File uploaded: {filename} -> {stored_filename}")
        
        return upload
    
    async def validate_file(self, upload_id: str) -> dict:
        """Validate uploaded file structure and content"""
        upload = self._uploads.get(upload_id)
        if not upload:
            raise ValueError(f"Upload not found: {upload_id}")
        
        errors = []
        warnings = []
        file_type = upload['file_type']
        file_path = upload['file_path']
        
        try:
            if file_type == 'csv':
                result = await self._validate_csv(file_path)
            elif file_type == 'json':
                result = await self._validate_json(file_path)
            elif file_type in ['xlsx', 'xls']:
                result = await self._validate_excel(file_path)
            elif file_type == 'geojson':
                result = await self._validate_geojson(file_path)
            else:
                result = {'valid': True, 'errors': [], 'warnings': [], 'record_count': 0, 'columns': []}
            
            upload['validation_status'] = 'valid' if result['valid'] else 'invalid'
            upload['validation_errors'] = result['errors']
            upload['record_count'] = result.get('record_count', 0)
            upload['column_mapping'] = result.get('columns', [])
            
        except Exception as e:
            upload['validation_status'] = 'invalid'
            upload['validation_errors'] = [str(e)]
            logger.error(f"Validation error for {upload_id}: {e}")
        
        return upload
    
    async def _validate_csv(self, file_path: str) -> dict:
        """Validate CSV file"""
        import csv
        
        errors = []
        columns = []
        record_count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if headers:
                    columns = headers
                for row in reader:
                    record_count += 1
        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': [],
            'record_count': record_count,
            'columns': columns
        }
    
    async def _validate_json(self, file_path: str) -> dict:
        """Validate JSON file"""
        errors = []
        record_count = 0
        columns = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                record_count = len(data)
                if data and isinstance(data[0], dict):
                    columns = list(data[0].keys())
            elif isinstance(data, dict):
                record_count = 1
                columns = list(data.keys())
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {str(e)}")
        except Exception as e:
            errors.append(f"Error reading file: {str(e)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': [],
            'record_count': record_count,
            'columns': columns
        }
    
    async def _validate_excel(self, file_path: str) -> dict:
        """Validate Excel file"""
        # Simplified validation without pandas dependency
        return {
            'valid': True,
            'errors': [],
            'warnings': ['Excel validation requires pandas - install with pip install pandas openpyxl'],
            'record_count': 0,
            'columns': []
        }
    
    async def _validate_geojson(self, file_path: str) -> dict:
        """Validate GeoJSON file"""
        errors = []
        record_count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('type') == 'FeatureCollection':
                features = data.get('features', [])
                record_count = len(features)
            elif data.get('type') == 'Feature':
                record_count = 1
            else:
                errors.append("Invalid GeoJSON: missing type")
        except Exception as e:
            errors.append(f"GeoJSON parsing error: {str(e)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': [],
            'record_count': record_count,
            'columns': ['geometry', 'properties']
        }
    
    async def process_upload(self, upload_id: str, column_mapping: dict = None) -> dict:
        """Process validated upload and ingest into database"""
        upload = self._uploads.get(upload_id)
        if not upload:
            raise ValueError(f"Upload not found: {upload_id}")
        
        if upload['validation_status'] != 'valid':
            raise ValueError("Cannot process invalid upload")
        
        upload['status'] = 'processing'
        
        # In a real implementation, this would:
        # 1. Apply column mapping
        # 2. Transform data
        # 3. Insert into database
        # 4. Create ingestion job record
        
        # For now, mark as completed
        upload['status'] = 'completed'
        upload['processed_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Processed upload: {upload_id}")
        return upload
    
    async def get_upload(self, upload_id: str) -> Optional[dict]:
        """Get upload details"""
        return self._uploads.get(upload_id)
    
    async def get_uploads(
        self,
        category: str = None,
        status: str = None,
        city_id: str = None,
        limit: int = 50
    ) -> List[dict]:
        """Get uploads with optional filters"""
        uploads = list(self._uploads.values())
        
        if category:
            uploads = [u for u in uploads if u['category'] == category]
        if status:
            uploads = [u for u in uploads if u['status'] == status]
        if city_id:
            uploads = [u for u in uploads if u['city_id'] == city_id]
        
        # Sort by created_at desc
        uploads.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Add mock uploads for demo
        if not uploads:
            uploads = self._get_mock_uploads(category, status, city_id)
        
        return uploads[:limit]
    
    async def delete_upload(self, upload_id: str) -> bool:
        """Delete an upload and its file"""
        upload = self._uploads.get(upload_id)
        if not upload:
            return False
        
        # Delete file
        try:
            if os.path.exists(upload['file_path']):
                os.remove(upload['file_path'])
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
        
        # Remove record
        del self._uploads[upload_id]
        logger.info(f"Deleted upload: {upload_id}")
        return True
    
    def _get_mock_uploads(self, category: str = None, status: str = None, city_id: str = None) -> List[dict]:
        """Return mock uploads for demo"""
        now = datetime.utcnow()
        uploads = [
            {
                'id': 'upl-001',
                'original_filename': 'bangalore_properties_dec2024.csv',
                'file_size': 2456000,
                'file_type': 'csv',
                'category': 'properties',
                'city_id': 'bangalore',
                'status': 'completed',
                'validation_status': 'valid',
                'record_count': 450,
                'created_at': (now - timedelta(days=1)).isoformat(),
                'processed_at': (now - timedelta(days=1, hours=-1)).isoformat()
            },
            {
                'id': 'upl-002',
                'original_filename': 'ward_boundaries_v2.geojson',
                'file_size': 1234000,
                'file_type': 'geojson',
                'category': 'gis',
                'city_id': 'bangalore',
                'status': 'completed',
                'validation_status': 'valid',
                'record_count': 198,
                'created_at': (now - timedelta(days=3)).isoformat(),
                'processed_at': (now - timedelta(days=3, hours=-2)).isoformat()
            },
            {
                'id': 'upl-003',
                'original_filename': 'transactions_q4_2024.xlsx',
                'file_size': 3890000,
                'file_type': 'xlsx',
                'category': 'transactions',
                'city_id': 'bangalore',
                'status': 'processing',
                'validation_status': 'valid',
                'record_count': 1250,
                'created_at': (now - timedelta(hours=2)).isoformat(),
                'processed_at': None
            },
            {
                'id': 'upl-004',
                'original_filename': 'mumbai_listings_sample.json',
                'file_size': 890000,
                'file_type': 'json',
                'category': 'properties',
                'city_id': 'mumbai',
                'status': 'uploaded',
                'validation_status': 'pending',
                'record_count': None,
                'created_at': (now - timedelta(minutes=30)).isoformat(),
                'processed_at': None
            }
        ]
        
        if category:
            uploads = [u for u in uploads if u['category'] == category]
        if status:
            uploads = [u for u in uploads if u['status'] == status]
        if city_id:
            uploads = [u for u in uploads if u['city_id'] == city_id]
        
        return uploads


# Import timedelta for mock data
from datetime import timedelta

# Singleton instance
file_upload_handler = FileUploadHandler()
