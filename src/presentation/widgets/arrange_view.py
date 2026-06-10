"""Arrange View - Timeline de arreglo profesional.

Características:
- Time ruler con bars numerados y subdivisiones
- Clips coloreados por track con nombre y duración
- Drag para mover clips con snap
- Resize clips desde bordes
- Split clip en playhead (tecla S)
- Loop region ajustable en la regla
- Markers en la regla
- Playhead con glow
- Zoom horizontal (Ctrl+scroll), vertical (drag separador)
- Pattern clips (sólido) vs audio clips (forma de onda)
"""

import logging
import math
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsSimpleTextItem, QPushButton, QComboBox,
    QSlider, QMenu, QScrollBar, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QBrush, QWheelEvent,
    QMouseEvent, QKeyEvent, QPainterPath
)

from src.presentation.styles.pro_theme import ProTheme
from src.presentation.styles.icons import Icons

logger = logging.getLogger(__name__)

_TRACK_HEIGHT = 48
_RULER_HEIGHT = 24
_MIN_TRACK_HEIGHT = 24
_SNAP_OPTIONS = ["1/1", "1/2", "1/4", "1/8", "1/16"]


def _ticks_to_bars(ticks: int) -> str:
    bars = ticks // 1920 + 1
    beats = (ticks % 1920) // 480 + 1
    return f"{bars}.{beats}"


class ClipItem(QGraphicsRectItem):
    """Item gráfico para un clip en el arrange."""

    def __init__(self, clip_id: str, name: str, color: str,
                 track_index: int, start_tick: int, length_ticks: int,
                 is_audio: bool = False, parent=None):
        super().__init__(parent)
        self.clip_id = clip_id
        self.clip_name = name
        self._color = color
        self.track_index = track_index
        self.start_tick = start_tick
        self.length_ticks = length_ticks
        self.is_audio = is_audio

        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)
        self._update_appearance()

    def _update_appearance(self):
        color = QColor(self._color)
        if self.is_audio:
            self.setBrush(QBrush(color.lighter(130)))
        else:
            self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(150), 1) if not self.isSelected()
                    else QPen(QColor("#ffffff"), 2))

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        r = self.rect()
        if r.width() > 30:
            painter.setPen(QColor(255, 255, 255, 180))
            painter.setFont(QFont("monospace", 7, QFont.Bold))
            painter.drawText(r.adjusted(4, 2, -4, -2), Qt.AlignLeft | Qt.AlignTop, self.clip_name)
            dur = _ticks_to_bars(self.length_ticks)
            painter.setPen(QColor(255, 255, 255, 100))
            painter.setFont(QFont("monospace", 6))
            painter.drawText(r.adjusted(4, 0, -4, -2), Qt.AlignLeft | Qt.AlignBottom, dur)


class MarkerItem(QGraphicsRectItem):
    """Marcador en la regla."""

    def __init__(self, text: str, tick: int, parent=None):
        super().__init__(parent)
        self.marker_text = text
        self.tick = tick


class ArrangeScene(QGraphicsScene):
    """Escena del arrange con rendering del timeline."""

    def __init__(self, parent=None):
        super().__init__(parent)


