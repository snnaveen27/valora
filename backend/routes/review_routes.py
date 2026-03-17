"""
Valora AI - Locality Review Routes

FOCUSED: Locality reviews with verified resident proof.

This supports the product thesis: "defensible locality context" that brokers need.
Key features:
- Verified resident badges (not anonymous reviews)
- India-specific categories: Vastu, schools, transport, safety
- Community validation (helpful votes)

REMOVED (not aligned with product thesis):
- Builder profiles and reviews (generic directory)
- RERA verification (not core to broker workflow)

Endpoints:
  Locality Reviews:
    POST   /api/reviews/locality                    - Submit locality review (with verification)
    GET    /api/reviews/locality/{locality_id}      - Get reviews for locality
    GET    /api/reviews/locality/{locality_id}/stats - Get review statistics
    PUT    /api/reviews/locality/{review_id}        - Update review
    DELETE /api/reviews/locality/{review_id}        - Delete review

  Community Validation:
    POST   /api/reviews/{review_type}/{review_id}/helpful - Mark review helpful
    DELETE /api/reviews/{review_type}/{review_id}/helpful - Remove helpful
    GET    /api/reviews/user/helpful                  - Get user's helpful reviews
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
    init_phase2_tables,
    create_locality_review,
    get_locality_reviews,
    get_locality_review_stats,
    update_locality_review,
    delete_locality_review,
    mark_review_helpful,
    unmark_review_helpful,
    get_user_helpful_reviews,
)

logger = logging.getLogger("valora.review_routes")

router = APIRouter(prefix="/api/reviews", tags=["Locality Reviews (Community)"])


# ============================================================================
# ENUMS
# ============================================================================

class ReviewType(str, Enum):
    LOCALITY = "locality"


class VerificationType(str, Enum):
    RESIDENT = "resident"
    OWNER = "owner"
    VISITOR = "visitor"


class SortBy(str, Enum):
    CREATED_AT = "created_at"
    HELPFUL_COUNT = "helpful_count"
    OVERALL_RATING = "overall_rating"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_db() -> CommunityPulseDB:
    """Get the Community Pulse database instance."""
    return get_community_pulse_db()


async def award_credits(user_id: str, amount: int, reason: str) -> bool:
    """
    Award credits to a user for review actions.
    
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
        
        logger.info(f"[Reviews] Awarded {amount} credits to {user_id} for: {reason}")
        return True
    except Exception as e:
        logger.error(f"[Reviews] Failed to award credits: {e}")
        return False


def init_review_routes() -> None:
    """Initialize the review routes database tables."""
    try:
        init_phase2_tables()
        logger.info("[Reviews] Phase 2 tables initialized successfully")
    except Exception as e:
        logger.error(f"[Reviews] Failed to initialize Phase 2 tables: {e}")


# ============================================================================
# REQUEST MODELS - LOCALITY REVIEWS
# ============================================================================

class CreateLocalityReviewRequest(BaseModel):
    """Request to create a locality review."""
    locality_id: str = Field(..., description="Locality ID")
    locality_name: str = Field(..., min_length=1, max_length=200, description="Locality name")
    overall_rating: float = Field(..., ge=1, le=5, description="Overall rating (1-5)")
    vastu_rating: Optional[float] = Field(None, ge=1, le=5, description="Vastu compliance rating")
    vastu_notes: Optional[str] = Field(None, max_length=500, description="Vastu notes")
    school_rating: Optional[float] = Field(None, ge=1, le=5, description="School proximity rating")
    school_notes: Optional[str] = Field(None, max_length=500, description="School notes")
    religious_proximity: Optional[Dict[str, str]] = Field(None, description="Religious place distances")
    transport_rating: Optional[float] = Field(None, ge=1, le=5, description="Transport connectivity rating")
    transport_notes: Optional[str] = Field(None, max_length=500, description="Transport notes")
    safety_rating: Optional[float] = Field(None, ge=1, le=5, description="Safety rating")
    safety_notes: Optional[str] = Field(None, max_length=500, description="Safety notes")
    amenities_rating: Optional[float] = Field(None, ge=1, le=5, description="Amenities rating")
    amenities_notes: Optional[str] = Field(None, max_length=500, description="Amenities notes")
    water_supply_rating: Optional[float] = Field(None, ge=1, le=5, description="Water supply rating")
    power_supply_rating: Optional[float] = Field(None, ge=1, le=5, description="Power supply rating")
    pros: Optional[List[str]] = Field(None, description="List of pros")
    cons: Optional[List[str]] = Field(None, description="List of cons")
    review_text: Optional[str] = Field(None, max_length=2000, description="Full review text")
    verification_type: Optional[VerificationType] = Field(None, description="Verification type")


