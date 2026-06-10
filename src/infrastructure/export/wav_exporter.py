"""WAV exporter - Export audio to WAV format."""

import numpy as np
import wave
from pathlib import Path
from typing import Optional


class WAVExporter:
    """Export audio to WAV format."""
    
    def __init__(self, sample_rate: int = 44100, bit_depth: int = 16):
        """Initialize the WAV exporter.
        
        Args:
            sample_rate: Audio sample rate in Hz
            bit_depth: Bit depth (8, 16, 24, or 32)
        """
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
    
    def export(self, audio_data: np.ndarray, 
               output_path: Path) -> bool:
        """Export audio data to WAV file.
        
        Args:
            audio_data: Audio samples (normalized -1.0 to 1.0)
            output_path: Output file path
            
        Returns:
            True if export successful
        """
        try:
            # Convert to appropriate format
            if self.bit_depth == 8:
                # 8-bit WAV uses unsigned bytes (128 = 0)
                audio_int = ((audio_data + 1.0) * 127.5).astype(np.uint8)
                num_channels = 1
            elif self.bit_depth == 16:
                # 16-bit signed integers
                audio_int = (audio_data * 32767.0).astype(np.int16)
                num_channels = 1 if audio_data.ndim == 1 else audio_data.shape[1]
            elif self.bit_depth == 24:
                # 24-bit - convert to int32 then truncate
                audio_int = (audio_data * 8388607.0).astype(np.int32)
                num_channels = 1 if audio_data.ndim == 1 else audio_data.shape[1]
            elif self.bit_depth == 32:
                # 32-bit float
                audio_int = audio_data.astype(np.float32)
                num_channels = 1 if audio_data.ndim == 1 else audio_data.shape[1]
            else:
                raise ValueError(f"Unsupported bit depth: {self.bit_depth}")
            
            # Ensure mono/stereo consistency
            if audio_data.ndim == 1:
                audio_int = audio_int.reshape(-1, 1)
                num_channels = 1
            
            # Write WAV file
            with wave.open(str(output_path), 'wb') as wav_file:
                wav_file.setnchannels(num_channels)
                wav_file.setsampwidth(self.bit_depth // 8)
                wav_file.setframerate(self.sample_rate)
                
                # Interleave if stereo
                if num_channels == 2:
                    audio_int = audio_int.T.flatten()
                
                wav_file.writeframes(audio_int.tobytes())
            
            return True
        
        except Exception as e:
            print(f"Error exporting WAV: {e}")
            return False
    
    def export_mono(self, audio_data: np.ndarray, 
                    output_path: Path) -> bool:
        """Export mono audio to WAV file.
        
        Args:
            audio_data: Mono audio samples
            output_path: Output file path
            
        Returns:
            True if export successful
        """
        # Ensure mono
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)
        
        return self.export(audio_data, output_path)
    
    def export_stereo(self, left_channel: np.ndarray, 
                      right_channel: np.ndarray,
                      output_path: Path) -> bool:
        """Export stereo audio to WAV file.
        
        Args:
            left_channel: Left channel audio
            right_channel: Right channel audio
            output_path: Output file path
            
        Returns:
            True if export successful
        """
        stereo_data = np.column_stack([left_channel, right_channel])
        return self.export(stereo_data, output_path)
