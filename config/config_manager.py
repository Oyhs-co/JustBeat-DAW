"""Config Manager - TOML-based settings persistence.

Loads/saves application configuration to platform-appropriate locations:
  - Linux:   ~/.config/justbeat/config.toml
  - Windows: %APPDATA%/JustBeat/config.toml
  - macOS:   ~/Library/Application Support/JustBeat/config.toml
"""

import os
import logging
from pathlib import Path
from typing import Optional

from config.settings import Settings, AudioSettings, MIDISettings, ProjectSettings, UISettings, PluginSettings


try:
    import tomllib
except ImportError:
    tomllib = None  # Python <3.11

try:
    import tomli_w as tomli_writer
except ImportError:
    tomli_writer = None


logger = logging.getLogger(__name__)


def _get_config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "JustBeat"


def _get_config_path() -> Path:
    return _get_config_dir() / "config.toml"


def _settings_to_dict(settings: Settings) -> dict:
    return {
        "app": {
            "debug": settings.debug,
            "log_level": settings.log_level,
        },
        "audio": {
            "sample_rate": settings.audio.sample_rate,
            "buffer_size": settings.audio.buffer_size,
            "bit_depth": settings.audio.bit_depth,
            "output_channels": settings.audio.output_channels,
            "target_latency_ms": settings.audio.target_latency_ms,
            "output_device": settings.audio.output_device,
            "input_device": settings.audio.input_device,
            "verbose_audio": settings.audio.verbose_audio,
        },
        "midi": {
            "default_input_device": settings.midi.default_input_device,
            "default_output_device": settings.midi.default_output_device,
            "clock_sync_enabled": settings.midi.clock_sync_enabled,
            "quantize_value": settings.midi.quantize_value,
        },
        "project": {
            "default_bpm": settings.project.default_bpm,
            "default_time_signature": f"{settings.project.default_time_signature[0]}/{settings.project.default_time_signature[1]}",
            "default_pattern_length": settings.project.default_pattern_length,
            "max_tracks": settings.project.max_tracks,
            "auto_save_interval": settings.project.auto_save_interval,
            "projects_directory": str(settings.project.projects_directory),
        },
        "ui": {
            "theme": settings.ui.theme,
            "window_width": settings.ui.window_width,
            "window_height": settings.ui.window_height,
            "show_step_numbers": settings.ui.show_step_numbers,
        },
        "plugins": {
            "plugins_directory": str(settings.plugins.plugins_directory),
            "sandbox_enabled": settings.plugins.sandbox_enabled,
            "auto_load_builtin": settings.plugins.auto_load_builtin,
        },
    }


