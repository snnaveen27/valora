"""
Production Configuration for Valora Backend
Optimized settings for performance, security, and reliability
"""

import os
from typing import Dict, Any

# Server Configuration
SERVER_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "workers": 4,  # Number of worker processes
    "timeout": 120,  # Request timeout in seconds
    "keepalive": 5,  # Keep-alive timeout
    "max_requests": 1000,  # Restart worker after N requests (memory leak protection)
    "max_requests_jitter": 50,  # Add randomness to max_requests
}

# CORS Configuration
CORS_CONFIG = {
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["*"],
    "max_age": 3600,  # Cache preflight requests for 1 hour
}

# Cache Configuration
CACHE_CONFIG = {
    "geocoding_ttl": 86400,  # 24 hours
    "terrain_ttl": 3600,  # 1 hour
    "property_ttl": 1800,  # 30 minutes
    "analysis_ttl": 600,  # 10 minutes
    "max_cache_size": 1000,  # Maximum number of cached items
}

# Database Connection Pool
DB_POOL_CONFIG = {
    "min_size": 5,
    "max_size": 20,
    "timeout": 30,
    "command_timeout": 60,
}

# Rate Limiting
RATE_LIMIT_CONFIG = {
    "enabled": True,
    "requests_per_minute": 60,
    "burst_size": 10,
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/valora_backend.log",
    "max_bytes": 10485760,  # 10MB
    "backup_count": 5,
}

# Performance Optimization
PERFORMANCE_CONFIG = {
    "enable_gzip": True,
    "gzip_min_size": 1024,  # Compress responses larger than 1KB
    "enable_etag": True,
    "enable_response_cache": True,
    "async_workers": True,
}

# Security Configuration
SECURITY_CONFIG = {
    "enable_https_redirect": os.getenv("ENABLE_HTTPS_REDIRECT", "false").lower() == "true",
    "enable_hsts": True,
    "hsts_max_age": 31536000,  # 1 year
    "enable_cors": True,
    "trusted_hosts": ["*"],  # Configure for production
}

def get_production_config() -> Dict[str, Any]:
    """Get complete production configuration"""
    return {
        "server": SERVER_CONFIG,
        "cors": CORS_CONFIG,
        "cache": CACHE_CONFIG,
        "db_pool": DB_POOL_CONFIG,
        "rate_limit": RATE_LIMIT_CONFIG,
        "logging": LOGGING_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "security": SECURITY_CONFIG,
    }
