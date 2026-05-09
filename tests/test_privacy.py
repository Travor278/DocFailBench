from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from docfailbench.evaluator import evaluate
from docfailbench.io import dump_json, load_cases, load_predictions
from docfailbench.privacy import (
    build_private_profile,
    hash_assertion_id,
    hash_case_id,
    redact_benchmark_run,
    redact_predictions,
)

_CASES = "data/cases/sample_cases.json"
_PREDICTIONS = "data/predictions/sample_parser_predictions.json"
_ORIGINAL_CASE_ID = "zh_paper_double_column_001_p3"
_ORIGINAL_ASSERTION_ID = "title_present"
_SAMPLE_CONTENT = "\u57fa\u4e8e\u89c6\u89c9\u8bed\u8a00\u6a21\u578b"
_PRIVATE_MARKDOWN = "secret parser markdown"

_FAKE_PRIVATE_PARSER = r'''\
import argparse
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--input", required=True)
ap.add_argument("--output", required=True)
ap.add_argument("--case-id", default="")
args = ap.parse_args()

Path(args.output).write_text(
    "secret parser markdown for " + args.case_id,
    encoding="utf-8",
)
'''


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_cli(*args: object, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "docfailbench.cli", *[str(arg) for arg in args]],
        cwd=_repo_root(),
        check=check,
        capture_output=True,
        text=True,
    )


def _write_private_manifest(tmp_path: Path) -> Path:
    script = tmp_path / "fake_private_parser.py"
    script.write_text(_FAKE_PRIVATE_PARSER, encoding="utf-8")
    command = (
        f'"{sys.executable}" "{script}" '
        '--input "$document_path" --output "$output_path" --case-id "$case_id"'
    )
    manifest = {
        "parsers": [
            {
                "name": "private_fake",
                "output_kind": "markdown",
                "timeout_seconds": 30,
                "command": command,
            }
        ]
    }
    path = tmp_path / "manifest.json"
    dump_json(path, manifest)
    return path


def test_private_hashes_are_stable_and_salted() -> None:
    case_id = hash_case_id("customer_contract_case_001")
    assert case_id == hash_case_id("customer_contract_case_001")
    assert case_id.startswith("case_")
    assert hash_case_id("customer_contract_case_001", salt="team-a") != case_id

    assertion_id = hash_assertion_id("payment_terms", "customer_contract_case_001")
    assert assertion_id.startswith("assertion_")
    assert assertion_id == hash_assertion_id("payment_terms", "customer_contract_case_001")


def test_redacted_benchmark_run_drops_contentful_fields() -> None:
    run = evaluate(load_cases(_CASES), load_predictions(_PREDICTIONS))
    payload = redact_benchmark_run(run)
    text = json.dumps(payload, ensure_ascii=False)

    assert payload["private_mode"] is True
    assert payload["case_results"][0]["case_id"].startswith("case_")
    assert payload["case_results"][0]["results"][0]["assertion_id"].startswith("assertion_")
    assert payload["case_results"][0]["results"][0]["message"] in {"passed", "failed"}
    assert payload["case_results"][0]["results"][0]["evidence"] == {"private": True}
    assert _ORIGINAL_CASE_ID not in text
    assert _ORIGINAL_ASSERTION_ID not in text
    assert "data/source_pdfs" not in text
    assert _SAMPLE_CONTENT not in text


def test_private_profile_is_aggregate_only() -> None:
    run = evaluate(load_cases(_CASES), load_predictions(_PREDICTIONS))
    profile = build_private_profile(run, salt="demo")
    text = json.dumps(profile, ensure_ascii=False)

    assert profile["private_mode"] is True
    assert profile["private_salt_used"] is True
    assert "case_results" not in profile
    assert set(profile["case_scores"]).pop().startswith("case_")
    assert _ORIGINAL_CASE_ID not in text
    assert _ORIGINAL_ASSERTION_ID not in text
    assert _SAMPLE_CONTENT not in text


def test_redacted_predictions_drop_parser_output() -> None:
    redacted = redact_predictions(load_predictions(_PREDICTIONS))
    text = json.dumps({"predictions": redacted}, ensure_ascii=False)

    assert redacted[0] == {
        "case_id": hash_case_id(_ORIGINAL_CASE_ID),
        "parser": "sample_parser",
        "private": True,
    }
    assert "markdown" not in text
    assert "elements" not in text
    assert "metadata" not in text
    assert _ORIGINAL_CASE_ID not in text
    assert _SAMPLE_CONTENT not in text


