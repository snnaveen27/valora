"""
REALTY-GPT Backend API
Enhanced FastAPI application with DMPE, RAG, and Mappls integration
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.dmpe_engine import DMPEEngine
from backend.services.data_processor import DataProcessor
from backend.services.mappls_integration import MapplsService
from backend.services.model_retraining import ModelRetrainingService
from backend.services.multi_agent_orchestrator import ValoraOrchestrator
from backend.utils.config import Settings
from backend.utils.logger import setup_logger
import pandas as pd

# Ensure a base logger exists before any try/except uses it
logger = logging.getLogger(__name__)

# Try to import additional endpoints
try:
    from backend.api.endpoints_patch import register_additional_endpoints
    ENDPOINTS_PATCH_AVAILABLE = True
except ImportError:
    ENDPOINTS_PATCH_AVAILABLE = False
    logger.warning("endpoints_patch not available, some endpoints may be missing")

# Import API routers with graceful degradation
map_router = prediction_router = property_router = recommendation_router = multi_agent_router = auth_router = None

MAP_ENDPOINTS_AVAILABLE = False

try:
    from backend.api.auth_endpoints import router as auth_router
except ImportError as exc:
    logger.warning("Auth endpoints not available: %s", exc)

try:
    from backend.api.map_endpoints import router as map_router
except ImportError as exc:
    logger.warning("Map endpoints not available: %s", exc)

try:
    from backend.api.prediction_endpoints import router as prediction_router
except ImportError as exc:
    logger.warning("Prediction endpoints not available: %s", exc)

try:
    from backend.api.property_endpoints import router as property_router
except ImportError as exc:
    logger.warning("Property endpoints not available: %s", exc)

try:
    from backend.api.recommendation_endpoints import router as recommendation_router
except ImportError as exc:
    logger.warning("Recommendation endpoints not available: %s", exc)

try:
    from backend.api.multi_agent_endpoints import router as multi_agent_router
except ImportError as exc:
    logger.warning("Multi-agent endpoints not available: %s", exc)

try:
    from backend.api.data_layer_endpoints import router as data_layer_router
    from backend.api.settings_endpoints import router as settings_router
except ImportError as exc:
    data_layer_router = None
    settings_router = None
    logger.warning("Data layer endpoints or settings endpoints not available: %s", exc)

try:
    from backend.api.city_intel_endpoints import router as city_intel_router
except ImportError as exc:
    city_intel_router = None
    logger.warning("City intelligence endpoints not available: %s", exc)

try:
    from backend.api.digital_twin_endpoints import router as digital_twin_router
except ImportError as exc:
    digital_twin_router = None
    logger.warning("Digital twin endpoints not available: %s", exc)

try:
    from backend.api.llm_endpoints import router as llm_router
except ImportError as exc:
    llm_router = None
    logger.warning("LLM management endpoints not available: %s", exc)

try:
    from backend.api.scraping_endpoints import router as scraping_router
except ImportError as exc:
    scraping_router = None
    logger.warning("Scraping endpoints not available: %s", exc)

try:
    from backend.api.voice_endpoints import router as voice_router
except ImportError as exc:
    voice_router = None
    logger.warning("Voice endpoints not available: %s", exc)

try:
    from backend.api.error_endpoints import router as error_router
except ImportError as exc:
    error_router = None
    logger.warning("Error logging endpoints not available: %s", exc)

# Determine availability based on critical routers
if map_router is not None:
    MAP_ENDPOINTS_AVAILABLE = True

# Setup logging
logger = setup_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Valora v1.0 API",
    description="Real Estate Analytics Platform with AI-powered predictions",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3003",
        "http://127.0.0.1:3003",
    ],
    # Allow any localhost or 127.0.0.1 origin/port (supports preview proxy like 127.0.0.1:55956)
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
settings = Settings()
dmpe_engine = DMPEEngine()
data_processor = DataProcessor()
mappls_service = MapplsService()
retraining_service = ModelRetrainingService()
scheduler = None  # Scheduler removed - use model_retraining service directly
multi_agent_orchestrator = ValoraOrchestrator(
    dmpe_service=dmpe_engine,
    mappls_service=mappls_service,
    db_service=None  # Add database service if needed
)

# Register additional endpoints if available
if ENDPOINTS_PATCH_AVAILABLE:
    app = register_additional_endpoints(app, dmpe_engine, data_processor)
else:
    # Add fallback endpoints
    @app.post("/api/predict/price")
    async def predict_price_fallback(request: Dict[str, Any]):
        try:
            predictions = dmpe_engine.predict(request)
            return {
                "status": "success",
                "predicted_price": predictions.get("price", {}).get("predicted", 0),
                "confidence": 0.75
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/market/properties")
    async def list_properties_fallback(city: str, limit: int = 10):
        return {
            "status": "success",
            "properties": [],
            "message": "Using fallback endpoint"
        }

# Pydantic models for request/response
class PropertyInput(BaseModel):
    """Input model for property prediction"""
    id: Optional[str] = Field(None, description="Property ID")
    city: str = Field(..., description="City name")
    locality: str = Field(..., description="Locality/Area name")
    property_type: str = Field(..., description="Type: apartment, house, plot, commercial")
    bedrooms: int = Field(2, description="Number of bedrooms")
    bathrooms: int = Field(2, description="Number of bathrooms")
    area_sqft: float = Field(..., description="Property area in sqft")
    floor: Optional[int] = Field(None, description="Floor number")
    total_floors: Optional[int] = Field(None, description="Total floors in building")
    age_years: Optional[int] = Field(5, description="Age of property in years")
    parking_spaces: Optional[int] = Field(1, description="Number of parking spaces")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    amenities: Optional[List[str]] = Field([], description="List of amenities")

class ForecastRequest(BaseModel):
    """Request model for comprehensive forecasting"""
    property: PropertyInput
    forecast_months: int = Field(12, description="Number of months to forecast")
    include_comparables: bool = Field(True, description="Include comparable properties")
    include_market_trends: bool = Field(True, description="Include market trend analysis")

class MarketAnalysisRequest(BaseModel):
    """Request model for market analysis"""
    city: str
    localities: Optional[List[str]] = None
    property_types: Optional[List[str]] = None
    price_range: Optional[Dict[str, float]] = None
    analysis_type: str = Field("comprehensive", description="Type: comprehensive, hotspots, growth")

class PortfolioRequest(BaseModel):
    """Request model for portfolio analysis"""
    properties: List[PropertyInput]
    optimization_goal: str = Field("balanced", description="Goal: yield, growth, balanced")

# Register auth endpoints first
if auth_router is not None:
    app.include_router(auth_router)
    logger.info("Auth endpoints registered")

# Register map and related endpoints if available
if map_router is not None:
    app.include_router(map_router)
    logger.info("Map endpoints registered")

if prediction_router is not None:
    app.include_router(prediction_router)
    logger.info("Prediction endpoints registered")

if property_router is not None:
    app.include_router(property_router)
    logger.info("Property endpoints registered")

if recommendation_router is not None:
    app.include_router(recommendation_router)
    logger.info("Recommendation endpoints registered")

if multi_agent_router is not None:
    app.include_router(multi_agent_router)
    logger.info("Multi-agent endpoints registered")

if data_layer_router is not None:
    app.include_router(data_layer_router)
    logger.info("Data layer endpoints registered")

if settings_router is not None:
    app.include_router(settings_router)
    logger.info("Cloud services settings endpoints registered")

if city_intel_router is not None:
    app.include_router(city_intel_router)
    logger.info("City intelligence endpoints registered")

if digital_twin_router is not None:
    app.include_router(digital_twin_router)
    logger.info("Digital twin endpoints registered")

if llm_router is not None:
    app.include_router(llm_router)
    logger.info("LLM management endpoints registered")

if scraping_router is not None:
    app.include_router(scraping_router)
    logger.info("Scraping endpoints registered")

if voice_router is not None:
    app.include_router(voice_router)
    logger.info("Voice endpoints registered")

if error_router is not None:
    app.include_router(error_router)
    logger.info("Error logging endpoints registered")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "dmpe": "active",
            "mappls": mappls_service.is_connected(),
            "data_processor": "active"
        }
    }

# Debug endpoint to test CORS and API availability
@app.get("/api/debug")
async def debug_endpoint():
    """Debug endpoint that returns basic info to test connectivity and CORS"""
    return {
        "message": "API is accessible",
        "timestamp": datetime.now().isoformat(),
        "cors": "working if you can see this",
        "properties_endpoint": "/api/properties?limit=300&zoom=12"
    }

# Main prediction endpoint
@app.post("/api/forecast")
async def forecast(request: ForecastRequest) -> Dict[str, Any]:
    """
    Comprehensive forecast endpoint returning price, rental yield, and demand index
    """
    try:
        # Convert property input to dict
        property_data = request.property.dict()
        
        # Get DMPE predictions
        predictions = dmpe_engine.predict(property_data)
        
        # Add time series forecast if requested
        if request.forecast_months > 0:
            # This would need historical data - for now, we'll simulate
            forecast_data = {
                "months": request.forecast_months,
                "price_trend": "increasing",
                "expected_appreciation": 8.5,  # percentage
                "confidence": 0.75
            }
            predictions["time_series_forecast"] = forecast_data
        
        # Get comparable properties if requested
        if request.include_comparables:
            comparables = await get_comparable_properties(property_data)
            predictions["comparables"] = comparables
        
        # Get market trends if requested
        if request.include_market_trends:
            trends = await get_market_trends(property_data["city"], property_data.get("locality"))
            predictions["market_trends"] = trends
        
        return {
            "status": "success",
            "data": predictions,
            "metadata": {
                "model_version": "2.0",
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Forecast error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Demand index endpoint
@app.post("/api/demand")
async def get_demand_index(property_input: PropertyInput) -> Dict[str, Any]:
    """
    Get demand index for a specific property or area
    """
    try:
        property_data = property_input.dict()
        
        # Get spatial features from Mappls
        if property_data.get("latitude") and property_data.get("longitude"):
            spatial_features = dmpe_engine.fetch_mappls_spatial_features(
                property_data["latitude"],
                property_data["longitude"]
            )
            property_data.update(spatial_features)
        
        # Calculate demand index
        predictions = dmpe_engine.predict(property_data)
        demand_data = predictions.get("demand_index", {})
        
        return {
            "status": "success",
            "demand_index": demand_data,
            "factors": {
                "infrastructure": property_data.get("infrastructure_score", 5),
                "poi_density": property_data.get("poi_density", 10),
                "market_activity": "moderate",
                "price_trend": "stable"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Demand calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Rental yield endpoint
@app.post("/api/rental-yield")
async def calculate_rental_yield(property_input: PropertyInput) -> Dict[str, Any]:
    """
    Calculate rental yield for a property
    """
    try:
        property_data = property_input.dict()
        predictions = dmpe_engine.predict(property_data)
        rental_data = predictions.get("rental_yield", {})
        
        return {
            "status": "success",
            "rental_yield": rental_data,
            "comparison": {
                "city_average": 3.5,
                "locality_average": 3.8,
                "property_type_average": 3.6
            },
            "recommendation": _get_rental_recommendation(rental_data.get("predicted_percentage", 0)),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Rental yield error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Market analysis endpoint
@app.post("/api/market-analysis")
async def analyze_market(request: MarketAnalysisRequest) -> Dict[str, Any]:
    """
    Comprehensive market analysis for a city or localities
    """
    try:
        analysis = {
            "city": request.city,
            "timestamp": datetime.now().isoformat(),
            "summary": {}
        }
        
        if request.analysis_type == "hotspots":
            # Identify investment hotspots
            hotspots = await identify_hotspots(request.city, request.localities)
            analysis["hotspots"] = hotspots
            
        elif request.analysis_type == "growth":
            # Growth zone analysis
            growth_zones = await analyze_growth_zones(request.city)
            analysis["growth_zones"] = growth_zones
            
        else:  # comprehensive
            # Full market analysis
            market_data = await comprehensive_market_analysis(request)
            analysis.update(market_data)
        
        return {
            "status": "success",
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Market analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Portfolio optimization endpoint
@app.post("/api/portfolio/optimize")
async def optimize_portfolio(request: PortfolioRequest) -> Dict[str, Any]:
    """
    Analyze and optimize a real estate portfolio
    """
    try:
        portfolio_analysis = {
            "total_properties": len(request.properties),
            "optimization_goal": request.optimization_goal,
            "current_metrics": {},
            "recommendations": []
        }
        
        # Analyze each property
        property_analyses = []
        total_value = 0
        total_rental_yield = 0
        
        for prop in request.properties:
            prop_data = prop.dict()
            predictions = dmpe_engine.predict(prop_data)
            
            property_analyses.append({
                "property_id": prop_data.get("id", "unknown"),
                "predictions": predictions,
                "score": predictions.get("investment_metrics", {}).get("investment_score", 50)
            })
            
            total_value += predictions.get("price", {}).get("predicted", 0)
            total_rental_yield += predictions.get("rental_yield", {}).get("predicted_percentage", 0)
        
        # Calculate portfolio metrics
        portfolio_analysis["current_metrics"] = {
            "total_value": total_value,
            "average_rental_yield": total_rental_yield / len(request.properties) if request.properties else 0,
            "risk_distribution": _calculate_risk_distribution(property_analyses),
            "diversification_score": _calculate_diversification_score(request.properties)
        }
        
        # Generate optimization recommendations
        portfolio_analysis["recommendations"] = _generate_portfolio_recommendations(
            property_analyses,
            request.optimization_goal
        )
        
        portfolio_analysis["optimized_metrics"] = {
            "expected_improvement": "15-20%",
            "suggested_actions": _get_optimization_actions(request.optimization_goal)
        }
        
        return {
            "status": "success",
            "portfolio_analysis": portfolio_analysis,
            "properties": property_analyses
        }
        
    except Exception as e:
        logger.error(f"Portfolio optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Risk assessment endpoint
@app.post("/api/risk")
async def assess_risk(property_input: PropertyInput) -> Dict[str, Any]:
    """
    Comprehensive risk assessment for a property
    """
    try:
        property_data = property_input.dict()
        predictions = dmpe_engine.predict(property_data)
        
        risk_factors = {
            "market_risk": _calculate_market_risk(predictions),
            "liquidity_risk": _calculate_liquidity_risk(predictions),
            "location_risk": _calculate_location_risk(property_data),
            "regulatory_risk": "low",  # Would need regulatory data
            "environmental_risk": "medium"  # Would need environmental data
        }
        
        overall_risk = sum([
            _risk_to_score(risk) for risk in risk_factors.values()
        ]) / len(risk_factors)
        
        return {
            "status": "success",
            "risk_assessment": {
                "overall_risk_score": overall_risk,
                "risk_level": _score_to_risk_level(overall_risk),
                "factors": risk_factors,
                "mitigation_strategies": _get_risk_mitigation_strategies(risk_factors)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Risk assessment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Recommendation endpoint
@app.post("/api/recommend")
async def get_recommendations(
    budget_min: float,
    budget_max: float,
    city: str,
    property_type: Optional[str] = None,
    purpose: str = "investment"
) -> Dict[str, Any]:
    """
    Get property recommendations based on criteria
    """
    try:
        # This would typically query a database
        # For now, we'll return simulated recommendations
        recommendations = {
            "criteria": {
                "budget_range": [budget_min, budget_max],
                "city": city,
                "property_type": property_type,
                "purpose": purpose
            },
            "recommendations": [
                {
                    "id": "prop_001",
                    "score": 85,
                    "reason": "High rental yield and growing area",
                    "expected_roi": 12.5,
                    "risk_level": "low"
                },
                {
                    "id": "prop_002",
                    "score": 78,
                    "reason": "Good capital appreciation potential",
                    "expected_roi": 10.2,
                    "risk_level": "medium"
                }
            ],
            "market_insights": [
                "Current market favors buyers",
                "Expected 8-10% appreciation in next 2 years",
                "High demand in IT corridor areas"
            ]
        }
        
        return {
            "status": "success",
            "data": recommendations,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# DMPE-style compatibility endpoints used by the Node proxy and legacy UI hooks
# ---------------------------------------------------------------------------

@app.get("/api/market/summary")
async def get_market_summary() -> Dict[str, Any]:
    """Return market summary in format expected by frontend"""
    try:
        # Default to Bangalore for primary stats
        primary_city = "Bangalore"
        zones = await multi_agent_orchestrator.map_agent._identify_zones(
            city=primary_city,
            budget={"min": 0, "max": 20000000},
            property_type="3BHK"
        )
        
        # Calculate stats from zones
        if zones:
            prices = [z.get("base_price", 7000000) for z in zones]
            ppsf_list = [z.get("avg_price_sqft", 6500) for z in zones]
            avg_price = sum(prices) / len(prices)
            price_per_sqft = sum(ppsf_list) / len(ppsf_list)
            total_listings = len(zones) * 250
            # Get top 3 hot areas by price
            sorted_zones = sorted(zones, key=lambda z: z.get("avg_price_sqft", 0), reverse=True)
            hot_areas = ", ".join([z.get("name", "Unknown")[:15] for z in sorted_zones[:3]])
        else:
            # Fallback defaults for Bangalore
            avg_price = 8500000
            price_per_sqft = 7200
            total_listings = 12500
            hot_areas = "Whitefield, Koramangala, HSR Layout"
        
        return {
            "avg_price": avg_price,
            "total_listings": total_listings,
            "price_per_sqft": price_per_sqft,
            "hot_areas": hot_areas,
            "city": primary_city
        }
    except Exception as e:
        logger.error(f"Market summary error: {e}")
        # Return fallback data instead of error to keep UI working
        return {
            "avg_price": 8500000,
            "total_listings": 12500,
            "price_per_sqft": 7200,
            "hot_areas": "Whitefield, Koramangala, HSR Layout",
            "city": "Bangalore"
        }


@app.get("/api/market/hotspots")
async def get_market_hotspots(city: Optional[str] = None) -> Dict[str, Any]:
    try:
        target_city = city or "Bangalore"
        zones = await multi_agent_orchestrator.map_agent._identify_zones(  # type: ignore
            city=target_city,
            budget={"min": 0, "max": 20000000},
            property_type="3BHK"
        )
        hotspots = []
        for z in zones:
            score = min(100.0, max(0.0, (z.get("avg_price_sqft", 6000) - 4000) / 40))
            hotspots.append({
                "locality": z.get("name", "Unknown"),
                "investment_score": round(score, 2)
            })
        return {"hotspots": hotspots}
    except Exception as e:
        logger.error(f"Hotspots error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/price-distribution")
async def price_distribution(city: Optional[str] = None, property_type: Optional[str] = None) -> Dict[str, Any]:
    try:
        target_city = city or "Bangalore"
        zones = await multi_agent_orchestrator.map_agent._identify_zones(  # type: ignore
            city=target_city,
            budget={"min": 0, "max": 20000000},
            property_type=property_type or "3BHK"
        )
        prices = [z.get("base_price", 7000000) for z in zones]
        if not prices:
            prices = [6000000, 7000000, 8000000, 9000000, 10000000]
        min_p, max_p = min(prices), max(prices)
        buckets = []
        step = max(1, int((max_p - min_p) / 8_00_000)) * 100000  # ~8 buckets
        cur = int(min_p // 100000) * 100000
        while cur <= max_p + step:
            nxt = cur + step
            count = len([p for p in prices if cur <= p < nxt])
            buckets.append({
                "range": f"₹{cur//100000}L - ₹{nxt//100000}L",
                "count": count
            })
            cur = nxt
        return {"histogram": buckets}
    except Exception as e:
        logger.error(f"Price distribution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/properties/list")
async def list_properties(
    limit: int = 50,
    city: Optional[str] = "Bangalore",
    property_type: Optional[str] = None
) -> Dict[str, Any]:
    """Get properties for map display"""
    try:
        import json
        import glob
        import os
        
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
        properties = []
        
        # Load from JSON files
        json_files = glob.glob(os.path.join(data_dir, "bangalore-*.json"))
        
        for json_file in json_files[:3]:  # Limit files to load
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        properties.extend(data[:limit//3])  # Distribute limit across files
            except Exception as e:
                logger.warning(f"Could not load {json_file}: {e}")
        
        # Filter and limit
        properties = properties[:limit]
        
        return {
            "properties": properties,
            "count": len(properties),
            "total": len(properties)
        }
    except Exception as e:
        logger.error(f"List properties error: {e}")
        return {"properties": [], "count": 0, "total": 0}

@app.get("/api/properties")
async def properties_alias(
    limit: Optional[int] = None,
    city: Optional[str] = "Bangalore",
    zoom: Optional[float] = None
) -> Dict[str, Any]:
    """Alias endpoint used by frontend to fetch properties for map markers."""
    try:
        import json
        from pathlib import Path

        props: List[Dict[str, Any]] = []

        # Determine effective limit based on zoom if not provided explicitly
        effective_zoom = zoom if zoom is not None else 12.0
        if limit is None:
            if effective_zoom < 11:
                limit = 250
            elif effective_zoom < 13:
                limit = 450
            elif effective_zoom < 15:
                limit = 700
            else:
                limit = 900
        else:
            limit = int(limit)

        if limit <= 0:
            # Treat non-positive limit as "fetch everything"
            limit = 100_000

        # Ensure we still have a reasonable minimum to populate the map
        limit = max(100, limit)

        project_root = Path(__file__).resolve().parents[2]
        processed_dir = project_root / "data" / "processed"
        if not processed_dir.exists():
            processed_dir = Path.cwd() / "data" / "processed"
        json_files = sorted(processed_dir.glob("bangalore-*processed.json"))

        def extract_coords(entry: Dict[str, Any]) -> Optional[tuple[float, float]]:
            loc = entry.get("location")
            if isinstance(loc, dict):
                coords = loc.get("coordinates") or {}
                if isinstance(coords, dict):
                    lat = coords.get("lat") or coords.get("latitude")
                    lon = coords.get("lon") or coords.get("lng") or coords.get("longitude")
                    try:
                        if lat is not None and lon is not None:
                            return float(lat), float(lon)
                    except Exception:
                        return None
                lat = loc.get("lat") or loc.get("latitude")
                lon = loc.get("lon") or loc.get("lng") or loc.get("longitude")
                try:
                    if lat is not None and lon is not None:
                        return float(lat), float(lon)
                except Exception:
                    return None
            if isinstance(loc, (list, tuple)) and len(loc) >= 2:
                try:
                    return float(loc[0]), float(loc[1])
                except Exception:
                    return None
            return None

        parsed_files: List[List[Dict[str, Any]]] = []

        for json_path in json_files:
            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
            except Exception as json_err:
                logger.warning(f"properties_alias: could not parse {json_path.name}: {json_err}")
                continue

            if isinstance(data, dict):
                records = data.get("properties") or data.get("items") or []
            else:
                records = data

            if not isinstance(records, list):
                records = []

            parsed_files.append(records)

        usable_files = [records for records in parsed_files if records]
        file_count = len(usable_files) or len(parsed_files) or 1
        per_file_quota = max(10, limit // file_count)
        seen_locations: set[str] = set()

        def city_matches(entry: Dict[str, Any]) -> bool:
            if not city:
                return True
            entry_city = entry.get("city") or entry.get("city_name")
            entry_loc = entry.get("location", {}).get("city") if isinstance(entry.get("location"), dict) else None
            city_text = str(entry_city or entry_loc or "")
            return not city_text or str(city).lower() in city_text.lower()

        def add_entry_if_valid(entry: Dict[str, Any]) -> bool:
            coords = extract_coords(entry)
            if not coords:
                return False

            lat, lon = coords
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return False

            location_str = f"{lat},{lon}"
            if not location_str or location_str in seen_locations:
                return False

            if not city_matches(entry):
                return False

            price = entry.get("price") or entry.get("pricing", {}).get("total_price")
            try:
                price_val = float(price) if price is not None else 0.0
            except Exception:
                price_val = 0.0

            props.append({
                "name": entry.get("name") or entry.get("title") or "Property",
                "price": price_val,
                "currency": entry.get("currency") or entry.get("pricing", {}).get("currency", "₹") or "₹",
                "bedrooms": entry.get("metadata", {}).get("bedrooms") if isinstance(entry.get("metadata"), dict) else entry.get("bedrooms"),
                "covered_area": entry.get("metadata", {}).get("area_sqft")
                if isinstance(entry.get("metadata"), dict) else entry.get("area_sqft"),
                "address": entry.get("location", {}).get("locality") if isinstance(entry.get("location"), dict) else entry.get("address", ""),
                "city_name": entry.get("location", {}).get("city") if isinstance(entry.get("location"), dict) else (entry.get("city") or city or "Bangalore"),
                "property_type": entry.get("property_type") or "residential_apartment",
                "location": location_str
            })

            seen_locations.add(location_str)
            return True

        # First pass: ensure each dataset contributes up to per_file_quota entries
        for records in parsed_files:
            if len(props) >= limit:
                break
            if not records:
                continue

            added_from_file = 0
            for entry in records:
                if len(props) >= limit or added_from_file >= per_file_quota:
                    break
                if not isinstance(entry, dict):
                    continue
                if add_entry_if_valid(entry):
                    added_from_file += 1

        # Second pass: fill any remaining slots regardless of per-file quotas
        if len(props) < limit:
            for records in parsed_files:
                if len(props) >= limit:
                    break
                if not records:
                    continue

                for entry in records:
                    if len(props) >= limit:
                        break
                    if not isinstance(entry, dict):
                        continue
                    add_entry_if_valid(entry)

        if not props:
            zones = await multi_agent_orchestrator.map_agent._identify_zones(  # type: ignore
                city=city or "Bangalore",
                budget={"min": 0, "max": 20000000},
                property_type="3BHK"
            )
            for z in zones[:limit]:
                lat, lon = z.get("centroid", [12.97, 77.59])
                location_str = f"{lat},{lon}"
                if location_str in seen_locations:
                    continue
                props.append({
                    "name": z.get("name", "Property"),
                    "price": z.get("base_price", 8000000),
                    "currency": "₹",
                    "bedrooms": 3,
                    "covered_area": 1200,
                    "address": z.get("name", ""),
                    "city_name": city or "Bangalore",
                    "property_type": "residential_apartment",
                    "location": f"{lat},{lon}"
                })
                seen_locations.add(location_str)

        return {"properties": props[:limit], "count": min(len(props), limit), "limit": limit, "zoom": effective_zoom}
    except Exception as e:
        logger.error(f"properties_alias error: {e}")
        return {"properties": [], "count": 0}

@app.get("/api/properties/top")
async def top_properties(
    city: Optional[str] = None,
    property_type: Optional[str] = None,
    limit: int = 10,
    sort_by: str = "investment_score",
    order: str = "desc"
) -> Dict[str, Any]:
    try:
        target_city = city or "Bangalore"
        zones = await multi_agent_orchestrator.map_agent._identify_zones(  # type: ignore
            city=target_city,
            budget={"min": 0, "max": 20000000},
            property_type=property_type or "3BHK"
        )
        props = []
        for z in zones:
            lat, lon = z.get("centroid", [12.97, 77.59])
            base = z.get("base_price", 7000000)
            props.append({
                "locality": z.get("name", "Unknown"),
                "price": base,
                "bedrooms": 3,
                "area_sqft": 1200,
                "latitude": lat,
                "longitude": lon,
                "investment_score": round(min(1.0, z.get("avg_price_sqft", 6000)/10000) * 100, 2)
            })
        props.sort(key=lambda p: p.get("investment_score", 0), reverse=(order.lower()=="desc"))
        return {"properties": props[:max(1, min(50, limit))]}
    except Exception as e:
        logger.error(f"Top properties error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/query")
async def rag_query(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        query = str(payload.get("query", "") or "")
        top_k = int(payload.get("top_k", 10))
        city = payload.get("city")
        property_type = payload.get("property_type")
        
        # Local search only (Pinecone removed)
        df_list: List[pd.DataFrame] = []
        gp_path = Path("data/processed/google_places_processed.csv")
        if gp_path.exists():
            try:
                df_list.append(pd.read_csv(gp_path, low_memory=False))
            except Exception:
                pass
        training_path = Path("data/processed/processed_training_data.csv")
        if training_path.exists():
            try:
                df_list.append(pd.read_csv(training_path, low_memory=False))
            except Exception:
                pass
        if not df_list:
            return {"matches": []}
        df = pd.concat(df_list, ignore_index=True)
        mask = pd.Series([True] * len(df), index=df.index)
        if city and "city" in df.columns:
            mask = mask & df["city"].astype(str).str.contains(str(city), case=False, na=False)
        if property_type and "property_type" in df.columns:
            mask = mask & df["property_type"].astype(str).str.contains(str(property_type), case=False, na=False)
        if query:
            cols = [c for c in ["name", "locality", "place_category", "address", "description"] if c in df.columns]
            if cols:
                # Build a combined lowercase text blob for each row
                text_df = df[cols].fillna("").astype(str)
                text_series = text_df.apply(lambda r: " ".join(r.values).lower(), axis=1)
                # Simple tokenization with stop-word removal
                tokens = [t for t in query.lower().split() if len(t) > 2 and t not in {"the","and","for","with","near","in","of","to"}]
                if tokens:
                    token_mask = pd.Series([True] * len(df), index=df.index)
                    for tok in tokens:
                        token_mask = token_mask & text_series.str.contains(tok, case=False, na=False)
                    mask = mask & token_mask
        filtered = df[mask].head(max(1, min(100, top_k))).copy()
        results: List[Dict[str, Any]] = []
        for _, r in filtered.iterrows():
            try:
                rating = float(r.get("place_rating", 0))
            except Exception:
                rating = 0.0
            results.append({
                "id": r.get("id", None),
                "name": r.get("name", r.get("locality", "")),
                "locality": r.get("locality", ""),
                "city": r.get("city", ""),
                "place_category": r.get("place_category", r.get("property_type", "")),
                "rating": rating,
                "latitude": r.get("latitude", None),
                "longitude": r.get("longitude", None),
                "address": r.get("address", "")
            })
        return {"matches": results}
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Training endpoint
@app.post("/api/train")
async def train_models(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Trigger model training in the background
    """
    try:
        # Add training task to background
        background_tasks.add_task(train_dmpe_models)
        
        return {
            "status": "success",
            "message": "Model training initiated in background",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Training initiation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def get_comparable_properties(property_data: Dict) -> List[Dict]:
    """Get comparable properties for analysis"""
    # Simulated data - would typically query database
    return [
        {
            "id": "comp_001",
            "similarity_score": 0.92,
            "price": property_data.get("price", 5000000) * 1.05,
            "location": "2km away"
        }
    ]

async def get_market_trends(city: str, locality: Optional[str]) -> Dict:
    """Get market trends for a location"""
    return {
        "price_trend": "increasing",
        "yoy_growth": 8.5,
        "qoq_growth": 2.1,
        "forecast_next_quarter": 2.5
    }

async def identify_hotspots(city: str, localities: Optional[List[str]]) -> List[Dict]:
    """Identify investment hotspots"""
    return [
        {
            "locality": "IT Corridor",
            "hotspot_score": 85,
            "factors": ["Metro connectivity", "IT parks", "Schools"]
        }
    ]

async def analyze_growth_zones(city: str) -> List[Dict]:
    """Analyze growth zones in a city"""
    return [
        {
            "zone": "North Zone",
            "growth_potential": "high",
            "expected_appreciation": 12.5,
            "key_drivers": ["Infrastructure", "Commercial development"]
        }
    ]

async def comprehensive_market_analysis(request: MarketAnalysisRequest) -> Dict:
    """Perform comprehensive market analysis"""
    return {
        "market_size": "₹2.5 Trillion",
        "active_listings": 15420,
        "average_price_psf": 5500,
        "market_sentiment": "positive",
        "key_trends": [
            "Shift towards affordable housing",
            "Increased demand in periphery",
            "Rise in co-working spaces"
        ]
    }

def train_dmpe_models():
    """Background task to train DMPE models"""
    try:
        # Load training data
        data = data_processor.load_training_data()
        
        # Train models
        dmpe_engine.train_price_model(data)
        dmpe_engine.train_rental_yield_model(data)
        dmpe_engine.train_demand_model(data)
        
        # Save models
        dmpe_engine.save_all_models()
        
        logger.info("Model training completed successfully")
    except Exception as e:
        logger.error(f"Model training failed: {e}")

def _get_rental_recommendation(rental_yield: float) -> str:
    """Generate rental recommendation based on yield"""
    if rental_yield > 4:
        return "Excellent rental investment opportunity"
    elif rental_yield > 3:
        return "Good rental returns, above market average"
    elif rental_yield > 2:
        return "Average rental returns, consider for long-term appreciation"
    else:
        return "Below average rental returns, better suited for self-use"

def _calculate_risk_distribution(analyses: List[Dict]) -> Dict[str, int]:
    """Calculate risk distribution across portfolio"""
    risk_dist = {"low": 0, "medium": 0, "high": 0}
    for analysis in analyses:
        risk = analysis.get("predictions", {}).get("investment_metrics", {}).get("risk_level", "medium")
        risk_dist[risk.lower()] = risk_dist.get(risk.lower(), 0) + 1
    return risk_dist

def _calculate_diversification_score(properties: List[PropertyInput]) -> float:
    """Calculate portfolio diversification score"""
    # Simple diversification based on property types and locations
    unique_types = len(set([p.property_type for p in properties]))
    unique_cities = len(set([p.city for p in properties]))
    unique_localities = len(set([p.locality for p in properties]))
    
    diversity_score = (unique_types * 30 + unique_cities * 30 + unique_localities * 40) / len(properties) if properties else 0
    return min(100, diversity_score)

def _generate_portfolio_recommendations(analyses: List[Dict], goal: str) -> List[str]:
    """Generate portfolio optimization recommendations"""
    recommendations = []
    
    if goal == "yield":
        recommendations.append("Focus on properties with rental yield > 4%")
        recommendations.append("Consider commercial properties for higher yields")
    elif goal == "growth":
        recommendations.append("Invest in emerging localities with infrastructure development")
        recommendations.append("Focus on properties in IT corridors and metro catchments")
    else:  # balanced
        recommendations.append("Maintain 60:40 ratio between growth and yield properties")
        recommendations.append("Diversify across residential and commercial segments")
    
    return recommendations

def _get_optimization_actions(goal: str) -> List[str]:
    """Get specific optimization actions based on goal"""
    if goal == "yield":
        return [
            "Sell low-yield properties",
            "Reinvest in commercial spaces",
            "Focus on ready-to-move properties"
        ]
    elif goal == "growth":
        return [
            "Invest in under-construction projects",
            "Focus on areas with upcoming infrastructure",
            "Consider land parcels in growth corridors"
        ]
    else:
        return [
            "Rebalance portfolio quarterly",
            "Maintain liquidity buffer",
            "Diversify across asset classes"
        ]

def _calculate_market_risk(predictions: Dict) -> str:
    """Calculate market risk from predictions"""
    demand_score = predictions.get("demand_index", {}).get("score", 50)
    if demand_score > 70:
        return "low"
    elif demand_score > 40:
        return "medium"
    else:
        return "high"

def _calculate_liquidity_risk(predictions: Dict) -> str:
    """Calculate liquidity risk"""
    demand_score = predictions.get("demand_index", {}).get("score", 50)
    if demand_score > 60:
        return "low"
    elif demand_score > 35:
        return "medium"
    else:
        return "high"

def _calculate_location_risk(property_data: Dict) -> str:
    """Calculate location-based risk"""
    # Simplified - would use actual location data
    return "medium"

def _risk_to_score(risk: str) -> float:
    """Convert risk level to numerical score"""
    risk_scores = {"low": 20, "medium": 50, "high": 80}
    return risk_scores.get(risk.lower(), 50)

def _score_to_risk_level(score: float) -> str:
    """Convert numerical score to risk level"""
    if score < 35:
        return "low"
    elif score < 65:
        return "medium"
    else:
        return "high"

def _get_risk_mitigation_strategies(risk_factors: Dict) -> List[str]:
    """Generate risk mitigation strategies"""
    strategies = []
    
    for factor, level in risk_factors.items():
        if level == "high":
            if "market" in factor:
                strategies.append("Consider waiting for market stabilization")
            elif "liquidity" in factor:
                strategies.append("Price competitively for faster sale")
            elif "location" in factor:
                strategies.append("Invest in property improvements")
    
    if not strategies:
        strategies.append("Maintain current strategy, risks are manageable")
    
    return strategies

# ============================================================================
# MODEL RETRAINING ENDPOINTS
# ============================================================================

@app.post("/api/models/retrain")
async def trigger_retraining(
    background_tasks: BackgroundTasks,
    force: bool = False,
    run_async: bool = True
) -> Dict[str, Any]:
    """
    Trigger model retraining
    
    Args:
        force: Force retraining even if not needed
        run_async: Run in background (recommended)
    
    Returns:
        Dictionary with retraining status or results
    """
    try:
        if run_async:
            # Run in background
            background_tasks.add_task(retraining_service.perform_full_retraining, force)
            
            return {
                "status": "started",
                "message": "Model retraining started in background",
                "forced": force,
                "timestamp": datetime.now().isoformat(),
                "check_status_at": "/api/models/retraining/status"
            }
        else:
            # Run synchronously (blocking)
            logger.info("Running synchronous retraining...")
            result = retraining_service.perform_full_retraining(force=force)
            
            return {
                "status": "completed",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Failed to trigger retraining: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models/retraining/status")
async def get_retraining_status() -> Dict[str, Any]:
    """Get current retraining status and history"""
    try:
        status = retraining_service.get_retraining_status()
        
        return {
            "status": "success",
            "retraining_status": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get retraining status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models/retraining/history")
async def get_retraining_history(limit: int = 10) -> Dict[str, Any]:
    """Get retraining history"""
    try:
        history = retraining_service.get_retraining_history(limit=limit)
        
        return {
            "status": "success",
            "history": history,
            "count": len(history),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get retraining history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/models/retraining/check")
async def check_retraining_needed() -> Dict[str, Any]:
    """Check if retraining is needed"""
    try:
        should_retrain, reason = retraining_service.check_if_retraining_needed()
        
        return {
            "status": "success",
            "retraining_needed": should_retrain,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to check retraining need: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models/scheduler/status")
async def get_scheduler_status() -> Dict[str, Any]:
    """Get scheduler status and scheduled jobs"""
    try:
        jobs = scheduler.get_scheduled_jobs() if scheduler else []
        
        return {
            "status": "success",
            "scheduler_running": scheduler.is_running if scheduler else False,
            "scheduled_jobs": jobs,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/models/scheduler/start")
async def start_scheduler(
    schedule_type: str = "cron",
    cron_expression: str = "0 2 * * 0",  # Every Sunday at 2 AM
    interval_hours: int = 168  # 7 days
) -> Dict[str, Any]:
    """
    Start the retraining scheduler
    
    Args:
        schedule_type: 'cron' or 'interval'
        cron_expression: Cron expression for scheduling
        interval_hours: Interval in hours for interval scheduling
    """
    try:
        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")
        
        # Add schedule
        if schedule_type == "cron":
            success = scheduler.add_cron_schedule(cron_expression=cron_expression)
            schedule_desc = f"cron: {cron_expression}"
        else:
            success = scheduler.add_interval_schedule(hours=interval_hours)
            schedule_desc = f"interval: every {interval_hours} hours"
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add schedule")
        
        # Start scheduler
        if not scheduler.is_running:
            success = scheduler.start()
            if not success:
                raise HTTPException(status_code=500, detail="Failed to start scheduler")
        
        return {
            "status": "success",
            "message": "Scheduler started successfully",
            "schedule": schedule_desc,
            "jobs": scheduler.get_scheduled_jobs(),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/models/scheduler/stop")
async def stop_scheduler() -> Dict[str, Any]:
    """Stop the retraining scheduler"""
    try:
        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")
        
        scheduler.stop()
        
        return {
            "status": "success",
            "message": "Scheduler stopped successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models/metrics")
async def get_model_metrics() -> Dict[str, Any]:
    """Get current model metrics"""
    try:
        status = retraining_service.get_retraining_status()
        metrics = status.get("last_metrics", {})
        
        return {
            "status": "success",
            "metrics": metrics,
            "last_retrain": status.get("last_retrain"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get model metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Multi-Agent System Endpoints
# ============================================

class AgentRequest(BaseModel):
    """Request model for multi-agent system"""
    user_id: Optional[str] = Field(None, description="User ID")
    intent: str = Field(..., description="User's natural language query")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")


@app.post("/api/agent/plan", response_model=Dict[str, Any])
async def create_agent_plan(request: AgentRequest) -> Dict[str, Any]:
    """
    Main endpoint for multi-agent system - processes user intent and returns coordinated response
    
    This endpoint coordinates all agents to:
    1. Understand user intent (Planner)
    2. Analyze zones (MapAgent)
    3. Forecast prices (Forecaster)
    4. Generate recommendations (Recommender)
    5. Validate results (Critic)
    
    The response is structured to update all three frontend panels:
    - Analysis Panel: forecasts and metrics
    - Map Panel: heatmap_url and geojson
    - AI Agent Panel: recommendations and chat response
    """
    try:
        user_id = request.user_id or "test_user"
        logger.info(f"Processing agent request for user {user_id}: {request.intent}")
        
        # Process request through multi-agent system
        response = await multi_agent_orchestrator.process_request(
            user_id=user_id,
            intent=request.intent,
            context=request.context or {}
        )
        
        logger.info(f"Agent plan {response['plan_id']} completed with confidence {response['confidence']}")
        return response
        
    except Exception as e:
        logger.error(f"Agent plan failed: {e}", exc_info=True)
        # Fallback response to ensure endpoint remains available without LLM keys
        return {
            "status": "success",
            "plan_id": "fallback",
            "confidence": 0.5,
            "recommendations": [],
            "final_result": {
                "recommendations": [],
                "forecasts": {},
                "spatial_overlays": {},
                "rag_matches": []
            },
            "plan": {
                "user_intent": request.intent,
                "tasks": []
            },
            "provenance": [],
            "human_actions": ["try_sample_queries", "check_backend_logs"],
            "validation": {"status": "error", "errors": [str(e)], "warnings": [], "confidence": 0.0, "validation_timestamp": datetime.now().isoformat()},
            "timestamp": datetime.now().isoformat(),
            "chat_response": f"I encountered an error while processing your request. Please check if the backend services are running properly. Error: {str(e)[:100]}"
        }


@app.get("/api/agent/plans", response_model=List[Dict[str, Any]])
async def get_active_plans() -> List[Dict[str, Any]]:
    """Get all active plans being executed"""
    try:
        plans = multi_agent_orchestrator.get_active_plans()
        return plans
    except Exception as e:
        logger.error(f"Failed to get active plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/plan/{plan_id}", response_model=Dict[str, Any])
async def get_plan_status(plan_id: str) -> Dict[str, Any]:
    """Get status of a specific plan"""
    try:
        status = multi_agent_orchestrator.get_plan_status(plan_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get plan status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/analyze", response_model=Dict[str, Any])
async def quick_analyze(
    city: str = "Bangalore",
    budget_max: float = 10000000,
    property_type: str = "3BHK",
    amenities: List[str] = ["metro", "school", "hospital"]
) -> Dict[str, Any]:
    """
    Quick analysis endpoint for simple property searches
    Bypasses the full multi-agent orchestration for faster response
    """
    try:
        # Create intent from parameters
        intent = f"Find {property_type} properties in {city} under {budget_max/10000000:.1f} Cr near {', '.join(amenities)}"
        
        # Process through orchestrator
        response = await multi_agent_orchestrator.process_request(
            user_id="quick_user",
            intent=intent,
            context={
                "city": city,
                "budget": {"min": 0, "max": budget_max},
                "property_type": property_type,
                "amenities": amenities
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Quick analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time agent communication
    Allows streaming responses and live updates
    """
    await websocket.accept()
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Process through multi-agent system
            response = await multi_agent_orchestrator.process_request(
                user_id=data.get("user_id", "ws_user"),
                intent=data.get("intent", ""),
                context=data.get("context", {})
            )
            
            # Send response back
            await websocket.send_json(response)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


# ============================================================================
# AIRFLOW ETL INTEGRATION ENDPOINTS
# ============================================================================

from backend.services.etl_service import ETLService

etl_service = ETLService()


class ETLRequest(BaseModel):
    """Request model for ETL operations"""
    source_file: str = Field(..., description="Path to source data file")
    operation: str = Field("full_pipeline", description="ETL operation: ingest, transform, merge, full_pipeline")


@app.post("/api/data/ingest")
async def ingest_scraped_data(request: ETLRequest) -> Dict[str, Any]:
    """
    Ingest scraped data from Airflow pipeline
    
    This endpoint receives data from Airflow DAGs after scraping
    """
    try:
        logger.info(f"Receiving data ingestion request: {request.source_file}")
        
        if request.operation == "full_pipeline":
            result = etl_service.run_full_etl_pipeline(request.source_file)
        elif request.operation == "ingest":
            result = etl_service.ingest_scraped_data(request.source_file)
        elif request.operation == "transform":
            result = etl_service.transform_for_dmpe(request.source_file)
        elif request.operation == "merge":
            result = etl_service.merge_with_training_data(request.source_file)
        else:
            raise ValueError(f"Unknown operation: {request.operation}")
        
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Data ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/stats")
async def get_etl_stats() -> Dict[str, Any]:
    """Get ETL pipeline statistics"""
    try:
        stats = etl_service.get_pipeline_stats()
        
        return {
            "status": "success",
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get ETL stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data/market-report")
async def receive_market_report(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Receive market report from Airflow enrichment pipeline
    
    This endpoint is called by the market_data_enrichment DAG
    """
    try:
        logger.info(f"Received market report: {report_data.get('type')}")
        
        # In production, store report in database or cache
        # For now, just acknowledge receipt
        
        return {
            "status": "success",
            "message": "Market report received",
            "report_timestamp": report_data.get('timestamp'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to process market report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/training-data")
async def get_training_data_info() -> Dict[str, Any]:
    """Get information about current training dataset"""
    try:
        from pathlib import Path
        import pandas as pd
        
        training_file = Path("data/processed/processed_training_data.csv")
        
        if not training_file.exists():
            return {
                "status": "success",
                "exists": False,
                "message": "No training data found"
            }
        
        df = pd.read_csv(training_file)
        
        info = {
            "exists": True,
            "total_records": len(df),
            "file_size_mb": training_file.stat().st_size / (1024 * 1024),
            "last_updated": datetime.fromtimestamp(training_file.stat().st_mtime).isoformat(),
            "columns": df.columns.tolist(),
            "cities": df['city'].unique().tolist() if 'city' in df.columns else [],
            "property_types": df['property_type'].unique().tolist() if 'property_type' in df.columns else [],
            "price_range": {
                "min": float(df['price'].min()) if 'price' in df.columns else 0,
                "max": float(df['price'].max()) if 'price' in df.columns else 0,
                "avg": float(df['price'].mean()) if 'price' in df.columns else 0
            }
        }
        
        return {
            "status": "success",
            "training_data": info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get training data info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
