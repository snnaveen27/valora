"""
Valora AI - Prompt A/B Testing Framework

Defines multiple prompt variants for tiered options.
Tracks conversion rates for each variant.
Serves optimal variant based on user segment.
"""

import json
import sqlite3
import logging
import hashlib
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from threading import Lock
from enum import Enum

logger = logging.getLogger("valora.prompt_ab_testing")

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "ab_testing.db"


class UserSegment(Enum):
    """User segments for A/B testing."""
    NEW_USER = "new_user"
    CASUAL_USER = "casual_user"  # 1-5 sessions
    ACTIVE_USER = "active_user"  # 5+ sessions
    POWER_USER = "power_user"    # 20+ sessions
    INVESTMENT_FOCUSED = "investment_focused"
    EXPLORER = "explorer"  # Browsing multiple areas


@dataclass
class PromptVariant:
    """A variant of a prompt."""
    variant_id: str
    text: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ABTestResult:
    """Result of an A/B test."""
    test_name: str
    variant: str
    user_id: str
    event_type: str  # 'shown', 'clicked', 'converted'
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# Define prompt variants for different contexts
PROMPT_VARIANTS = {
    'tiered_options_header': {
        'A': PromptVariant(
            variant_id='A',
            text="What level of analysis would you like?",
            description="Question format - inviting"
        ),
        'B': PromptVariant(
            variant_id='B',
            text="Choose your analysis depth:",
            description="Direct command format"
        ),
        'C': PromptVariant(
            variant_id='C',
            text="I can provide different levels of insights:",
            description="Informative format"
        )
    },
    
    'investment_prompt': {
        'A': PromptVariant(
            variant_id='A',
            text="Would you like a detailed investment analysis with ROI projections?",
            description="Question with benefit highlight"
        ),
        'B': PromptVariant(
            variant_id='B',
            text="Get a comprehensive investment report for this area.",
            description="Direct action prompt"
        ),
        'C': PromptVariant(
            variant_id='C',
            text="📈 Investment Analysis Available - See ROI potential and risk assessment.",
            description="Visual indicator with benefits"
        )
    },
    
    'comparison_prompt': {
        'A': PromptVariant(
            variant_id='A',
            text="I can compare these areas for you. Which aspects matter most?",
            description="Interactive question"
        ),
        'B': PromptVariant(
            variant_id='B',
            text="Compare {location1} vs {location2}: Price trends, amenities, and investment potential.",
            description="Feature-focused"
        ),
        'C': PromptVariant(
            variant_id='C',
            text="Let me help you decide! Here's a side-by-side comparison:",
            description="Helpful assistant tone"
        )
    },
    
    'free_tier_hook': {
        'A': PromptVariant(
            variant_id='A',
            text="Start with a free quick overview, or dive deeper with premium analysis.",
            description="Free-first approach"
        ),
        'B': PromptVariant(
            variant_id='B',
            text="Quick insights are free! Premium analysis available for detailed reports.",
            description="Benefit-first approach"
        ),
        'C': PromptVariant(
            variant_id='C',
            text="🎯 Free: Quick Overview | 💎 Premium: Detailed Analysis with ROI",
            description="Visual tier display"
        )
    },
    
    'engagement_hook': {
        'A': PromptVariant(
            variant_id='A',
            text="Want to explore more about this area?",
            description="Simple question"
        ),
        'B': PromptVariant(
            variant_id='B',
            text="I can tell you more about schools, hospitals, and connectivity here.",
            description="Specific features"
        ),
        'C': PromptVariant(
            variant_id='C',
            text="Discover hidden insights: upcoming developments, price trends, and neighborhood scores.",
            description="Discovery-focused"
        )
    },
    
    'upgrade_prompt': {
        'A': PromptVariant(
            variant_id='A',
            text="Unlock detailed analysis with more credits.",
            description="Direct upgrade"
        ),
        'B': PromptVariant(
            variant_id='B',
            text="Get comprehensive reports and ROI analysis with a credit pack.",
            description="Value proposition"
        ),
        'C': PromptVariant(
            variant_id='C',
            text="💡 Pro tip: Credit packs unlock detailed investment reports and comparisons.",
            description="Pro tip format"
        )
    }
}


