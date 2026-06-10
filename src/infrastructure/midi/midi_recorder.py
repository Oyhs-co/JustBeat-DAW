"""MIDI Recorder - Grabación de MIDI en tiempo real.

Captura mensajes MIDI desde dispositivos de entrada,
los almacena con timestamps precisos, y permite
exportar a formato MIDI file.
"""

from typing import Optional, Dict, List, Callable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
import time
from collections import defaultdict


logger = logging.getLogger(__name__)


try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False
    mido = None  # type: ignore[assignment]


class MIDIRecordingState(Enum):
    """Estado de grabación MIDI."""
    IDLE = "idle"
    COUNT_IN = "count_in"
    RECORDING = "recording"
    STOPPED = "stopped"


@dataclass
class MIDICaptureEvent:
    """Evento MIDI capturado.

    Attributes:
        message: Mensaje MIDI
        tick: Posición en ticks
        track_id: ID del track destino
    """
    message: "mido.Message"
    tick: int
    track_id: str

    def to_dict(self) -> dict:
        return {
            "type": self.message.type,
            "note": getattr(self.message, "note", 0),
            "velocity": getattr(self.message, "velocity", 0),
            "control": getattr(self.message, "control", 0),
            "value": getattr(self.message, "value", 0),
            "tick": self.tick,
            "track_id": self.track_id,
            "channel": self.message.channel if hasattr(
                self.message, "channel"
            ) else 0,
        }


@dataclass
class MIDITake:
    """Toma de grabación MIDI."""
    take_number: int
    events: List[MIDICaptureEvent] = field(
        default_factory=list
    )
    start_tick: int = 0
    end_tick: int = 0
    duration_ticks: int = 0
    track_id: str = ""


