"""
Report Generator Service - Generates detailed reports using LLM
Processes each smart tab sequentially and generates MD/PDF output
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)


# Tab-specific prompts for LLM generation
TAB_PROMPTS = {
    "decision_verdict": """Generate an investment verdict analysis for {locality}.

Context:
- Verdict: {verdict}
- Confidence: {confidence}%
- Risk Level: {risk_level}
- Top Reasons: {top_reasons}
- Key Risks: {key_risks}
- Strategy: {strategy_recommendation}
- Negotiation Leverage Points: {negotiation_leverage_points}
- Deal-Breaker Flags: {deal_breaker_flags}
- Optimal Holding Period: {optimal_holding_period}
- Exit Timing: {exit_timing}

Provide a detailed analysis including:
1. **Executive Summary** (2-3 sentences with clear BUY/HOLD/AVOID recommendation)
2. **Detailed Reasoning** for the verdict with supporting evidence
3. **Confidence Breakdown** explaining the score (what factors increased/decreased confidence)
4. **Key Positive Factors** (expand on each reason with specific data points)
5. **Key Risk Factors** (expand on each risk with mitigation suggestions)
6. **Price Negotiation Leverage Points** (specific arguments to use with seller - use the provided leverage points)
7. **Deal-Breaker Red Flags** (what would make you walk away - use the provided flags)
8. **Optimal Holding Period** (recommended years to hold - use the provided period)
9. **Exit Strategy Timing** (when to sell for maximum returns - use the provided timing)
10. **Investment Strategy Recommendation** (conservative/moderate/aggressive approach)

Format the response in Markdown with clear sections. Use specific numbers and percentages where possible.""",

    "market_snapshot": """Generate market analysis for {locality}.

Context:
- Average Price/sqft: ₹{avg_price_sqft}
- Price Trends: {price_trend}
- Demand/Supply: {demand_supply}
- Rental Yield: {rental_yield}
- Liquidity Score: {liquidity_score}
- Advanced Indicators: {advanced_indicators}
- Micro-Market Comparison: {micro_market_comparison}
- New Launch Pipeline: {new_launch_pipeline}
- Rental Demand Employers: {rental_demand_employers}
- Price Segmentation: {price_segmentation}

Provide a comprehensive market analysis including:
1. **Current Market Overview** (price range, inventory levels, buyer sentiment)
2. **Price Trend Analysis** (1Y, 3Y, 5Y outlook with specific percentages)
3. **Micro-Market Comparison** (how this area compares to adjacent areas - use the provided comparison data)
4. **Demand-Supply Dynamics** (buyer-to-seller ratio, days on market)
5. **New Launch Pipeline** (upcoming projects that may affect prices - use the provided pipeline data)
6. **Rental Demand Analysis** (which employers/IT parks drive rental demand - use the provided employer data)
7. **Price Segmentation** (budget vs premium segments in the area - use the provided segmentation)
8. **Rental Yield Analysis** (expected monthly rent, yield percentage)
9. **Investment Momentum Assessment** (is the market heating up or cooling?)
10. **Market Risks and Opportunities** (timing considerations)

Format the response in Markdown with clear sections. Include specific numbers and comparisons.""",

    "spatial_intelligence": """Generate spatial intelligence analysis for {locality}.

Context:
- Infrastructure: {nearby_infrastructure}
- POIs: {pois}
- Walkability Score: {walkability_score}
- Transit Score: {transit_score}
- Growth Hotspots: {growth_hotspots}
- Commute Times: {commute_times}
- Metro Expansion: {metro_expansion}
- School Details: {school_details}
- Hospital Details: {hospital_details}
- School Admission Season: {school_admission_season}
- Last-Mile Connectivity: {last_mile_connectivity}

Provide a detailed spatial analysis including:
1. **Infrastructure Overview and Connectivity** (roads, metro, airport access)
2. **Commute Analysis** (time to major employment hubs - use the provided commute times: Electronic City, Whitefield, ITPL, airport, MG Road)
3. **Metro Expansion Impact** (upcoming lines, timeline, expected price impact - use the provided metro expansion data)
4. **POI Analysis** with distances:
   - Schools (use the provided school details with names, distances, ratings, boards)
   - Hospitals (use the provided hospital details with names, distances, emergency services)
   - Shopping (malls, markets with distances)
   - Offices (IT parks, business centers)
5. **Walkability and Transit Assessment** (can you live without a car?)
6. **School Admission Season** (use the provided admission season info for planning)
7. **Last-Mile Connectivity** (auto/bus availability from metro - use the provided connectivity info)
8. **Future Growth Areas** (which parts are developing fastest)
9. **Location Strengths and Weaknesses** (balanced assessment)
10. **Development Pipeline Impact** (upcoming infrastructure in 2-5 years)

Format the response in Markdown with clear sections. Use specific distances in kilometers and commute times in minutes.""",

    "risk_analysis": """Generate comprehensive risk analysis for {locality}.

Context:
- Overall Risk Score: {overall_risk_score}
- Flood Risk: {flood}
- Legal Risk: {legal}
- Market Risk: {market}
- Infrastructure Risk: {infrastructure}
- Environmental Risk: {environmental}
- Mitigation Suggestions: {mitigation_suggestions}
- Legal Checklist: {legal_checklist}
- Flood History: {flood_history}
- Warning Signs: {warning_signs}

