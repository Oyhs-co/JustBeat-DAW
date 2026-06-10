"""Export Dialog - UI for export options."""

from typing import Optional
import logging

from PySide6.QtCore import Qt, QThread, Signal


logger = logging.getLogger(__name__)
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QComboBox, QSpinBox, QCheckBox,
    QPushButton, QProgressBar, QFileDialog, QLineEdit,
    QRadioButton, QButtonGroup, QDialogButtonBox, QWidget
)

from src.presentation.controllers.export_controller import (
    ExportController, ExportSettings, ExportFormat, ExportQuality,
    ExportProgress
)

# Theme Integration
from src.presentation.styles.theme_integration import ThemeMixin


class ExportThread(QThread):
    """Thread for export operations."""
    
    progress = Signal(object)  # ExportProgress
    
    def __init__(
        self,
        controller: ExportController,
        audio_data,
        output_path: str,
        settings: ExportSettings,
        is_stems: bool = False,
        track_audios=None,
        track_names=None
    ):
        super().__init__()
        self._controller = controller
        self._audio_data = audio_data
        self._output_path = output_path
        self._settings = settings
        self._is_stems = is_stems
        self._track_audios = track_audios or {}
        self._track_names = track_names or {}
        self._success = False
    
    def run(self):
        """Run export in background thread."""
        try:
            if self._is_stems:
                self._success = self._controller.export_stems(
                    self._track_audios,
                    self._output_path,
                    self._settings,
                    self._track_names,
                    lambda p: self.progress.emit(p)
                )
            else:
                self._success = self._controller.export_audio(
                    self._audio_data,
                    self._output_path,
                    self._settings,
                    lambda p: self.progress.emit(p)
                )
        except Exception as e:
            self.progress.emit(ExportProgress(error=str(e)))
    
    @property
    def success(self) -> bool:
        """Get export success status."""
        return self._success


