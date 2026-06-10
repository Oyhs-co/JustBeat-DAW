"""Plugin Manager - Gestor central de plugins.

Coordina plugins built-in (Python) y plugins VST externos.
Provee scanning, validación, categorización, y estado persistente.

Arquitectura:
    PluginManager
    ├── PluginHost        (plugins built-in Python)
    └── VSTHost           (plugins VST2/VST3 externos)
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import json
import logging

from src.infrastructure.plugins.host import PluginHost
from src.infrastructure.plugins.vst_host import (
    VSTHost, VSTPluginInfo, PluginCategory, VSTVersion
)


logger = logging.getLogger(__name__)


@dataclass
class PluginEntry:
    """Entrada de plugin en el catálogo."""
    name: str
    plugin_type: str  # "builtin", "vst2", "vst3"
    category: str  # "instrument", "effect", "utility", "synth"
    file_path: Optional[str] = None
    vendor: str = ""
    version: str = "1.0"
    is_loaded: bool = False
    is_favorite: bool = False
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)


class PluginManager:
    """Gestor central de plugins.

    Unifica plugins built-in y VST en un solo catálogo.
    Provee scanning, búsqueda, y gestión de estado.

    Uso:
        manager = PluginManager()
        manager.scan_all()
        for entry in manager.catalog:
            print(entry.name, entry.category)
        plugin = manager.load("MyPlugin")
    """

    def __init__(self, scan_at_start: bool = True):
        self._host = PluginHost()
        self._vst_host = VSTHost()
        self._catalog: Dict[str, PluginEntry] = {}
        self._favorites: List[str] = []
        self._blacklist: List[str] = []

        self._init_builtin_dirs()

        if scan_at_start:
            self.scan_all()

    def _init_builtin_dirs(self):
        builtin_dir = Path(__file__).parent / "builtin"
        if builtin_dir.exists():
            self._host.add_plugin_directory(builtin_dir)

    def scan_all(self) -> int:
        """Escanear todos los plugins (built-in + VST).

        Returns:
            Número total de plugins encontrados.
        """
        count = 0

        builtin_names = self._host.discover_plugins()
        for name in builtin_names:
            if name not in self._catalog and name not in self._blacklist:
                cls = self._host._plugin_classes.get(name)
                plugin_type = "instrument" if hasattr(cls, 'note_on') else "effect"
                self._catalog[name] = PluginEntry(
                    name=name,
                    plugin_type="builtin",
                    category=plugin_type,
                )
                count += 1

        vst_plugins = self._vst_host.scan_all()
        for info in vst_plugins:
            if info.name not in self._catalog and info.name not in self._blacklist:
                category_map = {
                    PluginCategory.SYNTH: "instrument",
                    PluginCategory.EFFECT: "effect",
                    PluginCategory.MULTI: "instrument",
                    PluginCategory.UNKNOWN: "effect",
                }
                vst_type = "vst2" if info.version == VSTVersion.VST2 else "vst3"
                self._catalog[info.name] = PluginEntry(
                    name=info.name,
                    plugin_type=vst_type,
                    category=category_map.get(info.category, "effect"),
                    file_path=str(info.file_path),
                    vendor=info.vendor,
                    version=f"{info.version.value}",
                )
                count += 1

        logger.info(f"PluginManager: {count} plugins en catálogo "
                    f"({len(builtin_names)} built-in, {len(vst_plugins)} VST)")
        return count

    def scan_directory(self, directory: Path) -> List[PluginEntry]:
        """Escanear un directorio específico en busca de plugins.

        Args:
            directory: Directorio a escanear.

        Returns:
            Lista de nuevos plugins encontrados.
        """
        found: List[PluginEntry] = []
        vst_infos = self._vst_host._scan_directory(directory, VSTVersion.VST2)
        vst_infos += self._vst_host._scan_directory(directory, VSTVersion.VST3)

        for info in vst_infos:
            if info.name not in self._catalog and info.name not in self._blacklist:
                vst_type = "vst2" if info.version == VSTVersion.VST2 else "vst3"
                entry = PluginEntry(
                    name=info.name,
                    plugin_type=vst_type,
                    category="effect",
                    file_path=str(info.file_path),
                )
                self._catalog[info.name] = entry
                found.append(entry)

        self._host.add_plugin_directory(directory)
        new_builtin = self._host.discover_plugins()
        for name in new_builtin:
            if name not in self._catalog and name not in self._blacklist:
                entry = PluginEntry(
                    name=name, plugin_type="builtin", category="instrument"
                )
                self._catalog[name] = entry
                found.append(entry)

        return found

    def load(self, name: str) -> Optional[object]:
        """Cargar un plugin por nombre.

        Args:
            name: Nombre del plugin.

        Returns:
            Instancia del plugin o None si falla.
        """
        entry = self._catalog.get(name)
        if entry is None:
            logger.warning(f"Plugin no encontrado: {name}")
            return None

        if entry.is_loaded:
            logger.debug(f"Plugin ya cargado: {name}")
            return None

        if entry.plugin_type == "builtin":
            success = self._host.load_plugin(name)
            if success:
                entry.is_loaded = True
                logger.info(f"Plugin built-in cargado: {name}")
            return self._host.get_plugin(name) if success else None

        elif entry.plugin_type in ("vst2", "vst3"):
            vst_info = self._vst_host.find_plugin(name)
            if vst_info:
                result = self._vst_host.load_plugin(vst_info)
                if result:
                    entry.is_loaded = True
                return result
        return None

    def unload(self, name: str) -> bool:
        """Descargar un plugin.

        Args:
            name: Nombre del plugin.

        Returns:
            True si se descargó correctamente.
        """
        entry = self._catalog.get(name)
        if not entry:
            return False

        if entry.plugin_type == "builtin":
            self._host.unload_plugin(name)

        self._vst_host.unload_plugin(name)
        entry.is_loaded = False
        return True

    def get_plugin(self, name: str) -> Optional[object]:
        """Obtener instancia de un plugin cargado.

        Args:
            name: Nombre del plugin.

        Returns:
            Instancia del plugin o None si no está cargado.
        """
        entry = self._catalog.get(name)
        if not entry:
            return None
        if entry.plugin_type == "builtin":
            return self._host.get_plugin(name)
        return self._vst_host._loaded_libraries.get(name)

    def get_plugins_by_type(self, category: str) -> List[PluginEntry]:
        """Obtener plugins por categoría.

        Args:
            category: "instrument", "effect", "utility", "synth".

        Returns:
            Lista de plugins.
        """
        return [
            e for e in self._catalog.values()
            if e.category == category
        ]

    def get_instruments(self) -> List[PluginEntry]:
        return self.get_plugins_by_type("instrument")

    def get_effects(self) -> List[PluginEntry]:
        return self.get_plugins_by_type("effect")

    def get_builtin(self) -> List[PluginEntry]:
        return [e for e in self._catalog.values() if e.plugin_type == "builtin"]

    def get_vst(self) -> List[PluginEntry]:
        return [e for e in self._catalog.values() if e.plugin_type in ("vst2", "vst3")]

    def toggle_favorite(self, name: str) -> bool:
        entry = self._catalog.get(name)
        if not entry:
            return False
        entry.is_favorite = not entry.is_favorite
        return True

    def add_to_blacklist(self, name: str):
        if name not in self._blacklist:
            self._blacklist.append(name)
        self._catalog.pop(name, None)

    @property
    def catalog(self) -> List[PluginEntry]:
        return list(self._catalog.values())

    @property
    def count(self) -> int:
        return len(self._catalog)

    @property
    def loaded_count(self) -> int:
        return sum(1 for e in self._catalog.values() if e.is_loaded)
