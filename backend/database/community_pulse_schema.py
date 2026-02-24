"""
Community Pulse Database Schema - Phase 1, Phase 2 & Phase 3

Phase 1: Family Hub
Enables collaborative property decision-making for joint families.
Tables:
- family_sessions: Core session management for family property search
- family_members: Members invited to participate in family sessions
- family_watchlist: Properties saved for family consideration
- family_votes: Individual votes and aspect-based ratings on properties
- family_timeline_events: Activity feed for family session events

Phase 2: Locality Reviews
Community-driven reviews with India-specific categories.
Tables:
- locality_reviews: User reviews for localities with Vastu, schools, transport ratings
- builder_profiles: Builder/developer profiles with RERA info
- builder_reviews: User reviews for builders
- review_helpful: Helpful votes on reviews
- rera_verifications: RERA registration verification data

Phase 3: Sentiment Dashboard
Market sentiment analysis, price trends, and investment intelligence.
Tables:
- market_sentiment: Overall market sentiment per locality with price metrics
- sentiment_signals: User signals (views, saves, searches) for sentiment
- sentiment_trends: Daily aggregated sentiment trends per locality
"""

import sqlite3
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


class CommunityPulseDB:
    """
    Database operations for Community Pulse Family Hub feature.
    Handles all CRUD operations for family collaboration on property decisions.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use the main database path from config
            try:
                from config import config
                self.db_path = config.DB_PATH
            except ImportError:
                self.db_path = str(Path(__file__).parent.parent / "valora.db")
        else:
            self.db_path = db_path
        
        logger.info(f"[CommunityPulse] Initialized with database at {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[CommunityPulse] Transaction failed: {e}")
            raise
        finally:
            conn.close()
    
    def _generate_id(self) -> str:
        """Generate a UUID for primary keys."""
        return str(uuid.uuid4())
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()


# ============================================================================
# TABLE CREATION
# ============================================================================

def init_community_pulse_tables(db_path: str = None) -> bool:
    """
    Initialize all Community Pulse tables (Phase 1, Phase 2, and Phase 3).
    
    Args:
        db_path: Optional path to database file. Uses main DB if not specified.
    
    Returns:
        True if successful, False otherwise.
    """
    # Initialize Phase 1 tables
    phase1_success = _init_phase1_tables(db_path)
    
    # Initialize Phase 2 tables
    phase2_success = init_phase2_tables(db_path)
    
    # Initialize Phase 3 tables
    phase3_success = init_phase3_tables(db_path)
    
    if phase1_success and phase2_success and phase3_success:
        logger.info("[CommunityPulse] All tables (Phase 1, 2 & 3) initialized successfully")
        return True
    else:
        logger.error("[CommunityPulse] Failed to initialize some tables")
        return False


def _init_phase1_tables(db_path: str = None) -> bool:
    """
    Initialize Phase 1 tables for Family Hub.
    
    Args:
        db_path: Optional path to database file. Uses main DB if not specified.
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        if db_path is None:
            try:
                from config import config
                db_path = config.DB_PATH
            except ImportError:
                db_path = str(Path(__file__).parent.parent / "valora.db")
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 1. family_sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS family_sessions (
                id TEXT PRIMARY KEY,
                owner_user_id TEXT NOT NULL,
                family_name TEXT NOT NULL,
                description TEXT,
                target_locality TEXT,
                budget_min REAL,
                budget_max REAL,
                property_types TEXT,
                settings TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (owner_user_id) REFERENCES users(user_id)
            )
        """)
        
        # Indexes for family_sessions
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_sessions_owner 
            ON family_sessions(owner_user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_sessions_status 
            ON family_sessions(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_sessions_locality 
            ON family_sessions(target_locality)
        """)
        
        # 2. family_members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS family_members (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT,
                email TEXT,
                phone TEXT,
                name TEXT NOT NULL,
                role TEXT DEFAULT 'member',
                invite_status TEXT DEFAULT 'pending',
                invited_at TEXT,
                joined_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES family_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Indexes for family_members
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_members_session 
            ON family_members(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_members_user 
            ON family_members(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_members_invite_status 
            ON family_members(invite_status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_members_email 
            ON family_members(email)
        """)
        
        # 3. family_watchlist table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS family_watchlist (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                property_id TEXT,
                property_title TEXT,
                locality TEXT,
                latitude REAL,
                longitude REAL,
                price REAL,
                added_by TEXT NOT NULL,
                notes TEXT,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'considering',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES family_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (property_id) REFERENCES properties(property_id),
                FOREIGN KEY (added_by) REFERENCES users(user_id)
            )
        """)
        
        # Indexes for family_watchlist
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_watchlist_session 
            ON family_watchlist(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_watchlist_property 
            ON family_watchlist(property_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_watchlist_status 
            ON family_watchlist(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_watchlist_priority 
            ON family_watchlist(priority)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_watchlist_added_by 
            ON family_watchlist(added_by)
        """)
        
        # 4. family_votes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS family_votes (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                property_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                vote TEXT NOT NULL,
                aspects TEXT,
                comment TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES family_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (property_id) REFERENCES properties(property_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(session_id, property_id, user_id)
            )
        """)
        
        # Indexes for family_votes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_votes_session 
            ON family_votes(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_votes_property 
            ON family_votes(property_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_votes_user 
            ON family_votes(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_votes_vote 
            ON family_votes(vote)
        """)
        
        # 5. family_timeline_events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS family_timeline_events (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                user_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES family_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Indexes for family_timeline_events
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_timeline_session 
            ON family_timeline_events(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_timeline_event_type 
            ON family_timeline_events(event_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_timeline_created_at 
            ON family_timeline_events(created_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_timeline_user 
            ON family_timeline_events(user_id)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("[CommunityPulse] Phase 1 tables initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to initialize Phase 1 tables: {e}")
        return False


def init_phase2_tables(db_path: str = None) -> bool:
    """
    Initialize Phase 2 tables for Locality Reviews.
    
    Args:
        db_path: Optional path to database file. Uses main DB if not specified.
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        if db_path is None:
            try:
                from config import config
                db_path = config.DB_PATH
            except ImportError:
                db_path = str(Path(__file__).parent.parent / "valora.db")
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 1. locality_reviews table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locality_reviews (
                id TEXT PRIMARY KEY,
                locality_id TEXT NOT NULL,
                locality_name TEXT NOT NULL,
                user_id TEXT NOT NULL,
                overall_rating REAL NOT NULL,
                vastu_rating REAL,
                vastu_notes TEXT,
                school_rating REAL,
                school_notes TEXT,
                religious_proximity TEXT,
                transport_rating REAL,
                transport_notes TEXT,
                safety_rating REAL,
                safety_notes TEXT,
                amenities_rating REAL,
                amenities_notes TEXT,
                water_supply_rating REAL,
                power_supply_rating REAL,
                pros TEXT,
                cons TEXT,
                review_text TEXT,
                is_verified INTEGER DEFAULT 0,
                verification_type TEXT,
                helpful_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (locality_id) REFERENCES localities(locality_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Indexes for locality_reviews
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_locality_reviews_locality 
            ON locality_reviews(locality_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_locality_reviews_user 
            ON locality_reviews(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_locality_reviews_status 
            ON locality_reviews(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_locality_reviews_rating 
            ON locality_reviews(overall_rating)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_locality_reviews_created 
            ON locality_reviews(created_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_locality_reviews_verified 
            ON locality_reviews(is_verified)
        """)
        
        # 2. builder_profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS builder_profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                logo_url TEXT,
                website TEXT,
                established_year INTEGER,
                cities_operating TEXT,
                total_projects INTEGER DEFAULT 0,
                completed_projects INTEGER DEFAULT 0,
                ongoing_projects INTEGER DEFAULT 0,
                avg_delivery_time_months REAL,
                on_time_delivery_rate REAL,
                avg_construction_quality_rating REAL,
                avg_after_sales_rating REAL,
                rera_registered INTEGER DEFAULT 0,
                rera_ids TEXT,
                contact_phone TEXT,
                contact_email TEXT,
                address TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Indexes for builder_profiles
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_builder_profiles_name 
            ON builder_profiles(name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_builder_profiles_rera 
            ON builder_profiles(rera_registered)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_builder_profiles_rating 
            ON builder_profiles(avg_construction_quality_rating)
        """)
        
        # 3. builder_reviews table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS builder_reviews (
                id TEXT PRIMARY KEY,
                builder_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                project_name TEXT,
                project_location TEXT,
                overall_rating REAL NOT NULL,
                construction_quality REAL,
                timely_delivery REAL,
                after_sales_service REAL,
                value_for_money REAL,
                transparency REAL,
                pros TEXT,
                cons TEXT,
                review_text TEXT,
                is_verified_buyer INTEGER DEFAULT 0,
                purchase_date TEXT,
                helpful_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (builder_id) REFERENCES builder_profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Indexes for builder_reviews
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_builder_reviews_builder 
            ON builder_reviews(builder_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_builder_reviews_user 
            ON builder_reviews(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_builder_reviews_status 
            ON builder_reviews(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_builder_reviews_rating 
            ON builder_reviews(overall_rating)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_builder_reviews_verified 
            ON builder_reviews(is_verified_buyer)
        """)
        
        # 4. review_helpful table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_helpful (
                id TEXT PRIMARY KEY,
                review_id TEXT NOT NULL,
                review_type TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created_at TEXT,
                UNIQUE(review_id, review_type, user_id)
            )
        """)
        
        # Indexes for review_helpful
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_review_helpful_review 
            ON review_helpful(review_id, review_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_review_helpful_user 
            ON review_helpful(user_id)
        """)
        
        # 5. rera_verifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rera_verifications (
                id TEXT PRIMARY KEY,
                rera_id TEXT NOT NULL,
                state TEXT NOT NULL,
                project_name TEXT,
                builder_name TEXT,
                project_status TEXT,
                registration_date TEXT,
                expiry_date TEXT,
                project_address TEXT,
                project_type TEXT,
                land_area REAL,
                proposed_units INTEGER,
                verification_status TEXT,
                verification_data TEXT,
                last_verified_at TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Indexes for rera_verifications
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rera_verifications_rera_id 
            ON rera_verifications(rera_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rera_verifications_state 
            ON rera_verifications(state)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rera_verifications_builder 
            ON rera_verifications(builder_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rera_verifications_status 
            ON rera_verifications(verification_status)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("[CommunityPulse] Phase 2 tables initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to initialize Phase 2 tables: {e}")
        return False


def init_phase3_tables(db_path: str = None) -> bool:
    """
    Initialize Phase 3 tables for Sentiment Dashboard.
    
    Args:
        db_path: Optional path to database file. Uses main DB if not specified.
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        if db_path is None:
            try:
                from config import config
                db_path = config.DB_PATH
            except ImportError:
                db_path = str(Path(__file__).parent.parent / "valora.db")
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 1. market_sentiment table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_sentiment (
                id TEXT PRIMARY KEY,
                locality_id TEXT NOT NULL,
                locality_name TEXT NOT NULL,
                city TEXT,
                price_current REAL,
                price_1_month_ago REAL,
                price_3_months_ago REAL,
                price_6_months_ago REAL,
                price_1_year_ago REAL,
                price_change_pct REAL,
                price_momentum TEXT,
                sentiment_score REAL,
                demand_score REAL,
                supply_score REAL,
                investment_score REAL,
                rental_yield_avg REAL,
                rental_yield_min REAL,
                rental_yield_max REAL,
                days_on_market_avg INTEGER,
                price_per_sqft_avg REAL,
                inventory_count INTEGER,
                new_listings_30d INTEGER,
                transactions_30d INTEGER,
                sentiment_breakdown TEXT,
                trend_indicators TEXT,
                last_updated TEXT,
                created_at TEXT
            )
        """)
        
        # Indexes for market_sentiment
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_sentiment_locality 
            ON market_sentiment(locality_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_sentiment_city 
            ON market_sentiment(city)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_sentiment_sentiment_score 
            ON market_sentiment(sentiment_score)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_sentiment_price_momentum 
            ON market_sentiment(price_momentum)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_sentiment_last_updated 
            ON market_sentiment(last_updated)
        """)
        
        # 2. sentiment_signals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_signals (
                id TEXT PRIMARY KEY,
                locality_id TEXT,
                property_id TEXT,
                signal_type TEXT NOT NULL,
                user_hash TEXT NOT NULL,
                signal_data TEXT,
                created_at TEXT
            )
        """)
        
        # Indexes for sentiment_signals
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_signals_locality 
            ON sentiment_signals(locality_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_signals_property 
            ON sentiment_signals(property_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_signals_type 
            ON sentiment_signals(signal_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_signals_user_hash 
            ON sentiment_signals(user_hash)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_signals_created 
            ON sentiment_signals(created_at)
        """)
        
        # 3. sentiment_trends table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_trends (
                id TEXT PRIMARY KEY,
                locality_id TEXT NOT NULL,
                trend_date TEXT NOT NULL,
                sentiment_score REAL,
                price_avg REAL,
                activity_count INTEGER,
                search_volume INTEGER,
                created_at TEXT,
                UNIQUE(locality_id, trend_date)
            )
        """)
        
        # Indexes for sentiment_trends
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_trends_locality 
            ON sentiment_trends(locality_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_trends_date 
            ON sentiment_trends(trend_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_trends_sentiment 
            ON sentiment_trends(sentiment_score)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("[CommunityPulse] Phase 3 tables initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to initialize Phase 3 tables: {e}")
        return False


# ============================================================================
# FAMILY SESSIONS CRUD
# ============================================================================

def create_family_session(
    db: CommunityPulseDB,
    owner_user_id: str,
    family_name: str,
    description: str = None,
    target_locality: str = None,
    budget_min: float = None,
    budget_max: float = None,
    property_types: List[str] = None,
    settings: Dict[str, Any] = None
) -> Optional[str]:
    """
    Create a new family session for collaborative property search.
    
    Args:
        db: CommunityPulseDB instance
        owner_user_id: User ID of the session owner
        family_name: Name for the family session
        description: Optional description
        target_locality: Target area/locality for property search
        budget_min: Minimum budget
        budget_max: Maximum budget
        property_types: List of preferred property types
        settings: Additional settings as JSON
    
    Returns:
        Session ID if successful, None otherwise
    """
    try:
        session_id = db._generate_id()
        timestamp = db._get_timestamp()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO family_sessions (
                    id, owner_user_id, family_name, description,
                    target_locality, budget_min, budget_max,
                    property_types, settings, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, owner_user_id, family_name, description,
                target_locality, budget_min, budget_max,
                json.dumps(property_types) if property_types else None,
                json.dumps(settings) if settings else None,
                'active', timestamp, timestamp
            ))
        
        logger.info(f"[CommunityPulse] Created family session {session_id}")
        return session_id
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to create family session: {e}")
        return None


def get_family_session(db: CommunityPulseDB, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a family session by ID.
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID to retrieve
    
    Returns:
        Session data as dict, or None if not found
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM family_sessions WHERE id = ?
            """, (session_id,))
            row = cursor.fetchone()
            
            if row:
                session = dict(row)
                # Parse JSON fields
                if session.get('property_types'):
                    session['property_types'] = json.loads(session['property_types'])
                if session.get('settings'):
                    session['settings'] = json.loads(session['settings'])
                return session
            return None
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get family session: {e}")
        return None


def get_user_family_sessions(
    db: CommunityPulseDB, 
    user_id: str, 
    status: str = None
) -> List[Dict[str, Any]]:
    """
    Get all family sessions for a user (as owner or member).
    
    Args:
        db: CommunityPulseDB instance
        user_id: User ID to get sessions for
        status: Optional status filter
    
    Returns:
        List of session dicts
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get sessions where user is owner or member
            query = """
                SELECT DISTINCT fs.* FROM family_sessions fs
                LEFT JOIN family_members fm ON fs.id = fm.session_id
                WHERE (fs.owner_user_id = ? OR fm.user_id = ?)
            """
            params = [user_id, user_id]
            
            if status:
                query += " AND fs.status = ?"
                params.append(status)
            
            query += " ORDER BY fs.updated_at DESC"
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            sessions = []
            for row in rows:
                session = dict(row)
                if session.get('property_types'):
                    session['property_types'] = json.loads(session['property_types'])
                if session.get('settings'):
                    session['settings'] = json.loads(session['settings'])
                sessions.append(session)
            
            return sessions
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get user family sessions: {e}")
        return []


def update_family_session(
    db: CommunityPulseDB,
    session_id: str,
    **kwargs
) -> bool:
    """
    Update a family session.
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID to update
        **kwargs: Fields to update (family_name, description, target_locality, 
                  budget_min, budget_max, property_types, settings, status)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        allowed_fields = {
            'family_name', 'description', 'target_locality',
            'budget_min', 'budget_max', 'property_types', 'settings', 'status'
        }
        
        updates = {}
        for key, value in kwargs.items():
            if key in allowed_fields:
                if key in ('property_types', 'settings') and value is not None:
                    updates[key] = json.dumps(value)
                else:
                    updates[key] = value
        
        if not updates:
            return True
        
        updates['updated_at'] = db._get_timestamp()
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        query = f"UPDATE family_sessions SET {set_clause} WHERE id = ?"
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(updates.values()) + (session_id,))
        
        logger.info(f"[CommunityPulse] Updated family session {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to update family session: {e}")
        return False


def delete_family_session(db: CommunityPulseDB, session_id: str) -> bool:
    """
    Delete a family session (cascade deletes all related data).
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID to delete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM family_sessions WHERE id = ?", (session_id,))
        
        logger.info(f"[CommunityPulse] Deleted family session {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to delete family session: {e}")
        return False


# ============================================================================
# FAMILY MEMBERS CRUD
# ============================================================================

def add_family_member(
    db: CommunityPulseDB,
    session_id: str,
    name: str,
    user_id: str = None,
    email: str = None,
    phone: str = None,
    role: str = 'member'
) -> Optional[str]:
    """
    Add a member to a family session.
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID to add member to
        name: Member's name
        user_id: User ID if they have an account
        email: Email for invitation
        phone: Phone for invitation
        role: Member role (owner/admin/member/viewer)
    
    Returns:
        Member ID if successful, None otherwise
    """
    try:
        member_id = db._generate_id()
        timestamp = db._get_timestamp()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO family_members (
                    id, session_id, user_id, email, phone, name, 
                    role, invite_status, invited_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                member_id, session_id, user_id, email, phone, name,
                role, 'pending' if email or phone else 'accepted',
                timestamp, timestamp
            ))
        
        logger.info(f"[CommunityPulse] Added member {member_id} to session {session_id}")
        return member_id
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to add family member: {e}")
        return None


def get_family_members(db: CommunityPulseDB, session_id: str) -> List[Dict[str, Any]]:
    """
    Get all members of a family session.
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID to get members for
    
    Returns:
        List of member dicts
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM family_members 
                WHERE session_id = ? 
                ORDER BY created_at ASC
            """, (session_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get family members: {e}")
        return []


def update_family_member(
    db: CommunityPulseDB,
    member_id: str,
    **kwargs
) -> bool:
    """
    Update a family member.
    
    Args:
        db: CommunityPulseDB instance
        member_id: Member ID to update
        **kwargs: Fields to update (role, invite_status, joined_at)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        allowed_fields = {'role', 'invite_status', 'joined_at', 'name', 'email', 'phone'}
        
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return True
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        query = f"UPDATE family_members SET {set_clause} WHERE id = ?"
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(updates.values()) + (member_id,))
        
        logger.info(f"[CommunityPulse] Updated family member {member_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to update family member: {e}")
        return False


def remove_family_member(db: CommunityPulseDB, member_id: str) -> bool:
    """
    Remove a member from a family session.
    
    Args:
        db: CommunityPulseDB instance
        member_id: Member ID to remove
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM family_members WHERE id = ?", (member_id,))
        
        logger.info(f"[CommunityPulse] Removed family member {member_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to remove family member: {e}")
        return False


# ============================================================================
# FAMILY WATCHLIST CRUD
# ============================================================================

def add_to_watchlist(
    db: CommunityPulseDB,
    session_id: str,
    added_by: str,
    property_id: str = None,
    property_title: str = None,
    locality: str = None,
    latitude: float = None,
    longitude: float = None,
    price: float = None,
    notes: str = None,
    priority: str = 'medium'
) -> Optional[str]:
    """
    Add a property to the family watchlist.
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID
        added_by: User ID who added the property
        property_id: Property ID (if from database)
        property_title: Property title
        locality: Property locality
        latitude: Property latitude
        longitude: Property longitude
        price: Property price
        notes: Notes about the property
        priority: Priority level (high/medium/low)
    
    Returns:
        Watchlist entry ID if successful, None otherwise
    """
    try:
        entry_id = db._generate_id()
        timestamp = db._get_timestamp()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO family_watchlist (
                    id, session_id, property_id, property_title, locality,
                    latitude, longitude, price, added_by, notes, priority,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id, session_id, property_id, property_title, locality,
                latitude, longitude, price, added_by, notes, priority,
                'considering', timestamp, timestamp
            ))
        
        logger.info(f"[CommunityPulse] Added property to watchlist {entry_id}")
        return entry_id
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to add to watchlist: {e}")
        return None


def get_watchlist(
    db: CommunityPulseDB, 
    session_id: str,
    status: str = None
) -> List[Dict[str, Any]]:
    """
    Get the watchlist for a family session.
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID
        status: Optional status filter
    
    Returns:
        List of watchlist entries
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                    SELECT * FROM family_watchlist 
                    WHERE session_id = ? AND status = ?
                    ORDER BY priority DESC, created_at DESC
                """, (session_id, status))
            else:
                cursor.execute("""
                    SELECT * FROM family_watchlist 
                    WHERE session_id = ?
                    ORDER BY priority DESC, created_at DESC
                """, (session_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get watchlist: {e}")
        return []


def update_watchlist_entry(
    db: CommunityPulseDB,
    entry_id: str,
    **kwargs
) -> bool:
    """
    Update a watchlist entry.
    
    Args:
        db: CommunityPulseDB instance
        entry_id: Watchlist entry ID
        **kwargs: Fields to update (notes, priority, status)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        allowed_fields = {'notes', 'priority', 'status'}
        
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        updates['updated_at'] = db._get_timestamp()
        
        if len(updates) == 1:  # Only updated_at
            return True
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        query = f"UPDATE family_watchlist SET {set_clause} WHERE id = ?"
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(updates.values()) + (entry_id,))
        
        logger.info(f"[CommunityPulse] Updated watchlist entry {entry_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to update watchlist entry: {e}")
        return False


def remove_from_watchlist(db: CommunityPulseDB, entry_id: str) -> bool:
    """
    Remove a property from the watchlist.
    
    Args:
        db: CommunityPulseDB instance
        entry_id: Watchlist entry ID to remove
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM family_watchlist WHERE id = ?", (entry_id,))
        
        logger.info(f"[CommunityPulse] Removed from watchlist {entry_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to remove from watchlist: {e}")
        return False


# ============================================================================
# FAMILY VOTES CRUD
# ============================================================================

def cast_vote(
    db: CommunityPulseDB,
    session_id: str,
    property_id: str,
    user_id: str,
    vote: str,
    aspects: Dict[str, str] = None,
    comment: str = None
) -> Optional[str]:
    """
    Cast or update a vote on a property.
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID
        property_id: Property ID
        user_id: User ID casting the vote
        vote: Vote value (up/down/maybe)
        aspects: Aspect-level votes {"location": "up", "price": "down", ...}
        comment: Optional comment
    
    Returns:
        Vote ID if successful, None otherwise
    """
    try:
        timestamp = db._get_timestamp()
        vote_id = db._generate_id()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Use INSERT OR REPLACE to handle upsert
            cursor.execute("""
                INSERT OR REPLACE INTO family_votes (
                    id, session_id, property_id, user_id, vote, 
                    aspects, comment, created_at, updated_at
                ) VALUES (
                    COALESCE(
                        (SELECT id FROM family_votes 
                         WHERE session_id = ? AND property_id = ? AND user_id = ?),
                        ?
                    ), ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                session_id, property_id, user_id,  # For COALESCE subquery
                vote_id,  # Default ID if no existing
                session_id, property_id, user_id, vote,
                json.dumps(aspects) if aspects else None,
                comment, timestamp, timestamp
            ))
            
            # Get the actual ID used
            cursor.execute("""
                SELECT id FROM family_votes 
                WHERE session_id = ? AND property_id = ? AND user_id = ?
            """, (session_id, property_id, user_id))
            result = cursor.fetchone()
            actual_id = result['id'] if result else vote_id
        
        logger.info(f"[CommunityPulse] Cast vote {actual_id}")
        return actual_id
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to cast vote: {e}")
        return None


def get_votes_for_property(
    db: CommunityPulseDB,
    session_id: str,
    property_id: str
) -> List[Dict[str, Any]]:
    """
    Get all votes for a property in a session.
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID
        property_id: Property ID
    
    Returns:
        List of vote dicts
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM family_votes 
                WHERE session_id = ? AND property_id = ?
                ORDER BY created_at DESC
            """, (session_id, property_id))
            rows = cursor.fetchall()
            
            votes = []
            for row in rows:
                vote = dict(row)
                if vote.get('aspects'):
                    vote['aspects'] = json.loads(vote['aspects'])
                votes.append(vote)
            
            return votes
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get votes: {e}")
        return []


def get_vote_summary(
    db: CommunityPulseDB,
    session_id: str,
    property_id: str
) -> Dict[str, Any]:
    """
    Get vote summary for a property.
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID
        property_id: Property ID
    
    Returns:
        Dict with vote counts and aspect averages
    """
    try:
        votes = get_votes_for_property(db, session_id, property_id)
        
        summary = {
            'total_votes': len(votes),
            'up': 0,
            'down': 0,
            'maybe': 0,
            'aspects_summary': {},
            'comments': []
        }
        
        aspect_counts = {}
        
        for vote in votes:
            # Count overall votes
            if vote['vote'] == 'up':
                summary['up'] += 1
            elif vote['vote'] == 'down':
                summary['down'] += 1
            elif vote['vote'] == 'maybe':
                summary['maybe'] += 1
            
            # Aggregate aspects
            if vote.get('aspects'):
                for aspect, aspect_vote in vote['aspects'].items():
                    if aspect not in aspect_counts:
                        aspect_counts[aspect] = {'up': 0, 'down': 0, 'maybe': 0}
                    aspect_counts[aspect][aspect_vote] = aspect_counts[aspect].get(aspect_vote, 0) + 1
            
            # Collect comments
            if vote.get('comment'):
                summary['comments'].append({
                    'user_id': vote['user_id'],
                    'comment': vote['comment']
                })
        
        summary['aspects_summary'] = aspect_counts
        
        return summary
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get vote summary: {e}")
        return {}


def delete_vote(
    db: CommunityPulseDB,
    session_id: str,
    property_id: str,
    user_id: str
) -> bool:
    """
    Delete a user's vote on a property.
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID
        property_id: Property ID
        user_id: User ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM family_votes 
                WHERE session_id = ? AND property_id = ? AND user_id = ?
            """, (session_id, property_id, user_id))
        
        logger.info(f"[CommunityPulse] Deleted vote")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to delete vote: {e}")
        return False


# ============================================================================
# FAMILY TIMELINE EVENTS CRUD
# ============================================================================

def add_timeline_event(
    db: CommunityPulseDB,
    session_id: str,
    event_type: str,
    event_data: Dict[str, Any] = None,
    user_id: str = None
) -> Optional[str]:
    """
    Add a timeline event to a family session.
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID
        event_type: Type of event (property_added/vote_cast/member_joined/etc.)
        event_data: Additional event data as JSON
        user_id: User who triggered the event
    
    Returns:
        Event ID if successful, None otherwise
    """
    try:
        event_id = db._generate_id()
        timestamp = db._get_timestamp()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO family_timeline_events (
                    id, session_id, event_type, event_data, user_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event_id, session_id, event_type,
                json.dumps(event_data) if event_data else None,
                user_id, timestamp
            ))
        
        logger.info(f"[CommunityPulse] Added timeline event {event_id}")
        return event_id
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to add timeline event: {e}")
        return None


def get_timeline_events(
    db: CommunityPulseDB,
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    event_type: str = None
) -> List[Dict[str, Any]]:
    """
    Get timeline events for a family session.
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID
        limit: Maximum number of events to return
        offset: Pagination offset
        event_type: Optional filter by event type
    
    Returns:
        List of event dicts
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if event_type:
                cursor.execute("""
                    SELECT * FROM family_timeline_events 
                    WHERE session_id = ? AND event_type = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (session_id, event_type, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM family_timeline_events 
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (session_id, limit, offset))
            
            rows = cursor.fetchall()
            
            events = []
            for row in rows:
                event = dict(row)
                if event.get('event_data'):
                    event['event_data'] = json.loads(event['event_data'])
                events.append(event)
            
            return events
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get timeline events: {e}")
        return []


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_session_statistics(db: CommunityPulseDB, session_id: str) -> Dict[str, Any]:
    """
    Get comprehensive statistics for a family session.
    
    Args:
        db: CommunityPulseDB instance
        session_id: Session ID
    
    Returns:
        Dict with various statistics
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Member count
            cursor.execute("""
                SELECT COUNT(*) as count FROM family_members WHERE session_id = ?
            """, (session_id,))
            stats['member_count'] = cursor.fetchone()['count']
            
            # Watchlist counts
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'shortlisted' THEN 1 ELSE 0 END) as shortlisted,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN status = 'visited' THEN 1 ELSE 0 END) as visited
                FROM family_watchlist WHERE session_id = ?
            """, (session_id,))
            watchlist_stats = cursor.fetchone()
            stats['watchlist'] = dict(watchlist_stats)
            
            # Vote counts
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_votes,
                    SUM(CASE WHEN vote = 'up' THEN 1 ELSE 0 END) as up_votes,
                    SUM(CASE WHEN vote = 'down' THEN 1 ELSE 0 END) as down_votes,
                    SUM(CASE WHEN vote = 'maybe' THEN 1 ELSE 0 END) as maybe_votes
                FROM family_votes WHERE session_id = ?
            """, (session_id,))
            vote_stats = cursor.fetchone()
            stats['votes'] = dict(vote_stats)
            
            # Timeline event count
            cursor.execute("""
                SELECT COUNT(*) as count FROM family_timeline_events WHERE session_id = ?
            """, (session_id,))
            stats['event_count'] = cursor.fetchone()['count']
            
            return stats
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get session statistics: {e}")
        return {}


# ============================================================================
# PHASE 2: LOCALITY REVIEWS CRUD
# ============================================================================

def create_locality_review(
    db: CommunityPulseDB,
    locality_id: str,
    locality_name: str,
    user_id: str,
    overall_rating: float,
    vastu_rating: float = None,
    vastu_notes: str = None,
    school_rating: float = None,
    school_notes: str = None,
    religious_proximity: Dict[str, float] = None,
    transport_rating: float = None,
    transport_notes: str = None,
    safety_rating: float = None,
    safety_notes: str = None,
    amenities_rating: float = None,
    amenities_notes: str = None,
    water_supply_rating: float = None,
    power_supply_rating: float = None,
    pros: List[str] = None,
    cons: List[str] = None,
    review_text: str = None,
    verification_type: str = None
) -> Optional[str]:
    """
    Create a new locality review.
    
    Args:
        db: CommunityPulseDB instance
        locality_id: Locality ID
        locality_name: Name of the locality
        user_id: User ID creating the review
        overall_rating: Overall rating (1-5)
        vastu_rating: Vastu compliance rating (1-5) - India-specific
        vastu_notes: Notes about direction facing, room placement
        school_rating: School proximity/quality rating (1-5)
        school_notes: Notes about schools
        religious_proximity: Dict of religious place distances
        transport_rating: Transport connectivity rating (1-5)
        transport_notes: Transport notes
        safety_rating: Safety rating (1-5)
        safety_notes: Safety notes
        amenities_rating: Amenities rating (1-5)
        amenities_notes: Amenities notes
        water_supply_rating: Water supply rating (1-5)
        power_supply_rating: Power supply rating (1-5)
        pros: List of pros
        cons: List of cons
        review_text: Full review text
        verification_type: Type of verification (resident/visitor/owner)
    
    Returns:
        Review ID if successful, None otherwise
    """
    try:
        review_id = db._generate_id()
        timestamp = db._get_timestamp()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO locality_reviews (
                    id, locality_id, locality_name, user_id, overall_rating,
                    vastu_rating, vastu_notes, school_rating, school_notes,
                    religious_proximity, transport_rating, transport_notes,
                    safety_rating, safety_notes, amenities_rating, amenities_notes,
                    water_supply_rating, power_supply_rating, pros, cons,
                    review_text, verification_type, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                review_id, locality_id, locality_name, user_id, overall_rating,
                vastu_rating, vastu_notes, school_rating, school_notes,
                json.dumps(religious_proximity) if religious_proximity else None,
                transport_rating, transport_notes,
                safety_rating, safety_notes, amenities_rating, amenities_notes,
                water_supply_rating, power_supply_rating,
                json.dumps(pros) if pros else None,
                json.dumps(cons) if cons else None,
                review_text, verification_type, timestamp, timestamp
            ))
        
        logger.info(f"[CommunityPulse] Created locality review {review_id}")
        return review_id
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to create locality review: {e}")
        return None


def get_locality_reviews(
    db: CommunityPulseDB,
    locality_id: str,
    status: str = 'active',
    limit: int = 20,
    offset: int = 0,
    sort_by: str = 'created_at'
) -> List[Dict[str, Any]]:
    """
    Get reviews for a locality.
    
    Args:
        db: CommunityPulseDB instance
        locality_id: Locality ID to get reviews for
        status: Status filter (default: 'active')
        limit: Maximum number of reviews to return
        offset: Pagination offset
        sort_by: Sort field (created_at/helpful_count/overall_rating)
    
    Returns:
        List of review dicts
    """
    try:
        # Validate sort_by to prevent SQL injection
        valid_sort_fields = {'created_at', 'helpful_count', 'overall_rating'}
        if sort_by not in valid_sort_fields:
            sort_by = 'created_at'
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM locality_reviews 
                WHERE locality_id = ? AND status = ?
                ORDER BY {sort_by} DESC
                LIMIT ? OFFSET ?
            """, (locality_id, status, limit, offset))
            rows = cursor.fetchall()
            
            reviews = []
            for row in rows:
                review = dict(row)
                # Parse JSON fields
                if review.get('religious_proximity'):
                    review['religious_proximity'] = json.loads(review['religious_proximity'])
                if review.get('pros'):
                    review['pros'] = json.loads(review['pros'])
                if review.get('cons'):
                    review['cons'] = json.loads(review['cons'])
                reviews.append(review)
            
            return reviews
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get locality reviews: {e}")
        return []


def get_locality_review_stats(db: CommunityPulseDB, locality_id: str) -> Dict[str, Any]:
    """
    Get aggregate statistics for locality reviews.
    
    Args:
        db: CommunityPulseDB instance
        locality_id: Locality ID to get stats for
    
    Returns:
        Dict with aggregate statistics
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_reviews,
                    AVG(overall_rating) as avg_overall_rating,
                    AVG(vastu_rating) as avg_vastu_rating,
                    AVG(school_rating) as avg_school_rating,
                    AVG(transport_rating) as avg_transport_rating,
                    AVG(safety_rating) as avg_safety_rating,
                    AVG(amenities_rating) as avg_amenities_rating,
                    AVG(water_supply_rating) as avg_water_supply_rating,
                    AVG(power_supply_rating) as avg_power_supply_rating,
                    SUM(CASE WHEN is_verified = 1 THEN 1 ELSE 0 END) as verified_count,
                    SUM(helpful_count) as total_helpful
                FROM locality_reviews 
                WHERE locality_id = ? AND status = 'active'
            """, (locality_id,))
            row = cursor.fetchone()
            
            if row:
                stats = dict(row)
                # Get rating distribution
                cursor.execute("""
                    SELECT overall_rating, COUNT(*) as count 
                    FROM locality_reviews 
                    WHERE locality_id = ? AND status = 'active'
                    GROUP BY overall_rating
                    ORDER BY overall_rating
                """, (locality_id,))
                stats['rating_distribution'] = {str(r['overall_rating']): r['count'] for r in cursor.fetchall()}
                return stats
            return {}
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get locality review stats: {e}")
        return {}


