"""
Feedback API Routes - Auto-save and credit rewards for user feedback
Uses the unified credits system for credit management.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import sqlite3
import logging

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/feedback", tags=["feedback"])

try:
    from routes.auth_routes import require_admin
    from auth.user_auth import User
except Exception:
    require_admin = None
    User = None

# Database path for feedback storage (feedback records only, not credits)
from config import config
DB_PATH = str(config.DB_PATH.parent / 'valora_memory.db')


def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_credits_manager():
    """Get the unified credits manager."""
    from ai.unified_credits import get_credits_manager
    return get_credits_manager()


def init_feedback_table():
    """Initialize feedback tables if they don't exist.
    Note: Credits are managed centrally via UnifiedCreditsManager, not here.
    """
    conn = get_db_connection()
    try:
        # Main feedback table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS message_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                session_id TEXT,
                message_content TEXT,
                feedback_text TEXT NOT NULL,
                quality_score INTEGER DEFAULT 0,
                credits_earned INTEGER DEFAULT 0,
                status TEXT DEFAULT 'submitted',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, message_id)
            )
        """)
        
        # Auto-save drafts table (temporary storage)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                draft_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, message_id)
            )
        """)
        
        conn.commit()
    finally:
        conn.close()


# Initialize tables on module load
init_feedback_table()


# Pydantic models
class FeedbackAutoSaveRequest(BaseModel):
    message_id: str
    content: str
    timestamp: str
    partial: bool = True


class FeedbackSubmitRequest(BaseModel):
    message_id: str
    message_content: Optional[str] = None
    feedback: str
    quality_score: int = Field(ge=0, le=5)
    credits_earned: int = Field(ge=0, le=10)
    timestamp: str


class FeedbackResponse(BaseModel):
    success: bool
    message: str
    credits_earned: int = 0
    total_credits: int = 0


class CreditInfoResponse(BaseModel):
    user_id: str
    total_credits: int
    earned_from_feedback: int
    pending_feedback_credits: int


@router.post("/auto-save")
async def auto_save_feedback(
    request: Request,
    feedback_data: FeedbackAutoSaveRequest
):
    """
    Auto-save feedback draft as user types.
    Stores in temporary drafts table.
    """
    try:
        # Get user ID from auth context (fallback to session ID)
        user_id = getattr(request.state, 'user_id', None) or f"anon_{request.client.host}"
        
        conn = get_db_connection()
        try:
            # Upsert draft
            conn.execute("""
                INSERT INTO feedback_drafts (user_id, message_id, draft_content, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, message_id) DO UPDATE SET
                    draft_content = excluded.draft_content,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, feedback_data.message_id, feedback_data.content))
            
            conn.commit()
            
            return {
                "success": True,
                "message": "Draft saved",
                "timestamp": datetime.now().isoformat()
            }
        finally:
            conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save draft: {str(e)}")


@router.post("/submit")
async def submit_feedback(
    request: Request,
    feedback_data: FeedbackSubmitRequest
):
    """
    Submit final feedback and award credits based on quality.
    Credits are awarded via the unified credits manager.
    """
    try:
        # Get user ID from auth context
        user_id = getattr(request.state, 'user_id', None) or f"anon_{request.client.host}"
        session_id = getattr(request.state, 'session_id', None)
        
        conn = get_db_connection()
        try:
            # Check if feedback already submitted for this message
            existing = conn.execute(
                "SELECT id FROM message_feedback WHERE user_id = ? AND message_id = ?",
                (user_id, feedback_data.message_id)
            ).fetchone()
            
            if existing:
                raise HTTPException(status_code=400, detail="Feedback already submitted for this message")
            
            # Insert feedback
            conn.execute("""
                INSERT INTO message_feedback 
                (user_id, message_id, session_id, message_content, feedback_text, 
                 quality_score, credits_earned, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'submitted', CURRENT_TIMESTAMP)
            """, (
                user_id, 
                feedback_data.message_id,
                session_id,
                feedback_data.message_content,
                feedback_data.feedback,
                feedback_data.quality_score,
                feedback_data.credits_earned
            ))
            
            # Delete draft if exists
            conn.execute(
                "DELETE FROM feedback_drafts WHERE user_id = ? AND message_id = ?",
                (user_id, feedback_data.message_id)
            )
            
            conn.commit()
            
        finally:
            conn.close()
        
        # Award credits via unified credits manager
        try:
            manager = get_credits_manager()
            result = manager.award_feedback_credits(user_id, feedback_data.quality_score)
            credits_awarded = result.get('credits_added', feedback_data.credits_earned)
            total_credits = result.get('new_balance', 0)
            logger.info(f"[Feedback] Awarded {credits_awarded} credits to {user_id} for feedback")
        except Exception as e:
            logger.error(f"[Feedback] Failed to award credits: {e}")
            credits_awarded = feedback_data.credits_earned
            total_credits = 0
            
        return {
            "success": True,
            "message": "Thank you for your feedback!",
            "credits_earned": credits_awarded,
            "total_credits": total_credits
        }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")


