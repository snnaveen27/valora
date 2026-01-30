"""
Migrate pricing configuration from JSON to Database
Run this once to initialize the database with current pricing
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from database.pricing_db import get_pricing_db

def migrate():
    """Migrate pricing config from JSON to database."""
    pricing_db = get_pricing_db()
    
    # Try to migrate from JSON if exists
    json_path = Path(__file__).parent / "config" / "pricing_config.json"
    
    if json_path.exists():
        print(f"[MIGRATION] Found JSON config at {json_path}")
        success = pricing_db.migrate_from_json(str(json_path))
        if success:
            print("[MIGRATION] ✅ Successfully migrated pricing config to database")
            print(f"[MIGRATION] Database location: {pricing_db.db_path}")
        else:
            print("[MIGRATION] ❌ Failed to migrate from JSON")
            return False
    else:
        print("[MIGRATION] No JSON config found, initializing with defaults")
        config = pricing_db._get_default_config()
        success = pricing_db.save_config(config, updated_by="initial_setup")
        if success:
            print("[MIGRATION] ✅ Initialized database with default config")
        else:
            print("[MIGRATION] ❌ Failed to initialize database")
            return False
    
    # Verify
    config = pricing_db.get_config()
    print(f"\n[VERIFICATION] Loaded config from database:")
    print(f"  - Action costs: {len(config.get('action_costs', {}))} actions")
    print(f"  - Tier limits: {list(config.get('tier_monthly_limits', {}).keys())}")
    print(f"  - Last updated: {config.get('last_updated')}")
    print(f"  - Updated by: {config.get('updated_by')}")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("PRICING DATABASE MIGRATION")
    print("=" * 60)
    
    success = migrate()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("\n📌 SECURITY NOTE:")
        print("   - Pricing now stored in SQLite database (pricing.db)")
        print("   - All changes logged with audit trail")
        print("   - Database location: backend/database/pricing.db")
        print("   - JSON file can be deleted (no longer used)")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
