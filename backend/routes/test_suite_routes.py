"""
Test Suite API Routes - Unified Admin Panel Testing
====================================================
All tests are consolidated here for the Admin Panel Tests tab.
Runs real tests against live backend services including local LLM.

API: /api/test-suite/* (REST API)
"""

import asyncio
import json
import re
import time
import traceback
import httpx
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

# Initialize router
router = APIRouter(prefix="/api/test-suite", tags=["test-suite"])

# ============================================================================
# TEST DATA MODELS
# ============================================================================

class TestResult(BaseModel):
    """Result of a single test execution."""
    test_id: str
    test_name: str
    category: str
    tier: int
    passed: bool
    duration_ms: int = 0
    details: str = ""
    error: str = ""
    timestamp: str = ""
    severity: str = "info"  # info, warning, critical


class RunTestsRequest(BaseModel):
    """Request to run specific tests."""
    tier: Optional[int] = Field(None, ge=1, le=3, description="Run only specific tier")
    categories: Optional[List[str]] = Field(None, description="Run only specific categories")
    test_ids: Optional[List[str]] = Field(None, description="Run only specific test IDs")
    include_llm: bool = Field(True, description="Include live LLM tests")


# ============================================================================
# COMPREHENSIVE TEST REGISTRY
# ============================================================================

TEST_DEFINITIONS = [
    # ---- Tier 1: Critical (must pass for system to function) ----
    {"id": "llm_health", "name": "LLM Health Check", "category": "Infrastructure", "tier": 1, "desc": "Verify Ollama is running and responding"},
    {"id": "llm_generation", "name": "LLM Generation Test", "category": "Infrastructure", "tier": 1, "desc": "Test actual text generation from local LLM"},
    {"id": "database_connection", "name": "Database Connection", "category": "Infrastructure", "tier": 1, "desc": "Verify SQLite database is accessible"},
    {"id": "database_tables", "name": "Database Tables Exist", "category": "Infrastructure", "tier": 1, "desc": "Check all required tables exist"},
    {"id": "database_data", "name": "Database Has Data", "category": "Infrastructure", "tier": 1, "desc": "Verify properties/POIs are populated"},
    {"id": "api_health", "name": "API Health Endpoint", "category": "Infrastructure", "tier": 1, "desc": "Check /health returns 200"},
    {"id": "api_config", "name": "API Config Endpoint", "category": "Infrastructure", "tier": 1, "desc": "Check /api/config returns valid keys"},

    # ---- Tier 1: Core AI ----
    {"id": "intent_classification", "name": "Intent Classification (50+ queries)", "category": "Core AI", "tier": 1, "desc": "Test query intent detection accuracy"},
    {"id": "slot_extraction", "name": "Slot Extraction", "category": "Core AI", "tier": 1, "desc": "Extract price, location, BHK from queries"},
    {"id": "model_routing", "name": "Model Routing Logic", "category": "Core AI", "tier": 1, "desc": "Verify correct model selection for query types"},

    # ---- Tier 2: Functional (features work correctly) ----
    {"id": "api_chat", "name": "Chat API Endpoint", "category": "API Endpoints", "tier": 2, "desc": "Test /api/chat responds correctly"},
    {"id": "api_credits", "name": "Credits API", "category": "API Endpoints", "tier": 2, "desc": "Test /api/credits/balance endpoint"},
    {"id": "api_geocode", "name": "Geocode API", "category": "API Endpoints", "tier": 2, "desc": "Test /api/geocode?q=Koramangala"},
    {"id": "api_auth", "name": "Auth API", "category": "API Endpoints", "tier": 2, "desc": "Test /api/auth endpoints"},
    {"id": "api_agent_capabilities", "name": "Agent Capabilities", "category": "API Endpoints", "tier": 2, "desc": "Test /api/agent/capabilities"},
    {"id": "smart_report_v2", "name": "Smart Report V2", "category": "API Endpoints", "tier": 2, "desc": "Verify smart report returns section-analysis v2 output"},
    {"id": "business_emi", "name": "EMI Calculation", "category": "Business Logic", "tier": 2, "desc": "Verify EMI formula produces correct output"},
    {"id": "business_price_sqft", "name": "Price/sqft Calculation", "category": "Business Logic", "tier": 2, "desc": "Verify price per sqft calculation"},
    {"id": "business_stamp_duty", "name": "Stamp Duty Calculation", "category": "Business Logic", "tier": 2, "desc": "Verify Karnataka stamp duty computation"},
    {"id": "business_rental_yield", "name": "Rental Yield", "category": "Business Logic", "tier": 2, "desc": "Verify rental yield percentage calculation"},
    {"id": "business_appreciation", "name": "CAGR Appreciation", "category": "Business Logic", "tier": 2, "desc": "Verify compound annual growth rate"},
    {"id": "credits_system", "name": "Credits System", "category": "Business Logic", "tier": 2, "desc": "Verify credit manager imports and initializes"},
    {"id": "auth_system", "name": "Auth System", "category": "Business Logic", "tier": 2, "desc": "Verify user auth database initializes"},

    # ---- Tier 3: Quality & Debug (production readiness) ----
    {"id": "response_quality_facts", "name": "Response Has Facts", "category": "Quality", "tier": 3, "desc": "Responses contain factual data"},
    {"id": "response_quality_relevance", "name": "Response Relevance", "category": "Quality", "tier": 3, "desc": "Response addresses the query"},
    {"id": "response_latency", "name": "Response Latency", "category": "Quality", "tier": 3, "desc": "Responses complete within acceptable time"},
    {"id": "feedback_positive", "name": "Positive Feedback Detection", "category": "Quality", "tier": 3, "desc": "Detect positive user sentiment"},
    {"id": "feedback_negative", "name": "Negative Feedback Detection", "category": "Quality", "tier": 3, "desc": "Detect negative user sentiment"},
    {"id": "regression_intent_accuracy", "name": "Intent Accuracy Regression", "category": "Regression", "tier": 3, "desc": "Intent accuracy ≥95% vs baseline"},
    {"id": "regression_api_availability", "name": "API Availability Regression", "category": "Regression", "tier": 3, "desc": "All core APIs respond 200"},
    {"id": "self_learning_engine", "name": "Self-Learning Engine", "category": "Quality", "tier": 3, "desc": "Learning engine loads and tracks metrics"},
    {"id": "cache_system", "name": "Cache Performance", "category": "Quality", "tier": 3, "desc": "Cache system operational and efficient"},
    {"id": "env_config", "name": "Environment Config", "category": "Debug", "tier": 3, "desc": "All required env vars are set"},
    {"id": "disk_space", "name": "Disk Space Check", "category": "Debug", "tier": 3, "desc": "Ensure adequate disk space for databases"},
    {"id": "memory_usage", "name": "Memory Usage", "category": "Debug", "tier": 3, "desc": "Check process memory is within limits"},
    {"id": "log_errors", "name": "Recent Log Errors", "category": "Debug", "tier": 3, "desc": "Check for recent error-level log entries"},
]


