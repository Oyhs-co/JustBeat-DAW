"""Transport Handler - Manejo del transporte de reproducción.

Este handler es responsable de todas las operaciones relacionadas con
la reproducción y control temporal del proyecto.
"""

from typing import Optional, Callable, Protocol
import logging

from src.domain.transport_state import TransportState


logger = logging.getLogger(__name__)


class IAudioService(Protocol):
    """Protocolo para el servicio de audio.
    
    Define la interfaz que debe implementar el motor de audio.
    """
    
    def play(self) -> None: ...
    def pause(self) -> None: ...
    def stop(self) -> None: ...
    def seek(self, position: int) -> None: ...
    def set_bpm(self, bpm: int) -> None: ...
    def get_position(self) -> int: ...
    def is_playing(self) -> bool: ...


class TransportHandler:
    """Handler para operaciones de transporte.
    
    Maneja la reproducción, pausa, parada, seek y tempo.
    Utiliza inyección de dependencias para el servicio de audio.
    
    Attributes:
        _audio_service: Servicio de audio para operaciones de reproducción
    """
    
    def __init__(self, audio_service: Optional[IAudioService] = None):
        """Inicializar el handler de transporte.
        
        Args:
            audio_service: Implementación de IAudioService.
                         Si es None, se guarda para configuración posterior.
        """
        self._audio_service = audio_service
        self._state = TransportState.STOPPED
        self._position = 0  # en ticks
        self._bpm = 120
        self._loop_enabled = False
        self._loop_start = 0
        self._loop_end = 16
        self._record_enabled = False
        
        # Callbacks para notificación
        self._on_playback_started: Optional[Callable[[], None]] = None
        self._on_playback_stopped: Optional[Callable[[], None]] = None
        self._on_position_changed: Optional[Callable[[int], None]] = None
        self._on_state_changed: Optional[Callable[[TransportState], None]] = None
        self._on_bpm_changed: Optional[Callable[[int], None]] = None
        
        logger.info("TransportHandler inicializado")
    
    # ==================== Properties ====================
    
    @property
    def audio_service(self) -> Optional[IAudioService]:
        """Obtener el servicio de audio."""
        return self._audio_service
    
    @audio_service.setter
    def audio_service(self, service: IAudioService) -> None:
        """Establecer el servicio de audio."""
        self._audio_service = service
        logger.info("Audio service configurado en TransportHandler")
    
    @property
    def state(self) -> TransportState:
        """Obtener el estado actual del transporte."""
        return self._state
    
    @property
    def position(self) -> int:
        """Obtener la posición actual en ticks."""
        return self._position
    
    @property
    def bpm(self) -> int:
        """Obtener el BPM actual."""
        return self._bpm
    
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
    def loop_enabled(self) -> bool:
        """Verificar si el loop está habilitado."""
        return self._loop_enabled
    
    @property
    def loop_region(self) -> tuple[int, int]:
        """Obtener la región de loop (start, end)."""
        return (self._loop_start, self._loop_end)
    
    # ==================== Callbacks ====================
    
    def set_on_playback_started(self, callback: Callable[[], None]) -> None:
        """Establecer callback para inicio de reproducción."""
        self._on_playback_started = callback
    
    def set_on_playback_stopped(self, callback: Callable[[], None]) -> None:
        """Establecer callback para parada de reproducción."""
        self._on_playback_stopped = callback
    
    def set_on_position_changed(self, callback: Callable[[int], None]) -> None:
        """Establecer callback para cambio de posición."""
        self._on_position_changed = callback
    
    def set_on_state_changed(self, callback: Callable[[TransportState], None]) -> None:
        """Establecer callback para cambio de estado."""
        self._on_state_changed = callback
    
    def set_on_bpm_changed(self, callback: Callable[[int], None]) -> None:
        """Establecer callback para cambio de BPM."""
        self._on_bpm_changed = callback
    
    # ==================== Transport Controls ====================
    
    def play(self) -> bool:
        """Iniciar reproducción.
        
        Returns:
            True si se inició correctamente
        """
        logger.info(f"Play requested, current state: {self._state.value}")
        if self._state == TransportState.PLAYING:
            logger.debug("Ya está reproduciendo")
            return True
        
        if self._audio_service is None:
            logger.error("No hay audio service configurado")
            return False
        
        try:
            self._audio_service.play()
            self._state = TransportState.PLAYING
            
            logger.info("Reproducción iniciada")
            
            if self._on_playback_started:
                self._on_playback_started()
            
            if self._on_state_changed:
                self._on_state_changed(self._state)
            
            return True
            
        except Exception as e:
            logger.error(f"Error iniciando reproducción: {e}")
            return False
    
    def pause(self) -> bool:
        """Pausar reproducción.
        
        Returns:
            True si se pausó correctamente
        """
        logger.info(f"Pause requested, current state: {self._state.value}")
        if self._state != TransportState.PLAYING:
            logger.debug("No está reproduciendo")
            return True
        
        if self._audio_service is None:
            logger.error("No hay audio service configurado")
            return False
        
        try:
            self._audio_service.pause()
            self._state = TransportState.PAUSED
            
            logger.info("Reproducción pausada")
            
            if self._on_state_changed:
                self._on_state_changed(self._state)
            
            return True
            
        except Exception as e:
            logger.error(f"Error pausando: {e}")
            return False
    
    def stop(self) -> bool:
        """Detener reproducción y resetear posición.
        
        Returns:
            True si se detuvo correctamente
        """
        logger.info(f"Stop requested, current state: {self._state.value}")
        if self._audio_service is None:
            # Si no hay servicio, solo cambiar estado
            self._state = TransportState.STOPPED
            self._position = 0
            return True
        
        try:
            self._audio_service.stop()
            self._state = TransportState.STOPPED
            self._position = 0
            
            logger.info("Reproducción detenida")
            
            if self._on_playback_stopped:
                self._on_playback_stopped()
            
            if self._on_position_changed:
                self._on_position_changed(self._position)
            
            if self._on_state_changed:
                self._on_state_changed(self._state)
            
            return True
            
        except Exception as e:
            logger.error(f"Error deteniendo: {e}")
            return False
    
    def toggle(self) -> bool:
        """Alternar entre reproducción y pausa.
        
        Returns:
            True si se cambió el estado correctamente
        """
        if self._state == TransportState.PLAYING:
            return self.pause()
        else:
            return self.play()
    
    def start_recording(self) -> bool:
        """Iniciar grabación.
        
        Returns:
            True si se inició correctamente
        """
        logger.info(f"Start recording requested, current state: {self._state.value}")
        if self._state == TransportState.RECORDING:
            logger.debug("Ya está grabando")
            return True
        
        # Asegurar que está reproduciendo
        if self._state != TransportState.PLAYING:
            if not self.play():
                return False
        
        self._record_enabled = True
        self._state = TransportState.RECORDING
        
        logger.info("Grabación iniciada")
        
        if self._on_state_changed:
            self._on_state_changed(self._state)
        
        return True
    
    def stop_recording(self) -> bool:
        """Detener grabación.
        
        Returns:
            True si se detuvo correctamente
        """
        if self._state != TransportState.RECORDING:
            return True
        
        self._record_enabled = False
        self._state = TransportState.PLAYING
        
        logger.info("Grabación detenida")
        
        if self._on_state_changed:
            self._on_state_changed(self._state)
        
        return True
    
    # ==================== Position ====================
    
    def seek(self, position: int) -> bool:
        """Mover a una posición específica.
        
        Args:
            position: Posición en ticks
            
        Returns:
            True si se movió correctamente
        """
        if position < 0:
            position = 0
        
        self._position = position
        
        if self._audio_service:
            try:
                self._audio_service.seek(position)
            except Exception as e:
                logger.error(f"Error en seek: {e}")
        
        logger.debug(f"Seek a posición {position}")
        
        if self._on_position_changed:
            self._on_position_changed(position)
        
        return True
    
    def seek_relative(self, delta: int) -> bool:
        """Mover relativamente desde la posición actual.
        
        Args:
            delta: Cambio de posición en ticks
            
        Returns:
            True si se movió correctamente
        """
        new_position = max(0, self._position + delta)
        return self.seek(new_position)
    
    def go_to_start(self) -> bool:
        """Ir al inicio del proyecto.
        
        Returns:
            True si se movió correctamente
        """
        return self.seek(0)
    
    def go_to_end(self, max_position: int = 0) -> bool:
        """Ir al final del proyecto.
        
        Args:
            max_position: Posición máxima del proyecto
            
        Returns:
            True si se movió correctamente
        """
        return self.seek(max_position)
    
    # ==================== Tempo ====================
    
    def set_bpm(self, bpm: int) -> bool:
        """Establecer el tempo.
        
        Args:
            bpm: Nuevo valor de BPM (20-300)
            
        Returns:
            True si se estableció correctamente
        """
        logger.info(f"Set BPM requested: {bpm}")
        if not 20 <= bpm <= 300:
            logger.warning(f"BPM {bpm} fuera de rango, ajustando a 20-300")
            bpm = max(20, min(300, bpm))
        
        self._bpm = bpm
        
        if self._audio_service:
            try:
                self._audio_service.set_bpm(bpm)
            except Exception as e:
                logger.error(f"Error estableciendo BPM: {e}")
        
        logger.info(f"BPM cambiado a {bpm}")
        
        if self._on_bpm_changed:
            self._on_bpm_changed(bpm)
        
        return True
    
    def set_bpm_relative(self, delta: int) -> bool:
        """Cambiar el tempo relativamente.
        
        Args:
            delta: Cambio de BPM
            
        Returns:
            True si se cambió correctamente
        """
        new_bpm = self._bpm + delta
        return self.set_bpm(new_bpm)
    
    # ==================== Loop ====================
    
    def set_loop(self, enabled: bool, start: int = 0, end: int = 16) -> None:
        """Establecer configuración de loop.
        
        Args:
            enabled: Si el loop está habilitado
            start: Inicio del loop en ticks
            end: Fin del loop en ticks
        """
        if end <= start:
            logger.warning("Loop end debe ser mayor que start")
            return
        
        self._loop_enabled = enabled
        self._loop_start = start
        self._loop_end = end
        
        logger.info(f"Loop configurado: enabled={enabled}, start={start}, end={end}")
    
    def toggle_loop(self) -> None:
        """Alternar loop."""
        self.set_loop(not self._loop_enabled, self._loop_start, self._loop_end)
    
    # ==================== Utilities ====================
    
    def get_position_in_beats(self) -> float:
        """Obtener posición en beats."""
        return self._position / 4.0  # Assuming 16th notes
    
    def get_position_in_seconds(self, ticks_per_beat: int = 480) -> float:
        """Obtener posición en segundos.
        
        Args:
            ticks_per_beat: Resolución (default 480)
            
        Returns:
            Posición en segundos
        """
        beats = self._position / ticks_per_beat
        return (beats / self._bpm) * 60.0
    
    def ticks_to_position(self, ticks: int, ticks_per_beat: int = 480) -> tuple:
        """Convertir ticks a posición musical (bar.beat.tick).
        
        Args:
            ticks: Número de ticks
            ticks_per_beat: Resolución
            
        Returns:
            Tupla (bar, beat, tick)
        """
        beats = ticks // ticks_per_beat
        bar = beats // 4 + 1  # 4/4 time
        beat = beats % 4 + 1
        tick = ticks % ticks_per_beat
        return (bar, beat, tick)
    
    def position_to_ticks(self, bar: int, beat: int, tick: int, 
                         ticks_per_beat: int = 480) -> int:
        """Convertir posición musical a ticks.
        
        Args:
            bar: Número de compás (1-based)
            beat: Número de beat (1-4)
            tick: Número de tick
            ticks_per_beat: Resolución
            
        Returns:
            Número de ticks
        """
        total_beats = (bar - 1) * 4 + (beat - 1)
        return total_beats * ticks_per_beat + tick
