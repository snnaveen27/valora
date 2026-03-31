# Valora AI - Bengaluru-First Business and Product Plan (Source of Truth)

Updated: March 30, 2026
Audience: Operating team, seed investors, implementation planning
Scope: Bengaluru-first execution with broker-led wedge and multi-segment expansion over 24 months

---

## 1. Executive Summary

Valora is a self-learning GIS AI decision agent for real estate, starting in Bengaluru.

Execution strategy:
1. Win with broker productivity and explainable decision intelligence.
2. Expand revenue with usage depth and digital workflows.
3. Layer in developer pilots and NRI investor features after workflow traction.

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

### 2.3 Bengaluru Market Context (Why Bengaluru First)
- Transaction velocity: Bengaluru real estate surging 21% in March 2026; one of India's fastest-growing residential markets.
- IT/tech workforce: High demand from tech professionals for residential properties in the 12 micro-markets.
- NRI investment: Bengaluru is a top NRI investment destination, driving remote diligence demand.
- Developer activity: Premium housing boom and luxury apartment launches in 2026.
- Data density: 42,452 properties, 686,370 buildings, 26,961 POIs already ingested.

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

### 3.4 Audience Feature Map (Codebase-Verified)

Each feature is tagged as `Live` (production-ready) or `Partial` (exists but needs hardening).

| Feature | Status | Brokers | Developers | NRI Investors |
|---|---|---|---|---|
| Chat + GIS Search | Live | Core | Good | Good |
| Onboarding (Bengaluru areas) | Live | Core | Strong | Strong |
| Smart Report (9-section) | Live | Strong | Strong | Critical |
| Digital Employee (Alerts/Tasks/Leads) | Live | Core | Partial | Weak |
| Agent Preferences + Recommendations | Live | Good | Good | Good |
| Learning Loop (feedback) | Live | Core | Good | Good |
| Family Hub (Decision Rooms) | Live | Weak | Weak | Good |
| Locality Reviews (Vastu, Schools, Transport, Safety) | Live | Good | Good | Critical |
| Market Sentiment (investment score, momentum, yield) | Live | Good | Critical | Good |
| Payment/Credits System | Partial | Good | Good | Good |
| Multilingual (6 Indian languages) | Live | Good | Good | Good |
| 3D Map (CesiumJS terrain/visibility) | Live | Good | Critical | Good |
| PDF Report Export | Live | Good | Good | Critical |
| Task Orchestration (multi-step queries) | Live | Good | Good | Partial |

Workability score by audience:
- Brokers: 80-85% — Digital Employee is the wedge; onboarding, reports, and learning loop are production-ready.
- Developers: 55-65% — Market Sentiment and 3D map are strong; B2B billing flows and broader data coverage are gaps.
- NRI Investors: 60-70% — PDF export, locality reviews, and Family Hub are critical; legal/video/currency gaps remain.

---

## 4. Current Product and Data Reality (March 2026)

### 4.1 Product Status
- Grounded chat and report flows: active.
- Spatial analysis stack (terrain, 3D, visibility, sunlight heuristics): active.
- Digital employee workflows: active.
- Credits/pricing system: active.
- Payments: partially productionized (Stripe route exists; some demo/stub paths remain to harden).
- Onboarding modal: active (collects interest type, preferred Bengaluru areas, budget range, language).
- Smart Report pipeline v2: active (9 sections with 24 spatial features, evidence traces, consistency validation).
- Community features: active (Family Hub decision rooms, locality reviews, market sentiment).
- Multilingual UI: active (English, Hindi, Kannada, Tamil, Telugu, Malayalam).
- Learning engine: active (self-learning + enhanced learning + agentic memory across 3 databases).

### 4.2 Data Footprint (Local Snapshot)
- Properties: 42,452
- Buildings: 686,370
- POIs: 26,961
- Roads: 334,784
- Transport stops: 5,384
- Open datasets catalog: 455,066

### 4.3 Architecture Snapshot
- Frontend: React app with chat-first UX, smart tabs, agent control panel, 3D map (CesiumJS).
- Backend: FastAPI server with 14 modular route handler files.
- AI orchestration: 44 modules in `backend/ai/` (intent router, GIS agents, model router, fact verification, section analysis v2, cognitive workflow engine, task orchestration, self-learning, A/B testing).
- Data layer: 16 SQLite databases for domain data, auth, credits, learning, automation, sentiment, pipeline metrics.
- Model providers: Local Ollama by default; cloud escalation via OpenRouter (kimi-k2.5, deepseek-v3.2, glm-5).
- External services: Nominatim (local Docker) for geocoding, Apify for scraping, Stripe/Razorpay for payments.

