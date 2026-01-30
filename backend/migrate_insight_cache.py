"""
Migration Script: Apply Insight Cache Tables to Valora Database
Run this once to add insight cache tables to existing database.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_service import DatabaseService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Apply insight cache migration to database."""
    logger.info("=" * 60)
    logger.info("Valora Insight Cache Migration")
    logger.info("=" * 60)
    
    db = DatabaseService()
    migration_file = Path(__file__).parent / "database" / "migrate_add_insight_cache.sql"
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    logger.info(f"Reading migration from: {migration_file}")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    try:
        with db.get_connection() as conn:
            logger.info("Executing migration SQL...")
            conn.executescript(migration_sql)
            logger.info("✓ Migration completed successfully!")
            
            # Verify tables were created
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('insight_cache', 'user_charges')")
            tables = cursor.fetchall()
            
            logger.info("\nVerification:")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table[0]}")
                count = cursor.fetchone()[0]
                logger.info(f"  ✓ Table '{table[0]}' exists (0 rows)")
            
            # Verify view was created
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='user_charge_summary'")
            if cursor.fetchone():
                logger.info("  ✓ View 'user_charge_summary' created")
            
            logger.info("\n" + "=" * 60)
            logger.info("Migration complete! Insight cache is ready.")
            logger.info("=" * 60)
            return True
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
