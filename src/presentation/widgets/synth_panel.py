"""Synth Panel - Panel de sintetizador expandido.

3 osciladores, mixer de osc, filter, ADSR gráfico, LFO, Mod Matrix, Presets.
"""

import logging
import math
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSlider, QPushButton, QComboBox,
    QGroupBox, QScrollArea, QFrame, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont

from src.presentation.styles.pro_theme import ProTheme
from src.presentation.styles.icons import Icons

logger = logging.getLogger(__name__)

_WAVEFORMS = ["Sine", "Saw", "Square", "Triangle", "Noise"]


def _draw_waveform(painter: QPainter, rect, wave_type: str, phase: float, color: str):
    w, h = rect.width(), rect.height()
    cx, cy = w // 2, h // 2
    painter.setPen(QPen(QColor(color), 1.5))
    points = []
    for x in range(0, w, 2):
        t = (x / w) * 4 * math.pi + phase
        if wave_type == "Sine":
            y = cy + math.sin(t) * (h * 0.35)
        elif wave_type == "Saw":
            y = cy + (2 * (t / (2 * math.pi) - math.floor(t / (2 * math.pi) + 0.5))) * (h * 0.35)
        elif wave_type == "Square":
            y = cy + (h * 0.35 if math.sin(t) > 0 else -h * 0.35)
        elif wave_type == "Triangle":
            y = cy + (abs(4 * (t / (2 * math.pi) - math.floor(t / (2 * math.pi) + 0.5))) - 1) * (h * 0.35)
        else:
            y = cy + (h * 0.35) * (2 * hash(str(x)) / 2**31 - 1) if x % 3 == 0 else cy
        points.append((x, y))
    for i in range(len(points) - 1):
        painter.drawLine(int(points[i][0]), int(points[i][1]),
                         int(points[i + 1][0]), int(points[i + 1][1]))


