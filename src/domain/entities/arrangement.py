"""Arrangement entity - Global timeline organization of clips."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import uuid
import logging

from src.domain.entities.clip import Clip, ClipCollection
from src.domain.entities.timeline import Timeline

logger = logging.getLogger(__name__)

@dataclass
class Arrangement:
    """Arrangement entity - represents the global organization of clips.
    
    Attributes:
        id: Unique identifier
        name: Name of the arrangement
        timeline: Timeline object for position/markers
        track_clips: Mapping of track_id to its ClipCollection
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Arrangement"
    timeline: Timeline = field(default_factory=Timeline)
    track_clips: Dict[str, ClipCollection] = field(default_factory=dict)
    
    def add_clip(self, track_id: str, clip: Clip) -> None:
        """Add a clip to a specific track's arrangement.
        
        Args:
            track_id: ID of the track
            clip: Clip to add
        """
        if track_id not in self.track_clips:
            self.track_clips[track_id] = ClipCollection()
        
        self.track_clips[track_id].add(clip)
        logger.info(f"Clip '{clip.name}' added to track '{track_id}' in arrangement")
    
    def remove_clip(self, track_id: str, clip_id: str) -> Optional[Clip]:
        """Remove a clip from a track.
        
        Args:
            track_id: ID of the track
            clip_id: ID of the clip
            
        Returns:
            Removed clip or None
        """
        if track_id in self.track_clips:
            return self.track_clips[track_id].remove(clip_id)
        return None
    
    def get_track_clips(self, track_id: str) -> List[Clip]:
        """Get all clips for a track.
        
        Args:
            track_id: ID of the track
            
        Returns:
            List of clips
        """
        if track_id in self.track_clips:
            return list(self.track_clips[track_id])
        return []
    
    def get_all_clips_at_tick(self, tick: int) -> Dict[str, List[Clip]]:
        """Get all clips playing at a specific tick across all tracks.
        
        Args:
            tick: Position in ticks
            
        Returns:
            Dict mapping track_id to list of clips
        """
        result = {}
        for track_id, collection in self.track_clips.items():
            clips = collection.get_at_tick(tick)
            if clips:
                result[track_id] = clips
        return result
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "timeline": self.timeline.to_dict(),
            "track_clips": {
                tid: [c.to_dict() for c in col]
                for tid, col in self.track_clips.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Arrangement":
        """Create from dictionary."""
        arrangement = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Arrangement"),
            timeline=Timeline.from_dict(data.get("timeline", {}))
        )
        
        clips_data = data.get("track_clips", {})
        for tid, col_data in clips_data.items():
            collection = ClipCollection()
            for c_data in col_data:
                collection.add(Clip.from_dict(c_data))
            arrangement.track_clips[tid] = collection
            
        return arrangement
