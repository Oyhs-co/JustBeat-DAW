"""Audio Engine Factory - Fábrica de motores de audio.

Crea diferentes tipos de engines de audio según la necesidad:
- RealtimeAudioEngine: Para reproducción en tiempo real
- OfflineAudioEngine: Para renderizado offline
- HybridAudioEngine: Combina ambos modos
"""

from typing import Optional
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class EngineType(Enum):
    """Tipos de motor de audio."""
    REALTIME = "realtime"
    OFFLINE = "offline"
    HYBRID = "hybrid"


class AudioEngineFactory:
    """Fábrica de motores de audio.
    
    Crea instancias de motores de audio según el tipo solicitado.
    """
    
    @staticmethod
    def create_engine(
        engine_type: EngineType,
        sample_rate: int = 44100,
        buffer_size: int = 512,
        **kwargs
    ):
        """Crear motor de audio.
        
        Args:
            engine_type: Tipo de motor
            sample_rate: Sample rate
            buffer_size: Tamaño de buffer
            **kwargs: Parámetros adicionales
            
        Returns:
            Instancia del motor
        """
        if engine_type == EngineType.REALTIME:
            return AudioEngineFactory._create_realtime_engine(
                sample_rate, buffer_size, **kwargs
            )
        elif engine_type == EngineType.OFFLINE:
            return AudioEngineFactory._create_offline_engine(
                sample_rate, **kwargs
            )
        elif engine_type == EngineType.HYBRID:
            return AudioEngineFactory._create_hybrid_engine(
                sample_rate, buffer_size, **kwargs
            )
        else:
            raise ValueError(f"Tipo de engine desconocido: {engine_type}")
    
    @staticmethod
    def _create_realtime_engine(
        sample_rate: int,
        buffer_size: int,
        **kwargs
    ):
        from .audio_manager import AudioManager

        logger.info(f"Creando RealtimeAudioEngine: {sample_rate}Hz, buffer={buffer_size}")

        return AudioManager(
            sample_rate=sample_rate,
            buffer_size=buffer_size
        )

    @staticmethod
    def _create_offline_engine(
        sample_rate: int,
        **kwargs
    ):
        from .audio_manager import AudioManager
        from .offline_renderer import OfflineRenderer

        logger.info(f"Creando OfflineAudioEngine: {sample_rate}Hz")

        audio_manager = AudioManager(
            sample_rate=sample_rate,
            buffer_size=8192
        )

        renderer = OfflineRenderer(
            audio_engine=audio_manager,
            sample_rate=sample_rate
        )

        return renderer

    @staticmethod
    def _create_hybrid_engine(
        sample_rate: int,
        buffer_size: int,
        **kwargs
    ):
        from .audio_manager import AudioManager

        logger.info(f"Creando HybridAudioEngine: {sample_rate}Hz")

        return AudioManager(
            sample_rate=sample_rate,
            buffer_size=buffer_size
        )


class AudioSystem:
    """Sistema de audio global.
    
    Gestiona el ciclo de vida del sistema de audio,
    incluyendo múltiples engines si es necesario.
    """
    
    def __init__(self):
        """Inicializar sistema."""
        self._current_engine = None
        self._engine_type = None
        self._sample_rate = 44100
        self._buffer_size = 512
        
        logger.info("AudioSystem inicializado")
    
    @property
    def sample_rate(self) -> int:
        """Obtener sample rate actual."""
        return self._sample_rate
    
    @property
    def buffer_size(self) -> int:
        """Obtener buffer size actual."""
        return self._buffer_size
    
    @property
    def engine(self):
        """Obtener engine actual."""
        return self._current_engine
    
    def initialize(
        self,
        engine_type: EngineType = EngineType.REALTIME,
        sample_rate: int = 44100,
        buffer_size: int = 512
    ) -> bool:
        """Inicializar el sistema de audio.
        
        Args:
            engine_type: Tipo de engine
            sample_rate: Sample rate
            buffer_size: Buffer size
            
        Returns:
            True si fue exitoso
        """
        try:
            self._sample_rate = sample_rate
            self._buffer_size = buffer_size
            self._engine_type = engine_type
            
            self._current_engine = AudioEngineFactory.create_engine(
                engine_type,
                sample_rate,
                buffer_size
            )
            
            logger.info(f"AudioSystem inicializado: {engine_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error inicializando AudioSystem: {e}")
            return False
    
    def switch_engine(
        self,
        engine_type: EngineType
    ) -> bool:
        """Cambiar tipo de engine.
        
        Args:
            engine_type: Nuevo tipo
            
        Returns:
            True si fue exitoso
        """
        if engine_type == self._engine_type:
            return True
        
        # Detener engine actual
        if self._current_engine:
            if hasattr(self._current_engine, 'stop'):
                self._current_engine.stop()
        
        # Crear nuevo engine
        return self.initialize(
            engine_type,
            self._sample_rate,
            self._buffer_size
        )
    
    def shutdown(self) -> None:
        """Apagar el sistema."""
        if self._current_engine:
            if hasattr(self._current_engine, 'stop'):
                self._current_engine.stop()
            if hasattr(self._current_engine, 'shutdown'):
                self._current_engine.shutdown()
        
        self._current_engine = None
        logger.info("AudioSystem apagado")


# Instancia global
_audio_system: Optional[AudioSystem] = None


def get_audio_system() -> AudioSystem:
    """Obtener instancia global del sistema de audio."""
    global _audio_system
    if _audio_system is None:
        _audio_system = AudioSystem()
    return _audio_system
