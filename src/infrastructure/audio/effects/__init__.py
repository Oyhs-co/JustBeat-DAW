"""Sistema de efectos DSP para JustBeat-DAW.

Cada efecto implementa AudioEffect con process(), reset(), to_dict(), from_dict().
Usa numpy arrays (n_samples, n_channels) para procesamiento eficiente.
"""

from typing import Protocol, Dict, Any
import numpy as np


class AudioEffect(Protocol):
    """Protocolo que todos los efectos DSP deben implementar."""

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        ...

    def reset(self) -> None:
        ...

    def to_dict(self) -> dict:
        ...

    @classmethod
    def from_dict(cls, data: dict) -> "AudioEffect":
        ...


class BaseEffect:
    """Base class con helpers comunes."""

    def reset(self):
        pass

    def to_dict(self) -> dict:
        return {"type": self.__class__.__name__}

    @classmethod
    def from_dict(cls, data: dict) -> "BaseEffect":
        return cls(**{k: v for k, v in data.items() if k != "type"})


def _db_to_gain(db: float) -> float:
    return 10.0 ** (db / 20.0)


def _gain_to_db(gain: float) -> float:
    if gain <= 0:
        return -float("inf")
    return 20.0 * np.log10(gain)
