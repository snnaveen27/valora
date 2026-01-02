"""
Startup script for REALTY-GPT Backend
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path.parent))

from backend.utils.logger import setup_logger
from backend.utils.config import settings


def _reload_enabled() -> bool:
    """Determine whether uvicorn reload should be enabled."""
    env_override = os.getenv("VALORA_BACKEND_RELOAD")
    if env_override is not None:
        return env_override not in {"0", "false", "False"}
    return True

# Setup logging
logger = setup_logger(
    name="backend_startup",
    log_level=settings.log_level,
    log_file=settings.log_file
)

def main():
    """Start the backend server"""
    logger.info("Starting REALTY-GPT Backend...")
    logger.info(f"API Title: {settings.api_title}")
    logger.info(f"API Version: {settings.api_version}")
    logger.info(f"Host: {settings.api_host}")
    logger.info(f"Port: {settings.api_port}")
    
    # Check for required environment variables
    if not settings.mappls_api_key:
        logger.warning("MAPPLS_API_KEY not set - Mappls features will be limited")
    
    if not settings.pinecone_api_key:
        logger.warning("PINECONE_API_KEY not set - RAG features will be disabled")
    
    if not settings.openrouter_api_key:
        logger.warning("OPENROUTER_API_KEY not set - LLM features will be disabled")
    
    # Start the server
    try:
        uvicorn.run(
            "backend.api.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=_reload_enabled(),
            log_level=settings.log_level.lower()
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
