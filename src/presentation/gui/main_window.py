"""Ventana principal de JustBeat-DAW con UI profesional.

Integra todos los paneles dockables, la barra de transporte
profesional y el sistema de temas ProTheme.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QToolBar, QStatusBar,
    QPushButton, QLabel, QSlider, QComboBox, QFileDialog,
    QMessageBox, QSplitter, QDialog, QTabWidget
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QAction, QIcon

from src.presentation.widgets.sequencer import StepSequencerWidget
from src.presentation.widgets.synth_panel import SynthPanelWidget
from src.presentation.widgets.mixer import MixerWidget
from src.presentation.widgets.piano_roll import PianoRollWidget
from src.presentation.widgets.browser import BrowserWidget
from src.presentation.widgets.virtual_keyboard import VirtualKeyboard, KeyboardWidget
from src.presentation.widgets.visualizer import AudioVisualizer, LevelMeter
from src.presentation.widgets.settings_dialog import ProjectSettingsDialog, PreferencesDialog

from src.presentation.widgets.toast import ToastManager
from src.presentation.widgets.shortcuts_dialog import ShortcutsDialog

# New widgets
from src.presentation.widgets.arrange_view import ArrangeViewWidget
from src.presentation.widgets.effect_chain import EffectChainWidget
from src.presentation.widgets.automation_lane import AutomationLane
from src.presentation.widgets.midi_learn_panel import MIDILearnPanel
from src.presentation.widgets.export_dialog import ExportDialog

# Controllers
from src.presentation.controllers import (
    PlaybackController, ExportController,
    ShortcutsManager, MIDILearnManager, ExportSettings,
    MenuBarManager, StatusBarManager, DockManager, PanelController
)

# App Core (nueva arquitectura)
from src.application.app_core import AppCore, get_app_core, initialize_app

# Presentation Model (Nueva arquitectura)
from src.presentation.models import (
    PresentationModel,
    get_presentation_model,
    initialize_presentation_model
)

# Theme Integration
from src.presentation.styles.theme_integration import ThemeMixin
from src.presentation.styles.theme_manager import ThemeManager

# Professional Theme
from src.presentation.styles.pro_theme import ProTheme
from src.presentation.styles.icons import Icons

# Transport Bar profesional
from src.presentation.gui.transport_bar import TransportBar

# Logger for this module
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window for JustBeat-DAW application."""
    
    # Signals
    play_clicked = Signal()
    stop_clicked = Signal()
    new_project_clicked = Signal()
    open_project_clicked = Signal()
    save_project_clicked = Signal()
    bpm_changed = Signal(int)
    
    def __init__(
        self,
        app_core: Optional[AppCore] = None,
        presentation_model: Optional[PresentationModel] = None
    ):
        """Inicializar la ventana principal con UI profesional.

        Args:
            app_core: Instancia de AppCore para control de la aplicación.
            presentation_model: Instancia de PresentationModel (preferida).
        """
        logger.info("MainWindow.__init__ started")
        super().__init__()
        logger.debug("[INIT] super().__init__() OK")
        
        # Aplicar tema profesional
        self._pro_theme = ProTheme.get("obsidian")
        logger.debug("[INIT] ProTheme loaded")
        
        # Usar PresentationModel si se proporciona, o obtener el global
        if presentation_model is not None:
            self._model = presentation_model
        else:
            self._model = get_presentation_model()
        logger.debug(f"[INIT] PresentationModel: {self._model}")
        
        # Mantener app_core para compatibilidad hacia atrás
        if app_core is not None:
            self._app_core = app_core
        else:
            self._app_core = get_app_core()
        logger.debug(f"[INIT] AppCore: {self._app_core}")
        
        self._is_playing = False
        self._current_project = None
        
        self.setWindowTitle("JustBeat-DAW")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        logger.info("MainWindow base properties set")

        # Start maximized
        self.showMaximized()
        logger.debug("[INIT] showMaximized() OK")

        # Controllers - ahora usan PresentationModel internamente
        self._playback_controller = PlaybackController(
            presentation_model=self._model
        )
        logger.debug("[INIT] PlaybackController OK")
        
        # New Controllers
        self._export_controller = ExportController()
        self._shortcut_manager = ShortcutsManager()
        self._menu_bar_manager = MenuBarManager()
        self._status_bar_manager = StatusBarManager(parent=self)
        self._dock_manager = DockManager(self)
        self._midi_learn_manager = MIDILearnManager()
        self._theme_manager = ThemeManager()
        logger.debug("[INIT] All controllers OK")
        
        # Inicializar ToastManager
        ToastManager.initialize(self)
        logger.debug("[INIT] ToastManager OK")
        
        # Transport Bar profesional
        self._transport_bar = TransportBar(presentation_model=self._model)
        logger.debug("[INIT] TransportBar OK")

        # 1. Initialize Widgets (References only)
        self._create_widgets()
        logger.debug("[INIT] _create_widgets() OK")

        # 2. Setup Managers & Layout
        self._setup_professional_ui()
        logger.debug("[INIT] _setup_professional_ui() OK")

        # Legacy toolbar compatibility (creates _swing_slider, _pattern_combo, etc.)
        self._setup_toolbar()
        logger.debug("[INIT] _setup_toolbar() OK")

        # 3. Connect Signals (después de crear widgets y toolbar para evitar race conditions)
        self._connect_signals()
        logger.debug("[INIT] _connect_signals() OK")
        self._connect_model_signals()
        logger.debug("[INIT] _connect_model_signals() OK")
        self._connect_manager_signals()
        logger.debug("[INIT] _connect_manager_signals() OK")

        # 4. Restore layout persistido (si existe)
        self._dock_manager.restore_settings()
        logger.debug("[INIT] restore_settings() OK")

        logger.info("MainWindow initialization complete")

    def _create_widgets(self):
        """Create all main widgets (but dont layout them yet)."""
        self._browser = BrowserWidget(self._model)
        self._sequencer = StepSequencerWidget(self._model)
        self._piano_roll = PianoRollWidget(self._model)
        self._synth_panel = SynthPanelWidget(self._model)
        self._mixer = MixerWidget(self._model)
        self._virtual_keyboard = KeyboardWidget(self._model)
        self._visualizer = AudioVisualizer(self._model)
        self._arrange_view = ArrangeViewWidget(self._model)
        self._effect_chain = EffectChainWidget(self._model)
        self._automation_lane = AutomationLane("", presentation_model=self._model)
        self._midi_learn_panel = MIDILearnPanel(self._model)

    def _setup_professional_ui(self):
        """Configurar la UI profesional usando managers y TransportBar."""
        c = self._pro_theme
        
        # Widget central con fondo del tema
        central = QWidget()
        central.setStyleSheet(f"background-color: {c.bg_primary};")
        self.setCentralWidget(central)

        # Layout vertical: TransportBar + contenido
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Menu Bar
        self.setMenuBar(self._menu_bar_manager.create_menu_bar())

        # Transport Bar como QToolBar en el área de toolbar del MainWindow
        self._transport_toolbar = QToolBar("Transport", self)
        self._transport_toolbar.setMovable(False)
        self._transport_toolbar.setFloatable(False)
        self._transport_toolbar.setIconSize(self._transport_bar.sizeHint())
        self._transport_toolbar.addWidget(self._transport_bar)
        self.addToolBar(self._transport_toolbar)

        # Dock Layout (contenido principal)
        widgets = {
            "browser": self._browser,
            "sequencer": self._sequencer,
            "piano_roll": self._piano_roll,
            "synth": self._synth_panel,
            "mixer": self._mixer,
            "keyboard": self._virtual_keyboard,
            "visualizer": self._visualizer,
            "arrange": self._arrange_view,
            "effect_chain": self._effect_chain,
            "automation": self._automation_lane,
            "midi_learn": self._midi_learn_panel,
        }
        
        # Los docks se añaden al MainWindow directamente, no al layout
        self._dock_manager.setup_standard_layout(widgets)

        # StatusBar
        self._status_bar_manager.create_status_bar()
        self.setStatusBar(self._status_bar_manager.status_bar)
        
        # Aplicar QSS global del tema
        self.setStyleSheet(ProTheme.to_stylesheet())
        
        logger.info("StatusBarManager wired and transport bar created")

        # Sincronizar estado inicial del menú con docks
        for name, dock in self._dock_manager.get_registered_docks().items():
            self._menu_bar_manager.update_view_state(name, dock.isVisible())

    def _connect_manager_signals(self):
        """Connect signals from MenuBarManager to MainWindow/Core actions."""
        m = self._menu_bar_manager
        
        # File
        m.new_project.connect(self._on_new_project)
        m.open_project.connect(self._on_open_project)
        m.save_project.connect(self._on_save_project)
        m.save_as.connect(self._on_save_project_as)
        m.export_wav.connect(self._on_export_wav)
        m.export_midi.connect(self._on_export_midi)
        m.preferences.connect(self._on_preferences)
        m.quit.connect(self.close)

        # Edit
        m.undo.connect(self._on_undo)
        m.redo.connect(self._on_redo)
        m.cut.connect(lambda: self.statusBar().showMessage("Cut: not implemented"))
        m.copy.connect(lambda: self.statusBar().showMessage("Copy: not implemented"))
        m.paste.connect(lambda: self.statusBar().showMessage("Paste: not implemented"))
        m.delete.connect(self._on_delete_track)
        m.select_all.connect(lambda: self.statusBar().showMessage("Select All: not implemented"))
        logger.info("Edit menu actions connected")

        # Transport
        m.play.connect(self._on_play)
        m.stop.connect(self._on_stop)

        # View (Toggles) - genérico via _toggle_dock
        dock_map = {
            m.show_arrange: "arrange",
            m.show_sequencer: "sequencer",
            m.show_synth: "synth",
            m.show_piano_roll: "piano_roll",
            m.show_mixer: "mixer",
            m.show_browser: "browser",
            m.show_keyboard: "keyboard",
            m.show_visualizer: "visualizer",
            m.show_effect_chain: "effect_chain",
            m.show_automation: "automation",
            m.show_midi_learn: "midi_learn",
        }
        for signal, name in dock_map.items():
            signal.connect(lambda v=None, n=name: self._toggle_dock(n, v))
        
        # Track
        m.remove_track.connect(self._on_delete_track)
        m.duplicate_track.connect(self._on_duplicate_track)
        m.rename_track.connect(self._on_rename_track)
        m.color_track.connect(self._on_color_track)
        
        # Transport - New signals
        m.loop.connect(self._on_loop_toggle)
        m.metronome.connect(lambda: self._on_metronome(not self._model.metronome_enabled if self._model else True))
        m.rewind.connect(self._on_rewind)
        m.goto_start.connect(self._on_goto_start)
        m.goto_end.connect(self._on_goto_end)
        m.record.connect(self._on_record)

        # Help
        m.about.connect(self._on_about)
        m.help_docs.connect(self._on_shortcuts)

        # Nuevas Conexiones
        m.project_settings.connect(self._on_project_settings)
        m.audio_settings.connect(self._on_audio_settings)
        m.add_track_instrument.connect(self._add_track_instrument)
        m.add_track_audio.connect(self._add_track_audio)
        m.add_track_automation.connect(self._add_track_automation)
        m.change_sample_rate.connect(self._on_sample_rate_changed)
        m.change_buffer_size.connect(self._on_buffer_size_changed)

        # Shortcuts dialog
        m.shortcuts.connect(self._on_show_shortcuts)
    
    def _connect_model_signals(self) -> None:
        """Conectar señales del PresentationModel."""
        if self._model is None:
            return
        
        # Re-emitir señales del modelo para uso interno
        self._model.playback_state_changed.connect(
            self._on_playback_state_changed
        )
        self._model.position_changed.connect(self._on_position_update)
        self._model.bpm_changed.connect(self._on_bpm_update)
        self._model.track_added.connect(self._update_track_lists)
        self._model.track_removed.connect(self._update_track_lists)
        self._model.track_selected.connect(self._on_track_selected)
        self._model.modification_changed.connect(self._on_modification_changed)
        self._model.recording_state_changed.connect(self._on_recording_state_changed)
        self._model.error_occurred.connect(self._on_error_occurred)
        
        # Conectar señales del DockManager para sincronizar el menú
        self._dock_manager.dock_visibility_changed.connect(self._on_dock_visibility_changed)
        
        logger.debug("PresentationModel signals connected")
    
    def _on_playback_state_changed(self, state: str) -> None:
        """Manejar cambio de estado de reproducción."""
        if not hasattr(self, '_transport_bar'):
            return

        if state == "playing":
            self._is_playing = True
            self._play_button.setIcon(Icons.PAUSE)
            self._transport_bar.set_playing(True)
            self.statusBar().showMessage("Playing...")
            if self._status_bar_manager:
                self._status_bar_manager.update_playback_state(True)
            # Actualizar visualizer
            if hasattr(self, '_visualizer'):
                self._visualizer.set_playing(True)
        elif state == "stopped":
            self._is_playing = False
            self._play_button.setIcon(Icons.PLAY)
            self._transport_bar.set_playing(False)
            self.statusBar().showMessage("Stopped")
            if self._status_bar_manager:
                self._status_bar_manager.update_playback_state(False)
            if hasattr(self, '_visualizer'):
                self._visualizer.set_playing(False)
        elif state == "paused":
            self._transport_bar.set_playing(False)
            self.statusBar().showMessage("Paused")
        logger.debug(f"Playback state changed: {state}")
    
    def _on_position_update(self, tick: int) -> None:
        """Manejar actualización de posición."""
        if self._status_bar_manager:
            self._status_bar_manager.update_position_ticks(tick)
        if self._arrange_view and hasattr(self._arrange_view, 'set_playhead_position'):
            self._arrange_view.set_playhead_position(tick)
        if self._sequencer and hasattr(self._sequencer, 'set_current_step'):
            step = tick // 480
            self._sequencer.set_current_step(step)
    
    def _on_bpm_update(self, bpm: int) -> None:
        """Manejar actualización de BPM."""
        if hasattr(self, '_transport_bar'):
            self._transport_bar.set_bpm(bpm)
    
    def _on_track_added(self, track) -> None:
        """Manejar pista añadida."""
        logger.info(f"Track added: {track.name if hasattr(track, 'name') else track}")
    
    def _on_track_removed(self, track_id: str) -> None:
        """Manejar pista eliminada."""
        logger.info(f"Track removed: {track_id}")
    
    def _on_modification_changed(self, modified: bool) -> None:
        """Manejar cambio de estado de modificación."""
        title = "JustBeat-DAW"
        if modified:
            title += " *"
        self.setWindowTitle(title)
    
    def _on_error_occurred(self, message: str) -> None:
        """Manejar error."""
        logger.error(f"Error: {message}")
        self.statusBar().showMessage(f"Error: {message}", 5000)
    



    
    def _setup_toolbar(self):
        """Configurar conexiones de la TransportBar (reemplaza al toolbar antiguo)."""
        logger.debug("[TOOLBAR] Starting _setup_toolbar...")
        # Obtener botones de la TransportBar
        logger.debug("[TOOLBAR] Getting transport_bar buttons...")
        btns = self._transport_bar.get_buttons()
        logger.debug(f"[TOOLBAR] Buttons dict keys: {list(btns.keys())}")
        self._play_button = btns["play"]
        logger.debug("[TOOLBAR] _play_button OK")
        self._stop_button = btns["stop"]
        logger.debug("[TOOLBAR] _stop_button OK")
        self._record_button = btns["record"]
        logger.debug("[TOOLBAR] _record_button OK")

        # Crear QComboBox para steps (necesario para compatibilidad)
        logger.debug("[TOOLBAR] Creating QComboBox _pattern_combo...")
        self._pattern_combo = QComboBox()
        self._pattern_combo.addItems(["8", "16", "32", "64"])
        self._pattern_combo.setCurrentText("16")
        logger.debug("[TOOLBAR] _pattern_combo OK")
        
        # Crear swing slider (necesario para compatibilidad)
        logger.debug("[TOOLBAR] Creating QSlider _swing_slider...")
        self._swing_slider = QSlider(Qt.Orientation.Horizontal)
        self._swing_slider.setRange(0, 100)
        self._swing_slider.setValue(0)
        self._swing_slider.setFixedWidth(60)
        logger.debug("[TOOLBAR] _swing_slider OK")
        
        logger.debug("[TOOLBAR] Creating QLabel _swing_label...")
        self._swing_label = QLabel("0%")
        logger.debug("[TOOLBAR] _swing_label OK")
        
        # Time Signature (para compatibilidad)
        logger.debug("[TOOLBAR] Creating QComboBox _ts_combo...")
        self._ts_combo = QComboBox()
        self._ts_combo.addItems(["4/4", "3/4", "2/4", "6/8"])
        logger.debug("[TOOLBAR] _ts_combo OK")
        
        logger.info("Toolbar legacy compatibility setup complete")
    
    def _setup_statusbar(self):
        """Setup the status bar."""
        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #333;
                color: white;
                border-top: 1px solid #555;
            }
        """)
    
    def _connect_signals(self):
        """Conectar señales internas incluyendo la TransportBar."""
        logger.debug("[SIGNALS] Connecting TransportBar signals...")
        # === Transport Bar Signals ===
        self._transport_bar.play_clicked.connect(self._on_play)
        self._transport_bar.stop_clicked.connect(self._on_stop)
        self._transport_bar.record_clicked.connect(self._on_record)
        self._transport_bar.bpm_changed.connect(self._on_bpm_changed)
        self._transport_bar.metronome_toggled.connect(self._on_metronome)
        self._transport_bar.loop_toggled.connect(self._on_loop_toggle)
        logger.debug("[SIGNALS] TransportBar signals OK")
        
        # Conectar TransportBar al modelo
        self._transport_bar.connect_signals(self._model)
        logger.debug("[SIGNALS] TransportBar model signals OK")
        
        # Legacy signal connections (compatibilidad)
        logger.debug(f"[SIGNALS] Connecting _swing_slider (type={type(self._swing_slider).__name__})...")
        self._swing_slider.valueChanged.connect(self._on_swing_changed)
        logger.debug(f"[SIGNALS] Connecting _pattern_combo (type={type(self._pattern_combo).__name__})...")
        self._pattern_combo.currentIndexChanged.connect(self._on_pattern_length_changed)
        
        # Connect keyboard shortcuts
        self._shortcut_manager.create_shortcuts(self)
        self._shortcut_manager.play_triggered.connect(self._on_play)
        self._shortcut_manager.stop_triggered.connect(self._on_stop)
        self._shortcut_manager.record_triggered.connect(self._on_record)
        self._shortcut_manager.undo_triggered.connect(self._on_undo)
        self._shortcut_manager.redo_triggered.connect(self._on_redo)
        self._shortcut_manager.cut_triggered.connect(lambda: self.statusBar().showMessage("Cut: not implemented"))
        self._shortcut_manager.copy_triggered.connect(lambda: self.statusBar().showMessage("Copy: not implemented"))
        self._shortcut_manager.paste_triggered.connect(lambda: self.statusBar().showMessage("Paste: not implemented"))
        self._shortcut_manager.delete_triggered.connect(self._on_delete_track)
        self._shortcut_manager.select_all_triggered.connect(lambda: self.statusBar().showMessage("Select All: not implemented"))
        
        # Connect F-key shortcuts to dock toggles
        fkey_docks = ["sequencer", "synth", "piano_roll", "mixer", "browser", "keyboard", "visualizer", "automation"]
        fkey_signals = [
            self._shortcut_manager.f1_triggered, self._shortcut_manager.f2_triggered,
            self._shortcut_manager.f3_triggered, self._shortcut_manager.f4_triggered,
            self._shortcut_manager.f5_triggered, self._shortcut_manager.f6_triggered,
            self._shortcut_manager.f7_triggered, self._shortcut_manager.f8_triggered,
        ]
        for signal, dock_name in zip(fkey_signals, fkey_docks):
            signal.connect(lambda v=None, n=dock_name: self._toggle_dock(n))
        logger.info("ShortcutsManager: play/stop/record/undo/redo + F1-F8 connected")
        
        # Connect sequencer signals
        if self._sequencer:
            self._sequencer.step_changed.connect(self._on_step_changed)
        
        # Connect piano roll signals
        if self._piano_roll:
            self._piano_roll.note_toggled.connect(self._on_note_toggled)
            self._piano_roll.note_clicked.connect(self._on_note_clicked)
        
        self._connect_mixer_signals()
        self._connect_synth_panel_signals()
        self._connect_widget_signals()
        self._connect_midi_learn_signals()
    
    def _connect_widget_signals(self) -> None:
        """Connect signals from widgets that were previously disconnected."""
        # Browser
        if self._browser:
            self._browser.file_selected.connect(self._on_browser_file_selected)
            logger.debug("BrowserWidget signals connected")
        
        # Virtual Keyboard
        if self._virtual_keyboard:
            self._virtual_keyboard.note_on.connect(self._on_keyboard_note_pressed)
            self._virtual_keyboard.note_off.connect(self._on_keyboard_note_released)
            logger.debug("VirtualKeyboard signals connected")
        
        # Arrange View
        if self._arrange_view:
            self._arrange_view.clip_selected.connect(self._on_arrange_clip_selected)
            self._arrange_view.clip_moved.connect(self._on_arrange_clip_moved)
            logger.debug("ArrangeViewWidget signals connected")
        
        # Automation Lane
        if self._automation_lane:
            self._automation_lane.point_added.connect(self._on_automation_point_added)
            self._automation_lane.point_moved.connect(self._on_automation_point_moved)
            self._automation_lane.point_removed.connect(self._on_automation_point_removed)
            logger.debug("AutomationLane signals connected")
        
        # Effect Chain
        if self._effect_chain:
            self._effect_chain.effect_added.connect(self._on_effect_changed)
            self._effect_chain.effect_removed.connect(self._on_effect_bypass_toggled)
            self._effect_chain.chain_changed.connect(self._on_effect_mix_changed)
            logger.debug("EffectChainWidget signals connected")
        
        # Time Signature combo
        if self._ts_combo:
            self._ts_combo.currentTextChanged.connect(self._on_time_signature_changed)
            logger.debug("Time signature combo connected")
        
        logger.info("All widget signals connected")
    
    def _connect_midi_learn_signals(self) -> None:
        """Connect MIDILearnPanel to MIDILearnManager."""
        if self._midi_learn_panel and self._midi_learn_manager:
            self._midi_learn_panel.mapping_added.connect(self._midi_learn_manager.add_mapping)
            self._midi_learn_panel.mapping_removed.connect(self._midi_learn_manager.remove_mapping)
            self._midi_learn_panel.midi_learn_started.connect(
                lambda param: self._midi_learn_manager.start_learn(param, "")
            )
            self._midi_learn_panel.midi_learn_stopped.connect(self._midi_learn_manager.cancel_learn)
            logger.info("MIDILearnPanel connected to MIDILearnManager")
    
    def _on_browser_file_selected(self, file_path: str) -> None:
        """Handle file selected from browser."""
        logger.info(f"Browser file selected: {file_path}")
        self.statusBar().showMessage(f"Selected: {file_path}")
    
    def _on_keyboard_note_pressed(self, midi_note: int) -> None:
        """Handle virtual keyboard note press."""
        if self._app_core:
            self._app_core.play_note(midi_note)
            note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            octave = (midi_note // 12) - 1
            note_name = note_names[midi_note % 12]
            logger.debug(f"Virtual keyboard: {note_name}{octave} ON")
    
    def _on_keyboard_note_released(self, midi_note: int) -> None:
        """Handle virtual keyboard note release."""
        if self._app_core:
            self._app_core.stop_note(midi_note)
            logger.debug(f"Virtual keyboard: MIDI {midi_note} OFF")
    
    def _on_arrange_clip_selected(self, clip_data) -> None:
        """Handle clip selection in arrange view."""
        logger.info(f"Arrange clip selected: {clip_data}")
        self.statusBar().showMessage(f"Clip selected")
    
    def _on_arrange_clip_moved(self, clip_id, new_tick) -> None:
        """Handle clip moved in arrange view."""
        logger.info(f"Arrange clip {clip_id} moved to tick {new_tick}")
    
    def _on_automation_point_added(self, point) -> None:
        logger.debug(f"Automation point added: {point}")
    
    def _on_automation_point_moved(self, point, new_value) -> None:
        logger.debug(f"Automation point moved: {point} -> {new_value}")
    
    def _on_automation_point_removed(self, point) -> None:
        logger.debug(f"Automation point removed: {point}")
    
    def _on_effect_changed(self, effect_data) -> None:
        logger.info(f"Effect changed: {effect_data}")
    
    def _on_effect_bypass_toggled(self, index: int, bypassed: bool) -> None:
        logger.debug(f"Effect {index} bypass: {bypassed}")
    
    def _on_effect_mix_changed(self) -> None:
        logger.debug("Effect chain changed")
    
    def _on_time_signature_changed(self, text: str) -> None:
        """Handle time signature combo change."""
        logger.info(f"Time signature changed to {text}")
        if self._status_bar_manager:
            parts = text.split("/")
            if len(parts) == 2:
                self._status_bar_manager.update_time_signature(int(parts[0]), int(parts[1]))
        self.statusBar().showMessage(f"Time Signature: {text}")
    
    # Toggle panel methods
    # Panel Toggles (connected to MenuBarManager signals)
    def _toggle_dock(self, name: str, visible: Optional[bool] = None) -> None:
        """Toggle dock visibility por nombre."""
        if visible is None:
            visible = not self._dock_manager.is_visible(name)
        if visible:
            self._dock_manager.show_dock(name)
        else:
            self._dock_manager.hide_dock(name)
        if self._menu_bar_manager:
            self._menu_bar_manager.update_view_state(name, visible)

    def closeEvent(self, event):
        self._dock_manager.save_settings()
        if self._app_core and hasattr(self._app_core, 'save_state'):
            self._app_core.save_state()
        super().closeEvent(event)

    def _on_dock_visibility_changed(self, name: str, visible: bool):
        """Update MenuBar state when a dock is shown/hidden (e.g. by manual close)."""
        if self._menu_bar_manager:
            self._menu_bar_manager.update_view_state(name, visible)

    # Event handlers
    def _on_play(self):
        """Handle play button click - toggle between play and stop."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Play button clicked via controller")
        
        # Connect sequencer before playing
        if self._sequencer:
            self._playback_controller.set_sequencer(self._sequencer)
        
        # Toggle playback (play if stopped, stop if playing)
        self._playback_controller.toggle_playback()
        
        self.play_clicked.emit()
    
    def _on_stop(self):
        """Handle stop button click."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Stop button clicked via controller")
        
        # Use playback controller
        self._playback_controller.stop()
        
        self.stop_clicked.emit()
        self._play_button.setIcon(Icons.PLAY)
        self.statusBar().showMessage("Stopped")
    
    def _on_bpm_changed(self, value: int):
        """Manejar cambio de BPM desde TransportBar o slider."""
        logger.info(f"BPM changed to {value}")
        self.bpm_changed.emit(value)
        if self._playback_controller:
            self._playback_controller.set_bpm(value)
        if hasattr(self, '_transport_bar'):
            self._transport_bar.set_bpm(value)
        if self._status_bar_manager:
            self._status_bar_manager.update_bpm(value)
        ToastManager.show_success(f"BPM changed to {value}")
    
    def _on_swing_changed(self, value: int):
        """Handle swing slider change."""
        self._swing_label.setText(f"{value}%")
    
    def _on_pattern_length_changed(self, index: int):
        """Handle pattern length combo box change."""
        length = int(self._pattern_combo.currentText())
        if self._sequencer:
            self._sequencer.set_num_steps(length)
        if self._app_core:
            self._app_core.set_pattern_length(length)
    
    def _on_step_changed(self, track_index: int, step_index: int, is_active: bool):
        """Handle step changed in sequencer."""
        if self._app_core:
            self._app_core.set_step_active(track_index, step_index, is_active)
        logger.debug(f"Step changed: track={track_index}, step={step_index}, active={is_active}")
    
    def _on_note_toggled(self, step: int, pitch: int):
        """Handle note toggled in piano roll.
        
        This connects the piano roll to the step sequencer - when a note
        is toggled in the piano roll, it updates the sequencer step.
        """
        if self._sequencer and self._app_core:
            # Get the selected track (first track by default)
            track_index = 0
            
            # Toggle the step in the sequencer based on piano roll note
            # Map pitch to track: lower pitches = earlier tracks
            track_for_note = (pitch % 4)  # Map to 4 tracks
            
            # Update the sequencer step
            self._sequencer.set_step_active(track_for_note, step, True)
            
            # Update the track note in the app controller
            self._app_core.set_track_note(track_for_note, pitch)
            
            notes = self._piano_roll.get_notes()
            self.statusBar().showMessage(f"Note at step {step+1}, pitch {pitch} -> Track {track_for_note}")
        
        # Update scheduler with new note
        if self._app_core:
            self._app_core.update_scheduler_notes()
    
    def _on_note_clicked(self, midi_note: int):
        """Handle note clicked in piano roll keyboard."""
        if self._app_core:
            # Play the note
            self._app_core.play_note(midi_note)
            
            # Set note for first track in sequencer (track index 0)
            self._app_core.set_track_note(0, midi_note)
            
            self.statusBar().showMessage(f"Playing note: MIDI {midi_note}")
        
        # Also show note name
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note // 12) - 1
        note_name = note_names[midi_note % 12]
        self.statusBar().showMessage(f"Playing: {note_name}{octave} (MIDI {midi_note})")
    
    def _connect_mixer_signals(self):
        """Connect mixer signals to app controller."""
        if self._mixer:
            # MixerWidget emits volume_changed(track_id, float) and mute_changed(track_id, bool)
            self._mixer.volume_changed.connect(self._on_mixer_volume_by_id)
            self._mixer.mute_changed.connect(self._on_mixer_mute_by_id)
            self._mixer.pan_changed.connect(self._on_mixer_pan_by_id)
    
    def _connect_synth_panel_signals(self):
        """Connect synth panel signals to app controller."""
        if self._synth_panel and self._app_core:
            # parameter_changed emits (track_id, param_name, value)
            self._synth_panel.parameter_changed.connect(
                self._on_synth_parameter_changed
            )
    
    def _on_mixer_volume_by_id(self, track_id: str, volume: float):
        """Handle mixer volume change by track_id (from MixerWidget signal)."""
        if self._app_core and self._model and self._model.current_project:
            tracks = self._model.current_project.get_tracks()
            for i, t in enumerate(tracks):
                if t.id == track_id:
                    self._app_core.set_track_volume(i, volume)
                    break
    
    def _on_mixer_mute_by_id(self, track_id: str, muted: bool):
        """Handle mixer mute change by track_id (from MixerWidget signal)."""
        if self._app_core and self._model and self._model.current_project:
            tracks = self._model.current_project.get_tracks()
            for i, t in enumerate(tracks):
                if t.id == track_id:
                    self._app_core.set_track_mute(i, muted)
                    break
    
    def _on_mixer_pan_by_id(self, track_id: str, pan: float):
        """Handle mixer pan change by track_id (from MixerWidget signal)."""
        if self._app_core and self._model and self._model.current_project:
            tracks = self._model.current_project.get_tracks()
            for i, t in enumerate(tracks):
                if t.id == track_id:
                    self._app_core.set_track_pan(i, pan)
                    break
    
    def _on_mixer_volume_changed(self, channel: int, volume: float):
        """Handle mixer volume change by index (legacy)."""
        if self._app_core:
            self._app_core.set_track_volume(channel, volume)
    
    def _on_mixer_mute_changed(self, channel: int, muted: bool):
        """Handle mixer mute change by index (legacy)."""
        if self._app_core:
            self._app_core.set_track_mute(channel, muted)
    
    def _on_synth_parameter_changed(self, track_id: str, param_name: str, value: float):
        """Handle synth parameter change (track_id, param_name, value)."""
        if self._app_core:
            self._app_core.set_synth_parameter(track_id, param_name, value)
    
    def _on_new_project(self):
        """Handle new project action."""
        if self._app_core:
            self._app_core.create_new_project()
        self.new_project_clicked.emit()
        self.statusBar().showMessage("New project created")
        ToastManager.show_success("New project created")
    
    def _on_open_project(self):
        """Handle open project action."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "JustBeat Project (*.jbproj)"
        )
        if file_path:
            if self._app_core:
                self._app_core.load_project(file_path)
            self.open_project_clicked.emit()
            self.statusBar().showMessage(f"Opened: {file_path}")
    
    def _on_save_project(self):
        """Handle save project action."""
        if self._app_core:
            self._app_core.save_project()
        self.save_project_clicked.emit()
        self.statusBar().showMessage("Project saved")
        ToastManager.show_success("Project saved")
    
    def _on_save_project_as(self):
        """Handle save project as action."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", "", "JustBeat Project (*.jbproj)"
        )
        if file_path:
            if self._app_core:
                self._app_core.save_project(file_path)
            self.save_project_clicked.emit()
            self.statusBar().showMessage(f"Saved: {file_path}")
    
    def _on_export_wav(self):
        """Handle export WAV action using ExportDialog."""
        logger.info("Export WAV triggered")
        dialog = ExportDialog(self._export_controller, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.statusBar().showMessage("Export completed successfully")
        else:
            self.statusBar().showMessage("Export cancelled")
    
    def _on_export_midi(self):
        """Handle export MIDI action."""
        logger.info("Export MIDI triggered")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export as MIDI", "", "MIDI File (*.mid)"
        )
        if file_path:
            if self._app_core:
                success = self._app_core.export_midi(file_path)
                if success:
                    self.statusBar().showMessage(f"Exported: {file_path}")
                else:
                    self.statusBar().showMessage("Export failed")
            else:
                self.statusBar().showMessage("Export failed - no app controller")
    
    def _on_undo(self):
        """Handle undo action."""
        # Usar PresentationModel para undo
        if self._model.app_core and hasattr(self._model.app_core, 'undo'):
            if self._model.app_core.undo():
                self.statusBar().showMessage("Undo")
            else:
                self.statusBar().showMessage("Nothing to undo")
        else:
            self.statusBar().showMessage("Undo not available")
    
    def _on_redo(self):
        """Handle redo action."""
        # Usar PresentationModel para redo
        if self._model.app_core and hasattr(self._model.app_core, 'redo'):
            if self._model.app_core.redo():
                self.statusBar().showMessage("Redo")
            else:
                self.statusBar().showMessage("Nothing to redo")
        else:
            self.statusBar().showMessage("Redo not available")
    
    def _on_preferences(self):
        """Handle preferences action."""
        dialog = PreferencesDialog(self)
        dialog.exec()
    
    def _on_project_settings(self):
        """Handle project settings action."""
        # Create new project if none exists
        if not self._current_project:
            self._on_new_project()
        
        if not self._current_project:
            return
            
        dialog = ProjectSettingsDialog(self._current_project, self)
        if dialog.exec():
            # Apply settings
            if self._current_project:
                self._current_project.name = dialog.get_project_name()
                self._current_project.set_bpm(dialog.get_bpm())
                self._current_project.set_pattern_length(dialog.get_pattern_length())
            
            # Update UI via TransportBar
            if hasattr(self, '_transport_bar'):
                self._transport_bar.set_bpm(dialog.get_bpm())
            
            # Update pattern combo
            pattern_length = dialog.get_pattern_length()
            index = self._pattern_combo.findText(str(pattern_length))
            if index >= 0:
                self._pattern_combo.setCurrentIndex(index)
            
            self.statusBar().showMessage("Project settings updated")
    
    def _on_rewind(self):
        """Handle rewind action."""
        if self._app_core:
            current = getattr(self._app_core, 'current_position', 0)
            rewind_to = max(0, current - 480 * 4)
            self._app_core.seek(rewind_to)
        logger.info("Rewind activated")
        self.statusBar().showMessage("Rewind")
    
    def _on_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def _on_add_track(self):
        """Handle add track action."""
        logger.info("Menu: Add Track clicked")
        
        # Usar PresentationModel en lugar de project_service
        if self._model:
            # Generate unique track name
            existing_tracks = []
            if self._model.current_project:
                existing_tracks = self._model.current_project.get_tracks()
            track_num = len(existing_tracks) + 1
            track_name = f"Track {track_num}"
            
            # Create track via PresentationModel
            track = self._model.add_track(track_name)
            
            if track:
                # Update widgets with new track list
                self._update_track_lists()
                
                logger.info(f"Track created: {track_name} (ID: {track.id})")
                self.statusBar().showMessage(f"Track '{track_name}' created")
                return
        
        self.statusBar().showMessage("Track added")
    
    def _on_delete_track(self):
        """Handle delete track action."""
        logger.info("Menu: Delete Track clicked")
        
        # Usar PresentationModel en lugar de project_service
        if self._model and self._model.current_project:
            tracks = self._model.current_project.get_tracks()
            if tracks:
                # Get selected track or first track
                track = tracks[0]
                success = self._model.remove_track(track.id)
                
                if success:
                    self._update_track_lists()
                    logger.info(f"Track deleted: {track.id}")
                    self.statusBar().showMessage(f"Track '{track.name}' deleted")
                    return
        
        self.statusBar().showMessage("Track deleted")
        ToastManager.show_info("Track deleted")
    
    def _on_audio_settings(self):
        """Handle audio settings action."""
        # Open ProjectSettingsDialog on the Audio tab
        if not self._current_project:
            self._on_new_project()
        
        if not self._current_project:
            return
            
        dialog = ProjectSettingsDialog(self._current_project, self)
        # Assuming Audio is tab 1
        tabs = dialog.findChild(QTabWidget)
        if tabs:
            tabs.setCurrentIndex(1)
            
        dialog.exec()
        self.statusBar().showMessage("Audio settings updated")

    def _add_track_instrument(self):
        """Add a new instrument track."""
        if self._model:
            new_track = self._model.add_track("Synth Track")
            if new_track:
                self._update_track_lists()
                self.statusBar().showMessage("Added Instrument Track")

    def _add_track_audio(self):
        """Add a new audio track."""
        if self._model:
            new_track = self._model.add_track("Audio Track")
            if new_track:
                self._update_track_lists()
                self.statusBar().showMessage("Added Audio Track")

    def _add_track_automation(self):
        """Add a new automation track."""
        if self._model:
            new_track = self._model.add_track("Automation Track")
            if new_track:
                self._update_track_lists()
                self.statusBar().showMessage("Added Automation Track")

    def _on_sample_rate_changed(self, sr):
        logger.info(f"Sample Rate changed to {sr}")
        self.statusBar().showMessage(f"Sample Rate: {sr} Hz")

    def _on_buffer_size_changed(self, buf):
        logger.info(f"Buffer Size changed to {buf}")
        self.statusBar().showMessage(f"Buffer Size: {buf} samples")

    def _on_duplicate_track(self):
        """Handle duplicate track action."""
        logger.info("Menu: Duplicate Track clicked")
        
        # Usar PresentationModel en lugar de project_service
        if self._model and self._model.current_project:
            tracks = self._model.current_project.get_tracks()
            if tracks:
                # Duplicate first track
                original = tracks[0]
                new_name = f"{original.name} (copy)"
                new_track = self._model.add_track(new_name)
                
                if new_track:
                    self._update_track_lists()
                    logger.info(f"Track duplicated: {original.name} -> {new_name}")
                    self.statusBar().showMessage(f"Track duplicated as '{new_name}'")
                    return
        
        self.statusBar().showMessage("Track duplicated")
    
    def _on_new_pattern(self):
        """Handle new pattern action."""
        logger.info("Menu: New Pattern clicked")
        
        if self._model and self._model.current_project:
            pattern = self._model.add_pattern("New Pattern")
            if pattern:
                self.statusBar().showMessage(f"Pattern '{pattern.name}' created")
                return
        
        self.statusBar().showMessage("Failed to create pattern")
    
    def _update_track_lists(self):
        """Update all widgets with current track list."""
        if not self._model or not self._model.current_project:
            return
        
        project = self._model.current_project
        tracks = project.get_tracks()
        track_list = [{"id": t.id, "name": t.name} for t in tracks]
        
        # Update sequencer
        if hasattr(self, '_sequencer'):
            self._sequencer.set_tracks(track_list)
        
        # Update piano roll
        if hasattr(self, '_piano_roll'):
            self._piano_roll.set_tracks(track_list)
        
        # Update mixer
        if hasattr(self, '_mixer'):
            self._mixer.set_tracks(track_list)
        
        # Update arrange view
        if hasattr(self, '_arrange_view'):
            self._arrange_view.set_tracks(track_list)
        
        logger.info(f"Updated track lists with {len(track_list)} tracks")
    
    def _on_midi_learn(self):
        """Handle MIDI learn action via DockManager."""
        self._toggle_dock("midi_learn")
        self.statusBar().showMessage("MIDI Learn toggled")
    
    def _on_metronome(self, enabled: bool):
        """Handle metronome toggle."""
        logger.info(f"Metronome toggled: enabled={enabled}")
        if self._model:
            is_enabled = self._model.toggle_metronome()
            self.statusBar().showMessage(f"Metronome {'enabled' if is_enabled else 'disabled'}")
        
    def _on_count_in(self, enabled: bool):
        """Handle count in toggle."""
        logger.info(f"Count-in toggled: enabled={enabled}")
        if self._model:
            is_enabled = self._model.toggle_count_in()
            self.statusBar().showMessage(f"Count In {'enabled' if is_enabled else 'disabled'}")
    
    def _on_loop_toggle(self, checked: bool = True):
        """Handle loop toggle."""
        logger.info(f"Loop toggled: checked={checked}")
        if self._model:
            is_enabled = self._model.toggle_loop()
            self.statusBar().showMessage(f"Loop {'enabled' if is_enabled else 'disabled'}")
    
    def _on_goto_start(self):
        """Handle go to start."""
        if self._app_core:
            self._app_core.seek(0)
        self.statusBar().showMessage("Go to start")
    
    def _on_goto_end(self):
        """Handle go to end."""
        if self._app_core:
            # Go to end of project (assuming 32 bars * 4 beats * 480 ticks)
            self._app_core.seek(32 * 4 * 480)
        self.statusBar().showMessage("Go to end")
    
    def _on_record(self):
        logger.info("Record button clicked via controller")
        if self._app_core and self._app_core.recording_handler:
            handler = self._app_core.recording_handler
            if handler.is_recording:
                handler.stop_recording()
                logger.info("Recording stopped")
                ToastManager.show_info("Recording stopped")
                self._update_record_button(False)
            else:
                if handler.start_recording():
                    logger.info("Recording started")
                    ToastManager.show_info("Recording started")
                    self._update_record_button(True)
        elif self._model:
            if self._model.is_recording:
                self._model.stop_recording()
                logger.info("Recording stopped (via model)")
                self._update_record_button(False)
            else:
                self._model.start_recording()
                logger.info("Recording started (via model)")
                self._update_record_button(True)
    
    def _on_recording_state_changed(self, is_recording: bool):
        self._update_record_button(is_recording)
        if self._status_bar_manager:
            self._status_bar_manager.update_recording(is_recording)
    
    def _update_record_button(self, recording: bool):
        """Actualizar estilo del botón de grabación."""
        if hasattr(self, '_transport_bar'):
            self._transport_bar.set_recording(recording)
    
    def _on_rename_track(self):
        """Handle rename track action."""
        logger.info("Menu: Rename Track clicked")
        if self._model and self._model.current_project:
            tracks = self._model.current_project.get_tracks()
            if tracks:
                # Select first track to rename
                self.statusBar().showMessage("Double-click track name to rename")
    
    def _on_color_track(self):
        """Handle color track action."""
        logger.info("Menu: Color Track clicked")
        self.statusBar().showMessage("Right-click track for color options")
    
    def _on_about(self):
        """Handle about action."""
        QMessageBox.about(
            self,
            "About JustBeat-DAW",
            "JustBeat-DAW v1.0\n\n"
            "An 8-bit Digital Audio Workstation\n"
            "Built with PySide6"
        )
    
    def _on_show_shortcuts(self):
        dialog = ShortcutsDialog(self._shortcut_manager, self)
        dialog.exec()
    
    def _on_shortcuts(self):
        """Show keyboard shortcuts."""
        shortcuts_text = """
        <h2>Keyboard Shortcuts</h2>
        <ul>
            <li><b>Space</b> - Play/Stop</li>
            <li><b>Ctrl+N</b> - New Project</li>
            <li><b>Ctrl+O</b> - Open Project</li>
            <li><b>Ctrl+S</b> - Save Project</li>
            <li><b>Ctrl+E</b> - Export WAV</li>
            <li><b>F11</b> - Full Screen</li>
            <li><b>Ctrl+T</b> - Add Track</li>
            <li><b>Ctrl+P</b> - New Pattern</li>
        </ul>
        """
        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts_text)
    
    def _on_track_selected(self, track_id: str) -> None:
        """Manejar selección de pista."""
        logger.info(f"Track selected in MainWindow: {track_id}")
        
        # Actualizar Piano Roll
        if hasattr(self, '_piano_roll'):
            self._piano_roll.set_track(track_id)
            
        # Actualizar Synth Panel
        if hasattr(self, '_synth_panel'):
            self._synth_panel.set_track(track_id)
            
        # Actualizar Automation Lane
        if hasattr(self, '_automation_lane'):
            self._automation_lane.set_track(track_id)
            
        # Actualizar Effect Chain
        if hasattr(self, '_effect_chain'):
            self._effect_chain.set_track(track_id)
            
        self.statusBar().showMessage(f"Selected track: {track_id}")

    # Public methods
    def get_sequencer(self) -> 'StepSequencerWidget':
        """Get the step sequencer widget."""
        return self._sequencer
    
    def get_synth_panel(self) -> 'SynthPanelWidget':
        """Get the synthesizer panel widget."""
        return self._synth_panel
    
    def get_piano_roll(self) -> 'PianoRollWidget':
        """Get the piano roll widget."""
        return self._piano_roll
    
    def get_mixer(self) -> 'MixerWidget':
        """Get the mixer widget."""
        return self._mixer
    
    def is_playing(self) -> bool:
        """Check if playback is active."""
        return self._is_playing



