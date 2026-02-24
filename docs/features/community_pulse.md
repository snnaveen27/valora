# Community Pulse Feature

> **Collaborative Real Estate Intelligence Platform — February 2026**

## Overview

Community Pulse is a comprehensive feature that enables collaborative property decision-making, community-driven reviews, and market sentiment analysis for the Valora real estate platform.

## Feature Components

### Phase 1: Family Hub
Collaborative property decision platform for families.

**Key Features:**
- Create family sessions with unique shareable links
- Invite family members via WhatsApp, email, or direct link
- Shared watchlist with property voting system
- Family timeline with decision tracking
- Credit-based reward system for participation

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/family/sessions` | POST | Create new family session |
| `/api/family/sessions/{id}` | GET | Get session details |
| `/api/family/sessions/{id}/members` | POST | Add member to session |
| `/api/family/sessions/{id}/watchlist` | POST | Add property to watchlist |
| `/api/family/sessions/{id}/vote` | POST | Vote on property |
| `/api/family/sessions/{id}/timeline` | GET | Get session timeline |

**Frontend Components:**
- `FamilyHub.jsx` - Main container
- `FamilySessionCreate.jsx` - Session creation form
- `FamilyInviteModal.jsx` - Member invitation
- `FamilyWatchlist.jsx` - Shared property list
- `FamilyVotingPanel.jsx` - Property voting interface
- `FamilyTimeline.jsx` - Decision timeline
- `WhatsAppShare.jsx` - WhatsApp integration

### Phase 2: Locality Reviews
Community-driven locality and builder reviews with India-specific categories.

**Key Features:**
- Locality reviews with ratings
- India-specific categories (Vastu, Water, Power, Safety, Connectivity)
- Builder profiles with project history
- RERA verification integration
- Review helpfulness voting

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/reviews/locality/{id}` | GET | Get locality reviews |
| `/api/reviews/locality` | POST | Submit locality review |
| `/api/reviews/builder/{id}` | GET | Get builder profile |
| `/api/reviews/builder` | POST | Submit builder review |
| `/api/reviews/helpful` | POST | Mark review helpful |
| `/api/reviews/rera/verify` | GET | Verify RERA status |

**Frontend Components:**
- `LocalityReviews.jsx` - Reviews container
- `ReviewForm.jsx` - Review submission form
- `VastuRating.jsx` - Vastu compliance rating
- `BuilderProfile.jsx` - Builder information
- `RERAVerification.jsx` - RERA verification

### Phase 3: Sentiment Dashboard
Market intelligence and sentiment analysis.

**Key Features:**
- Real-time market sentiment gauge
- Activity feed with market signals
- Investment score calculator
- Price trend charts
- Trending localities

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sentiment/overview` | GET | Get sentiment overview |
| `/api/sentiment/locality/{id}` | GET | Get locality sentiment |
| `/api/sentiment/activity` | GET | Get activity feed |
| `/api/sentiment/trends` | GET | Get price trends |
| `/api/sentiment/check-credits` | GET | Check user credits |

**Frontend Components:**
- `SentimentDashboard.jsx` - Main dashboard
- `SentimentGauge.jsx` - Sentiment visualization
- `ActivityFeed.jsx` - Market activity feed
- `InvestmentScore.jsx` - Investment scoring
- `PriceTrendChart.jsx` - Price trend visualization

## Database Schema

### Tables

```sql
-- Family Hub Tables
CREATE TABLE family_sessions (
    id TEXT PRIMARY KEY,
    creator_id TEXT NOT NULL,
    name TEXT,
    description TEXT,
    invite_code TEXT UNIQUE,
    max_members INTEGER DEFAULT 10,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE family_members (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES family_sessions(id),
    user_id TEXT,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'member',
    invited_by TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE family_watchlist (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES family_sessions(id),
    property_id TEXT,
    added_by TEXT,
    notes TEXT,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE family_votes (
    id TEXT PRIMARY KEY,
    watchlist_id TEXT REFERENCES family_watchlist(id),
    member_id TEXT,
    vote TEXT CHECK(vote IN ('yes', 'no', 'maybe')),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Review Tables
CREATE TABLE locality_reviews (
    id TEXT PRIMARY KEY,
    locality_id TEXT NOT NULL,
    user_id TEXT,
    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    title TEXT,
    content TEXT,
    categories JSON,
    vastu_score INTEGER,
    is_verified BOOLEAN DEFAULT FALSE,
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE builder_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    rera_id TEXT,
    description TEXT,
    established_year INTEGER,
    total_projects INTEGER,
    rating REAL,
    verified BOOLEAN DEFAULT FALSE
);

-- Sentiment Tables
CREATE TABLE market_sentiment (
    id TEXT PRIMARY KEY,
    locality_id TEXT,
    overall_score REAL,
    demand_score REAL,
    supply_score REAL,
    price_trend TEXT,
    investment_score REAL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sentiment_signals (
    id TEXT PRIMARY KEY,
    locality_id TEXT,
    signal_type TEXT,
    signal_value REAL,
    source TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Credit System

### Earning Credits
| Action | Credits |
|--------|---------|
| Create family session | +5 |
| Invite family member | +3 |
| Submit locality review | +10 |
| Verify RERA | +15 |
| Mark review helpful | +2 |

### Spending Credits
| Feature | Credits |
|---------|---------|
| View sentiment dashboard | 5 |
| Historical trends | 10 |
| Investment score | 15 |
| Premium locality report | 25 |

## Integration Points

### SmartPanel Integration
The Community Pulse tab is integrated into the SmartPanel sidebar:
- Tab ID: `community_pulse`
- Icon: `Users` (Lucide)
- Position: Last tab in sidebar

### API Service Layer
Located in `src/services/`:
- `familyApi.js` - Family Hub API calls
- `reviewApi.js` - Reviews API calls
- `sentimentApi.js` - Sentiment API calls

### Backend Routes
Located in `backend/routes/`:
- `family_routes.py` - Family Hub endpoints
- `review_routes.py` - Review endpoints
- `sentiment_routes.py` - Sentiment endpoints

## Configuration

### Environment Variables
```env
# Community Pulse Settings
COMMUNITY_PULSE_ENABLED=true
FAMILY_SESSION_EXPIRY_DAYS=30
MAX_FAMILY_MEMBERS=10
REVIEW_MODERATION_ENABLED=true
```

### Feature Flags
```json
{
  "community_pulse": {
    "family_hub": true,
    "locality_reviews": true,
    "sentiment_dashboard": true,
    "whatsapp_sharing": true,
    "rera_verification": true
  }
}
```

## Testing

### Unit Tests
```bash
# Run Community Pulse tests
pytest backend/tests/test_family_routes.py
pytest backend/tests/test_review_routes.py
pytest backend/tests/test_sentiment_routes.py
```

### Integration Tests
```bash
# Run full integration suite
pytest backend/tests/integration/test_community_pulse.py
```

## Future Enhancements

1. **AI-Powered Insights**
   - Sentiment prediction based on market trends
   - Automated locality recommendations
   - Price forecasting

2. **Enhanced Collaboration**
   - Real-time collaboration with WebSockets
   - Video call integration
   - Document sharing

3. **Gamification**
   - Leaderboards for top reviewers
   - Badges and achievements
   - Community rewards

## Support

For issues or feature requests, contact the Valora development team or create an issue in the project repository.
