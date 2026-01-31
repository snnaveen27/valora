"""
OpenRouter LLM Client for Valora AI
Production-grade client with DeepSeek V3.1 (671B) as default model.
Supports structured outputs (JSON mode) and proper error handling.
"""

import os
import json
import httpx
import asyncio
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path


# =============================================================================
# CONFIGURATION
# =============================================================================

class ModelType(Enum):
    """Available model types for different use cases."""
    PRIMARY = "primary"          # Main chat model (best quality)
    FAST = "fast"                # Quick responses
    REASONING = "reasoning"      # Deep analysis/simulation
    VISION = "vision"            # Image understanding


@dataclass
class OpenRouterConfig:
    """Configuration for OpenRouter client."""
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    
    # DeepSeek V3.2 (671B) - Best value, GPT-4 level performance
    primary_model: str = "deepseek/deepseek-chat"
    
    # Fast model for quick responses
    fast_model: str = "deepseek/deepseek-chat"
    
    # Reasoning model for simulations and complex analysis
    reasoning_model: str = "deepseek/deepseek-reasoner"
    
    # Vision model for property images
    vision_model: str = "qwen/qwen2.5-vl-72b-instruct"
    
    # Fallback models if primary fails
    fallback_models: List[str] = field(default_factory=lambda: [
        "anthropic/claude-3.5-sonnet",
        "google/gemini-2.0-flash-001",
    ])
    
    # Request settings
    timeout: float = 120.0
    max_retries: int = 2
    
    # Site info for OpenRouter
    site_url: str = "http://localhost:3000"
    site_name: str = "Valora AI - City Intelligence Platform"


# =============================================================================
# STRUCTURED OUTPUT SCHEMAS
# =============================================================================

@dataclass
class ValoraResponse:
    """Structured response from Valora AI."""
    message: str                           # Main response text
    confidence: float = 0.8                # Confidence score (0-1)
    intent_detected: str = ""              # Detected intent
    facts_used: List[str] = field(default_factory=list)  # Facts referenced
    ui_actions: List[Dict] = field(default_factory=list) # UI control actions
    follow_up_questions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass 
class AnalysisResponse:
    """Structured response for area/property analysis."""
    summary: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    confidence: float = 0.8
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SimulationResponse:
    """Structured response for what-if simulations."""
    scenario_summary: str
    impacts: Dict[str, Any] = field(default_factory=dict)
    timeline: List[Dict] = field(default_factory=list)
    confidence: float = 0.7
    assumptions: List[str] = field(default_factory=list)
    storyboard: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)


# JSON Schema for structured outputs
RESPONSE_SCHEMAS = {
    "chat": {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Main response to user query"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "facts_used": {"type": "array", "items": {"type": "string"}},
            "ui_actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["flyTo", "highlight", "openPanel", "switchTab", "setCinemaMode"]},
                        "value": {}
                    }
                }
            },
            "follow_up_questions": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["message"]
    },
    "analysis": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "metrics": {"type": "object"},
            "insights": {"type": "array", "items": {"type": "string"}},
            "recommendations": {"type": "array", "items": {"type": "string"}},
            "risk_factors": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"}
        },
        "required": ["summary"]
    },
    "simulation": {
        "type": "object", 
        "properties": {
            "scenario_summary": {"type": "string"},
            "impacts": {
                "type": "object",
                "properties": {
                    "property_value_pct": {"type": "number"},
                    "rental_yield_pct": {"type": "number"},
                    "demand_change": {"type": "string"},
                    "timeline_months": {"type": "integer"}
                }
            },
            "timeline": {"type": "array"},
            "confidence": {"type": "number"},
            "assumptions": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["scenario_summary", "impacts"]
    }
}


# =============================================================================
# OPENROUTER CLIENT
# =============================================================================

