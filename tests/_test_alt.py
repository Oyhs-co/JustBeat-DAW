import os, sys
os.environ["QT_API"] = "pyside6"
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
import qtawesome as qta

loop_alts = ["sync-alt", "redo", "rotate-left", "repeat", "retweet"]
for name in loop_alts:
    try:
        qta.icon("fa5s." + name)
        sys.stderr.write(f"fa5s.{name}: OK\n")
    except Exception as e:
        sys.stderr.write(f"fa5s.{name}: {e}\n")

sys.stderr.write("---\n")
piano_alts = ["keyboard", "music", "guitar", "drum", "sliders-h", "wave-square", "headphones", "microphone", "piano", "inbox", "table", "th", "braille", "dot-circle"]
for name in piano_alts:
    try:
        qta.icon("fa5s." + name)
        sys.stderr.write(f"fa5s.{name}: OK\n")
    except Exception as e:
        sys.stderr.write(f"fa5s.{name}: {e}\n")

sys.stderr.flush()
