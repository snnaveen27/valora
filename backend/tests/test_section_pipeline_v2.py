"""
Valora AI - V2 Section Analysis Pipeline Test Suite
====================================================

Comprehensive tests for all v2 pipeline components:
- IntentRouter (gis_agents)
- EvidenceReference / FeatureCache (spatial_feature_engine)
- ConsistencyValidator
- SectionPrompts (section_prompts_v2)
- PipelineMetrics
- DriftDetector
- ReviewFramework

All tests use unittest.mock for DB/LLM isolation.

Usage:
    python -m tests.test_section_pipeline_v2
"""

import importlib
import os
import sys
import time
import types
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# ---------------------------------------------------------------------------
# Pre-import stubs: create minimal mock modules so ai/__init__.py does not
# blow up when we import sub-modules through the package.
# ---------------------------------------------------------------------------

def _ensure_mock(name: str):
    """Register a lightweight mock module in sys.modules if missing."""
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)

# Stub out modules that ai/__init__.py tries to import but are unavailable
# in the test environment (missing backend.config, spatial.*, engines.*, etc.).
for _mod in [
    "backend", "backend.config",
    "config",
    "engines", "engines.digital_twin",
    "spatial", "spatial.spatial_nlp", "spatial.spatial_3d_reasoning",
    "spatial.spatial_memory_graph", "spatial.spatial_memory",
    "spatial.terrain_service",
    "ai_context",
    "enhanced_data_service",
    "spatial_inference",
    "viewshed_analyzer", "analyzers", "analyzers.viewshed_analyzer",
    "tool_executor",
    "city_intelligence", "city_intelligence.locality_personality",
    "city_intelligence.evolution_timeline", "city_intelligence.risk_indexes",
    "city_intelligence.causal_reasoning",
    "services", "services.property_service", "services.locality_service",
    "simulation_engine",
    "ai.response_templates",
    "ai.fact_verifier", "ai.agentic_loop", "ai.tools_registry",
    "ai.agentic_memory", "ai.self_learning",
]:
    _ensure_mock(_mod)

# Provide the config object that fact_verifier expects
_backend_config = sys.modules.get("backend.config", types.ModuleType("backend.config"))
_backend_config.config = MagicMock()
sys.modules["backend.config"] = _backend_config
sys.modules["config"] = _backend_config

