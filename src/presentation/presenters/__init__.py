"""Presenters - Presentadores para JustBeat-DAW.

Este paquete contiene los presentadores que implementan el patrón MVP
(Model-View-Presenter) para separar la lógica de presentación de la UI.
"""

from src.presentation.presenters.base_presenter import (
    BasePresenter,
    TransportPresenter,
    TrackListPresenter,
    SequencerPresenter,
    PianoRollPresenter
)


__all__ = [
    "BasePresenter",
    "TransportPresenter",
    "TrackListPresenter",
    "SequencerPresenter",
    "PianoRollPresenter",
]
