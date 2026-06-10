"""About Dialog - Diálogo Acerca de.

Diálogo de información de la aplicación,
separado del MainWindow.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextBrowser
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont
import logging


logger = logging.getLogger(__name__)


class AboutDialog(QDialog):
    """Diálogo Acerca de JustBeat-DAW."""
    
    closed = Signal()
    
    def __init__(self, parent=None):
        """Inicializar diálogo.
        
        Args:
            parent: Widget padre
        """
        super().__init__(parent)
        
        self.setWindowTitle("About JustBeat-DAW")
        self.setModal(True)
        self.setMinimumSize(450, 400)
        self.setMaximumSize(600, 500)
        
        self._setup_ui()
        
        logger.info("AboutDialog inicializado")
    
    def _setup_ui(self) -> None:
        """Configurar UI."""
        
        layout = QVBoxLayout(self)
        
        # Logo/Title
        title_label = QLabel("JustBeat-DAW")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #00d4ff;
                padding: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Version
        version_label = QLabel("Version 1.0.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("""
            QLabel {
                color: #888;
                padding: 5px;
            }
        """)
        layout.addWidget(version_label)
        
        # Description
        desc_label = QLabel(
            "Professional 8-bit DAW for chiptune music production"
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            QLabel {
                color: #ccc;
                padding: 15px;
            }
        """)
        layout.addWidget(desc_label)
        
        # Info
        info_browser = QTextBrowser()
        info_browser.setHtml("""
            <div style="color: #aaa; font-size: 11px;">
            <p><b>Features:</b></p>
            <ul>
                <li>Polyphonic synthesizers (16 voices)</li>
                <li>Hardware emulation (NES, GameBoy, C64)</li>
                <li>Pattern-based and linear sequencing</li>
                <li>Automation lanes</li>
                <li>MIDI Learn support</li>
                <li>WAV and MIDI export</li>
            </ul>
            <p><b>Technology:</b></p>
            <ul>
                <li>Python 3 + PySide6</li>
                <li>NumPy for audio processing</li>
                <li>Clean Architecture</li>
            </ul>
            </div>
        """)
        info_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #333;
                color: #aaa;
                border: 1px solid #444;
            }
        """)
        layout.addWidget(info_browser)
        
        # Copyright
        copyright_label = QLabel(
            "© 2024 ArcSoft. All rights reserved."
        )
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 10px;
                padding: 10px;
            }
        """)
        layout.addWidget(copyright_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_button = QPushButton("OK")
        ok_button.setFixedWidth(100)
        ok_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Estilo general
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QPushButton {
                background-color: #444;
                color: white;
                border: 1px solid #555;
                padding: 8px 20px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #333;
            }
        """)
    
    def closeEvent(self, event) -> None:
        """Evento de cierre."""
        self.closed.emit()
        super().closeEvent(event)
    
    @classmethod
    def show_about(cls, parent=None) -> None:
        """Mostrar diálogo.
        
        Args:
            parent: Widget padre
        """
        dialog = cls(parent)
        dialog.exec()


class PreferencesDialog(QDialog):
    """Diálogo de preferencias."""
    
    def __init__(self, parent=None):
        """Inicializar diálogo."""
        super().__init__(parent)
        
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        self._setup_ui()
        
        logger.info("PreferencesDialog inicializado")
    
    def _setup_ui(self) -> None:
        """Configurar UI."""
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Preferences")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Placeholder - implementar según necesidad
        placeholder = QLabel("Preferences will be implemented here.")
        placeholder.setStyleSheet("color: #888; padding: 20px;")
        layout.addWidget(placeholder)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ccc;
            }
            QPushButton {
                background-color: #444;
                color: white;
                border: 1px solid #555;
                padding: 8px 20px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
