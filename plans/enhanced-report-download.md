# Enhanced Report Download - Feature Specification

## Overview
Transform the existing download button into an AI-powered comprehensive report generator that:
1. Shows confirmation dialog with credit cost in chat
2. Deducts credits upon user approval
3. Iteratively generates detailed content for each smart tab using LLM
4. Shows real-time progress in a task bar
5. Downloads both MD and PDF files

## User Flow

```mermaid
graph TD
    A[User clicks Download Report] --> B{AI confirms in Chat}
    B -->|Show| C[Chat: "Generate detailed report? Cost: 200 credits"]
    C --> D{User replies Yes/Proceed?}
    D -->|No/Cancel| E[Cancel - no credits deducted]
    D -->|Yes| F[Deduct 200 credits]
    F --> G[Show Task Progress Bar]
    G --> H[Loop: Process each tab]
    H --> I1[Verdict Tab - LLM call]
    I1 --> I2[Market Tab - LLM call]
    I2 --> I3[Spatial Tab - LLM call]
    I3 --> I4[Risk Tab - LLM call]
    I4 --> I5[ROI Tab - LLM call]
    I5 --> I6[Comparables Tab - LLM call]
    I6 --> I7[Strategy Tab - LLM call]
    I7 --> I8[Data Tab - LLM call]
    I8 --> I9[Pitch Tab - LLM call]
    I9 --> J[Combine all content]
    J --> K[Generate MD file]
    K --> L[Generate PDF]
    L --> M[Download both files]
    M --> N[Update Task Bar: Complete]
```

## Credit System

### Cost Breakdown
- **Total Cost**: 200 credits
- **Per Tab**: ~20 credits per tab (10 tabs × 20 = 200)
- **Verification**: Backend verifies credit balance before starting

### Credit Flow
```
Frontend sends request → Backend checks balance → 
If sufficient: reserve 200 credits → Process tabs →
On success: finalize deduction → On failure: refund
```

## Smart Tab Prompts

### 1. Decision Verdict Tab
```
Generate an investment verdict analysis for {locality}.

Context:
- Verdict: {verdict}
- Confidence: {confidence}%
- Risk Level: {risk_level}
- Top Reasons: {top_reasons}
- Key Risks: {key_risks}
- Strategy: {strategy_recommendation}

Provide:
1. Executive Summary (2-3 sentences)
2. Detailed reasoning for the verdict
3. Confidence breakdown
4. Key positive factors (expand on each)
5. Key risk factors (expand on each)
6. Investment strategy recommendation
```

### 2. Market Snapshot Tab
```
Generate market analysis for {locality}.

Context:
- Avg Price/sqft: ₹{avg_price_sqft}
- Price Trends: {price_trend}
- Demand/Supply: {demand_supply}
- Rental Yield: {rental_yield}
- Liquidity Score: {liquidity_score}
- Advanced Indicators: {advanced_indicators}

Provide:
1. Current market overview
2. Price trend analysis (1Y, 3Y, 5Y)
3. Demand-supply dynamics
4. Rental yield analysis
5. Investment momentum assessment
6. Market risks and opportunities
```

### 3. Spatial Intelligence Tab
```
Generate spatial intelligence analysis for {locality}.

Context:
- Infrastructure: {nearby_infrastructure}
- POIs: {pois}
- Walkability Score: {walkability_score}
- Transit Score: {transit_score}
- Growth Hotspots: {growth_hotspots}

Provide:
1. Infrastructure overview and connectivity
2. POI analysis (schools, hospitals, malls, offices)
3. Walkability and transit assessment
4. Future growth areas
5. Location strengths and weaknesses
```

### 4. Risk Analysis Tab
```
Generate comprehensive risk analysis for {locality}.

Context:
- Overall Risk Score: {overall_risk_score}
- Flood Risk: {flood}
- Legal Risk: {legal}
- Market Risk: {market}
- Infrastructure Risk: {infrastructure}
- Environmental Risk: {environmental}
- Mitigation: {mitigation_suggestions}

Provide:
1. Risk assessment summary
2. Detailed flood risk analysis
3. Legal compliance considerations
4. Market risk factors
5. Infrastructure risk outlook
6. Environmental concerns
7. Mitigation strategies
```

### 5. ROI Projection Tab
```
Generate ROI projection analysis for {locality}.

Context:
- 3-Year Projection: {projection_3year}
- Entry/Exit: {entry_exit}
- Rental Yield: {rental_yield}
- Investment Score: {investment_score}

Provide:
1. Best/Expected/Worst case scenarios
2. Entry price recommendations
3. Target exit prices
4. Rental income potential
5. Timeline for returns
6. Risk-adjusted projections
```

### 6. Comparables Tab
```
Generate comparables analysis for {locality}.

Context:
- Comparables: {comparables}
- Price Analysis: {price_analysis}
- Building Valuation: {building_valuation}

Provide:
1. Comparable property overview
2. Price comparison analysis
3. Similarity assessments
4. Value proposition
5. Competitive positioning
```

