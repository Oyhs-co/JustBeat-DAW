"""Theme Integration - Integración de temas para widgets.

Mixin y utilities para que los widgets dependan
de la configuración de temas.
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor, QPalette, QFont
from PySide6.QtCore import Qt
import logging


logger = logging.getLogger(__name__)


class ThemeColors:
    """Colores del tema actual."""
    
    # Colores base
    BACKGROUND = "#2b2b2b"
    FOREGROUND = "#cccccc"
    BACKGROUND_LIGHT = "#333333"
    BACKGROUND_DARK = "#222222"
    
    # Acentos
    PRIMARY = "#00d4ff"      # Cyan neón
    SECONDARY = "#ff00ff"    # Magenta
    ACCENT = "#00ff88"       # Verde neón
    
    # Estados
    SUCCESS = "#4caf50"
    WARNING = "#ff9800"
    ERROR = "#f44336"
    INFO = "#2196f3"
    
    # Texto
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#aaaaaa"
    TEXT_DISABLED = "#666666"
    
    # Bordes
    BORDER = "#444444"
    BORDER_LIGHT = "#555555"
    
    @classmethod
    def get_color(cls, name: str, default: str = "#cccccc") -> str:
        """Obtener color por nombre.
        
        Args:
            name: Nombre del color
            default: Color por defecto
            
        Returns:
            Color en hex
        """
        return getattr(cls, name.upper(), default)
    
    @classmethod
    def from_dict(cls, colors: Dict[str, str]) -> None:
        """Actualizar colores desde diccionario.
        
        Args:
            colors: Diccionario de colores
        """
        for name, value in colors.items():
            if hasattr(cls, name.upper()):
                setattr(cls, name.upper(), value)


class ThemeStylesheet:
    """Generador de stylesheets basados en tema."""
    
    @staticmethod
    def widget() -> str:
        """Stylesheet base para widgets."""
        return f"""
            QWidget {{
                background-color: {ThemeColors.BACKGROUND};
                color: {ThemeColors.FOREGROUND};
                border: 1px solid {ThemeColors.BORDER};
            }}
        """
    
    @staticmethod
    def button(primary: bool = False) -> str:
        """Stylesheet para botones.
        
        Args:
            primary: Si es botón primario
        """
        if primary:
            return f"""
                QPushButton {{
                    background-color: {ThemeColors.PRIMARY};
                    color: #000000;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #33e5ff;
                }}
                QPushButton:pressed {{
                    background-color: #00b8d9;
                }}
                QPushButton:disabled {{
                    background-color: #444444;
                    color: #666666;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: {ThemeColors.BACKGROUND_LIGHT};
                    color: {ThemeColors.FOREGROUND};
                    border: 1px solid {ThemeColors.BORDER};
                    padding: 8px 16px;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    background-color: {ThemeColors.BORDER};
                }}
                QPushButton:pressed {{
                    background-color: {ThemeColors.BACKGROUND_DARK};
                }}
            """
    
    @staticmethod
    def slider() -> str:
        """Stylesheet para sliders."""
        return f"""
            QSlider::groove:horizontal {{
                background: {ThemeColors.BACKGROUND_DARK};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {ThemeColors.PRIMARY};
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::sub-page:horizontal {{
                background: {ThemeColors.PRIMARY};
                border-radius: 3px;
            }}
        """
    
    @staticmethod
    def label(bold: bool = False) -> str:
        """Stylesheet para labels.
        
        Args:
            bold: Si es texto bold
        """
        weight = "bold" if bold else "normal"
        return f"""
            QLabel {{
                color: {ThemeColors.TEXT_PRIMARY};
                font-weight: {weight};
            }}
        """
    
    @staticmethod
    def group_box() -> str:
        """Stylesheet para group boxes."""
        return f"""
            QGroupBox {{
                border: 1px solid {ThemeColors.BORDER};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                background-color: {ThemeColors.BACKGROUND_LIGHT};
            }}
            QGroupBox::title {{
                color: {ThemeColors.PRIMARY};
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 4px;
            }}
        """
    
    @staticmethod
    def dock_widget() -> str:
        """Stylesheet para dock widgets."""
        return f"""
            QDockWidget {{
                background-color: {ThemeColors.BACKGROUND};
                titlebar-close-icon: url(close.png);
                titlebar-normal-icon: url(float.png);
            }}
            QDockWidget::title {{
                background-color: {ThemeColors.BACKGROUND_LIGHT};
                text-align: left;
                padding: 4px;
                border-bottom: 1px solid {ThemeColors.BORDER};
            }}
            QDockWidget::close-button, QDockWidget::float-button {{
                background: transparent;
                border: none;
                padding: 2px;
            }}
        """
    
    @staticmethod
    def menu() -> str:
        """Stylesheet para menús."""
        return f"""
            QMenuBar {{
                background-color: {ThemeColors.BACKGROUND_LIGHT};
                color: {ThemeColors.FOREGROUND};
                border-bottom: 1px solid {ThemeColors.BORDER};
            }}
            QMenuBar::item:selected {{
                background-color: {ThemeColors.PRIMARY};
                color: #000000;
            }}
            QMenu {{
                background-color: {ThemeColors.BACKGROUND_LIGHT};
                color: {ThemeColors.FOREGROUND};
                border: 1px solid {ThemeColors.BORDER};
            }}
            QMenu::item:selected {{
                background-color: {ThemeColors.PRIMARY};
                color: #000000;
            }}
        """
    
    @staticmethod
    def scroll_bar() -> str:
        """Stylesheet para scroll bars."""
        return f"""
            QScrollBar:vertical {{
                background: {ThemeColors.BACKGROUND_DARK};
                width: 12px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {ThemeColors.BORDER};
                min-height: 20px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {ThemeColors.PRIMARY};
            }}
            QScrollBar:horizontal {{
                background: {ThemeColors.BACKGROUND_DARK};
                height: 12px;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: {ThemeColors.BORDER};
                min-width: 20px;
                border-radius: 6px;
            }}
        """


class ThemeMixin:
    """Mixin para widgets con soporte de tema.
    
    Uso:
        class MyWidget(ThemeMixin, QWidget):
            def __init__(self):
                super().__init__()
                self.apply_theme()
    """
    
    def apply_theme(self) -> None:
        """Aplicar tema al widget."""
        self.setStyleSheet(ThemeStylesheet.widget())
    
    def update_theme(self) -> None:
        """Actualizar tema (llamar cuando cambie el tema)."""
        self.apply_theme()


def apply_theme_to_widget(widget: QWidget, theme_type: str = "widget") -> None:
    """Aplicar tema a un widget.
    
    Args:
        widget: Widget a aplicar
        theme_type: Tipo de tema (widget, button, slider, etc.)
    """
    stylesheet = getattr(ThemeStylesheet, theme_type, ThemeStylesheet.widget)()
    widget.setStyleSheet(stylesheet)


def create_colored_button(text: str, color: str) -> str:
    """Crear stylesheet para botón con color.
    
    Args:
        text: Texto del botón
        color: Color de fondo
        
    Returns:
        Stylesheet
    """
    return f"""
        QPushButton {{
            background-color: {color};
            color: #ffffff;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {color}dd;
        }}
        QPushButton:pressed {{
            background-color: {color}aa;
        }}
    """
