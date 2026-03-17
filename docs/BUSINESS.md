# Valora AI - Bengaluru-First Business and Product Plan (Source of Truth)

Updated: March 2026
Audience: Operating team, seed investors, implementation planning
Scope: Bengaluru-first execution with broker-led wedge and multi-segment expansion over 24 months

---

## 1. Executive Summary

Valora is a self-learning GIS AI decision agent for real estate, starting in Bengaluru.

Execution strategy:
1. Win with broker productivity and explainable decision intelligence.
2. Expand revenue with usage depth and digital workflows.
3. Layer in developer pilots and institutional packaging after workflow traction.

Commercial model:
- Subscription + usage units + B2B pilots/retainers.

Primary operating metric:
- Weekly Active Workflow Users (WAWU).

---

## 2. Bengaluru Market Staging (Locked)

### 2.1 Phase-1 Coverage (Top 12 Micro-Markets)
1. Whitefield
2. Sarjapur Road
3. Electronic City
4. HSR Layout
5. Koramangala
6. Indiranagar
7. Bellandur
8. Marathahalli
9. Hebbal
10. Yelahanka
11. JP Nagar
12. Kanakapura Road

### 2.2 Expansion Rule
- Months 0-6: serve only the top 12 with deep data QA and repeatable playbooks.
- Months 6+: expand to broader Bengaluru corridors using two gates:
  1. demand density,
  2. data freshness and confidence score.

---

## 3. Product Thesis: All-Rounder GIS AI Agent

### 3.1 Positioning
- Valora is a self-learning GIS AI decision agent for high-stakes real-estate decisions.
- It is not a listing portal and not a generic chatbot.
- It combines grounded evidence, explainable reasoning, and recurring workflows.

### 3.2 Core User Jobs
1. Find and compare properties with verifiable locality context.
2. Generate client-ready intelligence outputs (shortlist, report, simulation).
3. Automate recurring work (alerts, reminders, lead follow-up).
4. Learn preferences and improve recommendations over time.

### 3.3 Functional Modules (MVP to Scale)
1. Search + Locality Intelligence
2. Explainable Comparison + Risk
3. Reports and Exports
4. Digital Employee (alerts, tasks, leads)
5. Learning Loop (feedback, pattern reinforcement)
6. Monetization Layer (plans, usage, top-ups, B2B tracking)

---

## 4. Current Product and Data Reality (March 2026)

### 4.1 Product Status
- Grounded chat and report flows: active.
- Spatial analysis stack (terrain, 3D, visibility, sunlight heuristics): active.
- Digital employee workflows: active.
- Credits/pricing system: active.
- Payments: partially productionized (Stripe route exists; some demo/stub paths remain to harden).

### 4.2 Data Footprint (Local Snapshot)
- Properties: 42,452
- Buildings: 686,370
- POIs: 26,961
- Roads: 334,784
- Transport stops: 5,384
- Open datasets catalog: 455,066

---

## 5. Planned Public Interfaces (App Design Spec)

These are planned interfaces for implementation sequencing. They are not yet declared as production-stable APIs.

### 5.1 API Additions
1. `POST /api/agent/preferences/upsert`
- Input: user preference profile (`budget`, `typology`, `commute`, `risk_tolerance`, `intent_horizon`)
- Output: normalized preference state + `profile_version`

2. `GET /api/agent/recommendations`
- Input: `profile_version` + locality/property filters
- Output: ranked explainable recommendations

3. `POST /api/agent/feedback`
- Input: `recommendation_id` + action (`save`, `reject`, `contacted`, `closed`) + optional reason
- Output: `learning_event_id` + updated confidence metadata

4. `GET /api/market/coverage`
- Output: Bengaluru micro-market coverage status, freshness, and confidence band

### 5.2 Planned Type Contracts
1. `PreferenceProfile`
- Fields: budget range, property type, commute preference, risk tolerance, time horizon, must-have filters

2. `RecommendationResult`
- Fields: rank score, rationale, comparable localities/properties, projected fit

3. `LearningEvent`
- Fields: event type, trigger action, model confidence delta, timestamp

4. `CoverageStatus`
- Fields: locality id/name, freshness timestamp, source count, confidence band

### 5.3 Standard Metadata Fields
- `confidence_score`
- `evidence_sources`
- `freshness_ts`
- `risk_flags`

---

## 6. ICP and Segment Sequence

### 6.1 Primary ICP (Months 0-12)
Brokers and small-to-mid agencies in Bengaluru top 12 micro-markets.

Why primary:
- Fastest cycle for activation and conversion.
- Strong fit with digital employee workflows.
- Higher repetition supports learning-loop quality.

### 6.2 Secondary Segments
1. Developers and builder sales teams (pilot to retainer motion)
2. NRI and remote investors (report-led trust workflows)
3. Institutional teams (later-stage explainability and deployment requirements)

---

## 7. Monetization Model and Packaging

Monetization remains hybrid and phase-aware:
1. Subscription MRR
2. Usage monetization (units)
3. B2B pilots and retainers

### 7.1 Usage Unit Costs (Current Configuration)

| Action | Units |
|---|---:|
| Chat Query | 1 |
| Property Search | 2 |
| Area Analysis | 3 |
| Valuation | 10 |
| Storyboard | 15 |
| Report Export / PDF | 20 |
| Simulation | 25 |

### 7.2 Tier Packaging (Customer-Facing Baseline)

| Tier | Units/Month | Launch Price | Regular Price |
|---|---:|---:|---:|
| Free | 50 | Rs 0 | Rs 0 |
| Pro | 1,000 | Rs 599 | Rs 2,999 |

Configured, rollout in progress:

