import sys
import qtawesome as qta
print("imported", file=sys.stderr)
i = qta._instance()
print(f"fontname: {i.fontname}", file=sys.stderr)
print(f"fontids: {i.fontids}", file=sys.stderr)
print(f"charmap keys: {list(i.charmap.keys())[:10]}", file=sys.stderr)
# Try a few prefixes
for prefix in ['fa', 'fas', 'fa5s', 'fa6s', 'Font Awesome']:
    try:
        icon = qta.icon(f'{prefix}.play')
        print(f"{prefix}.play: OK", file=sys.stderr)
    except Exception as e:
        print(f"{prefix}.play: ERROR - {e}", file=sys.stderr)
