"""
Smart Query Suggestions
Suggests relevant queries based on user's partial input and context
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class QuerySuggestion:
    """A suggested query."""
    query: str
    category: str
    description: str
    priority: int = 0


class QuerySuggestionEngine:
    """Generates smart query suggestions."""
    
    # Common query templates organized by category
    TEMPLATES = {
        "property_search": [
            "3 BHK apartments in {area}",
            "Properties near metro under {price}",
            "Villas in {area} for sale",
            "2 BHK flats for rent in {area}",
            "Luxury apartments in {area}",
            "Commercial properties in {area}",
            "Plots for sale in {area}",
        ],
        "area_analysis": [
            "Analyze {area}",
            "What's the area like in {area}",
            "Infrastructure in {area}",
            "Connectivity of {area}",
            "Schools and hospitals near {area}",
            "Safety and livability of {area}",
        ],
        "comparison": [
            "Compare {area1} and {area2}",
            "Which is better - {area1} or {area2}",
            "{area1} vs {area2} for investment",
            "Property prices {area1} vs {area2}",
        ],
        "valuation": [
            "Property value in {area}",
            "Price trend in {area}",
            "Is {area} expensive",
            "Average price per sqft in {area}",
        ],
        "simulation": [
            "What if metro comes to {area}",
            "Impact of new highway in {area}",
            "Simulate IT park in {area}",
        ],
    }
    
    # Popular areas in Bangalore
    POPULAR_AREAS = [
        "Indiranagar", "Whitefield", "Koramangala", "HSR Layout",
        "Electronic City", "Marathahalli", "Bannerghatta Road",
        "Hebbal", "Yelahanka", "JP Nagar", "Jayanagar",
        "BTM Layout", "Sarjapur Road", "Bellandur"
    ]
    
    # Common price ranges
    PRICE_RANGES = [
        "50 lakhs", "75 lakhs", "1 crore", "1.5 crore", "2 crore"
    ]
    
    def __init__(self):
        self.suggestion_cache = {}
    
    def get_suggestions(
        self,
        partial_query: str = "",
        user_context: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> List[QuerySuggestion]:
        """
        Get query suggestions based on partial input and context.
        
        Args:
            partial_query: User's partial typed query
            user_context: Context like current location, recent queries, etc.
            limit: Max suggestions to return
        """
        suggestions = []
        
        # If empty, show popular queries
        if not partial_query or len(partial_query) < 3:
            suggestions.extend(self._get_popular_suggestions(user_context))
        else:
            # Get context-aware suggestions
            suggestions.extend(self._get_contextual_suggestions(partial_query, user_context))
        
        # Sort by priority and limit
        suggestions.sort(key=lambda x: x.priority, reverse=True)
        return suggestions[:limit]
    
    def _get_popular_suggestions(self, context: Optional[Dict] = None) -> List[QuerySuggestion]:
        """Get popular/trending queries."""
        popular = [
            QuerySuggestion(
                "3 BHK apartments in Indiranagar",
                "property_search",
                "Popular property search",
                priority=10
            ),
            QuerySuggestion(
                "Compare Whitefield and Electronic City",
                "comparison",
                "Popular comparison",
                priority=9
            ),
            QuerySuggestion(
                "Analyze HSR Layout",
                "area_analysis",
                "Popular area analysis",
                priority=8
            ),
            QuerySuggestion(
                "Properties near metro under 1 crore",
                "property_search",
                "Budget property search",
                priority=7
            ),
            QuerySuggestion(
                "Price trend in Koramangala",
                "valuation",
                "Market analysis",
                priority=6
            ),
        ]
        
        # Customize based on context
        if context and context.get('selected_area'):
            area = context['selected_area']
            popular.insert(0, QuerySuggestion(
                f"Analyze {area}",
                "area_analysis",
                f"Analyze your current area",
                priority=15
            ))
        
        return popular
    
    def _get_contextual_suggestions(
        self,
        partial: str,
        context: Optional[Dict] = None
    ) -> List[QuerySuggestion]:
        """Get suggestions based on what user is typing."""
        suggestions = []
        partial_lower = partial.lower()
        
        # Check for property search keywords
        if any(kw in partial_lower for kw in ['bhk', 'apartment', 'flat', 'property', 'villa', 'house']):
            for area in self.POPULAR_AREAS:
                if partial_lower in area.lower() or area.lower() in partial_lower:
                    suggestions.append(QuerySuggestion(
                        f"3 BHK apartments in {area}",
                        "property_search",
                        f"Properties in {area}",
                        priority=12
                    ))
        
        # Check for comparison keywords
        if any(kw in partial_lower for kw in ['compare', 'vs', 'versus', 'or']):
            for area in self.POPULAR_AREAS[:5]:
                suggestions.append(QuerySuggestion(
                    f"Compare {area} and Whitefield",
                    "comparison",
                    f"Compare areas",
                    priority=11
                ))
        
        # Check for area analysis
        if any(kw in partial_lower for kw in ['analyze', 'about', 'what', 'how is']):
            for area in self.POPULAR_AREAS:
                if area.lower() in partial_lower:
                    suggestions.append(QuerySuggestion(
                        f"Analyze {area}",
                        "area_analysis",
                        f"Detailed area analysis",
                        priority=13
                    ))
        
        # Check for price/valuation keywords
        if any(kw in partial_lower for kw in ['price', 'value', 'cost', 'trend']):
            for area in self.POPULAR_AREAS[:5]:
                suggestions.append(QuerySuggestion(
                    f"Price trend in {area}",
                    "valuation",
                    f"Market trends",
                    priority=10
                ))
        
        # Check for simulation keywords
        if any(kw in partial_lower for kw in ['what if', 'simulate', 'impact']):
            suggestions.append(QuerySuggestion(
                "What if metro comes to HSR Layout",
                "simulation",
                "Infrastructure impact simulation",
                priority=14
            ))
        
        # Match specific areas mentioned
        for area in self.POPULAR_AREAS:
            if area.lower() in partial_lower:
                # Add area-specific suggestions
                suggestions.append(QuerySuggestion(
                    f"Properties near metro in {area}",
                    "property_search",
                    f"Find properties in {area}",
                    priority=11
                ))
                suggestions.append(QuerySuggestion(
                    f"Infrastructure in {area}",
                    "area_analysis",
                    f"{area} amenities and connectivity",
                    priority=10
                ))
        
        return suggestions
    
    def get_followup_suggestions(
        self,
        previous_query: str,
        previous_intent: str
    ) -> List[QuerySuggestion]:
        """Get relevant follow-up suggestions based on previous query."""
        suggestions = []
        
        if previous_intent == "property_search":
            suggestions.extend([
                QuerySuggestion(
                    "Show me similar properties",
                    "property_search",
                    "Find similar listings",
                    priority=10
                ),
                QuerySuggestion(
                    "Analyze the area",
                    "area_analysis",
                    "Learn about the locality",
                    priority=9
                ),
                QuerySuggestion(
                    "Price trends here",
                    "valuation",
                    "Check market trends",
                    priority=8
                ),
            ])
        
        elif previous_intent == "area_analysis":
            suggestions.extend([
                QuerySuggestion(
                    "Find properties here",
                    "property_search",
                    "Available properties",
                    priority=10
                ),
                QuerySuggestion(
                    "Compare with nearby areas",
                    "comparison",
                    "Area comparison",
                    priority=9
                ),
            ])
        
        elif previous_intent == "comparison":
            suggestions.extend([
                QuerySuggestion(
                    "Show properties in better area",
                    "property_search",
                    "Properties in recommended area",
                    priority=10
                ),
            ])
        
        return suggestions


# Singleton instance
_suggestion_engine: Optional[QuerySuggestionEngine] = None


def get_suggestion_engine() -> QuerySuggestionEngine:
    """Get or create suggestion engine singleton."""
    global _suggestion_engine
    if _suggestion_engine is None:
        _suggestion_engine = QuerySuggestionEngine()
    return _suggestion_engine
