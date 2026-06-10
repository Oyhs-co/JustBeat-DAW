"""Note Handler - Manejo de notas musicales.

Este handler es responsable de todas las operaciones relacionadas con notas,
incluyendo creación, edición, cuantización y transformación.
"""

from typing import Optional, List
import logging

from src.domain.entities.note import Note


logger = logging.getLogger(__name__)


class NoteHandler:
    """Handler para operaciones de notas.
    
    Maneja la creación, modificación y eliminación de notas.
    """
    
    def __init__(self):
        """Inicializar el handler de notas."""
        self._notes_cache: dict[str, Note] = {}
        logger.info("NoteHandler inicializado")
    
    def create_note(
        self,
        pitch: int = 60,
        velocity: int = 100,
        duration: int = 100,
        start_time: int = 0,
        channel: int = 0
    ) -> Note:
        """Crear una nueva nota.
        
        Args:
            pitch: Nota MIDI (0-127)
            velocity: Velocidad (0-127)
            duration: Duración en ticks
            start_time: Tiempo de inicio en ticks
            channel: Canal MIDI (0-15)
            
        Returns:
            La nota creada
        """
        note = Note(
            pitch=pitch,
            velocity=velocity,
            duration=duration,
            start_time=start_time
        )
        self._notes_cache[note.note_name] = note
        logger.debug(f"Nota creada: {note.note_name}")
        return note
    
    def create_note_from_name(
        self,
        note_name: str,
        velocity: int = 100,
        duration: int = 100,
        start_time: int = 0
    ) -> Note:
        """Crear una nota desde un nombre como 'C4' o 'F#5'.
        
        Args:
            note_name: Nombre de nota (ej: 'C4', 'F#5')
            velocity: Velocidad
            duration: Duración
            start_time: Tiempo de inicio
            
        Returns:
            La nota creada
        """
        note = Note.from_note_name(
            note_name=note_name,
            velocity=velocity,
            duration=duration,
            start_time=start_time
        )
        self._notes_cache[note.note_name] = note
        logger.debug(f"Nota creada: {note.note_name}")
        return note
    
    def transpose_note(self, note: Note, semitones: int) -> Note:
        """Transponer una nota.
        
        Args:
            note: Nota a transponer
            semitones: Semitones (positivo o negativo)
            
        Returns:
            Nueva nota transpuesta
        """
        new_note = note.transpose(semitones)
        self._notes_cache[new_note.note_name] = new_note
        logger.debug(f"Nota transpuesta: {note.note_name} -> {new_note.note_name}")
        return new_note
    
    def set_velocity(self, note: Note, velocity: int) -> None:
        """Establecer la velocidad de una nota.
        
        Args:
            note: Nota
            velocity: Nueva velocidad (0-127)
        """
        note.velocity = max(0, min(127, velocity))
        logger.debug(f"Velocidad de {note.note_name}: {note.velocity}")
    
    def set_duration(self, note: Note, duration: int) -> None:
        """Establecer la duración de una nota.
        
        Args:
            note: Nota
            duration: Nueva duración en ticks
        """
        note.duration = max(1, duration)
        logger.debug(f"Duración de {note.note_name}: {note.duration}")
    
    def set_start_time(self, note: Note, start_time: int) -> None:
        """Establecer el tiempo de inicio de una nota.
        
        Args:
            note: Nota
            start_time: Nuevo tiempo de inicio
        """
        note.start_time = max(0, start_time)
        logger.debug(f"Inicio de {note.note_name}: {note.start_time}")
    
    def quantize_note(
        self,
        note: Note,
        grid_size: int = 60
    ) -> Note:
        """Cuantizar el tiempo de inicio de una nota.
        
        Args:
            note: Nota a cuantizar
            grid_size: Tamaño de la rejilla en ticks
            
        Returns:
            Nota cuantizada
        """
        quantized_start = (note.start_time // grid_size) * grid_size
        note.start_time = quantized_start
        logger.debug(f"Nota cuantizada: {note.note_name} @ {quantized_start}")
        return note
    
    def quantize_duration(
        self,
        note: Note,
        grid_size: int = 60
    ) -> Note:
        """Cuantizar la duración de una nota.
        
        Args:
            note: Nota a cuantizar
            grid_size: Tamaño de la rejilla
            
        Returns:
            Nota cuantizada
        """
        quantized_duration = ((note.duration + grid_size - 1) // grid_size) * grid_size
        note.duration = quantized_duration
        logger.debug(f"Duración cuantizada: {note.note_name} @ {quantized_duration}")
        return note
    
    def add_note_to_track(self, track, note: Note) -> None:
        """Añadir una nota a una pista.
        
        Args:
            track: Pista destino
            note: Nota a añadir
        """
        # Las notas se almacenan en los patrones de la pista
        if hasattr(track, 'patterns') and track.patterns:
            # Añadir al primer patrón por defecto
            pattern = track.patterns[0]
            # Por ahora almacenamos en notes del track
            if not hasattr(track, 'notes'):
                track.notes = []
            track.notes.append(note)
            logger.debug(f"Nota {note.note_name} añadida a pista {track.name}")
    
    def remove_note_from_track(self, track, note_id: str) -> bool:
        """Eliminar una nota de una pista.
        
        Args:
            track: Pista
            note_id: ID de la nota
            
        Returns:
            True si se eliminó
        """
        if hasattr(track, 'notes'):
            for i, note in enumerate(track.notes):
                if hasattr(note, 'id') and note.id == note_id:
                    track.notes.pop(i)
                    logger.debug(f"Nota {note_id} eliminada de pista {track.name}")
                    return True
        return False
    
    def get_track_notes(self, track) -> List[Note]:
        """Obtener todas las notas de una pista.
        
        Args:
            track: Pista
            
        Returns:
            Lista de notas
        """
        if hasattr(track, 'notes'):
            return track.notes
        return []
    
    def get_note_state(self, note: Note) -> dict:
        """Obtener el estado de una nota.
        
        Args:
            note: Nota
            
        Returns:
            Diccionario con el estado
        """
        return {
            "pitch": note.pitch,
            "note_name": note.note_name,
            "velocity": note.velocity,
            "duration": note.duration,
            "start_time": note.start_time,
            "end_time": note.end_time,
        }
    
    def split_note(
        self,
        note: Note,
        split_time: int
    ) -> List[Note]:
        """Dividir una nota en dos.
        
        Args:
            note: Nota a dividir
            split_time: Tiempo donde dividir
            
        Returns:
            Lista con las dos notas resultantes
        """
        if split_time <= note.start_time or split_time >= note.end_time:
            logger.warning("Tiempo de división fuera de rango")
            return [note]
        
        # Primera nota
        note1 = Note(
            pitch=note.pitch,
            velocity=note.velocity,
            duration=split_time - note.start_time,
            start_time=note.start_time
        )
        
        # Segunda nota
        note2 = Note(
            pitch=note.pitch,
            velocity=note.velocity,
            duration=note.end_time - split_time,
            start_time=split_time
        )
        
        logger.debug(f"Nota dividida: {note.note_name} -> {note1.note_name}, {note2.note_name}")
        return [note1, note2]
    
    def adjust_velocity_linear(
        self,
        notes: List[Note],
        start_velocity: int,
        end_velocity: int
    ) -> List[Note]:
        """Ajustar velocidad linealmente entre notas.
        
        Args:
            notes: Lista de notas
            velocity_inicial: Velocidad inicial
            velocity_final: Velocidad final
            
        Returns:
            Lista de notas con velocidades ajustadas
        """
        if not notes:
            return notes
        
        if len(notes) == 1:
            notes[0].velocity = start_velocity
            return notes
        
        velocity_range = end_velocity - start_velocity
        step = velocity_range / (len(notes) - 1)
        
        for i, note in enumerate(notes):
            note.velocity = int(start_velocity + (step * i))
        
        logger.debug(f"Velocidad ajustada: {start_velocity} -> {end_velocity}")
        return notes
