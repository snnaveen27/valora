"""
Spatial NLP - Natural Language Understanding for Geospatial Queries
Bridges text understanding with spatial reasoning.

Key Features:
1. Spatial Relation Extraction ("near", "between", "within")
2. Directional Understanding ("north of", "across from")
3. Distance Interpretation ("5 min walk", "nearby", "close to")
4. Comparative Spatial Reasoning ("closer to X than Y")
5. Place Name Resolution with context
6. Spatial Constraint Parsing for property search

This module does NOT require external models like SpatialLM.
Uses rule-based NLP + local geocoding + spatial calculations.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import math


class SpatialRelation(Enum):
    """Types of spatial relationships."""
    NEAR = "near"
    WITHIN = "within"
    BETWEEN = "between"
    ADJACENT = "adjacent"
    FACING = "facing"
    OPPOSITE = "opposite"
    SURROUNDING = "surrounding"
    ALONG = "along"


class Direction(Enum):
    """Cardinal and intercardinal directions."""
    NORTH = "north"
    NORTHEAST = "northeast"
    EAST = "east"
    SOUTHEAST = "southeast"
    SOUTH = "south"
    SOUTHWEST = "southwest"
    WEST = "west"
    NORTHWEST = "northwest"
    CENTER = "center"


@dataclass
class SpatialEntity:
    """A resolved spatial entity (place, landmark, etc.)."""
    name: str
    entity_type: str  # location, landmark, poi, property, area
    lat: Optional[float] = None
    lng: Optional[float] = None
    confidence: float = 0.0
    aliases: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpatialConstraint:
    """A parsed spatial constraint from text."""
    relation: SpatialRelation
    reference_entity: Optional[SpatialEntity] = None
    direction: Optional[Direction] = None
    distance_m: Optional[float] = None
    distance_text: str = ""
    is_negated: bool = False


@dataclass
class ParsedSpatialQuery:
    """Fully parsed spatial query."""
    original_query: str
    intent: str
    entities: List[SpatialEntity] = field(default_factory=list)
    constraints: List[SpatialConstraint] = field(default_factory=list)
    property_filters: Dict[str, Any] = field(default_factory=dict)
    spatial_scope: Optional[Dict[str, float]] = None  # bbox or center+radius
    confidence: float = 0.0
    reasoning: List[str] = field(default_factory=list)


class DistanceParser:
    """Parses distance expressions from text."""
    
    # Distance patterns with approximate meters
    DISTANCE_PATTERNS = [
        # Exact distances
        (r'(\d+(?:\.\d+)?)\s*(?:km|kilometer|kilometres?)', lambda m: float(m.group(1)) * 1000),
        (r'(\d+(?:\.\d+)?)\s*(?:m|meter|metres?)\b', lambda m: float(m.group(1))),
        (r'(\d+(?:\.\d+)?)\s*(?:feet|ft)\b', lambda m: float(m.group(1)) * 0.3048),
        
        # Time-based distances (walking ~80m/min, driving ~500m/min in city)
        (r'(\d+)\s*(?:min|minute)s?\s*walk', lambda m: float(m.group(1)) * 80),
        (r'(\d+)\s*(?:min|minute)s?\s*(?:drive|driving)', lambda m: float(m.group(1)) * 500),
        (r'(\d+)\s*(?:min|minute)s?\s*(?:cycle|cycling|bike)', lambda m: float(m.group(1)) * 250),
        
        # Qualitative distances
        (r'\b(?:very\s+)?close\s+(?:to|by)\b', lambda m: 300),
        (r'\bnear(?:by)?\b', lambda m: 500),
        (r'\bwalking\s+distance\b', lambda m: 800),
        (r'\bshort\s+(?:walk|distance)\b', lambda m: 500),
        (r'\bwithin\s+reach\b', lambda m: 1000),
        (r'\bnot\s+(?:too\s+)?far\b', lambda m: 1500),
        (r'\breasonable\s+distance\b', lambda m: 2000),
        (r'\bfar\s+from\b', lambda m: 5000),
    ]
    
    @classmethod
    def parse(cls, text: str) -> Tuple[Optional[float], str]:
        """
        Parse distance from text.
        Returns (distance_meters, matched_text).
        """
        text_lower = text.lower()
        
        for pattern, extractor in cls.DISTANCE_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    distance = extractor(match)
                    return (distance, match.group(0))
                except:
                    pass
        
        return (None, "")


class DirectionParser:
    """Parses directional expressions from text."""
    
    DIRECTION_PATTERNS = {
        Direction.NORTH: [r'\bnorth\s+of\b', r'\bnorthern\s+(?:part|side|area)\b', r'\babove\b'],
        Direction.SOUTH: [r'\bsouth\s+of\b', r'\bsouthern\s+(?:part|side|area)\b', r'\bbelow\b'],
        Direction.EAST: [r'\beast\s+of\b', r'\beastern\s+(?:part|side|area)\b'],
        Direction.WEST: [r'\bwest\s+of\b', r'\bwestern\s+(?:part|side|area)\b'],
        Direction.NORTHEAST: [r'\bnorth\s*east\s+of\b', r'\bne\s+of\b'],
        Direction.NORTHWEST: [r'\bnorth\s*west\s+of\b', r'\bnw\s+of\b'],
        Direction.SOUTHEAST: [r'\bsouth\s*east\s+of\b', r'\bse\s+of\b'],
        Direction.SOUTHWEST: [r'\bsouth\s*west\s+of\b', r'\bsw\s+of\b'],
    }
    
    @classmethod
    def parse(cls, text: str) -> Optional[Direction]:
        """Extract direction from text."""
        text_lower = text.lower()
        
        for direction, patterns in cls.DIRECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return direction
        
        return None
    
    @classmethod
    def get_direction_offset(cls, direction: Direction, distance_m: float = 1000) -> Tuple[float, float]:
        """
        Get lat/lng offset for a direction.
        Returns (lat_offset, lng_offset) in degrees.
        """
        # Approximate: 1 degree lat = 111km, 1 degree lng = 111km * cos(lat)
        # For Bangalore (~13°N), cos(13°) ≈ 0.97
        lat_per_m = 1 / 111000
        lng_per_m = 1 / (111000 * 0.97)
        
        offsets = {
            Direction.NORTH: (distance_m * lat_per_m, 0),
            Direction.SOUTH: (-distance_m * lat_per_m, 0),
            Direction.EAST: (0, distance_m * lng_per_m),
            Direction.WEST: (0, -distance_m * lng_per_m),
            Direction.NORTHEAST: (distance_m * lat_per_m * 0.707, distance_m * lng_per_m * 0.707),
            Direction.NORTHWEST: (distance_m * lat_per_m * 0.707, -distance_m * lng_per_m * 0.707),
            Direction.SOUTHEAST: (-distance_m * lat_per_m * 0.707, distance_m * lng_per_m * 0.707),
            Direction.SOUTHWEST: (-distance_m * lat_per_m * 0.707, -distance_m * lng_per_m * 0.707),
            Direction.CENTER: (0, 0),
        }
        
        return offsets.get(direction, (0, 0))


class SpatialRelationParser:
    """Parses spatial relationship expressions."""
    
    RELATION_PATTERNS = {
        SpatialRelation.NEAR: [
            r'\bnear(?:by)?\s+(?:to\s+)?(.+?)(?:\s+and|\s+with|\s*$|\s*,)',
            r'\bclose\s+to\s+(.+?)(?:\s+and|\s+with|\s*$|\s*,)',
            r'\baround\s+(.+?)(?:\s+and|\s+with|\s*$|\s*,)',
            r'\bin\s+the\s+vicinity\s+of\s+(.+?)(?:\s+and|\s*$)',
        ],
        SpatialRelation.WITHIN: [
            r'\bwithin\s+(?:\d+\s*(?:km|m|min))?\s*(?:of\s+)?(.+?)(?:\s+and|\s*$)',
            r'\binside\s+(.+?)(?:\s+and|\s*$)',
            r'\bin\s+(.+?)(?:\s+area|\s+locality|\s+neighborhood)?(?:\s+and|\s*$)',
        ],
        SpatialRelation.BETWEEN: [
            r'\bbetween\s+(.+?)\s+and\s+(.+?)(?:\s*$|\s*,)',
        ],
        SpatialRelation.ADJACENT: [
            r'\badjacent\s+to\s+(.+?)(?:\s+and|\s*$)',
            r'\bnext\s+to\s+(.+?)(?:\s+and|\s*$)',
            r'\bbeside\s+(.+?)(?:\s+and|\s*$)',
        ],
        SpatialRelation.FACING: [
            r'\bfacing\s+(.+?)(?:\s+and|\s*$)',
            r'\bopposite\s+(?:to\s+)?(.+?)(?:\s+and|\s*$)',
            r'\bacross\s+from\s+(.+?)(?:\s+and|\s*$)',
        ],
        SpatialRelation.ALONG: [
            r'\balong\s+(.+?)(?:\s+road|\s+street)?(?:\s+and|\s*$)',
            r'\bon\s+(.+?)\s+(?:road|street|avenue|main)(?:\s+and|\s*$)',
        ],
    }
    
    @classmethod
    def parse(cls, text: str) -> List[Tuple[SpatialRelation, List[str]]]:
        """
        Extract spatial relations and referenced entities from text.
        Returns list of (relation, [entity_names]).
        """
        results = []
        text_lower = text.lower()
        
        for relation, patterns in cls.RELATION_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                for match in matches:
                    if isinstance(match, tuple):
                        entities = [m.strip() for m in match if m.strip()]
                    else:
                        entities = [match.strip()] if match.strip() else []
                    
                    if entities:
                        results.append((relation, entities))
        
        return results


class PropertyFilterParser:
    """Parses property-specific filters from text."""
    
    BUDGET_PATTERNS = [
        (r'(?:under|below|less than|max|maximum|upto|up to)\s*(?:rs\.?|₹)?\s*(\d+(?:\.\d+)?)\s*(lakh|lac|cr|crore)', 'max'),
        (r'(?:above|over|more than|min|minimum|at least)\s*(?:rs\.?|₹)?\s*(\d+(?:\.\d+)?)\s*(lakh|lac|cr|crore)', 'min'),
        (r'(?:rs\.?|₹)?\s*(\d+(?:\.\d+)?)\s*(lakh|lac|cr|crore)\s*(?:to|-)\s*(?:rs\.?|₹)?\s*(\d+(?:\.\d+)?)\s*(lakh|lac|cr|crore)', 'range'),
        (r'(?:budget|price)\s*(?:is|of|:)?\s*(?:rs\.?|₹)?\s*(\d+(?:\.\d+)?)\s*(lakh|lac|cr|crore)', 'exact'),
    ]
    
    BHK_PATTERNS = [
        (r'(\d+)\s*bhk', 'exact'),
        (r'(\d+)\s*(?:bed|bedroom)s?', 'exact'),
        (r'(\d+)\s*(?:to|-)\s*(\d+)\s*bhk', 'range'),
    ]
    
    TYPE_PATTERNS = {
        'apartment': [r'\bapartment\b', r'\bflat\b'],
        'villa': [r'\bvilla\b', r'\bindependent\s+house\b'],
        'plot': [r'\bplot\b', r'\bland\b', r'\bsite\b'],
        'commercial': [r'\bcommercial\b', r'\boffice\b', r'\bshop\b'],
        'pg': [r'\bpg\b', r'\bpaying\s+guest\b'],
        'rental': [r'\brent(?:al)?\b', r'\bfor\s+rent\b'],
    }
    
    @classmethod
    def parse(cls, text: str) -> Dict[str, Any]:
        """Extract property filters from text."""
        filters = {}
        text_lower = text.lower()
        
        # Parse budget
        for pattern, budget_type in cls.BUDGET_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                groups = match.groups()
                if budget_type == 'range' and len(groups) >= 4:
                    min_val = cls._to_lakhs(float(groups[0]), groups[1])
                    max_val = cls._to_lakhs(float(groups[2]), groups[3])
                    filters['budget_min'] = min_val
                    filters['budget_max'] = max_val
                elif budget_type == 'max':
                    filters['budget_max'] = cls._to_lakhs(float(groups[0]), groups[1])
                elif budget_type == 'min':
                    filters['budget_min'] = cls._to_lakhs(float(groups[0]), groups[1])
                elif budget_type == 'exact':
                    val = cls._to_lakhs(float(groups[0]), groups[1])
                    filters['budget_min'] = val * 0.8  # 20% below
                    filters['budget_max'] = val * 1.2  # 20% above
                break
        
        # Parse BHK
        for pattern, bhk_type in cls.BHK_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                if bhk_type == 'range':
                    filters['bhk_min'] = int(match.group(1))
                    filters['bhk_max'] = int(match.group(2))
                else:
                    filters['bhk'] = int(match.group(1))
                break
        
        # Parse property type
        for prop_type, patterns in cls.TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    filters['property_type'] = prop_type
                    break
        
        # Parse area (sqft)
        area_match = re.search(r'(\d+)\s*(?:to|-)\s*(\d+)\s*(?:sqft|sq\.?\s*ft|sft)', text_lower)
        if area_match:
            filters['area_min'] = int(area_match.group(1))
            filters['area_max'] = int(area_match.group(2))
        else:
            area_match = re.search(r'(\d+)\s*(?:sqft|sq\.?\s*ft|sft)', text_lower)
            if area_match:
                val = int(area_match.group(1))
                filters['area_min'] = int(val * 0.8)
                filters['area_max'] = int(val * 1.2)
        
        return filters
    
    @staticmethod
    def _to_lakhs(value: float, unit: str) -> float:
        """Convert to lakhs."""
        unit = unit.lower()
        if unit in ['cr', 'crore']:
            return value * 100
        return value  # Already in lakhs


class SpatialNLP:
    """
    Main Spatial NLP Engine.
    Combines all parsers to understand spatial queries.
    """
    
    def __init__(self, geocoder=None, db_service=None):
        self.geocoder = geocoder
        self.db_service = db_service
        self.distance_parser = DistanceParser()
        self.direction_parser = DirectionParser()
        self.relation_parser = SpatialRelationParser()
        self.filter_parser = PropertyFilterParser()
        
        # Bangalore area knowledge base
        self.known_areas = self._load_known_areas()
    
    def _load_known_areas(self) -> Dict[str, Dict]:
        """Load known Bangalore areas with coordinates."""
        return {
            # Major areas
            'indiranagar': {'lat': 12.9784, 'lng': 77.6408, 'type': 'locality'},
            'koramangala': {'lat': 12.9352, 'lng': 77.6245, 'type': 'locality'},
            'whitefield': {'lat': 12.9698, 'lng': 77.7500, 'type': 'locality'},
            'hsr layout': {'lat': 12.9116, 'lng': 77.6389, 'type': 'locality'},
            'hsr': {'lat': 12.9116, 'lng': 77.6389, 'type': 'locality'},
            'btm layout': {'lat': 12.9166, 'lng': 77.6101, 'type': 'locality'},
            'btm': {'lat': 12.9166, 'lng': 77.6101, 'type': 'locality'},
            'jayanagar': {'lat': 12.9308, 'lng': 77.5838, 'type': 'locality'},
            'jp nagar': {'lat': 12.9063, 'lng': 77.5857, 'type': 'locality'},
            'marathahalli': {'lat': 12.9591, 'lng': 77.6974, 'type': 'locality'},
            'electronic city': {'lat': 12.8399, 'lng': 77.6770, 'type': 'it_hub'},
            'hebbal': {'lat': 13.0358, 'lng': 77.5970, 'type': 'locality'},
            'yelahanka': {'lat': 13.1007, 'lng': 77.5963, 'type': 'locality'},
            'banashankari': {'lat': 12.9255, 'lng': 77.5468, 'type': 'locality'},
            'rajajinagar': {'lat': 12.9900, 'lng': 77.5533, 'type': 'locality'},
            'malleswaram': {'lat': 13.0035, 'lng': 77.5647, 'type': 'locality'},
            'basavanagudi': {'lat': 12.9416, 'lng': 77.5757, 'type': 'locality'},
            'sarjapur': {'lat': 12.8600, 'lng': 77.7870, 'type': 'locality'},
            'sarjapur road': {'lat': 12.9100, 'lng': 77.6800, 'type': 'corridor'},
            'outer ring road': {'lat': 12.9300, 'lng': 77.6800, 'type': 'corridor'},
            'orr': {'lat': 12.9300, 'lng': 77.6800, 'type': 'corridor'},
            'mg road': {'lat': 12.9756, 'lng': 77.6066, 'type': 'landmark'},
            'brigade road': {'lat': 12.9716, 'lng': 77.6070, 'type': 'landmark'},
            'cubbon park': {'lat': 12.9763, 'lng': 77.5929, 'type': 'landmark'},
            'ub city': {'lat': 12.9716, 'lng': 77.5946, 'type': 'landmark'},
            'vidhana soudha': {'lat': 12.9795, 'lng': 77.5913, 'type': 'landmark'},
            'kempegowda bus station': {'lat': 12.9778, 'lng': 77.5716, 'type': 'transport'},
            'majestic': {'lat': 12.9778, 'lng': 77.5716, 'type': 'transport'},
            'bangalore airport': {'lat': 13.1979, 'lng': 77.7063, 'type': 'transport'},
            'kempegowda airport': {'lat': 13.1979, 'lng': 77.7063, 'type': 'transport'},
            'kia': {'lat': 13.1979, 'lng': 77.7063, 'type': 'transport'},
        }
    
    def parse(self, query: str, context: Dict[str, Any] = None) -> ParsedSpatialQuery:
        """
        Parse a natural language query into structured spatial query.
        
        Args:
            query: User's natural language query
            context: Optional context (current location, viewport, etc.)
            
        Returns:
            ParsedSpatialQuery with all extracted information
        """
        context = context or {}
        result = ParsedSpatialQuery(original_query=query, intent='search')
        
        # Step 1: Parse property filters
        result.property_filters = self.filter_parser.parse(query)
        result.reasoning.append(f"Extracted filters: {result.property_filters}")
        
        # Step 2: Extract spatial relations
        relations = self.relation_parser.parse(query)
        for relation, entity_names in relations:
            for name in entity_names:
                entity = self._resolve_entity(name)
                if entity:
                    constraint = SpatialConstraint(
                        relation=relation,
                        reference_entity=entity,
                    )
                    result.constraints.append(constraint)
                    result.entities.append(entity)
                    result.reasoning.append(f"Found relation: {relation.value} {name}")
        
        # Step 3: Parse distances
        distance_m, distance_text = self.distance_parser.parse(query)
        if distance_m and result.constraints:
            result.constraints[-1].distance_m = distance_m
            result.constraints[-1].distance_text = distance_text
            result.reasoning.append(f"Distance constraint: {distance_m}m ({distance_text})")
        
        # Step 4: Parse direction
        direction = self.direction_parser.parse(query)
        if direction and result.constraints:
            result.constraints[-1].direction = direction
            result.reasoning.append(f"Direction: {direction.value}")
        
        # Step 5: Detect intent
        result.intent = self._detect_intent(query)
        
        # Step 6: Calculate spatial scope
        result.spatial_scope = self._calculate_scope(result, context)
        
        # Step 7: Calculate confidence
        result.confidence = self._calculate_confidence(result)
        
        return result
    
    def _resolve_entity(self, name: str) -> Optional[SpatialEntity]:
        """Resolve entity name to coordinates."""
        name_lower = name.lower().strip()
        
        # Check known areas
        if name_lower in self.known_areas:
            area = self.known_areas[name_lower]
            return SpatialEntity(
                name=name,
                entity_type=area.get('type', 'location'),
                lat=area['lat'],
                lng=area['lng'],
                confidence=0.95,
            )
        
        # Try geocoder
        if self.geocoder:
            try:
                result = self.geocoder.geocode(name)
                if result:
                    return SpatialEntity(
                        name=name,
                        entity_type='location',
                        lat=result.get('lat'),
                        lng=result.get('lng'),
                        confidence=result.get('confidence', 0.7),
                    )
            except:
                pass
        
        # Fuzzy match known areas
        for known_name, area in self.known_areas.items():
            if name_lower in known_name or known_name in name_lower:
                return SpatialEntity(
                    name=name,
                    entity_type=area.get('type', 'location'),
                    lat=area['lat'],
                    lng=area['lng'],
                    confidence=0.7,
                )
        
        return None
    
    def _detect_intent(self, query: str) -> str:
        """Detect query intent."""
        q = query.lower()
        
        if any(w in q for w in ['compare', 'versus', 'vs', 'better', 'difference']):
            return 'compare'
        if any(w in q for w in ['what if', 'simulate', 'imagine', 'scenario']):
            return 'simulate'
        if any(w in q for w in ['price', 'cost', 'value', 'worth', 'estimate']):
            return 'valuation'
        if any(w in q for w in ['go to', 'show me', 'navigate', 'take me', 'fly to']):
            return 'navigate'
        if any(w in q for w in ['analyze', 'tell me about', 'what is']):
            return 'analyze'
        
        return 'search'
    
    def _calculate_scope(self, result: ParsedSpatialQuery, context: Dict) -> Optional[Dict]:
        """Calculate spatial scope for the query."""
        # If we have entities with coordinates, use them
        if result.entities:
            lats = [e.lat for e in result.entities if e.lat]
            lngs = [e.lng for e in result.entities if e.lng]
            
            if lats and lngs:
                center_lat = sum(lats) / len(lats)
                center_lng = sum(lngs) / len(lngs)
                
                # Determine radius from constraints
                radius = 1000  # Default 1km
                for constraint in result.constraints:
                    if constraint.distance_m:
                        radius = constraint.distance_m
                        break
                
                return {
                    'center_lat': center_lat,
                    'center_lng': center_lng,
                    'radius_m': radius,
                }
        
        # Fall back to context
        if context.get('lat') and context.get('lng'):
            return {
                'center_lat': context['lat'],
                'center_lng': context['lng'],
                'radius_m': context.get('radius_m', 1000),
            }
        
        return None
    
    def _calculate_confidence(self, result: ParsedSpatialQuery) -> float:
        """Calculate overall parsing confidence."""
        score = 0.5  # Base score
        
        # Boost for resolved entities
        if result.entities:
            score += 0.2 * min(len(result.entities), 2) / 2
        
        # Boost for spatial constraints
        if result.constraints:
            score += 0.15
        
        # Boost for property filters
        if result.property_filters:
            score += 0.1 * min(len(result.property_filters), 3) / 3
        
        # Boost for spatial scope
        if result.spatial_scope:
            score += 0.1
        
        return min(score, 1.0)
    
    def generate_search_params(self, parsed: ParsedSpatialQuery) -> Dict[str, Any]:
        """
        Convert parsed query to search parameters.
        Can be used directly with property search.
        """
        params = {}
        
        # Location parameters
        if parsed.spatial_scope:
            params['lat'] = parsed.spatial_scope['center_lat']
            params['lng'] = parsed.spatial_scope['center_lng']
            params['radius_m'] = parsed.spatial_scope['radius_m']
        
        # Property filters
        params.update(parsed.property_filters)
        
        # Direction adjustment
        for constraint in parsed.constraints:
            if constraint.direction and constraint.reference_entity:
                lat_offset, lng_offset = self.direction_parser.get_direction_offset(
                    constraint.direction,
                    constraint.distance_m or 500
                )
                if constraint.reference_entity.lat and constraint.reference_entity.lng:
                    params['lat'] = constraint.reference_entity.lat + lat_offset
                    params['lng'] = constraint.reference_entity.lng + lng_offset
        
        return params
    
    def explain_query(self, parsed: ParsedSpatialQuery) -> str:
        """Generate human-readable explanation of parsed query."""
        parts = []
        
        # Intent
        parts.append(f"**Intent:** {parsed.intent.title()}")
        
        # Entities
        if parsed.entities:
            entity_names = [e.name for e in parsed.entities]
            parts.append(f"**Locations:** {', '.join(entity_names)}")
        
        # Constraints
        for constraint in parsed.constraints:
            if constraint.reference_entity:
                desc = f"{constraint.relation.value} {constraint.reference_entity.name}"
                if constraint.direction:
                    desc = f"{constraint.direction.value} of {constraint.reference_entity.name}"
                if constraint.distance_m:
                    desc += f" (within {constraint.distance_m}m)"
                parts.append(f"**Constraint:** {desc}")
        
        # Filters
        if parsed.property_filters:
            filter_parts = []
            if 'budget_max' in parsed.property_filters:
                filter_parts.append(f"Budget: ≤₹{parsed.property_filters['budget_max']:.0f}L")
            if 'bhk' in parsed.property_filters:
                filter_parts.append(f"{parsed.property_filters['bhk']}BHK")
            if 'property_type' in parsed.property_filters:
                filter_parts.append(parsed.property_filters['property_type'].title())
            if filter_parts:
                parts.append(f"**Filters:** {', '.join(filter_parts)}")
        
        # Confidence
        parts.append(f"**Confidence:** {parsed.confidence:.0%}")
        
        return "\n".join(parts)


# Singleton instance
_spatial_nlp = None


def get_spatial_nlp(geocoder=None, db_service=None) -> SpatialNLP:
    """Get or create SpatialNLP singleton."""
    global _spatial_nlp
    if _spatial_nlp is None:
        _spatial_nlp = SpatialNLP(geocoder=geocoder, db_service=db_service)
    return _spatial_nlp