class UpdateLocalityReviewRequest(BaseModel):
    """Request to update a locality review."""
    overall_rating: Optional[float] = Field(None, ge=1, le=5)
    vastu_rating: Optional[float] = Field(None, ge=1, le=5)
    vastu_notes: Optional[str] = Field(None, max_length=500)
    school_rating: Optional[float] = Field(None, ge=1, le=5)
    school_notes: Optional[str] = Field(None, max_length=500)
    religious_proximity: Optional[Dict[str, str]] = None
    transport_rating: Optional[float] = Field(None, ge=1, le=5)
    transport_notes: Optional[str] = Field(None, max_length=500)
    safety_rating: Optional[float] = Field(None, ge=1, le=5)
    safety_notes: Optional[str] = Field(None, max_length=500)
    amenities_rating: Optional[float] = Field(None, ge=1, le=5)
    amenities_notes: Optional[str] = Field(None, max_length=500)
    water_supply_rating: Optional[float] = Field(None, ge=1, le=5)
    power_supply_rating: Optional[float] = Field(None, ge=1, le=5)
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None
    review_text: Optional[str] = Field(None, max_length=2000)
    verification_type: Optional[VerificationType] = None


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class LocalityReviewResponse(BaseModel):
    """Response for a locality review."""
    id: str
    locality_id: str
    locality_name: str
    user_id: str
    overall_rating: float
    vastu_rating: Optional[float]
    vastu_notes: Optional[str]
    school_rating: Optional[float]
    school_notes: Optional[str]
    religious_proximity: Optional[Dict[str, str]]
    transport_rating: Optional[float]
    transport_notes: Optional[str]
    safety_rating: Optional[float]
    safety_notes: Optional[str]
    amenities_rating: Optional[float]
    amenities_notes: Optional[str]
    water_supply_rating: Optional[float]
    power_supply_rating: Optional[float]
    pros: Optional[List[str]]
    cons: Optional[List[str]]
    review_text: Optional[str]
    is_verified: int
    verification_type: Optional[str]
    helpful_count: int
    status: str
    created_at: str
    updated_at: str


class LocalityReviewStatsResponse(BaseModel):
    """Response for locality review statistics."""
    total_reviews: int
    avg_overall_rating: Optional[float]
    avg_vastu_rating: Optional[float]
    avg_school_rating: Optional[float]
    avg_transport_rating: Optional[float]
    avg_safety_rating: Optional[float]
    avg_amenities_rating: Optional[float]
    avg_water_supply_rating: Optional[float]
    avg_power_supply_rating: Optional[float]
    verified_count: int
    total_helpful: int
    rating_distribution: Dict[str, int]


class HelpfulResponse(BaseModel):
    """Response for helpful mark."""
    id: str
    review_id: str
    review_type: str
    user_id: str
    created_at: str


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


# ============================================================================
# LOCALITY REVIEW ENDPOINTS
# ============================================================================

@router.post("/locality", response_model=LocalityReviewResponse, status_code=201)
async def create_locality_review_endpoint(
    request: CreateLocalityReviewRequest,
    user: User = Depends(require_auth)
):
    """
    Submit a locality review.
    
    Awards +10 credits for verified reviews.
    """
    db = get_db()
    
    review_id = create_locality_review(
        db=db,
        locality_id=request.locality_id,
        locality_name=request.locality_name,
        user_id=user.id,
        overall_rating=request.overall_rating,
        vastu_rating=request.vastu_rating,
        vastu_notes=request.vastu_notes,
        school_rating=request.school_rating,
        school_notes=request.school_notes,
        religious_proximity=request.religious_proximity,
        transport_rating=request.transport_rating,
        transport_notes=request.transport_notes,
        safety_rating=request.safety_rating,
        safety_notes=request.safety_notes,
        amenities_rating=request.amenities_rating,
        amenities_notes=request.amenities_notes,
        water_supply_rating=request.water_supply_rating,
        power_supply_rating=request.power_supply_rating,
        pros=request.pros,
        cons=request.cons,
        review_text=request.review_text,
        verification_type=request.verification_type.value if request.verification_type else None
    )
    
    if not review_id:
        raise HTTPException(status_code=500, detail="Failed to create locality review")
    
    # Award credits for verified reviews (+10 credits)
    if request.verification_type in [VerificationType.RESIDENT, VerificationType.OWNER]:
        await award_credits(user.id, 10, f"verified locality review for {request.locality_name}")
    
    # Get the created review
    reviews = get_locality_reviews(db, request.locality_id, limit=1, offset=0)
    if reviews:
        return reviews[0]
    
    raise HTTPException(status_code=500, detail="Failed to retrieve created review")


