"""AutomationPoint - Represents a single point on an automation curve."""

from dataclasses import dataclass
from enum import Enum


class CurveShape(Enum):
    """Shape of the curve segment leading to this point."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    BEZIER = "bezier"
    HOLD = "hold"


@dataclass
class AutomationPoint:
    """A single point on an automation curve.
    
    Attributes:
        time: Time position in beats (or samples, depending on context)
        value: The parameter value (0.0 to 1.0 typically)
        curve_out: Shape of curve leaving this point
        curve_in: Shape of curve entering this point (for bezier)
        bezier_handle_out: Control point offset for bezier out (x, y)
        bezier_handle_in: Control point offset for bezier in (x, y)
    """
    
    time: float
    value: float
    curve_out: CurveShape = CurveShape.LINEAR
    curve_in: CurveShape = CurveShape.LINEAR
    bezier_handle_out: tuple[float, float] = (0.0, 0.0)
    bezier_handle_in: tuple[float, float] = (0.0, 0.0)
    
    def __post_init__(self):
        """Validate point values."""
        if not 0.0 <= self.value <= 1.0:
            raise ValueError("Value must be between 0.0 and 1.0")
        if self.time < 0:
            raise ValueError("Time cannot be negative")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "time": self.time,
            "value": self.value,
            "curve_out": self.curve_out.value,
            "curve_in": self.curve_in.value,
            "bezier_handle_out": self.bezier_handle_out,
            "bezier_handle_in": self.bezier_handle_in,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AutomationPoint":
        """Create point from dictionary."""
        return cls(
            time=data["time"],
            value=data["value"],
            curve_out=CurveShape(data.get("curve_out", "linear")),
            curve_in=CurveShape(data.get("curve_in", "linear")),
            bezier_handle_in=tuple(data.get("bezier_handle_in", (0.0, 0.0))),
            bezier_handle_out=tuple(data.get("bezier_handle_out", (0.0, 0.0))),
        )
