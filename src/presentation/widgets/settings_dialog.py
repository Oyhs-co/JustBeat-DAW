"""Project settings dialog widget."""

import logging

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QGroupBox, QPushButton, QDialogButtonBox,
    QTabWidget, QWidget, QCheckBox
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class ProjectSettingsDialog(QDialog):
    """Dialog for editing project settings."""
    
    def __init__(self, project=None, parent=None):
        """Initialize the settings dialog.
        
        Args:
            project: Project to edit (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._project = project
        
        self.setWindowTitle("Project Settings")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self._setup_ui()
        self._load_project_data()
    
    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        # Tab widget
        tabs = QTabWidget()
        
        # General tab
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, "General")
        
        # Audio tab
        audio_tab = self._create_audio_tab()
        tabs.addTab(audio_tab, "Audio")
        
        # MIDI tab
        midi_tab = self._create_midi_tab()
        tabs.addTab(midi_tab, "MIDI")
        
        layout.addWidget(tabs)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def accept(self) -> None:
        changed_settings = self._collect_changed_settings()
        logger.info(f"Settings dialog accepted, changed settings: {changed_settings}")
        super().accept()
    
    def _collect_changed_settings(self) -> dict:
        if not self._project:
            return {}
        changes = {}
        name = self._name_edit.text()
        if name != getattr(self._project, 'name', ''):
            changes["name"] = name
        bpm = self._bpm_spin.value()
        if bpm != getattr(self._project, 'bpm', 120):
            changes["bpm"] = bpm
        pat_len = int(self._pattern_length_combo.currentText())
        if pat_len != getattr(self._project, 'pattern_length', 16):
            changes["pattern_length"] = pat_len
        return changes
    
    def _create_general_tab(self) -> QWidget:
        """Create the general settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Project name
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Untitled Project")
        layout.addRow("Name:", self._name_edit)
        
        # Tempo (BPM)
        self._bpm_spin = QSpinBox()
        self._bpm_spin.setRange(20, 300)
        self._bpm_spin.setValue(120)
        self._bpm_spin.setSuffix(" BPM")
        layout.addRow("Tempo:", self._bpm_spin)
        
        # Pattern length
        self._pattern_length_combo = QComboBox()
        self._pattern_length_combo.addItems(["8", "16", "32", "64"])
        self._pattern_length_combo.setCurrentIndex(1)
        layout.addRow("Pattern:", self._pattern_length_combo)
        
        # Time Signature
        time_sig_layout = QHBoxLayout()
        
        self._beats_spin = QSpinBox()
        self._beats_spin.setRange(1, 16)
        self._beats_spin.setValue(4)
        time_sig_layout.addWidget(self._beats_spin)
        
        time_sig_layout.addWidget(QLabel("/"))
        
        self._beat_type_spin = QSpinBox()
        self._beat_type_spin.setRange(1, 16)
        self._beat_type_spin.setValue(4)
        time_sig_layout.addWidget(self._beat_type_spin)
        
        time_sig_layout.addStretch()
        layout.addRow("Time Signature:", time_sig_layout)
        
        # Master volume
        self._master_volume = QDoubleSpinBox()
        self._master_volume.setRange(0.0, 1.0)
        self._master_volume.setValue(0.8)
        self._master_volume.setSingleStep(0.05)
        self._master_volume.setDecimals(2)
        layout.addRow("Master Volume:", self._master_volume)
        
        return widget
    
    def _create_audio_tab(self) -> QWidget:
        """Create the audio settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Sample rate
        self._sample_rate = QComboBox()
        self._sample_rate.addItems(['22050', '44100', '48000', '96000'])
        self._sample_rate.setCurrentText('44100')
        layout.addRow("Sample Rate:", self._sample_rate)
        
        # Bit depth
        self._bit_depth = QComboBox()
        self._bit_depth.addItems(['16-bit', '24-bit', '32-bit float'])
        self._bit_depth.setCurrentText('16-bit')
        layout.addRow("Bit Depth:", self._bit_depth)
        
        # Buffer size
        self._buffer_size = QComboBox()
        self._buffer_size.addItems(['64', '128', '256', '512', '1024', '2048'])
        self._buffer_size.setCurrentText('256')
        layout.addRow("Buffer Size:", self._buffer_size)
        
        # Latency compensation
        self._latency_comp = QDoubleSpinBox()
        self._latency_comp.setRange(0.0, 100.0)
        self._latency_comp.setValue(0.0)
        self._latency_comp.setSuffix(" ms")
        layout.addRow("Latency:", self._latency_comp)
        
        # Audio driver
        self._audio_driver = QComboBox()
        self._audio_driver.addItems(['WASAPI', 'DirectSound', 'ASIO', 'WASAPI Loopback'])
        self._audio_driver.setCurrentText('WASAPI')
        layout.addRow("Audio Driver:", self._audio_driver)
        
        return widget
    
    def _create_midi_tab(self) -> QWidget:
        """Create the MIDI settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # MIDI input
        self._midi_input = QComboBox()
        self._midi_input.addItems(['None', 'MIDI Input 1', 'MIDI Input 2'])
        layout.addRow("MIDI Input:", self._midi_input)
        
        # MIDI output
        self._midi_output = QComboBox()
        self._midi_output.addItems(['None', 'MIDI Output 1', 'MIDI Output 2'])
        layout.addRow("MIDI Output:", self._midi_output)
        
        # MIDI channel
        self._midi_channel = QSpinBox()
        self._midi_channel.setRange(1, 16)
        self._midi_channel.setValue(1)
        layout.addRow("MIDI Channel:", self._midi_channel)
        
        # MIDI clock
        self._midi_clock = QCheckBox("Send MIDI Clock")
        layout.addRow("", self._midi_clock)
        
        # MIDI start/stop
        self._midi_start_stop = QCheckBox("Send Start/Stop")
        layout.addRow("", self._midi_start_stop)
        
        return widget
    
    def _load_project_data(self):
        """Load project data into the dialog."""
        if not self._project:
            return
        
        # Load general settings
        self._name_edit.setText(self._project.name)
        self._bpm_spin.setValue(self._project.bpm)
        
        # Set pattern length combo
        pattern_length = getattr(self._project, 'pattern_length', 16)
        index = self._pattern_length_combo.findText(str(pattern_length))
        if index >= 0:
            self._pattern_length_combo.setCurrentIndex(index)
    
    def get_project_name(self) -> str:
        """Get the project name.
        
        Returns:
            Project name
        """
        return self._name_edit.text()
    
    def get_bpm(self) -> int:
        """Get the BPM.
        
        Returns:
            BPM value
        """
        return self._bpm_spin.value()
    
    def get_pattern_length(self) -> int:
        """Get the pattern length.
        
        Returns:
            Pattern length value
        """
        return int(self._pattern_length_combo.currentText())
    
    def get_time_signature(self) -> tuple[int, int]:
        """Get the time signature.
        
        Returns:
            Tuple of (beats, beat_type)
        """
        return (self._beats_spin.value(), self._beat_type_spin.value())
    
    def get_sample_rate(self) -> int:
        """Get the sample rate.
        
        Returns:
            Sample rate in Hz
        """
        return int(self._sample_rate.currentText())
    
    def get_buffer_size(self) -> int:
        """Get the buffer size.
        
        Returns:
            Buffer size in samples
        """
        return int(self._buffer_size.currentText())