def update_locality_review(
    db: CommunityPulseDB,
    review_id: str,
    user_id: str,
    **kwargs
) -> bool:
    """
    Update a locality review. Only the original author can update.
    
    Args:
        db: CommunityPulseDB instance
        review_id: Review ID to update
        user_id: User ID (for authorization)
        **kwargs: Fields to update
    
    Returns:
        True if successful, False otherwise
    """
    try:
        allowed_fields = {
            'overall_rating', 'vastu_rating', 'vastu_notes',
            'school_rating', 'school_notes', 'religious_proximity',
            'transport_rating', 'transport_notes', 'safety_rating',
            'safety_notes', 'amenities_rating', 'amenities_notes',
            'water_supply_rating', 'power_supply_rating',
            'pros', 'cons', 'review_text', 'verification_type', 'status'
        }
        
        updates = {}
        for key, value in kwargs.items():
            if key in allowed_fields:
                if key in ('religious_proximity', 'pros', 'cons') and value is not None:
                    updates[key] = json.dumps(value)
                else:
                    updates[key] = value
        
        if not updates:
            return True
        
        updates['updated_at'] = db._get_timestamp()
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        query = f"UPDATE locality_reviews SET {set_clause} WHERE id = ? AND user_id = ?"
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(updates.values()) + (review_id, user_id))
            
            if cursor.rowcount == 0:
                logger.warning(f"[CommunityPulse] No review updated - review not found or unauthorized")
                return False
        
        logger.info(f"[CommunityPulse] Updated locality review {review_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to update locality review: {e}")
        return False


