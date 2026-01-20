"""
Valora AI - RAG Service with Pinecone
Phase 1: Spatial Knowledge Layer

Provides vector embeddings and semantic search for:
- Properties (real estate listings)
- POIs (points of interest)
- Places (neighborhoods, landmarks)
- Transport (metro, bus stops)
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np

# Pinecone and embeddings
try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    print("[WARNING]  Pinecone not installed. RAG features will be limited.")

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
    Uses Pinecone for vector storage and sentence-transformers for embeddings.
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.embedding_model = None
        self.pc = None
        self.index = None
        self.index_name = os.getenv("PINECONE_INDEX", "valora-spatial")
        self.dimension = 384  # all-MiniLM-L6-v2 dimension
        
        self._init_embeddings()
        self._init_pinecone()
    
    def _init_embeddings(self):
        """Initialize the embedding model."""
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
    
    def _init_pinecone(self):
        """Initialize Pinecone client and index."""
        if not PINECONE_AVAILABLE:
            print("[WARNING]  Pinecone not available. Using local fallback.")
            return
        
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            print("[WARNING]  PINECONE_API_KEY not set. RAG disabled.")
            return
        
        try:
            self.pc = Pinecone(api_key=api_key)
            
            # Check if index exists
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                print(f"[INFO] Creating Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                print(f"[OK] Created Pinecone index: {self.index_name}")
            
            self.index = self.pc.Index(self.index_name)
            stats = self.index.describe_index_stats()
            print(f"[OK] Connected to Pinecone index: {self.index_name} ({stats.total_vector_count} vectors)")
            
        except Exception as e:
            print(f"[ERROR] Pinecone initialization failed: {e}")
            self.pc = None
            self.index = None
    
    def _generate_id(self, text: str, prefix: str = "") -> str:
        """Generate a unique ID for a text."""
        hash_str = hashlib.md5(text.encode()).hexdigest()[:12]
        return f"{prefix}_{hash_str}" if prefix else hash_str
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        if self.embedding_model is None:
            # Fallback: random embeddings (for testing only)
            return np.random.randn(len(texts), self.dimension).astype(np.float32)
        
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        return embeddings.astype(np.float32)
    
    def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self.embed([text])[0].tolist()
    
    def upsert_vectors(self, vectors: List[Dict[str, Any]], namespace: str = ""):
        """Upsert vectors to Pinecone."""
        if self.index is None:
            print("[WARNING]  Pinecone index not available. Skipping upsert.")
            return False
        
        try:
            # Batch upsert (max 100 at a time)
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch, namespace=namespace)
            return True
        except Exception as e:
            print(f"[ERROR] Upsert failed: {e}")
            return False
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        namespace: str = "",
        filter_dict: Optional[Dict] = None,
        include_metadata: bool = True
    ) -> List[SearchResult]:
        """Search for similar vectors."""
        if self.index is None:
            return []
        
        try:
            query_embedding = self.embed_single(query)
            
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                filter=filter_dict,
                include_metadata=include_metadata
            )
            
            search_results = []
            for match in results.matches:
                metadata = match.metadata or {}
                search_results.append(SearchResult(
                    id=match.id,
                    score=match.score,
                    text=metadata.get("text", ""),
                    metadata=metadata,
                    lat=metadata.get("lat"),
                    lng=metadata.get("lng")
                ))
            
            return search_results
            
        except Exception as e:
            print(f"[ERROR] Search failed: {e}")
            return []
    
    def delete_all(self, namespace: str = ""):
        """Delete all vectors in a namespace."""
        if self.index is None:
            return False
        
        try:
            self.index.delete(delete_all=True, namespace=namespace)
            print(f"[OK] Deleted all vectors in namespace: {namespace or 'default'}")
            return True
        except Exception as e:
            print(f"[ERROR] Delete failed: {e}")
            return False
    
    def index_properties(self, properties_dir: Path) -> int:
        """Index all property listings."""
        if self.index is None:
            print("[WARNING]  Pinecone not available. Skipping property indexing.")
            return 0
        
        print("[INFO] Indexing properties...")
        vectors = []
        count = 0
        
        for json_file in properties_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    properties = json.load(f)
                
                category = json_file.stem.replace("bangalore-", "").replace("-", "_")
                
                for prop in properties:
                    # Create searchable text
                    text_parts = [
                        prop.get("name", ""),
                        prop.get("description", ""),
                        prop.get("address", ""),
                        f"{prop.get('bedrooms', '')} BHK" if prop.get('bedrooms') else "",
                        f"{prop.get('covered_area', '')} sq ft" if prop.get('covered_area') else "",
                        prop.get("amenities", ""),
                        " ".join(prop.get("landmark_details", []) if isinstance(prop.get("landmark_details"), list) else [])
                    ]
                    text = " ".join([p for p in text_parts if p]).strip()
                    
                    if not text:
                        continue
                    
                    # Parse location
                    lat, lng = None, None
                    loc = prop.get("location", "")
                    if loc and "," in loc:
                        try:
                            lat, lng = map(float, loc.split(","))
                        except:
                            pass
                    
                    prop_id = self._generate_id(f"{prop.get('id', '')}_{category}", "prop")
                    
                    # Ensure all metadata values are not None (Pinecone requirement)
                    # Convert all values to proper types, defaulting to safe values
                    try:
                        bedrooms_val = int(prop.get("bedrooms") or 0) if prop.get("bedrooms") is not None else 0
                    except (ValueError, TypeError):
                        bedrooms_val = 0
                    try:
                        price_val = float(prop.get("price") or 0) if prop.get("price") is not None else 0.0
                    except (ValueError, TypeError):
                        price_val = 0.0
                    try:
                        price_sqft_val = float(prop.get("price_per_sq_ft") or 0) if prop.get("price_per_sq_ft") is not None else 0.0
                    except (ValueError, TypeError):
                        price_sqft_val = 0.0
                    try:
                        area_val = float(prop.get("covered_area") or 0) if prop.get("covered_area") is not None else 0.0
                    except (ValueError, TypeError):
                        area_val = 0.0
                    
                    vectors.append({
                        "id": prop_id,
                        "values": self.embed_single(text),
                        "metadata": {
                            "type": "property",
                            "category": str(category),
                            "text": str(text[:500]) if text else "",
                            "name": str(prop.get("name") or "")[:200],
                            "price": price_val,
                            "price_per_sqft": price_sqft_val,
                            "bedrooms": bedrooms_val,
                            "covered_area": area_val,
                            "lat": float(lat) if lat is not None else 0.0,
                            "lng": float(lng) if lng is not None else 0.0,
                            "original_id": str(prop.get("id") or "")
                        }
                    })
                    count += 1
                    
                    # Batch upsert every 500 vectors
                    if len(vectors) >= 500:
                        self.upsert_vectors(vectors, namespace="properties")
                        vectors = []
                        print(f"  Indexed {count} properties...")
                        
            except Exception as e:
                print(f"[WARNING]  Error indexing {json_file.name}: {e}")
        
        # Upsert remaining vectors
        if vectors:
            self.upsert_vectors(vectors, namespace="properties")
        
        print(f"[OK] Indexed {count} properties")
        return count
    
    def index_pois(self, osm_dir: Path) -> int:
        """Index POIs from OSM data."""
        if self.index is None:
            return 0
        
        print("[INFO] Indexing POIs...")
        pois_file = osm_dir / "pois.geojson"
        
        if not pois_file.exists():
            print(f"[WARNING]  POIs file not found: {pois_file}")
            return 0
        
        vectors = []
        count = 0
        
        try:
            with open(pois_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            features = data.get("features", [])
            
            for feat in features:
                props = feat.get("properties", {})
                geom = feat.get("geometry", {})
                
                name = props.get("name", "")
                if not name:
                    continue
                
                # Get coordinates
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    lng, lat = coords[0], coords[1]
                else:
                    continue
                
                # Create searchable text
                amenity = props.get("amenity", "")
                shop = props.get("shop", "")
                cuisine = props.get("cuisine", "")
                
                text = f"{name} {amenity} {shop} {cuisine}".strip()
                
                poi_id = self._generate_id(f"{name}_{lat}_{lng}", "poi")
                
                vectors.append({
                    "id": poi_id,
                    "values": self.embed_single(text),
                    "metadata": {
                        "type": "poi",
                        "text": text,
                        "name": name,
                        "amenity": amenity,
                        "shop": shop,
                        "lat": lat,
                        "lng": lng
                    }
                })
                count += 1
                
                if len(vectors) >= 500:
                    self.upsert_vectors(vectors, namespace="pois")
                    vectors = []
                    print(f"  Indexed {count} POIs...")
                    
        except Exception as e:
            print(f"[ERROR] Error indexing POIs: {e}")
        
        if vectors:
            self.upsert_vectors(vectors, namespace="pois")
        
        print(f"[OK] Indexed {count} POIs")
        return count
    
    def index_places(self, osm_dir: Path) -> int:
        """Index places (neighborhoods, landmarks) from OSM data."""
        if self.index is None:
            return 0
        
        print("[INFO] Indexing places...")
        places_file = osm_dir / "places.geojson"
        
        if not places_file.exists():
            print(f"[WARNING]  Places file not found: {places_file}")
            return 0
        
        vectors = []
        count = 0
        
        try:
            with open(places_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            features = data.get("features", [])
            
            for feat in features:
                props = feat.get("properties", {})
                geom = feat.get("geometry", {})
                
                name = props.get("name", "")
                if not name:
                    continue
                
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    lng, lat = coords[0], coords[1]
                else:
                    continue
                
                place_type = props.get("place", "")
                text = f"{name} {place_type} Bangalore".strip()
                
                place_id = self._generate_id(f"{name}_{lat}_{lng}", "place")
                
                vectors.append({
                    "id": place_id,
                    "values": self.embed_single(text),
                    "metadata": {
                        "type": "place",
                        "text": text,
                        "name": name,
                        "place_type": place_type,
                        "lat": lat,
                        "lng": lng
                    }
                })
                count += 1
                
                if len(vectors) >= 500:
                    self.upsert_vectors(vectors, namespace="places")
                    vectors = []
                    
        except Exception as e:
            print(f"[ERROR] Error indexing places: {e}")
        
        if vectors:
            self.upsert_vectors(vectors, namespace="places")
        
        print(f"[OK] Indexed {count} places")
        return count
    
    def index_transport(self, osm_dir: Path) -> int:
        """Index transport stops (metro, bus) from OSM data."""
        if self.index is None:
            return 0
        
        print("[INFO] Indexing transport...")
        transport_file = osm_dir / "transport.geojson"
        
        if not transport_file.exists():
            print(f"[WARNING]  Transport file not found: {transport_file}")
            return 0
        
        vectors = []
        count = 0
        
        try:
            with open(transport_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            features = data.get("features", [])
            
            for feat in features:
                props = feat.get("properties", {})
                geom = feat.get("geometry", {})
                
                name = props.get("name", "")
                if not name:
                    continue
                
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    lng, lat = coords[0], coords[1]
                else:
                    continue
                
                transport_type = props.get("railway", "") or props.get("highway", "") or props.get("amenity", "")
                text = f"{name} {transport_type} station stop Bangalore".strip()
                
                transport_id = self._generate_id(f"{name}_{lat}_{lng}", "transport")
                
                vectors.append({
                    "id": transport_id,
                    "values": self.embed_single(text),
                    "metadata": {
                        "type": "transport",
                        "text": text,
                        "name": name,
                        "transport_type": transport_type,
                        "lat": lat,
                        "lng": lng
                    }
                })
                count += 1
                
                if len(vectors) >= 500:
                    self.upsert_vectors(vectors, namespace="transport")
                    vectors = []
                    
        except Exception as e:
            print(f"[ERROR] Error indexing transport: {e}")
        
        if vectors:
            self.upsert_vectors(vectors, namespace="transport")
        
        print(f"[OK] Indexed {count} transport stops")
        return count
    
    def index_all(self, properties_dir: Path, osm_dir: Path, force_reindex: bool = False) -> Dict[str, int]:
        """Index all data sources."""
        if force_reindex:
            print("🗑️  Clearing existing index...")
            self.delete_all("properties")
            self.delete_all("pois")
            self.delete_all("places")
            self.delete_all("transport")
        
        results = {
            "properties": self.index_properties(properties_dir),
            "pois": self.index_pois(osm_dir),
            "places": self.index_places(osm_dir),
            "transport": self.index_transport(osm_dir)
        }
        
        total = sum(results.values())
        print(f"[OK] Total indexed: {total} vectors")
        return results
    
    def semantic_search(
        self,
        query: str,
        namespaces: List[str] = None,
        top_k: int = 10,
        lat: float = None,
        lng: float = None,
        radius_km: float = None
    ) -> List[SearchResult]:
        """
        Semantic search across multiple namespaces with optional location filtering.
        """
        if namespaces is None:
            namespaces = ["properties", "pois", "places", "transport"]
        
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
                name = item.metadata.get("name", "Unknown")
                if data_type == "property":
                    price = item.metadata.get("price", 0)
                    beds = item.metadata.get("bedrooms", 0)
                    area = item.metadata.get("covered_area", 0)
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


def get_rag_service(data_dir: Path = None) -> RAGService:
    """Get or create the RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / 'src' / 'data'
        _rag_service = RAGService(data_dir)
    return _rag_service
