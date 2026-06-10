"""Sampler - Sample-based instrument.

Loads audio files (WAV) and plays them back with pitch shifting,
looping, and ADSR envelope.
"""

import math
from pathlib import Path
from typing import Optional, List
import numpy as np
import logging


logger = logging.getLogger(__name__)

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False


class SamplerVoice:
    def __init__(self, sample_data: np.ndarray, sample_rate: int):
        self._sample_data = sample_data.astype(np.float32)
        if self._sample_data.ndim > 1:
            self._sample_data = self._sample_data.mean(axis=1)
        self._sample_rate = sample_rate
        self._read_index = 0
        self._envelope = 1.0
        self._is_active = False
        self._is_finished = False
        self._base_note = 60
        self._playback_speed = 1.0
        self._loop_mode = False
        self._loop_start = 0
        self._loop_end = len(sample_data)

    def trigger(self, note: int, velocity: int, base_note: int = 60):
        semitones = note - base_note
        self._playback_speed = 2.0 ** (semitones / 12.0)
        self._read_index = 0
        self._envelope = velocity / 127.0
        self._is_active = True
        self._is_finished = False

    def release(self):
        self._is_active = False

    @property
    def is_finished(self) -> bool:
        return self._is_finished

    def process(self, num_samples: int) -> np.ndarray:
        if self._is_finished or len(self._sample_data) == 0:
            return np.zeros(num_samples, dtype=np.float32)

        output = np.zeros(num_samples, dtype=np.float32)
        data = self._sample_data
        total = len(data)

        for i in range(num_samples):
            idx = int(self._read_index)
            if idx >= total:
                if self._loop_mode:
                    self._read_index = self._loop_start
                    idx = int(self._read_index)
                else:
                    self._is_finished = True
                    break

            frac = self._read_index - idx
            next_idx = min(idx + 1, total - 1)
            sample = data[idx] * (1.0 - frac) + data[next_idx] * frac

            if not self._is_active:
                self._envelope *= 0.995
                if self._envelope < 0.001:
                    self._is_finished = True
                    break

            output[i] = sample * self._envelope
            self._read_index += self._playback_speed

        return output


class Sampler:
    """Sample-based instrument with pitch shifting, looping, and ADSR."""

    def __init__(self, sample_path: str = "", sample_rate: int = 44100):
        self._sample_rate = sample_rate
        self._sample_data: Optional[np.ndarray] = None
        self._base_note = 60
        self._loop_mode = False
        self._loop_start = 0
        self._loop_end = 0
        self._voices: List[SamplerVoice] = []
        self._master_volume = 0.8

        if sample_path:
            self.load_sample(sample_path)

    def load_sample(self, path: str) -> bool:
        if not HAS_SOUNDFILE:
            logger.warning("soundfile not available, cannot load samples")
            return False

        try:
            data, sr = sf.read(path)
            if data.ndim > 1:
                data = data.mean(axis=1)
            self._sample_data = data.astype(np.float32)
            self._loop_end = len(data)
            logger.info(f"Sample loaded: {path} ({len(data)} samples, {sr}Hz)")
            return True
        except Exception as e:
            logger.error(f"Error loading sample {path}: {e}")
            return False

    def set_loop(self, enabled: bool, start: int = 0, end: int = 0):
        self._loop_mode = enabled
        self._loop_start = start
        if end > 0:
            self._loop_end = end

    def set_base_note(self, note: int):
        self._base_note = note

    def note_on(self, note: int, velocity: int = 100) -> None:
        if self._sample_data is None:
            return
        voice = SamplerVoice(self._sample_data, self._sample_rate)
        voice._loop_mode = self._loop_mode
        voice._loop_start = self._loop_start
        voice._loop_end = self._loop_end
        voice.trigger(note, velocity, self._base_note)
        self._voices.append(voice)

    def note_off(self, note: int) -> None:
        for voice in self._voices:
            voice.release()

    def all_notes_off(self) -> None:
        for voice in self._voices:
            voice.release()

    def process(self, num_samples: int) -> np.ndarray:
        if not self._voices or self._sample_data is None:
            return np.zeros(num_samples, dtype=np.float32)

        output = np.zeros(num_samples, dtype=np.float32)
        finished: List[int] = []

        for i, voice in enumerate(self._voices):
            if voice.is_finished:
                finished.append(i)
                continue
            chunk = voice.process(num_samples)
            output += chunk

        for i in reversed(finished):
            self._voices.pop(i)

        output *= self._master_volume
        return output

    def set_parameter(self, param: str, value: float) -> None:
        if param == "volume":
            self._master_volume = max(0.0, min(1.0, value))
        elif param == "base_note":
            self._base_note = int(value)
