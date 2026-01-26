"""
Visual AI Analyzer for Valora AI
Phase 3.1: Property image analysis and visual understanding

Features:
- Property image quality scoring
- Style classification (Modern, Traditional, Colonial, etc.)
- Condition assessment from photos
- Amenity detection from images
- View quality analysis from photos
- Visual similarity search

Supports:
- Qwen 3 VL (local via Ollama)
- LLaVA (local via Ollama)
- Future: CLIP for embeddings
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import base64
import json
from pathlib import Path


@dataclass
class ImageAnalysis:
    """Result of property image analysis."""
    image_id: str
    quality_score: float  # 0-100
    style: str  # modern, traditional, colonial, contemporary, minimalist
    condition: str  # excellent, good, fair, needs_work
    detected_features: List[str] = field(default_factory=list)
    detected_amenities: List[str] = field(default_factory=list)
    view_quality: str = "unknown"
    lighting: str = "unknown"  # bright, moderate, dim
    cleanliness: str = "unknown"
    spaciousness: str = "unknown"  # spacious, adequate, compact
    description: str = ""
    confidence: float = 0.0


@dataclass
class VisualSimilarity:
    """Result of visual similarity search."""
    query_image_id: str
    similar_properties: List[Dict[str, Any]] = field(default_factory=list)
    similarity_scores: List[float] = field(default_factory=list)


class VisualAnalyzer:
    """
    Analyzes property images using vision-language models.
    Integrates with local Ollama models (Qwen VL, LLaVA) for offline analysis.
    """
    
    # Supported vision models in preference order
    VISION_MODELS = [
        "qwen2.5-vl",      # Qwen 3 VL
        "qwen2-vl",
        "llava:latest",
        "llava:13b",
        "llava:7b",
        "bakllava",
        "moondream"
    ]
    
    # Style classification keywords
    STYLES = {
        'modern': ['modern', 'contemporary', 'sleek', 'minimalist', 'glass', 'steel'],
        'traditional': ['traditional', 'classic', 'heritage', 'vintage', 'old-world'],
        'colonial': ['colonial', 'british', 'bungalow', 'verandah', 'pillars'],
        'minimalist': ['minimalist', 'simple', 'clean', 'sparse', 'zen'],
        'luxury': ['luxury', 'premium', 'high-end', 'opulent', 'lavish'],
        'contemporary': ['contemporary', 'current', 'trendy', 'urban', 'chic']
    }
    
    # Condition keywords
    CONDITIONS = {
        'excellent': ['excellent', 'pristine', 'perfect', 'immaculate', 'brand new'],
        'good': ['good', 'well-maintained', 'clean', 'nice', 'decent'],
        'fair': ['fair', 'average', 'okay', 'acceptable', 'livable'],
        'needs_work': ['needs work', 'renovation', 'repair', 'dated', 'worn', 'old']
    }
    
    def __init__(self):
        self.vlm_model = None
        self.vlm_available = False
        self._init_vlm()
        
        # Image cache
        self.analysis_cache: Dict[str, ImageAnalysis] = {}
    
    def _init_vlm(self):
        """Initialize vision-language model connection."""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=3)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                
                # Find first available vision model
                for vm in self.VISION_MODELS:
                    for name in model_names:
                        if vm.lower() in name.lower():
                            self.vlm_model = name
                            self.vlm_available = True
                            print(f"[VisualAnalyzer] Vision model: {self.vlm_model}")
                            return
                
                print("[VisualAnalyzer] No vision model found in Ollama")
        except Exception as e:
            print(f"[VisualAnalyzer] Ollama not available: {e}")
    
    def analyze_property_image(self, image_path: str = None, 
                               image_base64: str = None,
                               image_id: str = None) -> ImageAnalysis:
        """
        Analyze a property image.
        
        Args:
            image_path: Path to image file
            image_base64: Base64 encoded image
            image_id: Unique identifier for caching
            
        Returns:
            ImageAnalysis with quality, style, condition, etc.
        """
        # Generate ID if not provided
        if not image_id:
            image_id = f"img_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Check cache
        if image_id in self.analysis_cache:
            return self.analysis_cache[image_id]
        
        # Get base64 from path if needed
        if image_path and not image_base64:
            image_base64 = self._load_image_base64(image_path)
        
        if not image_base64:
            return ImageAnalysis(
                image_id=image_id,
                quality_score=0,
                style="unknown",
                condition="unknown",
                description="No image provided",
                confidence=0
            )
        
        # Analyze with VLM if available
        if self.vlm_available:
            analysis = self._analyze_with_vlm(image_base64, image_id)
        else:
            analysis = self._analyze_basic(image_id)
        
        # Cache result
        self.analysis_cache[image_id] = analysis
        
        return analysis
    
    def _load_image_base64(self, image_path: str) -> Optional[str]:
        """Load image and convert to base64."""
        try:
            path = Path(image_path)
            if path.exists():
                with open(path, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"[VisualAnalyzer] Error loading image: {e}")
        return None
    
    def _analyze_with_vlm(self, image_base64: str, image_id: str) -> ImageAnalysis:
        """Analyze image using vision-language model."""
        try:
            import requests
            
            prompt = """Analyze this property/real estate image and provide:

