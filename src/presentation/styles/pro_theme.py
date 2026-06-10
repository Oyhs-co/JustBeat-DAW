"""Sistema de tema profesional para JustBeat-DAW.

Proporciona 3 variantes de color con glass morphism,
gradientes animados, sombras y elevaciones.

Variantes:
    - Obsidian: Dark primario con acento verde-cyan (#00d4aa)
    - Midnight: Blue-dark con acento azul (#4488ff)
    - Slate: Gris neutro con acento gris-azulado (#8888aa)

Uso:
    theme = ProTheme.get("obsidian")
    qss = theme.to_stylesheet()
    widget.setStyleSheet(qss)
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum


class ThemeVariant(Enum):
    """Variantes de tema disponibles."""
    OBSIDIAN = "obsidian"
    MIDNIGHT = "midnight"
    SLATE = "slate"


@dataclass
class GlassMorphism:
    """Configuración de glass morphism (efecto vidrio)."""
    enabled: bool = True
    background: str = "rgba(18, 18, 24, 0.85)"
    border: str = "rgba(255, 255, 255, 0.06)"
    blur_radius: int = 12
    shadow_opacity: float = 0.3


@dataclass
class GradientDef:
    """Definición de gradiente."""
    start: str = "#00d4aa"
    end: str = "#0088ff"
    angle: str = "180deg"  # Para QSS: qlineargradient


@dataclass
class ProColors:
    """Paleta de color profesional completa."""

    # Fondos
    bg_primary: str = "#0a0a0f"
    bg_secondary: str = "#121218"
    bg_tertiary: str = "#1a1a24"
    bg_surface: str = "#181820"
    bg_hover: str = "#222230"
    bg_active: str = "#2a2a3d"
    bg_elevated: str = "#1e1e2a"

    # Glass morphism
    glass_bg: str = "rgba(18, 18, 24, 0.85)"
    glass_border: str = "rgba(255, 255, 255, 0.06)"
    glass_highlight: str = "rgba(255, 255, 255, 0.03)"

    # Texto
    text_primary: str = "#f0f0f0"
    text_secondary: str = "#a0a0b0"
    text_tertiary: str = "#606070"
    text_accent: str = "#00d4aa"
    text_inverse: str = "#0a0a0f"

    # Acentos
    accent_primary: str = "#00d4aa"
    accent_secondary: str = "#0088cc"
    accent_success: str = "#00e676"
    accent_warning: str = "#ffab00"
    accent_danger: str = "#ff1744"
    accent_info: str = "#448aff"

    # Botones
    button_bg: str = "#222230"
    button_hover: str = "#2a2a3d"
    button_active: str = "#3a3a50"
    button_play: str = "#00d4aa"
    button_play_hover: str = "#00e8bb"
    button_stop: str = "#ff1744"
    button_stop_hover: str = "#ff3d5c"
    button_record: str = "#ff1744"
    button_record_active: str = "#ff5252"
    button_text: str = "#f0f0f0"

    # Sliders / Knobs
    slider_groove: str = "#2a2a3d"
    slider_handle: str = "#00d4aa"
    slider_fill: str = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d4aa, stop:1 #0088cc)"

    # Grid (sequencer / piano roll)
    grid_line: str = "#1e1e2a"
    grid_line_bold: str = "#2a2a3d"
    grid_active: str = "#00d4aa"
    grid_inactive: str = "#2a2a3d"
    grid_playhead: str = "#ff6600"
    grid_playhead_glow: str = "rgba(255, 102, 0, 0.3)"

    # Notas MIDI
    note_color: str = "#00d4aa"
    note_color_selected: str = "#66e6cc"
    note_color_ghost: str = "rgba(0, 212, 170, 0.2)"
    note_color_playback: str = "#ffab00"
    note_velocity_low: str = "rgba(0, 212, 170, 0.3)"
    note_velocity_high: str = "#00d4aa"

    # Piano roll
    piano_white: str = "#e8e8e8"
    piano_black: str = "#1a1a1a"
    piano_white_pressed: str = "#00d4aa"
    piano_black_pressed: str = "#00aa88"

    # Mixer - VU Meter
    meter_green: str = "#00e676"
    meter_yellow: str = "#ffab00"
    meter_red: str = "#ff1744"
    meter_bg: str = "#0a0a0f"
    meter_clip: str = "#ffffff"
    meter_gradient: str = (
        "qlineargradient(x1:0, y1:1, x2:0, y2:0, "
        "stop:0 #00e676, stop:0.6 #ffab00, stop:0.85 #ff1744)"
    )

    # Mixer - Mute/Solo
    mute_color: str = "#ffab00"
    mute_bg: str = "rgba(255, 171, 0, 0.15)"
    solo_color: str = "#00d4aa"
    solo_bg: str = "rgba(0, 212, 170, 0.15)"
    arm_color: str = "#ff1744"
    arm_bg: str = "rgba(255, 23, 68, 0.15)"

    # Transport
    transport_bg: str = "#0d0d14"
    transport_border: str = "rgba(255, 255, 255, 0.05)"
    time_display_bg: str = "#060608"
    time_display_color: str = "#00d4aa"

    # Bordes
    border_color: str = "rgba(255, 255, 255, 0.06)"
    border_focus: str = "#00d4aa"
    border_accent: str = "rgba(0, 212, 170, 0.3)"

    # Scrollbars
    scrollbar_bg: str = "transparent"
    scrollbar_handle: str = "rgba(255, 255, 255, 0.1)"
    scrollbar_handle_hover: str = "rgba(0, 212, 170, 0.5)"

    # Menús
    menu_bg: str = "#14141c"
    menu_hover: str = "rgba(0, 212, 170, 0.15)"
    menu_text: str = "#f0f0f0"
    menu_border: str = "rgba(255, 255, 255, 0.06)"
    menu_separator: str = "rgba(255, 255, 255, 0.06)"

    # Tooltips
    tooltip_bg: str = "#1a1a24"
    tooltip_text: str = "#f0f0f0"
    tooltip_border: str = "rgba(255, 255, 255, 0.1)"

    # Docks / Paneles
    dock_bg: str = "#0d0d14"
    dock_title_bg: str = "#12121a"
    dock_title_text: str = "#a0a0b0"
    dock_border: str = "rgba(255, 255, 255, 0.04)"

    # Colores de pista (para arrangement)
    track_colors: list = field(default_factory=lambda: [
        "#00d4aa", "#4488ff", "#ffab00", "#ff1744",
        "#aa66ff", "#ff66aa", "#00e676", "#ff8800",
        "#66ccff", "#cc66ff", "#ffcc00", "#ff6688",
    ])

    # Efectos visuales
    glow_color: str = "rgba(0, 212, 170, 0.15)"
    shadow_color: str = "rgba(0, 0, 0, 0.3)"
    overlay_color: str = "rgba(0, 0, 0, 0.5)"

    # Gradiente principal
    gradient_primary: str = (
        "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        "stop:0 #00d4aa, stop:1 #4488ff)"
    )

    # Gradiente para botón de play
    gradient_play: str = (
        "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        "stop:0 #00d4aa, stop:1 #00e676)"
    )

    # Gradiente para botón de stop
    gradient_stop: str = (
        "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        "stop:0 #ff1744, stop:1 #ff5252)"
    )


def _obsidian_colors() -> ProColors:
    """Paleta Obsidian - Dark con acento verde-cyan."""
    return ProColors(
        bg_primary="#0a0a0f",
        bg_secondary="#121218",
        bg_tertiary="#1a1a24",
        bg_surface="#181820",
        bg_hover="#222230",
        bg_active="#2a2a3d",
        bg_elevated="#1e1e2a",
        accent_primary="#00d4aa",
        accent_secondary="#0088cc",
        text_accent="#00d4aa",
        slider_handle="#00d4aa",
        note_color="#00d4aa",
        grid_active="#00d4aa",
        meter_green="#00e676",
        time_display_color="#00d4aa",
        button_play="#00d4aa",
    )


def _midnight_colors() -> ProColors:
    """Paleta Midnight - Blue-dark con acento azul."""
    return ProColors(
        bg_primary="#0a0a14",
        bg_secondary="#10101c",
        bg_tertiary="#181828",
        bg_surface="#141420",
        bg_hover="#1e1e30",
        bg_active="#262640",
        bg_elevated="#1c1c2e",
        accent_primary="#4488ff",
        accent_secondary="#66aaff",
        text_accent="#4488ff",
        slider_handle="#4488ff",
        note_color="#4488ff",
        grid_active="#4488ff",
        meter_green="#00e676",
        time_display_color="#4488ff",
        button_play="#4488ff",
        gradient_primary=(
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #4488ff, stop:1 #66aaff)"
        ),
        slider_fill=(
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #4488ff, stop:1 #66aaff)"
        ),
    )


def _slate_colors() -> ProColors:
    """Paleta Slate - Gris neutro con acento gris-azulado."""
    return ProColors(
        bg_primary="#0e0e0e",
        bg_secondary="#141414",
        bg_tertiary="#1c1c1c",
        bg_surface="#161616",
        bg_hover="#242424",
        bg_active="#2e2e2e",
        bg_elevated="#1a1a1a",
        accent_primary="#8888aa",
        accent_secondary="#666688",
        text_accent="#8888aa",
        slider_handle="#8888aa",
        note_color="#8888aa",
        grid_active="#8888aa",
        meter_green="#00e676",
        time_display_color="#8888aa",
        button_play="#8888aa",
        gradient_primary=(
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #8888aa, stop:1 #aaaacc)"
        ),
        slider_fill=(
            "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #8888aa, stop:1 #aaaacc)"
        ),
    )


class ProTheme:
    """Tema profesional con 3 variantes y utilidades QSS.

    Uso:
        theme = ProTheme.get("obsidian")
        qss = theme.to_stylesheet("QPushButton { ... }")
        widget.setStyleSheet(qss)
    """

    VARIANTS: Dict[str, ProColors] = {
        "obsidian": _obsidian_colors(),
        "midnight": _midnight_colors(),
        "slate": _slate_colors(),
    }

    _current: str = "obsidian"

    @classmethod
    def get(cls, variant: Optional[str] = None) -> ProColors:
        """Obtener paleta de colores para una variante.

        Args:
            variant: Nombre de la variante (obsidian, midnight, slate).
                     Si es None, devuelve la variante actual.

        Returns:
            ProColors con la paleta correspondiente.
        """
        if variant is not None:
            cls._current = variant
        return cls.VARIANTS.get(cls._current, cls.VARIANTS["obsidian"])

    @classmethod
    def set_variant(cls, variant: str) -> bool:
        """Cambiar la variante activa.

        Args:
            variant: Nombre de la variante.

        Returns:
            True si la variante existe.
        """
        if variant in cls.VARIANTS:
            cls._current = variant
            return True
        return False

    @classmethod
    def get_variant(cls) -> str:
        """Obtener nombre de la variante actual."""
        return cls._current

    @classmethod
    def get_available(cls) -> list:
        """Obtener lista de variantes disponibles."""
        return list(cls.VARIANTS.keys())

    @classmethod
    def to_stylesheet(cls, custom_qss: str = "") -> str:
        """Generar stylesheet QSS completo con la variante actual.

        Args:
            custom_qss: QSS adicional para añadir.

        Returns:
            String QSS completo.
        """
        c = cls.get()

        base = f"""
        QMainWindow, QWidget {{
            background-color: {c.bg_primary};
            color: {c.text_primary};
            font-family: "Segoe UI", "SF Pro Display", sans-serif;
            font-size: 10pt;
        }}

        QMainWindow::separator {{
            width: 1px;
            height: 1px;
            background-color: {c.border_color};
        }}

        /* === GLASS PANELS === */
        QFrame#glassPanel, QDockWidget {{
            background-color: {c.glass_bg};
            border: 1px solid {c.glass_border};
        }}

        QDockWidget::title {{
            background-color: {c.dock_title_bg};
            color: {c.dock_title_text};
            padding: 6px 12px;
            font-size: 9pt;
            font-weight: bold;
            text-align: left;
            border-bottom: 1px solid {c.dock_border};
        }}

        QDockWidget::close-button, QDockWidget::float-button {{
            background: transparent;
            border: none;
            padding: 2px;
        }}
        QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
            background-color: {c.bg_hover};
            border-radius: 2px;
        }}

        /* === BUTTONS === */
        QPushButton {{
            background-color: {c.button_bg};
            color: {c.button_text};
            border: 1px solid {c.border_color};
            border-radius: 4px;
            padding: 6px 14px;
            font-size: 9pt;
        }}
        QPushButton:hover {{
            background-color: {c.button_hover};
            border-color: {c.border_accent};
        }}
        QPushButton:pressed {{
            background-color: {c.button_active};
        }}
        QPushButton:disabled {{
            opacity: 0.4;
        }}

        QPushButton#playButton {{
            background-color: {c.button_play};
            color: {c.text_inverse};
            border: none;
            font-weight: bold;
        }}
        QPushButton#playButton:hover {{
            background-color: {c.button_play_hover};
        }}

        QPushButton#stopButton {{
            background-color: {c.button_stop};
            color: {c.text_inverse};
            border: none;
            font-weight: bold;
        }}
        QPushButton#stopButton:hover {{
            background-color: {c.button_stop_hover};
        }}

        QPushButton#recordButton {{
            background-color: {c.button_record};
            color: {c.text_inverse};
            border: none;
            font-weight: bold;
        }}
        QPushButton#recordButton:hover {{
            background-color: {c.button_record_active};
        }}

        /* === SLIDERS === */
        QSlider::groove:horizontal {{
            background: {c.slider_groove};
            height: 4px;
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: {c.slider_handle};
            width: 12px;
            margin: -4px 0;
            border-radius: 6px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {c.text_accent};
            width: 14px;
            margin: -5px 0;
        }}
        QSlider::sub-page:horizontal {{
            background: {c.slider_fill};
            border-radius: 2px;
        }}

        QSlider::groove:vertical {{
            background: {c.slider_groove};
            width: 4px;
            border-radius: 2px;
        }}
        QSlider::handle:vertical {{
            background: {c.slider_handle};
            height: 12px;
            margin: 0 -4px;
            border-radius: 6px;
        }}
        QSlider::handle:vertical:hover {{
            background: {c.text_accent};
            height: 14px;
            margin: 0 -5px;
        }}

        /* === MENUBAR === */
        QMenuBar {{
            background-color: {c.bg_secondary};
            color: {c.text_tertiary};
            border: none;
            padding: 2px;
        }}
        QMenuBar::item {{
            padding: 4px 12px;
            border-radius: 4px;
        }}
        QMenuBar::item:selected {{
            background-color: {c.menu_hover};
            color: {c.text_primary};
        }}

        QMenu {{
            background-color: {c.menu_bg};
            color: {c.menu_text};
            border: 1px solid {c.menu_border};
            border-radius: 6px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 24px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background-color: {c.menu_hover};
            color: {c.text_accent};
        }}
        QMenu::separator {{
            height: 1px;
            background: {c.menu_separator};
            margin: 4px 8px;
        }}

        /* === SCROLLBARS === */
        QScrollBar:vertical {{
            background: {c.scrollbar_bg};
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {c.scrollbar_handle};
            min-height: 30px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c.scrollbar_handle_hover};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        QScrollBar:horizontal {{
            background: {c.scrollbar_bg};
            height: 8px;
        }}
        QScrollBar::handle:horizontal {{
            background: {c.scrollbar_handle};
            min-width: 30px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {c.scrollbar_handle_hover};
        }}

        /* === COMBOBOX === */
        QComboBox {{
            background-color: {c.button_bg};
            color: {c.text_primary};
            border: 1px solid {c.border_color};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QComboBox:hover {{
            border-color: {c.border_accent};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {c.menu_bg};
            color: {c.menu_text};
            border: 1px solid {c.menu_border};
            border-radius: 4px;
            selection-background-color: {c.menu_hover};
            selection-color: {c.text_accent};
        }}

        /* === TOOLTIP === */
        QToolTip {{
            background-color: {c.tooltip_bg};
            color: {c.tooltip_text};
            border: 1px solid {c.tooltip_border};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 9pt;
        }}

        /* === LINEEDIT === */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {c.bg_tertiary};
            color: {c.text_primary};
            border: 1px solid {c.border_color};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border-color: {c.border_focus};
        }}

        /* === GROUPBOX === */
        QGroupBox {{
            background-color: {c.bg_surface};
            border: 1px solid {c.border_color};
            border-radius: 6px;
            margin-top: 10px;
            padding: 12px 8px 8px 8px;
        }}
        QGroupBox::title {{
            color: {c.text_accent};
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 6px;
            font-size: 8pt;
            font-weight: bold;
        }}

        /* === SPLITTER === */
        QSplitter::handle {{
            background-color: {c.border_color};
        }}
        QSplitter::handle:horizontal {{
            width: 1px;
        }}
        QSplitter::handle:vertical {{
            height: 1px;
        }}

        /* === TAB === */
        QTabWidget::pane {{
            background-color: {c.bg_primary};
            border: 1px solid {c.border_color};
            border-radius: 4px;
        }}
        QTabBar::tab {{
            background-color: {c.bg_tertiary};
            color: {c.text_tertiary};
            padding: 6px 16px;
            border: 1px solid {c.border_color};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        QTabBar::tab:selected {{
            background-color: {c.bg_primary};
            color: {c.text_accent};
            border-bottom: 2px solid {c.accent_primary};
        }}
        QTabBar::tab:hover {{
            color: {c.text_primary};
        }}
        """

        if custom_qss:
            base += f"\n\n{custom_qss}"

        return base
