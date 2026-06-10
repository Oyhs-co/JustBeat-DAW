"""Project Manager - Save, load, and manage projects.

This module provides:
- ProjectManager: Main project management
- RecentFiles: Track recent projects
- ProjectTemplates: Built-in project templates
- BackupManager: Auto-backup functionality
"""

import json
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ProjectState(Enum):
    """Project state."""
    NEW = "new"
    MODIFIED = "modified"
    SAVED = "saved"


@dataclass
class RecentFile:
    """A recently opened file."""
    path: str
    name: str
    last_opened: str
    exists: bool = True
    
    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "name": self.name,
            "last_opened": self.last_opened,
            "exists": self.exists,
        }


@dataclass
class ProjectMetadata:
    """Project metadata."""
    name: str = "Untitled Project"
    author: str = "User"
    description: str = ""
    created: str = ""
    modified: str = ""
    version: str = "1.0"
    bpm: int = 120
    time_signature: tuple = (4, 4)
    tags: List[str] = field(default_factory=list)


class RecentFiles:
    """Manager for recent files."""
    
    def __init__(self, max_items: int = 10):
        """Initialize recent files manager.
        
        Args:
            max_items: Maximum number of recent files to track
        """
        self._max_items = max_items
        self._files: List[RecentFile] = []
    
    def add(self, filepath: Path) -> None:
        """Add a file to recent files.
        
        Args:
            filepath: Path to add
        """
        # Remove if already exists
        self.remove(filepath)
        
        # Add to front
        recent = RecentFile(
            path=str(filepath),
            name=filepath.stem,
            last_opened=datetime.now().isoformat(),
            exists=filepath.exists()
        )
        
        self._files.insert(0, recent)
        
        # Trim to max
        if len(self._files) > self._max_items:
            self._files = self._files[:self._max_items]
    
    def remove(self, filepath: Path) -> bool:
        """Remove a file from recent files.
        
        Args:
            filepath: Path to remove
            
        Returns:
            True if file was found and removed
        """
        for i, f in enumerate(self._files):
            if f.path == str(filepath):
                self._files.pop(i)
                return True
        return False
    
    def get_all(self) -> List[RecentFile]:
        """Get all recent files."""
        # Update exists status
        for f in self._files:
            f.exists = Path(f.path).exists()
        return self._files
    
    def clear(self) -> None:
        """Clear all recent files."""
        self._files.clear()
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "files": [f.to_dict() for f in self._files]
        }
    
    @classmethod
    def from_dict(cls, data: dict, max_items: int = 10) -> "RecentFiles":
        """Create from dictionary."""
        manager = cls(max_items)
        for f in data.get("files", []):
            manager._files.append(RecentFile(**f))
        return manager


