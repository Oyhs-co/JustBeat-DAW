# JustBeat-DAW Architecture

> **Last updated**: 2026-06-10
> **Python**: 3.11+ | **GUI**: PySide6 | **Architecture**: Hexagonal (Ports & Adapters) + DDD

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Principles](#2-architecture-principles)
3. [Layer Structure](#3-layer-structure)
4. [Contract & Interface Design](#4-contract--interface-design)
5. [Configuration System](#5-configuration-system)
6. [Frontend Architecture](#6-frontend-architecture)
7. [Audio Pipeline](#7-audio-pipeline)
8. [MIDI Pipeline](#8-midi-pipeline)
9. [Persistence Layer](#9-persistence-layer)
10. [Plugin System](#10-plugin-system)
11. [Cross-Platform Strategy](#11-cross-platform-strategy)
12. [Refactoring Tracker](#12-refactoring-tracker)

---

## 1. Project Overview

JustBeat-DAW is a digital audio workstation built with Python and PySide6. It follows a strict hexagonal (ports & adapters) architecture combined with Domain-Driven Design patterns.

### Key Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| GUI | PySide6 (Qt for Python) ^6.11.0 | Cross-platform UI framework |
| Audio I/O | sounddevice ^0.5.5 | Real-time audio via PortAudio |
| Audio Processing | numpy ^2.4.4 | Buffer-level DSP |
| MIDI | mido ^1.3.0 + python-rtmidi ^1.2.0 | MIDI file I/O + hardware |
| Serialization | Pydantic ^2.0.0 | Data validation & settings |
| Build | Poetry | Dependency & packaging |
| Testing | pytest + pytest-cov | Unit tests with coverage |
| Quality | black, isort, flake8, mypy | Pre-commit enforced |

### Build & Run

```bash
poetry install
poetry run justbeat        # Run the application
poetry run pytest          # Run tests
poetry run mypy src/       # Type checking
```

---

## 2. Architecture Principles

### 2.1 Hexagonal Architecture (Ports & Adapters)

```
                     ┌─────────────┐
                     │ Presentation │
                     │   (Views)    │
                     └──────┬──────┘
                            │ depends on
                     ┌──────▼──────┐
                     │ Application │
                     │  (Handlers)  │
                     └──────┬──────┘
                            │ depends on
                     ┌──────▼──────┐
                     │   Domain    │
                     │ (Entities)  │
                     └──────┬──────┘
                            │ implements ports
                     ┌──────▼──────┐
                     │Infrastructure│
                     │ (Adaptadores) │
                     └─────────────┘
```

### 2.2 Dependency Rule

- **Domain** depends on NOTHING (pure Python)
- **Application** depends ONLY on Domain
- **Infrastructure** depends on Domain (implements ports)
- **Presentation** depends on Application (via PresentationModel)

### 2.3 Key Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| Ports & Adapters | `domain/interfaces/` → `infrastructure/` | Decouple core from IO |
| Command Pattern | `application/commands/` | Undo/Redo support |
| Event Bus | `domain/events/` | Decoupled communication |
| Builder | `application/app_core_builder.py` | DI composition root |
| Presentation Model | `presentation/models/` | UI state facade |
| Protocol (structural typing) | `application/ports/` | Contract definitions |

---

## 3. Layer Structure

### 3.1 Domain Layer (`src/domain/`)

The innermost layer with zero external dependencies.

```
domain/
  entities/           # Business entities (Project, Track, Note, Pattern, Clip, etc.)
    automation/       # Automation subsystem (points, curves, tracks)
  events/             # Domain events + EventBus
  interfaces/         # [DEPRECATED] Old ABC-based ports — replaced by app protocols
```

**Key entities:**
- `Project` — Aggregate root, contains tracks, arrangement, tempo map
- `Track` — Individual track with patterns, clips, automation
- `Pattern` — Step sequencer pattern (16 steps)
- `Note` — MIDI note with pitch, velocity, timing
- `Clip` — Audio/MIDI clip in arrangement
- `Arrangement` — Timeline of clips across tracks
- `TempoMap` — Tempo & time signature changes
- `Timeline` — Global timeline state

### 3.2 Application Layer (`src/application/`)

Orchestration layer containing all use-case logic.

```
application/
  app_core.py           # Central controller (QObject)
  app_core_builder.py   # DI composition builder
  ports/                # Protocol definitions (contracts)
    audio_port.py        # AudioEngineProtocol, MixerEngineProtocol, etc.
    persistence_port.py  # ProjectManagerProtocol, RecoverySystemProtocol
  handlers/             # Business logic handlers
    project_handler.py
    transport_handler.py
    track_handler.py
    note_handler.py
    automation_handler.py
    arrangement_handler.py
    recording_handler.py
    midi_recording_handler.py
    state_handler.py
  commands/             # Command pattern for undo/redo
    command_history.py
    add_note.py
  services/             # [DEPRECATED] Legacy services — being removed
```

### 3.3 Infrastructure Layer (`src/infrastructure/`)

Contains all IO adapters implementing application ports.

```
infrastructure/
  audio/                # Audio subsystem
    audio_manager.py     # Thin orchestrator (sequencer, tracks, metronome, IAudioService)
    device_manager.py    # Device scanning & ASIO selection
    stream_manager.py    # Stream lifecycle & underrun recovery
    audio_router.py      # Audio routing matrix
    mixer_engine.py      # Mixing engine (reduced, ~560 lines)
    mixer_channel.py     # ChannelState / Send / ChannelStrip dataclasses
    mixer_bus.py         # Bus dataclass
    polyphonic_synth.py  # Synth engine (reduced, ~450 lines)
    oscillator.py        # Waveform/NoiseType/EnvStage enums + generate_waveform()
    voice.py             # Voice / ADSREnvelope dataclasses
    multi_oscillator_synth.py  # OscillatorConfig + MultiOscillatorSynth
    instrument_rack.py   # Instrument management
    effect_factory.py    # EffectFactory (registers 10 effects)
    performance_monitor.py
    hardware_emulation.py
    player.py
    recorder.py
    offline_renderer.py
    preset_manager.py
    effects/             # DSP effects (delay, distortion, reverb, chorus, compressor, etc.)
    oscillators/         # Waveform generators
  midi/                  # MIDI subsystem
    midi_handler.py      # MIDI input/output
    midi_recorder.py     # MIDI recording
  export/                # Audio file export
    wav_exporter.py
    flac_exporter.py
    mp3_exporter.py
    ogg_exporter.py
    midi_exporter.py
  persistence/           # Project save/load
    project_manager.py
    project_repository.py
    project_recovery.py
  plugins/               # Plugin system
    host.py
    plugin_manager.py
```

### 3.4 Presentation Layer (`src/presentation/`)

All UI code following MVP pattern.

```
presentation/
  views/                # Pure QWidget views (no business logic)
    main_window.py
    transport_bar.py
    sequencer.py
    piano_roll.py
    mixer.py
    arrange_view.py
    browser.py
    synth_panel.py
    ...
  controllers/          # Signal wiring & user action handling
    playback_controller.py
    export_controller.py
    keyboard_shortcuts.py
    menu_bar.py
    dock_manager.py
  models/               # Qt Models for view data
    presentation_model.py
  theme/                # Styling system
    theme.py
    pro_theme.py
    theme_manager.py
    style_manager.py
    animations.py
    icons.py
    *.qss
```

---

## 4. Contract & Interface Design

### 4.1 Protocol-Based Ports (Standard)

All contracts use `typing.Protocol` for structural typing, defined in `application/ports/`.

```python
# application/ports/audio_port.py
class AudioEngineProtocol(Protocol):
    def play(self) -> None: ...
    def stop(self) -> None: ...
    def process_buffer(self, frames: int) -> np.ndarray: ...
```

**Why Protocols over ABCs:**
- No inheritance coupling — adapters just need matching signatures
- Easier testing — mock any protocol with any compatible object
- More Pythonic — "duck typing" with static verification
- Single source of truth — no parallel ABC + Protocol hierarchies

### 4.2 Current Ports

| Port Protocol | Location | Implemented By |
|---|---|---|
| `AudioEngineProtocol` | `ports/audio_port.py` | `AudioManager` |
| `MixerEngineProtocol` | `ports/audio_port.py` | `MixerEngine` |
| `AudioRouterProtocol` | `ports/audio_port.py` | `AudioRouter` |
| `InstrumentRackProtocol` | `ports/audio_port.py` | `InstrumentRack` |
| `ProjectManagerProtocol` | `ports/persistence_port.py` | `ProjectManager` |
| `RecoverySystemProtocol` | `ports/persistence_port.py` | `ProjectRecoverySystem` |

### 4.3 Transport State (Single Source)

Defined once in `domain/`:

```python
# domain/transport_state.py  (shared enum)
class TransportState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    RECORDING = "recording"
```

---

## 5. Configuration System

### 5.1 Settings Structure

```
config/
  settings.py         # Settings dataclasses
  config_manager.py   # TOML persistence (load/save/watch)
```

Settings are organized in a nested structure:

```
Settings
  ├── AudioSettings      # sample_rate, buffer_size, bit_depth, device
  ├── MIDISettings       # devices, clock sync, quantize
  ├── ProjectSettings    # default_bpm, time_signature, auto_save
  ├── UISettings         # theme, window_size, layout
  └── PluginSettings     # directories, sandbox mode
```

### 5.2 Persistence (TOML)

Config is stored in platform-appropriate locations:
- **Linux**: `~/.config/justbeat/config.toml`
- **Windows**: `%APPDATA%/JustBeat/config.toml`

Format example:
```toml
[audio]
sample_rate = 44100
buffer_size = 1024
device = "default"

[project]
default_bpm = 120
auto_save = true

[ui]
theme = "obsidian"
window_width = 1600
window_height = 900
```

### 5.3 Environment Overrides

Environment variables override TOML values at runtime:
- `JUSTBEAT_SAMPLE_RATE`
- `JUSTBEAT_BUFFER_SIZE`
- `JUSTBEAT_DEFAULT_BPM`
- `JUSTBEAT_DEBUG`
- `JUSTBEAT_VERBOSE_AUDIO`

---

## 6. Frontend Architecture

### 6.1 Architecture: View → Controller → Model

```
User Input
    │
    ▼
┌──────────┐   Signals    ┌────────────┐   calls    ┌──────────────┐
│  Views   │─────────────▶│Controllers │───────────▶│Presentation  │
│(Widgets) │              │ (Actions)  │            │   Model      │
└──────────┘              └────────────┘            └──────┬───────┘
                                                           │ signals
                                                           ▼
                                                     ┌──────────┐
                                                     │ AppCore  │
                                                     │(QObject) │
                                                     └────┬─────┘
                                                          │ calls
                                                     ┌────▼─────┐
                                                     │ Handlers │
                                                     └──────────┘
```

### 6.2 Key Design Rules

1. **Views never access AppCore directly** — no `get_app_core()`
2. **Controllers wire signals** — they connect view signals to model/AppCore slots
3. **PresentationModel** is the single facade for all UI state
4. **Qt Model/View** used for data-heavy widgets (sequencer grid, piano roll, mixer)
5. **Theme system** provides consistent styling via QSS + runtime switching

### 6.3 Widget Hierarchy

```
MainWindow
  ├── MenuBar (MenuBarManager)
  ├── TransportBar
  ├── Workspace (QDockWidget-based)
  │   ├── ArrangeView (timeline)
  │   ├── Mixer (channel strips)
  │   ├── Browser (file browser)
  │   ├── PianoRoll
  │   ├── Sequencer
  │   ├── SynthPanel
  │   └── AutomationLane
  ├── StatusBar
  └── ToastManager (overlay notifications)
```

---

## 7. Audio Pipeline

### 7.1 Architecture (Unified)

The audio system is a **single unified pipeline** managed by `AudioManager`:

```
sounddevice callback
    │
    ▼
┌──────────────────────────────────────────────────┐
│                 AudioManager                     │
│  ┌──────────────┐  ┌──────────────┐             │
│  │ DeviceManager │  │ StreamManager│             │
│  │(device scan/  │  │(stream life- │             │
│  │ ASIO select)  │  │ cycle, under-│             │
│  └──────────────┘  │ run recovery)│             │
│                    └──────────────┘             │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐     │
│  │ Scheduler │  │  Engine  │  │IAudioSvc │     │
│  │(step seq) │  │Processor │  │(play/stop │     │
│  └──────────┘  └─────┬─────┘  │ seek/pos) │     │
│                      │        └───────────┘     │
└──────────────────────┼──────────────────────────┘
                       │
              ┌────────▼────────┐
              │   MixerEngine   │
              │  (sum bus + FX) │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │   AudioRouter   │
              │ (output matrix) │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  Output Device  │
              └─────────────────┘
```

### 7.2 Processing Chain (per callback)

1. `AudioManager.process_buffer(frames)` is called from sounddevice callback
2. Schedule step sequencer events (if playing)
3. Process instruments (synths) → generate buffers
4. Process audio clips → read from disk buffers
5. Route through `MixerEngine` (volume, pan, FX sends)
6. Route through `AudioRouter` (output mapping)
7. Return mixed buffer to sounddevice

### 7.3 Audio Files & Folders

- **Recordings**: `{project_dir}/recordings/`
- **Exports**: User-selected directory
- **Cache**: `{project_dir}/cache/` (processed audio files)

---

## 8. MIDI Pipeline

```
MIDI Input (hardware)
    │
    ▼
┌────────────────┐
│  MIDIHandler   │
│  (python-rtmidi)│
└───┬────────────┘
    │ events
    ▼
┌────────────────┐
│  EventBus      │
│  (domain events)│
└───┬────────────┘
    │ routed to
    ▼
┌──────────────────┐  ┌───────────────────┐
│ RecordingHandler │  │ VirtualKeyboard   │
│ (capture MIDI)   │  │ (on-screen keys)  │
└──────────────────┘  └───────────────────┘
```

---

## 9. Persistence Layer

### 9.1 Project Files

Projects are saved as JSON files with the `.justbeat` extension.

```
Project/
  project.justbeat        # Main project file (JSON)
  recordings/             # Audio recordings
    recording_001.wav
    ...
  cache/                  # Processed audio cache
    track_1_processed.wav
    ...
  exports/                # Exported files
    mixdown.wav
    ...
```

### 9.2 Save/Load Flow

```
User: Ctrl+S
  │
  ▼
PresentationModel.save_project()
  │
  ▼
AppCore.handle_save()
  │
  ▼
ProjectHandler.save_project(project, path)
  │
  ▼
ProjectManagerProtocol.save(project, path)
  │
  ▼
ProjectManager (JSON serialization → file)
```

### 9.3 Auto-Recovery

- Auto-save every N minutes (configurable)
- Recovery file stored in `~/.justbeat/recovery/`
- On crash, recovery dialog offers to restore on next launch

---

## 10. Plugin System

### 10.1 Plugin Types

| Type | Interface | Examples |
|------|-----------|---------|
| Instrument | Produces audio | PolyphonicSynth, external VSTi |
| Effect | Processes audio | Reverb, Delay, Chorus, Compressor |
| Utility | MIDI/utils | Arpeggiator, Chord generator |

### 10.2 Built-in vs External

- **Built-in**: Native Python implementations (PolyphonicSynth, effects)
- **External**: VST3 plugins loaded via host process (future)

### 10.3 Plugin Discovery

```
PluginManager
  ├── Built-in → already registered
  └── User plugins → scanned from configured directories
```

---

## 11. Cross-Platform Strategy

### 11.1 Platform Support

| Feature | Windows | Linux | macOS (future) |
|---------|---------|-------|----------------|
| GUI (PySide6) | ✅ | ✅ | ✅ |
| Audio (sounddevice) | ✅ (WASAPI) | ✅ (ALSA/Pulse) | - |
| MIDI (rtmidi) | ✅ (Windows MIDI) | ✅ (ALSA) | - |
| File paths (pathlib) | ✅ | ✅ | ✅ |
| App data dirs (platformdirs) | ✅ | ✅ | - |

### 11.2 Platform-Specific Concerns

- **Audio device names** differ per platform — use description matching, not name
- **MIDI API** selected automatically by `python-rtmidi`
- **File paths** always use `pathlib.Path` — never string concatenation
- **Process priority** — Windows uses `SetPriorityClass`, Linux uses `nice`
- **High-DPI** — PySide6 handles via `QtCore.Qt.HighDpiScaleFactorRoundingPolicy`

---

## 12. Refactoring Tracker

### 12.1 Phase Status

| Phase | Description | Status | Date |
|-------|-----------|--------|------|
| 0 | Architecture document | ✅ DONE | 2026-06-10 |
| 1 | Legacy code removal | ✅ DONE | 2026-06-10 |
| 2 | Audio pipeline unification | ✅ DONE | 2026-06-10 |
| 3 | Contract unification (Protocols) | ✅ DONE | 2026-06-10 |
| 4 | Frontend recreation | ✅ DONE | 2026-06-10 |
| 5 | TOML config persistence | ✅ DONE | 2026-06-10 |
| 6 | Cross-platform hardening | ✅ DONE | 2026-06-10 |
| 7 | Modularization (large files) | ✅ DONE | 2026-06-10 |
| 7b | Split audio_manager.py → device_manager.py + stream_manager.py | ✅ DONE | 2026-06-10 |
| 7c | Split polyphonic_synth.py → oscillator.py + voice.py + multi_oscillator_synth.py | ✅ DONE | 2026-06-10 |
| 7d | Split mixer_engine.py → mixer_channel.py + mixer_bus.py | ✅ DONE | 2026-06-10 |

### 12.2 All Refactoring Complete

All planned refactoring phases (1–7) have been completed. Key outcomes:

- **13 legacy files deleted** (Phase 1)
- **Audio pipeline unified** into AudioManager with DeviceManager/StreamManager delegation (Phase 2)
- **All contracts use `typing.Protocol`** — no ABCs remain (Phase 3)
- **Dock-based MainWindow** with 8 configurable panels (Phase 4)
- **TOML config persistence** with platform-appropriate paths (Phase 5)
- **Cross-platform CI** (ubuntu + windows, Python 3.11/3.12/3.14) (Phase 6)
- **Large file splits**: audio_manager (1074→400), polyphonic_synth (1145→450), mixer_engine (1063→560) (Phase 7)

### 12.5 Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-10 | Use Protocols over ABCs | Structural typing, no inheritance coupling |
| 2026-06-10 | Merge audio into AudioManager | Single entry point for audio callback |
| 2026-06-10 | Delete use_cases/ | Unused, handlers do the job |
| 2026-06-10 | TOML for config | Poetry-compatible, human-readable |
| 2026-06-10 | Full frontend recreation | Clean slate with proper View/Controller/Model |
| 2026-06-10 | Split audio_manager into device_manager + stream_manager | Single-responsibility, <500 lines per file |
| 2026-06-10 | Split polyphonic_synth into oscillator/voice/multi_oscillator | Isolate waveform gen, voice state, multi-osc logic |
| 2026-06-10 | Split mixer_engine into mixer_channel + mixer_bus | ChannelStrip and Bus are separate concerns |
