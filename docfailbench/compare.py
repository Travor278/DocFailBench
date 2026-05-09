"""Compare multiple DocFailBench results JSON files side by side.

Produces a JSON summary and a Markdown table report. No external dependencies.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def load_result(path: str | Path) -> dict[str, Any]:
    """Load a single DocFailBench results JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def extract_metrics(result: dict[str, Any]) -> dict[str, Any]:
    """Pull the high-level comparison fields out of a results dict."""
    summary = result.get("summary", {})
    return {
        "parser": result.get("parser", "unknown"),
        "score": summary.get("score", 0.0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "assertion_count": summary.get("assertion_count", 0),
        "case_count": summary.get("case_count", 0),
        "failures_by_type": dict(summary.get("failures_by_type", {})),
        "case_scores": dict(summary.get("case_scores", {})),
    }


def compare_results(
    labeled_paths: Mapping[str, str] | Iterable[tuple[str, str]],
) -> dict[str, Any]:
    """Build a comparison summary from multiple results files.

    ``labeled_paths`` may be a mapping or an iterable of ``(label, json_path)``.
    Empty labels fall back to the parser field, then the filename stem.
    """
    entries: list[dict[str, Any]] = []
    items = labeled_paths.items() if isinstance(labeled_paths, Mapping) else labeled_paths
    used_labels: set[str] = set()
    for label, path in items:
        raw = load_result(path)
        metrics = extract_metrics(raw)
        if not label:
            label = metrics["parser"] or Path(path).stem
        label = _dedupe_label(label, used_labels)
        metrics["label"] = label
        entries.append(metrics)

    # Collect the union of all case IDs for per-case comparison.
    all_case_ids: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        for cid in entry["case_scores"]:
            if cid not in seen:
                all_case_ids.append(cid)
                seen.add(cid)

    case_score_rows: list[dict[str, Any]] = []
    for cid in all_case_ids:
        row: dict[str, Any] = {"case_id": cid}
        for entry in entries:
            row[entry["label"]] = entry["case_scores"].get(cid)
        case_score_rows.append(row)

    return {
        "parsers": entries,
        "case_scores": case_score_rows,
    }


def render_markdown(comparison: dict[str, Any]) -> str:
    """Render a comparison dict as a Markdown document."""
    lines: list[str] = []
    parsers = comparison["parsers"]
    labels = [p["label"] for p in parsers]

    # -- Overview table --
    lines.append("# Comparison Report\n")
    lines.append("## Overview\n")
    header = "| Metric | " + " | ".join(labels) + " |"
    sep = "| --- | " + " | ".join(["---"] * len(labels)) + " |"
    lines.append(header)
    lines.append(sep)

    def _row(key: str, fmt: str = "{}") -> None:
        cells = " | ".join(fmt.format(p.get(key, "")) for p in parsers)
        lines.append(f"| {key} | {cells} |")

    _row("score", "{:.4f}")
    _row("passed")
    _row("failed")
    _row("assertion_count")
    _row("case_count")

    # -- Failure type breakdown --
    all_failure_types: list[str] = []
    seen_ft: set[str] = set()
    for p in parsers:
        for ft in p.get("failures_by_type", {}):
            if ft not in seen_ft:
                all_failure_types.append(ft)
                seen_ft.add(ft)

    if all_failure_types:
        lines.append("\n## Failures by Type\n")
        lines.append(header)
        lines.append(sep)
        for ft in all_failure_types:
            cells = " | ".join(
                str(p.get("failures_by_type", {}).get(ft, 0)) for p in parsers
            )
            lines.append(f"| {ft} | {cells} |")

    # -- Per-case score table --
    case_scores = comparison.get("case_scores", [])
    if case_scores:
        lines.append("\n## Per-Case Scores\n")
        case_header = "| Case | " + " | ".join(labels) + " |"
        case_sep = "| --- | " + " | ".join(["---"] * len(labels)) + " |"
        lines.append(case_header)
        lines.append(case_sep)
        for row in case_scores:
            cells = " | ".join(
                _fmt_score(row.get(lbl)) for lbl in labels
            )
            lines.append(f"| {row['case_id']} | {cells} |")

    lines.append("")
    return "\n".join(lines)


def _fmt_score(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.4f}"


def _dedupe_label(label: str, used_labels: set[str]) -> str:
    if label not in used_labels:
        used_labels.add(label)
        return label
    index = 2
    while f"{label}_{index}" in used_labels:
        index += 1
    deduped = f"{label}_{index}"
    used_labels.add(deduped)
    return deduped
