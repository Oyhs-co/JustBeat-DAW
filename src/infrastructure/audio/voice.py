from typing import List
from dataclasses import dataclass, field

from src.infrastructure.audio.oscillator import EnvStage


@dataclass
class Voice:
    note: int
    velocity: int
    age: int = 0
    envelope: EnvStage = EnvStage.IDLE
    envelope_level: float = 0.0
    phase: float = 0.0
    release_time: float = 0.0
    unison_phases: List[float] = field(default_factory=list)
    velocity_scale: float = 1.0


@dataclass
class ADSREnvelope:
    attack: float = 0.01
    decay: float = 0.1
    sustain: float = 0.7
    release: float = 0.3
    attack_curve: float = 2.0
    decay_curve: float = 2.0
    release_curve: float = 2.0

    def __post_init__(self):
        self.attack = max(0.001, self.attack)
        self.decay = max(0.0, self.decay)
        self.sustain = max(0.0, min(1.0, self.sustain))
        self.release = max(0.01, self.release)
        self.attack_curve = max(0.5, min(10.0, self.attack_curve))
        self.decay_curve = max(0.5, min(10.0, self.decay_curve))
        self.release_curve = max(0.5, min(10.0, self.release_curve))
