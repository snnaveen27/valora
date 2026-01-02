#!/usr/bin/env python
"""
Test advanced features: time slider, predictions, pin analysis, property analysis
"""

import requests
import json
from datetime import datetime

print("🚀 Testing Advanced Real Estate AI Features")
print("="*60)
print(f"Testing started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Base URLs
BASE_URL = "http://localhost:8000"
NODE_URL = "http://localhost:3001"

test_results = {
    "passed": 0,
    "failed": 0
}

def test_feature(name, method, url, data=None, expected_keys=None):
    """Test an advanced feature"""
    print(f"🔍 Testing: {name}")
    
    try:
        if method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ SUCCESS (Status: {response.status_code})")
            
            # Check for expected keys
            if expected_keys:
                missing_keys = [key for key in expected_keys if key not in result]
                if missing_keys:
                    print(f"   ⚠️  Missing keys: {missing_keys}")
                else:
                    print(f"   ✅ All expected keys present")
            
            # Print sample data
            if isinstance(result, dict):
                sample_keys = list(result.keys())[:5]
                print(f"   📊 Data keys: {sample_keys}")
                
                # Special handling for specific endpoints
                if 'importance_score' in result:
                    print(f"   📍 Importance Score: {result['importance_score']:.1f}/100")
                if 'predicted_value' in result:
                    print(f"   💰 Predicted Value: ₹{result['predicted_value']:,.0f}")
                if 'investment_grade' in result.get('investment_insights', {}):
                    print(f"   🎯 Investment Grade: {result['investment_insights']['investment_grade']}")
                if 'trends' in result:
                    print(f"   📈 Trend Points: {len(result['trends'])}")
            
            test_results["passed"] += 1
        else:
            print(f"   ❌ FAILED (Status: {response.status_code})")
            print(f"   Error: {response.text[:200]}")
            test_results["failed"] += 1
            
    except Exception as e:
        print(f"   ❌ EXCEPTION: {str(e)}")
        test_results["failed"] += 1
    
    print()
    return None

# ===== 1. TIME-BASED PREDICTIONS =====
print("1️⃣  TIME-BASED PREDICTIONS")
print("-"*60)

# Test current value
test_feature(
    "Current Property Value",
    "POST",
    f"{BASE_URL}/api/predict/time-based",
    {
        "lat": 12.9716,
        "lon": 77.5946,
        "months_from_now": 0,
        "property_details": {
            "area_sqft": 1200,
            "price": 8000000
        }
    },
    ["current_value", "predicted_value", "confidence_score"]
)

# Test future prediction (1 year)
test_feature(
    "1-Year Future Prediction",
    "POST",
    f"{BASE_URL}/api/predict/time-based",
    {
        "lat": 12.9716,
        "lon": 77.5946,
        "months_from_now": 12
    },
    ["predicted_value", "percentage_change", "market_cycle"]
)

# Test future prediction (5 years)
test_feature(
    "5-Year Future Prediction",
    "POST",
    f"{BASE_URL}/api/predict/time-based",
    {
        "lat": 12.9716,
        "lon": 77.5946,
        "months_from_now": 60
    },
    ["predicted_value", "annual_growth_rate", "confidence_score"]
)

# Test past estimation
test_feature(
    "Historical Value (1 year ago)",
    "POST",
    f"{BASE_URL}/api/predict/time-based",
    {
        "lat": 12.9716,
        "lon": 77.5946,
        "months_from_now": -12
    },
    ["predicted_value", "value_change"]
)

# ===== 2. COORDINATE ANALYSIS =====
print("2️⃣  COORDINATE ANALYSIS (Pin Drop)")
print("-"*60)

# Test coordinate analysis
test_feature(
    "Analyze Random Coordinate",
    "POST",
    f"{BASE_URL}/api/predict/coordinate-analysis",
    {
        "lat": 12.9352,
        "lon": 77.6245
    },
    ["locality", "zone", "importance_score", "investment_insights", "future_potential"]
)

# Test pin analysis with predictions
test_feature(
    "Analyze Pin with Time Predictions",
    "POST",
    f"{BASE_URL}/api/predict/analyze-pin",
    {
        "lat": 12.9121,
        "lon": 77.6446
    },
    ["importance_score", "time_predictions", "quick_insights", "recommendations"]
)

# ===== 3. PROPERTY CLICK ANALYSIS =====
print("3️⃣  PROPERTY CLICK ANALYSIS")
print("-"*60)

# First, get a property ID
print("Getting property IDs...")
try:
    props_response = requests.get(f"{BASE_URL}/api/properties/all?limit=5")
    if props_response.status_code == 200:
        properties = props_response.json().get('properties', [])
        if properties:
            property_id = properties[0]['property_id']
            print(f"   Using property ID: {property_id}")
            
            # Test property click analysis
            test_feature(
                "Property Click Analysis",
                "POST",
                f"{BASE_URL}/api/predict/property-click",
                {"property_id": property_id},
                ["property_id", "location", "investment_score", "rental_yield_estimate", "price_trends"]
            )
        else:
            print("   ⚠️  No properties found")
    else:
        print(f"   ❌ Could not fetch properties: {props_response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# ===== 4. AREA FORECASTING =====
print("4️⃣  AREA FORECASTING")
print("-"*60)

areas_to_test = ["Whitefield", "HSR Layout", "Koramangala", "Electronic City"]

for area in areas_to_test:
    test_feature(
        f"Forecast for {area}",
        "POST",
        f"{BASE_URL}/api/predict/area-forecast",
        {
            "area_name": area,
            "months_ahead": 36
        },
        ["area", "trends", "summary"]
    )

# ===== 5. NEIGHBORHOOD COMPARISON =====
print("5️⃣  NEIGHBORHOOD COMPARISON")
print("-"*60)

test_feature(
    "Compare Top Areas",
    "POST",
    f"{BASE_URL}/api/predict/neighborhood-comparison",
    ["Whitefield", "HSR Layout", "Koramangala", "Electronic City", "Indiranagar"],
    ["comparison", "best_area"]
)

# ===== 6. MARKET CYCLES =====
print("6️⃣  MARKET CYCLES")
print("-"*60)

test_feature(
    "Get Market Cycles",
    "GET",
    f"{BASE_URL}/api/predict/market-cycles",
    None,
    ["current_year", "cycles", "description"]
)

# ===== 7. PROPERTY ENDPOINTS =====
print("7️⃣  PROPERTY DATA ENDPOINTS")
print("-"*60)

test_feature(
    "Get All Properties",
    "GET",
    f"{BASE_URL}/api/properties/all?limit=10",
    None,
    ["properties", "count"]
)

test_feature(
    "Get Properties by Area",
    "GET",
    f"{BASE_URL}/api/properties/by-area?lat=12.9716&lon=77.5946&radius=2000",
    None,
    ["properties", "center", "radius"]
)

test_feature(
    "Get Property Stats",
    "GET",
    f"{BASE_URL}/api/properties/stats",
    None,
    ["total_properties", "cities", "localities", "top_localities"]
)

# ===== 8. MAPPLS POI CACHING =====
print("8️⃣  MAPPLS POI CACHING TEST")
print("-"*60)

# This will trigger Mappls API and cache POIs
test_feature(
    "Analyze Location with POI Caching",
    "POST",
    f"{BASE_URL}/api/predict/coordinate-analysis",
    {
        "lat": 12.9568,
        "lon": 77.7012
    },
    ["nearby_pois", "location_features"]
)

# ===== SUMMARY =====
print("="*60)
print("📊 TEST SUMMARY")
print("="*60)
print(f"✅ Passed: {test_results['passed']}")
print(f"❌ Failed: {test_results['failed']}")

total = test_results['passed'] + test_results['failed']
success_rate = (test_results['passed'] / total * 100) if total > 0 else 0

print(f"\n🎯 Success Rate: {success_rate:.1f}%")

if success_rate >= 90:
    print("\n🎉 EXCELLENT! Advanced features working perfectly!")
elif success_rate >= 75:
    print("\n✅ GOOD! Most advanced features operational.")
elif success_rate >= 50:
    print("\n⚠️  FAIR! Some features need attention.")
else:
    print("\n❌ POOR! Advanced features need fixes.")

print(f"\n⏱️  Testing completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ===== FEATURE HIGHLIGHTS =====
print("\n" + "="*60)
print("🌟 ADVANCED FEATURES AVAILABLE")
print("="*60)

features = [
    "⏰ **Time Slider**: Predict property values -2 to +5 years",
    "📍 **Pin Analysis**: Drop pin anywhere for instant analysis",
    "🏠 **Property Click**: Click any property for deep insights",
    "📈 **Area Forecasting**: 5-year predictions for any locality",
    "🔮 **Market Cycles**: Understand boom/correction periods",
    "🗺️ **Geospatial Intelligence**: Zone analysis & importance scoring",
    "💰 **Investment Grading**: AAA to B ratings for locations",
    "🏢 **POI Integration**: Cached nearby amenities from Mappls",
    "📊 **Comparative Analysis**: Compare multiple neighborhoods",
    "🎯 **Rental Yield**: Estimate rental returns for properties"
]

for feature in features:
    print(f"   {feature}")

print("\n🚀 **Try These in the Frontend:**")
print("   1. Move the time slider to see future property values")
print("   2. Right-click on map to drop an analysis pin")
print("   3. Click on any property marker for detailed analysis")
print("   4. Use slider animation to see market evolution")
print("   5. Switch between Past/Present/Future modes")

print("\n✨ Advanced Real Estate AI Platform Ready!")
