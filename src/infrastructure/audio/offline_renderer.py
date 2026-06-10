"""Offline Renderer - Renderizado offline de audio.

Sistema de exportación de audio sin dependencia del tiempo real,
para renderizado de alta calidad.
"""

from typing import Optional, Callable, Dict, Any, List
import numpy as np
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class OfflineRenderer:
    """Renderizador offline de audio.
    
    Permite renderizar proyectos completos a archivos de audio
    sin las limitaciones del procesamiento en tiempo real.
    """
    
    def __init__(
        self,
        audio_engine,
        sample_rate: int = 44100,
        bit_depth: int = 16,
        audio_manager=None,
    ):
        """Inicializar el renderer.
        
        Args:
            audio_engine: Motor de audio a usar
            sample_rate: Sample rate de salida
            bit_depth: Profundidad de bits
            audio_manager: AudioManager opcional para datos de secuenciador
        """
        self._audio_engine = audio_engine
        self._sample_rate = sample_rate
        self._bit_depth = bit_depth
        self._audio_manager = audio_manager
        
        # Estado del renderizado
        self._is_rendering = False
        self._progress = 0.0
        self._cancel_requested = False
        
        # Callbacks
        self._progress_callback: Optional[Callable[[float], None]] = None
        self._status_callback: Optional[Callable[[str], None]] = None
        
        logger.info(f"OfflineRenderer inicializado: {sample_rate}Hz, {bit_depth}bit")
    
    @property
    def sample_rate(self) -> int:
        """Obtener sample rate."""
        return self._sample_rate
    
    @property
    def bit_depth(self) -> int:
        """Obtener profundidad de bits."""
        return self._bit_depth
    
    @property
    def is_rendering(self) -> bool:
        """Verificar si está renderizando."""
        return self._is_rendering
    
    @property
    def progress(self) -> float:
        """Obtener progreso (0.0 - 1.0)."""
        return self._progress
    
    def set_progress_callback(
        self,
        callback: Callable[[float], None]
    ) -> None:
        """Establecer callback de progreso.
        
        Args:
            callback: Función que recibe progreso (0.0 - 1.0)
        """
        self._progress_callback = callback
    
    def set_status_callback(
        self,
        callback: Callable[[str], None]
    ) -> None:
        """Establecer callback de estado.
        
        Args:
            callback: Función que recibe mensaje de estado
        """
        self._status_callback = callback
    
    def _update_progress(self, progress: float) -> None:
        """Actualizar progreso.
        
        Args:
            progress: Valor de 0.0 a 1.0
        """
        self._progress = max(0.0, min(1.0, progress))
        if self._progress_callback:
            self._progress_callback(self._progress)
    
    def _update_status(self, status: str) -> None:
        """Actualizar estado.
        
        Args:
            status: Mensaje de estado
        """
        logger.info(f"Render: {status}")
        if self._status_callback:
            self._status_callback(status)
    
    def request_cancel(self) -> None:
        """Solicitar cancelación del renderizado."""
        self._cancel_requested = True
        logger.info("Cancelación solicitada")
    
    def render_to_wav(
        self,
        output_path: Path,
        duration_samples: int,
        project: Any = None,
        bpm: int = 120
    ) -> bool:
        """Renderizar a archivo WAV.
        
        Args:
            output_path: Ruta de salida
            duration_samples: Duración en muestras
            project: Proyecto a renderizar
            bpm: BPM del proyecto
            
        Returns:
            True si fue exitoso
        """
        self._is_rendering = True
        self._cancel_requested = False
        self._progress = 0.0
        
        try:
            self._update_status(f"Renderizando a {output_path}")
            
            # Calcular tamaño de chunk para progreso
            chunk_size = 44100  # 1 segundo
            chunks = (duration_samples + chunk_size - 1) // chunk_size
            
            # Buffer de salida
            output = np.zeros((2, duration_samples), dtype=np.float32)
            
            # Procesar en chunks
            for i in range(chunks):
                if self._cancel_requested:
                    self._update_status("Renderizado cancelado")
                    return False
                
                start_sample = i * chunk_size
                end_sample = min((i + 1) * chunk_size, duration_samples)
                process_samples = end_sample - start_sample
                
                # Generar audio para este chunk
                chunk_audio = self._render_chunk(
                    start_sample,
                    process_samples,
                    project,
                    bpm
                )
                
                # Copiar al buffer de salida
                output[:, start_sample:end_sample] = chunk_audio
                
                # Actualizar progreso
                self._update_progress((i + 1) / chunks)
            
            # Escribir archivo WAV
            self._write_wav(output_path, output)
            
            self._update_status(f"Renderizado completado: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error en renderizado: {e}")
            self._update_status(f"Error: {e}")
            return False
            
        finally:
            self._is_rendering = False
    
    def _render_chunk(
        self,
        start_sample: int,
        num_samples: int,
        project: Any,
        bpm: int
    ) -> np.ndarray:
        """Renderizar un chunk de audio.
        
        Args:
            start_sample: Muestra inicial
            num_samples: Número de muestras
            project: Proyecto
            bpm: BPM
            
        Returns:
            Audio estéreo
        """
        audio = np.zeros((2, num_samples), dtype=np.float32)
        
        if self._audio_manager is not None:
            try:
                step_states = self._audio_manager.get_step_states()
                track_synths = self._audio_manager.get_all_track_synths()
                
                bpm = bpm or 120
                samples_per_step = int(self._sample_rate * 60.0 / bpm / 4.0)
                
                from src.infrastructure.audio.polyphonic_synth import PolyphonicSynth
                synth = PolyphonicSynth(sample_rate=self._sample_rate)
                
                step_start = start_sample // samples_per_step
                step_idx = 0
                
                for s in range(num_samples):
                    current_step = step_start + (s // samples_per_step)
                    for track_idx, steps in step_states.items():
                        if len(steps) > 0 and steps[current_step % len(steps)]:
                            track_data = track_synths.get(f"track_{track_idx}", {})
                            note = track_data.get("note", 60)
                            synth.note_on(note, 100)
                    
                    chunk = synth.process(1)
                    
                    for track_idx in step_states:
                        track_data = track_synths.get(f"track_{track_idx}", {})
                        note = track_data.get("note", 60)
                        synth.note_off(note)
                    
                    audio[0, s] = chunk[0]
                    audio[1, s] = chunk[0]
                
            except Exception as e:
                logger.warning(f"Error rendering chunk with audio_manager: {e}")
        
        return audio
    
    def _write_wav(
        self,
        path: Path,
        audio: np.ndarray
    ) -> None:
        """Escribir archivo WAV.
        
        Args:
            path: Ruta de salida
            audio: Audio estéreo
        """
        import wave
        
        # Normalizar si es necesario
        max_val = np.abs(audio).max()
        if max_val > 1.0:
            audio = audio / max_val
        
        # Convertir a int16 si es necesario
        if self._bit_depth == 16:
            audio_int = (audio * 32767).astype(np.int16)
            bytes_per_sample = 2
        elif self._bit_depth == 24:
            audio_int = (audio * 8388607).astype(np.int32)
            bytes_per_sample = 3
        elif self._bit_depth == 32:
            audio_int = (audio * 2147483647).astype(np.int32)
            bytes_per_sample = 4
        else:
            audio_int = (audio * 32767).astype(np.int16)
            bytes_per_sample = 2
        
        # Escribir archivo
        with wave.open(str(path), 'wb') as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(bytes_per_sample)
            wav_file.setframerate(self._sample_rate)
            
            # Intercalar canales
            if audio_int.ndim == 1:
                interleaved = audio_int
            else:
                interleaved = np.empty(
                    audio_int.shape[0] * audio_int.shape[1],
                    dtype=audio_int.dtype
                )
                interleaved[0::2] = audio_int[0]
                interleaved[1::2] = audio_int[1]
            
            wav_file.writeframes(interleaved.tobytes())
        
        logger.info(f"WAV escrito: {path}")
    
    def render_to_midi(
        self,
        output_path: Path,
        project: Any
    ) -> bool:
        """Exportar a MIDI.
        
        Args:
            output_path: Ruta de salida
            project: Proyecto
            
        Returns:
            True si fue exitoso
        """
        try:
            import mido
            mid = mido.MidiFile()
            mt = mido.MidiTrack()
            mid.tracks.append(mt)
            mt.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))
            
            if self._audio_manager:
                step_states = self._audio_manager.get_step_states()
                track_synths = self._audio_manager.get_all_track_synths()
                ticks_per_step = 120
                for track_idx, steps in step_states.items():
                    note = track_synths.get(f"track_{track_idx}", {}).get("note", 60)
                    for si, active in enumerate(steps):
                        if active:
                            t = si * ticks_per_step
                            mt.append(mido.Message('note_on', note=note, velocity=100, time=t))
                            mt.append(mido.Message('note_off', note=note, velocity=0, time=ticks_per_step // 2))
            
            mid.save(str(output_path))
            logger.info(f"MIDI exportado a: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting MIDI: {e}")
            return False
    
    def render_region(
        self,
        start_tick: int,
        end_tick: int,
        sample_rate: int,
        bpm: int,
        ticks_per_beat: int = 480
    ) -> np.ndarray:
        """Renderizar una región específica.
        
        Args:
            start_tick: Inicio en ticks
            end_tick: Fin en ticks
            sample_rate: Sample rate
            bpm: BPM
            ticks_per_beat: Ticks por beat
            
        Returns:
            Audio renderizado
        """
        # Calcular duración en muestras
        ticks = end_tick - start_tick
        beats = ticks / ticks_per_beat
        seconds = beats * 60.0 / bpm
        num_samples = int(seconds * sample_rate)
        
        # Renderizar
        return self._render_chunk(0, num_samples, None, bpm)
    
    def get_estimated_duration(
        self,
        total_ticks: int,
        bpm: int,
        ticks_per_beat: int = 480
    ) -> float:
        """Obtener duración estimada.
        
        Args:
            total_ticks: Ticks totales
            bpm: BPM
            ticks_per_beat: Ticks por beat
            
        Returns:
            Duración en segundos
        """
        beats = total_ticks / ticks_per_beat
        return beats * 60.0 / bpm
    
    def get_estimated_file_size(
        self,
        duration_seconds: float
    ) -> int:
        """Obtener tamaño estimado de archivo.
        
        Args:
            duration_seconds: Duración en segundos
            
        Returns:
            Tamaño en bytes
        """
        bytes_per_sample = self._bit_depth // 8
        bytes_per_second = self._sample_rate * 2 * bytes_per_sample
        return int(duration_seconds * bytes_per_second)


class ExportService:
    """Servicio de exportación.
    
    Coordina la exportación de proyectos a diferentes formatos.
    """
    
    def __init__(self, audio_engine, sample_rate: int = 44100, audio_manager=None):
        """Inicializar servicio de exportación.
        
        Args:
            audio_engine: Motor de audio
            sample_rate: Sample rate
            audio_manager: AudioManager (opcional) para datos de secuenciador
        """
        self._renderer = OfflineRenderer(audio_engine, sample_rate, audio_manager=audio_manager)
        self._sample_rate = sample_rate
        self._audio_manager = audio_manager
    
    @property
    def sample_rate(self) -> int:
        """Obtener sample rate."""
        return self._sample_rate
    
    def set_progress_callback(
        self,
        callback: Callable[[float], None]
    ) -> None:
        """Establecer callback de progreso."""
        self._renderer.set_progress_callback(callback)
    
    def set_status_callback(
        self,
        callback: Callable[[str], None]
    ) -> None:
        """Establecer callback de estado."""
        self._renderer.set_status_callback(callback)
    
    def export_wav(
        self,
        project: Any,
        output_path: str,
        bpm: int = 120,
        bit_depth: int = 16
    ) -> bool:
        """Exportar proyecto a WAV.
        
        Args:
            project: Proyecto
            output_path: Ruta de salida
            bpm: BPM
            bit_depth: Profundidad de bits
            
        Returns:
            True si fue exitoso
        """
        renderer = OfflineRenderer(
            audio_engine=self._renderer._audio_engine,
            sample_rate=self._sample_rate,
            bit_depth=bit_depth,
            audio_manager=self._audio_manager,
        )
        
        # Calcular duración
        duration_samples = int(
            self._renderer.get_estimated_duration(
                project.duration if hasattr(project, 'duration') else 10000,
                bpm
            ) * self._sample_rate
        )
        
        return renderer.render_to_wav(
            Path(output_path),
            duration_samples,
            project,
            bpm
        )
    
    def export_midi(
        self,
        project: Any,
        output_path: str
    ) -> bool:
        """Exportar proyecto a MIDI.
        
        Args:
            project: Proyecto
            output_path: Ruta de salida
            
        Returns:
            True si fue exitoso
        """
        renderer = OfflineRenderer(
            audio_engine=None,
            sample_rate=self._sample_rate
        )
        
        return renderer.render_to_midi(Path(output_path), project)
    
    def cancel_export(self) -> None:
        """Cancelar exportación en progreso."""
        self._renderer.request_cancel()