1. QUALITY SCORE (0-100): Rate overall image quality and property appeal
2. STYLE: Classify as one of: modern, traditional, colonial, minimalist, luxury, contemporary
3. CONDITION: Rate as: excellent, good, fair, or needs_work
4. FEATURES: List visible features (balcony, garden, parking, pool, etc.)
5. AMENITIES: List visible amenities (AC, modular kitchen, marble flooring, etc.)
6. LIGHTING: Rate as: bright, moderate, or dim
7. SPACIOUSNESS: Rate as: spacious, adequate, or compact
8. VIEW: Describe the view quality if visible
9. BRIEF DESCRIPTION: 1-2 sentence summary

Format your response as:
QUALITY: [score]
STYLE: [style]
CONDITION: [condition]
FEATURES: [comma-separated list]
AMENITIES: [comma-separated list]
LIGHTING: [rating]
SPACIOUSNESS: [rating]
VIEW: [description]
DESCRIPTION: [summary]"""
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.vlm_model,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return self._parse_vlm_response(result.get('response', ''), image_id)
            
        except Exception as e:
            print(f"[VisualAnalyzer] VLM error: {e}")
        
        return self._analyze_basic(image_id)
    
    def _parse_vlm_response(self, response: str, image_id: str) -> ImageAnalysis:
        """Parse VLM response into ImageAnalysis."""
        analysis = ImageAnalysis(
            image_id=image_id,
            quality_score=50,
            style="unknown",
            condition="unknown",
            confidence=0.8
        )
        
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if ':' not in line:
                continue
            
            key, value = line.split(':', 1)
            key = key.strip().upper()
            value = value.strip()
            
            if key == 'QUALITY':
                try:
                    score = float(''.join(c for c in value if c.isdigit() or c == '.'))
                    analysis.quality_score = min(100, max(0, score))
                except:
                    pass
            
            elif key == 'STYLE':
                value_lower = value.lower()
                for style in self.STYLES:
                    if style in value_lower:
                        analysis.style = style
                        break
            
            elif key == 'CONDITION':
                value_lower = value.lower()
                for condition in self.CONDITIONS:
                    if condition.replace('_', ' ') in value_lower or condition in value_lower:
                        analysis.condition = condition
                        break
            
            elif key == 'FEATURES':
                analysis.detected_features = [f.strip() for f in value.split(',') if f.strip()]
            
            elif key == 'AMENITIES':
                analysis.detected_amenities = [a.strip() for a in value.split(',') if a.strip()]
            
            elif key == 'LIGHTING':
                if 'bright' in value.lower():
                    analysis.lighting = 'bright'
                elif 'dim' in value.lower():
                    analysis.lighting = 'dim'
                else:
                    analysis.lighting = 'moderate'
            
            elif key == 'SPACIOUSNESS':
                if 'spacious' in value.lower():
                    analysis.spaciousness = 'spacious'
                elif 'compact' in value.lower():
                    analysis.spaciousness = 'compact'
                else:
                    analysis.spaciousness = 'adequate'
            
            elif key == 'VIEW':
                analysis.view_quality = value
            
            elif key == 'DESCRIPTION':
                analysis.description = value
        
        return analysis
    
    def _analyze_basic(self, image_id: str) -> ImageAnalysis:
        """Basic analysis when VLM is not available."""
        return ImageAnalysis(
            image_id=image_id,
            quality_score=50,
            style="unknown",
            condition="unknown",
            description="Visual analysis requires a vision model (Qwen VL, LLaVA). Install via: ollama pull qwen2.5-vl",
            confidence=0.0
        )
    
    def analyze_property_photos(self, image_paths: List[str] = None,
                                images_base64: List[str] = None) -> Dict[str, Any]:
        """
        Analyze multiple property photos and aggregate results.
        
        Args:
            image_paths: List of image file paths
            images_base64: List of base64 encoded images
            
        Returns:
            Aggregated analysis of all images
        """
        analyses = []
        
        # Get list of images to analyze
        images = []
        if image_paths:
            for i, path in enumerate(image_paths):
                b64 = self._load_image_base64(path)
                if b64:
                    images.append((f"img_{i}", b64))
        elif images_base64:
            for i, b64 in enumerate(images_base64):
                images.append((f"img_{i}", b64))
        
        # Analyze each image
        for img_id, img_b64 in images:
            analysis = self.analyze_property_image(image_base64=img_b64, image_id=img_id)
            analyses.append(analysis)
        
        # Aggregate results
        if not analyses:
            return {"error": "No images to analyze"}
        
        avg_quality = sum(a.quality_score for a in analyses) / len(analyses)
        
        # Most common style
        styles = [a.style for a in analyses if a.style != "unknown"]
        common_style = max(set(styles), key=styles.count) if styles else "unknown"
        
        # Most common condition
        conditions = [a.condition for a in analyses if a.condition != "unknown"]
        common_condition = max(set(conditions), key=conditions.count) if conditions else "unknown"
        
        # Collect all features and amenities
        all_features = set()
        all_amenities = set()
        for a in analyses:
            all_features.update(a.detected_features)
            all_amenities.update(a.detected_amenities)
        
        return {
            "image_count": len(analyses),
            "average_quality_score": round(avg_quality, 1),
            "dominant_style": common_style,
            "overall_condition": common_condition,
            "detected_features": list(all_features),
            "detected_amenities": list(all_amenities),
            "individual_analyses": [
                {
                    "image_id": a.image_id,
                    "quality": a.quality_score,
                    "style": a.style,
                    "condition": a.condition,
                    "description": a.description
                }
                for a in analyses
            ],
            "vlm_model": self.vlm_model,
            "vlm_available": self.vlm_available
        }
    
    def compare_properties_visually(self, 
                                    property_a_images: List[str],
                                    property_b_images: List[str]) -> Dict[str, Any]:
        """
        Compare two properties based on their images.
        
        Args:
            property_a_images: Base64 images of property A
            property_b_images: Base64 images of property B
            
        Returns:
            Visual comparison results
        """
        analysis_a = self.analyze_property_photos(images_base64=property_a_images)
        analysis_b = self.analyze_property_photos(images_base64=property_b_images)
        
        comparison = {
            "property_a": analysis_a,
            "property_b": analysis_b,
            "comparison": {
                "quality_winner": "A" if analysis_a.get('average_quality_score', 0) > analysis_b.get('average_quality_score', 0) else "B",
                "quality_difference": abs(analysis_a.get('average_quality_score', 0) - analysis_b.get('average_quality_score', 0)),
                "style_match": analysis_a.get('dominant_style') == analysis_b.get('dominant_style'),
                "condition_winner": self._compare_condition(
                    analysis_a.get('overall_condition', 'unknown'),
                    analysis_b.get('overall_condition', 'unknown')
                ),
                "features_only_in_a": list(set(analysis_a.get('detected_features', [])) - set(analysis_b.get('detected_features', []))),
                "features_only_in_b": list(set(analysis_b.get('detected_features', [])) - set(analysis_a.get('detected_features', []))),
            }
        }
        
        return comparison
    
    def _compare_condition(self, cond_a: str, cond_b: str) -> str:
        """Compare two conditions and return winner."""
        order = {'excellent': 4, 'good': 3, 'fair': 2, 'needs_work': 1, 'unknown': 0}
        score_a = order.get(cond_a, 0)
        score_b = order.get(cond_b, 0)
        
        if score_a > score_b:
            return "A"
        elif score_b > score_a:
            return "B"
        else:
            return "tie"
    
    def get_vlm_status(self) -> Dict[str, Any]:
        """Get status of vision-language model."""
        return {
            "available": self.vlm_available,
            "model": self.vlm_model,
            "supported_models": self.VISION_MODELS,
            "install_command": "ollama pull qwen2.5-vl" if not self.vlm_available else None
        }


# Singleton instance
_visual_analyzer = None


def get_visual_analyzer() -> VisualAnalyzer:
    """Get or create visual analyzer singleton."""
    global _visual_analyzer
    if _visual_analyzer is None:
        _visual_analyzer = VisualAnalyzer()
    return _visual_analyzer
