"""
Valora Listings API Routes
User property listings endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
import json

from database.listings_schema import ListingsDB, create_listing, get_listings, update_listing, delete_listing, get_listing_by_id
from auth.jwt_handler import get_current_user_dependency

router = APIRouter(prefix="/api/listings", tags=["listings"])

db = ListingsDB()


# Models
class ListingCreate(BaseModel):
    user_id: str
    property_type: Optional[str] = None
    bedrooms: Optional[str] = None
    area_sqft: Optional[int] = None
    price: Optional[int] = None
    locality: Optional[str] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None


class ListingUpdate(BaseModel):
    property_type: Optional[str] = None
    bedrooms: Optional[str] = None
    area_sqft: Optional[int] = None
    price: Optional[int] = None
    locality: Optional[str] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    status: Optional[str] = None


# Routes
@router.post("")
async def create_listing_endpoint(data: ListingCreate):
    """Create a new listing"""
    listing = create_listing(db, data.dict())
    return listing


@router.get("")
async def get_user_listings(user_id: str):
    """Get all listings for a user"""
    return get_listings(db, user_id)


@router.get("/{listing_id}")
async def get_listing(listing_id: str):
    """Get a single listing"""
    listing = get_listing_by_id(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.put("/{listing_id}")
async def update_listing_endpoint(listing_id: str, data: ListingUpdate):
    """Update a listing"""
    listing = update_listing(db, listing_id, data.dict(exclude_none=True))
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.delete("/{listing_id}")
async def delete_listing_endpoint(listing_id: str):
    """Delete a listing"""
    success = delete_listing(db, listing_id)
    if not success:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"success": True}