import os
os.environ["QT_API"] = "pyside6"

import sys
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

import qtawesome as qta

results = []
for p in ["fa5", "fa5s", "fa5r", "fa6", "fa6s", "fa5b"]:
    try:
        qta.icon(p + ".star")
        results.append(f"{p}.star: OK")
    except Exception as e:
        results.append(f"{p}.star: {e}")

i = qta._instance()
results.append(f"fontids: {i.fontids}")

sys.stderr.write("\n".join(results) + "\n")
sys.stderr.flush()

# Now let's check all icon names that fail
# Try the ones from our Icons class
icon_names = [
    ("STAR_EMPTY", "fa5r.star"),
]
for label, name in icon_names:
    try:
        qta.icon(name)
        sys.stderr.write(f"{label} ({name}): OK\n")
    except Exception as e:
        sys.stderr.write(f"{label} ({name}): {e}\n")
