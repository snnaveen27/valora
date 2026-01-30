# Backend Organization Guide

## Current Structure

The backend has been organized into logical modules:

### Core Modules

```
backend/
├── config/                    # Configuration files (admin-editable)
│   └── pricing_config.json   # Pricing and tier limits
├── database/                  # Database services
│   ├── db_service.py
│   ├── api_routes.py
│   └── ...
├── city_intelligence/         # City analysis modules
│   ├── causal_reasoning.py
│   ├── evolution_timeline.py
│   └── ...
├── middleware/                # Request/response middleware
│   └── usage_middleware.py
├── session_memory/            # User session data
├── training_data/             # ML training data (gitignored)
└── utils/                     # Utility functions
```

### Main Files

**Authentication & Authorization:**
- `auth_routes.py` - Login, signup, user management
- `user_auth.py` - User database, authentication logic

**Monetization & Usage:**
- `usage_tracker.py` - Usage tracking, balance management
- `data_collector.py` - Training data collection
- `payment_routes.py` - Payment endpoints
- `payment_service.py` - Payment gateway integration

**Admin & Configuration:**
- `admin_routes.py` - Admin panel API endpoints
- `admin_config.json` - Admin settings
- `config/pricing_config.json` - **Admin-editable pricing**

**AI & Intelligence:**
- `gis_agents.py` - Multi-agent orchestrator
- `rag_service.py` - RAG for context
- `multi_agent_orchestrator.py` - Agent coordination
- `simulation_engine.py` - What-if simulations
- `narrative_generator.py` - Storyboard generation

**Spatial Analysis:**
- `spatial_reasoning.py` - Spatial logic
- `terrain_service.py` - Terrain analysis
- `network_analyzer.py` - Network analysis
- `viewshed_analyzer.py` - Visibility analysis

**Data Services:**
- `property_service.py` - Property data
- `locality_service.py` - Locality data
- `apify_service.py` - External data integration

**Server:**
- `server.py` - Main FastAPI application

## Pricing Configuration (Admin-Editable)

### Location
`backend/config/pricing_config.json`

### Structure
```json
{
  "action_costs": {
    "chat_query": 1,
    "area_analysis": 3,
    "valuation": 10,
    ...
  },
  "tier_monthly_limits": {
    "free": 50,
    "pro": 1000,
    "team": 3000,
    ...
  },
  "pricing": {
    "promo_per_unit_inr": 2,
    "regular_per_unit_inr": 10,
    "promo_active": true,
    "promo_discount_percent": 80,
    "promo_valid_until": "2026-03-31"
  },
  "topup_packs": [...],
  "subscription_tiers": {...}
}
```

### Admin API Endpoints

**Get Pricing Config:**
```bash
GET /api/admin/pricing/config
Authorization: Bearer <admin_token>
```

**Update Pricing:**
```bash
POST /api/admin/pricing/config
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "action_costs": {
    "chat_query": 2,
    "valuation": 15
  },
  "pricing": {
    "promo_per_unit_inr": 3
  }
}
```

**Reload Config (without restart):**
```bash
POST /api/admin/pricing/reload
Authorization: Bearer <admin_token>
```

## Security Features

### Input Validation
- All user_id validated as positive integers
- Units validated (0-100,000 range)
- Action types sanitized (alphanumeric + underscore only)
- Source parameters whitelisted
- Date formats validated with regex

### Admin Authentication
- All sensitive endpoints require `require_admin` dependency
- JWT token verification
- Role-based access control (RBAC)

### Audit Logging
- All admin actions logged with user ID
- Critical actions (clear data, pricing changes) marked as CRITICAL
- Full transaction history maintained

### Rate Limiting
- 100 requests per minute per user
- Prevents DoS and abuse attacks

## Git Workflow

### Before Committing

1. **Check sensitive files are gitignored:**
   - `backend/config/pricing_config.json`
   - `backend/training_data/*.jsonl`
   - `backend/session_memory/*.json`
   - API keys, certificates

2. **Create template files:**
   ```bash
   cp backend/config/pricing_config.json backend/config/pricing_config.template.json
   ```

3. **Test locally:**
   ```bash
   # Backend
   cd backend
   python server.py
   
   # Frontend
   npm run dev
   ```

### Commit & Push

```bash
# Initialize git (if not already)
git init

# Add files
git add .

# Commit
git commit -m "feat: Add usage-based monetization with admin pricing config"

# Add remote
git remote add origin https://github.com/yourusername/valora-ai.git

# Push
git push -u origin main
```

## Environment Variables

Create `.env` file in root:

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/valora

# Payment Gateways
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
CASHFREE_APP_ID=xxxxxxxxxxxxxxxxxxxxx
CASHFREE_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx

# JWT
JWT_SECRET=your-secret-key-here

# LLM (Optional)
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
```

## Deployment Checklist

- [ ] Set production environment variables
- [ ] Update `pricing_config.json` with production prices
- [ ] Enable HTTPS
- [ ] Set up database backups
- [ ] Configure rate limiting
- [ ] Set up monitoring (Sentry, etc.)
- [ ] Test payment webhooks
- [ ] Verify admin authentication
- [ ] Test pricing changes via admin panel

## Maintenance

### Update Pricing
1. Login as admin
2. Go to Admin Panel → Pricing Configuration
3. Update prices
4. Click "Save & Reload"

### Export Training Data
1. Login as admin
2. Go to Admin Panel → Training Data
3. Select data type
4. Click "Export"
5. Use for ML training

### Monitor Usage
1. Login as admin
2. Go to Admin Panel → Usage Stats
3. View revenue estimates, top actions, active users
