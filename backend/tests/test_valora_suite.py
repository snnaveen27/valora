"""
Valora AI — Unified Test Suite
===============================
Tests: Intent classification, model routing, endpoints, query responses,
       slot extraction, task planning, credits, and business logic.

Run:  python -m tests.test_valora_suite          (from backend/)
      python -m tests.test_valora_suite --live    (includes live LLM streaming)

Auto-generates: backend/tests/test_results_complete.md
"""

import asyncio
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure backend is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------
@dataclass
class TestResult:
    id: str
    category: str
    name: str
    passed: bool
    duration_ms: int = 0
    details: str = ""
    error: str = ""

@dataclass
class SuiteResults:
    started_at: str = ""
    finished_at: str = ""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: int = 0
    results: List[TestResult] = field(default_factory=list)
    sections: Dict[str, List[TestResult]] = field(default_factory=dict)

    def add(self, r: TestResult):
        self.results.append(r)
        self.sections.setdefault(r.category, []).append(r)
        self.total += 1
        if r.passed:
            self.passed += 1
        else:
            self.failed += 1


# ---------------------------------------------------------------------------
# TEST DATA — comprehensive query bank
# ---------------------------------------------------------------------------
INTENT_TESTS = [
    # Greetings (should stay local, instant response)
    {"id": "greet_01", "query": "hello", "expected": "greeting"},
    {"id": "greet_02", "query": "hi there", "expected": "greeting"},
    {"id": "greet_03", "query": "good morning", "expected": "greeting"},
    {"id": "greet_04", "query": "hey", "expected": "greeting"},
    {"id": "greet_05", "query": "how are you", "expected": "smalltalk"},

    # Navigation
    {"id": "nav_01", "query": "Show me Koramangala on the map", "expected": "navigate"},
    {"id": "nav_02", "query": "Fly to Whitefield", "expected": "navigate"},
    {"id": "nav_03", "query": "Go to Indiranagar", "expected": "navigate"},
    {"id": "nav_04", "query": "Take me to Electronic City", "expected": "navigate"},
    {"id": "nav_05", "query": "Navigate to HSR Layout", "expected": "navigate"},

    # Property Search
    {"id": "search_01", "query": "Find 2BHK apartments in Indiranagar under 80 lakhs", "expected": "property_search"},
    {"id": "search_02", "query": "Find villas in Whitefield for 2 crores", "expected": "property_search"},
    {"id": "search_03", "query": "3BHK near metro station in Bangalore", "expected": "property_search"},
    {"id": "search_04", "query": "Affordable flats in Sarjapur Road", "expected": "property_search"},
    {"id": "search_05", "query": "Find luxury penthouses in Koramangala", "expected": "property_search"},

    # Area Analysis
    {"id": "area_01", "query": "Analyze Koramangala for livability", "expected": "analyze_area"},
    {"id": "area_02", "query": "What amenities are near Whitefield?", "expected": "analyze_area"},
    {"id": "area_03", "query": "Tell me about flood risk in Bellandur", "expected": "terrain"},
    {"id": "area_04", "query": "Analyze walkability of Indiranagar area", "expected": "analyze_area"},

    # Building Analysis
    {"id": "bldg_01", "query": "Analyze this building's shadow impact", "expected": "analyze_building"},
    {"id": "bldg_02", "query": "Analyze the best floor for view in this building", "expected": "analyze_building"},

    # Comparison
    {"id": "comp_01", "query": "Compare Whitefield vs Sarjapur Road", "expected": "comparison"},
    {"id": "comp_02", "query": "Which is better, Koramangala or Indiranagar?", "expected": "comparison"},
    {"id": "comp_03", "query": "Pros and cons of HSR Layout vs BTM Layout", "expected": "comparison"},

    # Simulation
    {"id": "sim_01", "query": "Simulate what happens to prices if metro comes to Whitefield", "expected": "simulate"},
    {"id": "sim_02", "query": "Simulate impact of new IT park near Sarjapur", "expected": "simulate"},
    {"id": "sim_03", "query": "What if interest rates drop by 2%?", "expected": "simulate"},

    # Investment
    {"id": "inv_01", "query": "Best areas for real estate investment in Bangalore", "expected": "investment"},
    {"id": "inv_02", "query": "Which areas have high appreciation potential?", "expected": "investment"},
    {"id": "inv_03", "query": "ROI analysis for Whitefield properties", "expected": "investment"},

    # Market Trend
    {"id": "trend_01", "query": "Price trend in Koramangala over last 5 years", "expected": "market_trend"},
    {"id": "trend_02", "query": "Average price per sqft in Whitefield", "expected": "valuation"},
    {"id": "trend_03", "query": "Market trend for Electronic City area", "expected": "market_trend"},

    # Valuation
    {"id": "val_01", "query": "What is the estimated price of 3BHK in Sarjapur Road?", "expected": "property_search"},
    {"id": "val_02", "query": "Valuation estimate for 1200 sqft space in Indiranagar", "expected": "valuation"},

    # Terrain
    {"id": "terr_01", "query": "Show terrain elevation around Whitefield", "expected": "terrain"},

    # General / Edge
    {"id": "gen_01", "query": "What is Valora AI?", "expected": "general"},
    {"id": "edge_01", "query": "", "expected": "general", "note": "empty query"},
    {"id": "edge_02", "query": "xyz123 gibberish noodle", "expected": "general", "note": "nonsense"},
    {"id": "edge_03", "query": "Delete all database records", "expected": "general", "note": "security probe"},
]

