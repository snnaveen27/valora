#!/usr/bin/env python
"""
Test various queries on the real estate AI system
"""

import requests
import json
import time
from datetime import datetime

print("🧪 Testing Real Estate AI System Queries")
print("="*60)
print(f"Testing started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Track test results
test_results = {
    "passed": 0,
    "failed": 0,
    "warnings": 0
}

def test_query(name, url, method="GET", data=None, expected_status=200):
    """Test a query and track results"""
    try:
        print(f"🔍 Testing: {name}")
        
        if method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            response = requests.get(url, timeout=10)
        
        if response.status_code == expected_status:
            print(f"   ✅ Status: {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                result = response.json()
                if isinstance(result, dict) and 'message' in result:
                    print(f"   📝 Response: {result['message'][:100]}...")
                elif isinstance(result, list):
                    print(f"   📊 Results: {len(result)} items")
            test_results["passed"] += 1
        else:
            print(f"   ❌ Status: {response.status_code} (expected {expected_status})")
            print(f"   📝 Error: {response.text[:200]}")
            test_results["failed"] += 1
            
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
        test_results["failed"] += 1
    
    print()

# ===== 1. HEALTH CHECKS =====
print("1️⃣  HEALTH CHECKS")
print("-"*60)

test_query("FastAPI Health", "http://localhost:8000/health")
test_query("Node.js Health", "http://localhost:3001/api/health")

# ===== 2. MARKET ANALYSIS =====
print("2️⃣  MARKET ANALYSIS")
print("-"*60)

test_query("Market Summary", "http://localhost:8000/api/market/summary")

# ===== 3. CHAT API TESTS =====
print("3️⃣  CHAT API TESTS")
print("-"*60)

chat_queries = [
    "Hello, I'm looking for properties in Bangalore",
    "Find 3BHK apartments in Whitefield under 1 crore",
    "Show properties near HSR Layout with good infrastructure",
    "What's the average price in Electronic City?",
    "Compare Koramangala vs BTM for investment",
    "Draw a 2km radius around Manyata Tech Park",
    "Find commercial properties near metro stations",
    "Show agricultural land in outskirts under 50 lakhs",
    "What are the best investment zones in Bangalore?",
    "Find properties with swimming pool and gym"
]

for query in chat_queries:
    test_query(
        f"Chat: {query[:30]}...",
        "http://localhost:3001/api/chat",
        method="POST",
        data={"message": query}
    )

# ===== 4. MULTI-AGENT TESTS =====
print("4️⃣  MULTI-AGENT TESTS")
print("-"*60)

agent_queries = [
    ("Property Search", "Find 3BHK properties in Whitefield under 1 crore"),
    ("Investment Analysis", "Analyze investment potential in HSR Layout"),
    ("Zone Comparison", "Compare Whitefield vs Electronic City"),
    ("Infrastructure Analysis", "Find areas with good metro connectivity"),
    ("Price Analysis", "What's the price trend in Bangalore?"),
    ("Geospatial Query", "Draw polygon around Koramangala and analyze"),
    ("Commercial Analysis", "Find commercial properties with high footfall"),
    ("Future Growth", "Which areas have best growth potential?")
]

for name, intent in agent_queries:
    test_query(
        f"Agent: {name}",
        "http://localhost:8000/api/agent/plan",
        method="POST",
        data={
            "intent": intent,
            "user_id": "test_user",
            "context": {"city": "Bangalore"}
        }
    )

# ===== 5. PROPERTY API TESTS =====
print("5️⃣  PROPERTY API TESTS")
print("-"*60)

# Test forecast endpoint with proper data
test_query(
    "Property Forecast",
    "http://localhost:8000/api/forecast",
    method="POST",
    data={
        "property_data": {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "area_sqft": 1200,
            "bedrooms": 3,
            "bathrooms": 2,
            "city": "Bangalore",
            "locality": "Whitefield"
        }
    }
)

# Test demand index
test_query(
    "Demand Index",
    "http://localhost:8000/api/demand",
    method="POST",
    data={
        "latitude": 12.9716,
        "longitude": 77.5946,
        "city": "Bangalore",
        "locality": "Whitefield"
    }
)

# Test rental yield
test_query(
    "Rental Yield",
    "http://localhost:8000/api/rental-yield",
    method="POST",
    data={
        "latitude": 12.9716,
        "longitude": 77.5946,
        "area_sqft": 1200,
        "price": 8000000,
        "city": "Bangalore"
    }
)

# ===== 6. DATABASE QUERIES =====
print("6️⃣  DATABASE VERIFICATION")
print("-"*60)

try:
    from backend.database.multiconnection import mdb
    from sqlalchemy import text
    
    with mdb.spatial() as session:
        # Check properties count
        result = session.execute(text("SELECT COUNT(*) FROM property_locations"))
        prop_count = result.scalar()
        print(f"✅ Properties in DB: {prop_count:,}")
        
        # Check cities
        result = session.execute(text("SELECT COUNT(DISTINCT city) FROM property_locations"))
        city_count = result.scalar()
        print(f"✅ Cities: {city_count}")
        
        # Check GIS tables
        result = session.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name LIKE 'gis_%'
        """))
        gis_count = result.scalar()
        print(f"✅ GIS Tables: {gis_count}")
        
        # Sample property query
        result = session.execute(text("""
            SELECT city, COUNT(*) as count 
            FROM property_locations 
            GROUP BY city 
            ORDER BY count DESC 
            LIMIT 5
        """))
        print("✅ Top 5 cities by property count:")
        for row in result:
            print(f"   - {row[0]}: {row[1]:,}")
        
        test_results["passed"] += 1
        
except Exception as e:
    print(f"❌ Database error: {e}")
    test_results["failed"] += 1

print()

# ===== 7. FRONTEND ACCESS =====
print("7️⃣  FRONTEND ACCESS")
print("-"*60)

test_query("Frontend Homepage", "http://localhost:3000/")

# ===== 8. API DOCUMENTATION =====
print("8️⃣  API DOCUMENTATION")
print("-"*60)

test_query("FastAPI Docs", "http://localhost:8000/docs")

# ===== SUMMARY =====
print("="*60)
print("📊 TEST SUMMARY")
print("="*60)
print(f"✅ Passed: {test_results['passed']}")
print(f"❌ Failed: {test_results['failed']}")
print(f"⚠️  Warnings: {test_results['warnings']}")

total = test_results['passed'] + test_results['failed'] + test_results['warnings']
success_rate = (test_results['passed'] / total * 100) if total > 0 else 0

print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")

if success_rate >= 90:
    print("\n🎉 EXCELLENT! System is performing exceptionally well!")
elif success_rate >= 75:
    print("\n✅ GOOD! System is mostly operational with minor issues.")
elif success_rate >= 50:
    print("\n⚠️  FAIR! System has some issues that need attention.")
else:
    print("\n❌ POOR! System needs significant fixes.")

print(f"\n⏱️  Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ===== SAMPLE INTERACTIONS =====
print("\n" + "="*60)
print("🎮 SAMPLE INTERACTIONS TO TRY IN FRONTEND")
print("="*60)

sample_interactions = [
    "🏠 Find 3BHK apartments in Whitefield under 1 crore",
    "🗺️ Draw a 2km buffer around Manyata Tech Park",
    "📊 Compare HSR Layout vs BTM Layout for investment",
    "🏢 Find commercial properties near metro stations",
    "🌳 Show agricultural land with good road access",
    "📈 What's the price trend in Electronic City?",
    "🎯 Find properties with best investment potential",
    "🏗️ Analyze infrastructure quality in Koramangala",
    "💰 Show properties with high rental yield",
    "📍 Find properties near international schools"
]

for interaction in sample_interactions:
    print(f"   {interaction}")

print("\n✨ All tests completed! Try these interactions in the frontend at http://localhost:3000")
