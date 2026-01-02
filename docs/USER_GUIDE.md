# User Guide

## Getting Started

### Access the Platform

1. Open your browser
2. Navigate to **http://localhost:3000**
3. You'll see the split-screen interface:
   - **Left:** Interactive map
   - **Right:** AI chat panel

---

## Map Features

### Navigation

- **Pan:** Click and drag
- **Zoom:** Scroll wheel or +/- buttons
- **Center on Bangalore:** Click the home button

### Viewing Properties

1. Properties appear as markers on the map
2. **Click** any marker to see:
   - Property type and location
   - Price and size
   - Bedrooms and price per sq ft
3. Click **"Analyze Property"** for detailed insights

### Drawing Tools

Access drawing tools from the bottom toolbar:

| Tool | Use |
|------|-----|
| **Polygon** | Draw custom area for analysis |
| **Circle** | Create radius-based zones |
| **Rectangle** | Quick box selection |
| **Polyline** | Measure distances |
| **Marker** | Mark points of interest |

**How to Draw:**
1. Select a tool
2. Click on map to start
3. Continue clicking to add points
4. **Double-click** or **right-click** to finish

### Layers

Toggle map layers from the Layers dropdown:
- **Properties:** Show/hide property markers
- **Wards:** BBMP ward boundaries
- **Zones:** Zone boundaries
- **POIs:** Points of interest
- **Roads:** Road network

---

## AI Chat

### Basic Queries

Type natural language questions:

```
"Find 3BHK apartments in Whitefield under 1 crore"
"Show investment hotspots in South Bangalore"
"What's the rental yield in Electronic City?"
```

### Map Commands

Control the map with chat:

```
"Draw 2km buffer around Manyata Tech Park"
"Show properties in Koramangala"
"Zoom to HSR Layout"
"Compare Whitefield and Sarjapur"
```

### Analysis Queries

Get AI-powered insights:

```
"Analyze the drawn polygon for investment"
"What's the growth potential of this area?"
"Compare these two zones for residential vs commercial"
"Predict property values for 2027"
```

### Example Conversations

**Investment Analysis:**
```
You: "I'm looking for investment properties with high rental yield"
AI: "Based on current data, Electronic City and Whitefield show 
     strong rental yields of 3.5-4.2%. Would you like me to show 
     properties in these areas?"
You: "Yes, show me options under 80 lakhs"
AI: [Displays filtered properties on map]
```

**Area Comparison:**
```
You: "Compare Koramangala and Indiranagar for buying a flat"
AI: "Both are premium localities. Here's the comparison:
     - Koramangala: Avg ₹12,500/sqft, mature market, stable growth
     - Indiranagar: Avg ₹14,000/sqft, higher premium, metro access
     Koramangala offers better value; Indiranagar better appreciation."
```

---

## Time Slider

The time slider at the top of the map lets you explore property values across time:

1. **Drag** the slider to a different year
2. Property values update to show:
   - Historical prices (past years)
   - Current prices (today)
   - Predicted prices (future years)
3. Click **Play** to animate through time

---

## Location Analysis

### Pin Analysis

1. **Right-click** anywhere on the map
2. A pin appears with instant analysis:
   - Location importance score
   - Investment grade (A+ to C)
   - Nearby amenities
   - Price prediction

### Polygon Analysis

1. Draw a polygon on the map
2. Ask the AI: "Analyze this area"
3. Get detailed report:
   - Property count and density
   - Average prices
   - Infrastructure score
   - Development potential
   - Investment recommendations

---

## Tips & Tricks

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+Z` | Undo last action |
| `Ctrl+Y` | Redo |
| `Escape` | Cancel current drawing |
| `Delete` | Remove selected shape |

### Best Practices

1. **Be specific** in chat queries for better results
2. **Draw smaller polygons** for more accurate analysis
3. **Use zone comparison** before making investment decisions
4. **Check confidence scores** — lower scores mean less certain predictions

### Common Questions

**Q: Why are some areas grayed out?**
A: Those areas may have insufficient data for accurate predictions.

**Q: How accurate are the price predictions?**
A: Predictions have 80-90% accuracy for well-covered areas. Always check the confidence score.

**Q: Can I save my analysis?**
A: Shapes are automatically saved in your browser. Export to GeoJSON for permanent storage.

**Q: How often is data updated?**
A: Property data is updated weekly. Market statistics are updated daily.

---

## Troubleshooting

### Map Not Loading

1. Check if Mappls API key is configured
2. Clear browser cache
3. Try a different browser

### Chat Not Responding

1. Check if backend services are running
2. Look for errors in browser console
3. Refresh the page

### Predictions Seem Wrong

1. Verify the property details are correct
2. Check if the area has sufficient data
3. Note the confidence score — low confidence means uncertain prediction

---

## Glossary

| Term | Definition |
|------|------------|
| **DMPE** | Dynamic Market Prediction Engine |
| **Growth Phase** | Stage of area development (Emerging → Mature) |
| **Investment Grade** | Rating from A+ (best) to C (risky) |
| **Rental Yield** | Annual rent as percentage of property value |
| **Absorption Rate** | Rate at which properties sell in an area |
| **Infrastructure Score** | Rating of roads, metro, amenities |
| **POI** | Point of Interest (schools, hospitals, etc.) |

---

## Getting Help

- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Developer Guide:** See `DEVELOPER_GUIDE.md`