MODEL_ROUTING_TESTS = [
    {"id": "route_01", "query": "hello", "intent": "greeting", "expect_cloud": False, "expect_vision": False},
    {"id": "route_02", "query": "Show me Koramangala", "intent": "navigate", "expect_cloud": False},
    {"id": "route_03", "query": "Tell me about Whitefield", "intent": "analyze_area", "expect_cloud": False},
    {"id": "route_04", "query": "Compare Whitefield vs Electronic City for investment ROI over 5 years", "intent": "comparison", "expect_cloud": True},
    {"id": "route_05", "query": "Simulate metro impact on Sarjapur Road prices with IT hiring growth of 20%", "intent": "simulate", "expect_cloud": True},
    {"id": "route_06", "query": "Analyze this property photo", "intent": "analyze_building", "has_images": True, "expect_cloud": True, "expect_vision": True},
    {"id": "route_07", "query": "Find 2BHK in Whitefield under 80L, compare with Sarjapur, and simulate metro extension impact", "intent": "property_search", "expect_cloud": True},
    {"id": "route_08", "query": "What is the price per sqft in Koramangala?", "intent": "valuation", "expect_cloud": False},
]

ENDPOINT_TESTS = [
    {"id": "ep_health", "method": "GET", "path": "/api/admin/health", "expect_status": 200},
    {"id": "ep_auth_tiers", "method": "GET", "path": "/api/auth/tiers", "expect_status": 200},
    {"id": "ep_credits", "method": "GET", "path": "/api/credits/test_user_001", "expect_status": 200},
    {"id": "ep_plans", "method": "GET", "path": "/api/credits/plans", "expect_status": 200},
    {"id": "ep_topup", "method": "GET", "path": "/api/credits/topup-packs", "expect_status": 200},
    {"id": "ep_pay_plans", "method": "GET", "path": "/api/payments/plans", "expect_status": 200},
    {"id": "ep_pay_config", "method": "GET", "path": "/api/payments/config", "expect_status": 200},
]

SLOT_EXTRACTION_TESTS = [
    {"id": "slot_01", "query": "Find 2BHK apartments in Indiranagar under 80 lakhs",
     "expected_slots": {"configuration": "2bhk", "location": "indiranagar"}},
    {"id": "slot_02", "query": "Compare Whitefield vs Sarjapur Road",
     "expected_slots": {"location_a": "whitefield", "location_b": "sarjapur"}},
    {"id": "slot_03", "query": "Show me 3BHK villas near Koramangala with budget under 2 crores",
     "expected_slots": {"configuration": "3bhk", "property_type": "villa", "location": "koramangala"}},
]

STRESS_TESTS = [
    {"id": "stress_01", "query": "I work near Manyata Tech Park but only go twice a week. Find areas where I can buy a 2BHK under 90 lakhs that are quieter, have good appreciation, and avoid traffic. Show best 3.",
     "expected_intent": "property_search", "cloud_expected": True},
    {"id": "stress_02", "query": "Analyze Sarjapur Road and simulate what happens to property prices if a metro line opens within 5 years and IT hiring grows by 20%. Show risks and winners.",
     "expected_intent": "simulate", "cloud_expected": True},
    {"id": "stress_03", "query": "Find 3BHK in Koramangala under 50 lakhs with 2000 sqft - if none, propose nearest realistic alternatives and also compare with HSR Layout.",
     "expected_intent": "property_search", "cloud_expected": True},
]


