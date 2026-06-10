"""Presentation Models - Modelos de presentación para JustBeat-DAW.

Este paquete contiene los modelos de presentación que proporcionan una capa
de abstracción entre la UI y los handlers de la capa de aplicación.
"""

from src.presentation.models.presentation_model import (
    PresentationModel,
    get_presentation_model,
    initialize_presentation_model
)


__all__ = [
    "PresentationModel",
    "get_presentation_model",
    "initialize_presentation_model",
]
