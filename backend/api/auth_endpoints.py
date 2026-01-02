"""
Authentication API Endpoints
Handles user registration, login, Google OAuth, and JWT tokens
"""

import os
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
import logging
import json
from pathlib import Path

from backend.database.connection import get_db, db_manager
from backend.database.models.user import User
from backend.database.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "valora-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security
security = HTTPBearer(auto_error=False)

# Flag to track if we should use database or fallback to JSON
USE_DATABASE = True

# Fallback: User storage file (used if database is unavailable)
USERS_FILE = Path(__file__).parent.parent.parent / "data" / "shared" / "users.json"

# Default admin user (for fallback)
DEFAULT_ADMIN = {
    "email": "naveen.sandcube@gmail.com",
    "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
    "role": "admin",
    "name": "Admin",
    "created_at": datetime.now().isoformat(),
    "is_active": True,
    "auth_provider": "local"
}

# Default demo user (for fallback)
DEFAULT_DEMO_USER = {
    "email": "demo@valora.ai",
    "password_hash": hashlib.sha256("demo123".encode()).hexdigest(),
    "role": "user",
    "name": "Demo User",
    "created_at": datetime.now().isoformat(),
    "is_active": True,
    "auth_provider": "local"
}


def check_database_available() -> bool:
    """Check if database is available"""
    try:
        return db_manager.test_connection()
    except Exception:
        return False


# Supported languages for text and voice
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "ml": "Malayalam",
    "pa": "Punjabi"
}

# Pydantic Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=2)
    text_language: str = Field(default="en", description="Preferred language for text")
    voice_language: str = Field(default="en", description="Preferred language for voice")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str  # Google ID token
    

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    auth_provider: str
    text_language: str = "en"
    voice_language: str = "en"


# Helper Functions
def load_users() -> Dict[str, Dict]:
    """Load users from JSON file"""
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    if not USERS_FILE.exists():
        # Initialize with default admin and demo user
        users = {
            DEFAULT_ADMIN["email"]: DEFAULT_ADMIN,
            DEFAULT_DEMO_USER["email"]: DEFAULT_DEMO_USER
        }
        save_users(users)
        return users
    
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
            # Ensure admin exists
            if DEFAULT_ADMIN["email"] not in users:
                users[DEFAULT_ADMIN["email"]] = DEFAULT_ADMIN
            # Ensure demo user exists
            if DEFAULT_DEMO_USER["email"] not in users:
                users[DEFAULT_DEMO_USER["email"]] = DEFAULT_DEMO_USER
            save_users(users)
            return users
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        return {
            DEFAULT_ADMIN["email"]: DEFAULT_ADMIN,
            DEFAULT_DEMO_USER["email"]: DEFAULT_DEMO_USER
        }


def save_users(users: Dict[str, Dict]):
    """Save users to JSON file"""
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2, default=str)


def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == password_hash


def create_token(user_data: Dict) -> str:
    """Create JWT token"""
    payload = {
        "sub": user_data["email"],
        "name": user_data["name"],
        "role": user_data["role"],
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict]:
    """Get current user from JWT token"""
    if not credentials:
        return None
    
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    
    users = load_users()
    user = users.get(payload.get("sub"))
    if not user or not user.get("is_active", True):
        return None
    
    return user


async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Require authentication"""
    user = await get_current_user(credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Require admin role"""
    user = await require_auth(credentials)
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


