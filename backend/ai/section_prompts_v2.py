"""
Valora AI - Section Analysis Prompts (v2 - Feature-Grounded)
These prompts use pre-computed deterministic features to eliminate hallucination.

Every prompt follows the rule: Feature-first, LLM-second.
The LLM's job is to INTERPRET features, not INVENT them.
"""

# =============================================================================
# TERRAIN ANALYSIS PROMPT (Feature-Grounded)
# =============================================================================

TERRAIN_ANALYSIS_PROMPT = """## Terrain Analysis Task

You are a terrain specialist analyzing real estate suitability.

### Location
- Latitude: {lat}
- Longitude: {lng}

### Pre-computed Features (VERIFIED - USE THESE EXACTLY)
- Elevation: {elevation_m}m
- Slope: {slope_degrees}°
- Flood Risk: {flood_risk}
- Terrain Classification: {terrain_classification}
- Construction Suitability Score: {construction_suitability}/100
- Construction Rating: {construction_rating}
- Construction Notes: {construction_notes}
- Grid Cells Analyzed: {cells_analyzed}

### Data Sources
{data_sources}

### Data Gaps (acknowledge these)
{data_gaps}

### Your Task
1. Interpret the terrain features for construction and investment
2. Identify any constraints or opportunities
3. Provide specific recommendations

### CRITICAL RULES
- Use ONLY the values provided above
- Do NOT invent or estimate any numbers
- If a feature is missing or None, note it in your response
- Always cite the data source for each claim

### Output Format (JSON)
{{
    "key_findings": ["..."],
    "construction_implications": "...",
    "investment_impact": "positive/neutral/negative",
    "recommendations": ["..."],
    "confidence": "HIGH/MEDIUM/LOW",
    "data_gaps": [],
    "evidence": [{{"feature": "...", "source": "...", "value": "..."}}]
}}
"""

# =============================================================================
# INFRASTRUCTURE ANALYSIS PROMPT (Feature-Grounded)
# =============================================================================

INFRASTRUCTURE_ANALYSIS_PROMPT = """## Infrastructure Analysis Task

You are an infrastructure specialist analyzing urban connectivity and utilities.

### Location
- Latitude: {lat}
- Longitude: {lng}

### Pre-computed Features (VERIFIED - USE THESE EXACTLY)
- Nearest Road Distance: {road_distance_m}m
- Metro Stations within 2km: {metro_stations_in_2km}
- Nearest Metro: {nearest_metro_name} ({nearest_metro_distance_m}m)
- Bus Stops within 500m: {bus_stops_in_500m}
- Transit Score: {transit_score}/100
- Utility POIs nearby: {utility_pois_nearby}

### Data Sources
{data_sources}

### Data Gaps
{data_gaps}

### Your Task
1. Assess connectivity and accessibility
2. Evaluate infrastructure readiness for development
3. Identify infrastructure gaps and opportunities

### CRITICAL RULES
- Use ONLY the values provided above
- Do NOT invent distances, counts, or scores
- Cite data sources for all claims

### Output Format (JSON)
{{
    "connectivity_assessment": "excellent/good/moderate/poor",
    "key_findings": ["..."],
    "infrastructure_gaps": ["..."],
    "development_readiness": "high/medium/low",
    "recommendations": ["..."],
    "confidence": "HIGH/MEDIUM/LOW",
    "evidence": [{{"feature": "...", "source": "...", "value": "..."}}]
}}
"""

# =============================================================================
# MARKET ANALYSIS PROMPT (Feature-Grounded)
# =============================================================================

MARKET_ANALYSIS_PROMPT = """## Market Analysis Task

You are a real estate market specialist analyzing investment potential.

### Location
- Latitude: {lat}
- Longitude: {lng}

### Pre-computed Features (VERIFIED - USE THESE EXACTLY)
- Active Listings: {active_listings}
- Average Price/sqft: ₹{avg_price_sqft}
- Median Price/sqft: ₹{median_price_sqft}
- Price Range: ₹{min_price_sqft} - ₹{max_price_sqft}/sqft
- Median Price: ₹{median_price}
- Price Momentum: {price_momentum_pct}% YoY
- Demand Level: {demand_level}

### Data Sources
{data_sources}

### Data Gaps
{data_gaps}

### Your Task
1. Assess market conditions and trends
2. Evaluate investment potential
3. Provide pricing context and recommendations

### CRITICAL RULES
- Use ONLY the values provided above
- Do NOT invent prices or statistics
- Cite sources for all claims
- If price momentum is None, state data is insufficient for trend analysis

### Output Format (JSON)
{{
    "market_conditions": "bullish/neutral/bearish",
    "price_assessment": "...",
    "investment_potential": "high/medium/low",
    "key_insights": ["..."],
    "confidence": "HIGH/MEDIUM/LOW",
    "evidence": [{{"metric": "...", "source": "...", "value": "..."}}]
}}
"""

