"""
Valora Brain - Unified AI System with Map Actions
Core orchestrator with systematic query handling and GIS operations
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class MapAction:
    """Represents a map UI action"""
    action: str  # flyTo, drawPolygon, drawRoute, markBuilding, addLayer, etc.
    params: Dict[str, Any]
    purpose: str
    priority: int = 1  # 1=high, 2=medium, 3=low

@dataclass
class GISOperation:
    """Represents a GIS analysis operation"""
    operation: str  # spatialQuery, proximitySearch, viewshed, etc.
    inputs: Dict[str, Any]
    expected_output: str

@dataclass
class QueryIntent:
    """Parsed intent from user query"""
    intent_type: str
    confidence: float
    slots: Dict[str, Any]
    map_actions: List[MapAction]
    gis_operations: List[GISOperation]
    reasoning: str

class ValoraBrainCore:
    """
    Core Valora Brain with systematic query handling
    Understands GIS operations and map actions
    """
    
    # Intent types with their patterns
    INTENT_PATTERNS = {
        "navigate": {
            "patterns": ["go to", "take me to", "navigate to", "fly to", "where is", "explore"],
            "slots": ["location", "coordinates"],
            "default_actions": [
                {"action": "flyTo", "params": {"location": "{location}", "zoom": 16}, "purpose": "Navigate to area"},
                {"action": "addLayer", "params": {"layer": "context"}, "purpose": "Show area context"}
            ]
        },
        "property_search": {
            "patterns": ["find", "search", "looking for", "show me", "properties", "apartments", "flats",
                         "houses", "villas", "plots", "land", "bhk", "top properties", "best properties",
                         "available", "listings", "for sale", "for rent", "budget", "under", "below"],
            "slots": ["bhk", "location", "budget", "amenities", "property_type"],
            "default_actions": [
                {"action": "flyTo", "params": {"location": "{location}", "zoom": 15}, "purpose": "Show search area"},
                {"action": "markProperties", "params": {"filter": "{filter}"}, "purpose": "Highlight matching properties"}
            ]
        },
        "analyze_area": {
            "patterns": ["analyze", "tell me about", "how is", "what about", "insights on",
                         "good for", "suitable for", "livability", "infrastructure", "connectivity",
                         "amenities in", "amenities around", "top amenities", "facilities",
                         "schools near", "hospitals near", "metro near", "pois near",
                         "walkability", "tell me everything", "deep dive", "overview of",
                         "neighborhood", "locality", "what are the",
                         "flood", "flooding", "safe from", "risk", "drainage",
                         "elevation", "terrain", "slope", "livable", "family friendly"],
            "slots": ["location", "metrics"],
            "default_actions": [
                {"action": "flyTo", "params": {"location": "{location}", "zoom": 15}, "purpose": "Focus on area"},
                {"action": "addLayer", "params": {"layer": "analytics"}, "purpose": "Show analysis overlay"},
                {"action": "orbit", "params": {"center": "{location}", "duration": 5000}, "purpose": "360° area view"}
            ]
        },
        "price_trend": {
            "patterns": ["price trend", "price history", "price growth",
                         "price movement", "market trend", "price forecast", "price prediction",
                         "how much has", "price change", "rental yield", "rental trend",
                         "price per sqft", "price per sq", "average price", "median price",
                         "price distribution", "price range"],
            "slots": ["location", "time_period"],
            "default_actions": [
                {"action": "flyTo", "params": {"location": "{location}", "zoom": 14}, "purpose": "Focus on area"},
                {"action": "showChart", "params": {"type": "price_trend", "location": "{location}"}, "purpose": "Display price chart"}
            ]
        },
        "building_analysis": {
            "patterns": ["this building", "analyze building", "building details", "building info",
                         "what building", "building height", "building type", "structure",
                         "construction", "floors", "stories", "levels"],
            "slots": ["building_id", "coordinates"],
            "default_actions": [
                {"action": "highlightBuilding", "params": {"building_id": "{building_id}"}, "purpose": "Highlight selected building"},
                {"action": "showBuildingInfo", "params": {"building_id": "{building_id}"}, "purpose": "Show building details"}
            ]
        },
        "investment": {
            "patterns": ["best investment", "investment potential", "roi", "return on", "profitable",
                         "growth potential", "capital appreciation", "best area to buy",
                         "where should i buy", "hotspot", "emerging area",
                         "invest in bangalore", "investment properties",
                         "appreciation areas", "areas for buying", "high appreciation",
                         "good investment", "invest in"],
            "slots": ["location", "budget", "investment_type"],
            "default_actions": [
                {"action": "flyTo", "params": {"location": "{location}", "zoom": 13}, "purpose": "Show investment area"},
                {"action": "addLayer", "params": {"layer": "heatmap"}, "purpose": "Show investment heatmap"}
            ]
        },
        "draw_polygon": {
            "patterns": ["draw", "create polygon", "mark area", "highlight zone", "buffer"],
            "slots": ["location", "radius", "coordinates"],
            "default_actions": [
                {"action": "drawPolygon", "params": {"center": "{location}", "radius": "{radius}"}, "purpose": "Visualize area"},
                {"action": "spatialQuery", "params": {"polygon": "drawn"}, "purpose": "Query within polygon"}
            ]
        },
        "comparison": {
            "patterns": ["compare", "versus", "vs", "which is better", "difference between",
                         "better area", "which area", " or "],
            "slots": ["location_a", "location_b"],
            "default_actions": [
                {"action": "splitView", "params": {"left": "{location_a}", "right": "{location_b}"}, "purpose": "Side-by-side comparison"},
                {"action": "markAreas", "params": {"areas": ["{location_a}", "{location_b}"]}, "purpose": "Highlight both areas"}
            ]
        },
        "route_analysis": {
            "patterns": ["route", "commute", "travel time", "drive from", "distance to",
                         "how far", "how long", "nearest metro", "nearest station"],
            "slots": ["from_location", "to_location"],
            "default_actions": [
                {"action": "drawRoute", "params": {"from": "{from_location}", "to": "{to_location}"}, "purpose": "Show commute route"},
                {"action": "flyTo", "params": {"bounds": "route", "padding": 0.2}, "purpose": "Show full route"}
            ]
        },
        "simulate": {
            "patterns": ["what if", "simulate", "scenario", "impact", "happens when",
                         "effect of", "consequence", "predict"],
            "slots": ["scenario_type", "location", "change"],
            "default_actions": [
                {"action": "flyTo", "params": {"location": "{location}", "zoom": 14}, "purpose": "Focus on impact area"},
                {"action": "addLayer", "params": {"layer": "simulation"}, "purpose": "Show simulation overlay"},
                {"action": "animateScenario", "params": {"scenario": "{scenario_type}"}, "purpose": "Visualize impact"}
            ]
        }
    }
    
    def __init__(self):
        self.session_context = {}
        self.query_history = []
    
    async def process(self, query: str, context: Optional[Dict] = None) -> QueryIntent:
        """
        Process user query and return structured intent with map actions
        """
        query_lower = query.lower()
        
        # Step 1: Classify intent
        intent_type, confidence = self._classify_intent(query_lower)
        
        # Step 2: Extract slots
        slots = self._extract_slots(query, intent_type)
        
        # Step 3: Generate map actions based on intent
        map_actions = self._generate_map_actions(intent_type, slots)
        
        # Step 4: Generate GIS operations
        gis_operations = self._generate_gis_operations(intent_type, slots)
        
        # Step 5: Build reasoning
        reasoning = self._build_reasoning(intent_type, slots, map_actions)
        
        return QueryIntent(
            intent_type=intent_type,
            confidence=confidence,
            slots=slots,
            map_actions=map_actions,
            gis_operations=gis_operations,
            reasoning=reasoning
        )
    
    def _classify_intent(self, query: str) -> tuple:
        """Classify query intent using pattern matching with specificity tiebreaking"""
        scores = {}
        
        for intent, config in self.INTENT_PATTERNS.items():
            score = 0
            matched_len = 0
            for pattern in config["patterns"]:
                if pattern in query:
                    score += 1
                    matched_len += len(pattern)
            scores[intent] = (score, matched_len)
        
        # Get highest scoring intent (score first, then matched_len for specificity)
        if scores:
            best_intent = max(scores, key=lambda k: (scores[k][0], scores[k][1]))
            best_score = scores[best_intent][0]
            if best_score > 0:
                confidence = min(0.6 + (best_score * 0.1), 0.95)
                return best_intent, confidence
        
        return "general", 0.5
    
    def _extract_slots(self, query: str, intent: str) -> Dict[str, Any]:
        """Extract relevant slots from query"""
        import re
        
        slots = {}
        query_lower = query.lower()
        
        # Extract BHK
        bhk_match = re.search(r'(\d)\s*bhk', query_lower)
        if bhk_match:
            slots['bhk'] = int(bhk_match.group(1))
        
        # Extract budget
        budget_patterns = [
            r'(?:under|below|within)\s+(\d+(?:\.\d+)?)\s*(lakh|lac|crore|cr)',
            r'(\d+(?:\.\d+)?)\s*(lakh|lac|crore|cr)'
        ]
        for pattern in budget_patterns:
            budget_match = re.search(pattern, query_lower)
            if budget_match:
                amount = float(budget_match.group(1))
                unit = budget_match.group(2)
                if unit in ['crore', 'cr']:
                    slots['budget'] = amount * 10000000
                else:
                    slots['budget'] = amount * 100000
                break
        
        # Extract radius/distance
        radius_match = re.search(r'(\d+(?:\.\d+)?)\s*(km|m|meters?)', query_lower)
        if radius_match:
            value = float(radius_match.group(1))
            unit = radius_match.group(2)
            if unit == 'km':
                slots['radius'] = value * 1000  # Convert to meters
            else:
                slots['radius'] = value
        
        # Extract location using common Bangalore area names
        bangalore_areas = [
            'whitefield', 'koramangala', 'indiranagar', 'hsr layout', 'electronic city',
            'marathahalli', 'sarjapur', 'bellandur', 'hebbal', 'jayanagar', 'btm layout',
            'jp nagar', 'mg road', 'manyata', 'yelahanka', 'doddanekundi', 'mahadevapura',
            'bannerghatta', 'rajajinagar', 'malleswaram', 'malleshwaram', 'basavanagudi',
            'vijayanagar', 'banashankari', 'yeshwanthpur', 'devanahalli', 'silk board',
            'sarjapur road', 'outer ring road', 'old madiwala', 'hsr', 'bommanahalli',
            'begur', 'kudlu', 'kanakapura', 'tumkur road', 'mysore road', 'hosur road',
            'nagarbhavi', 'rajarajeshwari nagar', 'kengeri', 'uttarahalli', 'vidyaranyapura',
            'hennur', 'thanisandra', 'jakkur', 'sahakara nagar', 'sadashivanagar',
            'richmond town', 'shivajinagar', 'cunningham road', 'brigade road',
            'lavelle road', 'residency road', 'ulsoor', 'frazer town', 'cox town',
            'benson town', 'rt nagar', 'kammanahalli', 'kalyan nagar', 'banaswadi',
            'ramamurthy nagar', 'kr puram', 'mahadevapura', 'varthur', 'kadugodi',
            'hoodi', 'brookefield', 'kundalahalli', 'doddanekundi',
            'harlur', 'haralur', 'kasavanahalli', 'carmelaram', 'chandra layout',
            'vijayanagar', 'nagarbhavi', 'govindarajanagar', 'peenya'
        ]
        
        # Sort by length (longest first) so "hsr layout" matches before "hsr"
        bangalore_areas.sort(key=len, reverse=True)
        for area in bangalore_areas:
            if area in query_lower:
                slots['location'] = area
                break
        
        # Extract comparison locations (location_a vs location_b)
        import re as _re
        vs_match = _re.search(r'(\w[\w\s]+?)\s+(?:vs|versus|or|compared to|compared with)\s+(\w[\w\s]+)', query_lower)
        if vs_match:
            loc_a = vs_match.group(1).strip()
            loc_b = vs_match.group(2).strip()
            # Clean up common prefixes
            for prefix in ['compare ', 'which is better ', 'between ']:
                if loc_a.startswith(prefix):
                    loc_a = loc_a[len(prefix):]
            slots['location_a'] = loc_a
            slots['location_b'] = loc_b
            if not slots.get('location'):
                slots['location'] = loc_a
        
        # Extract coordinates if present
        coord_match = re.search(r'(\d+\.\d+)\s*,?\s*(\d+\.\d+)', query)
        if coord_match:
            slots['coordinates'] = {
                'lat': float(coord_match.group(1)),
                'lng': float(coord_match.group(2))
            }
        
        # Extract amenities
        amenities = []
        amenity_keywords = ['school', 'hospital', 'metro', 'park', 'gym', 'mall', 'restaurant']
        for amenity in amenity_keywords:
            if amenity in query_lower:
                amenities.append(amenity)
        if amenities:
            slots['amenities'] = amenities
        
        return slots
    
    def _generate_map_actions(self, intent: str, slots: Dict) -> List[MapAction]:
        """Generate appropriate map actions for the intent"""
        actions = []
        
        if intent not in self.INTENT_PATTERNS:
            return actions
        
        config = self.INTENT_PATTERNS[intent]
        
        for action_def in config.get("default_actions", []):
            # Fill in slot values
            params = {}
            for key, value in action_def["params"].items():
                if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                    slot_key = value[1:-1]  # Remove braces
                    if slot_key in slots:
                        params[key] = slots[slot_key]
                    else:
                        params[key] = None
                else:
                    params[key] = value
            
            actions.append(MapAction(
                action=action_def["action"],
                params=params,
                purpose=action_def["purpose"],
                priority=1
            ))
        
        return actions
    
    def _generate_gis_operations(self, intent: str, slots: Dict) -> List[GISOperation]:
        """Generate GIS operations based on intent"""
        operations = []
        
        if intent == "property_search":
            operations.append(GISOperation(
                operation="spatialQuery",
                inputs={
                    "location": slots.get('location'),
                    "radius": slots.get('radius', 2000),
                    "filters": {
                        "bhk": slots.get('bhk'),
                        "budget_max": slots.get('budget')
                    }
                },
                expected_output="property_list"
            ))
        
        elif intent == "analyze_area":
            operations.append(GISOperation(
                operation="areaMetrics",
                inputs={
                    "location": slots.get('location'),
                    "metrics": ["price_trend", "livability", "connectivity", "risk"]
                },
                expected_output="area_profile"
            ))
        
        elif intent == "draw_polygon":
            operations.append(GISOperation(
                operation="spatialQuery",
                inputs={
                    "polygon": "user_drawn",
                    "query_type": "properties"
                },
                expected_output="properties_in_polygon"
            ))
        
        elif intent == "route_analysis":
            operations.append(GISOperation(
                operation="routeAnalysis",
                inputs={
                    "from": slots.get('from_location'),
                    "to": slots.get('to_location'),
                    "mode": "driving"
                },
                expected_output="route_with_metrics"
            ))
        
        return operations
    
    def _build_reasoning(self, intent: str, slots: Dict, actions: List[MapAction]) -> str:
        """Build human-readable reasoning for the query processing"""
        reasoning_parts = []
        
        reasoning_parts.append(f"Detected intent: {intent}")
        
        if slots:
            slot_desc = ", ".join([f"{k}={v}" for k, v in slots.items() if v])
            reasoning_parts.append(f"Extracted: {slot_desc}")
        
        if actions:
            action_desc = " → ".join([a.action for a in actions])
            reasoning_parts.append(f"Map actions: {action_desc}")
        
        return "; ".join(reasoning_parts)
    
    def to_json(self, intent: QueryIntent) -> Dict:
        """Convert intent to JSON-serializable dict"""
        return {
            "intent_type": intent.intent_type,
            "confidence": intent.confidence,
            "slots": intent.slots,
            "map_actions": [
                {
                    "action": a.action,
                    "params": a.params,
                    "purpose": a.purpose,
                    "priority": a.priority
                }
                for a in intent.map_actions
            ],
            "gis_operations": [
                {
                    "operation": g.operation,
                    "inputs": g.inputs,
                    "expected_output": g.expected_output
                }
                for g in intent.gis_operations
            ],
            "reasoning": intent.reasoning
        }


# Singleton instance
_brain_instance = None

def get_valora_brain() -> ValoraBrainCore:
    """Get or create Valora Brain singleton"""
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = ValoraBrainCore()
    return _brain_instance
