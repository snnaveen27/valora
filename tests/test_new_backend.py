"""
Test script for the new REALTY-GPT backend
"""

import requests
import json

# Base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print("🏥 Health Check:")
    print(json.dumps(response.json(), indent=2))
    print()

def test_forecast():
    """Test comprehensive forecast"""
    payload = {
        "property": {
            "city": "Bangalore",
            "locality": "Koramangala",
            "property_type": "apartment",
            "bedrooms": 3,
            "bathrooms": 2,
            "area_sqft": 1500,
            "latitude": 12.9352,
            "longitude": 77.6245
        },
        "forecast_months": 12,
        "include_comparables": True,
        "include_market_trends": True
    }
    
    print("🔮 Forecast Request:")
    response = requests.post(f"{BASE_URL}/api/forecast", json=payload)
    result = response.json()
    
    if result.get("status") == "success":
        data = result["data"]
        print(f"  Price Prediction: ₹{data['price']['predicted']:,.0f}")
        print(f"  Rental Yield: {data['rental_yield']['predicted_percentage']:.2f}%")
        print(f"  Demand Score: {data['demand_index']['score']:.1f}/100")
        print(f"  Investment Score: {data['investment_metrics']['investment_score']:.1f}")
        print(f"  Risk Level: {data['investment_metrics']['risk_level']}")
        
        if data.get('market_insights'):
            print("\n  Market Insights:")
            for insight in data['market_insights'][:3]:
                print(f"    • {insight}")
    else:
        print(f"  Error: {result}")
    print()

def test_demand():
    """Test demand index"""
    payload = {
        "city": "Mumbai",
        "locality": "Bandra",
        "property_type": "apartment",
        "bedrooms": 2,
        "area_sqft": 1000,
        "latitude": 19.0596,
        "longitude": 72.8295
    }
    
    print("📊 Demand Index:")
    response = requests.post(f"{BASE_URL}/api/demand", json=payload)
    result = response.json()
    
    if result.get("status") == "success":
        demand = result["demand_index"]
        print(f"  Score: {demand['score']:.1f}/100")
        print(f"  Category: {demand['category']}")
        print(f"  Trend: {demand['trend']}")
        print(f"  Infrastructure Score: {result['factors']['infrastructure']:.1f}")
    else:
        print(f"  Error: {result}")
    print()

def test_rental_yield():
    """Test rental yield calculation"""
    payload = {
        "city": "Pune",
        "locality": "Hinjewadi",
        "property_type": "apartment",
        "bedrooms": 2,
        "area_sqft": 1200,
        "latitude": 18.5912,
        "longitude": 73.7389
    }
    
    print("💰 Rental Yield Analysis:")
    response = requests.post(f"{BASE_URL}/api/rental-yield", json=payload)
    result = response.json()
    
    if result.get("status") == "success":
        rental = result["rental_yield"]
        print(f"  Predicted Yield: {rental['predicted_percentage']:.2f}%")
        print(f"  Annual Income: ₹{rental['annual_rental_income']:,.0f}")
        print(f"  Recommendation: {result['recommendation']}")
    else:
        print(f"  Error: {result}")
    print()

def test_market_analysis():
    """Test market analysis"""
    payload = {
        "city": "Bangalore",
        "analysis_type": "hotspots",
        "property_types": ["apartment", "house"]
    }
    
    print("🗺️ Market Analysis (Hotspots):")
    response = requests.post(f"{BASE_URL}/api/market-analysis", json=payload)
    result = response.json()
    
    if result.get("status") == "success":
        hotspots = result["analysis"].get("hotspots", [])
        for hotspot in hotspots[:3]:
            print(f"  • {hotspot['locality']}: Score {hotspot['hotspot_score']}")
            print(f"    Factors: {', '.join(hotspot['factors'][:3])}")
    else:
        print(f"  Error: {result}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("🏗️ REALTY-GPT Backend Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_health()
        test_forecast()
        test_demand()
        test_rental_yield()
        test_market_analysis()
        
        print("✅ All tests completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Ensure it's running on port 8000")
    except Exception as e:
        print(f"❌ Test failed: {e}")
