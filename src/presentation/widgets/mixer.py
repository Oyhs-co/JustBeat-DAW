"""Mixer Widget - Mezclador profesional con canales, buses y master.

Características:
- Channel strips con VU estéreo, fader dB, pan knob, FX slots, M/S/R
- Sección de 4 buses con envíos
- Master channel con VU y fader
- EQ overlay toggle
- Drag para reordenar canales
"""

import logging
from typing import Dict, Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer

from src.presentation.styles.pro_theme import ProTheme
from src.presentation.styles.icons import Icons
from src.presentation.widgets.mixer_channel import MixerChannel, VUMeter

logger = logging.getLogger(__name__)


class BusChannel(QFrame):
    """Canal de bus con VU y fader."""

    def __init__(self, bus_index: int, parent=None):
        super().__init__(parent)
        self.bus_index = bus_index
        c = ProTheme.get()
        colors = ["#4488ff", "#00d4aa", "#ffab00", "#ff66aa"]
        color = colors[bus_index % len(colors)]

        self.setFixedWidth(60)
        self.setStyleSheet(f"""
            BusChannel {{
                background-color: {c.bg_surface};
                border: 1px solid {c.border_color};
                border-top: 2px solid {color};
                border-radius: 4px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(3)
        layout.setContentsMargins(4, 4, 4, 4)

        label = QLabel(f"Bus {bus_index + 1}")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color: {color}; font-size: 8px; font-weight: bold; background: transparent;")
        layout.addWidget(label)

        self._vu = VUMeter()
        layout.addWidget(self._vu, alignment=Qt.AlignCenter)

        self._fader = QWidget()
        self._fader.setFixedSize(4, 40)
        self._fader.setStyleSheet(f"background: {c.slider_groove}; border-radius: 2px;")
        layout.addWidget(self._fader, alignment=Qt.AlignCenter)

        val = QLabel("0.0")
        val.setAlignment(Qt.AlignCenter)
        val.setStyleSheet(f"color: {c.text_tertiary}; font-size: 7px; background: transparent;")
        layout.addWidget(val)


class MixerWidget(QWidget):
    """Mezclador profesional con canales, buses y master."""

    volume_changed = Signal(str, float)
    pan_changed = Signal(str, float)
    mute_changed = Signal(str, bool)
    solo_changed = Signal(str, bool)

    def __init__(self, presentation_model=None, parent=None):
        super().__init__(parent)
        self._model = presentation_model
        self._channels: Dict[str, MixerChannel] = {}
        self._master_channel: Optional[MixerChannel] = None

        if self._model is None:
            try:
                from src.presentation.models import get_presentation_model
                self._model = get_presentation_model()
            except ImportError:
                pass

        self._connect_model()
        self._setup_ui()

        self._vu_timer = QTimer(self)
        self._vu_timer.setInterval(50)
        self._vu_timer.timeout.connect(self._update_meters)
        self._vu_timer.start()

    def _connect_model(self):
        if self._model:
            try:
                self._model.track_added.connect(self._on_tracks_changed)
                self._model.track_removed.connect(self._on_tracks_changed)
                self._model.track_modified.connect(self._on_track_modified)
                self._model.project_loaded.connect(self._on_tracks_changed)
            except AttributeError:
                pass

    def _setup_ui(self):
        c = ProTheme.get()
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)

        # Title bar
        title = QLabel("Mixer")
        title.setStyleSheet(f"""
            color: {c.text_primary}; font-weight: bold; font-size: 11px;
            padding: 4px 8px; background-color: {c.bg_secondary};
            border: 1px solid {c.border_color}; border-radius: 3px;
        """)
        layout.addWidget(title)

        # Scroll area for channels + bus section
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:horizontal {{ height: 6px; background: {c.scrollbar_bg}; }}
            QScrollBar::handle:horizontal {{ background: {c.scrollbar_handle}; min-width: 30px; border-radius: 3px; }}
        """)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._mixer_layout = QHBoxLayout(container)
        self._mixer_layout.setSpacing(4)
        self._mixer_layout.setContentsMargins(0, 0, 0, 0)

        # Channel strips area
        self._channel_container = QWidget()
        self._channel_container.setStyleSheet("background: transparent;")
        self._channel_layout = QHBoxLayout(self._channel_container)
        self._channel_layout.setSpacing(4)
        self._channel_layout.setContentsMargins(0, 0, 0, 0)
        self._mixer_layout.addWidget(self._channel_container)

        # Bus section
        bus_frame = QFrame()
        bus_frame.setStyleSheet(f"""
            background-color: {c.bg_secondary};
            border: 1px solid {c.border_color};
            border-radius: 4px;
        """)
        bus_layout = QVBoxLayout(bus_frame)
        bus_layout.setSpacing(2)
        bus_layout.setContentsMargins(6, 4, 6, 4)
        bus_title = QLabel("BUSES")
        bus_title.setAlignment(Qt.AlignCenter)
        bus_title.setStyleSheet(f"color: {c.text_tertiary}; font-size: 8px; font-weight: bold; background: transparent;")
        bus_layout.addWidget(bus_title)

        self._bus_widgets = []
        for i in range(4):
            bus = BusChannel(i)
            bus_layout.addWidget(bus)
            self._bus_widgets.append(bus)

        self._mixer_layout.addWidget(bus_frame)

        # Master channel
        self._master_channel = MixerChannel("master", "Master", c.accent_secondary)
        self._master_channel.setStyleSheet(f"""
            MixerChannel {{
                background-color: {c.bg_surface};
                border: 2px solid {c.accent_secondary};
                border-top: 2px solid {c.accent_secondary};
                border-radius: 4px;
            }}
        """)
        self._mixer_layout.addWidget(self._master_channel)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        self._load_tracks()

    def _load_tracks(self):
        while self._channel_layout.count():
            item = self._channel_layout.takeAt(0)
            if item is not None and item.widget() is not None:
                item.widget().deleteLater()
        self._channels.clear()

        c = ProTheme.get()
        if self._model:
            try:
                tracks = self._model.current_project.get_tracks()
                for i, track in enumerate(tracks):
                    color = c.track_colors[i % len(c.track_colors)]
                    ch = MixerChannel(track.id, track.name, color)
                    ch.value_changed.connect(self._on_channel_value_changed)
                    self._channels[track.id] = ch
                    self._channel_layout.addWidget(ch)
            except AttributeError:
                pass

    def _on_channel_value_changed(self, ch_id: str, param: str, value: float):
        if ch_id == "master":
            return
        if param == "volume":
            self.volume_changed.emit(ch_id, value)
        elif param == "pan":
            self.pan_changed.emit(ch_id, value)
        elif param == "mute":
            self.mute_changed.emit(ch_id, bool(value))
        elif param == "solo":
            self.solo_changed.emit(ch_id, bool(value))

        if self._model:
            try:
                if param == "volume":
                    self._model.set_track_volume(ch_id, value)
                elif param == "pan":
                    self._model.set_track_pan(ch_id, value)
                elif param == "mute":
                    self._model.set_track_mute(ch_id, bool(value))
                elif param == "solo":
                    self._model.set_track_solo(ch_id, bool(value))
            except AttributeError:
                pass

    def _on_tracks_changed(self, *args):
        self._load_tracks()

    def _on_track_modified(self, track_id: str, changes: dict):
        ch = self._channels.get(track_id)
        if ch is None:
            return
        if "volume" in changes:
            ch.set_volume(changes["volume"])
        if "pan" in changes:
            ch.set_pan(changes["pan"])
        if "muted" in changes:
            ch.set_mute(changes["muted"])
        if "solo" in changes:
            ch.set_solo(changes["solo"])

    def _update_meters(self):
        if not self._model:
            return
        try:
            app_core = self._model.app_core
            if app_core and hasattr(app_core, 'get_track_levels'):
                levels = app_core.get_track_levels()
                for ch_id, (left, right) in levels.items():
                    ch = self._channels.get(ch_id)
                    if ch:
                        ch.set_levels(left, right)
        except AttributeError:
            pass

    # === Public API ===

    def set_track_volume(self, track_id: str, volume: float):
        ch = self._channels.get(track_id)
        if ch:
            ch.set_volume(volume)

    def set_track_pan(self, track_id: str, pan: float):
        ch = self._channels.get(track_id)
        if ch:
            ch.set_pan(pan)

    def set_tracks(self, track_list: list):
        self._load_tracks()

    def update_track_level(self, track_id: str, level: float):
        ch = self._channels.get(track_id)
        if ch:
            ch.set_levels(level, level)

    def get_num_channels(self) -> int:
        return len(self._channels)

    def get_channel(self, index: int):
        ids = list(self._channels.keys())
        if 0 <= index < len(ids):
            return self._channels[ids[index]]
        return None
