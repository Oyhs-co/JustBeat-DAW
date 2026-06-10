"""MIDI Recording Handler - Gestión de grabación MIDI.

Coordina la grabación MIDI entre la UI, el MIDIRecorder,
y los servicios de transporte y tracks.
"""

from typing import Optional, Dict, List, Callable
from pathlib import Path
import logging

from src.infrastructure.midi.midi_recorder import (
    MIDIRecorder, MIDIRecordingState, MIDICaptureEvent,
    MIDITake,
)

logger = logging.getLogger(__name__)


class MIDIRecordingHandler:
    """Handler para operaciones de grabación y reproducción MIDI.

    Coordina el MIDIRecorder con la aplicación, maneja
    selección de dispositivos, routing de tracks a canales,
    cuantización al grabar, overdub, y loop recording.

    Signals (vía callbacks):
        event_captured(event)
        recording_started()
        recording_stopped(count)
        device_changed(device_name)
        track_routed(track_id, channel)
    """

    def __init__(
        self,
        recorder: Optional[MIDIRecorder] = None,
    ):
        """Inicializar MIDIRecordingHandler.

        Args:
            recorder: MIDIRecorder instance
            (se crea por defecto si None)
        """
        self._recorder = recorder or MIDIRecorder()

        # Estado
        self._input_device: Optional[str] = None
        self._quantize_enabled: bool = False
        self._quantize_grid: int = 120
        self._overdub_enabled: bool = False

        # MIDI clock sync
        self._midi_clock_sync: bool = False
        self._midi_clock_master: bool = True

        # Callbacks
        self._on_event_captured: Optional[
            Callable[[MIDICaptureEvent], None]
        ] = None
        self._on_recording_started: Optional[
            Callable[[], None]
        ] = None
        self._on_recording_stopped: Optional[
            Callable[[int], None]
        ] = None
        self._on_state_changed: Optional[
            Callable[[MIDIRecordingState], None]
        ] = None

        # Conectar callbacks del recorder
        self._recorder.set_on_event_captured(
            self._on_event_captured_callback
        )
        self._recorder.set_on_state_changed(
            self._on_recorder_state_changed
        )

        logger.info("MIDIRecordingHandler inicializado")

    # === Callbacks ===

    def set_on_event_captured(
        self, callback: Callable[[MIDICaptureEvent], None]
    ) -> None:
        self._on_event_captured = callback

    def set_on_recording_started(
        self, callback: Callable[[], None]
    ) -> None:
        self._on_recording_started = callback

    def set_on_recording_stopped(
        self, callback: Callable[[int], None]
    ) -> None:
        self._on_recording_stopped = callback

    def set_on_state_changed(
        self, callback: Callable[[MIDIRecordingState], None]
    ) -> None:
        self._on_state_changed = callback

    # === Dispositivos MIDI ===

    def get_input_devices(self) -> List[str]:
        """Obtener dispositivos MIDI de entrada disponibles."""
        return self._recorder.get_input_devices()

    def set_input_device(self, device_name: str) -> bool:
        """Seleccionar dispositivo MIDI de entrada.

        Args:
            device_name: Nombre del dispositivo

        Returns:
            True si se seleccionó
        """
        result = self._recorder.set_input_device(device_name)
        if result:
            self._input_device = device_name
        return result

    @property
    def input_device(self) -> Optional[str]:
        return self._input_device

    # === Routing de Tracks ===

    def route_track(
        self, track_id: str, midi_channel: int = 0
    ) -> None:
        """Rutear un track a un canal MIDI para grabación.

        Args:
            track_id: ID del track
            midi_channel: Canal MIDI (0-15)
        """
        self._recorder.route_track(track_id, midi_channel)
        logger.info(
            f"Track {track_id} ruteado a canal MIDI "
            f"{midi_channel}"
        )

    def unroute_track(self, track_id: str) -> None:
        """Desconectar track del MIDI."""
        self._recorder.unroute_track(track_id)

    def get_routed_tracks(self) -> Dict[str, int]:
        """Obtener tracks ruteados y sus canales."""
        return dict(
            self._recorder._track_channels
        )

    # === Cuantización ===

    @property
    def quantize_enabled(self) -> bool:
        return self._quantize_enabled

    @property
    def quantize_grid(self) -> int:
        return self._quantize_grid

    def set_quantize(
        self, enabled: bool, grid: int = 120
    ) -> None:
        """Configurar cuantización al grabar.

        Args:
            enabled: Activar/desactivar
            grid: Grid en ticks (120 = 32nd notes)
        """
        self._quantize_enabled = enabled
        self._quantize_grid = grid
        self._recorder.set_quantize(enabled, grid)

    # === Overdub ===

    @property
    def overdub_enabled(self) -> bool:
        return self._overdub_enabled

    def set_overdub(self, enabled: bool) -> None:
        """Alternar overdub mode."""
        self._overdub_enabled = enabled
        self._recorder.set_overdub(enabled)

    # === MIDI Clock Sync ===

    @property
    def midi_clock_sync(self) -> bool:
        return self._midi_clock_sync

    @property
    def midi_clock_master(self) -> bool:
        return self._midi_clock_master

    def set_midi_clock_sync(
        self, enabled: bool, master: bool = True
    ) -> None:
        """Configurar sincronización MIDI clock.

        Args:
            enabled: Activar sync
            master: True = master, False = slave
        """
        self._midi_clock_sync = enabled
        self._midi_clock_master = master
        logger.info(
            f"MIDI Clock: {'master' if master else 'slave'}"
            if enabled else "MIDI Clock: off"
        )

    # === Grabación ===

    @property
    def is_recording(self) -> bool:
        return (
            self._recorder.state
            == MIDIRecordingState.RECORDING
        )

    @property
    def state(self) -> MIDIRecordingState:
        return self._recorder.state

    def start_recording(self, bpm: int = 120) -> bool:
        """Iniciar grabación MIDI.

        Args:
            bpm: BPM para tick calculation

        Returns:
            True si se inició
        """
        result = self._recorder.start_recording(bpm)

        if result:
            if self._on_recording_started:
                self._on_recording_started()
            logger.info(
                f"Grabación MIDI iniciada (BPM={bpm})"
            )

        return result

    def stop_recording(self) -> Dict[str, List[MIDICaptureEvent]]:
        """Detener grabación MIDI.

        Returns:
            Eventos capturados por track
        """
        result = self._recorder.stop_recording()
        total = sum(len(v) for v in result.values())

        if self._on_recording_stopped:
            self._on_recording_stopped(total)

        if total > 0:
            logger.info(
                f"Grabación MIDI detenida: "
                f"{total} eventos en "
                f"{len(result)} tracks"
            )

        return result

    # === Eventos Capturados ===

    def get_captured_events(
        self, track_id: Optional[str] = None
    ) -> List[MIDICaptureEvent]:
        """Obtener eventos capturados.

        Args:
            track_id: Filtrar por track

        Returns:
            Lista de eventos
        """
        return self._recorder.get_captured_events(track_id)

    def clear_captured(self) -> None:
        """Limpiar eventos capturados."""
        self._recorder.clear_captured()

    # === Takes ===

    def get_takes(self, track_id: str) -> List[MIDITake]:
        """Obtener takes MIDI de un track."""
        return self._recorder.get_takes(track_id)

    def clear_takes(self, track_id: Optional[str] = None) -> None:
        """Limpiar takes."""
        self._recorder.clear_takes(track_id)

    # === Exportación ===

    def export_to_midi(
        self, file_path: Path, bpm: int = 120
    ) -> bool:
        """Exportar eventos capturados a MIDI file.

        Args:
            file_path: Ruta de salida
            bpm: BPM del proyecto

        Returns:
            True si se exportó
        """
        return self._recorder.export_to_midi(file_path, bpm)

    # === Loop Record ===

    def set_loop_record(
        self, enabled: bool, start: int = 0, end: int = 0
    ) -> None:
        """Configurar loop recording MIDI."""
        self._recorder.set_loop_record(enabled, start, end)

    # === Callbacks internos ===

    def _on_event_captured_callback(
        self, event: MIDICaptureEvent
    ) -> None:
        if self._on_event_captured:
            self._on_event_captured(event)

    def _on_recorder_state_changed(
        self, state: MIDIRecordingState
    ) -> None:
        if self._on_state_changed:
            self._on_state_changed(state)

    # === Cleanup ===

    def shutdown(self) -> None:
        """Apagar handler y recorder."""
        self._recorder.shutdown()
        logger.info("MIDIRecordingHandler apagado")