class MIDIRecorder:
    """Grabador de MIDI en tiempo real.

    Captura mensajes MIDI entrantes con timestamps de tick,
    soporta múltiples tracks, cuantización al grabar,
    overdub, y loop recording.
    """

    PPQN = 480  # Pulses per quarter note

    def __init__(
        self,
        ticks_per_beat: int = 480,
    ):
        """Inicializar MIDIRecorder.

        Args:
            ticks_per_beat: Resolución de ticks
        """
        self._ticks_per_beat = ticks_per_beat

        # Estado
        self._state = MIDIRecordingState.IDLE
        self._captured_events: List[MIDICaptureEvent] = []
        self._input_device: Optional[str] = None
        self._input_port: Optional["mido.ports.BaseInput"] = None
        self._midi_thread: Optional[threading.Thread] = None
        self._midi_lock = threading.Lock()

        # Tick tracking
        self._current_tick: int = 0
        self._tick_rate: float = 0.0  # ticks per second
        self._start_time: float = 0.0

        # Track routing
        self._track_channels: Dict[str, int] = {}
        self._active_tracks: List[str] = []

        # Options
        self._quantize_on_record: bool = False
        self._quantize_grid: int = 120  # 32nd notes
        self._overdub: bool = False
        self._loop_record: bool = False
        self._loop_start: int = 0
        self._loop_end: int = 0

        # Takes
        self._takes: Dict[str, List[MIDITake]] = defaultdict(
            list
        )

        # Callbacks
        self._on_event_captured: Optional[
            Callable[[MIDICaptureEvent], None]
        ] = None
        self._on_state_changed: Optional[
            Callable[[MIDIRecordingState], None]
        ] = None

        logger.info("MIDIRecorder inicializado")

    # === Callbacks ===

    def set_on_event_captured(
        self, callback: Callable[[MIDICaptureEvent], None]
    ) -> None:
        self._on_event_captured = callback

    def set_on_state_changed(
        self, callback: Callable[[MIDIRecordingState], None]
    ) -> None:
        self._on_state_changed = callback

    # === Configuración ===

    @property
    def state(self) -> MIDIRecordingState:
        return self._state

    @property
    def ticks_per_beat(self) -> int:
        return self._ticks_per_beat

    def set_input_device(self, device_name: str) -> bool:
        """Seleccionar dispositivo MIDI de entrada.

        Args:
            device_name: Nombre del dispositivo

        Returns:
            True si se encontró
        """
        if not HAS_MIDO:
            return False

        available = mido.get_input_names()
        for name in available:
            if device_name.lower() in name.lower():
                self._input_device = name
                logger.info(
                    f"Dispositivo MIDI: {name}"
                )
                return True

        logger.warning(
            f"Dispositivo MIDI no encontrado: "
            f"{device_name}"
        )
        return False

    def get_input_devices(self) -> List[str]:
        """Obtener lista de dispositivos MIDI disponibles."""
        if not HAS_MIDO:
            return []
        return mido.get_input_names()

    def set_quantize(
        self, enabled: bool, grid: int = 120
    ) -> None:
        """Configurar cuantización al grabar.

        Args:
            enabled: Activar/desactivar
            grid: Grid en ticks (120 = 32nd notes)
        """
        self._quantize_on_record = enabled
        self._quantize_grid = max(1, grid)

    def set_overdub(self, enabled: bool) -> None:
        """Configurar overdub (grabar sobre eventos existentes)."""
        self._overdub = enabled

    def set_loop_record(
        self, enabled: bool, start: int = 0, end: int = 0
    ) -> None:
        """Configurar loop recording."""
        self._loop_record = enabled
        self._loop_start = start
        self._loop_end = end

    def set_bpm(self, bpm: int) -> None:
        """Actualizar tick rate basado en BPM.

        Args:
            bpm: Beats per minute
        """
        self._tick_rate = (
            bpm * self._ticks_per_beat / 60.0
        )

    # === Track Routing ===

    def route_track(
        self, track_id: str, midi_channel: int = 0
    ) -> None:
        """Rutear un track a un canal MIDI.

        Args:
            track_id: ID del track
            midi_channel: Canal MIDI (0-15, -1 = all)
        """
        self._track_channels[track_id] = midi_channel
        if track_id not in self._active_tracks:
            self._active_tracks.append(track_id)

    def unroute_track(self, track_id: str) -> None:
        """Desconectar un track del MIDI."""
        self._track_channels.pop(track_id, None)
        if track_id in self._active_tracks:
            self._active_tracks.remove(track_id)

    def get_track_for_channel(
        self, channel: int
    ) -> Optional[str]:
        """Obtener track asociado a un canal MIDI."""
        for track_id, ch in self._track_channels.items():
            if ch == channel or ch == -1:
                return track_id
        return None

    # === Grabación ===

    def start_recording(
        self, bpm: int = 120
    ) -> bool:
        """Iniciar grabación MIDI.

        Args:
            bpm: BPM para cálculo de ticks

        Returns:
            True si se inició
        """
        if not HAS_MIDO:
            logger.warning("mido no disponible")
            return False

        if self._state == MIDIRecordingState.RECORDING:
            return True

        if not self._active_tracks:
            logger.warning(
                "No hay tracks activos para MIDI"
            )
            return False

        if not self._overdub:
            self._captured_events.clear()

        self.set_bpm(bpm)
        self._state = MIDIRecordingState.RECORDING
        self._start_time = time.time()
        self._current_tick = 0

        # Abrir puerto MIDI de entrada
        if self._input_device:
            try:
                self._input_port = mido.open_input(
                    self._input_device
                )
            except Exception as e:
                logger.error(
                    f"Error abriendo puerto MIDI: {e}"
                )
                self._input_port = None

        # Hilo de captura
        self._midi_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name="MIDIRecorder",
        )
        self._midi_thread.start()

        if self._on_state_changed:
            self._on_state_changed(self._state)

        logger.info("Grabación MIDI iniciada")
        return True

    def stop_recording(self) -> Dict[str, List[MIDICaptureEvent]]:
        """Detener grabación MIDI.

        Returns:
            Dict {track_id: [eventos]} de eventos capturados
        """
        if self._state != MIDIRecordingState.RECORDING:
            return {}

        self._state = MIDIRecordingState.STOPPED

        # Cerrar puerto
        if self._input_port:
            try:
                self._input_port.close()
            except Exception:
                pass
            self._input_port = None

        # Esperar hilo
        if self._midi_thread:
            self._midi_thread.join(timeout=2.0)
            self._midi_thread = None

        # Organizar eventos por track
        result: Dict[str, List[MIDICaptureEvent]] = {}
        for event in self._captured_events:
            tid = event.track_id
            if tid not in result:
                result[tid] = []
            result[tid].append(event)

        # Crear takes
        for track_id, events in result.items():
            if events:
                take = MIDITake(
                    take_number=len(
                        self._takes[track_id]
                    ) + 1,
                    events=events,
                    start_tick=events[0].tick,
                    end_tick=events[-1].tick,
                    duration_ticks=(
                        events[-1].tick - events[0].tick
                    ),
                    track_id=track_id,
                )
                self._takes[track_id].append(take)

        self._state = MIDIRecordingState.IDLE
        if self._on_state_changed:
            self._on_state_changed(self._state)

        logger.info(
            f"Grabación MIDI detenida: "
            f"{len(self._captured_events)} eventos"
        )

        return result

    def _capture_loop(self) -> None:
        """Bucle de captura MIDI."""
        while self._state == MIDIRecordingState.RECORDING:
            try:
                if self._input_port:
                    # Poll con timeout
                    msg = self._input_port.poll()
                    if msg is not None:
                        self._process_message(msg)
                else:
                    # Sin puerto: esperar
                    time.sleep(0.001)

                # Actualizar tick actual
                elapsed = (
                    time.time() - self._start_time
                )
                self._current_tick = int(
                    elapsed * self._tick_rate
                )

                # Loop recording
                if (
                    self._loop_record
                    and self._loop_end > 0
                    and self._current_tick >= self._loop_end
                ):
                    self._current_tick = self._loop_start

            except Exception as e:
                logger.error(
                    f"Error en captura MIDI: {e}"
                )
                time.sleep(0.01)

    def _process_message(
        self, msg: "mido.Message"
    ) -> None:
        """Procesar un mensaje MIDI recibido.

        Args:
            msg: Mensaje MIDI
        """
        tick = self._current_tick

        if self._quantize_on_record:
            tick = self._quantize_tick(tick)

        # Determinar track destino
        track_id = self.get_track_for_channel(
            msg.channel if hasattr(msg, "channel") else 0
        )

        if not track_id and self._active_tracks:
            track_id = self._active_tracks[0]

        if not track_id:
            return

        event = MIDICaptureEvent(
            message=msg,
            tick=tick,
            track_id=track_id,
        )

        with self._midi_lock:
            self._captured_events.append(event)

        if self._on_event_captured:
            self._on_event_captured(event)

    def _quantize_tick(self, tick: int) -> int:
        """Cuantizar un tick al grid.

        Args:
            tick: Tick original

        Returns:
            Tick cuantizado
        """
        if self._quantize_grid <= 0:
            return tick

        grid = self._quantize_grid
        return round(tick / grid) * grid

    # === Utilidades ===

    def get_captured_events(
        self, track_id: Optional[str] = None
    ) -> List[MIDICaptureEvent]:
        """Obtener eventos capturados.

        Args:
            track_id: Filtrar por track (None = todos)

        Returns:
            Lista de eventos
        """
        if track_id:
            return [
                e for e in self._captured_events
                if e.track_id == track_id
            ]
        return list(self._captured_events)

    def get_takes(
        self, track_id: str
    ) -> List[MIDITake]:
        """Obtener takes de un track."""
        return list(self._takes.get(track_id, []))

    def clear_captured(self) -> None:
        """Limpiar eventos capturados."""
        self._captured_events.clear()

    def clear_takes(self, track_id: Optional[str] = None) -> None:
        """Limpiar takes."""
        if track_id:
            self._takes.pop(track_id, None)
        else:
            self._takes.clear()

    def export_to_midi(
        self, file_path: Path, bpm: int = 120
    ) -> bool:
        """Exportar eventos capturados a archivo MIDI.

        Args:
            file_path: Ruta de salida
            bpm: BPM del proyecto

        Returns:
            True si se exportó
        """
        if not HAS_MIDO:
            return False

        try:
            mid = mido.MidiFile()
            track = mido.MidiTrack()
            mid.tracks.append(track)

            track.append(
                mido.MetaMessage(
                    "set_tempo",
                    tempo=mido.bpm2tempo(bpm),
                )
            )
            track.append(
                mido.MetaMessage("time_signature", numerator=4, denominator=4)
            )

            current_tick = 0
            for event in sorted(
                self._captured_events,
                key=lambda e: e.tick,
            ):
                delta = event.tick - current_tick
                msg = event.message.copy()
                msg.time = delta
                track.append(msg)
                current_tick = event.tick

            mid.save(str(file_path))
            logger.info(
                f"MIDI exportado: {file_path}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error exportando MIDI: {e}"
            )
            return False

    # === Cleanup ===

    def shutdown(self) -> None:
        """Apagar el MIDIRecorder."""
        self.stop_recording()
        self.clear_captured()
        self.clear_takes()
        logger.info("MIDIRecorder apagado")
