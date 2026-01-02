"""
PostgreSQL Database Connection Manager
Handles connection pooling and session management
"""

import os
from typing import Generator, Optional
from contextlib import contextmanager
import logging
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geometry
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

load_dotenv(override=True)
logger = logging.getLogger(__name__)

# Database configuration

def _clean_env_value(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value.strip()


def _ensure_sslmode_require(db_url: str) -> str:
    try:
        parsed = urlparse(db_url)
        host = (parsed.hostname or "").lower()
        if "supabase" not in host:
            return db_url

        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if not query.get("sslmode"):
            query["sslmode"] = "require"
            parsed = parsed._replace(query=urlencode(query))
            return urlunparse(parsed)
        return db_url
    except Exception:
        return db_url


_raw_database_url = _clean_env_value(os.getenv("DATABASE_URL_POOLER")) or _clean_env_value(os.getenv("DATABASE_URL"))
DATABASE_URL = _raw_database_url or "postgresql://postgres:postgres@localhost:5432/realestate"
DATABASE_URL = _ensure_sslmode_require(DATABASE_URL)

_parsed_db_url = urlparse(DATABASE_URL)
_db_host = (_parsed_db_url.hostname or "").lower()
_connect_args = {
    "options": "-c timezone=utc",
    "connect_timeout": 10
}
if "supabase" in _db_host:
    _connect_args["sslmode"] = "require"

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=pool.QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=False,          # Set to True for SQL query logging
    connect_args=_connect_args
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """Get a new session (caller must close)"""
        return self.SessionLocal()
    
    def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            with self.engine.connect() as conn:
                result = conn.exec_driver_sql("SELECT 1")
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def check_postgis(self) -> bool:
        """Check if PostGIS extension is available"""
        try:
            with self.engine.connect() as conn:
                result = conn.exec_driver_sql(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'postgis')"
                )
                return result.scalar()
        except Exception as e:
            logger.error(f"PostGIS check failed: {e}")
            return False
    
    def initialize_extensions(self):
        """Initialize required PostgreSQL extensions"""
        try:
            with self.engine.connect() as conn:
                conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS postgis")
                conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS postgis_topology")
                conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pgcrypto")
                conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
                conn.commit()
            logger.info("PostgreSQL extensions initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize extensions: {e}")
            raise
    
    def create_all_tables(self):
        """Create all tables defined in models"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("All database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_all_tables(self):
        """Drop all tables (use with caution!)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    def execute_sql_file(self, filepath: str):
        """Execute SQL file (for schema initialization)"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            # Use raw connection to execute the full script (handles functions/triggers)
            raw_conn = self.engine.raw_connection()
            try:
                cursor = raw_conn.cursor()
                cursor.execute(sql)
                raw_conn.commit()
            finally:
                try:
                    cursor.close()
                except Exception:
                    pass
                raw_conn.close()
            
            logger.info(f"Successfully executed SQL file: {filepath}")
        except Exception as e:
            logger.error(f"Failed to execute SQL file {filepath}: {e}")
            raise
    
    def vacuum_analyze(self):
        """Run VACUUM ANALYZE for performance optimization"""
        try:
            # Need isolation level autocommit for VACUUM
            conn = self.engine.raw_connection()
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            cursor.execute("VACUUM ANALYZE")
            cursor.close()
            conn.close()
            logger.info("VACUUM ANALYZE completed")
        except Exception as e:
            logger.error(f"VACUUM ANALYZE failed: {e}")
    
    def refresh_materialized_views(self):
        """Refresh all materialized views"""
        try:
            with self.engine.connect() as conn:
                conn.exec_driver_sql("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_city_summary")
                conn.commit()
            logger.info("Materialized views refreshed")
        except Exception as e:
            logger.error(f"Failed to refresh materialized views: {e}")


# Singleton instance
db_manager = DatabaseManager()


# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# Event listeners for connection management
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Set connection parameters on connect"""
    cursor = dbapi_conn.cursor()
    cursor.execute("SET timezone='UTC'")
    cursor.execute("SET statement_timeout='30000'")  # 30 second timeout
    cursor.close()


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log connection checkout (for debugging)"""
    logger.debug("Connection checked out from pool")


# Health check function
def health_check() -> dict:
    """Check database health"""
    try:
        is_connected = db_manager.test_connection()
        has_postgis = db_manager.check_postgis()
        # Check other extensions
        with engine.connect() as conn:
            has_vector = conn.exec_driver_sql(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            ).scalar()
            has_pgcrypto = conn.exec_driver_sql(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto')"
            ).scalar()
        
        return {
            "status": "healthy" if is_connected else "unhealthy",
            "database_connected": is_connected,
            "postgis_enabled": has_postgis,
            "vector_enabled": has_vector,
            "pgcrypto_enabled": has_pgcrypto,
            "pool_size": engine.pool.size(),
            "checked_out_connections": engine.pool.checkedout()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
