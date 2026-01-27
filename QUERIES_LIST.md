# Valora AI - Complete Query Test Suite

Comprehensive test prompts covering all platform capabilities. Use these to validate the AI-driven panel orchestration, explainability, and storytelling features.

---

## 🎯 Quick Start Tests

| Query | Expected Behavior |
|-------|-------------------|
| "Analyze Koramangala" | Chat: Area insights, Analysis: Market data + Why? tab updates, Map: Flies to location |
| "Show me properties in Whitefield under 80 lakhs" | Chat: Property list, Analysis: Listings, Map: Highlights properties |
| "What if a metro opens near Sarjapur?" | Chat: Impact analysis, Analysis: Simulation results, Map: Storytelling animation |

---

## 📍 Navigation & Location Queries

### Basic Navigation
```
Go to Indiranagar
Take me to Hebbal
Navigate to Electronic City
Fly to MG Road
Where is Jayanagar?
```

**Expected:**
- Map flies to location with orbit animation
- Analysis panel updates with area context
- Chat shows brief location insights

### Landmark Navigation
```
Show me Bangalore Palace

Go to Cubbon Park
Navigate to Vidhana Soudha
Where is Lalbagh Garden?
```

### Area Exploration
```
Explore Koramangala 4th Block
Show me HSR Sector 7
Take me to JP Nagar Phase 6
```

### Coordinate Navigation
```
Go to 12.9716, 77.5946
Fly to 12.9352 77.6245
Navigate to coordinates 12.8456,77.6603
```

**Expected:**
- Map flies to exact coordinates
- Chat confirms lat/lng and provides nearby area name if available
- Facts include `lat`/`lng`

### Disambiguation & Spelling Robustness
```
Go to Koramangla
Navigate to Indira Nagar
Take me to Sarjapura Road
Go to Malleshwaram
Take me to Mahadevpura
```

**Expected:**
- Correct best-match geocode (with safe fallback / clarification if uncertain)
- Map flyTo + Insights refresh

---

## 🏠 Property Search Queries

### Basic Search
```
Find 2BHK apartments in Whitefield
Show me 3BHK flats in Indiranagar
Properties in Koramangala
Apartments near MG Road metro
```

**Expected:**
- Chat: Property listings with details
- Analysis: Property cards with "Ask about this" buttons
- Map: Property markers highlighted

### Filtered Search
```
2BHK apartments in Whitefield under 80 lakhs
3BHK with parking in HSR Layout
Properties with gym in Sarjapur Road
Gated community apartments in Electronic City
New construction in Hebbal
```

### Nearby / Radius Search
```
Properties within 1 km of Indiranagar
Apartments near Sarjapur Road (within 2 km)
Show properties near 12.9716, 77.5946 within 1500 meters
Find homes near metro within 800m in MG Road
```

**Expected:**
- Chat lists results and clearly states radius used
- Map highlights/marks results
- If no results, show graceful “0 results” with suggestions (expand radius / change filters)

### Conflicting / Strict Filters (Robustness)
```
2BHK under 10 lakhs in Indiranagar
5BHK under 50 lakhs in Koramangala
Studio apartment with 4 bathrooms
Properties under 30 lakhs with 5000 sqft covered area
```

**Expected:**
- No crash
- Chat explains constraints are too strict / unrealistic and suggests alternatives

### Investment-Focused
```
Best investment properties in Bangalore
High appreciation areas for buying
Properties with rental yield potential
Affordable areas with growth potential
```

### Amenity-Driven Search (POI constraints)
```
Homes near good restaurants in Indiranagar
Properties near parks in Jayanagar
Apartments near hospitals in Hebbal
Homes near tech parks in Whitefield
```

**Expected:**
- Chat describes nearby amenity evidence used (POIs/transport counts)
- Why? tab shows the factors used when applicable

---

## 📊 Area Analysis Queries

### Comprehensive Analysis
```
Analyze Koramangala for investment
Tell me about Whitefield market trends
What's the walkability score of Indiranagar?
How is the connectivity in HSR Layout?
```

### POI / Amenity Deep-Dive
```
What are the top amenities around Koramangala?
How many POIs are near Indiranagar?
Show nearby transport options around Hebbal
Nearest metro and bus stops near MG Road
```

**Expected:**
- Chat references POI/transport counts and nearest items
- Facts include relevant counts (POIs/transport)

### Micro-Risk & Livability
```
Is Bellandur safe from flooding?
What are the key risks in Silk Board area?
Which areas have low flood risk and good connectivity?
```

