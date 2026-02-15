"""
FAISS Local Vector Store
Offline vector search as fallback to Pinecone
"""

import os
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("[WARNING] FAISS not installed. Install: pip install faiss-cpu")


@dataclass
class LocalSearchResult:
    """Search result from FAISS."""
    id: str
    score: float
    text: str
    metadata: Dict[str, Any]
    lat: Optional[float] = None
    lng: Optional[float] = None


class LocalVectorStore:
    """
    FAISS-based local vector store for offline operation.
    Serves as fallback when Pinecone is unavailable.
    """
    
    def __init__(self, data_dir: Path, dimension: int = 384):
        self.data_dir = Path(data_dir)
        self.dimension = dimension
        self.store_dir = self.data_dir
        self.store_dir.mkdir(exist_ok=True)
        
        # Separate indexes for each namespace
        self.indexes = {}
        self.metadata_stores = {}
        self.id_maps = {}  # Maps index position to vector ID
        
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS not available. Install: pip install faiss-cpu")
        
        print(f"[INFO] LocalVectorStore initialized at {self.store_dir}")
    
    def _get_index_path(self, namespace: str) -> Path:
        """Get file path for namespace index."""
        return self.store_dir / f"{namespace}.faiss"
    
    def _get_metadata_path(self, namespace: str) -> Path:
        """Get file path for namespace metadata."""
        return self.store_dir / f"{namespace}_metadata.pkl"
    
    def _get_idmap_path(self, namespace: str) -> Path:
        """Get file path for namespace ID map."""
        return self.store_dir / f"{namespace}_idmap.pkl"
    
    def create_index(self, namespace: str = "default"):
        """Create a new FAISS index for a namespace."""
        # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
        index = faiss.IndexFlatIP(self.dimension)
        self.indexes[namespace] = index
        self.metadata_stores[namespace] = []
        self.id_maps[namespace] = []
        print(f"[OK] Created FAISS index for namespace: {namespace}")
        return index
    
    def has_vector(self, vector_id: str, namespace: str = "default") -> bool:
        """Check if a vector ID exists in the namespace."""
        if namespace not in self.id_maps:
            return False
        return vector_id in self.id_maps[namespace]
    
    def get_existing_ids(self, namespace: str = "default") -> set:
        """Get all existing vector IDs in a namespace."""
        if namespace not in self.id_maps:
            return set()
        return set(self.id_maps[namespace])
    
    def add_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str = "default",
        skip_duplicates: bool = True
    ) -> int:
        """
        Add vectors to the index.
        
        Args:
            vectors: List of dicts with 'id', 'values', 'metadata'
            namespace: Namespace to add to
            skip_duplicates: If True, skip vectors with existing IDs
            
        Returns:
            Number of vectors actually added
        """
        if namespace not in self.indexes:
            self.create_index(namespace)
        
        index = self.indexes[namespace]
        existing_ids = self.get_existing_ids(namespace) if skip_duplicates else set()
        
        # Extract embeddings and metadata, skipping duplicates
        embeddings = []
        ids = []
        metadata = []
        skipped = 0
        
        for vec in vectors:
            vec_id = vec['id']
            if skip_duplicates and vec_id in existing_ids:
                skipped += 1
                continue
            embeddings.append(vec['values'])
            ids.append(vec_id)
            metadata.append(vec.get('metadata', {}))
        
        # Return early if nothing to add
        if not embeddings:
            if skipped > 0:
                print(f"[INFO] Skipped {skipped} duplicate vectors (no new vectors to add)")
            return 0
        
        # Convert to numpy array and normalize for cosine similarity
        embeddings_np = np.array(embeddings).astype('float32')
        faiss.normalize_L2(embeddings_np)
        
        # Add to index
        index.add(embeddings_np)
        
        # Store metadata and ID mapping
        self.metadata_stores[namespace].extend(metadata)
        self.id_maps[namespace].extend(ids)
        
        added = len(ids)
        msg = f"[OK] Added {added} vectors to namespace: {namespace}"
        if skipped > 0:
            msg += f" (skipped {skipped} duplicates)"
        print(msg)
        return added
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        namespace: str = "default",
        filter_dict: Optional[Dict] = None
    ) -> List[LocalSearchResult]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query embedding
            top_k: Number of results
            namespace: Namespace to search
            filter_dict: Metadata filters (applied post-search)
        """
        if namespace not in self.indexes:
            print(f"[WARNING] Namespace '{namespace}' not found")
            return []
        
        index = self.indexes[namespace]
        metadata_store = self.metadata_stores[namespace]
        id_map = self.id_maps[namespace]
        
        if index.ntotal == 0:
            print(f"[WARNING] No vectors in namespace '{namespace}'")
            return []
        
        # Normalize query vector
        query_np = np.array([query_vector]).astype('float32')
        faiss.normalize_L2(query_np)
        
        # Search (get more than top_k for filtering)
        search_k = min(top_k * 3, index.ntotal) if filter_dict else top_k
        scores, indices = index.search(query_np, search_k)
        
        # Build results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            
            metadata = metadata_store[idx]
            
            # Apply filters if provided
            if filter_dict and not self._matches_filter(metadata, filter_dict):
                continue
            
            results.append(LocalSearchResult(
                id=id_map[idx],
                score=float(score),
                text=metadata.get('text', ''),
                metadata=metadata,
                lat=metadata.get('lat'),
                lng=metadata.get('lng')
            ))
            
            if len(results) >= top_k:
                break
        
        return results
    
    def _matches_filter(self, metadata: Dict, filter_dict: Dict) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_dict.items():
            if key not in metadata:
                return False
            
            meta_val = metadata[key]
            
            # Handle different filter types
            if isinstance(value, dict):
                # Range filter: {"$gte": 3, "$lte": 5}
                if "$gte" in value and meta_val < value["$gte"]:
                    return False
                if "$lte" in value and meta_val > value["$lte"]:
                    return False
                if "$gt" in value and meta_val <= value["$gt"]:
                    return False
                if "$lt" in value and meta_val >= value["$lt"]:
                    return False
                if "$eq" in value and meta_val != value["$eq"]:
                    return False
            else:
                # Exact match
                if meta_val != value:
                    return False
        
        return True
    
    def save(self, namespace: str = "default"):
        """Save index and metadata to disk."""
        if namespace not in self.indexes:
            print(f"[WARNING] Namespace '{namespace}' not found")
            return False
        
        try:
            # Save FAISS index
            index_path = self._get_index_path(namespace)
            faiss.write_index(self.indexes[namespace], str(index_path))
            
            # Save metadata
            metadata_path = self._get_metadata_path(namespace)
            with open(metadata_path, 'wb') as f:
                pickle.dump(self.metadata_stores[namespace], f)
            
            # Save ID map
            idmap_path = self._get_idmap_path(namespace)
            with open(idmap_path, 'wb') as f:
                pickle.dump(self.id_maps[namespace], f)
            
            print(f"[OK] Saved namespace '{namespace}' to disk")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save namespace '{namespace}': {e}")
            return False
    
    def load(self, namespace: str = "default") -> bool:
        """Load index and metadata from disk."""
        index_path = self._get_index_path(namespace)
        metadata_path = self._get_metadata_path(namespace)
        idmap_path = self._get_idmap_path(namespace)
        
        if not index_path.exists():
            print(f"[INFO] No saved index for namespace '{namespace}'")
            return False
        
        try:
            # Load FAISS index
            self.indexes[namespace] = faiss.read_index(str(index_path))
            
            # Load metadata
            with open(metadata_path, 'rb') as f:
                self.metadata_stores[namespace] = pickle.load(f)
            
            # Load ID map
            with open(idmap_path, 'rb') as f:
                self.id_maps[namespace] = pickle.load(f)
            
            vector_count = self.indexes[namespace].ntotal
            print(f"[OK] Loaded namespace '{namespace}' with {vector_count:,} vectors")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to load namespace '{namespace}': {e}")
            return False
    
    def save_all(self):
        """Save all namespaces."""
        for namespace in self.indexes.keys():
            self.save(namespace)
    
    def load_all(self) -> int:
        """Load all available namespaces from disk."""
        count = 0
        for file_path in self.store_dir.glob("*.faiss"):
            namespace = file_path.stem
            if self.load(namespace):
                count += 1
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored vectors."""
        stats = {
            "total_vectors": 0,
            "namespaces": {}
        }
        
        for namespace, index in self.indexes.items():
            count = index.ntotal
            stats["total_vectors"] += count
            stats["namespaces"][namespace] = {
                "vector_count": count,
                "dimension": self.dimension
            }
        
        return stats
    
    def get_vector_count(self, namespace: str = "default") -> int:
        """Get vector count for a specific namespace."""
        if namespace not in self.indexes:
            # Try to load the namespace
            self.load(namespace)
        
        if namespace in self.indexes:
            return self.indexes[namespace].ntotal
        return 0
    
    def delete_namespace(self, namespace: str = "default"):
        """Delete a namespace and its files."""
        if namespace in self.indexes:
            del self.indexes[namespace]
            del self.metadata_stores[namespace]
            del self.id_maps[namespace]
        
        # Delete files
        for path in [
            self._get_index_path(namespace),
            self._get_metadata_path(namespace),
            self._get_idmap_path(namespace)
        ]:
            if path.exists():
                path.unlink()
        
        print(f"[OK] Deleted namespace: {namespace}")
    
    def clear_all_namespaces(self):
        """Clear all namespaces and delete all files."""
        # Clear in-memory data
        self.indexes.clear()
        self.metadata_stores.clear()
        self.id_maps.clear()
        
        # Delete all FAISS files
        for file_path in self.store_dir.glob("*.faiss"):
            file_path.unlink()
        for file_path in self.store_dir.glob("*.index"):
            file_path.unlink()
        for file_path in self.store_dir.glob("*_metadata.pkl"):
            file_path.unlink()
        for file_path in self.store_dir.glob("*_idmap.pkl"):
            file_path.unlink()
        for file_path in self.store_dir.glob("*_ids.json"):
            file_path.unlink()
        
        print(f"[OK] Cleared all FAISS namespaces")


# Singleton instance
_local_store: Optional[LocalVectorStore] = None


def get_local_store(data_dir: Optional[Path] = None) -> LocalVectorStore:
    """Get or create local vector store singleton."""
    global _local_store
    
    if _local_store is None:
        if data_dir is None:
            from config import config
            data_dir = config.FAISS_DIR
        
        _local_store = LocalVectorStore(data_dir)
        
        # Try to load existing indexes
        loaded = _local_store.load_all()
        if loaded > 0:
            print(f"[OK] Loaded {loaded} existing FAISS indexes")
    
    return _local_store