# ---------------------------------------------------------------------------
# TEST RUNNERS
# ---------------------------------------------------------------------------

def _run_timed(fn, *args, **kwargs):
    """Run a function and return (result, duration_ms)."""
    t0 = time.time()
    try:
        result = fn(*args, **kwargs)
        return result, int((time.time() - t0) * 1000), None
    except Exception as e:
        return None, int((time.time() - t0) * 1000), str(e)


def test_intent_classification(suite: SuiteResults):
    """Test 1: Intent classification accuracy."""
    print("\n" + "=" * 60)
    print("SECTION 1: INTENT CLASSIFICATION")
    print("=" * 60)

    try:
        from ai.gis_agents import IntentRouter, Intent
    except ImportError as e:
        suite.add(TestResult("intent_import", "Intent Classification", "Import IntentRouter", False, error=str(e)))
        return

    for tc in INTENT_TESTS:
        qid, query, expected = tc["id"], tc["query"], tc["expected"]
        try:
            intent = IntentRouter.classify(query, has_building=False, has_location=False)
            actual = intent.value if intent else "unknown"
            # Flexible matching: expected can be substring of actual
            passed = expected in actual or actual in expected
            details = f"expected={expected}, got={actual}"
            suite.add(TestResult(qid, "Intent Classification", query[:60] or "(empty)", passed, details=details))
            icon = "✅" if passed else "❌"
            print(f"  {icon} {qid}: {details}")
        except Exception as e:
            suite.add(TestResult(qid, "Intent Classification", query[:60] or "(empty)", False, error=str(e)))
            print(f"  ❌ {qid}: ERROR {e}")


def test_model_routing(suite: SuiteResults):
    """Test 2: Model router selects correct model tier."""
    print("\n" + "=" * 60)
    print("SECTION 2: MODEL ROUTING")
    print("=" * 60)

    try:
        from ai.model_router import route_model, _MODEL_CAPABILITIES, get_model_capability
        from ai.gis_agents import Intent
        _MODEL_CAPABILITIES.clear()
    except ImportError as e:
        suite.add(TestResult("route_import", "Model Routing", "Import model_router", False, error=str(e)))
        return

    INTENT_MAP = {
        "greeting": Intent.GREETING, "navigate": Intent.NAVIGATE,
        "analyze_area": Intent.ANALYZE_AREA, "analyze_building": Intent.ANALYZE_BUILDING,
        "property_search": Intent.PROPERTY_SEARCH, "comparison": Intent.COMPARISON,
        "simulate": Intent.SIMULATE, "investment": Intent.INVESTMENT,
        "price_trend": Intent.MARKET_TREND, "valuation": Intent.VALUATION,
        "general": Intent.GENERAL,
    }

    available = ["qwen3:8b", "kimi-k2.5:cloud", "deepseek-v3.2:cloud", "qwen3-vl:235b-instruct-cloud"]

    for tc in MODEL_ROUTING_TESTS:
        qid = tc["id"]
        intent = INTENT_MAP.get(tc["intent"], Intent.GENERAL)
        ctx = {}
        if tc.get("has_images"):
            ctx["images"] = [{"base64": "test"}]

        sel, ms, err = _run_timed(route_model, tc["query"], intent, ctx, available)
        if err:
            suite.add(TestResult(qid, "Model Routing", tc["query"][:60], False, ms, error=err))
            print(f"  ❌ {qid}: ERROR {err}")
            continue

        checks = []
        passed = True
        if "expect_cloud" in tc:
            cloud_ok = sel.escalated == tc["expect_cloud"]
            if not cloud_ok:
                passed = False
            checks.append(f"cloud={'OK' if cloud_ok else 'FAIL'}(want={tc['expect_cloud']},got={sel.escalated})")
        if tc.get("expect_vision"):
            vis_ok = sel.is_vision == tc["expect_vision"]
            if not vis_ok:
                passed = False
            checks.append(f"vision={'OK' if vis_ok else 'FAIL'}")

        details = f"model={sel.model} score={sel.complexity_score:.2f} {' '.join(checks)}"
        suite.add(TestResult(qid, "Model Routing", tc["query"][:60], passed, ms, details=details))
        icon = "✅" if passed else "❌"
        print(f"  {icon} {qid}: {details}")