def delete_locality_review(
    db: CommunityPulseDB,
    review_id: str,
    user_id: str
) -> bool:
    """
    Delete a locality review. Only the original author can delete.
    
    Args:
        db: CommunityPulseDB instance
        review_id: Review ID to delete
        user_id: User ID (for authorization)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM locality_reviews 
                WHERE id = ? AND user_id = ?
            """, (review_id, user_id))
            
            if cursor.rowcount == 0:
                logger.warning(f"[CommunityPulse] No review deleted - review not found or unauthorized")
                return False
        
        logger.info(f"[CommunityPulse] Deleted locality review {review_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to delete locality review: {e}")
        return False


# ============================================================================
# PHASE 2: BUILDER PROFILES CRUD
# ============================================================================

def create_builder_profile(
    db: CommunityPulseDB,
    name: str,
    description: str = None,
    logo_url: str = None,
    website: str = None,
    established_year: int = None,
    cities_operating: List[str] = None,
    rera_registered: bool = False,
    rera_ids: List[str] = None,
    contact_phone: str = None,
    contact_email: str = None,
    address: str = None
) -> Optional[str]:
    """
    Create a new builder profile.
    
    Args:
        db: CommunityPulseDB instance
        name: Builder/developer name
        description: Builder description
        logo_url: URL to builder logo
        website: Builder website
        established_year: Year established
        cities_operating: List of cities where builder operates
        rera_registered: Whether builder is RERA registered
        rera_ids: List of RERA registration IDs
        contact_phone: Contact phone number
        contact_email: Contact email
        address: Office address
    
    Returns:
        Builder ID if successful, None otherwise
    """
    try:
        builder_id = db._generate_id()
        timestamp = db._get_timestamp()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO builder_profiles (
                    id, name, description, logo_url, website,
                    established_year, cities_operating, rera_registered,
                    rera_ids, contact_phone, contact_email, address,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                builder_id, name, description, logo_url, website,
                established_year,
                json.dumps(cities_operating) if cities_operating else None,
                1 if rera_registered else 0,
                json.dumps(rera_ids) if rera_ids else None,
                contact_phone, contact_email, address,
                timestamp, timestamp
            ))
        
        logger.info(f"[CommunityPulse] Created builder profile {builder_id}")
        return builder_id
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to create builder profile: {e}")
        return None


