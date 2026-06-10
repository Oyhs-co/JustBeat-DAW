"""Audio Recorder - Grabación de audio a disco.

Captura audio desde dispositivos de entrada usando sounddevice,
escribe archivos WAV con múltiples formatos, y provee
medición de nivel con detección de clipping.
"""

from typing import Optional, Dict, List, Callable
from pathlib import Path
import threading
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


logger = logging.getLogger(__name__)


try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
    sd = None  # type: ignore[assignment]


class RecordingState(Enum):
    """Estado de la grabación."""
    IDLE = "idle"
    COUNT_IN = "count_in"
    RECORDING = "recording"
    STOPPED = "stopped"


@dataclass
class TakeInfo:
    """Información de una toma (take)."""
    take_number: int
    file_path: Path
    duration: float
    sample_rate: int
    channels: int
    bit_depth: int
    peak_level: float
    has_clipped: bool
    timestamp: float = 0.0


@dataclass
class RecordingBuffer:
    """Buffer circular para grabación."""
    data: np.ndarray = field(default_factory=lambda: np.zeros((0,), dtype=np.float32))
    sample_rate: int = 44100
    channels: int = 1
    peak: float = 0.0
    has_clipped: bool = False
    start_time: float = 0.0

    def append(self, samples: np.ndarray) -> None:
        if self.data.size == 0:
            self.data = samples.copy()
        else:
            self.data = np.concatenate([self.data, samples])

        current_peak = np.max(np.abs(samples))
        if current_peak > self.peak:
            self.peak = current_peak
        if current_peak >= 0.999:
            self.has_clipped = True

    def get_rms(self) -> float:
        if self.data.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(self.data ** 2)))

    def clear(self) -> None:
        self.data = np.zeros((0,), dtype=np.float32)
        self.peak = 0.0
        self.has_clipped = False
        self.start_time = 0.0


