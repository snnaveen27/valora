"""
Configuration management for REALTY-GPT backend
"""

import os
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings"""
    
    def __init__(self):
        # API Configuration
        self.api_title = "REALTY-GPT API"
        self.api_version = "2.0.0"
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        
        # DMPE Configuration
        self.dmpe_models_dir = "data/models"
        self.dmpe_data_dir = "data"
        self.dmpe_cache_size = 1000
        
        # Mappls Configuration
        self.mappls_api_key = os.getenv("MAPPLS_API_KEY", os.getenv("VITE_MAPPLS_API_KEY", ""))
        self.mappls_base_url = "https://apis.mappls.com"
        self.mappls_timeout = 10
        
        # OpenRouter Configuration (for LLM)
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-opus")
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
        
        # Pinecone Configuration
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY", "")
        self.pinecone_environment = os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp-free")
        self.pinecone_index = os.getenv("PINECONE_INDEX", "valora-realestate")
        
        # Database Configuration (Cloud-first: Supabase)
        self.database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/valora_ai")
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        
        # Redis Configuration (Cloud-first: Upstash)
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.upstash_redis_rest_url = os.getenv("UPSTASH_REDIS_REST_URL", "")
        self.upstash_redis_rest_token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        self.cache_ttl = 3600  # seconds
        
        # Cloudflare R2 Storage Configuration
        self.r2_account_id = os.getenv("R2_ACCOUNT_ID", "")
        self.r2_access_key_id = os.getenv("R2_ACCESS_KEY_ID", "")
        self.r2_secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY", "")
        self.r2_bucket_name = os.getenv("R2_BUCKET_NAME", "valora-storage")
        self.r2_endpoint = os.getenv("R2_ENDPOINT", "")
        
        # CORS Settings
        cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:3001")
        self.cors_origins = cors_origins_str.split(",")
        
        # Model Training Settings
        self.train_test_split = 0.2
        self.random_seed = 42
        self.max_training_samples = 100000
        
        # Prediction Settings
        self.default_confidence = 0.75
        self.price_prediction_range = 0.1  # +/- 10%
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = "backend/logs/app.log"
        
        # Feature Flags
        self.enable_caching = True
        self.enable_async_processing = True
        self.enable_model_monitoring = True
        self.enable_data_validation = True
        
        # Rate Limiting
        self.rate_limit_requests = 100
        self.rate_limit_period = 60  # seconds
        
        # File Upload Settings
        self.max_upload_size = 50 * 1024 * 1024  # 50 MB
        self.allowed_file_types = [".csv", ".xlsx", ".json", ".parquet"]

# Singleton instance
settings = Settings()

# Path configurations
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
MODELS_DIR = PROJECT_ROOT / "data" / "models"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = BACKEND_ROOT / "logs"

# Create directories if they don't exist
for dir_path in [MODELS_DIR, DATA_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Model configurations
MODEL_CONFIGS = {
    "price_model": {
        "type": "xgboost",
        "params": {
            "n_estimators": 200,
            "learning_rate": 0.05,
            "max_depth": 6,
            "random_state": 42
        }
    },
    "rental_yield_model": {
        "type": "gradient_boosting",
        "params": {
            "n_estimators": 150,
            "learning_rate": 0.1,
            "max_depth": 5,
            "random_state": 42
        }
    },
    "demand_model": {
        "type": "random_forest",
        "params": {
            "n_estimators": 100,
            "max_depth": 8,
            "random_state": 42
        }
    }
}

# Feature configurations
FEATURE_CONFIGS = {
    "spatial_features": [
        "distance_to_metro",
        "distance_to_hospital",
        "distance_to_school",
        "distance_to_mall",
        "distance_to_airport",
        "distance_to_railway",
        "poi_density",
        "infrastructure_score",
        "connectivity_score",
        "lifestyle_score"
    ],
    "property_features": [
        "bedrooms",
        "bathrooms",
        "area_sqft",
        "floor",
        "total_floors",
        "age_years",
        "parking_spaces",
        "balconies"
    ],
    "market_features": [
        "avg_price_locality",
        "price_growth_3m",
        "price_growth_6m",
        "listings_count",
        "absorption_rate",
        "days_on_market"
    ]
}

# API Response Messages
MESSAGES = {
    "success": "Request processed successfully",
    "error": "An error occurred while processing the request",
    "not_found": "Resource not found",
    "invalid_input": "Invalid input provided",
    "model_not_trained": "Model not yet trained, using default values",
    "api_limit_exceeded": "API rate limit exceeded",
    "unauthorized": "Unauthorized access"
}