**Expected:**
- Chat provides risk summary and mitigation suggestions
- Why? tab risk meters populated when available

**Expected:**
- Chat: Detailed analysis with recommendations
- Analysis: Market overview, accessibility scores
- Why? Tab: SHAP-style feature bars, confidence gauge
- Locality Card: Inline in chat with Explore/Ask buttons

### Comparative Analysis
```
Compare Whitefield vs Electronic City
Which is better: Koramangala or Indiranagar?
Sarjapur vs Marathahalli for families
HSR Layout vs BTM Layout for IT professionals
```

**Expected:**
- Chat: Side-by-side comparison
- Analysis: Both areas' metrics
- Map: May show both locations

### Demographic-Specific
```
Best areas for families with kids
IT professional-friendly neighborhoods
Senior-friendly localities in Bangalore
Pet-friendly apartments in South Bangalore
```

### Follow-up Within Same Area (Context Carry)
```
Analyze Koramangala
What are the transport options there?
How is the flood risk?
Now compare it with Indiranagar
```

**Expected:**
- Follow-ups reuse the last selected location without forcing the user to repeat it
- Map/Insights stay aligned to the same location unless user switches

---

## 🧠 Explainability Queries (Why? Tab)

### Investment Reasoning
```
Why should I invest in Koramangala?
What makes Whitefield a good investment?
Why is Electronic City popular for IT buyers?
Explain the risks of buying in Sarjapur Road
```

**Expected:**
- Chat: Detailed reasoning
- Why? Tab: 
  - Feature impact bars (positive/negative)
  - Confidence gauge
  - Reasoning chain
  - Risk breakdown

### Risk Assessment
```
What are the risks of investing in Bellandur?
Is Mahadevapura flood-prone?
Infrastructure risks in Sarjapur
Traffic concerns in Silk Board area
```

**Expected:**
- Why? Tab: Risk meters, caution factors
- Chat: Risk analysis with mitigation suggestions

---

## 🔮 Simulation Queries (What-If)

### Infrastructure Scenarios
```
What if a metro station opens near Sarjapur Road?
Simulate impact of Peripheral Ring Road on Whitefield
What if a new IT park comes to Devanahalli?
Impact of airport expansion on Hebbal prices
```

**Expected:**
- Chat: Causal impact analysis
- Analysis: Simulation panel with % changes
- Map: **Storytelling animation** showing the scenario
- Narration overlay during playback

### Policy Scenarios
```
What if zoning changes in Koramangala allow high-rises?
Simulate population growth impact on infrastructure
What if water supply improves in Sarjapur?
Impact of new schools opening in HSR Layout
```

### Market Scenarios
```
What if IT companies expand in Whitefield?
Simulate rental demand increase in Marathahalli
What if land prices double in Yelahanka?
```

---

## � 3D Spatial Reasoning Queries

### Sky View & Openness Analysis
```
What is the sky view factor at Koramangala?
How open is the view from a 10th floor apartment in Indiranagar?
Analyze vertical openness at 12.9716, 77.5946
Which directions have clear views from this building?
```

**Expected:**
- Facts include `sky_view_factor` (0-1 range)
- Facts include `open_view_directions` (list of directions like N, NE, E, etc.)
- Chat describes view quality and openness

### Optimal Floor Recommendation
```
What's the best floor to buy in Whitefield for good views?
Recommend optimal floor for a building at this location
Which floor has the best sky view factor here?
Find the ideal floor level for maximum sunlight
```

**Expected:**
- Facts include `optimal_floor` with recommended floor number
- Chat explains reasoning (taller neighbors, shadow analysis)
- Why? tab shows floor optimization factors

### Shadow Analysis
```
How much shadow does this building get in the morning?
Shadow impact analysis for 10 AM at Koramangala
Will this apartment get good sunlight?
Analyze shadow patterns at this location
```

**Expected:**
- Facts include `shadow_analysis` with hour-based shadow data
- Chat describes shadow impact and sunlight availability
- Map may show shadow visualization if supported

### Skyline Character
```
What's the skyline character of Whitefield?
Describe the urban density around this location
Is this area high-rise or low-rise dominated?
Analyze building heights in 200m radius
```

**Expected:**
- Facts include `skyline_character` (e.g., "high-rise", "mixed", "low-rise")
- Facts include `spatial_3d_analysis` with building counts above/below
- Chat provides urban density context

