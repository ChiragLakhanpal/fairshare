"""diagram-design's skin lint, with one allowed exception: the official AA logo keeps its own colors.

    python3 docs/diagrams/src/lint.py docs/diagrams/0*.html

Fails when any finding lands outside the single line that holds data-brand="aa-logo".
"""
import subprocess
import sys

import aa

files = sys.argv[1:]
run = subprocess.run([sys.executable, str(aa.SCRIPTS / "lint-skin.py"), *files], capture_output=True, text=True)
bad = []
for line in run.stdout.splitlines():
    name, _, rest = line.partition(":")
    num = rest.split(":", 1)[0]
    if not num.isdigit():
        continue  # the summary line
    path = next(f for f in files if f.endswith(name) or name.endswith(f.split("/")[-1]))
    if 'data-brand="aa-logo"' not in open(path, encoding="utf-8").read().splitlines()[int(num) - 1]:
        bad.append(line)
print("\n".join(bad) if bad else f"OK lint: {len(files)} file(s), only the AA logo's own colors are off-palette")
sys.exit(1 if bad else 0)
