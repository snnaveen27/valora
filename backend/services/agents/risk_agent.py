"""
Risk Assessment Agents - Market, Liquidity, and Regulatory Risk Analysis
Part of VALORA-DMPE+ Enhanced Architecture
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RiskAssessment:
    """Risk assessment result"""
    risk_score: float  # 0-1, higher is riskier
    risk_level: str  # low, moderate, high, very_high
    risk_factors: List[Dict[str, Any]]
    mitigation_strategies: List[str]
    confidence: float

class MarketRiskAgent:
    """
    Agent for assessing market-related risks
    """
    
    def __init__(self):
        self.market_data = self._load_market_data()
        logger.info("MarketRiskAgent initialized")
    
    def _load_market_data(self):
        """Load market data for risk assessment"""
        # Generate synthetic market data
        dates = pd.date_range(end=datetime.now(), periods=365, freq='D')
        
        # Market indices
        market_index = 1000 + np.cumsum(np.random.normal(0, 10, 365))
        volatility = np.abs(np.random.normal(0.15, 0.05, 365))  # Daily volatility
        
        return pd.DataFrame({
            'date': dates,
            'index': market_index,
            'volatility': volatility,
            'volume': np.random.uniform(1000, 5000, 365)
        })
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute market risk assessment"""
        
        if action == "assess":
            return await self.assess_market_risk(parameters)
        elif action == "calculate_var":
            return await self.calculate_var(parameters)
        elif action == "stress_test":
            return await self.stress_test(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def assess_market_risk(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive market risk assessment
        """
        try:
            property_value = parameters.get("property_value", 10000000)
            location = parameters.get("location", "Koramangala")
            investment_horizon = parameters.get("horizon_months", 12)
            
            # Calculate various risk metrics
            volatility_risk = self._calculate_volatility_risk()
            beta = self._calculate_beta(location)
            concentration_risk = self._calculate_concentration_risk(location)
            liquidity_risk = self._calculate_market_liquidity()
            
            # Calculate VaR
            var_95 = self._calculate_value_at_risk(property_value, 0.95)
            var_99 = self._calculate_value_at_risk(property_value, 0.99)
            
            # Overall market risk score
            risk_score = (
                volatility_risk * 0.3 +
                abs(beta - 1) * 0.2 +
                concentration_risk * 0.2 +
                liquidity_risk * 0.3
            )
            risk_score = min(1.0, risk_score)
            
            # Risk level categorization
            if risk_score < 0.3:
                risk_level = "low"
            elif risk_score < 0.5:
                risk_level = "moderate"
            elif risk_score < 0.7:
                risk_level = "high"
            else:
                risk_level = "very_high"
            
            # Risk factors
            risk_factors = []
            
            if volatility_risk > 0.5:
                risk_factors.append({
                    "factor": "High Market Volatility",
                    "impact": "high",
                    "score": volatility_risk,
                    "description": "Market showing significant price fluctuations"
                })
            
            if abs(beta - 1) > 0.3:
                risk_factors.append({
                    "factor": "Market Sensitivity",
                    "impact": "moderate",
                    "score": abs(beta - 1),
                    "description": f"Property {'more' if beta > 1 else 'less'} sensitive to market changes"
                })
            
            if concentration_risk > 0.5:
                risk_factors.append({
                    "factor": "Geographic Concentration",
                    "impact": "moderate",
                    "score": concentration_risk,
                    "description": "High exposure to single location"
                })
            
            # Mitigation strategies
            mitigation = self._generate_mitigation_strategies(risk_factors, risk_score)
            
            return {
                "status": "success",
                "risk_assessment": {
                    "overall_score": float(risk_score),
                    "risk_level": risk_level,
                    "confidence": 0.75
                },
                "metrics": {
                    "volatility": float(volatility_risk),
                    "beta": float(beta),
                    "var_95": float(var_95),
                    "var_99": float(var_99),
                    "expected_shortfall": float(var_99 * 1.2),
                    "max_drawdown": float(self._calculate_max_drawdown())
                },
                "risk_factors": risk_factors,
                "mitigation_strategies": mitigation,
                "market_outlook": self._generate_market_outlook(risk_score),
                "recommendations": self._generate_recommendations(risk_level, investment_horizon)
            }
            
        except Exception as e:
            logger.error(f"Market risk assessment failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _calculate_volatility_risk(self) -> float:
        """Calculate volatility-based risk"""
        recent_volatility = self.market_data.tail(30)['volatility'].mean()
        historical_volatility = self.market_data['volatility'].mean()
        
        if recent_volatility > historical_volatility * 1.5:
            return 0.8
        elif recent_volatility > historical_volatility * 1.2:
            return 0.6
        else:
            return 0.3
    
    def _calculate_beta(self, location: str) -> float:
        """Calculate beta (market sensitivity)"""
        # Simplified beta calculation based on location
        location_betas = {
            "Koramangala": 1.2,
            "Whitefield": 1.1,
            "Electronic City": 0.9,
            "Indiranagar": 1.3,
            "default": 1.0
        }
        return location_betas.get(location, 1.0)
    
    def _calculate_concentration_risk(self, location: str) -> float:
        """Calculate geographic concentration risk"""
        # High-demand areas have lower concentration risk
        premium_areas = ["Koramangala", "Indiranagar", "Whitefield"]
        return 0.3 if location in premium_areas else 0.6
    
    def _calculate_market_liquidity(self) -> float:
        """Calculate market liquidity risk"""
        recent_volume = self.market_data.tail(30)['volume'].mean()
        historical_volume = self.market_data['volume'].mean()
        
        if recent_volume < historical_volume * 0.7:
            return 0.7  # Low liquidity = high risk
        else:
            return 0.3
    
    def _calculate_value_at_risk(self, value: float, confidence: float) -> float:
        """Calculate Value at Risk"""
        # Simplified VaR calculation
        volatility = self.market_data['volatility'].mean()
        
        # Z-score for confidence level
        z_scores = {0.95: 1.645, 0.99: 2.326}
        z = z_scores.get(confidence, 1.645)
        
        # Daily VaR
        daily_var = value * volatility * z
        
        # Annual VaR
        annual_var = daily_var * np.sqrt(252)
        
        return annual_var
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        prices = self.market_data['index'].values
        peak = np.maximum.accumulate(prices)
        drawdown = (prices - peak) / peak
        return abs(np.min(drawdown))
    
    def _generate_mitigation_strategies(self, risk_factors: List, risk_score: float) -> List[str]:
        """Generate risk mitigation strategies"""
        strategies = []
        
        if risk_score > 0.5:
            strategies.append("Diversify across multiple locations")
            strategies.append("Consider hedging strategies")
        
        if any(f['factor'] == 'High Market Volatility' for f in risk_factors):
            strategies.append("Time entry/exit based on market cycles")
            strategies.append("Use dollar-cost averaging for investment")
        
        if any(f['factor'] == 'Geographic Concentration' for f in risk_factors):
            strategies.append("Invest in properties across different areas")
        
        strategies.append("Maintain adequate liquidity buffer")
        strategies.append("Regular portfolio rebalancing")
        
        return strategies
    
    def _generate_market_outlook(self, risk_score: float) -> str:
        """Generate market outlook based on risk"""
        if risk_score < 0.3:
            return "Stable market with low volatility. Good conditions for investment."
        elif risk_score < 0.5:
            return "Moderate market conditions. Proceed with standard risk management."
        elif risk_score < 0.7:
            return "Elevated market risk. Consider defensive strategies."
        else:
            return "High market risk. Exercise caution and consider postponing major investments."
    
    def _generate_recommendations(self, risk_level: str, horizon: int) -> List[str]:
        """Generate investment recommendations"""
        recommendations = []
        
        if risk_level == "low":
            recommendations.append("Market conditions favorable for investment")
            if horizon > 12:
                recommendations.append("Consider leveraging for higher returns")
        elif risk_level == "moderate":
            recommendations.append("Balanced approach recommended")
            recommendations.append("Focus on quality properties in prime locations")
        elif risk_level in ["high", "very_high"]:
            recommendations.append("Conservative approach advised")
            recommendations.append("Focus on capital preservation")
            recommendations.append("Consider waiting for better market conditions")
        
        return recommendations
    
    async def calculate_var(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate detailed VaR metrics"""
        value = parameters.get("property_value", 10000000)
        horizon_days = parameters.get("horizon_days", 30)
        
        var_metrics = {}
        for confidence in [0.90, 0.95, 0.99]:
            var = self._calculate_value_at_risk(value, confidence)
            var_metrics[f"var_{int(confidence*100)}"] = var
        
        return {
            "status": "success",
            "value_at_risk": var_metrics,
            "horizon_days": horizon_days,
            "interpretation": f"With 95% confidence, maximum loss won't exceed ₹{var_metrics['var_95']:,.0f}"
        }
    
    async def stress_test(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform stress testing"""
        value = parameters.get("property_value", 10000000)
        
        scenarios = {
            "market_crash": value * 0.7,  # 30% drop
            "recession": value * 0.8,  # 20% drop
            "correction": value * 0.9,  # 10% drop
            "stagnation": value * 1.0,  # No change
            "moderate_growth": value * 1.1,  # 10% growth
            "boom": value * 1.3  # 30% growth
        }
        
        return {
            "status": "success",
            "stress_scenarios": scenarios,
            "worst_case": min(scenarios.values()),
            "best_case": max(scenarios.values())
        }


class LiquidityRiskAgent:
    """
    Agent for assessing liquidity risks
    """
    
    def __init__(self):
        self.transaction_data = self._load_transaction_data()
        logger.info("LiquidityRiskAgent initialized")
    
    def _load_transaction_data(self):
        """Load transaction data"""
        # Synthetic transaction data
        return {
            "avg_days_on_market": {
                "apartment": 45,
                "house": 60,
                "plot": 90,
                "commercial": 120
            },
            "transaction_velocity": {
                "Koramangala": 0.8,
                "Whitefield": 0.7,
                "Electronic City": 0.6,
                "Indiranagar": 0.85
            }
        }
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute liquidity risk assessment"""
        
        if action == "assess":
            return await self.assess_liquidity_risk(parameters)
        elif action == "estimate_exit_time":
            return await self.estimate_exit_time(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def assess_liquidity_risk(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess liquidity risk for property
        """
        try:
            property_type = parameters.get("property_type", "apartment")
            location = parameters.get("location", "Koramangala")
            price = parameters.get("price", 10000000)
            
            # Days on market
            dom = self.transaction_data["avg_days_on_market"].get(property_type, 60)
            
            # Transaction velocity
            velocity = self.transaction_data["transaction_velocity"].get(location, 0.5)
            
            # Price factor (higher priced properties are less liquid)
            price_factor = 1.0
            if price > 50000000:  # 5 Cr+
                price_factor = 1.5
            elif price > 20000000:  # 2 Cr+
                price_factor = 1.3
            elif price > 10000000:  # 1 Cr+
                price_factor = 1.1
            
            # Adjusted days on market
            adjusted_dom = dom * price_factor / velocity
            
            # Liquidity score (0-1, lower is better)
            if adjusted_dom < 30:
                liquidity_score = 0.2
                risk_level = "low"
            elif adjusted_dom < 60:
                liquidity_score = 0.4
                risk_level = "moderate"
            elif adjusted_dom < 90:
                liquidity_score = 0.6
                risk_level = "high"
            else:
                liquidity_score = 0.8
                risk_level = "very_high"
            
            # Liquidity discount
            liquidity_discount = self._calculate_liquidity_discount(adjusted_dom)
            
            # Risk factors
            risk_factors = []
            
            if adjusted_dom > 60:
                risk_factors.append({
                    "factor": "Extended Marketing Period",
                    "impact": "high",
                    "description": f"Expected {adjusted_dom:.0f} days to sell"
                })
            
            if velocity < 0.6:
                risk_factors.append({
                    "factor": "Low Market Activity",
                    "impact": "moderate",
                    "description": "Below average transaction velocity in area"
                })
            
            if price > 20000000:
                risk_factors.append({
                    "factor": "High Value Property",
                    "impact": "moderate",
                    "description": "Limited buyer pool for high-value properties"
                })
            
            # Mitigation strategies
            mitigation = [
                "Price competitively to attract buyers",
                "Enhance property presentation and marketing",
                "Consider offering flexible payment terms",
                "Target specific buyer segments",
                "Work with experienced real estate agents"
            ]
            
            return {
                "status": "success",
                "liquidity_assessment": {
                    "score": float(liquidity_score),
                    "risk_level": risk_level,
                    "expected_days_on_market": float(adjusted_dom),
                    "transaction_velocity": float(velocity),
                    "liquidity_discount": float(liquidity_discount)
                },
                "market_depth": {
                    "active_buyers": "moderate" if velocity > 0.6 else "low",
                    "price_sensitivity": "high" if price > 20000000 else "moderate",
                    "seasonal_factors": self._get_seasonal_factors()
                },
                "risk_factors": risk_factors,
                "mitigation_strategies": mitigation[:3],  # Top 3 strategies
                "recommendations": self._generate_liquidity_recommendations(liquidity_score)
            }
            
        except Exception as e:
            logger.error(f"Liquidity risk assessment failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _calculate_liquidity_discount(self, days_on_market: float) -> float:
        """Calculate discount needed for quick sale"""
        if days_on_market < 30:
            return 0.0
        elif days_on_market < 60:
            return 0.02  # 2% discount
        elif days_on_market < 90:
            return 0.05  # 5% discount
        else:
            return 0.10  # 10% discount
    
    def _get_seasonal_factors(self) -> Dict[str, str]:
        """Get seasonal market factors"""
        month = datetime.now().month
        
        if month in [1, 2, 3]:  # Q1
            return {
                "season": "Q1",
                "activity": "moderate",
                "trend": "Beginning of fiscal year - moderate activity"
            }
        elif month in [4, 5, 6]:  # Q2
            return {
                "season": "Q2",
                "activity": "low",
                "trend": "Summer season - lower activity"
            }
        elif month in [7, 8, 9]:  # Q3
            return {
                "season": "Q3",
                "activity": "high",
                "trend": "Festival season approaching - higher activity"
            }
        else:  # Q4
            return {
                "season": "Q4",
                "activity": "very_high",
                "trend": "Festival and year-end - peak activity"
            }
    
    def _generate_liquidity_recommendations(self, score: float) -> List[str]:
        """Generate liquidity recommendations"""
        recommendations = []
        
        if score < 0.4:
            recommendations.append("Good liquidity - standard marketing approach sufficient")
            recommendations.append("Can afford to wait for optimal price")
        elif score < 0.6:
            recommendations.append("Moderate liquidity - active marketing recommended")
            recommendations.append("Consider staged price reductions if needed")
        else:
            recommendations.append("Low liquidity - aggressive marketing required")
            recommendations.append("Consider immediate price adjustment")
            recommendations.append("Explore alternative sale methods (auction, bulk sale)")
        
        return recommendations
    
    async def estimate_exit_time(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate time to exit investment"""
        property_type = parameters.get("property_type", "apartment")
        location = parameters.get("location", "Koramangala")
        urgency = parameters.get("urgency", "normal")  # urgent, normal, flexible
        
        base_dom = self.transaction_data["avg_days_on_market"].get(property_type, 60)
        velocity = self.transaction_data["transaction_velocity"].get(location, 0.5)
        
        # Adjust for urgency
        urgency_factors = {
            "urgent": 0.5,  # Half the time but need discount
            "normal": 1.0,
            "flexible": 1.5  # Can wait for better price
        }
        
        urgency_factor = urgency_factors.get(urgency, 1.0)
        estimated_days = base_dom * urgency_factor / velocity
        
        # Calculate required discount for urgent sale
        discount = 0.0
        if urgency == "urgent":
            discount = 0.05 + (1 - velocity) * 0.05  # 5-10% discount
        
        return {
            "status": "success",
            "estimated_days": float(estimated_days),
            "confidence_interval": {
                "optimistic": float(estimated_days * 0.7),
                "pessimistic": float(estimated_days * 1.5)
            },
            "required_discount": float(discount),
            "strategy": self._get_exit_strategy(urgency, estimated_days)
        }
    
    def _get_exit_strategy(self, urgency: str, days: float) -> str:
        """Get recommended exit strategy"""
        if urgency == "urgent":
            return "Price below market for quick sale. Consider auction or bulk buyers."
        elif days < 45:
            return "Market conditions favorable. List at market price with room for negotiation."
        else:
            return "Extended sale period expected. Start high and implement staged reductions."


class RegulatoryRiskAgent:
    """
    Agent for assessing regulatory and compliance risks
    """
    
    def __init__(self):
        self.regulations = self._load_regulations()
        logger.info("RegulatoryRiskAgent initialized")
    
    def _load_regulations(self):
        """Load regulatory information"""
        return {
            "zoning": {
                "residential": ["single_family", "multi_family", "mixed_use"],
                "commercial": ["retail", "office", "industrial"],
                "agricultural": ["farming", "limited_residential"]
            },
            "compliance_checklist": [
                "Title deed verification",
                "Encumbrance certificate",
                "Property tax receipts",
                "Approved building plan",
                "Completion certificate",
                "Khata certificate",
                "NOC from society"
            ],
            "recent_changes": [
                {
                    "regulation": "RERA compliance",
                    "impact": "high",
                    "date": "2024-01-01"
                },
                {
                    "regulation": "Green building norms",
                    "impact": "moderate",
                    "date": "2024-06-01"
                }
            ]
        }
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute regulatory risk assessment"""
        
        if action == "assess":
            return await self.assess_regulatory_risk(parameters)
        elif action == "compliance_check":
            return await self.check_compliance(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def assess_regulatory_risk(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess regulatory and compliance risks
        """
        try:
            property_type = parameters.get("property_type", "residential")
            documents = parameters.get("documents", [])
            zone = parameters.get("zone", "residential")
            
            # Check zoning compliance
            zoning_risk = self._assess_zoning_risk(property_type, zone)
            
            # Check document completeness
            doc_risk = self._assess_documentation_risk(documents)
            
            # Check for recent regulatory changes
            regulatory_change_risk = self._assess_regulatory_changes()
            
            # Overall risk score
            risk_score = (
                zoning_risk * 0.3 +
                doc_risk * 0.5 +
                regulatory_change_risk * 0.2
            )
            
            # Risk level
            if risk_score < 0.3:
                risk_level = "low"
            elif risk_score < 0.5:
                risk_level = "moderate"
            elif risk_score < 0.7:
                risk_level = "high"
            else:
                risk_level = "very_high"
            
            # Risk factors
            risk_factors = []
            
            if zoning_risk > 0.5:
                risk_factors.append({
                    "factor": "Zoning Compliance",
                    "impact": "high",
                    "description": "Property may not comply with zoning regulations"
                })
            
            if doc_risk > 0.5:
                risk_factors.append({
                    "factor": "Documentation",
                    "impact": "high",
                    "description": "Missing critical documents"
                })
            
            if regulatory_change_risk > 0.3:
                risk_factors.append({
                    "factor": "Regulatory Changes",
                    "impact": "moderate",
                    "description": "Recent regulatory changes may affect property"
                })
            
            # Compliance checklist
            checklist = self._generate_compliance_checklist(documents)
            
            # Mitigation strategies
            mitigation = [
                "Conduct thorough legal due diligence",
                "Obtain all missing documents before transaction",
                "Consult with real estate lawyer",
                "Get title insurance",
                "Verify with local municipal authorities"
            ]
            
            return {
                "status": "success",
                "regulatory_assessment": {
                    "risk_score": float(risk_score),
                    "risk_level": risk_level,
                    "confidence": 0.8
                },
                "compliance": {
                    "zoning_status": "compliant" if zoning_risk < 0.3 else "review_needed",
                    "documentation_status": f"{len(documents)}/{len(self.regulations['compliance_checklist'])} documents available",
                    "recent_regulations": len(self.regulations["recent_changes"])
                },
                "risk_factors": risk_factors,
                "compliance_checklist": checklist,
                "mitigation_strategies": mitigation[:3],
                "legal_recommendations": self._generate_legal_recommendations(risk_score),
                "estimated_compliance_cost": self._estimate_compliance_cost(risk_factors)
            }
            
        except Exception as e:
            logger.error(f"Regulatory risk assessment failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _assess_zoning_risk(self, property_type: str, zone: str) -> float:
        """Assess zoning compliance risk"""
        allowed_uses = self.regulations["zoning"].get(zone, [])
        
        # Simplified check
        if property_type in zone:
            return 0.1  # Low risk
        elif zone == "mixed_use":
            return 0.3  # Moderate risk
        else:
            return 0.7  # High risk
    
    def _assess_documentation_risk(self, documents: List[str]) -> float:
        """Assess documentation completeness risk"""
        required = len(self.regulations["compliance_checklist"])
        available = len(documents)
        
        completeness = available / required if required > 0 else 0
        
        return 1 - completeness  # Higher missing docs = higher risk
    
    def _assess_regulatory_changes(self) -> float:
        """Assess impact of recent regulatory changes"""
        recent_changes = [
            r for r in self.regulations["recent_changes"]
            if datetime.fromisoformat(r["date"]) > datetime.now() - timedelta(days=365)
        ]
        
        if not recent_changes:
            return 0.1
        
        high_impact = sum(1 for r in recent_changes if r["impact"] == "high")
        
        if high_impact > 0:
            return 0.6
        else:
            return 0.3
    
    def _generate_compliance_checklist(self, available_docs: List[str]) -> List[Dict[str, Any]]:
        """Generate compliance checklist"""
        checklist = []
        
        for doc in self.regulations["compliance_checklist"]:
            checklist.append({
                "document": doc,
                "status": "available" if doc in available_docs else "missing",
                "priority": "high" if doc in ["Title deed verification", "Encumbrance certificate"] else "medium"
            })
        
        return checklist
    
    def _generate_legal_recommendations(self, risk_score: float) -> List[str]:
        """Generate legal recommendations"""
        recommendations = []
        
        if risk_score < 0.3:
            recommendations.append("Standard legal verification sufficient")
        elif risk_score < 0.6:
            recommendations.append("Enhanced due diligence recommended")
            recommendations.append("Consider title insurance")
        else:
            recommendations.append("Comprehensive legal audit required")
            recommendations.append("Engage specialized real estate lawyer")
            recommendations.append("Consider postponing transaction until issues resolved")
        
        return recommendations
    
    def _estimate_compliance_cost(self, risk_factors: List[Dict]) -> float:
        """Estimate cost of achieving compliance"""
        base_cost = 50000  # Base legal fees
        
        for factor in risk_factors:
            if factor["impact"] == "high":
                base_cost += 100000
            elif factor["impact"] == "moderate":
                base_cost += 50000
        
        return base_cost
    
    async def check_compliance(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Quick compliance check"""
        documents = parameters.get("documents", [])
        
        missing = [
            doc for doc in self.regulations["compliance_checklist"]
            if doc not in documents
        ]
        
        compliance_score = 1 - (len(missing) / len(self.regulations["compliance_checklist"]))
        
        return {
            "status": "success",
            "compliance_score": float(compliance_score),
            "missing_documents": missing,
            "is_compliant": compliance_score > 0.8,
            "next_steps": [
                f"Obtain {doc}" for doc in missing[:3]
            ]
        }
