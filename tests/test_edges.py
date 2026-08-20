from __future__ import annotations

import io
import json
import subprocess
import urllib.error
from pathlib import Path

import pytest

import repoimmune.cli as cli
import repoimmune.mcp as mcp
import repoimmune.miner as miner
from repoimmune.capsule import CapsuleError, replay_capsule
from repoimmune.models import CheckReport
from repoimmune.reporting import to_sarif, write_html
from repoimmune.schema import CardValidationError, load_card, validate_card
from repoimmune.storage import find_memory_root, load_cards
from repoimmune.structure import structural_similarity, structural_tokens

ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT / "examples" / "memory"


def test_schema_rejects_bad_json_nonobject_bad_evidence_and_hash(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    with pytest.raises(CardValidationError, match="cannot load"):
        load_card(broken)
    broken.write_text("[]", encoding="utf-8")
    with pytest.raises(CardValidationError, match="JSON object"):
        load_card(broken)
    card = json.loads((MEMORY / "cards" / "astropy-12907.json").read_text(encoding="utf-8"))
    card["evidence"] = [{"url": "http://unsafe.invalid"}]
    card["content_hash"] = "sha256:bad"
    errors = validate_card(card)
    assert any("https URL" in error for error in errors)
    assert any("hash mismatch" in error for error in errors)
    card["confidence"] = "unknown"
    assert any("numeric" in error for error in validate_card(card, verify_hash=False))


def test_storage_discovers_ancestor_and_rejects_invalid_card(tmp_path: Path) -> None:
    memory = tmp_path / ".repoimmune"
    cards = memory / "cards"
    cards.mkdir(parents=True)
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_memory_root(nested) == memory
    (cards / "bad.json").write_text("{}", encoding="utf-8")
    with pytest.raises(CardValidationError):
        load_cards(memory)


def test_structure_supports_javascript_tokens_and_empty_inputs() -> None:
    tokens = structural_tokens("const result = value?.items ?? [];", "sample.ts")
    assert "program" in tokens
    assert "$ID" in tokens
    assert structural_similarity("", "value", "x.js") == 0
    assert structural_tokens("const a=1", "x.js") == structural_tokens("const a=1", "x.js")


def test_capsule_rejects_invalid_and_dash_arguments(tmp_path: Path) -> None:
    manifest = {"id": "bad", "runs": [{"name": "bad", "args": "file.py", "expected_exit": 0}]}
    (tmp_path / "capsule.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(CapsuleError, match="invalid run"):
        replay_capsule(tmp_path)
    manifest["runs"][0]["args"] = ["-c"]
    (tmp_path / "capsule.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(CapsuleError, match="relative files"):
        replay_capsule(tmp_path)


def test_cli_read_diff_file_stdin_git_success_and_fail(tmp_path: Path, monkeypatch) -> None:
    diff_path = tmp_path / "change.diff"
    diff_path.write_text("diff", encoding="utf-8")
    assert cli._read_diff(str(diff_path), tmp_path) == "diff"
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO("stdin diff"))
    assert cli._read_diff("-", tmp_path) == "stdin diff"
    with pytest.raises(ValueError, match="unsafe git ref"):
        cli._read_diff("HEAD;bad", tmp_path)
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "git diff", ""),
    )
    assert cli._read_diff("HEAD~1", tmp_path) == "git diff"
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, "", "bad ref"),
    )
    with pytest.raises(RuntimeError, match="bad ref"):
        cli._read_diff("HEAD~1", tmp_path)


def test_cli_mine_sarif_and_failed_replay(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "mine_candidates", lambda repo, limit: [{"repository": repo}])
    assert cli.main(["mine", "--repo", "owner/project", "--output", "candidates.json"]) == 0
    assert (
        json.loads((tmp_path / "candidates.json").read_text())[0]["repository"] == "owner/project"
    )
    diff = ROOT / "examples" / "reintroduce-astropy-12907.diff"
    assert (
        cli.main(["check", "--diff", str(diff), "--memory", str(MEMORY), "--format", "sarif"]) == 2
    )
    assert '"version": "2.1.0"' in capsys.readouterr().out
    monkeypatch.setattr(cli, "replay_capsule", lambda path: {"passed": False})
    assert cli.main(["replay", "astropy-12907", "--memory", str(MEMORY)]) == 3


class _Response:
    def __init__(self, payload: object, length: int = 10) -> None:
        self.payload = payload
        self.headers = {"Content-Length": str(length)}

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def test_miner_request_limits_errors_and_candidate_dedup(monkeypatch) -> None:
    assert miner.stable_patch_id("@@ -1 +1 @@\n-old\n+new") == miner.stable_patch_id(
        "@@ -99 +42 @@\n-old\n+new"
    )
    monkeypatch.setattr(
        miner.urllib.request, "urlopen", lambda *args, **kwargs: _Response({"ok": True})
    )
    assert miner._request("https://api.github.com/test") == {"ok": True}
    monkeypatch.setattr(
        miner.urllib.request, "urlopen", lambda *args, **kwargs: _Response({}, 20_000_000)
    )
    with pytest.raises(ValueError, match="10MB"):
        miner._request("https://api.github.com/test")
    forbidden = urllib.error.HTTPError("https://api.github.com", 403, "rate", {}, None)
    monkeypatch.setattr(
        miner.urllib.request, "urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(forbidden)
    )
    with pytest.raises(RuntimeError, match="rate-limited"):
        miner._request("https://api.github.com/test")
    server_error = urllib.error.HTTPError("https://api.github.com", 500, "server", {}, None)
    monkeypatch.setattr(
        miner.urllib.request, "urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(server_error)
    )
    with pytest.raises(RuntimeError, match="500"):
        miner._request("https://api.github.com/test")
    monkeypatch.setattr(
        miner,
        "_request",
        lambda *args, **kwargs: {
            "items": [
                {
                    "number": 7,
                    "html_url": "https://github.com/o/r/pull/7",
                    "title": "fix",
                    "state": "closed",
                },
                {
                    "number": 7,
                    "html_url": "https://github.com/o/r/pull/7",
                    "title": "dup",
                    "state": "closed",
                },
            ]
        },
    )
    assert len(miner.mine_candidates("o/r")) == 1
    with pytest.raises(ValueError):
        miner.mine_candidates("unsafe repo", 101)


def test_mcp_main_protocol_and_unknown_tool(monkeypatch, capsys) -> None:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "search_past_failures", "arguments": {"query": "nested"}},
        },
        {"jsonrpc": "2.0", "id": 4, "method": "unknown"},
    ]
    monkeypatch.setattr(mcp, "find_memory_root", lambda path: MEMORY)
    monkeypatch.setattr(
        mcp.sys, "stdin", io.StringIO("\n".join(json.dumps(item) for item in requests))
    )
    assert mcp.main() == 0
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert lines[0]["result"]["serverInfo"]["name"] == "repoimmune"
    assert len(lines[1]["result"]["tools"]) == 6
    assert lines[2]["result"]["structuredContent"]
    assert lines[3]["error"]["code"] == -32603
    with pytest.raises(KeyError):
        mcp.dispatch("missing", {}, MEMORY)


def test_empty_sarif_and_html_pass_state(tmp_path: Path) -> None:
    report = CheckReport([], 0, 0)
    assert to_sarif(report)["runs"][0]["results"] == []
    output = tmp_path / "pass.html"
    write_html(report, output)
    assert "No historical regression detected" in output.read_text(encoding="utf-8")
