from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_id(batch_label: str, index: int, assertion_type: str) -> str:
    safe_label = "".join(
        char if char.isalnum() or char in ("_", "-") else "_"
        for char in batch_label.strip()
    ).strip("_-") or "batch"
    return f"human_{safe_label}_{index:03d}_{assertion_type}"


def build_reviewed(args: argparse.Namespace) -> dict[str, Any]:
    decisions_payload = _load_json(Path(args.decisions))
    decisions = decisions_payload.get("decisions", [])

    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    accepted = 0
    edited = 0
    rejected = 0

    for decision in decisions:
        status = str(decision.get("decision", "")).strip().lower()
        if status == "reject":
            rejected += 1
            continue
        if status not in {"approve", "edit"}:
            continue

        assertion_type = decision["type"]
        params = decision.get("edited_params") or decision.get("original_params") or {}
        rationale = decision.get("notes", "")
        index = int(decision["index"])
        case_id = decision["case_id"]
        candidate: dict[str, Any] = {
            "proposed_id": _candidate_id(args.batch_label, index, assertion_type),
            "type": assertion_type,
            "severity": "major",
            "params": params,
            "rationale": rationale,
            "source": args.source,
            "status": "accepted",
            "review_index": index,
        }
        if status == "edit":
            edited += 1
            candidate["assertion"] = {
                "type": assertion_type,
                "severity": "major",
                "params": params,
                "description": rationale,
                "tags": ["human_reviewed", args.batch_label, "codex_strict_edit"],
            }
        else:
            accepted += 1
            candidate["tags"] = ["human_reviewed", args.batch_label, "codex_strict"]
        by_case[case_id].append(candidate)

    records = []
    for case_id in sorted(by_case):
        candidates = by_case[case_id]
        records.append({
            "case_id": case_id,
            "candidate_assertions": candidates,
            "review": {
                "status": args.accepted_status,
                "reviewed_by": args.reviewer,
                "rationale": f"Human-style strict review accepted {len(candidates)} candidate assertion(s).",
            },
        })

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )

    summary = {
        "source": args.decisions,
        "out": args.out,
        "record_count": len(records),
        "accepted": accepted,
        "edited": edited,
        "rejected": rejected,
        "importable_assertions": accepted + edited,
        "accepted_status": args.accepted_status,
        "batch_label": args.batch_label,
        "reviewer": args.reviewer,
    }
    if args.summary:
        Path(args.summary).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--decisions",
        default="runs/stage6_annotation/review_packet_batch1/codex_review_decisions_batch1.json",
    )
    parser.add_argument(
        "--out",
        default="runs/stage6_annotation/reviewed_human_batch1.jsonl",
    )
    parser.add_argument(
        "--summary",
        default="runs/stage6_annotation/reviewed_human_batch1_summary.json",
    )
    parser.add_argument("--accepted-status", default="accepted_human_batch1")
    parser.add_argument("--batch-label", default="batch1")
    parser.add_argument("--source", default="human:codex_strict_v1")
    parser.add_argument("--reviewer", default="codex_strict_v1")
    args = parser.parse_args()
    print(json.dumps(build_reviewed(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
