# Valora AI — Business Model & Execution Plan

**Document Version**: 1.0  
**Date**: January 2026  
**Scope**: Bangalore offline-first MVP → repeatable expansion to other Indian metros

---

## 1) Executive Summary

Valora AI is an **offline-first 3D GIS + AI reasoning platform for real estate intelligence**.

It combines:

- **Deterministic spatial analytics** (grounded facts, no hallucinated numbers)
- **3D city visualization** (buildings/terrain/POIs/transport)
- **Local LLM narration + planning** (via Ollama; privacy-friendly, low-latency)

**Core promise**: *Trustworthy, explainable real estate and city intelligence that works even with unreliable internet.*

### Why now
Indian real estate decisions still rely on:

- Fragmented listing portals
- Unverifiable broker “gut feel”
- Limited spatial context (flood risk, access, amenities, micro-location)

Valora packages these into a **single interactive 3D intelligence layer**.

---

## 2) Problem Statement (What we solve)

### 2.1 For buyers & investors
- Hard to compare neighborhoods beyond “brand value”
- Unclear micro-risks (flood, access bottlenecks, noise corridors)
- No grounded explanation of why a locality is good/bad

### 2.2 For brokers
- Need faster, more confident answers during client calls
- Need credible “why” narratives to close deals
- Need quick shortlists based on constraints

### 2.3 For developers
- Need demand signals to decide where/what to build
- Need scenario reasoning: “if metro arrives, what happens?”
- Need sharper pricing, positioning, and messaging

### 2.4 For lenders & enterprise
- Need consistent valuations and risk flags
- Need portfolio monitoring and localized risk intelligence
- Need on-prem / privacy-friendly deployment options

---

## 3) Product Definition (What Valora is)

### 3.1 Product modules

1. **3D City Model (Digital Twin UI)**
   - Buildings, POIs, transport, roads, terrain
   - Click-to-select building intelligence
   - Camera fly-to, tours, storytelling overlays

2. **AI Orchestrator (Multi-agent reasoning)**
   - Intent classification
   - Deterministic fact gathering from local datasets
   - Narrative synthesis from grounded facts

3. **Decision Intelligence**
   - Area analysis (amenities, access, risk)
   - Building/3D context (sky view, skyline character, shadow)
   - Valuation estimation (with confidence)
   - What-if simulations (metro, IT park, zoning/FAR changes)

### 3.2 Differentiation

- **Offline-first**: designed to operate with **local data + local models**
- **Grounded**: “LLM only narrates; tools compute facts”
- **3D-native**: view quality, shadow, skyline, verticality, neighborhood morphology
- **Explainable**: Why tab + confidence + assumptions

---

## 4) Target Customers & Personas

### 4.1 Brokers & agencies (B2B SaaS / license)

**Jobs-to-be-done**:
- Shortlist areas and properties quickly
- Explain “why this locality” in plain language
- Build credibility with objective metrics

**Value from Valora**:
- Faster turnaround for client requests
- Standardized reports and shortlists
- Differentiated service (“3D intelligence + explainability”)

**Primary product package**:
- Valora Pro (seat-based)

### 4.2 Developers & builders (B2B per project + retainer)

**Jobs-to-be-done**:
- Identify high-potential micro-markets
- Run scenario-based impact narratives
- Create 3D-driven storytelling for sales & marketing

**Value from Valora**:
- Faster site selection and pricing alignment
- Better sell-through via credible neighborhood narrative
- Competitive advantage through visual + analytical storytelling

**Primary product package**:
- Valora Developer Studio (per project)

### 4.3 Banks, lenders, NBFCs (Enterprise on-prem)

**Jobs-to-be-done**:
- Automated valuation support
- Risk flags & locality intelligence
- Portfolio monitoring

**Value from Valora**:
- Consistent internal valuation assistance
- Reduced underwriting risk through spatial intelligence
- On-prem deployment option

**Primary product package**:
- Valora Enterprise (annual license + SLAs)

### 4.4 NRI / remote investors (Premium service)

**Jobs-to-be-done**:
- Remotely evaluate areas with confidence
- Get explainable shortlists + risk summaries

**Value from Valora**:
- Shortlists grounded in local data
- Decision support without “portal bias”

**Primary product package**:
- Valora Premium Reports (per report / concierge)

---

## 5) Business Model Canvas

