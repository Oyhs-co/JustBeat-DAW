import sys
from PySide6.QtWidgets import QApplication
import qtawesome as qta

app = QApplication(sys.argv)
print("QApp created")
try:
    icon = qta.icon('fa5s.play')
    print("fa5s.play: OK")
except Exception as e:
    print(f"fa5s.play: ERROR - {e}")

try:
    icon = qta.icon('fa.play')
    print("fa.play: OK")
except Exception as e:
    print(f"fa.play: ERROR - {e}")

try:
    icon = qta.icon('fas.play')
    print("fas.play: OK")
except Exception as e:
    print(f"fas.play: ERROR - {e}")

try:
    icon = qta.icon('fa6s.play')
    print("fa6s.play: OK")
except Exception as e:
    print(f"fa6s.play: ERROR - {e}")

i = qta._instance()
print(f"fontids: {i.fontids}")
print(f"fontname: {i.fontname}")
charmap_keys = list(i.charmap.keys())
print(f"charmap keys: {charmap_keys[:20]}")
