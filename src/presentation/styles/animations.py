"""Sistema de animaciones para JustBeat-DAW.

Proporciona utilidades de animación reutilizables para toda la UI:
- fade_in / fade_out para paneles
- glow_pulse para botones de play/record
- slide_in / slide_out para notificaciones
- hover_scale para efectos de escala
- color_transition para cambios de estado

Uso:
    from src.presentation.styles.animations import animate_fade_in, animate_glow_pulse

    animate_fade_in(widget, duration=300)
    animate_glow_pulse(button, color="#00d4aa")
"""

from typing import Optional, Callable
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QTimer
from PySide6.QtWidgets import QWidget, QPushButton
from PySide6.QtGui import QColor, QPalette


def animate_fade_in(
    widget: QWidget,
    duration: int = 300,
    on_finished: Optional[Callable] = None
) -> QPropertyAnimation:
    """Animar fade-in de un widget (0 → 1 opacidad).

    Args:
        widget: Widget a animar.
        duration: Duración en milisegundos.
        on_finished: Callback al terminar.

    Returns:
        QPropertyAnimation para control.
    """
    widget.setGraphicsEffect(None)
    anim = QPropertyAnimation(widget, b"windowOpacity")
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    if on_finished:
        anim.finished.connect(on_finished)
    anim.start()
    return anim


def animate_fade_out(
    widget: QWidget,
    duration: int = 200,
    on_finished: Optional[Callable] = None
) -> QPropertyAnimation:
    """Animar fade-out de un widget (1 → 0 opacidad).

    Args:
        widget: Widget a animar.
        duration: Duración en milisegundos.
        on_finished: Callback al terminar.

    Returns:
        QPropertyAnimation para control.
    """
    anim = QPropertyAnimation(widget, b"windowOpacity")
    anim.setDuration(duration)
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    if on_finished:
        anim.finished.connect(on_finished)
    anim.start()
    return anim


def animate_glow_pulse(
    widget: QPushButton,
    color: str = "#00d4aa",
    interval_ms: int = 1500
) -> QTimer:
    """Crear efecto de glow pulsante en un botón.

    Args:
        widget: Botón a animar.
        color: Color del glow en hex.
        interval_ms: Intervalo del pulso.

    Returns:
        QTimer que controla el pulso (llamar stop() para detener).
    """
    base_style = widget.styleSheet()
    glow_style = base_style + f"""
        QPushButton {{
            border: 2px solid {color};
            box-shadow: 0 0 8px {color};
        }}
    """

    timer = QTimer(widget)
    pulse_state = [False]

    def _toggle_pulse():
        pulse_state[0] = not pulse_state[0]
        if pulse_state[0]:
            widget.setStyleSheet(glow_style)
        else:
            widget.setStyleSheet(base_style)

    timer.timeout.connect(_toggle_pulse)
    timer.start(interval_ms)
    return timer


def animate_slide_in(
    widget: QWidget,
    start_x: int = 100,
    duration: int = 300,
    on_finished: Optional[Callable] = None
) -> QPropertyAnimation:
    """Animar slide-in desde la derecha.

    Args:
        widget: Widget a deslizar.
        start_x: Posición X inicial (offset desde la derecha).
        duration: Duración en milisegundos.
        on_finished: Callback al terminar.

    Returns:
        QPropertyAnimation para control.
    """
    orig_pos = widget.pos()
    widget.move(orig_pos.x() + start_x, orig_pos.y())

    anim = QPropertyAnimation(widget, b"pos")
    anim.setDuration(duration)
    anim.setStartValue(widget.pos())
    anim.setEndValue(orig_pos)
    anim.setEasingCurve(QEasingCurve.Type.OutBack)
    if on_finished:
        anim.finished.connect(on_finished)
    anim.start()
    return anim


def animate_color_transition(
    widget: QWidget,
    property_name: str,
    start_color: QColor,
    end_color: QColor,
    duration: int = 200
) -> QPropertyAnimation:
    """Animar transición de color.

    Args:
        widget: Widget a animar.
        property_name: Propiedad de color (ej. "palette").
        start_color: Color inicial.
        end_color: Color final.
        duration: Duración en milisegundos.

    Returns:
        QPropertyAnimation para control.
    """
    palette = widget.palette()
    anim = QPropertyAnimation(widget, b"palette")
    anim.setDuration(duration)
    anim.setStartValue(palette)
    
    end_palette = QPalette(palette)
    end_palette.setColor(QPalette.ColorRole.Button, end_color)
    anim.setEndValue(end_palette)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()
    return anim


def animate_height_expand(
    widget: QWidget,
    target_height: int,
    duration: int = 200
) -> QPropertyAnimation:
    """Animar expansión vertical de un widget.

    Args:
        widget: Widget a expandir.
        target_height: Altura final en píxeles.
        duration: Duración en milisegundos.

    Returns:
        QPropertyAnimation para control.
    """
    anim = QPropertyAnimation(widget, b"maximumHeight")
    anim.setDuration(duration)
    anim.setStartValue(widget.height())
    anim.setEndValue(target_height)
    anim.setEasingCurve(QEasingCurve.Type.OutQuad)
    anim.start()
    return anim


def animate_group_parallel(
    animations: list,
    on_finished: Optional[Callable] = None
) -> QParallelAnimationGroup:
    """Ejecutar múltiples animaciones en paralelo.

    Args:
        animations: Lista de QPropertyAnimation.
        on_finished: Callback cuando todas terminan.

    Returns:
        QParallelAnimationGroup.
    """
    group = QParallelAnimationGroup()
    for anim in animations:
        group.addAnimation(anim)
    if on_finished:
        group.finished.connect(on_finished)
    group.start()
    return group
