"""
Valora AI - Observability & Metrics
Lightweight metrics collection and logging for monitoring.

Features:
- Request latency tracking
- Error rate monitoring
- Endpoint usage metrics
- Verifier mismatch tracking
- Database operation latency
- Model inference latency

For production, integrate with:
- Prometheus for metrics
- OpenTelemetry for tracing
- ELK/Loki for logs
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps
from contextlib import contextmanager
import json


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("valora")


@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels
        }


@dataclass
class LatencyStats:
    """Latency statistics for an endpoint/operation."""
    count: int = 0
    total_ms: float = 0
    min_ms: float = float('inf')
    max_ms: float = 0
    p50_samples: List[float] = field(default_factory=list)
    p95_samples: List[float] = field(default_factory=list)
    p99_samples: List[float] = field(default_factory=list)
    errors: int = 0
    
    def record(self, latency_ms: float, is_error: bool = False):
        self.count += 1
        self.total_ms += latency_ms
        self.min_ms = min(self.min_ms, latency_ms)
        self.max_ms = max(self.max_ms, latency_ms)
        
        # Keep last 1000 samples for percentile calculation
        self.p50_samples.append(latency_ms)
        if len(self.p50_samples) > 1000:
            self.p50_samples = self.p50_samples[-1000:]
        
        if is_error:
            self.errors += 1
    
    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count > 0 else 0
    
    @property
    def p50(self) -> float:
        if not self.p50_samples:
            return 0
        sorted_samples = sorted(self.p50_samples)
        idx = int(len(sorted_samples) * 0.5)
        return sorted_samples[idx]
    
    @property
    def p95(self) -> float:
        if not self.p50_samples:
            return 0
        sorted_samples = sorted(self.p50_samples)
        idx = int(len(sorted_samples) * 0.95)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]
    
    @property
    def p99(self) -> float:
        if not self.p50_samples:
            return 0
        sorted_samples = sorted(self.p50_samples)
        idx = int(len(sorted_samples) * 0.99)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]
    
    @property
    def error_rate(self) -> float:
        return (self.errors / self.count * 100) if self.count > 0 else 0
    
    def to_dict(self) -> Dict:
        return {
            "count": self.count,
            "avg_ms": round(self.avg_ms, 2),
            "min_ms": round(self.min_ms, 2) if self.min_ms != float('inf') else 0,
            "max_ms": round(self.max_ms, 2),
            "p50_ms": round(self.p50, 2),
            "p95_ms": round(self.p95, 2),
            "p99_ms": round(self.p99, 2),
            "errors": self.errors,
            "error_rate_pct": round(self.error_rate, 2)
        }


class MetricsCollector:
    """
    Collects and aggregates metrics for Valora AI.
    
    Metrics tracked:
    - Request latency by endpoint
    - Database operation latency
    - Model inference latency
    - Verifier mismatch rate
    - Error counts by type
    """
    
    def __init__(self):
        self._endpoint_latency: Dict[str, LatencyStats] = defaultdict(LatencyStats)
        self._db_latency: Dict[str, LatencyStats] = defaultdict(LatencyStats)
        self._model_latency: Dict[str, LatencyStats] = defaultdict(LatencyStats)
        self._verifier_stats = {
            "total_claims": 0,
            "verified": 0,
            "unverified": 0,
            "partial": 0,
            "errors": 0
        }
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._start_time = time.time()
    
    def record_request(self, endpoint: str, latency_ms: float, status_code: int = 200):
        """Record a request to an endpoint."""
        is_error = status_code >= 400
        self._endpoint_latency[endpoint].record(latency_ms, is_error)
        
        if is_error:
            self._error_counts[f"http_{status_code}"] += 1
        
        self._counters["total_requests"] += 1
    
    def record_db_operation(self, operation: str, latency_ms: float, is_error: bool = False):
        """Record a database operation."""
        self._db_latency[operation].record(latency_ms, is_error)
        
        if is_error:
            self._error_counts["db_error"] += 1
    
    def record_model_inference(self, model: str, latency_ms: float, is_error: bool = False):
        """Record a model inference."""
        self._model_latency[model].record(latency_ms, is_error)
        
        if is_error:
            self._error_counts["model_error"] += 1
    
    def record_verification(self, status: str, claim_count: int = 1):
        """Record fact verification result."""
        self._verifier_stats["total_claims"] += claim_count
        
        if status == "verified":
            self._verifier_stats["verified"] += claim_count
        elif status == "unverified":
            self._verifier_stats["unverified"] += claim_count
        elif status == "partially_verified":
            self._verifier_stats["partial"] += claim_count
        elif status == "error":
            self._verifier_stats["errors"] += claim_count
    
    def increment_counter(self, name: str, value: int = 1):
        """Increment a counter metric."""
        self._counters[name] += value
    
    def set_gauge(self, name: str, value: float):
        """Set a gauge metric."""
        self._gauges[name] = value
    
    def get_endpoint_stats(self, endpoint: str = None) -> Dict[str, Any]:
        """Get latency stats for endpoint(s)."""
        if endpoint:
            return {endpoint: self._endpoint_latency[endpoint].to_dict()}
        return {ep: stats.to_dict() for ep, stats in self._endpoint_latency.items()}
    
    def get_db_stats(self) -> Dict[str, Any]:
        """Get database operation stats."""
        return {op: stats.to_dict() for op, stats in self._db_latency.items()}
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get model inference stats."""
        return {model: stats.to_dict() for model, stats in self._model_latency.items()}
    
    def get_verifier_stats(self) -> Dict[str, Any]:
        """Get fact verifier stats."""
        total = self._verifier_stats["total_claims"]
        verified = self._verifier_stats["verified"]
        
        return {
            **self._verifier_stats,
            "verification_rate_pct": round(verified / total * 100, 2) if total > 0 else 0,
            "mismatch_rate_pct": round(self._verifier_stats["unverified"] / total * 100, 2) if total > 0 else 0
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get complete metrics summary."""
        uptime = time.time() - self._start_time
        
        # Calculate overall request stats
        total_requests = self._counters.get("total_requests", 0)
        total_errors = sum(self._error_counts.values())
        
        # Find slowest endpoints
        slowest_endpoints = sorted(
            [(ep, stats.p95) for ep, stats in self._endpoint_latency.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "uptime_seconds": round(uptime, 0),
            "total_requests": total_requests,
            "requests_per_minute": round(total_requests / (uptime / 60), 2) if uptime > 0 else 0,
            "total_errors": total_errors,
            "error_rate_pct": round(total_errors / total_requests * 100, 2) if total_requests > 0 else 0,
            "slowest_endpoints": [{"endpoint": ep, "p95_ms": round(lat, 2)} for ep, lat in slowest_endpoints],
            "verifier": self.get_verifier_stats(),
            "counters": dict(self._counters),
            "gauges": self._gauges,
            "error_breakdown": dict(self._error_counts)
        }
    
    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # Endpoint latency
        for endpoint, stats in self._endpoint_latency.items():
            safe_ep = endpoint.replace("/", "_").replace("-", "_")
            lines.append(f'valora_request_latency_ms{{endpoint="{endpoint}"}} {stats.avg_ms}')
            lines.append(f'valora_request_count{{endpoint="{endpoint}"}} {stats.count}')
            lines.append(f'valora_request_errors{{endpoint="{endpoint}"}} {stats.errors}')
        
        # Verifier stats
        for key, value in self._verifier_stats.items():
            lines.append(f'valora_verifier_{key} {value}')
        
        # Counters
        for name, value in self._counters.items():
            safe_name = name.replace("-", "_")
            lines.append(f'valora_counter_{safe_name} {value}')
        
        # Gauges
        for name, value in self._gauges.items():
            safe_name = name.replace("-", "_")
            lines.append(f'valora_gauge_{safe_name} {value}')
        
        return "\n".join(lines)
    
    def reset(self):
        """Reset all metrics."""
        self._endpoint_latency.clear()
        self._db_latency.clear()
        self._model_latency.clear()
        self._verifier_stats = {
            "total_claims": 0,
            "verified": 0,
            "unverified": 0,
            "partial": 0,
            "errors": 0
        }
        self._error_counts.clear()
        self._counters.clear()
        self._gauges.clear()
        self._start_time = time.time()


# Global metrics collector
_metrics = None


def get_metrics() -> MetricsCollector:
    """Get or create metrics collector singleton."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


@contextmanager
def track_latency(operation_type: str, name: str):
    """
    Context manager to track operation latency.
    
    Usage:
        with track_latency("endpoint", "/api/chat"):
            # do work
            pass
    """
    metrics = get_metrics()
    start = time.time()
    is_error = False
    
    try:
        yield
    except Exception as e:
        is_error = True
        raise
    finally:
        latency_ms = (time.time() - start) * 1000
        
        if operation_type == "endpoint":
            metrics.record_request(name, latency_ms, 500 if is_error else 200)
        elif operation_type == "db":
            metrics.record_db_operation(name, latency_ms, is_error)
        elif operation_type == "model":
            metrics.record_model_inference(name, latency_ms, is_error)


def track_endpoint(func: Callable):
    """Decorator to track endpoint latency."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        endpoint = func.__name__
        metrics = get_metrics()
        start = time.time()
        status_code = 200
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            status_code = 500
            raise
        finally:
            latency_ms = (time.time() - start) * 1000
            metrics.record_request(endpoint, latency_ms, status_code)
    
    return wrapper


def log_request(endpoint: str, method: str, user_id: str = "anonymous", extra: Dict = None):
    """Log a request with structured data."""
    log_data = {
        "event": "request",
        "endpoint": endpoint,
        "method": method,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }
    if extra:
        log_data.update(extra)
    
    logger.info(json.dumps(log_data))


def log_error(error_type: str, message: str, extra: Dict = None):
    """Log an error with structured data."""
    log_data = {
        "event": "error",
        "error_type": error_type,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    if extra:
        log_data.update(extra)
    
    logger.error(json.dumps(log_data))
    
    # Also increment error counter
    get_metrics().increment_counter(f"error_{error_type}")


def log_verification(status: str, claim_count: int, details: Dict = None):
    """Log a verification event."""
    log_data = {
        "event": "verification",
        "status": status,
        "claim_count": claim_count,
        "timestamp": datetime.now().isoformat()
    }
    if details:
        log_data.update(details)
    
    logger.info(json.dumps(log_data))
    
    # Update metrics
    get_metrics().record_verification(status, claim_count)
