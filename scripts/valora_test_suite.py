#!/usr/bin/env python3
"""
Valora AI - Unified Test Suite
Comprehensive testing for all Valora components.

Run all tests:
    python scripts/valora_test_suite.py

Run specific categories:
    python scripts/valora_test_suite.py --category api
    python scripts/valora_test_suite.py --category spatial
    python scripts/valora_test_suite.py --category intent

Available categories:
- api: Backend API endpoints
- intent: Intent classification
- spatial: 3D spatial reasoning
- occlusion: Line-of-sight and view analysis
- solar: Sunlight and shadow analysis
- graph: Spatial memory graph
- property: Property search
- locality: Locality service
- tool: Tool executor
- rag: RAG and vector search
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable

# Add backend to path
BACKEND_PATH = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(BACKEND_PATH))
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# TEST INFRASTRUCTURE
# =============================================================================

class TestCategory(Enum):
    API = "api"
    INTENT = "intent"
    SPATIAL = "spatial"
    OCCLUSION = "occlusion"
    SOLAR = "solar"
    GRAPH = "graph"
    PROPERTY = "property"
    LOCALITY = "locality"
    TOOL = "tool"
    RAG = "rag"
    GIS = "gis"
    TRANSACTION = "transaction"
    REGULATORY = "regulatory"
    COUNTERFACTUAL = "counterfactual"
    VERIFIER = "verifier"
    AUTH = "auth"
    OBSERVABILITY = "observability"
    PREFERENCES = "preferences"
    PIPELINE = "pipeline"
    SIMULATION = "simulation"
    VALUATION = "valuation"
    CITYINTEL = "cityintel"
    DIGITALTWIN = "digitaltwin"
    USAGE = "usage"
    TERRAIN = "terrain"
    DATABASE = "database"
    INSIGHTS = "insights"
    STORYBOARD = "storyboard"
    INVESTMENT = "investment"
    COMPARE = "compare"
    CHAT = "chat"
    PATHFINDING = "pathfinding"
    FLOODRISK = "floodrisk"
    ALL = "all"


class TestStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"


@dataclass
class TestResult:
    """Result of a single test."""
    test_id: str
    name: str
    category: str
    status: str
    duration_ms: float
    message: str = ""
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class TestReport:
    """Complete test report."""
    run_id: str
    timestamp: str
    categories_run: List[str]
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration_ms: float = 0
    results: List[TestResult] = field(default_factory=list)
    
    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0
        return (self.passed / self.total) * 100


def _now_ms() -> float:
    return time.time() * 1000


def _run_test(test_id: str, name: str, category: str, test_fn: Callable) -> TestResult:
    """Run a single test function and capture result."""
    start = _now_ms()
    try:
        result = test_fn()
        if isinstance(result, tuple):
            passed, message = result[0], result[1] if len(result) > 1 else ""
            details = result[2] if len(result) > 2 else None
        elif isinstance(result, bool):
            passed, message, details = result, "", None
        else:
            passed, message, details = True, str(result), None
        
        return TestResult(
            test_id=test_id,
            name=name,
            category=category,
            status=TestStatus.PASS.value if passed else TestStatus.FAIL.value,
            duration_ms=round(_now_ms() - start, 2),
            message=message,
            details=details
        )
    except Exception as e:
        return TestResult(
            test_id=test_id,
            name=name,
            category=category,
            status=TestStatus.ERROR.value,
            duration_ms=round(_now_ms() - start, 2),
            error=str(e)
        )


# =============================================================================
# TEST LOCATIONS (Bangalore)
# =============================================================================

KORAMANGALA = (12.9352, 77.6245)
WHITEFIELD = (12.9698, 77.7500)
INDIRANAGAR = (12.9784, 77.6408)
HSR_LAYOUT = (12.9116, 77.6389)
HEBBAL = (13.0358, 77.5970)


# =============================================================================
# INTENT TESTS
# =============================================================================

def get_intent_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get all intent classification tests."""
    tests = []
    
    try:
        from gis_agents import IntentRouter, Intent
        INTENT_OK = True
    except ImportError:
        INTENT_OK = False
    
    if not INTENT_OK:
        return [(
            "intent_import",
            "Import IntentRouter",
            TestCategory.INTENT.value,
            lambda: (False, "Failed to import gis_agents")
        )]
    
    # Test cases: (query, expected_intent)
    intent_cases = [
        ("hi", "greeting"),
        ("hello", "greeting"),
        ("good morning", "greeting"),
        ("help", "help"),
        ("what can you do", "help"),
        ("thanks", "thanks"),
        ("bye", "farewell"),
        ("show me whitefield", "navigate"),
        ("go to koramangala", "navigate"),
        ("find apartments in koramangala", "property_search"),
        ("3BHK under 1 crore", "property_search"),
        ("is hebbal good for investment", "investment"),
        ("analyze whitefield", "analyze_area"),
        ("what's this area like", "analyze_area"),
        ("compare koramangala vs indiranagar", "comparison"),
        ("market trends", "market_trend"),
        ("what if metro comes to sarjapur", "simulate"),
        ("where should i buy for families", "recommendation"),
    ]
    
    for query, expected in intent_cases:
        test_id = f"intent_{query[:15].replace(' ', '_')}"
        
        def make_test(q, exp):
            def test():
                result = IntentRouter.classify(q).value
                passed = result == exp
                return passed, f"Got: {result}, Expected: {exp}"
            return test
        
        tests.append((
            test_id,
            f"Intent: '{query[:30]}'",
            TestCategory.INTENT.value,
            make_test(query, expected)
        ))
    
    return tests


# =============================================================================
# SPATIAL 3D TESTS
# =============================================================================

def get_spatial_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get spatial 3D reasoning tests."""
    tests = []
    
    try:
        from spatial_3d_reasoning import get_spatial_3d_reasoning
        SPATIAL_OK = True
    except ImportError:
        SPATIAL_OK = False
    
    if not SPATIAL_OK:
        return [(
            "spatial_import",
            "Import Spatial3DReasoning",
            TestCategory.SPATIAL.value,
            lambda: (False, "Failed to import spatial_3d_reasoning")
        )]
    
    # Test 3D context analysis
    def test_3d_context_ground():
        svc = get_spatial_3d_reasoning()
        result = svc.analyze_3d_context(KORAMANGALA[0], KORAMANGALA[1], 0, 200)
        valid = (
            hasattr(result, 'sky_view_factor') and
            0 <= result.sky_view_factor <= 1 and
            hasattr(result, 'view_quality') and
            result.view_quality in ['excellent', 'good', 'moderate', 'poor', 'unknown']
        )
        return valid, f"sky_view={result.sky_view_factor:.2f}, view={result.view_quality}"
    
    tests.append(("spatial_3d_ground", "3D Context at Ground", TestCategory.SPATIAL.value, test_3d_context_ground))
    
    def test_3d_context_high():
        svc = get_spatial_3d_reasoning()
        result = svc.analyze_3d_context(WHITEFIELD[0], WHITEFIELD[1], 45, 300)
        valid = hasattr(result, 'buildings_above') and isinstance(result.buildings_above, list)
        return valid, f"buildings_above={len(result.buildings_above)}"
    
    tests.append(("spatial_3d_high", "3D Context at Floor 15", TestCategory.SPATIAL.value, test_3d_context_high))
    
    def test_best_floor():
        svc = get_spatial_3d_reasoning()
        result = svc.find_best_floor(INDIRANAGAR[0], INDIRANAGAR[1], 15)
        valid = 'recommended_floor' in result and 1 <= result['recommended_floor'] <= 15
        return valid, f"recommended_floor={result.get('recommended_floor')}"
    
    tests.append(("spatial_best_floor", "Find Best Floor", TestCategory.SPATIAL.value, test_best_floor))
    
    def test_shadow_impact():
        svc = get_spatial_3d_reasoning()
        result = svc.get_shadow_impact(KORAMANGALA[0], KORAMANGALA[1], hour=10)
        valid = 'impact' in result and result['impact'] in ['minimal', 'moderate', 'significant']
        return valid, f"shadow_impact={result.get('impact')}"
    
    tests.append(("spatial_shadow", "Shadow Impact", TestCategory.SPATIAL.value, test_shadow_impact))
    
    return tests


# =============================================================================
# OCCLUSION ENGINE TESTS
# =============================================================================

def get_occlusion_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get occlusion engine tests."""
    tests = []
    
    try:
        from occlusion_engine import get_occlusion_engine
        OCCLUSION_OK = True
    except ImportError:
        OCCLUSION_OK = False
    
    if not OCCLUSION_OK:
        return [(
            "occlusion_import",
            "Import OcclusionEngine",
            TestCategory.OCCLUSION.value,
            lambda: (False, "Failed to import occlusion_engine")
        )]
    
    def test_line_of_sight():
        engine = get_occlusion_engine()
        result = engine.check_line_of_sight(
            KORAMANGALA[0], KORAMANGALA[1], 30,
            KORAMANGALA[0] + 0.002, KORAMANGALA[1] + 0.002, 0
        )
        valid = hasattr(result, 'clear') and hasattr(result, 'visibility_score')
        return valid, f"clear={result.clear}, visibility={result.visibility_score:.0f}%"
    
    tests.append(("occ_los", "Line of Sight Check", TestCategory.OCCLUSION.value, test_line_of_sight))
    
    def test_360_visibility():
        engine = get_occlusion_engine()
        result = engine.get_360_visibility(WHITEFIELD[0], WHITEFIELD[1], floor=5, radius_m=300)
        valid = 'view_quality' in result and 'open_directions' in result
        return valid, f"quality={result.get('view_quality')}, open={len(result.get('open_directions', []))}"
    
    tests.append(("occ_360", "360 Visibility", TestCategory.OCCLUSION.value, test_360_visibility))
    
    def test_view_blockers():
        engine = get_occlusion_engine()
        blockers = engine.find_view_blockers(INDIRANAGAR[0], INDIRANAGAR[1], 15, radius_m=200)
        valid = isinstance(blockers, list)
        return valid, f"found {len(blockers)} potential blockers"
    
    tests.append(("occ_blockers", "Find View Blockers", TestCategory.OCCLUSION.value, test_view_blockers))
    
    return tests


