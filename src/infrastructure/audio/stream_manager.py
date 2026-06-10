import time
import logging
from typing import Optional, Callable
import numpy as np

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
    sd = None  # type: ignore[assignment]
    logger.warning("sounddevice no disponible, stream de audio desactivado")


class StreamManager:
    UNDERRUN_THRESHOLD_MS = 30.0

    def __init__(self) -> None:
        self._stream: Optional[sd.OutputStream] = None
        self._user_callback: Optional[Callable] = None
        self._sample_rate: int = 44100
        self._buffer_size: int = 512
        self._device_index: Optional[int] = None

        self._last_callback_time: float = 0.0
        self._underrun_count: int = 0
        self._recovery_attempts: int = 0
        self._max_recovery_attempts: int = 5
        self._peak_callback_time: float = 0.0
        self._total_underruns: int = 0
        self._callback_count: int = 0
        self._next_audio_log_callback: int = 0
        self._startup_grace_callbacks: int = 1

    @property
    def is_active(self) -> bool:
        return self._stream is not None

    @property
    def underrun_count(self) -> int:
        return self._total_underruns

    @property
    def peak_callback_time(self) -> float:
        return self._peak_callback_time

    def start(
        self,
        sample_rate: int,
        buffer_size: int,
        device_index: Optional[int],
        callback: Callable,
    ) -> bool:
        if not HAS_SOUNDDEVICE:
            logger.warning("sounddevice no disponible, sin audio en tiempo real")
            return False

        if self._stream is not None:
            return True

        self._sample_rate = sample_rate
        self._buffer_size = buffer_size
        self._device_index = device_index
        self._user_callback = callback

        self._last_callback_time = time.perf_counter()
        self._underrun_count = 0
        self._callback_count = 0
        self._next_audio_log_callback = 0
        self._startup_grace_callbacks = 1

        logger.debug(
            f"[AUDIO] start_stream() called at T={time.perf_counter():.3f}s"
        )

        def _wrapped_callback(outdata, frames, time_info, status) -> None:
            now = time.perf_counter()
            self._callback_count += 1
            elapsed_ms = (now - self._last_callback_time) * 1000.0
            expected_ms = (frames / self._sample_rate) * 1000.0

            if self._callback_count >= self._next_audio_log_callback:
                logger.debug(
                    f"[AUDIO] Callback #{self._callback_count}: "
                    f"elapsed={elapsed_ms:.1f}ms (expected={expected_ms:.1f}ms) "
                    f"underruns={self._underrun_count}"
                )
                self._next_audio_log_callback = self._callback_count + 43

            if (
                self._last_callback_time > 0
                and self._callback_count > self._startup_grace_callbacks
                and elapsed_ms > expected_ms + self.UNDERRUN_THRESHOLD_MS
            ):
                self._underrun_count += 1
                self._total_underruns += 1

                logger.debug(
                    f"[AUDIO] Underrun #{self._underrun_count}: "
                    f"{elapsed_ms:.1f}ms "
                    f"(threshold={expected_ms + self.UNDERRUN_THRESHOLD_MS:.1f}ms) "
                    f"callback_count={self._callback_count}"
                )

                if self._underrun_count >= self._max_recovery_attempts:
                    logger.warning(
                        f"Buffer underrun detectado ({elapsed_ms:.1f}ms, "
                        f"esperado {expected_ms:.1f}ms) - intentando recovery..."
                    )
                    logger.debug(
                        f"[AUDIO] Underrun recovery triggered at "
                        f"T={now:.3f}s, callback #{self._callback_count}"
                    )
                    self.recover()
                    self._underrun_count = 0

            self._last_callback_time = now

            if self._user_callback:
                self._user_callback(outdata, frames, time_info, status)

            cb_time = (time.perf_counter() - now) * 1000.0
            if cb_time > self._peak_callback_time:
                self._peak_callback_time = cb_time

        try:
            kwargs = {
                "samplerate": self._sample_rate,
                "blocksize": self._buffer_size,
                "channels": 2,
                "dtype": "float32",
                "callback": _wrapped_callback,
            }

            if self._device_index is not None:
                kwargs["device"] = self._device_index

            self._stream = sd.OutputStream(**kwargs)
            self._stream.start()

            logger.info(
                f"Audio stream iniciado: {self._sample_rate}Hz, "
                f"buffer {self._buffer_size}"
                + (f", device: index={self._device_index}" if self._device_index is not None else "")
            )
            return True

        except Exception as e:
            logger.error(f"Error iniciando audio stream: {e}")
            try:
                self._stream = sd.OutputStream(
                    samplerate=self._sample_rate,
                    blocksize=self._buffer_size,
                    channels=2,
                    dtype="float32",
                    callback=_wrapped_callback,
                )
                self._stream.start()
                logger.info("Audio stream iniciado (fallback device)")
                return True
            except Exception as e2:
                logger.error(f"Error en fallback de audio stream: {e2}")
                self._stream = None
                return False

    def stop(self) -> None:
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Error deteniendo audio stream: {e}")
            self._stream = None
            logger.info("Audio stream detenido")

    def recover(self) -> bool:
        if self._recovery_attempts >= self._max_recovery_attempts:
            logger.error("Máximo de intentos de recovery alcanzado")
            return False

        self._recovery_attempts += 1
        logger.info(f"Recovery de stream (intento {self._recovery_attempts})...")

        self.stop()
        time.sleep(0.05)

        success = self.start(
            self._sample_rate,
            self._buffer_size,
            self._device_index,
            self._user_callback,
        )

        if success:
            self._recovery_attempts = 0

        return success

    def get_stats(self) -> dict:
        return {
            "underruns": self._total_underruns,
            "peak_callback_time_ms": round(self._peak_callback_time, 2),
        }

    def reset_stats(self) -> None:
        self._total_underruns = 0
        self._peak_callback_time = 0.0
        self._recovery_attempts = 0
