"""Oscillators module - 8-bit oscillator implementations."""

import numpy as np
from typing import Optional


class BaseOscillator:
    """Base class for all oscillators."""
    
    def __init__(self, sample_rate: int = 44100):
        """Initialize the oscillator.
        
        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.frequency = 440.0
        self.phase = 0.0
    
    def set_frequency(self, freq: float) -> None:
        """Set oscillator frequency.
        
        Args:
            freq: Frequency in Hz
        """
        self.frequency = freq
    
    def set_sample_rate(self, sample_rate: int) -> None:
        """Set sample rate.
        
        Args:
            sample_rate: Sample rate in Hz
        """
        self.sample_rate = sample_rate
    
    def increment_phase(self, num_samples: int) -> None:
        """Increment the phase based on frequency.
        
        Args:
            num_samples: Number of samples to process
        """
        phase_increment = (self.frequency * 2 * np.pi) / self.sample_rate
        self.phase += phase_increment * num_samples
        self.phase = self.phase % (2 * np.pi)
    
    def reset(self) -> None:
        """Reset oscillator phase to zero."""
        self.phase = 0.0


class SquareOscillator(BaseOscillator):
    """Square wave oscillator for 8-bit sound generation."""
    
    def generate(self, num_samples: int) -> np.ndarray:
        """Generate square wave samples.
        
        Args:
            num_samples: Number of samples to generate
            
        Returns:
            Array of samples
        """
        # Calculate phase increment
        phase_increment = (self.frequency * 2 * np.pi) / self.sample_rate
        
        # Generate phase values
        phases = np.linspace(
            self.phase, 
            self.phase + phase_increment * num_samples, 
            num_samples
        )
        
        # Square wave: 1 if sin(phase) >= 0, else -1
        samples = np.where(np.sin(phases) >= 0, 1.0, -1.0)
        
        # Update phase
        self.phase = (self.phase + phase_increment * num_samples) % (2 * np.pi)
        
        return samples


class TriangleOscillator(BaseOscillator):
    """Triangle wave oscillator."""
    
    def generate(self, num_samples: int) -> np.ndarray:
        """Generate triangle wave samples.
        
        Args:
            num_samples: Number of samples to generate
            
        Returns:
            Array of samples
        """
        # Calculate phase increment
        phase_increment = (self.frequency * 2 * np.pi) / self.sample_rate
        
        # Generate phase values
        phases = np.linspace(
            self.phase, 
            self.phase + phase_increment * num_samples, 
            num_samples
        )
        
        # Triangle wave: 2*asin(sin(x))/pi
        samples = (2 / np.pi) * np.arcsin(np.sin(phases))
        
        # Update phase
        self.phase = (self.phase + phase_increment * num_samples) % (2 * np.pi)
        
        return samples


class NoiseOscillator(BaseOscillator):
    """White noise oscillator for percussion and effects."""
    
    def __init__(self, sample_rate: int = 44100):
        """Initialize the noise oscillator.
        
        Args:
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(sample_rate)
        self._last_state = 0.0
    
    def generate(self, num_samples: int) -> np.ndarray:
        """Generate white noise samples.
        
        Args:
            num_samples: Number of samples to generate
            
        Returns:
            Array of random samples
        """
        # Generate random samples
        samples = np.random.uniform(-1.0, 1.0, num_samples)
        return samples


class PulseWidthOscillator(BaseOscillator):
    """Pulse width modulated square wave."""
    
    def __init__(self, sample_rate: int = 44100, duty_cycle: float = 0.5):
        """Initialize the PWM oscillator.
        
        Args:
            sample_rate: Audio sample rate in Hz
            duty_cycle: Duty cycle (0.0 to 1.0)
        """
        super().__init__(sample_rate)
        self.duty_cycle = duty_cycle
    
    def set_duty_cycle(self, duty_cycle: float) -> None:
        """Set the duty cycle.
        
        Args:
            duty_cycle: Duty cycle (0.0 to 1.0)
        """
        self.duty_cycle = max(0.0, min(1.0, duty_cycle))
    
    def generate(self, num_samples: int) -> np.ndarray:
        """Generate PWM square wave samples.
        
        Args:
            num_samples: Number of samples to generate
            
        Returns:
            Array of samples
        """
        phase_increment = (self.frequency * 2 * np.pi) / self.sample_rate
        
        phases = np.linspace(
            self.phase, 
            self.phase + phase_increment * num_samples, 
            num_samples
        )
        
        # PWM: compare to duty cycle
        normalized_phase = (phases % (2 * np.pi)) / (2 * np.pi)
        samples = np.where(normalized_phase < self.duty_cycle, 1.0, -1.0)
        
        self.phase = (self.phase + phase_increment * num_samples) % (2 * np.pi)
        
        return samples


class SawtoothOscillator(BaseOscillator):
    """Sawtooth wave oscillator."""
    
    def generate(self, num_samples: int) -> np.ndarray:
        """Generate sawtooth wave samples.
        
        Args:
            num_samples: Number of samples to generate
            
        Returns:
            Array of samples
        """
        phase_increment = (self.frequency * 2 * np.pi) / self.sample_rate
        
        phases = np.linspace(
            self.phase, 
            self.phase + phase_increment * num_samples, 
            num_samples
        )
        
        # Sawtooth: 2*(phase/2pi) - 1
        normalized_phase = (phases % (2 * np.pi)) / (2 * np.pi)
        samples = 2.0 * normalized_phase - 1.0
        
        self.phase = (self.phase + phase_increment * num_samples) % (2 * np.pi)
        
        return samples


class SineOscillator(BaseOscillator):
    """Sine wave oscillator."""
    
    def generate(self, num_samples: int) -> np.ndarray:
        """Generate sine wave samples.
        
        Args:
            num_samples: Number of samples to generate
            
        Returns:
            Array of samples
        """
        phase_increment = (self.frequency * 2 * np.pi) / self.sample_rate
        
        phases = np.linspace(
            self.phase, 
            self.phase + phase_increment * num_samples, 
            num_samples
        )
        
        # Sine wave
        samples = np.sin(phases)
        
        self.phase = (self.phase + phase_increment * num_samples) % (2 * np.pi)
        
        return samples


class OscillatorFactory:
    """Factory for creating oscillators."""
    
    _oscillator_types = {
        "square": SquareOscillator,
        "triangle": TriangleOscillator,
        "noise": NoiseOscillator,
        "pwm": PulseWidthOscillator,
        "sawtooth": SawtoothOscillator,
        "sine": SineOscillator,
    }
    
    @classmethod
    def create(cls, oscillator_type: str, 
               sample_rate: int = 44100, **kwargs) -> BaseOscillator:
        """Create an oscillator of the specified type.
        
        Args:
            oscillator_type: Type of oscillator ('square', 'triangle', 'noise', 'pwm')
            sample_rate: Audio sample rate
            **kwargs: Additional parameters for the oscillator
            
        Returns:
            Oscillator instance
            
        Raises:
            ValueError: If oscillator type is unknown
        """
        if oscillator_type not in cls._oscillator_types:
            raise ValueError(
                f"Unknown oscillator type: {oscillator_type}. "
                f"Available types: {list(cls._oscillator_types.keys())}"
            )
        
        oscillator_class = cls._oscillator_types[oscillator_type]
        return oscillator_class(sample_rate=sample_rate, **kwargs)
    
    @classmethod
    def get_available_types(cls) -> list[str]:
        """Get list of available oscillator types.
        
        Returns:
            List of oscillator type names
        """
        return list(cls._oscillator_types.keys())
