"""Platform utilities — cross-platform paths, audio backends, and system info."""

import os
import sys
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


# === Platform Detection ===

def is_windows() -> bool:
    return os.name == "nt"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_macos() -> bool:
    return sys.platform == "darwin"


def platform_name() -> str:
    if is_windows():
        return "windows"
    elif is_linux():
        return "linux"
    elif is_macos():
        return "macos"
    return sys.platform


# === Config/Data Directories ===

def config_dir() -> Path:
    if is_windows():
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif is_macos():
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "JustBeat"


def data_dir() -> Path:
    if is_windows():
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif is_macos():
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "JustBeat"


def cache_dir() -> Path:
    if is_windows():
        base = Path(os.environ.get("TEMP", Path.home() / "AppData" / "Local" / "Temp"))
    elif is_macos():
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "JustBeat"


def ensure_dirs() -> None:
    for d in [config_dir(), data_dir(), cache_dir()]:
        d.mkdir(parents=True, exist_ok=True)


# === Default Project Directory ===

def default_projects_dir() -> Path:
    if is_windows():
        return Path.home() / "Documents" / "JustBeat-DAW" / "Projects"
    elif is_macos():
        return Path.home() / "Music" / "JustBeat-DAW" / "Projects"
    else:
        xdg = os.environ.get("XDG_MUSIC_DIR", str(Path.home() / "Music"))
        return Path(xdg) / "JustBeat-DAW" / "Projects"


# === Audio Backend Info ===

def recommended_audio_backend() -> str:
    if is_windows():
        return "WASAPI"
    elif is_linux():
        return "ALSA"
    elif is_macos():
        return "CoreAudio"
    return "default"


def recommended_buffer_size() -> int:
    if is_windows():
        return 512
    elif is_linux():
        return 1024
    return 512


def high_performance_buffer_size() -> int:
    if is_windows():
        return 256
    elif is_linux():
        return 512
    return 256


# === MIDI Backend Info ===

def midi_backend() -> str:
    if is_windows():
        return "winmidi"
    elif is_linux():
        return "alsa"
    return "default"


# === System Resources ===

def get_cpu_count() -> int:
    try:
        import psutil
        return psutil.cpu_count(logical=True) or os.cpu_count() or 4
    except ImportError:
        return os.cpu_count() or 4


def get_available_memory_mb() -> int:
    try:
        import psutil
        return int(psutil.virtual_memory().available / (1024 * 1024))
    except ImportError:
        return 0
