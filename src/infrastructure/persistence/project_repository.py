"""Project repository - Handles project persistence."""

import json
from pathlib import Path
from typing import Optional

from src.domain.entities.project import Project


class ProjectRepository:
    """Repository for saving and loading projects."""
    
    def __init__(self, base_directory: Optional[Path] = None):
        """Initialize the repository.
        
        Args:
            base_directory: Base directory for projects
        """
        self._base_directory = base_directory or Path.home() / "Documents" / "JustBeat-DAW" / "Projects"
        self._base_directory.mkdir(parents=True, exist_ok=True)
    
    def save(self, project: Project, file_path: Optional[Path] = None) -> bool:
        """Save a project to file.
        
        Args:
            project: Project to save
            file_path: Optional file path (uses project.file_path if not provided)
            
        Returns:
            True if save successful
        """
        try:
            if file_path is None:
                file_path = project.file_path
            
            if file_path is None:
                # Generate filename from project name
                filename = self._sanitize_filename(project.name) + ".jbproj"
                file_path = self._base_directory / filename
            
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert project to dictionary (includes tracks)
            data = project.to_dict()
            
            # Add additional metadata
            data["version"] = "1.0"
            
            # Save to JSON file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Update project file path
            project.file_path = file_path
            project.update_modified_time()
            
            return True
        
        except Exception as e:
            print(f"Error saving project: {e}")
            return False
    
    def load(self, file_path: Path) -> Optional[Project]:
        """Load a project from file.
        
        Args:
            file_path: Path to project file
            
        Returns:
            Project instance or None if loading failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create project from dictionary (includes tracks)
            project = Project.from_dict(data)
            project.file_path = file_path
            
            return project
        
        except Exception as e:
            print(f"Error loading project: {e}")
            return None
    
    def load_from_name(self, name: str) -> Optional[Project]:
        """Load a project by name.
        
        Args:
            name: Project name
            
        Returns:
            Project instance or None if not found
        """
        filename = self._sanitize_filename(name) + ".jbproj"
        file_path = self._base_directory / filename
        
        if file_path.exists():
            return self.load(file_path)
        
        return None
    
    def list_projects(self) -> list[dict]:
        """List all available projects.
        
        Returns:
            List of project metadata dictionaries
        """
        projects = []
        
        for file_path in self._base_directory.glob("*.jbproj"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    projects.append({
                        "name": data.get("name", "Untitled"),
                        "bpm": data.get("bpm", 120),
                        "modified": data.get("modified_at", ""),
                        "path": str(file_path),
                    })
            except Exception:
                pass
        
        return projects
    
    def delete(self, project: Project) -> bool:
        """Delete a project file.
        
        Args:
            project: Project to delete
            
        Returns:
            True if deletion successful
        """
        if project.file_path and project.file_path.exists():
            try:
                project.file_path.unlink()
                return True
            except Exception as e:
                print(f"Error deleting project: {e}")
                return False
        
        return False
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a filename.
        
        Args:
            name: Original name
            
        Returns:
            Sanitized filename
        """
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # Limit length
        if len(name) > 50:
            name = name[:50]
        
        return name
    
    @property
    def base_directory(self) -> Path:
        """Get the base directory for projects."""
        return self._base_directory
