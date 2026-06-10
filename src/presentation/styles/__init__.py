"""Styles Module - Sistema de estilos con qt-material + QSS DAW.

Proporciona un sistema de temas profesional con qt-material como base
y hojas de estilo QSS específicas para widgets DAW.
"""

from .style_manager import (
    StyleManager,
    load_application_styles,
    reload_application_styles,
    get_current_theme,
    set_application_theme,
)

__all__ = [
    "StyleManager",
    "load_application_styles",
    "reload_application_styles",
    "get_current_theme",
    "set_application_theme",
]
