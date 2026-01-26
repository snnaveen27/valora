"""
Check complete system status for AI agent readiness
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

DB_PATH = Path(__file__).parent.parent / 'src' / 'data' / 'valora.db'
FAISS_PATH = Path(__file__).parent.parent / 'src' / 'data' / 'faiss_store'
POSTED_PROPS = Path(__file__).parent.parent / 'src' / 'data' / 'posted_properties'

def check_database():
    print("\n" + "="*60)
    print("DATABASE STATUS")
    print("="*60)
    
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    
    # Table counts
    tables = ['properties', 'pois', 'places', 'transport_stops', 'buildings']
    print("\nTable Counts:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table:20} {count:>10,}")
    
    # Properties by source/platform
    print("\nProperties by Platform/Source:")
    cursor.execute("SELECT source, COUNT(*) as cnt FROM properties GROUP BY source ORDER BY cnt DESC")
    for row in cursor.fetchall():
        print(f"  {row['source'] or 'unknown':20} {row['cnt']:>10,}")
    
    # Properties by listing type
    print("\nProperties by Listing Type:")
    cursor.execute("SELECT listing_type, COUNT(*) as cnt FROM properties GROUP BY listing_type ORDER BY cnt DESC")
    for row in cursor.fetchall():
        print(f"  {row['listing_type'] or 'unknown':20} {row['cnt']:>10,}")
    
    # Properties by property type
    print("\nProperties by Property Type (top 10):")
    cursor.execute("SELECT property_type, COUNT(*) as cnt FROM properties GROUP BY property_type ORDER BY cnt DESC LIMIT 10")
    for row in cursor.fetchall():
        print(f"  {(row['property_type'] or 'unknown')[:20]:20} {row['cnt']:>10,}")
    
    db.close()

def check_faiss():
    print("\n" + "="*60)
    print("FAISS STATUS")
    print("="*60)
    
    if not FAISS_PATH.exists():
        print("  [ERROR] FAISS directory not found")
        return
    
    print("\nFAISS Files:")
    for f in FAISS_PATH.glob("*.faiss"):
        size_mb = f.stat().st_size / (1024*1024)
        print(f"  {f.name:30} {size_mb:>8.2f} MB")
    
    # Check namespaces
    namespaces = ['pois', 'places', 'transport', 'properties']
    print("\nNamespaces:")
    for ns in namespaces:
        faiss_file = FAISS_PATH / f"{ns}.faiss"
        if faiss_file.exists():
            print(f"  ✅ {ns}")
        else:
            print(f"  ❌ {ns} (missing)")

def check_pinecone():
    print("\n" + "="*60)
    print("PINECONE STATUS")
    print("="*60)
    
    try:
        from rag_service import get_rag_service
        rag = get_rag_service()
        
        if not rag.index:
            print("  [ERROR] Pinecone not connected")
            return
        
        stats = rag.index.describe_index_stats()
        print(f"\nTotal vectors: {stats.total_vector_count:,}")
        print("\nNamespaces:")
        for ns, ns_stats in stats.namespaces.items():
            print(f"  {ns:20} {ns_stats.vector_count:>10,}")
        
        # Check what's missing
        expected = ['properties', 'pois', 'places', 'transport', 'spatial']
        for ns in expected:
            if ns not in stats.namespaces:
                print(f"  ❌ {ns} (missing)")
    except Exception as e:
        print(f"  [ERROR] {e}")

def check_posted_properties():
    print("\n" + "="*60)
    print("POSTED PROPERTIES FOLDER")
    print("="*60)
    
    if not POSTED_PROPS.exists():
        print("  [ERROR] posted_properties directory not found")
        return
    
    print("\nPlatform Folders:")
    total_files = 0
    for platform_dir in POSTED_PROPS.iterdir():
        if platform_dir.is_dir():
            file_count = len(list(platform_dir.glob("**/*.json")))
            total_files += file_count
            print(f"  {platform_dir.name:20} {file_count:>5} JSON files")
    
    print(f"\nTotal JSON files: {total_files}")

def main():
    print("\n" + "="*60)
    print("VALORA AI - COMPLETE SYSTEM STATUS CHECK")
    print("="*60)
    
    check_database()
    check_faiss()
    check_pinecone()
    check_posted_properties()
    
    print("\n" + "="*60)
    print("AI AGENT READINESS SUMMARY")
    print("="*60)
    
    # Summary
    print("""
For AI Agent to work properly, we need:
1. ✅ POIs indexed in Pinecone/FAISS (for nearby searches)
2. ✅ Places indexed in Pinecone/FAISS (for location context)
3. ✅ Transport indexed in Pinecone/FAISS (for connectivity)
4. ⚠️  Properties indexed in Pinecone/FAISS (for property search)
5. ⚠️  Database with correct platform/source attribution
6. ⚠️  Posted properties saved for offline reuse
""")

if __name__ == "__main__":
    main()
