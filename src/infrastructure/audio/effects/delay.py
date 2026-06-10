"""Delay - Ping-pong estéreo con feedback."""

import numpy as np
from . import BaseEffect


class DelayEffect(BaseEffect):
    """Delay ping-pong estéreo."""

    def __init__(self, delay_time: float = 0.25, feedback: float = 0.4,
                 ping_pong: bool = True, wet_dry: float = 0.3):
        self.delay_time = max(0.01, min(5.0, delay_time))
        self.feedback = max(0.0, min(0.99, feedback))
        self.ping_pong = ping_pong
        self.wet_dry = max(0.0, min(1.0, wet_dry))
        self._buf = np.zeros(0, dtype=np.float32)
        self._idx = 0
        self._sample_rate = 44100
        self._init_buf()

    def _init_buf(self):
        size = max(1, int(self.delay_time * self._sample_rate))
        if len(self._buf) != size:
            self._buf = np.zeros(size, dtype=np.float32)
            self._idx = 0

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        self._sample_rate = sample_rate
        self._init_buf()
        out = np.zeros_like(audio)
        n = len(audio)

        for s in range(n):
            if audio.ndim == 1:
                dry = float(audio[s])
            else:
                dry = float(audio[s].mean())

            buf_out = float(self._buf[self._idx])
            self._buf[self._idx] = dry + buf_out * self.feedback

            wet = buf_out
            if audio.ndim == 1:
                out[s] = dry * (1.0 - self.wet_dry) + wet * self.wet_dry
            else:
                if self.ping_pong:
                    alt = 1 if (s // int(self.delay_time * sample_rate)) % 2 == 0 else 0
                    l = dry * (1.0 - self.wet_dry) + (wet if alt == 0 else 0) * self.wet_dry
                    r = dry * (1.0 - self.wet_dry) + (wet if alt == 1 else 0) * self.wet_dry
                else:
                    l = dry * (1.0 - self.wet_dry) + wet * self.wet_dry
                    r = l
                out[s, 0] = l
                out[s, 1] = r

            self._idx = (self._idx + 1) % len(self._buf)
        return out

    def reset(self):
        self._buf.fill(0.0)
        self._idx = 0

    def to_dict(self) -> dict:
        return {"type": "DelayEffect", "delay_time": self.delay_time,
                "feedback": self.feedback, "ping_pong": self.ping_pong, "wet_dry": self.wet_dry}

    @classmethod
    def from_dict(cls, data: dict) -> "DelayEffect":
        return cls(data.get("delay_time", 0.25), data.get("feedback", 0.4),
                   data.get("ping_pong", True), data.get("wet_dry", 0.3))
