"""Workspace widget - Main workspace container that integrates all widgets."""

import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QLabel
)

logger = logging.getLogger(__name__)
from PySide6.QtCore import Qt, Signal

from src.presentation.widgets.sequencer import StepSequencerWidget
from src.presentation.widgets.synth_panel import SynthesizerPanel
from src.presentation.widgets.mixer import MixerWidget
from src.presentation.widgets.piano_roll import PianoRollWidget


class WorkspaceWidget(QWidget):
    """Main workspace widget that integrates all editor widgets."""
    
    # Signals
    bpm_changed = Signal(int)
    step_changed = Signal(int)
    note_changed = Signal(int, int)  # step, pitch
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(2)
        main_layout.setContentsMargins(2, 2, 2, 2)
        
        # Create horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Step Sequencer + Synth Panel
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel: Piano Roll + Mixer
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set initial sizes
        splitter.setSizes([600, 400])
        
        main_layout.addWidget(splitter, 1)
    
    def _create_left_panel(self) -> QWidget:
        """Create the left panel with sequencer and synth panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Step Sequencer
        self._sequencer = StepSequencerWidget(num_tracks=4, steps=16)
        layout.addWidget(self._sequencer, 1)
        
        # Synthesizer Panel
        self._synth_panel = SynthesizerPanel()
        layout.addWidget(self._synth_panel)
        
        return widget
    
    def _create_right_panel(self) -> QWidget:
        """Create the right panel with piano roll and mixer."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Piano Roll (takes most space)
        self._piano_roll = PianoRollWidget(steps=16, octaves=4)
        layout.addWidget(self._piano_roll, 3)
        
        # Mixer
        self._mixer = MixerWidget(num_channels=4)
        layout.addWidget(self._mixer)
        
        return widget
    
    def _connect_signals(self):
        """Connect signals between widgets."""
        # Connect sequencer to piano roll
        self._sequencer.step_clicked.connect(self._on_step_clicked)
        
        # Connect synth panel to other components
        self._synth_panel.adsr_changed.connect(self._on_adsr_changed)
        
        # Connect mixer to project service
        for i in range(self._mixer.get_num_channels()):
            channel = self._mixer.get_channel(i)
            if channel:
                channel.volume_changed.connect(
                    lambda v, idx=i: self._on_volume_changed(idx, v)
                )
                channel.pan_changed.connect(
                    lambda p, idx=i: self._on_pan_changed(idx, p)
                )
                channel.mute_changed.connect(
                    lambda m, idx=i: self._on_mute_changed(idx, m)
                )
                channel.solo_changed.connect(
                    lambda s, idx=i: self._on_solo_changed(idx, s)
                )
    
    def _on_step_clicked(self, track: int, step: int):
        """Handle step click from sequencer.
        
        Args:
            track: Track index
            step: Step index
        """
        self.step_changed.emit(step)
    
    def _on_adsr_changed(self, attack: float, decay: float, 
                        sustain: float, release: float):
        """Handle ADSR change from synth panel.
        
        Args:
            attack: Attack time
            decay: Decay time
            sustain: Sustain level
            release: Release time
        """
        # Update project/track settings
        print(f"ADSR: A={attack}, D={decay}, S={sustain}, R={release}")
    
    def _on_volume_changed(self, channel: int, volume: float):
        """Handle volume change from mixer.
        
        Args:
            channel: Channel index
            volume: Volume (0.0 to 1.0)
        """
        pass
    
    def _on_pan_changed(self, channel: int, pan: float):
        pass
    
    def _on_mute_changed(self, channel: int, muted: bool):
        pass
    
    def _on_solo_changed(self, channel: int, solo: bool):
        pass
    
    # Public methods for external access
    
    def get_sequencer(self) -> StepSequencerWidget:
        """Get the step sequencer widget.
        
        Returns:
            StepSequencerWidget instance
        """
        return self._sequencer
    
    def get_synth_panel(self) -> SynthesizerPanel:
        """Get the synthesizer panel widget.
        
        Returns:
            SynthesizerPanel instance
        """
        return self._synth_panel
    
    def get_mixer(self) -> MixerWidget:
        """Get the mixer widget.
        
        Returns:
            MixerWidget instance
        """
        return self._mixer
    
    def get_piano_roll(self) -> PianoRollWidget:
        """Get the piano roll widget.
        
        Returns:
            PianoRollWidget instance
        """
        return self._piano_roll
    
    def set_bpm(self, bpm: int):
        """Set the BPM for all widgets.
        
        Args:
            bpm: BPM value
        """
        self._sequencer.set_bpm(bpm)
    
    def play(self):
        """Start playback visualization."""
        self._sequencer.set_playing(True)
    
    def stop(self):
        """Stop playback visualization."""
        self._sequencer.set_playing(False)
        self._sequencer.reset_position()
    
    def set_current_step(self, step: int):
        """Set the current playback step.
        
        Args:
            step: Step index
        """
        self._sequencer.set_current_step(step)
