"""
Valora Listings Schema
User-created property listings for sellers
"""

import sqlite3
from typing import Dict, Any, Optional, List
from datetime import datetime


class ListingsDB:
    """Listings database operations"""
    
    def __init__(self, db_path: str = None):
        from config import config
        self.db_path = db_path or str(config.DB_PATH.parent / "listings.db")
    
    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)
    
    def _ensure_schema(self, cursor: sqlite3.Cursor) -> None:
        """Create listings table if not exists"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                property_type TEXT,
                bedrooms TEXT,
                area_sqft INTEGER,
                price INTEGER,
                locality TEXT,
                description TEXT,
                images TEXT,
                status TEXT DEFAULT 'draft',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_listings_user 
            ON listings(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_listings_locality 
            ON listings(locality)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_listings_status 
            ON listings(status)
        """)


def create_listing(db: ListingsDB, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new listing"""
    import uuid
    conn = db._get_conn()
    cursor = conn.cursor()
    
    db._ensure_schema(cursor)
    
    listing_id = f"listing_{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO listings (
            id, user_id, property_type, bedrooms, area_sqft, price,
            locality, description, images, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        listing_id,
        data.get('user_id'),
        data.get('property_type'),
        data.get('bedrooms'),
        data.get('area_sqft'),
        data.get('price'),
        data.get('locality'),
        data.get('description'),
        ','.join(data.get('images', [])) if data.get('images') else '',
        data.get('status', 'draft'),
        now,
        now
    ))
    
    conn.commit()
    conn.close()
    
    return {
        **data,
        'id': listing_id,
        'status': data.get('status', 'draft'),
        'created_at': now,
        'updated_at': now
    }


def get_listings(db: ListingsDB, user_id: str) -> List[Dict[str, Any]]:
    """Get all listings for a user"""
    conn = db._get_conn()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM listings 
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [_row_to_listing(row) for row in rows]


def update_listing(db: ListingsDB, listing_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a listing"""
    conn = db._get_conn()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    updates = []
    values = []
    
    for field in ['property_type', 'bedrooms', 'area_sqft', 'price', 'locality', 'description', 'images', 'status']:
        if field in data:
            updates.append(f"{field} = ?")
            val = data[field]
            if field == 'images' and isinstance(val, list):
                val = ','.join(val)
            values.append(val)
    
    if not updates:
        return None
    
    values.append(listing_id)
    values.append(now)
    
    query = f"UPDATE listings SET {', '.join(updates)}, updated_at = ? WHERE id = ?"
    cursor.execute(query, values)
    
    conn.commit()
    conn.close()
    
    return get_listing_by_id(db, listing_id)


def delete_listing(db: ListingsDB, listing_id: str) -> bool:
    """Delete a listing"""
    conn = db._get_conn()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM listings WHERE id = ?", (listing_id,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    
    return deleted


def get_listing_by_id(db: ListingsDB, listing_id: str) -> Optional[Dict[str, Any]]:
    """Get a single listing by ID"""
    conn = db._get_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
    row = cursor.fetchone()
    conn.close()
    
    return _row_to_listing(row) if row else None


def _row_to_listing(row: tuple) -> Dict[str, Any]:
    """Convert database row to listing dict"""
    if not row:
        return None
    
    return {
        'id': row[0],
        'user_id': row[1],
        'property_type': row[2],
        'bedrooms': row[3],
        'area_sqft': row[4],
        'price': row[5],
        'locality': row[6],
        'description': row[7],
        'images': row[8].split(',') if row[8] else [],
        'status': row[9],
        'created_at': row[10],
        'updated_at': row[11],
    }