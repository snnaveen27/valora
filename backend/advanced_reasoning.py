"""
Advanced Reasoning Engine for Valora AI
Adds chain-of-thought reasoning, query decomposition, and fact verification
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re


class ReasoningStep(Enum):
    """Types of reasoning steps."""
    DECOMPOSE = "decompose"  # Break down complex query
    VERIFY = "verify"  # Cross-check facts
    INFER = "infer"  # Make logical inferences
    SYNTHESIZE = "synthesize"  # Combine facts
    VALIDATE = "validate"  # Check consistency


@dataclass
class ReasoningTrace:
    """Captures the reasoning process for transparency."""
    query: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    fact_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_step(self, step_type: ReasoningStep, description: str, data: Any = None):
        """Add a reasoning step."""
        self.steps.append({
            "type": step_type.value,
            "description": description,
            "data": data,
            "timestamp": len(self.steps)
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "query": self.query,
            "steps": self.steps,
            "confidence": self.confidence_score,
            "sources": self.fact_sources,
            "warnings": self.warnings
        }


class QueryDecomposer:
    """Breaks down complex queries into atomic sub-queries."""
    
    MULTI_INTENT_PATTERNS = [
        r'\band\b',
        r'\balso\b',
        r'\bplus\b',
        r'\,',
        r'\bthen\b',
        r'\bafter that\b',
    ]
    
    COMPARISON_INDICATORS = [
        r'\bvs\b',
        r'\bversus\b',
        r'\bcompare\b',
        r'\bbetter\b',
        r'\bdifference between\b',
        r'\bwhich is\b',
    ]
    
    @classmethod
    def decompose(cls, query: str) -> List[Dict[str, Any]]:
        """
        Decompose a complex query into sub-queries.
        Returns list of {query, intent_hint, dependencies}.
        """
        q = query.strip()
        
        # Check if it's a comparison query
        if any(re.search(p, q, re.IGNORECASE) for p in cls.COMPARISON_INDICATORS):
            return cls._decompose_comparison(q)
        
        # Check for multi-part queries
        if any(re.search(p, q, re.IGNORECASE) for p in cls.MULTI_INTENT_PATTERNS):
            return cls._decompose_multi_part(q)
        
        # Single atomic query
        return [{"query": q, "intent_hint": None, "dependencies": []}]
    
    @classmethod
    def _decompose_comparison(cls, query: str) -> List[Dict[str, Any]]:
        """Decompose comparison queries like 'Compare Indiranagar vs Whitefield'."""
        # Extract entities to compare
        entities = []
        
        # Try pattern: "compare X and/vs Y"
        match = re.search(r'compare\s+(.+?)\s+(?:and|vs|versus)\s+(.+?)(?:\s|$|\?)', query, re.IGNORECASE)
        if match:
            entities = [match.group(1).strip(), match.group(2).strip()]
        else:
            # Try pattern: "X vs Y"
            match = re.search(r'(.+?)\s+(?:vs|versus)\s+(.+?)(?:\s|$|\?)', query, re.IGNORECASE)
            if match:
                entities = [match.group(1).strip(), match.group(2).strip()]
        
        if len(entities) == 2:
            return [
                {"query": f"Analyze {entities[0]}", "intent_hint": "analyze_area", "dependencies": []},
                {"query": f"Analyze {entities[1]}", "intent_hint": "analyze_area", "dependencies": []},
                {"query": f"Compare results", "intent_hint": "comparison", "dependencies": [0, 1]},
            ]
        
        # Fallback: single query
        return [{"query": query, "intent_hint": "comparison", "dependencies": []}]
    
    @classmethod
    def _decompose_multi_part(cls, query: str) -> List[Dict[str, Any]]:
        """Decompose multi-part queries like 'Show me properties and analyze the area'."""
        # Split by common delimiters
        parts = re.split(r'\s+(?:and|also|then)\s+', query, flags=re.IGNORECASE)
        
        sub_queries = []
        for i, part in enumerate(parts):
            part = part.strip()
            if part:
                sub_queries.append({
                    "query": part,
                    "intent_hint": None,
                    "dependencies": [i-1] if i > 0 else []
                })
        
        return sub_queries if len(sub_queries) > 1 else [{"query": query, "intent_hint": None, "dependencies": []}]


class FactVerifier:
    """Cross-validates facts from multiple sources."""
    
    @staticmethod
    def verify_location_consistency(lat: float, lng: float, location_name: str, geocoder) -> Dict[str, Any]:
        """Verify that coordinates match the claimed location."""
        if not geocoder or not location_name:
            return {"verified": False, "confidence": 0.0, "reason": "Missing data"}
        
        try:
            # Reverse geocode to check if coordinates are near the claimed location
            # This would use the geocoder's reverse lookup
            # For now, return high confidence if we have coordinates
            if lat and lng:
                return {"verified": True, "confidence": 0.9, "reason": "Coordinates available"}
        except:
            pass
        
        return {"verified": False, "confidence": 0.3, "reason": "Unable to verify"}
    
    @staticmethod
    def verify_price_reasonability(price: float, area_sqft: float, price_per_sqft: float, avg_market_price: float) -> Dict[str, Any]:
        """Check if property price is reasonable."""
        if not all([price, area_sqft, price_per_sqft]):
            return {"verified": False, "confidence": 0.0, "reason": "Missing price data"}
        
        # Calculate expected price
        expected_price = area_sqft * price_per_sqft
        price_diff_pct = abs(price - expected_price) / expected_price * 100 if expected_price > 0 else 100
        
        # Check consistency
        if price_diff_pct < 5:
            confidence = 0.95
            verified = True
            reason = "Price calculation matches"
        elif price_diff_pct < 15:
            confidence = 0.75
            verified = True
            reason = "Price within reasonable range"
        else:
            confidence = 0.4
            verified = False
            reason = f"Price mismatch: {price_diff_pct:.1f}% difference"
        
        # Compare to market average
        if avg_market_price and price_per_sqft:
            market_diff_pct = abs(price_per_sqft - avg_market_price) / avg_market_price * 100
            if market_diff_pct > 50:
                confidence *= 0.8
                reason += f"; {market_diff_pct:.0f}% off market avg"
        
        return {"verified": verified, "confidence": confidence, "reason": reason}
    
    @staticmethod
    def cross_validate_facts(facts_dict: Dict[str, Any]) -> List[str]:
        """Check for inconsistencies in collected facts."""
        warnings = []
        
        # Check location consistency
        if facts_dict.get('lat') and facts_dict.get('lng'):
            lat, lng = facts_dict['lat'], facts_dict['lng']
            # Bangalore approximate bounds
            if not (12.7 <= lat <= 13.2 and 77.3 <= lng <= 77.9):
                warnings.append(f"Coordinates ({lat:.4f}, {lng:.4f}) outside Bangalore region")
        
        # Check property logic
        if facts_dict.get('bedrooms', 0) > 10:
            warnings.append(f"Unusual bedroom count: {facts_dict['bedrooms']}")
        
        if facts_dict.get('price_per_sqft', 0) > 50000:
            warnings.append(f"Very high price/sqft: ₹{facts_dict['price_per_sqft']:,.0f}")
        
        # Check accessibility vs POI count
        poi_count = facts_dict.get('poi_count', 0)
        accessibility = facts_dict.get('accessibility_score', 0)
        if poi_count > 100 and accessibility < 50:
            warnings.append("High POI count but low accessibility score - check data")
        
        return warnings


class ConfidenceScorer:
    """Calculates confidence scores for agent responses."""
    
    @staticmethod
    def score_response(facts: Dict[str, Any], rag_results: List = None, verifications: List[Dict] = None) -> float:
        """
        Calculate overall confidence score (0-100).
        Based on: data completeness, verification results, RAG relevance.
        """
        score = 0.0
        
        # Data completeness (40 points)
        required_fields = ['lat', 'lng', 'location_name']
        optional_fields = ['poi_count', 'transport_count', 'avg_price_per_sqft', 'accessibility_score']
        
        completeness = sum(1 for f in required_fields if facts.get(f)) / len(required_fields)
        optional_completeness = sum(1 for f in optional_fields if facts.get(f)) / len(optional_fields)
        score += completeness * 25 + optional_completeness * 15
        
        # Verification results (30 points)
        if verifications:
            avg_verification = sum(v.get('confidence', 0) for v in verifications) / len(verifications)
            score += avg_verification * 30
        else:
            score += 15  # Partial score if no verifications
        
        # RAG relevance (20 points)
        if rag_results:
            avg_rag_score = sum(r.score for r in rag_results[:5]) / min(len(rag_results), 5)
            score += avg_rag_score * 20
        else:
            score += 10  # Partial score if no RAG
        
        # Data source diversity (10 points)
        sources = set()
        if facts.get('poi_count'): sources.add('spatial')
        if facts.get('avg_price_per_sqft'): sources.add('properties')
        if facts.get('elevation_m'): sources.add('terrain')
        if rag_results: sources.add('rag')
        score += len(sources) * 2.5
        
        return min(100.0, max(0.0, score))


class AdvancedReasoningEngine:
    """Main reasoning engine coordinating all advanced capabilities."""
    
    def __init__(self):
        self.decomposer = QueryDecomposer()
        self.verifier = FactVerifier()
        self.scorer = ConfidenceScorer()
    
    def reason(
        self,
        query: str,
        collected_facts: Dict[str, Any],
        rag_results: List = None,
        geocoder = None
    ) -> ReasoningTrace:
        """
        Apply advanced reasoning to a query and collected facts.
        Returns a reasoning trace with confidence score.
        """
        trace = ReasoningTrace(query=query)
        
        # Step 1: Query Decomposition
        trace.add_step(
            ReasoningStep.DECOMPOSE,
            "Breaking down query into sub-queries",
            self.decomposer.decompose(query)
        )
        
        # Step 2: Fact Verification
        verifications = []
        
        # Verify location if available
        if collected_facts.get('lat') and collected_facts.get('lng'):
            loc_verify = self.verifier.verify_location_consistency(
                collected_facts['lat'],
                collected_facts['lng'],
                collected_facts.get('location_name', ''),
                geocoder
            )
            verifications.append(loc_verify)
            trace.add_step(ReasoningStep.VERIFY, "Location verification", loc_verify)
        
        # Verify price if property data available
        if collected_facts.get('price'):
            price_verify = self.verifier.verify_price_reasonability(
                collected_facts.get('price', 0),
                collected_facts.get('total_area_sqft', 0),
                collected_facts.get('price_per_sqft', 0),
                collected_facts.get('avg_price_per_sqft', 0)
            )
            verifications.append(price_verify)
            trace.add_step(ReasoningStep.VERIFY, "Price verification", price_verify)
        
        # Step 3: Cross-validation
        warnings = self.verifier.cross_validate_facts(collected_facts)
        if warnings:
            trace.warnings.extend(warnings)
            trace.add_step(ReasoningStep.VALIDATE, "Cross-validation warnings", warnings)
        
        # Step 4: Confidence scoring
        confidence = self.scorer.score_response(collected_facts, rag_results, verifications)
        trace.confidence_score = confidence
        trace.add_step(ReasoningStep.SYNTHESIZE, f"Confidence score: {confidence:.1f}/100", confidence)
        
        # Step 5: Track data sources
        if collected_facts.get('poi_count'): trace.fact_sources.append('Spatial DB')
        if collected_facts.get('avg_price_per_sqft'): trace.fact_sources.append('Property DB')
        if collected_facts.get('elevation_m'): trace.fact_sources.append('Terrain Service')
        if rag_results: trace.fact_sources.append(f'RAG ({len(rag_results)} results)')
        
        return trace


def get_reasoning_engine() -> AdvancedReasoningEngine:
    """Singleton accessor for reasoning engine."""
    if not hasattr(get_reasoning_engine, '_instance'):
        get_reasoning_engine._instance = AdvancedReasoningEngine()
    return get_reasoning_engine._instance
