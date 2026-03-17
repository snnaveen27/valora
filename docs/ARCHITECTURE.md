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
5. [Data Ingestion Architecture](#5-data-ingestion-architecture)
6. [Data and Storage Architecture](#6-data-and-storage-architecture)
7. [API Surface (Live vs Planned)](#7-api-surface-live-vs-planned)
8. [Learning and Recommendation Architecture](#8-learning-and-recommendation-architecture)
9. [Digital Employee Runtime](#9-digital-employee-runtime)
10. [Production Readiness Controls](#10-production-readiness-controls)
11. [24-Month Architecture Roadmap](#11-24-month-architecture-roadmap)
12. [Testing and Verification Matrix](#12-testing-and-verification-matrix)
13. [Known Gaps and Decision Log](#13-known-gaps-and-decision-log)

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
- React app with chat-first UX, smart tabs, and agent control panel.

2. Backend API
- FastAPI server (`backend/server.py`) with modular route handlers.

3. AI orchestration
- Intent router + GIS agents + model router + fact verification.

4. Data layer
- SQLite databases for domain data, auth, credits, learning, and automation state.

5. Background workers
- In-process scheduler for digital employee scans and due task execution.

6. Model providers
- Local Ollama by default.
- Optional cloud escalation (OpenRouter/Ollama cloud) based on route and policy.

### 3.2 Topology Diagram

```text
Frontend (React)
   -> FastAPI (/api/*)
      -> Intent + GIS + Model Router + Verifier
      -> Domain services (Digital Employee, Reports, Preferences)
      -> SQLite stores (valora, users, credits, learning, digital_employee, agent_state)
      -> Background scheduler (alerts/tasks)
      -> Local/Ollama cloud/OpenRouter inference
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

## 5. Data Ingestion Architecture

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

### 6.1 Core Databases

1. `valora.db`
- Properties, POIs, places, buildings, roads, transport, analytics, ingestion logs.

2. `users.db`
- User identities, credentials, roles/tiers, usage audit.

3. `valora_credits.db`
- Credit balances, usage and payment mappings.

4. `digital_employee.db`
- Alerts, scheduled tasks, leads, automation activity and runs.

5. `agent_state.db`
- Agent preference profiles and recommendation feedback events.

6. Learning stores (`model_performance.db`, `enhanced_learning.db`, `valora_memory.db`, others)
- Model routing optimization and behavior memory.

### 6.2 Storage Access Pattern

- App services use a thread-local SQLite pool for WAL-safe concurrent access.
- Query service centralizes read paths for GIS and property retrieval.

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

## 10. Production Readiness Controls

### 10.1 Reliability

`Live`
1. Circuit breaker behavior for model providers.
2. Request timing middleware.
3. Caching and fallback responses.
4. Scheduler lifecycle management on startup/shutdown.
5. Backward-compatible auth DB column migration on startup (`users` schema safety).

### 10.2 Observability

`Live`
1. `/api/metrics` summary endpoint.
2. Endpoint-level metrics and verifier metrics exports.

`Planned`
1. Ingestion SLO dashboards (freshness lag, quarantine ratio).
2. Locality-level confidence and freshness alerting.

### 10.3 Security

`Live`
1. JWT auth for protected routes.
2. Role-based checks for admin operations.
3. CORS origin validation.

`Planned`
1. Endpoint-specific throttling for high-risk automation commands.
2. Secret rotation runbook and periodic key audit automation.

### 10.4 Billing Integrity

`Live`
1. Credit checks and deductions in chat path.
2. Tier-aware feature gating.

`Planned`
1. Cross-table billing reconciliation job.
2. Contract tests for pricing/tier consistency across APIs.

---

## 11. 24-Month Architecture Roadmap

### Phase 1 (Months 0-6)

1. Stabilize Bengaluru top-12 data quality and ingestion reliability.
2. Enforce recommendation metadata contract in all core responses.
3. Reduce runtime coupling in `server.py` through domain route ownership.

### Phase 2 (Months 6-12)

1. Strengthen recommendation-learning loop and confidence calibration.
2. Add ingestion quality and quarantine inspection APIs.
3. Harden billing consistency checks.

### Phase 3 (Months 12-18)

1. Expand team/enterprise controls and auditability.
2. Improve automation execution safety and observability.
3. Introduce stronger model/provider resilience policies.

### Phase 4 (Months 18-24)

1. Institutional-grade explainability package.
2. Replication-ready ingestion and coverage gating blueprint for next city.
3. SLO-backed operations for data freshness and recommendation trust.

---

## 12. Testing and Verification Matrix

### 12.1 API Contract Tests

1. Validate all `Live` endpoints and auth behavior.
2. Verify recommendation payload includes contract metadata keys.
3. Validate profile version behavior in preferences upsert/recommendations.

### 12.2 Ingestion Tests

1. Validation rejects malformed records.
2. Quarantine receives invalid records with reason.
3. Quality metrics are persisted per run.
4. Duplicate handling and price history remain stable.

### 12.3 Reliability Tests

1. Provider fallback behavior under failure.
2. Scheduler start/stop health checks.
3. Streaming response behavior under cancellation.

### 12.4 Documentation Integrity Checks

1. No mixed status claims (`Live` vs `Planned`).
2. No stale date/version markers.
3. Internal section links resolve.

---

## 13. Known Gaps and Decision Log

### 13.1 Known Gaps

1. Ingestion freshness/confidence propagation is not fully standardized across all response surfaces.
2. Ingestion quality and quarantine are persisted but not yet fully exposed via dedicated APIs.
3. `server.py` still hosts many legacy endpoints and should continue moving to domain routers.

### 13.2 Decision Log (Current)

1. Keep single-runtime digital employee architecture.
2. Keep Bengaluru top-12 as quality gate before broader expansion.
3. Keep architecture doc explicit about `Live` vs `Planned` to prevent operational confusion.

---

Valora architecture is now production-readiness-first with explicit ingestion, recommendation, and reliability boundaries.
