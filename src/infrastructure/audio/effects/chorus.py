"""Chorus - Modulación de delay con LFO."""

import numpy as np
from . import BaseEffect


class ChorusEffect(BaseEffect):
    """Chorus con LFO modulando delay."""

    def __init__(self, rate: float = 0.5, depth: float = 0.003,
                 delay: float = 0.025, feedback: float = 0.2, wet_dry: float = 0.4):
        self.rate = max(0.05, min(20.0, rate))
        self.depth = max(0.0, min(0.01, depth))
        self.delay_base = max(0.001, min(0.05, delay))
        self.feedback = max(0.0, min(0.95, feedback))
        self.wet_dry = max(0.0, min(1.0, wet_dry))
        self._lfo_phase = 0.0
        self._buf = np.zeros(0, dtype=np.float32)
        self._idx = 0
        self._sample_rate = 44100
        self._init_buf()

    def _init_buf(self):
        size = int(0.1 * self._sample_rate)
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
            mod_delay = int((self.delay_base + self.depth * (1.0 + lfo)) * sample_rate)
            mod_delay = max(1, min(mod_delay, buf_len - 1))

            read_idx = (self._idx - mod_delay) % buf_len
            wet = float(self._buf[int(read_idx)])

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
        return {"type": "ChorusEffect", "rate": self.rate, "depth": self.depth,
                "delay": self.delay_base, "feedback": self.feedback, "wet_dry": self.wet_dry}

    @classmethod
    def from_dict(cls, data: dict) -> "ChorusEffect":
        return cls(data.get("rate", 0.5), data.get("depth", 0.003),
                   data.get("delay", 0.025), data.get("feedback", 0.2),
                   data.get("wet_dry", 0.4))
