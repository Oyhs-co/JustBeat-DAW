"""Sistema centralizado de iconos para JustBeat-DAW.

Usa QtAwesome (Font Awesome 5) como proveedor de iconos vectoriales.
Los iconos se cargan de forma lazy para evitar problemas de importación
antes de que exista un QApplication.

Uso:
    from src.presentation.styles.icons import Icons

    button.setIcon(Icons.PLAY)
    button.setIcon(Icons.icon('fa5s.play'))
"""

from typing import Optional


class _IconDescriptor:
    """Descriptor que carga un icono Font Awesome de forma lazy."""
    def __init__(self, name: str):
        self._name = name
        self._icon = None

    def __get__(self, obj, objtype):
        if self._icon is None:
            import qtawesome as qta
            self._icon = qta.icon(self._name)
        return self._icon


class Icons:
    """Iconos vectoriales Font Awesome 5 para la aplicación.

    Cada atributo es un QIcon lazy-loaded.
    """

    # === Transporte ===
    PLAY = _IconDescriptor('fa5s.play')
    PAUSE = _IconDescriptor('fa5s.pause')
    STOP = _IconDescriptor('fa5s.stop')
    RECORD = _IconDescriptor('fa5s.dot-circle')
    RECORD_ACTIVE = _IconDescriptor('fa5s.dot-circle')
    REWIND = _IconDescriptor('fa5s.fast-backward')
    FAST_FORWARD = _IconDescriptor('fa5s.fast-forward')
    SKIP_BACK = _IconDescriptor('fa5s.step-backward')
    SKIP_FORWARD = _IconDescriptor('fa5s.step-forward')
    LOOP = _IconDescriptor('fa5s.retweet')
    LOOP_ONE = _IconDescriptor('fa5s.sync-alt')
    SHUFFLE = _IconDescriptor('fa5s.random')

    # === Estado ===
    MUTE = _IconDescriptor('fa5s.volume-mute')
    VOLUME_LOW = _IconDescriptor('fa5s.volume-down')
    VOLUME_MED = _IconDescriptor('fa5s.volume-up')
    VOLUME_HIGH = _IconDescriptor('fa5s.volume-up')
    METRONOME = _IconDescriptor('fa5s.music')
    ARM = _IconDescriptor('fa5s.microphone-alt')
    SOLO = _IconDescriptor('fa5s.circle')
    MUTE_ALT = _IconDescriptor('fa5s.times-circle')

    # === Edición ===
    UNDO = _IconDescriptor('fa5s.undo')
    REDO = _IconDescriptor('fa5s.redo')
    CUT = _IconDescriptor('fa5s.cut')
    COPY = _IconDescriptor('fa5s.copy')
    PASTE = _IconDescriptor('fa5s.paste')
    DELETE = _IconDescriptor('fa5s.trash-alt')
    SAVE = _IconDescriptor('fa5s.save')
    OPEN = _IconDescriptor('fa5s.folder-open')
    NEW_FILE = _IconDescriptor('fa5s.file-alt')
    EDIT = _IconDescriptor('fa5s.pencil-alt')
    TRASH = _IconDescriptor('fa5s.trash-alt')
    SEARCH = _IconDescriptor('fa5s.search')

    # === Tools ===
    TOOL_DRAW = _IconDescriptor('fa5s.pencil-alt')
    TOOL_ERASE = _IconDescriptor('fa5s.eraser')
    TOOL_SELECT = _IconDescriptor('fa5s.mouse-pointer')
    TOOL_LINE = _IconDescriptor('fa5s.vector-square')
    TOOL_ZOOM = _IconDescriptor('fa5s.search-plus')
    TOOL_SNAP = _IconDescriptor('fa5s.magnet')

    # === Pistas / Instrumentos ===
    PIANO = _IconDescriptor('fa5s.keyboard')
    GUITAR = _IconDescriptor('fa5s.guitar')
    DRUMS = _IconDescriptor('fa5s.drum')
    SYNTH = _IconDescriptor('fa5s.wave-square')
    MICROPHONE = _IconDescriptor('fa5s.microphone')
    SPEAKER = _IconDescriptor('fa5s.volume-up')
    HEADPHONES = _IconDescriptor('fa5s.headphones')
    EFFECTS = _IconDescriptor('fa5s.sliders-h')
    WAVEFORM = _IconDescriptor('fa5s.wave-square')
    MIDI = _IconDescriptor('fa5s.plug')

    # === UI / Navegación ===
    SETTINGS = _IconDescriptor('fa5s.cog')
    INFO = _IconDescriptor('fa5s.info-circle')
    HELP = _IconDescriptor('fa5s.question-circle')
    CLOSE = _IconDescriptor('fa5s.times')
    MINIMIZE = _IconDescriptor('fa5s.window-minimize')
    MAXIMIZE = _IconDescriptor('fa5s.window-maximize')
    RESTORE = _IconDescriptor('fa5s.window-restore')
    MENU = _IconDescriptor('fa5s.bars')
    MORE = _IconDescriptor('fa5s.ellipsis-h')
    DROP_DOWN = _IconDescriptor('fa5s.chevron-down')
    DROP_UP = _IconDescriptor('fa5s.chevron-up')
    EXPAND = _IconDescriptor('fa5s.chevron-right')
    COLLAPSE = _IconDescriptor('fa5s.chevron-down')
    PIN = _IconDescriptor('fa5s.thumbtack')
    LOCK = _IconDescriptor('fa5s.lock')
    UNLOCK = _IconDescriptor('fa5s.lock-open')

    # === Misceláneos ===
    CHECK = _IconDescriptor('fa5s.check')
    CROSS = _IconDescriptor('fa5s.times')
    STAR = _IconDescriptor('fa5s.star')
    STAR_EMPTY = _IconDescriptor('fa5.star')
    ARROW_UP = _IconDescriptor('fa5s.arrow-up')
    ARROW_DOWN = _IconDescriptor('fa5s.arrow-down')
    ARROW_LEFT = _IconDescriptor('fa5s.arrow-left')
    ARROW_RIGHT = _IconDescriptor('fa5s.arrow-right')
    PLUS = _IconDescriptor('fa5s.plus')
    MINUS = _IconDescriptor('fa5s.minus')
    DOT = _IconDescriptor('fa5s.circle')
    BPM = _IconDescriptor('fa5s.music')
    TIME = _IconDescriptor('fa5s.clock')
    TAG = _IconDescriptor('fa5s.tag')
    FOLDER = _IconDescriptor('fa5s.folder')
    FILE_AUDIO = _IconDescriptor('fa5s.file-audio')
    FILE_MIDI = _IconDescriptor('fa5s.file-audio')
    FILE_PROJECT = _IconDescriptor('fa5s.file-alt')
    REFRESH = _IconDescriptor('fa5s.sync-alt')
    CLOSE_CIRCLE = _IconDescriptor('fa5s.times-circle')
    CHECK_CIRCLE = _IconDescriptor('fa5s.check-circle')
    WARNING = _IconDescriptor('fa5s.exclamation-triangle')

    # === Constantes de texto (no iconos) ===
    TIME_SEPARATOR = ":"
    BEAT_DOT = "."
    PLAY_TEXT = ">"
    PAUSE_TEXT = "||"
    STOP_TEXT = "[]"
    RECORD_TEXT = "(O)"
    REWIND_TEXT = "<<"
    FORWARD_TEXT = ">>"


