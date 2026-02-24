# Valora AI - Business & GTM

## Executive Summary

**Valora AI** is an offline-first 3D GIS + AI reasoning platform for real estate intelligence.

### Core Value Proposition
- **Truth Firewall**: AI only narrates verified facts, never invents data
- **Offline-First**: Runs locally with no internet dependency for core intelligence
- **3D-Native**: Models view quality, shadows, skyline—not just 2D maps
- **Explainable**: Every insight grounded in deterministic data

### Market Opportunity
- **Bengaluru**: 14.7M sq ft office absorption (2024), 47K housing sales
- **Target**: 5% of 100K+ brokers, 20 top developers before Mumbai/NCR expansion
- **Market**: $1 Trillion Indian real estate by 2030

---

## Customer Segments

### Brokers & Agencies (B2B SaaS)
**Package**: Valora Pro — Seat-based license
- Shortlist areas and properties quickly
- Explain "why this locality" with objective metrics
- Standardized reports and WhatsApp-shareable summaries

### Developers & Builders (B2B Project-based)
**Package**: Valora Developer Studio — Per project + quarterly retainer
- Identify high-potential micro-markets
- Run scenario-based impact narratives
- 3D storytelling for sales & marketing

### Banks & Lenders (Enterprise)
**Package**: Valora Enterprise — Annual license + SLA
- Automated valuation support
- Risk flags & locality intelligence
- On-prem deployment option

### NRI / Remote Investors (Premium)
**Package**: Valora Premium Reports — Per report / concierge
- Remotely evaluate areas with confidence
- Explainable shortlists + risk summaries

---

## Pricing Model

### Usage-Based Units

| Action | Units | Regular Price | Launch Price (80% off) |
|--------|-------|---------------|------------------------|
| Chat Query | 1 | ₹10 | ₹2 |
| Property Search | 2 | ₹20 | ₹4 |
| Area Analysis | 3 | ₹30 | ₹6 |
| Valuation | 10 | ₹100 | ₹20 |
| Storyboard | 15 | ₹150 | ₹30 |
| Report Export | 20 | ₹200 | ₹40 |
| What-If Simulation | 25 | ₹250 | ₹50 |

### Subscription Tiers

| Tier | Units/Month | Regular Price | Launch Price |
|------|---------------|---------------|--------------|
| **Free** | 50 | ₹0 | ₹0 |
| **Pro** | 1,000 | ₹2,999 | ₹599 |
| **Team** | 3,000/seat | ₹4,999/seat | ₹999/seat |
| **Enterprise** | Unlimited | Custom | Custom |

### Top-Up Packs
| Pack | Units | Launch Price |
|------|-------|--------------|
| Starter | 100 | ₹59 |
| Standard | 300 | ₹139 |
| Bulk | 1,000 | ₹399 |

**Promo Code**: LAUNCH80 (valid until March 31, 2026)

---

## Digital Employee Monetization (Implemented)

Valora now includes a native digital employee layer (alerts + automations + lead CRM) inside the core product, not as a separate product line.

### Free vs Pro Packaging

| Capability | Free | Pro |
|------------|------|-----|
| Active property alerts | Up to 3 | Unlimited |
| Scheduled automations | Up to 5 | Unlimited |
| Email automation | No | Yes |
| Auto-execution | Manual confirmation default | Auto-execution allowed |
| Lead manager | Basic | Full workflow |

### Revenue Impact Thesis

- Improves **Free → Pro conversion** by gating high-frequency automation and email delivery.
- Improves **retention** because users rely on always-on workflows, not just ad hoc chats.
- Increases **ARPU** by combining subscription value (automation) with usage-based analytics/reporting.

### Build-vs-Buy Decision (OpenClaw)

Current direction is to **extend Valora’s own architecture** rather than replacing the stack with OpenClaw:

- Existing auth, tiering, credits, and GIS data pipelines are already productionized.
- A separate agent runtime would duplicate orchestration, state, and observability.
- In-product integration keeps lower operational complexity and better control over policy/security.

---

## Technology Differentiation

| Feature | Generic PropTech | Valora AI |
|--------|------------------|-----------|
| Data Source | Scraped listings | Listings + 455K+ Gov/GIS datasets |
| AI Reliability | Hallucinates numbers | Truth Firewall verified |
| 3D Context | None or static | Volumetric 3D (shadows, views) |
| Privacy | Cloud-only | Offline-First / On-Prem |
| Logic | Text matching | Causal Reasoning (simulations) |

---

## Go-To-Market Strategy

### Phase 1 (Months 1-6): Bengaluru Beachhead
- Pilot 50 top brokers (East/South Bengaluru IT corridors)
- Channel: Direct sales + Broker associations (BRAI)
- Goal: 90%+ query success rate on core intents

### Phase 2 (Months 7-12): Developer Partnerships
- Deploy "Sales Office Twin" for 5 major launches
- Prove simulation value prop
- Quarterly retainer model validation

### Phase 3 (Year 2): Pan-India Expansion
- Replicate data pipeline for Mumbai and NCR
- Multi-city schema already active

---

## Revenue Model Mechanics

### Data Flywheel
- Users pay for intelligence with compute units
- Every query improves AI (anonymized data collection)
- Training data exported in JSONL for ML improvement

### Security & Pricing Database
- Pricing stored in SQLite (not JSON) with full audit trail
- Admin authentication required for changes
- Database ACLs, input validation, transaction logging

### Integration
- **Stripe**: For AI usage tracking, metered billing, LLM proxy
- **Razorpay**: For subscriptions, UPI AutoPay, quantity billing

---

## Metrics & KPIs

### North Star
- Weekly Active Decision Sessions (WADS)
- Shortlist-to-action conversion rate

### Product KPIs
- Intent accuracy, tool success rate, median latency
- % responses with grounded numeric facts
- % users with active digital employee automations
- Alert trigger-to-user-action conversion
- Lead follow-up completion rate

### Business KPIs
- Trial → paid conversion
- Net Revenue Retention (NRR)
- CAC, LTV/CAC ratio, payback period

---

## The Ask: $2M Seed

**Allocation**:
- 45% Engineering (Truth Firewall, Simulation Engine)
- 30% Data Ops (Historical price data, GIS layers)
- 25% GTM (1,000 paying brokers in Bengaluru)

**Vision**: Become the City Operating System—starting with real estate intelligence, expanding to urban planning.

---

*Unified: February 2026 (includes digital employee packaging and automation GTM)*
