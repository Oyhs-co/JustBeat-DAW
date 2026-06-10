"""Transport Service - Servicio de transporte musical.

Sistema completo de transporte con loop, punch-in,
time-stretching y sincronización.
"""

from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from src.domain.transport_state import TransportState


logger = logging.getLogger(__name__)


class LoopMode(Enum):
    """Modo de loop."""
    OFF = "off"
    ALL = "all"           # Loop en toda la canción
    REGION = "region"     # Loop en región
    PINGPONG = "pingpong" # Ping-pong loop


class TransportMode(Enum):
    """Modo de reproducción."""
    NORMAL = "normal"
    LOOP = "loop"
    STRETCH = "stretch"    # Time stretching
    TAP_TEMPO = "tap_tempo"


@dataclass
class LoopRegion:
    """Región de loop.
    
    Attributes:
        start: Inicio en ticks
        end: Fin en ticks
        enabled: Si está habilitado
    """
    start: int
    end: int
    enabled: bool = True
    
    @property
    def length(self) -> int:
        """Obtener longitud."""
        return self.end - self.start


@dataclass
class PunchPoints:
    """Puntos de punch-in/punch-out.
    
    Attributes:
        punch_in: Posición de punch-in
        punch_out: Posición de punch-out
        enabled: Si está habilitado
    """
    punch_in: int = 0
    punch_out: int = 0
    enabled: bool = False


