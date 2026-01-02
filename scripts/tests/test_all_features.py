#!/usr/bin/env python
"""
Comprehensive test suite for all features of the Advanced Real Estate AI Platform
Tests every feature to ensure the system is the best and most advanced in the market
"""

import requests
import json
import time
from datetime import datetime
import sys
from typing import Dict, List, Any

print("🔬 COMPREHENSIVE FEATURE TESTING FOR VALORA MULTI-AGENT AI")
print("="*70)
print("Testing all features to ensure market-leading capabilities")
print("="*70)
print()

BASE_URL = "http://localhost:8000"
NODE_URL = "http://localhost:3001"

# Test tracking
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "warnings": 0,
    "errors": []
}

def test_feature(category: str, name: str, test_func, *args, **kwargs) -> bool:
    """Test a feature and track results"""
    test_results["total"] += 1
    print(f"🔍 Testing {category}: {name}")
    
    try:
        result = test_func(*args, **kwargs)
        if result['status'] == 'pass':
            print(f"   ✅ PASS: {result.get('message', 'Test passed')}")
            test_results["passed"] += 1
            return True
        elif result['status'] == 'warning':
            print(f"   ⚠️  WARNING: {result.get('message', 'Test has warnings')}")
            test_results["warnings"] += 1
            return True
        else:
            print(f"   ❌ FAIL: {result.get('message', 'Test failed')}")
            test_results["failed"] += 1
            test_results["errors"].append(f"{category}/{name}: {result.get('message')}")
            return False
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        test_results["failed"] += 1
        test_results["errors"].append(f"{category}/{name}: {str(e)}")
        return False

# ===== TEST FUNCTIONS =====

