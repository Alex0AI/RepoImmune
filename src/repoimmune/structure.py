from __future__ import annotations

import ast
import io
import re
import textwrap
import tokenize
from difflib import SequenceMatcher
from pathlib import Path

_JS_TOKEN = re.compile(r"(?:[A-Za-z_$][\w$]*|\d+(?:\.\d+)?|===|!==|=>|&&|\|\||\?\?|.)")


class _NamesToSlots(ast.NodeTransformer):
    def visit_Name(self, node: ast.Name) -> ast.AST:  # noqa: N802
        return ast.copy_location(ast.Name(id="$ID", ctx=node.ctx), node)

    def visit_arg(self, node: ast.arg) -> ast.AST:  # noqa: N802
        return ast.copy_location(ast.arg(arg="$ARG", annotation=None, type_comment=None), node)


def _parse_python_fragment(source: str) -> ast.AST | None:
    source = textwrap.dedent(source).strip()
    attempts = [
        source,
        "def _fragment():\n" + "\n".join("    " + line for line in source.splitlines()),
    ]
    for attempt in attempts:
        try:
            return ast.parse(attempt)
        except SyntaxError:
            continue
    return None


def python_fingerprint(source: str) -> str:
    tree = _parse_python_fragment(source)
    if tree is None:
        return ""
    normalized = _NamesToSlots().visit(tree)
    ast.fix_missing_locations(normalized)
    return ast.dump(normalized, annotate_fields=True, include_attributes=False)


def python_calls(source: str) -> list[str]:
    tree = _parse_python_fragment(source)
    if tree is None:
        return []
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
    return sorted(set(calls))


def _python_tokens(source: str) -> list[str]:
    try:
        stream = tokenize.generate_tokens(io.StringIO(source).readline)
        return [
            token.string
            for token in stream
            if token.type
            not in {
                tokenize.ENCODING,
                tokenize.ENDMARKER,
                tokenize.INDENT,
                tokenize.DEDENT,
                tokenize.NEWLINE,
                tokenize.NL,
            }
        ]
    except (tokenize.TokenError, IndentationError):
        return source.split()


def structural_tokens(source: str, path: str = "") -> list[str]:
    suffix = Path(path).suffix.lower()
    if suffix == ".py":
        fingerprint = python_fingerprint(source)
        return (
            fingerprint.replace("(", " ").replace(")", " ").replace(",", " ").split()
            if fingerprint
            else _python_tokens(source)
        )
    if suffix in {".ts", ".tsx"}:
        try:
            from .typescript import analyze_typescript

            language = "tsx" if suffix == ".tsx" else "typescript"
            fingerprint = analyze_typescript(source, language).fingerprint
            return fingerprint.replace("(", " ").replace(")", " ").replace(",", " ").split()
        except (ImportError, RuntimeError):
            pass
    return [token for token in _JS_TOKEN.findall(source) if not token.isspace()]


def structural_similarity(left: str, right: str, path: str = "") -> float:
    a = structural_tokens(left, path)
    b = structural_tokens(right, path)
    if not a or not b:
        return 0.0
    return SequenceMatcher(a=a, b=b, autojunk=False).ratio()
