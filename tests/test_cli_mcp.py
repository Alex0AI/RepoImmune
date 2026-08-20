from __future__ import annotations

import json
from pathlib import Path

from repoimmune.cli import main
from repoimmune.mcp import TOOLS, dispatch

ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT / "examples" / "memory"


def test_cli_init_validate_recall_explain_replay(tmp_path: Path, capsys) -> None:
    assert main(["init", str(tmp_path)]) == 0
    assert (tmp_path / ".repoimmune" / "cards" / "astropy-12907.json").is_file()
    assert main(["validate", str(tmp_path / ".repoimmune" / "cards" / "astropy-12907.json")]) == 0
    assert main(["recall", "nested matrix", "--memory", str(MEMORY)]) == 0
    assert "astropy-12907" in capsys.readouterr().out
    assert main(["explain", "astropy-12907-nested-separability", "--memory", str(MEMORY)]) == 0
    assert main(["replay", "astropy-12907", "--memory", str(MEMORY)]) == 0


def test_cli_check_formats_and_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    diff = ROOT / "examples" / "reintroduce-astropy-12907.diff"
    output = tmp_path / "result.json"
    assert (
        main(
            [
                "check",
                "--diff",
                str(diff),
                "--memory",
                str(MEMORY),
                "--format",
                "json",
                "--output",
                str(output),
            ]
        )
        == 2
    )
    data = json.loads(output.read_text())
    assert data["findings"]
    assert main(["report", "--input", "repoimmune-report.json", "--output", "report.html"]) == 0
    assert (tmp_path / "report.html").is_file()


def test_cli_errors_are_nonzero(tmp_path: Path) -> None:
    assert main(["validate", str(tmp_path / "missing.json")]) == 1


def test_mcp_all_tools_return_structured_data() -> None:
    diff = (ROOT / "examples" / "reintroduce-astropy-12907.diff").read_text()
    values = {
        "search_past_failures": {"query": "separability"},
        "explain_code_history": {"path": "astropy/modeling/separable.py"},
        "check_patch_against_memory": {"diff": diff},
        "list_invariants_for_file": {"path": "astropy/modeling/separable.py"},
        "get_regression_test": {"card_id": "astropy-12907-nested-separability"},
        "replay_behavior_case": {"capsule_id": "astropy-12907"},
    }
    for tool in TOOLS:
        assert dispatch(tool, values[tool], MEMORY)
