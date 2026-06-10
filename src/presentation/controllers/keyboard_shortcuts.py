"""Keyboard Shortcuts Manager - Gestor de atajos de teclado configurables.

Sistema de atajos con persistencia en JSON (~/.justbeat/shortcuts.json),
detección de conflictos, categorías, y reset a valores por defecto.

Uso:
    manager = ShortcutsManager(parent)
    manager.create_shortcuts(window)
    manager.get_shortcut("Play/Pause")  # devuelve la key actual
    manager.set_shortcut("Play/Pause", "Ctrl+Space")  # reasignar
"""

from pathlib import Path
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass, field, asdict
import json
import logging

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QKeySequence, QShortcut


logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".justbeat"
SHORTCUTS_FILE = CONFIG_DIR / "shortcuts.json"


@dataclass
class ShortcutEntry:
    name: str
    category: str
    default_key: str
    description: str = ""
    current_key: str = ""

    def __post_init__(self):
        if not self.current_key:
            self.current_key = self.default_key


DEFAULT_SHORTCUTS: List[ShortcutEntry] = [
    # Transport
    ShortcutEntry("Play/Pause", "Transport", "Space", "Iniciar/detener reproducción"),
    ShortcutEntry("Stop", "Transport", "Ctrl+.", "Detener y volver al inicio"),
    ShortcutEntry("Record", "Transport", "R", "Iniciar/detener grabación"),
    ShortcutEntry("Loop", "Transport", "L", "Activar/desactivar loop"),
    ShortcutEntry("Metronome", "Transport", "M", "Activar/desactivar metrónomo"),
    ShortcutEntry("Rewind", "Transport", "Ctrl+Left", "Retroceder"),
    ShortcutEntry("Forward", "Transport", "Ctrl+Right", "Avanzar"),
    ShortcutEntry("Go to Start", "Transport", "Home", "Ir al inicio"),
    ShortcutEntry("Go to End", "Transport", "End", "Ir al final"),
    # Edit
    ShortcutEntry("Undo", "Edit", "Ctrl+Z", "Deshacer última acción"),
    ShortcutEntry("Redo", "Edit", "Ctrl+Y", "Rehacer última acción"),
    ShortcutEntry("Cut", "Edit", "Ctrl+X", "Cortar selección"),
    ShortcutEntry("Copy", "Edit", "Ctrl+C", "Copiar selección"),
    ShortcutEntry("Paste", "Edit", "Ctrl+V", "Pegar"),
    ShortcutEntry("Delete", "Edit", "Del", "Eliminar selección"),
    ShortcutEntry("Select All", "Edit", "Ctrl+A", "Seleccionar todo"),
    ShortcutEntry("Duplicate", "Edit", "Ctrl+D", "Duplicar selección"),
    # View
    ShortcutEntry("Sequencer", "View", "F1", "Abrir Step Sequencer"),
    ShortcutEntry("Synth", "View", "F2", "Abrir Synth Panel"),
    ShortcutEntry("Piano Roll", "View", "F3", "Abrir Piano Roll"),
    ShortcutEntry("Mixer", "View", "F4", "Abrir Mixer"),
    ShortcutEntry("Browser", "View", "F5", "Abrir Browser"),
    ShortcutEntry("Keyboard", "View", "F6", "Abrir Virtual Keyboard"),
    ShortcutEntry("Visualizer", "View", "F7", "Abrir Visualizer"),
    ShortcutEntry("Fullscreen", "View", "F11", "Pantalla completa"),
    # Track
    ShortcutEntry("Add Track", "Track", "Ctrl+T", "Agregar nueva pista"),
    ShortcutEntry("Duplicate Track", "Track", "Ctrl+Shift+D", "Duplicar pista actual"),
    ShortcutEntry("Delete Track", "Track", "Ctrl+Shift+X", "Eliminar pista actual"),
    ShortcutEntry("Mute Track", "Track", "Ctrl+M", "Silenciar pista actual"),
    ShortcutEntry("Solo Track", "Track", "Ctrl+S", "Solo pista actual"),
    ShortcutEntry("Arm Track", "Track", "Ctrl+Shift+R", "Armar pista para grabación"),
    # File
    ShortcutEntry("New Project", "File", "Ctrl+N", "Nuevo proyecto"),
    ShortcutEntry("Open Project", "File", "Ctrl+O", "Abrir proyecto"),
    ShortcutEntry("Save Project", "File", "Ctrl+S", "Guardar proyecto"),
    ShortcutEntry("Save As", "File", "Ctrl+Shift+S", "Guardar como..."),
    ShortcutEntry("Export Audio", "File", "Ctrl+E", "Exportar audio"),
    ShortcutEntry("Export MIDI", "File", "Ctrl+Shift+E", "Exportar MIDI"),
    ShortcutEntry("Preferences", "File", "Ctrl+,", "Abrir preferencias"),
    ShortcutEntry("Quit", "File", "Ctrl+Q", "Salir de la aplicación"),
    # Tools
    ShortcutEntry("Quantize", "Tools", "Ctrl+Q", "Cuantizar notas seleccionadas"),
    ShortcutEntry("Split", "Tools", "S", "Dividir clip en playhead"),
    ShortcutEntry("Snap Toggle", "Tools", "N", "Activar/desactivar snap"),
]


