"""
Apify Google Maps Integration for Bangalore Location Data
Fetches real location data to enhance property predictions
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from apify_client import ApifyClient
from dotenv import load_dotenv
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

# Ensure environment variables from .env are loaded for APIFY token
try:
    load_dotenv()
except Exception:
    pass

class ApifyGoogleMapsService:
    """
    Service to fetch Google Maps data for Bangalore locations
    Used to enhance property predictions with real location intelligence
    """
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("APIFY_API_TOKEN") or os.getenv("APIFY_API_KEY")
        
        if not self.api_token:
            logger.warning("APIFY_API_TOKEN not set - Google Maps data enrichment disabled")
            self.client = None
        else:
            self.client = ApifyClient(self.api_token)
            logger.info("Apify Google Maps service initialized")
        
        self.data_dir = Path("data/location_intelligence")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Bangalore key locations for real estate
        self.bangalore_locations = [
            # Prime Residential Areas
            {"name": "Koramangala", "category": "residential", "type": "neighborhood"},
            {"name": "Indiranagar", "category": "residential", "type": "neighborhood"},
            {"name": "Whitefield", "category": "residential", "type": "neighborhood"},
            {"name": "HSR Layout", "category": "residential", "type": "neighborhood"},
            {"name": "Jayanagar", "category": "residential", "type": "neighborhood"},
            {"name": "BTM Layout", "category": "residential", "type": "neighborhood"},
            {"name": "Electronic City", "category": "tech_hub", "type": "neighborhood"},
            {"name": "Marathahalli", "category": "residential", "type": "neighborhood"},
            {"name": "Sarjapur Road", "category": "residential", "type": "neighborhood"},
            {"name": "Bannerghatta Road", "category": "residential", "type": "neighborhood"},
            
            # Commercial Hubs
            {"name": "MG Road Bangalore", "category": "commercial", "type": "business_district"},
            {"name": "Brigade Road Bangalore", "category": "commercial", "type": "shopping"},
            {"name": "Commercial Street Bangalore", "category": "commercial", "type": "shopping"},
            {"name": "Outer Ring Road Bangalore", "category": "tech_corridor", "type": "business"},
            
            # Educational Institutions (affects property values)
            {"name": "Indian Institute of Science Bangalore", "category": "education", "type": "university"},
            {"name": "IIM Bangalore", "category": "education", "type": "university"},
            
            # Healthcare (important for residential value)
            {"name": "Apollo Hospital Bangalore", "category": "healthcare", "type": "hospital"},
            {"name": "Fortis Hospital Bangalore", "category": "healthcare", "type": "hospital"},
            
            # Malls and Entertainment
            {"name": "Forum Mall Koramangala", "category": "shopping", "type": "mall"},
            {"name": "Phoenix Marketcity Bangalore", "category": "shopping", "type": "mall"},
            {"name": "UB City Mall Bangalore", "category": "shopping", "type": "mall"}
        ]
    
    async def fetch_location_data(self, location: str, search_type: str = "general") -> Dict[str, Any]:
        """Fetch Google Maps data for a specific location"""
        if not self.client:
            logger.warning("Apify client not initialized")
            return {}
        
        try:
            # Prepare multiple candidate inputs to support different actors
            loc_query = f"{location} Bangalore India"
            input_candidates = [
                {
                    # apify/google-maps-scraper
                    "searchStringsArray": [loc_query],
                    "maxCrawledPlacesPerSearch": 20,
                    "maxReviews": 20,
                    "language": "en",
                    "countryCode": "IN",
                    "includeReviews": True,
                    "includeImages": False,
                    "exportPlaceUrls": False,
                },
                {
                    # Some actors accept 'queries'
                    "queries": [loc_query],
                    "maxResults": 20,
                    "language": "en",
                    "includeReviews": True,
                },
                {
                    # Generic 'search' or 'keyword'
                    "search": loc_query,
                    "maxResults": 20,
                    "language": "en",
                },
                {
                    "keyword": loc_query,
                    "maxResults": 20,
                },
            ]
            
            # Run the Actor/Task and wait for it to finish
            logger.info(f"Fetching Google Maps data for: {location}")

            # Prefer a pre-created TASK from user's account if provided
            task_id = os.getenv("APIFY_GMAPS_TASK_ID")
            run = None
            last_err = None
            if task_id:
                try:
                    logger.info(f"Running Apify task: {task_id}")
                    # Try candidate inputs until one works
                    for inp in input_candidates:
                        try:
                            run = self.client.task(task_id).call(run_input=inp)
                            break
                        except Exception as e:
                            last_err = e
                            continue
                except Exception as e:
                    logger.warning(f"Failed running task '{task_id}': {e}")
                    last_err = e

            # If no task or task failed, try known public actors
            if run is None:
                actor_candidates = [
                    os.getenv("APIFY_GMAPS_ACTOR"),
                    "compass/google-maps-extractor",
                    "apify/google-maps-scraper",
                    "apify~google-maps-scraper",
                    "dtrungtin/google-maps-scraper",
                    "compass/google-maps-scraper",
                ]
                for aid in [a for a in actor_candidates if a]:
                    for inp in input_candidates:
                        try:
                            run = self.client.actor(aid).call(run_input=inp)
                            logger.info(f"Apify actor started: {aid}")
                            break
                        except Exception as e:
                            logger.warning(f"Failed with actor '{aid}' using input keys {list(inp.keys())}: {e}")
                            last_err = e
                            run = None
                            continue
                    if run is not None:
                        break
            if run is None:
                raise RuntimeError(f"All actor/task attempts failed: {last_err}")
            
            # Fetch results
            items = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                items.append(item)
            
            # Process and structure the data
            location_data = self._process_maps_data(items, location)
            
            # Save to file
            self._save_location_data(location_data, location)
            
            return location_data
            
        except Exception as e:
            logger.error(f"Error fetching Google Maps data: {e}")
            return {"error": str(e)}
    
    def _process_maps_data(self, items: List[Dict], location: str) -> Dict[str, Any]:
        """Process raw Google Maps data into structured format"""
        
        if not items:
            return {"location": location, "data_available": False}
        
        # Aggregate location intelligence
        location_intel = {
            "location": location,
            "timestamp": datetime.now().isoformat(),
            "data_available": True,
            "places_count": len(items),
            "categories": {},
            "amenities": {
                "restaurants": [],
                "schools": [],
                "hospitals": [],
                "shopping": [],
                "parks": [],
                "transport": []
            },
            "ratings": {
                "average_rating": 0,
                "total_reviews": 0
            },
            "popular_times": {},
            "accessibility": {},
            "nearby_landmarks": []
        }
        
        total_rating = 0
        rating_count = 0
        
        for item in items:
            # Categorize the place
            category = self._categorize_place(item)
            if category not in location_intel["categories"]:
                location_intel["categories"][category] = 0
            location_intel["categories"][category] += 1
            
            # Extract amenities
            place_info = {
                "name": item.get("title", ""),
                "address": item.get("address", ""),
                "rating": item.get("rating", 0),
                "reviews": item.get("reviewsCount", 0),
                "category": category,
                "phone": item.get("phone"),
                "website": item.get("website"),
                "coordinates": {
                    "lat": item.get("latitude"),
                    "lng": item.get("longitude")
                }
            }
            
            # Add to appropriate amenity list
            if category in location_intel["amenities"]:
                location_intel["amenities"][category].append(place_info)
            
            # Update ratings
            if item.get("rating"):
                total_rating += item.get("rating", 0)
                rating_count += 1
            
            location_intel["ratings"]["total_reviews"] += item.get("reviewsCount", 0)
            
            # Extract popular times if available
            if item.get("popularTimes"):
                location_intel["popular_times"] = item.get("popularTimes")
            
            # Check accessibility
            if item.get("accessibilityInfo"):
                location_intel["accessibility"] = item.get("accessibilityInfo")
        
        # Calculate average rating
        if rating_count > 0:
            location_intel["ratings"]["average_rating"] = total_rating / rating_count
        
        # Generate location score for real estate
        location_intel["real_estate_score"] = self._calculate_location_score(location_intel)
        
        return location_intel
    
    def _categorize_place(self, place: Dict) -> str:
        """Categorize a place based on its type"""
        title = place.get("title", "").lower()
        category_text = place.get("categoryName", "").lower()
        
        # Restaurant/Food
        if any(word in title + category_text for word in ["restaurant", "cafe", "food", "dining", "eat"]):
            return "restaurants"
        
        # Education
        elif any(word in title + category_text for word in ["school", "college", "university", "education", "institute"]):
            return "schools"
        
        # Healthcare
        elif any(word in title + category_text for word in ["hospital", "clinic", "medical", "doctor", "health"]):
            return "hospitals"
        
        # Shopping
        elif any(word in title + category_text for word in ["mall", "shop", "store", "market", "shopping"]):
            return "shopping"
        
        # Parks/Recreation
        elif any(word in title + category_text for word in ["park", "garden", "recreation", "sports", "gym"]):
            return "parks"
        
        # Transport
        elif any(word in title + category_text for word in ["metro", "bus", "station", "airport", "transport"]):
            return "transport"
        
        else:
            return "other"
    
    def _calculate_location_score(self, location_data: Dict) -> float:
        """Calculate a real estate score based on location amenities"""
        score = 50  # Base score
        
        # Amenity scoring
        amenities = location_data.get("amenities", {})
        
        # Schools (very important for families)
        schools_count = len(amenities.get("schools", []))
        score += min(schools_count * 3, 15)  # Max 15 points
        
        # Hospitals (healthcare access)
        hospitals_count = len(amenities.get("hospitals", []))
        score += min(hospitals_count * 4, 12)  # Max 12 points
        
        # Shopping (lifestyle)
        shopping_count = len(amenities.get("shopping", []))
        score += min(shopping_count * 2, 10)  # Max 10 points
        
        # Restaurants (social life)
        restaurants_count = len(amenities.get("restaurants", []))
        score += min(restaurants_count * 1, 8)  # Max 8 points
        
        # Transport (connectivity)
        transport_count = len(amenities.get("transport", []))
        score += min(transport_count * 5, 15)  # Max 15 points
        
        # Parks (green spaces)
        parks_count = len(amenities.get("parks", []))
        score += min(parks_count * 2, 6)  # Max 6 points
        
        # Rating bonus
        avg_rating = location_data.get("ratings", {}).get("average_rating", 0)
        if avg_rating > 4.0:
            score += 5
        elif avg_rating > 3.5:
            score += 3
        
        return min(100, score)  # Cap at 100
    
    def _save_location_data(self, data: Dict, location: str):
        """Save location data to file"""
        filename = f"{location.replace(' ', '_').lower()}_google_maps_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = self.data_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved location data to: {filepath}")
    
    async def fetch_all_bangalore_locations(self) -> Dict[str, Any]:
        """Fetch Google Maps data for all key Bangalore locations"""
        if not self.client:
            logger.warning("Apify client not initialized")
            return {"error": "Apify not configured"}
        
        logger.info(f"Starting to fetch data for {len(self.bangalore_locations)} Bangalore locations")
        
        all_location_data = []
        success_count = 0
        error_count = 0
        
        # Process locations in batches to respect API limits
        batch_size = 5
        for i in range(0, len(self.bangalore_locations), batch_size):
            batch = self.bangalore_locations[i:i + batch_size]
            
            for location in batch:
                try:
                    logger.info(f"Fetching data for: {location['name']}")
                    location_data = await self.fetch_location_data(
                        location['name'], 
                        location.get('type', 'general')
                    )
                    
                    if not location_data.get("error"):
                        location_data["category"] = location["category"]
                        location_data["type"] = location["type"]
                        all_location_data.append(location_data)
                        success_count += 1
                    else:
                        error_count += 1
                    
                    # Small delay between requests
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing {location['name']}: {e}")
                    error_count += 1
            
            # Longer delay between batches
            if i + batch_size < len(self.bangalore_locations):
                logger.info(f"Completed batch {i//batch_size + 1}, waiting before next batch...")
                await asyncio.sleep(10)
        
        # Save aggregate data
        aggregate_file = self.data_dir / f"bangalore_aggregate_{datetime.now().strftime('%Y%m%d')}.json"
        aggregate_data = {
            "city": "Bangalore",
            "timestamp": datetime.now().isoformat(),
            "locations_processed": success_count,
            "errors": error_count,
            "location_data": all_location_data,
            "summary": self._generate_city_summary(all_location_data)
        }
        
        with open(aggregate_file, 'w') as f:
            json.dump(aggregate_data, f, indent=2)
        
        logger.info(f"Fetched data for {success_count} locations, {error_count} errors")
        logger.info(f"Aggregate data saved to: {aggregate_file}")
        
        return aggregate_data
    
    def _generate_city_summary(self, location_data: List[Dict]) -> Dict[str, Any]:
        """Generate summary statistics for the city"""
        summary = {
            "total_locations": len(location_data),
            "average_location_score": 0,
            "best_locations": [],
            "amenity_distribution": {},
            "category_distribution": {}
        }
        
        if not location_data:
            return summary
        
        # Calculate averages and distributions
        total_score = 0
        all_amenities = {}
        
        for location in location_data:
            # Location scores
            score = location.get("real_estate_score", 0)
            total_score += score
            
            if score > 80:
                summary["best_locations"].append({
                    "name": location.get("location"),
                    "score": score,
                    "category": location.get("category")
                })
            
            # Amenity counts
            amenities = location.get("amenities", {})
            for amenity_type, items in amenities.items():
                if amenity_type not in all_amenities:
                    all_amenities[amenity_type] = 0
                all_amenities[amenity_type] += len(items)
            
            # Category distribution
            category = location.get("category", "other")
            if category not in summary["category_distribution"]:
                summary["category_distribution"][category] = 0
            summary["category_distribution"][category] += 1
        
        summary["average_location_score"] = total_score / len(location_data)
        summary["amenity_distribution"] = all_amenities
        
        # Sort best locations by score
        summary["best_locations"].sort(key=lambda x: x["score"], reverse=True)
        summary["best_locations"] = summary["best_locations"][:10]  # Top 10
        
        return summary
    
    def load_cached_data(self, location: Optional[str] = None) -> Dict[str, Any]:
        """Load cached Google Maps data"""
        if location:
            # Load specific location data
            pattern = f"{location.replace(' ', '_').lower()}_google_maps_*.json"
            files = list(self.data_dir.glob(pattern))
            
            if files:
                # Get most recent file
                latest_file = max(files, key=lambda f: f.stat().st_mtime)
                with open(latest_file) as f:
                    return json.load(f)
        else:
            # Load aggregate Bangalore data
            pattern = "bangalore_aggregate_*.json"
            files = list(self.data_dir.glob(pattern))
            
            if files:
                latest_file = max(files, key=lambda f: f.stat().st_mtime)
                with open(latest_file) as f:
                    return json.load(f)
        
        return {}
    
    def enrich_property_with_location_intel(self, property_data: Dict, location_data: Dict) -> Dict:
        """Enrich property data with Google Maps location intelligence"""
        
        if not location_data.get("data_available"):
            return property_data
        
        # Add location intelligence
        property_data["location_intelligence"] = {
            "location_score": location_data.get("real_estate_score", 0),
            "nearby_schools": len(location_data.get("amenities", {}).get("schools", [])),
            "nearby_hospitals": len(location_data.get("amenities", {}).get("hospitals", [])),
            "nearby_shopping": len(location_data.get("amenities", {}).get("shopping", [])),
            "transport_connectivity": len(location_data.get("amenities", {}).get("transport", [])),
            "lifestyle_amenities": len(location_data.get("amenities", {}).get("restaurants", [])),
            "green_spaces": len(location_data.get("amenities", {}).get("parks", [])),
            "area_rating": location_data.get("ratings", {}).get("average_rating", 0),
            "total_reviews": location_data.get("ratings", {}).get("total_reviews", 0)
        }
        
        # Adjust property valuation based on location score
        location_multiplier = 1 + (location_data.get("real_estate_score", 50) - 50) / 100
        property_data["location_adjusted_price"] = property_data.get("price", 0) * location_multiplier
        
        # Add investment insights
        property_data["location_insights"] = []
        
        if property_data["location_intelligence"]["nearby_schools"] > 5:
            property_data["location_insights"].append("Excellent for families - multiple schools nearby")
        
        if property_data["location_intelligence"]["transport_connectivity"] > 3:
            property_data["location_insights"].append("Great connectivity - multiple transport options")
        
        if property_data["location_intelligence"]["location_score"] > 80:
            property_data["location_insights"].append("Premium location with high appreciation potential")
        
        return property_data
