"""Audio Router - Routing de audio entre componentes.

Maneja el flujo de audio desde los instrumentos hasta la salida,
incluyendo efectos, mezcla y master.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import numpy as np
import logging

from src.infrastructure.audio.polyphonic_synth import PolyphonicSynth
from src.infrastructure.audio.mixer_engine import MixerEngine
from src.infrastructure.audio.mixer_channel import ChannelStrip


logger = logging.getLogger(__name__)


@dataclass
class TrackChannel:
    """Canal de audio asociado a un track."""
    track_id: str
    synth: PolyphonicSynth
    mixer_channel: Optional[ChannelStrip] = None
    effects: List[Any] = field(default_factory=list)
    volume: float = 0.8
    pan: float = 0.0
    muted: bool = False
    solo: bool = False


class AudioRouter:
    """Router de audio centralizado.
    
    Maneja el flujo de audio desde tracks → canales → efectos → mixer → master.
    """
    
    def __init__(
        self,
        sample_rate: int = 44100,
        buffer_size: int = 512,
        verbose_audio: bool = False,
    ):
        """Inicializar el router de audio.

        Args:
            sample_rate: Tasa de muestreo
            buffer_size: Tamaño de buffer
            verbose_audio: Log detallado de cada process_buffer
        """
        self._sample_rate = sample_rate
        self._buffer_size = buffer_size
        self._verbose_audio = verbose_audio
        
        # Canales de tracks
        self._track_channels: Dict[str, TrackChannel] = {}
        
        # Sintetizador global (para step sequencer)
        self._global_synth: Optional[PolyphonicSynth] = None
        
        # Mixer
        self._mixer = MixerEngine(
            sample_rate=sample_rate,
            buffer_size=buffer_size
        )
        
        # Master
        self._master_volume: float = 0.8
        self._master_peak: float = 0.0
        
        # Efectos globales (post-mixer)
        self._master_effects: List[Any] = []
        
        # Último buffer procesado (para visualización en tiempo real)
        self._last_output_buffer: np.ndarray = np.zeros((buffer_size, 4), dtype=np.float32)
        
        # Rate-limiting para logs de process_buffer
        self._process_buffer_count: int = 0
        self._next_verbose_log: int = 0
        
        logger.info(f"AudioRouter inicializado: {sample_rate}Hz, buffer {buffer_size}")
    
    @property
    def mixer(self) -> MixerEngine:
        """Obtener el mixer."""
        return self._mixer
    
    def set_global_synth(self, synth: PolyphonicSynth) -> None:
        """Establecer sintetizador global.
        
        Args:
            synth: PolyphonicSynth instance
        """
        self._global_synth = synth
    
    def create_track_channel(
        self,
        track_id: str,
        waveform: str = "square",
        note: int = 60,
        volume: float = 0.8
    ) -> TrackChannel:
        """Crear un canal de audio para un track.
        
        Args:
            track_id: ID del track
            waveform: Forma de onda inicial
            note: Nota MIDI base
            volume: Volumen inicial
            
        Returns:
            TrackChannel creado o existente
        """
        # Si ya existe, removerlo primero para recrear
        if track_id in self._track_channels:
            self.remove_track_channel(track_id)
        
        # Crear sintetizador para el track
        synth = PolyphonicSynth(
            sample_rate=self._sample_rate,
            max_voices=8  # Menos voces por track
        )
        synth.set_waveform(waveform)
        
        # Crear canal en mixer (remover primero si existe)
        try:
            mixer_channel = self._mixer.add_channel(
                channel_id=track_id,
                name=track_id
            )
        except ValueError:
            # El canal ya existe, obtenerlo
            mixer_channel = self._mixer.get_channel(track_id)
            if mixer_channel is None:
                raise
        
        mixer_channel.volume = volume
        
        # Crear TrackChannel
        track_channel = TrackChannel(
            track_id=track_id,
            synth=synth,
            mixer_channel=mixer_channel,
            volume=volume
        )
        
        self._track_channels[track_id] = track_channel
        logger.info(f"Canal de audio creado para track: {track_id}")
        
        return track_channel
    
    def remove_track_channel(self, track_id: str) -> bool:
        """Eliminar un canal de audio.
        
        Args:
            track_id: ID del track
            
        Returns:
            True si se eliminó
        """
        if track_id in self._track_channels:
            channel = self._track_channels[track_id]
            
            # Remover del mixer
            if channel.mixer_channel:
                self._mixer.remove_channel(track_id)
            
            del self._track_channels[track_id]
            logger.info(f"Canal de audio eliminado para track: {track_id}")
            return True
        return False
    
    def get_track_channel(self, track_id: str) -> Optional[TrackChannel]:
        """Obtener un canal de track.
        
        Args:
            track_id: ID del track
            
        Returns:
            TrackChannel o None
        """
        return self._track_channels.get(track_id)
    
    def set_track_volume(self, track_id: str, volume: float) -> bool:
        """Establecer volumen de un track.
        
        Args:
            track_id: ID del track
            volume: Volumen (0.0 - 1.0)
            
        Returns:
            True si se estableció
        """
        channel = self._track_channels.get(track_id)
        if channel:
            channel.volume = max(0.0, min(1.0, volume))
            if channel.mixer_channel:
                channel.mixer_channel.volume = channel.volume
            return True
        return False
    
    def set_track_pan(self, track_id: str, pan: float) -> bool:
        """Establecer panorámica de un track.
        
        Args:
            track_id: ID del track
            pan: Pan (-1.0 a 1.0)
            
        Returns:
            True si se estableció
        """
        channel = self._track_channels.get(track_id)
        if channel:
            channel.pan = max(-1.0, min(1.0, pan))
            if channel.mixer_channel:
                channel.mixer_channel.pan = channel.pan
            return True
        return False
    
    def set_track_mute(self, track_id: str, muted: bool) -> bool:
        """Establecer mute de un track.
        
        Args:
            track_id: ID del track
            muted: Estado de mute
            
        Returns:
            True si se estableció
        """
        channel = self._track_channels.get(track_id)
        if channel:
            channel.muted = muted
            if channel.mixer_channel:
                channel.mixer_channel.mute = muted
            return True
        return False
    
    def set_track_solo(self, track_id: str, solo: bool) -> bool:
        """Establecer solo de un track.
        
        Args:
            track_id: ID del track
            solo: Estado de solo
            
        Returns:
            True si se estableció
        """
        channel = self._track_channels.get(track_id)
        if channel:
            channel.solo = solo
            # Actualizar estado de solo en mixer
            self._update_solo_state()
            return True
        return False
    
    def _update_solo_state(self) -> None:
        """Actualizar estado de solo en mixer."""
        has_solo = any(ch.solo for ch in self._track_channels.values())
        
        for channel in self._track_channels.values():
            if channel.mixer_channel:
                if has_solo:
                    # Si hay algún solo, solo escuchar los que tienen solo
                    channel.mixer_channel.solo = channel.solo
                else:
                    # Si no hay solo, tutti
                    channel.mixer_channel.solo = False
    
    def add_effect_to_track(
        self,
        track_id: str,
        effect: Any,
        position: int = -1
    ) -> bool:
        """Añadir un efecto a un track.
        
        Args:
            track_id: ID del track
            effect: Efecto a añadir (debe implementar process())
            position: Posición en la cadena (-1 = al final)
            
        Returns:
            True si se añadió
        """
        channel = self._track_channels.get(track_id)
        if channel:
            if position < 0:
                channel.effects.append(effect)
            else:
                channel.effects.insert(position, effect)
            logger.debug(f"Efecto añadido a track {track_id}")
            return True
        return False
    
    def remove_effect_from_track(
        self,
        track_id: str,
        effect_index: int
    ) -> bool:
        """Quitar un efecto de un track.
        
        Args:
            track_id: ID del track
            effect_index: Índice del efecto
            
        Returns:
            True si se quitó
        """
        channel = self._track_channels.get(track_id)
        if channel and 0 <= effect_index < len(channel.effects):
            channel.effects.pop(effect_index)
            return True
        return False
    
    def clear_track_effects(self, track_id: str) -> bool:
        """Limpiar todos los efectos de un track.
        
        Args:
            track_id: ID del track
            
        Returns:
            True si se limpió
        """
        channel = self._track_channels.get(track_id)
        if channel:
            channel.effects.clear()
            return True
        return False
    
    def set_waveform(self, track_id: str, waveform: str) -> bool:
        """Establecer forma de onda de un track.
        
        Args:
            track_id: ID del track
            waveform: Tipo de forma de onda
        """
        channel = self._track_channels.get(track_id)
        if channel:
            channel.synth.set_waveform(waveform)
            return True
        return False
    
    def set_synth_parameter(self, track_id: str, param: str, value: Any) -> bool:
        """Establecer parámetro del sintetizador.
        
        Args:
            track_id: ID del track
            param: Nombre del parámetro
            value: Valor
        """
        channel = self._track_channels.get(track_id)
        if channel:
            channel.synth.set_parameter(param, value)
            return True
        return False
    
    def note_on(self, track_id: str, note: int, velocity: int = 100) -> bool:
        """Activar nota en un track.
        
        Args:
            track_id: ID del track
            note: Nota MIDI
            velocity: Velocidad
            
        Returns:
            True si se activó
        """
        channel = self._track_channels.get(track_id)
        if channel and not channel.muted:
            channel.synth.note_on(note, velocity)
            return True
        return False
    
    def note_off(self, track_id: str, note: int) -> bool:
        """Desactivar nota en un track.
        
        Args:
            track_id: ID del track
            note: Nota MIDI
            
        Returns:
            True si se desactivó
        """
        channel = self._track_channels.get(track_id)
        if channel:
            channel.synth.note_off(note)
            return True
        return False
    
    def all_notes_off(self) -> None:
        """Desactivar todas las notas."""
        for channel in self._track_channels.values():
            channel.synth.all_notes_off()
        if self._global_synth:
            self._global_synth.all_notes_off()
    
    def process_buffer(self, num_samples: int) -> np.ndarray:
        """Procesar un buffer de audio.
        
        Args:
            num_samples: Número de muestras
            
        Returns:
            Audio quad (shape: [num_samples, 4])
        """
        self._process_buffer_count += 1
        if self._verbose_audio and self._process_buffer_count > self._next_verbose_log:
            logger.debug(f"AudioRouter.process_buffer: {num_samples} samples, {len(self._track_channels)} tracks")
            self._next_verbose_log = self._process_buffer_count + 43
        
        # Procesar cada canal de track
        mixer_input: Dict[str, np.ndarray] = {}
        
        for track_id, channel in self._track_channels.items():
            if channel.muted:
                continue
            
            # Procesar sintetizador (mono output)
            audio = channel.synth.process(num_samples)
            
            # Asegurar que es mono 1D
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            
            # Aplicar efectos de cadena
            for effect in channel.effects:
                if hasattr(effect, 'process'):
                    try:
                        effect_buffer = effect.process(audio)
                        if effect_buffer.ndim > 1:
                            audio = effect_buffer.mean(axis=1)
                        else:
                            audio = effect_buffer
                    except Exception as e:
                        logger.warning(f"Error en efecto {effect}: {e}")
            
            mixer_input[track_id] = audio
        
        # Si no hay inputs, silencio quad
        if not mixer_input:
            return np.zeros((num_samples, 4), dtype=np.float32)
        
        # Mezclar usando el mixer - procesar a quad
        try:
            mixed = self._mixer.process_quad(mixer_input, num_samples)
        except Exception as e:
            logger.warning(f"Error en mixer.process_quad: {e}")
            # Fallback: usar process_stereo y replicar a 4 canales
            try:
                stereo = self._mixer.process_stereo(mixer_input, num_samples)
                # Replicar a quad: [L, R] -> [L, R, L, R]
                mixed = np.zeros((4, num_samples), dtype=np.float32)
                mixed[0] = stereo[0]
                mixed[1] = stereo[1]
                mixed[2] = stereo[0]
                mixed[3] = stereo[1]
            except Exception as e2:
                logger.warning(f"Error en mixer fallback: {e2}")
                return np.zeros((num_samples, 4), dtype=np.float32)
        
        # mixed es (4, num_samples) - transponer a (num_samples, 4)
        mixed = mixed.T

        # Verificar forma
        if mixed.shape[1] != 4:
            logger.warning(f"Forma de audio incorrecta: {mixed.shape}")
            # Ajustar a 4 canales
            if mixed.shape[1] == 2:
                # Replicar estéreo a quad
                new_mixed = np.zeros((num_samples, 4), dtype=np.float32)
                new_mixed[:, 0] = mixed[:, 0]  # L
                new_mixed[:, 1] = mixed[:, 1]  # R
                new_mixed[:, 2] = mixed[:, 0]  # L
                new_mixed[:, 3] = mixed[:, 1]  # R
                mixed = new_mixed
            else:
                mixed = np.zeros((num_samples, 4), dtype=np.float32)
        
        # Aplicar efectos master (mono processing)
        for effect in self._master_effects:
            if hasattr(effect, 'process'):
                mono_audio = mixed.mean(axis=1)
                effect_output = effect.process(mono_audio)
                if effect_output.ndim > 1:
                    # Expandir a quad
                    new_mixed = np.zeros((num_samples, 4), dtype=np.float32)
                    if effect_output.shape[1] >= 2:
                        new_mixed[:, 0] = effect_output[:, 0]
                        new_mixed[:, 1] = effect_output[:, 1]
                        new_mixed[:, 2] = effect_output[:, 0]
                        new_mixed[:, 3] = effect_output[:, 1]
                    mixed = new_mixed
                else:
                    # Replicar mono a quad
                    new_mixed = np.zeros((num_samples, 4), dtype=np.float32)
                    for i in range(4):
                        new_mixed[:, i] = effect_output
                    mixed = new_mixed
        
        # Aplicar volumen master
        mixed *= self._master_volume
        
        # Soft clip
        max_val = np.max(np.abs(mixed)) + 0.0001
        if max_val > 1.0:
            mixed = mixed / max_val
        mixed = np.tanh(mixed * 0.8)
        
        # Calcular pico (promedio de todos los canales)
        self._master_peak = np.max(np.abs(mixed))
        
        # Guardar para visualización
        self._last_output_buffer = mixed
        
        return mixed
    
    def get_last_buffer(self) -> np.ndarray:
        """Obtener el último buffer de audio procesado.

        Returns:
            Array numpy (num_samples, 4) con el buffer más reciente
        """
        return self._last_output_buffer.copy()

    def get_output_level(self) -> float:
        """Obtener nivel de salida actual."""
        return self._master_peak
    
    def get_track_levels(self) -> Dict[str, float]:
        """Obtener niveles de cada track.
        
        Returns:
            Diccionario {track_id: nivel}
        """
        levels = {}
        for track_id, channel in self._track_channels.items():
            if channel.mixer_channel:
                levels[track_id] = (channel.mixer_channel.peak_left + 
                                   channel.mixer_channel.peak_right) / 2
            else:
                levels[track_id] = 0.0
        return levels
    
    def set_master_volume(self, volume: float) -> None:
        """Establecer volumen master.
        
        Args:
            volume: Volumen (0.0 - 1.0)
        """
        self._master_volume = max(0.0, min(1.0, volume))
    
    def add_master_effect(self, effect: Any) -> None:
        """Añadir efecto al master.
        
        Args:
            effect: Efecto a añadir
        """
        self._master_effects.append(effect)
    
    def clear_master_effects(self) -> None:
        """Limpiar efectos del master."""
        self._master_effects.clear()
    
    def get_track_count(self) -> int:
        """Obtener número de tracks."""
        return len(self._track_channels)
    
    def get_all_track_ids(self) -> List[str]:
        """Obtener todos los IDs de tracks."""
        return list(self._track_channels.keys())