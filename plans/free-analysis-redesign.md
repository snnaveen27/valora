# Free Analysis Tab Redesign

## Overview
Redesign the Free Analysis tab to show randomized free properties from the database. Users can analyze these properties for free (no credits deducted) using local LLM only.

## Requirements

### User Experience
1. Display property cards organized by category (Apartment, Flat, Villa, Warehouse, Shop, Plot, etc.)
2. Each user sees different randomized properties daily
3. One free property per category
4. **Limit: 3 free analyses per day**
5. **Daily refresh** - new properties each day
6. Clicking a property triggers free analysis (no credits deducted)
7. Analysis uses local model only (qwen3:4b-instruct or similar)
8. **Map integration**: Fly to property location, show labels on map

### Property Categories (by property_type/listing_type)
- **Apartment** (for sale)
- **Flat** (for rent)
- **Villa** (independent house)
- **Warehouse** (commercial)
- **Shop** (retail)
- **Plot** (land)
- **Office** (commercial)

### Property Card Display
- Property image (if available)
- Property title/name
- Location/Locality
- Price
- Area (sqft)
- Type badge (Apartment, Villa, etc.)
- Listing type badge (Sale/Rent)
- "Analyze Free" button (disabled if daily limit reached)
- "View on Map" button

## Technical Implementation

### Backend Changes

#### 1. New Endpoint: `/api/free-properties`
```python
@router.get("/api/free-properties")
async def get_free_properties(user_id: str = None):
    """
    Get randomized free properties for user.
    Returns one property per category.
    Daily refresh based on date seed.
    """
    categories = ['apartment', 'flat', 'villa', 'warehouse', 'shop', 'plot', 'office']
    # Randomize based on user_id + date (daily rotation)
    # Return property details with images
```

#### 2. Free Analysis Endpoint: `/api/analyze-free`
```python
@router.post("/api/analyze-free")
async def analyze_free_property(request: FreeAnalysisRequest):
    """
    Analyze a free property without deducting credits.
    Uses local model only.
    Limit: 3 per day per user.
    """
    # Check daily limit (3 per day)
    # Verify property is in free list
    # Use local model (qwen3:4b-instruct)
    # Return analysis + flyTo coordinates
```

#### 3. Database Query
```sql
-- Get one random property per category (daily seed)
SELECT * FROM properties 
WHERE property_type = 'apartment'
  AND listing_type = 'sale'
ORDER BY RANDOM() 
LIMIT 1;
```

### Frontend Changes

#### 1. FreeAnalysisContent Component
```jsx
function FreeAnalysisContent({ setAgentData }) {
  const [freeProperties, setFreeProperties] = useState({});
  const [loading, setLoading] = useState(true);
  const [analyzingProperty, setAnalyzingProperty] = useState(null);
  const [dailyLimitReached, setDailyLimitReached] = useState(false);
  const [analysesRemaining, setAnalysesRemaining] = useState(3);
  
  // Fetch free properties on mount
  useEffect(() => {
    fetchFreeProperties();
  }, []);
  
  // Handle free analysis click
  const handleAnalyzeFree = async (property) => {
    if (analysesRemaining <= 0) return;
    setAnalyzingProperty(property.id);
    
    // Call /api/analyze-free
    const result = await analyzeFreeProperty(property.id);
    
    // Update agentData with results + flyTo
    setAgentData(prev => ({
      ...prev,
      flyTo: { lat: property.latitude, lng: property.longitude, zoom: 18 },
      freeAnalysis: result.analysis
    }));
    
    setAnalysesRemaining(prev => prev - 1);
  };
  
  // Handle view on map
  const handleViewOnMap = (property) => {
    setAgentData(prev => ({
      ...prev,
      flyTo: { lat: property.latitude, lng: property.longitude, zoom: 17 }
    }));
  };
  
  return (
    <div className="free-properties-container">
      <div className="free-header">
        <h3>Free Property Analysis</h3>
        <span>{analysesRemaining}/3 analyses remaining today</span>
      </div>
      
      <div className="free-properties-grid">
        {Object.entries(freeProperties).map(([category, property]) => (
          <PropertyCard 
            key={category}
            property={property}
            category={category}
            onAnalyze={() => handleAnalyzeFree(property)}
            onViewMap={() => handleViewOnMap(property)}
            isAnalyzing={analyzingProperty === property.id}
            disabled={analysesRemaining <= 0}
          />
        ))}
      </div>
    </div>
  );
}
```

