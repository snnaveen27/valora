# Valora City Intelligence Engine

> **Version 2.1** | Production Ready | December 2024

An AI-powered urban real estate platform that transforms raw spatial data into actionable investment intelligence through a layered architecture: **Knowledge Substrate → Reasoning Layer → Narrative Generation → Memory Systems**.

---

## 🧠 The Vision

**The most important and unique feature: City Intelligence Engine (Living City Brain)**

Not property search. Not investor tips. Not digital twin visuals.

A City Intelligence Engine is the foundation that makes everything else inevitable.

### Why This Matters

Real estate today is **reactive**. A City Brain makes it **predictive, structured, and intelligent**.

| Today | With City Brain |
|-------|-----------------|
| Static listings | Living markets |
| Gut feeling | Data-backed foresight |
| Locations as addresses | Dynamic organisms |

### What Makes It Unique

No portal, no startup, no proptech company in India (or globally) has:
- A structured model of how a city evolves
- How micro-markets shift over time
- How infrastructure decisions ripple through price, demand, livability
- How zones behave like living systems

**Everyone else shows what exists. We show how the city thinks and where it's going.**

---

## 🏗️ The Architecture

```
┌───────────────────────────────────────────────────────┐
│           🧠 CITY INTELLIGENCE ENGINE                 │
├───────────────────────────────────────────────────────┤
│ 4. MEMORY LAYER → Self-Learning, Feedback Loops      │
│ 3. NARRATIVE LAYER → LLM as Conscious Voice          │
│ 2. REASONING LAYER → Logic Engine + Simulation       │
│ 1. KNOWLEDGE LAYER → Structured Urban Ontology       │
└───────────────────────────────────────────────────────┘
```

**The brain is the SYSTEM, not the model.**

| Layer | What It Does |
|-------|--------------|
| **Knowledge** | City exists in structured form: Growth Phase, Infra Impact, Risk Profile |
| **Reasoning** | Encodes HOW cities evolve, WHY prices rise, WHAT infra changes do |
| **Narrative** | LLM interprets structured reasoning into human insight |
| **Memory** | Stores predictions, observes outcomes, adjusts rules over time |

---

## 🎯 Core Capabilities

### 1. Locality Personality Models
Every locality gets a living profile:
- **Growth Phase:** Emerging / Accelerating / Mature / Saturated
- **Investor Type:** Speculative / Stable Yield / Defensive
- **Risk Index:** Flood / Infrastructure / Liquidity

### 2. Evolution Timelines
Each area has a story: **Past → Present → Predicted Future**
- How it grew
- Why it grew
- Where it's heading next

### 3. Infrastructure Impact Forecasting
Simulate: New metro, road expansion, zoning change, IT corridor
Predict: Which micro-markets win, which decay, how prices shift

### 4. Intelligent Narratives
Instead of dashboards, the AI explains:
> "Whitefield is entering late-stage commercialization; expect rental yield stabilization but slower capital appreciation compared to Sarjapur Road which is entering mid-growth."

---

## 🚀 Quick Start

```bash
# 1. Start all services
python start.py

# 2. Access the platform
Frontend:  http://localhost:3000
API Docs:  http://localhost:8000/docs
Chat API:  http://localhost:3001
```

## Tech Stack

- **Frontend:** React + Vite + TailwindCSS + Mappls Maps
- **Backend:** FastAPI (Python) + Express (Node.js)
- **Database:** PostgreSQL + PostGIS + pgvector
- **AI:** Qwen3 VL (vision) + Qwen3 Next (reasoning) + OpenRouter
- **Spatial:** BBMP wards, OSM layers, GIS analysis

---

## 🛠️ Two Core Products

### 1. Dynamic Market Prediction Engine (DMPE)

The DMPE is the Reasoning Layer exposed as a product. It provides:

| Feature | Description |
|---------|-------------|
| **Price Forecasting** | 1yr, 3yr, 5yr predictions with confidence intervals |
| **Automated Valuation** | Instant property valuations via API |
| **Market Heatmaps** | City-wide visualization of trends |
| **Investment Scoring** | Opportunity ranking by strategy (growth, yield, defensive) |
| **Risk Assessment** | Flood, infrastructure, liquidity risk indices |

### 2. 3D Property Digital Twins

Virtual property experiences powered by intelligence:

| Feature | Description |
|---------|-------------|
| **Virtual Tours** | WebGL-based 3D walkthroughs |
| **Virtual Staging** | AI-generated furniture and decor |
| **Data Overlays** | Price predictions, risk badges on rooms |
| **Remote Viewing** | NRI investors explore properties from anywhere |
| **Measurements** | In-viewer room dimensions |

---

## 👥 Target Users

| Segment | Use Case |
|---------|----------|
| **Real Estate Agents** | Data-backed valuations, virtual showings, faster sales |
| **Property Developers** | Market sizing, pricing strategy, virtual project launches |
| **NRI Investors** | Remote property viewing, investment analysis, trusted data |
| **Banks & Lenders** | Automated valuations, portfolio risk, collateral assessment |
| **Homebuyers** | Transparent pricing, neighborhood insights, virtual tours |

---

## 📊 Market Context

- India's real estate market: **$320B → $1T by 2030**
- PropTech market: **$1.5B → $4B+ by 2030** (15% CAGR)
- 65% of buyers struggle with reliable property information
- Average property search: **6-12 months** (we aim to cut this dramatically)

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design, 5-layer architecture, agents, Phase-1 ORR pilot |
| [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) | Implementation status, Phase-1 checklist, CityGML pipeline |
| [API_REFERENCE.md](./API_REFERENCE.md) | All API endpoints with curl examples |
| [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) | Setup, database, ETL, testing |
| [USER_GUIDE.md](./USER_GUIDE.md) | How to use the application |
| [CHANGELOG.md](./CHANGELOG.md) | Version history and release notes |

---

## Project Structure

```
windsurf-project/
├── backend/                 # FastAPI backend
│   ├── api/                # API endpoints
│   ├── services/           # Business logic + agents
│   ├── database/           # PostgreSQL schemas + connections
│   └── models/             # ML models
├── src/                    # React frontend
│   ├── components/         # UI components
│   └── pages/              # Application pages
├── scripts/                # Utilities and startup scripts
├── data/                   # Raw and processed data
└── docs/                   # Documentation
```

## License

Proprietary — All rights reserved.

---

*Built with the vision of making real estate decisions data-driven and intelligent.*
