"""
Index all database data to Pinecone for RAG
- Properties from database (not files)
- POIs, Places, Transport
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_service import DatabaseService
from ai.rag_service import RAGService
from dotenv import load_dotenv

load_dotenv()

def index_properties_from_db(rag_service: RAGService, db: DatabaseService, resume_from: int = 0):
    """Index all properties from database to Pinecone with resume capability."""
    
    if rag_service.index is None:
        print("[ERROR] Pinecone index not available")
        return 0
    
    print("\n" + "="*70)
    print("INDEXING PROPERTIES FROM DATABASE TO PINECONE")
    print("="*70)
    
    # Get all properties from database
    properties = db.execute("SELECT * FROM properties")
    
    if not properties:
        print("[WARNING] No properties found in database")
        return 0
    
    print(f"[INFO] Found {len(properties)} properties in database")
    if resume_from > 0:
        print(f"[INFO] Resuming from index {resume_from}")
        properties = properties[resume_from:]
    
    vectors = []
    count = resume_from
    skipped = 0
    indexed_this_run = 0
    
    try:
        for i, prop in enumerate(properties):
            # Create searchable text from all relevant fields
            text_parts = [
                prop.get("title", ""),
                prop.get("description", ""),
                prop.get("address", ""),
                prop.get("locality", ""),
                prop.get("area_name", ""),
                prop.get("city", ""),
                f"{prop.get('bedrooms', '')} BHK" if prop.get('bedrooms') else "",
                f"{prop.get('total_area_sqft', '')} sq ft" if prop.get('total_area_sqft') else "",
                prop.get("property_type", ""),
                prop.get("listing_type", ""),
                prop.get("furnishing", ""),
                prop.get("amenities", ""),
            ]
            text = " ".join([str(p) for p in text_parts if p]).strip()
            
            if not text or len(text) < 10:
                skipped += 1
                continue
            
            # Get coordinates
            lat = prop.get("latitude", 0.0) or 0.0
            lng = prop.get("longitude", 0.0) or 0.0
            
            # Prepare metadata (ensure all values are valid types)
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
            
            prop_id = prop.get("property_id", f"prop_{count}")
            
            vectors.append({
                "id": prop_id,
                "values": rag_service.embed_single(text),
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
            count += 1
            indexed_this_run += 1
            
            # Batch upsert every 50 vectors (smaller batches for reliability)
            if len(vectors) >= 50:
                try:
                    rag_service.upsert_vectors(vectors, namespace="properties")
                    vectors = []
                    print(f"  Progress: {count:,} properties indexed...")
                except Exception as e:
                    print(f"  [ERROR] Batch upsert failed: {e}")
                    print(f"  [INFO] Resume from index {count - len(vectors)} if needed")
                    raise
    
    except KeyboardInterrupt:
        print(f"\n[INFO] Interrupted! Indexed {indexed_this_run} properties this run.")
        print(f"[INFO] To resume, use: resume_from={count}")
        # Upsert remaining vectors before exit
        if vectors:
            try:
                rag_service.upsert_vectors(vectors, namespace="properties")
                print(f"[OK] Saved {len(vectors)} pending vectors")
            except:
                pass
        return indexed_this_run
    except Exception as e:
        print(f"\n[ERROR] Indexing failed: {e}")
        if vectors:
            print(f"[INFO] {len(vectors)} vectors not saved. Resume from {count - len(vectors)}")
        raise
    
    # Upsert remaining vectors
    if vectors:
        rag_service.upsert_vectors(vectors, namespace="properties")
    
    print(f"\n[OK] Indexed {indexed_this_run:,} properties this run (total: {count:,})")
    if skipped > 0:
        print(f"[INFO] Skipped {skipped} properties (insufficient data)")
    
    return indexed_this_run


def index_pois_from_db(rag_service: RAGService, db: DatabaseService):
    """Index POIs from database to Pinecone."""
    
    if rag_service.index is None:
        return 0
    
    print("\n" + "="*70)
    print("INDEXING POIs FROM DATABASE TO PINECONE")
    print("="*70)
    
    pois = db.execute("SELECT * FROM pois")
    
    if not pois:
        print("[WARNING] No POIs found")
        return 0
    
    print(f"[INFO] Found {len(pois)} POIs in database")
    
    vectors = []
    count = 0
    
    for poi in pois:
        text_parts = [
            poi.get("name", ""),
            poi.get("category", ""),
            poi.get("subcategory", ""),
            poi.get("address", ""),
        ]
        text = " ".join([str(p) for p in text_parts if p]).strip()
        
        if not text:
            continue
        
        lat = poi.get("latitude", 0.0) or 0.0
        lng = poi.get("longitude", 0.0) or 0.0
        
        vectors.append({
            "id": poi.get("poi_id", f"poi_{count}"),
            "values": rag_service.embed_single(text),
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
        count += 1
        
        if len(vectors) >= 100:
            rag_service.upsert_vectors(vectors, namespace="spatial")
            vectors = []
            print(f"  Progress: {count:,} POIs indexed...")
    
    if vectors:
        rag_service.upsert_vectors(vectors, namespace="spatial")
    
    print(f"[OK] Indexed {count:,} POIs to Pinecone")
    return count


def index_places_from_db(rag_service: RAGService, db: DatabaseService):
    """Index places from database to Pinecone."""
    
    if rag_service.index is None:
        return 0
    
    print("\n" + "="*70)
    print("INDEXING PLACES FROM DATABASE TO PINECONE")
    print("="*70)
    
    places = db.execute("SELECT * FROM places")
    
    if not places:
        print("[WARNING] No places found")
        return 0
    
    print(f"[INFO] Found {len(places)} places in database")
    
    vectors = []
    count = 0
    
    for place in places:
        text = f"{place.get('name', '')} {place.get('place_type', '')}"
        
        if not text.strip():
            continue
        
        lat = place.get("center_latitude", 0.0) or 0.0
        lng = place.get("center_longitude", 0.0) or 0.0
        
        # Parse population (handle strings like '>5,000')
        pop_val = 0
        try:
            pop_str = str(place.get("population") or "0")
            # Remove non-numeric characters except digits
            pop_str = pop_str.replace(">", "").replace("<", "").replace(",", "").strip()
            pop_val = int(pop_str) if pop_str.isdigit() else 0
        except:
            pop_val = 0
        
        vectors.append({
            "id": place.get("place_id", f"place_{count}"),
            "values": rag_service.embed_single(text),
            "metadata": {
                "type": "place",
                "text": str(text[:500]),
                "name": str(place.get("name") or "")[:200],
                "place_type": str(place.get("place_type") or ""),
                "population": pop_val,
                "lat": float(lat),
                "lng": float(lng),
            }
        })
        count += 1
        
        if len(vectors) >= 100:
            rag_service.upsert_vectors(vectors, namespace="spatial")
            vectors = []
    
    if vectors:
        rag_service.upsert_vectors(vectors, namespace="spatial")
    
    print(f"[OK] Indexed {count:,} places to Pinecone")
    return count


def main():
    """Main indexing function."""
    
    # Initialize services
    db_path = Path(__file__).parent.parent.parent / 'storage' / 'valora.db'
    data_dir = Path(__file__).parent.parent.parent / 'storage'
    
    print("\n" + "="*70)
    print("VALORA AI - PINECONE INDEXING FROM DATABASE")
    print("="*70)
    print(f"Database: {db_path}")
    print(f"Pinecone Index: {os.getenv('PINECONE_INDEX', 'valora-realestate')}")
    print("="*70)
    
    db = DatabaseService(str(db_path))
    rag_service = RAGService(data_dir)
    
    if rag_service.index is None:
        print("\n[ERROR] Pinecone not available. Check PINECONE_API_KEY environment variable.")
        return
    
    # Get current stats
    stats = rag_service.index.describe_index_stats()
    print(f"\n[INFO] Current Pinecone stats:")
    print(f"  Total vectors: {stats.total_vector_count:,}")
    if hasattr(stats, 'namespaces'):
        for ns, count in stats.namespaces.items():
            print(f"  Namespace '{ns}': {count.vector_count:,} vectors")
    
    # Ask user if they want to clear existing data
    print("\n" + "="*70)
    response = input("Do you want to CLEAR existing Pinecone data before indexing? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        print("[INFO] Clearing existing data...")
        rag_service.delete_all(namespace="properties")
        rag_service.delete_all(namespace="spatial")
        print("[OK] Cleared all existing vectors")
    
    # Index all data
    total_indexed = 0
    total_indexed += index_properties_from_db(rag_service, db)
    total_indexed += index_pois_from_db(rag_service, db)
    total_indexed += index_places_from_db(rag_service, db)
    
    # Final stats
    print("\n" + "="*70)
    print("INDEXING COMPLETE")
    print("="*70)
    stats = rag_service.index.describe_index_stats()
    print(f"Total vectors indexed: {total_indexed:,}")
    print(f"Total vectors in Pinecone: {stats.total_vector_count:,}")
    if hasattr(stats, 'namespaces'):
        for ns, ns_stats in stats.namespaces.items():
            print(f"  Namespace '{ns}': {ns_stats.vector_count:,} vectors")
    print("="*70)


if __name__ == "__main__":
    main()
