import math
import random
from typing import List, Optional, Any
from dataclasses import dataclass
import numpy as np
import logging

from src.infrastructure.audio.oscillator import Waveform, NoiseType, generate_waveform
from src.infrastructure.audio.polyphonic_synth import PolyphonicSynth


logger = logging.getLogger(__name__)


@dataclass
class OscillatorConfig:
    waveform: Waveform = Waveform.SINE
    volume: float = 1.0
    pan: float = 0.0
    coarse_tune: int = 0
    fine_tune: float = 0.0
    unison_count: int = 1
    unison_detune: float = 5.0


class MultiOscillatorSynth:
    MAX_OSCILLATORS = 4

    def __init__(
        self,
        sample_rate: int = 44100,
        max_voices: int = 16
    ):
        self._sample_rate = sample_rate
        self._max_voices = max_voices

        self._oscillators: List[PolyphonicSynth] = [
            PolyphonicSynth(sample_rate, max_voices)
            for _ in range(3)
        ]

        self._osc_configs: List[OscillatorConfig] = [
            OscillatorConfig(waveform=Waveform.SQUARE, volume=1.0),
            OscillatorConfig(waveform=Waveform.SAWTOOTH, volume=0.5),
            OscillatorConfig(waveform=Waveform.SINE, volume=0.25),
        ]
        self._apply_osc_configs()

        self._ring_mod_amount: float = 0.0
        self._fm_amount: float = 0.0

        self._noise_type: NoiseType = NoiseType.WHITE
        self._noise_level: float = 0.0
        self._pink_state: float = 0.0
        self._brown_state: float = 0.0

        self._volume: float = 0.8
        self._effects: List[Any] = []

        logger.info(
            f"MultiOscillatorSynth mejorado: {sample_rate}Hz, "
            f"{max_voices} voces/osc"
        )

    def _apply_osc_configs(self) -> None:
        for i, (osc, config) in enumerate(
            zip(self._oscillators, self._osc_configs)
        ):
            osc.waveform = config.waveform
            total_cents = config.coarse_tune * 100 + config.fine_tune
            osc.tuning_multiplier = 2.0 ** (total_cents / 1200.0)
            osc.unison_count = config.unison_count
            osc.unison_detune = config.unison_detune

    # === Configuración de osciladores ===

    def set_oscillator_waveform(
        self, index: int, waveform: Waveform
    ) -> bool:
        if 0 <= index < len(self._osc_configs):
            self._osc_configs[index].waveform = waveform
            self._oscillators[index].waveform = waveform
            return True
        return False

    def set_oscillator_volume(
        self, index: int, volume: float
    ) -> bool:
        if 0 <= index < len(self._osc_configs):
            self._osc_configs[index].volume = max(0.0, min(1.0, volume))
            return True
        return False

    def set_oscillator_pan(
        self, index: int, pan: float
    ) -> bool:
        if 0 <= index < len(self._osc_configs):
            self._osc_configs[index].pan = max(-1.0, min(1.0, pan))
            return True
        return False

    def set_oscillator_tuning(
        self, index: int, coarse: int = 0, fine: float = 0.0
    ) -> bool:
        if 0 <= index < len(self._osc_configs):
            self._osc_configs[index].coarse_tune = max(
                -24, min(24, coarse)
            )
            self._osc_configs[index].fine_tune = max(
                -100.0, min(100.0, fine)
            )
            total_cents = (
                self._osc_configs[index].coarse_tune * 100
                + self._osc_configs[index].fine_tune
            )
            self._oscillators[index].tuning_multiplier = (
                2.0 ** (total_cents / 1200.0)
            )
            return True
        return False

    def set_oscillator_unison(
        self, index: int, count: int = 1, detune: float = 5.0
    ) -> bool:
        if 0 <= index < len(self._osc_configs):
            self._osc_configs[index].unison_count = max(1, min(8, count))
            self._osc_configs[index].unison_detune = max(0.0, min(50.0, detune))
            osc = self._oscillators[index]
            osc.unison_count = self._osc_configs[index].unison_count
            osc.unison_detune = self._osc_configs[index].unison_detune
            return True
        return False

    def get_oscillator_config(
        self, index: int
    ) -> Optional[OscillatorConfig]:
        if 0 <= index < len(self._osc_configs):
            return self._osc_configs[index]
        return None

    # === Ring Modulation ===

    @property
    def ring_mod_amount(self) -> float:
        return self._ring_mod_amount

    @ring_mod_amount.setter
    def ring_mod_amount(self, value: float) -> None:
        self._ring_mod_amount = max(0.0, min(1.0, value))

    # === FM Synthesis ===

    @property
    def fm_amount(self) -> float:
        return self._fm_amount

    @fm_amount.setter
    def fm_amount(self, value: float) -> None:
        self._fm_amount = max(0.0, min(1.0, value))

    # === Noise Generator ===

    @property
    def noise_type(self) -> NoiseType:
        return self._noise_type

    @noise_type.setter
    def noise_type(self, value: NoiseType) -> None:
        self._noise_type = value

    @property
    def noise_level(self) -> float:
        return self._noise_level

    @noise_level.setter
    def noise_level(self, value: float) -> None:
        self._noise_level = max(0.0, min(1.0, value))

    def _generate_noise(self, num_samples: int) -> np.ndarray:
        if self._noise_level <= 0:
            return np.zeros(num_samples, dtype=np.float32)

        if self._noise_type == NoiseType.WHITE:
            noise = np.random.uniform(
                -1.0, 1.0, num_samples
            ).astype(np.float32)

        elif self._noise_type == NoiseType.PINK:
            noise = np.zeros(num_samples, dtype=np.float32)
            state = self._pink_state
            b0 = 0.99765
            b1 = 0.96300
            b2 = 0.57050
            for i in range(num_samples):
                white = random.uniform(-1.0, 1.0)
                state = b0 * state + white * 0.1
                pink = state + b1 * random.uniform(-1.0, 1.0)
                pink += b2 * random.uniform(-1.0, 1.0)
                noise[i] = pink * 0.5
            self._pink_state = state

        elif self._noise_type == NoiseType.BROWN:
            noise = np.zeros(num_samples, dtype=np.float32)
            state = self._brown_state
            for i in range(num_samples):
                white = random.uniform(-1.0, 1.0)
                state = state * 0.998 + white * 0.02
                if state > 1.0:
                    state = 1.0
                elif state < -1.0:
                    state = -1.0
                noise[i] = state * 0.5
            self._brown_state = state

        else:
            noise = np.zeros(num_samples, dtype=np.float32)

        return noise * self._noise_level

    # === Notas ===

    def note_on(self, note: int, velocity: int) -> None:
        for osc in self._oscillators:
            osc.note_on(note, velocity)

    def note_off(self, note: int) -> None:
        for osc in self._oscillators:
            osc.note_off(note)

    def all_notes_off(self) -> None:
        for osc in self._oscillators:
            osc.all_notes_off()

    # === Procesamiento ===

    def process(self, num_samples: int) -> np.ndarray:
        if num_samples <= 0:
            return np.zeros(1, dtype=np.float32)

        osc_outputs: List[np.ndarray] = []
        for osc in self._oscillators:
            osc_outputs.append(osc.process(num_samples))

        if self._fm_amount > 0 and len(osc_outputs) >= 2:
            fm_mod = osc_outputs[0] * self._fm_amount * 0.5
            osc2_phase_mod = np.cumsum(fm_mod) * 0.1
            osc2_phase_mod = np.clip(osc2_phase_mod, -1.0, 1.0)
            osc_outputs[1] = osc_outputs[1] * (
                1.0 - self._fm_amount * 0.3
            )

        if self._ring_mod_amount > 0 and len(osc_outputs) >= 2:
            ring = (
                osc_outputs[0]
                * osc_outputs[1]
                * self._ring_mod_amount
            )
            osc_outputs[0] = osc_outputs[0] * (
                1.0 - self._ring_mod_amount * 0.3
            ) + ring * 0.5

        output = np.zeros(num_samples, dtype=np.float32)
        for i, (osc_out, config) in enumerate(
            zip(osc_outputs, self._osc_configs)
        ):
            vol = config.volume
            pan = config.pan
            if abs(pan) > 0.01:
                pan_gain = 1.0 - abs(pan) * 0.3
                output += osc_out * vol * pan_gain
            else:
                output += osc_out * vol

        noise = self._generate_noise(num_samples)
        output += noise

        if self._oscillators:
            output /= math.sqrt(len(self._oscillators))

        output *= self._volume

        return output

    # === Utilidades ===

    def get_oscillator_count(self) -> int:
        return len(self._oscillators)

    def get_active_voices(self) -> int:
        return sum(
            osc.get_active_voices() for osc in self._oscillators
        )

    # === Serialización ===

    def to_dict(self) -> dict:
        return {
            "oscillators": [
                {
                    "waveform": config.waveform.value,
                    "volume": config.volume,
                    "pan": config.pan,
                    "coarse_tune": config.coarse_tune,
                    "fine_tune": config.fine_tune,
                    "unison_count": config.unison_count,
                    "unison_detune": config.unison_detune,
                    "synth": osc.to_dict(),
                }
                for osc, config in zip(
                    self._oscillators, self._osc_configs
                )
            ],
            "ring_mod_amount": self._ring_mod_amount,
            "fm_amount": self._fm_amount,
            "noise_type": self._noise_type.value,
            "noise_level": self._noise_level,
            "volume": self._volume,
        }

    @classmethod
    def from_dict(
        cls, data: dict, sample_rate: int = 44100
    ) -> "MultiOscillatorSynth":
        synth = cls(sample_rate=sample_rate)

        osc_data_list = data.get("oscillators", [])
        for i, osc_data in enumerate(osc_data_list):
            if i >= len(synth._osc_configs):
                break
            config = synth._osc_configs[i]
            config.waveform = Waveform(
                osc_data.get("waveform", "sine")
            )
            config.volume = osc_data.get("volume", 1.0)
            config.pan = osc_data.get("pan", 0.0)
            config.coarse_tune = osc_data.get("coarse_tune", 0)
            config.fine_tune = osc_data.get("fine_tune", 0.0)
            config.unison_count = osc_data.get("unison_count", 1)
            config.unison_detune = osc_data.get("unison_detune", 5.0)

            osc_synth_data = osc_data.get("synth", {})
            synth._oscillators[i] = PolyphonicSynth.from_dict(
                osc_synth_data, sample_rate
            )

        synth._apply_osc_configs()

        synth._ring_mod_amount = data.get("ring_mod_amount", 0.0)
        synth._fm_amount = data.get("fm_amount", 0.0)
        synth._noise_type = NoiseType(
            data.get("noise_type", "white")
        )
        synth._noise_level = data.get("noise_level", 0.0)
        synth._volume = data.get("volume", 0.8)

        return synth
