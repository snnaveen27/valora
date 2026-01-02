"""
Voice API Endpoints
Provides REST and WebSocket endpoints for voice transcription and TTS.
"""

import os
import json
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import base64

from backend.services.voice import DeepgramService, get_deepgram_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/voice", tags=["Voice"])


class TranscribeRequest(BaseModel):
    """Request for audio transcription from base64"""
    audio_base64: str = Field(..., description="Base64 encoded audio data")
    content_type: str = Field(default="audio/wav", description="MIME type of audio")
    language: str = Field(default="en-IN", description="Language code")


class TranscribeUrlRequest(BaseModel):
    """Request for audio transcription from URL"""
    audio_url: str = Field(..., description="URL to audio file")
    language: str = Field(default="en-IN", description="Language code")


class TTSRequest(BaseModel):
    """Request for text-to-speech"""
    text: str = Field(..., description="Text to synthesize", max_length=5000)
    voice: str = Field(default="aura-asteria-en", description="Voice model")
    encoding: str = Field(default="mp3", description="Audio encoding")


class StreamingConfig(BaseModel):
    """Configuration for streaming transcription"""
    language: str = Field(default="en-IN")
    interim_results: bool = Field(default=True)


@router.get("/health")
async def voice_health_check():
    """Check voice service health"""
    service = get_deepgram_service()
    health = await service.health_check()
    return health


@router.get("/languages")
async def get_supported_languages():
    """Get list of supported transcription languages"""
    service = get_deepgram_service()
    return {
        "languages": service.get_supported_languages(),
        "default": "en-IN"
    }


@router.get("/commands")
async def get_voice_commands():
    """Get list of supported voice commands"""
    service = get_deepgram_service()
    return {
        "commands": service.get_voice_commands()
    }


