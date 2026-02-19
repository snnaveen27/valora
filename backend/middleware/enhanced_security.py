"""
Enhanced Security Middleware for Valora AI
Comprehensive protection against common attacks and abuse.

Security Features:
1. Input Validation - SQL injection, XSS, command injection
2. Request Signing - Tamper-proof API requests
3. Abuse Detection - Pattern-based threat detection
4. Credit Protection - Prevent credit manipulation
5. Rate Limiting Enhancement - Smarter rate limiting
6. Audit Logging - Complete request audit trail
"""

import re
import time
import json
import hashlib
import hmac
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import threading

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("valora.security")


# =============================================================================
# SECURITY PATTERNS
# =============================================================================

# SQL Injection patterns
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b)",
    r"(--|\#|\/\*|\*\/)",
    r"(\bUNION\b.*\bSELECT\b)",
    r"(\bOR\b.*=.*)",
    r"(\bAND\b.*=.*)",
    r"('.*(\bOR\b|\bAND\b).*')",
    r"(;\s*$)",
    r"(\bEXEC\b|\bEXECUTE\b)",
    r"(\bXP_\w+)",
    r"(\bSP_\w+)",
]

# XSS patterns
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript\s*:",
    r"on\w+\s*=",
    r"<iframe",
    r"<object",
    r"<embed",
    r"<form",
    r"eval\s*\(",
    r"document\.",
    r"window\.",
    r"alert\s*\(",
]

# Command injection patterns
COMMAND_INJECTION_PATTERNS = [
    r"[;&|`$]",
    r"\b(cat|ls|pwd|whoami|id|uname|wget|curl|nc|bash|sh|python|perl|ruby)\b",
    r"\|\s*\w+",
    r">\s*/",
    r"\$\([^)]+\)",
    r"`[^`]+`",
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.\\",
    r"%2e%2e%2f",
    r"%2e%2e/",
    r"\.\.%2f",
    r"%252e",
]

# Suspicious user agents
SUSPICIOUS_USER_AGENTS = [
    r"sqlmap",
    r"nmap",
    r"nikto",
    r"masscan",
    r"zgrab",
    r"curl/",
    r"wget/",
    r"python-requests",
    r"go-http-client",
    r"java/",
]


# =============================================================================
# SECURITY DATA CLASSES
# =============================================================================

@dataclass
class SecurityEvent:
    """Security event for logging."""
    timestamp: float
    event_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    ip_address: str
    user_id: str
    endpoint: str
    details: Dict[str, Any]
    blocked: bool = False


@dataclass
class ThreatScore:
    """Threat score for a request."""
    score: int  # 0-100
    reasons: List[str] = field(default_factory=list)
    blocked: bool = False
    
    def add_reason(self, reason: str, points: int = 10):
        self.score = min(100, self.score + points)
        self.reasons.append(reason)
        if self.score >= 80:
            self.blocked = True


# =============================================================================
# INPUT VALIDATOR
# =============================================================================