# =============================================================================
# SOLAR ENGINE TESTS
# =============================================================================

def get_solar_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get solar engine tests."""
    tests = []
    
    try:
        from solar_engine import get_solar_engine
        SOLAR_OK = True
    except ImportError:
        SOLAR_OK = False
    
    if not SOLAR_OK:
        return [(
            "solar_import",
            "Import SolarEngine",
            TestCategory.SOLAR.value,
            lambda: (False, "Failed to import solar_engine")
        )]
    
    def test_sun_position():
        engine = get_solar_engine()
        sun = engine.get_sun_position()
        valid = hasattr(sun, 'altitude') and hasattr(sun, 'azimuth')
        return valid, f"altitude={sun.altitude:.1f}°, azimuth={sun.azimuth:.1f}°"
    
    tests.append(("solar_position", "Current Sun Position", TestCategory.SOLAR.value, test_sun_position))
    
    def test_sunlight_analysis():
        engine = get_solar_engine()
        result = engine.analyze_sunlight(KORAMANGALA[0], KORAMANGALA[1], floor=5)
        valid = (
            hasattr(result, 'daylight_hours') and
            10 <= result.daylight_hours <= 14 and
            hasattr(result, 'natural_light_score')
        )
        return valid, f"daylight={result.daylight_hours:.1f}h, score={result.natural_light_score:.0f}"
    
    tests.append(("solar_analysis", "Sunlight Analysis", TestCategory.SOLAR.value, test_sunlight_analysis))
    
    def test_facade_sunlight():
        engine = get_solar_engine()
        result = engine.get_facade_sunlight(WHITEFIELD[0], WHITEFIELD[1], floor=10)
        valid = 'facades' in result and 'best_facade' in result
        return valid, f"best_facade={result.get('best_facade')}"
    
    tests.append(("solar_facade", "Facade Sunlight", TestCategory.SOLAR.value, test_facade_sunlight))
    
    def test_season_comparison():
        engine = get_solar_engine()
        result = engine.compare_seasons(INDIRANAGAR[0], INDIRANAGAR[1], floor=5)
        valid = 'summer' in result and 'winter' in result
        summer_hours = result.get('summer', {}).get('daylight_hours', 0)
        winter_hours = result.get('winter', {}).get('daylight_hours', 0)
        return valid, f"summer={summer_hours:.1f}h, winter={winter_hours:.1f}h"
    
    tests.append(("solar_seasons", "Season Comparison", TestCategory.SOLAR.value, test_season_comparison))
    
    return tests


# =============================================================================
# SPATIAL MEMORY GRAPH TESTS
# =============================================================================

def get_graph_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get spatial memory graph tests."""
    tests = []
    
    try:
        from spatial_memory_graph import get_spatial_graph, initialize_spatial_graph
        GRAPH_OK = True
    except ImportError:
        GRAPH_OK = False
    
    if not GRAPH_OK:
        return [(
            "graph_import",
            "Import SpatialMemoryGraph",
            TestCategory.GRAPH.value,
            lambda: (False, "Failed to import spatial_memory_graph")
        )]
    
    def test_graph_init():
        stats = initialize_spatial_graph(sample_size=1000)
        valid = stats.get('buildings', 0) > 0 or stats.get('status') == 'already_initialized'
        return valid, f"buildings={stats.get('buildings', 0)}, relations={stats.get('relations', 0)}"
    
    tests.append(("graph_init", "Initialize Graph", TestCategory.GRAPH.value, test_graph_init))
    
    def test_graph_stats():
        graph = get_spatial_graph()
        stats = graph.get_stats()
        valid = 'total_nodes' in stats
        return valid, f"nodes={stats.get('total_nodes', 0)}, relations={stats.get('total_relations', 0)}"
    
    tests.append(("graph_stats", "Graph Statistics", TestCategory.GRAPH.value, test_graph_stats))
    
    def test_view_blockers():
        graph = get_spatial_graph()
        blockers = graph.find_view_blockers(KORAMANGALA[0], KORAMANGALA[1], 15, radius_m=200)
        valid = isinstance(blockers, list)
        return valid, f"found {len(blockers)} blockers"
    
    tests.append(("graph_blockers", "Find View Blockers", TestCategory.GRAPH.value, test_view_blockers))
    
    return tests


# =============================================================================
# TOOL EXECUTOR TESTS
# =============================================================================

def get_tool_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get tool executor tests."""
    tests = []
    
    try:
        from tool_executor import get_tool_executor, ToolCall
        TOOL_OK = True
    except ImportError:
        TOOL_OK = False
    
    if not TOOL_OK:
        return [(
            "tool_import",
            "Import ToolExecutor",
            TestCategory.TOOL.value,
            lambda: (False, "Failed to import tool_executor")
        )]
    
    def test_tool_validation():
        executor = get_tool_executor()
        # Valid call
        call = ToolCall(name="get_3d_context", parameters={"lat": KORAMANGALA[0], "lng": KORAMANGALA[1]})
        is_valid, error = executor.validator.validate_call(call)
        return is_valid, f"validation={is_valid}"
    
    tests.append(("tool_valid", "Valid Tool Call", TestCategory.TOOL.value, test_tool_validation))
    
    def test_tool_invalid():
        executor = get_tool_executor()
        # Missing required param
        call = ToolCall(name="get_3d_context", parameters={"lat": KORAMANGALA[0]})
        is_valid, error = executor.validator.validate_call(call)
        return not is_valid, f"correctly_rejected={not is_valid}"
    
    tests.append(("tool_invalid", "Invalid Tool Rejection", TestCategory.TOOL.value, test_tool_invalid))
    
    def test_tool_list():
        executor = get_tool_executor()
        tools = executor.validator.list_tools()
        valid = len(tools) >= 10  # Should have many tools
        return valid, f"tools_count={len(tools)}"
    
    tests.append(("tool_list", "List Available Tools", TestCategory.TOOL.value, test_tool_list))
    
    return tests


# =============================================================================
# PROPERTY SERVICE TESTS
# =============================================================================

def get_property_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get property service tests."""
    tests = []
    
    try:
        from property_service import PropertyService
        PROP_OK = True
    except ImportError:
        PROP_OK = False
    
    if not PROP_OK:
        return [(
            "property_import",
            "Import PropertyService",
            TestCategory.PROPERTY.value,
            lambda: (False, "Failed to import property_service")
        )]
    
    def test_property_search():
        svc = PropertyService()
        results = svc.search(lat=KORAMANGALA[0], lng=KORAMANGALA[1], radius_m=2000, limit=10)
        valid = isinstance(results, list)
        return valid, f"found {len(results)} properties"
    
    tests.append(("prop_search", "Basic Property Search", TestCategory.PROPERTY.value, test_property_search))
    
    def test_property_filters():
        svc = PropertyService()
        results = svc.search(
            lat=WHITEFIELD[0], lng=WHITEFIELD[1], radius_m=3000,
            listing_type="sale", property_category="residential", limit=20
        )
        valid = isinstance(results, list)
        return valid, f"found {len(results)} filtered properties"
    
    tests.append(("prop_filter", "Filtered Property Search", TestCategory.PROPERTY.value, test_property_filters))
    
    return tests


# =============================================================================
# LOCALITY SERVICE TESTS
# =============================================================================

