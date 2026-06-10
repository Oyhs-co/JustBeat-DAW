"""Style Manager - Tema base qt-material + overrides QSS para DAW.

Carga qt-material como tema base profesional y aplica QSS
específico de widgets DAW (sequencer, mixer, piano roll, etc.)
como overrides.
"""

from pathlib import Path
from typing import Optional
import logging

from PySide6.QtWidgets import QApplication


logger = logging.getLogger(__name__)


class StyleManager:
    """Gestor de estilos con qt-material como base + QSS DAW.

    Uso:
        StyleManager.get_instance().load_styles(app)
        StyleManager.get_instance().set_theme("light", app)
    """

    _instance: Optional["StyleManager"] = None

    THEME_MAP = {
        "dark": "dark_cyan.xml",
        "light": "light_cyan.xml",
    }

    DAW_QSS_FILES = [
        "sequencer.qss",
        "synthesizer.qss",
        "mixer.qss",
        "piano_roll.qss",
        "dialogs.qss",
        "virtual_keyboard.qss",
    ]

    def __init__(self):
        self._styles_dir = Path(__file__).parent
        self._current_theme: str = "dark"
        self._loaded = False

    @classmethod
    def get_instance(cls) -> "StyleManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current_theme(self) -> str:
        return self._current_theme

    def load_styles(self, app: QApplication) -> bool:
        """Cargar y aplicar qt-material + overrides DAW."""
        if self._loaded:
            return True

        try:
            self._apply_material_theme(app)
            self._apply_daw_overrides(app)

            self._loaded = True
            logger.info(
                f"Estilos cargados: qt-material ({self._current_theme}) + DAW QSS"
            )
            return True

        except Exception as e:
            logger.error(f"Error cargando estilos: {e}", exc_info=True)
            return False

    def _apply_material_theme(self, app: QApplication) -> None:
        """Aplicar qt-material como tema base."""
        theme_file = self.THEME_MAP.get(self._current_theme, "dark_cyan.xml")
        try:
            from qt_material import apply_stylesheet
            apply_stylesheet(app, theme=theme_file)
            logger.debug(f"qt-material aplicado: {theme_file}")
        except ImportError:
            logger.warning(
                "qt-material no instalado, usando fallback QSS clásico"
            )
            self._apply_classic_fallback(app)

    def _apply_classic_fallback(self, app: QApplication) -> None:
        """Fallback si qt-material no está disponible."""
        qss = self._load_stylesheet("neon_wave.qss")
        if qss:
            app.setStyleSheet(qss)

    def _apply_daw_overrides(self, app: QApplication) -> None:
        """Aplicar QSS específico de widgets DAW sobre el tema base."""
        daw_qss_parts = []
        for filename in self.DAW_QSS_FILES:
            qss = self._load_stylesheet(filename)
            if qss:
                daw_qss_parts.append(qss)

        if daw_qss_parts:
            daw_qss = "\n\n".join(daw_qss_parts)
            current = app.styleSheet() or ""
            app.setStyleSheet(current + "\n\n" + daw_qss)

    def _load_stylesheet(self, filename: str) -> str:
        """Cargar un archivo QSS del directorio de estilos."""
        filepath = self._styles_dir / filename
        if not filepath.exists():
            logger.debug(f"QSS no encontrado: {filename}")
            return ""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Error cargando {filename}: {e}")
            return ""

    def set_theme(self, theme: str, app: QApplication) -> bool:
        """Cambiar el tema (dark/light) y recargar."""
        if theme not in self.THEME_MAP:
            logger.warning(f"Tema no soportado: {theme}, usando dark")
            theme = "dark"

        self._current_theme = theme
        self._loaded = False
        return self.load_styles(app)

    def reload_styles(self, app: QApplication) -> bool:
        """Recargar todos los estilos."""
        self._loaded = False
        return self.load_styles(app)

    def get_available_themes(self) -> list[str]:
        return list(self.THEME_MAP.keys())


# === Funciones de conveniencia ===


def load_application_styles(app: QApplication) -> bool:
    return StyleManager.get_instance().load_styles(app)


def reload_application_styles(app: QApplication) -> bool:
    return StyleManager.get_instance().reload_styles(app)


def get_current_theme() -> str:
    return StyleManager.get_instance().current_theme


def set_application_theme(theme: str, app: QApplication) -> bool:
    return StyleManager.get_instance().set_theme(theme, app)
