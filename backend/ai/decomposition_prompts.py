"""
Decomposition Prompts - LLM Prompts for Task Decomposition
Contains prompt templates for extracting tasks from natural language queries.
Based on QUERIES_LIST.md - comprehensive query test suite for Valora.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class DecompositionPrompt:
    """A prompt template for task decomposition"""
    name: str
    system_prompt: str
    user_prompt_template: str
    examples: List[Dict[str, Any]] = field(default_factory=list)


# System prompt for task decomposition
DECOMPOSITION_SYSTEM_PROMPT = """You are an expert task decomposition system for a real estate intelligence platform called Valora.

Your role is to analyze user queries and break them down into atomic, executable tasks that provide professional, informative feedback.

## Query Categories (from QUERIES_LIST.md)

### 1. Navigation & Location Queries
- Basic: "Go to Indiranagar", "Take me to Hebbal", "Fly to MG Road"
- Landmark: "Show me Bangalore Palace", "Navigate to Cubbon Park"
- Area Exploration: "Explore Koramangala 4th Block"
- Coordinates: "Go to 12.9716, 77.5946"

### 2. Property Search Queries
- Basic: "Find 2BHK apartments in Whitefield"
- Filtered: "2BHK apartments in Whitefield under 80 lakhs"
- Nearby/Radius: "Properties within 1 km of Indiranagar"
- Investment: "Best investment properties in Bangalore"
- Amenity-driven: "Homes near good restaurants in Indiranagar"

### 3. Area Analysis Queries
- Comprehensive: "Analyze Koramangala for investment"
- POI Deep-dive: "What are the top amenities around Koramangala?"
- Risk & Livability: "Is Bellandur safe from flooding?"
- Comparative: "Compare Whitefield vs Electronic City"
- Demographic: "Best areas for families with kids"

### 4. Explainability Queries (Why? Tab)
- Investment: "Why should I invest in Koramangala?"
- Risk: "What are the risks of investing in Bellandur?"

### 5. Simulation Queries (What-If)
- Infrastructure: "What if a metro station opens near Sarjapur Road?"
- Policy: "What if FAR increases in Koramangala?"
- Development: "Simulate new IT park development in Devanahalli"
- Time-based: "Project property values in 5 years for Koramangala"

### 6. 3D Spatial Reasoning Queries
- Sky View: "What is the sky view factor at Koramangala?"
- Optimal Floor: "What's the best floor to buy in Whitefield?"
- Shadow: "How much shadow does this building get in the morning?"
- Building Context: "How many taller buildings are near this location?"

### 7. Digital Twin Queries
- Initialize: "Initialize digital twin for Koramangala"
- State: "What's the current digital twin state?"
- Update: "Update digital twin with new metro station"

### 8. Valuation Queries
- Estimate: "Estimate value of a 2BHK 1200 sqft in Koramangala"
- Compare: "Compare property values: Koramangala vs Indiranagar"
- Rental: "What rental yield can I expect in Koramangala?"

### 9. Terrain & Environmental Queries
- Elevation: "What's the elevation in Whitefield?"
- Flood Risk: "Is Bellandur flood-prone?"
- Terrain: "Terrain analysis of Sarjapur Road"

### 10. Market & Valuation Queries
- Price: "Average price per sqft in Koramangala"
- Trends: "Price trends in Whitefield last 5 years"
- Stats: "How many active listings are near Koramangala?"

### 11. Storytelling & Animation Queries
- Tours: "Give me a tour of Koramangala"
- Comparative: "Show me the difference between old and new Whitefield"

## Available Task Types

1. **map_action** - Visual operations on the map
   - flyTo: Navigate to a location with smooth animation
   - orbit: 360° view around a point
   - highlightBuilding: Focus on a building
   - drawRoute: Draw a route line
   - addLayer: Add analytics overlay
   - markProperties: Highlight properties
   - drawCircle: Draw radius/buffer zone

2. **gis_operation** - Spatial data operations
   - geocode: Convert location name to coordinates
   - spatialQuery: Search properties/POIs in area
   - areaMetrics: Calculate area statistics
   - routeAnalysis: Compute route between points
   - terrainAnalysis: Get elevation, slope, flood risk
   - skyViewAnalysis: Calculate sky view factor

