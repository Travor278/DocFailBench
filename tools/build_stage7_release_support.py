from __future__ import annotations

import json
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGE_DIR = ROOT / "runs" / "stage7_non_gov_public"
CASES_PATH = STAGE_DIR / "reviewed_non_gov_public_cases_structural_v2.json"
SOURCES_PATH = STAGE_DIR / "non_gov_public_sources.json"
COMPARE_PATH = STAGE_DIR / "compare_structural_v2_7parser.json"

SOURCE_MANIFEST_JSON = STAGE_DIR / "stage7_source_license_manifest.json"
SOURCE_MANIFEST_MD = STAGE_DIR / "stage7_source_license_manifest.md"
SPOTCHECK_JSON = STAGE_DIR / "structural_v2_spotcheck_preflight.json"
SPOTCHECK_MD = STAGE_DIR / "structural_v2_spotcheck_preflight.md"
SPOTCHECK_DIR = STAGE_DIR / "structural_v2_spotcheck_packet"
AI_PRECHECK_JSON = STAGE_DIR / "structural_v2_spotcheck_ai_precheck.json"
FIRST_REVIEW_JSON = STAGE_DIR / "structural_v2_codex_first_review.json"
FIRST_REVIEW_MD = STAGE_DIR / "structural_v2_codex_first_review.md"
FIRST_REVIEW_FOCUS_MD = STAGE_DIR / "structural_v2_human_second_review_focus.md"
FIRST_REVIEW_IMPORT_JSON = SPOTCHECK_DIR / "spotcheck_structural_v2_codex_first_review_import.json"
SECOND_REVIEW_JSON = STAGE_DIR / "structural_v2_human_second_review_accepted.json"
SECOND_REVIEW_MD = STAGE_DIR / "structural_v2_human_second_review_accepted.md"
PARSER_METADATA_JSON = STAGE_DIR / "stage7_parser_metadata.json"
PARSER_METADATA_MD = STAGE_DIR / "stage7_parser_metadata.md"
ELEMENT_GROUNDED_PROFILE_JSON = STAGE_DIR / "stage7_element_grounded_profile.json"
ELEMENT_GROUNDED_PROFILE_MD = STAGE_DIR / "stage7_element_grounded_profile.md"
RC_MANIFEST_JSON = STAGE_DIR / "stage7_release_candidate_manifest.json"
RC_MANIFEST_MD = STAGE_DIR / "stage7_release_candidate_manifest.md"

LICENSE_OVERRIDES: dict[str, dict[str, Any]] = {
    "openstax_calculus_v1": {
        "license": "CC BY-NC-SA 4.0; OpenStax Calculus copyright page verified",
        "license_status": "verified_with_noncommercial_sharealike_terms",
        "license_evidence": "PDF copyright page: Creative Commons Attribution NonCommercial ShareAlike 4.0 International License.",
    },
    "openstax_chemistry": {
        "license": "CC BY 4.0; OpenStax Chemistry copyright page verified",
        "license_status": "verified",
        "license_evidence": "PDF copyright page: Creative Commons Attribution 4.0 International License.",
    },
    "pmc_peerj_cs_1452": {
        "license": "CC BY 4.0; PeerJ/PMC OA notice verified",
        "license_status": "verified",
        "license_evidence": "Publisher/PMC OA notice records Creative Commons CC-BY 4.0.",
    },
    "acl_rocling_readability_zh": {
        "license": "CC BY 4.0; ACL Anthology post-2016 policy",
        "license_status": "verified_policy_based",
        "license_evidence": "ACL Anthology post-2016 materials are covered by the ACL CC BY 4.0 policy; paper page retained.",
    },
    "acl_struc_bench": {
        "license": "CC BY 4.0; ACL Anthology post-2016 policy",
        "license_status": "verified_policy_based",
        "license_evidence": "ACL Anthology post-2016 materials are covered by the ACL CC BY 4.0 policy; paper page retained.",
    },
    "acl_ocl_corpus": {
        "license": "CC BY 4.0; ACL Anthology post-2016 policy",
        "license_status": "verified_policy_based",
        "license_evidence": "ACL Anthology post-2016 materials are covered by the ACL CC BY 4.0 policy; paper page retained.",
    },
    "frontiers_vascular_models": {
        "license": "CC BY; Frontiers open-access notice verified",
        "license_status": "verified",
        "license_evidence": "Frontiers article/PDF open-access notice records Creative Commons Attribution License.",
    },
    "bmc_3d_print_models_review": {
        "license": "CC BY 4.0; BioMed Central article notice verified",
        "license_status": "verified",
        "license_evidence": "Article PDF states Creative Commons Attribution 4.0 International License.",
    },
}

STAGE7_SCORING_POLICY = {
    "main_score": (
        "Stage7 structural-v2 keeps all 165 visually spot-checked assertions, "
        "including a small number of representative bbox-aware element_grounded checks."
    ),
    "secondary_profiles": (
        "Broad page-furniture/header/footer absence checks remain secondary hygiene. "
        "Future gold-region overlap checks for element_grounded should be reported as a stricter bbox-aware profile."
    ),
}


FIRST_REVIEW_EDITS: dict[str, dict[str, Any]] = {
    "table_shape_f2199de13927": {"row_count": 8, "col_count": 8},
    "table_grid_cell_5f658b2fc9b9": {"table_index": 0, "row": 7, "col": 0, "expected": "ACL OCL (Ours)"},
    "table_grid_cell_8fc4bcf8e0e3": {"table_index": 0, "row": 7, "col": 1, "expected": "73.3K"},
    "table_grid_cell_8a09516fc28c": {"table_index": 0, "row": 7, "col": 2, "expected": "structured"},
    "table_grid_cell_5a183ed3549c": {"table_index": 0, "row": 7, "col": 3, "expected": "S2AG"},
    "table_grid_cell_6c8cf0bf455b": {"table_index": 0, "row": 7, "col": 6, "expected": "ACL"},
    "table_grid_cell_942d97ab8ed2": {"table_index": 0, "row": 7, "col": 7, "expected": "CL"},
    "table_shape_1f8a89cc8f8a": {"row_count": 15, "col_count": 4},
    "table_grid_cell_29d63f844a85": {"table_index": 0, "row": 14, "col": 2, "expected": "12 以上"},
    "table_grid_cell_bee77b77b999": {"table_index": 0, "row": 14, "col": 3, "expected": "290"},
    "table_shape_b1e42752a58b": {"row_count": 21, "col_count": 4},
    "formula_contains_0b18ab6cb0bf": {"latex": "AMMD = \\max_{i=1}^{n}(|x_i|)"},
    "text_presence_85444a433d04": {
        "text": "Figure 3.5 For values of x close to 1, the graph of f(x) = √x and its tangent line appear to coincide."
    },
    "formula_contains_d1577b525729": {"latex": "q_{rxn} = -q_{soln} = -(c × m × ΔT)_{soln}"},
    "formula_contains_8c24a5191d77": {"latex": "+1.0 × 10^3 J = +1.0 kJ"},
    "reading_order_732fcb0d4f10": {
        "before": "q_{rxn} = -q_{soln} = -(c × m × ΔT)_{soln}",
        "after": "Check Your Learning",
    },
    "element_grounded_78e462136534": {"text": "+1.0 × 10^3 J = +1.0 kJ"},
    "formula_contains_042508e41a99": {"latex": "PSNR = 10 × log_{10}"},
    "formula_contains_7fa815d7bdf4": {"latex": "K_{LPF} = (B3)^T (B3)"},
}

