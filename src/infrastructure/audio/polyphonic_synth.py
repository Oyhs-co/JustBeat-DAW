import math
from typing import Dict, List, Optional, Any
import numpy as np
import logging

from src.infrastructure.audio.oscillator import Waveform, EnvStage, generate_waveform
from src.infrastructure.audio.voice import Voice, ADSREnvelope


logger = logging.getLogger(__name__)


class PolyphonicSynth:
    MAX_VOICES = 16

    _MIDI_FREQ_TABLE: List[float] = [
        440.0 * (2.0 ** ((n - 69) / 12.0)) for n in range(128)
    ]

    def __init__(
        self,
        sample_rate: int = 44100,
        max_voices: int = 16
    ):
        self._sample_rate = sample_rate
        self._max_voices = min(max_voices, self.MAX_VOICES)

        self._voices: Dict[int, Voice] = {}

        self._waveform = Waveform.SQUARE
        self._envelope = ADSREnvelope()
        self._volume = 0.8
        self._detune = 0.0
        self._glide = 0.0
        self._glide_speed = 0.1
        self._last_note: Optional[int] = None

        self._lpf_state: float = 0.0
        self._lpf_cutoff: float = 20000.0
        self._lpf_coef: float = 0.0
        self._update_lpf_coef()

        self._velocity_amount: float = 0.5

        self._unison_count: int = 1
        self._unison_detune: float = 5.0
        self._unison_mults: List[float] = [1.0]

        self._base_frequency = 440.0
        self._tuning_multiplier: float = 1.0

        logger.info(
            f"PolyphonicSynth mejorado: {self._max_voices} voces, "
            f"{sample_rate}Hz"
        )

    def _update_lpf_coef(self) -> None:
        if self._lpf_cutoff >= self._sample_rate * 0.5:
            self._lpf_coef = 1.0
        else:
            self._lpf_coef = 1.0 - math.exp(
                -2.0 * math.pi * self._lpf_cutoff / self._sample_rate
            )

    def _update_unison_mults(self) -> None:
        self._unison_mults = [1.0]
        if self._unison_count > 1:
            center = (self._unison_count - 1) / 2.0
            for i in range(1, self._unison_count):
                offset = (i - center) / center
                mult = 2.0 ** (self._unison_detune * offset / 1200.0)
                self._unison_mults.append(mult)

    # === Propiedades ===

    @property
    def waveform(self) -> Waveform:
        return self._waveform

    @waveform.setter
    def waveform(self, value: Waveform) -> None:
        self._waveform = value

    @property
    def envelope(self) -> ADSREnvelope:
        return self._envelope

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = max(0.0, min(1.0, value))

    @property
    def detune(self) -> float:
        return self._detune

    @detune.setter
    def detune(self, value: float) -> None:
        self._detune = max(-100.0, min(100.0, value))

    @property
    def glide(self) -> float:
        return self._glide

    @glide.setter
    def glide(self, value: float) -> None:
        self._glide = max(0.0, min(1.0, value))

    @property
    def tuning_multiplier(self) -> float:
        return self._tuning_multiplier

    @tuning_multiplier.setter
    def tuning_multiplier(self, value: float) -> None:
        self._tuning_multiplier = max(0.5, min(2.0, value))

    @property
    def unison_count(self) -> int:
        return self._unison_count

    @unison_count.setter
    def unison_count(self, value: int) -> None:
        self._unison_count = max(1, min(8, value))
        self._update_unison_mults()

    @property
    def unison_detune(self) -> float:
        return self._unison_detune

    @unison_detune.setter
    def unison_detune(self, value: float) -> None:
        self._unison_detune = max(0.0, min(50.0, value))
        self._update_unison_mults()

    @property
    def velocity_amount(self) -> float:
        return self._velocity_amount

    @velocity_amount.setter
    def velocity_amount(self, value: float) -> None:
        self._velocity_amount = max(0.0, min(1.0, value))

    # === Configuración ===

    def set_waveform(self, waveform: str) -> None:
        try:
            self._waveform = Waveform(waveform.lower())
        except ValueError:
            logger.warning(f"Waveform desconocida: {waveform}, usando square")
            self._waveform = Waveform.SQUARE

    def set_parameter(self, param: str, value: Any) -> None:
        param = param.lower()

        if param == "attack":
            self._envelope.attack = max(0.001, float(value) / 1000.0)
        elif param == "decay":
            self._envelope.decay = max(0.0, float(value) / 1000.0)
        elif param == "sustain":
            self._envelope.sustain = max(0.0, min(1.0, float(value) / 100.0))
        elif param == "release":
            self._envelope.release = max(0.01, float(value) / 1000.0)
        elif param == "attack_curve":
            self._envelope.attack_curve = max(0.5, min(10.0, float(value)))
        elif param == "decay_curve":
            self._envelope.decay_curve = max(0.5, min(10.0, float(value)))
        elif param == "release_curve":
            self._envelope.release_curve = max(0.5, min(10.0, float(value)))
        elif param == "volume":
            self._volume = max(0.0, min(1.0, float(value)))
        elif param == "detune":
            self._detune = float(value)
        elif param == "glide":
            self._glide = max(0.0, min(1.0, float(value)))
        elif param == "velocity_amount":
            self._velocity_amount = max(0.0, min(1.0, float(value)))
        elif param == "unison_count":
            self.unison_count = int(value)
        elif param == "unison_detune":
            self.unison_detune = float(value)
        elif param == "lpf_cutoff":
            self._lpf_cutoff = max(20.0, min(20000.0, float(value)))
            self._update_lpf_coef()
        elif param == "tuning":
            self._tuning_multiplier = max(0.5, min(2.0, float(value)))

    # === Nota On/Off ===

    def note_on(self, note: int, velocity: int) -> None:
        if velocity == 0:
            self.note_off(note)
            return

        velocity = max(1, min(127, velocity))

        if self._velocity_amount > 0:
            v_scale = (velocity / 127.0) ** (1.0 - self._velocity_amount * 0.7)
        else:
            v_scale = 1.0

        if note in self._voices:
            voice = self._voices[note]
            voice.velocity = velocity
            voice.velocity_scale = v_scale
            voice.envelope = EnvStage.ATTACK
            voice.envelope_level = 0.0
            voice.phase = 0.0
            voice.unison_phases = [0.0] * (self._unison_count - 1)
        else:
            voice = self._allocate_voice(note, velocity, v_scale)
            if voice:
                self._voices[note] = voice

        self._last_note = note

    def note_off(self, note: int) -> None:
        if note in self._voices:
            voice = self._voices[note]
            voice.envelope = EnvStage.RELEASE
            voice.release_time = 0.0

    def _allocate_voice(
        self,
        note: int,
        velocity: int,
        velocity_scale: float
    ) -> Optional[Voice]:
        if len(self._voices) < self._max_voices:
            return Voice(
                note=note,
                velocity=velocity,
                velocity_scale=velocity_scale,
                envelope=EnvStage.ATTACK,
                envelope_level=0.0,
                phase=0.0,
                unison_phases=[0.0] * (self._unison_count - 1)
            )

        oldest_note = min(
            self._voices.keys(),
            key=lambda n: self._voices[n].age
        )

        voice = self._voices[oldest_note]
        del self._voices[oldest_note]

        voice.note = note
        voice.velocity = velocity
        voice.velocity_scale = velocity_scale
        voice.envelope = EnvStage.ATTACK
        voice.envelope_level = 0.0
        voice.phase = 0.0
        voice.unison_phases = [0.0] * (self._unison_count - 1)
        voice.age = 0

        return voice

    def _get_frequency(self, note: int) -> float:
        if 0 <= note < 128:
            freq = self._MIDI_FREQ_TABLE[note]
        else:
            freq = self._base_frequency * (2.0 ** ((note - 69) / 12.0))

        freq *= 2.0 ** (self._detune / 1200.0)
        freq *= self._tuning_multiplier

        return freq

    def _gen_waveform(self, phase: float) -> float:
        return generate_waveform(phase, self._waveform)

    # === Procesamiento ===

    def process(self, num_samples: int) -> np.ndarray:
        if num_samples <= 0:
            return np.zeros(1, dtype=np.float32)

        output = np.zeros(num_samples, dtype=np.float32)

        if not self._voices:
            return output

        env = self._envelope
        sr = self._sample_rate

        a_coef = 0.0
        if env.attack > 0:
            a_coef = 1.0 - math.exp(-env.attack_curve / (env.attack * sr))

        d_coef = 0.0
        if env.decay > 0:
            d_coef = 1.0 - math.exp(-env.decay_curve / (env.decay * sr))

        r_coef = 0.0
        if env.release > 0:
            r_coef = 1.0 - math.exp(-env.release_curve / (env.release * sr))

        voices_to_remove: List[int] = []

        for note, voice in self._voices.items():
            freq = self._get_frequency(voice.note)
            phase_inc = freq / sr
            u_mults = self._unison_mults
            u_count = self._unison_count

            for i in range(num_samples):
                stage = voice.envelope

                if stage == EnvStage.ATTACK:
                    voice.envelope_level += (
                        (1.0 - voice.envelope_level) * a_coef
                    )
                    if voice.envelope_level >= 0.999:
                        voice.envelope_level = 1.0
                        voice.envelope = EnvStage.DECAY

                elif stage == EnvStage.DECAY:
                    diff = voice.envelope_level - env.sustain
                    if diff > 0.0001:
                        voice.envelope_level -= diff * d_coef
                    else:
                        voice.envelope_level = env.sustain
                        voice.envelope = EnvStage.SUSTAIN

                elif stage == EnvStage.SUSTAIN:
                    pass

                elif stage == EnvStage.RELEASE:
                    if voice.envelope_level > 0.0001:
                        voice.envelope_level -= (
                            voice.envelope_level * r_coef
                        )
                    else:
                        voice.envelope_level = 0.0
                        voices_to_remove.append(note)
                        break

                voice.phase += phase_inc
                if voice.phase >= 1.0:
                    voice.phase -= 1.0

                for j in range(len(voice.unison_phases)):
                    voice.unison_phases[j] += (
                        phase_inc * u_mults[j + 1]
                    )
                    if voice.unison_phases[j] >= 1.0:
                        voice.unison_phases[j] -= 1.0

                sample = self._gen_waveform(voice.phase)
                for j in range(len(voice.unison_phases)):
                    sample += self._gen_waveform(voice.unison_phases[j])
                sample /= u_count

                sample *= voice.envelope_level * voice.velocity_scale

                output[i] += sample

            voice.age += num_samples

        for note in voices_to_remove:
            self._voices.pop(note, None)

        if self._lpf_coef < 1.0 and output.any():
            state = self._lpf_state
            coef = self._lpf_coef
            for i in range(num_samples):
                state += coef * (output[i] - state)
                output[i] = state
            self._lpf_state = state

        output *= self._volume

        voice_count = len(self._voices)
        if voice_count > 0:
            gain = 1.0 / math.sqrt(voice_count + 1)
            output *= min(1.0, gain * 2.0)

        return output

    # === Utilidades ===

    def get_active_voices(self) -> int:
        return len(self._voices)

    def is_playing_note(self, note: int) -> bool:
        return note in self._voices

    def all_notes_off(self) -> None:
        self._voices.clear()

    # === Serialización ===

    def to_dict(self) -> dict:
        return {
            "waveform": self._waveform.value,
            "envelope": {
                "attack": self._envelope.attack,
                "decay": self._envelope.decay,
                "sustain": self._envelope.sustain,
                "release": self._envelope.release,
                "attack_curve": self._envelope.attack_curve,
                "decay_curve": self._envelope.decay_curve,
                "release_curve": self._envelope.release_curve,
            },
            "volume": self._volume,
            "detune": self._detune,
            "glide": self._glide,
            "max_voices": self._max_voices,
            "velocity_amount": self._velocity_amount,
            "unison_count": self._unison_count,
            "unison_detune": self._unison_detune,
            "lpf_cutoff": self._lpf_cutoff,
            "tuning_multiplier": self._tuning_multiplier,
        }

    @classmethod
    def from_dict(cls, data: dict, sample_rate: int = 44100) -> "PolyphonicSynth":
        synth = cls(sample_rate=sample_rate)

        synth._waveform = Waveform(data.get("waveform", "square"))

        env_data = data.get("envelope", {})
        synth._envelope = ADSREnvelope(
            attack=env_data.get("attack", 0.01),
            decay=env_data.get("decay", 0.1),
            sustain=env_data.get("sustain", 0.7),
            release=env_data.get("release", 0.3),
            attack_curve=env_data.get("attack_curve", 2.0),
            decay_curve=env_data.get("decay_curve", 2.0),
            release_curve=env_data.get("release_curve", 2.0),
        )

        synth._volume = data.get("volume", 0.8)
        synth._detune = data.get("detune", 0.0)
        synth._glide = data.get("glide", 0.0)
        synth._velocity_amount = data.get("velocity_amount", 0.5)
        synth._unison_count = data.get("unison_count", 1)
        synth._unison_detune = data.get("unison_detune", 5.0)
        synth._lpf_cutoff = data.get("lpf_cutoff", 20000.0)
        synth._tuning_multiplier = data.get("tuning_multiplier", 1.0)

        synth._update_unison_mults()
        synth._update_lpf_coef()

        return synth