3. **llm_call** - Language model operations
   - parse: Extract structured data from text
   - compare: Compare multiple entities
   - analyze: Generate insights from data
   - summarize: Create summary of results
   - explain: Generate reasoning/explainability
   - simulate: Run what-if scenarios

4. **data_fetch** - Data retrieval operations
   - getPropertyDetails: Fetch property information
   - getMarketData: Retrieve market statistics
   - getHistoricalData: Get historical trends
   - getPOIData: Get points of interest
   - getDigitalTwinState: Get simulation state

## Task Decomposition Rules

1. Each task should be atomic and focused on a single operation
2. Tasks should have clear dependencies on other tasks when needed
3. Extract all entities (locations, properties, areas) from the query
4. Assign confidence scores (0.0-1.0) based on extraction certainty
5. Preserve the original text span that generated each task
6. Generate human-readable labels for each task

## Output Format

Return a JSON object with this structure:
{
  "tasks": [
    {
      "id": "unique_task_id",
      "action": "action_name",
      "entity": "entity_type",
      "label": "Human readable task description",
      "task_type": "map_action|gis_operation|llm_call|data_fetch",
      "parameters": {...},
      "dependencies": ["task_id1", "task_id2"],
      "confidence": 0.95,
      "source_span": "original text that generated this task",
      "priority": 1
    }
  ],
  "overall_confidence": 0.92,
  "reasoning": "Brief explanation of decomposition decisions"
}

## Priority Levels
- 1 (HIGH): Critical path tasks, user-facing actions
- 2 (MEDIUM): Supporting tasks, data gathering
- 3 (LOW): Optional enhancements, visual polish

## Dependency Rules
- geocode must complete before flyTo
- flyTo must complete before orbit
- spatialQuery needs geocode or flyTo first
- compare needs metrics from both entities first
- markProperties needs query results first
- analyze needs data fetch tasks first
"""


# User prompt template
DECOMPOSITION_USER_TEMPLATE = """Decompose the following user query into executable tasks.

**User Query:** {query}

**Context:**
- Intent: {intent}
- Extracted Slots: {slots}
- Previous Context: {context}

**Available Tools:** {available_tools}

