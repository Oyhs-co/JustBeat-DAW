"""Barra de transporte profesional para JustBeat-DAW.

Proporciona una barra de transporte completa con:
- Controles de transporte grandes con hover glow
- Display de tiempo: BBB:BB:SS:TT (Bars:Beats:Sixteenths:Ticks)
- BPM editable + botón Tap Tempo
- Botones toggle: Metronome, Loop, Snap
- Master Volume con mini VU meter

Uso:
    transport = TransportBar(presentation_model)
    main_layout.addWidget(transport)
"""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QSlider, QLineEdit,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QFont

from src.presentation.styles.pro_theme import ProTheme
from src.presentation.styles.icons import Icons


logger = logging.getLogger(__name__)


class MiniVUMeter(QWidget):
    """Mini VU meter integrado en la barra de transporte.

    Muestra niveles RMS estéreo con gradiente verde-amarillo-rojo.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 16)
        self._level_left = 0.0
        self._level_right = 0.0
        self._peak_left = 0.0
        self._peak_right = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._decay_peak)
        self._timer.start()

    def set_levels(self, left: float, right: float):
        """Actualizar niveles RMS."""
        self._level_left = max(0.0, min(1.0, left))
        self._level_right = max(0.0, min(1.0, right))
        self._peak_left = max(self._peak_left, self._level_left)
        self._peak_right = max(self._peak_right, self._level_right)
        self.update()

    def _decay_peak(self):
        """Decaer picos gradualmente."""
        self._peak_left *= 0.92
        self._peak_right *= 0.92
        if self._peak_left < 0.01:
            self._peak_left = 0.0
        if self._peak_right < 0.01:
            self._peak_right = 0.0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = ProTheme.get()
        w, h = self.width(), self.height()
        bar_w = (w - 2) // 2

        for ch, level, peak in [
            (0, self._level_left, self._peak_left),
            (1, self._level_right, self._peak_right)
        ]:
            x = ch * (bar_w + 2)
            # Fondo
            painter.fillRect(x, 0, bar_w, h, QColor(c.meter_bg))

            # Barra de nivel
            lh = int(level * h)
            if lh > 0:
                gradient = QLinearGradient(0, h, 0, 0)
                gradient.setColorAt(0.0, QColor(c.meter_green))
                gradient.setColorAt(0.6, QColor(c.meter_yellow))
                gradient.setColorAt(0.85, QColor(c.meter_red))
                painter.fillRect(x, h - lh, bar_w, lh, gradient)

            # Línea de pico
            if peak > 0:
                py = h - int(peak * h)
                painter.setPen(QPen(QColor(c.meter_clip), 1))
                painter.drawLine(x, py, x + bar_w, py)

        # Borde
        painter.setPen(QPen(QColor(c.border_color), 1))
        painter.drawRect(0, 0, w - 1, h - 1)


class TimeDisplay(QWidget):
    """Display de tiempo BBB:BB:SS:TT.

    Muestra la posición actual en Bars:Beats:Sixteenths:Ticks.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 32)
        self._bars = 1
        self._beats = 1
        self._sixteenths = 0
        self._ticks = 0
        self._time_sig_beats = 4
        self._time_sig_unit = 4

    def set_position(self, tick: int, bpm: int = 120):
        """Actualizar posición desde ticks.

        Calcula la posición en términos musicales.
        """
        ticks_per_beat = 480
        ticks_per_bar = ticks_per_beat * self._time_sig_beats

        total_beats = tick / ticks_per_beat
        self._bars = int(total_beats / self._time_sig_beats) + 1
        self._beats = int(total_beats % self._time_sig_beats) + 1
        self._sixteenths = int((tick % ticks_per_beat) / (ticks_per_beat / 4))
        self._ticks = tick % (ticks_per_beat // 4)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = ProTheme.get()

        # Fondo oscuro tipo display LED
        painter.fillRect(self.rect(), QColor(c.time_display_bg))

        # Borde
        painter.setPen(QPen(QColor(c.border_color), 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        # Texto del display
        font = QFont("Consolas", 14, QFont.Weight.Bold)
        painter.setFont(font)

        time_str = f"{self._bars:03d}:{self._beats:02d}:{self._sixteenths:02d}:{self._ticks:02d}"

        # Sombra del texto
        painter.setPen(QColor(0, 0, 0, 80))
        painter.drawText(1, 1, self.width(), self.height(), Qt.AlignmentFlag.AlignCenter, time_str)

        # Texto principal
        painter.setPen(QColor(c.time_display_color))
        painter.drawText(0, 0, self.width(), self.height(), Qt.AlignmentFlag.AlignCenter, time_str)


class TransportButton(QPushButton):
    """Botón de transporte con glow en hover y active state."""

    def __init__(self, icon, tooltip: str = "", parent=None):
        super().__init__(parent)
        self.setIcon(icon)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._update_style()

    def _update_style(self, hover: bool = False):
        c = ProTheme.get()
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c.text_tertiary};
                border: none;
                font-size: 18px;
                padding: 6px 10px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {c.bg_hover};
                color: {c.text_accent};
            }}
            QPushButton:pressed {{
                background-color: {c.bg_active};
                color: {c.text_accent};
            }}
        """)

    def set_active(self, active: bool):
        """Marcar como activo (para play/record)."""
        c = ProTheme.get()
        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c.bg_active};
                    color: {c.text_accent};
                    border: 1px solid {c.border_accent};
                    font-size: 18px;
                    padding: 6px 10px;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {c.bg_hover};
                }}
            """)
        else:
            self._update_style()


