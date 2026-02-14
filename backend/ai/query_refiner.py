"""
Query Refiner - Production-grade query understanding and enhancement.

Features:
1. Missing slot detection (location, budget, property type, etc.)
2. Query complexity classification
3. Context enrichment from user session
4. Result deduplication and ranking
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"       # Single intent, no decomposition needed
    MODERATE = "moderate"   # 2-3 intents, light decomposition
    COMPLEX = "complex"     # 4+ intents or requires deep analysis


class MissingSlot(Enum):
    """Slots that may be missing from a query."""
    LOCATION = "location"
    BUDGET = "budget"
    PROPERTY_TYPE = "property_type"
    BEDROOMS = "bedrooms"
    TIME_HORIZON = "time_horizon"  # For investment queries
    COMPARISON_TARGET = "comparison_target"  # For comparison queries


@dataclass
class SlotStatus:
    """Status of a required slot."""
    slot: MissingSlot
    is_present: bool
    value: Optional[Any] = None
    suggested_default: Optional[Any] = None
    clarification_question: Optional[str] = None


@dataclass
class RefinedQuery:
    """Result of query refinement."""
    original_query: str
    complexity: QueryComplexity
    slots: List[SlotStatus] = field(default_factory=list)
    missing_critical: List[MissingSlot] = field(default_factory=list)
    suggested_clarifications: List[str] = field(default_factory=list)
    enriched_context: Dict[str, Any] = field(default_factory=dict)
    should_use_swarm: bool = False
    confidence: float = 1.0


class QueryRefiner:
    """
    Refines and enhances user queries for better understanding.
    
    Detects missing information, suggests clarifications,
    and determines if swarm decomposition is needed.
    """
    
    # Patterns for slot detection
    LOCATION_PATTERNS = [
        r'\b(koramangala|indiranagar|whitefield|jayanagar|hsr layout|'
        r'electronic city|marathahalli|sarjapur|bellandur|hebbal|'
        r'yelahanka|jp nagar|btm layout|bannerghatta|mg road|'
        r'brigade road|commercial street|ub city|bangalore|bengaluru|'
        r'rajajinagar|malleswaram|basavanagudi|vijayanagar|'
        r'banashankari|jayanagar|wilson garden|richmond town|'
        r'cunningham road|ulsoor|domlur|kormangala|hrbr layout|'
        r'rt nagar|hennur|kalyan nagar|ramamurthy nagar|'
        r'kr puram|mahadevpura|varthur|kadugodi|hoodi|'
        r'brookefield|kundalahalli|thubarahalli|hagadur|'
        r'bommanahalli|arekere|begur|hulimavu|'
        r'jp nagar|uttarahalli|kanakapura road|'
        r'bannerghatta road|electronic city|hosur road)\b',
    ]
    
    BUDGET_PATTERNS = [
        r'(\d+(?:\.\d+)?)\s*(lakh|lakhs|lac|lacs|cr|crore|crores|k|thousand)',
        r'under\s+(\d+)',
        r'budget\s+(?:of\s+)?(\d+)',
        r'(?:less than|below|max|maximum)\s+(\d+)',
    ]
    
    PROPERTY_TYPE_PATTERNS = [
        r'\b(apartment|flat|villa|house|plot|land|office|commercial|'
        r'penthouse|studio|duplex|triplex|row house|independent house|'
        r'pg|hostel|shop|showroom|warehouse|factory|farmhouse)\b',
    ]
    
    BHK_PATTERNS = [
        r'(\d+)\s*bhk',
        r'(\d+)\s*bedroom',
        r'(\d+)\s*bed\b',
    ]
    
    # Complexity indicators
    COMPLEX_INDICATORS = [
        r'\band\b.*\band\b',  # Multiple "and"s
        r'\bcompare\b.*\bvs\b',
        r'\bwhat if\b',
        r'\bsimulate\b',
        r'\binvestment\b.*\brisk\b',
        r'\bmarket\b.*\btrend\b.*\bfuture\b',
    ]
    
    MODERATE_INDICATORS = [
        r'\band\b',
        r'\bwith\b',
        r'\bnear\b.*\b(school|hospital|metro)\b',
        r'\bgood for\b',
    ]
    
    def __init__(self):
        self.default_location = "Bangalore"
        self.default_budget_lakhs = 100  # 1 crore
    
    def refine(self, query: str, context: Dict[str, Any] = None) -> RefinedQuery:
        """
        Refine a user query to detect missing info and determine complexity.
        
        Args:
            query: User's natural language query
            context: Optional context (selected location, user preferences, etc.)
        
        Returns:
            RefinedQuery with slot analysis and recommendations
        """
        context = context or {}
        query_lower = query.lower()
        
        # Detect complexity
        complexity = self._classify_complexity(query_lower)
        
        # Analyze slots
        slots = self._analyze_slots(query_lower, context)
        
        # Find missing critical slots
        missing_critical = [
            s.slot for s in slots 
            if not s.is_present and s.slot in self._get_critical_slots(query_lower)
        ]
        
        # Generate clarification suggestions
        clarifications = self._generate_clarifications(slots, missing_critical)
        
        # Enrich context from detected values
        enriched = self._enrich_context(slots, context)
        
        # Determine if swarm should be used
        should_use_swarm = (
            complexity in (QueryComplexity.MODERATE, QueryComplexity.COMPLEX)
            or len(missing_critical) == 0  # Only use swarm if we have enough info
        )
        
        # Calculate confidence based on slot coverage
        filled_slots = sum(1 for s in slots if s.is_present)
        confidence = filled_slots / max(len(slots), 1)
        
        return RefinedQuery(
            original_query=query,
            complexity=complexity,
            slots=slots,
            missing_critical=missing_critical,
            suggested_clarifications=clarifications,
            enriched_context=enriched,
            should_use_swarm=should_use_swarm,
            confidence=confidence
        )
    
    def _classify_complexity(self, query: str) -> QueryComplexity:
        """Classify query complexity."""
        # Check for complex patterns
        for pattern in self.COMPLEX_INDICATORS:
            if re.search(pattern, query, re.IGNORECASE):
                return QueryComplexity.COMPLEX
        
        # Check for moderate patterns
        moderate_count = 0
        for pattern in self.MODERATE_INDICATORS:
            if re.search(pattern, query, re.IGNORECASE):
                moderate_count += 1
        
        if moderate_count >= 2:
            return QueryComplexity.COMPLEX
        elif moderate_count >= 1:
            return QueryComplexity.MODERATE
        
        return QueryComplexity.SIMPLE
    
    def _analyze_slots(self, query_lower: str, context: Dict[str, Any] = None) -> List[SlotStatus]:
        """Analyze which slots are filled vs missing."""
        if context is None:
            context = {}
            
        slots = []
        
        # Location
        location = self._extract_location(query_lower, context)
        slots.append(SlotStatus(
            slot=MissingSlot.LOCATION,
            is_present=location is not None,
            value=location,
            suggested_default=(context.get('selectedLocation') or {}).get('name') or self.default_location,
            clarification_question="Which area in Bangalore are you interested in?"
        ))
        
        # Budget
        budget = self._extract_budget(query_lower)
        slots.append(SlotStatus(
            slot=MissingSlot.BUDGET,
            is_present=budget is not None,
            value=budget,
            suggested_default=self.default_budget_lakhs,
            clarification_question="What's your budget range? (e.g., 50 lakhs to 1 crore)"
        ))
        
        # Property type
        prop_type = self._extract_property_type(query_lower)
        slots.append(SlotStatus(
            slot=MissingSlot.PROPERTY_TYPE,
            is_present=prop_type is not None,
            value=prop_type,
            suggested_default="apartment",
            clarification_question="Are you looking for an apartment, villa, or plot?"
        ))
        
        # Bedrooms
        bedrooms = self._extract_bedrooms(query_lower)
        slots.append(SlotStatus(
            slot=MissingSlot.BEDROOMS,
            is_present=bedrooms is not None,
            value=bedrooms,
            suggested_default=2,
            clarification_question="How many bedrooms do you need?"
        ))
        
        return slots
    
    def _extract_location(self, query: str, context: Dict) -> Optional[str]:
        """Extract location from query or context."""
        if context is None:
            context = {}
            
        for pattern in self.LOCATION_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).title()
        
        # Check context
        if context.get('selectedLocation'):
            return (context['selectedLocation'] or {}).get('name')
        if context.get('selectedPlace'):
            return (context['selectedPlace'] or {}).get('name')
        
        return None
    
    def _extract_budget(self, query: str) -> Optional[float]:
        """Extract budget in lakhs from query."""
        for pattern in self.BUDGET_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                value = float(match.group(1).replace(',', ''))
                # Convert to lakhs
                if len(match.groups()) > 1:
                    unit = match.group(2).lower() if match.group(2) else ''
                    if unit in ('cr', 'crore', 'crores'):
                        value *= 100
                    elif unit in ('k', 'thousand'):
                        value /= 100
                return value
        return None
    
    def _extract_property_type(self, query: str) -> Optional[str]:
        """Extract property type from query."""
        for pattern in self.PROPERTY_TYPE_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        return None
    
    def _extract_bedrooms(self, query: str) -> Optional[int]:
        """Extract bedroom count from query."""
        for pattern in self.BHK_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None
    
    def _get_critical_slots(self, query: str) -> Set[MissingSlot]:
        """Determine which slots are critical based on query type."""
        critical = set()
        
        # Property search requires location
        if re.search(r'\b(find|search|looking|show|list)\b.*\b(property|flat|apartment|house)\b', query):
            critical.add(MissingSlot.LOCATION)
        
        # Investment queries benefit from location
        if re.search(r'\b(invest|investment|roi|appreciation)\b', query):
            critical.add(MissingSlot.LOCATION)
        
        # Comparison queries need targets
        if re.search(r'\b(compare|vs|versus)\b', query):
            critical.add(MissingSlot.COMPARISON_TARGET)
        
        return critical
    
    def _generate_clarifications(
        self, 
        slots: List[SlotStatus], 
        missing_critical: List[MissingSlot]
    ) -> List[str]:
        """Generate clarification questions for missing slots."""
        clarifications = []
        
        for slot_status in slots:
            if slot_status.slot in missing_critical and slot_status.clarification_question:
                clarifications.append(slot_status.clarification_question)
        
        return clarifications[:3]  # Max 3 questions
    
    def _enrich_context(self, slots: List[SlotStatus], context: Dict) -> Dict[str, Any]:
        """Enrich context with detected slot values."""
        if context is None:
            context = {}
        enriched = dict(context)
        
        for slot_status in slots:
            if slot_status.is_present and slot_status.value:
                if slot_status.slot == MissingSlot.LOCATION:
                    enriched['detected_location'] = slot_status.value
                elif slot_status.slot == MissingSlot.BUDGET:
                    enriched['detected_budget_lakhs'] = slot_status.value
                elif slot_status.slot == MissingSlot.PROPERTY_TYPE:
                    enriched['detected_property_type'] = slot_status.value
                elif slot_status.slot == MissingSlot.BEDROOMS:
                    enriched['detected_bedrooms'] = slot_status.value
        
        return enriched


class ResultMerger:
    """
    Merges and ranks results from parallel swarm execution.
    
    Handles deduplication, importance ranking, and fact capping.
    """
    
    # Importance weights for different fact types
    FACT_WEIGHTS = {
        'user_constraint': 100,  # Direct answer to user's constraints
        'property': 90,
        'price': 85,
        'location': 80,
        'infrastructure': 70,
        'market_trend': 60,
        'risk': 55,
        'rag': 40,
        'general': 20,
    }
    
    # Caps for different result types
    RESULT_CAPS = {
        'facts': 15,
        'properties': 10,
        'pois': 20,
        'trends': 5,
        'risks': 5,
    }
    
    def __init__(self):
        self.seen_facts: Set[str] = set()
    
    def merge_facts(self, fact_lists: List[List[str]]) -> List[str]:
        """
        Merge and deduplicate facts from multiple sources.
        
        Args:
            fact_lists: List of fact lists from different agents
        
        Returns:
            Deduplicated, ranked, and capped facts
        """
        self.seen_facts.clear()
        scored_facts = []
        
        for facts in fact_lists:
            for fact in facts:
                normalized = self._normalize_fact(fact)
                if normalized not in self.seen_facts:
                    self.seen_facts.add(normalized)
                    score = self._score_fact(fact)
                    scored_facts.append((fact, score))
        
        # Sort by score (descending)
        scored_facts.sort(key=lambda x: -x[1])
        
        # Cap and return
        return [f[0] for f in scored_facts[:self.RESULT_CAPS['facts']]]
    
    def merge_properties(self, property_lists: List[List[Dict]]) -> List[Dict]:
        """Merge and deduplicate properties."""
        seen_ids = set()
        merged = []
        
        for props in property_lists:
            for prop in props:
                prop_id = prop.get('property_id') or prop.get('id')
                if prop_id and prop_id not in seen_ids:
                    seen_ids.add(prop_id)
                    merged.append(prop)
        
        # Sort by relevance score if available, else by price
        merged.sort(key=lambda p: (-p.get('relevance_score', 0), p.get('price', 0)))
        
        return merged[:self.RESULT_CAPS['properties']]
    
    def merge_dashboard(self, dashboards: List[Dict]) -> Dict:
        """Merge multiple dashboard objects."""
        merged = {
            "summary": {},
            "metrics": {},
            "locations": [],
            "properties": [],
            "trends": {},
            "risks": [],
            "infrastructure": {},
        }
        
        for dash in dashboards:
            if not dash:
                continue
            
            # Merge summaries
            if dash.get('summary'):
                merged['summary'].update(dash['summary'])
            
            # Merge metrics
            if dash.get('metrics'):
                merged['metrics'].update(dash['metrics'])
            
            # Merge locations (dedupe)
            for loc in dash.get('locations', []):
                if loc not in merged['locations']:
                    merged['locations'].append(loc)
            
            # Merge properties
            merged['properties'].extend(dash.get('properties', []))
            
            # Merge trends
            if dash.get('trends'):
                merged['trends'].update(dash['trends'])
            
            # Merge risks
            merged['risks'].extend(dash.get('risks', []))
            
            # Merge infrastructure
            if dash.get('infrastructure'):
                merged['infrastructure'].update(dash['infrastructure'])
        
        # Apply caps
        merged['properties'] = merged['properties'][:self.RESULT_CAPS['properties']]
        merged['risks'] = merged['risks'][:self.RESULT_CAPS['risks']]
        merged['locations'] = merged['locations'][:10]
        
        return merged
    
    def _normalize_fact(self, fact: str) -> str:
        """Normalize a fact for deduplication."""
        # Lowercase, remove extra spaces, remove punctuation
        normalized = fact.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized
    
    def _score_fact(self, fact: str) -> int:
        """Score a fact based on importance."""
        fact_lower = fact.lower()
        
        # Check for fact type indicators
        if any(kw in fact_lower for kw in ['found', 'matching', 'properties']):
            return self.FACT_WEIGHTS['property']
        if any(kw in fact_lower for kw in ['price', '₹', 'lakh', 'crore', 'sqft']):
            return self.FACT_WEIGHTS['price']
        if any(kw in fact_lower for kw in ['koramangala', 'whitefield', 'indiranagar', 'area', 'locality']):
            return self.FACT_WEIGHTS['location']
        if any(kw in fact_lower for kw in ['school', 'hospital', 'metro', 'mall', 'park']):
            return self.FACT_WEIGHTS['infrastructure']
        if any(kw in fact_lower for kw in ['trend', 'growth', 'appreciation', 'demand']):
            return self.FACT_WEIGHTS['market_trend']
        if any(kw in fact_lower for kw in ['risk', 'flood', 'legal', 'safety']):
            return self.FACT_WEIGHTS['risk']
        if any(kw in fact_lower for kw in ['rag', 'semantic']):
            return self.FACT_WEIGHTS['rag']
        
        return self.FACT_WEIGHTS['general']


# Singleton instances
_query_refiner: Optional[QueryRefiner] = None
_result_merger: Optional[ResultMerger] = None


def get_query_refiner() -> QueryRefiner:
    """Get or create the query refiner singleton."""
    global _query_refiner
    if _query_refiner is None:
        _query_refiner = QueryRefiner()
    return _query_refiner


def get_result_merger() -> ResultMerger:
    """Get or create the result merger singleton."""
    global _result_merger
    if _result_merger is None:
        _result_merger = ResultMerger()
    return _result_merger
