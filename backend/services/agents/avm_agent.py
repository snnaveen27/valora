"""
AVM Agent - Advanced Valuation Model for property pricing
Part of VALORA-DMPE+ Enhanced Architecture
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import joblib
from pathlib import Path
from dataclasses import dataclass

# ML imports
try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    import xgboost as xgb
    from sklearn.model_selection import cross_val_score
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class ValuationResult:
    """Result from property valuation"""
    property_id: str
    estimated_value: float
    confidence_interval: Tuple[float, float]
    confidence_score: float
    value_breakdown: Dict[str, float]
    comparables: List[Dict[str, Any]]
    market_position: float  # Percentile in market
    valuation_date: datetime

class AVMAgent:
    """
    Advanced Valuation Model Agent for property pricing
    Uses ensemble of models for accurate valuation
    """
    
    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or "data/processed"
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        
        # Load pre-trained models if available
        self._load_models()
        
        # Load property data for training/comparison
        self._load_property_data()
        
        logger.info("AVMAgent initialized")
    
    def _load_models(self):
        """Load pre-trained models if available"""
        model_dir = Path("dmpe/models")
        
        # Try to load existing models
        for property_type in ["apartment", "house", "commercial"]:
            for transaction_type in ["sale", "rent"]:
                model_name = f"price_model_Bangalore_residential_{property_type}_{transaction_type}.joblib"
                model_path = model_dir / model_name
                
                if model_path.exists():
                    try:
                        self.models[f"{property_type}_{transaction_type}"] = joblib.load(model_path)
                        logger.info(f"Loaded model: {model_name}")
                    except Exception as e:
                        logger.warning(f"Could not load model {model_name}: {e}")
        
        # If no models loaded, initialize default models
        if not self.models and ML_AVAILABLE:
            self._initialize_default_models()
    
    def _initialize_default_models(self):
        """Initialize default ensemble models"""
        # XGBoost model
        self.models["xgboost"] = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        ) if ML_AVAILABLE else None
        
        # Random Forest
        self.models["random_forest"] = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        ) if ML_AVAILABLE else None
        
        # Gradient Boosting
        self.models["gradient_boosting"] = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            random_state=42
        ) if ML_AVAILABLE else None
        
        # Initialize scalers
        self.scalers["standard"] = StandardScaler() if ML_AVAILABLE else None
    
    def _load_property_data(self):
        """Load processed property data for training and comparison"""
        self.property_data = {}
        
        data_dir = Path(self.data_path)
        
        # Load all processed property files
        for file_path in data_dir.glob("bangalore-*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                    # Extract property type from filename
                    property_type = file_path.stem.replace("bangalore-", "").replace("_processed", "")
                    self.property_data[property_type] = data
                    
                    logger.info(f"Loaded {len(data)} properties from {file_path.name}")
            except Exception as e:
                logger.warning(f"Could not load {file_path}: {e}")
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute valuation action
        
        Actions:
        - estimate: Estimate property value
        - analyze: Detailed valuation analysis
        - compare: Find and analyze comparables
        - breakdown: Value breakdown by components
        - forecast: Future value forecast
        """
        
        if action == "estimate":
            return await self.estimate_value(parameters)
        elif action == "analyze":
            return await self.analyze_property(parameters)
        elif action == "compare":
            return await self.find_comparables(parameters)
        elif action == "breakdown":
            return await self.value_breakdown(parameters)
        elif action == "forecast":
            return await self.forecast_value(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def estimate_value(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate property value using ensemble models
        """
        try:
            # Extract features
            features = self._extract_features(parameters)
            
            # Get predictions from all models
            predictions = {}
            
            # Use pre-trained models if available
            property_type = parameters.get("property_type", "apartment")
            transaction_type = parameters.get("transaction_type", "sale")
            model_key = f"{property_type}_{transaction_type}"
            
            if model_key in self.models:
                # Use specific model
                model = self.models[model_key]
                if hasattr(model, 'predict'):
                    pred = model.predict([features])[0]
                    predictions["specialized"] = pred
            
            # Use ensemble models as fallback or additional predictions
            for name, model in self.models.items():
                if name not in predictions and hasattr(model, 'predict'):
                    try:
                        pred = self._safe_predict(model, features)
                        if pred is not None:
                            predictions[name] = pred
                    except:
                        pass
            
            # If no ML models, use heuristic
            if not predictions:
                predictions["heuristic"] = self._heuristic_valuation(parameters)
            
            # Calculate final estimate
            if predictions:
                final_estimate = np.mean(list(predictions.values()))
                std_dev = np.std(list(predictions.values())) if len(predictions) > 1 else final_estimate * 0.1
            else:
                final_estimate = self._heuristic_valuation(parameters)
                std_dev = final_estimate * 0.15
            
            # Calculate confidence interval
            confidence_interval = (
                final_estimate - 1.96 * std_dev,
                final_estimate + 1.96 * std_dev
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence(predictions, parameters)
            
            # Find comparables
            comparables = await self._find_similar_properties(parameters, limit=5)
            
            # Market position
            market_position = self._calculate_market_position(final_estimate, parameters)
            
            return {
                "status": "success",
                "valuation": {
                    "estimated_value": float(final_estimate),
                    "confidence_interval": {
                        "lower": float(confidence_interval[0]),
                        "upper": float(confidence_interval[1])
                    },
                    "confidence_score": float(confidence_score),
                    "currency": "INR",
                    "per_sqft_value": float(final_estimate / parameters.get("size", 1000))
                },
                "model_predictions": {k: float(v) for k, v in predictions.items()},
                "comparables": comparables[:3],  # Top 3 comparables
                "market_position": {
                    "percentile": float(market_position),
                    "category": self._categorize_market_position(market_position)
                },
                "valuation_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Valuation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "fallback_estimate": self._heuristic_valuation(parameters)
            }
    
    def _extract_features(self, parameters: Dict[str, Any]) -> List[float]:
        """
        Extract features for ML models
        """
        features = []
        
        # Basic features
        features.append(parameters.get("size", 1000))  # Size in sqft
        features.append(parameters.get("bedrooms", 2))
        features.append(parameters.get("bathrooms", 2))
        features.append(parameters.get("age", 5))
        features.append(parameters.get("floor", 2))
        features.append(parameters.get("total_floors", 10))
        
        # Location features (simplified - would use actual coordinates in production)
        features.append(parameters.get("latitude", 12.9716))
        features.append(parameters.get("longitude", 77.5946))
        
        # Amenity features (binary)
        amenities = parameters.get("amenities", [])
        features.append(1 if "parking" in amenities else 0)
        features.append(1 if "gym" in amenities else 0)
        features.append(1 if "swimming_pool" in amenities else 0)
        features.append(1 if "security" in amenities else 0)
        
        # Property type encoding
        property_type = parameters.get("property_type", "apartment")
        features.append(1 if property_type == "apartment" else 0)
        features.append(1 if property_type == "house" else 0)
        features.append(1 if property_type == "villa" else 0)
        
        # Furnishing status
        furnishing = parameters.get("furnishing", "semi")
        features.append(1 if furnishing == "furnished" else 0)
        features.append(1 if furnishing == "semi" else 0)
        
        return features
    
    def _safe_predict(self, model, features: List[float]) -> Optional[float]:
        """
        Safely predict with error handling
        """
        try:
            # Ensure features match model expectations
            if hasattr(model, 'n_features_in_'):
                expected = model.n_features_in_
                if len(features) < expected:
                    # Pad with zeros
                    features = features + [0] * (expected - len(features))
                elif len(features) > expected:
                    # Truncate
                    features = features[:expected]
            
            # Make prediction
            pred = model.predict([features])[0]
            return float(pred)
        except Exception as e:
            logger.warning(f"Prediction failed: {e}")
            return None
    
    def _heuristic_valuation(self, parameters: Dict[str, Any]) -> float:
        """
        Heuristic-based valuation as fallback
        """
        # Base price per sqft based on location (simplified)
        base_price_per_sqft = 5000  # Default Bangalore average
        
        # Adjust for area (simplified zones)
        area = parameters.get("area", "").lower()
        if any(premium in area for premium in ["koramangala", "indiranagar", "whitefield"]):
            base_price_per_sqft *= 1.3
        elif any(budget in area for budget in ["electronic city", "marathahalli"]):
            base_price_per_sqft *= 0.9
        
        # Calculate base value
        size = parameters.get("size", 1000)
        base_value = size * base_price_per_sqft
        
        # Adjust for bedrooms
        bedrooms = parameters.get("bedrooms", 2)
        base_value *= (1 + (bedrooms - 2) * 0.1)
        
        # Adjust for age
        age = parameters.get("age", 5)
        depreciation = min(0.3, age * 0.02)  # 2% per year, max 30%
        base_value *= (1 - depreciation)
        
        # Adjust for floor
        floor = parameters.get("floor", 2)
        total_floors = parameters.get("total_floors", 10)
        if floor == 0:  # Ground floor
            base_value *= 0.95
        elif floor == total_floors:  # Top floor
            base_value *= 1.05
        
        # Adjust for amenities
        amenities = parameters.get("amenities", [])
        amenity_multiplier = 1 + len(amenities) * 0.02  # 2% per amenity
        base_value *= amenity_multiplier
        
        # Adjust for furnishing
        furnishing = parameters.get("furnishing", "unfurnished")
        if furnishing == "furnished":
            base_value *= 1.15
        elif furnishing == "semi":
            base_value *= 1.07
        
        return base_value
    
    async def _find_similar_properties(self, parameters: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar properties for comparison
        """
        comparables = []
        
        # Get property type
        property_type = parameters.get("property_type", "apartment")
        transaction_type = parameters.get("transaction_type", "sale")
        
        # Look for matching dataset
        for key, properties in self.property_data.items():
            if property_type in key and transaction_type in key:
                # Filter similar properties
                for prop in properties[:100]:  # Limit search for performance
                    similarity_score = self._calculate_similarity(parameters, prop)
                    
                    if similarity_score > 0.7:  # Similarity threshold
                        comparables.append({
                            "property_id": prop.get("id", "unknown"),
                            "price": prop.get("price", 0),
                            "size": prop.get("size", 0),
                            "bedrooms": prop.get("bedrooms", 0),
                            "location": prop.get("location", ""),
                            "similarity_score": similarity_score,
                            "price_per_sqft": prop.get("price", 0) / max(1, prop.get("size", 1))
                        })
        
        # Sort by similarity
        comparables.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return comparables[:limit]
    
    def _calculate_similarity(self, prop1: Dict, prop2: Dict) -> float:
        """
        Calculate similarity between two properties
        """
        score = 0.0
        weights = {
            "size": 0.3,
            "bedrooms": 0.2,
            "bathrooms": 0.1,
            "age": 0.1,
            "location": 0.2,
            "amenities": 0.1
        }
        
        # Size similarity
        size1 = prop1.get("size", 1000)
        size2 = prop2.get("size", 1000)
        size_diff = abs(size1 - size2) / max(size1, size2)
        score += weights["size"] * (1 - size_diff)
        
        # Bedrooms similarity
        bed1 = prop1.get("bedrooms", 2)
        bed2 = prop2.get("bedrooms", 2)
        if bed1 == bed2:
            score += weights["bedrooms"]
        elif abs(bed1 - bed2) == 1:
            score += weights["bedrooms"] * 0.5
        
        # Location similarity (simplified)
        loc1 = prop1.get("area", "").lower()
        loc2 = prop2.get("location", "").lower()
        if loc1 and loc2 and loc1 in loc2 or loc2 in loc1:
            score += weights["location"]
        
        # Age similarity
        age1 = prop1.get("age", 5)
        age2 = prop2.get("property_age", 5)
        age_diff = abs(age1 - age2)
        if age_diff <= 2:
            score += weights["age"] * (1 - age_diff / 10)
        
        return min(1.0, score)
    
    def _calculate_confidence(self, predictions: Dict[str, float], parameters: Dict[str, Any]) -> float:
        """
        Calculate confidence score for valuation
        """
        confidence = 0.5  # Base confidence
        
        # More models = higher confidence
        if len(predictions) > 1:
            confidence += min(0.2, len(predictions) * 0.05)
        
        # Lower variance = higher confidence
        if len(predictions) > 1:
            values = list(predictions.values())
            cv = np.std(values) / np.mean(values)  # Coefficient of variation
            if cv < 0.1:
                confidence += 0.2
            elif cv < 0.2:
                confidence += 0.1
        
        # Complete data = higher confidence
        required_fields = ["size", "bedrooms", "bathrooms", "age", "location"]
        completeness = sum(1 for field in required_fields if field in parameters) / len(required_fields)
        confidence += completeness * 0.1
        
        return min(1.0, confidence)
    
    def _calculate_market_position(self, value: float, parameters: Dict[str, Any]) -> float:
        """
        Calculate property's position in market (percentile)
        """
        # Get similar properties
        property_type = parameters.get("property_type", "apartment")
        transaction_type = parameters.get("transaction_type", "sale")
        
        all_prices = []
        for key, properties in self.property_data.items():
            if property_type in key and transaction_type in key:
                all_prices.extend([p.get("price", 0) for p in properties if p.get("price", 0) > 0])
        
        if all_prices:
            # Calculate percentile
            all_prices.sort()
            position = sum(1 for price in all_prices if price < value) / len(all_prices)
            return position * 100
        
        return 50.0  # Default to median if no data
    
    def _categorize_market_position(self, percentile: float) -> str:
        """
        Categorize market position
        """
        if percentile >= 90:
            return "premium"
        elif percentile >= 70:
            return "above_average"
        elif percentile >= 30:
            return "average"
        else:
            return "below_average"
    
    async def analyze_property(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detailed property analysis
        """
        # Get basic valuation
        valuation = await self.estimate_value(parameters)
        
        # Add detailed analysis
        analysis = {
            **valuation,
            "detailed_analysis": {
                "strengths": self._identify_strengths(parameters),
                "weaknesses": self._identify_weaknesses(parameters),
                "opportunities": self._identify_opportunities(parameters),
                "risks": self._identify_risks(parameters)
            },
            "investment_metrics": {
                "rental_yield": self._calculate_rental_yield(valuation["valuation"]["estimated_value"], parameters),
                "appreciation_potential": self._estimate_appreciation(parameters),
                "liquidity_score": self._calculate_liquidity(parameters)
            }
        }
        
        return analysis
    
    def _identify_strengths(self, parameters: Dict[str, Any]) -> List[str]:
        """Identify property strengths"""
        strengths = []
        
        if parameters.get("bedrooms", 0) >= 3:
            strengths.append("Spacious layout with multiple bedrooms")
        
        amenities = parameters.get("amenities", [])
        if len(amenities) > 5:
            strengths.append("Excellent amenities")
        
        if parameters.get("age", 10) < 3:
            strengths.append("New/recent construction")
        
        return strengths
    
    def _identify_weaknesses(self, parameters: Dict[str, Any]) -> List[str]:
        """Identify property weaknesses"""
        weaknesses = []
        
        if parameters.get("age", 0) > 10:
            weaknesses.append("Older property may need renovation")
        
        if parameters.get("floor", 0) == 0:
            weaknesses.append("Ground floor may have privacy/security concerns")
        
        return weaknesses
    
    def _identify_opportunities(self, parameters: Dict[str, Any]) -> List[str]:
        """Identify investment opportunities"""
        return [
            "Growing rental demand in area",
            "Upcoming infrastructure development",
            "Potential for value appreciation"
        ]
    
    def _identify_risks(self, parameters: Dict[str, Any]) -> List[str]:
        """Identify investment risks"""
        return [
            "Market volatility risk",
            "Maintenance cost escalation",
            "Regulatory changes"
        ]
    
    def _calculate_rental_yield(self, value: float, parameters: Dict[str, Any]) -> float:
        """Calculate expected rental yield"""
        # Estimate monthly rent (simplified)
        monthly_rent = value * 0.004  # 0.4% of value as monthly rent
        annual_rent = monthly_rent * 12
        rental_yield = (annual_rent / value) * 100
        return rental_yield
    
    def _estimate_appreciation(self, parameters: Dict[str, Any]) -> float:
        """Estimate annual appreciation potential"""
        # Simplified model
        base_appreciation = 5.0  # 5% base
        
        # Adjust for age
        age = parameters.get("age", 5)
        if age < 3:
            base_appreciation += 2
        elif age > 10:
            base_appreciation -= 1
        
        return base_appreciation
    
    def _calculate_liquidity(self, parameters: Dict[str, Any]) -> float:
        """Calculate liquidity score (0-1)"""
        score = 0.5  # Base score
        
        # Popular configurations are more liquid
        bedrooms = parameters.get("bedrooms", 2)
        if bedrooms in [2, 3]:
            score += 0.2
        
        # Mid-range properties are more liquid
        size = parameters.get("size", 1000)
        if 800 <= size <= 1500:
            score += 0.2
        
        return min(1.0, score)
    
    async def value_breakdown(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Break down property value by components
        """
        base_value = self._heuristic_valuation(parameters)
        
        breakdown = {
            "land_value": base_value * 0.4,
            "construction_value": base_value * 0.35,
            "location_premium": base_value * 0.15,
            "amenity_value": base_value * 0.08,
            "brand_value": base_value * 0.02
        }
        
        return {
            "status": "success",
            "total_value": base_value,
            "breakdown": breakdown,
            "percentage_breakdown": {
                k: (v / base_value) * 100 for k, v in breakdown.items()
            }
        }
    
    async def forecast_value(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Forecast future property value
        """
        current_value = (await self.estimate_value(parameters))["valuation"]["estimated_value"]
        appreciation_rate = self._estimate_appreciation(parameters) / 100
        
        forecasts = {}
        for years in [1, 3, 5, 10]:
            forecasts[f"{years}_year"] = current_value * ((1 + appreciation_rate) ** years)
        
        return {
            "status": "success",
            "current_value": current_value,
            "annual_appreciation": appreciation_rate * 100,
            "forecasts": forecasts
        }
