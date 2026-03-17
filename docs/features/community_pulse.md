# Community Pulse Feature - FOCUSED VERSION

> **Decision-Room & Locality Intelligence — March 2026**

## Overview

Community Pulse is a **focused** feature aligned with Valora's product thesis:
- Broker productivity and explainable decision intelligence
- Client-ready intelligence outputs
- Multi-stakeholder buying workflows

## FOCUSED Feature Components

### 1. Decision-Room (Family Hub) - Multi-stakeholder Workflow
**NOT social or decorative** - This is a real workflow for buyer committees to support WAWU.

**Key Features:**
- Create decision-rooms with unique shareable links
- Invite stakeholders (family, business partners) via WhatsApp or email
- Shared property shortlist with voting system
- Decision timeline with activity tracking
- Vote summaries for client-ready outputs

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/family/sessions` | POST | Create new decision-room |
| `/api/family/sessions/{id}` | GET | Get decision-room details |
| `/api/family/sessions/{id}/members` | POST | Add stakeholder |
| `/api/family/sessions/{id}/watchlist` | POST | Add property to shortlist |
| `/api/family/sessions/{id}/vote` | POST | Vote on property |
| `/api/family/sessions/{id}/vote-summary` | GET | Get decision summary (CLIENT-READY) |

**Frontend Components:**
- `FamilyHub.jsx` - Main container
- `FamilySessionCreate.jsx` - Session creation
- `FamilyInviteModal.jsx` - Stakeholder invitation
- `FamilyWatchlist.jsx` - Property shortlist
- `FamilyVotingPanel.jsx` - Voting interface
- `FamilyTimeline.jsx` - Decision activity
- `WhatsAppShare.jsx` - Share functionality

### 2. Locality Reviews with Verified Resident Proof
**Defensible locality context** that brokers need.

**Key Features:**
- Locality reviews with verified resident badges
- India-specific categories: Vastu, Schools, Transport, Safety
- Community validation (helpful votes)
- Focus on verifiable, defensible context

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/reviews/locality/{id}` | GET | Get locality reviews |
| `/api/reviews/locality` | POST | Submit locality review |
| `/api/reviews/{type}/{id}/helpful` | POST | Mark review helpful |

**Frontend Components:**
- `LocalityReviews.jsx` - Reviews container
- `ReviewForm.jsx` - Review submission
- `VastuRating.jsx` - Vastu compliance rating

### 3. Market Sentiment - Supporting Intelligence (SECONDARY)
**NOT a consumer-style dashboard** - Supports shortlisted decisions, not passive browsing.

**Key Features:**
- Market sentiment gauge for locality
- Price momentum and trends
- Investment score for decisions
- Rental yield metrics

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sentiment/locality/{id}` | GET | Get locality sentiment |
| `/api/sentiment/price-momentum/{id}` | GET | Price momentum |
| `/api/sentiment/investment-score/{id}` | GET | Investment score |
| `/api/sentiment/rental-yield/{id}` | GET | Rental yield |

**Frontend Components:**
- `SentimentDashboard.jsx` - Main dashboard
- `SentimentGauge.jsx` - Sentiment visualization
- `InvestmentScore.jsx` - Investment scoring
- `PriceTrendChart.jsx` - Price trends

---

## REMOVED Features (Not Aligned with Product Thesis)

The following were removed to keep Valora **niche and focused**:

| Feature | Reason |
|---------|--------|
| Builder Profiles | Generic directory, not broker-focused |
| Builder Reviews | Not locality-focused |
| RERA Verification | Not core to broker workflow |
| Raw Sentiment Signals | Too complex, not client-ready |
| Historical Sentiment Trends | Supporting, not primary |

---

## Database Schema (FOCUSED)

```sql
-- Decision-Room Tables
CREATE TABLE family_sessions (
    id TEXT PRIMARY KEY,
    owner_user_id TEXT NOT NULL,
    family_name TEXT NOT NULL,
    target_locality TEXT,
    budget_min REAL,
    budget_max REAL,
    property_types TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE family_members (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES family_sessions(id),
    user_id TEXT,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'member',
    invite_status TEXT DEFAULT 'pending'
);

CREATE TABLE family_watchlist (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES family_sessions(id),
    property_id TEXT,
    added_by TEXT,
    notes TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'considering'
);

CREATE TABLE family_votes (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES family_sessions(id),
    property_id TEXT,
    user_id TEXT,
    vote TEXT CHECK(vote IN ('up', 'down', 'maybe')),
    aspects TEXT,
    comment TEXT
);

-- Locality Reviews Table
CREATE TABLE locality_reviews (
    id TEXT PRIMARY KEY,
    locality_id TEXT NOT NULL,
    locality_name TEXT NOT NULL,
    user_id TEXT NOT NULL,
    overall_rating REAL NOT NULL,
    vastu_rating REAL,
    school_rating REAL,
    transport_rating REAL,
    safety_rating REAL,
    is_verified INTEGER DEFAULT 0,
    verification_type TEXT,
    helpful_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active'
);

CREATE TABLE review_helpful (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    review_type TEXT NOT NULL,
    user_id TEXT NOT NULL
);

-- Market Sentiment Table (Supporting Intelligence)
CREATE TABLE market_sentiment (
    id TEXT PRIMARY KEY,
    locality_id TEXT NOT NULL,
    sentiment_score REAL,
    demand_score REAL,
    supply_score REAL,
    investment_score REAL,
    price_change_pct REAL,
    price_momentum TEXT,
    rental_yield_avg REAL,
    last_updated TEXT
);
```

---

## Integration Points

### SmartPanel Integration
- Tab ID: `community_pulse`
- Icon: `Users` (Lucide)
- Description: "Decision-Room, Locality Reviews & Market Sentiment"

### Backend Routes
- `backend/routes/family_routes.py` - Decision-Room endpoints
- `backend/routes/review_routes.py` - Locality review endpoints
- `backend/routes/sentiment_routes.py` - Market sentiment endpoints

---

## Product Alignment

This feature directly supports Valora's product thesis:

| Product Thesis | Community Feature |
|----------------|-------------------|
| Broker productivity | Decision-Room workflow for multi-stakeholder buying |
| Explainable decision intelligence | Locality reviews with verified resident proof |
| Client-ready intelligence outputs | Vote summaries, decision reports |
| WAWU (Weekly Active Workflow Users) | Real workflow for buyer committees |

---

*Last Updated: March 2026*
