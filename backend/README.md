# REALTY-GPT Backend

## 🏗️ Architecture

The REALTY-GPT backend is a comprehensive real estate analytics platform powered by AI and machine learning.

### Directory Structure

```
backend/
├── api/                 # FastAPI endpoints
│   └── main.py         # Main API application
├── services/           # Core business logic
│   ├── dmpe_engine.py  # Dynamic Market Prediction Engine
│   ├── data_processor.py # Data processing and validation
│   └── mappls_integration.py # Mappls API integration
├── models/             # Trained ML models (auto-created)
├── data/              # Data storage (auto-created)
├── utils/             # Utilities
│   ├── config.py      # Configuration management
│   └── logger.py      # Logging setup
├── tests/             # Test cases
└── logs/              # Application logs (auto-created)
```

## 🚀 Features

### Core Capabilities

1. **Price Prediction** - XGBoost-based price forecasting
2. **Rental Yield Analysis** - Gradient Boosting rental yield predictions
3. **Demand Index** - Random Forest demand scoring
4. **Market Analysis** - Comprehensive market insights
5. **Portfolio Optimization** - Multi-property portfolio analysis
6. **Risk Assessment** - Property investment risk evaluation
7. **Spatial Intelligence** - Mappls-powered location features
8. **Time Series Forecasting** - Future price trends

### API Endpoints

#### Prediction & Analysis
- `POST /api/forecast` - Comprehensive property forecast
- `POST /api/demand` - Demand index calculation
- `POST /api/rental-yield` - Rental yield analysis
- `POST /api/risk` - Risk assessment

#### Market Intelligence
- `POST /api/market-analysis` - Market analysis (hotspots, growth zones)
- `POST /api/recommend` - Property recommendations
- `POST /api/portfolio/optimize` - Portfolio optimization

#### System
- `GET /health` - Health check
- `POST /api/train` - Trigger model training

## 📦 Installation

### Prerequisites

- Python 3.8+
- pip
- Virtual environment (recommended)

### Setup

1. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
cd backend
pip install -r requirements.txt
```

3. **Configure environment variables**
Create a `.env` file in the project root:
```env
# Mappls API
MAPPLS_API_KEY=your_mappls_api_key

# Pinecone (for RAG)
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX=valora-realestate

# OpenRouter (for LLM)
OPENROUTER_API_KEY=your_openrouter_api_key

# Optional
LOG_LEVEL=INFO
```

## 🏃 Running the Backend

### Development Mode

```bash
python backend/start_backend.py
```

Or directly with uvicorn:
```bash
uvicorn backend.api.main:app --reload --port 8000
```

### Production Mode

```bash
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🧪 Testing

### Run Tests
```bash
cd backend
pytest tests/
```

### Test Coverage
```bash
pytest --cov=backend tests/
```

## 📊 API Usage Examples

### 1. Price Forecast

```python
import requests

url = "http://localhost:8000/api/forecast"
data = {
    "property": {
        "city": "Bangalore",
        "locality": "Koramangala",
        "property_type": "apartment",
        "bedrooms": 3,
        "bathrooms": 2,
        "area_sqft": 1500,
        "latitude": 12.9352,
        "longitude": 77.6245
    },
    "forecast_months": 12,
    "include_comparables": True,
    "include_market_trends": True
}

response = requests.post(url, json=data)
print(response.json())
```

### 2. Demand Index

```python
url = "http://localhost:8000/api/demand"
data = {
    "city": "Mumbai",
    "locality": "Andheri East",
    "property_type": "apartment",
    "bedrooms": 2,
    "area_sqft": 1000,
    "latitude": 19.1136,
    "longitude": 72.8697
}

response = requests.post(url, json=data)
print(response.json())
```

### 3. Market Analysis

```python
url = "http://localhost:8000/api/market-analysis"
data = {
    "city": "Delhi",
    "analysis_type": "hotspots",
    "property_types": ["apartment", "house"],
    "price_range": {
        "min": 5000000,
        "max": 20000000
    }
}

response = requests.post(url, json=data)
print(response.json())
```

## 🔧 Model Training

The system includes three main models:

1. **Price Model** (XGBoost)
   - Features: Property + Spatial + Market
   - Target: Property price
   - Metrics: MAE, RMSE, R², MAPE

2. **Rental Yield Model** (Gradient Boosting)
   - Features: Property + Spatial
   - Target: Rental yield percentage
   - Metrics: MAE, RMSE, R²

3. **Demand Model** (Random Forest)
   - Features: Spatial + Market
   - Target: Demand index (0-100)
   - Metrics: MAE, RMSE, R²

### Trigger Training

```bash
curl -X POST http://localhost:8000/api/train
```

## 📈 Performance Metrics

- **Response Time**: < 500ms for predictions
- **Model Accuracy**: R² > 0.85 for price predictions
- **Scalability**: Handles 100+ requests/second
- **Cache Hit Rate**: > 80% for repeated queries

## 🛠️ Development

### Adding New Features

1. Add feature to `FEATURE_CONFIGS` in `utils/config.py`
2. Update feature engineering in `services/dmpe_engine.py`
3. Retrain models with new features

### Adding New Endpoints

1. Create endpoint in `api/main.py`
2. Add business logic to appropriate service
3. Update API documentation

### Debugging

Enable debug logging:
```env
LOG_LEVEL=DEBUG
```

Check logs:
```bash
tail -f backend/logs/app.log
```

## 📝 API Documentation

When the server is running, access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🚨 Error Handling

The API uses standard HTTP status codes:
- `200`: Success
- `400`: Bad Request
- `404`: Not Found
- `500`: Internal Server Error

Error responses include:
```json
{
    "status": "error",
    "detail": "Error description",
    "timestamp": "2024-01-01T00:00:00"
}
```

## 🔐 Security

- API key authentication (optional)
- Rate limiting: 100 requests/minute
- Input validation with Pydantic
- SQL injection prevention
- XSS protection

## 📊 Monitoring

- Health check endpoint
- Request/response logging
- Model performance tracking
- Error tracking

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit pull request

## 📄 License

MIT License - See LICENSE file for details
