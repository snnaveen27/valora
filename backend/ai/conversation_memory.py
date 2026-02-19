"""
Valora AI - Conversation Memory Context

Stores user's previous queries and analysis preferences.
Tracks last locations discussed, analysis types used.
Provides context for personalized suggestions.
"""

import json
import sqlite3
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from threading import Lock

logger = logging.getLogger("valora.conversation_memory")

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "conversation_memory.db"


@dataclass
class SessionData:
    """Session data for a user conversation."""
    user_id: str
    last_location: Optional[str] = None
    last_location_coords: Optional[Dict[str, float]] = None
    last_analysis_type: Optional[str] = None
    locations_discussed: List[str] = field(default_factory=list)
    analysis_history: List[Dict[str, Any]] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    query_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionData':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class UserBehaviorProfile:
    """User behavior profile for smart recommendations."""
    user_id: str
    investment_focus: float = 0.0  # 0-1 score
    price_range_min: Optional[float] = None
    price_range_max: Optional[float] = None
    preferred_localities: List[str] = field(default_factory=list)
    analysis_types_used: Dict[str, int] = field(default_factory=dict)
    engagement_score: float = 0.0
    total_sessions: int = 0
    total_queries: int = 0
    last_active: Optional[str] = None


class ConversationMemory:
    """
    Manages conversation memory and user preferences.
    
    Features:
    - Store user's previous queries and analysis preferences
    - Track last locations discussed, analysis types used
    - Provide context for personalized suggestions
    - SQLite persistence for both authenticated and anonymous users
    """
    
    # Maximum items to keep in history
    MAX_QUERY_HISTORY = 50
    MAX_LOCATIONS_DISCUSSED = 20
    MAX_ANALYSIS_HISTORY = 30
    
    def __init__(self, user_id: str, db_path: Optional[Path] = None):
        """
        Initialize conversation memory for a user.
        
        Args:
            user_id: Unique user identifier (can be anonymous session ID)
            db_path: Optional path to SQLite database
        """
        self.user_id = user_id
        self.db_path = db_path or DEFAULT_DB_PATH
        self._lock = Lock()
        
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize session data
        self.session_data = SessionData(
            user_id=user_id,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        
        # Initialize database
        self._init_database()
        
        # Load existing data if available
        self._load_from_db()
    
    def _init_database(self):
        """Initialize SQLite database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Session data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    user_id TEXT PRIMARY KEY,
                    session_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # User behavior profiles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_behavior_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # A/B testing tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ab_test_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ab_test_user ON ab_test_events(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ab_test_name ON ab_test_events(test_name)')
            
            conn.commit()
    
    def _load_from_db(self):
        """Load session data from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT session_data FROM conversation_sessions WHERE user_id = ?',
                    (self.user_id,)
                )
                row = cursor.fetchone()
                if row:
                    data = json.loads(row[0])
                    self.session_data = SessionData.from_dict(data)
                    logger.debug(f"Loaded session data for user {self.user_id}")
        except Exception as e:
            logger.warning(f"Could not load session data: {e}")
    
    def _save_to_db(self):
        """Save session data to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                self.session_data.updated_at = datetime.utcnow().isoformat()
                cursor.execute('''
                    INSERT OR REPLACE INTO conversation_sessions (user_id, session_data, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (self.user_id, json.dumps(self.session_data.to_dict())))
                conn.commit()
        except Exception as e:
            logger.error(f"Could not save session data: {e}")
    
    def update_context(
        self,
        query: str,
        intent: str,
        location: Optional[str] = None,
        location_coords: Optional[Dict[str, float]] = None,
        analysis_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update session context with new interaction.
        
        Args:
            query: User's query text
            intent: Classified intent
            location: Location mentioned in query
            location_coords: Coordinates of the location
            analysis_type: Type of analysis performed
            metadata: Additional metadata about the interaction
        """
        with self._lock:
            # Update last location
            if location:
                self.session_data.last_location = location
                if location_coords:
                    self.session_data.last_location_coords = location_coords
                
                # Add to locations discussed (avoid duplicates)
                if location not in self.session_data.locations_discussed:
                    self.session_data.locations_discussed.insert(0, location)
                    # Trim to max size
                    self.session_data.locations_discussed = \
                        self.session_data.locations_discussed[:self.MAX_LOCATIONS_DISCUSSED]
            
            # Update last analysis type
            if analysis_type:
                self.session_data.last_analysis_type = analysis_type
                
                # Add to analysis history
                analysis_entry = {
                    'type': analysis_type,
                    'location': location,
                    'timestamp': datetime.utcnow().isoformat(),
                    'intent': intent
                }
                self.session_data.analysis_history.insert(0, analysis_entry)
                self.session_data.analysis_history = \
                    self.session_data.analysis_history[:self.MAX_ANALYSIS_HISTORY]
            
            # Add to query history
            query_entry = {
                'query': query,
                'intent': intent,
                'location': location,
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': metadata or {}
            }
            self.session_data.query_history.insert(0, query_entry)
            self.session_data.query_history = \
                self.session_data.query_history[:self.MAX_QUERY_HISTORY]
            
            # Update preferences based on interaction
            self._update_preferences(intent, location, analysis_type, metadata)
            
            # Save to database
            self._save_to_db()
            
            logger.debug(f"Updated context for user {self.user_id}: location={location}, intent={intent}")
    
    def _update_preferences(
        self,
        intent: str,
        location: Optional[str],
        analysis_type: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ):
        """Update user preferences based on interaction."""
        prefs = self.session_data.preferences
        
        # Track intent frequency
        intent_key = f"intent_{intent}"
        prefs[intent_key] = prefs.get(intent_key, 0) + 1
        
        # Track location frequency
        if location:
            loc_key = f"location_{location.lower()}"
            prefs[loc_key] = prefs.get(loc_key, 0) + 1
        
        # Track analysis type frequency
        if analysis_type:
            analysis_key = f"analysis_{analysis_type}"
            prefs[analysis_key] = prefs.get(analysis_key, 0) + 1
        
        # Track price range preferences from metadata
        if metadata and 'price_range' in metadata:
            price_range = metadata['price_range']
            if 'min' in price_range:
                prefs['price_range_min'] = min(
                    prefs.get('price_range_min', float('inf')),
                    price_range['min']
                )
            if 'max' in price_range:
                prefs['price_range_max'] = max(
                    prefs.get('price_range_max', 0),
                    price_range['max']
                )
        
        # Track investment focus
        investment_intents = ['investment', 'roi_inquiry', 'investment_evaluation', 'investment_comparison']
        if intent in investment_intents:
            prefs['investment_focus_count'] = prefs.get('investment_focus_count', 0) + 1
    
    def get_personalized_suggestion(self) -> str:
        """
        Generate personalized suggestion based on history.
        
        Returns:
            A personalized suggestion string
        """
        prefs = self.session_data.preferences
        suggestions = []
        
        # Check investment focus
        investment_count = prefs.get('investment_focus_count', 0)
        total_queries = len(self.session_data.query_history)
        
        if total_queries > 2 and investment_count / max(total_queries, 1) > 0.3:
            suggestions.append(
                "Based on your interest in investments, I can provide detailed ROI analysis "
                "and market trend forecasts for any area you're considering."
            )
        
        # Check for locations discussed but not analyzed
        if self.session_data.last_location and not self.session_data.last_analysis_type:
            suggestions.append(
                f"Would you like me to perform a detailed analysis of {self.session_data.last_location}?"
            )
        
        # Check for comparison opportunities
        if len(self.session_data.locations_discussed) >= 2:
            loc1, loc2 = self.session_data.locations_discussed[:2]
            suggestions.append(
                f"You've been exploring {loc1} and {loc2}. Would you like a comparison analysis?"
            )
        
        # Check for unused analysis types
        used_analyses = set(k.replace('analysis_', '') for k in prefs if k.startswith('analysis_'))
        available_analyses = {'area_analysis', 'investment_report', 'market_trend', 'terrain_analysis'}
        unused = available_analyses - used_analyses
        
        if unused and self.session_data.last_location:
            if 'investment_report' in unused:
                suggestions.append(
                    f"I can generate a comprehensive investment report for {self.session_data.last_location} "
                    "with ROI projections and risk assessment."
                )
            elif 'terrain_analysis' in unused:
                suggestions.append(
                    f"Would you like to see terrain and flood risk analysis for {self.session_data.last_location}?"
                )
        
        # Return the most relevant suggestion
        return suggestions[0] if suggestions else ""
    
    def get_context_for_query(self) -> Dict[str, Any]:
        """
        Return context to enhance query understanding.
        
        Returns:
            Dictionary with context information
        """
        return {
            'last_location': self.session_data.last_location,
            'last_location_coords': self.session_data.last_location_coords,
            'last_analysis_type': self.session_data.last_analysis_type,
            'locations_discussed': self.session_data.locations_discussed[:5],
            'recent_intents': [q['intent'] for q in self.session_data.query_history[:5]],
            'preferences': self.session_data.preferences,
            'total_queries': len(self.session_data.query_history),
            'investment_focus_ratio': self._calculate_investment_focus()
        }
    
    def _calculate_investment_focus(self) -> float:
        """Calculate the ratio of investment-related queries."""
        if not self.session_data.query_history:
            return 0.0
        
        investment_intents = {
            'investment', 'roi_inquiry', 'investment_evaluation', 
            'investment_comparison', 'market_trend'
        }
        
        investment_count = sum(
            1 for q in self.session_data.query_history[:10]
            if q.get('intent') in investment_intents
        )
        
        return investment_count / min(len(self.session_data.query_history), 10)
    
    def resolve_pronoun(self, pronoun: str) -> Optional[str]:
        """
        Resolve pronouns like 'it', 'there', 'that area' to actual location.
        
        Args:
            pronoun: The pronoun to resolve
            
        Returns:
            The resolved location or None
        """
        pronoun_lower = pronoun.lower()
        
        # Pronouns that refer to location
        location_pronouns = {
            'it', 'there', 'that area', 'that place', 'that locality',
            'this area', 'this place', 'this locality', 'here', 'that'
        }
        
        if pronoun_lower in location_pronouns:
            return self.session_data.last_location
        
        return None
    
    def get_followup_context(self, current_query: str) -> Dict[str, Any]:
        """
        Get context for handling follow-up queries.
        
        Args:
            current_query: The current user query
            
        Returns:
            Context dictionary for follow-up handling
        """
        context = self.get_context_for_query()
        
        # Check if this is a follow-up query
        followup_indicators = [
            'what about', 'how about', 'tell me more', 'and there',
            'also', 'just', 'only', 'there', 'that area', 'it'
        ]
        
        is_followup = any(
            indicator in current_query.lower() 
            for indicator in followup_indicators
        )
        
        context['is_followup'] = is_followup
        context['previous_query'] = (
            self.session_data.query_history[0] 
            if self.session_data.query_history else None
        )
        
        return context
    
    def clear_session(self):
        """Clear the current session data."""
        with self._lock:
            self.session_data = SessionData(
                user_id=self.user_id,
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
            self._save_to_db()
            logger.info(f"Cleared session for user {self.user_id}")


class ConversationMemoryManager:
    """
    Manager for conversation memory instances.
    Provides caching and cleanup of memory instances.
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._memory_cache: Dict[str, ConversationMemory] = {}
        self._cache_lock = Lock()
        self._db_path = DEFAULT_DB_PATH
    
    def get_memory(self, user_id: str) -> ConversationMemory:
        """
        Get or create conversation memory for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            ConversationMemory instance
        """
        with self._cache_lock:
            if user_id not in self._memory_cache:
                self._memory_cache[user_id] = ConversationMemory(
                    user_id=user_id,
                    db_path=self._db_path
                )
            return self._memory_cache[user_id]
    
    def clear_cache(self, user_id: Optional[str] = None):
        """Clear memory cache for a user or all users."""
        with self._cache_lock:
            if user_id:
                self._memory_cache.pop(user_id, None)
            else:
                self._memory_cache.clear()
    
    def cleanup_inactive(self, max_age_hours: int = 24):
        """Remove inactive memory instances from cache."""
        # This is a simple cleanup - in production, you might want more sophisticated logic
        with self._cache_lock:
            to_remove = []
            for user_id, memory in self._memory_cache.items():
                if memory.session_data.updated_at:
                    updated = datetime.fromisoformat(memory.session_data.updated_at)
                    if datetime.utcnow() - updated > timedelta(hours=max_age_hours):
                        to_remove.append(user_id)
            
            for user_id in to_remove:
                del self._memory_cache[user_id]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} inactive memory instances")


# Singleton instance
_memory_manager = None


def get_conversation_memory(user_id: str) -> ConversationMemory:
    """
    Get conversation memory for a user.
    
    Args:
        user_id: User identifier (can be anonymous session ID)
        
    Returns:
        ConversationMemory instance
    """
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = ConversationMemoryManager()
    return _memory_manager.get_memory(user_id)


def get_memory_manager() -> ConversationMemoryManager:
    """Get the conversation memory manager singleton."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = ConversationMemoryManager()
    return _memory_manager
