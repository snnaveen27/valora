"""
Narrative Generator
Converts structured intelligence into human-readable insights using LLM.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NarrativeGenerator:
    """
    Uses LLM to narrate structured intelligence.
    
    Rules:
    - Never invent numbers (only explain what reasoning produced)
    - Always include confidence level
    - Always cite drivers (cause → effect)
    - Support multiple POVs (investor, homebuyer, developer)
    """
    
    # Prompt templates for different narrative types
    TEMPLATES = {
        'locality_profile': """
You are a real estate analyst. Generate a concise summary based on this data:

**Locality:** {ward_name}
**Growth Phase:** {growth_phase}
**Annual Price Change:** {price_change_12m}%
**Avg Price/sqft:** ₹{avg_price_sqft}
**Risk Index:** {risk_index_overall}/1.0
**Infrastructure Score:** {infrastructure_score}/1.0
**Key Drivers:** {drivers}
**Forecast (1Y):** {price_forecast_1y} (Confidence: {forecast_confidence}%)

Generate a 3-4 sentence summary for an {audience} explaining:
1. Current market state
2. Key factors driving the trend
3. Outlook and main risk/opportunity

Be specific and data-driven. No vague statements.
""",

        'comparison': """
Compare these two localities for {purpose}:

**Locality A: {ward_a}**
- Growth Phase: {phase_a}
- Price: ₹{price_a}/sqft
- Price Change (12M): {growth_a}%
- Risk Index: {risk_a}/1.0
- Infrastructure: {infra_a}/1.0

**Locality B: {ward_b}**
- Growth Phase: {phase_b}
- Price: ₹{price_b}/sqft
- Price Change (12M): {growth_b}%
- Risk Index: {risk_b}/1.0
- Infrastructure: {infra_b}/1.0

Provide a clear recommendation with specific rationale.
""",

        'scenario_impact': """
Analyze this infrastructure event impact:

**Event:** {event_type} - {event_name}
**Location:** {location}
**Timeline:** {timeline_years} years

**Top Winners:**
{winners}

**Potential Losers:**
{losers}

Explain:
1. Why these areas will be affected
2. Best entry timing for investors
3. Risk factors to consider
""",

        'investment_brief': """
Generate an investment brief for this property/locality:

**Location:** {location}
**Property Type:** {property_type}
**Price:** ₹{price}
**Area:** {area_sqft} sqft
**Growth Phase:** {growth_phase}
**Risk Level:** {risk_level}
**Predicted Appreciation (1Y):** {appreciation_1y}%
**Rental Yield:** {rental_yield}%

Provide:
1. Investment thesis (2 sentences)
2. Key risks (2-3 points)
3. Target investor profile
4. Recommended holding period
""",

        'market_update': """
Generate a weekly market update for {city}:

**Average Price Change (Week):** {weekly_change}%
**Top Performing Areas:**
{top_areas}

**Underperforming Areas:**
{bottom_areas}

**Key Developments:**
{developments}

