"""
Error Logging Service
Centralized error tracking and logging for admin monitoring.
"""

import os
import json
import logging
import traceback
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import threading
import uuid

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for filtering"""
    API = "api"
    DATABASE = "database"
    AUTH = "auth"
    VOICE = "voice"
    LLM = "llm"
    SCRAPING = "scraping"
    MAP = "map"
    PREDICTION = "prediction"
    AGENT = "agent"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorLog:
    """Single error log entry"""
    id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    details: Optional[str] = None
    stack_trace: Optional[str] = None
    endpoint: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data


class ErrorLoggingService:
    """
    Centralized error logging service for admin monitoring.
    
    Features:
    - In-memory error storage (last 1000 errors)
    - Error categorization and severity levels
    - Error resolution tracking
    - Statistics and aggregations
    - Thread-safe operations
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._errors: deque = deque(maxlen=1000)  # Keep last 1000 errors
        self._error_counts: Dict[str, int] = {}
        self._lock = threading.Lock()
        self._initialized = True
        
        # Log service initialization
        self.log_info(
            category=ErrorCategory.SYSTEM,
            message="Error logging service initialized",
            metadata={"max_errors": 1000}
        )
    
    def _generate_id(self) -> str:
        """Generate unique error ID"""
        return f"err_{uuid.uuid4().hex[:12]}"
    
    def log_error(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[str] = None,
        exception: Optional[Exception] = None,
        endpoint: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ErrorLog:
        """
        Log an error.
        
        Args:
            message: Error message
            category: Error category for filtering
            severity: Error severity level
            details: Additional details
            exception: Exception object (will extract stack trace)
            endpoint: API endpoint where error occurred
            user_id: User ID if available
            request_id: Request ID for tracing
            metadata: Additional metadata
            
        Returns:
            ErrorLog entry
        """
        stack_trace = None
        if exception:
            stack_trace = ''.join(traceback.format_exception(
                type(exception), exception, exception.__traceback__
            ))
            if not details:
                details = str(exception)
        
        error = ErrorLog(
            id=self._generate_id(),
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            message=message,
            details=details,
            stack_trace=stack_trace,
            endpoint=endpoint,
            user_id=user_id,
            request_id=request_id,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._errors.appendleft(error)
            
            # Update counts
            key = f"{category.value}:{severity.value}"
            self._error_counts[key] = self._error_counts.get(key, 0) + 1
        
        # Also log to standard logger
        log_method = getattr(logger, severity.value, logger.error)
        log_method(f"[{category.value}] {message}")
        
        return error
    
    def log_warning(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        **kwargs
    ) -> ErrorLog:
        """Log a warning"""
        return self.log_error(
            message=message,
            category=category,
            severity=ErrorSeverity.WARNING,
            **kwargs
        )
    
    def log_info(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        **kwargs
    ) -> ErrorLog:
        """Log an info message"""
        return self.log_error(
            message=message,
            category=category,
            severity=ErrorSeverity.INFO,
            **kwargs
        )
    
    def log_critical(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        **kwargs
    ) -> ErrorLog:
        """Log a critical error"""
        return self.log_error(
            message=message,
            category=category,
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )
    
    def get_errors(
        self,
        limit: int = 100,
        offset: int = 0,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        resolved: Optional[bool] = None,
        since: Optional[datetime] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get errors with filtering.
        
        Args:
            limit: Maximum number of errors to return
            offset: Offset for pagination
            severity: Filter by severity
            category: Filter by category
            resolved: Filter by resolved status
            since: Only errors after this time
            search: Search in message and details
            
        Returns:
            List of error dictionaries
        """
        with self._lock:
            errors = list(self._errors)
        
        # Apply filters
        if severity:
            errors = [e for e in errors if e.severity == severity]
        
        if category:
            errors = [e for e in errors if e.category == category]
        
        if resolved is not None:
            errors = [e for e in errors if e.resolved == resolved]
        
        if since:
            errors = [e for e in errors if e.timestamp >= since]
        
        if search:
            search_lower = search.lower()
            errors = [
                e for e in errors 
                if search_lower in e.message.lower() 
                or (e.details and search_lower in e.details.lower())
            ]
        
        # Apply pagination
        paginated = errors[offset:offset + limit]
        
        return [e.to_dict() for e in paginated]
    
    def get_error_by_id(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific error by ID"""
        with self._lock:
            for error in self._errors:
                if error.id == error_id:
                    return error.to_dict()
        return None
    
    def resolve_error(
        self,
        error_id: str,
        resolved_by: Optional[str] = None
    ) -> bool:
        """Mark an error as resolved"""
        with self._lock:
            for error in self._errors:
                if error.id == error_id:
                    error.resolved = True
                    error.resolved_at = datetime.now()
                    error.resolved_by = resolved_by
                    return True
        return False
    
    def resolve_all(
        self,
        category: Optional[ErrorCategory] = None,
        resolved_by: Optional[str] = None
    ) -> int:
        """Resolve all errors, optionally filtered by category"""
        count = 0
        with self._lock:
            for error in self._errors:
                if not error.resolved:
                    if category is None or error.category == category:
                        error.resolved = True
                        error.resolved_at = datetime.now()
                        error.resolved_by = resolved_by
                        count += 1
        return count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        with self._lock:
            errors = list(self._errors)
        
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(weeks=1)
        
        # Count by time period
        last_hour = [e for e in errors if e.timestamp >= hour_ago]
        last_day = [e for e in errors if e.timestamp >= day_ago]
        last_week = [e for e in errors if e.timestamp >= week_ago]
        
        # Count by severity
        by_severity = {}
        for sev in ErrorSeverity:
            by_severity[sev.value] = len([e for e in errors if e.severity == sev])
        
        # Count by category
        by_category = {}
        for cat in ErrorCategory:
            by_category[cat.value] = len([e for e in errors if e.category == cat])
        
        # Unresolved counts
        unresolved = [e for e in errors if not e.resolved]
        unresolved_critical = [e for e in unresolved if e.severity == ErrorSeverity.CRITICAL]
        unresolved_errors = [e for e in unresolved if e.severity == ErrorSeverity.ERROR]
        
        return {
            "total_errors": len(errors),
            "unresolved_count": len(unresolved),
            "unresolved_critical": len(unresolved_critical),
            "unresolved_errors": len(unresolved_errors),
            "last_hour": len(last_hour),
            "last_day": len(last_day),
            "last_week": len(last_week),
            "by_severity": by_severity,
            "by_category": by_category,
            "recent_errors": [e.to_dict() for e in errors[:5]]
        }
    
    def clear_resolved(self) -> int:
        """Clear all resolved errors"""
        with self._lock:
            original_count = len(self._errors)
            self._errors = deque(
                [e for e in self._errors if not e.resolved],
                maxlen=1000
            )
            return original_count - len(self._errors)
    
    def export_errors(
        self,
        format: str = "json",
        since: Optional[datetime] = None
    ) -> str:
        """Export errors to JSON"""
        errors = self.get_errors(limit=1000, since=since)
        return json.dumps(errors, indent=2, default=str)


# Singleton instance
_error_service: Optional[ErrorLoggingService] = None


def get_error_service() -> ErrorLoggingService:
    """Get singleton error logging service"""
    global _error_service
    if _error_service is None:
        _error_service = ErrorLoggingService()
    return _error_service


def log_error(message: str, **kwargs) -> ErrorLog:
    """Convenience function to log an error"""
    return get_error_service().log_error(message, **kwargs)


def log_warning(message: str, **kwargs) -> ErrorLog:
    """Convenience function to log a warning"""
    return get_error_service().log_warning(message, **kwargs)


def log_critical(message: str, **kwargs) -> ErrorLog:
    """Convenience function to log a critical error"""
    return get_error_service().log_critical(message, **kwargs)
