"""TempoMap - Mapa de tempo y signatura de tiempo.

Gestiona cambios de tempo y signatura de tiempo a lo largo
de la canción.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from bisect import bisect_right
import logging


logger = logging.getLogger(__name__)


@dataclass
class TempoPoint:
    """Punto de tempo.
    
    Attributes:
        tick: Posición en ticks
        bpm: Beats por minuto
    """
    tick: int
    bpm: float


@dataclass
class TimeSignaturePoint:
    """Punto de signatura de tiempo.
    
    Attributes:
        tick: Posición en ticks
        numerator: Numerador (beats por compás)
        denominator: Denominador (figura de negra)
    """
    tick: int
    numerator: int = 4
    denominator: int = 4


class TempoMap:
    """Mapa de tempo y signatura de tiempo.
    
    Permite cambios de tempo y signatura de tiempo en cualquier
    punto de la canción.
    
    Attributes:
        default_bpm: BPM por defecto
        default_time_signature: Signatura de tiempo por defecto
    """
    
    def __init__(
        self,
        default_bpm: float = 120.0,
        default_time_signature: Tuple[int, int] = (4, 4)
    ):
        """Inicializar el mapa de tempo.
        
        Args:
            default_bpm: BPM por defecto
            default_time_signature: Signatura por defecto
        """
        self._default_bpm = default_bpm
        self._default_time_signature = default_time_signature
        
        # Puntos de tempo ordenados
        self._tempo_points: List[TempoPoint] = [TempoPoint(0, default_bpm)]
        
        # Puntos de signatura de tiempo
        self._time_signature_points: List[TimeSignaturePoint] = [
            TimeSignaturePoint(0, default_time_signature[0], default_time_signature[1])
        ]
        
        logger.info(f"TempoMap inicializado: {default_bpm} BPM")
    
    @property
    def default_bpm(self) -> float:
        """Obtener BPM por defecto."""
        return self._default_bpm
    
    @property
    def default_time_signature(self) -> Tuple[int, int]:
        """Obtener signatura por defecto."""
        return (
            self._default_time_signature[0],
            self._default_time_signature[1]
        )
    
    # === Gestión de Tempo ===
    
    def get_bpm_at(self, tick: int) -> float:
        """Obtener BPM en una posición.
        
        Args:
            tick: Posición en ticks
            
        Returns:
            BPM en esa posición
        """
        if not self._tempo_points:
            return self._default_bpm
        
        # Encontrar el último punto de tempo antes del tick
        ticks = [p.tick for p in self._tempo_points]
        index = bisect_right(ticks, tick) - 1
        
        if index < 0:
            return self._default_bpm
        
        return self._tempo_points[index].bpm
    
    def set_bpm(self, tick: int, bpm: float) -> None:
        """Establecer BPM en una posición.
        
        Args:
            tick: Posición en ticks
            bpm: Nuevo BPM
        """
        if bpm <= 0:
            raise ValueError("El BPM debe ser positivo")
        
        # Buscar punto existente en esta posición
        for point in self._tempo_points:
            if point.tick == tick:
                point.bpm = bpm
                logger.debug(f"Tempo actualizado: tick={tick}, bpm={bpm}")
                return
        
        # Añadir nuevo punto
        new_point = TempoPoint(tick, bpm)
        self._tempo_points.append(new_point)
        self._tempo_points.sort(key=lambda p: p.tick)
        
        logger.debug(f"Tempo añadido: tick={tick}, bpm={bpm}")
    
    def remove_bpm_at(self, tick: int) -> bool:
        """Quitar un cambio de tempo.
        
        Args:
            tick: Posición del punto
            
        Returns:
            True si se removió
        """
        for i, point in enumerate(self._tempo_points):
            if point.tick == tick and i > 0:  # No borrar el primero
                self._tempo_points.pop(i)
                logger.debug(f"Tempo removido: tick={tick}")
                return True
        return False
    
    def get_tempo_points(self) -> List[TempoPoint]:
        """Obtener todos los puntos de tempo."""
        return list(self._tempo_points)
    
    # === Gestión de Time Signature ===
    
    def get_time_signature_at(self, tick: int) -> Tuple[int, int]:
        """Obtener signatura de tiempo en una posición.
        
        Args:
            tick: Posición en ticks
            
        Returns:
            (numerator, denominator)
        """
        if not self._time_signature_points:
            return self._default_time_signature
        
        ticks = [p.tick for p in self._time_signature_points]
        index = bisect_right(ticks, tick) - 1
        
        if index < 0:
            return self._default_time_signature
        
        point = self._time_signature_points[index]
        return (point.numerator, point.denominator)
    
    def set_time_signature(
        self,
        tick: int,
        numerator: int,
        denominator: int
    ) -> None:
        """Establecer signatura de tiempo.
        
        Args:
            tick: Posición en ticks
            numerator: Beats por compás
            denominator: Figura (1=whole, 2=half, 4=quarter, etc.)
        """
        if numerator <= 0:
            raise ValueError("El numerador debe ser positivo")
        if denominator not in (1, 2, 4, 8, 16):
            raise ValueError("Denominador inválido")
        
        # Buscar punto existente
        for point in self._time_signature_points:
            if point.tick == tick:
                point.numerator = numerator
                point.denominator = denominator
                logger.debug(
                    f"Time signature actualizado: tick={tick}, {numerator}/{denominator}"
                )
                return
        
        # Añadir nuevo punto
        new_point = TimeSignaturePoint(tick, numerator, denominator)
        self._time_signature_points.append(new_point)
        self._time_signature_points.sort(key=lambda p: p.tick)
        
        logger.debug(f"Time signature añadido: tick={tick}, {numerator}/{denominator}")
    
    def get_time_signature_points(self) -> List[TimeSignaturePoint]:
        """Obtener todos los puntos de signatura."""
        return list(self._time_signature_points)
    
    # === Conversiones ===
    
    def tick_to_beat(self, tick: int) -> float:
        """Convertir ticks a beats.
        
        Args:
            tick: Posición en ticks
            
        Returns:
            Número de beats
        """
        if not self._tempo_points:
            return tick / 480.0  # Asumir 480 ticks/beat
        
        # Simplificación: usar el tempo actual
        bpm = self.get_bpm_at(tick)
        ticks_per_beat = self.get_ticks_per_beat()
        
        return tick / ticks_per_beat
    
    def beat_to_tick(self, beat: float) -> int:
        """Convertir beats a ticks.
        
        Args:
            beat: Número de beat
            
        Returns:
            Posición en ticks
        """
        ticks_per_beat = self.get_ticks_per_beat()
        return int(beat * ticks_per_beat)
    
    def tick_to_bar_beat_tick(
        self,
        tick: int,
        ticks_per_beat: int = 480
    ) -> Tuple[int, int, int]:
        """Convertir ticks a bar.beat.tick.
        
        Args:
            tick: Posición en ticks
            ticks_per_beat: Ticks por beat
            
        Returns:
            (bar, beat, tick)
        """
        time_sig = self.get_time_signature_at(tick)
        beats_per_bar = time_sig[0]
        
        # Calcular beat absoluto
        beat_absolute = tick / ticks_per_beat
        
        # Calcular compás
        bar = int(beat_absolute / beats_per_bar) + 1
        beat = int(beat_absolute % beats_per_bar) + 1
        tick_in_beat = int(tick % ticks_per_beat)
        
        return (bar, beat, tick_in_beat)
    
    def bar_beat_tick_to_tick(
        self,
        bar: int,
        beat: int,
        tick: int,
        ticks_per_beat: int = 480
    ) -> int:
        """Convertir bar.beat.tick a ticks.
        
        Args:
            bar: Número de compás (1-based)
            beat: Beat (1-based)
            tick: Tick dentro del beat
            ticks_per_beat: Ticks por beat
            
        Returns:
            Posición en ticks
        """
        time_sig = self.get_time_signature_at(0)  # Simplificación
        beats_per_bar = time_sig[0]
        
        total_beats = (bar - 1) * beats_per_bar + (beat - 1)
        return int(total_beats * ticks_per_beat + tick)
    
    def get_ticks_per_beat(self, ticks_per_quarter: int = 480) -> float:
        """Obtener ticks por beat (considerando denominador).
        
        Args:
            ticks_per_quarter: Ticks por negra
            
        Returns:
            Ticks por beat
        """
        # En 4/4, negra = beat
        # En 6/8, negra = medio beat (3 negras = 2 beats)
        return float(ticks_per_quarter)
    
    def get_ticks_per_bar(self, ticks_per_beat: int = 480) -> int:
        """Obtener ticks por compás.
        
        Args:
            ticks_per_beat: Ticks por beat
            
        Returns:
            Ticks por compás
        """
        time_sig = self.get_time_signature_at(0)
        beats_per_bar = time_sig[0]
        return beats_per_bar * ticks_per_beat
    
    # === Utilidades ===
    
    def get_duration_in_bars(self, total_ticks: int) -> float:
        """Obtener duración en compases.
        
        Args:
            total_ticks: Duración total en ticks
            
        Returns:
            Duración en compases
        """
        ticks_per_bar = self.get_ticks_per_bar()
        return total_ticks / ticks_per_bar
    
    def smooth_tempo_changes(
        self,
        start_tick: int,
        end_tick: int
    ) -> List[TempoPoint]:
        """Obtener puntos de tempo en un rango.
        
        Args:
            start_tick: Inicio del rango
            end_tick: Fin del rango
            
        Returns:
            Lista de puntos de tempo
        """
        result = []
        for point in self._tempo_points:
            if start_tick <= point.tick <= end_tick:
                result.append(point)
            elif point.tick > end_tick:
                break
        
        return result
    
    def to_dict(self) -> dict:
        """Serializar a diccionario."""
        return {
            "default_bpm": self._default_bpm,
            "default_time_signature": list(self._default_time_signature),
            "tempo_points": [
                {"tick": p.tick, "bpm": p.bpm}
                for p in self._tempo_points
            ],
            "time_signature_points": [
                {"tick": p.tick, "numerator": p.numerator, "denominator": p.denominator}
                for p in self._time_signature_points
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TempoMap":
        """Crear desde diccionario."""
        default_bpm = data.get("default_bpm", 120.0)
        time_sig = data.get("default_time_signature", [4, 4])
        
        tempo_map = cls(
            default_bpm=default_bpm,
            default_time_signature=(time_sig[0], time_sig[1])
        )
        
        # Cargar puntos de tempo
        tempo_map._tempo_points = []
        for point in data.get("tempo_points", []):
            tempo_map.set_bpm(point["tick"], point["bpm"])
        
        # Cargar signaturas de tiempo
        tempo_map._time_signature_points = []
        for point in data.get("time_signature_points", []):
            tempo_map.set_time_signature(
                point["tick"],
                point["numerator"],
                point["denominator"]
            )
        
        return tempo_map
