"""Compressor - RMS/Peak detector con knee."""

import numpy as np
from . import BaseEffect, _db_to_gain, _gain_to_db


class CompressorEffect(BaseEffect):
    """Compresor dinámico con detector RMS/Peak."""

    def __init__(self, threshold: float = -20.0, ratio: float = 4.0,
                 attack: float = 0.005, release: float = 0.1,
                 knee: float = 6.0, makeup: float = 0.0, auto_makeup: bool = True):
        self.threshold = max(-80.0, min(0.0, threshold))
        self.ratio = max(1.0, min(50.0, ratio))
        self.attack = max(0.0001, min(1.0, attack))
        self.release = max(0.001, min(5.0, release))
        self.knee = max(0.0, min(20.0, knee))
        self.makeup = max(0.0, min(24.0, makeup))
        self.auto_makeup = auto_makeup
        self._env = 0.0
        self._sample_rate = 44100

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        self._sample_rate = sample_rate
        out = np.zeros_like(audio)
        n = len(audio)
        att_coeff = np.exp(-1.0 / (sample_rate * self.attack))
        rel_coeff = np.exp(-1.0 / (sample_rate * self.release))
        thresh = _db_to_gain(self.threshold)
        makeup_gain = _db_to_gain(self.makeup)

        if self.auto_makeup:
            r = 1.0 - 1.0 / self.ratio
            makeup_gain = _db_to_gain(r * -self.threshold * 0.5)

        for s in range(n):
            if audio.ndim == 1:
                dry = float(audio[s])
            else:
                dry = float(audio[s].mean())

            level = abs(dry)
            coeff = att_coeff if level > self._env else rel_coeff
            self._env += (level - self._env) * (1.0 - coeff)

            if self.knee > 0 and self._env > thresh - _db_to_gain(self.knee * 0.5):
                db_env = _gain_to_db(max(1e-10, self._env))
                if self._env > thresh:
                    reduction = (db_env - self.threshold) * (1.0 - 1.0 / self.ratio)
                else:
                    k = self.knee
                    reduction = ((db_env - self.threshold + k * 0.5) ** 2) / (2 * k) * (1.0 - 1.0 / self.ratio)
                gain = _db_to_gain(-reduction) * makeup_gain
            elif self._env > thresh:
                db_env = _gain_to_db(max(1e-10, self._env))
                reduction = (db_env - self.threshold) * (1.0 - 1.0 / self.ratio)
                gain = _db_to_gain(-reduction) * makeup_gain
            else:
                gain = makeup_gain

            if audio.ndim == 1:
                out[s] = dry * gain
            else:
                out[s, 0] = audio[s, 0] * gain
                out[s, 1] = audio[s, 1] * gain
        return out

    def reset(self):
        self._env = 0.0

    def to_dict(self) -> dict:
        return {"type": "CompressorEffect", "threshold": self.threshold,
                "ratio": self.ratio, "attack": self.attack, "release": self.release,
                "knee": self.knee, "makeup": self.makeup, "auto_makeup": self.auto_makeup}

    @classmethod
    def from_dict(cls, data: dict) -> "CompressorEffect":
        return cls(data.get("threshold", -20.0), data.get("ratio", 4.0),
                   data.get("attack", 0.005), data.get("release", 0.1),
                   data.get("knee", 6.0), data.get("makeup", 0.0),
                   data.get("auto_makeup", True))
