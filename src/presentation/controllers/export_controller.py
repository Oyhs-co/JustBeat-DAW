"""Export Controller - Unified export system for JustBeat-DAW.

This module provides:
- AudioExporter: Export mixed audio to WAV/FLAC/MP3
- StemsExporter: Export individual track stems
- ProjectSerializer: Save/load project files
- ExportDialog: UI for export options
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable
import threading

import numpy as np

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Supported export formats."""
    WAV = "wav"
    FLAC = "flac"
    MP3 = "mp3"
    OGG = "ogg"


class ExportQuality(Enum):
    """Export quality presets."""
    LOW = "low"       # 128 kbps / 22kHz
    MEDIUM = "medium" # 192 kbps / 44.1kHz
    HIGH = "high"    # 256 kbps / 44.1kHz
    LOSSLESS = "lossless"  # 320 kbps / 48kHz


@dataclass
class ExportSettings:
    """Settings for audio export."""
    format: ExportFormat = ExportFormat.WAV
    quality: ExportQuality = ExportQuality.HIGH
    sample_rate: int = 44100
    bit_depth: int = 16
    channels: int = 2  # 1 = mono, 2 = stereo
    normalize: bool = True
    fade_out: float = 0.0  # seconds
    start_time: float = 0.0  # seconds
    end_time: float = 0.0  # 0 = full length
    
    def get_bit_rate(self) -> int:
        """Get bit rate based on quality."""
        rates = {
            ExportQuality.LOW: 128000,
            ExportQuality.MEDIUM: 192000,
            ExportQuality.HIGH: 256000,
            ExportQuality.LOSSLESS: 320000,
        }
        return rates.get(self.quality, 192000)


@dataclass
class ExportProgress:
    """Progress information for export."""
    current_track: int = 0
    total_tracks: int = 0
    progress: float = 0.0  # 0.0 to 1.0
    status: str = ""
    is_complete: bool = False
    error: Optional[str] = None


