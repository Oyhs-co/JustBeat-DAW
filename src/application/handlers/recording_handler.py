"""Recording Handler - Gestión de grabación de audio.

Coordina la grabación de audio entre la UI, el Recorder,
y el sistema de transporte.
"""

from typing import Optional, Dict, List, Callable
from pathlib import Path
from dataclasses import dataclass, field
import logging
import time

from src.infrastructure.audio.recorder import (
    Recorder, RecordingState, TakeInfo, RecordingBuffer
)

logger = logging.getLogger(__name__)


@dataclass
class TrackArmState:
    """Estado de armado de un track."""
    track_id: str
    armed: bool = False
    input_channel: int = 0
    monitor_enabled: bool = False
    take_count: int = 0


class RecordingHandler:
    """Handler para operaciones de grabación de audio.

    Coordina el Recorder con el estado de la aplicación,
    maneja armado de tracks, count-in, punch in/out,
    y compilación de takes.

    Signals (vía callbacks):
        recording_started(track_ids)
        recording_stopped(track_id, file_path)
        recording_level(track_id, peak, rms)
        recording_clip(track_id)
        take_completed(track_id, take_info)
    """

    def __init__(
        self,
        recorder: Optional[Recorder] = None,
    ):
        """Inicializar RecordingHandler.

        Args:
            recorder: Recorder instance (se crea por defecto si None)
        """
        self._recorder = recorder or Recorder()
        self._track_arms: Dict[str, TrackArmState] = {}
        self._recording_dir: Path = Path("recordings")

        # Estado
        self._is_recording: bool = False
        self._punch_in_enabled: bool = False
        self._punch_out_enabled: bool = False
        self._count_in_beats: int = 0
        self._loop_record: bool = False

        # Callbacks
        self._on_recording_started: Optional[
            Callable[[List[str]], None]
        ] = None
        self._on_recording_stopped: Optional[
            Callable[[str, Path], None]
        ] = None
        self._on_recording_level: Optional[
            Callable[[str, float, float], None]
        ] = None
        self._on_recording_clip: Optional[
            Callable[[str], None]
        ] = None
        self._on_state_changed: Optional[
            Callable[[RecordingState], None]
        ] = None

        # Conectar callbacks del Recorder
        self._recorder.set_on_level(self._on_level_callback)
        self._recorder.set_on_clip(self._on_clip_callback)
        self._recorder.set_on_state_changed(
            self._on_recorder_state_changed
        )
        self._recorder.set_on_take_completed(
            self._on_take_completed_callback
        )

        self._recording_dir.mkdir(exist_ok=True)

        logger.info("RecordingHandler inicializado")

    # === Callbacks ===

    def set_on_recording_started(
        self, callback: Callable[[List[str]], None]
    ) -> None:
        self._on_recording_started = callback

    def set_on_recording_stopped(
        self, callback: Callable[[str, Path], None]
    ) -> None:
        self._on_recording_stopped = callback

    def set_on_recording_level(
        self, callback: Callable[[str, float, float], None]
    ) -> None:
        self._on_recording_level = callback

    def set_on_recording_clip(
        self, callback: Callable[[str], None]
    ) -> None:
        self._on_recording_clip = callback

    def set_on_state_changed(
        self, callback: Callable[[RecordingState], None]
    ) -> None:
        self._on_state_changed = callback

    # === Armado de Tracks ===

    def arm_track(
        self, track_id: str, input_channel: int = 0
    ) -> None:
        """Armar un track para grabación.

        Args:
            track_id: ID del track
            input_channel: Canal de entrada (0 = primer canal)
        """
        if track_id not in self._track_arms:
            self._track_arms[track_id] = TrackArmState(
                track_id=track_id
            )

        arm = self._track_arms[track_id]
        arm.armed = True
        arm.input_channel = input_channel

        self._recorder.arm_track(track_id)

        logger.info(
            f"Track armado: {track_id} "
            f"(canal {input_channel})"
        )

    def disarm_track(self, track_id: str) -> None:
        """Desarmar un track."""
        arm = self._track_arms.get(track_id)
        if arm:
            arm.armed = False
            self._recorder.disarm_track(track_id)
            logger.info(f"Track desarmado: {track_id}")

    def disarm_all(self) -> None:
        """Desarmar todos los tracks."""
        for track_id in list(self._track_arms.keys()):
            self.disarm_track(track_id)

    def toggle_arm(self, track_id: str) -> bool:
        """Alternar armado de un track.

        Returns:
            Nuevo estado de armado
        """
        arm = self._track_arms.get(track_id)
        if arm and arm.armed:
            self.disarm_track(track_id)
            return False
        else:
            self.arm_track(track_id)
            return True

    def is_armed(self, track_id: str) -> bool:
        """Verificar si un track está armado."""
        arm = self._track_arms.get(track_id)
        return arm is not None and arm.armed

    def get_armed_tracks(self) -> List[str]:
        """Obtener lista de tracks armados."""
        return [
            tid for tid, arm in self._track_arms.items()
            if arm.armed
        ]

    # === Control de Grabación ===

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start_recording(self, bpm: int = 120) -> bool:
        """Iniciar grabación.
        
        Args:
            bpm: BPM para count-in
        
        Returns:
            True si se inició
        """
        logger.info(f"Start recording requested, armed_tracks={self.get_armed_tracks()}, bpm={bpm}")
        armed_tracks = self.get_armed_tracks()
        if not armed_tracks:
            logger.warning(
                "No hay tracks armados para grabar"
            )
            return False

        self._recorder.set_count_in(self._count_in_beats)

        if self._punch_in_enabled:
            punch_sample = int(
                self._punch_in_sample
            )
            self._recorder.set_punch_in(punch_sample)

        if self._punch_out_enabled:
            punch_sample = int(
                self._punch_out_sample
            )
            self._recorder.set_punch_out(punch_sample)

        result = self._recorder.start_recording(bpm)

        if result:
            self._is_recording = True
            if self._on_recording_started:
                self._on_recording_started(armed_tracks)
            logger.info(
                f"Grabación iniciada: {len(armed_tracks)} "
                f"tracks"
            )

        return result

    def stop_recording(self) -> Dict[str, Path]:
        """Detener grabación.
        
        Returns:
            Dict {track_id: file_path} de archivos guardados
        """
        logger.info(f"Stop recording requested, is_recording={self._is_recording}")
        if not self._is_recording:
            return {}

        saved_files = self._recorder.stop_recording()
        self._is_recording = False

        for track_id, file_path in saved_files.items():
            if self._on_recording_stopped:
                self._on_recording_stopped(
                    track_id, file_path
                )
            arm = self._track_arms.get(track_id)
            if arm:
                arm.take_count += 1

        logger.info(
            f"Grabación detenida: "
            f"{len(saved_files)} archivos"
        )

        return saved_files

    # === Punch In/Out ===

    @property
    def punch_in_enabled(self) -> bool:
        return self._punch_in_enabled

    def set_punch_in(
        self, enabled: bool, sample: int = 0
    ) -> None:
        """Configurar punch-in.

        Args:
            enabled: Activar/desactivar
            sample: Posición en samples
        """
        self._punch_in_enabled = enabled
        if enabled:
            self._recorder.set_punch_in(sample)
        else:
            self._recorder.disable_punch()

    @property
    def punch_out_enabled(self) -> bool:
        return self._punch_out_enabled

    def set_punch_out(
        self, enabled: bool, sample: int = 0
    ) -> None:
        """Configurar punch-out."""
        self._punch_out_enabled = enabled
        if enabled:
            self._recorder.set_punch_out(sample)
        else:
            self._recorder.disable_punch()

    # === Count-in ===

    @property
    def count_in_beats(self) -> int:
        return self._count_in_beats

    def set_count_in(self, beats: int) -> None:
        """Establecer beats de count-in.

        Args:
            beats: Número de beats (0-8)
        """
        self._count_in_beats = max(0, min(8, beats))

    # === Loop Record ===

    @property
    def loop_record(self) -> bool:
        return self._loop_record

    def set_loop_record(self, enabled: bool) -> None:
        self._loop_record = enabled

    # === Niveles y Clipping ===

    def get_peak_level(self, track_id: str) -> float:
        """Obtener nivel pico de un track."""
        return self._recorder.get_peak_level(track_id)

    def get_rms_level(self, track_id: str) -> float:
        """Obtener nivel RMS de un track."""
        return self._recorder.get_rms_level(track_id)

    def has_clipped(self, track_id: str) -> bool:
        """Verificar si un track ha clipado."""
        return self._recorder.has_clipped(track_id)

    # === Takes ===

    def get_take_number(self, track_id: str) -> int:
        """Obtener número de take actual."""
        arm = self._track_arms.get(track_id)
        if arm:
            return arm.take_count + 1
        return 1

    def get_takes_dir(self) -> Path:
        """Obtener directorio de takes."""
        return Path(Recorder.TAKES_DIR)

    # === Callbacks internos ===

    def _on_level_callback(
        self, track_id: str, peak: float, rms: float
    ) -> None:
        if self._on_recording_level:
            self._on_recording_level(track_id, peak, rms)

    def _on_clip_callback(self, track_id: str) -> None:
        if self._on_recording_clip:
            self._on_recording_clip(track_id)

    def _on_recorder_state_changed(
        self, state: RecordingState
    ) -> None:
        if self._on_state_changed:
            self._on_state_changed(state)

    def _on_take_completed_callback(
        self, track_id: str, take_info: TakeInfo
    ) -> None:
        logger.info(
            f"Take completado: {track_id} -> "
            f"{take_info.file_path.name}"
        )

    # === Utilidades ===

    @property
    def state(self) -> RecordingState:
        """Obtener estado actual del Recorder."""
        return self._recorder.state

    @property
    def elapsed_seconds(self) -> float:
        """Tiempo transcurrido de grabación."""
        return self._recorder.elapsed_seconds

    # === Cleanup ===

    def shutdown(self) -> None:
        """Apagar el handler y el recorder."""
        self.stop_recording()
        self.disarm_all()
        self._recorder.shutdown()
        logger.info("RecordingHandler apagado")
