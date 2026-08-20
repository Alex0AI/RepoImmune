from __future__ import annotations

import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for finding in report.get("findings", []):
    path = str(finding["path"]).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    title = str(finding["title"]).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    message = str(finding["reason"]).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(
        f"::error file={path},line={max(1, int(finding['line']))},title=RepoImmune: {title}::{message}"
    )
