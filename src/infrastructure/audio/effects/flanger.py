"""Flanger - Chorus con feedback e invert."""

import numpy as np
from . import BaseEffect


class FlangerEffect(BaseEffect):
    """Flanger con LFO, feedback e invert."""

    def __init__(self, rate: float = 0.3, depth: float = 0.002,
                 feedback: float = 0.5, invert: bool = False, wet_dry: float = 0.5):
        self.rate = max(0.05, min(20.0, rate))
        self.depth = max(0.0001, min(0.005, depth))
        self.feedback = max(0.0, min(0.95, feedback))
        self.invert = invert
        self.wet_dry = max(0.0, min(1.0, wet_dry))
        self._lfo_phase = 0.0
        self._buf = np.zeros(0, dtype=np.float32)
        self._idx = 0
        self._sample_rate = 44100
        self._init_buf()

    def _init_buf(self):
        size = int(0.02 * self._sample_rate)
        if len(self._buf) != size:
            self._buf = np.zeros(size, dtype=np.float32)
            self._idx = 0

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        self._sample_rate = sample_rate
        self._init_buf()
        out = np.zeros_like(audio)
        n = len(audio)
        buf_len = len(self._buf)
        dt = 1.0 / sample_rate

        for s in range(n):
            if audio.ndim == 1:
                dry = float(audio[s])
            else:
                dry = float(audio[s].mean())

            self._lfo_phase += self.rate * dt
            if self._lfo_phase > 1.0:
                self._lfo_phase -= 1.0

            lfo = np.sin(2 * np.pi * self._lfo_phase)
            mod_delay = int(self.depth * (1.0 + lfo) * sample_rate)
            mod_delay = max(1, min(mod_delay, buf_len - 1))

            read_idx = (self._idx - mod_delay) % buf_len
            wet = float(self._buf[int(read_idx)])

            if self.invert:
                wet = -wet

            self._buf[self._idx] = dry + wet * self.feedback
            self._idx = (self._idx + 1) % buf_len

            if audio.ndim == 1:
                out[s] = dry * (1.0 - self.wet_dry) + wet * self.wet_dry
            else:
                v = dry * (1.0 - self.wet_dry) + wet * self.wet_dry
                out[s, 0] = v
                out[s, 1] = v
        return out

    def reset(self):
        self._buf.fill(0.0)
        self._idx = 0
        self._lfo_phase = 0.0

    def to_dict(self) -> dict:
        return {"type": "FlangerEffect", "rate": self.rate, "depth": self.depth,
                "feedback": self.feedback, "invert": self.invert, "wet_dry": self.wet_dry}

    @classmethod
    def from_dict(cls, data: dict) -> "FlangerEffect":
        return cls(data.get("rate", 0.3), data.get("depth", 0.002),
                   data.get("feedback", 0.5), data.get("invert", False),
                   data.get("wet_dry", 0.5))
