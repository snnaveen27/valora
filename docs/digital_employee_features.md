# Digital Employee Features for Valora

Last verified: March 5, 2026

> **Note:** This document tracks digital employee vision and implementation status in Valora.

---

## Overview

Autonomous workflows represent a shift from passive AI responses to action-oriented digital employees. Valora implements these capabilities natively within the existing stack to keep security, tiering, and observability unified.

This document outlines implemented and planned digital employee features within Valora's Free + Pro structure.

### Architecture Decision

**Native implementation** - extending Valora's current architecture:

- Reuses existing auth, credit/tier controls, and grounded GIS data pipeline.
- Avoids duplicated state and operational complexity from a second agent runtime.
- Enables faster production rollout with lower migration risk.

---

## Table of Contents

1. [What is a Digital Employee?](#what-is-a-digital-employee)
2. [Why It Matters for Real Estate](#why-it-matters-for-real-estate)
3. [User Tier Structure](#user-tier-structure)
4. [Feature Breakdown by Tier](#feature-breakdown-by-tier)
5. [Use Cases](#use-cases)
6. [Technical Implementation](#technical-implementation)
7. [UI/UX Changes](#uiux-changes)
8. [Integration Points](#integration-points)
9. [Security Considerations](#security-considerations)
10. [Roadmap](#roadmap)

---

## What is a Digital Employee?

A digital employee (autonomous AI agent) is an AI that:

- ✅ Doesn't just answer questions - it **acts** on your behalf
- ✅ Monitors tasks continuously in the background
- ✅ Executes multi-step workflows automatically
- ✅ Integrates with external tools (email, calendar, CRMs)
- ✅ Learns from interactions to improve automation

**Example:**
- *Passive AI:* "What's the weather?"
- *Digital Employee:* "Alert me when a 2BHK in Whitefield under 80L is listed, email it to my client, and schedule a viewing."

---

## Why It Matters for Real Estate

Real estate involves many repetitive, time-consuming tasks:

| Task | Time Spent | Automation Potential |
|------|------------|---------------------|
| Lead follow-ups | High | Very High |
| Property matching | High | Very High |
| Scheduling viewings | Medium | High |
| Market research | High | Very High |
| Report generation | Medium | High |
| Email updates to clients | High | Very High |

Digital employees excel at automating these repetitive workflows, freeing up agents to focus on high-value activities like closing deals.

---

## User Tier Structure

Valora currently has a **2-tier subscription model**:

| Tier | Target Users | Monthly Credits |
|------|--------------|-----------------|
| **Free** | Home buyers, passive investors | 50 |
| **Pro** | Real estate agents, active investors | 1,000 |

Digital employee features are distributed across these tiers to drive conversions.

---

## Feature Breakdown by Tier

### Free Tier Features

| Feature | Limit | Description |
|---------|-------|-------------|
| Property Alerts | 3 active | Get notified when properties match criteria |
| Scheduled Tasks | 5 active | Weekly reports and task automations (manual confirmation default) |
| Notifications | In-app only | Automation results in activity feed |
| Lead Manager | Included | Basic lead CRUD and pipeline tracking |
| Chat Commands | Included | `alert me...`, `schedule...`, `add lead...` routed to automation APIs |

**Example Commands:**
- "Alert me when 2BHK in Whitefield under 80L is listed"
- "Schedule a weekly report for Whitefield every Monday at 9am"
- "Add lead Rahul mehta@example.com +91 98765 43210"

### Pro Tier Features

| Feature | Description |
|---------|-------------|
| Unlimited Alerts + Tasks | No hard cap on active alerts/scheduled tasks |
| Automated Email Delivery | Email channel for alerts and scheduled reports |
| Auto-Execution | Tasks can run without manual confirmation |
| Faster Alert Scans | 15-minute instant scan interval vs 60-minute free tier |
| Lead Management | Full lead workflow with follow-up task support |

**Example Commands:**
- "Send weekly market report to lead@example.com every Monday 9am"
- "Alert me when 3BHK in Koramangala under 2.5cr is listed"
- "Add lead Priya priya@example.com +91 99887 66554"

---

## Use Cases

### 1. Lead Generation & Qualification

```
Incoming Lead → Qualify via Chat → Match Properties → Email Listings → Schedule Visit
```

**Workflow:**
1. Lead arrives via WhatsApp/Email/Website
2. Digital employee qualifies with questions (budget, location, timeline)
3. Matches with properties from database
4. Emails listings to lead
5. Proposes viewing times based on calendar
6. Sends confirmation and reminders

### 2. Property Alert System

```
New Listing Detected → Compare with User Criteria → Send Alert → Track Interest → Follow Up
```

**Workflow:**
1. Scrapers detect new listing
2. Compare against user's saved criteria
3. If match → send push notification + email
4. Track if user shows interest
5. Auto-follow-up if no response in 48 hours

### 3. Client Report Automation

```
Scheduled Trigger → Collect Data → Generate Report → Email to Client → Log Activity
```

**Workflow:**
1. Client (or agent) sets weekly report schedule
2. System collects: new listings, price changes, market trends
3. AI generates personalized report
4. Emails to client automatically
5. Logs activity in CRM

### 4. Market Intelligence

```
Continuous Monitoring → Price Change Detection → Competitor Tracking → Alert
```

**Workflow:**
1. Monitor target areas 24/7
2. Track price changes on watched properties
3. Alert when similar properties listed below market price
4. Track competitor activity in specific areas

---

## Technical Implementation

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Valora Backend                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Chat API   │  │  Task       │  │  Email      │          │
│  │   (Routes)   │  │  Orchestrator│  │  Service    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                 │                    │
│         ▼                 ▼                 ▼                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Digital Employee Brain                      │   │
│  │  - Intent Recognition                                    │   │
│  │  - Task Decomposition                                    │   │
│  │  - Action Planning                                       │   │
│  │  - Execution Engine                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│         │                 │                 │                    │
│         ▼                 ▼                 ▼                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Scraper     │  │  Calendar   │  │  WhatsApp    │          │
│  │  Service     │  │  Service    │  │  API         │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Implemented Backend Services

| Service | File | Purpose |
|---------|------|---------|
| Email Automation | `backend/services/email_automation.py` | Send automated emails |
| Scheduler Service | `backend/services/scheduler_service.py` | In-process async scheduler loop for scans + due task execution |
| Notification Service | `backend/services/notification_service.py` | In-app automation activity notifications |
| Lead Manager | `backend/services/lead_manager.py` | CRM lead lifecycle support |
| Digital Employee Core | `backend/services/digital_employee_service.py` | Alerts, schedules, leads, command parsing, audit logs |
| API Routes | `backend/routes/digital_employee_routes.py` | `/api/digital-employee`, `/api/automations`, `/api/leads` endpoints |

### Database Schema Extensions

```sql
-- Property Alerts
CREATE TABLE property_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',
    name TEXT NOT NULL,
    criteria_json TEXT NOT NULL,
    frequency TEXT NOT NULL DEFAULT 'instant',
    channels_json TEXT NOT NULL DEFAULT '["in_app"]',
    is_active INTEGER NOT NULL DEFAULT 1,
    last_checked_at REAL,
    last_triggered_at REAL,
    last_match_fingerprint TEXT,
    trigger_count INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

-- Scheduled Tasks
CREATE TABLE scheduled_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',
    name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    schedule_json TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    requires_confirmation INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    next_run_at REAL,
    last_run_at REAL,
    run_count INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

-- Leads
CREATE TABLE leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    source TEXT DEFAULT 'manual',
    status TEXT NOT NULL DEFAULT 'new',
    notes TEXT,
    last_contact_at REAL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

-- Automation audit feed
CREATE TABLE automation_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    action TEXT NOT NULL,
    details_json TEXT,
    status TEXT NOT NULL DEFAULT 'success',
    error_message TEXT,
    created_at REAL NOT NULL
);

-- Scheduled task run deduplication + results
CREATE TABLE automation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheduled_task_id INTEGER NOT NULL,
    run_key TEXT NOT NULL UNIQUE,
    started_at REAL NOT NULL,
    finished_at REAL,
    status TEXT NOT NULL DEFAULT 'running',
    summary TEXT,
    error_message TEXT
);
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/digital-employee/summary` | GET | Dashboard snapshot + tier policy |
| `/api/digital-employee/alerts` | GET/POST | Manage property alerts |
| `/api/digital-employee/alerts/{id}` | PUT/DELETE | Update/deactivate alerts |
| `/api/digital-employee/scheduled-tasks` | GET/POST | Manage scheduled tasks |
| `/api/digital-employee/scheduled-tasks/{id}` | PUT/DELETE | Update/deactivate tasks |
| `/api/digital-employee/leads` | GET/POST | Lead management |
| `/api/digital-employee/activity` | GET | Automation audit feed |
| `/api/digital-employee/commands/parse` | POST | Parse command intent and payload without executing |
| `/api/digital-employee/commands/parse-and-execute` | POST | Execute explicit automation commands from chat |
| `/api/automations/*` | GET/POST | Compatibility aliases for automation flows |
| `/api/leads/*` | GET/POST/PUT/DELETE | Compatibility lead CRUD aliases |

---

## UI/UX Changes

### New Sidebar Components

```
├── Chat
├── Properties
├── Reports
└── 🤖 Agent (NEW)
    ├── Active Alerts
    ├── Scheduled Tasks
    ├── Lead Manager
    └── Settings
```

### New UI Components

| Component | File | Purpose |
|-----------|------|---------|
| AgentControlPanel | `src/components/AgentControlPanel.jsx` | Central automation hub |
| Smart panel tab integration | `src/components/SmartPanel.jsx`, `src/components/SmartTabsContainer.jsx` | Exposes `agent_control` tab |
| App-level tab wiring | `src/components/MainApp.jsx` | Routes agent commands to Agent tab state |
| Chat command router | `src/components/chat/EnhancedChatPanel.jsx` | Fast-path parse-and-execute for explicit automation commands |

### Chat Interface Extensions

Implemented in `src/components/chat/EnhancedChatPanel.jsx` with fast-path API routing for explicit commands:

```javascript
// Explicit automation commands routed before normal AI streaming
const commands = [
  "Alert me when 2BHK in Whitefield under 80L is listed",
  "Schedule weekly report for Koramangala Monday 09:00",
  "Add lead Rahul rahul@example.com +91 98765 43210"
];
```

---

## Integration Points

### Existing Systems to Leverage

| Existing Component | Integration Purpose |
|-------------------|-------------------|
| `backend/database/query_service.py` | Property search for alert scans |
| `backend/auth/user_auth.py`, `backend/routes/auth_routes.py` | Authenticated automation APIs |
| `backend/ai/unified_credits.py` | Tier resolution (Free vs Pro policy enforcement) |
| `backend/core/sqlite_pool.py` | Thread-local DB pooling for automation state |
| `src/components/chat/EnhancedChatPanel.jsx` | Command routing from chat to automation APIs |
| `src/components/SmartPanel.jsx` | Agent tab entry point in main product UI |

### External Integrations (India-Specific)

| Platform | Integration Method | Priority | Status |
|----------|------------------|----------|--------|
| SMTP Providers (Gmail/SES/etc.) | SMTP host/user/password env configuration | High | Implemented |
| Google Calendar | Google Calendar API | Medium | Planned |
| WhatsApp Business | WhatsApp Cloud API | High | Planned |
| Google Sheets / CRM export | API sync jobs | Low | Planned |

---

## Security Considerations

Since digital employees can execute actions autonomously, security is paramount:

### 1. Permission Levels

| Action | Free Tier | Pro Tier |
|--------|-----------|----------|
| Set alerts | ✅ (3 max) | ✅ Unlimited |
| Send emails | ❌ | ✅ |
| Scheduled tasks | ✅ (5 max, confirmation default) | ✅ Unlimited, auto-execution allowed |
| Access leads/CRM | ✅ Basic | ✅ Full |
| Scheduler controls (`/scheduler/run-once`) | ✅ Auth required | ✅ Auth required |

### 2. Audit Logging

All automated actions must be logged:

```python
conn.execute(
    """
    INSERT INTO automation_activity
    (user_id, entity_type, entity_id, action, details_json, status, error_message, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (...)
)
```

### 3. Confirmation Workflow

- **Free tier:** Scheduled tasks default to manual confirmation.
- **Pro tier:** Auto-execution is enabled for trusted scheduled flows.

### 4. Rate Limiting

Current + recommended controls:

- Free tier daily alert notification cap (implemented in automation logic)
- Alert/task count limits by tier (implemented)
- Standard authenticated API protections already enforced
- Add endpoint-level throttling for `/api/digital-employee/commands/parse-and-execute` as a next hardening step

---

## Roadmap

### Phase 1: Foundation (MVP)

- [x] Property alert system (max 3 for free, unlimited for Pro)
- [x] Basic email notifications
- [ ] Viewing scheduling (manual confirmation)
- [x] Chat commands for automation

**Estimated Time:** historical estimate (already implemented in core)

### Phase 2: Automation

- [x] Email automation for Pro users
- [ ] Calendar integration
- [x] Scheduled reports
- [x] Lead management

**Estimated Time:** historical estimate (partially implemented)

### Phase 3: Advanced Features

- [ ] WhatsApp integration
- [ ] Competitor monitoring
- [ ] Advanced CRM features
- [ ] Bulk operations (Pro only)

**Estimated Time:** roadmap estimate

### Phase 4: Intelligence

- [ ] AI-powered lead qualification
- [ ] Predictive property matching
- [ ] Market trend analysis
- [ ] Automated follow-ups

**Estimated Time:** roadmap estimate

---

## Validation Snapshot (March 5, 2026)

### Automated Tests

- `pytest backend/tests/test_digital_employee_service.py` -> 4 passed
- `pytest backend/tests/test_user_auth_schema_migration.py` -> 1 passed

### API Smoke Coverage

Authenticated end-to-end checks passed for:

- `/api/digital-employee/summary`
- `/api/digital-employee/alerts` (GET/POST/PUT/DELETE)
- `/api/digital-employee/scheduled-tasks` (GET/POST/PUT/DELETE)
- `/api/digital-employee/leads` (GET/POST/PUT/DELETE)
- `/api/digital-employee/activity`
- `/api/digital-employee/commands/parse-and-execute`
- `/api/digital-employee/scheduler/status`
- `/api/digital-employee/scheduler/run-once`
- Compatibility aliases: `/api/automations/alerts`, `/api/leads`

### Reliability Fixes Applied

- Legacy `users.db` instances now auto-migrate missing `users.job_role` column during auth DB initialization.
- Profile update API now persists `job_role` updates via `/api/auth/me`.

---

## Conclusion

Digital employee capabilities are now implemented as a native Valora runtime and materially improve the platform value proposition:

1. **For Free users:** Basic automation to experience the product's power
2. **For Pro users:** Full automation suite to streamline their business
3. **For Valora:** Drives conversions from Free → Pro tier

Implemented core additions:
- Email automation service with safe fallback mode
- Background scheduler for alert scans + due tasks
- Lead lifecycle APIs and activity audit stream
- Agent control panel and chat command routing

Next milestones are calendar/WhatsApp integrations, advanced CRM workflows, and stronger policy/rate-limit controls for scale.

---

## Related Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [Feature List](./features/)
- [API Documentation](./reports_information.md)

---

*Last Updated: 2026-03-05 (aligned with Bengaluru-first architecture and current tiering)*