---

## 5. Prototype Gaps (Prioritized for Execution)

These are the identified gaps from codebase review that must be closed to improve workability for each audience segment.

### 5.1 Broker Gaps (Current: 80-85%)

| # | Gap | Impact | Priority |
|---|---|---|---|
| 1 | No dedicated broker dashboard for lead pipeline/conversion metrics | Reduces broker productivity visibility | High |
| 2 | Team collaboration features partially rolled out | Blocks agency-level adoption | High |
| 3 | No CRM integration (e.g., Salesforce, HubSpot) | Brokers cannot sync existing workflows | Medium |
| 4 | Email channel for alerts exists but needs hardening | Alert reliability risk | Medium |

### 5.2 Developer Gaps (Current: 55-65%)

| # | Gap | Impact | Priority |
|---|---|---|---|
| 1 | No B2B pilot/retainer billing flow (only subscription + top-up exists) | Cannot monetize developer pilots | Critical |
| 2 | No project-level analytics (demand density, competitor pricing by micro-market) | Developers lack launch confidence data | High |
| 3 | No bulk property analysis or batch report generation | Manual work for large projects | High |
| 4 | No API access for developer system integration | Blocks B2B adoption | Medium |
| 5 | Coverage limited to top-12 micro-markets | Developers need broader Bengaluru data | Medium |

### 5.3 NRI Investor Gaps (Current: 60-70%)

| # | Gap | Impact | Priority |
|---|---|---|---|
| 1 | No dedicated NRI onboarding flow | NRI users lack tailored onboarding | High |
| 2 | No property comparison export for offline review | NRI users cannot share/export comparisons | High |
| 3 | No currency conversion or international payment support | Payment barrier for cross-border transactions | Medium |
| 4 | No time zone-aware scheduling for tasks | Task scheduling confusing for NRI users | Medium |
| 5 | No video/virtual tour integration | Remote inspection limitation | Low |

---

## 6. ICP and Segment Sequence (Detailed)

### 6.1 Primary ICP: Bengaluru Brokers (Months 0-12)

**Who:** Brokers and small-to-mid real estate agencies operating in Bengaluru's top 12 micro-markets.

**Profile:**
- Active in: Whitefield, Sarjapur Road, Electronic City, HSR Layout, Koramangala, Indiranagar, Bellandur, Marathahalli, Hebbal, Yelahanka, JP Nagar, Kanakapura Road.
- Typical size: 1-50 agents per agency.
- Deal types: Residential resale and new launches, primarily in the ₹50L-₹3Cr range.
- Tech comfort: Moderate; uses WhatsApp, basic CRM tools, and listing portals.

**Pain points:**
1. Cannot defend property recommendations with verifiable evidence to clients.
2. Manual follow-ups and fragmented lead workflows reduce closure speed.
3. Lack of locality intelligence to justify pricing and locality choices.
4. No automated alerts for new listings matching client criteria.

**Why primary:**
- Fastest cycle for activation and conversion.
- Strong fit with digital employee workflows (alerts, scheduled tasks, lead management).
- Higher repetition supports learning-loop quality.
- Conversion path: Free (50 units) → Pro (1,000 units at Rs 599 launch) → Team (3,000 units at Rs 999 launch).

**Workability: 80-85%**
- Core features live: Digital Employee, Smart Report, Chat + GIS Search, Learning Loop, Onboarding.
- Gaps: No dedicated broker dashboard for lead pipeline/conversion metrics; team collaboration partially rolled out; no CRM integration.

### 6.2 Secondary Segment: Developers and Builder Sales Teams (Months 6-18)

**Who:** Real estate developers and builder sales teams launching projects in Bengaluru.

**Profile:**
- Project sizes: Mid-to-large residential and commercial developments.
- Decision makers: Sales heads, project managers, marketing teams.
- Needs: Micro-market confidence for launch decisions, pricing intelligence, competitive positioning.

**Pain points:**
1. Launch decisions lack micro-market confidence and demand density data.
2. No localized data for pricing, competitor analysis, and buyer sentiment.
3. Manual report generation for investor presentations.

**Motion:** Pilot → Retainer (B2B).

**Workability: 55-65%**
- Strong features: Market Sentiment (investment scores, price momentum, rental yield), 3D map with terrain/visibility, Smart Report ROI Projection and Comparables.
- Gaps: No project-level analytics (demand density, competitor pricing by micro-market); no bulk property analysis or batch report generation; no B2B pilot/retainer billing flow (only subscription + top-up exists); no API access for developer system integration; coverage limited to top-12 micro-markets.

