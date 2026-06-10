"""JustBeat-DAW - 8-bit Digital Audio Workstation

A professional 8-bit music production workstation based on Clean Architecture principles.
"""

__version__ = "0.1.0"
__author__ = "JustBeat-DAW Team"

from src.domain.entities import Project, Track, Pattern, Note

__all__ = [
    "Project",
    "Track",
    "Pattern",
    "Note",
]
