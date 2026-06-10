"""Application settings and configuration for JustBeat-DAW.

This module contains all configuration settings for the application,
including audio settings, MIDI configuration, and UI preferences.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os


@dataclass
class AudioSettings:
    """Audio engine configuration settings."""
    
    # Sample rate in Hz
    sample_rate: int = 44100
    
    # Buffer size (samples) - 1024 reduce underruns en sistemas con alta latencia
    buffer_size: int = 1024
    
    # Bit depth
    bit_depth: int = 16
    
    # Output channels
    output_channels: int = 2
    
    # Latency target in milliseconds
    target_latency_ms: float = 20.0
    
    # Output device (None = auto-detect, -1 = first available)
    output_device: Optional[int] = -1
    
    # Input device (None = auto-detect)
    input_device: Optional[int] = None
    
    # Verbose audio logging (process_buffer, callback timing, etc.)
    # Habilitar con env: JUSTBEAT_VERBOSE_AUDIO=1
    verbose_audio: bool = False


@dataclass
class MIDISettings:
    """MIDI configuration settings."""
    
    # Default MIDI input device (None = first available)
    default_input_device: Optional[str] = None
    
    # Default MIDI output device (None = first available)
    default_output_device: Optional[str] = None
    
    # Enable MIDI clock sync by default
    clock_sync_enabled: bool = False
    
    # Default quantize value (1/4, 1/8, 1/16, etc.)
    quantize_value: int = 16


@dataclass
class ProjectSettings:
    """Project default settings."""
    
    # Default BPM
    default_bpm: int = 120
    
    # Default time signature (numerator, denominator)
    default_time_signature: tuple[int, int] = (4, 4)
    
    # Default pattern length (steps)
    default_pattern_length: int = 16
    
    # Maximum number of tracks
    max_tracks: int = 16
    
    # Project file extension
    file_extension: str = ".jbproj"
    
    # Auto-save interval in seconds
    auto_save_interval: int = 300
    
    # Projects directory
    projects_directory: Path = field(default_factory=lambda: Path.home() / "Documents" / "JustBeat-DAW" / "Projects")


@dataclass
class UISettings:
    """User interface configuration settings."""
    
    # Theme ("dark" or "light")
    theme: str = "dark"
    
    # Window size
    window_width: int = 1280
    window_height: int = 720
    
    # Show step numbers
    show_step_numbers: bool = True
    
    # Grid color scheme
    grid_color_active: str = "#00AA00"
    grid_color_inactive: str = "#333333"
    grid_color_beat: str = "#006600"


@dataclass
class PluginSettings:
    """Plugin system configuration."""
    
    # Plugins directory
    plugins_directory: Path = field(default_factory=lambda: Path.home() / "Documents" / "JustBeat-DAW" / "Plugins")
    
    # Enable plugin sandboxing
    sandbox_enabled: bool = False
    
    # Auto-load built-in plugins
    auto_load_builtin: bool = True


@dataclass
class Settings:
    """Main application settings container."""
    
    # Application info
    app_name: str = "JustBeat-DAW"
    app_version: str = "0.1.0"
    
    # Subsystem settings
    audio: AudioSettings = field(default_factory=AudioSettings)
    midi: MIDISettings = field(default_factory=MIDISettings)
    project: ProjectSettings = field(default_factory=ProjectSettings)
    ui: UISettings = field(default_factory=UISettings)
    plugins: PluginSettings = field(default_factory=PluginSettings)
    
    # Debug mode
    debug: bool = False
    
    # Log level
    log_level: str = "INFO"
    
    def __post_init__(self):
        """Ensure directories exist after initialization."""
        self.project.projects_directory.mkdir(parents=True, exist_ok=True)
        self.plugins.plugins_directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load_from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        settings = cls()
        
        # Override with environment variables if present
        if audio_rate := os.getenv("JUSTBEAT_SAMPLE_RATE"):
            settings.audio.sample_rate = int(audio_rate)
        
        if buffer_size := os.getenv("JUSTBEAT_BUFFER_SIZE"):
            settings.audio.buffer_size = int(buffer_size)
        
        if bpm := os.getenv("JUSTBEAT_DEFAULT_BPM"):
            settings.project.default_bpm = int(bpm)
        
        if debug := os.getenv("JUSTBEAT_DEBUG"):
            settings.debug = debug.lower() in ("true", "1", "yes")
        
        if verbose := os.getenv("JUSTBEAT_VERBOSE_AUDIO"):
            settings.audio.verbose_audio = verbose.lower() in ("true", "1", "yes")
        
        return settings
    
    @classmethod
    def get_default(cls) -> "Settings":
        """Get default settings instance."""
        return cls()


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings.load_from_env()
    return _settings


def reset_settings() -> Settings:
    """Reset settings to defaults."""
    global _settings
    _settings = Settings()
    return _settings
