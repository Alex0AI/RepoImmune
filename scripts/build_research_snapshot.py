from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repoimmune.diff import parse_unified_diff  # noqa: E402
from repoimmune.schema import seal_card  # noqa: E402

DATASET = "SWE-bench/SWE-bench_Verified"
SOURCE = "https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified"
SAFE_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def get_rows(offset: int, length: int) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "dataset": DATASET,
            "config": "default",
            "split": "test",
            "offset": offset,
            "length": length,
        }
    )
    request = urllib.request.Request(
        "https://datasets-server.huggingface.co/rows?" + query,
        headers={"User-Agent": "RepoImmune/0.1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        if int(response.headers.get("Content-Length", "0")) > 40_000_000:
            raise RuntimeError("dataset response exceeds 40MB safety limit")
        payload = json.load(response)
    return [item["row"] for item in payload.get("rows", [])]


def gh_json(path: str) -> dict[str, Any] | None:
    completed = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    if completed.returncode or not completed.stdout:
        return None
    value = json.loads(completed.stdout)
    return value if isinstance(value, dict) else None


def issue_number(instance_id: str) -> int | None:
    match = re.search(r"-(\d+)$", instance_id)
    return int(match.group(1)) if match else None


def compact(value: str, limit: int = 180) -> str:
    return " ".join(value.replace("\x00", "").split())[:limit]


def category(problem: str) -> str:
    lowered = problem.lower()
    groups = [
        ("null", (" none", "null", "missing value")),
        ("boundary", ("boundary", "off-by-one", "index", "empty")),
        ("pagination", ("pagination", "paginator", " page ")),
        ("cache", ("cache", "cached")),
        ("state", ("state", "session")),
        ("exception", ("exception", "traceback", "raises", "error")),
        ("serialization", ("serializ", " json", " yaml", "pickle")),
        ("async", ("async", "await", "concurren", "race")),
    ]
    return next((name for name, words in groups if any(word in lowered for word in words)), "other")


def first_pair(patch: str) -> tuple[str, str, str, str] | None:
    lines = parse_unified_diff(patch)
    for deleted in lines:
        if deleted.kind != "delete" or not deleted.text.strip():
            continue
        for added in lines:
            if added.kind == "add" and added.path == deleted.path and added.text.strip():
                return (
                    deleted.path,
                    deleted.symbol or "<module>",
                    deleted.text.strip(),
                    added.text.strip(),
                )
    return None


def write_capsule(root: Path, card_id: str, buggy: str, fixed: str, source: str) -> None:
    capsule = root / card_id
    capsule.mkdir(parents=True, exist_ok=True)
    (capsule / "buggy.txt").write_text(buggy + "\n", encoding="utf-8")
    (capsule / "fixed.txt").write_text(fixed + "\n", encoding="utf-8")
    (capsule / "expected.txt").write_text(fixed + "\n", encoding="utf-8")
    (capsule / "test_case.py").write_text(
        "import pathlib,sys\nassert pathlib.Path(sys.argv[1]).read_text() == pathlib.Path(sys.argv[2]).read_text()\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "1.0.0",
        "id": card_id,
        "source": source,
        "environment": {"python": ">=3.10", "dependencies": []},
        "runs": [
            {
                "name": "historical line differs from fixed evidence",
                "args": ["test_case.py", "buggy.txt", "expected.txt"],
                "expected_exit": 1,
            },
            {
                "name": "fixed line matches evidence",
                "args": ["test_case.py", "fixed.txt", "expected.txt"],
                "expected_exit": 0,
            },
        ],
        "provenance": {
            "classification": "heuristic",
            "scope": "structural patch replay only; not upstream behavior execution",
        },
    }
    (capsule / "capsule.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=220)
    parser.add_argument("--cards", type=int, default=120)
    args = parser.parse_args()
    if not 1 <= args.limit <= 500 or not 0 <= args.cards <= args.limit:
        parser.error("--limit must be 1..500 and --cards must be <= limit")
    rows: list[dict[str, Any]] = []
    for offset in range(0, args.limit, 100):
        rows.extend(get_rows(offset, min(100, args.limit - offset)))
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    research = ROOT / "research"
    cards_dir = research / "cards"
    capsules_dir = research / "capsules"
    cards_dir.mkdir(parents=True, exist_ok=True)
    capsules_dir.mkdir(parents=True, exist_ok=True)
    candidates: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    license_cache: dict[str, tuple[str, str]] = {}
    for row in rows:
        repo = str(row.get("repo", ""))
        instance = str(row.get("instance_id", ""))
        number = issue_number(instance)
        if not SAFE_REPO.fullmatch(repo) or number is None:
            continue
        url = f"https://github.com/{repo}/pull/{number}"
        pair = first_pair(str(row.get("patch", "")))
        bug_category = category(str(row.get("problem_statement", "")))
        tests = (
            list(row.get("FAIL_TO_PASS", [])) if isinstance(row.get("FAIL_TO_PASS"), list) else []
        )
        candidates.append(
            {
                "id": instance,
                "repository": repo,
                "source_url": url,
                "source_commit": row.get("base_commit"),
                "has_production_patch": bool(pair),
                "has_test_patch": bool(row.get("test_patch")),
                "fail_to_pass_count": len(tests),
                "classification": "externally_reported",
                "category": bug_category,
                "retrieved_at": now,
                "dataset": SOURCE,
            }
        )
        if len(cards) >= args.cards or not pair or not row.get("test_patch") or not tests:
            continue
        card_id = instance.lower().replace("__", "-").replace("_", "-")
        existing_path = cards_dir / f"{card_id}.json"
        existing = (
            json.loads(existing_path.read_text(encoding="utf-8")) if existing_path.is_file() else {}
        )
        pr = None if existing else gh_json(f"repos/{repo}/pulls/{number}")
        fixed_sha = str(existing.get("fixed_commit") or (pr or {}).get("merge_commit_sha") or "")
        if not re.fullmatch(r"[0-9a-f]{40}", fixed_sha):
            continue
        if repo not in license_cache:
            if existing.get("license"):
                license_cache[repo] = (
                    str(existing["license"].get("spdx") or "NOASSERTION"),
                    str(existing["license"].get("source") or f"https://github.com/{repo}"),
                )
            else:
                license_data = gh_json(f"repos/{repo}/license") or {}
                license_cache[repo] = (
                    str((license_data.get("license") or {}).get("spdx_id") or "NOASSERTION"),
                    str(license_data.get("html_url") or f"https://github.com/{repo}"),
                )
        license_id, license_url = license_cache[repo]
        path, symbol, buggy, fixed = pair
        test_lines = parse_unified_diff(str(row.get("test_patch", "")))
        test_path = next((line.path for line in test_lines if line.kind == "add"), "")
        title = (
            compact(str(row.get("problem_statement", "Historical regression")).splitlines()[0], 120)
            or f"Historical regression {instance}"
        )
        card = seal_card(
            {
                "schema_version": "1.0.0",
                "id": card_id,
                "title": title,
                "bug_trigger": f"A patch changes {path} near {compact(symbol, 80)} back toward the historical deleted structure.",
                "observed_failure": f"SWE-bench Verified records {len(tests)} fail-to-pass test(s): {compact(', '.join(tests), 300)}",
                "affected_symbols": [
                    {"path": path, "symbol": compact(symbol, 120), "language": "python"}
                ],
                "buggy_pattern": {"code": buggy, "kind": "historical_deleted_line", "calls": []},
                "fixed_pattern": {"code": fixed, "kind": "historical_added_line", "calls": []},
                "invariant": "Preserve the fixed structural form at this evidenced path/symbol unless the linked regression tests and applicability are deliberately superseded.",
                "reproducer": {
                    "capsule_id": card_id if len(cards) < 30 else "",
                    "status": "heuristic",
                    "scope": "structural patch replay; upstream behavior externally reported",
                },
                "regression_tests": [
                    {"path": test_path, "name": str(name), "framework": "pytest"}
                    for name in tests[:20]
                ],
                "applicability": {
                    "paths": [path],
                    "symbols": [compact(symbol, 120)],
                    "languages": ["python"],
                    "category": bug_category,
                },
                "evidence": [
                    {"type": "swe_bench_verified", "url": SOURCE, "observed_at": now},
                    {"type": "pull_request", "url": url, "sha": fixed_sha, "observed_at": now},
                    {
                        "type": "base_commit",
                        "url": f"https://github.com/{repo}/commit/{row['base_commit']}",
                        "sha": row["base_commit"],
                        "observed_at": now,
                    },
                ],
                "confidence": {
                    "score": 0.90,
                    "classification": "externally_reported",
                    "rationale": "Human-filtered benchmark record, merged PR, production patch, test patch and fail-to-pass test names are present; upstream tests were not run locally.",
                },
                "limitations": [
                    "Invariant wording is conservative and mechanically generated from the patch, not a semantic human annotation.",
                    "The upstream environment was not executed locally.",
                    "The optional capsule checks structural patch identity only.",
                ],
                "source_commit": row["base_commit"],
                "fixed_commit": fixed_sha,
                "repository": repo,
                "license": {"spdx": license_id, "source": license_url},
                "timestamps": {"reported": row.get("created_at"), "mined": now},
            }
        )
        cards.append(card)
        (cards_dir / f"{card_id}.json").write_text(
            json.dumps(card, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if len(cards) <= 30:
            write_capsule(capsules_dir, card_id, buggy, fixed, url)
    (research / "candidates.json").write_text(
        json.dumps(candidates, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    repositories = sorted({item["repository"] for item in candidates})
    for repository in repositories:
        if repository not in license_cache:
            license_data = gh_json(f"repos/{repository}/license") or {}
            license_cache[repository] = (
                str((license_data.get("license") or {}).get("spdx_id") or "NOASSERTION"),
                str(license_data.get("html_url") or f"https://github.com/{repository}"),
            )
    manifest = {
        "generated_at": now,
        "source": SOURCE,
        "requested_candidates": args.limit,
        "candidates": len(candidates),
        "cards": len(cards),
        "repositories": repositories,
        "licenses": {
            repository: {
                "spdx": license_cache[repository][0],
                "source": license_cache[repository][1],
            }
            for repository in repositories
        },
        "categories": {
            name: sum(item["category"] == name for item in candidates)
            for name in sorted({item["category"] for item in candidates})
        },
        "capsules": min(30, len(cards)),
        "classifications": {
            "cards": "externally_reported",
            "capsules": "heuristic structural replay",
        },
    }
    (research / "snapshot.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if len(candidates) >= 200 and len(cards) >= 100 else 2


if __name__ == "__main__":
    raise SystemExit(main())
