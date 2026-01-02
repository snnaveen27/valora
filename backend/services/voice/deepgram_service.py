"""
Deepgram Voice Service
Provides real-time voice transcription and text-to-speech for Valora platform.
"""

import os
import json
import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import base64

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class TranscriptionLanguage(str, Enum):
    """Supported transcription languages"""
    ENGLISH_IN = "en-IN"  # Indian English
    ENGLISH_US = "en-US"
    ENGLISH_GB = "en-GB"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"
    KANNADA = "kn"
    MARATHI = "mr"


class VoiceModel(str, Enum):
    """Deepgram voice models"""
    NOVA_2 = "nova-2"  # Best accuracy
    NOVA_2_GENERAL = "nova-2-general"
    NOVA_2_MEETING = "nova-2-meeting"
    NOVA_2_PHONECALL = "nova-2-phonecall"
    ENHANCED = "enhanced"
    BASE = "base"


@dataclass
class VoiceTranscription:
    """Voice transcription result"""
    transcript: str
    confidence: float
    language: str
    duration_seconds: float
    words: List[Dict[str, Any]] = field(default_factory=list)
    is_final: bool = True
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transcript": self.transcript,
            "confidence": self.confidence,
            "language": self.language,
            "duration_seconds": self.duration_seconds,
            "words": self.words,
            "is_final": self.is_final,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class TTSResult:
    """Text-to-speech result"""
    audio_base64: str
    content_type: str
    duration_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "audio_base64": self.audio_base64,
            "content_type": self.content_type,
            "duration_seconds": self.duration_seconds
        }