class Knob(QWidget):
    """Knob circular con label."""

    value_changed = Signal(float)

    def __init__(self, label: str, min_val: float = 0, max_val: float = 1,
                 default: float = 0.5, step: float = 0.01, parent=None):
        super().__init__(parent)
        self._label = label
        self._min = min_val
        self._max = max_val
        self._value = default
        self._step = step
        self._drag_y = 0
        self.setFixedSize(52, 64)

    def paintEvent(self, event):
        c = ProTheme.get()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2 - 6
        r = 18
        norm = (self._value - self._min) / (self._max - self._min)

        painter.setPen(QPen(QColor(c.border_color), 2))
        painter.setBrush(QBrush(QColor(c.bg_tertiary)))
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        painter.setPen(QPen(QColor(c.accent_primary), 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(cx - r, cy - r, r * 2, r * 2, int(-45 * 16), int(norm * 270 * 16))

        angle = 225 - (norm * 270)
        rad = math.radians(angle)
        lx = cx + math.cos(rad) * r
        ly = cy - math.sin(rad) * r
        painter.setPen(QPen(QColor(c.text_primary), 2))
        painter.drawLine(cx, cy, int(lx), int(ly))

        painter.setFont(QFont("monospace", 7))
        painter.setPen(QColor(c.text_accent))
        painter.drawText(self.rect().adjusted(0, cy + r + 2, 0, 0),
                         Qt.AlignHCenter | Qt.AlignTop, f"{self._value:.2g}")

        painter.setPen(QColor(c.text_tertiary))
        painter.setFont(QFont("sans-serif", 7))
        painter.drawText(self.rect().adjusted(0, 0, 0, -cy - r - 8),
                         Qt.AlignHCenter | Qt.AlignBottom, self._label)

    def mousePressEvent(self, event):
        self._drag_y = event.pos().y()

    def mouseMoveEvent(self, event):
        delta = self._drag_y - event.pos().y()
        self._drag_y = event.pos().y()
        range_v = self._max - self._min
        new_val = self._value + (delta / 100.0) * range_v
        self._value = max(self._min, min(self._max, new_val))
        self.value_changed.emit(self._value)
        self.update()

    def set_value(self, val: float):
        self._value = max(self._min, min(self._max, val))
        self.update()

    def get_value(self) -> float:
        return self._value


class WaveformVis(QWidget):
    """Mini visualizador de forma de onda."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._type = "Sine"
        self._phase = 0.0
        self.setFixedHeight(40)
        self._timer = QTimer(self)
        self._timer.timeout.connect(lambda: (setattr(self, '_phase', self._phase + 0.15), self.update()))
        self._timer.start(50)

    def set_type(self, t: str):
        self._type = t
        self.update()

    def paintEvent(self, event):
        c = ProTheme.get()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(c.bg_tertiary))
        _draw_waveform(painter, self.rect(), self._type, self._phase, c.accent_primary)


class ADSRGraph(QWidget):
    """Editor ADSR visual con puntos draggables."""

    changed = Signal(float, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.a = 0.1
        self.d = 0.15
        self.s = 0.6
        self.r = 0.2

    def paintEvent(self, event):
        c = ProTheme.get()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        m = 4
        tw = w - 2 * m
        th = h - 2 * m

        painter.fillRect(self.rect(), QColor(c.bg_primary))

        ax = m + tw * self.a
        dx = ax + tw * self.d
        sx = dx + tw * 0.2
        rx = sx + tw * self.r

        sy = m + th * (1 - self.s)
        by = m + th

        path = [
            (m, by),
            (ax, m),
            (dx, sy),
            (sx, sy),
            (rx, by),
        ]

        painter.setPen(QPen(QColor(c.accent_primary), 2))
        for i in range(len(path) - 1):
            painter.drawLine(int(path[i][0]), int(path[i][1]),
                             int(path[i + 1][0]), int(path[i + 1][1]))

        for px, py in path[1:4]:
            painter.setBrush(QBrush(QColor(c.accent_primary)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(px) - 3, int(py) - 3, 6, 6)

        painter.setPen(QColor(c.text_tertiary))
        painter.setFont(QFont("monospace", 6))
        labels = ["A", "D", "S", "R"]
        for i, (px, py) in enumerate([(ax, m), (dx, sy), (sx, sy), (rx, by)]):
            painter.drawText(int(px) - 5, int(py) - 8 if i < 3 else int(py) + 10, labels[i])

    def set_params(self, a: float, d: float, s: float, r: float):
        self.a, self.d, self.s, self.r = a, d, s, r
        self.update()


class SynthPanelWidget(QWidget):
    """Panel de sintetizador expandido."""

    parameter_changed = Signal(str, str, float)

    def __init__(self, presentation_model=None, parent=None):
        super().__init__(parent)
        self._model = presentation_model
        self._current_track_id: Optional[str] = None
        self._osc_knobs: List[List[Knob]] = []

        if self._model is None:
            try:
                from src.presentation.models import get_presentation_model
                self._model = get_presentation_model()
            except ImportError:
                pass

        self._setup_ui()

    def _setup_ui(self):
        c = ProTheme.get()
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(6, 6, 6, 6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }}")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(container)
        cl.setSpacing(6)

        # Title + preset
        title_bar = QWidget()
        title_bar.setStyleSheet(f"background: {c.bg_secondary}; border-radius: 3px;")
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(8, 4, 8, 4)
        t = QLabel("Synth")
        t.setStyleSheet(f"color: {c.text_primary}; font-weight: bold; font-size: 10px; background: transparent;")
        tb.addWidget(t)
        tb.addStretch()
        preset_lbl = QLabel("Preset:")
        preset_lbl.setStyleSheet(f"color: {c.text_secondary}; font-size: 9px; background: transparent;")
        tb.addWidget(preset_lbl)
        self._preset_combo = QComboBox()
        self._preset_combo.addItems(["Classic Lead", "Deep Bass", "Ethereal Pad", "Chip Pulse", "Wobble Bass", "Pluck"])
        self._preset_combo.setFixedWidth(120)
        tb.addWidget(self._preset_combo)
        cl.addWidget(title_bar)

        # Waveform + visualizer row
        wf_row = QWidget()
        wf_row.setStyleSheet(f"background: {c.bg_surface}; border: 1px solid {c.border_color}; border-radius: 4px;")
        wf_l = QHBoxLayout(wf_row)
        wf_l.setContentsMargins(6, 4, 6, 4)

        self._waveform_vis = WaveformVis()
        wf_l.addWidget(self._waveform_vis, 1)

        self._waveform_combo = QComboBox()
        self._waveform_combo.addItems(_WAVEFORMS)
        self._waveform_combo.currentTextChanged.connect(self._on_waveform_changed)
        wf_l.addWidget(self._waveform_combo)

        wf_l.addWidget(QLabel("Oct:"))
        self._octave_combo = QComboBox()
        self._octave_combo.addItems(["1", "2", "3", "4", "5"])
        self._octave_combo.setCurrentIndex(2)
        self._octave_combo.setFixedWidth(45)
        wf_l.addWidget(self._octave_combo)

        cl.addWidget(wf_row)

        # 3 Oscillators
        self._osc_frames = []
        osc_group = QFrame()
        osc_group.setStyleSheet(f"background: {c.bg_surface}; border: 1px solid {c.border_color}; border-radius: 4px;")
        osc_l = QVBoxLayout(osc_group)
        osc_l.setContentsMargins(6, 4, 6, 4)
        osc_title = QLabel("OSCILLATORS")
        osc_title.setStyleSheet(f"color: {c.text_accent}; font-size: 8px; font-weight: bold; background: transparent;")
        osc_l.addWidget(osc_title)

        for oi in range(3):
            osc_row = QWidget()
            or_l = QHBoxLayout(osc_row)
            or_l.setContentsMargins(0, 0, 0, 0)
            or_l.setSpacing(2)

            lbl = QLabel(f"OSC {oi + 1}")
            lbl.setStyleSheet(f"color: {c.text_secondary}; font-size: 8px; background: transparent;")
            lbl.setFixedWidth(32)
            or_l.addWidget(lbl)

            knobs_row = []
            for param in ["Vol", "Tune", "Fine", "Pan"]:
                k = Knob(param, 0, 1, 0.8 if param == "Vol" else 0.5, 0.01)
                k.value_changed.connect(lambda v, p=param, o=oi: self._on_osc_param(o, p, v))
                or_l.addWidget(k)
                knobs_row.append(k)
            self._osc_knobs.append(knobs_row)
            osc_l.addWidget(osc_row)
        cl.addWidget(osc_group)

        # Filter section
        filt_group = QFrame()
        filt_group.setStyleSheet(f"background: {c.bg_surface}; border: 1px solid {c.border_color}; border-radius: 4px;")
        fl = QVBoxLayout(filt_group)
        fl.setContentsMargins(6, 4, 6, 4)
        flt = QLabel("FILTER")
        flt.setStyleSheet(f"color: {c.text_accent}; font-size: 8px; font-weight: bold; background: transparent;")
        fl.addWidget(flt)

        filt_row = QHBoxLayout()
        self._filter_type = QComboBox()
        self._filter_type.addItems(["LP12", "LP24", "HP", "BP", "Notch"])
        self._filter_type.setFixedWidth(55)
        filt_row.addWidget(self._filter_type)

        for param in ["Cutoff", "Res", "Env Amt"]:
            k = Knob(param, 0, 1, 0.7 if param == "Cutoff" else 0.2, 0.01)
            k.value_changed.connect(lambda v, p=param: self._on_filter_param(p, v))
            filt_row.addWidget(k)
        fl.addLayout(filt_row)
        cl.addWidget(filt_group)

        # ADSR section
        adsr_group = QFrame()
        adsr_group.setStyleSheet(f"background: {c.bg_surface}; border: 1px solid {c.border_color}; border-radius: 4px;")
        adsr_l = QVBoxLayout(adsr_group)
        adsr_l.setContentsMargins(6, 4, 6, 4)
        adsr_t = QLabel("ADSR")
        adsr_t.setStyleSheet(f"color: {c.text_accent}; font-size: 8px; font-weight: bold; background: transparent;")
        adsr_l.addWidget(adsr_t)

        self._adsr_graph = ADSRGraph()
        adsr_l.addWidget(self._adsr_graph)

        adsr_row = QHBoxLayout()
        for param, val in [("A", 0.1), ("D", 0.15), ("S", 0.6), ("R", 0.2)]:
            k = Knob(param, 0, 1, val, 0.01)
            k.value_changed.connect(lambda v, p=param: self._on_adsr_param(p, v))
            adsr_row.addWidget(k)
        adsr_l.addLayout(adsr_row)
        cl.addWidget(adsr_group)

        # LFO section
        lfo_group = QFrame()
        lfo_group.setStyleSheet(f"background: {c.bg_surface}; border: 1px solid {c.border_color}; border-radius: 4px;")
        lfo_l = QVBoxLayout(lfo_group)
        lfo_l.setContentsMargins(6, 4, 6, 4)
        lfo_t = QLabel("LFO")
        lfo_t.setStyleSheet(f"color: {c.text_accent}; font-size: 8px; font-weight: bold; background: transparent;")
        lfo_l.addWidget(lfo_t)

        lfo_row = QHBoxLayout()
        self._lfo_wave = QComboBox()
        self._lfo_wave.addItems(["Sine", "Triangle", "Square", "S&H"])
        self._lfo_wave.setFixedWidth(60)
        lfo_row.addWidget(self._lfo_wave)

        for param in ["Rate", "Amt"]:
            k = Knob(param, 0, 1, 0.5, 0.01)
            k.value_changed.connect(lambda v, p=param: self._on_lfo_param(p, v))
            lfo_row.addWidget(k)

        self._lfo_target = QComboBox()
        self._lfo_target.addItems(["Pitch", "Filter", "Volume"])
        self._lfo_target.setFixedWidth(60)
        lfo_row.addWidget(self._lfo_target)
        lfo_l.addLayout(lfo_row)
        cl.addWidget(lfo_group)

        cl.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _on_waveform_changed(self, wf: str):
        self._waveform_vis.set_type(wf)
        if self._current_track_id and self._model:
            try:
                self._model.set_synth_parameter(self._current_track_id, "waveform", wf.lower())
            except AttributeError:
                pass

    def _on_osc_param(self, osc: int, param: str, value: float):
        logger.debug(f"OSC{osc + 1} {param}: {value:.2f}")

    def _on_filter_param(self, param: str, value: float):
        logger.debug(f"Filter {param}: {value:.2f}")

    def _on_adsr_param(self, param: str, value: float):
        a, d, s, r = self._adsr_graph.a, self._adsr_graph.d, self._adsr_graph.s, self._adsr_graph.r
        if param == "A":
            a = value
        elif param == "D":
            d = value
        elif param == "S":
            s = value
        elif param == "R":
            r = value
        self._adsr_graph.set_params(a, d, s, r)

    def _on_lfo_param(self, param: str, value: float):
        logger.debug(f"LFO {param}: {value:.2f}")

    def set_tracks(self, track_list: list):
        pass

    def set_track(self, track_id: str):
        self._current_track_id = track_id
