"""PlaybackController - Controller for playback and transport controls.

This controller manages:
- Play/Stop/Record operations
- BPM changes
- Playhead position
- Loop settings
- Transport state synchronization

Now uses PresentationModel for cleaner separation of concerns.
"""

import logging
from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from src.presentation.models.presentation_model import (
    PresentationModel,
    get_presentation_model
)

if TYPE_CHECKING:
    from src.application.app_core import AppCore


logger = logging.getLogger(__name__)


class PlaybackController(QObject):
    """
    Controller for managing playback and transport operations.
    
    Uses PresentationModel to communicate with handlers, providing
    a cleaner separation of concerns.
    
    Signals:
        playback_started: Emitido cuando inicia reproducción
        playback_stopped: Emitido cuando se detiene
        bpm_changed: Emitido cuando cambia BPM (new_bpm)
        position_changed: Emitido cuando cambia posición (step)
        loop_changed: Emitido cuando cambia loop (enabled, start, end)
    """
    
    # Signals
    playback_started = Signal()
    playback_stopped = Signal()
    bpm_changed = Signal(int)
    position_changed = Signal(int)
    loop_changed = Signal(bool, int, int)
    
    def __init__(
        self,
        app_core: Optional["AppCore"] = None,
        presentation_model: Optional[PresentationModel] = None
    ) -> None:
        """Initialize the playback controller.
        
        Args:
            app_core: AppCore instance for audio control (deprecated, use presentation_model)
            presentation_model: PresentationModel instance
        """
        super().__init__()
        
        # Usar PresentationModel si se proporciona, o obtener el global
        if presentation_model is not None:
            self._model = presentation_model
        else:
            self._model = get_presentation_model()
        
        # Mantener referencia a AppCore para compatibilidad hacia atrás
        self._app_core = app_core
        
        # Estado local
        self._sequencer = None
        self._is_playing = False
        self._bpm = 120
        self._current_step = 0
        self._loop_enabled = True
        self._loop_start = 0
        self._loop_end = 15
        
        # Conectar señales del modelo
        self._connect_model_signals()
        
        logger.info("PlaybackController initialized with PresentationModel")
    
    def _connect_model_signals(self) -> None:
        """Conectar señales del PresentationModel."""
        self._model.playback_state_changed.connect(self._on_playback_state_changed)
        self._model.position_changed.connect(self._on_position_changed)
        self._model.bpm_changed.connect(self._on_bpm_changed)
    
    @property
    def is_playing(self) -> bool:
        """Check if playback is active."""
        return self._is_playing
    
    @property
    def bpm(self) -> int:
        """Get current BPM."""
        return self._bpm
    
    @property
    def current_step(self) -> int:
        """Get current playhead position."""
        return self._current_step
    
    @property
    def model(self) -> PresentationModel:
        """Get the presentation model."""
        return self._model
    
    def play(self) -> None:
        """Start playback."""
        logger.info(f"Play requested, current state: {'playing' if self._is_playing else 'stopped/paused'}")
        if self._is_playing:
            logger.debug("Already playing, ignoring play command")
            return
        
        try:
            # Usar PresentationModel para reproducir
            self._model.play()
            
            self._is_playing = True
            self.playback_started.emit()
            logger.info("Playback started via PresentationModel")
        except Exception as e:
            logger.error(f"Error starting playback: {e}", exc_info=True)
            raise
    
    def stop(self) -> None:
        """Stop playback."""
        logger.info(f"Stop requested, current state: {'playing' if self._is_playing else 'stopped'}")
        if not self._is_playing:
            logger.debug("Already stopped, ignoring stop command")
            return
        
        try:
            # Usar PresentationModel para detener
            self._model.stop()
            
            self._is_playing = False
            self._current_step = 0
            self.playback_stopped.emit()
            logger.info("Playback stopped via PresentationModel")
        except Exception as e:
            logger.error(f"Error stopping playback: {e}", exc_info=True)
            raise
    
    def toggle_playback(self) -> None:
        """Toggle between play and stop."""
        if self._is_playing:
            self.stop()
        else:
            self.play()
    
    def set_bpm(self, bpm: int) -> None:
        """Set BPM (beats per minute).
        
        Args:
            bpm: New BPM value (20-300)
        """
        logger.info(f"Set BPM requested: {bpm}")
        if not (20 <= bpm <= 300):
            logger.warning(f"BPM {bpm} out of range, clamping to 20-300")
            bpm = max(20, min(300, bpm))
        
        self._bpm = bpm
        
        # Usar PresentationModel para establecer BPM
        self._model.set_bpm(bpm)
        
        self.bpm_changed.emit(bpm)
        logger.info(f"BPM changed to {bpm} via PresentationModel")
    
    def set_position(self, step: int) -> None:
        """Set playhead position.
        
        Args:
            step: New step position
        """
        self._current_step = step
        self.position_changed.emit(step)
        
        # También actualizar en el modelo
        ticks = step * 480  # Convertir pasos a ticks
        self._model.set_position(ticks)
    
    def set_loop(self, enabled: bool, start: int = 0, end: int = 15) -> None:
        """Set loop region.
        
        Args:
            enabled: Whether loop is enabled
            start: Loop start step
            end: Loop end step
        """
        self._loop_enabled = enabled
        self._loop_start = start
        self._loop_end = end
        
        # Usar PresentationModel para establecer loop
        self._model.set_loop(enabled, start, end)
        
        self.loop_changed.emit(enabled, start, end)
        logger.info(
            f"Loop {'enabled' if enabled else 'disabled'}: {start}-{end}"
        )
    
    def set_sequencer(self, sequencer) -> None:
        """Set the sequencer for playback.
        
        Args:
            sequencer: Sequencer widget instance
        """
        self._sequencer = sequencer
        logger.info("Sequencer connected to playback controller")
    
    def set_app_core(self, app_core: "AppCore") -> None:
        """Set or update the app core reference.
        
        Args:
            app_core: New AppCore instance
            
        Note:
            This is maintained for backward compatibility.
            The controller now uses PresentationModel internally.
        """
        self._app_core = app_core
        logger.debug("App core updated in PlaybackController (legacy)")
    
    # === Signal Handlers ===
    
    def _on_playback_state_changed(self, state: str) -> None:
        """Manejar cambio de estado de reproducción desde el modelo."""
        if state == "playing":
            if not self._is_playing:
                self._is_playing = True
                self.playback_started.emit()
        elif state == "stopped":
            if self._is_playing:
                self._is_playing = False
                self.playback_stopped.emit()
    
    def _on_position_changed(self, tick: int) -> None:
        """Manejar cambio de posición desde el modelo."""
        # Convertir ticks a pasos
        step = tick // 480
        self._current_step = step
        self.position_changed.emit(step)
    
    def _on_bpm_changed(self, bpm: int) -> None:
        """Manejar cambio de BPM desde el modelo."""
        self._bpm = bpm
        self.bpm_changed.emit(bpm)
