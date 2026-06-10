"""AutomationLane widget - UI for displaying and editing automation curves."""

import logging
from typing import Optional, List, Tuple, Callable

from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QMouseEvent, QPainterPath
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSlider
)

from src.domain.entities.automation.automation_track import (
    AutomationTrack, AutomationMode, AutomationParameter
)
from src.domain.entities.automation.automation_point import AutomationPoint

# Theme Integration
from src.presentation.styles.theme_integration import ThemeMixin

# Logger for this module
logger = logging.getLogger(__name__)


class AutomationCurveEditor(QWidget):
    """Widget for displaying and editing an automation curve.
    
    Signals:
        point_added: Emitted when a point is added (time, value)
        point_moved: Emitted when a point is moved (index, time, value)
        point_removed: Emitted when a point is removed (index)
    """
    
    point_added = Signal(float, float)
    point_moved = Signal(int, float, float)
    point_removed = Signal(int)
    
    def __init__(
        self,
        automation_curve=None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._curve = automation_curve
        self._points: List[AutomationPoint] = []
        self._selected_point: Optional[int] = None
        self._is_dragging = False
        self._drag_index: Optional[int] = None
        
        # UI settings
        self._background_color = QColor("#1a1a2e")
        self._grid_color = QColor("#2a2a4e")
        self._curve_color = QColor("#00ff00")
        self._point_color = QColor("#ffffff")
        self._selection_color = QColor("#ffff00")
        
        self.setMinimumHeight(100)
        self.setMaximumHeight(200)
    
    def set_curve(self, curve) -> None:
        """Set the automation curve to display."""
        self._curve = curve
        if curve and curve.points:
            self._points = list(curve.points)
        else:
            self._points = []
        self.update()
    
    def paintEvent(self, event) -> None:
        """Paint the automation curve."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), self._background_color)
        
        # Grid
        self._draw_grid(painter)
        
        # Curve
        self._draw_curve(painter)
        
        # Points
        self._draw_points(painter)
    
    def _draw_grid(self, painter: QPainter) -> None:
        """Draw background grid."""
        painter.setPen(QPen(self._grid_color, 1))
        
        # Vertical lines (time divisions)
        width = self.width()
        num_vertical = 16  # 16 steps default
        for i in range(num_vertical + 1):
            x = int(width * i / num_vertical)
            painter.drawLine(x, 0, x, self.height())
        
        # Horizontal lines (value divisions)
        height = self.height()
        num_horizontal = 10
        for i in range(num_horizontal + 1):
            y = int(height * i / num_horizontal)
            painter.drawLine(0, y, width, y)
    
    def _draw_curve(self, painter: QPainter) -> None:
        """Draw the automation curve."""
        if len(self._points) < 2:
            return
        
        path = QPainterPath()
        
        # Convert points to screen coordinates
        points = [self._point_to_screen(p) for p in self._points]
        
        path.moveTo(points[0])
        for i in range(1, len(points)):
            # Draw line to next point (simplified - no bezier yet)
            path.lineTo(points[i])
        
        painter.setPen(QPen(self._curve_color, 2))
        painter.drawPath(path)
    
    def _draw_points(self, painter: QPainter) -> None:
        """Draw automation points."""
        for i, point in enumerate(self._points):
            screen_pos = self._point_to_screen(point)
            
            # Select color based on selection
            if i == self._selected_point:
                painter.setPen(QPen(self._selection_color, 2))
                painter.setBrush(QColor(self._selection_color))
            else:
                painter.setPen(QPen(self._point_color, 1))
                painter.setBrush(QColor(self._point_color))
            
            # Draw point as circle
            radius = 6
            painter.drawEllipse(
                int(screen_pos.x() - radius),
                int(screen_pos.y() - radius),
                radius * 2,
                radius * 2
            )
    
    def _point_to_screen(self, point: AutomationPoint) -> QPointF:
        """Convert automation point to screen coordinates."""
        # Time: 0 to 16 (or more) beats -> 0 to width
        # Value: 0 to 1 -> height to 0 (inverted Y)
        
        # Get the time range from the curve
        max_time = 16.0  # Default
        if self._curve and self._curve.points:
            max_time = max(p.time for p in self._curve.points)
            if max_time < 16:
                max_time = 16
        
        x = (point.time / max_time) * self.width()
        y = self.height() - (point.value * self.height())
        
        return QPointF(x, y)
    
    def _screen_to_point(self, screen_pos: QPointF) -> Tuple[float, float]:
        """Convert screen coordinates to automation point."""
        max_time = 16.0
        
        time = (screen_pos.x() / self.width()) * max_time
        value = 1.0 - (screen_pos.y() / self.height())
        
        # Clamp value
        value = max(0.0, min(1.0, value))
        
        return time, value
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for point selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            
            # Check if clicking on existing point
            for i, point in enumerate(self._points):
                screen_pos = self._point_to_screen(point)
                distance = (pos.x() - screen_pos.x())**2 + \
                          (pos.y() - screen_pos.y())**2
                
                if distance < 100:  # Within 10 pixels
                    self._selected_point = i
                    self._is_dragging = True
                    self._drag_index = i
                    self.update()
                    return
            
            # If not clicking on point, add new point
            time, value = self._screen_to_point(pos)
            self.point_added.emit(time, value)
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for point dragging."""
        if self._is_dragging and self._drag_index is not None:
            time, value = self._screen_to_point(event.pos())
            self.point_moved.emit(self._drag_index, time, value)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        self._is_dragging = False
        self._drag_index = None
    
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle double click to remove point."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            
            # Check if clicking on existing point
            for i, point in enumerate(self._points):
                screen_pos = self._point_to_screen(point)
                distance = (pos.x() - screen_pos.x())**2 + \
                          (pos.y() - screen_pos.y())**2
                
                if distance < 100:  # Within 10 pixels
                    self.point_removed.emit(i)
                    return


class AutomationLane(ThemeMixin, QWidget):
    """Widget for displaying and editing automation for a track.
    
    This widget shows:
    - Parameter selector
    - Automation mode selector
    - Automation curve editor
    - Clear button
    """
    
    # Signals
    point_added = Signal(float, float)
    point_moved = Signal(int, float, float)
    point_removed = Signal(int)
    
    def __init__(
        self,
        track_id: str = "",
        presentation_model: Optional[object] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        logger.info(f"Initializing AutomationLane for track_id: {track_id}")
        try:
            ThemeMixin.__init__(self)
            super().__init__(parent)
            
            self._track_id = track_id
            self._model = presentation_model
            self._automation_track = AutomationTrack(track_id=track_id)
            
            self._setup_ui()
            self.apply_theme()
            logger.info("AutomationLane initialized successfully")
        except Exception as e:
            logger.exception(f"Error initializing AutomationLane: {e}")
            raise

    def set_track(self, track_id: str) -> None:
        """Set the track to display automation for.
        
        Args:
            track_id: ID of the track
        """
        if track_id == self._track_id:
            return
        logger.info(f"AutomationLane switching to track: {track_id}")
        self._track_id = track_id
        self._automation_track = AutomationTrack(track_id=track_id)
        self._update_curve()
    
    def _setup_ui(self) -> None:
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with controls
        header = QHBoxLayout()
        
        # Parameter selector
        self._param_combo = QComboBox()
        self._param_combo.addItems(AutomationParameter.ALL)
        self._param_combo.setCurrentText(AutomationParameter.VOLUME)
        self._param_combo.currentTextChanged.connect(self._on_param_changed)
        header.addWidget(QLabel("Parameter:"))
        header.addWidget(self._param_combo)
        
        # Mode selector
        self._mode_combo = QComboBox()
        self._mode_combo.addItems([m.value for m in AutomationMode])
        self._mode_combo.setCurrentText(AutomationMode.READ.value)
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        header.addWidget(QLabel("Mode:"))
        header.addWidget(self._mode_combo)
        
        # Clear button
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._on_clear)
        header.addWidget(self._clear_btn)
        
        header.addStretch()
        
        layout.addLayout(header)
        
        # Curve editor
        self._curve_editor = AutomationCurveEditor()
        self._curve_editor.point_added.connect(self._on_point_added)
        self._curve_editor.point_moved.connect(self._on_point_moved)
        self._curve_editor.point_removed.connect(self._on_point_removed)
        layout.addWidget(self._curve_editor)
        
        # Initial curve
        self._update_curve()
    
    def _on_param_changed(self, param: str) -> None:
        """Handle parameter selection change."""
        self._update_curve()
    
    def _on_mode_changed(self, mode: str) -> None:
        """Handle mode selection change."""
        self._automation_track.set_mode(AutomationMode(mode))
    
    def _on_clear(self) -> None:
        """Clear all automation points."""
        param = self._param_combo.currentText()
        curve = self._automation_track.get_curve(param)
        if curve:
            curve.clear()
            self._update_curve()
    
    def _on_point_added(self, time: float, value: float) -> None:
        """Handle new point added."""
        param = self._param_combo.currentText()
        self._automation_track.add_point(param, time, value)
        self._update_curve()
    
    def _on_point_moved(self, index: int, time: float, value: float) -> None:
        """Handle point moved."""
        param = self._param_combo.currentText()
        curve = self._automation_track.get_curve(param)
        if curve and 0 <= index < len(curve.points):
            curve.points[index].time = time
            curve.points[index].value = value
            curve.points.sort(key=lambda p: p.time)
            self._update_curve()
    
    def _on_point_removed(self, index: int) -> None:
        """Handle point removed."""
        param = self._param_combo.currentText()
        curve = self._automation_track.get_curve(param)
        if curve and 0 <= index < len(curve.points):
            curve.remove_point(index)
            self._update_curve()
    
    def _update_curve(self) -> None:
        """Update the curve editor with current curve."""
        param = self._param_combo.currentText()
        curve = self._automation_track.get_curve(param)
        self._curve_editor.set_curve(curve)
    
    def get_automation_track(self) -> AutomationTrack:
        """Get the automation track."""
        return self._automation_track
