"""Limiter - Brickwall con lookahead."""

import numpy as np
from . import BaseEffect, _db_to_gain


class LimiterEffect(BaseEffect):
    """Brickwall limiter con lookahead y release."""

    def __init__(self, threshold: float = -1.0, release: float = 0.05, lookahead: float = 0.002):
        self.threshold = max(-20.0, min(0.0, threshold))
        self.release = max(0.001, min(1.0, release))
        self.lookahead = max(0.0, min(0.01, lookahead))
        self._gain = 1.0
        self._buf = np.zeros(0, dtype=np.float32)
        self._idx = 0
        self._sample_rate = 44100
        self._init_buf()

    def _init_buf(self):
        size = max(1, int(self.lookahead * self._sample_rate))
        if len(self._buf) != size:
            self._buf = np.zeros(size, dtype=np.float32)
            self._idx = 0

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        self._sample_rate = sample_rate
        self._init_buf()
        out = np.zeros_like(audio)
        n = len(audio)
        buf_len = len(self._buf)
        ceil = _db_to_gain(self.threshold)
        rel_coeff = np.exp(-1.0 / (sample_rate * self.release))

        for s in range(n):
            if audio.ndim == 1:
                dry = float(audio[s])
            else:
                dry = float(audio[s].mean())

            level = abs(dry)
            if level > ceil:
                target_gain = ceil / max(1e-10, level)
                self._gain = min(self._gain, target_gain)
            else:
                self._gain += (1.0 - self._gain) * (1.0 - rel_coeff)

            self._buf[self._idx] = dry * self._gain
            read_idx = (self._idx + 1) % buf_len
            delayed = float(self._buf[int(read_idx)])
            self._idx = read_idx

            if audio.ndim == 1:
                out[s] = delayed
            else:
                out[s, 0] = delayed
                out[s, 1] = delayed
        return out

    def reset(self):
        self._gain = 1.0
        self._buf.fill(0.0)
        self._idx = 0

    def to_dict(self) -> dict:
        return {"type": "LimiterEffect", "threshold": self.threshold,
                "release": self.release, "lookahead": self.lookahead}

    @classmethod
    def from_dict(cls, data: dict) -> "LimiterEffect":
        return cls(data.get("threshold", -1.0), data.get("release", 0.05),
                   data.get("lookahead", 0.002))
