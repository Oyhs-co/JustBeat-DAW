"""Track entity - Represents an audio track in the project."""

from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class Track:
    """Track entity - represents an audio track in the project.
    
    Attributes:
        id: Unique identifier for the track
        name: Track name
        volume: Track volume (0.0 to 1.0)
        pan: Track pan (-1.0 left to 1.0 right)
        muted: Whether the track is muted
        solo: Whether the track is solo
        instrument_id: ID of the instrument assigned to this track
        effect_chain: List of effect plugin IDs
        patterns: List of patterns for this track
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Track"
    volume: float = 1.0
    pan: float = 0.0
    muted: bool = False
    solo: bool = False
    instrument_id: Optional[str] = None
    effect_chain: list[str] = field(default_factory=list)
    patterns: list[object] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate track attributes after initialization."""
        if not 0.0 <= self.volume <= 1.0:
            raise ValueError("Volume must be between 0.0 and 1.0")
        if not -1.0 <= self.pan <= 1.0:
            raise ValueError("Pan must be between -1.0 and 1.0")
    
    def set_volume(self, volume: float) -> None:
        """Set the track volume.
        
        Args:
            volume: New volume (0.0 to 1.0)
        """
        if not 0.0 <= volume <= 1.0:
            raise ValueError("Volume must be between 0.0 and 1.0")
        self.volume = volume
    
    def set_pan(self, pan: float) -> None:
        """Set the track pan.
        
        Args:
            pan: New pan value (-1.0 left to 1.0 right)
        """
        if not -1.0 <= pan <= 1.0:
            raise ValueError("Pan must be between -1.0 and 1.0")
        self.pan = pan
    
    def toggle_mute(self) -> None:
        """Toggle the mute state."""
        self.muted = not self.muted
    
    def toggle_solo(self) -> None:
        """Toggle the solo state."""
        self.solo = not self.solo
    
    def add_effect(self, effect_id: str) -> None:
        """Add an effect to the track's effect chain.
        
        Args:
            effect_id: ID of the effect plugin
        """
        if effect_id not in self.effect_chain:
            self.effect_chain.append(effect_id)
    
    def remove_effect(self, effect_id: str) -> None:
        """Remove an effect from the track's effect chain.
        
        Args:
            effect_id: ID of the effect plugin
        """
        if effect_id in self.effect_chain:
            self.effect_chain.remove(effect_id)
    
    def to_dict(self) -> dict:
        """Convert track to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "volume": self.volume,
            "pan": self.pan,
            "muted": self.muted,
            "solo": self.solo,
            "instrument_id": self.instrument_id,
            "effect_chain": self.effect_chain,
            "patterns": [p.to_dict() for p in self.patterns] if hasattr(self, 'patterns') else [],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Track":
        """Create track from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Track"),
            volume=data.get("volume", 1.0),
            pan=data.get("pan", 0.0),
            muted=data.get("muted", False),
            solo=data.get("solo", False),
            instrument_id=data.get("instrument_id"),
            effect_chain=data.get("effect_chain", []),
        )
