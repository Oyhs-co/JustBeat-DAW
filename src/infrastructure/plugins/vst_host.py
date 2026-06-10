"""VST Host - Carga y gestión de plugins VST2/VST3.

Busca VSTs en directorios estándar, valida DLLs,
y gestiona el ciclo de vida de plugins externos.

Arquitectura VST2:
    Un plugin VST2 es un DLL que exporta una función mágica
    llamada "VSTPluginMain" (o "main") que devuelve un AEffect*.
    Esta implementación usa ctypes para cargar y comunicarse
    con el DLL.

Nota:
    VST2.4 es el último protocolo abierto. VST3 requiere un
    esquema de interfaces COM más complejo. Esta implementación
    se enfoca en VST2 con placeholders para VST3.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import platform
import struct


logger = logging.getLogger(__name__)


class VSTVersion(Enum):
    VST2 = "vst2"
    VST3 = "vst3"
    UNKNOWN = "unknown"


class PluginCategory(Enum):
    UNKNOWN = 0
    EFFECT = 1
    SYNTH = 2
    MULTI = 4


@dataclass
class VSTPluginInfo:
    """Información de un plugin VST encontrado."""
    name: str
    file_path: Path
    version: VSTVersion
    vendor: str = ""
    category: PluginCategory = PluginCategory.UNKNOWN
    uid: int = 0
    is_valid: bool = False
    num_inputs: int = 2
    num_outputs: int = 2
    has_editor: bool = False
    parameters: List[Tuple[str, float]] = field(default_factory=list)


# Directorios estándar de VST por plataforma
VST2_STANDARD_DIRS: Dict[str, List[str]] = {
    "win32": [
        "C:\\Program Files\\Common Files\\VST2",
        "C:\\Program Files\\Common Files\\Steinberg\\VST2",
        "C:\\Program Files\\VSTPlugins",
        str(Path.home() / "Documents" / "VST2"),
    ],
    "darwin": [
        "/Library/Audio/Plug-Ins/VST",
        "~/Library/Audio/Plug-Ins/VST",
    ],
    "linux": [
        "/usr/lib/vst",
        "/usr/local/lib/vst",
        "~/.vst",
    ],
}

VST3_STANDARD_DIRS: Dict[str, List[str]] = {
    "win32": [
        "C:\\Program Files\\Common Files\\VST3",
        str(Path.home() / "Documents" / "VST3"),
    ],
    "darwin": [
        "/Library/Audio/Plug-Ins/VST3",
        "~/Library/Audio/Plug-Ins/VST3",
    ],
    "linux": [
        "/usr/lib/vst3",
        "/usr/local/lib/vst3",
        "~/.vst3",
    ],
}


def _get_platform() -> str:
    if platform.system() == "Windows":
        return "win32"
    elif platform.system() == "Darwin":
        return "darwin"
    return "linux"


class VSTHost:
    """Host para plugins VST2/VST3.

    Escanea directorios, valida DLLs, y gestiona
    el ciclo de vida de plugins externos.

    Uso:
        host = VSTHost()
        plugins = host.scan_all()
        info = host.validate_plugin(Path("path/to/plugin.dll"))
    """

    def __init__(self):
        self._scanned_plugins: Dict[str, VSTPluginInfo] = {}
        self._loaded_libraries: Dict[str, object] = {}

    def scan_all(self) -> List[VSTPluginInfo]:
        """Escanear todos los directorios VST estándar.

        Returns:
            Lista de plugins VST encontrados.
        """
        found: List[VSTPluginInfo] = []

        for d in self._get_standard_dirs(VSTVersion.VST2):
            found.extend(self._scan_directory(d, VSTVersion.VST2))

        for d in self._get_standard_dirs(VSTVersion.VST3):
            found.extend(self._scan_directory(d, VSTVersion.VST3))

        for info in found:
            if info.name not in self._scanned_plugins:
                self._scanned_plugins[info.name] = info

        logger.info(f"VST scan: {len(found)} plugins encontrados")
        return found

    def _get_standard_dirs(self, version: VSTVersion) -> List[Path]:
        dirs_map = VST2_STANDARD_DIRS if version == VSTVersion.VST2 else VST3_STANDARD_DIRS
        platform_key = _get_platform()
        paths = []
        for p in dirs_map.get(platform_key, []):
            path = Path(p).expanduser().resolve()
            if path.exists():
                paths.append(path)
        return paths

    def _scan_directory(self, directory: Path, version: VSTVersion) -> List[VSTPluginInfo]:
        ext = ".dll" if platform.system() == "Windows" else \
              ".vst3" if version == VSTVersion.VST3 else ".so" if platform.system() == "Linux" else ".vst"
        plugins = []
        if not directory.exists():
            return plugins

        for f in sorted(directory.iterdir()):
            if f.suffix.lower() == ext or (version == VSTVersion.VST3 and f.suffix == ".vst3"):
                info = self.validate_plugin(f)
                if info.is_valid:
                    plugins.append(info)
        return plugins

    def validate_plugin(self, file_path: Path) -> VSTPluginInfo:
        """Validar que un archivo sea un plugin VST válido.

        Para VST2: verifica que el DLL exporte la función
        mágica y tiene el tamaño mínimo de un AEffect.

        Args:
            file_path: Ruta al archivo del plugin.

        Returns:
            VSTPluginInfo con is_valid=True si es válido.
        """
        if not file_path.exists():
            return VSTPluginInfo(
                name=file_path.stem, file_path=file_path,
                version=VSTVersion.UNKNOWN, is_valid=False
            )

        ext = file_path.suffix.lower()
        if ext == ".vst3":
            return self._validate_vst3(file_path)
        elif ext == ".dll":
            return self._validate_vst2_dll(file_path)
        elif ext == ".so" or ext == ".vst":
            return self._validate_vst2_dll(file_path)
        else:
            return VSTPluginInfo(
                name=file_path.stem, file_path=file_path,
                version=VSTVersion.UNKNOWN, is_valid=False
            )

    def _validate_vst2_dll(self, file_path: Path) -> VSTPluginInfo:
        """Validar un DLL VST2.

        Verifica:
        1. El archivo tiene al menos 1KB (mínimo para un VST)
        2. Intenta detectar la función de entrada mágica.
           En VST2, se espera "VSTPluginMain" o "main"
           como export del DLL.

        Nota:
            La validación completa requiere cargar el DLL,
            lo cual puede ser riesgoso. Aquí hacemos una
            validación superficial.
        """
        info = VSTPluginInfo(
            name=file_path.stem, file_path=file_path,
            version=VSTVersion.VST2
        )

        try:
            size = file_path.stat().st_size
            if size < 1024:
                info.is_valid = False
                return info

            data = file_path.read_bytes()
            magic_vst = b"VstPluginMain" in data or b"VSTPluginMain" in data
            magic_effect = b"AEffect" in data
            is_dll = data[:2] == b"MZ"

            if _get_platform() != "win32":
                is_dll = True

            info.is_valid = magic_vst or magic_effect or (is_dll and size > 50000)
            info.uid = hash(str(file_path)) & 0xFFFFFFFF

            logger.debug(
                f"VST2 DLL: {file_path.name} "
                f"(VSTPluginMain={magic_vst}, AEffect={magic_effect}, "
                f"DLL={is_dll}, size={size})"
            )

        except Exception as e:
            logger.warning(f"Error validando {file_path}: {e}")
            info.is_valid = False

        return info

    def _validate_vst3(self, file_path: Path) -> VSTPluginInfo:
        """Validar un plugin VST3.

        Los VST3 son bundles con extensión .vst3 que contienen
        un DLL/so interno. La validación verifica que el bundle
        tenga la estructura esperada.
        """
        info = VSTPluginInfo(
            name=file_path.stem, file_path=file_path,
            version=VSTVersion.VST3
        )

        try:
            if file_path.is_dir():
                resource_dir = file_path / "Contents" / "Resources"
                if _get_platform() == "win32":
                    dll_path = file_path / "Contents" / "x86_64-win" / f"{file_path.stem}.vst3"
                elif _get_platform() == "darwin":
                    dll_path = file_path / "Contents" / "MacOS" / file_path.stem
                else:
                    dll_path = file_path / f"{file_path.stem}.so"

                info.is_valid = resource_dir.exists() or dll_path.exists()
            else:
                is_vst3_snapshot = b"VST3" in file_path.read_bytes()[:100]
                info.is_valid = is_vst3_snapshot

        except Exception as e:
            logger.warning(f"Error validando VST3 {file_path}: {e}")
            info.is_valid = False

        return info

    def load_plugin(self, info: VSTPluginInfo) -> Optional[object]:
        """Cargar un plugin VST en memoria.

        Para VST2 en Windows, usa ctypes para cargar el DLL.
        En otras plataformas, es un placeholder.

        Args:
            info: Información del plugin a cargar.

        Returns:
            Handle del módulo cargado o None si falla.
        """
        if info.name in self._loaded_libraries:
            return self._loaded_libraries[info.name]

        if not info.is_valid:
            logger.warning(f"No se puede cargar plugin inválido: {info.name}")
            return None

        if _get_platform() != "win32" or info.version == VSTVersion.VST3:
            logger.info(
                f"VST loading placeholder: {info.name} "
                f"(VST3/Cross-platform requiere implementación nativa)"
            )
            self._loaded_libraries[info.name] = object()
            return self._loaded_libraries[info.name]

        try:
            import ctypes
            lib = ctypes.CDLL(str(info.file_path))

            if hasattr(lib, "VSTPluginMain"):
                lib.VSTPluginMain.restype = ctypes.c_void_p
                effect_ptr = lib.VSTPluginMain(
                    ctypes.c_void_p(None),
                    ctypes.c_void_p(None),
                    ctypes.c_void_p(None)
                )
                logger.debug(f"AEffect* = {effect_ptr}")
            elif hasattr(lib, "main"):
                lib.main.restype = ctypes.c_void_p
                effect_ptr = lib.main(ctypes.c_void_p(None))
                logger.debug(f"AEffect* (main) = {effect_ptr}")
            else:
                logger.info(f"Plugin {info.name}: cargado pero sin función main detectable")

            self._loaded_libraries[info.name] = lib
            logger.info(f"Plugin VST cargado: {info.name}")
            return lib

        except Exception as e:
            logger.error(f"Error cargando VST {info.name}: {e}")
            return None

    def unload_plugin(self, name: str) -> bool:
        """Descargar un plugin de memoria.

        Args:
            name: Nombre del plugin.

        Returns:
            True si se descargó correctamente.
        """
        if name in self._loaded_libraries:
            del self._loaded_libraries[name]
            logger.info(f"Plugin descargado: {name}")
            return True
        return False

    def get_scanned_plugins(self) -> List[VSTPluginInfo]:
        """Obtener lista de plugins escaneados."""
        return list(self._scanned_plugins.values())

    def find_plugin(self, name: str) -> Optional[VSTPluginInfo]:
        """Buscar un plugin por nombre.

        Args:
            name: Nombre del plugin.

        Returns:
            VSTPluginInfo o None si no se encuentra.
        """
        return self._scanned_plugins.get(name)

    def get_loaded_count(self) -> int:
        return len(self._loaded_libraries)