_icon_cache: dict = {}


def icon(name: str, color: Optional[str] = None) -> 'QIcon':
    """Obtener un icono Font Awesome por nombre.

    Args:
        name: Nombre del icono (ej. 'fa5s.play', 'fa5s.music')
        color: Color opcional en hex (ej. '#ff0000')

    Returns:
        QIcon
    """
    import qtawesome as qta
    if color:
        return qta.icon(name, color=color)
    return qta.icon(name)


def icon_button_text(icon_name: str, label: str = "") -> str:
    """Generar texto para botón con icono (legacy - usar setIcon en su lugar).

    Args:
        icon_name: Nombre del icono Font Awesome (no usado, mantenido por compat).
        label: Texto opcional junto al icono.

    Returns:
        String label (el icono se asigna via setIcon).
    """
    return label


def transport_button_style(
    icon_name: str = "",
    color: str = "#a0a0b0",
    active_color: str = "#00d4aa",
    is_active: bool = False
) -> str:
    """Generar stylesheet para botón de transporte.

    Args:
        icon_name: No usado, mantenido por compatibilidad.
        color: Color por defecto.
        active_color: Color cuando activo.
        is_active: Si está activo inicialmente.

    Returns:
        String QSS.
    """
    base_color = active_color if is_active else color
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {base_color};
            border: none;
            font-size: 16px;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.05);
            color: {active_color};
        }}
        QPushButton:pressed {{
            color: {active_color};
            background-color: rgba(0, 212, 170, 0.1);
        }}
    """


def get_track_color(index: int, variant: str = "obsidian") -> str:
    """Obtener color por defecto para una pista según índice.

    Args:
        index: Índice de la pista (0-11).
        variant: Variante de tema.

    Returns:
        Color hex.
    """
    from src.presentation.styles.pro_theme import ProTheme
    colors = ProTheme.get(variant)
    track_list = colors.track_colors
    return track_list[index % len(track_list)]
