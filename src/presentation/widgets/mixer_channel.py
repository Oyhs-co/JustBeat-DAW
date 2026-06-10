"""MixerChannel - Canal de mezclador profesional.

VU Meter estéreo, fader con escala dB, pan knob,
FX slots, botones M/S/R, envíos a buses.
"""

import logging
import math
from typing import Optional, List, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QFrame, QMenu, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QFont

from src.presentation.styles.pro_theme import ProTheme
from src.presentation.styles.icons import Icons

logger = logging.getLogger(__name__)

_DB_SCALE = [-60, -48, -36, -24, -18, -12, -6, -3, 0, 3, 6]


def _amp_to_db(amp: float) -> float:
    if amp <= 0:
        return -float('inf')
    return 20.0 * math.log10(amp)


def _db_to_amp(db: float) -> float:
    return 10.0 ** (db / 20.0)


class VUMeter(QWidget):
    """VU Meter estéreo con gradiente LED."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(14)
        self._level_l = 0.0
        self._level_r = 0.0
        self._peak_l = 0.0
        self._peak_r = 0.0

    def set_levels(self, left: float, right: float):
        self._level_l = max(0.0, min(1.0, left))
        self._level_r = max(0.0, min(1.0, right))
        peak_decay = 0.92
        self._peak_l = max(self._peak_l * peak_decay, self._level_l)
        self._peak_r = max(self._peak_r * peak_decay, self._level_r)
        self.update()

    def paintEvent(self, event):
        c = ProTheme.get()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        half = h // 2

        painter.fillRect(self.rect(), QColor(c.meter_bg))

        for ch, level, peak in [(0, self._level_l, self._peak_l),
                                 (1, self._level_r, self._peak_r)]:
            y0 = half * ch
            mh = half - 2
            lh = int(level * mh)
            ph = int(peak * mh)

            if lh > 0:
                grad = QLinearGradient(0, y0 + mh, 0, y0)
                grad.setColorAt(0.0, QColor(c.meter_green))
                grad.setColorAt(0.55, QColor(c.meter_yellow))
                grad.setColorAt(0.85, QColor(c.meter_red))
                painter.fillRect(1, y0 + mh - lh, w - 2, lh, grad)

            if peak > 0:
                py = y0 + mh - ph
                painter.setPen(QPen(QColor(c.meter_clip), 1))
                painter.drawLine(1, py, w - 2, py)

        painter.setPen(QPen(QColor(255, 255, 255, 15), 1))
        for i in range(1, 10):
            gy = int(h * (i / 10.0))
            painter.drawLine(0, gy, w, gy)


class _PanKnob(QWidget):
    """Knob de pan circular."""

    pan_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 20)
        self._pan = 0.0

    def set_pan(self, value: float):
        self._pan = max(-1.0, min(1.0, value))
        self.update()

    def mousePressEvent(self, event):
        self._update_from_pos(event.pos().x())

    def mouseMoveEvent(self, event):
        self._update_from_pos(event.pos().x())

    def _update_from_pos(self, x: int):
        ratio = (x / self.width()) * 2.0 - 1.0
        self._pan = max(-1.0, min(1.0, ratio))
        self.update()
        self.pan_changed.emit(self._pan)

    def paintEvent(self, event):
        c = ProTheme.get()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        r = min(w, h) // 2 - 2

        painter.setPen(QPen(QColor(c.border_color), 1))
        painter.setBrush(QColor(c.bg_tertiary))
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        angle = self._pan * 60.0
        import math as m
        ex = cx + int(r * m.sin(m.radians(angle)))
        ey = cy - int(r * m.cos(m.radians(angle)))
        painter.setPen(QPen(QColor(c.accent_primary), 2))
        painter.drawLine(cx, cy, ex, ey)

        label = "C"
        if self._pan < -0.05:
            label = f"L{int(abs(self._pan) * 100)}"
        elif self._pan > 0.05:
            label = f"R{int(self._pan * 100)}"
        painter.setPen(QColor(c.text_accent))
        painter.setFont(QFont("monospace", 7))
        painter.drawText(self.rect(), Qt.AlignBottom | Qt.AlignHCenter, label)


class MixerChannel(QFrame):
    """Canal individual del mezclador profesional."""

    value_changed = Signal(str, str, float)
    remove_requested = Signal(str)
    duplicate_requested = Signal(str)
    rename_requested = Signal(str, str)
    color_changed = Signal(str, str)

    def __init__(self, channel_id: str, name: str, track_color: str = "#00d4aa",
                 channel_index: int = 0, parent=None):
        super().__init__(parent)
        self.channel_id = channel_id
        self.channel_name = name
        self._track_color = track_color
        self._channel_index = channel_index

        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setFixedWidth(72)
        self._setup_ui()

    def _setup_ui(self):
        c = ProTheme.get()
        self.setStyleSheet(f"""
            MixerChannel {{
                background-color: {c.bg_surface};
                border: 1px solid {c.border_color};
                border-top: 2px solid {self._track_color};
                border-radius: 4px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(3)
        layout.setContentsMargins(4, 4, 4, 4)

        self._name_label = QLabel(self.channel_name)
        self._name_label.setAlignment(Qt.AlignCenter)
        self._name_label.setStyleSheet(f"color: {c.text_primary}; font-size: 9px; font-weight: bold; background: transparent;")
        layout.addWidget(self._name_label)

        # VU Meters
        vu_layout = QHBoxLayout()
        vu_layout.setSpacing(2)
        self._vu_l = VUMeter()
        self._vu_r = VUMeter()
        vu_layout.addWidget(self._vu_l)
        vu_layout.addWidget(self._vu_r)
        layout.addLayout(vu_layout)

        # Fader
        fader_layout = QHBoxLayout()
        fader_layout.setSpacing(2)

        db_scale = QLabel()
        db_scale.setFixedWidth(14)
        db_scale.setStyleSheet(f"color: {c.text_tertiary}; font-size: 7px; background: transparent;")
        db_text = "\n".join(str(d) for d in _DB_SCALE)
        db_scale.setText(db_text)
        fader_layout.addWidget(db_scale)

        self._fader = QSlider(Qt.Vertical)
        self._fader.setRange(0, 1000)
        self._fader.setValue(800)
        self._fader.setInvertedAppearance(True)
        self._fader.setStyleSheet(f"""
            QSlider::groove:vertical {{
                width: 4px; background: {c.slider_groove}; border-radius: 2px;
            }}
            QSlider::handle:vertical {{
                background: {c.slider_handle}; height: 12px; width: 20px;
                margin: 0 -8px; border-radius: 2px;
                border: 1px solid {c.border_color};
            }}
            QSlider::handle:vertical:hover {{
                background: {c.text_accent};
            }}
        """)
        self._fader.valueChanged.connect(self._on_fader_changed)
        fader_layout.addWidget(self._fader)

        layout.addLayout(fader_layout)

        # dB label
        self._db_label = QLabel("0.0 dB")
        self._db_label.setAlignment(Qt.AlignCenter)
        self._db_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 8px; font-family: monospace; background: transparent;")
        layout.addWidget(self._db_label)

        # Pan knob
        self._pan = _PanKnob()
        self._pan.pan_changed.connect(lambda v: self.value_changed.emit(self.channel_id, "pan", v))
        layout.addWidget(self._pan, alignment=Qt.AlignCenter)

        # FX slots
        fx_frame = QFrame()
        fx_frame.setStyleSheet(f"background: {c.bg_tertiary}; border: 1px solid {c.border_color}; border-radius: 2px;")
        fx_layout = QVBoxLayout(fx_frame)
        fx_layout.setSpacing(1)
        fx_layout.setContentsMargins(2, 2, 2, 2)

        fx_title = QLabel("FX")
        fx_title.setAlignment(Qt.AlignCenter)
        fx_title.setStyleSheet(f"color: {c.text_tertiary}; font-size: 7px; font-weight: bold; background: transparent;")
        fx_layout.addWidget(fx_title)

        self._fx_slots: List[QPushButton] = []
        for i in range(3):
            slot = QPushButton("+")
            slot.setFixedHeight(16)
            slot.setStyleSheet(f"""
                QPushButton {{
                    background: {c.bg_surface}; color: {c.text_tertiary};
                    border: 1px solid {c.border_color}; font-size: 8px;
                    border-radius: 2px;
                }}
                QPushButton:hover {{ border-color: {c.text_accent}; color: {c.text_accent}; }}
            """)
            slot.clicked.connect(lambda checked, idx=i: self._show_fx_menu(idx))
            fx_layout.addWidget(slot)
            self._fx_slots.append(slot)

        layout.addWidget(fx_frame)

        # M/S/R buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(2)

        self._mute_btn = QPushButton("M")
        self._mute_btn.setCheckable(True)
        self._mute_btn.setFixedSize(20, 18)
        self._mute_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.bg_tertiary}; color: {c.text_tertiary};
                          border: none; font-size: 8px; font-weight: bold; border-radius: 2px; }}
            QPushButton:checked {{ background: {c.mute_bg}; color: {c.mute_color}; }}
        """)
        self._mute_btn.toggled.connect(lambda checked: self.value_changed.emit(self.channel_id, "mute", float(checked)))
        btn_layout.addWidget(self._mute_btn)

        self._solo_btn = QPushButton("S")
        self._solo_btn.setCheckable(True)
        self._solo_btn.setFixedSize(20, 18)
        self._solo_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.bg_tertiary}; color: {c.text_tertiary};
                          border: none; font-size: 8px; font-weight: bold; border-radius: 2px; }}
            QPushButton:checked {{ background: {c.solo_bg}; color: {c.solo_color}; }}
        """)
        self._solo_btn.toggled.connect(lambda checked: self.value_changed.emit(self.channel_id, "solo", float(checked)))
        btn_layout.addWidget(self._solo_btn)

        self._arm_btn = QPushButton("R")
        self._arm_btn.setCheckable(True)
        self._arm_btn.setFixedSize(20, 18)
        self._arm_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.bg_tertiary}; color: {c.text_tertiary};
                          border: none; font-size: 8px; font-weight: bold; border-radius: 2px; }}
            QPushButton:checked {{ background: {c.arm_bg}; color: {c.arm_color}; }}
        """)
        btn_layout.addWidget(self._arm_btn)

        layout.addLayout(btn_layout)

    def _on_fader_changed(self, value: int):
        norm = value / 1000.0
        self.value_changed.emit(self.channel_id, "volume", norm)
        if value == 0:
            self._db_label.setText("-inf dB")
        else:
            db = _amp_to_db(norm)
            self._db_label.setText(f"{db:.1f} dB")

    def _show_fx_menu(self, idx: int):
        c = ProTheme.get()
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {c.menu_bg}; color: {c.menu_text};
                     border: 1px solid {c.menu_border}; border-radius: 4px; padding: 4px; }}
            QMenu::item {{ padding: 4px 16px; border-radius: 2px; font-size: 9px; }}
            QMenu::item:selected {{ background: {c.menu_hover}; color: {c.text_accent}; }}
        """)
        plugins = ["Reverb", "Delay", "Chorus", "EQ", "Distortion", "Compressor", "- clear -"]
        for p in plugins:
            action = menu.addAction(p)
            action.setData(p)
        selected = menu.exec(self._fx_slots[idx].mapToGlobal(self._fx_slots[idx].rect().bottomLeft()))
        if selected:
            name = selected.data()
            if name == "- clear -":
                self._fx_slots[idx].setText("+")
            else:
                self._fx_slots[idx].setText(name)

    def set_levels(self, left: float, right: float):
        self._vu_l.set_levels(left, right)
        self._vu_r.set_levels(left, right)

    def set_volume(self, norm: float):
        self._fader.setValue(int(norm * 1000))

    def set_pan(self, value: float):
        self._pan.set_pan(value)

    def set_mute(self, muted: bool):
        self._mute_btn.setChecked(muted)

    def set_solo(self, soloed: bool):
        self._solo_btn.setChecked(soloed)

    def _add_fx_to_channel(self, fx_name: str):
        for slot in self._fx_slots:
            if slot.text() == "+":
                slot.setText(fx_name)
                break

    def _inline_rename(self):
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self, "Rename Channel", "Channel name:",
            text=self.channel_name
        )
        if ok and new_name.strip():
            self.channel_name = new_name.strip()
            self._name_label.setText(self.channel_name)
            self.rename_requested.emit(self.channel_id, self.channel_name)

    def _set_channel_color(self, color: str):
        self._track_color = color
        c = ProTheme.get()
        self.setStyleSheet(f"""
            MixerChannel {{
                background-color: {c.bg_surface};
                border: 1px solid {c.border_color};
                border-top: 2px solid {color};
                border-radius: 4px;
            }}
        """)
        self.color_changed.emit(self.channel_id, color)

    def contextMenuEvent(self, event):
        c = ProTheme.get()
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {c.menu_bg}; color: {c.menu_text};
                     border: 1px solid {c.menu_border}; border-radius: 4px; padding: 4px; }}
            QMenu::item {{ padding: 4px 16px; border-radius: 2px; font-size: 9px; }}
            QMenu::item:selected {{ background: {c.menu_hover}; color: {c.text_accent}; }}
            QMenu::submenu {{ background: {c.menu_bg}; border: 1px solid {c.menu_border};
                             border-radius: 4px; padding: 4px; }}
        """)

        fx_menu = menu.addMenu("Add FX")
        fx_menu.setIcon(Icons.EFFECTS)
        plugins = ["Reverb", "Delay", "Chorus", "EQ", "Distortion", "Compressor"]
        for p in plugins:
            action = fx_menu.addAction(p)
            action.triggered.connect(lambda checked, name=p: self._add_fx_to_channel(name))

        menu.addSeparator()
        rename = menu.addAction("Rename")
        rename.setIcon(Icons.EDIT)
        dup = menu.addAction("Duplicate Channel")
        dup.setIcon(Icons.COPY)
        menu.addSeparator()
        remove = menu.addAction("Remove Channel")
        remove.setIcon(Icons.DELETE)
        menu.addSeparator()

        colors_menu = menu.addMenu("Color")
        colors_menu.setIcon(Icons.CHECK)
        for hex_c in c.track_colors[:8]:
            color_action = colors_menu.addAction(f"\u25A0 {hex_c}")
            color_action.triggered.connect(lambda checked, col=hex_c: self._set_channel_color(col))

        action = menu.exec(event.globalPos())
        if action == rename:
            self._inline_rename()
        elif action == dup:
            self.duplicate_requested.emit(self.channel_id)
            logger.info(f"Duplicate channel {self.channel_id}")
        elif action == remove:
            self.remove_requested.emit(self.channel_id)
            logger.info(f"Remove channel {self.channel_id}")
