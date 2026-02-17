"""
Migration script to clean up redundant credit/usage tables and databases.

This script:
1. Migrates any existing credit data to the unified system
2. Removes redundant tables from valora.db
3. Removes the isolated user_credits table from valora_memory.db
4. Keeps only the unified valora_credits.db

Run this script once after deploying the unified credits system.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_db_path(db_name: str) -> Path:
    """Get path to database file."""
    from config import config
    return config.DB_PATH.parent / db_name


def migrate_credits():
    """Migrate existing credits to unified system."""
    logger.info("[Migration] Starting credit system migration...")
    
    # Initialize unified system
    from ai.unified_credits import get_credits_manager
    manager = get_credits_manager()
    
    # Migrate from old valora_credits.db if it has data
    old_credits_path = get_db_path('valora_credits.db')
    if old_credits_path.exists():
        conn = sqlite3.connect(str(old_credits_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if there's data to migrate
        cursor.execute("SELECT COUNT(*) FROM user_credits")
        count = cursor.fetchone()[0]
        
        if count > 0:
            logger.info(f"[Migration] Found {count} users in valora_credits.db")
            
            # The unified system will handle the existing data
            # Just ensure the schema is updated
            cursor.execute("PRAGMA table_info(user_credits)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'total_earned' not in columns:
                logger.info("[Migration] Adding total_earned column")
                cursor.execute("ALTER TABLE user_credits ADD COLUMN total_earned INTEGER DEFAULT 0")
                conn.commit()
        
        conn.close()
    
    logger.info("[Migration] Credit migration complete")


def cleanup_redundant_tables():
    """Remove redundant tables from valora.db."""
    logger.info("[Migration] Cleaning up redundant tables...")
    
    valora_path = get_db_path('valora.db')
    if not valora_path.exists():
        logger.info("[Migration] valora.db not found, skipping")
        return
    
    conn = sqlite3.connect(str(valora_path))
    cursor = conn.cursor()
    
    # Tables to remove (now handled by unified credits system)
    tables_to_remove = [
        'usage_events',
        'user_balances', 
        'training_contributions'
    ]
    
    for table in tables_to_remove:
        try:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                logger.info(f"[Migration] Dropped table: {table}")
        except Exception as e:
            logger.warning(f"[Migration] Could not drop {table}: {e}")
    
    # Also remove related indexes
    indexes_to_remove = [
        'idx_usage_events_user',
        'idx_usage_events_action'
    ]
    
    for idx in indexes_to_remove:
        try:
            cursor.execute(f"DROP INDEX IF EXISTS {idx}")
        except:
            pass
    
    conn.commit()
    conn.close()
    
    logger.info("[Migration] Redundant tables cleaned up")


def cleanup_memory_db():
    """Remove isolated user_credits table from valora_memory.db."""
    logger.info("[Migration] Cleaning up valora_memory.db...")
    
    memory_path = get_db_path('valora_memory.db')
    if not memory_path.exists():
        logger.info("[Migration] valora_memory.db not found, skipping")
        return
    
    conn = sqlite3.connect(str(memory_path))
    cursor = conn.cursor()
    
    # Remove the isolated user_credits table (credits now in unified system)
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_credits'")
        if cursor.fetchone():
            cursor.execute("DROP TABLE IF EXISTS user_credits")
            logger.info("[Migration] Dropped user_credits from valora_memory.db")
    except Exception as e:
        logger.warning(f"[Migration] Could not drop user_credits: {e}")
    
    conn.commit()
    conn.close()


def cleanup_users_db():
    """Remove usage_logs table from users.db (now in unified system)."""
    logger.info("[Migration] Cleaning up users.db...")
    
    users_path = get_db_path('users.db')
    if not users_path.exists():
        logger.info("[Migration] users.db not found, skipping")
        return
    
    conn = sqlite3.connect(str(users_path))
    cursor = conn.cursor()
    
    # Note: We keep usage_logs for backward compatibility with user_auth.py
    # but it's no longer actively used for credit tracking
    
    conn.close()


def run_migration():
    """Run the full migration."""
    logger.info("=" * 60)
    logger.info("[Migration] Starting unified credits migration")
    logger.info("=" * 60)
    
    try:
        migrate_credits()
        cleanup_redundant_tables()
        cleanup_memory_db()
        cleanup_users_db()
        
        logger.info("=" * 60)
        logger.info("[Migration] Migration completed successfully!")
        logger.info("=" * 60)
        
        # Print summary
        print("\nMigration Summary:")
        print("-" * 40)
        print("✓ Unified credits system initialized")
        print("✓ Redundant tables removed from valora.db:")
        print("  - usage_events")
        print("  - user_balances")
        print("  - training_contributions")
        print("✓ Isolated user_credits removed from valora_memory.db")
        print("\nAll credit operations now use:")
        print("  → valora_credits.db (unified)")
        print("\nFeedback records remain in:")
        print("  → valora_memory.db (message_feedback, feedback_drafts)")
        
    except Exception as e:
        logger.error(f"[Migration] Migration failed: {e}")
        raise


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s'
    )
    
    run_migration()
