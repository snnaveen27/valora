"""
Export Pinecone vectors to FAISS local store
Run this to create offline FAISS backup
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rag_service import RAGService
from backend.local_vector_store import get_local_store, FAISS_AVAILABLE
from dotenv import load_dotenv

load_dotenv()


def export_namespace(
    rag: RAGService,
    local_store,
    namespace: str,
    batch_size: int = 1000
):
    """
    Export a Pinecone namespace to FAISS.
    
    Note: Pinecone doesn't provide a direct way to list all vectors,
    so we need to query the database and re-embed.
    """
    print(f"\n{'='*70}")
    print(f"EXPORTING NAMESPACE: {namespace}")
    print('='*70)
    
    if namespace == "properties":
        return export_properties(rag, local_store, batch_size)
    elif namespace == "pois":
        return export_pois(rag, local_store, batch_size)
    elif namespace == "places":
        return export_places(rag, local_store, batch_size)
    elif namespace == "transport":
        return export_transport(rag, local_store, batch_size)
    else:
        print(f"[WARNING] Unknown namespace: {namespace}")
        return 0


def export_properties(rag: RAGService, local_store, batch_size: int):
    """Export properties from database and embed."""
    from backend.database.query_service import get_query_service
    
    db = get_query_service()
    
    print("[INFO] Fetching properties from database...")
    properties = db.get_all_properties()
    
    if not properties:
        print("[WARNING] No properties found")
        return 0
    
    print(f"[INFO] Found {len(properties):,} properties")
    
    vectors_batch = []
    total_exported = 0
    
    for i, prop in enumerate(properties):
        # Create searchable text
        text_parts = [
            prop.get("title", ""),
            prop.get("description", ""),
            prop.get("address", ""),
            prop.get("locality", ""),
            prop.get("area_name", ""),
            f"{prop.get('bedrooms', '')} BHK" if prop.get('bedrooms') else "",
            prop.get("property_type", ""),
            prop.get("amenities", ""),
        ]
        text = " ".join([str(p) for p in text_parts if p]).strip()
        
        if not text or len(text) < 10:
            continue
        
        # Prepare metadata
        lat = prop.get("latitude", 0.0) or 0.0
        lng = prop.get("longitude", 0.0) or 0.0
        
        try:
            bedrooms_val = int(prop.get("bedrooms") or 0)
        except:
            bedrooms_val = 0
        
        try:
            price_val = float(prop.get("price") or 0)
        except:
            price_val = 0.0
        
        try:
            price_sqft_val = float(prop.get("price_per_sqft") or 0)
        except:
            price_sqft_val = 0.0
        
        try:
            area_val = float(prop.get("total_area_sqft") or 0)
        except:
            area_val = 0.0
        
        prop_id = prop.get("property_id", f"prop_{i}")
        
        # Embed and prepare vector
        embedding = rag.embed_single(text)
        
        vectors_batch.append({
            "id": prop_id,
            "values": embedding,
            "metadata": {
                "type": "property",
                "source": str(prop.get("source") or "unknown"),
                "text": str(text[:1000]),
                "title": str(prop.get("title") or "")[:200],
                "property_type": str(prop.get("property_type") or ""),
                "listing_type": str(prop.get("listing_type") or ""),
                "price": price_val,
                "price_per_sqft": price_sqft_val,
                "bedrooms": bedrooms_val,
                "total_area_sqft": area_val,
                "locality": str(prop.get("locality") or "")[:100],
                "area_name": str(prop.get("area_name") or "")[:100],
                "city": str(prop.get("city") or "")[:50],
                "lat": float(lat),
                "lng": float(lng),
            }
        })
        
        # Batch insert
        if len(vectors_batch) >= batch_size:
            local_store.add_vectors(vectors_batch, namespace="properties")
            total_exported += len(vectors_batch)
            print(f"  Exported {total_exported:,} / {len(properties):,} properties...")
            vectors_batch = []
    
    # Insert remaining
    if vectors_batch:
        local_store.add_vectors(vectors_batch, namespace="properties")
        total_exported += len(vectors_batch)
    
    print(f"[OK] Exported {total_exported:,} properties to FAISS")
    return total_exported


def export_pois(rag: RAGService, local_store, batch_size: int):
    """Export POIs from database."""
    from backend.database.query_service import get_query_service
    
    db = get_query_service()
    try:
        pois = db.get_all_pois()
    except Exception as e:
        print(f"[WARNING] POIs table not available: {e}")
        return 0
    
    if not pois:
        print("[INFO] No POIs found in database")
        return 0
    
    print(f"[INFO] Found {len(pois):,} POIs")
    
    vectors_batch = []
    total = 0
    
    for poi in pois:
        text = f"{poi.get('name', '')} {poi.get('category', '')} {poi.get('subcategory', '')}"
        
        if not text.strip():
            continue
        
        lat = poi.get("latitude", 0.0) or 0.0
        lng = poi.get("longitude", 0.0) or 0.0
        
        vectors_batch.append({
            "id": poi.get("poi_id", f"poi_{total}"),
            "values": rag.embed_single(text),
            "metadata": {
                "type": "poi",
                "text": str(text[:500]),
                "name": str(poi.get("name") or "")[:200],
                "category": str(poi.get("category") or ""),
                "subcategory": str(poi.get("subcategory") or ""),
                "lat": float(lat),
                "lng": float(lng),
            }
        })
        total += 1
        
        if len(vectors_batch) >= batch_size:
            local_store.add_vectors(vectors_batch, namespace="pois")
            print(f"  Exported {total:,} / {len(pois):,} POIs...")
            vectors_batch = []
    
    if vectors_batch:
        local_store.add_vectors(vectors_batch, namespace="pois")
    
    print(f"[OK] Exported {total:,} POIs to FAISS")
    return total


def export_places(rag: RAGService, local_store, batch_size: int):
    """Export places from database."""
    from backend.database.query_service import get_query_service
    
    db = get_query_service()
    try:
        places = db.get_all_places()
    except Exception as e:
        print(f"[WARNING] Places table not available: {e}")
        return 0
    
    if not places:
        return 0
    
    print(f"[INFO] Found {len(places):,} places")
    
    vectors_batch = []
    total = 0
    
    for place in places:
        text = f"{place.get('name', '')} {place.get('type', '')} {place.get('city', '')}"
        
        if not text.strip():
            continue
        
        lat = place.get("latitude", 0.0) or 0.0
        lng = place.get("longitude", 0.0) or 0.0
        
        vectors_batch.append({
            "id": place.get("place_id", f"place_{total}"),
            "values": rag.embed_single(text),
            "metadata": {
                "type": "place",
                "text": str(text[:500]),
                "name": str(place.get("name") or "")[:200],
                "place_type": str(place.get("type") or ""),
                "lat": float(lat),
                "lng": float(lng),
            }
        })
        total += 1
        
        if len(vectors_batch) >= batch_size:
            local_store.add_vectors(vectors_batch, namespace="places")
            vectors_batch = []
    
    if vectors_batch:
        local_store.add_vectors(vectors_batch, namespace="places")
    
    print(f"[OK] Exported {total:,} places to FAISS")
    return total


def export_transport(rag: RAGService, local_store, batch_size: int):
    """Export transport stops from database."""
    from backend.database.query_service import get_query_service
    
    db = get_query_service()
    try:
        stops = db.get_all_transport()
    except Exception as e:
        print(f"[WARNING] Transport table not available: {e}")
        return 0
    
    if not stops:
        return 0
    
    print(f"[INFO] Found {len(stops):,} transport stops")
    
    vectors_batch = []
    total = 0
    
    for stop in stops:
        text = f"{stop.get('name', '')} {stop.get('type', '')} {stop.get('route', '')}"
        
        if not text.strip():
            continue
        
        lat = stop.get("latitude", 0.0) or 0.0
        lng = stop.get("longitude", 0.0) or 0.0
        
        vectors_batch.append({
            "id": stop.get("stop_id", f"stop_{total}"),
            "values": rag.embed_single(text),
            "metadata": {
                "type": "transport",
                "text": str(text[:500]),
                "name": str(stop.get("name") or "")[:200],
                "transport_type": str(stop.get("type") or ""),
                "route": str(stop.get("route") or ""),
                "lat": float(lat),
                "lng": float(lng),
            }
        })
        total += 1
        
        if len(vectors_batch) >= batch_size:
            local_store.add_vectors(vectors_batch, namespace="transport")
            vectors_batch = []
    
    if vectors_batch:
        local_store.add_vectors(vectors_batch, namespace="transport")
    
    print(f"[OK] Exported {total:,} transport stops to FAISS")
    return total


def main():
    """Main export process."""
    print("\n" + "="*70)
    print("EXPORTING DATABASE TO FAISS (OFFLINE BACKUP)")
    print("="*70)
    
    if not FAISS_AVAILABLE:
        print("[ERROR] FAISS not available. Install: pip install faiss-cpu")
        return
    
    # Initialize services
    data_dir = Path(__file__).parent.parent / 'src' / 'data'
    rag = RAGService(data_dir)
    local_store = get_local_store(data_dir)
    
    # CLEAR EXISTING FAISS INDEXES TO PREVENT DUPLICATES
    print("\n[INFO] Clearing existing FAISS indexes to prevent duplicates...")
    local_store.clear_all_namespaces()
    print("[OK] FAISS store cleared")
    
    # Export all namespaces
    namespaces = ["properties", "pois", "places", "transport"]
    total_vectors = 0
    
    for namespace in namespaces:
        count = export_namespace(rag, local_store, namespace)
        total_vectors += count
        
        # Save after each namespace
        local_store.save(namespace)
    
    elapsed = time.time() - start_time
    
    # Print summary
    print("\n" + "="*70)
    print("EXPORT COMPLETE")
    print("="*70)
    print(f"Total vectors exported: {total_vectors:,}")
    print(f"Time taken: {elapsed:.1f}s")
    print()
    
    stats = local_store.get_stats()
    print("FAISS Store Statistics:")
    for ns, info in stats["namespaces"].items():
        print(f"  {ns}: {info['vector_count']:,} vectors")
    
    print(f"\nFAISS indexes saved to: {local_store.store_dir}")
    print("\n✅ Ready for offline operation!")


if __name__ == "__main__":
    main()