def get_builder_profile(db: CommunityPulseDB, builder_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a builder profile by ID.
    
    Args:
        db: CommunityPulseDB instance
        builder_id: Builder ID to retrieve
    
    Returns:
        Builder profile as dict, or None if not found
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM builder_profiles WHERE id = ?
            """, (builder_id,))
            row = cursor.fetchone()
            
            if row:
                builder = dict(row)
                # Parse JSON fields
                if builder.get('cities_operating'):
                    builder['cities_operating'] = json.loads(builder['cities_operating'])
                if builder.get('rera_ids'):
                    builder['rera_ids'] = json.loads(builder['rera_ids'])
                return builder
            return None
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get builder profile: {e}")
        return None


def search_builders(
    db: CommunityPulseDB,
    query: str = None,
    city: str = None,
    rera_registered: bool = None,
    min_rating: float = None,
    limit: int = 20,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Search for builder profiles.
    
    Args:
        db: CommunityPulseDB instance
        query: Search query for builder name
        city: Filter by city
        rera_registered: Filter by RERA registration status
        min_rating: Minimum average rating
        limit: Maximum results to return
        offset: Pagination offset
    
    Returns:
        List of builder profile dicts
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            conditions = []
            params = []
            
            if query:
                conditions.append("name LIKE ?")
                params.append(f"%{query}%")
            
            if city:
                conditions.append("cities_operating LIKE ?")
                params.append(f"%{city}%")
            
            if rera_registered is not None:
                conditions.append("rera_registered = ?")
                params.append(1 if rera_registered else 0)
            
            if min_rating is not None:
                conditions.append("avg_construction_quality_rating >= ?")
                params.append(min_rating)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query_sql = f"""
                SELECT * FROM builder_profiles 
                WHERE {where_clause}
                ORDER BY avg_construction_quality_rating DESC NULLS LAST, name ASC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            
            cursor.execute(query_sql, tuple(params))
            rows = cursor.fetchall()
            
            builders = []
            for row in rows:
                builder = dict(row)
                if builder.get('cities_operating'):
                    builder['cities_operating'] = json.loads(builder['cities_operating'])
                if builder.get('rera_ids'):
                    builder['rera_ids'] = json.loads(builder['rera_ids'])
                builders.append(builder)
            
            return builders
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to search builders: {e}")
        return []


def update_builder_profile(
    db: CommunityPulseDB,
    builder_id: str,
    **kwargs
) -> bool:
    """
    Update a builder profile.
    
    Args:
        db: CommunityPulseDB instance
        builder_id: Builder ID to update
        **kwargs: Fields to update
    
    Returns:
        True if successful, False otherwise
    """
    try:
        allowed_fields = {
            'name', 'description', 'logo_url', 'website',
            'established_year', 'cities_operating', 'total_projects',
            'completed_projects', 'ongoing_projects', 'avg_delivery_time_months',
            'on_time_delivery_rate', 'avg_construction_quality_rating',
            'avg_after_sales_rating', 'rera_registered', 'rera_ids',
            'contact_phone', 'contact_email', 'address'
        }
        
        updates = {}
        for key, value in kwargs.items():
            if key in allowed_fields:
                if key in ('cities_operating', 'rera_ids') and value is not None:
                    updates[key] = json.dumps(value)
                else:
                    updates[key] = value
        
        if not updates:
            return True
        
        updates['updated_at'] = db._get_timestamp()
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        query = f"UPDATE builder_profiles SET {set_clause} WHERE id = ?"
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(updates.values()) + (builder_id,))
        
        logger.info(f"[CommunityPulse] Updated builder profile {builder_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to update builder profile: {e}")
        return False


