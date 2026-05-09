from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


INPUT_CASES = Path("runs/stage6_public_real/imported_human_public_real_cases.json")
OUT_CASES = Path("runs/stage6_public_real/public_real_v2_enhanced_cases.json")
OUT_REPORT_JSON = Path("runs/stage6_public_real/public_real_v2_enhancement_report.json")
OUT_REPORT_MD = Path("runs/stage6_public_real/public_real_v2_enhancement_report.md")

DIRTY_ANCHOR_CHARS = set("※§＊每〞∫")


def _stable_id(a_type: str, params: dict[str, Any]) -> str:
    payload = json.dumps({"type": a_type, "params": params}, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"{a_type}_{digest}"


def _assertion(
    a_type: str,
    params: dict[str, Any],
    *,
    severity: str = "major",
    description: str,
    tags: list[str],
) -> dict[str, Any]:
    return {
        "id": _stable_id(a_type, params),
        "type": a_type,
        "severity": severity,
        "params": params,
        "description": description,
        "tags": ["public_real_v2", *tags],
    }


def _dirty_value(value: Any) -> bool:
    if isinstance(value, str):
        return any(ch in value for ch in DIRTY_ANCHOR_CHARS)
    if isinstance(value, dict):
        return any(_dirty_value(v) for v in value.values())
    if isinstance(value, list):
        return any(_dirty_value(v) for v in value)
    return False


def _clean_existing(assertions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept = []
    removed = []
    for assertion in assertions:
        if _dirty_value(assertion.get("params", {})):
            removed.append(
                {
                    "id": assertion.get("id", ""),
                    "type": assertion.get("type", ""),
                    "params": assertion.get("params", {}),
                    "reason": "removed dirty PDF-encoding artifact anchor",
                }
            )
            continue
        copied = dict(assertion)
        tags = list(copied.get("tags", []))
        if "public_real_v2_inherited" not in tags:
            tags.append("public_real_v2_inherited")
        copied["tags"] = tags
        kept.append(copied)
    return kept, removed


def _add(case_additions: dict[str, list[dict[str, Any]]], case_id: str, assertion: dict[str, Any]) -> None:
    case_additions.setdefault(case_id, []).append(assertion)


def build_additions() -> dict[str, list[dict[str, Any]]]:
    additions: dict[str, list[dict[str, Any]]] = {}

    # NIST SP 800-53 revision table: a clean, regular 32x4 grid.
    cid = "public_real_nist_sp800_53r5_p027"
    desc = "NIST SP 800-53 revision table visible on page xxv."
    _add(additions, cid, _assertion("table_shape", {"row_count": 32, "col_count": 4}, description=desc, tags=["nist", "table_shape"]))
    for row, col, expected in [
        (0, 0, "DATE"),
        (0, 1, "TYPE"),
        (0, 2, "REVISION"),
        (0, 3, "PAGE"),
        (1, 0, "12-10-2020"),
        (1, 1, "Editorial"),
        (1, 3, "427"),
        (11, 2, "Table C-5: Delete duplicate row CM-8(5)."),
        (11, 3, "438"),
        (30, 2, "Table C-19"),
        (30, 3, "463"),
        (31, 2, "SI-19(7)"),
        (31, 3, "464"),
    ]:
        _add(
            additions,
            cid,
            _assertion(
                "table_grid_cell",
                {"table_index": 0, "row": row, "col": col, "expected": expected},
                description=desc,
                tags=["nist", "table_grid_cell"],
            ),
        )
    for text in [
        "Appendix B Acronyms: Add",
        "UPS Uninterruptible Power Supply",
        "Table C-5: Delete duplicate row CM-8(5).",
        "Table C-18 (SC-19)",
        "Table C-19 (SI-19(7))",
    ]:
        _add(additions, cid, _assertion("table_cell_exists", {"text": text}, description=desc, tags=["nist", "table_cell_exists"]))
    _add(
        additions,
        cid,
        _assertion(
            "reading_order",
            {"before": "Appendix B Acronyms", "after": "Table C-19"},
            description="Revision rows should preserve top-to-bottom order.",
            tags=["nist", "reading_order"],
        ),
    )

    # NIST AI RMF figure/caption and section flow.
    cid = "public_real_nist_ai_rmf_p017"
    _add(
        additions,
        cid,
        _assertion(
            "caption_binding",
            {
                "anchor": "Valid & Reliable",
                "caption": "Fig. 4. Characteristics of trustworthy AI systems",
                "max_lines": 8,
            },
            description="Figure 4 caption should remain bound to the trustworthiness diagram.",
            tags=["nist", "caption_binding"],
        ),
    )
    for before, after in [
        ("3. AI Risks and Trustworthiness", "Fig. 4. Characteristics of trustworthy AI systems"),
        ("Fig. 4. Characteristics of trustworthy AI systems", "Trustworthiness characteristics"),
        ("valid and reliable", "privacy-enhanced"),
    ]:
        _add(
            additions,
            cid,
            _assertion(
                "reading_order",
                {"before": before, "after": after},
                description="NIST AI RMF page should preserve heading, figure, and paragraph order.",
                tags=["nist", "reading_order"],
            ),
        )

    # GovInfo CFR two-column legal text.
    cid = "public_real_govinfo_cfr_title1_p014"
    for before, after in [
        ("PART 1", "Administrative Committee means"),
        ("Agency means", "Document includes"),
        ("Document includes", "Document having general applicability"),
        ("Document having general applicability", "Filing means"),
        ("PART 2", "Scope and purpose"),
    ]:
        _add(
            additions,
            cid,
            _assertion(
                "reading_order",
                {"before": before, "after": after},
                description="GovInfo CFR page should preserve two-column legal reading order.",
                tags=["govinfo", "reading_order"],
            ),
        )

    cid = "public_real_govinfo_cfr_title1_p035"
    for before, after in [
        ("PART 21", "21.19 Composition of part headings"),
        ("21.19 Composition of part headings", "21.35 OMB control numbers"),
        ("Preparation of documents", "OMB control numbers"),
        ("PART 21", "otherwise noted"),
    ]:
        _add(
            additions,
            cid,
            _assertion(
                "reading_order",
                {"before": before, "after": after},
                description="GovInfo CFR table-of-contents-like legal page should preserve list order.",
                tags=["govinfo", "reading_order"],
            ),
        )

    # IRS Form 1040 page 1: dense form labels and section order.
    cid = "public_real_irs_1040_2024_p001"
    for text in [
        "Presidential Election Campaign",
        "Filing Status",
        "Digital Assets",
        "Standard Deduction",
        "Total amount from Form(s) W-2",
        "Tax-exempt interest",
        "Capital gain or (loss)",
        "Qualified business income deduction",
        "taxable income",
    ]:
        _add(additions, cid, _assertion("table_cell_exists", {"text": text}, description="IRS Form 1040 page 1 form fields should remain structured.", tags=["irs", "form", "table_cell_exists"]))
    for before, after in [
        ("Filing Status", "Digital Assets"),
        ("Digital Assets", "Standard Deduction"),
        ("Standard Deduction", "Dependents"),
        ("Dependents", "Total amount from Form(s) W-2"),
    ]:
        _add(additions, cid, _assertion("reading_order", {"before": before, "after": after}, description="IRS Form 1040 section order should be preserved.", tags=["irs", "form", "reading_order"]))

    # IRS Schedule A.
    cid = "public_real_irs_1040sa_2024_p001"
    for text in [
        "Medical and dental expenses",
        "State and local income taxes",
        "State and local real estate taxes",
        "State and local personal property taxes",
        "Home mortgage interest and points",
        "Investment interest",
        "Gifts by cash or check",
        "Casualty and theft loss",
        "Other Itemized Deductions",
        "Total Itemized Deductions",
    ]:
        _add(additions, cid, _assertion("table_cell_exists", {"text": text}, description="IRS Schedule A itemized deduction rows should remain as form/table cells.", tags=["irs", "schedule_a", "table_cell_exists"]))
    for before, after in [
        ("Medical and Dental Expenses", "Taxes You Paid"),
        ("Taxes You Paid", "Interest You Paid"),
        ("Interest You Paid", "Gifts to Charity"),
        ("Gifts to Charity", "Casualty and Theft Losses"),
    ]:
        _add(additions, cid, _assertion("reading_order", {"before": before, "after": after}, description="IRS Schedule A section order should be preserved.", tags=["irs", "schedule_a", "reading_order"]))

    # IRS Schedule C page 1.
    cid = "public_real_irs_1040sc_2024_p001"
    for text in [
        "Profit or Loss From Business",
        "Principal business or profession",
        "Enter code from instructions",
        "Employer ID number",
        "Accounting method",
        "Gross receipts or sales",
        "Gross profit",
        "Office expense",
        "Taxes and licenses",
        "Other expenses (from line 48)",
        "Total expenses before expenses for business use of home",
        "Net profit or (loss)",
    ]:
        _add(additions, cid, _assertion("table_cell_exists", {"text": text}, description="IRS Schedule C page 1 form/table rows should remain structured.", tags=["irs", "schedule_c", "table_cell_exists"]))
    for before, after in [
        ("Part I", "Part II"),
        ("Gross receipts or sales", "Gross income"),
        ("Advertising", "Taxes and licenses"),
        ("Other expenses (from line 48)", "Total expenses"),
        ("Total expenses", "Net profit or (loss)"),
    ]:
        _add(additions, cid, _assertion("reading_order", {"before": before, "after": after}, description="IRS Schedule C page 1 form row order should be preserved.", tags=["irs", "schedule_c", "reading_order"]))

    # IRS Schedule C page 2.
    cid = "public_real_irs_1040sc_2024_p002"
    for text in [
        "Cost of Goods Sold",
        "Method(s) used to value closing inventory",
        "Inventory at beginning of year",
        "Purchases less cost of items withdrawn",
        "Subtract line 41 from line 40",
        "Information on Your Vehicle",
        "Do you have evidence to support your deduction",
        "Other Expenses",
        "Total other expenses",
    ]:
        _add(additions, cid, _assertion("table_cell_exists", {"text": text}, description="IRS Schedule C page 2 form/table rows should remain structured.", tags=["irs", "schedule_c", "table_cell_exists"]))
    for before, after in [
        ("Part III", "Part IV"),
        ("Part IV", "Part V"),
        ("Method(s) used to value closing inventory", "Cost of goods sold"),
        ("When did you place your vehicle in service", "Do you have evidence to support your deduction"),
        ("Other Expenses", "Total other expenses"),
    ]:
        _add(additions, cid, _assertion("reading_order", {"before": before, "after": after}, description="IRS Schedule C page 2 section and row order should be preserved.", tags=["irs", "schedule_c", "reading_order"]))

    # IRS Schedule D page 1.
    cid = "public_real_irs_1040sd_2024_p001"
    for text in [
        "Short-Term Capital Gains and Losses",
        "Proceeds",
        "Cost",
        "Adjustments",
        "Gain or (loss)",
        "Box A checked",
        "Box F checked",
        "Net short-term capital gain or (loss)",
        "Long-Term Capital Gains and Losses",
        "Net long-term capital gain or (loss)",
    ]:
        _add(additions, cid, _assertion("table_cell_exists", {"text": text}, description="IRS Schedule D page 1 capital gains table should remain structured.", tags=["irs", "schedule_d", "table_cell_exists"]))
    for before, after in [
        ("Part I", "Part II"),
        ("Box A checked", "Box F checked"),
        ("Net short-term capital gain or (loss)", "Long-Term Capital Gains and Losses"),
        ("Long-Term Capital Gains and Losses", "Net long-term capital gain or (loss)"),
    ]:
        _add(additions, cid, _assertion("reading_order", {"before": before, "after": after}, description="IRS Schedule D page 1 table sections should preserve order.", tags=["irs", "schedule_d", "reading_order"]))

    # IRS Schedule D page 2.
    cid = "public_real_irs_1040sd_2024_p002"
    for text in [
        "Part III Summary",
        "Combine lines 7 and 15",
        "Capital Gain Tax Worksheet",
        "Unrecaptured Section 1250 Gain Worksheet",
        "Schedule D Tax Worksheet",
        "Qualified Dividends and Capital Gain Tax Worksheet",
    ]:
        _add(additions, cid, _assertion("table_cell_exists", {"text": text}, description="IRS Schedule D page 2 summary worksheet rows should remain structured.", tags=["irs", "schedule_d", "table_cell_exists"]))
    for before, after in [
        ("Part III Summary", "Unrecaptured Section 1250 Gain Worksheet"),
        ("Unrecaptured Section 1250 Gain Worksheet", "Schedule D Tax Worksheet"),
        ("Qualified Dividends and Capital Gain Tax Worksheet", "Schedule D Tax Worksheet"),
    ]:
        _add(additions, cid, _assertion("reading_order", {"before": before, "after": after}, description="IRS Schedule D page 2 worksheet order should be preserved.", tags=["irs", "schedule_d", "reading_order"]))

    # A small amount of page-furniture pollution checking.
    for cid, text in [
        ("public_real_irs_1040sc_2024_p001", "Cat. No. 11334P"),
        ("public_real_irs_1040sd_2024_p001", "Cat. No. 11338H"),
        ("public_real_nist_sp800_53r5_p027", "This publication is available free of charge"),
    ]:
        _add(
            additions,
            cid,
            _assertion(
                "text_absence",
                {"text": text},
                severity="minor",
                description="Do not include low-value repeated page furniture in the parser content stream.",
                tags=["page_furniture", "hygiene", "secondary", "non_scored", "text_absence"],
            ),
        )

    return additions


def main() -> int:
    payload = json.loads(INPUT_CASES.read_text(encoding="utf-8"))
    additions = build_additions()
    removed_all: list[dict[str, Any]] = []
    skipped_empty_cases: list[str] = []
    added_count = 0
    enhanced_cases = []
    for case in payload.get("cases", []):
        case = dict(case)
        kept, removed = _clean_existing(case.get("assertions", []))
        removed_all.extend({"case_id": case["case_id"], **item} for item in removed)
        existing_keys = {
            (item["type"], json.dumps(item.get("params", {}), ensure_ascii=False, sort_keys=True))
            for item in kept
        }
        for item in additions.get(case["case_id"], []):
            key = (item["type"], json.dumps(item.get("params", {}), ensure_ascii=False, sort_keys=True))
            if key in existing_keys:
                continue
            kept.append(item)
            existing_keys.add(key)
            added_count += 1
        case["assertions"] = kept
        if kept:
            enhanced_cases.append(case)
        else:
            skipped_empty_cases.append(case["case_id"])

    out_payload = {"version": "0.1-public-real-v2-enhanced", "cases": enhanced_cases}
    OUT_CASES.parent.mkdir(parents=True, exist_ok=True)
    OUT_CASES.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    by_type = Counter(a["type"] for c in enhanced_cases for a in c.get("assertions", []))
    by_case = {
        c["case_id"]: Counter(a["type"] for a in c.get("assertions", []))
        for c in enhanced_cases
        if c.get("assertions")
    }
    report = {
        "input_cases": str(INPUT_CASES),
        "output_cases": str(OUT_CASES),
        "case_count": len(enhanced_cases),
        "assertion_count": sum(len(c.get("assertions", [])) for c in enhanced_cases),
        "added_assertions": added_count,
        "removed_dirty_existing_assertions": len(removed_all),
        "skipped_empty_cases": skipped_empty_cases,
        "removed": removed_all,
        "assertions_by_type": dict(sorted(by_type.items())),
        "assertions_by_case": {k: dict(v) for k, v in sorted(by_case.items())},
    }
    OUT_REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Public-Real v2 Enhancement Report",
        "",
        f"- Input: `{INPUT_CASES}`",
        f"- Output: `{OUT_CASES}`",
        f"- Cases: {report['case_count']}",
        f"- Assertions: {report['assertion_count']}",
        f"- Added structural assertions: {added_count}",
        f"- Removed dirty inherited anchors: {len(removed_all)}",
        "",
        "## Assertions By Type",
        "",
        "| Type | Count |",
        "| --- | ---: |",
    ]
    for key, value in sorted(by_type.items()):
        md_lines.append(f"| `{key}` | {value} |")
    md_lines.extend(["", "## Removed Dirty Anchors", ""])
    if removed_all:
        md_lines.extend(["| Case | Type | Reason |", "| --- | --- | --- |"])
        for item in removed_all:
            md_lines.append(f"| `{item['case_id']}` | `{item['type']}` | {item['reason']} |")
    else:
        md_lines.append("None.")
    OUT_REPORT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