class ArrangeViewWidget(QWidget):
    """Vista de arrange profesional."""

    clip_selected = Signal(str)
    clip_moved = Signal(str, int)
    clip_resized = Signal(str, int)
    delete_requested = Signal(str)
    rename_requested = Signal(str, str)
    color_changed = Signal(str, str)
    marker_added = Signal(int, str)
    split_requested = Signal(str)
    edit_in_piano_roll = Signal(str)
    duplicate_requested = Signal(str)

    def __init__(self, presentation_model=None, parent=None):
        super().__init__(parent)
        self._model = presentation_model
        self._tracks: List[Dict] = []
        self._clips: Dict[str, ClipItem] = {}
        self._markers: List[Dict] = []
        self._playback_tick = 0
        self._zoom = 1.0
        self._total_bars = 16
        self._snap_index = 2
        self._loop_start = -1
        self._loop_end = -1
        self._track_heights: List[int] = []
        self._dragging_clip: Optional[ClipItem] = None
        self._resizing_clip: Optional[ClipItem] = None
        self._drag_start_pos = QPointF()

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
                self._model.track_added.connect(self._on_tracks_changed)
                self._model.track_removed.connect(self._on_tracks_changed)
                self._model.position_changed.connect(self._on_position_changed)
                self._model.project_loaded.connect(self._on_tracks_changed)
                self._model.arrangement_changed.connect(self._redraw)
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
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(6, 3, 6, 3)
        tb.setSpacing(4)

        title = QLabel("Arrange")
        title.setStyleSheet(f"color: {c.text_primary}; font-weight: bold; font-size: 10px; background: transparent;")
        tb.addWidget(title)

        tb.addStretch()

        snap_label = QLabel("Snap:")
        snap_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 9px; background: transparent;")
        tb.addWidget(snap_label)

        self._snap_combo = QComboBox()
        self._snap_combo.addItems(_SNAP_OPTIONS)
        self._snap_combo.setCurrentIndex(self._snap_index)
        self._snap_combo.setFixedWidth(55)
        tb.addWidget(self._snap_combo)

        zoom_label = QLabel("Zoom:")
        zoom_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 9px; background: transparent;")
        tb.addWidget(zoom_label)

        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setRange(20, 200)
        self._zoom_slider.setValue(100)
        self._zoom_slider.setFixedWidth(60)
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)
        tb.addWidget(self._zoom_slider)

        layout.addWidget(toolbar)

        # Scene
        self._scene = QGraphicsScene()
        self._view = ArrangeGraphicsView(self._scene)
        self._view.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._view.setStyleSheet(f"""
            QGraphicsView {{ border: none; background: {c.bg_primary}; }}
        """)
        layout.addWidget(self._view, 1)

        self._load_tracks()

    def _on_zoom_changed(self, value: int):
        self._zoom = value / 100.0
        self._redraw()

    def _snap_ticks(self) -> int:
        divisions = [1920, 960, 480, 240, 120]
        return divisions[self._snap_index]

    def _pixels_per_beat(self) -> float:
        return 40.0 * self._zoom

    def _total_width(self) -> float:
        return self._total_bars * 4 * self._pixels_per_beat()

    def _load_tracks(self):
        if self._model:
            try:
                project = self._model.current_project
                if project:
                    tracks_data = project.get_tracks()
                    self._tracks = []
                    c = ProTheme.get()
                    for i, t in enumerate(tracks_data):
                        color = c.track_colors[i % len(c.track_colors)]
                        self._tracks.append({"id": t.id, "name": t.name, "color": color})
                    self._track_heights = [_TRACK_HEIGHT] * len(self._tracks)
                    self._redraw()
            except AttributeError:
                pass

    def _redraw(self):
        self._scene.clear()
        self._clips.clear()

        c = ProTheme.get()
        ppb = self._pixels_per_beat()
        total_w = self._total_width()
        total_h = _RULER_HEIGHT + sum(self._track_heights)

        self._scene.setSceneRect(0, 0, total_w, total_h)
        self._scene.setBackgroundBrush(QColor(c.bg_primary))

        # Ruler
        ruler_rect = self._scene.addRect(
            0, 0, total_w, _RULER_HEIGHT,
            QPen(Qt.NoPen), QBrush(QColor(c.bg_secondary))
        )
        ruler_rect.setZValue(20)

        for bar in range(self._total_bars * 4):
            x = bar * ppb
            is_bar = bar % 4 == 0
            lh = 14 if is_bar else 8
            p = QPen(QColor(c.grid_line_bold), 2 if is_bar else 1)
            self._scene.addLine(x, _RULER_HEIGHT, x, _RULER_HEIGHT - lh, p).setZValue(21)

            if is_bar:
                txt = self._scene.addSimpleText(str(bar // 4 + 1), QFont("monospace", 8, QFont.Bold))
                txt.setBrush(QBrush(QColor(c.text_secondary)))
                txt.setPos(x + 3, 3)
                txt.setZValue(22)

        # Loop region
        if self._loop_start >= 0 and self._loop_end > self._loop_start:
            lx = self._loop_start * ppb
            lw = (self._loop_end - self._loop_start) * ppb
            loop = self._scene.addRect(
                lx, 0, lw, _RULER_HEIGHT,
                QPen(QColor(c.grid_playhead), 1),
                QBrush(QColor(c.grid_playhead_glow))
            )
            loop.setZValue(15)

        # Track rows
        y = _RULER_HEIGHT
        for i, track in enumerate(self._tracks):
            th = self._track_heights[i]
            bg = QColor(c.bg_surface).lighter(105) if i % 2 == 0 else QColor(c.bg_surface)
            self._scene.addRect(0, y, total_w, th, QPen(QColor(c.grid_line), 1), QBrush(bg)).setZValue(0)

            # Track label overlay
            txt = self._scene.addSimpleText(track["name"], QFont("monospace", 8, QFont.Bold))
            txt.setBrush(QBrush(QColor(c.text_tertiary)))
            txt.setPos(6, y + 4)
            txt.setZValue(5)

            # Grid lines
            for beat in range(self._total_bars * 4 + 1):
                gx = beat * ppb
                is_strong = beat % 4 == 0
                gp = QPen(QColor(c.grid_line).darker(120) if is_strong else QColor(c.grid_line), 1)
                self._scene.addLine(gx, y, gx, y + th, gp).setZValue(1)

            y += th

        # Clips
        if self._model:
            try:
                arrangement = self._model.current_project.arrangement
                for i, track in enumerate(self._tracks):
                    y0 = _RULER_HEIGHT + sum(self._track_heights[:i])
                    th = self._track_heights[i]
                    clips = arrangement.get_track_clips(track["id"])
                    for clip in clips:
                        cx = (clip.start_tick / 480) * ppb
                        cw = max(8, (clip.length_ticks / 480) * ppb)
                        item = ClipItem(
                            clip.id, clip.name, track["color"], i,
                            clip.start_tick, clip.length_ticks,
                            getattr(clip, 'clip_type', None) == 'audio'
                        )
                        item.setRect(0, 0, cw, th - 4)
                        item.setPos(cx, y0 + 2)
                        self._scene.addItem(item)
                        self._clips[clip.id] = item
            except AttributeError:
                pass

        # Markers
        for marker in self._markers:
            mx = (marker["tick"] / 480) * ppb
            path = QPainterPath()
            path.moveTo(mx, _RULER_HEIGHT)
            path.lineTo(mx + 6, _RULER_HEIGHT - 8)
            path.lineTo(mx - 6, _RULER_HEIGHT - 8)
            path.closeSubpath()
            marker_item = self._scene.addPath(path, QPen(Qt.NoPen), QBrush(QColor(c.accent_warning)))
            marker_item.setZValue(23)

            txt = self._scene.addSimpleText(marker["name"], QFont("monospace", 6))
            txt.setBrush(QBrush(QColor(c.accent_warning)))
            txt.setPos(mx - 10, _RULER_HEIGHT - 16)
            txt.setZValue(23)

        # Playhead
        phx = (self._playback_tick / 480) * ppb
        ph_h = _RULER_HEIGHT + sum(self._track_heights)
        self._playhead_item = self._scene.addLine(
            phx, 0, phx, ph_h,
            QPen(QColor(c.grid_playhead), 2)
        )
        self._playhead_item.setZValue(30)

        # Playhead glow
        glow = self._scene.addRect(
            phx - 2, 0, 4, ph_h,
            QPen(Qt.NoPen), QBrush(QColor(c.grid_playhead_glow))
        )
        glow.setZValue(29)

    def _on_tracks_changed(self, *args):
        self._load_tracks()

    def _on_position_changed(self, tick: int):
        self._playback_tick = tick
        ppb = self._pixels_per_beat()
        if hasattr(self, '_playhead_item') and self._playhead_item:
            phx = (tick / 480) * ppb
            ph_h = _RULER_HEIGHT + sum(self._track_heights)
            self._playhead_item.setLine(phx, 0, phx, ph_h)
            self._view.centerOn(phx, ph_h / 2)

    # === Public API ===

    def set_tracks(self, tracks: list):
        self._tracks = list(tracks)
        self._track_heights = [_TRACK_HEIGHT] * len(self._tracks)
        self._redraw()

    def get_tracks(self) -> list:
        return self._tracks

    def clear(self):
        self._scene.clear()
        self._tracks = []
        self._clips.clear()

    def set_playhead_position(self, tick: int):
        self._playback_tick = tick


class ArrangeGraphicsView(QGraphicsView):
    """QGraphicsView con zoom y manejo de clips."""

    edit_in_piano_roll = Signal(str)
    duplicate_requested = Signal(str)
    split_requested = Signal(str)
    delete_requested = Signal(str)
    rename_requested = Signal(str, str)
    color_changed = Signal(str, str)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMouseTracking(True)
        self._is_panning = False
        self._pan_start = QPointF()
        self._resize_margin = 6

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.12
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

        item = self.itemAt(event.pos())

        if event.button() == Qt.MouseButton.RightButton:
            if isinstance(item, ClipItem):
                self._show_clip_menu(item, event.globalPos())
            else:
                self._add_marker(event.pos())
            return

        if isinstance(item, ClipItem):
            self._handle_clip_press(item, event)
        elif event.button() == Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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

    def mouseReleaseEvent(self, event):
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_S:
            self._split_at_playhead()
        super().keyPressEvent(event)

    def _handle_clip_press(self, item: ClipItem, event):
        self._dragging_clip = item
        self._drag_start_pos = event.scenePos()
        self._drag_original_x = item.scenePos().x()
        if event.modifiers() & Qt.ShiftModifier:
            self._current_selection.add(item.clip_id)
        elif item.clip_id not in self._current_selection:
            self._current_selection = {item.clip_id}
        self.clip_selected.emit(item.clip_id)

    def _rename_clip(self, item: ClipItem):
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self, "Rename Clip", "Clip name:",
            text=item.clip_name
        )
        if ok and new_name.strip():
            item.clip_name = new_name.strip()
            item._update_appearance()
            self.rename_requested.emit(item.clip_id, item.clip_name)

    def _set_clip_color(self, item: ClipItem, color: str):
        item._color = color
        item._update_appearance()
        self.color_changed.emit(item.clip_id, color)

    def _show_clip_menu(self, item: ClipItem, global_pos):
        c = ProTheme.get()
        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{ background: {c.menu_bg}; color: {c.menu_text};
                     border: 1px solid {c.menu_border}; border-radius: 4px; padding: 4px; }}
            QMenu::item {{ padding: 4px 16px; border-radius: 2px; font-size: 9px; }}
            QMenu::item:selected {{ background: {c.menu_hover}; color: {c.text_accent}; }}
            QMenu::submenu {{ background: {c.menu_bg}; border: 1px solid {c.menu_border};
                             border-radius: 4px; padding: 4px; }}
        """)

        edit = menu.addAction("Edit in Piano Roll")
        edit.setIcon(Icons.EDIT)
        edit.triggered.connect(lambda: self.edit_in_piano_roll.emit(item.clip_id))

        dup = menu.addAction("Duplicate")
        dup.setIcon(Icons.COPY)
        dup.triggered.connect(lambda: self.duplicate_requested.emit(item.clip_id))

        split = menu.addAction("Split")
        split.setIcon(Icons.CUT)
        split.triggered.connect(lambda: self.split_requested.emit(item.clip_id))

        menu.addSeparator()
        delete = menu.addAction("Delete")
        delete.setIcon(Icons.DELETE)
        delete.triggered.connect(lambda: self.delete_requested.emit(item.clip_id))

        menu.addSeparator()
        rename = menu.addAction("Rename")
        rename.setIcon(Icons.EDIT)
        rename.triggered.connect(lambda: self._rename_clip(item))

        colors_menu = menu.addMenu(Icons.CHECK, "Color")
        for hex_c in c.track_colors[:8]:
            color_action = colors_menu.addAction(f"\u25A0 {hex_c}")
            color_action.triggered.connect(lambda checked, col=hex_c: self._set_clip_color(item, col))

        menu.exec(global_pos)

    def _add_marker(self, pos):
        tick = int(pos)
        name = f"Marker {len([m for m in self._markers if m['name'].startswith('Marker')]) + 1}"
        self._markers.append({"tick": tick, "name": name, "color": "#ffab00"})
        self._redraw()
        self.marker_added.emit(tick, name)

    def _split_at_playhead(self):
        tick = self._playback_tick
        clips_to_split = [(cid, c) for cid, c in self._clips.items()
                          if c.start_tick < tick < c.start_tick + c.duration]
        for cid, clip in clips_to_split:
            self.split_requested.emit(cid)
            logger.info(f"Split clip {cid} at tick {tick}")