### 3D Building Context
```
How many taller buildings are near this location?
What's the average building height around Indiranagar?
Analyze vertical urban context at this point
Show me the 3D density score for this area
```

**Expected:**
- Facts include `spatial_3d_analysis` with `buildings_above`, `buildings_below`, `avg_height`, `max_height`, `density_score`
- Chat summarizes the 3D urban environment

---

## 🏙️ Digital Twin Queries

### Digital Twin Initialization
```
Initialize digital twin for Koramangala
Create a city simulation model for Whitefield
Start digital twin at 12.9716, 77.5946
Load digital twin state for this area
```

**Expected:**
- Digital twin state returned in response
- State includes location, timestamp, metrics
- Chat confirms initialization

### Digital Twin State Queries
```
What's the current digital twin state?
Show me the city model metrics
Get digital twin population and building count
What does the simulation model say about this area?
```

**Expected:**
- Response includes `digital_twin_state` with metrics
- Metrics include: building_count, population_estimate, avg_property_price, infrastructure_score
- Chat summarizes current state

### Digital Twin Updates
```
Update digital twin with new metro station at Sarjapur
Add a school to the digital twin simulation
Modify the city model to include new infrastructure
Simulate adding 500 residential units to this area
```

**Expected:**
- Digital twin state updates with changes
- Response shows before/after comparison
- Chat explains impact of changes

### Digital Twin History
```
Show digital twin change history
What changes have been simulated?
List all modifications to the city model
Get simulation history for this session
```

**Expected:**
- Returns list of state changes with timestamps
- Each entry shows what was modified
- Chat summarizes simulation history

---

## 💰 Dynamic Valuation Queries

### Property Value Estimation
```
Estimate value of a 2BHK 1200 sqft in Koramangala
What's the price for 3BHK 1800 sqft in Whitefield?
Valuation for 1500 sqft apartment in Indiranagar
How much is a 4BHK villa worth in HSR Layout?
```

**Expected:**
- Facts include `estimated_value` with price
- Response includes confidence range (±15-30%)
- Chat explains valuation factors
- Why? tab shows price drivers

### Comparative Valuation
```
Compare property values: Koramangala vs Indiranagar for 2BHK
Which area offers better value for 80 lakhs budget?
Price difference between Whitefield and Electronic City
Value comparison for same property type across areas
```

**Expected:**
- Side-by-side valuation comparison
- Price per sqft comparison
- Chat explains value drivers for each area

### Valuation Factors
```
What factors affect property prices in Koramangala?
Why is Indiranagar more expensive than Marathahalli?
Explain the valuation model for this property
What's driving prices up in Whitefield?
```

**Expected:**
- Facts include valuation breakdown
- Response lists key factors: location, connectivity, amenities, demand
- Why? tab shows feature importance bars

### Market-Adjusted Valuation
```
Fair market value for 2BHK in current market conditions
Is 1.5 crore overpriced for this property?
What's a reasonable offer for this listing?
Market-adjusted price estimate for 1000 sqft in Sarjapur
```

**Expected:**
- Valuation considers current market trends
- Response includes `price_trend_pct` context
- Chat provides negotiation guidance

### Rental Yield Estimation
```
What rental yield can I expect in Koramangala?
Estimate monthly rent for 2BHK in Whitefield
ROI analysis for investment property in HSR
Rental income potential for this property
```

**Expected:**
- Estimated rental value
- Yield percentage calculation
- Comparison with area averages

---

## 🔮 Advanced Simulation Queries

### Infrastructure Impact Simulation
```
Simulate metro station impact on Sarjapur Road property prices
What if Peripheral Ring Road opens near Whitefield?
Impact of new flyover on Electronic City connectivity
Simulate highway expansion effect on Hebbal
```

**Expected:**
- Causal analysis with impact percentages
- Response includes `simulation` data
- Map shows storytelling animation
- Chat explains cause-effect chain

### Zoning & Policy Simulation
```
What if FAR increases in Koramangala?
Simulate commercial zoning change in Indiranagar
Impact of height restriction removal in CBD
What if parking requirements change for new buildings?
```

**Expected:**
- Policy impact analysis
- Price and density projections
- Chat explains regulatory implications

### Development Scenario Simulation
```
Simulate new IT park development in Devanahalli
What if 1000 new apartments are built in Sarjapur?
Impact of new shopping mall on local property values
Simulate mixed-use development near metro station
```

**Expected:**
- Development impact on prices, traffic, amenities
- Population and infrastructure strain analysis
- Chat provides development feasibility insights