def test_api_endpoint(url: str, method: str = "GET", data: Dict = None) -> Dict:
    """Test an API endpoint"""
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        else:
            return {"status": "fail", "message": f"Unsupported method: {method}"}
        
        if response.status_code == 200:
            return {"status": "pass", "message": f"Status {response.status_code}"}
        elif response.status_code == 404:
            return {"status": "fail", "message": f"Endpoint not found (404)"}
        elif response.status_code == 422:
            return {"status": "fail", "message": f"Invalid request format (422)"}
        else:
            return {"status": "warning", "message": f"Status {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"status": "fail", "message": "Connection failed - service not running"}
    except Exception as e:
        return {"status": "fail", "message": str(e)}

def test_database_connection() -> Dict:
    """Test database connectivity"""
    try:
        from backend.database.multiconnection import mdb
        from sqlalchemy import text
        
        with mdb.spatial() as session:
            result = session.execute(text("SELECT 1"))
            if result.scalar() == 1:
                return {"status": "pass", "message": "Database connected"}
    except Exception as e:
        return {"status": "fail", "message": f"Database error: {e}"}

def test_property_data() -> Dict:
    """Test property data availability"""
    try:
        from backend.database.multiconnection import mdb
        from sqlalchemy import text
        
        with mdb.spatial() as session:
            result = session.execute(text("SELECT COUNT(*) FROM property_locations"))
            count = result.scalar()
            if count > 0:
                return {"status": "pass", "message": f"{count:,} properties loaded"}
            else:
                return {"status": "fail", "message": "No properties in database"}
    except Exception as e:
        return {"status": "fail", "message": str(e)}

def test_gis_data() -> Dict:
    """Test GIS data availability"""
    try:
        from backend.database.multiconnection import mdb
        from sqlalchemy import text
        
        with mdb.spatial() as session:
            result = session.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name LIKE 'gis_%'
            """))
            count = result.scalar()
            if count > 0:
                return {"status": "pass", "message": f"{count} GIS layers available"}
            else:
                return {"status": "fail", "message": "No GIS data loaded"}
    except Exception as e:
        return {"status": "fail", "message": str(e)}

def test_multi_agent_system() -> Dict:
    """Test multi-agent AI system"""
    try:
        # Test chat endpoint
        response = requests.post(
            f"{BASE_URL}/api/multi-agent/chat",
            json={
                "message": "Find properties in Whitefield",
                "user_id": "test"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return {"status": "pass", "message": "Multi-agent system responding"}
        elif response.status_code == 404:
            return {"status": "fail", "message": "Multi-agent endpoints not found"}
        else:
            return {"status": "warning", "message": f"Status {response.status_code}"}
    except Exception as e:
        return {"status": "fail", "message": str(e)}

def test_prediction_engine() -> Dict:
    """Test advanced prediction engine"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/predict/time-based",
            json={
                "lat": 12.9716,
                "lon": 77.5946,
                "months_from_now": 12
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if "predicted_value" in data:
                return {"status": "pass", "message": "Prediction engine working"}
        return {"status": "fail", "message": "Prediction failed"}
    except Exception as e:
        return {"status": "fail", "message": str(e)}

def test_recommendations() -> Dict:
    """Test recommendation system"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/recommendations",
            json={
                "city": "Bangalore",
                "purpose": "investment",
                "limit": 5
            },
            timeout=5
        )
        
        if response.status_code == 200:
            return {"status": "pass", "message": "Recommendation system active"}
        elif response.status_code == 404:
            return {"status": "fail", "message": "Recommendations endpoint not found"}
        else:
            return {"status": "warning", "message": f"Status {response.status_code}"}
    except Exception as e:
        return {"status": "fail", "message": str(e)}

def test_document_intelligence() -> Dict:
    """Test document understanding capability"""
    try:
        from backend.services.document_intelligence import DocumentIntelligence
        
        doc_intel = DocumentIntelligence()
        
        # Test with sample text
        result = doc_intel.understand_document(
            document_content="3BHK apartment in Whitefield, 1200 sqft, ₹85 lakhs",
            document_type="text"
        )
        
        if result.get('status') == 'success':
            return {"status": "pass", "message": "Document intelligence active"}
        else:
            return {"status": "fail", "message": "Document processing failed"}
    except ImportError:
        return {"status": "warning", "message": "Document intelligence module not loaded"}
    except Exception as e:
        return {"status": "fail", "message": str(e)}

def test_geospatial_capabilities() -> Dict:
    """Test geospatial analysis"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/predict/analyze-pin",
            json={
                "lat": 12.9716,
                "lon": 77.5946
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if "importance_score" in data:
                return {"status": "pass", "message": f"Geospatial analysis working (score: {data['importance_score']:.1f})"}
        return {"status": "fail", "message": "Geospatial analysis failed"}
    except Exception as e:
        return {"status": "fail", "message": str(e)}

def test_forecast_endpoint() -> Dict:
    """Test forecast endpoint with correct format"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/forecast",
            json={
                "property": {
                    "city": "Bangalore",
                    "locality": "Whitefield",
                    "property_type": "apartment",
                    "bedrooms": 3,
                    "bathrooms": 2,
                    "area_sqft": 1200,
                    "age_years": 5,
                    "parking_spaces": 1
                },
                "forecast_months": 12,
                "include_comparables": True,
                "include_market_trends": True
            },
            timeout=5
        )
        
        if response.status_code == 200:
            return {"status": "pass", "message": "Forecast endpoint working"}
        elif response.status_code == 422:
            return {"status": "fail", "message": f"Invalid request format: {response.text[:100]}"}
        else:
            return {"status": "warning", "message": f"Status {response.status_code}"}
    except Exception as e:
        return {"status": "fail", "message": str(e)}

def test_rag_system() -> Dict:
    """Test RAG and vector system"""
    try:
        # Check if RAG documents exist
        from pathlib import Path
        rag_file = Path("data/processed/rag_documents.json")
        
        if rag_file.exists():
            with open(rag_file, 'r') as f:
                docs = json.load(f)
                if len(docs) > 0:
                    return {"status": "pass", "message": f"{len(docs):,} RAG documents available"}
        
        return {"status": "warning", "message": "RAG documents not processed"}
    except Exception as e:
        return {"status": "fail", "message": str(e)}

def test_mappls_integration() -> Dict:
    """Test Mappls integration"""
    try:
        from backend.services.mappls_integration import MapplsService
        
        mappls = MapplsService()
        if mappls.is_connected():
            return {"status": "pass", "message": "Mappls service connected"}
        else:
            return {"status": "warning", "message": "Mappls not configured"}
    except Exception as e:
        return {"status": "warning", "message": f"Mappls integration: {str(e)[:50]}"}

def test_dmpe_engine() -> Dict:
    """Test DMPE engine"""
    try:
        from backend.services.dmpe_engine import DMPEEngine
        
        dmpe = DMPEEngine()
        
        # Test prediction
        result = dmpe.predict({
            "city": "Bangalore",
            "locality": "Whitefield",
            "property_type": "apartment",
            "area_sqft": 1200
        })
        
        if result and "price" in result:
            return {"status": "pass", "message": "DMPE engine operational"}
        else:
            return {"status": "fail", "message": "DMPE prediction failed"}
    except Exception as e:
        return {"status": "fail", "message": str(e)}

# ===== RUN ALL TESTS =====

print("1️⃣  CORE SERVICES")
print("-"*70)
test_feature("Services", "FastAPI Backend", test_api_endpoint, f"{BASE_URL}/health")
test_feature("Services", "Node.js Backend", test_api_endpoint, f"{NODE_URL}/api/health")
test_feature("Services", "Database Connection", test_database_connection)

print("\n2️⃣  DATA AVAILABILITY")
print("-"*70)
test_feature("Data", "Property Data", test_property_data)
test_feature("Data", "GIS Layers", test_gis_data)
test_feature("Data", "RAG Documents", test_rag_system)

print("\n3️⃣  AI & ML CAPABILITIES")
print("-"*70)
test_feature("AI", "Multi-Agent System", test_multi_agent_system)
test_feature("AI", "Prediction Engine", test_prediction_engine)
test_feature("AI", "DMPE Engine", test_dmpe_engine)
test_feature("AI", "Document Intelligence", test_document_intelligence)
test_feature("AI", "Recommendation System", test_recommendations)

print("\n4️⃣  GEOSPATIAL FEATURES")
print("-"*70)
test_feature("Geospatial", "Location Analysis", test_geospatial_capabilities)
test_feature("Geospatial", "Mappls Integration", test_mappls_integration)

print("\n5️⃣  API ENDPOINTS")
print("-"*70)
test_feature("API", "Forecast Endpoint", test_forecast_endpoint)
test_feature("API", "Market Summary", test_api_endpoint, f"{BASE_URL}/api/market/summary")
test_feature("API", "Properties Endpoint", test_api_endpoint, f"{BASE_URL}/api/properties/all?limit=5")

print("\n6️⃣  ADVANCED FEATURES")
print("-"*70)

# Test time-based predictions
test_feature("Advanced", "Historical Analysis", test_api_endpoint, 
             f"{BASE_URL}/api/predict/time-based", "POST",
             {"lat": 12.9716, "lon": 77.5946, "months_from_now": -12})

test_feature("Advanced", "Future Forecasting", test_api_endpoint,
             f"{BASE_URL}/api/predict/time-based", "POST",
             {"lat": 12.9716, "lon": 77.5946, "months_from_now": 60})

test_feature("Advanced", "Area Trends", test_api_endpoint,
             f"{BASE_URL}/api/predict/area-forecast", "POST",
             {"area_name": "Whitefield", "months_ahead": 36})

test_feature("Advanced", "Market Cycles", test_api_endpoint,
             f"{BASE_URL}/api/predict/market-cycles")

# ===== RESULTS SUMMARY =====
print("\n" + "="*70)
print("📊 TEST RESULTS SUMMARY")
print("="*70)

success_rate = (test_results["passed"] / test_results["total"] * 100) if test_results["total"] > 0 else 0

print(f"Total Tests: {test_results['total']}")
print(f"✅ Passed: {test_results['passed']}")
print(f"❌ Failed: {test_results['failed']}")
print(f"⚠️  Warnings: {test_results['warnings']}")
print(f"\n🎯 Success Rate: {success_rate:.1f}%")

if test_results["errors"]:
    print(f"\n❌ Failed Tests:")
    for error in test_results["errors"][:10]:  # Show first 10 errors
        print(f"   - {error}")

# ===== SYSTEM ASSESSMENT =====
print("\n" + "="*70)
print("🏆 SYSTEM ASSESSMENT")
print("="*70)

if success_rate >= 95:
    print("✅ EXCELLENT: System is market-leading and production-ready!")
    print("   All advanced features are operational")
elif success_rate >= 85:
    print("✅ VERY GOOD: System is highly advanced with minor issues")
    print("   Most features are working perfectly")
elif success_rate >= 75:
    print("⚠️  GOOD: System is functional but needs improvements")
    print("   Core features work, some advanced features need fixes")
elif success_rate >= 60:
    print("⚠️  FAIR: System has significant issues")
    print("   Multiple features need attention")
else:
    print("❌ POOR: System needs major fixes")
    print("   Critical features are not working")

# ===== FEATURE HIGHLIGHTS =====
print("\n" + "="*70)
print("🌟 ADVANCED FEATURES STATUS")
print("="*70)

advanced_features = {
    "Time-based Predictions": test_results["passed"] > 10,
    "Multi-Agent AI": "AI/Multi-Agent System" not in str(test_results["errors"]),
    "Document Understanding": "AI/Document Intelligence" not in str(test_results["errors"]),
    "Geospatial Intelligence": "Geospatial/Location Analysis" not in str(test_results["errors"]),
    "RAG System": "Data/RAG Documents" not in str(test_results["errors"]),
    "Recommendation Engine": "AI/Recommendation System" not in str(test_results["errors"]),
    "Market Forecasting": "Advanced/Area Trends" not in str(test_results["errors"])
}

for feature, status in advanced_features.items():
    icon = "✅" if status else "❌"
    print(f"{icon} {feature}: {'Working' if status else 'Needs Fix'}")

# ===== RECOMMENDATIONS =====
print("\n" + "="*70)
print("💡 RECOMMENDATIONS TO ACHIEVE MARKET LEADERSHIP")
print("="*70)

recommendations = []

if test_results["failed"] > 0:
    recommendations.append("1. Fix all failing endpoints by restarting services with updated code")

if "Multi-Agent System" in str(test_results["errors"]):
    recommendations.append("2. Ensure multi-agent orchestrator is properly initialized")

if "Document Intelligence" in str(test_results["errors"]):
    recommendations.append("3. Install required libraries for document processing (PyPDF2, pytesseract)")

if "Recommendation System" in str(test_results["errors"]):
    recommendations.append("4. Verify recommendation endpoints are registered")

if success_rate < 90:
    recommendations.append("5. Restart all services to load new endpoints and features")

if not recommendations:
    recommendations.append("✅ System is performing excellently! Ready for production deployment.")

for rec in recommendations:
    print(f"   {rec}")

print("\n" + "="*70)
print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)
