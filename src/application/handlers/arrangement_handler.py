"""Arrangement Handler - Management of the song timeline."""

import logging
from typing import Optional, List
from pathlib import Path

from src.domain.entities.project import Project
from src.domain.entities.clip import Clip, ClipType
from src.domain.entities.arrangement import Arrangement

logger = logging.getLogger(__name__)

class ArrangementHandler:
    """Handler for arrangement operations.
    
    Manages clips on the global timeline.
    """
    
    def __init__(self):
        """Initialize the arrangement handler."""
        logger.info("ArrangementHandler initialized")
    
    def add_clip(
        self,
        project: Project,
        track_id: str,
        name: str,
        clip_type: ClipType,
        start_tick: int,
        duration: int,
        content_id: str
    ) -> Clip:
        """Add a new clip to the project's arrangement.
        
        Args:
            project: Current project
            track_id: Target track ID
            name: Clip name
            clip_type: Type of clip
            start_tick: Start position in ticks
            duration: Length in ticks
            content_id: Reference to content (path or pattern ID)
            
        Returns:
            The created clip
        """
        clip = Clip(
            id=content_id,
            name=name,
            clip_type=clip_type,
            start_tick=start_tick,
            duration=duration
        )
        
        project.arrangement.add_clip(track_id, clip)
        project.update_modified_time()
        logger.info(f"Clip '{name}' added to arrangement @ {start_tick}")
        return clip

    def move_clip(
        self,
        project: Project,
        track_id: str,
        clip_id: str,
        new_start_tick: int
    ) -> bool:
        """Move an existing clip.
        
        Args:
            project: Current project
            track_id: Track ID
            clip_id: Clip ID
            new_start_tick: New start position
            
        Returns:
            True if moved
        """
        clip = project.arrangement.track_clips.get(track_id, {}).get_by_id(clip_id)
        if clip:
            clip.start_tick = new_start_tick
            project.update_modified_time()
            return True
        return False

    def remove_clip(self, project: Project, track_id: str, clip_id: str) -> bool:
        """Remove a clip.
        
        Args:
            project: Current project
            track_id: Track ID
            clip_id: Clip ID
            
        Returns:
            True if removed
        """
        removed = project.arrangement.remove_clip(track_id, clip_id)
        if removed:
            project.update_modified_time()
            return True
        return False

    def get_track_clips(self, project: Project, track_id: str) -> List[Clip]:
        """Get all clips for a track."""
        return project.arrangement.get_track_clips(track_id)
