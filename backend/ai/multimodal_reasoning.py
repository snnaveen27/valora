"""
Multi-Modal Reasoning Engine for Valora AI
Phase 2.1: Combines text + spatial + visual understanding

Architecture:
- Text Encoder: NLP understanding of user queries
- Spatial Encoder: Building, POI, and location context
- Visual Encoder: Map state, viewport, building appearance
- Fusion Layer: Cross-modal attention and integration
- Decoder: Spatially-grounded response generation

Qwen 3 VL Integration Ready: Can use local vision-language model
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import re


@dataclass
class TextContext:
    """Extracted text context from user query."""
    original_query: str
    intent: str
    entities: List[str] = field(default_factory=list)  # Locations, property types, etc.
    constraints: Dict[str, Any] = field(default_factory=dict)  # Budget, bedrooms, etc.
    sentiment: str = "neutral"  # positive, negative, neutral
    urgency: str = "normal"  # urgent, normal, casual


@dataclass
class SpatialContext:
    """Spatial context from GIS data."""
    center_lat: float = 0.0
    center_lng: float = 0.0
    zoom_level: float = 15.0
    visible_buildings: int = 0
    visible_pois: int = 0
    selected_building: Optional[Dict] = None
    nearby_landmarks: List[str] = field(default_factory=list)
    area_characteristics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualContext:
    """Visual context from map/viewport state."""
    viewport_bounds: Dict[str, float] = field(default_factory=dict)
    dominant_building_type: str = "mixed"
    urban_density: str = "medium"  # low, medium, high
    green_coverage: float = 0.0
    skyline_character: str = "mixed"  # low-rise, mid-rise, high-rise
    street_pattern: str = "organic"  # grid, organic, radial


@dataclass
class FusedContext:
    """Fused multi-modal context for reasoning."""
    text: TextContext
    spatial: SpatialContext
    visual: VisualContext
    confidence: float = 0.0
    reasoning_steps: List[Dict[str, Any]] = field(default_factory=list)


class TextEncoder:
    """Encodes and extracts meaning from text queries."""
    
    # Intent patterns
    INTENT_PATTERNS = {
        'search': r'\b(find|search|show|looking for|want|need)\b',
        'compare': r'\b(compare|versus|vs|better|difference)\b',
        'analyze': r'\b(analyze|analysis|assess|evaluate|tell me about)\b',
        'navigate': r'\b(go to|take me|show me|navigate|fly to)\b',
        'simulate': r'\b(what if|simulate|imagine|hypothetical)\b',
        'value': r'\b(price|cost|value|worth|estimate)\b',
    }
    
    # Entity patterns
    ENTITY_PATTERNS = {
        'location': r'\b(indiranagar|koramangala|whitefield|hsr|btm|jayanagar|jp nagar|marathahalli|electronic city|hebbal|yelahanka|banashankari|rajajinagar|malleswaram|basavanagudi)\b',
        'property_type': r'\b(apartment|flat|house|villa|plot|land|commercial|office|shop)\b',
        'bedrooms': r'\b(\d+)\s*bhk\b',
        'budget': r'\b(\d+(?:\.\d+)?)\s*(lakh|lac|cr|crore)\b',
    }
    
    def encode(self, query: str) -> TextContext:
        """Extract structured context from text query."""
        query_lower = query.lower()
        
        # Detect intent
        intent = 'general'
        for intent_type, pattern in self.INTENT_PATTERNS.items():
            if re.search(pattern, query_lower):
                intent = intent_type
                break
        
        # Extract entities
        entities = []
        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            matches = re.findall(pattern, query_lower)
            entities.extend(matches)
        
        # Extract constraints
        constraints = {}
        
        # Budget
        budget_match = re.search(r'(\d+(?:\.\d+)?)\s*(lakh|lac|cr|crore)', query_lower)
        if budget_match:
            amount = float(budget_match.group(1))
            unit = budget_match.group(2)
            if unit in ['cr', 'crore']:
                amount *= 100  # Convert to lakhs
            constraints['max_budget_lakhs'] = amount
        
        # Bedrooms
        bhk_match = re.search(r'(\d+)\s*bhk', query_lower)
        if bhk_match:
            constraints['bedrooms'] = int(bhk_match.group(1))
        
        # Sentiment detection (simple)
        positive_words = ['good', 'great', 'excellent', 'best', 'nice', 'love']
        negative_words = ['bad', 'worst', 'avoid', 'problem', 'issue', 'expensive']
        
        sentiment = 'neutral'
        if any(word in query_lower for word in positive_words):
            sentiment = 'positive'
        elif any(word in query_lower for word in negative_words):
            sentiment = 'negative'
        
        # Urgency
        urgency = 'normal'
        if any(word in query_lower for word in ['urgent', 'asap', 'immediately', 'quickly']):
            urgency = 'urgent'
        elif any(word in query_lower for word in ['just curious', 'wondering', 'maybe']):
            urgency = 'casual'
        
        return TextContext(
            original_query=query,
            intent=intent,
            entities=entities,
            constraints=constraints,
            sentiment=sentiment,
            urgency=urgency
        )


class SpatialEncoder:
    """Encodes spatial context from GIS data."""
    
    def __init__(self):
        self.db_service = None
        self._init_database()
    
    def _init_database(self):
        """Initialize database connection."""
        try:
            from database.db_service import DatabaseService
            from pathlib import Path
            from backend.config import config
            self.db_service = DatabaseService(str(config.DB_PATH))
        except Exception as e:
            print(f"[SpatialEncoder] Database init error: {e}")
    
    def encode(self, lat: float, lng: float, 
               selected_building: Dict = None,
               viewport: Dict = None) -> SpatialContext:
        """Extract spatial context from location."""
        context = SpatialContext(
            center_lat=lat,
            center_lng=lng,
            selected_building=selected_building
        )
        
        if not self.db_service:
            return context
        
        radius_deg = 1000 / 111000  # 1km
        
        try:
            # Count visible buildings
            building_query = """
                SELECT COUNT(*) as cnt FROM buildings
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            result = self.db_service.execute(building_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            context.visible_buildings = result[0]['cnt'] if result else 0
            
            # Count POIs
            poi_query = """
                SELECT COUNT(*) as cnt FROM pois
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            result = self.db_service.execute(poi_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            context.visible_pois = result[0]['cnt'] if result else 0
            
            # Get nearby landmarks
            landmark_query = """
                SELECT name FROM pois
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                AND name IS NOT NULL AND name != ''
                LIMIT 10
            """
            landmarks = self.db_service.execute(landmark_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            )) or []
            context.nearby_landmarks = [l['name'] for l in landmarks]
            
            # Area characteristics
            context.area_characteristics = self._analyze_area(lat, lng)
            
        except Exception as e:
            print(f"[SpatialEncoder] Query error: {e}")
        
        return context
    
    def _analyze_area(self, lat: float, lng: float) -> Dict[str, Any]:
        """Analyze area characteristics."""
        characteristics = {
            'development_level': 'moderate',
            'residential_density': 'medium',
            'commercial_activity': 'medium',
            'connectivity': 'good'
        }
        
        if not self.db_service:
            return characteristics
        
        radius_deg = 2000 / 111000
        
        try:
            # Check for metro
            metro_query = """
                SELECT COUNT(*) as cnt FROM transport
                WHERE type IN ('metro', 'metro_station')
                AND latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            result = self.db_service.execute(metro_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            if result and result[0]['cnt'] > 0:
                characteristics['connectivity'] = 'excellent'
            
            # Building density
            building_query = """
                SELECT COUNT(*) as cnt FROM buildings
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
            """
            result = self.db_service.execute(building_query, (
                lat - radius_deg, lat + radius_deg,
                lng - radius_deg, lng + radius_deg
            ))
            building_count = result[0]['cnt'] if result else 0
            
            if building_count > 200:
                characteristics['residential_density'] = 'high'
                characteristics['development_level'] = 'mature'
            elif building_count > 100:
                characteristics['residential_density'] = 'medium'
                characteristics['development_level'] = 'developing'
            else:
                characteristics['residential_density'] = 'low'
                characteristics['development_level'] = 'emerging'
            
        except:
            pass
        
        return characteristics


class VisualEncoder:
    """Encodes visual context from map state."""
    
    def encode(self, viewport: Dict = None, 
               buildings_in_view: List[Dict] = None) -> VisualContext:
        """Extract visual context from viewport state."""
        context = VisualContext()
        
        if viewport:
            context.viewport_bounds = viewport
        
        if not buildings_in_view:
            return context
        
        # Analyze building types
        type_counts = {}
        heights = []
        for b in buildings_in_view:
            btype = b.get('building_type', 'unknown')
            type_counts[btype] = type_counts.get(btype, 0) + 1
            if b.get('height'):
                heights.append(b['height'])
        
        # Dominant type
        if type_counts:
            context.dominant_building_type = max(type_counts, key=type_counts.get)
        
        # Density
        total_buildings = len(buildings_in_view)
        if total_buildings > 100:
            context.urban_density = 'high'
        elif total_buildings > 50:
            context.urban_density = 'medium'
        else:
            context.urban_density = 'low'
        
        # Skyline character
        if heights:
            avg_height = sum(heights) / len(heights)
            if avg_height > 30:
                context.skyline_character = 'high-rise'
            elif avg_height > 15:
                context.skyline_character = 'mid-rise'
            else:
                context.skyline_character = 'low-rise'
        
        return context


class FusionLayer:
    """Fuses multi-modal contexts into unified understanding."""
    
    def fuse(self, text: TextContext, spatial: SpatialContext, 
             visual: VisualContext) -> FusedContext:
        """Fuse text, spatial, and visual contexts."""
        reasoning_steps = []
        confidence = 0.7  # Base confidence
        
        # Step 1: Text understanding
        reasoning_steps.append({
            "step": "text_understanding",
            "description": f"Detected intent: {text.intent}, entities: {text.entities}",
            "confidence": 0.9
        })
        
        # Step 2: Spatial grounding
        spatial_description = f"Location at {spatial.center_lat:.4f}, {spatial.center_lng:.4f}"
        if spatial.nearby_landmarks:
            spatial_description += f" near {', '.join(spatial.nearby_landmarks[:3])}"
        
        reasoning_steps.append({
            "step": "spatial_grounding",
            "description": spatial_description,
            "confidence": 0.85 if spatial.visible_buildings > 0 else 0.5
        })
        
        # Step 3: Visual analysis
        reasoning_steps.append({
            "step": "visual_analysis",
            "description": f"Urban density: {visual.urban_density}, skyline: {visual.skyline_character}",
            "confidence": 0.75
        })
        
        # Step 4: Cross-modal integration
        integration_notes = []
        
        # Check if text mentions location that matches spatial context
        if text.entities and spatial.nearby_landmarks:
            if any(e in ' '.join(spatial.nearby_landmarks).lower() for e in text.entities):
                integration_notes.append("Text query matches spatial context")
                confidence += 0.1
        
        # Check if visual matches expected from text
        if text.intent == 'search' and 'apartment' in str(text.constraints):
            if visual.urban_density in ['medium', 'high']:
                integration_notes.append("Area suitable for apartment search")
                confidence += 0.05
        
        reasoning_steps.append({
            "step": "cross_modal_integration",
            "description": " | ".join(integration_notes) if integration_notes else "Standard fusion applied",
            "confidence": confidence
        })
        
        return FusedContext(
            text=text,
            spatial=spatial,
            visual=visual,
            confidence=min(1.0, confidence),
            reasoning_steps=reasoning_steps
        )


class MultiModalReasoner:
    """
    Main multi-modal reasoning engine.
    Combines text, spatial, and visual understanding for grounded responses.
    
    Qwen 3 VL Ready: Can integrate local vision-language model for image understanding.
    """
    
    def __init__(self):
        self.text_encoder = TextEncoder()
        self.spatial_encoder = SpatialEncoder()
        self.visual_encoder = VisualEncoder()
        self.fusion_layer = FusionLayer()
        
        # Vision-language model (optional - for Qwen 3 VL)
        self.vlm = None
        self.vlm_available = False
        self._init_vlm()
    
    def _init_vlm(self):
        """Initialize vision-language model if available."""
        try:
            # Check for Ollama with vision model
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                vision_models = [m for m in models if 'vl' in m.get('name', '').lower() 
                                or 'vision' in m.get('name', '').lower()
                                or 'llava' in m.get('name', '').lower()]
                if vision_models:
                    self.vlm = vision_models[0]['name']
                    self.vlm_available = True
                    print(f"[MultiModalReasoner] Vision model available: {self.vlm}")
        except:
            pass
    
    def reason(self, query: str, 
               lat: float = None, lng: float = None,
               selected_building: Dict = None,
               viewport: Dict = None,
               buildings_in_view: List[Dict] = None,
               image_base64: str = None) -> Dict[str, Any]:
        """
        Perform multi-modal reasoning on a query.
        
        Args:
            query: User's text query
            lat, lng: Current map center
            selected_building: Currently selected building
            viewport: Current viewport bounds
            buildings_in_view: Buildings visible in viewport
            image_base64: Optional screenshot for visual analysis
            
        Returns:
            Reasoning result with fused context and response guidance
        """
        # Encode text
        text_context = self.text_encoder.encode(query)
        
        # Encode spatial
        spatial_context = SpatialContext()
        if lat is not None and lng is not None:
            spatial_context = self.spatial_encoder.encode(
                lat, lng, selected_building, viewport
            )
        
        # Encode visual
        visual_context = self.visual_encoder.encode(viewport, buildings_in_view)
        
        # Fuse contexts
        fused = self.fusion_layer.fuse(text_context, spatial_context, visual_context)
        
        # Generate response guidance
        guidance = self._generate_guidance(fused)
        
        # If VLM available and image provided, add visual understanding
        visual_understanding = None
        if self.vlm_available and image_base64:
            visual_understanding = self._analyze_image(image_base64, query)
        
        return {
            "query": query,
            "intent": text_context.intent,
            "entities": text_context.entities,
            "constraints": text_context.constraints,
            "spatial_context": {
                "lat": spatial_context.center_lat,
                "lng": spatial_context.center_lng,
                "visible_buildings": spatial_context.visible_buildings,
                "nearby_landmarks": spatial_context.nearby_landmarks,
                "area_characteristics": spatial_context.area_characteristics
            },
            "visual_context": {
                "urban_density": visual_context.urban_density,
                "skyline_character": visual_context.skyline_character,
                "dominant_building_type": visual_context.dominant_building_type
            },
            "reasoning_steps": fused.reasoning_steps,
            "confidence": fused.confidence,
            "response_guidance": guidance,
            "visual_understanding": visual_understanding,
            "vlm_available": self.vlm_available
        }
    
    def _generate_guidance(self, fused: FusedContext) -> Dict[str, Any]:
        """Generate response guidance based on fused context."""
        guidance = {
            "response_type": "informative",
            "focus_areas": [],
            "suggested_actions": [],
            "tone": "professional"
        }
        
        # Set response type based on intent
        intent_to_type = {
            'search': 'list',
            'compare': 'comparison',
            'analyze': 'analysis',
            'navigate': 'navigation',
            'simulate': 'simulation',
            'value': 'valuation',
            'general': 'informative'
        }
        guidance["response_type"] = intent_to_type.get(fused.text.intent, 'informative')
        
        # Set focus areas based on context
        if fused.text.constraints.get('max_budget_lakhs'):
            guidance["focus_areas"].append("budget_analysis")
        if fused.text.constraints.get('bedrooms'):
            guidance["focus_areas"].append("property_specifications")
        if fused.spatial.area_characteristics.get('connectivity') == 'excellent':
            guidance["focus_areas"].append("connectivity")
        if fused.visual.urban_density == 'high':
            guidance["focus_areas"].append("urban_density")
        
        # Suggested UI actions
        if fused.text.intent == 'navigate' and fused.text.entities:
            guidance["suggested_actions"].append({
                "action": "flyTo",
                "location": fused.text.entities[0]
            })
        if fused.text.intent == 'search':
            guidance["suggested_actions"].append({
                "action": "showProperties",
                "filters": fused.text.constraints
            })
        if fused.text.intent == 'analyze':
            guidance["suggested_actions"].append({
                "action": "showAnalysisPanel"
            })
        
        # Set tone based on sentiment and urgency
        if fused.text.urgency == 'urgent':
            guidance["tone"] = "direct"
        elif fused.text.sentiment == 'positive':
            guidance["tone"] = "enthusiastic"
        
        return guidance
    
    def _analyze_image(self, image_base64: str, query: str) -> Dict[str, Any]:
        """Analyze image using vision-language model (Qwen VL, LLaVA, etc.)."""
        if not self.vlm_available or not self.vlm:
            return None
        
        try:
            import requests
            
            prompt = f"""Analyze this map/property image and answer: {query}
            
Focus on:
- Building types and density
- Urban character (modern, traditional, mixed)
- Green spaces and amenities
- Overall area appeal

Provide a brief, factual analysis."""
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.vlm,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "model": self.vlm,
                    "analysis": result.get('response', ''),
                    "success": True
                }
        except Exception as e:
            print(f"[MultiModalReasoner] VLM error: {e}")
        
        return None
    
    def get_context_for_llm(self, fused_result: Dict[str, Any]) -> str:
        """Generate context string for LLM prompt."""
        parts = []
        
        # Query understanding
        parts.append(f"**User Intent:** {fused_result['intent']}")
        if fused_result['entities']:
            parts.append(f"**Mentioned Locations:** {', '.join(fused_result['entities'])}")
        if fused_result['constraints']:
            constraints_str = ', '.join(f"{k}: {v}" for k, v in fused_result['constraints'].items())
            parts.append(f"**Requirements:** {constraints_str}")
        
        # Spatial context
        spatial = fused_result.get('spatial_context', {})
        if spatial.get('nearby_landmarks'):
            parts.append(f"**Nearby Landmarks:** {', '.join(spatial['nearby_landmarks'][:5])}")
        if spatial.get('area_characteristics'):
            chars = spatial['area_characteristics']
            parts.append(f"**Area:** {chars.get('development_level', 'unknown')} development, {chars.get('connectivity', 'unknown')} connectivity")
        
        # Visual context
        visual = fused_result.get('visual_context', {})
        parts.append(f"**Urban Character:** {visual.get('urban_density', 'unknown')} density, {visual.get('skyline_character', 'unknown')} skyline")
        
        # Confidence
        parts.append(f"**Confidence:** {fused_result.get('confidence', 0):.0%}")
        
        return "\n".join(parts)


# Singleton instance
_multimodal_reasoner = None


def get_multimodal_reasoner() -> MultiModalReasoner:
    """Get or create multi-modal reasoner singleton."""
    global _multimodal_reasoner
    if _multimodal_reasoner is None:
        _multimodal_reasoner = MultiModalReasoner()
    return _multimodal_reasoner