| Block | Summary |
|------|---------|
| **Customer Segments** | Brokers/agencies, developers, lenders, NRI investors, asset managers |
| **Value Propositions** | Offline-first 3D intelligence, grounded analytics + explainability, scenario simulation |
| **Channels** | Direct sales (enterprise/dev), broker partnerships, workshops/webinars, content, referrals |
| **Customer Relationships** | Onboarding + templates, training, customer success, account management |
| **Revenue Streams** | Seat licenses, project licenses, enterprise annual license, data update subscription, premium reports |
| **Key Resources** | Datasets, spatial/3D engines, valuation models, local LLM setup, UI/UX, domain expertise |
| **Key Activities** | Data packaging, model training, tool reliability, UX + reporting, customer onboarding |
| **Key Partners** | Broker associations, developers, data providers, GIS/open data ecosystem, channel partners |
| **Cost Structure** | Engineering, data ops, sales, customer success, compute/hardware testing, legal/compliance |

---

## 6) Pricing & Packaging

### 6.1 Usage-Based Model (Monthly Units)

Valora uses a **monthly unit allocation** model instead of traditional seat-based pricing. This aligns cost with value delivered.

#### Unit Costs by Action
| Action | Unit Cost |
|--------|-----------|
| Basic Chat Query | 1 |
| Property Search | 2 |
| Area Analysis | 3 |
| Valuation Estimate | 10 |
| Storyboard/Narrative | 15 |
| Report Export (PDF) | 20 |
| What-If Simulation | 25 |

#### Subscription Tiers

| Tier | Units/Month | Base Price | Launch Price (80% off) |
|------|-------------|------------|------------------------|
| **Free** | 50 | ₹0 | ₹0 |
| **Pro** | 1,000 | ₹2,999/mo | ₹599/mo |
| **Team** | 3,000/seat | ₹4,999/seat/mo | ₹999/seat/mo |
| **Enterprise** | Unlimited | Custom | Custom |

#### Top-up Packs (When Units Exhausted)

| Pack | Units | Base Price | Launch Price |
|------|-------|------------|--------------|
| Starter | 100 | ₹299 | ₹59 |
| Standard | 300 | ₹699 | ₹139 |
| Bulk | 1,000 | ₹1,999 | ₹399 |

### 6.2 Launch Promotion (80% OFF)

**Promo Code: LAUNCH80**
- **Discount**: 80% off all plans and top-ups
- **Valid Until**: March 31, 2026
- **Purpose**: Drive early adoption and engagement
- **Auto-applied**: No code entry required

### 6.3 Payment Gateways

Valora supports dual payment gateway integration for flexibility:

#### Stripe (Recommended for AI)
- **Best for**: AI/LLM usage tracking, metered billing
- **Features**: Billing Meters API, automatic token tracking, LLM Proxy (private preview)
- **Fees**: 2.9% + ₹2 per transaction
- **Why Stripe for AI**: Syncs model prices, records usage automatically, supports usage-based margins

#### Razorpay
- **Best for**: Subscriptions with add-ons
- **Features**: UPI AutoPay, Quantity-based billing, Proration
- **Fees**: 2% per transaction + 0.9% subscription management

#### Cashfree
- **Best for**: Fast settlements, UPI AutoPay
- **Features**: Auto-Collect, e-NACH for recurring
- **Fees**: 1.9% per transaction

#### Gateway-to-Plan Mapping
| Plan | Recommended Gateway |
|------|---------------------|
| AI Usage (metered) | Stripe Billing Meters |
| Pro (fixed monthly) | Stripe or Razorpay |
| Team (per-seat) | Razorpay Quantity-Based |
| Top-ups | Any gateway |

### 6.4 Billing Behavior

**When units exhausted (Hard Limit - Option A)**:
- ✅ Map navigation remains available (read-only)
- ❌ AI queries blocked
- ❌ Reports/simulations blocked
- 💡 Upgrade/Top-up modal shown with promo pricing

**Monthly Reset**: Units reset on billing cycle date
**Proration**: Auto-calculated when upgrading mid-cycle

### 6.5 Developer Plans

- **Per project license** (site + catchment analysis + storytelling)
- **Quarterly retainer** for updates and scenario iterations

### 6.6 Enterprise (Banks / lenders)

- Annual enterprise license
- On-prem deployment option
- SLA + security review
- API integration add-on
- Fair-use unlimited units

### 6.7 Data & Model Update Subscription

Offline-first systems still need updates.

- Monthly/quarterly "data packs" (listings, POIs, transport updates)
- Model refresh schedule (valuation recalibration)

---

## 7) Go-To-Market (GTM) Plan

### 7.1 Beachhead strategy (Bangalore)

**Goal**: win a narrow segment deeply, then expand.

- Pilot 20–50 brokers (high activity, premium clientele)
- Pilot 3–5 developer teams (pre-sales + market intelligence)
- Collect feedback from decision-makers (not only operators)

