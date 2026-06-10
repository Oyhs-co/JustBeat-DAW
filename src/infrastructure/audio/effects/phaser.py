"""Phaser - All-pass filter chain."""

import numpy as np
from . import BaseEffect


class PhaserEffect(BaseEffect):
    """Phaser con all-pass filters en cascada."""

    def __init__(self, stages: int = 6, rate: float = 0.4,
                 feedback: float = 0.5, spread: float = 0.5, wet_dry: float = 0.5):
        self.stages = max(2, min(24, stages))
        self.rate = max(0.01, min(20.0, rate))
        self.feedback = max(0.0, min(0.95, feedback))
        self.spread = max(0.0, min(1.0, spread))
        self.wet_dry = max(0.0, min(1.0, wet_dry))
        self._lfo_phase = 0.0
        self._state = np.zeros(self.stages, dtype=np.float32)
        self._fb_out = 0.0
        self._sample_rate = 44100

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        self._sample_rate = sample_rate
        out = np.zeros_like(audio)
        n = len(audio)
        dt = 1.0 / sample_rate

        for s in range(n):
            if audio.ndim == 1:
                dry = float(audio[s])
            else:
                dry = float(audio[s].mean())

            self._lfo_phase += self.rate * dt
            if self._lfo_phase > 1.0:
                self._lfo_phase -= 1.0

            lfo = (np.sin(2 * np.pi * self._lfo_phase) + 1.0) * 0.5
            base_freq = 200 + lfo * 3000
            x = dry + self._fb_out * self.feedback

            for i in range(self.stages):
                f = base_freq * (1.0 + self.spread * (i / max(1, self.stages - 1) - 0.5))
                f = max(20, min(sample_rate * 0.45, f))
                coeff = (1.0 - np.tan(np.pi * f / sample_rate)) / (1.0 + np.tan(np.pi * f / sample_rate))
                y = coeff * (x - self._state[i])
                self._state[i] = y + x
                x = y

            wet = y
            self._fb_out = wet

            if audio.ndim == 1:
                out[s] = dry * (1.0 - self.wet_dry) + wet * self.wet_dry
            else:
                v = dry * (1.0 - self.wet_dry) + wet * self.wet_dry
                out[s, 0] = v
                out[s, 1] = v
        return out

    def reset(self):
        self._state.fill(0.0)
        self._fb_out = 0.0
        self._lfo_phase = 0.0

    def to_dict(self) -> dict:
        return {"type": "PhaserEffect", "stages": self.stages, "rate": self.rate,
                "feedback": self.feedback, "spread": self.spread, "wet_dry": self.wet_dry}

    @classmethod
    def from_dict(cls, data: dict) -> "PhaserEffect":
        return cls(data.get("stages", 6), data.get("rate", 0.4),
                   data.get("feedback", 0.5), data.get("spread", 0.5),
                   data.get("wet_dry", 0.5))
