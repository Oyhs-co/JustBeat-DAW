"""Sistema de notificaciones toast para JustBeat-DAW.

Proporciona notificaciones animadas en la esquina superior derecha
con 4 tipos: Success, Error, Info, Warning.

Uso:
    from src.presentation.widgets.toast import ToastManager

    ToastManager.show_info("Project saved successfully")
    ToastManager.show_error("Export failed")
    ToastManager.show_success("Track added")
    ToastManager.show_warning("High CPU usage")
"""

from enum import Enum
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtGui import QFont

from src.presentation.styles.pro_theme import ProTheme
from src.presentation.styles.icons import Icons


logger = __import__("logging").getLogger(__name__)


class ToastType(Enum):
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"


def _get_type_config(toast_type: ToastType) -> dict:
    """Obtener configuración para un tipo de toast.
    
    Los iconos se resuelven lazy para evitar importar qtawesome
    antes de que exista un QApplication.
    """
    from src.presentation.styles.icons import Icons
    _ICON_MAP = {
        ToastType.SUCCESS: Icons.CHECK,
        ToastType.ERROR: Icons.CROSS,
        ToastType.INFO: Icons.INFO,
        ToastType.WARNING: Icons.WARNING,
    }
    return {
        "bg": {
            ToastType.SUCCESS: "rgba(0, 230, 118, 0.15)",
            ToastType.ERROR: "rgba(255, 23, 68, 0.15)",
            ToastType.INFO: "rgba(68, 138, 255, 0.15)",
            ToastType.WARNING: "rgba(255, 171, 0, 0.15)",
        }[toast_type],
        "border": {
            ToastType.SUCCESS: "#00e676",
            ToastType.ERROR: "#ff1744",
            ToastType.INFO: "#448aff",
            ToastType.WARNING: "#ffab00",
        }[toast_type],
        "icon_color": {
            ToastType.SUCCESS: "#00e676",
            ToastType.ERROR: "#ff1744",
            ToastType.INFO: "#448aff",
            ToastType.WARNING: "#ffab00",
        }[toast_type],
        "icon": _ICON_MAP[toast_type],
    }


class Toast(QFrame):
    """Widget de notificación individual.

    Aparece con slide-in desde la derecha y se cierra con fade-out.
    """

    DISPLAY_DURATION = 3000
    ANIM_DURATION = 250

    def __init__(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        parent: Optional[QWidget] = None,
        duration: int = DISPLAY_DURATION,
    ):
        super().__init__(parent)
        self._toast_type = toast_type
        self._config = _get_type_config(toast_type)
        self._duration = duration
        self._closing = False

        self._message = message
        self._setup_ui()
        self._apply_style()
        self._start_timers()

    def _setup_ui(self):
        self.setFixedWidth(320)
        self.setMinimumHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        self._icon_label = QLabel()
        from PySide6.QtCore import QSize
        self._icon_label.setPixmap(self._config["icon"].pixmap(QSize(16, 16)))
        self._icon_label.setFont(QFont("Segoe UI", 14))
        self._icon_label.setStyleSheet(f"color: {self._config['icon_color']};")
        self._icon_label.setFixedWidth(20)
        layout.addWidget(self._icon_label)

        self._message_label = QLabel(self._message)
        self._message_label.setWordWrap(True)
        self._message_label.setStyleSheet("color: #f0f0f0; font-size: 10pt;")
        layout.addWidget(self._message_label, 1)

        self._close_btn = QPushButton()
        self._close_btn.setIcon(Icons.CLOSE)
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #606070; border: none;
                font-size: 12px; padding: 0;
            }
            QPushButton:hover { color: #f0f0f0; }
        """)
        self._close_btn.clicked.connect(self._animate_out)
        layout.addWidget(self._close_btn)

        self.setLayout(layout)

    def _apply_style(self):
        c = ProTheme.get()
        self.setStyleSheet(f"""
            Toast {{
                background-color: {self._config['bg']};
                border: 1px solid {self._config['border']};
                border-radius: 6px;
            }}
        """)

    def _start_timers(self):
        QTimer.singleShot(60, self._animate_in)
        QTimer.singleShot(self._duration, self._animate_out)

    def _animate_in(self):
        parent_width = self.parent().width() if self.parent() else 0
        start_x = parent_width - 20
        end_x = parent_width - self.width() - 16

        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(self.ANIM_DURATION)
        anim.setStartValue(QPoint(start_x, self.pos().y()))
        anim.setEndValue(QPoint(end_x, self.pos().y()))
        anim.setEasingCurve(QEasingCurve.Type.OutBack)
        anim.start()

    def _animate_out(self):
        if self._closing:
            return
        self._closing = True

        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(200)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(self._on_closed)
        anim.start()

    def _on_closed(self):
        self.deleteLater()


class ToastManager:
    """Gestor singleton de notificaciones toast.

    Administra el apilamiento y posicionamiento de toasts
    en la esquina superior derecha de un widget contenedor.
    """

    _instance: Optional["ToastManager"] = None
    _container: Optional[QWidget] = None
    _active_toasts: list = []
    _spacing = 8

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def initialize(cls, container: QWidget):
        """Inicializar el gestor con un widget contenedor.

        Args:
            container: Widget padre donde aparecerán los toasts.
                       Generalmente el main_window o un overlay.
        """
        cls._container = container
        cls._active_toasts = []

    @classmethod
    def _show(cls, message: str, toast_type: ToastType, duration: int = Toast.DISPLAY_DURATION):
        if cls._container is None:
            logger.warning("ToastManager no inicializado. Llamar ToastManager.initialize(container)")
            return

        toast = Toast(message, toast_type, cls._container, duration)
        toast.show()

        cls._active_toasts.append(toast)
        cls._reposition_toasts()

        toast.destroyed.connect(lambda: cls._on_toast_destroyed(toast))

    @classmethod
    def _on_toast_destroyed(cls, toast: Toast):
        if toast in cls._active_toasts:
            cls._active_toasts.remove(toast)
        cls._reposition_toasts()

    @classmethod
    def _reposition_toasts(cls):
        y_offset = 12
        for toast in cls._active_toasts:
            if toast.isVisible():
                toast.move(toast.pos().x(), y_offset)
                y_offset += toast.height() + cls._spacing

    @classmethod
    def show_info(cls, message: str, duration: int = Toast.DISPLAY_DURATION):
        """Mostrar notificación informativa."""
        cls._show(message, ToastType.INFO, duration)

    @classmethod
    def show_success(cls, message: str, duration: int = Toast.DISPLAY_DURATION):
        """Mostrar notificación de éxito."""
        cls._show(message, ToastType.SUCCESS, duration)

    @classmethod
    def show_warning(cls, message: str, duration: int = Toast.DISPLAY_DURATION):
        """Mostrar notificación de advertencia."""
        cls._show(message, ToastType.WARNING, duration)

    @classmethod
    def show_error(cls, message: str, duration: int = Toast.DISPLAY_DURATION):
        """Mostrar notificación de error."""
        cls._show(message, ToastType.ERROR, duration)

    @classmethod
    def clear_all(cls):
        """Cerrar todas las notificaciones activas."""
        for toast in cls._active_toasts[:]:
            toast._animate_out()
        cls._active_toasts.clear()
