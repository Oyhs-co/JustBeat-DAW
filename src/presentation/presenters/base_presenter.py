"""Base Presenter - Clase base para presentadores de JustBeat-DAW.

Este módulo proporciona una clase base para los presentadores en la arquitectura
Model-View-Presenter (MVP). Los presentadores manejan la lógica de presentación
y se comunican entre la vista (widget) y el modelo (PresentationModel).

Patrón de uso:
    1. Crear un presenter que herede de BasePresenter
    2. Implementar los métodos de actualización de vista
    3. Conectar las señales del widget a los métodos del presenter
    4. El presenter actualiza el modelo y responde a cambios del modelo
"""

from typing import Optional, Any, Dict, List, Callable
import logging
from abc import ABC, abstractmethod

from PySide6.QtCore import QObject, Signal

from src.presentation.models.presentation_model import (
    PresentationModel,
    get_presentation_model
)


logger = logging.getLogger(__name__)


class BasePresenter(QObject, ABC):
    """Presentador base para widgets.
    
    Clase base abstracta que proporciona funcionalidad común para todos
    los presentadores. Maneja la comunicación entre el widget (vista)
    y el PresentationModel.
    
    Attributes:
        _widget: Referencia al widget asociado
        _model: Referencia al modelo de presentación
        _is_updating: Bandera para evitar actualizaciones recursivas
    
    Signals:
        view_updated: Emitido cuando la vista necesita actualizarse
    """
    
    view_updated = Signal()
    
    def __init__(
        self,
        widget: QObject,
        presentation_model: Optional[PresentationModel] = None
    ):
        """Inicializar el presentador.
        
        Args:
            widget: Widget asociado al presentador
            presentation_model: Modelo de presentación a usar.
                               Si es None, usa el global.
        """
        super().__init__()
        self._widget = widget
        self._model = presentation_model or get_presentation_model()
        self._is_updating = False
        
        # Conectar señales del modelo
        self._connect_model_signals()
        
        logger.debug(f"{self.__class__.__name__} inicializado")
    
    @property
    def widget(self) -> QObject:
        """Obtener el widget asociado."""
        return self._widget
    
    @property
    def model(self) -> PresentationModel:
        """Obtener el modelo de presentación."""
        return self._model
    
    @property
    def is_updating(self) -> bool:
        """Verificar si está actualizando (para evitar recursión)."""
        return self._is_updating
    
    def _connect_model_signals(self) -> None:
        """Conectar señales del modelo. Override en subclases."""
        pass
    
    def _begin_update(self) -> None:
        """Iniciar actualización. Evita actualizaciones recursivas."""
        self._is_updating = True
    
    def _end_update(self) -> None:
        """Finalizar actualización."""
        self._is_updating = False
    
    def update_view(self) -> None:
        """Actualizar la vista con datos del modelo.
        
        Método principal que debe ser implementado por subclases.
        """
        if self._is_updating:
            return
        self._begin_update()
        try:
            self._update_view_impl()
        finally:
            self._end_update()
        self.view_updated.emit()
    
    @abstractmethod
    def _update_view_impl(self) -> None:
        """Implementación concreta de actualización de vista.
        
        Debe ser implementado por subclases.
        """
        pass
    
    # === Helper Methods ===
    
    def get_tracks(self) -> List[Any]:
        """Obtener todas las pistas del proyecto."""
        project = self._model.current_project
        if project:
            return project.get_tracks()
        return []
    
    def get_selected_track_id(self) -> Optional[str]:
        """Obtener el ID de la pista seleccionada."""
        return self._model.selected_track_id
    
    def get_current_project(self) -> Optional[Any]:
        """Obtener el proyecto actual."""
        return self._model.current_project
    
    def show_error(self, message: str) -> None:
        """Mostrar un mensaje de error."""
        logger.error(f"Error en {self.__class__.__name__}: {message}")
        self._model.error_occurred.emit(message)


