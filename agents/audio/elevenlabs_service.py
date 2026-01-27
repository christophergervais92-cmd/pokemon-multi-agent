#!/usr/bin/env python3
"""
ElevenLabs Audio Service

Generates high-quality voiceovers with word-level timestamps
for perfect caption synchronization.
"""
import os
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from agents.utils.logger import get_logger

logger = get_logger("elevenlabs")

# Try to import ElevenLabs
try:
    from elevenlabs import ElevenLabs, Voice, VoiceSettings
    HAS_ELEVENLABS = True
except ImportError:
    HAS_ELEVENLABS = False
    logger.warning("elevenlabs package not installed. Using demo mode.")


class ElevenLabsService:
    """
    ElevenLabs text-to-speech service with timestamp generation.
    
    Features:
    - High-quality voiceover generation
    - Word-level timestamps for captions
    - Multiple voice options
    - Audio file management
    """
    
    # Voice presets for different styles
    VOICE_PRESETS = {
        "documentary": "21m00Tcm4TlvDq8ikWAM",  # Rachel - calm, clear
        "energetic": "EXAVITQu4vr4xnSDxMaL",    # Bella - energetic
        "storytelling": "pNInz6obpgDQGcFmaJgB", # Adam - deep, narrative
        "female_warm": "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "male_deep": "pNInz6obpgDQGcFmaJgB",    # Adam
    }
    
    def __init__(self, output_dir: str = "remotion/public/audio/generated"):
        """
        Initialize ElevenLabs service.
        
        Args:
            output_dir: Directory to save generated audio files
        """
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if self.api_key and HAS_ELEVENLABS:
            self.client = ElevenLabs(api_key=self.api_key)
            self.mode = "live"
            logger.info("ElevenLabs service initialized in live mode")
        else:
            self.client = None
            self.mode = "demo"
            logger.warning("ElevenLabs service initialized in demo mode (no API key)")
    
    def generate_voiceover(
        self,
        script: str,
        voice_style: str = "documentary",
        output_filename: Optional[str] = None
    ) -> Dict:
        """
        Generate voiceover from script with timestamps.
        
        Args:
            script: Text to convert to speech
            voice_style: Voice preset (documentary, energetic, storytelling)
            output_filename: Custom filename (auto-generated if None)
        
        Returns:
            Dict with: audio_path, duration, timestamps, word_count
        """
        if self.mode == "demo":
            return self._generate_demo(script, output_filename)
        
        try:
            # Get voice ID
            voice_id = self.VOICE_PRESETS.get(voice_style, self.VOICE_PRESETS["documentary"])
            
            # Generate audio with alignment (timestamps)
            logger.info(f"Generating voiceover with {voice_style} voice...")
            
            response = self.client.text_to_speech.convert_with_timestamps(
                voice_id=voice_id,
                text=script,
                model_id="eleven_multilingual_v2",
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.5,
                    use_speaker_boost=True
                )
            )
            
            # Save audio file
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"voiceover_{timestamp}.mp3"
            
            audio_path = self.output_dir / output_filename
            
            # Write audio data
            with open(audio_path, 'wb') as f:
                for chunk in response.audio_iterator:
                    f.write(chunk)
            
            # Get alignment data (timestamps)
            alignment = response.alignment
            
            # Process timestamps
            timestamps = self._process_timestamps(alignment, script)
            
            result = {
                'audio_path': str(audio_path),
                'duration': timestamps[-1]['end'] if timestamps else 0,
                'timestamps': timestamps,
                'word_count': len(script.split()),
                'voice_style': voice_style,
                'generated_at': datetime.now().isoformat()
            }
            
            # Save metadata
            metadata_path = audio_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"Generated voiceover: {audio_path} ({result['duration']:.2f}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"ElevenLabs generation failed: {e}")
            return self._generate_demo(script, output_filename)
    
    def _process_timestamps(self, alignment: Dict, script: str) -> List[Dict]:
        """
        Process ElevenLabs alignment data into word timestamps.
        
        Args:
            alignment: ElevenLabs alignment data
            script: Original script text
        
        Returns:
            List of {word, start, end} dictionaries
        """
        timestamps = []
        
        if not alignment or not hasattr(alignment, 'characters'):
            # Fallback: estimate timestamps
            return self._estimate_timestamps(script)
        
        words = script.split()
        current_word = ""
        word_start = 0
        
        for i, char_data in enumerate(alignment.characters):
            char = char_data.character
            start_time = char_data.start_time_ms / 1000.0  # Convert to seconds
            
            if char.isspace() or char in '.,!?;:':
                if current_word:
                    timestamps.append({
                        'word': current_word,
                        'start': word_start,
                        'end': start_time
                    })
                    current_word = ""
            else:
                if not current_word:
                    word_start = start_time
                current_word += char
        
        # Add last word
        if current_word:
            end_time = alignment.characters[-1].start_time_ms / 1000.0
            timestamps.append({
                'word': current_word,
                'start': word_start,
                'end': end_time
            })
        
        return timestamps
    
    def _estimate_timestamps(self, script: str, words_per_second: float = 2.5) -> List[Dict]:
        """
        Estimate timestamps based on average speaking rate.
        
        Args:
            script: Script text
            words_per_second: Average speaking rate
        
        Returns:
            List of estimated timestamps
        """
        words = script.split()
        timestamps = []
        current_time = 0.0
        
        for word in words:
            word_duration = 1.0 / words_per_second
            # Add extra time for punctuation
            if word[-1] in '.,!?;:':
                word_duration += 0.2
            
            timestamps.append({
                'word': word,
                'start': current_time,
                'end': current_time + word_duration
            })
            
            current_time += word_duration
        
        return timestamps
    
    def _generate_demo(self, script: str, output_filename: Optional[str]) -> Dict:
        """
        Generate demo response without actual audio generation.
        For testing without ElevenLabs API key.
        """
        logger.info("Generating demo voiceover (no actual audio)")
        
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"voiceover_demo_{timestamp}.mp3"
        
        audio_path = self.output_dir / output_filename
        
        # Create empty audio file
        audio_path.touch()
        
        # Estimate timestamps
        timestamps = self._estimate_timestamps(script)
        duration = timestamps[-1]['end'] if timestamps else 0
        
        result = {
            'audio_path': str(audio_path),
            'duration': duration,
            'timestamps': timestamps,
            'word_count': len(script.split()),
            'voice_style': 'demo',
            'generated_at': datetime.now().isoformat(),
            'demo_mode': True
        }
        
        # Save metadata
        metadata_path = audio_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.warning(f"Demo voiceover created: {audio_path}")
        
        return result
    
    def get_available_voices(self) -> List[Dict]:
        """Get list of available ElevenLabs voices."""
        if self.mode == "demo":
            return [
                {"id": k, "name": k.replace("_", " ").title(), "preset": True}
                for k in self.VOICE_PRESETS.keys()
            ]
        
        try:
            voices = self.client.voices.get_all()
            return [
                {
                    "id": voice.voice_id,
                    "name": voice.name,
                    "category": voice.category,
                    "preset": voice.voice_id in self.VOICE_PRESETS.values()
                }
                for voice in voices.voices
            ]
        except Exception as e:
            logger.error(f"Failed to fetch voices: {e}")
            return []
    
    def generate_with_retry(
        self,
        script: str,
        voice_style: str = "documentary",
        max_retries: int = 3
    ) -> Optional[Dict]:
        """
        Generate voiceover with automatic retry on failure.
        
        Args:
            script: Text to convert
            voice_style: Voice preset
            max_retries: Maximum retry attempts
        
        Returns:
            Result dict or None if all retries fail
        """
        for attempt in range(max_retries):
            try:
                result = self.generate_voiceover(script, voice_style)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"All {max_retries} attempts failed")
                    return None
        
        return None


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    service = ElevenLabsService()
    
    # Test script
    script = """Watch this! In Mongolia's Altai Mountains, eagle hunters train golden eagles 
    to hunt foxes and rabbits. This tradition dates back 4,000 years. Follow for more!"""
    
    # Generate voiceover
    result = service.generate_voiceover(script, voice_style="documentary")
    
    print(f"\nGenerated: {result['audio_path']}")
    print(f"Duration: {result['duration']:.2f}s")
    print(f"Words: {result['word_count']}")
    print(f"\nFirst 5 timestamps:")
    for ts in result['timestamps'][:5]:
        print(f"  {ts['start']:.2f}s - {ts['end']:.2f}s: {ts['word']}")
