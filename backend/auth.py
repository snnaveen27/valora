"""
Valora AI - Authentication & Authorization
Minimal RBAC (Role-Based Access Control) for API security.

Roles:
- superadmin: Full access to all endpoints
- analyst: Read/write access to analysis, limited admin
- viewer: Read-only access
- external_api: Limited API access with rate limits

This is a minimal implementation for development/internal use.
For production, integrate with OAuth2/OIDC provider (Keycloak, Auth0, Cognito).
"""

import os
import time
import hashlib
import secrets
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum

from fastapi import HTTPException, Depends, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class Role(Enum):
    """User roles with hierarchical permissions."""
    SUPERADMIN = "superadmin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    EXTERNAL_API = "external_api"
    ANONYMOUS = "anonymous"


class Permission(Enum):
    """Granular permissions."""
    # Read permissions
    READ_PROPERTIES = "read:properties"
    READ_ANALYSIS = "read:analysis"
    READ_ADMIN = "read:admin"
    READ_EXPORTS = "read:exports"
    
    # Write permissions
    WRITE_PROPERTIES = "write:properties"
    WRITE_ANALYSIS = "write:analysis"
    WRITE_ADMIN = "write:admin"
    
    # Execute permissions
    EXEC_SIMULATION = "exec:simulation"
    EXEC_SCRAPE = "exec:scrape"
    EXEC_EXPORT = "exec:export"
    EXEC_CHAT = "exec:chat"
    
    # Admin permissions
    ADMIN_DATABASE = "admin:database"
    ADMIN_CONFIG = "admin:config"
    ADMIN_USERS = "admin:users"


# Role to permissions mapping
ROLE_PERMISSIONS = {
    Role.SUPERADMIN: [p for p in Permission],  # All permissions
    Role.ANALYST: [
        Permission.READ_PROPERTIES,
        Permission.READ_ANALYSIS,
        Permission.READ_EXPORTS,
        Permission.WRITE_PROPERTIES,
        Permission.WRITE_ANALYSIS,
        Permission.EXEC_SIMULATION,
        Permission.EXEC_EXPORT,
        Permission.EXEC_CHAT,
    ],
    Role.VIEWER: [
        Permission.READ_PROPERTIES,
        Permission.READ_ANALYSIS,
        Permission.EXEC_CHAT,
    ],
    Role.EXTERNAL_API: [
        Permission.READ_PROPERTIES,
        Permission.READ_ANALYSIS,
        Permission.EXEC_CHAT,
    ],
    Role.ANONYMOUS: [
        Permission.READ_PROPERTIES,
        Permission.READ_ANALYSIS,
    ],
}


@dataclass
class User:
    """User representation."""
    user_id: str
    username: str
    role: Role
    permissions: List[Permission] = field(default_factory=list)
    api_key: Optional[str] = None
    rate_limit: int = 100  # requests per minute
    created_at: str = ""
    
    def __post_init__(self):
        if not self.permissions:
            self.permissions = ROLE_PERMISSIONS.get(self.role, [])
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        return any(p in self.permissions for p in permissions)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        return all(p in self.permissions for p in permissions)


@dataclass
class RateLimitState:
    """Rate limit tracking for a user/IP."""
    requests: List[float] = field(default_factory=list)
    blocked_until: Optional[float] = None


class AuthService:
    """
    Authentication and authorization service.
    
    For development, uses simple API key auth.
    For production, integrate with OAuth2/OIDC.
    """
    
    def __init__(self):
        # In-memory user store (replace with DB in production)
        self._users: Dict[str, User] = {}
        self._api_keys: Dict[str, str] = {}  # api_key -> user_id
        self._rate_limits: Dict[str, RateLimitState] = {}
        
        # Initialize default users for development
        self._init_default_users()
    
    def _init_default_users(self):
        """Initialize default users for development."""
        # Superadmin
        admin_key = os.environ.get("VALORA_ADMIN_KEY", "valora-dev-admin-key")
        self.create_user("admin", "admin", Role.SUPERADMIN, api_key=admin_key, rate_limit=1000)
        
        # Analyst
        analyst_key = os.environ.get("VALORA_ANALYST_KEY", "valora-dev-analyst-key")
        self.create_user("analyst", "analyst", Role.ANALYST, api_key=analyst_key, rate_limit=500)
        
        # Viewer
        viewer_key = os.environ.get("VALORA_VIEWER_KEY", "valora-dev-viewer-key")
        self.create_user("viewer", "viewer", Role.VIEWER, api_key=viewer_key, rate_limit=200)
        
        # External API
        api_key = os.environ.get("VALORA_API_KEY", "valora-dev-api-key")
        self.create_user("api_user", "api_user", Role.EXTERNAL_API, api_key=api_key, rate_limit=100)
    
    def create_user(
        self, 
        user_id: str, 
        username: str, 
        role: Role,
        api_key: str = None,
        rate_limit: int = 100
    ) -> User:
        """Create a new user."""
        if api_key is None:
            api_key = secrets.token_urlsafe(32)
        
        user = User(
            user_id=user_id,
            username=username,
            role=role,
            api_key=api_key,
            rate_limit=rate_limit
        )
        
        self._users[user_id] = user
        self._api_keys[api_key] = user_id
        
        return user
    
    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Get user by API key."""
        user_id = self._api_keys.get(api_key)
        if user_id:
            return self._users.get(user_id)
        return None
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)
    
    def authenticate(self, api_key: str) -> Optional[User]:
        """Authenticate user by API key."""
        return self.get_user_by_api_key(api_key)
    
    def check_rate_limit(self, identifier: str, limit: int = 100, window_seconds: int = 60) -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: User ID or IP address
            limit: Max requests per window
            window_seconds: Time window in seconds
            
        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        
        if identifier not in self._rate_limits:
            self._rate_limits[identifier] = RateLimitState()
        
        state = self._rate_limits[identifier]
        
        # Check if blocked
        if state.blocked_until and now < state.blocked_until:
            return False
        
        # Clean old requests
        window_start = now - window_seconds
        state.requests = [t for t in state.requests if t > window_start]
        
        # Check limit
        if len(state.requests) >= limit:
            # Block for 60 seconds
            state.blocked_until = now + 60
            return False
        
        # Record request
        state.requests.append(now)
        return True
    
    def get_rate_limit_info(self, identifier: str, limit: int = 100, window_seconds: int = 60) -> Dict[str, Any]:
        """Get current rate limit info for identifier."""
        now = time.time()
        
        if identifier not in self._rate_limits:
            return {
                "remaining": limit,
                "limit": limit,
                "reset_in_seconds": window_seconds
            }
        
        state = self._rate_limits[identifier]
        window_start = now - window_seconds
        recent_requests = [t for t in state.requests if t > window_start]
        
        return {
            "remaining": max(0, limit - len(recent_requests)),
            "limit": limit,
            "reset_in_seconds": int(window_seconds - (now - min(recent_requests)) if recent_requests else window_seconds),
            "blocked": state.blocked_until and now < state.blocked_until
        }


# Global auth service instance
_auth_service = None


def get_auth_service() -> AuthService:
    """Get or create auth service singleton."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


