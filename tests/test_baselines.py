"""Tests for the baseline runner workflow using a fake local parser."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from docfailbench.baselines import run_baseline
from docfailbench.evaluator import evaluate
from docfailbench.io import load_cases, load_predictions


_FAKE_PARSER = r'''\
import argparse, pathlib, textwrap

ap = argparse.ArgumentParser()
ap.add_argument("--input", required=True)
ap.add_argument("--output", required=True)
ap.add_argument("--page", default="")
ap.add_argument("--case-id", default="")
args = ap.parse_args()

name = pathlib.Path(args.input).stem

# Produce deterministic markdown that satisfies a few sample assertions.
md = textwrap.dedent(f"""\
    # Fake output for {name}

    基于视觉语言模型的文档理解

    Some body text.

    | 项目 | 2025 | 2024 |
    | --- | --- | --- |
    | 营业收入 | 1,234.56 | 1,010.30 |

    $\\sum_{{i=1}}^{{n}} a_i$

    动能定理表明合外力做功等于物体动能的变化量
""")

pathlib.Path(args.output).write_text(md, encoding="utf-8")
'''

_FAKE_JSON_PARSER = r'''\
import argparse, json, pathlib

ap = argparse.ArgumentParser()
ap.add_argument("--input", required=True)
ap.add_argument("--output", required=True)
ap.add_argument("--page", default="")
ap.add_argument("--case-id", default="")
args = ap.parse_args()

payload = {
    "markdown": "json parser output for " + pathlib.Path(args.input).stem,
    "elements": [{"type": "text", "text": "json element", "page": 1}],
    "metadata": {"source": "fake_json"},
}
pathlib.Path(args.output).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
'''

_BAD_JSON_PARSER = r'''\
import argparse, pathlib

ap = argparse.ArgumentParser()
ap.add_argument("--input", required=True)
ap.add_argument("--output", required=True)
args = ap.parse_args()

pathlib.Path(args.output).write_text("{not valid json", encoding="utf-8")
'''

# Real sample case files that exist in the repo
_CASES_PATH = "data/cases/sample_cases.json"
_cases = load_cases(_CASES_PATH)
_N_CASES = len(_cases)
_N_ASSERTIONS = sum(len(c.assertions) for c in _cases)


def _write_fake_parser(tmp_path: Path, name: str = "fake_parser.py", source: str = _FAKE_PARSER) -> Path:
    script = tmp_path / name
    script.write_text(source, encoding="utf-8")
    return script


def _write_manifest(tmp_path: Path, parser_name: str, command: str, output_kind: str = "markdown") -> Path:
    manifest = {
        "parsers": [
            {
                "name": parser_name,
                "output_kind": output_kind,
                "timeout_seconds": 30,
                "command": command,
            }
        ]
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return path




def test_baseline_runs_and_writes_predictions(tmp_path: Path) -> None:
    """The baseline command runs a fake parser and writes predictions JSON."""
    script = _write_fake_parser(tmp_path)
    cmd = f'"{sys.executable}" "{script}" --input "$document_path" --output "$output_path" --page "$page" --case-id "$case_id"'
    manifest = _write_manifest(tmp_path, "fake", cmd)
    out = tmp_path / "preds.json"

    written = run_baseline(
        manifest_path=manifest,
        parser_name="fake",
        cases_path=_CASES_PATH,
        predictions_out=out,
    )

    assert written["predictions_count"] == _N_CASES
    assert out.exists()
    preds = load_predictions(out)
    assert len(preds) == _N_CASES
    assert all(p.parser == "fake" for p in preds)
    # Our fake parser writes recognisable text.
    assert "基于视觉语言模型的文档理解" in preds[0].markdown


def test_baseline_writes_raw_outputs(tmp_path: Path) -> None:
    """When --raw-dir is given, per-case .meta.json and .md files appear."""
    script = _write_fake_parser(tmp_path)
    cmd = f'"{sys.executable}" "{script}" --input "$document_path" --output "$output_path" --page "$page" --case-id "$case_id"'
    manifest = _write_manifest(tmp_path, "fake", cmd)
    out = tmp_path / "preds.json"
    raw = tmp_path / "raw"

    run_baseline(
        manifest_path=manifest,
        parser_name="fake",
        cases_path=_CASES_PATH,
        predictions_out=out,
        raw_dir=raw,
    )

    assert raw.is_dir()
    meta_files = list(raw.glob("*.meta.json"))
    md_files = list(raw.glob("*.md"))
    assert len(meta_files) == 3
    assert len(md_files) == 3
    # Sidecar JSON should be valid and contain case_id.
    sidecar = json.loads(meta_files[0].read_text(encoding="utf-8"))
    assert "case_id" in sidecar
    assert "metadata" in sidecar


def test_baseline_evaluate_in_one_shot(tmp_path: Path) -> None:
    """Passing results_out triggers evaluation and writes results JSON."""
    script = _write_fake_parser(tmp_path)
    cmd = f'"{sys.executable}" "{script}" --input "$document_path" --output "$output_path" --page "$page" --case-id "$case_id"'
    manifest = _write_manifest(tmp_path, "fake", cmd)
    out = tmp_path / "preds.json"
    results = tmp_path / "results.json"
    html = tmp_path / "report.html"

    written = run_baseline(
        manifest_path=manifest,
        parser_name="fake",
        cases_path=_CASES_PATH,
        predictions_out=out,
        results_out=results,
        html_out=html,
    )

    assert "results" in written
    assert "html" in written
    assert results.exists()
    assert html.exists()

    payload = json.loads(results.read_text(encoding="utf-8"))
    assert payload["summary"]["case_count"] == 3
    assert payload["summary"]["assertion_count"] == 15
    # The fake parser satisfies some but not all assertions.
    assert payload["summary"]["passed"] > 0
    assert payload["summary"]["failed"] > 0


def test_baseline_metadata_enriched(tmp_path: Path) -> None:
    """Predictions include enriched metadata: elapsed_seconds, output_source, etc."""
    script = _write_fake_parser(tmp_path)
    cmd = f'"{sys.executable}" "{script}" --input "$document_path" --output "$output_path" --page "$page" --case-id "$case_id"'
    manifest = _write_manifest(tmp_path, "fake", cmd)
    out = tmp_path / "preds.json"

    run_baseline(
        manifest_path=manifest,
        parser_name="fake",
        cases_path=_CASES_PATH,
        predictions_out=out,
    )

    preds = json.loads(out.read_text(encoding="utf-8"))["predictions"]
    for pred in preds:
        meta = pred["metadata"]
        assert "elapsed_seconds" in meta
        assert isinstance(meta["elapsed_seconds"], (int, float))
        assert meta["elapsed_seconds"] >= 0
        assert meta["output_source"] == "file"
        assert "returncode" in meta
        assert meta["returncode"] == 0
        assert "command" in meta
        assert "case_id" in meta
        assert "document_path" in meta
        assert Path(meta["document_path"]).is_absolute()


def test_baseline_json_output_kind(tmp_path: Path) -> None:
    """A parser with output_kind=json is correctly parsed."""
    script = _write_fake_parser(tmp_path, "json_parser.py", _FAKE_JSON_PARSER)
    cmd = f'"{sys.executable}" "{script}" --input "$document_path" --output "$output_path" --page "$page" --case-id "$case_id"'
    manifest = _write_manifest(tmp_path, "jsonfake", cmd, output_kind="json")
    out = tmp_path / "preds.json"

    run_baseline(
        manifest_path=manifest,
        parser_name="jsonfake",
        cases_path=_CASES_PATH,
        predictions_out=out,
    )

    preds = load_predictions(out)
    assert len(preds) == 3
    assert preds[0].markdown.startswith("json parser output for")
    assert len(preds[0].elements) == 1
    assert preds[0].elements[0]["text"] == "json element"
    assert preds[0].metadata["source"] == "fake_json"
    assert isinstance(preds[0].metadata["page"], int)


def test_baseline_bad_json_output_fails_prediction_not_run(tmp_path: Path) -> None:
    """Invalid JSON output should produce a failed prediction, not crash baseline."""
    script = _write_fake_parser(tmp_path, "bad_json_parser.py", _BAD_JSON_PARSER)
    cmd = f'"{sys.executable}" "{script}" --input "$document_path" --output "$output_path"'
    manifest = _write_manifest(tmp_path, "badjson", cmd, output_kind="json")
    out = tmp_path / "preds.json"

    run_baseline(
        manifest_path=manifest,
        parser_name="badjson",
        cases_path=_CASES_PATH,
        predictions_out=out,
    )

    preds = json.loads(out.read_text(encoding="utf-8"))["predictions"]
    assert len(preds) == 3
    assert all(pred["markdown"] == "" for pred in preds)
    assert all("JSON output could not be read" in pred["metadata"]["error"] for pred in preds)


def test_baseline_failing_parser_returns_empty(tmp_path: Path) -> None:
    """A parser that exits non-zero produces empty predictions with metadata."""
    script = tmp_path / "fail_parser.py"
    script.write_text("import sys; sys.exit(42)", encoding="utf-8")
    cmd = f'"{sys.executable}" "{script}" --input "$document_path" --output "$output_path"'
    manifest = _write_manifest(tmp_path, "failer", cmd)
    out = tmp_path / "preds.json"

    run_baseline(
        manifest_path=manifest,
        parser_name="failer",
        cases_path=_CASES_PATH,
        predictions_out=out,
    )

    preds = json.loads(out.read_text(encoding="utf-8"))["predictions"]
    assert len(preds) == 3
    for pred in preds:
        assert pred["markdown"] == ""
        assert pred["metadata"]["returncode"] == 42
        assert pred["metadata"]["output_source"] == "none"


def test_baseline_unknown_parser_raises(tmp_path: Path) -> None:
    """Requesting a parser not in the manifest raises ValueError."""
    manifest = _write_manifest(tmp_path, "real_parser", "echo hi")
    out = tmp_path / "preds.json"

    try:
        run_baseline(
            manifest_path=manifest,
            parser_name="nonexistent",
            cases_path=_CASES_PATH,
            predictions_out=out,
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "nonexistent" in str(exc)