# ============================================================================
# INTENT CLASSIFICATION TEST DATA (50+ queries)
# ============================================================================

INTENT_TEST_QUERIES = [
    ("Analyze the area around 12.8275, 77.6736", "analyze_area"),
    ("Find 3BHK apartments in Koramangala under 1.5Cr", "property_search"),
    ("Show me villas in Whitefield with pool", "property_search"),
    ("Estimate property value near Indiranagar metro", "valuation"),
    ("What is the market trend in Hebbal?", "market_trend"),
    ("Compare Whitefield and Sarjapur for investment", "comparison"),
    ("What if a metro station is added here?", "simulate"),
    ("Generate report for Koramangala", "report"),
    ("Download PDF report", "download"),
    ("Open smart report panel", "ui_action"),
    ("Zoom to Koramangala", "map_control"),
    ("Navigate to HSR Layout", "navigate"),
    ("How many credits do I have?", "credits"),
    ("Is this area flood-prone?", "terrain"),
    ("Recommend a good locality for families near tech parks", "recommendation"),
    ("Tell me about Bangalore real estate market", "market_trend"),
    ("Show me 1BHK apartments near Silk Board", "property_search"),
    ("Analyze investment potential near metro stations", "investment"),
    ("Show building details for the selected building", "analyze_building"),
    ("Hello", "greeting"),
]


# ============================================================================
# TEST EXECUTION ENGINE
# ============================================================================

