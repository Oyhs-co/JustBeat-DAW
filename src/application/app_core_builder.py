"""AppCoreBuilder - Builder para AppCore con inyección de dependencias.

Proporciona una interfaz fluida para construir AppCore
con dependencias personalizadas o valores por defecto.
"""

from typing import Optional
import logging

from src.domain.events.event_bus import EventBus


logger = logging.getLogger(__name__)

from src.application.handlers.project_handler import ProjectHandler
from src.application.handlers.transport_handler import TransportHandler
from src.application.handlers.track_handler import TrackHandler
from src.application.handlers.note_handler import NoteHandler
from src.application.handlers.automation_handler import AutomationHandler
from src.application.handlers.arrangement_handler import ArrangementHandler
from src.application.commands.command_history import CommandHistory
from src.application.services.transport_service import TransportService

from src.application.ports.audio_port import (
    AudioManagerProtocol, AudioEngineProtocol,
    MixerEngineProtocol, AudioRouterProtocol,
    InstrumentRackProtocol, PresetManagerProtocol,
    PerformanceMonitorProtocol, HardwareEmulationProtocol,
)
from src.application.ports.persistence_port import (
    ProjectManagerProtocol, RecoverySystemProtocol,
)

from src.infrastructure.midi.midi_handler import MIDIHandler

from src.application.app_core import AppCore


class AppCoreBuilder:
    """Builder para construir AppCore con DI.

    Uso:
        app = (AppCoreBuilder()
               .with_sample_rate(48000)
               .with_buffer_size(256)
               .build())
        app.initialize()
    """

    def __init__(self):
        self._sample_rate: int = 44100
        self._buffer_size: int = 512
        self._event_bus: Optional[EventBus] = None
        self._transport_service: Optional[TransportService] = None
        self._command_history: Optional[CommandHistory] = None
        self._project_handler: Optional[ProjectHandler] = None
        self._transport_handler: Optional[TransportHandler] = None
        self._track_handler: Optional[TrackHandler] = None
        self._note_handler: Optional[NoteHandler] = None
        self._automation_handler: Optional[AutomationHandler] = None
        self._arrangement_handler: Optional[ArrangementHandler] = None
        self._audio_engine: Optional[AudioEngineProtocol] = None
        self._mixer_engine: Optional[MixerEngineProtocol] = None
        self._audio_manager: Optional[AudioManagerProtocol] = None
        self._audio_router: Optional[AudioRouterProtocol] = None
        self._instrument_rack: Optional[InstrumentRackProtocol] = None
        self._preset_manager: Optional[PresetManagerProtocol] = None
        self._performance_monitor: Optional[PerformanceMonitorProtocol] = None
        self._hardware_emulation: Optional[HardwareEmulationProtocol] = None
        self._midi_handler: Optional[MIDIHandler] = None
        self._project_manager: Optional[ProjectManagerProtocol] = None
        self._recovery_system: Optional[RecoverySystemProtocol] = None

    def with_sample_rate(self, rate: int) -> "AppCoreBuilder":
        self._sample_rate = rate
        return self

    def with_buffer_size(self, size: int) -> "AppCoreBuilder":
        self._buffer_size = size
        return self

    def with_event_bus(self, bus: EventBus) -> "AppCoreBuilder":
        self._event_bus = bus
        return self

    def with_transport_service(
        self, service: TransportService
    ) -> "AppCoreBuilder":
        self._transport_service = service
        return self

    def with_command_history(
        self, history: CommandHistory
    ) -> "AppCoreBuilder":
        self._command_history = history
        return self

    def with_project_handler(
        self, handler: ProjectHandler
    ) -> "AppCoreBuilder":
        self._project_handler = handler
        return self

    def with_transport_handler(
        self, handler: TransportHandler
    ) -> "AppCoreBuilder":
        self._transport_handler = handler
        return self

    def with_track_handler(
        self, handler: TrackHandler
    ) -> "AppCoreBuilder":
        self._track_handler = handler
        return self

    def with_note_handler(
        self, handler: NoteHandler
    ) -> "AppCoreBuilder":
        self._note_handler = handler
        return self

    def with_automation_handler(
        self, handler: AutomationHandler
    ) -> "AppCoreBuilder":
        self._automation_handler = handler
        return self

    def with_arrangement_handler(
        self, handler: ArrangementHandler
    ) -> "AppCoreBuilder":
        self._arrangement_handler = handler
        return self

    def with_audio_engine(
        self, engine: AudioEngineProtocol
    ) -> "AppCoreBuilder":
        self._audio_engine = engine
        return self

    def with_mixer_engine(
        self, mixer: MixerEngineProtocol
    ) -> "AppCoreBuilder":
        self._mixer_engine = mixer
        return self

    def with_audio_manager(
        self, manager: AudioManagerProtocol
    ) -> "AppCoreBuilder":
        self._audio_manager = manager
        return self

    def with_audio_router(
        self, router: AudioRouterProtocol
    ) -> "AppCoreBuilder":
        self._audio_router = router
        return self

    def with_instrument_rack(
        self, rack: InstrumentRackProtocol
    ) -> "AppCoreBuilder":
        self._instrument_rack = rack
        return self

    def with_preset_manager(
        self, manager: PresetManagerProtocol
    ) -> "AppCoreBuilder":
        self._preset_manager = manager
        return self

    def with_performance_monitor(
        self, monitor: PerformanceMonitorProtocol
    ) -> "AppCoreBuilder":
        self._performance_monitor = monitor
        return self

    def with_hardware_emulation(
        self, hw: HardwareEmulationProtocol
    ) -> "AppCoreBuilder":
        self._hardware_emulation = hw
        return self

    def with_midi_handler(
        self, handler: MIDIHandler
    ) -> "AppCoreBuilder":
        self._midi_handler = handler
        return self

    def with_project_manager(
        self, manager: ProjectManagerProtocol
    ) -> "AppCoreBuilder":
        self._project_manager = manager
        return self

    def with_recovery_system(
        self, system: RecoverySystemProtocol
    ) -> "AppCoreBuilder":
        self._recovery_system = system
        return self

    def build(self) -> AppCore:
        """Construir AppCore con las dependencias configuradas.

        Las dependencias no configuradas se crearán con valores
        por defecto cuando se llame a initialize().

        Returns:
            AppCore configurado (aún no inicializado)
        """
        return AppCore(
            sample_rate=self._sample_rate,
            buffer_size=self._buffer_size,
            event_bus=self._event_bus,
            transport_service=self._transport_service,
            command_history=self._command_history,
            project_handler=self._project_handler,
            transport_handler=self._transport_handler,
            track_handler=self._track_handler,
            note_handler=self._note_handler,
            automation_handler=self._automation_handler,
            arrangement_handler=self._arrangement_handler,
            audio_engine=self._audio_engine,
            mixer_engine=self._mixer_engine,
            audio_manager=self._audio_manager,
            audio_router=self._audio_router,
            instrument_rack=self._instrument_rack,
            preset_manager=self._preset_manager,
            performance_monitor=self._performance_monitor,
            hardware_emulation=self._hardware_emulation,
            midi_handler=self._midi_handler,
            project_manager=self._project_manager,
            recovery_system=self._recovery_system,
        )
