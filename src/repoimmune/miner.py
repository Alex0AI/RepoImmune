from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_TEST_PATH = re.compile(r"(^|/)(tests?|__tests__)(/|$)|(?:test|spec)\.[jt]sx?$", re.IGNORECASE)


def stable_patch_id(patch: str) -> str:
    """Hash semantic patch lines while ignoring hunk positions and Git metadata."""
    lines = []
    for line in patch.replace("\r\n", "\n").splitlines():
        if line.startswith(("@@", "index ", "diff --git", "--- ", "+++ ")):
            continue
        if line.startswith(("+", "-")):
            lines.append(line.rstrip())
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def _request(url: str, token: str | None = None) -> Any:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "RepoImmune/0.1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)  # noqa: S310 - fixed HTTPS API URL
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            if int(response.headers.get("Content-Length", "0")) > 10_000_000:
                raise ValueError("GitHub response exceeds 10MB safety limit")
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise RuntimeError("GitHub API rate-limited; retry later or set GITHUB_TOKEN") from exc
        raise RuntimeError(f"GitHub API returned {exc.code}") from exc


def mine_candidates(
    repository: str, limit: int = 30, token: str | None = None
) -> list[dict[str, Any]]:
    if not _REPO.fullmatch(repository) or not 1 <= limit <= 100:
        raise ValueError("repository must be owner/name and limit must be 1..100")
    query = urllib.parse.quote(f"repo:{repository} is:pr is:merged (fix OR bug OR regression)")
    data = _request(
        f"https://api.github.com/search/issues?q={query}&per_page={limit}",
        token or os.getenv("GITHUB_TOKEN"),
    )
    seen: set[int] = set()
    seen_patches: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for item in data.get("items", []):
        number = int(item["number"])
        if number in seen:
            continue
        seen.add(number)
        details = _request(
            f"https://api.github.com/repos/{repository}/pulls/{number}",
            token or os.getenv("GITHUB_TOKEN"),
        )
        files_value = _request(
            f"https://api.github.com/repos/{repository}/pulls/{number}/files?per_page=100",
            token or os.getenv("GITHUB_TOKEN"),
        )
        files = files_value if isinstance(files_value, list) else []
        patches = [str(file.get("patch", "")) for file in files if isinstance(file, dict)]
        patch_id = stable_patch_id("\n".join(patches)) if patches else ""
        if patch_id and patch_id in seen_patches:
            continue
        if patch_id:
            seen_patches.add(patch_id)
        production = [
            str(file.get("filename"))
            for file in files
            if isinstance(file, dict) and not _TEST_PATH.search(str(file.get("filename", "")))
        ]
        tests = [
            str(file.get("filename"))
            for file in files
            if isinstance(file, dict) and _TEST_PATH.search(str(file.get("filename", "")))
        ]
        title = str(item["title"])
        body = str(details.get("body", "")) if isinstance(details, dict) else ""
        is_revert = title.lower().startswith("revert") or "reverts " in body.lower()
        candidates.append(
            {
                "repository": repository,
                "pr": number,
                "url": item["html_url"],
                "title": title,
                "state": item["state"],
                "base_sha": details.get("base", {}).get("sha") if isinstance(details, dict) else None,
                "head_sha": details.get("head", {}).get("sha") if isinstance(details, dict) else None,
                "fixed_commit": details.get("merge_commit_sha") if isinstance(details, dict) else None,
                "patch_id": patch_id or None,
                "production_files": production,
                "test_files": tests,
                "test_evidence_present": bool(tests),
                "revert": is_revert,
                "evidence_class": "heuristic",
                "reason": (
                    "candidate has production and test changes; replay and causal review required"
                    if production and tests
                    else "incomplete production/test evidence; no Behavior Card claimed"
                ),
                "mined_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return candidates