class PreferencesDialog(QDialog):
    """Dialog for application preferences."""
    
    def __init__(self, parent=None):
        """Initialize the preferences dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        # Tab widget
        tabs = QTabWidget()
        
        # Appearance tab
        appearance_tab = self._create_appearance_tab()
        tabs.addTab(appearance_tab, "Appearance")
        
        # Paths tab
        paths_tab = self._create_paths_tab()
        tabs.addTab(paths_tab, "Paths")
        
        # Plugins tab
        plugins_tab = self._create_plugins_tab()
        tabs.addTab(plugins_tab, "Plugins")
        
        layout.addWidget(tabs)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _create_appearance_tab(self) -> QWidget:
        """Create the appearance settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Theme
        self._theme = QComboBox()
        self._theme.addItems(['Dark', 'Light', 'System'])
        self._theme.setCurrentText('Dark')
        layout.addRow("Theme:", self._theme)
        
        # Font size
        self._font_size = QSpinBox()
        self._font_size.setRange(8, 20)
        self._font_size.setValue(11)
        layout.addRow("Font Size:", self._font_size)
        
        # Show tooltips
        self._show_tooltips = QCheckBox("Show tooltips")
        self._show_tooltips.setChecked(True)
        layout.addRow("", self._show_tooltips)
        
        return widget
    
    def _create_paths_tab(self) -> QWidget:
        """Create the paths settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Projects folder
        projects_layout = QHBoxLayout()
        projects_layout.addWidget(QLabel("Default: ./projects"))
        projects_layout.addStretch()
        layout.addRow("Projects Folder:", projects_layout)
        
        # Exports folder
        exports_layout = QHBoxLayout()
        exports_layout.addWidget(QLabel("Default: ./exports"))
        exports_layout.addStretch()
        layout.addRow("Exports Folder:", exports_layout)
        
        # Plugins folder
        plugins_layout = QHBoxLayout()
        plugins_layout.addWidget(QLabel("Default: ./plugins"))
        plugins_layout.addStretch()
        layout.addRow("Plugins Folder:", plugins_layout)
        
        return widget
    
    def _create_plugins_tab(self) -> QWidget:
        """Create the plugins settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel(
            "Plugins are loaded from the plugins folder. "
            "Restart the application to reload plugins."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        
        layout.addStretch()
        
        return widget
    
    def get_theme(self) -> str:
        """Get the selected theme.
        
        Returns:
            Theme name
        """
        return self._theme.currentText()
