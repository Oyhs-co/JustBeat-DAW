"""Step Sequencer Widget - Grid-based step sequencer profesional.

Características:
- Drag para dibujar pasos activos/inactivos
- Right-click para borrar
- Colores por velocity (más brillo = más fuerte)
- Parámetros por step: Chance, Slide, Repeat, Offset
- Selector de patrón
- Playhead con glow pulsante
- Grid responsive con scroll
"""

import logging
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QSizePolicy, QComboBox,
    QGridLayout, QScrollArea, QFrame, QSlider,
    QCheckBox, QSpinBox, QMenu
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QMouseEvent

from src.presentation.styles.pro_theme import ProTheme
from src.presentation.styles.icons import Icons


logger = logging.getLogger(__name__)


@dataclass
class StepParams:
    """Parámetros avanzados por step."""
    chance: int = 100        # 0-100%
    slide: bool = False      # portamento al siguiente step
    repeat: int = 1          # subdivisiones internas (1-4)
    offset: int = 0          # micro-timing en ticks (-120 a +120)
    velocity: int = 100      # 0-127 MIDI velocity


def _velocity_color(velocity: int, c) -> str:
    """Generar color hex basado en velocity MIDI."""
    ratio = velocity / 127.0
    r_base, g_base, b_base = _hex_to_rgb(c.grid_active)
    r = int(r_base * ratio + 30 * (1 - ratio))
    g = int(g_base * ratio + 30 * (1 - ratio))
    b = int(b_base * ratio + 40 * (1 - ratio))
    return f"#{r:02x}{g:02x}{b:02x}"


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _blend_colors(c1: str, c2: str, ratio: float) -> str:
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * ratio)
    g = int(g1 + (g2 - g1) * ratio)
    b = int(b1 + (b2 - b1) * ratio)
    return f"#{r:02x}{g:02x}{b:02x}"


class StepButton(QPushButton):
    """Botón individual de step con soporte para velocity y hover param."""

    clicked_step = Signal(int, int, bool, int)  # track, step, active, velocity
    right_clicked = Signal(int, int)             # track, step

    def __init__(self, track_index: int, step_index: int, parent=None):
        super().__init__(parent)
        self.track_index = track_index
        self.step_index = step_index
        self.is_active = False
        self.is_beat = (step_index % 4 == 0)
        self._velocity = 100
        self._params = StepParams()
        self._is_playhead = False
        self._drag_entered = False

        self.setObjectName("stepButton")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(14, 20)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self._update_style()
        self.clicked.connect(self._on_clicked)

    def set_velocity(self, vel: int):
        self._velocity = max(1, min(127, vel))
        self._update_style()

    def get_velocity(self) -> int:
        return self._velocity

    def set_params(self, params: StepParams):
        self._params = params
        self._update_style()

    def get_params(self) -> StepParams:
        return self._params

    def set_playhead(self, active: bool):
        self._is_playhead = active
        self._update_style()

    def set_active(self, active: bool, velocity: Optional[int] = None):
        self.is_active = active
        if velocity is not None:
            self._velocity = max(1, min(127, velocity))
        self._update_style()

    def _on_clicked(self):
        self.is_active = not self.is_active
        if self.is_active:
            self._velocity = 100
        self._update_style()
        self.clicked_step.emit(self.track_index, self.step_index, self.is_active, self._velocity)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            if self.is_active:
                self.is_active = False
                self._update_style()
                self.right_clicked.emit(self.track_index, self.step_index)
            event.accept()
            return
        super().mousePressEvent(event)

    def _update_style(self):
        c = ProTheme.get()
        if self.is_active:
            bg = _velocity_color(self._velocity, c)
            border = c.border_accent if self._is_playhead else _blend_colors(bg, "#ffffff", 0.3)
            bw = "2px" if self._is_playhead else "1px"
            glow = f"0 0 4px {bg}" if self._is_playhead else "none"
        else:
            if self._is_playhead:
                bg = "#2a2a3d"
                border = c.grid_playhead
                bw = "2px"
                glow = f"0 0 6px {c.grid_playhead_glow}"
            else:
                bg = "#1a1a22" if self.is_beat else "#16161e"
                border = "#3a3a4a" if self.is_beat else "#2a2a3a"
                bw = "1px"
                glow = "none"

        qss = f"""
        QPushButton {{
            background-color: {bg};
            border: {bw} solid {border};
            border-radius: 2px;
        }}
        QPushButton:hover {{
            background-color: {_blend_colors(bg, "#ffffff", 0.15)};
            border-color: {c.text_accent};
        }}
        """
        self.setStyleSheet(qss)