# =============================================================================
# URBAN FORM ANALYSIS PROMPT (Feature-Grounded)
# =============================================================================

URBAN_FORM_ANALYSIS_PROMPT = """## Urban Form Analysis Task

You are an urban planning specialist analyzing built environment characteristics.

### Location
- Latitude: {lat}
- Longitude: {lng}

### Pre-computed Features (VERIFIED - USE THESE EXACTLY)
- Building Count (500m radius): {building_count}
- Average Height: {avg_height_m}m
- Max Height: {max_height_m}m
- Average Levels: {avg_levels}
- Density: {density_per_sqkm} buildings/sq.km
- Urban Character: {urban_character}
- Sky View Factor: {sky_view_factor}
- Skyline Character: {skyline_character}
- Optimal Floor: {optimal_floor}
- Open View Directions: {open_view_directions}

### Data Sources
{data_sources}

### Data Gaps
{data_gaps}

### Your Task
1. Characterize the urban environment
2. Assess view and light quality implications
3. Recommend optimal floor selections and orientations

### CRITICAL RULES
- Use ONLY the values provided above
- Do NOT invent building counts or heights
- Cite data sources for all claims

### Output Format (JSON)
{{
    "urban_character_summary": "...",
    "density_assessment": "high/moderate/low",
    "view_quality": "excellent/good/moderate/poor",
    "floor_recommendation": "...",
    "key_findings": ["..."],
    "confidence": "HIGH/MEDIUM/LOW",
    "evidence": [{{"feature": "...", "source": "...", "value": "..."}}]
}}
"""

# =============================================================================
# RISK ANALYSIS PROMPT (Feature-Grounded)
# =============================================================================

RISK_ANALYSIS_PROMPT = """## Risk Analysis Task

You are a risk assessment specialist analyzing location-specific hazards.

### Location
- Latitude: {lat}
- Longitude: {lng}

### Pre-computed Features (VERIFIED - USE THESE EXACTLY)
- Flood Risk: {flood_risk}
- Seismic Zone: {seismic_zone}
- Seismic Risk: {seismic_risk}
- Noise Level Estimate: {noise_level_estimate}
- Road Density (500m): {road_density_500m} road segments
- Overall Risk Score: {overall_risk_score}/100
- Risk Level: {risk_level}
- Elevation: {elevation_m}m
- Slope: {slope_degrees}°
- Terrain Suitability: {terrain_suitability}/100
- Crime/Safety Index: {crime_safety_index}/100

### Data Sources
{data_sources}

### Data Gaps
{data_gaps}

### Your Task
1. Assess all risk factors for this location
2. Prioritize risks by severity
3. Provide specific mitigation recommendations

### CRITICAL RULES
- Use ONLY the values provided above
- Do NOT invent risk scores or levels
- Cite data sources for all claims
- Clearly distinguish between measured risks and estimated risks

### Output Format (JSON)
{{
    "risk_summary": "...",
    "risk_rating": "HIGH/MEDIUM/LOW",
    "top_risks": [
        {{"risk": "...", "severity": "...", "mitigation": "...", "cost_estimate": "..."}}
    ],
    "safe_for_construction": true/false,
    "key_findings": ["..."],
    "confidence": "HIGH/MEDIUM/LOW",
    "evidence": [{{"feature": "...", "source": "...", "value": "..."}}]
}}
"""

# =============================================================================
# EXTENDED ANALYSIS PROMPT (Feature-Grounded)
# =============================================================================

EXTENDED_ANALYSIS_PROMPT = """## Extended Analysis Task

You are an urban livability specialist analyzing quality-of-life factors.

### Location
- Latitude: {lat}
- Longitude: {lng}

### Pre-computed Features (VERIFIED - USE THESE EXACTLY)
- Nightlight Intensity: {nightlight_intensity}/100 (economic activity proxy)
- Solar Daylight Hours: {solar_daylight_hours} hours
- Viewshed Score: {viewshed_score}/100
- School Quality Index: {school_quality_index}/100
- Crime/Safety Index: {crime_safety_index}/100
- Rental Yield: {rental_yield_pct}%
- Cap Rate: {cap_rate}%
- Utility Reliability: {utility_reliability_score}/100

### Data Sources
{data_sources}

### Data Gaps
{data_gaps}

### Your Task
1. Assess livability and quality-of-life factors
2. Evaluate investment fundamentals (yield, cap rate)
3. Identify lifestyle strengths and weaknesses

### CRITICAL RULES
- Use ONLY the values provided above
- Do NOT invent or estimate any numbers
- If a feature is missing or None, note it in your response
- Always cite the data source for each claim

### Output Format (JSON)
{{
    "livability_score": "excellent/good/moderate/poor",
    "investment_fundamentals": "...",
    "key_findings": ["..."],
    "lifestyle_strengths": ["..."],
    "lifestyle_weaknesses": ["..."],
    "recommendations": ["..."],
    "confidence": "HIGH/MEDIUM/LOW",
    "evidence": [{{"feature": "...", "source": "...", "value": "..."}}]
}}
"""

