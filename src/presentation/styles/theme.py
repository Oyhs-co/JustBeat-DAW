"""Theme configuration - Colors and theme settings."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Colors:
    """Color palette for the application."""
    
    # Background colors
    bg_primary: str = "#1a1a1a"
    bg_secondary: str = "#222222"
    bg_tertiary: str = "#2a2a2a"
    bg_hover: str = "#333333"
    bg_active: str = "#444444"
    
    # Text colors
    text_primary: str = "#ffffff"
    text_secondary: str = "#cccccc"
    text_tertiary: str = "#888888"
    text_accent: str = "#00aaff"
    
    # Accent colors
    accent_primary: str = "#00aaff"
    accent_secondary: str = "#0088cc"
    accent_success: str = "#4CAF50"
    accent_warning: str = "#ff9800"
    accent_danger: str = "#f44336"
    
    # Button colors
    button_bg: str = "#333333"
    button_hover: str = "#444444"
    button_active: str = "#555555"
    button_play: str = "#4CAF50"
    button_stop: str = "#f44336"
    button_record: str = "#ff0000"
    
    # Slider colors
    slider_groove: str = "#333333"
    slider_handle: str = "#00aaff"
    
    # Grid colors
    grid_line: str = "#333333"
    grid_line_bold: str = "#444444"
    grid_active: str = "#00ff00"
    grid_inactive: str = "#444444"
    
    # Piano roll colors
    piano_white: str = "#fafafa"
    piano_black: str = "#333333"
    note_color: str = "#00ff88"
    note_color_black: str = "#6688ff"
    
    # Mixer colors
    meter_green: str = "#00ff00"
    meter_yellow: str = "#ffcc00"
    meter_red: str = "#ff0000"
    
    # Mute/Solo colors
    mute_color: str = "#ff0000"
    solo_color: str = "#ffff00"


@dataclass
class Fonts:
    """Font configuration."""
    
    family: str = "Segoe UI"
    size_small: int = 9
    size_normal: int = 11
    size_large: int = 14
    size_title: int = 16
    
    # Font weights
    weight_normal: str = "normal"
    weight_bold: str = "bold"


class Theme:
    """Theme manager for the application."""
    
    def __init__(self, name: str = "default"):
        """Initialize theme.
        
        Args:
            name: Theme name
        """
        self.name = name
        self.colors = Colors()
        self.fonts = Fonts()
    
    def to_dict(self) -> Dict:
        """Convert theme to dictionary."""
        return {
            "name": self.name,
            "colors": {
                "bg_primary": self.colors.bg_primary,
                "bg_secondary": self.colors.bg_secondary,
                "bg_tertiary": self.colors.bg_tertiary,
                "bg_hover": self.colors.bg_hover,
                "bg_active": self.colors.bg_active,
                "text_primary": self.colors.text_primary,
                "text_secondary": self.colors.text_secondary,
                "text_tertiary": self.colors.text_tertiary,
                "text_accent": self.colors.text_accent,
                "accent_primary": self.colors.accent_primary,
                "accent_success": self.colors.accent_success,
                "accent_warning": self.colors.accent_warning,
                "accent_danger": self.colors.accent_danger,
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Theme":
        """Create theme from dictionary."""
        theme = cls(data.get("name", "custom"))
        
        if "colors" in data:
            colors = data["colors"]
            for key, value in colors.items():
                if hasattr(theme.colors, key):
                    setattr(theme.colors, key, value)
        
        return theme


# Pre-defined themes
THEMES = {
    "default": Theme("default"),
    "dark": Theme("dark"),
    "light": Theme("light"),
}


def get_theme(name: str = "default") -> Theme:
    """Get a theme by name.
    
    Args:
        name: Theme name
        
    Returns:
        Theme instance
    """
    return THEMES.get(name, Theme("default"))
