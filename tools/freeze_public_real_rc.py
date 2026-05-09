from __future__ import annotations

import hashlib
import importlib.metadata as importlib_metadata
import json
import platform
import shutil
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "runs/stage6_public_real"
RELEASE = ROOT / "data/releases"
CASES = STAGE / "public_real_v2_enhanced_cases.json"
MERGED_CASES = STAGE / "merged_v0_1_public_real_v2_cases.json"
OUT_CASES = RELEASE / "docfailbench_v0_1_public_real_rc_cases.json"
OUT_HYGIENE_CASES = RELEASE / "docfailbench_v0_1_public_real_rc_hygiene_cases.json"
OUT_METADATA = RELEASE / "docfailbench_v0_1_public_real_rc_metadata.json"
OUT_SPOTCHECK_JSON = RELEASE / "docfailbench_v0_1_public_real_rc_spotcheck.json"
OUT_SPOTCHECK_MD = RELEASE / "docfailbench_v0_1_public_real_rc_spotcheck.md"
OUT_CARD = RELEASE / "docfailbench_v0_1_public_real_rc_card.md"
OUT_COMPARE_JSON = RELEASE / "docfailbench_v0_1_public_real_rc_leaderboard.json"
OUT_COMPARE_MD = RELEASE / "docfailbench_v0_1_public_real_rc_leaderboard.md"
OUT_PUBLIC_COMPARE_JSON = RELEASE / "docfailbench_v0_1_public_real_rc_public_only_leaderboard.json"
OUT_PUBLIC_COMPARE_MD = RELEASE / "docfailbench_v0_1_public_real_rc_public_only_leaderboard.md"


PARSER_LABELS = {
    "qwen": "Qwen-VL API",
    "plain": "PyMuPDF4LLM plain",
    "paddleocr": "PaddleOCR",
    "mineru": "MinerU",
    "marker": "Marker",
    "docling": "Docling",
    "bbox": "PyMuPDF4LLM bbox",
}

PARSER_RESULT_LABELS = ["qwen", "plain", "paddleocr", "mineru", "marker", "docling", "bbox"]


