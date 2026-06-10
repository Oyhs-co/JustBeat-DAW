"""Audio Player - Real-time audio playback using sounddevice.

This module provides a concrete implementation of the AudioPort interface
that connects to the system's audio output using sounddevice.
"""

import logging
import threading
import time
from typing import Optional, Dict

import numpy as np

logger = logging.getLogger(__name__)


# Try to import sounddevice
try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
    logger.warning("sounddevice not available, audio playback disabled")


class AudioPlayer:
    """Real-time audio player using sounddevice.
    
    This class provides audio playback by integrating with the PolyphonicSynth
    and routing the output through sounddevice's OutputStream.
    
    Attributes:
        sample_rate: Audio sample rate (default: 44100)
        buffer_size: Buffer size for audio callback
    """
    
    def __init__(
        self,
        synth,
        sample_rate: int = 44100,
        buffer_size: int = 256
    ):
        """Initialize the audio player.
        
        Args:
            synth: PolyphonicSynth instance for generating audio
            sample_rate: Audio sample rate
            buffer_size: Buffer size for callback
        """
        self._synth = synth
        self._sample_rate = sample_rate
        self._buffer_size = buffer_size
        
        self._stream: Optional[sd.OutputStream] = None
        self._is_running = False
        self._lock = threading.Lock()
        
        # Metronome
        self._metronome_enabled = False
        self._metronome_volume = 0.3
        self._last_beat = -1
        
        # BPM tracking
        self._bpm = 120
        self._beats_per_sample = 0
        
        logger.info(f"AudioPlayer initialized: rate={sample_rate}, buffer={buffer_size}")
    
    def _calculate_beat_interval(self) -> float:
        """Calculate samples per beat based on BPM."""
        return self._sample_rate * 60.0 / self._bpm
    
    def start(self) -> bool:
        """Start the audio stream.
        
        Returns:
            True if started successfully
        """
        if not HAS_SOUNDDEVICE:
            logger.error("Cannot start: sounddevice not available")
            return False
        
        if self._is_running:
            logger.warning("Audio player already running")
            return True
        
        try:
            self._stream = sd.OutputStream(
                samplerate=self._sample_rate,
                blocksize=self._buffer_size,
                channels=2,
                dtype='float32',
                callback=self._audio_callback
            )
            self._stream.start()
            self._is_running = True
            self._beats_per_sample = self._calculate_beat_interval()
            logger.info("Audio stream started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            self._stream = None
            return False
    
    def stop(self) -> None:
        """Stop the audio stream."""
        if not self._is_running:
            return
        
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            self._is_running = False
            logger.info("Audio stream stopped")
        except Exception as e:
            logger.warning(f"Error stopping audio stream: {e}")
    
    def _audio_callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time_info: sd.CallbackInfo
    ) -> None:
        """Callback function for sounddevice stream.
        
        This is called periodically to generate audio samples.
        
        Args:
            outdata: Output buffer to write audio to
            frames: Number of frames to generate
            time_info: Callback timing information
        """
        try:
            # Generate audio from synth
            audio = self._synth.process(frames)
            
            # Apply soft clipping
            audio = np.tanh(audio * 0.8)
            
            # Convert to stereo
            stereo = np.column_stack([audio, audio])
            
            # Add metronome if enabled
            if self._metronome_enabled:
                self._add_metronome(outdata, frames, time_info.inputBufferAdcTime)
            else:
                outdata[:] = stereo.astype(np.float32)
                
        except Exception as e:
            logger.error(f"Error in audio callback: {e}")
            outdata[:] = 0
    
    def _add_metronome(
        self,
        outdata: np.ndarray,
        frames: int,
        buffer_time: float
    ) -> None:
        """Add metronome click to the output.
        
        Args:
            outdata: Output buffer
            frames: Number of frames
            buffer_time: Buffer timestamp
        """
        # Simple metronome: click on every beat
        samples_per_beat = int(self._sample_rate * 60.0 / self._bpm)
        
        # Generate stereo output first
        audio = self._synth.process(frames)
        audio = np.tanh(audio * 0.8)
        stereo = np.column_stack([audio, audio])
        
        # Add click at beat boundaries
        current_sample = int(buffer_time * self._sample_rate) % samples_per_beat
        
        for i in range(frames):
            sample_pos = current_sample + i
            
            # Check if we're at a beat
            beat_position = sample_pos % samples_per_beat
            
            if beat_position < 100:  # Click duration (short blip)
                # Different pitch for downbeat
                if beat_position < 50:
                    click = np.sin(2 * np.pi * 1000 * beat_position / self._sample_rate)
                else:
                    click = np.sin(2 * np.pi * 800 * beat_position / self._sample_rate)
                
                click *= self._metronome_volume * (1 - beat_position / 100)
                stereo[i] += click
        
        outdata[:] = stereo.astype(np.float32)
    
    def is_running(self) -> bool:
        """Check if audio is running."""
        return self._is_running
    
    def set_bpm(self, bpm: int) -> None:
        """Set BPM for metronome timing.
        
        Args:
            bpm: Beats per minute
        """
        self._bpm = max(20, min(300, bpm))
        self._beats_per_sample = self._calculate_beat_interval()
    
    def set_metronome(self, enabled: bool) -> None:
        """Enable or disable metronome.
        
        Args:
            enabled: Whether to enable metronome
        """
        self._metronome_enabled = enabled
        logger.debug(f"Metronome: {enabled}")
    
    def play_note(self, note: int, velocity: int = 100) -> None:
        """Play a note through the synth.
        
        Args:
            note: MIDI note number
            velocity: Note velocity
        """
        if self._synth:
            self._synth.note_on(note, velocity)
    
    def stop_note(self, note: int) -> None:
        """Stop a playing note.
        
        Args:
            note: MIDI note number
        """
        if self._synth:
            self._synth.note_off(note)
    
    def all_notes_off(self) -> None:
        """Stop all playing notes."""
        if self._synth:
            self._synth.all_notes_off()


