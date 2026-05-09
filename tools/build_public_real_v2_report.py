from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


CASES = Path("runs/stage6_public_real/public_real_rc_scored_cases.json")
HYGIENE_CASES = Path("runs/stage6_public_real/public_real_rc_hygiene_cases.json")
PUBLIC_COMPARE = Path("data/releases/docfailbench_v0_1_public_real_rc_public_only_leaderboard.json")
MERGED_COMPARE = Path("data/releases/docfailbench_v0_1_public_real_rc_leaderboard.json")
ENHANCEMENT = Path("runs/stage6_public_real/public_real_v2_enhancement_report.json")
OUT = Path("runs/stage6_public_real/public_real_v2_release_candidate_report.md")

LABELS = {
    "qwen": "Qwen-VL API",
    "plain": "PyMuPDF4LLM plain",
    "paddleocr": "PaddleOCR",
    "mineru": "MinerU",
    "marker": "Marker",
    "docling": "Docling",
    "bbox": "PyMuPDF4LLM bbox",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _leaderboard(path: Path) -> list[dict[str, Any]]:
    data = _load(path)
    rows = []
    for item in data["parsers"]:
        rows.append(
            {
                "label": LABELS.get(item["label"], item["label"]),
                "passed": item["passed"],
                "failed": item["failed"],
                "score": float(item["score"]),
            }
        )
    return sorted(rows, key=lambda row: row["score"], reverse=True)


def _table(rows: list[dict[str, Any]]) -> list[str]:
    lines = ["| Parser | Passed | Failed | Score |", "| --- | ---: | ---: | ---: |"]
    for row in rows:
        lines.append(f"| {row['label']} | {row['passed']} | {row['failed']} | {row['score']:.4f} |")
    return lines


def main() -> int:
    cases = _load(CASES)["cases"]
    hygiene_cases = _load(HYGIENE_CASES)["cases"] if HYGIENE_CASES.exists() else []
    enhancement = _load(ENHANCEMENT)
    type_counts = Counter(a["type"] for c in cases for a in c.get("assertions", []))
    hygiene_count = sum(len(c.get("assertions", [])) for c in hygiene_cases)
    doc_counts = Counter(c["profile"].get("document_type", "unknown") for c in cases)
    source_counts = Counter(Path(c["document"].get("path", "")).name for c in cases)

    lines = [
        "# Public-Real v2 Release Candidate Report",
        "",
        "This report summarizes the stronger public-real staging set built after the initial 54-assertion public-real pass.",
        "",
        "## Scope",
        "",
        f"- Cases: {len(cases)}",
        f"- Main assertions: {sum(len(c.get('assertions', [])) for c in cases)}",
        f"- Secondary hygiene assertions excluded from score: {hygiene_count}",
        f"- Added v2 assertions before hygiene split: {enhancement['added_assertions']}",
        f"- Skipped empty pages: {', '.join(enhancement.get('skipped_empty_cases', [])) or 'none'}",
        "- Formal `data/cases`: not modified",
        "",
        "## Source Mix",
        "",
        "| Source PDF | Cases |",
        "| --- | ---: |",
    ]
    for source, count in sorted(source_counts.items()):
        lines.append(f"| `{source}` | {count} |")

    lines.extend(["", "## Document Types", "", "| Document type | Cases |", "| --- | ---: |"])
    for key, value in sorted(doc_counts.items()):
        lines.append(f"| `{key}` | {value} |")

    lines.extend(["", "## Assertion Mix", "", "| Type | Count |", "| --- | ---: |"])
    for key, value in sorted(type_counts.items()):
        lines.append(f"| `{key}` | {value} |")

    lines.extend(
        [
            "",
            "## Review Standard",
            "",
            "- `table_cell_exists` is the main structural addition because it checks visible form/table content without requiring exact row/column reconstruction.",
            "- `reading_order` is used for visible section and legal-text order where anchors are short and page-local.",
            "- `table_grid_cell` and `table_shape` are limited to the regular NIST SP 800-53 revision table, where the 32x4 grid is visually unambiguous.",
            "- `caption_binding` is limited to the NIST AI RMF figure/caption page because the figure and caption are unique.",
            "- `text_absence` is used only for low-value page furniture and is published as secondary hygiene, excluded from the main RC score.",
            "",
            "## Public-Real Only Baseline",
            "",
        ]
    )
    lines.extend(_table(_leaderboard(PUBLIC_COMPARE)))

    lines.extend(["", "## Merged Diagnostic + Public-Real v2 Baseline", ""])
    lines.extend(_table(_leaderboard(MERGED_COMPARE)))

    lines.extend(
        [
            "",
            "## Freeze Status",
            "",
            "- Frozen RC artifacts now live under `data/releases/docfailbench_v0_1_public_real_rc_*`.",
            "- Spot-check records are in `data/releases/docfailbench_v0_1_public_real_rc_spotcheck.md`.",
            "- Parser version/runtime metadata is in `data/releases/docfailbench_v0_1_public_real_rc_metadata.json`.",
            "- Next release gate: add 20-40 non-government public pages.",
        ]
    )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