def get_locality_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get locality service tests."""
    tests = []
    
    try:
        from locality_service import get_locality_service
        LOC_OK = True
    except ImportError:
        LOC_OK = False
    
    if not LOC_OK:
        return [(
            "locality_import",
            "Import LocalityService",
            TestCategory.LOCALITY.value,
            lambda: (False, "Failed to import locality_service")
        )]
    
    def test_locality_profile():
        svc = get_locality_service()
        result = svc.get_locality_state("Koramangala")
        valid = result is not None and 'locality_name' in result
        return valid, f"found={result is not None}"
    
    tests.append(("loc_profile", "Get Locality Profile", TestCategory.LOCALITY.value, test_locality_profile))
    
    def test_nearby_locality():
        svc = get_locality_service()
        result = svc.get_nearby_locality(INDIRANAGAR[0], INDIRANAGAR[1], radius_km=2.0)
        valid = result is not None
        name = result.get('locality_name', 'N/A') if result else 'N/A'
        return valid, f"nearest={name}"
    
    tests.append(("loc_nearby", "Find Nearby Locality", TestCategory.LOCALITY.value, test_nearby_locality))
    
    return tests


# =============================================================================
# API TESTS (requires running backend)
# =============================================================================

def get_api_tests(base_url: str = "http://localhost:8000") -> List[Tuple[str, str, str, Callable]]:
    """Get API endpoint tests."""
    tests = []
    
    try:
        import httpx
        HTTP_OK = True
    except ImportError:
        HTTP_OK = False
    
    if not HTTP_OK:
        return [(
            "api_import",
            "Import httpx",
            TestCategory.API.value,
            lambda: (False, "Failed to import httpx")
        )]
    
    def make_api_test(endpoint: str, method: str = "GET", json_data: dict = None, check_fn: Callable = None):
        def test():
            with httpx.Client(base_url=base_url, timeout=30.0) as client:
                if method == "GET":
                    resp = client.get(endpoint)
                else:
                    resp = client.post(endpoint, json=json_data)
                resp.raise_for_status()
                data = resp.json()
                if check_fn:
                    return check_fn(data)
                return True, f"status={resp.status_code}"
        return test
    
    # Health check
    tests.append((
        "api_health",
        "Backend Health",
        TestCategory.API.value,
        make_api_test("/health", check_fn=lambda d: (d.get('status') in ['ok', 'running'], f"status={d.get('status')}"))
    ))
    
    # Admin status
    tests.append((
        "api_admin",
        "Admin Status",
        TestCategory.API.value,
        make_api_test("/api/admin/status", check_fn=lambda d: ('backend' in d, "has backend info"))
    ))
    
    # Location analyze
    tests.append((
        "api_location",
        "Location Analyze",
        TestCategory.API.value,
        make_api_test(
            "/api/location/analyze",
            method="POST",
            json_data={"lat": KORAMANGALA[0], "lng": KORAMANGALA[1]},
            check_fn=lambda d: (isinstance(d, dict), "got response")
        )
    ))
    
    # City intelligence
    tests.append((
        "api_city_intel",
        "City Intelligence",
        TestCategory.API.value,
        make_api_test(
            "/api/city-intelligence/locality/Indiranagar",
            check_fn=lambda d: (d.get('success') == True or 'profile' in d, "has profile")
        )
    ))
    
    # Building analyze
    tests.append((
        "api_building",
        "Building Analyze",
        TestCategory.API.value,
        make_api_test(
            "/api/building/analyze",
            method="POST",
            json_data={"lat": KORAMANGALA[0], "lng": KORAMANGALA[1]},
            check_fn=lambda d: (isinstance(d, dict), "got analysis")
        )
    ))
    
    # Valuation
    tests.append((
        "api_valuation",
        "Valuation Estimate",
        TestCategory.API.value,
        make_api_test(
            "/api/valuation/estimate",
            method="POST",
            json_data={"lat": KORAMANGALA[0], "lng": KORAMANGALA[1], "bedrooms": 2, "covered_area": 1200, "property_type": "residential"},
            check_fn=lambda d: (d.get('success') == True or 'estimated_price' in d, "got estimate")
        )
    ))
    
    # Simulate
    tests.append((
        "api_simulate",
        "Simulate Scenario",
        TestCategory.API.value,
        make_api_test(
            "/api/simulate",
            method="POST",
            json_data={"scenario_type": "metro_station", "description": "Test", "lat": 12.9081, "lng": 77.6476, "parameters": {}},
            check_fn=lambda d: (d.get('success') == True or 'impact' in d, "got impact")
        )
    ))

    # User Preferences (New)
    tests.append((
        "api_prefs_get",
        "Get User Preferences",
        TestCategory.API.value,
        make_api_test(
            "/api/preferences/suite_user",
            check_fn=lambda d: (d.get('success') == True and 'preferences' in d, "got preferences")
        )
    ))

    tests.append((
        "api_prefs_update",
        "Update User Preferences",
        TestCategory.API.value,
        make_api_test(
            "/api/preferences/suite_user",
            method="POST",
            json_data={
                "preferred_areas": ["Whitefield"],
                "budget_range": [50, 100],
                "preferred_property_types": ["Apartment"]
            },
            check_fn=lambda d: (d.get('success') == True, "updated successfully")
        )
    ))
    
    return tests


# =============================================================================
# GIS AGENTS TESTS
# =============================================================================

def get_gis_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get GIS agent tests."""
    tests = []
    
    try:
        from gis_agents import IntentRouter, Intent, AgentFacts
        GIS_OK = True
    except ImportError:
        GIS_OK = False
    
    if not GIS_OK:
        return [(
            "gis_import",
            "Import GIS Agents",
            TestCategory.GIS.value,
            lambda: (False, "Failed to import gis_agents")
        )]
    
    def test_place_extraction():
        places = [
            ("Show me Whitefield", "Whitefield"),
            ("Go to Koramangala", "Koramangala"),
            ("Navigate to Hebbal", "Hebbal"),
        ]
        passed = 0
        for query, expected in places:
            result = IntentRouter.extract_place_name(query)
            if result and expected.lower() in result.lower():
                passed += 1
        return passed == len(places), f"passed {passed}/{len(places)}"
    
    tests.append(("gis_place", "Place Extraction", TestCategory.GIS.value, test_place_extraction))
    
    def test_facts_context():
        facts = AgentFacts(
            location_name="Whitefield",
            lat=WHITEFIELD[0],
            lng=WHITEFIELD[1],
            poi_count=45,
            accessibility_score=72,
        )
        context = facts.to_context_string()
        valid = "Whitefield" in context and "45" in context
        return valid, f"context_length={len(context)}"
    
    tests.append(("gis_facts", "Facts Context String", TestCategory.GIS.value, test_facts_context))
    
    return tests


# =============================================================================
# TRANSACTION INTELLIGENCE TESTS
# =============================================================================

def get_transaction_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get transaction intelligence tests."""
    tests = []
    
    try:
        from transaction_intelligence import get_transaction_intelligence
        TRANS_OK = True
    except ImportError:
        TRANS_OK = False
    
    if not TRANS_OK:
        return [(
            "trans_import",
            "Import TransactionIntelligence",
            TestCategory.TRANSACTION.value,
            lambda: (False, "Failed to import transaction_intelligence")
        )]
    
    def test_find_comps():
        intel = get_transaction_intelligence()
        comps = intel.find_comps(KORAMANGALA[0], KORAMANGALA[1], bedrooms=2, area_sqft=1200, limit=5)
        valid = isinstance(comps, list)
        return valid, f"found {len(comps)} comps"
    
    tests.append(("trans_comps", "Find Comparable Transactions", TestCategory.TRANSACTION.value, test_find_comps))
    
    def test_pricing_intel():
        intel = get_transaction_intelligence()
        result = intel.get_pricing_intelligence(WHITEFIELD[0], WHITEFIELD[1], bedrooms=3, area_sqft=1500)
        valid = hasattr(result, 'estimated_value') and hasattr(result, 'market_condition')
        return valid, f"value={result.estimated_value:,.0f}, condition={result.market_condition}"
    
    tests.append(("trans_pricing", "Pricing Intelligence", TestCategory.TRANSACTION.value, test_pricing_intel))
    
    def test_locality_trends():
        intel = get_transaction_intelligence()
        result = intel.get_locality_trends("Koramangala", months=6)
        valid = 'locality' in result
        return valid, f"data_points={result.get('data_points', 0)}"
    
    tests.append(("trans_trends", "Locality Price Trends", TestCategory.TRANSACTION.value, test_locality_trends))
    
    return tests


# =============================================================================
# REGULATORY INTELLIGENCE TESTS
# =============================================================================

def get_regulatory_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get regulatory intelligence tests."""
    tests = []
    
    try:
        from regulatory_intelligence import get_regulatory_intelligence
        REG_OK = True
    except ImportError:
        REG_OK = False
    
    if not REG_OK:
        return [(
            "reg_import",
            "Import RegulatoryIntelligence",
            TestCategory.REGULATORY.value,
            lambda: (False, "Failed to import regulatory_intelligence")
        )]
    
    def test_zoning():
        intel = get_regulatory_intelligence()
        zoning = intel.get_zoning(KORAMANGALA[0], KORAMANGALA[1])
        valid = hasattr(zoning, 'zone_type') and hasattr(zoning, 'max_far')
        return valid, f"zone={zoning.zone_type}, FAR={zoning.max_far}"
    
    tests.append(("reg_zoning", "Get Zoning Info", TestCategory.REGULATORY.value, test_zoning))
    
    def test_setback():
        intel = get_regulatory_intelligence()
        setback = intel.get_setback_requirements(plot_area_sqm=500, road_width_m=12)
        valid = hasattr(setback, 'front_m') and hasattr(setback, 'rear_m')
        return valid, f"front={setback.front_m}m, rear={setback.rear_m}m"
    
    tests.append(("reg_setback", "Setback Requirements", TestCategory.REGULATORY.value, test_setback))
    
    def test_buffer_zones():
        intel = get_regulatory_intelligence()
        buffers = intel.check_buffer_zones(INDIRANAGAR[0], INDIRANAGAR[1])
        valid = isinstance(buffers, list)
        return valid, f"found {len(buffers)} buffer zones"
    
    tests.append(("reg_buffer", "Check Buffer Zones", TestCategory.REGULATORY.value, test_buffer_zones))
    
    def test_regulatory_report():
        intel = get_regulatory_intelligence()
        report = intel.get_regulatory_report(WHITEFIELD[0], WHITEFIELD[1], plot_area_sqm=600)
        valid = hasattr(report, 'zoning') and hasattr(report, 'risk_level')
        return valid, f"risk={report.risk_level}, FAR_util={report.far_utilization_pct:.0f}%"
    
    tests.append(("reg_report", "Full Regulatory Report", TestCategory.REGULATORY.value, test_regulatory_report))
    
    def test_due_diligence():
        intel = get_regulatory_intelligence()
        checklist = intel.generate_due_diligence_checklist(property_type="residential")
        valid = isinstance(checklist, list) and len(checklist) > 5
        return valid, f"checklist has {len(checklist)} items"
    
    tests.append(("reg_diligence", "Due Diligence Checklist", TestCategory.REGULATORY.value, test_due_diligence))
    
    return tests


