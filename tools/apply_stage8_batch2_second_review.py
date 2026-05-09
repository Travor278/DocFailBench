from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "runs" / "stage8_non_gov_public_batch2"
CASES_PATH = STAGE / "reviewed_non_gov_public_batch2_cases.json"
FIRST_REVIEW_PATH = STAGE / "stage8_codex_first_review.json"
SECOND_REVIEW_JSON = STAGE / "stage8_human_second_review_accepted.json"
SECOND_REVIEW_MD = STAGE / "stage8_human_second_review_accepted.md"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply_second_review() -> dict[str, Any]:
    cases_payload = _load(CASES_PATH)
    first_review = _load(FIRST_REVIEW_PATH)
    cases_payload["status"] = "staging_second_review_accepted"
    cases_payload["description"] = (
        "Stage8 non-government public PDF batch2 cases accepted by human second review; "
        "kept as an audit source and included in DocFailBench-v0.1-combined-public-rc."
    )
    cases_payload["review_status"] = {
        "first_review": str(FIRST_REVIEW_PATH.relative_to(ROOT)).replace("\\", "/"),
        "second_review": str(SECOND_REVIEW_JSON.relative_to(ROOT)).replace("\\", "/"),
        "release_status": "included_in_combined_public_rc",
    }
    accepted_decisions = [
        decision
        for decision in first_review["decisions"]
        if decision["decision"] in {"approve", "edit"}
    ]
    accepted_by_key = {
        (
            decision["case_id"],
            decision["final_type"],
            json.dumps(decision["edited_params"], ensure_ascii=False, sort_keys=True),
        ): decision
        for decision in accepted_decisions
    }
    accepted_assertions: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for case in cases_payload["cases"]:
        for assertion in case.get("assertions", []):
            key = (
                case["case_id"],
                assertion["type"],
                json.dumps(assertion.get("params", {}), ensure_ascii=False, sort_keys=True),
            )
            decision = accepted_by_key.get(key)
            if decision is None:
                raise RuntimeError(f"Reviewed assertion missing from first review: {case['case_id']} {assertion['id']}")
            description = assertion.get("description", "")
            if "Human second review accepted:" not in description:
                assertion["description"] = (
                    f"{description} Human second review accepted: user approved Stage8 first-review direction; edits refined for stable gold."
                    if description
                    else "Human second review accepted: user approved Stage8 first-review direction; edits refined for stable gold."
                )
            tags = list(assertion.get("tags", []))
            for tag in ("human_second_review_accepted", "stage8_batch2_gold_candidate"):
                if tag not in tags:
                    tags.append(tag)
            assertion["tags"] = tags
            seen.add(key)
            accepted_assertions.append(
                {
                    "assertion_id": assertion["id"],
                    "case_id": case["case_id"],
                    "type": assertion["type"],
                    "params": assertion.get("params", {}),
                    "source_decision_index": decision["index"],
                    "source_decision": decision["decision"],
                    "page_image": decision.get("page_image", ""),
                    "reason": decision["notes"],
                }
            )

    missing = sorted(set(accepted_by_key) - seen)
    if missing:
        raise RuntimeError(f"Accepted first-review decisions not found in cases: {missing}")

    _dump(CASES_PATH, cases_payload)
    now = datetime.now(timezone.utc).isoformat()
    type_counts = Counter(item["type"] for item in accepted_assertions)
    source_counts = Counter(item["case_id"].removeprefix("non_gov_public_batch2_").rsplit("_p", 1)[0] for item in accepted_assertions)
    payload = {
        "name": "Stage8 batch2 human second review accepted",
        "status": "accepted_first_review_applied_to_staging_cases",
        "generated_at": now,
        "reviewer": "user_human_second_review",
        "basis": "User reviewed Stage8 first-review focus list and approved the accepted/rejected direction in chat; Codex refined edit params before applying.",
        "case_file": str(CASES_PATH.relative_to(ROOT)).replace("\\", "/"),
        "summary": {
            "accepted_assertion_count": len(accepted_assertions),
            "accepted_by_type": dict(sorted(type_counts.items())),
            "accepted_by_source": dict(sorted(source_counts.items())),
            "fail_count": 0,
            "unsure_count": 0,
        },
        "accepted_assertions": accepted_assertions,
    }
    _dump(SECOND_REVIEW_JSON, payload)
    SECOND_REVIEW_MD.write_text(_render_md(payload), encoding="utf-8")
    return payload


def _render_md(payload: dict[str, Any]) -> str:
    lines = [
        "# Stage8 Batch2 Human Second Review Accepted",
        "",
        "Status: accepted first-review assertions applied to staging cases.",
        "",
        f"- Accepted assertions: {payload['summary']['accepted_assertion_count']}",
        "- Fail: 0",
        "- Unsure: 0",
        f"- Case file: `{payload['case_file']}`",
        "",
        "## Accepted By Type",
        "",
        "| Type | Count |",
        "| --- | ---: |",
    ]
    for key, value in payload["summary"]["accepted_by_type"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Accepted Assertions", "", "| Assertion | Case | Type | Params | Reason |", "| --- | --- | --- | --- | --- |"])
    for item in payload["accepted_assertions"]:
        lines.append(
            f"| `{item['assertion_id']}` | `{item['case_id']}` | `{item['type']}` | "
            f"`{json.dumps(item['params'], ensure_ascii=False)}` | {item['reason']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    print(json.dumps(apply_second_review(), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