# Now import the real sub-modules (these do NOT pull in ai/__init__.py
# because we import them as individual modules via importlib).
def _import_module_direct(module_filename: str, module_name: str):
    """Import a .py file directly without triggering ai/__init__.py."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        module_name,
        os.path.join(os.path.dirname(__file__), '..', 'ai', module_filename),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

# Import modules we need to test
_cv_mod = _import_module_direct("consistency_validator.py", "ai.consistency_validator")
_sfe_mod = _import_module_direct("spatial_feature_engine.py", "ai.spatial_feature_engine")
_sp_mod = _import_module_direct("section_prompts_v2.py", "ai.section_prompts_v2")
_pm_mod = _import_module_direct("pipeline_metrics.py", "ai.pipeline_metrics")
_dd_mod = _import_module_direct("drift_detector.py", "ai.drift_detector")
_rf_mod = _import_module_direct("review_framework.py", "ai.review_framework")
# gis_agents depends on many things, but we only need IntentRouter and Intent
_ga_mod = _import_module_direct("gis_agents.py", "ai.gis_agents")


# =============================================================================
# 1. TestIntentRouter
# =============================================================================

class TestIntentRouter(unittest.TestCase):
    """Tests for IntentRouter from ai.gis_agents."""

    def setUp(self):
        self.router = _ga_mod.IntentRouter
        self.Intent = _ga_mod.Intent

    def test_classify_investment_query(self):
        """'Is this a good investment?' should return INVESTMENT."""
        result = self.router.classify("Is this a good investment?")
        self.assertEqual(result, self.Intent.INVESTMENT)

    def test_classify_valuation_query(self):
        """'What is the value?' should return VALUATION."""
        result = self.router.classify("What is the value of this property?")
        self.assertEqual(result, self.Intent.VALUATION)

    def test_classify_area_query(self):
        """'Analyze this area' should return ANALYZE_AREA."""
        result = self.router.classify("Analyze this area")
        self.assertEqual(result, self.Intent.ANALYZE_AREA)

    def test_classify_buy_query(self):
        """'Should I buy this?' should return INVESTMENT or RECOMMENDATION."""
        result = self.router.classify("Should I buy this property?")
        self.assertIn(result, [self.Intent.INVESTMENT, self.Intent.RECOMMENDATION])

    def test_get_sections_for_analyze(self):
        """ANALYZE_AREA should return all 5 core sections."""
        sections = self.router.get_sections_for_intent(self.Intent.ANALYZE_AREA, "")
        expected = {"terrain", "infrastructure", "market", "risk", "urban_form"}
        self.assertEqual(set(sections), expected)

    def test_get_sections_for_investment(self):
        """INVESTMENT should return market, risk, infrastructure."""
        sections = self.router.get_sections_for_intent(self.Intent.INVESTMENT, "")
        expected = {"market", "risk", "infrastructure"}
        self.assertEqual(set(sections), expected)

    def test_extract_place_name(self):
        """'in Koramangala' should extract 'Koramangala'."""
        result = self.router.extract_place_name("Is it good to invest in Koramangala?")
        self.assertEqual(result, "Koramangala")

    def test_extract_coordinates(self):
        """'12.9716, 77.5946' should extract (12.9716, 77.5946)."""
        result = self.router.extract_coordinates("Analyze coordinates 12.9716, 77.5946")
        self.assertIsNotNone(result)
        lat, lng = result
        self.assertAlmostEqual(lat, 12.9716, places=3)
        self.assertAlmostEqual(lng, 77.5946, places=3)


# =============================================================================
# 2. TestEvidenceReference
# =============================================================================

class TestEvidenceReference(unittest.TestCase):
    """Tests for EvidenceReference from ai.spatial_feature_engine."""

    def setUp(self):
        self.EvidenceReference = _sfe_mod.EvidenceReference

    def test_to_dict(self):
        """to_dict returns correct dict with feature, source, value, timestamp, confidence."""
        ref = self.EvidenceReference(
            feature="elevation_m",
            source="terrain_grid",
            value=920.5,
            timestamp="2025-01-01T00:00:00",
            confidence="HIGH"
        )
        d = ref.to_dict()
        self.assertEqual(d["feature"], "elevation_m")
        self.assertEqual(d["source"], "terrain_grid")
        self.assertEqual(d["value"], "920.5")
        self.assertEqual(d["timestamp"], "2025-01-01T00:00:00")
        self.assertEqual(d["confidence"], "HIGH")

    def test_default_timestamp(self):
        """Timestamp is auto-generated when not provided."""
        ref = self.EvidenceReference(
            feature="slope_degrees",
            source="terrain_grid",
            value=3.2,
            confidence="MEDIUM"
        )
        self.assertTrue(len(ref.timestamp) > 0)
        parsed = datetime.fromisoformat(ref.timestamp)
        self.assertIsNotNone(parsed)


# =============================================================================
# 3. TestFeatureCache
# =============================================================================

class TestFeatureCache(unittest.TestCase):
    """Tests for FeatureCache from ai.spatial_feature_engine."""

    def setUp(self):
        self.FeatureCache = _sfe_mod.FeatureCache
        self.cache = self.FeatureCache(ttl_seconds=2)

    def test_cache_set_and_get(self):
        """Set a value and get it back."""
        self.cache.set(12.97, 77.59, "terrain", {"elevation": 920})
        result = self.cache.get(12.97, 77.59, "terrain")
        self.assertEqual(result, {"elevation": 920})

    def test_cache_miss(self):
        """Returns None for unknown key."""
        result = self.cache.get(0.0, 0.0, "nonexistent")
        self.assertIsNone(result)

    def test_cache_ttl_expiration(self):
        """Entries expire after TTL."""
        short_cache = self.FeatureCache(ttl_seconds=1)
        short_cache.set(12.97, 77.59, "market", {"price": 8000})
        self.assertIsNotNone(short_cache.get(12.97, 77.59, "market"))
        time.sleep(1.1)
        self.assertIsNone(short_cache.get(12.97, 77.59, "market"))

    def test_cache_clear(self):
        """Clear removes all entries."""
        self.cache.set(12.97, 77.59, "terrain", {"elevation": 920})
        self.cache.set(12.97, 77.59, "market", {"price": 8000})
        self.assertEqual(self.cache.size, 2)
        self.cache.clear()
        self.assertEqual(self.cache.size, 0)


# =============================================================================
# 4. TestConsistencyValidator
# =============================================================================

class TestConsistencyValidator(unittest.TestCase):
    """Tests for ConsistencyValidator from ai.consistency_validator."""

    def setUp(self):
        self.ConsistencyValidator = _cv_mod.ConsistencyValidator
        self.validator = self.ConsistencyValidator()

    def test_no_contradictions(self):
        """Consistent data returns no contradictions."""
        sections = {
            "terrain": {"flood_risk": "LOW", "construction_suitability": 80},
            "risk": {"flood_risk": "LOW", "overall_risk_score": 20},
            "market": {"demand_level": "MEDIUM", "avg_price_sqft": 9000},
            "infrastructure": {"transit_score": 60, "road_distance_m": 200},
        }
        result = self.validator.validate(sections)
        self.assertFalse(result.has_contradictions)
        self.assertEqual(len(result.contradictions), 0)
        self.assertGreater(result.confidence, 0.7)

    def test_flood_risk_contradiction(self):
        """terrain says LOW, risk says HIGH -> contradiction."""
        sections = {
            "terrain": {"flood_risk": "LOW"},
            "risk": {"flood_risk": "HIGH"},
        }
        result = self.validator.validate(sections)
        self.assertTrue(result.has_contradictions)
        error_contradictions = [c for c in result.contradictions if c.severity == "error"]
        self.assertGreater(len(error_contradictions), 0)
        self.assertIn("flood_risk", error_contradictions[0].field_a)

    def test_high_demand_low_transit(self):
        """High demand + transit_score < 30 -> warning."""
        sections = {
            "market": {"demand_level": "HIGH"},
            "infrastructure": {"transit_score": 20},
        }
        result = self.validator.validate(sections)
        self.assertTrue(result.has_contradictions)
        warning_contradictions = [c for c in result.contradictions if c.severity == "warning"]
        self.assertGreater(len(warning_contradictions), 0)

    def test_high_rise_low_price(self):
        """max_height > 100 + price < 5000 -> warning."""
        sections = {
            "urban_form": {"max_height_m": 120},
            "market": {"avg_price_sqft": 3000},
        }
        result = self.validator.validate(sections)
        self.assertTrue(result.has_contradictions)
        warning_contradictions = [c for c in result.contradictions if c.severity == "warning"]
        self.assertGreater(len(warning_contradictions), 0)

    def test_confidence_calculation(self):
        """Errors reduce confidence."""
        clean_sections = {
            "terrain": {"flood_risk": "LOW"},
            "risk": {"flood_risk": "LOW"},
            "market": {"demand_level": "MEDIUM"},
        }
        dirty_sections = {
            "terrain": {"flood_risk": "LOW"},
            "risk": {"flood_risk": "HIGH"},
            "market": {"demand_level": "HIGH"},
            "infrastructure": {"transit_score": 10},
            "urban_form": {"max_height_m": 150},
        }
        clean_result = self.validator.validate(clean_sections)
        dirty_result = self.validator.validate(dirty_sections)
        self.assertGreater(clean_result.confidence, dirty_result.confidence)

    def test_validation_result_to_dict(self):
        """ValidationResult serialization works."""
        sections = {
            "terrain": {"flood_risk": "LOW"},
            "risk": {"flood_risk": "HIGH"},
        }
        result = self.validator.validate(sections)
        d = result.to_dict()
        self.assertIn("has_contradictions", d)
        self.assertIn("contradictions", d)
        self.assertIn("confidence", d)
        self.assertIn("resolution_summary", d)
        self.assertIsInstance(d["contradictions"], list)


# =============================================================================
# 5. TestSectionPrompts
# =============================================================================

class TestSectionPrompts(unittest.TestCase):
    """Tests for section_prompts_v2 module."""

    def setUp(self):
        self.format_section_prompt = _sp_mod.format_section_prompt
        self.format_synthesis_prompt = _sp_mod.format_synthesis_prompt
        self.SECTION_PROMPT_MAP = _sp_mod.SECTION_PROMPT_MAP

    def test_format_terrain_prompt(self):
        """Terrain prompt fills in elevation, slope, flood_risk."""
        features = {
            "elevation_m": 920.5,
            "slope_degrees": 3.2,
            "flood_risk": "LOW",
            "terrain_classification": "gently sloping",
            "construction_suitability": 85,
            "construction_rating": "Good",
            "construction_notes": "Suitable for mid-rise",
            "cells_analyzed": 10,
        }
        prompt = self.format_section_prompt(
            section_name="terrain",
            lat=12.97,
            lng=77.59,
            features=features,
            data_sources=["terrain_grid:elevation"],
            data_gaps=[],
        )
        self.assertIn("920.5", prompt)
        self.assertIn("3.2", prompt)
        self.assertIn("LOW", prompt)
        self.assertIn("12.97", prompt)

    def test_format_market_prompt(self):
        """Market prompt fills in price, listings."""
        features = {
            "active_listings": 42,
            "avg_price_sqft": 8500,
            "median_price_sqft": 8200,
            "min_price_sqft": 5000,
            "max_price_sqft": 15000,
            "median_price": 7500000,
            "price_momentum_pct": 5.2,
            "demand_level": "HIGH",
        }
        prompt = self.format_section_prompt(
            section_name="market",
            lat=12.97,
            lng=77.59,
            features=features,
            data_sources=["properties_table"],
            data_gaps=[],
        )
        self.assertIn("42", prompt)
        self.assertIn("8500", prompt)
        self.assertIn("HIGH", prompt)

    def test_format_synthesis_prompt(self):
        """Synthesis prompt fills in query, features, evidence."""
        prompt = self.format_synthesis_prompt(
            user_query="Analyze Koramangala",
            features_json='{"terrain": {"elevation_m": 920}}',
            section_results='{"terrain": {"findings": "Good elevation"}}',
            evidence_map='[{"feature": "elevation_m", "source": "terrain_grid"}]',
            validation_result="All sections consistent",
        )
        self.assertIn("Analyze Koramangala", prompt)
        self.assertIn("920", prompt)
        self.assertIn("terrain_grid", prompt)
        self.assertIn("All sections consistent", prompt)

    def test_missing_features_become_na(self):
        """None values become 'N/A' in formatted prompts."""
        features = {
            "elevation_m": None,
            "slope_degrees": None,
            "flood_risk": None,
            "terrain_classification": None,
            "construction_suitability": None,
            "construction_rating": None,
            "construction_notes": None,
            "cells_analyzed": None,
        }
        prompt = self.format_section_prompt(
            section_name="terrain",
            lat=12.97,
            lng=77.59,
            features=features,
        )
        self.assertIn("N/A", prompt)

    def test_section_prompt_map_complete(self):
        """All 5 core sections are in the map."""
        expected = {"terrain", "infrastructure", "market", "urban_form", "risk"}
        actual = set(self.SECTION_PROMPT_MAP.keys())
        self.assertTrue(expected.issubset(actual), f"Missing sections: {expected - actual}")


# =============================================================================
# 6. TestPipelineMetrics
# =============================================================================

class TestPipelineMetrics(unittest.TestCase):
    """Tests for PipelineMetrics from ai.pipeline_metrics."""

    def setUp(self):
        import tempfile
        self.tmp_db = os.path.join(tempfile.mkdtemp(), "test_metrics.db")
        self.pm = _pm_mod.PipelineMetrics(db_path=self.tmp_db)

    def test_record_and_get_stats(self):
        """Record runs and get stats back."""
        self.pm.record_pipeline_run(
            latency_ms=500,
            sections=["terrain", "market"],
            cache_hits=1,
            cache_misses=1,
            model_calls=2,
            tokens_used=1000,
            cost_estimate=0.01,
            confidence_score=0.85,
        )
        stats = self.pm.get_stats(hours=1)
        self.assertEqual(stats["total_runs"], 1)
        self.assertGreater(stats["avg_latency_ms"], 0)
        self.assertEqual(stats["total_cache_hits"], 1)
        self.assertEqual(stats["total_model_calls"], 2)

    def test_cache_hit_rate(self):
        """Record hits/misses and calculate rate."""
        self.pm.record_pipeline_run(
            latency_ms=300, sections=["terrain"],
            cache_hits=7, cache_misses=3,
        )
        rate = self.pm.get_cache_hit_rate(hours=1)
        self.assertAlmostEqual(rate, 70.0, places=1)

    def test_p95_latency(self):
        """Record latencies and get P95."""
        latencies = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        for lat_ms in latencies:
            self.pm.record_pipeline_run(latency_ms=lat_ms, sections=["terrain"])
        p95 = self.pm.get_p95_latency(hours=1)
        self.assertGreaterEqual(p95, 800)


# =============================================================================
# 7. TestDriftDetector
# =============================================================================

class TestDriftDetector(unittest.TestCase):
    """Tests for DriftDetector from ai.drift_detector."""

    def setUp(self):
        import tempfile
        self.tmp_db = os.path.join(tempfile.mkdtemp(), "test_drift.db")
        self.dd = _dd_mod.DriftDetector(db_path=self.tmp_db)
        self.lat = 12.97
        self.lng = 77.59

    def test_record_features(self):
        """Records features without error."""
        self.dd.record_features(
            self.lat, self.lng, "terrain",
            {"elevation_m": 920.0, "slope_degrees": 3.5},
        )
        baselines = self.dd.get_baselines(self.lat, self.lng, "terrain")
        self.assertIn("elevation_m", baselines)
        self.assertIn("slope_degrees", baselines)

    def test_no_drift_small_change(self):
        """Small changes don't trigger alert."""
        for i in range(10):
            self.dd.record_features(
                self.lat, self.lng, "terrain",
                {"elevation_m": 920.0},
            )
        alerts = self.dd.check_drift(
            self.lat, self.lng, "terrain",
            {"elevation_m": 925.0},
        )
        self.assertEqual(len(alerts), 0)

    def test_drift_large_change(self):
        """Large changes trigger alert."""
        for i in range(10):
            self.dd.record_features(
                self.lat, self.lng, "terrain",
                {"elevation_m": 920.0},
            )
        alerts = self.dd.check_drift(
            self.lat, self.lng, "terrain",
            {"elevation_m": 1500.0},
        )
        self.assertGreater(len(alerts), 0)
        self.assertIn("CRITICAL", alerts[0].severity)

    def test_baseline_update(self):
        """Baseline updates with EMA."""
        self.dd.record_features(
            self.lat, self.lng, "market",
            {"avg_price_sqft": 8000.0},
        )
        baselines_before = self.dd.get_baselines(self.lat, self.lng, "market")
        baseline_before = baselines_before["avg_price_sqft"]["baseline_value"]

        self.dd.record_features(
            self.lat, self.lng, "market",
            {"avg_price_sqft": 10000.0},
        )
        baselines_after = self.dd.get_baselines(self.lat, self.lng, "market")
        baseline_after = baselines_after["avg_price_sqft"]["baseline_value"]

        self.assertGreater(baseline_after, baseline_before)
        self.assertLess(baseline_after, 10000.0)


