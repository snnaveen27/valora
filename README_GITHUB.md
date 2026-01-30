# Valora AI - Real Estate Intelligence Platform

**Offline-first 3D GIS + AI reasoning platform for real estate intelligence**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18.0+-61dafb.svg)](https://reactjs.org/)

## 🌟 Features

### Core Capabilities
- **3D City Visualization** - Interactive 3D buildings, terrain, POIs, and transport networks
- **AI-Powered Analysis** - Multi-agent reasoning with grounded facts (no hallucinations)
- **What-If Simulations** - Scenario planning for infrastructure changes
- **Offline-First** - Works with local data and local LLMs (Ollama)
- **Usage-Based Monetization** - Pay-per-computation with automatic data collection for ML

### Key Differentiators
- ✅ **Grounded Analytics** - LLM only narrates, tools compute facts
- ✅ **Explainable AI** - Confidence scores, assumptions, and reasoning chains
- ✅ **Privacy-Compliant** - Anonymized data collection, GDPR/PDPA ready
- ✅ **Admin-Configurable Pricing** - Dynamic pricing without code changes

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- PostgreSQL 14+ (with pgvector)
- Ollama (for local LLM)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/valora-ai.git
cd valora-ai
```

2. **Backend Setup**
```bash
cd backend
pip install -r requirements.txt

# Create config from template
cp config/pricing_config.template.json config/pricing_config.json

# Set environment variables
cp .env.example .env
# Edit .env with your credentials
```

3. **Frontend Setup**
```bash
npm install
```

4. **Database Setup**
```bash
# Create database
createdb valora

# Run migrations (if any)
python backend/database/init_db.py
```

5. **Start Services**
```bash
# Terminal 1: Backend
cd backend
python server.py

# Terminal 2: Frontend
npm run dev
```

6. **Access Application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 📊 Usage-Based Monetization

### Pricing Model

| Action | Units | Price (Promo) | Price (Regular) |
|--------|-------|---------------|-----------------|
| Basic Chat | 1 | ₹2 | ₹10 |
| Property Search | 2 | ₹4 | ₹20 |
| Area Analysis | 3 | ₹6 | ₹30 |
| Valuation | 10 | ₹20 | ₹100 |
| Storyboard | 15 | ₹30 | ₹150 |
| Report Export | 20 | ₹40 | ₹200 |
| Simulation | 25 | ₹50 | ₹250 |

### Subscription Tiers

| Tier | Monthly Units | Price (Promo) | Price (Regular) |
|------|---------------|---------------|-----------------|
| Free | 50 | ₹0 | ₹0 |
| Pro | 1,000 | ₹599 | ₹2,999 |
| Team | 3,000/seat | ₹999 | ₹4,999 |
| Enterprise | Unlimited | Custom | Custom |

**Launch Promo:** 80% off until March 31, 2026

---

## 🔧 Admin Panel

### Pricing Configuration

Admins can update pricing without code changes:

1. Login as admin
2. Navigate to Admin Panel → Pricing Configuration
3. Update action costs, tier limits, or promotional pricing
4. Click "Save & Reload" (no server restart needed)

**API Endpoints:**
```bash
# Get pricing config
GET /api/admin/pricing/config

# Update pricing
POST /api/admin/pricing/config
{
  "action_costs": {
    "chat_query": 2,
    "valuation": 15
  }
}

# Reload config
POST /api/admin/pricing/reload
```

### Training Data Management

Export anonymized training data for ML:

```bash
# Get stats
GET /api/admin/training-data/stats

# Export data
POST /api/admin/training-data/export
{
  "data_type": "queries",
  "limit": 1000
}
```

---

## 🏗️ Architecture

### Backend Structure
```
backend/
├── config/                    # Admin-editable configs
│   └── pricing_config.json   # Pricing & tier limits
├── database/                  # Database services
├── city_intelligence/         # City analysis modules
├── middleware/                # Request middleware
│   └── usage_middleware.py   # Auto-charging
├── training_data/             # ML training data (gitignored)
├── usage_tracker.py           # Usage tracking & balance
├── data_collector.py          # Training data collection
├── admin_routes.py            # Admin API endpoints
├── auth_routes.py             # Authentication
├── payment_routes.py          # Payment processing
└── server.py                  # Main FastAPI app
```

### Frontend Structure
```
src/
├── components/
│   ├── AdminPanel.jsx         # Admin dashboard
│   ├── PricingManager.jsx     # Pricing config UI
│   ├── UsageDashboard.jsx     # User usage stats
│   └── Cesium3DMap.jsx        # 3D visualization
└── contexts/
    └── AuthContext.jsx        # Authentication state
```

---

## 🔒 Security Features

- ✅ **Rate Limiting** - 100 requests/min per user
- ✅ **Input Validation** - All parameters sanitized
- ✅ **Admin Authentication** - JWT + RBAC
- ✅ **Balance Protection** - Max 10,000 units per addition
- ✅ **SQL Injection Prevention** - Parameterized queries
- ✅ **Audit Logging** - All admin actions logged
- ✅ **Data Anonymization** - Hashed IDs, generalized locations

---

## 📚 Documentation

- [Business Model & Plan](docs/BUSINESS_MODEL_AND_PLAN.md)
- [Usage-Based Monetization](docs/USAGE_BASED_MONETIZATION.md)
- [Backend Organization](docs/BACKEND_ORGANIZATION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API Documentation](http://localhost:8000/docs) (when running)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 Environment Variables

Create `.env` file:

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

---

## 🐛 Known Issues

- Training data export limited to 10,000 samples per request
- Pricing reload requires active sessions to refresh
- 3D building loading may be slow for large datasets

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- CesiumJS for 3D visualization
- FastAPI for backend framework
- Ollama for local LLM support
- Stripe for metered billing API

---

## 📧 Contact

- Website: https://valora.ai
- Email: support@valora.ai
- Twitter: [@ValoraAI](https://twitter.com/ValoraAI)

---

**Built with ❤️ for the real estate intelligence community**
