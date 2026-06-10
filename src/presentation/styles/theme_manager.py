"""Advanced Theme System - Multiple themes and theme management.

This module provides:
- Theme: Complete theme definition
- ThemeManager: Load/save/switch themes
- Predefined themes: Dark, Light, Cyber-Noir, etc.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ThemePreset(Enum):
    """Built-in theme presets."""
    DARK = "dark"
    LIGHT = "light"
    CYBER_NOIR = "cyber_noir"
    NEON = "neon"
    MINIMAL = "minimal"


@dataclass
class ThemeColors:
    """Complete color palette for a theme."""
    
    # Theme type
    is_dark: bool = True
    
    # Background colors
    bg_primary: str = "#1a1a1a"
    bg_secondary: str = "#222222"
    bg_tertiary: str = "#2a2a2a"
    bg_hover: str = "#333333"
    bg_active: str = "#444444"
    bg_panel: str = "#252525"
    
    # Text colors
    text_primary: str = "#ffffff"
    text_secondary: str = "#cccccc"
    text_tertiary: str = "#888888"
    text_accent: str = "#00aaff"
    text_inverse: str = "#000000"
    
    # Accent colors
    accent_primary: str = "#00aaff"
    accent_secondary: str = "#0088cc"
    accent_success: str = "#4CAF50"
    accent_warning: str = "#ff9800"
    accent_danger: str = "#f44336"
    accent_info: str = "#2196F3"
    
    # Button colors
    button_bg: str = "#333333"
    button_hover: str = "#444444"
    button_active: str = "#555555"
    button_play: str = "#4CAF50"
    button_stop: str = "#f44336"
    button_record: str = "#ff0000"
    button_text: str = "#ffffff"
    
    # Slider/Knob colors
    slider_groove: str = "#333333"
    slider_handle: str = "#00aaff"
    slider_fill: str = "#00aaff"
    
    # Grid colors (sequencer/piano roll)
    grid_line: str = "#333333"
    grid_line_bold: str = "#444444"
    grid_active: str = "#00ff00"
    grid_inactive: str = "#444444"
    grid_playhead: str = "#ffffff"
    
    # Note colors
    note_color: str = "#00ff88"
    note_color_selected: str = "#88ffaa"
    note_color_black: str = "#6688ff"
    note_color_playback: str = "#ffaa00"
    
    # Piano roll
    piano_white: str = "#fafafa"
    piano_black: str = "#333333"
    piano_white_black: str = "#dddddd"
    piano_black_black: str = "#222222"
    
    # Meter colors
    meter_green: str = "#00ff00"
    meter_yellow: str = "#ffcc00"
    meter_red: str = "#ff0000"
    meter_background: str = "#222222"
    
    # Mute/Solo colors
    mute_color: str = "#ff9800"
    solo_color: str = "#00aaff"
    
    # Track colors (for arrangement)
    track_colors: List[str] = field(default_factory=lambda: [
        "#ff6b6b", "#4ecdc4", "#45b7d1", "#f9ca24",
        "#6c5ce7", "#a29bfe", "#fd79a8", "#00b894",
        "#e17055", "#00cec9", "#0984e3", "#d63031"
    ])
    
    # Border colors
    border_color: str = "#444444"
    border_focus: str = "#00aaff"
    
    # Scrollbar colors
    scrollbar_bg: str = "#222222"
    scrollbar_handle: str = "#555555"
    
    # Menu colors
    menu_bg: str = "#2a2a2a"
    menu_hover: str = "#444444"
    menu_text: str = "#ffffff"
    
    # Tooltip
    tooltip_bg: str = "#333333"
    tooltip_text: str = "#ffffff"


@dataclass
class Theme:
    """Complete theme definition."""
    
    id: str = ""
    name: str = ""
    author: str = "JustBeat"
    description: str = ""
    colors: ThemeColors = field(default_factory=ThemeColors)
    is_dark: bool = True
    font_family: str = "Segoe UI"
    font_size: int = 10
    border_radius: int = 4
    
    def to_dict(self) -> dict:
        """Convert theme to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "author": self.author,
            "description": self.description,
            "colors": self.colors.__dict__,
            "is_dark": self.is_dark,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "border_radius": self.border_radius,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Theme":
        """Create theme from dictionary."""
        colors = ThemeColors(**data.get("colors", {}))
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            author=data.get("author", "JustBeat"),
            description=data.get("description", ""),
            colors=colors,
            is_dark=data.get("is_dark", True),
            font_family=data.get("font_family", "Segoe UI"),
            font_size=data.get("font_size", 10),
            border_radius=data.get("border_radius", 4),
        )


