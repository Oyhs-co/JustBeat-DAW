import os
os.environ.setdefault("QT_API", "pyside6")

# Access icon BEFORE QApplication exists (like what piano_roll.py does at import time)
import qtawesome as qta
icon1 = qta.icon('fa5s.pencil-alt')
print("Pre-QApp icon access: OK (deferred)")

# Now create QApplication
from PySide6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
print("QApp created")

# Now try accessing another icon
try:
    icon2 = qta.icon('fa5s.file-alt')
    print("fa5s.file-alt (post-QApp): OK")
except Exception as e:
    print(f"fa5s.file-alt (post-QApp): ERROR - {e}")
    import traceback
    traceback.print_exc()

# Try all the icons used in transport_bar
for name in ['fa5s.play', 'fa5s.stop', 'fa5s.dot-circle', 'fa5s.file-alt', 'fa5s.folder-open', 'fa5s.save', 'fa5s.undo', 'fa5s.redo', 'fa5s.search', 'fa5s.music', 'fa5s.sliders-h', 'fa5s.cog', 'fa5s.trash-alt', 'fa5s.cut', 'fa5s.copy', 'fa5s.paste']:
    try:
        qta.icon(name)
        print(f"  {name}: OK")
    except Exception as e:
        print(f"  {name}: ERROR - {e}")

i = qta._instance()
print(f"\nfontids: {i.fontids}")