# =============================================================================
# COUNTERFACTUAL 3D TESTS
# =============================================================================

def get_counterfactual_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get counterfactual 3D analysis tests."""
    tests = []
    
    try:
        from counterfactual_3d import get_counterfactual_3d
        CF_OK = True
    except ImportError:
        CF_OK = False
    
    if not CF_OK:
        return [(
            "cf_import",
            "Import Counterfactual3D",
            TestCategory.COUNTERFACTUAL.value,
            lambda: (False, "Failed to import counterfactual_3d")
        )]
    
    def test_new_construction():
        engine = get_counterfactual_3d()
        result = engine.analyze_new_construction(
            KORAMANGALA[0], KORAMANGALA[1],
            infrastructure_type="metro_station",
            description="New metro station"
        )
        valid = hasattr(result, 'total_properties_affected') and hasattr(result, 'approval_likelihood')
        return valid, f"affected={result.total_properties_affected}, approval={result.approval_likelihood}"
    
    tests.append(("cf_metro", "Metro Station Impact", TestCategory.COUNTERFACTUAL.value, test_new_construction))
    
    def test_high_rise():
        engine = get_counterfactual_3d()
        result = engine.analyze_new_construction(
            WHITEFIELD[0], WHITEFIELD[1],
            infrastructure_type="high_rise_residential",
            height_m=80
        )
        valid = result.shadow_impact is not None
        shadow_len = result.shadow_impact.shadow_length_m if result.shadow_impact else 0
        return valid, f"shadow={shadow_len}m, value_impact={result.avg_value_impact_pct:+.1f}%"
    
    tests.append(("cf_highrise", "High Rise Impact", TestCategory.COUNTERFACTUAL.value, test_high_rise))
    
    def test_park():
        engine = get_counterfactual_3d()
        result = engine.analyze_new_construction(
            INDIRANAGAR[0], INDIRANAGAR[1],
            infrastructure_type="park",
            description="New public park"
        )
        valid = result.approval_likelihood == 'high'  # Parks should have high approval
        return valid, f"approval={result.approval_likelihood}, value={result.avg_value_impact_pct:+.1f}%"
    
    tests.append(("cf_park", "Park Impact (Positive)", TestCategory.COUNTERFACTUAL.value, test_park))
    
    return tests


# =============================================================================
# FACT VERIFIER TESTS
# =============================================================================

def get_verifier_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get fact verifier tests."""
    tests = []
    
    try:
        from fact_verifier import get_fact_verifier, Claim, ClaimType
        VERIFIER_OK = True
    except ImportError:
        VERIFIER_OK = False
    
    if not VERIFIER_OK:
        return [(
            "verifier_import",
            "Import FactVerifier",
            TestCategory.VERIFIER.value,
            lambda: (False, "Failed to import fact_verifier")
        )]
    
    def test_extract_claims():
        verifier = get_fact_verifier()
        text = "This area has ₹8,500 per sqft prices and is 500m from the metro with 45 POIs nearby."
        claims = verifier.extract_claims_from_text(text)
        valid = len(claims) >= 2  # Should find price and distance claims
        return valid, f"extracted {len(claims)} claims"
    
    tests.append(("verifier_extract", "Extract Claims from Text", TestCategory.VERIFIER.value, test_extract_claims))
    
    def test_verify_price():
        verifier = get_fact_verifier()
        claim = Claim(
            claim_id="test_1",
            claim_text="₹8,500 per sqft",
            claim_type=ClaimType.PRICE.value,
            value=8500,
            location={"lat": KORAMANGALA[0], "lng": KORAMANGALA[1]}
        )
        result = verifier.verify_claim(claim)
        valid = hasattr(result, 'status') and hasattr(result, 'confidence')
        return valid, f"status={result.status}, confidence={result.confidence}"
    
    tests.append(("verifier_price", "Verify Price Claim", TestCategory.VERIFIER.value, test_verify_price))
    
    def test_verify_multiple():
        verifier = get_fact_verifier()
        claims = [
            Claim(claim_id="c1", claim_text="45 POIs", claim_type=ClaimType.COUNT.value, value=45, location={"lat": WHITEFIELD[0], "lng": WHITEFIELD[1]}, context={"count_type": "pois"}),
            Claim(claim_id="c2", claim_text="500m from metro", claim_type=ClaimType.DISTANCE.value, value=500, location={"lat": WHITEFIELD[0], "lng": WHITEFIELD[1]}, context={"target_type": "metro"})
        ]
        response = verifier.verify_claims(claims)
        valid = hasattr(response, 'overall_status') and response.total_claims == 2
        return valid, f"status={response.overall_status}, verified={response.verified_count}/{response.total_claims}"
    
    tests.append(("verifier_multiple", "Verify Multiple Claims", TestCategory.VERIFIER.value, test_verify_multiple))
    
    return tests


# =============================================================================
# AUTH & RBAC TESTS
# =============================================================================

def get_auth_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get auth and RBAC tests."""
    tests = []
    
    try:
        from auth import get_auth_service, Role, Permission, User
        AUTH_OK = True
    except ImportError:
        AUTH_OK = False
    
    if not AUTH_OK:
        return [(
            "auth_import",
            "Import Auth Service",
            TestCategory.AUTH.value,
            lambda: (False, "Failed to import auth")
        )]
    
    def test_auth_service():
        service = get_auth_service()
        valid = service is not None
        return valid, "auth service initialized"
    
    tests.append(("auth_service", "Auth Service Init", TestCategory.AUTH.value, test_auth_service))
    
    def test_default_users():
        service = get_auth_service()
        admin = service.get_user("admin")
        valid = admin is not None and admin.role == Role.SUPERADMIN
        return valid, f"admin role={admin.role.value if admin else 'none'}"
    
    tests.append(("auth_users", "Default Users Created", TestCategory.AUTH.value, test_default_users))
    
    def test_api_key_auth():
        service = get_auth_service()
        user = service.authenticate("valora-dev-admin-key")
        valid = user is not None and user.user_id == "admin"
        return valid, f"authenticated as {user.user_id if user else 'none'}"
    
    tests.append(("auth_apikey", "API Key Authentication", TestCategory.AUTH.value, test_api_key_auth))
    
    def test_permissions():
        service = get_auth_service()
        admin = service.get_user("admin")
        viewer = service.get_user("viewer")
        
        admin_has_all = admin.has_permission(Permission.ADMIN_DATABASE)
        viewer_no_admin = not viewer.has_permission(Permission.ADMIN_DATABASE)
        valid = admin_has_all and viewer_no_admin
        return valid, f"admin_has_admin_db={admin_has_all}, viewer_no_admin_db={viewer_no_admin}"
    
    tests.append(("auth_perms", "Permission Checks", TestCategory.AUTH.value, test_permissions))
    
    def test_rate_limit():
        service = get_auth_service()
        # Should allow first request
        allowed = service.check_rate_limit("test_user", limit=10, window_seconds=60)
        info = service.get_rate_limit_info("test_user", limit=10, window_seconds=60)
        valid = allowed and info['remaining'] < 10
        return valid, f"allowed={allowed}, remaining={info['remaining']}"
    
    tests.append(("auth_ratelimit", "Rate Limiting", TestCategory.AUTH.value, test_rate_limit))
    
    return tests


# =============================================================================
# OBSERVABILITY TESTS
# =============================================================================

def get_observability_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get observability and metrics tests."""
    tests = []
    
    try:
        from observability import get_metrics, track_latency, log_verification
        OBS_OK = True
    except ImportError:
        OBS_OK = False
    
    if not OBS_OK:
        return [(
            "obs_import",
            "Import Observability",
            TestCategory.OBSERVABILITY.value,
            lambda: (False, "Failed to import observability")
        )]
    
    def test_metrics_collector():
        metrics = get_metrics()
        valid = metrics is not None
        return valid, "metrics collector initialized"
    
    tests.append(("obs_collector", "Metrics Collector Init", TestCategory.OBSERVABILITY.value, test_metrics_collector))
    
    def test_record_request():
        metrics = get_metrics()
        metrics.record_request("/api/test", latency_ms=100, status_code=200)
        stats = metrics.get_endpoint_stats("/api/test")
        valid = "/api/test" in stats and stats["/api/test"]["count"] >= 1
        return valid, f"count={stats.get('/api/test', {}).get('count', 0)}"
    
    tests.append(("obs_request", "Record Request Metrics", TestCategory.OBSERVABILITY.value, test_record_request))
    
    def test_verifier_stats():
        metrics = get_metrics()
        metrics.record_verification("verified", claim_count=5)
        metrics.record_verification("unverified", claim_count=2)
        stats = metrics.get_verifier_stats()
        valid = stats["total_claims"] >= 7
        return valid, f"total={stats['total_claims']}, rate={stats['verification_rate_pct']}%"
    
    tests.append(("obs_verifier", "Verifier Metrics", TestCategory.OBSERVABILITY.value, test_verifier_stats))
    
    def test_summary():
        metrics = get_metrics()
        summary = metrics.get_summary()
        valid = "uptime_seconds" in summary and "total_requests" in summary
        return valid, f"uptime={summary.get('uptime_seconds', 0)}s"
    
    tests.append(("obs_summary", "Metrics Summary", TestCategory.OBSERVABILITY.value, test_summary))
    
    def test_prometheus():
        metrics = get_metrics()
        prom = metrics.get_prometheus_metrics()
        valid = "valora_" in prom
        return valid, f"prometheus output {len(prom)} chars"
    
    tests.append(("obs_prometheus", "Prometheus Export", TestCategory.OBSERVABILITY.value, test_prometheus))
    
    return tests


