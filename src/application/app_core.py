"""Application Core - Núcleo de la aplicación.

Controlador principal de la aplicación (reemplaza JustBeatApp legacy).
Wiring completo de la nueva arquitectura con handlers y servicios.
"""

from typing import Optional, Dict, List, Any, Callable
from pathlib import Path
import logging
import time
import numpy as np
import wave

from PySide6.QtCore import QObject, Signal

from src.domain.events.event_bus import (
    EventBus, get_event_bus,
    ProjectEvents, TransportEvents, TrackEvents, NoteEvents
)
from src.domain.entities.project import Project
from src.domain.entities.track import Track
from src.domain.entities.timeline import Timeline
from src.domain.entities.tempo_map import TempoMap

from src.application.handlers.project_handler import ProjectHandler
from src.application.handlers.transport_handler import TransportHandler
from src.application.handlers.track_handler import TrackHandler
from src.application.handlers.note_handler import NoteHandler
from src.application.handlers.automation_handler import AutomationHandler
from src.application.handlers.arrangement_handler import ArrangementHandler
from src.application.handlers.recording_handler import RecordingHandler
from src.application.handlers.midi_recording_handler import MIDIRecordingHandler
from src.application.handlers.state_handler import StateHandler
from src.application.commands.command_history import CommandHistory

from src.application.services.transport_service import TransportService
from src.domain.transport_state import TransportState

from src.application.ports.audio_port import (
    AudioManagerProtocol, AudioEngineProtocol,
    MixerEngineProtocol, AudioRouterProtocol,
    InstrumentRackProtocol, PresetManagerProtocol,
    PerformanceMonitorProtocol, HardwareEmulationProtocol,
)
from src.application.ports.persistence_port import (
    ProjectManagerProtocol, RecoverySystemProtocol,
)

# Concrete infrastructure imports (only for default creation in initialize())
from src.infrastructure.audio.polyphonic_synth import PolyphonicSynth
from src.infrastructure.audio.instrument_rack import InstrumentFactory
from src.infrastructure.audio.preset_manager import get_preset_manager
from src.infrastructure.audio.hardware_emulation import ChipType
from src.infrastructure.audio.audio_manager import AudioManager
from src.infrastructure.audio.audio_router import AudioRouter
from src.infrastructure.audio.mixer_engine import MixerEngine
from src.infrastructure.audio.instrument_rack import InstrumentRack
from src.infrastructure.audio.preset_manager import PresetManager
from src.infrastructure.audio.performance_monitor import PerformanceMonitor
from src.infrastructure.audio.hardware_emulation import HardwareEmulationMode
from src.infrastructure.midi.midi_handler import MIDIHandler
from src.infrastructure.persistence.project_manager import ProjectManager
from src.infrastructure.persistence.project_recovery import ProjectRecoverySystem


logger = logging.getLogger(__name__)


