from __future__ import annotations

from typing import Any, Literal

from .diff import parse_unified_diff
from .models import CheckReport, DiffLine, Finding
from .structure import structural_similarity


def _pattern_code(card: dict[str, Any], which: str) -> str:
    pattern = card.get(which, {})
    return str(pattern.get("code", "")) if isinstance(pattern, dict) else str(pattern)


def _evidence_urls(card: dict[str, Any]) -> list[str]:
    return [
        str(item["url"])
        for item in card.get("evidence", [])
        if isinstance(item, dict) and item.get("url")
    ]


def _path_applies(card: dict[str, Any], line: DiffLine) -> bool:
    symbols = card.get("affected_symbols", [])
    paths = {
        str(item.get("path")) for item in symbols if isinstance(item, dict) and item.get("path")
    }
    return not paths or line.path in paths


def check_diff(diff_text: str, cards: list[dict[str, Any]]) -> CheckReport:
    lines = parse_unified_diff(diff_text)
    findings: list[Finding] = []
    for card in cards:
        buggy = _pattern_code(card, "buggy_pattern")
        fixed = _pattern_code(card, "fixed_pattern")
        applicable = [line for line in lines if _path_applies(card, line)]
        added = [line for line in applicable if line.kind == "add"]
        deleted = [line for line in applicable if line.kind == "delete"]
        buggy_matches = [
            line
            for line in added
            if buggy and structural_similarity(line.text, buggy, line.path) >= 0.92
        ]
        fixed_removed = [
            line
            for line in deleted
            if fixed and structural_similarity(line.text, fixed, line.path) >= 0.92
        ]
        for match in buggy_matches:
            checks = ["historical_buggy_ast_reintroduced"]
            severity: Literal["critical", "high", "medium", "low"] = "high"
            reason = "Added code structurally matches the repository's historical buggy form."
            if fixed_removed:
                severity = "critical"
                checks.append("historical_fix_removed")
                reason = "This patch removes the historical fix and restores the old buggy AST structure."
            findings.append(
                Finding(
                    card["id"],
                    card["title"],
                    severity,
                    reason,
                    match.path,
                    match.line,
                    _evidence_urls(card),
                    match.text,
                    checks,
                )
            )
        tests = card.get("regression_tests", [])
        test_paths = {
            str(item.get("path")) for item in tests if isinstance(item, dict) and item.get("path")
        }
        weakened = [
            line
            for line in lines
            if line.kind == "delete"
            and line.path in test_paths
            and ("assert" in line.text or "expect(" in line.text)
        ]
        for match in weakened:
            findings.append(
                Finding(
                    card["id"],
                    card["title"],
                    "high",
                    "A historical regression assertion was removed or weakened.",
                    match.path,
                    match.line,
                    _evidence_urls(card),
                    match.text,
                    ["regression_assertion_removed"],
                )
            )
    unique: dict[tuple[str, str, int, str], Finding] = {}
    for finding in findings:
        unique[(finding.card_id, finding.path, finding.line, finding.reason)] = finding
    return CheckReport(list(unique.values()), len(cards), len({line.path for line in lines}))