### 7. Strategy Tab
```
Generate investment strategy for {locality}.

Context:
- Strategy: {investment_strategy}
- Action Items: {action_items}
- Timeline: {timeline}

Provide:
1. Entry timing recommendation
2. Negotiation strategy
3. Due diligence checklist
4. Action timeline
5. Portfolio fit assessment
```

### 8. Data Transparency Tab
```
Generate data transparency report for {locality}.

Context:
- Verification Status: {verification_status}
- Data Sources: {data_sources}
- Confidence Breakdown: {confidence_breakdown}
- Data Quality: {data_quality}

Provide:
1. Data verification status
2. Source breakdown and freshness
3. Confidence analysis
4. Data quality assessment
5. Missing data warnings
```

### 9. Client Pitch Tab
```
Generate client pitch for {locality}.

Context:
- Summary: {client_summary}
- Building: {building_name}
- Valuation: {building_valuation}

Provide:
1. Compelling headline
2. Key selling points
3. Investment highlights
4. Expected returns
5. Call to action
```

## Backend API Design

### New Endpoints

#### POST /api/smart-report/generate-detailed
Request:
```json
{
  "locality": "Whitefield, Bangalore",
  "lat": 12.9848,
  "lng": 77.7117,
  "building_name": "Prestige Lakeside",
  "include_tabs": ["verdict", "market", "spatial", "risk", "roi", "comparables", "strategy", "data", "pitch"],
  "user_id": "user123"
}
```

Response:
```json
{
  "task_id": "task_abc123",
  "status": "started",
  "total_tabs": 9,
  "credits_charged": 200,
  "progress": {
    "current": 0,
    "percentage": 0,
    "current_tab": "starting..."
  }
}
```

#### GET /api/smart-report/task/{task_id}
Response:
```json
{
  "task_id": "task_abc123",
  "status": "processing|completed|failed",
  "progress": {
    "current": 5,
    "percentage": 55,
    "current_tab": "spatial_intelligence",
    "completed_tabs": ["verdict", "market", "spatial", "risk", "roi"]
  },
  "result": {
    "markdown": "...",
    "pdf_base64": "...",
    "download_urls": {
      "md": "/api/smart-report/download/md/task_abc123",
      "pdf": "/api/smart-report/download/pdf/task_abc123"
    }
  },
  "error": null
}
```

#### GET /api/smart-report/download/{type}/{task_id}
Download MD or PDF file

## Frontend Components

### 1. Task Progress Bar
Location: Top of Smart Panel (replaces or overlays existing header)

Features:
- Circular progress indicator with percentage
- Current tab name being processed
- List of completed tabs with checkmarks
- Cancel button (with credit refund)
- Estimated time remaining
- Status: "Processing", "Generating PDF", "Complete", "Failed"

### 2. Chat Confirmation Dialog
When user clicks download:
1. Send message to AI in chat panel
2. AI responds with confirmation message:
   ```
   📊 **Generate Detailed Report?**
   
   This will create a comprehensive investment report covering:
   - Decision Verdict
   - Market Analysis
   - Spatial Intelligence
   - Risk Assessment
   - ROI Projections
   - Comparables
   - Investment Strategy
   - Data Transparency
   - Client Pitch
   
   **Cost: 200 credits**
   
   Reply **YES** or **PROCEED** to continue, or **CANCEL** to abort.
   ```
3. Listen for user response

### 3. Download Button Enhancement
- Show credit cost on hover/click
- Disable if insufficient credits
- Different states: idle, confirming, processing, complete

## Data Flow

```
1. User clicks Download Button
       ↓
2. Frontend dispatches 'valora-download-report' event
       ↓
3. Chat Panel receives event → Shows confirmation in chat
       ↓
4. User replies "YES" → Frontend calls /api/credits/deduct
       ↓
5. Credits deducted → Backend creates task → Returns task_id
       ↓
6. Frontend shows Progress Bar → Polls task status every 2s
       ↓
7. Backend processes each tab sequentially using LLM
       ↓
8. Each tab completion → Update task progress
       ↓
9. All tabs complete → Generate MD → Generate PDF
       ↓
10. Task complete → Frontend receives download URLs
       ↓
11. Auto-download both files → Update UI to "Complete"
```

## File Structure Changes

### Backend
- `backend/routes/smart_report_routes.py` - Add new endpoints
- `backend/services/report_generator.py` - New service for multi-tab generation
- `backend/services/task_manager.py` - Task tracking and progress

### Frontend
- `src/components/TaskProgressBar.jsx` - New component
- `src/components/MainApp.jsx` - Integrate confirmation flow
- `src/components/chat/EnhancedChatPanel.jsx` - Add confirmation listener

## Implementation Phases

### Phase 1: Backend Foundation
1. Create task management system
2. Implement multi-tab LLM generation
3. Add credit verification and deduction

### Phase 2: Frontend Integration
1. Create TaskProgressBar component
2. Implement chat confirmation flow
3. Add progress polling and download

### Phase 3: Polish
1. Error handling and retry logic
2. PDF quality improvements
3. UX refinements