class StepParamPopup(QFrame):
    """Popup flotante para editar parámetros de un step."""

    params_changed = Signal(int, int, StepParams)

    def __init__(self, track: int, step: int, params: StepParams, parent=None):
        super().__init__(parent)
        self._track = track
        self._step = step
        self._params = params

        self.setObjectName("stepParamPopup")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setFrameShape(QFrame.StyledPanel)

        c = ProTheme.get()
        self.setStyleSheet(f"""
            QFrame#stepParamPopup {{
                background-color: {c.bg_elevated};
                border: 1px solid {c.border_color};
                border-radius: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 6, 8, 6)

        title = QLabel(f"Step {step + 1} Parameters")
        title.setStyleSheet(f"color: {c.text_accent}; font-weight: bold; font-size: 10px;")
        layout.addWidget(title)

        # Chance
        chance_layout = QHBoxLayout()
        chance_label = QLabel("Chance:")
        chance_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 9px;")
        chance_layout.addWidget(chance_label)
        self._chance_spin = QSpinBox()
        self._chance_spin.setRange(0, 100)
        self._chance_spin.setValue(params.chance)
        self._chance_spin.setSuffix("%")
        self._chance_spin.setStyleSheet(f"""
            QSpinBox {{ background: {c.bg_tertiary}; color: {c.text_primary};
                        border: 1px solid {c.border_color}; border-radius: 3px; padding: 1px 4px; }}
        """)
        self._chance_spin.valueChanged.connect(self._on_param_changed)
        chance_layout.addWidget(self._chance_spin)
        layout.addLayout(chance_layout)

        # Repeat
        repeat_layout = QHBoxLayout()
        repeat_label = QLabel("Repeat:")
        repeat_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 9px;")
        repeat_layout.addWidget(repeat_label)
        self._repeat_spin = QSpinBox()
        self._repeat_spin.setRange(1, 4)
        self._repeat_spin.setValue(params.repeat)
        self._repeat_spin.setStyleSheet(f"""
            QSpinBox {{ background: {c.bg_tertiary}; color: {c.text_primary};
                        border: 1px solid {c.border_color}; border-radius: 3px; padding: 1px 4px; }}
        """)
        self._repeat_spin.valueChanged.connect(self._on_param_changed)
        repeat_layout.addWidget(self._repeat_spin)
        layout.addLayout(repeat_layout)

        # Offset
        offset_layout = QHBoxLayout()
        offset_label = QLabel("Offset:")
        offset_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 9px;")
        offset_layout.addWidget(offset_label)
        self._offset_spin = QSpinBox()
        self._offset_spin.setRange(-120, 120)
        self._offset_spin.setValue(params.offset)
        self._offset_spin.setSuffix(" tck")
        self._offset_spin.setStyleSheet(f"""
            QSpinBox {{ background: {c.bg_tertiary}; color: {c.text_primary};
                        border: 1px solid {c.border_color}; border-radius: 3px; padding: 1px 4px; }}
        """)
        self._offset_spin.valueChanged.connect(self._on_param_changed)
        offset_layout.addWidget(self._offset_spin)
        layout.addLayout(offset_layout)

        # Slide (toggle)
        slide_layout = QHBoxLayout()
        slide_label = QLabel("Slide:")
        slide_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 9px;")
        slide_layout.addWidget(slide_label)
        self._slide_check = QCheckBox()
        self._slide_check.setChecked(params.slide)
        self._slide_check.setStyleSheet(f"""
            QCheckBox {{ color: {c.text_primary}; font-size: 9px; }}
            QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 3px;
                border: 1px solid {c.border_color}; background: {c.bg_tertiary}; }}
            QCheckBox::indicator:checked {{ background-color: {c.accent_primary}; border-color: {c.accent_primary}; }}
        """)
        self._slide_check.toggled.connect(self._on_param_changed)
        slide_layout.addWidget(self._slide_check)
        slide_layout.addStretch()
        layout.addLayout(slide_layout)

    def _on_param_changed(self):
        self._params.chance = self._chance_spin.value()
        self._params.repeat = self._repeat_spin.value()
        self._params.offset = self._offset_spin.value()
        self._params.slide = self._slide_check.isChecked()
        self.params_changed.emit(self._track, self._step, self._params)


class StepGridWidget(QWidget):
    """Grid interno de steps que maneja drag painting.

    Cada instancia maneja una sola fila (un track).
    """

    step_clicked = Signal(int, int, bool, int)
    step_right_clicked = Signal(int, int)

    def __init__(self, track_index: int, num_steps: int, parent=None):
        super().__init__(parent)
        self._track_index = track_index
        self._num_steps = num_steps
        self._buttons: List[StepButton] = []
        self._dragging = False
        self._drag_state = None
        self.setMouseTracking(True)
        self._setup_grid()

    def set_step_count(self, count: int):
        self._num_steps = count
        self._rebuild_grid()

    def _rebuild_grid(self):
        for btn in self._buttons:
            btn.deleteLater()
        self._buttons.clear()
        self._setup_grid()

    def _setup_grid(self):
        grid = QGridLayout(self)
        grid.setSpacing(1)
        grid.setContentsMargins(0, 0, 0, 0)

        for s in range(self._num_steps):
            btn = StepButton(self._track_index, s)
            btn.clicked_step.connect(self._on_step_clicked)
            btn.right_clicked.connect(self._on_step_right_clicked)
            grid.addWidget(btn, 0, s)
            self._buttons.append(btn)

    def _on_step_clicked(self, track: int, step: int, active: bool, velocity: int):
        self.step_clicked.emit(track, step, active, velocity)

    def _on_step_right_clicked(self, track: int, step: int):
        self.step_right_clicked.emit(track, step)

    def get_button(self, step: int) -> Optional[StepButton]:
        if 0 <= step < len(self._buttons):
            return self._buttons[step]
        return None

    def get_all_buttons(self) -> List[StepButton]:
        return self._buttons

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            if isinstance(child, StepButton):
                self._dragging = True
                self._drag_state = child.is_active
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            child = self.childAt(event.pos())
            if isinstance(child, StepButton):
                if child.is_active != self._drag_state:
                    child.set_active(not child.is_active)
                    child.clicked_step.emit(
                        child.track_index, child.step_index,
                        child.is_active, child.get_velocity()
                    )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._dragging = False
        self._drag_state = None
        super().mouseReleaseEvent(event)


class StepSequencerWidget(QWidget):
    """Step sequencer widget profesional con grid, drag, velocity y parámetros por step.

    Señales:
        step_changed: track_index, step, active
        step_param_changed: track, step, param_name, value
        pattern_changed: pattern_index
    """

    step_changed = Signal(int, int, bool)
    step_param_changed = Signal(int, int, str, float)
    pattern_changed = Signal(int)

    def __init__(
        self,
        presentation_model=None,
        num_tracks: int = 4,
        num_steps: int = 16,
        parent=None
    ):
        super().__init__(parent)
        self._model = presentation_model
        self._num_tracks = num_tracks
        self._num_steps = num_steps
        self._current_step = 0
        self._current_pattern = 0
        self._current_velocity = 100
        self._clipboard_pattern: Optional[List[List[bool]]] = None
        self._clipboard_velocities: Dict[Tuple[int, int], int] = {}

        self._track_names: List[str] = []
        self._track_widgets: List[QWidget] = []
        self._step_params: Dict[Tuple[int, int, int], StepParams] = {}

        self._playhead_timer = QTimer(self)
        self._playhead_timer.setInterval(600)
        self._playhead_timer.timeout.connect(self._toggle_playhead_glow)
        self._playhead_glow_on = False

        self._connect_model()
        self._setup_ui()

    def _connect_model(self):
        if self._model is None:
            try:
                from src.presentation.models import get_presentation_model
                self._model = get_presentation_model()
            except ImportError:
                pass

        if self._model:
            try:
                self._model.position_changed.connect(self._on_position_changed)
            except AttributeError:
                pass
            try:
                self._model.track_added.connect(self._on_tracks_changed)
            except AttributeError:
                pass
            try:
                self._model.track_removed.connect(self._on_tracks_changed)
            except AttributeError:
                pass
            try:
                self._model.project_loaded.connect(self._on_tracks_changed)
            except AttributeError:
                pass

    def _setup_ui(self):
        c = ProTheme.get()

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(2)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # === Top bar: Pattern selector + tools ===
        top_bar = QWidget()
        top_bar.setStyleSheet(f"""
            background-color: {c.bg_secondary};
            border: 1px solid {c.border_color};
            border-radius: 4px;
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)
        top_layout.setSpacing(6)

        # Pattern selector
        pat_label = QLabel("Pattern:")
        pat_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 9px; font-weight: bold;")
        top_layout.addWidget(pat_label)

        self._pattern_combo = QComboBox()
        self._pattern_combo.addItems(["01", "02", "03", "04", "05", "06", "07", "08"])
        self._pattern_combo.setFixedWidth(50)
        self._pattern_combo.currentIndexChanged.connect(self._on_pattern_changed)
        top_layout.addWidget(self._pattern_combo)

        # Steps selector
        steps_label = QLabel("Steps:")
        steps_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 9px;")
        top_layout.addWidget(steps_label)

        self._steps_combo = QComboBox()
        self._steps_combo.addItems(["8", "16", "32", "64"])
        self._steps_combo.setCurrentText(str(self._num_steps))
        self._steps_combo.setFixedWidth(50)
        self._steps_combo.currentTextChanged.connect(self._on_steps_changed)
        top_layout.addWidget(self._steps_combo)

        # Swing
        swing_label = QLabel(f"Swing:")
        swing_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 9px;")
        top_layout.addWidget(swing_label)

        self._swing_slider = QSlider(Qt.Horizontal)
        self._swing_slider.setRange(0, 100)
        self._swing_slider.setValue(0)
        self._swing_slider.setFixedWidth(60)
        self._swing_slider.valueChanged.connect(self._on_swing_changed)
        top_layout.addWidget(self._swing_slider)

        self._swing_label = QLabel("0%")
        self._swing_label.setStyleSheet(f"color: {c.text_accent}; font-size: 9px;")
        top_layout.addWidget(self._swing_label)

        top_layout.addStretch()

        # Step indicator
        self._step_label = QLabel(f"Step: {self._current_step + 1}")
        self._step_label.setStyleSheet(f"""
            color: {c.text_accent}; font-size: 10px; font-weight: bold;
            padding: 2px 8px; background-color: {c.bg_tertiary};
            border: 1px solid {c.border_color}; border-radius: 3px;
        """)
        top_layout.addWidget(self._step_label)

        main_layout.addWidget(top_bar)

        # === Scroll area con grid ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:horizontal {{ height: 8px; background: {c.scrollbar_bg}; }}
            QScrollBar::handle:horizontal {{ background: {c.scrollbar_handle}; min-width: 30px; border-radius: 4px; }}
            QScrollBar::handle:horizontal:hover {{ background: {c.scrollbar_handle_hover}; }}
        """)

        grid_container = QWidget()
        grid_container.setStyleSheet("background: transparent;")
        self._grid_layout = QVBoxLayout(grid_container)
        self._grid_layout.setSpacing(1)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)

        self._populate_grid()

        scroll.setWidget(grid_container)
        main_layout.addWidget(scroll)

    def _populate_grid(self):
        c = ProTheme.get()

        # Clear existing
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item is not None and item.widget() is not None:
                item.widget().deleteLater()

        self._track_widgets = []

        # Grid layout per track: [header | step buttons]
        for t in range(self._num_tracks):
            row_widget = QWidget()
            row_widget.setStyleSheet("background: transparent;")
            row_layout = QHBoxLayout(row_widget)
            row_layout.setSpacing(2)
            row_layout.setContentsMargins(0, 0, 0, 0)

            # Track header
            header = self._create_track_header(t)
            row_layout.addWidget(header)

            # Step grid
            grid_widget = StepGridWidget(t, self._num_steps)
            grid_widget.setFixedHeight(28)
            grid_widget.step_clicked.connect(self._on_step_clicked)
            grid_widget.step_right_clicked.connect(self._on_step_right_clicked)
            row_layout.addWidget(grid_widget, 1)

            self._track_widgets.append(row_widget)
            self._grid_layout.addWidget(row_widget)

        # Bottom status bar
        status_bar = QWidget()
        status_bar.setStyleSheet(f"""
            background-color: {c.bg_secondary};
            border: 1px solid {c.border_color};
            border-radius: 3px;
        """)
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(8, 2, 8, 2)

        clear_btn = QPushButton("Clear")
        clear_btn.setIcon(Icons.DELETE)
        clear_btn.setFixedHeight(20)
        clear_btn.clicked.connect(self._clear_pattern)
        status_layout.addWidget(clear_btn)

        random_btn = QPushButton("Randomize")
        random_btn.setIcon(Icons.SHUFFLE)
        random_btn.setFixedHeight(20)
        random_btn.clicked.connect(self._randomize_pattern)
        status_layout.addWidget(random_btn)

        status_layout.addStretch()

        tracks_total = QLabel(f"Tracks: {self._num_tracks} | Steps: {self._num_steps}")
        tracks_total.setStyleSheet(f"color: {c.text_tertiary}; font-size: 9px;")
        status_layout.addWidget(tracks_total)

        self._grid_layout.addWidget(status_bar)

    def _create_track_header(self, track_index: int) -> QWidget:
        c = ProTheme.get()
        track_color = c.track_colors[track_index % len(c.track_colors)]

        header = QWidget()
        header.setFixedWidth(130)
        header.setStyleSheet(f"""
            background-color: {c.bg_tertiary};
            border: 1px solid {c.border_color};
            border-radius: 3px;
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(6, 1, 6, 1)
        h_layout.setSpacing(4)

        # Color indicator
        color_dot = QLabel()
        color_dot.setFixedSize(8, 8)
        color_dot.setStyleSheet(f"""
            background-color: {track_color};
            border-radius: 4px;
        """)
        h_layout.addWidget(color_dot)

        # Track name
        name = f"Track {track_index + 1}"
        if track_index < len(self._track_names):
            name = self._track_names[track_index]
        name_label = QLabel(name)
        name_label.setStyleSheet(f"color: {c.text_primary}; font-size: 9px; font-weight: bold;")
        name_label.setFixedWidth(50)
        h_layout.addWidget(name_label)

        h_layout.addStretch()

        # Mute
        mute_btn = QPushButton()
        mute_btn.setIcon(Icons.MUTE_ALT)
        mute_btn.setCheckable(True)
        mute_btn.setFixedSize(18, 18)
        mute_btn.setToolTip("Mute")
        mute_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; font-size: 10px; }}
            QPushButton:checked {{ background: {c.mute_bg}; border-radius: 3px; }}
        """)
        h_layout.addWidget(mute_btn)

        # Solo
        solo_btn = QPushButton("S")
        solo_btn.setCheckable(True)
        solo_btn.setFixedSize(18, 18)
        solo_btn.setToolTip("Solo")
        solo_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.text_tertiary};
                          border: none; font-size: 9px; font-weight: bold; }}
            QPushButton:checked {{ color: {c.solo_color}; background: {c.solo_bg}; border-radius: 3px; }}
        """)
        h_layout.addWidget(solo_btn)

        return header

    def _on_step_clicked(self, track: int, step: int, active: bool, velocity: int):
        self.step_changed.emit(track, step, active)
        key = (self._current_pattern, track, step)
        if key not in self._step_params:
            self._step_params[key] = StepParams()
        self._step_params[key].velocity = velocity

        if self._model:
            try:
                tracks = self._model.current_project.get_tracks()
                if track < len(tracks):
                    self._model.set_pattern_step(
                        tracks[track].id, self._current_pattern, step, active
                    )
            except (AttributeError, IndexError):
                pass

    def _on_step_right_clicked(self, track: int, step: int):
        key = (self._current_pattern, track, step)
        if key in self._step_params:
            del self._step_params[key]
        self.step_changed.emit(track, step, False)

        if self._model:
            try:
                tracks = self._model.current_project.get_tracks()
                if track < len(tracks):
                    self._model.set_pattern_step(
                        tracks[track].id, self._current_pattern, step, False
                    )
            except (AttributeError, IndexError):
                pass

    def _on_pattern_changed(self, index: int):
        self._current_pattern = index
        self.pattern_changed.emit(index)
        self._sync_grid_from_model()

    def _on_steps_changed(self, text: str):
        self._num_steps = int(text)
        self._rebuild_ui()

    def _on_swing_changed(self, value: int):
        self._swing_label.setText(f"{value}%")

    def _on_position_changed(self, tick: int):
        step = tick // 480
        if step >= self._num_steps:
            step = 0

        if step == self._current_step:
            return

        old_step = self._current_step
        self._current_step = step
        self._step_label.setText(f"Step: {step + 1}")

        self._highlight_column(old_step, False)
        self._highlight_column(step, True)

    def _highlight_column(self, step: int, highlight: bool):
        for row_widget in self._track_widgets:
            grid = row_widget.findChild(StepGridWidget)
            if grid:
                btn = grid.get_button(step)
                if btn:
                    btn.set_playhead(highlight)

    def _toggle_playhead_glow(self):
        self._playhead_glow_on = not self._playhead_glow_on
        self._highlight_column(self._current_step, self._playhead_glow_on)

    def _on_tracks_changed(self):
        if self._model and self._model.current_project:
            try:
                tracks = self._model.current_project.get_tracks()
                self._num_tracks = len(tracks)
                self._track_names = [t.name for t in tracks]
                self._rebuild_ui()
            except AttributeError:
                pass

    def _rebuild_ui(self):
        self._populate_grid()
        self._sync_grid_from_model()

    def _sync_grid_from_model(self):
        if not self._model or not self._model.current_project:
            return
        try:
            tracks = self._model.current_project.get_tracks()
            for t, row_widget in enumerate(self._track_widgets):
                grid = row_widget.findChild(StepGridWidget)
                if grid and t < len(tracks):
                    track = tracks[t]
                    if self._current_pattern < len(track.patterns):
                        pattern = track.patterns[self._current_pattern]
                        for s in range(pattern.length):
                            btn = grid.get_button(s)
                            if btn:
                                active = pattern.get_step(s)
                                key = (self._current_pattern, t, s)
                                vel = 100
                                if key in self._step_params:
                                    vel = self._step_params[key].velocity
                                btn.set_active(active, vel)
        except (AttributeError, IndexError):
            pass

    def _clear_pattern(self):
        for row_widget in self._track_widgets:
            grid = row_widget.findChild(StepGridWidget)
            if grid:
                for s in range(self._num_steps):
                    btn = grid.get_button(s)
                    if btn:
                        btn.set_active(False)
                        self.step_changed.emit(btn.track_index, s, False)

    def _randomize_pattern(self):
        import random
        for row_widget in self._track_widgets:
            grid = row_widget.findChild(StepGridWidget)
            if grid:
                for s in range(self._num_steps):
                    btn = grid.get_button(s)
                    if btn:
                        active = random.random() < 0.3
                        vel = random.randint(60, 127)
                        btn.set_active(active, vel)
                        self.step_changed.emit(btn.track_index, s, active)

    def _copy_pattern(self):
        self._clipboard_pattern = self.get_all_step_states()
        self._clipboard_velocities = {}
        for row_widget in self._track_widgets:
            grid = row_widget.findChild(StepGridWidget)
            if grid:
                for s in range(self._num_steps):
                    btn = grid.get_button(s)
                    if btn:
                        self._clipboard_velocities[(btn.track_index, s)] = btn.get_velocity()

    def _paste_pattern(self):
        if self._clipboard_pattern is None:
            return
        for t, row_widget in enumerate(self._track_widgets):
            grid = row_widget.findChild(StepGridWidget)
            if grid and t < len(self._clipboard_pattern):
                for s in range(self._num_steps):
                    btn = grid.get_button(s)
                    if btn and s < len(self._clipboard_pattern[t]):
                        active = self._clipboard_pattern[t][s]
                        vel = self._clipboard_velocities.get((t, s), 100)
                        btn.set_active(active, vel)
                        self.step_changed.emit(btn.track_index, s, active)
        self.pattern_changed.emit(self._current_pattern)

    def contextMenuEvent(self, event):
        self._show_context_menu(event.globalPos())

    def _show_context_menu(self, global_pos):
        c = ProTheme.get()
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {c.menu_bg}; color: {c.menu_text};
                     border: 1px solid {c.menu_border}; border-radius: 4px; padding: 4px; }}
            QMenu::item {{ padding: 4px 16px; border-radius: 2px; font-size: 9px; }}
            QMenu::item:selected {{ background: {c.menu_hover}; color: {c.text_accent}; }}
        """)
        copy_action = menu.addAction("Copy Pattern")
        copy_action.setIcon(Icons.COPY)
        copy_action.triggered.connect(self._copy_pattern)
        paste_action = menu.addAction("Paste Pattern")
        paste_action.setIcon(Icons.PASTE)
        paste_action.triggered.connect(self._paste_pattern)
        menu.addSeparator()
        clear_action = menu.addAction("Clear Pattern")
        clear_action.setIcon(Icons.DELETE)
        clear_action.triggered.connect(self._clear_pattern)
        shuffle_action = menu.addAction("Randomize")
        shuffle_action.setIcon(Icons.SHUFFLE)
        shuffle_action.triggered.connect(self._randomize_pattern)
        menu.exec(global_pos)

    # === Public API ===

    def set_num_steps(self, num_steps: int):
        self._num_steps = num_steps
        self._steps_combo.setCurrentText(str(num_steps))

    def set_step_active(self, track: int, step: int, active: bool, velocity: int = 100):
        for row_widget in self._track_widgets:
            grid = row_widget.findChild(StepGridWidget)
            if grid:
                btn = grid.get_button(step)
                if btn and btn.track_index == track:
                    btn.set_active(active, velocity)
                    return

    def get_active_steps(self, track: int) -> List[int]:
        result = []
        for row_widget in self._track_widgets:
            grid = row_widget.findChild(StepGridWidget)
            if grid:
                for s in range(self._num_steps):
                    btn = grid.get_button(s)
                    if btn and btn.track_index == track and btn.is_active:
                        result.append(s)
        return result

    def get_all_step_states(self) -> List[List[bool]]:
        states = []
        for t, row_widget in enumerate(self._track_widgets):
            grid = row_widget.findChild(StepGridWidget)
            if not grid:
                states.append([False] * self._num_steps)
                continue
            row = []
            for s in range(self._num_steps):
                btn = grid.get_button(s)
                row.append(btn.is_active if btn else False)
            states.append(row)
        return states

    def set_tracks(self, track_list: list):
        self._num_tracks = len(track_list)
        self._track_names = [t["name"] if isinstance(t, dict) else t[1] for t in track_list]
        self._rebuild_ui()

    def highlight_step(self, step: int):
        self._on_position_changed(step * 480)

    def get_step_params(self, track: int, step: int) -> StepParams:
        key = (self._current_pattern, track, step)
        if key not in self._step_params:
            self._step_params[key] = StepParams()
        return self._step_params[key]

    def set_current_velocity(self, vel: int):
        self._current_velocity = max(1, min(127, vel))
