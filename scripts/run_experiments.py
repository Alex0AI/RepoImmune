from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repoimmune.checker import check_diff  # noqa: E402
from repoimmune.schema import load_card  # noqa: E402
from repoimmune.storage import search_cards  # noqa: E402


def mutation_diff(card: dict, *, test_delete: bool = False) -> str:
    if test_delete:
        test = card["regression_tests"][0]
        return f"diff --git a/{test['path']} b/{test['path']}\n--- a/{test['path']}\n+++ b/{test['path']}\n@@ -1 +0,0 @@\n-assert regression_behavior\n"
    symbol = card["affected_symbols"][0]
    path = symbol["path"]
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@ {symbol['symbol']}\n-{card['fixed_pattern']['code']}\n+{card['buggy_pattern']['code']}\n"


def refactor_diff(card: dict) -> str:
    symbol = card["affected_symbols"][0]
    path = symbol["path"]
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@ {symbol['symbol']}\n-{card['fixed_pattern']['code']}\n+{card['fixed_pattern']['code']}  # retained by refactor\n"


def rate(values: list[bool]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> int:
    cards = [load_card(path) for path in sorted((ROOT / "research" / "cards").glob("*.json"))]
    candidates = json.loads((ROOT / "research" / "candidates.json").read_text(encoding="utf-8"))
    reversions = [not check_diff(mutation_diff(card), cards).passed for card in cards]
    refactors = [not check_diff(refactor_diff(card), cards).passed for card in cards]
    test_deletions = [
        not check_diff(mutation_diff(card, test_delete=True), cards).passed
        for card in cards
        if card["regression_tests"]
    ]
    reciprocal: list[float] = []
    recall_at_5: list[bool] = []
    for card in cards:
        query = " ".join(card["title"].split()[:6])
        ranked = [item[1]["id"] for item in search_cards(cards, query, 10)]
        rank = ranked.index(card["id"]) + 1 if card["id"] in ranked else 0
        reciprocal.append(1 / rank if rank else 0)
        recall_at_5.append(bool(rank and rank <= 5))
    evidence_fields = [
        all(
            [
                card.get("evidence"),
                card.get("source_commit"),
                card.get("fixed_commit"),
                card.get("regression_tests"),
                card.get("buggy_pattern"),
                card.get("fixed_pattern"),
            ]
        )
        for card in cards
    ]
    repo_count = len({item["repository"] for item in candidates})
    results = {
        "generated_from": "research snapshot and deterministic mutations; no LLM judging",
        "candidate_count": len(candidates),
        "behavior_card_count": len(cards),
        "repository_count": repo_count,
        "capsule_count": len(list((ROOT / "research" / "capsules").glob("*/capsule.json"))),
        "experiments": {
            "mining_precision": {
                "classification": "inconclusive",
                "n": 0,
                "reason": "No independent manual labeling round was completed; SWE-bench Verified membership is not reused as a precision label.",
            },
            "evidence_coverage": {
                "classification": "externally_reported",
                "n": len(cards),
                "complete_rate": rate(evidence_fields),
            },
            "retrieval": {
                "classification": "heuristic",
                "n": len(cards),
                "recall_at_5": rate(recall_at_5),
                "mrr": statistics.mean(reciprocal) if reciprocal else 0,
            },
            "known_reversion_detection": {
                "classification": "verified",
                "n": len(reversions),
                "rate": rate(reversions),
            },
            "normal_refactor_false_positive": {
                "classification": "verified",
                "n": len(refactors),
                "rate": rate(refactors),
            },
            "test_assertion_deletion_detection": {
                "classification": "verified",
                "n": len(test_deletions),
                "rate": rate(test_deletions),
            },
            "ablation": {
                "classification": "heuristic",
                "n": len(cards),
                "rule_only": rate([bool(card["affected_symbols"]) for card in cards]),
                "text_only_recall_at_5": rate(recall_at_5),
                "ast_only_reversion": rate(reversions),
                "hybrid_reversion_or_test": rate(reversions + test_deletions),
            },
            "agent_ab": {
                "classification": "inconclusive",
                "n": 0,
                "reason": "Not run: no claim is made without equal-task/model/config/budget trials.",
            },
        },
        "limitations": [
            "Mutation results measure deliberate exact historical reversions, not arbitrary future semantic regressions.",
            "Generated card invariants are conservative and externally reported, not human semantic annotations.",
            "Retrieval queries reuse title terms and therefore do not estimate natural user-query performance.",
            "Structural capsules are not full upstream behavioral replays.",
        ],
    }
    output = ROOT / "research" / "results.json"
    output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    md = [
        "# Experiment results",
        "",
        f"Generated candidates: **{len(candidates)}**; Behavior Cards: **{len(cards)}**; repositories: **{repo_count}**.",
        "",
        "| Experiment | n | Result | Class |",
        "|---|---:|---:|---|",
    ]
    for name, value in results["experiments"].items():
        metric = next(
            (f"{key}={number:.3f}" for key, number in value.items() if isinstance(number, float)),
            value.get("reason", "see JSON"),
        )
        md.append(
            f"| {name.replace('_', ' ')} | {value.get('n', '—')} | {metric} | {value['classification']} |"
        )
    md.extend(["", "## Limitations", "", *[f"- {item}" for item in results["limitations"]]])
    (ROOT / "research" / "RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
