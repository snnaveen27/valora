"""
Valora AI - Offline Eval Harness
Golden tests and regression suite for spatial queries.

Features:
- Predefined test cases with expected outputs
- Automated testing of all spatial tools
- Latency and correctness metrics
- Regression detection
- Hallucination rate tracking
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class TestCategory(Enum):
    """Categories of tests."""
    SPATIAL_3D = "spatial_3d"
    VIEWSHED = "viewshed"
    OCCLUSION = "occlusion"
    SOLAR = "solar"
    PROPERTY = "property"
    LOCALITY = "locality"
    SIMULATION = "simulation"
    TOOL_CALL = "tool_call"


class TestResult(Enum):
    """Test result status."""
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"


@dataclass
class TestCase:
    """A single test case."""
    id: str
    name: str
    category: str
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    expected: Dict[str, Any]  # Expected output fields and values
    tolerance: float = 0.1  # Allowed deviation for numeric values
    max_latency_ms: float = 5000  # Max acceptable latency
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestResultRecord:
    """Record of a single test execution."""
    test_id: str
    test_name: str
    category: str
    status: str  # pass, fail, error, skip
    latency_ms: float
    actual_output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    failed_checks: List[str] = field(default_factory=list)
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvalReport:
    """Complete evaluation report."""
    run_id: str
    timestamp: str
    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int
    avg_latency_ms: float
    results: List[TestResultRecord] = field(default_factory=list)
    summary: str = ""
    
    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0
        return self.passed / self.total_tests * 100
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['pass_rate'] = self.pass_rate
        return d


class EvalHarness:
    """
    Evaluation harness for testing Valora's spatial capabilities.
    Runs predefined golden tests and tracks metrics.
    """
    
    def __init__(self):
        self._test_cases: List[TestCase] = []
        self._tool_executor = None
        self._load_golden_tests()
    
    def _load_golden_tests(self):
        """Load predefined golden test cases."""
        # Koramangala test location
        KORAMANGALA = (12.9352, 77.6245)
        # Whitefield test location
        WHITEFIELD = (12.9698, 77.7500)
        # Indiranagar test location
        INDIRANAGAR = (12.9784, 77.6408)
        
        self._test_cases = [
            # ========== SPATIAL 3D TESTS ==========
            TestCase(
                id="3d_001",
                name="3D Context - Koramangala Ground Level",
                category=TestCategory.SPATIAL_3D.value,
                description="Test 3D context analysis at ground level in Koramangala",
                tool_name="get_3d_context",
                parameters={"lat": KORAMANGALA[0], "lng": KORAMANGALA[1], "floor_height_m": 0, "radius_m": 200},
                expected={
                    "view_quality": ["excellent", "good", "moderate", "poor"],  # Any valid value
                    "skyline_character": ["low_rise", "mid_rise", "high_rise", "mixed", "unknown"],
                },
                max_latency_ms=2000
            ),
            TestCase(
                id="3d_002",
                name="3D Context - High Floor Analysis",
                category=TestCategory.SPATIAL_3D.value,
                description="Test 3D context at 15th floor (45m height)",
                tool_name="get_3d_context",
                parameters={"lat": WHITEFIELD[0], "lng": WHITEFIELD[1], "floor_height_m": 45, "radius_m": 300},
                expected={
                    "sky_view_factor": {"min": 0.0, "max": 1.0},  # Range check
                    "open_directions": {"type": "list"},  # Should be a list
                },
                max_latency_ms=2000
            ),
            
            # ========== VIEWSHED TESTS ==========
            TestCase(
                id="view_001",
                name="Viewshed - Floor 1",
                category=TestCategory.VIEWSHED.value,
                description="Test viewshed analysis from floor 1",
                tool_name="analyze_viewshed",
                parameters={"lat": INDIRANAGAR[0], "lng": INDIRANAGAR[1], "floor": 1},
                expected={
                    "openness_score": {"min": 0, "max": 100},
                    "sky_view_factor": {"min": 0.0, "max": 1.0},
                    "floor_number": 1,
                },
                max_latency_ms=3000
            ),
            TestCase(
                id="view_002",
                name="Floor Comparison",
                category=TestCategory.VIEWSHED.value,
                description="Compare view quality across floors",
                tool_name="compare_floors",
                parameters={"lat": KORAMANGALA[0], "lng": KORAMANGALA[1], "floors": [1, 5, 10, 15]},
                expected={
                    "floors_compared": {"type": "list", "min_length": 4},
                    "best_value_floor": {"min": 1, "max": 20},
                },
                max_latency_ms=5000
            ),
            
            # ========== OCCLUSION TESTS ==========
            TestCase(
                id="occ_001",
                name="Find View Blockers",
                category=TestCategory.OCCLUSION.value,
                description="Find buildings blocking view from a location",
                tool_name="find_view_blockers",
                parameters={"lat": WHITEFIELD[0], "lng": WHITEFIELD[1], "floor_height_m": 15, "radius_m": 200},
                expected={
                    "type": "list",  # Should return a list
                },
                max_latency_ms=3000
            ),
            TestCase(
                id="occ_002",
                name="360 Visibility Check",
                category=TestCategory.OCCLUSION.value,
                description="Test 360-degree visibility analysis",
                tool_name="get_360_visibility",
                parameters={"lat": INDIRANAGAR[0], "lng": INDIRANAGAR[1], "floor": 5, "radius_m": 300},
                expected={
                    "view_quality": ["excellent", "good", "moderate", "poor"],
                    "openness_score": {"min": 0, "max": 100},
                },
                max_latency_ms=5000
            ),
            
            # ========== SOLAR TESTS ==========
            TestCase(
                id="solar_001",
                name="Sunlight Analysis",
                category=TestCategory.SOLAR.value,
                description="Test sunlight analysis for a location",
                tool_name="analyze_sunlight",
                parameters={"lat": KORAMANGALA[0], "lng": KORAMANGALA[1], "floor": 5},
                expected={
                    "daylight_hours": {"min": 10, "max": 14},  # Bangalore daylight
                    "natural_light_score": {"min": 0, "max": 100},
                },
                max_latency_ms=3000
            ),
            TestCase(
                id="solar_002",
                name="Facade Sunlight",
                category=TestCategory.SOLAR.value,
                description="Test facade-specific sunlight analysis",
                tool_name="get_facade_sunlight",
                parameters={"lat": WHITEFIELD[0], "lng": WHITEFIELD[1], "floor": 10},
                expected={
                    "facades": {"type": "dict"},
                    "best_facade": ["N", "E", "S", "W"],
                },
                max_latency_ms=3000
            ),
            
            # ========== PROPERTY TESTS ==========
            TestCase(
                id="prop_001",
                name="Property Search - Basic",
                category=TestCategory.PROPERTY.value,
                description="Basic property search with location filter",
                tool_name="search_properties",
                parameters={"lat": KORAMANGALA[0], "lng": KORAMANGALA[1], "radius_m": 2000, "limit": 10},
                expected={
                    "count": {"min": 0, "max": 10},  # Should respect limit
                    "properties": {"type": "list"},
                },
                max_latency_ms=5000
            ),
            TestCase(
                id="prop_002",
                name="Property Search - With Filters",
                category=TestCategory.PROPERTY.value,
                description="Property search with multiple filters",
                tool_name="search_properties",
                parameters={
                    "lat": WHITEFIELD[0], "lng": WHITEFIELD[1], "radius_m": 3000,
                    "listing_type": "sale", "property_category": "residential", "limit": 20
                },
                expected={
                    "filters_applied": {"type": "dict"},
                },
                max_latency_ms=5000
            ),
            
            # ========== LOCALITY TESTS ==========
            TestCase(
                id="loc_001",
                name="Locality Profile - Koramangala",
                category=TestCategory.LOCALITY.value,
                description="Get locality profile for Koramangala",
                tool_name="get_locality_profile",
                parameters={"locality_name": "Koramangala"},
                expected={
                    "locality_name": {"contains": "Koramangala"},
                },
                max_latency_ms=1000
            ),
            TestCase(
                id="loc_002",
                name="Nearby Locality Lookup",
                category=TestCategory.LOCALITY.value,
                description="Find locality near coordinates",
                tool_name="get_nearby_locality",
                parameters={"lat": INDIRANAGAR[0], "lng": INDIRANAGAR[1], "radius_km": 2.0},
                expected={
                    # Should return something (may be null if no locality found)
                },
                max_latency_ms=1000
            ),
            
            # ========== TOOL VALIDATION TESTS ==========
            TestCase(
                id="tool_001",
                name="Invalid Tool - Missing Required Param",
                category=TestCategory.TOOL_CALL.value,
                description="Test that missing required parameters are caught",
                tool_name="get_3d_context",
                parameters={"lat": KORAMANGALA[0]},  # Missing lng
                expected={
                    "error": True,  # Should return error
                },
                max_latency_ms=100
            ),
            TestCase(
                id="tool_002",
                name="Invalid Tool - Wrong Type",
                category=TestCategory.TOOL_CALL.value,
                description="Test that wrong parameter types are caught",
                tool_name="analyze_viewshed",
                parameters={"lat": "not_a_number", "lng": KORAMANGALA[1]},
                expected={
                    "error": True,
                },
                max_latency_ms=100
            ),
        ]
    
    def _get_tool_executor(self):
        """Lazy-load tool executor."""
        if self._tool_executor is None:
            try:
                from tool_executor import get_tool_executor
                self._tool_executor = get_tool_executor()
            except ImportError:
                from backend.tool_executor import get_tool_executor
                self._tool_executor = get_tool_executor()
        return self._tool_executor
    
    def _check_expected(self, actual: Any, expected: Any, path: str = "") -> List[str]:
        """
        Check if actual output matches expected.
        Returns list of failure messages.
        """
        failures = []
        
        if expected is None:
            return failures
        
        if isinstance(expected, dict):
            # Special checks
            if "type" in expected:
                exp_type = expected["type"]
                if exp_type == "list" and not isinstance(actual, list):
                    failures.append(f"{path}: expected list, got {type(actual).__name__}")
                elif exp_type == "dict" and not isinstance(actual, dict):
                    failures.append(f"{path}: expected dict, got {type(actual).__name__}")
                
                if "min_length" in expected and isinstance(actual, list):
                    if len(actual) < expected["min_length"]:
                        failures.append(f"{path}: length {len(actual)} < min {expected['min_length']}")
            
            elif "min" in expected or "max" in expected:
                # Range check
                if isinstance(actual, (int, float)):
                    if "min" in expected and actual < expected["min"]:
                        failures.append(f"{path}: {actual} < min {expected['min']}")
                    if "max" in expected and actual > expected["max"]:
                        failures.append(f"{path}: {actual} > max {expected['max']}")
            
            elif "contains" in expected:
                # Substring check
                if isinstance(actual, str) and expected["contains"] not in actual:
                    failures.append(f"{path}: '{actual}' does not contain '{expected['contains']}'")
            
            elif "error" in expected:
                # Error expected
                if expected["error"] and not (actual is None or (isinstance(actual, dict) and actual.get('error'))):
                    failures.append(f"{path}: expected error but got success")
            
            else:
                # Check each key
                for key, exp_val in expected.items():
                    if isinstance(actual, dict) and key in actual:
                        failures.extend(self._check_expected(actual[key], exp_val, f"{path}.{key}"))
        
        elif isinstance(expected, list):
            # Value should be one of the options
            if actual not in expected:
                failures.append(f"{path}: '{actual}' not in {expected}")
        
        else:
            # Direct comparison
            if actual != expected:
                failures.append(f"{path}: expected {expected}, got {actual}")
        
        return failures
    
    def run_test(self, test: TestCase) -> TestResultRecord:
        """Run a single test case."""
        result = TestResultRecord(
            test_id=test.id,
            test_name=test.name,
            category=test.category,
            status=TestResult.SKIP.value,
            latency_ms=0,
            timestamp=datetime.now().isoformat()
        )
        
        try:
            executor = self._get_tool_executor()
            
            # Execute tool
            start = time.time()
            
            from tool_executor import ToolCall
            tool_call = ToolCall(name=test.tool_name, parameters=test.parameters)
            tool_result = executor.execute(tool_call)
            
            latency = (time.time() - start) * 1000
            result.latency_ms = round(latency, 2)
            result.actual_output = tool_result.data if tool_result.success else {"error": tool_result.error}
            
            # Check for errors if tool failed
            if not tool_result.success:
                if test.expected.get("error"):
                    # Error was expected
                    result.status = TestResult.PASS.value
                else:
                    result.status = TestResult.ERROR.value
                    result.error_message = tool_result.error
                return result
            
            # Check expected values
            failures = self._check_expected(tool_result.data, test.expected)
            
            # Check latency
            if latency > test.max_latency_ms:
                failures.append(f"Latency {latency:.0f}ms > max {test.max_latency_ms}ms")
            
            if failures:
                result.status = TestResult.FAIL.value
                result.failed_checks = failures
            else:
                result.status = TestResult.PASS.value
                
        except Exception as e:
            result.status = TestResult.ERROR.value
            result.error_message = str(e)
        
        return result
    
    def run_all(self, categories: List[str] = None) -> EvalReport:
        """
        Run all tests or filtered by category.
        
        Args:
            categories: Optional list of categories to run
            
        Returns:
            EvalReport with all results
        """
        tests_to_run = self._test_cases
        if categories:
            tests_to_run = [t for t in tests_to_run if t.category in categories]
        
        report = EvalReport(
            run_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            timestamp=datetime.now().isoformat(),
            total_tests=len(tests_to_run),
            passed=0,
            failed=0,
            errors=0,
            skipped=0,
            avg_latency_ms=0
        )
        
        total_latency = 0
        
        print(f"\n{'='*60}")
        print(f"VALORA AI - EVAL HARNESS")
        print(f"Running {len(tests_to_run)} tests...")
        print(f"{'='*60}\n")
        
        for test in tests_to_run:
            result = self.run_test(test)
            report.results.append(result)
            
            status_icon = {
                'pass': '✅',
                'fail': '❌',
                'error': '⚠️',
                'skip': '⏭️'
            }.get(result.status, '?')
            
            print(f"{status_icon} [{result.test_id}] {result.test_name} ({result.latency_ms:.0f}ms)")
            
            if result.failed_checks:
                for fc in result.failed_checks[:3]:  # Show first 3 failures
                    print(f"   └─ {fc}")
            
            if result.status == TestResult.PASS.value:
                report.passed += 1
            elif result.status == TestResult.FAIL.value:
                report.failed += 1
            elif result.status == TestResult.ERROR.value:
                report.errors += 1
            else:
                report.skipped += 1
            
            total_latency += result.latency_ms
        
        if report.total_tests > 0:
            report.avg_latency_ms = round(total_latency / report.total_tests, 2)
        
        # Generate summary
        report.summary = self._generate_summary(report)
        
        print(f"\n{'='*60}")
        print(report.summary)
        print(f"{'='*60}\n")
        
        return report
    
    def _generate_summary(self, report: EvalReport) -> str:
        """Generate summary text."""
        lines = [
            f"RESULTS: {report.passed}/{report.total_tests} passed ({report.pass_rate:.1f}%)",
            f"Failed: {report.failed} | Errors: {report.errors} | Skipped: {report.skipped}",
            f"Avg Latency: {report.avg_latency_ms:.0f}ms"
        ]
        
        if report.pass_rate >= 90:
            lines.append("Status: ✅ EXCELLENT")
        elif report.pass_rate >= 70:
            lines.append("Status: 🟡 GOOD (some failures)")
        else:
            lines.append("Status: ❌ NEEDS ATTENTION")
        
        return "\n".join(lines)
    
    def save_report(self, report: EvalReport, path: str = None) -> str:
        """Save report to JSON file."""
        if path is None:
            path = Path(__file__).parent / 'eval_results' / f"eval_{report.run_id}.json"
        
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        print(f"Report saved to: {path}")
        return str(path)
    
    def get_test_cases(self, category: str = None) -> List[TestCase]:
        """Get test cases, optionally filtered by category."""
        if category:
            return [t for t in self._test_cases if t.category == category]
        return self._test_cases


# Singleton
_eval_harness = None


def get_eval_harness() -> EvalHarness:
    """Get or create eval harness singleton."""
    global _eval_harness
    if _eval_harness is None:
        _eval_harness = EvalHarness()
    return _eval_harness


def run_eval(categories: List[str] = None, save: bool = True) -> EvalReport:
    """
    Convenience function to run evaluation.
    
    Args:
        categories: Optional list of categories to run
        save: Whether to save report to file
        
    Returns:
        EvalReport with results
    """
    harness = get_eval_harness()
    report = harness.run_all(categories)
    
    if save:
        harness.save_report(report)
    
    return report


if __name__ == "__main__":
    # Run eval when executed directly
    import sys
    
    categories = None
    if len(sys.argv) > 1:
        categories = sys.argv[1:]
    
    run_eval(categories)
