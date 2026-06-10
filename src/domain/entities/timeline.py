"""Timeline - Línea de tiempo musical.

Representa la dimensión temporal de una composición musical,
gestionando la posición de eventos en el tiempo.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import logging


logger = logging.getLogger(__name__)


@dataclass
class MusicalPosition:
    """Posición musical (bar.beat.tick)."""
    bar: int = 1
    beat: int = 1
    tick: int = 0
    
    def to_ticks(self, ticks_per_beat: int = 480) -> int:
        """Convertir a ticks."""
        return ((self.bar - 1) * 4 + (self.beat - 1)) * ticks_per_beat + self.tick
    
    @classmethod
    def from_ticks(cls, ticks: int, ticks_per_beat: int = 480) -> "MusicalPosition":
        """Crear desde ticks."""
        total_beats = ticks // ticks_per_beat
        bar = total_beats // 4 + 1
        beat = total_beats % 4 + 1
        tick = ticks % ticks_per_beat
        return cls(bar=bar, beat=beat, tick=tick)
    
    def __str__(self) -> str:
        return f"{self.bar}.{self.beat}.{self.tick}"


class Timeline:
    """Línea de tiempo musical.
    
    Gestiona la posición de eventos musicales en el tiempo,
    con resolución configurable.
    
    Attributes:
        resolution: Ticks por beat (default 480)
    """
    
    def __init__(self, resolution: int = 480):
        """Inicializar la timeline.
        
        Args:
            resolution: Ticks por beat (default 480)
        """
        self._resolution = resolution
        self._duration = 0  # en ticks
        self._markers: List[Tuple[int, str]] = []  # (tick, name)
        
        logger.info(f"Timeline inicializada: {resolution} ticks/beat")
    
    @property
    def resolution(self) -> int:
        """Obtener la resolución."""
        return self._resolution
    
    @property
    def duration(self) -> int:
        """Obtener la duración total en ticks."""
        return self._duration
    
    @duration.setter
    def duration(self, value: int) -> None:
        """Establecer la duración."""
        self._duration = max(0, value)
    
    def set_duration_from_ticks(self, ticks: int) -> None:
        """Establecer duración desde ticks."""
        self._duration = ticks
    
    def set_duration_from_bars(self, bars: int, beats_per_bar: int = 4) -> None:
        """Establecer duración desde compases.
        
        Args:
            bars: Número de compases
            beats_per_bar: Beats por compás
        """
        self._duration = bars * beats_per_bar * self._resolution
    
    def ticks_to_position(self, ticks: int) -> MusicalPosition:
        """Convertir ticks a posición musical.
        
        Args:
            ticks: Número de ticks
            
        Returns:
            Posición musical
        """
        return MusicalPosition.from_ticks(ticks, self._resolution)
    
    def position_to_ticks(self, position: MusicalPosition) -> int:
        """Convertir posición musical a ticks.
        
        Args:
            position: Posición musical
            
        Returns:
            Número de ticks
        """
        return position.to_ticks(self._resolution)
    
    def add_marker(self, tick: int, name: str) -> None:
        """Añadir un marcador.
        
        Args:
            tick: Posición del marcador
            name: Nombre del marcador
        """
        self._markers.append((tick, name))
        self._markers.sort(key=lambda m: m[0])
        logger.debug(f"Marcador añadido: {name} @ {tick}")
    
    def remove_marker(self, tick: int) -> bool:
        """Quitar un marcador.
        
        Args:
            tick: Posición del marcador
            
        Returns:
            True si se quitó
        """
        for i, (t, name) in enumerate(self._markers):
            if t == tick:
                self._markers.pop(i)
                logger.debug(f"Marcador removido: {name}")
                return True
        return False
    
    def get_markers(self) -> List[Tuple[int, str]]:
        """Obtener todos los marcadores."""
        return list(self._markers)
    
    def get_nearest_marker(self, tick: int) -> Optional[Tuple[int, str]]:
        """Obtener el marcador más cercano.
        
        Args:
            tick: Posición de referencia
            
        Returns:
            (tick, name) o None
        """
        if not self._markers:
            return None
        
        nearest = min(self._markers, key=lambda m: abs(m[0] - tick))
        return nearest
    
    def get_position_at_sample(
        self,
        sample: int,
        sample_rate: int,
        bpm: int
    ) -> int:
        """Obtener posición en ticks para una muestra.
        
        Args:
            sample: Número de muestra
            sample_rate: Tasa de muestreo
            bpm: BPM
            
        Returns:
            Posición en ticks
        """
        seconds = sample / sample_rate
        beats = (seconds / 60.0) * bpm
        ticks = int(beats * self._resolution)
        return ticks
    
    def get_sample_at_position(
        self,
        ticks: int,
        sample_rate: int,
        bpm: int
    ) -> int:
        """Obtener muestra para una posición en ticks.
        
        Args:
            ticks: Posición en ticks
            sample_rate: Tasa de muestreo
            bpm: BPM
            
        Returns:
            Número de muestra
        """
        beats = ticks / self._resolution
        seconds = (beats / bpm) * 60.0
        return int(seconds * sample_rate)
    
    def quantize_position(self, tick: int, grid_size: int) -> int:
        """Cuantizar una posición.
        
        Args:
            tick: Posición en ticks
            grid_size: Tamaño de la rejilla
            
        Returns:
            Posición cuantizada
        """
        return (tick // grid_size) * grid_size
    
    def get_beats_per_bar(self, time_signature: Tuple[int, int]) -> int:
        """Obtener beats por compás.
        
        Args:
            time_signature: (numerator, denominator)
            
        Returns:
            Beats por compás
        """
        return time_signature[0]
    
    def get_bar_count(self, time_signature: Tuple[int, int] = (4, 4)) -> int:
        """Obtener el número de compases.
        
        Args:
            time_signature: Signatura de tiempo
            
        Returns:
            Número de compases
        """
        beats_per_bar = self.get_beats_per_bar(time_signature)
        total_beats = self._duration / self._resolution
        return int(total_beats / beats_per_bar) + 1
    
    def to_dict(self) -> dict:
        """Serializar a diccionario."""
        return {
            "resolution": self._resolution,
            "duration": self._duration,
            "markers": [{"tick": t, "name": n} for t, n in self._markers]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Timeline":
        """Crear desde diccionario."""
        timeline = cls(resolution=data.get("resolution", 480))
        timeline._duration = data.get("duration", 0)
        for marker in data.get("markers", []):
            timeline.add_marker(marker["tick"], marker["name"])
        return timeline
