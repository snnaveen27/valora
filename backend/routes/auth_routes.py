"""
Valora AI - Authentication API Routes
Login, signup, and user management endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime

from auth.user_auth import (
    get_user_database, 
    create_token, 
    decode_token,
    SubscriptionTier,
    UserRole,
    TIER_LIMITS,
    User
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# Request/Response Models
class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    company: Optional[str] = None
    phone: Optional[str] = None
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v
    
    @validator('email')
    def email_format(cls, v):
        if '@' not in v or '.' not in v:
            raise ValueError('Invalid email format')
        return v.lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    tier: str
    role: str
    company: Optional[str]
    phone: Optional[str]
    queries_today: int
    reports_this_month: int
    created_at: str
    last_login: Optional[str]
    tier_limits: dict


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


class AdminUpdateUserRequest(BaseModel):
    name: Optional[str] = None
    tier: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


# Helper to get current user from token
import logging
_auth_logger = logging.getLogger(__name__)

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """Extract and verify user from Authorization header."""
    _auth_logger.info(f"[AUTH] get_current_user called, authorization header present: {authorization is not None}")
    
    if not authorization:
        _auth_logger.warning("[AUTH] No authorization header provided")
        return None
    
    if not authorization.startswith("Bearer "):
        _auth_logger.warning(f"[AUTH] Invalid authorization format: {authorization[:20]}...")
        return None
    
    token = authorization[7:]  # Remove "Bearer " prefix
    _auth_logger.info(f"[AUTH] Token received, length: {len(token)}")
    
    payload = decode_token(token)
    
    if not payload:
        _auth_logger.warning("[AUTH] Token decode failed - token may be expired or invalid")
        return None
    
    _auth_logger.info(f"[AUTH] Token decoded successfully, user_id: {payload.get('user_id')}, role: {payload.get('role')}")
    
    db = get_user_database()
    user = db.get_user_by_id(payload.get("user_id"))
    
    if not user:
        _auth_logger.warning(f"[AUTH] User not found in database for user_id: {payload.get('user_id')}")
    else:
        _auth_logger.info(f"[AUTH] User found: {user.email}, role: {user.role}")
    
    return user


async def require_auth(
    authorization: Optional[str] = Header(None)
) -> User:
    """Require authentication - raises 401 if not authenticated."""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_admin(
    authorization: Optional[str] = Header(None)
) -> User:
    """Require admin role."""
    user = await require_auth(authorization)
    if user.role != UserRole.ADMIN:
        _auth_logger.warning(f"[AUTH] User {user.email} is not admin, role: {user.role}")
        raise HTTPException(status_code=403, detail="Admin access required")
    _auth_logger.info(f"[AUTH] Admin access granted for {user.email}")
    return user


# Routes
@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login with email and password."""
    db = get_user_database()
    user, error = db.authenticate(request.email, request.password)
    
    if not user:
        if error == "account_locked":
            raise HTTPException(status_code=423, detail="Account locked. Too many failed attempts. Try again in 24 hours.")
        elif error == "too_many_attempts":
            raise HTTPException(status_code=429, detail="Too many login attempts today. Try again tomorrow.")
        elif error.startswith("invalid_credentials:"):
            retries_left = error.split(":")[1]
            raise HTTPException(status_code=401, detail=f"Invalid email or password. {retries_left} attempts remaining today.")
        else:
            raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_token(user.id, user.email, user.tier.value, user.role.value)
    
    return TokenResponse(
        access_token=token,
        user=user.to_dict()
    )


@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest):
    """Create new user account."""
    db = get_user_database()
    
    # Check if email already exists
    existing = db.get_user_by_email(request.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user with free tier
    user = db.create_user(
        email=request.email,
        name=request.name,
        password=request.password,
        tier=SubscriptionTier.FREE,
        role=UserRole.USER,
        company=request.company,
        phone=request.phone
    )
    
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    token = create_token(user.id, user.email, user.tier.value, user.role.value)
    
    # Log signup
    db.log_usage(user.id, "signup", f"New user registered: {user.email}")
    
    return TokenResponse(
        access_token=token,
        user=user.to_dict()
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(require_auth)):
    """Get current user profile."""
    return user.to_dict()


@router.put("/me", response_model=UserResponse)
async def update_me(
    request: UpdateUserRequest,
    user: User = Depends(require_auth)
):
    """Update current user profile."""
    db = get_user_database()
    
    updates = {}
    if request.name:
        updates["name"] = request.name
    if request.company is not None:
        updates["company"] = request.company
    if request.phone is not None:
        updates["phone"] = request.phone
    
    if updates:
        db.update_user(user.id, **updates)
    
    updated_user = db.get_user_by_id(user.id)
    return updated_user.to_dict()


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(require_auth)
):
    """Change password."""
    db = get_user_database()
    
    # Verify current password
    verified_user, error = db.authenticate(user.email, request.current_password)
    if not verified_user:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Change password
    success = db.change_password(user.id, request.new_password)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to change password")
    
    db.log_usage(user.id, "password_change", "Password changed")
    
    return {"success": True, "message": "Password changed successfully"}