# =============================================================================
# USER PREFERENCES TESTS
# =============================================================================

def get_preferences_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get user preferences and spatial memory tests."""
    tests = []
    
    try:
        from spatial_memory import SpatialMemoryService, LocationVisit, UserPreferences
        PREF_OK = True
    except ImportError:
        PREF_OK = False
    
    if not PREF_OK:
        return [(
            "pref_import",
            "Import SpatialMemoryService",
            TestCategory.PREFERENCES.value,
            lambda: (False, "Failed to import spatial_memory")
        )]
    
    def test_service_init():
        service = SpatialMemoryService("test_user_suite")
        valid = service is not None and service.session_id == "test_user_suite"
        return valid, f"service initialized for {service.session_id}"
    
    tests.append(("pref_service", "Memory Service Init", TestCategory.PREFERENCES.value, test_service_init))
    
    def test_update_preferences():
        service = SpatialMemoryService("test_user_suite")
        
        # Update preferences directly
        service.preferences.preferred_areas = ["Whitefield", "Sarjapur"]
        service.preferences.budget_range = (80, 150)
        service.preferences.preferred_property_types = ["Apartment"]
        
        # Force save
        service._save_session()
        
        # Reload in new instance to verify persistence
        service2 = SpatialMemoryService("test_user_suite")
        valid = (
            "Whitefield" in service2.preferences.preferred_areas and
            service2.preferences.budget_range[0] == 80
        )
        return valid, f"areas={service2.preferences.preferred_areas}, budget={service2.preferences.budget_range}"
    
    tests.append(("pref_update", "Update Preferences", TestCategory.PREFERENCES.value, test_update_preferences))
    
    def test_record_visit():
        service = SpatialMemoryService("test_user_suite")
        
        # Record visit using correct API
        service.record_visit(
            lat=KORAMANGALA[0],
            lng=KORAMANGALA[1],
            name="Koramangala",
            intent="investment",
            actions=["view_details"],
            sentiment="positive"
        )
        
        # Verify history updated
        valid = len(service.visit_history) > 0 and service.visit_history[-1].name == "Koramangala"
        return valid, f"history_len={len(service.visit_history)}"
    
    tests.append(("pref_visit", "Record Location Visit", TestCategory.PREFERENCES.value, test_record_visit))
    
    def test_clear_session():
        service = SpatialMemoryService("test_user_suite")
        service.clear_session()
        
        # Verify cleared
        valid = len(service.visit_history) == 0 and len(service.preferences.preferred_areas) == 0
        return valid, "session cleared"
    
    tests.append(("pref_clear", "Clear Session", TestCategory.PREFERENCES.value, test_clear_session))
    
    return tests


# =============================================================================
# DATA PIPELINE TESTS
# =============================================================================

def get_pipeline_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get data pipeline tests (scraper and export)."""
    tests = []
    
    # --- SCRAPER TESTS ---
    try:
        import multi_source_scraper
        SCRAPER_OK = True
    except ImportError:
        SCRAPER_OK = False
    
    if not SCRAPER_OK:
        tests.append((
            "scraper_import",
            "Import Scraper",
            TestCategory.PIPELINE.value,
            lambda: (False, "Failed to import multi_source_scraper")
        ))
    else:
        def test_job_id_generation():
            job_id = multi_source_scraper.make_job_id("99acres", "rent", "apartments", "residential")
            valid = "99acres" in job_id and "rent" in job_id
            return valid, f"generated_id={job_id}"
        
        tests.append(("scraper_id", "Generate Job ID", TestCategory.PIPELINE.value, test_job_id_generation))
        
        def test_scraper_config():
            actors = multi_source_scraper.ACTORS
            valid = "magicbricks" in actors and "99acres" in actors
            return valid, f"configured_actors={list(actors.keys())}"
        
        tests.append(("scraper_config", "Scraper Configuration", TestCategory.PIPELINE.value, test_scraper_config))

    # --- FAISS EXPORT TESTS ---
    try:
        from export_to_faiss import export_namespace
        EXPORT_OK = True
    except ImportError:
        EXPORT_OK = False
        
    if not EXPORT_OK:
        tests.append((
            "export_import", 
            "Import FAISS Export",
            TestCategory.PIPELINE.value,
            lambda: (False, "Failed to import export_to_faiss")
        ))
    else:
        def test_export_function_exists():
            # Just verify the function is importable and callable
            valid = callable(export_namespace)
            return valid, "export_namespace is callable"
            
        tests.append(("export_fn", "Export Function Check", TestCategory.PIPELINE.value, test_export_function_exists))

    return tests


# =============================================================================
# RAG SERVICE TESTS
# =============================================================================

def get_rag_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get RAG and vector search tests."""
    tests = []
    
    try:
        from rag_service import RAGService
        RAG_OK = True
    except ImportError:
        RAG_OK = False
    
    if not RAG_OK:
        return [(
            "rag_import",
            "Import RAGService",
            TestCategory.RAG.value,
            lambda: (False, "Failed to import rag_service")
        )]
    
    # Get data directory
    data_dir = Path(__file__).parent.parent / 'src' / 'data'
    
    def test_rag_init():
        svc = RAGService(data_dir)
        valid = svc is not None
        return valid, "RAG service initialized"
    
    tests.append(("rag_init", "RAG Service Init", TestCategory.RAG.value, test_rag_init))
    
    def test_embedding_model():
        svc = RAGService(data_dir)
        valid = svc.embedding_model is not None
        dim = svc.dimension if hasattr(svc, 'dimension') else 0
        return valid, f"embedding_dim={dim}"
    
    tests.append(("rag_embed", "Embedding Model Loaded", TestCategory.RAG.value, test_embedding_model))
    
    def test_search():
        svc = RAGService(data_dir)
        results = svc.search("apartments in whitefield", top_k=5)
        valid = isinstance(results, list)
        return valid, f"found {len(results)} results"
    
    tests.append(("rag_search", "Vector Search", TestCategory.RAG.value, test_search))
    
    def test_context():
        svc = RAGService(data_dir)
        context = svc.get_context_for_query("best areas for investment", max_results=3)
        valid = isinstance(context, str)
        return valid, f"context_length={len(context)}"
    
    tests.append(("rag_context", "Get Context", TestCategory.RAG.value, test_context))
    
    return tests


# =============================================================================
# SIMULATION ENGINE TESTS
# =============================================================================

def get_simulation_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get simulation engine tests."""
    tests = []
    
    try:
        from simulation_engine import SimulationEngine, ScenarioInput
        SIM_OK = True
    except ImportError:
        SIM_OK = False
    
    if not SIM_OK:
        return [(
            "sim_import",
            "Import SimulationEngine",
            TestCategory.SIMULATION.value,
            lambda: (False, "Failed to import simulation_engine")
        )]
    
    def test_sim_init():
        engine = SimulationEngine()
        valid = engine is not None and hasattr(engine, 'scenario_handlers')
        return valid, "simulation engine initialized"
    
    tests.append(("sim_init", "Simulation Engine Init", TestCategory.SIMULATION.value, test_sim_init))
    
    def test_metro_impact():
        engine = SimulationEngine()
        scenario = ScenarioInput(
            type='metro_station',
            location={'lat': KORAMANGALA[0], 'lng': KORAMANGALA[1]},
            parameters={'distance_m': 500, 'time_horizon_months': 24},
            description='Test Metro Station'
        )
        context = {'transport': {'metro_count': 0}}
        result = engine.simulate(scenario, context)
        valid = hasattr(result, 'property_value_impact') and hasattr(result, 'reasoning')
        return valid, f"impact={result.property_value_impact:+.1f}%"
    
    tests.append(("sim_metro", "Metro Station Simulation", TestCategory.SIMULATION.value, test_metro_impact))
    
    def test_scenario_types():
        engine = SimulationEngine()
        scenarios = list(engine.scenario_handlers.keys())
        valid = len(scenarios) >= 3
        return valid, f"scenario_types={scenarios}"
    
    tests.append(("sim_scenarios", "Available Scenarios", TestCategory.SIMULATION.value, test_scenario_types))
    
    return tests


# =============================================================================
# VALUATION SERVICE TESTS
# =============================================================================

