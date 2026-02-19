"""
Valora AI - Production Query Pipeline

Enhanced query handling with:
1. Parallel fact gathering
2. Semantic caching
3. Cancellation tokens
4. Connection pooling
5. Request tracing
6. Intent confidence scoring
"""

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Awaitable, Tuple
from enum import Enum
import logging
import aiohttp

logger = logging.getLogger("valora.query_pipeline")


# =============================================================================
# 1. INTENT CONFIDENCE SCORING
# =============================================================================

@dataclass
class IntentResult:
    """Result of intent classification with confidence."""
    primary: 'Intent'
    confidence: float  # 0.0 - 1.0
    secondary: Optional['Intent'] = None
    slots: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    
    def needs_clarification(self) -> bool:
        """Check if confidence is too low and clarification needed."""
        return self.confidence < 0.6


class IntentClassifierWithConfidence:
    """
    Enhanced intent classifier with confidence scoring.
    
    Uses multiple signals:
    - Pattern matching strength
    - Keyword density
    - Entity presence
    - Context alignment
    """
    
    def __init__(self):
        from ai.gis_agents import Intent, IntentRouter
        self.Intent = Intent
        self.IntentRouter = IntentRouter
    
    def classify_with_confidence(
        self, 
        query: str, 
        context: Dict[str, Any]
    ) -> IntentResult:
        """Classify intent with confidence score."""
        q = query.lower().strip()
        scores: Dict[Any, float] = {}
        slots = {}
        reasoning_parts = []
        
        # Get pattern-based classification
        has_building = bool(context.get('selectedBuilding'))
        has_location = bool(context.get('selectedLocation') or context.get('selectedPlace'))
        
        pattern_intent = self.IntentRouter.classify(query, has_building, has_location)
        
        # Score based on pattern match strength
        # Strong patterns get higher confidence
        strong_patterns = {
            self.Intent.GREETING: self.IntentRouter.GREETING_PATTERNS,
            self.Intent.NAVIGATE: self.IntentRouter.NAVIGATE_PATTERNS,
            self.Intent.SIMULATE: self.IntentRouter.SIMULATE_PATTERNS,
            self.Intent.COMPARISON: self.IntentRouter.COMPARISON_PATTERNS,
        }
        
        # Check for strong pattern match
        for intent, patterns in strong_patterns.items():
            import re
            for pattern in patterns:
                match = re.search(pattern, q, re.IGNORECASE)
                if match:
                    # Full sentence match = high confidence
                    if match.group(0) == q:
                        scores[intent] = 0.95
                        reasoning_parts.append(f"exact pattern match for {intent.value}")
                    else:
                        scores[intent] = 0.8
                        reasoning_parts.append(f"partial pattern match for {intent.value}")
                    break
        
        # Score based on keyword density
        keyword_scores = self._score_by_keywords(q)
        for intent, score in keyword_scores.items():
            if intent not in scores:
                scores[intent] = score
            else:
                scores[intent] = max(scores[intent], score)
        
        # Context boost
        if has_building:
            if self.Intent.ANALYZE_BUILDING not in scores:
                scores[self.Intent.ANALYZE_BUILDING] = 0.7
            else:
                scores[self.Intent.ANALYZE_BUILDING] = min(1.0, scores[self.Intent.ANALYZE_BUILDING] + 0.15)
            reasoning_parts.append("building selected in context")
        
        if has_location:
            if self.Intent.ANALYZE_AREA not in scores:
                scores[self.Intent.ANALYZE_AREA] = 0.6
            reasoning_parts.append("location selected in context")
        
        # Extract slots (entities)
        slots['location'] = self.IntentRouter.extract_place_name(query)
        if context.get('selectedBuilding'):
            slots['building'] = context['selectedBuilding']
        
        # Determine primary and secondary intents
        if not scores:
            # Fallback to pattern classifier
            return IntentResult(
                primary=pattern_intent,
                confidence=0.5,
                slots=slots,
                reasoning="fallback to pattern classifier"
            )
        
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_intent, primary_score = sorted_intents[0]
        
        secondary = None
        if len(sorted_intents) > 1 and sorted_intents[1][1] > 0.5:
            secondary = sorted_intents[1][0]
        
        return IntentResult(
            primary=primary_intent,
            confidence=primary_score,
            secondary=secondary,
            slots=slots,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "keyword scoring"
        )
    
    def _score_by_keywords(self, query: str) -> Dict[Any, float]:
        """Score intent based on keyword presence and density."""
        scores = {}
        words = set(query.split())
        
        # Investment keywords
        investment_words = {'invest', 'roi', 'return', 'appreciation', 'growth', 'profit'}
        if investment_words & words:
            scores[self.Intent.INVESTMENT] = min(0.9, 0.5 + 0.1 * len(investment_words & words))
        
        # Property keywords
        property_words = {'apartment', 'flat', 'house', 'plot', 'property', 'bhk', 'bedroom'}
        if property_words & words:
            scores[self.Intent.PROPERTY_SEARCH] = min(0.85, 0.5 + 0.1 * len(property_words & words))
        
        # Area keywords
        area_words = {'area', 'locality', 'neighborhood', 'analyse', 'analyze', 'about'}
        if area_words & words:
            scores[self.Intent.ANALYZE_AREA] = min(0.8, 0.4 + 0.1 * len(area_words & words))
        
        # Terrain keywords
        terrain_words = {'elevation', 'flood', 'terrain', 'slope', 'topography'}
        if terrain_words & words:
            scores[self.Intent.TERRAIN] = min(0.85, 0.5 + 0.1 * len(terrain_words & words))
        
        return scores