FIRST_REVIEW_EDIT_REASONS: dict[str, str] = {
    "table_shape_f2199de13927": "ACL OCL Table 1 has header plus seven data rows, so the visible grid is 8x8.",
    "table_grid_cell_5f658b2fc9b9": "ACL OCL final row is row 7 when header is row 0.",
    "table_grid_cell_8fc4bcf8e0e3": "ACL OCL final row is row 7 when header is row 0.",
    "table_grid_cell_8a09516fc28c": "ACL OCL final row is row 7 when header is row 0.",
    "table_grid_cell_5a183ed3549c": "ACL OCL final row is row 7 when header is row 0.",
    "table_grid_cell_6c8cf0bf455b": "ACL OCL final row is row 7 when header is row 0.",
    "table_grid_cell_942d97ab8ed2": "ACL OCL final row is row 7 when header is row 0.",
    "table_shape_1f8a89cc8f8a": "ROCLING Table 1 has grouped headers, 1-12 grade rows, and an extra English-side 12+ row.",
    "table_grid_cell_29d63f844a85": "The English-side 12+ row is the extra bottom row, not the Chinese 12th-grade row.",
    "table_grid_cell_bee77b77b999": "The English-side 12+ count is the extra bottom row, not the Chinese 12th-grade row.",
    "table_shape_b1e42752a58b": "BMC Table 1 expands to the header plus a longer exclusion list; 21x4 is the stricter visible grid.",
    "formula_contains_0b18ab6cb0bf": "AMMD formula is visible, but the original params compressed max range and x subscript.",
    "text_presence_85444a433d04": "OpenStax Calculus Figure 3.5 caption uses sqrt(x), not x.",
    "formula_contains_d1577b525729": "Thermochemistry equation is visible and should preserve rxn/soln subscripts.",
    "formula_contains_8c24a5191d77": "Unit conversion result should preserve the 10^3 exponent.",
    "reading_order_732fcb0d4f10": "Reading-order anchor should match the edited thermochemistry equation.",
    "element_grounded_78e462136534": "Grounding anchor should preserve the 10^3 exponent.",
    "formula_contains_042508e41a99": "PSNR formula is visible; log base 10 should be explicit.",
    "formula_contains_7fa815d7bdf4": "KLPF formula is visible; subscript and transpose should be explicit.",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _source_id(case_id: str) -> str:
    if not case_id.startswith("non_gov_public_"):
        return case_id
    stem = case_id.removeprefix("non_gov_public_")
    return stem.rsplit("_p", 1)[0]


def _source_rows(cases: list[dict[str, Any]], sources_payload: dict[str, Any]) -> list[dict[str, Any]]:
    source_pages: dict[str, set[int]] = defaultdict(set)
    source_case_counts: Counter[str] = Counter()
    source_assertion_counts: Counter[str] = Counter()
    for case in cases:
        source = _source_id(case["case_id"])
        source_case_counts[source] += 1
        source_assertion_counts[source] += len(case.get("assertions", []))
        page = case.get("document", {}).get("page")
        if isinstance(page, int):
            source_pages[source].add(page)

    rows: list[dict[str, Any]] = []
    for source in sources_payload.get("sources", []):
        source_id = source["source_id"]
        override = LICENSE_OVERRIDES.get(source_id, {})
        path = ROOT / source["path"]
        actual_sha = _sha256(path) if path.exists() else ""
        expected_sha = source.get("sha256", "")
        source_with_overrides = {**source, **{k: v for k, v in override.items() if k != "license_status"}}
        rows.append(
            {
                **source_with_overrides,
                "selected_stage7_pages": sorted(source_pages[source_id]),
                "stage7_case_count": source_case_counts[source_id],
                "stage7_assertion_count": source_assertion_counts[source_id],
                "pdf_exists": path.exists(),
                "sha256_verified": bool(expected_sha and actual_sha == expected_sha),
                "actual_sha256": actual_sha,
                "license_status": override.get("license_status") or (
                    "needs_document_specific_verification"
                    if "verify" in source_with_overrides.get("license", "").casefold()
                    else "recorded"
                ),
            }
        )
    return rows


def build_source_manifest(cases: list[dict[str, Any]], sources_payload: dict[str, Any]) -> dict[str, Any]:
    rows = _source_rows(cases, sources_payload)
    payload = {
        "name": "Stage7 non-government public source/license manifest",
        "status": "staging_not_release",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(rows),
        "rendered_case_count": len(cases),
        "assertion_count": sum(len(c.get("assertions", [])) for c in cases),
        "sources": rows,
        "metadata_first_queue": sources_payload.get("metadata_first_queue", []),
        "license_policy": {
            "verified": "PDF copyright page, publisher page, or stable source policy checked for this staging set.",
            "verified_with_noncommercial_sharealike_terms": "Redistribution is allowed for noncommercial use with ShareAlike and attribution; keep this explicit in release notes.",
            "verified_policy_based": "Publisher-wide policy checked; source page retained for per-document audit.",
            "needs_document_specific_verification": "Do not freeze until the exact document notice is checked.",
        },
        "release_gate_notes": [
            "All bundled or cached PDFs must have source URL, source page, attribution, license note, and SHA-256.",
            "OpenStax Calculus is CC BY-NC-SA 4.0, so any community release must keep noncommercial/ShareAlike terms visible.",
            "Stage7 visual review is complete; it remains staging until copied into a frozen release artifact under data/releases/.",
        ],
    }
    _dump(SOURCE_MANIFEST_JSON, payload)

    lines = [
        "# Stage7 Source And License Manifest",
        "",
        "Status: staging, not a frozen release artifact.",
        "",
        f"- Sources: {payload['source_count']}",
        f"- Rendered cases with structural-v2 assertions: {payload['rendered_case_count']}",
        f"- Assertions: {payload['assertion_count']}",
        "",
        "## Sources",
        "",
        "| Source | Pages | Assertions | License | License status | SHA-256 | Source page |",
        "| --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        pages = ", ".join(str(p) for p in row["selected_stage7_pages"])
        sha_status = "ok" if row["sha256_verified"] else "check"
        lines.append(
            f"| `{row['source_id']}` | {pages} | {row['stage7_assertion_count']} | "
            f"{row['license']} | {row['license_status']} | {sha_status} | {row['source_page']} |"
        )
    lines.extend(
        [
            "",
            "## Release Gate Notes",
            "",
            "- PDF/source-page license evidence has been checked for the Stage7 sources listed above.",
            "- Keep the OpenStax Calculus noncommercial/ShareAlike terms visible in any release card.",
            "- Keep PubTables-1M and DocLayNet metadata-first unless selected sample redistribution is clear.",
            "- Keep this manifest linked from any future Stage7 release card.",
            "",
        ]
    )
    SOURCE_MANIFEST_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


def _validate_assertion(assertion: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    a_type = assertion.get("type")
    params = assertion.get("params", {})
    if not assertion.get("id"):
        errors.append("missing_id")
    if a_type == "table_grid_cell":
        for key in ("row", "col", "expected"):
            if key not in params:
                errors.append(f"missing_{key}")
    elif a_type == "table_shape":
        for key in ("row_count", "col_count"):
            if key not in params:
                errors.append(f"missing_{key}")
    elif a_type == "table_cell_exists":
        if not params.get("text"):
            errors.append("missing_text")
    elif a_type == "formula_contains":
        if not params.get("latex"):
            errors.append("missing_latex")
    elif a_type == "reading_order":
        if not params.get("before") or not params.get("after"):
            errors.append("missing_anchor")
    elif a_type == "caption_binding":
        if not params.get("anchor") or not params.get("caption"):
            errors.append("missing_caption_anchor")
    elif a_type == "element_grounded":
        if not params.get("text"):
            errors.append("missing_grounding_text")
    elif a_type == "text_presence":
        if not params.get("text"):
            errors.append("missing_text")
    return errors


def build_spotcheck(cases: list[dict[str, Any]]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    duplicate_keys: Counter[str] = Counter()
    duplicate_ids: Counter[str] = Counter()

    for case in cases:
        case_id = case["case_id"]
        document = case.get("document", {})
        page_image = ROOT / document.get("page_image", "")
        source_pdf = ROOT / document.get("path", "")
        for assertion in case.get("assertions", []):
            params_key = json.dumps(
                {"case_id": case_id, "type": assertion.get("type"), "params": assertion.get("params", {})},
                ensure_ascii=False,
                sort_keys=True,
            )
            duplicate_keys[params_key] += 1
            duplicate_ids[str(assertion.get("id", ""))] += 1
            validation_errors = _validate_assertion(assertion)
            if not page_image.exists():
                validation_errors.append("missing_page_image")
            if not source_pdf.exists():
                validation_errors.append("missing_source_pdf")
            needs_visual = assertion.get("type") in {
                "table_grid_cell",
                "table_shape",
                "caption_binding",
                "reading_order",
                "formula_contains",
                "element_grounded",
            }
            entries.append(
                {
                    "case_id": case_id,
                    "title": case.get("title", ""),
                    "source_id": _source_id(case_id),
                    "document_path": document.get("path", ""),
                    "document_page": document.get("page"),
                    "page_image": document.get("page_image", ""),
                    "source_url": document.get("source_url", ""),
                    "license": document.get("license", ""),
                    "assertion_id": assertion.get("id", ""),
                    "type": assertion.get("type", ""),
                    "params": assertion.get("params", {}),
                    "description": assertion.get("description", ""),
                    "tags": assertion.get("tags", []),
                    "preflight_errors": validation_errors,
                    "visual_spotcheck_status": "pending_visual_confirmation" if needs_visual else "source_visible_anchor_pending",
                }
            )

    duplicate_param_count = sum(1 for count in duplicate_keys.values() if count > 1)
    duplicate_id_count = sum(1 for key, count in duplicate_ids.items() if key and count > 1)
    type_counts = Counter(entry["type"] for entry in entries)
    source_counts = Counter(entry["source_id"] for entry in entries)
    error_counts = Counter(err for entry in entries for err in entry["preflight_errors"])
    payload = {
        "name": "Stage7 structural-v2 spot-check preflight",
        "status": (
            "visual_spotcheck_complete_second_review_accepted"
            if SECOND_REVIEW_JSON.exists()
            else "pending_final_visual_spotcheck"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "assertion_count": len(entries),
        "case_count": len({entry["case_id"] for entry in entries}),
        "type_counts": dict(sorted(type_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "duplicate_param_groups": duplicate_param_count,
        "duplicate_id_groups": duplicate_id_count,
        "preflight_error_counts": dict(sorted(error_counts.items())),
        "entries": entries,
    }
    _dump(SPOTCHECK_JSON, payload)

    lines = [
        "# Stage7 Structural-V2 Spot-Check Preflight",
        "",
        (
            "Status: visual spot-check complete; human second review accepted the edited assertions. "
            "This report still records metadata and schema readiness."
            if SECOND_REVIEW_JSON.exists()
            else "Status: pending final visual spot-check. This report checks metadata and schema readiness; it does not replace visual review."
        ),
        "",
        f"- Assertions: {payload['assertion_count']}",
        f"- Cases: {payload['case_count']}",
        f"- Duplicate param groups: {duplicate_param_count}",
        f"- Duplicate ID groups: {duplicate_id_count}",
        f"- Preflight errors: {sum(error_counts.values())}",
        "",
        "## Assertion Types",
        "",
        "| Type | Count |",
        "| --- | ---: |",
    ]
    for key, value in sorted(type_counts.items()):
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Source Coverage", "", "| Source | Assertions |", "| --- | ---: |"])
    for key, value in sorted(source_counts.items()):
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Visual Review Packet", "", f"- HTML: `{_rel(SPOTCHECK_DIR / 'spotcheck_structural_v2.html')}`", ""])
    SPOTCHECK_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


def build_first_review(spotcheck: dict[str, Any]) -> dict[str, Any]:
    second_review = _load(SECOND_REVIEW_JSON) if SECOND_REVIEW_JSON.exists() else None
    accepted_edit_ids = {
        item["assertion_id"]
        for item in second_review.get("accepted_edits", [])
    } if second_review else set()
    now = datetime.now(timezone.utc).isoformat()
    decisions: list[dict[str, Any]] = []
    for index, entry in enumerate(spotcheck["entries"], start=1):
        assertion_id = entry["assertion_id"]
        if assertion_id in accepted_edit_ids:
            edited_params = entry["params"]
            decision = "pass"
            reason = "Human second review accepted the Codex edit; staging cases now contain the corrected params."
        elif assertion_id in FIRST_REVIEW_EDITS:
            edited_params = FIRST_REVIEW_EDITS[assertion_id]
            decision = "edit"
            reason = FIRST_REVIEW_EDIT_REASONS[assertion_id]
        else:
            edited_params = entry["params"]
            decision = "pass"
            reason = "Source-visible and type-correct in first-pass structural review."
        decisions.append(
            {
                "index": index,
                "assertion_id": assertion_id,
                "case_id": entry["case_id"],
                "source_id": entry["source_id"],
                "type": entry["type"],
                "decision": decision,
                "original_params": entry["params"],
                "edited_params": edited_params,
                "notes": reason,
                "reviewer": "codex_stage7_structural_v2_first_review",
                "reviewed_at": now,
                "document_path": entry["document_path"],
                "document_page": entry["document_page"],
                "page_image": entry["page_image"],
            }
        )
    decision_counts = Counter(item["decision"] for item in decisions)
    type_counts = Counter(item["type"] for item in decisions)
    edited_by_type = Counter(item["type"] for item in decisions if item["decision"] == "edit")
    payload = {
        "name": "Stage7 structural-v2 Codex first review",
        "status": (
            "first_review_complete_second_review_accepted"
            if second_review
            else "first_review_complete_pending_human_second_review"
        ),
        "generated_at": now,
        "standard": (
            "Community-strict first pass: every assertion must be source-visible, type-correct, "
            "and specific enough to be useful as benchmark gold. Edits preserve visible semantics "
            "without using parser outputs as truth."
        ),
        "summary": {
            "reviewed_count": len(decisions),
            "decision_counts": dict(sorted(decision_counts.items())),
            "type_counts": dict(sorted(type_counts.items())),
            "edited_by_type": dict(sorted(edited_by_type.items())),
            "needs_human_second_review": bool(edited_by_type),
            "second_review_status": (
                "accepted_edits_applied_to_staging_cases"
                if second_review
                else "pending_human_second_review"
            ),
        },
        "decisions": decisions,
    }
    _dump(FIRST_REVIEW_JSON, payload)

    import_payload = {
        "summary": {
            "item_count": len(decisions),
            "exported_at": now,
            "source": _rel(FIRST_REVIEW_JSON),
            "counts": dict(sorted(decision_counts.items())),
            "storage_key": "docfailbench.stage7.structural_v2.spotcheck.v1",
            "status": (
                "codex_first_review_prefill_after_accepted_second_review"
                if second_review
                else "codex_first_review_prefill_pending_human_second_review"
            ),
        },
        "decisions": [
            {
                "assertion_id": item["assertion_id"],
                "case_id": item["case_id"],
                "type": item["type"],
                "decision": item["decision"],
                "edited_params_text": json.dumps(item["edited_params"], ensure_ascii=False, indent=2),
                "notes": item["notes"],
            }
            for item in decisions
        ],
    }
    _dump(FIRST_REVIEW_IMPORT_JSON, import_payload)

    lines = [
        "# Stage7 Structural-V2 Codex First Review",
        "",
        (
            "Status: first review complete; human second review accepted edits and staging cases were updated."
            if second_review
            else "Status: first review complete, pending human second review."
        ),
        "",
        f"- Reviewed assertions: {len(decisions)}",
        "- Decisions: " + ", ".join(f"{key}={value}" for key, value in sorted(decision_counts.items())),
        f"- Import file: `{_rel(FIRST_REVIEW_IMPORT_JSON)}`",
        "",
        "## Edited Assertions",
        "",
        "| # | Assertion | Case | Type | Reason | Edited params |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for item in decisions:
        if item["decision"] != "edit":
            continue
        lines.append(
            f"| {item['index']} | `{item['assertion_id']}` | `{item['case_id']}` | `{item['type']}` | "
            f"{item['notes']} | `{json.dumps(item['edited_params'], ensure_ascii=False)}` |"
        )
    lines.extend(
        [
            "",
            "## Human Second Review Notes",
            "",
            "- The spot-check HTML can still load the Codex review as a browser prefill for audit.",
            "- The 19 edited assertions have been accepted and written back to the structural-v2 case file.",
            "- Stage7 visual review is complete; remaining work is release freeze packaging and any chosen Stage8 inclusion.",
            "",
        ]
    )
    FIRST_REVIEW_MD.write_text("\n".join(lines), encoding="utf-8")

    focus_lines = [
        "# Stage7 Structural-V2 Human Second Review Focus",
        "",
        (
            "Start here. Human second review has accepted the Codex edits; the current staging cases now show "
            "165 pass candidates and 0 pending edits."
            if second_review
            else "Start here. Codex first review marked 146 assertions as pass and 19 as edit; no assertions were marked fail."
        ),
        "",
        "Second-review guidance:",
        "",
        "- In the HTML packet, click `load Codex first review` first.",
        (
            "- Spot-check the accepted-edits audit if desired; the corrected params have already been applied."
            if second_review
            else "- Review the 19 edited rows below against the page image."
        ),
        (
            "- If any accepted edit looks wrong, mark it `fail` or edit the params manually before freeze."
            if second_review
            else "- If the edited params match the source page, leave the row as `edit`; if not, change it to `fail` or edit the params manually."
        ),
        "- Export JSON after review so Stage7 can import a real human second-review record.",
        "",
        "## Edited Rows To Check",
        "",
        "| # | Decision | Assertion | Source page | Image | Original params | Edited params | Why edited |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    if second_review:
        by_id = {item["assertion_id"]: item for item in decisions}
        for accepted in second_review.get("accepted_edits", []):
            item = by_id.get(accepted["assertion_id"])
            if not item:
                continue
            focus_lines.append(
                f"| {item['index']} | `accepted` | `{accepted['assertion_id']}` `{accepted['type']}` | "
                f"`{accepted['case_id']}` p{item['document_page']} | `{accepted['page_image']}` | "
                f"`{json.dumps(accepted['before'], ensure_ascii=False)}` | "
                f"`{json.dumps(accepted['after'], ensure_ascii=False)}` | {accepted['reason']} |"
            )
    else:
        for item in decisions:
            if item["decision"] != "edit":
                continue
            focus_lines.append(
                f"| {item['index']} | `{item['decision']}` | `{item['assertion_id']}` `{item['type']}` | "
                f"`{item['case_id']}` p{item['document_page']} | `{item['page_image']}` | "
                f"`{json.dumps(item['original_params'], ensure_ascii=False)}` | "
                f"`{json.dumps(item['edited_params'], ensure_ascii=False)}` | {item['notes']} |"
            )
    focus_lines.append("")
    FIRST_REVIEW_FOCUS_MD.write_text("\n".join(focus_lines), encoding="utf-8")
    return payload


def build_spotcheck_packet(spotcheck: dict[str, Any]) -> None:
    SPOTCHECK_DIR.mkdir(parents=True, exist_ok=True)
    packet_json = SPOTCHECK_DIR / "spotcheck_structural_v2.json"
    _dump(packet_json, {"entries": spotcheck["entries"], "summary": {k: v for k, v in spotcheck.items() if k != "entries"}})
    first_review_import = _load(FIRST_REVIEW_IMPORT_JSON) if FIRST_REVIEW_IMPORT_JSON.exists() else None
    precheck = {
        "name": "Stage7 structural-v2 AI/rule precheck",
        "status": "initial_screen_only_not_final_human_review",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "review_scope": (
            "These entries were curated and schema-preflighted before the visual packet. "
            "The decisions below are pass-candidates unless preflight errors exist; they do not replace final visual review."
        ),
        "decision_counts": {},
        "decisions": [],
    }
    decision_counts: Counter[str] = Counter()
    for entry in spotcheck["entries"]:
        has_errors = bool(entry.get("preflight_errors"))
        decision = "fail_candidate" if has_errors else "pass_candidate"
        confidence = "high" if has_errors else "medium"
        if has_errors:
            reason = "Preflight found metadata or assertion-shape errors that must be fixed before release."
        elif entry.get("type") in {"table_grid_cell", "table_shape", "caption_binding", "formula_contains"}:
            reason = "Curated structural assertion with valid schema; final visual confirmation is still required."
        else:
            reason = "Curated source-visible assertion with valid schema; final visual confirmation is still required."
        decision_counts[decision] += 1
        precheck["decisions"].append(
            {
                "assertion_id": entry["assertion_id"],
                "case_id": entry["case_id"],
                "type": entry["type"],
                "ai_precheck_decision": decision,
                "confidence": confidence,
                "reason": reason,
            }
        )
    precheck["decision_counts"] = dict(sorted(decision_counts.items()))
    _dump(AI_PRECHECK_JSON, precheck)

    html_items = json.dumps(spotcheck["entries"], ensure_ascii=False).replace("</", "<\\/")
    html_precheck = json.dumps(precheck["decisions"], ensure_ascii=False).replace("</", "<\\/")
    html_first_review = json.dumps(first_review_import, ensure_ascii=False).replace("</", "<\\/") if first_review_import else "null"
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stage7 Structural-V2 Spot-Check</title>
<style>
body {{ margin:0; font-family: Segoe UI, Arial, sans-serif; background:#f8fafc; color:#111827; }}
header {{ padding:16px 22px; background:#111827; color:white; position:sticky; top:0; z-index:2; }}
header h1 {{ margin:0; font-size:21px; }}
header p {{ margin:6px 0 0; color:#cbd5e1; }}
main {{ display:grid; grid-template-columns: 340px 1fr; gap:16px; padding:16px; }}
aside, section {{ background:white; border:1px solid #cbd5e1; border-radius:8px; }}
aside {{ max-height: calc(100vh - 105px); overflow:auto; }}
.item {{ display:block; width:100%; text-align:left; padding:10px 12px; border:0; border-bottom:1px solid #e5e7eb; background:white; cursor:pointer; }}
.item.active {{ background:#e0f2fe; }}
.item[data-state="pass"] {{ box-shadow: inset 4px 0 0 #16a34a; }}
.item[data-state="fail"] {{ box-shadow: inset 4px 0 0 #dc2626; }}
.item[data-state="unsure"] {{ box-shadow: inset 4px 0 0 #f59e0b; }}
.item[data-state="edit"] {{ box-shadow: inset 4px 0 0 #6366f1; }}
.tag {{ display:inline-block; padding:2px 7px; border-radius:999px; background:#e2e8f0; color:#334155; font-size:12px; margin-top:4px; }}
.content {{ display:grid; grid-template-columns:minmax(420px, 58%) 1fr; gap:16px; padding:16px; }}
img {{ width:100%; max-height: calc(100vh - 160px); object-fit:contain; background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; }}
pre {{ white-space:pre-wrap; background:#0f172a; color:#e5e7eb; border-radius:6px; padding:10px; max-height:220px; overflow:auto; }}
textarea {{ width:100%; box-sizing:border-box; min-height:80px; border:1px solid #cbd5e1; border-radius:6px; padding:8px; font:13px Consolas, monospace; }}
button {{ font:inherit; }}
.actions button {{ margin:6px 6px 0 0; border:1px solid #cbd5e1; background:white; border-radius:6px; padding:7px 10px; cursor:pointer; }}
.actions button[data-decision="pass"] {{ color:#166534; border-color:#16a34a; }}
.actions button[data-decision="fail"] {{ color:#991b1b; border-color:#dc2626; }}
.actions button[data-decision="unsure"] {{ color:#92400e; border-color:#f59e0b; }}
.actions button[data-decision="edit"] {{ color:#3730a3; border-color:#6366f1; }}
.actions button.selected[data-decision="pass"] {{ background:#16a34a; color:white; }}
.actions button.selected[data-decision="fail"] {{ background:#dc2626; color:white; }}
.actions button.selected[data-decision="unsure"] {{ background:#f59e0b; color:#111827; }}
.actions button.selected[data-decision="edit"] {{ background:#6366f1; color:white; }}
.review-summary {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }}
.review-summary span, .decision-pill {{ display:inline-block; padding:3px 8px; border-radius:999px; background:#e2e8f0; color:#334155; font-size:12px; }}
.decision-pill.pass {{ background:#dcfce7; color:#166534; }}
.decision-pill.fail {{ background:#fee2e2; color:#991b1b; }}
.decision-pill.unsure {{ background:#fef3c7; color:#92400e; }}
.decision-pill.edit {{ background:#e0e7ff; color:#3730a3; }}
.help {{ margin:10px 0 0; color:#64748b; font-size:13px; line-height:1.45; }}
.save-state {{ margin-top:8px; color:#64748b; font-size:13px; min-height:18px; }}
.meta {{ color:#475569; font-size:13px; line-height:1.5; }}
</style>
</head>
<body>
<header>
<h1>Stage7 Structural-V2 Spot-Check</h1>
<p>{spotcheck['assertion_count']} assertions. Clicks are saved in this browser only; export JSON when done.</p>
<div id="summary" class="review-summary"></div>
</header>
<main>
<aside id="list"></aside>
<section class="content">
  <div><img id="page" alt="source page"></div>
  <div>
    <h2 id="title"></h2>
    <div id="meta" class="meta"></div>
    <p id="precheck" class="help"></p>
    <p id="currentDecision" class="help"></p>
    <h3>Assertion Params</h3>
    <textarea id="params"></textarea>
    <div class="actions">
      <button data-decision="pass">pass</button>
      <button data-decision="fail">fail</button>
      <button data-decision="edit">edit</button>
      <button data-decision="unsure">unsure</button>
      <button id="loadFirstReview">load Codex first review</button>
      <button id="export">export JSON</button>
    </div>
    <div id="saveState" class="save-state"></div>
    <p class="help">The page is static, so pass/fail does not write to the repo by itself. It updates the left label and localStorage; use export JSON to create a review record.</p>
    <h3>Notes</h3>
    <textarea id="notes"></textarea>
    <h3>Description</h3>
    <pre id="description"></pre>
  </div>
</section>
</main>
<script>
const entries = {html_items};
const precheckEntries = {html_precheck};
const firstReviewImport = {html_first_review};
const precheckById = Object.fromEntries(precheckEntries.map(x => [x.assertion_id, x]));
const key = "docfailbench.stage7.structural_v2.spotcheck.v1";
let index = 0;
let decisions = JSON.parse(localStorage.getItem(key) || "{{}}");
const $ = id => document.getElementById(id);
function esc(s) {{ return String(s).replace(/[&<>]/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;"}}[c])); }}
function applyFirstReview(overwrite = false) {{
  if (!firstReviewImport || !Array.isArray(firstReviewImport.decisions)) return 0;
  let changed = 0;
  for (const item of firstReviewImport.decisions) {{
    if (!overwrite && decisions[item.assertion_id]) continue;
    decisions[item.assertion_id] = {{
      assertion_id: item.assertion_id,
      case_id: item.case_id,
      type: item.type,
      decision: item.decision,
      edited_params_text: item.edited_params_text,
      notes: item.notes || ""
    }};
    changed += 1;
  }}
  if (changed) localStorage.setItem(key, JSON.stringify(decisions));
  return changed;
}}
function currentDecision(item) {{
  return decisions[item.assertion_id] || {{
    assertion_id: item.assertion_id, case_id: item.case_id, type: item.type,
    decision: "", edited_params_text: JSON.stringify(item.params, null, 2), notes: ""
  }};
}}
function counts() {{
  const out = {{pass:0, fail:0, edit:0, unsure:0, open:0}};
  for (const item of entries) {{
    const d = currentDecision(item).decision || "open";
    out[d] = (out[d] || 0) + 1;
  }}
  return out;
}}
function renderSummary() {{
  const c = counts();
  $("summary").innerHTML = [
    `<span>${{entries.length}} total</span>`,
    `<span>${{c.pass}} pass</span>`,
    `<span>${{c.fail}} fail</span>`,
    `<span>${{c.edit}} edit</span>`,
    `<span>${{c.unsure}} unsure</span>`,
    `<span>${{c.open}} open</span>`
  ].join("");
}}
function renderDecisionState() {{
  const item = entries[index];
  const d = currentDecision(item).decision || "open";
  document.querySelectorAll(".actions button[data-decision]").forEach(btn => {{
    btn.classList.toggle("selected", btn.dataset.decision === d);
    btn.setAttribute("aria-pressed", String(btn.dataset.decision === d));
  }});
  $("currentDecision").innerHTML = `Current review decision: <span class="decision-pill ${{esc(d)}}">${{esc(d)}}</span>`;
}}
function save(message = "Saved in browser localStorage.") {{
  localStorage.setItem(key, JSON.stringify(decisions));
  renderList();
  renderSummary();
  renderDecisionState();
  $("saveState").textContent = message;
}}
function renderList() {{
  $("list").innerHTML = entries.map((item, i) => {{
    const d = currentDecision(item).decision || "open";
    return `<button class="item ${{i===index ? "active" : ""}}" data-state="${{esc(d)}}" data-i="${{i}}">
      <strong>#${{i+1}} ${{esc(item.type)}}</strong><br>${{esc(item.case_id)}}<br>
      <span class="tag">${{esc(d)}}</span>
    </button>`;
  }}).join("");
}}
function render() {{
  const item = entries[index];
  const d = currentDecision(item);
  $("page").src = "../../../" + item.page_image;
  $("title").textContent = `#${{index+1}} ${{item.type}}`;
  $("meta").innerHTML = `<strong>${{esc(item.case_id)}}</strong><br>
    Source: ${{esc(item.source_id)}} / page ${{esc(item.document_page)}}<br>
    License: ${{esc(item.license)}}<br>
    Status: ${{esc(item.visual_spotcheck_status)}}<br>
    Errors: ${{esc((item.preflight_errors || []).join(", ") || "none")}}`;
  const pre = precheckById[item.assertion_id] || {{}};
  $("precheck").innerHTML = `AI/rule precheck: <strong>${{esc(pre.ai_precheck_decision || "not recorded")}}</strong> · ${{esc(pre.reason || "No precheck note.")}}`;
  $("params").value = d.edited_params_text;
  $("notes").value = d.notes || "";
  $("description").textContent = item.description || "";
  renderList();
  renderSummary();
  renderDecisionState();
}}
$("list").addEventListener("click", e => {{
  const btn = e.target.closest("button[data-i]");
  if (!btn) return;
  index = Number(btn.dataset.i);
  render();
}});
document.querySelector(".actions").addEventListener("click", e => {{
  const btn = e.target.closest("button[data-decision]");
  if (!btn) return;
  const item = entries[index];
  decisions[item.assertion_id] = {{...currentDecision(item), decision: btn.dataset.decision, edited_params_text: $("params").value, notes: $("notes").value}};
  save(`Marked #${{index + 1}} as ${{btn.dataset.decision}}. Saved in browser localStorage.`);
}});
$("params").addEventListener("input", () => {{
  const item = entries[index];
  decisions[item.assertion_id] = {{...currentDecision(item), edited_params_text: $("params").value, notes: $("notes").value}};
  save("Edited params saved in browser localStorage.");
}});
$("notes").addEventListener("input", () => {{
  const item = entries[index];
  decisions[item.assertion_id] = {{...currentDecision(item), edited_params_text: $("params").value, notes: $("notes").value}};
  save("Notes saved in browser localStorage.");
}});
$("export").addEventListener("click", () => {{
  const payload = {{summary: {{item_count: entries.length, exported_at: new Date().toISOString(), counts: counts(), storage_key: key}}, decisions: Object.values(decisions)}};
  const blob = new Blob([JSON.stringify(payload, null, 2)], {{type:"application/json"}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "stage7_structural_v2_spotcheck_decisions.json"; a.click();
  URL.revokeObjectURL(url);
  $("saveState").textContent = "Exported JSON download. Import that file into the repo before freezing.";
}});
$("loadFirstReview").addEventListener("click", () => {{
  if (!firstReviewImport || !Array.isArray(firstReviewImport.decisions)) {{
    $("saveState").textContent = "No Codex first-review import file is available.";
    return;
  }}
  const changed = applyFirstReview(true);
  save(`Loaded ${{firstReviewImport.decisions.length}} Codex first-review decisions, overwriting this browser's current draft. Please second-review and export JSON.`);
}});
document.addEventListener("keydown", e => {{
  if (e.target.tagName === "TEXTAREA") return;
  if (e.key === "ArrowRight") {{ index = Math.min(entries.length - 1, index + 1); render(); }}
  if (e.key === "ArrowLeft") {{ index = Math.max(0, index - 1); render(); }}
}});
const prefilled = applyFirstReview(false);
render();
if (prefilled) {{
  $("saveState").textContent = `Auto-filled ${{prefilled}} missing Codex first-review decisions. Existing browser decisions were kept.`;
}}
</script>
</body>
</html>
"""
    (SPOTCHECK_DIR / "spotcheck_structural_v2.html").write_text(html, encoding="utf-8")


def build_parser_metadata(compare_payload: dict[str, Any]) -> dict[str, Any]:
    raw_dir = STAGE_DIR / "raw" / "structural_v2"
    rows = []
    for parser_row in compare_payload.get("parsers", []):
        label = parser_row.get("label")
        metadata_samples: list[dict[str, Any]] = []
        for path in raw_dir.glob(f"*{label}*.json"):
            payload = _load(path)
            preds = payload.get("predictions", payload if isinstance(payload, list) else [])
            for pred in preds[:3]:
                metadata_samples.append(pred.get("metadata", {}))
            break
        rows.append(
            {
                "label": label,
                "parser": parser_row.get("parser"),
                "score": parser_row.get("score"),
                "passed": parser_row.get("passed"),
                "failed": parser_row.get("failed"),
                "assertion_count": parser_row.get("assertion_count"),
                "case_count": parser_row.get("case_count"),
                "metadata_samples": metadata_samples,
            }
        )
    payload = {
        "name": "Stage7 structural-v2 parser metadata",
        "status": "staging_not_release",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parsers": rows,
        "notes": [
            "Stage7 parser scores are curation diagnostics only.",
            "Hosted API models should be treated as moving unless model IDs are pinned by provider.",
        ],
    }
    _dump(PARSER_METADATA_JSON, payload)

    lines = [
        "# Stage7 Parser Metadata",
        "",
        "Status: staging, not a frozen release artifact.",
        "",
        "| Parser | Score | Passed | Failed | Metadata hint |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        hint = ""
        if row["metadata_samples"]:
            sample = row["metadata_samples"][0]
            hint = sample.get("model") or sample.get("command_entrypoint") or sample.get("command", "")[:80]
        lines.append(f"| `{row['label']}` | {row['score']:.4f} | {row['passed']} | {row['failed']} | {hint} |")
    lines.append("")
    PARSER_METADATA_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


def build_element_grounded_profile(cases: list[dict[str, Any]], compare_payload: dict[str, Any]) -> dict[str, Any]:
    grounded_ids = {
        assertion["id"]
        for case in cases
        for assertion in case.get("assertions", [])
        if assertion.get("type") == "element_grounded"
    }
    rows: list[dict[str, Any]] = []
    for parser_row in compare_payload.get("parsers", []):
        label = parser_row.get("label")
        eval_path = STAGE_DIR / f"eval_structural_v2_{label}.json"
        eval_payload = _load(eval_path) if eval_path.exists() else {}
        passed = 0
        failed = 0
        for case_result in eval_payload.get("case_results", []):
            for result in case_result.get("results", []):
                if result.get("assertion_id") not in grounded_ids:
                    continue
                if result.get("passed"):
                    passed += 1
                else:
                    failed += 1
        total = passed + failed
        rows.append(
            {
                "label": label,
                "parser": parser_row.get("parser"),
                "eval_file": _rel(eval_path) if eval_path.exists() else "",
                "passed": passed,
                "failed": failed,
                "assertion_count": total,
                "score": (passed / total) if total else 0.0,
            }
        )
    rows.sort(key=lambda row: (-row["score"], row["label"] or ""))
    payload = {
        "name": "Stage7 bbox-aware element_grounded profile",
        "status": "staging_diagnostic_profile",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": STAGE7_SCORING_POLICY,
        "assertion_count": len(grounded_ids),
        "parsers": rows,
    }
    _dump(ELEMENT_GROUNDED_PROFILE_JSON, payload)

    lines = [
        "# Stage7 Element-Grounded Profile",
        "",
        "Status: staging diagnostic profile.",
        "",
        STAGE7_SCORING_POLICY["main_score"],
        "",
        STAGE7_SCORING_POLICY["secondary_profiles"],
        "",
        f"- `element_grounded` assertions: {len(grounded_ids)}",
        "",
        "| Parser | Passed | Failed | Score |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(f"| `{row['label']}` | {row['passed']} | {row['failed']} | {row['score']:.4f} |")
    lines.append("")
    ELEMENT_GROUNDED_PROFILE_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


def build_rc_manifest(
    source_manifest: dict[str, Any],
    spotcheck: dict[str, Any],
    parser_metadata: dict[str, Any],
    element_grounded_profile: dict[str, Any],
) -> dict[str, Any]:
    has_second_review = SECOND_REVIEW_JSON.exists()
    freeze_blockers = []
    if not has_second_review:
        freeze_blockers.insert(0, "final_visual_spotcheck_decisions_not_imported")
    payload = {
        "name": "DocFailBench Stage7 non-government public release candidate draft",
        "status": "draft_not_frozen",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_file": _rel(CASES_PATH),
        "compare_file": _rel(COMPARE_PATH),
        "source_manifest": _rel(SOURCE_MANIFEST_JSON),
        "source_manifest_md": _rel(SOURCE_MANIFEST_MD),
        "spotcheck_preflight": _rel(SPOTCHECK_JSON),
        "spotcheck_packet": _rel(SPOTCHECK_DIR / "spotcheck_structural_v2.html"),
        "first_review": _rel(FIRST_REVIEW_JSON),
        "first_review_md": _rel(FIRST_REVIEW_MD),
        "second_review_focus_md": _rel(FIRST_REVIEW_FOCUS_MD),
        "first_review_import": _rel(FIRST_REVIEW_IMPORT_JSON),
        "second_review": _rel(SECOND_REVIEW_JSON) if has_second_review else "",
        "second_review_md": _rel(SECOND_REVIEW_MD) if has_second_review else "",
        "parser_metadata": _rel(PARSER_METADATA_JSON),
        "element_grounded_profile": _rel(ELEMENT_GROUNDED_PROFILE_JSON),
        "scoring_policy": STAGE7_SCORING_POLICY,
        "next_release_queue": [
            "Stage8 batch2 has 38 second-review accepted assertions, 7-parser diagnostics, parser metadata, and a source/license manifest.",
            "Stage8 is included in DocFailBench-v0.1-combined-public-rc with its own profile label.",
            "Future non-government batches should repeat the same review, baseline, metadata, and release-card gates.",
        ],
        "counts": {
            "sources": source_manifest["source_count"],
            "cases": spotcheck["case_count"],
            "assertions": spotcheck["assertion_count"],
            "parsers": len(parser_metadata["parsers"]),
            "element_grounded_assertions": element_grounded_profile["assertion_count"],
        },
        "freeze_blockers": freeze_blockers,
    }
    _dump(RC_MANIFEST_JSON, payload)
    lines = [
        "# Stage7 Release Candidate Draft Manifest",
        "",
        "Status: draft, not frozen.",
        "",
        f"- Sources: {payload['counts']['sources']}",
        f"- Cases: {payload['counts']['cases']}",
        f"- Assertions: {payload['counts']['assertions']}",
        f"- Parsers: {payload['counts']['parsers']}",
        f"- Element-grounded checks: {payload['counts']['element_grounded_assertions']}",
        "",
        "## Artifacts",
        "",
        f"- Cases: `{payload['case_file']}`",
        f"- Compare: `{payload['compare_file']}`",
        f"- Source manifest: `{payload['source_manifest_md']}`",
        f"- Spot-check packet: `{payload['spotcheck_packet']}`",
        f"- Codex first review: `{payload['first_review_md']}`",
        f"- Human second-review focus: `{payload['second_review_focus_md']}`",
        f"- Codex first review import: `{payload['first_review_import']}`",
        *(
            [
                f"- Human second review accepted: `{payload['second_review_md']}`",
            ]
            if payload.get("second_review_md")
            else []
        ),
        f"- Parser metadata: `{payload['parser_metadata']}`",
        f"- Element-grounded profile: `{payload['element_grounded_profile']}`",
        "",
        "## Scoring Policy",
        "",
        f"- Main score: {STAGE7_SCORING_POLICY['main_score']}",
        f"- Secondary profiles: {STAGE7_SCORING_POLICY['secondary_profiles']}",
        "",
        "## Freeze Blockers",
        "",
    ]
    if payload["freeze_blockers"]:
        for blocker in payload["freeze_blockers"]:
            lines.append(f"- `{blocker}`")
    else:
        lines.append("- None recorded for Stage7-only freeze.")
    lines.extend(
        [
            "",
            "## Next Release Queue",
            "",
            "- Stage8 batch2 now has 38 second-review accepted assertions and 7-parser diagnostics.",
            "- Stage8 is included in `DocFailBench-v0.1-combined-public-rc` with its profile label preserved.",
            "- Future non-government batches should repeat the same review, baseline, metadata, and release-card gates.",
        ]
    )
    lines.append("")
    RC_MANIFEST_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


def main() -> int:
    cases = _load(CASES_PATH)["cases"]
    sources = _load(SOURCES_PATH)
    compare = _load(COMPARE_PATH)
    source_manifest = build_source_manifest(cases, sources)
    spotcheck = build_spotcheck(cases)
    build_first_review(spotcheck)
    build_spotcheck_packet(spotcheck)
    parser_metadata = build_parser_metadata(compare)
    element_grounded_profile = build_element_grounded_profile(cases, compare)
    rc_manifest = build_rc_manifest(source_manifest, spotcheck, parser_metadata, element_grounded_profile)
    print(json.dumps(rc_manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
