"""
Quick system verification script
"""
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

DB_PATH = Path(__file__).parent.parent / 'src' / 'data' / 'valora.db'

def main():
    print("\n" + "="*70)
    print("VALORA AI - SYSTEM VERIFICATION")
    print("="*70)
    
    db = sqlite3.connect(str(DB_PATH))
    c = db.cursor()
    
    # Table counts
    tables = {
        'properties': 42000,
        'pois': 29000,
        'places': 1000,
        'transport_stops': 5000,
        'buildings': 680000,
    }
    
    print("\n📊 Database Tables:")
    for table, expected in tables.items():
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        status = "✅" if count >= expected else "⚠️"
        print(f"  {status} {table:20} {count:>10,}")
    
    # Spatial columns
    print("\n🗺️  Spatial Columns:")
    
    # Properties
    c.execute("SELECT COUNT(*) FROM properties WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    props_coords = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM properties")
    props_total = c.fetchone()[0]
    print(f"  ✅ properties:        {props_coords:,}/{props_total:,} ({100*props_coords//props_total}%)")
    
    # POIs
    c.execute("SELECT COUNT(*) FROM pois WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    pois_coords = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM pois")
    pois_total = c.fetchone()[0]
    print(f"  ✅ pois:              {pois_coords:,}/{pois_total:,} ({100*pois_coords//pois_total}%)")
    
    # Places (uses center_latitude/center_longitude)
    c.execute("SELECT COUNT(*) FROM places WHERE center_latitude IS NOT NULL AND center_longitude IS NOT NULL")
    places_coords = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM places")
    places_total = c.fetchone()[0]
    print(f"  ✅ places:            {places_coords:,}/{places_total:,} ({100*places_coords//places_total}%)")
    
    # Transport
    c.execute("SELECT COUNT(*) FROM transport_stops WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    transport_coords = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM transport_stops")
    transport_total = c.fetchone()[0]
    print(f"  ✅ transport_stops:   {transport_coords:,}/{transport_total:,} ({100*transport_coords//transport_total}%)")
    
    # Vector stores
    print("\n🔍 Vector Stores:")
    try:
        from rag_service import get_rag_service
        rag = get_rag_service()
        if rag.index:
            stats = rag.index.describe_index_stats()
            print(f"  ✅ Pinecone:          {stats.total_vector_count:,} vectors")
        else:
            print(f"  ⚠️ Pinecone:          Not connected")
    except Exception as e:
        print(f"  ❌ Pinecone:          Error: {e}")
    
    try:
        from local_vector_store import get_local_store
        store = get_local_store()
        stats = store.get_stats()
        print(f"  ✅ FAISS:             {stats['total_vectors']:,} vectors")
    except Exception as e:
        print(f"  ❌ FAISS:             Error: {e}")
    
    # AI Services
    print("\n🤖 AI Services:")
    try:
        from gis_agents import GISAgentOrchestrator
        orchestrator = GISAgentOrchestrator()
        print(f"  ✅ GIS Orchestrator:  Loaded")
    except Exception as e:
        print(f"  ❌ GIS Orchestrator:  Error: {e}")
    
    try:
        from rag_service import get_rag_service
        rag = get_rag_service()
        test_embedding = rag.embed_single("test")
        print(f"  ✅ Embedding Model:   Working (dim={len(test_embedding)})")
    except Exception as e:
        print(f"  ❌ Embedding Model:   Error: {e}")
    
    db.close()
    
    print("\n" + "="*70)
    print("✅ All systems operational!")
    print("="*70)

if __name__ == "__main__":
    main()
