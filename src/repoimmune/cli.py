from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .capsule import replay_capsule
from .checker import check_diff
from .miner import mine_candidates
from .reporting import to_markdown, to_sarif, write_html
from .schema import load_card
from .storage import find_memory_root, load_cards, search_cards

_SAFE_REF = re.compile(r"^[A-Za-z0-9._~^/@{}+-]+$")


def _bundled_memory() -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "memory"


def _read_diff(value: str, cwd: Path) -> str:
    candidate = Path(value)
    if candidate.is_file():
        return candidate.read_text(encoding="utf-8")
    if value == "-":
        return sys.stdin.read()
    if not _SAFE_REF.fullmatch(value):
        raise ValueError("unsafe git ref; pass a diff file instead")
    completed = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--unified=3", value],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "git diff failed")
    return completed.stdout


def command_init(path: Path) -> int:
    root = path.resolve()
    memory = root / ".repoimmune"
    (memory / "cards").mkdir(parents=True, exist_ok=True)
    (memory / "capsules").mkdir(exist_ok=True)
    config = memory / "config.json"
    if not config.exists():
        config.write_text(
            json.dumps({"schema_version": "1.0.0", "read_only": True}, indent=2) + "\n",
            encoding="utf-8",
        )
    demo = _bundled_memory()
    if demo.exists() and not any((memory / "cards").glob("*.json")):
        shutil.copytree(demo / "cards", memory / "cards", dirs_exist_ok=True)
        shutil.copytree(demo / "capsules", memory / "capsules", dirs_exist_ok=True)
    print(f"Initialized behavior memory at {memory}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repoimmune", description="Executable memory of bugs your repository already fixed"
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("path", nargs="?", default=".")
    mine = sub.add_parser("mine")
    mine.add_argument("--repo", required=True)
    mine.add_argument("--limit", type=int, default=30)
    mine.add_argument("--output", default="repoimmune-candidates.json")
    check = sub.add_parser("check")
    check.add_argument("--diff", required=True)
    check.add_argument("--memory")
    check.add_argument("--format", choices=["json", "markdown", "sarif"], default="markdown")
    check.add_argument("--output")
    recall = sub.add_parser("recall")
    recall.add_argument("query")
    recall.add_argument("--memory")
    recall.add_argument("--limit", type=int, default=5)
    explain = sub.add_parser("explain")
    explain.add_argument("card_id")
    explain.add_argument("--memory")
    replay = sub.add_parser("replay")
    replay.add_argument("capsule_id")
    replay.add_argument("--memory")
    report = sub.add_parser("report")
    report.add_argument("--input", default="repoimmune-report.json")
    report.add_argument("--output", default="repoimmune-report.html")
    report.add_argument("--format", choices=["html"], default="html")
    validate = sub.add_parser("validate")
    validate.add_argument("card")
    return parser


def _memory(value: str | None) -> Path:
    return Path(value).resolve() if value else find_memory_root(Path.cwd())


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            return command_init(Path(args.path))
        if args.command == "mine":
            data = mine_candidates(args.repo, args.limit)
            Path(args.output).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print(
                f"Saved {len(data)} conservative candidates to {args.output}; no cards were claimed."
            )
            return 0
        if args.command == "check":
            report = check_diff(_read_diff(args.diff, Path.cwd()), load_cards(_memory(args.memory)))
            value = (
                json.dumps(
                    to_sarif(report) if args.format == "sarif" else report.to_dict(), indent=2
                )
                if args.format != "markdown"
                else to_markdown(report)
            )
            if args.output:
                Path(args.output).write_text(value + "\n", encoding="utf-8")
            else:
                print(value)
            Path("repoimmune-report.json").write_text(
                json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8"
            )
            return 0 if report.passed else 2
        if args.command == "recall":
            for score, card in search_cards(
                load_cards(_memory(args.memory)), args.query, args.limit
            ):
                print(f"{score:.2f}\t{card['id']}\t{card['title']}")
            return 0
        if args.command == "explain":
            cards = {card["id"]: card for card in load_cards(_memory(args.memory))}
            print(json.dumps(cards[args.card_id], indent=2, ensure_ascii=False))
            return 0
        if args.command == "replay":
            result = replay_capsule(_memory(args.memory) / "capsules" / args.capsule_id)
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 3
        if args.command == "report":
            raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
            from .models import CheckReport, Finding

            report = CheckReport(
                [Finding(**item) for item in raw["findings"]],
                raw["cards_checked"],
                raw["files_checked"],
                raw.get("engine_version", "0.1.0"),
            )
            write_html(report, Path(args.output))
            print(f"Wrote {args.output}")
            return 0
        if args.command == "validate":
            card = load_card(Path(args.card))
            print(f"valid {card['id']} {card['content_hash']}")
            return 0
    except (FileNotFoundError, KeyError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"repoimmune: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
