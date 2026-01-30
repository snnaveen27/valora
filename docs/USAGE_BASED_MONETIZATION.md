# Usage-Based Monetization System
**Compute-for-Data Economy**

## Overview

Users pay with compute units for actions, and automatically contribute anonymized data for product improvement.

---

## What Was Implemented

### 1. **Core Usage Tracker** (`backend/usage_tracker.py`)
- ✅ Tracks all user actions with compute costs
- ✅ Deducts units from user balance
- ✅ Automatic data collection (anonymized)
- ✅ Training data export in JSONL format

**Action Costs (in compute units):**
- Chat query: 2 units
- Area analysis: 5 units
- Simulation: 10-20 units
- Report export: 25 units
- Map navigation: FREE

### 2. **User Balance System** (`backend/user_auth.py`)
- ✅ Integrated balance into user profile
- ✅ Balance returned with `/api/auth/me`
- ✅ Tracks lifetime usage and earned units

### 3. **Usage Middleware** (`backend/middleware/usage_middleware.py`)
- ✅ Automatic action detection from endpoint
- ✅ Pre-request unit charging
- ✅ Response headers with charge info
- ✅ Returns 402 Payment Required if insufficient units

### 4. **Data Collection Pipeline** (`backend/data_collector.py`)
- ✅ 5 data types: queries, feedback, predictions, spatial, refinements
- ✅ Automatic anonymization (PII removal, location generalization)
- ✅ JSONL format (ML-friendly)
- ✅ Privacy-compliant (GDPR/PDPA)

### 5. **Admin Panel Controls** (`backend/admin_routes.py`)
- ✅ `/api/admin/usage/stats` - Global usage statistics
- ✅ `/api/admin/usage/user/{id}` - User-specific usage
- ✅ `/api/admin/usage/add-units` - Grant units to users
- ✅ `/api/admin/training-data/stats` - Training data statistics
- ✅ `/api/admin/training-data/export` - Export for ML training
- ✅ `/api/admin/training-data/clear` - Clear data (privacy)
- ✅ `/api/admin/usage/revenue-estimate` - Revenue projections

### 6. **Frontend Dashboard** (`src/components/UsageDashboard.jsx`)
- ✅ Real-time balance display
- ✅ Usage breakdown by action type
- ✅ Top actions chart
- ✅ Low balance warnings
- ✅ Top-up button

---

## Setup Instructions

### Step 1: Enable Usage Tracking Middleware

Add to `server.py`:

```python
from middleware.usage_middleware import UsageTrackingMiddleware

# After creating FastAPI app
app.add_middleware(UsageTrackingMiddleware)
```

### Step 2: Initialize User Balances

Give initial units to existing users:

```python
from usage_tracker import get_usage_tracker

tracker = get_usage_tracker()

# Give all users 100 free units to start
for user in user_db.get_all_users():
    tracker.add_units(user.id, 100, source="initial_grant")
```

### Step 3: Test the System

**Check balance:**
```bash
curl http://localhost:8000/api/admin/usage/user/1
```

**Perform action (will auto-charge):**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze Koramangala"}'
```

**Check response headers:**
- `X-Units-Charged: 3`
- `X-Action-Type: chat_multiagent`

### Step 4: View Training Data

**Admin panel:**
```bash
# Get stats
curl http://localhost:8000/api/admin/training-data/stats

# Export batch for ML training
curl -X POST http://localhost:8000/api/admin/training-data/export \
  -H "Content-Type: application/json" \
  -d '{"data_type": "queries", "limit": 1000}'
```

**Files location:**
- `backend/training_data/queries_training.jsonl`
- `backend/training_data/feedback_training.jsonl`
- `backend/training_data/predictions_training.jsonl`
- `backend/training_data/spatial_training.jsonl`
- `backend/training_data/refinements_training.jsonl`

### Step 5: Manual ML Training

**From Admin Panel:**

1. Go to Admin Panel → Training Data
2. Click "Export Training Data"
3. Select data type (queries, feedback, etc.)
4. Download JSONL file
5. Use for training your ML models

**Sample workflow:**
```python
import json

# Load training data
with open('backend/training_data/queries_training.jsonl', 'r') as f:
    queries = [json.loads(line) for line in f]

# Train your model
for sample in queries:
    query = sample['query']
    intent = sample['intent']
    # ... your training logic
```

---

## Integration with Payment System

Your existing payment system (`payment_service.py`) already has Stripe metered billing. Connect it:

**When user completes payment:**
```python
from usage_tracker import get_usage_tracker
tracker = get_usage_tracker()