class InputValidator:
    """Validates and sanitizes user input."""
    
    def __init__(self):
        self.sql_patterns = [re.compile(p, re.IGNORECASE) for p in SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(p, re.IGNORECASE) for p in XSS_PATTERNS]
        self.cmd_patterns = [re.compile(p, re.IGNORECASE) for p in COMMAND_INJECTION_PATTERNS]
        self.path_patterns = [re.compile(p, re.IGNORECASE) for p in PATH_TRAVERSAL_PATTERNS]
    
    def validate_string(self, value: str, field_name: str = "input") -> ThreatScore:
        """Validate a string input for threats."""
        threat = ThreatScore(score=0)
        
        # Check SQL injection
        for pattern in self.sql_patterns:
            if pattern.search(value):
                threat.add_reason(f"SQL injection pattern in {field_name}", 30)
                break
        
        # Check XSS
        for pattern in self.xss_patterns:
            if pattern.search(value):
                threat.add_reason(f"XSS pattern in {field_name}", 25)
                break
        
        # Check command injection
        for pattern in self.cmd_patterns:
            if pattern.search(value):
                threat.add_reason(f"Command injection pattern in {field_name}", 35)
                break
        
        # Check path traversal
        for pattern in self.path_patterns:
            if pattern.search(value):
                threat.add_reason(f"Path traversal pattern in {field_name}", 30)
                break
        
        return threat
    
    def validate_dict(self, data: Dict, prefix: str = "") -> ThreatScore:
        """Recursively validate a dictionary."""
        threat = ThreatScore(score=0)
        
        for key, value in data.items():
            field_name = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, str):
                sub_threat = self.validate_string(value, field_name)
                threat.score += sub_threat.score
                threat.reasons.extend(sub_threat.reasons)
            elif isinstance(value, dict):
                sub_threat = self.validate_dict(value, field_name)
                threat.score += sub_threat.score
                threat.reasons.extend(sub_threat.reasons)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        sub_threat = self.validate_string(item, f"{field_name}[{i}]")
                        threat.score += sub_threat.score
                        threat.reasons.extend(sub_threat.reasons)
        
        if threat.score >= 80:
            threat.blocked = True
        
        return threat
    
    def sanitize_string(self, value: str) -> str:
        """Sanitize a string by removing dangerous patterns."""
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Escape HTML entities
        value = value.replace('<', '<').replace('>', '>')
        value = value.replace('"', '"').replace("'", '&#x27;')
        
        # Remove control characters
        value = ''.join(c for c in value if ord(c) >= 32 or c in '\n\r\t')
        
        return value


# =============================================================================
# ABUSE DETECTOR
# =============================================================================

class AbuseDetector:
    """Detects abusive patterns and attacks."""
    
    def __init__(self):
        self.request_history: Dict[str, List[float]] = defaultdict(list)
        self.failed_attempts: Dict[str, List[float]] = defaultdict(list)
        self.blocked_ips: Set[str] = set()
        self.suspicious_ips: Dict[str, int] = defaultdict(int)
        
        # Thresholds
        self.max_requests_per_minute = 60
        self.max_failed_attempts = 10
        self.block_duration = 3600  # 1 hour
        self.suspicious_threshold = 5
        
        self._lock = threading.Lock()
    
    def check_request(self, ip: str, user_id: str, endpoint: str) -> ThreatScore:
        """Check if a request is suspicious."""
        threat = ThreatScore(score=0)
        now = time.time()
        
        with self._lock:
            # Check if IP is blocked
            if ip in self.blocked_ips:
                threat.add_reason("IP is blocked", 100)
                threat.blocked = True
                return threat
            
            # Check request rate
            recent_requests = [t for t in self.request_history[ip] if now - t < 60]
            if len(recent_requests) > self.max_requests_per_minute:
                threat.add_reason(f"Rate limit exceeded: {len(recent_requests)} requests/min", 40)
            
            # Check failed attempts
            recent_failures = [t for t in self.failed_attempts[ip] if now - t < 300]
            if len(recent_failures) > self.max_failed_attempts:
                threat.add_reason(f"Too many failed attempts: {len(recent_failures)}", 50)
            
            # Record request
            self.request_history[ip].append(now)
            
            # Cleanup old entries
            self.request_history[ip] = [t for t in self.request_history[ip] if now - t < 3600]
        
        return threat
    
    def record_failure(self, ip: str, reason: str = ""):
        """Record a failed attempt."""
        now = time.time()
        
        with self._lock:
            self.failed_attempts[ip].append(now)
            
            # Increment suspicious score
            self.suspicious_ips[ip] += 1
            
            # Auto-block if threshold exceeded
            if self.suspicious_ips[ip] > self.suspicious_threshold:
                self.blocked_ips.add(ip)
                logger.warning(f"Auto-blocked IP {ip} for suspicious activity")
            
            # Cleanup old entries
            self.failed_attempts[ip] = [t for t in self.failed_attempts[ip] if now - t < 3600]
    
    def record_success(self, ip: str):
        """Record a successful request (reduces suspicion)."""
        with self._lock:
            if ip in self.suspicious_ips:
                self.suspicious_ips[ip] = max(0, self.suspicious_ips[ip] - 1)
    
    def is_blocked(self, ip: str) -> bool:
        """Check if an IP is blocked."""
        return ip in self.blocked_ips
    
    def unblock_ip(self, ip: str):
        """Manually unblock an IP."""
        with self._lock:
            self.blocked_ips.discard(ip)
            self.suspicious_ips[ip] = 0
            self.failed_attempts[ip] = []


