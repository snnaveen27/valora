"""
Test cases for REALTY-GPT API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.api.main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "services" in data

def test_forecast_endpoint():
    """Test forecast endpoint"""
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
        "forecast_months": 6,
        "include_comparables": False,
        "include_market_trends": False
    }
    
    response = client.post("/api/forecast", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "price" in data["data"]
    assert "rental_yield" in data["data"]
    assert "demand_index" in data["data"]

def test_demand_endpoint():
    """Test demand index endpoint"""
    payload = {
        "city": "Mumbai",
        "locality": "Andheri",
        "property_type": "apartment",
        "bedrooms": 2,
        "area_sqft": 1000
    }
    
    response = client.post("/api/demand", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "demand_index" in data
    assert "factors" in data

def test_rental_yield_endpoint():
    """Test rental yield endpoint"""
    payload = {
        "city": "Delhi",
        "locality": "Connaught Place",
        "property_type": "commercial",
        "area_sqft": 2000
    }
    
    response = client.post("/api/rental-yield", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "rental_yield" in data
    assert "comparison" in data
    assert "recommendation" in data

def test_risk_assessment():
    """Test risk assessment endpoint"""
    payload = {
        "city": "Pune",
        "locality": "Hinjewadi",
        "property_type": "apartment",
        "bedrooms": 2,
        "area_sqft": 1200,
        "latitude": 18.5912,
        "longitude": 73.7389
    }
    
    response = client.post("/api/risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "risk_assessment" in data
    assert "overall_risk_score" in data["risk_assessment"]
    assert "risk_level" in data["risk_assessment"]
    assert "factors" in data["risk_assessment"]

def test_market_analysis():
    """Test market analysis endpoint"""
    payload = {
        "city": "Bangalore",
        "analysis_type": "comprehensive",
        "property_types": ["apartment", "house"]
    }
    
    response = client.post("/api/market-analysis", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "analysis" in data
    assert data["analysis"]["city"] == "Bangalore"

def test_portfolio_optimization():
    """Test portfolio optimization endpoint"""
    payload = {
        "properties": [
            {
                "city": "Mumbai",
                "locality": "Bandra",
                "property_type": "apartment",
                "bedrooms": 3,
                "area_sqft": 1500
            },
            {
                "city": "Bangalore",
                "locality": "Whitefield",
                "property_type": "house",
                "bedrooms": 4,
                "area_sqft": 2500
            }
        ],
        "optimization_goal": "balanced"
    }
    
    response = client.post("/api/portfolio/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "portfolio_analysis" in data
    assert data["portfolio_analysis"]["total_properties"] == 2

def test_recommendations():
    """Test recommendations endpoint"""
    response = client.post(
        "/api/recommend",
        params={
            "budget_min": 5000000,
            "budget_max": 15000000,
            "city": "Bangalore",
            "property_type": "apartment",
            "purpose": "investment"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "recommendations" in data["data"]

def test_invalid_property_type():
    """Test with invalid property type"""
    payload = {
        "city": "Mumbai",
        "locality": "Andheri",
        "property_type": "invalid_type",
        "bedrooms": 2,
        "area_sqft": 1000
    }
    
    response = client.post("/api/demand", json=payload)
    # Should still work with default handling
    assert response.status_code == 200

def test_missing_required_fields():
    """Test with missing required fields"""
    payload = {
        "property": {
            "city": "Bangalore"
            # Missing required fields
        }
    }
    
    response = client.post("/api/forecast", json=payload)
    assert response.status_code == 422  # Validation error

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
