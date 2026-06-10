"""MIDI Learn Panel Widget - Panel de aprendizaje MIDI.

Este widget permite asignar controles MIDI a parámetros de la aplicación.

Implementado con PresentationModel para seguir la nueva arquitectura.
"""

import logging
from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox
)
from PySide6.QtCore import Qt, Signal

from src.presentation.styles.theme_integration import ThemeMixin


logger = logging.getLogger(__name__)


class MIDILearnPanel(QWidget, ThemeMixin):
    """Panel de aprendizaje MIDI.
    
    Permite mapear mensajes MIDI a parámetros de la aplicación.
    """
    
    # Señales
    mapping_added = Signal(str, int, str)  # param_id, midi_channel, midi_control
    mapping_removed = Signal(str)  # param_id
    midi_learn_started = Signal()
    midi_learn_stopped = Signal()
    
    def __init__(
        self,
        presentation_model=None,
        parent=None
    ):
        """Inicializar el panel MIDI Learn.
        
        Args:
            presentation_model: PresentationModel para acceder a los datos
            parent: Widget padre
        """
        ThemeMixin.__init__(self)
        super().__init__(parent)
        
        # Usar PresentationModel si se proporciona, o obtener el global
        if presentation_model is not None:
            self._model = presentation_model
        else:
            from src.presentation.models import get_presentation_model
            self._model = get_presentation_model()
        
        # Estado
        self._mappings: Dict[str, Dict] = {}
        self._is_learning = False
        self._selected_mapping: Optional[str] = None
        
        # Conectar señales del modelo
        self._connect_model_signals()
        
        self._setup_ui()
        self.apply_theme()
    
    def _connect_model_signals(self) -> None:
        """Conectar señales del PresentationModel."""
        pass  # Añadir señales según necesidad
    
    def _setup_ui(self) -> None:
        """Configurar interfaz de usuario."""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Título
        title = QLabel("MIDI Learn")
        title.setStyleSheet("""
            color: white;
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #2a2a2a;
        """)
        layout.addWidget(title)
        
        # Botones de control
        btn_layout = QHBoxLayout()
        
        self._learn_btn = QPushButton("Learn")
        self._learn_btn.setCheckable(True)
        self._learn_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:checked {
                background-color: #0a0;
            }
        """)
        self._learn_btn.clicked.connect(self._on_learn_clicked)
        btn_layout.addWidget(self._learn_btn)
        
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #a44;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c55;
            }
        """)
        self._clear_btn.clicked.connect(self._on_clear_clicked)
        btn_layout.addWidget(self._clear_btn)
        
        layout.addLayout(btn_layout)
        
        # Estado de aprendizaje
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("""
            color: #888;
            font-size: 11px;
            padding: 3px;
        """)
        layout.addWidget(self._status_label)
        
        # Tabla de mappings
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels([
            "Parameter", "MIDI Channel", "MIDI Control"
        ])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                color: white;
                gridline-color: #333;
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #0af;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: white;
                padding: 5px;
                border: none;
            }
        """)
        layout.addWidget(self._table)
        
        # Información de ayuda
        help_text = QLabel(
            "Click 'Learn' then move a MIDI control\n"
            "to assign it to a parameter."
        )
        help_text.setStyleSheet("""
            color: #666;
            font-size: 10px;
            padding: 5px;
        """)
        layout.addWidget(help_text)
    
    def _on_learn_clicked(self, checked: bool) -> None:
        """Manejar clic en botón Learn."""
        self._is_learning = checked
        
        if checked:
            self._status_label.setText("Waiting for MIDI input...")
            self._status_label.setStyleSheet("""
                color: #0f0;
                font-size: 11px;
                padding: 3px;
            """)
            self.midi_learn_started.emit()
        else:
            self._status_label.setText("Ready")
            self._status_label.setStyleSheet("""
                color: #888;
                font-size: 11px;
                padding: 3px;
            """)
            self.midi_learn_stopped.emit()
    
    def _on_clear_clicked(self) -> None:
        """Manejar clic en botón Clear."""
        if self._selected_mapping:
            self.remove_mapping(self._selected_mapping)
    
    def add_mapping(
        self,
        param_id: str,
        param_name: str,
        midi_channel: int,
        midi_control: int
    ) -> None:
        """Añadir un mapping MIDI.
        
        Args:
            param_id: ID del parámetro
            param_name: Nombre del parámetro
            midi_channel: Canal MIDI (0-15)
            midi_control: Número de control MIDI (0-127)
        """
        self._mappings[param_id] = {
            "name": param_name,
            "channel": midi_channel,
            "control": midi_control
        }
        
        # Añadir a la tabla
        row = self._table.rowCount()
        self._table.insertRow(row)
        
        self._table.setItem(row, 0, QTableWidgetItem(param_name))
        self._table.setItem(row, 1, QTableWidgetItem(str(midi_channel + 1)))
        self._table.setItem(row, 2, QTableWidgetItem(str(midi_control)))
        
        logger.info(
            f"MIDI mapping added: {param_name} -> "
            f"Ch.{midi_channel + 1} CC{midi_control}"
        )
    
    def remove_mapping(self, param_id: str) -> None:
        """Eliminar un mapping MIDI.
        
        Args:
            param_id: ID del parámetro
        """
        if param_id in self._mappings:
            del self._mappings[param_id]
            self.midi_learn_removed.emit(param_id)
            
            # Actualizar tabla
            for row in range(self._table.rowCount()):
                item = self._table.item(row, 0)
                if item and item.text() == param_id:
                    self._table.removeRow(row)
                    break
            
            logger.info(f"MIDI mapping removed: {param_id}")
    
    def get_mappings(self) -> Dict[str, Dict]:
        """Obtener todos los mappings.
        
        Returns:
            Diccionario de mappings
        """
        return self._mappings.copy()
    
    def clear_all_mappings(self) -> None:
        """Eliminar todos los mappings."""
        self._mappings.clear()
        self._table.setRowCount(0)
        logger.info("All MIDI mappings cleared")
