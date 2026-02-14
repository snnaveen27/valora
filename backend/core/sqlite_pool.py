"""
Thread-Local SQLite Connection Manager
Prevents "database is locked" errors under concurrent FastAPI requests.

Each thread gets its own persistent connection (reused across calls).
Connections use WAL mode for better concurrent read/write performance.
"""

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger("valora.sqlite_pool")


class ThreadLocalSQLite:
    """Thread-local SQLite connection manager.
    
    Usage:
        db = ThreadLocalSQLite("/path/to/database.db")
        conn = db.get()          # returns thread-local connection
        conn.execute("SELECT ...")
        conn.commit()
        # No need to close — reused across calls in the same thread.
        # Call db.close_all() on shutdown to clean up.
    """

    def __init__(self, db_path: str, init_sql: Optional[str] = None):
        self.db_path = str(db_path)
        self.init_sql = init_sql
        self._local = threading.local()
        self._all_connections = []
        self._lock = threading.Lock()

    def get(self) -> sqlite3.Connection:
        """Get or create a thread-local connection."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            return conn

        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # WAL mode: allows concurrent readers + single writer without blocking
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")  # wait up to 5s on locks

        if self.init_sql:
            conn.executescript(self.init_sql)
            conn.commit()

        self._local.conn = conn
        with self._lock:
            self._all_connections.append(conn)

        logger.debug(f"[SQLitePool] New connection for thread {threading.current_thread().name} → {self.db_path}")
        return conn

    def close_all(self):
        """Close all thread-local connections (call on app shutdown)."""
        with self._lock:
            for conn in self._all_connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._all_connections.clear()
        logger.info(f"[SQLitePool] All connections closed for {self.db_path}")


# ---------------------------------------------------------------------------
# Pre-configured pools for Valora databases
# ---------------------------------------------------------------------------
_pools = {}
_pool_lock = threading.Lock()


def get_pool(name: str, db_path: str, init_sql: Optional[str] = None) -> ThreadLocalSQLite:
    """Get or create a named connection pool."""
    with _pool_lock:
        if name not in _pools:
            _pools[name] = ThreadLocalSQLite(db_path, init_sql)
        return _pools[name]


def close_all_pools():
    """Close all pools (call on app shutdown)."""
    with _pool_lock:
        for name, pool in _pools.items():
            pool.close_all()
        _pools.clear()
    logger.info("[SQLitePool] All pools closed")
