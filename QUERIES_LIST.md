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

### Investment-Focused
```
Best investment properties in Bangalore
High appreciation areas for buying
Properties with rental yield potential
Affordable areas with growth potential
```

---

## 📊 Area Analysis Queries

### Comprehensive Analysis
```
Analyze Koramangala for investment
Tell me about Whitefield market trends
What's the walkability score of Indiranagar?
How is the connectivity in HSR Layout?
```

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

## 🏗️ Building Analysis Queries

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

### Ambiguous Queries
```
Best area
Good investment
Nice place
```
**Expected:** Follow-up question for clarification

### Invalid Data Requests
```
Properties from 1800s
Future prices in 2050
Historical data from 1900
```
**Expected:** Explain data limitations

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

---

## 📊 Performance Benchmarks

| Query Type | Expected Response Time |
|------------|------------------------|
| Navigation | < 2 seconds |
| Property Search | < 3 seconds |
| Area Analysis | < 5 seconds |
| Simulation | < 8 seconds |
| Comparison | < 6 seconds |

---

*Generated: January 2026*
*Platform: Valora AI v2.0 - City Intelligence Platform*
