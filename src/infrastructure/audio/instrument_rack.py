"""Instrument Rack - Gestor de instrumentos.

Sistema de rack de instrumentos similar a hardware,
con slots de instrumentos interchangeables.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class InstrumentType(Enum):
    """Tipos de instrumento."""
    SYNTH = "synth"
    SAMPLER = "sampler"
    DRUM_MACHINE = "drum_machine"
    EFFECT = "effect"


@dataclass
class InstrumentSlot:
    """Slot de instrumento.
    
    Attributes:
        index: Índice del slot
        name: Nombre
        instrument_type: Tipo de instrumento
        instrument: Instancia del instrumento
        enabled: Si está habilitado
        volume: Volumen del slot
    """
    index: int
    name: str = ""
    instrument_type: InstrumentType = InstrumentType.SYNTH
    instrument: Any = None
    enabled: bool = True
    volume: float = 1.0
    
    def is_active(self) -> bool:
        """Verificar si el slot está activo."""
        return self.enabled and self.instrument is not None


class InstrumentRack:
    """Rack de instrumentos.
    
    Gestiona hasta 16 instrumentos interchangeables,
    similar a un rack de hardware.
    """
    
    MAX_SLOTS = 16
    
    def __init__(self, num_slots: int = 8):
        """Inicializar rack.
        
        Args:
            num_slots: Número de slots (max 16)
        """
        self._num_slots = min(num_slots, self.MAX_SLOTS)
        self._slots: Dict[int, InstrumentSlot] = {}
        
        # Inicializar slots vacíos
        for i in range(self._num_slots):
            self._slots[i] = InstrumentSlot(index=i)
        
        # Slot seleccionado
        self._selected_slot = 0
        
        logger.info(f"InstrumentRack inicializado: {self._num_slots} slots")
    
    @property
    def selected_slot(self) -> int:
        """Obtener slot seleccionado."""
        return self._selected_slot
    
    @selected_slot.setter
    def selected_slot(self, value: int) -> None:
        """Establecer slot seleccionado."""
        if 0 <= value < self._num_slots:
            self._selected_slot = value
    
    @property
    def slot_count(self) -> int:
        """Obtener número de slots."""
        return self._num_slots
    
    def get_slot(self, index: int) -> Optional[InstrumentSlot]:
        """Obtener slot por índice.
        
        Args:
            index: Índice del slot
            
        Returns:
            Slot o None
        """
        return self._slots.get(index)
    
    def get_all_slots(self) -> List[InstrumentSlot]:
        """Obtener todos los slots."""
        return [self._slots[i] for i in range(self._num_slots)]
    
    def get_active_slots(self) -> List[InstrumentSlot]:
        """Obtener slots activos."""
        return [s for s in self._slots.values() if s.is_active()]
    
    def set_instrument(
        self,
        slot_index: int,
        instrument: Any,
        instrument_type: InstrumentType = InstrumentType.SYNTH,
        name: str = ""
    ) -> bool:
        """Establecer instrumento en un slot.
        
        Args:
            slot_index: Índice del slot
            instrument: Instancia del instrumento
            instrument_type: Tipo de instrumento
            name: Nombre del instrumento
            
        Returns:
            True si fue exitoso
        """
        if slot_index not in self._slots:
            logger.warning(f"Slot {slot_index} no existe")
            return False
        
        slot = self._slots[slot_index]
        slot.instrument = instrument
        slot.instrument_type = instrument_type
        slot.name = name or instrument_type.value
        
        logger.info(f"Instrumento establecido en slot {slot_index}: {slot.name}")
        return True
    
    def clear_slot(self, slot_index: int) -> bool:
        """Limpiar un slot.
        
        Args:
            slot_index: Índice del slot
            
        Returns:
            True si fue exitoso
        """
        if slot_index not in self._slots:
            return False
        
        slot = self._slots[slot_index]
        slot.instrument = None
        slot.name = ""
        
        logger.info(f"Slot {slot_index} limpiado")
        return True
    
    def enable_slot(self, slot_index: int, enabled: bool = True) -> bool:
        """Habilitar/deshabilitar un slot.
        
        Args:
            slot_index: Índice del slot
            enabled: Estado
            
        Returns:
            True si fue exitoso
        """
        if slot_index not in self._slots:
            return False
        
        self._slots[slot_index].enabled = enabled
        return True
    
    def set_slot_volume(
        self,
        slot_index: int,
        volume: float
    ) -> bool:
        """Establecer volumen de un slot.
        
        Args:
            slot_index: Índice del slot
            volume: Volumen (0.0 - 1.0)
            
        Returns:
            True si fue exitoso
        """
        if slot_index not in self._slots:
            return False
        
        self._slots[slot_index].volume = max(0.0, min(1.0, volume))
        return True
    
    def get_instrument(self, slot_index: int) -> Optional[Any]:
        """Obtener instrumento de un slot.
        
        Args:
            slot_index: Índice del slot
            
        Returns:
            Instrumento o None
        """
        slot = self._slots.get(slot_index)
        return slot.instrument if slot else None
    
    # === Procesamiento ===
    
    def process(
        self,
        note: int,
        velocity: int,
        num_samples: int
    ) -> Any:
        """Procesar nota en todos los instrumentos activos.
        
        Args:
            note: Nota MIDI
            velocity: Velocidad
            num_samples: Número de muestras
            
        Returns:
            Audio combinado
        """
        import numpy as np
        
        output = np.zeros(num_samples, dtype=np.float32)
        
        for slot in self.get_active_slots():
            if slot.instrument and hasattr(slot.instrument, 'process'):
                # Procesar nota
                slot.instrument.note_on(note, velocity)
                audio = slot.instrument.process(num_samples)
                
                # Aplicar volumen del slot
                audio *= slot.volume
                
                output += audio
        
        return output
    
    def all_notes_off(self) -> None:
        """Apagar todas las notas en todos los instrumentos."""
        for slot in self.get_active_slots():
            if slot.instrument and hasattr(slot.instrument, 'all_notes_off'):
                slot.instrument.all_notes_off()
    
    # === Serialización ===
    
    def to_dict(self) -> dict:
        """Serializar a diccionario."""
        return {
            "slot_count": self._num_slots,
            "selected_slot": self._selected_slot,
            "slots": [
                {
                    "index": s.index,
                    "name": s.name,
                    "instrument_type": s.instrument_type.value,
                    "enabled": s.enabled,
                    "volume": s.volume
                }
                for s in self._slots.values()
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "InstrumentRack":
        """Crear desde diccionario."""
        rack = cls(num_slots=data.get("slot_count", 8))
        rack._selected_slot = data.get("selected_slot", 0)
        
        for slot_data in data.get("slots", []):
            index = slot_data["index"]
            if index in rack._slots:
                slot = rack._slots[index]
                slot.name = slot_data.get("name", "")
                slot.enabled = slot_data.get("enabled", True)
                slot.volume = slot_data.get("volume", 1.0)
        
        return rack


class InstrumentFactory:
    """Fábrica de instrumentos.
    
    Crea instancias de instrumentos predefinidos.
    """
    
    @staticmethod
    def create_synth(
        synth_type: str = "square",
        sample_rate: int = 44100
    ) -> Any:
        """Crear sintetizador.
        
        Args:
            synth_type: Tipo de synth
            sample_rate: Sample rate
            
        Returns:
            Instancia de sintetizador
        """
        from .polyphonic_synth import PolyphonicSynth
        from .oscillator import Waveform
        
        synth = PolyphonicSynth(sample_rate=sample_rate)
        
        # Configurar según tipo
        if synth_type == "square":
            synth.waveform = Waveform.SQUARE
        elif synth_type == "saw":
            synth.waveform = Waveform.SAWTOOTH
        elif synth_type == "triangle":
            synth.waveform = Waveform.TRIANGLE
        elif synth_type == "sine":
            synth.waveform = Waveform.SINE
        
        logger.info(f"Synth creado: {synth_type}")
        return synth
    
    @staticmethod
    def create_drum_machine(
        sample_rate: int = 44100
    ) -> Any:
        """Crear drum machine real con síntesis.
        
        Args:
            sample_rate: Sample rate
            
        Returns:
            Instancia de DrumMachine
        """
        from .drum_machine import DrumMachine
        drum = DrumMachine(sample_rate=sample_rate)
        logger.info(f"DrumMachine creado: {sample_rate}Hz")
        return drum
    
    @staticmethod
    def create_sampler(
        sample_path: str = "",
        sample_rate: int = 44100
    ) -> Any:
        """Crear sampler real.
        
        Args:
            sample_path: Ruta del sample (opcional)
            sample_rate: Sample rate
            
        Returns:
            Instancia de Sampler
        """
        from .sampler_module import Sampler
        sampler = Sampler(sample_path=sample_path, sample_rate=sample_rate)
        logger.info(f"Sampler creado: {sample_path or '(empty)'}")
        return sampler