| Tier | Units/Month | Launch Price | Regular Price | Status |
|---|---:|---:|---:|---|
| Team | 3,000 | Rs 999 | Rs 4,999 | Configured, partial rollout |
| Enterprise | Unlimited | Custom | Custom | Contract-led |

### 7.3 Top-up Packs

| Pack | Units | Launch Price | Regular Price |
|---|---:|---:|---:|
| Starter | 100 | Rs 59 | Rs 299 |
| Standard | 300 | Rs 139 | Rs 699 |
| Bulk | 1,000 | Rs 399 | Rs 1,999 |

### 7.4 Phase-Specific Monetization Focus
- Months 0-6: Free to Pro conversion + top-up behavior.
- Months 6-12: Team adoption + workflow-linked upsell.
- Months 12-18: developer pilot ACV expansion.
- Months 18-24: institutional packaging and annual contracts.

---

## 8. KPI Framework and Operating Dashboard

### 8.1 North-Star Metric
- Weekly Active Workflow Users (WAWU)

Definition:
- Unique users who trigger at least one recurring workflow action in a week (alert create/update, scheduled task activity, lead workflow action, automation command execution).

### 8.2 Supporting Metrics
1. Free to Pro conversion rate
2. Workflow activation rate (alerts/tasks/leads created)
3. 4-week cohort retention
4. Top-up attach rate
5. Broker team expansion rate
6. B2B pilot to retainer conversion

### 8.3 Dashboard Views
1. Acquisition and activation funnel
2. WAWU trend by segment and micro-market
3. Revenue mix (subscription vs usage vs B2B)
4. Churn and retention by cohort
5. Coverage confidence and data freshness view for top 12 micro-markets

---

## 9. 24-Month Product and GTM Roadmap (Locked)

| Phase | Timeline | Product Priorities | GTM Priorities | Primary KPI | Key Risk |
|---|---|---|---|---|---|
| Phase 1 | Months 0-6 | Stabilize broker workflows, onboarding templates, top-12 data QA | Broker-first penetration in Bengaluru | WAWU growth in broker cohort | Data freshness drift |
| Phase 2 | Months 6-12 | Learning-loop improvements, recommendation confidence, conversion hooks | Start developer paid pilots | Free to Pro + pilot count | Billing/tier inconsistency |
| Phase 3 | Months 12-18 | Deeper automation, report quality, team controls | Scale broker teams and B2B repeatability | Team expansion + retention | Trust and explainability gaps |
| Phase 4 | Months 18-24 | Institutional-ready packaging, advanced intelligence modules | Institutional design partners + early city replication prep | B2B renewals + ARR quality | GTM concentration risk |

---

## 10. Risk Register and Mitigation Playbooks

### 10.1 Data Freshness Drift
Risk:
- Locality or listing intelligence becomes stale, reducing trust.

Mitigation:
1. Freshness SLAs by data source.
2. Coverage confidence scoring by micro-market.
3. UI-level freshness disclosure with timestamp.
4. Escalation workflow when confidence drops below threshold.

### 10.2 Billing and Plans Inconsistency
Risk:
- Misalignment across auth, credits, pricing, and checkout surfaces.

Mitigation:
1. Single pricing config registry.
2. Contract tests across billing-related APIs.
3. Remove demo-only billing paths from production runtime.
4. Monthly reconciliation report (plan, credits, payment state).

### 10.3 Model Trust and Explainability Gaps
Risk:
- Users cannot defend recommendations to clients.

Mitigation:
1. Evidence-first outputs with explicit source references.
2. Confidence and risk flags in recommendation payloads.
3. Post-response verification checks for numeric claims.
4. Feedback loop for rejected recommendations.

### 10.4 GTM Concentration Risk
Risk:
- Over-dependence on one acquisition channel or one micro-market.

Mitigation:
1. Multi-channel broker acquisition (direct, partner, referral).
2. Market-by-market pipeline target balancing.
3. Quarterly segment mix review.
4. Expand to developer pilots by month 12 to diversify revenue base.

---

## 11. Revenue Trajectory Framing

### 11.1 Base-Case Logic
Revenue quality depends on:
1. Workflow activation (drives retention)
2. Free to Pro conversion (drives predictable MRR)
3. Usage depth (drives top-up expansion)
4. B2B renewals (drives ARR quality)

### 11.2 Example Operating Targets (Illustrative, execution-dependent)
- Month 12: repeatable broker conversion engine + first paying developer pilots.
- Month 24: diversified mix across Pro, Team, usage top-ups, and retained B2B accounts.

Note:
- Forecast values should be maintained in a separate financial model sheet to avoid stale hardcoded figures in this document.

---

## 12. Implementation Handoff Notes

### 12.1 What This Document Locks
1. Bengaluru-first market sequence and top-12 launch scope.
2. Broker-first wedge with multi-segment expansion.
3. 24-month roadmap and KPI priorities.
4. Planned API/type additions for the learning agent loop.
5. Hybrid monetization framing by phase.

### 12.2 What Remains for Execution Pass
1. Endpoint implementation and schema validation.
2. Database migrations for preference and learning-event persistence.
3. Billing hardening and rollout cleanup.
4. Dashboard instrumentation and alerting thresholds.

---

## 13. Assumptions and Defaults

1. Immediate narrative audience: seed investors.
2. Primary wedge: brokers in Bengaluru.
3. Product direction: all-rounder self-learning GIS AI agent.
4. Planning horizon: 24 months.
5. This pass updates only `docs/BUSINESS.md` and `docs/pitch.md`.
6. Monetization model remains subscription + usage + B2B pilots.
7. Existing architecture remains valid and is not rewritten here.