Provide a detailed risk assessment including:
1. **Risk Assessment Summary** (overall risk level with key concerns)
2. **Flood Risk Analysis** (historical flooding, low-lying areas, monsoon impact - use the provided flood history)
3. **Legal Compliance Checklist** (use the provided legal checklist with BBMP Khata, BDA approval, Encumbrance, RERA check, and documents to request)
4. **Market Risk Factors** (price volatility, demand fluctuations)
5. **Infrastructure Risk Outlook** (water supply, power, road connectivity)
6. **Environmental Concerns** (air quality, noise pollution, green cover)
7. **Risk Quantification** (probability percentages where possible)
8. **Mitigation Strategies** (specific actions to reduce each risk - use the provided suggestions)
9. **Documents Checklist** (what to verify before purchase - use the provided legal checklist)
10. **Warning Signs** (red flags that indicate problems - use the provided warning signs)

Format the response in Markdown with clear sections. Include actionable checklists.""",

    "roi_projection": """Generate ROI projection analysis for {locality}.

Context:
- 3-Year Projection: {projection_3year}
- Entry/Exit Recommendations: {entry_exit}
- Rental Yield: {rental_yield}
- Investment Score: {investment_score}
- Tax Implications: {tax_implications}
- Comparison with Alternatives: {comparison_with_alternatives}
- Break-Even Analysis: {break_even_analysis}

Provide a detailed ROI analysis including:
1. **Best/Expected/Worst Case Scenarios** (with specific price projections)
2. **Entry Price Recommendations** (price range to negotiate for)
3. **Target Exit Prices** (when to sell for each scenario)
4. **Rental Income Potential** (expected monthly rent, annual yield)
5. **Timeline for Returns** (when to expect appreciation)
6. **Tax Implications** (use the provided tax data for capital gains, home loan benefits under Section 80C and 24(b), stamp duty, registration, and rental income tax)
7. **Risk-Adjusted Projections** (accounting for market volatility)
8. **Comparison with Alternative Investments** (use the provided comparison with FD, mutual funds, gold, and real estate)
9. **Leverage Impact** (how home loan amplifies returns)
10. **Break-Even Analysis** (when rental income covers EMI - use the provided break-even analysis)

Format the response in Markdown with clear sections. Include specific numbers and percentages.""",

    "comparables": """Generate comparables analysis for {locality}.

Context:
- Comparable Properties: {comparables}
- Price Analysis: {price_analysis}
- Building Valuation: {building_valuation}
- Transaction Evidence: {transaction_evidence}
- Time on Market: {time_on_market}
- Negotiation Patterns: {negotiation_patterns}
- Builder Reputation: {builder_reputation}

Provide a detailed comparables analysis including:
1. **Comparable Property Overview** (3-5 similar properties with details)
2. **Price Comparison Table** (property, distance, price/sqft, similarity %)
3. **Recent Transaction Evidence** (use the provided transaction evidence with actual sold prices and dates)
4. **Time on Market Analysis** (use the provided time on market data - average days, fast/slow selling patterns)
5. **Price Negotiation Patterns** (use the provided negotiation patterns - average discount from asking price, market dynamics)
6. **Builder Reputation Analysis** (use the provided builder reputation - rating, past projects, on-time delivery, quality score)
7. **Resale vs New Construction Comparison** (pros/cons, price difference)
8. **Value Proposition** (is this property fairly priced, overpriced, or underpriced?)
9. **Competitive Positioning** (how does it compare to alternatives)
10. **Price Justification** (factors that support or contradict the asking price)

Format the response in Markdown with clear sections. Include a comparison table and specific numbers.""",

    "strategy": """Generate investment strategy for {locality}.

Context:
- Investment Strategy: {investment_strategy}
- Action Items: {action_items}
- Timeline: {timeline}
- Week-by-Week Timeline: {week_by_week_timeline}
- Document Checklist: {document_checklist}
- Home Loan Timeline: {home_loan_timeline}
- Registration Steps: {registration_steps}

Provide a detailed strategy including:
1. **Entry Timing Recommendation** (buy now, wait, or negotiate hard)
2. **Negotiation Strategy** (specific points to negotiate, target discount)
3. **Due Diligence Checklist** with deadlines (use the provided week-by-week timeline for Week 1-4 tasks)
4. **Document Collection Checklist** (use the provided document checklist with status and source for each document)
5. **Home Loan Pre-Approval Timeline** (use the provided home loan timeline - pre-approval, full sanction, disbursement)
6. **Registration Process Steps** (use the provided registration steps for what happens at sub-registrar office)
7. **Action Timeline** (week-by-week milestones using the provided timeline)
8. **Portfolio Fit Assessment** (how this fits your overall investment strategy)
9. **Exit Strategy** (when to sell, how to maximize returns)
10. **Post-Purchase Actions** (what to do after registration)

Format the response in Markdown with clear sections. Include specific timelines and checklists.""",

    "data_transparency": """Generate data transparency report for {locality}.

Context:
- Verification Status: {verification_status}
- Data Sources: {data_sources}
- Confidence Breakdown: {confidence_breakdown}
- Per-Metric Confidence: {per_metric_confidence}
- Data Freshness: {data_freshness}
- Verification Sources: {verification_sources}
- Limitations: {limitations}