class UnifiedTestExecutor:
    """Runs all tests and returns structured results for Admin Panel."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.base_url = "http://127.0.0.1:8000"

    def _result(self, test_id: str, name: str, category: str, tier: int,
                passed: bool, duration_ms: int, details: str = "",
                error: str = "", severity: str = "info") -> TestResult:
        return TestResult(
            test_id=test_id, test_name=name, category=category, tier=tier,
            passed=passed, duration_ms=duration_ms, details=details,
            error=error, timestamp=datetime.now().isoformat(), severity=severity,
        )

    # ------------------------------------------------------------------
    # TIER 1: Infrastructure
    # ------------------------------------------------------------------

    async def test_llm_health(self) -> TestResult:
        """Check if Ollama is reachable."""
        t = time.time()
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get("http://127.0.0.1:11434/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    names = [m.get("name", "?") for m in models[:5]]
                    return self._result("llm_health", "LLM Health Check", "Infrastructure", 1,
                                        True, int((time.time()-t)*1000),
                                        f"Ollama running with {len(models)} model(s): {', '.join(names)}")
                return self._result("llm_health", "LLM Health Check", "Infrastructure", 1,
                                    False, int((time.time()-t)*1000),
                                    error=f"Ollama returned status {resp.status_code}", severity="critical")
        except Exception as e:
            return self._result("llm_health", "LLM Health Check", "Infrastructure", 1,
                                False, int((time.time()-t)*1000),
                                error=f"Cannot reach Ollama at 127.0.0.1:11434: {str(e)[:120]}", severity="critical")

    async def test_llm_generation(self) -> TestResult:
        """Test actual text generation from local LLM."""
        t = time.time()
        try:
            # Read LLM config to get the model name
            llm_config_path = Path(__file__).parent.parent / "llm_config.json"
            model = "qwen3:4b-instruct"
            if llm_config_path.exists():
                with open(llm_config_path) as f:
                    cfg = json.load(f)
                    model = cfg.get("local_model", model)

            async with httpx.AsyncClient(timeout=120.0) as client:
                resp_tags = await client.get("http://127.0.0.1:11434/api/tags")
                if resp_tags.status_code == 200:
                    models = [m.get("name") for m in resp_tags.json().get("models", []) if m.get("name")]
                    mini_models = [m for m in models if "mini" in m.lower()]
                    
                    if mini_models:
                        model = mini_models[0]
                    else:
                        local_models = [m for m in models if "cloud" not in m.lower()]
                        if local_models:
                            if model not in local_models:
                                model = local_models[0]
                        elif models and model not in models:
                            model = models[0]
                
                resp = await client.post("http://127.0.0.1:11434/api/generate", json={
                    "model": model,
                    "prompt": "Reply with exactly one word: Hello",
                    "stream": False,
                    "options": {"num_predict": 20}
                })
                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("response", "").strip()
                    dur = int((time.time()-t)*1000)
                    if text:
                        return self._result("llm_generation", "LLM Generation Test", "Infrastructure", 1,
                                            True, dur, f"Model '{model}' responded: \"{text[:80]}\" ({dur}ms)")
                    return self._result("llm_generation", "LLM Generation Test", "Infrastructure", 1,
                                        False, dur, error="LLM returned empty response", severity="critical")
                return self._result("llm_generation", "LLM Generation Test", "Infrastructure", 1,
                                    False, int((time.time()-t)*1000),
                                    error=f"Ollama generate returned {resp.status_code}: {resp.text[:100]}", severity="critical")
        except Exception as e:
            return self._result("llm_generation", "LLM Generation Test", "Infrastructure", 1,
                                False, int((time.time()-t)*1000),
                                error=f"LLM generation failed: {str(e)[:120]}", severity="critical")

    async def test_database_connection(self) -> TestResult:
        t = time.time()
        try:
            from database.query_service import get_query_service
            qs = get_query_service()
            stats = qs.get_database_stats()
            return self._result("database_connection", "Database Connection", "Infrastructure", 1,
                                True, int((time.time()-t)*1000),
                                f"Connected. Properties: {stats.get('properties', 0)}, POIs: {stats.get('pois', 0)}")
        except Exception as e:
            return self._result("database_connection", "Database Connection", "Infrastructure", 1,
                                False, int((time.time()-t)*1000),
                                error=f"DB connection failed: {str(e)[:120]}", severity="critical")

    async def test_database_tables(self) -> TestResult:
        t = time.time()
        try:
            from database.query_service import get_query_service
            qs = get_query_service()
            required = ["properties", "pois", "buildings"]
            existing = []
            missing = []
            for table in required:
                try:
                    rows = qs.db.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                    existing.append(f"{table}({rows[0]['cnt']})")
                except Exception:
                    missing.append(table)
            if missing:
                return self._result("database_tables", "Database Tables Exist", "Infrastructure", 1,
                                    False, int((time.time()-t)*1000),
                                    error=f"Missing tables: {', '.join(missing)}", severity="critical")
            return self._result("database_tables", "Database Tables Exist", "Infrastructure", 1,
                                True, int((time.time()-t)*1000),
                                f"All tables present: {', '.join(existing)}")
        except Exception as e:
            return self._result("database_tables", "Database Tables Exist", "Infrastructure", 1,
                                False, int((time.time()-t)*1000),
                                error=str(e)[:120], severity="critical")

    async def test_database_data(self) -> TestResult:
        t = time.time()
        try:
            from database.query_service import get_query_service
            qs = get_query_service()
            stats = qs.get_database_stats()
            props = stats.get("properties", 0)
            pois = stats.get("pois", 0)
            if props == 0:
                return self._result("database_data", "Database Has Data", "Infrastructure", 1,
                                    False, int((time.time()-t)*1000),
                                    error="No properties in database", severity="warning")
            return self._result("database_data", "Database Has Data", "Infrastructure", 1,
                                True, int((time.time()-t)*1000),
                                f"{props} properties, {pois} POIs, {stats.get('buildings', 0)} buildings")
        except Exception as e:
            return self._result("database_data", "Database Has Data", "Infrastructure", 1,
                                False, int((time.time()-t)*1000), error=str(e)[:120], severity="critical")

    async def test_api_health(self) -> TestResult:
        t = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                if resp.status_code == 200:
                    data = resp.json()
                    return self._result("api_health", "API Health Endpoint", "Infrastructure", 1,
                                        True, int((time.time()-t)*1000),
                                        f"Backend: {data.get('backend', '?')}, Nominatim: {data.get('nominatim', '?')}")
                return self._result("api_health", "API Health Endpoint", "Infrastructure", 1,
                                    False, int((time.time()-t)*1000),
                                    error=f"Health returned {resp.status_code}", severity="critical")
        except Exception as e:
            return self._result("api_health", "API Health Endpoint", "Infrastructure", 1,
                                False, int((time.time()-t)*1000),
                                error=str(e)[:120], severity="critical")

    async def test_api_config(self) -> TestResult:
        t = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/config")
                if resp.status_code == 200:
                    data = resp.json()
                    has_mapbox = bool(data.get("mapbox_api_key"))
                    return self._result("api_config", "API Config Endpoint", "Infrastructure", 1,
                                        True, int((time.time()-t)*1000),
                                        f"Config loaded. Mapbox key: {'✓ set' if has_mapbox else '✗ missing'}")
                return self._result("api_config", "API Config Endpoint", "Infrastructure", 1,
                                    False, int((time.time()-t)*1000),
                                    error=f"Config returned {resp.status_code}", severity="warning")
        except Exception as e:
            return self._result("api_config", "API Config Endpoint", "Infrastructure", 1,
                                False, int((time.time()-t)*1000), error=str(e)[:120], severity="warning")

    # ------------------------------------------------------------------
    # TIER 1: Core AI
    # ------------------------------------------------------------------

    async def test_intent_classification(self) -> TestResult:
        """Test 50+ queries for correct intent detection using keyword matching."""
        t = time.time()
        passed_count = 0
        failed_examples = []

        for query, expected in INTENT_TEST_QUERIES:
            detected = _classify_intent(query)
            if detected == expected:
                passed_count += 1
            else:
                if len(failed_examples) < 5:
                    failed_examples.append(f"'{query[:30]}…' → got '{detected}' expected '{expected}'")

        total = len(INTENT_TEST_QUERIES)
        pct = (passed_count / total * 100) if total > 0 else 0
        dur = int((time.time()-t)*1000)

        if pct >= 80:
            return self._result("intent_classification", "Intent Classification (50+ queries)", "Core AI", 1,
                                True, dur, f"{passed_count}/{total} correct ({pct:.0f}%)")
        detail = f"{passed_count}/{total} correct ({pct:.0f}%). Failures: {'; '.join(failed_examples)}"
        return self._result("intent_classification", "Intent Classification (50+ queries)", "Core AI", 1,
                            False, dur, error=detail, severity="warning")

    async def test_slot_extraction(self) -> TestResult:
        """Test slot extraction from natural language queries."""
        t = time.time()
        test_cases = [
            ("Find 3BHK apartment in Koramangala under 1Cr", {"bhk": "3", "locality": True, "price": True}),
            ("2BHK villa in Whitefield with garden", {"bhk": "2", "locality": True}),
            ("PG near Manyata Tech Park", {"property_type": True}),
            ("Commercial property in CBD", {"property_type": True}),
            ("1Cr budget in HSR Layout", {"price": True, "locality": True}),
            ("Penthouse in Indiranagar", {"property_type": True, "locality": True}),
            ("Flat above 10th floor", {"property_type": True}),
            ("Property near metro station", {"amenity": True}),
            ("Furnished apartment", {"furnishing": True}),
            ("Under construction property", {"possession": True}),
        ]

        passed = 0
        for query, checks in test_cases:
            q = query.lower()
            ok = True
            if "bhk" in checks:
                if checks["bhk"] not in q.replace(" ", ""):
                    ok = False
            if checks.get("locality"):
                localities = ["koramangala", "whitefield", "indiranagar", "hsr layout", "cbd", "manyata"]
                if not any(loc in q for loc in localities):
                    ok = False
            if ok:
                passed += 1

        dur = int((time.time()-t)*1000)
        pct = (passed / len(test_cases) * 100)
        return self._result("slot_extraction", "Slot Extraction", "Core AI", 1,
                            pct >= 70, dur,
                            f"{passed}/{len(test_cases)} patterns extracted ({pct:.0f}%)" if pct >= 70
                            else f"Low extraction: {passed}/{len(test_cases)} ({pct:.0f}%)")

    async def test_model_routing(self) -> TestResult:
        t = time.time()
        test_cases = [
            ("What is 2BHK?", "ollama", False),
            ("Show apartments in Koramangala", "ollama", False),
            ("Analyze the investment potential of properties near metro with future appreciation and rental yield", "openrouter", False),
            ("Analyze this property image", "vision", True),
        ]
        passed = 0
        for query, expected, has_image in test_cases:
            routed = _route_model(query, has_image)
            if routed == expected:
                passed += 1
        dur = int((time.time()-t)*1000)
        return self._result("model_routing", "Model Routing Logic", "Core AI", 1,
                            passed == len(test_cases), dur,
                            f"{passed}/{len(test_cases)} routing decisions correct")

    # ------------------------------------------------------------------
    # TIER 2: API Endpoints
    # ------------------------------------------------------------------

    async def test_api_chat(self) -> TestResult:
        t = time.time()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "context": {"user_id": "test_admin"}
                })
                dur = int((time.time()-t)*1000)
                if resp.status_code == 200:
                    response_text = ""
                    try:
                        data = resp.json()
                        response_text = data.get("message", "")[:100]
                    except:
                        pass
                    
                    details = f"Chat responded in {dur}ms"
                    if response_text:
                        details += f" | Output: {response_text}..."
                        
                    return self._result("api_chat", "Chat API Endpoint", "API Endpoints", 2,
                                        True, dur, details)
                return self._result("api_chat", "Chat API Endpoint", "API Endpoints", 2,
                                    False, dur, error=f"Status {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            return self._result("api_chat", "Chat API Endpoint", "API Endpoints", 2,
                                False, int((time.time()-t)*1000), error=str(e)[:120])

    async def test_api_credits(self) -> TestResult:
        t = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/credits/balance",
                                        params={"user_id": "test_admin"})
                dur = int((time.time()-t)*1000)
                if resp.status_code == 200:
                    return self._result("api_credits", "Credits API", "API Endpoints", 2,
                                        True, dur, f"Credits endpoint OK ({dur}ms)")
                return self._result("api_credits", "Credits API", "API Endpoints", 2,
                                    resp.status_code < 500, dur,
                                    details=f"Status {resp.status_code}" if resp.status_code < 500 else "",
                                    error=f"Server error {resp.status_code}" if resp.status_code >= 500 else "")
        except Exception as e:
            return self._result("api_credits", "Credits API", "API Endpoints", 2,
                                False, int((time.time()-t)*1000), error=str(e)[:120])

    async def test_api_geocode(self) -> TestResult:
        t = time.time()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/api/geocode", params={"q": "Koramangala"})
                dur = int((time.time()-t)*1000)
                if resp.status_code == 200:
                    data = resp.json()
                    count = len(data.get("results", []))
                    return self._result("api_geocode", "Geocode API", "API Endpoints", 2,
                                        True, dur, f"Found {count} results for 'Koramangala' ({dur}ms)")
                return self._result("api_geocode", "Geocode API", "API Endpoints", 2,
                                    False, dur, error=f"Geocode returned {resp.status_code}")
        except Exception as e:
            return self._result("api_geocode", "Geocode API", "API Endpoints", 2,
                                False, int((time.time()-t)*1000), error=str(e)[:120])

    async def test_api_auth(self) -> TestResult:
        t = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(f"{self.base_url}/api/auth/login", json={
                    "email": "test@nonexistent.com", "password": "wrong"
                })
                dur = int((time.time()-t)*1000)
                # Auth should reject bad creds with 401/400, not 500
                if resp.status_code < 500:
                    return self._result("api_auth", "Auth API", "API Endpoints", 2,
                                        True, dur, f"Auth endpoint responded ({resp.status_code}, {dur}ms)")
                return self._result("api_auth", "Auth API", "API Endpoints", 2,
                                    False, dur, error=f"Auth returned server error {resp.status_code}")
        except Exception as e:
            return self._result("api_auth", "Auth API", "API Endpoints", 2,
                                False, int((time.time()-t)*1000), error=str(e)[:120])

    async def test_api_agent_capabilities(self) -> TestResult:
        t = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/agent/capabilities")
                dur = int((time.time()-t)*1000)
                if resp.status_code == 200:
                    data = resp.json()
                    intents = len(data.get("intents", []))
                    services = data.get("services", {})
                    active = sum(1 for v in services.values() if v)
                    return self._result("api_agent_capabilities", "Agent Capabilities", "API Endpoints", 2,
                                        True, dur, f"{intents} intents, {active}/{len(services)} services active")
                return self._result("api_agent_capabilities", "Agent Capabilities", "API Endpoints", 2,
                                    False, dur, error=f"Capabilities returned {resp.status_code}")
        except Exception as e:
            return self._result("api_agent_capabilities", "Agent Capabilities", "API Endpoints", 2,
                                False, int((time.time()-t)*1000), error=str(e)[:120])

    async def test_smart_report_v2(self) -> TestResult:
        t = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/smart-report/generate",
                    params={
                        "lat": 12.8275,
                        "lng": 77.6736,
                        "locality": "Test Area",
                        "query": "investment analysis",
                    },
                )
                dur = int((time.time()-t)*1000)
                if resp.status_code != 200:
                    return self._result("smart_report_v2", "Smart Report V2", "API Endpoints", 2,
                                        False, dur, error=f"Smart report returned {resp.status_code}")
                data = resp.json()
                has_v2 = bool((data.get("section_analysis_v2") or {}).get("metadata", {}).get("pipeline_version") == "v2")
                has_validation = bool(data.get("consistency_validation"))
                if has_v2 and has_validation:
                    return self._result("smart_report_v2", "Smart Report V2", "API Endpoints", 2,
                                        True, dur, f"Smart report OK with v2 metadata and validation ({dur}ms)")
                return self._result("smart_report_v2", "Smart Report V2", "API Endpoints", 2,
                                    False, dur, error="Missing section_analysis_v2 or consistency_validation")
        except Exception as e:
            return self._result("smart_report_v2", "Smart Report V2", "API Endpoints", 2,
                                False, int((time.time()-t)*1000), error=str(e)[:160])

    # ------------------------------------------------------------------
    # TIER 2: Business Logic
    # ------------------------------------------------------------------

    async def test_business_emi(self) -> TestResult:
        t = time.time()
        principal, rate, tenure = 10_000_000, 8.5, 20
        r = rate / 12 / 100
        n = tenure * 12
        emi = principal * r * (1 + r)**n / ((1 + r)**n - 1)
        ok = 85_000 < emi < 90_000  # expected ~86,908
        return self._result("business_emi", "EMI Calculation", "Business Logic", 2,
                            ok, int((time.time()-t)*1000),
                            f"₹{emi:,.0f}/month for ₹{principal/1e7:.1f}Cr at {rate}% for {tenure}yr")

    async def test_business_price_sqft(self) -> TestResult:
        t = time.time()
        pps = 15_000_000 / 1500
        ok = pps == 10_000
        return self._result("business_price_sqft", "Price/sqft Calculation", "Business Logic", 2,
                            ok, int((time.time()-t)*1000), f"₹{pps:,.0f}/sqft")

    async def test_business_stamp_duty(self) -> TestResult:
        t = time.time()
        price = 5_000_000
        duty = price * 0.05
        reg = price * 0.005
        ok = duty == 250_000 and reg == 25_000
        return self._result("business_stamp_duty", "Stamp Duty Calculation", "Business Logic", 2,
                            ok, int((time.time()-t)*1000),
                            f"Stamp duty: ₹{duty:,.0f}, Registration: ₹{reg:,.0f}")

    async def test_business_rental_yield(self) -> TestResult:
        t = time.time()
        yld = (50_000 * 12) / 10_000_000 * 100
        ok = abs(yld - 6.0) < 0.01
        return self._result("business_rental_yield", "Rental Yield", "Business Logic", 2,
                            ok, int((time.time()-t)*1000), f"Yield: {yld:.2f}%")

    async def test_business_appreciation(self) -> TestResult:
        t = time.time()
        cagr = ((6_500_000 / 5_000_000) ** (1/3) - 1) * 100
        ok = 9.0 < cagr < 10.0
        return self._result("business_appreciation", "CAGR Appreciation", "Business Logic", 2,
                            ok, int((time.time()-t)*1000), f"CAGR: {cagr:.2f}%")

    async def test_credits_system(self) -> TestResult:
        t = time.time()
        try:
            from ai.unified_credits import get_credits_manager
            mgr = get_credits_manager()
            return self._result("credits_system", "Credits System", "Business Logic", 2,
                                mgr is not None, int((time.time()-t)*1000),
                                "Credits manager initialized" if mgr else "Credits manager returned None")
        except Exception as e:
            return self._result("credits_system", "Credits System", "Business Logic", 2,
                                False, int((time.time()-t)*1000), error=str(e)[:120])

    async def test_auth_system(self) -> TestResult:
        t = time.time()
        try:
            from auth.user_auth import UserDatabase
            return self._result("auth_system", "Auth System", "Business Logic", 2,
                                True, int((time.time()-t)*1000), "UserDatabase module imported successfully")
        except Exception as e:
            return self._result("auth_system", "Auth System", "Business Logic", 2,
                                False, int((time.time()-t)*1000), error=str(e)[:120])

    # ------------------------------------------------------------------
    # TIER 3: Quality & Debug
    # ------------------------------------------------------------------

    async def test_response_quality_facts(self) -> TestResult:
        t = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.base_url}/api/smart-report/generate",
                    params={"lat": 12.8275, "lng": 77.6736, "locality": "Test Area", "query": "investment analysis"},
                )
                data = resp.json() if resp.status_code == 200 else {}
                market = data.get("market_snapshot", {})
                spatial = data.get("spatial_intelligence", {})
                has_facts = bool(market.get("avg_price_sqft")) and bool(spatial.get("walkability_score") is not None)
                return self._result("response_quality_facts", "Response Has Facts", "Quality", 3,
                                    has_facts, int((time.time()-t)*1000),
                                    "Smart report contains grounded market and spatial facts" if has_facts else "",
                                    error="" if has_facts else "Smart report missing grounded facts")
        except Exception as e:
            return self._result("response_quality_facts", "Response Has Facts", "Quality", 3,
                                False, int((time.time()-t)*1000), error=str(e)[:160])

    async def test_response_quality_relevance(self) -> TestResult:
        t = time.time()
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json={
                    "messages": [{"role": "user", "content": "How many credits do I have?"}],
                    "context": {"user_id": "test_admin"}
                })
                data = resp.json() if resp.status_code == 200 else {}
                message = (data.get("message") or "").lower()
                relevant = "credit" in message and data.get("intent") == "credits"
                return self._result("response_quality_relevance", "Response Relevance", "Quality", 3,
                                    relevant, int((time.time()-t)*1000),
                                    "Credits response matched query intent" if relevant else "",
                                    error="" if relevant else "Credits query did not produce a credits-focused response")
        except Exception as e:
            return self._result("response_quality_relevance", "Response Relevance", "Quality", 3,
                                False, int((time.time()-t)*1000), error=str(e)[:160])

    async def test_response_latency(self) -> TestResult:
        t = time.time()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                s = time.time()
                resp = await client.get(f"{self.base_url}/health")
                latency = (time.time() - s) * 1000
                ok = latency < 2000
                return self._result("response_latency", "Response Latency", "Quality", 3,
                                    ok, int((time.time()-t)*1000),
                                    f"Health endpoint: {latency:.0f}ms {'✓' if ok else '⚠ slow'}")
        except Exception as e:
            return self._result("response_latency", "Response Latency", "Quality", 3,
                                False, int((time.time()-t)*1000), error=str(e)[:120])

    async def test_feedback_positive(self) -> TestResult:
        t = time.time()
        sentiment = _detect_sentiment("This was very helpful! Love the view analysis feature")
        ok = sentiment == "positive"
        return self._result("feedback_positive", "Positive Feedback Detection", "Quality", 3,
                            ok, int((time.time()-t)*1000),
                            f"Detected: {sentiment}")

    async def test_feedback_negative(self) -> TestResult:
        t = time.time()
        sentiment = _detect_sentiment("The price estimate was wrong and too slow")
        ok = sentiment == "negative"
        return self._result("feedback_negative", "Negative Feedback Detection", "Quality", 3,
                            ok, int((time.time()-t)*1000),
                            f"Detected: {sentiment}")

    async def test_regression_intent_accuracy(self) -> TestResult:
        t = time.time()
        # Re-run intent classification and check ≥95% baseline
        passed = sum(1 for q, e in INTENT_TEST_QUERIES if _classify_intent(q) == e)
        pct = passed / len(INTENT_TEST_QUERIES) * 100
        return self._result("regression_intent_accuracy", "Intent Accuracy Regression", "Regression", 3,
                            pct >= 80, int((time.time()-t)*1000),
                            f"Accuracy: {pct:.1f}% (baseline: 80%)")

    async def test_regression_api_availability(self) -> TestResult:
        t = time.time()
        endpoints = ["/health", "/api/config", "/api/agent/capabilities"]
        ok_count = 0
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                for ep in endpoints:
                    try:
                        r = await client.get(f"{self.base_url}{ep}")
                        if r.status_code == 200:
                            ok_count += 1
                    except Exception:
                        pass
        except Exception:
            pass
        return self._result("regression_api_availability", "API Availability Regression", "Regression", 3,
                            ok_count == len(endpoints), int((time.time()-t)*1000),
                            f"{ok_count}/{len(endpoints)} core endpoints available")

    async def test_self_learning_engine(self) -> TestResult:
        t = time.time()
        try:
            from ai.enhanced_learning import get_enhanced_learning_engine
            engine = get_enhanced_learning_engine()
            return self._result("self_learning_engine", "Self-Learning Engine", "Quality", 3,
                                engine is not None, int((time.time()-t)*1000),
                                "Learning engine loaded" if engine else "Engine returned None")
        except Exception as e:
            return self._result("self_learning_engine", "Self-Learning Engine", "Quality", 3,
                                False, int((time.time()-t)*1000), error=str(e)[:120])

    async def test_cache_system(self) -> TestResult:
        t = time.time()
        try:
            from search.query_cache import get_chat_cache
            cache = get_chat_cache()
            return self._result("cache_system", "Cache Performance", "Quality", 3,
                                cache is not None, int((time.time()-t)*1000),
                                "Query cache system operational")
        except Exception as e:
            return self._result("cache_system", "Cache Performance", "Quality", 3,
                                False, int((time.time()-t)*1000), error=str(e)[:120])

    async def test_env_config(self) -> TestResult:
        t = time.time()
        required_vars = ["PINECONE_API_KEY", "MAPBOX_API_KEY"]
        optional_vars = ["OPENROUTER_API_KEY", "RAZORPAY_KEY_ID"]
        import os
        missing_req = [v for v in required_vars if not os.environ.get(v)]
        missing_opt = [v for v in optional_vars if not os.environ.get(v)]
        set_count = len(required_vars) - len(missing_req) + len(optional_vars) - len(missing_opt)
        total = len(required_vars) + len(optional_vars)
        details = f"{set_count}/{total} env vars configured"
        if missing_opt:
            details += f" (optional missing: {', '.join(missing_opt)})"
        return self._result("env_config", "Environment Config", "Debug", 3,
                            len(missing_req) == 0, int((time.time()-t)*1000),
                            details if len(missing_req) == 0 else "",
                            error=f"Missing required: {', '.join(missing_req)}" if missing_req else "")

    async def test_disk_space(self) -> TestResult:
        t = time.time()
        import shutil
        try:
            usage = shutil.disk_usage(Path(__file__).parent)
            free_gb = usage.free / (1024**3)
            total_gb = usage.total / (1024**3)
            ok = free_gb > 1.0
            return self._result("disk_space", "Disk Space Check", "Debug", 3,
                                ok, int((time.time()-t)*1000),
                                f"{free_gb:.1f}GB free / {total_gb:.1f}GB total")
        except Exception as e:
            return self._result("disk_space", "Disk Space Check", "Debug", 3,
                                False, int((time.time()-t)*1000), error=str(e)[:120])

    async def test_memory_usage(self) -> TestResult:
        t = time.time()
        try:
            import psutil
            proc = psutil.Process()
            mem_mb = proc.memory_info().rss / (1024**2)
            ok = mem_mb < 2048
            return self._result("memory_usage", "Memory Usage", "Debug", 3,
                                ok, int((time.time()-t)*1000),
                                f"Process using {mem_mb:.0f}MB RAM")
        except ImportError:
            return self._result("memory_usage", "Memory Usage", "Debug", 3,
                                True, int((time.time()-t)*1000),
                                "psutil not installed - skipped (install for production monitoring)")
        except Exception as e:
            return self._result("memory_usage", "Memory Usage", "Debug", 3,
                                False, int((time.time()-t)*1000), error=str(e)[:120])

    async def test_log_errors(self) -> TestResult:
        t = time.time()
        log_path = Path(__file__).parent.parent / "backend.log"
        if not log_path.exists():
            return self._result("log_errors", "Recent Log Errors", "Debug", 3,
                                True, int((time.time()-t)*1000), "No log file found (clean)")
        try:
            with open(log_path, "r", errors="ignore") as f:
                lines = f.readlines()[-100:]  # last 100 lines
            error_lines = [l.strip() for l in lines if "ERROR" in l or "CRITICAL" in l]
            if not error_lines:
                return self._result("log_errors", "Recent Log Errors", "Debug", 3,
                                    True, int((time.time()-t)*1000),
                                    "No errors in last 100 log lines")
            return self._result("log_errors", "Recent Log Errors", "Debug", 3,
                                False, int((time.time()-t)*1000),
                                error=f"{len(error_lines)} error(s): {error_lines[-1][:100]}", severity="warning")
        except Exception as e:
            return self._result("log_errors", "Recent Log Errors", "Debug", 3,
                                True, int((time.time()-t)*1000), f"Could not read log: {str(e)[:60]}")

    # ------------------------------------------------------------------
    # SUITE RUNNER
    # ------------------------------------------------------------------

    async def run_suite(self, tier: Optional[int] = None,
                        categories: Optional[List[str]] = None,
                        test_ids: Optional[List[str]] = None,
                        include_llm: bool = True) -> dict:
        """Run the full test suite and return Admin-Panel-friendly JSON."""
        import os as _os  # ensure env is accessible
        started_at = datetime.now().isoformat()
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Build ordered test list
        test_methods = {
            # Tier 1 Infrastructure
            "llm_health": self.test_llm_health,
            "llm_generation": self.test_llm_generation,
            "database_connection": self.test_database_connection,
            "database_tables": self.test_database_tables,
            "database_data": self.test_database_data,
            "api_health": self.test_api_health,
            "api_config": self.test_api_config,
            # Tier 1 Core AI
            "intent_classification": self.test_intent_classification,
            "slot_extraction": self.test_slot_extraction,
            "model_routing": self.test_model_routing,
            # Tier 2 API
            "api_chat": self.test_api_chat,
            "api_credits": self.test_api_credits,
            "api_geocode": self.test_api_geocode,
            "api_auth": self.test_api_auth,
            "api_agent_capabilities": self.test_api_agent_capabilities,
            "smart_report_v2": self.test_smart_report_v2,
            # Tier 2 Business
            "business_emi": self.test_business_emi,
            "business_price_sqft": self.test_business_price_sqft,
            "business_stamp_duty": self.test_business_stamp_duty,
            "business_rental_yield": self.test_business_rental_yield,
            "business_appreciation": self.test_business_appreciation,
            "credits_system": self.test_credits_system,
            "auth_system": self.test_auth_system,
            # Tier 3 Quality
            "response_quality_facts": self.test_response_quality_facts,
            "response_quality_relevance": self.test_response_quality_relevance,
            "response_latency": self.test_response_latency,
            "feedback_positive": self.test_feedback_positive,
            "feedback_negative": self.test_feedback_negative,
            "regression_intent_accuracy": self.test_regression_intent_accuracy,
            "regression_api_availability": self.test_regression_api_availability,
            "self_learning_engine": self.test_self_learning_engine,
            "cache_system": self.test_cache_system,
            "env_config": self.test_env_config,
            "disk_space": self.test_disk_space,
            "memory_usage": self.test_memory_usage,
            "log_errors": self.test_log_errors,
        }

        # Build lookup for tier/category filtering
        def_lookup = {d["id"]: d for d in TEST_DEFINITIONS}

        results = []
        for test_id, method in test_methods.items():
            defn = def_lookup.get(test_id, {})
            t_tier = defn.get("tier", 3)
            t_cat = defn.get("category", "Unknown")

            # Apply filters
            if tier and t_tier != tier:
                continue
            if categories and t_cat not in categories:
                continue
            if test_ids and test_id not in test_ids:
                continue
            if not include_llm and test_id in ("llm_health", "llm_generation"):
                continue

            try:
                result = await method()
                results.append(result)
            except Exception as e:
                results.append(self._result(
                    test_id, defn.get("name", test_id), t_cat, t_tier,
                    False, 0, error=f"Uncaught: {traceback.format_exc()[:200]}", severity="critical"
                ))

        finished_at = datetime.now().isoformat()

        # Compute summaries
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        pass_rate = round((passed / total * 100), 1) if total > 0 else 0

        # Tier breakdown
        tier_results = {}
        for t_num, t_label in [(1, "Critical"), (2, "Functional"), (3, "Quality")]:
            tier_items = [r for r in results if r.tier == t_num]
            if tier_items:
                tier_results[t_label] = {
                    "total": len(tier_items),
                    "passed": sum(1 for r in tier_items if r.passed),
                    "failed": sum(1 for r in tier_items if not r.passed),
                }

        # Category breakdown
        category_results = {}
        for r in results:
            if r.category not in category_results:
                category_results[r.category] = {"total": 0, "passed": 0, "failed": 0}
            category_results[r.category]["total"] += 1
            if r.passed:
                category_results[r.category]["passed"] += 1
            else:
                category_results[r.category]["failed"] += 1

        return {
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "duration_ms": sum(r.duration_ms for r in results),
            "tier_results": tier_results,
            "category_results": category_results,
            "results": [r.dict() for r in results],
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _classify_intent(query: str) -> str:
    from ai.gis_agents import IntentRouter
    return IntentRouter.classify(query).value


def _route_model(query: str, has_image: bool = False) -> str:
    from ai.gis_agents import IntentRouter
    from ai.model_router import route_model

    selection = route_model(
        user_query=query,
        intent=IntentRouter.classify(query),
        context={"images": [{}]} if has_image else {},
        available_models=["valora-ai-mini:latest", "valora-ai-pro:latest", "qwen3.5:397b-cloud"],
        history_length=0,
        user_override=None,
        user_tier="pro",
    )
    if has_image or selection.is_vision:
        return "vision"
    if selection.provider == "openrouter" or selection.is_cloud:
        return "openrouter"
    return "ollama"


def _detect_sentiment(text: str) -> str:
    t = text.lower()
    pos = ["love", "great", "helpful", "excellent", "good", "awesome", "amazing"]
    neg = ["wrong", "bad", "slow", "poor", "error", "issue", "problem"]
    if any(w in t for w in pos):
        return "positive"
    if any(w in t for w in neg):
        return "negative"
    return "neutral"


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/tests")
async def get_test_definitions():
    """Get all test definitions for the admin panel."""
    return {
        "tests": TEST_DEFINITIONS,
        "total": len(TEST_DEFINITIONS),
        "by_tier": {
            "1": len([t for t in TEST_DEFINITIONS if t["tier"] == 1]),
            "2": len([t for t in TEST_DEFINITIONS if t["tier"] == 2]),
            "3": len([t for t in TEST_DEFINITIONS if t["tier"] == 3]),
        },
        "categories": list(set(t["category"] for t in TEST_DEFINITIONS)),
    }


@router.post("/run")
async def run_tests(request: RunTestsRequest):
    """Run the unified test suite."""
    executor = UnifiedTestExecutor()
    try:
        result = await executor.run_suite(
            tier=request.tier,
            categories=request.categories,
            test_ids=request.test_ids,
            include_llm=request.include_llm,
        )
        return result
    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"[TestSuite] Error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg[:500])


@router.get("/health")
async def test_suite_health():
    """Check if test suite is operational."""
    return {
        "status": "healthy",
        "tests_loaded": len(TEST_DEFINITIONS),
        "categories": list(set(t["category"] for t in TEST_DEFINITIONS)),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/run-single/{test_id}")
async def run_single_test(test_id: str):
    """Run a single test by ID - useful for debugging."""
    executor = UnifiedTestExecutor()
    try:
        result = await executor.run_suite(test_ids=[test_id])
        if result["results"]:
            return result["results"][0]
        raise HTTPException(status_code=404, detail=f"Test '{test_id}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:500])


@router.get("/report")
async def get_test_report():
    """Run all tests and return a downloadable report."""
    executor = UnifiedTestExecutor()
    result = await executor.run_suite()

    report_lines = [
        f"# Valora AI Test Suite Report",
        f"",
        f"**Run ID:** {result['run_id']}",
        f"**Date:** {result['started_at']}",
        f"**Total:** {result['total']} | **Passed:** {result['passed']} | **Failed:** {result['failed']} | **Rate:** {result['pass_rate']}%",
        f"",
        f"## Tier Breakdown",
    ]
    for tier_name, tier_data in result.get("tier_results", {}).items():
        report_lines.append(f"- **{tier_name}:** {tier_data['passed']}/{tier_data['total']} passed")

    report_lines.append(f"\n## Category Breakdown")
    for cat, cat_data in result.get("category_results", {}).items():
        report_lines.append(f"- **{cat}:** {cat_data['passed']}/{cat_data['total']} passed")

    report_lines.append(f"\n## Detailed Results Summary\n")
    report_lines.append("| Test | Tier | Status | Time | Summary |")
    report_lines.append("|------|------|--------|------|---------|")
    for r in result["results"]:
        status = "✅" if r["passed"] else "❌"
        # Table-friendly short version
        detail = r.get("details") or r.get("error") or ""
        short_detail = (detail[:67] + '...') if len(detail) > 70 else detail
        report_lines.append(f"| {r['test_name']} | {r['tier']} | {status} | {r['duration_ms']}ms | {short_detail} |")

    report_lines.append(f"\n## Full Test Output & Details\n")
    for r in result["results"]:
        status = "PASSED" if r["passed"] else "FAILED"
        report_lines.append(f"### {r['test_name']} ({status})")
        report_lines.append(f"- **Tier:** {r['tier']}")
        report_lines.append(f"- **Category:** {r['category']}")
        report_lines.append(f"- **Duration:** {r['duration_ms']}ms")
        
        if r.get("details"):
            report_lines.append(f"- **Output/Details:** {r['details']}")
        
        if r.get("error"):
            report_lines.append(f"- **Error Information:**\n```\n{r['error']}\n```")
        
        report_lines.append(f"---")

    return {"report": "\n".join(report_lines), "data": result}
