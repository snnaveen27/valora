"""
Valora AI - Decision-Room API Routes (Family Hub)

FOCUSED: Multi-stakeholder buying workflow for broker productivity.

This is NOT social or decorative - this is a real workflow for buyer committees.
Primary KPI is WAWU (Weekly Active Workflow Users), driven by recurring workflow actions.

Core Endpoints:
  Session Management (Decision-Room):
    POST   /api/family/session                    - Create decision-room for property search
    GET    /api/family/sessions                   - Get all decision-rooms for user
    GET    /api/family/session/{session_id}       - Get specific decision-room details
    PUT    /api/family/session/{session_id}       - Update decision-room settings
    DELETE /api/family/session/{session_id}       - Archive/delete decision-room
  
  Committee Member Management:
    POST   /api/family/session/{session_id}/invite      - Invite stakeholder
    GET    /api/family/session/{session_id}/members     - Get all stakeholders
    PUT    /api/family/session/{session_id}/member/{member_id} - Update member role
    DELETE /api/family/session/{session_id}/member/{member_id} - Remove member
    POST   /api/family/session/{session_id}/join        - Accept invitation
  
  Property Shortlist (Client-Ready):
    POST   /api/family/session/{session_id}/watchlist   - Add property to shortlist
    GET    /api/family/session/{session_id}/watchlist   - Get shortlist
    PUT    /api/family/session/{session_id}/watchlist/{item_id} - Update item status
    DELETE /api/family/session/{session_id}/watchlist/{item_id} - Remove from shortlist
  
  Voting & Decision Support:
    POST   /api/family/session/{session_id}/vote        - Cast vote on property
    GET    /api/family/session/{session_id}/votes       - Get all votes
    GET    /api/family/session/{session_id}/votes/{property_id} - Get votes for property
    GET    /api/family/session/{session_id}/vote-summary - Get decision summary (CLIENT-READY)
  
  Activity Feed:
    GET    /api/family/session/{session_id}/timeline    - Get decision activity
    GET    /api/family/session/{session_id}/statistics  - Get session statistics
  
  Sharing:
    POST   /api/family/session/{session_id}/share       - Generate share link
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field, validator
from enum import Enum

from auth.user_auth import User
from routes.auth_routes import require_auth
from database.community_pulse_schema import (
    CommunityPulseDB,
    get_community_pulse_db,
    create_family_session,
    get_family_session,
    get_user_family_sessions,
    update_family_session,
    delete_family_session,
    add_family_member,
    get_family_members,
    update_family_member,
    remove_family_member,
    add_to_watchlist,
    get_watchlist,
    update_watchlist_entry,
    remove_from_watchlist,
    cast_vote,
    get_votes_for_property,
    get_vote_summary,
    delete_vote,
    add_timeline_event,
    get_timeline_events,
    get_session_statistics,
)

logger = logging.getLogger("valora.family_routes")

router = APIRouter(prefix="/api/family", tags=["Decision-Room (Multi-stakeholder)"])


# ============================================================================
# ENUMS
# ============================================================================

class SessionStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"


class MemberRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class InviteStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class VoteType(str, Enum):
    UP = "up"
    DOWN = "down"
    MAYBE = "maybe"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class WatchlistStatus(str, Enum):
    CONSIDERING = "considering"
    SHORTLISTED = "shortlisted"
    VISITED = "visited"
    REJECTED = "rejected"


# ============================================================================
# REQUEST MODELS
# ============================================================================

class CreateSessionRequest(BaseModel):
    """Request to create a new family session."""
    family_name: str = Field(..., min_length=1, max_length=100, description="Name for the family session")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")
    target_locality: Optional[str] = Field(None, max_length=200, description="Target area/locality")
    budget_min: Optional[float] = Field(None, ge=0, description="Minimum budget")
    budget_max: Optional[float] = Field(None, ge=0, description="Maximum budget")
    property_types: Optional[List[str]] = Field(None, description="List of preferred property types")
    settings: Optional[Dict[str, Any]] = Field(None, description="Additional settings")
    
    @validator('budget_max')
    def budget_max_greater_than_min(cls, v, values):
        if v is not None and 'budget_min' in values and values['budget_min'] is not None:
            if v < values['budget_min']:
                raise ValueError('budget_max must be greater than budget_min')
        return v


class UpdateSessionRequest(BaseModel):
    """Request to update a family session."""
    family_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    target_locality: Optional[str] = Field(None, max_length=200)
    budget_min: Optional[float] = Field(None, ge=0)
    budget_max: Optional[float] = Field(None, ge=0)
    property_types: Optional[List[str]] = None
    settings: Optional[Dict[str, Any]] = None
    status: Optional[SessionStatus] = None
    
    @validator('budget_max')
    def budget_max_greater_than_min(cls, v, values):
        if v is not None and 'budget_min' in values and values['budget_min'] is not None:
            if v < values['budget_min']:
                raise ValueError('budget_max must be greater than budget_min')
        return v


class InviteMemberRequest(BaseModel):
    """Request to invite a family member."""
    name: str = Field(..., min_length=1, max_length=100, description="Member's name")
    email: Optional[str] = Field(None, description="Email for invitation")
    phone: Optional[str] = Field(None, description="Phone for invitation")
    role: MemberRole = Field(MemberRole.MEMBER, description="Member role")
    
    @validator('role')
    def cannot_assign_owner(cls, v):
        if v == MemberRole.OWNER:
            raise ValueError("Cannot assign owner role through invitation")
        return v


class JoinSessionRequest(BaseModel):
    """Request to accept an invitation and join a session."""
    invite_token: Optional[str] = Field(None, description="Invitation token (optional)")
    name: Optional[str] = Field(None, max_length=100, description="Display name (if not provided from account)")


class UpdateMemberRequest(BaseModel):
    """Request to update a family member's role."""
    role: Optional[MemberRole] = Field(None, description="New role")
    name: Optional[str] = Field(None, max_length=100, description="Updated name")


