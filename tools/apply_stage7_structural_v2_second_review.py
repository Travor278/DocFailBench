from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGE_DIR = ROOT / "runs" / "stage7_non_gov_public"
CASES_PATH = STAGE_DIR / "reviewed_non_gov_public_cases_structural_v2.json"
FIRST_REVIEW_PATH = STAGE_DIR / "structural_v2_codex_first_review.json"
SECOND_REVIEW_JSON = STAGE_DIR / "structural_v2_human_second_review_accepted.json"
SECOND_REVIEW_MD = STAGE_DIR / "structural_v2_human_second_review_accepted.md"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_second_review() -> dict[str, Any]:
    cases_payload = _load(CASES_PATH)
    first_review = _load(FIRST_REVIEW_PATH)
    prior_review = _load(SECOND_REVIEW_JSON) if SECOND_REVIEW_JSON.exists() else None
    if prior_review:
        edits = {
            item["assertion_id"]: {
                "assertion_id": item["assertion_id"],
                "case_id": item["case_id"],
                "type": item["type"],
                "original_params": item["before"],
                "edited_params": item["after"],
                "notes": item["reason"],
                "page_image": item["page_image"],
            }
            for item in prior_review.get("accepted_edits", [])
        }
    else:
        edits = {
            decision["assertion_id"]: decision
            for decision in first_review["decisions"]
            if decision["decision"] == "edit"
        }
    updated: list[dict[str, Any]] = []
    seen_edits: set[str] = set()

    for case in cases_payload["cases"]:
        for assertion in case.get("assertions", []):
            assertion_id = assertion["id"]
            if assertion_id not in edits:
                continue
            decision = edits[assertion_id]
            before = dict(decision.get("original_params", assertion.get("params", {})))
            after = dict(decision["edited_params"])
            assertion["params"] = after
            description = assertion.get("description", "")
            if "Second review accepted edit:" not in description:
                assertion["description"] = (
                    f"{description} Second review accepted edit: {decision['notes']}"
                    if description
                    else f"Second review accepted edit: {decision['notes']}"
                )
            tags = list(assertion.get("tags", []))
            for tag in ("human_second_review_accepted", "structural_v2_gold_fixed"):
                if tag not in tags:
                    tags.append(tag)
            assertion["tags"] = tags
            seen_edits.add(assertion_id)
            updated.append(
                {
                    "assertion_id": assertion_id,
                    "case_id": case["case_id"],
                    "type": assertion["type"],
                    "before": before,
                    "after": after,
                    "reason": decision["notes"],
                    "page_image": decision["page_image"],
                }
            )

    missing = sorted(set(edits) - seen_edits)
    if missing:
        raise RuntimeError(f"Edited assertions not found in cases: {missing}")

    _dump(CASES_PATH, cases_payload)
    now = datetime.now(timezone.utc).isoformat()
    type_counts = Counter(item["type"] for item in updated)
    payload = {
        "name": "Stage7 structural-v2 human second review accepted edits",
        "status": "accepted_edits_applied_to_staging_cases",
        "generated_at": now,
        "reviewer": "user_human_second_review",
        "basis": "User reviewed Codex first-review edits and approved them in chat.",
        "case_file": str(CASES_PATH.relative_to(ROOT)).replace("\\", "/"),
        "summary": {
            "accepted_edit_count": len(updated),
            "accepted_by_type": dict(sorted(type_counts.items())),
            "fail_count": 0,
            "unsure_count": 0,
        },
        "accepted_edits": updated,
    }
    _dump(SECOND_REVIEW_JSON, payload)

    lines = [
        "# Stage7 Structural-V2 Human Second Review Accepted",
        "",
        "Status: accepted edits applied to staging cases.",
        "",
        f"- Accepted edits: {len(updated)}",
        "- Fail: 0",
        "- Unsure: 0",
        f"- Case file: `{payload['case_file']}`",
        "",
        "## Accepted Edits",
        "",
        "| Assertion | Case | Type | Before | After | Reason |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in updated:
        lines.append(
            f"| `{item['assertion_id']}` | `{item['case_id']}` | `{item['type']}` | "
            f"`{json.dumps(item['before'], ensure_ascii=False)}` | "
            f"`{json.dumps(item['after'], ensure_ascii=False)}` | {item['reason']} |"
        )
    lines.append("")
    SECOND_REVIEW_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


def main() -> int:
    print(json.dumps(apply_second_review(), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