SPOTCHECKED_ASSERTIONS = [
    ("public_real_nist_sp800_53r5_p027", "table_shape_4a52f945214a", "approved", "Visual page review confirms a regular 32-row by 4-column revision table."),
    ("public_real_nist_sp800_53r5_p027", "table_grid_cell_7f5aeace671f", "approved", "Header cell DATE is visible in row 0, column 0."),
    ("public_real_nist_sp800_53r5_p027", "table_grid_cell_a0c29a88a352", "approved", "Header cell TYPE is visible in row 0, column 1."),
    ("public_real_nist_sp800_53r5_p027", "table_grid_cell_23c1839386a1", "approved", "Header cell REVISION is visible in row 0, column 2."),
    ("public_real_nist_sp800_53r5_p027", "table_grid_cell_d6299f23d151", "approved", "Header cell PAGE is visible in row 0, column 3."),
    ("public_real_nist_sp800_53r5_p027", "table_grid_cell_b852eba9523d", "approved", "First data-row date 12-10-2020 is visually present."),
    ("public_real_nist_sp800_53r5_p027", "table_grid_cell_4446cb697879", "approved", "First data-row type Editorial is visually present."),
    ("public_real_nist_sp800_53r5_p027", "table_grid_cell_c24191dc3f8a", "approved", "First data-row page value 427 is visually present."),
    ("public_real_nist_sp800_53r5_p027", "table_grid_cell_386963b063d6", "approved", "Row 11 revision text for Table C-5 duplicate deletion is visible."),
    ("public_real_nist_sp800_53r5_p027", "table_grid_cell_2e8557cd970c", "approved", "Row 11 page value 438 is visible."),
    ("public_real_nist_sp800_53r5_p027", "table_grid_cell_6750102d1311", "approved", "Near-tail revision entry Table C-19 is visible."),
    ("public_real_nist_sp800_53r5_p027", "table_grid_cell_82be1ff5d528", "approved", "Near-tail page value 463 is visible."),
    ("public_real_nist_sp800_53r5_p027", "table_grid_cell_44fb09c941d3", "approved", "Tail revision entry SI-19(7) is visible."),
    ("public_real_nist_sp800_53r5_p027", "table_grid_cell_0b607d521dd8", "approved", "Tail page value 464 is visible."),
    ("public_real_nist_sp800_53r5_p027", "table_cell_exists_d7d3816de474", "approved", "Revision cell beginning Appendix B Acronyms: Add is visible."),
    ("public_real_nist_sp800_53r5_p027", "table_cell_exists_4ed8d55f644b", "approved", "UPS Uninterruptible Power Supply is visible within the first revision row."),
    ("public_real_nist_sp800_53r5_p027", "table_cell_exists_8c917d4fa3d9", "approved", "Table C-5 duplicate-row deletion text is visible."),
    ("public_real_nist_sp800_53r5_p027", "table_cell_exists_ac5fdbb233cd", "approved", "Table C-18 (SC-19) row is visible."),
    ("public_real_nist_sp800_53r5_p027", "table_cell_exists_e3118535aa36", "approved", "Table C-19 (SI-19(7)) row is visible."),
    ("public_real_nist_sp800_53r5_p027", "reading_order_7fb05dfe98ce", "approved", "Appendix B Acronyms appears above the Table C-19 rows."),
    ("public_real_nist_ai_rmf_p017", "caption_binding_08b0fd565d5b", "approved", "Trustworthiness diagram and Figure 4 caption are adjacent."),
    ("public_real_nist_ai_rmf_p017", "reading_order_0728a2413a0c", "approved", "Section heading precedes the figure caption."),
    ("public_real_nist_ai_rmf_p017", "reading_order_59722044cf62", "approved", "Figure caption precedes the Trustworthiness characteristics paragraph."),
    ("public_real_nist_ai_rmf_p017", "reading_order_958b96e778e9", "approved", "The characteristic list places valid and reliable before privacy-enhanced."),
    ("public_real_irs_1040_2024_p001", "table_cell_exists_847a240ce65d", "approved", "Presidential Election Campaign box is visible in the upper-right form block."),
    ("public_real_irs_1040_2024_p001", "table_cell_exists_a3cd4eefe792", "approved", "Filing Status label is visible on the left side of the form."),
    ("public_real_irs_1040_2024_p001", "table_cell_exists_dffadf7dc9f2", "approved", "Digital Assets section label is visible below Filing Status."),
    ("public_real_irs_1040_2024_p001", "table_cell_exists_6b597cd48f00", "approved", "Standard Deduction label is visible below Digital Assets."),
    ("public_real_irs_1040_2024_p001", "table_cell_exists_f83738d8b990", "approved", "W-2 total amount row is visible in the Income section."),
    ("public_real_irs_1040_2024_p001", "reading_order_8e674fe7f026", "approved_with_edit", "Original Dependents-to-Income anchor was ambiguous because Income appears in side text; edited to Dependents before W-2 row."),
    ("public_real_irs_1040sa_2024_p001", "table_cell_exists_62392c31d800", "approved", "Medical and dental expenses row is visible."),
    ("public_real_irs_1040sa_2024_p001", "table_cell_exists_3c08328e4754", "approved", "State and local income taxes row is visible."),
    ("public_real_irs_1040sa_2024_p001", "table_cell_exists_77833f29bc31", "approved", "Home mortgage interest and points row is visible."),
    ("public_real_irs_1040sa_2024_p001", "table_cell_exists_994d77595721", "approved", "Gifts by cash or check row is visible."),
    ("public_real_irs_1040sa_2024_p001", "reading_order_c83ac0b9231c", "approved", "Interest You Paid section precedes Gifts to Charity."),
    ("public_real_irs_1040sc_2024_p001", "table_cell_exists_794d85e431f3", "approved", "Schedule C title Profit or Loss From Business is visible."),
    ("public_real_irs_1040sc_2024_p001", "table_cell_exists_6232f0848451", "approved", "Gross receipts or sales row is visible."),
    ("public_real_irs_1040sc_2024_p001", "table_cell_exists_b86903e37050", "approved", "Taxes and licenses expense row is visible."),
    ("public_real_irs_1040sc_2024_p001", "table_cell_exists_714320a018ce", "approved", "Net profit or loss row is visible."),
    ("public_real_irs_1040sc_2024_p001", "reading_order_bb0e3ab4fb61", "approved", "Other expenses from line 48 precedes Total expenses."),
    ("public_real_irs_1040sc_2024_p002", "table_cell_exists_1f9e0c1c5837", "approved", "Cost of Goods Sold section is visible."),
    ("public_real_irs_1040sc_2024_p002", "table_cell_exists_f3b3edfbaea9", "approved", "Information on Your Vehicle section is visible."),
    ("public_real_irs_1040sc_2024_p002", "table_cell_exists_c28b9b28769c", "approved", "Other Expenses section is visible."),
    ("public_real_irs_1040sc_2024_p002", "reading_order_dc6ac7201f91", "approved", "Vehicle service-date question precedes evidence-support question."),
    ("public_real_irs_1040sd_2024_p001", "table_cell_exists_0ff9020cdcbe", "approved", "Short-Term Capital Gains and Losses header is visible."),
    ("public_real_irs_1040sd_2024_p001", "table_cell_exists_94f89be175ee", "approved", "Gain or (loss) column header is visible."),
    ("public_real_irs_1040sd_2024_p001", "table_cell_exists_9416183769cd", "approved", "Net short-term capital gain or loss row is visible."),
    ("public_real_irs_1040sd_2024_p001", "reading_order_473cbab141be", "approved", "Short-term net row precedes Long-Term Capital Gains and Losses."),
    ("public_real_irs_1040sd_2024_p002", "table_cell_exists_39e8665ad998", "approved", "Part III Summary heading is visible."),
    ("public_real_irs_1040sd_2024_p002", "table_cell_exists_584f04c789a5", "approved", "Capital Gain Tax Worksheet line is visible."),
    ("public_real_irs_1040sd_2024_p002", "reading_order_c4ae3284620e", "approved_with_edit", "Original order was reversed; edited to Qualified Dividends before Schedule D Tax Worksheet."),
    ("public_real_govinfo_cfr_title1_p014", "reading_order_c3696e8c330f", "approved", "PART 1 appears before Administrative Committee definition."),
    ("public_real_govinfo_cfr_title1_p014", "reading_order_463faedcf7af", "approved", "Agency means appears before Document includes in the left column."),
    ("public_real_govinfo_cfr_title1_p014", "reading_order_6d673d9bc7b0", "approved", "Document includes appears before Document having general applicability."),
    ("public_real_govinfo_cfr_title1_p014", "reading_order_676d0d90e7d9", "removed", "Removed from main RC because the cross-column anchor was too broad and failed sanity checks."),
    ("public_real_govinfo_cfr_title1_p035", "reading_order_5fd51a00c55e", "approved", "21.19 appears before 21.35 in the contents-like list."),
    ("public_real_govinfo_cfr_title1_p035", "reading_order_dca7e39a47bb", "approved", "PART 21 appears before otherwise noted."),
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _assertion_lookup(cases: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (case["case_id"], assertion["id"]): assertion
        for case in cases
        for assertion in case.get("assertions", [])
    }


def _split_scored_cases(public_cases: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    scored_cases: list[dict[str, Any]] = []
    hygiene_cases: list[dict[str, Any]] = []
    for case in public_cases.get("cases", []):
        scored_assertions = []
        hygiene_assertions = []
        for assertion in case.get("assertions", []):
            tags = set(assertion.get("tags", []))
            if assertion.get("type") == "text_absence" and {"secondary", "non_scored"} & tags:
                hygiene_assertions.append(assertion)
            else:
                scored_assertions.append(assertion)
        if scored_assertions:
            copied = dict(case)
            copied["assertions"] = scored_assertions
            scored_cases.append(copied)
        if hygiene_assertions:
            copied = dict(case)
            copied["assertions"] = hygiene_assertions
            hygiene_cases.append(copied)
    return (
        {"version": "0.1-public-real-rc-public-only-scored", "cases": scored_cases},
        {"version": "0.1-public-real-rc-hygiene", "cases": hygiene_cases},
    )


def _merge_with_diagnostic(scored_public: dict[str, Any]) -> dict[str, Any]:
    diagnostic = _load(RELEASE / "docfailbench_v0_1_diagnostic_cases.json")
    seen = {case["case_id"] for case in diagnostic.get("cases", [])}
    additions = [case for case in scored_public["cases"] if case["case_id"] not in seen]
    return {
        "version": "0.1-public-real-rc",
        "release_name": "DocFailBench-v0.1-public-real-rc",
        "description": "Frozen diagnostic v0.1 plus strict-reviewed public-real PDF pages. Secondary hygiene checks are published separately and excluded from the main score.",
        "cases": [*diagnostic.get("cases", []), *additions],
    }


def _package_version(pkg: str, python_exe: str | None = None) -> str | None:
    if python_exe is None:
        try:
            return importlib_metadata.version(pkg)
        except importlib_metadata.PackageNotFoundError:
            return None
    code = (
        "import importlib.metadata as md, sys\n"
        f"pkg={pkg!r}\n"
        "try:\n"
        "    print(md.version(pkg))\n"
        "except Exception:\n"
        "    sys.exit(1)\n"
    )
    try:
        result = subprocess.run(
            [python_exe, "-c", code],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _runtime_stats(raw_dir: Path) -> dict[str, Any]:
    metas = []
    for path in sorted(raw_dir.glob("*.meta.json")):
        metas.append(_load(path).get("metadata", {}))
    elapsed = [item.get("elapsed_seconds") for item in metas if isinstance(item.get("elapsed_seconds"), (int, float))]
    stats: dict[str, Any] = {"runs": len(metas)}
    if elapsed:
        stats.update(
            {
                "elapsed_seconds_total": round(sum(elapsed), 3),
                "elapsed_seconds_mean": round(statistics.mean(elapsed), 3),
                "elapsed_seconds_min": round(min(elapsed), 3),
                "elapsed_seconds_max": round(max(elapsed), 3),
            }
        )
    return stats


def _gpu_info() -> list[dict[str, str]]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total",
                "--format=csv,noheader",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    rows = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) == 3:
            rows.append({"name": parts[0], "driver_version": parts[1], "memory_total": parts[2]})
    return rows


def _metadata() -> dict[str, Any]:
    parser_env = ROOT / ".parser_envs"
    parser_meta = {
        "qwen": {
            "display_name": PARSER_LABELS["qwen"],
            "parser": "qwen_vl_api",
            "execution": "remote_api",
            "model": "qwen-vl-ocr-latest",
            "provider_host": "dashscope.aliyuncs.com",
            "command_entrypoint": "examples/run_qwen_vl.py",
            "runtime": _runtime_stats(STAGE / "raw_qwen_actual"),
        },
        "plain": {
            "display_name": PARSER_LABELS["plain"],
            "parser": "pymupdf4llm",
            "execution": "local_python",
            "pymupdf4llm_version": _package_version("pymupdf4llm"),
            "pymupdf_version": _package_version("pymupdf"),
            "command_entrypoint": "examples/run_pymupdf4llm.py",
            "runtime": _runtime_stats(STAGE / "raw_plain_actual"),
        },
        "bbox": {
            "display_name": PARSER_LABELS["bbox"],
            "parser": "pymupdf4llm_bbox",
            "execution": "local_python",
            "pymupdf4llm_version": _package_version("pymupdf4llm"),
            "pymupdf_version": _package_version("pymupdf"),
            "bbox_coordinate_space": "image pixels at 144 DPI",
            "command_entrypoint": "examples/run_pymupdf4llm_bbox.py",
            "runtime": _runtime_stats(STAGE / "raw_bbox_actual"),
        },
        "docling": {
            "display_name": PARSER_LABELS["docling"],
            "parser": "docling",
            "execution": "local_python",
            "docling_version": _package_version("docling"),
            "ocr_enabled": False,
            "command_entrypoint": "examples/run_docling.py",
            "runtime": _runtime_stats(STAGE / "raw_docling_actual"),
        },
        "marker": {
            "display_name": PARSER_LABELS["marker"],
            "parser": "marker",
            "execution": "local_cli_env",
            "cli": ".parser_envs/marker/Scripts/marker_single.exe",
            "marker_pdf_version": _package_version("marker-pdf", str(parser_env / "marker/Scripts/python.exe")),
            "surya_ocr_version": _package_version("surya-ocr", str(parser_env / "marker/Scripts/python.exe")),
            "torch_version": _package_version("torch", str(parser_env / "marker/Scripts/python.exe")),
            "transformers_version": _package_version("transformers", str(parser_env / "marker/Scripts/python.exe")),
            "command_entrypoint": "examples/run_marker.py",
            "runtime": _runtime_stats(STAGE / "raw_marker_actual"),
        },
        "mineru": {
            "display_name": PARSER_LABELS["mineru"],
            "parser": "mineru",
            "execution": "local_cli_env",
            "cli": ".parser_envs/mineru_latest/Scripts/mineru.exe",
            "mineru_version": _package_version("mineru", str(parser_env / "mineru_latest/Scripts/python.exe")),
            "torch_version": _package_version("torch", str(parser_env / "mineru_latest/Scripts/python.exe")),
            "transformers_version": _package_version("transformers", str(parser_env / "mineru_latest/Scripts/python.exe")),
            "command_entrypoint": "examples/run_mineru.py",
            "runtime": _runtime_stats(STAGE / "raw_mineru_actual"),
        },
        "paddleocr": {
            "display_name": PARSER_LABELS["paddleocr"],
            "parser": "paddleocr",
            "execution": "local_cli_env",
            "cli": ".parser_envs/paddleocr/Scripts/paddleocr.exe",
            "paddleocr_version": _package_version("paddleocr", str(parser_env / "paddleocr/Scripts/python.exe")),
            "paddlepaddle_gpu_version": _package_version("paddlepaddle-gpu", str(parser_env / "paddleocr/Scripts/python.exe")),
            "paddlex_version": _package_version("paddlex", str(parser_env / "paddleocr/Scripts/python.exe")),
            "device": "gpu:0",
            "lang": "ch",
            "command_entrypoint": "examples/run_paddleocr.py",
            "runtime": _runtime_stats(STAGE / "raw_paddleocr_actual"),
        },
    }
    return {
        "release_name": "DocFailBench-v0.1-public-real-rc",
        "generated_at": "2026-05-08",
        "environment": {
            "os": platform.platform(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "python_executable": sys.executable,
            "gpus": _gpu_info(),
        },
        "parsers": parser_meta,
        "notes": [
            "Parser versions are recorded from the local environment used for the baseline run.",
            "Qwen-VL API is a remote model endpoint; qwen-vl-ocr-latest can change over time unless provider-side pinning is available.",
            "The main score excludes secondary page-furniture hygiene checks.",
        ],
    }


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def _evaluate_and_compare(cases_path: Path, prefix: str, compare_name: str, *, public_only: bool = False) -> None:
    result_paths: list[tuple[str, Path]] = []
    for label in PARSER_RESULT_LABELS:
        pred = STAGE / (
            f"actual_predictions_public_real_{label}.json"
            if public_only
            else f"predictions_v0_1_public_real_v2_{label}.json"
        )
        out = STAGE / f"{prefix}_{label}.json"
        _run(["python", "-m", "docfailbench.cli", "evaluate", "--cases", str(cases_path), "--predictions", str(pred), "--out", str(out)])
        result_paths.append((label, out))

    compare_args = ["python", "-m", "docfailbench.cli", "compare"]
    for label, path in result_paths:
        compare_args.extend(["--results", f"{label}={path}"])
    compare_args.extend(
        [
            "--out-json",
            str(STAGE / f"{compare_name}.json"),
            "--out-md",
            str(STAGE / f"{compare_name}.md"),
        ]
    )
    _run(compare_args)


def _copy_release_outputs() -> None:
    shutil.copyfile(STAGE / "compare_v0_1_public_real_rc_7way.json", OUT_COMPARE_JSON)
    shutil.copyfile(STAGE / "compare_v0_1_public_real_rc_7way.md", OUT_COMPARE_MD)
    shutil.copyfile(STAGE / "compare_public_real_rc_scored_7way.json", OUT_PUBLIC_COMPARE_JSON)
    shutil.copyfile(STAGE / "compare_public_real_rc_scored_7way.md", OUT_PUBLIC_COMPARE_MD)


def _leaderboard_rows(compare_path: Path) -> list[dict[str, Any]]:
    data = _load(compare_path)
    rows = []
    for item in data["parsers"]:
        rows.append(
            {
                "label": item["label"],
                "parser": PARSER_LABELS.get(item["label"], item["label"]),
                "passed": item["passed"],
                "failed": item["failed"],
                "score": item["score"],
                "assertion_count": item["assertion_count"],
                "case_count": item["case_count"],
            }
        )
    return sorted(rows, key=lambda item: item["score"], reverse=True)


def _md_table(rows: list[dict[str, Any]]) -> list[str]:
    lines = ["| Parser | Passed | Failed | Score |", "| --- | ---: | ---: | ---: |"]
    for row in rows:
        lines.append(f"| {row['parser']} | {row['passed']} | {row['failed']} | {float(row['score']):.4f} |")
    return lines


def _write_spotcheck(public_cases: dict[str, Any], hygiene_cases: dict[str, Any]) -> None:
    lookup = _assertion_lookup(public_cases["cases"])
    hygiene_ids = {(case["case_id"], assertion["id"]) for case in hygiene_cases["cases"] for assertion in case["assertions"]}
    records = []
    for case_id, assertion_id, decision, note in SPOTCHECKED_ASSERTIONS:
        assertion = lookup.get((case_id, assertion_id))
        records.append(
            {
                "case_id": case_id,
                "assertion_id": assertion_id,
                "type": assertion.get("type") if assertion else None,
                "params": assertion.get("params") if assertion else None,
                "decision": decision,
                "scoring_profile": "secondary_hygiene" if (case_id, assertion_id) in hygiene_ids else "main" if assertion else "removed",
                "note": note,
            }
        )
    by_decision = Counter(record["decision"] for record in records)
    payload = {
        "release_name": "DocFailBench-v0.1-public-real-rc",
        "review_date": "2026-05-08",
        "reviewer": "Codex strict visual spot-check",
        "sample_count": len(records),
        "decision_counts": dict(sorted(by_decision.items())),
        "policy": {
            "main_score": "Content and structure assertions only.",
            "secondary_hygiene": "Low-value page-furniture text_absence checks are retained separately and excluded from the main leaderboard.",
        },
        "records": records,
    }
    _write_json(OUT_SPOTCHECK_JSON, payload)

    lines = [
        "# Public-Real RC Spot-Check",
        "",
        f"- Release: `{payload['release_name']}`",
        f"- Review date: {payload['review_date']}",
        f"- Sampled assertions: {payload['sample_count']}",
        f"- Decisions: {', '.join(f'{k}={v}' for k, v in sorted(by_decision.items()))}",
        "",
        "## Policy",
        "",
        "- Main score keeps visible content and structure assertions.",
        "- Page-furniture `text_absence` checks are published as secondary hygiene and excluded from the main leaderboard.",
        "- Ambiguous or visually wrong reading-order anchors are edited or removed before freeze.",
        "",
        "## Records",
        "",
        "| Case | Assertion | Type | Decision | Profile | Note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        lines.append(
            f"| `{record['case_id']}` | `{record['assertion_id']}` | `{record['type'] or ''}` | "
            f"{record['decision']} | {record['scoring_profile']} | {record['note']} |"
        )
    OUT_SPOTCHECK_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_card(public_cases: dict[str, Any], merged_cases: dict[str, Any], hygiene_cases: dict[str, Any]) -> None:
    public_assertion_count = sum(len(case.get("assertions", [])) for case in public_cases["cases"])
    merged_assertion_count = sum(len(case.get("assertions", [])) for case in merged_cases["cases"])
    hygiene_assertion_count = sum(len(case.get("assertions", [])) for case in hygiene_cases["cases"])
    source_counts = Counter(Path(case["document"].get("path", "")).name for case in public_cases["cases"])
    doc_counts = Counter(case.get("profile", {}).get("document_type", "unknown") for case in public_cases["cases"])
    type_counts = Counter(assertion["type"] for case in public_cases["cases"] for assertion in case.get("assertions", []))
    public_rows = _leaderboard_rows(OUT_PUBLIC_COMPARE_JSON)
    merged_rows = _leaderboard_rows(OUT_COMPARE_JSON)

    lines = [
        "# DocFailBench v0.1 Public-Real RC Card",
        "",
        "`DocFailBench-v0.1-public-real-rc` freezes the first real-public PDF expansion layer on top of the diagnostic v0.1 set.",
        "",
        "## Frozen Artifacts",
        "",
        f"- Main cases: `{OUT_CASES.relative_to(ROOT)}`",
        f"- Main leaderboard: `{OUT_COMPARE_MD.relative_to(ROOT)}`",
        f"- Machine-readable leaderboard: `{OUT_COMPARE_JSON.relative_to(ROOT)}`",
        f"- Public-only leaderboard: `{OUT_PUBLIC_COMPARE_MD.relative_to(ROOT)}`",
        f"- Secondary hygiene cases: `{OUT_HYGIENE_CASES.relative_to(ROOT)}`",
        f"- Parser metadata: `{OUT_METADATA.relative_to(ROOT)}`",
        f"- Spot-check report: `{OUT_SPOTCHECK_MD.relative_to(ROOT)}`",
        "",
        "## Scope",
        "",
        f"- Public-real pages: {len(public_cases['cases'])}",
        f"- Public-real main assertions: {public_assertion_count}",
        f"- Secondary hygiene assertions excluded from main score: {hygiene_assertion_count}",
        f"- Merged diagnostic + public-real cases: {len(merged_cases['cases'])}",
        f"- Merged main assertions: {merged_assertion_count}",
        "",
        "## Source Mix",
        "",
        "| Source PDF | Pages |",
        "| --- | ---: |",
    ]
    for source, count in sorted(source_counts.items()):
        lines.append(f"| `{source}` | {count} |")
    lines.extend(["", "## Document Types", "", "| Type | Pages |", "| --- | ---: |"])
    for doc_type, count in sorted(doc_counts.items()):
        lines.append(f"| `{doc_type}` | {count} |")
    lines.extend(["", "## Main Assertion Mix", "", "| Assertion type | Count |", "| --- | ---: |"])
    for a_type, count in sorted(type_counts.items()):
        lines.append(f"| `{a_type}` | {count} |")
    lines.extend(["", "## Public-Real Only Leaderboard", ""])
    lines.extend(_md_table(public_rows))
    lines.extend(["", "## Merged Leaderboard", ""])
    lines.extend(_md_table(merged_rows))
    lines.extend(
        [
            "",
            "## Review Standard",
            "",
            "- `table_cell_exists` checks visible form/table fields that should remain cell-like in Markdown.",
            "- `table_grid_cell` and `table_shape` are limited to the visually unambiguous NIST SP 800-53 revision table.",
            "- `reading_order` uses short page-local anchors and was spot-checked visually on forms, two-column legal text, and technical reports.",
            "- `caption_binding` is used once for a unique figure/caption pair.",
            "- Page-furniture `text_absence` checks are secondary hygiene checks and do not affect the main leaderboard.",
            "",
            "## Remaining Gap",
            "",
            "This RC is stronger than the synthetic-heavy diagnostic release, but it is still government-source heavy. The next community step is to add 20-40 non-government public pages from sources such as PMC OA, OpenStax, PubTables-1M, ACL Anthology, DocLayNet, BLS, and permissive arXiv/OpenReview papers.",
        ]
    )
    OUT_CARD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    public_cases_all = _load(CASES)
    scored_public, hygiene_cases = _split_scored_cases(public_cases_all)
    merged = _merge_with_diagnostic(scored_public)

    _write_json(STAGE / "public_real_rc_scored_cases.json", scored_public)
    _write_json(STAGE / "public_real_rc_hygiene_cases.json", hygiene_cases)
    _write_json(MERGED_CASES, merged)
    _write_json(OUT_CASES, merged)
    _write_json(OUT_HYGIENE_CASES, hygiene_cases)

    _evaluate_and_compare(STAGE / "public_real_rc_scored_cases.json", "actual_eval_public_real_rc_scored", "compare_public_real_rc_scored_7way", public_only=True)
    _evaluate_and_compare(MERGED_CASES, "eval_v0_1_public_real_rc", "compare_v0_1_public_real_rc_7way")
    _copy_release_outputs()

    _write_json(OUT_METADATA, _metadata())
    _write_spotcheck(scored_public, hygiene_cases)
    _write_card(scored_public, merged, hygiene_cases)

    manifest = {
        "release_name": "DocFailBench-v0.1-public-real-rc",
        "files": {
            str(path.relative_to(ROOT)): _sha256(path)
            for path in [
                OUT_CASES,
                OUT_COMPARE_JSON,
                OUT_COMPARE_MD,
                OUT_PUBLIC_COMPARE_JSON,
                OUT_PUBLIC_COMPARE_MD,
                OUT_HYGIENE_CASES,
                OUT_METADATA,
                OUT_SPOTCHECK_JSON,
                OUT_SPOTCHECK_MD,
                OUT_CARD,
            ]
        },
    }
    _write_json(RELEASE / "docfailbench_v0_1_public_real_rc_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
