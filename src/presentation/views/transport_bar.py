import logging

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QSpinBox,
    QToolButton, QSlider
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from src.application.app_core import AppCore

logger = logging.getLogger(__name__)


class TransportBarView(QWidget):
    play_toggled = Signal(bool)
    stop_triggered = Signal()
    record_toggled = Signal(bool)
    bpm_changed = Signal(int)
    metronome_toggled = Signal(bool)
    loop_toggled = Signal(bool)

    def __init__(self, app_core: AppCore, parent=None):
        super().__init__(parent)
        self._app_core = app_core
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        self._play_btn = QPushButton("\u25B6")
        self._play_btn.setFixedSize(36, 28)
        self._play_btn.setCheckable(True)
        self._play_btn.setToolTip("Play / Pause")

        self._stop_btn = QPushButton("\u25A0")
        self._stop_btn.setFixedSize(36, 28)
        self._stop_btn.setToolTip("Stop")

        self._record_btn = QPushButton("\u25CF")
        self._record_btn.setFixedSize(36, 28)
        self._record_btn.setCheckable(True)
        self._record_btn.setToolTip("Record")

        self._metronome_btn = QPushButton("M")
        self._metronome_btn.setFixedSize(36, 28)
        self._metronome_btn.setCheckable(True)
        self._metronome_btn.setToolTip("Metronome")

        self._loop_btn = QPushButton("\u21BA")
        self._loop_btn.setFixedSize(36, 28)
        self._loop_btn.setCheckable(True)
        self._loop_btn.setToolTip("Loop")

        layout.addWidget(self._play_btn)
        layout.addWidget(self._stop_btn)
        layout.addWidget(self._record_btn)
        layout.addWidget(self._metronome_btn)
        layout.addWidget(self._loop_btn)

        layout.addSpacing(12)

        bpm_label = QLabel("BPM:")
        self._bpm_spin = QSpinBox()
        self._bpm_spin.setRange(20, 300)
        self._bpm_spin.setValue(120)
        self._bpm_spin.setFixedWidth(60)
        layout.addWidget(bpm_label)
        layout.addWidget(self._bpm_spin)

        layout.addSpacing(12)

        self._position_label = QLabel("1.1.1.0")
        self._position_label.setFixedWidth(100)
        layout.addWidget(self._position_label)

        layout.addStretch()

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(80)
        self._volume_slider.setFixedWidth(80)
        layout.addWidget(QLabel("Vol:"))
        layout.addWidget(self._volume_slider)

    def _connect_signals(self):
        self._play_btn.toggled.connect(self.play_toggled.emit)
        self._stop_btn.clicked.connect(self.stop_triggered.emit)
        self._record_btn.toggled.connect(self.record_toggled.emit)
        self._metronome_btn.toggled.connect(self.metronome_toggled.emit)
        self._loop_btn.toggled.connect(self.loop_toggled.emit)
        self._bpm_spin.valueChanged.connect(self.bpm_changed.emit)

    def set_playing(self, playing: bool):
        self._play_btn.setChecked(playing)

    def set_recording(self, recording: bool):
        self._record_btn.setChecked(recording)

    def set_bpm(self, bpm: int):
        self._bpm_spin.setValue(bpm)

    def set_position(self, tick: int):
        bar = tick // (480 * 4) + 1
        beat = (tick // 480) % 4 + 1
        sixteenth = (tick // 120) % 4 + 1
        self._position_label.setText(f"{bar}.{beat}.{sixteenth}.0")

    def set_metronome(self, enabled: bool):
        self._metronome_btn.setChecked(enabled)

    def set_loop(self, enabled: bool):
        self._loop_btn.setChecked(enabled)