class ShortcutsManager(QObject):
    """Gestor de atajos de teclado configurables y persistentes."""

    # Transport
    play_triggered = Signal()
    stop_triggered = Signal()
    record_triggered = Signal()

    # Edit
    undo_triggered = Signal()
    redo_triggered = Signal()
    cut_triggered = Signal()
    copy_triggered = Signal()
    paste_triggered = Signal()
    delete_triggered = Signal()
    select_all_triggered = Signal()
    duplicate_triggered = Signal()

    # View
    sequencer_triggered = Signal()
    synth_triggered = Signal()
    piano_roll_triggered = Signal()
    mixer_triggered = Signal()
    browser_triggered = Signal()
    keyboard_triggered = Signal()
    visualizer_triggered = Signal()
    fullscreen_triggered = Signal()

    # Track
    add_track_triggered = Signal()
    duplicate_track_triggered = Signal()
    delete_track_triggered = Signal()
    mute_track_triggered = Signal()
    solo_track_triggered = Signal()
    arm_track_triggered = Signal()

    # File
    new_project_triggered = Signal()
    open_project_triggered = Signal()
    save_project_triggered = Signal()
    save_as_triggered = Signal()
    export_audio_triggered = Signal()
    export_midi_triggered = Signal()
    preferences_triggered = Signal()
    quit_triggered = Signal()

    # Tools
    quantize_triggered = Signal()
    split_triggered = Signal()
    snap_toggle_triggered = Signal()

    # Legacy F-key aliases (backward compat)
    @property
    def f1_triggered(self): return self.sequencer_triggered
    @property
    def f2_triggered(self): return self.synth_triggered
    @property
    def f3_triggered(self): return self.piano_roll_triggered
    @property
    def f4_triggered(self): return self.mixer_triggered
    @property
    def f5_triggered(self): return self.browser_triggered
    @property
    def f6_triggered(self): return self.keyboard_triggered
    @property
    def f7_triggered(self): return self.visualizer_triggered
    @property
    def f8_triggered(self): return self.fullscreen_triggered

    _SIGNAL_MAP: Dict[str, str] = {
        "Play/Pause": "play_triggered",
        "Stop": "stop_triggered",
        "Record": "record_triggered",
        "Undo": "undo_triggered",
        "Redo": "redo_triggered",
        "Cut": "cut_triggered",
        "Copy": "copy_triggered",
        "Paste": "paste_triggered",
        "Delete": "delete_triggered",
        "Select All": "select_all_triggered",
        "Duplicate": "duplicate_triggered",
        "Sequencer": "sequencer_triggered",
        "Synth": "synth_triggered",
        "Piano Roll": "piano_roll_triggered",
        "Mixer": "mixer_triggered",
        "Browser": "browser_triggered",
        "Keyboard": "keyboard_triggered",
        "Visualizer": "visualizer_triggered",
        "Fullscreen": "fullscreen_triggered",
        "Add Track": "add_track_triggered",
        "Duplicate Track": "duplicate_track_triggered",
        "Delete Track": "delete_track_triggered",
        "Mute Track": "mute_track_triggered",
        "Solo Track": "solo_track_triggered",
        "Arm Track": "arm_track_triggered",
        "New Project": "new_project_triggered",
        "Open Project": "open_project_triggered",
        "Save Project": "save_project_triggered",
        "Save As": "save_as_triggered",
        "Export Audio": "export_audio_triggered",
        "Export MIDI": "export_midi_triggered",
        "Preferences": "preferences_triggered",
        "Quit": "quit_triggered",
        "Quantize": "quantize_triggered",
        "Split": "split_triggered",
        "Snap Toggle": "snap_toggle_triggered",
        "Loop": None,
        "Metronome": None,
        "Rewind": None,
        "Forward": None,
        "Go to Start": None,
        "Go to End": None,
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._parent = parent
        self._shortcuts: Dict[str, QShortcut] = {}
        self._entries: Dict[str, ShortcutEntry] = {}
        self._enabled = True
        self._load_defaults()
        self._load_from_disk()
        logger.info(f"ShortcutsManager: {len(self._entries)} atajos cargados")

    def _load_defaults(self):
        for entry in DEFAULT_SHORTCUTS:
            self._entries[entry.name] = entry

    def _load_from_disk(self):
        if not SHORTCUTS_FILE.exists():
            return
        try:
            data = json.loads(SHORTCUTS_FILE.read_text(encoding="utf-8"))
            for name, key in data.items():
                if name in self._entries:
                    self._entries[name].current_key = key
            logger.debug(f"Shortcuts cargados desde {SHORTCUTS_FILE}")
        except Exception as e:
            logger.warning(f"Error cargando shortcuts: {e}")

    def _save_to_disk(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            data = {name: e.current_key for name, e in self._entries.items()
                    if e.current_key != e.default_key}
            SHORTCUTS_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Error guardando shortcuts: {e}")

    def create_shortcuts(self, parent_widget: QWidget):
        for entry in self._entries.values():
            self._create_shortcut(parent_widget, entry)

    def _create_shortcut(self, parent: QWidget, entry: ShortcutEntry):
        signal_name = self._SIGNAL_MAP.get(entry.name)
        if signal_name is None:
            return
        signal: Signal = getattr(self, signal_name, None)
        if signal is None:
            return
        shortcut = QShortcut(QKeySequence(entry.current_key), parent)
        shortcut.activated.connect(signal.emit)
        self._shortcuts[entry.name] = shortcut

    def set_shortcut(self, name: str, new_key: str) -> bool:
        entry = self._entries.get(name)
        if entry is None:
            return False

        conflict = self.find_conflict(name, new_key)
        if conflict:
            logger.warning(f"Conflicto: {new_key} ya asignado a '{conflict}'")
            return False

        entry.current_key = new_key
        qs = self._shortcuts.get(name)
        if qs:
            qs.setKey(QKeySequence(new_key))
        self._save_to_disk()
        return True

    def find_conflict(self, name: str, new_key: str) -> Optional[str]:
        for other_name, entry in self._entries.items():
            if other_name != name and entry.current_key == new_key:
                return other_name
        return None

    def get_shortcut(self, name: str) -> Optional[str]:
        entry = self._entries.get(name)
        return entry.current_key if entry else None

    def get_all_shortcuts(self) -> Dict[str, ShortcutEntry]:
        return dict(self._entries)

    def get_by_category(self, category: str) -> List[ShortcutEntry]:
        return [e for e in self._entries.values() if e.category == category]

    def get_categories(self) -> List[str]:
        cats: List[str] = []
        for e in self._entries.values():
            if e.category not in cats:
                cats.append(e.category)
        return cats

    def reset_defaults(self):
        for entry in self._entries.values():
            entry.current_key = entry.default_key
        for name, qs in self._shortcuts.items():
            entry = self._entries.get(name)
            if entry:
                qs.setKey(QKeySequence(entry.default_key))
        self._save_to_disk()

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        for shortcut in self._shortcuts.values():
            shortcut.setEnabled(enabled)
