"""
Cloud Storage Service - Cloudflare R2 Integration
Handles file uploads, downloads, and management for property images, ML models, and documents.
"""

import os
import logging
from typing import Optional, BinaryIO
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import boto3 for R2
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not installed. Install with: pip install boto3")


class StorageService:
    """
    Cloud storage service using Cloudflare R2 (S3-compatible)
    Falls back to local filesystem if R2 not configured.
    """
    
    def __init__(self):
        self.s3_client = None
        self.bucket_name = os.getenv('R2_BUCKET_NAME', 'valora-storage')
        self.use_local_storage = False
        self.local_storage_path = Path('data/storage')
        
        # Try to initialize R2 client
        if BOTO3_AVAILABLE:
            r2_endpoint = os.getenv('R2_ENDPOINT')
            r2_access_key = os.getenv('R2_ACCESS_KEY_ID')
            r2_secret_key = os.getenv('R2_SECRET_ACCESS_KEY')
            
            if r2_endpoint and r2_access_key and r2_secret_key:
                try:
                    self.s3_client = boto3.client(
                        's3',
                        endpoint_url=r2_endpoint,
                        aws_access_key_id=r2_access_key,
                        aws_secret_access_key=r2_secret_key,
                        region_name='auto'  # Cloudflare R2 uses 'auto'
                    )
                    # Test connection
                    self.s3_client.head_bucket(Bucket=self.bucket_name)
                    logger.info(f"✅ Connected to Cloudflare R2 bucket: {self.bucket_name}")
                    return
                except Exception as e:
                    logger.warning(f"R2 connection failed: {str(e)}")
        
        # Fallback to local storage
        logger.warning("⚠️  Using local file storage (R2 unavailable)")
        self.use_local_storage = True
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
    
    def upload_file(self, file_path: str, object_key: str, folder: str = 'files/') -> Optional[str]:
        """
        Upload file to R2 or local storage
        
        Args:
            file_path: Path to local file
            object_key: Key/name for the object in storage
            folder: Folder prefix (photos/, models/, docs/, exports/)
        
        Returns:
            URL or path to uploaded file
        """
        try:
            full_key = f"{folder}{object_key}"
            
            if self.use_local_storage:
                # Local storage
                dest_path = self.local_storage_path / full_key
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                import shutil
                shutil.copy2(file_path, dest_path)
                logger.info(f"Uploaded to local storage: {dest_path}")
                return str(dest_path)
            
            if self.s3_client:
                # Upload to R2
                with open(file_path, 'rb') as f:
                    self.s3_client.upload_fileobj(f, self.bucket_name, full_key)
                
                # Generate public URL (if configured)
                public_url = os.getenv('R2_PUBLIC_URL')
                if public_url:
                    url = f"{public_url}/{full_key}"
                else:
                    url = f"r2://{self.bucket_name}/{full_key}"
                
                logger.info(f"Uploaded to R2: {full_key}")
                return url
            
            return None
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            return None
    
    def download_file(self, object_key: str, dest_path: str, folder: str = 'files/') -> bool:
        """Download file from R2 or local storage"""
        try:
            full_key = f"{folder}{object_key}"
            
            if self.use_local_storage:
                # Local storage
                source_path = self.local_storage_path / full_key
                if source_path.exists():
                    import shutil
                    shutil.copy2(source_path, dest_path)
                    return True
                return False
            
            if self.s3_client:
                # Download from R2
                self.s3_client.download_file(self.bucket_name, full_key, dest_path)
                logger.info(f"Downloaded from R2: {full_key}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            return False
    
    def delete_file(self, object_key: str, folder: str = 'files/') -> bool:
        """Delete file from R2 or local storage"""
        try:
            full_key = f"{folder}{object_key}"
            
            if self.use_local_storage:
                # Local storage
                file_path = self.local_storage_path / full_key
                if file_path.exists():
                    file_path.unlink()
                    return True
                return False
            
            if self.s3_client:
                # Delete from R2
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=full_key)
                logger.info(f"Deleted from R2: {full_key}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Delete failed: {str(e)}")
            return False
    
    def list_files(self, folder: str = 'files/', max_keys: int = 100) -> list:
        """List files in a folder"""
        try:
            if self.use_local_storage:
                # Local storage
                folder_path = self.local_storage_path / folder
                if not folder_path.exists():
                    return []
                
                files = []
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(self.local_storage_path)
                        files.append(str(rel_path))
                
                return files[:max_keys]
            
            if self.s3_client:
                # List from R2
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=folder,
                    MaxKeys=max_keys
                )
                
                if 'Contents' in response:
                    return [obj['Key'] for obj in response['Contents']]
                
                return []
            
            return []
        except Exception as e:
            logger.error(f"List failed: {str(e)}")
            return []
    
    def get_storage_stats(self) -> dict:
        """Get storage statistics"""
        try:
            if self.use_local_storage:
                # Local storage stats
                total_size = sum(f.stat().st_size for f in self.local_storage_path.rglob('*') if f.is_file())
                file_count = sum(1 for f in self.local_storage_path.rglob('*') if f.is_file())
                
                return {
                    'type': 'local',
                    'total_size_bytes': total_size,
                    'total_size_mb': round(total_size / (1024 * 1024), 2),
                    'file_count': file_count
                }
            
            if self.s3_client:
                # R2 stats (approximate)
                response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
                
                total_size = 0
                file_count = 0
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        total_size += obj.get('Size', 0)
                        file_count += 1
                
                return {
                    'type': 'r2',
                    'bucket': self.bucket_name,
                    'total_size_bytes': total_size,
                    'total_size_mb': round(total_size / (1024 * 1024), 2),
                    'file_count': file_count
                }
            
            return {'type': 'none', 'status': 'unavailable'}
        except Exception as e:
            logger.error(f"Stats error: {str(e)}")
            return {'type': 'error', 'error': str(e)}


# Global storage instance
storage = StorageService()


# Convenience functions
def upload_property_image(image_path: str, property_id: str) -> Optional[str]:
    """Upload property image to R2/local storage"""
    filename = Path(image_path).name
    object_key = f"{property_id}/{filename}"
    return storage.upload_file(image_path, object_key, folder='photos/')


def upload_ml_model(model_path: str, model_name: str) -> Optional[str]:
    """Upload ML model to R2/local storage"""
    return storage.upload_file(model_path, model_name, folder='models/')


def upload_document(doc_path: str, doc_name: str) -> Optional[str]:
    """Upload document to R2/local storage"""
    return storage.upload_file(doc_path, doc_name, folder='docs/')
