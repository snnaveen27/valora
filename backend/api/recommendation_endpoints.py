"""
Advanced Recommendation Endpoints for Real Estate AI
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
from sqlalchemy import text
from backend.database.multiconnection import mdb
from backend.services.advanced_prediction_engine import AdvancedPredictionEngine
from backend.services.dmpe_engine import DMPEEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["recommendations"])

# Initialize services
prediction_engine = AdvancedPredictionEngine()
dmpe_engine = DMPEEngine()

class RecommendationRequest(BaseModel):
    """Request model for property recommendations"""
    city: str = "Bangalore"
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    area_min: Optional[float] = None
    area_max: Optional[float] = None
    localities: Optional[List[str]] = None
    amenities: Optional[List[str]] = None
    purpose: str = "investment"  # investment, residential, commercial
    limit: int = 10

@router.post("/recommendations")
async def get_property_recommendations(request: RecommendationRequest):
    """
    Get AI-powered property recommendations based on criteria
    """
    try:
        recommendations = []
        
        with mdb.spatial() as session:
            # Build query based on criteria
            query_parts = ["SELECT property_id, ST_Y(location) as lat, ST_X(location) as lon, city, locality"]
            query_parts.append("FROM property_locations")
            where_clauses = ["city = :city"]
            params = {"city": request.city}
            
            # Apply filters
            if request.localities and len(request.localities) > 0:
                locality_placeholders = ", ".join([f":loc_{i}" for i in range(len(request.localities))])
                where_clauses.append(f"locality IN ({locality_placeholders})")
                for i, loc in enumerate(request.localities):
                    params[f"loc_{i}"] = loc
            
            if where_clauses:
                query_parts.append("WHERE " + " AND ".join(where_clauses))
            
            query_parts.append(f"LIMIT {request.limit}")
            
            # Execute query
            query = " ".join(query_parts)
            result = session.execute(text(query), params)
            
            # Process results
            for row in result:
                property_id = row[0]
                lat = row[1]
                lon = row[2]
                locality = row[4]
                
                # Get prediction for each property
                prediction = prediction_engine.predict_property_value(
                    lat, lon, 
                    months_from_now=12,
                    property_details={"area_sqft": 1200}  # Default
                )
                
                # Calculate investment score
                location_analysis = prediction_engine.analyze_coordinate(lat, lon)
                
                # Build recommendation
                rec = {
                    "property_id": property_id,
                    "location": {
                        "latitude": lat,
                        "longitude": lon,
                        "locality": locality
                    },
                    "predicted_value": prediction.get("predicted_value", 0),
                    "appreciation_potential": f"{prediction.get('percentage_change', 0):.1f}%",
                    "investment_score": location_analysis.get("importance_score", 0),
                    "investment_grade": location_analysis.get("investment_insights", {}).get("investment_grade", "B"),
                    "future_potential": location_analysis.get("future_potential", {}),
                    "recommendation_reason": _get_recommendation_reason(
                        request.purpose,
                        prediction,
                        location_analysis
                    ),
                    "confidence": prediction.get("confidence_score", 0.7)
                }
                
                recommendations.append(rec)
        
        # Sort by investment score
        recommendations.sort(key=lambda x: x["investment_score"], reverse=True)
        
        return {
            "status": "success",
            "recommendations": recommendations[:request.limit],
            "total_found": len(recommendations),
            "criteria": {
                "city": request.city,
                "purpose": request.purpose,
                "budget": f"{request.budget_min or 0} - {request.budget_max or 'unlimited'}"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations/top-investments")
async def get_top_investment_opportunities(
    city: str = Query("Bangalore", description="City name"),
    limit: int = Query(10, description="Number of recommendations")
):
    """
    Get top investment opportunities based on AI analysis
    """
    try:
        top_investments = []
        
        # Get high-growth localities
        high_growth_areas = [
            "Hebbal", "Sarjapur Road", "Electronic City", 
            "Whitefield", "HSR Layout"
        ]
        
        for area in high_growth_areas[:limit]:
            forecast = prediction_engine.forecast_area_trends(area, 60)
            
            investment = {
                "locality": area,
                "annual_growth_rate": prediction_engine.growth_rates.get(area, 10),
                "5_year_appreciation": forecast["summary"]["expected_appreciation"],
                "investment_score": forecast["summary"]["avg_investment_score"],
                "recommendation": forecast["summary"]["recommendation"],
                "key_highlights": [
                    f"Annual growth: {prediction_engine.growth_rates.get(area, 10)}%",
                    f"5-year potential: {forecast['summary']['expected_appreciation']}",
                    f"Investment score: {forecast['summary']['avg_investment_score']:.1f}/100"
                ],
                "risk_level": "Medium" if forecast["summary"]["avg_investment_score"] > 70 else "High",
                "optimal_property_types": _get_optimal_property_types(area)
            }
            
            top_investments.append(investment)
        
        return {
            "status": "success",
            "top_investments": top_investments,
            "market_insights": {
                "best_performing": top_investments[0]["locality"] if top_investments else None,
                "average_growth": sum(i["annual_growth_rate"] for i in top_investments) / len(top_investments) if top_investments else 0,
                "market_trend": "Bullish",
                "investment_window": "Next 6-12 months optimal"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Top investments error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations/similar-properties/{property_id}")
async def get_similar_properties(
    property_id: str,
    limit: int = Query(5, description="Number of similar properties")
):
    """
    Get similar properties based on AI analysis
    """
    try:
        similar_properties = []
        
        with mdb.spatial() as session:
            # Get original property
            result = session.execute(text("""
                SELECT ST_Y(location) as lat, ST_X(location) as lon, locality
                FROM property_locations
                WHERE property_id = :pid
            """), {"pid": property_id})
            
            original = result.fetchone()
            if not original:
                raise HTTPException(status_code=404, detail="Property not found")
            
            lat, lon, locality = original
            
            # Find similar properties nearby
            result = session.execute(text("""
                SELECT 
                    property_id,
                    ST_Y(location) as lat,
                    ST_X(location) as lon,
                    locality,
                    ST_Distance(location::geography, 
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) as distance
                FROM property_locations
                WHERE property_id != :pid
                AND ST_DWithin(
                    location::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                    2000  -- Within 2km
                )
                ORDER BY distance
                LIMIT :limit
            """), {"lat": lat, "lon": lon, "pid": property_id, "limit": limit})
            
            for row in result:
                sim_id, sim_lat, sim_lon, sim_locality, distance = row
                
                # Analyze similarity
                similarity_score = max(0, 100 - (distance / 20))  # Score based on distance
                
                similar_properties.append({
                    "property_id": sim_id,
                    "location": {
                        "latitude": sim_lat,
                        "longitude": sim_lon,
                        "locality": sim_locality
                    },
                    "distance_meters": round(distance),
                    "similarity_score": round(similarity_score, 1),
                    "comparison": {
                        "location_match": sim_locality == locality,
                        "proximity": "Very Close" if distance < 500 else "Close" if distance < 1000 else "Nearby"
                    }
                })
        
        return {
            "status": "success",
            "original_property": property_id,
            "similar_properties": similar_properties,
            "total_found": len(similar_properties),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Similar properties error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recommendations/personalized")
async def get_personalized_recommendations(
    user_preferences: Dict[str, Any]
):
    """
    Get personalized recommendations based on user preferences and AI learning
    """
    try:
        # Analyze user preferences
        preferred_localities = user_preferences.get("localities", [])
        budget = user_preferences.get("budget", {})
        lifestyle = user_preferences.get("lifestyle", "family")
        investment_goal = user_preferences.get("investment_goal", "long-term")
        
        recommendations = []
        
        # Generate personalized recommendations
        if lifestyle == "family":
            # Focus on residential areas with schools
            focus_areas = ["Whitefield", "HSR Layout", "JP Nagar"]
        elif lifestyle == "professional":
            # Focus on areas near tech parks
            focus_areas = ["Electronic City", "Marathahalli", "Koramangala"]
        else:
            focus_areas = ["Indiranagar", "Koramangala", "HSR Layout"]
        
        for area in focus_areas[:5]:
            # Get area analysis
            forecast = prediction_engine.forecast_area_trends(area, 36)
            
            rec = {
                "locality": area,
                "match_score": 85 + (5 if area in preferred_localities else 0),
                "why_recommended": _get_personalized_reason(lifestyle, investment_goal, area),
                "investment_potential": forecast["summary"]["avg_investment_score"],
                "lifestyle_fit": _calculate_lifestyle_fit(lifestyle, area),
                "predicted_appreciation": forecast["summary"]["expected_appreciation"],
                "action": "Explore Properties"
            }
            
            recommendations.append(rec)
        
        # Sort by match score
        recommendations.sort(key=lambda x: x["match_score"], reverse=True)
        
        return {
            "status": "success",
            "personalized_recommendations": recommendations,
            "user_profile": {
                "lifestyle": lifestyle,
                "investment_goal": investment_goal,
                "preferred_areas": preferred_localities
            },
            "insights": {
                "best_match": recommendations[0]["locality"] if recommendations else None,
                "average_match_score": sum(r["match_score"] for r in recommendations) / len(recommendations) if recommendations else 0
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Personalized recommendations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _get_recommendation_reason(purpose: str, prediction: Dict, analysis: Dict) -> str:
    """Generate recommendation reason based on purpose"""
    if purpose == "investment":
        return f"High growth potential ({prediction.get('percentage_change', 0):.1f}% in 1 year) with {analysis.get('investment_insights', {}).get('investment_grade', 'B')} grade"
    elif purpose == "residential":
        return f"Excellent locality with {analysis.get('importance_score', 0):.0f}/100 livability score"
    else:
        return f"Strategic location with strong commercial potential"

def _get_optimal_property_types(area: str) -> List[str]:
    """Get optimal property types for an area"""
    if area in ["Whitefield", "Electronic City", "Marathahalli"]:
        return ["2BHK Apartments", "3BHK Apartments", "Studio Apartments"]
    elif area in ["HSR Layout", "Koramangala"]:
        return ["3BHK Apartments", "Villas", "Penthouses"]
    else:
        return ["2BHK Apartments", "3BHK Apartments", "Plots"]

def _get_personalized_reason(lifestyle: str, goal: str, area: str) -> str:
    """Generate personalized recommendation reason"""
    if lifestyle == "family":
        return f"{area} offers excellent schools, parks, and family-friendly amenities"
    elif lifestyle == "professional":
        return f"{area} provides quick access to tech parks and business centers"
    else:
        return f"{area} features vibrant nightlife, cafes, and urban lifestyle"

def _calculate_lifestyle_fit(lifestyle: str, area: str) -> float:
    """Calculate lifestyle fit score"""
    lifestyle_area_scores = {
        "family": {"Whitefield": 95, "HSR Layout": 90, "JP Nagar": 85},
        "professional": {"Electronic City": 95, "Marathahalli": 90, "Koramangala": 92},
        "urban": {"Indiranagar": 95, "Koramangala": 92, "HSR Layout": 88}
    }
    
    return lifestyle_area_scores.get(lifestyle, {}).get(area, 70)