### Multi-Factor Simulation
```
Simulate metro + IT park + residential development in Whitefield
What if both water supply and roads improve in Sarjapur?
Combined impact of school + hospital + park on property values
Simulate complete infrastructure upgrade for this area
```

**Expected:**
- Combined effect analysis
- Synergy or conflict identification
- Comprehensive impact summary

### Time-Based Projection
```
Project property values in 5 years for Koramangala
What will prices be after metro completion in 2027?
Long-term appreciation forecast for Whitefield
3-year investment outlook for HSR Layout
```

**Expected:**
- Time-series projection
- Confidence intervals
- Key assumptions stated

---

## �🏗️ Building Analysis Queries

### Click-Based Analysis
1. Click on any building on the map
2. **Expected:**
   - Map: 360° orbit around building
   - Analysis: Building details (height, type, levels)
   - Chat: Automatic building insights

### Query-Based
```
Analyze this building
Tell me about the selected building
What type of building is this?
Height and floor count of this building
```

### Building Context Follow-ups
```
Analyze this building
Is this building in a flood-prone zone?
What are the nearest POIs from this building?
Estimate the property value for a 2BHK here
```

**Expected:**
- No crash if building context is missing; asks user to click/select a building
- When a building is selected, answers reference that building’s location

### 3D Building Intelligence
```
Analyze 3D context of this building
What's the view quality from this building?
How does this building compare to neighbors?
Vertical analysis of selected building
```

**Expected:**
- Facts include `building_3d_analysis` with neighbor counts
- Facts include `view_quality`, `shadow_impact`
- Chat describes 3D building context
- Why? tab shows building analysis factors

### Building Investment Analysis
```
Is this building a good investment?
Analyze investment potential of selected building
What's the appreciation outlook for this property?
ROI analysis for this building
```

**Expected:**
- Combined valuation + 3D + market analysis
- Investment score or recommendation
- Risk factors identified

---

## 🗺️ Terrain & Environmental Queries

### Elevation & Topography
```
What's the elevation in Whitefield?
Is Bellandur on low-lying terrain?
Terrain analysis of Sarjapur Road
Slope assessment for this location
```

### Flood Risk
```
Flood risk in Bellandur
Is Mahadevapura flood-prone?
Safe areas from flooding near Koramangala
Drainage quality in HSR Layout
```

### Terrain Robustness
```
What's the slope in Sarjapur Road?
Is this area suitable for construction?
Which areas have low flood risk but good access to metro?
```

**Expected:**
- Terrain fields present (elevation/slope/aspect/flood risk) where supported
- If some terrain metrics are missing, response should explain limitations (no crash)

**Expected:**
- Chat: Terrain insights
- Analysis: Flood risk indicators
- Why? Tab: Environmental risk meters

---

## 📈 Market & Valuation Queries

### Price Analysis
```
Average price per sqft in Koramangala
Price trends in Whitefield last 5 years
Most expensive areas in Bangalore
Affordable neighborhoods under 8000/sqft
```

### Valuation
```
What's a fair price for 2BHK in Indiranagar?
Is 1.2 crore reasonable for 3BHK in HSR?
Price estimate for 1500 sqft in Electronic City
```

### Valuation Parameter Coverage
```
Estimate price for 1BHK 650 sqft in Whitefield
Estimate price for 3BHK 1800 sqft in Koramangala
Estimate price for 2BHK 1200 sqft in Sarjapur Road
Price per sqft estimate in Indiranagar for 1000 sqft
```

**Expected:**
- Chat includes estimated price + price/sqft + confidence/range (if model provides)
- If valuation cannot be computed, return a clear reason + fallback suggestions

### Market Stats Consistency
```
How many active listings are near Koramangala?
Show median price near Whitefield
What is the price trend percentage in Electronic City?
```

**Expected:**
- Fields should be numeric and never crash on `None` values

---

## 🎬 Storytelling & Animation Queries

### Locality Tours
```
Give me a tour of Koramangala
Show me around Whitefield
Explore Indiranagar with me
Take me on a virtual tour of HSR Layout
```

**Expected:**
- Map: Camera flies through the area
- Narration overlay: Description of the area
- Multiple scene transitions

### Comparative Tours
```
Show me the difference between old and new Whitefield
Tour the IT corridor from Silk Board to Electronic City
```

---

## 💬 Conversational Follow-ups

