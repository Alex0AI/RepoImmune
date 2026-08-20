from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .capsule import replay_capsule
from .checker import check_diff
from .storage import find_memory_root, load_cards, search_cards

TOOLS = [
    "search_past_failures",
    "explain_code_history",
    "check_patch_against_memory",
    "list_invariants_for_file",
    "get_regression_test",
    "replay_behavior_case",
]


def dispatch(name: str, arguments: dict[str, Any], memory: Path) -> Any:
    cards = load_cards(memory)
    if name == "search_past_failures":
        return [
            {"score": score, "card": card}
            for score, card in search_cards(
                cards, str(arguments.get("query", "")), int(arguments.get("limit", 5))
            )
        ]
    if name == "explain_code_history":
        path = str(arguments.get("path", ""))
        return [
            card
            for card in cards
            if any(item.get("path") == path for item in card.get("affected_symbols", []))
        ]
    if name == "check_patch_against_memory":
        return check_diff(str(arguments.get("diff", "")), cards).to_dict()
    if name == "list_invariants_for_file":
        path = str(arguments.get("path", ""))
        return [
            {"id": card["id"], "invariant": card["invariant"], "evidence": card["evidence"]}
            for card in cards
            if any(item.get("path") == path for item in card.get("affected_symbols", []))
        ]
    if name == "get_regression_test":
        return next(
            card["regression_tests"] for card in cards if card["id"] == arguments.get("card_id")
        )
    if name == "replay_behavior_case":
        return replay_capsule(memory / "capsules" / str(arguments["capsule_id"]))
    raise KeyError(name)


def _tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": name.replace("_", " "),
            "inputSchema": {"type": "object", "additionalProperties": True},
        }
        for name in TOOLS
    ]


def main() -> int:
    memory = find_memory_root(Path.cwd())
    for line in sys.stdin:
        try:
            request = json.loads(line)
            method = request.get("method")
            request_id = request.get("id")
            if method == "initialize":
                result: Any = {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "repoimmune", "version": "0.1.0"},
                }
            elif method == "tools/list":
                result = {"tools": _tool_definitions()}
            elif method == "tools/call":
                params = request.get("params", {})
                value = dispatch(params["name"], params.get("arguments", {}), memory)
                result = {
                    "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}],
                    "structuredContent": value,
                }
            else:
                raise KeyError(str(method))
            print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}), flush=True)
        except Exception as exc:  # MCP boundary: return sanitized error, keep server alive
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": locals().get("request_id"),
                        "error": {"code": -32603, "message": str(exc)[:300]},
                    }
                ),
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
