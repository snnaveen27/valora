"""
Initialize multi-database setup:
- Core DB (no PostGIS, no vectors)
- Spatial DB (PostGIS)
- Vector DB (pgvector)

Requires the following env vars in .env or environment:
  CORE_DATABASE_URL=postgresql://postgres:password@localhost:5432/realestate_core
  SPATIAL_DATABASE_URL=postgresql://postgres:password@localhost:5432/realestate_spatial
  VECTOR_DATABASE_URL=postgresql://postgres:password@localhost:5432/realestate_vectors
"""

import sys
import logging
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy.engine.url import make_url

# Ensure repository root is on sys.path when running as a script
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database.multiconnection import mdb, CORE_DATABASE_URL, SPATIAL_DATABASE_URL, VECTOR_DATABASE_URL

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _create_db_if_missing(db_url: str):
    """Create a database if it does not exist using superuser connection to 'postgres' db."""
    url = make_url(db_url)
    dbname = url.database
    user = url.username or 'postgres'
    password = url.password or ''
    host = url.host or 'localhost'
    port = url.port or 5432

    # Connect to default 'postgres' database
    conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host, port=port)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        exists = cur.fetchone()
        if not exists:
            logger.info(f"Creating database {dbname}...")
            cur.execute(f'CREATE DATABASE "{dbname}"')
        else:
            logger.info(f"Database {dbname} already exists")
    finally:
        cur.close()
        conn.close()


def initialize():
    base = Path(__file__).parent
    core_sql = base / 'schemas' / 'core' / 'schema_core.sql'
    spatial_sql = base / 'schemas' / 'spatial' / 'schema_spatial.sql'
    vector_sql = base / 'schemas' / 'vector' / 'schema_vector.sql'

    if not core_sql.exists() or not spatial_sql.exists() or not vector_sql.exists():
        logger.error('Schema files missing. Ensure schema_core.sql, schema_spatial.sql, schema_vector.sql exist.')
        return False

    logger.info('Initializing multi-database setup...')

    # Ensure databases exist
    logger.info('Ensuring databases exist (core, spatial, vector)...')
    _create_db_if_missing(CORE_DATABASE_URL)
    _create_db_if_missing(SPATIAL_DATABASE_URL)
    _create_db_if_missing(VECTOR_DATABASE_URL)

    # Initialize extensions per DB
    logger.info('Initializing core DB extensions...')
    mdb.init_core_extensions()

    logger.info('Initializing spatial DB extensions...')
    mdb.init_spatial_extensions()

    # Vector extension is optional; skip if not available
    vector_ok = True
    try:
        logger.info('Initializing vector DB extensions...')
        mdb.init_vector_extensions()
    except Exception as e:
        logger.warning(f"Vector extension not available, skipping vector DB init: {e}")
        vector_ok = False

    # Execute schemas
    logger.info('Creating core schema...')
    mdb.execute_sql_file('core', str(core_sql))

    logger.info('Creating spatial schema...')
    mdb.execute_sql_file('spatial', str(spatial_sql))

    if vector_ok:
        logger.info('Creating vector schema...')
        mdb.execute_sql_file('vector', str(vector_sql))
    else:
        logger.info('Skipping vector schema because pgvector extension is unavailable')

    logger.info('Multi-database initialization completed successfully')
    return True


if __name__ == '__main__':
    ok = initialize()
    sys.exit(0 if ok else 1)