# =============================================================================
# SYNTHESIS PROMPT (Feature-Grounded)
# =============================================================================

SYNTHESIS_PROMPT = """## Multi-Section Synthesis Task

You are synthesizing a comprehensive real estate analysis report.

### Original Query
{user_query}

### Pre-computed Features (Deterministic - VERIFIED)
{features_json}

### Section Analyses
{section_results}

### Evidence References
{evidence_map}

### Consistency Validation
{validation_result}

### Your Task
1. Produce a 5-line executive verdict (one-sentence recommendation)
2. Provide 3 supporting facts (MUST reference evidence from EVIDENCE section)
3. List top-3 risks and mitigation actions with cost ballpark if available
4. Provide confidence (HIGH/MEDIUM/LOW) and top-2 reasons for that confidence
5. Include livability assessment if extended analysis data is available
6. Output JSON with keys: verdict, facts, mitigations, confidence, evidence_refs

### CRITICAL RULES
- Do NOT invent numeric values - use only from FEATURES section
- Every fact must reference an evidence item
- If confidence is LOW, explain why
- Flag any data gaps clearly
- If contradictions were detected, explain how they were resolved

### Output Format (JSON)
{{
    "verdict": "...",
    "facts": [
        {{"statement": "...", "evidence": "...", "source": "..."}}
    ],
    "mitigations": [
        {{"risk": "...", "action": "...", "cost_estimate": "..."}}
    ],
    "confidence": "HIGH/MEDIUM/LOW",
    "confidence_reasons": ["...", "..."],
    "data_gaps": ["..."],
    "evidence_refs": [...]
}}
"""


# =============================================================================
# SECTION MAPPING
# =============================================================================

# Maps section names to their prompt templates
SECTION_PROMPT_MAP = {
    "terrain": TERRAIN_ANALYSIS_PROMPT,
    "infrastructure": INFRASTRUCTURE_ANALYSIS_PROMPT,
    "market": MARKET_ANALYSIS_PROMPT,
    "urban_form": URBAN_FORM_ANALYSIS_PROMPT,
    "risk": RISK_ANALYSIS_PROMPT,
    "extended": EXTENDED_ANALYSIS_PROMPT,
}


def get_section_prompt(section_name: str) -> str:
    """Get the prompt template for a given section."""
    return SECTION_PROMPT_MAP.get(section_name, "")


def format_section_prompt(
    section_name: str,
    lat: float,
    lng: float,
    features: dict,
    data_sources: list = None,
    data_gaps: list = None
) -> str:
    """
    Format a section prompt with actual feature values.

    Args:
        section_name: Name of the section (terrain, market, etc.)
        lat: Latitude
        lng: Longitude
        features: Dict of feature name -> value
        data_sources: List of data source strings
        data_gaps: List of data gap strings

    Returns:
        Formatted prompt string ready for LLM
    """
    template = get_section_prompt(section_name)
    if not template:
        return ""

    # Build format kwargs
    kwargs = {
        "lat": lat,
        "lng": lng,
        "data_sources": "\n".join(f"- {s}" for s in (data_sources or [])) or "N/A",
        "data_gaps": "\n".join(f"- {g}" for g in (data_gaps or [])) or "None",
    }

    # Add all features, using "N/A" for missing values
    for key, value in features.items():
        if value is None:
            kwargs[key] = "N/A"
        elif isinstance(value, list):
            kwargs[key] = ", ".join(str(v) for v in value) if value else "N/A"
        elif isinstance(value, dict):
            kwargs[key] = str(value)
        else:
            kwargs[key] = str(value)

    # Fill in any missing template variables with "N/A"
    import re
    placeholders = re.findall(r'\{(\w+)\}', template)
    for ph in placeholders:
        if ph not in kwargs:
            kwargs[ph] = "N/A"

    try:
        return template.format(**kwargs)
    except KeyError as e:
        return template  # Return unformatted if there's a key error


def format_synthesis_prompt(
    user_query: str,
    features_json: str,
    section_results: str,
    evidence_map: str,
    validation_result: str = "All sections consistent"
) -> str:
    """
    Format the synthesis prompt with all section data.

    Args:
        user_query: Original user query
        features_json: JSON string of all pre-computed features
        section_results: JSON string of all section analysis results
        evidence_map: JSON string of evidence references
        validation_result: Consistency validation summary

    Returns:
        Formatted synthesis prompt
    """
    return SYNTHESIS_PROMPT.format(
        user_query=user_query,
        features_json=features_json,
        section_results=section_results,
        evidence_map=evidence_map,
        validation_result=validation_result
    )
