"""
Folder Watcher - Monitors folders for new data files
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4
from pathlib import Path

logger = logging.getLogger(__name__)


class FolderWatcher:
    """Monitors folders for new data files to ingest"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self._watchers: Dict[str, dict] = {}
        self._discovered_files: Dict[str, List[dict]] = {}
    
    async def create_watcher(
        self,
        source_id: str,
        watch_path: str,
        file_pattern: str = "*",
        recursive: bool = False,
        auto_process: bool = True,
        process_action: str = "ingest"
    ) -> dict:
        """Create a new folder watcher"""
        watcher = {
            'id': str(uuid4()),
            'source_id': source_id,
            'watch_path': watch_path,
            'file_pattern': file_pattern,
            'recursive': recursive,
            'status': 'active',
            'auto_process': auto_process,
            'process_action': process_action,
            'last_scan_at': None,
            'files_discovered': 0,
            'files_processed': 0,
            'files_pending': 0,
            'files_failed': 0,
            'created_at': datetime.utcnow().isoformat()
        }
        
        self._watchers[watcher['id']] = watcher
        self._discovered_files[watcher['id']] = []
        
        logger.info(f"Created folder watcher: {watcher['id']} for {watch_path}")
        return watcher
    
    async def scan(self, watcher_id: str) -> dict:
        """Scan folder for new files"""
        watcher = self._watchers.get(watcher_id)
        if not watcher:
            raise ValueError(f"Watcher not found: {watcher_id}")
        
        watch_path = Path(watcher['watch_path'])
        if not watch_path.exists():
            logger.warning(f"Watch path does not exist: {watch_path}")
            return {'new_files': 0, 'error': 'Path does not exist'}
        
        pattern = watcher['file_pattern']
        recursive = watcher['recursive']
        
        # Find files
        if recursive:
            files = list(watch_path.rglob(pattern))
        else:
            files = list(watch_path.glob(pattern))
        
        # Filter to only files
        files = [f for f in files if f.is_file()]
        
        # Track new files
        existing_paths = {f['path'] for f in self._discovered_files.get(watcher_id, [])}
        new_files = []
        
        for file_path in files:
            path_str = str(file_path)
            if path_str not in existing_paths:
                file_info = {
                    'path': path_str,
                    'name': file_path.name,
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    'status': 'pending',
                    'discovered_at': datetime.utcnow().isoformat()
                }
                new_files.append(file_info)
                self._discovered_files[watcher_id].append(file_info)
        
        # Update watcher stats
        watcher['last_scan_at'] = datetime.utcnow().isoformat()
        watcher['files_discovered'] = len(self._discovered_files[watcher_id])
        watcher['files_pending'] = sum(1 for f in self._discovered_files[watcher_id] if f['status'] == 'pending')
        
        logger.info(f"Scanned {watcher_id}: found {len(new_files)} new files")
        return {
            'watcher_id': watcher_id,
            'new_files': len(new_files),
            'total_files': len(files),
            'files': new_files
        }
    
    async def process_pending(self, watcher_id: str) -> dict:
        """Process pending files for a watcher"""
        watcher = self._watchers.get(watcher_id)
        if not watcher:
            raise ValueError(f"Watcher not found: {watcher_id}")
        
        files = self._discovered_files.get(watcher_id, [])
        pending = [f for f in files if f['status'] == 'pending']
        
        processed = 0
        failed = 0
        
        for file_info in pending:
            try:
                # In real implementation, this would ingest the file
                file_info['status'] = 'processed'
                file_info['processed_at'] = datetime.utcnow().isoformat()
                processed += 1
            except Exception as e:
                file_info['status'] = 'failed'
                file_info['error'] = str(e)
                failed += 1
        
        watcher['files_processed'] += processed
        watcher['files_failed'] += failed
        watcher['files_pending'] = sum(1 for f in files if f['status'] == 'pending')
        
        logger.info(f"Processed files for {watcher_id}: {processed} success, {failed} failed")
        return {
            'processed': processed,
            'failed': failed,
            'remaining': watcher['files_pending']
        }
    
    async def get_watcher(self, watcher_id: str) -> Optional[dict]:
        """Get watcher details"""
        return self._watchers.get(watcher_id)
    
    async def get_watchers(self, source_id: str = None, status: str = None) -> List[dict]:
        """Get watchers with optional filters"""
        watchers = list(self._watchers.values())
        
        if source_id:
            watchers = [w for w in watchers if w['source_id'] == source_id]
        if status:
            watchers = [w for w in watchers if w['status'] == status]
        
        # Add mock watchers for demo
        if not watchers:
            watchers = self._get_mock_watchers(source_id, status)
        
        return watchers
    
    async def get_files(self, watcher_id: str, status: str = None) -> List[dict]:
        """Get files discovered by a watcher"""
        files = self._discovered_files.get(watcher_id, [])
        
        if status:
            files = [f for f in files if f['status'] == status]
        
        return files
    
    async def pause_watcher(self, watcher_id: str) -> dict:
        """Pause a watcher"""
        watcher = self._watchers.get(watcher_id)
        if not watcher:
            raise ValueError(f"Watcher not found: {watcher_id}")
        
        watcher['status'] = 'paused'
        logger.info(f"Paused watcher: {watcher_id}")
        return watcher
    
    async def resume_watcher(self, watcher_id: str) -> dict:
        """Resume a paused watcher"""
        watcher = self._watchers.get(watcher_id)
        if not watcher:
            raise ValueError(f"Watcher not found: {watcher_id}")
        
        watcher['status'] = 'active'
        logger.info(f"Resumed watcher: {watcher_id}")
        return watcher
    
    async def delete_watcher(self, watcher_id: str) -> bool:
        """Delete a watcher"""
        if watcher_id in self._watchers:
            del self._watchers[watcher_id]
            if watcher_id in self._discovered_files:
                del self._discovered_files[watcher_id]
            logger.info(f"Deleted watcher: {watcher_id}")
            return True
        return False
    
    def _get_mock_watchers(self, source_id: str = None, status: str = None) -> List[dict]:
        """Return mock watchers for demo"""
        now = datetime.utcnow()
        watchers = [
            {
                'id': 'watch-001',
                'source_id': 'src-004',
                'watch_path': 'data/raw/gis',
                'file_pattern': '*.geojson',
                'recursive': True,
                'status': 'active',
                'auto_process': True,
                'last_scan_at': (now - timedelta(hours=1)).isoformat(),
                'files_discovered': 481,
                'files_processed': 469,
                'files_pending': 12,
                'files_failed': 0
            },
            {
                'id': 'watch-002',
                'source_id': 'src-003',
                'watch_path': 'data/uploads/properties',
                'file_pattern': '*.csv',
                'recursive': False,
                'status': 'active',
                'auto_process': False,
                'last_scan_at': (now - timedelta(minutes=30)).isoformat(),
                'files_discovered': 52,
                'files_processed': 50,
                'files_pending': 2,
                'files_failed': 0
            },
            {
                'id': 'watch-003',
                'source_id': 'src-004',
                'watch_path': 'data/raw/external',
                'file_pattern': '*',
                'recursive': True,
                'status': 'active',
                'auto_process': True,
                'last_scan_at': (now - timedelta(hours=6)).isoformat(),
                'files_discovered': 40,
                'files_processed': 38,
                'files_pending': 0,
                'files_failed': 2
            }
        ]
        
        if source_id:
            watchers = [w for w in watchers if w['source_id'] == source_id]
        if status:
            watchers = [w for w in watchers if w['status'] == status]
        
        return watchers


# Singleton instance
folder_watcher = FolderWatcher()