### 7.2 Positioning

**Positioning statement**:

> Valora is the offline-first 3D intelligence layer for real estate decisions—combining trustworthy spatial analytics with explainable AI.

### 7.3 Acquisition channels

- **Broker associations**: training sessions + certification
- **Workshops**: “3D intelligence for closing deals”
- **Referral loops**: broker invites broker
- **Developer partnerships**: demonstrate scenario + storytelling
- **Content**: locality intelligence briefs, risk explainers (flood/infra)

### 7.4 Sales motion

- **Brokers**: product-led + inside sales
- **Developers**: consultative sale (project ROI)
- **Enterprise**: longer cycle (security + procurement)

---

## 8) Product Roadmap (Execution Plan)

### Phase 1 — Offline Bangalore MVP (0–8 weeks)

- Stabilize property search + filters
- Harden intent routing + deterministic fact extraction
- Improve explainability (confidence, missing data warnings)
- Add report templates (PDF/Markdown export)

**Exit criteria**:
- 90%+ query success on core intents
- Consistent metrics for repeated queries
- Latency targets met (interactive experience)

### Phase 2 — Monetization & Workflow Fit (2–4 months)

- Broker workflows: saved searches, shortlists, shareable reports
- Developer workflows: scenario packs, corridor analysis, narratives
- Admin tools: data pack updates + health checks

### Phase 3 — Expand to other metros (6–12 months)

- Build “city onboarding pipeline” (data ingestion + QA + locality profiles)
- Replicate Bangalore playbook to 1–2 metros

### Phase 4 — Enterprise scale (9–18 months)

- On-prem hardening, audit logs, role-based access
- Portfolio monitoring dashboards

---

## 9) Operations Plan

### 9.1 Data operations (offline-first)

- Standardized ingestion pipelines
- Validation checks (schema, null coverage, duplicates)
- QA dashboards for dataset completeness
- Release process for “data packs” (versioned)

### 9.2 Model operations

- Local model compatibility matrix (Ollama models)
- Evaluation harness for:
  - accuracy of intent routing
  - deterministic tool outputs
  - hallucination prevention (grounding contract)

### 9.3 Customer success

- Onboarding playbook (1-hour setup + 1-hour training)
- “Top 50 queries” cheat sheet
- Monthly business review for enterprise/dev

---

## 10) Metrics & KPIs

### North Star metrics
- **Weekly Active Decision Sessions** (WADS)
- **Shortlist-to-action conversion** (did the shortlist lead to site visit/booking?)

### Product KPIs
- Intent accuracy
- Tool success rate (no-crash, valid outputs)
- Median response latency per intent
- % responses with grounded numeric facts
- % queries requiring clarification

### Business KPIs
- Trial → paid conversion
- Net revenue retention (NRR)
- CAC, payback period
- LTV/CAC

---

## 11) Financial Plan (Planning Assumptions)

> These are planning assumptions for internal sizing and investor narrative.

### Example Year-1 targets
- 500 paying broker seats
- 10 developer projects
- 1 enterprise pilot

### Cost buckets
- Engineering (full-stack, GIS, ML)
- Data ops
- Sales + customer success
- Legal/compliance

### Unit economics (to validate in pilot)
- Broker CAC depends on acquisition channel (association vs paid ads)
- Gross margin expected high because deployment is local/offline-first

---

## 12) Risk Register & Mitigations

### Product risks
- **Data gaps / missing coverage** → clear missing-data messaging + roadmap for pack updates
- **Hallucinations** → strict grounding contract + deterministic tooling
- **Latency** → caching + optimized queries + precomputed locality profiles

### Market risks
- **Broker adoption friction** → training + templates + ROI storytelling
- **Competition from portals** → differentiate on explainability + 3D + offline + decision workflows

### Operational risks
- **Data licensing** → prefer open data + explicit partner agreements
- **Compliance/security** → on-prem option + audit trails for enterprise

---

## 13) Implementation Checklist (Practical)

- Define target segments for pilot (brokers vs developers)
- Confirm pricing hypotheses via 15–20 user interviews
- Create “report templates” that match how brokers sell (PDF/WhatsApp share)
- Build a repeatable “city data pack” process for expansion
- Establish evaluation benchmarks and regression suite

---

## Appendix A — Suggested Packaging for Offline Deployment

- Windows installer for frontend + backend + local DB
- Optional GPU support for local LLM acceleration
- Versioned data packs (monthly/quarterly)
- Admin health dashboard:
  - DB present
  - local LLM reachable
  - tile/model assets available
  - key endpoints healthy
