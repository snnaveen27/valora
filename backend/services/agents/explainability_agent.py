"""
Explainability Agents - SHAP, PDP, and Counterfactual explanations
Part of VALORA-DMPE+ Enhanced Architecture
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

# ML explanation imports
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

logger = logging.getLogger(__name__)


class SHAPAgent:
    """
    SHAP-based explainability agent for model interpretability
    """
    
    def __init__(self):
        self.explainer = None
        self.feature_names = [
            "size", "bedrooms", "bathrooms", "age", "floor", "total_floors",
            "latitude", "longitude", "parking", "gym", "pool", "security",
            "is_apartment", "is_house", "is_villa", "furnished", "semi_furnished"
        ]
        logger.info("SHAPAgent initialized")
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SHAP explanation"""
        
        if action == "explain":
            return await self.explain_prediction(parameters)
        elif action == "feature_importance":
            return await self.get_feature_importance(parameters)
        elif action == "interaction_effects":
            return await self.analyze_interactions(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def explain_prediction(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Explain a single prediction using SHAP values
        """
        try:
            prediction = parameters.get("prediction", 10000000)
            features = parameters.get("features", [])
            model_type = parameters.get("model_type", "xgboost")
            
            # Generate synthetic SHAP values (in production, use actual model)
            shap_values = self._generate_synthetic_shap_values(features)
            
            # Get base value (average prediction)
            base_value = 8000000  # Average property price
            
            # Calculate feature contributions
            feature_contributions = []
            for i, (name, value, shap_val) in enumerate(zip(self.feature_names[:len(shap_values)], 
                                                            features[:len(shap_values)], 
                                                            shap_values)):
                contribution = {
                    "feature": name,
                    "value": value,
                    "shap_value": float(shap_val),
                    "contribution": float(shap_val * 1000000),  # Convert to currency
                    "direction": "positive" if shap_val > 0 else "negative"
                }
                feature_contributions.append(contribution)
            
            # Sort by absolute impact
            feature_contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
            
            # Generate waterfall data
            waterfall = self._generate_waterfall_data(base_value, feature_contributions)
            
            # Generate narrative explanation
            narrative = self._generate_narrative(feature_contributions, prediction, base_value)
            
            return {
                "status": "success",
                "explanation": {
                    "prediction": float(prediction),
                    "base_value": float(base_value),
                    "difference": float(prediction - base_value)
                },
                "feature_contributions": feature_contributions[:10],  # Top 10 features
                "waterfall_data": waterfall,
                "narrative": narrative,
                "confidence": 0.85,
                "model_type": model_type
            }
            
        except Exception as e:
            logger.error(f"SHAP explanation failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _generate_synthetic_shap_values(self, features: List) -> np.ndarray:
        """Generate synthetic SHAP values for demo"""
        # In production, use actual SHAP explainer
        num_features = min(len(features), len(self.feature_names))
        
        # Generate values with some structure
        shap_values = np.random.normal(0, 0.5, num_features)
        
        # Make size and location most important
        if num_features > 0:
            shap_values[0] *= 2  # Size
        if num_features > 6:
            shap_values[6] *= 1.5  # Latitude
            shap_values[7] *= 1.5  # Longitude
        
        return shap_values
    
    def _generate_waterfall_data(self, base: float, contributions: List[Dict]) -> Dict[str, Any]:
        """Generate data for waterfall chart"""
        waterfall = {
            "start": base,
            "steps": [],
            "end": base
        }
        
        cumulative = base
        for contrib in contributions[:5]:  # Top 5 for waterfall
            step_value = contrib["contribution"]
            cumulative += step_value
            
            waterfall["steps"].append({
                "name": contrib["feature"],
                "value": step_value,
                "cumulative": cumulative
            })
        
        waterfall["end"] = cumulative
        
        return waterfall
    
    def _generate_narrative(self, contributions: List[Dict], prediction: float, base: float) -> str:
        """Generate human-readable explanation"""
        narrative = f"The predicted value of ₹{prediction:,.0f} differs from the average of ₹{base:,.0f} by ₹{prediction-base:,.0f}. "
        
        # Top positive factors
        positive = [c for c in contributions if c["direction"] == "positive"][:2]
        if positive:
            narrative += f"Key factors increasing value: "
            for factor in positive:
                narrative += f"{factor['feature']} (+₹{factor['contribution']:,.0f}), "
            narrative = narrative[:-2] + ". "
        
        # Top negative factors
        negative = [c for c in contributions if c["direction"] == "negative"][:2]
        if negative:
            narrative += f"Factors decreasing value: "
            for factor in negative:
                narrative += f"{factor['feature']} (-₹{abs(factor['contribution']):,.0f}), "
            narrative = narrative[:-2] + "."
        
        return narrative
    
    async def get_feature_importance(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get global feature importance
        """
        # Generate synthetic global importance
        importance_scores = {}
        for i, name in enumerate(self.feature_names):
            # Decay importance
            importance_scores[name] = max(0, 1.0 - i * 0.05) * np.random.uniform(0.5, 1.0)
        
        # Normalize
        total = sum(importance_scores.values())
        importance_scores = {k: v/total for k, v in importance_scores.items()}
        
        # Sort by importance
        sorted_importance = sorted(importance_scores.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "status": "success",
            "feature_importance": [
                {"feature": name, "importance": score}
                for name, score in sorted_importance
            ],
            "top_features": sorted_importance[:5],
            "interpretation": self._interpret_importance(sorted_importance[:3])
        }
    
    def _interpret_importance(self, top_features: List[Tuple[str, float]]) -> str:
        """Interpret feature importance"""
        interpretation = "The most important factors for property valuation are: "
        
        for name, score in top_features:
            interpretation += f"{name} ({score*100:.1f}%), "
        
        interpretation = interpretation[:-2] + ". "
        interpretation += "These features have the strongest influence on property prices in the model."
        
        return interpretation
    
    async def analyze_interactions(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze feature interactions
        """
        features = parameters.get("features", self.feature_names[:5])
        
        # Generate synthetic interaction matrix
        n = len(features)
        interaction_matrix = np.random.uniform(-0.3, 0.3, (n, n))
        np.fill_diagonal(interaction_matrix, 0)
        
        # Make it symmetric
        interaction_matrix = (interaction_matrix + interaction_matrix.T) / 2
        
        # Find strongest interactions
        interactions = []
        for i in range(n):
            for j in range(i+1, n):
                interactions.append({
                    "feature1": features[i],
                    "feature2": features[j],
                    "strength": float(abs(interaction_matrix[i, j])),
                    "type": "positive" if interaction_matrix[i, j] > 0 else "negative"
                })
        
        # Sort by strength
        interactions.sort(key=lambda x: x["strength"], reverse=True)
        
        return {
            "status": "success",
            "interactions": interactions[:10],
            "strongest_interaction": interactions[0] if interactions else None,
            "interpretation": "Size and location show the strongest interaction effect on price"
        }


class PDPAgent:
    """
    Partial Dependence Plot agent for feature effect analysis
    """
    
    def __init__(self):
        logger.info("PDPAgent initialized")
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute PDP analysis"""
        
        if action == "calculate_pdp":
            return await self.calculate_pdp(parameters)
        elif action == "calculate_ice":
            return await self.calculate_ice(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def calculate_pdp(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate partial dependence plot data
        """
        try:
            feature = parameters.get("feature", "size")
            feature_range = parameters.get("range", [500, 3000])
            num_points = parameters.get("num_points", 20)
            
            # Generate grid
            grid = np.linspace(feature_range[0], feature_range[1], num_points)
            
            # Generate synthetic PDP (in production, use actual model)
            if feature == "size":
                # Size has positive relationship with price
                pdp_values = 3000 * grid + np.random.normal(0, 50000, num_points)
            elif feature == "age":
                # Age has negative relationship
                pdp_values = 10000000 - 50000 * grid + np.random.normal(0, 50000, num_points)
            elif feature == "bedrooms":
                # Bedrooms have diminishing returns
                pdp_values = 5000000 + 2000000 * np.log(grid + 1) + np.random.normal(0, 50000, num_points)
            else:
                # Default linear relationship
                pdp_values = 8000000 + 1000 * grid + np.random.normal(0, 50000, num_points)
            
            # Calculate confidence intervals
            std = np.std(pdp_values) * 0.1
            lower_bound = pdp_values - 1.96 * std
            upper_bound = pdp_values + 1.96 * std
            
            # Identify key points
            min_idx = np.argmin(pdp_values)
            max_idx = np.argmax(pdp_values)
            
            return {
                "status": "success",
                "feature": feature,
                "pdp_data": {
                    "grid": grid.tolist(),
                    "values": pdp_values.tolist(),
                    "confidence_interval": {
                        "lower": lower_bound.tolist(),
                        "upper": upper_bound.tolist()
                    }
                },
                "key_points": {
                    "minimum": {"x": float(grid[min_idx]), "y": float(pdp_values[min_idx])},
                    "maximum": {"x": float(grid[max_idx]), "y": float(pdp_values[max_idx])},
                    "optimal_value": float(grid[max_idx])
                },
                "interpretation": self._interpret_pdp(feature, grid, pdp_values),
                "marginal_effects": self._calculate_marginal_effects(grid, pdp_values)
            }
            
        except Exception as e:
            logger.error(f"PDP calculation failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _interpret_pdp(self, feature: str, grid: np.ndarray, values: np.ndarray) -> str:
        """Interpret PDP results"""
        # Calculate trend
        correlation = np.corrcoef(grid, values)[0, 1]
        
        if abs(correlation) < 0.2:
            relationship = "no clear relationship"
        elif correlation > 0:
            relationship = "positive relationship"
        else:
            relationship = "negative relationship"
        
        # Calculate effect size
        effect_size = (np.max(values) - np.min(values)) / np.mean(values)
        
        if effect_size < 0.1:
            impact = "minimal impact"
        elif effect_size < 0.3:
            impact = "moderate impact"
        else:
            impact = "strong impact"
        
        interpretation = f"{feature} shows {relationship} with property value, having {impact} on prices. "
        
        # Add specific insights
        if feature == "size":
            interpretation += "Each additional square foot adds approximately ₹3,000 to value."
        elif feature == "age":
            interpretation += "Properties depreciate by approximately ₹50,000 per year."
        elif feature == "bedrooms":
            interpretation += "Additional bedrooms have diminishing returns on value."
        
        return interpretation
    
    def _calculate_marginal_effects(self, grid: np.ndarray, values: np.ndarray) -> List[Dict[str, float]]:
        """Calculate marginal effects"""
        marginal = np.gradient(values, grid)
        
        return [
            {"x": float(x), "marginal_effect": float(m)}
            for x, m in zip(grid[::4], marginal[::4])  # Sample every 4th point
        ]
    
    async def calculate_ice(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Individual Conditional Expectation curves
        """
        feature = parameters.get("feature", "size")
        num_samples = parameters.get("num_samples", 10)
        feature_range = parameters.get("range", [500, 3000])
        
        # Generate ICE curves (individual predictions for different instances)
        grid = np.linspace(feature_range[0], feature_range[1], 20)
        ice_curves = []
        
        for i in range(num_samples):
            # Each curve represents a different property
            base = np.random.uniform(5000000, 15000000)
            slope = np.random.uniform(2000, 4000)
            noise = np.random.normal(0, 50000, len(grid))
            
            curve = base + slope * (grid - np.mean(grid)) + noise
            ice_curves.append(curve.tolist())
        
        # Calculate average (PDP)
        pdp = np.mean(ice_curves, axis=0)
        
        return {
            "status": "success",
            "feature": feature,
            "ice_data": {
                "grid": grid.tolist(),
                "curves": ice_curves,
                "pdp": pdp.tolist()
            },
            "heterogeneity": float(np.std([np.std(curve) for curve in ice_curves])),
            "interpretation": "Individual instances show varied responses to feature changes"
        }


class CounterfactualAgent:
    """
    Counterfactual explanation agent for what-if analysis
    """
    
    def __init__(self):
        logger.info("CounterfactualAgent initialized")
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute counterfactual analysis"""
        
        if action == "generate":
            return await self.generate_counterfactuals(parameters)
        elif action == "whatif":
            return await self.whatif_analysis(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def generate_counterfactuals(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate counterfactual examples
        """
        try:
            current_features = parameters.get("features", {})
            current_prediction = parameters.get("prediction", 10000000)
            desired_change = parameters.get("desired_change", "increase")  # increase/decrease
            target_value = parameters.get("target_value", current_prediction * 1.2)
            
            # Generate counterfactuals
            counterfactuals = []
            
            # Strategy 1: Minimal change
            minimal = self._generate_minimal_change(current_features, desired_change)
            counterfactuals.append(minimal)
            
            # Strategy 2: Feasible change
            feasible = self._generate_feasible_change(current_features, desired_change)
            counterfactuals.append(feasible)
            
            # Strategy 3: Optimal change
            optimal = self._generate_optimal_change(current_features, desired_change)
            counterfactuals.append(optimal)
            
            # Generate recommendations
            recommendations = self._generate_counterfactual_recommendations(
                counterfactuals, current_prediction, target_value
            )
            
            return {
                "status": "success",
                "current_state": {
                    "features": current_features,
                    "prediction": current_prediction
                },
                "target_value": target_value,
                "counterfactuals": counterfactuals,
                "recommendations": recommendations,
                "feasibility_analysis": self._analyze_feasibility(counterfactuals)
            }
            
        except Exception as e:
            logger.error(f"Counterfactual generation failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _generate_minimal_change(self, features: Dict, direction: str) -> Dict[str, Any]:
        """Generate counterfactual with minimal changes"""
        new_features = features.copy()
        
        if direction == "increase":
            # Add one bedroom (minimal change)
            new_features["bedrooms"] = features.get("bedrooms", 2) + 1
            new_value = features.get("value", 10000000) * 1.1
        else:
            # Remove one amenity
            new_features["gym"] = 0
            new_value = features.get("value", 10000000) * 0.95
        
        return {
            "strategy": "minimal_change",
            "changes": self._calculate_changes(features, new_features),
            "new_features": new_features,
            "predicted_value": new_value,
            "num_changes": 1,
            "feasibility": "high"
        }
    
    def _generate_feasible_change(self, features: Dict, direction: str) -> Dict[str, Any]:
        """Generate feasible counterfactual"""
        new_features = features.copy()
        
        if direction == "increase":
            # Feasible improvements
            new_features["parking"] = 1
            new_features["security"] = 1
            new_features["gym"] = 1
            new_value = features.get("value", 10000000) * 1.15
        else:
            # Accept older property
            new_features["age"] = features.get("age", 5) + 5
            new_value = features.get("value", 10000000) * 0.9
        
        return {
            "strategy": "feasible_change",
            "changes": self._calculate_changes(features, new_features),
            "new_features": new_features,
            "predicted_value": new_value,
            "num_changes": 3,
            "feasibility": "moderate"
        }
    
    def _generate_optimal_change(self, features: Dict, direction: str) -> Dict[str, Any]:
        """Generate optimal counterfactual"""
        new_features = features.copy()
        
        if direction == "increase":
            # Optimal improvements (may not be feasible)
            new_features["size"] = features.get("size", 1000) * 1.2
            new_features["bedrooms"] = features.get("bedrooms", 2) + 1
            new_features["floor"] = min(features.get("floor", 2) + 3, 15)
            new_value = features.get("value", 10000000) * 1.3
        else:
            # Move to less premium location
            new_features["latitude"] = features.get("latitude", 12.97) - 0.05
            new_value = features.get("value", 10000000) * 0.85
        
        return {
            "strategy": "optimal_change",
            "changes": self._calculate_changes(features, new_features),
            "new_features": new_features,
            "predicted_value": new_value,
            "num_changes": 3,
            "feasibility": "low"
        }
    
    def _calculate_changes(self, old: Dict, new: Dict) -> List[Dict[str, Any]]:
        """Calculate changes between feature sets"""
        changes = []
        
        for key in new:
            if key in old and new[key] != old[key]:
                changes.append({
                    "feature": key,
                    "old_value": old[key],
                    "new_value": new[key],
                    "change": new[key] - old[key] if isinstance(new[key], (int, float)) else "modified"
                })
        
        return changes
    
    def _generate_counterfactual_recommendations(self, counterfactuals: List[Dict], 
                                                current: float, target: float) -> List[str]:
        """Generate recommendations based on counterfactuals"""
        recommendations = []
        
        # Find most feasible option
        feasible = [cf for cf in counterfactuals if cf["feasibility"] in ["high", "moderate"]]
        if feasible:
            best = max(feasible, key=lambda x: x["predicted_value"])
            recommendations.append(f"Most feasible option: {best['strategy']} strategy")
            recommendations.append(f"Expected value increase: ₹{best['predicted_value'] - current:,.0f}")
        
        # Specific actionable items
        for cf in counterfactuals:
            if cf["strategy"] == "minimal_change" and cf["num_changes"] == 1:
                change = cf["changes"][0]
                recommendations.append(f"Quick win: Modify {change['feature']} for immediate impact")
        
        return recommendations
    
    def _analyze_feasibility(self, counterfactuals: List[Dict]) -> Dict[str, Any]:
        """Analyze feasibility of counterfactuals"""
        return {
            "high_feasibility": len([cf for cf in counterfactuals if cf["feasibility"] == "high"]),
            "moderate_feasibility": len([cf for cf in counterfactuals if cf["feasibility"] == "moderate"]),
            "low_feasibility": len([cf for cf in counterfactuals if cf["feasibility"] == "low"]),
            "recommendation": "Focus on high-feasibility changes for best ROI"
        }
    
    async def whatif_analysis(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform what-if analysis
        """
        scenarios = parameters.get("scenarios", [])
        base_features = parameters.get("base_features", {})
        base_value = parameters.get("base_value", 10000000)
        
        results = []
        
        for scenario in scenarios:
            # Apply scenario changes
            new_features = base_features.copy()
            new_features.update(scenario.get("changes", {}))
            
            # Simple prediction (in production, use actual model)
            value_change = 0
            if "size" in scenario.get("changes", {}):
                value_change += (scenario["changes"]["size"] - base_features.get("size", 1000)) * 3000
            if "bedrooms" in scenario.get("changes", {}):
                value_change += (scenario["changes"]["bedrooms"] - base_features.get("bedrooms", 2)) * 500000
            
            new_value = base_value + value_change
            
            results.append({
                "scenario_name": scenario.get("name", "Unnamed"),
                "changes": scenario.get("changes", {}),
                "predicted_value": new_value,
                "value_change": value_change,
                "percentage_change": (value_change / base_value) * 100
            })
        
        # Sort by value
        results.sort(key=lambda x: x["predicted_value"], reverse=True)
        
        return {
            "status": "success",
            "base_value": base_value,
            "scenarios": results,
            "best_scenario": results[0] if results else None,
            "worst_scenario": results[-1] if results else None,
            "summary": f"Value ranges from ₹{results[-1]['predicted_value']:,.0f} to ₹{results[0]['predicted_value']:,.0f}"
        }
