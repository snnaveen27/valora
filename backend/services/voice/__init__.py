"""
Voice Services Module
Provides voice transcription and text-to-speech capabilities using Deepgram.
"""

from .deepgram_service import DeepgramService, VoiceTranscription

__all__ = ['DeepgramService', 'VoiceTranscription']
