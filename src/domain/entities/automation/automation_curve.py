"""AutomationCurve - Represents a complete automation curve with interpolation."""

from dataclasses import dataclass, field
from typing import List, Optional
import uuid

from src.domain.entities.automation.automation_point import AutomationPoint, CurveShape


@dataclass
class AutomationCurve:
    """An automation curve containing multiple points.
    
    This class manages a collection of automation points and provides
    interpolation methods to get the value at any time position.
    
    Attributes:
        id: Unique identifier for this curve
        parameter_name: Name of the parameter being automated
                        (e.g., "volume", "pan", "filter_cutoff")
        points: List of automation points sorted by time
        color: Color for UI display
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parameter_name: str = ""
    points: List[AutomationPoint] = field(default_factory=list)
    color: str = "#00FF00"  # Default green
    
    def add_point(self, point: AutomationPoint) -> None:
        """Add a point to the curve.
        
        Points are automatically sorted by time after insertion.
        
        Args:
            point: The automation point to add
        """
        self.points.append(point)
        self.points.sort(key=lambda p: p.time)
    
    def remove_point(self, index: int) -> None:
        """Remove a point by index.
        
        Args:
            index: Index of the point to remove
        """
        if 0 <= index < len(self.points):
            self.points.pop(index)
    
    def get_point_at(self, time: float) -> Optional[AutomationPoint]:
        """Get the point at a specific time, or None if not found.
        
        Args:
            time: Time position to search for
            
        Returns:
            The point at the given time, or None
        """
        for point in self.points:
            if abs(point.time - time) < 0.001:  # Floating point tolerance
                return point
        return None
    
    def get_value_at(self, time: float) -> float:
        """Get the interpolated value at a specific time.
        
        Uses the curve shapes defined in the points to interpolate
        between surrounding points.
        
        Args:
            time: Time position to get value for
            
        Returns:
            Interpolated value (0.0 to 1.0)
        """
        if not self.points:
            return 0.5  # Default neutral value
        
        # If before first point, return first point value
        if time <= self.points[0].time:
            return self.points[0].value
        
        # If after last point, return last point value
        if time >= self.points[-1].time:
            return self.points[-1].value
        
        # Find surrounding points and interpolate
        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            
            if p1.time <= time <= p2.time:
                return self._interpolate(p1, p2, time)
        
        return 0.5
    
    def _interpolate(
        self, p1: AutomationPoint, p2: AutomationPoint, time: float
    ) -> float:
        """Interpolate between two points.
        
        Args:
            p1: First point
            p2: Second point
            time: Time position to interpolate at
            
        Returns:
            Interpolated value
        """
        # Calculate normalized position (0.0 to 1.0)
        duration = p2.time - p1.time
        if duration == 0:
            return p1.value
        
        t = (time - p1.time) / duration
        
        # Apply curve shape
        shape = p1.curve_out
        if shape == CurveShape.LINEAR:
            return p1.value + (p2.value - p1.value) * t
        elif shape == CurveShape.EXPONENTIAL:
            # Exponential curve (ease in)
            t = t * t
            return p1.value + (p2.value - p1.value) * t
        elif shape == CurveShape.LOGARITHMIC:
            # Logarithmic curve (ease out)
            t = 1 - (1 - t) * (1 - t)
            return p1.value + (p2.value - p1.value) * t
        elif shape == CurveShape.BEZIER:
            # Simple bezier approximation
            t = t * t * (3 - 2 * t)  # Smoothstep
            return p1.value + (p2.value - p1.value) * t
        else:  # HOLD
            return p1.value
    
    def clear(self) -> None:
        """Remove all points from the curve."""
        self.points.clear()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "parameter_name": self.parameter_name,
            "points": [p.to_dict() for p in self.points],
            "color": self.color,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AutomationCurve":
        """Create curve from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            parameter_name=data.get("parameter_name", ""),
            points=[
                AutomationPoint.from_dict(p) for p in data.get("points", [])
            ],
            color=data.get("color", "#00FF00"),
        )