#### 2. Property Card Component
```jsx
function PropertyCard({ property, category, onAnalyze, onViewMap, isAnalyzing, disabled }) {
  return (
    <div className="property-card">
      <div className="property-image">
        <img src={property.image_url || placeholder} alt={property.title} />
        <span className="category-badge">{category}</span>
        <span className="listing-badge">{property.listing_type}</span>
      </div>
      
      <div className="property-details">
        <h4>{property.title}</h4>
        <p className="location"><MapPin /> {property.locality}</p>
        <div className="price-area">
          <span>₹{formatPrice(property.price)}</span>
          <span>{property.area_sqft} sqft</span>
        </div>
      </div>
      
      <div className="property-actions">
        <button onClick={onViewMap} className="view-map-btn">
          <MapPin /> View on Map
        </button>
        <button onClick={onAnalyze} disabled={disabled || isAnalyzing} className="analyze-btn">
          {isAnalyzing ? <Loader /> : 'Analyze Free'}
        </button>
      </div>
    </div>
  );
}
```

### Credit System Integration

#### Daily Limit Check
```python
# In credits_rate_limiter.py or new free_analysis_tracker.py
def get_free_analyses_today(user_id: str) -> int:
    """Get count of free analyses used today."""
    # Query free_property_views for today's count
    
def can_analyze_free(user_id: str) -> tuple[bool, int]:
    """Check if user can do free analysis today."""
    count = get_free_analyses_today(user_id)
    return count < 3, 3 - count
```

#### Model Selection
```python
# Free analysis always uses local model
FREE_ANALYSIS_MODEL = "qwen3:4b-instruct"
```

## Implementation Steps

### Phase 1: Backend
1. Create `/api/free-properties` endpoint
2. Create `/api/analyze-free` endpoint with daily limit
3. Add free analysis tracking table
4. Implement property randomization by date

### Phase 2: Frontend
1. Redesign FreeAnalysisContent component
2. Add PropertyCard component
3. Implement map flyTo integration
4. Add daily limit UI feedback

### Phase 3: Integration
1. Connect frontend to new endpoints
2. Test daily limit enforcement
3. Verify local model usage
4. Test map flyTo and labels

## Database Schema

### Free Analysis Tracking
```sql
CREATE TABLE IF NOT EXISTS free_analysis_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    property_id INTEGER NOT NULL,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_result TEXT,  -- JSON
    FOREIGN KEY (property_id) REFERENCES properties(id)
);

CREATE INDEX idx_free_analysis_user_date 
ON free_analysis_log(user_id, date(analyzed_at));
```

## API Response Format

### GET /api/free-properties
```json
{
  "properties": {
    "apartment": {
      "id": 123,
      "title": "2BHK Apartment in Koramangala",
      "locality": "Koramangala",
      "price": 8500000,
      "area_sqft": 1200,
      "property_type": "apartment",
      "listing_type": "sale",
      "image_url": "...",
      "latitude": 12.9352,
      "longitude": 77.6245
    },
    "flat": {...},
    "villa": {...},
    "warehouse": {...},
    "shop": {...},
    "plot": {...},
    "office": {...}
  },
  "analyses_remaining": 3,
  "refresh_in_hours": 12
}
```

### POST /api/analyze-free
```json
{
  "property_id": 123,
  "analysis": {
    "verdict": "BUY",
    "confidence": 75,
    "price_fairness": "Fair",
    "connectivity_score": 8,
    "safety_score": 7,
    "investment_potential": "Moderate",
    "key_insights": ["Close to metro", "Growing area"],
    "flyTo": {
      "lat": 12.9352,
      "lng": 77.6245,
      "zoom": 18
    }
  },
  "analyses_remaining": 2
}
```