class OpenRouterClient:
    """
    Production-grade OpenRouter client for Valora AI.
    Uses DeepSeek V3.1 (671B) by default with structured outputs.
    """
    
    def __init__(self, config: Optional[OpenRouterConfig] = None):
        """Initialize client with config."""
        self.config = config or self._load_config()
        self._client: Optional[httpx.AsyncClient] = None
    
    def _load_config(self) -> OpenRouterConfig:
        """Load config from environment and config file."""
        config = OpenRouterConfig()
        
        # Load from environment
        config.api_key = os.getenv("OPENROUTER_API_KEY", "")
        
        # Load from config file if exists
        config_path = Path(__file__).parent.parent / "llm_config.json"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    saved = json.load(f)
                    if saved.get("openrouter_api_key"):
                        config.api_key = saved["openrouter_api_key"]
                    if saved.get("openrouter_model"):
                        config.primary_model = saved["openrouter_model"]
            except Exception as e:
                print(f"[WARNING] Failed to load LLM config: {e}")
        
        return config
    
    @property
    def is_configured(self) -> bool:
        """Check if API key is set."""
        return bool(self.config.api_key)
    
    def get_model(self, model_type: ModelType = ModelType.PRIMARY) -> str:
        """Get model ID for given type."""
        model_map = {
            ModelType.PRIMARY: self.config.primary_model,
            ModelType.FAST: self.config.fast_model,
            ModelType.REASONING: self.config.reasoning_model,
            ModelType.VISION: self.config.vision_model,
        }
        return model_map.get(model_type, self.config.primary_model)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model_type: ModelType = ModelType.PRIMARY,
        temperature: float = 0.5,
        max_tokens: int = 1024,
        json_mode: bool = False,
        json_schema: Optional[Dict] = None,
        stream: bool = False,
    ) -> Union[str, Dict[str, Any]]:
        """
        Send chat completion request to OpenRouter.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model_type: Type of model to use
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            json_mode: If True, request JSON output
            json_schema: Optional JSON schema for structured output
            stream: If True, return async generator
            
        Returns:
            Generated text or parsed JSON dict
        """
        if not self.is_configured:
            raise ValueError("OpenRouter API key not configured. Set OPENROUTER_API_KEY in environment.")
        
        model = self.get_model(model_type)
        client = await self._get_client()
        
        # Build request payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        
        # Add JSON mode if requested
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "HTTP-Referer": self.config.site_url,
            "X-Title": self.config.site_name,
            "Content-Type": "application/json",
        }
        
        # Retry logic
        last_error = None
        models_to_try = [model] + self.config.fallback_models[:self.config.max_retries]
        
        for attempt, current_model in enumerate(models_to_try):
            try:
                payload["model"] = current_model
                
                if stream:
                    return self._stream_response(client, headers, payload)
                
                response = await client.post(
                    self.config.base_url,
                    headers=headers,
                    json=payload,
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # Handle reasoning models that have separate reasoning field
                    reasoning = result.get("choices", [{}])[0].get("message", {}).get("reasoning")
                    
                    # Parse JSON if requested
                    if json_mode and content:
                        try:
                            parsed = json.loads(content)
                            if reasoning:
                                parsed["_reasoning"] = reasoning
                            return parsed
                        except json.JSONDecodeError:
                            # Try to extract JSON from response
                            import re
                            json_match = re.search(r'\{[\s\S]*\}', content)
                            if json_match:
                                try:
                                    parsed = json.loads(json_match.group())
                                    if reasoning:
                                        parsed["_reasoning"] = reasoning
                                    return parsed
                                except:
                                    pass
                            return {"message": content, "_raw": True}
                    
                    return content
                
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    await asyncio.sleep(2 ** attempt)
                    continue
                    
                else:
                    last_error = f"API error {response.status_code}: {response.text[:200]}"
                    print(f"[LLM] {last_error}")
                    continue
                    
            except httpx.TimeoutException:
                last_error = f"Timeout with model {current_model}"
                print(f"[LLM] {last_error}")
                continue
            except Exception as e:
                last_error = str(e)
                print(f"[LLM] Error: {last_error}")
                continue
        
        raise RuntimeError(f"All LLM attempts failed. Last error: {last_error}")
    
    async def _stream_response(
        self,
        client: httpx.AsyncClient,
        headers: Dict,
        payload: Dict,
    ):
        """Stream response chunks."""
        async with client.stream(
            "POST",
            self.config.base_url,
            headers=headers,
            json=payload,
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if content := delta.get("content"):
                            yield content
                    except json.JSONDecodeError:
                        continue
    
    async def analyze(
        self,
        query: str,
        facts: Dict[str, Any],
        context: Optional[str] = None,
    ) -> AnalysisResponse:
        """
        Generate structured analysis from facts.
        
        Args:
            query: User's analysis request
            facts: Grounded facts from GIS agents
            context: Additional context
            
        Returns:
            Structured AnalysisResponse
        """
        system_prompt = VALORA_PROMPTS["analysis"]
        
        facts_str = json.dumps(facts, indent=2, default=str)
        user_content = f"QUERY: {query}\n\nGROUNDED FACTS:\n{facts_str}"
        if context:
            user_content += f"\n\nADDITIONAL CONTEXT:\n{context}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        
        result = await self.chat(
            messages=messages,
            model_type=ModelType.PRIMARY,
            json_mode=True,
            temperature=0.4,
            max_tokens=1500,
        )
        
        if isinstance(result, dict):
            return AnalysisResponse(
                summary=result.get("summary", ""),
                metrics=result.get("metrics", {}),
                insights=result.get("insights", []),
                recommendations=result.get("recommendations", []),
                risk_factors=result.get("risk_factors", []),
                confidence=result.get("confidence", 0.8),
            )
        
        return AnalysisResponse(summary=str(result))
    
    async def simulate(
        self,
        scenario: str,
        current_state: Dict[str, Any],
        location: Optional[Dict] = None,
    ) -> SimulationResponse:
        """
        Generate what-if simulation results.
        
        Args:
            scenario: Scenario description
            current_state: Current area/property state
            location: Location coordinates
            
        Returns:
            Structured SimulationResponse
        """
        system_prompt = VALORA_PROMPTS["simulation"]
        
        state_str = json.dumps(current_state, indent=2, default=str)
        user_content = f"SCENARIO: {scenario}\n\nCURRENT STATE:\n{state_str}"
        if location:
            user_content += f"\n\nLOCATION: {location.get('lat')}, {location.get('lng')}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        
        result = await self.chat(
            messages=messages,
            model_type=ModelType.REASONING,
            json_mode=True,
            temperature=0.6,
            max_tokens=2000,
        )
        
        if isinstance(result, dict):
            return SimulationResponse(
                scenario_summary=result.get("scenario_summary", ""),
                impacts=result.get("impacts", {}),
                timeline=result.get("timeline", []),
                confidence=result.get("confidence", 0.7),
                assumptions=result.get("assumptions", []),
                storyboard=result.get("storyboard", {}),
            )
        
        return SimulationResponse(scenario_summary=str(result))


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

# Import production prompts
try:
    from ai.prompts import (
        SYSTEM_CONSTITUTION, INTENT_PROMPTS, Intent,
        get_system_prompt, format_facts_context,
        RESPONSE_SCHEMA, ANALYSIS_SCHEMA, SIMULATION_SCHEMA
    )
    PROMPTS_AVAILABLE = True
except ImportError:
    PROMPTS_AVAILABLE = False
    SYSTEM_CONSTITUTION = ""
    INTENT_PROMPTS = {}


VALORA_PROMPTS = {
    "chat": """# VALORA AI - CITY INTELLIGENCE AGENT

## IDENTITY
You are Valora AI, an expert city intelligence assistant for Bangalore real estate.
You are powered by deterministic GIS agents and a comprehensive offline database.

## CORE CONSTRAINTS (NEVER VIOLATE)

### 1. GROUNDED FACTS ONLY
- ONLY use data from the [GROUNDED FACTS] section below
- NEVER invent statistics, prices, scores, or counts
- If data is missing, explicitly state: "I don't have data for X"
- Every number you cite must come from the facts provided

### 2. OFFLINE-FIRST
- All data comes from local Bangalore database (686K buildings, 42K properties, 27K POIs)
- Never mention or reference external websites, APIs, or online resources
- Never suggest users "check online" or "visit websites"

### 3. CONFIDENCE LEVELS
- HIGH: Data directly from facts, verified
- MEDIUM: Inferred from available data  
- LOW: Limited data, state assumptions clearly

### 4. BANGALORE SCOPE
- Only cover Bangalore/Bengaluru areas
- For non-Bangalore queries, politely explain coverage limitation
- Use local terminology: "crore", "lakh", "sqft", locality names

## OUTPUT FORMAT

### Response Structure
1. **Direct Answer** (1-2 sentences) - Answer the user's question immediately
2. **Supporting Evidence** (2-3 bullets) - Cite specific facts
3. **Actionable Insight** (1-2 sentences) - What should user do next?

### Formatting Rules
- Use bullet points for lists (max 5 items)
- Use ₹ for prices, format large numbers with commas
- Bold key metrics: **₹12,500/sqft**, **85/100 walkability**
- Keep responses under 250 words unless complex analysis
- Never use emojis unless user explicitly uses them

## DATA DOMAINS

### Available Data (cite with confidence)
- Buildings: 686,370 with height, type, footprint
- Properties: 42,452 listings with prices, bedrooms, area
- POIs: 26,961 schools, hospitals, restaurants, parks
- Transport: 5,384 stops (29 metro + 4,224 bus)
- Localities: 788 with precomputed profiles
- Terrain: 9,090 grid cells with flood risk

### Computed Metrics (explain derivation)
- Walkability score: POI density + transport proximity
- Investment score: Growth trend + infrastructure + demand
- Livability: Schools + hospitals + parks + safety
- Flood risk: Terrain elevation + drainage data

When location data is available, use it to contextualize your response.
When market data is available, cite specific prices and trends.
Never make up statistics - if data isn't available, say so.""",

    "analysis": """# VALORA AI - AREA ANALYSIS ENGINE

You are generating structured area/property analysis from grounded GIS agent facts.

## INPUT
You receive deterministic facts from spatial, market, terrain, and POI agents.

## OUTPUT FORMAT (JSON)
{
  "summary": "2-3 sentence executive summary with key investment insight",
  "metrics": {
    "investment_score": 0-100,
    "livability_score": 0-100,
    "growth_potential": "high/medium/low",
    "risk_level": "low/medium/high"
  },
  "market_snapshot": {
    "avg_price_sqft": number,
    "price_trend_pct": number,
    "active_listings": number,
    "demand_level": "high/medium/low"
  },
  "infrastructure": {
    "walkability_score": 0-100,
    "metro_distance_km": number,
    "schools_1km": number,
    "hospitals_1km": number
  },
  "insights": ["Insight 1", "Insight 2", "Insight 3"],
  "risks": ["Risk 1", "Risk 2"],
  "recommendations": {
    "end_user": "Recommendation for home buyers",
    "investor": "Recommendation for investors"
  },
  "confidence": "HIGH/MEDIUM/LOW",
  "data_points_used": number
}

## RULES
- ALL metrics must come from provided facts - never invent
- If a metric is missing, omit it or set to null
- Be conservative with scores when data is limited
- Confidence reflects data completeness
- Insights must be specific, not generic""",

    "simulation": """# VALORA AI - SIMULATION ENGINE

You are simulating what-if scenarios for infrastructure and policy changes.

## INPUT
Scenario description + current area state from deterministic agents.

## OUTPUT FORMAT (JSON)
{
  "scenario_summary": "Clear description of scenario and primary impact",
  "impacts": {
    "property_value_change_pct": -20 to +50,
    "rental_yield_change_pct": -5 to +15,
    "demand_change": "significant_increase/moderate_increase/stable/moderate_decrease/significant_decrease",
    "timeline_months": 6-60,
    "affected_radius_km": 0.5-5.0,
    "confidence": 0.0-1.0
  },
  "causal_chain": [
    "1. [Intervention]",
    "2. [Primary effect]",
    "3. [Secondary effect]",
    "4. [Price impact]"
  ],
  "timeline": [
    {"month": 6, "event": "Announcement", "impact": "Initial speculation"},
    {"month": 24, "event": "Completion", "impact": "Value realization"}
  ],
  "assumptions": ["Assumption 1", "Assumption 2"],
  "historical_reference": "Similar case: [example] resulted in [X]% change",
  "recommendation": "Investment strategy recommendation"
}

## SCENARIO BENCHMARKS (Bangalore-specific)
- Metro station (0-500m): +18-30% over 24-36 months
- IT park (1km): +10-20% value, +2-3% rental yield
- School/Hospital: +5-12% in 1km radius
- Road widening: +5-10%, may have 1-2 year disruption dip
- Zoning change (residential→commercial): +20-40% but 3-5 year timeline

## RULES
- Base predictions on current state facts
- Always state confidence level
- Reference similar Bangalore cases when possible (Purple Line, ORR impact)
- Account for construction disruption in timeline""",

    "narrative": """# VALORA AI - NARRATIVE DIRECTOR

You are creating 3D cinematic storyboards for city exploration.

## OUTPUT FORMAT (JSON)
{
  "scenes": [
    {
      "id": 1,
      "camera": {
        "lat": 12.9716,
        "lng": 77.5946,
        "height": 500,
        "heading": 0,
        "pitch": -30
      },
      "duration_seconds": 5,
      "transition": "flyTo",
      "voiceover": "Welcome to Koramangala, Bangalore's startup hub..."
    }
  ],
  "total_duration": 30,
  "mood": "professional"
}

## RULES
- Voiceovers: 15-20 words max per scene
- Camera movements: Smooth, purposeful
- Scene count: 3-6 for typical tours
- Always start with establishing shot (high altitude)
- End with actionable insight
- Use Bangalore-specific landmarks and references"""
}


# =============================================================================
# GLOBAL INSTANCE & HELPERS
# =============================================================================

_client: Optional[OpenRouterClient] = None


def get_openrouter_client() -> OpenRouterClient:
    """Get or create global OpenRouter client."""
    global _client
    if _client is None:
        _client = OpenRouterClient()
    return _client


async def quick_chat(
    message: str,
    system_prompt: Optional[str] = None,
    model_type: ModelType = ModelType.PRIMARY,
    json_mode: bool = False,
) -> Union[str, Dict]:
    """
    Quick helper for simple chat requests.
    
    Args:
        message: User message
        system_prompt: Optional system prompt (defaults to chat prompt)
        model_type: Model type to use
        json_mode: Return JSON
        
    Returns:
        Response string or dict
    """
    client = get_openrouter_client()
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    else:
        messages.append({"role": "system", "content": VALORA_PROMPTS["chat"]})
    
    messages.append({"role": "user", "content": message})
    
    return await client.chat(
        messages=messages,
        model_type=model_type,
        json_mode=json_mode,
    )


# Model info for admin panel
MODEL_INFO = {
    "primary": {
        "id": "deepseek/deepseek-chat-v3-0324",
        "name": "DeepSeek V3.1 (671B)",
        "description": "Best value - GPT-4 level performance at 1/10th cost",
        "context": 64000,
        "cost_per_1m": "$0.27 input / $1.10 output"
    },
    "reasoning": {
        "id": "deepseek/deepseek-reasoner", 
        "name": "DeepSeek Reasoner",
        "description": "Chain-of-thought reasoning for complex analysis",
        "context": 64000,
        "cost_per_1m": "$0.55 input / $2.19 output"
    },
    "vision": {
        "id": "qwen/qwen2.5-vl-72b-instruct",
        "name": "Qwen 2.5 VL (72B)",
        "description": "Vision-language model for property images",
        "context": 32000,
        "cost_per_1m": "$0.40 input / $0.40 output"
    },
    "fallback": {
        "id": "anthropic/claude-3.5-sonnet",
        "name": "Claude 3.5 Sonnet",
        "description": "High-quality fallback model",
        "context": 200000,
        "cost_per_1m": "$3.00 input / $15.00 output"
    }
}
