from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class CapsuleError(RuntimeError):
    pass


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def replay_capsule(capsule_dir: Path, timeout: int = 20) -> dict[str, Any]:
    root = capsule_dir.resolve()
    manifest_path = root / "capsule.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for path in root.rglob("*"):
        if path.is_symlink() or not _inside(root, path):
            raise CapsuleError("capsule contains an unsafe link or path")
    results: list[dict[str, Any]] = []
    for case in manifest.get("runs", []):
        args = case.get("args", [])
        if not isinstance(args, list) or not args or any(not isinstance(arg, str) for arg in args):
            raise CapsuleError("invalid run arguments")
        for arg in args:
            if Path(arg).is_absolute() or arg.startswith("-") or not _inside(root, root / arg):
                raise CapsuleError("capsule arguments must be local relative files")
        completed = subprocess.run(
            [sys.executable, "-I", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        expected = int(case["expected_exit"])
        results.append(
            {
                "name": case["name"],
                "exit_code": completed.returncode,
                "expected_exit": expected,
                "passed": completed.returncode == expected,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
            }
        )
    return {
        "capsule_id": manifest["id"],
        "passed": bool(results) and all(item["passed"] for item in results),
        "runs": results,
        "content_hash": "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }
