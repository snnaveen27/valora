#!/usr/bin/env python
"""
Test with corrected query formats
"""

import requests
import json

print("🔧 Testing with Corrected Query Formats\n")

# Test 1: Multi-agent with proper format
print("1️⃣  Multi-Agent Property Search")
try:
    response = requests.post(
        "http://localhost:8000/api/agent/plan",
        json={
            "intent": "Find 3BHK properties in Whitefield under 1 crore",
            "user_id": "test_user",
            "context": {
                "city": "Bangalore",
                "budget": {"min": 5000000, "max": 10000000},
                "property_type": "3BHK",
                "locality": "Whitefield"
            }
        },
        timeout=10
    )
    if response.status_code == 200:
        result = response.json()
        print("✅ Multi-agent working")
        print(f"   Response: {str(result)[:200]}...")
    else:
        print(f"❌ Status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 2: Forecast with correct format
print("2️⃣  Property Forecast (Corrected)")
try:
    response = requests.post(
        "http://localhost:8000/api/forecast",
        json={
            "property": {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "area_sqft": 1200,
                "bedrooms": 3,
                "bathrooms": 2,
                "city": "Bangalore",
                "locality": "Whitefield"
            }
        },
        timeout=10
    )
    if response.status_code == 200:
        result = response.json()
        print("✅ Forecast working")
        print(f"   Keys: {list(result.keys())}")
    else:
        print(f"❌ Status: {response.status_code}")
        print(f"   Error: {response.text[:200]}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 3: Demand Index with correct format
print("3️⃣  Demand Index (Corrected)")
try:
    response = requests.post(
        "http://localhost:8000/api/demand",
        json={
            "property_type": "residential",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "city": "Bangalore",
            "locality": "Whitefield"
        },
        timeout=10
    )
    if response.status_code == 200:
        result = response.json()
        print("✅ Demand index working")
        print(f"   Demand Score: {result.get('demand_index', 'N/A')}")
    else:
        print(f"❌ Status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 4: Rental Yield with correct format
print("4️⃣  Rental Yield (Corrected)")
try:
    response = requests.post(
        "http://localhost:8000/api/rental-yield",
        json={
            "latitude": 12.9716,
            "longitude": 77.5946,
            "area_sqft": 1200,
            "price": 8000000,
            "city": "Bangalore",
            "locality": "Whitefield"
        },
        timeout=10
    )
    if response.status_code == 200:
        result = response.json()
        print("✅ Rental yield working")
        print(f"   Yield: {result.get('rental_yield', 'N/A')}%")
    else:
        print(f"❌ Status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 5: Quick analyze endpoint
print("5️⃣  Quick Analyze")
try:
    response = requests.post(
        "http://localhost:8000/api/agent/analyze",
        json={
            "city": "Bangalore",
            "budget_max": 10000000,
            "property_type": "3BHK"
        },
        timeout=10
    )
    if response.status_code == 200:
        result = response.json()
        print("✅ Quick analyze working")
        print(f"   Found: {result.get('properties_found', 'N/A')} properties")
    else:
        print(f"❌ Status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 6: Market Analysis
print("6️⃣  Market Analysis")
try:
    response = requests.post(
        "http://localhost:8000/api/market-analysis",
        json={
            "city": "Bangalore",
            "localities": ["Whitefield", "HSR Layout", "Koramangala"],
            "property_types": ["residential", "commercial"]
        },
        timeout=10
    )
    if response.status_code == 200:
        result = response.json()
        print("✅ Market analysis working")
        print(f"   Analyzed: {result.get('localities_analyzed', 'N/A')} areas")
    else:
        print(f"❌ Status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 7: RAG Query
print("7️⃣  RAG Query")
try:
    response = requests.post(
        "http://localhost:8000/api/rag/query",
        json={
            "query": "What are the best investment areas in Bangalore?",
            "top_k": 5
        },
        timeout=10
    )
    if response.status_code == 200:
        result = response.json()
        print("✅ RAG query working")
        print(f"   Results: {len(result.get('results', []))} items")
    else:
        print(f"❌ Status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 8: Check AI service status
print("8️⃣  AI Service Check")
try:
    from backend.services.external_apis import simple_chat
    result = simple_chat("Hello, can you help me find properties?")
    print("✅ AI service working")
    print(f"   Response: {result[:100]}...")
except Exception as e:
    print(f"❌ AI service issue: {e}")

print("\n" + "="*60)
print("🎮 INTERACTIVE TESTS TO TRY IN FRONTEND")
print("="*60)

frontend_tests = [
    {
        "query": "Find 3BHK apartments in Whitefield under 1 crore",
        "expected": "Property listings with price and location"
    },
    {
        "query": "Draw a 2km buffer around Manyata Tech Park",
        "expected": "Map visualization with buffer zone"
    },
    {
        "query": "Compare HSR Layout vs Koramangala for investment",
        "expected": "Comparison analysis with metrics"
    },
    {
        "query": "Show properties near metro stations",
        "expected": "Properties with proximity analysis"
    },
    {
        "query": "What's the price trend in Electronic City?",
        "expected": "Market trend analysis"
    },
    {
        "query": "Find commercial shops in Indiranagar",
        "expected": "Commercial property listings"
    },
    {
        "query": "Analyze infrastructure in Whitefield",
        "expected": "Infrastructure scoring and analysis"
    },
    {
        "query": "Show agricultural land near Bangalore",
        "expected": "Land listings with zoning info"
    }
]

for i, test in enumerate(frontend_tests, 1):
    print(f"{i}. Query: {test['query']}")
    print(f"   Expected: {test['expected']}")
    print()

print("🌐 Open http://localhost:3000 to try these in the frontend!")
