"""Project Handler - Manejo de proyectos con inyección de dependencias.

Este handler es responsable de todas las operaciones relacionadas con proyectos,
siguiendo el patrón de inyección de dependencias para facilitar el testing.
"""

from pathlib import Path
from typing import Optional, Protocol, List
from datetime import datetime
import logging
import uuid

from src.domain.entities.project import Project
from src.domain.entities.track import Track
from src.domain.entities.pattern import Pattern


logger = logging.getLogger(__name__)


class IProjectRepository(Protocol):
    """Protocolo para repositorio de proyectos.
    
    Define la interfaz que debe implementar cualquier clase
    que proporcione persistencia de proyectos.
    """
    
    def save(self, project: Project, path: Optional[Path] = None) -> bool:
        """Guardar proyecto."""
        ...
    
    def load(self, path: Path) -> Optional[Project]:
        """Cargar proyecto."""
        ...
    
    def exists(self, path: Path) -> bool:
        """Verificar si existe un proyecto."""
        ...
    
    def list_projects(self, directory: Path) -> List[dict]:
        """Listar proyectos en un directorio."""
        ...


class ProjectHandler:
    """Handler para operaciones de proyecto.
    
    Maneja la creación, carga, guardado y gestión de proyectos.
    Utiliza inyección de dependencias para el repositorio.
    
    Attributes:
        _repository: Repositorio para persistencia de proyectos
    """
    
    def __init__(self, repository: Optional[IProjectRepository] = None):
        """Inicializar el handler de proyectos.
        
        Args:
            repository: Implementación de IProjectRepository.
                       Si es None, se usa un repositorio por defecto.
        """
        self._repository = repository
        self._current_project: Optional[Project] = None
        self._current_path: Optional[Path] = None
        self._is_modified = False
        
        logger.info("ProjectHandler inicializado")
    
    @property
    def repository(self) -> Optional[IProjectRepository]:
        """Obtener el repositorio."""
        return self._repository
    
    @repository.setter
    def repository(self, repo: IProjectRepository) -> None:
        """Establecer el repositorio."""
        self._repository = repo
        logger.info("Repositorio establecido en ProjectHandler")
    
    @property
    def current_project(self) -> Optional[Project]:
        """Obtener el proyecto actual."""
        return self._current_project
    
    @property
    def is_modified(self) -> bool:
        """Verificar si hay cambios sin guardar."""
        return self._is_modified
    
    @property
    def has_project(self) -> bool:
        """Verificar si hay un proyecto cargado."""
        return self._current_project is not None
    
    def create_project(
        self,
        name: str = "Untitled Project",
        bpm: int = 120,
        time_signature: tuple = (4, 4)
    ) -> Project:
        """Crear un nuevo proyecto.
        
        Args:
            name: Nombre del proyecto
            bpm: Beats por minuto inicial
            time_signature: Signatura de tiempo (numerador, denominador)
            
        Returns:
            El proyecto creado
        """
        logger.info(f"Create project requested: name={name}, bpm={bpm}, time_sig={time_signature}")
        self._current_project = Project(
            name=name,
            bpm=bpm,
            time_signature_numerator=time_signature[0],
            time_signature_denominator=time_signature[1]
        )
        self._current_path = None
        self._is_modified = False
        
        # Crear pista por defecto
        default_track = self._current_project.add_track("Track 1")
        
        # Crear patrón por defecto
        default_pattern = self._current_project.add_pattern("Pattern 1", length=16)
        
        logger.info(f"Proyecto creado: {name}")
        return self._current_project
    
    def load_project(self, path: Path) -> Optional[Project]:
        """Cargar un proyecto desde archivo.
        
        Args:
            path: Ruta al archivo del proyecto
            
        Returns:
            El proyecto cargado, o None si falló
        """
        logger.info(f"Load project requested: {path}")
        if self._repository is None:
            logger.error("No hay repositorio configurado para cargar proyectos")
            return None
        
        try:
            project = self._repository.load(path)
            if project:
                self._current_project = project
                self._current_path = path
                self._is_modified = False
                logger.info(f"Proyecto cargado: {project.name}")
                return project
            else:
                logger.error(f"No se pudo cargar el proyecto desde {path}")
                return None
        except Exception as e:
            logger.error(f"Error cargando proyecto: {e}")
            return None
    
    def save_project(self, path: Optional[Path] = None) -> bool:
        """Guardar el proyecto actual.
        
        Args:
            path: Ruta opcional. Si no se proporciona, usa la última ruta guardada.
            
        Returns:
            True si el guardado fue exitoso
        """
        logger.info(f"Save project requested: {path or self._current_path}")
        if self._current_project is None:
            logger.warning("No hay proyecto para guardar")
            return False
        
        save_path = path or self._current_path
        if save_path is None:
            logger.error("No hay ruta especificada para guardar")
            return False
        
        if self._repository is None:
            logger.error("No hay repositorio configurado para guardar proyectos")
            return False
        
        try:
            # Actualizar timestamp
            self._current_project.update_modified_time()
            
            # Guardar
            success = self._repository.save(self._current_project, save_path)
            
            if success:
                self._current_path = save_path
                self._is_modified = False
                logger.info(f"Proyecto guardado: {save_path}")
                return True
            else:
                logger.error(f"Error guardando proyecto en {save_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error guardando proyecto: {e}")
            return False
    
    def close_project(self) -> None:
        """Cerrar el proyecto actual."""
        if self._current_project:
            logger.info(f"Proyecto cerrado: {self._current_project.name}")
        self._current_project = None
        self._current_path = None
        self._is_modified = False
    
    def mark_modified(self) -> None:
        """Marcar el proyecto como modificado."""
        self._is_modified = True
        logger.debug("Proyecto marcado como modificado")
    
    def set_bpm(self, bpm: int) -> bool:
        """Establecer el BPM del proyecto.
        
        Args:
            bpm: Nuevo valor de BPM
            
        Returns:
            True si se estableció correctamente
        """
        if self._current_project is None:
            return False
        
        try:
            self._current_project.set_bpm(bpm)
            self._is_modified = True
            logger.info(f"BPM cambiado a {bpm}")
            return True
        except ValueError as e:
            logger.error(f"Error estableciendo BPM: {e}")
            return False
    
    def get_bpm(self) -> int:
        """Obtener el BPM actual."""
        if self._current_project:
            return self._current_project.bpm
        return 120
    
    def set_time_signature(self, numerator: int, denominator: int) -> bool:
        """Establecer la signatura de tiempo.
        
        Args:
            numerator: Numerador (beats por compás)
            denominator: Denominador (figura del beat)
            
        Returns:
            True si se estableció correctamente
        """
        if self._current_project is None:
            return False
        
        try:
            self._current_project.set_time_signature(numerator, denominator)
            self._is_modified = True
            logger.info(f"Time signature cambiada a {numerator}/{denominator}")
            return True
        except ValueError as e:
            logger.error(f"Error estableciendo time signature: {e}")
            return False
    
    def add_track(self, name: str = "New Track") -> Optional[Track]:
        """Añadir una nueva pista al proyecto.
        
        Args:
            name: Nombre de la pista
            
        Returns:
            La pista creada, o None si no hay proyecto
        """
        if self._current_project is None:
            logger.warning("No hay proyecto para añadir pista")
            return None
        
        track = self._current_project.add_track(name)
        self._is_modified = True
        logger.info(f"Pista añadida: {name}")
        return track
    
    def remove_track(self, track_id: str) -> bool:
        """Eliminar una pista del proyecto.
        
        Args:
            track_id: ID de la pista a eliminar
            
        Returns:
            True si se eliminó correctamente
        """
        if self._current_project is None:
            return False
        
        success = self._current_project.remove_track(track_id)
        if success:
            self._is_modified = True
            logger.info(f"Pista eliminada: {track_id}")
        return success
    
    def get_track(self, track_id: str) -> Optional[Track]:
        """Obtener una pista por ID.
        
        Args:
            track_id: ID de la pista
            
        Returns:
            La pista, o None si no existe
        """
        if self._current_project:
            return self._current_project.get_track(track_id)
        return None
    
    def get_all_tracks(self) -> List[Track]:
        """Obtener todas las pistas del proyecto.
        
        Returns:
            Lista de pistas
        """
        if self._current_project:
            return self._current_project.get_tracks()
        return []
    
    def add_pattern(self, name: str = "New Pattern", length: int = 16) -> Optional[Pattern]:
        """Añadir un nuevo patrón al proyecto.
        
        Args:
            name: Nombre del patrón
            length: Número de steps
            
        Returns:
            El patrón creado, o None si no hay proyecto
        """
        if self._current_project is None:
            logger.warning("No hay proyecto para añadir patrón")
            return None
        
        pattern = self._current_project.add_pattern(name, length)
        self._is_modified = True
        logger.info(f"Patrón añadido: {name}")
        return pattern
    
    def remove_pattern(self, pattern_id: str) -> bool:
        """Eliminar un patrón del proyecto.
        
        Args:
            pattern_id: ID del patrón a eliminar
            
        Returns:
            True si se eliminó correctamente
        """
        if self._current_project is None:
            return False
        
        success = self._current_project.remove_pattern(pattern_id)
        if success:
            self._is_modified = True
            logger.info(f"Patrón eliminado: {pattern_id}")
        return success
    
    def get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        """Obtener un patrón por ID.
        
        Args:
            pattern_id: ID del patrón
            
        Returns:
            El patrón, o None si no existe
        """
        if self._current_project:
            return self._current_project.get_pattern(pattern_id)
        return None
    
    def get_all_patterns(self) -> List[Pattern]:
        """Obtener todos los patrones del proyecto.
        
        Returns:
            Lista de patrones
        """
        if self._current_project:
            return self._current_project.get_patterns()
        return []
    
    def set_pattern_length(self, length: int) -> bool:
        """Establecer la longitud de los patrones.
        
        Args:
            length: Nueva longitud (1-64)
            
        Returns:
            True si se estableció correctamente
        """
        if self._current_project is None:
            return False
        
        try:
            self._current_project.set_pattern_length(length)
            self._is_modified = True
            logger.info(f"Pattern length cambiada a {length}")
            return True
        except ValueError as e:
            logger.error(f"Error estableciendo pattern length: {e}")
            return False
    
    def get_project_info(self) -> dict:
        """Obtener información del proyecto actual.
        
        Returns:
            Diccionario con información del proyecto
        """
        if self._current_project is None:
            return {}
        
        return {
            "name": self._current_project.name,
            "bpm": self._current_project.bpm,
            "time_signature": self._current_project.time_signature,
            "pattern_length": self._current_project.pattern_length,
            "track_count": len(self._current_project.tracks),
            "pattern_count": len(self._current_project.patterns),
            "is_modified": self._is_modified,
            "file_path": str(self._current_path) if self._current_path else None,
            "created_at": self._current_project.created_at.isoformat(),
            "modified_at": self._current_project.modified_at.isoformat(),
        }
