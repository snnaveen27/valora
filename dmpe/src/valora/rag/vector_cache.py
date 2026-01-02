"""
Persistent vector cache for Pinecone RAG.
- Stores embeddings locally to avoid reprocessing
- Tracks which vectors are already in Pinecone
- Supports incremental updates
"""

import os
import json
import hashlib
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import logging

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class VectorCache:
    """Manages persistent cache of embeddings and Pinecone sync status."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent.parent.parent.parent / ".vector_cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.embeddings_file = self.cache_dir / "embeddings.pkl"
        self.metadata_file = self.cache_dir / "metadata.json"
        self.pinecone_sync_file = self.cache_dir / "pinecone_sync.json"
        
        self._embeddings_cache: Dict[str, np.ndarray] = {}
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._pinecone_sync: Dict[str, str] = {}
        
        self._load_cache()
    
    def _load_cache(self):
        """Load existing cache from disk."""
        try:
            if self.embeddings_file.exists():
                with open(self.embeddings_file, 'rb') as f:
                    self._embeddings_cache = pickle.load(f)
                logger.info(f"Loaded {len(self._embeddings_cache)} embeddings from cache")
        except Exception as e:
            logger.warning(f"Failed to load embeddings cache: {e}")
            self._embeddings_cache = {}
        
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    self._metadata_cache = json.load(f)
                logger.info(f"Loaded {len(self._metadata_cache)} metadata records from cache")
        except Exception as e:
            logger.warning(f"Failed to load metadata cache: {e}")
            self._metadata_cache = {}
        
        try:
            if self.pinecone_sync_file.exists():
                with open(self.pinecone_sync_file, 'r') as f:
                    self._pinecone_sync = json.load(f)
                logger.info(f"Loaded {len(self._pinecone_sync)} Pinecone sync records")
        except Exception as e:
            logger.warning(f"Failed to load Pinecone sync cache: {e}")
            self._pinecone_sync = {}
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            # Save embeddings
            with open(self.embeddings_file, 'wb') as f:
                pickle.dump(self._embeddings_cache, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            # Save metadata
            with open(self.metadata_file, 'w') as f:
                json.dump(self._metadata_cache, f, indent=2)
            
            # Save Pinecone sync status
            with open(self.pinecone_sync_file, 'w') as f:
                json.dump(self._pinecone_sync, f, indent=2)
            
            logger.info("Cache saved to disk")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _get_content_hash(self, text: str, metadata: Dict[str, Any]) -> str:
        """Generate hash for content to detect changes."""
        content = text + json.dumps(metadata, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_or_create_embedding(self, vector_id: str, text: str, metadata: Dict[str, Any], 
                               embedder: SentenceTransformer) -> np.ndarray:
        """Get embedding from cache or create and cache it."""
        content_hash = self._get_content_hash(text, metadata)
        
        # Check if we have a cached embedding with same content
        if vector_id in self._embeddings_cache:
            cached_hash = self._metadata_cache.get(vector_id, {}).get('_content_hash')
            if cached_hash == content_hash:
                return self._embeddings_cache[vector_id]
        
        # Create new embedding
        embedding = embedder.encode(text, normalize_embeddings=True)
        
        # Cache it
        self._embeddings_cache[vector_id] = embedding
        self._metadata_cache[vector_id] = {
            **metadata,
            '_content_hash': content_hash,
            '_created_at': pd.Timestamp.now().isoformat()
        }
        
        return embedding
    
    def needs_upload(self, vector_id: str, content_hash: str) -> bool:
        """Check if vector needs to be uploaded to Pinecone."""
        synced_hash = self._pinecone_sync.get(vector_id)
        return synced_hash != content_hash
    
    def mark_uploaded(self, vector_id: str, content_hash: str):
        """Mark vector as uploaded to Pinecone."""
        self._pinecone_sync[vector_id] = content_hash
    
    def get_pending_vectors(self) -> List[Tuple[str, np.ndarray, Dict[str, Any]]]:
        """Get all vectors that need to be uploaded to Pinecone."""
        pending = []
        for vector_id, embedding in self._embeddings_cache.items():
            metadata = self._metadata_cache.get(vector_id, {})
            content_hash = metadata.get('_content_hash')
            if content_hash and self.needs_upload(vector_id, content_hash):
                # Remove internal fields from metadata
                clean_metadata = {k: v for k, v in metadata.items() 
                                if not k.startswith('_')}
                pending.append((vector_id, embedding, clean_metadata))
        return pending
    
    def batch_get_or_create(self, items: List[Tuple[str, str, Dict[str, Any]]], 
                           embedder: SentenceTransformer, batch_size: int = 32) -> List[np.ndarray]:
        """Batch get or create embeddings."""
        embeddings = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_embeddings = []
            
            for vector_id, text, metadata in batch:
                emb = self.get_or_create_embedding(vector_id, text, metadata, embedder)
                batch_embeddings.append(emb)
            
            embeddings.extend(batch_embeddings)
            
            # Save cache periodically
            if i % (batch_size * 10) == 0:
                self._save_cache()
        
        self._save_cache()
        return embeddings
    
    def clear_cache(self):
        """Clear all cached data."""
        self._embeddings_cache.clear()
        self._metadata_cache.clear()
        self._pinecone_sync.clear()
        
        # Remove cache files
        for file in [self.embeddings_file, self.metadata_file, self.pinecone_sync_file]:
            if file.exists():
                file.unlink()
        
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cached_embeddings': len(self._embeddings_cache),
            'cached_metadata': len(self._metadata_cache),
            'synced_to_pinecone': len(self._pinecone_sync),
            'pending_upload': len(self.get_pending_vectors()),
            'cache_size_mb': sum(
                f.stat().st_size for f in self.cache_dir.glob('*')
                if f.is_file()
            ) / (1024 * 1024)
        }
