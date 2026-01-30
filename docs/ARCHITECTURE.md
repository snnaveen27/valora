# Valora AI - Next-Gen 3D GIS Agent Architecture

**Vision: An AI that reasons about 3D urban space like humans do**

---

## Core Principle

> **Geometry + Simulation + Memory + Causal Models = True 3D Intelligence**  
> **The LLM is only the narrator and planner.**

The LLM never invents spatial facts. All 3D understanding comes from deterministic engines that compute geometry, visibility, relationships, and impacts. The LLM orchestrates these tools and narrates results.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VALORA NEXT-GEN 3D GIS AGENT                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LAYER 5: LLM ORCHESTRATOR (Narrator + Planner)                            │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  • Tool Selection: Which spatial tool to call?                        │ │
│  │  • Query Planning: Break complex queries into tool calls              │ │
│  │  • Narrative Synthesis: Convert facts to human-readable insights     │ │
│  │  • NEVER invents spatial facts - only uses tool outputs              │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    ▲                                        │
│                                    │ Tool Calls + Facts                     │
│                                    ▼                                        │
│  LAYER 4: SPATIAL TOOL REGISTRY                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  Offline Internal Tools (JSON Schema)                                 │ │
│  │  ├── get_3d_context(lat, lng, floor_height, radius)                  │ │
│  │  ├── find_buildings_blocking_view(from_lat, from_lng, to_lat, to_lng)│ │
│  │  ├── get_shadow_at_time(lat, lng, hour)                              │ │
│  │  ├── query_spatial_graph(relationship, entity_a, entity_b)           │ │
│  │  ├── simulate_infrastructure(type, location, params)                 │ │
│  │  ├── search_properties(filters, spatial_scope)                       │ │
│  │  ├── get_locality_profile(name)                                      │ │
│  │  └── ui_command(action, payload)                                     │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    ▲                                        │
│                                    │ Deterministic Computation              │
│                                    ▼                                        │
│  LAYER 3: 3D REASONING ENGINES                                             │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐           │
│  │ SPATIAL 3D       │ │ VIEWSHED         │ │ SHADOW           │           │
│  │ • Neighbors      │ │ • Ray casting    │ │ • Sun position   │           │
│  │ • Volumes        │ │ • Visibility     │ │ • Shadow length  │           │
│  │ • Sky view       │ │ • Landmarks      │ │ • Impact zones   │           │
│  │ • Skyline        │ │ • Floor compare  │ │ • Time of day    │           │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘           │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐           │
│  │ OCCLUSION        │ │ PATH 3D          │ │ SCENE UNDERSTAND │           │
│  │ • Line of sight  │ │ • 3D routing     │ │ • Urban character│           │
│  │ • Blocking query │ │ • Elevation      │ │ • Density class  │           │
│  │ • View corridors │ │ • Vertical access│ │ • Morphology     │           │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘           │
│                                    ▲                                        │
│                                    │ Spatial Relationships                  │
│                                    ▼                                        │
│  LAYER 2: SPATIAL MEMORY GRAPH                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  Entity Nodes:                                                        │ │
│  │  • Buildings (686K) with height, type, footprint                     │ │
│  │  • POIs (27K) with category, rating                                  │ │
│  │  • Transport (5K) with type, routes                                  │ │
│  │  • Localities (788) with profiles                                    │ │
│  │                                                                       │ │
│  │  Relationship Edges:                                                  │ │
│  │  • BLOCKS_VIEW(building_a, building_b, direction)                    │ │
│  │  • SHADOWS(building_a, building_b, time_range)                       │ │
│  │  • WITHIN_WALK(entity_a, entity_b, minutes)                          │ │
│  │  • OVERLOOKS(building, landmark)                                     │ │
│  │  • ADJACENT_TO(building_a, building_b)                               │ │
│  │  • IN_LOCALITY(building, locality)                                   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    ▲                                        │
│                                    │ Raw Geometry                           │
│                                    ▼                                        │
│  LAYER 1: 3D WORLD DATABASE                                                │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  SQLite + Spatial Indexes                                             │ │
│  │  • buildings: 686K with polygon_coords, height, centroid             │ │
│  │  • pois: 27K with lat/lng, category                                  │ │
│  │  • terrain: elevation grid, flood zones                              │ │
│  │  • roads: 335K segments                                              │ │
│  │  • properties: 42K listings                                          │ │
│  │                                                                       │ │
│  │  FAISS Vector Index (77K embeddings for semantic search)             │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Current State vs Target State

### ✅ Already Implemented (Layer 1-3 Partial)

| Component | File | Capabilities |
|-----------|------|--------------|
| **3D World DB** | `valora.db` | 686K buildings, 27K POIs, 335K roads |
| **Spatial 3D** | `spatial_3d_reasoning.py` | Neighbors, volumes, sky view, skyline |
| **Viewshed** | `viewshed_analyzer.py` | Ray casting, visibility, floor compare |
| **Building Analyzer** | `building_analyzer.py` | 3D analysis, view quality, rooftop |
| **Shadow** | `spatial_3d_reasoning.py` | Basic shadow impact (single time) |
| **Simulation** | `simulation_engine.py` | Causal graph, what-if scenarios |
| **Knowledge** | `locality_service.py` | 788 locality profiles |

