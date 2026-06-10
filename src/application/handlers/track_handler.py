"""Track Handler - Manejo de pistas y clips.

Este handler es responsable de todas las operaciones relacionadas con pistas,
incluyendo gestión de volumen, pan, mute, solo, y efectos.
"""

from typing import Optional, List
import logging

from src.domain.entities.track import Track
from src.domain.entities.pattern import Pattern


logger = logging.getLogger(__name__)


class TrackHandler:
    """Handler para operaciones de pistas.
    
    Maneja la creación, modificación y eliminación de pistas.
    """
    
    def __init__(self):
        """Inicializar el handler de pistas."""
        self._tracks_cache: dict[str, Track] = {}
        logger.info("TrackHandler inicializado")
    
    def create_track(
        self,
        name: str = "New Track",
        instrument_id: Optional[str] = None
    ) -> Track:
        """Crear una nueva pista.
        
        Args:
            name: Nombre de la pista
            instrument_id: ID del instrumento
            
        Returns:
            La pista creada
        """
        logger.info(f"Add track requested: name={name}, instrument_id={instrument_id}")
        track = Track(name=name, instrument_id=instrument_id)
        # Añadir un patrón inicial
        track.patterns.append(Pattern(name="Pattern 1", length=16))
        self._tracks_cache[track.id] = track
        logger.info(f"Pista creada: {name} ({track.id})")
        return track
    
    def set_volume(self, track: Track, volume: float) -> bool:
        """Establecer el volumen de una pista.
        
        Args:
            track: Pista
            volume: Volumen (0.0 - 1.0)
            
        Returns:
            True si se estableció correctamente
        """
        try:
            track.set_volume(volume)
            logger.debug(f"Volumen de {track.name}: {volume}")
            return True
        except ValueError as e:
            logger.error(f"Error estableciendo volumen: {e}")
            return False
    
    def set_pan(self, track: Track, pan: float) -> bool:
        """Establecer el pan de una pista.
        
        Args:
            track: Pista
            pan: Pan (-1.0 a 1.0)
            
        Returns:
            True si se estableció correctamente
        """
        try:
            track.set_pan(pan)
            logger.debug(f"Pan de {track.name}: {pan}")
            return True
        except ValueError as e:
            logger.error(f"Error estableciendo pan: {e}")
            return False
    
    def toggle_mute(self, track: Track) -> None:
        """Alternar mute de una pista."""
        logger.info(f"Mute track: {track.name} (id={track.id})")
        track.toggle_mute()
        logger.debug(f"Mute de {track.name}: {track.muted}")
    
    def toggle_solo(self, track: Track) -> None:
        """Alternar solo de una pista."""
        logger.info(f"Solo track: {track.name} (id={track.id})")
        track.toggle_solo()
        logger.debug(f"Solo de {track.name}: {track.solo}")
    
    def set_instrument(self, track: Track, instrument_id: str) -> None:
        """Establecer el instrumento de una pista."""
        track.instrument_id = instrument_id
        logger.debug(f"Instrumento de {track.name}: {instrument_id}")
    
    def add_effect(self, track: Track, effect_id: str) -> bool:
        """Añadir un efecto a la cadena de efectos."""
        if effect_id in track.effect_chain:
            logger.warning(f"Efecto {effect_id} ya está en la cadena")
            return False
        
        track.add_effect(effect_id)
        logger.debug(f"Efecto añadido a {track.name}: {effect_id}")
        return True
    
    def remove_effect(self, track: Track, effect_id: str) -> bool:
        """Quitar un efecto de la cadena de efectos."""
        if effect_id not in track.effect_chain:
            logger.warning(f"Efecto {effect_id} no está en la cadena")
            return False
        
        track.remove_effect(effect_id)
        logger.debug(f"Efecto quitado de {track.name}: {effect_id}")
        return True
    
    def get_track_state(self, track: Track) -> dict:
        """Obtener el estado completo de una pista."""
        return {
            "id": track.id,
            "name": track.name,
            "volume": track.volume,
            "pan": track.pan,
            "muted": track.muted,
            "solo": track.solo,
            "instrument_id": track.instrument_id,
            "effect_chain": list(track.effect_chain),
        }
