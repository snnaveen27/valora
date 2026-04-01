"""
Ollama Client for Local LLM Integration
Provides async interface to local Ollama models.
"""

import asyncio
import aiohttp
import json
import os
import re
from typing import Optional, Dict, Any, AsyncGenerator


class OllamaClient:
    """
    Async client for Ollama local LLM server.
    Supports text generation and streaming.
    """
    
    def __init__(self, 
                 model: str = "valora-ai-mini:latest",
                 base_url: str = "http://localhost:11434",
                 timeout: int = 120,
                 max_context: int = 8192):
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout  # 120s for local 8B model inference
        self.max_context = max_context  # Context window size, 0 means unlimited
        self.api_url = f"{self.base_url}/api/generate"

    def _create_session(self, timeout: aiohttp.ClientTimeout) -> aiohttp.ClientSession:
        connector = None
        if os.name == "nt":
            connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
        return aiohttp.ClientSession(timeout=timeout, connector=connector)

    @staticmethod
    def _clean_text(text: Optional[str]) -> str:
        """Strip reasoning tags and partial thinking output from model text."""
        if not text:
            return ""
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()
        if "<think>" in cleaned.lower():
            cleaned = re.split(r"<think>", cleaned, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        return cleaned
    
    async def generate(self, 
                      prompt: str,
                      system: Optional[str] = None,
                      temperature: float = 0.7,
                      max_tokens: int = 1024,
                      **kwargs) -> str:
        """
        Generate text using Ollama model.
        
        Args:
            prompt: The prompt text
            system: System message (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        think = kwargs.pop("think", False)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": think,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": self.max_context if self.max_context > 0 else 2048,  # Use 0 for unlimited, fallback to 2048
            }
        }
        
        if system:
            payload["system"] = system
        
        # Add any additional options
        for key, value in kwargs.items():
            if key not in payload["options"]:
                payload["options"][key] = value
        
        try:
            async with self._create_session(aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama error {response.status}: {error_text}")
                    
                    result = await response.json()
                    text = self._clean_text(result.get("response", ""))
                    if text:
                        return text

                    # Some Ollama-hosted cloud models return empty /api/generate content
                    # while /api/chat succeeds with the same prompt.
                    chat_messages = [{"role": "user", "content": prompt}]
                    if system:
                        chat_messages.insert(0, {"role": "system", "content": system})
                    return await self.chat(
                        messages=chat_messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs,
                    )
                    
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to connect to Ollama at {self.base_url}: {e}")
        except asyncio.TimeoutError:
            raise Exception(f"Ollama timed out after {self.timeout}s - model may be overloaded")
        except Exception as e:
            if "Ollama" in str(e):
                raise  # Re-raise our own exceptions
            raise Exception(f"Ollama generation failed: {e}")
    
    async def generate_stream(self,
                             prompt: str,
                             system: Optional[str] = None,
                             temperature: float = 0.7,
                             max_tokens: int = 1024,
                             **kwargs) -> AsyncGenerator[str, None]:
        """
        Stream text generation from Ollama.
        
        Args:
            prompt: The prompt text
            system: System message (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Yields:
            Chunks of generated text
        """
        think = kwargs.pop("think", False)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "think": think,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": self.max_context if self.max_context > 0 else 2048,  # Use 0 for unlimited, fallback to 2048
            }
        }
        
        if system:
            payload["system"] = system
        
        for key, value in kwargs.items():
            if key not in payload["options"]:
                payload["options"][key] = value
        
        try:
            async with self._create_session(aiohttp.ClientTimeout(total=self.timeout, sock_read=self.timeout)) as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout, sock_read=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama error {response.status}: {error_text}")
                    
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line)
                                chunk = data.get("response", "")
                                if chunk:
                                    yield chunk
                                
                                # Check if done
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
                                
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to connect to Ollama: {e}")
        except Exception as e:
            raise Exception(f"Ollama streaming failed: {e}")
    
    async def chat(self,
                  messages: list,
                  temperature: float = 0.7,
                  max_tokens: int = 1024,
                  **kwargs) -> str:
        """
        Chat using Ollama /api/chat with proper message roles.
        Uses the model's native chat template (ChatML for Qwen3).
        
        Args:
            messages: List of {"role": str, "content": str} dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        think = kwargs.pop("think", False)
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": think,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": self.max_context if self.max_context > 0 else 2048,  # Use 0 for unlimited, fallback to 2048
            }
        }
        
        for key, value in kwargs.items():
            if key not in payload["options"]:
                payload["options"][key] = value
        
        chat_url = f"{self.base_url}/api/chat"
        
        try:
            async with self._create_session(aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    chat_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama chat error {response.status}: {error_text}")
                    
                    result = await response.json()
                    text = self._clean_text(result.get("message", {}).get("content", ""))
                    return text
                    
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to connect to Ollama at {self.base_url}: {e}")
        except asyncio.TimeoutError:
            raise Exception(f"Ollama chat timed out after {self.timeout}s")
        except Exception as e:
            if "Ollama" in str(e):
                raise
            raise Exception(f"Ollama chat failed: {e}")
    
    async def chat_stream(self,
                         messages: list,
                         temperature: float = 0.7,
                         max_tokens: int = 1024,
                         **kwargs) -> AsyncGenerator[str, None]:
        """
        Stream chat from Ollama /api/chat with proper message roles.
        Uses the model's native chat template (ChatML for Qwen3).
        
        Args:
            messages: List of {"role": str, "content": str} dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Yields:
            Chunks of generated text
        """
        think = kwargs.pop("think", False)
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "think": think,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": self.max_context if self.max_context > 0 else 2048,  # Use 0 for unlimited, fallback to 2048
            }
        }
        
        for key, value in kwargs.items():
            if key not in payload["options"]:
                payload["options"][key] = value
        
        chat_url = f"{self.base_url}/api/chat"
        
        try:
            async with self._create_session(aiohttp.ClientTimeout(total=self.timeout, sock_read=self.timeout)) as session:
                async with session.post(
                    chat_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout, sock_read=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama chat error {response.status}: {error_text}")
                    
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line)
                                chunk = data.get("message", {}).get("content", "")
                                if chunk:
                                    yield chunk
                                
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
                                
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to connect to Ollama chat: {e}")
        except Exception as e:
            raise Exception(f"Ollama chat streaming failed: {e}")
    
    async def classify_intent(self, query: str, 
                             intents: list = None) -> tuple[str, float]:
        """
        Classify intent using local model.
        
        Args:
            query: User query
            intents: List of possible intents (optional)
            
        Returns:
            Tuple of (intent, confidence)
        """
        if intents is None:
            intents = [
                "navigate", "analyze_area", "analyze_building", 
                "property_search", "valuation", "terrain", 
                "comparison", "simulate", "general"
            ]
        
        prompt = f"""Classify the user query into one of these intents: {', '.join(intents)}

User Query: "{query}"

Respond with JSON: {{"intent": "...", "confidence": 0.0-1.0}}"""
        
        try:
            response = await self.generate(prompt, temperature=0.1, max_tokens=100)
            
            # Extract JSON
            json_str = response
            if '{' in json_str:
                start = json_str.find('{')
                end = json_str.rfind('}') + 1
                json_str = json_str[start:end]
            
            result = json.loads(json_str)
            intent = result.get("intent", "general")
            confidence = result.get("confidence", 0.5)
            
            # Validate intent
            if intent not in intents:
                intent = "general"
            
            return intent, confidence
            
        except Exception as e:
            # Fallback to pattern matching
            return self._pattern_classify(query, intents), 0.5
    
    def _pattern_classify(self, query: str, intents: list) -> str:
        """Fallback pattern-based classification."""
        q = query.lower()
        
        patterns = {
            'navigate': ['show me', 'go to', 'where is', 'navigate to'],
            'analyze_area': ['what\'s the area', 'how is', 'analyze this', 'tell me about'],
            'analyze_building': ['this building', 'the building', 'analyze building'],
            'property_search': ['find', 'search', 'apartments', 'properties', 'flats', 'looking for'],
            'valuation': ['price', 'value', 'cost', 'worth', 'estimate', 'how much'],
            'terrain': ['elevation', 'flood', 'slope', 'terrain', 'height', 'ground'],
            'comparison': ['compare', 'versus', 'vs', 'better than', 'difference between'],
            'simulate': ['what if', 'simulate', 'scenario', 'add a', 'build a'],
        }
        
        for intent, keywords in patterns.items():
            if intent in intents and any(kw in q for kw in keywords):
                return intent
        
        return 'general'
    
    async def health_check(self) -> bool:
        """Check if Ollama server is running and model is available."""
        try:
            async with self._create_session(aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        return any(m.get("name") == self.model for m in models)
                    return False
        except Exception:
            return False
    
    async def list_models(self) -> list:
        """List available models on Ollama server."""
        try:
            async with self._create_session(aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [m.get("name") for m in data.get("models", [])]
                    return []
        except Exception:
            return []


# Singleton instance
_ollama_client = None

def get_ollama_client(model: str = None) -> OllamaClient:
    """Get singleton Ollama client instance.

    Args:
        model: Model name (optional, reads from llm_config.json if not provided)
    """
    global _ollama_client
    if _ollama_client is None:
        # Load from config if model not specified
        if model is None:
            try:
                import json
                from pathlib import Path
                config_path = Path(__file__).parent.parent / "llm_config.json"
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        model = config.get("local_model", "valora-ai-mini:latest")
                        max_context = config.get("max_context", 8192)
                else:
                    model = "valora-ai-mini:latest"
                    max_context = 8192
            except Exception:
                model = "valora-ai-mini:latest"
                max_context = 8192
        else:
            max_context = 8192  # default if model is specified
        
        _ollama_client = OllamaClient(model=model, max_context=max_context)
    return _ollama_client