class AddToWatchlistRequest(BaseModel):
    """Request to add a property to the watchlist."""
    property_id: Optional[str] = Field(None, description="Property ID (if from database)")
    property_title: Optional[str] = Field(None, max_length=500, description="Property title")
    locality: Optional[str] = Field(None, max_length=200, description="Property locality")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Property latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Property longitude")
    price: Optional[float] = Field(None, ge=0, description="Property price")
    notes: Optional[str] = Field(None, max_length=1000, description="Notes about the property")
    priority: Priority = Field(Priority.MEDIUM, description="Priority level")


class UpdateWatchlistRequest(BaseModel):
    """Request to update a watchlist entry."""
    notes: Optional[str] = Field(None, max_length=1000)
    priority: Optional[Priority] = None
    status: Optional[WatchlistStatus] = None


class CastVoteRequest(BaseModel):
    """Request to cast a vote on a property."""
    property_id: str = Field(..., description="Property ID")
    vote: VoteType = Field(..., description="Vote value")
    aspects: Optional[Dict[str, str]] = Field(None, description="Aspect-level votes (e.g., {'location': 'up', 'price': 'down'})")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional comment")


class ShareSessionRequest(BaseModel):
    """Request to generate a share link for a session."""
    expiry_hours: int = Field(72, ge=1, le=168, description="Hours until share link expires")
    max_uses: Optional[int] = Field(None, ge=1, le=100, description="Maximum number of uses")


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class SessionResponse(BaseModel):
    """Response for a family session."""
    id: str
    owner_user_id: str
    family_name: str
    description: Optional[str]
    target_locality: Optional[str]
    budget_min: Optional[float]
    budget_max: Optional[float]
    property_types: Optional[List[str]]
    settings: Optional[Dict[str, Any]]
    status: str
    created_at: str
    updated_at: str
    is_owner: bool = False


class MemberResponse(BaseModel):
    """Response for a family member."""
    id: str
    session_id: str
    user_id: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    name: str
    role: str
    invite_status: str
    invited_at: Optional[str]
    joined_at: Optional[str]
    created_at: str


class WatchlistItemResponse(BaseModel):
    """Response for a watchlist item."""
    id: str
    session_id: str
    property_id: Optional[str]
    property_title: Optional[str]
    locality: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    price: Optional[float]
    added_by: str
    notes: Optional[str]
    priority: str
    status: str
    created_at: str
    updated_at: str