class Recorder:
    """Motor de grabación de audio.

    Captura audio desde dispositivos de entrada usando sounddevice,
    soporta múltiples canales, punch in/out, count-in, y auto-naming.

    Attributes:
        sample_rate: Sample rate de grabación
        bit_depth: Profundidad de bits (16, 24, 32)
        channels: Número de canales a grabar
        device_name: Nombre del dispositivo de entrada
    """

    TAKES_DIR = "takes"

    def __init__(
        self,
        sample_rate: int = 44100,
        bit_depth: int = 24,
        channels: int = 2,
        device_name: Optional[str] = None,
    ):
        """Inicializar el Recorder.

        Args:
            sample_rate: Sample rate
            bit_depth: Profundidad de bits (16, 24, 32)
            channels: Canales de entrada
            device_name: Dispositivo de entrada (None = default)
        """
        self._sample_rate = sample_rate
        self._bit_depth = bit_depth
        self._channels = channels
        self._device_name = device_name

        # Estado de grabación
        self._state = RecordingState.IDLE
        self._buffers: Dict[str, RecordingBuffer] = {}
        self._active_takes: Dict[str, int] = {}

        # Count-in
        self._count_in_beats: int = 0
        self._count_in_beat: int = 0
        self._count_in_thread: Optional[threading.Thread] = None

        # Punch in/out
        self._punch_in_enabled: bool = False
        self._punch_out_enabled: bool = False
        self._punch_in_sample: int = 0
        self._punch_out_sample: int = 0

        # Input stream
        self._input_stream: Optional[sd.InputStream] = None
        self._stream_lock = threading.Lock()

        # Input device
        self._input_device_index: Optional[int] = None
        self._auto_select_device()

        # Callbacks
        self._on_level: Optional[Callable[[str, float, float], None]] = None
        self._on_clip: Optional[Callable[[str], None]] = None
        self._on_state_changed: Optional[Callable[[RecordingState], None]] = None
        self._on_take_completed: Optional[Callable[[str, TakeInfo], None]] = None

        # Sample counter for timing
        self._sample_count: int = 0

        logger.info(
            f"Recorder inicializado: {sample_rate}Hz, "
            f"{bit_depth}bit, {channels} canales"
        )

    def _auto_select_device(self) -> None:
        """Auto-seleccionar dispositivo de entrada."""
        if not HAS_SOUNDDEVICE:
            return

        try:
            if self._device_name:
                devices = sd.query_devices()
                for i, dev in enumerate(devices):
                    if self._device_name.lower() in dev["name"].lower():
                        self._input_device_index = i
                        break
            else:
                default = sd.query_devices(kind="input")
                if default:
                    self._input_device_index = default["index"]
                    self._device_name = default["name"]
        except Exception as e:
            logger.warning(f"Error seleccionando dispositivo: {e}")

    # === Callbacks ===

    def set_on_level(
        self, callback: Callable[[str, float, float], None]
    ) -> None:
        """Callback cuando cambia el nivel: (track_id, peak, rms)."""
        self._on_level = callback

    def set_on_clip(self, callback: Callable[[str], None]) -> None:
        """Callback cuando hay clipping."""
        self._on_clip = callback

    def set_on_state_changed(
        self, callback: Callable[[RecordingState], None]
    ) -> None:
        self._on_state_changed = callback

    def set_on_take_completed(
        self, callback: Callable[[str, TakeInfo], None]
    ) -> None:
        self._on_take_completed = callback

    # === Configuración ===

    @property
    def state(self) -> RecordingState:
        return self._state

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, value: int) -> None:
        self._sample_rate = value

    @property
    def bit_depth(self) -> int:
        return self._bit_depth

    @bit_depth.setter
    def bit_depth(self, value: int) -> None:
        if value in (16, 24, 32):
            self._bit_depth = value

    @property
    def channels(self) -> int:
        return self._channels

    @channels.setter
    def channels(self, value: int) -> None:
        self._channels = max(1, min(8, value))

    def set_count_in(self, beats: int) -> None:
        """Establecer número de beats de count-in."""
        self._count_in_beats = max(0, min(8, beats))

    def set_punch_in(self, sample: int) -> None:
        """Establecer punto de punch-in en samples."""
        self._punch_in_sample = max(0, sample)
        self._punch_in_enabled = True

    def set_punch_out(self, sample: int) -> None:
        """Establecer punto de punch-out en samples."""
        self._punch_out_sample = max(0, sample)
        self._punch_out_enabled = True

    def disable_punch(self) -> None:
        """Deshabilitar punch in/out."""
        self._punch_in_enabled = False
        self._punch_out_enabled = False

    # === Grabación ===

    def arm_track(self, track_id: str) -> None:
        """Armar un track para grabación.

        Args:
            track_id: ID del track
        """
        if track_id not in self._buffers:
            self._buffers[track_id] = RecordingBuffer(
                sample_rate=self._sample_rate,
                channels=self._channels,
            )
            self._active_takes[track_id] = 0

        logger.info(f"Track armado para grabación: {track_id}")

    def disarm_track(self, track_id: str) -> None:
        """Desarmar un track."""
        self._buffers.pop(track_id, None)
        self._active_takes.pop(track_id, None)

    def disarm_all(self) -> None:
        """Desarmar todos los tracks."""
        self._buffers.clear()
        self._active_takes.clear()

    def get_armed_tracks(self) -> List[str]:
        """Obtener lista de tracks armados."""
        return list(self._buffers.keys())

    def start_recording(
        self, bpm: int = 120
    ) -> bool:
        """Iniciar grabación.

        Si count-in está activo, primero ejecuta el count-in
        y luego comienza la grabación.

        Args:
            bpm: BPM para count-in

        Returns:
            True si se inició
        """
        if not HAS_SOUNDDEVICE:
            logger.warning("sounddevice no disponible")
            return False

        if self._state == RecordingState.RECORDING:
            return True

        if not self._buffers:
            logger.warning("No hay tracks armados")
            return False

        # Limpiar buffers
        for buf in self._buffers.values():
            buf.clear()

        self._sample_count = 0

        # Count-in
        if self._count_in_beats > 0:
            self._state = RecordingState.COUNT_IN
            self._count_in_beat = 0
            logger.info(
                f"Count-in: {self._count_in_beats} beats"
            )
            if self._on_state_changed:
                self._on_state_changed(self._state)

            # Ejecutar count-in (bloqueante, thread separado)
            self._count_in_thread = threading.Thread(
                target=self._run_count_in,
                args=(bpm,),
                daemon=True,
            )
            self._count_in_thread.start()
            return True

        # Iniciar grabación directamente
        return self._begin_capture()

    def _run_count_in(self, bpm: int) -> None:
        """Ejecutar count-in y luego iniciar grabación."""
        beat_duration = 60.0 / bpm

        for i in range(self._count_in_beats):
            if self._state != RecordingState.COUNT_IN:
                return
            self._count_in_beat = i + 1
            time.sleep(beat_duration)

        # Iniciar grabación después del count-in
        if self._state == RecordingState.COUNT_IN:
            self._begin_capture()

    def _begin_capture(self) -> bool:
        """Iniciar captura de audio.

        Returns:
            True si se inició correctamente
        """
        try:
            self._state = RecordingState.RECORDING

            if self._on_state_changed:
                self._on_state_changed(self._state)

            kwargs = {
                "samplerate": self._sample_rate,
                "channels": self._channels,
                "dtype": "float32",
                "blocksize": 256,
            }

            if self._input_device_index is not None:
                kwargs["device"] = self._input_device_index

            def input_callback(
                indata, frames, time_info, status
            ):
                if status:
                    logger.debug(
                        f"Status grabación: {status}"
                    )

                if self._state != RecordingState.RECORDING:
                    return

                with self._stream_lock:
                    if self._channels == 1:
                        # Mono: un solo buffer
                        for buf in self._buffers.values():
                            buf.append(indata[:, 0])
                    else:
                        # Multi-canal: distribuir por track
                        for i, track_id in enumerate(
                            self._buffers.keys()
                        ):
                            if i < indata.shape[1]:
                                channel_data = indata[:, i]
                                self._buffers[
                                    track_id
                                ].append(channel_data)

                    self._sample_count += frames

                    # Punch in/out
                    if self._punch_in_enabled:
                        if (
                            self._sample_count
                            < self._punch_in_sample
                        ):
                            return

                    if self._punch_out_enabled:
                        if (
                            self._sample_count
                            >= self._punch_out_sample
                        ):
                            self._stop_capture()
                            return

                    # Reportar niveles
                    for track_id, buf in self._buffers.items():
                        peak = buf.peak
                        rms = buf.get_rms()
                        if self._on_level:
                            self._on_level(
                                track_id, peak, rms
                            )
                        if buf.has_clipped and self._on_clip:
                            self._on_clip(track_id)
                            buf.has_clipped = False

            self._input_stream = sd.InputStream(**kwargs)
            self._input_stream.start()

            logger.info(
                f"Grabación iniciada: {self._sample_rate}Hz, "
                f"{self._channels} canales"
            )
            return True

        except Exception as e:
            logger.error(f"Error iniciando grabación: {e}")
            self._state = RecordingState.IDLE
            if self._on_state_changed:
                self._on_state_changed(self._state)
            return False

    def stop_recording(self) -> Dict[str, Path]:
        """Detener grabación y guardar archivos.

        Returns:
            Dict {track_id: file_path} de archivos guardados
        """
        if self._state not in (
            RecordingState.RECORDING, RecordingState.COUNT_IN
        ):
            return {}

        self._state = RecordingState.STOPPED

        # Detener captura
        saved_files = self._stop_capture()

        self._state = RecordingState.IDLE
        if self._on_state_changed:
            self._on_state_changed(self._state)

        return saved_files

    def _stop_capture(self) -> Dict[str, Path]:
        """Detener captura y guardar archivos WAV."""
        saved_files: Dict[str, Path] = {}

        # Detener stream
        if self._input_stream:
            try:
                self._input_stream.stop()
                self._input_stream.close()
            except Exception as e:
                logger.warning(
                    f"Error cerrando stream: {e}"
                )
            self._input_stream = None

        waves_dir = Path(self.TAKES_DIR)
        waves_dir.mkdir(exist_ok=True)

        # Guardar cada buffer a WAV
        for track_id, buf in self._buffers.items():
            if buf.data.size == 0:
                logger.warning(
                    f"Buffer vacío para {track_id}"
                )
                continue

            take_num = self._active_takes.get(track_id, 0) + 1
            self._active_takes[track_id] = take_num

            file_name = (
                f"{track_id}_Take_{take_num:03d}.wav"
            )
            file_path = waves_dir / file_name

            duration = buf.data.size / self._sample_rate

            try:
                self._write_wav(
                    buf.data, file_path, self._sample_rate,
                    self._bit_depth
                )

                take_info = TakeInfo(
                    take_number=take_num,
                    file_path=file_path,
                    duration=duration,
                    sample_rate=self._sample_rate,
                    channels=buf.channels,
                    bit_depth=self._bit_depth,
                    peak_level=buf.peak,
                    has_clipped=buf.has_clipped,
                    timestamp=time.time(),
                )

                saved_files[track_id] = file_path

                if self._on_take_completed:
                    self._on_take_completed(
                        track_id, take_info
                    )

                logger.info(
                    f"Take guardado: {file_name} "
                    f"({duration:.1f}s, "
                    f"peak={buf.peak:.2f})"
                )

            except Exception as e:
                logger.error(
                    f"Error guardando {file_name}: {e}"
                )

        return saved_files

    @staticmethod
    def _write_wav(
        audio_data: np.ndarray,
        file_path: Path,
        sample_rate: int,
        bit_depth: int,
    ) -> None:
        """Escribir datos de audio a archivo WAV.

        Args:
            audio_data: Audio mono como float32
            file_path: Ruta de salida
            sample_rate: Sample rate
            bit_depth: Profundidad de bits
        """
        import wave

        # Normalizar y convertir
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = audio_data / max_val * 0.95

        if bit_depth == 16:
            audio_int = (audio_data * 32767.0).astype(np.int16)
            sampwidth = 2
        elif bit_depth == 24:
            audio_int = (audio_data * 8388607.0).astype(np.int32)
            sampwidth = 3
        elif bit_depth == 32:
            audio_int = (audio_data * 2147483647.0).astype(np.int32)
            sampwidth = 4
        else:
            audio_int = (audio_data * 32767.0).astype(np.int16)
            sampwidth = 2

        with wave.open(str(file_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(sampwidth)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int.tobytes())

    # === Utilidades ===

    def get_peak_level(self, track_id: str) -> float:
        """Obtener nivel pico de un track."""
        buf = self._buffers.get(track_id)
        if buf:
            return buf.peak
        return 0.0

    def get_rms_level(self, track_id: str) -> float:
        """Obtener nivel RMS de un track."""
        buf = self._buffers.get(track_id)
        if buf:
            return buf.get_rms()
        return 0.0

    def has_clipped(self, track_id: str) -> bool:
        """Verificar si un track ha clipado."""
        buf = self._buffers.get(track_id)
        if buf:
            return buf.has_clipped
        return False

    def get_take_number(self, track_id: str) -> int:
        """Obtener número de take actual para un track."""
        return self._active_takes.get(track_id, 0) + 1

    @property
    def elapsed_samples(self) -> int:
        return self._sample_count

    @property
    def elapsed_seconds(self) -> float:
        return self._sample_count / self._sample_rate

    # === Cleanup ===

    def shutdown(self) -> None:
        """Apagar el Recorder."""
        self.stop_recording()
        self.disarm_all()
        logger.info("Recorder apagado")