class ThemeManager:
    """Manager for loading, saving, and switching themes."""
    
    def __init__(self, themes_dir: Optional[Path] = None):
        """Initialize the theme manager.
        
        Args:
            themes_dir: Directory for storing themes
        """
        self._themes_dir = themes_dir
        self._themes: Dict[str, Theme] = {}
        self._current_theme: Optional[Theme] = None
        
        # Load built-in themes
        self._load_builtin_themes()
        
        if themes_dir:
            themes_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("ThemeManager initialized")
    
    def _load_builtin_themes(self) -> None:
        """Load built-in theme presets."""
        
        # Dark theme (default)
        self._themes[ThemePreset.DARK.value] = Theme(
            id=ThemePreset.DARK.value,
            name="Dark",
            description="Default dark theme",
            colors=ThemeColors(),
            is_dark=True,
        )
        
        # Light theme
        light_colors = ThemeColors(
            bg_primary="#f5f5f5",
            bg_secondary="#e0e0e0",
            bg_tertiary="#d0d0d0",
            bg_hover="#c0c0c0",
            bg_active="#b0b0b0",
            bg_panel="#ebebeb",
            text_primary="#1a1a1a",
            text_secondary="#444444",
            text_tertiary="#888888",
            text_accent="#0066cc",
            text_inverse="#ffffff",
            accent_primary="#0066cc",
            accent_secondary="#0055aa",
            button_bg="#d0d0d0",
            button_hover="#c0c0c0",
            button_active="#b0b0b0",
            slider_groove="#c0c0c0",
            slider_handle="#0066cc",
            grid_line="#d0d0d0",
            grid_line_bold="#b0b0b0",
            note_color="#00aa66",
            note_color_black="#4466cc",
            piano_white="#ffffff",
            piano_black="#333333",
            meter_green="#00cc00",
            meter_yellow="#cccc00",
            meter_red="#cc0000",
            scrollbar_bg="#d0d0d0",
            scrollbar_handle="#999999",
            menu_bg="#f0f0f0",
            menu_hover="#d0d0d0",
            menu_text="#1a1a1a",
            is_dark=False,
        )
        self._themes[ThemePreset.LIGHT.value] = Theme(
            id=ThemePreset.LIGHT.value,
            name="Light",
            description="Light theme for daytime use",
            colors=light_colors,
            is_dark=False,
        )
        
        # Cyber-Noir theme
        noir_colors = ThemeColors(
            bg_primary="#0a0a0f",
            bg_secondary="#12121a",
            bg_tertiary="#1a1a25",
            bg_hover="#222230",
            bg_active="#2a2a40",
            bg_panel="#0f0f18",
            text_primary="#e0e0ff",
            text_secondary="#a0a0c0",
            text_tertiary="#606080",
            text_accent="#ff00ff",
            accent_primary="#ff00ff",
            accent_secondary="#cc00cc",
            accent_success="#00ff88",
            accent_warning="#ff8800",
            accent_danger="#ff0044",
            button_bg="#1a1a25",
            button_hover="#2a2a40",
            button_active="#3a3a55",
            button_play="#00ff88",
            button_stop="#ff0044",
            button_record="#ff0000",
            slider_groove="#1a1a25",
            slider_handle="#ff00ff",
            slider_fill="#ff00ff",
            grid_line="#1a1a25",
            grid_line_bold="#2a2a40",
            grid_active="#ff00ff",
            grid_inactive="#2a2a40",
            grid_playhead="#ffffff",
            note_color="#ff00ff",
            note_color_selected="#ff66ff",
            note_color_black="#8800ff",
            note_color_playback="#00ff88",
            meter_green="#00ff88",
            meter_yellow="#ffaa00",
            meter_red="#ff0044",
            mute_color="#ff8800",
            solo_color="#ff00ff",
            border_color="#2a2a40",
            border_focus="#ff00ff",
            scrollbar_bg="#0a0a0f",
            scrollbar_handle="#ff00ff",
            menu_bg="#12121a",
            menu_hover="#2a2a40",
            menu_text="#e0e0ff",
            tooltip_bg="#1a1a25",
            tooltip_text="#e0e0ff",
        )
        self._themes[ThemePreset.CYBER_NOIR.value] = Theme(
            id=ThemePreset.CYBER_NOIR.value,
            name="Cyber-Noir",
            description="Futuristic neon theme",
            colors=noir_colors,
            is_dark=True,
        )
        
        # Set default
        self._current_theme = self._themes[ThemePreset.DARK.value]
    
    def get_theme(self, theme_id: str) -> Optional[Theme]:
        """Get a theme by ID."""
        return self._themes.get(theme_id)
    
    def get_all_themes(self) -> List[Theme]:
        """Get all available themes."""
        return list(self._themes.values())
    
    def set_current_theme(self, theme_id: str) -> bool:
        """Set the current theme.
        
        Args:
            theme_id: ID of theme to activate
            
        Returns:
            True if theme was found and set
        """
        theme = self._themes.get(theme_id)
        if theme:
            self._current_theme = theme
            logger.info(f"Theme set to: {theme.name}")
            return True
        return False
    
    def get_current_theme(self) -> Theme:
        """Get the current theme."""
        return self._current_theme
    
    def save_theme(self, theme: Theme, filepath: Optional[Path] = None) -> bool:
        """Save a custom theme.
        
        Args:
            theme: Theme to save
            filepath: Optional custom filepath
            
        Returns:
            True if successful
        """
        if filepath is None:
            if self._themes_dir is None:
                logger.error("No themes directory configured")
                return False
            filepath = self._themes_dir / f"{theme.id}.json"
        
        try:
            with open(filepath, "w") as f:
                json.dump(theme.to_dict(), f, indent=2)
            
            self._themes[theme.id] = theme
            logger.info(f"Saved theme to: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save theme: {e}")
            return False
    
    def load_theme(self, filepath: Path) -> Optional[Theme]:
        """Load a theme from file.
        
        Args:
            filepath: Path to theme file
            
        Returns:
            Loaded theme or None
        """
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            
            theme = Theme.from_dict(data)
            self._themes[theme.id] = theme
            
            logger.info(f"Loaded theme: {theme.name}")
            return theme
        except Exception as e:
            logger.error(f"Failed to load theme: {e}")
            return None
    
    def delete_theme(self, theme_id: str) -> bool:
        """Delete a custom theme.
        
        Args:
            theme_id: ID of theme to delete
            
        Returns:
            True if deleted
        """
        if theme_id in self._themes:
            del self._themes[theme_id]
            return True
        return False
    
    def export_to_qss(self, theme: Theme) -> str:
        """Export theme to Qt Style Sheets format.
        
        Args:
            theme: Theme to export
            
        Returns:
            QSS string
        """
        c = theme.colors
        
        return f"""
/* {theme.name} Theme - Generated by JustBeat-DAW */

QMainWindow, QWidget {{
    background-color: {c.bg_primary};
    color: {c.text_primary};
    font-family: {theme.font_family};
    font-size: {theme.font_size}pt;
}}

QGroupBox {{
    border: 1px solid {c.border_color};
    border-radius: {theme.border_radius}px;
    margin-top: 10px;
    padding-top: 10px;
}}

QGroupBox::title {{
    color: {c.text_accent};
}}

QPushButton {{
    background-color: {c.button_bg};
    color: {c.button_text};
    border: 1px solid {c.border_color};
    border-radius: {theme.border_radius}px;
    padding: 5px 15px;
}}

QPushButton:hover {{
    background-color: {c.button_hover};
}}

QPushButton:pressed {{
    background-color: {c.button_active};
}}

QPushButton#PlayButton {{
    background-color: {c.button_play};
}}

QPushButton#StopButton {{
    background-color: {c.button_stop};
}}

QPushButton#RecordButton {{
    background-color: {c.button_record};
}}

QSlider::groove:horizontal {{
    background: {c.slider_groove};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {c.slider_handle};
    width: 14px;
    margin: -4px 0;
    border-radius: 7px;
}}

QSlider::sub-page:horizontal {{
    background: {c.slider_fill};
    border-radius: 3px;
}}

QMenuBar {{
    background-color: {c.menu_bg};
    color: {c.menu_text};
}}

QMenuBar::item:selected {{
    background-color: {c.menu_hover};
}}

QMenu {{
    background-color: {c.menu_bg};
    color: {c.menu_text};
    border: 1px solid {c.border_color};
}}

QMenu::item:selected {{
    background-color: {c.menu_hover};
}}

QScrollBar:vertical {{
    background: {c.scrollbar_bg};
    width: 12px;
}}

QScrollBar::handle:vertical {{
    background: {c.scrollbar_handle};
    min-height: 20px;
    border-radius: 6px;
}}

QScrollBar:horizontal {{
    background: {c.scrollbar_bg};
    height: 12px;
}}

QScrollBar::handle:horizontal {{
    background: {c.scrollbar_handle};
    min-width: 20px;
    border-radius: 6px;
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {c.bg_secondary};
    color: {c.text_primary};
    border: 1px solid {c.border_color};
    border-radius: {theme.border_radius}px;
    padding: 4px;
}}

QLineEdit:focus, QTextEdit:focus {{
    border: 2px solid {c.border_focus};
}}

QComboBox {{
    background-color: {c.bg_secondary};
    color: {c.text_primary};
    border: 1px solid {c.border_color};
    border-radius: {theme.border_radius}px;
    padding: 4px;
}}

QComboBox::drop-down {{
    border: none;
}}

QToolTip {{
    background-color: {c.tooltip_bg};
    color: {c.tooltip_text};
    border: 1px solid {c.border_color};
}}

QDockWidget {{
    background-color: {c.bg_panel};
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(undock.png);
}}

QDockWidget::title {{
    background-color: {c.bg_secondary};
    padding: 4px;
}}
"""
