"""
Initialize Supabase Database with Valora Schemas
Run this script after creating your Supabase project to set up all tables and extensions.

Prerequisites:
1. Create Supabase project at https://supabase.com
2. Update .env with your Supabase credentials
3. Install dependencies: pip install python-dotenv sqlalchemy psycopg2-binary

Usage:
    python scripts/init_supabase.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load environment variables
load_dotenv()

def init_supabase():
    """Initialize Supabase database with all schemas"""
    
    # Get database URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url or '[PROJECT-REF]' in db_url or '[YOUR_SUPABASE_PASSWORD]' in db_url:
        print("❌ ERROR: Please update DATABASE_URL in .env with your Supabase credentials")
        print("\n📝 Steps to get credentials:")
        print("1. Go to https://app.supabase.com")
        print("2. Select your project")
        print("3. Go to Settings → Database")
        print("4. Copy the Connection String (connection pooling)")
        print("5. Replace [password] with your database password")
        print("6. Update DATABASE_URL in .env")
        return False
    
    print("🚀 Initializing Supabase Database...")
    print(f"📍 Connecting to: {db_url.split('@')[1].split('/')[0] if '@' in db_url else 'database'}")
    
    try:
        engine = create_engine(db_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL: {version.split(',')[0]}")
        
        # Enable extensions
        print("\n📦 Enabling PostgreSQL Extensions...")
        extensions = [
            ('postgis', 'Spatial database functionality'),
            ('postgis_topology', 'Topology support'),
            ('vector', 'pgvector for embeddings'),
            ('pg_trgm', 'Fuzzy text search'),
            ('uuid-ossp', 'UUID generation')
        ]
        
        with engine.connect() as conn:
            for ext_name, description in extensions:
                try:
                    conn.execute(text(f"CREATE EXTENSION IF NOT EXISTS \"{ext_name}\""))
                    conn.commit()
                    print(f"  ✅ {ext_name} - {description}")
                except Exception as e:
                    if 'does not exist' in str(e):
                        print(f"  ⚠️  {ext_name} - Not available (skip)")
                    else:
                        print(f"  ⚠️  {ext_name} - {str(e)}")
        
        # Execute schema files
        schema_files = [
            ('backend/database/migrations/001_create_users_table.sql', 'Users & Authentication'),
            ('backend/database/schemas/unified/schema.sql', 'Unified Schema (Properties, Transactions)'),
            ('backend/database/schemas/city_intel/schema_city_intel.sql', 'City Intelligence Tables'),
            ('backend/database/schemas/data_layer/schema_data_layer.sql', 'Data Layer Tables'),
        ]
        
        print("\n📋 Creating Database Tables...")
        for schema_file, description in schema_files:
            schema_path = ROOT / schema_file
            
            if not schema_path.exists():
                print(f"  ⚠️  Skipped: {description} (file not found)")
                continue
            
            print(f"\n  📄 Executing: {description}")
            with open(schema_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            
            with engine.connect() as conn:
                for i, statement in enumerate(statements, 1):
                    if not statement:
                        continue
                    try:
                        conn.execute(text(statement))
                        conn.commit()
                    except Exception as e:
                        if 'already exists' in str(e).lower():
                            pass  # Table already exists, skip
                        else:
                            print(f"     ⚠️  Statement {i} warning: {str(e)[:100]}")
            
            print(f"  ✅ {description} - Complete")
        
        # Verify tables created
        print("\n🔍 Verifying Tables...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f"✅ Created {len(tables)} tables:")
                for table in tables[:10]:  # Show first 10
                    print(f"   • {table}")
                if len(tables) > 10:
                    print(f"   ... and {len(tables) - 10} more")
            else:
                print("⚠️  No tables found (may need manual verification)")
        
        print("\n" + "="*60)
        print("✅ Supabase Database Initialization Complete!")
        print("="*60)
        print("\n📝 Next Steps:")
        print("1. Verify tables in Supabase Dashboard → Table Editor")
        print("2. Seed sample data: python scripts/seed_data.py")
        print("3. Start backend: cd backend && python main.py")
        print("4. Start frontend: npm run dev")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\n💡 Troubleshooting:")
        print("1. Check DATABASE_URL in .env is correct")
        print("2. Verify Supabase project is active")
        print("3. Check database password is correct")
        print("4. Ensure network connection is stable")
        return False

if __name__ == '__main__':
    success = init_supabase()
    sys.exit(0 if success else 1)
