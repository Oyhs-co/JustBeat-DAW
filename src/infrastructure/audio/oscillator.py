import math
import random
from enum import Enum


class Waveform(Enum):
    SINE = "sine"
    SQUARE = "square"
    SAWTOOTH = "sawtooth"
    TRIANGLE = "triangle"
    NOISE = "noise"
    PULSE_25 = "pulse_25"
    PULSE_12_5 = "pulse_12_5"


class NoiseType(Enum):
    WHITE = "white"
    PINK = "pink"
    BROWN = "brown"


class EnvStage(Enum):
    IDLE = "idle"
    ATTACK = "attack"
    DECAY = "decay"
    SUSTAIN = "sustain"
    RELEASE = "release"


def generate_waveform(phase: float, waveform: Waveform) -> float:
    if waveform == Waveform.SINE:
        return math.sin(phase * 2.0 * math.pi)

    elif waveform == Waveform.SQUARE:
        return 1.0 if phase < 0.5 else -1.0

    elif waveform == Waveform.SAWTOOTH:
        return 2.0 * phase - 1.0

    elif waveform == Waveform.TRIANGLE:
        if phase < 0.5:
            return 4.0 * phase - 1.0
        else:
            return 3.0 - 4.0 * phase

    elif waveform == Waveform.PULSE_25:
        return 1.0 if phase < 0.25 else -1.0

    elif waveform == Waveform.PULSE_12_5:
        return 1.0 if phase < 0.125 else -1.0

    elif waveform == Waveform.NOISE:
        return random.uniform(-1.0, 1.0)

    return 0.0
