import os, sys
os.environ["QT_API"] = "pyside6"
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
import qtawesome as qta

# All names from Icons class
checks = [
    ("PLAY", "fa5s.play"), ("PAUSE", "fa5s.pause"), ("STOP", "fa5s.stop"),
    ("RECORD", "fa5s.dot-circle"), ("RECORD_ACTIVE", "fa5s.dot-circle"),
    ("REWIND", "fa5s.fast-backward"), ("FAST_FORWARD", "fa5s.fast-forward"),
    ("SKIP_BACK", "fa5s.step-backward"), ("SKIP_FORWARD", "fa5s.step-forward"),
    ("LOOP", "fa5s.retweet"), ("LOOP_ONE", "fa5s.repeat"), ("SHUFFLE", "fa5s.random"),
    ("MUTE", "fa5s.volume-mute"), ("VOLUME_LOW", "fa5s.volume-down"),
    ("VOLUME_MED", "fa5s.volume-up"), ("VOLUME_HIGH", "fa5s.volume-up"),
    ("METRONOME", "fa5s.music"), ("ARM", "fa5s.microphone-alt"),
    ("SOLO", "fa5s.circle"), ("MUTE_ALT", "fa5s.times-circle"),
    ("UNDO", "fa5s.undo"), ("REDO", "fa5s.redo"),
    ("CUT", "fa5s.cut"), ("COPY", "fa5s.copy"), ("PASTE", "fa5s.paste"),
    ("DELETE", "fa5s.trash-alt"), ("SAVE", "fa5s.save"),
    ("OPEN", "fa5s.folder-open"), ("NEW_FILE", "fa5s.file-alt"),
    ("EDIT", "fa5s.pencil-alt"), ("TRASH", "fa5s.trash-alt"),
    ("SEARCH", "fa5s.search"),
    ("TOOL_DRAW", "fa5s.pencil-alt"), ("TOOL_ERASE", "fa5s.eraser"),
    ("TOOL_SELECT", "fa5s.mouse-pointer"), ("TOOL_LINE", "fa5s.vector-square"),
    ("TOOL_ZOOM", "fa5s.search-plus"), ("TOOL_SNAP", "fa5s.magnet"),
    ("PIANO", "fa5s.piano"), ("GUITAR", "fa5s.guitar"),
    ("DRUMS", "fa5s.drum"), ("SYNTH", "fa5s.wave-square"),
    ("MICROPHONE", "fa5s.microphone"), ("SPEAKER", "fa5s.volume-up"),
    ("HEADPHONES", "fa5s.headphones"), ("EFFECTS", "fa5s.sliders-h"),
    ("WAVEFORM", "fa5s.wave-square"), ("MIDI", "fa5s.plug"),
    ("SETTINGS", "fa5s.cog"), ("INFO", "fa5s.info-circle"),
    ("HELP", "fa5s.question-circle"), ("CLOSE", "fa5s.times"),
    ("MINIMIZE", "fa5s.window-minimize"), ("MAXIMIZE", "fa5s.window-maximize"),
    ("RESTORE", "fa5s.window-restore"), ("MENU", "fa5s.bars"),
    ("MORE", "fa5s.ellipsis-h"), ("DROP_DOWN", "fa5s.chevron-down"),
    ("DROP_UP", "fa5s.chevron-up"), ("EXPAND", "fa5s.chevron-right"),
    ("COLLAPSE", "fa5s.chevron-down"), ("PIN", "fa5s.thumbtack"),
    ("LOCK", "fa5s.lock"), ("UNLOCK", "fa5s.lock-open"),
    ("CHECK", "fa5s.check"), ("CROSS", "fa5s.times"),
    ("STAR", "fa5s.star"), ("STAR_EMPTY", "fa5.star"),
    ("ARROW_UP", "fa5s.arrow-up"), ("ARROW_DOWN", "fa5s.arrow-down"),
    ("ARROW_LEFT", "fa5s.arrow-left"), ("ARROW_RIGHT", "fa5s.arrow-right"),
    ("PLUS", "fa5s.plus"), ("MINUS", "fa5s.minus"),
    ("DOT", "fa5s.circle"), ("BPM", "fa5s.music"),
    ("TIME", "fa5s.clock"), ("TAG", "fa5s.tag"),
    ("FOLDER", "fa5s.folder"), ("FILE_AUDIO", "fa5s.file-audio"),
    ("FILE_MIDI", "fa5s.file-audio"), ("FILE_PROJECT", "fa5s.file-alt"),
    ("REFRESH", "fa5s.sync-alt"), ("CLOSE_CIRCLE", "fa5s.times-circle"),
    ("CHECK_CIRCLE", "fa5s.check-circle"), ("WARNING", "fa5s.exclamation-triangle"),
]

failed = []
for label, name in checks:
    try:
        qta.icon(name)
    except Exception as e:
        failed.append(f"{label} ({name}): {e}")

sys.stderr.write(f"Checked {len(checks)} icons\n")
if failed:
    sys.stderr.write(f"FAILED ({len(failed)}):\n")
    sys.stderr.write("\n".join(failed) + "\n")
else:
    sys.stderr.write("ALL ICONS VALID\n")
sys.stderr.flush()
