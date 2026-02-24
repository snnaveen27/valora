"""
Valora AI - Review Routes (Community Pulse Phase 2)
Locality and Builder Reviews API.

Endpoints:
  Locality Reviews:
    POST   /api/reviews/locality                    - Submit locality review
    GET    /api/reviews/locality/{locality_id}      - Get reviews for locality
    GET    /api/reviews/locality/{locality_id}/stats - Get review statistics
    PUT    /api/reviews/locality/{review_id}        - Update review
    DELETE /api/reviews/locality/{review_id}        - Delete review

  Builder Profiles:
    POST   /api/reviews/builder                     - Create builder profile (admin)
    GET    /api/reviews/builder/{builder_id}        - Get builder profile
    GET    /api/reviews/builders                    - Search builders
    PUT    /api/reviews/builder/{builder_id}         - Update builder profile (admin)

  Builder Reviews:
    POST   /api/reviews/builder/{builder_id}/review - Submit builder review
    GET    /api/reviews/builder/{builder_id}/reviews - Get builder reviews
    PUT    /api/reviews/builder/review/{review_id}   - Update review
    DELETE /api/reviews/builder/review/{review_id}   - Delete review

  Helpful System:
    POST   /api/reviews/{review_type}/{review_id}/helpful - Mark helpful
    DELETE /api/reviews/{review_type}/{review_id}/helpful - Remove helpful
    GET    /api/reviews/user/helpful                  - Get user's helpful reviews

  RERA Verification:
    GET    /api/rera/verify/{rera_id}               - Verify RERA ID
    POST   /api/rera/refresh/{rera_id}              - Force refresh RERA data
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field, validator
from enum import Enum

from auth.user_auth import User
from routes.auth_routes import require_auth, require_admin
from database.community_pulse_schema import (
    CommunityPulseDB,
    get_community_pulse_db,
    init_phase2_tables,
    create_locality_review,
    get_locality_reviews,
    get_locality_review_stats,
    update_locality_review,
    delete_locality_review,
    create_builder_profile,
    get_builder_profile,
    search_builders,
    update_builder_profile,
    update_builder_aggregates,
    create_builder_review,
    get_builder_reviews,
    update_builder_review,
    delete_builder_review,
    mark_review_helpful,
    unmark_review_helpful,
    get_user_helpful_reviews,
    create_rera_verification,
    get_rera_verification,
    update_rera_verification,
)

logger = logging.getLogger("valora.review_routes")

router = APIRouter(prefix="/api/reviews", tags=["Reviews (Community Pulse)"])
rera_router = APIRouter(prefix="/api/rera", tags=["RERA Verification"])


# ============================================================================
# ENUMS
# ============================================================================

class ReviewType(str, Enum):
    LOCALITY = "locality"
    BUILDER = "builder"


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
# REQUEST MODELS - BUILDER PROFILES
# ============================================================================

class CreateBuilderProfileRequest(BaseModel):
    """Request to create a builder profile."""
    name: str = Field(..., min_length=1, max_length=200, description="Builder name")
    description: Optional[str] = Field(None, max_length=1000, description="Builder description")
    logo_url: Optional[str] = Field(None, description="URL to builder logo")
    website: Optional[str] = Field(None, description="Builder website")
    established_year: Optional[int] = Field(None, ge=1900, le=2030, description="Year established")
    cities_operating: Optional[List[str]] = Field(None, description="List of cities")
    rera_registered: bool = Field(False, description="RERA registration status")
    rera_ids: Optional[List[str]] = Field(None, description="RERA registration IDs")
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    contact_email: Optional[str] = Field(None, description="Contact email")
    address: Optional[str] = Field(None, max_length=500, description="Office address")


class UpdateBuilderProfileRequest(BaseModel):
    """Request to update a builder profile."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    logo_url: Optional[str] = None
    website: Optional[str] = None
    established_year: Optional[int] = Field(None, ge=1900, le=2030)
    cities_operating: Optional[List[str]] = None
    rera_registered: Optional[bool] = None
    rera_ids: Optional[List[str]] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = Field(None, max_length=500)


# ============================================================================
# REQUEST MODELS - BUILDER REVIEWS
# ============================================================================