### Context-Aware
```
User: "Analyze Koramangala"
AI: [Analysis response]
User: "What about schools nearby?"
User: "How's the traffic?"
User: "Compare it with Indiranagar"
```

**Expected:** AI maintains context from previous messages

### Clarification
```
User: "Find properties"
AI: "Which area are you interested in?"
User: "Whitefield, under 1 crore"
```

---

## 🔧 System & Admin Queries

### Status Checks
```
What data do you have?
How many properties are in the database?
What areas do you cover?
```

### Capability Queries
```
What can you help me with?
What analysis can you do?
How do simulations work?
```

---

## ⚠️ Edge Cases & Error Handling

### Unknown Locations
```
Go to Mars
Show me properties in Mumbai
Navigate to New York
```
**Expected:** Graceful error with suggestion to try Bangalore areas

### Outside-Scope India Locations (Graceful)
```
Go to Chennai
Analyze Delhi real estate
Show me properties in Hyderabad
```
**Expected:** Clear “offline Bangalore-only dataset” limitation + suggestions

### Ambiguous Queries
```
Best area
Good investment
Nice place
```
**Expected:** Follow-up question for clarification

### Ambiguity With Follow-up (Must Resolve)
```
Best area
For a family, budget 90 lakhs, near metro
```

**Expected:**
- Second message should trigger a concrete shortlist (not another vague question)

### Invalid Data Requests
```
Properties from 1800s
Future prices in 2050
Historical data from 1900
```
**Expected:** Explain data limitations

### Conflicting Intents (Router Robustness)
```
Go to Whitefield and show me 2BHK under 80 lakhs
Compare Koramangala vs Indiranagar and tell me where to invest
Analyze Bellandur and simulate a new metro station there
```

**Expected:**
- System either executes a combined workflow or asks a single clarifying question
- No intent misfire that drops critical actions (map flyTo + results)

---

## 🧪 Advanced Test Scenarios

### Multi-Step Workflows

**Scenario 1: First-Time Buyer Journey**
```
1. "I'm looking to buy my first apartment in Bangalore"
2. "Budget is around 70-80 lakhs"
3. "I work in Electronic City"
4. "Prefer good schools nearby"
5. "Show me the best options"
6. "Why is this area good for families?"
7. "What are the risks?"
```

**Scenario 2: Investor Analysis**
```
1. "Best areas for investment in 2026"
2. "Compare top 3 for appreciation potential"
3. "What if metro expands to Sarjapur?"
4. "Show me properties with high rental yield"
5. "Explain the investment thesis"
```

**Scenario 3: Area Deep-Dive**
```
1. "Tell me everything about Whitefield"
2. "Show me the area on map" [Click Explore button]
3. "What's driving the price growth?"
4. "Simulate impact of new IT parks"
5. "Compare with Electronic City"
```

---

## 🧾 Grounding / No-Hallucination Tests

### Force the System to Stay Grounded
```
Give me exact price trend % for Koramangala and cite the source
How many POIs are there within 1km of Indiranagar? Provide the number used.
What is the elevation of Whitefield? If unknown, say unknown.
```

**Expected:**
- If a number is not available from deterministic agents, AI explicitly says it’s unavailable
- No invented statistics

### Consistency Across Repeats
```
Analyze Koramangala
Analyze Koramangala again
```

**Expected:**
- Deterministic fields should be consistent (counts/scores) unless the underlying data changes

---

## ✅ Validation Checklist

After running queries, verify:

### Chat Panel
- [ ] Responses are contextual and accurate
- [ ] Markdown formatting renders correctly
- [ ] Locality cards appear for area queries
- [ ] Thinking/Reasoning panel expands properly

### Analysis Panel (Insights Tab)
- [ ] Market overview updates with real data
- [ ] Simulation results show for what-if queries
- [ ] "Ask about this" buttons work

### Analysis Panel (Why? Tab)
- [ ] Feature impact bars show positive/negative
- [ ] Confidence gauge displays correctly
- [ ] Reasoning steps are expandable
- [ ] Risk meters show appropriate levels

### Map Panel
- [ ] Camera flies to locations smoothly
- [ ] Orbit animation plays during analysis
- [ ] Storyboard narration appears
- [ ] Stop button works for animations
- [ ] Properties highlight correctly

### Cross-Panel Sync
- [ ] Chat triggers analysis updates
- [ ] Map responds to flyTo commands
- [ ] Locality cards trigger map fly-to
- [ ] "Ask about this" triggers chat query

