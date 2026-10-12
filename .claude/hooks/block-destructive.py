#!/usr/bin/env python3
"""Claude Code PreToolUse hook: refuses edits or commands that drop, truncate, or blanket-delete lakehouse objects.
Exit 2 blocks the tool call and shows the reason to the agent. CREATE OR REPLACE and DELETE ... WHERE are allowed."""
import json
import re
import sys

payload = json.load(sys.stdin)
inp = payload.get("tool_input", {}) or {}
text = "\n".join(str(inp.get(k, "")) for k in ("new_string", "content", "command"))
rules = [
    (r"\bdrop\s+(table|schema|catalog|view|volume)\b", "DROP of a lakehouse object"),
    (r"\btruncate\s+table\b", "TRUNCATE"),
    (r"\bdelete\s+from\s+[\w.]+\s*(;|$)", "DELETE without a WHERE clause"),
    (r"rm\s+-rf\s+(/|~|\$HOME|data/out)\b", "recursive delete of a data folder"),
]
for pattern, why in rules:
    if re.search(pattern, text, re.I | re.M):
        print(f"blocked by .claude/hooks/block-destructive.py: {why}. Use CREATE OR REPLACE, or a DELETE with a WHERE clause.", file=sys.stderr)
        sys.exit(2)
sys.exit(0)
