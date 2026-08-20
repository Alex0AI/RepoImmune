from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EvidenceClass = Literal["verified", "externally_reported", "heuristic", "inconclusive"]


@dataclass(frozen=True)
class DiffLine:
    path: str
    line: int
    text: str
    kind: Literal["add", "delete"]
    symbol: str | None = None


@dataclass(frozen=True)
class Finding:
    card_id: str
    title: str
    severity: Literal["critical", "high", "medium", "low"]
    reason: str
    path: str
    line: int
    evidence_urls: list[str]
    matched_code: str
    checks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CheckReport:
    findings: list[Finding]
    cards_checked: int
    files_checked: int
    engine_version: str = "0.1.0"

    @property
    def passed(self) -> bool:
        return not any(item.severity in {"critical", "high"} for item in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "passed": self.passed,
            "cards_checked": self.cards_checked,
            "files_checked": self.files_checked,
            "findings": [item.to_dict() for item in self.findings],
        }