class AudioExporter:
    """Export mixed audio to various formats."""
    
    def __init__(self) -> None:
        """Initialize the audio exporter."""
        self._cancel_flag = False
    
    def cancel(self) -> None:
        """Cancel the current export."""
        self._cancel_flag = True
    
    def export(
        self,
        audio_data: np.ndarray,
        output_path: Path,
        settings: ExportSettings,
        progress_callback: Optional[Callable[[ExportProgress], None]] = None
    ) -> bool:
        """Export audio to file.
        
        Args:
            audio_data: Audio samples
            output_path: Output file path
            settings: Export settings
            progress_callback: Callback for progress updates
            
        Returns:
            True if export successful
        """
        self._cancel_flag = False
        
        try:
            progress = ExportProgress(
                status="Preparing export...",
                progress=0.0
            )
            
            if progress_callback:
                progress_callback(progress)
            
            # Normalize if requested
            if settings.normalize:
                audio_data = self._normalize(audio_data)
            
            # Apply fade out
            if settings.fade_out > 0:
                audio_data = self._apply_fade_out(audio_data, settings)
            
            # Export based on format
            if settings.format == ExportFormat.WAV:
                success = self._export_wav(audio_data, output_path, settings, progress_callback)
            elif settings.format == ExportFormat.FLAC:
                success = self._export_flac(audio_data, output_path, settings, progress_callback)
            elif settings.format == ExportFormat.MP3:
                success = self._export_mp3(audio_data, output_path, settings, progress_callback)
            elif settings.format == ExportFormat.OGG:
                success = self._export_ogg(audio_data, output_path, settings, progress_callback)
            else:
                raise ValueError(f"Unsupported format: {settings.format}")
            
            progress.is_complete = True
            progress.progress = 1.0
            progress.status = "Export complete"
            
            if progress_callback:
                progress_callback(progress)
            
            return success
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            
            progress = ExportProgress(
                is_complete=True,
                error=str(e)
            )
            
            if progress_callback:
                progress_callback(progress)
            
            return False
    
    def _normalize(self, audio_data: np.ndarray) -> np.ndarray:
        """Normalize audio to prevent clipping."""
        max_val = np.abs(audio_data).max()
        if max_val > 0:
            # Normalize to 0.95 to leave headroom
            audio_data = audio_data * (0.95 / max_val)
        return audio_data
    
    def _apply_fade_out(
        self, audio_data: np.ndarray, settings: ExportSettings
    ) -> np.ndarray:
        """Apply fade out to audio."""
        sample_rate = settings.sample_rate
        fade_samples = int(settings.fade_out * sample_rate)
        
        if fade_samples >= len(audio_data):
            return audio_data * 0
        
        fade_curve = np.linspace(1.0, 0.0, fade_samples)
        
        if audio_data.ndim == 1:
            audio_data[-fade_samples:] *= fade_curve
        else:
            audio_data[-fade_samples:] *= fade_curve[:, np.newaxis]
        
        return audio_data
    
    def _export_wav(
        self,
        audio_data: np.ndarray,
        output_path: Path,
        settings: ExportSettings,
        progress_callback: Optional[Callable]
    ) -> bool:
        """Export to WAV format."""
        logger.info(f"Export WAV: path={output_path}, sr={settings.sample_rate}, bit_depth={settings.bit_depth}, channels={settings.channels}")
        import wave
        
        progress = ExportProgress(status="Exporting WAV...", progress=0.5)
        if progress_callback:
            progress_callback(progress)
        
        try:
            # Convert to appropriate format
            if settings.bit_depth == 16:
                audio_int = (audio_data * 32767.0).astype(np.int16)
            elif settings.bit_depth == 24:
                audio_int = (audio_data * 8388607.0).astype(np.int32)
            elif settings.bit_depth == 32:
                audio_int = audio_data.astype(np.float32)
            else:
                raise ValueError(f"Unsupported bit depth: {settings.bit_depth}")
            
            # Determine channels
            if audio_data.ndim == 1:
                num_channels = 1
            else:
                num_channels = audio_data.shape[1]
            
            # Write WAV
            with wave.open(str(output_path), 'wb') as wav_file:
                wav_file.setnchannels(num_channels)
                wav_file.setsampwidth(settings.bit_depth // 8)
                wav_file.setframerate(settings.sample_rate)
                
                # Interleave if stereo
                if num_channels == 2:
                    audio_int = audio_int.T.flatten()
                
                wav_file.writeframes(audio_int.tobytes())
            
            return True
            
        except Exception as e:
            logger.error(f"WAV export failed: {e}")
            return False
    
    def _export_flac(
        self,
        audio_data: np.ndarray,
        output_path: Path,
        settings: ExportSettings,
        progress_callback: Optional[Callable]
    ) -> bool:
        """Export to FLAC format."""
        logger.info(f"Export FLAC: path={output_path}, sr={settings.sample_rate}, bit_depth={settings.bit_depth}")
        # FLAC export would require soundfile library
        logger.warning("FLAC export not fully implemented, falling back to WAV")
        
        # Change extension to .wav
        wav_path = output_path.with_suffix(".wav")
        return self._export_wav(audio_data, wav_path, settings, progress_callback)
    
    def _export_mp3(
        self,
        audio_data: np.ndarray,
        output_path: Path,
        settings: ExportSettings,
        progress_callback: Optional[Callable]
    ) -> bool:
        """Export to MP3 format."""
        logger.info(f"Export MP3: path={output_path}, sr={settings.sample_rate}, quality={settings.quality.value}")
        # MP3 export would require pydub or lame
        logger.warning("MP3 export not fully implemented, falling back to WAV")
        
        # Change extension to .wav
        wav_path = output_path.with_suffix(".wav")
        return self._export_wav(audio_data, wav_path, settings, progress_callback)
    
    def _export_ogg(
        self,
        audio_data: np.ndarray,
        output_path: Path,
        settings: ExportSettings,
        progress_callback: Optional[Callable]
    ) -> bool:
        """Export to OGG format."""
        logger.info(f"Export OGG: path={output_path}, sr={settings.sample_rate}, quality={settings.quality.value}")
        from src.infrastructure.export.ogg_exporter import OGGExporter

        quality_map = {
            ExportQuality.LOW: 0.1,
            ExportQuality.MEDIUM: 0.4,
            ExportQuality.HIGH: 0.7,
            ExportQuality.LOSSLESS: 0.9,
        }
        quality = quality_map.get(settings.quality, 0.5)
        sr = settings.sample_rate or 44100

        exporter = OGGExporter(sample_rate=sr, quality=quality)
        return exporter.export(audio_data, output_path, progress_callback)


class StemsExporter:
    """Export individual track stems."""
    
    def __init__(self) -> None:
        """Initialize the stems exporter."""
        self._cancel_flag = False
        self._audio_exporter = AudioExporter()
    
    def cancel(self) -> None:
        """Cancel the current export."""
        self._cancel_flag = True
    
    def export_tracks(
        self,
        track_audios: Dict[str, np.ndarray],
        output_dir: Path,
        settings: ExportSettings,
        track_names: Dict[str, str],
        progress_callback: Optional[Callable[[ExportProgress], None]] = None
    ) -> bool:
        """Export tracks as separate stems.
        
        Args:
            track_audios: Dictionary of track_id -> audio data
            output_dir: Output directory for stems
            settings: Export settings
            track_names: Dictionary of track_id -> track name
            progress_callback: Callback for progress updates
            
        Returns:
            True if all exports successful
        """
        self._cancel_flag = False
        
        total_tracks = len(track_audios)
        success_count = 0
        
        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            for i, (track_id, audio_data) in enumerate(track_audios.items()):
                if self._cancel_flag:
                    logger.info("Export cancelled by user")
                    break
                
                progress = ExportProgress(
                    current_track=i + 1,
                    total_tracks=total_tracks,
                    progress=i / total_tracks,
                    status=f"Exporting stem {i + 1}/{total_tracks}"
                )
                
                if progress_callback:
                    progress_callback(progress)
                
                # Get track name
                track_name = track_names.get(track_id, f"Track_{i + 1}")
                
                # Sanitize filename
                safe_name = "".join(c for c in track_name if c.isalnum() or c in " -_")
                
                # Create output path
                output_path = output_dir / f"{safe_name}.wav"
                
                # Export stem
                if self._audio_exporter.export(audio_data, output_path, settings):
                    success_count += 1
            
            progress = ExportProgress(
                current_track=total_tracks,
                total_tracks=total_tracks,
                progress=1.0,
                status=f"Exported {success_count}/{total_tracks} stems",
                is_complete=True
            )
            
            if progress_callback:
                progress_callback(progress)
            
            return success_count == total_tracks
            
        except Exception as e:
            logger.error(f"Stems export failed: {e}")
            return False


class ExportController:
    """Controller for export operations."""
    
    def __init__(self) -> None:
        """Initialize the export controller."""
        self._audio_exporter = AudioExporter()
        self._stems_exporter = StemsExporter()
        
        logger.info("ExportController initialized")
    
    def export_audio(
        self,
        audio_data: np.ndarray,
        output_path: Path,
        settings: ExportSettings,
        progress_callback: Optional[Callable[[ExportProgress], None]] = None
    ) -> bool:
        """Export mixed audio.
        
        Args:
            audio_data: Mixed audio data
            output_path: Output file path
            settings: Export settings
            progress_callback: Progress callback
            
        Returns:
            True if successful
        """
        return self._audio_exporter.export(
            audio_data, output_path, settings, progress_callback
        )
    
    def export_stems(
        self,
        track_audios: Dict[str, np.ndarray],
        output_dir: Path,
        settings: ExportSettings,
        track_names: Dict[str, str],
        progress_callback: Optional[Callable[[ExportProgress], None]] = None
    ) -> bool:
        """Export track stems.
        
        Args:
            track_audios: Dictionary of track_id -> audio
            output_dir: Output directory
            settings: Export settings
            track_names: Track names
            progress_callback: Progress callback
            
        Returns:
            True if successful
        """
        return self._stems_exporter.export_tracks(
            track_audios, output_dir, settings, track_names, progress_callback
        )
    
    def cancel_export(self) -> None:
        """Cancel ongoing export."""
        self._audio_exporter.cancel()
        self._stems_exporter.cancel()
