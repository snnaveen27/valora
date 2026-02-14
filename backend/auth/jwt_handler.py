"""
JWT Authentication System for Valora
Handles user tokens, tier verification, and session management
"""
import jwt
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7

security = HTTPBearer()

class JWTHandler:
    """Handle JWT token creation and verification"""
    
    @staticmethod
    def create_access_token(user_id: str, tier: str = "free", additional_claims: Dict = None) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            "sub": user_id,  # Subject (user ID)
            "tier": tier,    # User tier (free/pro)
            "type": "access",
            "iat": datetime.utcnow(),  # Issued at
            "exp": expire,  # Expiration
            "jti": f"{user_id}_{int(time.time())}"  # Unique token ID
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": datetime.utcnow(),
            "exp": expire,
            "jti": f"refresh_{user_id}_{int(time.time())}"
        }
        
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check token type
            if payload.get("type") != token_type:
                raise HTTPException(status_code=401, detail=f"Invalid token type. Expected {token_type}")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    @staticmethod
    def get_current_user(request: Request) -> Dict[str, Any]:
        """Extract and verify user from request headers"""
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            # Return anonymous user if no token
            return {
                "user_id": "anonymous",
                "tier": "free",
                "authenticated": False
            }
        
        token = auth_header.split(" ")[1]
        payload = JWTHandler.verify_token(token)
        
        return {
            "user_id": payload.get("sub", "anonymous"),
            "tier": payload.get("tier", "free"),
            "authenticated": True,
            "token_exp": payload.get("exp")
        }
    
    @staticmethod
    def require_auth(request: Request) -> Dict[str, Any]:
        """Require authentication - raise error if not authenticated"""
        user = JWTHandler.get_current_user(request)
        
        if not user["authenticated"]:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user
    
    @staticmethod
    def require_pro(request: Request) -> Dict[str, Any]:
        """Require Pro tier - raise error if not Pro"""
        user = JWTHandler.require_auth(request)
        
        if user["tier"] != "pro":
            raise HTTPException(
                status_code=403,
                detail="Pro subscription required for this feature"
            )
        
        return user


# FastAPI dependencies
def get_current_user_dependency(request: Request) -> Dict[str, Any]:
    """FastAPI dependency to get current user"""
    return JWTHandler.get_current_user(request)

def require_auth_dependency(request: Request) -> Dict[str, Any]:
    """FastAPI dependency to require authentication"""
    return JWTHandler.require_auth(request)

def require_pro_dependency(request: Request) -> Dict[str, Any]:
    """FastAPI dependency to require Pro tier"""
    return JWTHandler.require_pro(request)


# Token blacklist for logout (store in Redis in production)
token_blacklist = set()

class TokenBlacklist:
    """Manage blacklisted tokens (logout/revoke)"""
    
    @staticmethod
    def blacklist_token(token: str):
        """Add token to blacklist"""
        try:
            payload = JWTHandler.verify_token(token)
            jti = payload.get("jti")
            if jti:
                token_blacklist.add(jti)
        except:
            pass
    
    @staticmethod
    def is_blacklisted(token: str) -> bool:
        """Check if token is blacklisted"""
        try:
            payload = JWTHandler.verify_token(token)
            jti = payload.get("jti")
            return jti in token_blacklist
        except:
            return True


# Rate limiting by user tier
class TierRateLimit:
    """Rate limiting configuration per tier"""
    
    LIMITS = {
        "free": {
            "requests_per_hour": 100,
            "queries_per_session": 5,
            "max_message_length": 1000,
            "max_history": 10
        },
        "pro": {
            "requests_per_hour": 1000,
            "queries_per_session": -1,  # Unlimited
            "max_message_length": 5000,
            "max_history": 50
        }
    }
    
    @staticmethod
    def get_limits(tier: str) -> Dict[str, int]:
        return TierRateLimit.LIMITS.get(tier, TierRateLimit.LIMITS["free"])
    
    @staticmethod
    def check_limit(tier: str, limit_type: str, current_value: int) -> bool:
        limits = TierRateLimit.get_limits(tier)
        limit = limits.get(limit_type, 0)
        
        if limit == -1:  # Unlimited
            return True
        
        return current_value < limit