def update_builder_aggregates(db: CommunityPulseDB, builder_id: str) -> bool:
    """
    Update aggregate ratings for a builder based on reviews.
    
    Args:
        db: CommunityPulseDB instance
        builder_id: Builder ID to update aggregates for
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate aggregates from reviews
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_reviews,
                    AVG(overall_rating) as avg_overall,
                    AVG(construction_quality) as avg_construction,
                    AVG(timely_delivery) as avg_timely,
                    AVG(after_sales_service) as avg_after_sales,
                    AVG(value_for_money) as avg_value,
                    AVG(transparency) as avg_transparency
                FROM builder_reviews 
                WHERE builder_id = ? AND status = 'active'
            """, (builder_id,))
            row = cursor.fetchone()
            
            if row and row['total_reviews'] > 0:
                cursor.execute("""
                    UPDATE builder_profiles SET
                        avg_construction_quality_rating = ?,
                        avg_after_sales_rating = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (
                    row['avg_construction'],
                    row['avg_after_sales'],
                    db._get_timestamp(),
                    builder_id
                ))
        
        logger.info(f"[CommunityPulse] Updated builder aggregates for {builder_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to update builder aggregates: {e}")
        return False


# ============================================================================
# PHASE 2: BUILDER REVIEWS CRUD
# ============================================================================

def create_builder_review(
    db: CommunityPulseDB,
    builder_id: str,
    user_id: str,
    overall_rating: float,
    project_name: str = None,
    project_location: str = None,
    construction_quality: float = None,
    timely_delivery: float = None,
    after_sales_service: float = None,
    value_for_money: float = None,
    transparency: float = None,
    pros: List[str] = None,
    cons: List[str] = None,
    review_text: str = None,
    is_verified_buyer: bool = False,
    purchase_date: str = None
) -> Optional[str]:
    """
    Create a new builder review.
    
    Args:
        db: CommunityPulseDB instance
        builder_id: Builder ID being reviewed
        user_id: User ID creating the review
        overall_rating: Overall rating (1-5)
        project_name: Name of the project
        project_location: Location of the project
        construction_quality: Construction quality rating (1-5)
        timely_delivery: Timely delivery rating (1-5)
        after_sales_service: After-sales service rating (1-5)
        value_for_money: Value for money rating (1-5)
        transparency: Transparency rating (1-5)
        pros: List of pros
        cons: List of cons
        review_text: Full review text
        is_verified_buyer: Whether the reviewer is a verified buyer
        purchase_date: Date of purchase
    
    Returns:
        Review ID if successful, None otherwise
    """
    try:
        review_id = db._generate_id()
        timestamp = db._get_timestamp()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO builder_reviews (
                    id, builder_id, user_id, overall_rating, project_name,
                    project_location, construction_quality, timely_delivery,
                    after_sales_service, value_for_money, transparency,
                    pros, cons, review_text, is_verified_buyer, purchase_date,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                review_id, builder_id, user_id, overall_rating, project_name,
                project_location, construction_quality, timely_delivery,
                after_sales_service, value_for_money, transparency,
                json.dumps(pros) if pros else None,
                json.dumps(cons) if cons else None,
                review_text, 1 if is_verified_buyer else 0, purchase_date,
                timestamp, timestamp
            ))
        
        # Update builder aggregates
        update_builder_aggregates(db, builder_id)
        
        logger.info(f"[CommunityPulse] Created builder review {review_id}")
        return review_id
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to create builder review: {e}")
        return None


def get_builder_reviews(
    db: CommunityPulseDB,
    builder_id: str,
    status: str = 'active',
    limit: int = 20,
    offset: int = 0,
    sort_by: str = 'created_at'
) -> List[Dict[str, Any]]:
    """
    Get reviews for a builder.
    
    Args:
        db: CommunityPulseDB instance
        builder_id: Builder ID to get reviews for
        status: Status filter (default: 'active')
        limit: Maximum number of reviews to return
        offset: Pagination offset
        sort_by: Sort field (created_at/helpful_count/overall_rating)
    
    Returns:
        List of review dicts
    """
    try:
        valid_sort_fields = {'created_at', 'helpful_count', 'overall_rating'}
        if sort_by not in valid_sort_fields:
            sort_by = 'created_at'
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM builder_reviews 
                WHERE builder_id = ? AND status = ?
                ORDER BY {sort_by} DESC
                LIMIT ? OFFSET ?
            """, (builder_id, status, limit, offset))
            rows = cursor.fetchall()
            
            reviews = []
            for row in rows:
                review = dict(row)
                if review.get('pros'):
                    review['pros'] = json.loads(review['pros'])
                if review.get('cons'):
                    review['cons'] = json.loads(review['cons'])
                reviews.append(review)
            
            return reviews
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get builder reviews: {e}")
        return []


