"""
Comprehensive testing system for Valora AI Bangalore prompts
Tests all map navigation, property search, and analysis features
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.map_command_processor import MapCommandProcessor
from backend.services.multi_agent_orchestrator import ValoraOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('valora_test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ValoraTestSuite:
    """Comprehensive test suite for Valora AI Bangalore functionality"""
    
    def __init__(self):
        self.map_processor = MapCommandProcessor()
        self.orchestrator = ValoraOrchestrator()
        self.test_results = []
        self.test_categories = {
            "map_navigation": [],
            "property_search": [],
            "investment_analysis": [],
            "buffer_zones": [],
            "area_comparisons": [],
            "market_intelligence": [],
            "specific_use_cases": [],
            "commute_based": [],
            "budget_based": [],
            "geocoding_edge_cases": [],
            "drawing_analysis": []
        }
    
    def log_test_result(self, category: str, prompt: str, result: Dict[str, Any], success: bool):
        """Log test result for analysis"""
        test_entry = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "prompt": prompt,
            "success": success,
            "result": result
        }
        self.test_results.append(test_entry)
        self.test_categories[category].append(test_entry)
        
        # Log to console and file
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} | {category} | {prompt[:50]}...")
        if not success:
            logger.error(f"Failed test details: {json.dumps(result, indent=2)}")
    
    async def test_map_navigation(self):
        """Test map navigation prompts for Bangalore neighborhoods"""
        prompts = [
            "show me whitefield",
            "navigate to koramangala",
            "go to hsr layout",
            "center on marathahalli",
            "show electronic city",
            "go to indiranagar",
            "navigate to hebbal",
            "show btm layout",
            "go to jp nagar",
            "show me sarjapur",
            "navigate to yeshwanthpur",
            "go to yelahanka",
            "show bannerghatta",
            "navigate to jayanagar",
            "show malleshwaram"
        ]
        
        for prompt in prompts:
            try:
                # Test map command parsing
                parsed = self.map_processor.parse_intent(prompt)
                map_action = self.map_processor.generate_map_action(parsed)
                
                success = (
                    parsed.get("command") == "navigate" and
                    map_action is not None and
                    "coordinates" in map_action
                )
                
                self.log_test_result("map_navigation", prompt, {
                    "parsed": parsed,
                    "map_action": map_action
                }, success)
                
            except Exception as e:
                self.log_test_result("map_navigation", prompt, {
                    "error": str(e)
                }, False)
    
    async def test_property_search(self):
        """Test property search prompts"""
        prompts = [
            "find 3bhk apartments in whitefield under 1.5 crore",
            "show 2bhk flats in koramangala for rent",
            "top 10 properties in hsr layout",
            "properties in electronic city under 80 lakhs",
            "luxury apartments in indiranagar above 2 crore",
            "affordable 1bhk in marathahalli",
            "villas in sarjapur road",
            "plots in yelahanka"
        ]
        
        for prompt in prompts:
            try:
                # Test with orchestrator
                response = await self.orchestrator.process_request(
                    user_id="test_user",
                    intent=prompt,
                    context={"test_mode": True}
                )
                
                success = (
                    response.get("plan_id") is not None and
                    response.get("confidence", 0) > 0
                )
                
                self.log_test_result("property_search", prompt, {
                    "plan_id": response.get("plan_id"),
                    "confidence": response.get("confidence"),
                    "has_recommendations": bool(response.get("final_result", {}).get("recommendations"))
                }, success)
                
            except Exception as e:
                self.log_test_result("property_search", prompt, {
                    "error": str(e)
                }, False)
    
    async def test_investment_analysis(self):
        """Test investment analysis prompts"""
        prompts = [
            "analyze investment potential in whitefield",
            "compare whitefield with electronic city",
            "roi analysis for koramangala apartments",
            "which is better investment: hsr layout or marathahalli?",
            "show appreciation trends in sarjapur",
            "rental yield in indiranagar vs koramangala",
            "growth potential of yelahanka"
        ]
        
        for prompt in prompts:
            try:
                response = await self.orchestrator.process_request(
                    user_id="test_user",
                    intent=prompt,
                    context={"test_mode": True}
                )
                
                success = (
                    response.get("final_result", {}).get("forecasts") is not None or
                    response.get("final_result", {}).get("recommendations") is not None
                )
                
                self.log_test_result("investment_analysis", prompt, {
                    "has_forecasts": bool(response.get("final_result", {}).get("forecasts")),
                    "has_recommendations": bool(response.get("final_result", {}).get("recommendations")),
                    "confidence": response.get("confidence")
                }, success)
                
            except Exception as e:
                self.log_test_result("investment_analysis", prompt, {
                    "error": str(e)
                }, False)
    
    async def test_buffer_zones(self):
        """Test buffer zone prompts"""
        prompts = [
            "draw 2km radius around whitefield tech parks",
            "5km buffer around koramangala",
            "show 3km circle around manyata tech park",
            "1km radius around mg road",
            "draw 4km buffer around electronic city phase 1"
        ]
        
        for prompt in prompts:
            try:
                parsed = self.map_processor.parse_intent(prompt)
                map_action = self.map_processor.generate_map_action(parsed)
                
                success = (
                    parsed.get("command") == "draw_buffer" and
                    map_action is not None and
                    "radius" in map_action
                )
                
                self.log_test_result("buffer_zones", prompt, {
                    "parsed": parsed,
                    "map_action": map_action
                }, success)
                
            except Exception as e:
                self.log_test_result("buffer_zones", prompt, {
                    "error": str(e)
                }, False)
    
    async def test_area_comparisons(self):
        """Test area comparison prompts"""
        prompts = [
            "compare whitefield, koramangala and indiranagar",
            "compare east bangalore vs north bangalore",
            "compare btm layout with jp nagar",
            "compare sarjapur with whitefield",
            "hsr layout vs marathahalli comparison"
        ]
        
        for prompt in prompts:
            try:
                parsed = self.map_processor.parse_intent(prompt)
                
                # Also test with orchestrator
                response = await self.orchestrator.process_request(
                    user_id="test_user",
                    intent=prompt,
                    context={"test_mode": True}
                )
                
                success = (
                    parsed.get("command") == "compare" or
                    response.get("confidence", 0) > 0
                )
                
                self.log_test_result("area_comparisons", prompt, {
                    "parsed_command": parsed.get("command"),
                    "orchestrator_confidence": response.get("confidence")
                }, success)
                
            except Exception as e:
                self.log_test_result("area_comparisons", prompt, {
                    "error": str(e)
                }, False)
    
    async def test_geocoding_edge_cases(self):
        """Test geocoding with typos and variations"""
        test_cases = [
            ("show me whitfield", "whitefield"),  # typo
            ("go to koramangla", "koramangala"),  # typo
            ("navigate to blr", "bangalore"),  # synonym
            ("show bangalor", "bangalore")  # typo
        ]
        
        for prompt, expected_location in test_cases:
            try:
                parsed = self.map_processor.parse_intent(prompt)
                location = parsed.get("parameters", {}).get("location", "")
                
                success = (
                    parsed.get("command") == "navigate" and
                    location.lower() == expected_location.lower()
                )
                
                self.log_test_result("geocoding_edge_cases", prompt, {
                    "parsed_location": location,
                    "expected": expected_location,
                    "confidence": parsed.get("confidence", 0)
                }, success)
                
            except Exception as e:
                self.log_test_result("geocoding_edge_cases", prompt, {
                    "error": str(e)
                }, False)
    
    async def test_scenario_flows(self):
        """Test complete scenario flows"""
        scenarios = [
            {
                "name": "First-time homebuyer",
                "prompts": [
                    "I'm looking for my first home in bangalore under 80 lakhs",
                    "show me affordable areas with good connectivity",
                    "what's the average price in marathahalli?",
                    "compare marathahalli with btm layout",
                    "show 2bhk properties in marathahalli"
                ]
            },
            {
                "name": "IT professional relocating",
                "prompts": [
                    "I work in whitefield, show nearby areas",
                    "properties within 5km of whitefield",
                    "what's the commute time from hsr layout to whitefield?",
                    "compare hsr layout with marathahalli for whitefield commute",
                    "show 3bhk rentals near whitefield"
                ]
            },
            {
                "name": "Investor looking for ROI",
                "prompts": [
                    "best investment areas in bangalore for 1 crore budget",
                    "show appreciation trends in electronic city",
                    "compare whitefield and sarjapur for investment",
                    "roi analysis for 3bhk in koramangala",
                    "forecast prices for next 2 years in these areas"
                ]
            }
        ]
        
        for scenario in scenarios:
            logger.info(f"\n=== Testing Scenario: {scenario['name']} ===")
            scenario_results = []
            
            for prompt in scenario["prompts"]:
                try:
                    response = await self.orchestrator.process_request(
                        user_id="test_user",
                        intent=prompt,
                        context={"scenario": scenario["name"]}
                    )
                    
                    success = response.get("confidence", 0) > 0
                    scenario_results.append(success)
                    
                    self.log_test_result("scenario_flow", f"{scenario['name']}: {prompt}", {
                        "confidence": response.get("confidence"),
                        "has_map_action": bool(response.get("map_action")),
                        "has_results": bool(response.get("final_result"))
                    }, success)
                    
                except Exception as e:
                    scenario_results.append(False)
                    self.log_test_result("scenario_flow", f"{scenario['name']}: {prompt}", {
                        "error": str(e)
                    }, False)
            
            # Log scenario summary
            success_rate = sum(scenario_results) / len(scenario_results) * 100 if scenario_results else 0
            logger.info(f"Scenario '{scenario['name']}' success rate: {success_rate:.1f}%")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.test_results),
            "passed": sum(1 for r in self.test_results if r["success"]),
            "failed": sum(1 for r in self.test_results if not r["success"]),
            "categories": {}
        }
        
        for category, results in self.test_categories.items():
            if results:
                passed = sum(1 for r in results if r["success"])
                total = len(results)
                report["categories"][category] = {
                    "total": total,
                    "passed": passed,
                    "failed": total - passed,
                    "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%"
                }
        
        # Calculate overall success rate
        if report["total_tests"] > 0:
            report["overall_success_rate"] = f"{(report['passed']/report['total_tests']*100):.1f}%"
        else:
            report["overall_success_rate"] = "0%"
        
        # Save report to file
        report_file = f"valora_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("VALORA AI TEST REPORT SUMMARY")
        print("="*60)
        print(f"Total Tests: {report['total_tests']}")
        print(f"Passed: {report['passed']} ({report['overall_success_rate']})")
        print(f"Failed: {report['failed']}")
        print("\nCategory Breakdown:")
        for category, stats in report["categories"].items():
            print(f"  {category}: {stats['passed']}/{stats['total']} ({stats['success_rate']})")
        print("="*60)
        print(f"Full report saved to: {report_file}")
        
        return report
    
    async def run_all_tests(self):
        """Run all test categories"""
        logger.info("Starting Valora AI comprehensive test suite...")
        
        # Run each test category
        await self.test_map_navigation()
        await self.test_property_search()
        await self.test_investment_analysis()
        await self.test_buffer_zones()
        await self.test_area_comparisons()
        await self.test_geocoding_edge_cases()
        await self.test_scenario_flows()
        
        # Generate and return report
        return self.generate_report()


async def main():
    """Main test runner"""
    test_suite = ValoraTestSuite()
    report = await test_suite.run_all_tests()
    return report


if __name__ == "__main__":
    # Run tests
    report = asyncio.run(main())
    
    # Exit with appropriate code
    if report["failed"] == 0:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {report['failed']} tests failed")
        sys.exit(1)
