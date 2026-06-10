"""Piano Roll Widget - Editor de notas MIDI profesional.

Características:
- QGraphicsView con zoom (Ctrl+scroll) y pan (middle-click drag)
- Crear, mover, redimensionar, seleccionar notas
- Velocity lane con barras editables
- Grid snap: 1/1, 1/2, 1/4, 1/8, 1/16, 1/32
- Herramientas: Draw, Erase, Select, Line
- Colores por velocity (verde → amarillo → rojo)
- Teclado de piano a la izquierda
- Fold mode (solo notas activas)
"""

import logging
import math
from typing import Optional, List, Dict, Tuple, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QPushButton, QComboBox, QSlider, QScrollArea,
    QSizePolicy, QMenu
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QBrush, QWheelEvent,
    QMouseEvent, QKeyEvent, QTransform
)

from src.presentation.styles.pro_theme import ProTheme
from src.presentation.styles.icons import Icons

logger = logging.getLogger(__name__)

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_WHITE_KEYS = {0, 2, 4, 5, 7, 9, 11}
_SNAP_OPTIONS = ["1/1", "1/2", "1/4", "1/8", "1/16", "1/32"]
def _get_tools():
    return [Icons.TOOL_DRAW, Icons.TOOL_ERASE, Icons.TOOL_SELECT, Icons.TOOL_LINE]
_PIANO_WIDTH = 50
_NOTE_HEIGHT = 14
_STEP_WIDTH = 24
_DEFAULT_VELOCITY = 100


def _pitch_to_name(pitch: int) -> str:
    return f"{_NOTE_NAMES[pitch % 12]}{pitch // 12 - 1}"


def _velocity_color(vel: int) -> str:
    if vel > 110:
        return "#ff4444"
    elif vel > 80:
        return "#ffaa00"
    elif vel > 50:
        return "#88dd44"
    else:
        return "#44aa66"


def _snap_to_grid(x: float, snap: int) -> float:
    return round(x / snap) * snap


class NoteItem(QGraphicsRectItem):
    """Item gráfico para una nota MIDI."""

    def __init__(self, note_id: str, pitch: int, start_tick: int,
                 duration: int, velocity: int, parent=None):
        super().__init__(parent)
        self.note_id = note_id
        self.pitch = pitch
        self.start_tick = start_tick
        self.duration = duration
        self._velocity = velocity
        self._dragging = False
        self._resizing = False
        self._drag_start = QPointF()
        self._original_pos = QPointF()

        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setAcceptHoverEvents(True)
        self.setZValue(50)
        self._update_appearance()

    def _update_appearance(self):
        color = _velocity_color(self._velocity)
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(QColor(color).darker(150), 1) if not self.isSelected()
                    else QPen(QColor("#ffffff"), 2))

    def set_velocity(self, vel: int):
        self._velocity = max(1, min(127, vel))
        self._update_appearance()

    def get_velocity(self) -> int:
        return self._velocity

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.rect().width() > 20:
            painter.setPen(QColor(255, 255, 255, 80))
            painter.setFont(QFont("monospace", 6))
            painter.drawText(self.rect(), Qt.AlignCenter, _pitch_to_name(self.pitch))