### 🔶 Gaps to Fill (Layer 2-4)

| Gap | Impact | Effort |
|-----|--------|--------|
| **Spatial Memory Graph** | Enable relational queries ("buildings behind the mall") | Medium |
| **Occlusion Engine** | Answer "what blocks the lake view?" | Medium |
| **Tool Schema** | LLM-directed tool calling with validation | Low |
| **Temporal Shadow** | Shadow movement through day | Low |
| **Scene Understanding** | Urban morphology from viewport | Medium |
| **Spatial Language NLU** | Parse "near", "behind", "overlooking" | Medium |

---

## Target Capabilities

### Human-Like 3D Queries the Agent Should Handle

```
# Visibility Queries
"Which buildings block the lake view from this apartment?"
"Can I see Cubbon Park from floor 15?"
"What's visible from the rooftop?"

# Spatial Relationship Queries  
"Buildings behind Embassy Tech Park"
"Properties overlooking the metro line"
"Apartments facing east with morning sun"

# Comparative 3D Queries
"Compare floor 5 vs floor 15 for views"
"Which direction has the least shadow?"
"Best floor for natural light in this building"

# Temporal 3D Queries
"How does sunlight change through the day here?"
"Evening shadow impact from neighboring towers"
"Winter vs summer sun exposure"

# Complex Reasoning
"If a 40-floor tower is built next door, how does my view change?"
"Best 3BHK with lake view under 1.5 crore"
"Quiet apartments away from highway noise"
```

---

## Implementation Roadmap

### Phase 1: Tool Schema (1-2 days)

Create formal JSON schema for all spatial tools so LLM can call them reliably.

**File:** `backend/spatial_tools_schema.json`

```json
{
  "tools": [
    {
      "name": "get_3d_context",
      "description": "Analyze 3D spatial context at a location and floor height",
      "parameters": {
        "lat": {"type": "number", "required": true},
        "lng": {"type": "number", "required": true},
        "floor_height_m": {"type": "number", "default": 0},
        "radius_m": {"type": "number", "default": 200}
      },
      "returns": "Spatial3DAnalysis"
    },
    {
      "name": "find_view_blockers",
      "description": "Find buildings that block view from point A toward point B",
      "parameters": {
        "from_lat": {"type": "number", "required": true},
        "from_lng": {"type": "number", "required": true},
        "from_height_m": {"type": "number", "required": true},
        "toward_direction": {"type": "string", "enum": ["N","NE","E","SE","S","SW","W","NW"]},
        "max_distance_m": {"type": "number", "default": 500}
      },
      "returns": "List[BlockingBuilding]"
    },
    {
      "name": "get_shadow_timeline",
      "description": "Get shadow impact through the day at a location",
      "parameters": {
        "lat": {"type": "number", "required": true},
        "lng": {"type": "number", "required": true},
        "hours": {"type": "array", "items": {"type": "integer"}, "default": [8,10,12,14,16,18]}
      },
      "returns": "List[ShadowAnalysis]"
    },
    {
      "name": "query_spatial_relationship",
      "description": "Query spatial relationships between entities",
      "parameters": {
        "relationship": {"type": "string", "enum": ["BLOCKS_VIEW","SHADOWS","OVERLOOKS","ADJACENT_TO","WITHIN_WALK"]},
        "entity_type": {"type": "string", "enum": ["building","poi","locality","property"]},
        "reference_lat": {"type": "number"},
        "reference_lng": {"type": "number"},
        "filter": {"type": "object"}
      },
      "returns": "List[RelatedEntity]"
    },
    {
      "name": "compare_floors",
      "description": "Compare view quality across multiple floors",
      "parameters": {
        "lat": {"type": "number", "required": true},
        "lng": {"type": "number", "required": true},
        "floors": {"type": "array", "items": {"type": "integer"}, "default": [1,5,10,15]}
      },
      "returns": "FloorComparison"
    },
    {
      "name": "simulate_new_building",
      "description": "Simulate impact of a new building on surroundings",
      "parameters": {
        "lat": {"type": "number", "required": true},
        "lng": {"type": "number", "required": true},
        "height_m": {"type": "number", "required": true},
        "footprint_m2": {"type": "number", "default": 500}
      },
      "returns": "SimulationImpact"
    }
  ]
}
```

### Phase 2: Spatial Memory Graph (3-5 days)

Create a graph layer that precomputes and caches spatial relationships.

**File:** `backend/spatial_memory_graph.py`

