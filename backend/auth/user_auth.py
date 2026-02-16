"""
Valora AI - User Authentication System
JWT-based authentication with email/password login and subscription tiers.
"""

import os
import jwt
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Configuration
JWT_SECRET = os.environ.get("JWT_SECRET", "valora-jwt-secret-change-in-production-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7  # 7 days
from config import config
DATABASE_PATH = config.DB_PATH.parent / "users.db"


class SubscriptionTier(Enum):
    """Subscription tiers from business model."""
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"
    ADMIN = "admin"


class UserRole(Enum):
    """User roles."""
    USER = "user"
    TEAM_ADMIN = "team_admin"
    ADMIN = "admin"


# Tier limits and features
TIER_LIMITS = {
    SubscriptionTier.FREE: {
        "queries_per_day": 10,
        "reports_per_month": 2,
        "features": ["basic_navigation", "basic_area_insight", "limited_chat"],
        "price_inr": 0,
    },
    SubscriptionTier.PRO: {
        "queries_per_day": 500,
        "reports_per_month": 50,
        "features": ["full_search", "area_analysis", "valuation", "report_export", "explainability", "unlimited_chat"],
        "price_inr": 2999,
    },
    SubscriptionTier.TEAM: {
        "queries_per_day": 2000,
        "reports_per_month": 200,
        "features": ["all_pro_features", "shared_shortlists", "team_admin", "audit_trails", "team_reporting"],
        "price_inr": 4999,
    },
    SubscriptionTier.ENTERPRISE: {
        "queries_per_day": -1,  # Unlimited
        "reports_per_month": -1,
        "features": ["all_team_features", "api_access", "on_prem", "sla", "custom_integrations", "priority_support"],
        "price_inr": -1,  # Custom
    },
    SubscriptionTier.ADMIN: {
        "queries_per_day": -1,
        "reports_per_month": -1,
        "features": ["all_features", "user_management", "system_config", "data_management"],
        "price_inr": 0,
    },
}


@dataclass
class User:
    """User model."""
    id: int
    email: str
    name: str
    password_hash: str
    tier: SubscriptionTier
    role: UserRole
    company: Optional[str]
    phone: Optional[str]
    queries_today: int
    reports_this_month: int
    created_at: str
    last_login: Optional[str]
    is_active: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding password)."""
        data = {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "tier": self.tier.value,
            "role": self.role.value,
            "company": self.company,
            "phone": self.phone,
            "queries_today": self.queries_today,
            "reports_this_month": self.reports_this_month,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "is_active": self.is_active,
            "tier_limits": TIER_LIMITS[self.tier],
        }
        
        # Add balance info if usage tracker available
        try:
            from usage_tracker import get_usage_tracker
            tracker = get_usage_tracker()
            balance = tracker.get_user_balance(self.id)
            data["units_available"] = balance.get("units_available", 0)
            data["units_used_lifetime"] = balance.get("units_used_lifetime", 0)
        except:
            data["units_available"] = 0
            data["units_used_lifetime"] = 0
        
        return data


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hash password with salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return hash_obj.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verify password against hash."""
    computed_hash, _ = hash_password(password, salt)
    return computed_hash == password_hash