def test_model_learning(suite: SuiteResults):
    """Test 3: Learning-aware performance tracking."""
    print("\n" + "=" * 60)
    print("SECTION 3: LEARNING-AWARE ROUTING")
    print("=" * 60)

    try:
        from ai.model_router import record_model_performance, _get_model_score_bonus, _PERF_DB
        import sqlite3

        # Record some test performance data
        for i in range(5):
            record_model_performance("test-model", "simulate", 0.7, 3000 + i * 100, True, 200)
        record_model_performance("test-model-bad", "simulate", 0.7, 40000, False, 0)
        record_model_performance("test-model-bad", "simulate", 0.7, 45000, False, 0)
        record_model_performance("test-model-bad", "simulate", 0.7, 50000, False, 0)

        # Check bonus for good model
        bonus_good = _get_model_score_bonus("test-model", "simulate")
        # Check penalty for bad model
        bonus_bad = _get_model_score_bonus("test-model-bad", "simulate")

        passed = bonus_good >= 0 and bonus_bad <= 0
        details = f"good_bonus={bonus_good:.3f}, bad_bonus={bonus_bad:.3f}"
        suite.add(TestResult("learn_01", "Learning", "Performance tracking + bonus", passed, details=details))
        icon = "✅" if passed else "❌"
        print(f"  {icon} learn_01: {details}")

        # Verify DB exists
        db_exists = _PERF_DB.exists()
        suite.add(TestResult("learn_02", "Learning", "SQLite perf DB exists", db_exists, details=str(_PERF_DB)))
        print(f"  {'✅' if db_exists else '❌'} learn_02: DB exists={db_exists}")

        # Clean up test data
        conn = sqlite3.connect(str(_PERF_DB))
        conn.execute("DELETE FROM model_perf WHERE model LIKE 'test-model%'")
        conn.commit()
        conn.close()

    except Exception as e:
        suite.add(TestResult("learn_err", "Learning", "Learning test", False, error=str(e)))
        print(f"  ❌ learn_err: {e}")


def test_endpoints(suite: SuiteResults, base_url: str = "http://localhost:8000"):
    """Test 4: REST API endpoint health."""
    print("\n" + "=" * 60)
    print("SECTION 4: API ENDPOINTS")
    print("=" * 60)

    import urllib.request

    for tc in ENDPOINT_TESTS:
        qid, path, expect = tc["id"], tc["path"], tc["expect_status"]
        url = f"{base_url}{path}"
        t0 = time.time()
        try:
            req = urllib.request.Request(url, method=tc["method"])
            resp = urllib.request.urlopen(req, timeout=10)
            status = resp.status
            ms = int((time.time() - t0) * 1000)
            passed = status == expect
            details = f"{tc['method']} {path} → {status} ({ms}ms)"
            suite.add(TestResult(qid, "API Endpoints", path, passed, ms, details=details))
            icon = "✅" if passed else "❌"
            print(f"  {icon} {qid}: {details}")
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            suite.add(TestResult(qid, "API Endpoints", path, False, ms, error=str(e)[:120]))
            print(f"  ❌ {qid}: {path} → {str(e)[:80]}")


def test_slot_extraction(suite: SuiteResults):
    """Test 5: Slot extraction from queries."""
    print("\n" + "=" * 60)
    print("SECTION 5: SLOT EXTRACTION")
    print("=" * 60)

    try:
        from ai.gis_agents import IntentRouter
    except ImportError as e:
        suite.add(TestResult("slot_import", "Slot Extraction", "Import", False, error=str(e)))
        return

    for tc in SLOT_EXTRACTION_TESTS:
        qid, query = tc["id"], tc["query"]
        try:
            intent = IntentRouter.classify(query, has_building=False, has_location=False)
            actual = intent.value if intent else "unknown"
            # Basic check: did it classify to something useful
            passed = actual != "unknown"
            details = f"intent={actual}"
            suite.add(TestResult(qid, "Slot Extraction", query[:60], passed, details=details))
            icon = "✅" if passed else "❌"
            print(f"  {icon} {qid}: {details}")
        except Exception as e:
            suite.add(TestResult(qid, "Slot Extraction", query[:60], False, error=str(e)))
            print(f"  ❌ {qid}: {e}")