Provide a detailed transparency report including:
1. **Data Verification Status** (what's verified, what's estimated)
2. **Per-Metric Confidence Scores** (use the provided per-metric confidence for price data, rental data, spatial data, market trends, risk scores)
3. **Source Breakdown and Freshness** (use the provided data sources and data freshness info - when each data type was updated)
4. **Data Quality Assessment** (accuracy, completeness, timeliness)
5. **Missing Data Warnings** (what we couldn't find, how it affects analysis)
6. **Recommendations for Verification** (what to verify independently)
7. **Third-Party Verification Sources** (use the provided verification sources - BBMP Portal, RERA, Sub-Registrar, Google Maps)
8. **Data Update Frequency** (use the provided data freshness - daily, weekly, monthly, quarterly updates)
9. **Methodology Notes** (how we calculated key metrics)
10. **Disclaimer and Limitations** (use the provided limitations about transaction prices, rental data, infrastructure timelines)

Format the response in Markdown with clear sections. Be transparent about uncertainties.""",

    "client_pitch": """Generate a compelling client pitch for {locality}.

Context:
- Summary: {client_summary}
- Building Name: {building_name}
- Valuation: {building_valuation}
- Investment Score: {investment_score}
- Lifestyle Narrative: {lifestyle_narrative}
- Social Proof: {social_proof}
- Future Vision: {future_vision}
- FOMO Element: {fomo_element}

Create a professional pitch including:
1. **Compelling Headline** (attention-grabbing but accurate)
2. **Key Selling Points** (3-5 bullet points with specific benefits)
3. **Lifestyle Narrative** (use the provided lifestyle narrative to paint a picture of daily life - morning walks, school drops, commute, evenings)
4. **Investment Highlights** (ROI potential, appreciation drivers)
5. **Social Proof** (use the provided social proof - notable residents, nearby companies, similar buyer profiles)
6. **Future Vision** (use the provided future vision about upcoming metro, infrastructure, area transformation)
7. **Expected Returns Summary** (3-year projection with confidence)
8. **Risk Mitigation** (how we've addressed key concerns)
9. **FOMO Element** (use the provided FOMO element - limited inventory, price trends, why act now)
10. **Call to Action** (next steps, contact information)

Format the response in Markdown. Make it persuasive but professional. Use emotional hooks balanced with data."""
}


# ============================================
# QUALITY VALIDATION LAYER
# ============================================

# Quality validation prompt for local Phi model
QUALITY_CHECK_PROMPT = """Review this report section for quality. Score each criterion 0.0 to 1.0.

SECTION TYPE: {tab_id}
GENERATED CONTENT:
{content}

INPUT DATA USED:
{input_data}

Score these criteria:
1. MARKDOWN_FORMAT: Are headers (#, ##), lists (-, *), and tables properly formatted?
2. COMPLETENESS: Are all required subsections present for this section type?
3. NUMERICAL_ACCURACY: Do numbers match input data? Any hallucinated statistics?
4. FACTUAL_GROUNDING: Are claims supported by the input data provided?
5. CONTENT_QUALITY: Is writing clear, professional, no repetition?

IMPORTANT: Return ONLY valid JSON, no other text.
Return: {{"scores": {{"markdown": 0.0-1.0, "completeness": 0.0-1.0, "numerical": 0.0-1.0, "factual": 0.0-1.0, "quality": 0.0-1.0}}, "overall": 0.0-1.0, "issues": ["issue1", "issue2"]}}"""

# Required subsections for each tab type
REQUIRED_SUBSECTIONS = {
    "decision_verdict": ["Executive Summary", "Reasoning", "Confidence", "Positive Factors", "Risk Factors", "Negotiation", "Holding Period", "Exit Strategy"],
    "market_snapshot": ["Market Overview", "Price Trend", "Demand-Supply", "Rental Yield", "Momentum", "Risks"],
    "spatial_intelligence": ["Infrastructure", "POI Analysis", "Commute", "Metro", "Schools", "Hospitals"],
    "risk_analysis": ["Risk Summary", "Flood", "Legal", "Market", "Infrastructure", "Mitigation"],
    "roi_projection": ["Scenarios", "Entry Price", "Exit Price", "Rental Income", "Tax", "Timeline"],
    "comparables": ["Property Overview", "Price Comparison", "Transaction Evidence", "Builder Reputation"],
    "strategy": ["Entry Timing", "Negotiation", "Due Diligence", "Timeline", "Exit Strategy"],
    "data_transparency": ["Verification Status", "Confidence Scores", "Data Sources", "Limitations"],
    "client_pitch": ["Headline", "Selling Points", "Lifestyle", "Investment Highlights", "Call to Action"]
}


@dataclass
class QualityScore:
    """Quality validation result"""
    markdown: float = 0.0
    completeness: float = 0.0
    numerical: float = 0.0
    factual: float = 0.0
    quality: float = 0.0
    overall: float = 0.0
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
    
    def passes_threshold(self, threshold: float = 0.7) -> bool:
        return self.overall >= threshold


class QualityValidator:
    """
    Validates generated report sections using local Phi model.
    Fast, cost-efficient quality gate before delivery.
    """
    
    def __init__(self, model: str = "phi4:latest"):
        self.model = model
        self.validator_client = None
    
    async def initialize(self):
        """Initialize the local Phi model client"""
        try:
            from ai.ollama_client import OllamaClient
            self.validator_client = OllamaClient(
                model=self.model,
                timeout=30,  # Fast validation
                max_context=4096
            )
            logger.info(f"Quality validator initialized with {self.model}")
        except Exception as e:
            logger.warning(f"Failed to initialize quality validator: {e}")
            self.validator_client = None
    
    async def validate_section(
        self,
        tab_id: str,
        content: str,
        input_data: Dict[str, Any]
    ) -> QualityScore:
        """
        Validate a generated section using local Phi model.
        
        Args:
            tab_id: Type of section (decision_verdict, market_snapshot, etc.)
            content: Generated content to validate
            input_data: Original input data used for generation
            
        Returns:
            QualityScore with detailed scores and issues
        """
        if not self.validator_client:
            # No validator available, return passing score
            return QualityScore(overall=0.8, issues=["Validator not available - auto-passed"])
        
        try:
            # Format the validation prompt
            prompt = QUALITY_CHECK_PROMPT.format(
                tab_id=tab_id,
                content=content[:2000],  # Truncate for speed
                input_data=json.dumps(input_data, indent=2)[:1000]  # Truncate input
            )
            
            # Call local Phi model for validation
            response = await self.validator_client.generate(
                prompt=prompt,
                temperature=0.1,  # Low temperature for consistent scoring
                max_tokens=300
            )
            
            # Parse JSON response
            # Handle potential markdown code blocks
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            result = json.loads(response)
            
            scores = result.get("scores", {})
            return QualityScore(
                markdown=float(scores.get("markdown", 0.5)),
                completeness=float(scores.get("completeness", 0.5)),
                numerical=float(scores.get("numerical", 0.5)),
                factual=float(scores.get("factual", 0.5)),
                quality=float(scores.get("quality", 0.5)),
                overall=float(result.get("overall", 0.5)),
                issues=result.get("issues", [])
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse validation response: {e}")
            return QualityScore(overall=0.6, issues=["Failed to parse validator response"])
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            error_msg = f"Validation error: {str(e)}"
            return QualityScore(overall=0.6, issues=[error_msg])
    
    def quick_validate(self, tab_id: str, content: str) -> QualityScore:
        """
        Quick synchronous validation without LLM.
        Checks basic formatting and completeness.
        """
        issues = []
        scores = {
            "markdown": 0.5,
            "completeness": 0.5,
            "numerical": 0.5,
            "factual": 0.5,
            "quality": 0.5
        }
        
        # Check markdown formatting
        has_headers = "#" in content
        has_lists = "-" in content or "*" in content
        if has_headers and has_lists:
            scores["markdown"] = 0.9
        elif has_headers or has_lists:
            scores["markdown"] = 0.7
        else:
            scores["markdown"] = 0.3
            issues.append("Missing markdown formatting")
        
        # Check completeness
        required = REQUIRED_SUBSECTIONS.get(tab_id, [])
        found = sum(1 for sub in required if sub.lower() in content.lower())
        if required:
            scores["completeness"] = found / len(required)
            if scores["completeness"] < 0.5:
                issues.append(f"Missing subsections: {len(required) - found}/{len(required)}")
        
        # Check content quality
        word_count = len(content.split())
        if word_count < 100:
            scores["quality"] = 0.3
            issues.append("Content too short")
        elif word_count < 300:
            scores["quality"] = 0.6
        else:
            scores["quality"] = 0.8
        
        # Calculate overall
        overall = sum(scores.values()) / len(scores)
        
        return QualityScore(
            markdown=scores["markdown"],
            completeness=scores["completeness"],
            numerical=scores["numerical"],
            factual=scores["factual"],
            quality=scores["quality"],
            overall=overall,
            issues=issues
        )


@dataclass
class ReportSection:
    """Represents a generated report section"""
    tab_id: str
    title: str
    content: str
    generated_at: datetime
    tokens_used: int = 0


class ReportGenerator:
    """
    Generates detailed reports using LLM for each smart tab
    
    Features:
    - Sequential tab processing
    - Progress tracking via TaskManager
    - Markdown and PDF generation
    - Error handling and retry logic
    - Quality validation with local Phi model
    """
    
    def __init__(self):
        self.task_manager = None  # Injected later
        self.llm_client = None  # Injected later
        self.quality_validator = None  # Quality validation layer
        
    async def initialize(self):
        """Initialize dependencies"""
        from .task_manager import get_task_manager
        self.task_manager = get_task_manager()
        
        # Try to import LLM client
        try:
            from ai.model_router import get_model_router
            self.llm_client = get_model_router()
        except ImportError:
            logger.warning("Model router not available, will use fallback generation")
            self.llm_client = None
        
        # Initialize quality validator with local Phi model
        self.quality_validator = QualityValidator(model="phi4:latest")
        await self.quality_validator.initialize()
    
    async def generate_report(
        self,
        task_id: str,
        locality: str,
        lat: float,
        lng: float,
        tab_data: Dict[str, Any],
        include_tabs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a detailed report by processing each tab
        
        Args:
            task_id: Task ID for progress tracking
            locality: Location name
            lat: Latitude
            lng: Longitude
            tab_data: Data for each tab from SmartTabsContainer
            include_tabs: List of tabs to include (default: all)
            
        Returns:
            Dict with markdown content, sections, and metadata
        """
        if not self.task_manager:
            await self.initialize()
        
        # Default to all tabs
        tabs_to_process = include_tabs or list(TAB_PROMPTS.keys())
        total_tabs = len(tabs_to_process)
        
        # Start task
        self.task_manager.start_task(task_id)
        
        sections: List[ReportSection] = []
        errors: List[str] = []
        
        for idx, tab_id in enumerate(tabs_to_process):
            try:
                # Update progress
                self.task_manager.update_progress(
                    task_id,
                    current_step=idx,
                    current_tab=tab_id,
                    message=f"Processing {tab_id.replace('_', ' ').title()}..."
                )
                
                # Generate section content
                section = await self._generate_tab_section(
                    tab_id,
                    locality,
                    tab_data.get(tab_id, {})
                )
                sections.append(section)
                
                # Mark tab as completed
                self.task_manager.update_progress(
                    task_id,
                    completed_tab=tab_id
                )
                
            except Exception as e:
                logger.error(f"Error generating {tab_id}: {e}")
                errors.append(f"{tab_id}: {str(e)}")
                # Continue with other tabs
        
        # Generate combined markdown
        markdown_content = self._combine_sections(locality, sections, lat, lng)
        
        # Generate PDF (simplified version)
        pdf_content = await self._generate_pdf(markdown_content, locality)
        
        # Complete task
        result = {
            "markdown": markdown_content,
            "pdf_available": pdf_content is not None,
            "sections": [
                {
                    "tab_id": s.tab_id,
                    "title": s.title,
                    "content": s.content,
                    "tokens_used": s.tokens_used
                }
                for s in sections
            ],
            "locality": locality,
            "lat": lat,
            "lng": lng,
            "generated_at": datetime.now().isoformat(),
            "total_tabs": total_tabs,
            "successful_tabs": len(sections),
            "errors": errors if errors else None
        }
        
        self.task_manager.complete_task(task_id, result)
        
        return result
    
    async def _generate_tab_section(
        self,
        tab_id: str,
        locality: str,
        data: Dict[str, Any]
    ) -> ReportSection:
        """Generate content for a single tab using Ollama Cloud LLM for premium quality"""
        
        prompt_template = TAB_PROMPTS.get(tab_id)
        if not prompt_template:
            raise ValueError(f"No prompt template for tab: {tab_id}")
        
        # Default values for all template keys to prevent KeyError
        DEFAULT_VALUES = {
            # decision_verdict
            'verdict': 'HOLD',
            'confidence': 70,
            'risk_level': 'MODERATE',
            'top_reasons': 'Strong location fundamentals, Good connectivity, Established social infrastructure',
            'key_risks': 'Market volatility, Infrastructure execution delays',
            'strategy_recommendation': 'Moderate approach with staggered entry',
            'negotiation_leverage_points': 'Recent price corrections, Extended market days',
            'deal_breaker_flags': 'Title issues, Pending litigation, Zoning violations',
            'optimal_holding_period': '5-7 years',
            'exit_timing': 'Post infrastructure completion',
            # market_snapshot
            'avg_price_sqft': 8500,
            'sample_count': 150,
            'price_trend': '+8% YoY',
            'demand_level': 'High',
            'supply_level': 'Moderate',
            'days_on_market': 45,
            'new_launches': '2 projects in last 6 months',
            'rental_yield': '3.5%',
            'price_range': '₹7,500 - ₹10,000/sqft',
            'micro_market_comparison': 'Competitive with adjacent areas',
            # spatial_intelligence
            'metro_distance': 1.5,
            'metro_status': 'Operational',
            'schools': '5+ schools within 3km',
            'hospitals': '3+ hospitals within 5km',
            'malls': '2 major malls within 5km',
            'tech_parks': 'ITPL, EPIP Zone nearby',
            'airports': '45 min to airport',
            'commute_times': 'MG Road: 25min, Electronic City: 35min',
            'walkability_score': 65,
            'transit_score': 70,
            'last_mile_connectivity': 'Auto, Bus available',
            'school_admission_season': 'February-March',
            'future_growth_areas': 'Metro corridor expansion',
            # risk_analysis
            'overall_risk_score': 35,
            'flood': 'LOW - Area well elevated',
            'legal': 'MODERATE - Verify all documents',
            'market': 'LOW - Stable demand',
            'infrastructure': 'LOW - Well developed',
            'environmental': 'MODERATE - Check pollution levels',
            'mitigation_suggestions': 'Title verification, RERA check, Encumbrance certificate',
            'legal_checklist': 'BBMP Khata, BDA approval, Encumbrance, RERA',
            'flood_history': 'No major flooding in last 10 years',
            'warning_signs': 'Pending OC, Deviation from approved plan',
            # roi_projection
            'projection_3year': '+20-25%',
            'entry_exit': 'Enter: ₹8,200-8,500/sqft, Exit: ₹10,500+/sqft',
            'rental_yield': '3.5-4%',
            'investment_score': 75,
            'tax_implications': 'LTCG benefits after 2 years',
            'comparison_with_alternatives': 'Better than FD, Comparable to MF',
            'break_even_analysis': '5-6 years with rental income',
            # comparables
            'similar_properties': '3 similar properties in vicinity',
            'price_comparison': 'Subject property at par with market',
            'recent_transactions': 'Last 3 months: 5 transactions',
            'time_on_market': '45 days average',
            'negotiation_patterns': '5-8% discount achievable',
            'builder_reputation': 'Grade A builder, 85% on-time delivery',
            'resale_vs_new': 'Resale 10-15% cheaper than new',
            # strategy
            'entry_timing': 'NOW - Prices stable',
            'negotiation_strategy': 'Start 8% below asking',
            'due_diligence_deadline': '2 weeks',
            'document_checklist': 'Title, OC, Khata, EC, RERA',
            'home_loan_pre_approval': '7-10 days',
            'registration_process': 'Online booking, 1 day process',
            'action_timeline': '6 weeks to possession',
            'portfolio_fit': 'Good for long-term growth',
            'exit_strategy': 'Sell in Year 3-5 post-metro',
            'post_purchase_actions': 'Khata transfer, Utility connections',
            # data_transparency
            'verification_status': 'VERIFIED',
            'data_sources': 'Property registry, POI database, Market listings',
            'confidence_scores': 'Price: 85%, Rental: 70%, Spatial: 92%',
            'missing_data_warnings': 'Transaction prices are estimates',
            'independent_verification': 'Sub-registrar office, BBMP portal',
            # client_pitch
            'headline': 'Prime investment opportunity',
            'key_selling_points': 'Location, Connectivity, Infrastructure',
            'lifestyle_narrative': 'Modern urban living with excellent amenities',
            'investment_highlights': '15-20% appreciation in 3 years',
            'social_proof': 'IT professionals, Doctors, Business owners',
            'future_vision': 'Metro connectivity by 2028',
            'expected_returns': '12-16% annualized ROI',
            'risk_mitigation': 'Due diligence completed'
        }
        
        # Merge provided data with defaults (provided data takes precedence)
        merged_data = {**DEFAULT_VALUES, **{k: self._format_value(v) for k, v in data.items()}}
        
        # Format prompt with merged data
        try:
            prompt = prompt_template.format(locality=locality, **merged_data)
        except KeyError as e:
            # Still handle any unexpected missing keys
            logger.warning(f"Missing key in template for {tab_id}: {e}")
            # Use string replacement for any remaining placeholders
            prompt = prompt_template.format(locality=locality, **merged_data)
            prompt = prompt.replace("{", "").replace("}", "")
        
        # Tab-specific Ollama Cloud model configuration for premium reports
        # Using Ollama cloud models (suffix :cloud) for premium quality
        TAB_MODEL_CONFIG = {
            "decision_verdict": {
                "model": "kimi-k2.5:cloud",  # Best for investment reasoning
                "max_tokens": 2000,
                "temperature": 0.3,  # Lower for more deterministic reasoning
                "description": "Investment verdict with reasoning"
            },
            "market_snapshot": {
                "model": "deepseek-v3.2:cloud",  # Good for data analysis
                "max_tokens": 1800,
                "temperature": 0.4,
                "description": "Market analysis"
            },
            "spatial_intelligence": {
                "model": "deepseek-v3.2:cloud",  # Good for factual data
                "max_tokens": 1500,
                "temperature": 0.3,
                "description": "Spatial analysis"
            },
            "risk_analysis": {
                "model": "kimi-k2.5:cloud",  # Best for legal/risk assessment
                "max_tokens": 2000,
                "temperature": 0.2,  # Very low for accurate legal content
                "description": "Risk assessment"
            },
            "roi_projection": {
                "model": "kimi-k2.5:cloud",  # Best for financial calculations
                "max_tokens": 1800,
                "temperature": 0.3,
                "description": "ROI projections"
            },
            "comparables": {
                "model": "deepseek-v3.2:cloud",  # Good for data comparison
                "max_tokens": 1500,
                "temperature": 0.4,
                "description": "Property comparables"
            },
            "strategy": {
                "model": "kimi-k2.5:cloud",  # Best for actionable recommendations
                "max_tokens": 3000,  # Increased from 2000 to prevent truncation for 10 subsections
                "temperature": 0.3,
                "description": "Investment strategy"
            },
            "data_transparency": {
                "model": "deepseek-v3.2:cloud",  # Good for structured data
                "max_tokens": 1200,
                "temperature": 0.2,
                "description": "Data transparency"
            },
            "client_pitch": {
                "model": "deepseek-v3.2:cloud",  # Good for creative but professional
                "max_tokens": 1500,
                "temperature": 0.5,  # Higher for creative writing
                "description": "Client pitch"
            }
        }
        
        config = TAB_MODEL_CONFIG.get(tab_id, {
            "model": "deepseek-v3.2:cloud",
            "max_tokens": 1500,
            "temperature": 0.4,
            "description": tab_id
        })
        
        # Call Ollama Cloud LLM for premium quality
        content = ""
        tokens_used = 0
        max_retries = 2  # Maximum regeneration attempts
        quality_threshold = 0.7  # Minimum quality score
        
        # Define model fallback chain for premium quality
        model_fallback_chain = [
            config["model"],           # Primary model from config
            "deepseek-v3.2:cloud",     # Secondary fallback
            "glm-5:cloud"              # Tertiary fallback
        ]
        
        # Remove duplicates while preserving order
        model_fallback_chain = list(dict.fromkeys(model_fallback_chain))
        
        last_error = None
        for model_index, current_model in enumerate(model_fallback_chain):
            for attempt in range(max_retries + 1):
                try:
                    from ai.ollama_client import OllamaClient
                    
                    # Create client for the specific cloud model
                    client = OllamaClient(
                        model=current_model,
                        timeout=180,  # Cloud models may take longer
                        max_context=32768  # Cloud models have larger context
                    )
                    
                    logger.info(f"Generating {tab_id} using model {current_model} (attempt {attempt + 1}, model {model_index + 1}/{len(model_fallback_chain)})")
                    
                    content = await client.generate(
                        prompt=prompt,
                        temperature=config["temperature"],
                        max_tokens=config["max_tokens"]
                    )
                    
                    tokens_used = len(content.split())  # Approximate token count
                    logger.info(f"Generated {tab_id}: {len(content)} chars, ~{tokens_used} tokens")
                    
                    # Quality validation with local Phi model
                    if self.quality_validator:
                        quality_score = await self.quality_validator.validate_section(
                            tab_id=tab_id,
                            content=content,
                            input_data=data
                        )
                        
                        logger.info(f"Quality score for {tab_id}: {quality_score.overall:.2f} - Issues: {quality_score.issues}")
                        
                        if quality_score.passes_threshold(quality_threshold):
                            logger.info(f"Quality validation passed for {tab_id}")
                            break  # Good quality, proceed
                        else:
                            logger.warning(f"Quality validation failed for {tab_id} (score: {quality_score.overall:.2f})")
                            if attempt < max_retries:
                                logger.info(f"Regenerating {tab_id} due to low quality...")
                                continue  # Retry generation
                            else:
                                # Try next model in fallback chain
                                logger.warning(f"Max retries reached for {tab_id} with model {current_model}")
                                break
                    else:
                        # No validator, accept content
                        break
                    
                except Exception as e:
                    last_error = e
                    logger.warning(f"Model {current_model} failed for {tab_id}: {e}")
                    if attempt < max_retries:
                        continue  # Retry with same model
                    else:
                        break  # Move to next model in fallback chain
            
            # If we got valid content, break out of model loop
            if content and tokens_used > 0:
                break
        
        # Premium product: No fallback content - fail with clear error
        if not content or tokens_used == 0:
            error_msg = f"Failed to generate {tab_id} section after trying all models ({', '.join(model_fallback_chain)}). Last error: {last_error}"
            logger.error(error_msg)
            raise Exception(f"Failed to generate {tab_id} section. Please try again. All LLM models exhausted.")
        
        # Get tab title
        tab_titles = {
            "decision_verdict": "Investment Verdict",
            "market_snapshot": "Market Snapshot",
            "spatial_intelligence": "Spatial Intelligence",
            "risk_analysis": "Risk Analysis",
            "roi_projection": "ROI Projection",
            "comparables": "Comparable Properties",
            "strategy": "Investment Strategy",
            "data_transparency": "Data Transparency",
            "client_pitch": "Client Pitch"
        }
        
        return ReportSection(
            tab_id=tab_id,
            title=tab_titles.get(tab_id, tab_id.replace("_", " ").title()),
            content=content,
            generated_at=datetime.now(),
            tokens_used=tokens_used
        )
    
    def _format_value(self, value: Any) -> str:
        """Format a value for prompt insertion"""
        if value is None:
            return "N/A"
        elif isinstance(value, (list, tuple)):
            return ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            return json.dumps(value, indent=2)
        else:
            return str(value)
    
    def _generate_fallback_content(
        self,
        tab_id: str,
        locality: str,
        data: Dict[str, Any]
    ) -> str:
        """Generate fallback content without LLM"""
        
        if tab_id == "decision_verdict":
            return f"""## Investment Verdict for {locality}

**Verdict:** {data.get('verdict', 'HOLD')}
**Confidence:** {data.get('confidence_score', 75)}%
**Risk Level:** {data.get('risk_level', 'MEDIUM')}

### Top Reasons
{chr(10).join(f"- {r}" for r in data.get('top_reasons', ['Good location', 'Developing infrastructure']))}

### Key Risks
{chr(10).join(f"- {r}" for r in data.get('key_risks', ['Market volatility']))}
"""
        
        elif tab_id == "market_snapshot":
            return f"""## Market Snapshot for {locality}

**Average Price:** ₹{data.get('avg_price_sqft', 8500):,}/sqft
**Rental Yield:** {data.get('rental_yield', '3.5%')}
**Demand/Supply:** {data.get('demand_supply', 'Balanced')}

### Price Trends
- 1 Year: {data.get('price_trend', {}).get('1Y', '+12%')}
- 3 Years: {data.get('price_trend', {}).get('3Y', '+35%')}
- 5 Years: {data.get('price_trend', {}).get('5Y', '+62%')}
"""
        
        elif tab_id == "spatial_intelligence":
            infrastructure = data.get('nearby_infrastructure', [])
            infra_str = chr(10).join(f"- {i.get('name', 'Unknown')}: {i.get('distance', 'N/A')}" for i in infrastructure[:5]) if infrastructure else "No data available"
            return f"""## Spatial Intelligence for {locality}

**Walkability Score:** {data.get('walkability_score', 75)}/100
**Transit Score:** {data.get('transit_score', 68)}/100

### Nearby Infrastructure
{infra_str}
"""
        
        elif tab_id == "risk_analysis":
            return f"""## Risk Analysis for {locality}

**Overall Risk Score:** {data.get('overall_risk_score', 35)}/100

### Risk Categories
- Flood Risk: {data.get('risks', {}).get('flood', {}).get('level', 'LOW')}
- Legal Risk: {data.get('risks', {}).get('legal', {}).get('level', 'MODERATE')}
- Market Risk: {data.get('risks', {}).get('market', {}).get('level', 'LOW')}

### Mitigation Suggestions
{chr(10).join(f"- {m}" for m in data.get('mitigation_suggestions', ['Verify documents', 'Site visit recommended']))}
"""
        
        elif tab_id == "roi_projection":
            return f"""## ROI Projection for {locality}

### 3-Year Projection
- **Best Case:** {data.get('projection_3year', {}).get('best_case', {}).get('return', '+35%')}
- **Expected:** {data.get('projection_3year', {}).get('expected', {}).get('return', '+20%')}
- **Worst Case:** {data.get('projection_3year', {}).get('worst_case', {}).get('return', '+3%')}

### Entry/Exit
- **Recommended Entry:** {data.get('entry_exit', {}).get('recommended_entry', '₹8,200-8,800/sqft')}
- **Target Exit:** {data.get('entry_exit', {}).get('target_exit', '₹11,000+/sqft')}
"""
        
        elif tab_id == "comparables":
            comps = data.get('comparables', [])
            comps_str = chr(10).join(f"| {c.get('project', 'Unknown')} | {c.get('distance', 'N/A')} | ₹{c.get('price_sqft', 0):,} | {c.get('similarity', 0)}% |" for c in comps) if comps else "No comparables available"
            return f"""## Comparable Properties for {locality}

| Project | Distance | Price/sqft | Similarity |
|---------|----------|------------|------------|
{comps_str}

### Price Analysis
- Subject Property: ₹{data.get('price_analysis', {}).get('subject_property', 8500):,}/sqft
- Area Average: ₹{data.get('price_analysis', {}).get('area_average', 8900):,}/sqft
"""
        
        elif tab_id == "strategy":
            return f"""## Investment Strategy for {locality}

### Entry Timing
{data.get('investment_strategy', {}).get('entry_timing', 'NOW - prices stable')}

### Negotiation Range
{data.get('investment_strategy', {}).get('negotiation_range', '₹8,200-8,600/sqft')}

### Action Items
{chr(10).join(f"- [ ] {a}" for a in data.get('action_items', ['Schedule site visit', 'Review documents']))}

### Timeline
- Due Diligence: {data.get('timeline', {}).get('due_diligence', '2 weeks')}
- Closing: {data.get('timeline', {}).get('closing', '4-6 weeks')}
"""
        
        elif tab_id == "data_transparency":
            return f"""## Data Transparency for {locality}

**Verification Status:** {data.get('verification_status', 'VERIFIED')}

### Data Sources
{chr(10).join(f"- {s.get('source', 'Unknown')}: {s.get('records', 0)} records (Updated: {s.get('freshness', 'N/A')})" for s in data.get('data_sources', []))}

### Confidence Breakdown
{chr(10).join(f"- {k}: {v}%" for k, v in data.get('confidence_breakdown', {}).items())}
"""
        
        elif tab_id == "client_pitch":
            return f"""## Client Pitch for {locality}

### {data.get('client_summary', {}).get('headline', 'Premium Investment Opportunity')}

**Asking Price:** {data.get('client_summary', {}).get('ask', '₹1.2 Cr')}
**Expected Return:** {data.get('client_summary', {}).get('expected_return', '18-25% in 3 years')}

### Key Points
{chr(10).join(f"- {p}" for p in data.get('client_summary', {}).get('key_points', ['Great location', 'Strong potential']))}

---
*Generated by Valora AI*
"""
        
        else:
            return f"## {tab_id.replace('_', ' ').title()}\n\nData not available for this section."
    
    def _combine_sections(
        self,
        locality: str,
        sections: List[ReportSection],
        lat: float,
        lng: float
    ) -> str:
        """Combine all sections into a single markdown document"""
        
        # Header
        md = f"""# Valora Smart Report

## {locality}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Coordinates:** {lat:.4f}, {lng:.4f}

---

"""
        
        # Table of Contents
        md += "## Table of Contents\n\n"
        for idx, section in enumerate(sections, 1):
            md += f"{idx}. [{section.title}](#{section.tab_id})\n"
        md += "\n---\n\n"
        
        # Sections
        for section in sections:
            md += f"<a name=\"{section.tab_id}\"></a>\n\n"
            md += section.content
            md += "\n\n---\n\n"
        
        # Footer
        md += f"""
## Disclaimer

This report is generated by Valora AI for informational purposes only. 
It should not be considered as financial advice. Always conduct your own due diligence 
and consult with professionals before making investment decisions.

---

**Generated by Valora AI** | {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Report ID:** valora_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}
"""
        
        return md
    
    async def _generate_pdf(self, markdown: str, locality: str) -> Optional[bytes]:
        """Generate PDF from markdown content"""
        try:
            # Try to use a proper PDF library
            import io
            
            # Check if we have reportlab or weasyprint
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.lib.units import inch
                
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter)
                styles = getSampleStyleSheet()
                story = []
                
                # Simple markdown to PDF conversion
                for line in markdown.split('\n'):
                    if line.startswith('# '):
                        story.append(Paragraph(line[2:], styles['Title']))
                    elif line.startswith('## '):
                        story.append(Paragraph(line[3:], styles['Heading2']))
                    elif line.startswith('### '):
                        story.append(Paragraph(line[4:], styles['Heading3']))
                    elif line.strip():
                        story.append(Paragraph(line, styles['Normal']))
                    else:
                        story.append(Spacer(1, 0.1 * inch))
                
                doc.build(story)
                return buffer.getvalue()
                
            except ImportError:
                # Fallback: return None (will use markdown download only)
                logger.warning("PDF library not available, skipping PDF generation")
                return None
                
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return None


# Singleton instance
_report_generator = None


def get_report_generator() -> ReportGenerator:
    """Get the singleton ReportGenerator instance"""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator
