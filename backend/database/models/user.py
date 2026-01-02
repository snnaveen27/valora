"""
User Model for SQLAlchemy
Handles user authentication and profile data
"""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from backend.database.connection import Base


class AuthProvider(enum.Enum):
    LOCAL = "local"
    GOOGLE = "google"


class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"
    ANALYST = "analyst"


class User(Base):
    """User model for authentication and profile"""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=True)  # Nullable for OAuth users
    name = Column(String(255), nullable=False)
    role = Column(String(50), default="user", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    auth_provider = Column(String(50), default="local", nullable=False)
    google_id = Column(String(255), nullable=True, unique=True)
    
    # Profile fields
    phone = Column(String(20), nullable=True)
    avatar_url = Column(Text, nullable=True)
    
    # Language preferences
    text_language = Column(String(10), default="en", nullable=False)  # en, hi, kn, ta, te, etc.
    voice_language = Column(String(10), default="en", nullable=False)  # en, hi, kn, ta, te, etc.
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Email verification
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token = Column(String(256), nullable=True)
    
    # Password reset
    password_reset_token = Column(String(256), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    def to_dict(self):
        """Convert user to dictionary for API responses"""
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "is_active": self.is_active,
            "auth_provider": self.auth_provider,
            "phone": self.phone,
            "avatar_url": self.avatar_url,
            "text_language": self.text_language,
            "voice_language": self.voice_language,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "email_verified": self.email_verified
        }
    
    def to_public_dict(self):
        """Convert user to public dictionary (no sensitive data)"""
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "is_active": self.is_active,
            "auth_provider": self.auth_provider,
            "text_language": self.text_language,
            "voice_language": self.voice_language
        }
