# Valora AI Backend

## Production-Ready Features

✅ **Usage-Based Monetization** - Compute unit tracking with database storage  
✅ **Secure Pricing Config** - Stored in database (not JSON files)  
✅ **Full Audit Trail** - All pricing changes logged  
✅ **Rate Limiting** - 100 requests/min per user  
✅ **Admin Authentication** - JWT + RBAC on all sensitive endpoints  
✅ **Data Collection** - Anonymized training data for ML  

## Backend Structure

```
backend/
├── auth/                      # Authentication (organized)
│   ├── user_auth.py
│   └── auth.py
├── routes/                    # API routes (organized)
│   ├── auth_routes.py
│   ├── admin_routes.py
│   └── payment_routes.py
├── database/                  # Database layer
│   ├── db_service.py
│   ├── pricing_db.py         # Secure pricing storage
│   └── ...
├── city_intelligence/         # City analysis modules
├── middleware/                # Usage middleware (auto-charging)
├── config/                    # Configuration templates
├── migrations/                # Database migrations (organized)
│   ├── migrate_pricing_to_db.py
│   └── ...
├── session_memory/            # User sessions
├── training_data/             # ML data (gitignored)
└── [50+ specialized modules]  # Core functionality
    ├── server.py              # Main FastAPI app
    ├── usage_tracker.py       # Usage tracking
    ├── gis_agents.py          # Multi-agent system
    ├── rag_service.py         # RAG context
    └── ...
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python migrations/migrate_pricing_to_db.py
```

### 3. Start Server
```bash
python server.py
```

Server runs on: http://localhost:8000  
API docs: http://localhost:8000/docs

## Verified Working

✅ Server imports successfully  
✅ Pricing database loads (35 actions)  
✅ Compute costs defined (35 actions)  
✅ Tier limits configured (5 tiers)  
✅ All modules initialize properly  
✅ 42,452 properties loaded  
✅ 26,961 POIs indexed  
✅ 77,907 vectors in Pinecone  

## Security Features

- **Database storage** for pricing (not JSON)
- **Admin authentication** required for all sensitive ops
- **Audit logging** for all pricing changes
- **Rate limiting** prevents abuse
- **Input validation** on all endpoints
- **SQL injection prevention** via parameterized queries

## Key Modules

| Module | Purpose |
|--------|---------|
| `server.py` | Main FastAPI application |
| `usage_tracker.py` | Usage-based billing system |
| `database/pricing_db.py` | Secure pricing storage |
| `gis_agents.py` | Multi-agent orchestrator |
| `rag_service.py` | RAG for context |
| `spatial_reasoning.py` | Spatial analysis |
| `simulation_engine.py` | What-if simulations |
| `payment_service.py` | Payment gateways |

## Environment Variables

Create `.env` file:
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/valora
RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=xxxxx
STRIPE_SECRET_KEY=sk_test_xxxxx
JWT_SECRET=your-secret-key
```

## Production Deployment

1. Set environment variables
2. Run migrations
3. Start with uvicorn:
   ```bash
   uvicorn server:app --host 0.0.0.0 --port 8000
   ```

## Monitoring

- Health check: `GET /health`
- System status: `GET /api/admin/status` (admin only)
- Usage stats: `GET /api/admin/usage/stats` (admin only)

---

**Status:** Production Ready ✅