class TransportService:
    """Servicio de transporte.
    
    Gestiona la reproducción, posicionamiento,
    loop y sincronización.
    """
    
    def __init__(
        self,
        sample_rate: int = 44100,
        ticks_per_beat: int = 480
    ):
        """Inicializar transporte.
        
        Args:
            sample_rate: Sample rate
            ticks_per_beat: Ticks por beat
        """
        self._sample_rate = sample_rate
        self._ticks_per_beat = ticks_per_beat
        
        # Estado
        self._state = TransportState.STOPPED
        self._position = 0  # en ticks
        self._last_position = 0  # posición antes de stop
        
        # Tempo
        self._bpm = 120
        self._target_bpm = 120  # Para automation
        self._time_signature = (4, 4)
        
        # Loop
        self._loop_mode = LoopMode.OFF
        self._loop_region = LoopRegion(start=0, end=1920)  # 4 bars
        self._loop_count = 0
        
        # Punch
        self._punch = PunchPoints()
        
        # Modo
        self._mode = TransportMode.NORMAL
        
        # Callbacks
        self._on_position_changed: Optional[Callable[[int], None]] = None
        self._on_state_changed: Optional[Callable[[TransportState], None]] = None
        self._on_loop: Optional[Callable[[int], None]] = None
        self._on_bpm_changed: Optional[Callable[[int], None]] = None
        
        logger.info(f"TransportService inicializado: {self._bpm} BPM")
    
    # === Estado ===
    
    @property
    def state(self) -> TransportState:
        """Obtener estado."""
        return self._state
    
    @property
    def is_playing(self) -> bool:
        """Verificar si está reproduciendo."""
        return self._state == TransportState.PLAYING
    
    @property
    def is_paused(self) -> bool:
        """Verificar si está pausado."""
        return self._state == TransportState.PAUSED
    
    @property
    def is_stopped(self) -> bool:
        """Verificar si está detenido."""
        return self._state == TransportState.STOPPED
    
    @property
    def is_recording(self) -> bool:
        """Verificar si está grabando."""
        return self._state == TransportState.RECORDING
    
    # === Posición ===
    
    @property
    def position(self) -> int:
        """Obtener posición en ticks."""
        return self._position
    
    @property
    def position_beats(self) -> float:
        """Obtener posición en beats."""
        return self._position / self._ticks_per_beat
    
    @property
    def position_bars(self) -> Tuple[int, int, int]:
        """Obtener posición como (bar, beat, tick)."""
        beats_per_bar = self._time_signature[0]
        
        total_beats = int(self.position_beats)
        bar = total_beats // beats_per_bar + 1
        beat = total_beats % beats_per_bar + 1
        tick = self._position % self._ticks_per_beat
        
        return (bar, beat, tick)
    
    def set_position(self, ticks: int) -> None:
        """Establecer posición.
        
        Args:
            ticks: Posición en ticks
        """
        self._position = max(0, ticks)
        
        if self._on_position_changed:
            self._on_position_changed(self._position)
    
    def set_position_beats(self, beats: float) -> None:
        """Establecer posición en beats."""
        ticks = int(beats * self._ticks_per_beat)
        self.set_position(ticks)
    
    def set_position_bars(self, bar: int, beat: int = 1, tick: int = 0) -> None:
        """Establecer posición como bar.beat.tick."""
        beats_per_bar = self._time_signature[0]
        
        total_beats = (bar - 1) * beats_per_bar + (beat - 1)
        ticks = int(total_beats * self._ticks_per_beat + tick)
        
        self.set_position(ticks)
    
    # === Transport ===
    
    def play(self) -> None:
        """Iniciar reproducción."""
        if self._state == TransportState.STOPPED:
            # Desde stopped, empezar desde última posición
            self._position = self._last_position
        
        self._state = TransportState.PLAYING
        
        if self._on_state_changed:
            self._on_state_changed(self._state)
        
        logger.debug(f"Play: posición {self._position}")
    
    def pause(self) -> None:
        """Pausar reproducción."""
        if self._state == TransportState.PLAYING:
            self._state = TransportState.PAUSED
            
            if self._on_state_changed:
                self._on_state_changed(self._state)
            
            logger.debug("Pause")
    
    def stop(self) -> None:
        """Detener reproducción."""
        self._last_position = self._position
        self._position = 0
        self._loop_count = 0
        self._state = TransportState.STOPPED
        
        if self._on_state_changed:
            self._on_state_changed(self._state)
        
        logger.debug("Stop")
    
    def record(self) -> None:
        """Iniciar grabación."""
        self._state = TransportState.RECORDING
        
        if self._on_state_changed:
            self._on_state_changed(self._state)
        
        logger.debug("Record")
    
    def toggle_play_pause(self) -> None:
        """Alternar play/pause."""
        if self.is_playing:
            self.pause()
        else:
            self.play()
    
    # === Tempo ===
    
    @property
    def bpm(self) -> int:
        """Obtener BPM."""
        return self._bpm
    
    @property
    def time_signature(self) -> Tuple[int, int]:
        """Obtener signatura de tiempo."""
        return self._time_signature
    
    def set_bpm(self, bpm: int) -> None:
        """Establecer BPM.
        
        Args:
            bpm: Nuevo BPM
        """
        if 20 <= bpm <= 300:
            self._bpm = bpm
            self._target_bpm = bpm
            
            if self._on_bpm_changed:
                self._on_bpm_changed(bpm)
            
            logger.debug(f"BPM: {bpm}")
    
    def set_time_signature(self, numerator: int, denominator: int) -> None:
        """Establecer signatura de tiempo.
        
        Args:
            numerator: Beats por compás
            denominator: Figura (4 = negra)
        """
        if numerator > 0 and denominator in (1, 2, 4, 8, 16):
            self._time_signature = (numerator, denominator)
            logger.debug(f"Time signature: {numerator}/{denominator}")
    
    # === Loop ===
    
    @property
    def loop_mode(self) -> LoopMode:
        """Obtener modo de loop."""
        return self._loop_mode
    
    @property
    def loop_region(self) -> LoopRegion:
        """Obtener región de loop."""
        return self._loop_region
    
    def set_loop_mode(self, mode: LoopMode) -> None:
        """Establecer modo de loop.
        
        Args:
            mode: Modo de loop
        """
        self._loop_mode = mode
        logger.debug(f"Loop mode: {mode.value}")
    
    def set_loop_region(self, start: int, end: int) -> None:
        """Establecer región de loop.
        
        Args:
            start: Inicio en ticks
            end: Fin en ticks
        """
        if end > start:
            self._loop_region.start = start
            self._loop_region.end = end
            logger.debug(f"Loop region: {start} - {end}")
    
    def enable_loop(self, enabled: bool = True) -> None:
        """Habilitar/deshabilitar loop."""
        if enabled:
            self._loop_mode = LoopMode.REGION
            self._loop_region.enabled = True
        else:
            self._loop_mode = LoopMode.OFF
            self._loop_region.enabled = False
    
    def toggle_loop(self) -> None:
        """Alternar loop."""
        if self._loop_mode == LoopMode.OFF:
            self.enable_loop()
        else:
            self.enable_loop(False)
    
    # === Punch ===
    
    @property
    def punch(self) -> PunchPoints:
        """Obtener puntos de punch."""
        return self._punch
    
    def set_punch_in(self, tick: int) -> None:
        """Establecer punch-in."""
        self._punch.punch_in = tick
        self._punch.enabled = True
    
    def set_punch_out(self, tick: int) -> None:
        """Establecer punch-out."""
        self._punch.punch_out = tick
        self._punch.enabled = True
    
    def enable_punch(self, enabled: bool = True) -> None:
        """Habilitar punch-in/out."""
        self._punch.enabled = enabled
    
    def is_punching_in(self, position: int) -> bool:
        """Verificar si está en punto de punch-in."""
        if not self._punch.enabled:
            return False
        return position == self._punch.punch_in
    
    def is_punching_out(self, position: int) -> bool:
        """Verificar si está en punto de punch-out."""
        if not self._punch.enabled:
            return False
        return position == self._punch.punch_out
    
    # === Avance ===
    
    def advance(self, tick_increment: int) -> int:
        """Avanzar posición.
        
        Args:
            tick_increment: Incremento en ticks
            
        Returns:
            Nueva posición
        """
        if self._state not in (TransportState.PLAYING, TransportState.RECORDING):
            return self._position
        
        self._position += tick_increment
        
        # Verificar punch-out
        if self._punch.enabled and self._position >= self._punch.punch_out:
            self.pause()
            return self._position
        
        # Verificar loop
        if self._loop_mode != LoopMode.OFF and self._loop_region.enabled:
            if self._position >= self._loop_region.end:
                self._position = self._loop_region.start
                self._loop_count += 1
                
                if self._on_loop:
                    self._on_loop(self._loop_count)
        
        if self._on_position_changed:
            self._on_position_changed(self._position)
        
        return self._position
    
    def seek(self, ticks: int) -> None:
        """Buscar a posición.
        
        Args:
            ticks: Posición destino
        """
        was_playing = self.is_playing
        
        if was_playing:
            self.pause()
        
        self.set_position(ticks)
        
        if was_playing:
            self.play()
    
    # === Conversiones ===
    
    def ticks_to_seconds(self, ticks: int) -> float:
        """Convertir ticks a segundos.
        
        Args:
            ticks: Ticks
            
        Returns:
            Segundos
        """
        beats = ticks / self._ticks_per_beat
        return (beats / self._bpm) * 60.0
    
    def seconds_to_ticks(self, seconds: float) -> int:
        """Convertir segundos a ticks.
        
        Args:
            seconds: Segundos
            
        Returns:
            Ticks
        """
        beats = (seconds * self._bpm) / 60.0
        return int(beats * self._ticks_per_beat)
    
    def get_duration_seconds(self, total_ticks: int) -> float:
        """Obtener duración en segundos.
        
        Args:
            total_ticks: Duración en ticks
            
        Returns:
            Duración en segundos
        """
        return self.ticks_to_seconds(total_ticks)
    
    # === Callbacks ===
    
    def set_position_callback(
        self,
        callback: Callable[[int], None]
    ) -> None:
        """Establecer callback de cambio de posición."""
        self._on_position_changed = callback
    
    def set_state_callback(
        self,
        callback: Callable[[TransportState], None]
    ) -> None:
        """Establecer callback de cambio de estado."""
        self._on_state_changed = callback
    
    def set_loop_callback(
        self,
        callback: Callable[[int], None]
    ) -> None:
        """Establecer callback de loop."""
        self._on_loop = callback
    
    def set_bpm_callback(
        self,
        callback: Callable[[int], None]
    ) -> None:
        """Establecer callback de cambio de BPM."""
        self._on_bpm_changed = callback
    
    # === Serialización ===
    
    def to_dict(self) -> dict:
        """Serializar a diccionario."""
        return {
            "state": self._state.value,
            "position": self._position,
            "last_position": self._last_position,
            "bpm": self._bpm,
            "target_bpm": self._target_bpm,
            "time_signature": list(self._time_signature),
            "loop_mode": self._loop_mode.value,
            "loop_region": {
                "start": self._loop_region.start,
                "end": self._loop_region.end,
                "enabled": self._loop_region.enabled
            },
            "punch": {
                "punch_in": self._punch.punch_in,
                "punch_out": self._punch.punch_out,
                "enabled": self._punch.enabled
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TransportService":
        """Crear desde diccionario."""
        service = cls()
        
        service._state = TransportState(data.get("state", "stopped"))
        service._position = data.get("position", 0)
        service._last_position = data.get("last_position", 0)
        service._bpm = data.get("bpm", 120)
        service._target_bpm = data.get("target_bpm", 120)
        
        time_sig = data.get("time_signature", [4, 4])
        service._time_signature = (time_sig[0], time_sig[1])
        
        service._loop_mode = LoopMode(data.get("loop_mode", "off"))
        
        loop_data = data.get("loop_region", {})
        service._loop_region.start = loop_data.get("start", 0)
        service._loop_region.end = loop_data.get("end", 1920)
        service._loop_region.enabled = loop_data.get("enabled", True)
        
        punch_data = data.get("punch", {})
        service._punch.punch_in = punch_data.get("punch_in", 0)
        service._punch.punch_out = punch_data.get("punch_out", 0)
        service._punch.enabled = punch_data.get("enabled", False)
        
        return service