def update_builder_review(
    db: CommunityPulseDB,
    review_id: str,
    user_id: str,
    **kwargs
) -> bool:
    """
    Update a builder review. Only the original author can update.
    
    Args:
        db: CommunityPulseDB instance
        review_id: Review ID to update
        user_id: User ID (for authorization)
        **kwargs: Fields to update
    
    Returns:
        True if successful, False otherwise
    """
    try:
        allowed_fields = {
            'overall_rating', 'project_name', 'project_location',
            'construction_quality', 'timely_delivery', 'after_sales_service',
            'value_for_money', 'transparency', 'pros', 'cons',
            'review_text', 'is_verified_buyer', 'purchase_date', 'status'
        }
        
        updates = {}
        for key, value in kwargs.items():
            if key in allowed_fields:
                if key in ('pros', 'cons') and value is not None:
                    updates[key] = json.dumps(value)
                else:
                    updates[key] = value
        
        if not updates:
            return True
        
        updates['updated_at'] = db._get_timestamp()
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        query = f"UPDATE builder_reviews SET {set_clause} WHERE id = ? AND user_id = ?"
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(updates.values()) + (review_id, user_id))
            
            if cursor.rowcount == 0:
                logger.warning(f"[CommunityPulse] No review updated - review not found or unauthorized")
                return False
            
            # Get builder_id to update aggregates
            cursor.execute("SELECT builder_id FROM builder_reviews WHERE id = ?", (review_id,))
            row = cursor.fetchone()
            if row:
                builder_id = row['builder_id']
        
        # Update builder aggregates
        if builder_id:
            update_builder_aggregates(db, builder_id)
        
        logger.info(f"[CommunityPulse] Updated builder review {review_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to update builder review: {e}")
        return False


def delete_builder_review(
    db: CommunityPulseDB,
    review_id: str,
    user_id: str
) -> bool:
    """
    Delete a builder review. Only the original author can delete.
    
    Args:
        db: CommunityPulseDB instance
        review_id: Review ID to delete
        user_id: User ID (for authorization)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get builder_id before deletion
            cursor.execute("SELECT builder_id FROM builder_reviews WHERE id = ? AND user_id = ?", 
                          (review_id, user_id))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"[CommunityPulse] No review deleted - review not found or unauthorized")
                return False
            
            builder_id = row['builder_id']
            
            cursor.execute("""
                DELETE FROM builder_reviews 
                WHERE id = ? AND user_id = ?
            """, (review_id, user_id))
        
        # Update builder aggregates
        update_builder_aggregates(db, builder_id)
        
        logger.info(f"[CommunityPulse] Deleted builder review {review_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to delete builder review: {e}")
        return False


# ============================================================================
# PHASE 2: REVIEW HELPFUL CRUD
# ============================================================================

def mark_review_helpful(
    db: CommunityPulseDB,
    review_id: str,
    review_type: str,
    user_id: str
) -> Optional[str]:
    """
    Mark a review as helpful.
    
    Args:
        db: CommunityPulseDB instance
        review_id: Review ID
        review_type: Type of review ('locality' or 'builder')
        user_id: User ID marking as helpful
    
    Returns:
        Helpful entry ID if successful, None otherwise
    """
    try:
        if review_type not in ('locality', 'builder'):
            logger.error(f"[CommunityPulse] Invalid review type: {review_type}")
            return None
        
        helpful_id = db._generate_id()
        timestamp = db._get_timestamp()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert helpful record
            cursor.execute("""
                INSERT OR IGNORE INTO review_helpful (id, review_id, review_type, user_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (helpful_id, review_id, review_type, user_id, timestamp))
            
            if cursor.rowcount == 0:
                # Already marked as helpful
                return helpful_id
            
            # Update helpful count on the review
            table = 'locality_reviews' if review_type == 'locality' else 'builder_reviews'
            cursor.execute(f"""
                UPDATE {table} SET helpful_count = helpful_count + 1
                WHERE id = ?
            """, (review_id,))
        
        logger.info(f"[CommunityPulse] Marked review {review_id} as helpful")
        return helpful_id
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to mark review as helpful: {e}")
        return None


