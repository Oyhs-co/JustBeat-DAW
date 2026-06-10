"""Note entity - Represents a musical note."""

from dataclasses import dataclass
from enum import IntEnum


class NoteName(IntEnum):
    """Musical note names."""
    C = 0
    C_SHARP = 1
    D = 2
    D_SHARP = 3
    E = 4
    F = 5
    F_SHARP = 6
    G = 7
    G_SHARP = 8
    A = 9
    A_SHARP = 10
    B = 11


@dataclass
class Note:
    """Note entity - represents a musical note.
    
    Attributes:
        pitch: MIDI note number (0-127)
        velocity: Note velocity (0-127)
        duration: Note duration in ticks
        start_time: Start time in ticks
    """
    
    pitch: int = 60  # Middle C
    velocity: int = 100
    duration: int = 100
    start_time: int = 0
    
    def __post_init__(self):
        """Validate note attributes after initialization."""
        if not 0 <= self.pitch <= 127:
            raise ValueError("Pitch must be between 0 and 127")
        if not 0 <= self.velocity <= 127:
            raise ValueError("Velocity must be between 0 and 127")
        if self.duration < 0:
            raise ValueError("Duration must be non-negative")
        if self.start_time < 0:
            raise ValueError("Start time must be non-negative")
    
    @property
    def note_name(self) -> str:
        """Get the note name (e.g., 'C4', 'F#5')."""
        note_names = ["C", "C#", "D", "D#", "E", "F",
                      "F#", "G", "G#", "A", "A#", "B"]
        octave = (self.pitch // 12) - 1
        note = note_names[self.pitch % 12]
        return f"{note}{octave}"
    
    @property
    def end_time(self) -> int:
        """Get the end time of the note."""
        return self.start_time + self.duration
    
    def transpose(self, semitones: int) -> "Note":
        """Create a transposed copy of this note.
        
        Args:
            semitones: Number of semitones to transpose
            
        Returns:
            New Note instance with transposed pitch
        """
        new_pitch = max(0, min(127, self.pitch + semitones))
        return Note(
            pitch=new_pitch,
            velocity=self.velocity,
            duration=self.duration,
            start_time=self.start_time,
        )
    
    def to_dict(self) -> dict:
        """Convert note to dictionary for serialization."""
        return {
            "pitch": self.pitch,
            "velocity": self.velocity,
            "duration": self.duration,
            "start_time": self.start_time,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Note":
        """Create note from dictionary."""
        return cls(
            pitch=data.get("pitch", 60),
            velocity=data.get("velocity", 100),
            duration=data.get("duration", 100),
            start_time=data.get("start_time", 0),
        )
    
    @classmethod
    def from_note_name(cls, note_name: str, velocity: int = 100,
                       duration: int = 100, start_time: int = 0) -> "Note":
        """Create a note from a note name like 'C4' or 'F#5'.
        
        Args:
            note_name: Note name (e.g., 'C4', 'F#5')
            velocity: Note velocity
            duration: Note duration in ticks
            start_time: Start time in ticks
            
        Returns:
            New Note instance
        """
        note_names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
                      "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
        
        # Parse note name
        if len(note_name) < 2:
            raise ValueError(f"Invalid note name: {note_name}")
        
        note = note_name[:-1]
        octave = int(note_name[-1])
        
        if note not in note_names:
            raise ValueError(f"Invalid note name: {note_name}")
        
        pitch = (octave + 1) * 12 + note_names[note]
        
        return cls(
            pitch=pitch,
            velocity=velocity,
            duration=duration,
            start_time=start_time,
        )
