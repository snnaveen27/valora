"""
Database Initialization Script
Run this to set up the PostgreSQL database with all tables and functions
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database.connection import db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize database with schema, tables, and functions"""
    
    logger.info("=" * 80)
    logger.info("Starting Database Initialization")
    logger.info("=" * 80)
    
    # Step 1: Test connection
    logger.info("\n1. Testing database connection...")
    if not db_manager.test_connection():
        logger.error("❌ Database connection failed! Please check your DATABASE_URL")
        return False
    logger.info("✅ Database connection successful")
    
    # Step 2: Initialize extensions
    logger.info("\n2. Initializing PostgreSQL extensions...")
    try:
        db_manager.initialize_extensions()
        logger.info("✅ Extensions initialized (PostGIS, pg_trgm)")
    except Exception as e:
        logger.error(f"❌ Failed to initialize extensions: {e}")
        return False
    
    # Step 3: Execute schema SQL files
    logger.info("\n3. Creating tables, views, and functions...")
    
    # Main schema file
    schema_file = Path(__file__).parent / "schemas" / "unified" / "schema.sql"
    if schema_file.exists():
        try:
            db_manager.execute_sql_file(str(schema_file))
            logger.info("✅ Main schema created successfully")
        except Exception as e:
            logger.warning(f"⚠️ Main schema may already exist or failed: {e}")
    else:
        logger.warning(f"⚠️ Main schema file not found: {schema_file}")
    
    # Users table migration
    users_migration = Path(__file__).parent / "migrations" / "001_create_users_table.sql"
    if users_migration.exists():
        try:
            db_manager.execute_sql_file(str(users_migration))
            logger.info("✅ Users table migration executed successfully")
        except Exception as e:
            logger.warning(f"⚠️ Users migration may already exist: {e}")
    
    # Step 4: Verify PostGIS
    logger.info("\n4. Verifying PostGIS installation...")
    if not db_manager.check_postgis():
        logger.error("❌ PostGIS not available")
        return False
    logger.info("✅ PostGIS is available")
    
    # Step 5: Create initial data directories
    logger.info("\n5. Creating data directories...")
    data_dirs = [
        Path("data/raw"),
        Path("data/processed"),
        Path("data/models"),
        Path("data/exports"),
    ]
    
    for dir_path in data_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Created directory: {dir_path}")
    
    # Step 6: Health check
    logger.info("\n6. Running health check...")
    health = db_manager.test_connection()
    if health:
        logger.info("✅ Database health check passed")
    else:
        logger.error("❌ Database health check failed")
        return False
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ Database initialization completed successfully!")
    logger.info("=" * 80)
    logger.info("\nNext steps:")
    logger.info("1. Add CSV files to data/raw/ directory")
    logger.info("2. Run ETL service to ingest data")
    logger.info("3. Start the FastAPI backend")
    
    return True


def reset_database():
    """Reset database (WARNING: Drops all tables!)"""
    logger.warning("=" * 80)
    logger.warning("⚠️  DATABASE RESET - THIS WILL DELETE ALL DATA")
    logger.warning("=" * 80)
    
    response = input("\nAre you sure you want to reset the database? Type 'yes' to confirm: ")
    
    if response.lower() != 'yes':
        logger.info("Database reset cancelled")
        return False
    
    logger.info("Dropping all tables...")
    try:
        db_manager.drop_all_tables()
        logger.info("✅ All tables dropped")
        
        # Recreate schema
        return initialize_database()
    except Exception as e:
        logger.error(f"❌ Failed to reset database: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize or reset the database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the database (WARNING: deletes all data)"
    )
    
    args = parser.parse_args()
    
    if args.reset:
        success = reset_database()
    else:
        success = initialize_database()
    
    sys.exit(0 if success else 1)