# FastAPI security
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> User:
    """
    Get current user from request.
    
    Checks for:
    1. Bearer token in Authorization header
    2. X-API-Key header
    3. api_key query parameter
    
    Returns anonymous user if no auth provided.
    """
    auth_service = get_auth_service()
    
    # Try Bearer token
    if credentials:
        user = auth_service.authenticate(credentials.credentials)
        if user:
            return user
    
    # Try X-API-Key header
    if x_api_key:
        user = auth_service.authenticate(x_api_key)
        if user:
            return user
    
    # Try query parameter
    api_key = request.query_params.get("api_key")
    if api_key:
        user = auth_service.authenticate(api_key)
        if user:
            return user
    
    # Return anonymous user
    return User(
        user_id="anonymous",
        username="anonymous",
        role=Role.ANONYMOUS
    )


def require_permission(permission: Permission):
    """Decorator to require a specific permission."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user from kwargs (injected by Depends)
            user = kwargs.get("current_user")
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            if not user.has_permission(permission):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Permission denied: {permission.value} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: Role):
    """Decorator to require a minimum role."""
    role_hierarchy = [Role.ANONYMOUS, Role.EXTERNAL_API, Role.VIEWER, Role.ANALYST, Role.SUPERADMIN]
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("current_user")
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            user_level = role_hierarchy.index(user.role) if user.role in role_hierarchy else 0
            required_level = role_hierarchy.index(role) if role in role_hierarchy else 0
            
            if user_level < required_level:
                raise HTTPException(
                    status_code=403,
                    detail=f"Role {role.value} or higher required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def check_rate_limit(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> bool:
    """
    FastAPI dependency to check rate limit.
    
    Usage:
        @app.get("/api/endpoint")
        async def endpoint(rate_ok: bool = Depends(check_rate_limit)):
            ...
    """
    auth_service = get_auth_service()
    
    # Use user ID for authenticated users, IP for anonymous
    identifier = current_user.user_id if current_user.role != Role.ANONYMOUS else request.client.host
    limit = current_user.rate_limit
    
    if not auth_service.check_rate_limit(identifier, limit):
        info = auth_service.get_rate_limit_info(identifier, limit)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {info['reset_in_seconds']} seconds.",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(info['remaining']),
                "X-RateLimit-Reset": str(info['reset_in_seconds'])
            }
        )
    
    return True


# Endpoint-specific permission requirements
ENDPOINT_PERMISSIONS = {
    # Admin endpoints
    "/api/admin/": [Permission.READ_ADMIN],
    "/api/admin/config": [Permission.ADMIN_CONFIG],
    "/api/admin/database": [Permission.ADMIN_DATABASE],
    
    # Scraping endpoints
    "/api/scrape/": [Permission.EXEC_SCRAPE],
    
    # Simulation endpoints
    "/api/simulate": [Permission.EXEC_SIMULATION],
    "/api/digital-twin/": [Permission.EXEC_SIMULATION],
    
    # Export endpoints
    "/api/export/": [Permission.EXEC_EXPORT],
    
    # Chat endpoints
    "/api/chat": [Permission.EXEC_CHAT],
}


def get_required_permissions(path: str) -> List[Permission]:
    """Get required permissions for an endpoint path."""
    for pattern, perms in ENDPOINT_PERMISSIONS.items():
        if path.startswith(pattern):
            return perms
    return []  # No specific permissions required


class AuthMiddleware:
    """
    Middleware to check permissions for protected endpoints.
    
    Add to FastAPI app:
        app.add_middleware(AuthMiddleware)
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"]
            required_perms = get_required_permissions(path)
            
            if required_perms:
                # Check permissions (simplified - in production use proper auth)
                # This is handled by dependencies in the actual endpoints
                pass
        
        await self.app(scope, receive, send)