### 6.3 Secondary Segment: NRI and Remote Investors (Months 12-18)

**Who:** Non-Resident Indians and remote investors looking to buy/invest in Bengaluru real estate.

**Profile:**
- Location: Primarily US, UK, Middle East, Singapore, Australia.
- Investment range: ₹50L to ₹5Cr+.
- Decision style: Data-driven, risk-averse, need high-trust evidence.
- Pain: Cannot physically inspect or do due diligence remotely.

**Pain points:**
1. Remote diligence is time-consuming and inconsistent.
2. Cannot verify locality quality (schools, transport, safety, Vastu).
3. No way to collaborate with family in India on property decisions.
4. Payment and legal verification barriers for cross-border transactions.

**Motion:** Report-led trust workflows.

**Workability: 60-70%**
- Critical features: Smart Report with PDF export, Locality Reviews (Vastu, Schools, Transport, Safety), Family Hub (decision rooms for cross-border collaboration), Multilingual support (6 Indian languages), Explainability panels with evidence sources and confidence scores.
- Gaps: No video/virtual tour integration; no legal document or title verification features; no currency conversion or international payment support; no time zone-aware scheduling for tasks; no dedicated NRI onboarding flow; no property comparison export for offline review.

---

## 6.4 Identity and Access Architecture (4-Layer Model)

The system uses a 4-layer architecture to separate concerns cleanly. Each layer operates independently and composes together at runtime.

### Layer 1: Identity Layer — WHO they are

| Role | Value | Description |
|---|---|---|
| Broker | `broker` | Real estate agents/agencies. Deals, clients, listings, workflows. |
| Buyer | `buyer` | Home buyers, investors, NRI users. Can also sell properties. |
| Developer | `developer` | Real estate developers. Project planning, land acquisition, pricing. |
| Admin | `admin` | Internal Valora team (hidden, not in signup) |
| Valora Team | `valora-team` | Valora employees (hidden, not in signup) |

Set at signup. Immutable after onboarding starts. Drives AI persona, dashboard layout, and feature surface.

### Layer 2: Intent — WHAT they want to do

| Intent | Value | Description | Available For |
|---|---|---|---|
| Buy | `buy` | Looking to purchase property | Broker, Buyer |
| Sell | `sell` | Want to list and sell property | Broker, Buyer |
| Both | `both` | Buy and sell - complete transactions | Broker, Buyer |

Selected during onboarding. Determines which features are visible. Seller is NOT a role - it's an intent.

### Layer 3: Workspace — HOW they operate

| Workspace | Value | Description |
|---|---|---|
| Individual | `individual` | Solo operator. Own workspace, own data, own limits. |
| Team | `team` | Agency, developer org, or family unit. Shared workspace with member management. |

- Broker teams → Agency workspace (shared leads, shared alerts, team reports)
- Developer teams → Org workspace (project-level analytics, team dashboards)
- Buyer teams → Family workspace (Family Hub, shared decision rooms, collaborative shortlists)

Workspace type is selected during onboarding. Affects billing (Team tier), member invites, and data sharing scope.

### Layer 4: Workspace Role — WHO can do what

Role-based access within a workspace. Applies only to Team workspaces.

| Permission | Manager | Member |
|---|---|---|
| Manage workspace members | Yes | No |
| Billing and plan changes | Yes | No |
| View all workspace data | Yes | Yes |
| Create/edit shared resources | Yes | Yes |
| Export workspace reports | Yes | Yes |
| Delete workspace resources | Yes | Own only |

Individual workspaces: owner has full access. No member management.

### Layer 5: Subscription Plan — WHAT they can access

Subscription tier. Determines usage limits and feature gates.

| Plan | Units/Month | Launch Price | Team Members |
|---|---:|---:|---|
| Free | 50 | Rs 0 | 1 |
| Pro | 1,000 | Rs 599 | 1 |
| Team | 3,000 | Rs 999 | Up to 10 |

Feature gates by plan:

| Feature | Free | Pro | Team |
|---|---|---|---|
| Alerts | 3 max | Unlimited | Unlimited |
| Scheduled Tasks | 5 max | Unlimited | Unlimited |
| Smart Tabs | Free Analysis only | All 9 tabs | All 9 tabs |
| PDF Export | No | Yes | Yes |
| Team Management | No | No | Yes |
| Email Channel | Disabled | Enabled | Enabled |
| Auto Execution | Confirmation default | Allowed | Allowed |

