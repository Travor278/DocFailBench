from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "runs" / "stage7_non_gov_public"
RELEASE = ROOT / "data" / "releases"
PREFIX = "docfailbench_v0_1_non_gov_public_stage7_rc"
RELEASE_NAME = "DocFailBench-v0.1-non-gov-public-stage7-rc"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _source_id(case_id: str) -> str:
    return case_id.removeprefix("non_gov_public_").rsplit("_p", 1)[0]


def _write_leaderboard(path: Path, compare: dict[str, Any]) -> None:
    rows = sorted(compare["parsers"], key=lambda row: (-row["score"], row.get("label", "")))
    lines = [
        "# DocFailBench v0.1 Non-Government Public Stage7 RC Leaderboard",
        "",
        "Scope: 24 reviewed non-government public PDF pages / 165 assertions.",
        "",
        "| Parser | Passed | Failed | Score |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(f"| `{row['label']}` | {row['passed']} | {row['failed']} | {row['score']:.4f} |")
    lines.extend(
        [
            "",
            "This is a Stage7-only release candidate. Report it as an auxiliary profile, not as the combined public RC aggregate.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_source_manifest_md(path: Path, source_manifest: dict[str, Any]) -> None:
    lines = [
        "# DocFailBench v0.1 Non-Government Public Stage7 RC Source Manifest",
        "",
        "| Source | Pages | Assertions | License | License status | SHA-256 | Source page |",
        "| --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in source_manifest["sources"]:
        pages = ", ".join(str(page) for page in row.get("selected_stage7_pages", []))
        sha_status = "ok" if row.get("sha256_verified") else "check"
        lines.append(
            f"| `{row['source_id']}` | {pages} | {row.get('stage7_assertion_count', 0)} | "
            f"{row.get('license', '')} | {row.get('license_status', '')} | {sha_status} | {row.get('source_page', '')} |"
        )
    lines.extend(
        [
            "",
            "OpenStax Calculus is CC BY-NC-SA 4.0; keep noncommercial and ShareAlike terms visible in downstream release notes.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_card(
    path: Path,
    release_cases: dict[str, Any],
    compare: dict[str, Any],
    source_manifest: dict[str, Any],
    second_review: dict[str, Any],
) -> None:
    type_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    for case in release_cases["cases"]:
        source_counts[_source_id(case["case_id"])] += 1
        for assertion in case.get("assertions", []):
            type_counts[assertion["type"]] += 1

    source_status = {row["source_id"]: row.get("license_status", "") for row in source_manifest["sources"]}
    rows = sorted(compare["parsers"], key=lambda row: (-row["score"], row.get("label", "")))
    lines = [
        "# DocFailBench v0.1 Non-Government Public Stage7 RC Card",
        "",
        f"`{RELEASE_NAME}` freezes the reviewed Stage7 non-government public PDF subset. It is an auxiliary non-government profile and is also included in `DocFailBench-v0.1-combined-public-rc`.",
        "",
        "## Frozen Artifacts",
        "",
        f"- Cases: `data/releases/{PREFIX}_cases.json`",
        f"- Leaderboard: `data/releases/{PREFIX}_leaderboard.md`",
        f"- Machine-readable leaderboard: `data/releases/{PREFIX}_leaderboard.json`",
        f"- Source/license manifest: `data/releases/{PREFIX}_source_license_manifest.json`",
        f"- Source/license manifest MD: `data/releases/{PREFIX}_source_license_manifest.md`",
        f"- Parser metadata: `data/releases/{PREFIX}_parser_metadata.json`",
        f"- Element-grounded profile: `data/releases/{PREFIX}_element_grounded_profile.json`",
        "",
        "## Scope",
        "",
        f"- Pages/cases: {len(release_cases['cases'])}",
        f"- Assertions: {sum(type_counts.values())}",
        f"- Sources: {len(source_counts)}",
        f"- Parsers: {len(rows)}",
        "",
        "## Source Mix",
        "",
        "| Source | Pages | License status |",
        "| --- | ---: | --- |",
    ]
    for source, count in sorted(source_counts.items()):
        lines.append(f"| `{source}` | {count} | {source_status.get(source, '')} |")

    lines.extend(["", "## Assertion Mix", "", "| Assertion type | Count |", "| --- | ---: |"])
    for key, value in sorted(type_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| `{key}` | {value} |")

    lines.extend(["", "## Leaderboard Snapshot", "", "| Parser | Passed | Failed | Score |", "| --- | ---: | ---: | ---: |"])
    for row in rows:
        lines.append(f"| `{row['label']}` | {row['passed']} | {row['failed']} | {row['score']:.4f} |")

    accepted = second_review.get("summary", {}).get("accepted_edit_count")
    lines.extend(
        [
            "",
            "## Review And Scoring Policy",
            "",
            f"- 165 structural-v2 assertions received Codex first review and human second-review acceptance of all {accepted} edits.",
            "- Stage7 `element_grounded` checks remain in the main score as representative bbox-aware checks.",
            "- Broad page-furniture/header/footer absence checks remain a secondary hygiene profile for future releases.",
            "- OpenStax Calculus is CC BY-NC-SA 4.0; release notes must preserve noncommercial and ShareAlike terms.",
            "",
            "## Not Included",
            "",
            "- Stage8 batch2 is not part of this Stage7-only RC; it is included separately in `DocFailBench-v0.1-combined-public-rc`.",
            "- PubTables-1M and DocLayNet remain metadata-first until redistribution and sample selection are pinned.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def build() -> dict[str, Any]:
    RELEASE.mkdir(parents=True, exist_ok=True)

    case_src = STAGE / "reviewed_non_gov_public_cases_structural_v2.json"
    compare_src = STAGE / "compare_structural_v2_7parser.json"
    source_manifest_src = STAGE / "stage7_source_license_manifest.json"
    parser_meta_src = STAGE / "stage7_parser_metadata.json"
    element_profile_src = STAGE / "stage7_element_grounded_profile.json"
    second_review_src = STAGE / "structural_v2_human_second_review_accepted.json"

    release_cases = dict(_load(case_src))
    compare = _load(compare_src)
    source_manifest = _load(source_manifest_src)
    parser_meta = _load(parser_meta_src)
    element_profile = _load(element_profile_src)
    second_review = _load(second_review_src)

    release_cases["version"] = "0.1-non-gov-public-stage7-rc"
    release_cases["release_name"] = RELEASE_NAME
    release_cases["status"] = "release_candidate_frozen_from_stage7"
    release_cases["description"] = (
        "Non-government public PDF structural-v2 release candidate; reviewed Stage7 subset only, "
        "also included as a profile in the combined public RC."
    )

    outputs = {
        "cases": RELEASE / f"{PREFIX}_cases.json",
        "leaderboard_json": RELEASE / f"{PREFIX}_leaderboard.json",
        "leaderboard_md": RELEASE / f"{PREFIX}_leaderboard.md",
        "card": RELEASE / f"{PREFIX}_card.md",
        "manifest": RELEASE / f"{PREFIX}_manifest.json",
        "source_manifest": RELEASE / f"{PREFIX}_source_license_manifest.json",
        "source_manifest_md": RELEASE / f"{PREFIX}_source_license_manifest.md",
        "parser_metadata": RELEASE / f"{PREFIX}_parser_metadata.json",
        "element_grounded_profile": RELEASE / f"{PREFIX}_element_grounded_profile.json",
    }

    _dump(outputs["cases"], release_cases)
    _dump(outputs["leaderboard_json"], compare)
    _write_leaderboard(outputs["leaderboard_md"], compare)
    _dump(outputs["source_manifest"], source_manifest)
    _write_source_manifest_md(outputs["source_manifest_md"], source_manifest)
    _dump(outputs["parser_metadata"], parser_meta)
    _dump(outputs["element_grounded_profile"], element_profile)
    _write_card(outputs["card"], release_cases, compare, source_manifest, second_review)

    type_counts = Counter(
        assertion["type"]
        for case in release_cases["cases"]
        for assertion in case.get("assertions", [])
    )
    source_counts = Counter(_source_id(case["case_id"]) for case in release_cases["cases"])
    manifest = {
        "release_name": RELEASE_NAME,
        "status": "release_candidate_frozen_from_stage7",
        "source_stage": _rel(STAGE),
        "created_from": {
            "cases": _rel(case_src),
            "compare": _rel(compare_src),
            "source_manifest": _rel(source_manifest_src),
            "second_review": _rel(second_review_src),
        },
        "counts": {
            "cases": len(release_cases["cases"]),
            "assertions": sum(type_counts.values()),
            "sources": len(source_counts),
            "parsers": len(compare["parsers"]),
            "accepted_second_review_edits": second_review.get("summary", {}).get("accepted_edit_count"),
        },
        "files": {},
        "notes": [
            "Stage8 batch2 is not included in this Stage7-only RC; it is included in docfailbench_v0_1_combined_public_rc_* artifacts.",
            "This release candidate is separate from docfailbench_v0_1_public_real_rc_* artifacts.",
            "OpenStax Calculus carries CC BY-NC-SA 4.0 terms.",
        ],
    }
    for key, path in outputs.items():
        if key == "manifest":
            continue
        manifest["files"][_rel(path)] = _sha256(path)
    _dump(outputs["manifest"], manifest)
    return {"written": {key: _rel(path) for key, path in outputs.items()}}


def main() -> int:
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