class ABTestingManager:
    """
    Manages A/B testing for prompts.
    
    Features:
    - Define multiple prompt variants
    - Track conversion rates for each variant
    - Serve optimal variant based on user segment
    - SQLite persistence for test results
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize A/B testing manager.
        
        Args:
            db_path: Optional path to SQLite database
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self._lock = Lock()
        
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Cache for variant assignments
        self._user_variants: Dict[str, Dict[str, str]] = {}
        
        # Load existing test results into memory for quick stats
        self._stats_cache: Dict[str, Dict[str, Dict[str, int]]] = {}
        self._load_stats()
    
    def _init_database(self):
        """Initialize SQLite database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # A/B test events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ab_test_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_segment TEXT,
                    event_type TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Variant assignments table (for consistency)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS variant_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    user_segment TEXT,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(test_name, user_id)
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ab_test_name ON ab_test_events(test_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ab_test_variant ON ab_test_events(variant)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ab_test_user ON ab_test_events(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_variant_assignments ON variant_assignments(test_name, user_id)')
            
            conn.commit()
    
    def _load_stats(self):
        """Load statistics into memory cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT test_name, variant, event_type, COUNT(*) 
                    FROM ab_test_events 
                    GROUP BY test_name, variant, event_type
                ''')
                
                for row in cursor.fetchall():
                    test_name, variant, event_type, count = row
                    if test_name not in self._stats_cache:
                        self._stats_cache[test_name] = {}
                    if variant not in self._stats_cache[test_name]:
                        self._stats_cache[test_name][variant] = {}
                    self._stats_cache[test_name][variant][event_type] = count
        except Exception as e:
            logger.warning(f"Could not load stats cache: {e}")
    
    def get_variant(
        self,
        test_name: str,
        user_id: str,
        user_segment: UserSegment = UserSegment.NEW_USER
    ) -> PromptVariant:
        """
        Get the appropriate variant for a user.
        
        Uses consistent assignment - once a user is assigned a variant,
        they always see that variant for the same test.
        
        Args:
            test_name: Name of the A/B test
            user_id: User identifier
            user_segment: User's segment for targeting
            
        Returns:
            PromptVariant to show to the user
        """
        variants = PROMPT_VARIANTS.get(test_name)
        if not variants:
            logger.warning(f"Unknown test name: {test_name}")
            return PromptVariant(variant_id='default', text="")
        
        with self._lock:
            # Check if user already has an assignment
            if user_id in self._user_variants and test_name in self._user_variants[user_id]:
                variant_id = self._user_variants[user_id][test_name]
                return variants.get(variant_id, list(variants.values())[0])
            
            # Check database for existing assignment
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT variant FROM variant_assignments 
                        WHERE test_name = ? AND user_id = ?
                    ''', (test_name, user_id))
                    row = cursor.fetchone()
                    if row:
                        variant_id = row[0]
                        if user_id not in self._user_variants:
                            self._user_variants[user_id] = {}
                        self._user_variants[user_id][test_name] = variant_id
                        return variants.get(variant_id, list(variants.values())[0])
            except Exception as e:
                logger.warning(f"Could not check existing assignment: {e}")
            
            # Assign new variant based on strategy
            variant_id = self._select_variant(test_name, user_segment)
            
            # Store assignment
            if user_id not in self._user_variants:
                self._user_variants[user_id] = {}
            self._user_variants[user_id][test_name] = variant_id
            
            # Persist assignment
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR IGNORE INTO variant_assignments 
                        (test_name, user_id, variant, user_segment)
                        VALUES (?, ?, ?, ?)
                    ''', (test_name, user_id, variant_id, user_segment.value))
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not persist variant assignment: {e}")
            
            return variants.get(variant_id, list(variants.values())[0])
    
    def _select_variant(self, test_name: str, user_segment: UserSegment) -> str:
        """
        Select a variant using multi-armed bandit approach.
        
        Uses epsilon-greedy with 10% exploration, 90% exploitation.
        For new tests, uses equal distribution.
        
        Args:
            test_name: Name of the test
            user_segment: User's segment
            
        Returns:
            Selected variant ID
        """
        variants = PROMPT_VARIANTS.get(test_name, {})
        if not variants:
            return 'A'
        
        variant_ids = list(variants.keys())
        
        # 10% chance to explore (random assignment)
        if random.random() < 0.1:
            return random.choice(variant_ids)
        
        # 90% chance to exploit (use best performing)
        stats = self._stats_cache.get(test_name, {})
        
        if not stats:
            # No data yet, use equal distribution
            return random.choice(variant_ids)
        
        # Calculate conversion rate for each variant
        best_variant = variant_ids[0]
        best_rate = 0.0
        
        for variant_id in variant_ids:
            variant_stats = stats.get(variant_id, {})
            shown = variant_stats.get('shown', 0)
            converted = variant_stats.get('converted', 0)
            
            if shown > 0:
                rate = converted / shown
                # Add small random factor to break ties
                rate += random.random() * 0.01
                if rate > best_rate:
                    best_rate = rate
                    best_variant = variant_id
        
        return best_variant
    
    def track_event(
        self,
        test_name: str,
        variant: str,
        user_id: str,
        event_type: str,
        user_segment: UserSegment = UserSegment.NEW_USER,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track an A/B test event.
        
        Args:
            test_name: Name of the test
            variant: Variant ID
            user_id: User identifier
            event_type: Type of event ('shown', 'clicked', 'converted')
            user_segment: User's segment
            metadata: Additional metadata
        """
        with self._lock:
            # Update stats cache
            if test_name not in self._stats_cache:
                self._stats_cache[test_name] = {}
            if variant not in self._stats_cache[test_name]:
                self._stats_cache[test_name][variant] = {}
            self._stats_cache[test_name][variant][event_type] = \
                self._stats_cache[test_name][variant].get(event_type, 0) + 1
            
            # Persist event
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO ab_test_events 
                        (test_name, variant, user_id, user_segment, event_type, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (test_name, variant, user_id, user_segment.value, 
                          event_type, json.dumps(metadata or {})))
                    conn.commit()
            except Exception as e:
                logger.error(f"Could not track A/B test event: {e}")
    
    def get_test_stats(self, test_name: str) -> Dict[str, Any]:
        """
        Get statistics for a test.
        
        Args:
            test_name: Name of the test
            
        Returns:
            Dictionary with test statistics
        """
        stats = self._stats_cache.get(test_name, {})
        variants = PROMPT_VARIANTS.get(test_name, {})
        
        result = {
            'test_name': test_name,
            'variants': {},
            'best_variant': None,
            'total_events': 0
        }
        
        best_variant = None
        best_rate = 0.0
        
        for variant_id in variants:
            variant_stats = stats.get(variant_id, {})
            shown = variant_stats.get('shown', 0)
            clicked = variant_stats.get('clicked', 0)
            converted = variant_stats.get('converted', 0)
            
            click_rate = clicked / shown if shown > 0 else 0
            conversion_rate = converted / shown if shown > 0 else 0
            
            result['variants'][variant_id] = {
                'shown': shown,
                'clicked': clicked,
                'converted': converted,
                'click_rate': click_rate,
                'conversion_rate': conversion_rate
            }
            result['total_events'] += shown
            
            if conversion_rate > best_rate:
                best_rate = conversion_rate
                best_variant = variant_id
        
        result['best_variant'] = best_variant
        result['best_conversion_rate'] = best_rate
        
        return result
    
    def get_all_test_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all tests."""
        return {
            test_name: self.get_test_stats(test_name)
            for test_name in PROMPT_VARIANTS
        }
    
    def format_prompt(
        self,
        test_name: str,
        user_id: str,
        user_segment: UserSegment = UserSegment.NEW_USER,
        **kwargs
    ) -> Tuple[str, str]:
        """
        Get and format a prompt for a user.
        
        Args:
            test_name: Name of the test
            user_id: User identifier
            user_segment: User's segment
            **kwargs: Variables to substitute in the prompt
            
        Returns:
            Tuple of (formatted_text, variant_id)
        """
        variant = self.get_variant(test_name, user_id, user_segment)
        
        # Track that the prompt was shown
        self.track_event(test_name, variant.variant_id, user_id, 'shown', user_segment)
        
        # Format the prompt with any provided variables
        text = variant.text
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass  # Some placeholders not provided
        
        return text, variant.variant_id
    
    def track_conversion(
        self,
        test_name: str,
        user_id: str,
        variant_id: str,
        user_segment: UserSegment = UserSegment.NEW_USER
    ):
        """
        Track a conversion event.
        
        Args:
            test_name: Name of the test
            user_id: User identifier
            variant_id: Variant ID
            user_segment: User's segment
        """
        self.track_event(test_name, variant_id, user_id, 'converted', user_segment)
    
    def track_click(
        self,
        test_name: str,
        user_id: str,
        variant_id: str,
        user_segment: UserSegment = UserSegment.NEW_USER
    ):
        """
        Track a click event.
        
        Args:
            test_name: Name of the test
            user_id: User identifier
            variant_id: Variant ID
            user_segment: User's segment
        """
        self.track_event(test_name, variant_id, user_id, 'clicked', user_segment)


# Singleton instance
_ab_testing_manager: Optional[ABTestingManager] = None


def get_ab_testing_manager() -> ABTestingManager:
    """Get or create the singleton A/B testing manager."""
    global _ab_testing_manager
    if _ab_testing_manager is None:
        _ab_testing_manager = ABTestingManager()
    return _ab_testing_manager


def get_prompt_variant(
    test_name: str,
    user_id: str,
    user_segment: UserSegment = UserSegment.NEW_USER,
    **kwargs
) -> Tuple[str, str]:
    """
    Convenience function to get a formatted prompt variant.
    
    Args:
        test_name: Name of the test
        user_id: User identifier
        user_segment: User's segment
        **kwargs: Variables to substitute in the prompt
        
    Returns:
        Tuple of (formatted_text, variant_id)
    """
    manager = get_ab_testing_manager()
    return manager.format_prompt(test_name, user_id, user_segment, **kwargs)


def determine_user_segment(
    total_queries: int = 0,
    investment_focus: float = 0.0,
    locations_explored: int = 0
) -> UserSegment:
    """
    Determine user segment based on behavior.
    
    Args:
        total_queries: Total number of queries
        investment_focus: Investment focus score (0-1)
        locations_explored: Number of locations explored
        
    Returns:
        UserSegment enum value
    """
    if total_queries == 0:
        return UserSegment.NEW_USER
    elif total_queries >= 20:
        return UserSegment.POWER_USER
    elif total_queries >= 5:
        return UserSegment.ACTIVE_USER
    elif investment_focus > 0.5:
        return UserSegment.INVESTMENT_FOCUSED
    elif locations_explored >= 3:
        return UserSegment.EXPLORER
    else:
        return UserSegment.CASUAL_USER
