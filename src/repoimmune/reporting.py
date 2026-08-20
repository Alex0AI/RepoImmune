from __future__ import annotations

import html
import json
from pathlib import Path

from .models import CheckReport


def to_markdown(report: CheckReport) -> str:
    icon = "✅" if report.passed else "🛡️"
    lines = [
        f"# {icon} RepoImmune patch check",
        "",
        f"Checked {report.files_checked} files against {report.cards_checked} behavior cards.",
        "",
    ]
    if not report.findings:
        lines.append("No evidence-backed historical regression was detected.")
    for finding in report.findings:
        lines.extend(
            [
                f"## {finding.severity.upper()}: {finding.title}",
                "",
                f"`{finding.path}:{finding.line}` — {finding.reason}",
                "",
                f"```\n{finding.matched_code}\n```",
                "",
                "Source evidence: "
                + ", ".join(f"[source]({url})" for url in finding.evidence_urls),
                "",
            ]
        )
    return "\n".join(lines)


def to_sarif(report: CheckReport) -> dict[str, object]:
    rules = {
        finding.card_id: {
            "id": finding.card_id,
            "name": finding.title,
            "shortDescription": {"text": finding.reason},
        }
        for finding in report.findings
    }
    results = [
        {
            "ruleId": finding.card_id,
            "level": "error" if finding.severity in {"critical", "high"} else "warning",
            "message": {"text": finding.reason + " Evidence: " + ", ".join(finding.evidence_urls)},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": finding.path},
                        "region": {"startLine": max(1, finding.line)},
                    }
                }
            ],
        }
        for finding in report.findings
    ]
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "RepoImmune",
                        "version": report.engine_version,
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }


def write_html(report: CheckReport, output: Path) -> None:
    cards = (
        "".join(
            f'<article class="finding {html.escape(item.severity)}"><span>{html.escape(item.severity.upper())}</span>'
            f"<h2>{html.escape(item.title)}</h2><p>{html.escape(item.reason)}</p>"
            f"<code>{html.escape(item.path)}:{item.line}</code><pre>{html.escape(item.matched_code)}</pre>"
            + "".join(
                f'<a href="{html.escape(url)}">source evidence ↗</a>' for url in item.evidence_urls
            )
            + "</article>"
            for item in report.findings
        )
        or '<article class="finding pass"><h2>No historical regression detected</h2></article>'
    )
    payload = html.escape(json.dumps(report.to_dict(), ensure_ascii=False))
    document = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>RepoImmune report</title><style>
body{{margin:0;background:#07110e;color:#eafff5;font:16px system-ui}}main{{max-width:1040px;margin:auto;padding:48px 24px}}header{{border:1px solid #1c4d3b;background:linear-gradient(135deg,#0b211a,#101829);padding:32px;border-radius:20px}}h1{{font-size:3rem;margin:.2em 0}}.metric{{color:#58f2ac;font-weight:700}}.finding{{margin-top:24px;padding:24px;border:1px solid #2d6651;border-radius:16px;background:#0b1915}}.critical,.high{{border-color:#ff6b6b}}.finding span{{font-size:.75rem;color:#ff8a8a}}pre{{overflow:auto;background:#030806;padding:16px;border-radius:10px}}a{{color:#58f2ac;margin-right:14px}}small{{color:#8da99e}}</style></head><body><main><header><small>BEHAVIOR EVIDENCE REPORT</small><h1>Patch immunity check</h1><p class="metric">{len(report.findings)} findings · {report.cards_checked} memories consulted</p></header>{cards}<script type="application/json" id="report-data">{payload}</script></main></body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