def unmark_review_helpful(
    db: CommunityPulseDB,
    review_id: str,
    review_type: str,
    user_id: str
) -> bool:
    """
    Remove helpful mark from a review.
    
    Args:
        db: CommunityPulseDB instance
        review_id: Review ID
        review_type: Type of review ('locality' or 'builder')
        user_id: User ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if review_type not in ('locality', 'builder'):
            logger.error(f"[CommunityPulse] Invalid review type: {review_type}")
            return False
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete helpful record
            cursor.execute("""
                DELETE FROM review_helpful 
                WHERE review_id = ? AND review_type = ? AND user_id = ?
            """, (review_id, review_type, user_id))
            
            if cursor.rowcount == 0:
                return True  # Already not marked
            
            # Update helpful count on the review
            table = 'locality_reviews' if review_type == 'locality' else 'builder_reviews'
            cursor.execute(f"""
                UPDATE {table} SET helpful_count = MAX(0, helpful_count - 1)
                WHERE id = ?
            """, (review_id,))
        
        logger.info(f"[CommunityPulse] Unmarked review {review_id} as helpful")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to unmark review as helpful: {e}")
        return False


def get_user_helpful_reviews(
    db: CommunityPulseDB,
    user_id: str,
    review_type: str = None
) -> List[Dict[str, Any]]:
    """
    Get all reviews marked as helpful by a user.
    
    Args:
        db: CommunityPulseDB instance
        user_id: User ID
        review_type: Optional filter by review type
    
    Returns:
        List of helpful entries
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if review_type:
                cursor.execute("""
                    SELECT * FROM review_helpful 
                    WHERE user_id = ? AND review_type = ?
                    ORDER BY created_at DESC
                """, (user_id, review_type))
            else:
                cursor.execute("""
                    SELECT * FROM review_helpful 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                """, (user_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get user helpful reviews: {e}")
        return []


# ============================================================================
# PHASE 2: RERA VERIFICATIONS CRUD
# ============================================================================

def create_rera_verification(
    db: CommunityPulseDB,
    rera_id: str,
    state: str,
    project_name: str = None,
    builder_name: str = None,
    project_status: str = None,
    registration_date: str = None,
    expiry_date: str = None,
    project_address: str = None,
    project_type: str = None,
    land_area: float = None,
    proposed_units: int = None,
    verification_status: str = 'pending',
    verification_data: Dict[str, Any] = None
) -> Optional[str]:
    """
    Create a new RERA verification record.
    
    Args:
        db: CommunityPulseDB instance
        rera_id: RERA registration number
        state: State where the project is registered
        project_name: Name of the project
        builder_name: Name of the builder/developer
        project_status: Status (registered/ongoing/completed/expired)
        registration_date: Date of registration
        expiry_date: Expiry date of registration
        project_address: Project address
        project_type: Type of project
        land_area: Land area in sq meters
        proposed_units: Number of proposed units
        verification_status: Verification status (verified/not_found/error/pending)
        verification_data: Full verification data from RERA API
    
    Returns:
        Verification record ID if successful, None otherwise
    """
    try:
        record_id = db._generate_id()
        timestamp = db._get_timestamp()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO rera_verifications (
                    id, rera_id, state, project_name, builder_name,
                    project_status, registration_date, expiry_date,
                    project_address, project_type, land_area, proposed_units,
                    verification_status, verification_data, last_verified_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record_id, rera_id, state, project_name, builder_name,
                project_status, registration_date, expiry_date,
                project_address, project_type, land_area, proposed_units,
                verification_status,
                json.dumps(verification_data) if verification_data else None,
                timestamp, timestamp, timestamp
            ))
        
        logger.info(f"[CommunityPulse] Created RERA verification record {record_id}")
        return record_id
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to create RERA verification: {e}")
        return None


def get_rera_verification(
    db: CommunityPulseDB,
    rera_id: str = None,
    builder_name: str = None,
    state: str = None
) -> Optional[Dict[str, Any]]:
    """
    Get RERA verification by ID or builder name.
    
    Args:
        db: CommunityPulseDB instance
        rera_id: RERA registration number
        builder_name: Builder name to search for
        state: State filter
    
    Returns:
        Verification record as dict, or None if not found
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if rera_id:
                cursor.execute("""
                    SELECT * FROM rera_verifications WHERE rera_id = ?
                """, (rera_id,))
            elif builder_name and state:
                cursor.execute("""
                    SELECT * FROM rera_verifications 
                    WHERE builder_name LIKE ? AND state = ?
                    ORDER BY last_verified_at DESC
                    LIMIT 1
                """, (f"%{builder_name}%", state))
            elif builder_name:
                cursor.execute("""
                    SELECT * FROM rera_verifications 
                    WHERE builder_name LIKE ?
                    ORDER BY last_verified_at DESC
                    LIMIT 1
                """, (f"%{builder_name}%",))
            else:
                return None
            
            row = cursor.fetchone()
            
            if row:
                record = dict(row)
                if record.get('verification_data'):
                    record['verification_data'] = json.loads(record['verification_data'])
                return record
            return None
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get RERA verification: {e}")
        return None


def update_rera_verification(
    db: CommunityPulseDB,
    verification_id: str,
    **kwargs
) -> bool:
    """
    Update a RERA verification record.
    
    Args:
        db: CommunityPulseDB instance
        verification_id: Verification record ID
        **kwargs: Fields to update
    
    Returns:
        True if successful, False otherwise
    """
    try:
        allowed_fields = {
            'rera_id', 'state', 'project_name', 'builder_name',
            'project_status', 'registration_date', 'expiry_date',
            'project_address', 'project_type', 'land_area', 'proposed_units',
            'verification_status', 'verification_data', 'last_verified_at'
        }
        
        updates = {}
        for key, value in kwargs.items():
            if key in allowed_fields:
                if key == 'verification_data' and value is not None:
                    updates[key] = json.dumps(value)
                else:
                    updates[key] = value
        
        if not updates:
            return True
        
        updates['updated_at'] = db._get_timestamp()
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        query = f"UPDATE rera_verifications SET {set_clause} WHERE id = ?"
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(updates.values()) + (verification_id,))
        
        logger.info(f"[CommunityPulse] Updated RERA verification {verification_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to update RERA verification: {e}")
        return False


# ============================================================================
# PHASE 3: SENTIMENT DASHBOARD CRUD
# ============================================================================

def create_market_sentiment(
    db: CommunityPulseDB,
    locality_id: str,
    locality_name: str,
    city: str = None,
    price_current: float = None,
    price_1_month_ago: float = None,
    price_3_months_ago: float = None,
    price_6_months_ago: float = None,
    price_1_year_ago: float = None,
    price_change_pct: float = None,
    price_momentum: str = None,
    sentiment_score: float = None,
    demand_score: float = None,
    supply_score: float = None,
    investment_score: float = None,
    rental_yield_avg: float = None,
    rental_yield_min: float = None,
    rental_yield_max: float = None,
    days_on_market_avg: int = None,
    price_per_sqft_avg: float = None,
    inventory_count: int = None,
    new_listings_30d: int = None,
    transactions_30d: int = None,
    sentiment_breakdown: Dict[str, Any] = None,
    trend_indicators: Dict[str, Any] = None
) -> Optional[str]:
    """
    Create a new market sentiment record.
    
    Args:
        db: CommunityPulseDB instance
        locality_id: Locality identifier
        locality_name: Locality name
        city: City name
        price_current: Current price
        price_1_month_ago: Price 1 month ago
        price_3_months_ago: Price 3 months ago
        price_6_months_ago: Price 6 months ago
        price_1_year_ago: Price 1 year ago
        price_change_pct: Price change percentage
        price_momentum: bullish/bearish/neutral
        sentiment_score: Overall sentiment score (0-100)
        demand_score: Demand score (0-100)
        supply_score: Supply score (0-100)
        investment_score: Investment score (0-100)
        rental_yield_avg: Average rental yield
        rental_yield_min: Minimum rental yield
        rental_yield_max: Maximum rental yield
        days_on_market_avg: Average days on market
        price_per_sqft_avg: Average price per sqft
        inventory_count: Total inventory count
        new_listings_30d: New listings in last 30 days
        transactions_30d: Transactions in last 30 days
        sentiment_breakdown: JSON breakdown of sentiment
        trend_indicators: JSON trend indicators
    
    Returns:
        Sentiment record ID if successful, None otherwise
    """
    try:
        record_id = db._generate_id()
        timestamp = db._get_timestamp()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO market_sentiment (
                    id, locality_id, locality_name, city,
                    price_current, price_1_month_ago, price_3_months_ago,
                    price_6_months_ago, price_1_year_ago, price_change_pct,
                    price_momentum, sentiment_score, demand_score, supply_score,
                    investment_score, rental_yield_avg, rental_yield_min,
                    rental_yield_max, days_on_market_avg, price_per_sqft_avg,
                    inventory_count, new_listings_30d, transactions_30d,
                    sentiment_breakdown, trend_indicators, last_updated, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record_id, locality_id, locality_name, city,
                price_current, price_1_month_ago, price_3_months_ago,
                price_6_months_ago, price_1_year_ago, price_change_pct,
                price_momentum, sentiment_score, demand_score, supply_score,
                investment_score, rental_yield_avg, rental_yield_min,
                rental_yield_max, days_on_market_avg, price_per_sqft_avg,
                inventory_count, new_listings_30d, transactions_30d,
                json.dumps(sentiment_breakdown) if sentiment_breakdown else None,
                json.dumps(trend_indicators) if trend_indicators else None,
                timestamp, timestamp
            ))
        
        logger.info(f"[CommunityPulse] Created market sentiment {record_id}")
        return record_id
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to create market sentiment: {e}")
        return None


def get_market_sentiment(
    db: CommunityPulseDB,
    locality_id: str = None,
    city: str = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get market sentiment records.
    
    Args:
        db: CommunityPulseDB instance
        locality_id: Optional locality filter
        city: Optional city filter
        limit: Maximum records to return
    
    Returns:
        List of market sentiment records
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM market_sentiment WHERE 1=1"
            params = []
            
            if locality_id:
                query += " AND locality_id = ?"
                params.append(locality_id)
            
            if city:
                query += " AND city = ?"
                params.append(city)
            
            query += " ORDER BY last_updated DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(row)
                if record.get('sentiment_breakdown'):
                    record['sentiment_breakdown'] = json.loads(record['sentiment_breakdown'])
                if record.get('trend_indicators'):
                    record['trend_indicators'] = json.loads(record['trend_indicators'])
                results.append(record)
            
            return results
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get market sentiment: {e}")
        return []


def update_market_sentiment(
    db: CommunityPulseDB,
    sentiment_id: str,
    **kwargs
) -> bool:
    """
    Update a market sentiment record.
    
    Args:
        db: CommunityPulseDB instance
        sentiment_id: Sentiment record ID
        **kwargs: Fields to update
    
    Returns:
        True if successful, False otherwise
    """
    try:
        allowed_fields = {
            'locality_name', 'city', 'price_current', 'price_1_month_ago',
            'price_3_months_ago', 'price_6_months_ago', 'price_1_year_ago',
            'price_change_pct', 'price_momentum', 'sentiment_score',
            'demand_score', 'supply_score', 'investment_score',
            'rental_yield_avg', 'rental_yield_min', 'rental_yield_max',
            'days_on_market_avg', 'price_per_sqft_avg', 'inventory_count',
            'new_listings_30d', 'transactions_30d', 'sentiment_breakdown',
            'trend_indicators'
        }
        
        updates = {}
        for key, value in kwargs.items():
            if key in allowed_fields:
                if key in ('sentiment_breakdown', 'trend_indicators') and value is not None:
                    updates[key] = json.dumps(value)
                else:
                    updates[key] = value
        
        if not updates:
            return True
        
        updates['last_updated'] = db._get_timestamp()
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        query = f"UPDATE market_sentiment SET {set_clause} WHERE id = ?"
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(updates.values()) + (sentiment_id,))
        
        logger.info(f"[CommunityPulse] Updated market sentiment {sentiment_id}")
        return True
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to update market sentiment: {e}")
        return False


def get_sentiment_history(
    db: CommunityPulseDB,
    locality_id: str,
    days: int = 30
) -> List[Dict[str, Any]]:
    """
    Get sentiment history for a locality.
    
    Args:
        db: CommunityPulseDB instance
        locality_id: Locality ID
        days: Number of days to look back
    
    Returns:
        List of historical sentiment records
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM market_sentiment 
                WHERE locality_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (locality_id, days))
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(row)
                if record.get('sentiment_breakdown'):
                    record['sentiment_breakdown'] = json.loads(record['sentiment_breakdown'])
                if record.get('trend_indicators'):
                    record['trend_indicators'] = json.loads(record['trend_indicators'])
                results.append(record)
            
            return results
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get sentiment history: {e}")
        return []


