"""
Multi-Database Connection Manager
- Core DB: properties, transactions, market stats (no PostGIS, no vectors)
- Spatial DB: PostGIS features, POIs, spatial calculations
- Vector DB: pgvector embeddings and similarity search
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

logger = logging.getLogger(__name__)

load_dotenv(override=True)


def _clean_env_value(value: str | None) -> str | None:
    if not value:
        return value
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1]
    return v.strip()


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

# Environment variables (prioritize DATABASE_URL for cloud setup)
# For cloud (Supabase), all three point to same database with different schemas
DATABASE_URL = _clean_env_value(os.getenv("DATABASE_URL_POOLER")) or _clean_env_value(os.getenv("DATABASE_URL"))
if DATABASE_URL:
    DATABASE_URL = _ensure_sslmode_require(DATABASE_URL)

# If DATABASE_URL is set (cloud setup), use it for all connections
# Otherwise fall back to separate local databases
if DATABASE_URL and "supabase.co" in DATABASE_URL:
    # Cloud setup: single Supabase database with multiple schemas
    CORE_DATABASE_URL = DATABASE_URL
    SPATIAL_DATABASE_URL = DATABASE_URL
    VECTOR_DATABASE_URL = DATABASE_URL
    logger.info("Using cloud database (Supabase) for all connections")
else:
    # Local setup: separate databases
    CORE_DATABASE_URL = os.getenv(
        "CORE_DATABASE_URL", 
        DATABASE_URL or "postgresql://postgres:postgres@localhost:5432/realestate_core"
    )
    SPATIAL_DATABASE_URL = os.getenv(
        "SPATIAL_DATABASE_URL", 
        "postgresql://postgres:postgres@localhost:5432/realestate_spatial"
    )
    VECTOR_DATABASE_URL = os.getenv(
        "VECTOR_DATABASE_URL", 
        "postgresql://postgres:postgres@localhost:5432/realestate_vectors"
    )
    logger.info("Using local multi-database setup")


def _create_engine(url: str):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    connect_args = {"options": "-c timezone=utc", "connect_timeout": 10}
    if "supabase" in host:
        connect_args["sslmode"] = "require"
    return create_engine(
        url,
        poolclass=pool.QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
        connect_args=connect_args,
    )


engine_core = _create_engine(CORE_DATABASE_URL)
engine_spatial = _create_engine(SPATIAL_DATABASE_URL)
engine_vector = _create_engine(VECTOR_DATABASE_URL)

SessionCore = sessionmaker(autocommit=False, autoflush=False, bind=engine_core)
SessionSpatial = sessionmaker(autocommit=False, autoflush=False, bind=engine_spatial)
SessionVector = sessionmaker(autocommit=False, autoflush=False, bind=engine_vector)


class MultiDBManager:
    def __init__(self):
        self.engine_core = engine_core
        self.engine_spatial = engine_spatial
        self.engine_vector = engine_vector
        self.SessionCore = SessionCore
        self.SessionSpatial = SessionSpatial
        self.SessionVector = SessionVector

    @contextmanager
    def core(self) -> Generator[Session, None, None]:
        session = self.SessionCore()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def spatial(self) -> Generator[Session, None, None]:
        session = self.SessionSpatial()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def vector(self) -> Generator[Session, None, None]:
        session = self.SessionVector()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def init_core_extensions(self):
        with self.engine_core.connect() as conn:
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            conn.commit()

    def init_spatial_extensions(self):
        with self.engine_spatial.connect() as conn:
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS postgis")
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS postgis_topology")
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            conn.commit()

    def init_vector_extensions(self):
        with self.engine_vector.connect() as conn:
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            conn.commit()

    def execute_sql_file(self, which: str, filepath: str):
        engine_map = {
            "core": self.engine_core,
            "spatial": self.engine_spatial,
            "vector": self.engine_vector,
        }
        engine = engine_map[which]
        raw_conn = engine.raw_connection()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                sql = f.read()
            cursor = raw_conn.cursor()
            cursor.execute(sql)
            raw_conn.commit()
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            raw_conn.close()


mdb = MultiDBManager()


@event.listens_for(engine_core, "connect")
def _core_connect(dbapi_conn, connection_record):
    cur = dbapi_conn.cursor()
    cur.execute("SET timezone='UTC'")
    cur.execute("SET statement_timeout='30000'")
    cur.close()


@event.listens_for(engine_spatial, "connect")
def _spatial_connect(dbapi_conn, connection_record):
    cur = dbapi_conn.cursor()
    cur.execute("SET timezone='UTC'")
    cur.execute("SET statement_timeout='60000'")
    cur.close()


@event.listens_for(engine_vector, "connect")
def _vector_connect(dbapi_conn, connection_record):
    cur = dbapi_conn.cursor()
    cur.execute("SET timezone='UTC'")
    cur.execute("SET statement_timeout='30000'")
    cur.close()
