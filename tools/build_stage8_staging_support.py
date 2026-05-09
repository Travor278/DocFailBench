from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "runs" / "stage8_non_gov_public_batch2"
CASES_PATH = STAGE / "reviewed_non_gov_public_batch2_cases.json"
SOURCES_PATH = STAGE / "non_gov_public_batch2_sources.json"
COMPARE_PATH = STAGE / "compare_stage8_second_review_7parser.json"

SOURCE_MANIFEST_JSON = STAGE / "stage8_source_license_manifest.json"
SOURCE_MANIFEST_MD = STAGE / "stage8_source_license_manifest.md"
PARSER_METADATA_JSON = STAGE / "stage8_parser_metadata.json"
PARSER_METADATA_MD = STAGE / "stage8_parser_metadata.md"
STAGING_MANIFEST_JSON = STAGE / "stage8_staging_manifest.json"
STAGING_MANIFEST_MD = STAGE / "stage8_staging_manifest.md"

PARSER_FILES = {
    "qwen": {
        "display_name": "Qwen-VL API",
        "prediction": STAGE / "raw" / "predictions_non_gov_public_batch2_qwen_vl_api.json",
        "result": STAGE / "results_stage8_qwen_vl_api_second_review.json",
        "report": STAGE / "report_stage8_qwen_vl_api_second_review.html",
    },
    "plain": {
        "display_name": "PyMuPDF plain",
        "prediction": STAGE / "raw" / "predictions_non_gov_public_batch2_plain.json",
        "result": STAGE / "results_stage8_plain_second_review.json",
        "report": STAGE / "report_stage8_plain_second_review.html",
    },
    "paddleocr": {
        "display_name": "PaddleOCR",
        "prediction": STAGE / "raw" / "predictions_non_gov_public_batch2_paddleocr.json",
        "result": STAGE / "results_stage8_paddleocr_second_review.json",
        "report": STAGE / "report_stage8_paddleocr_second_review.html",
    },
    "mineru": {
        "display_name": "MinerU",
        "prediction": STAGE / "raw" / "predictions_non_gov_public_batch2_mineru.json",
        "result": STAGE / "results_stage8_mineru_second_review.json",
        "report": STAGE / "report_stage8_mineru_second_review.html",
    },
    "marker": {
        "display_name": "Marker",
        "prediction": STAGE / "raw" / "predictions_non_gov_public_batch2_marker.json",
        "result": STAGE / "results_stage8_marker_second_review.json",
        "report": STAGE / "report_stage8_marker_second_review.html",
    },
    "docling": {
        "display_name": "Docling",
        "prediction": STAGE / "raw" / "predictions_non_gov_public_batch2_docling.json",
        "result": STAGE / "results_stage8_docling_second_review.json",
        "report": STAGE / "report_stage8_docling_second_review.html",
    },
    "bbox": {
        "display_name": "PyMuPDF bbox",
        "prediction": STAGE / "raw" / "predictions_non_gov_public_batch2_bbox.json",
        "result": STAGE / "results_stage8_bbox_second_review.json",
        "report": STAGE / "report_stage8_bbox_second_review.html",
    },
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _package_version(package: str, python_exe: str | None = None) -> str:
    exe = python_exe or sys.executable
    try:
        result = subprocess.run(
            [exe, "-m", "pip", "show", package],
            check=False,
            text=True,
            capture_output=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    if result.returncode != 0:
        return "not_installed"
    for line in result.stdout.splitlines():
        if line.startswith("Version:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def _nvidia_smi() -> dict[str, str]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ],
            check=False,
            text=True,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if result.returncode != 0 or not result.stdout.strip():
        return {}
    first = result.stdout.splitlines()[0]
    parts = [p.strip() for p in first.split(",")]
    if len(parts) < 3:
        return {"raw": first}
    return {"name": parts[0], "memory_total": parts[1], "driver_version": parts[2]}


def _prediction_stats(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    payload = _load(path)
    predictions = payload.get("predictions", [])
    returncodes = Counter(p.get("metadata", {}).get("returncode") for p in predictions)
    elapsed = [
        float(p.get("metadata", {}).get("elapsed_seconds", 0))
        for p in predictions
        if isinstance(p.get("metadata", {}).get("elapsed_seconds"), (int, float))
    ]
    first_meta = predictions[0].get("metadata", {}) if predictions else {}
    return {
        "exists": True,
        "sha256": _sha256(path),
        "prediction_count": len(predictions),
        "returncodes": {str(k): v for k, v in returncodes.items()},
        "elapsed_seconds_total": round(sum(elapsed), 3),
        "elapsed_seconds_mean": round(sum(elapsed) / len(elapsed), 3) if elapsed else 0.0,
        "first_metadata": {
            key: first_meta.get(key)
            for key in (
                "parser",
                "model",
                "base_url_host",
                "command",
                "document_path",
                "page",
                "output_source",
            )
            if key in first_meta
        },
    }


def _source_id(case_id: str) -> str:
    stem = case_id.removeprefix("non_gov_public_batch2_")
    return stem.rsplit("_p", 1)[0]


def build_source_manifest(cases: list[dict[str, Any]], sources_payload: dict[str, Any]) -> dict[str, Any]:
    pages_by_source: dict[str, set[int]] = defaultdict(set)
    case_counts: Counter[str] = Counter()
    assertion_counts: Counter[str] = Counter()
    for case in cases:
        source_id = _source_id(case["case_id"])
        case_counts[source_id] += 1
        assertion_counts[source_id] += len(case.get("assertions", []))
        page = case.get("document", {}).get("page")
        if isinstance(page, int):
            pages_by_source[source_id].add(page)

    sources = []
    for source in sources_payload.get("sources", []):
        path = ROOT / source["path"]
        actual_sha = _sha256(path) if path.exists() else ""
        sources.append(
            {
                **source,
                "selected_stage8_pages": sorted(pages_by_source[source["source_id"]]),
                "stage8_case_count": case_counts[source["source_id"]],
                "stage8_assertion_count": assertion_counts[source["source_id"]],
                "pdf_exists": path.exists(),
                "sha256_verified": bool(source.get("sha256") and source.get("sha256") == actual_sha),
                "actual_sha256": actual_sha,
                "license_status": "inherits_stage7_verified_notice_check",
            }
        )
    payload = {
        "name": "Stage8 batch2 source/license manifest",
        "status": "audit_source_included_in_combined_public_rc",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(sources),
        "case_count": len(cases),
        "assertion_count": sum(len(c.get("assertions", [])) for c in cases),
        "sources": sources,
        "release_gate_notes": [
            "Stage8 reuses the already cached Stage7 public PDFs and source-license evidence.",
            "The accepted Stage8 subset is included in DocFailBench-v0.1-combined-public-rc.",
            "OpenStax Calculus remains CC BY-NC-SA 4.0 and must keep noncommercial/ShareAlike terms visible.",
        ],
    }
    _dump(SOURCE_MANIFEST_JSON, payload)

    lines = [
        "# Stage8 Source And License Manifest",
        "",
        "Status: audit source included in combined public RC.",
        "",
        f"- Sources: {payload['source_count']}",
        f"- Cases with accepted assertions: {payload['case_count']}",
        f"- Assertions: {payload['assertion_count']}",
        "",
        "| Source | Accepted pages | Assertions | License | SHA-256 | Source page |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in sources:
        pages = ", ".join(str(p) for p in row["selected_stage8_pages"]) or "-"
        sha = "ok" if row["sha256_verified"] else "check"
        lines.append(
            f"| `{row['source_id']}` | {pages} | {row['stage8_assertion_count']} | "
            f"{row['license']} | {sha} | {row['source_page']} |"
        )
    lines.extend(["", "## Release Gate Notes", ""])
    lines.extend(f"- {note}" for note in payload["release_gate_notes"])
    SOURCE_MANIFEST_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


def build_parser_metadata(compare: dict[str, Any]) -> dict[str, Any]:
    parser_env = ROOT / ".parser_envs"
    gpu = _nvidia_smi()
    package_versions = {
        "python": platform.python_version(),
        "docfailbench_python": sys.executable,
        "docling": _package_version("docling"),
        "pymupdf": _package_version("pymupdf"),
        "marker_pdf": _package_version("marker-pdf", str(parser_env / "marker" / "Scripts" / "python.exe")),
        "mineru": _package_version("mineru", str(parser_env / "mineru_latest" / "Scripts" / "python.exe")),
        "paddleocr": _package_version("paddleocr", str(parser_env / "paddleocr" / "Scripts" / "python.exe")),
        "paddlepaddle_gpu": _package_version("paddlepaddle-gpu", str(parser_env / "paddleocr" / "Scripts" / "python.exe")),
    }
    rows = []
    compare_by_label = {row.get("label", row.get("parser")): row for row in compare.get("parsers", [])}
    for label, info in PARSER_FILES.items():
        stats = _prediction_stats(info["prediction"])
        score_row = compare_by_label.get(label, {})
        row = {
            "label": label,
            "display_name": info["display_name"],
            "score": score_row.get("score"),
            "passed": score_row.get("passed"),
            "failed": score_row.get("failed"),
            "assertion_count": score_row.get("assertion_count"),
            "case_count": score_row.get("case_count"),
            "prediction_file": _rel(info["prediction"]),
            "result_file": _rel(info["result"]),
            "html_report": _rel(info["report"]),
            "prediction_stats": stats,
        }
        if label == "qwen":
            meta = stats.get("first_metadata", {})
            row["api_metadata"] = {
                "endpoint_host": meta.get("base_url_host"),
                "requested_model": meta.get("model"),
                "run_note": "Hosted latest alias; provider-side backend may drift.",
            }
        if label == "paddleocr":
            row["device_note"] = "Full Stage8 rerun used DOCFAILBENCH_PADDLEOCR_DEVICE=gpu:0 on local GPU."
        rows.append(row)

    payload = {
        "name": "Stage8 batch2 parser metadata",
        "status": "audit_source_included_in_combined_public_rc",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "python_executable": sys.executable,
            "gpu": gpu,
            "package_versions": package_versions,
        },
        "parsers": rows,
        "compare_file": _rel(COMPARE_PATH),
    }
    _dump(PARSER_METADATA_JSON, payload)

    lines = [
        "# Stage8 Parser Metadata",
        "",
        "Status: audit source included in combined public RC.",
        "",
        f"- Python: `{sys.executable}`",
        f"- GPU: {gpu.get('name', 'not recorded')} {gpu.get('memory_total', '')}".rstrip(),
        f"- Compare: `{_rel(COMPARE_PATH)}`",
        "",
        "| Parser | Passed | Failed | Score | Predictions | Notes |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        notes = []
        if row["label"] == "qwen":
            api = row.get("api_metadata", {})
            notes.append(f"{api.get('requested_model')} on {api.get('endpoint_host')}")
        if row["label"] == "paddleocr":
            notes.append("GPU run: gpu:0")
        stats = row["prediction_stats"]
        lines.append(
            f"| {row['display_name']} | {row['passed']} | {row['failed']} | "
            f"{float(row['score'] or 0):.4f} | {stats.get('prediction_count', 0)} | "
            f"{'; '.join(notes) or '-'} |"
        )
    lines.extend(
        [
            "",
            "## Package Versions",
            "",
        ]
    )
    for key, value in package_versions.items():
        lines.append(f"- `{key}`: {value}")
    PARSER_METADATA_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


def build_staging_manifest(
    cases: list[dict[str, Any]],
    compare: dict[str, Any],
    source_manifest: dict[str, Any],
    parser_metadata: dict[str, Any],
) -> dict[str, Any]:
    assertion_types = Counter(a["type"] for c in cases for a in c.get("assertions", []))
    payload = {
        "name": "Stage8 non-government public batch2 staging manifest",
        "status": "second_review_accepted_full_parser_baselined_included_in_combined_public_rc",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "rendered_pages_in_queue": 24,
            "accepted_cases": len(cases),
            "accepted_assertions": sum(len(c.get("assertions", [])) for c in cases),
            "sources": source_manifest["source_count"],
            "parsers": len(parser_metadata["parsers"]),
        },
        "assertion_types": dict(assertion_types),
        "artifacts": {
            "cases": _rel(CASES_PATH),
            "source_manifest_json": _rel(SOURCE_MANIFEST_JSON),
            "source_manifest_md": _rel(SOURCE_MANIFEST_MD),
            "parser_metadata_json": _rel(PARSER_METADATA_JSON),
            "parser_metadata_md": _rel(PARSER_METADATA_MD),
            "compare_json": _rel(COMPARE_PATH),
            "compare_md": _rel(STAGE / "compare_stage8_second_review_7parser.md"),
            "first_review": _rel(STAGE / "stage8_codex_first_review.md"),
            "second_review": _rel(STAGE / "stage8_human_second_review_accepted.md"),
        },
        "leaderboard_rows": sorted(
            [
                {
                    "label": row["label"],
                    "parser": row["parser"],
                    "passed": row["passed"],
                    "failed": row["failed"],
                    "score": row["score"],
                }
                for row in compare.get("parsers", [])
            ],
            key=lambda row: (-row["score"], row["label"]),
        ),
        "release_gate_notes": [
            "Stage8 remains an audit/staging workspace, not a standalone release.",
            "Its second-reviewed subset is included in DocFailBench-v0.1-combined-public-rc with profile labels preserved.",
            "Future Stage8-style batches should create frozen combined artifacts under data/releases/ before README leaderboard claims change.",
        ],
    }
    _dump(STAGING_MANIFEST_JSON, payload)

    lines = [
        "# Stage8 Staging Manifest",
        "",
        "Status: second-review accepted, full-parser-baselined, included in combined public RC as an audit source.",
        "",
        f"- Accepted cases: {payload['counts']['accepted_cases']}",
        f"- Accepted assertions: {payload['counts']['accepted_assertions']}",
        f"- Sources: {payload['counts']['sources']}",
        f"- Parser baselines: {payload['counts']['parsers']}",
        f"- Assertion mix: {payload['assertion_types']}",
        "",
        "## 7-Parser Results",
        "",
        "| Parser | Passed | Failed | Score |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in payload["leaderboard_rows"]:
        lines.append(f"| {row['label']} | {row['passed']} | {row['failed']} | {row['score']:.4f} |")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
        ]
    )
    for key, value in payload["artifacts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Release Gate Notes", ""])
    lines.extend(f"- {note}" for note in payload["release_gate_notes"])
    STAGING_MANIFEST_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


def build() -> dict[str, Any]:
    cases_payload = _load(CASES_PATH)
    cases = cases_payload.get("cases", [])
    sources = _load(SOURCES_PATH)
    compare = _load(COMPARE_PATH)
    source_manifest = build_source_manifest(cases, sources)
    parser_metadata = build_parser_metadata(compare)
    staging_manifest = build_staging_manifest(cases, compare, source_manifest, parser_metadata)
    return {
        "source_manifest": _rel(SOURCE_MANIFEST_JSON),
        "parser_metadata": _rel(PARSER_METADATA_JSON),
        "staging_manifest": _rel(STAGING_MANIFEST_JSON),
        "status": staging_manifest["status"],
    }


def main() -> int:
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
