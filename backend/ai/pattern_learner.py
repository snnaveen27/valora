"""
Query Pattern Learning System for Valora Brain
Parses QUERIES_LIST.md to extract query patterns and intents
Provides fast pattern matching for intent classification
"""

import re
import json
import sqlite3
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime


@dataclass
class QueryPattern:
    """Represents a learned query pattern"""
    pattern_id: str
    query_text: str
    intent: str
    expected_tasks: List[str]
    category: str  # e.g., "navigation", "property_search", "analysis"
    confidence: float = 0.9
    usage_count: int = 0
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class QueryPatternLearner:
    """
    Learns query patterns from QUERIES_LIST.md and user interactions
    Provides fast pattern matching for intent classification
    """
    
    def __init__(self, db_path: str = "backend/valora_patterns.db"):
        self.db_path = db_path
        self._init_database()
        self._patterns_cache = {}  # In-memory cache
        self._load_patterns()
    
    def _init_database(self):
        """Initialize SQLite database for patterns"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    expected_tasks TEXT,  -- JSON list
                    category TEXT,
                    confidence REAL DEFAULT 0.9,
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    last_used TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_intent 
                ON query_patterns(intent)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_category 
                ON query_patterns(category)
            """)
            
            conn.commit()
    
    def load_from_queries_list(self, queries_file: str = "docs/QUERIES_LIST.md") -> int:
        """
        Parse QUERIES_LIST.md and extract query patterns
        Returns number of patterns loaded
        """
        if not Path(queries_file).exists():
            print(f"[PatternLearner] {queries_file} not found, skipping load")
            return 0
        
        patterns = []
        content = Path(queries_file).read_text(encoding='utf-8')
        
        # Extract navigation patterns (with emoji tolerant regex)
        nav_patterns = self._extract_patterns_from_section(
            content, 
            "Navigation.*Location",
            "navigate"
        )
        patterns.extend(nav_patterns)
        
        # Extract property search patterns
        search_patterns = self._extract_patterns_from_section(
            content,
            "Property.*Search",
            "property_search"
        )
        patterns.extend(search_patterns)
        
        # Extract area analysis patterns
        analysis_patterns = self._extract_patterns_from_section(
            content,
            "Area.*Analysis",
            "analyze_area"
        )
        patterns.extend(analysis_patterns)
        
        # Extract comparison patterns
        compare_patterns = self._extract_patterns_from_section(
            content,
            "Comparative|Comparison",
            "comparison"
        )
        patterns.extend(compare_patterns)
        
        # Extract simulation patterns
        sim_patterns = self._extract_patterns_from_section(
            content,
            "Simulation",
            "simulate"
        )
        patterns.extend(sim_patterns)
        
        # Extract valuation patterns
        val_patterns = self._extract_patterns_from_section(
            content,
            "Valuation|Dynamic.*Valuation",
            "valuation"
        )
        patterns.extend(val_patterns)
        
        # Save to database
        count = 0
        for pattern in patterns:
            if self._save_pattern(pattern):
                count += 1
        
        self._load_patterns()  # Reload cache
        print(f"[PatternLearner] Loaded {count} patterns from {queries_file}")
        return count
    
    def _extract_patterns_from_section(
        self, 
        content: str, 
        section_pattern: str,
        intent: str
    ) -> List[QueryPattern]:
        """Extract query examples from a markdown section using flexible regex"""
        patterns = []
        
        # Find section with emoji-tolerant regex
        # Match ## followed by any characters, then section pattern
        regex = rf'^##\s*.*?{section_pattern}.*?$'
        
        # Find all section starts
        sections = list(re.finditer(r'^##\s+.*$', content, re.MULTILINE | re.IGNORECASE))
        
        section_content = None
        for i, section_match in enumerate(sections):
            section_title = section_match.group(0)
            if re.search(section_pattern, section_title, re.IGNORECASE):
                # Found matching section, extract until next ## or end
                start_pos = section_match.end()
                end_pos = sections[i + 1].start() if i + 1 < len(sections) else len(content)
                section_content = content[start_pos:end_pos]
                break
        
        if not section_content:
            return patterns
        
        # Extract code blocks (queries are often in ``` blocks)
        code_blocks = re.findall(r'```\n(.*?)\n```', section_content, re.DOTALL)
        
        for block in code_blocks:
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            for line in lines:
                # Skip non-query lines (headers, comments, etc.)
                if self._is_valid_query(line):
                    pattern = QueryPattern(
                        pattern_id=self._generate_pattern_id(line),
                        query_text=line,
                        intent=intent,
                        expected_tasks=self._infer_tasks(intent),
                        category=intent,
                        confidence=0.9
                    )
                    patterns.append(pattern)
        
        # Also extract inline queries (not in code blocks)
        # Look for patterns like "Find 2BHK..." or "Analyze..."
        inline_queries = re.findall(
            r'(?:^|\n)(?:\d+\.\s*)?["\']?((?:Find|Show|Analyze|Compare|Go to|Navigate|What if|Estimate).+?)["\']?(?=\n|$)',
            section_content,
            re.MULTILINE | re.IGNORECASE
        )
        
        for query in inline_queries:
            if self._is_valid_query(query) and len(query) > 10:
                pattern = QueryPattern(
                    pattern_id=self._generate_pattern_id(query),
                    query_text=query,
                    intent=intent,
                    expected_tasks=self._infer_tasks(intent),
                    category=intent,
                    confidence=0.85
                )
                # Avoid duplicates
                if pattern.pattern_id not in [p.pattern_id for p in patterns]:
                    patterns.append(pattern)
        
        return patterns
    
    def _is_valid_query(self, text: str) -> bool:
        """Check if text looks like a valid user query"""
        if len(text) < 5 or len(text) > 200:
            return False
        
        # Skip markdown headers, comments, etc.
        invalid_prefixes = ['#', '-', '*', '|', 'Expected:', 'Note:', '**']
        if any(text.startswith(p) for p in invalid_prefixes):
            return False
        
        # Should contain some real content (not just code)
        if text.startswith('`') or text.startswith('http'):
            return False
        
        return True
    
    def _infer_tasks(self, intent: str) -> List[str]:
        """Infer expected tasks for an intent"""
        task_map = {
            "navigate": ["geocode_location", "fly_to_map", "show_context"],
            "property_search": ["parse_filters", "search_properties", "rank_results", "show_on_map"],
            "analyze_area": ["fetch_area_data", "compute_metrics", "generate_insights", "show_charts"],
            "comparison": ["fetch_area_data", "compute_comparison", "generate_analysis"],
            "simulate": ["parse_scenario", "run_simulation", "generate_impact", "create_storyboard"],
            "valuation": ["fetch_comparables", "compute_valuation", "generate_report"],
            "analyze_building": ["fetch_building_data", "3d_analysis", "generate_insights"],
            "general": ["understand_query", "generate_response"]
        }
        return task_map.get(intent, ["process_query"])
    
    def _generate_pattern_id(self, query: str) -> str:
        """Generate unique ID for a query pattern"""
        return hashlib.md5(query.lower().encode()).hexdigest()[:16]
    
    def _save_pattern(self, pattern: QueryPattern) -> bool:
        """Save pattern to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO query_patterns 
                    (pattern_id, query_text, intent, expected_tasks, category, 
                     confidence, usage_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.pattern_id,
                    pattern.query_text,
                    pattern.intent,
                    json.dumps(pattern.expected_tasks),
                    pattern.category,
                    pattern.confidence,
                    pattern.usage_count,
                    pattern.created_at
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"[PatternLearner] Error saving pattern: {e}")
            return False
    
    def _load_patterns(self):
        """Load all patterns into memory cache"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM query_patterns")
                rows = cursor.fetchall()
                
                self._patterns_cache = {}
                for row in rows:
                    pattern = QueryPattern(
                        pattern_id=row['pattern_id'],
                        query_text=row['query_text'],
                        intent=row['intent'],
                        expected_tasks=json.loads(row['expected_tasks'] or '[]'),
                        category=row['category'],
                        confidence=row['confidence'],
                        usage_count=row['usage_count'],
                        created_at=row['created_at']
                    )
                    self._patterns_cache[pattern.pattern_id] = pattern
                
                print(f"[PatternLearner] Loaded {len(self._patterns_cache)} patterns into cache")
        except Exception as e:
            print(f"[PatternLearner] Error loading patterns: {e}")
    
    def find_matching_pattern(self, query: str, threshold: float = 0.7) -> Optional[QueryPattern]:
        """
        Find best matching pattern for a query
        Uses exact match first, then fuzzy matching
        """
        query_lower = query.lower().strip()
        query_hash = self._generate_pattern_id(query)
        
        # Check exact match first
        if query_hash in self._patterns_cache:
            pattern = self._patterns_cache[query_hash]
            pattern.usage_count += 1
            self._update_usage(pattern.pattern_id)
            return pattern
        
        # Fuzzy matching
        best_match = None
        best_score = 0.0
        
        for pattern in self._patterns_cache.values():
            score = self._compute_similarity(query_lower, pattern.query_text.lower())
            if score > best_score and score >= threshold:
                best_score = score
                best_match = pattern
        
        if best_match:
            best_match.usage_count += 1
            self._update_usage(best_match.pattern_id)
            # Update confidence based on match score
            best_match.confidence = best_score
        
        return best_match
    
    def _compute_similarity(self, query1: str, query2: str) -> float:
        """Compute similarity between two queries (0-1)"""
        # Exact match
        if query1 == query2:
            return 1.0
        
        # Contains match (one is substring of other)
        if query1 in query2 or query2 in query1:
            return 0.9
        
        # Word overlap (Jaccard similarity)
        words1 = set(query1.split())
        words2 = set(query2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        jaccard = len(intersection) / len(union)
        
        # Boost for keyword matches (location names, property types)
        keywords = ['whitefield', 'koramangala', 'indiranagar', 'hsr', '2bhk', '3bhk', 
                   'apartment', 'villa', 'analyze', 'compare', 'find', 'search']
        keyword_matches = sum(1 for k in keywords if k in query1 and k in query2)
        keyword_boost = min(keyword_matches * 0.1, 0.3)
        
        return min(jaccard + keyword_boost, 1.0)
    
    def _update_usage(self, pattern_id: str):
        """Update usage count and last_used timestamp"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE query_patterns 
                    SET usage_count = usage_count + 1,
                        last_used = ?
                    WHERE pattern_id = ?
                """, (datetime.now().isoformat(), pattern_id))
                conn.commit()
        except Exception as e:
            print(f"[PatternLearner] Error updating usage: {e}")
    
    def learn_from_interaction(self, query: str, intent: str, tasks: List[str], success: bool):
        """Learn from a new user interaction"""
        pattern_id = self._generate_pattern_id(query)
        
        # Check if pattern exists
        if pattern_id in self._patterns_cache:
            # Update existing pattern
            pattern = self._patterns_cache[pattern_id]
            if success:
                pattern.confidence = min(pattern.confidence + 0.01, 1.0)
            else:
                pattern.confidence = max(pattern.confidence - 0.05, 0.5)
            pattern.usage_count += 1
            self._save_pattern(pattern)
        else:
            # Create new pattern
            category = intent
            new_pattern = QueryPattern(
                pattern_id=pattern_id,
                query_text=query,
                intent=intent,
                expected_tasks=tasks,
                category=category,
                confidence=0.8 if success else 0.6,
                usage_count=1
            )
            if self._save_pattern(new_pattern):
                self._patterns_cache[pattern_id] = new_pattern
                print(f"[PatternLearner] Learned new pattern: {query[:50]}...")
    
    def get_patterns_by_intent(self, intent: str) -> List[QueryPattern]:
        """Get all patterns for a specific intent"""
        return [p for p in self._patterns_cache.values() if p.intent == intent]
    
    def get_stats(self) -> Dict:
        """Get pattern learning statistics"""
        return {
            "total_patterns": len(self._patterns_cache),
            "patterns_by_intent": {
                intent: len(self.get_patterns_by_intent(intent))
                for intent in set(p.intent for p in self._patterns_cache.values())
            },
            "most_used": sorted(
                self._patterns_cache.values(),
                key=lambda p: p.usage_count,
                reverse=True
            )[:10],
            "high_confidence": len([p for p in self._patterns_cache.values() if p.confidence > 0.9])
        }


# Singleton instance
_learner_instance: Optional[QueryPatternLearner] = None

def get_pattern_learner(db_path: str = "backend/valora_patterns.db") -> QueryPatternLearner:
    """Get or create singleton pattern learner"""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = QueryPatternLearner(db_path)
    return _learner_instance


def initialize_patterns_from_queries_list():
    """Initialize pattern database from QUERIES_LIST.md"""
    learner = get_pattern_learner()
    count = learner.load_from_queries_list("docs/QUERIES_LIST.md")
    print(f"[PatternLearner] Initialized with {count} patterns")
    return count