# =============================================================================
# REQUEST SIGNER
# =============================================================================

class RequestSigner:
    """Signs and verifies API requests for tamper protection."""
    
    def __init__(self, secret_key: str = None):
        import os
        self.secret_key = secret_key or os.getenv("VALORA_SECRET_KEY", "valora-default-secret-change-in-production")
        if self.secret_key == "valora-default-secret-change-in-production":
            logger.warning("Using default secret key! Set VALORA_SECRET_KEY environment variable.")
    
    def sign_request(self, method: str, path: str, body: str = "", timestamp: float = None) -> str:
        """Generate a request signature."""
        if timestamp is None:
            timestamp = time.time()
        
        message = f"{method}:{path}:{body}:{timestamp}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{signature}:{timestamp}"
    
    def verify_signature(self, method: str, path: str, body: str, provided_signature: str, 
                         max_age: float = 300) -> bool:
        """Verify a request signature."""
        try:
            parts = provided_signature.split(":")
            if len(parts) != 2:
                return False
            
            provided_sig, timestamp_str = parts
            timestamp = float(timestamp_str)
            
            # Check age
            if time.time() - timestamp > max_age:
                logger.warning(f"Expired signature: {time.time() - timestamp}s old")
                return False
            
            # Compute expected signature
            expected = self.sign_request(method, path, body, timestamp)
            expected_sig = expected.split(":")[0]
            
            # Constant-time comparison
            return hmac.compare_digest(provided_sig, expected_sig)
            
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False


# =============================================================================
# CREDIT PROTECTION
# =============================================================================

class CreditProtector:
    """Protects against credit manipulation and abuse."""
    
    def __init__(self):
        self.credit_operations: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = threading.Lock()
        
        # Thresholds
        self.max_credit_operations_per_hour = 50
        self.max_single_credit_change = 1000
        self.suspicious_credit_patterns = [
            r"negative.*credit",
            r"free.*credit",
            r"unlimited",
            r"bypass",
        ]
    
    def check_credit_operation(self, user_id: str, amount: int, operation: str) -> ThreatScore:
        """Check if a credit operation is suspicious."""
        threat = ThreatScore(score=0)
        now = time.time()
        
        with self._lock:
            # Check operation frequency
            recent_ops = [
                op for op in self.credit_operations[user_id]
                if now - op['timestamp'] < 3600
            ]
            
            if len(recent_ops) > self.max_credit_operations_per_hour:
                threat.add_reason(f"Too many credit operations: {len(recent_ops)}/hour", 40)
            
            # Check for large changes
            if abs(amount) > self.max_single_credit_change:
                threat.add_reason(f"Large credit change: {amount}", 30)
            
            # Check for suspicious patterns in operation name
            for pattern in self.suspicious_credit_patterns:
                if re.search(pattern, operation, re.IGNORECASE):
                    threat.add_reason(f"Suspicious operation pattern: {pattern}", 50)
                    break
            
            # Record operation
            self.credit_operations[user_id].append({
                'timestamp': now,
                'amount': amount,
                'operation': operation,
            })
            
            # Cleanup old entries
            self.credit_operations[user_id] = [
                op for op in self.credit_operations[user_id]
                if now - op['timestamp'] < 86400
            ]
        
        return threat
    
    def detect_credit_anomaly(self, user_id: str, current_balance: int, 
                               previous_balance: int) -> Optional[str]:
        """Detect anomalies in credit balance changes."""
        change = current_balance - previous_balance
        
        # Check for impossible changes
        if current_balance < 0:
            return "Negative balance detected"
        
        if change > self.max_single_credit_change:
            return f"Unusually large credit increase: +{change}"
        
        # Check for rapid changes
        with self._lock:
            recent_ops = [
                op for op in self.credit_operations[user_id]
                if time.time() - op['timestamp'] < 300
            ]
            total_change = sum(op['amount'] for op in recent_ops)
            
            if abs(total_change) > 500:
                return f"Rapid credit changes: {total_change} in 5 minutes"
        
        return None