### Response Contract (API/UI)
- [ ] `intent` matches the user request type
- [ ] `ui_actions` is present for map actions when applicable
- [ ] `dashboard` is populated for the active panel
- [ ] `facts`/`facts_summary` are populated for deterministic agent outputs

---

## � RAG & Semantic Search Queries

### Semantic Property Search
```
Find properties similar to luxury apartments
Search for family-friendly homes with gardens
Properties matching "modern amenities near tech park"
Semantic search: quiet neighborhood with good schools
```

**Expected:**
- RAG-enhanced search results
- Relevance scores for matches
- Chat explains matching criteria

### Context-Aware Queries
```
What properties match my previous search criteria?
Find more like the last property I viewed
Similar areas to Koramangala for investment
Recommendations based on my preferences
```

**Expected:**
- Uses session context and history
- Personalized recommendations
- Chat references previous interactions

---

## 🧪 3D Facts Validation Tests

### Verify 3D Spatial Facts
```
Analyze Koramangala with full 3D context
Get complete spatial analysis for Whitefield
Full 3D reasoning for this location
```

**Expected Facts Fields:**
- `sky_view_factor`: float 0-1
- `open_view_directions`: list of cardinal directions
- `skyline_character`: string ("high-rise", "mixed", "low-rise")
- `optimal_floor`: integer
- `shadow_analysis`: dict with hour-based data
- `view_quality`: string rating
- `spatial_3d_analysis`: dict with density metrics

### Verify Digital Twin Facts
```
Initialize and query digital twin state
Get simulation model metrics
```

**Expected Facts Fields:**
- `digital_twin_state`: dict with city metrics
- `building_count`, `population_estimate`, `avg_property_price`

### Verify Valuation Facts
```
Estimate property value with full breakdown
Complete valuation analysis for 2BHK
```

**Expected Facts Fields:**
- `estimated_value`: float
- `price_per_sqft`: float
- `confidence`: float 0-1
- `price_range`: tuple (low, high)

---

## �📊 Performance Benchmarks

| Query Type | Expected Response Time |
|------------|------------------------|
| Navigation | < 2 seconds |
| Property Search | < 3 seconds |
| Area Analysis | < 5 seconds |
| 3D Spatial Analysis | < 4 seconds |
| Simulation | < 8 seconds |
| Digital Twin Init | < 3 seconds |
| Valuation | < 4 seconds |
| Comparison | < 6 seconds |
| RAG Search | < 3 seconds |

---

## 🎯 Extended Benchmark Suite

### Core Functionality Tests
| Test | Query | Expected Intent | Validate Facts |
|------|-------|-----------------|----------------|
| Nav-1 | Go to Indiranagar | navigate | lat, lng |
| Nav-2 | Fly to 12.9716, 77.5946 | navigate | lat, lng |
| Prop-1 | Find 2BHK in Whitefield | property_search | nearby_properties |
| Prop-2 | Properties under 80 lakhs near metro | property_search | nearby_properties |
| Area-1 | Analyze Koramangala | analyze_area | poi_count, walkability_score |
| Area-2 | Tell me about HSR Layout | analyze_area | accessibility_score |

### 3D Reasoning Tests
| Test | Query | Expected Facts |
|------|-------|----------------|
| 3D-1 | Sky view analysis at Indiranagar | sky_view_factor |
| 3D-2 | Optimal floor recommendation | optimal_floor |
| 3D-3 | Shadow analysis for morning | shadow_analysis |
| 3D-4 | Skyline character of Whitefield | skyline_character |

### Simulation Tests
| Test | Query | Expected Response |
|------|-------|-------------------|
| Sim-1 | Metro impact on Sarjapur | simulation data, causal_analysis |
| Sim-2 | What if IT park in Devanahalli | impact percentages |
| Sim-3 | Zoning change simulation | policy impact |

### Valuation Tests
| Test | Query | Expected Facts |
|------|-------|----------------|
| Val-1 | Estimate 2BHK 1200 sqft Koramangala | estimated_value |
| Val-2 | Price comparison Whitefield vs EC | price_per_sqft |
| Val-3 | Rental yield analysis | rental estimates |

### Digital Twin Tests
| Test | Query | Expected Response |
|------|-------|-------------------|
| DT-1 | Initialize digital twin | digital_twin_state |
| DT-2 | Get twin state | metrics dict |
| DT-3 | Update with metro | state changes |

---

*Generated: January 2026*
*Platform: Valora AI v2.0 - City Intelligence Platform*
