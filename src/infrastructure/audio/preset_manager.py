"""Preset Manager - Gestor de presets de instrumentos.

Sistema de gestión de presets para sintetizadores,
drum machines y efectos.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import json
import logging


logger = logging.getLogger(__name__)


@dataclass
class Preset:
    """Preset de instrumento.
    
    Attributes:
        id: Identificador único
        name: Nombre del preset
        category: Categoría
        instrument_type: Tipo de instrumento
        data: Datos del preset
        is_default: Si es un preset por defecto
    """
    id: str
    name: str
    category: str = ""
    instrument_type: str = ""
    data: Dict[str, Any] = None
    is_default: bool = False
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


class PresetManager:
    """Gestor de presets.
    
    Maneja la carga, guardado y organización de presets.
    """
    
    def __init__(self, preset_dir: Optional[Path] = None):
        """Inicializar gestor de presets.
        
        Args:
            preset_dir: Directorio de presets
        """
        self._preset_dir = preset_dir or Path("presets")
        self._presets: Dict[str, Preset] = {}
        self._categories: Dict[str, List[str]] = {}  # category -> [preset_ids]
        self._instrument_types: Dict[str, List[str]] = {}  # type -> [preset_ids]
        
        # Callbacks
        self._on_preset_loaded: Optional[Callable[[Preset], None]] = None
        self._on_preset_saved: Optional[Callable[[Preset], None]] = None
        
        logger.info(f"PresetManager inicializado: {self._preset_dir}")
    
    @property
    def preset_dir(self) -> Path:
        """Obtener directorio de presets."""
        return self._preset_dir
    
    # === Gestión de Presets ===
    
    def register_preset(self, preset: Preset) -> None:
        """Registrar un preset.
        
        Args:
            preset: Preset a registrar
        """
        self._presets[preset.id] = preset
        
        # Actualizar categorías
        if preset.category:
            if preset.category not in self._categories:
                self._categories[preset.category] = []
            self._categories[preset.category].append(preset.id)
        
        # Actualizar tipos
        if preset.instrument_type:
            if preset.instrument_type not in self._instrument_types:
                self._instrument_types[preset.instrument_type] = []
            self._instrument_types[preset.instrument_type].append(preset.id)
        
        logger.debug(f"Preset registrado: {preset.name}")
    
    def unregister_preset(self, preset_id: str) -> bool:
        """Desregistrar un preset.
        
        Args:
            preset_id: ID del preset
            
        Returns:
            True si se encontró y eliminó
        """
        if preset_id not in self._presets:
            return False
        
        preset = self._presets[preset_id]
        
        # Remover de categorías
        if preset.category in self._categories:
            if preset_id in self._categories[preset.category]:
                self._categories[preset.category].remove(preset_id)
        
        # Remover de tipos
        if preset.instrument_type in self._instrument_types:
            if preset_id in self._instrument_types[preset.instrument_type]:
                self._instrument_types[preset.instrument_type].remove(preset_id)
        
        del self._presets[preset_id]
        logger.debug(f"Preset desregistrado: {preset_id}")
        return True
    
    def get_preset(self, preset_id: str) -> Optional[Preset]:
        """Obtener un preset por ID.
        
        Args:
            preset_id: ID del preset
            
        Returns:
            Preset o None
        """
        return self._presets.get(preset_id)
    
    def get_all_presets(self) -> List[Preset]:
        """Obtener todos los presets."""
        return list(self._presets.values())
    
    def get_presets_by_category(self, category: str) -> List[Preset]:
        """Obtener presets por categoría.
        
        Args:
            category: Categoría
            
        Returns:
            Lista de presets
        """
        preset_ids = self._categories.get(category, [])
        return [self._presets[pid] for pid in preset_ids if pid in self._presets]
    
    def get_presets_by_type(self, instrument_type: str) -> List[Preset]:
        """Obtener presets por tipo de instrumento.
        
        Args:
            instrument_type: Tipo de instrumento
            
        Returns:
            Lista de presets
        """
        preset_ids = self._instrument_types.get(instrument_type, [])
        return [self._presets[pid] for pid in preset_ids if pid in self._presets]
    
    def get_categories(self) -> List[str]:
        """Obtener todas las categorías."""
        return list(self._categories.keys())
    
    def get_instrument_types(self) -> List[str]:
        """Obtener todos los tipos de instrumento."""
        return list(self._instrument_types.keys())
    
    # === Carga y Guardado ===
    
    def save_preset(self, preset: Preset, path: Optional[Path] = None) -> bool:
        """Guardar un preset a archivo.
        
        Args:
            preset: Preset a guardar
            path: Ruta (None usa el directorio de presets)
            
        Returns:
            True si fue exitoso
        """
        if path is None:
            filename = f"{preset.id}.json"
            path = self._preset_dir / preset.instrument_type / filename
        
        # Crear directorio si no existe
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(path, 'w') as f:
                json.dump({
                    "id": preset.id,
                    "name": preset.name,
                    "category": preset.category,
                    "instrument_type": preset.instrument_type,
                    "is_default": preset.is_default,
                    "data": preset.data
                }, f, indent=2)
            
            logger.info(f"Preset guardado: {path}")
            
            if self._on_preset_saved:
                self._on_preset_saved(preset)
            
            return True
            
        except Exception as e:
            logger.error(f"Error guardando preset: {e}")
            return False
    
    def load_preset(self, path: Path) -> Optional[Preset]:
        """Cargar un preset desde archivo.
        
        Args:
            path: Ruta del archivo
            
        Returns:
            Preset cargado o None
        """
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            preset = Preset(
                id=data["id"],
                name=data["name"],
                category=data.get("category", ""),
                instrument_type=data.get("instrument_type", ""),
                data=data.get("data", {}),
                is_default=data.get("is_default", False)
            )
            
            self.register_preset(preset)
            
            logger.info(f"Preset cargado: {preset.name}")
            
            if self._on_preset_loaded:
                self._on_preset_loaded(preset)
            
            return preset
            
        except Exception as e:
            logger.error(f"Error cargando preset {path}: {e}")
            return None
    
    def load_presets_from_dir(self, directory: Optional[Path] = None) -> int:
        """Cargar todos los presets de un directorio.
        
        Args:
            directory: Directorio (None usa el directorio de presets)
            
        Returns:
            Número de presets cargados
        """
        directory = directory or self._preset_dir
        count = 0
        
        if not directory.exists():
            logger.warning(f"Directorio de presets no existe: {directory}")
            return 0
        
        for file_path in directory.rglob("*.json"):
            if self.load_preset(file_path):
                count += 1
        
        logger.info(f"Presets cargados: {count}")
        return count
    
    # === Presets por Defecto ===
    
    def create_default_presets(self) -> None:
        """Crear presets por defecto para 8-bit."""
        
        # Square Synth presets
        self.register_preset(Preset(
            id="square_lead",
            name="Square Lead",
            category="Leads",
            instrument_type="synth",
            is_default=True,
            data={
                "waveform": "square",
                "attack": 0.01,
                "decay": 0.1,
                "sustain": 0.7,
                "release": 0.2,
                "volume": 0.8,
                "detune": 0
            }
        ))
        
        self.register_preset(Preset(
            id="square_bass",
            name="Square Bass",
            category="Basses",
            instrument_type="synth",
            is_default=True,
            data={
                "waveform": "square",
                "attack": 0.01,
                "decay": 0.3,
                "sustain": 0.5,
                "release": 0.1,
                "volume": 0.9,
                "detune": -10
            }
        ))
        
        # Saw Synth presets
        self.register_preset(Preset(
            id="saw_lead",
            name="Saw Lead",
            category="Leads",
            instrument_type="synth",
            is_default=True,
            data={
                "waveform": "sawtooth",
                "attack": 0.02,
                "decay": 0.2,
                "sustain": 0.6,
                "release": 0.3,
                "volume": 0.75,
                "detune": 5
            }
        ))
        
        # Triangle presets
        self.register_preset(Preset(
            id="triangle_bell",
            name="Triangle Bell",
            category="Keys",
            instrument_type="synth",
            is_default=True,
            data={
                "waveform": "triangle",
                "attack": 0.001,
                "decay": 0.5,
                "sustain": 0.0,
                "release": 0.8,
                "volume": 0.7,
                "detune": 0
            }
        ))
        
        # Pulse presets
        self.register_preset(Preset(
            id="pulse_organ",
            name="Pulse Organ",
            category="Organs",
            instrument_type="synth",
            is_default=True,
            data={
                "waveform": "pulse_25",
                "attack": 0.01,
                "decay": 0.1,
                "sustain": 0.8,
                "release": 0.1,
                "volume": 0.8,
                "detune": 0
            }
        ))
        
        logger.info("Presets por defecto creados")
    
    # === Callbacks ===
    
    def set_preset_loaded_callback(
        self,
        callback: Callable[[Preset], None]
    ) -> None:
        """Establecer callback cuando se carga un preset."""
        self._on_preset_loaded = callback
    
    def set_preset_saved_callback(
        self,
        callback: Callable[[Preset], None]
    ) -> None:
        """Establecer callback cuando se guarda un preset."""
        self._on_preset_saved = callback
    
    # === Serialización ===
    
    def to_dict(self) -> dict:
        """Serializar a diccionario."""
        return {
            "preset_dir": str(self._preset_dir),
            "presets": [
                {
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "instrument_type": p.instrument_type,
                    "is_default": p.is_default,
                    "data": p.data
                }
                for p in self._presets.values()
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PresetManager":
        """Crear desde diccionario."""
        manager = cls(preset_dir=Path(data.get("preset_dir", "presets")))
        
        for preset_data in data.get("presets", []):
            preset = Preset(
                id=preset_data["id"],
                name=preset_data["name"],
                category=preset_data.get("category", ""),
                instrument_type=preset_data.get("instrument_type", ""),
                data=preset_data.get("data", {}),
                is_default=preset_data.get("is_default", False)
            )
            manager.register_preset(preset)
        
        return manager


# Instancia global
_preset_manager: Optional[PresetManager] = None


def get_preset_manager() -> PresetManager:
    """Obtener instancia global del gestor de presets."""
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = PresetManager()
        _preset_manager.create_default_presets()
    return _preset_manager
