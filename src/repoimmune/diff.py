from __future__ import annotations

import re

from .models import DiffLine

_HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(?:\s*(.*))?$")


def parse_unified_diff(text: str) -> list[DiffLine]:
    path = ""
    old_line = new_line = 0
    symbol: str | None = None
    result: list[DiffLine] = []
    for raw in text.splitlines():
        if raw.startswith("+++ "):
            candidate = raw[4:].strip()
            path = candidate[2:] if candidate.startswith("b/") else candidate
            continue
        match = _HUNK.match(raw)
        if match:
            old_line, new_line = int(match.group(1)), int(match.group(2))
            symbol = (match.group(3) or "").strip() or None
            continue
        if not path or raw.startswith(("diff --git", "--- ")):
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            result.append(DiffLine(path, new_line, raw[1:], "add", symbol))
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            result.append(DiffLine(path, old_line, raw[1:], "delete", symbol))
            old_line += 1
        else:
            old_line += 1
            new_line += 1
    return result