# =============================================================================
# 8. TestReviewFramework
# =============================================================================

class TestReviewFramework(unittest.TestCase):
    """Tests for ReviewQueue from ai.review_framework."""

    def setUp(self):
        import tempfile
        self.tmp_db = os.path.join(tempfile.mkdtemp(), "test_review.db")
        self.queue = _rf_mod.ReviewQueue(db_path=self.tmp_db)
        self.ReviewStatus = _rf_mod.ReviewStatus

    def test_flag_low_confidence(self):
        """Flags items with confidence < 0.6."""
        item = self.queue.flag_for_review(
            query="Test query",
            lat=12.97,
            lng=77.59,
            pipeline_result={"validation": {"low_confidence_sections": []}},
            contradictions=[],
            confidence=0.4,
        )
        self.assertIsNotNone(item)
        self.assertIn("low_confidence", item.flag_reasons[0])

    def test_no_flag_high_confidence(self):
        """Doesn't flag items with confidence > 0.8 and no contradictions."""
        item = self.queue.flag_for_review(
            query="Test query",
            lat=12.97,
            lng=77.59,
            pipeline_result={"validation": {"low_confidence_sections": []}},
            contradictions=[],
            confidence=0.95,
        )
        self.assertIsNone(item)

    def test_approve_review(self):
        """Approval works."""
        item = self.queue.flag_for_review(
            query="Test query",
            lat=12.97,
            lng=77.59,
            pipeline_result={"validation": {"low_confidence_sections": []}},
            contradictions=[],
            confidence=0.4,
        )
        self.assertIsNotNone(item)
        success = self.queue.approve_review(item.review_id, reviewer_notes="Looks good")
        self.assertTrue(success)

    def test_get_pending_reviews(self):
        """Returns pending items."""
        self.queue.flag_for_review(
            query="Query 1", lat=12.97, lng=77.59,
            pipeline_result={"validation": {"low_confidence_sections": []}},
            contradictions=[], confidence=0.3,
        )
        self.queue.flag_for_review(
            query="Query 2", lat=12.97, lng=77.59,
            pipeline_result={"validation": {"low_confidence_sections": []}},
            contradictions=[], confidence=0.2,
        )
        pending = self.queue.get_pending_reviews()
        self.assertEqual(len(pending), 2)
        self.assertEqual(pending[0].status, self.ReviewStatus.PENDING)
        self.assertEqual(pending[1].status, self.ReviewStatus.PENDING)


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    unittest.main()
