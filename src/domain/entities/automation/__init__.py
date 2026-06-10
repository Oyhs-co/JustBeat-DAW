"""Automation entities for JustBeat-DAW.

This module provides classes for managing automation curves:
- AutomationPoint: A single point on an automation curve
- AutomationCurve: A curve containing multiple points
- AutomationTrack: A track dedicated to automation data
"""

from src.domain.entities.automation.automation_point import AutomationPoint
from src.domain.entities.automation.automation_curve import AutomationCurve
from src.domain.entities.automation.automation_track import AutomationTrack

__all__ = [
    "AutomationPoint",
    "AutomationCurve", 
    "AutomationTrack",
]
