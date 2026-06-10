import os
os.environ["QT_API"] = "pyside6"
import sys
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

import qtawesome as qta
from src.presentation.styles.icons import Icons

failed = []
for name in dir(Icons):
    if name.startswith("_"):
        continue
    if name in ("TIME_SEPARATOR", "BEAT_DOT", "PLAY_TEXT", "PAUSE_TEXT", "STOP_TEXT", "RECORD_TEXT", "REWIND_TEXT", "FORWARD_TEXT"):
        continue
    val = getattr(Icons, name)
    if hasattr(val, "_name"):
        try:
            qta.icon(val._name)
        except Exception as e:
            failed.append(f"FAIL: {name} ({val._name}): {e}")

sys.stderr.write(f"Tested {len(dir(Icons))} icons\n")
if failed:
    sys.stderr.write("\n".join(failed) + "\n")
else:
    sys.stderr.write("All icons OK\n")
sys.stderr.flush()
