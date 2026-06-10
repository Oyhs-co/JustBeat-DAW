"""Drum Machine - Synthesis-based drum sound generator.

Generates classic drum sounds (kick, snare, hi-hat, etc.)
using pure synthesis (no samples needed).
"""

import math
import random
from typing import Dict, List, Optional
import numpy as np
import logging


logger = logging.getLogger(__name__)


GM_KICK = 36
GM_SNARE = 38
GM_HH_CLOSED = 42
GM_HH_OPEN = 46
GM_CLAP = 39
GM_TOM_LOW = 41
GM_TOM_MID = 45
GM_TOM_HIGH = 47
GM_CRASH = 49
GM_RIDE = 51
GM_RIM = 37


class DrumSynth:
    def __init__(self, sample_rate: int = 44100):
        self._sample_rate = sample_rate
        self._voices: Dict[int, DrumVoice] = {}
        self._master_volume = 0.8

    def note_on(self, note: int, velocity: int = 100) -> None:
        if velocity == 0:
            return
        voice = DrumVoice(note, velocity, self._sample_rate)
        voice.trigger()
        self._voices[note] = voice

    def note_off(self, note: int) -> None:
        if note in self._voices:
            self._voices[note].release()

    def all_notes_off(self) -> None:
        for voice in self._voices.values():
            voice.release()

    def process(self, num_samples: int) -> np.ndarray:
        if not self._voices:
            return np.zeros(num_samples, dtype=np.float32)

        output = np.zeros(num_samples, dtype=np.float32)
        finished: List[int] = []

        for note, voice in self._voices.items():
            if voice.is_finished:
                finished.append(note)
                continue
            chunk = voice.process(num_samples)
            output += chunk

        for note in finished:
            del self._voices[note]

        output *= self._master_volume
        return output

    def set_parameter(self, param: str, value: float) -> None:
        pass


class DrumVoice:
    def __init__(self, note: int, velocity: int, sample_rate: int):
        self._note = note
        self._velocity = velocity / 127.0
        self._sample_rate = sample_rate
        self._phase = 0.0
        self._envelope = 1.0
        self._age = 0
        self._is_released = False
        self._is_finished = False
        self._noise_state = 0.0

        self._drum_type = self._get_drum_type(note)
        self._setup_params()

    def _get_drum_type(self, note: int) -> str:
        mapping = {
            GM_KICK: "kick",
            GM_SNARE: "snare",
            GM_HH_CLOSED: "hh_closed",
            GM_HH_OPEN: "hh_open",
            GM_CLAP: "clap",
            GM_TOM_LOW: "tom_low",
            GM_TOM_MID: "tom_mid",
            GM_TOM_HIGH: "tom_high",
            GM_CRASH: "crash",
            GM_RIDE: "ride",
            GM_RIM: "rim",
        }
        return mapping.get(note, "kick")

    def _setup_params(self):
        t = self._drum_type
        if t == "kick":
            self._freq_start = 150.0
            self._freq_end = 40.0
            self._decay = 0.15
            self._noise_amt = 0.0
        elif t == "snare":
            self._freq_start = 200.0
            self._freq_end = 180.0
            self._decay = 0.2
            self._noise_amt = 0.6
        elif t == "hh_closed":
            self._freq_start = 8000.0
            self._freq_end = 8000.0
            self._decay = 0.05
            self._noise_amt = 0.9
        elif t == "hh_open":
            self._freq_start = 8000.0
            self._freq_end = 6000.0
            self._decay = 0.4
            self._noise_amt = 0.9
        elif t == "clap":
            self._freq_start = 1000.0
            self._freq_end = 500.0
            self._decay = 0.15
            self._noise_amt = 1.0
        elif t == "tom_low":
            self._freq_start = 150.0
            self._freq_end = 80.0
            self._decay = 0.3
            self._noise_amt = 0.1
        elif t == "tom_mid":
            self._freq_start = 220.0
            self._freq_end = 120.0
            self._decay = 0.3
            self._noise_amt = 0.1
        elif t == "tom_high":
            self._freq_start = 330.0
            self._freq_end = 180.0
            self._decay = 0.3
            self._noise_amt = 0.1
        elif t in ("crash", "ride"):
            self._freq_start = 10000.0
            self._freq_end = 4000.0
            self._decay = 0.8
            self._noise_amt = 0.85
        elif t == "rim":
            self._freq_start = 3000.0
            self._freq_end = 2000.0
            self._decay = 0.03
            self._noise_amt = 0.7
        else:
            self._freq_start = 200.0
            self._freq_end = 100.0
            self._decay = 0.2
            self._noise_amt = 0.3

    def trigger(self):
        self._phase = 0.0
        self._envelope = 1.0
        self._age = 0
        self._is_released = False
        self._is_finished = False

    def release(self):
        self._is_released = True

    @property
    def is_finished(self) -> bool:
        return self._is_finished

    def process(self, num_samples: int) -> np.ndarray:
        output = np.zeros(num_samples, dtype=np.float32)
        sr = self._sample_rate
        vel = self._velocity

        for i in range(num_samples):
            if self._is_finished:
                break

            t = self._age / sr
            env = math.exp(-t / self._decay) if self._decay > 0 else 1.0
            if env < 0.001:
                self._is_finished = True
                break

            freq = self._freq_end + (self._freq_start - self._freq_end) * env
            self._phase += freq / sr
            if self._phase >= 1.0:
                self._phase -= 1.0

            tone = math.sin(self._phase * 2.0 * math.pi)
            noise = random.uniform(-1.0, 1.0)

            sample = tone * (1.0 - self._noise_amt) + noise * self._noise_amt
            sample *= env * vel
            output[i] = sample
            self._age += 1

        return output


class DrumMachine:
    """Drum machine with multiple synthesis-based drum voices.

    Maps to General MIDI drum notes by default.
    """

    def __init__(self, sample_rate: int = 44100):
        self._synth = DrumSynth(sample_rate)

    def note_on(self, note: int, velocity: int = 100) -> None:
        self._synth.note_on(note, velocity)

    def note_off(self, note: int) -> None:
        self._synth.note_off(note)

    def all_notes_off(self) -> None:
        self._synth.all_notes_off()

    def process(self, num_samples: int) -> np.ndarray:
        return self._synth.process(num_samples)

    def set_parameter(self, param: str, value: float) -> None:
        self._synth.set_parameter(param, value)
