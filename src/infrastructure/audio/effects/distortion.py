"""Distortion - Waveshaping + Bitcrushing."""

import numpy as np
from . import BaseEffect


class DistortionEffect(BaseEffect):
    """Distorsión con waveshaping y bitcrushing."""

    def __init__(self, drive: float = 0.5, tone: float = 0.5,
                 bit_depth: int = 16, sample_rate_reduce: int = 1, mix: float = 1.0):
        self.drive = max(0.0, min(1.0, drive))
        self.tone = max(0.0, min(1.0, tone))
        self.bit_depth = max(1, min(16, bit_depth))
        self.sample_rate_reduce = max(1, min(64, sample_rate_reduce))
        self.mix = max(0.0, min(1.0, mix))
        self._sample_count = 0
        self._last_sample = 0.0

    def _waveshape(self, x: float) -> float:
        d = self.drive * 8.0 + 1.0
        return np.tanh(x * d) / np.tanh(d)

    def _bitcrush(self, x: float) -> float:
        if self.bit_depth >= 16:
            return x
        levels = 2 ** self.bit_depth
        return np.floor(x * levels + 0.5) / levels

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        out = np.zeros_like(audio)
        n = len(audio)
        lowpass_fb = 0.0

        for s in range(n):
            if audio.ndim == 1:
                dry = float(audio[s])
            else:
                dry = float(audio[s].mean())

            self._sample_count += 1
            if self._sample_count % self.sample_rate_reduce == 0:
                shaped = self._waveshape(dry)
                crushed = self._bitcrush(shaped)
                self._last_sample = crushed

            wet = self._last_sample
            lowpass_fb = lowpass_fb * self.tone + wet * (1.0 - self.tone)
            wet = lowpass_fb * self.drive + wet * (1.0 - self.drive)
            wet = self.mix * wet + (1.0 - self.mix) * dry

            if audio.ndim == 1:
                out[s] = wet
            else:
                out[s, 0] = wet
                out[s, 1] = wet
        return out

    def reset(self):
        self._sample_count = 0
        self._last_sample = 0.0

    def to_dict(self) -> dict:
        return {"type": "DistortionEffect", "drive": self.drive, "tone": self.tone,
                "bit_depth": self.bit_depth, "sample_rate_reduce": self.sample_rate_reduce,
                "mix": self.mix}

    @classmethod
    def from_dict(cls, data: dict) -> "DistortionEffect":
        return cls(data.get("drive", 0.5), data.get("tone", 0.5),
                   data.get("bit_depth", 16), data.get("sample_rate_reduce", 1),
                   data.get("mix", 1.0))
