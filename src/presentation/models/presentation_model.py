"""Presentation Model - Modelo de presentación para JustBeat-DAW.

Este módulo proporciona una capa de abstracción entre la capa de presentación
(y sus widgets) y los handlers de la capa de aplicación. Implementa el patrón
Presentation Model (PM) que actúa como un facade para los servicios.

La arquitectura es:
    UI Widgets <-> Presenters <-> PresentationModel <-> Handlers <-> Domain

Este diseño sigue los principios de:
- Inyección de dependencias
- Separación de responsabilidades
- Acoplamiento débil mediante interfaces
"""

from typing import Optional, Callable, List
from pathlib import Path
import logging

from PySide6.QtCore import QObject, Signal

from src.application.app_core import AppCore
from src.application.handlers.project_handler import ProjectHandler
from src.application.handlers.transport_handler import TransportHandler
from src.domain.transport_state import TransportState
from src.application.handlers.track_handler import TrackHandler
from src.application.handlers.note_handler import NoteHandler
from src.application.handlers.automation_handler import AutomationHandler

from src.domain.entities.project import Project
from src.domain.entities.track import Track
from src.domain.entities.note import Note
from src.domain.events.event_bus import DomainEvent


logger = logging.getLogger(__name__)


class PresentationModel(QObject):
    """Modelo de presentación - Fachada para los handlers de aplicación.
    
    Proporciona una interfaz unificada para que los widgets y controllers
    de la capa de presentación interactúen con los handlers de la capa de aplicación.
    
    Señales:
        project_loaded: Emitido cuando se carga un proyecto (project: Project)
        project_saved: Emitido cuando se guarda un proyecto (path: str)
        playback_state_changed: Emitido cuando cambia el estado de reproducción (state: str)
        position_changed: Emitido cuando cambia la posición (tick: int)
        bpm_changed: Emitido cuando cambia el BPM (bpm: int)
        track_added: Emitido cuando se añade una pista (track: Track)
        track_removed: Emitido cuando se elimina una pista (track_id: str)
        track_modified: Emitido cuando se modifica una pista (track_id: str, changes: dict)
        note_added: Emitido cuando se añade una nota (note: Note)
        note_removed: Emitido cuando se elimina una nota (note_id: str)
        modification_changed: Emitido cuando cambia el estado de modificación (modified: bool)
        recording_state_changed: Emitido cuando cambia el estado de grabación (is_recording: bool)
        error_occurred: Emitido cuando ocurre un error (message: str)
    """
    
    # Señales sincronizadas con AppCore
    project_loaded = Signal(object)
    project_saved = Signal(str)
    playback_state_changed = Signal(str)
    position_changed = Signal(int)
    bpm_changed = Signal(int)
    track_added = Signal(object)
    track_removed = Signal(str)
    track_selected = Signal(str)  # track_id
    track_modified = Signal(str, dict)
    note_added = Signal(object)
    note_removed = Signal(str)
    modification_changed = Signal(bool)
    error_occurred = Signal(str)
    active_pattern_changed = Signal(int)  # index
    arrangement_changed = Signal()
    recording_state_changed = Signal(bool)
    
    def __init__(self, app_core: Optional[AppCore] = None):
        """Inicializar el modelo de presentación.
        
        Args:
            app_core: Instancia de AppCore. Si es None, se obtiene la global.
        """
        super().__init__()
        
        if app_core is not None:
            self._app_core = app_core
        else:
            # Import here to avoid circular dependency
            from src.application.app_core import get_app_core
            self._app_core = get_app_core()
        
        # Referencias a handlers (se obtienen bajo demanda)
        self._project_handler: Optional[ProjectHandler] = None
        self._transport_handler: Optional[TransportHandler] = None
        self._track_handler: Optional[TrackHandler] = None
        self._note_handler: Optional[NoteHandler] = None
        self._automation_handler: Optional[AutomationHandler] = None
        
        # Estado local
        self._current_project: Optional[Project] = None
        self._selected_track: Optional[Track] = None
        self._active_pattern_index: int = 0
        self._selected_track_id: Optional[str] = None
        
        # Callbacks registrados por widgets/presenters
        self._position_callbacks: List[Callable[[int], None]] = []
        self._state_callbacks: List[Callable[[TransportState], None]] = []
        
        # Conectar señales de AppCore
        self._connect_app_core_signals()
        
        # Conectar EventBus
        self._connect_event_bus()
        
        logger.info("PresentationModel inicializado")
    
    def _connect_app_core_signals(self) -> None:
        """Conectar señales de AppCore al PresentationModel."""
        if self._app_core is None:
            return
        
        # Re-emitir señales de AppCore
        self._app_core.project_loaded.connect(self._on_project_loaded)
        self._app_core.project_saved.connect(self._on_project_saved)
        self._app_core.playback_state_changed.connect(self._on_playback_state_changed)
        self._app_core.position_changed.connect(self._on_position_changed)
        self._app_core.bpm_changed.connect(self._on_bpm_changed)
        self._app_core.track_added.connect(self._on_track_added)
        self._app_core.track_removed.connect(self._on_track_removed)
        self._app_core.track_selected.connect(self.track_selected.emit)
        self._app_core.modification_changed.connect(self._on_modification_changed)
        self._app_core.error_occurred.connect(self._on_error_occurred)
    
    def _connect_event_bus(self) -> None:
        """Conectar EventBus para recibir eventos de dominio."""
        try:
            from src.domain.events.event_bus import get_event_bus
            event_bus = get_event_bus()
            
            def on_domain_event(event: DomainEvent) -> None:
                logger.debug(f"Evento de dominio recibido: {event.event_type}")
                
                if event.event_type == "project.saved":
                    path = event.data.get("path", "")
                    self.project_saved.emit(path)
                    
                elif event.event_type == "project.modified":
                    self.modification_changed.emit(True)
                    
                elif event.event_type == "transport.started":
                    self.playback_state_changed.emit("playing")
                    
                elif event.event_type == "transport.paused":
                    self.playback_state_changed.emit("paused")
                    
                elif event.event_type == "transport.stopped":
                    self.playback_state_changed.emit("stopped")
                    
                elif event.event_type == "transport.bpm_changed":
                    bpm = event.data.get("bpm", 120)
                    self.bpm_changed.emit(bpm)
                    
                elif event.event_type == "track.removed":
                    track_id = event.data.get("id", "")
                    self.track_removed.emit(track_id)
            
            event_bus.subscribe("*", on_domain_event)
            logger.info("PresentationModel conectado al EventBus")
            
        except Exception as e:
            logger.warning(f"No se pudo conectar al EventBus: {e}")
    
    # === Properties ===
    
    @property
    def app_core(self) -> Optional[AppCore]:
        """Obtener referencia a AppCore."""
        return self._app_core
    
    @property
    def project_handler(self) -> Optional[ProjectHandler]:
        """Obtener el handler de proyectos."""
        if self._project_handler is None and self._app_core:
            self._project_handler = self._app_core.project_handler
        return self._project_handler
    
    @property
    def transport_handler(self) -> Optional[TransportHandler]:
        """Obtener el handler de transporte."""
        if self._transport_handler is None and self._app_core:
            self._transport_handler = self._app_core.transport_handler
        return self._transport_handler
    
    @property
    def track_handler(self) -> Optional[TrackHandler]:
        """Obtener el handler de pistas."""
        if self._track_handler is None and self._app_core:
            self._track_handler = self._app_core.track_handler
        return self._track_handler
    
    @property
    def note_handler(self) -> Optional[NoteHandler]:
        """Obtener el handler de notas."""
        if self._note_handler is None and self._app_core:
            self._note_handler = self._app_core.note_handler
        return self._note_handler
    
    @property
    def automation_handler(self) -> Optional[AutomationHandler]:
        """Obtener el handler de automatización."""
        if self._automation_handler is None and self._app_core:
            self._automation_handler = self._app_core.automation_handler
        return self._automation_handler
    
    @property
    def current_project(self) -> Optional[Project]:
        """Obtener el proyecto actual."""
        if self._current_project is None and self._app_core:
            self._current_project = self._app_core.current_project
        return self._current_project
    
    @property
    def selected_track(self) -> Optional[Track]:
        """Obtener la pista seleccionada."""
        return self._selected_track
    
    @property
    def selected_track_id(self) -> Optional[str]:
        """Obtener el ID de la pista seleccionada."""
        return self._selected_track_id
    
    @property
    def bpm(self) -> int:
        """Obtener el BPM actual."""
        if self._app_core:
            return self._app_core.bpm
        return 120
    
    @property
    def position(self) -> int:
        """Obtener la posición actual."""
        if self._app_core:
            return self._app_core.position
        return 0
    
    @property
    def is_playing(self) -> bool:
        """Verificar si está reproduciendo."""
        if self._app_core:
            return self._app_core.is_playing
        return False
    
    # === Handlers Proxy Methods ===
    # Estos métodos delegan en los handlers correspondientes
    
    # --- Project Operations ---
    
    def new_project(self, name: str = "Untitled Project") -> Optional[Project]:
        """Crear un nuevo proyecto.
        
        Args:
            name: Nombre del proyecto
            
        Returns:
            El proyecto creado o None si falla
        """
        if self.project_handler:
            project = self.project_handler.create_project(name)
            self._current_project = project
            self.project_loaded.emit(project)
            logger.info(f"Nuevo proyecto creado: {name}")
            return project
        return None
    
    def load_project(self, path: Path) -> Optional[Project]:
        """Cargar un proyecto desde archivo.
        
        Args:
            path: Ruta al archivo de proyecto
            
        Returns:
            El proyecto cargado o None si falla
        """
        if self.project_handler:
            project = self.project_handler.load_project(path)
            if project:
                self._current_project = project
                self.project_loaded.emit(project)
                logger.info(f"Proyecto cargado: {path}")
            return project
        return None
    
    def save_project(self, path: Optional[Path] = None) -> bool:
        """Guardar el proyecto actual.
        
        Args:
            path: Ruta de guardado (None para usar la actual)
            
        Returns:
            True si se guardó correctamente
        """
        if self.project_handler and self._current_project:
            # Guardar en el handler
            if path:
                self.project_handler._current_path = path
            success = self.project_handler.save_project(path)
            if success:
                self.project_saved.emit(str(path or self.project_handler._current_path))
                logger.info(f"Proyecto guardado: {path}")
            return success
        return False
    
    # --- Transport Operations ---
    
    def play(self) -> None:
        """Iniciar reproducción."""
        if self._app_core:
            self._app_core.play()
    
    def stop(self) -> None:
        """Detener reproducción."""
        if self._app_core:
            self._app_core.stop()
    
    def pause(self) -> None:
        """Pausar reproducción."""
        if self.transport_handler:
            self.transport_handler.pause()
    
    def set_bpm(self, bpm: int) -> None:
        """Establecer BPM.
        
        Args:
            bpm: Nuevo valor de BPM (20-300)
        """
        bpm = max(20, min(300, bpm))
        if self._app_core:
            self._app_core.set_bpm(bpm)
        self.bpm_changed.emit(bpm)
    
    def set_position(self, tick: int) -> None:
        """Establecer posición de reproducción.
        
        Args:
            tick: Nueva posición en ticks
        """
        if self.transport_handler:
            self.transport_handler.seek(tick)
        self.position_changed.emit(tick)
    
    def set_loop(self, enabled: bool, start: int = 0, end: int = 16) -> None:
        """Establecer región de loop.
        
        Args:
            enabled: Si el loop está habilitado
            start: Inicio del loop en pasos
            end: Fin del loop en pasos
        """
        if self.transport_handler:
            self.transport_handler.set_loop(enabled, start, end)
            
    def toggle_metronome(self) -> bool:
        """Alternar metrónomo."""
        if self._app_core:
            return self._app_core.toggle_metronome()
        return False
        
    def toggle_count_in(self) -> bool:
        """Alternar count-in."""
        if self._app_core:
            return self._app_core.toggle_count_in()
        return False
    
    def toggle_loop(self) -> bool:
        """Alternar loop."""
        if self._app_core:
            return self._app_core.toggle_loop()
        return False
        
    @property
    def metronome_enabled(self) -> bool:
        return self._app_core.metronome_enabled if self._app_core else False
        
    @property
    def count_in_enabled(self) -> bool:
        return self._app_core.count_in_enabled if self._app_core else False
    
    @property
    def loop_enabled(self) -> bool:
        return self._app_core.loop_enabled if self._app_core else False
    
    def start_recording(self) -> bool:
        if self._app_core:
            result = self._app_core.start_recording()
            if result:
                self.recording_state_changed.emit(True)
            return result
        return False
    
    def stop_recording(self) -> bool:
        if self._app_core:
            result = self._app_core.stop_recording()
            if result:
                self.recording_state_changed.emit(False)
            return result
        return False
    
    @property
    def is_recording(self) -> bool:
        return self._app_core.is_recording if self._app_core else False
    
    # --- Track Operations ---
    
    def add_track(self, name: str = "New Track") -> Optional[Track]:
        """Añadir una nueva pista al proyecto.
        
        Args:
            name: Nombre de la pista
            
        Returns:
            La pista creada o None si falla
        """
        if self._app_core:
            return self._app_core.add_track(name)
            
        if self.track_handler and self._current_project:
            # Fallback si no hay AppCore (no debería ocurrir en producción)
            # Aseguramos que pasamos el NOMBRE no el objeto
            track = self._current_project.add_track(name)
            if self.track_handler:
                self.track_handler._tracks_cache[track.id] = track
            self.track_added.emit(track)
            self.modification_changed.emit(True)
            logger.info(f"Pista añadida (fallback): {name}")
            return track
        return None
    
    def remove_track(self, track_id: str) -> bool:
        """Eliminar una pista del proyecto.
        
        Args:
            track_id: ID de la pista a eliminar
            
        Returns:
            True si se eliminó correctamente
        """
        if self._current_project:
            success = self._current_project.remove_track(track_id)
            if success:
                self.track_removed.emit(track_id)
                self.modification_changed.emit(True)
                logger.info(f"Pista eliminada: {track_id}")
            return success
        return False
    
    def select_track(self, track_id: str) -> None:
        """Seleccionar una pista.
        
        Args:
            track_id: ID de la pista a seleccionar
        """
        self._selected_track_id = track_id
        if self._current_project:
            self._selected_track = self._current_project.get_track(track_id)
        self.track_modified.emit(track_id, {"selected": True})
        self.track_selected.emit(track_id)
    
    def set_track_volume(self, track_id: str, volume: float) -> bool:
        """Establecer volumen de una pista.
        
        Args:
            track_id: ID de la pista
            volume: Volumen (0.0 - 1.0)
            
        Returns:
            True si se estableció correctamente
        """
        track = self._current_project.get_track(track_id) if self._current_project else None
        if track and self.track_handler:
            success = self.track_handler.set_volume(track, volume)
            if success:
                self.track_modified.emit(track_id, {"volume": volume})
            return success
        return False
    
    def set_track_pan(self, track_id: str, pan: float) -> bool:
        """Establecer pan de una pista.
        
        Args:
            track_id: ID de la pista
            pan: Pan (-1.0 a 1.0)
            
        Returns:
            True si se estableció correctamente
        """
        track = self._current_project.get_track(track_id) if self._current_project else None
        if track and self.track_handler:
            success = self.track_handler.set_pan(track, pan)
            if success:
                self.track_modified.emit(track_id, {"pan": pan})
            return success
        return False
    
    def set_track_mute(self, track_id: str, muted: bool) -> bool:
        """Establecer mute de una pista.
        
        Args:
            track_id: ID de la pista
            muted: Estado de mute
            
        Returns:
            True si se estableció correctamente
        """
        track = self._current_project.get_track(track_id) if self._current_project else None
        if track:
            track.muted = muted
            self.track_modified.emit(track_id, {"muted": muted})
            return True
        return False
    
    def set_track_solo(self, track_id: str, solo: bool) -> bool:
        """Establecer solo de una pista.
        
        Args:
            track_id: ID de la pista
            solo: Estado de solo
            
        Returns:
            True si se estableció correctamente
        """
        track = self._current_project.get_track(track_id) if self._current_project else None
        if track:
            track.solo = solo
            self.track_modified.emit(track_id, {"solo": solo})
            return True
        return False
    
    # --- Synth Operations ---
    
    def set_synth_parameter(self, track_id: str, param_name: str, value: float) -> bool:
        """Establecer parámetro de sintetizador.
        
        Args:
            track_id: ID de la pista
            param_name: Nombre del parámetro
            value: Valor del parámetro
            
        Returns:
            True si se estableció correctamente
        """
        logger.info(f"Setting synth param {param_name} = {value} for track {track_id}")
        # Emit signal for track modification
        if self._current_project:
            track = self._current_project.get_track(track_id)
            if track:
                self.track_modified.emit(track_id, {param_name: value})
                return True
        return False
    
    # --- Note Operations ---
    
    def add_note(self, track_id: str, note: Note) -> bool:
        """Añadir una nota a una pista.
        
        Args:
            track_id: ID de la pista
            note: Nota a añadir
            
        Returns:
            True si se añadió correctamente
        """
        track = self._current_project.get_track(track_id) if self._current_project else None
        if track and self.note_handler:
            self.note_handler.add_note_to_track(track, note)
            self.note_added.emit(note)
            self.modification_changed.emit(True)
            return True
        return False
    
    def remove_note(self, track_id: str, note_id: str) -> bool:
        """Eliminar una nota de una pista.
        
        Args:
            track_id: ID de la pista
            note_id: ID de la nota a eliminar
            
        Returns:
            True si se eliminó correctamente
        """
        track = self._current_project.get_track(track_id) if self._current_project else None
        if track and self.note_handler:
            success = self.note_handler.remove_note_from_track(track, note_id)
            if success:
                self.note_removed.emit(note_id)
                self.modification_changed.emit(True)
            return success
        return False
    
    def get_notes(self, track_id: str) -> List[Note]:
        """Obtener todas las notas de una pista.
        
        Args:
            track_id: ID de la pista
            
        Returns:
            Lista de notas
        """
        track = self._current_project.get_track(track_id) if self._current_project else None
        if track and self.note_handler:
            return self.note_handler.get_track_notes(track)
        return []
    
    # --- Pattern Operations ---
    
    def set_pattern_step(self, track_id: str, pattern_index: int, step: int, active: bool) -> bool:
        """Establecer el estado de un paso en un patrón.
        
        Args:
            track_id: ID de la pista
            pattern_index: Índice del patrón
            step: Paso a modificar
            active: Estado activo
            
        Returns:
            True si se estableció correctamente
        """
        track = self._current_project.get_track(track_id) if self._current_project else None
        if track and pattern_index < len(track.patterns):
            pattern = track.patterns[pattern_index]
            pattern.set_step(step, active)
            self.modification_changed.emit(True)
            return True
        return False
    
    def set_pattern_note(self, track_id: str, pattern_index: int, step: int, note: Note) -> bool:
        """Establecer una nota en un paso de un patrón.
        
        Args:
            track_id: ID de la pista
            pattern_index: Índice del patrón
            step: Paso a modificar
            note: Nota a establecer
            
        Returns:
            True si se estableció correctamente
        """
        track = self._current_project.get_track(track_id) if self._current_project else None
        if track and pattern_index < len(track.patterns):
            pattern = track.patterns[pattern_index]
            pattern.set_note(step, note)
            self.modification_changed.emit(True)
            return True
        return False
    
    # --- Callback Registration ---
    
    def register_position_callback(self, callback: Callable[[int], None]) -> None:
        """Registrar callback para cambios de posición.
        
        Args:
            callback: Función a llamar con la nueva posición
        """
        if callback not in self._position_callbacks:
            self._position_callbacks.append(callback)
    
    def register_state_callback(self, callback: Callable[[TransportState], None]) -> None:
        """Registrar callback para cambios de estado.
        
        Args:
            callback: Función a llamar con el nuevo estado
        """
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)

    # === Pattern Operations ===

    def add_pattern(self, name: str = "New Pattern") -> Optional[object]:
        """Añadir un nuevo patrón al proyecto.
        
        Args:
            name: Nombre del patrón
            
        Returns:
            El patrón creado o None si falla
        """
        if not self.current_project:
            return None
        try:
            pattern = self.current_project.add_pattern(name=name)
            if pattern:
                self.modification_changed.emit(True)
            return pattern
        except Exception:
            return None

    def get_active_pattern_index(self) -> int:
        """Obtener el índice del patrón activo."""
        if self.current_project:
            return self.current_project.active_pattern_index
        return self._active_pattern_index

    def set_active_pattern_index(self, index: int) -> None:
        """Establecer el patrón activo por índice."""
        if self.current_project:
            if self.current_project.set_active_pattern(index):
                self._active_pattern_index = index
                self.active_pattern_changed.emit(index)
        else:
            self._active_pattern_index = index
            self.active_pattern_changed.emit(index)

    def add_pattern_clip(self, track_id: str, start_tick: int) -> bool:
        """Añadir un clip de patrón al arreglo.
        
        Args:
            track_id: ID de la pista
            start_tick: Posición de inicio
            
        Returns:
            True si se añadió correctamente
        """
        if not self.current_project:
            return False
            
        pattern = self.current_project.get_active_pattern()
        if not pattern:
            return False
        
        from src.application.handlers.arrangement_handler import ArrangementHandler
        from src.domain.entities.clip import ClipType
        handler = ArrangementHandler()
        
        duration = pattern.length * 480
        
        clip = handler.add_clip(
            project=self.current_project,
            track_id=track_id,
            name=pattern.name,
            clip_type=ClipType.PATTERN,
            start_tick=start_tick,
            duration=duration,
            content_id=pattern.id
        )
        
        if clip:
            self.arrangement_changed.emit()
            self.modification_changed.emit(True)
            return True
        return False

    # === Audio Data (for Visualizer) ===

    def get_audio_levels(self) -> tuple:
        """Obtener niveles RMS (L, R) desde AudioManager."""
        if self._app_core:
            return self._app_core.get_audio_levels()
        return (0.0, 0.0)

    def get_waveform_data(self, num_samples: int = 256) -> tuple:
        """Obtener datos de forma de onda."""
        if self._app_core:
            return self._app_core.get_waveform_data(num_samples)
        return ([0.0] * num_samples, [0.0] * num_samples)

    # === Signal Handlers ===
    
    def _on_project_loaded(self, project: Project) -> None:
        """Manejar señal de proyecto cargado."""
        self._current_project = project
        self.project_loaded.emit(project)
    
    def _on_project_saved(self, path: str) -> None:
        """Manejar señal de proyecto guardado."""
        self.project_saved.emit(path)
    
    def _on_playback_state_changed(self, state: str) -> None:
        """Manejar cambio de estado de reproducción."""
        self.playback_state_changed.emit(state)
    
    def _on_position_changed(self, tick: int) -> None:
        """Manejar cambio de posición."""
        self.position_changed.emit(tick)
        for callback in self._position_callbacks:
            callback(tick)
    
    def _on_bpm_changed(self, bpm: int) -> None:
        """Manejar cambio de BPM."""
        self.bpm_changed.emit(bpm)
    
    def _on_track_added(self, track: Track) -> None:
        """Manejar pista añadida."""
        self.track_added.emit(track)
    
    def _on_track_removed(self, track_id: str) -> None:
        """Manejar pista eliminada."""
        self.track_removed.emit(track_id)
    
    def _on_modification_changed(self, modified: bool) -> None:
        """Manejar cambio de estado de modificación."""
        self.modification_changed.emit(modified)
    
    def _on_error_occurred(self, message: str) -> None:
        """Manejar error."""
        self.error_occurred.emit(message)


# === Global Instance ===

_presentation_model: Optional[PresentationModel] = None


def get_presentation_model() -> PresentationModel:
    """Obtener la instancia global del modelo de presentación.
    
    Returns:
        Instancia global de PresentationModel
    """
    global _presentation_model
    if _presentation_model is None:
        _presentation_model = PresentationModel()
    return _presentation_model


def initialize_presentation_model(app_core: AppCore) -> PresentationModel:
    """Inicializar el modelo de presentación con un AppCore específico.
    
    Args:
        app_core: Instancia de AppCore a usar
        
    Returns:
        Instancia de PresentationModel
    """
    global _presentation_model
    _presentation_model = PresentationModel(app_core)
    return _presentation_model
