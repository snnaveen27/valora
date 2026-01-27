"""
Update FAISS indexes with POIs, places, and transport data.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

import json
import numpy as np

def main():
    print("=" * 70)
    print("UPDATING FAISS INDEXES")
    print("=" * 70)
    
    faiss_dir = Path(__file__).parent.parent / 'src' / 'data' / 'faiss_store'
    faiss_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if FAISS is available
    try:
        import faiss
        print("[OK] FAISS library available")
    except ImportError:
        print("[WARNING] FAISS not installed. Skipping index update.")
        print("  Install with: pip install faiss-cpu")
        return
    
    # Check if sentence-transformers is available
    try:
        from sentence_transformers import SentenceTransformer
        print("[OK] SentenceTransformers available")
    except ImportError:
        print("[WARNING] sentence-transformers not installed. Skipping.")
        print("  Install with: pip install sentence-transformers")
        return
    
    # Load embedding model
    print("\n[1/4] Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Get data from database
    print("\n[2/4] Loading data from database...")
    from database.query_service import get_query_service
    db = get_query_service()
    
    pois = db.get_all_pois(limit=30000)
    places = db.get_all_places(limit=2000)
    transport = db.get_all_transport(limit=10000)
    
    print(f"  POIs: {len(pois)}")
    print(f"  Places: {len(places)}")
    print(f"  Transport: {len(transport)}")
    
    # Create embeddings for POIs
    print("\n[3/4] Creating embeddings...")
    
    # POIs
    if pois:
        poi_texts = []
        poi_ids = []
        for poi in pois:
            text = f"{poi.get('name', '')} {poi.get('category', '')} {poi.get('subcategory', '')}"
            if text.strip():
                poi_texts.append(text)
                poi_ids.append(poi.get('poi_id', ''))
        
        if poi_texts:
            print(f"  Embedding {len(poi_texts)} POIs...")
            poi_embeddings = model.encode(poi_texts, show_progress_bar=True)
            
            # Create FAISS index
            dim = poi_embeddings.shape[1]
            poi_index = faiss.IndexFlatIP(dim)  # Inner product for cosine similarity
            faiss.normalize_L2(poi_embeddings)
            poi_index.add(poi_embeddings)
            
            # Save index
            faiss.write_index(poi_index, str(faiss_dir / 'pois.index'))
            with open(faiss_dir / 'pois_ids.json', 'w') as f:
                json.dump(poi_ids, f)
            print(f"  ✓ POIs index saved ({len(poi_ids)} vectors)")
    
    # Places
    if places:
        place_texts = []
        place_ids = []
        for place in places:
            text = f"{place.get('name', '')} {place.get('type', '')} Bangalore"
            if text.strip():
                place_texts.append(text)
                place_ids.append(place.get('place_id', ''))
        
        if place_texts:
            print(f"  Embedding {len(place_texts)} places...")
            place_embeddings = model.encode(place_texts, show_progress_bar=True)
            
            dim = place_embeddings.shape[1]
            place_index = faiss.IndexFlatIP(dim)
            faiss.normalize_L2(place_embeddings)
            place_index.add(place_embeddings)
            
            faiss.write_index(place_index, str(faiss_dir / 'places.index'))
            with open(faiss_dir / 'places_ids.json', 'w') as f:
                json.dump(place_ids, f)
            print(f"  ✓ Places index saved ({len(place_ids)} vectors)")
    
    # Transport
    if transport:
        transport_texts = []
        transport_ids = []
        for t in transport:
            text = f"{t.get('name', '')} {t.get('type', '')} station stop Bangalore"
            if text.strip():
                transport_texts.append(text)
                transport_ids.append(t.get('stop_id', ''))
        
        if transport_texts:
            print(f"  Embedding {len(transport_texts)} transport stops...")
            transport_embeddings = model.encode(transport_texts, show_progress_bar=True)
            
            dim = transport_embeddings.shape[1]
            transport_index = faiss.IndexFlatIP(dim)
            faiss.normalize_L2(transport_embeddings)
            transport_index.add(transport_embeddings)
            
            faiss.write_index(transport_index, str(faiss_dir / 'transport.index'))
            with open(faiss_dir / 'transport_ids.json', 'w') as f:
                json.dump(transport_ids, f)
            print(f"  ✓ Transport index saved ({len(transport_ids)} vectors)")
    
    print("\n[4/4] Verifying indexes...")
    for idx_file in faiss_dir.glob('*.index'):
        index = faiss.read_index(str(idx_file))
        print(f"  {idx_file.name}: {index.ntotal} vectors")
    
    print("\n" + "=" * 70)
    print("✅ FAISS INDEXES UPDATED")
    print("=" * 70)

if __name__ == '__main__':
    main()