class StepSequencerPlayer:
    """Step sequencer player that triggers notes based on step pattern.
    
    This class manages the timing and triggering of notes for the
    step sequencer functionality.
    """
    
    def __init__(
        self,
        audio_player: AudioPlayer,
        num_tracks: int = 4,
        num_steps: int = 16
    ):
        """Initialize the step sequencer player.
        
        Args:
            audio_player: AudioPlayer instance
            num_tracks: Number of tracks
            num_steps: Number of steps per track
        """
        self._audio_player = audio_player
        self._num_tracks = num_tracks
        self._num_steps = num_steps
        
        # Track data: {track_index: {note, volume, waveform, muted}}
        self._track_data: Dict[int, dict] = {}
        
        # Step states: {track_index: [bool * num_steps]}
        self._step_states: Dict[int, list] = {}
        
        # Initialize defaults
        for i in range(num_tracks):
            self._track_data[i] = {
                "note": 60 + i * 5,  # Different pitch per track
                "volume": 0.8,
                "waveform": "square",
                "muted": False
            }
            self._step_states[i] = [False] * num_steps
        
        # Playback state
        self._current_step = 0
        self._is_playing = False
        self._bpm = 120
        self._thread: Optional[threading.Thread] = None
        
        logger.info(f"StepSequencerPlayer initialized: {num_tracks}x{num_steps}")
    
    def set_track_data(
        self,
        track_index: int,
        note: int = None,
        volume: float = None,
        waveform: str = None,
        muted: bool = None
    ) -> None:
        """Set data for a track.
        
        Args:
            track_index: Track index
            note: MIDI note (optional)
            volume: Volume 0-1 (optional)
            waveform: Waveform type (optional)
            muted: Mute state (optional)
        """
        if track_index not in self._track_data:
            self._track_data[track_index] = {}
        
        if note is not None:
            self._track_data[track_index]["note"] = note
        if volume is not None:
            self._track_data[track_index]["volume"] = max(0, min(1, volume))
        if waveform is not None:
            self._track_data[track_index]["waveform"] = waveform
        if muted is not None:
            self._track_data[track_index]["muted"] = muted
    
    def set_step(self, track_index: int, step: int, active: bool) -> None:
        """Set step state for a track.
        
        Args:
            track_index: Track index
            step: Step index
            active: Whether step is active
        """
        if track_index not in self._step_states:
            self._step_states[track_index] = [False] * self._num_steps
        
        if 0 <= step < self._num_steps:
            self._step_states[track_index][step] = active
    
    def set_step_count(self, num_steps: int) -> None:
        """Change the number of steps.
        
        Args:
            num_steps: New number of steps
        """
        self._num_steps = max(1, min(64, num_steps))
        
        # Adjust existing states
        for track_idx in self._step_states:
            current = self._step_states[track_idx]
            if len(current) < self._num_steps:
                current.extend([False] * (self._num_steps - len(current)))
            else:
                self._step_states[track_idx] = current[:self._num_steps]
    
    def set_bpm(self, bpm: int) -> None:
        """Set BPM for playback.
        
        Args:
            bpm: Beats per minute
        """
        self._bpm = max(20, min(300, bpm))
    
    def start(self) -> None:
        """Start step sequencer playback."""
        if self._is_playing:
            return
        
        self._is_playing = True
        self._current_step = 0
        self._thread = threading.Thread(target=self._play_loop, daemon=True)
        self._thread.start()
        logger.info("Step sequencer started")
    
    def stop(self) -> None:
        """Stop step sequencer playback."""
        self._is_playing = False
        self._current_step = 0
        
        if self._thread:
            self._thread.join(timeout=1.0)
        
        logger.info("Step sequencer stopped")
    
    def _play_loop(self) -> None:
        """Main playback loop running in separate thread."""
        while self._is_playing:
            try:
                # Calculate step duration
                step_duration = 60.0 / self._bpm / 4.0  # 16th notes
                
                # Trigger notes for active steps
                self._trigger_current_step()
                
                # Advance step
                self._current_step = (self._current_step + 1) % self._num_steps
                
                time.sleep(step_duration)
                
            except Exception as e:
                logger.error(f"Error in step sequencer loop: {e}")
                time.sleep(0.1)
    
    def _trigger_current_step(self) -> None:
        """Trigger notes for the current step."""
        if not self._audio_player.is_running():
            return
        
        for track_idx, step_states in self._step_states.items():
            if track_idx not in self._track_data:
                continue
            
            # Check if step is active
            if self._current_step < len(step_states) and step_states[self._current_step]:
                track_data = self._track_data[track_idx]
                
                # Skip if muted
                if track_data.get("muted", False):
                    continue
                
                # Trigger note
                note = track_data.get("note", 60)
                volume = track_data.get("volume", 0.8)
                
                # Convert volume to velocity
                velocity = int(volume * 127)
                
                self._audio_player.play_note(note, velocity)
                
                # Schedule note off
                note_copy = note
                duration = (60.0 / self._bpm / 4.0) * 0.7
                
                def note_off():
                    time.sleep(duration)
                    self._audio_player.stop_note(note_copy)
                
                threading.Thread(target=note_off, daemon=True).start()
    
    @property
    def current_step(self) -> int:
        """Get current step index."""
        return self._current_step
    
    @property
    def is_playing(self) -> bool:
        """Check if sequencer is playing."""
        return self._is_playing