from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_ACCEPTED_PER_CASE = 3
GROUNDING_KEEP = {
    "public_real_irs_1040_2024_p001",
    "public_real_irs_1040sc_2024_p001",
    "public_real_irs_1040sd_2024_p001",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _weak_text(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 12:
        return True
    if "http" in stripped.lower():
        return True
    if stripped.lower().startswith(("fig.", "table of contents", "list of")):
        return True
    if stripped.endswith((".", ",")) and len(stripped) < 35:
        return True
    if "※" in stripped or "§" in stripped:
        return True
    if re.search(r"[＊�]", stripped):
        return True
    if re.search(r"[\u0370-\u03ff\u0400-\u052f\u1100-\u11ff]", stripped):
        return True
    if re.search(r"[A-Za-z]—[A-Za-z]", stripped):
        return True
    if stripped.endswith("-"):
        return True
    return False


def _decide(item: dict[str, Any], accepted_by_case: dict[str, int]) -> tuple[str, dict[str, Any], str]:
    a_type = item["type"]
    params = item.get("params", {})
    case_id = item["case_id"]

    if accepted_by_case[case_id] >= MAX_ACCEPTED_PER_CASE:
        return "reject", params, "Reject: per-page cap reached; stronger public-real checks are already kept."

    if a_type == "text_presence":
        text = str(params.get("text", ""))
        if _weak_text(text):
            return "reject", params, "Reject: weak, truncated, page-furniture, or OCR-artifact text anchor."
        accepted_by_case[case_id] += 1
        return "approve", params, "Visible public-real content anchor with enough specificity for a smoke check."

    if a_type == "reading_order":
        before = str(params.get("before", ""))
        after = str(params.get("after", ""))
        if _weak_text(before) or _weak_text(after):
            return "reject", params, "Reject: reading-order anchors are weak, truncated, or page furniture."
        accepted_by_case[case_id] += 1
        return "approve", params, "Visible public-real anchors with meaningful top-to-bottom order."

    if a_type == "regex_absence":
        return "reject", params, "Reject for public-real v0.1: proposed absence pattern often matches legitimate source page furniture."

    if a_type == "element_grounded":
        text = str(params.get("text", ""))
        if case_id not in GROUNDING_KEEP or _weak_text(text):
            return "reject", params, "Reject: grounding is downsampled to a few form/layout anchors."
        accepted_by_case[case_id] += 1
        return "approve", params, "Visible public-real form/layout anchor kept for bbox grounding coverage."

    return "reject", params, "Reject: unsupported assertion type for public-real strict import."


def build_review(args: argparse.Namespace) -> dict[str, Any]:
    packet_path = Path(args.packet)
    packet = _load_json(packet_path)
    now = datetime.now(timezone.utc).isoformat()
    accepted_by_case: dict[str, int] = defaultdict(int)
    decisions = []
    for item in packet.get("items", []):
        decision, edited_params, notes = _decide(item, accepted_by_case)
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
    by_type = Counter(d["type"] for d in decisions if d["decision"] == "approve")
    payload = {
        "summary": {
            "source": packet_path.name,
            "reviewer": args.reviewer,
            "standard": "public-real strict v1: visible anchors, limited per-page count, low-signal grounding/absence downsampled",
            "exported_at": now,
            "item_count": len(decisions),
            "reviewed_count": len(decisions),
            "counts": dict(counts),
            "accepted_by_type": dict(sorted(by_type.items())),
            "accepted_case_count": len({d["case_id"] for d in decisions if d["decision"] == "approve"}),
        },
        "decisions": decisions,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_lines = [
        "# Public Real Strict Review",
        "",
        f"- Items: {len(decisions)}",
        "- Decisions: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
        "",
        "## Accepted By Type",
        "",
    ]
    for key, value in sorted(by_type.items()):
        md_lines.append(f"- `{key}`: {value}")
    Path(args.md).write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return payload["summary"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", default="runs/stage6_public_real/review_packet_public_real/review_packet_public_real.json")
    parser.add_argument("--out", default="runs/stage6_public_real/review_packet_public_real/codex_review_decisions_public_real.json")
    parser.add_argument("--md", default="runs/stage6_public_real/review_packet_public_real/codex_review_decisions_public_real.md")
    parser.add_argument("--reviewer", default="codex_public_real_strict_v1")
    args = parser.parse_args()
    print(json.dumps(build_review(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
