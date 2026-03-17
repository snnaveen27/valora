"""
Community Pulse Database Schema - Focused on Valora's Product Thesis

This schema is intentionally narrowed to focus on features that directly 
support the product thesis: broker productivity, explainable decision 
intelligence, and client-ready outputs.

CORE FEATURES (Aligned with Product Thesis):
=============================================
1. Decision-Room (Family Hub) - Multi-stakeholder buying workflow
   - family_sessions: Collaborative property decision sessions
   - family_members: Committee members with roles
   - family_watchlist: Properties under consideration
   - family_votes: Individual votes with aspect-based ratings
   - family_timeline_events: Decision activity feed

2. Locality Reviews with Verified Resident Proof
   - locality_reviews: User reviews with verification badges
   - review_helpful: Community validation of reviews
   - Focus: Vastu, schools, transport, safety - defensible locality context

3. Market Sentiment as Supporting Intelligence
   - market_sentiment: Price trends supporting shortlisted decisions
   - NOT a consumer-style sentiment dashboard
   - Supports broker decision-making, not passive browsing

DEPRECATED/REMOVED (Not aligned with product thesis):
======================================================
- Builder profiles and reviews (generic, not broker-focused)
- RERA verification (not core to decision workflow)
- Raw sentiment signals (complex, not client-ready)
- Historical sentiment trends (supporting, not primary)

These were removed to keep Valora niche: broker workflow, explainable reasoning,
and client-ready intelligence outputs.
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
    Initialize Community Pulse tables - FOCUSED VERSION.
    
    Only includes tables aligned with product thesis:
    - Decision-Room (Family Hub) for multi-stakeholder buying
    - Locality reviews with verified resident proof
    - Market sentiment as supporting intelligence (not dashboard)
    
    Removed (not aligned with broker workflow):
    - Builder profiles/reviews
    - RERA verification
    - Raw sentiment signals
    
    Args:
        db_path: Optional path to database file. Uses main DB if not specified.
    
    Returns:
        True if successful, False otherwise.
    """
    # Initialize Decision-Room (Family Hub) tables
    phase1_success = _init_phase1_tables(db_path)
    
    # Initialize Locality Reviews (focused on verified resident proof)
    phase2_success = init_phase2_tables(db_path)
    
    # Initialize Market Sentiment (supporting intelligence only)
    phase3_success = init_phase3_tables(db_path)
    
    if phase1_success and phase2_success and phase3_success:
        logger.info("[CommunityPulse] All focused tables initialized successfully")
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
    Initialize Phase 2 tables - LOCALITY REVIEWS WITH VERIFIED RESIDENT PROOF.
    
    This focuses on defensible locality context that brokers need:
    - Vastu compliance ratings
    - School accessibility
    - Transport connectivity
    - Safety ratings
    - Verified resident badges
    
    REMOVED (not aligned with product thesis):
    - Builder profiles (generic directory)
    - Builder reviews (not locality-focused)
    - RERA verification (not core to broker workflow)
    
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
        
        # 2. review_helpful table - Community validation of reviews
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
        
        conn.commit()
        conn.close()
        
        logger.info("[CommunityPulse] Phase 2 tables initialized: locality_reviews, review_helpful")
        return True
        
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
    Initialize Phase 3 tables - MARKET SENTIMENT AS SUPPORTING INTELLIGENCE.
    
    This is SECONDARY to core broker workflow features.
    Market sentiment should support shortlisted decisions, not dominate the tab.
    
    Only includes:
    - market_sentiment: Price trends and sentiment for decision support
    
    REMOVED (not aligned with product thesis):
    - sentiment_signals: Raw user behavior tracking (too complex)
    - sentiment_trends: Historical trends (can be derived from market_sentiment)
    
    Valora wins on broker workflow + explainable reasoning, not consumer-style 
    sentiment dashboard.
    
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
        
        conn.commit()
        conn.close()
        
        logger.info("[CommunityPulse] Phase 3 tables initialized: market_sentiment (supporting intelligence)")
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
                # Handle None values - convert to defaults
                if stats.get('verified_count') is None:
                    stats['verified_count'] = 0
                if stats.get('total_helpful') is None:
                    stats['total_helpful'] = 0
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
            # Return default stats when no reviews
            return {
                'total_reviews': 0,
                'avg_overall_rating': None,
                'avg_vastu_rating': None,
                'avg_school_rating': None,
                'avg_transport_rating': None,
                'avg_safety_rating': None,
                'avg_amenities_rating': None,
                'avg_water_supply_rating': None,
                'avg_power_supply_rating': None,
                'verified_count': 0,
                'total_helpful': 0,
                'rating_distribution': {}
            }
            
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
    Mark a locality review as helpful.
    
    Args:
        db: CommunityPulseDB instance
        review_id: Review ID
        review_type: Type of review ('locality')
        user_id: User ID marking as helpful
    
    Returns:
        Helpful entry ID if successful, None otherwise
    """
    try:
        if review_type != 'locality':
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
            
            # Update helpful count on the locality review
            cursor.execute("""
                UPDATE locality_reviews SET helpful_count = helpful_count + 1
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
    Remove helpful mark from a locality review.
    
    Args:
        db: CommunityPulseDB instance
        review_id: Review ID
        review_type: Type of review ('locality')
        user_id: User ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if review_type != 'locality':
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
            
            # Update helpful count on the locality review
            cursor.execute("""
                UPDATE locality_reviews SET helpful_count = MAX(0, helpful_count - 1)
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
    Get all locality reviews marked as helpful by a user.
    
    Args:
        db: CommunityPulseDB instance
        user_id: User ID
        review_type: Optional filter by review type (only 'locality' supported)
    
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