Return the decomposition as a JSON object following the specified format.
"""


# Few-shot examples for better decomposition - covering all query categories
DECOMPOSITION_EXAMPLES = [
    # Navigation Query
    {
        "query": "Go to Koramangala",
        "intent": "navigate",
        "slots": {"location": "Koramangala"},
        "expected_output": {
            "tasks": [
                {
                    "id": "t1_geocode",
                    "action": "geocode",
                    "entity": "location",
                    "label": "Locating Koramangala",
                    "task_type": "gis_operation",
                    "parameters": {"location": "Koramangala"},
                    "dependencies": [],
                    "confidence": 0.98,
                    "source_span": "Koramangala",
                    "priority": 1
                },
                {
                    "id": "t2_flyto",
                    "action": "flyTo",
                    "entity": "location",
                    "label": "Navigating to Koramangala",
                    "task_type": "map_action",
                    "parameters": {"location": "Koramangala", "zoom": 15},
                    "dependencies": ["t1_geocode"],
                    "confidence": 0.95,
                    "source_span": "Go to Koramangala",
                    "priority": 1
                }
            ],
            "overall_confidence": 0.96,
            "reasoning": "Simple navigation query requiring geocoding then flying to location."
        }
    },
    # Property Search Query
    {
        "query": "Show me 3BHK apartments under 1 crore in Koramangala",
        "intent": "property_search",
        "slots": {"bhk": "3BHK", "budget": "1 crore", "location": "Koramangala"},
        "expected_output": {
            "tasks": [
                {
                    "id": "t1_parse_filters",
                    "action": "parse",
                    "entity": "filters",
                    "label": "Parsing search criteria",
                    "task_type": "llm_call",
                    "parameters": {"bhk": "3BHK", "budget_max": 10000000},
                    "dependencies": [],
                    "confidence": 0.95,
                    "source_span": "3BHK apartments under 1 crore",
                    "priority": 1
                },
                {
                    "id": "t2_geocode",
                    "action": "geocode",
                    "entity": "location",
                    "label": "Locating Koramangala",
                    "task_type": "gis_operation",
                    "parameters": {"location": "Koramangala"},
                    "dependencies": [],
                    "confidence": 0.98,
                    "source_span": "Koramangala",
                    "priority": 1
                },
                {
                    "id": "t3_flyto",
                    "action": "flyTo",
                    "entity": "location",
                    "label": "Navigating to area",
                    "task_type": "map_action",
                    "parameters": {"location": "Koramangala", "zoom": 15},
                    "dependencies": ["t2_geocode"],
                    "confidence": 0.95,
                    "source_span": "in Koramangala",
                    "priority": 1
                },
                {
                    "id": "t4_query_properties",
                    "action": "spatialQuery",
                    "entity": "property",
                    "label": "Searching properties",
                    "task_type": "gis_operation",
                    "parameters": {
                        "location": "Koramangala",
                        "radius": 2000,
                        "filters": {"bhk": "3BHK", "budget_max": 10000000}
                    },
                    "dependencies": ["t1_parse_filters", "t2_geocode"],
                    "confidence": 0.92,
                    "source_span": "Show me 3BHK apartments under 1 crore in Koramangala",
                    "priority": 1
                },
                {
                    "id": "t5_mark_properties",
                    "action": "markProperties",
                    "entity": "property",
                    "label": "Displaying results",
                    "task_type": "map_action",
                    "parameters": {"filter": "query_results"},
                    "dependencies": ["t3_flyto", "t4_query_properties"],
                    "confidence": 0.90,
                    "source_span": "Show me",
                    "priority": 1
                }
            ],
            "overall_confidence": 0.94,
            "reasoning": "Property search requires parsing filters, geocoding location, navigating, searching, and displaying results."
        }
    },
    # Area Analysis Query
    {
        "query": "Analyze Koramangala for investment potential",
        "intent": "analyze_area",
        "slots": {"location": "Koramangala", "purpose": "investment"},
        "expected_output": {
            "tasks": [
                {
                    "id": "t1_geocode",
                    "action": "geocode",
                    "entity": "location",
                    "label": "Locating Koramangala",
                    "task_type": "gis_operation",
                    "parameters": {"location": "Koramangala"},
                    "dependencies": [],
                    "confidence": 0.98,
                    "source_span": "Koramangala",
                    "priority": 1
                },
                {
                    "id": "t2_flyto",
                    "action": "flyTo",
                    "entity": "location",
                    "label": "Navigating to area",
                    "task_type": "map_action",
                    "parameters": {"location": "Koramangala", "zoom": 15},
                    "dependencies": ["t1_geocode"],
                    "confidence": 0.95,
                    "source_span": "Koramangala",
                    "priority": 1
                },
                {
                    "id": "t3_area_metrics",
                    "action": "areaMetrics",
                    "entity": "area",
                    "label": "Calculating area metrics",
                    "task_type": "gis_operation",
                    "parameters": {
                        "location": "Koramangala",
                        "metrics": ["price_trend", "livability", "connectivity", "investment_potential"]
                    },
                    "dependencies": ["t1_geocode"],
                    "confidence": 0.95,
                    "source_span": "investment potential",
                    "priority": 1
                },
                {
                    "id": "t4_poi_data",
                    "action": "getPOIData",
                    "entity": "amenities",
                    "label": "Fetching nearby amenities",
                    "task_type": "data_fetch",
                    "parameters": {"location": "Koramangala", "radius": 1000},
                    "dependencies": ["t1_geocode"],
                    "confidence": 0.92,
                    "source_span": "Analyze Koramangala",
                    "priority": 2
                },
                {
                    "id": "t5_analyze",
                    "action": "analyze",
                    "entity": "investment",
                    "label": "Generating investment analysis",
                    "task_type": "llm_call",
                    "parameters": {
                        "location": "Koramangala",
                        "focus": "investment_potential"
                    },
                    "dependencies": ["t3_area_metrics", "t4_poi_data"],
                    "confidence": 0.90,
                    "source_span": "Analyze Koramangala for investment potential",
                    "priority": 2
                }
            ],
            "overall_confidence": 0.94,
            "reasoning": "Area analysis requires geocoding, navigation, metrics computation, POI data, and insight generation."
        }
    },
    # Comparison Query
    {
        "query": "Compare Whitefield and Electronic City for investment potential",
        "intent": "comparison",
        "slots": {"location_a": "Whitefield", "location_b": "Electronic City", "purpose": "investment"},
        "expected_output": {
            "tasks": [
                {
                    "id": "t1_geocode_a",
                    "action": "geocode",
                    "entity": "location_a",
                    "label": "Locating Whitefield",
                    "task_type": "gis_operation",
                    "parameters": {"location": "Whitefield"},
                    "dependencies": [],
                    "confidence": 0.98,
                    "source_span": "Whitefield",
                    "priority": 1
                },
                {
                    "id": "t2_geocode_b",
                    "action": "geocode",
                    "entity": "location_b",
                    "label": "Locating Electronic City",
                    "task_type": "gis_operation",
                    "parameters": {"location": "Electronic City"},
                    "dependencies": [],
                    "confidence": 0.98,
                    "source_span": "Electronic City",
                    "priority": 1
                },
                {
                    "id": "t3_metrics_a",
                    "action": "areaMetrics",
                    "entity": "area_a",
                    "label": "Analyzing Whitefield metrics",
                    "task_type": "gis_operation",
                    "parameters": {
                        "location": "Whitefield",
                        "metrics": ["price_trend", "livability", "connectivity", "investment_potential"]
                    },
                    "dependencies": ["t1_geocode_a"],
                    "confidence": 0.95,
                    "source_span": "Whitefield for investment",
                    "priority": 1
                },
                {
                    "id": "t4_metrics_b",
                    "action": "areaMetrics",
                    "entity": "area_b",
                    "label": "Analyzing Electronic City metrics",
                    "task_type": "gis_operation",
                    "parameters": {
                        "location": "Electronic City",
                        "metrics": ["price_trend", "livability", "connectivity", "investment_potential"]
                    },
                    "dependencies": ["t2_geocode_b"],
                    "confidence": 0.95,
                    "source_span": "Electronic City for investment",
                    "priority": 1
                },
                {
                    "id": "t5_compare",
                    "action": "compare",
                    "entity": "areas",
                    "label": "Comparing areas",
                    "task_type": "llm_call",
                    "parameters": {
                        "area_a": "Whitefield",
                        "area_b": "Electronic City",
                        "purpose": "investment"
                    },
                    "dependencies": ["t3_metrics_a", "t4_metrics_b"],
                    "confidence": 0.92,
                    "source_span": "Compare Whitefield and Electronic City for investment potential",
                    "priority": 2
                }
            ],
            "overall_confidence": 0.96,
            "reasoning": "Comparison requires parallel data gathering for both areas, then synthesis."
        }
    },
    # Simulation Query
    {
        "query": "What if a metro station opens near Sarjapur Road?",
        "intent": "simulation",
        "slots": {"infrastructure": "metro station", "location": "Sarjapur Road"},
        "expected_output": {
            "tasks": [
                {
                    "id": "t1_geocode",
                    "action": "geocode",
                    "entity": "location",
                    "label": "Locating Sarjapur Road",
                    "task_type": "gis_operation",
                    "parameters": {"location": "Sarjapur Road"},
                    "dependencies": [],
                    "confidence": 0.98,
                    "source_span": "Sarjapur Road",
                    "priority": 1
                },
                {
                    "id": "t2_flyto",
                    "action": "flyTo",
                    "entity": "location",
                    "label": "Navigating to area",
                    "task_type": "map_action",
                    "parameters": {"location": "Sarjapur Road", "zoom": 15},
                    "dependencies": ["t1_geocode"],
                    "confidence": 0.95,
                    "source_span": "Sarjapur Road",
                    "priority": 1
                },
                {
                    "id": "t3_baseline_metrics",
                    "action": "areaMetrics",
                    "entity": "area",
                    "label": "Getting baseline metrics",
                    "task_type": "gis_operation",
                    "parameters": {
                        "location": "Sarjapur Road",
                        "metrics": ["current_prices", "connectivity", "demand"]
                    },
                    "dependencies": ["t1_geocode"],
                    "confidence": 0.95,
                    "source_span": "Sarjapur Road",
                    "priority": 1
                },
                {
                    "id": "t4_simulate",
                    "action": "simulate",
                    "entity": "infrastructure",
                    "label": "Running metro impact simulation",
                    "task_type": "llm_call",
                    "parameters": {
                        "scenario": "metro_station",
                        "location": "Sarjapur Road",
                        "impact_areas": ["property_prices", "connectivity", "demand"]
                    },
                    "dependencies": ["t3_baseline_metrics"],
                    "confidence": 0.90,
                    "source_span": "What if a metro station opens near Sarjapur Road",
                    "priority": 2
                }
            ],
            "overall_confidence": 0.95,
            "reasoning": "Simulation requires baseline data then scenario modeling."
        }
    },
    # Valuation Query
    {
        "query": "Estimate value of a 2BHK 1200 sqft in Koramangala",
        "intent": "valuation",
        "slots": {"bhk": "2BHK", "area": "1200 sqft", "location": "Koramangala"},
        "expected_output": {
            "tasks": [
                {
                    "id": "t1_geocode",
                    "action": "geocode",
                    "entity": "location",
                    "label": "Locating Koramangala",
                    "task_type": "gis_operation",
                    "parameters": {"location": "Koramangala"},
                    "dependencies": [],
                    "confidence": 0.98,
                    "source_span": "Koramangala",
                    "priority": 1
                },
                {
                    "id": "t2_market_data",
                    "action": "getMarketData",
                    "entity": "market",
                    "label": "Fetching market data",
                    "task_type": "data_fetch",
                    "parameters": {"location": "Koramangala", "property_type": "2BHK"},
                    "dependencies": ["t1_geocode"],
                    "confidence": 0.95,
                    "source_span": "2BHK in Koramangala",
                    "priority": 1
                },
                {
                    "id": "t3_valuation",
                    "action": "analyze",
                    "entity": "valuation",
                    "label": "Calculating property value",
                    "task_type": "llm_call",
                    "parameters": {
                        "location": "Koramangala",
                        "bhk": "2BHK",
                        "area_sqft": 1200
                    },
                    "dependencies": ["t2_market_data"],
                    "confidence": 0.92,
                    "source_span": "Estimate value of a 2BHK 1200 sqft in Koramangala",
                    "priority": 2
                }
            ],
            "overall_confidence": 0.95,
            "reasoning": "Valuation requires location data, market data, then analysis."
        }
    },
    # Route Query
    {
        "query": "What's the route from Indiranagar to Whitefield?",
        "intent": "route_analysis",
        "slots": {"from_location": "Indiranagar", "to_location": "Whitefield"},
        "expected_output": {
            "tasks": [
                {
                    "id": "t1_geocode_from",
                    "action": "geocode",
                    "entity": "start",
                    "label": "Locating Indiranagar",
                    "task_type": "gis_operation",
                    "parameters": {"location": "Indiranagar"},
                    "dependencies": [],
                    "confidence": 0.98,
                    "source_span": "Indiranagar",
                    "priority": 1
                },
                {
                    "id": "t2_geocode_to",
                    "action": "geocode",
                    "entity": "end",
                    "label": "Locating Whitefield",
                    "task_type": "gis_operation",
                    "parameters": {"location": "Whitefield"},
                    "dependencies": [],
                    "confidence": 0.98,
                    "source_span": "Whitefield",
                    "priority": 1
                },
                {
                    "id": "t3_route",
                    "action": "routeAnalysis",
                    "entity": "route",
                    "label": "Computing route",
                    "task_type": "gis_operation",
                    "parameters": {
                        "from": "Indiranagar",
                        "to": "Whitefield",
                        "mode": "driving"
                    },
                    "dependencies": ["t1_geocode_from", "t2_geocode_to"],
                    "confidence": 0.95,
                    "source_span": "route from Indiranagar to Whitefield",
                    "priority": 1
                },
                {
                    "id": "t4_draw_route",
                    "action": "drawRoute",
                    "entity": "route",
                    "label": "Displaying route on map",
                    "task_type": "map_action",
                    "parameters": {
                        "from": "Indiranagar",
                        "to": "Whitefield"
                    },
                    "dependencies": ["t3_route"],
                    "confidence": 0.92,
                    "source_span": "What's the route",
                    "priority": 1
                }
            ],
            "overall_confidence": 0.96,
            "reasoning": "Route analysis requires geocoding both endpoints, computing route, then visualizing."
        }
    },
    # Flood Risk Query
    {
        "query": "Is Bellandur flood-prone?",
        "intent": "risk_assessment",
        "slots": {"location": "Bellandur", "risk_type": "flood"},
        "expected_output": {
            "tasks": [
                {
                    "id": "t1_geocode",
                    "action": "geocode",
                    "entity": "location",
                    "label": "Locating Bellandur",
                    "task_type": "gis_operation",
                    "parameters": {"location": "Bellandur"},
                    "dependencies": [],
                    "confidence": 0.98,
                    "source_span": "Bellandur",
                    "priority": 1
                },
                {
                    "id": "t2_terrain",
                    "action": "terrainAnalysis",
                    "entity": "terrain",
                    "label": "Analyzing terrain",
                    "task_type": "gis_operation",
                    "parameters": {
                        "location": "Bellandur",
                        "metrics": ["elevation", "slope", "drainage"]
                    },
                    "dependencies": ["t1_geocode"],
                    "confidence": 0.95,
                    "source_span": "flood-prone",
                    "priority": 1
                },
                {
                    "id": "t3_risk_analysis",
                    "action": "analyze",
                    "entity": "risk",
                    "label": "Assessing flood risk",
                    "task_type": "llm_call",
                    "parameters": {
                        "location": "Bellandur",
                        "risk_type": "flood"
                    },
                    "dependencies": ["t2_terrain"],
                    "confidence": 0.92,
                    "source_span": "Is Bellandur flood-prone",
                    "priority": 2
                }
            ],
            "overall_confidence": 0.95,
            "reasoning": "Risk assessment requires location, terrain analysis, then risk evaluation."
        }
    },
    # Radius Search Query
    {
        "query": "Properties within 1 km of Indiranagar",
        "intent": "radius_search",
        "slots": {"location": "Indiranagar", "radius": "1 km"},
        "expected_output": {
            "tasks": [
                {
                    "id": "t1_geocode",
                    "action": "geocode",
                    "entity": "location",
                    "label": "Locating Indiranagar",
                    "task_type": "gis_operation",
                    "parameters": {"location": "Indiranagar"},
                    "dependencies": [],
                    "confidence": 0.98,
                    "source_span": "Indiranagar",
                    "priority": 1
                },
                {
                    "id": "t2_flyto",
                    "action": "flyTo",
                    "entity": "location",
                    "label": "Navigating to area",
                    "task_type": "map_action",
                    "parameters": {"location": "Indiranagar", "zoom": 14},
                    "dependencies": ["t1_geocode"],
                    "confidence": 0.95,
                    "source_span": "Indiranagar",
                    "priority": 1
                },
                {
                    "id": "t3_draw_circle",
                    "action": "drawCircle",
                    "entity": "radius",
                    "label": "Drawing search radius",
                    "task_type": "map_action",
                    "parameters": {"center": "Indiranagar", "radius": 1000},
                    "dependencies": ["t1_geocode"],
                    "confidence": 0.95,
                    "source_span": "within 1 km",
                    "priority": 1
                },
                {
                    "id": "t4_query",
                    "action": "spatialQuery",
                    "entity": "property",
                    "label": "Searching properties in radius",
                    "task_type": "gis_operation",
                    "parameters": {
                        "location": "Indiranagar",
                        "radius": 1000
                    },
                    "dependencies": ["t1_geocode"],
                    "confidence": 0.92,
                    "source_span": "Properties within 1 km of Indiranagar",
                    "priority": 1
                },
                {
                    "id": "t5_mark",
                    "action": "markProperties",
                    "entity": "property",
                    "label": "Displaying results",
                    "task_type": "map_action",
                    "parameters": {"filter": "radius_results"},
                    "dependencies": ["t2_flyto", "t3_draw_circle", "t4_query"],
                    "confidence": 0.90,
                    "source_span": "Properties",
                    "priority": 1
                }
            ],
            "overall_confidence": 0.94,
            "reasoning": "Radius search requires geocoding, drawing circle, querying, and displaying results."
        }
    },
    # 3D Spatial Query
    {
        "query": "What's the sky view factor at Koramangala?",
        "intent": "spatial_3d",
        "slots": {"location": "Koramangala", "metric": "sky_view_factor"},
        "expected_output": {
            "tasks": [
                {
                    "id": "t1_geocode",
                    "action": "geocode",
                    "entity": "location",
                    "label": "Locating Koramangala",
                    "task_type": "gis_operation",
                    "parameters": {"location": "Koramangala"},
                    "dependencies": [],
                    "confidence": 0.98,
                    "source_span": "Koramangala",
                    "priority": 1
                },
                {
                    "id": "t2_sky_view",
                    "action": "skyViewAnalysis",
                    "entity": "spatial_3d",
                    "label": "Calculating sky view factor",
                    "task_type": "gis_operation",
                    "parameters": {"location": "Koramangala"},
                    "dependencies": ["t1_geocode"],
                    "confidence": 0.95,
                    "source_span": "sky view factor",
                    "priority": 1
                },
                {
                    "id": "t3_analyze",
                    "action": "analyze",
                    "entity": "spatial_3d",
                    "label": "Analyzing view quality",
                    "task_type": "llm_call",
                    "parameters": {
                        "location": "Koramangala",
                        "focus": "sky_view"
                    },
                    "dependencies": ["t2_sky_view"],
                    "confidence": 0.90,
                    "source_span": "What's the sky view factor at Koramangala",
                    "priority": 2
                }
            ],
            "overall_confidence": 0.94,
            "reasoning": "3D spatial analysis requires location then specialized analysis."
        }
    }
]


# Tool capability mapping
TOOL_CAPABILITIES = {
    "map_action": {
        "flyTo": {
            "description": "Navigate map to a location with smooth animation",
            "required_params": ["location"],
            "optional_params": ["zoom", "duration"]
        },
        "orbit": {
            "description": "360° orbit around a point",
            "required_params": ["center"],
            "optional_params": ["duration"]
        },
        "highlightBuilding": {
            "description": "Highlight a specific building",
            "required_params": ["building_id"],
            "optional_params": ["color", "duration"]
        },
        "drawRoute": {
            "description": "Draw a route on the map",
            "required_params": ["from", "to"],
            "optional_params": ["color", "width"]
        },
        "addLayer": {
            "description": "Add analytics overlay layer",
            "required_params": ["layer"],
            "optional_params": ["opacity", "style"]
        },
        "markProperties": {
            "description": "Highlight properties on map",
            "required_params": ["filter"],
            "optional_params": ["style", "cluster"]
        },
        "drawCircle": {
            "description": "Draw a circle/radius on the map",
            "required_params": ["center", "radius"],
            "optional_params": ["color", "fill", "opacity"]
        }
    },
    "gis_operation": {
        "geocode": {
            "description": "Convert location name to coordinates",
            "required_params": ["location"],
            "optional_params": []
        },
        "spatialQuery": {
            "description": "Search properties/POIs in an area",
            "required_params": ["location"],
            "optional_params": ["radius", "filters", "limit"]
        },
        "areaMetrics": {
            "description": "Calculate area statistics",
            "required_params": ["location"],
            "optional_params": ["metrics", "radius"]
        },
        "routeAnalysis": {
            "description": "Compute route between points",
            "required_params": ["from", "to"],
            "optional_params": ["mode", "alternatives"]
        },
        "terrainAnalysis": {
            "description": "Analyze terrain (elevation, slope, flood risk)",
            "required_params": ["location"],
            "optional_params": ["metrics"]
        },
        "skyViewAnalysis": {
            "description": "Calculate sky view factor for 3D context",
            "required_params": ["location"],
            "optional_params": ["radius"]
        }
    },
    "llm_call": {
        "parse": {
            "description": "Extract structured data from text",
            "required_params": ["text"],
            "optional_params": ["schema"]
        },
        "compare": {
            "description": "Compare multiple entities",
            "required_params": ["entities"],
            "optional_params": ["criteria"]
        },
        "analyze": {
            "description": "Generate insights from data",
            "required_params": ["focus"],
            "optional_params": ["location", "data"]
        },
        "summarize": {
            "description": "Create summary of results",
            "required_params": ["content"],
            "optional_params": ["format", "length"]
        },
        "explain": {
            "description": "Generate reasoning/explainability",
            "required_params": ["topic"],
            "optional_params": ["location", "factors"]
        },
        "simulate": {
            "description": "Run what-if scenario simulation",
            "required_params": ["scenario"],
            "optional_params": ["location", "parameters"]
        }
    },
    "data_fetch": {
        "getPropertyDetails": {
            "description": "Fetch property information",
            "required_params": ["property_id"],
            "optional_params": ["fields"]
        },
        "getMarketData": {
            "description": "Retrieve market statistics",
            "required_params": ["location"],
            "optional_params": ["property_type", "timeframe"]
        },
        "getHistoricalData": {
            "description": "Get historical trends",
            "required_params": ["location"],
            "optional_params": ["metric", "years"]
        },
        "getPOIData": {
            "description": "Get points of interest",
            "required_params": ["location"],
            "optional_params": ["radius", "categories"]
        },
        "getDigitalTwinState": {
            "description": "Get digital twin simulation state",
            "required_params": ["location"],
            "optional_params": []
        }
    }
}


def get_decomposition_prompt(query: str, intent: str, slots: Dict, context: Dict, available_tools: List[str]) -> str:
    """Generate a decomposition prompt for the given query"""
    return DECOMPOSITION_USER_TEMPLATE.format(
        query=query,
        intent=intent,
        slots=slots,
        context=context,
        available_tools=available_tools
    )


def get_relevant_examples(intent: str, limit: int = 2) -> List[Dict]:
    """Get relevant examples for the given intent"""
    intent_mapping = {
        "navigate": ["navigate"],
        "property_search": ["property_search", "radius_search"],
        "analyze_area": ["analyze_area"],
        "comparison": ["comparison"],
        "simulation": ["simulation"],
        "valuation": ["valuation"],
        "route_analysis": ["route_analysis"],
        "risk_assessment": ["risk_assessment"],
        "radius_search": ["radius_search"],
        "spatial_3d": ["spatial_3d"]
    }
    
    relevant_intents = intent_mapping.get(intent, ["navigate", "property_search"])
    
    examples = []
    for example in DECOMPOSITION_EXAMPLES:
        if example.get("intent") in relevant_intents:
            examples.append(example)
            if len(examples) >= limit:
                break
    
    return examples


# Alias for backward compatibility
format_decomposition_prompt = get_decomposition_prompt
get_example_for_intent = get_relevant_examples


def validate_decomposition_output(output: Dict) -> Tuple[bool, List[str]]:
    """
    Validate decomposition output structure.
    Returns (is_valid, list_of_errors).
    """
    errors = []
    
    if not isinstance(output, dict):
        return False, ["Output must be a dictionary"]
    
    if "tasks" not in output:
        return False, ["Output must contain 'tasks' key"]
    
    tasks = output.get("tasks", [])
    if not isinstance(tasks, list):
        errors.append("'tasks' must be a list")
    
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f"Task {i} must be a dictionary")
            continue
        
        if "action" not in task:
            errors.append(f"Task {i} missing 'action' field")
        
        if "id" not in task:
            errors.append(f"Task {i} missing 'id' field")
    
    return len(errors) == 0, errors
