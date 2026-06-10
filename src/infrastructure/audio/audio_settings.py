"""Audio Settings - Configuration for audio engine.

This module provides:
- AudioSettings: Audio configuration
- AudioConfigDialog: UI for audio settings
- LatencyCalculator: Calculate and display latency
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class SampleRate(Enum):
    """Standard sample rates."""
    RATE_22050 = 22050
    RATE_44100 = 44100
    RATE_48000 = 48000
    RATE_96000 = 96000


class BufferSize(Enum):
    """Standard buffer sizes."""
    BUF_64 = 64
    BUF_128 = 128
    BUF_256 = 256
    BUF_512 = 512
    BUF_1024 = 1024
    BUF_2048 = 2048


class AudioBackend(Enum):
    """Audio backend types."""
    JACK = "jack"
    ALSA = "alsa"
    WASAPI = "wasapi"
    ASIO = "asio"
    COREAUDIO = "coreaudio"


@dataclass
class AudioDevice:
    """Audio device information."""
    id: int
    name: str
    is_input: bool
    is_output: bool
    sample_rates: List[int] = field(default_factory=list)
    channels: int = 2


@dataclass
class AudioSettings:
    """Audio configuration settings."""
    sample_rate: int = 44100
    buffer_size: int = 256
    input_device: Optional[str] = None
    output_device: Optional[str] = None
    backend: str = "auto"
    bit_depth: int = 32  # 32-bit float internal
    channels: int = 2
    auto_start: bool = True
    prime_buffers: bool = True
    double_buffer: bool = False
    
    # Performance settings
    use_double_precision: bool = False
    enable_mixing: bool = True
    enable_precise_timing: bool = True
    
    # Monitoring
    enable_metering: bool = True
    meter_update_rate: int = 30  # Hz
    
    def get_latency_ms(self) -> float:
        """Calculate latency in milliseconds.
        
        Returns:
            Latency in milliseconds
        """
        return (self.buffer_size / self.sample_rate) * 1000 * 2  # input + output
    
    def get_latency_samples(self) -> int:
        """Get latency in samples.
        
        Returns:
            Latency in samples
        """
        return self.buffer_size * 2  # input + output
    
    def get_recommended_buffer_size(self, target_latency_ms: float) -> int:
        """Get recommended buffer size for target latency.
        
        Args:
            target_latency_ms: Target latency in milliseconds
            
        Returns:
            Recommended buffer size
        """
        # Round trip = 2x buffer size
        samples = (target_latency_ms / 1000) * self.sample_rate / 2
        return max(64, min(2048, int(samples) & -64))  # Round to nearest power of 2


@dataclass
class AudioDiagnostics:
    """Audio system diagnostics."""
    available_sample_rates: List[int] = field(default_factory=list)
    available_buffer_sizes: List[int] = field(default_factory=list)
    input_devices: List[AudioDevice] = field(default_factory=list)
    output_devices: List[AudioDevice] = field(default_factory=list)
    current_cpu_usage: float = 0.0
    xruns: int = 0
    sample_rate_actual: int = 0
    buffer_underruns: int = 0
    
    def is_healthy(self, max_latency_ms: float = 20.0) -> bool:
        """Check if audio system is healthy.
        
        Args:
            max_latency_ms: Maximum acceptable latency
            
        Returns:
            True if system is healthy
        """
        if self.xruns > 10:
            return False
        if self.buffer_underruns > 10:
            return False
        return True


class LatencyCalculator:
    """Calculate audio latency for different configurations."""
    
    @staticmethod
    def calculate_latency(
        sample_rate: int,
        buffer_size: int,
        include_in_out: bool = True
    ) -> float:
        """Calculate latency in milliseconds.
        
        Args:
            sample_rate: Sample rate in Hz
            buffer_size: Buffer size in samples
            include_in_out: Include input and output
            
        Returns:
            Latency in milliseconds
        """
        factor = 2 if include_in_out else 1
        return (buffer_size / sample_rate) * 1000 * factor
    
    @staticmethod
    def get_latency_description(latency_ms: float) -> str:
        """Get human-readable latency description.
        
        Args:
            latency_ms: Latency in milliseconds
            
        Returns:
            Description string
        """
        if latency_ms < 5:
            return "Very Low (Professional)"
        elif latency_ms < 10:
            return "Low (Studio)"
        elif latency_ms < 20:
            return "Medium (Home Studio)"
        elif latency_ms < 50:
            return "High (Acceptable)"
        else:
            return "Very High (Not Recommended)"
    
    @staticmethod
    def suggest_settings(target_latency_ms: float) -> AudioSettings:
        """Suggest optimal audio settings for target latency.
        
        Args:
            target_latency_ms: Target latency in milliseconds
            
        Returns:
            Suggested audio settings
        """
        # Try different sample rates
        for rate in [96000, 48000, 44100]:
            for buffer in [64, 128, 256, 512, 1024]:
                latency = LatencyCalculator.calculate_latency(rate, buffer)
                if latency <= target_latency_ms:
                    return AudioSettings(
                        sample_rate=rate,
                        buffer_size=buffer,
                        enable_precise_timing=(buffer <= 256)
                    )
        
        # Fallback to defaults
        return AudioSettings()
    
    @staticmethod
    def get_buffer_size_options(sample_rate: int) -> List[int]:
        """Get available buffer sizes for a sample rate.
        
        Args:
            sample_rate: Sample rate in Hz
            
        Returns:
            List of buffer sizes
        """
        # All standard buffer sizes work with any sample rate
        return [64, 128, 256, 512, 1024, 2048]