class AppCore(QObject):
    """Core of the application.
    
    Integrates all components of the new architecture.
    Replaces the old AppState singleton.
    """
    
    # Señales para la UI
    project_loaded = Signal(object)  # Project
    project_saved = Signal(str)     # path
    playback_state_changed = Signal(str)  # state
    position_changed = Signal(int)   # tick
    bpm_changed = Signal(int)        # bpm
    track_added = Signal(object)     # Track
    track_removed = Signal(str)      # track_id
    track_selected = Signal(str)     # track_id
    modification_changed = Signal(bool)  # is_modified
    error_occurred = Signal(str)     # error_message
    
    def __init__(
        self,
        sample_rate: int = 44100,
        buffer_size: int = 512,
        event_bus: Optional[EventBus] = None,
        transport_service: Optional[TransportService] = None,
        command_history: Optional[CommandHistory] = None,
        project_handler: Optional[ProjectHandler] = None,
        transport_handler: Optional[TransportHandler] = None,
        track_handler: Optional[TrackHandler] = None,
        note_handler: Optional[NoteHandler] = None,
        automation_handler: Optional[AutomationHandler] = None,
        arrangement_handler: Optional[ArrangementHandler] = None,
        audio_engine: Optional[AudioEngineProtocol] = None,
        mixer_engine: Optional[MixerEngineProtocol] = None,
        audio_manager: Optional[AudioManagerProtocol] = None,
        audio_router: Optional[AudioRouterProtocol] = None,
        instrument_rack: Optional[InstrumentRackProtocol] = None,
        preset_manager: Optional[PresetManagerProtocol] = None,
        performance_monitor: Optional[PerformanceMonitorProtocol] = None,
        hardware_emulation: Optional[HardwareEmulationProtocol] = None,
        midi_handler: Optional[MIDIHandler] = None,
        project_manager: Optional[ProjectManagerProtocol] = None,
        recovery_system: Optional[RecoverySystemProtocol] = None,
        recording_handler: Optional[RecordingHandler] = None,
        midi_recording_handler: Optional[MIDIRecordingHandler] = None,
    ):
        """Inicializar núcleo de aplicación con inyección de dependencias.

        Cada dependencia es opcional. Si no se provee, initialize()
        crea una instancia por defecto.

        Args:
            sample_rate: Sample rate
            buffer_size: Buffer size
            event_bus: Event bus (crea global si no se provee)
            transport_service: Servicio de transporte
            command_history: Historial de comandos (undo/redo)
            project_handler: Handler de proyectos
            transport_handler: Handler de transporte
            track_handler: Handler de pistas
            note_handler: Handler de notas
            automation_handler: Handler de automatización
            arrangement_handler: Handler de arreglo
            audio_engine: Motor de audio
            mixer_engine: Mezclador
            audio_manager: Gestor de audio
            audio_router: Ruteador de audio
            instrument_rack: Rack de instrumentos
            preset_manager: Gestor de presets
            performance_monitor: Monitor de rendimiento
            hardware_emulation: Modo de emulación de hardware
            midi_handler: Handler MIDI
            project_manager: Gestor de proyectos
            recovery_system: Sistema de recuperación
        """
        super().__init__()

        self._sample_rate = sample_rate
        self._buffer_size = buffer_size
        self._event_bus = event_bus or get_event_bus()

        # Estado
        self._is_initialized = False
        self._current_project: Optional[Project] = None
        self._is_modified = False

        # === Dependencias inyectadas (None = se crearán en initialize()) ===
        self._transport_service = transport_service
        self._command_history = command_history
        self._project_handler = project_handler
        self._transport_handler = transport_handler
        self._track_handler = track_handler
        self._note_handler = note_handler
        self._automation_handler = automation_handler
        self._arrangement_handler = arrangement_handler
        self._audio_engine = audio_engine
        self._mixer_engine = mixer_engine
        self._audio_manager = audio_manager
        self._audio_router = audio_router
        self._instrument_rack = instrument_rack
        self._preset_manager = preset_manager
        self._performance_monitor = performance_monitor
        self._hardware_emulation = hardware_emulation
        self._midi_handler = midi_handler
        self._project_manager = project_manager
        self._recovery_system = recovery_system
        self._state_handler = StateHandler()
        self._recording_handler = recording_handler
        self._midi_recording_handler = midi_recording_handler

        logger.info("AppCore creado")
    
    # === Inicialización ===
    
    def initialize(self) -> bool:
        """Inicializar todos los componentes.

        Crea valores por defecto solo para dependencias que no fueron
        inyectadas en el constructor.
        """
        if self._is_initialized:
            logger.warning("AppCore ya inicializado")
            return True

        try:
            # === Servicios ===
            if self._transport_service is None:
                self._transport_service = TransportService(
                    sample_rate=self._sample_rate,
                    ticks_per_beat=480
                )
            if self._command_history is None:
                self._command_history = CommandHistory(max_history=100)

            # === Handlers ===
            if self._project_handler is None:
                self._project_handler = ProjectHandler()
            if self._transport_handler is None:
                self._transport_handler = TransportHandler()
            if self._track_handler is None:
                self._track_handler = TrackHandler()
            if self._note_handler is None:
                self._note_handler = NoteHandler()
            if self._automation_handler is None:
                self._automation_handler = AutomationHandler()
            if self._arrangement_handler is None:
                self._arrangement_handler = ArrangementHandler()
            if self._recording_handler is None:
                self._recording_handler = RecordingHandler()
            if self._midi_recording_handler is None:
                self._midi_recording_handler = MIDIRecordingHandler()

            # === Infraestructura de audio ===
            if self._audio_router is None:
                from config.settings import get_settings
                _settings = get_settings()
                self._audio_router = AudioRouter(
                    sample_rate=self._sample_rate,
                    buffer_size=self._buffer_size,
                    verbose_audio=_settings.audio.verbose_audio
                )
            if self._audio_engine is None and self._audio_manager is None:
                self._audio_manager = AudioManager(
                    sample_rate=self._sample_rate,
                    buffer_size=self._buffer_size,
                    audio_router=self._audio_router
                )
                self._audio_engine = self._audio_manager
            elif self._audio_engine is None and self._audio_manager is not None:
                self._audio_engine = self._audio_manager
            elif self._audio_engine is not None and self._audio_manager is None:
                self._audio_manager = self._audio_engine
            if self._mixer_engine is None:
                self._mixer_engine = MixerEngine(
                    sample_rate=self._sample_rate,
                    buffer_size=self._buffer_size
                )
            if self._instrument_rack is None:
                self._instrument_rack = InstrumentRack(num_slots=8)
                default_synth = InstrumentFactory.create_synth(
                    "square", self._sample_rate
                )
                self._instrument_rack.set_instrument(
                    0, default_synth, name="Square Lead"
                )
            if self._preset_manager is None:
                self._preset_manager = get_preset_manager()
            if self._performance_monitor is None:
                self._performance_monitor = PerformanceMonitor(
                    sample_rate=self._sample_rate,
                    buffer_size=self._buffer_size
                )
            if self._hardware_emulation is None:
                self._hardware_emulation = HardwareEmulationMode(
                    sample_rate=self._sample_rate
                )
                self._hardware_emulation.add_chip(ChipType.NES)
                self._hardware_emulation.add_chip(ChipType.C64)

            # === MIDI ===
            if self._midi_handler is None:
                self._midi_handler = MIDIHandler()

            # === Persistencia ===
            if self._project_manager is None:
                self._project_manager = ProjectManager()
            if self._recovery_system is None:
                self._recovery_system = ProjectRecoverySystem()

            # === Wiring (siempre ejecutar) ===
            if self._transport_handler and self._audio_engine:
                self._transport_handler.audio_service = self._audio_engine

            if self._transport_service:
                self._transport_service.set_position_callback(
                    self._on_position_changed
                )
                self._transport_service.set_state_callback(
                    self._on_transport_state_changed
                )
                self._transport_service.set_bpm_callback(
                    self._on_bpm_changed
                )

            self._is_initialized = True

            # Restore persisted state
            theme_variant = self._state_handler.get("theme.variant", "obsidian")
            try:
                from src.presentation.styles.pro_theme import ProTheme
                ProTheme.set_variant(theme_variant)
            except Exception:
                pass

            last_sample_rate = self._state_handler.get("audio.sample_rate", self._sample_rate)
            last_buffer = self._state_handler.get("audio.buffer_size", self._buffer_size)
            if self._audio_manager and hasattr(self._audio_manager, 'set_project_sample_rate'):
                try:
                    self._audio_manager.set_project_sample_rate(last_sample_rate)
                except Exception:
                    pass

            # Inicializar PresentationModel con esta misma instancia
            try:
                from src.presentation.models.presentation_model import (
                    initialize_presentation_model
                )
                initialize_presentation_model(self)
                logger.info("PresentationModel inicializado con AppCore")
            except Exception as pm_err:
                logger.warning(
                    f"No se pudo inicializar PresentationModel: {pm_err}"
                )

            # Crear proyecto por defecto
            self.create_new_project("Untitled")

            # Crear cache inicial
            self._create_startup_cache()

            # Verificar capas de audio
            self.verify_audio_layers()

            # NOTA: El stream de audio NO se inicia aquí.
            # Se inicia de forma diferida en main() después de que MainWindow
            # esté completamente creada, para evitar buffer underruns durante
            # la inicialización pesada de la UI (widgets, docks, layouts).
            # Ver: start_audio_stream()

            logger.info("AppCore inicializado correctamente")
            return True

        except Exception as e:
            logger.error(f"Error inicializando AppCore: {e}")
            self.error_occurred.emit(str(e))
            return False
    
    # === Callbacks del Transport ===
    
    def _on_position_changed(self, tick: int) -> None:
        self.position_changed.emit(tick)
    
    def _on_transport_state_changed(self, state: TransportState) -> None:
        self.playback_state_changed.emit(state.value)
        if self._event_bus:
            if state == TransportState.PLAYING:
                self._event_bus.publish(TransportEvents.started())
            elif state == TransportState.PAUSED:
                self._event_bus.publish(TransportEvents.paused())
            elif state == TransportState.STOPPED:
                self._event_bus.publish(TransportEvents.stopped())
    
    def _on_bpm_changed(self, bpm: int) -> None:
        self.bpm_changed.emit(bpm)
        if self._event_bus:
            self._event_bus.publish(TransportEvents.bpm_changed(bpm))

    def save_state(self):
        if hasattr(self, '_state_handler'):
            self._state_handler.set("audio.sample_rate", self._sample_rate)
            self._state_handler.set("audio.buffer_size", self._buffer_size)
            theme_variant = self._state_handler.get("theme.variant", "obsidian")
            from src.presentation.styles.pro_theme import ProTheme
            self._state_handler.set("theme.variant", ProTheme.get_variant())

    # === Proyecto ===
    
    def create_new_project(self, name: str = "Untitled") -> Project:
        project = Project(name=name)
        project.timeline = Timeline()
        project.tempo_map = TempoMap()
        self._current_project = project
        self._is_modified = False
        
        default_tracks = [
            ("Square Lead", 60, "square"),
            ("Triangle Bass", 48, "triangle"),
            ("Noise Drums", 36, "noise"),
            ("Saw Melody", 64, "sawtooth"),
        ]
        for i, (track_name, note, waveform) in enumerate(default_tracks):
            track = project.add_track(track_name)
            if self._track_handler:
                self._track_handler._tracks_cache[track.id] = track
            track_id = f"track_{i}"
            if self._audio_manager:
                self._audio_manager.register_track(
                    track_id=track_id, note=note,
                    volume=0.8, waveform=waveform
                )
                self._audio_manager.init_track_steps(i)
        
        self.project_loaded.emit(project)
        logger.info(f"Nuevo proyecto: {name} con {len(project.get_tracks())} tracks")
        self._create_startup_cache()
        if self._event_bus:
            self._event_bus.publish(ProjectEvents.created(project.name, project.id))
        return project
    
    def _create_startup_cache(self) -> None:
        if not self._current_project:
            return
        try:
            cache_dir = Path("cache")
            cache_dir.mkdir(exist_ok=True)
            cache_path = cache_dir / "startup_project.jbp"
            if self._project_manager:
                self._project_manager.save_project(
                    self._current_project.to_dict(),
                    filepath=cache_path, create_backup=False
                )
        except Exception as e:
            logger.warning(f"No se pudo crear la caché: {e}")
    
    def verify_audio_layers(self) -> bool:
        logger.info("Verificando capas de audio...")
        status = True
        for name, comp in [("AudioEngine", self._audio_engine),
                           ("MixerEngine", self._mixer_engine),
                           ("InstrumentRack", self._instrument_rack),
                           ("AudioManager", self._audio_manager)]:
            if comp:
                logger.info(f"  - {name}: OK")
            else:
                logger.error(f"  - {name}: FALLIDO")
                status = False
        return status
    
    def load_project(self, path: Path) -> bool:
        try:
            project = self._project_manager.load(str(path))
            if project:
                self._current_project = project
                self._is_modified = False
                self.project_loaded.emit(project)
                if self._event_bus:
                    self._event_bus.publish(ProjectEvents.loaded(project.name, project.id))
                return True
        except Exception as e:
            logger.error(f"Error cargando proyecto: {e}")
            self.error_occurred.emit(str(e))
        return False
    
    def save_project(self, path: Optional[Path] = None) -> bool:
        if not self._current_project:
            return False
        try:
            save_path = path or self._current_project.file_path
            if save_path:
                self._project_manager.save(self._current_project, str(save_path))
                self._is_modified = False
                self.project_saved.emit(str(save_path))
                if self._event_bus:
                    self._event_bus.publish(ProjectEvents.saved(
                        self._current_project.id, str(save_path)
                    ))
                return True
        except Exception as e:
            logger.error(f"Error guardando proyecto: {e}")
            self.error_occurred.emit(str(e))
        return False
    
    @property
    def current_project(self) -> Optional[Project]:
        return self._current_project
    
    @property
    def is_modified(self) -> bool:
        return self._is_modified
    
    def set_modified(self, modified: bool = True) -> None:
        self._is_modified = modified
        self.modification_changed.emit(modified)
        if modified and self._event_bus and self._current_project:
            self._event_bus.publish(ProjectEvents.modified(self._current_project.id))
    
    # === Transport ===
    
    def play(self) -> None:
        if self._transport_service:
            self._transport_service.play()
        if self._audio_manager:
            self._audio_manager.start_sequencer()
    
    def pause(self) -> None:
        if self._transport_service:
            self._transport_service.pause()
        if self._audio_manager:
            self._audio_manager.pause_sequencer()
    
    def stop(self) -> None:
        if self._transport_service:
            self._transport_service.stop()
        if self._audio_manager:
            self._audio_manager.stop_sequencer()
    
    def seek(self, tick: int) -> None:
        if self._transport_service:
            self._transport_service.seek(tick)
    
    def set_bpm(self, bpm: int) -> None:
        if self._transport_service:
            self._transport_service.set_bpm(bpm)
    
    @property
    def bpm(self) -> int:
        return self._transport_service.bpm if self._transport_service else 120
    
    @property
    def position(self) -> int:
        return self._transport_service.position if self._transport_service else 0
    
    @property
    def is_playing(self) -> bool:
        if self._audio_manager:
            return self._audio_manager.is_playing
        return False
    
    def toggle_metronome(self) -> bool:
        return self._audio_manager.toggle_metronome() if self._audio_manager else False
    
    def toggle_count_in(self) -> bool:
        return self._audio_manager.toggle_count_in() if self._audio_manager else False
    
    def toggle_loop(self) -> bool:
        return self._audio_manager.toggle_loop() if self._audio_manager else False
    
    @property
    def metronome_enabled(self) -> bool:
        return self._audio_manager.metronome_enabled if self._audio_manager else False
    
    @property
    def count_in_enabled(self) -> bool:
        return self._audio_manager.count_in_enabled if self._audio_manager else False
    
    @property
    def loop_enabled(self) -> bool:
        return self._audio_manager.loop_enabled if self._audio_manager else False
    
    def start_recording(self) -> bool:
        if self._transport_handler:
            return self._transport_handler.start_recording()
        return False
    
    def stop_recording(self) -> bool:
        if self._transport_handler:
            return self._transport_handler.stop_recording()
        return False
    
    @property
    def is_recording(self) -> bool:
        if self._transport_handler:
            return self._transport_handler.state == TransportState.RECORDING
        return False

    @property
    def recording_handler(self) -> Optional[RecordingHandler]:
        return self._recording_handler

    @property
    def midi_recording_handler(self) -> Optional[MIDIRecordingHandler]:
        return self._midi_recording_handler

    def arm_track(self, track_id: str, armed: bool = True):
        if self._recording_handler:
            self._recording_handler.arm_track(track_id, armed)

    def is_track_armed(self, track_id: str) -> bool:
        if self._recording_handler:
            return self._recording_handler.is_armed(track_id)
        return False

    def play_note(self, note: int, velocity: int = 100, channel: int = 0) -> None:
        if self._instrument_rack:
            synth = self._instrument_rack.get_instrument(0)
            if synth:
                synth.note_on(note, velocity)
        if self._audio_manager:
            self._audio_manager.note_on(note, velocity)
    
    def stop_note(self, note: int, channel: int = 0) -> None:
        if self._instrument_rack:
            synth = self._instrument_rack.get_instrument(0)
            if synth:
                synth.note_off(note)
        if self._audio_manager:
            self._audio_manager.note_off(note)
    
    # === Tracks ===
    
    def add_track(self, name: str = "New Track") -> Track:
        if not self._current_project:
            return None
        track = self._current_project.add_track(name)
        if self._track_handler:
            self._track_handler._tracks_cache[track.id] = track
        track_count = len(self._current_project.get_tracks()) - 1
        track_id = f"track_{track_count}"
        waveforms = ["square", "triangle", "noise", "sawtooth"]
        if self._audio_manager:
            self._audio_manager.register_track(
                track_id=track_id, note=60 + track_count * 5,
                waveform=waveforms[track_count % len(waveforms)]
            )
            self._audio_manager.init_track_steps(track_count)
        self.set_modified()
        self.track_added.emit(track)
        if self._event_bus:
            self._event_bus.publish(TrackEvents.added(track.id, track.name))
        return track
    
    def remove_track(self, track_id: str) -> bool:
        if self._current_project:
            self._current_project.remove_track(track_id)
            if self._audio_manager:
                self._audio_manager.unregister_track(track_id)
            self.set_modified()
            self.track_removed.emit(track_id)
            if self._event_bus:
                self._event_bus.publish(TrackEvents.removed(track_id))
            return True
        return False
    
    def set_track_volume(self, track_index: int, volume: float) -> None:
        track_id = f"track_{track_index}"
        if self._audio_manager:
            self._audio_manager.set_track_volume(track_id, volume)
        if self._current_project:
            tracks = self._current_project.get_tracks()
            if track_index < len(tracks):
                tracks[track_index].volume = volume
    
    def set_track_mute(self, track_index: int, muted: bool) -> None:
        track_id = f"track_{track_index}"
        if self._audio_manager:
            self._audio_manager.set_track_mute(track_id, muted)
    
    def set_track_pan(self, track_index: int, pan: float) -> None:
        track_id = f"track_{track_index}"
        if self._audio_manager:
            self._audio_manager.set_track_pan(track_id, pan)
    
    def set_track_note(self, track_index: int, note: int) -> None:
        track_id = f"track_{track_index}"
        if self._audio_manager:
            self._audio_manager.set_track_note(track_id, note)
    
    def update_scheduler_notes(self) -> None:
        logger.debug("update_scheduler_notes called")
    
    def set_pattern_length(self, length: int) -> None:
        if self._audio_manager:
            self._audio_manager.set_num_steps(length)
    
    def set_synth_parameter(self, synth_name_or_track: str, param_name: str, value: float) -> None:
        if self._audio_router:
            self._audio_router.set_synth_parameter(synth_name_or_track, param_name, value)
        if self._audio_manager:
            if param_name == "waveform":
                self._audio_manager.set_track_note(synth_name_or_track, int(value))
            elif param_name == "volume":
                self._audio_manager.set_track_volume(synth_name_or_track, value)
    
    def get_audio_levels(self) -> tuple:
        if self._audio_manager:
            return self._audio_manager.get_audio_levels()
        return (0.0, 0.0)

    def get_waveform_data(self, num_samples: int = 256) -> tuple:
        if self._audio_manager:
            return self._audio_manager.get_waveform_data(num_samples)
        return ([0.0] * num_samples, [0.0] * num_samples)
    
    def get_track_levels(self) -> Dict[str, tuple]:
        if self._mixer_engine:
            return self._mixer_engine.get_meter_levels()
        return {}

    def set_step_active(self, track_index: int, step: int, active: bool) -> None:
        if self._audio_manager:
            self._audio_manager.set_step_active(track_index, step, active)
    
    def preview_audio_file(self, path: str) -> bool:
        return False
    
    def export_wav(self, file_path: str, duration: float = 8.0) -> bool:
        try:
            sample_rate = self._sample_rate
            num_samples = int(sample_rate * duration)
            synth = PolyphonicSynth(sample_rate=sample_rate)
            audio_data = np.zeros(num_samples, dtype=np.float32)
            bpm = self._transport_service.bpm if self._transport_service else 120
            step_samples = int(sample_rate * 60.0 / bpm / 4.0)

            pos = 0
            step = 0
            step_states = self._audio_manager.get_step_states() if self._audio_manager else {}
            track_synths = self._audio_manager.get_all_track_synths() if self._audio_manager else {}
            while pos < num_samples:
                for track_idx, steps in step_states.items():
                    n_steps = len(steps)
                    if n_steps > 0 and steps[step % n_steps]:
                        track_data = track_synths.get(f"track_{track_idx}", {})
                        synth.note_on(track_data.get("note", 60), 100)
                chunk_size = min(step_samples, num_samples - pos)
                chunk = synth.process(chunk_size)
                audio_data[pos:pos + chunk_size] = chunk[:chunk_size]
                for track_idx in step_states:
                    track_data = track_synths.get(f"track_{track_idx}", {})
                    synth.note_off(track_data.get("note", 60))
                pos += chunk_size
                step += 1

            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                audio_data = audio_data * (0.9 / max_val)
            audio_int16 = (audio_data * 32767).astype(np.int16)
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(np.column_stack([audio_int16, audio_int16]).tobytes())
            logger.info(f"WAV exportado: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error exportando WAV: {e}")
            self.error_occurred.emit(f"Export WAV failed: {e}")
            return False
    
    def export_midi(self, file_path: str) -> bool:
        try:
            import mido
            bpm = self._transport_service.bpm if self._transport_service else 120
            mid = mido.MidiFile()
            mt = mido.MidiTrack()
            mid.tracks.append(mt)
            mt.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm), time=0))
            ticks_per_step = 120
            step_states = self._audio_manager.get_step_states() if self._audio_manager else {}
            track_synths = self._audio_manager.get_all_track_synths() if self._audio_manager else {}
            for track_idx, steps in step_states.items():
                note = track_synths.get(f"track_{track_idx}", {}).get("note", 60)
                for si, active in enumerate(steps):
                    if active:
                        t = si * ticks_per_step
                        mt.append(mido.Message('note_on', note=note, velocity=100, time=t))
                        mt.append(mido.Message('note_off', note=note, velocity=0, time=ticks_per_step // 2))
            mid.save(file_path)
            logger.info(f"MIDI exportado: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error exportando MIDI: {e}")
            self.error_occurred.emit(f"Export MIDI failed: {e}")
            return False
    
    # === Propiedades de Handlers (para PresentationModel) ===
    
    @property
    def track_handler(self) -> Optional[TrackHandler]:
        """Obtener handler de pistas."""
        return self._track_handler
    
    @property
    def note_handler(self) -> Optional[NoteHandler]:
        """Obtener handler de notas."""
        return self._note_handler
    
    @property
    def automation_handler(self) -> Optional[AutomationHandler]:
        """Obtener handler de automatización."""
        return self._automation_handler
    
    @property
    def project_handler(self) -> Optional[ProjectHandler]:
        """Obtener handler de proyecto."""
        return self._project_handler
    
    @property
    def transport_handler(self) -> Optional[TransportHandler]:
        """Obtener handler de transporte."""
        return self._transport_handler
        
    @property
    def arrangement_handler(self) -> Optional[ArrangementHandler]:
        """Obtener handler de arreglo."""
        return self._arrangement_handler
    
    # === Instrumentos ===
    
    def set_instrument_preset(self, slot: int, preset_id: str) -> bool:
        """Establecer preset en slot."""
        preset = self._preset_manager.get_preset(preset_id)
        if preset:
            synth = InstrumentFactory.create_synth(
                preset.data.get("waveform", "square"),
                self._sample_rate
            )
            # Aplicar parámetros del preset
            # (env, volumen, etc.)
            
            self._instrument_rack.set_instrument(
                slot,
                synth,
                name=preset.name
            )
            return True
        return False
    
    def set_hardware_mode(self, chip_type: ChipType) -> None:
        """Cambiar modo de emulación de hardware."""
        if self._hardware_emulation:
            self._hardware_emulation.set_active_chip(chip_type)
    
    # === Undo/Redo ===
    
    def undo(self) -> bool:
        """Deshacer."""
        if self._command_history:
            result = self._command_history.undo()
            if result:
                self.set_modified()
            return result
        return False
    
    def redo(self) -> bool:
        """Rehacer."""
        if self._command_history:
            result = self._command_history.redo()
            if result:
                self.set_modified()
            return result
        return False
    
    @property
    def can_undo(self) -> bool:
        """Verificar si puede deshacer."""
        return self._command_history.can_undo if self._command_history else False
    
    @property
    def can_redo(self) -> bool:
        """Verificar si puede rehacer."""
        return self._command_history.can_redo if self._command_history else False
    
    # === Recuperación ===
    
    def check_recovery(self) -> bool:
        """Verificar si hay recuperación pendiente."""
        if not self._current_project or not self._recovery_system:
            return False
        
        backup = self._recovery_system.check_for_recovery(
            self._current_project.file_path
        )
        
        if backup:
            # recovery_available signal debería emitirse
            logger.info(f"Recuperación disponible: {backup.path}")
            return True
        
        return False
    
    # === Audio Stream ===

    def start_audio_stream(self) -> None:
        """Iniciar el stream de audio en tiempo real.

        Se llama de forma diferida desde main() después de que MainWindow
        esté completamente creada, para evitar buffer underruns durante
        la inicialización pesada de la UI.
        """
        if self._audio_manager:
            logger.info("Starting audio stream (deferred after UI init)...")
            self._audio_manager.start_stream()
        else:
            logger.warning("Cannot start audio stream: AudioManager not available")

    # === Cleanup ===
    
    def shutdown(self) -> None:
        """Apagar aplicación."""
        logger.info("Apagando AppCore...")
        
        # Detener audio engine y stream
        if self._audio_engine:
            self._audio_engine.shutdown()
        
        # Guardar recovery point
        if self._current_project and self._is_modified and self._recovery_system:
            try:
                self._recovery_system.save_recovery_point(
                    self._current_project.file_path
                )
            except Exception:
                pass
        
        # Limpiar performance monitor
        if self._performance_monitor:
            self._performance_monitor.stop_monitoring()
        
        logger.info("AppCore apagado")


# Instancia global
_app_core: Optional[AppCore] = None


def get_app_core() -> AppCore:
    """Obtener instancia global del núcleo."""
    global _app_core
    if _app_core is None:
        from src.application.app_core_builder import AppCoreBuilder
        _app_core = AppCoreBuilder().build()
    return _app_core


def initialize_app(
    sample_rate: int = 44100,
    buffer_size: int = 512
) -> AppCore:
    """Inicializar aplicación completa usando AppCoreBuilder."""
    from src.application.app_core_builder import AppCoreBuilder
    builder = AppCoreBuilder()
    builder.with_sample_rate(sample_rate)
    builder.with_buffer_size(buffer_size)
    app = builder.build()
    app.initialize()
    return app
