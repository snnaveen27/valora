"""
Pricing Configuration Database
Stores all pricing config in database instead of JSON files for security.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class PricingDatabase:
    """
    Database storage for pricing configuration.
    SECURITY: More secure than JSON files - prevents direct file access/manipulation.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "database" / "pricing.db")
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize pricing configuration tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main pricing config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pricing_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                config_json TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                updated_by TEXT,
                version INTEGER DEFAULT 1
            )
        """)
        
        # Audit log for pricing changes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pricing_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                changed_at TEXT NOT NULL,
                changed_by TEXT NOT NULL,
                change_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                description TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("[PricingDB] Database initialized")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current pricing configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT config_json, last_updated, updated_by FROM pricing_config WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            config = json.loads(row['config_json'])
            config['last_updated'] = row['last_updated']
            config['updated_by'] = row['updated_by']
            return config
        else:
            # Return default config if none exists
            return self._get_default_config()
    
    def save_config(self, config: Dict[str, Any], updated_by: str = "system") -> bool:
        """
        Save pricing configuration to database.
        SECURITY: Logs all changes for audit trail.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get old config for audit
            cursor.execute("SELECT config_json FROM pricing_config WHERE id = 1")
            old_row = cursor.fetchone()
            old_config = json.loads(old_row[0]) if old_row else None
            
            # Add metadata
            config['last_updated'] = datetime.now().isoformat()
            config['updated_by'] = updated_by
            
            config_json = json.dumps(config)
            
            # Insert or replace
            cursor.execute("""
                INSERT OR REPLACE INTO pricing_config (id, config_json, last_updated, updated_by, version)
                VALUES (1, ?, ?, ?, COALESCE((SELECT version FROM pricing_config WHERE id = 1) + 1, 1))
            """, (config_json, config['last_updated'], updated_by))
            
            # Audit log
            cursor.execute("""
                INSERT INTO pricing_audit_log (changed_at, changed_by, change_type, old_value, new_value, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                updated_by,
                "update",
                json.dumps(old_config) if old_config else None,
                config_json,
                "Pricing configuration updated"
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"[PricingDB] Config saved by {updated_by}")
            return True
        except Exception as e:
            logger.error(f"[PricingDB] Save failed: {e}")
            return False
    
    def get_audit_log(self, limit: int = 50) -> list:
        """Get pricing change audit log."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT changed_at, changed_by, change_type, description
            FROM pricing_audit_log
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default pricing configuration."""
        return {
            "action_costs": {
                "chat_query": 1,
                "chat_multiagent": 2,
                "chat_simulation": 25,
                "area_analysis": 3,
                "building_analysis": 9,
                "viewport_analysis": 1,
                "location_analysis": 3,
                "comparison": 3,
                "valuation": 5,
                "investment_analysis": 10,
                "simulation_basic": 10,
                "simulation_advanced": 25,
                "storyboard_generation": 15,
                "scenario_analysis": 25,
                "property_search": 1,
                "poi_search": 1,
                "map_navigation": 0,
                "viewport_load": 0,
                "tileset_load": 0,
                "report_export": 10,
                "dashboard_snapshot": 10,
                "pdf_generation": 10,
                "infrastructure_card": 3,
                "investment_card": 10,
                "livability_card": 3,
                "market_card": 3,
                "terrain_card": 3,
                "spatial_card": 3,
                "comparison_card": 3,
                "locality_brain": 3,
                "growth_prediction": 10,
                "risk_assessment": 10,
                "explainability": 1,
                "fact_verification": 1,
                "causal_reasoning": 10,
                "detailed_report": 200,
                "feedback_reward": -5,
            },
            "tier_monthly_limits": {
                "free": 50,
                "pro": 1000,
                "team": 3000,
                "admin": -1,
            },
            "pricing": {
                "promo_per_unit_inr": 2,
                "regular_per_unit_inr": 10,
                "promo_active": True,
                "promo_discount_percent": 80,
                "promo_valid_until": "2026-03-31"
            },
            "topup_packs": [
                {"name": "Starter", "units": 100, "price_inr": 59, "regular_price": 299},
                {"name": "Standard", "units": 300, "price_inr": 139, "regular_price": 699},
                {"name": "Power", "units": 1000, "price_inr": 399, "regular_price": 1999},
            ],
            "subscription_tiers": {
                "free": {"units": 50, "price_inr": 0, "regular_price": 0},
                "pro": {"units": 1000, "price_inr": 599, "regular_price": 2999},
                "team": {"units": 3000, "price_inr": 999, "regular_price": 4999},
            },
            "last_updated": datetime.now().isoformat(),
            "updated_by": "system"
        }
    
    def migrate_from_json(self, json_path: str) -> bool:
        """Migrate pricing config from JSON file to database."""
        try:
            with open(json_path, 'r') as f:
                config = json.load(f)
            return self.save_config(config, updated_by="migration")
        except Exception as e:
            logger.error(f"[PricingDB] Migration failed: {e}")
            return False


# Singleton instance
_pricing_db = None

def get_pricing_db() -> PricingDatabase:
    """Get or create pricing database singleton."""
    global _pricing_db
    if _pricing_db is None:
        _pricing_db = PricingDatabase()
    return _pricing_db