# API Endpoints
@router.post("/register", response_model=TokenResponse)
async def register(request: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    if USE_DATABASE and check_database_available():
        # Use PostgreSQL database
        repo = UserRepository(db)
        
        # Check if email already exists
        existing_user = repo.get_by_email(request.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate language preferences
        text_lang = request.text_language if request.text_language in SUPPORTED_LANGUAGES else "en"
        voice_lang = request.voice_language if request.voice_language in SUPPORTED_LANGUAGES else "en"
        
        # Create new user
        user = repo.create(
            email=request.email,
            password=request.password,
            name=request.name,
            role="user",
            auth_provider="local",
            text_language=text_lang,
            voice_language=voice_lang
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        # Create token
        token = create_token(user.to_public_dict())
        
        logger.info(f"New user registered (DB): {request.email}")
        
        return TokenResponse(
            access_token=token,
            expires_in=JWT_EXPIRATION_HOURS * 3600,
            user=user.to_public_dict()
        )
    else:
        # Fallback to JSON file
        users = load_users()
        
        if request.email in users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate language preferences
        text_lang = request.text_language if request.text_language in SUPPORTED_LANGUAGES else "en"
        voice_lang = request.voice_language if request.voice_language in SUPPORTED_LANGUAGES else "en"
        
        user_id = secrets.token_hex(16)
        new_user = {
            "id": user_id,
            "email": request.email,
            "password_hash": hash_password(request.password),
            "name": request.name,
            "role": "user",
            "created_at": datetime.now().isoformat(),
            "is_active": True,
            "auth_provider": "local",
            "text_language": text_lang,
            "voice_language": voice_lang
        }
        
        users[request.email] = new_user
        save_users(users)
        
        token = create_token(new_user)
        
        logger.info(f"New user registered (JSON): {request.email}")
        
        return TokenResponse(
            access_token=token,
            expires_in=JWT_EXPIRATION_HOURS * 3600,
            user={
                "id": user_id,
                "email": request.email,
                "name": request.name,
                "role": "user",
                "is_active": True,
                "auth_provider": "local",
                "text_language": text_lang,
                "voice_language": voice_lang
            }
        )


# Endpoint to get supported languages
@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages for text and voice"""
    return {
        "languages": SUPPORTED_LANGUAGES,
        "default": "en"
    }


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password"""
    if USE_DATABASE and check_database_available():
        # Use PostgreSQL database
        repo = UserRepository(db)
        
        user = repo.get_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not repo.verify_password(user, request.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )
        
        # Update last login
        repo.update_last_login(user)
        
        # Create token
        token = create_token(user.to_public_dict())
        
        logger.info(f"User logged in (DB): {request.email}")
        
        return TokenResponse(
            access_token=token,
            expires_in=JWT_EXPIRATION_HOURS * 3600,
            user=user.to_public_dict()
        )
    else:
        # Fallback to JSON file
        users = load_users()
        
        user = users.get(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not verify_password(request.password, user.get("password_hash", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )
        
        token = create_token(user)
        
        logger.info(f"User logged in (JSON): {request.email}")
        
        return TokenResponse(
            access_token=token,
            expires_in=JWT_EXPIRATION_HOURS * 3600,
            user={
                "id": user.get("id", ""),
                "email": user["email"],
                "name": user.get("name", ""),
                "role": user.get("role", "user"),
                "is_active": user.get("is_active", True),
                "auth_provider": user.get("auth_provider", "local")
            }
        )


@router.post("/google", response_model=TokenResponse)
async def google_auth(request: GoogleAuthRequest):
    """Authenticate with Google"""
    try:
        # Decode Google ID token (in production, verify with Google's public keys)
        # For now, we'll decode without verification for development
        # In production, use google-auth library to verify
        
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        
        GOOGLE_CLIENT_ID = os.getenv("VITE_GOOGLE_CLIENT_ID", "")
        
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured"
            )
        
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            request.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        email = idinfo.get("email")
        name = idinfo.get("name", email.split("@")[0])
        
        users = load_users()
        
        if email in users:
            # Existing user - update and login
            user = users[email]
            user["last_login"] = datetime.now().isoformat()
            if user.get("auth_provider") != "google":
                user["auth_provider"] = "google"  # Link account
            save_users(users)
        else:
            # New user - register
            user_id = secrets.token_hex(16)
            user = {
                "id": user_id,
                "email": email,
                "password_hash": "",  # No password for Google auth
                "name": name,
                "role": "user",
                "created_at": datetime.now().isoformat(),
                "is_active": True,
                "auth_provider": "google",
                "google_id": idinfo.get("sub")
            }
            users[email] = user
            save_users(users)
            logger.info(f"New Google user registered: {email}")
        
        # Create token
        token = create_token(user)
        
        return TokenResponse(
            access_token=token,
            expires_in=JWT_EXPIRATION_HOURS * 3600,
            user={
                "id": user.get("id", ""),
                "email": user["email"],
                "name": user.get("name", ""),
                "role": user.get("role", "user"),
                "is_active": user.get("is_active", True),
                "auth_provider": "google"
            }
        )
        
    except ImportError:
        # Google auth library not installed - use simple decode
        logger.warning("google-auth library not installed, using fallback")
        
        # Decode JWT without verification (development only!)
        try:
            parts = request.credential.split(".")
            if len(parts) != 3:
                raise HTTPException(status_code=400, detail="Invalid token format")
            
            import base64
            payload = parts[1]
            # Add padding if needed
            payload += "=" * (4 - len(payload) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            
            email = decoded.get("email")
            name = decoded.get("name", email.split("@")[0] if email else "User")
            
            if not email:
                raise HTTPException(status_code=400, detail="No email in token")
            
            users = load_users()
            
            if email in users:
                user = users[email]
            else:
                user_id = secrets.token_hex(16)
                user = {
                    "id": user_id,
                    "email": email,
                    "password_hash": "",
                    "name": name,
                    "role": "user",
                    "created_at": datetime.now().isoformat(),
                    "is_active": True,
                    "auth_provider": "google"
                }
                users[email] = user
                save_users(users)
            
            token = create_token(user)
            
            return TokenResponse(
                access_token=token,
                expires_in=JWT_EXPIRATION_HOURS * 3600,
                user={
                    "id": user.get("id", ""),
                    "email": user["email"],
                    "name": user.get("name", ""),
                    "role": user.get("role", "user"),
                    "is_active": True,
                    "auth_provider": "google"
                }
            )
        except Exception as e:
            logger.error(f"Google auth error: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")
    
    except Exception as e:
        logger.error(f"Google auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_me(user: Dict = Depends(require_auth)):
    """Get current user info"""
    return UserResponse(
        id=user.get("id", ""),
        email=user["email"],
        name=user.get("name", ""),
        role=user.get("role", "user"),
        is_active=user.get("is_active", True),
        auth_provider=user.get("auth_provider", "local")
    )


@router.post("/logout")
async def logout():
    """Logout - client should clear token"""
    return {"message": "Logged out successfully"}


# Admin endpoints
@router.get("/admin/users")
async def list_users(admin: Dict = Depends(require_admin), db: Session = Depends(get_db)):
    """List all users (admin only)"""
    if USE_DATABASE and check_database_available():
        repo = UserRepository(db)
        users = repo.get_all_users()
        return [u.to_dict() for u in users]
    else:
        users = load_users()
        return [
            {
                "id": u.get("id", ""),
                "email": u["email"],
                "name": u.get("name", ""),
                "role": u.get("role", "user"),
                "is_active": u.get("is_active", True),
                "auth_provider": u.get("auth_provider", "local"),
                "created_at": u.get("created_at", "")
            }
            for u in users.values()
        ]


@router.put("/admin/users/{email}/role")
async def update_user_role(email: str, role: str, admin: Dict = Depends(require_admin), db: Session = Depends(get_db)):
    """Update user role (admin only)"""
    if role not in ["user", "admin", "analyst"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    if USE_DATABASE and check_database_available():
        repo = UserRepository(db)
        user = repo.get_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not repo.update_role(user, role):
            raise HTTPException(status_code=500, detail="Failed to update role")
    else:
        users = load_users()
        if email not in users:
            raise HTTPException(status_code=404, detail="User not found")
        
        users[email]["role"] = role
        save_users(users)
    
    return {"message": f"User {email} role updated to {role}"}


@router.put("/admin/users/{email}/status")
async def toggle_user_status(email: str, admin: Dict = Depends(require_admin), db: Session = Depends(get_db)):
    """Toggle user active status (admin only)"""
    # Prevent disabling self
    if email == admin["email"]:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")
    
    if USE_DATABASE and check_database_available():
        repo = UserRepository(db)
        user = repo.get_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not repo.toggle_active(user):
            raise HTTPException(status_code=500, detail="Failed to toggle status")
        
        user_status = "enabled" if user.is_active else "disabled"
    else:
        users = load_users()
        if email not in users:
            raise HTTPException(status_code=404, detail="User not found")
        
        users[email]["is_active"] = not users[email].get("is_active", True)
        save_users(users)
        
        user_status = "enabled" if users[email]["is_active"] else "disabled"
    
    return {"message": f"User {email} {user_status}"}