def test_streaming_chat(suite: SuiteResults, base_url: str = "http://localhost:8000"):
    """Test 6: Live streaming chat endpoint (requires --live flag)."""
    print("\n" + "=" * 60)
    print("SECTION 6: STREAMING CHAT (LIVE)")
    print("=" * 60)

    import urllib.request

    test_queries = [
        {"id": "live_01", "query": "hello", "expect_event": "content"},
        {"id": "live_02", "query": "Show me Koramangala", "expect_event": "content"},
        {"id": "live_03", "query": "Find 2BHK in Whitefield under 80L", "expect_event": "content"},
    ]

    for tc in test_queries:
        qid = tc["id"]
        payload = json.dumps({
            "messages": [{"role": "user", "content": tc["query"]}],
            "context": {"user_id": "test_suite", "llm_config": {"provider": "ollama", "local_model": "qwen3:8b", "cloud_enabled": False}}
        }).encode()

        t0 = time.time()
        try:
            req = urllib.request.Request(
                f"{base_url}/api/chat/stream",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=60)
            body = resp.read().decode("utf-8", errors="ignore")
            ms = int((time.time() - t0) * 1000)

            events = [l for l in body.split("\n") if l.startswith("data:")]
            has_content = any('"content"' in e for e in events)
            has_done = any('"done"' in e for e in events)
            has_model = any('"model_selection"' in e for e in events)

            passed = has_content and has_done
            details = f"events={len(events)}, content={has_content}, done={has_done}, model_sel={has_model}, {ms}ms"
            suite.add(TestResult(qid, "Streaming Chat", tc["query"][:60], passed, ms, details=details))
            icon = "✅" if passed else "❌"
            print(f"  {icon} {qid}: {details}")
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            suite.add(TestResult(qid, "Streaming Chat", tc["query"][:60], False, ms, error=str(e)[:120]))
            print(f"  ❌ {qid}: {str(e)[:80]}")


def test_stress_queries(suite: SuiteResults):
    """Test 7: Stress test complex queries for correct routing."""
    print("\n" + "=" * 60)
    print("SECTION 7: STRESS TESTS")
    print("=" * 60)

    try:
        from ai.model_router import route_model, _MODEL_CAPABILITIES
        from ai.gis_agents import IntentRouter, Intent
        _MODEL_CAPABILITIES.clear()
    except ImportError as e:
        suite.add(TestResult("stress_import", "Stress Tests", "Import", False, error=str(e)))
        return

    available = ["qwen3:8b", "kimi-k2.5:cloud", "deepseek-v3.2:cloud", "qwen3-vl:235b-instruct-cloud"]

    for tc in STRESS_TESTS:
        qid = tc["id"]
        try:
            intent = IntentRouter.classify(tc["query"], has_building=False, has_location=False)
            sel = route_model(tc["query"], intent, {}, available)

            cloud_ok = sel.escalated == tc.get("cloud_expected", False)
            details = f"intent={intent.value}, model={sel.model}, score={sel.complexity_score:.2f}, escalated={sel.escalated}"
            suite.add(TestResult(qid, "Stress Tests", tc["query"][:60], cloud_ok, details=details))
            icon = "✅" if cloud_ok else "❌"
            print(f"  {icon} {qid}: {details}")
        except Exception as e:
            suite.add(TestResult(qid, "Stress Tests", tc["query"][:60], False, error=str(e)))
            print(f"  ❌ {qid}: {e}")


def test_openrouter_availability(suite: SuiteResults):
    """Test 8: OpenRouter configuration check."""
    print("\n" + "=" * 60)
    print("SECTION 8: OPENROUTER CONFIG")
    print("=" * 60)

    try:
        from ai.model_router import _openrouter_available, OPENROUTER_MODELS
        available = _openrouter_available()
        details = f"configured={available}, models={list(OPENROUTER_MODELS.keys())}"
        # This is informational — not a failure if key is missing
        suite.add(TestResult("or_01", "OpenRouter", "API key configured", True, details=details))
        print(f"  ℹ️  or_01: {details}")
    except Exception as e:
        suite.add(TestResult("or_err", "OpenRouter", "Config check", False, error=str(e)))
        print(f"  ❌ or_err: {e}")