class TransportBar(QFrame):
    """Barra de transporte profesional.

    Señales:
        play_clicked: Emitido al hacer clic en play.
        stop_clicked: Emitido al hacer clic en stop.
        record_clicked: Emitido al hacer clic en record.
        bpm_changed: Emitido al cambiar BPM (int).
        metronome_toggled: Emitido al toggle metronome (bool).
        loop_toggled: Emitido al toggle loop (bool).
    """

    play_clicked = Signal()
    stop_clicked = Signal()
    record_clicked = Signal()
    bpm_changed = Signal(int)
    metronome_toggled = Signal(bool)
    loop_toggled = Signal(bool)

    def __init__(self, presentation_model=None, parent=None):
        super().__init__(parent)
        self._model = presentation_model

        c = ProTheme.get()
        self.setFixedHeight(48)
        self.setStyleSheet(f"""
            TransportBar {{
                background-color: {c.transport_bg};
                border: none;
                border-bottom: 1px solid {c.transport_border};
            }}
        """)

        self._is_playing = False
        self._is_recording = False
        self._metronome_enabled = False
        self._loop_enabled = False

        self._setup_ui()

        # Timer para animación de glow en play
        self._pulse_timer: Optional[QTimer] = None

    def _setup_ui(self):
        """Configurar todos los componentes de la barra."""
        layout = QHBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 2, 8, 2)

        # === SECCIÓN IZQUIERDA: File Operations ===
        file_section = self._make_section()
        self._btn_new = self._make_tool_button(Icons.NEW_FILE, "New Project (Ctrl+N)")
        self._btn_open = self._make_tool_button(Icons.OPEN, "Open Project (Ctrl+O)")
        self._btn_save = self._make_tool_button(Icons.SAVE, "Save Project (Ctrl+S)")
        file_section.addWidget(self._btn_new)
        file_section.addWidget(self._btn_open)
        file_section.addWidget(self._btn_save)

        file_section.addWidget(self._make_separator())
        layout.addLayout(file_section)

        # === SECCIÓN CENTRAL: Transport Controls ===
        transport_section = self._make_section()

        self._btn_rewind = TransportButton(Icons.REWIND, "Rewind (Home)")
        transport_section.addWidget(self._btn_rewind)

        self._btn_play = TransportButton(Icons.PLAY, "Play/Pause (Space)")
        self._btn_play.set_active(False)
        transport_section.addWidget(self._btn_play)

        self._btn_stop = TransportButton(Icons.STOP, "Stop (Ctrl+.)")
        transport_section.addWidget(self._btn_stop)

        self._btn_record = TransportButton(Icons.RECORD, "Record (Ctrl+R)")
        transport_section.addWidget(self._btn_record)

        self._btn_forward = TransportButton(Icons.FAST_FORWARD, "Fast Forward (End)")
        transport_section.addWidget(self._btn_forward)

        transport_section.addWidget(self._make_separator())
        layout.addLayout(transport_section)

        # === DISPLAY DE TIEMPO ===
        self._time_display = TimeDisplay()
        layout.addWidget(self._time_display)

        layout.addWidget(self._make_separator())

        # === SECCIÓN BPM ===
        bpm_section = self._make_section()

        bpm_label = QLabel("BPM")
        bpm_label.setStyleSheet(f"color: {ProTheme.get().text_tertiary}; font-size: 9px;")
        bpm_section.addWidget(bpm_label)

        self._bpm_input = QLineEdit("120")
        self._bpm_input.setFixedWidth(40)
        self._bpm_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bpm_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {ProTheme.get().bg_tertiary};
                color: {ProTheme.get().text_accent};
                border: 1px solid {ProTheme.get().border_color};
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 14px;
                font-weight: bold;
                font-family: Consolas;
            }}
            QLineEdit:focus {{
                border-color: {ProTheme.get().border_focus};
            }}
        """)
        self._bpm_input.returnPressed.connect(self._on_bpm_entered)
        bpm_section.addWidget(self._bpm_input)

        self._btn_tap = QPushButton("Tap")
        self._btn_tap.setFixedSize(32, 22)
        self._btn_tap.setStyleSheet(f"""
            QPushButton {{
                background-color: {ProTheme.get().button_bg};
                color: {ProTheme.get().text_tertiary};
                border: 1px solid {ProTheme.get().border_color};
                border-radius: 4px;
                font-size: 8px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background-color: {ProTheme.get().bg_hover};
                color: {ProTheme.get().text_accent};
            }}
        """)
        self._btn_tap.clicked.connect(self._on_tap_tempo)
        bpm_section.addWidget(self._btn_tap)

        layout.addLayout(bpm_section)
        layout.addWidget(self._make_separator())

        # === SECCIÓN TOGGLES ===
        toggle_section = self._make_section()

        self._btn_metronome = QPushButton()
        self._btn_metronome.setIcon(Icons.METRONOME)
        self._btn_metronome.setCheckable(True)
        self._btn_metronome.setToolTip("Metronome (M)")
        self._btn_metronome.setFixedSize(28, 24)
        self._update_toggle_style(self._btn_metronome, False)
        self._btn_metronome.clicked.connect(self._on_metronome_toggled)
        toggle_section.addWidget(self._btn_metronome)

        self._btn_loop = QPushButton()
        self._btn_loop.setIcon(Icons.LOOP)
        self._btn_loop.setCheckable(True)
        self._btn_loop.setToolTip("Loop (L)")
        self._btn_loop.setFixedSize(28, 24)
        self._update_toggle_style(self._btn_loop, False)
        self._btn_loop.clicked.connect(self._on_loop_toggled)
        toggle_section.addWidget(self._btn_loop)

        self._btn_snap = QPushButton()
        self._btn_snap.setIcon(Icons.TOOL_SNAP)
        self._btn_snap.setCheckable(True)
        self._btn_snap.setChecked(True)
        self._btn_snap.setToolTip("Snap to Grid (N)")
        self._btn_snap.setFixedSize(28, 24)
        self._update_toggle_style(self._btn_snap, True)
        toggle_section.addWidget(self._btn_snap)

        layout.addLayout(toggle_section)

        layout.addStretch()

        # === SECCIÓN DERECHA: Master Volume + VU ===
        right_section = self._make_section()

        master_label = QLabel("Master")
        master_label.setStyleSheet(f"color: {ProTheme.get().text_tertiary}; font-size: 9px;")
        right_section.addWidget(master_label)

        self._master_vol = QSlider(Qt.Orientation.Horizontal)
        self._master_vol.setRange(0, 100)
        self._master_vol.setValue(80)
        self._master_vol.setFixedWidth(60)
        self._master_vol.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {ProTheme.get().slider_groove};
                height: 3px;
                border-radius: 1px;
            }}
            QSlider::handle:horizontal {{
                background: {ProTheme.get().slider_handle};
                width: 8px;
                margin: -3px 0;
                border-radius: 4px;
            }}
            QSlider::sub-page:horizontal {{
                background: {ProTheme.get().slider_fill};
                border-radius: 1px;
            }}
        """)
        right_section.addWidget(self._master_vol)

        self._mini_vu = MiniVUMeter()
        right_section.addWidget(self._mini_vu)

        layout.addLayout(right_section)

    def _make_section(self) -> QHBoxLayout:
        """Crear una sección horizontal con espaciado."""
        section = QHBoxLayout()
        section.setSpacing(4)
        section.setContentsMargins(0, 0, 0, 0)
        return section

    def _make_separator(self) -> QFrame:
        """Crear separador vertical."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background-color: {ProTheme.get().border_color};")
        return sep

    def _make_tool_button(self, icon, tooltip: str) -> QPushButton:
        """Crear botón de herramienta pequeño."""
        btn = QPushButton()
        btn.setIcon(icon)
        btn.setToolTip(tooltip)
        btn.setFixedSize(24, 24)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {ProTheme.get().text_tertiary};
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {ProTheme.get().bg_hover};
                color: {ProTheme.get().text_accent};
            }}
            QPushButton:pressed {{
                background-color: {ProTheme.get().bg_active};
            }}
        """)
        return btn

    def _update_toggle_style(self, btn: QPushButton, checked: bool):
        """Actualizar estilo de botón toggle."""
        c = ProTheme.get()
        if checked:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c.bg_active};
                    color: {c.text_accent};
                    border: 1px solid {c.border_accent};
                    border-radius: 4px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {c.bg_hover};
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {c.text_tertiary};
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {c.bg_hover};
                    color: {c.text_accent};
                }}
            """)

    def _on_bpm_entered(self):
        """Procesar BPM ingresado manualmente."""
        try:
            bpm = int(self._bpm_input.text())
            bpm = max(20, min(300, bpm))
            self._bpm_input.setText(str(bpm))
            self.bpm_changed.emit(bpm)
        except ValueError:
            pass

    def _on_tap_tempo(self):
        """Procesar tap tempo."""
        import time
        now = time.time()
        if not hasattr(self, '_tap_times'):
            self._tap_times = []
        self._tap_times.append(now)
        # Mantener solo los últimos 4 taps
        if len(self._tap_times) > 4:
            self._tap_times.pop(0)
        if len(self._tap_times) >= 2:
            intervals = [self._tap_times[i+1] - self._tap_times[i]
                        for i in range(len(self._tap_times)-1)]
            avg_interval = sum(intervals) / len(intervals)
            if avg_interval > 0:
                bpm = int(60.0 / avg_interval)
                bpm = max(20, min(300, bpm))
                self._bpm_input.setText(str(bpm))
                self.bpm_changed.emit(bpm)

    def _on_metronome_toggled(self, checked: bool):
        """Toggle metronome."""
        self._metronome_enabled = checked
        self._update_toggle_style(self._btn_metronome, checked)
        self.metronome_toggled.emit(checked)
        logger.info(f"Metronome: {checked}")

    def _on_loop_toggled(self, checked: bool):
        """Toggle loop."""
        self._loop_enabled = checked
        self._update_toggle_style(self._btn_loop, checked)
        self.loop_toggled.emit(checked)
        logger.info(f"Loop: {checked}")

    # === Métodos públicos ===

    def set_playing(self, playing: bool):
        """Actualizar estado de play."""
        self._is_playing = playing
        if playing:
            self._btn_play.setIcon(Icons.PAUSE)
            self._btn_play.set_active(True)
            self._start_play_glow()
        else:
            self._btn_play.setIcon(Icons.PLAY)
            self._btn_play.set_active(False)
            self._stop_play_glow()

    def set_recording(self, recording: bool):
        """Actualizar estado de grabación."""
        self._is_recording = recording
        if recording:
            self._btn_record.set_active(True)
        else:
            self._btn_record.set_active(False)

    def set_bpm(self, bpm: int):
        """Actualizar display de BPM."""
        self._bpm_input.setText(str(bpm))

    def set_position(self, tick: int, bpm: int = 120):
        """Actualizar display de tiempo."""
        self._time_display.set_position(tick, bpm)

    def set_levels(self, left: float, right: float):
        """Actualizar VU meter."""
        self._mini_vu.set_levels(left, right)

    def set_metronome(self, enabled: bool):
        """Establecer estado de metronome."""
        self._metronome_enabled = enabled
        self._btn_metronome.setChecked(enabled)
        self._update_toggle_style(self._btn_metronome, enabled)

    def set_loop(self, enabled: bool):
        """Establecer estado de loop."""
        self._loop_enabled = enabled
        self._btn_loop.setChecked(enabled)
        self._update_toggle_style(self._btn_loop, enabled)

    def _start_play_glow(self):
        """Iniciar animación de glow en botón play."""
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(800)

        c = ProTheme.get()
        normal = f"""
            QPushButton {{
                background-color: {c.bg_active};
                color: {c.button_play};
                border: 1px solid {c.border_accent};
                font-size: 18px;
                padding: 6px 10px;
                border-radius: 6px;
            }}
        """
        glow = f"""
            QPushButton {{
                background-color: rgba(0, 212, 170, 0.15);
                color: {c.button_play_hover};
                border: 1px solid {c.accent_primary};
                font-size: 18px;
                padding: 6px 10px;
                border-radius: 6px;
            }}
        """

        state = [False]
        def _pulse():
            state[0] = not state[0]
            self._btn_play.setStyleSheet(glow if state[0] else normal)

        self._pulse_timer.timeout.connect(_pulse)
        self._pulse_timer.start()

    def _stop_play_glow(self):
        """Detener animación de glow."""
        if self._pulse_timer:
            self._pulse_timer.stop()
            self._pulse_timer = None

    def connect_signals(self, model) -> None:
        """Conectar señales del modelo a la barra de transporte.

        Args:
            model: PresentationModel para conectar.
        """
        if model is None:
            return

        model.playback_state_changed.connect(self._on_playback_state)
        model.position_changed.connect(self._on_position_changed)
        model.bpm_changed.connect(self.set_bpm)

    def _on_playback_state(self, state: str):
        """Manejar cambio de estado de reproducción."""
        if state == "playing":
            self.set_playing(True)
        elif state in ("stopped", "paused"):
            self.set_playing(False)

    def _on_position_changed(self, tick: int):
        """Manejar cambio de posición."""
        bpm = 120
        if self._model and hasattr(self._model, 'bpm'):
            bpm = self._model.bpm
        self.set_position(tick, bpm)

    def get_buttons(self) -> dict:
        """Obtener referencia a botones para conectar señales externas.

        Returns:
            Dict con nombres de botones.
        """
        return {
            "play": self._btn_play,
            "stop": self._btn_stop,
            "record": self._btn_record,
            "rewind": self._btn_rewind,
            "forward": self._btn_forward,
            "new": self._btn_new,
            "open": self._btn_open,
            "save": self._btn_save,
            "metronome": self._btn_metronome,
            "loop": self._btn_loop,
            "snap": self._btn_snap,
        }