@router.post("/transcribe")
async def transcribe_audio(request: TranscribeRequest):
    """
    Transcribe base64 encoded audio.
    
    Supports: WAV, MP3, WebM, OGG, FLAC
    """
    try:
        # Decode base64 audio
        audio_data = base64.b64decode(request.audio_base64)
        
        service = get_deepgram_service()
        result = await service.transcribe_audio(
            audio_data=audio_data,
            content_type=request.content_type,
            language=request.language
        )
        
        return {
            "success": True,
            "transcription": result.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe/upload")
async def transcribe_uploaded_audio(
    file: UploadFile = File(...),
    language: str = Query(default="en-IN", description="Language code")
):
    """
    Transcribe uploaded audio file.
    
    Supports: WAV, MP3, WebM, OGG, FLAC, M4A
    """
    try:
        # Read file content
        audio_data = await file.read()
        content_type = file.content_type or "audio/wav"
        
        service = get_deepgram_service()
        result = await service.transcribe_audio(
            audio_data=audio_data,
            content_type=content_type,
            language=language
        )
        
        return {
            "success": True,
            "filename": file.filename,
            "transcription": result.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Upload transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe/url")
async def transcribe_from_url(request: TranscribeUrlRequest):
    """Transcribe audio from URL"""
    try:
        service = get_deepgram_service()
        result = await service.transcribe_url(
            audio_url=request.audio_url,
            language=request.language
        )
        
        return {
            "success": True,
            "transcription": result.to_dict()
        }
        
    except Exception as e:
        logger.error(f"URL transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech.
    
    Returns base64 encoded audio.
    """
    try:
        service = get_deepgram_service()
        result = await service.text_to_speech(
            text=request.text,
            voice=request.voice,
            encoding=request.encoding
        )
        
        if not result.audio_base64:
            raise HTTPException(status_code=500, detail="TTS generation failed")
        
        return {
            "success": True,
            "audio": result.to_dict()
        }
        
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/streaming/config")
async def get_streaming_config(
    language: str = Query(default="en-IN"),
    interim_results: bool = Query(default=True)
):
    """
    Get WebSocket URL and configuration for real-time streaming.
    
    Client should connect to the returned WebSocket URL with the API key.
    """
    service = get_deepgram_service()
    api_key = os.getenv("DEEPGRAM_API_KEY", "")
    
    if not api_key:
        raise HTTPException(
            status_code=503, 
            detail="Voice service not configured. Set DEEPGRAM_API_KEY."
        )
    
    ws_url = service.get_streaming_url(
        language=language,
        interim_results=interim_results
    )
    
    return {
        "websocket_url": ws_url,
        "api_key": api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***",
        "config": {
            "language": language,
            "interim_results": interim_results,
            "sample_rate": 16000,
            "encoding": "linear16",
            "channels": 1
        },
        "instructions": {
            "1": "Connect to websocket_url with Authorization header",
            "2": "Send audio chunks as binary messages",
            "3": "Receive JSON transcription results",
            "4": "Send {'type': 'CloseStream'} to end"
        }
    }


@router.websocket("/stream")
async def websocket_transcription(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming transcription.
    
    Protocol:
    1. Connect with ?language=en-IN query param
    2. Send audio chunks as binary
    3. Receive JSON with transcription results
    4. Send "STOP" text message to end
    """
    await websocket.accept()
    
    service = get_deepgram_service()
    api_key = os.getenv("DEEPGRAM_API_KEY")
    
    if not api_key:
        await websocket.send_json({
            "error": "Voice service not configured",
            "code": "NO_API_KEY"
        })
        await websocket.close()
        return
    
    # Get language from query params
    language = websocket.query_params.get("language", "en-IN")
    
    # Buffer for accumulating audio
    audio_buffer = bytearray()
    
    try:
        await websocket.send_json({
            "status": "connected",
            "message": "Send audio chunks as binary. Send 'STOP' to end and get final transcription.",
            "language": language
        })
        
        while True:
            # Receive message
            message = await websocket.receive()
            
            if message["type"] == "websocket.disconnect":
                break
            
            if "text" in message:
                text = message["text"]
                if text.upper() == "STOP":
                    # Process accumulated audio
                    if audio_buffer:
                        result = await service.transcribe_audio(
                            audio_data=bytes(audio_buffer),
                            content_type="audio/webm",
                            language=language
                        )
                        await websocket.send_json({
                            "type": "final",
                            "transcription": result.to_dict()
                        })
                    break
                else:
                    # Try to parse as config update
                    try:
                        config = json.loads(text)
                        if "language" in config:
                            language = config["language"]
                            await websocket.send_json({
                                "type": "config_updated",
                                "language": language
                            })
                    except:
                        pass
            
            elif "bytes" in message:
                # Accumulate audio data
                audio_buffer.extend(message["bytes"])
                
                # Send interim result every ~1 second of audio (assuming 16kHz, 16-bit)
                if len(audio_buffer) > 32000:  # ~1 second
                    result = await service.transcribe_audio(
                        audio_data=bytes(audio_buffer),
                        content_type="audio/webm",
                        language=language
                    )
                    await websocket.send_json({
                        "type": "interim",
                        "transcription": result.to_dict()
                    })
                    # Keep last 0.5 seconds for context
                    audio_buffer = audio_buffer[-16000:]
    
    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}")
        await websocket.send_json({
            "error": str(e),
            "code": "STREAM_ERROR"
        })
    finally:
        try:
            await websocket.close()
        except:
            pass


@router.get("/voices")
async def get_available_voices():
    """Get available TTS voices"""
    return {
        "voices": [
            {
                "id": "aura-asteria-en",
                "name": "Asteria",
                "language": "English",
                "gender": "Female",
                "accent": "Indian",
                "recommended": True
            },
            {
                "id": "aura-luna-en",
                "name": "Luna",
                "language": "English",
                "gender": "Female",
                "accent": "American",
                "recommended": False
            },
            {
                "id": "aura-stella-en",
                "name": "Stella",
                "language": "English",
                "gender": "Female",
                "accent": "British",
                "recommended": False
            },
            {
                "id": "aura-orion-en",
                "name": "Orion",
                "language": "English",
                "gender": "Male",
                "accent": "American",
                "recommended": False
            },
            {
                "id": "aura-arcas-en",
                "name": "Arcas",
                "language": "English",
                "gender": "Male",
                "accent": "American",
                "recommended": False
            }
        ],
        "default": "aura-asteria-en"
    }
