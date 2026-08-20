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


def capsule_content_hash(capsule_dir: Path) -> str:
    """Hash every regular file while excluding the manifest's self-referential hash field."""
    root = capsule_dir.resolve()
    digest = hashlib.sha256()
    manifest_path = root / "capsule.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = manifest.get("files")
    if declared is not None:
        if not isinstance(declared, list) or any(not isinstance(item, str) for item in declared):
            raise CapsuleError("capsule files must be a list of relative paths")
        files = [manifest_path]
        for item in declared:
            candidate = root / item
            if Path(item).is_absolute() or not _inside(root, candidate) or not candidate.is_file():
                raise CapsuleError("capsule files must be existing local relative files")
            files.append(candidate)
    else:
        files = [
            path
            for path in root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and not path.name.endswith((".pyc", ".pyo"))
        ]
    files = sorted(set(files), key=lambda p: p.relative_to(root).as_posix())
    for path in files:
        if path.is_symlink() or not _inside(root, path):
            raise CapsuleError("capsule contains an unsafe link or path")
        relative = path.relative_to(root).as_posix()
        payload = path.read_bytes()
        if relative == "capsule.json":
            canonical_manifest = json.loads(payload)
            canonical_manifest.pop("content_hash", None)
            payload = json.dumps(
                canonical_manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        else:
            try:
                payload = payload.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
            except UnicodeDecodeError:
                pass
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(payload)).encode("ascii"))
        digest.update(b"\0")
        digest.update(payload)
    return "sha256:" + digest.hexdigest()


def replay_capsule(capsule_dir: Path, timeout: int = 20) -> dict[str, Any]:
    root = capsule_dir.resolve()
    manifest_path = root / "capsule.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for path in root.rglob("*"):
        if path.is_symlink() or not _inside(root, path):
            raise CapsuleError("capsule contains an unsafe link or path")
    content_hash = capsule_content_hash(root)
    expected_hash = manifest.get("content_hash")
    if expected_hash is not None and expected_hash != content_hash:
        raise CapsuleError("capsule content hash mismatch")
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
        "content_hash": content_hash,
    }