def create_token(user_id: int, email: str, tier: str, role: str) -> str:
    """Create JWT token."""
    payload = {
        "user_id": user_id,
        "email": email,
        "tier": tier,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


class UserDatabase:
    """SQLite database for user management."""
    
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                tier TEXT DEFAULT 'free',
                role TEXT DEFAULT 'user',
                company TEXT,
                phone TEXT,
                queries_today INTEGER DEFAULT 0,
                reports_this_month INTEGER DEFAULT 0,
                last_query_date TEXT,
                last_report_date TEXT,
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active INTEGER DEFAULT 1,
                login_attempts_today INTEGER DEFAULT 0,
                last_login_attempt_date TEXT,
                locked_until TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                filters TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        
        # Seed admin user if not exists
        cursor.execute("SELECT id FROM users WHERE email = ?", ("admin@valora.ai",))
        if not cursor.fetchone():
            self._seed_admin(cursor)
            conn.commit()
        
        conn.close()
    
    def _seed_admin(self, cursor):
        """Seed admin user."""
        password_hash, salt = hash_password("admin@valora.ai")
        cursor.execute("""
            INSERT INTO users (email, name, password_hash, password_salt, tier, role, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "admin@valora.ai",
            "Valora Admin",
            password_hash,
            salt,
            SubscriptionTier.ADMIN.value,
            UserRole.ADMIN.value,
            datetime.now().isoformat(),
            1
        ))
        print("[OK] Admin user seeded: admin@valora.ai")
        
        # Seed demo user
        demo_hash, demo_salt = hash_password("demouser")
        cursor.execute("""
            INSERT INTO users (email, name, password_hash, password_salt, tier, role, company, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "demouser@valora.ai",
            "Demo User",
            demo_hash,
            demo_salt,
            SubscriptionTier.PRO.value,
            UserRole.USER.value,
            "Valora Demo",
            datetime.now().isoformat(),
            1
        ))
        print("[OK] Demo user seeded: demouser@valora.ai")
    
    def create_user(
        self,
        email: str,
        name: str,
        password: str,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        role: UserRole = UserRole.USER,
        company: str = None,
        phone: str = None
    ) -> Optional[User]:
        """Create new user."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Check if email exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email.lower(),))
        if cursor.fetchone():
            conn.close()
            return None  # Email already exists
        
        password_hash, salt = hash_password(password)
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO users (email, name, password_hash, password_salt, tier, role, company, phone, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email.lower(),
            name,
            password_hash,
            salt,
            tier.value,
            role.value,
            company,
            phone,
            now,
            1
        ))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return self.get_user_by_id(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email.lower(),))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_user(row)
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_user(row)
        return None
    
    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convert database row to User object."""
        return User(
            id=row["id"],
            email=row["email"],
            name=row["name"],
            password_hash=row["password_hash"],
            tier=SubscriptionTier(row["tier"]),
            role=UserRole(row["role"]),
            company=row["company"],
            phone=row["phone"],
            queries_today=row["queries_today"],
            reports_this_month=row["reports_this_month"],
            created_at=row["created_at"],
            last_login=row["last_login"],
            is_active=bool(row["is_active"])
        )
    
    def authenticate(self, email: str, password: str) -> tuple[Optional[User], str]:
        """
        Authenticate user with email/password.
        Returns: (User or None, error_message)
        Error messages: 'success', 'invalid_credentials', 'account_locked', 'too_many_attempts'
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.lower(),)
        )
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None, "invalid_credentials"
        
        if not row["is_active"]:
            conn.close()
            return None, "account_locked"
        
        today = datetime.now().date().isoformat()
        
        # Check if locked
        if row["locked_until"]:
            locked_until = datetime.fromisoformat(row["locked_until"])
            if datetime.now() < locked_until:
                conn.close()
                return None, "account_locked"
        
        # Check login attempts (reset if new day)
        attempts_today = row["login_attempts_today"] or 0
        last_attempt_date = row["last_login_attempt_date"]
        
        if last_attempt_date != today:
            attempts_today = 0  # Reset for new day
        
        MAX_LOGIN_ATTEMPTS = 5
        
        if attempts_today >= MAX_LOGIN_ATTEMPTS:
            conn.close()
            return None, "too_many_attempts"
        
        if verify_password(password, row["password_hash"], row["password_salt"]):
            # Successful login - reset attempts and update last login
            cursor.execute(
                "UPDATE users SET last_login = ?, login_attempts_today = 0, last_login_attempt_date = ?, locked_until = NULL WHERE id = ?",
                (datetime.now().isoformat(), today, row["id"])
            )
            conn.commit()
            conn.close()
            return self._row_to_user(row), "success"
        
        # Failed login - increment attempts
        new_attempts = attempts_today + 1
        locked_until = None
        
        if new_attempts >= MAX_LOGIN_ATTEMPTS:
            # Lock account for 24 hours after 5 failed attempts
            locked_until = (datetime.now() + timedelta(hours=24)).isoformat()
        
        cursor.execute(
            "UPDATE users SET login_attempts_today = ?, last_login_attempt_date = ?, locked_until = ? WHERE id = ?",
            (new_attempts, today, locked_until, row["id"])
        )
        conn.commit()
        conn.close()
        
        if new_attempts >= MAX_LOGIN_ATTEMPTS:
            return None, "account_locked"
        
        return None, f"invalid_credentials:{MAX_LOGIN_ATTEMPTS - new_attempts}"
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields."""
        allowed_fields = ["name", "tier", "role", "company", "phone", "is_active"]
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [user_id]
        
        cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        return affected > 0
    
    def change_password(self, user_id: int, new_password: str) -> bool:
        """Change user password."""
        password_hash, salt = hash_password(new_password)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ?, password_salt = ? WHERE id = ?",
            (password_hash, salt, user_id)
        )
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        return affected > 0
    
    def increment_query_count(self, user_id: int) -> bool:
        """Increment user's query count for today."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        today = datetime.now().date().isoformat()
        
        # Check if date changed, reset counter
        cursor.execute("SELECT last_query_date FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row and row["last_query_date"] != today:
            # New day, reset counter
            cursor.execute(
                "UPDATE users SET queries_today = 1, last_query_date = ? WHERE id = ?",
                (today, user_id)
            )
        else:
            # Same day, increment
            cursor.execute(
                "UPDATE users SET queries_today = queries_today + 1, last_query_date = ? WHERE id = ?",
                (today, user_id)
            )
        
        conn.commit()
        conn.close()
        return True
    
    def check_query_limit(self, user_id: int) -> tuple[bool, int, int]:
        """Check if user is within query limit. Returns (allowed, used, limit)."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False, 0, 0
        
        limit = TIER_LIMITS[user.tier]["queries_per_day"]
        if limit == -1:  # Unlimited
            return True, user.queries_today, -1
        
        # Check if date changed
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT last_query_date FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        today = datetime.now().date().isoformat()
        if row and row["last_query_date"] != today:
            return True, 0, limit  # New day, counter will reset
        
        return user.queries_today < limit, user.queries_today, limit
    
    def get_all_users(self, include_inactive: bool = False) -> List[User]:
        """Get all users (admin function)."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if include_inactive:
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM users WHERE is_active = 1 ORDER BY created_at DESC")
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_user(row) for row in rows]
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics (admin function)."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total users
        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE is_active = 1")
        stats["total_users"] = cursor.fetchone()["cnt"]
        
        # Users by tier
        cursor.execute("""
            SELECT tier, COUNT(*) as cnt 
            FROM users WHERE is_active = 1 
            GROUP BY tier
        """)
        stats["users_by_tier"] = {row["tier"]: row["cnt"] for row in cursor.fetchall()}
        
        # New users today
        today = datetime.now().date().isoformat()
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE created_at LIKE ?",
            (f"{today}%",)
        )
        stats["new_users_today"] = cursor.fetchone()["cnt"]
        
        # Active users today (logged in)
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE last_login LIKE ?",
            (f"{today}%",)
        )
        stats["active_users_today"] = cursor.fetchone()["cnt"]
        
        conn.close()
        return stats
    
    def log_usage(self, user_id: int, action: str, details: str = None):
        """Log user action."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usage_logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, action, details, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    def delete_user(self, user_id: int) -> bool:
        """Soft delete user (set is_active = 0)."""
        return self.update_user(user_id, is_active=0)


# Singleton instance
_user_db = None


def get_user_database() -> UserDatabase:
    """Get user database singleton."""
    global _user_db
    if _user_db is None:
        _user_db = UserDatabase()
    return _user_db