# =============================================================================
# 2. REQUEST TRACING
# =============================================================================

@dataclass
class RequestTrace:
    """Trace of a request through the pipeline."""
    request_id: str
    user_id: str
    query: str
    intent: str = ""
    model: str = ""
    stages: Dict[str, int] = field(default_factory=dict)  # stage_name -> duration_ms
    cache_hit: bool = False
    credits_used: int = 0
    total_latency_ms: int = 0
    success: bool = True
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    def start_stage(self, stage: str) -> float:
        """Start timing a stage, return start time."""
        return time.time()
    
    def end_stage(self, stage: str, start_time: float):
        """End timing a stage."""
        self.stages[stage] = int((time.time() - start_time) * 1000)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "query": self.query[:100],
            "intent": self.intent,
            "model": self.model,
            "stages": self.stages,
            "cache_hit": self.cache_hit,
            "credits_used": self.credits_used,
            "total_latency_ms": self.total_latency_ms,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class TraceContext:
    """Context manager for request tracing."""
    
    _current_trace: Optional[RequestTrace] = None
    
    @classmethod
    def start_trace(cls, user_id: str, query: str) -> RequestTrace:
        """Start a new trace."""
        trace = RequestTrace(
            request_id=str(uuid.uuid4())[:12],
            user_id=user_id,
            query=query,
        )
        cls._current_trace = trace
        return trace
    
    @classmethod
    def get_current(cls) -> Optional[RequestTrace]:
        return cls._current_trace
    
    @classmethod
    def end_trace(cls, success: bool = True, error: str = None) -> Optional[RequestTrace]:
        """End the current trace."""
        trace = cls._current_trace
        if trace:
            trace.total_latency_ms = int((time.time() - trace.timestamp) * 1000)
            trace.success = success
            trace.error = error
            cls._current_trace = None
        return trace


