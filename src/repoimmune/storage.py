from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from .schema import CardValidationError, load_card

_WORD = re.compile(r"[a-zA-Z_][\w.-]+")


def find_memory_root(start: Path) -> Path:
    candidate = start.resolve()
    for base in (candidate, *candidate.parents):
        if (base / ".repoimmune").is_dir():
            return base / ".repoimmune"
    bundled = Path(__file__).resolve().parents[2] / "examples" / "memory"
    if bundled.is_dir():
        return bundled
    raise FileNotFoundError("no .repoimmune directory found; run `repoimmune init .`")


def load_cards(memory_root: Path) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for path in sorted((memory_root / "cards").glob("*.json")):
        try:
            cards.append(load_card(path))
        except CardValidationError:
            raise
    return cards


def _terms(value: Any) -> list[str]:
    return [word.lower() for word in _WORD.findall(json.dumps(value, ensure_ascii=False))]


def search_cards(
    cards: list[dict[str, Any]], query: str, limit: int = 5
) -> list[tuple[float, dict[str, Any]]]:
    query_terms = set(_terms(query))
    if not query_terms:
        return []
    documents = [set(_terms(card)) for card in cards]
    frequencies = {term: sum(term in doc for doc in documents) for term in query_terms}
    scored: list[tuple[float, dict[str, Any]]] = []
    for card, terms in zip(cards, documents, strict=True):
        score = sum(
            (1.0 + math.log((len(cards) + 1) / (frequencies[term] + 1)))
            for term in query_terms
            if term in terms
        )
        title_terms = set(_terms(card.get("title", "")))
        score += 1.5 * len(query_terms & title_terms)
        if score:
            scored.append((score, card))
    return sorted(scored, key=lambda item: (-item[0], item[1]["id"]))[:limit]