def _dict_to_settings(data: dict, settings: Settings) -> Settings:
    def _get(section, key, default=None):
        return data.get(section, {}).get(key, default)

    if audio := data.get("audio"):
        settings.audio.sample_rate = audio.get("sample_rate", settings.audio.sample_rate)
        settings.audio.buffer_size = audio.get("buffer_size", settings.audio.buffer_size)
        settings.audio.bit_depth = audio.get("bit_depth", settings.audio.bit_depth)
        settings.audio.output_channels = audio.get("output_channels", settings.audio.output_channels)
        settings.audio.target_latency_ms = audio.get("target_latency_ms", settings.audio.target_latency_ms)
        settings.audio.output_device = audio.get("output_device", settings.audio.output_device)
        settings.audio.input_device = audio.get("input_device", settings.audio.input_device)
        settings.audio.verbose_audio = audio.get("verbose_audio", settings.audio.verbose_audio)

    if midi := data.get("midi"):
        settings.midi.default_input_device = midi.get("default_input_device", settings.midi.default_input_device)
        settings.midi.default_output_device = midi.get("default_output_device", settings.midi.default_output_device)
        settings.midi.clock_sync_enabled = midi.get("clock_sync_enabled", settings.midi.clock_sync_enabled)
        settings.midi.quantize_value = midi.get("quantize_value", settings.midi.quantize_value)

    if project := data.get("project"):
        settings.project.default_bpm = project.get("default_bpm", settings.project.default_bpm)
        sig = project.get("default_time_signature", None)
        if sig and isinstance(sig, str) and "/" in sig:
            parts = sig.split("/")
            settings.project.default_time_signature = (int(parts[0]), int(parts[1]))
        settings.project.default_pattern_length = project.get("default_pattern_length", settings.project.default_pattern_length)
        settings.project.max_tracks = project.get("max_tracks", settings.project.max_tracks)
        settings.project.auto_save_interval = project.get("auto_save_interval", settings.project.auto_save_interval)
        dir_str = project.get("projects_directory", None)
        if dir_str:
            settings.project.projects_directory = Path(dir_str)

    if ui := data.get("ui"):
        settings.ui.theme = ui.get("theme", settings.ui.theme)
        settings.ui.window_width = ui.get("window_width", settings.ui.window_width)
        settings.ui.window_height = ui.get("window_height", settings.ui.window_height)
        settings.ui.show_step_numbers = ui.get("show_step_numbers", settings.ui.show_step_numbers)

    if plugins := data.get("plugins"):
        dir_str = plugins.get("plugins_directory", None)
        if dir_str:
            settings.plugins.plugins_directory = Path(dir_str)
        settings.plugins.sandbox_enabled = plugins.get("sandbox_enabled", settings.plugins.sandbox_enabled)
        settings.plugins.auto_load_builtin = plugins.get("auto_load_builtin", settings.plugins.auto_load_builtin)

    if app_section := data.get("app"):
        settings.debug = app_section.get("debug", settings.debug)
        settings.log_level = app_section.get("log_level", settings.log_level)

    return settings


def load_config() -> Settings:
    settings = Settings.load_from_env()

    config_path = _get_config_path()
    if not config_path.exists():
        logger.info(f"No config file found at {config_path}, using defaults + env")
        return settings

    try:
        with open(config_path, "rb") as f:
            if tomllib:
                data = tomllib.load(f)
            else:
                import tomli as _tomli
                data = _tomli.load(f)

        settings = _dict_to_settings(data, settings)
        logger.info(f"Loaded config from {config_path}")
    except Exception as e:
        logger.warning(f"Failed to load config from {config_path}: {e}")

    return settings


def save_config(settings: Settings) -> bool:
    config_dir = _get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = _get_config_path()

    data = _settings_to_dict(settings)

    try:
        if tomli_writer:
            import tomli_w
            with open(config_path, "wb") as f:
                tomli_w.dump(data, f)
        else:
            _write_toml_simple(config_path, data)
        logger.info(f"Saved config to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save config to {config_path}: {e}")
        return False


def _write_toml_simple(path: Path, data: dict, indent: int = 0) -> None:
    """Simple TOML writer fallback when tomli_w is not available."""
    with open(path, "w", encoding="utf-8") as f:
        for section, values in data.items():
            f.write(f"[{section}]\n")
            for key, value in values.items():
                if value is None:
                    f.write(f"{key} = \"\"\n")
                elif isinstance(value, bool):
                    f.write(f"{key} = {'true' if value else 'false'}\n")
                elif isinstance(value, int):
                    f.write(f"{key} = {value}\n")
                elif isinstance(value, float):
                    f.write(f"{key} = {value}\n")
                else:
                    f.write(f"{key} = \"{value}\"\n")
            f.write("\n")


# Patch get_settings to load from TOML on first access
_original_get_settings = None


def _patch_settings():
    global _original_get_settings
    from config.settings import get_settings as original_get_settings
    _original_get_settings = original_get_settings

    def _patched_get_settings():
        from config.settings import _settings
        if _settings is None:
            from config.settings import Settings
            _settings = load_config()
        return _settings

    import config.settings
    config.settings.get_settings = _patched_get_settings


# Auto-patch on import
_patch_settings()


import sys  # noqa: E402 (needed for _get_config_dir platform check)
