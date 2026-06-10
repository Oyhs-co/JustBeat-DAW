"""Virtual Keyboard - Teclado MIDI virtual expandido.

5 octavas, velocity-sensitive, sustain pedal, chord memory, arpeggiator.
"""

import logging
import math
import random
from typing import Optional, List, Dict, Set

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QCheckBox, QSpinBox, QComboBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QMouseEvent, QBrush

from src.presentation.styles.pro_theme import ProTheme
from src.presentation.styles.icons import Icons

logger = logging.getLogger(__name__)

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_WHITE_KEYS = {0, 2, 4, 5, 7, 9, 11}
_BLACK_KEY_WIDTH = 22
_WHITE_KEY_WIDTH = 36
_WHITE_KEY_HEIGHT = 100
_BLACK_KEY_HEIGHT = 60


class KeyWidget(QWidget):
    """Tecla individual pintada a medida."""

    pressed = Signal(int, int)
    released = Signal(int)

    def __init__(self, pitch: int, is_black: bool, parent=None):
        super().__init__(parent)
        self.pitch = pitch
        self.is_black = is_black
        self._pressed = False
        self._vel = 100

        w = _BLACK_KEY_WIDTH if is_black else _WHITE_KEY_WIDTH
        h = _BLACK_KEY_HEIGHT if is_black else _WHITE_KEY_HEIGHT
        self.setFixedSize(w, h)

    def paintEvent(self, event):
        c = ProTheme.get()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if self.is_black:
            bg = QColor("#222") if not self._pressed else QColor(c.accent_primary).darker(120)
            painter.setBrush(QBrush(bg))
            painter.setPen(QPen(QColor("#111"), 1))
            painter.drawRect(0, 0, w, h)
            if self._pressed:
                glow = QColor(c.accent_primary)
                glow.setAlpha(60)
                painter.setBrush(QBrush(glow))
                painter.drawRect(1, 1, w - 2, h - 2)
        else:
            bg = QColor("#e8e8e8") if not self._pressed else QColor(c.accent_primary).lighter(150)
            painter.setBrush(QBrush(bg))
            painter.setPen(QPen(QColor("#bbb"), 1))
            painter.drawRect(0, 0, w, h)

            if self.pitch % 12 == 0:
                painter.setPen(QColor("#888"))
                painter.setFont(QFont("monospace", 6))
                name = f"{_NOTE_NAMES[self.pitch % 12]}{(self.pitch // 12) - 1}"
                painter.drawText(2, h - 4, name)

    def mousePressEvent(self, event: QMouseEvent):
        self._pressed = True
        vel = max(30, min(127, int(event.pos().y() * 127 / self.height())))
        self._vel = vel
        self.update()
        self.pressed.emit(self.pitch, vel)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._pressed = False
        self.update()
        self.released.emit(self.pitch)

    def set_pressed(self, p: bool):
        self._pressed = p
        self.update()