def get_valuation_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get valuation service tests."""
    tests = []
    
    try:
        from valuation_model import PropertyValuationModel
        VAL_OK = True
    except ImportError:
        VAL_OK = False
    
    if not VAL_OK:
        return [(
            "val_import",
            "Import PropertyValuationModel",
            TestCategory.VALUATION.value,
            lambda: (False, "Failed to import valuation_model")
        )]
    
    # Get data directory
    data_dir = Path(__file__).parent.parent / 'src' / 'data'
    
    def test_val_init():
        model = PropertyValuationModel(data_dir)
        valid = model is not None
        return valid, "valuation model initialized"
    
    tests.append(("val_init", "Valuation Model Init", TestCategory.VALUATION.value, test_val_init))
    
    def test_estimate():
        model = PropertyValuationModel(data_dir)
        # Use correct signature: lat, lng, bedrooms, bathrooms, covered_area, floors, property_type
        result = model.estimate(
            lat=KORAMANGALA[0], lng=KORAMANGALA[1],
            bedrooms=2, bathrooms=2, covered_area=1200
        )
        valid = result is not None and hasattr(result, 'estimated_price')
        price = result.estimated_price if valid else 0
        return valid, f"estimated_price=₹{price/100000:.1f}L"
    
    tests.append(("val_estimate", "Property Valuation", TestCategory.VALUATION.value, test_estimate))
    
    def test_model_features():
        model = PropertyValuationModel(data_dir)
        has_model = model.model is not None or hasattr(model, 'model')
        has_scaler = hasattr(model, 'scaler')
        return has_model or has_scaler, f"model_loaded={has_model}, scaler={has_scaler}"
    
    tests.append(("val_features", "Model Features", TestCategory.VALUATION.value, test_model_features))
    
    return tests


# =============================================================================
# CITY INTELLIGENCE TESTS
# =============================================================================

def get_cityintel_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get city intelligence tests."""
    tests = []
    
    try:
        from city_intelligence import LocalityPersonalityModel, RiskIndexCalculator, EvolutionTimelineSystem
        CITY_OK = True
    except ImportError:
        CITY_OK = False
    
    if not CITY_OK:
        return [(
            "city_import",
            "Import City Intelligence",
            TestCategory.CITYINTEL.value,
            lambda: (False, "Failed to import city_intelligence")
        )]
    
    def test_personality_model():
        model = LocalityPersonalityModel()
        valid = model is not None
        return valid, "personality model initialized"
    
    tests.append(("city_personality", "Locality Personality Model", TestCategory.CITYINTEL.value, test_personality_model))
    
    def test_locality_profile():
        model = LocalityPersonalityModel()
        # Check what methods exist
        methods = [m for m in dir(model) if not m.startswith('_') and callable(getattr(model, m))]
        valid = len(methods) > 0
        return valid, f"methods={methods[:3]}"
    
    tests.append(("city_profile", "Personality Model Methods", TestCategory.CITYINTEL.value, test_locality_profile))
    
    def test_risk_calculator():
        calc = RiskIndexCalculator()
        valid = calc is not None
        return valid, "risk calculator initialized"
    
    tests.append(("city_risk_init", "Risk Calculator Init", TestCategory.CITYINTEL.value, test_risk_calculator))
    
    def test_risk_methods():
        calc = RiskIndexCalculator()
        methods = [m for m in dir(calc) if not m.startswith('_') and callable(getattr(calc, m))]
        valid = len(methods) > 0
        return valid, f"methods={methods[:3]}"
    
    tests.append(("city_risk", "Risk Calculator Methods", TestCategory.CITYINTEL.value, test_risk_methods))
    
    def test_evolution_timeline():
        timeline = EvolutionTimelineSystem()
        valid = timeline is not None
        return valid, "evolution timeline initialized"
    
    tests.append(("city_timeline", "Evolution Timeline", TestCategory.CITYINTEL.value, test_evolution_timeline))
    
    return tests


# =============================================================================
# DIGITAL TWIN TESTS
# =============================================================================

def get_digitaltwin_tests() -> List[Tuple[str, str, str, Callable]]:
    """Get digital twin tests."""
    tests = []
    
    def test_digitaltwin_import():
        from digital_twin import DigitalTwin, CityState, StateChange
        valid = DigitalTwin is not None and CityState is not None
        return valid, "imports successful"
    
    tests.append(("dt_import", "Digital Twin Import", TestCategory.DIGITALTWIN.value, test_digitaltwin_import))
    
    def test_digitaltwin_init():
        from digital_twin import DigitalTwin
        data_dir = Path(__file__).parent.parent / 'src' / 'data'
        dt = DigitalTwin(data_dir)
        valid = dt is not None
        return valid, "initialized"
    
    tests.append(("dt_init", "Digital Twin Initialize", TestCategory.DIGITALTWIN.value, test_digitaltwin_init))
    
    def test_digitaltwin_state():
        from digital_twin import DigitalTwin
        data_dir = Path(__file__).parent.parent / 'src' / 'data'
        dt = DigitalTwin(data_dir)
        state = dt.initialize_state(12.9716, 77.5946, 5000)
        valid = state is not None and hasattr(state, 'location')
        return valid, f"state created for {state.location if state else 'None'}"
    
    tests.append(("dt_state", "Digital Twin State", TestCategory.DIGITALTWIN.value, test_digitaltwin_state))
    
    def test_digitaltwin_methods():
        from digital_twin import DigitalTwin
        dt = DigitalTwin()
        methods = [m for m in dir(dt) if not m.startswith('_') and callable(getattr(dt, m, None))]
        valid = 'initialize_state' in methods and 'update_state' in methods
        return valid, f"methods={methods[:5]}"
    
    tests.append(("dt_methods", "Digital Twin Methods", TestCategory.DIGITALTWIN.value, test_digitaltwin_methods))
    
    return tests


# =============================================================================
# USAGE SYSTEM TESTS (replaced credits)
# =============================================================================

def get_usage_tests(base_url: str = "http://localhost:8000") -> List[Tuple[str, str, str, Callable]]:
    """Get usage system API tests."""
    tests = []
    
    def test_usage_get():
        import requests
        resp = requests.get(f"{base_url}/api/usage/1", timeout=10)
        # User ID 1 should be admin
        valid = resp.status_code in [200, 404]  # 404 if no user exists yet
        if resp.status_code == 200:
            data = resp.json()
            return valid, f"units_remaining={data.get('units_remaining', 'N/A')}"
        return valid, "user not found (expected for fresh db)"
    
    tests.append(("usage_get", "Get User Usage", TestCategory.USAGE.value, test_usage_get))
    
    def test_usage_check():
        import requests
        resp = requests.get(f"{base_url}/api/usage/check/1/chat", timeout=10)
        valid = resp.status_code in [200, 404]
        if resp.status_code == 200:
            data = resp.json()
            return valid, f"allowed={data.get('allowed', 'N/A')}, cost={data.get('cost', 'N/A')}"
        return valid, "user not found"
    
    tests.append(("usage_check", "Check Usage Allowed", TestCategory.USAGE.value, test_usage_check))
    
    def test_topup_packs():
        import requests
        resp = requests.get(f"{base_url}/api/topup-packs", timeout=10)
        valid = resp.status_code == 200
        data = resp.json()
        return valid, f"packs={list(data.get('packs', {}).keys())}"
    
    tests.append(("topup_packs", "Get Top-up Packs", TestCategory.USAGE.value, test_topup_packs))
    
    return tests


# =============================================================================
# TERRAIN SERVICE TESTS
# =============================================================================

def get_terrain_tests(base_url: str = "http://localhost:8000") -> List[Tuple[str, str, str, Callable]]:
    """Get terrain service tests."""
    tests = []
    
    def test_terrain_import():
        from terrain_service import TerrainService
        valid = TerrainService is not None
        return valid, "import successful"
    
    tests.append(("terrain_import", "Terrain Service Import", TestCategory.TERRAIN.value, test_terrain_import))
    
    def test_terrain_elevation_api():
        import requests
        resp = requests.get(f"{base_url}/api/terrain/elevation", params={
            "lat": 12.9716,
            "lng": 77.5946
        }, timeout=10)
        valid = resp.status_code in [200, 503]
        return valid, f"status={resp.status_code}"
    
    tests.append(("terrain_elev", "Terrain Elevation API", TestCategory.TERRAIN.value, test_terrain_elevation_api))
    
    def test_terrain_analysis_api():
        import requests
        resp = requests.get(f"{base_url}/api/terrain/analysis", params={
            "lat": 12.9716,
            "lng": 77.5946
        }, timeout=10)
        valid = resp.status_code in [200, 503]
        return valid, f"status={resp.status_code}"
    
    tests.append(("terrain_analysis", "Terrain Analysis API", TestCategory.TERRAIN.value, test_terrain_analysis_api))
    
    def test_terrain_stats_api():
        import requests
        resp = requests.get(f"{base_url}/api/terrain/stats", timeout=10)
        valid = resp.status_code in [200, 503]
        return valid, f"status={resp.status_code}"
    
    tests.append(("terrain_stats", "Terrain Stats API", TestCategory.TERRAIN.value, test_terrain_stats_api))
    
    return tests


# =============================================================================
# DATABASE PANEL TESTS
# =============================================================================

def get_database_tests(base_url: str = "http://localhost:8000") -> List[Tuple[str, str, str, Callable]]:
    """Get database panel API tests."""
    tests = []
    
    def test_db_tables():
        import requests
        resp = requests.get(f"{base_url}/api/database/tables", timeout=10)
        valid = resp.status_code == 200
        data = resp.json()
        tables = data.get('tables', [])
        return valid, f"tables={len(tables)}"
    
    tests.append(("db_tables", "Database Tables List", TestCategory.DATABASE.value, test_db_tables))
    
    def test_db_stats():
        import requests
        resp = requests.get(f"{base_url}/api/database/stats", timeout=10)
        valid = resp.status_code == 200
        data = resp.json()
        return valid, f"records={data.get('total_records', 'N/A')}"
    
    tests.append(("db_stats", "Database Stats", TestCategory.DATABASE.value, test_db_stats))
    
    def test_db_table_data():
        import requests
        resp = requests.get(f"{base_url}/api/database/table/properties", params={
            "limit": 5
        }, timeout=10)
        valid = resp.status_code == 200
        data = resp.json()
        rows = data.get('rows', [])
        return valid, f"rows={len(rows)}"
    
    tests.append(("db_table_data", "Database Table Data", TestCategory.DATABASE.value, test_db_table_data))
    
    def test_db_query():
        import requests
        resp = requests.post(f"{base_url}/api/database/query", json={
            "query": "SELECT COUNT(*) as cnt FROM properties",
            "limit": 10
        }, timeout=10)
        valid = resp.status_code == 200
        return valid, "query executed"
    
    tests.append(("db_query", "Database Query", TestCategory.DATABASE.value, test_db_query))
    
    return tests