### Layer 6: AI Layer — HOW the system behaves

| AI Persona | Identity | Behavior Focus |
|---|---|---|
| Broker AI | `broker` | Execution layer. Deals, clients, listings. High frequency. |
| Developer AI | `developer` | Institutional decisions. Project planning, pricing, demand. |
| Buyer AI | `buyer` | Individual decisions. Personal choices, report-driven. |

### Composition at Runtime (Multi-Tenant Model)

```
User = Identity (broker) + Workspace (team) + Role (manager) + Plan (pro) + AI (broker-ai)
```

Example:
- Raj, a broker, signs up as `broker`
- Joins his agency's `team` workspace as `manager`
- Agency is on `Team` plan
- System serves `broker-ai` persona with workspace isolation

### Multi-Tenant Isolation

All data access is scoped by tenant (workspace). No cross-tenant data visibility.

| Resource | Individual | Team |
|----------|------------|------|
| Leads | Own only | Shared within workspace |
| Alerts | Own only | Shared within workspace |
| Reports | Own only | Shared within workspace |
| Market Data | Public | Public + workspace analytics |

---

## 7. Planned Public Interfaces (App Design Spec)

These are planned interfaces for implementation sequencing. They are not yet declared as production-stable APIs.

### 6.1 API Additions
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

### 6.2 Planned Type Contracts
1. `PreferenceProfile`
- Fields: budget range, property type, commute preference, risk tolerance, time horizon, must-have filters

2. `RecommendationResult`
- Fields: rank score, rationale, comparable localities/properties, projected fit

3. `LearningEvent`
- Fields: event type, trigger action, model confidence delta, timestamp

4. `CoverageStatus`
- Fields: locality id/name, freshness timestamp, source count, confidence band

### 6.3 Standard Metadata Fields
- `confidence_score`
- `evidence_sources`
- `freshness_ts`
- `risk_flags`

### 6.4 Live API Surface (Codebase-Verified)

**Chat and Core Analysis:**
- `POST /api/chat`, `POST /api/chat/stream`
- `GET /api/area/analyze`, `GET /api/viewport/analyze`
- `POST /api/building/analyze`

**Agent APIs:**
- `POST /api/agent/preferences/upsert` (Live)
- `GET /api/agent/recommendations` (Live)
- `POST /api/agent/feedback` (Live)
- `GET /api/market/coverage` (Live)

**Digital Employee APIs:**
- `/api/digital-employee/summary`, `/alerts`, `/scheduled-tasks`, `/leads`, `/activity`
- `/api/digital-employee/commands/parse`, `/commands/parse-and-execute`
- `/api/digital-employee/scheduler/status`, `/scheduler/run-once`

**Smart Report APIs:**
- `GET /api/smart-report/generate`, `/verdict`, `/market`, `/risk`
- `POST /api/smart-report/export/pdf`, `/export/section`, `/share`
- `POST /api/smart-report/generate-detailed`
- `GET /api/smart-report/investment-analysis`

**Family Hub APIs:**
- `POST /api/family/session`, `GET /api/family/sessions`
- `POST /api/family/session/{id}/invite`, `/watchlist`, `/vote`
- `GET /api/family/session/{id}/vote-summary`, `/timeline`
- `POST /api/family/session/{id}/share`

**Locality Review APIs:**
- `POST /api/reviews/locality`, `GET /api/reviews/locality/{id}`
- `GET /api/reviews/locality/{id}/stats`
- `POST /api/reviews/{type}/{id}/helpful`

**Market Sentiment APIs:**
- `GET /api/sentiment/locality/{id}`, `/city/{city}`, `/investment-score/{id}`
- `GET /api/sentiment/price-momentum/{id}`, `/price-history/{id}`, `/rental-yield/{id}`
- `GET /api/sentiment/trending`, `/trends/{id}`

**Task Orchestration APIs:**
- `POST /api/tasks/decompose`
- `GET /api/tasks/execution/{id}`, `/execution/{id}/graph`
- `GET /api/tasks/templates`, `/metrics`, `/statistics`, `/monitoring/realtime`

**Feedback APIs:**
- `POST /api/feedback/submit`, `/auto-save`
- `GET /api/feedback/credits`, `/history`

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

### 7.3 Top-up Packs

| Pack | Units | Launch Price | Regular Price |
|---|---:|---:|---:|
| Starter | 100 | Rs 59 | Rs 299 |
| Standard | 300 | Rs 139 | Rs 699 |
| Bulk | 1,000 | Rs 399 | Rs 1,999 |

