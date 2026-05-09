from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

from docfailbench.evaluator import evaluate, to_dict
from docfailbench.io import dump_json, load_cases, load_predictions
from docfailbench.issue_bundle import export_issues


def _write_cases(tmp_path: Path, *, page_image: str = "") -> Path:
    document = {
        "path": str(tmp_path / "private" / "secret_source.pdf"),
        "page": 1,
    }
    if page_image:
        document["page_image"] = page_image

    payload = {
        "cases": [
            {
                "case_id": "bundle_case_001",
                "title": "Bundle export fixture",
                "document": document,
                "profile": {"language": "zh_en_mixed", "document_type": "fixture"},
                "assertions": [
                    {
                        "id": "present_ok",
                        "type": "text_presence",
                        "severity": "major",
                        "params": {"text": "kept text"},
                    },
                    {
                        "id": "missing_fail",
                        "type": "text_presence",
                        "severity": "blocker",
                        "params": {"text": "missing text"},
                    },
                ],
            }
        ]
    }
    path = tmp_path / "cases.json"
    dump_json(path, payload)
    return path


def _write_predictions(tmp_path: Path) -> Path:
    payload = {
        "predictions": [
            {
                "case_id": "bundle_case_001",
                "parser": "fixture_parser",
                "markdown": "kept text " * 200,
                "metadata": {"source": "unit-test"},
            }
        ]
    }
    path = tmp_path / "predictions.json"
    dump_json(path, payload)
    return path


def _read_manifest(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as zf:
        return json.loads(zf.read("manifest.json"))


def test_export_issues_failed_only(tmp_path: Path) -> None:
    cases_path = _write_cases(tmp_path)
    predictions_path = _write_predictions(tmp_path)
    out_path = tmp_path / "issues.zip"

    summary = export_issues(
        cases_path=cases_path,
        predictions_path=predictions_path,
        out_path=out_path,
    )

    assert summary["exported"] == 1
    with zipfile.ZipFile(out_path) as zf:
        names = set(zf.namelist())
        assert "manifest.json" in names
        assert "issues/bundle_case_001/missing_fail.json" in names
        assert "issues/bundle_case_001/missing_fail.md" in names
        assert "issues/bundle_case_001/present_ok.json" not in names

    manifest = _read_manifest(out_path)
    assert manifest["only_failed"] is True
    assert manifest["total_assertions"] == 2
    assert manifest["total_failed"] == 1
    assert manifest["exported_count"] == 1


def test_export_issues_include_passed(tmp_path: Path) -> None:
    cases_path = _write_cases(tmp_path)
    predictions_path = _write_predictions(tmp_path)
    out_path = tmp_path / "issues.zip"

    summary = export_issues(
        cases_path=cases_path,
        predictions_path=predictions_path,
        out_path=out_path,
        only_failed=False,
    )

    assert summary["exported"] == 2
    with zipfile.ZipFile(out_path) as zf:
        names = set(zf.namelist())
        assert "issues/bundle_case_001/missing_fail.json" in names
        assert "issues/bundle_case_001/present_ok.json" in names

    manifest = _read_manifest(out_path)
    assert manifest["only_failed"] is False
    assert manifest["exported_count"] == 2


def test_export_issues_copies_page_image(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"not a real png but copyable")
    cases_path = _write_cases(tmp_path, page_image=str(image_path))
    predictions_path = _write_predictions(tmp_path)
    out_path = tmp_path / "issues.zip"

    summary = export_issues(
        cases_path=cases_path,
        predictions_path=predictions_path,
        out_path=out_path,
    )

    assert summary["page_images_copied"] == 1
    with zipfile.ZipFile(out_path) as zf:
        assert zf.read("issues/bundle_case_001/source_page.png") == b"not a real png but copyable"


def test_export_issues_missing_page_image_does_not_crash(tmp_path: Path) -> None:
    cases_path = _write_cases(tmp_path, page_image=str(tmp_path / "missing.png"))
    predictions_path = _write_predictions(tmp_path)
    out_path = tmp_path / "issues.zip"

    summary = export_issues(
        cases_path=cases_path,
        predictions_path=predictions_path,
        out_path=out_path,
    )

    assert out_path.exists()
    assert summary["page_images_copied"] == 0


def test_export_issues_redacts_document_path(tmp_path: Path) -> None:
    image_path = tmp_path / "private" / "page.png"
    cases_path = _write_cases(tmp_path, page_image=str(image_path))
    predictions_path = _write_predictions(tmp_path)
    out_path = tmp_path / "issues.zip"

    export_issues(
        cases_path=cases_path,
        predictions_path=predictions_path,
        out_path=out_path,
    )

    with zipfile.ZipFile(out_path) as zf:
        issue = json.loads(zf.read("issues/bundle_case_001/missing_fail.json"))
        document = issue["case"]["document"]
        assert "path" not in document
        assert "page_image" not in document
        assert document["path_basename"] == "secret_source.pdf"
        assert document["page_image_basename"] == "page.png"


def test_export_issues_accepts_precomputed_results(tmp_path: Path) -> None:
    cases_path = _write_cases(tmp_path)
    predictions_path = _write_predictions(tmp_path)
    cases = load_cases(cases_path)
    predictions = load_predictions(predictions_path)
    results_path = tmp_path / "results.json"
    dump_json(results_path, to_dict(evaluate(cases, predictions)))

    summary = export_issues(
        cases_path=cases_path,
        predictions_path=predictions_path,
        results_path=results_path,
        out_path=tmp_path / "issues.zip",
    )

    assert summary["exported"] == 1


def test_export_issues_cli_smoke(tmp_path: Path) -> None:
    cases_path = _write_cases(tmp_path)
    predictions_path = _write_predictions(tmp_path)
    out_path = tmp_path / "issues.zip"
    repo_root = Path(__file__).resolve().parents[1]

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "docfailbench.cli",
            "export-issues",
            "--cases",
            str(cases_path),
            "--predictions",
            str(predictions_path),
            "--out",
            str(out_path),
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Exported 1 issue(s)" in completed.stdout
    assert _read_manifest(out_path)["exported_count"] == 1