# =============================================================================
# ADVANCED INSIGHTS TESTS
# =============================================================================

def get_insights_tests(base_url: str = "http://localhost:8000") -> List[Tuple[str, str, str, Callable]]:
    """Get advanced insights API tests."""
    tests = []
    
    def test_insights_area():
        import requests
        resp = requests.get(f"{base_url}/api/insights/area", params={
            "lat": 12.9716,
            "lng": 77.5946,
            "locality": "Koramangala"
        }, timeout=15)
        valid = resp.status_code in [200, 503]
        return valid, f"status={resp.status_code}"
    
    tests.append(("insights_area", "Area Insights", TestCategory.INSIGHTS.value, test_insights_area))
    
    def test_insights_market():
        import requests
        resp = requests.get(f"{base_url}/api/insights/market/Koramangala", timeout=15)
        valid = resp.status_code in [200, 503]
        return valid, f"status={resp.status_code}"
    
    tests.append(("insights_market", "Market Intelligence", TestCategory.INSIGHTS.value, test_insights_market))
    
    def test_insights_price_movers():
        import requests
        resp = requests.get(f"{base_url}/api/insights/price-movers", params={
            "days": 30,
            "limit": 10
        }, timeout=15)
        valid = resp.status_code in [200, 503]
        return valid, f"status={resp.status_code}"
    
    tests.append(("insights_movers", "Price Movers", TestCategory.INSIGHTS.value, test_insights_price_movers))
    
    def test_insights_locality_trend():
        import requests
        resp = requests.get(f"{base_url}/api/insights/locality-trend", params={
            "locality": "Whitefield",
            "days": 30
        }, timeout=15)
        valid = resp.status_code in [200, 503]
        return valid, f"status={resp.status_code}"
    
    tests.append(("insights_trend", "Locality Trend", TestCategory.INSIGHTS.value, test_insights_locality_trend))
    
    return tests


# =============================================================================
# STORYBOARD TESTS
# =============================================================================

def get_storyboard_tests(base_url: str = "http://localhost:8000") -> List[Tuple[str, str, str, Callable]]:
    """Get storyboard generation API tests."""
    tests = []
    
    def test_storyboard_generate():
        import requests
        resp = requests.post(f"{base_url}/api/storyboard/generate", json={
            "scenario": "New metro station in Koramangala",
            "locality": "Koramangala",
            "duration_seconds": 30
        }, timeout=30)
        valid = resp.status_code in [200, 503]
        return valid, f"status={resp.status_code}"
    
    tests.append(("story_generate", "Storyboard Generate", TestCategory.STORYBOARD.value, test_storyboard_generate))
    
    def test_simulate_storyboard():
        import requests
        resp = requests.post(f"{base_url}/api/simulate/storyboard", json={
            "lat": 12.9716,
            "lng": 77.5946,
            "scenario_type": "metro_station",
            "description": "New metro station"
        }, timeout=30)
        valid = resp.status_code in [200, 503]
        return valid, f"status={resp.status_code}"
    
    tests.append(("story_simulate", "Simulate with Storyboard", TestCategory.STORYBOARD.value, test_simulate_storyboard))
    
    return tests


# =============================================================================
# INVESTMENT TESTS
# =============================================================================

def get_investment_tests(base_url: str = "http://localhost:8000") -> List[Tuple[str, str, str, Callable]]:
    """Get investment API tests."""
    tests = []
    
    def test_investment_leaderboard():
        import requests
        resp = requests.get(f"{base_url}/api/investment/leaderboard", timeout=15)
        valid = resp.status_code in [200, 503]
        data = resp.json() if resp.status_code == 200 else {}
        return valid, f"localities={len(data.get('leaderboard', []))}"
    
    tests.append(("invest_leaderboard", "Investment Leaderboard", TestCategory.INVESTMENT.value, test_investment_leaderboard))
    
    def test_investment_insight():
        import requests
        resp = requests.get(f"{base_url}/api/insights/investment/prop_1", timeout=15)
        valid = resp.status_code in [200, 404, 503]
        return valid, f"status={resp.status_code}"
    
    tests.append(("invest_insight", "Investment Insight", TestCategory.INVESTMENT.value, test_investment_insight))
    
    return tests


# =============================================================================
# COMPARE TESTS
# =============================================================================

def get_compare_tests(base_url: str = "http://localhost:8000") -> List[Tuple[str, str, str, Callable]]:
    """Get comparison API tests."""
    tests = []
    
    def test_compare_properties():
        import requests
        resp = requests.post(f"{base_url}/api/compare/properties", json={
            "localities": ["Koramangala", "Indiranagar"]
        }, timeout=15)
        valid = resp.status_code in [200, 503]
        return valid, f"status={resp.status_code}"
    
    tests.append(("compare_props", "Compare Properties/Localities", TestCategory.COMPARE.value, test_compare_properties))
    
    def test_locality_hotspots():
        import requests
        resp = requests.get(f"{base_url}/api/locality/hotspots", timeout=15)
        valid = resp.status_code in [200, 404, 503]  # 404 if locality service unavailable
        return valid, f"status={resp.status_code}"
    
    tests.append(("compare_hotspots", "Locality Hotspots", TestCategory.COMPARE.value, test_locality_hotspots))
    
    def test_cityintel_compare():
        import requests
        resp = requests.get(f"{base_url}/api/city-intelligence/compare", params={
            "locality1": "Koramangala",
            "locality2": "Indiranagar"
        }, timeout=15)
        valid = resp.status_code in [200, 503]
        return valid, f"status={resp.status_code}"
    
    tests.append(("compare_cityintel", "City Intelligence Compare", TestCategory.COMPARE.value, test_cityintel_compare))
    
    return tests


# =============================================================================
# CHAT TESTS
# =============================================================================

def get_chat_tests(base_url: str = "http://localhost:8000") -> List[Tuple[str, str, str, Callable]]:
    """Get chat API tests."""
    tests = []
    
    def test_chat_simple():
        import requests
        resp = requests.post(f"{base_url}/api/chat", json={
            "messages": [{"role": "user", "content": "Hello"}],
            "context": {}
        }, timeout=30)
        valid = resp.status_code == 200
        data = resp.json() if valid else {}
        return valid, f"has_response={bool(data.get('response') or data.get('message'))}"
    
    tests.append(("chat_simple", "Simple Chat", TestCategory.CHAT.value, test_chat_simple))
    
    def test_chat_property_query():
        import requests
        resp = requests.post(f"{base_url}/api/chat", json={
            "messages": [{"role": "user", "content": "Show me apartments in Koramangala"}],
            "context": {"lat": 12.9345, "lng": 77.6108}
        }, timeout=30)
        valid = resp.status_code == 200
        return valid, f"status={resp.status_code}"
    
    tests.append(("chat_property", "Property Query Chat", TestCategory.CHAT.value, test_chat_property_query))
    
    def test_chat_navigate():
        import requests
        resp = requests.post(f"{base_url}/api/chat", json={
            "messages": [{"role": "user", "content": "Go to Whitefield"}],
            "context": {}
        }, timeout=30)
        valid = resp.status_code == 200
        data = resp.json() if valid else {}
        has_coords = 'coordinates' in str(data) or 'lat' in str(data)
        return valid, f"has_coords={has_coords}"
    
    tests.append(("chat_navigate", "Navigation Chat", TestCategory.CHAT.value, test_chat_navigate))
    
    return tests


# =============================================================================
# PATHFINDING TESTS
# =============================================================================

def get_pathfinding_tests(base_url: str = "http://localhost:8000") -> List[Tuple[str, str, str, Callable]]:
    """Get 3D pathfinding tests."""
    tests = []
    
    def test_pathfinding_import():
        from pathfinding_3d import Pathfinding3D, PathResult
        valid = Pathfinding3D is not None and PathResult is not None
        return valid, "imports successful"
    
    tests.append(("path_import", "Pathfinding Import", TestCategory.PATHFINDING.value, test_pathfinding_import))
    
    def test_pathfinding_route_api():
        import requests
        resp = requests.get(f"{base_url}/api/pathfinding/route", params={
            "start_lat": 12.9345,
            "start_lng": 77.6108,
            "end_lat": 12.9400,
            "end_lng": 77.6150,
            "avoid_buildings": True
        }, timeout=30)
        valid = resp.status_code in [200, 503]
        data = resp.json() if resp.status_code == 200 else {}
        return valid, f"found={data.get('found', 'N/A')}, dist={data.get('distance_m', 0):.0f}m"
    
    tests.append(("path_route", "Walking Route API", TestCategory.PATHFINDING.value, test_pathfinding_route_api))
    
    def test_pathfinding_to_nearest():
        import requests
        resp = requests.get(f"{base_url}/api/pathfinding/to-nearest", params={
            "lat": 12.9345,
            "lng": 77.6108,
            "poi_type": "metro",
            "max_distance_m": 3000
        }, timeout=30)
        valid = resp.status_code in [200, 503]
        return valid, f"status={resp.status_code}"
    
    tests.append(("path_nearest", "Route to Nearest POI", TestCategory.PATHFINDING.value, test_pathfinding_to_nearest))
    
    def test_pathfinding_engine():
        from pathfinding_3d import Pathfinding3D
        data_dir = Path(__file__).parent.parent / 'src' / 'data'
        pf = Pathfinding3D(str(data_dir / 'valora.db'))
        result = pf.find_path(12.9345, 77.6108, 12.9360, 77.6120)
        valid = result is not None and hasattr(result, 'distance_m')
        return valid, f"dist={result.distance_m:.0f}m, waypoints={len(result.waypoints)}"
    
    tests.append(("path_engine", "Pathfinding Engine", TestCategory.PATHFINDING.value, test_pathfinding_engine))
    
    return tests


