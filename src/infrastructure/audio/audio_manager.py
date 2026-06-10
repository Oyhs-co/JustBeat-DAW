"""Audio Manager - Gestor de audio en tiempo real mejorado.

Maneja el step sequencer, registro de tracks, metronomo,
y orquesta DeviceManager + StreamManager.
"""

from typing import Optional, Dict, List, Callable
import threading
import time
import logging
import numpy as np

from src.infrastructure.audio.polyphonic_synth import PolyphonicSynth
from src.infrastructure.audio.audio_router import AudioRouter
from src.infrastructure.audio.device_manager import DeviceManager
from src.infrastructure.audio.stream_manager import StreamManager

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
    sd = None  # type: ignore[assignment]
    logger.warning("sounddevice no disponible, audio playback desactivado")


_global_synth: Optional[PolyphonicSynth] = None


def _get_global_synth(sample_rate: int = 44100) -> PolyphonicSynth:
    global _global_synth
    if _global_synth is None:
        _global_synth = PolyphonicSynth(
            sample_rate=sample_rate, max_voices=16
        )
    return _global_synth


class AudioManager:
    """Gestor de audio en tiempo real mejorado.

    Responsabilidades:
    - Orquestacion de DeviceManager y StreamManager
    - Step sequencer loop (timer preciso basado en perf_counter)
    - Registro de tracks y sus estados de step
    - Metronome, count-in, loop
    - Sintetizador global (PolyphonicSynth)
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        buffer_size: int = 512,
        audio_router: Optional[AudioRouter] = None,
    ):
        self._sample_rate = sample_rate
        self._buffer_size = buffer_size

        self._audio_router = audio_router

        self._synth = _get_global_synth(sample_rate)
        if self._audio_router:
            self._audio_router.set_global_synth(self._synth)

        self._device_manager = DeviceManager()
        self._stream_manager = StreamManager()
        self._device_manager.set_on_device_changed(self._on_device_changed)

        self._step_states: Dict[int, List[bool]] = {}
        self._num_steps: int = 16
        self._current_step: int = 0
        self._step_running: bool = False
        self._step_thread: Optional[threading.Thread] = None
        self._step_stop_event: threading.Event = threading.Event()

        self._track_synths: Dict[str, dict] = {}

        self._is_playing: bool = False
        self._metronome_enabled: bool = False
        self._count_in_enabled: bool = False
        self._loop_enabled: bool = False
        self._metronome_sample_count: int = 0
        self._bpm: int = 120
        self._project_sample_rate: int = sample_rate
        self._position_in_ticks: int = 0

        self._on_tick_callback: Optional[Callable[[int], None]] = None
        self._on_step_callback: Optional[Callable[[int], None]] = None
        self._on_state_change: Optional[Callable[[bool], None]] = None

        self._audio_lock = threading.Lock()

        logger.info(
            f"AudioManager: {sample_rate}Hz, "
            f"buffer {buffer_size}"
        )

    def _on_device_changed(self) -> None:
        if self._stream_manager.is_active:
            self.stop_stream()
            self.start_stream()

    # === Device delegation ===

    def get_available_devices(self) -> List:
        return self._device_manager.get_available_devices()

    def set_device(self, device_name: str, is_asio: bool = False) -> bool:
        return self._device_manager.set_device(device_name, is_asio)

    @property
    def output_latency(self) -> float:
        return self._device_manager.output_latency

    @property
    def input_latency(self) -> float:
        return self._device_manager.input_latency

    @property
    def total_latency(self) -> float:
        return self._device_manager.total_latency

    # === Project sample rate ===

    def set_project_sample_rate(self, sample_rate: int) -> bool:
        if sample_rate not in (22050, 44100, 48000, 88200, 96000):
            logger.warning(
                f"Sample rate no soportado: {sample_rate}"
            )
            return False

        self._project_sample_rate = sample_rate

        if sample_rate != self._sample_rate:
            logger.info(
                f"Sample rate de proyecto: {sample_rate} "
                f"(device: {self._sample_rate})"
            )

        return True

    # === Callbacks ===

    def set_on_tick(
        self, callback: Callable[[int], None]
    ) -> None:
        self._on_tick_callback = callback

    def set_on_step(
        self, callback: Callable[[int], None]
    ) -> None:
        self._on_step_callback = callback

    def set_on_state_change(
        self, callback: Callable[[bool], None]
    ) -> None:
        self._on_state_change = callback

    # === Stream ===

    def start_stream(self) -> None:
        self._stream_manager.start(
            sample_rate=self._sample_rate,
            buffer_size=self._buffer_size,
            device_index=self._device_manager.device_index,
            callback=self._audio_callback,
        )

    def stop_stream(self) -> None:
        self._stream_manager.stop()

    # === Audio Callback ===

    def _audio_callback(self, outdata, frames, time_info, status) -> None:
        if status:
            logger.debug(f"Audio status: {status}")

        try:
            if self._audio_router:
                audio = self._audio_router.process_buffer(frames)
                if audio.shape[1] >= 4:
                    stereo = np.column_stack(
                        [audio[:, 0], audio[:, 1]]
                    )
                elif audio.shape[1] == 2:
                    stereo = audio
                else:
                    stereo = np.column_stack(
                        [audio, audio]
                    )
            else:
                audio = self._synth.process(frames)
                audio = np.tanh(audio * 0.8)
                stereo = np.column_stack([audio, audio])

            if self._metronome_enabled:
                self._add_metronome_click(stereo, frames)

            outdata[:] = stereo.astype(np.float32)

        except Exception as e:
            logger.error(
                f"Error en audio_callback: {e}"
            )
            outdata[:] = 0

    # === Step Sequencer ===

    def start_sequencer(self) -> None:
        if self._step_running:
            return

        self._step_running = True
        self._is_playing = True
        self._step_stop_event.clear()

        self._step_thread = threading.Thread(
            target=self._step_loop_precise,
            daemon=True,
            name="StepSequencer",
        )
        self._step_thread.start()

        if self._on_state_change:
            self._on_state_change(True)

        logger.info("Step sequencer iniciado (timer preciso)")

    def stop_sequencer(self) -> None:
        self._step_running = False
        self._is_playing = False
        self._step_stop_event.set()
        self._current_step = 0
        self._synth.all_notes_off()

        if self._on_state_change:
            self._on_state_change(False)

    def pause_sequencer(self) -> None:
        self._step_running = False
        self._is_playing = False
        self._step_stop_event.set()

        if self._on_state_change:
            self._on_state_change(False)

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def current_step(self) -> int:
        return self._current_step

    # === IAudioService Protocol (Transport compatibility) ===

    def play(self) -> None:
        self.start_sequencer()

    def pause(self) -> None:
        self.pause_sequencer()

    def stop(self) -> None:
        self.stop_sequencer()

    def seek(self, position: int) -> None:
        self._position_in_ticks = max(0, position)
        self._current_step = (
            self._position_in_ticks // 480
        ) % self._num_steps

    def get_position(self) -> int:
        return self._current_step * 480

    def _ticks_to_samples(self, ticks: int) -> int:
        beats = ticks / 480
        seconds_per_beat = 60.0 / self._bpm
        return int(
            beats * seconds_per_beat * self._sample_rate
        )

    def _samples_to_ticks(self, samples: int) -> int:
        seconds = samples / self._sample_rate
        seconds_per_beat = 60.0 / self._bpm
        beats = seconds / seconds_per_beat
        return int(beats * 480)

    def _step_loop_precise(self) -> None:
        bpm = self._bpm
        step_duration = 60.0 / bpm / 4.0

        next_time = time.perf_counter()

        while (
            self._step_running
            and not self._step_stop_event.is_set()
        ):
            try:
                next_time += step_duration
                now = time.perf_counter()

                if now > next_time:
                    missed = int(
                        (now - next_time) / step_duration
                    ) + 1
                    self._current_step = (
                        self._current_step + missed
                    ) % self._num_steps
                    next_time = now + step_duration

                with self._audio_lock:
                    for (
                        track_idx,
                        steps,
                    ) in self._step_states.items():
                        if self._current_step < len(
                            steps
                        ) and steps[self._current_step]:
                            self._trigger_step_note(
                                track_idx
                            )

                if self._on_step_callback:
                    self._on_step_callback(
                        self._current_step
                    )

                self._current_step = (
                    self._current_step + 1
                ) % self._num_steps

                if self._on_tick_callback:
                    self._on_tick_callback(
                        self._current_step * 480
                    )

                wait = (
                    next_time - time.perf_counter()
                )
                if wait > 0:
                    self._step_stop_event.wait(wait)
                else:
                    time.sleep(0)

            except Exception as e:
                logger.error(
                    f"Error en step_loop_precise: {e}",
                    exc_info=True,
                )
                time.sleep(0.01)

    def _trigger_step_note(self, track_idx: int) -> None:
        track_id = f"track_{track_idx}"
        track_data = self._track_synths.get(track_id, {})
        note = track_data.get("note", 60)
        volume = track_data.get("volume", 0.8)
        muted = track_data.get("muted", False)

        if not muted and HAS_SOUNDDEVICE:
            if self._audio_router:
                self._audio_router.note_on(
                    track_id, note, int(100 * volume)
                )
            else:
                self._synth.note_on(
                    note, int(100 * volume)
                )

            step_duration = 60.0 / 120 / 4.0
            n = note
            tid = track_id

            def note_off_later():
                time.sleep(step_duration * 0.7)
                if self._audio_router:
                    self._audio_router.note_off(tid, n)
                else:
                    self._synth.note_off(n)

            threading.Thread(
                target=note_off_later, daemon=True
            ).start()

    # === Track Management ===

    def register_track(
        self,
        track_id: str,
        note: int = 60,
        volume: float = 0.8,
        muted: bool = False,
        waveform: str = "square",
        pan: float = 0.0,
    ) -> None:
        logger.info(
            f"Register track: id={track_id}, note={note}, "
            f"volume={volume}, muted={muted}, waveform={waveform}"
        )
        with self._audio_lock:
            self._track_synths[track_id] = {
                "note": note,
                "volume": volume,
                "muted": muted,
                "waveform": waveform,
                "pan": pan,
            }

        if self._audio_router:
            self._audio_router.create_track_channel(
                track_id=track_id,
                waveform=waveform,
                note=note,
                volume=volume,
            )

    def unregister_track(self, track_id: str) -> None:
        logger.info(f"Unregister track: id={track_id}")
        with self._audio_lock:
            self._track_synths.pop(track_id, None)

        if self._audio_router:
            self._audio_router.remove_track_channel(
                track_id
            )

    def set_track_volume(
        self, track_id: str, volume: float
    ) -> None:
        with self._audio_lock:
            if track_id not in self._track_synths:
                self._track_synths[track_id] = {}
            self._track_synths[track_id]["volume"] = max(
                0.0, min(1.0, volume)
            )

        if self._audio_router:
            self._audio_router.set_track_volume(
                track_id, volume
            )

    def set_track_mute(
        self, track_id: str, muted: bool
    ) -> None:
        with self._audio_lock:
            if track_id not in self._track_synths:
                self._track_synths[track_id] = {}
            self._track_synths[track_id]["muted"] = muted

        if self._audio_router:
            self._audio_router.set_track_mute(
                track_id, muted
            )

    def set_track_pan(
        self, track_id: str, pan: float
    ) -> None:
        with self._audio_lock:
            if track_id not in self._track_synths:
                self._track_synths[track_id] = {}
            self._track_synths[track_id]["pan"] = max(
                -1.0, min(1.0, pan)
            )

        if self._audio_router:
            self._audio_router.set_track_pan(
                track_id, pan
            )

    def set_track_note(
        self, track_id: str, note: int
    ) -> None:
        with self._audio_lock:
            if track_id not in self._track_synths:
                self._track_synths[track_id] = {}
            self._track_synths[track_id]["note"] = note

    def get_track_synth(self, track_id: str) -> dict:
        return self._track_synths.get(track_id, {})

    def get_all_track_synths(self) -> Dict[str, dict]:
        return dict(self._track_synths)

    # === Step States ===

    def set_num_steps(self, num_steps: int) -> None:
        self._num_steps = max(1, num_steps)
        with self._audio_lock:
            for track_idx in list(
                self._step_states.keys()
            ):
                current = self._step_states[track_idx]
                if len(current) < self._num_steps:
                    self._step_states[track_idx] = (
                        current
                        + [False]
                        * (
                            self._num_steps
                            - len(current)
                        )
                    )
                else:
                    self._step_states[track_idx] = (
                        current[: self._num_steps]
                    )
        logger.info(f"Pattern length set to {num_steps}")

    def set_step_active(
        self,
        track_index: int,
        step: int,
        active: bool,
    ) -> None:
        with self._audio_lock:
            if (
                track_index
                not in self._step_states
            ):
                self._step_states[track_index] = (
                    [False] * self._num_steps
                )
            if 0 <= step < len(
                self._step_states[track_index]
            ):
                self._step_states[track_index][
                    step
                ] = active

    def get_step_states(
        self,
    ) -> Dict[int, List[bool]]:
        return dict(self._step_states)

    def init_track_steps(
        self, track_index: int
    ) -> None:
        if track_index not in self._step_states:
            self._step_states[track_index] = (
                [False] * self._num_steps
            )

    # === Notas en tiempo real ===

    def note_on(
        self, note: int, velocity: int = 100
    ) -> None:
        if HAS_SOUNDDEVICE:
            try:
                self._synth.note_on(note, velocity)
                duration = 0.5
                samples = int(
                    self._sample_rate * duration
                )
                audio_data = self._synth.process(
                    samples
                )
                sd.play(
                    audio_data,
                    self._sample_rate,
                    blocking=False,
                )
            except Exception as e:
                logger.warning(
                    f"Error tocando nota: {e}"
                )

    def note_off(self, note: int) -> None:
        if HAS_SOUNDDEVICE:
            try:
                self._synth.note_off(note)
            except Exception as e:
                logger.warning(
                    f"Error deteniendo nota: {e}"
                )

    def all_notes_off(self) -> None:
        if HAS_SOUNDDEVICE:
            try:
                self._synth.all_notes_off()
            except Exception:
                pass

    # === Metronome, Loop, Count-in ===

    @property
    def metronome_enabled(self) -> bool:
        return self._metronome_enabled

    def toggle_metronome(self) -> bool:
        self._metronome_enabled = (
            not self._metronome_enabled
        )
        self._metronome_sample_count = 0
        logger.info(
            f"Metronome: {self._metronome_enabled}"
        )
        return self._metronome_enabled

    def _add_metronome_click(
        self, stereo: np.ndarray, frames: int
    ) -> None:
        samples_per_beat = int(
            self._sample_rate * 60.0 / self._bpm
        )
        if samples_per_beat <= 0:
            return

        for i in range(frames):
            beat_position = (
                self._metronome_sample_count
                % samples_per_beat
            )
            if beat_position < 100:
                click = np.sin(
                    2
                    * np.pi
                    * (
                        1000
                        if beat_position < 50
                        else 800
                    )
                    * beat_position
                    / self._sample_rate
                )
                click *= 0.3 * (
                    1 - beat_position / 100
                )
                stereo[i, 0] += click
                stereo[i, 1] += click
            self._metronome_sample_count += 1

    def set_bpm(self, bpm: int) -> None:
        self._bpm = max(20, min(300, bpm))

    @property
    def bpm(self) -> int:
        return self._bpm

    @property
    def loop_enabled(self) -> bool:
        return self._loop_enabled

    def toggle_loop(self) -> bool:
        self._loop_enabled = not self._loop_enabled
        logger.info(f"Loop: {self._loop_enabled}")
        return self._loop_enabled

    @property
    def count_in_enabled(self) -> bool:
        return self._count_in_enabled

    def toggle_count_in(self) -> bool:
        self._count_in_enabled = (
            not self._count_in_enabled
        )
        logger.info(
            f"Count-in: {self._count_in_enabled}"
        )
        return self._count_in_enabled

    # === Audio Levels ===

    def get_audio_levels(self) -> tuple:
        try:
            router = self._audio_router
            if router is not None:
                buf = router.get_last_buffer()
                if buf.size == 0:
                    return (0.0, 0.0)
                rms = np.sqrt(
                    np.mean(buf**2, axis=0)
                )
                left = float(
                    min(1.0, rms[0] * 3.0)
                )
                right = float(
                    min(1.0, rms[1] * 3.0)
                )
                return (left, right)
        except Exception:
            pass
        return (0.0, 0.0)

    def get_waveform_data(
        self, num_samples: int = 256
    ) -> tuple:
        try:
            if self._audio_router:
                buf = (
                    self._audio_router.get_last_buffer()
                )
                if buf.size == 0:
                    return (
                        [0.0] * num_samples,
                        [0.0] * num_samples,
                    )
                step = max(
                    1, buf.shape[0] // num_samples
                )
                left = buf[::step, 0].tolist()[
                    :num_samples
                ]
                right = buf[::step, 1].tolist()[
                    :num_samples
                ]
                return (left, right)
        except Exception:
            pass
        return (
            [0.0] * num_samples,
            [0.0] * num_samples,
        )

    # === Performance Stats ===

    def get_performance_stats(self) -> dict:
        stream_stats = (
            self._stream_manager.get_stats()
        )
        return {
            **stream_stats,
            "active_voices": (
                self._synth.get_active_voices()
            ),
            "output_latency_ms": round(
                self._device_manager.output_latency,
                2,
            ),
            "input_latency_ms": round(
                self._device_manager.input_latency, 2
            ),
            "sample_rate": self._sample_rate,
            "buffer_size": self._buffer_size,
            "device": (
                self._device_manager.device_name
                or "default"
            ),
            "bpm": self._bpm,
        }

    def reset_performance_stats(self) -> None:
        self._stream_manager.reset_stats()

    # === Cleanup ===

    def shutdown(self) -> None:
        self.stop_sequencer()
        self.stop_stream()
        self.all_notes_off()
        logger.info("AudioManager apagado")
