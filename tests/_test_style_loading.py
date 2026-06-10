import os
os.environ.setdefault("QT_API", "pyside6")

import sys
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
print("QApp created")

# Load styles like the actual app does
from src.presentation.styles import load_application_styles
load_application_styles(app)
print("Styles loaded")

# Now try icons
import qtawesome as qta
try:
    icon = qta.icon('fa5s.play')
    print("fa5s.play: OK")
except Exception as e:
    print(f"fa5s.play: ERROR - {e}")
    import traceback
    traceback.print_exc()

i = qta._instance()
print(f"fontids: {i.fontids}")
print(f"fontname keys: {list(i.fontname.keys()) if isinstance(i.fontname, dict) else i.fontname}")