class BackupManager:
    """Manager for automatic backups."""
    
    def __init__(self, backup_dir: Optional[Path] = None):
        """Initialize backup manager.
        
        Args:
            backup_dir: Directory for backups
        """
        self._backup_dir = backup_dir
        self._max_backups = 5
        self._enabled = True
    
    def set_backup_directory(self, directory: Path) -> None:
        """Set backup directory."""
        self._backup_dir = directory
        directory.mkdir(parents=True, exist_ok=True)
    
    def create_backup(
        self, project_path: Path, project_name: str
    ) -> Optional[Path]:
        """Create a backup of a project.
        
        Args:
            project_path: Original project path
            project_name: Project name
            
        Returns:
            Path to backup, or None if failed
        """
        if not self._enabled or not self._backup_dir:
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{project_name}_{timestamp}.jbak"
            backup_path = self._backup_dir / backup_name
            
            shutil.copy2(project_path, backup_path)
            
            # Clean old backups
            self._clean_old_backups(project_name)
            
            logger.info(f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def _clean_old_backups(self, project_name: str) -> None:
        """Remove old backups, keeping only max_backups."""
        if not self._backup_dir:
            return
        
        # Find backups for this project
        backups = sorted(
            self._backup_dir.glob(f"{project_name}_*.jbak"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # Remove old backups
        for old in backups[self._max_backups:]:
            try:
                old.unlink()
                logger.info(f"Removed old backup: {old}")
            except Exception as e:
                logger.error(f"Failed to remove backup: {e}")
    
    def get_backup_count(self, project_name: str) -> int:
        """Get number of backups for a project."""
        if not self._backup_dir:
            return 0
        return len(list(self._backup_dir.glob(f"{project_name}_*.jbak")))


class ProjectTemplates:
    """Built-in project templates."""
    
    TEMPLATES = {
        "empty": {
            "name": "Empty Project",
            "description": "Blank project with default settings",
            "bpm": 120,
            "tracks": [],
        },
        "basic_beat": {
            "name": "Basic Beat",
            "description": "4-track beat project",
            "bpm": 120,
            "tracks": [
                {"name": "Kick", "instrument": "sine"},
                {"name": "Snare", "instrument": "noise"},
                {"name": "HiHat", "instrument": "square"},
                {"name": "Bass", "instrument": "saw"},
            ],
        },
        "synth_lead": {
            "name": "Synth Lead",
            "description": "Lead synthesizer project",
            "bpm": 128,
            "tracks": [
                {"name": "Lead", "instrument": "saw"},
                {"name": "Pad", "instrument": "sine"},
                {"name": "Bass", "instrument": "square"},
            ],
        },
        "ambient": {
            "name": "Ambient Pad",
            "description": "Ambient soundscape project",
            "bpm": 70,
            "tracks": [
                {"name": "Pad 1", "instrument": "sine"},
                {"name": "Pad 2", "instrument": "saw"},
                {"name": "Drone", "instrument": "sine"},
            ],
        },
    }
    
    @classmethod
    def get_template(cls, template_id: str) -> Optional[dict]:
        """Get a template by ID."""
        return cls.TEMPLATES.get(template_id)
    
    @classmethod
    def get_all_templates(cls) -> List[dict]:
        """Get all available templates."""
        return [
            {"id": k, **v} for k, v in cls.TEMPLATES.items()
        ]


class ProjectManager:
    """Main project manager."""
    
    def __init__(self, projects_dir: Optional[Path] = None):
        """Initialize project manager.
        
        Args:
            projects_dir: Default projects directory
        """
        self._projects_dir = projects_dir
        self._recent_files = RecentFiles()
        self._backup_manager = BackupManager()
        self._current_project_path: Optional[Path] = None
        self._project_state = ProjectState.NEW
        
        if projects_dir:
            projects_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("ProjectManager initialized")
    
    def set_projects_directory(self, directory: Path) -> None:
        """Set default projects directory."""
        self._projects_dir = directory
        directory.mkdir(parents=True, exist_ok=True)
    
    def new_project(self) -> ProjectMetadata:
        """Create a new project.
        
        Returns:
            New project metadata
        """
        self._current_project_path = None
        self._project_state = ProjectState.NEW
        
        return ProjectMetadata(
            name="Untitled Project",
            created=datetime.now().isoformat(),
            modified=datetime.now().isoformat(),
        )
    
    def save_project(
        self,
        project_data: dict,
        filepath: Optional[Path] = None,
        create_backup: bool = True
    ) -> bool:
        """Save project to file.
        
        Args:
            project_data: Project data dictionary
            filepath: Optional custom filepath
            create_backup: Whether to create backup
            
        Returns:
            True if successful
        """
        track_count = len(project_data.get("tracks", [])) if isinstance(project_data.get("tracks"), list) else 0
        logger.info(f"Save project requested: {filepath}, track_count={track_count}")
        # Determine filepath
        if filepath is None:
            if self._projects_dir is None:
                logger.error("No projects directory set")
                return False
            filepath = self._projects_dir / f"{project_data.get('name', 'Untitled')}.jbp"
        
        try:
            # Create backup if exists
            if create_backup and filepath.exists():
                self._backup_manager.create_backup(filepath, filepath.stem)
            
            # Save project
            with open(filepath, "w") as f:
                json.dump(project_data, f, indent=2)
            
            self._current_project_path = filepath
            self._project_state = ProjectState.SAVED
            
            # Add to recent files
            self._recent_files.add(filepath)
            
            logger.info(f"Saved project: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            return False
    
    def load_project(self, filepath: Path) -> Optional[dict]:
        """Load project from file.
        
        Args:
            filepath: Path to project file
            
        Returns:
            Project data dictionary, or None if failed
        """
        logger.info(f"Load project requested: {filepath}")
        try:
            with open(filepath, "r") as f:
                project_data = json.load(f)
            
            self._current_project_path = filepath
            self._project_state = ProjectState.SAVED
            
            # Add to recent files
            self._recent_files.add(filepath)
            
            result_name = project_data.get("name", "unknown")
            logger.info(f"Project loaded: {filepath}, name={result_name}")
            return project_data
            
        except Exception as e:
            logger.error(f"Failed to load project: {e}")
            return None
    
    def get_recent_files(self) -> List[RecentFile]:
        """Get recent files."""
        return self._recent_files.get_all()
    
    def get_current_path(self) -> Optional[Path]:
        """Get current project path."""
        return self._current_project_path
    
    def mark_modified(self) -> None:
        """Mark project as modified."""
        if self._project_state == ProjectState.SAVED:
            self._project_state = ProjectState.MODIFIED
    
    def is_modified(self) -> bool:
        """Check if project has unsaved changes."""
        return self._project_state != ProjectState.SAVED
