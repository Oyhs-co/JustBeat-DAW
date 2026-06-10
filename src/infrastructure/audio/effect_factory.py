"""Effect Factory - Factory para crear efectos desde strings.

Convierte nombres de efectos en instancias de efectos reales.
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class EffectFactory:
    """Factory para crear efectos de audio."""
    
    # Mapeo de nombres a clases de efectos
    _EFFECT_CLASSES = {}
    
    @classmethod
    def register(cls, name: str, effect_class: type) -> None:
        """Registrar una clase de efecto.
        
        Args:
            name: Nombre del efecto
            effect_class: Clase del efecto
        """
        cls._EFFECT_CLASSES[name.lower()] = effect_class
    
    @classmethod
    def create(cls, effect_name: str, **kwargs) -> Optional[Any]:
        """Crear una instancia de efecto.
        
        Args:
            effect_name: Nombre del efecto
            **kwargs: Argumentos para el constructor
            
        Returns:
            Instancia del efecto o None si no existe
        """
        effect_name = effect_name.lower()
        
        if effect_name == "none" or effect_name == "":
            return None
        
        if effect_name not in cls._EFFECT_CLASSES:
            logger.warning(f"Efecto desconocido: {effect_name}")
            return None
        
        try:
            return cls._EFFECT_CLASSES[effect_name](**kwargs)
        except Exception as e:
            logger.error(f"Error creando efecto {effect_name}: {e}")
            return None
    
    @classmethod
    def get_available_effects(cls) -> list:
        """Obtener lista de efectos disponibles."""
        return list(cls._EFFECT_CLASSES.keys())


def _register_effects():
    try:
        from src.infrastructure.audio.effects.delay import DelayEffect
        from src.infrastructure.audio.effects.distortion import DistortionEffect
        from src.infrastructure.audio.effects.reverb import ReverbEffect
        from src.infrastructure.audio.effects.chorus import ChorusEffect
        from src.infrastructure.audio.effects.compressor import CompressorEffect
        from src.infrastructure.audio.effects.equalizer import EQEffect
        from src.infrastructure.audio.effects.flanger import FlangerEffect
        from src.infrastructure.audio.effects.phaser import PhaserEffect
        from src.infrastructure.audio.effects.gate import GateEffect
        from src.infrastructure.audio.effects.limiter import LimiterEffect

        EffectFactory.register("delay", DelayEffect)
        EffectFactory.register("distortion", DistortionEffect)
        EffectFactory.register("overdrive", DistortionEffect)
        EffectFactory.register("reverb", ReverbEffect)
        EffectFactory.register("chorus", ChorusEffect)
        EffectFactory.register("compressor", CompressorEffect)
        EffectFactory.register("equalizer", EQEffect)
        EffectFactory.register("eq", EQEffect)
        EffectFactory.register("flanger", FlangerEffect)
        EffectFactory.register("phaser", PhaserEffect)
        EffectFactory.register("gate", GateEffect)
        EffectFactory.register("limiter", LimiterEffect)

        logger.info("Efectos DSP registrados en EffectFactory")
    except ImportError as e:
        logger.warning(f"No se pudieron registrar efectos DSP: {e}")


_register_effects()