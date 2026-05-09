from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APPROVED_GRID_BY_PAGE: dict[int, set[int]] = {
    1: {4, 5, 7, 10},
    2: {14, 15, 18, 20},
    3: {25, 26, 28, 30},
    4: {34, 35, 36, 37, 38},
    14: {44, 45, 46, 48, 49, 50},
    15: {53, 55, 56, 57, 58, 59},
}

APPROVED_TABLE_CELL_ITEMS = {
    76, 80, 84, 99, 100, 101, 103, 104,
}

REJECTED_READING_ORDER_ITEMS = {107, 108, 109}
REJECTED_REGEX_ITEMS = {168, 170, 172}
APPROVED_ELEMENT_GROUNDED_ITEMS = {
    148,  # scanned formula block anchor
    149,  # scanned formula block anchor
    150,  # scanned formula block anchor
    151,  # scanned formula block anchor
    152,  # scanned formula block anchor
    153,  # scanned formula block anchor
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _page_from_case_id(case_id: str) -> int:
    try:
        return int(case_id.rsplit("_p", 1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"Unexpected batch2 case_id: {case_id}") from exc


def _decide(item: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    index = int(item["index"])
    a_type = item["type"]
    params = item.get("params", {})
    page = _page_from_case_id(item["case_id"])

    if a_type == "formula_contains":
        return (
            "approve",
            params,
            "Visible source formula and high diagnostic value for OCR/LaTeX fidelity.",
        )

    if a_type == "element_grounded":
        if index not in APPROVED_ELEMENT_GROUNDED_ITEMS:
            return (
                "reject",
                params,
                "Reject: visible but low-signal grounding anchor; Batch2 keeps only a small representative grounding subset.",
            )
        return (
            "approve",
            params,
            "Visible structural anchor kept as part of a small representative grounding subset.",
        )

    if a_type == "regex_absence":
        if index in REJECTED_REGEX_ITEMS:
            return (
                "reject",
                params,
                "Reject: this visible scan-area label is document content, not a header/footer artifact.",
            )
        return (
            "approve",
            params,
            "Visible running header/footer or plausible OCR artifact guard; appropriate pollution check.",
        )

    if a_type == "reading_order":
        if index in REJECTED_READING_ORDER_ITEMS:
            return (
                "reject",
                params,
                "Reject: the proposed anchors are not both visible on the generated source page.",
            )
        return (
            "approve",
            params,
            "Visible anchors with meaningful top-to-bottom or section ordering.",
        )

    if a_type == "table_grid_cell":
        if index in APPROVED_GRID_BY_PAGE.get(page, set()):
            return (
                "approve",
                params,
                "High-value grid-position check for a specific numeric/value cell.",
            )
        return (
            "reject",
            params,
            "Reject as redundant or low-signal grid cell; stronger grid checks on this page are already kept.",
        )

    if a_type == "table_cell_exists":
        if index in APPROVED_TABLE_CELL_ITEMS:
            return (
                "approve",
                params,
                "Specific table value worth keeping as a format-independent cell-existence check.",
            )
        return (
            "reject",
            params,
            "Reject: duplicate of kept grid checks, weak standalone label/value, or ordinary prose term miscast as a table cell.",
        )

    return "reject", params, "Reject: unsupported or out-of-scope assertion type for Batch2 strict import."


def build_review(args: argparse.Namespace) -> dict[str, Any]:
    packet_path = Path(args.packet)
    packet = _load_json(packet_path)
    items = packet.get("items", [])
    now = datetime.now(timezone.utc).isoformat()

    decisions: list[dict[str, Any]] = []
    for item in items:
        decision, edited_params, notes = _decide(item)
        decisions.append(
            {
                "index": item["index"],
                "case_id": item["case_id"],
                "title": item.get("title", ""),
                "type": item["type"],
                "original_params": item.get("params", {}),
                "decision": decision,
                "edited_params": edited_params,
                "edited_params_text": json.dumps(edited_params, ensure_ascii=False, indent=2),
                "edited_params_parse_error": "",
                "notes": notes,
                "document_path": item.get("document_path", ""),
                "document_page": item.get("document_page", ""),
                "updated_at": now,
                "reviewer": args.reviewer,
            }
        )

    counts = Counter(d["decision"] for d in decisions)
    by_type = Counter(d["type"] for d in decisions if d["decision"] in {"approve", "edit"})
    payload = {
        "summary": {
            "source": packet_path.name,
            "reviewer": args.reviewer,
            "standard": (
                "community-strict batch2: source-visible, high-signal, no invisible anchors, "
                "limited redundant table cells, representative spatial grounding only, "
                "balanced structural coverage"
            ),
            "exported_at": now,
            "item_count": len(items),
            "reviewed_count": len(decisions),
            "counts": dict(counts),
            "accepted_by_type": dict(sorted(by_type.items())),
            "notes": (
                "Suggested Codex strict pass. It intentionally trims redundant table cells and rejects "
                "invalid reading-order anchors and low-signal grounding anchors before temporary import."
            ),
        },
        "decisions": decisions,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = Path(args.md)
    if args.md:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_render_md(payload), encoding="utf-8")

    if args.prefill_html:
        _write_prefill_html(Path(args.html), Path(args.prefill_html), payload, args.storage_key)

    return payload["summary"]


def _render_md(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Stage6 Batch2 Codex Strict Review",
        "",
        f"- Items: {summary['item_count']}",
        "- Decisions: "
        + ", ".join(f"{k}={v}" for k, v in sorted(summary["counts"].items())),
        "",
        "## Accepted By Type",
        "",
    ]
    for a_type, count in summary["accepted_by_type"].items():
        lines.append(f"- `{a_type}`: {count}")
    lines.extend(["", "## Rejections Worth Human Spot-Check", ""])
    for decision in payload["decisions"]:
        if decision["decision"] != "reject":
            continue
        if decision["type"] in {"reading_order", "table_grid_cell", "table_cell_exists"}:
            lines.append(
                f"- #{decision['index']} `{decision['case_id']}` `{decision['type']}` "
                f"{json.dumps(decision['original_params'], ensure_ascii=False)} — {decision['notes']}"
            )
    lines.append("")
    return "\n".join(lines)


def _write_prefill_html(
    html_path: Path,
    out_path: Path,
    payload: dict[str, Any],
    storage_key: str,
) -> None:
    html = html_path.read_text(encoding="utf-8")
    prefill: dict[str, dict[str, Any]] = {}
    for decision in payload["decisions"]:
        prefill[str(decision["index"])] = {
            "index": decision["index"],
            "case_id": decision["case_id"],
            "type": decision["type"],
            "decision": decision["decision"],
            "edited_params_text": decision["edited_params_text"],
            "notes": decision["notes"],
            "updated_at": decision["updated_at"],
        }

    replacement = (
        f"const storageKey = {json.dumps(storage_key)};\n"
        f"const codexPrefill = {json.dumps(prefill, ensure_ascii=False, indent=2)};\n"
        "let decisions = loadDecisions();\n"
        "if (Object.keys(decisions).length === 0) {\n"
        "  decisions = codexPrefill;\n"
        "  localStorage.setItem(storageKey, JSON.stringify(decisions));\n"
        "}\n"
    )
    marker_start = 'const storageKey = "docfailbench.review.batch2.v2";\nlet decisions = loadDecisions();\n'
    if marker_start not in html:
        marker_start = "let decisions = loadDecisions();\n"
        replacement = (
            f"const codexPrefill = {json.dumps(prefill, ensure_ascii=False, indent=2)};\n"
            "let decisions = loadDecisions();\n"
            "if (Object.keys(decisions).length === 0) {\n"
            "  decisions = codexPrefill;\n"
            "  localStorage.setItem(storageKey, JSON.stringify(decisions));\n"
            "}\n"
        )
    html = html.replace(marker_start, replacement, 1)
    html = html.replace(
        '<div class="subline" id="summary-line">Loading packet...</div>',
        '<div class="subline" id="summary-line">Codex strict prefill loaded; your edits in this copy override suggestions.</div>',
        1,
    )
    out_path.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--packet",
        default="runs/stage6_annotation/review_packet_batch2/review_packet_batch2.json",
    )
    parser.add_argument(
        "--html",
        default="runs/stage6_annotation/review_packet_batch2/review_packet_batch2.html",
    )
    parser.add_argument(
        "--out",
        default="runs/stage6_annotation/review_packet_batch2/codex_review_decisions_batch2.json",
    )
    parser.add_argument(
        "--md",
        default="runs/stage6_annotation/review_packet_batch2/codex_review_decisions_batch2.md",
    )
    parser.add_argument(
        "--prefill-html",
        default="runs/stage6_annotation/review_packet_batch2/review_packet_batch2_codex_prefilled.html",
    )
    parser.add_argument("--reviewer", default="codex_strict_v3_grounding_subset")
    parser.add_argument("--storage-key", default="docfailbench.review.batch2.codex_strict_v3_grounding_subset")
    args = parser.parse_args()
    print(json.dumps(build_review(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
