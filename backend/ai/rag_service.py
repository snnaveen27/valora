"""
Valora AI - RAG Service (FAISS-only, offline-first)

Provides vector embeddings and semantic search for:
- Properties (real estate listings)
- POIs (points of interest)
- Places (neighborhoods, landmarks)
- Transport (metro, bus stops)

Uses local FAISS for vector storage and sentence-transformers for embeddings.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from threading import Lock

# Import caching
try:
    from search.query_cache import get_rag_cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    get_rag_cache = None

# Import FAISS fallback
try:
    from search.local_vector_store import get_local_store
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    get_local_store = None

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except (ImportError, Exception) as e:
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None
    print(f"[WARNING] sentence-transformers not available: {type(e).__name__}")


@dataclass
class SearchResult:
    id: str
    score: float
    text: str
    metadata: Dict[str, Any]
    lat: Optional[float] = None
    lng: Optional[float] = None


class RAGService:
    """
    RAG (Retrieval Augmented Generation) service for spatial data.
    Uses local FAISS for vector storage and sentence-transformers for embeddings.
    Production mode: FAISS only (offline-first).
    
    Features:
    - Namespace-based vector storage (properties, pois, places, transport)
    - Auto-indexing on first search (optional)
    - Health check for monitoring
    - Dynamic namespace discovery
    """
    
    # Default namespaces for real estate data
    DEFAULT_NAMESPACES = ["properties", "pois", "places", "transport"]
    
    def __init__(self, data_dir: Path, auto_index: bool = False):
        """
        Initialize RAG service.
        
        Args:
            data_dir: Directory for FAISS indexes
            auto_index: If True, automatically index from DB on first search if empty
        """
        self.data_dir = data_dir
        self.dimension = 384  # all-MiniLM-L6-v2 dimension
        self.auto_index = auto_index
        self._auto_indexed = False  # Track if auto-indexing has been done
        
        # Initialize embedding model (lazy loading)
        self.embedding_model = None
        self._model_loading = False
        self._model_lock = Lock()
        
        # Initialize cache
        self.cache = None
        if CACHE_AVAILABLE:
            try:
                self.cache = get_rag_cache()
                print("[OK] RAG caching enabled")
            except Exception as e:
                print(f"[INFO] RAG caching not available: {e}")
        
        # Initialize FAISS (primary vector store)
        self.local_store = None
        if FAISS_AVAILABLE:
            try:
                self.local_store = get_local_store(data_dir)
                print("[OK] FAISS vector store initialized (production mode)")
            except Exception as e:
                print(f"[ERROR] FAISS initialization failed: {e}")
    
    def _init_embedding_model(self, lazy: bool = True):
        """
        Initialize the embedding model.
        
        Args:
            lazy: If True, defer model loading until first use
        """
        if lazy:
            # Defer loading until first embedding request
            self.embedding_model = None
            return
            
        if EMBEDDINGS_AVAILABLE:
            try:
                # Use a lightweight but effective model
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                print("[OK] Loaded embedding model: all-MiniLM-L6-v2")
            except Exception as e:
                print(f"[WARNING]  Failed to load embedding model: {e}")
                self.embedding_model = None
        else:
            self.embedding_model = None
    
    def _ensure_embedding_model(self):
        """Ensure embedding model is loaded (lazy loading support)."""
        if self.embedding_model is not None:
            return True
            
        with self._model_lock:
            if self.embedding_model is not None:
                return True
            if self._model_loading:
                return False
                
            self._model_loading = True
            try:
                if EMBEDDINGS_AVAILABLE:
                    self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                    print("[OK] Lazy-loaded embedding model: all-MiniLM-L6-v2")
                    return True
                else:
                    print("[WARNING] sentence-transformers not available")
                    return False
            except Exception as e:
                print(f"[WARNING] Failed to load embedding model: {e}")
                return False
            finally:
                self._model_loading = False
    
    def _generate_id(self, text: str, prefix: str = "") -> str:
        """Generate a unique ID for a text."""
        hash_str = hashlib.md5(text.encode()).hexdigest()[:12]
        return f"{prefix}_{hash_str}" if prefix else hash_str
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        # Ensure model is loaded (lazy loading)
        if self.embedding_model is None:
            if not self._ensure_embedding_model():
                raise RuntimeError(
                    "Embedding model not available. Install backend requirements (sentence-transformers) "
                    "and restart the backend to enable RAG."
                )
        
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        return embeddings.astype(np.float32)
    
    def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self.embed([text])[0].tolist()
    
    def index_faiss_from_db(self, force_reindex: bool = False, batch_size: int = 1000) -> Dict[str, int]:
        """Build / refresh FAISS indexes from the local database (offline-first)."""
        if not self.local_store:
            raise RuntimeError("FAISS local store not available. Install faiss-cpu and restart backend.")

        try:
            from database.query_service import get_query_service
        except ImportError:
            from backend.database.query_service import get_query_service

        db = get_query_service()

        if force_reindex:
            self.local_store.clear_all_namespaces()

        def _add(namespace: str, vectors: List[Dict[str, Any]]) -> int:
            added = self.local_store.add_vectors(
                vectors,
                namespace=namespace,
                skip_duplicates=(not force_reindex),
            )
            self.local_store.save(namespace)
            return added

        results: Dict[str, int] = {"properties": 0, "pois": 0, "places": 0, "transport": 0}

        # -----------------
        # Properties
        # -----------------
        props = db.get_all_properties()
        vectors: List[Dict[str, Any]] = []
        for i, prop in enumerate(props):
            text_parts = [
                prop.get("title", ""),
                prop.get("description", ""),
                prop.get("address", ""),
                prop.get("locality", ""),
                prop.get("area_name", ""),
                f"{prop.get('bedrooms')} BHK" if prop.get("bedrooms") else "",
                prop.get("property_type", ""),
                prop.get("amenities", ""),
            ]
            text = " ".join([str(p) for p in text_parts if p]).strip()
            if not text or len(text) < 10:
                continue

            prop_id = str(prop.get("property_id") or prop.get("id") or f"prop_{i}")
            lat = float(prop.get("latitude") or 0.0)
            lng = float(prop.get("longitude") or 0.0)

            vectors.append(
                {
                    "id": prop_id,
                    "values": self.embed_single(text),
                    "metadata": {
                        "type": "property",
                        "text": str(text[:1000]),
                        "name": str(prop.get("title") or "")[:200],
                        "title": str(prop.get("title") or "")[:200],
                        "property_type": str(prop.get("property_type") or ""),
                        "listing_type": str(prop.get("listing_type") or ""),
                        "price": float(prop.get("price") or 0.0),
                        "price_per_sqft": float(prop.get("price_per_sqft") or prop.get("price_per_sqft") or 0.0),
                        "bedrooms": int(prop.get("bedrooms") or 0),
                        "covered_area": float(prop.get("total_area_sqft") or 0.0),
                        "total_area_sqft": float(prop.get("total_area_sqft") or 0.0),
                        "locality": str(prop.get("locality") or "")[:100],
                        "area_name": str(prop.get("area_name") or "")[:100],
                        "city": str(prop.get("city") or "")[:50],
                        "lat": lat,
                        "lng": lng,
                    },
                }
            )

            if len(vectors) >= batch_size:
                results["properties"] += _add("properties", vectors)
                vectors = []
        if vectors:
            results["properties"] += _add("properties", vectors)

        # -----------------
        # POIs
        # -----------------
        pois = db.get_all_pois()
        vectors = []
        for i, poi in enumerate(pois):
            text = f"{poi.get('name', '')} {poi.get('category', '')} {poi.get('subcategory', '')}".strip()
            if not text:
                continue
            poi_id = str(poi.get("poi_id") or f"poi_{i}")
            lat = float(poi.get("lat") or 0.0)
            lng = float(poi.get("lng") or 0.0)
            vectors.append(
                {
                    "id": poi_id,
                    "values": self.embed_single(text),
                    "metadata": {
                        "type": "poi",
                        "text": str(text[:500]),
                        "name": str(poi.get("name") or "")[:200],
                        "amenity": str(poi.get("category") or ""),
                        "category": str(poi.get("category") or ""),
                        "subcategory": str(poi.get("subcategory") or ""),
                        "lat": lat,
                        "lng": lng,
                    },
                }
            )
            if len(vectors) >= batch_size:
                results["pois"] += _add("pois", vectors)
                vectors = []
        if vectors:
            results["pois"] += _add("pois", vectors)

        # -----------------
        # Places
        # -----------------
        places = db.get_all_places()
        vectors = []
        for i, place in enumerate(places):
            text = f"{place.get('name', '')} {place.get('type', '')} Bangalore".strip()
            if not text:
                continue
            place_id = str(place.get("place_id") or f"place_{i}")
            lat = float(place.get("lat") or 0.0)
            lng = float(place.get("lng") or 0.0)
            vectors.append(
                {
                    "id": place_id,
                    "values": self.embed_single(text),
                    "metadata": {
                        "type": "place",
                        "text": str(text[:500]),
                        "name": str(place.get("name") or "")[:200],
                        "place_type": str(place.get("type") or ""),
                        "lat": lat,
                        "lng": lng,
                    },
                }
            )
            if len(vectors) >= batch_size:
                results["places"] += _add("places", vectors)
                vectors = []
        if vectors:
            results["places"] += _add("places", vectors)

        # -----------------
        # Transport
        # -----------------
        stops = db.get_all_transport()
        vectors = []
        for i, stop in enumerate(stops):
            text = f"{stop.get('name', '')} {stop.get('type', '')} {stop.get('line_name', '')}".strip()
            if not text:
                continue
            stop_id = str(stop.get("stop_id") or f"stop_{i}")
            lat = float(stop.get("lat") or 0.0)
            lng = float(stop.get("lng") or 0.0)
            vectors.append(
                {
                    "id": stop_id,
                    "values": self.embed_single(text),
                    "metadata": {
                        "type": "transport",
                        "text": str(text[:500]),
                        "name": str(stop.get("name") or "")[:200],
                        "transport_type": str(stop.get("type") or ""),
                        "line_name": str(stop.get("line_name") or ""),
                        "lat": lat,
                        "lng": lng,
                    },
                }
            )
            if len(vectors) >= batch_size:
                results["transport"] += _add("transport", vectors)
                vectors = []
        if vectors:
            results["transport"] += _add("transport", vectors)

        return results
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        namespace: str = "",
        filter_dict: Optional[Dict] = None,
        include_metadata: bool = True,
        use_cache: bool = True,
        use_fallback: bool = True,
        skip_namespace_check: bool = False
    ) -> List[SearchResult]:
        """
        Search for similar vectors with caching and FAISS fallback.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            namespace: Namespace to search (empty string for default)
            filter_dict: Metadata filters
            include_metadata: Whether to include metadata in results
            use_cache: Whether to use query caching
            use_fallback: Whether to use FAISS fallback
            skip_namespace_check: Skip namespace existence check (for internal use)
            
        Returns:
            List of SearchResult objects
        """
        # Check if namespace exists (skip warning for default namespace)
        if not skip_namespace_check and self.local_store and namespace:
            if not self.local_store.namespace_exists(namespace):
                # Silently skip non-existent namespaces to avoid log spam
                return []
        
        # Check cache first
        if use_cache and self.cache:
            cached = self.cache.get(query, namespace=namespace, top_k=top_k)
            if cached is not None:
                return cached

        try:
            query_embedding = self.embed_single(query)
        except Exception as e:
            print(f"[WARNING] RAG embeddings unavailable: {e}")
            return []

        def _search_faiss() -> Optional[List[SearchResult]]:
            if not (use_fallback and self.local_store):
                return None
            try:
                local_results = self.local_store.search(
                    query_embedding,
                    top_k=top_k,
                    namespace=namespace or "default",
                    filter_dict=filter_dict,
                )
                return [
                    SearchResult(
                        id=r.id,
                        score=r.score,
                        text=r.text,
                        metadata=r.metadata,
                        lat=r.lat,
                        lng=r.lng,
                    )
                    for r in local_results
                ]
            except Exception as e:
                print(f"[ERROR] FAISS search failed: {e}")
                return []

        # Search using FAISS
        search_results = _search_faiss() or []

        if use_cache and self.cache:
            self.cache.set(query, search_results, namespace=namespace, top_k=top_k)

        return search_results
    
    def get_available_namespaces(self) -> List[str]:
        """
        Get list of namespaces that exist and have vectors.
        
        Returns:
            List of available namespace names
        """
        if not self.local_store:
            return []
        return self.local_store.list_namespaces(include_empty=False)
    
    def get_namespace_stats(self) -> Dict[str, Any]:
        """
        Get statistics about all namespaces.
        
        Returns:
            Dict with namespace statistics
        """
        if not self.local_store:
            return {"error": "FAISS not available", "namespaces": {}}
        return self.local_store.get_all_namespace_info()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on RAG service.
        
        Returns:
            Dict with health status information
        """
        health = {
            "status": "healthy",
            "embedding_model": "not_loaded",
            "faiss_available": FAISS_AVAILABLE and self.local_store is not None,
            "cache_available": self.cache is not None,
            "namespaces": {},
            "total_vectors": 0,
            "auto_index_enabled": self.auto_index,
            "issues": []
        }
        
        # Check embedding model
        if self.embedding_model is not None:
            health["embedding_model"] = "loaded"
        elif EMBEDDINGS_AVAILABLE:
            health["embedding_model"] = "available_lazy"
        else:
            health["embedding_model"] = "unavailable"
            health["issues"].append("Embedding model not available")
        
        # Check FAISS
        if not self.local_store:
            health["status"] = "degraded"
            health["issues"].append("FAISS local store not initialized")
        else:
            # Get namespace info
            ns_info = self.local_store.get_all_namespace_info()
            health["namespaces"] = ns_info
            
            for ns_name, ns_data in ns_info.items():
                health["total_vectors"] += ns_data.get("vector_count", 0)
            
            # Check if any default namespaces are missing
            available = set(self.get_available_namespaces())
            missing = [ns for ns in self.DEFAULT_NAMESPACES if ns not in available]
            if missing:
                health["issues"].append(f"Missing namespaces: {', '.join(missing)}")
                if health["status"] == "healthy":
                    health["status"] = "degraded"
        
        # Set status based on issues
        if len(health["issues"]) > 1:
            health["status"] = "degraded"
        elif len(health["issues"]) > 2:
            health["status"] = "unhealthy"
        
        return health
    
    def ensure_namespaces_indexed(self, force: bool = False) -> Dict[str, int]:
        """
        Ensure all default namespaces are indexed.
        Will run auto-indexing if enabled and namespaces are empty.
        
        Args:
            force: Force reindex even if namespaces exist
            
        Returns:
            Dict with indexing results
        """
        if not self.local_store:
            return {"error": "FAISS not available"}
        
        # Check if already indexed
        if not force and self._auto_indexed:
            return {"status": "already_indexed", "namespaces": self.get_available_namespaces()}
        
        # Check if any default namespace is missing
        available = set(self.get_available_namespaces())
        missing = [ns for ns in self.DEFAULT_NAMESPACES if ns not in available]
        
        if not missing and not force:
            return {"status": "already_indexed", "namespaces": list(available)}
        
        # Run indexing
        print(f"[RAG] Indexing namespaces: {missing if missing else 'all (force)'}")
        result = self.index_faiss_from_db(force_reindex=force)
        self._auto_indexed = True
        
        return result
    
    def semantic_search(
        self,
        query: str,
        namespaces: List[str] = None,
        top_k: int = 10,
        lat: float = None,
        lng: float = None,
        radius_km: float = None,
        auto_index: bool = None
    ) -> List[SearchResult]:
        """
        Semantic search across multiple namespaces with optional location filtering.
        
        Args:
            query: Search query text
            namespaces: List of namespaces to search (None for all available)
            top_k: Number of results to return
            lat: Latitude for location filtering
            lng: Longitude for location filtering
            radius_km: Radius in km for location filtering
            auto_index: Override auto_index setting for this search
            
        Returns:
            List of SearchResult objects sorted by score
        """
        # Handle auto-indexing
        if auto_index is None:
            auto_index = self.auto_index
        
        if auto_index and self.local_store:
            available = self.get_available_namespaces()
            if not available:
                print("[RAG] No namespaces available, running auto-index...")
                self.ensure_namespaces_indexed()
        
        # Get namespaces to search
        if namespaces is None:
            # Use default namespaces but filter to only existing ones
            namespaces = self.DEFAULT_NAMESPACES
        
        # Filter to only existing namespaces
        if self.local_store:
            available = set(self.get_available_namespaces())
            namespaces = [ns for ns in namespaces if ns in available]
            
            if not namespaces:
                # No namespaces available, return empty
                return []
        
        all_results = []
        
        for ns in namespaces:
            results = self.search(query, top_k=top_k, namespace=ns)
            all_results.extend(results)
        
        # Sort by score
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Filter by location if provided
        if lat is not None and lng is not None and radius_km is not None:
            filtered = []
            for r in all_results:
                if r.lat is not None and r.lng is not None:
                    dist = self._haversine(lat, lng, r.lat, r.lng)
                    if dist <= radius_km:
                        filtered.append(r)
            all_results = filtered
        
        return all_results[:top_k]
    
    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in km between two points."""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth radius in km
        
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def get_context_for_query(
        self,
        query: str,
        lat: float = None,
        lng: float = None,
        radius_km: float = 2.0,
        max_results: int = 15
    ) -> str:
        """
        Get relevant context for a query to augment LLM responses.
        Returns a formatted string with relevant information.
        """
        results = self.semantic_search(
            query,
            top_k=max_results,
            lat=lat,
            lng=lng,
            radius_km=radius_km if lat and lng else None
        )
        
        if not results:
            return ""
        
        context_parts = ["## Relevant Information from Knowledge Base:\n"]
        
        # Group by type
        by_type = {}
        for r in results:
            t = r.metadata.get("type", "other")
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(r)
        
        for data_type, items in by_type.items():
            context_parts.append(f"\n### {data_type.title()}s:")
            for item in items[:5]:  # Limit per type
                name = item.metadata.get("name") or item.metadata.get("title") or "Unknown"
                if data_type == "property":
                    price = item.metadata.get("price", 0)
                    beds = item.metadata.get("bedrooms", 0)
                    area = item.metadata.get("covered_area", None)
                    if area in (None, 0, "0"):
                        area = item.metadata.get("total_area_sqft", 0)
                    context_parts.append(f"- **{name}**: ₹{price:,.0f}, {beds} BHK, {area} sq ft")
                elif data_type == "poi":
                    amenity = item.metadata.get("amenity", "")
                    context_parts.append(f"- {name} ({amenity})")
                elif data_type == "transport":
                    tt = item.metadata.get("transport_type", "")
                    context_parts.append(f"- {name} ({tt})")
                else:
                    context_parts.append(f"- {name}")
        
        return "\n".join(context_parts)


# Singleton instance
_rag_service: Optional[RAGService] = None
_rag_service_lock: Lock = Lock()


def get_rag_service(data_dir: Path = None, auto_index: bool = False) -> RAGService:
    """
    Get or create the RAG service singleton.
    
    Args:
        data_dir: Directory for FAISS indexes (default: from config)
        auto_index: If True, automatically index from DB on first search if empty
        
    Returns:
        RAGService singleton instance
    """
    global _rag_service
    if _rag_service is None:
        with _rag_service_lock:
            if _rag_service is None:
                if data_dir is None:
                    from config import config
                    data_dir = config.FAISS_DIR
                _rag_service = RAGService(data_dir, auto_index=auto_index)
    return _rag_service


def reset_rag_service():
    """Reset the RAG service singleton (for testing)."""
    global _rag_service
    with _rag_service_lock:
        _rag_service = None