class TransportPresenter(BasePresenter):
    """Presentador para controles de transporte.
    
    Maneja la lógica de reproducción, parada, pausa y cambio de tempo.
    """
    
    def __init__(
        self,
        widget: QObject,
        presentation_model: Optional[PresentationModel] = None
    ):
        """Inicializar el presentador de transporte."""
        super().__init__(widget, presentation_model)
        
        # Señales del widget que conectamos
        self._widget.play_clicked.connect(self._on_play_clicked)
        self._widget.stop_clicked.connect(self._on_stop_clicked)
        self._widget.pause_clicked.connect(self._on_pause_clicked)
        self._widget.bpm_changed.connect(self._on_bpm_changed)
        self._widget.position_changed.connect(self._on_position_changed)
    
    def _connect_model_signals(self) -> None:
        """Conectar señales del modelo de transporte."""
        self._model.playback_state_changed.connect(self._on_playback_state_changed)
        self._model.position_changed.connect(self._on_position_update)
        self._model.bpm_changed.connect(self._on_bpm_update)
    
    def _update_view_impl(self) -> None:
        """Actualizar vista con estado actual."""
        # Actualizar estado de botones según reproducción
        # Esta implementación depende del widget específico
        pass
    
    # === Widget Event Handlers ===
    
    def _on_play_clicked(self) -> None:
        """Manejar clic en botón de reproducción."""
        self._model.play()
    
    def _on_stop_clicked(self) -> None:
        """Manejar clic en botón de parada."""
        self._model.stop()
    
    def _on_pause_clicked(self) -> None:
        """Manejar clic en botón de pausa."""
        self._model.pause()
    
    def _on_bpm_changed(self, bpm: int) -> None:
        """Manejar cambio de BPM."""
        self._model.set_bpm(bpm)
    
    def _on_position_changed(self, tick: int) -> None:
        """Manejar cambio de posición."""
        self._model.set_position(tick)
    
    # === Model Signal Handlers ===
    
    def _on_playback_state_changed(self, state: str) -> None:
        """Manejar cambio de estado de reproducción."""
        self.update_view()
    
    def _on_position_update(self, tick: int) -> None:
        """Manejar actualización de posición."""
        self.update_view()
    
    def _on_bpm_update(self, bpm: int) -> None:
        """Manejar actualización de BPM."""
        self.update_view()


class TrackListPresenter(BasePresenter):
    """Presentador para lista de pistas.
    
    Maneja la lógica de creación, eliminación y modificación de pistas.
    """
    
    def __init__(
        self,
        widget: QObject,
        presentation_model: Optional[PresentationModel] = None
    ):
        """Inicializar el presentador de lista de pistas."""
        super().__init__(widget, presentation_model)
        
        # Conectar señales del widget
        self._widget.track_selected.connect(self._on_track_selected)
        self._widget.track_added.connect(self._on_track_added)
        self._widget.track_removed.connect(self._on_track_removed)
        self._widget.track_modified.connect(self._on_track_modified)
    
    def _connect_model_signals(self) -> None:
        """Conectar señales del modelo de pistas."""
        self._model.track_added.connect(self._on_model_track_added)
        self._model.track_removed.connect(self._on_model_track_removed)
        self._model.track_modified.connect(self._on_model_track_modified)
    
    def _update_view_impl(self) -> None:
        """Actualizar lista de pistas."""
        tracks = self.get_tracks()
        # Actualizar el widget con las pistas
        # Esta implementación depende del widget específico
        pass
    
    # === Widget Event Handlers ===
    
    def _on_track_selected(self, track_id: str) -> None:
        """Manejar selección de pista."""
        self._model.select_track(track_id)
    
    def _on_track_added(self, name: str) -> None:
        """Manejar añadir pista."""
        self._model.add_track(name)
    
    def _on_track_removed(self, track_id: str) -> None:
        """Manejar eliminar pista."""
        self._model.remove_track(track_id)
    
    def _on_track_modified(self, track_id: str, changes: Dict[str, Any]) -> None:
        """Manejar modificación de pista."""
        # Aplicar cambios según el tipo
        if "volume" in changes:
            self._model.set_track_volume(track_id, changes["volume"])
        if "pan" in changes:
            self._model.set_track_pan(track_id, changes["pan"])
        if "muted" in changes:
            self._model.set_track_mute(track_id, changes["muted"])
        if "solo" in changes:
            self._model.set_track_solo(track_id, changes["solo"])
    
    # === Model Signal Handlers ===
    
    def _on_model_track_added(self, track: Any) -> None:
        """Manejar pista añadida desde el modelo."""
        self.update_view()
    
    def _on_model_track_removed(self, track_id: str) -> None:
        """Manejar pista eliminada desde el modelo."""
        self.update_view()
    
    def _on_model_track_modified(self, track_id: str, changes: Dict) -> None:
        """Manejar pista modificada desde el modelo."""
        self.update_view()