class DeepgramService:
    """
    Deepgram voice service for transcription and TTS.
    
    Features:
    - Real-time streaming transcription
    - Pre-recorded audio transcription
    - Text-to-speech synthesis
    - Indian English optimization
    - Multi-language support
    """
    
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        self.base_url = "https://api.deepgram.com/v1"
        self.default_language = TranscriptionLanguage.ENGLISH_IN
        self.default_model = VoiceModel.NOVA_2
        
        # Real estate specific vocabulary for better accuracy
        self.real_estate_keywords = [
            "Whitefield", "Koramangala", "Indiranagar", "HSR Layout",
            "Electronic City", "Marathahalli", "Sarjapur", "Hebbal",
            "Jayanagar", "Bannerghatta", "Yelahanka", "Devanahalli",
            "crore", "lakh", "sqft", "BHK", "apartment", "villa",
            "plot", "commercial", "residential", "rental", "yield",
            "appreciation", "investment", "property", "locality",
            "metro", "infrastructure", "amenities", "BBMP", "RERA"
        ]
        
        # WebSocket connection for streaming
        self._ws_connection = None
        self._streaming_callback: Optional[Callable] = None
        
        if not self.api_key:
            logger.warning("DEEPGRAM_API_KEY not set. Voice features will be limited.")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _get_audio_headers(self, content_type: str = "audio/wav") -> Dict[str, str]:
        """Get headers for audio upload"""
        return {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": content_type
        }
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        content_type: str = "audio/wav",
        language: TranscriptionLanguage = TranscriptionLanguage.ENGLISH_IN,
        model: VoiceModel = VoiceModel.NOVA_2,
        punctuate: bool = True,
        smart_format: bool = True,
        diarize: bool = False
    ) -> VoiceTranscription:
        """
        Transcribe pre-recorded audio.
        
        Args:
            audio_data: Raw audio bytes
            content_type: MIME type of audio
            language: Transcription language
            model: Deepgram model to use
            punctuate: Add punctuation
            smart_format: Format numbers, dates, etc.
            diarize: Speaker diarization
            
        Returns:
            VoiceTranscription with results
        """
        if not self.api_key:
            return VoiceTranscription(
                transcript="[Voice service not configured]",
                confidence=0.0,
                language=language.value,
                duration_seconds=0.0
            )
        
        # Build query parameters
        params = {
            "model": model.value,
            "language": language.value,
            "punctuate": str(punctuate).lower(),
            "smart_format": str(smart_format).lower(),
            "diarize": str(diarize).lower(),
            "keywords": ":".join(self.real_estate_keywords[:20])  # Boost real estate terms
        }
        
        url = f"{self.base_url}/listen"
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query_string}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    full_url,
                    content=audio_data,
                    headers=self._get_audio_headers(content_type)
                )
                response.raise_for_status()
                result = response.json()
                
                # Parse response
                channel = result.get("results", {}).get("channels", [{}])[0]
                alternative = channel.get("alternatives", [{}])[0]
                
                transcript = alternative.get("transcript", "")
                confidence = alternative.get("confidence", 0.0)
                words = alternative.get("words", [])
                
                # Get duration from metadata
                metadata = result.get("metadata", {})
                duration = metadata.get("duration", 0.0)
                
                logger.info(f"Transcribed {duration:.1f}s audio: '{transcript[:50]}...'")
                
                return VoiceTranscription(
                    transcript=transcript,
                    confidence=confidence,
                    language=language.value,
                    duration_seconds=duration,
                    words=words,
                    is_final=True
                )
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Deepgram API error: {e.response.status_code} - {e.response.text}")
            return VoiceTranscription(
                transcript=f"[Transcription error: {e.response.status_code}]",
                confidence=0.0,
                language=language.value,
                duration_seconds=0.0
            )
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return VoiceTranscription(
                transcript=f"[Transcription failed: {str(e)}]",
                confidence=0.0,
                language=language.value,
                duration_seconds=0.0
            )
    
    async def transcribe_url(
        self,
        audio_url: str,
        language: TranscriptionLanguage = TranscriptionLanguage.ENGLISH_IN,
        model: VoiceModel = VoiceModel.NOVA_2
    ) -> VoiceTranscription:
        """
        Transcribe audio from URL.
        
        Args:
            audio_url: URL to audio file
            language: Transcription language
            model: Deepgram model
            
        Returns:
            VoiceTranscription with results
        """
        if not self.api_key:
            return VoiceTranscription(
                transcript="[Voice service not configured]",
                confidence=0.0,
                language=language.value,
                duration_seconds=0.0
            )
        
        params = {
            "model": model.value,
            "language": language.value,
            "punctuate": "true",
            "smart_format": "true"
        }
        
        url = f"{self.base_url}/listen"
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query_string}"
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    full_url,
                    json={"url": audio_url},
                    headers=self._get_headers()
                )
                response.raise_for_status()
                result = response.json()
                
                channel = result.get("results", {}).get("channels", [{}])[0]
                alternative = channel.get("alternatives", [{}])[0]
                
                return VoiceTranscription(
                    transcript=alternative.get("transcript", ""),
                    confidence=alternative.get("confidence", 0.0),
                    language=language.value,
                    duration_seconds=result.get("metadata", {}).get("duration", 0.0),
                    words=alternative.get("words", [])
                )
                
        except Exception as e:
            logger.error(f"URL transcription failed: {e}")
            return VoiceTranscription(
                transcript=f"[Transcription failed: {str(e)}]",
                confidence=0.0,
                language=language.value,
                duration_seconds=0.0
            )
    
    async def text_to_speech(
        self,
        text: str,
        voice: str = "aura-asteria-en",  # Female Indian English voice
        encoding: str = "mp3",
        sample_rate: int = 24000
    ) -> TTSResult:
        """
        Convert text to speech using Deepgram TTS.
        
        Args:
            text: Text to synthesize
            voice: Voice model (aura-asteria-en for Indian English)
            encoding: Audio encoding (mp3, wav, etc.)
            sample_rate: Audio sample rate
            
        Returns:
            TTSResult with audio data
        """
        if not self.api_key:
            return TTSResult(
                audio_base64="",
                content_type="audio/mp3",
                duration_seconds=0.0
            )
        
        url = f"{self.base_url}/speak"
        params = {
            "model": voice,
            "encoding": encoding,
            "sample_rate": sample_rate
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query_string}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    full_url,
                    json={"text": text},
                    headers=self._get_headers()
                )
                response.raise_for_status()
                
                audio_data = response.content
                audio_base64 = base64.b64encode(audio_data).decode("utf-8")
                
                # Estimate duration (rough: 150 words per minute)
                word_count = len(text.split())
                estimated_duration = word_count / 2.5  # ~150 wpm
                
                return TTSResult(
                    audio_base64=audio_base64,
                    content_type=f"audio/{encoding}",
                    duration_seconds=estimated_duration
                )
                
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            return TTSResult(
                audio_base64="",
                content_type="audio/mp3",
                duration_seconds=0.0
            )
    
    def get_streaming_url(
        self,
        language: TranscriptionLanguage = TranscriptionLanguage.ENGLISH_IN,
        model: VoiceModel = VoiceModel.NOVA_2,
        interim_results: bool = True
    ) -> str:
        """
        Get WebSocket URL for real-time streaming transcription.
        
        Args:
            language: Transcription language
            model: Deepgram model
            interim_results: Include interim results
            
        Returns:
            WebSocket URL for streaming
        """
        params = {
            "model": model.value,
            "language": language.value,
            "punctuate": "true",
            "smart_format": "true",
            "interim_results": str(interim_results).lower(),
            "endpointing": "300",  # 300ms silence = end of utterance
            "vad_events": "true"
        }
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"wss://api.deepgram.com/v1/listen?{query_string}"
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages"""
        return [
            {"code": "en-IN", "name": "English (India)", "recommended": True},
            {"code": "en-US", "name": "English (US)", "recommended": False},
            {"code": "hi", "name": "Hindi", "recommended": True},
            {"code": "ta", "name": "Tamil", "recommended": False},
            {"code": "te", "name": "Telugu", "recommended": False},
            {"code": "kn", "name": "Kannada", "recommended": False},
            {"code": "mr", "name": "Marathi", "recommended": False}
        ]
    
    def get_voice_commands(self) -> List[Dict[str, Any]]:
        """Get supported voice commands for the platform"""
        return [
            {
                "category": "Search",
                "commands": [
                    {"phrase": "Find properties in [location]", "example": "Find properties in Whitefield"},
                    {"phrase": "Search [X] BHK in [location]", "example": "Search 3 BHK in Koramangala"},
                    {"phrase": "Show apartments under [X] crore", "example": "Show apartments under 2 crore"}
                ]
            },
            {
                "category": "Map",
                "commands": [
                    {"phrase": "Show map of [location]", "example": "Show map of Electronic City"},
                    {"phrase": "Draw circle around [location]", "example": "Draw circle around Manyata Tech Park"},
                    {"phrase": "Zoom in / Zoom out", "example": "Zoom in"},
                    {"phrase": "Show nearby [amenity]", "example": "Show nearby metro stations"}
                ]
            },
            {
                "category": "Analysis",
                "commands": [
                    {"phrase": "Predict price for [location]", "example": "Predict price for HSR Layout"},
                    {"phrase": "What is the growth rate of [location]", "example": "What is the growth rate of Sarjapur"},
                    {"phrase": "Compare [location1] and [location2]", "example": "Compare Whitefield and Electronic City"},
                    {"phrase": "Show investment hotspots", "example": "Show investment hotspots"}
                ]
            },
            {
                "category": "General",
                "commands": [
                    {"phrase": "Help", "example": "Help"},
                    {"phrase": "Clear chat", "example": "Clear chat"},
                    {"phrase": "Stop listening", "example": "Stop listening"}
                ]
            }
        ]
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Deepgram API health"""
        if not self.api_key:
            return {
                "status": "unconfigured",
                "message": "DEEPGRAM_API_KEY not set",
                "features": {
                    "transcription": False,
                    "streaming": False,
                    "tts": False
                }
            }
        
        try:
            # Test with a simple API call
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/projects",
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "message": "Deepgram API connected",
                        "features": {
                            "transcription": True,
                            "streaming": True,
                            "tts": True
                        }
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"API returned {response.status_code}",
                        "features": {
                            "transcription": False,
                            "streaming": False,
                            "tts": False
                        }
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "features": {
                    "transcription": False,
                    "streaming": False,
                    "tts": False
                }
            }


# Singleton instance
_deepgram_service: Optional[DeepgramService] = None


def get_deepgram_service() -> DeepgramService:
    """Get singleton Deepgram service instance"""
    global _deepgram_service
    if _deepgram_service is None:
        _deepgram_service = DeepgramService()
    return _deepgram_service
