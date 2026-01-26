"""
Test FAISS local store
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.local_vector_store import get_local_store
from backend.rag_service import RAGService

def test_faiss():
    print("\n" + "="*70)
    print("TESTING FAISS LOCAL STORE")
    print("="*70)
    
    # Initialize
    data_dir = Path(__file__).parent.parent / 'src' / 'data'
    local_store = get_local_store(data_dir)
    
    # Check stats
    stats = local_store.get_stats()
    print(f"\nFAISS Statistics:")
    print(f"Total vectors: {stats['total_vectors']:,}")
    print("\nNamespaces:")
    for ns, info in stats['namespaces'].items():
        print(f"  {ns}: {info['vector_count']:,} vectors")
    
    # Test search on properties
    if stats['total_vectors'] > 0:
        print("\n" + "="*70)
        print("TESTING SEARCH")
        print("="*70)
        
        rag = RAGService(data_dir)
        
        # Test query
        query = "3 BHK apartment near metro"
        print(f"\nQuery: '{query}'")
        
        # Try with FAISS only (use_fallback=True, but Pinecone might fail)
        results = rag.search(
            query=query,
            top_k=5,
            namespace="properties",
            use_cache=False,  # Don't cache for testing
            use_fallback=True
        )
        
        print(f"\nFound {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Score: {result.score:.3f}")
            print(f"   Title: {result.metadata.get('title', 'N/A')[:60]}")
            print(f"   Type: {result.metadata.get('property_type', 'N/A')}")
            print(f"   Bedrooms: {result.metadata.get('bedrooms', 'N/A')}")
            print(f"   Price: ₹{result.metadata.get('price', 0):,.0f}")
        
        print("\n" + "="*70)
        print("✅ FAISS TEST COMPLETE")
        print("="*70)
    else:
        print("\n⚠️  No vectors in FAISS store. Run export_to_faiss.py first.")


if __name__ == "__main__":
    test_faiss()
