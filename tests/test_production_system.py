"""
Production System Testing Suite
Tests all major functionality of the Valora Real Estate Platform
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any

class ProductionSystemTester:
    """Comprehensive testing for production system"""
    
    def __init__(self, backend_url="http://localhost:8000", frontend_url="http://localhost:3001"):
        self.backend_url = backend_url
        self.frontend_url = frontend_url
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, message: str = "", data: Any = None):
        """Log test result"""
        result = {
            'test': test_name,
            'passed': passed,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        if data:
            result['data'] = data
        
        self.test_results.append(result)
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if message:
            print(f"   {message}")
        if data and not passed:
            print(f"   Error: {data}")
    
    def test_backend_health(self):
        """Test 1: Backend Health Check"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Backend Health Check", True, 
                            f"Status: {data.get('status')}", data)
            else:
                self.log_test("Backend Health Check", False, 
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Backend Health Check", False, 
                        "Backend not accessible", str(e))
    
    def test_market_summary(self):
        """Test 2: Market Summary API"""
        try:
            response = requests.get(f"{self.backend_url}/api/market/summary", timeout=10)
            if response.status_code == 200:
                data = response.json()
                total_props = data.get('total_properties', 0)
                cities = data.get('cities', [])
                self.log_test("Market Summary API", True,
                            f"Total properties: {total_props:,}, Cities: {len(cities)}")
            else:
                self.log_test("Market Summary API", False,
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Market Summary API", False,
                        "API not accessible", str(e))
    
    def test_price_prediction(self):
        """Test 3: Price Prediction"""
        try:
            test_property = {
                "city": "Bangalore",
                "locality": "Koramangala",
                "property_type": "residential_apartment",
                "bedrooms": 3,
                "bathrooms": 2,
                "area_sqft": 1500,
                "floor": 5,
                "total_floors": 10,
                "age_years": 3,
                "parking_spaces": 2
            }
            
            response = requests.post(
                f"{self.backend_url}/api/predict/price",
                json=test_property,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                predicted_price = data.get('predicted_price', 0)
                self.log_test("Price Prediction", True,
                            f"Predicted price: ₹{predicted_price:,.0f}")
            else:
                self.log_test("Price Prediction", False,
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Price Prediction", False,
                        "Prediction failed", str(e))
    
    def test_property_listing(self):
        """Test 4: Property Listing API"""
        try:
            params = {
                "city": "Bangalore",
                "property_type": "residential_apartment",
                "limit": 10
            }
            
            response = requests.get(
                f"{self.backend_url}/api/market/properties",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                properties = data.get('properties', [])
                self.log_test("Property Listing API", True,
                            f"Retrieved {len(properties)} properties")
            else:
                self.log_test("Property Listing API", False,
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Property Listing API", False,
                        "API not accessible", str(e))
    
    def test_market_hotspots(self):
        """Test 5: Market Hotspots API"""
        try:
            params = {"city": "Bangalore"}
            
            response = requests.get(
                f"{self.backend_url}/api/market/hotspots",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                hotspots = data.get('hotspots', [])
                self.log_test("Market Hotspots API", True,
                            f"Found {len(hotspots)} hotspots")
            else:
                self.log_test("Market Hotspots API", False,
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Market Hotspots API", False,
                        "API not accessible", str(e))
    
    def test_price_distribution(self):
        """Test 6: Price Distribution Analytics"""
        try:
            params = {
                "city": "Bangalore",
                "property_type": "residential_apartment"
            }
            
            response = requests.get(
                f"{self.backend_url}/api/analytics/price-distribution",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Price Distribution Analytics", True,
                            "Retrieved price distribution data")
            else:
                self.log_test("Price Distribution Analytics", False,
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Price Distribution Analytics", False,
                        "API not accessible", str(e))
    
    def test_rag_query(self):
        """Test 7: RAG Query (if Pinecone is configured)"""
        try:
            query_data = {
                "query": "best investment properties in Bangalore",
                "top_k": 5,
                "city": "Bangalore"
            }
            
            response = requests.post(
                f"{self.backend_url}/api/rag/query",
                json=query_data,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                self.log_test("RAG Query", True,
                            f"Retrieved {len(matches)} semantic matches")
            else:
                self.log_test("RAG Query", False,
                            f"Status code: {response.status_code} (Pinecone may not be fully indexed yet)")
        except Exception as e:
            self.log_test("RAG Query", False,
                        "RAG not available (Pinecone indexing may be in progress)", str(e))
    
    def test_frontend_access(self):
        """Test 8: Frontend Accessibility"""
        try:
            response = requests.get(self.frontend_url, timeout=5)
            if response.status_code == 200:
                self.log_test("Frontend Access", True,
                            f"Frontend accessible at {self.frontend_url}")
            else:
                self.log_test("Frontend Access", False,
                            f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Frontend Access", False,
                        "Frontend not accessible", str(e))
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("PRODUCTION SYSTEM TEST REPORT")
        print("="*80)
        
        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\nTests Run: {total}")
        print(f"Tests Passed: {passed}")
        print(f"Tests Failed: {total - passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        print("\nTest Details:")
        for result in self.test_results:
            status = "✅" if result['passed'] else "❌"
            print(f"  {status} {result['test']}")
            if result.get('message'):
                print(f"     {result['message']}")
        
        print("\n" + "="*80)
        print("SYSTEM STATUS")
        print("="*80)
        print(f"Backend API: {self.backend_url}")
        print(f"Frontend App: {self.frontend_url}")
        print(f"API Docs: {self.backend_url}/docs")
        
        print("\nKey Features Tested:")
        print("  ✓ Health monitoring")
        print("  ✓ Market data analytics")
        print("  ✓ Price prediction (DMPE)")
        print("  ✓ Property listings")
        print("  ✓ Investment hotspots")
        print("  ✓ Price distribution")
        print("  ✓ Semantic search (RAG)")
        print("  ✓ Frontend UI")
        
        print("\n" + "="*80)
        
        # Save report
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_tests': total,
                    'passed': passed,
                    'failed': total - passed,
                    'success_rate': success_rate
                },
                'results': self.test_results
            }, f, indent=2)
        
        print(f"Detailed report saved to: {report_file}\n")
        
        return success_rate >= 75  # Consider success if 75%+ tests pass
    
    def run_all_tests(self):
        """Run all tests"""
        print("="*80)
        print("STARTING PRODUCTION SYSTEM TESTS")
        print("="*80 + "\n")
        
        # Run tests
        self.test_backend_health()
        self.test_market_summary()
        self.test_price_prediction()
        self.test_property_listing()
        self.test_market_hotspots()
        self.test_price_distribution()
        self.test_rag_query()
        self.test_frontend_access()
        
        # Generate report
        return self.generate_report()


if __name__ == "__main__":
    tester = ProductionSystemTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