```python
# Core relationships to precompute
RELATIONSHIPS = [
    "BLOCKS_VIEW",      # building A blocks view from building B in direction D
    "SHADOWS",          # building A casts shadow on building B at time T
    "OVERLOOKS",        # building A has view of landmark L
    "ADJACENT_TO",      # building A is within 50m of building B
    "WITHIN_WALK",      # entity A is within N minutes walk of entity B
    "IN_LOCALITY",      # building A is in locality L
]

# Graph can be:
# - NetworkX (in-memory, simple)
# - SQLite with relationship table (persistent, queryable)
# - Neo4j (future, for complex traversals)
```

### Phase 3: Occlusion Engine (2-3 days)

Add true line-of-sight and view corridor analysis.

**File:** `backend/occlusion_engine.py`

```python
class OcclusionEngine:
    def find_blockers(self, from_point, toward_direction, observer_height):
        """Find all buildings that block view in a direction."""
        pass
    
    def get_view_corridor(self, from_point, to_landmark, observer_height):
        """Get the corridor of buildings between observer and landmark."""
        pass
    
    def can_see(self, from_point, from_height, to_point, to_height):
        """Check if line of sight exists between two 3D points."""
        pass
```

### Phase 4: Strengthen System Prompts (1 day)

Add explicit grounding rules to prevent LLM hallucination.

**Add to `backend/response_templates.py`:**

```python
SYSTEM_CONSTITUTION = """
# VALORA AI AGENT RULES

## CORE CONSTRAINTS
1. OFFLINE ONLY - Never mention or use external APIs, websites, or online data
2. GROUNDED FACTS ONLY - Only use data from the [FACTS] block below
3. NO INVENTION - If data is missing, say "I don't have data for X" 
4. CONFIDENCE - Always state confidence level (high/medium/low)

## OUTPUT FORMAT
- Use short bullet points
- Include specific numbers from facts
- State assumptions explicitly
- End with actionable next step

## SPATIAL REASONING
- All 3D facts come from spatial tools, never invent heights/views/shadows
- When comparing floors, use compare_floors tool output
- For visibility queries, use viewshed tool output
"""
```

### Phase 5: Spatial Language Understanding (3-5 days)

Parse natural language spatial references.

**File:** `backend/spatial_nlp.py` (enhance existing)

```python
SPATIAL_PATTERNS = {
    "behind": {"relationship": "OPPOSITE_DIRECTION", "reference": True},
    "in front of": {"relationship": "SAME_DIRECTION", "reference": True},
    "overlooking": {"relationship": "OVERLOOKS", "requires_height": True},
    "near": {"relationship": "WITHIN_WALK", "default_minutes": 10},
    "facing": {"relationship": "VIEW_DIRECTION", "requires_direction": True},
    "between": {"relationship": "CORRIDOR", "requires_two_refs": True},
}
```

---

## Data Flow: Example Query

**Query:** "Which buildings block the lake view from this apartment on floor 10?"

```
1. Intent Router → SPATIAL_QUERY (view blocker)

2. LLM Planner selects tools:
   - get_3d_context(lat, lng, floor_height=30)
   - find_view_blockers(lat, lng, height=30, toward="lake_direction")

3. Spatial 3D Engine executes:
   - Gets buildings in 500m radius
   - Calculates line-of-sight to lake
   - Returns: [Building_A (height=45m, dist=80m), Building_B (height=38m, dist=150m)]

4. LLM Narrator synthesizes:
   "Two buildings partially block the lake view from floor 10:
    - Building A (45m tall, 80m away) blocks ~40% of lake view
    - Building B (38m tall, 150m away) blocks ~15%
    Recommendation: Floor 15+ would have unobstructed lake views."

5. UI Actions:
   - Highlight blocking buildings in red on 3D map
   - Draw view corridor overlay
```

---

## Key Metrics

| Metric | Current | Target |
|--------|---------|--------|
| 3D Query Types Supported | 5 | 15 |
| Spatial Relationships | 0 (computed on-demand) | 6 precomputed |
| Tool Schema Coverage | 0% | 100% |
| Avg 3D Query Response | 1-2s | <500ms (with graph) |
| LLM Hallucination Rate | ~5% | <1% (with grounding) |

---

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| CREATE | `backend/spatial_tools_schema.json` | Formal tool definitions |
| CREATE | `backend/spatial_memory_graph.py` | Relationship graph |
| CREATE | `backend/occlusion_engine.py` | Line-of-sight queries |
| MODIFY | `backend/response_templates.py` | Add system constitution |
| MODIFY | `backend/spatial_nlp.py` | Spatial language patterns |
| MODIFY | `backend/gis_agents.py` | Tool-calling integration |

---

## Summary

Valora already has strong 3D reasoning primitives. The next-gen upgrade is about:

1. **Formalizing tools** → LLM reliably calls spatial functions
2. **Caching relationships** → Fast graph queries for "behind", "blocking", "overlooking"
3. **Stronger grounding** → LLM never invents spatial facts
4. **Richer queries** → "Which buildings block the lake view?" becomes answerable

This architecture makes Valora a **true 3D reasoning agent** that understands urban space like humans do—not just lat/lng, but height, visibility, shadows, and spatial relationships.