class CreateBuilderReviewRequest(BaseModel):
    """Request to create a builder review."""
    overall_rating: float = Field(..., ge=1, le=5, description="Overall rating (1-5)")
    project_name: Optional[str] = Field(None, max_length=200, description="Project name")
    project_location: Optional[str] = Field(None, max_length=200, description="Project location")
    construction_quality: Optional[float] = Field(None, ge=1, le=5, description="Construction quality rating")
    timely_delivery: Optional[float] = Field(None, ge=1, le=5, description="Timely delivery rating")
    after_sales_service: Optional[float] = Field(None, ge=1, le=5, description="After-sales service rating")
    value_for_money: Optional[float] = Field(None, ge=1, le=5, description="Value for money rating")
    transparency: Optional[float] = Field(None, ge=1, le=5, description="Transparency rating")
    pros: Optional[List[str]] = Field(None, description="List of pros")
    cons: Optional[List[str]] = Field(None, description="List of cons")
    review_text: Optional[str] = Field(None, max_length=2000, description="Full review text")
    is_verified_buyer: bool = Field(False, description="Verified buyer status")
    purchase_date: Optional[str] = Field(None, description="Date of purchase")


class UpdateBuilderReviewRequest(BaseModel):
    """Request to update a builder review."""
    overall_rating: Optional[float] = Field(None, ge=1, le=5)
    project_name: Optional[str] = Field(None, max_length=200)
    project_location: Optional[str] = Field(None, max_length=200)
    construction_quality: Optional[float] = Field(None, ge=1, le=5)
    timely_delivery: Optional[float] = Field(None, ge=1, le=5)
    after_sales_service: Optional[float] = Field(None, ge=1, le=5)
    value_for_money: Optional[float] = Field(None, ge=1, le=5)
    transparency: Optional[float] = Field(None, ge=1, le=5)
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None
    review_text: Optional[str] = Field(None, max_length=2000)
    is_verified_buyer: Optional[bool] = None
    purchase_date: Optional[str] = None


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


class BuilderProfileResponse(BaseModel):
    """Response for a builder profile."""
    id: str
    name: str
    description: Optional[str]
    logo_url: Optional[str]
    website: Optional[str]
    established_year: Optional[int]
    cities_operating: Optional[List[str]]
    total_projects: int
    completed_projects: int
    ongoing_projects: int
    avg_delivery_time_months: Optional[float]
    on_time_delivery_rate: Optional[float]
    avg_construction_quality_rating: Optional[float]
    avg_after_sales_rating: Optional[float]
    rera_registered: int
    rera_ids: Optional[List[str]]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    address: Optional[str]
    created_at: str
    updated_at: str


class BuilderReviewResponse(BaseModel):
    """Response for a builder review."""
    id: str
    builder_id: str
    user_id: str
    project_name: Optional[str]
    project_location: Optional[str]
    overall_rating: float
    construction_quality: Optional[float]
    timely_delivery: Optional[float]
    after_sales_service: Optional[float]
    value_for_money: Optional[float]
    transparency: Optional[float]
    pros: Optional[List[str]]
    cons: Optional[List[str]]
    review_text: Optional[str]
    is_verified_buyer: int
    purchase_date: Optional[str]
    helpful_count: int
    status: str
    created_at: str
    updated_at: str


class HelpfulResponse(BaseModel):
    """Response for helpful mark."""
    id: str
    review_id: str
    review_type: str
    user_id: str
    created_at: str


class ReraVerificationResponse(BaseModel):
    """Response for RERA verification."""
    id: str
    rera_id: str
    state: str
    project_name: Optional[str]
    builder_name: Optional[str]
    project_status: Optional[str]
    registration_date: Optional[str]
    expiry_date: Optional[str]
    project_address: Optional[str]
    project_type: Optional[str]
    land_area: Optional[float]
    proposed_units: Optional[int]
    verification_status: str
    verification_data: Optional[Dict[str, Any]]
    last_verified_at: str
    created_at: str
    updated_at: str


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
        user_id=user.user_id,
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
        await award_credits(user.user_id, 10, f"verified locality review for {request.locality_name}")
    
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
        user_id=user.user_id,
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
        user_id=user.user_id
    )
    
    if not success:
        raise HTTPException(status_code=403, detail="Review not found or unauthorized")
    
    return SuccessResponse(success=True, message="Review deleted successfully")


# ============================================================================
# BUILDER PROFILE ENDPOINTS
# ============================================================================