class ExportDialog(ThemeMixin, QDialog):
    """Dialog for configuring and running export."""
    
    def __init__(
        self,
        controller: ExportController,
        parent: Optional[QWidget] = None
    ):
        ThemeMixin.__init__(self)
        super().__init__(parent)
        
        self._controller = controller
        self._export_thread: Optional[ExportThread] = None
        self._is_stems = False
        
        self.setWindowTitle("Export Audio")
        self.setMinimumWidth(500)
        
        self._setup_ui()
        self.apply_theme()
    
    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        # Export type
        type_group = QGroupBox("Export Type")
        type_layout = QVBoxLayout()
        
        self._mixed_radio = QRadioButton("Mixed Audio (Single File)")
        self._mixed_radio.setChecked(True)
        self._mixed_radio.toggled.connect(self._on_type_changed)
        type_layout.addWidget(self._mixed_radio)
        
        self._stems_radio = QRadioButton("Individual Tracks (Stems)")
        self._stems_radio.toggled.connect(self._on_type_changed)
        type_layout.addWidget(self._stems_radio)
        
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Format settings
        format_group = QGroupBox("Format Settings")
        format_layout = QVBoxLayout()
        
        # Format
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Format:"))
        self._format_combo = QComboBox()
        self._format_combo.addItems([f.value for f in ExportFormat])
        self._format_combo.setCurrentText(ExportFormat.WAV.value)
        format_row.addWidget(self._format_combo)
        format_row.addStretch()
        format_layout.addLayout(format_row)
        
        # Quality
        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel("Quality:"))
        self._quality_combo = QComboBox()
        self._quality_combo.addItems([q.value for q in ExportQuality])
        self._quality_combo.setCurrentText(ExportQuality.HIGH.value)
        quality_row.addWidget(self._quality_combo)
        quality_row.addStretch()
        format_layout.addLayout(quality_row)
        
        # Sample rate
        sample_row = QHBoxLayout()
        sample_row.addWidget(QLabel("Sample Rate:"))
        self._sample_rate_combo = QComboBox()
        self._sample_rate_combo.addItems(["22050", "44100", "48000", "96000"])
        self._sample_rate_combo.setCurrentText("44100")
        sample_row.addWidget(self._sample_rate_combo)
        sample_row.addWidget(QLabel("Hz"))
        sample_row.addStretch()
        format_layout.addLayout(sample_row)
        
        # Bit depth
        bit_row = QHBoxLayout()
        bit_row.addWidget(QLabel("Bit Depth:"))
        self._bit_depth_combo = QComboBox()
        self._bit_depth_combo.addItems(["16", "24", "32"])
        self._bit_depth_combo.setCurrentText("16")
        bit_row.addWidget(self._bit_depth_combo)
        bit_row.addWidget(QLabel("bit"))
        bit_row.addStretch()
        format_layout.addLayout(bit_row)
        
        # Channels
        channels_row = QHBoxLayout()
        channels_row.addWidget(QLabel("Channels:"))
        self._channels_combo = QComboBox()
        self._channels_combo.addItems(["Mono", "Stereo"])
        self._channels_combo.setCurrentText("Stereo")
        channels_row.addWidget(self._channels_combo)
        channels_row.addStretch()
        format_layout.addLayout(channels_row)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        self._normalize_check = QCheckBox("Normalize audio")
        self._normalize_check.setChecked(True)
        options_layout.addWidget(self._normalize_check)
        
        fade_row = QHBoxLayout()
        fade_row.addWidget(QLabel("Fade out:"))
        self._fade_spin = QSpinBox()
        self._fade_spin.setRange(0, 10)
        self._fade_spin.setSuffix(" sec")
        fade_row.addWidget(self._fade_spin)
        fade_row.addStretch()
        options_layout.addLayout(fade_row)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Output
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()
        
        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("File:"))
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText("Select output file...")
        output_row.addWidget(self._output_edit)
        
        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.clicked.connect(self._on_browse)
        output_row.addWidget(self._browse_btn)
        
        output_layout.addLayout(output_row)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # Progress
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)
        
        self._status_label = QLabel("")
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_export)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _on_type_changed(self, checked: bool) -> None:
        """Handle export type change."""
        self._is_stems = self._stems_radio.isChecked()
    
    def _on_browse(self) -> None:
        """Handle browse button click."""
        if self._is_stems:
            # Select directory for stems
            directory = QFileDialog.getExistingDirectory(
                self,
                "Select Output Directory",
                "",
                QFileDialog.Option.ShowDirsOnly
            )
            if directory:
                self._output_edit.setText(directory)
        else:
            # Select file
            format_ext = self._format_combo.currentText()
            filename = f"export.{format_ext}"
            
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Save Audio File",
                filename,
                f"Audio Files (*.{format_ext});;All Files (*)"
            )
            
            if filepath:
                self._output_edit.setText(filepath)
    
    def _on_export(self) -> None:
        """Handle export button click."""
        output_path = self._output_edit.text()
        
        if not output_path:
            self._status_label.setText("Please select output location")
            self._status_label.setVisible(True)
            return
        
        # Get settings
        settings = ExportSettings(
            format=ExportFormat(self._format_combo.currentText()),
            quality=ExportQuality(self._quality_combo.currentText()),
            sample_rate=int(self._sample_rate_combo.currentText()),
            bit_depth=int(self._bit_depth_combo.currentText()),
            channels=2 if self._channels_combo.currentText() == "Stereo" else 1,
            normalize=self._normalize_check.isChecked(),
            fade_out=self._fade_spin.value(),
        )
        
        # Disable UI
        self._set_ui_enabled(False)
        
        # Start export thread
        self._progress_bar.setVisible(True)
        self._status_label.setVisible(True)
        self._progress_bar.setValue(0)
        self._status_label.setText("Exporting...")
        
        # Note: In real implementation, we'd get actual audio data
        # For now, this is a placeholder
        audio_data = None
        
        self._export_thread = ExportThread(
            self._controller,
            audio_data,
            output_path,
            settings,
            self._is_stems
        )
        
        self._export_thread.progress.connect(self._on_progress)
        self._export_thread.finished.connect(self._on_export_finished)
        self._export_thread.start()
    
    def _on_progress(self, progress: ExportProgress) -> None:
        """Handle export progress."""
        self._progress_bar.setValue(int(progress.progress * 100))
        self._status_label.setText(progress.status)
    
    def _on_export_finished(self) -> None:
        """Handle export completion."""
        self._set_ui_enabled(True)
        
        if self._export_thread.success:
            self._status_label.setText("Export completed successfully!")
            QDialog.accept(self)
        else:
            self._status_label.setText("Export failed. Check logs for details.")
    
    def _set_ui_enabled(self, enabled: bool) -> None:
        """Enable or disable UI elements."""
        self._mixed_radio.setEnabled(enabled)
        self._stems_radio.setEnabled(enabled)
        self._format_combo.setEnabled(enabled)
        self._quality_combo.setEnabled(enabled)
        self._sample_rate_combo.setEnabled(enabled)
        self._bit_depth_combo.setEnabled(enabled)
        self._channels_combo.setEnabled(enabled)
        self._normalize_check.setEnabled(enabled)
        self._fade_spin.setEnabled(enabled)
        self._output_edit.setEnabled(enabled)
        self._browse_btn.setEnabled(enabled)