@router.get("/locality/{locality_id}", response_model=List[LocalityReviewResponse])
async def get_locality_reviews_endpoint(
    locality_id: str = Path(..., description="Locality ID"),
    status: str = Query("active", description="Status filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sort_by: SortBy = Query(SortBy.CREATED_AT, description="Sort field")
):
    """Get reviews for a locality."""
    db = get_db()
    
    reviews = get_locality_reviews(
        db=db,
        locality_id=locality_id,
        status=status,
        limit=limit,
        offset=offset,
        sort_by=sort_by.value
    )
    
    return reviews


@router.get("/locality/{locality_id}/stats", response_model=LocalityReviewStatsResponse)
async def get_locality_review_stats_endpoint(
    locality_id: str = Path(..., description="Locality ID")
):
    """Get review statistics for a locality."""
    db = get_db()
    
    stats = get_locality_review_stats(db, locality_id)
    
    if not stats:
        # Return empty stats if no reviews
        return LocalityReviewStatsResponse(
            total_reviews=0,
            avg_overall_rating=None,
            avg_vastu_rating=None,
            avg_school_rating=None,
            avg_transport_rating=None,
            avg_safety_rating=None,
            avg_amenities_rating=None,
            avg_water_supply_rating=None,
            avg_power_supply_rating=None,
            verified_count=0,
            total_helpful=0,
            rating_distribution={}
        )
    
    return stats


@router.put("/locality/{review_id}", response_model=SuccessResponse)
async def update_locality_review_endpoint(
    request: UpdateLocalityReviewRequest,
    review_id: str = Path(..., description="Review ID"),
    user: User = Depends(require_auth)
):
    """Update a locality review (only by the original author)."""
    db = get_db()
    
    # Build kwargs from request
    kwargs = {k: v for k, v in request.dict().items() if v is not None}
    
    success = update_locality_review(
        db=db,
        review_id=review_id,
        user_id=user.id,
        **kwargs
    )
    
    if not success:
        raise HTTPException(status_code=403, detail="Review not found or unauthorized")
    
    return SuccessResponse(success=True, message="Review updated successfully")


@router.delete("/locality/{review_id}", response_model=SuccessResponse)
async def delete_locality_review_endpoint(
    review_id: str = Path(..., description="Review ID"),
    user: User = Depends(require_auth)
):
    """Delete a locality review (only by the original author)."""
    db = get_db()
    
    success = delete_locality_review(
        db=db,
        review_id=review_id,
        user_id=user.id
    )
    
    if not success:
        raise HTTPException(status_code=403, detail="Review not found or unauthorized")
    
    return SuccessResponse(success=True, message="Review deleted successfully")


# ============================================================================
# HELPFUL SYSTEM ENDPOINTS
# ============================================================================

@router.post("/{review_type}/{review_id}/helpful", response_model=SuccessResponse)
async def mark_review_helpful_endpoint(
    review_type: ReviewType = Path(..., description="Type of review (locality)"),
    review_id: str = Path(..., description="Review ID"),
    user: User = Depends(require_auth)
):
    """Mark a locality review as helpful."""
    db = get_db()
    
    helpful_id = mark_review_helpful(
        db=db,
        review_id=review_id,
        review_type=review_type.value,
        user_id=user.id
    )
    
    if not helpful_id:
        raise HTTPException(status_code=500, detail="Failed to mark review as helpful")
    
    return SuccessResponse(success=True, message="Review marked as helpful")


@router.delete("/{review_type}/{review_id}/helpful", response_model=SuccessResponse)
async def unmark_review_helpful_endpoint(
    review_type: ReviewType = Path(..., description="Type of review (locality)"),
    review_id: str = Path(..., description="Review ID"),
    user: User = Depends(require_auth)
):
    """Remove helpful mark from a review."""
    db = get_db()
    
    success = unmark_review_helpful(
        db=db,
        review_id=review_id,
        review_type=review_type.value,
        user_id=user.id
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove helpful mark")
    
    return SuccessResponse(success=True, message="Helpful mark removed")


@router.get("/user/helpful", response_model=List[HelpfulResponse])
async def get_user_helpful_reviews_endpoint(
    user: User = Depends(require_auth),
    review_type: ReviewType = Query(None, description="Filter by review type")
):
    """Get all locality reviews marked as helpful by the user."""
    db = get_db()
    
    helpful_reviews = get_user_helpful_reviews(
        db=db,
        user_id=user.id,
        review_type=review_type.value if review_type else None
    )
    
    return helpful_reviews


# ============================================================================
# LOCALITY REVIEWS - FOCUSED VERSION
# ============================================================================
# This file exports only locality review functionality.
# Builder profiles/reviews and RERA verification have been removed
# as they are not aligned with Valora's product thesis.
