"""
Vector Compression & Optimization for Valora AI
Phase 5.2: Handle 1M+ vectors efficiently

Features:
- Product Quantization (PQ) for compression
- Dimensionality reduction (384 → 128)
- Hierarchical indexing (IVF)
- Batch processing for large datasets
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from pathlib import Path
import json
import time


class VectorOptimizer:
    """
    Optimizes FAISS indexes for large-scale vector search.
    Provides compression, dimensionality reduction, and hierarchical indexing.
    """
    
    def __init__(self, base_path: str = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            from config import config
            self.base_path = config.FAISS_DIR
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.faiss = None
        self._init_faiss()
    
    def _init_faiss(self):
        """Initialize FAISS library."""
        try:
            import faiss
            self.faiss = faiss
        except ImportError:
            print("[VectorOptimizer] FAISS not installed. Run: pip install faiss-cpu")
    
    def create_ivf_index(self, vectors: np.ndarray, nlist: int = 100, 
                         nprobe: int = 10) -> Optional[Any]:
        """
        Create IVF (Inverted File) index for faster search.
        
        IVF partitions the vector space into clusters (nlist).
        During search, only nprobe clusters are searched.
        
        Args:
            vectors: numpy array of shape (n_vectors, dimension)
            nlist: number of clusters (more = more accurate but slower to build)
            nprobe: number of clusters to search (more = more accurate but slower search)
            
        Returns:
            FAISS IVF index
        """
        if self.faiss is None:
            return None
        
        n, d = vectors.shape
        
        # Adjust nlist based on dataset size
        nlist = min(nlist, int(np.sqrt(n)))
        
        # Create quantizer (flat index for cluster centroids)
        quantizer = self.faiss.IndexFlatL2(d)
        
        # Create IVF index
        index = self.faiss.IndexIVFFlat(quantizer, d, nlist)
        
        # Train the index on the vectors
        index.train(vectors.astype('float32'))
        
        # Add vectors
        index.add(vectors.astype('float32'))
        
        # Set search parameters
        index.nprobe = nprobe
        
        return index
    
    def create_ivfpq_index(self, vectors: np.ndarray, nlist: int = 100,
                          m: int = 8, nbits: int = 8) -> Optional[Any]:
        """
        Create IVF + Product Quantization index for maximum compression.
        
        PQ divides vectors into m sub-vectors and quantizes each.
        This dramatically reduces memory while maintaining search quality.
        
        Args:
            vectors: numpy array of shape (n_vectors, dimension)
            nlist: number of IVF clusters
            m: number of sub-quantizers (dimension must be divisible by m)
            nbits: bits per sub-quantizer (typically 8)
            
        Returns:
            FAISS IVFPQ index
        """
        if self.faiss is None:
            return None
        
        n, d = vectors.shape
        
        # Ensure dimension is divisible by m
        if d % m != 0:
            # Pad or use a different m
            m = min(m, d)
            while d % m != 0:
                m -= 1
        
        nlist = min(nlist, int(np.sqrt(n)))
        
        # Create quantizer
        quantizer = self.faiss.IndexFlatL2(d)
        
        # Create IVFPQ index
        index = self.faiss.IndexIVFPQ(quantizer, d, nlist, m, nbits)
        
        # Train
        index.train(vectors.astype('float32'))
        
        # Add vectors
        index.add(vectors.astype('float32'))
        
        return index
    
    def reduce_dimensions(self, vectors: np.ndarray, target_dim: int = 128,
                         method: str = 'pca') -> Tuple[np.ndarray, Any]:
        """
        Reduce vector dimensions using PCA or random projection.
        
        Args:
            vectors: numpy array of shape (n_vectors, dimension)
            target_dim: target dimension (e.g., 384 → 128)
            method: 'pca' or 'random'
            
        Returns:
            (reduced_vectors, transformer) - transformer can be used for new vectors
        """
        n, d = vectors.shape
        
        if target_dim >= d:
            return vectors, None
        
        if method == 'pca':
            try:
                from sklearn.decomposition import PCA
                pca = PCA(n_components=target_dim)
                reduced = pca.fit_transform(vectors)
                return reduced, pca
            except ImportError:
                method = 'random'
        
        if method == 'random':
            # Random projection (faster but less accurate)
            np.random.seed(42)
            projection_matrix = np.random.randn(d, target_dim) / np.sqrt(target_dim)
            reduced = vectors @ projection_matrix
            return reduced, projection_matrix
        
        return vectors, None
    
    def create_hnsw_index(self, vectors: np.ndarray, M: int = 32,
                         efConstruction: int = 200) -> Optional[Any]:
        """
        Create HNSW (Hierarchical Navigable Small World) index.
        
        HNSW provides excellent search speed with good accuracy.
        Good for datasets where you need fast search but don't need compression.
        
        Args:
            vectors: numpy array of shape (n_vectors, dimension)
            M: number of connections per layer (higher = more accurate, more memory)
            efConstruction: construction time accuracy (higher = more accurate)
            
        Returns:
            FAISS HNSW index
        """
        if self.faiss is None:
            return None
        
        n, d = vectors.shape
        
        # Create HNSW index
        index = self.faiss.IndexHNSWFlat(d, M)
        index.hnsw.efConstruction = efConstruction
        
        # Add vectors
        index.add(vectors.astype('float32'))
        
        return index
    
    def optimize_existing_index(self, index_path: str, 
                                optimization: str = 'ivfpq') -> Dict[str, Any]:
        """
        Optimize an existing FAISS index file.
        
        Args:
            index_path: path to existing FAISS index
            optimization: 'ivf', 'ivfpq', 'hnsw', or 'reduce'
            
        Returns:
            Optimization results
        """
        if self.faiss is None:
            return {"error": "FAISS not available"}
        
        try:
            # Load existing index
            original_index = self.faiss.read_index(index_path)
            n = original_index.ntotal
            d = original_index.d
            
            # Extract vectors (works for flat indexes)
            if hasattr(original_index, 'reconstruct_n'):
                vectors = np.zeros((n, d), dtype='float32')
                for i in range(n):
                    vectors[i] = original_index.reconstruct(i)
            else:
                return {"error": "Cannot extract vectors from this index type"}
            
            # Apply optimization
            start_time = time.time()
            
            if optimization == 'ivf':
                new_index = self.create_ivf_index(vectors)
            elif optimization == 'ivfpq':
                new_index = self.create_ivfpq_index(vectors)
            elif optimization == 'hnsw':
                new_index = self.create_hnsw_index(vectors)
            elif optimization == 'reduce':
                reduced_vectors, _ = self.reduce_dimensions(vectors, target_dim=128)
                new_index = self.faiss.IndexFlatL2(128)
                new_index.add(reduced_vectors.astype('float32'))
            else:
                return {"error": f"Unknown optimization: {optimization}"}
            
            build_time = time.time() - start_time
            
            # Save optimized index
            optimized_path = index_path.replace('.faiss', f'_{optimization}.faiss')
            self.faiss.write_index(new_index, optimized_path)
            
            # Calculate compression ratio
            import os
            original_size = os.path.getsize(index_path)
            optimized_size = os.path.getsize(optimized_path)
            
            return {
                "original_vectors": n,
                "original_dimension": d,
                "optimization": optimization,
                "build_time_sec": round(build_time, 2),
                "original_size_mb": round(original_size / (1024 * 1024), 2),
                "optimized_size_mb": round(optimized_size / (1024 * 1024), 2),
                "compression_ratio": round(original_size / optimized_size, 2),
                "optimized_path": optimized_path
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def benchmark_index(self, index: Any, query_vectors: np.ndarray, 
                       k: int = 10, n_queries: int = 100) -> Dict[str, Any]:
        """
        Benchmark search performance of an index.
        
        Args:
            index: FAISS index to benchmark
            query_vectors: sample query vectors
            k: number of neighbors to retrieve
            n_queries: number of queries to run
            
        Returns:
            Benchmark results
        """
        if self.faiss is None or index is None:
            return {"error": "Index not available"}
        
        # Use subset of query vectors
        n_queries = min(n_queries, len(query_vectors))
        queries = query_vectors[:n_queries].astype('float32')
        
        # Warm up
        index.search(queries[:1], k)
        
        # Benchmark
        start_time = time.time()
        distances, indices = index.search(queries, k)
        total_time = time.time() - start_time
        
        return {
            "n_queries": n_queries,
            "k": k,
            "total_time_sec": round(total_time, 4),
            "avg_query_time_ms": round(total_time / n_queries * 1000, 3),
            "queries_per_second": round(n_queries / total_time, 1)
        }
    
    def get_optimization_recommendations(self, n_vectors: int, 
                                         dimension: int) -> Dict[str, Any]:
        """
        Get recommendations for index optimization based on dataset size.
        
        Args:
            n_vectors: number of vectors
            dimension: vector dimension
            
        Returns:
            Optimization recommendations
        """
        memory_flat = n_vectors * dimension * 4 / (1024 * 1024)  # MB
        
        recommendations = {
            "dataset_size": n_vectors,
            "dimension": dimension,
            "flat_index_memory_mb": round(memory_flat, 1),
            "recommendations": []
        }
        
        if n_vectors < 10000:
            recommendations["recommendations"].append({
                "type": "flat",
                "reason": "Small dataset - flat index is fast enough",
                "expected_memory_mb": round(memory_flat, 1)
            })
        
        if n_vectors >= 10000 and n_vectors < 100000:
            recommendations["recommendations"].append({
                "type": "ivf",
                "reason": "Medium dataset - IVF provides good speed/accuracy tradeoff",
                "nlist": int(np.sqrt(n_vectors)),
                "expected_memory_mb": round(memory_flat * 1.1, 1)
            })
        
        if n_vectors >= 100000:
            recommendations["recommendations"].append({
                "type": "ivfpq",
                "reason": "Large dataset - IVFPQ provides good compression",
                "nlist": int(np.sqrt(n_vectors)),
                "m": 8,
                "expected_memory_mb": round(memory_flat * 0.1, 1),
                "compression": "~10x"
            })
        
        if dimension > 256:
            recommendations["recommendations"].append({
                "type": "dimension_reduction",
                "reason": f"High dimension ({dimension}) - consider reducing to 128",
                "target_dim": 128,
                "expected_memory_reduction": f"{dimension / 128:.1f}x"
            })
        
        if n_vectors >= 50000:
            recommendations["recommendations"].append({
                "type": "hnsw",
                "reason": "Good for fast approximate search without compression",
                "M": 32,
                "expected_memory_mb": round(memory_flat * 1.5, 1)
            })
        
        return recommendations


# Singleton instance
_vector_optimizer = None


def get_vector_optimizer() -> VectorOptimizer:
    """Get or create vector optimizer singleton."""
    global _vector_optimizer
    if _vector_optimizer is None:
        _vector_optimizer = VectorOptimizer()
    return _vector_optimizer
