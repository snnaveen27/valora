# Valora Architecture

> System architecture, production controls, and 24-month technical roadmap (Bengaluru-first).

Updated: March 2026
Status: Active source of truth
Primary owner: Engineering

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Core Principles](#2-core-principles)
3. [Runtime Topology](#3-runtime-topology)
4. [Canonical Request Lifecycle](#4-canonical-request-lifecycle)
5. [Identity and Access Architecture](#5-identity-and-access-architecture)
6. [Data Ingestion Architecture](#6-data-ingestion-architecture)
7. [Data and Storage Architecture](#7-data-and-storage-architecture)
8. [API Surface (Live vs Planned)](#8-api-surface-live-vs-planned)
9. [Learning and Recommendation Architecture](#9-learning-and-recommendation-architecture)
10. [Digital Employee Runtime](#10-digital-employee-runtime)
11. [Community and Collaboration Features](#11-community-and-collaboration-features)
12. [Smart Report and Analysis Pipeline](#12-smart-report-and-analysis-pipeline)
13. [Task Orchestration](#13-task-orchestration)
14. [Production Readiness Controls](#14-production-readiness-controls)
15. [24-Month Architecture Roadmap](#15-24-month-architecture-roadmap)
16. [Testing and Verification Matrix](#16-testing-and-verification-matrix)
17. [Known Gaps and Decision Log](#17-known-gaps-and-decision-log)

---

## 1. Purpose and Scope

This document defines the production architecture for Valora as a Bengaluru-first, GIS-native AI decision system.

In scope:
- Live backend/frontend architecture and data path.
- Ingestion, recommendation, and automation runtime.
- Live and planned API contracts.
- Production reliability, security, and observability controls.

Out of scope:
- Sales narrative and pricing strategy details (see `docs/BUSINESS.md`).

---

## 2. Core Principles

1. Truth-first responses
- LLM output is grounded by deterministic GIS/property facts.

2. Reliability over novelty
- Production uptime, billing consistency, and explainability are prioritized before feature expansion.

3. Single operational plane
- Digital employee is implemented in the same stack (auth, usage, observability), not as a separate runtime.

4. Explicit status boundaries
- APIs and modules are always tagged as `Live` or `Planned`.

5. Bengaluru-first quality gating
- Top-12 micro-market coverage quality is enforced before broader expansion.

---

## 3. Runtime Topology

### 3.1 High-Level Components

1. Frontend
- React app with chat-first UX, smart tabs, agent control panel, 3D map (CesiumJS), and community features.
- Multilingual support (6 Indian languages).
- Three-panel layout: Smart Report | Map | Chat.

2. Backend API
- FastAPI server (`backend/server.py`) with 14 modular route handler files.
- Direct server.py endpoints for geocode, tiles, buildings, ingestion, metrics.

3. AI orchestration (44 modules in `backend/ai/`)
- Intent router + GIS agents + model router + fact verification.
- Section analysis pipeline v2 with consistency validation.
- Cognitive workflow engine for adaptive reasoning.
- Task orchestration with decomposition and parallel execution.
- Self-learning and enhanced learning engines.
- A/B testing framework for prompt optimization.

4. Data layer
- 16 SQLite databases for domain data, auth, credits, learning, automation, sentiment, and pipeline metrics.
- WAL mode on high-traffic databases for concurrent access.

5. Background workers
- In-process scheduler for digital employee scans and due task execution.
- Task orchestrator for multi-stage query execution.

6. Model providers
- Local Ollama by default.
- Cloud models: kimi-k2.5:cloud, deepseek-v3.2:cloud, glm-5:cloud via OpenRouter.
- Rules-based routing for model selection by complexity and intent.

7. External services
- Nominatim (local Docker) for geocoding.
- Apify for external property scraping.
- Stripe/Razorpay for payments.

### 3.2 Topology Diagram

```text
Frontend (React + CesiumJS 3D)
   -> FastAPI (/api/*, 14 route modules)
      -> Intent Router + GIS Agents + Model Router + Verifier
      -> Section Analysis Pipeline v2 (feature-first, LLM-second)
      -> Task Orchestrator (decompose → parallel execute → synthesize)
      -> Domain services:
         - Digital Employee (alerts, tasks, leads)
         - Smart Reports (9-section analysis)
         - Family Hub (decision-rooms, voting)
         - Locality Reviews
         - Market Sentiment
         - Agent Preferences + Recommendations
      -> 16 SQLite stores (valora, users, credits, learning, digital_employee,
         agent_state, conversation_memory, pricing, sentiment, pipeline_metrics...)
      -> Background scheduler (alerts/tasks/scans)
      -> Model inference: Ollama local / cloud escalation
      -> External: Nominatim geocoder, Apify scraper, Stripe payments
```

---

## 4. Canonical Request Lifecycle

1. Request intake
- Auth, input parsing, and context assembly.

2. Intent and task decomposition
- IntentRouter classifies query and identifies execution path.

3. Fact gathering
- GIS agents query deterministic data services.

4. Model routing
- Complexity-aware routing selects local or cloud model.

5. Response generation
- Streaming or non-stream response generation.

6. Post-generation verification
- Fact verifier checks key claims against grounded data.

7. Response metadata
- Emit `confidence_score`, `evidence_sources`, `freshness_ts`, `risk_flags` where available.

8. Learning event recording
- Query outcome and feedback signals are persisted for future adaptation.

---

## 5. Identity and Access Architecture

> Live: All layers implemented in codebase and documented in `BUSINESS.md` section 6.4.

### 5.1 4-Layer Model

The system uses a 4-layer architecture to separate concerns cleanly:

#### Layer 1: Identity — WHO they are

| Role | Value | Description |
|------|-------|-------------|
| Broker | `broker` | Deals, clients, listings, workflows. |
| Developer | `developer` | Project planning, land acquisition, pricing. |
| Buyer | `buyer` | Home buyers, investors, NRI. |
| Admin | `admin` | Internal (hidden) |
| Valora Team | `valora-team` | Internal (hidden) |

Set at signup via `job_role` field. Drives AI persona and dashboard layout.

#### Layer 2: Workspace — HOW they operate

| Workspace | Value | Description |
|-----------|-------|-------------|
| Individual | `individual` | Solo operator. Own workspace, own data. |
| Team | `team` | Agency/developer org/family. Shared workspace. |

Selected during onboarding. Stored in `workspace_type` field.

#### Layer 3: Workspace Role — WHO can do what

| Permission | Manager | Member |
|------------|---------|--------|
| Manage members | Yes | No |
| Change plan | Yes | No |
| View all data | Yes | Yes |
| Create shared resources | Yes | Yes |
| Export reports | Yes | Yes |
| Delete resources | Yes | Own only |

Individual workspaces: owner is always `manager`. Stored in `workspace_role` field.

#### Layer 4: Subscription Plan — WHAT they can access

| Plan | Units/Month | Team Members |
|------|------------|-------------|
| Free | 50 | 1 |
| Pro | 1,000 | 1 |
| Team | 3,000 | Up to 10 |

### 5.3 Data Isolation (Privacy by Design)

> Critical: Prevents data leakage between segments. Live implementation.

| Issue | Fix |
|-------|------|
| Brokers see other brokers' leads | ❌ Privacy violation → Leads scoped to workspace |
| Developers see competitor data | ❌ Anti-competitive → Competitor data blocked |
| Buyers see other buyers' data | ❌ Privacy violation → Family Hub isolation |

### 5.4 Code Execution Sandbox (AI Runtime)

Separation of AI code/script execution from user data isolation.

- AI-generated code runs in isolated container
- Time-bounded execution
- No filesystem access
- Network restrictions
- Memory limits

This is distinct from multi-tenant data isolation.

### 5.5 Canonical Ingestion Metadata Contract

| File | Purpose |
|------|---------|
| `src/config/roles.js` | RBAC configuration, permissions, feature flags |
| `src/components/RoleGuard.jsx` | Route/feature protection component |
| `src/contexts/AuthContext.jsx` | Exposes identity, workspace, role, plan, permissions |
| `src/components/OnboardingModal.jsx` | 5-step identity + workspace selection |
| `src/components/SignupPage.jsx` | 3 focused roles + 2 hidden internal roles |
| `backend/auth/user_auth.py` | User model with workspace fields |
| `backend/routes/auth_routes.py` | Signup/update API with workspace support |

### 5.3 Composition at Runtime

```
User = Identity (broker) + Workspace (team) + Role (manager) + Plan (pro)
```

---

## 6. Data Ingestion Architecture

### 5.1 Goals

1. Keep market data fresh and auditable.
2. Preserve source provenance.
3. Block low-quality records from polluting serving tables.
4. Provide ingestion quality signals to downstream APIs.

### 5.2 Pipeline Stages

1. Source acquisition
- Scrapers/connectors pull raw listings and market data.

2. Raw staging
- Raw records persisted with source attribution.

3. Validation
- Required fields and sanity checks (coordinates, price, locality).

4. Dedup + merge
- Property/listing identity logic and price-history updates.

5. Quarantine
- Invalid records stored with explicit reason and error payload.

6. Publish
- Valid data written to core serving tables.

7. Quality metrics
- Per-run quality score and quarantine/error counts recorded.

### 5.3 Live Ingestion Components

`Live`
- `backend/scrapers/production_ingestion.py`
  - batch ingest
  - duplicate handling
  - ingestion_log
  - price history
  - location analytics
  - quarantine table
  - quality metrics table

`Live`
- `backend/services/apify_service.py`
  - external scrape orchestration and status snapshots.

### 5.4 Canonical Ingestion Metadata Contract

The architecture standard for records and downstream payloads:
- `source`
- `freshness_ts`
- `confidence_score`
- `evidence_sources`
- `risk_flags`

Current state:
- Partially available across modules.
- Full uniform enforcement remains roadmap work.

### 5.5 Coverage Gate Policy (Bengaluru Top-12)

Coverage is evaluated per locality:
1. Listing volume
2. Source diversity
3. Freshness window
4. Confidence band (`high`/`medium`/`low`)

`Live`
- `/api/market/coverage` provides current top-12 coverage summary.

---

## 6. Data and Storage Architecture

### 6.1 Core Databases (Storage: `storage/database/`)

1. `valora.db`
- Properties, POIs, places, buildings, roads, transport, analytics, ingestion logs.
- Primary database referenced by ~50+ modules.

2. `users.db`
- User identities, credentials, roles/tiers, usage audit.

3. `valora_credits.db`
- Credit balances, usage and payment mappings.

4. `digital_employee.db`
- Alerts, scheduled tasks, leads, automation activity and runs.

5. `agent_state.db`
- Agent preference profiles and recommendation feedback events.

### 6.2 Learning and Memory Databases

6. `model_performance.db`
- Model latency, success rates, token usage per model/intent. Used by model router.

7. `enhanced_learning.db`
- Cross-session learning, semantic pattern clustering, negative learning from failures.

8. `self_learning.db`
- Base learning engine for pattern recognition and query improvement.

9. `agentic_memory.db`
- Long-term memory for AI agent operations.

10. `valora_memory.db`
- User feedback records and session memory.

### 6.3 Specialized Databases

11. `conversation_memory.db`
- Chat thread history, user queries, and conversation context.

12. `pricing.db`
- Pricing configuration (tiers, action costs, top-up packs).

13. `ab_testing.db`
- Prompt variant conversion rates and experiment results.

14. `feature_drift.db`
- Feature drift detection tracking computed features vs historical baselines.

15. `pipeline_metrics.db`
- Durable metrics for section analysis v2 pipeline (latency, cache, cost, confidence).

16. `review_queue.db`
- Human-in-the-loop review queue for pipeline results needing verification.

### 6.4 Storage Access Pattern

- App services use a thread-local SQLite pool for WAL-safe concurrent access.
- Query service centralizes read paths for GIS and property retrieval.
- Database path configuration centralized in `backend/config.py`.
- WAL mode enabled on high-traffic databases (credits, model_performance, learning).

---

## 7. API Surface (Live vs Planned)

## 7.1 Chat and Core Analysis

`Live`
1. `POST /api/chat`
2. `POST /api/chat/stream`
3. `GET /api/area/analyze`
4. `GET /api/viewport/analyze`
5. `POST /api/building/analyze`

## 7.2 Agent APIs

`Live`
1. `POST /api/agent/preferences/upsert`
- Upserts normalized preference profile and increments profile version.

2. `GET /api/agent/recommendations`
- Returns ranked recommendations with rationale and metadata.

3. `POST /api/agent/feedback`
- Records recommendation action (`save`, `reject`, `contacted`, `closed`) as learning signal.

4. `GET /api/market/coverage`
- Returns top-12 Bengaluru coverage status with freshness/confidence band.

## 7.3 Digital Employee APIs

`Live`
1. `/api/digital-employee/summary`
2. `/api/digital-employee/alerts` and `/alerts/{id}`
3. `/api/digital-employee/scheduled-tasks` and `/scheduled-tasks/{id}`
4. `/api/digital-employee/leads` and `/leads/{id}`
5. `/api/digital-employee/activity`
6. `/api/digital-employee/commands/parse`
7. `/api/digital-employee/commands/parse-and-execute`
8. `/api/digital-employee/scheduler/status`
9. `/api/digital-employee/scheduler/run-once`

Compatibility aliases remain live under:
- `/api/automations/*`
- `/api/leads/*`

## 7.4 Ingestion APIs

`Live`
1. `GET /api/ingestion/status`
2. `GET /api/scrape/platforms`
3. `POST /api/scrape/{platform}/start`

`Planned`
1. `GET /api/ingestion/quality`
- Per-run quality and quarantine metrics.

2. `GET /api/ingestion/quarantine`
- Paginated quarantine inspection endpoint.

3. `POST /api/ingestion/reprocess`
- Controlled replay of quarantined records.

## 7.5 Smart Report APIs

`Live`
1. `GET /api/smart-report/generate`
- Generate comprehensive 9-section report for a property/locality.

2. `GET /api/smart-report/verdict`
- Decision verdict (Buy/Hold/Avoid) only.

3. `GET /api/smart-report/market`
- Market snapshot section.

4. `GET /api/smart-report/risk`
- Risk analysis section.

5. `POST /api/smart-report/export/pdf`
- Export report as PDF.

6. `POST /api/smart-report/export/section`
- Export single section report.

7. `POST /api/smart-report/share`
- Create shareable report link.

8. `POST /api/smart-report/generate-detailed`
- Detailed AI-powered report (credits required).

9. `GET /api/smart-report/investment-analysis`
- Investment analysis with ROI projections.

## 7.6 Family Hub (Decision-Room) APIs

`Live`
1. `POST /api/family/session`
- Create a decision-room session.

2. `GET /api/family/sessions`
- List user sessions.

3. `GET /api/family/session/{id}`
- Get session detail with members and watchlist.

4. `PUT /api/family/session/{id}`
- Update session metadata.

5. `DELETE /api/family/session/{id}`
- Archive session.

6. `POST /api/family/session/{id}/invite`
- Invite member by email/phone.

7. `POST /api/family/session/{id}/watchlist`
- Add property to watchlist.

8. `POST /api/family/session/{id}/vote`
- Cast vote on a property.

9. `GET /api/family/session/{id}/vote-summary`
- Aggregate vote summary.

10. `GET /api/family/session/{id}/timeline`
- Activity timeline.

11. `POST /api/family/session/{id}/share`
- Generate share link for non-users.

## 7.7 Locality Review APIs

`Live`
1. `POST /api/reviews/locality`
- Submit verified locality review (Vastu, Schools, Transport, Safety categories).

2. `GET /api/reviews/locality/{id}`
- Get reviews for a locality.

3. `GET /api/reviews/locality/{id}/stats`
- Aggregated review statistics.

4. `PUT /api/reviews/locality/{id}`
- Update review.

5. `DELETE /api/reviews/locality/{id}`
- Delete review.

6. `POST /api/reviews/{type}/{id}/helpful`
- Mark review as helpful.

## 7.8 Market Sentiment APIs

`Live`
1. `GET /api/sentiment/locality/{id}`
- Locality sentiment score (5 credits).

2. `GET /api/sentiment/city/{city}`
- City-level sentiment (5 credits).

3. `GET /api/sentiment/investment-score/{id}`
- Investment score with breakdown (5 credits).

4. `GET /api/sentiment/price-momentum/{id}`
- Price momentum indicator (free).

5. `GET /api/sentiment/price-history/{id}`
- Historical price data (free).

6. `GET /api/sentiment/rental-yield/{id}`
- Rental yield estimate (free).

7. `GET /api/sentiment/trending`
- Trending localities (free).

8. `GET /api/sentiment/trends/{id}`
- Historical trend analysis (10 credits).

## 7.9 Task Orchestration APIs

`Live`
1. `POST /api/tasks/decompose`
- Decompose complex query into sub-tasks.

2. `GET /api/tasks/execution/{id}`
- Task execution status.

3. `GET /api/tasks/execution/{id}/graph`
- Task dependency graph.

4. `GET /api/tasks/templates`
- List task templates.

5. `GET /api/tasks/metrics`
- Task system metrics.

6. `GET /api/tasks/statistics`
- Orchestrator statistics.

7. `GET /api/tasks/monitoring/realtime`
- Real-time execution stats.

## 7.10 Feedback APIs

`Live`
1. `POST /api/feedback/submit`
- Submit feedback and earn credits.

2. `POST /api/feedback/auto-save`
- Auto-save feedback draft.

3. `GET /api/feedback/credits`
- Feedback credit balance.

4. `GET /api/feedback/history`
- Feedback submission history.

---

## 8. Learning and Recommendation Architecture

### 8.1 Live Learning Inputs

1. Query outcomes from chat pipeline.
2. Model performance logs for routing.
3. Agent feedback events from `/api/agent/feedback`.
4. Conversation/session memory.

### 8.2 Recommendation Metadata Contract

Each recommendation is expected to include:
- `confidence_score`
- `evidence_sources`
- `freshness_ts`
- `risk_flags`

### 8.3 Planned Enhancements

`Planned`
1. Unified cross-service confidence calibrator.
2. Feature-level attribution in recommendation payloads.
3. Better freshness propagation from ingestion to all downstream responses.

---

## 9. Digital Employee Runtime

### 9.1 Runtime Model

Digital employee workflows run inside existing Valora auth, credits, and API plane.

### 9.2 Capabilities

`Live`
1. Alerts with tier-based limits.
2. Scheduled tasks and execution logging.
3. Lead CRUD and activity feeds.
4. Chat command parse-and-execute path.

### 9.3 Tier Policy (Current)

1. Alerts
- Free: up to 3
- Pro: unlimited

2. Scheduled tasks
- Free: up to 5
- Pro: unlimited

3. Email channel
- Free: disabled
- Pro: enabled

4. Auto execution
- Free: confirmation default
- Pro: allowed

---

## 10. Community and Collaboration Features

### 10.1 Family Hub (Decision-Room)

Multi-stakeholder buying workflow for families and groups.

`Live`
1. Session-based decision rooms with invite system.
2. Property watchlist with per-property voting (approve/reject/undecided).
3. Member roles and permission levels.
4. Activity timeline for session audit trail.
5. Shareable links for non-registered participants.

Implementation:
- `backend/routes/family_routes.py`
- `src/components/community/FamilyHub.jsx`
- `src/components/community/FamilyVotingPanel.jsx`
- `src/components/community/FamilyWatchlist.jsx`
- `src/services/familyApi.js`

### 10.2 Locality Reviews

Verified resident reviews with India-specific categories.

`Live`
1. Review categories: Vastu, Schools, Transport, Safety, Parks, Noise.
2. Verified resident proof mechanism.
3. Helpful/not-helpful voting.
4. Aggregated statistics per locality.

Implementation:
- `backend/routes/review_routes.py`
- `src/components/community/LocalityReviews.jsx`
- `src/components/community/ReviewForm.jsx`
- `src/services/reviewApi.js`

### 10.3 Market Sentiment Engine

Supporting intelligence layer for market mood and investment signals.

`Live`
1. Locality and city-level sentiment scoring.
2. Investment score with multi-factor breakdown.
3. Price momentum, rental yield, days-on-market indicators.
4. Trending localities detection.
5. Historical trend analysis.

Implementation:
- `backend/routes/sentiment_routes.py`
- `backend/services/sentiment_engine.py`
- `src/components/community/SentimentDashboard.jsx`
- `src/services/sentimentApi.js`

---

## 11. Smart Report and Analysis Pipeline

### 11.1 Section Analysis Pipeline (v2)

Feature-first, LLM-second architecture for property analysis.

`Live`
1. 9 report sections: Decision Verdict, Market Snapshot, Spatial Intelligence, Risk Analysis, ROI Projection, Comparables, Strategy, Data Transparency, Client Pitch.
2. Deterministic feature computation before LLM calls (24 spatial features).
3. Rules-based intent router (<5ms latency).
4. Consistency validator detects contradictions between sections.
5. Evidence trace system: every claim has traceable source, value, timestamp, confidence.
6. Cognitive workflow engine for adaptive reasoning.

Implementation:
- `backend/ai/section_pipeline_v2.py`
- `backend/ai/consistency_validator.py`
- `backend/ai/cognitive_workflow_engine.py`
- `backend/ai/spatial_feature_engine.py`
- `backend/ai/multi_domain_specialists.py`
- `backend/routes/smart_report_routes.py`
- `backend/services/report_generator.py`

### 11.2 Model Assignment

Rules-based routing (no model) → `valora-ai-mini` for section analysis → `valora-ai-pro` for synthesis → cloud fallback.

Performance targets:
- P95 cached: <3s
- P95 fresh: <6s
- Hallucination rate: <2%
- Cost per query: <$0.005

### 11.3 Frontend Components

- `src/components/SmartPanel.jsx` - Analysis panel with tab system
- `src/components/SmartTabsContainer.jsx` - Tiered tab access (889 lines)
- `src/components/smart_report/DecisionVerdictTab.jsx`
- `src/components/smart_report/RiskAnalysisTab.jsx`
- `src/components/CinemaOverlay.jsx` - Cinematic narration mode

---

## 12. Task Orchestration

### 12.1 Architecture

`Live`
1. NLP-based task decomposition from complex queries.
2. Template library for common multi-step workflows.
3. Dependency graph resolution and parallel execution.
4. Real-time progress tracking (5-stage: understand → plan → execute → validate → synthesize).
5. Feature flags for progressive rollout.

Implementation:
- `backend/ai/task_orchestrator.py`
- `backend/ai/task_decomposer.py`
- `backend/ai/task_templates.py`
- `backend/ai/task_monitor.py`
- `backend/ai/task_graph.py`
- `backend/ai/multi_stage_executor.py`
- `backend/ai/parallel_executor.py`
- `backend/routes/task_routes.py`

### 12.2 Frontend Integration

- `src/components/TaskProgressBar.jsx` - Multi-stage execution display
- `src/components/TopTaskBanner.jsx` - Floating progress banner
- `src/components/ScenarioSimulator.jsx` - What-if scenario execution

---

## 13. Production Readiness Controls

### 13.1 Reliability

`Live`
1. Circuit breaker behavior for model providers.
2. Request timing middleware.
3. Caching and fallback responses.
4. Scheduler lifecycle management on startup/shutdown.
5. Backward-compatible auth DB column migration on startup (`users` schema safety).

### 13.2 Observability

`Live`
1. `/api/metrics` summary endpoint.
2. Endpoint-level metrics and verifier metrics exports.

`Planned`
1. Ingestion SLO dashboards (freshness lag, quarantine ratio).
2. Locality-level confidence and freshness alerting.

### 13.3 Security

`Live`
1. JWT auth for protected routes.
2. Role-based checks for admin operations.
3. CORS origin validation.

`Planned`
1. Endpoint-specific throttling for high-risk automation commands.
2. Secret rotation runbook and periodic key audit automation.

### 13.4 Billing Integrity

`Live`
1. Credit checks and deductions in chat path.
2. Tier-aware feature gating.

`Planned`
1. Cross-table billing reconciliation job.
2. Contract tests for pricing/tier consistency across APIs.

---

## 14. 24-Month Architecture Roadmap

### Phase 1 (Months 0-6)

1. Stabilize Bengaluru top-12 data quality and ingestion reliability.
2. Enforce recommendation metadata contract in all core responses.
3. Reduce runtime coupling in `server.py` through domain route ownership.

### Phase 2 (Months 6-12)

1. Strengthen recommendation-learning loop and confidence calibration.
2. Add ingestion quality and quarantine inspection APIs.
3. Harden billing consistency checks.

### Phase 3 (Months 12-18)

1. Expand team controls and agency-level collaboration features.
2. Improve automation execution safety and observability.
3. Introduce stronger model/provider resilience policies.
4. NRI-focused features: PDF export hardening, shareable report links, comparison export.

### Phase 4 (Months 18-24)

1. B2B billing flow hardening (pilot to retainer for developers).
2. Replication-ready ingestion and coverage gating blueprint for next city.
3. SLO-backed operations for data freshness and recommendation trust.
4. Project-level analytics and batch report generation for developers.

---

## 15. Testing and Verification Matrix

### 15.1 API Contract Tests

1. Validate all `Live` endpoints and auth behavior.
2. Verify recommendation payload includes contract metadata keys.
3. Validate profile version behavior in preferences upsert/recommendations.

### 15.2 Ingestion Tests

1. Validation rejects malformed records.
2. Quarantine receives invalid records with reason.
3. Quality metrics are persisted per run.
4. Duplicate handling and price history remain stable.

### 15.3 Reliability Tests

1. Provider fallback behavior under failure.
2. Scheduler start/stop health checks.
3. Streaming response behavior under cancellation.

### 15.4 Documentation Integrity Checks

1. No mixed status claims (`Live` vs `Planned`).
2. No stale date/version markers.
3. Internal section links resolve.

---

## 16. Known Gaps and Decision Log

### 16.1 Known Technical Gaps

1. Ingestion freshness/confidence propagation is not fully standardized across all response surfaces.
2. Ingestion quality and quarantine are persisted but not yet fully exposed via dedicated APIs.
3. `server.py` still hosts many legacy endpoints and should continue moving to domain routers.
4. Billing has demo/stub paths that need removal from production runtime.
5. Team collaboration features are partially rolled out (no member invitation workflow, no shared watchlists).

### 16.2 Prototype Feature Gaps (Audience-Blocking)

**Broker Gaps:**
1. No dedicated broker dashboard for lead pipeline/conversion metrics.
2. Email channel for alerts exists but needs hardening for production reliability.

**Developer Gaps:**
1. No B2B pilot/retainer billing flow — only subscription + top-up exists.
2. No project-level analytics (demand density, competitor pricing by micro-market).
3. No bulk property analysis or batch report generation.
4. No API access for developer system integration.

**NRI Investor Gaps:**
1. No dedicated NRI onboarding flow with currency conversion awareness.
2. No property comparison export for offline review.
3. No time zone-aware scheduling for tasks.

### 16.3 Decision Log (Current)

1. Keep single-runtime digital employee architecture.
2. Keep Bengaluru top-12 as quality gate before broader expansion.
3. Keep architecture doc explicit about `Live` vs `Planned` to prevent operational confusion.
4. Enterprise/institutional features deferred — prototype focus on Brokers, Developers, NRI.

---

Valora architecture is now production-readiness-first with explicit ingestion, recommendation, and reliability boundaries.
