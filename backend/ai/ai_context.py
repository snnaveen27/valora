"""
AI Context & Self-Learning Module for Valora
Enables the AI to understand itself, learn from interactions, and maintain context.

Features:
1. System Self-Awareness - AI knows its own capabilities
2. Interaction Learning - Learns from user queries and outcomes
3. Context Accumulation - Builds understanding over sessions
4. Knowledge Graph - Maintains entity relationships
5. Query Pattern Recognition - Identifies common query patterns
6. Feedback Integration - Learns from user corrections
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib


@dataclass
class SystemCapability:
    """Describes a system capability."""
    name: str
    description: str
    module: str
    example_queries: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    accuracy: float = 0.8


@dataclass
class LearnedPattern:
    """A learned query pattern."""
    pattern_id: str
    pattern_type: str  # location_search, comparison, simulation, etc.
    example_queries: List[str] = field(default_factory=list)
    successful_responses: int = 0
    total_uses: int = 0
    avg_satisfaction: float = 0.0
    last_used: str = ""


@dataclass
class EntityKnowledge:
    """Knowledge about an entity (location, building, etc.)."""
    entity_id: str
    entity_type: str
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    mentions: int = 0
    last_queried: str = ""


@dataclass
class AIContext:
    """Complete AI context state."""
    session_id: str
    capabilities: List[SystemCapability] = field(default_factory=list)
    learned_patterns: List[LearnedPattern] = field(default_factory=list)
    entity_knowledge: Dict[str, EntityKnowledge] = field(default_factory=dict)
    recent_queries: List[Dict[str, Any]] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    system_stats: Dict[str, Any] = field(default_factory=dict)


class AIContextManager:
    """
    Manages AI context, learning, and self-awareness.
    """
    
    # Define system capabilities
    SYSTEM_CAPABILITIES = [
        SystemCapability(
            name="Property Search",
            description="Find properties based on location, price, BHK, amenities",
            module="property_service.py",
            example_queries=[
                "Find 3BHK apartments in Koramangala under 1 crore",
                "Show me properties near metro station",
                "Apartments with gym and pool in HSR"
            ],
            data_sources=["properties (42,202 listings)"],
            accuracy=0.9
        ),
        SystemCapability(
            name="3D Building Analysis",
            description="Analyze building height, shadow, view quality, neighbors",
            module="building_analyzer.py",
            example_queries=[
                "What's the view from this building?",
                "How many taller buildings are nearby?",
                "Shadow impact analysis"
            ],
            data_sources=["buildings (1.37M with heights)"],
            accuracy=0.85
        ),
        SystemCapability(
            name="Spatial Reasoning",
            description="Understand spatial relationships, distances, accessibility",
            module="spatial_nlp.py, spatial_inference.py",
            example_queries=[
                "Properties near Indiranagar metro",
                "What's within walking distance?",
                "Compare Whitefield vs Koramangala"
            ],
            data_sources=["pois, transport_stops, terrain_grid"],
            accuracy=0.88
        ),
        SystemCapability(
            name="Price Prediction",
            description="Forecast property values, investment recommendations",
            module="predictive_model.py",
            example_queries=[
                "What will prices be in 5 years?",
                "Is this a good investment?",
                "Market cycle analysis"
            ],
            data_sources=["properties, price_history, terrain_grid"],
            accuracy=0.75
        ),
        SystemCapability(
            name="What-If Simulation",
            description="Simulate infrastructure changes and their impact",
            module="simulation_engine.py",
            example_queries=[
                "What if a metro station opens here?",
                "Impact of new IT park",
                "Zoning change effects"
            ],
            data_sources=["buildings, properties, pois"],
            accuracy=0.7
        ),
        SystemCapability(
            name="Area Analysis",
            description="Analyze neighborhoods, amenities, connectivity",
            module="area_analyzer.py, spatial_reasoning.py",
            example_queries=[
                "Tell me about Koramangala",
                "What's the area like?",
                "Walkability score"
            ],
            data_sources=["places, pois, transport_stops, gov_data"],
            accuracy=0.85
        ),
        SystemCapability(
            name="Terrain Analysis",
            description="Elevation, flood risk, construction suitability",
            module="terrain_service.py",
            example_queries=[
                "Is this area flood-prone?",
                "Elevation analysis",
                "Construction suitability"
            ],
            data_sources=["terrain_grid (9,090 cells)"],
            accuracy=0.8
        ),
        SystemCapability(
            name="Visual Analysis",
            description="Property image analysis (when Qwen VL available)",
            module="visual_analyzer.py",
            example_queries=[
                "Rate this property from photos",
                "What style is this building?",
                "Condition assessment"
            ],
            data_sources=["property photos"],
            accuracy=0.7
        ),
    ]
    
    def __init__(self, session_id: str = "default", db_path: str = None):
        self.session_id = session_id
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
        
        self.context = AIContext(
            session_id=session_id,
            capabilities=self.SYSTEM_CAPABILITIES.copy()
        )
        
        self._load_learned_patterns()
        self._load_system_stats()
    
    def _load_learned_patterns(self):
        """Load previously learned patterns from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if learning table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='ai_learning'
            """)
            if not cursor.fetchone():
                # Create learning table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ai_learning (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern_id TEXT UNIQUE,
                        pattern_type TEXT,
                        pattern_data TEXT,
                        successful_uses INTEGER DEFAULT 0,
                        total_uses INTEGER DEFAULT 0,
                        avg_satisfaction REAL DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create feedback table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ai_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT,
                        response_quality TEXT,
                        user_correction TEXT,
                        session_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create entity knowledge table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ai_entity_knowledge (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        entity_id TEXT UNIQUE,
                        entity_type TEXT,
                        name TEXT,
                        attributes TEXT,
                        relationships TEXT,
                        mentions INTEGER DEFAULT 1,
                        last_queried TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            
            # Load existing patterns
            cursor.execute("SELECT * FROM ai_learning ORDER BY total_uses DESC LIMIT 100")
            for row in cursor.fetchall():
                try:
                    pattern_data = json.loads(row['pattern_data']) if row['pattern_data'] else {}
                    pattern = LearnedPattern(
                        pattern_id=row['pattern_id'],
                        pattern_type=row['pattern_type'],
                        example_queries=pattern_data.get('examples', []),
                        successful_responses=row['successful_uses'],
                        total_uses=row['total_uses'],
                        avg_satisfaction=row['avg_satisfaction'],
                        last_used=str(row['updated_at'])
                    )
                    self.context.learned_patterns.append(pattern)
                except:
                    pass
            
            conn.close()
        except Exception as e:
            print(f"[AIContext] Error loading patterns: {e}")
    
    def _load_system_stats(self):
        """Load system statistics from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            # Property count
            cursor.execute("SELECT COUNT(*) FROM properties")
            stats['total_properties'] = cursor.fetchone()[0]
            
            # Building count
            cursor.execute("SELECT COUNT(*) FROM buildings")
            stats['total_buildings'] = cursor.fetchone()[0]
            
            # POI count
            cursor.execute("SELECT COUNT(*) FROM pois")
            stats['total_pois'] = cursor.fetchone()[0]
            
            # Transport count
            cursor.execute("SELECT COUNT(*) FROM transport_stops")
            stats['total_transport'] = cursor.fetchone()[0]
            
            # Places count
            cursor.execute("SELECT COUNT(*) FROM places")
            stats['total_places'] = cursor.fetchone()[0]
            
            # Terrain coverage
            cursor.execute("SELECT COUNT(*) FROM terrain_grid")
            stats['terrain_cells'] = cursor.fetchone()[0]
            
            # Properties with analytics
            cursor.execute("SELECT COUNT(*) FROM property_analytics")
            stats['properties_with_analytics'] = cursor.fetchone()[0]
            
            self.context.system_stats = stats
            conn.close()
        except Exception as e:
            print(f"[AIContext] Error loading stats: {e}")
    
    def get_self_description(self) -> str:
        """Generate AI's description of its own capabilities."""
        desc = []
        desc.append("I am Valora AI, a city intelligence assistant for Bangalore real estate.")
        desc.append(f"\n**My Knowledge Base:**")
        desc.append(f"- {self.context.system_stats.get('total_properties', 0):,} property listings")
        desc.append(f"- {self.context.system_stats.get('total_buildings', 0):,} 3D building models")
        desc.append(f"- {self.context.system_stats.get('total_pois', 0):,} points of interest")
        desc.append(f"- {self.context.system_stats.get('total_transport', 0):,} transport stops")
        desc.append(f"- {self.context.system_stats.get('terrain_cells', 0):,} terrain analysis cells")
        
        desc.append(f"\n**My Capabilities:**")
        for cap in self.context.capabilities:
            desc.append(f"- **{cap.name}** ({cap.accuracy*100:.0f}% accuracy): {cap.description}")
        
        if self.context.learned_patterns:
            desc.append(f"\n**Learned from {len(self.context.learned_patterns)} query patterns**")
        
        return "\n".join(desc)
    
    def record_query(self, query: str, intent: str, entities: List[str], 
                    response_quality: str = None):
        """Record a query for learning."""
        query_record = {
            'query': query,
            'intent': intent,
            'entities': entities,
            'timestamp': datetime.now().isoformat(),
            'quality': response_quality
        }
        self.context.recent_queries.append(query_record)
        
        # Keep only recent 100 queries
        if len(self.context.recent_queries) > 100:
            self.context.recent_queries = self.context.recent_queries[-100:]
        
        # Update entity knowledge
        for entity in entities:
            self._update_entity_knowledge(entity, query)
        
        # Learn pattern
        self._learn_pattern(query, intent)
    
    def _update_entity_knowledge(self, entity_name: str, query: str):
        """Update knowledge about an entity."""
        entity_id = hashlib.md5(entity_name.lower().encode()).hexdigest()[:12]
        
        if entity_id in self.context.entity_knowledge:
            self.context.entity_knowledge[entity_id].mentions += 1
            self.context.entity_knowledge[entity_id].last_queried = datetime.now().isoformat()
        else:
            # Try to determine entity type
            entity_type = 'location'
            name_lower = entity_name.lower()
            if any(w in name_lower for w in ['apartment', 'flat', 'villa', 'property']):
                entity_type = 'property_type'
            elif any(w in name_lower for w in ['metro', 'bus', 'station']):
                entity_type = 'transport'
            elif any(w in name_lower for w in ['school', 'hospital', 'mall', 'park']):
                entity_type = 'poi'
            
            self.context.entity_knowledge[entity_id] = EntityKnowledge(
                entity_id=entity_id,
                entity_type=entity_type,
                name=entity_name,
                mentions=1,
                last_queried=datetime.now().isoformat()
            )
    
    def _learn_pattern(self, query: str, intent: str):
        """Learn from a query pattern."""
        pattern_id = f"{intent}_{hashlib.md5(query.lower().encode()).hexdigest()[:8]}"
        
        # Check if similar pattern exists
        for pattern in self.context.learned_patterns:
            if pattern.pattern_type == intent:
                # Add to existing pattern
                if query not in pattern.example_queries:
                    pattern.example_queries.append(query)
                    if len(pattern.example_queries) > 10:
                        pattern.example_queries = pattern.example_queries[-10:]
                pattern.total_uses += 1
                pattern.last_used = datetime.now().isoformat()
                return
        
        # Create new pattern
        new_pattern = LearnedPattern(
            pattern_id=pattern_id,
            pattern_type=intent,
            example_queries=[query],
            total_uses=1,
            last_used=datetime.now().isoformat()
        )
        self.context.learned_patterns.append(new_pattern)
    
    def record_feedback(self, query: str, quality: str, correction: str = None):
        """Record user feedback for learning."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ai_feedback (query, response_quality, user_correction, session_id)
                VALUES (?, ?, ?, ?)
            """, (query, quality, correction, self.session_id))
            
            conn.commit()
            conn.close()
            
            # Update pattern success rates
            for pattern in self.context.learned_patterns:
                if query in pattern.example_queries:
                    if quality in ['good', 'excellent']:
                        pattern.successful_responses += 1
                    pattern.avg_satisfaction = (
                        pattern.successful_responses / pattern.total_uses
                        if pattern.total_uses > 0 else 0
                    )
        except Exception as e:
            print(f"[AIContext] Error recording feedback: {e}")
    
    def save_learning(self):
        """Save learned patterns to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for pattern in self.context.learned_patterns:
                cursor.execute("""
                    INSERT OR REPLACE INTO ai_learning (
                        pattern_id, pattern_type, pattern_data, 
                        successful_uses, total_uses, avg_satisfaction, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.pattern_id,
                    pattern.pattern_type,
                    json.dumps({'examples': pattern.example_queries}),
                    pattern.successful_responses,
                    pattern.total_uses,
                    pattern.avg_satisfaction,
                    datetime.now().isoformat()
                ))
            
            # Save entity knowledge
            for entity_id, entity in self.context.entity_knowledge.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO ai_entity_knowledge (
                        entity_id, entity_type, name, attributes, relationships, 
                        mentions, last_queried
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity.entity_id,
                    entity.entity_type,
                    entity.name,
                    json.dumps(entity.attributes),
                    json.dumps(entity.relationships),
                    entity.mentions,
                    entity.last_queried
                ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[AIContext] Error saving learning: {e}")
    
    def get_relevant_context(self, query: str) -> Dict[str, Any]:
        """Get relevant context for a query."""
        context = {
            'capabilities': [],
            'similar_patterns': [],
            'relevant_entities': [],
            'system_stats': self.context.system_stats
        }
        
        query_lower = query.lower()
        
        # Find relevant capabilities
        for cap in self.context.capabilities:
            for example in cap.example_queries:
                if any(word in query_lower for word in example.lower().split()):
                    context['capabilities'].append({
                        'name': cap.name,
                        'module': cap.module,
                        'accuracy': cap.accuracy
                    })
                    break
        
        # Find similar patterns
        for pattern in self.context.learned_patterns:
            for example in pattern.example_queries:
                if any(word in query_lower for word in example.lower().split()):
                    context['similar_patterns'].append({
                        'type': pattern.pattern_type,
                        'success_rate': pattern.avg_satisfaction,
                        'uses': pattern.total_uses
                    })
                    break
        
        # Find relevant entities
        for entity_id, entity in self.context.entity_knowledge.items():
            if entity.name.lower() in query_lower:
                context['relevant_entities'].append({
                    'name': entity.name,
                    'type': entity.entity_type,
                    'mentions': entity.mentions
                })
        
        return context
    
    def get_improvement_suggestions(self) -> List[str]:
        """Suggest areas for improvement based on learning."""
        suggestions = []
        
        # Check for low-performing patterns
        for pattern in self.context.learned_patterns:
            if pattern.total_uses >= 5 and pattern.avg_satisfaction < 0.5:
                suggestions.append(
                    f"Low satisfaction ({pattern.avg_satisfaction:.0%}) for {pattern.pattern_type} queries"
                )
        
        # Check for underused capabilities
        used_capabilities = set()
        for pattern in self.context.learned_patterns:
            used_capabilities.add(pattern.pattern_type)
        
        for cap in self.context.capabilities:
            cap_key = cap.name.lower().replace(' ', '_')
            if cap_key not in used_capabilities:
                suggestions.append(f"'{cap.name}' capability rarely used")
        
        # Check system stats
        stats = self.context.system_stats
        if stats.get('properties_with_analytics', 0) < stats.get('total_properties', 1) * 0.5:
            suggestions.append("Less than 50% of properties have pre-computed analytics")
        
        return suggestions


# Singleton instance
_ai_context_manager = None


def get_ai_context(session_id: str = "default") -> AIContextManager:
    """Get or create AI context manager."""
    global _ai_context_manager
    if _ai_context_manager is None or _ai_context_manager.session_id != session_id:
        _ai_context_manager = AIContextManager(session_id)
    return _ai_context_manager
