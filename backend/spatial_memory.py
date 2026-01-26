"""
Spatial Memory Service for Valora AI
Phase 2.2: Session-based location memory and preference learning

Features:
- Session-based location memory
- Preference learning from interactions
- Comparison history tracking
- Context-aware suggestions
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
from pathlib import Path
import math


@dataclass
class LocationVisit:
    """Represents a visited location"""
    lat: float
    lng: float
    name: str
    timestamp: str
    intent: str  # What the user was looking for
    duration_seconds: float = 0  # How long they stayed
    actions_taken: List[str] = field(default_factory=list)  # clicks, queries, etc.
    sentiment: str = "neutral"  # positive, neutral, negative (inferred)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass  
class UserPreferences:
    """Learned user preferences from interactions"""
    preferred_areas: List[str] = field(default_factory=list)  # Areas visited multiple times
    preferred_property_types: List[str] = field(default_factory=list)
    budget_range: Optional[Tuple[float, float]] = None  # (min, max) in lakhs
    preferred_amenities: List[str] = field(default_factory=list)
    avoid_areas: List[str] = field(default_factory=list)  # Areas with negative sentiment
    exploration_style: str = "balanced"  # "focused", "exploratory", "balanced"
    
    def to_dict(self) -> Dict:
        return {
            "preferred_areas": self.preferred_areas,
            "preferred_property_types": self.preferred_property_types,
            "budget_range": self.budget_range,
            "preferred_amenities": self.preferred_amenities,
            "avoid_areas": self.avoid_areas,
            "exploration_style": self.exploration_style
        }


@dataclass
class ComparisonEntry:
    """A comparison the user made"""
    location_a: Dict[str, Any]
    location_b: Dict[str, Any]
    timestamp: str
    winner: Optional[str] = None  # Which one user preferred
    factors_compared: List[str] = field(default_factory=list)


class SpatialMemoryService:
    """
    Manages spatial memory for user sessions.
    Tracks exploration history, learns preferences, enables smart suggestions.
    """
    
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.visit_history: List[LocationVisit] = []
        self.comparisons: List[ComparisonEntry] = []
        self.preferences = UserPreferences()
        self.current_location: Optional[LocationVisit] = None
        self.session_start = datetime.now().isoformat()
        
        # Load persisted memory if exists
        self._load_session()
    
    def _get_memory_path(self) -> Path:
        """Get path to session memory file."""
        memory_dir = Path(__file__).parent / 'session_memory'
        memory_dir.mkdir(exist_ok=True)
        return memory_dir / f"{self.session_id}.json"
    
    def _load_session(self):
        """Load session from disk if exists."""
        path = self._get_memory_path()
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.visit_history = [
                        LocationVisit(**v) for v in data.get('visits', [])
                    ]
                    self.preferences = UserPreferences(**data.get('preferences', {}))
                    self.comparisons = [
                        ComparisonEntry(**c) for c in data.get('comparisons', [])
                    ]
            except Exception as e:
                print(f"[SpatialMemory] Load error: {e}")
    
    def _save_session(self):
        """Persist session to disk."""
        path = self._get_memory_path()
        try:
            data = {
                'session_id': self.session_id,
                'session_start': self.session_start,
                'visits': [v.to_dict() for v in self.visit_history],
                'preferences': self.preferences.to_dict(),
                'comparisons': [asdict(c) for c in self.comparisons],
                'last_updated': datetime.now().isoformat()
            }
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[SpatialMemory] Save error: {e}")
    
    def record_visit(self, lat: float, lng: float, name: str, intent: str,
                     actions: List[str] = None, sentiment: str = "neutral"):
        """Record a location visit."""
        # Calculate duration if we have a previous location
        duration = 0
        if self.current_location:
            try:
                prev_time = datetime.fromisoformat(self.current_location.timestamp)
                duration = (datetime.now() - prev_time).total_seconds()
                self.current_location.duration_seconds = duration
            except:
                pass
        
        visit = LocationVisit(
            lat=lat,
            lng=lng,
            name=name,
            timestamp=datetime.now().isoformat(),
            intent=intent,
            actions_taken=actions or [],
            sentiment=sentiment
        )
        
        self.visit_history.append(visit)
        self.current_location = visit
        
        # Update preferences based on visit
        self._update_preferences_from_visit(visit)
        
        # Persist
        self._save_session()
    
    def _update_preferences_from_visit(self, visit: LocationVisit):
        """Learn preferences from visit patterns."""
        # Track frequently visited areas
        area_visits = {}
        for v in self.visit_history:
            name = v.name.lower()
            area_visits[name] = area_visits.get(name, 0) + 1
        
        # Areas visited 2+ times are preferred
        self.preferences.preferred_areas = [
            area for area, count in area_visits.items() if count >= 2
        ][:5]  # Top 5
        
        # Track areas with negative sentiment
        negative_areas = set()
        for v in self.visit_history:
            if v.sentiment == "negative":
                negative_areas.add(v.name.lower())
        self.preferences.avoid_areas = list(negative_areas)[:3]
        
        # Determine exploration style
        unique_locations = len(set(v.name for v in self.visit_history))
        total_visits = len(self.visit_history)
        
        if total_visits > 0:
            uniqueness_ratio = unique_locations / total_visits
            if uniqueness_ratio > 0.8:
                self.preferences.exploration_style = "exploratory"
            elif uniqueness_ratio < 0.4:
                self.preferences.exploration_style = "focused"
            else:
                self.preferences.exploration_style = "balanced"
    
    def record_comparison(self, location_a: Dict, location_b: Dict, 
                         winner: str = None, factors: List[str] = None):
        """Record a comparison between locations."""
        comparison = ComparisonEntry(
            location_a=location_a,
            location_b=location_b,
            timestamp=datetime.now().isoformat(),
            winner=winner,
            factors_compared=factors or []
        )
        self.comparisons.append(comparison)
        self._save_session()
    
    def get_exploration_summary(self) -> Dict[str, Any]:
        """Get summary of exploration session."""
        if not self.visit_history:
            return {"message": "No locations explored yet"}
        
        # Calculate stats
        total_visits = len(self.visit_history)
        unique_areas = len(set(v.name for v in self.visit_history))
        
        # Time spent
        total_time = sum(v.duration_seconds for v in self.visit_history)
        
        # Most visited
        area_counts = {}
        for v in self.visit_history:
            area_counts[v.name] = area_counts.get(v.name, 0) + 1
        most_visited = sorted(area_counts.items(), key=lambda x: -x[1])[:3]
        
        # Intent distribution
        intent_counts = {}
        for v in self.visit_history:
            intent_counts[v.intent] = intent_counts.get(v.intent, 0) + 1
        
        return {
            "total_visits": total_visits,
            "unique_areas": unique_areas,
            "total_time_minutes": round(total_time / 60, 1),
            "most_visited": most_visited,
            "intent_distribution": intent_counts,
            "exploration_style": self.preferences.exploration_style,
            "preferred_areas": self.preferences.preferred_areas,
            "comparisons_made": len(self.comparisons)
        }
    
    def get_context_for_query(self, current_lat: float = None, 
                              current_lng: float = None) -> str:
        """Generate context string for LLM based on memory."""
        parts = []
        
        # Recent history
        if self.visit_history:
            recent = self.visit_history[-5:]
            parts.append("**Recent Exploration:**")
            for v in recent:
                parts.append(f"  - {v.name} ({v.intent})")
        
        # Preferences
        if self.preferences.preferred_areas:
            parts.append(f"**User prefers:** {', '.join(self.preferences.preferred_areas)}")
        
        if self.preferences.avoid_areas:
            parts.append(f"**User avoiding:** {', '.join(self.preferences.avoid_areas)}")
        
        parts.append(f"**Exploration style:** {self.preferences.exploration_style}")
        
        # Comparisons
        if self.comparisons:
            parts.append(f"**Comparisons made:** {len(self.comparisons)}")
            last_comp = self.comparisons[-1]
            parts.append(f"  Last compared: {last_comp.location_a.get('name', 'A')} vs {last_comp.location_b.get('name', 'B')}")
        
        return "\n".join(parts) if parts else ""
    
    def suggest_next_locations(self, current_lat: float, current_lng: float,
                               limit: int = 3) -> List[Dict[str, Any]]:
        """Suggest next locations based on exploration history."""
        suggestions = []
        
        # If exploratory, suggest new areas
        if self.preferences.exploration_style == "exploratory":
            # Suggest areas NOT in history
            visited_names = {v.name.lower() for v in self.visit_history}
            # Would normally query database for nearby areas
            # For now, return concept
            suggestions.append({
                "type": "explore_new",
                "reason": "You seem to enjoy exploring. Try a new area!"
            })
        
        # If focused, suggest similar to preferred
        elif self.preferences.exploration_style == "focused":
            if self.preferences.preferred_areas:
                suggestions.append({
                    "type": "similar_to_preferred",
                    "areas": self.preferences.preferred_areas,
                    "reason": f"Based on your interest in {self.preferences.preferred_areas[0]}"
                })
        
        # Suggest based on comparison patterns
        if self.comparisons:
            last_winner = self.comparisons[-1].winner
            if last_winner:
                suggestions.append({
                    "type": "compare_similar",
                    "reason": f"You preferred {last_winner}. Want to compare more options?"
                })
        
        return suggestions[:limit]
    
    def get_first_location(self) -> Optional[Dict[str, Any]]:
        """Get the first explored location (for 'compare with earlier')."""
        if self.visit_history:
            first = self.visit_history[0]
            return {
                "name": first.name,
                "lat": first.lat,
                "lng": first.lng,
                "intent": first.intent
            }
        return None
    
    def find_similar_to_current(self, current_lat: float, current_lng: float,
                                 radius_km: float = 5) -> List[LocationVisit]:
        """Find previously visited locations similar to current."""
        similar = []
        for visit in self.visit_history:
            # Calculate distance
            dist = self._haversine(current_lat, current_lng, visit.lat, visit.lng)
            if dist <= radius_km and dist > 0.1:  # Within radius but not same spot
                similar.append(visit)
        return similar
    
    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in km between two points."""
        R = 6371  # Earth radius in km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def clear_session(self):
        """Clear current session memory."""
        self.visit_history = []
        self.comparisons = []
        self.preferences = UserPreferences()
        self.current_location = None
        
        # Delete persisted file
        path = self._get_memory_path()
        if path.exists():
            path.unlink()


# Session storage
_sessions: Dict[str, SpatialMemoryService] = {}


def get_spatial_memory(session_id: str = "default") -> SpatialMemoryService:
    """Get or create spatial memory for a session."""
    if session_id not in _sessions:
        _sessions[session_id] = SpatialMemoryService(session_id)
    return _sessions[session_id]