def trace_stage(stage_name: str):
    """Decorator to trace a pipeline stage."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            trace = TraceContext.get_current()
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                if trace:
                    trace.end_stage(stage_name, start)
                return result
            except Exception as e:
                if trace:
                    trace.end_stage(stage_name, start)
                raise
        return wrapper
    return decorator


# =============================================================================
# 3. CANCELLATION TOKEN
# =============================================================================

class CancellationToken:
    """Token for cancelling async operations."""
    
    def __init__(self):
        self._cancelled = False
        self._callbacks: List[Callable[[], None]] = []
    
    def cancel(self):
        """Cancel the token and trigger callbacks."""
        self._cancelled = True
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                logger.warning(f"Cancellation callback error: {e}")
    
    @property
    def is_cancelled(self) -> bool:
        return self._cancelled
    
    def throw_if_cancelled(self):
        """Raise CancelledError if cancelled."""
        if self._cancelled:
            raise asyncio.CancelledError("Operation was cancelled")
    
    def add_callback(self, callback: Callable[[], None]):
        """Add a callback to be called on cancellation."""
        self._callbacks.append(callback)


class CancellableOperation:
    """Base class for cancellable operations."""
    
    def __init__(self, token: Optional[CancellationToken] = None):
        self.token = token or CancellationToken()
    
    async def check_cancelled(self):
        """Check if operation should be cancelled."""
        if self.token and self.token.is_cancelled:
            raise asyncio.CancelledError("Operation cancelled by token")


# =============================================================================
# 4. CONNECTION POOL
# =============================================================================

class ConnectionPool:
    """
    Shared connection pool for HTTP sessions.
    
    Features:
    - Connection reuse
    - Keep-alive
    - Configurable limits
    - Graceful cleanup
    """
    
    _instance: Optional['ConnectionPool'] = None
    _session: Optional[aiohttp.ClientSession] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        """Get or create the shared session."""
        async with cls._lock:
            if cls._session is None or cls._session.closed:
                connector = aiohttp.TCPConnector(
                    limit=100,  # Total connection limit
                    limit_per_host=20,  # Per-host limit
                    keepalive_timeout=30,
                    enable_cleanup_closed=True,
                )
                timeout = aiohttp.ClientTimeout(total=180, connect=10)
                cls._session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                )
                logger.info("[ConnectionPool] Created new shared session")
            return cls._session
    
    @classmethod
    async def close(cls):
        """Close the shared session."""
        async with cls._lock:
            if cls._session and not cls._session.closed:
                await cls._session.close()
                cls._session = None
                logger.info("[ConnectionPool] Closed shared session")


async def get_http_session() -> aiohttp.ClientSession:
    """Get the shared HTTP session."""
    return await ConnectionPool.get_session()


# =============================================================================
# 5. SEMANTIC CACHE
# =============================================================================

@dataclass
class SemanticCacheEntry:
    """Entry in the semantic cache."""
    query: str
    embedding: List[float]
    response: Dict[str, Any]
    intent: str
    timestamp: float
    hit_count: int = 0


class SemanticCache:
    """
    Semantic similarity-based cache.
    
    Instead of exact key matching, uses embedding similarity
    to find cached responses for semantically similar queries.
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.92,
        max_entries: int = 500,
        ttl_seconds: float = 600.0,
    ):
        self.similarity_threshold = similarity_threshold
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._entries: List[SemanticCacheEntry] = []
        self._embedding_model = None
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text."""
        if self._embedding_model is None:
            # Use a simple hash-based embedding for now
            # In production, use sentence-transformers or similar
            import hashlib
            h = hashlib.sha256(text.lower().encode()).hexdigest()
            # Convert to pseudo-embedding (128 dims)
            return [float(int(h[i:i+2], 16)) / 255.0 for i in range(0, 256, 2)]
        return await self._embedding_model.embed(text)
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    
    async def get(
        self, 
        query: str, 
        intent: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached response for semantically similar query."""
        query_embedding = await self._get_embedding(query)
        
        best_match = None
        best_similarity = 0.0
        
        for entry in self._entries:
            # Check TTL
            if time.time() - entry.timestamp > self.ttl_seconds:
                continue
            
            # Check intent match if specified
            if intent and entry.intent != intent:
                continue
            
            similarity = self._cosine_similarity(query_embedding, entry.embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = entry
        
        if best_match and best_similarity >= self.similarity_threshold:
            best_match.hit_count += 1
            logger.info(
                f"[SemanticCache] HIT for '{query[:50]}' "
                f"(similarity={best_similarity:.3f}, cached_query='{best_match.query[:50]}')"
            )
            return {**best_match.response, "cached": True, "cache_similarity": best_similarity}
        
        return None
    
    async def set(
        self, 
        query: str, 
        response: Dict[str, Any], 
        intent: str = None
    ):
        """Cache a response."""
        embedding = await self._get_embedding(query)
        
        entry = SemanticCacheEntry(
            query=query,
            embedding=embedding,
            response=response,
            intent=intent or "general",
            timestamp=time.time(),
        )
        
        self._entries.append(entry)
        
        # Prune old entries
        if len(self._entries) > self.max_entries:
            # Remove oldest and lowest hit count entries
            self._entries.sort(key=lambda e: (e.timestamp, -e.hit_count))
            self._entries = self._entries[-self.max_entries:]
    
    def clear(self):
        """Clear the cache."""
        self._entries.clear()


# Global semantic cache instance
_semantic_cache: Optional[SemanticCache] = None


def get_semantic_cache() -> SemanticCache:
    """Get the global semantic cache."""
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCache()
    return _semantic_cache


# =============================================================================
# 6. PARALLEL FACT GATHERING
# =============================================================================

@dataclass
class FactGatheringTask:
    """A single fact-gathering task."""
    name: str
    agent_name: str
    func: Callable[[float, float, Dict], Awaitable[Dict[str, Any]]]
    dependencies: List[str] = field(default_factory=list)
    timeout: float = 10.0


class ParallelFactGatherer:
    """
    Gathers facts from multiple agents in parallel.
    
    Features:
    - Concurrent execution of independent agents
    - Dependency-aware scheduling
    - Timeout handling
    - Cancellation support
    """
    
    def __init__(
        self,
        max_concurrent: int = 4,
        default_timeout: float = 10.0,
    ):
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def gather(
        self,
        lat: float,
        lng: float,
        context: Dict[str, Any],
        tasks: List[FactGatheringTask],
        token: Optional[CancellationToken] = None,
    ) -> Dict[str, Any]:
        """
        Execute fact gathering tasks in parallel.
        
        Returns merged facts from all tasks.
        """
        results = {}
        errors = {}
        
        async def run_task(task: FactGatheringTask) -> Tuple[str, Dict[str, Any], Optional[str]]:
            """Run a single task with timeout and cancellation."""
            if token:
                token.throw_if_cancelled()
            
            async with self._semaphore:
                try:
                    result = await asyncio.wait_for(
                        task.func(lat, lng, context),
                        timeout=task.timeout
                    )
                    return task.name, result, None
                except asyncio.TimeoutError:
                    return task.name, {}, f"timeout after {task.timeout}s"
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    return task.name, {}, str(e)
        
        # Build dependency graph
        completed = set()
        pending = list(tasks)
        
        while pending:
            # Find tasks with satisfied dependencies
            ready = [
                t for t in pending 
                if all(d in completed for d in t.dependencies)
            ]
            
            if not ready:
                # Circular dependency or all remaining tasks have unmet deps
                logger.warning(f"[ParallelFactGatherer] {len(pending)} tasks with unmet dependencies")
                break
            
            # Run ready tasks concurrently
            coros = [run_task(task) for task in ready]
            
            try:
                task_results = await asyncio.gather(*coros, return_exceptions=True)
                
                for i, result in enumerate(task_results):
                    task = ready[i]
                    if isinstance(result, Exception):
                        errors[task.name] = str(result)
                    else:
                        name, data, error = result
                        if error:
                            errors[name] = error
                        else:
                            results[name] = data
                    completed.add(task.name)
                
            except asyncio.CancelledError:
                logger.info("[ParallelFactGatherer] Cancelled by token")
                raise
            
            # Remove completed from pending
            pending = [t for t in pending if t.name not in completed]
        
        # Merge results
        merged = {}
        for task_name, data in results.items():
            merged.update(data)
        
        if errors:
            merged['_errors'] = errors
            logger.warning(f"[ParallelFactGatherer] Errors: {errors}")
        
        return merged


# =============================================================================
# 7. PRODUCTION PIPELINE
# =============================================================================

class ProductionQueryPipeline:
    """
    Production-ready query processing pipeline.
    
    Combines all enhancements:
    - Intent classification with confidence
    - Semantic caching
    - Parallel fact gathering
    - Request tracing
    - Cancellation support
    - Connection pooling
    """
    
    def __init__(self):
        self.intent_classifier = IntentClassifierWithConfidence()
        self.semantic_cache = get_semantic_cache()
        self.fact_gatherer = ParallelFactGatherer()
    
    async def process(
        self,
        query: str,
        context: Dict[str, Any],
        user_id: str = "anonymous",
        token: Optional[CancellationToken] = None,
    ) -> Dict[str, Any]:
        """
        Process a query through the enhanced pipeline.
        
        Returns response dict with trace info.
        """
        # Start trace
        trace = TraceContext.start_trace(user_id, query)
        
        try:
            # 1. Check semantic cache
            cache_start = time.time()
            cached = await self.semantic_cache.get(query)
            if cached:
                trace.cache_hit = True
                trace.end_stage("cache_check", cache_start)
                TraceContext.end_trace(success=True)
                return {**cached, "trace": trace.to_dict()}
            trace.end_stage("cache_check", cache_start)
            
            if token:
                token.throw_if_cancelled()
            
            # 2. Classify intent with confidence
            intent_start = time.time()
            intent_result = self.intent_classifier.classify_with_confidence(query, context)
            trace.intent = intent_result.primary.value
            trace.end_stage("intent_classification", intent_start)
            
            if token:
                token.throw_if_cancelled()
            
            # 3. Gather facts in parallel (if location available)
            facts_start = time.time()
            lat = context.get('selectedLocation', {}).get('lat')
            lng = context.get('selectedLocation', {}).get('lng')
            
            facts = {}
            if lat and lng:
                facts = await self._gather_facts_parallel(lat, lng, context, token)
            trace.end_stage("fact_gathering", facts_start)
            
            if token:
                token.throw_if_cancelled()
            
            # 4. Build response (LLM call would happen here)
            # For now, return facts directly
            response = {
                "success": True,
                "intent": intent_result.primary.value,
                "intent_confidence": intent_result.confidence,
                "needs_clarification": intent_result.needs_clarification(),
                "facts": facts,
                "message": f"Processed query with intent: {intent_result.primary.value}",
            }
            
            # 5. Cache response
            await self.semantic_cache.set(query, response, intent_result.primary.value)
            
            # End trace
            TraceContext.end_trace(success=True)
            
            return {**response, "trace": trace.to_dict()}
            
        except asyncio.CancelledError:
            TraceContext.end_trace(success=False, error="Cancelled")
            return {
                "success": False,
                "error": "Request cancelled",
                "trace": trace.to_dict(),
            }
        except Exception as e:
            TraceContext.end_trace(success=False, error=str(e))
            logger.error(f"[ProductionPipeline] Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "trace": trace.to_dict(),
            }
    
    async def _gather_facts_parallel(
        self,
        lat: float,
        lng: float,
        context: Dict[str, Any],
        token: Optional[CancellationToken] = None,
    ) -> Dict[str, Any]:
        """Gather facts from all agents in parallel."""
        
        # Define fact-gathering tasks
        tasks = [
            FactGatheringTask(
                name="spatial",
                agent_name="spatial_service",
                func=self._gather_spatial_facts,
                timeout=5.0,
            ),
            FactGatheringTask(
                name="terrain",
                agent_name="terrain_service",
                func=self._gather_terrain_facts,
                timeout=5.0,
            ),
            FactGatheringTask(
                name="market",
                agent_name="property_service",
                func=self._gather_market_facts,
                timeout=8.0,
            ),
            FactGatheringTask(
                name="locality",
                agent_name="locality_service",
                func=self._gather_locality_facts,
                timeout=3.0,
            ),
        ]
        
        return await self.fact_gatherer.gather(lat, lng, context, tasks, token)
    
    async def _gather_spatial_facts(
        self, lat: float, lng: float, context: Dict
    ) -> Dict[str, Any]:
        """Gather spatial facts."""
        try:
            from spatial.spatial_service import get_spatial_service
            service = get_spatial_service()
            summary = service.get_summary(lat, lng, radius_m=1000)
            
            if isinstance(summary, dict):
                return {
                    "poi_count": summary.get('by_category', {}).get('poi', 0),
                    "transport_count": summary.get('by_category', {}).get('transport', 0),
                    "accessibility_score": summary.get('accessibility_score', 0),
                    "walkability_score": summary.get('walkability_score', 0),
                }
            else:
                return {
                    "poi_count": getattr(summary, 'poi_count', 0),
                    "transport_count": getattr(summary, 'transport_count', 0),
                    "accessibility_score": getattr(summary, 'accessibility_score', 0),
                    "walkability_score": getattr(summary, 'walkability_score', 0),
                }
        except Exception as e:
            logger.warning(f"Spatial facts error: {e}")
            return {}
    
    async def _gather_terrain_facts(
        self, lat: float, lng: float, context: Dict
    ) -> Dict[str, Any]:
        """Gather terrain facts."""
        try:
            from spatial.terrain_service import get_terrain_service
            service = get_terrain_service()
            terrain = service.get_terrain_analysis(lat, lng)
            
            if terrain:
                return {
                    "elevation_m": terrain.get('elevation_mean'),
                    "slope_deg": terrain.get('slope_mean'),
                    "flood_risk": terrain.get('flood_risk', 'unknown'),
                }
            return {}
        except Exception as e:
            logger.warning(f"Terrain facts error: {e}")
            return {}
    
    async def _gather_market_facts(
        self, lat: float, lng: float, context: Dict
    ) -> Dict[str, Any]:
        """Gather market facts."""
        try:
            from services.property_service import get_property_service
            service = get_property_service()
            props = service.search(lat=lat, lng=lng, radius_m=1500, limit=100)
            
            if not props:
                return {}
            
            prices = [p.get('price_per_sq_ft') for p in props if p.get('price_per_sq_ft')]
            avg_price = sum(prices) / len(prices) if prices else None
            
            return {
                "avg_price_per_sqft": avg_price,
                "active_listings": len(props),
                "demand_level": "High" if len(props) > 50 else "Medium" if len(props) > 20 else "Low",
            }
        except Exception as e:
            logger.warning(f"Market facts error: {e}")
            return {}
    
    async def _gather_locality_facts(
        self, lat: float, lng: float, context: Dict
    ) -> Dict[str, Any]:
        """Gather locality facts."""
        try:
            from services.locality_service import get_locality_service
            service = get_locality_service()
            nearby = service.get_nearby_locality(lat, lng, radius_km=3.0)
            
            if nearby:
                return {
                    "locality_name": nearby.get('locality_name'),
                    "growth_phase": nearby.get('growth_phase'),
                    "risk_level": nearby.get('risk_level'),
                    "hotspot_score": nearby.get('hotspot_score'),
                }
            return {}
        except Exception as e:
            logger.warning(f"Locality facts error: {e}")
            return {}


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_pipeline: Optional[ProductionQueryPipeline] = None


def get_production_pipeline() -> ProductionQueryPipeline:
    """Get the global production pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = ProductionQueryPipeline()
    return _pipeline
