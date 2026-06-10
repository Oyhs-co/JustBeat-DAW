"""Handlers - Handlers de aplicación para JustBeat-DAW.

Este paquete contiene los handlers que manejan la lógica de negocio
siguiendo el patrón de inyección de dependencias.
"""

from src.application.handlers.project_handler import ProjectHandler
from src.application.handlers.transport_handler import TransportHandler
from src.application.handlers.track_handler import TrackHandler
from src.application.handlers.note_handler import NoteHandler


__all__ = [
    "ProjectHandler",
    "TransportHandler",
    "TrackHandler",
    "NoteHandler",
]