### 7.4 Tier Feature Gating (Current)

| Feature | Free | Pro | Team |
|---|---|---|---|
| Alerts | Up to 3 | Unlimited | Unlimited |
| Scheduled Tasks | Up to 5 | Unlimited | Unlimited |
| Email Channel | Disabled | Enabled | Enabled |
| Auto Execution | Confirmation default | Allowed | Allowed |
| Smart Tabs | Free Analysis only | All 9 tabs | All 9 tabs |
| PDF Export | No | Yes | Yes |
| Team Management | No | No | Partial |

### 7.5 Phase-Specific Monetization Focus
- Months 0-6: Free to Pro conversion + top-up behavior.
- Months 6-12: Team adoption + workflow-linked upsell.
- Months 12-18: Developer pilot ACV expansion + NRI investor monetization.

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

### 8.3 Guardrail Metrics
1. Billing incident count
2. Data freshness SLA breaches
3. Recommendation confidence below threshold
4. Time-to-first-value after onboarding

### 8.4 Dashboard Views
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
| Phase 2 | Months 6-12 | Learning-loop improvements, recommendation confidence, conversion hooks, B2B billing flows | Start developer paid pilots | Free to Pro + pilot count | Billing/tier inconsistency |
| Phase 3 | Months 12-18 | Deeper automation, report quality, team controls, NRI-focused features (PDF export hardening, comparison export) | Scale broker teams and B2B repeatability; NRI investor acquisition | Team expansion + retention | Trust and explainability gaps |

### 9.1 Audience-Specific Roadmap Milestones

**Brokers (Phase 1-2):**
- Month 3: Repeatable onboarding flow with first-week activation checklist.
- Month 6: Free to Pro conversion engine proven in top-12 micro-markets.
- Month 9: Team tier fully rolled out with agency-level features.
- Month 12: Measurable workflow-led retention; broker case studies published.

**Developers (Phase 2-3):**
- Month 8: First paid developer pilot closed.
- Month 12: B2B billing flow (pilot to retainer) productionized.
- Month 15: Project-level analytics and batch report generation available.
- Month 18: API access for developer system integration.

**NRI Investors (Phase 3):**
- Month 12: PDF export and shareable report links hardened.
- Month 15: NRI-focused onboarding flow with currency conversion awareness.
- Month 18: Property comparison export for offline review.

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

### 10.5 Audience Workability Gaps
Risk:
- Features not fully ready for secondary audiences (developers, NRI) delay expansion.

Mitigation:
1. Track per-audience feature completeness score monthly.
2. Prioritize B2B billing flows (blocks developer segment).
3. Harden PDF export and shareable links (blocks NRI segment).

---

## 11. Revenue Trajectory Framing

### 11.1 Base-Case Logic
Revenue quality depends on:
1. Workflow activation (drives retention)
2. Free to Pro conversion (drives predictable MRR)
3. Usage depth (drives top-up expansion)
4. B2B renewals (drives ARR quality)

### 11.2 Revenue Mix by Audience (Target)

| Segment | Month 12 Revenue Share | Month 18 Revenue Share |
|---|---|---|
| Brokers (Pro + Team) | 70-80% | 45-55% |
| Developers (B2B) | 10-15% | 25-30% |
| NRI Investors (Pro + Top-up) | 5-10% | 15-20% |

### 11.3 Example Operating Targets (Illustrative, execution-dependent)
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
6. Per-audience feature workability scores and gap tracking.

### 12.2 What Remains for Execution Pass
1. Endpoint implementation and schema validation for planned APIs.
2. Database migrations for preference and learning-event persistence.
3. Billing hardening and rollout cleanup (remove demo/stub paths from production).
4. Dashboard instrumentation and alerting thresholds.
5. B2B billing flow implementation (pilot to retainer for developers).
6. Team tier full rollout with agency-level collaboration features.
7. NRI-focused feature hardening (PDF export, shareable links, comparison export).

---

## 13. Assumptions and Defaults

1. Immediate narrative audience: seed investors.
2. Primary wedge: brokers in Bengaluru.
3. Product direction: all-rounder self-learning GIS AI agent.
4. Planning horizon: 24 months.
5. This pass updates only `docs/BUSINESS.md` and `docs/pitch.md`.
6. Monetization model remains subscription + usage + B2B pilots.
7. Existing architecture remains valid and is not rewritten here.
8. Per-audience workability scores are derived from codebase review (March 30, 2026) and will be refreshed quarterly.