def test_private_evaluate_cli_writes_redacted_results_and_profile(tmp_path: Path) -> None:
    out = tmp_path / "results.private.json"
    profile = tmp_path / "profile.private.json"

    completed = _run_cli(
        "evaluate",
        "--cases",
        _CASES,
        "--predictions",
        _PREDICTIONS,
        "--out",
        out,
        "--private",
        "--private-profile",
        profile,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    text = out.read_text(encoding="utf-8") + profile.read_text(encoding="utf-8")
    assert "(private mode)" in completed.stdout
    assert payload["private_mode"] is True
    assert profile.exists()
    assert _ORIGINAL_CASE_ID not in text
    assert _ORIGINAL_ASSERTION_ID not in text
    assert _SAMPLE_CONTENT not in text


def test_private_evaluate_rejects_html(tmp_path: Path) -> None:
    completed = _run_cli(
        "evaluate",
        "--cases",
        _CASES,
        "--predictions",
        _PREDICTIONS,
        "--out",
        tmp_path / "results.json",
        "--html",
        tmp_path / "report.html",
        "--private",
        check=False,
    )

    assert completed.returncode == 1
    assert "--html is not allowed in private mode" in completed.stdout


def test_private_baseline_cli_writes_only_redacted_artifacts(tmp_path: Path) -> None:
    manifest = _write_private_manifest(tmp_path)
    predictions = tmp_path / "predictions.private.json"
    results = tmp_path / "results.private.json"
    profile = tmp_path / "profile.private.json"

    _run_cli(
        "baseline",
        "--manifest",
        manifest,
        "--parser",
        "private_fake",
        "--cases",
        _CASES,
        "--out",
        predictions,
        "--results",
        results,
        "--private-profile",
        profile,
        "--private",
    )

    pred_payload = json.loads(predictions.read_text(encoding="utf-8"))
    text = (
        predictions.read_text(encoding="utf-8")
        + results.read_text(encoding="utf-8")
        + profile.read_text(encoding="utf-8")
    )
    assert pred_payload["private_mode"] is True
    assert pred_payload["predictions"][0]["case_id"].startswith("case_")
    assert "markdown" not in text
    assert "elements" not in text
    assert "metadata" not in text
    assert _PRIVATE_MARKDOWN not in text
    assert _ORIGINAL_CASE_ID not in text
    assert _ORIGINAL_ASSERTION_ID not in text


def test_private_baseline_rejects_contentful_outputs(tmp_path: Path) -> None:
    manifest = _write_private_manifest(tmp_path)
    common = [
        "baseline",
        "--manifest",
        manifest,
        "--parser",
        "private_fake",
        "--cases",
        _CASES,
        "--out",
        tmp_path / "predictions.json",
        "--private",
    ]

    raw_completed = _run_cli(*common, "--raw-dir", tmp_path / "raw", check=False)
    assert raw_completed.returncode == 1
    assert "--raw-dir is not allowed in private mode" in raw_completed.stdout

    html_completed = _run_cli(*common, "--html", tmp_path / "report.html", check=False)
    assert html_completed.returncode == 1
    assert "--html is not allowed in private mode" in html_completed.stdout


def test_compare_cli_accepts_private_results(tmp_path: Path) -> None:
    default_results = tmp_path / "default.private.json"
    salted_results = tmp_path / "salted.private.json"
    comparison_json = tmp_path / "compare.json"
    comparison_md = tmp_path / "compare.md"

    _run_cli(
        "evaluate",
        "--cases",
        _CASES,
        "--predictions",
        _PREDICTIONS,
        "--out",
        default_results,
        "--private",
    )
    _run_cli(
        "evaluate",
        "--cases",
        _CASES,
        "--predictions",
        _PREDICTIONS,
        "--out",
        salted_results,
        "--private",
        "--private-salt",
        "demo",
    )
    _run_cli(
        "compare",
        "--results",
        f"default={default_results}",
        "--results",
        f"salted={salted_results}",
        "--out-json",
        comparison_json,
        "--out-md",
        comparison_md,
    )

    comparison = json.loads(comparison_json.read_text(encoding="utf-8"))
    text = comparison_json.read_text(encoding="utf-8") + comparison_md.read_text(encoding="utf-8")
    assert len(comparison["parsers"]) == 2
    assert comparison["case_scores"][0]["case_id"].startswith("case_")
    assert _ORIGINAL_CASE_ID not in text
    assert _SAMPLE_CONTENT not in text
