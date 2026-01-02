"""
External API Integration Service
Integrates OpenRouter (LLM), Mappls (Maps), HuggingFace (ML), and Pinecone (Vector DB)
"""

import os
import json
import requests
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np
import logging
import random

# Optional Pinecone import
try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Pinecone not available - vector search features will be disabled")

logger = logging.getLogger(__name__)


class ExternalAPIService:
    """Manages all external API integrations"""
    
    def __init__(self):
        """Initialize with API keys from environment"""
        # API Keys from environment
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.mappls_key = os.getenv("MAPPLS_API_KEY", "")
        self.huggingface_key = os.getenv("HUGGINGFACE_API_KEY", "")
        self.pinecone_key = os.getenv("PINECONE_API_KEY", "")
        
        # API Endpoints
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.mappls_base_url = "https://apis.mappls.com/advancedmaps/v1"
        self.huggingface_url = "https://api-inference.huggingface.co/models"
        
        # Initialize Pinecone if available and key exists
        self.pinecone_index = None
        if PINECONE_AVAILABLE and self.pinecone_key:
            try:
                pc = Pinecone(api_key=self.pinecone_key)
                self.pinecone_index = pc.Index("realty-gpt-vectors")
                logger.info("Pinecone initialized successfully")
            except Exception as e:
                logger.warning(f"Pinecone initialization failed: {e}")
        elif not PINECONE_AVAILABLE:
            logger.info("Pinecone library not installed - vector search disabled")
    
    async def query_llm(self, prompt: str, context: str = "", model: str = "openai/gpt-3.5-turbo") -> str:
        """Query LLM via OpenRouter for intelligent responses"""
        if not self.openrouter_key:
            # Fallback to simple response
            return self._generate_fallback_response(prompt)
        
        try:
            headers = {
                "Authorization": f"Bearer {self.openrouter_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a real estate investment expert analyzing Indian markets."},
                    {"role": "user", "content": f"Context: {context}\n\nQuery: {prompt}"}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            response = requests.post(self.openrouter_url, json=data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.warning(f"OpenRouter API error: {response.status_code}")
                return self._generate_fallback_response(prompt)
                
        except Exception as e:
            logger.error(f"LLM query failed: {e}")
            return self._generate_fallback_response(prompt)

    async def simple_chat(self, prompt: str, system: str = "You are Valora, a friendly and helpful AI assistant. Be warm, conversational, and engaging.", model: str = "openai/gpt-3.5-turbo") -> str:
        """Lightweight general chat for non-real-estate queries (e.g., jokes, greetings, casual conversation)."""
        if not self.openrouter_key:
            # Enhanced fallback for common conversations
            pl = prompt.lower()
            if "joke" in pl or "funny" in pl:
                jokes = [
                    "Why did the developer go broke? Because he used up all his cache! 😄",
                    "I told my computer I needed a break, and it said 'No problem — I'll go to sleep.' 💤",
                    "Why do programmers prefer dark mode? Because light attracts bugs! 🐛",
                    "Why don't real estate agents play hide and seek? Because good luck hiding when they can always find the best location! 🏠",
                ]
                return random.choice(jokes)
            if "hello" in pl or "hi " in pl or "hey" in pl:
                return "Hello! I'm Valora, your friendly AI assistant. How can I help you today? 😊"
            if "how are you" in pl or "what's up" in pl or "how's it going" in pl:
                return "I'm doing wonderfully, thank you for asking! I'm here and ready to help. What's on your mind?"
            if "thank" in pl:
                return "You're very welcome! I'm always happy to help. Feel free to ask me anything else! 😊"
            if "who are you" in pl or "what are you" in pl:
                return "I'm Valora, an AI assistant designed to help with real estate queries and friendly conversation. I'm here to make your experience better! What can I do for you?"
            return "I'm here and listening! What would you like to talk about?"

        try:
            headers = {
                "Authorization": f"Bearer {self.openrouter_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 250
            }
            response = requests.post(self.openrouter_url, json=data, headers=headers, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.warning(f"OpenRouter returned status {response.status_code}")
                return "I'm here and ready to chat! What would you like to know?"
        except Exception as e:
            logger.error(f"Simple chat failed: {e}")
            return "I'm here and listening! How can I help you today?"
    
    def get_embedding(self, text: str, model: str = "openai/text-embedding-3-small") -> Optional[list]:
        """Get text embedding via OpenRouter (OpenAI-compatible) or return None if unavailable.
        Caller may provide a deterministic fallback when None is returned.
        """
        if not text:
            return None
        if not self.openrouter_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.openrouter_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "input": text
            }
            resp = requests.post("https://openrouter.ai/api/v1/embeddings", json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # OpenAI-compatible response: { data: [ { embedding: [...] } ] }
                if data and isinstance(data.get("data"), list) and data["data"]:
                    emb = data["data"][0].get("embedding")
                    if isinstance(emb, list):
                        return emb
            logger.warning(f"Embedding API returned status {resp.status_code}")
            return None
        except Exception as e:
            logger.warning(f"Embedding fetch failed: {e}")
            return None
    
    async def get_mappls_data(self, location: str, search_type: str = "locality") -> Dict[str, Any]:
        """Get location data from Mappls API"""
        if not self.mappls_key:
            # Return mock data if no API key
            return self._generate_mock_mappls_data(location)
        
        try:
            # Geocoding endpoint
            geocode_url = f"{self.mappls_base_url}/{self.mappls_key}/geocode"
            params = {"address": location}
            
            response = requests.get(geocode_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("copResults"):
                    result = data["copResults"][0]
                    return {
                        "location": location,
                        "latitude": result.get("latitude"),
                        "longitude": result.get("longitude"),
                        "formatted_address": result.get("formatted_address"),
                        "city": result.get("city"),
                        "state": result.get("state"),
                        "pincode": result.get("pincode"),
                        "place_id": result.get("eLoc")
                    }
            
            return self._generate_mock_mappls_data(location)
            
        except Exception as e:
            logger.error(f"Mappls API failed: {e}")
            return self._generate_mock_mappls_data(location)
    
    async def get_nearby_pois(self, lat: float, lon: float, category: str = "FINATM") -> List[Dict[str, Any]]:
        """Get nearby POIs from Mappls"""
        if not self.mappls_key:
            return self._generate_mock_pois(category)
        
        try:
            # Nearby search endpoint
            nearby_url = f"{self.mappls_base_url}/{self.mappls_key}/nearby"
            params = {
                "keywords": category,
                "refLocation": f"{lat},{lon}",
                "radius": 5000  # 5km radius
            }
            
            response = requests.get(nearby_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                pois = []
                for place in data.get("suggestedLocations", [])[:10]:
                    pois.append({
                        "name": place.get("placeName"),
                        "distance": place.get("distance"),
                        "category": place.get("category"),
                        "address": place.get("placeAddress"),
                        "lat": place.get("latitude"),
                        "lon": place.get("longitude")
                    })
                return pois
            
            return self._generate_mock_pois(category)
            
        except Exception as e:
            logger.error(f"Mappls POI search failed: {e}")
            return self._generate_mock_pois(category)
    
    async def analyze_with_huggingface(self, text: str, task: str = "sentiment-analysis") -> Dict[str, Any]:
        """Analyze text using HuggingFace models"""
        if not self.huggingface_key:
            return {"label": "POSITIVE", "score": 0.85}
        
        try:
            # Select model based on task
            models = {
                "sentiment-analysis": "nlptown/bert-base-multilingual-uncased-sentiment",
                "text-generation": "gpt2",
                "summarization": "facebook/bart-large-cnn",
                "zero-shot": "facebook/bart-large-mnli"
            }
            
            model = models.get(task, "distilbert-base-uncased")
            url = f"{self.huggingface_url}/{model}"
            
            headers = {"Authorization": f"Bearer {self.huggingface_key}"}
            data = {"inputs": text}
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                return response.json()
            
            return {"label": "NEUTRAL", "score": 0.5}
            
        except Exception as e:
            logger.error(f"HuggingFace API failed: {e}")
            return {"label": "NEUTRAL", "score": 0.5}
    
    async def search_similar_properties(self, query_embedding: List[float], 
                                       filters: Dict[str, Any] = None,
                                       top_k: int = 5) -> List[Dict[str, Any]]:
        """Search similar properties using Pinecone vector database"""
        if not self.pinecone_index:
            return self._generate_mock_similar_properties()
        
        try:
            # Prepare filter
            pinecone_filter = {}
            if filters:
                if "city" in filters:
                    pinecone_filter["city"] = filters["city"]
                if "min_price" in filters and "max_price" in filters:
                    pinecone_filter["price"] = {
                        "$gte": filters["min_price"],
                        "$lte": filters["max_price"]
                    }
            
            # Query Pinecone
            results = self.pinecone_index.query(
                vector=query_embedding,
                filter=pinecone_filter if pinecone_filter else None,
                top_k=top_k,
                include_metadata=True
            )
            
            properties = []
            for match in results["matches"]:
                properties.append({
                    "id": match["id"],
                    "score": match["score"],
                    "metadata": match.get("metadata", {})
                })
            
            return properties
            
        except Exception as e:
            logger.error(f"Pinecone search failed: {e}")
            return self._generate_mock_similar_properties()
    
    async def store_property_embedding(self, property_id: str, 
                                      embedding: List[float],
                                      metadata: Dict[str, Any]) -> bool:
        """Store property embedding in Pinecone"""
        if not self.pinecone_index:
            return True  # Mock success
        
        try:
            self.pinecone_index.upsert(
                vectors=[
                    {
                        "id": property_id,
                        "values": embedding,
                        "metadata": metadata
                    }
                ]
            )
            return True
            
        except Exception as e:
            logger.error(f"Pinecone upsert failed: {e}")
            return False
    
    async def generate_property_insights(self, property_data: Dict[str, Any]) -> str:
        """Generate intelligent insights using LLM"""
        prompt = f"""
        Analyze this property for investment potential:
        Location: {property_data.get('location')}
        Price: ₹{property_data.get('price', 0)/100000:.1f}L
        Size: {property_data.get('area_sqft', 0)} sqft
        Type: {property_data.get('property_type')}
        
        Provide investment insights in 3-4 sentences focusing on:
        1. Growth potential
        2. Rental yield expectations
        3. Key investment factors
        """
        
        return await self.query_llm(prompt)
    
    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate fallback response when LLM is unavailable"""
        if "growth" in prompt.lower():
            return "Based on historical trends, this area shows promising growth potential with expected appreciation of 8-12% annually driven by infrastructure development and IT corridor expansion."
        elif "investment" in prompt.lower():
            return "This property presents a balanced investment opportunity with moderate risk and steady returns. Consider factors like connectivity, upcoming infrastructure, and rental demand in your decision."
        else:
            return "This analysis suggests favorable market conditions for real estate investment in this area. Please consult detailed metrics for comprehensive insights."
    
    def _generate_mock_mappls_data(self, location: str) -> Dict[str, Any]:
        """Generate mock Mappls data for testing"""
        locations = {
            "Whitefield": {"lat": 12.9698, "lon": 77.7499, "pincode": "560066"},
            "Koramangala": {"lat": 12.9352, "lon": 77.6245, "pincode": "560034"},
            "Hebbal": {"lat": 13.0358, "lon": 77.5970, "pincode": "560024"},
            "Electronic City": {"lat": 12.8406, "lon": 77.6762, "pincode": "560100"}
        }
        
        loc_data = locations.get(location, {"lat": 12.9716, "lon": 77.5946, "pincode": "560001"})
        
        return {
            "location": location,
            "latitude": loc_data["lat"],
            "longitude": loc_data["lon"],
            "formatted_address": f"{location}, Bangalore, Karnataka",
            "city": "Bangalore",
            "state": "Karnataka",
            "pincode": loc_data["pincode"],
            "place_id": f"mappls_{location.lower().replace(' ', '_')}"
        }
    
    def _generate_mock_pois(self, category: str) -> List[Dict[str, Any]]:
        """Generate mock POI data"""
        poi_types = {
            "FINATM": ["HDFC ATM", "SBI ATM", "ICICI Bank"],
            "SCHOOL": ["DPS School", "Ryan International", "Vibgyor High"],
            "HOSPITAL": ["Columbia Asia", "Manipal Hospital", "Apollo Clinic"],
            "MALL": ["Forum Mall", "Phoenix Marketcity", "VR Mall"]
        }
        
        pois = []
        names = poi_types.get(category, ["Generic POI"])
        
        for i, name in enumerate(names[:3]):
            pois.append({
                "name": name,
                "distance": round(0.5 + i * 0.8, 1),
                "category": category,
                "address": f"Near {name}, Bangalore",
                "lat": 12.97 + i * 0.01,
                "lon": 77.59 + i * 0.01
            })
        
        return pois
    
    def _generate_mock_similar_properties(self) -> List[Dict[str, Any]]:
        """Generate mock similar properties"""
        properties = []
        zones = ["Whitefield", "Sarjapur", "Hebbal", "Electronic City"]
        
        for i, zone in enumerate(zones):
            properties.append({
                "id": f"prop_{i+1}",
                "score": 0.95 - i * 0.05,
                "metadata": {
                    "location": zone,
                    "price": 7000000 + i * 500000,
                    "area_sqft": 1200 + i * 100,
                    "bedrooms": 3,
                    "property_type": "Apartment"
                }
            })
        
        return properties


# Singleton instance
external_api_service = ExternalAPIService()
