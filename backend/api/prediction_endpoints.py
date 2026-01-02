"""
API endpoints for advanced prediction and analysis
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
from backend.services.advanced_prediction_engine import AdvancedPredictionEngine

router = APIRouter(prefix="/api/predict", tags=["prediction"])
prediction_engine = AdvancedPredictionEngine()

class TimePredictionRequest(BaseModel):
    lat: float
    lon: float
    months_from_now: int
    property_details: Optional[Dict] = None

class CoordinateAnalysisRequest(BaseModel):
    lat: float
    lon: float

class PropertyClickRequest(BaseModel):
    property_id: str

class AreaForecastRequest(BaseModel):
    area_name: str
    months_ahead: int = 60

@router.post("/time-based")
async def predict_time_based(request: TimePredictionRequest):
    """
    Predict property value at a specific time point
    """
    try:
        result = prediction_engine.predict_property_value(
            request.lat,
            request.lon,
            request.months_from_now,
            request.property_details
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/coordinate-analysis")
async def analyze_coordinate(request: CoordinateAnalysisRequest):
    """
    Comprehensive analysis of any coordinate in Bangalore
    """
    try:
        result = prediction_engine.analyze_coordinate(
            request.lat,
            request.lon
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/property-click")
async def analyze_property_click(request: PropertyClickRequest):
    """
    Comprehensive analysis when a property is clicked on the map
    """
    try:
        result = prediction_engine.analyze_property_click(
            request.property_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/area-forecast")
async def forecast_area(request: AreaForecastRequest):
    """
    Forecast trends for an entire area
    """
    try:
        result = prediction_engine.forecast_area_trends(
            request.area_name,
            request.months_ahead
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-pin")
async def analyze_pin_location(request: CoordinateAnalysisRequest):
    """
    Analyze importance when a pin is marked on the map
    """
    try:
        # Get coordinate analysis
        analysis = prediction_engine.analyze_coordinate(
            request.lat,
            request.lon
        )
        
        # Get time predictions
        predictions = {}
        for months in [-12, 0, 12, 24, 36, 60]:
            pred = prediction_engine.predict_property_value(
                request.lat,
                request.lon,
                months
            )
            predictions[f"{'past' if months < 0 else 'future'}_{abs(months)}m"] = {
                'value': pred.get('predicted_value', 0),
                'change': pred.get('percentage_change', 0)
            }
        
        # Combine results
        result = {
            **analysis,
            'time_predictions': predictions,
            'quick_insights': {
                'current_importance': analysis.get('importance_score', 0),
                'investment_grade': analysis.get('investment_insights', {}).get('investment_grade', 'B'),
                'future_potential': analysis.get('future_potential', {}),
                'top_recommendation': analysis.get('recommendations', [''])[0] if analysis.get('recommendations') else ''
            }
        }
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market-cycles")
async def get_market_cycles():
    """
    Get market cycle information
    """
    try:
        current_year = datetime.now().year
        cycles = []
        
        for year in range(current_year - 2, current_year + 6):
            cycle = prediction_engine._get_market_cycle(year)
            multiplier = prediction_engine._get_cycle_multiplier(year)
            cycles.append({
                'year': year,
                'cycle': cycle,
                'multiplier': multiplier,
                'impact': f"{(multiplier - 1) * 100:+.0f}%"
            })
        
        return {
            'current_year': current_year,
            'cycles': cycles,
            'description': {
                'boom': 'High demand, rapid price appreciation',
                'stable': 'Balanced market, steady growth',
                'correction': 'Price adjustment, buying opportunity'
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/neighborhood-comparison")
async def compare_neighborhoods(areas: List[str]):
    """
    Compare multiple neighborhoods
    """
    try:
        comparisons = []
        
        for area in areas[:5]:  # Limit to 5 areas
            forecast = prediction_engine.forecast_area_trends(area, 60)
            comparisons.append({
                'area': area,
                'current_growth': prediction_engine.growth_rates.get(area, 10),
                'expected_appreciation': forecast['summary']['expected_appreciation'],
                'investment_score': forecast['summary']['avg_investment_score'],
                'recommendation': forecast['summary']['recommendation']
            })
        
        # Sort by investment score
        comparisons.sort(key=lambda x: x['investment_score'], reverse=True)
        
        return {
            'comparison': comparisons,
            'best_area': comparisons[0]['area'] if comparisons else None,
            'analysis_date': datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
