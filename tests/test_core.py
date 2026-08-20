from __future__ import annotations

import json
from pathlib import Path

import pytest

from repoimmune.capsule import CapsuleError, replay_capsule
from repoimmune.checker import check_diff
from repoimmune.diff import parse_unified_diff
from repoimmune.models import CheckReport
from repoimmune.reporting import to_markdown, to_sarif, write_html
from repoimmune.schema import content_hash, load_card, seal_card, validate_card
from repoimmune.storage import load_cards, search_cards
from repoimmune.structure import python_calls, python_fingerprint, structural_similarity

ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT / "examples" / "memory"


def test_real_card_is_valid_and_sealed() -> None:
    card = load_card(MEMORY / "cards" / "astropy-12907.json")
    assert not validate_card(card)
    assert card["content_hash"] == content_hash(card)


def test_validation_rejects_missing_fields_and_bad_confidence() -> None:
    card = seal_card({"schema_version": "0", "confidence": {"score": 2}, "evidence": []})
    errors = validate_card(card)
    assert any("missing required" in error for error in errors)
    assert any("unsupported" in error for error in errors)
    assert any("between" in error for error in errors)


def test_python_structure_is_identifier_insensitive_but_value_sensitive() -> None:
    assert python_fingerprint("x[a:b] = y") == python_fingerprint("left[i:j] = right")
    assert python_fingerprint("x[a:b] = 1") != python_fingerprint("x[a:b] = y")
    assert structural_similarity("x[a:b] = 1", "cright[-right.shape[0]:] = 1", "x.py") > 0.70
    assert python_calls("value = obj.parse(raw); emit(value)") == ["emit", "parse"]
    assert not python_fingerprint("if ???")
    assert python_fingerprint("    target[index] = 1") == python_fingerprint("target[index] = 1")


def test_diff_parser_tracks_paths_lines_and_symbols() -> None:
    diff = (ROOT / "examples" / "reintroduce-astropy-12907.diff").read_text()
    lines = parse_unified_diff(diff)
    assert [(line.kind, line.line) for line in lines] == [("delete", 245), ("add", 245)]
    assert all(line.path == "astropy/modeling/separable.py" for line in lines)
    assert lines[0].symbol == "def _cstack(left, right):"


def test_checker_finds_exact_historical_reversion() -> None:
    cards = load_cards(MEMORY)
    diff = (ROOT / "examples" / "reintroduce-astropy-12907.diff").read_text()
    report = check_diff(diff, cards)
    assert not report.passed
    assert report.findings[0].severity == "critical"
    assert set(report.findings[0].checks) == {
        "historical_buggy_ast_reintroduced",
        "historical_fix_removed",
    }


def test_checker_reports_regression_assertion_deletion() -> None:
    diff = """diff --git a/astropy/modeling/tests/test_separable.py b/astropy/modeling/tests/test_separable.py
--- a/astropy/modeling/tests/test_separable.py
+++ b/astropy/modeling/tests/test_separable.py
@@ -10,1 +10,0 @@ test_case
-    assert actual == expected
"""
    report = check_diff(diff, load_cards(MEMORY))
    assert report.findings[0].checks == ["regression_assertion_removed"]


def test_checker_ignores_unrelated_refactor() -> None:
    diff = """diff --git a/other.py b/other.py
--- a/other.py
+++ b/other.py
@@ -1 +1 @@
-value = build(data)
+result = build(data)
"""
    assert check_diff(diff, load_cards(MEMORY)).passed


def test_search_ranks_relevant_memory() -> None:
    results = search_cards(load_cards(MEMORY), "nested separability matrix")
    assert results and results[0][1]["id"].startswith("astropy-12907")
    assert search_cards(load_cards(MEMORY), "") == []


def test_capsule_replays_buggy_and_fixed_behaviors() -> None:
    result = replay_capsule(MEMORY / "capsules" / "astropy-12907")
    assert result["passed"]
    assert [run["exit_code"] for run in result["runs"]] == [1, 0]


def test_capsule_rejects_absolute_argument(tmp_path: Path) -> None:
    manifest = {
        "id": "bad",
        "runs": [{"name": "bad", "args": [str(tmp_path.resolve())], "expected_exit": 0}],
    }
    (tmp_path / "capsule.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(CapsuleError):
        replay_capsule(tmp_path)


def test_reports_are_evidence_rich(tmp_path: Path) -> None:
    diff = (ROOT / "examples" / "reintroduce-astropy-12907.diff").read_text()
    report = check_diff(diff, load_cards(MEMORY))
    assert "source evidence" in to_markdown(report).lower()
    assert to_sarif(report)["runs"][0]["results"]
    output = tmp_path / "report.html"
    write_html(report, output)
    assert "Patch immunity check" in output.read_text(encoding="utf-8")
    empty = CheckReport([], 1, 0)
    assert "historical regression" in to_markdown(empty).lower()