@router.get("/credits")
async def get_user_credits(request: Request):
    """
    Get user's current credit balance and feedback statistics.
    Uses unified credits manager for credit balance.
    """
    try:
        user_id = getattr(request.state, 'user_id', None) or f"anon_{request.client.host}"
        
        # Get credit balance from unified system
        try:
            manager = get_credits_manager()
            balance = manager.get_balance(user_id)
            total_credits = balance.get('total_available', 0)
        except Exception as e:
            logger.error(f"[Feedback] Failed to get balance: {e}")
            total_credits = 0
        
        # Get feedback-specific stats from local DB
        conn = get_db_connection()
        try:
            # Count pending feedback (drafts that could be submitted)
            pending = conn.execute(
                "SELECT COUNT(*) as count FROM feedback_drafts WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            # Get total credits earned from feedback
            earned = conn.execute(
                "SELECT SUM(credits_earned) as total FROM message_feedback WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            return {
                "user_id": user_id,
                "total_credits": total_credits,
                "earned_from_feedback": earned['total'] if earned and earned['total'] else 0,
                "pending_feedback_credits": pending['count'] * 5  # Estimate max potential credits
            }
        finally:
            conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get credits: {str(e)}")


@router.get("/history")
async def get_feedback_history(
    request: Request,
    limit: int = 50,
    offset: int = 0
):
    """
    Get user's feedback history.
    """
    try:
        user_id = getattr(request.state, 'user_id', None) or f"anon_{request.client.host}"
        
        conn = get_db_connection()
        try:
            feedbacks = conn.execute("""
                SELECT message_id, message_content, feedback_text, 
                       quality_score, credits_earned, created_at
                FROM message_feedback
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset)).fetchall()
            
            return {
                "feedbacks": [dict(f) for f in feedbacks],
                "total": len(feedbacks),
            }
        finally:
            conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.get("/drafts")
async def get_drafts(request: Request):
    """Get user's saved drafts."""
    try:
        user_id = getattr(request.state, 'user_id', None) or f"anon_{request.client.host}"
        
        conn = get_db_connection()
        try:
            drafts = conn.execute("""
                SELECT message_id, draft_content, updated_at
                FROM feedback_drafts
                WHERE user_id = ?
                ORDER BY updated_at DESC
            """, (user_id,)).fetchall()
            
            return {
                "drafts": [dict(d) for d in drafts]
            }
        finally:
            conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get drafts: {str(e)}")


@router.delete("/drafts/{message_id}")
async def delete_draft(request: Request, message_id: str):
    """Delete a specific draft."""
    try:
        user_id = getattr(request.state, 'user_id', None) or f"anon_{request.client.host}"
        
        conn = get_db_connection()
        try:
            conn.execute(
                "DELETE FROM feedback_drafts WHERE user_id = ? AND message_id = ?",
                (user_id, message_id)
            )
            conn.commit()
            
            return {"success": True, "message": "Draft deleted"}
        finally:
            conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete draft: {str(e)}")
