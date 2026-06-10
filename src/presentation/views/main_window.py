import logging

from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QWidget, QVBoxLayout,
    QApplication, QStatusBar, QMenu
)
from PySide6.QtCore import Qt, QByteArray

from src.presentation.views.transport_bar import TransportBarView
from src.presentation.widgets.sequencer import StepSequencerWidget
from src.presentation.widgets.piano_roll import PianoRollWidget
from src.presentation.widgets.mixer import MixerWidget
from src.presentation.widgets.browser import BrowserWidget
from src.presentation.widgets.arrange_view import ArrangeViewWidget
from src.presentation.widgets.effect_chain import EffectChainWidget
from src.presentation.widgets.automation_lane import AutomationLane
from src.presentation.widgets.synth_panel import SynthPanelWidget
from src.presentation.models.presentation_model import PresentationModel
from src.application.app_core import AppCore

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, app_core: AppCore, parent=None):
        super().__init__(parent)
        self._app_core = app_core
        self._presentation = PresentationModel(app_core)

        self._setup_window()
        self._create_menu_bar()
        self._create_central_widget()
        self._create_docks()
        self._create_status_bar()
        self._connect_signals()
        self._restore_layout()

    def _setup_window(self):
        self.setWindowTitle("JustBeat-DAW")
        self.setMinimumSize(1200, 700)
        self.resize(1600, 900)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("&New Project", self._on_new_project, "Ctrl+N")
        file_menu.addAction("&Open...", self._on_open_project, "Ctrl+O")
        file_menu.addAction("&Save", self._on_save_project, "Ctrl+S")
        file_menu.addAction("Save &As...", self._on_save_as, "Ctrl+Shift+S")
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close, "Ctrl+Q")

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction("&Undo", self._on_undo, "Ctrl+Z")
        edit_menu.addAction("&Redo", self._on_redo, "Ctrl+Y")

        self._view_menu = menu_bar.addMenu("&View")
        self._dock_actions = {}
        self._view_menu.addSeparator()
        self._view_menu.addAction("&Preferences...", self._on_preferences)

        transport_menu = menu_bar.addMenu("&Transport")
        transport_menu.addAction("&Play", self._on_play, "Space")
        transport_menu.addAction("&Stop", self._on_stop, "Shift+Space")
        transport_menu.addAction("&Record", self._on_record, "Ctrl+R")

        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction("&About", self._on_about)
        help_menu.addAction("About &Qt", QApplication.instance().aboutQt)

    def _create_central_widget(self):
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._transport_bar = TransportBarView(self._app_core)
        layout.addWidget(self._transport_bar)
        self.setCentralWidget(central)

    def _create_docks(self):
        self._sequencer_dock = self._make_dock(
            "Sequencer", StepSequencerWidget, Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self._piano_roll_dock = self._make_dock(
            "Piano Roll", PianoRollWidget,
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self._mixer_dock = self._make_dock(
            "Mixer", MixerWidget,
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self._browser_dock = self._make_dock(
            "Browser", BrowserWidget,
            Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self._arrange_dock = self._make_dock(
            "Arrangement", ArrangeViewWidget,
            Qt.DockWidgetArea.TopDockWidgetArea
        )
        self._synth_dock = self._make_dock(
            "Synthesizer", SynthPanelWidget,
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self._effects_dock = self._make_dock(
            "Effects", EffectChainWidget,
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self._automation_dock = self._make_dock(
            "Automation", AutomationLane,
            Qt.DockWidgetArea.BottomDockWidgetArea
        )

        self.tabifyDockWidget(self._piano_roll_dock, self._sequencer_dock)
        self.tabifyDockWidget(self._piano_roll_dock, self._automation_dock)
        self.tabifyDockWidget(self._mixer_dock, self._synth_dock)
        self.tabifyDockWidget(self._mixer_dock, self._effects_dock)

        self._dock_widgets = {
            "sequencer": self._sequencer_dock,
            "piano_roll": self._piano_roll_dock,
            "mixer": self._mixer_dock,
            "browser": self._browser_dock,
            "arrange": self._arrange_dock,
            "synth": self._synth_dock,
            "effects": self._effects_dock,
            "automation": self._automation_dock,
        }

    def _make_dock(self, title, widget_factory, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(f"{title}Dock")
        dock.setWidget(widget_factory() if callable(widget_factory) else widget_factory)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(area, dock)

        action = dock.toggleViewAction()
        action.setText(f"&{title}")
        self._dock_actions[title.lower()] = action
        self._view_menu.addAction(action)
        return dock

    def _create_status_bar(self):
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

    def _connect_signals(self):
        self._presentation.project_loaded.connect(self._on_project_loaded)
        self._presentation.position_changed.connect(self._on_position_changed)

        self._transport_bar.play_toggled.connect(self._on_play_toggle)
        self._transport_bar.stop_triggered.connect(self._on_stop)
        self._transport_bar.record_toggled.connect(self._on_record_toggle)
        self._transport_bar.bpm_changed.connect(self._on_bpm_changed)
        self._transport_bar.metronome_toggled.connect(self._on_metronome_toggle)
        self._transport_bar.loop_toggled.connect(self._on_loop_toggle)

    def _restore_layout(self):
        try:
            settings = self._app_core.get_state("window.layout")
            if settings:
                state = QByteArray.fromBase64(settings.encode())
                self.restoreState(state)
        except Exception:
            pass

    def _save_layout(self):
        try:
            state = self.saveState().toBase64().data().decode()
            self._app_core.set_state("window.layout", state)
        except Exception:
            pass

    def closeEvent(self, event):
        self._save_layout()
        super().closeEvent(event)

    def _on_new_project(self):
        self._presentation.new_project()

    def _on_open_project(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "JustBeat Projects (*.justbeat)"
        )
        if path:
            from pathlib import Path
            self._presentation.load_project(Path(path))

    def _on_save_project(self):
        self._presentation.save_project()

    def _on_save_as(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", "", "JustBeat Projects (*.justbeat)"
        )
        if path:
            from pathlib import Path
            self._presentation.save_project(Path(path))

    def _on_undo(self):
        self._app_core.undo()

    def _on_redo(self):
        self._app_core.redo()

    def _on_play(self):
        self._app_core.play()

    def _on_play_toggle(self, playing: bool):
        if playing:
            self._app_core.play()
        else:
            self._app_core.stop()

    def _on_stop(self):
        self._app_core.stop()
        self._transport_bar.set_playing(False)

    def _on_record(self):
        logger.info("Record toggled")

    def _on_record_toggle(self, recording: bool):
        logger.info(f"Record: {recording}")

    def _on_bpm_changed(self, bpm: int):
        pass

    def _on_metronome_toggle(self, enabled: bool):
        pass

    def _on_loop_toggle(self, enabled: bool):
        pass

    def _on_preferences(self):
        from src.presentation.widgets.settings_dialog import PreferencesDialog
        dialog = PreferencesDialog(self._app_core, self)
        if dialog.exec():
            self._status.showMessage("Preferences saved", 3000)

    def _on_about(self):
        from src.presentation.widgets.about_dialog import AboutDialog
        AboutDialog(self).exec()

    def _on_project_loaded(self):
        self._status.showMessage("Project loaded", 3000)

    def _on_position_changed(self, tick: int):
        try:
            self._transport_bar.set_position(tick)
        except Exception:
            pass
