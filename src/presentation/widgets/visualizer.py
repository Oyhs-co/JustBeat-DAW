"""Audio Visualizer Widget - 3 modos: Waveform, Spectrum, Phase.

Usa pyqtgraph para rendering en tiempo real con colores dinámicos.
"""

import logging
import numpy as np
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

import pyqtgraph as pg

from src.presentation.styles.pro_theme import ProTheme
from src.presentation.styles.icons import Icons

logger = logging.getLogger(__name__)
pg.setConfigOptions(antialias=True)


class VisualizerWidget(QWidget):
    """Visualizador de audio con 3 modos: Waveform, Spectrum, Phase."""

    MODES = ["Waveform", "Spectrum", "Phase"]
    REFRESH_MS = 40
    BAR_COUNT = 32

    def __init__(self, presentation_model=None, parent=None):
        super().__init__(parent)
        self._model = presentation_model
        self._mode = 0
        self._is_playing = False
        self._frozen = False
        self._waveform_data = np.zeros(256)
        self._bar_levels = np.zeros(self.BAR_COUNT)
        self._fft_data = np.zeros(self.BAR_COUNT // 2)
        self._phase_x = np.zeros(128)
        self._phase_y = np.zeros(128)

        if self._model is None:
            try:
                from src.presentation.models import get_presentation_model
                self._model = get_presentation_model()
            except ImportError:
                pass

        self._setup_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_data)

    def _setup_ui(self):
        c = ProTheme.get()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header
        header = QWidget()
        header.setStyleSheet(f"background-color: {c.bg_secondary}; border-radius: 3px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(6, 2, 6, 2)

        title = QLabel("Visualizer")
        title.setStyleSheet(f"color: {c.text_primary}; font-weight: bold; font-size: 10px; background: transparent;")
        h_layout.addWidget(title)

        h_layout.addStretch()

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(self.MODES)
        self._mode_combo.setFixedWidth(90)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        h_layout.addWidget(self._mode_combo)

        self._freeze_btn = QPushButton()
        self._freeze_btn.setIcon(Icons.PAUSE)
        self._freeze_btn.setCheckable(True)
        self._freeze_btn.setFixedSize(22, 22)
        self._freeze_btn.toggled.connect(self._toggle_freeze)
        h_layout.addWidget(self._freeze_btn)

        layout.addWidget(header)

        # Plot
        self._plot = pg.GraphicsLayoutWidget()
        self._plot.setBackground(c.bg_primary)
        self._plot.setMinimumHeight(100)

        self._axis = self._plot.addPlot(title="")
        self._axis.hideAxis("left")
        self._axis.hideAxis("bottom")
        self._axis.setMouseEnabled(x=False, y=False)
        self._axis.setRange(yRange=[-1, 1])

        self._curve = self._axis.plot(pen=pg.mkPen(c.accent_primary, width=1.5), fillLevel=0, brush=c.accent_primary.replace(")", ", 30)").replace("rgb", "rgba") if "rgba" not in c.accent_primary else c.accent_primary)

        self._bar_graph = pg.BarGraphItem(
            x=np.arange(self.BAR_COUNT), height=np.zeros(self.BAR_COUNT),
            width=0.8, brush=c.accent_primary, pen=None,
        )
        self._axis.addItem(self._bar_graph)
        self._bar_graph.hide()

        layout.addWidget(self._plot)

    def _on_mode_changed(self, idx: int):
        self._mode = idx
        if idx == 0:
            self._curve.show()
            self._bar_graph.hide()
            self._axis.setRange(yRange=[-1, 1])
        elif idx == 1:
            self._curve.hide()
            self._bar_graph.show()
            self._axis.setRange(yRange=[0, 1])
        else:
            self._curve.show()
            self._bar_graph.hide()
            self._axis.setRange(yRange=[-1, 1])

    def _toggle_freeze(self, frozen: bool):
        self._frozen = frozen

    def _update_data(self):
        if self._frozen or not self._is_playing:
            return
        if not self._model:
            return

        try:
            levels = self._model.get_audio_levels() if hasattr(self._model, 'get_audio_levels') else (0.0, 0.0)
            waveform = self._model.get_waveform_data(256) if hasattr(self._model, 'get_waveform_data') else None

            if waveform:
                left, _ = waveform
                if left is not None and len(left) > 0:
                    self._waveform_data = np.array(left, dtype=np.float32)

            if self._mode == 0:
                x = np.linspace(0, len(self._waveform_data), len(self._waveform_data))
                self._curve.setData(x, self._waveform_data)
            elif self._mode == 1:
                bar_val = max(abs(levels[0]), abs(levels[1])) if levels else 0.0
                target = np.full(self.BAR_COUNT, bar_val)
                for i in range(self.BAR_COUNT):
                    decay = 1.0 - (i / self.BAR_COUNT)
                    target[i] = target[i] * (0.3 + 0.7 * decay)
                self._bar_levels = self._bar_levels * 0.7 + target * 0.3
                self._bar_graph.setOpts(height=np.abs(self._bar_levels))
            else:
                t = np.linspace(0, 2 * np.pi, 128)
                self._phase_x = np.sin(t + self._phase_x.mean() if self._phase_x.any() else 0) * self._waveform_data[:128]
                self._phase_y = np.cos(t + self._phase_y.mean() if self._phase_y.any() else 0) * self._waveform_data[:128]
                self._curve.setData(self._phase_x[:64], self._phase_y[:64])
        except (AttributeError, IndexError, TypeError):
            pass

    def set_playing(self, playing: bool):
        self._is_playing = playing
        if playing and not self._timer.isActive():
            self._timer.start(self.REFRESH_MS)
        elif not playing:
            self._timer.stop()
            self._waveform_data = np.zeros(256)
            self._curve.setData([], [])
            self._bar_graph.setOpts(height=np.zeros(self.BAR_COUNT))

    def set_levels(self, levels: list):
        pass

    def set_waveform(self, waveform: list):
        pass


class AudioVisualizer(QWidget):
    """Contenedor principal del visualizador."""

    def __init__(self, presentation_model=None, parent=None):
        super().__init__(parent)
        self._model = presentation_model
        if self._model is None:
            try:
                from src.presentation.models import get_presentation_model
                self._model = get_presentation_model()
            except ImportError:
                pass
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._visualizer = VisualizerWidget(self._model)
        layout.addWidget(self._visualizer)

    def set_playing(self, playing: bool):
        self._visualizer.set_playing(playing)


LevelMeter = VisualizerWidget
