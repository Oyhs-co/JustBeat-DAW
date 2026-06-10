"""Reverb - Freeverb mejorado (8 comb filters + 4 allpass)."""

import numpy as np
from . import BaseEffect


class ReverbEffect(BaseEffect):
    """Reverb basado en Freeverb con 8 comb filters y 4 allpass filters."""

    def __init__(self, room_size: float = 0.7, damping: float = 0.5,
                 width: float = 1.0, wet_dry: float = 0.3):
        self.room_size = min(0.99, max(0.0, room_size))
        self.damping = min(1.0, max(0.0, damping))
        self.width = min(1.0, max(0.0, width))
        self.wet_dry = min(1.0, max(0.0, wet_dry))
        self._sample_rate = 44100
        self._comb_delays = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617]
        self._allpass_delays = [225, 341, 441, 556]
        self._comb_gains = [0.0] * 8
        self._allpass_gains = [0.0] * 4
        self._buf = [np.zeros(d, dtype=np.float32) for d in self._comb_delays + self._allpass_delays]
        self._idx = [0] * (8 + 4)
        self._update_gains()

    def _update_gains(self):
        scale = self.room_size * 0.8 + 0.2
        for i in range(8):
            self._comb_gains[i] = scale * (0.96 + 0.005 * (i % 4))
        for i in range(4):
            self._allpass_gains[i] = 0.5

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        self._sample_rate = sample_rate
        self._update_gains()
        out = np.zeros_like(audio)
        n = len(audio)

        for s in range(n):
            input_s = float(audio[s]) if audio.ndim == 1 else float(audio[s].mean())
            dry = float(audio[s]) if audio.ndim == 1 else float(audio[s, 0])

            # Comb filters
            comb_sum = 0.0
            for i in range(8):
                idx = self._idx[i]
                delay = self._comb_delays[i]
                buf_out = self._buf[i][idx]
                self._buf[i][idx] = input_s + self._comb_gains[i] * buf_out
                comb_sum += buf_out
                self._idx[i] = (idx + 1) % delay
            comb_sum /= 8.0

            # Allpass filters
            for i in range(8, 12):
                idx = self._idx[i]
                delay = self._allpass_delays[i - 8]
                buf_out = self._buf[i][idx]
                ap_in = comb_sum if i == 8 else buf_out
                self._buf[i][idx] = ap_in + self._allpass_gains[i - 8] * buf_out
                comb_sum = -ap_in * self._allpass_gains[i - 8] + buf_out
                self._idx[i] = (idx + 1) % delay

            wet = comb_sum
            damped = wet * (1.0 - self.damping)
            if audio.ndim == 1:
                out[s] = dry * (1.0 - self.wet_dry) + damped * self.wet_dry
            else:
                l = dry * (1.0 - self.wet_dry) + damped * self.wet_dry * (1.0 - self.width * 0.5)
                r = dry * (1.0 - self.wet_dry) + damped * self.wet_dry * (0.5 + self.width * 0.5)
                out[s, 0] = l
                out[s, 1] = r
        return out

    def reset(self):
        for i in range(len(self._buf)):
            self._buf[i].fill(0.0)
            self._idx[i] = 0

    def to_dict(self) -> dict:
        return {"type": "ReverbEffect", "room_size": self.room_size,
                "damping": self.damping, "width": self.width, "wet_dry": self.wet_dry}

    @classmethod
    def from_dict(cls, data: dict) -> "ReverbEffect":
        return cls(data.get("room_size", 0.7), data.get("damping", 0.5),
                   data.get("width", 1.0), data.get("wet_dry", 0.3))
