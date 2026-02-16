"""
Update Pinecone index with new POI data from database.
"""

import os
import sqlite3
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "valora.db"

try:
    from sentence_transformers import SentenceTransformer
    from pinecone import Pinecone
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    print("⚠️  sentence-transformers or pinecone not installed")


def update_pinecone_pois():
    """Update Pinecone with new POI data."""
    if not DEPS_AVAILABLE:
        print("❌ Dependencies not available")
        return
    
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX = os.getenv("PINECONE_INDEX", "valora-realestate")
    
    if not PINECONE_API_KEY:
        print("❌ PINECONE_API_KEY not set")
        return
    
    print("=" * 70)
    print("VALORA AI - PINECONE UPDATE")
    print("=" * 70)
    
    # Load embedding model
    print("\n[1/4] Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✓ Model loaded")
    
    # Connect to Pinecone
    print("\n[2/4] Connecting to Pinecone...")
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(PINECONE_INDEX)
    
    # Get index stats
    stats = index.describe_index_stats()
    print(f"✓ Connected to index: {PINECONE_INDEX}")
    print(f"   Current vectors: {stats.total_vector_count:,}")
    
    # Load POIs from database
    print("\n[3/4] Loading POIs from database...")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get POIs with Google Maps data (have ratings/reviews)
    cursor.execute("""
        SELECT poi_id, name, category, subcategory, latitude, longitude, source_data
        FROM pois
        WHERE source = 'google_maps' AND latitude IS NOT NULL
    """)
    
    pois = cursor.fetchall()
    print(f"✓ Found {len(pois)} Google Maps POIs to update")
    
    # Get real estate agents
    cursor.execute("""
        SELECT agent_id, name, rating, reviews_count, phone, address, latitude, longitude
        FROM real_estate_agents
        WHERE latitude IS NOT NULL
    """)
    
    agents = cursor.fetchall()
    print(f"✓ Found {len(agents)} real estate agents to add")
    
    conn.close()
    
    # Prepare vectors for POIs
    print("\n[4/4] Upserting to Pinecone...")
    
    batch_size = 100
    total_upserted = 0
    
    # Process POIs
    poi_vectors = []
    for poi in pois:
        try:
            source_data = json.loads(poi['source_data']) if poi['source_data'] else {}
            rating = source_data.get('rating', '')
            reviews = source_data.get('reviews_count', 0)
            
            # Create rich text for embedding
            text = f"{poi['name']} - {poi['category']} {poi['subcategory']} in Bangalore"
            if rating:
                text += f" - Rated {rating}/5 ({reviews} reviews)"
            
            embedding = model.encode(text).tolist()
            
            poi_vectors.append({
                "id": f"poi_{poi['poi_id']}",
                "values": embedding,
                "metadata": {
                    "type": "poi",
                    "name": poi['name'],
                    "category": poi['category'],
                    "subcategory": poi['subcategory'] or '',
                    "lat": poi['latitude'],
                    "lng": poi['longitude'],
                    "rating": rating or 0,
                    "reviews_count": reviews
                }
            })
            
            if len(poi_vectors) >= batch_size:
                index.upsert(vectors=poi_vectors, namespace="pois")
                total_upserted += len(poi_vectors)
                print(f"   Upserted {total_upserted} POI vectors...")
                poi_vectors = []
                
        except Exception as e:
            continue
    
    # Upsert remaining POIs
    if poi_vectors:
        index.upsert(vectors=poi_vectors, namespace="pois")
        total_upserted += len(poi_vectors)
    
    print(f"✓ Upserted {total_upserted} POI vectors")
    
    # Process Agents
    agent_vectors = []
    for agent in agents:
        try:
            text = f"{agent['name']} - Real Estate Agent in Bangalore"
            if agent['rating']:
                text += f" - Rated {agent['rating']}/5 ({agent['reviews_count']} reviews)"
            if agent['address']:
                text += f" at {agent['address']}"
            
            embedding = model.encode(text).tolist()
            
            agent_vectors.append({
                "id": f"agent_{agent['agent_id']}",
                "values": embedding,
                "metadata": {
                    "type": "agent",
                    "name": agent['name'],
                    "phone": agent['phone'] or '',
                    "lat": agent['latitude'],
                    "lng": agent['longitude'],
                    "rating": agent['rating'] or 0,
                    "reviews_count": agent['reviews_count'] or 0
                }
            })
            
        except Exception as e:
            continue
    
    if agent_vectors:
        index.upsert(vectors=agent_vectors, namespace="agents")
        print(f"✓ Upserted {len(agent_vectors)} agent vectors")
    
    # Final stats
    final_stats = index.describe_index_stats()
    print(f"\n✓ Final vector count: {final_stats.total_vector_count:,}")
    
    print("\n" + "=" * 70)
    print("PINECONE UPDATE COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    update_pinecone_pois()
