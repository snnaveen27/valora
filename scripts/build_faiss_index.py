"""
Build FAISS Vector Index for Semantic Property Search
Creates embeddings from property data for similarity search
"""

import os
import sys
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.db_service import DatabaseService

# Check dependencies
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("❌ FAISS not installed. Run: pip install faiss-cpu")

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("❌ sentence-transformers not installed. Run: pip install sentence-transformers")

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "src" / "data" / "valora.db"
FAISS_DIR = BASE_DIR / "src" / "data" / "faiss_store"

# Config
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
BATCH_SIZE = 500


def create_property_text(row: Dict) -> str:
    """Create searchable text from property data."""
    parts = []
    
    # Title and description
    if row.get('title'):
        parts.append(row['title'])
    
    # Category and type
    if row.get('property_category'):
        parts.append(row['property_category'])
    if row.get('property_subtype'):
        parts.append(row['property_subtype'])
    if row.get('bhk'):
        parts.append(row['bhk'])
    
    # Location
    if row.get('locality'):
        parts.append(row['locality'])
    if row.get('area_name') and row['area_name'] != row.get('locality'):
        parts.append(row['area_name'])
    if row.get('city'):
        parts.append(row['city'])
    if row.get('pincode'):
        parts.append(f"pincode {row['pincode']}")
    
    # Listing type
    if row.get('listing_type'):
        parts.append(f"for {row['listing_type']}")
    
    # Price range description
    price = row.get('price')
    if price:
        if price >= 10000000:
            parts.append(f"{price/10000000:.1f} crore")
        elif price >= 100000:
            parts.append(f"{price/100000:.1f} lac")
    
    # Specs
    if row.get('bedrooms'):
        parts.append(f"{row['bedrooms']} bedroom")
    if row.get('total_area_sqft'):
        parts.append(f"{row['total_area_sqft']:.0f} sqft")
    
    # Furnishing
    if row.get('furnishing'):
        parts.append(row['furnishing'])
    
    return ' '.join(str(p) for p in parts if p)


def build_index():
    """Build FAISS index from database properties."""
    if not FAISS_AVAILABLE or not EMBEDDINGS_AVAILABLE:
        print("❌ Missing dependencies. Cannot build index.")
        return False
    
    print("=" * 60)
    print("🔧 BUILDING FAISS VECTOR INDEX")
    print("=" * 60)
    
    # Create output directory
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load embedding model
    print(f"\n📦 Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print("  ✅ Model loaded")
    
    # Connect to database
    print(f"\n📂 Connecting to database: {DB_PATH}")
    db = DatabaseService(str(DB_PATH))
    
    # Get all properties
    print("\n📊 Fetching properties...")
    rows = db.execute("""
        SELECT 
            id, property_id, title, property_category, property_subtype,
            bhk, locality, area_name, city, pincode, listing_type,
            price, bedrooms, total_area_sqft, furnishing,
            latitude, longitude
        FROM properties
        WHERE status = 'active'
    """)
    
    print(f"  Found {len(rows):,} properties")
    
    if not rows:
        print("❌ No properties found")
        return False
    
    # Create texts for embedding
    print("\n📝 Creating searchable texts...")
    texts = []
    metadata = []
    
    for row in rows:
        text = create_property_text(row)
        texts.append(text)
        
        metadata.append({
            'id': row['id'],
            'property_id': row['property_id'],
            'title': row['title'],
            'category': row['property_category'],
            'subtype': row['property_subtype'],
            'bhk': row['bhk'],
            'locality': row['locality'],
            'city': row['city'],
            'pincode': row['pincode'],
            'listing_type': row['listing_type'],
            'price': row['price'],
            'lat': row['latitude'],
            'lng': row['longitude'],
            'text': text[:500]
        })
    
    print(f"  Created {len(texts):,} text entries")
    
    # Generate embeddings in batches
    print(f"\n🧠 Generating embeddings (batch size: {BATCH_SIZE})...")
    all_embeddings = []
    
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        batch_embeddings = model.encode(batch, show_progress_bar=False)
        all_embeddings.append(batch_embeddings)
        
        progress = min(i + BATCH_SIZE, len(texts))
        print(f"  Processed {progress:,}/{len(texts):,} ({100*progress/len(texts):.1f}%)")
    
    embeddings = np.vstack(all_embeddings).astype('float32')
    print(f"  ✅ Generated {embeddings.shape[0]:,} embeddings of dimension {embeddings.shape[1]}")
    
    # Normalize for cosine similarity
    print("\n📐 Normalizing vectors...")
    faiss.normalize_L2(embeddings)
    
    # Create FAISS index
    print("\n🗂️ Building FAISS index...")
    index = faiss.IndexFlatIP(EMBEDDING_DIM)  # Inner product for cosine similarity
    index.add(embeddings)
    print(f"  ✅ Index contains {index.ntotal:,} vectors")
    
    # Save index
    index_path = FAISS_DIR / "properties.faiss"
    print(f"\n💾 Saving index to {index_path}")
    faiss.write_index(index, str(index_path))
    
    # Save metadata
    metadata_path = FAISS_DIR / "properties_metadata.pkl"
    print(f"💾 Saving metadata to {metadata_path}")
    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata, f)
    
    # Save ID mapping
    id_map = [m['property_id'] for m in metadata]
    idmap_path = FAISS_DIR / "properties_idmap.pkl"
    with open(idmap_path, 'wb') as f:
        pickle.dump(id_map, f)
    
    print("\n" + "=" * 60)
    print("✅ FAISS INDEX BUILT SUCCESSFULLY")
    print("=" * 60)
    print(f"\n📊 Stats:")
    print(f"  • Total vectors: {index.ntotal:,}")
    print(f"  • Dimension: {EMBEDDING_DIM}")
    print(f"  • Index file: {index_path}")
    print(f"  • Metadata file: {metadata_path}")
    
    # Test search
    print("\n🔍 Testing search...")
    test_query = "3 BHK apartment in Whitefield for sale under 1 crore"
    query_embedding = model.encode([test_query])
    faiss.normalize_L2(query_embedding)
    
    scores, indices = index.search(query_embedding, 5)
    
    print(f"  Query: '{test_query}'")
    print(f"  Top 5 results:")
    for i, (score, idx) in enumerate(zip(scores[0], indices[0]), 1):
        m = metadata[idx]
        print(f"    {i}. [{score:.3f}] {m['title'][:50]}... ({m['category']}, {m['listing_type']})")
    
    print("\n✨ Done!")
    return True


if __name__ == "__main__":
    build_index()
