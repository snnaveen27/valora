"""
User Repository
Handles database operations for users
"""

import hashlib
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging

from backend.database.models.user import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user database operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            return self.session.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            return self.session.query(User).filter(User.email == email.lower()).first()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def get_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID"""
        try:
            return self.session.query(User).filter(User.google_id == google_id).first()
        except Exception as e:
            logger.error(f"Error getting user by Google ID: {e}")
            return None
    
    def create(self, email: str, password: str, name: str, 
               role: str = "user", auth_provider: str = "local",
               google_id: Optional[str] = None,
               text_language: str = "en", voice_language: str = "en") -> Optional[User]:
        """Create a new user"""
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest() if password else None
            
            user = User(
                email=email.lower(),
                password_hash=password_hash,
                name=name,
                role=role,
                auth_provider=auth_provider,
                google_id=google_id,
                is_active=True,
                email_verified=False,
                text_language=text_language,
                voice_language=voice_language
            )
            
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
            
            logger.info(f"Created new user: {email}")
            return user
            
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"User already exists: {email}")
            return None
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating user: {e}")
            return None
    
    def update_last_login(self, user: User) -> bool:
        """Update user's last login timestamp"""
        try:
            user.last_login = datetime.utcnow()
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating last login: {e}")
            return False
    
    def update_role(self, user: User, role: str) -> bool:
        """Update user's role"""
        try:
            user.role = role
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating role: {e}")
            return False
    
    def toggle_active(self, user: User) -> bool:
        """Toggle user's active status"""
        try:
            user.is_active = not user.is_active
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error toggling active status: {e}")
            return False
    
    def update_password(self, user: User, new_password: str) -> bool:
        """Update user's password"""
        try:
            user.password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating password: {e}")
            return False
    
    def verify_password(self, user: User, password: str) -> bool:
        """Verify user's password"""
        if not user.password_hash:
            return False
        return user.password_hash == hashlib.sha256(password.encode()).hexdigest()
    
    def get_all_users(self) -> List[User]:
        """Get all users"""
        try:
            return self.session.query(User).order_by(User.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    def count_users(self) -> int:
        """Count total users"""
        try:
            return self.session.query(User).count()
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0
    
    def link_google_account(self, user: User, google_id: str) -> bool:
        """Link Google account to existing user"""
        try:
            user.google_id = google_id
            user.auth_provider = "google"
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error linking Google account: {e}")
            return False
