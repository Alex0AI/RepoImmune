from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class TypeScriptAdapterUnavailable(RuntimeError):
    """Raised when the optional tree-sitter adapter was not installed."""


@dataclass(frozen=True)
class TypeScriptStructure:
    language: str
    root_kind: str
    fingerprint: str
    calls: list[str]
    has_errors: bool


def _runtime(language: str) -> tuple[Any, Any]:
    try:
        from tree_sitter import Language, Parser
        from tree_sitter_typescript import language_tsx, language_typescript
    except ImportError as exc:
        raise TypeScriptAdapterUnavailable(
            "install `repoimmune[typescript]` for tree-sitter TypeScript support"
        ) from exc
    grammar = language_tsx() if language == "tsx" else language_typescript()
    parser = Parser(Language(grammar))
    return parser, Language


def _node_fingerprint(node: Any, source: bytes) -> str:
    if node.type in {"identifier", "property_identifier", "shorthand_property_identifier_pattern"}:
        return "$ID"
    if node.child_count == 0:
        text = source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
        return f"{node.type}:{text}" if node.is_named else text
    children = ",".join(_node_fingerprint(child, source) for child in node.children)
    return f"{node.type}({children})"


def analyze_typescript(source: str, language: str = "typescript") -> TypeScriptStructure:
    if language not in {"typescript", "tsx"}:
        raise ValueError("language must be 'typescript' or 'tsx'")
    parser, _ = _runtime(language)
    payload = source.encode("utf-8")
    root = parser.parse(payload).root_node
    calls: list[str] = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == "call_expression":
            function = node.child_by_field_name("function")
            if function is not None:
                calls.append(payload[function.start_byte : function.end_byte].decode("utf-8"))
        stack.extend(reversed(node.children))
    return TypeScriptStructure(
        language=language,
        root_kind=root.type,
        fingerprint=_node_fingerprint(root, payload),
        calls=sorted(set(calls)),
        has_errors=root.has_error,
    )