@router.post("/builder", response_model=BuilderProfileResponse, status_code=201)
async def create_builder_profile_endpoint(
    request: CreateBuilderProfileRequest,
    user: User = Depends(require_admin)
):
    """Create a builder profile (admin only)."""
    db = get_db()
    
    builder_id = create_builder_profile(
        db=db,
        name=request.name,
        description=request.description,
        logo_url=request.logo_url,
        website=request.website,
        established_year=request.established_year,
        cities_operating=request.cities_operating,
        rera_registered=request.rera_registered,
        rera_ids=request.rera_ids,
        contact_phone=request.contact_phone,
        contact_email=request.contact_email,
        address=request.address
    )
    
    if not builder_id:
        raise HTTPException(status_code=500, detail="Failed to create builder profile")
    
    # Get the created profile
    profile = get_builder_profile(db, builder_id)
    if not profile:
        raise HTTPException(status_code=500, detail="Failed to retrieve created profile")
    
    return profile


@router.get("/builder/{builder_id}", response_model=BuilderProfileResponse)
async def get_builder_profile_endpoint(
    builder_id: str = Path(..., description="Builder ID")
):
    """Get a builder profile with aggregates."""
    db = get_db()
    
    profile = get_builder_profile(db, builder_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Builder profile not found")
    
    return profile


@router.get("/builders", response_model=List[BuilderProfileResponse])
async def search_builders_endpoint(
    query: str = Query(None, description="Search query for builder name"),
    city: str = Query(None, description="Filter by city"),
    rera_registered: bool = Query(None, description="Filter by RERA registration"),
    min_rating: float = Query(None, ge=1, le=5, description="Minimum rating"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """Search builder profiles."""
    db = get_db()
    
    builders = search_builders(
        db=db,
        query=query,
        city=city,
        rera_registered=rera_registered,
        min_rating=min_rating,
        limit=limit,
        offset=offset
    )
    
    return builders


@router.put("/builder/{builder_id}", response_model=SuccessResponse)
async def update_builder_profile_endpoint(
    request: UpdateBuilderProfileRequest,
    builder_id: str = Path(..., description="Builder ID"),
    user: User = Depends(require_admin)
):
    """Update a builder profile (admin only)."""
    db = get_db()
    
    # Check if builder exists
    profile = get_builder_profile(db, builder_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Builder profile not found")
    
    # Build kwargs from request
    kwargs = {k: v for k, v in request.dict().items() if v is not None}
    
    success = update_builder_profile(
        db=db,
        builder_id=builder_id,
        **kwargs
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update builder profile")
    
    return SuccessResponse(success=True, message="Builder profile updated successfully")


# ============================================================================
# BUILDER REVIEW ENDPOINTS
# ============================================================================

@router.post("/builder/{builder_id}/review", response_model=BuilderReviewResponse, status_code=201)
async def create_builder_review_endpoint(
    request: CreateBuilderReviewRequest,
    builder_id: str = Path(..., description="Builder ID"),
    user: User = Depends(require_auth)
):
    """
    Submit a builder review.
    
    Awards +8 credits for the review.
    """
    db = get_db()
    
    # Check if builder exists
    builder = get_builder_profile(db, builder_id)
    if not builder:
        raise HTTPException(status_code=404, detail="Builder profile not found")
    
    review_id = create_builder_review(
        db=db,
        builder_id=builder_id,
        user_id=user.user_id,
        overall_rating=request.overall_rating,
        project_name=request.project_name,
        project_location=request.project_location,
        construction_quality=request.construction_quality,
        timely_delivery=request.timely_delivery,
        after_sales_service=request.after_sales_service,
        value_for_money=request.value_for_money,
        transparency=request.transparency,
        pros=request.pros,
        cons=request.cons,
        review_text=request.review_text,
        is_verified_buyer=request.is_verified_buyer,
        purchase_date=request.purchase_date
    )
    
    if not review_id:
        raise HTTPException(status_code=500, detail="Failed to create builder review")
    
    # Award credits for the review (+8 credits)
    await award_credits(user.user_id, 8, f"builder review for {builder.get('name', 'Unknown')}")
    
    # Get the created review
    reviews = get_builder_reviews(db, builder_id, limit=1, offset=0)
    if reviews:
        return reviews[0]
    
    raise HTTPException(status_code=500, detail="Failed to retrieve created review")


@router.get("/builder/{builder_id}/reviews", response_model=List[BuilderReviewResponse])
async def get_builder_reviews_endpoint(
    builder_id: str = Path(..., description="Builder ID"),
    status: str = Query("active", description="Status filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sort_by: SortBy = Query(SortBy.CREATED_AT, description="Sort field")
):
    """Get reviews for a builder."""
    db = get_db()
    
    reviews = get_builder_reviews(
        db=db,
        builder_id=builder_id,
        status=status,
        limit=limit,
        offset=offset,
        sort_by=sort_by.value
    )
    
    return reviews


@router.put("/builder/review/{review_id}", response_model=SuccessResponse)
async def update_builder_review_endpoint(
    request: UpdateBuilderReviewRequest,
    review_id: str = Path(..., description="Review ID"),
    user: User = Depends(require_auth)
):
    """Update a builder review (only by the original author)."""
    db = get_db()
    
    # Build kwargs from request
    kwargs = {k: v for k, v in request.dict().items() if v is not None}
    
    success = update_builder_review(
        db=db,
        review_id=review_id,
        user_id=user.user_id,
        **kwargs
    )
    
    if not success:
        raise HTTPException(status_code=403, detail="Review not found or unauthorized")
    
    return SuccessResponse(success=True, message="Review updated successfully")


@router.delete("/builder/review/{review_id}", response_model=SuccessResponse)
async def delete_builder_review_endpoint(
    review_id: str = Path(..., description="Review ID"),
    user: User = Depends(require_auth)
):
    """Delete a builder review (only by the original author)."""
    db = get_db()
    
    success = delete_builder_review(
        db=db,
        review_id=review_id,
        user_id=user.user_id
    )
    
    if not success:
        raise HTTPException(status_code=403, detail="Review not found or unauthorized")
    
    return SuccessResponse(success=True, message="Review deleted successfully")


# ============================================================================
# HELPFUL SYSTEM ENDPOINTS
# ============================================================================

@router.post("/{review_type}/{review_id}/helpful", response_model=SuccessResponse)
async def mark_review_helpful_endpoint(
    review_type: ReviewType = Path(..., description="Type of review (locality or builder)"),
    review_id: str = Path(..., description="Review ID"),
    user: User = Depends(require_auth)
):
    """Mark a review as helpful."""
    db = get_db()
    
    helpful_id = mark_review_helpful(
        db=db,
        review_id=review_id,
        review_type=review_type.value,
        user_id=user.user_id
    )
    
    if not helpful_id:
        raise HTTPException(status_code=500, detail="Failed to mark review as helpful")
    
    return SuccessResponse(success=True, message="Review marked as helpful")


@router.delete("/{review_type}/{review_id}/helpful", response_model=SuccessResponse)
async def unmark_review_helpful_endpoint(
    review_type: ReviewType = Path(..., description="Type of review (locality or builder)"),
    review_id: str = Path(..., description="Review ID"),
    user: User = Depends(require_auth)
):
    """Remove helpful mark from a review."""
    db = get_db()
    
    success = unmark_review_helpful(
        db=db,
        review_id=review_id,
        review_type=review_type.value,
        user_id=user.user_id
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove helpful mark")
    
    return SuccessResponse(success=True, message="Helpful mark removed")


@router.get("/user/helpful", response_model=List[HelpfulResponse])
async def get_user_helpful_reviews_endpoint(
    user: User = Depends(require_auth),
    review_type: ReviewType = Query(None, description="Filter by review type")
):
    """Get all reviews marked as helpful by the user."""
    db = get_db()
    
    helpful_reviews = get_user_helpful_reviews(
        db=db,
        user_id=user.user_id,
        review_type=review_type.value if review_type else None
    )
    
    return helpful_reviews


# ============================================================================
# RERA VERIFICATION ENDPOINTS
# ============================================================================

@rera_router.get("/verify/{rera_id}", response_model=Optional[ReraVerificationResponse])
async def verify_rera_endpoint(
    rera_id: str = Path(..., description="RERA ID to verify")
):
    """Verify a RERA ID (check cache or fetch)."""
    db = get_db()
    
    verification = get_rera_verification(db, rera_id=rera_id)
    
    if not verification:
        raise HTTPException(status_code=404, detail="RERA ID not found in cache")
    
    return verification


@rera_router.post("/refresh/{rera_id}", response_model=SuccessResponse)
async def refresh_rera_endpoint(
    rera_id: str = Path(..., description="RERA ID to refresh"),
    user: User = Depends(require_admin)
):
    """
    Force refresh RERA data.
    
    This endpoint would typically call an external RERA API to fetch fresh data.
    For now, it just updates the last_verified_at timestamp.
    """
    db = get_db()
    
    # Check if RERA exists
    verification = get_rera_verification(db, rera_id=rera_id)
    
    if not verification:
        raise HTTPException(status_code=404, detail="RERA ID not found")
    
    # Update the verification timestamp
    success = update_rera_verification(
        db=db,
        verification_id=verification['id'],
        last_verified_at=datetime.now().isoformat()
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to refresh RERA data")
    
    return SuccessResponse(success=True, message="RERA data refreshed successfully")
