"""Hardware Emulation - Emulación de hardware 8-bit.

Sistema de emulación de chips de sonido clásico para
autenticidad en la producción chiptune.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np
import logging


logger = logging.getLogger(__name__)


class ChipType(Enum):
    """Tipos de chip emulado."""
    NES = "nes"           # 2A03
    GAMEBOY = "gameboy"   # APU
    C64 = "c64"           # SID
    AY38910 = "ay38910"   # MSX, Atari ST
    SN76489 = "sn76489"   # Sega Master/Game Gear
    POKEY = "pokey"       # Atari 800
    OPFM = "opfm"         # Yamaha OPM/FM


@dataclass
class ChipConfig:
    """Configuración del chip.
    
    Attributes:
        chip_type: Tipo de chip
        channels: Número de canales
        sample_rate: Sample rate
        pulse_widths: Anchos de pulso disponibles
        has_noise: Si tiene canal de ruido
        has_volume_table: Tabla de volúmenes
    """
    chip_type: ChipType
    channels: int
    sample_rate: int
    pulse_widths: List[float]
    has_noise: bool
    has_volume_table: bool


class HardwareEmulator:
    """Emulador de hardware 8-bit.
    
    Emula las características específicas de chips de sonido
    para lograr autenticidad en la producción chiptune.
    """
    
    # Configuraciones de chips
    CHIP_CONFIGS = {
        ChipType.NES: ChipConfig(
            chip_type=ChipType.NES,
            channels=2,
            sample_rate=1789773,  # NTSC
            pulse_widths=[0.125, 0.25, 0.5, 0.75],
            has_noise=True,
            has_volume_table=True
        ),
        ChipType.GAMEBOY: ChipConfig(
            chip_type=ChipType.GAMEBOY,
            channels=4,
            sample_rate=1048576,
            pulse_widths=[0.5],  # Solo duty 50%
            has_noise=True,
            has_volume_table=True
        ),
        ChipType.C64: ChipConfig(
            chip_type=ChipType.C64,
            channels=3,
            sample_rate=985248,  # PAL
            pulse_widths=[0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875],
            has_noise=True,
            has_volume_table=True
        ),
        ChipType.AY38910: ChipConfig(
            chip_type=ChipType.AY38910,
            channels=3,
            sample_rate=1789773,
            pulse_widths=[0.5],  # Fixed duty
            has_noise=True,
            has_volume_table=True
        ),
        ChipType.SN76489: ChipConfig(
            chip_type=ChipType.SN76489,
            channels=4,
            sample_rate=3579545,
            pulse_widths=[0.5],
            has_noise=True,
            has_volume_table=True
        ),
    }
    
    def __init__(
        self,
        chip_type: ChipType = ChipType.NES,
        sample_rate: int = 44100
    ):
        """Inicializar emulador.
        
        Args:
            chip_type: Tipo de chip a emular
            sample_rate: Sample rate de salida
        """
        self._chip_type = chip_type
        self._sample_rate = sample_rate
        self._config = self.CHIP_CONFIGS[chip_type]
        
        # Estado de canales
        self._channel_frequencies: Dict[int, float] = {}
        self._channel_volumes: Dict[int, float] = {}
        self._channel_duty: Dict[int, float] = {}
        
        # Ruido
        self._noise_enabled = False
        self._noise_value = 0
        self._noise_shift = 0
        
        # Fase del chip
        self._chip_phase = 0.0
        self._chip_clock = self._config.sample_rate
        
        logger.info(f"HardwareEmulator inicializado: {chip_type.value}")
    
    @property
    def chip_type(self) -> ChipType:
        """Obtener tipo de chip."""
        return self._chip_type
    
    @property
    def config(self) -> ChipConfig:
        """Obtener configuración."""
        return self._config
    
    # === Configuración de Canales ===
    
    def set_channel_frequency(
        self,
        channel: int,
        frequency: float
    ) -> None:
        """Establecer frecuencia de un canal.
        
        Args:
            channel: Índice del canal
            frequency: Frecuencia en Hz
        """
        self._channel_frequencies[channel] = frequency
    
    def set_channel_volume(
        self,
        channel: int,
        volume: float
    ) -> None:
        """Establecer volumen de un canal.
        
        Args:
            channel: Índice del canal
            volume: Volumen (0.0 - 1.0)
        """
        self._channel_volumes[channel] = max(0.0, min(1.0, volume))
    
    def set_channel_duty(
        self,
        channel: int,
        duty: float
    ) -> None:
        """Establecer ciclo de trabajo (duty cycle).
        
        Args:
            channel: Índice del canal
            duty: Ciclo de trabajo (0.0 - 1.0)
        """
        # Ajustar a los anchos disponibles
        available = self._config.pulse_widths
        closest = min(available, key=lambda x: abs(x - duty))
        self._channel_duty[channel] = closest
    
    def enable_noise(self, enabled: bool = True) -> None:
        """Habilitar/deshabilitar canal de ruido.
        
        Args:
            enabled: Estado
        """
        self._noise_enabled = enabled
    
    def set_noise_frequency(self, frequency: float) -> None:
        """Establecer frecuencia del ruido.
        
        Args:
            frequency: Frecuencia
        """
        # En chips reales, esto controla la tasa de cambio
        self._noise_shift = int(frequency)
    
    # === Procesamiento ===
    
    def process(self, num_samples: int) -> np.ndarray:
        """Procesar muestras de audio.
        
        Args:
            num_samples: Número de muestras
            
        Returns:
            Audio estéreo
        """
        output = np.zeros(num_samples, dtype=np.float32)
        
        # Procesar cada canal
        for channel in range(self._config.channels):
            freq = self._channel_frequencies.get(channel, 0)
            volume = self._channel_volumes.get(channel, 0)
            duty = self._channel_duty.get(channel, 0.5)
            
            if freq > 0 and volume > 0:
                # Generar pulso
                channel_output = self._generate_pulse(
                    num_samples,
                    freq,
                    duty
                )
                
                # Aplicar volumen
                channel_output *= volume * 0.3  # Escalar para evitar clipping
                
                output += channel_output
        
        # Procesar ruido si está habilitado
        if self._noise_enabled:
            noise_output = self._generate_noise(num_samples)
            output += noise_output * 0.3
        
        # Normalizar
        max_channels = self._config.channels + (1 if self._noise_enabled else 0)
        if max_channels > 0:
            output /= np.sqrt(max_channels)
        
        return output
    
    def _generate_pulse(
        self,
        num_samples: int,
        frequency: float,
        duty: float
    ) -> np.ndarray:
        """Generar forma de onda de pulso.
        
        Args:
            num_samples: Número de muestras
            frequency: Frecuencia
            duty: Ciclo de trabajo
            
        Returns:
            Forma de onda
        """
        # Phase increment por muestra
        phase_inc = frequency / self._sample_rate
        
        # Generar fase acumulativa
        phases = np.cumsum(np.full(num_samples, phase_inc))
        phases = phases % 1.0
        
        # Generar pulso
        output = np.where(phases < duty, 1.0, -1.0)
        
        return output
    
    def _generate_noise(self, num_samples: int) -> np.ndarray:
        """Generar ruido.
        
        Args:
            num_samples: Número de muestras
            
        Returns:
            Ruido
        """
        # Generar ruido simple
        output = np.random.choice([-1.0, 1.0], size=num_samples)
        
        # Aplicar фильtro simple (simulando registro de desplazamiento)
        if self._noise_shift > 0:
            # Downsampling simple para simular shift register
            step = max(1, self._noise_shift)
            output[::step] = 0
        
        return output
    
    # === Utilidades ===
    
    def note_to_frequency(self, note: int) -> float:
        """Convertir nota MIDI a frecuencia.
        
        Args:
            note: Nota MIDI
            
        Returns:
            Frecuencia en Hz
        """
        return 440.0 * (2.0 ** ((note - 69) / 12.0))
    
    def frequency_to_period(self, frequency: float) -> int:
        """Convertir frecuencia a período del chip.
        
        Args:
            frequency: Frecuencia
            
        Returns:
            Período en ciclos del chip
        """
        return int(self._chip_clock / frequency)
    
    def reset(self) -> None:
        """Resetear el emulador."""
        self._channel_frequencies.clear()
        self._channel_volumes.clear()
        self._channel_duty.clear()
        self._noise_enabled = False
        self._chip_phase = 0.0
        
        logger.debug("HardwareEmulator reseteado")
    
    # === Serialización ===
    
    def to_dict(self) -> dict:
        """Serializar a diccionario."""
        return {
            "chip_type": self._chip_type.value,
            "sample_rate": self._sample_rate,
            "channel_frequencies": self._channel_frequencies,
            "channel_volumes": self._channel_volumes,
            "channel_duty": self._channel_duty,
            "noise_enabled": self._noise_enabled,
            "noise_shift": self._noise_shift
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "HardwareEmulator":
        """Crear desde diccionario."""
        chip_type = ChipType(data.get("chip_type", "nes"))
        sample_rate = data.get("sample_rate", 44100)
        
        emulator = cls(chip_type=chip_type, sample_rate=sample_rate)
        
        emulator._channel_frequencies = data.get("channel_frequencies", {})
        emulator._channel_volumes = data.get("channel_volumes", {})
        emulator._channel_duty = data.get("channel_duty", {})
        emulator._noise_enabled = data.get("noise_enabled", False)
        emulator._noise_shift = data.get("noise_shift", 0)
        
        return emulator


class HardwareEmulationMode:
    """Modo de emulación de hardware.
    
    Gestiona múltiples chips y permite switching entre ellos.
    """
    
    def __init__(self, sample_rate: int = 44100):
        """Inicializar modo de emulación.
        
        Args:
            sample_rate: Sample rate
        """
        self._sample_rate = sample_rate
        self._emulators: Dict[ChipType, HardwareEmulator] = {}
        self._active_chip: Optional[ChipType] = None
        
        #mezcla de chips
        self._chip_mix: Dict[ChipType, float] = {}
        
        logger.info(f"HardwareEmulationMode inicializado: {sample_rate}Hz")
    
    def add_chip(self, chip_type: ChipType) -> HardwareEmulator:
        """Añadir un chip emulado.
        
        Args:
            chip_type: Tipo de chip
            
        Returns:
            Emulador creado
        """
        if chip_type in self._emulators:
            return self._emulators[chip_type]
        
        emulator = HardwareEmulator(
            chip_type=chip_type,
            sample_rate=self._sample_rate
        )
        
        self._emulators[chip_type] = emulator
        self._chip_mix[chip_type] = 1.0
        
        # Activar si es el primero
        if self._active_chip is None:
            self._active_chip = chip_type
        
        logger.info(f"Chip añadido: {chip_type.value}")
        return emulator
    
    def remove_chip(self, chip_type: ChipType) -> bool:
        """Quitar un chip.
        
        Args:
            chip_type: Tipo de chip
            
        Returns:
            True si se removió
        """
        if chip_type in self._emulators:
            del self._emulators[chip_type]
            del self._chip_mix[chip_type]
            
            # Cambiar chip activo si era el actual
            if self._active_chip == chip_type:
                self._active_chip = next(
                    iter(self._emulators.keys()), 
                    None
                )
            
            return True
        return False
    
    def set_active_chip(self, chip_type: ChipType) -> bool:
        """Establecer chip activo.
        
        Args:
            chip_type: Tipo de chip
            
        Returns:
            True si fue exitoso
        """
        if chip_type in self._emulators:
            self._active_chip = chip_type
            return True
        return False
    
    def get_active_chip(self) -> Optional[HardwareEmulator]:
        """Obtener chip activo."""
        if self._active_chip:
            return self._emulators.get(self._active_chip)
        return None
    
    def set_chip_mix(
        self,
        chip_type: ChipType,
        mix: float
    ) -> bool:
        """Establecer nivel de mezcla de un chip.
        
        Args:
            chip_type: Tipo de chip
            mix: Nivel de mezcla (0.0 - 1.0)
            
        Returns:
            True si fue exitoso
        """
        if chip_type in self._chip_mix:
            self._chip_mix[chip_type] = max(0.0, min(1.0, mix))
            return True
        return False
    
    def process(self, num_samples: int) -> np.ndarray:
        """Procesar audio de todos los chips.
        
        Args:
            num_samples: Número de muestras
            
        Returns:
            Audio combinado
        """
        output = np.zeros(num_samples, dtype=np.float32)
        
        for chip_type, emulator in self._emulators.items():
            mix = self.get(chip_type._chip_mix, 1.0)
            
            if mix > 0:
                chip_output = emulator.process(num_samples)
                output += chip_output * mix
        
        # Normalizar
        active_count = sum(1 for m in self._chip_mix.values() if m > 0)
        if active_count > 0:
            output /= np.sqrt(active_count)
        
        return output
    
    def note_on(
        self,
        channel: int,
        note: int,
        velocity: int
    ) -> None:
        """Iniciar nota en chip activo.
        
        Args:
            channel: Canal
            note: Nota
            velocity: Velocidad
        """
        emulator = self.get_active_chip()
        if emulator:
            freq = emulator.note_to_frequency(note)
            volume = velocity / 127.0
            emulator.set_channel_frequency(channel, freq)
            emulator.set_channel_volume(channel, volume)
    
    def note_off(self, channel: int) -> None:
        """Liberar nota.
        
        Args:
            channel: Canal
        """
        emulator = self.get_active_chip()
        if emulator:
            emulator.set_channel_volume(channel, 0)
    
    def all_notes_off(self) -> None:
        """Apagar todas las notas."""
        for emulator in self._emulators.values():
            emulator.reset()
    
    def get_available_chips(self) -> List[ChipType]:
        """Obtener chips disponibles."""
        return list(self._emulators.keys())
