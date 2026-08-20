from __future__ import annotations

import pytest

from repoimmune.typescript import analyze_typescript


def test_typescript_tree_sitter_ast_and_calls() -> None:
    left = analyze_typescript("const page = fetchPage(cursor ?? 0); return page.items;")
    right = analyze_typescript("const result = fetchPage(offset ?? 0); return result.items;")
    assert left.root_kind == "program"
    assert not left.has_errors
    assert left.calls == ["fetchPage"]
    assert left.fingerprint == right.fingerprint


def test_tsx_and_invalid_language() -> None:
    result = analyze_typescript("const view = <Panel value={load()} />;", "tsx")
    assert result.calls == ["load"]
    with pytest.raises(ValueError):
        analyze_typescript("x", "javascript")