# =============================================================================
# SECURITY MIDDLEWARE
# =============================================================================

class EnhancedSecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware.
    
    Features:
    - Input validation
    - Abuse detection
    - Request signing verification
    - Credit protection
    - Audit logging
    """
    
    def __init__(self, app, enable_signing: bool = False):
        super().__init__(app)
        self.validator = InputValidator()
        self.abuse_detector = AbuseDetector()
        self.request_signer = RequestSigner()
        self.credit_protector = CreditProtector()
        self.enable_signing = enable_signing
        
        self.audit_log: List[SecurityEvent] = []
        self._audit_lock = threading.Lock()
        
        # Exempt paths from security checks
        self.exempt_paths = {"/health", "/", "/api/debug", "/docs", "/openapi.json"}
        
        # Sensitive endpoints requiring extra protection
        self.sensitive_endpoints = {
            "/api/auth/login",
            "/api/auth/register",
            "/api/credits",
            "/api/payment",
            "/api/admin",
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security checks."""
        
        # Skip exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Get client info
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)
        
        # Check if IP is blocked
        if self.abuse_detector.is_blocked(client_ip):
            self._log_event(
                "blocked_ip", "HIGH", client_ip, user_id, 
                request.url.path, {"reason": "IP blocked"}
            )
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check for suspicious user agent
        user_agent = request.headers.get("user-agent", "")
        if self._is_suspicious_user_agent(user_agent):
            self._log_event(
                "suspicious_ua", "MEDIUM", client_ip, user_id,
                request.url.path, {"user_agent": user_agent}
            )
            self.abuse_detector.record_failure(client_ip, "suspicious_ua")
        
        # Check request rate
        rate_threat = self.abuse_detector.check_request(client_ip, user_id, request.url.path)
        if rate_threat.blocked:
            self._log_event(
                "rate_limit", "HIGH", client_ip, user_id,
                request.url.path, {"threat_score": rate_threat.score}
            )
            raise HTTPException(status_code=429, detail="Too many requests")
        
        # Validate request body for POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                input_threat = self.validator.validate_dict(body)
                
                if input_threat.blocked:
                    self._log_event(
                        "input_attack", "CRITICAL", client_ip, user_id,
                        request.url.path, {
                            "threat_score": input_threat.score,
                            "reasons": input_threat.reasons
                        }
                    )
                    self.abuse_detector.record_failure(client_ip, "input_attack")
                    raise HTTPException(status_code=400, detail="Invalid input")
                
                if input_threat.score > 30:
                    self._log_event(
                        "suspicious_input", "MEDIUM", client_ip, user_id,
                        request.url.path, {"threat_score": input_threat.score}
                    )
            except json.JSONDecodeError:
                pass  # Not JSON body
        
        # Verify request signature for sensitive endpoints
        if self.enable_signing and request.url.path in self.sensitive_endpoints:
            signature = request.headers.get("X-Request-Signature")
            if signature:
                # Re-read body for verification
                body_bytes = await request.body()
                if not self.request_signer.verify_signature(
                    request.method, 
                    request.url.path,
                    body_bytes.decode(),
                    signature
                ):
                    self._log_event(
                        "invalid_signature", "HIGH", client_ip, user_id,
                        request.url.path, {}
                    )
                    raise HTTPException(status_code=401, detail="Invalid request signature")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Record success
            self.abuse_detector.record_success(client_ip)
            
            # Add security headers
            response.headers["X-Security-Version"] = "2.0"
            response.headers["X-Request-ID"] = hashlib.md5(
                f"{client_ip}:{time.time()}".encode()
            ).hexdigest()[:16]
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            self.abuse_detector.record_failure(client_ip, str(e))
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _get_user_id(self, request: Request) -> str:
        """Extract user ID from request."""
        # Try Authorization header
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            # In production, decode JWT and get user ID
            return "authenticated"
        return "anonymous"
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious."""
        ua_lower = user_agent.lower()
        for pattern in SUSPICIOUS_USER_AGENTS:
            if re.search(pattern, ua_lower, re.IGNORECASE):
                return True
        return False
    
    def _log_event(self, event_type: str, severity: str, ip: str, user_id: str,
                   endpoint: str, details: Dict):
        """Log a security event."""
        event = SecurityEvent(
            timestamp=time.time(),
            event_type=event_type,
            severity=severity,
            ip_address=ip,
            user_id=user_id,
            endpoint=endpoint,
            details=details,
            blocked=severity in ["HIGH", "CRITICAL"]
        )
        
        with self._audit_lock:
            self.audit_log.append(event)
            # Keep last 10000 events
            if len(self.audit_log) > 10000:
                self.audit_log = self.audit_log[-10000:]
        
        # Log to system
        log_msg = f"Security Event: {event_type} [{severity}] IP={ip} User={user_id} Endpoint={endpoint}"
        if severity == "CRITICAL":
            logger.critical(log_msg)
        elif severity == "HIGH":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
    
    def get_security_stats(self) -> Dict:
        """Get security statistics."""
        with self._audit_lock:
            events = self.audit_log[-1000:]
            
            return {
                "total_events": len(self.audit_log),
                "recent_events": len(events),
                "blocked_ips": len(self.abuse_detector.blocked_ips),
                "suspicious_ips": len(self.abuse_detector.suspicious_ips),
                "events_by_type": self._count_by_attr(events, "event_type"),
                "events_by_severity": self._count_by_attr(events, "severity"),
            }
    
    def _count_by_attr(self, events: List[SecurityEvent], attr: str) -> Dict[str, int]:
        """Count events by attribute."""
        counts = defaultdict(int)
        for event in events:
            counts[getattr(event, attr)] += 1
        return dict(counts)


# =============================================================================
# SINGLETON INSTANCES
# =============================================================================

_input_validator = None
_abuse_detector = None
_request_signer = None
_credit_protector = None


def get_input_validator() -> InputValidator:
    """Get singleton InputValidator."""
    global _input_validator
    if _input_validator is None:
        _input_validator = InputValidator()
    return _input_validator


def get_abuse_detector() -> AbuseDetector:
    """Get singleton AbuseDetector."""
    global _abuse_detector
    if _abuse_detector is None:
        _abuse_detector = AbuseDetector()
    return _abuse_detector


def get_request_signer() -> RequestSigner:
    """Get singleton RequestSigner."""
    global _request_signer
    if _request_signer is None:
        _request_signer = RequestSigner()
    return _request_signer


def get_credit_protector() -> CreditProtector:
    """Get singleton CreditProtector."""
    global _credit_protector
    if _credit_protector is None:
        _credit_protector = CreditProtector()
    return _credit_protector


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'EnhancedSecurityMiddleware',
    'InputValidator',
    'AbuseDetector',
    'RequestSigner',
    'CreditProtector',
    'SecurityEvent',
    'ThreatScore',
    'get_input_validator',
    'get_abuse_detector',
    'get_request_signer',
    'get_credit_protector',
]