@router.post("/verify")
async def verify_token(user: User = Depends(require_auth)):
    """Verify token is valid."""
    return {
        "valid": True,
        "user": user.to_dict()
    }


@router.get("/usage")
async def get_usage(user: User = Depends(require_auth)):
    """Get current usage statistics."""
    db = get_user_database()
    allowed, used, limit = db.check_query_limit(user.id)
    
    return {
        "queries": {
            "used": used,
            "limit": limit,
            "remaining": limit - used if limit > 0 else -1,
            "allowed": allowed
        },
        "tier": user.tier.value,
        "tier_limits": TIER_LIMITS[user.tier]
    }


@router.get("/tiers")
async def get_tiers():
    """Get available subscription tiers."""
    return {
        tier.value: {
            **limits,
            "name": tier.value.title(),
        }
        for tier, limits in TIER_LIMITS.items()
        if tier != SubscriptionTier.ADMIN
    }


# Admin routes
@router.get("/admin/users", response_model=List[dict])
async def admin_get_users(
    include_inactive: bool = False,
    admin: User = Depends(require_admin)
):
    """Get all users (admin only)."""
    db = get_user_database()
    users = db.get_all_users(include_inactive=include_inactive)
    return [u.to_dict() for u in users]


@router.get("/admin/stats")
async def admin_get_stats(admin: User = Depends(require_admin)):
    """Get user statistics (admin only)."""
    db = get_user_database()
    return db.get_user_stats()


@router.get("/admin/users/{user_id}", response_model=dict)
async def admin_get_user(
    user_id: int,
    admin: User = Depends(require_admin)
):
    """Get specific user (admin only)."""
    db = get_user_database()
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


@router.put("/admin/users/{user_id}", response_model=dict)
async def admin_update_user(
    user_id: int,
    request: AdminUpdateUserRequest,
    admin: User = Depends(require_admin)
):
    """Update user (admin only)."""
    db = get_user_database()
    
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updates = {}
    if request.name:
        updates["name"] = request.name
    if request.tier:
        updates["tier"] = request.tier
    if request.role:
        updates["role"] = request.role
    if request.company is not None:
        updates["company"] = request.company
    if request.phone is not None:
        updates["phone"] = request.phone
    if request.is_active is not None:
        updates["is_active"] = 1 if request.is_active else 0
    
    if updates:
        db.update_user(user_id, **updates)
        db.log_usage(admin.id, "admin_update_user", f"Updated user {user_id}: {updates}")
    
    updated_user = db.get_user_by_id(user_id)
    return updated_user.to_dict()


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    admin: User = Depends(require_admin)
):
    """Delete user (soft delete, admin only)."""
    db = get_user_database()
    
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting own account
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    success = db.delete_user(user_id)
    if success:
        db.log_usage(admin.id, "admin_delete_user", f"Deleted user {user_id}")
    
    return {"success": success, "message": "User deleted" if success else "Failed to delete"}


@router.post("/admin/users", response_model=dict)
async def admin_create_user(
    request: SignupRequest,
    tier: str = "free",
    role: str = "user",
    admin: User = Depends(require_admin)
):
    """Create user (admin only)."""
    db = get_user_database()
    
    # Validate tier and role
    try:
        user_tier = SubscriptionTier(tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")
    
    try:
        user_role = UserRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
    
    user = db.create_user(
        email=request.email,
        name=request.name,
        password=request.password,
        tier=user_tier,
        role=user_role,
        company=request.company,
        phone=request.phone
    )
    
    if not user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db.log_usage(admin.id, "admin_create_user", f"Created user {user.email}")
    
    return user.to_dict()
