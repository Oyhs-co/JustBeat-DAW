"""Project entity - Root aggregate for JustBeat-DAW projects.

This module defines the Project entity which serves as the root aggregate
for all musical data in the application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import uuid
import logging


logger = logging.getLogger(__name__)

from src.domain.entities.track import Track
from src.domain.entities.pattern import Pattern
from src.domain.entities.arrangement import Arrangement


@dataclass
class Project:
    """Project entity - represents a complete musical project.
    
    This is the root aggregate in the domain model, containing all
    tracks, patterns, and settings for a musical composition.
    
    Attributes:
        id: Unique identifier for the project
        name: Project name
        bpm: Beats per minute (default: 120)
        time_signature_numerator: Numerator of time signature (default: 4)
        time_signature_denominator: Denominator of time signature (default: 4)
        created_at: Project creation timestamp
        modified_at: Last modification timestamp
        file_path: Path to saved project file (None if not saved)
        tracks: List of tracks in the project
        patterns: List of patterns in the project
        arrangement: Global timeline arrangement
        timeline: Timeline for musical positioning
        tempo_map: Tempo map for tempo changes
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled Project"
    bpm: int = 120
    time_signature_numerator: int = 4
    time_signature_denominator: int = 4
    pattern_length: int = 16
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    file_path: Optional[Path] = None
    tracks: List[Track] = field(default_factory=list)
    patterns: List[Pattern] = field(default_factory=list)
    arrangement: Arrangement = field(default_factory=Arrangement)
    active_pattern_index: int = 0
    timeline: Optional["Timeline"] = field(default=None)
    tempo_map: Optional["TempoMap"] = field(default=None)
    
    def __post_init__(self):
        """Validate project attributes after initialization."""
        if self.bpm < 20 or self.bpm > 300:
            raise ValueError("BPM must be between 20 and 300")
        
        if self.time_signature_numerator < 1 or self.time_signature_numerator > 16:
            raise ValueError("Time signature numerator must be between 1 and 16")
        
        if self.time_signature_denominator not in (2, 4, 8, 16):
            raise ValueError("Time signature denominator must be 2, 4, 8, or 16")
        
        if self.pattern_length < 1 or self.pattern_length > 64:
            raise ValueError("Pattern length must be between 1 and 64")
    
    def update_modified_time(self) -> None:
        """Update the last modified timestamp to current time."""
        self.modified_at = datetime.now()
    
    def set_bpm(self, bpm: int) -> None:
        """Set the project's BPM (beats per minute).
        
        Args:
            bpm: New BPM value (must be between 20 and 300)
            
        Raises:
            ValueError: If BPM is out of valid range
        """
        if bpm < 20 or bpm > 300:
            raise ValueError("BPM must be between 20 and 300")
        self.bpm = bpm
        self.update_modified_time()
    
    def set_time_signature(self, numerator: int, denominator: int) -> None:
        """Set the project's time signature.
        
        Args:
            numerator: Numerator of time signature (1-16)
            denominator: Denominator of time signature (2, 4, 8, or 16)
            
        Raises:
            ValueError: If values are out of valid ranges
        """
        if numerator < 1 or numerator > 16:
            raise ValueError(
                "Time signature numerator must be between 1 and 16"
            )
        
        if denominator not in (2, 4, 8, 16):
            raise ValueError(
                "Time signature denominator must be 2, 4, 8, or 16"
            )
        
        self.time_signature_numerator = numerator
        self.time_signature_denominator = denominator
        self.update_modified_time()
    
    def set_pattern_length(self, length: int) -> None:
        """Set the pattern length (number of steps).
        
        Args:
            length: New pattern length (1-64)
            
        Raises:
            ValueError: If length is out of valid range
        """
        if length < 1 or length > 64:
            raise ValueError("Pattern length must be between 1 and 64")
        self.pattern_length = length
        self.update_modified_time()
    
    def add_track(self, name: str = "Track") -> Track:
        """Add a track to the project.
        
        Args:
            name: Track name
            
        Returns:
            New Track instance with a default pattern
        """
        track = Track(name=name)
        # Add a default pattern to the track
        track.patterns.append(Pattern(name="Pattern 1", length=self.pattern_length))
        self.tracks.append(track)
        self.update_modified_time()
        return track
    
    def remove_track(self, track_id: str) -> bool:
        """Remove a track from the project.
        
        Args:
            track_id: Track identifier
            
        Returns:
            True if track was removed
        """
        for i, track in enumerate(self.tracks):
            if track.id == track_id:
                self.tracks.pop(i)
                self.update_modified_time()
                return True
        return False
    
    def get_track(self, track_id: str) -> Optional[Track]:
        """Get a track by ID.
        
        Args:
            track_id: Track identifier
            
        Returns:
            Track or None if not found
        """
        for track in self.tracks:
            if track.id == track_id:
                return track
        return None
    
    def get_tracks(self) -> List[Track]:
        """Get all tracks.
        
        Returns:
            List of tracks
        """
        return self.tracks
    
    # Pattern management
    def add_pattern(self, name: str = "Pattern", length: int = 16) -> Pattern:
        """Add a pattern to the project.
        
        Args:
            name: Pattern name
            length: Number of steps
            
        Returns:
            New Pattern instance
        """
        pattern = Pattern(name=name, length=length)
        self.patterns.append(pattern)
        self.update_modified_time()
        return pattern
    
    def remove_pattern(self, pattern_id: str) -> bool:
        """Remove a pattern from the project.
        
        Args:
            pattern_id: Pattern identifier
            
        Returns:
            True if pattern was removed
        """
        for i, pattern in enumerate(self.patterns):
            if pattern.id == pattern_id:
                self.patterns.pop(i)
                self.update_modified_time()
                return True
        return False
    
    def get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        """Get a pattern by ID.
        
        Args:
            pattern_id: Pattern identifier
            
        Returns:
            Pattern or None if not found
        """
        for pattern in self.patterns:
            if pattern.id == pattern_id:
                return pattern
        return None
    
    def get_patterns(self) -> List[Pattern]:
        """Get all patterns.
        
        Returns:
            List of patterns
        """
        return self.patterns
    
    def get_active_pattern(self) -> Optional[Pattern]:
        """Get the currently active pattern.
        
        Returns:
            Active pattern or first pattern if none active
        """
        if 0 <= self.active_pattern_index < len(self.patterns):
            return self.patterns[self.active_pattern_index]
        elif self.patterns:
            return self.patterns[0]
        return None
    
    def set_active_pattern(self, index: int) -> bool:
        """Set the active pattern by index.
        
        Args:
            index: Pattern index
            
        Returns:
            True if successful
        """
        if 0 <= index < len(self.patterns):
            self.active_pattern_index = index
            self.update_modified_time()
            return True
        return False
    
    @property
    def time_signature(self) -> tuple[int, int]:
        """Get the time signature as a tuple."""
        return (self.time_signature_numerator, self.time_signature_denominator)
    
    @property
    def is_saved(self) -> bool:
        """Check if the project has been saved to a file."""
        return self.file_path is not None
    
    @property
    def display_name(self) -> str:
        """Get the display name (with asterisk if unsaved)."""
        if self.is_saved:
            return self.name
        return f"{self.name} *"
    
    def to_dict(self) -> dict:
        """Convert project to dictionary for serialization.
        
        Returns:
            Dictionary representation of the project
        """
        return {
            "id": self.id,
            "name": self.name,
            "bpm": self.bpm,
            "time_signature": {
                "numerator": self.time_signature_numerator,
                "denominator": self.time_signature_denominator,
            },
            "pattern_length": self.pattern_length,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "file_path": str(self.file_path) if self.file_path else None,
            "tracks": [track.to_dict() for track in self.tracks],
            "patterns": [pattern.to_dict() for pattern in self.patterns],
            "active_pattern_index": self.active_pattern_index,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Create project from dictionary.
        
        Args:
            data: Dictionary containing project data
            
        Returns:
            New Project instance
        """
        from src.domain.entities.track import Track
        from src.domain.entities.pattern import Pattern
        
        time_sig = data.get("time_signature", {})
        
        # Load tracks
        tracks = []
        tracks_data = data.get("tracks", [])
        for track_data in tracks_data:
            tracks.append(Track.from_dict(track_data))
        
        # Load patterns
        patterns = []
        patterns_data = data.get("patterns", [])
        for pattern_data in patterns_data:
            patterns.append(Pattern.from_dict(pattern_data))
        
        active_pattern_index = data.get("active_pattern_index", 0)
        pattern_length = data.get("pattern_length", 16)
        
        project = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Untitled Project"),
            bpm=data.get("bpm", 120),
            time_signature_numerator=time_sig.get("numerator", 4),
            time_signature_denominator=time_sig.get("denominator", 4),
            pattern_length=pattern_length,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            modified_at=datetime.fromisoformat(data["modified_at"]) if data.get("modified_at") else datetime.now(),
            file_path=Path(data["file_path"]) if data.get("file_path") else None,
        )
        project.tracks = tracks
        project.patterns = patterns
        project.active_pattern_index = active_pattern_index
        return project
