from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
REQUIRED_FIELDS = {
    "schema_version",
    "id",
    "title",
    "bug_trigger",
    "observed_failure",
    "affected_symbols",
    "buggy_pattern",
    "fixed_pattern",
    "invariant",
    "reproducer",
    "regression_tests",
    "applicability",
    "evidence",
    "confidence",
    "limitations",
    "source_commit",
    "fixed_commit",
    "content_hash",
}


class CardValidationError(ValueError):
    """Raised when a Behavior Card fails deterministic validation."""


def canonical_payload(card: dict[str, Any]) -> bytes:
    payload = {key: value for key, value in card.items() if key != "content_hash"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def content_hash(card: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_payload(card)).hexdigest()


def seal_card(card: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(card)
    sealed["content_hash"] = content_hash(sealed)
    return sealed


def validate_card(card: dict[str, Any], *, verify_hash: bool = True) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - card.keys())
    if missing:
        errors.append("missing required fields: " + ", ".join(missing))
    if card.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"unsupported schema_version: {card.get('schema_version')!r}")
    confidence = card.get("confidence")
    if not isinstance(confidence, dict) or not isinstance(confidence.get("score"), int | float):
        errors.append("confidence.score must be numeric")
    elif not 0 <= float(confidence["score"]) <= 1:
        errors.append("confidence.score must be between 0 and 1")
    evidence = card.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence must contain at least one source")
    elif any(
        not isinstance(item, dict) or not str(item.get("url", "")).startswith("https://")
        for item in evidence
    ):
        errors.append("every evidence item must have an https URL")
    if verify_hash and "content_hash" in card and card["content_hash"] != content_hash(card):
        errors.append("content_hash mismatch")
    return errors


def load_card(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CardValidationError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CardValidationError(f"{path} must contain a JSON object")
    errors = validate_card(value)
    if errors:
        raise CardValidationError(f"{path}: " + "; ".join(errors))
    return value
