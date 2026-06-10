"""Performance Monitor Widget - Monitor de rendimiento en tiempo real.

Widget UI que visualiza las métricas de rendimiento del motor de audio:
CPU, buffer utilization, voice count, latencia, y tips de optimización.

Uso:
    monitor = PerformanceMonitorWidget(performance_monitor)
    dock.addWidget(monitor)
"""

from typing import Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QProgressBar, QGridLayout
)

from src.presentation.styles.pro_theme import ProTheme


class MetricBar(QFrame):
    """Barra de métrica individual con label, barra de progreso y valor."""

    def __init__(self, label: str, color: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = color
        self._label_text = label

        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self._label = QLabel(label)
        self._label.setFixedWidth(100)
        self._label.setStyleSheet("color: #a0a0b0; font-size: 9pt;")
        layout.addWidget(self._label)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(12)
        self._bar.setTextVisible(False)
        layout.addWidget(self._bar, 1)

        self._value_label = QLabel("0%")
        self._value_label.setFixedWidth(50)
        self._value_label.setStyleSheet("color: #f0f0f0; font-size: 9pt; font-weight: bold;")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._value_label)

        self._apply_style(0)

    def set_value(self, percent: float, text: str = ""):
        self._bar.setValue(int(percent))
        self._value_label.setText(text or f"{percent:.0f}%")
        self._apply_style(percent)

    def _apply_style(self, percent: float):
        c = ProTheme.get()
        if percent > 80:
            bar_color = c.accent_danger
        elif percent > 50:
            bar_color = c.accent_warning
        else:
            bar_color = c.accent_primary

        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {c.bg_tertiary};
                border: 1px solid {c.border_color};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 2px;
            }}
        """)


class PerformanceMonitorWidget(QFrame):
    """Widget de monitoreo de rendimiento en tiempo real."""

    REFRESH_MS = 500

    def __init__(
        self,
        performance_monitor: Optional[object] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._monitor = performance_monitor
        self._timer = QTimer(self)

        self._setup_ui()
        self._start_monitoring()

    def _setup_ui(self):
        c = ProTheme.get()
        self.setStyleSheet(f"""
            PerformanceMonitorWidget {{
                background-color: {c.bg_secondary};
                border: 1px solid {c.border_color};
                border-radius: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel("Performance Monitor")
        header.setStyleSheet(f"""
            color: {c.text_accent}; font-size: 10pt;
            font-weight: bold; padding-bottom: 4px;
        """)
        layout.addWidget(header)

        self._cpu_bar = MetricBar("CPU Usage", c.accent_primary)
        layout.addWidget(self._cpu_bar)

        self._buffer_bar = MetricBar("Buffer", c.accent_info)
        layout.addWidget(self._buffer_bar)

        self._voice_bar = MetricBar("Voices", c.accent_success)
        layout.addWidget(self._voice_bar)

        self._latency_bar = MetricBar("Latency", c.accent_secondary)
        layout.addWidget(self._latency_bar)

        info_layout = QGridLayout()
        info_layout.setSpacing(4)

        self._level_label = QLabel("Level: --")
        self._level_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 8pt;")
        info_layout.addWidget(self._level_label, 0, 0)

        self._underrun_label = QLabel("Under-runs: 0")
        self._underrun_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 8pt;")
        info_layout.addWidget(self._underrun_label, 0, 1)

        self._tip_label = QLabel("Tip: --")
        self._tip_label.setStyleSheet(f"color: {c.accent_info}; font-size: 8pt;")
        info_layout.addWidget(self._tip_label, 1, 0, 1, 2)

        layout.addLayout(info_layout)
        layout.addStretch()

    def _start_monitoring(self):
        self._timer.timeout.connect(self._refresh)
        self._timer.start(self.REFRESH_MS)

    def _refresh(self):
        if self._monitor is None:
            self._demo_mode()
            return
        try:
            metrics = self._monitor.get_metrics()

            cpu = getattr(metrics, 'cpu_percent', 0)
            self._cpu_bar.set_value(cpu, f"{cpu:.1f}%")

            buffer_usage = getattr(metrics, 'buffer_usage', 0)
            self._buffer_bar.set_value(buffer_usage, f"{buffer_usage:.0f}%")

            voices = getattr(metrics, 'active_voices', 0)
            max_voices = getattr(metrics, 'max_voices', 16)
            voice_pct = (voices / max_voices * 100) if max_voices > 0 else 0
            self._voice_bar.set_value(voice_pct, f"{voices}/{max_voices}")

            latency = getattr(metrics, 'current_latency_ms', 0)
            latency_pct = min(latency / 50 * 100, 100)
            self._latency_bar.set_value(latency_pct, f"{latency:.1f}ms")

            level = getattr(metrics, 'performance_level', None)
            if level:
                self._level_label.setText(f"Level: {level.value}")

            underruns = getattr(metrics, 'underruns', 0)
            self._underrun_label.setText(f"Under-runs: {underruns}")

            self._update_tip(cpu, buffer_usage, latency)

        except Exception as e:
            pass

    def _demo_mode(self):
        import math, time
        t = time.time()
        cpu = 25 + 15 * math.sin(t * 0.3)
        buffer_usage = 30 + 20 * math.sin(t * 0.2 + 1)
        voices = 4 + 3 * math.sin(t * 0.5)
        latency = 8 + 4 * math.sin(t * 0.4 + 2)
        underruns = 0

        self._cpu_bar.set_value(cpu, f"{cpu:.1f}%")
        self._buffer_bar.set_value(buffer_usage, f"{buffer_usage:.0f}%")
        max_voices = 16
        self._voice_bar.set_value(voices / max_voices * 100, f"{int(voices)}/{max_voices}")
        latency_pct = min(latency / 50 * 100, 100)
        self._latency_bar.set_value(latency_pct, f"{latency:.1f}ms")
        self._level_label.setText("Level: good (demo)")
        self._underrun_label.setText(f"Under-runs: {underruns}")
        self._update_tip(cpu, buffer_usage, latency)

    def _update_tip(self, cpu: float, buffer_usage: float, latency: float):
        if cpu > 70:
            tip = "High CPU. Try reducing voice count or FX."
        elif buffer_usage > 70:
            tip = "Buffer near limit. Increase buffer size."
        elif latency > 20:
            tip = "High latency. Decrease buffer size."
        else:
            tip = "Performance is optimal."
        self._tip_label.setText(f"Tip: {tip}")