class SequencerPresenter(BasePresenter):
    """Presentador para el step sequencer.
    
    Maneja la lógica de edición de pasos y notas en el secuenciador.
    """
    
    def __init__(
        self,
        widget: QObject,
        presentation_model: Optional[PresentationModel] = None
    ):
        """Inicializar el presentador del secuenciador."""
        super().__init__(widget, presentation_model)
        
        # Conectar señales del widget
        self._widget.step_toggled.connect(self._on_step_toggled)
        self._widget.step_changed.connect(self._on_step_changed)
        self._widget.pattern_changed.connect(self._on_pattern_changed)
    
    def _connect_model_signals(self) -> None:
        """Conectar señales del modelo."""
        self._model.position_changed.connect(self._on_position_changed)
        self._model.track_modified.connect(self._on_track_modified)
    
    def _update_view_impl(self) -> None:
        """Actualizar estado del secuenciador."""
        # Actualizar pasos activos según el modelo
        pass
    
    # === Widget Event Handlers ===
    
    def _on_step_toggled(
        self,
        track_id: str,
        pattern_index: int,
        step: int,
        active: bool
    ) -> None:
        """Manejar toggled de paso."""
        self._model.set_pattern_step(
            track_id, pattern_index, step, active
        )
    
    def _on_step_changed(self, step: int) -> None:
        """Manejar cambio de paso actual."""
        # Posición del playhead
        pass
    
    def _on_pattern_changed(self, pattern_index: int) -> None:
        """Manejar cambio de patrón."""
        pass
    
    # === Model Signal Handlers ===
    
    def _on_position_changed(self, tick: int) -> None:
        """Manejar cambio de posición."""
        self.update_view()
    
    def _on_track_modified(self, track_id: str, changes: Dict) -> None:
        """Manejar modificación de pista."""
        self.update_view()


class PianoRollPresenter(BasePresenter):
    """Presentador para el piano roll.
    
    Maneja la edición de notas en el piano roll.
    """
    
    def __init__(
        self,
        widget: QObject,
        presentation_model: Optional[PresentationModel] = None
    ):
        """Inicializar el presentador del piano roll."""
        super().__init__(widget, presentation_model)
        
        # Conectar señales del widget
        self._widget.note_added.connect(self._on_note_added)
        self._widget.note_removed.connect(self._on_note_removed)
        self._widget.note_modified.connect(self._on_note_modified)
        self._widget.note_clicked.connect(self._on_note_clicked)
    
    def _connect_model_signals(self) -> None:
        """Conectar señales del modelo."""
        self._model.note_added.connect(self._on_model_note_added)
        self._model.note_removed.connect(self._on_model_note_removed)
        self._model.track_selected.connect(self._on_track_selected)
    
    def _update_view_impl(self) -> None:
        """Actualizar notas del piano roll."""
        track_id = self.get_selected_track_id()
        if track_id:
            notes = self._model.get_notes(track_id)
            # Actualizar widget con notas
            pass
    
    # === Widget Event Handlers ===
    
    def _on_note_added(self, track_id: str, note: Any) -> None:
        """Manejar nota añadida."""
        self._model.add_note(track_id, note)
    
    def _on_note_removed(self, track_id: str, note_id: str) -> None:
        """Manejar nota eliminada."""
        self._model.remove_note(track_id, note_id)
    
    def _on_note_modified(self, note_id: str, changes: Dict[str, Any]) -> None:
        """Manejar nota modificada."""
        # Implementar modificación de nota
        pass
    
    def _on_note_clicked(self, pitch: int) -> None:
        """Manejar clic en nota del piano roll."""
        # Reproducir nota
        pass
    
    # === Model Signal Handlers ===
    
    def _on_model_note_added(self, note: Any) -> None:
        """Manejar nota añadida desde el modelo."""
        self.update_view()
    
    def _on_model_note_removed(self, note_id: str) -> None:
        """Manejar nota eliminada desde el modelo."""
        self.update_view()
    
    def _on_track_selected(self, track_id: str) -> None:
        """Manejar pista seleccionada."""
        self.update_view()
