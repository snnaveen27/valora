"""
Setup Users Database
Quick script to initialize the users table in PostgreSQL
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_users_table():
    """Setup the users table in PostgreSQL"""
    
    logger.info("=" * 60)
    logger.info("Setting up Users Table")
    logger.info("=" * 60)
    
    try:
        from backend.database.connection import db_manager
        
        # Test connection
        logger.info("\n1. Testing database connection...")
        if not db_manager.test_connection():
            logger.error("❌ Database connection failed!")
            logger.info("\nMake sure PostgreSQL is running and DATABASE_URL is set in .env")
            logger.info("Example: DATABASE_URL=postgresql://postgres:password@localhost:5432/realestate")
            return False
        
        logger.info("✅ Database connection successful")
        
        # Execute users migration
        logger.info("\n2. Creating users table...")
        migration_file = Path(__file__).parent.parent / "backend" / "database" / "migrations" / "001_create_users_table.sql"
        
        if not migration_file.exists():
            logger.error(f"❌ Migration file not found: {migration_file}")
            return False
        
        try:
            db_manager.execute_sql_file(str(migration_file))
            logger.info("✅ Users table created successfully")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✅ Users table already exists")
            else:
                logger.warning(f"⚠️ Migration warning: {e}")
        
        # Verify table exists
        logger.info("\n3. Verifying users table...")
        try:
            with db_manager.engine.connect() as conn:
                result = conn.exec_driver_sql(
                    "SELECT COUNT(*) FROM users"
                )
                count = result.scalar()
                logger.info(f"✅ Users table verified - {count} users found")
        except Exception as e:
            logger.error(f"❌ Could not verify users table: {e}")
            return False
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Users database setup complete!")
        logger.info("=" * 60)
        logger.info("\nDefault users created:")
        logger.info("  - Admin: naveen.sandcube@gmail.com / admin123")
        logger.info("  - Demo:  demo@valora.ai / demo123")
        logger.info("\nYou can now register new users through the frontend.")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.info("\nMake sure all dependencies are installed:")
        logger.info("  pip install sqlalchemy psycopg2-binary python-dotenv")
        return False
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return False


def check_env():
    """Check if .env file exists with required variables"""
    env_file = Path(__file__).parent.parent / ".env"
    
    if not env_file.exists():
        logger.warning("⚠️ No .env file found. Creating sample...")
        sample_env = """# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/realestate

# JWT Secret (change in production!)
JWT_SECRET=valora-secret-key-change-in-production

# API Configuration
VITE_API_URL=http://localhost:8000

# Mappls API Key
VITE_MAPPLS_API_KEY=your-mappls-api-key

# Google OAuth (optional)
VITE_GOOGLE_CLIENT_ID=your-google-client-id
"""
        with open(env_file, 'w') as f:
            f.write(sample_env)
        logger.info(f"✅ Sample .env file created at {env_file}")
        logger.info("Please update it with your actual database credentials.")
        return False
    
    return True


if __name__ == "__main__":
    if not check_env():
        logger.info("\nPlease configure your .env file and run again.")
        sys.exit(1)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    success = setup_users_table()
    sys.exit(0 if success else 1)
