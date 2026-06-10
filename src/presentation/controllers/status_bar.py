"""Status Bar Manager - Gestor de barra de estado.

Manejo desacoplado de la barra de estado,
separado del MainWindow.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QStatusBar, QLabel, QWidget, QHBoxLayout
)
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QPalette, QColor
import logging


logger = logging.getLogger(__name__)


class StatusBarManager(QObject):
    """Gestor de barra de estado.
    
    Maneja la visualización de información de estado
    como posición, BPM, CPU, etc.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Inicializar gestor de estado.
        
        Args:
            parent: Widget padre
        """
        super().__init__(parent)
        self._parent = parent
        self._statusbar: Optional[QStatusBar] = None
        
        # Labels
        self._position_label: Optional[QLabel] = None
        self._bpm_label: Optional[QLabel] = None
        self._time_signature_label: Optional[QLabel] = None
        self._cpu_label: Optional[QLabel] = None
        self._status_label: Optional[QLabel] = None
        self._record_label: Optional[QLabel] = None
        
        logger.info("StatusBarManager inicializado")
    
    def create_status_bar(self) -> QStatusBar:
        """Crear barra de estado.
        
        Returns:
            QStatusBar configurada
        """
        self._statusbar = QStatusBar(self._parent)
        
        # Configurar estilo
        self._statusbar.setStyleSheet("""
            QStatusBar {
                background-color: #2b2b2b;
                color: #cccccc;
                font-size: 11px;
            }
            QStatusBar::item {
                border: none;
            }
        """)
        
        # Crear widgets
        self._create_widgets()
        
        return self._statusbar
    
    def _create_widgets(self) -> None:
        """Crear widgets de estado."""
        
        # Posición (bar.beat.tick)
        self._position_label = QLabel("001.001.000")
        self._position_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                font-family: monospace;
            }
        """)
        self._statusbar.addPermanentWidget(self._position_label)
        
        # Separador
        self._statusbar.addPermanentWidget(self._create_separator())
        
        # BPM
        self._bpm_label = QLabel("120 BPM")
        self._bpm_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                font-weight: bold;
            }
        """)
        self._statusbar.addPermanentWidget(self._bpm_label)
        
        # Separador
        self._statusbar.addPermanentWidget(self._create_separator())
        
        # Time Signature
        self._time_signature_label = QLabel("4/4")
        self._time_signature_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
            }
        """)
        self._statusbar.addPermanentWidget(self._time_signature_label)
        
        # Separador
        self._statusbar.addPermanentWidget(self._create_separator())
        
        # CPU
        self._cpu_label = QLabel("CPU: 0%")
        self._cpu_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                color: #4caf50;
            }
        """)
        self._statusbar.addPermanentWidget(self._cpu_label)
        
        # Separador
        self._statusbar.addPermanentWidget(self._create_separator())
        
        # Record
        self._record_label = QLabel("")
        self._record_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                color: #f44336;
                font-weight: bold;
            }
        """)
        self._statusbar.addPermanentWidget(self._record_label)
        
        # Estado (mensaje)
        self._status_label = QLabel("Ready")
        self._statusbar.addWidget(self._status_label, 1)
    
    def _create_separator(self) -> QLabel:
        """Crear separador."""
        label = QLabel("|")
        label.setStyleSheet("""
            QLabel {
                color: #555;
                padding: 2px 4px;
            }
        """)
        return label
    
    # === Actualizaciones ===
    
    def update_position(self, bar: int, beat: int, tick: int) -> None:
        """Actualizar posición.
        
        Args:
            bar: Compás
            beat: Beat
            tick: Tick
        """
        if self._position_label:
            self._position_label.setText(
                f"{bar:03d}.{beat:03d}.{tick:03d}"
            )
    
    def update_position_ticks(self, ticks: int) -> None:
        """Actualizar posición desde ticks.
        
        Args:
            ticks: Posición en ticks
        """
        # Asumiendo 480 ticks/beat, 4/4
        ticks_per_beat = 480
        beats_per_bar = 4
        
        total_beats = ticks // ticks_per_beat
        bar = total_beats // beats_per_bar + 1
        beat = total_beats % beats_per_bar + 1
        tick = ticks % ticks_per_beat
        
        self.update_position(bar, beat, tick)
    
    def update_bpm(self, bpm: int) -> None:
        """Actualizar BPM.
        
        Args:
            bpm: Beats por minuto
        """
        if self._bpm_label:
            self._bpm_label.setText(f"{bpm} BPM")
    
    def update_time_signature(self, numerator: int, denominator: int) -> None:
        """Actualizar signatura de tiempo.
        
        Args:
            numerator: Beats por compás
            denominator: Figura
        """
        if self._time_signature_label:
            self._time_signature_label.setText(f"{numerator}/{denominator}")
    
    def update_cpu(self, percent: float) -> None:
        """Actualizar uso de CPU.
        
        Args:
            percent: Porcentaje
        """
        if self._cpu_label:
            self._cpu_label.setText(f"CPU: {percent:.0f}%")
            
            # Cambiar color según uso
            if percent < 30:
                color = "#4caf50"  # Verde
            elif percent < 60:
                color = "#ff9800"  # Naranja
            else:
                color = "#f44336"  # Rojo
            
            self._cpu_label.setStyleSheet(f"""
                QLabel {{
                    padding: 2px 8px;
                    color: {color};
                }}
            """)
    
    def update_status(self, message: str) -> None:
        """Actualizar mensaje de estado.
        
        Args:
            message: Mensaje
        """
        if self._status_label:
            self._status_label.setText(message)
    
    def update_recording(self, is_recording: bool) -> None:
        """Actualizar estado de grabación.
        
        Args:
            is_recording: Si está grabando
        """
        if self._record_label:
            if is_recording:
                self._record_label.setText("REC")
            else:
                self._record_label.setText("")
    
    def update_playback_state(self, is_playing: bool) -> None:
        """Actualizar estado de reproducción.
        
        Args:
            is_playing: Si está reproduciendo
        """
        if is_playing:
            self.update_status("Playing")
        else:
            self.update_status("Ready")
    
    def show_message(self, message: str, timeout: int = 3000) -> None:
        """Mostrar mensaje temporal.
        
        Args:
            message: Mensaje
            timeout: Timeout en ms
        """
        if self._statusbar:
            self._statusbar.showMessage(message, timeout)
    
    def clear_message(self) -> None:
        """Limpiar mensaje temporal."""
        if self._statusbar:
            self._statusbar.clearMessage()

    @property
    def status_bar(self) -> Optional[QStatusBar]:
        """Obtener la barra de estado.
        
        Returns:
            QStatusBar gestionada
        """
        return self._statusbar
