"""Audio Ports - Interfaces para el sistema de audio.

Define los contratos que AppCore espera de la capa de infraestructura
de audio. Las implementaciones concretas (AudioManager, MixerEngine,
etc.) cumplen estos protocolos por structural typing.
"""

from typing import Protocol, Dict, List, Tuple, Optional, Any


class AudioEngineProtocol(Protocol):
    """Contrato para el motor de audio (compatible con IAudioService)."""

    def play(self) -> None:
        ...

    def pause(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def seek(self, position: int) -> None:
        ...

    def set_bpm(self, bpm: int) -> None:
        ...

    def get_position(self) -> int:
        ...

    def is_playing(self) -> bool:
        ...

    def shutdown(self) -> None:
        ...


class MixerEngineProtocol(Protocol):
    """Contrato para el mezclador."""

    def get_meter_levels(self) -> Dict[str, Tuple[float, float]]:
        ...


class AudioRouterProtocol(Protocol):
    """Contrato para el ruteador de audio."""

    def process_buffer(self, frames: int) -> Any:
        ...

    def note_on(self, track_id: str, note: int, velocity: int) -> None:
        ...

    def note_off(self, track_id: str, note: int) -> None:
        ...

    def create_track_channel(
        self, track_id: str, waveform: str = "square",
        note: int = 60, volume: float = 0.8
    ) -> None:
        ...

    def remove_track_channel(self, track_id: str) -> None:
        ...

    def set_track_volume(self, track_id: str, volume: float) -> None:
        ...

    def set_track_mute(self, track_id: str, muted: bool) -> None:
        ...

    def set_track_pan(self, track_id: str, pan: float) -> None:
        ...

    def set_global_synth(self, synth: Any) -> None:
        ...


class InstrumentRackProtocol(Protocol):
    """Contrato para el rack de instrumentos."""

    def get_instrument(self, slot: int) -> Optional[Any]:
        ...

    def set_instrument(self, slot: int, instrument: Any, name: str = "") -> None:
        ...


class PresetManagerProtocol(Protocol):
    """Contrato para el gestor de presets."""

    def get_preset(self, preset_id: str) -> Optional[Any]:
        ...


class PerformanceMonitorProtocol(Protocol):
    """Contrato para el monitor de rendimiento."""

    def stop_monitoring(self) -> None:
        ...


class HardwareEmulationProtocol(Protocol):
    """Contrato para la emulación de hardware."""

    def add_chip(self, chip_type: Any) -> None:
        ...

    def set_active_chip(self, chip_type: Any) -> None:
        ...


class AudioManagerProtocol(Protocol):
    """Contrato para el gestor de audio en tiempo real."""

    @property
    def is_playing(self) -> bool:
        ...

    @property
    def count_in_enabled(self) -> bool:
        ...

    @property
    def loop_enabled(self) -> bool:
        ...

    def start_stream(self) -> None:
        ...

    def stop_stream(self) -> None:
        ...

    def start_sequencer(self) -> None:
        ...

    def stop_sequencer(self) -> None:
        ...

    def pause_sequencer(self) -> None:
        ...

    def register_track(
        self, track_id: str, note: int = 60,
        volume: float = 0.8, muted: bool = False,
        waveform: str = "square", pan: float = 0.0
    ) -> None:
        ...

    def unregister_track(self, track_id: str) -> None:
        ...

    def init_track_steps(self, track_index: int) -> None:
        ...

    def set_track_volume(self, track_id: str, volume: float) -> None:
        ...

    def set_track_mute(self, track_id: str, muted: bool) -> None:
        ...

    def set_track_pan(self, track_id: str, pan: float) -> None:
        ...

    def set_track_note(self, track_id: str, note: int) -> None:
        ...

    def set_num_steps(self, num_steps: int) -> None:
        ...

    def set_step_active(self, track_index: int, step: int, active: bool) -> None:
        ...

    def get_step_states(self) -> Dict[int, List[bool]]:
        ...

    def get_all_track_synths(self) -> Dict[str, dict]:
        ...

    def get_audio_levels(self) -> Tuple[float, float]:
        ...

    def get_waveform_data(self, num_samples: int = 256) -> Tuple[list, list]:
        ...

    def toggle_metronome(self) -> bool:
        ...

    def toggle_count_in(self) -> bool:
        ...

    def toggle_loop(self) -> bool:
        ...

    def note_on(self, note: int, velocity: int = 100) -> None:
        ...

    def note_off(self, note: int) -> None:
        ...

    def shutdown(self) -> None:
        ...
