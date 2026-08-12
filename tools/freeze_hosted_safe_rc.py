from __future__ import annotations

import copy
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from docfailbench.compare import compare_results, render_markdown
from docfailbench.evaluator import evaluate, to_dict
from docfailbench.hosted_safe import (
    EXCLUDED_CASES,
    HF_PAGE_PREFIX,
    HOSTED_SAFE_RELEASE_NAME,
    PARENT_CASES_CANONICAL_LF_SHA256,
    PARENT_GIT_COMMIT,
    PARENT_RELEASE_NAME,
    assert_parent_identity,
    build_source_pages,
    derive_hosted_safe_cases,
    write_json_lf,
)
from docfailbench.hosted_submission import RETRY_POLICY
from docfailbench.io import load_cases, load_predictions


RELEASE = ROOT / "data" / "releases"
WORK = ROOT / "runs" / "hosted_safe_rc"
PARSER_LABELS = ("qwen", "plain", "paddleocr", "mineru", "marker", "docling", "bbox")
PARENT_PREFIX = "docfailbench_v0_1_combined_public_rc"
PREFIX = "docfailbench_v0_1_hosted_safe_rc"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _write_text_lf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build(root: Path = ROOT) -> dict[str, Any]:
    release = root / "data" / "releases"
    work = root / "runs" / "hosted_safe_rc"
    source_pages_dir = work / "source_pages"
    release.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    parent_cases_path = release / f"{PARENT_PREFIX}_cases.json"
    assert_parent_identity(parent_cases_path)
    parent_cases = _load(parent_cases_path)
    cases_payload = derive_hosted_safe_cases(parent_cases)
    cases_path = release / f"{PREFIX}_cases.json"
    write_json_lf(cases_path, cases_payload)

    source_manifest = build_source_pages(
        cases_payload,
        root=root,
        output_dir=source_pages_dir,
    )
    source_manifest_path = release / f"{PREFIX}_source_manifest.json"
    write_json_lf(source_manifest_path, source_manifest)
    expected_page_files = {
        f"{row['sha256']}.pdf" for row in source_manifest["pages"]
    }
    actual_page_files = {path.name for path in source_pages_dir.glob("*.pdf")}
    if actual_page_files != expected_page_files:
        raise ValueError("Hosted-safe source page directory contains stale or missing PDFs")

    assertion_count = sum(
        len(case.get("assertions", [])) for case in cases_payload["cases"]
    )
    profile = {
        "release_name": HOSTED_SAFE_RELEASE_NAME,
        "version": "0.1-hosted-safe-rc",
        "status": "release_candidate_frozen_hosted_safe",
        "release_date": "2026-08-12",
        "parent": {
            "release_name": PARENT_RELEASE_NAME,
            "git_commit": PARENT_GIT_COMMIT,
            "cases_path": _rel(parent_cases_path, root),
            "cases_sha256_canonical_lf": PARENT_CASES_CANONICAL_LF_SHA256,
        },
        "counts": {
            "cases": len(cases_payload["cases"]),
            "assertions": assertion_count,
            "source_pages": len(source_manifest["pages"]),
        },
        "exclusions": [
            {"case_id": case_id, "reason": reason}
            for case_id, reason in EXCLUDED_CASES.items()
        ],
        "retry_policy": copy.deepcopy(RETRY_POLICY),
        "source_bundle": {
            "manifest_path": _rel(source_manifest_path, root),
            "hf_path_prefix": HF_PAGE_PREFIX,
            "total_bytes": sum(row["size_bytes"] for row in source_manifest["pages"]),
            "largest_page_bytes": max(
                row["size_bytes"] for row in source_manifest["pages"]
            ),
        },
        "license_policy": {
            "included": "redistribution-compatible public, government, synthetic, and placeholder fixtures",
            "excluded": ["arxiv-non-exclusive", "CC BY-NC-SA"],
            "attribution_source": _rel(source_manifest_path, root),
        },
    }
    profile_path = release / f"{PREFIX}_profile.json"
    write_json_lf(profile_path, profile)

    hosted_case_ids = [case["case_id"] for case in cases_payload["cases"]]
    case_objects = load_cases(cases_path)
    result_paths: dict[str, Path] = {}
    prediction_paths: dict[str, Path] = {}
    baseline_summaries: dict[str, dict[str, Any]] = {}
    for label in PARSER_LABELS:
        parent_prediction_path = release / f"{PARENT_PREFIX}_predictions_{label}.json"
        parent_prediction_payload = _load(parent_prediction_path)
        parent_predictions = parent_prediction_payload.get("predictions")
        if not isinstance(parent_predictions, list):
            raise ValueError(f"Parent predictions are missing for {label}")
        parent_by_id: dict[str, dict[str, Any]] = {}
        for prediction in parent_predictions:
            case_id = prediction["case_id"]
            if case_id in parent_by_id:
                raise ValueError(f"Duplicate parent prediction for {label}: {case_id}")
            parent_by_id[case_id] = prediction
        missing = [case_id for case_id in hosted_case_ids if case_id not in parent_by_id]
        if missing:
            raise ValueError(f"Parent predictions for {label} miss {len(missing)} cases")

        prediction_payload = {
            "release_name": HOSTED_SAFE_RELEASE_NAME,
            "parser_label": label,
            "display_name": parent_prediction_payload.get("display_name", label),
            "parent_prediction_artifact": {
                "path": _rel(parent_prediction_path, root),
                "sha256": _sha256(parent_prediction_path),
            },
            "predictions": [
                copy.deepcopy(parent_by_id[case_id]) for case_id in hosted_case_ids
            ],
        }
        prediction_path = release / f"{PREFIX}_predictions_{label}.json"
        write_json_lf(prediction_path, prediction_payload)
        prediction_paths[label] = prediction_path

        run = evaluate(case_objects, load_predictions(prediction_path))
        result_payload = to_dict(run)
        result_path = release / f"{PREFIX}_eval_{label}.json"
        write_json_lf(result_path, result_payload)
        result_paths[label] = result_path
        baseline_summaries[label] = {
            "passed": run.summary["passed"],
            "failed": run.summary["failed"],
            "score": run.summary["score"],
        }

    comparison = compare_results(
        [(label, str(result_paths[label])) for label in PARSER_LABELS]
    )
    leaderboard_json_path = release / f"{PREFIX}_leaderboard.json"
    leaderboard_md_path = release / f"{PREFIX}_leaderboard.md"
    write_json_lf(leaderboard_json_path, comparison)
    _write_text_lf(leaderboard_md_path, render_markdown(comparison))

    committed_files = [
        cases_path,
        profile_path,
        source_manifest_path,
        leaderboard_json_path,
        leaderboard_md_path,
        *[prediction_paths[label] for label in PARSER_LABELS],
        *[result_paths[label] for label in PARSER_LABELS],
    ]
    manifest = {
        "release_name": HOSTED_SAFE_RELEASE_NAME,
        "status": "release_candidate_frozen_hosted_safe",
        "parent": {
            "release_name": PARENT_RELEASE_NAME,
            "git_commit": PARENT_GIT_COMMIT,
            "cases_sha256_canonical_lf": PARENT_CASES_CANONICAL_LF_SHA256,
        },
        "counts": {
            "cases": len(cases_payload["cases"]),
            "assertions": assertion_count,
            "source_pages": len(source_manifest["pages"]),
            "parsers": len(PARSER_LABELS),
        },
        "source_manifest": {
            "path": _rel(source_manifest_path, root),
            "sha256": _sha256(source_manifest_path),
            "total_bytes": sum(row["size_bytes"] for row in source_manifest["pages"]),
        },
        "profile": {
            "path": _rel(profile_path, root),
            "sha256": _sha256(profile_path),
        },
        "baselines": baseline_summaries,
        "files": {
            _rel(path, root): _sha256(path)
            for path in sorted(committed_files, key=lambda item: _rel(item, root))
        },
    }
    manifest_path = release / f"{PREFIX}_manifest.json"
    write_json_lf(manifest_path, manifest)

    summary = {
        "release_name": HOSTED_SAFE_RELEASE_NAME,
        "cases": len(cases_payload["cases"]),
        "assertions": assertion_count,
        "source_pages": len(source_manifest["pages"]),
        "parsers": len(PARSER_LABELS),
        "manifest": _rel(manifest_path, root),
    }
    write_json_lf(
        work / "freeze_summary.json",
        {
            **summary,
            "environment": {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
            },
        },
    )
    return summary


def main() -> int:
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