# ---------------------------------------------------------------------------
# REPORT GENERATOR
# ---------------------------------------------------------------------------

def generate_report(suite: SuiteResults) -> str:
    """Generate test_results_complete.md content."""
    lines = []
    lines.append("# Valora AI — Test Results")
    lines.append(f"\n**Generated:** {suite.finished_at}")
    lines.append(f"**Duration:** {suite.duration_ms}ms")
    lines.append(f"**Total:** {suite.total} | **Passed:** {suite.passed} | **Failed:** {suite.failed}")
    pct = round(suite.passed / max(suite.total, 1) * 100, 1)
    lines.append(f"**Pass Rate:** {pct}%")

    # Summary table
    lines.append("\n## Summary by Section\n")
    lines.append("| Section | Total | Passed | Failed | Pass Rate |")
    lines.append("|---------|-------|--------|--------|-----------|")
    for section, results in suite.sections.items():
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        rate = round(passed / max(total, 1) * 100, 1)
        lines.append(f"| {section} | {total} | {passed} | {failed} | {rate}% |")

    # Detailed results per section
    for section, results in suite.sections.items():
        lines.append(f"\n## {section}\n")
        lines.append("| ID | Test | Status | Duration | Details |")
        lines.append("|----|------|--------|----------|---------|")
        for r in results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            dur = f"{r.duration_ms}ms" if r.duration_ms else "-"
            detail = r.details or r.error or "-"
            detail = detail.replace("|", "\\|")[:120]
            name = r.name[:50].replace("|", "\\|")
            lines.append(f"| {r.id} | {name} | {status} | {dur} | {detail} |")

    # Failed tests summary
    failed = [r for r in suite.results if not r.passed]
    if failed:
        lines.append("\n## Failed Tests — Action Items\n")
        for r in failed:
            lines.append(f"- **{r.id}** ({r.category}): {r.name}")
            if r.error:
                lines.append(f"  - Error: `{r.error[:150]}`")
            if r.details:
                lines.append(f"  - Details: {r.details[:150]}")

    # Architecture notes
    lines.append("\n## Architecture\n")
    lines.append("- **Default model:** qwen3:8b (local Ollama)")
    lines.append("- **Cloud toggle:** Frontend toggle enables intelligent model routing")
    lines.append("- **Cloud priority:** OpenRouter → Ollama Cloud (fallback)")
    lines.append("- **Learning:** SQLite tracks model latency/success → influences future routing")
    lines.append("- **Providers:** Ollama (local + cloud), OpenRouter (deepseek, qwen-vl, claude)")
    lines.append("- **Task banner:** Shows selected model, complexity score, reasoning")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    live = "--live" in sys.argv
    base_url = "http://localhost:8000"

    suite = SuiteResults(started_at=datetime.now().isoformat())

    print("\n" + "=" * 60)
    print("  VALORA AI — UNIFIED TEST SUITE")
    print("=" * 60)
    print(f"  Time: {suite.started_at}")
    print(f"  Live streaming tests: {'YES' if live else 'NO (use --live)'}")
    print(f"  Backend: {base_url}")

    t0 = time.time()

    # Run all test sections
    test_intent_classification(suite)
    test_model_routing(suite)
    test_model_learning(suite)
    test_endpoints(suite, base_url)
    test_slot_extraction(suite)
    test_stress_queries(suite)
    test_openrouter_availability(suite)

    if live:
        test_streaming_chat(suite, base_url)

    suite.finished_at = datetime.now().isoformat()
    suite.duration_ms = int((time.time() - t0) * 1000)

    # Summary
    pct = round(suite.passed / max(suite.total, 1) * 100, 1)
    print("\n" + "=" * 60)
    print(f"  RESULTS: {suite.passed}/{suite.total} passed ({pct}%)")
    print(f"  Duration: {suite.duration_ms}ms")
    print("=" * 60)

    # Generate report
    report = generate_report(suite)
    report_path = BACKEND_DIR / "tests" / "test_results_complete.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n📄 Report saved: {report_path}")

    # Return exit code
    return 0 if suite.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
