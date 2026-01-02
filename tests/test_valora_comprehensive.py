"""
Comprehensive Testing Engine for Valora AI
Tests all features with Bangalore-focused prompts
"""

import asyncio
import json
import requests
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import pandas as pd
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValoraTestEngine:
    """Comprehensive testing engine for Valora AI"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.node_url = "http://localhost:3001"
        self.test_results = []
        self.passed_tests = 0
        self.failed_tests = 0
        
        # All test prompts organized by category
        self.test_prompts = {
            "map_navigation": [
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
            ],
            "property_search": [
                "find 3bhk apartments in whitefield under 1.5 crore",
                "show 2bhk flats in koramangala for rent",
                "top 10 properties in hsr layout",
                "properties in electronic city under 80 lakhs",
                "luxury apartments in indiranagar above 2 crore",
                "affordable 1bhk in marathahalli",
                "villas in sarjapur road",
                "plots in yelahanka"
            ],
            "investment_analysis": [
                "analyze investment potential in whitefield",
                "compare whitefield with electronic city",
                "roi analysis for koramangala apartments",
                "which is better investment: hsr layout or marathahalli?",
                "show appreciation trends in sarjapur",
                "rental yield in indiranagar vs koramangala",
                "growth potential of yelahanka"
            ],
            "buffer_zones": [
                "draw 2km radius around whitefield tech parks",
                "5km buffer around koramangala",
                "show 3km circle around manyata tech park",
                "1km radius around mg road",
                "draw 4km buffer around electronic city phase 1"
            ],
            "area_comparisons": [
                "compare whitefield, koramangala and indiranagar",
                "compare east bangalore vs north bangalore",
                "compare btm layout with jp nagar",
                "compare sarjapur with whitefield",
                "hsr layout vs marathahalli comparison"
            ],
            "market_intelligence": [
                "show investment hotspots in bangalore",
                "current bangalore apartment prices",
                "bangalore real estate market trends",
                "price distribution for 3bhk in bangalore",
                "top 5 emerging areas in bangalore",
                "bangalore metro impact on property prices"
            ],
            "specific_use_cases": [
                "properties near whitefield railway station",
                "apartments near koramangala metro",
                "properties with good connectivity to electronic city",
                "family-friendly areas near good schools in bangalore",
                "bachelor-friendly pg areas in bangalore",
                "senior citizen apartments in bangalore"
            ],
            "commute_based": [
                "properties within 30 minutes of whitefield tech park",
                "apartments near manyata tech park",
                "housing near electronic city phase 2",
                "properties along outer ring road",
                "apartments near sarjapur road IT companies"
            ],
            "budget_based": [
                "affordable areas in bangalore under 50 lakhs",
                "mid-range properties 70-90 lakhs in bangalore",
                "premium apartments in bangalore above 1.5 crore",
                "cheapest 2bhk in bangalore",
                "luxury properties in north bangalore"
            ],
            "geocoding_edge_cases": [
                "show me whitfield",  # typo
                "go to koramangla",  # typo
                "navigate to blr",  # synonym
                "show bangalor"  # typo
            ]
        }
        
        # Test scenarios
        self.test_scenarios = {
            "first_time_buyer": [
                "I'm looking for my first home in bangalore under 80 lakhs",
                "show me affordable areas with good connectivity",
                "what's the average price in marathahalli?",
                "compare marathahalli with btm layout",
                "show 2bhk properties in marathahalli"
            ],
            "it_professional": [
                "I work in whitefield, show nearby areas",
                "properties within 5km of whitefield",
                "what's the commute time from hsr layout to whitefield?",
                "compare hsr layout with marathahalli for whitefield commute",
                "show 3bhk rentals near whitefield"
            ],
            "investor": [
                "best investment areas in bangalore for 1 crore budget",
                "show appreciation trends in electronic city",
                "compare whitefield and sarjapur for investment",
                "roi analysis for 3bhk in koramangala",
                "forecast prices for next 2 years in these areas"
            ],
            "luxury_buyer": [
                "luxury apartments in bangalore above 2 crore",
                "show me premium areas in north bangalore",
                "properties in indiranagar with modern amenities",
                "villas in whitefield above 3 crore",
                "compare indiranagar with koramangala for luxury living"
            ]
        }
    
    def test_health_endpoints(self):
        """Test if all services are healthy"""
        print(f"\n{Fore.CYAN}=== Testing Health Endpoints ==={Style.RESET_ALL}")
        
        endpoints = [
            (f"{self.base_url}/health", "FastAPI Backend"),
            (f"{self.node_url}/api/health", "Node.js Server"),
            (f"{self.base_url}/api/maps/health", "Maps Service")
        ]
        
        for endpoint, name in endpoints:
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    self._log_pass(f"{name} is healthy")
                else:
                    self._log_fail(f"{name} returned status {response.status_code}")
            except Exception as e:
                self._log_fail(f"{name} is not reachable: {e}")
    
    def test_geocoding(self):
        """Test geocoding endpoints"""
        print(f"\n{Fore.CYAN}=== Testing Geocoding ==={Style.RESET_ALL}")
        
        locations = ["whitefield", "koramangala", "hsr layout", "whitfield", "koramangla", "blr"]
        
        for location in locations:
            try:
                response = requests.get(
                    f"{self.base_url}/api/maps/geocode",
                    params={"address": location},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('coordinates'):
                        self._log_pass(f"Geocoded '{location}': {data['coordinates']}")
                    else:
                        self._log_fail(f"No coordinates for '{location}'")
                else:
                    self._log_fail(f"Geocoding failed for '{location}'")
            except Exception as e:
                self._log_fail(f"Geocoding error for '{location}': {e}")
    
    def test_chat_api(self):
        """Test chat API with various prompts"""
        print(f"\n{Fore.CYAN}=== Testing Chat API ==={Style.RESET_ALL}")
        
        # Test sample prompts from each category
        test_messages = [
            "show me whitefield",
            "find 3bhk apartments in koramangala",
            "analyze investment potential in hsr layout",
            "compare whitefield with electronic city"
        ]
        
        for message in test_messages:
            try:
                response = requests.post(
                    f"{self.node_url}/api/chat",
                    json={"message": message, "history": []},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('message'):
                        self._log_pass(f"Chat responded to: '{message[:50]}...'")
                    else:
                        self._log_fail(f"Empty response for: '{message[:50]}...'")
                else:
                    self._log_fail(f"Chat failed for: '{message[:50]}...'")
            except Exception as e:
                self._log_fail(f"Chat error: {e}")
    
    def test_market_api(self):
        """Test market analysis endpoints"""
        print(f"\n{Fore.CYAN}=== Testing Market APIs ==={Style.RESET_ALL}")
        
        endpoints = [
            "/api/market/summary",
            "/api/market/trends?locality=Whitefield",
            "/api/market/compare?area1=Koramangala&area2=HSR Layout"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        self._log_pass(f"Market API {endpoint} working")
                    else:
                        self._log_fail(f"Empty response from {endpoint}")
                else:
                    self._log_fail(f"Market API {endpoint} failed")
            except Exception as e:
                self._log_fail(f"Market API error {endpoint}: {e}")
    
    def test_property_search(self):
        """Test property search functionality"""
        print(f"\n{Fore.CYAN}=== Testing Property Search ==={Style.RESET_ALL}")
        
        searches = [
            {"locality": "Whitefield", "min_price": 5000000, "max_price": 15000000},
            {"bedrooms": 3, "property_type": "residential_apartment"},
            {"listing_type": "rent", "max_price": 50000}
        ]
        
        for search_params in searches:
            try:
                response = requests.get(
                    f"{self.base_url}/api/properties/search",
                    params=search_params,
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._log_pass(f"Property search successful: {search_params}")
                else:
                    self._log_fail(f"Property search failed: {search_params}")
            except Exception as e:
                self._log_fail(f"Property search error: {e}")
    
    def test_multi_agent_system(self):
        """Test multi-agent orchestration"""
        print(f"\n{Fore.CYAN}=== Testing Multi-Agent System ==={Style.RESET_ALL}")
        
        queries = [
            "analyze investment in whitefield",
            "compare koramangala and hsr layout",
            "forecast prices in electronic city"
        ]
        
        for query in queries:
            try:
                response = requests.post(
                    f"{self.base_url}/api/agent/plan",
                    json={"intent": query, "context": {}, "user_id": "test_user"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('plan'):
                        self._log_pass(f"Multi-agent handled: '{query[:40]}...'")
                    else:
                        self._log_fail(f"No plan generated for: '{query[:40]}...'")
                else:
                    self._log_fail(f"Multi-agent failed for: '{query[:40]}...'")
            except Exception as e:
                self._log_fail(f"Multi-agent error: {e}")
    
    def test_all_prompts_batch(self):
        """Test all prompts in batch mode"""
        print(f"\n{Fore.CYAN}=== Batch Testing All Prompts ==={Style.RESET_ALL}")
        
        total_prompts = sum(len(prompts) for prompts in self.test_prompts.values())
        tested = 0
        
        for category, prompts in self.test_prompts.items():
            print(f"\n{Fore.YELLOW}Testing {category}:{Style.RESET_ALL}")
            
            for prompt in prompts[:3]:  # Test first 3 from each category to save time
                tested += 1
                
                try:
                    # Quick validation - just check if the prompt is understood
                    response = requests.post(
                        f"{self.node_url}/api/chat",
                        json={"message": prompt, "history": []},
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        self._log_pass(f"✓ {prompt[:50]}")
                    else:
                        self._log_fail(f"✗ {prompt[:50]}")
                except:
                    self._log_fail(f"✗ {prompt[:50]}")
                
                time.sleep(0.5)  # Rate limiting
        
        print(f"\n{Fore.GREEN}Tested {tested} prompts out of {total_prompts} total{Style.RESET_ALL}")
    
    def test_scenarios(self):
        """Test complete user scenarios"""
        print(f"\n{Fore.CYAN}=== Testing User Scenarios ==={Style.RESET_ALL}")
        
        for scenario_name, messages in self.test_scenarios.items():
            print(f"\n{Fore.YELLOW}Scenario: {scenario_name}{Style.RESET_ALL}")
            
            history = []
            scenario_passed = True
            
            for message in messages:
                try:
                    response = requests.post(
                        f"{self.node_url}/api/chat",
                        json={"message": message, "history": history},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Check if data has a message
                        response_text = data.get('message', '') if isinstance(data, dict) else str(data)
                        history.append({"role": "user", "content": message})
                        history.append({"role": "assistant", "content": response_text})
                        print(f"  ✓ {message[:60]}")
                    else:
                        print(f"  ✗ {message[:60]}")
                        scenario_passed = False
                except Exception as e:
                    print(f"  ✗ {message[:60]} - Error: {e}")
                    scenario_passed = False
                
                time.sleep(1)  # Rate limiting
            
            if scenario_passed:
                self._log_pass(f"Scenario '{scenario_name}' completed")
            else:
                self._log_fail(f"Scenario '{scenario_name}' had failures")
    
    def _log_pass(self, message: str):
        """Log a passing test"""
        print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")
        self.passed_tests += 1
        self.test_results.append({"status": "pass", "message": message})
    
    def _log_fail(self, message: str):
        """Log a failing test"""
        print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")
        self.failed_tests += 1
        self.test_results.append({"status": "fail", "message": message})
    
    def generate_report(self):
        """Generate test report"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}VALORA AI TEST REPORT{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"{Fore.GREEN}Passed: {self.passed_tests}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {self.failed_tests}{Style.RESET_ALL}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        
        if self.failed_tests > 0:
            print(f"\n{Fore.YELLOW}Failed Tests:{Style.RESET_ALL}")
            for result in self.test_results:
                if result['status'] == 'fail':
                    print(f"  - {result['message']}")
        
        # Save report to file
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed": self.passed_tests,
            "failed": self.failed_tests,
            "pass_rate": pass_rate,
            "results": self.test_results
        }
        
        with open("test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{Fore.CYAN}Report saved to test_report.json{Style.RESET_ALL}")
    
    def run_all_tests(self):
        """Run complete test suite"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}VALORA AI COMPREHENSIVE TEST SUITE{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        start_time = time.time()
        
        # Run all test categories
        self.test_health_endpoints()
        self.test_geocoding()
        self.test_chat_api()
        self.test_market_api()
        self.test_property_search()
        self.test_multi_agent_system()
        self.test_all_prompts_batch()
        self.test_scenarios()
        
        # Generate report
        elapsed_time = time.time() - start_time
        print(f"\n{Fore.CYAN}Test suite completed in {elapsed_time:.2f} seconds{Style.RESET_ALL}")
        
        self.generate_report()


def main():
    """Main test runner"""
    tester = ValoraTestEngine()
    
    # Check if services are running
    print(f"{Fore.YELLOW}Checking if services are running...{Style.RESET_ALL}")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            print(f"{Fore.RED}FastAPI backend is not running. Start it first!{Style.RESET_ALL}")
            return
    except:
        print(f"{Fore.RED}FastAPI backend is not running. Start it first!{Style.RESET_ALL}")
        print("Run: cd backend && python -m uvicorn api.main:app --reload")
        return
    
    try:
        response = requests.get("http://localhost:3001/api/health", timeout=2)
        if response.status_code != 200:
            print(f"{Fore.RED}Node.js server is not running. Start it first!{Style.RESET_ALL}")
            return
    except:
        print(f"{Fore.RED}Node.js server is not running. Start it first!{Style.RESET_ALL}")
        print("Run: node server.js")
        return
    
    print(f"{Fore.GREEN}All services are running. Starting tests...{Style.RESET_ALL}")
    
    # Run all tests
    tester.run_all_tests()


if __name__ == "__main__":
    main()
