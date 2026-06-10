"""EQ - 4 bandas paramétricas (Low Shelf, 2x Peak, High Shelf)."""

import numpy as np
from . import BaseEffect


class EQEffect(BaseEffect):
    """Ecualizador paramétrico de 4 bandas."""

    def __init__(self, low_freq: float = 200, low_gain: float = 0.0,
                 peak1_freq: float = 800, peak1_gain: float = 0.0, peak1_q: float = 1.0,
                 peak2_freq: float = 3000, peak2_gain: float = 0.0, peak2_q: float = 1.0,
                 high_freq: float = 8000, high_gain: float = 0.0):
        self.low_freq = max(20, min(2000, low_freq))
        self.low_gain = max(-24, min(24, low_gain))
        self.peak1_freq = max(20, min(20000, peak1_freq))
        self.peak1_gain = max(-24, min(24, peak1_gain))
        self.peak1_q = max(0.1, min(20.0, peak1_q))
        self.peak2_freq = max(20, min(20000, peak2_freq))
        self.peak2_gain = max(-24, min(24, peak2_gain))
        self.peak2_q = max(0.1, min(20.0, peak2_q))
        self.high_freq = max(500, min(20000, high_freq))
        self.high_gain = max(-24, min(24, high_gain))
        self._sample_rate = 44100
        self._reset_filters()

    def _reset_filters(self):
        self._lp = [0.0, 0.0]
        self._bp1 = [0.0, 0.0]
        self._bp2 = [0.0, 0.0]
        self._hp = [0.0, 0.0]

    def _apply_shelf(self, x: float, freq: float, gain: float, low: bool, state) -> float:
        a = 10.0 ** (gain / 40.0)
        w0 = 2 * np.pi * freq / self._sample_rate
        alpha = np.sin(w0) * np.sqrt(2) * 0.5

        if low:
            b0 = a * ((a + 1) - (a - 1) * np.cos(w0) + 2 * np.sqrt(a) * alpha)
            b1 = 2 * a * ((a - 1) - (a + 1) * np.cos(w0))
            b2 = a * ((a + 1) - (a - 1) * np.cos(w0) - 2 * np.sqrt(a) * alpha)
            a0 = (a + 1) + (a - 1) * np.cos(w0) + 2 * np.sqrt(a) * alpha
            a1 = -2 * ((a - 1) + (a + 1) * np.cos(w0))
            a2 = (a + 1) + (a - 1) * np.cos(w0) - 2 * np.sqrt(a) * alpha
        else:
            b0 = a * ((a + 1) + (a - 1) * np.cos(w0) + 2 * np.sqrt(a) * alpha)
            b1 = -2 * a * ((a - 1) + (a + 1) * np.cos(w0))
            b2 = a * ((a + 1) + (a - 1) * np.cos(w0) - 2 * np.sqrt(a) * alpha)
            a0 = (a + 1) - (a - 1) * np.cos(w0) + 2 * np.sqrt(a) * alpha
            a1 = 2 * ((a - 1) - (a + 1) * np.cos(w0))
            a2 = (a + 1) - (a - 1) * np.cos(w0) - 2 * np.sqrt(a) * alpha

        y = (b0 / a0) * x + state[0]
        state[0] = (b1 / a0) * x - (a1 / a0) * y + state[1]
        state[1] = (b2 / a0) * x - (a2 / a0) * y
        return y

    def _apply_peak(self, x: float, freq: float, gain: float, q: float, state) -> float:
        a = 10.0 ** (gain / 40.0)
        w0 = 2 * np.pi * freq / self._sample_rate
        alpha = np.sin(w0) / (2 * q)
        b0 = 1 + alpha * a
        b1 = -2 * np.cos(w0)
        b2 = 1 - alpha * a
        a0 = 1 + alpha / a
        a1 = -2 * np.cos(w0)
        a2 = 1 - alpha / a

        y = (b0 / a0) * x + state[0]
        state[0] = (b1 / a0) * x - (a1 / a0) * y + state[1]
        state[1] = (b2 / a0) * x - (a2 / a0) * y
        return y

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        self._sample_rate = sample_rate
        out = np.zeros_like(audio)
        n = len(audio)

        for s in range(n):
            for ch in range(audio.shape[1] if audio.ndim > 1 else 1):
                x = float(audio[s]) if audio.ndim == 1 else float(audio[s, ch])
                if self.low_gain != 0:
                    x = self._apply_shelf(x, self.low_freq, self.low_gain, True,
                                          [self._lp[ch] if ch < len(self._lp) else 0.0])
                if self.peak1_gain != 0:
                    x = self._apply_peak(x, self.peak1_freq, self.peak1_gain, self.peak1_q,
                                          [self._bp1[ch] if ch < len(self._bp1) else 0.0])
                if self.peak2_gain != 0:
                    x = self._apply_peak(x, self.peak2_freq, self.peak2_gain, self.peak2_q,
                                          [self._bp2[ch] if ch < len(self._bp2) else 0.0])
                if self.high_gain != 0:
                    x = self._apply_shelf(x, self.high_freq, self.high_gain, False,
                                          [self._hp[ch] if ch < len(self._hp) else 0.0])
                if audio.ndim == 1:
                    out[s] = x
                else:
                    out[s, ch] = x
        return out

    def reset(self):
        self._reset_filters()

    def to_dict(self) -> dict:
        return {"type": "EQEffect", "low_freq": self.low_freq, "low_gain": self.low_gain,
                "peak1_freq": self.peak1_freq, "peak1_gain": self.peak1_gain, "peak1_q": self.peak1_q,
                "peak2_freq": self.peak2_freq, "peak2_gain": self.peak2_gain, "peak2_q": self.peak2_q,
                "high_freq": self.high_freq, "high_gain": self.high_gain}

    @classmethod
    def from_dict(cls, data: dict) -> "EQEffect":
        return cls(data.get("low_freq", 200), data.get("low_gain", 0.0),
                   data.get("peak1_freq", 800), data.get("peak1_gain", 0.0), data.get("peak1_q", 1.0),
                   data.get("peak2_freq", 3000), data.get("peak2_gain", 0.0), data.get("peak2_q", 1.0),
                   data.get("high_freq", 8000), data.get("high_gain", 0.0))