class PianoKeyboard(QWidget):
    """Teclado de piano vertical para el piano roll."""

    note_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._octave_start = 2
        self._octave_count = 3
        self.setFixedWidth(_PIANO_WIDTH)
        self.setMouseTracking(True)

    def set_octave_range(self, start: int, count: int):
        self._octave_start = start
        self._octave_count = count
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()

        for i in range(self._octave_count * 12):
            pitch = self._octave_start * 12 + (self._octave_count * 12 - 1 - i)
            note_in = pitch % 12
            is_black = note_in not in _WHITE_KEYS
            y = i * _NOTE_HEIGHT

            if is_black:
                painter.fillRect(0, y, w, _NOTE_HEIGHT, QColor("#1a1a1a"))
                painter.setPen(QPen(QColor("#333"), 1))
                painter.drawRect(0, y, w // 2, _NOTE_HEIGHT)
            else:
                painter.fillRect(0, y, w, _NOTE_HEIGHT, QColor("#e8e8e8"))
                painter.setPen(QPen(QColor("#ccc"), 1))
                painter.drawRect(0, y, w, _NOTE_HEIGHT)
                if note_in == 0:
                    painter.setPen(QColor("#999"))
                    painter.setFont(QFont("monospace", 7))
                    painter.drawText(2, y + _NOTE_HEIGHT - 2, _pitch_to_name(pitch))

    def mousePressEvent(self, event: QMouseEvent):
        idx = int(event.pos().y() // _NOTE_HEIGHT)
        pitch = self._octave_start * 12 + (self._octave_count * 12 - 1 - idx)
        if 0 <= pitch <= 127:
            self.note_clicked.emit(pitch)


class NoteScene(QGraphicsScene):
    """Escena del piano roll con manejo de notas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_tool = "Draw"
        self._snap = _STEP_WIDTH
        self._start_note = 24
        self._num_notes = 36
        self._num_steps = 64
        self._folded = False
        self._active_pitches: set = set()

    def configure(self, snap: int, start_note: int, num_notes: int,
                  num_steps: int, folded: bool, active_pitches: set):
        self._snap = snap
        self._start_note = start_note
        self._num_notes = num_notes
        self._num_steps = num_steps
        self._folded = folded
        self._active_pitches = active_pitches


class PianoRollWidget(QWidget):
    """Piano roll profesional con zoom, selección y velocity lane."""

    note_added = Signal(str, object)
    note_removed = Signal(str, str)
    note_moved = Signal(str, str, int)
    note_resized = Signal(str, str, int)
    selection_changed = Signal(list)
    note_clicked = Signal(int)
    note_toggled = Signal(int, int)

    def __init__(self, presentation_model=None, parent=None):
        super().__init__(parent)
        self._model = presentation_model
        self._notes: Dict[str, NoteItem] = {}
        self._current_track_id: Optional[str] = None
        self._tracks: list = []
        self._octave_start = 2
        self._octave_count = 3
        self._num_steps = 64
        self._snap_index = 2
        self._tool_index = 0
        self._folded = False
        self._current_step = 0
        self._clipboard: list = []
        self._marquee_start: Optional[QPointF] = None
        self._marquee_item = None
        self._dragging_notes: Optional[List[NoteItem]] = None
        self._resizing_note: Optional[NoteItem] = None

        if self._model is None:
            try:
                from src.presentation.models import get_presentation_model
                self._model = get_presentation_model()
            except ImportError:
                pass

        self._connect_model()
        self._setup_ui()

    def _connect_model(self):
        if self._model:
            try:
                self._model.position_changed.connect(self._on_position_changed)
                self._model.track_modified.connect(lambda *a: self._load_notes())
                self._model.project_loaded.connect(lambda: self._load_notes())
            except AttributeError:
                pass

    def _setup_ui(self):
        c = ProTheme.get()
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)

        # Toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet(f"""
            background-color: {c.bg_secondary};
            border: 1px solid {c.border_color};
            border-radius: 3px;
        """)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(6, 3, 6, 3)
        tb_layout.setSpacing(4)

        label = QLabel("Piano Roll")
        label.setStyleSheet(f"color: {c.text_primary}; font-weight: bold; font-size: 10px; background: transparent;")
        tb_layout.addWidget(label)

        # Tools
        self._tool_btns = []
        for t in _get_tools():
            btn = QPushButton()
            btn.setIcon(t)
            btn.setCheckable(True)
            btn.setFixedSize(26, 22)
            btn.setStyleSheet(self._tool_btn_style(c, False))
            btn.clicked.connect(lambda checked, idx=len(self._tool_btns): self._set_tool(idx))
            tb_layout.addWidget(btn)
            self._tool_btns.append(btn)
        self._tool_btns[0].setChecked(True)
        self._tool_btns[0].setStyleSheet(self._tool_btn_style(c, True))

        tb_layout.addSpacing(8)

        # Snap
        snap_label = QLabel("Snap:")
        snap_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 9px; background: transparent;")
        tb_layout.addWidget(snap_label)

        self._snap_combo = QComboBox()
        self._snap_combo.addItems(_SNAP_OPTIONS)
        self._snap_combo.setCurrentIndex(self._snap_index)
        self._snap_combo.setFixedWidth(55)
        self._snap_combo.currentIndexChanged.connect(self._on_snap_changed)
        tb_layout.addWidget(self._snap_combo)

        tb_layout.addStretch()

        # Fold toggle
        self._fold_btn = QPushButton("Fold")
        self._fold_btn.setIcon(Icons.CHECK)
        self._fold_btn.setCheckable(True)
        self._fold_btn.setFixedHeight(22)
        self._fold_btn.toggled.connect(self._toggle_fold)
        tb_layout.addWidget(self._fold_btn)

        # Octave controls
        oct_down = QPushButton()
        oct_down.setIcon(Icons.MINUS)
        oct_down.setFixedSize(22, 22)
        oct_down.clicked.connect(self._octave_down)
        tb_layout.addWidget(oct_down)

        self._oct_label = QLabel(f"C{self._octave_start + 1}-C{self._octave_start + self._octave_count + 1}")
        self._oct_label.setStyleSheet(f"color: {c.text_accent}; font-size: 9px; background: transparent;")
        tb_layout.addWidget(self._oct_label)

        oct_up = QPushButton()
        oct_up.setIcon(Icons.PLUS)
        oct_up.setFixedSize(22, 22)
        oct_up.clicked.connect(self._octave_up)
        tb_layout.addWidget(oct_up)

        layout.addWidget(toolbar)

        # Main area: keyboard + scene + velocity lane
        main_area = QVBoxLayout()
        main_area.setSpacing(1)

        scene_toolbar = QHBoxLayout()
        scene_toolbar.setSpacing(0)

        # Piano keyboard
        self._piano = PianoKeyboard()
        self._piano.set_octave_range(self._octave_start, self._octave_count)
        self._piano.note_clicked.connect(self._on_piano_key_clicked)
        scene_toolbar.addWidget(self._piano)

        # Scene
        self._scene = QGraphicsScene()
        self._view = GraphicsView(self._scene, parent_widget=self)
        self._view.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._view.setStyleSheet("border: none;")
        scene_toolbar.addWidget(self._view, 1)

        main_area.addLayout(scene_toolbar)

        # Velocity lane
        vel_bar = QWidget()
        vel_bar.setFixedHeight(30)
        vel_layout = QHBoxLayout(vel_bar)
        vel_layout.setContentsMargins(0, 0, 0, 0)
        vel_layout.setSpacing(0)

        vel_label = QWidget()
        vel_label.setFixedWidth(_PIANO_WIDTH)
        vel_label.setStyleSheet(f"background-color: {c.bg_tertiary}; border: 1px solid {c.border_color};")
        vl = QVBoxLayout(vel_label)
        vl.setContentsMargins(2, 0, 2, 0)
        l = QLabel("Vel")
        l.setStyleSheet(f"color: {c.text_tertiary}; font-size: 7px; background: transparent;")
        vl.addWidget(l)
        vel_layout.addWidget(vel_label)

        self._vel_scene = QGraphicsScene()
        self._vel_view = QGraphicsView(self._vel_scene)
        self._vel_view.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._vel_view.setFixedHeight(28)
        self._vel_view.setStyleSheet("border: none;")
        self._vel_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._vel_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        vel_layout.addWidget(self._vel_view, 1)

        main_area.addWidget(vel_bar)
        layout.addLayout(main_area)

        # Sync scroll between view and vel_view
        self._view.horizontalScrollBar().valueChanged.connect(
            self._vel_view.horizontalScrollBar().setValue
        )

        self._redraw()

    def _tool_btn_style(self, c, active: bool) -> str:
        if active:
            return f"""
                QPushButton {{ background: {c.bg_active}; color: {c.text_accent};
                              border: 1px solid {c.border_accent}; font-size: 12px;
                              border-radius: 3px; }}
            """
        return f"""
            QPushButton {{ background: transparent; color: {c.text_tertiary};
                          border: 1px solid transparent; font-size: 12px;
                          border-radius: 3px; }}
            QPushButton:hover {{ color: {c.text_primary}; background: {c.bg_hover}; }}
        """

    def _set_tool(self, idx: int):
        self._tool_index = idx
        c = ProTheme.get()
        for i, btn in enumerate(self._tool_btns):
            btn.setChecked(i == idx)
            btn.setStyleSheet(self._tool_btn_style(c, i == idx))

    def _on_snap_changed(self, idx: int):
        self._snap_index = idx

    def _snap_ticks(self) -> int:
        divisions = [1, 2, 4, 8, 16, 32]
        return _STEP_WIDTH // divisions[self._snap_index]

    def _toggle_fold(self, folded: bool):
        self._folded = folded
        self._redraw()

    def _octave_down(self):
        if self._octave_start > 0:
            self._octave_start -= 1
            self._piano.set_octave_range(self._octave_start, self._octave_count)
            self._oct_label.setText(f"C{self._octave_start + 1}-C{self._octave_start + self._octave_count + 1}")
            self._redraw()

    def _octave_up(self):
        if self._octave_start + self._octave_count < 9:
            self._octave_start += 1
            self._piano.set_octave_range(self._octave_start, self._octave_count)
            self._oct_label.setText(f"C{self._octave_start + 1}-C{self._octave_start + self._octave_count + 1}")
            self._redraw()

    def _on_piano_key_clicked(self, pitch: int):
        self.note_clicked.emit(pitch)

    def _redraw(self):
        self._scene.clear()
        self._vel_scene.clear()
        self._notes.clear()

        c = ProTheme.get()
        start_note = self._octave_start * 12
        num_notes = self._octave_count * 12
        total_h = num_notes * _NOTE_HEIGHT
        total_w = self._num_steps * _STEP_WIDTH

        self._scene.setSceneRect(0, 0, total_w, total_h + 1)
        self._scene.setBackgroundBrush(QColor(c.bg_primary))

        # Horizontal grid lines
        active_pitches = set()
        for n in range(num_notes + 1):
            y = n * _NOTE_HEIGHT
            pitch = start_note + (num_notes - n)
            note_in = pitch % 12
            is_black = note_in not in _WHITE_KEYS

            if is_black and n < num_notes:
                bg = self._scene.addRect(0, y, total_w, _NOTE_HEIGHT,
                                          QPen(Qt.NoPen), QBrush(QColor("#0d0d0d")))
                bg.setZValue(-2)

            if note_in == 0:
                p = QPen(QColor(c.grid_line_bold), 1)
            else:
                p = QPen(QColor(c.grid_line), 1) if not is_black else QPen(Qt.NoPen)
            self._scene.addLine(0, y, total_w, y, p)

        # Vertical grid lines
        for s in range(self._num_steps + 1):
            x = s * _STEP_WIDTH
            is_bar = s % 16 == 0
            is_beat = s % 4 == 0
            if is_bar:
                p = QPen(QColor(c.grid_line_bold), 2)
            elif is_beat:
                p = QPen(QColor(c.grid_line), 1)
            else:
                p = QPen(QColor(c.grid_line).darker(130), 1)
            self._scene.addLine(x, 0, x, total_h, p)

        # Playhead
        self._playhead_item = self._scene.addLine(
            0, 0, 0, total_h,
            QPen(QColor(c.grid_playhead), 2)
        )
        self._playhead_item.setZValue(100)

        # Load notes
        self._load_notes()

    def _load_notes(self):
        self._notes.clear()
        if not self._model:
            return
        num_notes = self._octave_count * 12
        start_note = self._octave_start * 12

        try:
            notes_data = []
            if self._current_track_id:
                notes_data = self._model.get_notes(self._current_track_id)
            for n in notes_data:
                pitch = n.pitch
                if pitch < start_note or pitch >= start_note + num_notes:
                    continue
                if self._folded and pitch not in active_pitches:
                    continue

                vis_pitch = num_notes - 1 - (pitch - start_note)
                y = vis_pitch * _NOTE_HEIGHT + 1
                x = (n.position // 480) * _STEP_WIDTH
                w = max(_STEP_WIDTH - 2, (n.duration // 480) * _STEP_WIDTH - 2)
                h = _NOTE_HEIGHT - 2

                item = NoteItem(n.id, pitch, n.position, n.duration, getattr(n, 'velocity', _DEFAULT_VELOCITY))
                item.setRect(0, 0, w, h)
                item.setPos(x, y)
                self._scene.addItem(item)
                self._notes[n.id] = item
        except (AttributeError, IndexError):
            pass

    def _on_position_changed(self, tick: int):
        step = tick // 480
        self._current_step = step
        if hasattr(self, '_playhead_item') and self._playhead_item:
            self._playhead_item.setLine(step * _STEP_WIDTH, 0,
                                         step * _STEP_WIDTH, self._scene.height())

    # === Event Handling ===

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self._delete_selected()
        elif event.matches(QKeyEvent.StandardKey.Copy):
            self._copy_selected()
        elif event.matches(QKeyEvent.StandardKey.Paste):
            self._paste_clipboard()
        elif event.key() == Qt.Key_N:
            self._snap_index = (self._snap_index + 1) % len(_SNAP_OPTIONS)
            self._snap_combo.setCurrentIndex(self._snap_index)
        super().keyPressEvent(event)

    def _delete_selected(self):
        for item in self._scene.selectedItems():
            if isinstance(item, NoteItem):
                self._scene.removeItem(item)
                del self._notes[item.note_id]
                self.note_removed.emit(self._current_track_id, item.note_id)

    def _copy_selected(self):
        self._clipboard = []
        for item in self._scene.selectedItems():
            if isinstance(item, NoteItem):
                self._clipboard.append({
                    "pitch": item.pitch,
                    "duration": item.duration,
                    "velocity": item.get_velocity(),
                    "start": item.start_tick
                })

    def _paste_clipboard(self):
        if not self._clipboard:
            return
        for note_data in self._clipboard:
            n = NoteItem(
                str(id(note_data)), note_data["pitch"],
                note_data["start"] + 480, note_data["duration"],
                note_data["velocity"]
            )
            self._scene.addItem(n)

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
        menu.addAction("Select All").triggered.connect(self._select_all)
        menu.addSeparator()
        copy_action = menu.addAction("Copy")
        copy_action.setIcon(Icons.COPY)
        copy_action.triggered.connect(self._copy_selected)
        paste_action = menu.addAction("Paste")
        paste_action.setIcon(Icons.PASTE)
        paste_action.triggered.connect(self._paste_clipboard)
        menu.addSeparator()
        delete_action = menu.addAction("Delete")
        delete_action.setIcon(Icons.DELETE)
        delete_action.triggered.connect(self._delete_selected)
        quantize_action = menu.addAction("Quantize")
        quantize_action.setIcon(Icons.TOOL_SNAP)
        quantize_action.triggered.connect(self._quantize_notes)
        menu.addSeparator()
        transpose_menu = menu.addMenu("Transpose")
        for label, amount in [("+1 semitone", 1), ("-1 semitone", -1), ("+12 semitones", 12), ("-12 semitones", -12)]:
            action = transpose_menu.addAction(label)
            action.triggered.connect(lambda checked, a=amount: self._transpose_notes(a))
        menu.exec(global_pos)

    def _select_all(self):
        for item in self._scene.items():
            if isinstance(item, NoteItem):
                item.setSelected(True)

    def _quantize_notes(self):
        snap = self._snap_ticks()
        for item in self._scene.selectedItems():
            if isinstance(item, NoteItem):
                new_x = _snap_to_grid(item.pos().x(), snap)
                item.setPos(new_x, item.pos().y())
                self.note_moved.emit(self._current_track_id, item.note_id, int(new_x))

    def _transpose_notes(self, semitones: int):
        for item in self._scene.selectedItems():
            if isinstance(item, NoteItem):
                old_pitch = item.pitch
                new_pitch = max(0, min(127, old_pitch + semitones))
                if new_pitch != old_pitch:
                    item.pitch = new_pitch
                    self.note_moved.emit(self._current_track_id, item.note_id, new_pitch)

    # === Public API ===

    def set_track(self, track_id: str):
        self._current_track_id = track_id
        self._load_notes()

    def set_tracks(self, track_list: list):
        self._tracks = track_list
        self._redraw()

    def get_notes(self) -> List[Dict]:
        result = []
        for nid, item in self._notes.items():
            result.append({
                "id": nid,
                "pitch": item.pitch,
                "position": item.start_tick,
                "duration": item.duration,
                "velocity": item.get_velocity()
            })
        return result

    def set_notes(self, notes: List[Dict]):
        self._redraw()


class GraphicsView(QGraphicsView):
    """QGraphicsView con zoom, pan y manejo de notas."""

    def __init__(self, scene, parent_widget=None, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setMouseTracking(True)
        self._parent_widget = parent_widget
        self._is_panning = False
        self._pan_start = QPointF()
        self._tool = "Draw"
        self._snap_px = _STEP_WIDTH // 4
        self._dragging_notes = None
        self._drag_start = QPointF()
        self._line_start = QPointF()

    def set_tool(self, tool: str):
        self._tool = tool

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15
            if event.angleDelta().y() > 0:
                self.scale(factor, factor)
            else:
                self.scale(1 / factor, 1 / factor)
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        scene_pos = self.mapToScene(event.pos())

        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())

            if self._tool == "Draw":
                if isinstance(item, NoteItem):
                    self._start_drag(item, scene_pos)
                else:
                    self._create_note(scene_pos)
            elif self._tool == "Erase":
                if isinstance(item, NoteItem):
                    self.scene().removeItem(item)
            elif self._tool == "Select":
                if isinstance(item, NoteItem):
                    self._start_drag(item, scene_pos)
                else:
                    self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
                    super().mousePressEvent(event)
            elif self._tool == "Line":
                self._line_start = scene_pos

        elif event.button() == Qt.MouseButton.RightButton:
            item = self.itemAt(event.pos())
            if isinstance(item, NoteItem):
                self.scene().removeItem(item)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        super().mouseReleaseEvent(event)

    def _start_drag(self, item: NoteItem, scene_pos):
        self._dragging_notes = [item]
        self._drag_start = scene_pos
        item.setSelected(True)

    def _create_note(self, scene_pos: QPointF):
        pw = self._parent_widget
        steps = max(0, round(scene_pos.x() / _STEP_WIDTH))
        tick = steps * 480
        scene_height = self.scene().height() if self.scene() else pw._octave_count * 12 * _NOTE_HEIGHT
        pitch = max(0, min(127, round((scene_height - scene_pos.y()) / _NOTE_HEIGHT) + pw._octave_start * 12))
        note_id = f"note_{len(pw._notes) + 1}_{tick}"
        new_note = NoteItem(note_id, pitch, tick, 480, 100)
        pw._notes[note_id] = new_note
        self.scene().addItem(new_note)
        new_note.setPos(tick, scene_height - pitch * _NOTE_HEIGHT)
        pw.note_added.emit(note_id, {"pitch": pitch, "start_tick": tick, "duration": 480, "velocity": 100})
