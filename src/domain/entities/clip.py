"""Clip - Reproducción de audio/MIDI en la timeline.

Un Clip representa una región de audio o datos MIDI que puede
ser reproducida en una pista.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
import logging


logger = logging.getLogger(__name__)


class ClipType(Enum):
    """Tipos de clip."""
    MIDI = "midi"
    AUDIO = "audio"
    AUTOMATION = "automation"
    PATTERN = "pattern"


class ClipColor(Enum):
    """Colores de clip para UI."""
    RED = "#e74c3c"
    ORANGE = "#e67e22"
    YELLOW = "#f1c40f"
    GREEN = "#2ecc71"
    TEAL = "#1abc9c"
    BLUE = "#3498db"
    PURPLE = "#9b59b6"
    PINK = "#e91e63"


@dataclass
class Clip:
    """Clip musical.
    
    Representa una región de datos (MIDI/Audio/Automation)
    que puede ser reproducida en una pista.
    
    Attributes:
        id: Identificador único
        name: Nombre del clip
        clip_type: Tipo de clip
        start_tick: Posición de inicio en ticks
        duration: Duración en ticks
        color: Color del clip
        data: Datos específicos del clip
    """
    id: str
    name: str
    clip_type: ClipType
    start_tick: int
    duration: int
    color: ClipColor = ClipColor.BLUE
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        """Inicialización post-dataclass."""
        if self.data is None:
            self.data = {}
        if self.id is None:
            self.id = str(uuid.uuid4())
    
    @property
    def end_tick(self) -> int:
        """Obtener tick final."""
        return self.start_tick + self.duration
    
    @property
    def has_velocity(self) -> bool:
        """Verificar si el clip tiene datos de velocidad."""
        return "velocity" in self.data or "notes" in self.data
    
    def contains_tick(self, tick: int) -> bool:
        """Verificar si un tick está dentro del clip.
        
        Args:
            tick: Posición a verificar
            
        Returns:
            True si está contenido
        """
        return self.start_tick <= tick < self.end_tick
    
    def overlaps(self, other: "Clip") -> bool:
        """Verificar si hay superposición con otro clip.
        
        Args:
            other: Otro clip
            
        Returns:
            True si hay superposición
        """
        return (
            self.start_tick < other.end_tick and
            self.end_tick > other.start_tick
        )
    
    def split_at(self, tick: int) -> tuple["Clip", "Clip"]:
        """Dividir el clip en dos en una posición.
        
        Args:
            tick: Posición de división
            
        Returns:
            (clip_left, clip_right)
        """
        if not self.contains_tick(tick):
            raise ValueError(f"Tick {tick} fuera del clip")
        
        # Crear clips resultantes
        left = Clip(
            id=str(uuid.uuid4()),
            name=f"{self.name} (L)",
            clip_type=self.clip_type,
            start_tick=self.start_tick,
            duration=tick - self.start_tick,
            color=self.color,
            data=self.data.copy()
        )
        
        right = Clip(
            id=str(uuid.uuid4()),
            name=f"{self.name} (R)",
            clip_type=self.clip_type,
            start_tick=tick,
            duration=self.end_tick - tick,
            color=self.color,
            data=self.data.copy()
        )
        
        return left, right
    
    def move_to(self, new_start: int) -> None:
        """Mover el clip a una nueva posición.
        
        Args:
            new_start: Nueva posición de inicio
        """
        if new_start < 0:
            raise ValueError("La posición no puede ser negativa")
        
        delta = new_start - self.start_tick
        self.start_tick = new_start
        logger.debug(f"Clip movido: delta={delta}")
    
    def resize(self, new_duration: int) -> None:
        """Redimensionar el clip.
        
        Args:
            new_duration: Nueva duración
        """
        if new_duration <= 0:
            raise ValueError("La duración debe ser positiva")
        
        self.duration = new_duration
        logger.debug(f"Clip redimensionado: nueva duración={new_duration}")
    
    def set_color(self, color: ClipColor) -> None:
        """Establecer color del clip.
        
        Args:
            color: Nuevo color
        """
        self.color = color
    
    def get_music_region(self) -> str:
        """Obtener región musical (bar.beat - bar.beat).
        
        Returns:
            Representación de región
        """
        from .timeline import MusicalPosition
        
        start_pos = MusicalPosition.from_ticks(self.start_tick)
        end_pos = MusicalPosition.from_ticks(self.end_tick)
        
        return f"{start_pos} - {end_pos}"
    
    def to_dict(self) -> dict:
        """Serializar a diccionario."""
        return {
            "id": self.id,
            "name": self.name,
            "clip_type": self.clip_type.value,
            "start_tick": self.start_tick,
            "duration": self.duration,
            "color": self.color.value,
            "data": self.data
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Clip":
        """Crear desde diccionario."""
        return cls(
            id=data["id"],
            name=data["name"],
            clip_type=ClipType(data["clip_type"]),
            start_tick=data["start_tick"],
            duration=data["duration"],
            color=ClipColor(data.get("color", "blue")),
            data=data.get("data", {})
        )
    
    @classmethod
    def create_midi_clip(
        cls,
        name: str,
        start_tick: int,
        duration: int,
        notes: Optional[List[dict]] = None
    ) -> "Clip":
        """Crear un clip MIDI.
        
        Args:
            name: Nombre del clip
            start_tick: Inicio en ticks
            duration: Duración en ticks
            notes: Lista de notas MIDI
            
        Returns:
            Nuevo clip MIDI
        """
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            clip_type=ClipType.MIDI,
            start_tick=start_tick,
            duration=duration,
            data={"notes": notes or []}
        )
    
    @classmethod
    def create_pattern_clip(
        cls,
        name: str,
        start_tick: int,
        steps: int,
        step_resolution: int = 480
    ) -> "Clip":
        """Crear un clip de patrón (para secuenciador).
        
        Args:
            name: Nombre del clip
            start_tick: Inicio en ticks
            steps: Número de pasos
            step_resolution: Resolución de cada paso
            
        Returns:
            Nuevo clip de patrón
        """
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            clip_type=ClipType.PATTERN,
            start_tick=start_tick,
            duration=steps * step_resolution,
            data={
                "steps": steps,
                "step_resolution": step_resolution,
                "step_data": [False] * steps
            }
        )


class ClipCollection:
    """Colección de clips.
    
    Gestiona un conjunto de clips en una pista,
    con operaciones de búsqueda y gestión.
    """
    
    def __init__(self):
        """Inicializar colección de clips."""
        self._clips: List[Clip] = []
    
    def add(self, clip: Clip) -> None:
        """Añadir un clip.
        
        Args:
            clip: Clip a añadir
        """
        self._clips.append(clip)
        self._clips.sort(key=lambda c: c.start_tick)
        logger.debug(f"Clip añadido: {clip.name}")
    
    def remove(self, clip_id: str) -> Optional[Clip]:
        """Quitar un clip por ID.
        
        Args:
            clip_id: ID del clip
            
        Returns:
            Clip removido o None
        """
        for i, clip in enumerate(self._clips):
            if clip.id == clip_id:
                removed = self._clips.pop(i)
                logger.debug(f"Clip removido: {removed.name}")
                return removed
        return None
    
    def get_by_id(self, clip_id: str) -> Optional[Clip]:
        """Obtener clip por ID.
        
        Args:
            clip_id: ID del clip
            
        Returns:
            Clip o None
        """
        for clip in self._clips:
            if clip.id == clip_id:
                return clip
        return None
    
    def get_at_tick(self, tick: int) -> List[Clip]:
        """Obtener clips en una posición.
        
        Args:
            tick: Posición en ticks
            
        Returns:
            Lista de clips
        """
        return [c for c in self._clips if c.contains_tick(tick)]
    
    def get_in_range(
        self,
        start_tick: int,
        end_tick: int
    ) -> List[Clip]:
        """Obtener clips en un rango.
        
        Args:
            start_tick: Inicio del rango
            end_tick: Fin del rango
            
        Returns:
            Lista de clips
        """
        return [
            c for c in self._clips
            if c.start_tick < end_tick and c.end_tick > start_tick
        ]
    
    def clear(self) -> None:
        """Limpiar todos los clips."""
        self._clips.clear()
    
    def __len__(self) -> int:
        return len(self._clips)
    
    def __iter__(self):
        return iter(self._clips)
    
    def __getitem__(self, index: int) -> Clip:
        return self._clips[index]