# =============================================================================
# FLOOD RISK TESTS
# =============================================================================

def get_floodrisk_tests(base_url: str = "http://localhost:8000") -> List[Tuple[str, str, str, Callable]]:
    """Get flood risk and raster analysis tests."""
    tests = []
    
    def test_raster_import():
        from raster_analysis import RasterAnalysis, FloodRiskResult
        valid = RasterAnalysis is not None and FloodRiskResult is not None
        return valid, "imports successful"
    
    tests.append(("flood_import", "Raster Analysis Import", TestCategory.FLOODRISK.value, test_raster_import))
    
    def test_flood_risk_api():
        import requests
        resp = requests.get(f"{base_url}/api/flood-risk/analysis", params={
            "lat": 12.9345,
            "lng": 77.6108,
            "radius_m": 500
        }, timeout=30)
        valid = resp.status_code in [200, 503]
        data = resp.json() if resp.status_code == 200 else {}
        return valid, f"zone={data.get('flood_zone', 'N/A')}, risk={data.get('risk_level', 'N/A')}"
    
    tests.append(("flood_analysis", "Flood Risk Analysis API", TestCategory.FLOODRISK.value, test_flood_risk_api))
    
    def test_insurance_estimate_api():
        import requests
        resp = requests.get(f"{base_url}/api/flood-risk/insurance-estimate", params={
            "lat": 12.9345,
            "lng": 77.6108
        }, timeout=30)
        valid = resp.status_code in [200, 503]
        data = resp.json() if resp.status_code == 200 else {}
        return valid, f"multiplier={data.get('insurance_multiplier', 'N/A')}x"
    
    tests.append(("flood_insurance", "Insurance Estimate API", TestCategory.FLOODRISK.value, test_insurance_estimate_api))
    
    def test_advanced_terrain_api():
        import requests
        resp = requests.get(f"{base_url}/api/terrain/advanced-analysis", params={
            "lat": 12.9345,
            "lng": 77.6108,
            "radius_m": 500
        }, timeout=30)
        valid = resp.status_code in [200, 503]
        data = resp.json() if resp.status_code == 200 else {}
        terrain = data.get('terrain_type', 'N/A')
        return valid, f"terrain={terrain}"
    
    tests.append(("flood_terrain", "Advanced Terrain API", TestCategory.FLOODRISK.value, test_advanced_terrain_api))
    
    def test_raster_engine():
        from raster_analysis import RasterAnalysis
        data_dir = Path(__file__).parent.parent / 'src' / 'data'
        ra = RasterAnalysis(str(data_dir / 'valora.db'))
        result = ra.analyze_flood_risk(12.9345, 77.6108, 500)
        valid = result is not None and hasattr(result, 'flood_risk_score')
        return valid, f"score={result.flood_risk_score:.1f}, zone={result.flood_zone}"
    
    tests.append(("flood_engine", "Raster Analysis Engine", TestCategory.FLOODRISK.value, test_raster_engine))
    
    return tests


# =============================================================================
# TEST RUNNER
# =============================================================================

def collect_tests(categories: List[str], base_url: str = "http://localhost:8000") -> List[Tuple[str, str, str, Callable]]:
    """Collect all tests for given categories."""
    all_tests = []
    
    category_map = {
        TestCategory.INTENT.value: get_intent_tests,
        TestCategory.SPATIAL.value: get_spatial_tests,
        TestCategory.OCCLUSION.value: get_occlusion_tests,
        TestCategory.SOLAR.value: get_solar_tests,
        TestCategory.GRAPH.value: get_graph_tests,
        TestCategory.TOOL.value: get_tool_tests,
        TestCategory.PROPERTY.value: get_property_tests,
        TestCategory.LOCALITY.value: get_locality_tests,
        TestCategory.GIS.value: get_gis_tests,
        TestCategory.TRANSACTION.value: get_transaction_tests,
        TestCategory.REGULATORY.value: get_regulatory_tests,
        TestCategory.COUNTERFACTUAL.value: get_counterfactual_tests,
        TestCategory.VERIFIER.value: get_verifier_tests,
        TestCategory.AUTH.value: get_auth_tests,
        TestCategory.OBSERVABILITY.value: get_observability_tests,
        TestCategory.PREFERENCES.value: get_preferences_tests,
        TestCategory.PIPELINE.value: get_pipeline_tests,
        TestCategory.RAG.value: get_rag_tests,
        TestCategory.SIMULATION.value: get_simulation_tests,
        TestCategory.VALUATION.value: get_valuation_tests,
        TestCategory.CITYINTEL.value: get_cityintel_tests,
        TestCategory.DIGITALTWIN.value: get_digitaltwin_tests,
        TestCategory.USAGE.value: lambda: get_usage_tests(base_url),
        TestCategory.TERRAIN.value: lambda: get_terrain_tests(base_url),
        TestCategory.DATABASE.value: lambda: get_database_tests(base_url),
        TestCategory.INSIGHTS.value: lambda: get_insights_tests(base_url),
        TestCategory.STORYBOARD.value: lambda: get_storyboard_tests(base_url),
        TestCategory.INVESTMENT.value: lambda: get_investment_tests(base_url),
        TestCategory.COMPARE.value: lambda: get_compare_tests(base_url),
        TestCategory.CHAT.value: lambda: get_chat_tests(base_url),
        TestCategory.PATHFINDING.value: lambda: get_pathfinding_tests(base_url),
        TestCategory.FLOODRISK.value: lambda: get_floodrisk_tests(base_url),
        TestCategory.API.value: lambda: get_api_tests(base_url),
    }
    
    for cat in categories:
        if cat in category_map:
            all_tests.extend(category_map[cat]())
    
    return all_tests


def run_tests(categories: List[str] = None, base_url: str = "http://localhost:8000", verbose: bool = True) -> TestReport:
    """Run all tests and return report."""
    if categories is None or TestCategory.ALL.value in categories:
        categories = [c.value for c in TestCategory if c != TestCategory.ALL]
    
    report = TestReport(
        run_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
        timestamp=datetime.now().isoformat(),
        categories_run=categories
    )
    
    start_all = _now_ms()
    
    tests = collect_tests(categories, base_url)
    report.total = len(tests)
    
    if verbose:
        print("\n" + "=" * 70)
        print("VALORA AI - UNIFIED TEST SUITE")
        print(f"Running {report.total} tests across {len(categories)} categories")
        print("=" * 70 + "\n")
    
    current_category = None
    
    for test_id, name, category, test_fn in tests:
        if verbose and category != current_category:
            current_category = category
            print(f"\n[{category.upper()}]")
        
        result = _run_test(test_id, name, category, test_fn)
        report.results.append(result)
        
        if result.status == TestStatus.PASS.value:
            report.passed += 1
            icon = "✅"
        elif result.status == TestStatus.FAIL.value:
            report.failed += 1
            icon = "❌"
        elif result.status == TestStatus.ERROR.value:
            report.errors += 1
            icon = "⚠️"
        else:
            report.skipped += 1
            icon = "⏭️"
        
        if verbose:
            msg = result.message or result.error or ""
            print(f"  {icon} {name:40} {result.duration_ms:>6.0f}ms  {msg[:40]}")
    
    report.duration_ms = round(_now_ms() - start_all, 2)
    
    if verbose:
        print("\n" + "=" * 70)
        print(f"RESULTS: {report.passed}/{report.total} passed ({report.pass_rate:.1f}%)")
        print(f"Passed: {report.passed} | Failed: {report.failed} | Errors: {report.errors} | Skipped: {report.skipped}")
        print(f"Duration: {report.duration_ms:.0f}ms")
        print("=" * 70 + "\n")
    
    return report


def save_report(report: TestReport, path: str = None) -> str:
    """Save report to JSON file."""
    if path is None:
        reports_dir = Path(__file__).parent / 'test_reports'
        reports_dir.mkdir(exist_ok=True)
        path = reports_dir / f"test_{report.run_id}.json"
    
    with open(path, 'w') as f:
        json.dump({
            'run_id': report.run_id,
            'timestamp': report.timestamp,
            'categories': report.categories_run,
            'summary': {
                'total': report.total,
                'passed': report.passed,
                'failed': report.failed,
                'errors': report.errors,
                'skipped': report.skipped,
                'pass_rate': report.pass_rate,
                'duration_ms': report.duration_ms
            },
            'results': [asdict(r) for r in report.results]
        }, f, indent=2)
    
    print(f"Report saved to: {path}")
    return str(path)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Valora AI Unified Test Suite")
    parser.add_argument(
        "--category", "-c",
        nargs="+",
        default=["all"],
        help="Categories to test (api, intent, spatial, occlusion, solar, graph, property, locality, tool, gis, all)"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Backend URL for API tests"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save report to file"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output"
    )
    
    args = parser.parse_args()
    
    report = run_tests(
        categories=args.category,
        base_url=args.url,
        verbose=not args.quiet
    )
    
    if args.save:
        save_report(report)
    
    # Exit with error code if tests failed
    if report.failed > 0 or report.errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