Summarize in 3-4 sentences suitable for a newsletter.
"""
    }
    
    def __init__(self, llm_client=None):
        """
        Initialize with optional LLM client.
        If no client provided, uses template-based generation.
        """
        self.llm = llm_client
        self._use_llm = llm_client is not None
        logger.info(f"NarrativeGenerator initialized (LLM: {self._use_llm})")
    
    async def generate_locality_narrative(
        self, 
        ward_data: Dict[str, Any], 
        audience: str = "investor"
    ) -> str:
        """Generate narrative for a locality profile."""
        
        # Prepare template variables
        variables = {
            'ward_name': ward_data.get('ward_name', 'Unknown'),
            'growth_phase': ward_data.get('growth_phase', 'unknown').replace('_', ' ').title(),
            'price_change_12m': ward_data.get('price_change_12m', 0),
            'avg_price_sqft': ward_data.get('avg_price_sqft', 0),
            'risk_index_overall': ward_data.get('risk_index_overall', 0.5),
            'infrastructure_score': ward_data.get('infrastructure_score', 0.5),
            'drivers': self._format_drivers(ward_data.get('drivers', {})),
            'price_forecast_1y': ward_data.get('price_forecast_1y', 'N/A'),
            'forecast_confidence': ward_data.get('forecast_confidence', 70),
            'audience': audience
        }
        
        if self._use_llm:
            prompt = self.TEMPLATES['locality_profile'].format(**variables)
            return await self._call_llm(prompt)
        else:
            return self._template_locality_narrative(variables)
    
    async def generate_comparison(
        self, 
        ward_a: Dict[str, Any], 
        ward_b: Dict[str, Any], 
        purpose: str = "investment"
    ) -> str:
        """Generate comparison narrative between two localities."""
        
        variables = {
            'purpose': purpose,
            'ward_a': ward_a.get('ward_name', 'Area A'),
            'phase_a': ward_a.get('growth_phase', 'unknown'),
            'price_a': ward_a.get('avg_price_sqft', 0),
            'growth_a': ward_a.get('price_change_12m', 0),
            'risk_a': ward_a.get('risk_index_overall', 0.5),
            'infra_a': ward_a.get('infrastructure_score', 0.5),
            'ward_b': ward_b.get('ward_name', 'Area B'),
            'phase_b': ward_b.get('growth_phase', 'unknown'),
            'price_b': ward_b.get('avg_price_sqft', 0),
            'growth_b': ward_b.get('price_change_12m', 0),
            'risk_b': ward_b.get('risk_index_overall', 0.5),
            'infra_b': ward_b.get('infrastructure_score', 0.5),
        }
        
        if self._use_llm:
            prompt = self.TEMPLATES['comparison'].format(**variables)
            return await self._call_llm(prompt)
        else:
            return self._template_comparison(variables)
    
    async def generate_scenario_narrative(
        self, 
        scenario_result: Dict[str, Any]
    ) -> str:
        """Generate narrative for scenario simulation."""
        
        event = scenario_result.get('event', {})
        winners = scenario_result.get('winners', [])
        losers = scenario_result.get('losers', [])
        
        variables = {
            'event_type': event.get('event_type', 'infrastructure'),
            'event_name': event.get('name', 'Unknown Event'),
            'location': f"{event.get('location', (0,0))}",
            'timeline_years': event.get('timeline_years', 0),
            'winners': self._format_winners(winners),
            'losers': self._format_losers(losers)
        }
        
        if self._use_llm:
            prompt = self.TEMPLATES['scenario_impact'].format(**variables)
            return await self._call_llm(prompt)
        else:
            return self._template_scenario(variables)
    
    async def generate_investment_brief(
        self, 
        property_data: Dict[str, Any]
    ) -> str:
        """Generate investment brief for a property."""
        
        variables = {
            'location': property_data.get('locality', 'Unknown'),
            'property_type': property_data.get('property_type', 'Residential'),
            'price': property_data.get('price', 0),
            'area_sqft': property_data.get('area_sqft', 0),
            'growth_phase': property_data.get('growth_phase', 'mature'),
            'risk_level': property_data.get('risk_level', 'moderate'),
            'appreciation_1y': property_data.get('appreciation_1y', 0),
            'rental_yield': property_data.get('rental_yield', 0)
        }
        
        if self._use_llm:
            prompt = self.TEMPLATES['investment_brief'].format(**variables)
            return await self._call_llm(prompt)
        else:
            return self._template_investment_brief(variables)
    
    # Template-based fallback methods (no LLM required)
    
    def _template_locality_narrative(self, v: Dict[str, Any]) -> str:
        """Generate locality narrative using templates (no LLM)."""
        
        phase = v['growth_phase'].lower()
        growth = v['price_change_12m']
        risk = v['risk_index_overall']
        
        # Opening statement based on growth phase
        if phase == 'emerging':
            opening = f"{v['ward_name']} is an emerging locality showing early signs of development."
        elif phase == 'accelerating':
            opening = f"{v['ward_name']} is in an accelerating growth phase with strong momentum."
        elif phase == 'mature':
            opening = f"{v['ward_name']} is a mature, established locality with stable market dynamics."
        else:
            opening = f"{v['ward_name']} shows signs of market saturation with limited growth potential."
        
        # Growth statement
        if growth > 10:
            growth_stmt = f"Prices have appreciated {growth:.1f}% over the past year, significantly outperforming the market."
        elif growth > 5:
            growth_stmt = f"The area has seen healthy {growth:.1f}% annual price growth."
        elif growth > 0:
            growth_stmt = f"Price growth has been modest at {growth:.1f}% annually."
        else:
            growth_stmt = f"Prices have declined {abs(growth):.1f}% over the past year."
        
        # Risk/outlook statement
        if risk < 0.3:
            outlook = "Low risk profile makes this suitable for conservative investors."
        elif risk < 0.5:
            outlook = "Moderate risk with balanced growth prospects."
        else:
            outlook = "Elevated risk requires careful due diligence before investment."
        
        return f"{opening} {growth_stmt} {outlook}"
    
    def _template_comparison(self, v: Dict[str, Any]) -> str:
        """Generate comparison narrative using templates."""
        
        # Determine recommendation
        score_a = (v['growth_a'] * 2) + ((1 - v['risk_a']) * 30) + (v['infra_a'] * 20)
        score_b = (v['growth_b'] * 2) + ((1 - v['risk_b']) * 30) + (v['infra_b'] * 20)
        
        if score_a > score_b * 1.1:
            recommendation = v['ward_a']
            reason = "better growth-risk balance"
        elif score_b > score_a * 1.1:
            recommendation = v['ward_b']
            reason = "better growth-risk balance"
        else:
            recommendation = "both are comparable"
            reason = "similar risk-adjusted returns"
        
        narrative = f"**Comparison: {v['ward_a']} vs {v['ward_b']}**\n\n"
        
        # Price comparison
        if v['price_a'] > v['price_b']:
            narrative += f"{v['ward_a']} is {((v['price_a']/v['price_b'])-1)*100:.0f}% more expensive. "
        else:
            narrative += f"{v['ward_b']} is {((v['price_b']/v['price_a'])-1)*100:.0f}% more expensive. "
        
        # Growth comparison
        narrative += f"{v['ward_a']} grew {v['growth_a']:.1f}% vs {v['ward_b']}'s {v['growth_b']:.1f}%. "
        
        # Recommendation
        if recommendation == "both are comparable":
            narrative += f"\n\n**Recommendation:** Both areas offer {reason}. Choose based on specific requirements."
        else:
            narrative += f"\n\n**Recommendation:** {recommendation} offers {reason}."
        
        return narrative
    
    def _template_scenario(self, v: Dict[str, Any]) -> str:
        """Generate scenario narrative using templates."""
        
        narrative = f"**Impact Analysis: {v['event_name']}**\n\n"
        narrative += f"This {v['event_type']} project, expected in {v['timeline_years']:.0f} years, "
        narrative += "will significantly impact nearby property values.\n\n"
        
        if v['winners']:
            narrative += f"**Top Beneficiaries:**\n{v['winners']}\n\n"
        
        if v['losers']:
            narrative += f"**Areas to Watch:**\n{v['losers']}\n\n"
        
        narrative += "**Investment Timing:** Consider entry 1-2 years before completion for optimal gains."
        
        return narrative
    
    def _template_investment_brief(self, v: Dict[str, Any]) -> str:
        """Generate investment brief using templates."""
        
        narrative = f"**Investment Brief: {v['property_type']} in {v['location']}**\n\n"
        
        # Investment thesis
        phase = v['growth_phase']
        if phase == 'accelerating':
            thesis = "Strong capital appreciation play in a rapidly developing area."
        elif phase == 'emerging':
            thesis = "Early-stage opportunity with high growth potential but elevated risk."
        elif phase == 'mature':
            thesis = "Stable investment suitable for rental yield focus."
        else:
            thesis = "Value play for specific requirements only."
        
        narrative += f"**Thesis:** {thesis}\n\n"
        
        # Key metrics
        narrative += f"**Price:** ₹{v['price']:,.0f} (₹{v['price']/v['area_sqft']:,.0f}/sqft)\n"
        narrative += f"**Expected 1Y Appreciation:** {v['appreciation_1y']:.1f}%\n"
        narrative += f"**Rental Yield:** {v['rental_yield']:.1f}%\n\n"
        
        # Risk level
        narrative += f"**Risk Level:** {v['risk_level'].title()}\n\n"
        
        # Holding period
        if phase in ['emerging', 'accelerating']:
            holding = "3-5 years for capital appreciation"
        else:
            holding = "5-7 years for stable returns"
        narrative += f"**Recommended Hold:** {holding}"
        
        return narrative
    
    # Helper methods
    
    def _format_drivers(self, drivers: Dict[str, Any]) -> str:
        """Format drivers dict into readable string."""
        if not drivers:
            return "Market dynamics"
        
        parts = []
        if 'primary' in drivers:
            parts.append(drivers['primary'].get('interpretation', ''))
        if 'supporting_signals' in drivers:
            parts.extend(drivers['supporting_signals'][:2])
        
        return "; ".join(parts) if parts else "Market dynamics"
    
    def _format_winners(self, winners: List[Dict[str, Any]]) -> str:
        """Format winners list for prompt."""
        if not winners:
            return "No significant winners identified"
        
        lines = []
        for w in winners[:5]:
            lines.append(f"- {w.get('ward_name', 'Unknown')}: +{w.get('impact_pct', 0):.1f}%")
        return "\n".join(lines)
    
    def _format_losers(self, losers: List[Dict[str, Any]]) -> str:
        """Format losers list for prompt."""
        if not losers:
            return "No significant negative impact expected"
        
        lines = []
        for l in losers[:3]:
            lines.append(f"- {l.get('ward_name', 'Unknown')}: {l.get('impact_pct', 0):.1f}%")
        return "\n".join(lines)
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM API for narrative generation."""
        try:
            if hasattr(self.llm, 'generate'):
                return await self.llm.generate(prompt)
            elif hasattr(self.llm, 'chat'):
                return await self.llm.chat(prompt)
            else:
                logger.warning("LLM client has no generate or chat method")
                return "Narrative generation unavailable."
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"Narrative generation failed: {str(e)}"