class VirtualKeyboard(QWidget):
    """Teclado MIDI virtual con 5 octavas y funciones avanzadas."""

    note_on = Signal(int, int)
    note_off = Signal(int)

    def __init__(self, presentation_model=None, parent=None):
        super().__init__(parent)
        self._model = presentation_model
        self._octave = 3
        self._octaves = 3
        self._keys: Dict[int, KeyWidget] = {}
        self._pressed_notes: Set[int] = set()
        self._sustain = False
        self._sustained_notes: Set[int] = set()
        self._chord_memory: List[List[int]] = [[] for _ in range(8)]

        # Arpeggiator
        self._arp_enabled = False
        self._arp_notes: List[int] = []
        self._arp_index = 0
        self._arp_direction = 0
        self._arp_octave_range = 1
        self._arp_timer = QTimer(self)
        self._arp_timer.timeout.connect(self._arp_step)

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
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)

        # Top controls
        controls = QWidget()
        controls.setStyleSheet(f"background: {c.bg_secondary}; border-radius: 3px;")
        ctrl_l = QHBoxLayout(controls)
        ctrl_l.setContentsMargins(6, 3, 6, 3)
        ctrl_l.setSpacing(4)

        title = QLabel("Keys")
        title.setStyleSheet(f"color: {c.text_primary}; font-weight: bold; font-size: 10px; background: transparent;")
        ctrl_l.addWidget(title)

        # Octave controls
        oct_down = QPushButton()
        oct_down.setIcon(Icons.MINUS)
        oct_down.setFixedSize(20, 20)
        oct_down.clicked.connect(self._octave_down)
        ctrl_l.addWidget(oct_down)

        self._oct_label = QLabel(f"C{self._octave + 1}")
        self._oct_label.setStyleSheet(f"color: {c.text_accent}; font-size: 10px; font-weight: bold; background: transparent;")
        self._oct_label.setFixedWidth(30)
        ctrl_l.addWidget(self._oct_label)

        oct_up = QPushButton()
        oct_up.setIcon(Icons.PLUS)
        oct_up.setFixedSize(20, 20)
        oct_up.clicked.connect(self._octave_up)
        ctrl_l.addWidget(oct_up)

        ctrl_l.addStretch()

        # Sustain
        self._sustain_btn = QPushButton(" Sust")
        self._sustain_btn.setIcon(Icons.CHECK)
        self._sustain_btn.setCheckable(True)
        self._sustain_btn.setFixedHeight(20)
        self._sustain_btn.toggled.connect(self._toggle_sustain)
        ctrl_l.addWidget(self._sustain_btn)

        # Arpeggiator
        self._arp_btn = QPushButton(" Arp")
        self._arp_btn.setIcon(Icons.SHUFFLE)
        self._arp_btn.setCheckable(True)
        self._arp_btn.setFixedHeight(20)
        self._arp_btn.toggled.connect(self._toggle_arp)
        ctrl_l.addWidget(self._arp_btn)

        ctrl_l.addWidget(self._make_combo(["Up", "Down", "Up/Down", "Random"], "Up", 55))
        ctrl_l.addWidget(self._make_spin(1, 4, 1, 30))

        layout.addWidget(controls)

        # Keyboard scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }}")

        self._keyboard_widget = QWidget()
        self._keyboard_widget.setFixedHeight(_WHITE_KEY_HEIGHT)
        self._rebuild_keyboard()
        scroll.setWidget(self._keyboard_widget)

        layout.addWidget(scroll)

        # Chord memory buttons
        chord_row = QWidget()
        chord_row.setStyleSheet(f"background: {c.bg_secondary}; border-radius: 3px;")
        chord_l = QHBoxLayout(chord_row)
        chord_l.setContentsMargins(6, 2, 6, 2)
        chord_l.setSpacing(2)

        chord_l.addWidget(QLabel(" Chords:"))
        for i in range(8):
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(24, 20)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self._chord_trigger(idx))
            chord_l.addWidget(btn)

        chord_l.addStretch()
        self._chord_learn_btn = QPushButton("Learn")
        self._chord_learn_btn.setCheckable(True)
        self._chord_learn_btn.setFixedHeight(20)
        self._chord_learn_btn.toggled.connect(self._toggle_chord_learn)
        chord_l.addWidget(self._chord_learn_btn)

        layout.addWidget(chord_row)

    def _make_combo(self, items, default, width):
        combo = QComboBox()
        combo.addItems(items)
        combo.setCurrentText(default)
        combo.setFixedWidth(width)
        return combo

    def _make_spin(self, min_v, max_v, default, width):
        spin = QSpinBox()
        spin.setRange(min_v, max_v)
        spin.setValue(default)
        spin.setFixedWidth(width)
        return spin

    def _rebuild_keyboard(self):
        for w in self._keyboard_widget.findChildren(KeyWidget):
            w.deleteLater()
        self._keys.clear()

        layout = QHBoxLayout(self._keyboard_widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        for oct in range(self._octave, self._octave + self._octaves):
            for note in range(12):
                pitch = oct * 12 + note
                if pitch > 127:
                    break
                is_black = note not in _WHITE_KEYS
                key = KeyWidget(pitch, is_black)
                key.pressed.connect(self._on_key_pressed)
                key.released.connect(self._on_key_released)
                self._keys[pitch] = key

                if is_black:
                    layout.addWidget(key)
                else:
                    layout.addWidget(key)

    def _on_key_pressed(self, pitch: int, vel: int):
        self._pressed_notes.add(pitch)
        self.note_on.emit(pitch, vel)

        if self._chord_learn_btn.isChecked():
            self._learn_chord_note(pitch)

        if self._arp_enabled:
            if pitch not in self._arp_notes:
                self._arp_notes.append(pitch)
                self._arp_notes.sort()
            if not self._arp_timer.isActive():
                self._arp_index = 0
                self._arp_timer.start(150)

    def _on_key_released(self, pitch: int):
        self._pressed_notes.discard(pitch)
        if self._sustain:
            self._sustained_notes.add(pitch)
        else:
            self.note_off.emit(pitch)
            if self._arp_enabled:
                self._arp_notes = [n for n in self._arp_notes if n != pitch]
                if not self._arp_notes:
                    self._arp_timer.stop()

    def key_press(self, pitch: int, vel: int = 100):
        key = self._keys.get(pitch)
        if key:
            key.set_pressed(True)
            self._on_key_pressed(pitch, vel)

    def key_release(self, pitch: int):
        key = self._keys.get(pitch)
        if key:
            key.set_pressed(False)
            self._on_key_released(pitch)

    def _octave_down(self):
        if self._octave > 0:
            self._octave -= 1
            self._oct_label.setText(f"C{self._octave + 1}")
            self._rebuild_keyboard()

    def _octave_up(self):
        if self._octave + self._octaves < 10:
            self._octave += 1
            self._oct_label.setText(f"C{self._octave + 1}")
            self._rebuild_keyboard()

    def _toggle_sustain(self, on: bool):
        self._sustain = on
        if not on:
            for p in self._sustained_notes:
                self.note_off.emit(p)
            self._sustained_notes.clear()

    def _toggle_arp(self, on: bool):
        self._arp_enabled = on
        if not on:
            self._arp_timer.stop()
            self._arp_notes.clear()

    def _arp_step(self):
        if not self._arp_notes:
            self._arp_timer.stop()
            return
        idx = self._arp_index % len(self._arp_notes)
        pitch = self._arp_notes[idx]
        for p in self._pressed_notes:
            self.note_off.emit(p)
        self.note_on.emit(pitch, 100)
        self._arp_index += 1

    def _learn_chord_note(self, pitch: int):
        pass

    def _toggle_chord_learn(self, on: bool):
        pass

    def _chord_trigger(self, idx: int):
        for p in self._chord_memory[idx]:
            self.note_on.emit(p, 100)

    def set_octave(self, octave: int):
        if 1 <= octave <= 8:
            self._octave = octave
            self._oct_label.setText(f"C{self._octave + 1}")

    def all_notes_off(self):
        for p in list(self._pressed_notes):
            self.note_off.emit(p)
        self._pressed_notes.clear()
        self._arp_timer.stop()


KeyboardWidget = VirtualKeyboard
