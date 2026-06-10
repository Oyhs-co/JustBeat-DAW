"""Gate - Noise gate con attack, hold, release y range."""

import numpy as np
from . import BaseEffect, _db_to_gain


class GateEffect(BaseEffect):
    """Noise gate con control de attack/hold/release/range."""

    def __init__(self, threshold: float = -40.0, attack: float = 0.002,
                 hold: float = 0.05, release: float = 0.1, range_db: float = -80.0):
        self.threshold = max(-80.0, min(0.0, threshold))
        self.attack = max(0.0001, min(1.0, attack))
        self.hold = max(0.0, min(5.0, hold))
        self.release = max(0.001, min(5.0, release))
        self.range = max(-100.0, min(0.0, range_db))
        self._env = 0.0
        self._gain = 1.0
        self._hold_counter = 0
        self._sample_rate = 44100

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        self._sample_rate = sample_rate
        out = np.zeros_like(audio)
        n = len(audio)
        att_coeff = np.exp(-1.0 / (sample_rate * self.attack))
        rel_coeff = np.exp(-1.0 / (sample_rate * self.release))
        thresh_level = _db_to_gain(self.threshold)
        range_gain = _db_to_gain(self.range)
        hold_samples = int(self.hold * sample_rate)

        for s in range(n):
            if audio.ndim == 1:
                dry = float(audio[s])
            else:
                dry = float(audio[s].mean())

            level = abs(dry)
            coeff = att_coeff if level > self._env else rel_coeff
            self._env += (level - self._env) * (1.0 - coeff)

            if self._env > thresh_level:
                self._gain = 1.0
                self._hold_counter = hold_samples
            elif self._hold_counter > 0:
                self._gain = 1.0
                self._hold_counter -= 1
            else:
                self._gain += (range_gain - self._gain) * (1.0 - rel_coeff)

            if audio.ndim == 1:
                out[s] = dry * self._gain
            else:
                out[s, 0] = audio[s, 0] * self._gain
                out[s, 1] = audio[s, 1] * self._gain
        return out

    def reset(self):
        self._env = 0.0
        self._gain = 1.0
        self._hold_counter = 0

    def to_dict(self) -> dict:
        return {"type": "GateEffect", "threshold": self.threshold,
                "attack": self.attack, "hold": self.hold,
                "release": self.release, "range": self.range}

    @classmethod
    def from_dict(cls, data: dict) -> "GateEffect":
        return cls(data.get("threshold", -40.0), data.get("attack", 0.002),
                   data.get("hold", 0.05), data.get("release", 0.1),
                   data.get("range", -80.0))