class VoteResponse(BaseModel):
    """Response for a vote."""
    id: str
    session_id: str
    property_id: str
    user_id: str
    vote: str
    aspects: Optional[Dict[str, str]]
    comment: Optional[str]
    created_at: str
    updated_at: str


class VoteSummaryResponse(BaseModel):
    """Response for vote summary."""
    property_id: str
    total_votes: int
    up: int
    down: int
    maybe: int
    aspects_summary: Dict[str, Dict[str, int]]
    comments: List[Dict[str, str]]


class TimelineEventResponse(BaseModel):
    """Response for a timeline event."""
    id: str
    session_id: str
    event_type: str
    event_data: Optional[Dict[str, Any]]
    user_id: Optional[str]
    created_at: str


class StatisticsResponse(BaseModel):
    """Response for session statistics."""
    member_count: int
    watchlist: Dict[str, int]
    votes: Dict[str, int]
    event_count: int


class ShareResponse(BaseModel):
    """Response for share link generation."""
    share_token: str
    share_url: str
    expires_at: str
    max_uses: Optional[int]


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_db() -> CommunityPulseDB:
    """Get the Community Pulse database instance."""
    return get_community_pulse_db()


async def award_credits(user_id: str, amount: int, reason: str) -> bool:
    """
    Award credits to a user for family hub actions.
    
    Args:
        user_id: User ID to award credits to
        amount: Number of credits to award
        reason: Reason for the award (for logging)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from ai.credits_rate_limiter import get_rate_limiter
        rl = get_rate_limiter()
        
        # Add top-up credits
        rl.add_top_up_credits(user_id, amount)
        
        logger.info(f"[FamilyHub] Awarded {amount} credits to {user_id} for: {reason}")
        return True
    except Exception as e:
        logger.error(f"[FamilyHub] Failed to award credits: {e}")
        return False


async def check_session_access(
    db: CommunityPulseDB,
    session_id: str,
    user_id: str,
    require_owner: bool = False
) -> Dict[str, Any]:
    """
    Check if a user has access to a session.
    
    Args:
        db: Database instance
        session_id: Session ID
        user_id: User ID
        require_owner: If True, only owner can access
    
    Returns:
        Session data if access granted
    
    Raises:
        HTTPException: If access denied
    """
    session = get_family_session(db, session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if user is owner
    if session['owner_user_id'] == user_id:
        return session
    
    if require_owner:
        raise HTTPException(status_code=403, detail="Only the session owner can perform this action")
    
    # Check if user is a member
    members = get_family_members(db, session_id)
    user_member = next(
        (m for m in members if m['user_id'] == user_id and m['invite_status'] == 'accepted'),
        None
    )
    
    if not user_member:
        raise HTTPException(status_code=403, detail="You are not a member of this session")
    
    return session


async def check_member_permission(
    db: CommunityPulseDB,
    session_id: str,
    user_id: str,
    allowed_roles: List[str] = ['owner', 'admin', 'member']
) -> Dict[str, Any]:
    """
    Check if a user has permission based on their role.
    
    Args:
        db: Database instance
        session_id: Session ID
        user_id: User ID
        allowed_roles: List of roles that have permission
    
    Returns:
        Member data if permission granted
    
    Raises:
        HTTPException: If permission denied
    """
    session = await check_session_access(db, session_id, user_id)
    
    # Owner always has permission
    if session['owner_user_id'] == user_id:
        return {'role': 'owner', 'session': session}
    
    # Check member role
    members = get_family_members(db, session_id)
    user_member = next(
        (m for m in members if m['user_id'] == user_id and m['invite_status'] == 'accepted'),
        None
    )
    
    if not user_member:
        raise HTTPException(status_code=403, detail="You are not a member of this session")
    
    if user_member['role'] not in allowed_roles:
        raise HTTPException(status_code=403, detail="You don't have permission for this action")
    
    return {'role': user_member['role'], 'session': session, 'member': user_member}


# ============================================================================
# SESSION MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/session", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    user: User = Depends(require_auth)
):
    """
    Create a new family session for collaborative property search.
    
    Awards +5 credits for creating a family session.
    """
    db = get_db()
    
    session_id = create_family_session(
        db=db,
        owner_user_id=user.id,
        family_name=request.family_name,
        description=request.description,
        target_locality=request.target_locality,
        budget_min=request.budget_min,
        budget_max=request.budget_max,
        property_types=request.property_types,
        settings=request.settings
    )
    
    if not session_id:
        raise HTTPException(status_code=500, detail="Failed to create session")
    
    # Add timeline event
    add_timeline_event(
        db=db,
        session_id=session_id,
        event_type="session_created",
        event_data={"family_name": request.family_name},
        user_id=user.id
    )
    
    # Award credits for creating a family session
    await award_credits(user.id, 5, "creating family session")
    
    # Get the created session
    session = get_family_session(db, session_id)
    session['is_owner'] = True
    
    logger.info(f"[FamilyHub] Created session {session_id} for user {user.id}")
    
    return SessionResponse(**session)


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    status: Optional[SessionStatus] = Query(None, description="Filter by status"),
    user: User = Depends(require_auth)
):
    """Get all family sessions for the current user (as owner or member)."""
    db = get_db()
    
    sessions = get_user_family_sessions(
        db=db,
        user_id=user.id,
        status=status.value if status else None
    )
    
    # Add is_owner flag
    for session in sessions:
        session['is_owner'] = session['owner_user_id'] == user.id
    
    return [SessionResponse(**s) for s in sessions]


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str = Path(..., description="Session ID"),
    user: User = Depends(require_auth)
):
    """Get details of a specific family session."""
    db = get_db()
    
    session = await check_session_access(db, session_id, user.id)
    session['is_owner'] = session['owner_user_id'] == user.id
    
    return SessionResponse(**session)


@router.put("/session/{session_id}", response_model=SessionResponse)
async def update_session(
    request: UpdateSessionRequest,
    session_id: str = Path(..., description="Session ID"),
    user: User = Depends(require_auth)
):
    """
    Update a family session's settings.
    
    Only the session owner can update settings.
    """
    db = get_db()
    
    # Only owner can update session
    session = await check_session_access(db, session_id, user.id, require_owner=True)
    
    # Build update dict (only non-None values)
    updates = request.dict(exclude_unset=True)
    
    if updates:
        success = update_family_session(db, session_id, **updates)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update session")
        
        # Add timeline event
        add_timeline_event(
            db=db,
            session_id=session_id,
            event_type="session_updated",
            event_data={"updates": list(updates.keys())},
            user_id=user.id
        )
    
    # Get updated session
    session = get_family_session(db, session_id)
    session['is_owner'] = True
    
    return SessionResponse(**session)


@router.delete("/session/{session_id}", response_model=SuccessResponse)
async def archive_session(
    session_id: str = Path(..., description="Session ID"),
    user: User = Depends(require_auth)
):
    """
    Archive/delete a family session.
    
    Only the session owner can archive the session.
    This sets the status to 'archived' instead of hard delete.
    """
    db = get_db()
    
    # Only owner can archive session
    await check_session_access(db, session_id, user.id, require_owner=True)
    
    # Archive instead of delete
    success = update_family_session(db, session_id, status='archived')
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to archive session")
    
    # Add timeline event
    add_timeline_event(
        db=db,
        session_id=session_id,
        event_type="session_archived",
        event_data={},
        user_id=user.id
    )
    
    logger.info(f"[FamilyHub] Archived session {session_id}")
    
    return SuccessResponse(message="Session archived successfully")


# ============================================================================
# MEMBER MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/session/{session_id}/invite", response_model=MemberResponse)
async def invite_member(
    request: InviteMemberRequest,
    session_id: str = Path(..., description="Session ID"),
    user: User = Depends(require_auth)
):
    """
    Invite a family member to join the session.
    
    Awards +3 credits per successful invitation.
    Only owner and admins can invite members.
    """
    db = get_db()
    
    # Check permission (owner or admin can invite)
    perm = await check_member_permission(
        db, session_id, user.id,
        allowed_roles=['owner', 'admin', 'member']
    )
    
    # Check if at least one contact method is provided
    if not request.email and not request.phone:
        raise HTTPException(status_code=400, detail="At least one of email or phone is required")
    
    # Add member
    member_id = add_family_member(
        db=db,
        session_id=session_id,
        name=request.name,
        email=request.email,
        phone=request.phone,
        role=request.role.value
    )
    
    if not member_id:
        raise HTTPException(status_code=500, detail="Failed to add member")
    
    # Add timeline event
    add_timeline_event(
        db=db,
        session_id=session_id,
        event_type="member_invited",
        event_data={
            "member_name": request.name,
            "member_email": request.email,
            "role": request.role.value
        },
        user_id=user.id
    )
    
    # Award credits for inviting a family member
    await award_credits(user.id, 3, "inviting family member")
    
    # Get the created member
    members = get_family_members(db, session_id)
    member = next((m for m in members if m['id'] == member_id), None)
    
    logger.info(f"[FamilyHub] Invited member {member_id} to session {session_id}")
    
    return MemberResponse(**member)


@router.get("/session/{session_id}/members", response_model=List[MemberResponse])
async def list_members(
    session_id: str = Path(..., description="Session ID"),
    user: User = Depends(require_auth)
):
    """Get all members of a family session."""
    db = get_db()
    
    # Check access
    await check_session_access(db, session_id, user.id)
    
    members = get_family_members(db, session_id)
    
    return [MemberResponse(**m) for m in members]


@router.put("/session/{session_id}/member/{member_id}", response_model=MemberResponse)
async def update_member(
    request: UpdateMemberRequest,
    session_id: str = Path(..., description="Session ID"),
    member_id: str = Path(..., description="Member ID"),
    user: User = Depends(require_auth)
):
    """
    Update a family member's role or name.
    
    Only owner and admins can update member roles.
    """
    db = get_db()
    
    # Check permission
    perm = await check_member_permission(
        db, session_id, user.id,
        allowed_roles=['owner', 'admin']
    )
    
    # Get member
    members = get_family_members(db, session_id)
    member = next((m for m in members if m['id'] == member_id), None)
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Cannot change owner's role
    if member['role'] == 'owner':
        raise HTTPException(status_code=400, detail="Cannot modify owner's role")
    
    # Build update dict
    updates = request.dict(exclude_unset=True)
    
    if updates:
        # Convert enum to value if present
        if 'role' in updates and updates['role'] is not None:
            updates['role'] = updates['role'].value
        
        success = update_family_member(db, member_id, **updates)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update member")
        
        # Add timeline event
        add_timeline_event(
            db=db,
            session_id=session_id,
            event_type="member_updated",
            event_data={"member_id": member_id, "updates": list(updates.keys())},
            user_id=user.id
        )
    
    # Get updated member
    members = get_family_members(db, session_id)
    member = next((m for m in members if m['id'] == member_id), None)
    
    return MemberResponse(**member)


@router.delete("/session/{session_id}/member/{member_id}", response_model=SuccessResponse)
async def remove_member(
    session_id: str = Path(..., description="Session ID"),
    member_id: str = Path(..., description="Member ID"),
    user: User = Depends(require_auth)
):
    """
    Remove a member from the family session.
    
    Only owner and admins can remove members.
    """
    db = get_db()
    
    # Check permission
    perm = await check_member_permission(
        db, session_id, user.id,
        allowed_roles=['owner', 'admin']
    )
    
    # Get member
    members = get_family_members(db, session_id)
    member = next((m for m in members if m['id'] == member_id), None)
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Cannot remove owner
    if member['role'] == 'owner':
        raise HTTPException(status_code=400, detail="Cannot remove the session owner")
    
    success = remove_family_member(db, member_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove member")
    
    # Add timeline event
    add_timeline_event(
        db=db,
        session_id=session_id,
        event_type="member_removed",
        event_data={"member_name": member['name']},
        user_id=user.id
    )
    
    logger.info(f"[FamilyHub] Removed member {member_id} from session {session_id}")
    
    return SuccessResponse(message="Member removed successfully")


@router.post("/session/{session_id}/join", response_model=MemberResponse)
async def join_session(
    request: JoinSessionRequest,
    session_id: str = Path(..., description="Session ID"),
    user: User = Depends(require_auth)
):
    """
    Accept an invitation and join a family session.
    
    This endpoint is called when a user clicks an invite link.
    """
    db = get_db()
    
    # Check if session exists
    session = get_family_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Find pending invitation for this user
    members = get_family_members(db, session_id)
    
    # Try to find by user_id or email
    member = next(
        (m for m in members if (
            m['user_id'] == user.id or 
            (m['email'] and m['email'].lower() == user.email.lower())
        ) and m['invite_status'] == 'pending'),
        None
    )
    
    if not member:
        raise HTTPException(status_code=404, detail="No pending invitation found for this session")
    
    # Update member to accepted
    update_data = {
        'invite_status': 'accepted',
        'joined_at': datetime.now().isoformat(),
        'user_id': user.id  # Link to actual user account
    }
    
    if request.name:
        update_data['name'] = request.name
    
    success = update_family_member(db, member['id'], **update_data)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to join session")
    
    # Add timeline event
    add_timeline_event(
        db=db,
        session_id=session_id,
        event_type="member_joined",
        event_data={"member_name": request.name or member['name']},
        user_id=user.id
    )
    
    # Get updated member
    members = get_family_members(db, session_id)
    member = next((m for m in members if m['id'] == member['id']), None)
    
    logger.info(f"[FamilyHub] User {user.id} joined session {session_id}")
    
    return MemberResponse(**member)


# ============================================================================
# WATCHLIST MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/session/{session_id}/watchlist", response_model=WatchlistItemResponse)
async def add_property_to_watchlist(
    request: AddToWatchlistRequest,
    session_id: str = Path(..., description="Session ID"),
    user: User = Depends(require_auth)
):
    """Add a property to the family watchlist."""
    db = get_db()
    
    # Check access
    await check_session_access(db, session_id, user.id)
    
    # Add to watchlist
    entry_id = add_to_watchlist(
        db=db,
        session_id=session_id,
        added_by=user.id,
        property_id=request.property_id,
        property_title=request.property_title,
        locality=request.locality,
        latitude=request.latitude,
        longitude=request.longitude,
        price=request.price,
        notes=request.notes,
        priority=request.priority.value
    )
    
    if not entry_id:
        raise HTTPException(status_code=500, detail="Failed to add to watchlist")
    
    # Add timeline event
    add_timeline_event(
        db=db,
        session_id=session_id,
        event_type="property_added",
        event_data={
            "property_id": request.property_id,
            "property_title": request.property_title,
            "priority": request.priority.value
        },
        user_id=user.id
    )
    
    # Get the created entry
    watchlist = get_watchlist(db, session_id)
    entry = next((w for w in watchlist if w['id'] == entry_id), None)
    
    logger.info(f"[FamilyHub] Added property to watchlist {entry_id}")
    
    return WatchlistItemResponse(**entry)


@router.get("/session/{session_id}/watchlist", response_model=List[WatchlistItemResponse])
async def get_session_watchlist(
    session_id: str = Path(..., description="Session ID"),
    status: Optional[WatchlistStatus] = Query(None, description="Filter by status"),
    user: User = Depends(require_auth)
):
    """Get the watchlist for a family session."""
    db = get_db()
    
    # Check access
    await check_session_access(db, session_id, user.id)
    
    watchlist = get_watchlist(
        db=db,
        session_id=session_id,
        status=status.value if status else None
    )
    
    return [WatchlistItemResponse(**w) for w in watchlist]


@router.put("/session/{session_id}/watchlist/{item_id}", response_model=WatchlistItemResponse)
async def update_watchlist_item(
    request: UpdateWatchlistRequest,
    session_id: str = Path(..., description="Session ID"),
    item_id: str = Path(..., description="Watchlist item ID"),
    user: User = Depends(require_auth)
):
    """Update a watchlist item."""
    db = get_db()
    
    # Check access
    await check_session_access(db, session_id, user.id)
    
    # Build update dict
    updates = request.dict(exclude_unset=True)
    
    # Convert enums to values
    if 'priority' in updates and updates['priority'] is not None:
        updates['priority'] = updates['priority'].value
    if 'status' in updates and updates['status'] is not None:
        updates['status'] = updates['status'].value
    
    if updates:
        success = update_watchlist_entry(db, item_id, **updates)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update watchlist item")
        
        # Add timeline event
        add_timeline_event(
            db=db,
            session_id=session_id,
            event_type="watchlist_updated",
            event_data={"item_id": item_id, "updates": list(updates.keys())},
            user_id=user.id
        )
    
    # Get updated entry
    watchlist = get_watchlist(db, session_id)
    entry = next((w for w in watchlist if w['id'] == item_id), None)
    
    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    
    return WatchlistItemResponse(**entry)


@router.delete("/session/{session_id}/watchlist/{item_id}", response_model=SuccessResponse)
async def remove_from_watchlist_endpoint(
    session_id: str = Path(..., description="Session ID"),
    item_id: str = Path(..., description="Watchlist item ID"),
    user: User = Depends(require_auth)
):
    """Remove a property from the watchlist."""
    db = get_db()
    
    # Check access
    await check_session_access(db, session_id, user.id)
    
    success = remove_from_watchlist(db, item_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove from watchlist")
    
    # Add timeline event
    add_timeline_event(
        db=db,
        session_id=session_id,
        event_type="property_removed",
        event_data={"item_id": item_id},
        user_id=user.id
    )
    
    logger.info(f"[FamilyHub] Removed item {item_id} from watchlist")
    
    return SuccessResponse(message="Property removed from watchlist")


# ============================================================================
# VOTING SYSTEM ENDPOINTS
# ============================================================================

@router.post("/session/{session_id}/vote", response_model=VoteResponse)
async def cast_vote_endpoint(
    request: CastVoteRequest,
    session_id: str = Path(..., description="Session ID"),
    user: User = Depends(require_auth)
):
    """
    Cast or update a vote on a property.
    
    If all family members have voted, awards +15 credits for consensus.
    """
    db = get_db()
    
    # Check access
    await check_session_access(db, session_id, user.id)
    
    # Cast vote
    vote_id = cast_vote(
        db=db,
        session_id=session_id,
        property_id=request.property_id,
        user_id=user.id,
        vote=request.vote.value,
        aspects=request.aspects,
        comment=request.comment
    )
    
    if not vote_id:
        raise HTTPException(status_code=500, detail="Failed to cast vote")
    
    # Add timeline event
    add_timeline_event(
        db=db,
        session_id=session_id,
        event_type="vote_cast",
        event_data={
            "property_id": request.property_id,
            "vote": request.vote.value
        },
        user_id=user.id
    )
    
    # Check if all members have voted (consensus)
    members = get_family_members(db, session_id)
    accepted_members = [m for m in members if m['invite_status'] == 'accepted']
    
    # Get all votes for this property
    votes = get_votes_for_property(db, session_id, request.property_id)
    
    # Check if all accepted members have voted
    voted_user_ids = {v['user_id'] for v in votes}
    all_voted = all(
        m['user_id'] in voted_user_ids 
        for m in accepted_members 
        if m['user_id']
    )
    
    # Also check if owner has voted
    session = get_family_session(db, session_id)
    owner_voted = session['owner_user_id'] in voted_user_ids
    
    if all_voted and owner_voted and len(accepted_members) > 0:
        # Award consensus credits to all voters
        for voter_id in voted_user_ids:
            await award_credits(voter_id, 15, "family reaching consensus")
        
        # Add timeline event for consensus
        add_timeline_event(
            db=db,
            session_id=session_id,
            event_type="consensus_reached",
            event_data={"property_id": request.property_id},
            user_id=user.id
        )
        
        logger.info(f"[FamilyHub] Consensus reached on property {request.property_id}")
    
    # Get the vote
    votes = get_votes_for_property(db, session_id, request.property_id)
    vote = next((v for v in votes if v['id'] == vote_id), None)
    
    logger.info(f"[FamilyHub] Cast vote {vote_id}")
    
    return VoteResponse(**vote)


@router.get("/session/{session_id}/votes", response_model=List[VoteResponse])
async def get_all_votes(
    session_id: str = Path(..., description="Session ID"),
    user: User = Depends(require_auth)
):
    """Get all votes in a family session."""
    db = get_db()
    
    # Check access
    await check_session_access(db, session_id, user.id)
    
    # Get all votes for session (need to query all properties in watchlist)
    watchlist = get_watchlist(db, session_id)
    all_votes = []
    
    for item in watchlist:
        if item['property_id']:
            votes = get_votes_for_property(db, session_id, item['property_id'])
            all_votes.extend(votes)
    
    return [VoteResponse(**v) for v in all_votes]


@router.get("/session/{session_id}/votes/{property_id}", response_model=List[VoteResponse])
async def get_property_votes(
    session_id: str = Path(..., description="Session ID"),
    property_id: str = Path(..., description="Property ID"),
    user: User = Depends(require_auth)
):
    """Get all votes for a specific property."""
    db = get_db()
    
    # Check access
    await check_session_access(db, session_id, user.id)
    
    votes = get_votes_for_property(db, session_id, property_id)
    
    return [VoteResponse(**v) for v in votes]


@router.get("/session/{session_id}/vote-summary", response_model=Dict[str, VoteSummaryResponse])
async def get_vote_summaries(
    session_id: str = Path(..., description="Session ID"),
    user: User = Depends(require_auth)
):
    """Get vote summary for all properties in the watchlist."""
    db = get_db()
    
    # Check access
    await check_session_access(db, session_id, user.id)
    
    watchlist = get_watchlist(db, session_id)
    summaries = {}
    
    for item in watchlist:
        if item['property_id']:
            summary = get_vote_summary(db, session_id, item['property_id'])
            summaries[item['property_id']] = VoteSummaryResponse(
                property_id=item['property_id'],
                **summary
            )
    
    return summaries


# ============================================================================
# TIMELINE & STATISTICS ENDPOINTS
# ============================================================================

@router.get("/session/{session_id}/timeline", response_model=List[TimelineEventResponse])
async def get_session_timeline(
    session_id: str = Path(..., description="Session ID"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of events"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user: User = Depends(require_auth)
):
    """Get timeline events for a family session."""
    db = get_db()
    
    # Check access
    await check_session_access(db, session_id, user.id)
    
    events = get_timeline_events(
        db=db,
        session_id=session_id,
        limit=limit,
        offset=offset,
        event_type=event_type
    )
    
    return [TimelineEventResponse(**e) for e in events]


@router.get("/session/{session_id}/statistics", response_model=StatisticsResponse)
async def get_session_stats(
    session_id: str = Path(..., description="Session ID"),
    user: User = Depends(require_auth)
):
    """Get comprehensive statistics for a family session."""
    db = get_db()
    
    # Check access
    await check_session_access(db, session_id, user.id)
    
    stats = get_session_statistics(db, session_id)
    
    return StatisticsResponse(**stats)


# ============================================================================
# SHARING ENDPOINTS
# ============================================================================

# In-memory store for share tokens (in production, use database)
_share_tokens: Dict[str, Dict[str, Any]] = {}


@router.post("/session/{session_id}/share", response_model=ShareResponse)
async def generate_share_link(
    request: ShareSessionRequest,
    session_id: str = Path(..., description="Session ID"),
    user: User = Depends(require_auth)
):
    """
    Generate a share link for inviting family members.
    
    Only owner and admins can generate share links.
    """
    import secrets
    from datetime import timedelta
    
    db = get_db()
    
    # Check permission
    perm = await check_member_permission(
        db, session_id, user.id,
        allowed_roles=['owner', 'admin']
    )
    
    # Generate share token
    share_token = secrets.token_urlsafe(32)
    
    # Calculate expiry
    expires_at = (datetime.now() + timedelta(hours=request.expiry_hours)).isoformat()
    
    # Store token
    _share_tokens[share_token] = {
        "session_id": session_id,
        "created_by": user.id,
        "expires_at": expires_at,
        "max_uses": request.max_uses,
        "uses": 0
    }
    
    # Add timeline event
    add_timeline_event(
        db=db,
        session_id=session_id,
        event_type="share_link_created",
        event_data={"expiry_hours": request.expiry_hours},
        user_id=user.id
    )
    
    # Generate share URL (frontend will handle the route)
    share_url = f"/family/join/{session_id}?token={share_token}"
    
    logger.info(f"[FamilyHub] Generated share link for session {session_id}")
    
    return ShareResponse(
        share_token=share_token,
        share_url=share_url,
        expires_at=expires_at,
        max_uses=request.max_uses
    )


# ============================================================================
# INITIALIZATION
# ============================================================================

def init_family_routes():
    """Initialize family routes - call this when including the router."""
    # Initialize database tables
    from database.community_pulse_schema import init_community_pulse_tables
    init_community_pulse_tables()
    logger.info("[FamilyHub] Family routes initialized, tables created")
