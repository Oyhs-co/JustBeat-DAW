"""AutomationTrack - Manages automation curves for a track."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional
import uuid

from src.domain.entities.automation.automation_curve import AutomationCurve


class AutomationMode(Enum):
    """Automation recording mode."""
    READ = "read"  # Automation is played back
    WRITE = "write"  # New automation is recorded
    TOUCH = "touch"  # Record only when user touches control
    LATCH = "latch"  # Record from first touch until stop
    OFF = "off"  # No automation


# Standard parameter names for automation
class AutomationParameter:
    """Standard parameter names that can be automated."""
    
    # Track-level parameters
    VOLUME = "volume"
    PAN = "pan"
    MUTE = "mute"
    SOLO = "solo"
    
    # Synth parameters
    OSCILLATOR_TYPE = "oscillator_type"
    OSCILLATOR_DETUNE = "oscillator_detune"
    OSCILLATOR_OCTAVE = "oscillator_octave"
    FILTER_CUTOFF = "filter_cutoff"
    FILTER_RESONANCE = "filter_resonance"
    FILTER_TYPE = "filter_type"
    AMP_ATTACK = "amp_attack"
    AMP_DECAY = "amp_decay"
    AMP_SUSTAIN = "amp_sustain"
    AMP_RELEASE = "amp_release"
    
    # Effect parameters
    EFFECT_BYPASS = "effect_bypass"
    EFFECT_MIX = "effect_mix"
    
    # All standard parameters
    ALL = [
        VOLUME, PAN, MUTE, SOLO,
        OSCILLATOR_TYPE, OSCILLATOR_DETUNE, OSCILLATOR_OCTAVE,
        FILTER_CUTOFF, FILTER_RESONANCE, FILTER_TYPE,
        AMP_ATTACK, AMP_DECAY, AMP_SUSTAIN, AMP_RELEASE,
        EFFECT_BYPASS, EFFECT_MIX,
    ]


# Default colors for parameters
PARAMETER_COLORS = {
    AutomationParameter.VOLUME: "#00FF00",      # Green
    AutomationParameter.PAN: "#00FFFF",          # Cyan
    AutomationParameter.FILTER_CUTOFF: "#FF00FF", # Magenta
    AutomationParameter.FILTER_RESONANCE: "#FF0080",
    AutomationParameter.AMP_ATTACK: "#FF8000",   # Orange
    AutomationParameter.AMP_DECAY: "#FF4000",    # Red-Orange
    AutomationParameter.AMP_SUSTAIN: "#FFFF00",  # Yellow
    AutomationParameter.AMP_RELEASE: "#80FF00",   # Yellow-Green
    AutomationParameter.EFFECT_MIX: "#8000FF",   # Purple
}


@dataclass
class AutomationTrack:
    """Manages automation for a specific track.
    
    This class contains multiple automation curves, one for each
    parameter that can be automated on the track.
    
    Attributes:
        id: Unique identifier
        track_id: ID of the track this automation belongs to
        curves: Dictionary mapping parameter names to automation curves
        mode: Current automation mode (read/write/touch/latch/off)
        color: Default color for new curves
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    track_id: str = ""
    curves: Dict[str, AutomationCurve] = field(default_factory=dict)
    mode: AutomationMode = AutomationMode.READ
    color: str = "#00FF00"
    
    def __post_init__(self):
        """Initialize default curves for common parameters."""
        # Create default curves for track-level parameters
        for param in [AutomationParameter.VOLUME, AutomationParameter.PAN]:
            if param not in self.curves:
                self.curves[param] = AutomationCurve(
                    parameter_name=param,
                    color=PARAMETER_COLORS.get(param, "#00FF00")
                )
    
    def get_curve(self, parameter_name: str) -> Optional[AutomationCurve]:
        """Get the automation curve for a parameter.
        
        Args:
            parameter_name: Name of the parameter
            
        Returns:
            The automation curve, or None if not exists
        """
        return self.curves.get(parameter_name)
    
    def get_or_create_curve(
        self, parameter_name: str, color: Optional[str] = None
    ) -> AutomationCurve:
        """Get or create an automation curve for a parameter.
        
        Args:
            parameter_name: Name of the parameter
            color: Optional color for the curve
            
        Returns:
            The automation curve
        """
        if parameter_name not in self.curves:
            self.curves[parameter_name] = AutomationCurve(
                parameter_name=parameter_name,
                color=color or PARAMETER_COLORS.get(parameter_name, "#00FF00")
            )
        return self.curves[parameter_name]
    
    def get_value_at(self, parameter_name: str, time: float) -> Optional[float]:
        """Get the value of a parameter at a specific time.
        
        Args:
            parameter_name: Name of the parameter
            time: Time position to get value for
            
        Returns:
            The interpolated value, or None if no curve exists
        """
        curve = self.curves.get(parameter_name)
        if curve is None:
            return None
        return curve.get_value_at(time)
    
    def add_point(
        self, parameter_name: str, time: float, value: float
    ) -> None:
        """Add a point to a parameter's automation curve.
        
        Args:
            parameter_name: Name of the parameter
            time: Time position of the point
            value: Value of the point (0.0 to 1.0)
        """
        from src.domain.entities.automation.automation_point import AutomationPoint
        
        curve = self.get_or_create_curve(parameter_name)
        point = AutomationPoint(time=time, value=value)
        curve.add_point(point)
    
    def remove_curve(self, parameter_name: str) -> bool:
        """Remove an automation curve.
        
        Args:
            parameter_name: Name of the parameter
            
        Returns:
            True if curve was removed, False if it didn't exist
        """
        if parameter_name in self.curves:
            del self.curves[parameter_name]
            return True
        return False
    
    def clear_all(self) -> None:
        """Clear all automation curves."""
        self.curves.clear()
    
    def set_mode(self, mode: AutomationMode) -> None:
        """Set the automation mode.
        
        Args:
            mode: The new automation mode
        """
        self.mode = mode
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "track_id": self.track_id,
            "curves": {
                name: curve.to_dict() 
                for name, curve in self.curves.items()
            },
            "mode": self.mode.value,
            "color": self.color,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AutomationTrack":
        """Create automation track from dictionary."""
        curves = {}
        curves_data = data.get("curves", {})
        for name, curve_data in curves_data.items():
            curves[name] = AutomationCurve.from_dict(curve_data)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            track_id=data.get("track_id", ""),
            curves=curves,
            mode=AutomationMode(data.get("mode", "read")),
            color=data.get("color", "#00FF00"),
        )
