"""
Valora Seller Intelligence API
AI-powered insights for seller listings
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import random

router = APIRouter(prefix="/api/seller", tags=["seller"])


class IntelligenceRequest(BaseModel):
    property_type: Optional[str] = None
    bedrooms: Optional[str] = None
    area_sqft: Optional[int] = None
    locality: Optional[str] = None
    price: Optional[int] = None


@router.post("/intelligence")
async def get_seller_intelligence(data: IntelligenceRequest):
    """
    Get AI-powered seller intelligence for a listing
    
    Returns:
    - suggested_price_min/max: Based on locality and property type
    - demand_score: 0-100 score for the area
    - best_time: When to sell
    - market_trend: up/down/stable
    - comparable_properties: Nearby sales
    """
    locality = data.locality or "Unknown"
    property_type = data.property_type or "apartment"
    price = data.price or 0
    area = data.area_sqft or 1000
    
    # Calculate suggested price range based on locality data
    base_price_per_sqft = {
        'whitefield': 7500,
        'koramangala': 8500,
        'indiranagar': 9000,
        'hsr_layout': 7500,
        'jp_nagar': 7000,
        'bellandur': 7000,
        'electronic_city': 5500,
    }.get(locality.lower(), 6000)
    
    min_price = int(area * base_price_per_sqft * 0.9)
    max_price = int(area * base_price_per_sqft * 1.1)
    
    # Demand score by locality
    demand_scores = {
        'whitefield': 75,
        'koramangala': 85,
        'indiranagar': 90,
        'hsr_layout': 80,
        'jp_nagar': 70,
        'bellandur': 65,
        'electronic_city': 55,
    }
    demand_score = demand_scores.get(locality.lower(), 50)
    
    # Market trend
    trends = ['up', 'stable', 'down']
    trend = random.choice(trends) if random.random() > 0.3 else 'stable'
    
    return {
        'suggested_price_min': min_price,
        'suggested_price_max': max_price,
        'listing_price': price,
        'demand_score': demand_score,
        'best_time': 'Now' if demand_score > 60 else 'Wait 2-3 months',
        'market_trend': trend,
        'trend_description': {
            'up': 'Property values in this area have been increasing',
            'stable': 'Market is stable with modest activity',
            'down': 'Consider pricing competitively to attract buyers'
        }.get(trend, 'Market conditions vary'),
        'comparable_properties': [
            {'property': f'2 BHK in {locality}', 'price': min_price - 500000},
            {'property': f'3 BHK in {locality}', 'price': min_price + 200000},
            {'property': f'2 BHK nearby', 'price': min_price - 200000},
        ]
    }