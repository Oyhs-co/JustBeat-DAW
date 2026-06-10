"""Splash Screen - Pantalla de carga profesional.

Basada en el diseño premium de JustBeat.
"""

import os
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtGui import QPixmap, QColor, QFont, QPalette
from PySide6.QtCore import Qt, Signal


class SplashScreen(QWidget):
    """Pantalla de carga profesional para JustBeat-DAW."""
    
    def __init__(self, bg_image_path: Optional[str] = None):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setFixedSize(600, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Fondo (Imagen o fallback)
        self._bg_label = QLabel(self)
        if bg_image_path is not None and os.path.exists(bg_image_path):
            pixmap = QPixmap(bg_image_path)
            self._bg_label.setPixmap(pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self._bg_label.setStyleSheet("""
                background-color: #0a0a0f;
                border-radius: 15px;
                border: 1px solid #333;
                color: white;
                font-size: 24px;
                font-weight: bold;
            """)
            self._bg_label.setText("JustBeat-DAW")
            self._bg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Overlay para información de carga
        overlay = QWidget(self._bg_label)
        overlay.setGeometry(0, 300, 600, 100)
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(40, 0, 40, 20)
        
        # Status Label
        self._status_label = QLabel("Initializing...")
        self._status_label.setStyleSheet("color: #aaa; font-size: 10px; background: transparent;")
        overlay_layout.addWidget(self._status_label)
        
        # Progress Bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 20);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff00ff, stop:1 #00ffff);
                border-radius: 2px;
            }
        """)
        overlay_layout.addWidget(self._progress)
        
        layout.addWidget(self._bg_label)
        
        # Centrar en pantalla
        screen = self.screen().availableGeometry()
        self.move(screen.center() - self.rect().center())

    def update_status(self, message: str, progress: int):
        """Update the loading message and progress bar."""
        self._status_label.setText(message)
        self._progress.setValue(progress)
        # Forzar actualización en el hilo principal
        self.repaint()
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
