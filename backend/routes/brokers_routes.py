"""
Valora Broker Matching API
Match sellers with relevant brokers
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import random

router = APIRouter(prefix="/api/brokers", tags=["brokers"])


class BrokerMatchRequest(BaseModel):
    property_type: Optional[str] = None
    locality: Optional[str] = None
    price_range: Optional[int] = None


@router.post("/match")
async def match_brokers(data: BrokerMatchRequest):
    """
    Find brokers matching the property criteria
    Returns top 3 brokers with locality expertise
    """
    locality = data.locality or "Unknown"
    
    # Mock broker data - in production, query broker database
    brokers = [
        {
            'id': 'broker_1',
            'name': 'Raj Properties',
            'locality': locality,
            'deals_count': random.randint(10, 50),
            'rating': round(random.uniform(4.0, 5.0), 1),
            'match_score': random.randint(75, 95),
            'phone': '+91 98765 43210'
        },
        {
            'id': 'broker_2',
            'name': 'Bangalore Realty',
            'locality': locality,
            'deals_count': random.randint(15, 40),
            'rating': round(random.uniform(4.2, 4.8), 1),
            'match_score': random.randint(70, 90),
            'phone': '+91 98765 43211'
        },
        {
            'id': 'broker_3',
            'name': 'City Homes',
            'locality': locality,
            'deals_count': random.randint(8, 30),
            'rating': round(random.uniform(4.0, 4.7), 1),
            'match_score': random.randint(65, 85),
            'phone': '+91 98765 43212'
        }
    ]
    
    # Sort by match score
    brokers.sort(key=lambda x: x['match_score'], reverse=True)
    
    return {'brokers': brokers[:3]}


@router.post("/{broker_id}/connect")
async def connect_broker(broker_id: str, data: dict = None):
    """
    Connect with a broker for a listing
    """
    return {
        'success': True,
        'message': f'Connection request sent to broker {broker_id}',
        'broker_id': broker_id
    }


@router.post("/share-listing")
async def share_listing_with_brokers(data: dict):
    """
    Share listing with multiple brokers
    """
    broker_ids = data.get('broker_ids', [])
    listing_id = data.get('listing_id')
    
    return {
        'success': True,
        'message': f'Listing shared with {len(broker_ids)} brokers',
        'listing_id': listing_id
    }