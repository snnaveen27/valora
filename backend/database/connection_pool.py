"""
SQLite Connection Pool for Valora
Thread-safe connection pooling with WAL mode optimization
"""

import sqlite3
import threading
import queue
from contextlib import contextmanager
from typing import Optional, Dict, Any
from pathlib import Path

class SQLiteConnectionPool:
    """
    Thread-safe SQLite connection pool
    
    Features:
    - Connection pooling (max 10 connections)
    - WAL mode for concurrent reads/writes
    - Automatic PRAGMA optimization
    - Thread-local connections
    """
    
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool = queue.Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._connection_count = 0
        self._local = threading.local()
        
        # Initialize database with optimizations
        self._init_database()
        
    def _init_database(self):
        """Initialize database with performance settings"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        # Performance PRAGMAs
        conn.execute("PRAGMA journal_mode=WAL")          # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")         # Balance safety/speed
        conn.execute("PRAGMA cache_size=-64000")          # 64MB cache
        conn.execute("PRAGMA page_size=4096")             # Optimal for SSDs
        conn.execute("PRAGMA temp_store=memory")          # Memory temp tables
        conn.execute("PRAGMA mmap_size=30000000000")      # Memory map (30GB limit)
        
        conn.commit()
        conn.close()
        print(f"[SQLitePool] Initialized with WAL mode: {self.db_path}")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new optimized connection"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        # Apply per-connection settings
        conn.execute("PRAGMA foreign_keys=ON")
        
        return conn
    
    def get_connection(self) -> sqlite3.Connection:
        """Get connection from pool or create new one"""
        # Check thread-local
        if hasattr(self._local, 'connection') and self._local.connection:
            return self._local.connection
        
        try:
            # Try to get from pool
            conn = self._pool.get(block=False)
            self._local.connection = conn
            return conn
        except queue.Empty:
            # Create new if under limit
            with self._lock:
                if self._connection_count < self.max_connections:
                    conn = self._create_connection()
                    self._connection_count += 1
                    self._local.connection = conn
                    return conn
                else:
                    # Wait for available connection
                    conn = self._pool.get(block=True, timeout=5.0)
                    self._local.connection = conn
                    return conn
    
    def release_connection(self, conn: sqlite3.Connection):
        """Return connection to pool"""
        try:
            self._pool.put(conn, block=False)
        except queue.Full:
            # Pool is full, close connection
            conn.close()
            with self._lock:
                self._connection_count -= 1
    
    def close_all(self):
        """Close all connections in pool"""
        while not self._pool.empty():
            try:
                conn = self._pool.get(block=False)
                conn.close()
            except queue.Empty:
                break
        
        with self._lock:
            self._connection_count = 0
    
    @contextmanager
    def connection(self):
        """Context manager for safe connection handling"""
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        finally:
            if conn:
                self.release_connection(conn)
    
    def execute(self, query: str, params: tuple = ()) -> list:
        """Execute query with automatic connection handling"""
        with self.connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
    
    def execute_many(self, query: str, params_list: list) -> int:
        """Execute many with automatic connection handling"""
        with self.connection() as conn:
            cursor = conn.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            "db_path": self.db_path,
            "max_connections": self.max_connections,
            "pool_size": self._pool.qsize(),
            "active_connections": self._connection_count,
            "available_connections": self._pool.qsize()
        }


# Global pool registry
_pools: Dict[str, SQLiteConnectionPool] = {}

def get_pool(db_path: str, max_connections: int = 10) -> SQLiteConnectionPool:
    """Get or create connection pool for database"""
    if db_path not in _pools:
        _pools[db_path] = SQLiteConnectionPool(db_path, max_connections)
    return _pools[db_path]

def close_all_pools():
    """Close all connection pools"""
    for pool in _pools.values():
        pool.close_all()
    _pools.clear()
    print("[SQLitePool] All pools closed")


def get_valora_pool() -> SQLiteConnectionPool:
    """Get pool for main Valora database"""
    # Find the database file
    possible_paths = [
        "backend/valora.db",
        "valora.db",
        "backend/database/valora.db",
        "database/valora.db"
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            return get_pool(path, max_connections=10)
    
    # Default to first path
    return get_pool(possible_paths[0], max_connections=10)
