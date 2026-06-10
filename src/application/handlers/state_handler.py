"""State Handler - Gestión de estado global y persistencia.

Maneja la persistencia del estado de la aplicación:
layout de docks, preferencias de audio, tema, ventana, etc.

El estado se guarda en ~/.justbeat/state.json
"""

from pathlib import Path
from typing import Any, Dict, Optional, List
import json
import logging


logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".justbeat"
STATE_FILE = CONFIG_DIR / "state.json"


DEFAULT_STATE: Dict[str, Any] = {
    "window": {
        "geometry": None,
        "maximized": False,
    },
    "audio": {
        "device": None,
        "sample_rate": 44100,
        "buffer_size": 512,
    },
    "theme": {
        "variant": "obsidian",
    },
    "project": {
        "last_path": None,
        "recent_files": [],
        "auto_save_interval": 300,
    },
    "docks": {},
}


class StateHandler:
    """Gestor de estado global con persistencia en JSON."""

    _instance: Optional["StateHandler"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._state: Dict[str, Any] = {}
        self._listeners: Dict[str, list] = {}
        self._load()

    def _load(self):
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self._state = data
            else:
                self._state = {}
        except Exception as e:
            logger.warning(f"Error cargando estado: {e}")
            self._state = {}

    def _save(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(
                json.dumps(self._state, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Error guardando estado: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._state
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any):
        keys = key.split(".")
        target = self._state
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self._save()
        self._notify(key, value)

    def get_all(self) -> Dict[str, Any]:
        return dict(self._state)

    def reset(self):
        self._state = {}
        self._save()

    def get_recent_files(self, max_items: int = 10) -> List[str]:
        recent = self.get("project.recent_files", [])
        return recent[:max_items]

    def add_recent_file(self, filepath: str):
        recent = self.get("project.recent_files", [])
        filepath = str(Path(filepath).resolve())
        if filepath in recent:
            recent.remove(filepath)
        recent.insert(0, filepath)
        self.set("project.recent_files", recent[:20])

    def remove_recent_file(self, filepath: str):
        recent = self.get("project.recent_files", [])
        filepath = str(Path(filepath).resolve())
        if filepath in recent:
            recent.remove(filepath)
            self.set("project.recent_files", recent)

    def listen(self, key: str, callback):
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(callback)

    def _notify(self, key: str, value: Any):
        for pattern, callbacks in self._listeners.items():
            if key.startswith(pattern):
                for cb in callbacks:
                    try:
                        cb(key, value)
                    except Exception as e:
                        logger.warning(f"Error en listener {key}: {e}")
