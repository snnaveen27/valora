"""
Incremental Pinecone Indexer
Only indexes new/updated records since last sync
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_service import DatabaseService
from ai.rag_service import RAGService
from backend.config import config
from dotenv import load_dotenv

load_dotenv()


class IncrementalIndexer:
    """Manages incremental updates to Pinecone index."""
    
    def __init__(self, db_path: Path, data_dir: Path):
        self.db = DatabaseService(str(db_path))
        self.rag = RAGService(data_dir)
        self.state_file = data_dir / '.pinecone_sync_state.txt'
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """Get timestamp of last successful sync."""
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r') as f:
                timestamp_str = f.read().strip()
                return datetime.fromisoformat(timestamp_str)
        except:
            return None
    
    def save_sync_time(self, timestamp: datetime = None):
        """Save current sync timestamp."""
        if timestamp is None:
            timestamp = datetime.now()
        
        with open(self.state_file, 'w') as f:
            f.write(timestamp.isoformat())
    
    def index_new_properties(self, since: Optional[datetime] = None) -> int:
        """Index properties created/updated since last sync."""
        
        if since is None:
            since = self.get_last_sync_time()
        
        if since is None:
            print("[INFO] No previous sync found. Use full indexing script.")
            return 0
        
        print(f"[INFO] Indexing properties updated since {since.isoformat()}")
        
        # Query for new/updated properties
        query = """
            SELECT * FROM properties 
            WHERE updated_at > ? OR created_at > ?
            ORDER BY updated_at DESC
        """
        
        since_str = since.isoformat()
        properties = self.db.execute(query, (since_str, since_str))
        
        if not properties:
            print("[INFO] No new properties to index")
            return 0
        
        print(f"[INFO] Found {len(properties)} new/updated properties")
        
        # Index them
        vectors = []
        count = 0
        
        for prop in properties:
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
            
            prop_id = prop.get("property_id", f"prop_{count}")
            
            vectors.append({
                "id": prop_id,
                "values": self.rag.embed_single(text),
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
            
            # Batch upsert every 50 vectors
            if len(vectors) >= 50:
                self.rag.upsert_vectors(vectors, namespace="properties")
                vectors = []
                print(f"  Indexed {count} properties...")
        
        # Upsert remaining
        if vectors:
            self.rag.upsert_vectors(vectors, namespace="properties")
        
        print(f"[OK] Indexed {count} new/updated properties")
        
        # Save sync timestamp
        self.save_sync_time()
        
        return count
    
    def index_new_pois(self, since: Optional[datetime] = None) -> int:
        """Index POIs created/updated since last sync."""
        
        if since is None:
            since = self.get_last_sync_time()
        
        if since is None:
            return 0
        
        query = """
            SELECT * FROM pois 
            WHERE created_at > ?
            ORDER BY created_at DESC
        """
        
        pois = self.db.execute(query, (since.isoformat(),))
        
        if not pois:
            return 0
        
        print(f"[INFO] Indexing {len(pois)} new POIs")
        
        vectors = []
        count = 0
        
        for poi in pois:
            text = f"{poi.get('name', '')} {poi.get('category', '')} {poi.get('subcategory', '')}"
            
            if not text.strip():
                continue
            
            lat = poi.get("latitude", 0.0) or 0.0
            lng = poi.get("longitude", 0.0) or 0.0
            
            vectors.append({
                "id": poi.get("poi_id", f"poi_{count}"),
                "values": self.rag.embed_single(text),
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
                self.rag.upsert_vectors(vectors, namespace="spatial")
                vectors = []
        
        if vectors:
            self.rag.upsert_vectors(vectors, namespace="spatial")
        
        print(f"[OK] Indexed {count} new POIs")
        return count
    
    def run_incremental_sync(self):
        """Run full incremental sync for all data types."""
        print("\n" + "="*70)
        print("INCREMENTAL PINECONE SYNC")
        print("="*70)
        
        last_sync = self.get_last_sync_time()
        if last_sync:
            print(f"Last sync: {last_sync.isoformat()}")
        else:
            print("No previous sync found - run full indexing first")
            return
        
        total = 0
        total += self.index_new_properties(last_sync)
        total += self.index_new_pois(last_sync)
        
        print("\n" + "="*70)
        print(f"SYNC COMPLETE: {total} new records indexed")
        print("="*70)


def main():
    """Run incremental sync."""
    db_path = config.DB_PATH
    project_root = Path(__file__).parent.parent
    data_dir = project_root / 'storage'
    
    indexer = IncrementalIndexer(db_path, data_dir)
    indexer.run_incremental_sync()


if __name__ == "__main__":
    main()
