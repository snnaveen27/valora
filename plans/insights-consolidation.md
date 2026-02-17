# Plan: Consolidate Insights Tab into Smart Tabs

## Overview
Consolidate the existing "insights" tab content into the smart tabs to create a unified, streamlined analysis experience. This is similar to the previous building analysis consolidation.

## Current Structure

### Insights Tab (to be removed)
Contains:
1. **KPI Summary Row** - median price, price change 3Y, momentum, risk score, confidence
2. **Sub-tabs**: Overview, Why?, Simulator, Comps, Data
3. **Overview**: Price Time Series Chart, Elevation Chart, Analytics Metrics
4. **Why?**: SHAP Explainability (key drivers)
5. **Simulator**: Scenario Simulator
6. **Comps**: Comparables Panel
7. **Data**: Data Quality Widget, Raw Viewport Data

### Smart Tabs (9 tabs - to be enhanced)
1. **Decision Verdict** - BUY/HOLD/AVOID recommendation
2. **Market Snapshot** - Price trends, market dynamics
3. **Spatial Intelligence** - Infrastructure, POIs
4. **Risk Analysis** - Flood, legal, market risks
5. **ROI Projection** - 3-year return scenarios
6. **Comparables** - Similar properties
7. **Strategy** - Entry/exit recommendations
8. **Data Transparency** - Source verification
9. **Client Pitch** - Broker presentation

## Consolidation Mapping

| Insights Content | Target Smart Tab | Notes |
|-----------------|-----------------|-------|
| KPI Summary Row | Market Snapshot | Top-level KPIs at top |
| Price Time Series Chart | Market Snapshot | Already has price_trend data |
| Elevation Chart | Spatial Intelligence | Terrain/elevation data |
| Analytics Metrics | Market Snapshot | Already has advanced_indicators |
| Why? (SHAP) | Decision Verdict | Already has top_reasons |
| Simulator | ROI Projection | Already has simulation-like data |
| Comparables | Comparables | Already exists! |
| Data Quality | Data Transparency | Already has data_sources |

## Implementation Steps

### Step 1: Update SmartTabsContainer.jsx
- Enhance `generateTabContent` for each tab to include insights data:
  - **Decision Verdict**: Add SHAP explainability (key drivers)
  - **Market Snapshot**: Add KPI metrics, price time series, analytics
  - **Spatial Intelligence**: Add elevation data
  - **ROI Projection**: Add simulation/scenario data
  - **Data Transparency**: Add raw viewport data option

### Step 2: Update SmartTab.jsx
- Modify each tab component to render insights content when available:
  - Add KPI Summary banner to Market Snapshot
  - Add price charts to Market Snapshot
  - Add explainability to Decision Verdict
  - Add comparables to existing Comparables tab
  - Add raw data viewer to Data Transparency

### Step 3: Update MainApp.jsx
- Remove "insights" from tab list
- Keep only "smart" tab

### Step 4: Update AnalysisPanel.jsx
- Remove insights tab rendering logic
- Pass viewportAnalysis to SmartTabsContainer

## Files to Modify
1. `src/components/SmartTabsContainer.jsx` - Add insights data to generateTabContent
2. `src/components/SmartTab.jsx` - Render insights content in each tab
3. `src/components/MainApp.jsx` - Remove insights tab
4. `src/components/AnalysisPanel.jsx` - Remove insights tab rendering

## Key Considerations
- Maintain backward compatibility if no viewportAnalysis data
- Keep the 9-tab structure but enhance each with insights content
- Ensure existing smart report functionality continues to work