def get_trending_localities(
    db: CommunityPulseDB,
    city: str = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get trending localities based on sentiment score.
    
    Args:
        db: CommunityPulseDB instance
        city: Optional city filter
        limit: Number of results
    
    Returns:
        List of trending localities
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM market_sentiment 
                WHERE 1=1
            """
            params = []
            
            if city:
                query += " AND city = ?"
                params.append(city)
            
            query += " ORDER BY sentiment_score DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(row)
                if record.get('sentiment_breakdown'):
                    record['sentiment_breakdown'] = json.loads(record['sentiment_breakdown'])
                if record.get('trend_indicators'):
                    record['trend_indicators'] = json.loads(record['trend_indicators'])
                results.append(record)
            
            return results
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get trending localities: {e}")
        return []


# ============================================================================
# SENTIMENT SIGNALS CRUD
# ============================================================================

def record_signal(
    db: CommunityPulseDB,
    signal_type: str,
    user_hash: str,
    locality_id: str = None,
    property_id: str = None,
    signal_data: Dict[str, Any] = None
) -> Optional[str]:
    """
    Record a user signal for sentiment analysis.
    
    Args:
        db: CommunityPulseDB instance
        signal_type: Type of signal (property_view/property_save/property_share/analysis_request/search)
        user_hash: Anonymized user identifier
        locality_id: Optional locality ID
        property_id: Optional property ID
        signal_data: Additional signal data as JSON
    
    Returns:
        Signal ID if successful, None otherwise
    """
    try:
        signal_id = db._generate_id()
        timestamp = db._get_timestamp()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sentiment_signals (
                    id, locality_id, property_id, signal_type, 
                    user_hash, signal_data, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id, locality_id, property_id, signal_type,
                user_hash, json.dumps(signal_data) if signal_data else None,
                timestamp
            ))
        
        logger.info(f"[CommunityPulse] Recorded signal {signal_id} of type {signal_type}")
        return signal_id
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to record signal: {e}")
        return None


def get_signals_by_locality(
    db: CommunityPulseDB,
    locality_id: str,
    signal_type: str = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get signals for a specific locality.
    
    Args:
        db: CommunityPulseDB instance
        locality_id: Locality ID
        signal_type: Optional signal type filter
        limit: Maximum records
    
    Returns:
        List of signal records
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if signal_type:
                cursor.execute("""
                    SELECT * FROM sentiment_signals 
                    WHERE locality_id = ? AND signal_type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (locality_id, signal_type, limit))
            else:
                cursor.execute("""
                    SELECT * FROM sentiment_signals 
                    WHERE locality_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (locality_id, limit))
            
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                signal = dict(row)
                if signal.get('signal_data'):
                    signal['signal_data'] = json.loads(signal['signal_data'])
                results.append(signal)
            
            return results
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get signals by locality: {e}")
        return []


def get_aggregated_signals(
    db: CommunityPulseDB,
    locality_id: str = None,
    days: int = 30
) -> Dict[str, Any]:
    """
    Get aggregated signal counts for a locality or overall.
    
    Args:
        db: CommunityPulseDB instance
        locality_id: Optional locality ID
        days: Number of days to aggregate
    
    Returns:
        Dict with aggregated signal counts
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if locality_id:
                cursor.execute("""
                    SELECT signal_type, COUNT(*) as count 
                    FROM sentiment_signals 
                    WHERE locality_id = ? AND created_at >= datetime('now', '-' || ? || ' days')
                    GROUP BY signal_type
                """, (locality_id, days))
            else:
                cursor.execute("""
                    SELECT signal_type, COUNT(*) as count 
                    FROM sentiment_signals 
                    WHERE created_at >= datetime('now', '-' || ? || ' days')
                    GROUP BY signal_type
                """, (days,))
            
            rows = cursor.fetchall()
            
            aggregated = {}
            total = 0
            for row in rows:
                signal_type = row['signal_type']
                count = row['count']
                aggregated[signal_type] = count
                total += count
            
            aggregated['total'] = total
            
            return aggregated
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get aggregated signals: {e}")
        return {}


# ============================================================================
# SENTIMENT TRENDS CRUD
# ============================================================================

def record_trend(
    db: CommunityPulseDB,
    locality_id: str,
    trend_date: str,
    sentiment_score: float = None,
    price_avg: float = None,
    activity_count: int = None,
    search_volume: int = None
) -> Optional[str]:
    """
    Record a daily sentiment trend.
    
    Args:
        db: CommunityPulseDB instance
        locality_id: Locality ID
        trend_date: Date for the trend (YYYY-MM-DD)
        sentiment_score: Sentiment score
        price_avg: Average price
        activity_count: Number of activities
        search_volume: Search volume
    
    Returns:
        Trend ID if successful, None otherwise
    """
    try:
        trend_id = db._generate_id()
        timestamp = db._get_timestamp()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sentiment_trends (
                    id, locality_id, trend_date, sentiment_score,
                    price_avg, activity_count, search_volume, created_at
                ) VALUES (
                    COALESCE(
                        (SELECT id FROM sentiment_trends 
                         WHERE locality_id = ? AND trend_date = ?),
                        ?
                    ), ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                locality_id, trend_date,  # For COALESCE subquery
                trend_id,  # Default ID if no existing
                locality_id, trend_date, sentiment_score,
                price_avg, activity_count, search_volume, timestamp
            ))
            
            # Get the actual ID
            cursor.execute("""
                SELECT id FROM sentiment_trends 
                WHERE locality_id = ? AND trend_date = ?
            """, (locality_id, trend_date))
            result = cursor.fetchone()
            actual_id = result['id'] if result else trend_id
        
        logger.info(f"[CommunityPulse] Recorded trend for {locality_id} on {trend_date}")
        return actual_id
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to record trend: {e}")
        return None


def get_trends(
    db: CommunityPulseDB,
    locality_id: str,
    start_date: str = None,
    end_date: str = None,
    limit: int = 90
) -> List[Dict[str, Any]]:
    """
    Get sentiment trends for a locality.
    
    Args:
        db: CommunityPulseDB instance
        locality_id: Locality ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum records
    
    Returns:
        List of trend records
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM sentiment_trends WHERE locality_id = ?"
            params = [locality_id]
            
            if start_date:
                query += " AND trend_date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND trend_date <= ?"
                params.append(end_date)
            
            query += " ORDER BY trend_date DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to get trends: {e}")
        return []


def calculate_sentiment_score(
    db: CommunityPulseDB,
    locality_id: str
) -> Optional[float]:
    """
    Calculate sentiment score based on aggregated signals.
    
    Args:
        db: CommunityPulseDB instance
        locality_id: Locality ID
    
    Returns:
        Calculated sentiment score (0-100), or None on error
    """
    try:
        # Get recent signals for the locality
        signals = get_aggregated_signals(db, locality_id, days=30)
        
        if not signals or signals.get('total', 0) == 0:
            return None
        
        # Weight different signal types
        weights = {
            'property_view': 1,
            'property_save': 3,
            'property_share': 4,
            'analysis_request': 5,
            'search': 2
        }
        
        weighted_sum = 0
        total_weight = 0
        
        for signal_type, count in signals.items():
            if signal_type != 'total' and signal_type in weights:
                weighted_sum += count * weights[signal_type]
                total_weight += count
        
        if total_weight == 0:
            return None
        
        # Normalize to 0-100 scale (cap at 100)
        raw_score = (weighted_sum / total_weight) * 20
        sentiment_score = min(100, max(0, raw_score))
        
        return round(sentiment_score, 2)
        
    except Exception as e:
        logger.error(f"[CommunityPulse] Failed to calculate sentiment score: {e}")
        return None


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_community_pulse_db = None

def get_community_pulse_db(db_path: str = None) -> CommunityPulseDB:
    """
    Get or create the Community Pulse database instance.
    
    Args:
        db_path: Optional database path
    
    Returns:
        CommunityPulseDB instance
    """
    global _community_pulse_db
    if _community_pulse_db is None:
        _community_pulse_db = CommunityPulseDB(db_path)
    return _community_pulse_db
