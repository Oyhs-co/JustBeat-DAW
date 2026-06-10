"""Effect Chain Widget - Panel de cadena de efectos.

Este widget permite añadir y configurar efectos en cadena para cada pista.

Implementado con PresentationModel para seguir la nueva arquitectura.
"""

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QSlider, QFrame,
    QScrollArea, QDial
)
from PySide6.QtCore import Qt, Signal

from src.presentation.styles.theme_integration import ThemeMixin


logger = logging.getLogger(__name__)


class EffectSlot(QFrame):
    """Ranura individual para un efecto."""
    
    effect_changed = Signal(str)
    bypass_toggled = Signal(bool)
    mix_changed = Signal(float)
    parameter_changed = Signal(str, float)
    
    EFFECTS = [
        "None",
        "Distortion",
        "Overdrive",
        "BitCrusher",
        "LowPass",
        "HighPass",
        "BandPass",
        "Reverb",
        "Delay",
        "Chorus",
        "Flanger",
        "Phaser",
        "Compressor",
        "Limiter",
        "EQ",
    ]
    
    def __init__(self, slot_index: int, parent=None):
        super().__init__(parent)
        self.slot_index = slot_index
        self._effect_type = "None"
        
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            EffectSlot {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #25252b, stop:1 #1e1e24);
                border: 1px solid #3a3a45;
                border-radius: 6px;
                padding: 2px;
                margin-bottom: 4px;
            }
            EffectSlot:hover {
                border: 1px solid #ff00ff;
            }
        """)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Header with label and bypass
        header = QHBoxLayout()
        header.setSpacing(2)
        
        self._slot_label = QLabel(f"SLOT {self.slot_index + 1}")
        self._slot_label.setStyleSheet("color: #667; font-size: 9px; font-weight: bold;")
        header.addWidget(self._slot_label)
        
        header.addStretch()
        
        self._bypass_btn = QPushButton("⏻") # Power icon
        self._bypass_btn.setCheckable(True)
        self._bypass_btn.setFixedSize(18, 18)
        self._bypass_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #555;
                border: 1px solid #444;
                border-radius: 9px;
                font-size: 10px;
            }
            QPushButton:checked {
                background-color: #00ff88;
                color: #000;
                border: 1px solid #00ff88;
            }
        """)
        self._bypass_btn.clicked.connect(self._on_bypass_clicked)
        header.addWidget(self._bypass_btn)
        layout.addLayout(header)
        
        # Effect combo
        self._effect_combo = QComboBox()
        self._effect_combo.addItems(self.EFFECTS)
        self._effect_combo.setStyleSheet("""
            QComboBox {
                background-color: #121216;
                color: white;
                border: 1px solid #333;
                border-radius: 3px;
                padding: 2px 5px;
                font-size: 11px;
            }
            QComboBox::drop-down { border: none; }
        """)
        self._effect_combo.currentTextChanged.connect(self._on_effect_changed)
        layout.addWidget(self._effect_combo)
        
        # Mix slider (compact)
        mix_layout = QHBoxLayout()
        mix_label = QLabel("MIX")
        mix_label.setStyleSheet("color: #889; font-size: 8px; min-width: 20px;")
        mix_layout.addWidget(mix_label)
        
        self._mix_slider = QSlider(Qt.Orientation.Horizontal)
        self._mix_slider.setRange(0, 100)
        self._mix_slider.setValue(100)
        self._mix_slider.setFixedHeight(12)
        self._mix_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 3px; background: #111; border-radius: 1px; }
            QSlider::handle:horizontal { background: #0af; width: 10px; margin: -4px 0; border-radius: 5px; }
        """)
        self._mix_slider.valueChanged.connect(self._on_mix_changed)
        mix_layout.addWidget(self._mix_slider)
        layout.addLayout(mix_layout)
    
    def _on_effect_changed(self, text: str) -> None:
        self._effect_type = text
        self.effect_changed.emit(text)
    
    def _on_bypass_clicked(self, checked: bool) -> None:
        self.bypass_toggled.emit(checked)
    
    def _on_mix_changed(self, value: int) -> None:
        self.mix_changed.emit(value / 100.0)
    
    def get_config(self) -> Dict[str, Any]:
        return {
            "type": self._effect_type,
            "bypassed": self._bypass_btn.isChecked(),
            "mix": self._mix_slider.value() / 100.0,
        }


class EffectChainWidget(QWidget, ThemeMixin):
    """Widget de cadena de efectos.
    
    Permite gestionar múltiples efectos en serie para una pista.
    """
    
    effect_added = Signal(int, str)  # slot_index, effect_type
    effect_removed = Signal(int)
    chain_changed = Signal()
    
    def __init__(
        self,
        presentation_model=None,
        max_slots: int = 8,
        parent=None
    ):
        ThemeMixin.__init__(self)
        super().__init__(parent)
        
        # Usar PresentationModel si se proporciona, o obtener el global
        if presentation_model is not None:
            self._model = presentation_model
        else:
            from src.presentation.models import get_presentation_model
            self._model = get_presentation_model()
        
        self._max_slots = max_slots
        self._slots: List[EffectSlot] = []
        
        # Inicializar track actual
        self._current_track_id: Optional[str] = None
        
        # Conectar señales del modelo
        self._connect_model_signals()
        
        self._setup_ui()
        self.apply_theme()
    
    def _connect_model_signals(self) -> None:
        """Conectar señales del PresentationModel."""
        if self._model:
            self._model.track_modified.connect(self._on_track_modified)
    
    def _on_track_modified(self, track_id: str, changes: Dict) -> None:
        """Manejar modificación de pista."""
        if track_id == self._current_track_id:
            # Re-cargar si es necesario
            pass

    def set_track(self, track_id: str) -> None:
        """Establecer la pista activa para la cadena de efectos."""
        self._current_track_id = track_id
        if self._model:
            # Cargar configuración de efectos desde el modelo
            # Por ahora es un placeholder ya que Track no tiene effects list en dominio simple
            pass
        logger.debug(f"EffectChain switching to track: {track_id}")
    
    def _setup_ui(self) -> None:
        """Configurar UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Título
        title = QLabel("Effect Chain")
        title.setStyleSheet("""
            color: white;
            font-weight: bold;
            font-size: 12px;
            padding: 5px;
            background-color: #2a2a2a;
        """)
        layout.addWidget(title)
        
        # Scroll area para efectos
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1a1a1a;
                border: none;
            }
        """)
        
        # Contenedor de slots
        slots_widget = QWidget()
        slots_layout = QVBoxLayout(slots_widget)
        slots_layout.setSpacing(5)
        
        # Crear slots
        for i in range(self._max_slots):
            slot = EffectSlot(i)
            slot.effect_changed.connect(
                lambda t, idx=i: self._on_effect_changed(idx, t)
            )
            slot.bypass_toggled.connect(
                lambda b, idx=i: self._on_bypass_toggled(idx, b)
            )
            slot.mix_changed.connect(
                lambda m, idx=i: self._on_mix_changed(idx, m)
            )
            self._slots.append(slot)
            slots_layout.addWidget(slot)
        
        slots_layout.addStretch()
        scroll.setWidget(slots_widget)
        layout.addWidget(scroll)
        
        # Botones de control
        btn_layout = QVBoxLayout()
        
        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet("""
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
        clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(clear_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_effect_changed(self, slot_index: int, effect_type: str) -> None:
        logger.debug(f"Effect changed: slot {slot_index} -> {effect_type}")
        self.chain_changed.emit()
    
    def _on_bypass_toggled(self, slot_index: int, bypassed: bool) -> None:
        logger.debug(f"Bypass toggled: slot {slot_index} -> {bypassed}")
        self.chain_changed.emit()
    
    def _on_mix_changed(self, slot_index: int, mix: float) -> None:
        self.chain_changed.emit()
    
    def _on_clear(self) -> None:
        """Limpiar todos los efectos."""
        for slot in self._slots:
            slot._effect_combo.setCurrentText("None")
            slot._bypass_btn.setChecked(False)
            slot._mix_slider.setValue(100)
        self.chain_changed.emit()
    
    def get_chain_config(self) -> List[Dict[str, Any]]:
        """Obtener configuración de la cadena de efectos.
        
        Returns:
            Lista de configuraciones de efectos
        """
        return [slot.get_config() for slot in self._slots]
    
    def set_chain_config(self, config: List[Dict[str, Any]]) -> None:
        """Establecer configuración de la cadena de efectos.
        
        Args:
            config: Lista de configuraciones de efectos
        """
        for i, slot_config in enumerate(config):
            if i < len(self._slots):
                slot = self._slots[i]
                slot._effect_combo.setCurrentText(
                    slot_config.get("type", "None")
                )
                slot._bypass_btn.setChecked(
                    slot_config.get("bypassed", False)
                )
                slot._mix_slider.setValue(
                    int(slot_config.get("mix", 1.0) * 100)
                )