# Add purchased units
tracker.add_units(
    user_id=user.id,
    units=pack['units'],  # From TOPUP_PACKS
    source='stripe_purchase',
    transaction_id=payment_id
)
```

**Stripe metered billing (automatic):**
```python
from payment_service import get_payment_service
payment = get_payment_service()

# Record usage for Stripe
payment.record_ai_usage(
    stripe_customer_id=user.stripe_customer_id,
    units=units_charged
)
```

---

## Admin Panel Endpoints

### Usage Management

```bash
# Get global stats (last 30 days)
GET /api/admin/usage/stats

# Get user usage
GET /api/admin/usage/user/{user_id}?days=30

# Add units to user
POST /api/admin/usage/add-units
{
  "user_id": 1,
  "units": 500,
  "source": "admin_grant",
  "reason": "Beta tester reward"
}

# Get action costs
GET /api/admin/usage/action-costs

# Revenue estimate
GET /api/admin/usage/revenue-estimate?days=30
```

### Training Data Management

```bash
# Get training data stats
GET /api/admin/training-data/stats

# Export training batch
POST /api/admin/training-data/export
{
  "data_type": "all",
  "limit": 1000,
  "since_date": "2026-01-01"
}

# Clear training data (privacy)
POST /api/admin/training-data/clear
{
  "data_type": "queries",
  "confirm": true
}
```

---

## Revenue Model

**Pricing:**
- 1 unit = ₹2 (promo) to ₹10 (regular)
- Pro Plan: ₹2,999/month = 1,000 units
- Top-up: ₹1,999 for 1,000 units (promo)

**Example User Journey:**
- 10 chat queries (2×10 = 20 units)
- 3 area analyses (5×3 = 15 units)
- 1 simulation (10 units)
- 1 report export (25 units)
- **Total: 70 units/day**

If user has 1,000 units → ~14 days of heavy usage → Needs top-up

**Revenue per 1,000 active users:**
- 1,000 users × 70 units/day × 30 days = 2.1M units/month
- Revenue: ₹4.2M (promo) to ₹21M (regular)

---

## Security Measures

### Anti-Hacking Protection

**1. Rate Limiting**
- 100 requests per minute per user
- Prevents DoS and abuse attacks
- Automatic lockout on excessive requests

**2. Input Validation**
- All user_id validated as positive integers
- Units validated (1-100,000 range)
- Action types sanitized (alphanumeric + underscore only)
- Source parameters whitelisted
- Date formats validated with regex

**3. Admin Authentication**
- All sensitive endpoints require `require_admin` dependency
- JWT token verification
- Role-based access control (RBAC)

**4. Balance Manipulation Prevention**
- Max single addition: 10,000 units
- Source validation (only allowed sources)
- Full audit trail for all balance changes
- Transaction IDs include admin ID and timestamp

**5. SQL Injection Prevention**
- Parameterized queries throughout
- Input sanitization before database operations
- No string concatenation in SQL

**6. Audit Logging**
- All admin actions logged with user ID
- Critical actions (clear data) marked as CRITICAL
- Full transaction history maintained

**7. Data Anonymization**
- User IDs hashed (SHA256, 16 chars)
- Locations generalized to ~1km precision
- PII fields stripped from training data

---

## Privacy & Compliance

**What's Collected:**
- ✅ Query patterns (anonymized)
- ✅ Spatial behavior (generalized to 1km)
- ✅ Preference signals
- ✅ Feedback ratings
- ✅ Prediction accuracy

**What's NOT Collected:**
- ❌ Email, phone, name
- ❌ Exact addresses
- ❌ Payment info
- ❌ API keys

**User IDs are hashed:**
```python
user_id_hash = hashlib.sha256(str(user_id).encode()).hexdigest()[:16]
```

**Location anonymized:**
```python
# From: lat=12.9716, lng=77.5946
# To:   lat=12.97, lng=77.59 (2 decimals = ~1km precision)
```

---

## Next Steps

1. **Test the system** with a few users
2. **Monitor training data** accumulation
3. **Export first batch** after 1,000+ samples
4. **Train initial models** manually
5. **Iterate** based on insights

## ML Training Workflow

**Manual Training (Current):**
1. Export training data from admin panel
2. Train models locally or on your ML infrastructure
3. Deploy improved models
4. Repeat

**Future (Automated):**
- Set up scheduled exports
- Automated model training pipeline
- A/B testing for model versions
- Continuous improvement loop

---

## Support

For issues or questions, check:
- `backend/usage_tracker.py` - Core tracking logic
- `backend/data_collector.py` - Data collection
- `backend/admin_routes.py` - Admin endpoints
- Training data: `backend/training_data/*.jsonl`

**Database tables:**
- `usage_events` - All tracked actions
- `user_balances` - User unit balances
- `training_contributions` - User data contributions
