"""
Valora AI - Structured Logging Configuration
Replaces scattered print() statements with proper Python logging.

Usage in any module:
    import logging
    logger = logging.getLogger("valora.module_name")
    logger.info("message")
    logger.error("message", exc_info=True)
"""

import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO", log_file: str = None):
    """
    Configure structured logging for the entire Valora backend.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path to also write logs to
    """
    fmt = "[%(asctime)s] %(levelname)-7s %(name)-20s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
        force=True,
    )

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)

    root = logging.getLogger("valora")
    root.info("Logging initialized (level=%s)", level)
    return root
