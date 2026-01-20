"""
Audio Narrator - TTS Pipeline for Voiceover Generation
Generates synchronized voiceover for storyboard steps using offline TTS
"""

from typing import Optional
from pathlib import Path
import hashlib
import json

class AudioNarrator:
    """Offline TTS pipeline for storyboard narration"""
    
    def __init__(self, cache_dir: str = "backend/audio_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.tts_available = self._check_tts_availability()
    
    def _check_tts_availability(self) -> bool:
        """Check if TTS engine is available"""
        try:
            import pyttsx3
            return True
        except ImportError:
            print("Warning: pyttsx3 not installed. Audio narration disabled.")
            print("Install with: pip install pyttsx3")
            return False
    
    def generate_audio(self, text: str, step_id: str) -> Optional[str]:
        """
        Generate audio file for narration text
        
        Args:
            text: Narration text to convert to speech
            step_id: Unique identifier for this step
            
        Returns:
            Path to generated audio file, or None if TTS unavailable
        """
        if not self.tts_available:
            return None
        
        # Generate cache key from text
        text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        audio_filename = f"{step_id}_{text_hash}.mp3"
        audio_path = self.cache_dir / audio_filename
        
        # Return cached file if exists
        if audio_path.exists():
            return f"/audio/{audio_filename}"
        
        # Generate new audio file
        try:
            import pyttsx3
            engine = pyttsx3.init()
            
            # Configure voice properties
            engine.setProperty('rate', 150)  # Speed (words per minute)
            engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
            
            # Try to use a pleasant voice
            voices = engine.getProperty('voices')
            if len(voices) > 1:
                # Prefer female voice (usually index 1)
                engine.setProperty('voice', voices[1].id)
            
            # Save to file
            engine.save_to_file(text, str(audio_path))
            engine.runAndWait()
            
            return f"/audio/{audio_filename}"
        
        except Exception as e:
            print(f"Error generating audio: {e}")
            return None
    
    def generate_storyboard_audio(self, storyboard: dict) -> dict:
        """
        Generate audio for all steps in a storyboard
        
        Args:
            storyboard: Storyboard dictionary with steps
            
        Returns:
            Updated storyboard with audio_url for each step
        """
        if not self.tts_available:
            return storyboard
        
        steps = storyboard.get('steps', [])
        
        for i, step in enumerate(steps):
            narration = step.get('narration', '')
            if narration:
                step_id = f"step_{i}"
                audio_url = self.generate_audio(narration, step_id)
                if audio_url:
                    step['audio_url'] = audio_url
        
        return storyboard
    
    def estimate_duration(self, text: str) -> int:
        """
        Estimate audio duration in milliseconds
        
        Args:
            text: Narration text
            
        Returns:
            Estimated duration in milliseconds
        """
        # Rough estimate: 150 words per minute = 2.5 words per second
        word_count = len(text.split())
        duration_seconds = word_count / 2.5
        return int(duration_seconds * 1000)
    
    def clear_cache(self):
        """Clear audio cache"""
        for audio_file in self.cache_dir.glob("*.mp3"):
            audio_file.unlink()
        print(f"Cleared audio cache: {self.cache_dir}")

# Singleton instance
_audio_narrator = None

def get_audio_narrator() -> AudioNarrator:
    """Get or create audio narrator singleton"""
    global _audio_narrator
    if _audio_narrator is None:
        _audio_narrator = AudioNarrator()
    return _audio_narrator
